// thumb.js — Native 9:16 Thumbnail Cover Art for KH-03.0.R1 ("The Message That Arrived One Second Late").
import { E, registerShot } from '/engine/core.js';
import { PAL, titleText, blockArrow, drawRomanCityApproachDusk2D, drawSealedRomanScroll2D, romanActorAt, drawRomanMasterActor2D } from '/packs/squire/pack.js';

registerShot('thumb', {
  draw(g) {
    const w = E.W || 1080;
    const h = E.H || 1920;
    drawRomanCityApproachDusk2D(g, { globalT: 1.5, gateCloseFrac: 0.78, boltDropFrac: 0.0 }, { horizonYFrac: 0.48, groundYFrac: 0.60 });
    const courier = romanActorAt(1.5, {
      start: 0, end: 2,
      actors: {
        courier_marcus: {
          archetypeId: 'courier_marcus', courierSatchel: true, hasShield: false, weapon: 'none',
          xFrac: 0.25, yFrac: 0.67, hFrac: 0.30, bodyRot: 0.14,
          leftFootLocal: [-12, 0], rightFootLocal: [14, -6], armsAng: [-45, -30, 58, 22], face: 'shock', look: 0.85,
        },
      },
    }, 'courier_marcus', { W: w, H: h, globalT: 1.5 });
    drawRomanMasterActor2D(g, courier, { seed: 7, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold], shoeMode: 'side' });
    blockArrow(g, w * 0.64, h * 0.27, w * 0.51, h * 0.35, { w: w * 0.048, fill: '#e0352f', lw: 6 });
    drawSealedRomanScroll2D(g, w * 0.70, h * 0.49, w * 0.27, { mode: 'unrolled_message', rot: 0.04, mudAmount: 0.85, lines: ['KEEP', 'THE GATE', 'OPEN'] });
    titleText(g, 'ONE SECOND', w * 0.5, h * 0.115, h * 0.064, { color: '#ffe875', rot: -0.025 });
    titleText(g, 'TOO LATE!', w * 0.5, h * 0.195, h * 0.068, { color: '#ff5247', rot: -0.025 });
  },
});
