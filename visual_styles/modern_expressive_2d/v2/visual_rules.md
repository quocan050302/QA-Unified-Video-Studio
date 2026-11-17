# Visual Style Rules & Human Signoff Checklist — `modern_expressive_2d.v2`

- **Profile**: `modern_expressive_2d.v2` (`visual_styles/modern_expressive_2d/v2/style_bible.json`)
- **Status**: `PROPOSED — NOT APPROVED` (`STYLE_APPROVED = HUMAN_REVIEW_PENDING`, `VQ_REFERENCE_MATCH = HUMAN_REVIEW_PENDING`)
- **Backward Compatibility**: `modern_expressive_2d.v1` remains frozen and untouched for all existing `KH-01` projects and baselines.

---

## 1. Mandatory Art & Engineering Rules (`v2`)

1. **Variable-Weight Calligraphic Ink**:
   - Outer character silhouette strokes use warm dark-espresso `#211612` (`1.05%–1.68%` of actor pixel height, clamped `3.5–10.5 px` in closeups) with smooth curve subdivision and tapered terminals.
   - Interior cloth creases, collar seams, nose bridges, and palm lines use `#3A2821` at `34%–54%` of outer contour thickness so silhouettes read instantaneously before interior detail.
2. **Curved Tapered Anatomy (Zero Pipe/Capsule Limbs)**:
   - Upper arms emerge from structured or draped sleeves (`bomber sleeve`, `rolled overshirt cuff`, `wide robe sleeve`, `tailored lab sleeve`).
   - Bare forearms and calves follow a curved Bezier spine with rounded elbow/knee volume and graceful taper into a narrower wrist/ankle.
   - Hands differentiate **wrist, palm volume, thumb, and 3–4 curved fingers** (`relaxed`, `open_reach`, `locked_grip`, `spread_shock`, `pointing`, `careful_pinch`).
3. **Layered Garments & Convincing Folds**:
   - Every hero/supporting character wears >= 2 readable garment layers (e.g., open windbreaker/parka or overshirt over inner tee/blouse, collar lapels, cuff bands, hem trim, pockets/straps) with `3–8` curved tension/drape creases.
   - Distinct silhouette per character: **Mina** (`inventive_school_youth`, compact energetic build, bob hair with side clip & flared coral-red windbreaker over striped tee) vs **Bao** (`caring_older_friend`, taller broad-shouldered build, tousled dark waves, teal open overshirt over warm ochre tee & cuffed chinos).
4. **4 True Authored Views + 7 Distinct Expressions**:
   - Views: `front`, `three_quarter`, `profile` (with sculpted nose/chin projection), and `rear_three_quarter` (for over-the-shoulder foreground depth staging—never a horizontally flipped or cropped front view).
   - Expressions: `neutral_attentive`, `wide_shock`, `strained_exertion`, `determined_focus`, `joyful_laugh`, `deadpan_disbelief`, and `warm_relief_smile`, featuring crisp tooth and tongue cel-planes on open mouths.
5. **Multi-Plane Tactile Environments & Motivated Lighting**:
   - Every wide/medium stage authors sky/atmosphere, far canopy/architecture, midground props with tactile material patterns (leaf clusters, wood grain/lattice, stone joints, bicycles, fountains), **diagonal warm sunlight shafts**, perspective ground paving with soft cast shadows, and foreground occluders.
   - Closeups and macro inserts soften far clutter into a designed atmospheric mood backdrop (`Reference 3` principle) while keeping foreground hands/props/faces razor-sharp.
6. **FX Discipline**:
   - Poster FX (`Reference 1`: white sticker border, neon chromatic edge, comic halftone) is opt-in ONLY for `poster_thumbnail_mode=True` and strictly forbidden in narrative scene shots.

---

## 2. Human Editorial Signoff Checklist (`HUMAN_REVIEW_PENDING`)

- [ ] **Outline Fluency**: Outer contours taper cleanly around head, shoulders, sleeves, and hands without jagged polygon corners or uniform wireframe lines.
- [ ] **Limb & Hand Craft**: Arms and legs show organic curve, elbow/knee volume, sleeve-to-wrist transitions, and readable fingers/thumbs (no rigid cylindrical pipes).
- [ ] **Distinct Silhouettes & Wardrobe**: Mina, Bao, and multi-niche characters read immediately by silhouette alone, with layered collars, cuffs, hems, and folds.
- [ ] **Facial Storytelling**: Joy, shock, focus, strain, and warm relief read effortlessly at both `1920x1080` and mobile thumbnail scale.
- [ ] **Shading & Lighting**: 3-band cel shading (lit base + curved core shadow + warm rim light) aligns with diagonal stage sunbeams and ground contact shadows.
- [ ] **Environment & Staging Depth**: Multi-plane park/interior stages exhibit real material texture, foreground overlap, and wide/medium/close/macro rhythm.
- [ ] **Reviewer Decision**: `PENDING USER VISUAL APPROVAL` (`STYLE_APPROVED = HUMAN_REVIEW_PENDING`).
