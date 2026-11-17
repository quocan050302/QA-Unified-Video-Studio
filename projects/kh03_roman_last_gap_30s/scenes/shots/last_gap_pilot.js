// last_gap_pilot.js — Fresh 100% Canvas2D Procedural Shots SH01..SH09 for KH-03.0 Pilot.
// Uses ONLY Production Squire primitives + opt-in roman_master/{motion,character_state,camera,environment}.
// Zero Three.js, zero external bitmaps, zero reused demo plates, zero mutable frame-to-frame state.
import { E, clamp, lerp, registerShot } from '/engine/core.js';
import {
  OUT, PAL, shape, rect, ellipse, circ, polyS, line, tube, alpha, mix, haze, vignette,
  soldier, shield, weapon, dustPuff,
  sampleTrack, romanActorAt, drawRomanMasterActor2D,
  evaluateRomanCameraAt, drawRomanParallaxPlanes,
  drawRomanDawnSkyAndHills, drawRomanGateAndRamp2D, drawRomanDrillGroundPlane,
  drawRomanCohortLine2D, drawRomanTrainingRack2D, drawRomanTrainingYard2D, drawRomanShieldWall2D, drawWoodenPracticeSpear2D,
} from '/packs/squire/pack.js';

function camFor(shotId, globalT, fallback) {
  const beats = E.kh03?.camBeats?.shots || {};
  const spec = beats[shotId] || fallback;
  return evaluateRomanCameraAt(shotId, globalT, { [shotId]: spec });
}

// ============================================================================
// SH01 (0.00 - 2.50s): HOOK — Extreme close-up of shaking red scutum edge,
// sunlit gap sliver, and blunt wooden practice spear approaching from left.
// ============================================================================
registerShot('SH01', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? lt;
    const W = E.W, H = E.H;
    const cam = camFor('SH01', gt, {
      start: 0.0, end: 2.5, framingScale: 'extreme_detail_insert', purpose: 'hook_exposed_gap',
      zoomKeys: [[0.0, 1.06, 'c1'], [2.5, 1.22, 'c1']],
      cxKeys: [[0.0, 0.50, 'c1'], [2.5, 0.52, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [2.5, 0.49, 'c1']],
    });

    const gapPx = sampleTrack(lt, [[0.0, 118, 'c1'], [1.1, 108, 'c1'], [2.5, 96, 'c1']], 110);
    const tremorPx = Math.sin(gt * 41.0) * 4.8 * sampleTrack(lt, [[0.0, 1.0, 'c1'], [1.8, 0.72, 'c1'], [2.5, 0.55, 'c1']], 0.8);
    const spearX = sampleTrack(lt, [[0.0, 0.14, 'c1'], [0.35, 0.24, 'c1'], [2.5, 0.445, 'c1']], 0.25) * W;
    const spearY = sampleTrack(lt, [[0.0, 0.45, 'c1'], [2.5, 0.485, 'c1']], 0.47) * H;

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 8,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.58, sunX: 0.51, sunY: 0.43, seed: 17 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.58, chalkLineY: 0.86, seed: 23 });
          drawRomanCohortLine2D(c, { globalT: gt }, { y: 0.69, hFrac: 0.17, x0: 0.18, x1: 0.84, count: 6, seed: 61 });
        },
      },
      {
        depth: 0.78,
        blurPx: 1.5,
        draw: (c) => {
          // Approaching harmless wooden practice spear slicing through the dawn sunbeam toward the gap
          drawWoodenPracticeSpear2D(c, spearX, spearY, H * 0.34, -Math.PI / 2 + 0.055, { smear: 0.45 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: gapPx,
            gapCenterX: 0.515,
            wallY: 1.04,
            shieldScaleH: 0.98,
            drawNeighborShields: true,
            rookieTremorPx: tremorPx,
            rookieDropPx: 14,
            rookieRot: 0.055,
            showSunSliver: true,
          });
          // Rookie's white round Squire glove visible gripping the inner edge of the right scutum
          const gloveX = W * 0.515 + gapPx * 0.5 + 34 + tremorPx;
          const gloveY = H * 0.58 + Math.sin(gt * 28) * 2.0;
          circ(c, gloveX, gloveY, H * 0.036, { fill: '#ffffff', lw: 4.2 });
          ellipse(c, gloveX - H * 0.022, gloveY - H * 0.014, H * 0.016, H * 0.012, { fill: '#ffffff', lw: 3.4, rot: -0.5 });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH02 (2.50 - 5.50s): REVEAL — Medium over-shoulder on rookie hastatus
// noticing the exposed shield gap and tightening his grip.
// ============================================================================
registerShot('SH02', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (2.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH02', gt, {
      start: 2.5, end: 5.5, framingScale: 'medium_over_shoulder', purpose: 'character_reveal_grip',
      zoomKeys: [[0.0, 1.04, 'c1'], [3.0, 1.13, 'c1']],
      cxKeys: [[0.0, 0.53, 'c1'], [3.0, 0.50, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.0, 0.48, 'c1']],
    });

    const rookiePose = romanActorAt(gt, {
      start: 2.5,
      end: 5.5,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.78,
          xFrac: 0.58,
          yFrac: 1.14,
          lookKeys: [[0.0, 0.12, 'c1'], [0.55, -0.58, 'c1'], [3.0, -0.62, 'c1']],
          faceKeys: [[0.0, 'neutral'], [0.50, 'focused'], [1.25, 'worried']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.1, -0.025, 'c1'], [3.0, -0.015, 'c1']],
          headNodKeys: [[0.0, 0.0, 'c1'], [0.8, 1.4, 'c1'], [2.0, 0.6, 'c1']],
          shieldOffsetUKeys: [[0.0, [-15.5, -37.0], 'c1'], [1.2, [-12.0, -38.0], 'c1'], [2.6, [-9.5, -38.2], 'c1']],
          shieldRotKeys: [[0.0, 0.06, 'c1'], [1.4, 0.01, 'c1'], [3.0, -0.02, 'c1']],
          rightHandUKeys: [[0.0, [16.5, -35.0], 'c1'], [1.3, [15.2, -37.5], 'c1'], [3.0, [15.0, -37.0], 'c1']],
          weaponAngKeys: [[0.0, Math.PI + 0.18, 'c1'], [1.4, Math.PI + 0.11, 'c1'], [3.0, Math.PI + 0.12, 'c1']],
          tremorKeys: [[0.0, 0.55, 'c1'], [1.6, 0.15, 'c1'], [3.0, 0.0, 'c1']],
          phaseKeys: [[0.0, 'anticipation'], [1.1, 'action'], [2.2, 'settle']],
        },
      },
    }, 'rookie', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.30,
        blurPx: 6.5,
        draw: (c) => {
          drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.64, gateX: 0.18, showCohort: true, showRack: false });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          // Warm sun sliver visible to the left of the rookie before his shield closes it
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: sampleTrack(lt, [[0.0, 92, 'c1'], [3.0, 76, 'c1']], 84),
            gapCenterX: 0.355,
            wallY: 0.96,
            shieldScaleH: 0.56,
            drawNeighborShields: false,
            showSunSliver: true,
          });
          drawRomanMasterActor2D(c, rookiePose, { polish: true, seed: 11 });
        },
      },
      {
        depth: 1.16,
        blurPx: 3.5,
        draw: (c) => {
          // Over-shoulder foreground edge of neighbor's red scutum on screen-left
          shield(c, W * 0.14, H * 0.63, H * 0.72, {
            type: 'scutum',
            color: PAL.red,
            rim: PAL.gold,
            charge: 'wings',
            chargeColor: PAL.yellow,
            romanMasterPolish: true,
            rot: -0.02,
          });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH03 (5.50 - 9.00s): WIDE GEOGRAPHY — Full Roman training ground at dawn:
// castra gate/ramp on left, shield cohort with open gap on right, instructor spotting it.
// ============================================================================
registerShot('SH03', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (5.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH03', gt, {
      start: 5.5, end: 9.0, framingScale: 'wide_geography', purpose: 'establish_castra_and_line',
      zoomKeys: [[0.0, 1.01, 'c1'], [3.5, 1.08, 'c1']],
      cxKeys: [[0.0, 0.46, 'c1'], [3.5, 0.53, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.5, 0.51, 'c1']],
    });

    const instructorPose = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.39,
          rootXKeys: [[0.0, 0.20, 'c1'], [1.4, 0.225, 'c1'], [3.5, 0.225, 'hold']],
          rootYKeys: [[0.0, 0.875, 'c1'], [3.5, 0.875, 'hold']],
          leftFootXKeys: [[0.0, 0.186, 'c1'], [1.4, 0.210, 'c1'], [3.5, 0.210, 'hold']],
          rightFootXKeys: [[0.0, 0.214, 'c1'], [1.4, 0.242, 'c1'], [3.5, 0.242, 'hold']],
          lookKeys: [[0.0, 0.45, 'c1'], [1.2, 0.72, 'c1']],
          faceKeys: [[0.0, 'neutral'], [1.1, 'focused'], [2.4, 'determined']],
          shieldOffsetUKeys: [[0.0, [-13, -38], 'c1'], [3.5, [-14, -38], 'c1']],
          rightHandUKeys: [[0.0, [15, -36], 'c1'], [1.8, [20, -48], 'c1'], [3.5, [22, -52], 'c1']],
          weapon: 'none',
        },
      },
    }, 'instructor', { W, H });

    const rookieWide = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.38,
          xFrac: 0.695,
          yFrac: 0.885,
          flip: true,
          lookKeys: [[0.0, 0.35, 'c1'], [2.0, 0.65, 'c1']],
          faceKeys: [[0.0, 'worried'], [2.2, 'focused']],
          shieldOffsetUKeys: [[0.0, [-14, -37], 'c1'], [2.0, [-11, -37.5], 'c1'], [3.5, [-12, -37.5], 'c1']],
          weaponAngKeys: [[0.0, Math.PI + 0.16, 'c1'], [3.5, Math.PI + 0.12, 'c1']],
          tremorKeys: [[0.0, 0.35, 'c1'], [3.5, 0.2, 'c1']],
        },
      },
    }, 'rookie', { W, H });

    const neighborWide = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.38,
          xFrac: 0.585,
          yFrac: 0.885,
          flip: true,
          look: 0.4,
          face: 'determined',
          shieldOffsetU: [2.5, -38],
          shieldRot: 0.0,
          weaponAng: Math.PI + 0.08,
        },
      },
    }, 'neighbor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.22,
        blurPx: 2.0,
        draw: (c) => drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.65, sunX: 0.64, sunY: 0.33, seed: 17 }),
      },
      {
        depth: 0.55,
        blurPx: 0.8,
        draw: (c) => {
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.14, scale: 0.32 });
          drawRomanCohortLine2D(c, { globalT: gt }, { y: 0.72, hFrac: 0.145, x0: 0.40, x1: 0.82, count: 7, flip: true, seed: 71 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.65, chalkLineY: 0.885, seed: 23 });
          drawRomanTrainingRack2D(c, W * 0.11, H * 0.84, H * 0.19, { withPalus: false, spearCount: 3 });
          drawRomanTrainingRack2D(c, W * 0.89, H * 0.83, H * 0.20, { withPalus: true, spearCount: 4 });

          // Front shield-wall squad with sunlit gap between neighbor (0.585) and rookie (0.695)
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: 42,
            gapCenterX: 0.64,
            wallY: 0.885,
            shieldScaleH: 0.24,
            drawNeighborShields: false,
            showSunSliver: true,
          });
          for (let i = 0; i < 3; i++) {
            const fx = W * (0.435 + i * 0.05);
            soldier(c, fx, H * 0.885, H * 0.38, {
              preset: 'hastatus',
              flip: true,
              pose: 'stand',
              face: i === 1 ? 'focused' : 'determined',
              t: gt + i * 0.83,
              seed: 90 + i * 7,
              romanMasterPolish: true,
              armsAng: [-28, -45, 14, 10],
              weaponAng: Math.PI + 0.08,
              shield: { type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'lightning', chargeColor: PAL.yellow, x: 3, y: -38, s: 62, rot: 0 },
              lod: 'high',
            });
          }
          drawRomanMasterActor2D(c, neighborWide, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookieWide, { polish: true, seed: 11 });

          // Instructor on left holding wooden practice spear ready to test the gap
          drawRomanMasterActor2D(c, instructorPose, { polish: true, seed: 21 });
          const rh = instructorPose.rightHandWorld;
          const aimAng = sampleTrack(lt, [[0.0, Math.PI * 0.82, 'c1'], [2.0, Math.PI * 0.53, 'c1'], [3.5, Math.PI * 0.49, 'c1']], Math.PI * 0.52);
          drawWoodenPracticeSpear2D(c, rh[0], rh[1], H * 0.26, -aimAng);
        },
      },
    ]);
    vignette(g, 0.16);
  },
});

// ============================================================================
// SH04 (9.00 - 12.00s): BEAT — Low-angle profile of instructor launching
// harmless wooden practice spear strictly left-to-right across stage axis.
// ============================================================================
registerShot('SH04', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (9.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH04', gt, {
      start: 9.0, end: 12.0, framingScale: 'low_angle_profile', purpose: 'inciting_spear_launch',
      zoomKeys: [[0.0, 1.05, 'c1'], [0.85, 1.12, 'c1'], [1.35, 1.06, 'c1'], [3.0, 1.10, 'c1']],
      cxKeys: [[0.0, 0.42, 'c1'], [0.95, 0.40, 'c1'], [1.6, 0.54, 'c1'], [3.0, 0.58, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [3.0, 0.50, 'c1']],
    });

    const releaseT = 0.96;
    const instPose = romanActorAt(gt, {
      start: 9.0,
      end: 12.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.64,
          rootXKeys: [[0.0, 0.34, 'c1'], [0.70, 0.325, 'c1'], [1.02, 0.375, 'c1'], [1.6, 0.372, 'c1']],
          rootYKeys: [[0.0, 0.96, 'c1'], [3.0, 0.96, 'hold']],
          leftFootXKeys: [[0.0, 0.31, 'c1'], [0.7, 0.30, 'c1'], [1.02, 0.30, 'hold'], [3.0, 0.30, 'hold']],
          rightFootXKeys: [[0.0, 0.37, 'c1'], [0.65, 0.36, 'c1'], [0.95, 0.425, 'c1'], [3.0, 0.425, 'hold']],
          bodyRotKeys: [[0.0, -0.02, 'c1'], [0.72, -0.10, 'c1'], [1.02, 0.11, 'c1'], [1.65, 0.05, 'c1']],
          lookKeys: [[0.0, 0.65, 'c1'], [3.0, 0.78, 'c1']],
          faceKeys: [[0.0, 'focused'], [0.72, 'determined'], [1.3, 'sternNod']],
          shieldOffsetUKeys: [[0.0, [-15, -36], 'c1'], [0.95, [-18, -35], 'c1'], [1.6, [-14, -37], 'c1']],
          rightHandUKeys: [
            [0.0, [8.0, -46.0], 'c1'],
            [0.72, [-14.0, -58.0], 'c1'],
            [0.98, [22.5, -53.0], 'outCubic'],
            [1.45, [19.0, -44.0], 'c1'],
            [3.0, [16.5, -40.0], 'c1'],
          ],
          weapon: 'none',
          phaseKeys: [[0.0, 'anticipation'], [0.72, 'action'], [0.96, 'contact'], [1.35, 'settle']],
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 4.0,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.76, sunX: 0.76, sunY: 0.38, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.76, gateX: 0.16, scale: 0.38 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.76, chalkLineY: 0.96, seed: 29 });
          if (lt >= 0.88 && lt <= 1.75) {
            dustPuff(c, W * 0.425, H * 0.955, H * 0.085, (1 - (lt - 0.88) / 0.87) * 0.65, gt);
          }
          drawRomanMasterActor2D(c, instPose, { polish: true, seed: 21, shoeMode: 'side' });

          // Wooden practice spear: locked in instructor's right hand before releaseT, then flying ballistic left->right
          const spearLen = H * 0.42;
          if (lt <= releaseT) {
            const rh = instPose.rightHandWorld;
            const windAng = sampleTrack(lt, [[0.0, -Math.PI * 0.48, 'c1'], [0.72, -Math.PI * 0.54, 'c1'], [releaseT, -Math.PI * 0.49, 'c1']], -Math.PI * 0.5);
            drawWoodenPracticeSpear2D(c, rh[0], rh[1], spearLen, windAng, { smear: lt > 0.78 ? 0.45 : 0 });
          } else {
            const flyDt = lt - releaseT;
            const sx = instPose.rightHandWorld[0] + flyDt * W * 0.78;
            const sy = instPose.rightHandWorld[1] - flyDt * H * 0.06 + flyDt * flyDt * H * 0.045;
            if (sx < W * 1.35) {
              drawWoodenPracticeSpear2D(c, sx, sy, spearLen, -Math.PI * 0.49 + flyDt * 0.04, { smear: 0.78 });
            }
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH05 (12.00 - 15.00s): ACTION — Tracking shot as rookie plants sandal and
// shoves his red scutum leftward into the shield wall to seal the gap.
// ============================================================================
registerShot('SH05', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (12.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH05', gt, {
      start: 12.0, end: 15.0, framingScale: 'medium_full_tracking', purpose: 'foot_plant_and_shield_shove',
      zoomKeys: [[0.0, 1.06, 'c1'], [1.05, 1.14, 'c1'], [1.75, 1.18, 'c1'], [3.0, 1.15, 'c1']],
      cxKeys: [[0.0, 0.58, 'c1'], [1.65, 0.51, 'c1'], [3.0, 0.50, 'c1']],
      cyKeys: [[0.0, 0.54, 'c1'], [3.0, 0.53, 'c1']],
      impactImpulse: { atLocal: 1.65, dur: 0.22, ampPx: 6.0 },
    });

    const neighborPose = romanActorAt(gt, {
      start: 12.0,
      end: 15.0,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.58,
          xFrac: 0.41,
          yFrac: 0.93,
          flip: true,
          leftFootXKeys: [[0.0, 0.445, 'hold'], [3.0, 0.445, 'hold']],
          rightFootXKeys: [[0.0, 0.375, 'hold'], [3.0, 0.375, 'hold']],
          lookKeys: [[0.0, 0.45, 'c1'], [1.65, 0.25, 'c1']],
          faceKeys: [[0.0, 'determined'], [1.65, 'focused']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.65, 0.0, 'c1'], [1.78, -0.02, 'c1'], [2.2, 0.0, 'c1']],
          shieldOffsetUKeys: [[0.0, [3.0, -38.0], 'c1'], [3.0, [3.0, -38.0], 'hold']],
          shieldRot: 0.0,
          weaponAng: Math.PI + 0.12,
        },
      },
    }, 'neighbor', { W, H });

    const rookiePose = romanActorAt(gt, {
      start: 12.0,
      end: 15.0,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.58,
          flip: true,
          // Anticipation coil (0..0.45s) -> Lead sandal step & plant (0.45..1.02s) -> Shield shove & rear follow-plant (1.02..1.65s) -> Settle (1.65..3.0s)
          rootXKeys: [
            [0.0, 0.595, 'c1'],
            [0.45, 0.598, 'c1'],
            [1.02, 0.578, 'c1'],
            [1.65, 0.556, 'outCubic'],
            [1.85, 0.558, 'c1'],
            [3.0, 0.558, 'hold'],
          ],
          rootYKeys: [
            [0.0, 0.93, 'c1'],
            [0.45, 0.935, 'c1'],
            [1.02, 0.93, 'c1'],
            [1.65, 0.93, 'c1'],
            [3.0, 0.93, 'hold'],
          ],
          // Two-phase world-locked footwork within exact 28.3u anatomical leg reach (0.00px drift!)
          leftFootXKeys: [
            [0.0, 0.615, 'hold'],
            [1.05, 0.615, 'c1'],
            [1.58, 0.578, 'outCubic'],
            [3.0, 0.578, 'hold'],
          ],
          leftFootYKeys: [
            [0.0, 0.93, 'hold'],
            [1.05, 0.93, 'c1'],
            [1.30, 0.914, 'c1'],
            [1.58, 0.93, 'outCubic'],
            [3.0, 0.93, 'hold'],
          ],
          rightFootXKeys: [
            [0.0, 0.575, 'hold'],
            [0.45, 0.575, 'c1'],
            [1.02, 0.536, 'outCubic'],
            [3.0, 0.536, 'hold'],
          ],
          rightFootYKeys: [
            [0.0, 0.93, 'hold'],
            [0.45, 0.93, 'c1'],
            [0.74, 0.904, 'c1'],
            [1.02, 0.93, 'outCubic'],
            [3.0, 0.93, 'hold'],
          ],
          bodyRotKeys: [
            [0.0, 0.0, 'hold'],
            [3.0, 0.0, 'hold'],
          ],
          headNodKeys: [
            [0.0, -0.5, 'c1'],
            [0.45, -1.2, 'c1'],
            [1.65, 2.2, 'outCubic'],
            [2.10, 1.0, 'c1'],
            [3.0, 1.0, 'hold'],
          ],
          lookKeys: [[0.0, 0.65, 'c1'], [1.65, 0.55, 'c1']],
          faceKeys: [[0.0, 'shock'], [0.55, 'determined'], [1.65, 'focused']],
          shieldOffsetUKeys: [
            [0.0, [-13.0, -37.5], 'c1'],
            [0.50, [-15.0, -37.0], 'c1'],
            [1.65, [5.2, -38.0], 'outCubic'],
            [3.0, [4.6, -38.0], 'c1'],
          ],
          shieldRotKeys: [[0.0, 0.05, 'c1'], [1.65, 0.0, 'outCubic'], [3.0, 0.0, 'hold']],
          rightHandUKeys: [[0.0, [16.0, -36.0], 'c1'], [1.65, [12.5, -37.5], 'c1'], [3.0, [12.5, -37.5], 'hold']],
          weaponAngKeys: [[0.0, Math.PI + 0.15, 'c1'], [1.65, Math.PI - 0.14, 'c1'], [3.0, Math.PI - 0.14, 'hold']],
          phaseKeys: [[0.0, 'anticipation'], [0.50, 'action'], [1.65, 'contact'], [2.1, 'settle']],
        },
      },
    }, 'rookie', { W, H });

    const gapRemainingPx = sampleTrack(lt, [[0.0, 96, 'c1'], [0.50, 102, 'c1'], [1.65, 0, 'outCubic'], [3.0, 0, 'hold']], 0);

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.30,
        blurPx: 4.5,
        draw: (c) => drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.14, showCohort: true }),
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.66, chalkLineY: 0.93, seed: 23 });
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: gapRemainingPx,
            gapCenterX: 0.485,
            wallY: 0.93,
            shieldScaleH: 0.36,
            drawNeighborShields: false,
            showSunSliver: gapRemainingPx > 3,
          });

          // Sand dust burst right as front sandal plants at lt=1.02s
          if (lt >= 1.00 && lt <= 1.95) {
            dustPuff(c, W * 0.522, H * 0.932, H * 0.095, (1 - (lt - 1.00) / 0.95) * 0.75, gt);
          }

          drawRomanMasterActor2D(c, neighborPose, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookiePose, { polish: true, seed: 11, shoeMode: 'side' });

          // Incoming wooden practice spear streaking in from screen-left during final 0.42s before cut to insert
          if (lt >= 2.52) {
            const p = (lt - 2.52) / 0.48;
            const spX = lerp(-W * 0.08, W * 0.36, p);
            const spY = lerp(H * 0.61, H * 0.65, p);
            drawWoodenPracticeSpear2D(c, spX, spY, H * 0.32, -Math.PI * 0.48, { smear: 0.85 });
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH06 (15.00 - 18.50s): INSERT — Blunt wooden spear tip strikes the newly
// closed red/gold scutum rim at 24fps, compresses, and glances harmlessly aside.
// ============================================================================
registerShot('SH06', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (15.0 + lt);
    const W = E.W, H = E.H;
    const hitT = 0.58;
    const cam = camFor('SH06', gt, {
      start: 15.0, end: 18.5, framingScale: 'macro_physics_insert', purpose: 'wooden_tip_deflection',
      zoomKeys: [[0.0, 1.12, 'c1'], [hitT, 1.24, 'outCubic'], [1.4, 1.16, 'c1'], [3.5, 1.10, 'c1']],
      cxKeys: [[0.0, 0.47, 'c1'], [hitT, 0.51, 'c1'], [2.4, 0.46, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [hitT, 0.50, 'c1'], [2.4, 0.56, 'c1']],
      impactImpulse: { atLocal: hitT, dur: 0.26, ampPx: 9.5 },
    });

    // Shield recoil curve: rock-solid absorb (5.5px peak at hitT + 0.06s, damped back to 0)
    const recoilPx = lt < hitT
      ? 0
      : Math.max(0, Math.sin(Math.min(Math.PI, ((lt - hitT) / 0.24) * Math.PI)) * 7.5);

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 9.0,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.60, sunX: 0.52, sunY: 0.40, seed: 17 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.60, chalkLineY: 0.88, seed: 23 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          // Sealed crimson-and-gold scutum wall (gap = 0px!)
          const seamX = W * 0.53 + recoilPx;
          const shieldS = H * 0.94;
          const rx = shieldS * 0.33;
          shield(c, seamX - rx * 0.95, H * 0.56, shieldS, {
            type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'wings', chargeColor: PAL.yellow,
            romanMasterPolish: true, rot: -0.01,
          });
          shield(c, seamX + rx * 0.95, H * 0.56, shieldS, {
            type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'lightning', chargeColor: PAL.yellow,
            romanMasterPolish: true, rot: 0.012,
          });

          // Contact flash & wood-dust ring during 4 impact frames around hitT
          const hitContactX = seamX + 12;
          const hitContactY = H * 0.49;
          if (lt >= hitT - 0.02 && lt <= hitT + 0.36) {
            const k = clamp((lt - (hitT - 0.02)) / 0.38, 0, 1);
            for (let i = 0; i < 7; i++) {
              const ang = Math.PI * (0.62 + i * 0.13);
              const r0 = 14 + k * 54;
              const r1 = 30 + k * 92;
              line(c, [
                [hitContactX + Math.cos(ang) * r0, hitContactY + Math.sin(ang) * r0],
                [hitContactX + Math.cos(ang) * r1, hitContactY + Math.sin(ang) * r1],
              ], { lw: 4.5 * (1 - k), ink: i % 2 ? '#ffe596' : '#e6c58e', a: 1 - k });
            }
            dustPuff(c, hitContactX - 18, hitContactY, H * 0.09, (1 - k) * 0.72, gt);
          }

          // Wooden practice spear trajectory: fast approach -> 2-frame pad squash -> spinning glance bounce -> sand rest
          const spLen = H * 0.44;
          if (lt < hitT) {
            const k = clamp(lt / hitT, 0, 1);
            const tipX = lerp(W * 0.06, hitContactX, k);
            const tipY = lerp(H * 0.44, hitContactY, k);
            const ang = -Math.PI * 0.47;
            // Draw shaft so tip (+0.93L along local +Y) lands at (tipX, tipY)
            const hx = tipX + Math.sin(ang) * (spLen * 0.93);
            const hy = tipY - Math.cos(ang) * (spLen * 0.93);
            drawWoodenPracticeSpear2D(c, hx, hy, spLen, ang, { smear: 0.85 });
          } else if (lt <= hitT + 0.09) {
            // Squash contact frame on gold rim
            const ang = -Math.PI * 0.43;
            const hx = hitContactX + Math.sin(ang) * (spLen * 0.90);
            const hy = hitContactY - Math.cos(ang) * (spLen * 0.90);
            c.save();
            c.translate(hitContactX, hitContactY);
            c.scale(0.92, 1.06);
            c.translate(-hitContactX, -hitContactY);
            drawWoodenPracticeSpear2D(c, hx, hy, spLen, ang, { smear: 0.2 });
            c.restore();
          } else {
            const dt = lt - (hitT + 0.09);
            const landDt = 1.52;
            const bDt = Math.min(dt, landDt);
            const cxSp = hitContactX - spLen * 0.42 - bDt * W * 0.16;
            const cySp = hitContactY - spLen * 0.06 - bDt * H * 0.18 + bDt * bDt * H * 0.31;
            const spinAng = -Math.PI * 0.43 - bDt * 2.55;
            const settleAng = dt > landDt ? spinAng + Math.sin((dt - landDt) * 14) * 0.04 * Math.max(0, 1 - (dt - landDt)) : spinAng;
            drawWoodenPracticeSpear2D(c, cxSp, cySp, spLen, settleAng, { smear: dt < landDt ? 0.32 : 0 });
            if (dt >= landDt && dt <= landDt + 0.55) {
              dustPuff(c, cxSp, cySp + 16, H * 0.065, (1 - (dt - landDt) / 0.55) * 0.55, gt);
            }
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH07 (18.50 - 23.00s): PAYOFF — Unbroken shield line holds; camera pushes in
// as drill instructor narrows his eyes (8-frame intentional hold) then nods once.
// ============================================================================
registerShot('SH07', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (18.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH07', gt, {
      start: 18.5, end: 23.0, framingScale: 'wide_to_medium_payoff', purpose: 'wall_holds_instructor_evaluates',
      zoomKeys: [[0.0, 1.02, 'c1'], [1.5, 1.18, 'c1'], [3.2, 1.36, 'c1'], [4.5, 1.38, 'c1']],
      cxKeys: [[0.0, 0.50, 'c1'], [1.6, 0.36, 'c1'], [3.2, 0.29, 'c1'], [4.5, 0.29, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [3.2, 0.48, 'c1'], [4.5, 0.48, 'c1']],
    });

    const instPayoff = romanActorAt(gt, {
      start: 18.5,
      end: 23.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.48,
          xFrac: 0.26,
          yFrac: 0.91,
          lookKeys: [[0.0, 0.65, 'c1'], [2.25, 0.65, 'hold'], [4.5, 0.62, 'c1']],
          faceKeys: [[0.0, 'determined'], [1.65, 'focused'], [2.65, 'sternNod']],
          // Intentional 8-frame hold [2.25..2.58s], followed by single crisp downward nod [2.65..3.45s]
          headNodKeys: [
            [0.0, 0.0, 'c1'],
            [2.25, 0.0, 'hold'],
            [2.58, 0.0, 'hold'],
            [2.95, 3.4, 'c1'],
            [3.45, 0.2, 'c1'],
            [4.5, 0.2, 'hold'],
          ],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [2.25, 0.02, 'hold'], [2.58, 0.02, 'hold'], [2.95, 0.04, 'c1'], [3.5, 0.02, 'c1']],
          shieldOffsetU: [-14, -38],
          rightHandU: [15.5, -36.5],
          weapon: 'pilum',
          weaponAng: Math.PI + 0.14,
          phaseKeys: [[0.0, 'settle'], [2.25, 'hold'], [2.60, 'reaction'], [3.5, 'settle']],
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 2.5,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.66, sunX: 0.68, sunY: 0.32, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.13, scale: 0.32 });
        },
      },
      {
        depth: 0.72,
        blurPx: 1.2,
        draw: (c) => {
          // Desynchronized background Roman squad holding locked crimson shield wall (zero gap!)
          drawRomanCohortLine2D(c, { globalT: gt }, {
            y: 0.84, hFrac: 0.34, x0: 0.48, x1: 0.88, count: 6, flip: true, shieldXU: 4.5, seed: 107,
          });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.66, chalkLineY: 0.91, seed: 23 });
          // Deflected wooden practice spear resting harmlessly on the sand in front of the wall
          drawWoodenPracticeSpear2D(c, W * 0.46, H * 0.915, H * 0.22, -Math.PI * 0.52);
          drawRomanMasterActor2D(c, instPayoff, { polish: true, seed: 21 });
        },
      },
    ]);
    vignette(g, 0.17);
  },
});

// ============================================================================
// SH08 (23.00 - 26.50s): TWIST — Rookie exhales in relief, then tugs his own
// spear and realizes it is caught in his neighbor's leather shield strap!
// ============================================================================
registerShot('SH08', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (23.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH08', gt, {
      start: 23.0, end: 26.5, framingScale: 'medium_two_shot', purpose: 'comic_spear_strap_twist',
      zoomKeys: [[0.0, 1.18, 'c1'], [1.2, 1.10, 'c1'], [3.5, 1.08, 'c1']],
      cxKeys: [[0.0, 0.54, 'c1'], [1.4, 0.51, 'c1'], [3.5, 0.50, 'c1']],
      cyKeys: [[0.0, 0.51, 'c1'], [3.5, 0.52, 'c1']],
    });

    const tugPulse = (lt >= 1.02 && lt <= 1.42 ? Math.sin(((lt - 1.02) / 0.40) * Math.PI * 2) : 0)
      + (lt >= 1.98 && lt <= 2.38 ? Math.sin(((lt - 1.98) / 0.40) * Math.PI * 2) * 0.8 : 0);

    const neighborTwist = romanActorAt(gt, {
      start: 23.0,
      end: 26.5,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.68,
          xFrac: 0.37,
          yFrac: 1.03,
          lookKeys: [[0.0, 0.15, 'c1'], [1.25, 0.72, 'c1'], [3.5, 0.75, 'hold']],
          faceKeys: [[0.0, 'determined'], [1.30, 'bored']],
          headRotKeys: [[0.0, 0.0, 'c1'], [1.35, 0.06, 'c1'], [3.5, 0.06, 'hold']],
          shieldOffsetUKeys: [[0.0, [5.0, -38.0], 'c1'], [3.5, [5.0 + tugPulse * 1.1, -38.0], 'c1']],
          shieldRot: -0.01 + tugPulse * 0.025,
          rightHandU: [-14.0, -36.0],
          weapon: 'none',
        },
      },
    }, 'neighbor', { W, H });

    const rookieTwist = romanActorAt(gt, {
      start: 23.0,
      end: 26.5,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.68,
          xFrac: 0.62,
          yFrac: 1.03,
          flip: true,
          lookKeys: [[0.0, 0.10, 'c1'], [0.85, 0.15, 'c1'], [1.20, 0.72, 'c1'], [3.5, 0.68, 'c1']],
          faceKeys: [[0.0, 'exhale'], [0.95, 'surprised'], [1.45, 'awkward']],
          headNodKeys: [[0.0, 2.2, 'c1'], [0.75, 3.0, 'c1'], [1.15, -0.6, 'c1'], [1.8, 0.8, 'c1']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.15, -0.03 + tugPulse * 0.03, 'c1'], [2.6, -0.015, 'c1']],
          shieldOffsetU: [3.5, -38.0],
          shieldRot: 0.01,
          rightHandUKeys: [
            [0.0, [13.5, -36.5], 'c1'],
            [1.05, [16.8, -41.5], 'c1'],
            [1.35, [14.2, -38.0], 'c1'],
            [2.05, [17.2, -42.0], 'c1'],
            [2.45, [14.8, -38.5], 'c1'],
          ],
          weapon: 'none',
          phaseKeys: [[0.0, 'settle'], [0.95, 'action'], [1.45, 'reaction']],
        },
      },
    }, 'rookie', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.28,
        blurPx: 6.0,
        draw: (c) => drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.64, gateX: 0.16, showCohort: true }),
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.64, chalkLineY: 0.96, seed: 23 });
          drawRomanMasterActor2D(c, neighborTwist, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookieTwist, { polish: true, seed: 11 });

          // Visible leather strap loop on neighbor's right scutum edge + rookie's spear snagged through it!
          const strapX = neighborTwist.shieldGrip.rimRightWorld[0] - 8 + tugPulse * 5;
          const strapY = neighborTwist.shieldGrip.shieldCenterWorld[1] - 48;
          const rh = rookieTwist.rightHandWorld;
          const snaggedAng = Math.atan2(rh[0] - strapX, strapY - rh[1]);
          weapon(c, 'spear', rh[0], rh[1], rookieTwist.actorH * 0.66, snaggedAng, { lw: 3.8 });
          shape(
            c,
            (ctx) => {
              ctx.moveTo(strapX - 14, strapY - 12);
              ctx.quadraticCurveTo(strapX + 18, strapY, strapX - 12, strapY + 14);
            },
            { fill: null, lw: 6.5, ink: PAL.leather }
          );
          circ(c, strapX - 12, strapY - 12, 4, { fill: PAL.gold, lw: 2 });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH09 (26.50 - 30.00s): OUTRO / LOOP — Unsmiling instructor gives one crisp
// nod, gliding smoothly to the tightly sealed red scutum gap motif (loop-ready).
// ============================================================================
registerShot('SH09', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (26.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH09', gt, {
      start: 26.5, end: 30.0, framingScale: 'motif_return_close', purpose: 'deadpan_nod_and_closed_wall_loop',
      zoomKeys: [[0.0, 1.06, 'c1'], [1.8, 1.14, 'c1'], [3.5, 1.22, 'c1']],
      cxKeys: [[0.0, 0.36, 'c1'], [1.7, 0.48, 'c1'], [3.5, 0.52, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.5, 0.51, 'c1']],
    });

    const instOutro = romanActorAt(gt, {
      start: 26.5,
      end: 30.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.62,
          xFrac: 0.25,
          yFrac: 0.98,
          look: 0.62,
          face: 'sternNod',
          headNodKeys: [[0.0, 0.0, 'c1'], [0.85, 0.0, 'hold'], [1.18, 3.8, 'c1'], [1.62, 0.2, 'c1'], [3.5, 0.2, 'hold']],
          shieldOffsetU: [-14, -38],
          rightHandU: [15.5, -36.5],
          weapon: 'pilum',
          weaponAng: Math.PI + 0.14,
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.26,
        blurPx: 5.5,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.60, sunX: 0.53, sunY: 0.42, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.60, gateX: 0.12, scale: 0.28 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.60, chalkLineY: 0.88, seed: 23 });
        },
      },
      {
        depth: 0.82,
        blurPx: 0.8,
        draw: (c) => {
          drawRomanMasterActor2D(c, instOutro, { polish: true, seed: 21 });
        },
      },
      {
        depth: 1.06,
        blurPx: 0,
        draw: (c) => {
          // Return to SH01 foreground red scutum motif — now locked flush with 0px gap!
          const wallX = lerp(W * 0.74, W * 0.56, sampleTrack(lt, [[0.0, 0.0, 'c1'], [2.2, 1.0, 'c1'], [3.5, 1.0, 'hold']], 1.0));
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: 0,
            gapCenterX: wallX / W,
            wallY: 1.05,
            shieldScaleH: 0.90,
            drawNeighborShields: true,
            rookieTremorPx: 0,
            rookieDropPx: 0,
            rookieRot: 0.008,
            showSunSliver: false,
            showNeighborStrap: true,
            snaggedSpear: true,
          });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});
