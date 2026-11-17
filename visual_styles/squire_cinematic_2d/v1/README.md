# Squire Cinematic 2D (`squire_cinematic_2d.v1`)

## Purpose & Lineage
`squire_cinematic_2d.v1` is a versioned, opt-in 2D visual style profile derived directly from the verified `origin/Production` Squire pack (`packs/squire/ink.js`, `packs/squire/chara.js`, `packs/squire/world.js`, `packs/squire/templates.js` at commit `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`).

It preserves the unmistakable Squire caricature DNA while addressing key structural limitations observed in baseline renders:
1. **Preserved Identity**:
   - Signature warm cream round head (`#f4ede1`) at `~38%` of body height (`R = 19u` for `100u` stature) and espresso-brown contours (`OUT = #392a21`).
   - Clear historical silhouette readability and soft 2D depth-of-field background separation (`blurLayer`).
   - Existing `Production` projects (`projects/squire-mau`, `projects/selfimprove-mau`) remain 100% untouched unless a project explicitly opts into `style_profile: "squire_cinematic_2d.v1"` and `render_mode: "canvas2d_only"`.
2. **Selective 2D Upgrades**:
   - **Tapered & Hierarchical Linework**: Screen-space aware outer contour vs interior crease weights (`strokeTapered2D`) instead of uniform single-width strokes.
   - **Organic Limb & Hand Anatomy**: Upper/forearm taper, elbow/knee articulation without exposed capsule circles, planted flat-sole sandals/boots, and articulated finger/thumb prop grips (`rope_grip`, `pin_catch`, `open_recoil`) instead of featureless white circular mittens.
   - **2–3 Purposeful Cel-Shading Bands**: Lit local value + cool pre-dawn shadow plane + selective contact occlusion and warm dawn rim highlight (`fillCelShadedShape2D`, `shadeClothFold2D`, `drawInkEdgeHighlight2D`).
   - **Semantic Niche Data Profiles**: Roman, medieval, and non-historical palettes/costumes live in `style_bible.json` data profiles resolved by `tools/kh02_style_contract.py`, never hardcoded into generic `ink.js` primitives.
   - **3–5 Layered Canvas2D Environments**: True 2D parallax depth planes (sky atmosphere, far hills/aqueducts, mid stone/timber architecture, subject stage, dark foreground framing occluder) with zero Three.js/WebGL dependencies.

## Verification
Stamp or verify the canonical SHA-256 style lock digest with:
```bash
python tools/kh02_style_contract.py --style-id squire_cinematic_2d.v1 --json
```
