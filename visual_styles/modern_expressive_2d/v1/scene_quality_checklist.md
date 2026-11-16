# Scene Quality Checklist — `modern_expressive_2d.v1`

- [ ] **C01 — Silhouette Readability**: Primary character silhouette separates clearly from midground/background (`luma contrast >= 0.22`) at both 1080p and 360px mobile thumbnail width.
- [ ] **C02 — Variable Ink Hierarchy**: Outer character contour is visibly bolder than interior cloth folds and distant architectural lines.
- [ ] **C03 — Cel-Shading & Rim Light**: At least 2–3 readable value groups (base + shadow + highlight) and grounded floor contact shadows are present on characters and hero props.
- [ ] **C04 — Non-Generic Character Design**: Actor head/body proportions, hairstyle, skin tone, and layered outfit match the script's niche and character bible (no default Roman soldier helmets in civilian/science/business scripts).
- [ ] **C05 — True Viewpoint Geometry**: Camera viewpoint (`front`, `three_quarter`, `profile`, `close_hand_insert`, `close_face_insert`) uses dedicated view geometry rather than a cropped/flipped front portrait.
- [ ] **C06 — Facial & Hand Acting**: Facial expression changes with narrative beat; gripping hands visibly close around prop anchors with zero hover (`<= 0.04` normalized actor height).
- [ ] **C07 — Planted Foot Grounding**: Stance feet hold world-space floor anchors (`median drift <= 0.03`); locomotion uses distance-coupled stepping.
- [ ] **C08 — Multi-Plane Depth & Perspective**: Wide/medium shots exhibit clear foreground/midground/background separation, architectural perspective lines, and material detail.
- [ ] **C09 — Diegetic & Overlay Text Legibility**: Any on-screen text (e.g., scroll lettering or minimal end badge) stays inside safe zones, meets contrast `>= 4.5`, and occupies `<= 20%` of frame area.
- [ ] **C10 — Copyright & Provenance Cleanliness**: Zero pixels from user reference frames, external copyrighted videos, Rigby2D demo mascots, or prior FL-01 preview stills.
