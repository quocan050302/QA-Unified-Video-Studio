# RESOURCE AUDIT — KH-03.0.R2 (`20261117_094557Z_0fd8`)

## 1. Host Environment & Safety Guardrails

- **CPU**: `12` logical processors
- **GPU**: `Microsoft Edge` (`ANGLE (Intel(R) UHD Graphics 730 Direct3D11 vs_5_0 ps_5_0, D3D11)`)
- **Active Guardrails**: `ResourceMonitor(min_disk_gb=6.0, min_ram_gb=2.0, interval_sec=0.5)`; async DAG bounded by `asyncio.Semaphore(2)` for short/light browser jobs and `asyncio.Semaphore(1)` for heavy exports.

## 2. Measured Disk, RAM & Concurrency Telemetry

- **Async DAG Telemetry (`evidence/async_dag_telemetry.json`)**:
  - `total_jobs_executed`: `32`
  - `max_concurrent_jobs_observed`: `3` (e.g., `P1/G05_controlled_ab`, `P2/G06_G08_perceptual_mp4`, `P1/G03_G04_graph_decoupling` overlapped cleanly at `00:56:10Z`; `real20_01`..`real20_20` executed `2` concurrent short renders throughout `P4_REAL20`)
- **R2 Pipeline Observed Peaks (`P0..P3 + P4_REAL20 + G15`)**:
  - `min_disk_free_gb`: **`51.42 GiB`** (threshold `>= 6.0 GiB`)
  - `min_ram_free_gb`: **`8.23 GiB`** (threshold `>= 2.0 GiB`)
  - `monitor_breached`: **`false`**
- **Isolated Legacy 81-Gate E2E (`G14` separate process monitor)**:
  - `legacy_e2e_min_disk_gb_observed`: **`51.43 GiB`**
  - `legacy_e2e_min_ram_gb_observed`: **`3.05 GiB`** (no breach above 2.0 GiB in clean isolated run)

## 3. 3-Repeat Serial (`workers=1`) vs Parallel (`workers=2`) Render Benchmark (`0..6s` @ `0.5x`)

| Repeat | `workers=1` (s) | `workers=2` (s) |
|---|---|---|
| Run 1 | `5.172` | `4.187` |
| Run 2 | `4.828` | `4.344` |
| Run 3 | `5.078` | `4.157` |
| **Median** | **`5.078s`** | **`4.187s`** |
| **Measured Speedup** | **1.000x** | **`1.213x`** |
