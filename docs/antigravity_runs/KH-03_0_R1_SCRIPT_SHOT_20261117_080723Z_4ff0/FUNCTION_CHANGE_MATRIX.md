# KH-03.0.R1 — Exact Implemented Function & Ownership Matrix (`FUNCTION_CHANGE_MATRIX.md`)

> Verified directly against implemented source modules on `feat/roman-2d-master`.

## 1. New R1 Modules (Zero Impact When Opt-In Flag Is Absent)

| Module | Functions | Responsibility & Scope |
|---|---|---|
| `tools/kh03_script_beat_director.py` | `normalize_script_lines`, `measure_voice_timeline`, `extract_semantic_beats`, `split_beat_into_visual_events`, `compose_shot_plan`, `build_line_shot_crosswalk`, `schedule_editorial_camera`, `score_pacing_proxies`, `validate_shot_plan_contract` | Reusable, deterministic script-driven beat/shot compiler supporting `1:many`, `many:1`, mid-sentence cuts without audio truncation, negation handling, world-state continuity, native `9:16` safe framing, and honest editorial pacing proxies (`subjective_retention_verified = false`, `editorial_approved = HUMAN_REVIEW_PENDING`). |
| `tools/kh03_narration_timeline.py` | `synthesize_or_import_narration`, `align_words_and_lines`, `pack_narration_into_30s`, `merge_narration_visual_mapping` | Independent audio/narration timeline builder producing continuous measured `voice.wav`, `lines.json`, `words.json`, and `narration_timeline.json` with hard `<= 1.15x` stretch guard (`<= 1.10x` preferred). |
| `tools/kh03_r1_project_builder.py` | `build_roman_script_driven_project`, `render_roman_r1_preview` | Deterministic end-to-end R1 compiler, procedural dusk city-gate SFX/underscore synthesizer, native `1080x1920 @ 24fps` render orchestrator, and preview packet builder. |
| `packs/squire/roman_master/gate_city_env.js` | `drawRomanCityApproachDusk2D`, `drawRomanGateWinch2D`, `drawRomanCobbleAlley2D`, `drawRomanGuardThreshold2D`, `drawRomanGateLeaves2D`, `drawStoneDrainGrate2D`, `drawSealedRomanScroll2D`, `drawRomanSandalMacro2D` | Brand-new procedural 2D Roman dusk city gate, winch tower, cobble street with curbstone, interior drain threshold, oak gate leaves, and legible `KEEP THE GATE OPEN` parchment scroll props using locked `#392a21` Squire ink. |
| `packs/squire/roman_master/editorial_state.js` | `resolveShotAtFrame`, `evaluateWorldStateAt`, `evaluateShotCameraAt`, `withEditorialCamera` | Opt-in runtime evaluator computing monotonic oak gate closure, iron bolt slam, scroll mud/seal continuity, and C2-smoothed camera trajectories strictly from `shot_plan.json` & `camera_beats.json`. |
| `packs/squire/roman_master/script_shot_renderer.js` | `renderScriptShotFrame` | Opt-in 100% Canvas2D runtime renderer driven dynamically by `E.kh03.shotPlan` (`sub_action` / `location_id` / `framing_scale`) and locked Squire Roman actor evaluation (`romanActorAt`, `drawRomanMasterActor2D`). |

## 2. Opt-In Additive Hooks on Existing Files (Legacy Default Behavior Preserved)

| File & Function | Old Role (Preserved 100%) | Opt-In R1 Extension |
|---|---|---|
| `packs/squire/chara.js::torso`, `soldier` | Original Squire body, clothing & return value | Optional `o.courierSatchel` cross-strap + pouch (`0` impact when omitted) and additional `leftHand: L.H` return property. |
| `packs/squire/roman_master/motion.js` & `character_state.js` | Locked Squire training-yard archetypes & IK solver | Optional `hipBobU`, `leftKneeBend`, `rightKneeBend`, `courierSatchel`, `shoeMode`, and locked cast aliases (`courier_marcus` -> `rookie_hastatus`, `gate_guard_gaius` -> `instructor_princeps`, `watchman_sec` -> `veteran_neighbor_legionary`). |
| `packs/squire/roman_master/environment.js` | Training yard, castra gate/ramp, dawn sky, cohort & shield wall | Re-exports `./gate_city_env.js` without changing any legacy function. |
| `packs/squire/pack.js::init` & exports | Loads `E.kh03` manifests for `roman_squire_master.v1` | Fetches `shot_plan.json`, `beats.json`, `shot_to_line_map.json`, `narration_timeline.json`, `pacing_report.json` when `E.cfg.editorial_mode === 'script_beat_director_v1'` and re-exports `editorial_state.js` & `script_shot_renderer.js`. |
| `tools/validator.py::validate_project` | Validates `shots.json`, scenes, `canvas2d_only`, `squire` voice | When `cfg.editorial_mode == 'script_beat_director_v1'`, validates contiguous `shot_plan.json` `[0..total_frames-1]` coverage and `shot_to_line_map.json` word coverage (`>= 0.999`). |
| `tools/kh03_preview_director.py` | Owns all KH-03.0 9-shot functions untouched | Re-exports opt-in `build_roman_script_driven_project` and `render_roman_r1_preview` at bottom of module. |
