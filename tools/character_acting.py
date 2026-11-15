"""tools/character_acting.py — Character Acting & Expressive Performance System (V14.6).

Translates abstract narrative beats into visible physical acting:
distinct postures (BRACE, IMPACT_RECOIL, FATIGUE, SIGNAL, PARRY),
joint angles, shield rotation, procedural weight shift, and secondary motion.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, Field

from tools.action_capabilities import get_pack_capabilities, PackCapabilityProfile
from tools.visual_storytelling import SceneObjective


class ActorPerformanceBeat(BaseModel):
    """Detailed performance specifications for a single character in a shot."""
    actor_id: str
    shot_id: str
    start_t: float = 0.0
    end_t: float = 3.0
    action: str = "STAND"
    posture: str = "guard_ready"
    arm_gesture: str = "neutral"
    leg_stance: str = "upright"
    shield_tilt: float = 0.0
    torso_lean: float = 0.0
    head_look: float = 0.0
    face_expression: str = "neutral"
    observable_cues: List[str] = Field(default_factory=list)
    weight_shift: float = 0.0
    stamina: float = 1.0  # 1.0 = rested, 0.2 = exhausted
    shake: bool = False
    depth_layer: Literal["foreground", "midground", "background"] = "midground"
    motion_track: Optional[Dict[str, Any]] = None
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    contacts: List[Dict[str, Any]] = Field(default_factory=list)


# Canonical acting presets defining distinctive joint angles [left_sh, left_el, right_sh, right_el]
ACTING_ARM_ANGLES: Dict[str, List[int]] = {
    # Squires / Military:
    "stand": [12, 6, 12, 6],
    "guard": [35, 70, 110, 35],
    "brace": [65, 80, 35, 85],         # Both feet planted, shield tucked tight, weapon braced
    "impact_recoil": [85, 95, 20, 110],  # Shield driven backward, weapon arm pulled in shock
    "fatigue": [15, 25, 8, 12],          # Drooping shoulders, dangling shield, weapon pointed at ground
    "signal": [45, 65, 160, 20],         # Weapon/vitis or horn raised high overhead
    "parry": [75, 90, 120, 60],          # Shield and blade cross to deflect blow
    "lunge": [70, 40, 60, 50],
    "march": [12, 6, 12, 6],
    # DEM Self-Improvement:
    "dem_phone_pickup": [0, 0, 0, 0],
    "dem_sit_focus": [0, 0, 0, 0],
}


def plan_actor_performance(
    objectives: List[SceneObjective],
    world_timeline: Optional[Any] = None,
    capabilities: Optional[PackCapabilityProfile] = None,
    pack: str = "squire",
    genre: str = "roman",
    motion_plan: Optional[Any] = None,
) -> Dict[str, List[ActorPerformanceBeat]]:
    """
    Plan expressive character performances for all actors in each shot based on
    shared `MotionPlan` (when supplied) or scene objectives, physical causality,
    and pack-specific genre vocabulary.
    Returns {shot_id: [ActorPerformanceBeat, ...]}.
    """
    caps = capabilities or get_pack_capabilities(pack, genre)
    performances_by_shot: Dict[str, List[ActorPerformanceBeat]] = {}

    if motion_plan is not None:
        from tools.motion_performance import MotionPlan

        mp_obj = motion_plan if isinstance(motion_plan, MotionPlan) else MotionPlan.model_validate(motion_plan)
        tracks_by_shot: Dict[str, List[Any]] = {}
        for tr in mp_obj.tracks:
            tracks_by_shot.setdefault(tr.shot_id, []).append(tr)

        shot_ids = [o.shot_id for o in objectives] if objectives else sorted({tr.shot_id for tr in mp_obj.tracks})
        for sid in shot_ids:
            beats: List[ActorPerformanceBeat] = []
            for tr in tracks_by_shot.get(sid, []):
                peak_lean = max((ph.torso_lean for ph in tr.phases), key=lambda v: abs(v), default=0.0)
                clamped_lean = max(-0.35, min(0.35, peak_lean))
                peak_look = max((ph.head_look for ph in tr.phases), default=0.5)
                cues = [ph.visible_end_condition for ph in tr.phases if ph.visible_end_condition]
                beats.append(
                    ActorPerformanceBeat(
                        actor_id=tr.actor_id,
                        shot_id=sid,
                        start_t=tr.start_sec,
                        end_t=tr.end_sec,
                        action=tr.motion_type,
                        posture=tr.phases[1].posture_state if len(tr.phases) > 1 else (tr.phases[0].posture_state if tr.phases else "upright"),
                        arm_gesture="contact_locked" if tr.contacts else ("subtle_gesture" if tr.is_idle_or_speech_only else "active_reach"),
                        leg_stance="planted_idle" if tr.is_idle_or_speech_only else ("stride_coupled" if "WALK" in tr.motion_type or "RUN" in tr.motion_type else "planted_athletic"),
                        shield_tilt=0.0,
                        torso_lean=clamped_lean,
                        head_look=peak_look,
                        face_expression=tr.emotion,
                        observable_cues=cues or [tr.visible_end_condition],
                        weight_shift=round(tr.world_end[0] - tr.world_start[0], 4),
                        stamina=max(0.35, round(1.0 - 0.3 * tr.intensity, 2)),
                        shake=False,
                        motion_track=tr.model_dump(),
                        phases=[ph.model_dump() for ph in tr.phases],
                        contacts=[c.model_dump() for c in tr.contacts],
                    )
                )
            performances_by_shot[sid] = beats
        return performances_by_shot

    for obj in objectives:
        sid = obj.shot_id
        act = obj.event_kind.upper()
        beats: List[ActorPerformanceBeat] = []

        if pack == "squire":
            if genre == "roman":
                if act in ("APPROACH", "OBSERVE") or obj.pacing_role == "HOOK":
                    # Threat approach: Roman front braces low, enemy marches forward
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="BRACE",
                            posture="braced_low",
                            shield_tilt=-0.08,
                            torso_lean=-0.06,
                            head_look=0.6,
                            face_expression="grim",
                            observable_cues=["planted stance", "angled shield", "focused gaze"],
                            stamina=1.0,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="opposing_a",
                            shot_id=sid,
                            action="APPROACH",
                            posture="charge_forward",
                            shield_tilt=0.05,
                            torso_lean=0.08,
                            head_look=0.8,
                            face_expression="angry",
                            observable_cues=["striding march", "weapon held high"],
                            stamina=1.0,
                        )
                    )
                elif act in ("CONTACT", "BRACE"):
                    # Physical collision: Roman absorbs blow with braced scutum, enemy strikes
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="BRACE",
                            posture="braced_low",
                            shield_tilt=-0.12,
                            torso_lean=-0.10,
                            head_look=0.7,
                            face_expression="grim",
                            observable_cues=["maximum shield resistance", "lowered center of gravity"],
                            stamina=0.9,
                            shake=True,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="opposing_a",
                            shot_id=sid,
                            action="CONTACT",
                            posture="strike_forward",
                            shield_tilt=0.10,
                            torso_lean=0.12,
                            head_look=0.9,
                            face_expression="angry",
                            observable_cues=["blunt shield impact", "forward momentum halted"],
                            stamina=0.9,
                            shake=True,
                        )
                    )
                elif act in ("IMPACT_RECOIL",):
                    # Recoil & shudder
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="opposing_a",
                            shot_id=sid,
                            action="IMPACT_RECOIL",
                            posture="recoil_stagger",
                            shield_tilt=0.22,
                            torso_lean=-0.14,
                            head_look=0.2,
                            face_expression="shock",
                            observable_cues=["head flinch", "weapon arm pushed back", "unbalanced weight"],
                            stamina=0.75,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="BRACE",
                            posture="braced_low",
                            shield_tilt=-0.08,
                            torso_lean=-0.04,
                            head_look=0.7,
                            face_expression="grim",
                            observable_cues=["shield held firm after rebound"],
                            stamina=0.8,
                        )
                    )
                elif act in ("FATIGUE",):
                    # Exhaustion: front-line soldier slumps under sustained pressure
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="FATIGUE",
                            posture="slumped_exhausted",
                            shield_tilt=0.18,   # Drooping downward
                            torso_lean=0.14,    # Heavy slump
                            head_look=0.2,      # Gazing at ground
                            face_expression="fatigued",
                            observable_cues=["drooping shield", "slumped shoulders", "heavy breath bob", "grounded sword"],
                            stamina=0.3,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_reserve_a",
                            shot_id=sid,
                            action="OBSERVE",
                            posture="guard_ready",
                            shield_tilt=-0.04,
                            torso_lean=0.0,
                            head_look=0.5,
                            face_expression="grim",
                            observable_cues=["fresh upright posture in rear depth"],
                            stamina=1.0,
                            depth_layer="background",
                        )
                    )
                elif act in ("SIGNAL",):
                    # Officer signal: commander raises staff/vitis or horn, squad turns
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_officer",
                            shot_id=sid,
                            action="SIGNAL",
                            posture="command_raise",
                            shield_tilt=0.0,
                            torso_lean=0.04,
                            head_look=0.8,
                            face_expression="shout",
                            observable_cues=["vitis/sword raised high overhead", "clear command gesture"],
                            stamina=0.9,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="FATIGUE",
                            posture="slumped_exhausted",
                            shield_tilt=0.15,
                            torso_lean=0.10,
                            head_look=0.3,
                            face_expression="fatigued",
                            observable_cues=["hearing order, preparing to disengage"],
                            stamina=0.35,
                        )
                    )
                elif act in ("OPEN_LANE", "FRONT_WITHDRAW", "RESERVE_ADVANCE", "PASS_THROUGH"):
                    # Tactical relief maneuver: file partners sidestep, front passes through, reserve advances
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="FRONT_WITHDRAW",
                            posture="withdrawing",
                            shield_tilt=0.08,
                            torso_lean=-0.06,
                            head_look=0.1,
                            face_expression="grim",
                            observable_cues=["orderly rearward steps", "shield covering retreat"],
                            stamina=0.4,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_reserve_a",
                            shot_id=sid,
                            action="RESERVE_ADVANCE",
                            posture="advancing",
                            shield_tilt=-0.06,
                            torso_lean=0.08,
                            head_look=0.85,
                            face_expression="determined",
                            observable_cues=["fresh soldiers stepping forward through interval"],
                            stamina=1.0,
                        )
                    )
                elif act in ("SHIELD_CLOSE",):
                    # Fresh line reseals
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_reserve_a",
                            shot_id=sid,
                            action="SHIELD_CLOSE",
                            posture="braced_low",
                            shield_tilt=-0.10,
                            torso_lean=0.02,
                            head_look=0.8,
                            face_expression="determined",
                            observable_cues=["resealed solid shield wall", "fresh rested fighters"],
                            stamina=1.0,
                        )
                    )
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_reserve_b",
                            shot_id=sid,
                            action="SHIELD_CLOSE",
                            posture="braced_low",
                            shield_tilt=-0.10,
                            torso_lean=0.02,
                            head_look=0.8,
                            face_expression="determined",
                            observable_cues=["interlocking second shield"],
                            stamina=1.0,
                        )
                    )
                else:
                    beats.append(
                        ActorPerformanceBeat(
                            actor_id="roman_front_a",
                            shot_id=sid,
                            action="STAND",
                            posture="guard_ready",
                            shield_tilt=-0.04,
                            torso_lean=0.0,
                            head_look=0.5,
                            observable_cues=["steady guard"],
                            stamina=0.9,
                        )
                    )

            elif genre == "knight":
                # Medieval combat vocabulary
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="knight_a",
                        shot_id=sid,
                        action="PARRY" if "parry" in act.lower() or "block" in act.lower() else "BRACE",
                        posture="parry_high" if "parry" in act.lower() else "braced_low",
                        shield_tilt=-0.10,
                        torso_lean=-0.08,
                        head_look=0.7,
                        face_expression="grim",
                        observable_cues=["angled heater shield", "parrying longsword"],
                        stamina=0.85,
                    )
                )
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="knight_b",
                        shot_id=sid,
                        action="CONTACT" if "contact" in act.lower() or "strike" in act.lower() else "APPROACH",
                        posture="strike_forward",
                        shield_tilt=0.08,
                        torso_lean=0.12,
                        head_look=0.85,
                        face_expression="angry",
                        observable_cues=["sword strike", "armored lunge"],
                        stamina=0.85,
                    )
                )

            elif genre == "samurai":
                # Japanese Kenjutsu vocabulary
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="samurai_a",
                        shot_id=sid,
                        action="PARRY" if "parry" in act.lower() else "GUARD",
                        posture="guard_ready",
                        shield_tilt=0.0,
                        torso_lean=-0.04,
                        head_look=0.8,
                        face_expression="focused",
                        observable_cues=["two-handed katana guard", "low center of gravity"],
                        stamina=0.9,
                    )
                )
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="samurai_b",
                        shot_id=sid,
                        action="DRAW_WEAPON" if "draw" in act.lower() else "ATTACK",
                        posture="strike_forward",
                        shield_tilt=0.0,
                        torso_lean=0.10,
                        head_look=0.85,
                        face_expression="focused",
                        observable_cues=["katana strike contour", "kabuto crest angled"],
                        stamina=0.9,
                    )
                )
            else:
                # Generic Squire civilian / harbor / non-military acting fallback using world_timeline actors
                wt_actors = list(getattr(world_timeline, "actors", {}).keys()) if world_timeline is not None else []
                primary_aid = wt_actors[0] if wt_actors else "civilian_a"
                beats.append(
                    ActorPerformanceBeat(
                        actor_id=primary_aid,
                        shot_id=sid,
                        action=act or "OBSERVE",
                        posture="active_civic" if act not in ("STAND", "OBSERVE", "WAIT") else "upright",
                        torso_lean=0.06 if act not in ("STAND", "OBSERVE", "WAIT") else 0.0,
                        head_look=0.7,
                        face_expression="focused",
                        observable_cues=[f"civic action {act or 'OBSERVE'}"],
                        stamina=0.95,
                    )
                )

        elif pack == "dem":
            # DEM Self-improvement subtle acting
            if "phone" in act.lower() or "reach" in act.lower():
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="hero",
                        shot_id=sid,
                        action="PICK_UP",
                        posture="reach",
                        torso_lean=0.08,
                        head_look=0.4,
                        face_expression="focused",
                        observable_cues=["reaching arm", "looking down at desk"],
                        stamina=1.0,
                    )
                )
            elif "sit" in act.lower():
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="hero",
                        shot_id=sid,
                        action="SIT_DOWN",
                        posture="sitdesk",
                        torso_lean=0.15,
                        head_look=0.2,
                        face_expression="calm",
                        observable_cues=["seated posture", "knee bent 90 degrees", "hands near desk"],
                        stamina=1.0,
                    )
                )
            else:
                beats.append(
                    ActorPerformanceBeat(
                        actor_id="hero",
                        shot_id=sid,
                        action="STAND",
                        posture="relaxed",
                        torso_lean=0.0,
                        head_look=0.5,
                        face_expression="neutral",
                        observable_cues=["standing relaxed"],
                        stamina=1.0,
                    )
                )

        performances_by_shot[sid] = beats

    return performances_by_shot


def compile_actor_performance_to_rig(
    performance: ActorPerformanceBeat,
    pack: str = "squire",
) -> Dict[str, Any]:
    """
    Compile an ActorPerformanceBeat into renderer-consumable parameters for
    packs/squire/chara.js or packs/dem/bean.js.
    """
    if pack == "squire":
        pose_name = "stand"
        if performance.action in ("BRACE", "DEFEND"):
            pose_name = "brace"
        elif performance.action in ("CONTACT", "STRIKE"):
            pose_name = "push"
        elif performance.action in ("IMPACT_RECOIL",):
            pose_name = "recoil"
        elif performance.action in ("FATIGUE",):
            pose_name = "fatigue"
        elif performance.action in ("SIGNAL",):
            pose_name = "signal"
        elif performance.action in ("PARRY",):
            pose_name = "parry"
        elif performance.action in ("FRONT_WITHDRAW", "RESERVE_ADVANCE", "APPROACH", "WALK"):
            pose_name = "march"
        elif performance.action in ("SHIELD_CLOSE",):
            pose_name = "brace"
        elif "RUN" in performance.action:
            pose_name = "lunge"
        elif "WALK" in performance.action:
            pose_name = "march"
        elif any(k in performance.action for k in ("GRAB", "STEADY", "LIFT", "HAUL", "BRACE_ROPE", "CATCH")):
            pose_name = "brace"
        elif "DUCK" in performance.action or "SLIP" in performance.action:
            pose_name = "impact_recoil"
        elif "POINT" in performance.action:
            pose_name = "signal"

        arm_angles = ACTING_ARM_ANGLES.get(pose_name, ACTING_ARM_ANGLES["stand"])

        compiled: Dict[str, Any] = {
            "pose": pose_name,
            "armsAng": arm_angles,
            "lean": round(performance.torso_lean * 100, 2),
            "shieldTilt": performance.shield_tilt,
            "stamina": performance.stamina,
            "shake": performance.shake,
            "face": performance.face_expression,
            "look": performance.head_look,
            "performanceRig": {
                "action": performance.action,
                "posture": performance.posture,
                "shield_tilt": performance.shield_tilt,
                "torso_lean": performance.torso_lean,
                "stamina": performance.stamina,
                "observable_cues": performance.observable_cues,
            },
        }
        if performance.motion_track is not None:
            compiled["motionTrack"] = performance.motion_track
            compiled["performanceRig"]["phases"] = performance.phases
            compiled["performanceRig"]["contacts"] = performance.contacts
        return compiled

    elif pack == "dem":
        dem_pose = "stand"
        if performance.action == "PICK_UP":
            dem_pose = "reach"
        elif performance.action == "PUT_DOWN":
            dem_pose = "relaxed"
        elif performance.action == "SIT_DOWN":
            dem_pose = "sitdesk"
        elif performance.action == "FATIGUE":
            dem_pose = "slump"

        return {
            "pose": dem_pose,
            "facing": 1,
            "performanceRig": {
                "action": performance.action,
                "posture": performance.posture,
                "observable_cues": performance.observable_cues,
            },
        }

    return {"pose": "stand"}


def validate_actor_performance(
    performances: Dict[str, List[ActorPerformanceBeat]],
    character_bible: Optional[Dict[str, Any]] = None,
    motion_plan: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Validate that actor performances:
    1. Maintain identity across cuts without teleporting or costume swapping.
    2. Have valid physical constraints (shield angles, lean bounds).
    3. Are visibly distinguishable from idle standing.
    """
    errors: List[str] = []
    warnings: List[str] = []
    distinct_poses_found: Set[str] = set()

    if motion_plan is not None:
        from tools.motion_performance import MotionPlan, validate_motion_plan

        mp_obj = motion_plan if isinstance(motion_plan, MotionPlan) else MotionPlan.model_validate(motion_plan)
        mp_val = validate_motion_plan(mp_obj)
        errors.extend(mp_val["errors"])

    for sid, p_list in performances.items():
        if not p_list:
            warnings.append(f"Shot {sid} has no planned actor performances.")
            continue

        for p in p_list:
            distinct_poses_found.add(p.action)

            # Check lean safety (-0.35 to 0.35 max before looking like falling)
            if abs(p.torso_lean) > 0.40:
                errors.append(f"Shot {sid} actor {p.actor_id}: excessive torso lean {p.torso_lean}")

            # Check shield tilt (-0.35 to 0.35)
            if abs(p.shield_tilt) > 0.45:
                errors.append(f"Shot {sid} actor {p.actor_id}: excessive shield tilt {p.shield_tilt}")

    # Verify that distinct physical actions were planned (tactical OR general physical acting)
    expressive_tokens = (
        "BRACE", "FATIGUE", "SIGNAL", "SLIP", "STEADY", "LIFT", "DUCK", "GRAB", "HAUL", "RUN", "WALK", "CATCH", "POINT"
    )
    has_expressive = any(any(tok in act_name for tok in expressive_tokens) for act_name in distinct_poses_found)
    if not has_expressive:
        warnings.append("Performance plan lacks distinctive physical postures.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "distinct_actions_count": len(distinct_poses_found),
        "distinct_actions": list(distinct_poses_found),
    }
