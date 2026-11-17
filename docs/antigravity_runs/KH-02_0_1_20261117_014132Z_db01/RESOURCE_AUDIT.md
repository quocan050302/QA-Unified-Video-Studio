# KH-02.0 + KH-02.1 — Resource Telemetry & Bounded Concurrency Audit (`RESOURCE_AUDIT.md`)

- **Source Telemetry**: `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/evidence/master_verdict.json` (`resource_telemetry`, `run_preflight`, `job_speed_trial`)
- **Monitor Implementation**: `scripts/resource_guard.py::ResourceMonitor` (`1.0s` sampling interval, child-tree PID registration only — never kills unrelated user applications)

## 1. Disk & RAM Guard Rails Across Full 542.58s Validation Run

| Metric | Guard Threshold | Preflight Value | Minimum Observed (`538` samples) | End-of-Run Value | Status |
| --- | --- | --- | --- | --- | --- |
| Free Disk Space (`D:`) | `>= 8.0 GiB` (`6 GiB` + `2 GiB` reserve; `>= 10 GiB` preferred) | `54.23 GiB` / `144.02 GiB` | **`53.99 GiB`** | `53.99 GiB` | `PASS` (`breached: false`) |
| Available RAM | `>= 1.0 GiB` post-reserve | `10.94 GiB` / `31.75 GiB` | **`4.91 GiB`** | `10.23 GiB` | `PASS` (`breached: false`) |

## 2. Bounded Async DAG Worker Caps

- **Logical CPUs Detected**: `12`
- **Light Async Worker Pool (`ThreadPoolExecutor`)**: `3` (`min(3, max(1, 12 // 2))`) — used for Wave 1 independent contract, syntax, and pytest mutation tasks.
- **Heavy 1080p Chromium Render Semaphore (`asyncio.Semaphore`)**: `1` — strictly serializes heavy Chromium/FFmpeg jobs (`job_2d_only_guard`, `job_generate_new_art`, `job_render_original_30s`, `job_render_motion_probe`, `job_backtests`) so peak browser RSS never starves available RAM.
- **Per-Job Workspace Isolation**:
  - KH-02 scratch artifacts stay inside `.test-runs/kh02_20261117_014132Z_db01/` (`guard_2d_probes/`, `determinism_probe/`, `backtests/`, `speed_trial/`, `legacy_e2e_scratch/`).
  - Pre-existing `.test-runs/kh01_r1_20261116_074000Z` was explicitly preserved (`QA_PRESERVE_TEST_RUNS=1`).
  - Zero raw PNG frame sequences were committed to Git.

## 3. Serial vs Bounded-Parallel QA Speed & Reproducibility Trial (`>= 3` Repeats)

Workload per repeat: `3` independent isolated project clones (`workload_0`, `workload_1`, `workload_2`), each running `node render.mjs --stills 0.5,8.2,20.4 --scale 0.5` + `python tools/validator.py --stage preflight --json`.

| Mode | Workers | Repeat 1 (s) | Repeat 2 (s) | Repeat 3 (s) | Mean (s) | Median (s) | Output PNG SHA-256 Digest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Serial | `1` | `5.079` | `4.909` | `4.837` | `4.942` | `4.909` | `8b2c24ec693ad4aed64f2e88a322bbfbc700eb63137cc6f3448b1a3213167388` (all 3 tasks x 3 repeats) |
| Bounded Parallel | `3` | `2.342` | `2.593` | `2.333` | `2.423` | `2.342` | `8b2c24ec693ad4aed64f2e88a322bbfbc700eb63137cc6f3448b1a3213167388` (`100%` byte-identical) |

- **Measured QA Workload Speedup Ratio**: **`2.04x`** (`4.942s -> 2.423s`), with real measured concurrency overlap windows (`[0.000..2.313s]`, `[0.001..2.341s]`, `[0.001..2.299s]`).
- **Scope Honesty Disclaimer**: This `2.04x` speedup applies **strictly to independent parallel QA tasks across isolated workspaces**. It is **NOT** extrapolated to single-stream video rendering or FFmpeg muxing (`job_render_original_30s` took `117.24s` wall time for `720` full `1920x1080` Canvas2D frames + audio mastering).
