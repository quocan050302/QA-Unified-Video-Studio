# KH-02.0 + KH-02.1 — Modules, Projects & Artifacts Kept Exactly As-Is (`KEPT_AS_IS.md`)

Every module, sample project, legacy renderer, UI workflow, and baseline test evidence listed below was preserved **byte-for-byte** from `origin/Production` (`80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`) and verified continuously via SHA-256 comparison against `evidence/baseline_snapshot.json` (`audit_style_baseline_preservation` in `tools/kh02_visual_qa.py`).

## 1. Legacy Optional 3D Engine (Preserved for Legacy Compatibility; Never Loaded by KH-02)

| Path | SHA-256 (`origin/Production` == `HEAD`) | Bytes | Verification |
| --- | --- | --- | --- |
| `engine/three3d.js` | `09884b6fd1a72d6839450345c86a63540b8f076dd38df48b1b1f2f972a1b42b1` | `14,919` | Byte-identical; `job_2d_only_guard` proves `threeUrlsCount == 0` in KH-02 and `three3dLoaded == true` in legacy 3D probe. |

## 2. Core Engine, Audio Synth & Studio Web UI Workflows

| Path | SHA-256 (`origin/Production` == `HEAD`) | Bytes |
| --- | --- | --- |
| `engine/core.js` | `a224b1dc69809b63e16544236ed2c37ed6c5ce16f9cdf2c55548a04b3ba40a56` | `13,486` |
| `engine/fx.js` | `e5dfee4627b1dd7737da8d4a5ae31e9062c3b7687b2862010fa7485a8663e36d` | `14,793` |
| `engine/rig.js` | `7436881c9651f5b15a8ec8b88c1d5ea11e12af0e05999a411e6dca23f82f3113` | `24,632` |
| `engine/ui.js` | `00143779d64d7754657c9dda250f13d7a0e4f39871ffd2f685f7181f8b1e03fa` | `12,687` |
| `engine/canonical_hash.js` | `ff8c8f99cba694b959eeccd5037e04a210dca21fbcdebc47494c6ade1bba4e50` | `6,946` |
| `player.html` | `7c9b6977d80fc01412fc42f5e08ee89c2097d8f0aaab4b30fba1f0cfebf7cf15` | `653` |
| `app.py` | `d1d74b64a79b677ccdf453653e5203f30b0aa302e12686be5c3082cbeae6e59c` | `47,540` |
| `web/index.html` | `3cd63e8f423aa3b8894db939c6fd05b09a9aa9083baab3c86eb96454225fccd2` | `28,446` |
| `audio/build_audio.py` | `69df1c1b15c0466a4094345058959fcd8d150867d5d0880e85eaaf0ef89ed678` | `687` |
| `audio/music.py` | `36650a1bad770d9942f17f8f5e8695a9187c41074cf3e896b42d662e3700f768` | `5,823` |
| `audio/synth.py` | `370f0d6a81e5221c774504ad305378b97fc92d51c31aa065170ca35b222ce6e4` | `11,717` |
| `scripts/resource_guard.py` | `84e1b4e76008fc86f8dc70741d2c3d9ed8a46e7736f93e87628f896f4479dda9` | `10,398` |
| `scripts/tts_helper.py` | `50aca7a95fd782a31820504a18df380b4e95ad7c7086f6869195ce6e2e77a656` | `2,697` |
| `package.json` / `package-lock.json` | `2dae16124faff...` / `001f87a4a368...` | `811` / `7,850` (Zero new npm packages added) |
| `.gitignore` | `ede593820d622187589b46b8d3fd66b6a7fbaea408103e141b765c29e33fe364` | `226` |

## 3. Sibling Visual Packs (`packs/dem/*`, `packs/doodle/*`, Untouched Squire Siblings)

- **All 9 files in `packs/dem/*`**: `art.js`, `audio.py`, `bean.js`, `ink.js`, `pack.js`, `phone.js`, `sets.js`, `templates.js`, `thumb.js` — **100% untouched**.
- **All 8 files in `packs/doodle/*`**: `host.js`, `ink.js`, `map.js`, `pack.js`, `props.js`, `sketch.js`, `templates.js`, `world.js` — **100% untouched**.
- **Untouched Squire Sibling Modules**: `packs/squire/army.js` (`94a4ad49...`), `packs/squire/horse.js` (`184e8647...`), `packs/squire/audio.py` (`64c82d1a...`) — **100% untouched**.
- **Untouched Compiler & Pipeline Tools**: `tools/assign_visuals.py`, `tools/draft_shots.py`, `tools/plan_hook.py`, `tools/plan_audio.py`, `tools/mix.py`, `tools/prep_voice.py`, `tools/common.py`, `tools/battle_choreo.py` — **100% untouched** (default behavior for existing projects never switches to KH-02 without explicit project opt-in).

## 4. Production Original Sample Projects & Historical Evidence

- **`projects/squire-mau/*`**: `config.json`, `scenes/shots/thumb.js`, `story/shots.json`, `timeline/{blocks,lines,transcript,words}` — **100% untouched**.
- **`projects/selfimprove-mau/*`**: `config.json`, `scenes/shots/thumb.js`, `story/shots.json` — **100% untouched**.
- **Tracked Baseline Evidence (`tests/evidence/*`)**: `latest-report.md`, `latest-summary.json`, `proof_g2..g5b.jpg`, and all `v6/`, `v7/`, `v8/`, `v9/`, `v10/` golden reports and contact sheets — **100% untouched** (`git status --porcelain` clean).
- **Pre-existing Local Scratch History**: `.test-runs/kh01_r1_20261116_074000Z` — **preserved intact on disk** (`QA_PRESERVE_TEST_RUNS=1`).
- **Protected Remote Branches**:
  - `origin/Production` (`80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`) — **untouched**.
  - `origin/fix/Image-Shot` (`c96c4f366b873aa3e81a299ab70a330b4adae5ee`) — **untouched**.
