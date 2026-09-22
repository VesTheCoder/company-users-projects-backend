import { actor, arrival, request, readFlow, projectFlow, assignmentFlow } from './common.js';

export const options = {
  scenarios: { business: arrival(Number(__ENV.RATE || 100), __ENV.DURATION || '30s') },
  thresholds: { http_req_duration: __ENV.FLOW === 'companies' ? ['p(95)<200', 'p(99)<500'] : __ENV.FLOW === 'employees' ? ['p(95)<250', 'p(99)<600'] : ['p(95)<300', 'p(99)<700'], unexpected_errors: ['rate<0.001'] },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const user = actor();
  if (__ENV.FLOW === 'companies') request('GET', '/api/v1/companies?limit=25', user);
  else if (__ENV.FLOW === 'projects') projectFlow(user);
  else if (__ENV.FLOW === 'assignments') assignmentFlow(user);
  else readFlow(user);
}
