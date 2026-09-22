import http from 'k6/http';
import { check } from 'k6';
import { base, origin, actor, unexpected, throttled } from './common.js';

export const options = {
  scenarios: { login: __ENV.FULL_PROFILE === 'true' ? { executor: 'constant-arrival-rate', rate: 8, timeUnit: '1s', duration: '10m', preAllocatedVUs: 20, maxVUs: 20 } : { executor: 'shared-iterations', vus: Number(__ENV.VUS || 2), iterations: Number(__ENV.ITERATIONS || 10), maxDuration: '1m' } },
  thresholds: { http_req_duration: ['p(95)<750', 'p(99)<1500'], unexpected_errors: ['rate<0.001'] },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const response = http.post(base + '/api/v1/auth/login', JSON.stringify({ login: actor().login, password: __ENV.LOAD_PASSWORD }), {
    headers: { Host: 'localhost:8080', Origin: origin, 'Content-Type': 'application/json', 'X-CSRF-Protection': '1' },
  });
  if (response.status === 429) throttled.add(1);
  unexpected.add(response.status !== 200 && response.status !== 429);
  check(response, { 'login accepted': r => r.status === 200 });
}
