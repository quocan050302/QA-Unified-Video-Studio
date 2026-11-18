# PERCEPTUAL QA REVIEW — KH-03.0.R2

Kiểm định thị giác từ pixel giải mã thực (`tools/kh03_perceptual_qa.py`, `ffmpeg` decode thực -> Pillow/NumPy/SciPy, loại trừ hoàn toàn vùng phụ đề `y >= 0.615*H` để chữ phụ đề không bao giờ ngụy tạo điểm chuyển động).

## 1. Story A (30.000s Pilot — `KH03_R2_ROMAN_RUNAWAY_CART_ORIGINAL_30S_9x16.mp4`)

- **Overall Perceptual QA Status**: `PASS`
- **Decoded Frames Sampled**: `112` (bao phủ cặp ranh giới cắt `f_end -> f_start` + các điểm nội bộ từng shot)
- **Non-adjacent Duplicate Pairs (`16x16` stage signature)**: `0` (`[]`)
- **Unannotated Low-Motion Shots**: `0` (`[]`)
- **Frozen-Actor Zoom-Spam Alerts**: `0` (`[]`)
- **Suspicious Low-Change Cuts (`15` cuts evaluated)**: `0` (`[]`)
- **Overscan Black Borders (`min_border_luma < 2.0`)**: `0` (`[]`)
- **Axis Violations (`stage_axis_sign`)**: `0` (`[]`)

| Shot | Action ID | `stage_mad_start_to_end` | `min_interior_step_mad` | Cut Out -> Next `cut_mad` |
|---|---|---|---|---|
| `SH01` | `world.market_hill_establish` | `53.139` | `3.830` | `50.987` (`SH01->SH02`) |
| `SH02` | `actor.idle_micro_act` | `51.814` | `1.634` | `53.530` (`SH02->SH03`) |
| `SH03` | `prop.peg_crack_snap` | `35.229` | `3.465` | `41.045` (`SH03->SH04`) |
| `SH04` | `prop.cart_roll_slope` | `39.354` | `7.099` | `51.122` (`SH04->SH05`) |
| `SH05` | `world.market_crowd_pass` | `50.651` | `10.634` | `46.166` (`SH05->SH06`) |
| `SH06` | `actor.sprint_chase` | `41.308` | `11.572` | `37.251` (`SH06->SH07`) |
| `SH07` | `actor.reach_grab_prop` | `38.675` | `11.115` | `37.695` (`SH07->SH08`) |
| `SH08` | `prop.rope_taut_post_wrap` | `34.415` | `2.283` | `38.785` (`SH08->SH09`) |
| `SH09` | `actor.stop_brace` | `31.492` | `2.123` | `30.104` (`SH09->SH10`) |
| `SH10` | `prop.cart_halt_skid` | `34.746` | `1.751` | `36.679` (`SH10->SH11`) |
| `SH11` | `prop.prop_bounce_tray` | `34.567` | `2.202` | `39.468` (`SH11->SH12`) |
| `SH12` | `prop.prop_parabolic_arc` | `33.324` | `5.684` | `44.278` (`SH12->SH13`) |
| `SH13` | `prop.helmet_impact_settle` | `44.537` | `3.733` | `45.508` (`SH13->SH14`) |
| `SH14` | `actor.deadpan_walk_unaffected` | `45.455` | `7.856` | `47.508` (`SH14->SH15`) |
| `SH15` | `actor.deadpan_walk_unaffected` | `51.690` | `8.588` | `57.681` (`SH15->SH16`) |
| `SH16` | `actor.crowd_reaction_cheer` | `50.465` | `7.851` | `—` |

## 2. Calibration Baseline (`R1`) & Negative Controls

- **R1 Baseline (`kh03_r1_roman_gate_message_30s`)**: `105` samples decoded, `PASS`, `0` duplicates, `0` low-motion shots, `0` suspicious cuts, `0` border alerts.
- **Negative Perceptual Controls (`test_perceptual_qa_catches_zoom_spam_duplicates_and_subtitle_only_motion`)**:
  1. Static actor card under pure `1.0->1.14x` zoom + flashing bottom caption box (`y >= 0.65*H`): flagged `FAIL` cleanly without being fooled by caption flicker.
  2. Non-adjacent duplicate shots (`SH01 == SH03`): flagged `duplicate_nonadjacent_pairs` & `status == FAIL`.
  3. Diverse animated trajectory control (`pos_varied.mp4`): passed cleanly (`status == PASS`).

## 3. Defects Visually Caught & Fixed During Still/Contact-Sheet Inspection

1. Crowd citizens at `y=0.50` originally overlapped behind Baker Lucius near his oven -> moved flanking citizens to upper walkway `y=0.45..0.47, h=0.165` (`market_env.js`).
2. `drawMarketForegroundPass2D` originally rendered a large brown foreground silhouette overlapping bottom captions at `y=0.63..0.82*H` (`SH06`) -> replaced with upper-edge speed streaks and stall post above `y <= 0.585*H`.
3. `prop_cart_halt_skid` originally stopped too close to oven table -> shifted cart (`x=0.43, wCart=0.33`) left of oven (`0.85`) for a clear visible handspan gap.
4. `forum_courtyard` `SH04` bench originally touched the messenger's calves -> moved marble bench right (`0.81`) cleanly clearing foreground floor.

- **Subjective Aesthetic & Humor Sign-Off**: `STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`.
