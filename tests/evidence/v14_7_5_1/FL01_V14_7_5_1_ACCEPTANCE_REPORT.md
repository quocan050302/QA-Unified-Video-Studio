# FL-01 / V14.7.5.1 Final Technical Verification & Original 30s Film — Acceptance Report

- **Release**: `V14.7.5.1` (`FL-01`)
- **Work Branch**: `fix/Image-Shot` (Baseline `a0813bd0b7a4428f9563d80e65f6cff6c6ef50a6`)
- **Protected Production SHA**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (`production_unchanged = True`)
- **Validation Run ID**: `v14_7_5_1_val_1794743976`
- **Master Verdict**: **`TECH_VERIFIED_PENDING_EDITORIAL`** (`8/8` Mandatory Technical Gates `PASS`)
- **Human Editorial Gate (`J13`)**: **`EDITORIAL_REVIEW_PENDING`**

## 1. Mandatory Gates (`R1`–`R8` + `J13`)

| Gate | Requirement | Status | Duration |
| :--- | :--- | :--- | :--- |
| `R1` | `NO_UNINTENDED_TELEPORT_AND_FULL_CUT_COVERAGE` | **PASS** | `0.0015s` |
| `R2` | `ACTOR_ID_APPEARANCE_RATIO_POSITION` | **PASS** | `0.0035s` |
| `R3` | `CAMERA_CUT_VALIDITY_AND_BOUNDARY_SAMPLES` | **PASS** | `0.0026s` |
| `R4` | `NARRATION_ACTION_ALIGNMENT_CAUSALITY` | **PASS** | `0.5904s` |
| `R5` | `NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR` | **PASS** | `0.6886s` |
| `R6` | `GEMINI_FALLBACK_PROVENANCE` | **PASS** | `0.8829s` |
| `R7` | `VERIFIED_NEW_30S_MP4_LINEAGE_ORIGINALITY_AND_SHEETS` | **PASS** | `12.9369s` |
| `R8` | `FULL_REGRESSION_BACKTEST_MUTATION_RESOURCE_PRESERVATION` | **PASS** | `0.0091s` |
| `J13` | `EDITORIAL_HUMAN_REVIEW` | **EDITORIAL_REVIEW_PENDING** | `0.0s` |

## 2. Original 30.000s Film: `THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET`

- **Subtitle / Framing**: *A fictional Roman engineering rescue; stylized reconstruction, NOT a documented historical event.*
- **Output MP4**: `projects/fl01_v14_7_5_1_roman_water_gate_preview/out/FL01_V14_7_5_1_ROMAN_WATER_GATE_ORIGINAL_30S_1080P.mp4`
- **Output SHA256**: `62e64088fb0b2d33e9c3382707b3fde9aaca9558c90941e100d4b6f676c7b603`
- **Input Fingerprint (64-hex)**: `e716fa1d938f4fde9f1261dae705be37bdfc423441fd44382981bf2ca054dafd` (`recomputed_input_fingerprint` match = `True`, `receipt_verified = True`, `cache_verified = True`)
- **Exact Frame & Stream Proof**: **`720` decoded frames** (`1920x1080` @ `24.0 fps`, container `30.0s`, video `30.0s`, audio `30.0s`, `h264`/`aac`)
- **Originality Lineage**: `prior_preview_derived_visual_inputs = 0`, `external_raster_images_count = 0`, `military_battlefield_props_count = 0`
- **Voice & Loudness**: `macos_say:Daniel`, `8` beats, **`0.0 ms`** overlap, min tail margin **`1.289s`**, Integrated **`-14.5 LUFS`**, True Peak **`-1.0 dBTP`**

## 3. P0 Verification Gap Closures & Full Regression Summary

- **100% Cut-Boundary Coverage (`07_cut_boundary_coverage.json`)**:
  - *Eagle in the Fog*: **`11/11`** cuts audited (`full_boundary_coverage = True`, diagram transitions `['s05->s06', 's06->s07']`)
  - *The Water Gate*: **`7/7`** cuts audited (`full_boundary_coverage = True`, `8/8` shots `VISUAL_TECH_PASS`)
- **Eagle V14.7.5 Re-Verified Provenance**: `input_fingerprint = b8051914461fc1f1c40a17ef8761c32455a2bfc5cd01f47fa9bf2caa005c6423` (`receipt_verified = True`; historical `tests/evidence/v14_7_5/*` untouched)
- **Resource Safety Telemetry (`02_resource_timeseries.json`)**: Min disk free **`17.739 GiB`** (floor `>= 6.0 GiB`), Min RAM available **`2.205 GiB`** (floor `>= 1.0 GiB`), Peak RSS **`3182.36 MB`**, Orphans **`0`**
- **Full Real E2E Regression (`05_e2e_full_regression.json`)**: Run `20261115_190043` -> **`FLOW_READY`** (`81/81` required gates `PASS`, exit `0`)
- **180-Shot Backtest Truth (`06_backtest_truth.json`)**: Synthetic 180-shot `G5 = PASS`, 20-shot real render `G5b = PASS`, company historical 180-shot `G5c = NOT_AVAILABLE` (`counted_not_available_as_real_replay_pass = False`)
- **Subprocess Mutations & Negative Suite (`04_mutation_negative_real.json`)**: **`6/6`** disposable-subprocess mutants killed + **`15/15`** negative fixtures `PASS`
- **Real Video Shot Repair (`09_shot_repair_video.json`)**: **`PASS`** (`mp4_rebuilt_and_changed = True`, `manual_locked_preserved = True`)
- **Speed Measurements (`13_speed_micro_and_e2e.json`)**:
  - Lightweight QA microbenchmark (`n = 3`): mean serial `0.6875s` vs parallel `0.4142s` (**`1.66x`**, 100% digest match)
  - End-to-end 30s *Water Gate* pipeline (`SMALL_SAMPLE`): cold render total `44.16s` (`render.mjs` `19.177s`), warm cache hit `9.501s`, temporal decode QA `24.142s`, full E2E `351.325s`
- **Historical Preservation & Old Film Versioned Corrections (`15_old_video_corrections_status.json`)**: All `9` preserved artifacts byte-identical (`all_preserved_intact = True`); old film versioned corrections status = **`PASS`**
