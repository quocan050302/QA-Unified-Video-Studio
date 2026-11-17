# KH-03.0.R1 — Post-Push Remote Attestation (`POST_PUSH_ATTESTATION.md`)

- **Run ID**: `20261117_080723Z_4ff0`
- **Pushed Branch**: `feat/roman-2d-master` -> `origin/feat/roman-2d-master`
- **Primary Feature Commit**: `925273a6be38e90458adb66cda8ae3ea2a7ceac4` (`feat(kh03.r1): script-driven roman 2d shot director and fresh gate short`)
- **Pre-Edit Baseline Commit**: `8d10b6e81b27632769fbf000487794925c6b0937`
- **Root Production Ancestor**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`

## Verified `git ls-remote origin` State After Push

| Remote Ref | Verified Commit Hash | Expected / Protected State |
|---|---|---|
| `refs/heads/feat/roman-2d-master` | `925273a6be38e90458adb66cda8ae3ea2a7ceac4` | Primary KH-03.0.R1 implementation commit (+ this attestation commit next) |
| `refs/heads/Production` | `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` | Untouched |
| `refs/heads/fix/Image-Shot` | `c96c4f366b873aa3e81a299ab70a330b4adae5ee` | Untouched |
| `refs/heads/feat/modern-2d-cinematic` | `688ec5351cf8fbcdb7740420d81e1bbeac4eb727` | Untouched |

## Primary Rendered MP4 Hash Proof (Local Output, Not Tracked Binary)

- **File**: `projects/kh03_r1_roman_gate_message_30s/out/KH03_R1_ROMAN_GATE_MESSAGE_ORIGINAL_30S_9x16.mp4`
- **SHA-256**: `1747ec31d948faf005ce3eb06f43fe1d3fd2113edbb32ce0dd8f816e1833f176`
- **Size / Format**: `10,626,429` bytes | `1080x1920` (`9:16`) | `24fps` (`720` decoded frames, `30.000s`) | `-14.0 LUFS` / `-2.6 dBTP`
- **Sign-Off Status**: `STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`
