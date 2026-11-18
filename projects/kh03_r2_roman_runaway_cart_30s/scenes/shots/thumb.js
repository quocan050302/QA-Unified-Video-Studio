// thumb.js — Native 9:16 Thumbnail Cover Art for KH-03.0.R2 (roman_market_hill).
import { E, registerShot } from '/engine/core.js';
import {
  PAL,
  titleText,
  drawRomanMarketSlopeBackdrop2D,
  drawRomanRiverHarbor2D,
  drawRomanForumCourtyard2D,
  drawRomanCart2D,
  drawRomanLoaf2D,
  romanActorAt,
  drawRomanMasterActor2D,
} from '/packs/squire/pack.js';

registerShot('thumb', {
  draw(g) {
    const w = E.W || 1080;
    const h = E.H || 1920;
    drawRomanMarketSlopeBackdrop2D(g, { globalT: 1.0 }, { scrollX: 120, slopeDropFrac: 0.08 });
    const hero = romanActorAt(1.0, {
      start: 0, end: 2,
      actors: {
        centurion_varro: {
          archetypeId: 'centurion_varro', hasShield: false, weapon: 'none',
          xFrac: 0.62, yFrac: 0.65, hFrac: 0.34, bodyRot: 0.04,
          leftFootLocal: [-10, 0], rightFootLocal: [10, 0], armsAng: [-20, -25, 32, -20], face: 'bored', look: -0.2,
        },
      },
    }, 'centurion_varro', { W: w, H: h, globalT: 1.0 });
    drawRomanMasterActor2D(g, hero, { seed: 41, shoeMode: 'front' });
    if ('roman_market_hill' === 'roman_market_hill') {
      drawRomanCart2D(g, w * 0.28, h * 0.62, w * 0.36, { tiltRad: 0.09, wheelAngleRad: 1.1 });
      drawRomanLoaf2D(g, w * 0.635, h * 0.275, w * 0.145, { rot: 0.04, squishFrac: 0.1 });
    }
    titleText(g, "THE CART", w * 0.5, h * 0.11, h * 0.064, { color: '#ffe875', rot: -0.025 });
    titleText(g, "WOULDN'T STOP!", w * 0.5, h * 0.19, h * 0.066, { color: '#ff5247', rot: -0.025 });
  },
});
