import exec from 'k6/execution';
import { actor, arrival, request, readFlow, projectFlow } from './common.js';

const fullProfile = { executor: 'ramping-arrival-rate', startRate: 0, timeUnit: '1s',
  preAllocatedVUs: 250, maxVUs: 1000, stages: [
    { duration: '5m', target: 220 }, { duration: '29m', target: 220 },
    { duration: '1m', target: 440 }, { duration: '5m', target: 0 } ] };

export const options = {
  scenarios: { mixed: __ENV.FULL_PROFILE === 'true' ? fullProfile : arrival(Number(__ENV.RATE || 200), __ENV.DURATION || '30s') },
  thresholds: { http_req_duration: ['p(95)<400', 'p(99)<1000'], unexpected_errors: ['rate<0.001'] },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const user = actor();
  const iteration = exec.scenario.iterationInTest % 20;
  if (iteration === 0) projectFlow(user);
  else if (iteration < 4) request('GET', '/api/v1/companies?limit=25', user);
  else readFlow(user);
}
