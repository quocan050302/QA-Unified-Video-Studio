"""tools/action_capabilities.py — Pack Capability Registry & Event Capability Resolver (V14.4).

Architecture layer 2:
Identifies available drawing/animation primitives for Squire (roman, knight, samurai)
and DEM (self-improvement silent). Validates and maps generic events to pack-supported
capabilities without silent fake substitutions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field

from tools.narrative_semantics import ActionKind, GroundedEventNode


class PackCapabilityProfile(BaseModel):
    pack: str
    genre: str
    supported_actions: Set[str] = Field(default_factory=set)
    supported_viewpoints: Set[str] = Field(default_factory=set)
    supported_templates: Set[str] = Field(default_factory=set)
    supported_props: Set[str] = Field(default_factory=set)
    supports_formation_actions: bool = False
    supports_motion_rig: bool = True
    supports_multi_actor_contact: bool = True
    supports_silent_beatboard: bool = False


# Capability definitions across packs and genres
CAPABILITY_REGISTRY: Dict[str, Dict[str, PackCapabilityProfile]] = {
    "squire": {
        "roman": PackCapabilityProfile(
            pack="squire",
            genre="roman",
            supported_actions={
                "APPROACH", "MOVE_TO", "STOP", "TURN", "BRACE", "CONTACT",
                "IMPACT_RECOIL", "FATIGUE", "SIGNAL", "OPEN_LANE",
                "FRONT_WITHDRAW", "RESERVE_ADVANCE", "PASS_THROUGH",
                "SHIELD_CLOSE", "DEFEND", "ATTACK", "OBSERVE", "WAIT",
                "CAMERA_REVEAL",
            },
            supported_viewpoints={
                "front", "front_three_quarter_left", "front_three_quarter_right",
                "profile_left", "profile_right", "rear_three_quarter_left",
                "rear_three_quarter_right", "rear", "over_shoulder_left",
                "over_shoulder_right", "high_angle", "low_angle", "top_down", "map",
            },
            supported_templates={"scene", "army", "close", "top", "plan", "map", "board"},
            supported_props={"shield", "gladius", "pilum", "standard", "eagle", "dust", "tent"},
            supports_formation_actions=True,
            supports_motion_rig=True,
            supports_multi_actor_contact=True,
            supports_silent_beatboard=False,
        ),
        "knight": PackCapabilityProfile(
            pack="squire",
            genre="knight",
            supported_actions={
                "APPROACH", "MOVE_TO", "STOP", "TURN", "BRACE", "CONTACT",
                "IMPACT_RECOIL", "DEFEND", "ATTACK", "BLOCK", "OBSERVE", "WAIT",
                "CAMERA_REVEAL",
            },
            supported_viewpoints={
                "front", "front_three_quarter_left", "front_three_quarter_right",
                "profile_left", "profile_right", "rear", "high_angle", "low_angle",
            },
            supported_templates={"scene", "army", "close", "board"},
            supported_props={"shield", "sword", "pollaxe", "lance", "flag", "banner", "dust"},
            supports_formation_actions=True,
            supports_motion_rig=True,
            supports_multi_actor_contact=True,
            supports_silent_beatboard=False,
        ),
        "samurai": PackCapabilityProfile(
            pack="squire",
            genre="samurai",
            supported_actions={
                "APPROACH", "MOVE_TO", "STOP", "TURN", "CONTACT",
                "IMPACT_RECOIL", "PARRY", "DRAW_WEAPON", "DEFEND", "ATTACK",
                "OBSERVE", "WAIT", "CAMERA_REVEAL",
            },
            supported_viewpoints={
                "front", "front_three_quarter_left", "front_three_quarter_right",
                "profile_left", "profile_right", "rear", "low_angle",
            },
            supported_templates={"scene", "close", "board"},
            supported_props={"katana", "naginata", "banner", "dust"},
            supports_formation_actions=False,
            supports_motion_rig=True,
            supports_multi_actor_contact=True,
            supports_silent_beatboard=False,
        ),
    },
    "dem": {
        "selfimprove": PackCapabilityProfile(
            pack="dem",
            genre="selfimprove",
            supported_actions={
                "WAKE_UP", "PICK_UP", "PUT_DOWN", "SIT_DOWN", "MOVE_TO",
                "STOP", "TURN", "OBSERVE", "WAIT", "CAMERA_REVEAL",
            },
            supported_viewpoints={
                "front", "profile_left", "profile_right", "front_three_quarter_left",
                "front_three_quarter_right", "rear", "over_shoulder",
            },
            supported_templates={"scene", "phone", "clock", "calendar", "face", "note", "black", "card", "cta"},
            supported_props={"phone", "clock", "calendar", "bed", "desk", "notebook", "book"},
            supports_formation_actions=False,
            supports_motion_rig=True,
            supports_multi_actor_contact=False,
            supports_silent_beatboard=True,
        ),
    },
}


def get_pack_capabilities(pack: str = "squire", genre: Optional[str] = None) -> PackCapabilityProfile:
    """Retrieve capability profile for a pack and genre combination."""
    p_genre = genre or ("roman" if pack == "squire" else "selfimprove")
    pack_dict = CAPABILITY_REGISTRY.get(pack, {})
    if p_genre in pack_dict:
        return pack_dict[p_genre]
    
    # Generic unspecialized profile for unknown/unregistered genres
    # Strictly avoids quietly inheriting Roman formation, weapons, or choreography
    return PackCapabilityProfile(
        pack=pack,
        genre=p_genre,
        supported_actions={"STAND", "WALK", "MOVE_TO", "STOP", "TURN", "OBSERVE", "WAIT", "CAMERA_REVEAL"},
        supported_viewpoints={"front", "profile_left", "profile_right"},
        supported_templates={"scene"},
        supported_props=set(),
        supports_formation_actions=False,
        supports_motion_rig=True,
        supports_multi_actor_contact=False,
        supports_silent_beatboard=(pack == "dem"),
    )


def resolve_event_capabilities(
    events: List[GroundedEventNode],
    pack: str = "squire",
    genre: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate whether events can be executed by target pack and genre.
    Returns supported events, labeled simplifications, and blocked unsupported events.
    """
    cap = get_pack_capabilities(pack, genre)
    
    supported: List[Dict[str, Any]] = []
    simplified: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []

    for ev in events:
        action = ev.action_kind
        if action in cap.supported_actions:
            supported.append({
                "event_id": ev.event_id,
                "action": action,
                "status": "SUPPORTED_DIRECT",
                "shot_id": ev.shot_id,
            })
        else:
            # Check for explicitly labeled safe simplifications
            if pack == "squire" and action in ("PARRY", "BLOCK"):
                simplified.append({
                    "event_id": ev.event_id,
                    "action": action,
                    "status": "SIMPLIFIED_BRACE",
                    "reason": f"{action} rendered as dynamic shield brace in {genre}",
                    "shot_id": ev.shot_id,
                })
            elif pack == "dem" and action in ("DEFEND", "BRACE"):
                unsupported.append({
                    "event_id": ev.event_id,
                    "action": action,
                    "status": "UNSUPPORTED_ACTION",
                    "reason": f"Military action '{action}' cannot be represented in DEM Self-Improvement pack",
                    "shot_id": ev.shot_id,
                })
            elif pack == "squire" and action in ("WAKE_UP", "PICK_UP"):
                unsupported.append({
                    "event_id": ev.event_id,
                    "action": action,
                    "status": "UNSUPPORTED_ACTION",
                    "reason": f"Domestic action '{action}' is outside Squire military combat vocabulary",
                    "shot_id": ev.shot_id,
                })
            else:
                unsupported.append({
                    "event_id": ev.event_id,
                    "action": action,
                    "status": "UNSUPPORTED_ACTION",
                    "reason": f"Action '{action}' not in capability registry for {pack}/{genre}",
                    "shot_id": ev.shot_id,
                })

    is_valid = len(unsupported) == 0

    return {
        "valid": is_valid,
        "pack": pack,
        "genre": cap.genre,
        "total_events": len(events),
        "supported_count": len(supported),
        "simplified_count": len(simplified),
        "unsupported_count": len(unsupported),
        "supported": supported,
        "simplified": simplified,
        "unsupported": unsupported,
    }
