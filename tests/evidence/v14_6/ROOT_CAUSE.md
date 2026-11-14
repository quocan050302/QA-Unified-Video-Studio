# ROOT CAUSE ANALYSIS — V14.5 DEFECTS & ARCHITECTURAL GAPS
**Release**: V14.6 Root Cause Map  
**Audited Baseline**: `cab69c97b09ffdc44953db099397246b61e37954` (fix/Image-Shot)  
**Date**: 2026-11-14  
**Author**: Antigravity Technical Director & QA Pipeline Auditor  

---

## 1. Executive Summary
In V14.5, while camera motion keyframes and basic multi-block formation top-downs were introduced, direct video inspection revealed several critical visual defects that prevented human editorial acceptance:
1. **Wallpaper Repetition**: Camera cuts between shots felt like interchangeable wallpaper with identical flat grass and blue sky.
2. **Stiff / Non-Differentiated Character Acting**: Beats labeled `CONTACT`, `BRACE`, `FATIGUE`, `SIGNAL`, or `SHIELD_CLOSE` looked virtually identical to idle standing.
3. **Sparse & Disconnected Ensemble Staging**: Battlefield scenes featured either one isolated fighter, two soldiers with static spacing, or a generic grid with no layered depth progression.
4. **False Green Pass on Framing QA (s06 Clipped Head Flaw)**: Visual QA reported 100% green `safe_framing` despite a character's helmet in shot s06 visibly clipping out of frame top-left, and shots s01/s07 touching the bottom edge.
5. **Microscopic Tactical Labels**: Tactical formation unit labels in the top-down map were 18px without high-contrast badges, rendering them completely unreadable at mobile preview sizes (480px).
6. **Superficial Cross-Genre Generalization**: Unseen test suites passed based on MP4 file existence without validating genre-specific period assets or genuine on-video acting.

Below is the verified root cause map based on direct source code inspection.

---

## 2. Root Cause A: Wallpaper Repetition Across Non-Tactical Shots
### Source Inspection:
In `tools/produce_v14_5_demo.py` (lines 237–241):
```python
shot_def = {
    "id": beat["id"],
    ...
    "args": {
        "view": beat["view"],
        "time": "day",
        "bg": "field",
    },
}
```
In `packs/squire/world.js` (lines 121–180), `bg(g, kind, o)` actually provides rich, cinematic environmental options:
- **Atmospheric Times**: `day`, `golden`, `sunset`, `dusk`, `storm`, `dawn`, `night`.
- **Topographies**: `battlefield`, `mud`, `hills`, `plain`, `field`, `castle`, `trench`.
- **Environmental Props & Accoutrements**: `tents`, `flags`, `trees`, `bushes`, `furrows`, `seed`, `groundY`, `mud`, `patches`, `pebbles`, `flowers`, `path`, `pathColor`, `patchColor`.

### The Defect:
Because `produce_v14_5_demo.py` hardcoded `{"time": "day", "bg": "field"}` without varying `seed`, `time`, `bgOpts`, `tents`, `flags`, or ground textures, `world.js` drew the exact same default clouds at the exact same coordinates, the same smooth grass ground, and the same horizon across every single shot. The battle felt frozen in an artificial sandbox.

### Resolution for V14.6:
Introduce `tools/scene_composition.py` to plan progressive battlefield environment states:
- Early approach: distant encampment tents, light morning haze (`golden`/`day`).
- Impact & clash: trampled ground, furrows, battle dust, standard flags.
- Relief & exhaustion: advancing storm/dusk lighting, deepening shadows, persistent terrain markers ensuring geographic continuity without static wallpaper loops.

---

## 3. Root Cause B: Weak Character Acting & Missing Pose Definitions
### Source Inspection:
In `packs/squire/chara.js`:
1. `POSES` table (lines 527–536):
   - Defined poses: `stand`, `idle`, `guard`, `thrust`, `raise`, `lunge`, `push`, `brace`, `run`, `march`.
   - Missing poses: `contact`, `fatigue`, `impact_recoil`, `signal`, `parry`, `retreat`, `open_lane`.
   - In `soldier()` (lines 1270–1275):
     `const pose = POSES[o.pose] ? o.pose : 'stand';`
     Any beat requesting `fatigue`, `impact_recoil`, or `signal` was silently downgraded to `stand` (`[12, 6, 12, 6]`)!
2. Viewpoint Handlers `drawSoldierProfile` (lines 765–1020) and `drawSoldierThreeQuarter` (lines 1060–1260):
   - In `drawSoldierProfile`:
     ```javascript
     // Shield position was completely hardcoded:
     g.translate(14 * u, -38 * u + br);
     // Near arm was completely hardcoded:
     const armPtsList = [[0, -52 * u], [10 * u, -42 * u], [20 * u, -45 * u]];
     ```
     `o.pose`, `o.armsAng`, `o.lean`, and `o.shieldTilt` were completely ignored!
   - In `drawSoldierThreeQuarter`:
     ```javascript
     // Shield position was completely hardcoded:
     g.translate(-12 * u, -38 * u);
     // Right arm was completely hardcoded:
     const rightA = armPts(14 * u, -52 * u, 1, 45, 55, u, 12 * u);
     ```
     `o.pose` was completely ignored!

### The Defect:
Whenever the camera switched to profile or 3/4 views (which comprised majority of the cinematic action shots), the character rig drew fixed idle arms and a fixed shield, regardless of whether the story beat called for a braced shield collision, battle fatigue, or an officer's horn signal.

### Resolution for V14.6:
1. Extend `POSES` in `packs/squire/chara.js` with distinct joint angles for `brace`, `impact_recoil`, `fatigue`, `signal`, `parry`, `retreat`.
2. Upgrade `drawSoldierProfile` and `drawSoldierThreeQuarter` to compute dynamic arm vectors, torso lean, and shield tilt based on `o.pose`, `o.armsAng`, `o.lean`, and `o.shieldTilt`.
3. Support procedural secondary motion (weight shifts, trembling exhaustion, impact impulse) across all angles.

---

## 4. Root Cause C: Disconnected Battlefield Choreography
### Source Inspection:
In `tools/narrative_action.py` and `tools/produce_v14_5_demo.py`:
- Actor placement was handled by assigning 1 or 2 isolated actor objects per shot in `args.actionActors`.
- Background and midground depth layers (`args.backPeople`, `args.mid`, `args.front`) were largely empty or populated by static uncoordinated figures.
- When an action occurred (e.g. Roman front opening a lane), only two actors shifted position; the surrounding line did not react, giving the impression of an empty field rather than a coordinated manipular maneuver.

### Resolution for V14.6:
1. Multi-actor choreography in `tools/character_acting.py` and `tools/scene_composition.py`:
   - Ensemble shots stage foreground, focal midground, and supporting background actors.
   - Front line withdrawal involves staggered sidesteps from multiple file partners (`front_left`, `front_right`, `flank_guard`).
   - Reserve advance maintains continuous spatial progression without instant popping.

---

## 5. Root Cause D: Inaccurate Framing QA False Green Pass (s06 Clipped Head Flaw)
### Source Inspection:
In `tools/visual_qa_v14_5.py` (lines 72–110):
```python
def detect_actor_bounds_and_center(img_arr: np.ndarray, tpl: str = "scene"):
    ...
    if tpl in ("scene", "army", "close"):
        region_mask = np.zeros_like(actor_mask)
        # BUG: Region mask explicitly discards all pixels in the top 20% and outer 5% of the frame!
        region_mask[int(h * 0.20):int(h * 0.98), int(w * 0.05):int(w * 0.95)] = True
        actor_pixels = actor_mask & region_mask
    ...
    ymin = float(np.min(y_indices)) / h
```
In `audit_visual_project`:
```python
# Pass condition checked ymin >= 0.05 and ymax <= 0.98:
framing_safe = (ymin >= 0.05) and (ymax <= 0.98)
```

### The Defect:
Because `region_mask` sliced out `y < 0.20`, any character whose head clipped the top boundary (`y = 0.00` to `y = 0.15`) had their head pixels excluded *before* calculating `ymin`!
Consequently, `ymin` was computed only from the character's neck/torso inside the 0.20 slice, yielding `ymin ~ 0.20`, which trivially satisfied `ymin >= 0.05`!
Furthermore, the bottom boundary allowed pixels all the way down to `0.98` (2% from bottom), permitting characters in s01/s07 to stand right on the screen edge without failing safe margin checks.

### Resolution for V14.6:
1. Rewrite `detect_actor_bounds_and_center` in `tools/visual_qa_v14_6.py` without artificial interior masking.
2. Introduce multi-subject silhouette & landmark tracking that explicitly samples boundary safety zones:
   - Top safe margin: head apex must not violate `y < 0.04`.
   - Bottom safe margin: feet base must not violate `y > 0.97`.
   - Left/right margins: lateral extremities must not violate `x < 0.03` or `x > 0.97`.
3. Add a negative regression fixture reproducing the s06 clipped-head frame and asserting that `visual_qa_v14_6` strictly flags and rejects it.

---

## 6. Root Cause E: Microscopic Tactical Formation Labels
### Source Inspection:
In `packs/squire/army.js` (lines 130–140):
```javascript
if (b.label) {
    g.save();
    g.font = `bold ${Math.max(12, Math.round(18 * (E.W / 1920)))}px sans-serif`;
    g.textAlign = 'center';
    g.fillStyle = '#ffffff';
    g.shadowColor = '#000000';
    g.shadowBlur = 4;
    g.fillText(String(b.label), 0, -H / 2 - 8);
    g.restore();
}
```

### The Defect:
At 1920x1080, `18px` text is under 1.6% of screen height. When viewed on YouTube mobile or in a 480px width player, 18px scales down to 4.5px, rendering the text illegible. Furthermore, without a high-contrast backing badge, the white text bled into dusty or sandy backgrounds.

### Resolution for V14.6:
1. Increase label font size in `packs/squire/army.js` to `Math.max(28, Math.round(38 * (E.W / 1920)))`.
2. Add rounded dark contrast badges (`rgba(16, 20, 28, 0.88)` with subtle golden/white border) behind tactical labels.
3. Add an automated mobile downscale readability test in `tools/visual_qa_v14_6.py` simulating 480px viewing width.

---

## 7. Root Cause F: Superficial Cross-Genre Generalization
### Source Inspection:
In `tools/run_unseen_tests_v14_5.py`:
- Unseen tests checked whether an MP4 output file existed and was larger than 1000 bytes.
- No direct pixel analysis was performed to verify if Knight scenes actually had bascinets/swords, or if Samurai scenes drew kabutos and katanas, or if DEM remained strictly silent.

### Resolution for V14.6:
Upgrade `tools/run_unseen_tests_v14_6.py`:
- Decode actual frames from rendered clips U1 (Knight), U2 (Samurai), U3 (DEM).
- Assert presence of period-specific color signatures and weapon geometries.
- Assert audio streams: Knight/Samurai retain English narration + sword clank SFX; DEM is strictly silent voice (music/SFX only).
- Enforce fail-closed behavior for unsupported generic genres.

---

## 8. Verification Matrix & Diagnostic Status
| Gap Identified | Source Location | Diagnostic Status | Fix Target Module |
|---|---|---|---|
| A. Wallpaper repetition | `tools/produce_v14_5_demo.py::build_action_storyboard` | Confirmed by code & frames | `tools/scene_composition.py` + `world.js` |
| B. Stiff acting | `packs/squire/chara.js::drawSoldierProfile/ThreeQuarter` | Confirmed by code & frames | `packs/squire/chara.js` + `tools/character_acting.py` |
| C. Multi-actor lack of ensemble | `tools/narrative_action.py::compile_action_choreography_to_shots` | Confirmed by code & frames | `tools/character_acting.py` + `tools/scene_composition.py` |
| D. Framing QA false green | `tools/visual_qa_v14_5.py::detect_actor_bounds_and_center` | Confirmed by code & math | `tools/visual_qa_v14_6.py` |
| E. Microscopic labels | `packs/squire/army.js::topBlock` | Confirmed by code & math | `packs/squire/army.js` + `visual_qa_v14_6.py` |
| F. Shallow cross-genre QA | `tools/run_unseen_tests_v14_5.py` | Confirmed by test structure | `tools/run_unseen_tests_v14_6.py` |

This root cause analysis is grounded directly in verified repository source code and frame measurements.
