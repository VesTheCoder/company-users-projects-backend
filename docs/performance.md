# Performance evidence

## Environment and dataset

Measured 2026-09-22 on Windows / Docker Desktop. Host: AMD Ryzen 5 7600X, 6 physical / 12 logical cores, 31.2 GiB RAM. Docker VM: **4 CPUs and 3.825 GiB total shared by API, PostgreSQL, Redis and k6**. API: one Uvicorn process, Python 3.13.12, no reload; PostgreSQL 18.6; Redis 8.10.2. k6: v2.3.0, image digest `sha256:e66db15b860113878fa74670e31f5e274830b7b6e42c8bff28b2f2d86a257603`.

This machine is substantially smaller than the plan's separate 4-vCPU API, 8-vCPU/16-GiB PostgreSQL and 2-vCPU Redis hosts. These are short local experiments, not production capacity certification.

The functional profile was loaded through bounded PostgreSQL COPY batches:

| Entity | Benchmark rows |
|---|---:|
| Accounts | 100,000 |
| Companies | 10,000 |
| Access grants | 500,000 |
| Employees | 1,000,000 |
| Projects | 250,000 |
| Assignments | 3,000,000 |
| Active sessions | 100,000 |

The Compose database also retains a small demo dataset. Employee skew: 80% in 20% of companies, with 100,000 employees in the largest company. Employee statuses include active, leave and terminated; terminated employees have no assignments. Project statuses include active and completed. The measured fixture uses admin grants to permit mutation scenarios; role enforcement is independently covered by API tests. Data generation wall time was 2,166.49 seconds on this Windows-to-Docker setup, including index/FK maintenance and short batch commits.

## Results and interpretation

The numeric table is in [benchmarks/results.md](benchmarks/results.md); raw summaries and query plans are committed alongside it. The final per-scenario runs lasted 30 seconds, except the 60-second lower-rate mixed baseline, the 10-login sample, and the 50-second local saturation ramp. Functional tests were not run concurrently with the final business scenarios. The short login sample overlapped briefly with the company-list scenario. Normal desktop activity was not isolated.

- Company lists, employee lists, project CRUD and assignment flows met their respective latency thresholds with no HTTP failures.
- The lower-rate mixed baseline sustained approximately **114 HTTP requests/s**, p95 **10 ms**, p99 **12 ms**, with no dropped iterations or HTTP failures.
- At 200 requested mixed iterations/s, the API delivered approximately **213 HTTP requests/s** but **failed** the p95 <400 ms / p99 <1,000 ms targets: observed p95 approximately **1.82 s**, p99 **2.81 s**. k6 dropped 244 iterations and reached its 250-VU limit. Every completed HTTP request succeeded; dropped demand must not be counted as serviced traffic.
- The mixed flow generates multiple requests per iteration, so iteration rate is not HTTP RPS. The measured mix is approximately 87% reads / 13% writes. Its target of 200 iterations/s is approximately 230 HTTP requests/s before dropped demand.
- The login result is only a 10-request, two-VU sample. It exercises real Argon2id and is **not** evidence for sustained 8-RPS login. The production IP/account limits remain enabled. Sustained login testing needs sufficiently distributed source IPs and accounts; spoofing forwarded headers is not supported by local Compose.

The saturation scenario records queue growth and achieved throughput in [benchmarks/saturation-curve.md](benchmarks/saturation-curve.md). It ramps **100 → 300 iterations/s** on this local machine, not the plan's 300 → 1,500 RPS on scaled hardware. The latter scenario is provided but was not claimed as validated here.

Pool acquisition metrics are recorded in [benchmarks/runtime-metrics.json](benchmarks/runtime-metrics.json). The saturation run produced **113 HTTP 503 responses**, matching **113 pool checkout timeouts**; the slow-query counter remained zero. Connection acquisition queues grow sharply under overload. This establishes a local pool/processing bottleneck; it does not identify CPU as the sole cause or justify adding database indexes. More API replicas, a suitable connection budget and isolated database resources require a new measurement. Company-wide write locks also bound throughput for a single hot tenant. Readiness and normal traffic recovered after the saturation run.

## Query plans

[benchmarks/query-plans.json](benchmarks/query-plans.json) contains PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` output after ANALYZE, plus relevant database settings. All nine critical queries use indexes. Measured execution times ranged from **0.031 to 3.16 ms**:

| Query | Execution ms | Main index |
|---|---:|---|
| Session + active user | 0.156 | unique token hash, user PK |
| Accessible companies | 0.752 | access user cursor index |
| Company access | 0.591 | company access PK |
| Employee first page | 0.957 | employee company cursor index |
| Employee status page | 1.065 | employee company/status cursor index |
| Employee deep page | 0.571 | employee company cursor index |
| Project page | 3.160 | project company/status index chosen by planner |
| Project status page | 0.031 | project company/status cursor index |
| Joined assignments | 1.421 | assignment cursor index, employee PK |

The deep employee query anchors around row 10,000 in a tenant containing 100,000 employees; it does not scan through OFFSET rows. These SQL timings exclude HTTP, serialization, authentication, Redis and pool waits. Planner choices vary with data distribution and cache state.

## Reproduce

Use a fresh migrated development database for each dataset profile. The generator refuses a second load when benchmark IDs already exist. It does not truncate an existing database. Preserve demo/business data by using a separate Compose project/database for experiments. Session fixtures expire eight hours after generation; regenerate on a fresh benchmark database before later runs.

```powershell
. .venv/Scripts/Activate.ps1
uv run python -m scripts.generate_load_data --profile functional
uv run python -m scripts.explain_queries
./load/run-local.ps1 -DurationSeconds 30
uv run python -m scripts.summarize_benchmarks
```

`small` generates a development-sized fixture; `functional` generates the table above; `cardinality` defines the long-term 10-million-account / 50-million-employee / 150-million-assignment dataset and requires appropriately sized infrastructure. **The cardinality profile was not executed.** Generated session credentials remain in ignored `.local/load-sessions.json`; they are never committed.

For a single scenario, mount `load/k6` as `/scripts`, `.local` read-only as `/data`, and an output directory as `/results` in the pinned k6 image. Run `business_flows.js` with `FLOW=companies|employees|projects|assignments`, `RATE=<iterations/s>` and `DURATION=<duration>`. `mixed.js` accepts RATE/DURATION; `FULL_PROFILE=true` supplies a 5-minute ramp, 30-minute steady/peak phase and 5-minute cooldown. `login.js` accepts a protected `LOAD_PASSWORD` environment variable; `FULL_PROFILE=true` configures the planned sustained login workload for distributed generators. `saturation.js` accepts START_RATE, PEAK_RATE, RAMP_DURATION and HOLD_DURATION; defaults target scaled hardware.

The full 40-minute mixed profile, sustained distributed login, scaled 1,500-RPS saturation, multi-replica capacity and 10-million-account cardinality remain **unmeasured**. No guarantee of 10 million concurrent users is made. The backend has the planned scaling mechanisms and reproducible measurement tools, with a documented local operating range and explicit failed thresholds.
