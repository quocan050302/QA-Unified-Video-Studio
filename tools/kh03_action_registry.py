#!/usr/bin/env python3
"""kh03_action_registry.py — Finite, Auditable, Fail-Closed Action Capability Registry for KH-03.0.R2.

Replaces keyword-guessing and generic fallback renders with explicit typed capabilities:
- Every supported Roman 2D action has a versioned ActionSpec, declared pre/post state deltas,
  compatible Squire archetypes, required props/locations, and a verified Canvas2D renderer handler id.
- Unsupported actions, missing assets, ambiguous pronouns, negated polarity, and state conflicts
  fail CLOSED with structured diagnostics (never silently drawing an unrelated guard scene).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

REGISTRY_VERSION = "kh03.r2.action_registry.v1"

ALLOWED_ERROR_CODES = (
    "UNSUPPORTED_ACTION",
    "AMBIGUOUS_ACTION",
    "MISSING_ASSET",
    "STATE_CONFLICT",
    "NEGATED_ACTION",
    "UNSAFE_OVERRIDE",
)

# Creatures / vehicles / speculative fantasy actions explicitly OUTSIDE the finite R2 2D capability set
UNSUPPORTED_TOKENS_PATTERN = re.compile(
    r"\b(?:horse|horses|cavalry|chariot|elephant|camel|oxen|ox|mule|griffin|dragon|"
    r"flying\s+aqueduct|aqueduct\s+fly|vault|vaults|vaulted|swim|swam|swimming|"
    r"catapult|ballista|trireme|shipwreck|teleport|laser|gun|motorcycle|airplane)\b",
    flags=re.IGNORECASE,
)

NEGATION_WORDS = (
    "never", "did not", "didn't", "do not", "don't", "could not", "couldn't",
    "cannot", "can't", "nobody", "no one", "without", "failed to", "refused to", "missed",
)


@dataclass(frozen=True)
class ActionRequirement:
    actors: Tuple[str, ...] = ()
    props: Tuple[str, ...] = ()
    locations: Tuple[str, ...] = ()
    required_pre_states: Dict[str, Any] = field(default_factory=dict)
    forbidden_pre_states: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    domain: str  # ACTOR | PROP | WORLD | CAMERA
    supported_verbs: Tuple[str, ...]
    compatible_actor_archetypes: Tuple[str, ...]
    required_props: Tuple[str, ...]
    required_locations: Tuple[str, ...]
    camera_affordances: Tuple[str, ...]
    event_class: str  # action | reaction | insert | establish | reveal
    default_min_max_frame_span: Tuple[int, int]
    allowed_state_deltas: Dict[str, Any]
    renderer_action_id: str
    motion_profile_id: str
    requirements: ActionRequirement = field(default_factory=ActionRequirement)
    artifact_version: str = REGISTRY_VERSION


@dataclass
class ActionBinding:
    binding_id: str
    line_id: str
    source_phrase: str
    action_id: str
    domain: str
    event_class: str
    renderer_action_id: str
    motion_profile_id: str
    actor_ids: List[str]
    prop_ids: List[str]
    location_id: str
    camera_affordance: str
    word_anchors: List[str]
    pre_states: Dict[str, Any]
    post_states: Dict[str, Any]
    evidence_source_span: Dict[str, Any]
    confidence: float
    ambiguity_flags: List[str] = field(default_factory=list)
    override_log: Optional[Dict[str, Any]] = None
    artifact_version: str = REGISTRY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UnsupportedRomanActionError(RuntimeError):
    """Structured fail-closed exception raised whenever a script requests an unverified capability."""

    def __init__(
        self,
        reason_code: str,
        line_id: str,
        source_phrase: str,
        action_name: str,
        message: str,
        *,
        missing_actors: Optional[List[str]] = None,
        missing_props: Optional[List[str]] = None,
        missing_locations: Optional[List[str]] = None,
        missing_render_handler: Optional[str] = None,
        suggested_valid_actions: Optional[List[str]] = None,
    ) -> None:
        if reason_code not in ALLOWED_ERROR_CODES:
            raise ValueError(f"Unknown error code {reason_code}")
        self.reason_code = reason_code
        self.line_id = line_id
        self.source_phrase = source_phrase
        self.action_name = action_name
        self.missing_actors = missing_actors or []
        self.missing_props = missing_props or []
        self.missing_locations = missing_locations or []
        self.missing_render_handler = missing_render_handler
        self.suggested_valid_actions = suggested_valid_actions or []
        self.details = {
            "error_code": reason_code,
            "line_id": line_id,
            "source_phrase": source_phrase,
            "action_name": action_name,
            "missing_actor": self.missing_actors,
            "missing_prop": self.missing_props,
            "missing_location": self.missing_locations,
            "missing_render_handler": self.missing_render_handler,
            "suggested_valid_actions": self.suggested_valid_actions,
            "registry_version": REGISTRY_VERSION,
        }
        super().__init__(f"{reason_code} [{line_id}]: {message} ({json.dumps(self.details)})")


# Locked Squire character base archetypes (R2 variants stay derived strictly from these + citizen)
COMPATIBLE_SQUIRE_ARCHETYPES = (
    "rookie_hastatus",
    "instructor_princeps",
    "veteran_neighbor_legionary",
    "centurion_crest",
    "apprentice_titus",
    "baker_lucius",
    "centurion_varro",
    "signifer_marc",
    "senator_cassius",
    "forum_messenger",
    "market_crowd",
    "courier_marcus",
    "gate_guard_gaius",
    "watchman_sec",
)


def build_roman_action_registry() -> Dict[str, ActionSpec]:
    """Return immutable finite capability map backed 1:1 by Canvas2D handlers in action_registry.js."""
    specs = [
        # ---- ACTOR DOMAIN ----
        ActionSpec(
            action_id="actor.idle_micro_act",
            domain="ACTOR",
            supported_verbs=("wait", "waited", "watch", "watched", "pause", "paused", "blink", "breathe", "stand", "stood", "stay", "stayed"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("reveal_payoff", "actor_follow", "push_in"),
            event_class="reaction",
            default_min_max_frame_span=(14, 54),
            allowed_state_deltas={"actor_posture": "idle_alert"},
            renderer_action_id="actor_idle_micro_act",
            motion_profile_id="micro_breathe_blink",
        ),
        ActionSpec(
            action_id="actor.walk_stride",
            domain="ACTOR",
            supported_verbs=("walk", "walked", "walking", "march", "marched", "marching", "stroll", "strolled", "stride", "strode"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("actor_follow", "motivated_cut", "parallax_track"),
            event_class="action",
            default_min_max_frame_span=(18, 72),
            allowed_state_deltas={"actor_gait": "walk"},
            renderer_action_id="actor_walk_stride",
            motion_profile_id="biped_walk_cycle",
        ),
        ActionSpec(
            action_id="actor.deadpan_walk_unaffected",
            domain="ACTOR",
            supported_verbs=("kept walking", "walked calmly", "walked on", "nobody dared laugh", "ignored loaf", "without blinking"),
            compatible_actor_archetypes=("centurion_varro", "centurion_crest", "instructor_princeps", "senator_cassius"),
            required_props=("roman_loaf",),
            required_locations=("roman_market_hill",),
            camera_affordances=("reveal_payoff", "push_in", "actor_follow"),
            event_class="reveal",
            default_min_max_frame_span=(28, 72),
            allowed_state_deltas={"centurion_composure": "deadpan_steady", "loaf_on_helmet": True},
            renderer_action_id="actor_deadpan_walk_unaffected",
            motion_profile_id="deadpan_centurion_stride",
            requirements=ActionRequirement(required_pre_states={"loaf_on_helmet": True}),
        ),
        ActionSpec(
            action_id="actor.sprint_chase",
            domain="ACTOR",
            supported_verbs=("sprint", "sprinted", "sprinting", "chase", "chased", "chasing", "dash", "dashed", "raced", "racing", "ran after", "ran behind", "ran downhill"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("actor_follow", "parallax_track", "whip_pan_motivated"),
            event_class="action",
            default_min_max_frame_span=(16, 68),
            allowed_state_deltas={"actor_gait": "sprint"},
            renderer_action_id="actor_sprint_chase",
            motion_profile_id="biped_sprint_lean",
        ),
        ActionSpec(
            action_id="actor.reach_grab_prop",
            domain="ACTOR",
            supported_verbs=("grab", "grabbed", "snatch", "snatched", "seize", "seized", "caught", "caught rope", "reach", "reached", "reaching", "loop", "looped", "lunged"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("prop_insert", "actor_follow", "impulse_snap_zoom"),
            event_class="action",
            default_min_max_frame_span=(14, 58),
            allowed_state_deltas={"hand_prop_contact": True},
            renderer_action_id="actor_reach_grab_prop",
            motion_profile_id="ik_reach_hand_lock",
        ),
        ActionSpec(
            action_id="actor.stop_brace",
            domain="ACTOR",
            supported_verbs=("brace", "braced", "bracing", "plant", "planted", "anchor", "anchored", "leaned back", "braced heels"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("hemp_rope", "stone_bollard"),
            required_locations=(),
            camera_affordances=("actor_follow", "impulse_snap_zoom", "push_in"),
            event_class="action",
            default_min_max_frame_span=(16, 64),
            allowed_state_deltas={"actor_posture": "braced_load", "rope_taut": True},
            renderer_action_id="actor_stop_brace",
            motion_profile_id="rear_heel_brace_ik",
            requirements=ActionRequirement(props=("hemp_rope", "stone_bollard")),
        ),
        ActionSpec(
            action_id="actor.release_throw_prop",
            domain="ACTOR",
            supported_verbs=("throw", "threw", "toss", "tossed", "cast", "release", "released", "fling"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("actor_follow", "prop_insert"),
            event_class="action",
            default_min_max_frame_span=(14, 52),
            allowed_state_deltas={"prop_airborne": True},
            renderer_action_id="actor_release_throw_prop",
            motion_profile_id="overarm_throw_followthrough",
        ),
        ActionSpec(
            action_id="actor.point_shout_look",
            domain="ACTOR",
            supported_verbs=("point", "pointed", "shout", "shouted", "yell", "yelled", "gasp", "look", "looked", "stare"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("motivated_cut", "actor_follow", "pull_out"),
            event_class="reaction",
            default_min_max_frame_span=(14, 54),
            allowed_state_deltas={"actor_attention": "alert_directed"},
            renderer_action_id="actor_point_shout_look",
            motion_profile_id="head_turn_arm_point",
        ),
        ActionSpec(
            action_id="actor.pickup_prop",
            domain="ACTOR",
            supported_verbs=("pick up", "picked up", "retrieve", "retrieved", "lifted", "stoop", "gathered"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("motivated_cut", "push_in", "reveal_payoff"),
            event_class="action",
            default_min_max_frame_span=(16, 62),
            allowed_state_deltas={"prop_recovered": True},
            renderer_action_id="actor_pickup_prop",
            motion_profile_id="stoop_pickup_ik",
        ),
        ActionSpec(
            action_id="actor.pull_drag_rope_tension",
            domain="ACTOR",
            supported_verbs=("pull", "pulled", "drag", "dragged", "haul", "hauled", "heave", "reel", "reeled"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("hemp_rope",),
            required_locations=(),
            camera_affordances=("actor_follow", "parallax_track", "push_in"),
            event_class="action",
            default_min_max_frame_span=(18, 66),
            allowed_state_deltas={"rope_taut": True, "prop_hauled": True},
            renderer_action_id="actor_pull_drag_rope_tension",
            motion_profile_id="two_hand_rope_haul",
            requirements=ActionRequirement(props=("hemp_rope",)),
        ),
        ActionSpec(
            action_id="actor.push_hold_load",
            domain="ACTOR",
            supported_verbs=("push", "pushed", "shove", "shoved", "hold back", "shoulder"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("actor_follow", "impulse_snap_zoom"),
            event_class="action",
            default_min_max_frame_span=(16, 58),
            allowed_state_deltas={"load_held": True},
            renderer_action_id="actor_push_hold_load",
            motion_profile_id="forward_shoulder_push",
        ),
        ActionSpec(
            action_id="actor.handoff_prop",
            domain="ACTOR",
            supported_verbs=("hand", "handed", "pass", "passed", "deliver", "delivered"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("motivated_cut", "actor_follow"),
            event_class="action",
            default_min_max_frame_span=(16, 56),
            allowed_state_deltas={"prop_handed_off": True},
            renderer_action_id="actor_handoff_prop",
            motion_profile_id="two_actor_handoff_sync",
        ),
        ActionSpec(
            action_id="actor.stumble_recover",
            domain="ACTOR",
            supported_verbs=("stumble", "stumbled", "slip", "slipped", "trip", "tripped", "recover"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=(),
            camera_affordances=("actor_follow", "impulse_snap_zoom"),
            event_class="action",
            default_min_max_frame_span=(14, 56),
            allowed_state_deltas={"actor_balance": "stumbled_recovered"},
            renderer_action_id="actor_stumble_recover",
            motion_profile_id="forward_trip_recovery",
        ),
        ActionSpec(
            action_id="actor.crowd_reaction_cheer",
            domain="ACTOR",
            supported_verbs=("cheer", "cheered", "applaud", "celebrate", "crowd gasped", "market cheered"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=("roman_market_hill",),
            camera_affordances=("pull_out", "reveal_payoff"),
            event_class="reaction",
            default_min_max_frame_span=(16, 52),
            allowed_state_deltas={"crowd_mood": "cheering"},
            renderer_action_id="actor_crowd_reaction_cheer",
            motion_profile_id="multi_citizen_cheer_jump",
            requirements=ActionRequirement(required_pre_states={"cart_stopped": True}),
        ),
        # ---- PROP DOMAIN ----
        ActionSpec(
            action_id="prop.peg_crack_snap",
            domain="PROP",
            supported_verbs=("brake peg snapped", "peg cracked", "peg snapped", "pin broke", "chock slipped", "snap of a brake peg"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("brake_peg", "market_cart"),
            required_locations=("roman_market_hill",),
            camera_affordances=("prop_insert", "impulse_snap_zoom"),
            event_class="insert",
            default_min_max_frame_span=(14, 48),
            allowed_state_deltas={"peg_snapped": True, "cart_rolling": True},
            renderer_action_id="prop_peg_crack_snap",
            motion_profile_id="brittle_fracture_creep",
            requirements=ActionRequirement(
                props=("brake_peg", "market_cart"),
                locations=("roman_market_hill",),
                forbidden_pre_states={"peg_snapped": True},
            ),
        ),
        ActionSpec(
            action_id="prop.cart_roll_slope",
            domain="PROP",
            supported_verbs=("cart began to roll", "gaining speed", "rolled downhill", "cart rolled", "kept gaining speed", "rattled over cobbles"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("market_cart",),
            required_locations=("roman_market_hill",),
            camera_affordances=("parallax_track", "prop_insert", "pull_out"),
            event_class="action",
            default_min_max_frame_span=(18, 68),
            allowed_state_deltas={"cart_rolling": True},
            renderer_action_id="prop_cart_roll_slope",
            motion_profile_id="slope_accel_wheel_spin",
            requirements=ActionRequirement(
                props=("market_cart",),
                locations=("roman_market_hill",),
                required_pre_states={"peg_snapped": True},
            ),
        ),
        ActionSpec(
            action_id="prop.rope_taut_post_wrap",
            domain="PROP",
            supported_verbs=("rope trailed", "trailed from axle", "snapped tight", "rope taut", "wound post", "whipped the rope", "around a stone post", "around a stone bollard"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("hemp_rope", "market_cart", "stone_bollard"),
            required_locations=("roman_market_hill",),
            camera_affordances=("prop_insert", "push_in", "impulse_snap_zoom"),
            event_class="insert",
            default_min_max_frame_span=(14, 54),
            allowed_state_deltas={"rope_attached": True, "rope_taut": True},
            renderer_action_id="prop_rope_taut_post_wrap",
            motion_profile_id="catenary_to_chord_tension",
            requirements=ActionRequirement(props=("hemp_rope", "market_cart")),
        ),
        ActionSpec(
            action_id="prop.cart_halt_skid",
            domain="PROP",
            supported_verbs=("cart stopped", "handspan from oven", "halted", "skidded to a stop", "skidded to a halt", "stopped short"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("market_cart", "bakery_oven", "hemp_rope", "stone_bollard"),
            required_locations=("roman_market_hill",),
            camera_affordances=("impulse_snap_zoom", "reveal_payoff", "motivated_cut"),
            event_class="action",
            default_min_max_frame_span=(18, 64),
            allowed_state_deltas={"cart_rolling": False, "cart_stopped": True, "jolt_occurred": True},
            renderer_action_id="prop_cart_halt_skid",
            motion_profile_id="recoil_wheel_skid_halt",
            requirements=ActionRequirement(
                props=("market_cart", "bakery_oven", "hemp_rope", "stone_bollard"),
                locations=("roman_market_hill",),
                required_pre_states={"rope_taut": True},
            ),
        ),
        ActionSpec(
            action_id="prop.prop_bounce_tray",
            domain="PROP",
            supported_verbs=("knocked a loaf", "baker's tray", "jolt knocked", "jarred the tray", "tray shook", "bounced"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("bread_tray", "roman_loaf"),
            required_locations=("roman_market_hill",),
            camera_affordances=("prop_insert", "motivated_cut"),
            event_class="insert",
            default_min_max_frame_span=(14, 52),
            allowed_state_deltas={"loaf_airborne": True},
            renderer_action_id="prop_bounce_tray",
            motion_profile_id="tray_impulse_launch",
            requirements=ActionRequirement(
                props=("bread_tray", "roman_loaf"),
                required_pre_states={"cart_stopped": True},
            ),
        ),
        ActionSpec(
            action_id="prop.prop_parabolic_arc",
            domain="PROP",
            supported_verbs=("loaf flew", "flew through air", "arced", "spinning airborne", "sailed"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("roman_loaf",),
            required_locations=(),
            camera_affordances=("prop_insert", "actor_follow"),
            event_class="insert",
            default_min_max_frame_span=(12, 48),
            allowed_state_deltas={"loaf_airborne": True},
            renderer_action_id="prop_parabolic_arc",
            motion_profile_id="ballistic_parabolic_arc",
        ),
        ActionSpec(
            action_id="prop.helmet_impact_settle",
            domain="PROP",
            supported_verbs=("landed squarely", "on centurion's helmet", "landed on helmet", "plume bounce", "settled onto", "landed on"),
            compatible_actor_archetypes=("centurion_varro", "centurion_crest", "instructor_princeps"),
            required_props=("roman_loaf",),
            required_locations=("roman_market_hill",),
            camera_affordances=("impulse_snap_zoom", "reveal_payoff", "push_in"),
            event_class="reveal",
            default_min_max_frame_span=(18, 60),
            allowed_state_deltas={"loaf_airborne": False, "loaf_on_helmet": True},
            renderer_action_id="prop_helmet_impact_settle",
            motion_profile_id="soft_crust_helmet_squish",
            requirements=ActionRequirement(
                props=("roman_loaf",),
                required_pre_states={"loaf_airborne": True},
            ),
        ),
        ActionSpec(
            action_id="prop.vexillum_river_drift",
            domain="PROP",
            supported_verbs=("vexillum", "river landing", "water current", "drifting standard", "fallen cloth", "river current", "standard drifted"),
            compatible_actor_archetypes=("signifer_marc", "veteran_neighbor_legionary", "rookie_hastatus"),
            required_props=("cloth_vexillum", "hemp_rope"),
            required_locations=("roman_river_harbor",),
            camera_affordances=("prop_insert", "parallax_track", "actor_follow"),
            event_class="action",
            default_min_max_frame_span=(16, 60),
            allowed_state_deltas={"vexillum_drifting": True},
            renderer_action_id="prop_vexillum_river_drift",
            motion_profile_id="water_current_bob_drift",
            requirements=ActionRequirement(props=("cloth_vexillum",), locations=("roman_river_harbor",)),
        ),
        ActionSpec(
            action_id="prop.helmet_roll_under_bench",
            domain="PROP",
            supported_verbs=("dropped helmet", "dropped his helmet", "rolled under bench", "rolled under the bench", "rolled under a stone bench", "helmet rolled", "under stone bench"),
            compatible_actor_archetypes=("forum_messenger", "senator_cassius", "rookie_hastatus", "instructor_princeps"),
            required_props=("ceremonial_helmet", "stone_bench"),
            required_locations=("roman_forum_courtyard",),
            camera_affordances=("prop_insert", "push_in"),
            event_class="insert",
            default_min_max_frame_span=(16, 56),
            allowed_state_deltas={"helmet_under_bench": True},
            renderer_action_id="prop_helmet_roll_under_bench",
            motion_profile_id="bronze_helmet_roll_decay",
            requirements=ActionRequirement(props=("ceremonial_helmet", "stone_bench"), locations=("roman_forum_courtyard",)),
        ),
        ActionSpec(
            action_id="prop.scroll_open_adapter",
            domain="PROP",
            supported_verbs=("crack seal", "unroll scroll", "read message"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("sealed_scroll",),
            required_locations=(),
            camera_affordances=("reveal_payoff", "push_in"),
            event_class="reveal",
            default_min_max_frame_span=(18, 64),
            allowed_state_deltas={"scroll_open": True},
            renderer_action_id="prop_scroll_open_adapter",
            motion_profile_id="r1_scroll_unfurl",
            requirements=ActionRequirement(props=("sealed_scroll",)),
        ),
        ActionSpec(
            action_id="prop.door_close_adapter",
            domain="PROP",
            supported_verbs=("gate began to close", "slammed shut", "doors closed", "iron bolt"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("city_gate",),
            required_locations=(),
            camera_affordances=("motivated_cut", "impulse_snap_zoom"),
            event_class="action",
            default_min_max_frame_span=(16, 56),
            allowed_state_deltas={"gate_closed": True},
            renderer_action_id="prop_door_close_adapter",
            motion_profile_id="r1_gate_slam_lock",
            requirements=ActionRequirement(props=("city_gate",), forbidden_pre_states={"gate_closed": True}),
        ),
        # ---- WORLD DOMAIN ----
        ActionSpec(
            action_id="world.market_hill_establish",
            domain="WORLD",
            supported_verbs=("baker's oven glowed", "downhill", "directly in its path", "market hill", "steep slope"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("bakery_oven", "market_cart"),
            required_locations=("roman_market_hill",),
            camera_affordances=("pull_out", "parallax_track", "motivated_cut"),
            event_class="establish",
            default_min_max_frame_span=(20, 68),
            allowed_state_deltas={"geography_established": True},
            renderer_action_id="world_market_hill_establish",
            motion_profile_id="slope_cart_and_glow_establish",
            requirements=ActionRequirement(props=("bakery_oven", "market_cart"), locations=("roman_market_hill",)),
        ),
        ActionSpec(
            action_id="world.market_crowd_pass",
            domain="WORLD",
            supported_verbs=("street obstacles", "crowd", "shoppers", "bystanders"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=("roman_market_hill",),
            camera_affordances=("parallax_track", "actor_follow"),
            event_class="action",
            default_min_max_frame_span=(16, 52),
            allowed_state_deltas={"crowd_active": True},
            renderer_action_id="world_market_crowd_pass",
            motion_profile_id="foreground_parallax_pass",
        ),
        ActionSpec(
            action_id="world.river_harbor_establish",
            domain="WORLD",
            supported_verbs=("harbor quay", "river quay", "wooden pier", "wharf", "river harbor", "tiber quay"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=(),
            required_locations=("roman_river_harbor",),
            camera_affordances=("pull_out", "parallax_track"),
            event_class="establish",
            default_min_max_frame_span=(18, 60),
            allowed_state_deltas={"harbor_established": True},
            renderer_action_id="world_river_harbor_establish",
            motion_profile_id="river_current_ambience",
        ),
        ActionSpec(
            action_id="world.forum_courtyard_establish",
            domain="WORLD",
            supported_verbs=("forum courtyard", "senate steps", "marble columns", "courtyard"),
            compatible_actor_archetypes=COMPATIBLE_SQUIRE_ARCHETYPES,
            required_props=("stone_bench",),
            required_locations=("roman_forum_courtyard",),
            camera_affordances=("pull_out", "motivated_cut"),
            event_class="establish",
            default_min_max_frame_span=(18, 60),
            allowed_state_deltas={"forum_established": True},
            renderer_action_id="world_forum_courtyard_establish",
            motion_profile_id="courtyard_establish",
        ),
    ]
    return {sp.action_id: sp for sp in specs}


def serialize_action_registry(registry: Optional[Dict[str, ActionSpec]] = None) -> Dict[str, Any]:
    reg = registry or build_roman_action_registry()
    return {
        "registry_version": REGISTRY_VERSION,
        "count": len(reg),
        "actions": {aid: asdict(spec) for aid, spec in sorted(reg.items())},
    }


def action_registry_digest(registry: Optional[Dict[str, ActionSpec]] = None) -> str:
    payload = serialize_action_registry(registry)
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _has_negation(text: str) -> Tuple[bool, Optional[str]]:
    low = f" {text.lower()} "
    for nw in NEGATION_WORDS:
        if re.search(rf"\b{re.escape(nw)}\b", low):
            return True, nw
    return False, None


def _check_ambiguous_pronouns(text: str, active_actors: List[str], matched_actors: List[str]) -> Optional[str]:
    low = text.lower()
    # Check ambiguous multi-actor pronoun references like "he pushed him" when >= 2 candidates exist without disambiguator
    if not matched_actors and re.search(r"\b(?:he|him|his)\b", low) and re.search(r"\b(?:him|another|the other|someone)\b", low):
        if len(active_actors) >= 2:
            return f"Ambiguous pronoun binding between actors {active_actors} in '{text}'"
    if not matched_actors and re.search(r"\b(?:he|she|they)\b", low) and len(active_actors) >= 3 and "market" not in low:
        return f"Unbound pronoun actor with {len(active_actors)} equal candidates in '{text}'"
    return None


def resolve_roman_action(
    semantic_beat: Dict[str, Any],
    entities: List[Dict[str, Any]],
    world_inventory: Dict[str, Any],
    style_contract: Optional[Dict[str, Any]] = None,
    *,
    world_state: Optional[Dict[str, Any]] = None,
    registry: Optional[Dict[str, ActionSpec]] = None,
    manual_override: Optional[Dict[str, Any]] = None,
) -> ActionBinding:
    """Resolve one grounded semantic beat strictly against the finite R2 capability registry.

    Raises UnsupportedRomanActionError cleanly on any unsupported, missing, negated, ambiguous,
    or contradictory state request rather than emitting an arbitrary guard fallback.
    """
    reg = registry or build_roman_action_registry()
    ws = dict(world_state or {})
    inv_props = set(world_inventory.get("props", []))
    inv_locs = set(world_inventory.get("locations", []))
    all_actors = [str(e.get("actor_id") or e.get("id")) for e in entities if e.get("actor_id") or e.get("id")]

    line_id = str(semantic_beat.get("line_id", "L00"))
    phrase = str(semantic_beat.get("source_text") or semantic_beat.get("source_phrase") or "").strip()
    low = phrase.lower()

    # 1. Manual override safety validation (explicit log required, cannot bypass missing handler/style!)
    if manual_override:
        ov_aid = manual_override.get("action_id")
        if ov_aid not in reg or not manual_override.get("author_reason"):
            raise UnsupportedRomanActionError(
                "UNSAFE_OVERRIDE",
                line_id,
                phrase,
                str(ov_aid or "unknown_override"),
                "Manual override requires a valid registered action_id and non-empty author_reason",
                missing_render_handler=str(ov_aid or ""),
                suggested_valid_actions=sorted(reg.keys())[:8],
            )
        explicit_id = ov_aid
    else:
        explicit_id = semantic_beat.get("requested_action_id")

    # 2. Style contract guard
    if style_contract and style_contract.get("style_id") != "roman_squire_master.v1":
        raise UnsupportedRomanActionError(
            "UNSAFE_OVERRIDE",
            line_id,
            phrase,
            str(explicit_id or "style_check"),
            f"Locked style must be roman_squire_master.v1 (got {style_contract.get('style_id')})",
        )

    # 3. Check explicit unsupported concepts FIRST (animals, fantastical objects, flying aqueduct, etc.)
    m_unsup = UNSUPPORTED_TOKENS_PATTERN.search(low)
    if m_unsup and not explicit_id:
        raise UnsupportedRomanActionError(
            "UNSUPPORTED_ACTION",
            line_id,
            phrase,
            m_unsup.group(0),
            f"Requested subject/action '{m_unsup.group(0)}' is outside finite Roman 2D R2 capability registry",
            suggested_valid_actions=["actor.sprint_chase", "prop.cart_roll_slope", "prop.vexillum_river_drift", "prop.helmet_roll_under_bench"],
        )

    # 4. Contradictory reversal checks (e.g. gate reopens after slammed shut)
    if re.search(r"\b(?:reopen|reopens|reopened|opens\s+again)\b", low) and ws.get("gate_closed"):
        raise UnsupportedRomanActionError(
            "STATE_CONFLICT",
            line_id,
            phrase,
            "reopen_closed_gate",
            "Causal state conflict: gate cannot reopen after irreversible 'gate_closed=True' without authored reset",
            suggested_valid_actions=["prop.door_close_adapter"],
        )

    # 5. Negated affirmative verb checks (e.g. "The senator never grabbed the spear" -> NEGATED_ACTION unless explicit hush beat)
    is_neg, neg_tok = _has_negation(phrase)
    explicit_non_laugh_beat = bool(re.search(r"\bnobody\s+(?:dared\s+)?laugh\b", low))
    if is_neg and not explicit_non_laugh_beat and not semantic_beat.get("negation_handled_explicitly"):
        # Confirm whether beat strictly asserts non-action like never grabbed / did not run / missed
        if re.search(r"\b(?:grab|grabbed|run|ran|sprint|throw|threw|catch|caught|open|opened|pull|pulled)\b", low):
            raise UnsupportedRomanActionError(
                "NEGATED_ACTION",
                line_id,
                phrase,
                f"negated:{neg_tok}",
                f"Phrase contains negative polarity '{neg_tok}'; cannot bind affirmative action handler",
                suggested_valid_actions=["actor.idle_micro_act", "actor.point_shout_look"],
            )

    # 6. Ambiguous pronoun check
    matched_actors = list(semantic_beat.get("primary_actors") or [])
    amb = _check_ambiguous_pronouns(phrase, all_actors, matched_actors if not semantic_beat.get("actors_inferred_by_pronoun") else [])
    if amb:
        raise UnsupportedRomanActionError(
            "AMBIGUOUS_ACTION",
            line_id,
            phrase,
            "pronoun_resolution",
            amb,
            suggested_valid_actions=["actor.idle_micro_act"],
        )

    # 7. Resolve ActionSpec strictly (either explicit_id or deterministic verb-phrase table, NEVER blind default)
    spec: Optional[ActionSpec] = None
    if explicit_id:
        if explicit_id not in reg:
            raise UnsupportedRomanActionError(
                "UNSUPPORTED_ACTION",
                line_id,
                phrase,
                explicit_id,
                f"Requested action_id '{explicit_id}' is not registered in {REGISTRY_VERSION}",
                missing_render_handler=explicit_id,
                suggested_valid_actions=sorted(reg.keys())[:10],
            )
        spec = reg[explicit_id]
    else:
        best_score = 0
        for aid, cand in reg.items():
            hits = sum(2 + len(v.split()) for v in cand.supported_verbs if re.search(rf"\b{re.escape(v)}\b", low))
            if hits > best_score:
                best_score = hits
                spec = cand
        if spec is None or best_score <= 0:
            raise UnsupportedRomanActionError(
                "UNSUPPORTED_ACTION",
                line_id,
                phrase,
                semantic_beat.get("raw_verb") or "unrecognized_verb",
                f"No supported 2D action matches phrase '{phrase}'",
                suggested_valid_actions=["actor.sprint_chase", "actor.reach_grab_prop", "prop.cart_roll_slope", "prop.vexillum_river_drift", "prop.helmet_roll_under_bench"],
            )

    # 8. Inventory & asset requirements validation
    missing_props = [p for p in (set(spec.required_props) | set(spec.requirements.props)) if p not in inv_props]
    loc_id = str(semantic_beat.get("location_id") or (spec.required_locations[0] if spec.required_locations else world_inventory.get("default_location", "")))
    missing_locs = [l for l in (set(spec.required_locations) | set(spec.requirements.locations)) if l not in inv_locs]
    if missing_props or missing_locs or (loc_id and inv_locs and loc_id not in inv_locs):
        miss_l = list(missing_locs)
        if loc_id and inv_locs and loc_id not in inv_locs and loc_id not in miss_l:
            miss_l.append(loc_id)
        raise UnsupportedRomanActionError(
            "MISSING_ASSET",
            line_id,
            phrase,
            spec.action_id,
            f"Required assets absent from scene_manifest inventory: props={missing_props}, locations={miss_l}",
            missing_props=missing_props,
            missing_locations=miss_l,
        )

    # 9. Causal precondition / state conflict validation
    for k, expected_v in spec.requirements.required_pre_states.items():
        if ws.get(k) != expected_v:
            raise UnsupportedRomanActionError(
                "STATE_CONFLICT",
                line_id,
                phrase,
                spec.action_id,
                f"Action '{spec.action_id}' requires world state '{k}=={expected_v}', got '{ws.get(k)}'",
            )
    for k, forbid_v in spec.requirements.forbidden_pre_states.items():
        if ws.get(k) == forbid_v:
            raise UnsupportedRomanActionError(
                "STATE_CONFLICT",
                line_id,
                phrase,
                spec.action_id,
                f"Action '{spec.action_id}' forbidden when '{k}=={forbid_v}'",
            )

    # 10. Archetype compatibility validation
    actor_map = {str(e.get("actor_id") or e.get("id")): str(e.get("archetype") or e.get("actor_id") or e.get("id")) for e in entities}
    use_actors = matched_actors or (all_actors[:1] if all_actors else [])
    for aid in use_actors:
        arch = actor_map.get(aid, aid)
        if arch not in spec.compatible_actor_archetypes:
            raise UnsupportedRomanActionError(
                "UNSUPPORTED_ACTION",
                line_id,
                phrase,
                spec.action_id,
                f"Actor '{aid}' archetype '{arch}' incompatible with '{spec.action_id}'",
                missing_actors=[aid],
            )

    post_state = dict(ws)
    post_state.update(spec.allowed_state_deltas)

    return ActionBinding(
        binding_id=str(semantic_beat.get("beat_id") or f"BND_{line_id}"),
        line_id=line_id,
        source_phrase=phrase,
        action_id=spec.action_id,
        domain=spec.domain,
        event_class=spec.event_class,
        renderer_action_id=spec.renderer_action_id,
        motion_profile_id=spec.motion_profile_id,
        actor_ids=use_actors,
        prop_ids=sorted(set(spec.required_props) | set(semantic_beat.get("props") or [])),
        location_id=loc_id or "roman_market_hill",
        camera_affordance=spec.camera_affordances[0],
        word_anchors=[w for w in phrase.split() if w.strip()],
        pre_states=dict(ws),
        post_states=post_state,
        evidence_source_span={"line_id": line_id, "text": phrase},
        confidence=0.96 if explicit_id else 0.88,
        ambiguity_flags=[],
        override_log=manual_override,
    )


def validate_action_bindings(
    shot_plan: Dict[str, Any],
    action_registry: Optional[Dict[str, ActionSpec]] = None,
    asset_manifest: Optional[Dict[str, Any]] = None,
    renderer_registry: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Fail-closed validation of compiled shot_plan against capability registry, scene assets & JS renderers."""
    reg = action_registry or build_roman_action_registry()
    known_renderers = set(renderer_registry) if renderer_registry is not None else {s.renderer_action_id for s in reg.values()}
    inv_props = set((asset_manifest or {}).get("props", []))
    inv_locs = set((asset_manifest or {}).get("locations", []))

    errors: List[Dict[str, Any]] = []
    shots = shot_plan.get("shots", [])
    if not shots:
        return {
            "valid": False,
            "registry_digest": action_registry_digest(reg),
            "errors": [{"error_code": "UNSUPPORTED_ACTION", "message": "shot_plan contains zero shots"}],
        }

    for sh in shots:
        sid = sh.get("id", "?")
        aid = sh.get("action_id")
        raid = sh.get("renderer_action_id") or sh.get("sub_action")
        if not aid or aid not in reg:
            errors.append({
                "error_code": "UNSUPPORTED_ACTION",
                "shot_id": sid,
                "action_id": aid,
                "message": f"Shot {sid} has unregistered or missing action_id '{aid}'",
            })
            continue
        spec = reg[aid]
        if raid != spec.renderer_action_id or raid not in known_renderers:
            errors.append({
                "error_code": "UNSUPPORTED_ACTION",
                "shot_id": sid,
                "action_id": aid,
                "missing_render_handler": raid,
                "message": f"Shot {sid} renderer handler '{raid}' invalid or not present in JS renderer map (expected '{spec.renderer_action_id}')",
            })
        if asset_manifest:
            miss_p = [p for p in spec.required_props if p not in inv_props]
            if miss_p:
                errors.append({"error_code": "MISSING_ASSET", "shot_id": sid, "missing_prop": miss_p})
            if inv_locs and sh.get("location_id") not in inv_locs:
                errors.append({"error_code": "MISSING_ASSET", "shot_id": sid, "missing_location": [sh.get("location_id")]})

    return {
        "valid": len(errors) == 0,
        "registry_version": REGISTRY_VERSION,
        "registry_digest": action_registry_digest(reg),
        "checked_shots": len(shots),
        "errors": errors,
    }
