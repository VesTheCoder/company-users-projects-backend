import http from 'k6/http';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';
import { Counter, Rate } from 'k6/metrics';

export const base = __ENV.BASE_URL || 'http://host.docker.internal:8080';
export const origin = __ENV.ORIGIN || 'http://localhost:8080';
export const sessions = new SharedArray('sessions', () => JSON.parse(open(__ENV.SESSIONS_FILE || '/data/load-sessions.json')));
export const conflicts = new Counter('expected_conflicts');
export const throttled = new Counter('rate_limited');
export const unexpected = new Rate('unexpected_errors');

export function actor() {
  return sessions[exec.scenario.iterationInTest % sessions.length];
}

export function request(method, path, user, body = null, extra = {}) {
  const response = http.request(method, base + path, body === null ? null : JSON.stringify(body), {
    headers: { Host: 'localhost:8080', Origin: origin, 'Content-Type': 'application/json',
      Cookie: `session=${user.cookie}`, 'X-CSRF-Token': user.csrf, ...extra },
    tags: { name: path.replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, ':id') },
  });
  const expectedConflict = response.status === 409 || response.status === 412;
  if (expectedConflict) conflicts.add(1);
  if (response.status === 429) throttled.add(1);
  unexpected.add(response.status >= 400 && !expectedConflict && response.status !== 429);
  check(response, { 'successful response': r => r.status >= 200 && r.status < 300 });
  return response;
}

export function arrival(rate, duration = '30s') {
  return { executor: 'constant-arrival-rate', rate, timeUnit: '1s', duration,
    preAllocatedVUs: 50, maxVUs: 250 };
}

export function readFlow(user) {
  const prefix = `/api/v1/companies/${user.company_id}`;
  const response = request('GET', prefix + '/employees?limit=25&status=active', user);
  if (response.status === 200 && response.json('next_cursor') && exec.scenario.iterationInTest % 10 === 0) {
    request('GET', prefix + '/employees?limit=25&status=active&cursor=' + encodeURIComponent(response.json('next_cursor')), user);
  }
}

export function projectFlow(user) {
  const prefix = `/api/v1/companies/${user.company_id}/projects`;
  const created = request('POST', prefix, user, { name: `Load ${__VU}-${__ITER}` });
  if (created.status !== 201) return;
  const path = prefix + '/' + created.json('id');
  const updated = request('PATCH', path, user, { status: 'active' }, { 'If-Match': created.headers.Etag });
  if (updated.status === 200) request('DELETE', path, user, null, { 'If-Match': updated.headers.Etag });
}

export function assignmentFlow(user) {
  const prefix = `/api/v1/companies/${user.company_id}`;
  const employees = request('GET', prefix + '/employees?status=active&limit=1', user);
  if (employees.status !== 200 || !employees.json('items').length) return;
  const project = request('POST', prefix + '/projects', user, { name: 'Assignment load' });
  if (project.status !== 201) return;
  const path = prefix + '/projects/' + project.json('id');
  const assignment = path + '/employees/' + employees.json('items.0.id');
  request('PUT', assignment, user);
  request('DELETE', assignment, user);
  request('DELETE', path, user, null, { 'If-Match': project.headers.Etag });
}
