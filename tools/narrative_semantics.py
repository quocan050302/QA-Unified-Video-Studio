"""tools/narrative_semantics.py — Universal Narrative Scene Graph & Grounded Event Graph (V14.4).

Architecture layer 1:
Builds capability-independent NarrativeSceneGraph and GroundedEventGraph
from script, storyboard shots, and silent beatboards.
Distinguishes facts, perceptions, illustrative reconstructions, negations,
and unsupported claims across both Squire and DEM packs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, Field

GroundingType = Literal[
    "NARRATED_FACT",
    "PERCEPTION",
    "ILLUSTRATIVE_RECONSTRUCTION",
    "NEGATION",
    "HYPOTHETICAL",
    "UNSUPPORTED",
]

EntityType = Literal["actor", "prop", "formation", "location"]

ActionKind = Literal[
    "APPROACH",
    "MOVE_TO",
    "STOP",
    "TURN",
    "BRACE",
    "CONTACT",
    "IMPACT_RECOIL",
    "FATIGUE",
    "SIGNAL",
    "OPEN_LANE",
    "FRONT_WITHDRAW",
    "RESERVE_ADVANCE",
    "PASS_THROUGH",
    "SHIELD_CLOSE",
    "DEFEND",
    "ATTACK",
    "BLOCK",
    "PARRY",
    "DRAW_WEAPON",
    "PICK_UP",
    "PUT_DOWN",
    "WAKE_UP",
    "SIT_DOWN",
    "OBSERVE",
    "WAIT",
    "CAMERA_REVEAL",
]


class SemanticEntity(BaseModel):
    entity_id: str
    entity_type: EntityType = "actor"
    pack: str = "squire"
    genre: str = "roman"
    name: str = ""
    faction: Optional[str] = None  # e.g. "roman", "opposing", "neutral", "user"
    role: str = "actor"  # e.g. "frontline_defender", "reserve_officer", "attacker", "hero", "tool"
    costume_id: Optional[str] = None
    equipment: List[str] = Field(default_factory=list)
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    grounding: GroundingType = "NARRATED_FACT"
    source_span: str = ""


class NarrativeSceneGraph(BaseModel):
    project_id: str = "unknown"
    pack: str = "squire"
    genre: str = "roman"
    entities: Dict[str, SemanticEntity] = Field(default_factory=dict)
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    locations: Dict[str, Any] = Field(default_factory=dict)
    shot_references: Dict[str, List[str]] = Field(default_factory=dict)
    ambiguities: List[str] = Field(default_factory=list)


class GroundedEventNode(BaseModel):
    event_id: str
    action_kind: ActionKind
    shot_id: str
    actor_ids: List[str] = Field(default_factory=list)
    target_ids: List[str] = Field(default_factory=list)
    target_slot_id: Optional[str] = None
    start_sec: float = 0.0
    end_sec: float = 1.0
    preconditions: List[Dict[str, Any]] = Field(default_factory=list)
    postconditions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_text: str = ""
    polarity: str = "AFFIRMED"  # AFFIRMED, NEGATED, PERCEIVED, HYPOTHETICAL
    grounding: GroundingType = "NARRATED_FACT"
    confidence: float = 1.0
    dependencies: List[str] = Field(default_factory=list)
    reconstruction_flag: bool = False


class GroundedEventGraph(BaseModel):
    events: List[GroundedEventNode] = Field(default_factory=list)
    causal_links: List[Dict[str, str]] = Field(default_factory=list)
    unsupported_events: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scene Graph Builder
# ---------------------------------------------------------------------------

def build_narrative_scene_graph(
    project_path_or_dict: Any,
    shots: List[Dict[str, Any]],
    script_or_silent_beats: Optional[List[Dict[str, Any]]] = None,
) -> NarrativeSceneGraph:
    """
    Build a capability-independent NarrativeSceneGraph from storyboard shots and text/beat cues.
    Resolves pronouns and entity references conservatively, flagging ambiguity.
    """
    cfg: Dict[str, Any] = {}
    proj_id = "project"
    
    if isinstance(project_path_or_dict, (str, Path)):
        p_path = Path(project_path_or_dict)
        proj_id = p_path.name
        cfg_file = p_path / "config.json"
        if cfg_file.is_file():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
    elif isinstance(project_path_or_dict, dict):
        cfg = project_path_or_dict
        proj_id = cfg.get("id", "project")

    pack = cfg.get("pack", "squire")
    genre = cfg.get("genre", "roman" if pack == "squire" else "selfimprove")

    sg = NarrativeSceneGraph(
        project_id=proj_id,
        pack=pack,
        genre=genre,
    )

    entities: Dict[str, SemanticEntity] = {}
    relations: List[Dict[str, Any]] = []
    shot_references: Dict[str, List[str]] = {}
    ambiguities: List[str] = []

    # 1. Initialize genre-appropriate baseline entities
    if pack == "squire":
        if genre == "roman":
            entities["roman_front_a"] = SemanticEntity(
                entity_id="roman_front_a",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Frontline Hastatus A",
                faction="roman",
                role="frontline_defender",
                costume_id="hastatus_scutum_pilum",
                equipment=["scutum", "gladius", "montefortino_helmet"],
                initial_state={"slot": "front_left", "status": "active"},
            )
            entities["roman_front_b"] = SemanticEntity(
                entity_id="roman_front_b",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Frontline Hastatus B",
                faction="roman",
                role="frontline_defender",
                costume_id="hastatus_scutum_pilum",
                equipment=["scutum", "gladius", "montefortino_helmet"],
                initial_state={"slot": "front_right", "status": "active"},
            )
            entities["roman_reserve_a"] = SemanticEntity(
                entity_id="roman_reserve_a",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Reserve Princeps A",
                faction="roman",
                role="reserve_line",
                costume_id="princeps_lorica_hamata",
                equipment=["scutum", "gladius", "plumed_helmet"],
                initial_state={"slot": "reserve_left", "status": "ready"},
            )
            entities["roman_reserve_b"] = SemanticEntity(
                entity_id="roman_reserve_b",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Reserve Princeps B",
                faction="roman",
                role="reserve_line",
                costume_id="princeps_lorica_hamata",
                equipment=["scutum", "gladius", "plumed_helmet"],
                initial_state={"slot": "reserve_right", "status": "ready"},
            )
            entities["opposing_a"] = SemanticEntity(
                entity_id="opposing_a",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Opposing Warrior",
                faction="opposing",
                role="attacker",
                costume_id="celtic_warrior",
                equipment=["spatha", "oval_shield"],
                initial_state={"slot": "enemy_front", "status": "charging"},
            )
            entities["centurion_officer"] = SemanticEntity(
                entity_id="centurion_officer",
                entity_type="actor",
                pack="squire",
                genre="roman",
                name="Centurion Marcus",
                faction="roman",
                role="command_officer",
                costume_id="centurion_transverse_crest",
                equipment=["gladius", "vitis", "lorica_hamata"],
                initial_state={"slot": "rear_command", "status": "observing"},
            )
        elif genre == "knight":
            entities["knight_a"] = SemanticEntity(
                entity_id="knight_a",
                entity_type="actor",
                pack="squire",
                genre="knight",
                name="Knight Defender",
                faction="defender",
                role="defender",
                costume_id="bascinet_heater_shield",
                equipment=["heater_shield", "arming_sword", "bascinet"],
                initial_state={"slot": "center_defend", "status": "ready"},
            )
            entities["knight_b"] = SemanticEntity(
                entity_id="knight_b",
                entity_type="actor",
                pack="squire",
                genre="knight",
                name="Knight Attacker",
                faction="attacker",
                role="attacker",
                costume_id="great_helm_pollaxe",
                equipment=["pollaxe", "great_helm"],
                initial_state={"slot": "center_attack", "status": "advance"},
            )
        elif genre == "samurai":
            entities["samurai_a"] = SemanticEntity(
                entity_id="samurai_a",
                entity_type="actor",
                pack="squire",
                genre="samurai",
                name="Samurai Master",
                faction="defender",
                role="duelist",
                costume_id="kabuto_do_armor",
                equipment=["katana", "kabuto"],
                initial_state={"slot": "duel_left", "status": "poised"},
            )
            entities["samurai_b"] = SemanticEntity(
                entity_id="samurai_b",
                entity_type="actor",
                pack="squire",
                genre="samurai",
                name="Opposing Samurai",
                faction="attacker",
                role="duelist",
                costume_id="eboshi_do_armor",
                equipment=["katana"],
                initial_state={"slot": "duel_right", "status": "striking"},
            )
    elif pack == "dem":
        # DEM Self-improvement entities
        entities["hero_bean"] = SemanticEntity(
            entity_id="hero_bean",
            entity_type="actor",
            pack="dem",
            genre="selfimprove",
            name="Hero Bean",
            faction="protagonist",
            role="hero",
            costume_id="dem_hoodie",
            equipment=[],
            initial_state={"pose": "sleep", "location": "bed"},
        )
        entities["phone_prop"] = SemanticEntity(
            entity_id="phone_prop",
            entity_type="prop",
            pack="dem",
            genre="selfimprove",
            name="Smartphone",
            role="tool",
            equipment=[],
            initial_state={"held_by": None, "state": "nightstand"},
        )
        entities["desk_prop"] = SemanticEntity(
            entity_id="desk_prop",
            entity_type="prop",
            pack="dem",
            genre="selfimprove",
            name="Work Desk",
            role="environment",
            initial_state={"occupied": False},
        )

    # 2. Extract entities referenced in shots or beats
    for s in shots:
        sid = s.get("id", "")
        line = s.get("line", "")
        args = s.get("args", {})
        shot_actors: List[str] = []

        # Check explicit actors in args
        if "people" in args and isinstance(args["people"], list):
            for p in args["people"]:
                pid = p.get("id") or p.get("preset")
                if pid:
                    shot_actors.append(pid)
                    if pid not in entities:
                        entities[pid] = SemanticEntity(
                            entity_id=pid,
                            pack=pack,
                            genre=genre,
                            name=str(pid).replace("_", " ").title(),
                            source_span=line,
                        )
        
        if "actors" in args and isinstance(args["actors"], list):
            for a in args["actors"]:
                who = a.get("who") or a.get("id")
                if who:
                    shot_actors.append(who)
                    if who not in entities:
                        entities[who] = SemanticEntity(
                            entity_id=who,
                            pack=pack,
                            genre=genre,
                            name=str(who).title(),
                            source_span=line,
                        )

        # Ambiguity check for pronouns in line
        lower_line = line.lower()
        if any(w in lower_line.split() for w in ["they", "them", "he", "she", "it"]):
            # If ambiguous pronoun exists and no clear subject is assigned in shot args
            if not shot_actors:
                ambiguities.append(f"Shot {sid}: pronoun in '{line}' requires conservative grounding")

        shot_references[sid] = list(set(shot_actors))

    sg.entities = entities
    sg.relations = relations
    sg.shot_references = shot_references
    sg.ambiguities = ambiguities
    return sg


# ---------------------------------------------------------------------------
# Grounded Event Graph Builder
# ---------------------------------------------------------------------------

def infer_grounded_event_graph(
    scene_graph: NarrativeSceneGraph,
    director_output: Optional[Dict[str, Any]] = None,
    shots: Optional[List[Dict[str, Any]]] = None,
) -> GroundedEventGraph:
    """
    Infer capability-independent GroundedEventGraph from NarrativeSceneGraph.
    Verbs and narrative intents are mapped to typed causal event nodes with pre/postconditions.
    """
    events: List[GroundedEventNode] = []
    causal_links: List[Dict[str, str]] = []
    unsupported_events: List[Dict[str, Any]] = []

    shots_list = shots or []
    if not shots_list and director_output and "shots" in director_output:
        shots_list = director_output["shots"]

    pack = scene_graph.pack
    genre = scene_graph.genre

    prev_event_id: Optional[str] = None

    for idx, s in enumerate(shots_list):
        sid = s.get("id") or s.get("shot_id") or f"s{idx+1:03d}"
        dur = float(s.get("dur", 3.0))
        start_t = float(s.get("start", idx * dur))
        end_t = float(s.get("end", start_t + dur))
        line = s.get("line") or s.get("source_span") or ""
        lower = line.lower()

        # Polarity & grounding inference
        polarity = "AFFIRMED"
        grounding: GroundingType = "NARRATED_FACT"
        reconstruction = False

        if any(w in lower for w in ("not", "never", "failed", "neither", "no ")):
            polarity = "NEGATED"
        elif any(w in lower for w in ("thought", "appeared", "seemed", "looked like", "illusion")):
            polarity = "PERCEIVED"
            grounding = "PERCEPTION"
        elif any(w in lower for w in ("reconstruction", "illustrates", "could work", "drill", "manoeuvre", "maneuver")):
            grounding = "ILLUSTRATIVE_RECONSTRUCTION"
            reconstruction = True
        elif any(w in lower for w in ("if", "would", "suppose", "hypothetically")):
            polarity = "HYPOTHETICAL"
            grounding = "HYPOTHETICAL"

        # Explicit action override if provided in shot spec
        explicit_action = (s.get("action") or s.get("action_kind") or "").upper()

        # Map narrative semantics to event nodes (prioritizing specific tactical transitions)
        if pack == "squire":
            if genre == "knight":
                if explicit_action == "APPROACH" or any(w in lower for w in ("charge", "approach", "advancing", "closes", "forward")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_approach",
                        action_kind="APPROACH",
                        shot_id=sid,
                        actor_ids=["knight_b"],
                        target_ids=["knight_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action in ("BLOCK", "BRACE") or any(w in lower for w in ("block", "brace", "heater", "raises shield")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_block",
                        action_kind="BLOCK",
                        shot_id=sid,
                        actor_ids=["knight_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "CONTACT" or any(w in lower for w in ("impact", "strike", "clashes", "blow", "collides")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_contact",
                        action_kind="CONTACT",
                        shot_id=sid,
                        actor_ids=["knight_b"],
                        target_ids=["knight_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "IMPACT_RECOIL" or any(w in lower for w in ("recoil", "staggers", "shudders", "recovering")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_recoil",
                        action_kind="IMPACT_RECOIL",
                        shot_id=sid,
                        actor_ids=["knight_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                else:
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_defend",
                        action_kind="DEFEND",
                        shot_id=sid,
                        actor_ids=["knight_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
            elif genre == "samurai":
                if explicit_action == "DRAW_WEAPON" or any(w in lower for w in ("draw", "iaido", "unsheathes", "katana")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_draw",
                        action_kind="DRAW_WEAPON",
                        shot_id=sid,
                        actor_ids=["samurai_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "APPROACH" or any(w in lower for w in ("step", "closes", "approach", "forward")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_approach",
                        action_kind="APPROACH",
                        shot_id=sid,
                        actor_ids=["samurai_b"],
                        target_ids=["samurai_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "PARRY" or any(w in lower for w in ("parry", "deflect", "side-step", "sidestep")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_parry",
                        action_kind="PARRY",
                        shot_id=sid,
                        actor_ids=["samurai_a"],
                        target_ids=["samurai_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "CONTACT" or any(w in lower for w in ("strike", "slash", "clash")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_contact",
                        action_kind="CONTACT",
                        shot_id=sid,
                        actor_ids=["samurai_b"],
                        target_ids=["samurai_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                else:
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_defend",
                        action_kind="DEFEND",
                        shot_id=sid,
                        actor_ids=["samurai_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
            else:
                # Squire Roman actions
                if explicit_action == "CAMERA_REVEAL" or any(w in lower for w in ("overhead", "tactical view", "reveal", "geometry")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_reveal",
                        action_kind="CAMERA_REVEAL",
                        shot_id=sid,
                        actor_ids=["roman_reserve_a", "roman_front_a", "opposing_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "SHIELD_CLOSE" or any(w in lower for w in ("close shields", "locked wall", "shields close", "close", "reform")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_shield_close",
                        action_kind="SHIELD_CLOSE",
                        shot_id=sid,
                        actor_ids=["roman_reserve_a", "roman_reserve_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"slot": "front_slots", "shield_wall": "open"}],
                        postconditions=[{"slot": "front_slots", "shield_wall": "locked"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "FRONT_WITHDRAW" or any(w in lower for w in ("withdraw", "retreat", "step away", "slip backward", "slip back", "falls back", "backward")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_front_withdraw",
                        action_kind="FRONT_WITHDRAW",
                        shot_id=sid,
                        actor_ids=["roman_front_a", "roman_front_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"lane": "corridor_center", "open": True}],
                        postconditions=[{"slot": "front_slots", "occupied": False}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "RESERVE_ADVANCE" or re.search(r"\b(reserves?|reserve\s+line|fresh\s+princeps|advance\s+to\s+replace|step\s+forward|marching\s+forward)\b", lower):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_reserve_advance",
                        action_kind="RESERVE_ADVANCE",
                        shot_id=sid,
                        actor_ids=["roman_reserve_a", "roman_reserve_b"],
                        target_slot_id="front_slots",
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"slot": "front_slots", "occupied": False}],
                        postconditions=[{"slot": "front_slots", "occupied": True}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "OPEN_LANE" or any(w in lower for w in ("corridor opens", "narrow corridor", "corridor", "open lane", "makes space", "parting the", "parts the")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_open_lane",
                        action_kind="OPEN_LANE",
                        shot_id=sid,
                        actor_ids=["roman_front_a", "roman_front_b"],
                        target_slot_id="corridor_center",
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"lane": "corridor_center", "open": False}],
                        postconditions=[{"lane": "corridor_center", "open": True}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "FATIGUE" or any(w in lower for w in ("fatigue", "exhausted", "tired", "struggle", "buckles")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_fatigue",
                        action_kind="FATIGUE",
                        shot_id=sid,
                        actor_ids=["roman_front_a", "roman_front_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"entity": "roman_front_a", "stamina": "fresh"}],
                        postconditions=[{"entity": "roman_front_a", "stamina": "exhausted"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "SIGNAL" or any(w in lower for w in ("signal", "order", "horn", "centurion", "commands")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_signal",
                        action_kind="SIGNAL",
                        shot_id=sid,
                        actor_ids=["centurion_officer"],
                        target_ids=["roman_reserve_a", "roman_reserve_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"entity": "centurion_officer", "signal_state": "idle"}],
                        postconditions=[{"entity": "centurion_officer", "signal_state": "signaled"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "CONTACT" or any(w in lower for w in ("impact", "collision", "contact", "clashes", "crash", "collide")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_contact",
                        action_kind="CONTACT",
                        shot_id=sid,
                        actor_ids=["opposing_a"],
                        target_ids=["roman_front_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"entity": "opposing_a", "distance": "near"}],
                        postconditions=[{"entity": "roman_front_a", "impact_state": "recoil"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "BRACE" or any(w in lower for w in ("brace", "holds", "locked", "shields held")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_brace",
                        action_kind="BRACE",
                        shot_id=sid,
                        actor_ids=["roman_front_a", "roman_front_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"entity": "roman_front_a", "shield_state": "normal"}],
                        postconditions=[{"entity": "roman_front_a", "shield_state": "braced"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                elif explicit_action == "APPROACH" or any(w in lower for w in ("charge", "closing", "charges", "threat", "advancing", "surge")):
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_approach",
                        action_kind="APPROACH",
                        shot_id=sid,
                        actor_ids=["opposing_a"],
                        target_ids=["roman_front_a", "roman_front_b"],
                        start_sec=start_t,
                        end_sec=end_t,
                        preconditions=[{"entity": "opposing_a", "distance": "far"}],
                        postconditions=[{"entity": "opposing_a", "distance": "near"}],
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)
                else:
                    # Default observation/defend
                    ev = GroundedEventNode(
                        event_id=f"ev_{sid}_defend",
                        action_kind="DEFEND",
                        shot_id=sid,
                        actor_ids=["roman_front_a"],
                        start_sec=start_t,
                        end_sec=end_t,
                        evidence_text=line,
                        polarity=polarity,
                        grounding=grounding,
                        reconstruction_flag=reconstruction,
                    )
                    events.append(ev)

        elif pack == "dem":
            # DEM Self-improvement event mapping
            if any(w in lower for w in ("wake", "wakes", "morning", "alarm", "open eyes", "bed")):
                ev = GroundedEventNode(
                    event_id=f"ev_{sid}_wake",
                    action_kind="WAKE_UP",
                    shot_id=sid,
                    actor_ids=["hero_bean"],
                    start_sec=start_t,
                    end_sec=end_t,
                    preconditions=[{"entity": "hero_bean", "pose": "sleep"}],
                    postconditions=[{"entity": "hero_bean", "pose": "awake"}],
                    evidence_text=line,
                    polarity=polarity,
                    grounding=grounding,
                )
                events.append(ev)
            elif any(w in lower for w in ("pick up", "grab", "phone", "takes phone", "check phone")):
                ev = GroundedEventNode(
                    event_id=f"ev_{sid}_pickup_phone",
                    action_kind="PICK_UP",
                    shot_id=sid,
                    actor_ids=["hero_bean"],
                    target_ids=["phone_prop"],
                    start_sec=start_t,
                    end_sec=end_t,
                    preconditions=[{"entity": "phone_prop", "held_by": None}],
                    postconditions=[{"entity": "phone_prop", "held_by": "hero_bean"}],
                    evidence_text=line,
                    polarity=polarity,
                    grounding=grounding,
                )
                events.append(ev)
            elif any(w in lower for w in ("put down", "places phone", "leaves phone", "away", "set down")):
                ev = GroundedEventNode(
                    event_id=f"ev_{sid}_putdown_phone",
                    action_kind="PUT_DOWN",
                    shot_id=sid,
                    actor_ids=["hero_bean"],
                    target_ids=["phone_prop"],
                    start_sec=start_t,
                    end_sec=end_t,
                    preconditions=[{"entity": "phone_prop", "held_by": "hero_bean"}],
                    postconditions=[{"entity": "phone_prop", "held_by": None}],
                    evidence_text=line,
                    polarity=polarity,
                    grounding=grounding,
                )
                events.append(ev)
            elif any(w in lower for w in ("desk", "sits", "starts work", "focus", "table")):
                ev = GroundedEventNode(
                    event_id=f"ev_{sid}_sit_desk",
                    action_kind="SIT_DOWN",
                    shot_id=sid,
                    actor_ids=["hero_bean"],
                    target_ids=["desk_prop"],
                    start_sec=start_t,
                    end_sec=end_t,
                    preconditions=[{"entity": "hero_bean", "pose": "awake"}],
                    postconditions=[{"entity": "hero_bean", "location": "desk"}],
                    evidence_text=line,
                    polarity=polarity,
                    grounding=grounding,
                )
                events.append(ev)
            else:
                ev = GroundedEventNode(
                    event_id=f"ev_{sid}_observe",
                    action_kind="OBSERVE",
                    shot_id=sid,
                    actor_ids=["hero_bean"],
                    start_sec=start_t,
                    end_sec=end_t,
                    evidence_text=line,
                    polarity=polarity,
                    grounding=grounding,
                )
                events.append(ev)

        # Connect causal chain
        if prev_event_id and events:
            causal_links.append({"from": prev_event_id, "to": events[-1].event_id})
        if events:
            prev_event_id = events[-1].event_id

    return GroundedEventGraph(
        events=events,
        causal_links=causal_links,
        unsupported_events=unsupported_events,
    )
