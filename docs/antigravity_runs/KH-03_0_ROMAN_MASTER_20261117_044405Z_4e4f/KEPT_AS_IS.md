# KH-03.0 — Fixed Preservation Matrix (`KEPT_AS_IS.md`)

Every module, sample fixture, pack, license, and historical branch listed below was verified byte-for-byte intact or default-pixel-identical against `origin/Production` (`80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`).

## 1. Protected Branches & Historical Run Artifacts

| Protected Target | Verification |
|---|---|
| `origin/Production` | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` — untouched before & after execution |
| `origin/fix/Image-Shot` | `c96c4f366b873aa3e81a299ab70a330b4adae5ee` — untouched; zero merges/cherry-picks |
| `origin/feat/modern-2d-cinematic` | `688ec5351cf8fbcdb7740420d81e1bbeac4eb727` — untouched; zero Tavi/Lyra/goat/bell imports |
| `.test-runs/kh01_*`, `.test-runs/kh02_*`, prior runs | Preserved via `QA_PRESERVE_TEST_RUNS=1`; zero blanket `clean_old_runs()` deletion |
| `tests/evidence/latest-*` & `v6..v10` golden evidence | `git status --porcelain -- tests/evidence` clean outside isolated `tests/evidence/kh03_0_20261117_044405Z_4e4f/` |

## 2. Byte-Identical Core, Pack, Audio, Sample & License Files

Verified via SHA-256 parity against `evidence/baseline_snapshot.json`:

- **Core 2D & Legacy 3D Engine**:
  - `engine/core.js` — byte-for-byte unchanged (`E`, `ease`, `kf`, `rng`, `noise`, `layer`, `blurLayer`, `registerShot`, `registerTemplate`, `talkAmount`).
  - `engine/three3d.js` — byte-for-byte unchanged for legacy non-KH03 projects (strictly blocked and `0` runtime loads in KH-03 `canvas2d_only`).
- **Self-Improvement (`packs/dem/*`) & Map/Doodle (`packs/doodle/*`) Packs**:
  - `packs/dem/pack.js`, `packs/dem/templates.js`, `packs/dem/audio.py` — byte-for-byte unchanged; `selfimprove-mau` stills match pre-edit SHA-256 identically.
  - `packs/doodle/pack.js`, `packs/doodle/draw.js`, `packs/doodle/char.js`, `packs/doodle/map.js`, `packs/doodle/objects.js` — byte-for-byte unchanged.
- **Squire Unmodified Submodules**:
  - `packs/squire/army.js`, `packs/squire/horse.js`, `packs/squire/audio.py` — byte-for-byte unchanged.
- **Audio & Story Compiler Pipeline**:
  - `audio/synth.py`, `audio/music.py`, `audio/build_audio.py`, `tools/mix.py`, `tools/prep_voice.py`, `tools/plan_audio.py`, `tools/draft_shots.py`, `tools/assign_visuals.py`, `tools/plan_hook.py`, `scripts/resource_guard.py`, `scripts/tts_helper.py`, `app.py` — byte-for-byte unchanged.
- **Sample Projects & Documentation/Licenses**:
  - `projects/squire-mau/**` and `projects/selfimprove-mau/**` — byte-for-byte unchanged (`squire-mau` post-edit stills at `1.2s, 4.0s, 15.0s` produce `0` pixel diff and identical PNG SHA-256s).
  - `docs/squire/**` and `docs/self-improvement/**` (including `GIAY-PHEP.txt` licenses and skill references) — byte-for-byte unchanged.

## 3. Original Squire Roman Identity Preserved as Long-Term Master Style

- **Character Family**: `CAST.hastatus` / `CAST.princeps` / `CAST.legionary` from Production `packs/squire/chara.js` — round `#f4ede1` ivory head (`R = 19u`, `38%` of body height), minimal `#392a21` warm-brown contour eyes/mouth, warm-gold `#d3a24e` Montefortino helmet with 3 feathers, `#c9473a` red Roman tunic + bronze pectoral plate, `#ffffff` round white gloves, tall red `scutum` (`#e7b04a` gold rim + steel boss), and wood/steel spear.
- **Profile-OFF Pixel Lock**: Same-pose `wide` and `close` renders with `romanMasterPolish` disabled yield **`0` differing pixels** (`0 / 2,073,600`) against an immutable `git show origin/Production:packs/squire/*` checkout.
