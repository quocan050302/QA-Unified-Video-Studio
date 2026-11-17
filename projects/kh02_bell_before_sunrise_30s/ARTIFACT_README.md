# ARTIFACT_README — `THE BELL THAT RANG TOO EARLY` (KH-02.1 Experimental 30.000s 2D Preview)

See also the full run audit packet in `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/ARTIFACT_README.md`.

- **Local Final 1080p24 MP4 Path**:
  `D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\projects\kh02_bell_before_sunrise_30s\out\KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4`
- **SHA-256**: `2f521d88e1da887bfe0654085230b95257154b6f16411e1aeaa39d8da5a9cf5a` (`9,009,085` bytes)
- **Specs**: `1920x1080`, `24/1 fps`, `720` decoded H.264 frames, `30.000s`, AAC `-14.0 LUFS` / `-1.7 dBTP`
- **Status**: `EXPERIMENTAL_PREVIEW` (`KH02_STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `KH02_EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`)

## Rebuild & Render Commands

```powershell
python tools/export_kh02_bell_film.py --project projects/kh02_bell_before_sunrise_30s --workers 2
node render.mjs --project projects/kh02_bell_before_sunrise_30s --sheet --scale 0.5
python -m pytest tests/kh02_2d -v
```
