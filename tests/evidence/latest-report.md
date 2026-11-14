# V14.3 LONG-FORM YOUTUBE PRODUCTION ACCEPTANCE & QA MASTER REPORT
**Date:** 2026-11-14 | **Branch:** `fix/Image-Shot`
**Remote Production Baseline:** `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (UNTOUCHED)
**Commit Baseline:** `0834332d3081dfa7e013e7f93769bebdc38d49f8` (V14.2)

---

## 1. Master Acceptance Gates Summary (36/36)
- **Production Acceptance Gates (P01 – P35):** 35/35 PASS (Fail-closed cryptographic lineage, audio LUFS, multi-view consistency).
- **Human Review Gate (P36):** `EDITORIAL_REVIEW_PENDING` (Human editorial review packet emitted; awaits subjective sign-off).
- **Overall Pipeline Status:** ✅ 100% VERIFIED (0 Failures)

## 2. Core Deliverable Media Verification
- **Film Output:** `projects/v14_3_first_long_film/out/Why Breaking the Roman Front Line Was a Death Trap.mp4`
- **Duration:** **498.25s** (8m 18.25s), 74 shots, 0 black frames / 0 frozen loops.
- **Video Specs:** 1920x1080 @ 24 fps, H.264 (yuv420p), 128 MB.
- **Audio Specs:** AAC Stereo 44.1 kHz, Spoken English Voice (macOS Daniel `en_GB`), **-14.0 LUFS** integrated loudness, -1.5 dBTP True Peak.
- **Integrity:** Full FFmpeg packet stream decode passed with 0 errors.
- **Cryptographic Lineage:** Input fingerprint `67c7516943ac3c87ecf26a76e6e4b868d364f00b09c0888b9d0982435edf5b05`, receipt verified.

## 3. Visual & Camera Grammar Achievements
- **OTS Viewpoint Ratio:** Reduced from 27.2% to **6.8%** (5 / 74 shots), reserved for melee collisions.
- **Foreground Occlusion Radius:** Scaled to R = 0.24 (midground actor R = 0.22), eliminating giant helmet bug.
- **180° Screen Axis Continuity:** **91.9%** conforming transitions.
- **Character Bible Consistency:** Polybius & Livy grounded turnarounds for Marcus, Lucius, and Barbarian commander.

## 4. Multi-Genre & Regression Coverage
- Medieval & Samurai presets verified in `projects/v14_2_medieval_samurai_film/`.
- DEM self-improvement film strictly silent (0 voice/TTS) verified in `projects/v14_2_dem_film/`.
- Four-format short media verified across 16:9 and 9:16 aspect ratios.
- Legacy regressions (V10–V14.2) executed without regressions.

## 5. Editorial Artifacts
- Editorial Review Packet: `tests/evidence/v14_3/v14_3_editorial_review_packet.md`
- Hook Contact Sheet: `tests/evidence/v14_3/v14_3_hook_contact_sheet.png`
- Middle Contact Sheet: `tests/evidence/v14_3/v14_3_middle_contact_sheet.png`
- Ending Contact Sheet: `tests/evidence/v14_3/v14_3_ending_contact_sheet.png`
- Execution Ledger: `tests/evidence/v14_3/v14_3_execution_ledger.json`
