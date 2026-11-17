# KH-03.0.R1 — Preserved Legacy Assets & Modules (`KEPT_AS_IS.md`)

To preserve backward compatibility across `Production`, `KH-03.0` (`projects/kh03_roman_last_gap_30s`), and legacy E2E regressions, the following files and assets were kept **byte-for-byte unchanged**:

- **Style Lock Authority**: `visual_styles/roman_squire_master/v1/style_bible.json` (canonical SHA-256 digest `1d3209a715bdd38a73f11acf5c5e2cb6974a6a1855d470e590eaa934360e1259`), `tools/kh03_style_lock.py`, `tools/kh03_baseline_comparator.py`, `tools/kh03_reference_audit.py`.
- **Legacy Core Engine & Render Pipeline**: `engine/core.js`, `engine/player.js`, `engine/three3d.js`, `render.mjs`, `tools/mix.py`, `tools/common.py`.
- **Legacy Packs & Existing Projects**: `packs/dem/*`, `packs/doodle/*`, `packs/squire/ink.js`, `packs/squire/world.js`, `packs/squire/army.js`, `packs/squire/horse.js`, `packs/squire/templates.js`, `projects/kh03_roman_last_gap_30s/*`, `projects/squire-mau/*`, `projects/selfimprove-mau/*`.
- **Protected Git Refs**: `origin/Production`, `origin/fix/Image-Shot`, `origin/feat/modern-2d-cinematic`.
- **Existing KH-03.0 Functions**: `compile_roman_training_beats`, `build_roman_preview_project`, `build_roman_audio_timeline`, and `render_roman_preview_30s` in `tools/kh03_preview_director.py`.
