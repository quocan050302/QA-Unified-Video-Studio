# KH-01 Modern Expressive 2D — Universal Style Lock, Asset Factories, Acting, Multi-Angle, Multi-Niche & Original 30s Film

## 1. Objective & Scope
Execute **KH-01 / FL-01 Visual Quality First** on branch `fix/Image-Shot` while preserving FL-01's unified architecture (`Story Director -> Visual Style Director + Character/Environment Factories -> MotionPlan + Canvas/Rigby2D + selective Claude FX -> Cinematic Camera -> Squire/DEM Chromium render.mjs -> FFmpeg -> Fail-Closed QA`), reconciling P0 V14.7.6 QA contradictions, proving multi-niche generalization across 4 domains, and delivering the brand-new 30.000s (720-frame) 1080p24 comedic animated short ***"ROME'S MOST URGENT SCROLL"***.

## 2. Live Git Baseline & Branch Invariants
- **Target Branch**: `fix/Image-Shot`
- **Baseline HEAD at Start**: `f2fbea4cb6ec50c6655b08f24177869dbc961dd1` (`Fix code`)
- **`origin/Production` Invariant SHA**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (verified untouched before and after run; see `tests/evidence/kh01_20261116_015100Z/01_git_preservation.json` and `21_postpush_git_attestation.json`)

## 3. Unified Pipeline Flow (Old vs Additive KH-01)
- **Legacy Projects (Unchanged Default)**: `input script -> StoryContext (roman/field default) -> assign_visuals -> Squire/DEM templates -> render.mjs -> FFmpeg`.
- **Opt-In Modern Expressive 2D (`styleId: "modern_expressive_2d.v1"`)**: `input script -> infer_niche_from_script + StoryContext -> resolve_visual_style + build_shot_art_direction -> CharacterFactory (SVG/PNG + 1024x1024 Rigby2D atlas) + EnvironmentFactory -> MotionPlan (unplanted APPROACH + planted IK + shared contact) -> link_camera_to_asset_views -> universal modern_expressive_2d renderer -> render.mjs -> measured Windows SAPI TTS + Foley (-14 LUFS) -> temporal_visual_qa + visual_style_qa -> editorial packet`.

## 4. Changed vs `KEPT AS IS` Modules
- Full per-function table: [`FUNCTION_CHANGE_MATRIX.md`](./FUNCTION_CHANGE_MATRIX.md)
- Unchanged modules & preserved historical evidence: [`KEPT_AS_IS.md`](./KEPT_AS_IS.md) (`app.py`, `render.mjs`, `packs/squire/templates.js`, `packs/squire/chara.js`, `packs/dem/pack.js`, `scripts/qa_scheduler.py`, `scripts/run_e2e_regression.py`, `scripts/production_fingerprint.py`, `tests/evidence/v14_7_5*`, `tests/evidence/v14_7_6/*`).

## 5. Visual Design Decisions, Reference Policy & Honest Limitations
- **Reference Availability & Copyright Policy**: `KH-01_STYLE_REFERENCES_ONLY.zip` was not present on this host (`STYLE_REFERENCE_UNAVAILABLE`; see [`STYLE_REFERENCE_MANIFEST.json`](./STYLE_REFERENCE_MANIFEST.json)). Zero reference images, crops, or legacy preview frames were used or committed.
- **Authored Style Rules (`visual_styles/modern_expressive_2d/v1/`)**: Clean bold variable-weight espresso-ink outlines, 3-band cel shading (base + cool shadow + warm key rim), non-homogeneous character archetypes, 4 physical views (`front`, `three_quarter`, `profile`, `rear_three_quarter`), 6 genuinely distinct facial expressions, 4 depth planes with foreground occlusion, and strict FX discipline (zero neon RGB fringes or halftone overlays on scene shots).
- **Subjective / Editorial Disclosure**: While deterministic style checks pass, programmatic SVG/Canvas cel-illustration is simpler in organic cloth brushwork than hand-painted feature animation. Neither `100% style match` nor audience retention gains are claimed; `STYLE_APPROVED` and `EDITORIAL_APPROVED` remain **`HUMAN_REVIEW_PENDING`**.

## 6. Test Matrix, Commands & Measured Resources
- **Validation Orchestrator**: `python scripts/run_kh01_validation.py`
- **Unit & Motion Suites**: `python -m pytest tests/kh01_modern_2d/ tests/motion_v14_7_6/ -q` (`28 passed`)
- **Full Legacy E2E Regression**: `python scripts/run_e2e_regression.py --max-concurrency 1` -> **`FLOW_READY`** (`81/81` required gates passed; `G5` synthetic 180-shot `PASS`, `G5b` real 20-shot `PASS`, `G5c` absent historical fixture recorded `NOT_AVAILABLE` and never counted as `PASS`).
- **Measured Resource Floors**: Min free disk `54.207 GiB` (`>= 6.0 GiB`), min available RAM `6.544 GiB` (`>= 1.0 GiB`), peak process-tree RSS `8387.45 MiB`, orphan child processes `0`.
- **Serial vs Bounded-Parallel QA Speed (`n=3`)**: `1.6019s` serial vs `0.612s` parallel (`2.617x` QA-only speedup, identical SHA-256s).
- Full gate index: [`TEST_RUN_INDEX.md`](./TEST_RUN_INDEX.md) | Acceptance report: [`../../tests/evidence/kh01_20261116_015100Z/KH01_ACCEPTANCE_REPORT.md`](../../tests/evidence/kh01_20261116_015100Z/KH01_ACCEPTANCE_REPORT.md)

## 7. Flagship 30s Film Artifact & Human Review Status
- **Local MP4 Path** (gitignored per repo policy): `projects/kh01_modern_2d_roman_urgent_scroll_30s/out/KH01_ROMES_MOST_URGENT_SCROLL_ORIGINAL_30S_1080P.mp4`
- **SHA-256**: `f205dd30d6146bef279491feb24ede1f872d30632d1c96b6af7234e5b9c939f0` | **Size**: `10481468` bytes | **Format**: H.264 + AAC, `1920x1080`, `24fps`, exact `720` decoded frames (`30.000s`), `-15.4 LUFS` / `-1.4 dBTP`.
- **Technical Verdict**: **`KH01_TECH_PASS_EDITORIAL_PENDING`** | **`STYLE_APPROVED`**: **`HUMAN_REVIEW_PENDING`** | **`EDITORIAL_APPROVED`**: **`HUMAN_REVIEW_PENDING`**
- **Post-Push Remote Attestation**: Recorded in `tests/evidence/kh01_20261116_015100Z/21_postpush_git_attestation.json`.
