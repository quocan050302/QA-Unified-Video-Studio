# KH-03.0 — Comprehensive Verification, Backtest & Mutation Matrix (`TEST_MATRIX.md`)

- **Runner**: `scripts/run_kh03_0_validation.py` + `tests/kh03_roman/test_style_lock.py` + `scripts/run_e2e_regression.py`
- **Machine-Readable Summary**: [`evidence/validation_summary.json`](./evidence/validation_summary.json)
- **Strict Honesty Rule**: `NOT_RUN_MISSING_FIXTURE` is reported separately and **never** counted as `PASS`. Human aesthetic/editorial gates remain `HUMAN_REVIEW_PENDING`.

---

## 1. Mandatory KH-03.0 Technical Gates (`13 / 13 PASS`)

| Gate | Status | Key Measured Evidence | Artifact Path |
|---|---|---|---|
| `preflight_guard` | **`PASS`** | Branch `feat/roman-2d-master` descends from `origin/Production@80559d09...`; `53.96 GiB` disk / `9.24 GiB` RAM | [`evidence/preflight_guard.json`](./evidence/preflight_guard.json) |
| `baseline_preservation` | **`PASS`** | `squire-mau` & `selfimprove-mau` canonical visual hashes + 6 rendered PNG stills match pre-edit SHA-256 (`0` pixel diff) | [`evidence/baseline_preservation_check.json`](./evidence/baseline_preservation_check.json) |
| `style_lock_contract` | **`PASS`** | `roman_squire_master.v1` digest `1d3209a7...` verified; `USER_SCREENSHOT_REFERENCE_UNAVAILABLE` disclosed | [`evidence/style_lock_contract.json`](./evidence/style_lock_contract.json) |
| `same_pose_reference_poc` | **`PASS`** | Profile-OFF diff = `0` px; `wide` & `close` Silhouette IoU = `1.000000`; `STYLE_APPROVED = HUMAN_REVIEW_PENDING` | [`style_poc/same_pose_ab_metrics.json`](./style_poc/same_pose_ab_metrics.json) |
| `guard_2d_only` | **`PASS`** | `/engine/three3d.js` loads = `0` across all 9 pilot shots; injected `kind:'3d'` rejected by validator & player; legacy `three3d.js` intact | [`evidence/guard_2d_only.json`](./evidence/guard_2d_only.json) |
| `fresh_preview_build` | **`PASS`** | `0` reused demo hashes across `27` audited files; `9` real offline SAPI lines (`67` words, RMS `0.086518`); `0` external bitmaps | [`evidence/fresh_preview_build_audit.json`](./evidence/fresh_preview_build_audit.json) |
| `render_full_30s` | **`PASS`** | `h264` `1920x1080` `24/1 fps`, **`720`** decoded frames, **`30.000s`**, `aac` `48kHz` `2ch`, **`-14.9 LUFS`**, **`-2.7 dBTP`** | [`evidence/render_full_30s_receipt.json`](./evidence/render_full_30s_receipt.json) |
| `frame_temporal_validation` | **`PASS`** | Streaming decode of all `720` frames: `0` black frames, `0` flat frames, first-0.4s MAD `3.3348`, `0` unapproved static streaks | [`evidence/frame_temporal_validation.json`](./evidence/frame_temporal_validation.json) |
| `camera_and_contact_qa` | **`PASS`** | All `8` shot cuts valid; `289` `SH05` subframes (`96 Hz`): `maxRearFootSkatePx = 0.0`, `maxPlantedFrontSkatePx = 0.0`, `maxShieldGripOffsetPx = 9.396px` | [`evidence/continuity_and_contact_traces.json`](./evidence/continuity_and_contact_traces.json) |
| `negative_mutations` | **`PASS`** | `11/11` `pytest` unit/mutation tests + `4/4` media/resource mutants killed; `2/2` false-positive guards passed | [`evidence/negative_mutations.json`](./evidence/negative_mutations.json) |
| `real_backtests` | **`PASS`** | `180`-shot `SYNTHETIC_PASS` + `20`-shot (`480` decoded frames) real MP4 `REAL_RENDERED_PASS` + `NOT_RUN_MISSING_FIXTURE` (Company-180) | [`evidence/backtests_180syn_20real.json`](./evidence/backtests_180syn_20real.json) |
| `legacy_regression` | **`PASS`** | Isolated `run_e2e_regression.py`: **`81` `PASS`**, **`0` `FAIL`**, **`1` `NOT_RUN_MISSING_FIXTURE`** (`d5_historical_company_180shot`) | [`evidence/legacy_regression_summary.json`](./evidence/legacy_regression_summary.json) |
| `speed_and_reproducibility` | **`PASS`** | `18/18` frames identical PNG SHA-256 across `forward`/`reverse`/`seeded_random`; 3-repeat QA speedup **`2.057x`** with `100%` digest parity | [`evidence/speed_and_reproducibility.json`](./evidence/speed_and_reproducibility.json) |

---

## 2. Negative Mutation & False-Positive Guard Matrix

| Mutant / Guard ID | Injected Defect or Valid Edge Case | Detector | Expected | Actual |
|---|---|---|---|---|
| `M01` | Tampered style bible digest / head-radius invariant | `validate_roman_style_contract` | Kill | **KILLED** |
| `M02` | Palette contour drift (`OUT: #392a21 -> #000000`) & bare-hair swap | `validate_roman_style_contract` | Kill | **KILLED** |
| `M03` | Fallback attempt to `modern2d_cinematic.v1` / `tavi` | `load_roman_master_style` & `resolve_roman_variant` | Kill | **KILLED** |
| `M04` | Recycled `squire-mau` file hash, `anh/` bitmap, or `tavi`/`bell` token | `assert_no_reused_demo_assets` | Kill | **KILLED** |
| `M05` | Injected `kind: "3d"` in `canvas2d_only` project | `validate_project` + `player.js` + `render.mjs` | Kill | **KILLED** |
| `M06` | Missing registered scene ID & overlapping timestamps | `validate_project` | Kill | **KILLED** |
| `M07` | Detached shield grip (`85px`), broken spear hand (`48px`), foot skate (`8.5px`), actor teleport (`240px`) | `validateRomanMasterRigAnchors` | Kill | **KILLED** |
| `M08` | Unmotivated gap-state flip, 180° stage-axis break & 3x repetitive framing | `validateRomanCameraCut` | Kill | **KILLED** |
| `M09` | Silhouette/palette swap in Same-Pose A/B image pair | `compare_roman_identity_geometry` | Kill | **KILLED** |
| `M10` | Truncated 5.0s (`120`-frame) MP4 | `inspect_mp4_temporal_stream` | Kill | **KILLED** |
| `M11` | Frozen >2.0s (`72`-frame) static image pan without hold justification | `inspect_mp4_temporal_stream` | Kill | **KILLED** |
| `M12` | Silent zero-amplitude narration `voice.wav` | Voice RMS speech detector | Kill | **KILLED** |
| `M13` | Disposable disk-threshold breach (`min_disk_gb=999999`) | `ResourceMonitor` cancels registered child PID only | Kill | **KILLED** |
| `FP01` | Valid 8-frame dramatic hold (`SH07` instructor eye-narrowing `[2.25..2.58s]`) | `romanActorAt` + `inspect_mp4_temporal_stream` | **PASS** | **PASSED (0 false alarm)** |
| `FP02` | Valid motivated cinematic scale jump (`wide_geography` -> `macro_physics_insert`) | `validateRomanCameraCut` | **PASS** | **PASSED (0 false alarm)** |

---

## 3. Backtest & Legacy Regression Breakdown (Synthetic vs Real vs Missing Fixture)

| Suite / Category | Classification | Exact Result | Notes |
|---|---|---|---|
| KH-03.0 Unit & Mutation Pytest (`tests/kh03_roman/test_style_lock.py`) | `UNIT_AND_MUTATION` | `11 PASS / 0 FAIL` | `0.57s` execution |
| 180-Shot Squire/Roman Multi-Template Stress | **`SYNTHETIC_PASS`** | `180/180` renderable shots | Validated in isolated scratch (`180.0s` timeline) |
| 20-Shot Roman Multi-Scene Real MP4 Backtest | **`REAL_RENDERED_PASS`** | `20` shots, `480` decoded H.264+AAC frames | Real MP4 SHA-256 `31b7336913f09112ad1cc60da3b29bc83eaa677645ae2885c8f98b539b9792b0` (`4,042,791` bytes) |
| Legacy E2E Suite (`scripts/run_e2e_regression.py` — Squire 16:9/9:16, DEM 16:9/9:16, V6–V10) | **`REAL_RENDERED_PASS`** | **`81 PASS / 0 FAIL`** | Isolated scratch & evidence; `tests/evidence/latest-*` untouched |
| External Historical Company 180-Shot Archive (`d5_historical_company_180shot`) | **`NOT_RUN_MISSING_FIXTURE`** | `1 NOT_RUN` (`PATH_MISSING`) | External archive absent from `origin/Production`; **not** counted as `PASS` |
