# KH-02.0 + KH-02.1 — Verified Production Baseline Audit (`BASELINE.md`)

- **Run Folder**: `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/`
- **Captured At (UTC)**: `2026-11-17T01:44:22Z`
- **Machine-Readable Receipt**: `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/evidence/baseline_snapshot.json`

## 1. Git Branch Ancestry & Remote SHA Verification (Phase A1–A2)

| Ref / Observation | Recorded SHA | Notes |
| --- | --- | --- |
| `origin/Production` (authoritative base) | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | Exact match with prompt's baseline observation; untouched. |
| `feat/modern-2d-cinematic` initial base | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | Created directly from `origin/Production` via `git switch -c feat/modern-2d-cinematic origin/Production`; upstream unset prior to target push so `Production` can never be pushed accidentally. |
| `origin/fix/Image-Shot` (live remote at fetch) | `c96c4f366b873aa3e81a299ab70a330b4adae5ee` | Historical KH-01 reference branch; drifted forward from prompt's earlier `3e470f87b168727372627d525f9e85e337de449e` observation. Left 100% untouched; zero commits merged, rebased, or cherry-picked. |
| `git merge-base --is-ancestor origin/Production HEAD` | `0` (`true`) | Verified continuously in preflight and post-push checks. |

## 2. Host Hardware, Disk, RAM & Toolchain Preflight

- **OS / Workspace**: Windows (`win32`), `D:/Project_github/QA-Unified-Video-Studio/QA-Unified-Video-Studio`
- **Logical CPUs**: `12`
- **Disk at Preflight**: `54.49 GiB` free / `144.02 GiB` total (`>= 10 GiB` preferred threshold satisfied with >44 GiB margin)
- **RAM at Preflight**: `6.65–10.47 GiB` available / `31.75 GiB` total (`>= 1.0 GiB` post-reserve threshold satisfied)
- **Toolchain**:
  - Node.js `v26.13.1` + Playwright Chromium (`msedge` D3D11 ANGLE GPU channel)
  - Python `3.12.10` + `pytest 9.2.0` + `numpy` + `scipy` + `Pillow`
  - FFmpeg / FFprobe `9.0.2`

## 3. Pre-Edit Syntax & Production Sample Health (Phase A3)

Before any code edit was made on `feat/modern-2d-cinematic`:

1. **JavaScript Syntax Sweep (`node --check`)**: `35 / 35` tracked `.js` / `.mjs` files passed (`0` failures).
2. **Python Syntax Sweep (`py_compile`)**: `25 / 25` tracked `.py` files passed (`0` failures).
3. **Isolated Squire Sample Full Render Check**:
   - Copied `projects/squire-mau` into `.test-runs/kh02_20261117_014132Z_db01/baseline_pre_edit/squire-mau-copy` (never mutating `projects/squire-mau`).
   - Executed `node render.mjs --project <copy> --check --check-mode full --scale 0.25`:
     - Exit code: `0` (`35.6s`)
     - Result: `PASS: 0 loi trong 1552 khung kiem tra (24 shots hop le, che do full).`
4. **Pre-Edit Squire Reference Captures (Reference Only — Never Reused in KH-02 Film)**:
   - `baseline_reference/pre_edit_squire_t_1.20.png` (`sha256: 59e2350a343b054839ee95e7f84f412512189019c9952cfc02f7a4d9142d8bff`)
   - `baseline_reference/pre_edit_squire_t_4.00.png` (`sha256: 854fdc1a1c42252f7f1e83d17a4be07f468aeb2723a5a89a5b2d795164edfb8a`)
   - `baseline_reference/pre_edit_squire_t_15.00.png` (`sha256: 9540210ae688a3c857cc0e0c289fa07a241dac6dd973424987f716d906fa9abd`)
   - `baseline_reference/pre_edit_squire_sheet_01.jpg` (`sha256: a3cd88c202ac45724683baaf99f7ba0e01519c84af04c75437383ae4d8973fd6`)
   - `baseline_reference/pre_edit_squire_stills_01.jpg` (`sha256: ec741e0a3028370554677cf407c29b5b7b0e455351aedfe8ed92f9ba91ab472a`)

## 4. Baseline Visual Audit of Production Squire (`packs/squire/*`)

- **Strengths to Preserve**:
  - Immediately recognizable round caricature head (`R = 19u`, ~`38%` of body height `h`) with warm parchment skin (`#f4ede1`) and dark warm-brown vector ink contour (`OUT = #392a21`).
  - Clean historical readability across Roman/medieval presets (`chara.js`, `world.js`, `army.js`), crisp silhouette staging, and authentic Canvas2D camera/depth layering (`engine/core.js::layer`, `blurLayer`).
- **Baseline Limitations Targeted by KH-02.1 Evolutionary Upgrade**:
  - Tube-stroke limbs (`tube()`) with uniform width and round mitten hands (`hand()`) lacked articulated finger wrap for close-up prop interactions (rope pulls, clapper catches).
  - Single-band flat fills lacked tapered interior cloth folds, secondary scarf/hair follow-through, and dawn key/rim separation.
  - Standing/walking feet used heuristic sinusoidal offsets rather than world-locked planted treads on stairs.
- **License & Provenance Check (`docs/squire/GIAY-PHEP.txt`)**:
  - Personal project license (`sha256: d69ff04603593b76287ada84ca7ab99114fc5424cc924a804338ca8ed3952f98`) forbids redistributing Squire source packs commercially as standalone asset packs. All KH-02 work stays strictly inside this repository's private/personal branch workflow, with `.gitignore` respected and zero third-party copyrighted media added.
