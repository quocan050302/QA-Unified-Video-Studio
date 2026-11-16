# Modern Expressive Editorial 2D (`modern_expressive_2d.v1`)

## Overview
`modern_expressive_2d.v1` locks the **visual craft, line quality, cel-shading structure, facial acting clarity, and multi-plane environmental richness** of QA-Unified-Video-Studio across all content niches while allowing domain-accurate costumes, architecture, props, skin tones, proportions, and color temperatures.

## Reference & Copyright Status
- **Reference Archive Status**: `STYLE_REFERENCE_UNAVAILABLE` (`KH-01_STYLE_REFERENCES_ONLY.zip` was not present on the host machine during KH-01 execution).
- **Strict Non-Reuse Policy**: Zero frames, crops, palettes, characters, or textures are copied from any external video or prior FL-01 previews. All parameters in `style_bible.json` represent original editorial 2D animation rules validated on newly rendered PNG panels and 24fps H.264 MP4 clips.
- **Editorial Gate**: `STYLE_APPROVED` and `EDITORIAL_APPROVED` remain `HUMAN_REVIEW_PENDING` until explicit human inspection.

## Files in This Package
- `style_bible.json` — Machine-validated immutable contract loaded by `tools/visual_style_director.py`.
- `visual_rules.md` — Editorial art-direction rules for line weight, silhouettes, faces, hands, shading, environments, and FX restraint.
- `scene_quality_checklist.md` — Mandatory shot-by-shot visual quality checklist enforced by `tools/visual_style_qa.py` and human review.
- `style_reference_manifest.json` — Provenance and copyright exclusion manifest (SHA-only policy; zero reference rasters in repo).
