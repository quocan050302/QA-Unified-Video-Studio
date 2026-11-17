# KH-02.0 + KH-02.1 — Visual Style & Editorial Review Packet (`VISUAL_REVIEW.md`)

> [!IMPORTANT]
> **Editorial & Artistic Sign-Off Status**:
> - `KH02_STYLE_APPROVED = HUMAN_REVIEW_PENDING`
> - `KH02_EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`
> Automated metrics verify structural invariants (proportions, outline hex, cel-band rendering, zero 3D, `0.0px` world-space hand/foot contact, frame determinism, and continuity across cuts), **not** subjective artistic appeal or audience retention uplift. Human review of the contact sheets and local MP4 is required before production sign-off.

## 1. KH-02.1 Style POC Artifacts (`style_poc/`)

Receipt: `docs/antigravity_runs/KH-02_0_1_20261117_014132Z_db01/style_poc/style_poc_receipt.json`

| Artifact | Purpose | SHA-256 |
| --- | --- | --- |
| `style_poc/poc_contact_sheet.jpg` | Master 9-panel overview of all original KH-02.1 2D POC proofs | `65279acf6cfa8317e386bd25d947ab9d4c361dee5d9079aef49ac0d059157c84` |
| `style_poc/baseline_vs_kh02_comparison.jpg` | Side-by-side comparison of pre-edit Squire baseline vs KH-02.1 evolutionary 2D style | `c5873911693b0b32bb9877239843030ea1f0748b054c3974be1861e77f374825` |
| `style_poc/poc_01_characters_dual_scale.png` | `TAVI` & `LYRA` rendered at full medium (`470px`) and far (`205px`) scales with adaptive stroke weights | `989812b3d6ef75144acfa740fc9dcdcc2488543b6a0aabb9c69b2f234c027f93` |
| `style_poc/poc_02_dramatic_close_face.png` | Dramatic close-up of `TAVI` (`wide_shock` expression, asymmetric brows, pupil highlight, dawn rim) | `dc7108a2dcf182cf3ababc25567840bb30058624cb7b6f7661db88fc92b8e590` |
| `style_poc/poc_03_wide_establishing_belfry.png` | 5-plane Roman hilltop belfry interior overlooking 5-arch aqueduct & twin cypresses | `23a6c1380955284ac25b29386ac2aa18e18bf68c7941c2f019710188c4efccd4` |
| `style_poc/poc_04_environment_stairwell_detail.png` | Travertine tower stairwell with arched window light shaft & foreground handrail parallax | `5f3650f53b57d867fccaef0ec96834eeffe4140590dd77b489b889e738603b13` |
| `style_poc/poc_05_prop_hand_contact_closeup.png` | Leather-wrapped articulated hand catching the iron clapper bulb inside the cast-bronze bell | `2f19180d8572121661ec1061ed590bf60e6b04ca9e0b39f151e95e8da1e660d1` |
| `style_poc/poc_06_goat_pip_quadruped.png` | `PIP` (`quadruped_animal_2d`) in rope-nudge and sneeze-stretch poses | `5cb0dd6e10605d940fc42677d943640a6d73f9af1bc3ee69793ae8d3b21e76d6` |
| `style_poc/model_sheet_turnaround_tavi_lyra.png` | `front`, `three_quarter`, and `profile` turnaround sheet for `TAVI` & `LYRA` | `9e7c45b83dc500f4ea49ecc1fc025d00e15c85d19ed46aeb7ac412a7e45b0835` |
| `style_poc/expression_sheet_tavi_lyra_6states.png` | 6-state expression & articulated hand-pose model sheet | `90a217ffa26a9d6e6f8b3c47c11f34c78171b9016c87e2618c7a9310d42802bf` |
| `style_poc/poc_09_courtyard_exterior_angle.png` | Cobbled hilltop courtyard below the bell tower with `LYRA` at balcony shutter & `MARCUS` below | `eb0cd0375e952f85812862476cddf370319fb9592474496ca03f532d9747a124` |

## 2. Experimental 30.000s Original Film Review Packet (`film_preview_packet/`)

- **Working Title**: `THE BELL THAT RANG TOO EARLY` (fictional original Roman pre-dawn comedy short; zero scrolls, couriers, marketplace carts, awnings, eagle banners, or reused renders)
- **Local MP4 Path**: `projects/kh02_bell_before_sunrise_30s/out/KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4` (`sha256: 2f521d88e1da887bfe0654085230b95257154b6f16411e1aeaa39d8da5a9cf5a`, `9,009,085` bytes)
- **8-Shot Contact Sheet**: `film_preview_packet/contact_sheet_8shots.jpg` (`sha256: c8c6b9aba5526134359a424bc013e1019d03c7dd6567ff3783bd18ae73a7d92f`)
- **Action Strips**:
  1. `action_strips/strip_1_hook_nudge.jpg` (`0.10s, 0.35s, 0.65s, 1.85s` — immediate 0.5s goat-rope hook with 2D blurred bell behind)
  2. `action_strips/strip_2_rising_climb_and_catch.jpg` (`7.80s, 8.85s, 15.20s, 19.80s` — low-angle rope pull & slip, non-skating stair climb, clapper catch)
  3. `action_strips/strip_3_sneeze_and_deadpan_payoff.jpg` (`24.20s, 24.95s, 27.30s, 29.10s` — goat sneeze squash/stretch, waking courtyard payoff, deadpan cut)

## 3. Honest Artistic Assessment & Known KH-02.1 Limitations

- **What Improved Over Production Baseline**:
  - Preserves Production Squire's signature ~38% round caricature head (`#f4ede1`) and dark warm-brown ink (`#392a21`) while replacing uniform stick/tube limbs and round mittens with tapered anatomical 2D envelopes, 2–3 band clipped cel shading, warm dawn rim lighting, cloth drape folds, and 7 readable finger-wrap/splay hand poses.
  - World-locked 2D IK eliminates planted-sandal skating on the stairwell (`0.0px` drift) and locks Tavi's hands directly onto the braided hemp rope (`S03`) and iron clapper bulb (`S06`) with `0.0px` world error.
  - Multi-plane 2D environments maintain consistent geographic landmarks (5-arch aqueduct, twin cypresses, bell yoke geometry) across all 6 camera angles without Three.js.
- **Known Limitations (To Address in Future KH-02.2..KH-02.5)**:
  1. **Procedural Canvas2D Vector Look vs Hand-Painted Bitmap Brushwork**: Outlines and cel bands are procedural vector paths; while tapered and cel-shaded, they remain crisp vector cartoons rather than textured gouache/watercolor paintings.
  2. **Bounded Local Choreography**: Shot motion in `bell_film.js` uses bounded per-shot 2D curves (`shot_direction.js`) authored specifically for this 30s preview rather than a generalized multi-shot character continuity/motion compiler (planned for KH-02.2 & KH-02.3).
  3. **Local Windows SAPI TTS**: English narration is clear, real spoken speech at 1.0x rate with exact silence margins, but uses local SAPI synthesis rather than a human voice actor recording.
