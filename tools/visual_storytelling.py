"""tools/visual_storytelling.py — Universal Narrative-to-Visual Storytelling Engine (V14.6).

Builds comprehensive story context, infers shot-by-shot scene objectives,
plans cohesive visual story sequences with cinematic pacing (Hook, Exposition,
Complication, Payoff), and strictly validates causal narrative continuity.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, Field

from tools.action_capabilities import get_pack_capabilities, PackCapabilityProfile


class StoryContext(BaseModel):
    """Contextual metadata and constraints governing visual storytelling across the timeline."""
    project_id: str = "default_project"
    pack: str = "squire"
    genre: str = "roman"
    niche: Optional[str] = None
    style_id: Optional[str] = None
    aspect: Literal["16:9", "9:16"] = "16:9"
    setting: Dict[str, Any] = Field(default_factory=dict)
    character_bible: Optional[Dict[str, Any]] = None
    shots: List[Dict[str, Any]] = Field(default_factory=list)
    beats: List[Dict[str, Any]] = Field(default_factory=list)
    protagonist_faction: str = "roman"
    antagonist_faction: str = "opposing"
    historical_facts: List[str] = Field(default_factory=list)
    intended_viewer_takeaway: str = "Tactical line relief prevents exhaustion and breaks enemy momentum."


NICHE_KEYWORD_MAP: Dict[str, Tuple[str, ...]] = {
    "city_park": (
        "park", "kite", "bench", "trees", "branch", "ribbon", "spool", "bicycle",
        "meadow", "pathway", "promenade", "origami", "paper dragon", "built a dragon from paper",
    ),
    "modern_science": (
        "lab", "cleanroom", "beaker", "crystal", "scientist", "microscope", "sample",
        "experiment", "laser", "molecule", "researcher", "pipette", "spectrometer",
    ),
    "everyday_business": (
        "cafe", "barista", "espresso", "customer", "shop", "office", "counter", "invoice",
        "bakery", "tray", "latte", "storefront", "cashier", "client",
    ),
    "holdout_botanical_conservatory": (
        "conservatory", "glasshouse", "botanist", "orchid", "fern", "seedling", "terrarium", "greenhouse",
    ),
    "holdout_astronomy_museum": (
        "planetarium", "telescope", "curator", "eclipse", "gallery", "museum", "dome", "star chart",
    ),
    "roman_forum": (
        "forum", "marketplace", "scroll", "courier", "vendor", "senator", "rostra", "awning",
        "fountain", "amphora", "toga", "emperor's order",
    ),
}


def infer_niche_from_script(script_text: str, explicit_niche: Optional[str] = None) -> str:
    """Infer domain niche from explicit parameter or script lexical cues without defaulting non-Roman text to military."""
    if explicit_niche and str(explicit_niche).strip():
        return str(explicit_niche).strip().lower()
    low = (script_text or "").lower()
    best_niche = "general_narrative"
    best_hits = 0
    for niche_key, keywords in NICHE_KEYWORD_MAP.items():
        hits = sum(1 for kw in keywords if kw in low)
        if hits > best_hits:
            best_hits = hits
            best_niche = niche_key
    if best_hits == 0:
        if any(w in low for w in ("legion", "hastati", "scutum", "centurion", "cohort")):
            return "roman_military"
        if any(w in low for w in ("rome", "roman", "emperor", "tunic")):
            return "roman_forum"
    return best_niche


class SceneObjective(BaseModel):
    """Specific narrative and visible requirements for each shot in the sequence."""
    shot_id: str
    narrative_goal: str
    pacing_role: Literal["HOOK", "EXPOSITION", "COMPLICATION", "CLIMAX", "PAYOFF"] = "EXPOSITION"
    event_kind: str = "OBSERVE"
    polarity: Literal["AFFIRMED", "NEGATED", "PERCEIVED", "HYPOTHETICAL"] = "AFFIRMED"
    visible_evidence: List[str] = Field(default_factory=list)
    required_prestate: Dict[str, Any] = Field(default_factory=dict)
    required_poststate: Dict[str, Any] = Field(default_factory=dict)
    emotional_beat: str = "tension"
    stakes: str = "high"
    focal_subject: str = "hero"
    camera_reason: str = "establish spatial orientation"


class VisualStoryPlan(BaseModel):
    """Full-timeline visual plan for an individual shot."""
    shot_id: str
    objective: SceneObjective
    viewpoint: str = "front"
    scale: Literal["wide", "medium", "close", "tactical"] = "medium"
    template: str = "scene"
    primary_actors: List[str] = Field(default_factory=list)
    supporting_actors: List[str] = Field(default_factory=list)
    depth_layers: Dict[str, List[str]] = Field(default_factory=dict)
    environment_phase: str = "standard"
    visual_intensity: Literal["subtle", "standard", "dynamic"] = "standard"


def build_story_context(
    shots: List[Dict[str, Any]],
    beats: Optional[List[Dict[str, Any]]] = None,
    character_bible: Optional[Dict[str, Any]] = None,
    setting: Optional[Dict[str, Any]] = None,
    pack: str = "squire",
    genre: str = "roman",
    aspect: Literal["16:9", "9:16"] = "16:9",
    project_id: str = "project",
    takeaway: Optional[str] = None,
    niche: Optional[str] = None,
    style_id: Optional[str] = None,
) -> StoryContext:
    """Build standardized story context for sequence planning.
    Preserves 100% legacy defaults when `niche` is omitted, while enabling explicit additive niche routing.
    """
    b_list = beats or []
    if not b_list and shots:
        b_list = [
            {
                "id": s.get("id") or f"s{i+1:02d}",
                "line": s.get("line", ""),
                "action": s.get("action") or s.get("action_kind") or "OBSERVE",
            }
            for i, s in enumerate(shots)
        ]

    resolved_niche = infer_niche_from_script(
        " ".join(str(b.get("line", "")) for b in b_list),
        explicit_niche=niche,
    ) if niche is not None else None

    if resolved_niche and resolved_niche not in ("roman_military",):
        cb_actors = list((character_bible or {}).get("characters", character_bible or {}).keys()) if isinstance(character_bible, dict) else []
        protagonist = cb_actors[0] if cb_actors else "lead_actor"
        antagonist = cb_actors[1] if len(cb_actors) > 1 else "environmental_challenge"
        facts: List[str] = []
        default_setting_by_niche = {
            "roman_forum": {"environment": "roman_forum_marketplace", "time": "day"},
            "modern_science": {"environment": "cleanroom_laboratory", "time": "day"},
            "everyday_business": {"environment": "neighborhood_cafe_interior", "time": "morning"},
            "holdout_astronomy_museum": {"environment": "planetarium_gallery", "time": "twilight"},
        }
        resolved_setting = setting or default_setting_by_niche.get(resolved_niche, {"environment": "interior_stage", "time": "day"})
        resolved_takeaway = takeaway or f"Clear visual cause-and-effect acting drives narrative payoff in {resolved_niche}."
        return StoryContext(
            project_id=project_id,
            pack=pack,
            genre=genre if genre != "roman" or "roman" in resolved_niche else resolved_niche,
            niche=resolved_niche,
            style_id=style_id,
            aspect=aspect,
            setting=resolved_setting,
            character_bible=character_bible,
            shots=shots,
            beats=b_list,
            protagonist_faction=protagonist,
            antagonist_faction=antagonist,
            historical_facts=facts,
            intended_viewer_takeaway=resolved_takeaway,
        )

    protagonist = "roman" if genre == "roman" else ("knight" if genre == "knight" else ("samurai" if genre == "samurai" else "protagonist"))
    antagonist = "opposing" if pack == "squire" else "distraction"
    resolved_takeaway = takeaway if takeaway is not None else "Coordinated tactics and disciplined relief conquer chaotic assault."

    facts = []
    if genre == "roman":
        facts = [
            "Roman manipular system relied on interval gaps (quincunx) for line relief.",
            "Fresh Princeps stood behind Hastati to absorb pressure upon tactical fatigue.",
            "Scutum shields formed an interlocking protective wall during initial contact.",
        ]
    elif genre == "knight":
        facts = [
            "Medieval men-at-arms maintained tight formations with heater shields and polearms.",
            "Mounted or armored strikes were met with braced shields and timed parries.",
        ]
    elif genre == "samurai":
        facts = [
            "Samurai duels and skirmishes emphasized precise weapon draw, guard stance, and deflection.",
        ]
    elif pack == "dem":
        facts = [
            "Visual focus rests on human gestures, attention shifts, and everyday object interactions.",
        ]

    return StoryContext(
        project_id=project_id,
        pack=pack,
        genre=genre,
        niche=niche,
        style_id=style_id,
        aspect=aspect,
        setting=setting or {"environment": "field", "time": "day"},
        character_bible=character_bible,
        shots=shots,
        beats=b_list,
        protagonist_faction=protagonist,
        antagonist_faction=antagonist,
        historical_facts=facts,
        intended_viewer_takeaway=resolved_takeaway,
    )


def infer_scene_objectives(context: StoryContext) -> List[SceneObjective]:
    """
    Infer scene objectives for each shot in the sequence, ensuring clear questions,
    visible evidence, and emotional stakes rather than isolated mechanical cuts.
    """
    objectives: List[SceneObjective] = []
    total = len(context.shots)

    for idx, s in enumerate(context.shots):
        sid = s.get("id") or f"s{idx+1:02d}"
        line = s.get("line", "")
        lower = line.lower()
        act = (s.get("action") or s.get("action_kind") or "").upper()

        # Determine pacing role along narrative arc
        rel_pos = idx / max(1, total - 1)
        if idx == 0 or rel_pos < 0.18:
            role = "HOOK"
        elif rel_pos < 0.45:
            role = "EXPOSITION"
        elif rel_pos < 0.75:
            role = "COMPLICATION"
        elif rel_pos < 0.90:
            role = "CLIMAX"
        else:
            role = "PAYOFF"

        # Polarity & Negation check
        polarity: Literal["AFFIRMED", "NEGATED", "PERCEIVED", "HYPOTHETICAL"] = "AFFIRMED"
        if any(w in lower for w in ("not", "never", "failed", "neither")):
            polarity = "NEGATED"
        elif any(w in lower for w in ("thought", "appeared", "seemed", "illusion")):
            polarity = "PERCEIVED"
        elif any(w in lower for w in ("if", "would", "hypothetically")):
            polarity = "HYPOTHETICAL"

        # Derive visible evidence and focal subject
        visible_evidence = []
        emotional_beat = "calm"
        stakes = "tactical positioning"
        focal_subject = context.protagonist_faction
        cam_reason = "show setup and scale"

        if context.niche and context.niche not in ("roman_military",):
            if role == "HOOK":
                narrative_goal = f"Hook viewer immediately with clear inciting visual event: {line[:64]}"
                emotional_beat = "surprise" if any(w in lower for w in ("gust", "wind", "urgent", "slip", "volatile", "tip")) else "curiosity"
                stakes = "immediate narrative stakes established visually"
                cam_reason = "motivated macro or dynamic establishing frame on inciting prop and actor reaction"
                visible_evidence = ["clear inciting prop interaction", "expressive eye/brow reaction", "layered environment context"]
            elif role == "CLIMAX" or any(w in lower for w in ("caught", "catch", "stabilize", "jump", "pass")):
                narrative_goal = f"Deliver physical climax and tactile prop contact: {line[:64]}"
                emotional_beat = "exertion_to_triumph"
                stakes = "decisive physical action succeeds or fails here"
                cam_reason = "multi-angle or tight framing proving physical hand-to-prop contact"
                visible_evidence = ["locked hand grip on focal prop", "planted stance or dynamic follow-through", "secondary cloth motion"]
            elif role == "PAYOFF":
                narrative_goal = f"Resolve story beat with expressive character reaction: {line[:64]}"
                emotional_beat = "comedic_payoff" if any(w in lower for w in ("tomorrow", "laugh", "postponed")) else "warm_resolution"
                stakes = "emotional or comedic payoff lands clearly"
                cam_reason = "readable two-shot or expressive close reaction with breathing room"
                visible_evidence = ["distinct facial expression shift", "settled prop state", "coherent spatial staging"]
            else:
                narrative_goal = f"Advance {context.niche} story beat: {line[:64]}"
                emotional_beat = "determined" if any(w in lower for w in ("chase", "brace", "steady", "adjust")) else "attentive"
                stakes = "maintaining causal momentum across scene"
                cam_reason = "purposeful framing motivated by actor gaze and prop interaction"
                visible_evidence = ["actor gesture aligned to script", "consistent wardrobe and props"]
            req_pre = {"world_consistent": True}
            req_post = {"world_consistent": True}
        elif role == "HOOK":
            narrative_goal = "Hook viewer curiosity by demonstrating the imminent danger of front-line combat."
            emotional_beat = "anticipation"
            stakes = "survival against oncoming assault"
            cam_reason = "wide spatial orientation showing both opposing lines"
            visible_evidence = ["oncoming mass of fighters", "braced defensive stance", "encampment in far depth"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif act in ("CONTACT", "IMPACT_RECOIL") or any(w in lower for w in ("impact", "clash", "strike", "slam")):
            narrative_goal = "Show the visceral physics of initial shield contact and kinetic transfer."
            emotional_beat = "shock"
            stakes = "holding the line under blunt kinetic pressure"
            cam_reason = "close or medium lateral angle to show collision point and recoil"
            visible_evidence = ["shield collision", "dust eruption", "staggering recoil", "facial exertion"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif act in ("FATIGUE",) or any(w in lower for w in ("tire", "exhaust", "heavy", "fatigue", "breath")):
            narrative_goal = "Demonstrate the real human limit: muscular exhaustion after continuous shield pushing."
            emotional_beat = "exhaustion"
            stakes = "physical collapse if not relieved"
            cam_reason = "intimate profile or 3/4 medium to register drooping arms and heavy breathing"
            visible_evidence = ["drooping shield", "slumped posture", "deep breath bob", "weapon pointed down"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif act in ("SIGNAL",) or any(w in lower for w in ("signal", "horn", "vitis", "order", "centurion")):
            narrative_goal = "Illustrate command decision to initiate line replacement before breaking."
            emotional_beat = "command authority"
            stakes = "timing the relief before panic ensues"
            cam_reason = "profile or over-shoulder showing commander gesture and squad reaction"
            visible_evidence = ["raised command staff/vitis", "raised horn", "waiting reserve looking up"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif act in ("OPEN_LANE", "FRONT_WITHDRAW", "RESERVE_ADVANCE", "PASS_THROUGH"):
            narrative_goal = "Demonstrate the precision maneuver: opening lanes, orderly rearward withdrawal, reserve advance."
            emotional_beat = "disciplined tension"
            stakes = "avoiding disorder while changing troops in face of the enemy"
            cam_reason = "tracking or diagonal angle to reveal continuous passage without gap collapse"
            visible_evidence = ["sidestepping file partners", "rearward motion with depth", "advancing fresh line"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif act in ("SHIELD_CLOSE",) or any(w in lower for w in ("lock", "reseal", "close", "re-form", "wall")):
            narrative_goal = "Show the re-establishment of the solid shield wall, shattering attacker expectations."
            emotional_beat = "triumph / steadfastness"
            stakes = "restoring defensive integrity"
            cam_reason = "low angle or medium heroic frame emphasizing impenetrable bronze and wood"
            visible_evidence = ["interlocking shields", "fresh rested postures", "advancing wall push"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        elif s.get("tpl") == "top" or any(w in lower for w in ("overhead", "top-down", "aerial", "manoeuvre", "quincunx", "formation")):
            narrative_goal = "Provide clear tactical overhead clarity explaining the geometry of the maneuver."
            emotional_beat = "tactical insight"
            stakes = "comprehending the macro-level organizational genius"
            cam_reason = "plan/top-down camera presenting legible unit blocks and movement vectors"
            visible_evidence = ["colored formation rectangles", "legible unit badges", "clear lane opening vectors"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}
        else:
            narrative_goal = f"Deliver narrative beat: {line[:50]}"
            cam_reason = "maintain continuity and viewer focus"
            visible_evidence = ["steady character presence", "environmental grounding"]
            req_pre = {"line_intact": True}
            req_post = {"line_intact": True}

        obj = SceneObjective(
            shot_id=sid,
            narrative_goal=narrative_goal,
            pacing_role=role,
            event_kind=act or "OBSERVE",
            polarity=polarity,
            visible_evidence=visible_evidence,
            required_prestate=req_pre,
            required_poststate=req_post,
            emotional_beat=emotional_beat,
            stakes=stakes,
            focal_subject=focal_subject,
            camera_reason=cam_reason,
        )
        objectives.append(obj)

    return objectives


def plan_visual_story_sequence(
    context: StoryContext,
    world_timeline: Optional[Any] = None,
    director_plan: Optional[Dict[str, Any]] = None,
    capabilities: Optional[PackCapabilityProfile] = None,
) -> List[VisualStoryPlan]:
    """
    Plan a full-timeline visual story sequence connecting objectives, viewpoints,
    and ensemble staging into a coherent film structure.
    """
    caps = capabilities or get_pack_capabilities(context.pack, context.genre)
    objectives = infer_scene_objectives(context)
    plans: List[VisualStoryPlan] = []

    for obj in objectives:
        # Match shot from context
        matched_shot = next((s for s in context.shots if (s.get("id") or s.get("shot_id")) == obj.shot_id), {})
        shot_args = matched_shot.get("args", {})
        tpl = matched_shot.get("tpl", "scene")

        # Determine scale and viewpoint
        vp = shot_args.get("view") or "front"
        if vp not in caps.supported_viewpoints and caps.supported_viewpoints:
            vp = "front"

        scale: Literal["wide", "medium", "close", "tactical"] = "medium"
        if tpl == "top":
            scale = "tactical"
        elif tpl == "army" or obj.pacing_role == "HOOK":
            scale = "wide"
        elif tpl == "close" or obj.emotional_beat in ("shock", "exhaustion"):
            scale = "close"
        else:
            scale = "medium"

        # Determine primary and supporting actors
        if context.niche and context.niche not in ("roman_military",):
            cb_raw = context.character_bible or {}
            cb_dict = cb_raw.get("characters", cb_raw) if isinstance(cb_raw, dict) else {}
            cb_ids = [str(k) for k in cb_dict.keys()] if isinstance(cb_dict, dict) else []
            if cb_ids:
                primary = cb_ids[:1] if scale == "close" else cb_ids[:2]
                supporting = cb_ids[len(primary):]
            else:
                primary = ["actor_lead"]
                supporting = ["actor_support"]
        elif context.genre == "roman":
            if obj.pacing_role == "HOOK" or "wide" in vp or scale == "wide":
                primary = ["roman_front_a", "opposing_a"]
                supporting = ["roman_front_b", "roman_reserve_a", "opposing_b"]
            elif obj.event_kind in ("CONTACT", "IMPACT_RECOIL"):
                primary = ["roman_front_a", "opposing_a"]
                supporting = ["roman_front_b"]
            elif obj.event_kind == "FATIGUE":
                primary = ["roman_front_a"]
                supporting = ["roman_front_b", "roman_reserve_a"]
            elif obj.event_kind == "SIGNAL":
                primary = ["roman_officer"]
                supporting = ["roman_front_a", "roman_reserve_a"]
            elif obj.event_kind in ("OPEN_LANE", "FRONT_WITHDRAW", "RESERVE_ADVANCE"):
                primary = ["roman_front_a", "roman_reserve_a"]
                supporting = ["roman_front_b", "roman_reserve_b"]
            elif obj.event_kind == "SHIELD_CLOSE":
                primary = ["roman_reserve_a", "roman_reserve_b"]
                supporting = ["roman_front_a"]
            else:
                primary = ["roman_front_a"]
                supporting = ["roman_front_b"]
        elif context.genre == "knight":
            primary = ["knight_a", "knight_b"]
            supporting = ["squire_support"]
        elif context.genre == "samurai":
            primary = ["samurai_a", "samurai_b"]
            supporting = []
        elif context.pack == "dem":
            primary = ["hero"]
            supporting = []
        else:
            primary = ["actor_1"]
            supporting = ["actor_2"]

        # Depth layer assignment
        depth_layers = {
            "foreground": [],
            "midground": primary,
            "background": supporting,
        }

        # Environmental phase progression across timeline
        if context.niche and context.niche not in ("roman_military",):
            env_phase = "ambient_establish"
            if obj.pacing_role in ("COMPLICATION", "CLIMAX"):
                env_phase = "dynamic_interaction"
            elif obj.pacing_role == "PAYOFF":
                env_phase = "settled_payoff"
        else:
            env_phase = "morning_approach"
            if obj.pacing_role in ("COMPLICATION", "CLIMAX"):
                env_phase = "battle_dust"
            elif obj.pacing_role == "PAYOFF":
                env_phase = "resolute_dusk"

        plan = VisualStoryPlan(
            shot_id=obj.shot_id,
            objective=obj,
            viewpoint=vp,
            scale=scale,
            template=tpl,
            primary_actors=primary,
            supporting_actors=supporting,
            depth_layers=depth_layers,
            environment_phase=env_phase,
            visual_intensity="dynamic" if scale in ("close", "tactical") else "standard",
        )
        plans.append(plan)

    return plans


def validate_visual_story_sequence(
    plans: List[VisualStoryPlan],
    script: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Validate that visual story sequence satisfies causal grammar:
    1. No duplicate identical shot compositions back-to-back.
    2. Event progression follows physical causality (e.g. contact before recoil, open before withdraw).
    3. Proper Hook -> Exposition -> Complication -> Climax -> Payoff progression.
    4. Negated events are flagged so physical action is not erroneously affirmed.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not plans:
        return {"valid": False, "errors": ["Empty visual story sequence"], "warnings": []}

    # Verify Hook presence
    if plans[0].objective.pacing_role != "HOOK":
        warnings.append("Sequence does not begin with an explicit HOOK objective.")

    # Check for identical back-to-back compositions
    for i in range(1, len(plans)):
        prev_p = plans[i - 1]
        curr_p = plans[i]
        if (
            prev_p.viewpoint == curr_p.viewpoint
            and prev_p.scale == curr_p.scale
            and prev_p.template == curr_p.template
            and prev_p.template != "top"
        ):
            warnings.append(
                f"Shots {prev_p.shot_id} and {curr_p.shot_id} share identical viewpoint ({curr_p.viewpoint}) and scale ({curr_p.scale}); consider camera variation."
            )

    # Check causality of specific tactical stages
    event_order = [p.objective.event_kind for p in plans]
    if "IMPACT_RECOIL" in event_order and "CONTACT" in event_order:
        if event_order.index("IMPACT_RECOIL") < event_order.index("CONTACT"):
            errors.append("Causal violation: IMPACT_RECOIL occurs before CONTACT.")

    if "FRONT_WITHDRAW" in event_order and "OPEN_LANE" in event_order:
        if event_order.index("FRONT_WITHDRAW") < event_order.index("OPEN_LANE"):
            errors.append("Causal violation: FRONT_WITHDRAW occurs before OPEN_LANE.")

    # Check negated beats
    for p in plans:
        if p.objective.polarity == "NEGATED":
            if p.objective.event_kind in ("BREAKTHROUGH", "COLLAPSE", "ROUT"):
                warnings.append(f"Shot {p.shot_id} has NEGATED action '{p.objective.event_kind}'; physical breakdown must be suppressed.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_shots_planned": len(plans),
        "has_hook": any(p.objective.pacing_role == "HOOK" for p in plans),
        "has_payoff": any(p.objective.pacing_role == "PAYOFF" for p in plans),
    }
