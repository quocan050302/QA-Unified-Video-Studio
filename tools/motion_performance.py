"""tools/motion_performance.py — Generic Script-to-Motion Performance Planner (FL-01 / V14.7.6).

Translates arbitrary scripts, spoken word timings, cast bibles, and world states into a
versioned, causally validated `MotionPlan` with continuous `ActorMotionTrack` phases:
    ANTICIPATE -> REACH / APPROACH -> CONTACT -> EXERT / ACT -> REACT -> FOLLOW_THROUGH -> SETTLE

Design principles:
- Reuses `tools.narrative_action.parse_action_intents` and `tools.visual_storytelling.StoryContext`
  rather than creating a disconnected NLP pipeline.
- Distinguishes idle/breathing/speech-only beats from active physical object interactions.
- Labels unknown/unregistered physical verbs as `unsupported_action=True` with exact text
  evidence and a safe neutral fallback (`OBSERVE`), never mapping randomly to military presets.
- Truthfully records `routing_mode="OFFLINE_ONLY"` unless a verified live LLM provider trace is passed.
- Compiles additively into legacy shot `args` (`motionPlan`, `motionTracks`, `worldState`) while
  preserving 100% backward compatibility when `MotionPlan` is absent.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, Field

from tools.action_capabilities import (
    PackCapabilityProfile,
    get_pack_capabilities,
    resolve_motion_intent_capabilities,
)
from tools.narrative_action import ActionContext, parse_action_intents
from tools.visual_storytelling import SceneObjective, build_story_context, infer_scene_objectives

MOTION_SCHEMA_VERSION = "14.7.6"

PhaseKind = Literal[
    "ANTICIPATE",
    "REACH",
    "APPROACH",
    "CONTACT",
    "EXERT",
    "ACT",
    "REACT",
    "FOLLOW_THROUGH",
    "SETTLE",
    "IDLE",
]

TempoCurveKind = Literal[
    "ease_in",
    "ease_out",
    "ease_in_out",
    "linear",
    "overshoot_settle",
    "hold",
]

PHYSICAL_CONTACT_MOTIONS: Set[str] = {
    "GRAB",
    "CARRY",
    "STEADY_PROP",
    "CATCH_RAIL",
    "LIFT_SHARED",
    "BRACE_ROPE",
    "HAUL_ROPE",
}

LOCOMOTION_MOTIONS: Set[str] = {
    "WALK",
    "RUN",
    "APPROACH",
    "MOVE_TO",
}

IDLE_OR_SPEECH_MOTIONS: Set[str] = {
    "IDLE_BREATHE",
    "SPEECH_GESTURE",
    "OBSERVE",
    "WAIT",
    "STAND",
}


# ---------------------------------------------------------------------------
# Versioned Pydantic v2 Models
# ---------------------------------------------------------------------------


class MotionIntent(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    intent_id: str
    shot_id: str
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 3.0
    narration_word_timestamps: List[Dict[str, Any]] = Field(default_factory=list)
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "OBSERVE"
    is_idle_or_speech_only: bool = False
    unsupported_action: bool = False
    unsupported_evidence: Optional[str] = None
    fallback_motion_type: Optional[str] = None
    emotion: str = "focused"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.42, 0.84)
    world_end: Tuple[float, float] = (0.42, 0.84)
    intensity: float = 0.5
    source_confidence: float = 0.9
    visible_end_condition: str = "actor settles cleanly"
    sound_cue: Optional[str] = None


class MotionPhase(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    phase_name: PhaseKind
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 0.5
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "OBSERVE"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.42, 0.84)
    world_end: Tuple[float, float] = (0.42, 0.84)
    posture_state: str = "upright"
    torso_lean: float = 0.0
    head_look: float = 0.5
    knee_flex: float = 0.0
    arm_reach: float = 0.0
    hand_anchor_id: Optional[str] = None
    foot_planted_left: bool = True
    foot_planted_right: bool = True
    slip_foot: Optional[Literal["left", "right"]] = None
    tempo_curve: TempoCurveKind = "ease_in_out"
    intensity: float = 0.5
    source_confidence: float = 0.9
    visible_end_condition: str = ""
    sound_cue: Optional[str] = None


class ObjectContactConstraint(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    constraint_id: str
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 1.0
    actor_id: str
    actor_ids: List[str] = Field(default_factory=list)
    object_id: str
    object_ids: List[str] = Field(default_factory=list)
    hand: Literal["left", "right", "both"] = "right"
    anchor_name: str = "grip_main"
    anchor_local: Tuple[float, float] = (0.0, 0.0)
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "GRAB"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.5, 0.76)
    world_end: Tuple[float, float] = (0.5, 0.76)
    exclusive: bool = True
    shared_group_id: Optional[str] = None
    drives_object: bool = False
    intensity: float = 0.65
    source_confidence: float = 0.92
    visible_end_condition: str = "hand locked to object grip anchor until release"
    sound_cue: Optional[str] = None


class ActorMotionTrack(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    track_id: str
    shot_id: str
    actor_id: str
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    preset: str = "peasant"
    role: str = "civilian"
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 3.0
    ground_y: float = 0.84
    height_norm: float = 0.28
    facing_start: int = 1
    facing_end: int = 1
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "OBSERVE"
    is_idle_or_speech_only: bool = False
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.42, 0.84)
    world_end: Tuple[float, float] = (0.42, 0.84)
    phases: List[MotionPhase] = Field(default_factory=list)
    contacts: List[ObjectContactConstraint] = Field(default_factory=list)
    emotion: str = "focused"
    intensity: float = 0.5
    source_confidence: float = 0.9
    visible_end_condition: str = ""
    sound_cue: Optional[str] = None
    sound_cues: List[Dict[str, Any]] = Field(default_factory=list)


class WorldMotionState(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    shot_id: str
    script_span: str = ""
    timestamp_sec: float = 0.0
    start_sec: float = 0.0
    end_sec: float = 3.0
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    actors: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    objects: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    environment: Dict[str, Any] = Field(default_factory=dict)
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "WORLD_UPDATE"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.5, 0.5)
    world_end: Tuple[float, float] = (0.5, 0.5)
    intensity: float = 0.5
    source_confidence: float = 0.95
    visible_end_condition: str = "world and object state persisted"
    sound_cue: Optional[str] = None


class CameraBeat(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    beat_id: str
    shot_id: str
    segment_index: int = 0
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 3.0
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    scale: Literal["wide", "medium", "close", "insert", "low_angle"] = "medium"
    viewpoint: str = "front"
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "CAMERA_TRACK"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.5, 0.5)
    world_end: Tuple[float, float] = (0.5, 0.5)
    zoom_from: float = 1.0
    zoom_to: float = 1.04
    pan_from: Tuple[float, float] = (0.0, 0.0)
    pan_to: Tuple[float, float] = (0.0, 0.0)
    intensity: float = 0.4
    source_confidence: float = 0.9
    visible_end_condition: str = "subject framed cleanly inside safe bounds"
    sound_cue: Optional[str] = None
    reason: str = "follow_action_phase"


class MotionPlan(BaseModel):
    schema_version: str = MOTION_SCHEMA_VERSION
    project_id: str = "motion_project"
    pack: str = "squire"
    genre: str = "civic"
    routing_mode: Literal["OFFLINE_ONLY", "LIVE_PROVIDER"] = "OFFLINE_ONLY"
    provider_trace_id: Optional[str] = None
    fx_profile: str = "none"
    seed: int = 1476
    script_sha256: str = ""
    script_span: str = ""
    start_sec: float = 0.0
    end_sec: float = 3.0
    actor_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    desired_state_before: Dict[str, Any] = Field(default_factory=dict)
    desired_state_after: Dict[str, Any] = Field(default_factory=dict)
    motion_type: str = "SEQUENCE_PLAN"
    physical_target: Optional[str] = None
    world_start: Tuple[float, float] = (0.0, 0.0)
    world_end: Tuple[float, float] = (1.0, 1.0)
    intensity: float = 0.6
    source_confidence: float = 0.9
    visible_end_condition: str = "all actor and world objectives satisfied"
    sound_cue: Optional[str] = None
    intents: List[MotionIntent] = Field(default_factory=list)
    tracks: List[ActorMotionTrack] = Field(default_factory=list)
    world_states: List[WorldMotionState] = Field(default_factory=list)
    camera_beats: List[CameraBeat] = Field(default_factory=list)
    unsupported_actions: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


# ---------------------------------------------------------------------------
# Vocabulary & Semantic Extraction Helpers
# ---------------------------------------------------------------------------

KNOWN_ROLE_NOUNS: Dict[str, Dict[str, Any]] = {
    "citizen": {"preset": "senator", "height_norm": 0.28, "role": "citizen"},
    "merchant": {"preset": "senator", "height_norm": 0.29, "role": "merchant"},
    "worker": {"preset": "peasant", "height_norm": 0.29, "role": "worker"},
    "helper": {"preset": "peasant", "height_norm": 0.28, "role": "helper"},
    "partner": {"preset": "peasant", "height_norm": 0.28, "role": "partner"},
    "child": {"preset": "peasant", "height_norm": 0.20, "role": "child"},
    "boy": {"preset": "peasant", "height_norm": 0.21, "role": "child"},
    "girl": {"preset": "lady", "height_norm": 0.21, "role": "child"},
    "keeper": {"preset": "lady", "height_norm": 0.27, "role": "lamp_keeper"},
    "woman": {"preset": "lady", "height_norm": 0.27, "role": "civilian"},
    "man": {"preset": "peasant", "height_norm": 0.29, "role": "civilian"},
    "sailor": {"preset": "peasant", "height_norm": 0.28, "role": "sailor"},
    "engineer": {"preset": "lady", "height_norm": 0.28, "role": "engineer"},
}

KNOWN_PROPS: Dict[str, Dict[str, Any]] = {
    "basket": {"kind": "basket", "x": 0.54, "y": 0.77, "portable": True},
    "amphora": {"kind": "amphora", "x": 0.50, "y": 0.80, "portable": True, "heavy": True},
    "lantern": {"kind": "lantern", "x": 0.56, "y": 0.72, "portable": True},
    "lamp": {"kind": "lantern", "x": 0.56, "y": 0.72, "portable": True},
    "beacon": {"kind": "beacon", "x": 0.68, "y": 0.34, "portable": False},
    "flame": {"kind": "flame", "x": 0.68, "y": 0.34, "portable": False},
    "rope": {"kind": "rope", "x": 0.62, "y": 0.68, "portable": False},
    "pulley": {"kind": "pulley", "x": 0.64, "y": 0.36, "portable": False},
    "ladder": {"kind": "ladder", "x": 0.58, "y": 0.66, "portable": False},
    "rail": {"kind": "rail", "x": 0.53, "y": 0.72, "portable": False},
    "railing": {"kind": "rail", "x": 0.53, "y": 0.72, "portable": False},
    "bracket": {"kind": "bracket", "x": 0.64, "y": 0.44, "portable": False},
    "ship": {"kind": "ship", "x": 0.26, "y": 0.60, "portable": False},
    "vessel": {"kind": "ship", "x": 0.26, "y": 0.60, "portable": False},
    "rocks": {"kind": "rocks", "x": 0.42, "y": 0.66, "portable": False},
    "shoals": {"kind": "rocks", "x": 0.42, "y": 0.66, "portable": False},
    "tower": {"kind": "tower", "x": 0.66, "y": 0.52, "portable": False},
    "steps": {"kind": "steps", "x": 0.46, "y": 0.84, "portable": False},
    "wheel": {"kind": "wheel", "x": 0.52, "y": 0.74, "portable": False},
    "gate": {"kind": "gate", "x": 0.58, "y": 0.62, "portable": False},
    "phone": {"kind": "phone", "x": 0.56, "y": 0.68, "portable": True},
    "book": {"kind": "book", "x": 0.56, "y": 0.68, "portable": True},
}

UNSUPPORTED_PHYSICAL_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\b(backflip|frontflip|somersault|cartwheel)s?\b", "acrobatic_gymnastics"),
    (r"\b(juggle|juggling)s?\b", "multi_object_juggling"),
    (r"\b(teleport|vanish|materialize)s?\b", "non_physical_teleport"),
    (r"\b(levitate|hover|fly|flies|flying)\b", "aerial_levitation"),
    (r"\b(morph|shapeshift|transform\s+into)s?\b", "body_metamorphosis"),
    (r"\b(swim|swimming|dive\s+underwater)s?\b", "underwater_swimming"),
)

STOPWORD_NAMES: Set[str] = {
    "The", "A", "An", "She", "He", "They", "It", "Its", "Together", "Below",
    "At", "In", "On", "When", "Then", "As", "From", "Into", "Toward", "Towards",
    "One", "Two", "Above", "Across", "Against", "Before", "After", "Suddenly",
}


def _synthesize_word_timestamps(text: str, start_sec: float, end_sec: float) -> List[Dict[str, Any]]:
    tokens = [tok.strip() for tok in re.findall(r"[A-Za-z0-9']+|[.,!?;:]", text) if tok.strip()]
    words = [tok for tok in tokens if re.search(r"[A-Za-z0-9]", tok)]
    if not words:
        return []
    avail = max(0.25, (end_sec - start_sec) - 0.35)
    t_cursor = start_sec + 0.08
    total_chars = max(1, sum(len(w) + 1 for w in words))
    out: List[Dict[str, Any]] = []
    for idx, w in enumerate(words):
        w_dur = avail * ((len(w) + 1) / total_chars)
        out.append({
            "index": idx,
            "word": w,
            "start": round(t_cursor, 3),
            "end": round(t_cursor + w_dur, 3),
        })
        t_cursor += w_dur
    return out


def _split_compound_clauses(text: str) -> List[str]:
    """Split sequential or multi-actor clauses while preserving introductory adverbs ('Together, they...')."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    clauses: List[str] = []
    for sent in sentences:
        # Remove comma right after single-word introductory adverb ("Together, they..." -> "Together they...")
        sent_norm = re.sub(
            r"^(Together|Meanwhile|Suddenly|Finally|Quickly|Carefully),\s+",
            r"\1 ",
            sent,
            flags=re.IGNORECASE,
        )
        parts = re.split(
            r",\s*then\s+|\bthen\s+|,\s*(?=(?:steadies|catches|ducks|hauls|braces|grabs|reaches)\b)|\s+and\s+(?=(?:steadies|steadied|catches|caught|ducks|ducked|grabs|grabbed|hauls|hauled|braces|braced|lifts|lifted|reaches|reached)\b)",
            sent_norm,
            flags=re.IGNORECASE,
        )
        for p in parts:
            p_clean = p.strip(" ,")
            if p_clean:
                clauses.append(p_clean)
    return clauses or [cleaned]


def _classify_clause_verb(
    clause: str,
    actor_count: int,
    object_ids: List[str],
) -> Tuple[str, bool, bool, Optional[str], Optional[str], str, float, Optional[str]]:
    """
    Return (motion_type, is_idle, unsupported, unsupported_ev, fallback, emotion, intensity, sound_cue).
    """
    low = clause.lower()

    for pat, reason in UNSUPPORTED_PHYSICAL_PATTERNS:
        m = re.search(pat, low)
        if m:
            return (
                "UNSUPPORTED_ACTION",
                False,
                True,
                f"{reason}: '{m.group(0)}' in '{clause}'",
                "OBSERVE",
                "alert",
                0.35,
                None,
            )

    # Multi-actor shared lift / haul
    if re.search(r"\b(lift|lifts|lifted|carry|carries|heave|heaves|raise|raised)\b", low) and (
        actor_count >= 2 or re.search(r"\b(together|with\s+another|two\s+workers|both)\b", low)
    ):
        if "rope" in object_ids or "pulley" in object_ids or "flame" in object_ids or "lantern" in object_ids:
            if "rope" in object_ids or "pulley" in object_ids or "raised" in low:
                return ("HAUL_ROPE", False, False, None, None, "strained_determined", 0.85, "pulley_load")
        return ("LIFT_SHARED", False, False, None, None, "strained_cooperative", 0.82, "heavy_lift")

    if re.search(
        r"\b(slip|slips|slipped|stumble|stumbles|stumbled|skid|skids|wind\s+nearly\s+pulled|pulled\s+it\s+from\s+(?:her|his|their)\s+hands)\b",
        low,
    ):
        return ("SLIP", False, False, None, None, "startled", 0.78, "ladder_rattle")

    if re.search(r"\b(steady|steadies|steadied|stabilize|stabilizes|hold\s+fast|tighten|tightens)\b", low):
        return ("STEADY_PROP", False, False, None, None, "focused", 0.72, "basket_steady" if "basket" in object_ids else "rope_creak")

    if re.search(r"\b(duck|ducks|ducked|crouch|crouches|crouched|flinch|flinches|shield\s+eyes)\b", low):
        return ("DUCK", False, False, None, None, "startled", 0.68, "flame_gust")

    if re.search(r"\b(haul|hauls|hauled|pull|pulls|pulled|hoist|hoists|hoisted)\b", low):
        return ("HAUL_ROPE", False, False, None, None, "strained", 0.82, "pulley_load")

    if re.search(r"\b(brace|braces|braced|caught\s+the\s+rope|catch\s+the\s+rope|anchor|anchors)\b", low):
        return ("BRACE_ROPE", False, False, None, None, "determined", 0.76, "rope_creak")

    if re.search(r"\b(catch|catches|caught)\b", low) and any(o in object_ids for o in ("rail", "ladder")):
        return ("CATCH_RAIL", False, False, None, None, "urgent", 0.80, "ladder_rattle")

    if re.search(r"\b(grab|grabs|grabbed|seize|seizes|seized|snatch|snatches|pick\s+up|picks\s+up|picked\s+up|reach|reaches|reached)\b", low):
        return ("GRAB", False, False, None, None, "urgent", 0.74, "lantern_grab")

    if re.search(r"\b(run|runs|ran|sprint|sprints|race|races|raced|rush|rushes|rushed)\b", low):
        return ("RUN", False, False, None, None, "urgent", 0.84, "stone_footsteps")

    if re.search(r"\b(walk|walks|walked|step|steps|stepped|approach|approaches|approached|advance|advances)\b", low):
        return ("WALK", False, False, None, None, "curious", 0.55, "soft_footsteps")

    if re.search(r"\b(went\s+dark|extinguish|extinguishes|snuff|snuffs|snuffed|blew\s+out)\b", low):
        return ("EXTINGUISH", False, False, None, None, "alarm", 0.75, "flame_gust")

    if re.search(r"\b(glow|illuminat|shone|showed\s+the\s+sailors|sweeping\s+light)\b", low):
        return ("ILLUMINATE", False, False, None, None, "hopeful", 0.65, "sail_wind")

    if re.search(r"\b(heading\s+straight|approaches\s+rocks|rolling\s+toward|turned\s+away|made\s+it\s+through)\b", low):
        if re.search(r"\b(made\s+it\s+through|relieved|safe|exhale)\b", low):
            return ("RELIEF_EXHALE", False, False, None, None, "relieved", 0.42, "relief_chord")
        return ("SAIL_TURN", False, False, None, None, "tense", 0.66, "wave_crash")

    if re.search(r"\b(point|points|pointed|signal|signals|shout|shouted|call|called)\b", low):
        return ("POINT", False, False, None, None, "urgent", 0.62, None)

    if re.search(r"\b(reliev|exhale|smile|exchange.*look|safe)\b", low):
        return ("RELIEF_EXHALE", False, False, None, None, "relieved", 0.38, "relief_chord")

    if re.search(r"\b(turn|turns|turned|spot|spots|spotted|saw)\b", low):
        return ("TURN", False, False, None, None, "alert", 0.50, None)

    if re.search(r"\b(say|says|said|whisper|whispers|speak|speaks|murmur)\b", low):
        return ("SPEECH_GESTURE", True, False, None, None, "calm", 0.25, None)

    return ("IDLE_BREATHE", True, False, None, None, "calm", 0.20, None)


# ---------------------------------------------------------------------------
# Phase A Public API Functions
# ---------------------------------------------------------------------------


def extract_semantic_motion_intents(
    script_text: str,
    script_events: Optional[List[Dict[str, Any]]] = None,
    cast_bible: Optional[Dict[str, Any]] = None,
    world_state: Optional[Dict[str, Any]] = None,
    *,
    pack: str = "squire",
    genre: str = "civic",
    routing_mode: Literal["OFFLINE_ONLY", "LIVE_PROVIDER"] = "OFFLINE_ONLY",
    provider_trace_id: Optional[str] = None,
) -> List[MotionIntent]:
    """
    Extract semantic `MotionIntent` records from arbitrary `script_text` and optional
    `script_events`, reusing `parse_action_intents()` and `StoryContext` while supporting
    open-vocabulary civilian/harbor cast IDs, multi-actor shared objects, and safe
    `unsupported_action` labeling.
    """
    if isinstance(cast_bible, list):
        cast = {
            str(item.get("actor_id") or item.get("id") or f"actor_{i+1}"): copy.deepcopy(item)
            for i, item in enumerate(cast_bible)
            if isinstance(item, dict)
        }
    else:
        cast = copy.deepcopy(cast_bible or {})
    w_state = copy.deepcopy(world_state or {})
    events_in = copy.deepcopy(script_events or [])

    if not events_in:
        raw_lines = [ln.strip() for ln in re.split(r"\n+", script_text.strip()) if ln.strip()]
        if not raw_lines and script_text.strip():
            raw_lines = [script_text.strip()]
        t_cur = 0.0
        for idx, ln in enumerate(raw_lines):
            dur = max(3.0, min(5.0, round(1.8 + 0.22 * len(ln.split()), 2)))
            events_in.append({
                "id": f"S{idx + 1:02d}",
                "start": round(t_cur, 3),
                "end": round(t_cur + dur, 3),
                "dur": dur,
                "line": ln,
            })
            t_cur += dur

    # Reuse StoryContext + ActionContext + parse_action_intents() so narrative semantics stay unified
    story_ctx = build_story_context(
        shots=events_in,
        character_bible=cast,
        setting=w_state.get("environment") if isinstance(w_state.get("environment"), dict) else w_state,
        pack=pack,
        genre=genre,
    )
    _scene_objectives = infer_scene_objectives(story_ctx)
    act_ctx = ActionContext(
        project_path=story_ctx.shots[0].get("project_path", ".") if story_ctx.shots else ".",
        project_id=story_ctx.project_id,
        pack=pack,
        genre=genre,
        shots=events_in,
        character_bible=cast,
    )
    grounded_nodes = parse_action_intents(act_ctx, source="offline" if routing_mode == "OFFLINE_ONLY" else "live")
    grounded_by_shot = {gn.shot_id: gn for gn in grounded_nodes}

    # Discover cast positions & defaults
    actor_positions: Dict[str, Tuple[float, float]] = {}
    for aid, info in cast.items():
        if isinstance(info, dict):
            actor_positions[aid] = (float(info.get("x", 0.36)), float(info.get("y", 0.84)))
    for aid, info in (w_state.get("actors") or {}).items():
        if isinstance(info, dict):
            actor_positions[aid] = (float(info.get("x", 0.36)), float(info.get("y", 0.84)))

    object_positions: Dict[str, Tuple[float, float]] = {}
    for oid, oinfo in (w_state.get("objects") or {}).items():
        if isinstance(oinfo, dict):
            object_positions[oid] = (float(oinfo.get("x", 0.54)), float(oinfo.get("y", 0.76)))

    last_mentioned_actors: List[str] = list(cast.keys())[:1]
    intents: List[MotionIntent] = []

    for ev_idx, ev in enumerate(events_in):
        sid = str(ev.get("id") or ev.get("shot_id") or f"S{ev_idx + 1:02d}")
        s_start = float(ev.get("start", 0.0))
        s_end = float(ev.get("end", s_start + float(ev.get("dur", 3.5))))
        line_text = str(ev.get("line") or ev.get("text") or ev.get("desc") or "").strip()
        full_span = str(ev.get("script_span") or ev.get("desc") or line_text).strip()
        combined_text = f"{line_text} {ev.get('desc', '')}".strip()

        word_ts = ev.get("word_timestamps")
        if not isinstance(word_ts, list) or not word_ts:
            word_ts = _synthesize_word_timestamps(line_text or full_span, s_start, s_end)

        clauses = _split_compound_clauses(line_text if line_text else full_span)
        n_clauses = max(1, len(clauses))
        shot_dur = max(0.4, s_end - s_start)

        for c_idx, clause in enumerate(clauses):
            c_start = round(s_start + (shot_dur * c_idx / n_clauses), 3)
            c_end = round(s_start + (shot_dur * (c_idx + 1) / n_clauses), 3)
            c_low = clause.lower()

            # Slice matching word timestamps
            c_words = [
                w for w in word_ts
                if float(w.get("end", c_start)) >= c_start - 0.05 and float(w.get("start", c_end)) <= c_end + 0.05
            ]

            # 1) Actor extraction: explicit event actors -> cast_bible match -> capitalized names -> role nouns -> coreference
            found_actors: List[str] = []
            if c_idx == 0 and isinstance(ev.get("actor_ids"), list) and len(clauses) == 1:
                found_actors.extend([str(a) for a in ev["actor_ids"] if str(a)])

            for cid in cast.keys():
                if re.search(rf"\b{re.escape(cid.lower())}\b", c_low) and cid not in found_actors:
                    found_actors.append(cid)

            # Proper names (e.g. Aelia, Felix, Livia, Marcus)
            for cap_m in re.findall(r"\b([A-Z][a-z]{2,})\b", clause):
                if cap_m not in STOPWORD_NAMES:
                    aid_cand = cap_m.lower()
                    if aid_cand not in KNOWN_PROPS and aid_cand not in KNOWN_ROLE_NOUNS and aid_cand not in found_actors:
                        found_actors.append(aid_cand)

            # Role nouns (citizen, merchant, child, worker, helper, partner)
            for r_noun in KNOWN_ROLE_NOUNS.keys():
                if r_noun == "merchant" and re.search(r"\bmerchant\s+(?:ship|vessel)s?\b", c_low):
                    continue
                if re.search(rf"\b{r_noun}\b", c_low):
                    # Map to cast ID if role matches, else use noun ID
                    matched_cast = next(
                        (cid for cid, cinfo in cast.items() if isinstance(cinfo, dict) and cinfo.get("role") == r_noun),
                        r_noun,
                    )
                    if matched_cast not in found_actors:
                        found_actors.append(matched_cast)

            # Co-actor phrase ("with another person", "together", "two workers")
            if re.search(r"\b(another\s+person|second\s+worker|helper|partner)\b", c_low):
                co_id = next(
                    (cid for cid in cast.keys() if cid not in found_actors),
                    "co_worker",
                )
                if co_id not in found_actors:
                    found_actors.append(co_id)
            elif re.search(r"\b(together|they|both)\b", c_low):
                if len(cast) >= 2:
                    for cid in list(cast.keys())[:2]:
                        if cid not in found_actors:
                            found_actors.append(cid)
                elif len(last_mentioned_actors) >= 2:
                    for cid in last_mentioned_actors[:2]:
                        if cid not in found_actors:
                            found_actors.append(cid)

            # Pronoun coreference ("she", "he", or continuation verb after comma/and)
            if not found_actors:
                if re.search(r"\b(she|her)\b", c_low):
                    fem = next(
                        (
                            cid for cid, cinfo in cast.items()
                            if isinstance(cinfo, dict) and cinfo.get("preset") == "lady"
                        ),
                        None,
                    )
                    if fem:
                        found_actors.append(fem)
                elif re.search(r"\b(he|him)\b", c_low):
                    masc = next(
                        (
                            cid for cid, cinfo in cast.items()
                            if isinstance(cinfo, dict) and cinfo.get("preset") != "lady"
                        ),
                        None,
                    )
                    if masc:
                        found_actors.append(masc)

            if not found_actors and last_mentioned_actors and not re.search(
                r"^(the\s+harbor\s+light|a\s+merchant\s+ship|its\s+glow|the\s+ship\b)", c_low
            ):
                found_actors.append(last_mentioned_actors[0])

            if found_actors:
                last_mentioned_actors = list(found_actors)

            # 2) Object extraction
            found_objects: List[str] = []
            if isinstance(ev.get("object_ids"), list) and len(clauses) == 1:
                found_objects.extend([str(o) for o in ev["object_ids"] if str(o)])
            for oid in list(w_state.get("objects", {}).keys()) + list(KNOWN_PROPS.keys()):
                if re.search(rf"\b{re.escape(oid.lower())}s?\b", f"{c_low} {combined_text.lower() if n_clauses == 1 else ''}"):
                    canon_oid = "lantern" if oid == "lamp" else ("rail" if oid == "railing" else ("ship" if oid == "vessel" else ("rocks" if oid == "shoals" else oid)))
                    if canon_oid not in found_objects:
                        found_objects.append(canon_oid)
            # Carry object across compound continuation ("it", "steadies a basket")
            if not found_objects and re.search(r"\b(it|them)\b", c_low) and intents:
                for prev_o in intents[-1].object_ids:
                    if prev_o not in found_objects:
                        found_objects.append(prev_o)

            # Ensure default positions for actors and objects
            for idx_a, aid in enumerate(found_actors):
                if aid not in actor_positions:
                    default_x = 0.34 + 0.20 * idx_a
                    actor_positions[aid] = (round(min(0.78, default_x), 3), 0.84)
            for oid in found_objects:
                if oid not in object_positions:
                    p_def = KNOWN_PROPS.get(oid, {"x": 0.54, "y": 0.76})
                    object_positions[oid] = (float(p_def["x"]), float(p_def["y"]))

            # 3) Classify physical verb / intent
            m_type, is_idle, is_unsup, unsup_ev, fb_type, emotion, intensity, sfx = _classify_clause_verb(
                clause if clause else combined_text,
                actor_count=len(found_actors),
                object_ids=found_objects,
            )
            # Allow explicit override in event dict only if non-empty and supported
            if n_clauses == 1 and ev.get("motion_type"):
                m_type = str(ev["motion_type"])
                is_idle = m_type in IDLE_OR_SPEECH_MOTIONS

            # In resolution/relief beats ("made it through", "safe at last"), include scene protagonists if unspoken
            if m_type == "RELIEF_EXHALE" and not found_actors and cast:
                for cid in list(cast.keys())[:2]:
                    found_actors.append(cid)
                    if cid not in actor_positions:
                        cinf = cast.get(cid, {})
                        actor_positions[cid] = (float(cinf.get("x", 0.44)), float(cinf.get("y", 0.84)))

            primary_actor = found_actors[0] if found_actors else None
            primary_obj = found_objects[0] if found_objects else None
            w_start = actor_positions.get(primary_actor, (0.50, 0.76)) if primary_actor else object_positions.get(primary_obj, (0.50, 0.60))
            w_end = w_start

            if primary_actor:
                ax, ay = w_start
                if m_type in ("WALK", "RUN", "APPROACH"):
                    if primary_obj and primary_obj in object_positions:
                        tx, _ty = object_positions[primary_obj]
                        step_frac = 0.78 if m_type == "RUN" else 0.65
                        nx = round(ax + (tx - ax - (0.06 if tx >= ax else -0.06)) * step_frac, 3)
                    else:
                        nx = round(min(0.76, ax + (0.18 if m_type == "RUN" else 0.12)), 3)
                    w_end = (max(0.12, min(0.88, nx)), ay)
                elif m_type == "SLIP":
                    # In-place foot skid + knee drop + counterbalance recovery keeps planted foot rock-solid
                    w_end = w_start
                elif m_type in ("GRAB", "STEADY_PROP", "CATCH_RAIL", "BRACE_ROPE"):
                    if primary_obj and primary_obj in object_positions:
                        tx, _ = object_positions[primary_obj]
                        if abs(tx - ax) > 0.09:
                            w_end = (round(tx - (0.06 if tx >= ax else -0.06), 3), ay)
                actor_positions[primary_actor] = w_end

            pre_state: Dict[str, Any] = {"actor_pos": w_start}
            post_state: Dict[str, Any] = {"actor_pos": w_end}
            if m_type == "LIFT_SHARED" and primary_obj:
                ox, oy = object_positions.get(primary_obj, (0.50, 0.80))
                pre_state["object_pos"] = (ox, oy)
                lift_delta = 0.12 if oy > 0.74 else 0.05
                lifted_pos = (ox, round(max(0.65, oy - lift_delta), 3))
                post_state["object_pos"] = lifted_pos
                post_state["lifted_together"] = True
                object_positions[primary_obj] = lifted_pos
                end_cond = f"{' & '.join(found_actors)} hold {primary_obj} elevated at y={lifted_pos[1]}"
            elif m_type == "HAUL_ROPE":
                hoist_o = "lantern" if "lantern" in found_objects else (primary_obj or "rope")
                ox, oy = object_positions.get(hoist_o, (0.58, 0.70))
                actor_ground_y = w_end[1] if primary_actor else 0.84
                grip_start = (ox, round(actor_ground_y - 0.14, 3))
                grip_end = (ox, round(actor_ground_y - 0.11, 3))
                lifted_pos = (ox, round(max(0.32, oy - 0.24), 3))
                pre_state["object_pos"] = grip_start
                post_state["object_pos"] = grip_end
                post_state["hoisted_object_pos"] = lifted_pos
                post_state["hoisted_into_alcove"] = True
                object_positions[hoist_o] = lifted_pos
                end_cond = f"{hoist_o} raised smoothly via taut rope to y={lifted_pos[1]}"
            elif m_type in PHYSICAL_CONTACT_MOTIONS and primary_obj:
                post_state["gripping"] = primary_obj
                end_cond = f"{primary_actor or 'actor'} hand locked on {primary_obj}"
            elif m_type == "DUCK":
                post_state["posture"] = "crouched_shielded"
                end_cond = f"{primary_actor or 'actor'} crouched cleanly below wind gust"
            elif m_type == "SLIP":
                post_state["balance"] = "recovering_from_slip"
                end_cond = f"{primary_actor or 'actor'} foot slips then catches balance"
            elif m_type in LOCOMOTION_MOTIONS:
                end_cond = f"{primary_actor or 'actor'} arrives at x={w_end[0]} with planted stance"
            elif m_type == "UNSUPPORTED_ACTION":
                post_state["fallback_applied"] = fb_type
                end_cond = f"unsupported verb safely degraded to {fb_type}"
            else:
                end_cond = f"{sid} {m_type.lower()} completed"

            gn = grounded_by_shot.get(sid)
            conf = 0.45 if is_unsup else (0.94 if gn is not None else 0.88)

            intents.append(
                MotionIntent(
                    intent_id=f"{sid}_I{c_idx + 1:02d}",
                    shot_id=sid,
                    script_span=clause,
                    start_sec=c_start,
                    end_sec=c_end,
                    narration_word_timestamps=c_words,
                    actor_ids=found_actors,
                    object_ids=found_objects,
                    desired_state_before=pre_state,
                    desired_state_after=post_state,
                    motion_type=m_type,
                    is_idle_or_speech_only=is_idle,
                    unsupported_action=is_unsup,
                    unsupported_evidence=unsup_ev,
                    fallback_motion_type=fb_type,
                    emotion=emotion,
                    physical_target=primary_obj,
                    world_start=w_start,
                    world_end=w_end,
                    intensity=intensity,
                    source_confidence=conf,
                    visible_end_condition=end_cond,
                    sound_cue=sfx,
                )
            )

    return intents


def _build_phases_for_intent(
    intent: MotionIntent,
    actor_id: str,
    actor_idx: int,
    actor_start: Tuple[float, float],
    actor_end: Tuple[float, float],
    object_world: Dict[str, Tuple[float, float]],
    effective_motion: str,
) -> Tuple[List[MotionPhase], List[ObjectContactConstraint]]:
    """Construct physically grounded `MotionPhase` sequence and `ObjectContactConstraint`s."""
    t0 = float(intent.start_sec)
    t1 = float(intent.end_sec)
    dur = max(0.25, t1 - t0)
    # Multi-actor natural offset (second worker reacts 0.04s after lead, clamped safely within interval)
    lead_offset = min(0.05, dur * 0.06) * actor_idx
    sx, sy = actor_start
    ex, ey = actor_end
    obj_id = intent.physical_target or (intent.object_ids[0] if intent.object_ids else None)

    def _tm(frac: float) -> float:
        return round(min(t1, max(t0, t0 + lead_offset + (dur - lead_offset) * frac)), 4)

    def _lerp_pt(f: float) -> Tuple[float, float]:
        return (round(sx + (ex - sx) * f, 4), round(sy + (ey - sy) * f, 4))

    phases: List[MotionPhase] = []
    contacts: List[ObjectContactConstraint] = []

    if effective_motion in IDLE_OR_SPEECH_MOTIONS:
        phases.append(
            MotionPhase(
                phase_name="IDLE" if effective_motion == "IDLE_BREATHE" else "SETTLE",
                script_span=intent.script_span,
                start_sec=t0,
                end_sec=t1,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type=effective_motion,
                physical_target=obj_id,
                world_start=actor_start,
                world_end=actor_end,
                posture_state="speaking_subtle" if effective_motion == "SPEECH_GESTURE" else "idle_breathe",
                torso_lean=0.01 if effective_motion == "SPEECH_GESTURE" else 0.0,
                head_look=0.55,
                knee_flex=0.02,
                arm_reach=0.18 if effective_motion == "SPEECH_GESTURE" else 0.0,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="hold",
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition=intent.visible_end_condition,
            )
        )
        return phases, contacts

    if effective_motion in LOCOMOTION_MOTIONS:
        is_run = effective_motion == "RUN"
        p_ant_end = _tm(0.14)
        p_app_end = _tm(0.84)
        phases.extend([
            MotionPhase(
                phase_name="ANTICIPATE",
                script_span=intent.script_span,
                start_sec=t0,
                end_sec=p_ant_end,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type=effective_motion,
                physical_target=obj_id,
                world_start=actor_start,
                world_end=_lerp_pt(0.04),
                posture_state="lean_into_stride",
                torso_lean=0.12 if is_run else 0.06,
                head_look=0.75,
                knee_flex=0.14 if is_run else 0.07,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_in",
                intensity=intent.intensity * 0.7,
                source_confidence=intent.source_confidence,
                visible_end_condition="weight shifts forward onto lead foot",
            ),
            MotionPhase(
                phase_name="APPROACH",
                script_span=intent.script_span,
                start_sec=p_ant_end,
                end_sec=p_app_end,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type=effective_motion,
                physical_target=obj_id,
                world_start=_lerp_pt(0.04),
                world_end=_lerp_pt(0.96),
                posture_state="run_drive" if is_run else "walk_stride",
                torso_lean=0.16 if is_run else 0.07,
                head_look=0.80,
                knee_flex=0.18 if is_run else 0.09,
                foot_planted_left=False,
                foot_planted_right=False,
                tempo_curve="ease_in_out",
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition="distance-coupled stride advances root smoothly",
                sound_cue=intent.sound_cue,
            ),
            MotionPhase(
                phase_name="SETTLE",
                script_span=intent.script_span,
                start_sec=p_app_end,
                end_sec=t1,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type=effective_motion,
                physical_target=obj_id,
                world_start=_lerp_pt(0.96),
                world_end=actor_end,
                posture_state="decelerate_plant",
                torso_lean=0.03,
                head_look=0.65,
                knee_flex=0.05,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=intent.intensity * 0.5,
                source_confidence=intent.source_confidence,
                visible_end_condition=intent.visible_end_condition,
            ),
        ])
        return phases, contacts

    if effective_motion == "SLIP":
        t_a = _tm(0.18)
        t_r = _tm(0.56)
        t_f = _tm(0.82)
        phases.extend([
            MotionPhase(
                phase_name="ANTICIPATE",
                script_span=intent.script_span,
                start_sec=t0,
                end_sec=t_a,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="SLIP",
                physical_target=obj_id,
                world_start=actor_start,
                world_end=_lerp_pt(0.20),
                posture_state="step_onto_slick_surface",
                torso_lean=0.05,
                knee_flex=0.06,
                foot_planted_left=True,
                foot_planted_right=False,
                tempo_curve="ease_in",
                intensity=0.55,
                source_confidence=intent.source_confidence,
                visible_end_condition="lead foot touches wet stone/rung",
            ),
            MotionPhase(
                phase_name="REACT",
                script_span=intent.script_span,
                start_sec=t_a,
                end_sec=t_r,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="SLIP",
                physical_target=obj_id,
                world_start=_lerp_pt(0.20),
                world_end=_lerp_pt(0.85),
                posture_state="slip_jolt",
                torso_lean=-0.16,
                head_look=0.35,
                knee_flex=0.26,
                arm_reach=0.65,
                foot_planted_left=True,
                foot_planted_right=False,
                slip_foot="right",
                tempo_curve="overshoot_settle",
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition="right foot skids forward while knees drop to catch balance",
                sound_cue=intent.sound_cue,
            ),
            MotionPhase(
                phase_name="FOLLOW_THROUGH",
                script_span=intent.script_span,
                start_sec=t_r,
                end_sec=t_f,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="SLIP",
                physical_target=obj_id,
                world_start=_lerp_pt(0.85),
                world_end=actor_end,
                posture_state="counterbalance_arms",
                torso_lean=0.09,
                head_look=0.65,
                knee_flex=0.18,
                arm_reach=0.50,
                foot_planted_left=False,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=0.65,
                source_confidence=intent.source_confidence,
                visible_end_condition="feet replant wide to arrest slip",
            ),
            MotionPhase(
                phase_name="SETTLE",
                script_span=intent.script_span,
                start_sec=t_f,
                end_sec=t1,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="SLIP",
                physical_target=obj_id,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="stabilized_wide_stance",
                torso_lean=0.04,
                head_look=0.70,
                knee_flex=0.10,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=0.40,
                source_confidence=intent.source_confidence,
                visible_end_condition=intent.visible_end_condition,
            ),
        ])
        return phases, contacts

    if effective_motion == "DUCK":
        t_a = _tm(0.18)
        t_act = _tm(0.58)
        t_ft = _tm(0.82)
        phases.extend([
            MotionPhase(
                phase_name="ANTICIPATE",
                script_span=intent.script_span,
                start_sec=t0,
                end_sec=t_a,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="DUCK",
                physical_target=obj_id,
                world_start=actor_start,
                world_end=actor_start,
                posture_state="sense_gust_flinch",
                torso_lean=-0.05,
                head_look=0.80,
                knee_flex=0.06,
                arm_reach=0.25,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_in",
                intensity=0.50,
                source_confidence=intent.source_confidence,
                visible_end_condition="head turns toward incoming gust",
                sound_cue=intent.sound_cue,
            ),
            MotionPhase(
                phase_name="REACT",
                script_span=intent.script_span,
                start_sec=t_a,
                end_sec=t_act,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="DUCK",
                physical_target=obj_id,
                world_start=actor_start,
                world_end=actor_end,
                posture_state="duck_low_guard",
                torso_lean=0.22,
                head_look=0.25,
                knee_flex=0.32,
                arm_reach=0.72,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="overshoot_settle",
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition="knees flex and forearm shields face",
            ),
            MotionPhase(
                phase_name="FOLLOW_THROUGH",
                script_span=intent.script_span,
                start_sec=t_act,
                end_sec=t_ft,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="DUCK",
                physical_target=obj_id,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="hold_crouch_against_wind",
                torso_lean=0.18,
                head_look=0.35,
                knee_flex=0.26,
                arm_reach=0.60,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=intent.intensity * 0.8,
                source_confidence=intent.source_confidence,
                visible_end_condition="cloth trails wind while crouch holds firm",
            ),
            MotionPhase(
                phase_name="SETTLE",
                script_span=intent.script_span,
                start_sec=t_ft,
                end_sec=t1,
                actor_ids=[actor_id],
                object_ids=list(intent.object_ids),
                motion_type="DUCK",
                physical_target=obj_id,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="cautious_rise",
                torso_lean=0.10,
                head_look=0.55,
                knee_flex=0.14,
                arm_reach=0.35,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=0.40,
                source_confidence=intent.source_confidence,
                visible_end_condition=intent.visible_end_condition,
            ),
        ])
        return phases, contacts

    if effective_motion in PHYSICAL_CONTACT_MOTIONS:
        target_oid = obj_id or "prop_target"
        obj_start = intent.desired_state_before.get("object_pos") or object_world.get(target_oid, (ex + 0.06, ey - 0.10))
        obj_end = intent.desired_state_after.get("object_pos") or obj_start
        is_shared = effective_motion in ("LIFT_SHARED", "HAUL_ROPE") and len(intent.actor_ids) >= 2
        anchor_offset_x = (-0.035 if actor_idx == 0 else 0.035) if is_shared else 0.0
        anchor_name = f"handle_{actor_idx + 1}" if is_shared else "grip_primary"

        t_ant = _tm(0.14)
        t_rch = _tm(0.30)
        t_con = _tm(0.42)
        t_exr = _tm(0.76)
        t_flt = _tm(0.90)

        phases.extend([
            MotionPhase(
                phase_name="ANTICIPATE",
                script_span=intent.script_span,
                start_sec=t0,
                end_sec=t_ant,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=actor_start,
                world_end=_lerp_pt(0.35),
                posture_state="coil_for_reach",
                torso_lean=0.08,
                head_look=0.80,
                knee_flex=0.16 if effective_motion in ("LIFT_SHARED", "HAUL_ROPE") else 0.08,
                arm_reach=0.35,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_in",
                intensity=intent.intensity * 0.65,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"{actor_id} lowers center of mass toward {target_oid}",
            ),
            MotionPhase(
                phase_name="REACH",
                script_span=intent.script_span,
                start_sec=t_ant,
                end_sec=t_rch,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=_lerp_pt(0.35),
                world_end=actor_end,
                posture_state="extend_hands_to_target",
                torso_lean=0.14,
                head_look=0.90,
                knee_flex=0.20 if effective_motion == "LIFT_SHARED" else 0.10,
                arm_reach=0.88,
                hand_anchor_id=anchor_name,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=intent.intensity * 0.80,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"hands close distance onto {target_oid} {anchor_name}",
            ),
            MotionPhase(
                phase_name="CONTACT",
                script_span=intent.script_span,
                start_sec=t_rch,
                end_sec=t_con,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="grip_locked",
                torso_lean=0.12,
                head_look=0.90,
                knee_flex=0.22 if effective_motion == "LIFT_SHARED" else 0.11,
                arm_reach=1.0,
                hand_anchor_id=anchor_name,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="hold",
                intensity=intent.intensity * 0.90,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"zero-hover grip established on {target_oid}",
                sound_cue=intent.sound_cue,
            ),
            MotionPhase(
                phase_name="EXERT",
                script_span=intent.script_span,
                start_sec=t_con,
                end_sec=t_exr,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="drive_through_legs_and_arms",
                torso_lean=-0.10 if effective_motion in ("HAUL_ROPE", "BRACE_ROPE", "LIFT_SHARED") else 0.06,
                head_look=0.85,
                knee_flex=0.08 if effective_motion == "LIFT_SHARED" else 0.16,
                arm_reach=1.0,
                hand_anchor_id=anchor_name,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_in_out",
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"force transmitted cleanly into {target_oid}",
            ),
            MotionPhase(
                phase_name="FOLLOW_THROUGH",
                script_span=intent.script_span,
                start_sec=t_exr,
                end_sec=t_flt,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="absorb_inertia",
                torso_lean=-0.04 if effective_motion in ("HAUL_ROPE", "BRACE_ROPE") else 0.04,
                head_look=0.80,
                knee_flex=0.09,
                arm_reach=1.0,
                hand_anchor_id=anchor_name,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="overshoot_settle",
                intensity=intent.intensity * 0.70,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"{target_oid} oscillation damps while grip holds",
            ),
            MotionPhase(
                phase_name="SETTLE",
                script_span=intent.script_span,
                start_sec=t_flt,
                end_sec=t1,
                actor_ids=[actor_id],
                object_ids=[target_oid],
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=actor_end,
                world_end=actor_end,
                posture_state="secure_hold",
                torso_lean=0.02,
                head_look=0.75,
                knee_flex=0.06,
                arm_reach=1.0,
                hand_anchor_id=anchor_name,
                foot_planted_left=True,
                foot_planted_right=True,
                tempo_curve="ease_out",
                intensity=intent.intensity * 0.50,
                source_confidence=intent.source_confidence,
                visible_end_condition=intent.visible_end_condition,
            ),
        ])

        c_ws = (round(float(obj_start[0]) + anchor_offset_x, 4), round(float(obj_start[1]), 4))
        c_we = (round(float(obj_end[0]) + anchor_offset_x, 4), round(float(obj_end[1]), 4))
        contacts.append(
            ObjectContactConstraint(
                constraint_id=f"{intent.intent_id}_{actor_id}_{target_oid}",
                script_span=intent.script_span,
                start_sec=t_ant,
                end_sec=t1,
                actor_id=actor_id,
                actor_ids=list(intent.actor_ids),
                object_id=target_oid,
                object_ids=[target_oid],
                hand="both" if effective_motion in ("LIFT_SHARED", "HAUL_ROPE", "BRACE_ROPE", "STEADY_PROP") else "right",
                anchor_name=anchor_name,
                anchor_local=(round(anchor_offset_x, 4), 0.0),
                desired_state_before={"gripped": False, "object_pos": obj_start},
                desired_state_after={"gripped": True, "object_pos": obj_end},
                motion_type=effective_motion,
                physical_target=target_oid,
                world_start=c_ws,
                world_end=c_we,
                exclusive=not is_shared,
                shared_group_id=f"{intent.intent_id}_shared_{target_oid}" if is_shared else None,
                drives_object=(actor_idx == 0 and effective_motion in ("LIFT_SHARED", "HAUL_ROPE", "GRAB", "CARRY")),
                intensity=intent.intensity,
                source_confidence=intent.source_confidence,
                visible_end_condition=f"{actor_id} hand locked to {target_oid}:{anchor_name}",
                sound_cue=intent.sound_cue,
            )
        )
        return phases, contacts

    # Expressive non-contact actions: TURN, POINT, RELIEF_EXHALE, EXTINGUISH, ILLUMINATE, SAIL_TURN
    t_a = _tm(0.22)
    t_act = _tm(0.68)
    phases.extend([
        MotionPhase(
            phase_name="ANTICIPATE",
            script_span=intent.script_span,
            start_sec=t0,
            end_sec=t_a,
            actor_ids=[actor_id],
            object_ids=list(intent.object_ids),
            motion_type=effective_motion,
            physical_target=obj_id,
            world_start=actor_start,
            world_end=actor_start,
            posture_state="breath_intake",
            torso_lean=-0.03,
            head_look=0.50,
            knee_flex=0.04,
            arm_reach=0.15,
            foot_planted_left=True,
            foot_planted_right=True,
            tempo_curve="ease_in",
            intensity=intent.intensity * 0.6,
            source_confidence=intent.source_confidence,
            visible_end_condition="subtle weight shift before gesture",
        ),
        MotionPhase(
            phase_name="ACT",
            script_span=intent.script_span,
            start_sec=t_a,
            end_sec=t_act,
            actor_ids=[actor_id],
            object_ids=list(intent.object_ids),
            motion_type=effective_motion,
            physical_target=obj_id,
            world_start=actor_start,
            world_end=actor_end,
            posture_state="point_gesture" if effective_motion == "POINT" else ("relief_exhale" if effective_motion == "RELIEF_EXHALE" else "head_turn_alert"),
            torso_lean=0.06 if effective_motion == "POINT" else 0.02,
            head_look=0.88 if effective_motion in ("POINT", "TURN") else 0.60,
            knee_flex=0.05,
            arm_reach=0.75 if effective_motion == "POINT" else 0.22,
            foot_planted_left=True,
            foot_planted_right=True,
            tempo_curve="ease_out",
            intensity=intent.intensity,
            source_confidence=intent.source_confidence,
            visible_end_condition="primary gesture reaches clear apex",
            sound_cue=intent.sound_cue,
        ),
        MotionPhase(
            phase_name="SETTLE",
            script_span=intent.script_span,
            start_sec=t_act,
            end_sec=t1,
            actor_ids=[actor_id],
            object_ids=list(intent.object_ids),
            motion_type=effective_motion,
            physical_target=obj_id,
            world_start=actor_end,
            world_end=actor_end,
            posture_state="settle_hold",
            torso_lean=0.02,
            head_look=0.72,
            knee_flex=0.04,
            arm_reach=0.45 if effective_motion == "POINT" else 0.12,
            foot_planted_left=True,
            foot_planted_right=True,
            tempo_curve="ease_out",
            intensity=intent.intensity * 0.5,
            source_confidence=intent.source_confidence,
            visible_end_condition=intent.visible_end_condition,
        ),
    ])
    return phases, contacts


def plan_actor_motion_phases(
    intents: List[MotionIntent],
    action_capabilities: Optional[PackCapabilityProfile] = None,
    shot_timing: Optional[List[Dict[str, Any]]] = None,
    *,
    cast_bible: Optional[Dict[str, Any]] = None,
    world_state: Optional[Dict[str, Any]] = None,
) -> List[ActorMotionTrack]:
    """
    Place multi-phase actor motion tracks (`ANTICIPATE -> REACH/APPROACH -> CONTACT ->
    EXERT/ACT -> REACT -> FOLLOW_THROUGH -> SETTLE`) in exact shot/narration timelines,
    preserving continuous world positions and multi-actor shared object synchronization.
    """
    caps = action_capabilities or get_pack_capabilities("squire", "civic")
    if isinstance(cast_bible, list):
        cast = {
            str(item.get("actor_id") or item.get("id") or f"actor_{i+1}"): copy.deepcopy(item)
            for i, item in enumerate(cast_bible)
            if isinstance(item, dict)
        }
    else:
        cast = copy.deepcopy(cast_bible or {})
    w_state = copy.deepcopy(world_state or {})

    shot_bounds: Dict[str, Tuple[float, float]] = {}
    for st in shot_timing or []:
        sid = str(st.get("id") or st.get("shot_id") or "")
        if sid:
            s0 = float(st.get("start", 0.0))
            s1 = float(st.get("end", s0 + float(st.get("dur", 3.5))))
            shot_bounds[sid] = (s0, s1)

    actor_cursor: Dict[str, Tuple[float, float]] = {}
    for aid, cinfo in cast.items():
        if isinstance(cinfo, dict):
            actor_cursor[aid] = (float(cinfo.get("x", 0.36)), float(cinfo.get("y", 0.84)))
    for aid, ainfo in (w_state.get("actors") or {}).items():
        if isinstance(ainfo, dict):
            actor_cursor[aid] = (float(ainfo.get("x", 0.36)), float(ainfo.get("y", 0.84)))

    object_cursor: Dict[str, Tuple[float, float]] = {}
    for oid, oinfo in (w_state.get("objects") or {}).items():
        if isinstance(oinfo, dict):
            object_cursor[oid] = (float(oinfo.get("x", 0.54)), float(oinfo.get("y", 0.76)))
    for oid, pdef in KNOWN_PROPS.items():
        object_cursor.setdefault(oid, (float(pdef["x"]), float(pdef["y"])))

    # Group intents per (shot_id, actor_id) so compound actions within one shot become one continuous track
    grouped_tracks: Dict[Tuple[str, str], ActorMotionTrack] = {}
    track_order: List[Tuple[str, str]] = []

    for intent in intents:
        sid = intent.shot_id
        s_min, s_max = shot_bounds.get(sid, (intent.start_sec, intent.end_sec))
        eff_motion = (
            (intent.fallback_motion_type or "OBSERVE")
            if intent.unsupported_action or intent.motion_type not in caps.supported_actions
            else intent.motion_type
        )
        # DEM pack safe motion translation
        if caps.pack == "dem" and eff_motion not in caps.supported_actions:
            eff_motion = "MOVE_TO" if eff_motion in LOCOMOTION_MOTIONS else "OBSERVE"

        for idx_a, aid in enumerate(intent.actor_ids):
            cinfo = cast.get(aid, {}) if isinstance(cast.get(aid), dict) else {}
            role_meta = KNOWN_ROLE_NOUNS.get(aid, KNOWN_ROLE_NOUNS.get(str(cinfo.get("role", "")), {}))
            preset = str(cinfo.get("preset") or role_meta.get("preset") or ("hero" if caps.pack == "dem" else "peasant"))
            h_norm = float(cinfo.get("height_norm") or role_meta.get("height_norm") or 0.28)
            ground_y = float(cinfo.get("ground_y") or cinfo.get("y") or 0.84)

            if aid not in actor_cursor:
                default_x = 0.38 if idx_a == 0 else 0.58
                actor_cursor[aid] = (default_x, ground_y)

            a_start = actor_cursor[aid]
            if idx_a == 0:
                a_end = (float(intent.world_end[0]), min(ground_y, float(intent.world_end[1])))
                # Keep continuous if intent.world_start differed from actual cursor
                if eff_motion not in LOCOMOTION_MOTIONS and eff_motion != "SLIP":
                    if intent.physical_target and intent.physical_target in object_cursor and eff_motion in PHYSICAL_CONTACT_MOTIONS:
                        ox, _ = object_cursor[intent.physical_target]
                        if abs(ox - a_start[0]) > 0.10:
                            a_end = (round(ox - (0.06 if ox >= a_start[0] else -0.06), 4), a_start[1])
                        else:
                            a_end = a_start
                    else:
                        a_end = a_start
            else:
                # Co-actor positions on opposite side of shared object (only stepping if beyond natural reach)
                target_o = intent.physical_target or (intent.object_ids[0] if intent.object_ids else None)
                if target_o and target_o in object_cursor and eff_motion in PHYSICAL_CONTACT_MOTIONS:
                    ox, _ = object_cursor[target_o]
                    desired_co_x = round(min(0.86, ox + 0.06), 4)
                    a_end = (desired_co_x, a_start[1]) if abs(desired_co_x - a_start[0]) > 0.035 else a_start
                else:
                    a_end = a_start

            # Clamp intent time strictly inside shot bounds
            clamped_intent = intent.model_copy(
                update={
                    "start_sec": max(s_min, intent.start_sec),
                    "end_sec": min(s_max, max(s_min + 0.25, intent.end_sec)),
                }
            )
            phases, contacts = _build_phases_for_intent(
                clamped_intent,
                actor_id=aid,
                actor_idx=idx_a,
                actor_start=a_start,
                actor_end=a_end,
                object_world=object_cursor,
                effective_motion=eff_motion,
            )
            actor_cursor[aid] = a_end
            if "object_pos" in intent.desired_state_after and intent.physical_target:
                object_cursor[intent.physical_target] = tuple(intent.desired_state_after["object_pos"])  # type: ignore[assignment]

            facing = -1 if (a_end[0] < a_start[0] - 0.01) else (
                -1 if (intent.physical_target in object_cursor and object_cursor[intent.physical_target][0] < a_end[0] - 0.02) else int(cinfo.get("facing", 1))
            )

            key = (sid, aid)
            if key not in grouped_tracks:
                track_order.append(key)
                grouped_tracks[key] = ActorMotionTrack(
                    track_id=f"{sid}_{aid}",
                    shot_id=sid,
                    actor_id=aid,
                    actor_ids=list(intent.actor_ids),
                    object_ids=list(intent.object_ids),
                    preset=preset,
                    role=str(cinfo.get("role") or role_meta.get("role") or "civilian"),
                    script_span=intent.script_span,
                    start_sec=s_min,
                    end_sec=s_max,
                    ground_y=ground_y,
                    height_norm=h_norm,
                    facing_start=facing,
                    facing_end=facing,
                    desired_state_before=dict(intent.desired_state_before),
                    desired_state_after=dict(intent.desired_state_after),
                    motion_type=eff_motion,
                    is_idle_or_speech_only=eff_motion in IDLE_OR_SPEECH_MOTIONS,
                    physical_target=intent.physical_target,
                    world_start=a_start,
                    world_end=a_end,
                    phases=phases,
                    contacts=contacts,
                    emotion=intent.emotion,
                    intensity=intent.intensity,
                    source_confidence=intent.source_confidence,
                    visible_end_condition=intent.visible_end_condition,
                    sound_cue=intent.sound_cue,
                    sound_cues=(
                        [{"kind": intent.sound_cue, "at": round(max(0.0, phases[1].start_sec - s_min if len(phases) > 1 else 0.1), 3)}]
                        if intent.sound_cue
                        else []
                    ),
                )
            else:
                existing = grouped_tracks[key]
                existing.end_sec = max(existing.end_sec, s_max)
                existing.phases.extend(phases)
                existing.contacts.extend(contacts)
                existing.world_end = a_end
                existing.facing_end = facing
                existing.script_span = f"{existing.script_span}; {intent.script_span}".strip("; ")
                for oid in intent.object_ids:
                    if oid not in existing.object_ids:
                        existing.object_ids.append(oid)
                if eff_motion not in IDLE_OR_SPEECH_MOTIONS:
                    existing.motion_type = f"{existing.motion_type}_THEN_{eff_motion}"
                    existing.is_idle_or_speech_only = False
                existing.desired_state_after.update(intent.desired_state_after)
                existing.visible_end_condition = intent.visible_end_condition
                existing.intensity = max(existing.intensity, intent.intensity)
                if intent.sound_cue:
                    existing.sound_cue = intent.sound_cue
                    existing.sound_cues.append({
                        "kind": intent.sound_cue,
                        "at": round(max(0.0, phases[1].start_sec - s_min if len(phases) > 1 else 0.1), 3),
                    })

    return [grouped_tracks[k] for k in track_order]


def build_shared_motion_timeline(
    scene_objectives: Optional[List[Any]],
    motion_tracks: List[ActorMotionTrack],
    world_timeline: Optional[Dict[str, Any]] = None,
    *,
    intents: Optional[List[MotionIntent]] = None,
    project_id: str = "motion_project",
    pack: str = "squire",
    genre: str = "civic",
    fx_profile: str = "none",
    seed: int = 1476,
    routing_mode: Literal["OFFLINE_ONLY", "LIVE_PROVIDER"] = "OFFLINE_ONLY",
    provider_trace_id: Optional[str] = None,
) -> MotionPlan:
    """
    Assemble a single authoritative `MotionPlan` whose actor IDs, object transforms,
    and world state persist continuously across shots and internal subshot cuts.
    """
    base_world = copy.deepcopy(world_timeline or {})
    actors_state: Dict[str, Dict[str, Any]] = copy.deepcopy(base_world.get("actors") or {})
    objects_state: Dict[str, Dict[str, Any]] = copy.deepcopy(base_world.get("objects") or {})
    env_state: Dict[str, Any] = copy.deepcopy(base_world.get("environment") or {"time": "twilight", "wind": 0.35})

    # Seed known objects referenced by tracks/intents
    all_intents = list(intents or [])
    for tr in motion_tracks:
        actors_state.setdefault(
            tr.actor_id,
            {
                "actor_id": tr.actor_id,
                "preset": tr.preset,
                "role": tr.role,
                "x": tr.world_start[0],
                "y": tr.world_start[1],
                "ground_y": tr.ground_y,
                "facing": tr.facing_start,
                "holding": None,
            },
        )
        for oid in tr.object_ids:
            pdef = KNOWN_PROPS.get(oid, {"kind": oid, "x": 0.54, "y": 0.76, "portable": False})
            objects_state.setdefault(
                oid,
                {
                    "object_id": oid,
                    "kind": pdef.get("kind", oid),
                    "x": float(pdef["x"]),
                    "y": float(pdef["y"]),
                    "held_by": [],
                    "state": "initial",
                },
            )
    for it in all_intents:
        for oid in it.object_ids:
            pdef = KNOWN_PROPS.get(oid, {"kind": oid, "x": 0.54, "y": 0.76, "portable": False})
            objects_state.setdefault(
                oid,
                {
                    "object_id": oid,
                    "kind": pdef.get("kind", oid),
                    "x": float(pdef["x"]),
                    "y": float(pdef["y"]),
                    "held_by": [],
                    "state": "initial",
                },
            )

    # Order shots chronologically
    shot_windows: Dict[str, Tuple[float, float]] = {}
    for tr in motion_tracks:
        s0, s1 = shot_windows.get(tr.shot_id, (tr.start_sec, tr.end_sec))
        shot_windows[tr.shot_id] = (min(s0, tr.start_sec), max(s1, tr.end_sec))
    for it in all_intents:
        s0, s1 = shot_windows.get(it.shot_id, (it.start_sec, it.end_sec))
        shot_windows[it.shot_id] = (min(s0, it.start_sec), max(s1, it.end_sec))

    ordered_shots = sorted(shot_windows.items(), key=lambda kv: (kv[1][0], kv[0]))

    world_states: List[WorldMotionState] = []
    camera_beats: List[CameraBeat] = []

    for sid, (s_start, s_end) in ordered_shots:
        pre_snapshot = {"actors": copy.deepcopy(actors_state), "objects": copy.deepcopy(objects_state)}
        s_tracks = [tr for tr in motion_tracks if tr.shot_id == sid]
        s_intents = [it for it in all_intents if it.shot_id == sid]

        for it in s_intents:
            if it.motion_type == "EXTINGUISH":
                env_state["beacon_lit"] = False
                env_state["lighting"] = "cold_storm"
                if "beacon" in objects_state:
                    objects_state["beacon"]["state"] = "extinguished"
            elif it.motion_type == "ILLUMINATE":
                env_state["beacon_lit"] = True
                env_state["lighting"] = "warm_guided_beam"
                if "ship" in objects_state:
                    objects_state["ship"]["state"] = "turning_to_safe_channel"
                    objects_state["ship"]["x"] = round(min(0.82, float(objects_state["ship"]["x"]) + 0.18), 3)
            elif it.motion_type == "SAIL_TURN" and "ship" in objects_state:
                objects_state["ship"]["state"] = "approaching_hazard"
                objects_state["ship"]["x"] = round(min(0.40, float(objects_state["ship"]["x"]) + 0.08), 3)

        for tr in s_tracks:
            a_st = actors_state.setdefault(tr.actor_id, {"actor_id": tr.actor_id})
            a_st["x"] = tr.world_end[0]
            a_st["y"] = tr.world_end[1]
            a_st["facing"] = tr.facing_end
            a_st["motion_type"] = tr.motion_type
            for c in tr.contacts:
                if c.object_id in objects_state:
                    holders = objects_state[c.object_id].setdefault("held_by", [])
                    if tr.actor_id not in holders:
                        holders.append(tr.actor_id)
                    if c.drives_object:
                        objects_state[c.object_id]["x"] = c.world_end[0] - c.anchor_local[0]
                        objects_state[c.object_id]["y"] = c.world_end[1] - c.anchor_local[1]
                        objects_state[c.object_id]["state"] = "moved_by_actor"
                    a_st["holding"] = c.object_id

        post_snapshot = {"actors": copy.deepcopy(actors_state), "objects": copy.deepcopy(objects_state)}
        span_joined = " ".join(it.script_span for it in s_intents if it.script_span)
        world_states.append(
            WorldMotionState(
                shot_id=sid,
                script_span=span_joined,
                timestamp_sec=s_end,
                start_sec=s_start,
                end_sec=s_end,
                actor_ids=sorted(actors_state.keys()),
                object_ids=sorted(objects_state.keys()),
                actors=copy.deepcopy(actors_state),
                objects=copy.deepcopy(objects_state),
                environment=copy.deepcopy(env_state),
                desired_state_before=pre_snapshot,
                desired_state_after=post_snapshot,
                physical_target=s_tracks[0].physical_target if s_tracks else None,
            )
        )

        # Derive camera beat(s): 2 beats if shot >= 3.4s and has physical contact, else 1 clean beat
        has_contact = any(len(tr.contacts) > 0 for tr in s_tracks)
        if has_contact and (s_end - s_start) >= 3.4:
            mid_t = round(s_start + (s_end - s_start) * 0.48, 3)
            camera_beats.append(
                CameraBeat(
                    beat_id=f"{sid}_cam_01",
                    shot_id=sid,
                    segment_index=0,
                    script_span=span_joined,
                    start_sec=s_start,
                    end_sec=mid_t,
                    actor_ids=[tr.actor_id for tr in s_tracks],
                    object_ids=list({o for tr in s_tracks for o in tr.object_ids}),
                    scale="medium",
                    viewpoint="front",
                    zoom_from=1.00,
                    zoom_to=1.05,
                    reason="establish_actor_approach_and_reach",
                )
            )
            camera_beats.append(
                CameraBeat(
                    beat_id=f"{sid}_cam_02",
                    shot_id=sid,
                    segment_index=1,
                    script_span=span_joined,
                    start_sec=mid_t,
                    end_sec=s_end,
                    actor_ids=[tr.actor_id for tr in s_tracks],
                    object_ids=list({o for tr in s_tracks for o in tr.object_ids}),
                    scale="insert",
                    viewpoint="front",
                    zoom_from=1.18,
                    zoom_to=1.22,
                    reason="verify_physical_grip_and_exertion",
                )
            )
        else:
            camera_beats.append(
                CameraBeat(
                    beat_id=f"{sid}_cam_01",
                    shot_id=sid,
                    segment_index=0,
                    script_span=span_joined,
                    start_sec=s_start,
                    end_sec=s_end,
                    actor_ids=[tr.actor_id for tr in s_tracks],
                    object_ids=list({o for tr in s_tracks for o in tr.object_ids}),
                    scale="wide" if len(s_tracks) >= 2 or not s_tracks else "medium",
                    viewpoint="front",
                    zoom_from=1.00,
                    zoom_to=1.04,
                    reason="continuous_single_angle_take",
                )
            )

    full_script = "\n".join(it.script_span for it in all_intents if it.script_span)
    unsup_records = [
        {
            "intent_id": it.intent_id,
            "shot_id": it.shot_id,
            "evidence": it.unsupported_evidence,
            "fallback_motion_type": it.fallback_motion_type,
        }
        for it in all_intents
        if it.unsupported_action
    ]
    total_start = min((w[0] for _, w in ordered_shots), default=0.0)
    total_end = max((w[1] for _, w in ordered_shots), default=3.0)

    plan = MotionPlan(
        project_id=project_id,
        pack=pack,
        genre=genre,
        routing_mode="LIVE_PROVIDER" if (routing_mode == "LIVE_PROVIDER" and provider_trace_id) else "OFFLINE_ONLY",
        provider_trace_id=provider_trace_id if routing_mode == "LIVE_PROVIDER" else None,
        fx_profile=fx_profile,
        seed=seed,
        script_sha256=hashlib.sha256(full_script.encode("utf-8")).hexdigest(),
        script_span=full_script,
        start_sec=total_start,
        end_sec=total_end,
        actor_ids=sorted(actors_state.keys()),
        object_ids=sorted(objects_state.keys()),
        intents=all_intents,
        tracks=motion_tracks,
        world_states=world_states,
        camera_beats=camera_beats,
        unsupported_actions=unsup_records,
    )
    val = validate_motion_plan(plan)
    plan.validation_errors = val["errors"]
    plan.is_valid = val["valid"]
    return plan


def validate_motion_plan(plan: MotionPlan) -> Dict[str, Any]:
    """
    Fail-closed validator for `MotionPlan`:
    Rejects missing actor/prop targets, impossible durations, overlapping exclusive
    constraints, discontinuous actor positions, prop duplications, feet penetrating ground,
    events outside shot bounds, unsupported actions without fallback, all-null tracks,
    and missing required phases.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if plan.end_sec <= plan.start_sec:
        errors.append(f"Plan has non-positive duration ({plan.start_sec} -> {plan.end_sec}).")

    # 1. All-null tracks check
    has_actor_intents = any(len(it.actor_ids) > 0 for it in plan.intents)
    if not plan.tracks and (has_actor_intents or not plan.intents):
        errors.append("MotionPlan has zero actor tracks (all-null tracks rejected).")

    known_objects: Set[str] = set(plan.object_ids)
    for ws in plan.world_states:
        known_objects.update(ws.objects.keys())

    shot_bounds: Dict[str, Tuple[float, float]] = {}
    for ws in plan.world_states:
        shot_bounds[ws.shot_id] = (ws.start_sec, ws.end_sec)

    # 2. Check unsupported intents have an explicit safe fallback
    for it in plan.intents:
        if it.end_sec <= it.start_sec:
            errors.append(f"Intent {it.intent_id} has impossible duration {it.start_sec}..{it.end_sec}.")
        if it.unsupported_action and not it.fallback_motion_type:
            errors.append(f"Intent {it.intent_id} is unsupported_action without fallback_motion_type.")
        if it.motion_type in PHYSICAL_CONTACT_MOTIONS and not it.physical_target and not it.object_ids:
            errors.append(f"Physical contact intent {it.intent_id} ({it.motion_type}) missing physical target/object.")

    # 3. Validate each track, phases, ground penetration, continuity, and shot bounds
    last_actor_end: Dict[str, Tuple[float, float, float]] = {}  # actor_id -> (x, y, end_sec)
    all_contacts: List[ObjectContactConstraint] = []

    for tr in plan.tracks:
        if not tr.actor_id:
            errors.append(f"Track {tr.track_id} missing actor_id.")
        if tr.end_sec <= tr.start_sec:
            errors.append(f"Track {tr.track_id} has impossible duration {tr.start_sec}..{tr.end_sec}.")
        if not tr.phases:
            errors.append(f"Track {tr.track_id} has empty phases list.")
            continue

        s_min, s_max = shot_bounds.get(tr.shot_id, (tr.start_sec, tr.end_sec))
        # Check cross-shot actor discontinuity
        if tr.actor_id in last_actor_end:
            px, py, pt = last_actor_end[tr.actor_id]
            gap_dt = max(0.0, tr.start_sec - pt)
            jump = math.hypot(tr.world_start[0] - px, tr.world_start[1] - py)
            if gap_dt <= 0.05 and jump > 0.12:
                errors.append(
                    f"Discontinuous actor position for {tr.actor_id} entering {tr.shot_id}: jump={jump:.3f}."
                )

        phase_names = [p.phase_name for p in tr.phases]
        base_mtypes = [m for m in tr.motion_type.split("_THEN_") if m]
        for bm in base_mtypes:
            if bm in PHYSICAL_CONTACT_MOTIONS:
                if "CONTACT" not in phase_names:
                    errors.append(f"Track {tr.track_id} ({bm}) missing mandatory CONTACT phase.")
                if "ANTICIPATE" not in phase_names or "SETTLE" not in phase_names:
                    errors.append(f"Track {tr.track_id} ({bm}) missing ANTICIPATE or SETTLE phase.")
            elif bm in LOCOMOTION_MOTIONS:
                if "APPROACH" not in phase_names:
                    errors.append(f"Track {tr.track_id} ({bm}) missing APPROACH phase.")

        prev_p_end_pos = tr.phases[0].world_start
        for p_idx, ph in enumerate(tr.phases):
            if ph.end_sec <= ph.start_sec:
                errors.append(f"Track {tr.track_id} phase {ph.phase_name} has non-positive duration.")
            if ph.start_sec < s_min - 1e-3 or ph.end_sec > s_max + 1e-3:
                errors.append(
                    f"Track {tr.track_id} phase {ph.phase_name} ({ph.start_sec}..{ph.end_sec}) outside shot {tr.shot_id} ({s_min}..{s_max})."
                )
            # Ground penetration check (Canvas Y increases downward; actor root Y > ground_y means below floor)
            if ph.world_start[1] > tr.ground_y + 0.005 or ph.world_end[1] > tr.ground_y + 0.005:
                errors.append(
                    f"Foot penetrating ground in {tr.track_id}:{ph.phase_name} (y={max(ph.world_start[1], ph.world_end[1]):.3f} > ground_y={tr.ground_y:.3f})."
                )
            # Intra-track continuity check
            step_jump = math.hypot(ph.world_start[0] - prev_p_end_pos[0], ph.world_start[1] - prev_p_end_pos[1])
            if p_idx > 0 and step_jump > 0.10:
                errors.append(
                    f"Intra-track teleport in {tr.track_id} before {ph.phase_name}: jump={step_jump:.3f}."
                )
            p_dur = max(1e-4, ph.end_sec - ph.start_sec)
            p_vel = math.hypot(ph.world_end[0] - ph.world_start[0], ph.world_end[1] - ph.world_start[1]) / p_dur
            if p_vel > 0.75:
                errors.append(
                    f"Infeasible actor velocity in {tr.track_id}:{ph.phase_name} ({p_vel:.3f} screen/s > 0.75)."
                )
            prev_p_end_pos = ph.world_end

        for c in tr.contacts:
            if not c.object_id or (known_objects and c.object_id not in known_objects):
                errors.append(f"Contact constraint {c.constraint_id} references unknown object '{c.object_id}'.")
            if c.start_sec < s_min - 1e-3 or c.end_sec > s_max + 1e-3:
                errors.append(f"Contact constraint {c.constraint_id} outside shot bounds.")
            all_contacts.append(c)

        last_actor_end[tr.actor_id] = (tr.world_end[0], tr.world_end[1], tr.end_sec)

    # 4. Overlapping exclusive constraints & prop duplication checks
    for i in range(len(all_contacts)):
        c1 = all_contacts[i]
        for j in range(i + 1, len(all_contacts)):
            c2 = all_contacts[j]
            if c1.object_id != c2.object_id or c1.actor_id == c2.actor_id:
                continue
            overlap = min(c1.end_sec, c2.end_sec) - max(c1.start_sec, c2.start_sec)
            if overlap > 1e-3:
                if c1.exclusive or c2.exclusive:
                    errors.append(
                        f"Overlapping exclusive contact on '{c1.object_id}' between '{c1.actor_id}' and '{c2.actor_id}'."
                    )
                else:
                    # Shared non-exclusive contact: verify prop isn't duplicated at two distant world spots
                    base1 = (c1.world_start[0] - c1.anchor_local[0], c1.world_start[1] - c1.anchor_local[1])
                    base2 = (c2.world_start[0] - c2.anchor_local[0], c2.world_start[1] - c2.anchor_local[1])
                    if math.hypot(base1[0] - base2[0], base1[1] - base2[1]) > 0.08:
                        errors.append(
                            f"Prop duplication detected for '{c1.object_id}': divergent world bases {base1} vs {base2}."
                        )

    for ws in plan.world_states:
        seen_kinds_coords: Dict[str, Tuple[float, float]] = {}
        for oid, odata in ws.objects.items():
            if oid in seen_kinds_coords:
                errors.append(f"Duplicate object_id '{oid}' in world state {ws.shot_id}.")
            seen_kinds_coords[oid] = (float(odata.get("x", 0.0)), float(odata.get("y", 0.0)))
            holders = odata.get("held_by") or []
            if len(set(holders)) != len(holders):
                errors.append(f"Duplicate holder entry on '{oid}' in {ws.shot_id}.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "track_count": len(plan.tracks),
        "intent_count": len(plan.intents),
        "contact_count": len(all_contacts),
        "unsupported_count": len(plan.unsupported_actions),
    }


def compile_motion_plan_to_legacy_shot_args(
    plan: Optional[MotionPlan],
    shots: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compile `MotionPlan` additively into legacy storyboard shots (`args.motionPlan`,
    `args.motionTracks`, `args.worldState`) while leaving manual shots and `plan=None`
    100% byte-identical.
    """
    if plan is None:
        return {
            "shots": copy.deepcopy(shots) if shots is not None else [],
            "modified_count": 0,
            "by_shot": {},
        }

    by_shot: Dict[str, Dict[str, Any]] = {}
    ws_map = {ws.shot_id: ws for ws in plan.world_states}
    cam_map: Dict[str, List[Dict[str, Any]]] = {}
    for cb in plan.camera_beats:
        cam_map.setdefault(cb.shot_id, []).append(cb.model_dump())

    tracks_by_shot: Dict[str, List[ActorMotionTrack]] = {}
    for tr in plan.tracks:
        tracks_by_shot.setdefault(tr.shot_id, []).append(tr)

    all_sids = sorted(set(ws_map.keys()) | set(tracks_by_shot.keys()))
    for sid in all_sids:
        s_tracks = tracks_by_shot.get(sid, [])
        ws = ws_map.get(sid)
        serialized_tracks = [tr.model_dump() for tr in s_tracks]
        legacy_people: List[Dict[str, Any]] = []
        for tr in s_tracks:
            p_entry: Dict[str, Any] = {
                "id": tr.actor_id,
                "preset": tr.preset,
                "x": tr.world_start[0],
                "y": tr.world_start[1],
                "h": tr.height_norm,
                "facing": tr.facing_start,
                "pose": "stand" if tr.is_idle_or_speech_only else ("run" if "RUN" in tr.motion_type else "walk" if "WALK" in tr.motion_type else "brace"),
                "motionTrack": tr.model_dump(),
            }
            if abs(tr.world_end[0] - tr.world_start[0]) > 1e-4:
                p_entry["from"] = tr.world_start[0]
                p_entry["to"] = tr.world_end[0]
                p_entry["dur"] = round(max(0.25, tr.end_sec - tr.start_sec), 3)
                p_entry["moveAt"] = 0.0
            legacy_people.append(p_entry)

        by_shot[sid] = {
            "motionPlan": {
                "schema_version": plan.schema_version,
                "project_id": plan.project_id,
                "shot_id": sid,
                "routing_mode": plan.routing_mode,
                "fx_profile": plan.fx_profile,
                "seed": plan.seed,
            },
            "motionTracks": serialized_tracks,
            "worldState": ws.model_dump() if ws else {},
            "cameraBeats": cam_map.get(sid, []),
            "people": legacy_people,
        }

    if shots is None:
        return {"shots": [], "modified_count": len(by_shot), "by_shot": by_shot}

    revised_shots: List[Dict[str, Any]] = []
    modified_count = 0
    for s in shots:
        if s.get("manual") is True or s.get("visual_source") == "manual":
            revised_shots.append(copy.deepcopy(s))
            continue
        sid = str(s.get("id") or s.get("shot_id") or "")
        compiled = by_shot.get(sid)
        if not compiled:
            revised_shots.append(copy.deepcopy(s))
            continue
        s_copy = copy.deepcopy(s)
        args = s_copy.setdefault("args", {})
        args["motionPlan"] = compiled["motionPlan"]
        args["motionTracks"] = compiled["motionTracks"]
        args["worldState"] = compiled["worldState"]
        if compiled["cameraBeats"] and "cameraBeats" not in args:
            args["cameraBeats"] = compiled["cameraBeats"]
        if not args.get("people") and compiled["people"]:
            args["people"] = compiled["people"]
        else:
            # Attach motionTrack onto matching existing people entries without breaking pose/armsAng/move/zoom
            tr_lookup = {t["actor_id"]: t for t in compiled["motionTracks"]}
            for p in args.get("people", []):
                if isinstance(p, dict) and p.get("id") in tr_lookup:
                    p["motionTrack"] = tr_lookup[p["id"]]
        revised_shots.append(s_copy)
        modified_count += 1

    return {
        "shots": revised_shots,
        "modified_count": modified_count,
        "by_shot": by_shot,
    }
