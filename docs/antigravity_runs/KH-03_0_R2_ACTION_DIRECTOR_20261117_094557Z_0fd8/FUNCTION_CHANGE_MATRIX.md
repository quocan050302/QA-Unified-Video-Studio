# FUNCTION CHANGE MATRIX — KH-03.0.R2

Toàn bộ danh mục module, hàm và dòng mã thực tế đã thêm mới hoặc mở rộng có điều kiện (opt-in qua `editorial_mode = "roman_action_director_v2"`, bảo toàn 100% R0/R1 legacy):

## A. Python Compiler, Capability Registry, Perceptual QA & Project Builders

| File | Symbols / Line Ranges | Role in KH-03.0.R2 | Change Type |
|---|---|---|---|
| `tools/kh03_action_registry.py` | `ActionRequirement` (44–49), `ActionSpec` (53–67), `ActionBinding` (71–94), `UnsupportedRomanActionError` (97–137), `build_roman_action_registry` (159–605), `resolve_roman_action` (642–852), `validate_action_bindings` (855–910) | Finite 29-capability registry, causal pre/post state guards, negation/ambiguity/missing-asset fail-closed rejection & canonical SHA-256 digest. | **Added** |
| `tools/kh03_perceptual_qa.py` | `sample_rendered_frames` (36–133), `detect_subject_roi` (136–168), `compute_visual_signatures` (171–205), `measure_shot_novelty` (208–314), `audit_motion_continuity` (317–362), `audit_cinematic_camera` (365–397), `build_perceptual_review_packet` (400–461) | Decoded-pixel perceptual shot QA (subtitle band `y >= 0.615*H` excluded, per-MP4 signature-scoped frame cache, zoom-spam/duplicate/low-motion/cut/border alerts). | **Added** |
| `tools/kh03_script_beat_director.py` | `parse_js_renderer_handlers` (1144–1150), `infer_scene_manifest_v2` (1153–1207), `split_line_clauses_v2` (1228–1243), `extract_semantic_beats_v2` (1246–1364), `split_beat_into_v2_visual_events` (1367–1410), `compose_v2_shot_plan` (1413–1555), `score_v2_pacing_proxies` (1558–1576), `validate_v2_shot_plan_contract` (1579–1677), `compile_v2_editorial_plan` (1680–1762) | Generalized ActionGraph + semantic clause splitter + variable-shot-count frame allocator (zero hardcoded `15` shots / `<=3s` cap). R1 functions lines 62–1076 untouched. | **Extended (opt-in)** |
| `tools/kh03_r2_project_builder.py` | `_synth_r2_original_audio` (95–186), `build_roman_r2_project` (289–496), `render_roman_r2_preview` (515–630) | Deterministic 48kHz audio synthesis + multi-corpus R2 builder & Edge GPU render/LUFS calibrator + Perceptual QA runner. | **Added** |
| `tools/kh03_narration_timeline.py` | `merge_narration_visual_mapping` (329–415) | Propagates `shot_plan.get("editorial_mode", "script_beat_director_v1")` dynamically instead of forcing v1 tag. | **Minor fix** |
| `tools/validator.py` | `validate_project` (26–328; R2 branch lines ~272–319) | Validates `action_graph.json`, `action_bindings.json`, `scene_manifest.json`, `canvas2d_only`, and fail-closed `validate_action_bindings` against JS handlers. | **Extended (opt-in)** |

## B. Production Squire 2D Canvas Modules (`packs/squire/`)

| File | Symbols / Line Ranges | Role in KH-03.0.R2 | Change Type |
|---|---|---|---|
| `packs/squire/roman_master/action_registry.js` | `RENDERER_REGISTRY_VERSION` (35), `ACTION_ID_TO_RENDERER_ID` (38–68), `ROMAN_ACTION_RENDERERS` (300–1082), `validateRomanActionRendererCoverage` (1084–1097), `renderRomanAction2D` (1099–1121) | Complete 29-handler 2D Canvas capability map (`actor_*`, `prop_*`, `world_*`); throws fail-closed `KH03_R2_UNSUPPORTED_RUNTIME_ACTION` on missing/unknown `action_id` (zero guard fallback). | **Added** |
| `packs/squire/roman_master/market_props.js` | `drawRomanLoaf2D` (7–37), `drawSpokedWheel2D` (39–60), `drawBrakePeg2D` (62–114), `drawAmphoraJar2D` (116–136), `drawRomanCart2D` (139–194), `drawStoneBollard2D` (196–212), `drawRopePath2D` (214–236), `drawBakeryOvenAndTray2D` (238–306) | Original 2D cart, wheel spokes, cracking wooden brake peg, bollard, taut/sag rope catenary, masonry hearth, and panis quadratus bread loaf. | **Added** |
| `packs/squire/roman_master/market_env.js` | `drawRomanMarketSlopeBackdrop2D` (11–101), `drawMarketCrowdGroup2D` (104–135), `drawMarketForegroundPass2D` (137–146) | Daylight hillside cobblestone Roman market backdrop, upper sidewalk citizen crowd, foreground speed-line sweep outside subtitle zone. | **Added** |
| `packs/squire/roman_master/holdout_envs.js` | `drawRomanRiverHarbor2D` (13–54), `drawClothVexillum2D` (56–85), `drawRomanForumCourtyard2D` (88–116), `drawStoneSenatorBench2D` (118–130), `drawCeremonialHelmetProp2D` (132–152) | Holdout B (river harbor quay + SPQR vexillum) & Holdout C (forum colonnade courtyard + marble bench + dropped bronze helmet). | **Added** |
| `packs/squire/roman_master/character_state.js` | `resolveArchetypeSpec` (84–124), `drawRomanMasterActor2D` (151–213) | Maps R2 cast (`apprentice_titus`, `baker_lucius`, `centurion_varro`, `signifer_marc`, `senator_cassius`, `forum_messenger`) to locked Squire bases + forwards clothing/hair/crest/toga overrides. | **Extended** |
| `packs/squire/roman_master/editorial_state.js` | `evaluateShotCameraAt` (112–171), `evaluateWorldStateAtV2` (185–240) | Continuous hillslope cart progression, wheel rotation, rope tautness, oven tray state, and v2 impact shake triggers; preserves v1 `evaluateWorldStateAt` untouched. | **Extended** |
| `packs/squire/roman_master/script_shot_renderer.js` | `renderScriptShotFrame` (97–156+) | Branches cleanly on `editorial_mode === 'roman_action_director_v2'` into strict fail-closed `renderRomanAction2D(...)` setting `E.lastShotError`; preserves R1 branch below. | **Extended** |
| `packs/squire/pack.js` | Lines 17–28 & `init()` fetch list (~50–70) | Exports R2 modules and loads JSON manifests identically for `script_beat_director_v1` and `roman_action_director_v2`. | **Extended** |

## C. Verification & Tests

| File | Symbols / Line Ranges | Role | Change Type |
|---|---|---|---|
| `tests/kh03_roman/test_r2_action_director.py` | 13 unit/integration test cases covering registry parity, fail-closed errors, 3-corpus compiles, negative & positive perceptual controls | Automated `pytest` suite (`tests/kh03_roman/`). | **Added** |
| `scripts/run_kh03_r2_validation.py` | `run_dag` (881–957), `gate_g00`..`gate_g17` | Genuine `asyncio` DAG validation suite (G00..G17) + telemetry + ResourceMonitor + isolated legacy E2E. | **Added** |
