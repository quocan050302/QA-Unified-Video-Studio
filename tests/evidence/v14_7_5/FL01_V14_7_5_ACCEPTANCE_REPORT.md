# FL-01 / V14.7.5 Evidence-Driven Production Closure — Acceptance Report

- **Release**: `V14.7.5` (`FL-01`)
- **Work Branch**: `fix/Image-Shot` (Baseline `35f071a29b50327ebfc0ad5bb56f58e6f8278a54`)
- **Protected Production Branch**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (`UNCHANGED`)
- **DAG Run ID**: `v14_7_5_val_1794737666`
- **Technical Verdict**: **TECH_VERIFIED_PENDING_EDITORIAL** (`8/8` Technical Gates `PASS`)
- **Human Editorial Gate (`J13`)**: **`EDITORIAL_REVIEW_PENDING`**

## 1. Mandatory Technical & Human Gates (`R1`–`R8` + `J13`)

| Gate | Requirement | Status |
| :--- | :--- | :--- |
| `R1` | `NO_UNINTENDED_TELEPORT` | **PASS** |
| `R2` | `ACTOR_ID_APPEARANCE_RATIO_POSITION` | **PASS** |
| `R3` | `CAMERA_CUT_VALIDITY` | **PASS** |
| `R4` | `NARRATION_ACTION_ALIGNMENT_CAUSALITY` | **PASS** |
| `R5` | `NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR` | **PASS** |
| `R6` | `GEMINI_FALLBACK_PROVENANCE` | **PASS** |
| `R7` | `VERIFIED_MP4_MEDIA_VISUAL` | **PASS** |
| `R8` | `FULL_REGRESSION_BACKTEST_RESOURCE` | **PASS** |
| `J13` | `EDITORIAL_HUMAN_REVIEW` | **EDITORIAL_REVIEW_PENDING** |

## 2. Brand-New Film: `THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE` (*Illustrative Fictional Reconstruction*)

- **Output MP4**: `projects/fl01_v14_7_5_roman_eagle_in_fog_preview/out/FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4`
- **SHA256**: `5276bb238384541139e59a04d8457d683d39f883abb480a523171da25ae51421`
- **Specs**: `1920x1080` @ `24.0 fps`, `h264` / `aac`, duration **`53.851s`**
- **Audio Loudness**: Integrated **`-14.2 LUFS`**, True Peak **`-1.4 dBTP`**, Mean Volume **`-18.4 dB`**
- **Spoken Narration (`Daniel`)**: `12` beats, **`0.0 ms`** overlap, min tail margin **`0.575s`**, `atempo_used_anywhere = False`
- **Decoded Temporal Visual QA**: **`VISUAL_TECH_PASS`** (`12/12` shots passed, `225` decoded frames inspected)

## 3. Real Validation & Performance Summary

- **Async Bounded DAG**: `8/8` jobs `PASS`, `3` measured concurrent job-pair overlaps (`max_active_workers = 3`)
- **Full E2E Regression (`scripts/run_e2e_regression.py`)**: **`FLOW_READY`** (`81/81` required gates `PASS`, exit `0`)
- **Historical 180-Shot Disclosure**: Synthetic 180-shot stress (`G5`) = `PASS`; company dataset `projects/why_knights_could_actually` = **`NOT_AVAILABLE`** (never counted as real replay `PASS`)
- **Disposable-Subprocess Mutation Suite**: **`4/4`** mutants killed + `15/15` negative fixtures `PASS`
- **Real Video Shot Repair Loop**: **`PASS`** (`FULL_RERENDER_FALLBACK`, rebuilt MP4 SHA256 verified changed, `manual_locked` `s01` preserved, locked defect -> `BLOCKED_MANUAL_REVIEW`)
- **Serial vs Parallel Benchmark (`n = 3`)**: Mean serial `0.7127s` vs parallel `0.4433s` (**`1.608x`** speedup, 100% identical SHA256 digests)
