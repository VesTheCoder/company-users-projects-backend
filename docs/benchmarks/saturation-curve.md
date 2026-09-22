| Completion window | Requests/s | p95 ms | p99 ms | HTTP failures |
|---|---:|---:|---:|---:|
| 0-10s | 165.0 | 26.58 | 36.59 | 0 |
| 10-20s | 197.4 | 1580.75 | 2280.41 | 0 |
| 20-30s | 229.8 | 4206.04 | 5601.49 | 26 |
| 30-40s | 210.1 | 5102.76 | 6250.47 | 39 |
| 40-50s | 192.7 | 5190.62 | 6457.89 | 48 |

Windows use completion time; the last window may be partial. This is a local 100-to-300 iteration/s ramp, not a scaled validation.
