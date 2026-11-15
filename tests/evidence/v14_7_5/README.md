# Evidence Directory — FL-01 / V14.7.5

All artifacts in `tests/evidence/v14_7_5/` are produced by real execution via `python3 scripts/run_fl01_v14_7_5_validation.py`:

- `00_master_acceptance.json` — Master `R1`–`R8` + `J13` verdict ledger and failure-injection self-checks.
- `01_branch_integrity.json` — Work branch (`fix/Image-Shot`), ancestor check, `Production` SHA invariant, and disk/RAM floor preflight.
- `02_process_tree_resources.json` — Recursive process-tree RSS, CPU, disk, inode, and sample-drop telemetry.
- `03_real_async_dag_jobs.json` — Multi-wave DAG job execution records and measured temporal concurrency overlap proof.
- `04_mutation_actual_execution.json` — 4 disposable-subprocess detector mutations + 15 negative fixtures.
- `05_e2e_regression_full.json` — Full `scripts/run_e2e_regression.py` execution summary (`FLOW_READY`).
- `06_historical_backtest_truth.json` — Explicit separation of `G5` synthetic 180-shot stress (`PASS`) vs `G5c` company dataset (`NOT_AVAILABLE`).
- `07_repair_loop_real_video.json` — Real disposable 3-shot Squire MP4 defect injection, repair rebuild, and `manual_locked` protection proof.
- `08_old_films_preservation.json` — Byte-for-byte SHA256 verification of all 7 prior preview MP4s and user configs.
- `09_eagle_fog_media_provenance.json` — Full decode, EBU R128 loudness, and cryptographic receipt provenance for *The Eagle in the Fog*.
- `10_eagle_fog_temporal_qa.json` — Frame-by-frame decoded Temporal Visual QA report (`12/12` shots).
- `11_voice_timing_measured.json` — Measured voice clip durations, `0.0 ms` overlap, and natural tail margins.
- `12_speed_serial_vs_parallel.json` — `n = 3` measured serial vs bounded-parallel benchmark runs.
- `13_production_post_push_attestation.json` — Remote `fix/Image-Shot` & `Production` SHA attestation before/after push.
- `contact_sheet_full.png`, `contact_sheet_hook.png`, `contact_sheet_action.png` — Decoded PNG contact sheets from the final 1080p24 MP4.
