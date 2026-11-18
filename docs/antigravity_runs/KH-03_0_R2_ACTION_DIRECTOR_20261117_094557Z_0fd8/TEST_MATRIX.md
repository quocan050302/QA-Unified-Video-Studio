# TEST MATRIX — KH-03.0.R2 (`G00..G17` + Pytest + Legacy E2E)

| Gate | Scope & Method | Measured Evidence | Status |
|---|---|---|---|
| `G00_BRANCH` | Verify current branch `feat/roman-2d-master`, ancestors `c0c239e3...` & `80559d09...`, protected remote refs intact | All 3 protected refs verified unchanged via `git ls-remote origin` | **PASS** |
| `G01_STYLE_AND_BACKWARD_COMPAT` | Verify `style_bible.json` digest (`1d3209a7...`), `0` protected diffs, R0 & R1 `render.mjs --check` | `protected_diff_bytes = 0`, `r0_check_exit = 0`, `r1_check_exit = 0` | **PASS** |
| `G02_CAPABILITY_REGISTRY_AND_2D_RUNTIME` | `29` Python-to-JS 1:1 handler parity, Playwright network audit during `renderFrame` | `missing_js_handlers = []`, `threejs_requests = []`, `runtime_editorial_mode = roman_action_director_v2` | **PASS** |
| `G03_ACTION_GRAPH_CAUSALITY` | Verify causal `action_graph.json` transitions (`peg_snapped->cart_rolling->rope_taut->cart_stopped->loaf_on_helmet`) | `nodes = 16`, `edges = 15`, terminal world state complete | **PASS** |
| `G04_NARRATION_EDIT_DECOUPLING` | Real SAPI WAV packing & bidirectional word/line crosswalk | `word_coverage_ratio = 1.0`, `one_to_many = 8`, `many_to_one = 7`, `mid_sentence_cuts = 12`, `tempo = 1.0606x` | **PASS** |
| `G05_CONTROLLED_AB_COMPARISON` | Same-script/same-asset Arm A (`1:1`, 10 shots, max `3.667s`) vs Arm B (`roman_action_director_v2`, 16 shots, max `3.0s`) | `cut_mad_mean`: `37.3` (A) -> `43.85` (B); panel saved in `preview_packet/ab_comparison_1to1_vs_r2_director.jpg` | **PASS** |
| `G06_PERCEPTUAL_SHOT_QA` | Decoded-pixel QA excluding `y >= 0.615*H` captions on Story A 30s MP4 | `samples_decoded = 112`, `duplicates = []`, `low_motion = []`, `zoom_spam = []`, `suspicious_cuts = []` | **PASS** |
| `G07_PERCEPTUAL_NEGATIVE_CONTROLS` | Synthetic negative controls (`zoom+caption flicker`, `non-adjacent duplicate`) vs positive control via `pytest` | `pytest tests/kh03_roman/test_r2_action_director.py -k perceptual` -> exit `0` | **PASS** |
| `G08_FINAL_MP4_AUDIO_AND_NONREUSE` | `ffprobe`, `ebur128`, non-reuse SHA comparison vs R0 & R1 MP4s | `720` frames, `30.0s`, `15513050` bytes, `-14.0 LUFS`, `-2.0 dBTP`, distinct SHA-256 `03282215f1df...` | **PASS** |
| `G09_DETERMINISM_AND_REBUILD_PARITY` | 24 frames rendered in forward/reverse/scrambled order + plan mutation diff + 2-rebuild JSON SHA match | `mismatches = []`, `runtimePlanChangedFrame240 = true`, `two_rebuild_sha_match = true` | **PASS** |
| `G10_22_NEGATIVE_MUTATIONS` | 10 semantic fail-closed + 10 contract mutants + validator `BLOCKED` + Chromium `--check` runtime reject + 2 FP guards | `22/22` mutants caught, both FP guards true | **PASS** |
| `G11_HOLDOUT_CORPORA_RENDERS` | Independent multi-setting renders (`river_harbor`, `forum_courtyard`) + Perceptual QA | Both MP4s valid (`1953326` & `1875668` bytes), `perceptual_qa_status = PASS` | **PASS** |
| `G12_180_SYNTHETIC_SCRIPTS` | 180 varied scripts across market/harbor/forum with duration 5.5s..30s (`company_180` = `NOT_RUN_MISSING_FIXTURE`) | `180/180` PASS; `company_180_real_videos = NOT_RUN_MISSING_FIXTURE` | **PASS** |
| `G13_REAL20_MULTI_CORPUS_MP4S` | 20 independently built & Edge-GPU-rendered MP4s (`30` decoded frames each, async `Semaphore(2)`) | `20/20` PASS across `3` corpora & `15` distinct action IDs | **PASS** |
| `G14_PYTEST_AND_LEGACY_E2E` | `pytest tests/kh03_roman/` (29 cases) + isolated `scripts/run_e2e_regression.py` (`81/81`) | `pytest = 0` (`29 passed`), `VERDICT: FLOW_READY (81/81 REQUIRED PASS)` | **PASS** |
| `G15_BENCHMARK_1W_VS_2W_AND_RESOURCES` | 3-repeat `1w vs 2w` 6s slice benchmark under active `ResourceMonitor` (`>=6 GiB disk, >=2 GiB RAM`) | `1w median = 5.078s`, `2w median = 4.187s` (`1.213x`), `min_disk = 51.42 GiB`, `min_ram = 8.23 GiB` | **PASS** |
| `G16_ASYNC_DAG_TELEMETRY` | Verify overlapping UTC intervals across `asyncio` DAG jobs | `total_jobs_executed = 32`, `max_concurrent_jobs_observed = 3` | **PASS** |
| `G17_HUMAN_EDITORIAL_AND_STYLE_SIGN_OFF` | Owner visual/comedic sign-off | `style_approved = HUMAN_REVIEW_PENDING`, `editorial_approved = HUMAN_REVIEW_PENDING` | **HUMAN_REVIEW_PENDING** |
