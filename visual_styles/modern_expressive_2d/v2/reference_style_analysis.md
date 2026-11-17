# Reference-Grounded Visual Style Analysis — `modern_expressive_2d.v2` (KH-01.R1)

- **Style Profile ID**: `modern_expressive_2d.v2`
- **Editorial Status**: `PROPOSED — HUMAN_REVIEW_PENDING` (Never auto-approved)
- **Reference Ingestion Status**: `STYLE_REFERENCES_INGESTED_3_OF_3`
- **Private Local Review Workspace**: `.test-runs/kh01_r1_20261116_074000Z/references_private/` (gitignored; zero reference pixels committed to public Git)

---

## 1. Frame-by-Frame Visual Language Extraction

### Reference Frame 1 — `media_1794812923609_b07e0faf.jpg` (`1024x576`, `SHA-256: 26846e213288ce8c1de20ff2a93001fe86c1f460be6b24ad3ec7b35c2c7bb5c1`)
- **Role**: **High-Energy Poster / Thumbnail Accent Mode ONLY** (explicitly NOT the normal-scene default).
- **Linework**: Bold dark-espresso ink contours (`7–11 px` equivalent at `1080p`) with dynamic calligraphic taper, wrapped in a thick white sticker cutout outline and neon magenta/green chromatic edge highlights.
- **Value & Shading**: Intense high-contrast 3-band cel shading—bright lit face plane, curved diagonal core shadow wrapping ~40% of the head volume, and warm orange firelight rim glow; comic halftone dot screens applied to secondary background silhouettes and sky.
- **Facial Expression & Hand Anatomy**: Expressive squinting eye rubbed by an **articulated 4-finger + thumb hand** with distinct palm, bent index finger, curled lower fingers, and sturdy forearm cuff bracer.
- **Silhouette & Depth**: Strong overlapping piggyback foreground figure against mid-ground silhouettes and a multi-tiered architectural backdrop.
- **FX Reconciliation Rule**: White sticker cutouts, neon magenta/green chromatic borders, and comic halftone screens are **strictly restricted to `poster_thumbnail_mode=True`** and are **forbidden** on narrative video shots.

### Reference Frame 2 — `media_1794812930039_77590f3d.jpg` (`1024x521`, `SHA-256: bac9bb42a94d85556815683abefcb1e2cec562e39a56ab98850adacd9489b1f2`)
- **Role**: **PRIMARY NORMAL-SCENE QUALITY BASELINE**.
- **Linework**: Warm dark-espresso outer silhouette contour (`~6.0–8.5 px` at `1080p`) paired with clearly subordinated interior cloth fold, collar, and facial lines (`~2.5–4.2 px`), smooth rounded caps and joins, zero wireframe hairlines.
- **Character Proportions & Silhouette Contrast**: Two immediately distinguishable silhouettes—left figure tall, upright, and robed with wide draped sleeves; right figure compact, casual, kneeling in loose tunic and pleated trousers.
- **Anatomical Limb Stylization (Key Fix vs `v1`)**: Instead of straight uniform pipes/capsules, upper arms integrate seamlessly into structured or draped sleeves; bare forearms curve organically with **rounded elbows**, **graceful wrist taper**, and **differentiated palms + 3–4 rounded fingers + thumb**. Kneeling legs show soft folded volume and curved hem overlaps rather than rigid rectangular sticks.
- **Costume & Fabric Detail**: Layered cross-collars and frog-button plackets, wide cuff borders, waist sashes, layered hems, and **curved interior tension/drape creases** at elbows, chest, waist, and knees.
- **Environment Layering, Materiality & Lighting**:
  1. **Foreground Plane**: Dark-shaded carved wooden chest with a small sculptural prop on the left edge, establishing immediate depth.
  2. **Midground Architecture**: Massive warm cylindrical structural columns at varied intervals + secondary furniture behind the left actor.
  3. **Tactile Wall Surfaces**: Wood-framed lattice screen panels filled with organic wood-grain/swirl linework (never a single blank flat wall).
  4. **Motivated Directional Lighting**: A crisp **diagonal warm sunbeam shaft (~38°)** cutting across wall panels and columns, paired with **soft elliptical/directional cast ground shadows** anchoring feet/knees onto perspective floor planks.

### Reference Frame 3 — `media_1794812936006_89d46e35.jpg` (`1024x487`, `SHA-256: f69b4b310a00c78e60c9923f3218d95259e8e60e736517b694ef54f882d49535`)
- **Role**: **EXPRESSIVE CLOSEUP & DYNAMIC OVERLAPPING STAGING**.
- **Compositional Depth Overlap**: Three-layer character staging—a large **rear-3/4 foreground figure** in deep shadow with a crisp warm rim-light edge frames a **midground joyful child closeup** in the center and a **taller draped figure** on the right third.
- **Facial Acting Language**: Bold expressive mouth and eye shapes—huge joyful **D-shaped open laugh mouth** with a crisp white upper tooth block and pink tongue cel-plane, tilted crescent/oval eyes, immediate emotional clarity at a glance.
- **Cloth & Hand Craft**: Outstretched wide sleeves with contrasting cuff trim and splayed fingers; right figure's raised hand shows elongated expressive fingers emerging from layered collar/sleeve folds.
- **Closeup Background Discipline**: Soft atmospheric gradient backdrop behind close facial acting so background clutter never competes with expression readability.

---

## 2. Diagnosis of `v1` Gaps & Concrete `v2` Art Upgrades

| Dimension | `modern_expressive_2d.v1` Baseline Weakness | `modern_expressive_2d.v2` Reference-Grounded Upgrade |
| :--- | :--- | :--- |
| **Limbs & Joints** | Straight uniform-width capsule strokes (`solvePixelLimb2D` 2-segment tubes) | Curved Bezier-spined tapered limb polygons with rounded elbows/knees, flared/cuffed sleeves, tapered wrists, and sculpted palms + thumb/fingers |
| **Torso & Garments** | Simple 4-point trapezoid torso with 1–2 straight lines | Multi-layered outerwear + inner collar/shirt + draped/pleated pants/skirts with collars, cuffs, pockets/sashes, curved tension folds, and shaped cel shadows |
| **Head & Expressions** | Uniform circular/elliptical heads and small mouth strokes | Sculpted cheek/jaw silhouettes per character archetype, curved 35% volumetric cel-shadow mask + warm rim arc, large emotive D-mouths (tooth + tongue planes) & expressive lids/brows |
| **Environments** | Single flat wall + repeated uniform arches | 4-plane depth with foreground framing props/foliage, varied structural verticals, tactile surface grain (wood/stone/foliage/brick), diagonal warm sunbeams, and perspective paving |
| **Camera & Staging** | Repetitive flat medium-wide horizontal staging | Motivated rhythm combining lush wide stages, profile/3/4 medium action, rear-3/4 over-the-shoulder depth framing, and genuine tactile hand/face closeup inserts |

---

## 3. Niche-Neutrality & Anti-Plagiarism Rules

1. **Universal Craft, Domain-Adaptive Subject Matter**: What stays locked across every niche (`city_park`, `roman_forum`, `modern_science`, `everyday_business`, `holdout_botanical_conservatory`, `holdout_astronomy_museum`) is **ink weight hierarchy, curved organic limb/garment craftsmanship, 3-band cel-shading + rim light, tactile multi-plane depth, and expressive facial acting**—NEVER ancient Chinese hats, robes, characters, or palace architecture.
2. **100% Original Authorship**: Zero traced outlines, zero copied compositions, zero palette lifting from copyrighted characters, and zero reference pixels in any project build or public commit.
