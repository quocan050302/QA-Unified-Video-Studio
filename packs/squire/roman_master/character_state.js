// character_state.js — Locked Original Squire Roman Character State & Renderer Wrapper for KH-03.0.
// Calls Production packs/squire/chara.js::soldier() directly so silhouette, face, helmet, white glove,
// red scutum, and #392a21 warm-brown line identity remain 100% faithful to Production Squire.
import { OUT, PAL } from '../ink.js';
import { soldier, CAST } from '../chara.js';
import { evaluateRomanActorPoseAt } from './motion.js';

export const ROMAN_MASTER_STYLE_ID = 'roman_squire_master.v1';
export const ROMAN_MASTER_STYLE_FAMILY = 'production_squire_original_roman_2d';

export const ROMAN_MASTER_ARCHETYPES = Object.freeze({
  rookie_hastatus: Object.freeze({
    preset: 'hastatus',
    helmet: 'montefortino',
    feathers: 3,
    featherColors: Object.freeze([PAL.white, OUT, PAL.white]),
    body: 'roman',
    tunicColor: PAL.red,
    legs: 'bare',
    shield: Object.freeze({
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'lightning',
      chargeColor: PAL.yellow,
    }),
    weapon: 'spear',
  }),
  instructor_princeps: Object.freeze({
    preset: 'princeps',
    helmet: 'montefortino',
    feathers: 3,
    featherColors: Object.freeze([PAL.red, OUT, PAL.red]),
    mustache: 'big',
    body: 'roman',
    tunicColor: PAL.red,
    legs: 'bare',
    shield: Object.freeze({
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'wings',
      chargeColor: PAL.yellow,
    }),
    weapon: 'pilum',
  }),
  veteran_neighbor_legionary: Object.freeze({
    preset: 'hastatus',
    helmet: 'montefortino',
    feathers: 3,
    featherColors: Object.freeze([PAL.white, PAL.red, PAL.white]),
    beard: 'stubble',
    body: 'roman',
    tunicColor: PAL.red,
    legs: 'bare',
    shield: Object.freeze({
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'lightning',
      chargeColor: PAL.yellow,
    }),
    weapon: 'spear',
  }),
  centurion_crest: Object.freeze({
    preset: 'legionary',
    helmet: 'montefortino',
    crest: PAL.red,
    mail: true,
    body: 'roman',
    tunicColor: PAL.red,
    legs: 'bare',
    shield: Object.freeze({
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'wings',
      chargeColor: PAL.yellow,
    }),
    weapon: 'pilum',
  }),
});

export function resolveArchetypeSpec(actorIdOrArchetype) {
  const alias = {
    rookie: 'rookie_hastatus',
    hero: 'rookie_hastatus',
    rookie_hastatus: 'rookie_hastatus',
    courier_marcus: 'rookie_hastatus',
    marcus: 'rookie_hastatus',
    courier: 'rookie_hastatus',
    apprentice_titus: 'rookie_hastatus',
    apprentice: 'rookie_hastatus',
    forum_messenger: 'rookie_hastatus',
    messenger: 'rookie_hastatus',
    market_crowd: 'rookie_hastatus',
    instructor: 'instructor_princeps',
    drill_instructor: 'instructor_princeps',
    instructor_princeps: 'instructor_princeps',
    gate_guard_gaius: 'instructor_princeps',
    gaius: 'instructor_princeps',
    gate_guard: 'instructor_princeps',
    baker_lucius: 'instructor_princeps',
    baker: 'instructor_princeps',
    senator_cassius: 'instructor_princeps',
    senator: 'instructor_princeps',
    neighbor: 'veteran_neighbor_legionary',
    veteran_neighbor: 'veteran_neighbor_legionary',
    veteran_neighbor_legionary: 'veteran_neighbor_legionary',
    watchman_sec: 'veteran_neighbor_legionary',
    winch_guard: 'veteran_neighbor_legionary',
    signifer_marc: 'veteran_neighbor_legionary',
    signifer: 'veteran_neighbor_legionary',
    centurion: 'centurion_crest',
    centurion_crest: 'centurion_crest',
    centurion_varro: 'centurion_crest',
  }[actorIdOrArchetype] || actorIdOrArchetype;

  const spec = ROMAN_MASTER_ARCHETYPES[alias];
  if (!spec) {
    throw new Error(`KH03_STYLE_LOCK_VIOLATION: Unlocked Roman archetype '${actorIdOrArchetype}'`);
  }
  return { archetypeId: alias, spec };
}

// Deterministic immutable actor state at globalT
export function romanActorAt(globalT, beat, actorId, worldState = {}) {
  const actorCfg = (beat?.actors && beat.actors[actorId]) || beat || {};
  const { archetypeId, spec } = resolveArchetypeSpec(actorCfg.archetypeId || actorId);
  const pose = evaluateRomanActorPoseAt(
    globalT,
    beat,
    {
      ...spec,
      ...actorCfg,
      actorId,
      archetypeId,
      preset: spec.preset,
    },
    worldState
  );
  return Object.freeze({
    ...pose,
    styleId: ROMAN_MASTER_STYLE_ID,
    styleFamily: ROMAN_MASTER_STYLE_FAMILY,
    archetypeSpec: spec,
  });
}

// Render locked Roman actor via original Production Squire soldier()
export function drawRomanMasterActor2D(g, pose, renderOpts = {}) {
  if (!pose || pose.styleFamily !== ROMAN_MASTER_STYLE_FAMILY) {
    throw new Error('KH03_STYLE_LOCK_VIOLATION: drawRomanMasterActor2D requires production_squire_original_roman_2d pose');
  }
  const spec = pose.archetypeSpec || CAST[pose.preset] || CAST.hastatus;
  const polish = renderOpts.polish !== false;
  const shieldSpec = pose.hasShield && pose.shieldGrip
    ? {
        ...spec.shield,
        ...(renderOpts.shieldOverrides || {}),
        x: pose.shieldGrip.shX_u,
        y: pose.shieldGrip.shY_u,
        s: pose.shieldGrip.scutumSizeU,
        rot: pose.shieldGrip.shieldRot,
      }
    : null;

  return soldier(g, pose.rootWorld[0], pose.rootWorld[1], pose.actorH, {
    preset: spec.preset,
    helmet: renderOpts.helmet !== undefined ? renderOpts.helmet : spec.helmet,
    hair: renderOpts.hair,
    hairColor: renderOpts.hairColor,
    feathers: renderOpts.feathers ?? spec.feathers,
    featherColors: renderOpts.featherColors ?? (spec.featherColors ? [...spec.featherColors] : undefined),
    crest: renderOpts.crest !== undefined ? renderOpts.crest : spec.crest,
    mustache: renderOpts.mustache !== undefined ? renderOpts.mustache : spec.mustache,
    beard: renderOpts.beard !== undefined ? renderOpts.beard : spec.beard,
    mail: renderOpts.mail !== undefined ? renderOpts.mail : spec.mail,
    body: renderOpts.body || spec.body,
    tunicColor: renderOpts.tunicColor || spec.tunicColor,
    sash: renderOpts.sash,
    legs: spec.legs,
    courierSatchel: !!(renderOpts.courierSatchel ?? pose.courierSatchel),
    pose: 'stand',
    walk: false,
    noSwing: true,
    flip: pose.flip,
    rot: pose.bodyRot,
    headNodU: pose.headNodU,
    headRot: pose.headRot,
    look: pose.look,
    face: pose.face,
    blink: pose.blink,
    t: pose.globalT,
    seed: renderOpts.seed ?? 11,
    armsAng: [...pose.armsAng],
    leftFootLocal: [...pose.footPlant.leftFootLocal],
    rightFootLocal: [...pose.footPlant.rightFootLocal],
    leftKneeBend: pose.leftKneeBend,
    rightKneeBend: pose.rightKneeBend,
    hipBobU: pose.hipBobU,
    leftFar: renderOpts.leftFar,
    shoeMode: renderOpts.shoeMode || pose.shoeMode || 'front',
    shield: shieldSpec,
    weapon: pose.weapon || 'none',
    weaponLen: pose.weaponLenU,
    weaponAng: pose.weaponAng,
    featherBend: polish ? pose.featherBend : 0,
    skirtSway: polish ? pose.skirtSway : 0,
    romanMasterPolish: polish,
    lod: renderOpts.lod || 'high',
  });
}

// Guard world-space foot-plant, scutum grip, spear contact, and cross-cut continuity
export function validateRomanMasterRigAnchors(pose, propSpec = {}) {
  const errors = [];
  if (!pose) {
    return { valid: false, errors: ['Pose is null or undefined'] };
  }
  if (pose.styleFamily !== ROMAN_MASTER_STYLE_FAMILY) {
    errors.push(`Forbidden styleFamily: ${pose.styleFamily}`);
  }
  const spec = pose.archetypeSpec || {};
  if (!['montefortino', 'attic'].includes(spec.helmet)) {
    errors.push(`Invalid Roman helmet '${spec.helmet}' on actor '${pose.actorId}'`);
  }
  if (spec.body !== 'roman') {
    errors.push(`Invalid body '${spec.body}' on actor '${pose.actorId}'`);
  }

  const maxFootDrift = propSpec.maxFootDriftPx ?? 2.0;
  if (propSpec.requirePlantedFeet !== false) {
    if (pose.footPlant.leftDriftPx > maxFootDrift) {
      errors.push(`Left foot skate/drift ${pose.footPlant.leftDriftPx.toFixed(2)}px > ${maxFootDrift}px`);
    }
    if (pose.footPlant.rightDriftPx > maxFootDrift) {
      errors.push(`Right foot skate/drift ${pose.footPlant.rightDriftPx.toFixed(2)}px > ${maxFootDrift}px`);
    }
  }

  if (pose.hasShield) {
    if (!pose.shieldGrip) {
      errors.push(`Actor '${pose.actorId}' expected scutum grip but shieldGrip is missing`);
    } else {
      const maxGripDist = propSpec.maxShieldGripOffsetPx ?? Math.max(18, pose.u * 6.0);
      if (pose.shieldGrip.gripDriftPx > maxGripDist) {
        errors.push(`Shield grip detached: ${pose.shieldGrip.gripDriftPx.toFixed(2)}px > ${maxGripDist.toFixed(2)}px`);
      }
    }
  }

  if (propSpec.requireWeapon && (!pose.weapon || pose.weapon === 'none')) {
    errors.push(`Actor '${pose.actorId}' missing required weapon '${propSpec.requireWeapon}'`);
  }

  if (propSpec.spearAnchorWorld && pose.rightHandWorld) {
    const dSpear = Math.hypot(
      pose.rightHandWorld[0] - propSpec.spearAnchorWorld[0],
      pose.rightHandWorld[1] - propSpec.spearAnchorWorld[1]
    );
    const maxSpearDist = propSpec.maxSpearDriftPx ?? 6.0;
    if (dSpear > maxSpearDist) {
      errors.push(`Spear hand contact broken: ${dSpear.toFixed(2)}px > ${maxSpearDist.toFixed(2)}px`);
    }
  }

  if (propSpec.prevPose && propSpec.sameWorldAnchor) {
    const jumpPx = Math.hypot(
      pose.rootWorld[0] - propSpec.prevPose.rootWorld[0],
      pose.rootWorld[1] - propSpec.prevPose.rootWorld[1]
    );
    const maxJump = propSpec.maxCutJumpPx ?? 90.0;
    if (jumpPx > maxJump) {
      errors.push(`Actor '${pose.actorId}' teleported across same-anchor join: ${jumpPx.toFixed(1)}px > ${maxJump}px`);
    }
  }

  return {
    valid: errors.length === 0,
    actorId: pose.actorId,
    globalT: pose.globalT,
    errors,
  };
}
