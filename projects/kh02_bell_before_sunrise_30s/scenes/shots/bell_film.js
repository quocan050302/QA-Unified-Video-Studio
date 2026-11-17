// bell_film.js — Custom 2D Shot Renderer for 'THE BELL THAT RANG TOO EARLY' (30.000s, 720 frames @ 24fps).
// Pure Canvas2D. Consumes live story/{style_profile,character_bible,environment_bible,props,camera_beats,storyboard}.json via E.kh02.
// Every shot is a pure deterministic function of (lt, info.globalT) — random frame order renders produce identical RGBA bytes.

import { E, clamp, lerp, ease, registerShot, speaking } from '/engine/core.js';
import {
  OUT,
  alpha,
  vignette,
  strokeTapered2D,
  fillCelShadedShape2D,
  drawSquireCinematic2DActor,
  drawPipGoat2D,
  drawLayeredRomanEnvironment2D,
  evaluateBellRigStateAt,
  resolve2DCameraAt,
  evaluate2DActionAt,
} from '/packs/squire/pack.js';

function requireManifests() {
  if (!E.kh02 || !E.kh02.styleProfile || !E.kh02.characterBible || !E.kh02.environmentBible || !E.kh02.cameraBeats || !E.kh02.storyboardSpec || !E.kh02.propsSpec) {
    throw new Error('KH02_MANIFEST_MISSING: story/{style_profile,character_bible,environment_bible,props,camera_beats,storyboard}.json must be loaded into E.kh02');
  }
  if (E.kh02.styleProfile.style_id !== 'squire_cinematic_2d.v1') {
    throw new Error(`KH02_STYLE_MISMATCH: unexpected style_id=${E.kh02.styleProfile.style_id}`);
  }
  return E.kh02;
}

function camFor(shotId, lt, dur) {
  const kh = requireManifests();
  const beat = (kh.cameraBeats.shots || {})[shotId] || {};
  return resolve2DCameraAt(lt, dur, beat);
}

// ======================================================================================
// S01 [0.0 - 3.0s]: Dramatic close-up of PIP nudging loose bell rope; bell blurred far behind in 2D.
// Strong action hook in first 0.5s; zero title-card stall.
// ======================================================================================
registerShot('S01', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S01', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    // Immediate hook in first 0.5s: Pip lunges snout into coiled hemp rope at t=0.05..0.48s, then playful second tug at 1.4..2.4s
    const hookWave = lt < 0.9
      ? Math.sin(clamp(lt / 0.85, 0, 1) * Math.PI)
      : lt < 1.35
        ? 0.15
        : Math.sin(clamp((lt - 1.35) / 1.25, 0, 1) * Math.PI);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_lower_arch',
      globalT: gt,
      rigState: rig,
      blurBackBell: 8.5,
      drawStageActors: (c, anc) => {
        const ropeLoop = anc.ropeFloorLoopWorld || [1110, 835];
        const goatX = ropeLoop[0] - 218 + hookWave * 16;
        const goatY = 898;
        drawPipGoat2D(c, goatX, goatY, 390, {
          action: hookWave > 0.18 ? 'rope_nudge' : 'curious_tilt',
          phase: hookWave,
          t: gt,
        });
        // Crisp 2D hemp motion arcs on active nudge
        if (hookWave > 0.45) {
          for (let i = 0; i < 2; i++) {
            strokeTapered2D(
              c,
              [[ropeLoop[0] + 24 + i * 14, ropeLoop[1] - 32], [ropeLoop[0] + 30 + i * 14, ropeLoop[1] + 18]],
              { lw: 3.4, ink: alpha('#ffe1a8', (hookWave - 0.4) * 1.1) }
            );
          }
        }
      },
    });
    vignette(g, 0.20, '#191322');
  },
});

// ======================================================================================
// S02 [3.0 - 6.5s]: Medium two-shot: TAVI notices swaying rope & Pip; pupils snap to bell;
// readable expression shift & body gesture; world-coordinate continuity of rope on right.
// ======================================================================================
registerShot('S02', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S02', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    // Phase 1 (0..0.55s): calm watchful -> Phase 2 (0.55..1.25s): sharp pupil snap & shock -> Phase 3 (1.25..3.5s): anxious lean toward rope
    const snapK = ease.out(clamp((lt - 0.48) / 0.28, 0, 1));
    const readyK = ease.inOut(clamp((lt - 1.55) / 1.75, 0, 1));
    const expr = lt < 0.50 ? 'calm_watchful' : lt < 1.55 ? 'wide_shock' : 'anxious_alert';

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_wide_interior',
      globalT: gt,
      rigState: rig,
      drawStageActors: (c) => {
        const taviX = lerp(635, 705, readyK);
        const taviY = 950;
        drawSquireCinematic2DActor(c, taviX, taviY, 495, {
          castId: 'TAVI',
          view: 'three_quarter',
          expression: expr,
          pupilX: lerp(0.05, 0.88, snapK),
          pupilY: lerp(0.0, -0.58, snapK),
          spineLean: lerp(0.0, -0.08, snapK) + readyK * 0.19,
          secondaryLag: readyK * 0.45,
          leftFootU: [-6.5, 0],
          rightFootU: [lerp(6.2, 13.5, readyK), 0],
          armAngles: [
            lerp(16, 62, snapK),
            lerp(18, 52, snapK),
            lerp(20, 84, snapK) - readyK * 14,
            lerp(18, 42, snapK),
          ],
          rightHandPose: lt < 0.50 ? 'relaxed' : lt < 1.65 ? 'open_recoil' : 'point_alert',
          leftHandPose: lt < 0.50 ? 'relaxed' : 'open_recoil',
          t: gt,
        });

        // Pip at same right-side rope world coordinate as S01!
        drawPipGoat2D(c, 1185, 950, 245, {
          flip: true,
          action: 'curious_tilt',
          phase: 0.35 + Math.sin(lt * 2.4) * 0.15,
          t: gt,
        });
      },
    });
    vignette(g, 0.19, '#191322');
  },
});

// ======================================================================================
// S03 [6.5 - 10.0s]: Artist-authored 2D low-angle close of rope slipping through hand:
// anticipate/reach (0..1.05s) -> taut pull (1.05..2.05s) -> slip & recoil (2.05..3.5s).
// ======================================================================================
registerShot('S03', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S03', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    const act = evaluate2DActionAt(lt, [
      { start: 0.0, end: 1.05, name: 'anticipate_reach', from: 0.0, to: 1.0, ease: 'out' },
      { start: 1.05, end: 2.05, name: 'pull_strain', from: 1.0, to: 2.0, ease: 'inOut' },
      { start: 2.05, end: 3.50, name: 'slip_recoil', from: 2.0, to: 3.0, ease: 'out' },
    ]);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_low_angle',
      globalT: gt,
      rigState: rig,
      drawStageActors: (c, anc) => {
        const ropeAnchor = anc.ropeGripWorld || [1115, 690];
        const h = 840;
        let actorX, actorY, expr, handPose, lean, rWorld, lWorld;

        if (lt <= 1.05) {
          const k = ease.out(lt / 1.05);
          actorX = lerp(ropeAnchor[0] - 320, ropeAnchor[0] - 205, k);
          actorY = lerp(1320, 1250, k);
          lean = lerp(0.18, 0.04, k);
          expr = k < 0.7 ? 'determined_climb' : 'strained_pull';
          handPose = k < 0.78 ? 'open_recoil' : 'rope_grip';
          const gx = lerp(actorX + 145, ropeAnchor[0], k);
          const gy = lerp(actorY - 420, ropeAnchor[1], k);
          rWorld = [gx, gy, -1];
          lWorld = [gx - 8, gy + 34, 1];
        } else if (lt <= 2.05) {
          const k = ease.inOut((lt - 1.05) / 1.0);
          actorX = lerp(ropeAnchor[0] - 205, ropeAnchor[0] - 215, k);
          actorY = lerp(1250, 1272, k);
          lean = lerp(0.04, -0.05, k);
          expr = 'strained_pull';
          handPose = 'rope_grip';
          rWorld = [ropeAnchor[0], ropeAnchor[1], -1];
          lWorld = [ropeAnchor[0] - 6, ropeAnchor[1] + 34, 1];
        } else {
          const k = ease.out(clamp((lt - 2.05) / 1.15, 0, 1));
          actorX = lerp(ropeAnchor[0] - 215, ropeAnchor[0] - 345, k);
          actorY = lerp(1272, 1345, k);
          lean = lerp(-0.05, -0.22, k);
          expr = 'wide_shock';
          handPose = 'open_recoil';
          const gx = lerp(ropeAnchor[0], actorX + 105, k);
          const gy = lerp(ropeAnchor[1], actorY - 360, k);
          rWorld = [gx, gy, -1];
          lWorld = [gx - 55, gy + 24, 1];

          // Crisp 2D slip friction streaks along rope when rope slips free
          if (k < 0.55) {
            for (let s = -1; s <= 1; s += 2) {
              strokeTapered2D(
                c,
                [[ropeAnchor[0] + s * 22, ropeAnchor[1] + 40], [ropeAnchor[0] + s * 26, ropeAnchor[1] - 65]],
                { lw: 4.0, ink: alpha('#fff0c8', (0.6 - k) * 1.4) }
              );
            }
          }
        }

        drawSquireCinematic2DActor(c, actorX, actorY, h, {
          castId: 'TAVI',
          view: 'three_quarter',
          expression: expr,
          pupilX: 0.72,
          pupilY: -0.68,
          spineLean: lean,
          secondaryLag: act.phaseName === 'slip_recoil' ? -0.8 : 0.4,
          rightHandWorldTarget: rWorld,
          leftHandWorldTarget: lWorld,
          rightHandPose: handPose,
          leftHandPose: handPose,
          t: gt,
        });
      },
    });
    vignette(g, 0.22, '#181220');
  },
});

// ======================================================================================
// S04 [10.0 - 13.5s]: Wider tower interior: heavy bronze bell swings rhythmically,
// 5 layered planes show real 2D parallax; Tavi dashes toward stairwell door; bounded push-in.
// ======================================================================================
registerShot('S04', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S04', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_wide_interior',
      globalT: gt,
      rigState: rig,
      drawStageActors: (c) => {
        // Tavi reacts to swinging bell above (0..0.8s), then sprints left-to-right across stone floor toward stairwell!
        const dashK = ease.inOut(clamp((lt - 0.65) / 2.65, 0, 1));
        const tx = lerp(690, 1460, dashK);
        const stride = dashK * 3.2;
        const f = stride % 1;
        const lFootX = lt < 0.65 ? -6 : lerp(12, -14, clamp(f * 2, 0, 1));
        const lFootY = lt < 0.65 ? 0 : (f > 0.5 ? -Math.sin((f - 0.5) * 2 * Math.PI) * 7 : 0);
        const rFootX = lt < 0.65 ? 8 : lerp(-14, 12, clamp(f * 2, 0, 1));
        const rFootY = lt < 0.65 ? 0 : (f <= 0.5 ? -Math.sin(f * 2 * Math.PI) * 7 : 0);

        drawSquireCinematic2DActor(c, tx, 950, 445, {
          castId: 'TAVI',
          view: lt < 0.65 ? 'three_quarter' : 'profile',
          expression: lt < 0.65 ? 'wide_shock' : 'determined_climb',
          pupilX: 0.75,
          pupilY: lt < 0.65 ? -0.7 : -0.25,
          spineLean: lt < 0.65 ? -0.06 : 0.18,
          secondaryLag: lt < 0.65 ? 0.1 : 0.9,
          leftFootU: [lFootX, lFootY],
          rightFootU: [rFootX, rFootY],
          armAngles: lt < 0.65
            ? [65, 50, 75, 45]
            : [Math.sin(stride * Math.PI * 2) * 48, 68, -Math.sin(stride * Math.PI * 2) * 48, 68],
          rightHandPose: lt < 0.65 ? 'open_recoil' : 'rope_grip',
          leftHandPose: 'rope_grip',
          t: gt,
        });

        // Pip watches innocently beside rope coil
        drawPipGoat2D(c, 1170, 950, 235, {
          flip: true,
          action: 'curious_tilt',
          phase: 0.5,
          t: gt,
        });
      },
    });
    vignette(g, 0.20, '#181220');
  },
});

// ======================================================================================
// S05 [13.5 - 17.5s]: Side view TAVI running up tower stairs (planted-sandal world lock -> ZERO foot skate!),
// scarf & forelock secondary action, tracking 2D camera, non-looping progressive 6-step ascent!
// ======================================================================================
registerShot('S05', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S05', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'tower_stairwell_ascent',
      globalT: gt,
      rigState: rig,
      drawStageActors: (c, anc) => {
        const stairs = anc.stairs;
        // Continuous non-looping ascent from step 1 to step 7 across 4.0s (6 distinct step transitions!)
        const totalSteps = 6.0;
        const uProg = clamp(lt / info.dur, 0, 0.999) * totalSteps;
        const stepIdx = Math.floor(uProg); // 0..5 -> planted on stairs[1 + stepIdx]
        const frac = uProg - stepIdx;      // 0..1 within single step climb

        const plantedStep = stairs[1 + stepIdx];
        const nextStep = stairs[2 + stepIdx];
        const prevStep = stairs[Math.max(0, stepIdx)];

        // Hip vaults smoothly from plantedStep toward nextStep with natural climb arc
        const vaultK = ease.inOut(frac);
        const actorX = lerp(plantedStep.treadX - 10, nextStep.treadX - 10, vaultK);
        const actorY = lerp(plantedStep.treadY, nextStep.treadY, vaultK) - Math.sin(frac * Math.PI) * 14;

        const h = 435, u = h / 100;
        // PLANTED FOOT WORLD LOCK: stance foot stays at EXACT world [plantedStep.treadX, plantedStep.treadY]!
        const stanceWorld = [plantedStep.treadX + 4, plantedStep.treadY];
        // Swing foot lifts cleanly off prevStep in parabolic arc and lands on nextStep!
        const swingK = ease.inOut(frac);
        const swingWorld = [
          lerp(prevStep.treadX + 4, nextStep.treadX + 4, swingK),
          lerp(prevStep.treadY, nextStep.treadY, swingK) - Math.sin(frac * Math.PI) * 46,
        ];

        const evenStride = (stepIdx % 2 === 0);
        const leftWorld = evenStride ? stanceWorld : swingWorld;
        const rightWorld = evenStride ? swingWorld : stanceWorld;

        // Progressive fatigue/effort across the 4s climb (non-identical across time!)
        const expr = stepIdx < 2 ? 'anxious_alert' : stepIdx < 4 ? 'determined_climb' : 'strained_pull';
        const lean = lerp(0.15, 0.24, lt / info.dur) + Math.sin(frac * Math.PI) * 0.03;
        const armSwing = (evenStride ? 1 : -1) * Math.cos(frac * Math.PI) * 46;

        drawSquireCinematic2DActor(c, actorX, actorY, h, {
          castId: 'TAVI',
          view: 'profile',
          showBothArmsInProfile: true,
          expression: expr,
          pupilX: 0.85,
          pupilY: -0.38,
          spineLean: lean,
          secondaryLag: 0.72 + (lt / info.dur) * 0.42 + Math.sin(frac * Math.PI) * 0.18,
          leftFootWorld: leftWorld,
          rightFootWorld: rightWorld,
          armAngles: [-armSwing + 18, 68, armSwing + 22, 72],
          rightHandPose: 'rope_grip',
          leftHandPose: 'rope_grip',
          t: gt,
        });
      },
    });
    vignette(g, 0.20, '#181220');
  },
});

// ======================================================================================
// S06 [17.5 - 23.0s]: Two motivated framings across internal cut at lt = 1.80s (globalT = 19.30s):
//   S06a [17.5 - 19.3s]: Medium catwalk view — Tavi lunges onto oak catwalk & catches iron clapper at 18.65s!
//   S06b [19.3 - 23.0s]: Tight close-up — Leather-wrapped hands hold clapper bulb millimeters from bronze rim;
//                        dramatic silence; eyes shift from strained effort to breathless relief!
// ======================================================================================
registerShot('S06', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const isCloseup = lt >= 1.80;
    const cam = isCloseup
      ? resolve2DCameraAt(lt - 1.80, info.dur - 1.80, { z0: 1.06, z1: 1.15, x0: -12, x1: 8, y0: -6, y1: -16, ease: 'sine' })
      : camFor('S06', lt, 1.80);
    const rig = evaluateBellRigStateAt(gt);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_catwalk_clapper',
      closeupClapper: isCloseup,
      globalT: gt,
      rigState: rig,
      drawStageActors: (c, anc) => {
        const bulb = anc.bell.clapperBulbWorld;
        if (!isCloseup) {
          // S06a: Medium framing on upper oak catwalk — Tavi reaches up & catches clapper at lt=1.15s (gt=18.65s)
          const catchK = ease.out(clamp(lt / 1.15, 0, 1));
          const h = 565;
          const actorX = lerp(anc.bell.pivotWorld[0] - 250, bulb[0] - 88, catchK);
          const actorY = anc.catwalkY - 12;
          const handGoalX = lerp(actorX + 95, bulb[0], catchK);
          const handGoalY = lerp(actorY - 310, bulb[1], catchK);
          drawSquireCinematic2DActor(c, actorX, actorY, h, {
            castId: 'TAVI',
            view: 'three_quarter',
            expression: lt < 1.15 ? 'determined_climb' : 'strained_pull',
            pupilX: 0.72,
            pupilY: -0.52,
            spineLean: lerp(0.18, 0.05, catchK),
            secondaryLag: (1 - catchK) * 0.75,
            leatherWraps: true,
            leftFootU: [-8.5, 0],
            rightFootU: [10.5, 0],
            rightHandWorldTarget: [handGoalX, handGoalY, -1],
            leftHandWorldTarget: [handGoalX - 10, handGoalY + 14, 1],
            rightHandPose: lt < 1.05 ? 'open_recoil' : 'pin_catch',
            leftHandPose: lt < 1.05 ? 'open_recoil' : 'pin_catch',
            t: gt,
          });
        } else {
          // S06b: Tight close-up — hands locked onto clapper bulb; expression transitions strained_pull -> breathless_relief!
          const subLt = lt - 1.80;
          const reliefK = ease.inOut(clamp((subLt - 0.85) / 0.9, 0, 1));
          const breathBob = Math.sin(subLt * 2.4) * 1.4;
          const h = 790;
          const actorX = bulb[0] - 118;
          const actorY = anc.catwalkY + 85;
          drawSquireCinematic2DActor(c, actorX, actorY, h, {
            castId: 'TAVI',
            view: 'three_quarter',
            expression: subLt < 0.95 ? 'strained_pull' : 'breathless_relief',
            pupilX: lerp(0.68, 0.22, reliefK),
            pupilY: lerp(-0.42, 0.12, reliefK),
            bobU: breathBob * 0.25,
            leatherWraps: true,
            rightHandWorldTarget: [bulb[0], bulb[1], -1],
            leftHandWorldTarget: [bulb[0] - 12, bulb[1] + 16, 1],
            rightHandPose: 'pin_catch',
            leftHandPose: 'pin_catch',
            t: gt,
          });
        }
      },
    });
    vignette(g, 0.23, '#14101d');
  },
});

// ======================================================================================
// S07 [23.0 - 26.5s]: Surprise close-up of PIP sneezing!
// 2D anticipation inhale squash (0..1.85s) -> explosive sneeze stretch (1.85..3.5s) yanking rope!
// ======================================================================================
registerShot('S07', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const cam = camFor('S07', lt, info.dur);
    const rig = evaluateBellRigStateAt(gt);

    drawLayeredRomanEnvironment2D(g, cam, {
      view: 'belfry_lower_arch',
      globalT: gt,
      rigState: rig,
      blurBackBell: 7.5,
      drawStageActors: (c, anc) => {
        const ropeLoop = anc.ropeFloorLoopWorld || [1110, 835];
        let action = 'curious_tilt', phase = 0.4;
        if (lt < 0.45) {
          action = 'curious_tilt';
          phase = lt / 0.45;
        } else if (lt < 1.85) {
          action = 'sneeze_anticipation';
          phase = (lt - 0.45) / 1.40;
        } else {
          action = 'sneeze_burst';
          phase = clamp((lt - 1.85) / 1.2, 0, 1);
        }

        // Drifting golden dust mote tickling Pip's nose right before sneeze!
        if (lt < 1.85) {
          const mx = lerp(ropeLoop[0] - 40, ropeLoop[0] - 92, clamp(lt / 1.6, 0, 1));
          const my = lerp(640, 692, clamp(lt / 1.6, 0, 1)) + Math.sin(lt * 7) * 8;
          fillCelShadedShape2D(c, (cc) => cc.arc(mx, my, 5.5, 0, Math.PI * 2), {
            fill: '#ffe6a8',
            lw: 2.0,
          });
        }

        drawPipGoat2D(c, ropeLoop[0] - 222, 902, 425, {
          action,
          phase,
          t: gt,
        });
      },
    });
    vignette(g, 0.20, '#191322');
  },
});

// ======================================================================================
// S08 [26.5 - 30.0s]: Payoff wide of courtyard residents (LYRA & MARCUS) waking to the early bell
// (26.5..28.35s), followed by a fast comic cut to TAVI's deadpan face (28.35..30.0s)!
// ======================================================================================
registerShot('S08', {
  draw(g, lt, info) {
    requireManifests();
    const gt = info.globalT;
    const rig = evaluateBellRigStateAt(gt);
    const isDeadpanCut = lt >= 1.85;

    if (!isDeadpanCut) {
      const cam = camFor('S08', lt, 1.85);
      const shutterK = ease.outBack(clamp((lt - 0.12) / 0.48, 0, 1));
      drawLayeredRomanEnvironment2D(g, cam, {
        view: 'hilltop_courtyard_wide',
        globalT: gt,
        rigState: rig,
        shutterOpenK: clamp(shutterK, 0, 1.08),
        drawStageActors: (c, anc) => {
          // Elder Bell-Mistress LYRA popping out of upper balcony shutter glaring up at bell tower!
          if (lt > 0.15) {
            const popK = ease.out(clamp((lt - 0.15) / 0.45, 0, 1));
            const [bx, by] = anc.balconyWindowWorld;
            c.save();
            c.beginPath();
            c.rect(bx - 105, by - 190, 210, 190);
            c.clip();
            drawSquireCinematic2DActor(c, bx, lerp(by + 210, by + 132, popK), 360, {
              castId: 'LYRA',
              view: 'front',
              expression: lt < 0.75 ? 'startled_gasp' : 'grumpy_glare',
              pupilX: -0.78,
              pupilY: -0.52,
              armAngles: [lerp(20, 68, popK), 46, lerp(20, 78, popK), 42],
              rightHandPose: 'point_alert',
              leftHandPose: 'palm_raised_react',
              t: gt,
            });
            c.restore();
          }

          // Courtyard resident MARCUS startled awake below!
          const reactK = ease.out(clamp(lt / 0.55, 0, 1));
          drawSquireCinematic2DActor(c, lerp(1040, 985, reactK), anc.courtyardGroundY + 36, 420, {
            castId: 'CITIZEN_A',
            view: 'three_quarter',
            flip: true,
            expression: lt < 0.65 ? 'wide_shock' : 'anxious_alert',
            pupilX: 0.75,
            pupilY: -0.62,
            spineLean: lerp(0.0, -0.10, reactK),
            armAngles: [lerp(18, 82, reactK), 48, lerp(22, 92, reactK), 42],
            rightHandPose: 'open_recoil',
            leftHandPose: 'open_recoil',
            t: gt,
          });
        },
      });
    } else {
      // Fast comic payoff cut (28.35..30.0s): Close on TAVI's deadpan disbelief face as bell vibrates!
      const subLt = lt - 1.85;
      const cam = resolve2DCameraAt(subLt, info.dur - 1.85, { z0: 1.12, z1: 1.14, x0: 0, x1: 0, y0: -8, y1: -8 });
      drawLayeredRomanEnvironment2D(g, cam, {
        view: 'belfry_catwalk_clapper',
        closeupClapper: true,
        globalT: gt,
        rigState: rig,
        drawStageActors: (c, anc) => {
          const vib = Math.sin(subLt * 28) * 3.5 * Math.exp(-subLt * 0.9);
          const blinkNow = (subLt > 0.68 && subLt < 0.84) ? 1 : 0;
          drawSquireCinematic2DActor(c, 955 + vib, anc.catwalkY + 340, 980, {
            castId: 'TAVI',
            view: 'front',
            expression: 'deadpan_disbelief',
            pupilX: 0.0,
            pupilY: 0.08,
            blink: blinkNow,
            secondaryLag: vib * 0.08,
            leatherWraps: true,
            armAngles: [24, 30, 26, 32],
            rightHandPose: 'relaxed',
            leftHandPose: 'relaxed',
            t: gt,
          });
        },
      });
    }
    vignette(g, 0.22, '#16111e');
  },
});
