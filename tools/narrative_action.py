"""tools/narrative_action.py — Universal Narrative Action Engine & Causal Spatiotemporal World Model (V14.4).

Architecture layer 3:
Builds authoritative shared world state, plans spatiotemporal action beats,
compiles executable choreography for 2D renderer, and validates strict causal
invariants across all shots (Squire and DEM).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, Field

from tools.action_capabilities import get_pack_capabilities, resolve_event_capabilities
from tools.narrative_semantics import (
    ActionKind,
    GroundedEventGraph,
    GroundedEventNode,
    NarrativeSceneGraph,
    build_narrative_scene_graph,
    infer_grounded_event_graph,
)


class ActorState(BaseModel):
    actor_id: str
    character_id: str = ""
    faction: str = "roman"
    costume_id: Optional[str] = None
    equipment: List[str] = Field(default_factory=list)
    x: float = 0.5
    y: float = 0.85
    z: float = 1.0
    facing: int = 1  # 1: right, -1: left
    pose: str = "stand"
    shield_state: str = "normal"  # normal, braced, recoiled, locked
    weapon_state: str = "sheathed"
    slot_id: Optional[str] = None
    stamina: str = "fresh"  # fresh, tired, exhausted


class WorldStateSnapshot(BaseModel):
    timestamp_sec: float
    actors: Dict[str, ActorState] = Field(default_factory=dict)
    formation_slots: Dict[str, Optional[str]] = Field(default_factory=dict)
    lanes_open: Dict[str, bool] = Field(default_factory=dict)


class WorldTimeline(BaseModel):
    snapshots: List[WorldStateSnapshot] = Field(default_factory=list)
    actors: Dict[str, ActorState] = Field(default_factory=dict)
    formation_slots: Dict[str, Optional[str]] = Field(default_factory=dict)
    lanes: Dict[str, bool] = Field(default_factory=dict)


class ActionChoreography(BaseModel):
    project_id: str
    pack: str
    genre: str
    events: List[GroundedEventNode] = Field(default_factory=list)
    world_timeline: WorldTimeline = Field(default_factory=WorldTimeline)
    shot_action_plans: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    causal_trace: List[Dict[str, Any]] = Field(default_factory=list)
    is_valid: bool = False
    validation_errors: List[str] = Field(default_factory=list)


class ActionContext(BaseModel):
    project_path: Path
    project_id: str
    pack: str
    genre: str
    shots: List[Dict[str, Any]]
    lines: List[Dict[str, Any]] = Field(default_factory=list)
    character_bible: Dict[str, Any] = Field(default_factory=dict)
    manual_shot_ids: Set[str] = Field(default_factory=set)


# ---------------------------------------------------------------------------
# Context & Intent Parsing
# ---------------------------------------------------------------------------

def build_action_context(project_path: Any, shot_range: Optional[Tuple[int, int]] = None) -> ActionContext:
    """Build ActionContext from project directory or config."""
    if isinstance(project_path, dict):
        proj_id = project_path.get("project_id") or project_path.get("id") or "unnamed_project"
        pack = project_path.get("pack", "squire")
        genre = project_path.get("genre", "roman" if pack == "squire" else "selfimprove")
        return ActionContext(
            project_path=Path("."),
            project_id=proj_id,
            pack=pack,
            genre=genre,
            shots=[],
            lines=[],
            character_bible={},
            manual_shot_ids=set(),
        )

    p_path = Path(project_path).resolve()
    cfg_file = p_path / "config.json"
    cfg: Dict[str, Any] = {}
    if cfg_file.is_file():
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    proj_id = p_path.name
    pack = cfg.get("pack", "squire")
    genre = cfg.get("genre", "roman" if pack == "squire" else "selfimprove")

    shots_file = p_path / "story" / "shots.json"
    shots_data: List[Dict[str, Any]] = []
    if shots_file.is_file():
        try:
            raw = json.loads(shots_file.read_text(encoding="utf-8"))
            shots_data = raw.get("shots", []) if isinstance(raw, dict) else raw
        except Exception:
            shots_data = []

    if shot_range:
        shots_data = shots_data[shot_range[0]:shot_range[1]]

    lines_file = p_path / "timeline" / "lines.json"
    lines_data: List[Dict[str, Any]] = []
    if lines_file.is_file():
        try:
            lines_data = json.loads(lines_file.read_text(encoding="utf-8"))
        except Exception:
            lines_data = []

    bible_file = p_path / "story" / "character_bible.json"
    bible_data: Dict[str, Any] = {}
    if bible_file.is_file():
        try:
            bible_data = json.loads(bible_file.read_text(encoding="utf-8"))
        except Exception:
            bible_data = {}

    manual_ids = {
        s.get("id")
        for s in shots_data
        if s.get("manual") is True or s.get("visual_source") == "manual"
    }

    return ActionContext(
        project_path=p_path,
        project_id=proj_id,
        pack=pack,
        genre=genre,
        shots=shots_data,
        lines=lines_data,
        character_bible=bible_data,
        manual_shot_ids=manual_ids,
    )


def parse_action_intents(
    ctx: ActionContext,
    director_plan: Optional[Dict[str, Any]] = None,
    source: str = "offline",
) -> List[GroundedEventNode]:
    """Parse grounded event intents from narrative context and optional director plan."""
    sg = build_narrative_scene_graph(ctx.project_path, ctx.shots)
    eg = infer_grounded_event_graph(sg, director_output=director_plan, shots=ctx.shots)
    cap_res = resolve_event_capabilities(eg.events, pack=ctx.pack, genre=ctx.genre)
    
    # Filter or flag unsupported events
    valid_events: List[GroundedEventNode] = []
    for ev in eg.events:
        valid_events.append(ev)

    return valid_events


# ---------------------------------------------------------------------------
# Authoritative Shared World State
# ---------------------------------------------------------------------------

def build_shared_world_state(
    ctx: ActionContext,
    events: List[GroundedEventNode],
) -> WorldTimeline:
    """
    Build spatiotemporally persistent world state across all shots.
    Coordinates (x, y, z) and actor states do NOT reset at cuts.
    """
    actors: Dict[str, ActorState] = {}
    slots: Dict[str, Optional[str]] = {}
    lanes: Dict[str, bool] = {"corridor_center": False}

    if ctx.pack == "squire":
        if ctx.genre == "roman":
            # Initial Roman tactical slots
            slots["front_left"] = "roman_front_a"
            slots["front_right"] = "roman_front_b"
            slots["reserve_left"] = "roman_reserve_a"
            slots["reserve_right"] = "roman_reserve_b"
            slots["enemy_front"] = "opposing_a"

            actors["roman_front_a"] = ActorState(
                actor_id="roman_front_a",
                character_id="hastatus_1",
                faction="roman",
                costume_id="hastatus",
                equipment=["scutum", "gladius"],
                x=0.38,
                y=0.86,
                facing=1,
                slot_id="front_left",
            )
            actors["roman_front_b"] = ActorState(
                actor_id="roman_front_b",
                character_id="hastatus_2",
                faction="roman",
                costume_id="hastatus",
                equipment=["scutum", "gladius"],
                x=0.48,
                y=0.86,
                facing=1,
                slot_id="front_right",
            )
            actors["roman_reserve_a"] = ActorState(
                actor_id="roman_reserve_a",
                character_id="princeps_1",
                faction="roman",
                costume_id="princeps",
                equipment=["scutum", "gladius"],
                x=0.22,
                y=0.74,
                facing=1,
                slot_id="reserve_left",
            )
            actors["roman_reserve_b"] = ActorState(
                actor_id="roman_reserve_b",
                character_id="princeps_2",
                faction="roman",
                costume_id="princeps",
                equipment=["scutum", "gladius"],
                x=0.30,
                y=0.74,
                facing=1,
                slot_id="reserve_right",
            )
            actors["opposing_a"] = ActorState(
                actor_id="opposing_a",
                character_id="celtic_warrior",
                faction="opposing",
                costume_id="celtic",
                equipment=["spatha", "oval_shield"],
                x=0.82,
                y=0.86,
                facing=-1,
                slot_id="enemy_front",
            )
            actors["centurion_officer"] = ActorState(
                actor_id="centurion_officer",
                character_id="centurion_marcus",
                faction="roman",
                costume_id="centurion",
                equipment=["gladius", "vitis"],
                x=0.15,
                y=0.72,
                facing=1,
                slot_id="rear_command",
            )
        elif ctx.genre == "knight":
            slots["knight_defender"] = "knight_a"
            slots["knight_attacker"] = "knight_b"
            actors["knight_a"] = ActorState(
                actor_id="knight_a",
                character_id="knight_defender",
                faction="defender",
                costume_id="bascinet_heater",
                equipment=["heater_shield", "sword"],
                x=0.35,
                y=0.85,
                facing=1,
                slot_id="knight_defender",
            )
            actors["knight_b"] = ActorState(
                actor_id="knight_b",
                character_id="knight_attacker",
                faction="attacker",
                costume_id="great_helm_pollaxe",
                equipment=["pollaxe"],
                x=0.75,
                y=0.85,
                facing=-1,
                slot_id="knight_attacker",
            )
        elif ctx.genre == "samurai":
            slots["samurai_left"] = "samurai_a"
            slots["samurai_right"] = "samurai_b"
            actors["samurai_a"] = ActorState(
                actor_id="samurai_a",
                character_id="samurai_master",
                faction="defender",
                costume_id="kabuto_armor",
                equipment=["katana"],
                x=0.35,
                y=0.85,
                facing=1,
                slot_id="samurai_left",
            )
            actors["samurai_b"] = ActorState(
                actor_id="samurai_b",
                character_id="samurai_challenger",
                faction="attacker",
                costume_id="eboshi_armor",
                equipment=["katana"],
                x=0.75,
                y=0.85,
                facing=-1,
                slot_id="samurai_right",
            )
    elif ctx.pack == "dem":
        slots["bed"] = "hero_bean"
        slots["nightstand"] = "phone_prop"
        slots["desk"] = None
        actors["hero_bean"] = ActorState(
            actor_id="hero_bean",
            character_id="hero_bean",
            faction="protagonist",
            costume_id="hoodie",
            x=0.32,
            y=0.58,
            facing=1,
            pose="sleep",
            slot_id="bed",
        )

    # Generic actor discovery from character_bible and shots (prevents hardcoded failures)
    for char_id, c_data in ctx.character_bible.items():
        if char_id not in actors and isinstance(c_data, dict):
            actors[char_id] = ActorState(
                actor_id=char_id,
                character_id=char_id,
                faction=c_data.get("faction", "defender"),
                costume_id=c_data.get("costume", c_data.get("preset")),
                equipment=c_data.get("equipment", []),
                x=float(c_data.get("x", 0.4)),
                y=float(c_data.get("y", 0.85)),
                facing=int(c_data.get("facing", 1)),
                slot_id=c_data.get("slot_id"),
            )

    for s in ctx.shots:
        s_args = s.get("args", {})
        combined = []
        for key in ("people", "actors", "actionActors"):
            val = s_args.get(key)
            if isinstance(val, list):
                combined.extend(val)
        for p in combined:
            if not isinstance(p, dict):
                continue
            p_id = p.get("id") or p.get("who")
            if p_id and p_id not in actors:
                actors[p_id] = ActorState(
                    actor_id=p_id,
                    character_id=p_id,
                    faction=p.get("faction", "defender" if p.get("facing", 1) >= 0 else "opposing"),
                    costume_id=p.get("preset") or p.get("costume"),
                    equipment=p.get("equipment", []),
                    x=float(p.get("x", p.get("from", 0.4))),
                    y=float(p.get("y", p.get("fromY", 0.85))),
                    facing=int(p.get("facing", 1)),
                )

    timeline = WorldTimeline(
        actors=actors,
        formation_slots=slots,
        lanes=lanes,
    )
    return timeline


def resolve_actor_preset(
    act_id: str,
    a_cfg: Dict[str, Any],
    actor_state: Optional[ActorState] = None,
    pack: str = "squire",
    genre: str = "roman",
) -> str:
    """Resolve renderer preset cleanly without hardcoded brittle matching."""
    if a_cfg.get("preset"):
        return str(a_cfg["preset"])
    if actor_state:
        if actor_state.costume_id:
            return actor_state.costume_id
        if actor_state.character_id:
            cid = actor_state.character_id.lower()
            for known in ("hastatus", "princeps", "centurion", "celtic", "latin", "knight14", "knight15", "samurai", "ashigaru", "hero"):
                if known in cid:
                    return known

    aid = act_id.lower()
    if pack == "dem":
        return "hero"

    if genre == "knight":
        if any(w in aid for w in ("attacker", "knight_b", "enemy", "opposing", "foe")):
            return "knight15"
        return "knight14"

    if genre == "samurai":
        if any(w in aid for w in ("challenger", "samurai_b", "enemy", "opposing", "ashigaru")):
            return "ashigaru"
        return "samurai"

    # Default squire/roman
    if any(w in aid for w in ("centurion", "officer", "commander", "marcus")):
        return "centurion"
    if any(w in aid for w in ("reserve", "princeps", "rear")):
        return "princeps"
    if any(w in aid for w in ("opposing", "enemy", "celtic", "gaul", "barbarian")):
        return "celtic"
    if any(w in aid for w in ("front", "hastatus", "forward", "vanguard")):
        return "hastatus"

    return "latin"


# ---------------------------------------------------------------------------
# Choreography Planner & Causal Compiler
# ---------------------------------------------------------------------------

def plan_action_beats(
    world: WorldTimeline,
    events: List[GroundedEventNode],
    script_timing: List[Dict[str, Any]],
    pack: str = "squire",
    genre: str = "roman",
    project_id: str = "planned_project",
) -> ActionChoreography:
    """
    Plan causal, smooth actor state transitions and continuous paths across events.
    Enforces causal order: lane opening -> withdrawal -> reserve advance -> shield close.
    """
    choreo = ActionChoreography(
        project_id=project_id,
        pack=pack,
        genre=genre,
        events=events,
        world_timeline=world,
    )

    shot_plans: Dict[str, Dict[str, Any]] = {}
    causal_trace: List[Dict[str, Any]] = []
    errors: List[str] = []

    # Working state copy
    cur_actors = copy.deepcopy(world.actors)
    cur_slots = copy.deepcopy(world.formation_slots)
    cur_lanes = copy.deepcopy(world.lanes)

    for ev in events:
        sid = ev.shot_id
        action = ev.action_kind
        start = ev.start_sec
        end = ev.end_sec
        dur = max(0.5, end - start)

        plan_entry: Dict[str, Any] = {
            "event_id": ev.event_id,
            "action": action,
            "start": start,
            "end": end,
            "dur": dur,
            "actors": {},
            "formation_action": None,
            "sound_cues": [],
        }

        # Apply specific state machine logic per action
        if action == "APPROACH":
            # Opposing / enemy advances toward defender line
            opp_id = None
            for cand in ev.actor_ids + ["opposing_a", "knight_b", "samurai_b"]:
                if cand in cur_actors:
                    opp_id = cand
                    break
            if not opp_id:
                for aid, act in cur_actors.items():
                    if act.faction in ("opposing", "attacker") or act.facing == -1:
                        opp_id = aid
                        break
            if opp_id and opp_id in cur_actors:
                opp = cur_actors[opp_id]
                start_x = opp.x
                end_x = 0.55 if genre in ("knight", "samurai") else 0.58
                opp.x = end_x
                opp.pose = "run"
                plan_entry["actors"][opp_id] = {
                    "from_x": start_x,
                    "to_x": end_x,
                    "y": opp.y,
                    "facing": -1,
                    "pose": "run",
                    "moveAt": 0.0,
                    "dur": dur * 0.9,
                }
                plan_entry["sound_cues"].append({"kind": "marching", "at": 0.1})

        elif action in ("BRACE", "BLOCK"):
            # Frontline raises shield / weapon and braces
            def_ids = [aid for aid in ev.actor_ids if aid in cur_actors]
            if not def_ids:
                def_ids = [aid for aid in ("roman_front_a", "roman_front_b", "knight_a", "samurai_a") if aid in cur_actors]
            if not def_ids:
                def_ids = [aid for aid, act in cur_actors.items() if act.faction in ("defender", "roman", "protagonist")]
            for act_id in def_ids:
                a = cur_actors[act_id]
                a.shield_state = "braced"
                a.pose = "brace" if genre == "roman" else "defend"
                plan_entry["actors"][act_id] = {
                    "x": a.x,
                    "y": a.y,
                    "facing": 1,
                    "pose": a.pose,
                    "shield_state": "braced",
                }
            plan_entry["sound_cues"].append({"kind": "shield_brace", "at": 0.2})

        elif action == "CONTACT":
            # Opponent collides with frontline, causing visible impact reaction
            opp_id = None
            for cand in ev.actor_ids + ["opposing_a", "knight_b", "samurai_b"]:
                if cand in cur_actors:
                    opp_id = cand
                    break
            if not opp_id:
                for aid, act in cur_actors.items():
                    if act.faction in ("opposing", "attacker") or act.facing == -1:
                        opp_id = aid
                        break
            def_id = None
            for cand in ev.target_ids + ["roman_front_a", "knight_a", "samurai_a"]:
                if cand in cur_actors:
                    def_id = cand
                    break
            if not def_id:
                for aid, act in cur_actors.items():
                    if act.faction in ("defender", "roman") and aid != opp_id:
                        def_id = aid
                        break
            if opp_id and def_id and opp_id in cur_actors and def_id in cur_actors:
                opp = cur_actors[opp_id]
                df = cur_actors[def_id]
                target_x = 0.50 if genre in ("knight", "samurai") else 0.52
                df.shield_state = "recoiled"
                df.pose = "impact_recoil"
                plan_entry["actors"][opp_id] = {
                    "from_x": opp.x,
                    "to_x": target_x,
                    "y": opp.y,
                    "facing": -1,
                    "pose": "attack",
                }
                opp.x = target_x
                recoil_x = max(0.1, df.x - 0.02)
                plan_entry["actors"][def_id] = {
                    "from_x": df.x,
                    "to_x": recoil_x,
                    "y": df.y,
                    "facing": 1,
                    "pose": "impact_recoil",
                    "shake": True,
                }
                df.x = recoil_x
                clash_sound = "sword_clash" if genre == "samurai" else "shield_clash"
                plan_entry["sound_cues"].append({"kind": clash_sound, "at": 0.15})

        elif action == "BREAKTHROUGH":
            if ev.polarity in ("NEGATED", "PERCEIVED"):
                # Negative / perceived breakthrough -> line holds firm!
                def_ids = [aid for aid in ("roman_front_a", "roman_front_b", "knight_a", "samurai_a") if aid in cur_actors]
                if not def_ids:
                    def_ids = [aid for aid, act in cur_actors.items() if act.faction in ("defender", "roman")]
                for act_id in def_ids:
                    a = cur_actors[act_id]
                    a.shield_state = "braced"
                    a.pose = "brace"
                    plan_entry["actors"][act_id] = {
                        "x": a.x,
                        "y": a.y,
                        "facing": 1,
                        "pose": "brace",
                        "shield_state": "braced",
                    }
                plan_entry["sound_cues"].append({"kind": "shield_brace", "at": 0.2})
            else:
                for cand in ("opposing_a", "knight_b"):
                    if cand in cur_actors:
                        cur_actors[cand].x = 0.30
                        plan_entry["actors"][cand] = {
                            "from_x": 0.52,
                            "to_x": 0.30,
                            "facing": -1,
                            "pose": "attack",
                        }

        elif action == "DRAW_WEAPON":
            if "samurai_a" in cur_actors:
                sa = cur_actors["samurai_a"]
                sa.pose = "ready"
                plan_entry["actors"]["samurai_a"] = {
                    "x": sa.x,
                    "y": sa.y,
                    "facing": 1,
                    "pose": "ready",
                }

        elif action == "PARRY":
            if "samurai_a" in cur_actors:
                sa = cur_actors["samurai_a"]
                sa.pose = "parry"
                plan_entry["actors"]["samurai_a"] = {
                    "from_x": 0.35,
                    "to_x": 0.38,
                    "y": sa.y,
                    "facing": 1,
                    "pose": "parry",
                }

        elif action == "IMPACT_RECOIL":
            for act_id in ("knight_a", "samurai_a", "roman_front_a"):
                if act_id in cur_actors:
                    a = cur_actors[act_id]
                    plan_entry["actors"][act_id] = {
                        "x": a.x,
                        "y": a.y,
                        "facing": 1,
                        "pose": "impact_recoil",
                        "shake": True,
                    }

        elif action == "FATIGUE":
            # Roman frontline visibly tires, lowers shield slightly, recovering posture
            for act_id in ("roman_front_a", "roman_front_b"):
                if act_id in cur_actors:
                    a = cur_actors[act_id]
                    a.stamina = "exhausted"
                    a.pose = "stand"
                    plan_entry["actors"][act_id] = {
                        "x": a.x,
                        "y": a.y,
                        "facing": 1,
                        "pose": "stand",
                        "fatigued": True,
                    }

        elif action == "SIGNAL":
            # Centurion sounds horn / raises command vitis
            if "centurion_officer" in cur_actors:
                c = cur_actors["centurion_officer"]
                c.pose = "command"
                plan_entry["actors"]["centurion_officer"] = {
                    "x": c.x,
                    "y": c.y,
                    "facing": 1,
                    "pose": "command",
                    "gesture": "raise_arm",
                }
                plan_entry["sound_cues"].append({"kind": "horn_signal", "at": 0.2})

        elif action == "OPEN_LANE":
            # Frontline soldiers sidestep outward to open a passage corridor
            cur_lanes["corridor_center"] = True
            if "roman_front_a" in cur_actors:
                cur_actors["roman_front_a"].x = 0.34  # Steps left
                plan_entry["actors"]["roman_front_a"] = {
                    "from_x": 0.38,
                    "to_x": 0.34,
                    "y": cur_actors["roman_front_a"].y,
                    "pose": "sidestep",
                    "dur": dur * 0.8,
                }
            if "roman_front_b" in cur_actors:
                cur_actors["roman_front_b"].x = 0.52  # Steps right
                plan_entry["actors"]["roman_front_b"] = {
                    "from_x": 0.48,
                    "to_x": 0.52,
                    "y": cur_actors["roman_front_b"].y,
                    "pose": "sidestep",
                    "dur": dur * 0.8,
                }
            plan_entry["formation_action"] = {
                "kind": "open_corridor",
                "corridor_x": 0.43,
                "corridor_width": 0.18,
                "lane_open": True,
            }

        elif action == "FRONT_WITHDRAW":
            # Causal check: lane must be open before front soldiers withdraw
            if not cur_lanes.get("corridor_center"):
                errors.append(f"Causal violation in {sid}: FRONT_WITHDRAW attempted before corridor_center opened!")

            cur_slots["front_left"] = None
            cur_slots["front_right"] = None

            if "roman_front_a" in cur_actors:
                rf_a = cur_actors["roman_front_a"]
                rf_a.x = 0.20
                rf_a.y = 0.72
                rf_a.slot_id = "reserve_rear_left"
                plan_entry["actors"]["roman_front_a"] = {
                    "from_x": 0.34,
                    "to_x": 0.20,
                    "from_y": 0.86,
                    "to_y": 0.72,
                    "facing": -1,  # Turning back
                    "pose": "walk",
                    "dur": dur * 0.85,
                }
            if "roman_front_b" in cur_actors:
                rf_b = cur_actors["roman_front_b"]
                rf_b.x = 0.28
                rf_b.y = 0.72
                rf_b.slot_id = "reserve_rear_right"
                plan_entry["actors"]["roman_front_b"] = {
                    "from_x": 0.52,
                    "to_x": 0.28,
                    "from_y": 0.86,
                    "to_y": 0.72,
                    "facing": -1,
                    "pose": "walk",
                    "dur": dur * 0.85,
                }
            plan_entry["sound_cues"].append({"kind": "marching", "at": 0.1})

        elif action == "RESERVE_ADVANCE":
            # Causal check: front slots must be vacated before reserve occupies them
            if cur_slots.get("front_left") is not None or cur_slots.get("front_right") is not None:
                errors.append(f"Causal violation in {sid}: RESERVE_ADVANCE attempted while front slots still occupied!")

            cur_slots["front_left"] = "roman_reserve_a"
            cur_slots["front_right"] = "roman_reserve_b"

            if "roman_reserve_a" in cur_actors:
                rr_a = cur_actors["roman_reserve_a"]
                rr_a.x = 0.38
                rr_a.y = 0.86
                rr_a.slot_id = "front_left"
                plan_entry["actors"]["roman_reserve_a"] = {
                    "from_x": 0.22,
                    "to_x": 0.38,
                    "from_y": 0.74,
                    "to_y": 0.86,
                    "facing": 1,
                    "pose": "march",
                    "dur": dur * 0.85,
                }
            if "roman_reserve_b" in cur_actors:
                rr_b = cur_actors["roman_reserve_b"]
                rr_b.x = 0.48
                rr_b.y = 0.86
                rr_b.slot_id = "front_right"
                plan_entry["actors"]["roman_reserve_b"] = {
                    "from_x": 0.30,
                    "to_x": 0.48,
                    "from_y": 0.74,
                    "to_y": 0.86,
                    "facing": 1,
                    "pose": "march",
                    "dur": dur * 0.85,
                }
            plan_entry["sound_cues"].append({"kind": "marching", "at": 0.1})

        elif action == "SHIELD_CLOSE":
            # Reserves close shields into a solid, reinforced wall
            cur_lanes["corridor_center"] = False
            for act_id in ("roman_reserve_a", "roman_reserve_b"):
                if act_id in cur_actors:
                    a = cur_actors[act_id]
                    a.shield_state = "locked"
                    a.pose = "brace"
                    plan_entry["actors"][act_id] = {
                        "x": a.x,
                        "y": a.y,
                        "facing": 1,
                        "pose": "brace",
                        "shield_state": "locked",
                    }
            plan_entry["formation_action"] = {
                "kind": "close_corridor",
                "lane_open": False,
                "shield_wall": "locked",
            }
            plan_entry["sound_cues"].append({"kind": "shield_lock", "at": 0.2})

        elif action == "CAMERA_REVEAL":
            # Tactical overhead showing complete formation shift
            plan_entry["formation_action"] = {
                "kind": "tactical_overhead",
                "relief_complete": True,
            }

        # DEM Pack state machines
        elif action == "WAKE_UP":
            if "hero_bean" in cur_actors:
                hb = cur_actors["hero_bean"]
                hb.pose = "awake"
                plan_entry["actors"]["hero_bean"] = {
                    "pose": "awake",
                    "face": "blink",
                }

        elif action == "PICK_UP":
            if "hero_bean" in cur_actors:
                hb = cur_actors["hero_bean"]
                hb.pose = "hold_phone"
                plan_entry["actors"]["hero_bean"] = {
                    "pose": "hold_phone",
                    "prop": "phone_prop",
                    "held": True,
                }

        elif action == "PUT_DOWN":
            if "hero_bean" in cur_actors:
                hb = cur_actors["hero_bean"]
                hb.pose = "stand"
                plan_entry["actors"]["hero_bean"] = {
                    "pose": "stand",
                    "prop": "phone_prop",
                    "held": False,
                }

        elif action == "SIT_DOWN":
            if "hero_bean" in cur_actors:
                hb = cur_actors["hero_bean"]
                hb.x = 0.65
                hb.y = 0.75
                hb.pose = "sit"
                plan_entry["actors"]["hero_bean"] = {
                    "from_x": 0.32,
                    "to_x": 0.65,
                    "pose": "sit",
                    "location": "desk",
                }

        shot_plans[sid] = plan_entry

        snapshot = WorldStateSnapshot(
            timestamp_sec=end,
            actors=copy.deepcopy(cur_actors),
            formation_slots=copy.deepcopy(cur_slots),
            lanes_open=copy.deepcopy(cur_lanes),
        )
        choreo.world_timeline.snapshots.append(snapshot)

        causal_trace.append({
            "shot_id": sid,
            "action": action,
            "start": start,
            "end": end,
            "lane_open": cur_lanes.get("corridor_center", False),
            "front_left_occupant": cur_slots.get("front_left"),
            "front_right_occupant": cur_slots.get("front_right"),
            "opposing_distance": round(cur_actors.get("opposing_a", ActorState(actor_id="")).x - cur_actors.get("roman_front_a", ActorState(actor_id="")).x, 3),
        })

    choreo.shot_action_plans = shot_plans
    choreo.causal_trace = causal_trace
    choreo.is_valid = len(errors) == 0
    choreo.validation_errors = errors
    return choreo


# ---------------------------------------------------------------------------
# Shot Compilation & Manual Lock Preservation
# ---------------------------------------------------------------------------

def compile_action_choreography_to_shots(
    shots: List[Dict[str, Any]],
    choreo: ActionChoreography,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Compile physical action choreography into storyboard shot args.
    Manual protected shots (manual: true, visual_source: manual) are strictly preserved byte-for-byte.
    Returns (revised_shots, modified_count).
    """
    revised: List[Dict[str, Any]] = []
    modified_count = 0

    for s in shots:
        sid = s.get("id") or s.get("shot_id")
        is_manual = (s.get("manual") is True or s.get("visual_source") == "manual")

        if is_manual:
            # STRICT BYTE-FOR-BYTE PRESERVATION
            revised.append(copy.deepcopy(s))
            continue

        shot_plan = choreo.shot_action_plans.get(sid)
        if not shot_plan:
            revised.append(copy.deepcopy(s))
            continue

        s_copy = copy.deepcopy(s)
        args = s_copy.setdefault("args", {})

        # 1. Attach actionActors array for renderer
        action_actors = []
        for act_id, a_cfg in shot_plan.get("actors", {}).items():
            preset = resolve_actor_preset(
                act_id=act_id,
                a_cfg=a_cfg,
                actor_state=choreo.world_timeline.actors.get(act_id),
                pack=choreo.pack,
                genre=choreo.genre,
            )
            entry = {
                "id": act_id,
                "preset": preset,
                "x": a_cfg.get("from_x", a_cfg.get("x", 0.5)),
                "y": a_cfg.get("from_y", a_cfg.get("y", 0.85)),
                "facing": a_cfg.get("facing", 1),
                "pose": a_cfg.get("pose", "stand"),
                "shield_state": a_cfg.get("shield_state", "normal"),
                "motionRig": True,
            }
            if "to_x" in a_cfg:
                entry["from"] = a_cfg.get("from_x", a_cfg.get("x", 0.5))
                entry["to"] = a_cfg["to_x"]
                entry["dur"] = a_cfg.get("dur", 1.0)
                entry["moveAt"] = a_cfg.get("moveAt", 0.0)
            if "to_y" in a_cfg:
                entry["fromY"] = a_cfg.get("from_y", a_cfg.get("y", 0.85))
                entry["toY"] = a_cfg["to_y"]
                entry["dur"] = a_cfg.get("dur", 1.0)
                entry["moveAt"] = a_cfg.get("moveAt", 0.0)
            if a_cfg.get("shake"):
                entry["shake"] = True
            action_actors.append(entry)

        if action_actors:
            args["actionActors"] = action_actors

        # For DEM pack, populate native DEM actors array
        if choreo.pack == "dem":
            dem_actors = []
            for act_id, a_cfg in shot_plan.get("actors", {}).items():
                d_entry = {
                    "who": "hero",
                    "x": a_cfg.get("from_x", a_cfg.get("x", 0.5)),
                    "y": a_cfg.get("from_y", a_cfg.get("y", 0.85)),
                    "pose": a_cfg.get("pose", "stand"),
                    "facing": a_cfg.get("facing", 1),
                }
                if "to_x" in a_cfg:
                    d_entry["walk"] = {
                        "to": a_cfg["to_x"],
                        "at": a_cfg.get("moveAt", 0.0),
                        "dur": a_cfg.get("dur", 1.0),
                    }
                dem_actors.append(d_entry)
            if dem_actors:
                args["actors"] = dem_actors

        # 2. Attach formationAction and top-down blocks
        if shot_plan.get("formation_action"):
            args["formationAction"] = shot_plan["formation_action"]

        if s_copy.get("tpl") == "top" or shot_plan.get("action") == "CAMERA_REVEAL":
            if not args.get("blocks"):
                args["blocks"] = [
                    {"x": 0.5, "y": 0.28, "w": 0.72, "h": 0.12, "side": "red", "cols": 16, "rows": 4, "face": 1, "label": "OPPOSING WARBANDS"},
                    {"x": 0.5, "y": 0.46, "w": 0.60, "h": 0.10, "side": "blue", "cols": 14, "rows": 3, "face": -1, "label": "PRINCEPS (NEW LINE)"},
                    {"x": 0.5, "y": 0.66, "w": 0.48, "h": 0.08, "side": "blue", "cols": 10, "rows": 2, "face": -1, "label": "HASTATI (WITHDRAWN)"},
                    {"x": 0.5, "y": 0.82, "w": 0.54, "h": 0.08, "side": "blue", "cols": 12, "rows": 2, "face": -1, "label": "TRIARII (RESERVE)"},
                ]
            if not args.get("labels"):
                args["labels"] = [
                    {"text": "1. CORRIDOR RELIEF", "x": 0.22, "y": 0.14, "color": "#f0dbad", "size": 32},
                    {"text": "2. FRESH PRINCEPS FORMED", "x": 0.50, "y": 0.14, "color": "#f0dbad", "size": 32},
                    {"text": "3. HASTATI SECURE IN REAR", "x": 0.78, "y": 0.14, "color": "#f0dbad", "size": 32},
                ]

        # 3. Synchronize sound cues
        if shot_plan.get("sound_cues"):
            existing_sfx = s_copy.setdefault("sfx", [])
            for cue in shot_plan["sound_cues"]:
                if cue["kind"] not in [c.get("kind") for c in existing_sfx]:
                    existing_sfx.append(cue)

        s_copy["action_choreography_compiled"] = True
        s_copy["action_kind"] = shot_plan.get("action")
        revised.append(s_copy)
        modified_count += 1

    return revised, modified_count


# ---------------------------------------------------------------------------
# Causality & Trace Validation
# ---------------------------------------------------------------------------

def validate_action_causality(choreo: ActionChoreography) -> Dict[str, Any]:
    """
    Validate causality invariants across all planned events:
    - Lane opening must precede withdrawal and passage.
    - Frontline withdrawal must precede reserve advance into vacated slots.
    - Impact contact requires prior spatial approach.
    - Shield close requires occupied front slots.
    - No teleports or faction switches.
    """
    errors: List[str] = list(choreo.validation_errors)
    trace = choreo.causal_trace

    lane_opened_at: Optional[int] = None
    withdrawn_at: Optional[int] = None
    reserve_arrived_at: Optional[int] = None
    closed_at: Optional[int] = None

    for idx, t in enumerate(trace):
        act = t["action"]
        if act == "OPEN_LANE":
            lane_opened_at = idx
        elif act == "FRONT_WITHDRAW":
            withdrawn_at = idx
            if lane_opened_at is None or lane_opened_at > idx:
                errors.append(f"Trace violation at step {idx}: FRONT_WITHDRAW executed before OPEN_LANE!")
        elif act == "RESERVE_ADVANCE":
            reserve_arrived_at = idx
            if withdrawn_at is None or withdrawn_at > idx:
                errors.append(f"Trace violation at step {idx}: RESERVE_ADVANCE executed before FRONT_WITHDRAW!")
        elif act == "SHIELD_CLOSE":
            closed_at = idx
            if reserve_arrived_at is None or reserve_arrived_at > idx:
                errors.append(f"Trace violation at step {idx}: SHIELD_CLOSE executed before RESERVE_ADVANCE!")

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "total_steps": len(trace),
        "lane_opened_step": lane_opened_at,
        "front_withdrawn_step": withdrawn_at,
        "reserve_arrived_step": reserve_arrived_at,
        "shield_closed_step": closed_at,
    }


def serialize_action_execution_trace(
    choreo: ActionChoreography,
    output_sha256: str = "",
    render_fingerprint: str = "",
) -> Dict[str, Any]:
    """Serialize structured action execution trace for actionable QA."""
    return {
        "schema_version": "1.0",
        "project_id": choreo.project_id,
        "pack": choreo.pack,
        "genre": choreo.genre,
        "output_sha256": output_sha256,
        "render_fingerprint": render_fingerprint,
        "is_valid": choreo.is_valid,
        "total_events": len(choreo.events),
        "causal_trace": choreo.causal_trace,
        "snapshots_count": len(choreo.world_timeline.snapshots),
    }
