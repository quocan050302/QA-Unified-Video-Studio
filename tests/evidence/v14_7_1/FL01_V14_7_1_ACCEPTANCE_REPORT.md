# FL-01 / V14.7.1 ACCEPTANCE REPORT & PROOF AUDIT
**QA-Unified-Video-Studio — Verification Repair, Narration-Grounded Physical Acting & Dual Acceptance Films**
**Date**: 2026-11-14 | **Branch**: `fix/Image-Shot` | **Technical Verdict**: `VISUAL_TECH_PASS` (13/14 Gates Passed, 1 Editorial Review Pending)

---

## 1. Executive Summary & Verification Proof

This release addresses the V14.7.1 verification gaps, enforces fail-closed routing integrity, expands the Squire animation engine with physical construction acting capabilities, and renders a brand-new second acceptance film (**The Bridge They Built Before the Enemy Arrived**), while keeping the V14.7 film (**The Warning Before Dawn**) 100% verified and intact.

| Metric | Target Specification | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Branch** | `fix/Image-Shot` ONLY | `fix/Image-Shot` | **PASS** |
| **Production Baseline Invariant** | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (Verified untouched) | **PASS** |
| **Acceptance Film 1 (Night Watch)** | 45–60s, 1080p, 24fps, H.264/AAC | 53.0s, 1920x1080, 24fps, 0 decode errors, SHA256: `6db2c5...` | **PASS** |
| **Acceptance Film 2 (River Bridge)** | 45–60s, 1080p, 24fps, H.264/AAC | 52.0s, 1920x1080, 24fps, 0 decode errors, SHA256: `4023ae...` | **PASS** |
| **Gemini AI Director Routing** | Fail-closed on missing key in `LIVE_REQUIRED` | CLI exits code 1, rolls back, zero false offline bypass | **PASS** |
| **Physical Construction Acting** | `beam`, `timber`, `plank`, `rope`, `bridge`, `hammer` | Props & poses rendered in canvas/Playwright | **PASS** |
| **Audio Loudness Normalization** | -14.0 LUFS ± 3.5 LUFS Broadcast Target | -14.8 LUFS (Night Watch) / -14.2 LUFS (Bridge Crossing) | **PASS** |
| **Multi-Format Regressions** | Squire 16:9, Squire 9:16, DEM 16:9 | All 3 decoded cleanly with 0 errors | **PASS** |
| **Historical 180-Shot Provenance** | Truthful labeling (no synthetic mislabeled as historical) | `HISTORICAL_180_REAL_REPLAY`: `NOT_AVAILABLE`<br>`SYNTHETIC_180_STRESS`: `PASS` (180/180 compiled) | **PASS** |
| **Technical Verdict** | 13/13 Mandatory Technical Gates PASS | `VISUAL_TECH_PASS` | **PASS** |
| **Editorial Gate** | Human review required | `EDITORIAL_REVIEW_PENDING` | **PENDING** |

---

## 2. Invariant & Repository Lineage Audit

- **Working Branch**: `fix/Image-Shot`
- **Current HEAD Commit**: Verified clean on working branch.
- **Production Baseline SHA**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (Checked via `git ls-remote origin refs/heads/Production` — identical and untouched).
- **Previous Release Artifacts Preserved**:
  - V14.4 MP4: `projects/v14_4_action_demo/out/V14_4_Narrative_Action_Demo_1080p.mp4` (Intact)
  - V14.5 MP4: `projects/v14_5_action_demo/out/V14_5_Universal_Action_Repair_1080p.mp4` (Intact)
  - V14.6 MP4: `projects/v14_6_action_demo/out/V14_6_Visual_Storytelling_Acting_Demo_1080p.mp4` (Intact)
  - V14.7 MP4: `projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4` (Intact)

---

## 3. Dual Acceptance Film Proofs

### Film 1: "THE WARNING BEFORE DAWN — A ROMAN NIGHT WATCH"
- **Project Directory**: `projects/fl01_v14_7_night_warning_preview/`
- **Output MP4**: `projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4`
- **Duration**: 53.0s (10 narrative shots)
- **Resolution**: 1920x1080 @ 24.0 fps
- **Video Codec**: `h264` | **Audio Codec**: `aac` (48kHz stereo)
- **File Size**: 14,085,487 bytes (~14.1 MB)
- **SHA-256**: `6db2c5862917f987c417198a31297a4ba89d007d5d0434d8362eea65837df818`
- **Render Receipt**: `projects/fl01_v14_7_night_warning_preview/build/render_receipt.json`
- **Fingerprint**: `2c52e1b8fa604b5c7295936a084428ae86db3f44b6c6ffb78547d84be46a5b6a`
- **Decode Check**: Clean (0 errors, returncode 0).
- **Launch Command**:
  ```bash
  open projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4
  ```

### Film 2: "THE BRIDGE THEY BUILT BEFORE THE ENEMY ARRIVED"
- **Project Directory**: `projects/fl01_v14_7_1_bridge_before_enemy_preview/`
- **Output MP4**: `projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4`
- **Duration**: 52.0s (10 narrative shots)
- **Resolution**: 1920x1080 @ 24.0 fps
- **Video Codec**: `h264` | **Audio Codec**: `aac` (48kHz stereo)
- **File Size**: 7,235,897 bytes (~7.2 MB)
- **SHA-256**: `4023ae779f5ba7b2ae86946b91ce942468febbdc8fb7ab639b8cd5f1f509b4f8`
- **Render Receipt**: `projects/fl01_v14_7_1_bridge_before_enemy_preview/build/render_receipt.json`
- **Fingerprint**: `14087289152abb416ca74ba71a68d9840ca29a3bc530cfc1a1e20b65e581777d`
- **Decode Check**: Clean (0 errors, returncode 0).
- **Launch Command**:
  ```bash
  open projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4
  ```

---

## 4. Master Acceptance Gates Summary (J0–J13)

| Gate ID | Gate Name | Status | Technical Details & Verification Evidence |
| :--- | :--- | :---: | :--- |
| **J0** | Git Branch & Remote Production Invariant | **PASS** | Branch `fix/Image-Shot`; Remote Production baseline `80559d09...` strictly verified untouched. |
| **J1** | Tooling Preflight & System Isolation | **PASS** | Node `v22.22.3`, Python `3.13.0`, FFmpeg `6.0`, Say TTS (Daniel) verified; `QA_STUDIO_TEST_MODE=1`. |
| **J2** | Gemini Routing Matrix & Fail-Closed Gate | **PASS** | OFFLINE_ONLY, DISABLED, LIVE_REQUIRED, LIVE_WITH_EXPLICIT_FALLBACK resolved; CLI fails closed with exit code 1 when key is missing. |
| **J3** | Schema, Actor Rig & Renderer Contracts | **PASS** | Depth scaling `hScale` (0.70-1.30); tent baseline; army flags array guard; props `beam`, `timber`, `plank`, `rope`, `bridge`; poses `pass_object`, `receive_object`, `equip`, `raise_shield`, `react`, `turn_head`, `hammer`; `river`/`riverbank` background preset. |
| **J4** | Cross-Shot Spatial Continuity & No-Teleport | **PASS** | Audited both preview films across all 20 shot cuts; zero teleport violations (dx < 0.50 for continuous scene actors). |
| **J5** | Truthful Visual QA & Classification | **PASS** | Decoded and audited all shots of Bridge Film; safe framing verified; no clipped heads; negative black-frame test returned `detected=False`; negative undetected actor returned `NOT_VERIFIED`; verdict `VISUAL_TECH_PASS`. |
| **J6** | Spoken Narration & Loudness Balance | **PASS** | Voice tracks + multi-track SFX + dynamic music bed; Night Watch integrated loudness -14.8 LUFS; Bridge Crossing integrated loudness -14.2 LUFS (Target: -14.0 LUFS ± 3.5 LUFS). |
| **J7** | Acceptance Preview Films Integrity | **PASS** | Both MP4s verified: 53.0s and 52.0s; 1920x1080 @ 24fps; H.264/AAC; zero decode corruption. |
| **J8** | Multi-Format Regressions | **PASS** | Squire 16:9 (1920x1080), Squire 9:16 (1080x1920), and DEM 16:9 (1920x1080) inspected and full-decoded with 0 errors. |
| **J9** | Historical Lineage & 180-Shot Stress | **PASS** | Regression suites v14.4 & v14.6 pass; `HISTORICAL_180_REAL_REPLAY`: `NOT_AVAILABLE` (honest provenance); `SYNTHETIC_180_STRESS`: `PASS` (180/180 compiled in 0.007s). |
| **J10** | Resource & Memory Telemetry Guard | **PASS** | Available RAM: 2.3 GB; Free Disk: 20.8 GB; Concurrency mode: `BOUNDED_SERIAL_SAFE` (limit: 1). |
| **J11** | Cryptographic Fingerprint & Receipt | **PASS** | Verified receipts for both films; input fingerprints computed; output sha256 matches actual disk file sha256; status `VERIFIED`. |
| **J12** | Git Workspace Cleanliness & Precommit | **PASS** | `guard_work_branch.py precommit` passed; valid launch receipts generated for both videos. |
| **J13** | Creative Editorial Narrative Gate | **PENDING** | **EDITORIAL_REVIEW_PENDING**: Awaiting human editor signoff on pacing, visual acting, and story beat engagement. |

---

## 5. Contact Sheet & Visual Proof

Contact sheet generated at:
`tests/evidence/v14_7_1/contact_sheet_v14_7_1.png`
Contains sampled high-resolution midpoint frames for all 10 narrative shots of the Bridge Acceptance Film:
- **s01**: Riverbank observation hook (Centurion Marcus).
- **s02**: Engineer consultation on swift river current (Marcus & Servius).
- **s03**: Command decision to bridge the river (Groma sighting & salute).
- **s04**: Tactical survey map (angled trestle piers).
- **s05**: Pile driving cadence (wooden mallets on timber stakes).
- **s06**: River mud near-fall slip danger (Titus & Lucius).
- **s07**: Rope catch recovery & beam bracing (Titus, Servius, Lucius).
- **s08**: Spanning bridge deck planks & iron pin hammering.
- **s09**: Completed bridge defensible position; enemy scouts on ridge.
- **s10**: Roman cohort disciplined march across the completed bridge (Payoff).

---

## 6. Reviewer Launch Instructions

To preview both acceptance films on macOS:
```bash
# Bridge Acceptance Film (52.0s):
open projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4

# Night Watch Acceptance Film (53.0s):
open projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4
```
