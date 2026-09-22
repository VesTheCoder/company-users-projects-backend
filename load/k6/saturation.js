import { actor, readFlow } from './common.js';

export const options = {
  scenarios: { saturation: { executor: 'ramping-arrival-rate', startRate: Number(__ENV.START_RATE || 300), timeUnit: '1s',
    preAllocatedVUs: 100, maxVUs: 500,
    stages: [ { target: Number(__ENV.PEAK_RATE || 1500), duration: __ENV.RAMP_DURATION || '5m' },
      { target: Number(__ENV.PEAK_RATE || 1500), duration: __ENV.HOLD_DURATION || '5m' }, { target: 0, duration: '10s' } ] } },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () { readFlow(actor()); }
