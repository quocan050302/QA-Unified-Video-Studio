# KH-03.0 Pilot Project & Deliverable Guide (`ARTIFACT_README.md`)

## 1. Project Identity & Scope

- **Project Path**: `projects/kh03_roman_last_gap_30s/`
- **Working Title**: *"THE LAST GAP IN THE SHIELD WALL"* (Fictional dramatized Roman training-yard vignette — not an unsourced claim about a specific recorded ancient incident)
- **Locked Master Style**: `roman_squire_master.v1` (`visual_styles/roman_squire_master/v1/style_bible.json`, digest `1d3209a715bdd38a73f11acf5c5e2cb6974a6a1855d470e590eaa934360e1259`)
- **Renderer Contract**: `render_mode = "canvas2d_only"` (`0` Three.js / WebGL 3D loads; `0` external bitmaps in `anh/`; `0` reused KH-01/KH-02/baseline demo assets)
- **Phase Scope Notice**: Implements **KH-03.0 ONLY** (style lock + pilot-scoped 2D motion/camera scaffolding + fresh 30.000s pilot). Generalized phases **KH-03.1..KH-03.6 are NOT implemented**.

## 2. Deliverable 30.000s MP4 (Local Host Artifact)

> **Git / Storage Honesty Note**: Per repository `.gitignore` (`projects/*/out/`), the full `12.40 MB` H.264+AAC MP4 resides on the local host disk rather than inside Git history. Compressed review sheets, action strips, thumbnail, story manifests, and SHA-256 verification receipts ARE tracked in Git.

- **Local Openable Path**:
  `D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\projects\kh03_roman_last_gap_30s\out\KH03_ROMAN_LAST_GAP_ORIGINAL_30S_1080P.mp4`
- **Open in Default Windows Player (PowerShell)**:
  ```powershell
  Start-Process "D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\projects\kh03_roman_last_gap_30s\out\KH03_ROMAN_LAST_GAP_ORIGINAL_30S_1080P.mp4"
  ```
- **Verified Media Specs**:
  - Container / Video: `MP4` (`h264`, `1920x1080`, `24/1 fps`, exact **`720`** decoded frames, **`30.000s`**)
  - Audio: `aac`, `48000 Hz`, stereo (`2 ch`), **`-14.9 LUFS`** integrated loudness, **`-2.7 dBTP`** true peak
  - Byte Size: `12,399,535` bytes
  - SHA-256: `114992fc726b7540d4edc2414419ded9f182fb837292878d1d18796ee544056e`

## 3. Reproducible Rebuild Commands

```powershell
# Rebuild manifests, offline SAPI speech, procedural foley SFX, 1080p24 MP4, and review packet:
python tools/kh03_preview_director.py

# Or run individual pipeline stages:
python tools/validator.py --project projects/kh03_roman_last_gap_30s
node render.mjs --project projects/kh03_roman_last_gap_30s --workers 2
python tools/mix.py --project projects/kh03_roman_last_gap_30s
```

## 4. Directory Map

- `config.json` — `pack: "squire"`, `style_profile: "roman_squire_master.v1"`, `render_mode: "canvas2d_only"`, `fadeIn: 0`, `fadeOut: 0`
- `story/` — `script.txt`, `shots.json`, `storyboard.json`, `roman_master_style_ref.json`, `character_bible.json`, `environment_bible.json`, `props.json`, `continuity_ledger.json`, `camera_beats.json`, `sound_design.json`
- `timeline/` — `lines.json` (9 measured beat lines), `words.json` (67 timed words), local `voice.wav`
- `sfx/` — 7 deterministic procedural 48kHz Roman training-yard foley WAVs (`kh03_*.wav`)
- `scenes/shots/` — `last_gap_pilot.js` (`SH01`..`SH09` pure Canvas2D), `thumb.js`
