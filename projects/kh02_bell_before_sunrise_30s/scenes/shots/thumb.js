// thumb.js — Original 2D Thumbnail for 'THE BELL THAT RANG TOO EARLY' (canvas2d_only).
import { E, registerShot } from '/engine/core.js';
import {
  titleText,
  vignette,
  drawSquireCinematic2DActor,
  drawPipGoat2D,
  drawLayeredRomanEnvironment2D,
  evaluateBellRigStateAt,
} from '/packs/squire/pack.js';

registerShot('thumb', {
  draw(g) {
    const rig = evaluateBellRigStateAt(11.2);
    drawLayeredRomanEnvironment2D(g, { z: 1.05, x: 20, y: 0 }, {
      view: 'belfry_wide_interior',
      globalT: 11.2,
      rigState: rig,
      drawStageActors: (c) => {
        drawSquireCinematic2DActor(c, 580, 995, 620, {
          castId: 'TAVI',
          view: 'three_quarter',
          expression: 'wide_shock',
          pupilX: 0.82,
          pupilY: -0.55,
          spineLean: -0.08,
          armAngles: [68, 52, 86, 46],
          rightHandPose: 'open_recoil',
          leftHandPose: 'open_recoil',
          t: 1.2,
        });
        drawPipGoat2D(c, 1255, 965, 340, {
          flip: true,
          action: 'sneeze_burst',
          phase: 0.65,
          t: 1.2,
        });
      },
    });
    vignette(g, 0.24, '#16111e');
    titleText(g, 'ONE HOUR', E.W * 0.27, E.H * 0.19, E.H * 0.14, { color: '#fff6e0', rot: -0.03 });
    titleText(g, 'EARLY?!', E.W * 0.27, E.H * 0.34, E.H * 0.15, { color: '#ffbf5e', rot: -0.02 });
  },
});
