# KH-03.0.R1 — Baseline & Preflight Snapshot (`BASELINE.md`)

- **Run ID**: `20261117_080723Z_4ff0`
- **Run Folder**: `docs/antigravity_runs/KH-03_0_R1_SCRIPT_SHOT_20261117_080723Z_4ff0/`
- **Pre-Edit Snapshot JSON**: [`evidence/preflight_r1_baseline.json`](./evidence/preflight_r1_baseline.json)

## 1. Git & Protected Refs (Preflight)

- **Active Target Branch**: `feat/roman-2d-master`
- **Verified Head Commit**: `8d10b6e81b27632769fbf000487794925c6b0937`
- **Root Ancestry (`git merge-base --is-ancestor 80559d09d4b7bb72ee4c5acc6cc846e69abd65d1 HEAD`)**: `0` (descends cleanly from `origin/Production`)
- **Protected Remote Refs Verified Before Editing**:
  - `refs/heads/Production`: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`
  - `refs/heads/fix/Image-Shot`: `c96c4f366b873aa3e81a299ab70a330b4adae5ee`
  - `refs/heads/feat/modern-2d-cinematic`: `688ec5351cf8fbcdb7740420d81e1bbeac4eb727`

## 2. System & Resource Baseline

- **Host OS / CPUs**: Windows 11, `12` logical CPUs
- **Disk (`D:\`)**: `52.96 GiB` free / `144.02 GiB` total (`>= 8.0 GiB` conservative threshold)
- **RAM**: `7.21–7.35 GiB` available / `31.75 GiB` total (`>= 2.0 GiB` conservative threshold)
- **Toolchains**: Python `3.12.10` (`numpy`, `scipy`, `soundfile`), Node `v26.13.1`, FFmpeg/FFprobe `9.0.2`, Playwright + ANGLE D3D11 (`msedge` GPU renderer).
- *Note on `tools/doctor.py`*: Reports `[THIEU] Chromium chay ngam` only because Playwright's standalone headless download is not cached, while `render.mjs` launches system `msedge` GPU rasterization automatically.

## 3. Baseline Evidence of Slow Pacing in Original KH-03.0 Pilot (`projects/kh03_roman_last_gap_30s`)

Inspected actual files & physical MP4 (`12,399,535` bytes, `720` decoded frames, SHA-256 `114992fc726b7540d4edc2414419ded9f182fb837292878d1d18796ee544056e`):

- **1:1 Line-to-Shot Coupling**: `9` narration lines bound `1:1` to `9` shots (`L01->SH01 .. L09->SH09`).
- **Shot Duration Distribution (s)**: `[2.5, 3.0, 3.5, 3.0, 3.0, 3.5, 4.5, 3.5, 3.5]` (`7/9 >= 3.0s`; `mean = 3.333s`; `max = 4.500s` on `SH07`).
- **Measured Speech Pauses `> 0.75s` Between Lines**:
  - `L03 -> L04`: `2.035s` silence tail inside `SH03`
  - `L06 -> L07`: `2.091s` silence tail inside `SH06`
  - `L07 -> L08`: `2.020s` silence tail inside `SH07` (`"Perfect drill. Almost."` occupies only `2.30s` of a `4.50s` shot)
- **Decoded Frame Activity**: `53` low-activity frames (`center ROI MAD < 0.8`), overall center MAD `7.1717`.
- **Same-Pose Roman Identity Truth**: `visual_styles/roman_squire_master/v1/style_bible.json` canonical digest `1d3209a715bdd38a73f11acf5c5e2cb6974a6a1855d470e590eaa934360e1259` locked and preserved.
