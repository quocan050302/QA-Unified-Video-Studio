# KH-03.0.R2 — Baseline & Preflight Snapshot (`BASELINE.md`)

- **Run ID**: `20261117_094557Z_0fd8`
- **Active Target Branch**: `feat/roman-2d-master`
- **Starting Head Commit**: `c0c239e36ed6cb2bf9365d3bd74d6d4bfa5cf0be`
- **Authoritative Root Production Baseline**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`

## 1. Protected Remote Refs Recorded Before Editing (`git ls-remote origin`)

- `refs/heads/Production`: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`
- `refs/heads/fix/Image-Shot`: `c96c4f366b873aa3e81a299ab70a330b4adae5ee`
- `refs/heads/feat/modern-2d-cinematic`: `688ec5351cf8fbcdb7740420d81e1bbeac4eb727`
- `refs/heads/feat/roman-2d-master`: `c0c239e36ed6cb2bf9365d3bd74d6d4bfa5cf0be`

## 2. Host Toolchains & Resource Baseline

- **Python**: `3.12.10` (`Pillow 13.0.0`, `numpy 2.5.4`, `scipy 1.18.1`, `soundfile`) — note `cv2` is absent, using Pillow + numpy + scipy natively.
- **Node / FFmpeg**: `Node v26.13.1`, `ffmpeg 9.0.2-full_build`, `ffprobe`, Edge GPU (`ANGLE D3D11`) via `render.mjs`.
- **Disk / RAM / CPU**: `52.55 GiB` free / `144.02 GiB` total; `11.13 GiB` RAM available / `31.75 GiB` total; `12` logical CPUs.

## 3. Protected File & Read-Only Baseline Checksums (Pre-Edit)

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `visual_styles/roman_squire_master/v1/style_bible.json` | 5,898 | `65cf35ba0c050902df5bf60f0bf08f46a5bd977032b68c61a9a77f57d216186c` |
| `tools/kh03_style_lock.py` | 10,355 | `f01f8c5d842bd84fe4bc2a9be0287ed745d4c457ffce860f8e74acfd30097a29` |
| `engine/core.js` | 13,486 | `a224b1dc69809b63e16544236ed2c37ed6c5ce16f9cdf2c55548a04b3ba40a56` |
| `engine/player.js` | 16,341 | `f7ad898dc78a2f10b3a3b28750db06c78dc5b22ddce43a2a2c4028b6e9ae2261` |
| `engine/three3d.js` | 14,919 | `09884b6fd1a72d6839450345c86a63540b8f076dd38df48b1b1f2f972a1b42b1` |
| `projects/kh03_roman_last_gap_30s/out/...1080P.mp4` | 12,399,535 | `114992fc726b7540d4edc2414419ded9f182fb837292878d1d18796ee544056e` |
| `projects/kh03_r1_roman_gate_message_30s/out/...9x16.mp4` | 10,626,429 | `1747ec31d948faf005ce3eb06f43fe1d3fd2113edbb32ce0dd8f816e1833f176` |
