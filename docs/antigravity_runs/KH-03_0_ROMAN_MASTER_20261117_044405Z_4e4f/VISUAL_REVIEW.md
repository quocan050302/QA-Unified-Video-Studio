# KH-03.0 — Visual Style Lock & 30s Pilot Editorial Review Guide (`VISUAL_REVIEW.md`)

> **Governance Gate Status**:
> - `SOURCE_BASELINE_LOCK`: **`PASS`** (Automated — `0` pixel diff when opt-in profile is disabled)
> - `ROMAN_IDENTITY_PRESERVED` (Technical Geometry/Palette): **`PASS`** (`Silhouette IoU = 1.000000` at both `wide` and `close`)
> - `STYLE_APPROVED`: **`HUMAN_REVIEW_PENDING`** *(Requires explicit human sign-off on A/B sheets)*
> - `EDITORIAL_APPROVED`: **`HUMAN_REVIEW_PENDING`** *(Requires human viewing of the 30.000s MP4; no retention uplift is claimed without real viewer analytics)*

---

## 1. Reviewer Guide: Same-Character, Same-Pose A/B Proof

- **Review Sheet**: [`style_poc/same_pose_ab_contact_sheet.jpg`](./style_poc/same_pose_ab_contact_sheet.jpg)
- **Expression & Pose Sheet**: [`style_poc/original_roman_expression_pose_sheet.jpg`](./style_poc/original_roman_expression_pose_sheet.jpg)
- **Metrics JSON**: [`style_poc/same_pose_ab_metrics.json`](./style_poc/same_pose_ab_metrics.json)

### What Was Locked (Zero Makeover / Zero Family Swap)
1. **Exact Original Production Squire Soldier (`CAST.hastatus` & `CAST.princeps`)**:
   - Round `#f4ede1` ivory face (`R = 19u`, `38%` of stature) with `#d9cfd0` cel crescent and minimal `#392a21` dot/open/closed eyes and mouth.
   - Warm-gold `#d3a24e` Montefortino helmet with cheek guards and 3 `[white, #392a21, white]` feathers (rookie) or `[#c9473a, #392a21, #c9473a]` feathers + mustache (instructor).
   - Red `#c9473a` Roman tunic with bronze pectoral plate, `#ffffff` round white gloves, tall red `scutum` (`0.33s x 0.50s` ellipse) with `#e7b04a` gold rim and `#dedbd8` steel boss, and wood/steel spear.
   - **Zero** KH-02 Tavi/Lyra characters, **zero** bare-hair swaps, **zero** anime irises, **zero** 3D meshes.

### Exact Deliberate Pixel Delta Between `BEFORE` and `AFTER`
- **Profile OFF vs Immutable `origin/Production`**: `0` changed pixels (`wide` = `0`, `close` = `0`).
- **Opt-In `romanMasterPolish: true` vs Immutable `origin/Production`** (same `hastatus`, same pose, same background, same camera):
  - **Silhouette IoU**: `1.000000` (`wide`) and `1.000000` (`close`) — outer contour is 100% identical.
  - **Changed Pixel Ratio**: `0.029%` (`595 / 2,073,600` px in `wide`) and `0.123%` (`2,557 / 2,073,600` px in `close`).
  - **Visual Explanation (highlighted in cyan on the Overlay panels)**: Adds only a thin `#fff2c6` specular highlight along the Montefortino helmet brow ridge and a crisp micro-glint on the `scutum` steel boss so dark/close shots retain clean material separation at 1080p.
  - **In-Motion Rig Upgrade (`original_roman_expression_pose_sheet.jpg`)**: Solves `lsh, lel` analytically (`solveRomanShieldGrip`) so the left white glove stays anchored behind the `scutum` in all 8 expressions/poses instead of swinging out into empty air as legacy `POSES.guard`/`push` did.

---

## 2. Reviewer Guide: Fresh 30.000s Pilot (*"THE LAST GAP IN THE SHIELD WALL"*)

- **9-Shot Contact Sheet**: [`film_preview_packet/contact_sheet_9shots.jpg`](./film_preview_packet/contact_sheet_9shots.jpg)
- **Action Strip 1 (`SH05` Foot-Plant & Shield Shove)**: [`film_preview_packet/action_strip_1_sh05_footplant_and_shield_shove.jpg`](./film_preview_packet/action_strip_1_sh05_footplant_and_shield_shove.jpg)
- **Action Strip 2 (`SH06` 24fps Rim Squash & Deflection)**: [`film_preview_packet/action_strip_2_sh06_wooden_spear_deflection.jpg`](./film_preview_packet/action_strip_2_sh06_wooden_spear_deflection.jpg)
- **Action Strip 3 (`SH07–SH08` Camera Push-In & Strap Twist)**: [`film_preview_packet/action_strip_3_sh07_sh08_camera_push_and_strap_twist.jpg`](./film_preview_packet/action_strip_3_sh07_sh08_camera_push_and_strap_twist.jpg)
- **Thumbnail**: [`film_preview_packet/thumbnail_1280.jpg`](./film_preview_packet/thumbnail_1280.jpg)

| Beat | Time (s) | Frames | Scale & Camera Move | Story / Visual Action Checkpoints |
|---|---|---|---|---|
| `SH01` | `0.00–2.50` | `0–59` | Extreme Detail Insert (`push_in_focus`) | Immediate frame-0 action (`fadeIn=0`): rookie's white glove grips trembling red `scutum` rim; dawn sunbeam & approaching blunt wooden spear visible in gap. |
| `SH02` | `2.50–5.50` | `60–131` | Medium Over-Shoulder (`subtle_lateral_drift`) | Foreground neighbor `scutum` on left; rookie's eyes shift left (`neutral -> focused -> worried`) and grip tightens. |
| `SH03` | `5.50–9.00` | `132–215` | Wide Geography (`pan_left_to_right`) | Timber `castra` gate/ramp on left, tents & desynchronized cohort in mid, sunlit gap in front squad, `princeps` instructor aiming wooden spear. |
| `SH04` | `9.00–12.00` | `216–287` | Low-Angle Profile (`dynamic_follow_launch`) | Instructor coils (`anticipation`), steps with sand dust puff, and launches harmless leather-knobbed wooden practice spear left-to-right. |
| `SH05` | `12.00–15.00` | `288–359` | Medium-Full Tracking (`lateral_track_into_lock`) | Rookie steps & plants front sandal (`0.00px` drift), shoves `scutum` leftward to seal the wall at `13.65s`, inadvertently angling his spear into neighbor's strap. |
| `SH06` | `15.00–18.50` | `360–443` | Macro Physics Insert (`snap_push_and_recoil`) | Blunt wooden spear hits sealed gold rim at `15.58s` with 2-frame pad squash, contact sparks, 7.5px damped shield recoil, and spinning deflection. |
| `SH07` | `18.50–23.00` | `444–551` | Wide-to-Medium Payoff (`push_in_to_instructor`) | Unbroken crimson wall holds; camera pushes in to instructor's documented 8-frame eye-narrowing hold followed by a single crisp nod. |
| `SH08` | `23.00–26.50` | `552–635` | Medium Two-Shot (`pull_back_comic_reveal`) | Rookie exhales (`exhale`), tugs his spear caught in neighbor's leather strap (`surprised -> awkward`), while stubble-bearded neighbor glares (`bored`). |
| `SH09` | `26.50–30.00` | `636–719` | Motif Return Close (`lateral_glide_to_sealed_seam`) | Unsmiling instructor gives one final nod as foreground glides back to the tightly sealed red `scutum` rims (`fadeOut=0`, loop-ready). |
