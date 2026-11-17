# KH-03.0 — Bounded Concurrency, Reproducibility & Resource Safety Audit (`RESOURCE_AUDIT.md`)

- **Telemetry Source**: [`evidence/validation_summary.json`](./evidence/validation_summary.json) & [`evidence/speed_and_reproducibility.json`](./evidence/speed_and_reproducibility.json)
- **Resource Monitor**: `scripts/resource_guard.py::ResourceMonitor` (`1.0s` continuous sampling across entire `422s` validation DAG)

## 1. Concurrency Caps & Safety Guardrails

- **Host Capacity**: `12` logical CPUs, `31.75 GiB` physical RAM, `144.02 GiB` output SSD (`53.96 GiB` free at preflight).
- **Configured Worker Caps**:
  - Lightweight CPU/IO executor (`ThreadPoolExecutor`): `max_workers = 3` (`<= min(3, floor(12 / 2))`).
  - Heavy Chromium/FFmpeg semaphore (`asyncio.Semaphore`): `2` (permitted only because preflight measured `9.24 GiB >= 6.0 GiB` free RAM and `53.96 GiB >= 16.0 GiB` free disk; each job ran in an isolated scratch directory).
- **Continuous 1s Resource Telemetry Across Full Run**:
  - Samples collected: **`419`**
  - Minimum free disk observed: **`53.27 GiB`** (safety floor: `10.00 GiB` -> `43.27 GiB` margin above floor)
  - Minimum available RAM observed: **`3.19 GiB`** (safety floor: `1.00 GiB` -> `2.19 GiB` margin above floor)
  - Threshold breaches: **`0`** (`breached: false`)
  - Streaming temporal validation decoded all `720` frames via in-memory FFmpeg `rgb24` pipe (`480x270`), writing **`0` bytes** of raw uncompressed RGB frame dumps to disk.
- **User & Historical Data Protection**:
  - `QA_PRESERVE_TEST_RUNS=1` enforced throughout; all prior `.test-runs/*` directories (`29` historical folders including KH-01/KH-02 runs) remained 100% untouched.
  - Disposable breach test (`M13`) verified `ResourceMonitor` terminates **only** registered owned child PIDs via `kill_process_tree()`.

## 2. DAG Monotonic Execution Trace

| Job | Category | Status | `t_start_mono` | `t_end_mono` | Wall Time (s) |
|---|---|---|---|---|---|
| `style_lock_contract` | `light` (concurrent Stage 1) | `PASS` | `394608.953` | `394608.968` | `0.015` |
| `baseline_preservation` | `heavy` (concurrent Stage 1) | `PASS` | `394608.953` | `394612.343` | `3.390` |
| `same_pose_reference_poc` | `heavy` (concurrent Stage 1) | `PASS` | `394608.953` | `394613.593` | `4.640` |
| `fresh_preview_build` | `light` (Stage 2) | `PASS` | `394613.593` | `394613.750` | `0.157` |
| `guard_2d_only` | `heavy` (Stage 2) | `PASS` | `394613.750` | `394616.421` | `2.671` |
| `render_full_30s` | `heavy` (Stage 3 receipt check) | `PASS` | `394616.421` | `394616.437` | `0.016` |
| `camera_and_contact_qa` | `light` (concurrent Stage 4) | `PASS` | `394616.437` | `394616.531` | `0.094` |
| `frame_temporal_validation` | `light` (concurrent Stage 4) | `PASS` | `394616.437` | `394619.375` | `2.938` |
| `negative_mutations` | `light` (concurrent Stage 4) | `PASS` | `394616.437` | `394620.328` | `3.891` |
| `real_backtests` | `heavy` (Stage 5) | `PASS` | `394620.328` | `394640.156` | `19.828` |
| `speed_and_reproducibility` | `heavy` (Stage 5) | `PASS` | `394640.156` | `394665.125` | `24.969` |
| `legacy_regression` | `heavy` (Stage 6) | `PASS` | `394665.125` | `395030.718` | `365.593` |

## 3. Frame-Order Determinism & 3-Repeat Speed Benchmark

1. **Forward / Reverse / Seeded-Random Frame-Order Invariance**:
   - Sampled `18` frames across all 9 pilot shots (`[0, 28, 65, 110, 150, 200, 239, 275, 313, 328, 374, 410, 460, 512, 575, 610, 660, 710]`) via `window.renderFrame(fr, { png: true })` on ANGLE Direct3D11.
   - Mismatches across `forward`, `reverse`, and `seeded_random` evaluation order: **`0 / 18`** (`100%` identical SHA-256 per frame).
   - *Cross-platform note*: Same-host, same-GPU rasterization is 100% deterministic; minor sub-pixel anti-aliasing differences are expected across different OS/GPU backends.
2. **3-Repeat QA Workload Speedup vs Video Export Wall Time (Separated Honestly)**:
   - **Tested QA Still-Slice Workload** (3 isolated 3-still slices @ `960x540`, 3 repeats each):
     - Serial (`1` worker): `[4.719s, 4.672s, 4.656s]` -> mean **`4.682s`**
     - Bounded Parallel (`3` workers): `[2.390s, 2.219s, 2.219s]` -> mean **`2.276s`**
     - Measured QA workload speedup: **`2.057x`** (`9` verified overlapping worker pairs; `100%` identical canonical output digest `96575e8db2662239fc0273129021f04656a40f23c620293948a831dfd1e6a033` across all `6` runs).
   - **Full 30.000s 1080p24 Pilot Video Export Wall Time** (`node render.mjs --workers 2` + preflight `--check` + `tools/mix.py`):
     - `720`-frame 1080p render + preflight check: ~`26.8s` (`~29.5 fps` encode throughput) + `mix.py` loudness/AAC remux ~`2.6s`.
