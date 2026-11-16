# KH-01 Acceptance Report — Modern Expressive 2D & *"ROME'S MOST URGENT SCROLL"*

- **Run ID**: `kh01_20261116_015100Z`
- **Branch**: `fix/Image-Shot` (Baseline HEAD `f2fbea4cb6ec50c6655b08f24177869dbc961dd1`; `origin/Production` invariant `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`)
- **Technical Verdict**: **`KH01_TECH_PASS_EDITORIAL_PENDING`** (`20/20` mandatory gates passed)
- **Human Signoff Gates**: `STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`
- **Reference Zip Status**: `STYLE_REFERENCE_UNAVAILABLE` (zero reference pixels used or committed; zero similarity % claimed)

## Visual Quality & Motion Gates
- **`VQ01_STYLE_FRAME_CANDIDATE`**: `CANDIDATE_GENERATED_HUMAN_REVIEW_PENDING` (`8` original 1080p environment & framed staging PNGs in `tests/evidence/kh01_20261116_015100Z/style_poc/`)
- **`VQ02_CHARACTER_MODEL_SHEET_CANDIDATE`**: `CANDIDATE_GENERATED_HUMAN_REVIEW_PENDING` (`4` original `2400x1600` 3-view + 6-expression sheets across Roman, Science & Business niches)
- **`VQ03_ACTING_8S`**: `PASS` (7.0s / 168-frame reaction + handoff clip + same-script `A / B1 / B2 / C` comparison isolating art upgrade `A->B1` from MotionPlan/Rigby2D WebGL acting `B1->B2->C`)
- **`VQ04_MULTICAMERA`**: `PASS` (continuous 2-actor cart brace & scroll catch across 3 genuine views + 100% intershot & internal cut audit)
- **`VQ05_MULTI_NICHE`**: `PASS` (`4` domains including unseen Planetarium holdout driven through universal `modern_expressive_2d` template with zero per-story JS modules)
- **`VQ06_FINAL_FILM`**: `CANDIDATE_TECH_VERIFIED_HUMAN_REVIEW_PENDING`
  - **Path**: `projects/kh01_modern_2d_roman_urgent_scroll_30s/out/KH01_ROMES_MOST_URGENT_SCROLL_ORIGINAL_30S_1080P.mp4`
  - **SHA-256**: `f205dd30d6146bef279491feb24ede1f872d30632d1c96b6af7234e5b9c939f0` (`10481468` bytes, `1920x1080`, `24fps`, `720` decoded frames, `0.0ms` narration overlap, `-15.4 LUFS`, `-1.4 dBTP`)

## Resource & Regression Summary
- **Minimum Free Disk Observed**: `54.207 GiB` (floor `>= 6.0 GiB`)
- **Minimum Available RAM Observed**: `6.544 GiB` (floor `>= 1.0 GiB`)
- **QA Microbenchmark (`n=3` `ffprobe`+`RGB24`)**: serial mean `1.6019s` vs bounded-parallel mean `0.612s` (`2.617x`, 100% identical SHA-256s; never extrapolated to full film render)
- **Full E2E Regression**: `FLOW_READY` (`81/81` required gates passed)
