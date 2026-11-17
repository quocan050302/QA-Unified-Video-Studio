# KH-03.0.R1 — Automated Validation & Test Matrix (`TEST_MATRIX.md`)

All technical verification recorded below was executed directly after final code and render edits; full machine-readable receipts reside in [`evidence/master_verdict.json`](./evidence/master_verdict.json).

| Gate / Suite | Status | Measured Scope & Observed Result |
|---|---|---|
| `pytest tests/kh03_roman/ -v` | `PASS` | `16 passed in 0.98s` (`test_style_lock.py` + `test_script_beat_director.py`) |
| `G00_BRANCH` | `PASS` | Branch `feat/roman-2d-master`, baseline `8d10b6e...` + `Production@80559d09...` verified ancestors, 3 protected remote refs unchanged |
| `G01_STYLE` | `PASS` | `roman_squire_master.v1` digest `1d3209a7...`, `0` protected file diff bytes, legacy `kh03_roman_last_gap_30s` check exit `0` |
| `G02_2D_ONLY` | `PASS` | `renderMode == canvas2d_only`, `three3dLoaded == false`, `0` network requests to `three`, `0` static 3D hits |
| `G03_STORY_BEATS` | `PASS` | `15` shots covering exact `720` frames (`1.292s..2.833s`, mean `2.000s`, `0` 3x scale repeats) |
| `G04_NARRATION_EDIT_DECOUPLE` | `PASS` | `0` `shot_id` hard coupling in `lines.json`; `1:many = 9`, `many:1 = 8`, `13` mid-sentence cuts, word coverage `1.0`, `tempo = 0.987` |
| `G05_RETENTION_PROXY` | `PASS` | Controlled A/B timeline & same-script strip verified (`mean 3.33s -> 2.00s`); `subjective_retention_verified = false` |
| `G06_MOTION_PHYSICS` | `PASS` | Hook `f0->f8` MAD `19.985`; scroll seal arc `(210,753)->(599,439)->(986,826)`; sandal drain stomp `230px -> 830px`; gate amber slit `0.992 -> 0.003` |
| `G07_CAMERA` | `PASS` | `15` C1/C2 camera beats verified within native `9:16` safe framing |
| `G08_QUALITY` | `PASS` | `1080x1920`, `h264`, `24/1`, `720` frames, `30.000s`, AAC `48kHz stereo`, `-14.0 LUFS`, `-2.6 dBTP`, `non_reuse = True` |
| `G09_DETERMINISM` | `PASS` | `24/24` frames exact SHA-256 parity across forward/reverse/scrambled orders + `shot_plan.json` runtime mutation altered rendered frame `240` |
| `G10_NEGATIVE_MUTATIONS` | `PASS` | `16/16` synthetic & pipeline mutants caught cleanly + `2/2` false-positive guards passing |
| `G11_BACKTEST` | `PASS` | `180/180` synthetic script plans PASS (`1.0`); `20/20` real low-res rendered MP4 clips PASS; `company_180_real_videos = NOT_RUN_MISSING_FIXTURE` |
| `G12_LEGACY_REGRESSION` | `PASS` | Isolated `scripts/run_e2e_regression.py` (`383.52s`): **`VERDICT: FLOW_READY (81/81 REQUIRED PASS)`** |
| `G13_PERFORMANCE_DISK_SAFETY` | `PASS` | 3-repeat serial `[4.078, 4.047, 4.156]s` (med `4.078s`) vs 2w parallel `[3.859, 3.828, 3.891]s` (med `3.859s`), speedup `1.057x` |
| `G14_EDITORIAL_SIGN_OFF` | `HUMAN_REVIEW_PENDING` | `STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING` |
