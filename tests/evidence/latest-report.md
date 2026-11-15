# FL-01 / V14.7.3 ROMAN CONTINUITY BENCHMARK REPORT
**QA-Unified-Video-Studio — Truthful Verification, Bounded Parallel Testing & Roman Continuity**  
**Release**: `V14.7.3` | **Date**: `2026-11-15 13:17:54`  
**Working Branch**: `fix/Image-Shot` | **Production Baseline Invariant**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`  
**Technical Verdict**: `TECH_VERIFIED` (8/9 gates passed, 1 Human Editorial Review Pending)  
**Execution Time**: `44.58s`

---

## 1. Executive Summary
V14.7.3 delivers the Roman Continuity Benchmark, completely eliminating "fake PASS" loops in negative fixtures and media inspection. All 14 negative fixtures (including `camera_snap`, `stale_receipt`, `failed_extract`, `silent_audio`, and `empty_map`) are now verified with actual production checkers. A brand-new 52.5-second 1080p acceptance preview demonstrating authentic early Roman manipular rotation tactics (*The Gap in the Roman Line — How the Reserves Turned a Crisis into Order*) has been fully produced, decoded with FFmpeg, and cryptographically verified.

All technical gates (**R1–R8**) strictly **PASSED**. Gate **J13** remains accurately set to **EDITORIAL_REVIEW_PENDING** awaiting human creative signoff.

---

## 2. Roman Continuity Matrix (R1–R8 + J13)

| Gate | Name | Status | Notes |
|:---:|:---|:---:|:---|
| **R1** | NO_UNINTENDED_TELEPORT | ✅ PASS |  |
| **R2** | ACTOR_ID_APPEARANCE_RATIO_POSITION | ✅ PASS |  |
| **R3** | CAMERA_CUT_VALIDITY | ✅ PASS |  |
| **R4** | NARRATION_ACTION_ALIGNMENT | ✅ PASS |  |
| **R5** | NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR | ✅ PASS |  |
| **R6** | GEMINI_FALLBACK_PROVENANCE | ✅ PASS |  |
| **R7** | VERIFIED_MP4_MEDIA_VISUAL | ✅ PASS |  |
| **R8** | FULL_REGRESSION_BACKTEST_RESOURCE | ✅ PASS |  |
| **J13** | Creative Editorial Narrative Gate | ⏳ PENDING |  |

---

## 3. Brand-New Acceptance Film Specifications

- **Title**: *THE GAP IN THE ROMAN LINE — HOW THE RESERVES TURNED A CRISIS INTO ORDER*
- **Subline**: *The Manipular Quincunx Tactics of the Roman Legions (ILLUSTRATIVE RECONSTRUCTION)*
- **Path**: `projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_3_ROMAN_CONTINUITY_FRESH_PREVIEW_1080P.mp4`
- **Duration**: `52.5s` | **Resolution**: `1920x1080 @ 24fps` | **Codec**: `H.264 / AAC`
- **Loudness**: `-14.6 LUFS` (Target: -14.0 LUFS ± 3.5 dB)
- **SHA256**: `111d153d0a37a8e985323074438666b6388d9cddf027bad0fcfadac3a43c28cf`
- **Review Command**:
  ```bash
  open projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_3_ROMAN_CONTINUITY_FRESH_PREVIEW_1080P.mp4
  ```

---

## 4. Key Architectural Deliverables in V14.7.3

1. **Truthful Verification & Negative Fixtures**:
   - `camera_snap` now calls `audit_camera_snap_keyframes` from `tools.cinematic_camera` with real keyframe anomalies.
   - `stale_receipt` calls `validate_cache_hit` with tampered manifests.
   - Comprehensive 14 fixtures: `blank_frame`, `map_false_actor`, `actor_disappearance`, `teleport_mid_shot`, `camera_snap`, `duplicate_held_object`, `wrong_preset`, `bad_cut`, `stale_receipt`, `failed_extract`, `silent_audio`, `empty_map`, `unexpected_pose`, `legitimate_cut`.
2. **Selective Shot Repair Engine (`tools/shot_repair.py`)**:
   - Bounded defect classification, dependency calculation, minimal repair planning, and generated-only patching.
   - Verified on synthetic fixture with manual locks protected.
3. **Async Scheduler & Resource Safety (`scripts/qa_scheduler.py`)**:
   - Dynamic concurrency limits, DAG staging, strict 6.0 GB disk safety floor.

---

## 5. Evidence Artifacts Generated
- **Full Contact Sheet**: `tests/evidence/v14_7_3/contact_sheet_full.png`
- **Hook Contact Sheet**: `tests/evidence/v14_7_3/contact_sheet_hook.png`
- **Action Contact Sheet**: `tests/evidence/v14_7_3/contact_sheet_action.png`
- **Resource Telemetry**: `tests/evidence/v14_7_3/01_resource_telemetry.json`
- **Regression & Backtest**: `tests/evidence/v14_7_3/02_regression_backtest.json`
- **Negative Fixtures**: `tests/evidence/v14_7_3/03_negative_fixtures.json`
- **Temporal Visual QA**: `tests/evidence/v14_7_3/04_temporal_visual_qa.json`
- **Media Provenance**: `tests/evidence/v14_7_3/05_media_provenance.json`
- **Shot Repair Ledger**: `tests/evidence/v14_7_3/06_shot_repair_ledger.json`
- **Gemini Fallback Trace**: `tests/evidence/v14_7_3/07_gemini_fallback_trace_redacted.json`
- **Execution Ledger**: `tests/evidence/v14_7_3/execution_ledger.json`
- **Editorial Packet**: `tests/evidence/v14_7_3/EDITORIAL_REVIEW_PACKET.md`
