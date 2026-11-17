# Roman Squire Master Style Bible v1 (`roman_squire_master.v1`)

`roman_squire_master.v1` locks the **exact Production Squire Roman 2D visual identity** (`origin/Production` @ `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1`) as the authoritative long-term Roman visual standard.

## Core Locked Identity Anchors
- **Head & Face**: Round ivory head (`R = 19u`, ~`38%` of body height `h`, `#f4ede1`), single clean cel-shade crescent (`#d9cfd0`), minimal dark-warm-brown dot/line eyes and mouth (`OUT = #392a21`).
- **Helmet**: Warm-bronze/gold Roman `montefortino` / `attic` helmet (`#d3a24e`) with hinged riveted cheek-guards and upright decorative feathers (`feathers: 3`) or transverse crest.
- **Body & Limbs**: Red Roman tunic (`#c9473a`) with rectangular bronze pectoral plate (`3` rivets), leather belt with gold buckle, clean Squire tube limbs, and signature round white glove hands (`#ffffff`).
- **Shield & Weapon**: Tall oval-rectangular red `scutum` (`#c9473a`) with gold rim (`#e7b04a`), central steel boss, vertical spine strip, yellow lightning/wings charge, and wood-shafted `spear` / `pilum`.
- **Environment**: Flat-layered 2D warm Roman field/camp grammar (`packs/squire/world.js` & `packs/squire/roman_master/environment.js`) with softened distant formations.

## Opt-In Contract & Baseline Guarantee
- Projects opt in explicitly via `"style_profile": "roman_squire_master.v1"` and `"render_mode": "canvas2d_only"` in `config.json`.
- When `style_profile` is omitted or disabled, `packs/squire/*` renders **100% identical Production pixels**.
- Artistic/editorial approval is never auto-stamped by code (`STYLE_APPROVED = HUMAN_REVIEW_PENDING`).
