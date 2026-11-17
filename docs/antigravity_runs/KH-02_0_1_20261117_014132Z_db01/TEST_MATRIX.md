# KH-02.0 + KH-02.1 — Complete Technical Test, Determinism, Backtest & Mutation Matrix (`TEST_MATRIX.md`)

- **Master Receipt**: `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/evidence/master_verdict.json`
- **Tracked Evidence Copy**: `tests/evidence/kh02_20261117_014132Z_db01/master_verdict.json`
- **Generated At (UTC)**: `2026-11-17T04:03:42Z`

## 1. Aggregate Test Counts (Zero False PASS)

| Suite / Category | PASS | FAIL | NOT_RUN (Honest Missing Fixture) | Verdict Label |
| --- | --- | --- | --- | --- |
| Master KH-02 Orchestration Jobs (`run_kh02_0_1_validation.py`) | `12` | `0` | `0` | `PASS` |
| KH-02 Pytest Unit + Negative Mutation Suites (`tests/kh02_2d`) | `6` (`14` mutants killed + `2` FP guards) | `0` | `0` | `PASS` |
| Backtest (a) 180-Shot Stress Case | `1` (`180` shots) | `0` | `0` | `SYNTHETIC_PASS` (`equivalent_to_historical: false`) |
| Backtest (b) 20-Shot Multi-Angle Real MP4 | `1` (`600` frames, `25.0s`) | `0` | `0` | `REAL_RENDERED_PASS` |
| Backtest (c) Historical Company Fixture Replay | `0` | `0` | `1` (`tests/fixtures/historical_company_180`) | `NOT_RUN_MISSING_FIXTURE` (`counted_as_pass: false`) |
| Legacy Studio Full E2E Regression (`scripts/run_e2e_regression.py`) | `81` required gates | `0` | `1` optional (`NOT_RUN_OPTIONAL_MISSING_FIXTURE`) | `FLOW_READY` |
| **Total Distinct Executed Technical Gates** | **`101` PASS** | **`0` FAIL** | **`2` NOT_RUN** (never counted as PASS) | **`TECH_PASS_HUMAN_REVIEW_PENDING`** |

## 2. Per-Job Breakdown (`scripts/run_kh02_0_1_validation.py`)

| Job Name | Status | Wall Time | Key Verified Metrics |
| --- | --- | --- | --- |
| `run_preflight` | `PASS` | `< 0.1s` | Branch `feat/modern-2d-cinematic`, ancestor of `origin/Production` (`80559d09...`), `54.23 GiB` free disk, `10.94 GiB` available RAM. |
| `job_baseline` | `PASS` | `1.659s` | `40/40` JS `--check` pass, `1552` Squire baseline frames `0` errors, all preserved baseline SHA-256 digests intact. |
| `job_style_contract` | `PASS` | `0.005s` | `style_id = squire_cinematic_2d.v1`, canonical digest `f1b22b7606f80d1e37c2f32a4cd97152c5c6765400506caa7a9e1f768f333a75`, 3 distinct niche digests (`roman`, `medieval`, `non_historical_future`), `8/8` shots valid. |
| `job_2d_only_guard` | `PASS` | `2.843s` | KH-02 loads `0` Three.js URLs (`three3dLoaded: false`); injected `kind: '3d'` shot rejected at boot + CLI (`KH02_2D_ONLY_VIOLATION`, `threeUrlsCount: 0`); legacy 3D probe still loads `/engine/three3d.js` (`three3dLoaded: true`). |
| `job_generate_new_art` | `PASS` | `3.071s` | `11` fresh Canvas2D POC files rendered and SHA-verified; `TAVI` & `LYRA` validated as human 2D rigs; `PIP` validated as `quadruped_animal_2d` (`is_human_rig: false`). |
| `job_render_original_30s` | `PASS` | `117.241s` | `KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4` (`9,009,085` bytes, `sha256: 2f521d88...`): `1920x1080`, `h264` + `aac`, `24/1 fps`, `30.0s`, `720` decoded frames, `-14.0 LUFS`, `-1.7 dBTP`. |
| `job_render_motion_probe` | `PASS` | `4.683s` | `16` keyframes across `S01..S08` rendered in `forward_pass_1`, `reverse_order`, `random_order`, and `forward_pass_2`: **`0` SHA-256 mismatches**. |
| `job_temporal_qa` | `PASS` | `1.742s` | `720` decoded frames, `0` blank frames, `92.91%` ROI temporal activity, `7/7` cut joins continuous, `max_grip_distance_px = 0.0`, `max_planted_foot_drift_px = 0.0`, `8/8` camera curves within 2D bounds. |
| `job_negative_mutations` | `PASS` | `1.917s` | `pytest tests/kh02_2d -v`: `6/6` passed (`1.42s`), killing all `14` mandatory negative mutations while passing `2` false-positive guards. |
| `job_backtests` | `PASS` | `23.449s` | `180`-shot `SYNTHETIC_PASS` (`7.086s` fast check); `20`-shot real MP4 `REAL_RENDERED_PASS` (`600` decoded frames, `25.0s`, `sha256: e72b8def...`); historic check `NOT_RUN_MISSING_FIXTURE`. |
| `job_speed_trial` | `PASS` | `~22.1s` | `3` serial (`mean 4.942s`) vs `3` parallel (`mean 2.423s`) repeats -> `2.04x` QA-only speedup with `100%` identical PNG output digests (`8b2c24ec...`). |
| `job_old_pack_e2e_regression` | `PASS` | `365.270s` | `81/81` required gates passed (`G1..G27`, `H1..H20`, `J1..J22`, `K1..K15`), `FLOW_READY`, zero tracked diff in `tests/evidence/*`. |

## 3. Negative Mutation Matrix (`tests/kh02_2d/test_kh02_foundation.py`)

All 14 negative fixtures failed locally when fed to the detectors and were killed cleanly:

1. `M01_3d_kind_in_canvas2d_only` — `validator.py` & `player.js` reject `kind: '3d'` inside `render_mode: "canvas2d_only"`.
2. `M02_blank_black_frame_mp4` — `audit_frame_temporal_liveness` rejects decoded MP4 containing black/flat frames.
3. `M03_static_3s_pan_in_action_shot` — `audit_frame_temporal_liveness` rejects frozen world-space actor pose (`>= 48` frames) even when camera pans.
4. `M04_actor_wardrobe_identity_flip_across_cut` — `audit_character_identity` rejects mid-sequence tunic/wardrobe color mutation against `continuity_ledger.json`.
5. `M05_prop_duplicate_and_angle_teleport` — `audit_continuity_across_cuts` rejects duplicated central bell (`prop_count != 1`) and unmotivated `bellAngle` jump (`> 0.35 rad`).
6. `M06_hand_releases_rope_early` — `audit_hand_prop_contact` rejects grip gap exceeding `tolerance_px` during active rope pull.
7. `M07_planted_foot_slides_on_stairs` — `audit_hand_prop_contact` rejects stance-foot world coordinate drift (`> 0.5px`) during stair climb.
8. `M08_camera_overzoom_out_of_bounds_snap` — `audit_camera_2d_bounds` rejects zoom `> 1.35` or excessive pan/rotation.
9. `M09_incorrect_shot_end_timing` — `audit_continuity_across_cuts` rejects timeline gap or final end `!= 30.0s`.
10. `M10_non_human_goat_claimed_as_human_rig` — `validate_character_model_consistency` rejects non-human `PIP` if `is_human_rig: true`.
11. `M11_tampered_style_lock_digest` — `validate_squire_style_contract` rejects mismatched `canonical_digest`.
12. `M12_forbidden_reused_scroll_motif` — `audit_unique_visual_language` & `validate_squire_style_contract` reject forbidden stock motifs (`urgent_scroll`, `marketplace_chase`, `runaway_cart`, `fountain_catch`).
13. `M13_corrupt_mp4_stream` — `audit_frame_temporal_liveness` rejects truncated/undecodable MP4 bytes.
14. `M14_false_positive_guards_6frame_hold_and_valid_cut_pass` — Verifies that a deliberate 6-frame (`0.25s`) narrative anticipation hold and a valid cut with continuous world contact **remain `PASS`** (no naive "every consecutive frame must differ" false alarm).
