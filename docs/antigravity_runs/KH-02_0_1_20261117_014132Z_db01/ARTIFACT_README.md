# ARTIFACT_README — `THE BELL THAT RANG TOO EARLY` (KH-02.1 Experimental 30.000s 2D Preview)

- **Project Path**: `projects/kh02_bell_before_sunrise_30s/`
- **Style Profile**: `squire_cinematic_2d.v1` (`f1b22b7606f80d1e37c2f32a4cd97152c5c6765400506caa7a9e1f768f333a75`)
- **Render Mode**: `canvas2d_only` (100% pure Canvas2D; zero Three.js / WebGL 3D / external bitmap images)
- **Editorial Status**: `EXPERIMENTAL_PREVIEW` (`KH02_STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `KH02_EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`)

## 1. Final Video File, Local Retrieval Path & SHA-256 Receipt

Because `.gitignore` intentionally excludes `projects/*/out/` and `projects/*/build/` (and `docs/squire/GIAY-PHEP.txt` restricts public commercial redistribution), the full 1080p MP4 lives directly on the local workstation disk and can also be deterministically regenerated from tracked code at any time:

- **Copyable Local Host File Path**:
  `D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\projects\kh02_bell_before_sunrise_30s\out\KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4`
- **Repository-Relative Path**:
  `projects/kh02_bell_before_sunrise_30s/out/KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4`
- **SHA-256**: `2f521d88e1da887bfe0654085230b95257154b6f16411e1aeaa39d8da5a9cf5a`
- **Size**: `9,009,085` bytes (`8.59 MiB`)
- **Verified Media Stream Specs**:
  - Video: `1920x1080`, `H.264` (`yuv420p`), `24/1 fps`, `30.000s`, **`720` decoded frames** (`0` blank frames)
  - Audio: `AAC` (`48,000 Hz` stereo), `30.000s`, **`-14.0 LUFS`** integrated loudness, **`-1.7 dBTP`** true peak (`<= -1.0 dBTP` ceiling)

## 2. 8-Shot Scene Script & Narration Timing (`0.000s – 30.000s`)

Cast locked in `story/character_bible.json` & `story/continuity_ledger.json`:
- **`TAVI`**: Young, anxious apprentice bell-keeper (madder-red Roman tunic, saffron scarf, brass tower key & pouch)
- **`PIP`**: Mischievous hilltop goat (`quadruped_animal_2d`, `is_human_rig: false`)
- **`LYRA`**: Elder bell-mistress (indigo stola & ochre palla)
- **`MARCUS`** (`CITIZEN_A`): Courtyard neighbor awakened below the tower

| Shot | Window (s) | Frames | Scale / 2D Projection | Spoken Narration (`1.0x` Real TTS) | Visual Action & Continuity Anchor |
| --- | --- | --- | --- | --- | --- |
| `S01` | `0.0 – 3.0` | `0..71` | `CU` (`65mm_shallow_dof_2d`) | *"Before dawn, Pip found the bell rope."* | Immediate `0.5s` hook: `PIP` nudges the loose braided hemp rope in crisp focus while the bronze bell blurs behind via Canvas2D `blurLayer`. |
| `S02` | `3.0 – 6.5` | `72..155` | `MS_TWO_SHOT` (`35mm_two_shot_2d`) | *"Tavi had one rule: wait for sunrise."* | Medium two-shot: `TAVI` hears the rope creak, pupils snap up-right in shock, leans ready to lunge; `PIP` stays at consistent right-side rope coordinate. |
| `S03` | `6.5 – 10.0` | `156..239` | `MCU_LOW_ANGLE` (`28mm_authored_low_angle_2d`) | *"He lunged, but the rope slipped free."* | Artist-authored 2D low-angle close-up: reach -> taut pull (`0.0px` world hand-rope lock) -> slip & open-palm recoil as heavy bell tilts. |
| `S04` | `10.0 – 13.5` | `240..323` | `WS` (`24mm_wide_interior_2d`) | *"One tug set the whole bell tower shaking."* | Wide belfry interior with 5 parallax layers: heavy bronze bell swings on oak yoke as `TAVI` sprints right toward stairwell. |
| `S05` | `13.5 – 17.5` | `324..419` | `MLS_PROFILE` (`35mm_tracking_stairs_2d`) | *"He sprinted up the stairs to catch the clapper."* | Non-looping 6-step ascent up travertine stairs: world-locked planted sandals (`0.0px` drift), trailing saffron scarf & hair follow-through. |
| `S06` | `17.5 – 23.0` | `420..551` | `MS -> ECU` (`internal cut @ 19.30s`) | *"For one breathless second, total silence."* | `S06a`: `TAVI` lunges onto upper catwalk and catches the iron clapper bulb (`18.65s`). `S06b`: Tight close-up holding clapper (`0.0px` grip error), score & bell drop to hush, eyes shift to breathless relief. |
| `S07` | `23.0 – 26.5` | `552..635` | `CU` (`50mm_surprise_closeup_2d`) | *"Then little Pip sneezed."* | Surprise close-up at tower base: golden dust mote tickles `PIP`'s nose -> 2D inhale squash -> explosive sneeze stretch yanking rope (`24.85s`). |
| `S08` | `26.5 – 30.0` | `636..719` | `EWS -> CU` (`fast cut @ 28.35s`) | *"And Rome woke up an hour early."* | Wide hilltop courtyard as bell tolls (`LYRA` throws open shutters, `MARCUS` jumps below), cutting at `28.35s` to `TAVI`'s deadpan disbelief face + blink. |

## 3. Tracked Compact Visual Proofs (Committed in Git)

Located in `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/film_preview_packet/` (and mirrored in `tests/evidence/kh02_20261117_014132Z_db01/`):
- `contact_sheet_8shots.jpg` (`sha256: c8c6b9aba5526134359a424bc013e1019d03c7dd6567ff3783bd18ae73a7d92f`)
- `action_strips/strip_1_hook_nudge.jpg` (`sha256: 7fa0433ed3b08f9ca2cc3d3e54754630b68f99ed7c6b8a32a5dbaa9c4013d7c6`)
- `action_strips/strip_2_rising_climb_and_catch.jpg` (`sha256: 7d5680ed4e9049f5b5ce12a55b389e542edc7e201673f5999e903f89009bb1ea`)
- `action_strips/strip_3_sneeze_and_deadpan_payoff.jpg` (`sha256: 7b92984d158d2f0cc7fc8df6a83de961e61112f3a1d33ff463d8b14e88cf0f7e`)
- `stills_8shots/S01_hook_goat_rope_0.50s.png` .. `stills_8shots/S08_courtyard_and_deadpan_27.40s.png` (8 full-1080p decoded PNG stills)
- `thumbnail_1280.jpg`

## 4. Exact Working CLI Commands to Rebuild & Re-Verify

```powershell
# 1. Rebuild voice narration, procedural SFX/score, and all 8 story/*.json manifests:
python tools/build_kh02_bell_project.py --project projects/kh02_bell_before_sunrise_30s

# 2. Render 30s preview directly via Studio renderer CLI (produces build/preview.mp4) or full silent master:
node render.mjs --project projects/kh02_bell_before_sunrise_30s --from 0 --to 30 --scale 0.5
node render.mjs --project projects/kh02_bell_before_sunrise_30s --workers 2

# 3. Mix audio + calibrate -14 LUFS / <= -1.0 dBTP final MP4 + build editorial packet:
python tools/export_kh02_bell_film.py --project projects/kh02_bell_before_sunrise_30s --workers 2

# 4. Run KH-02 unit + 14-mutant negative test suite:
python -m pytest tests/kh02_2d -v

# 5. Run full bounded-async KH-02.0 + KH-02.1 validation + 81-gate legacy E2E regression:
python scripts/run_kh02_0_1_validation.py
```
