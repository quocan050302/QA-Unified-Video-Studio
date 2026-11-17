# KH-03.0 — Authoritative Production Baseline & Environment Audit (`BASELINE.md`)

- **Run ID**: `KH-03_0_ROMAN_MASTER_20261117_044405Z_4e4f`
- **Captured Before Any Source Edits**: `2026-11-17T04:50:51Z`
- **Machine-Readable Snapshot**: [`evidence/baseline_snapshot.json`](./evidence/baseline_snapshot.json)

## 1. Git Branch & Protected Ref Provenance

| Reference | Verified SHA-1 | Status |
|---|---|---|
| `origin/Production` (Authoritative Source) | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | Matches prompt-authoring SHA; untouched |
| `feat/roman-2d-master` (Initial Parent) | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | Created directly from `origin/Production` (`merge-base --is-ancestor == 0`) |
| `origin/fix/Image-Shot` (Historical Protected) | `c96c4f366b873aa3e81a299ab70a330b4adae5ee` | Untouched; zero code cherry-picked or merged |
| `origin/feat/modern-2d-cinematic` (Historical Protected) | `688ec5351cf8fbcdb7740420d81e1bbeac4eb727` | Untouched; zero KH-02 assets/characters imported |

## 2. Host Hardware & Toolchain Baseline

- **OS**: Windows 11 (`win32`)
- **CPU**: `12` logical cores
- **RAM**: `31.75 GiB` total / `9.24–11.37 GiB` available at preflight
- **Output Drive (`D:\`)**: `144.02 GiB` total / `53.96 GiB` free (`>= 10.0 GiB` conservative floor)
- **Node.js / Chromium**: `v26.13.1` + Playwright `msedge` / Chromium ANGLE Direct3D11 (`Intel UHD Graphics 730`)
- **Python**: `3.12.10` (`pytest 9.2.0`, `numpy 2.5.4`, `scipy 1.18.1`, `Pillow 13.0.0`)
- **FFmpeg / FFprobe**: `9.0.2-full_build-www.gyan.dev`
- **`package-lock.json` SHA-256**: `001f87a4a36843a859f82c07a15dbdef4feeb429ee1094353da1cf464edefabc` (zero npm packages added or modified)
- **Pre-Edit Syntax Sweep**: `35/35` `.js`/`.mjs` passed `node --check`; `26/26` `.py` passed `py_compile`; `142` tracked files SHA-256 snapshotted.

## 3. Pre-Edit Sample Baseline Renders (Isolated Scratch Copies)

| Sample Project | Pack | Validator | Full Frame Sweep | Canonical Visual Hash | Deterministic Repeat Stills (Pass 1 == Pass 2) |
|---|---|---|---|---|---|
| `projects/squire-mau` | `squire` | `PASS` (`24/24` shots) | `1552` frames, `0` errors | `f57afc66562e3e2b80587942fb8e96040e7be658935951d3d2cbde4ad137b932` | `t_1.20.png`: `59e2350a...`<br>`t_4.00.png`: `854fdc1a...`<br>`t_15.00.png`: `9540210a...` |
| `projects/selfimprove-mau` | `dem` | `PASS` (`30/30` shots) | `1968` frames, `0` errors | `47624adbdb523133640160fb9ab3a08763a70ac7e58f0c989ae5ef38b1b8b084` | `t_1.00.png`: `81e722f3...`<br>`t_4.00.png`: `cf4401a1...`<br>`t_10.00.png`: `9cb1d7c0...` |

## 4. Primary Roman Squire Source Module Hashes (Pre-Edit Truth)

- `packs/squire/chara.js`: `8f1bea5cf62e3a7c3b905cd80395d12a18c32313098027fb4a1e9a8f818e913c`
- `packs/squire/ink.js`: `7af6a71ebc237cc23c869846e29077339da02d05761b74e56c9d1f0162236168`
- `packs/squire/world.js`: `9806a14ce877629455407a366034167bbc0c2bc40f2f0398eeef0311f8dc220a`
- `packs/squire/army.js`: `94a4ad492b2ae4a1b85d46ee2b9e9d901400cded07848b44ee3f03d29d1990fd`
- `engine/core.js`: untouched (`0` bytes changed)
- `engine/three3d.js`: untouched (`0` bytes changed; preserved for non-KH03 legacy projects, blocked in KH03 `canvas2d_only`)

## 5. Companion Screenshot Reference Status

- Expected companion filename: `KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY.png`
- Workspace/attachment search result: **`USER_SCREENSHOT_REFERENCE_UNAVAILABLE`** (disclosed in [`visual_styles/roman_squire_master/v1/references/REFERENCE_STATUS.json`](../../../visual_styles/roman_squire_master/v1/references/REFERENCE_STATUS.json)).
- Per Section 03 rules: exact `origin/Production` Squire Roman code (`CAST.hastatus` / `CAST.princeps` in `packs/squire/chara.js`) and pre-edit baseline renders serve as primary style truth. No AI recreation was attempted and no fake pixel comparison against an unattached screenshot is claimed.

## 6. Real Baseline Limitations of Production Squire 2D (Documented Honestly)

1. **Preset Arm Poses vs Shield Grip**: In unmodified Production `chara.js`, poses such as `guard`, `brace`, and `push` apply positive left-shoulder angles (`+35°..+75°`) that swing the left white glove outward into empty space away from the `scutum` when `shield.x` is shifted toward the torso center.
2. **Root Translation vs World-Locked Foot Plant**: Production `soldier()` computes standing/lunge feet purely in actor-local coordinates (`±7.2u`), so translating an actor's root X during a shield-shove without IK foot-plant causes visible sandal sliding on the ground line.
3. **Single-Layer Template Camera**: Default `templates.js::camera()` scales a single flattened group (`sceneBody` with one blurred background + one foreground) rather than multi-plane distance-weighted 2D parallax with explicit stage-axis & world-state cut validation.
4. **Global Default Fade-In/Out**: `engine/player.js` applies `fadeIn = 0.5s` and `fadeOut = 0.8s` unless `fadeIn: 0, fadeOut: 0` is explicitly configured, darkening frame `0` and frame `719` on loopable shorts.
