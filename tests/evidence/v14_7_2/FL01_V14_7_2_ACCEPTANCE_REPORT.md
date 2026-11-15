# FL-01 / V14.7.2 ACCEPTANCE REPORT
**QA-Unified-Video-Studio — Visual Truth, Temporal QA & Ballista Production Validation**  
**Release**: `V14.7.2` | **Date**: `2026-11-15 11:15:24`  
**Working Branch**: `fix/Image-Shot` | **Production Baseline Invariant**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`  
**Technical Verdict**: `VISUAL_TECH_PASS` (13/14 gates passed, 1 Human Editorial Review Pending)  
**Execution Time**: `30.36s`

---

## 1. Executive Summary
V14.7.2 delivers the complete FL-01 visual truth repair, actor preset resolution architecture, keyframed action physics engine, and a comprehensive temporal visual QA audit engine. In addition, V14.7.2 produces a brand-new third 1080p acceptance preview demonstrating authentic Roman artillery mechanics (*The Wooden Machine That Shook a Battlefield — How a Roman Ballista Worked*), alongside the re-rendered Bridge preview and the original Night Watch preview.

All 13 technical gates (**J0–J12**) strictly **PASSED**. Gate **J13** remains accurately set to **EDITORIAL_REVIEW_PENDING** awaiting human creative signoff.

---

## 2. Master Acceptance Matrix (J0–J13)

| Gate | Name | Status | Notes |
|:---:|:---|:---:|:---|
| **J0** | Git Branch & Remote Production Invariant | ✅ PASS |  |
| **J1** | Tooling Preflight & System Isolation | ✅ PASS |  |
| **J2** | FL-01 Gemini Policy Routing Matrix & Fail-Closed Gate | ✅ PASS |  |
| **J3** | Schema, Actor Rig & Renderer Contracts | ✅ PASS |  |
| **J4** | Cross-Shot Spatial Continuity & No Teleport | ✅ PASS |  |
| **J5** | Truthful Visual QA & Strict Classification | ✅ PASS |  |
| **J6** | Spoken English Narration & Loudness Balance | ✅ PASS |  |
| **J7** | Brand New Acceptance Preview Film | ✅ PASS |  |
| **J8** | Multi-Format Regressions (Squire 16:9, 9:16, DEM) | ✅ PASS |  |
| **J9** | Historical Lineage & Backtest Intactness | ✅ PASS |  |
| **J10** | Resource & Memory Telemetry Guard | ✅ PASS |  |
| **J11** | Cryptographic Fingerprint & Atomic Receipt | ✅ PASS |  |
| **J12** | Git Workspace Cleanliness & Launch Receipt | ✅ PASS |  |
| **J13** | Creative Editorial Narrative Gate | ⏳ PENDING |  |

---

## 3. Triple Acceptance Films Overview & Review Commands

### 1. Brand-New Roman Artillery Preview (V14.7.2)
- **Title**: *THE WOODEN MACHINE THAT SHOOK A BATTLEFIELD — HOW A ROMAN BALLISTA WORKED*
- **Subline**: *The Torsion Artillery of the Roman Legions (ILLUSTRATIVE RECONSTRUCTION)*
- **Path**: `projects/fl01_v14_7_2_ballista_preview/out/FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4`
- **Specs**: 51.5s, 1920x1080 @ 24fps, H.264/AAC, **-14.6 LUFS** (target: -14.0 LUFS ± 3.5 dB)
- **Visual QA**: `VISUAL_TECH_PASS` (10/10 shots passed, 0 safe-framing errors, 0 clipped heads)
- **Temporal Visual QA**: `VISUAL_TECH_PASS` (10/10 shots passed, 0 teleportations, 0 disappearances, 9/9 negative fixtures pass)
- **Narrative & Acting Highlights**:
  - Hook (0–3s): Frontier hill sunrise, heavy wooden ballista silhouette with wind ambiance.
  - Action Beats: Artillerist Lucius and crew ratchet bronze sucula winch; schematic cutaway reveals twisted sinew torsion cords; heavy bodkin iron bolt loaded into slider groove; centurion raises arm and lowers it with vocal fire signal; high-speed bolt arcs across valley; palisade barrier splinters on impact.
- **Review Command**:
  ```bash
  open projects/fl01_v14_7_2_ballista_preview/out/FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4
  ```

### 2. Improved Roman Bridge Preview (V14.7.1 Re-Rendered)
- **Title**: *THE BRIDGE THEY BUILT BEFORE THE ENEMY ARRIVED*
- **Subline**: *How Roman Engineers Could Turn a River Into a Road*
- **Path**: `projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4`
- **Specs**: 52.0s, 1920x1080 @ 24fps, H.264/AAC, **-14.8 LUFS**
- **Improvements**: Marcus and Servius wear authentic armor, transverse crest, and feathers (no generic blue tunics); hammer strikes pile with dynamic arm recoil; timber slip and rope recovery show visible displacement.
- **Review Command**:
  ```bash
  open projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4
  ```

### 3. Roman Night Watch Preview (V14.7 Baseline)
- **Title**: *THE WARNING BEFORE DAWN — A ROMAN NIGHT WATCH*
- **Path**: `projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4`
- **Specs**: 53.0s, 1920x1080 @ 24fps, H.264/AAC, **-15.1 LUFS**
- **Review Command**:
  ```bash
  open projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4
  ```

---

## 4. Key Engineering Deliverables in V14.7.2

1. **Root-Cause Actor Preset & Identity Architecture**:
   - Resolved the "Blue Tunic" bug where unknown presets silently fell back to unarmored peasants.
   - Added canonical presets in `packs/squire/chara.js`: `centurio`, `optio`, `principes`, `veles`, `aquilifer`, `cornicen`, `ballistarius`, `artillerist`, `celtic`.
   - Implemented `resolveActorPreset()` and `validateCastPreset()` across all view renderers (`soldier`, `bust`, `soldierLow`, profile, rear, three-quarter).
   - Added missing `oval` shield builder in `shield()` with safe fallbacks.

2. **Keyframed Prop & Weapon Physics Engine**:
   - Upgraded `packs/squire/templates.js` `prop()` with keyframe interpolation: `from`, `to`, `fromY`, `toY`, `rotFrom`, `rotTo`, `moveAt`, `dur`, `arc`.
   - Implemented parametric vector draw routines for `ballista`, `bolt`, `target_barrier`, and `torsion_diagram`.
   - Added dynamic arm physics for poses: `hammer`, `winch`, `crank`, `aim`, `load`, `fire_signal`, `react`/`recoil`.

3. **Temporal Visual QA Engine (`tools/temporal_visual_qa.py`)**:
   - Adaptive multi-frame temporal sampling (start, mid, end, boundary ±1, ±2 frames, 4-8 fps during dynamic motion).
   - Subject type alignment (`expected_subject == 'diagram'` / `'map'` correctly bypasses false actor detection).
   - Full temporal continuity audit: detects sudden disappearances, teleportations (>0.5 screen width mid-shot), and camera pops.
   - Comprehensive negative fixture suite (9/9 negative tests passed): `blank_frame`, `map_false_actor`, `actor_disappearance`, `teleport_mid_shot`, `camera_snap`, `duplicate_held_object`, `wrong_preset`, `bad_cut`, `stale_receipt`.

4. **Resource & Concurrency Telemetry**:
   - Bounded concurrency execution mode (`BOUNDED_CONCURRENT_SAFE`).
   - RAM available: `3.76 GB`.
   - Disk free: `19.64 GB`.

---

## 5. Evidence Artifacts
- **Ballista Contact Sheet**: `tests/evidence/v14_7_2/contact_sheet_v14_7_2.png`
- **Bridge Improved Contact Sheet**: `tests/evidence/v14_7_2/contact_sheet_bridge_improved.png`
- **Visual QA Report**: `tests/evidence/v14_7_2/06_visual_qa_report.json`
- **Temporal Issues Log**: `tests/evidence/v14_7_2/temporal_issues.json`
- **Resource Telemetry**: `tests/evidence/v14_7_2/resource_telemetry.json`
- **Master Acceptance Report**: `tests/evidence/v14_7_2/00_v14_7_2_acceptance_report.json`
