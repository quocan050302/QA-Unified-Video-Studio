"""tools/scene_composition.py — Dynamic Scene Composition & World Continuity Engine (V14.6).

Eliminates wallpaper repetition by planning purposeful environmental progression
(advancing dust, terrain props, tents, flags, evolving time-of-day/weather) while
preserving geographical continuity across the entire video.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, Field

from tools.visual_storytelling import StoryContext, VisualStoryPlan


class SceneEnvironment(BaseModel):
    """Environmental parameters and spatial staging for a single shot."""
    location_id: str = "battlefield_plains"
    ground_type: str = "battlefield"
    time_of_day: str = "day"
    seed: int = 42
    ground_y: float = 0.66
    weather: Dict[str, Any] = Field(default_factory=dict)
    terrain_props: Dict[str, Any] = Field(default_factory=dict)
    foreground_elements: List[Dict[str, Any]] = Field(default_factory=list)
    background_formations: List[Dict[str, Any]] = Field(default_factory=list)
    visual_motif: str = "open_field"
    environmental_phase: str = "early_approach"


def plan_scene_composition(
    timeline_plans: List[VisualStoryPlan],
    story_context: StoryContext,
    aspect: Literal["16:9", "9:16"] = "16:9",
) -> Dict[str, SceneEnvironment]:
    """
    Plan progressive, non-repetitive scene compositions across all shots in the timeline.
    Ensures that shots within an ongoing battle share geographical continuity while
    visibly evolving through 5 distinct environmental phases.
    """
    environments: Dict[str, SceneEnvironment] = {}
    total = len(timeline_plans)

    for idx, plan in enumerate(timeline_plans):
        sid = plan.shot_id
        rel_pos = idx / max(1, total - 1)
        base_seed = (idx * 17 + 101) % 997

        if story_context.genre == "roman":
            # 5 Causal Stages of Roman Battle:
            if rel_pos < 0.18:
                # Stage 1: Threat Approach / Hook
                # Wide expansive plain, distant Roman encampment tents on distant hill, light morning golden sun
                env = SceneEnvironment(
                    location_id="camp_plain",
                    ground_type="plain",
                    time_of_day="golden",
                    seed=base_seed,
                    ground_y=0.68,
                    weather={"sun": True, "clouds": 2, "haze": ["#e8b060", 0.12]},
                    terrain_props={
                        "tents": 4,
                        "flags": [{"color": "#b82b2b", "x": 0.85}],
                        "trees": 3,
                        "pebbles": 8,
                        "tufts": 28,
                    },
                    background_formations=[
                        {"preset": "triarius", "cols": 8, "rows": 2, "x": 0.25, "y": 0.64, "scale": 0.35}
                    ],
                    visual_motif="encampment_horizon",
                    environmental_phase="early_approach",
                )

            elif rel_pos < 0.40:
                # Stage 2: Physical Impact / Collision
                # Trampled mud furrows, dust puffs, shattered pilum debris, direct battle daylight
                env = SceneEnvironment(
                    location_id="contact_line",
                    ground_type="battlefield",
                    time_of_day="day",
                    seed=base_seed,
                    ground_y=0.66,
                    weather={"sun": True, "clouds": 3, "dust": True},
                    terrain_props={
                        "mud": True,
                        "wet": False,
                        "patches": 5,
                        "tufts": 18,
                        "pebbles": 14,
                        "bushes": 1,
                    },
                    foreground_elements=[
                        {"kind": "pilum", "x": 0.12, "y": 0.94, "s": 0.18, "rot": 0.4}
                    ],
                    visual_motif="trampled_clash_zone",
                    environmental_phase="shield_collision",
                )

            elif rel_pos < 0.65:
                # Stage 3: Intense Attrition & Command Signal
                # Rising battle dust, standard banner planted in midground, trampled dark earth, shifting skies
                env = SceneEnvironment(
                    location_id="attrition_line",
                    ground_type="mud",
                    time_of_day="sunset",
                    seed=base_seed,
                    ground_y=0.67,
                    weather={"sun": True, "clouds": 4, "haze": ["#b06545", 0.15]},
                    terrain_props={
                        "mud": True,
                        "wet": True,
                        "flags": [{"color": "#b82b2b", "charge": "eagle", "x": 0.18}],
                        "patches": 6,
                        "pebbles": 12,
                    },
                    background_formations=[
                        {"preset": "princeps", "cols": 10, "rows": 3, "x": 0.5, "y": 0.65, "scale": 0.38}
                    ],
                    visual_motif="heavy_attrition",
                    environmental_phase="intense_attrition",
                )

            elif rel_pos < 0.85:
                # Stage 4: Tactical Lane Opening & Withdrawal
                # Corridor opening, reserve banners visible in distance, storm/cloudy tension
                env = SceneEnvironment(
                    location_id="relief_corridor",
                    ground_type="battlefield",
                    time_of_day="dusk",
                    seed=base_seed,
                    ground_y=0.65,
                    weather={"sun": False, "clouds": 5, "haze": ["#5a4060", 0.14]},
                    terrain_props={
                        "tents": 1,
                        "flags": [{"color": "#2c5088", "x": 0.88}],
                        "mud": True,
                        "patches": 4,
                        "tufts": 14,
                    },
                    background_formations=[
                        {"preset": "hastatus", "cols": 6, "rows": 2, "x": 0.15, "y": 0.64, "scale": 0.32}
                    ],
                    visual_motif="maneuver_passage",
                    environmental_phase="relief_reorganization",
                )

            else:
                # Stage 5: Resolute Stand & Tactical Payoff
                # Dramatic dusk/sunset sky, fresh red flags, intact orderly line, clear tactical overview
                env = SceneEnvironment(
                    location_id="resolute_line",
                    ground_type="battlefield",
                    time_of_day="dusk",
                    seed=base_seed,
                    ground_y=0.66,
                    weather={"sun": True, "clouds": 3, "haze": ["#ff7744", 0.16]},
                    terrain_props={
                        "flags": [
                            {"color": "#b82b2b", "x": 0.12},
                            {"color": "#b82b2b", "charge": "eagle", "x": 0.50},
                            {"color": "#b82b2b", "x": 0.88},
                        ],
                        "mud": False,
                        "tufts": 22,
                        "pebbles": 10,
                    },
                    visual_motif="decisive_victory",
                    environmental_phase="decisive_stand",
                )

        elif story_context.genre == "knight":
            # Medieval tournament / castle siege field
            env = SceneEnvironment(
                location_id="medieval_field",
                ground_type="field",
                time_of_day="golden" if rel_pos < 0.5 else "sunset",
                seed=base_seed,
                ground_y=0.68,
                weather={"clouds": 3},
                terrain_props={
                    "flags": [{"color": "#3f6fb0", "charge": "fleur", "x": 0.82}],
                    "tents": 2,
                    "trees": 2,
                },
                visual_motif="chivalric_combat",
                environmental_phase="chivalric_engagement",
            )

        elif story_context.genre == "samurai":
            # Japanese feudal hills with cypress trees and mist
            env = SceneEnvironment(
                location_id="samurai_hills",
                ground_type="hills",
                time_of_day="dawn" if rel_pos < 0.5 else "dusk",
                seed=base_seed,
                ground_y=0.68,
                weather={"clouds": 2, "haze": ["#86a06a", 0.12]},
                terrain_props={
                    "trees": 4,
                    "bushes": 3,
                    "flags": [{"color": "#111111", "x": 0.85}],
                },
                visual_motif="feudal_clash",
                environmental_phase="bushido_duel",
            )

        elif story_context.pack == "dem":
            # Modern everyday room / desk setting
            env = SceneEnvironment(
                location_id="study_room",
                ground_type="paper",
                time_of_day="day",
                seed=base_seed,
                ground_y=0.82,
                visual_motif="modern_focus",
                environmental_phase="habit_progression",
            )

        else:
            # Generic safe environment
            env = SceneEnvironment(
                location_id="generic_outdoor",
                ground_type="field",
                time_of_day="day",
                seed=base_seed,
                ground_y=0.66,
                visual_motif="open_ground",
                environmental_phase="generic_progression",
            )

        environments[sid] = env

    return environments


def compile_environment_to_render_args(
    env: SceneEnvironment,
    shot_args: Dict[str, Any],
    pack: str = "squire",
) -> Dict[str, Any]:
    """
    Compile a SceneEnvironment into exact template arguments for render.mjs / packs/squire/world.js.
    """
    args = copy.deepcopy(shot_args)

    if pack == "squire":
        args["bg"] = env.ground_type
        args["time"] = env.time_of_day
        args["seed"] = env.seed

        bg_opts = args.setdefault("bgOpts", {})
        bg_opts["time"] = env.time_of_day
        bg_opts["seed"] = env.seed
        bg_opts["groundY"] = env.ground_y

        for k, v in env.terrain_props.items():
            bg_opts[k] = v

        if env.weather.get("dust"):
            fx_list = args.setdefault("fx", [])
            if not any(f.get("kind") == "dust" for f in fx_list):
                fx_list.append({"kind": "dust", "at": 0.2, "s": 0.15})

        if env.weather.get("haze"):
            args["midHaze"] = env.weather["haze"]

        # Back formation depth layer
        if env.background_formations and not args.get("back"):
            args["back"] = env.background_formations

        # Foreground prop occluders
        if env.foreground_elements and not args.get("props"):
            args["props"] = env.foreground_elements

    elif pack == "dem":
        args["bg"] = "paper"

    return args


def choose_shot_layout(
    scale: str,
    viewpoint: str,
    actors_count: int,
    aspect: Literal["16:9", "9:16"] = "16:9",
) -> Dict[str, Any]:
    """
    Calculate dynamic spatial staging: subject occupancy, focal quadrant,
    and safe margins for 16:9 or 9:16 aspect ratios.
    """
    is_vertical = (aspect == "9:16")

    if is_vertical:
        # Vertical framing: tighter horizontal bounds, more vertical headroom
        x_min, x_max = 0.12, 0.88
        y_min, y_max = 0.15, 0.88
    else:
        # Horizontal 16:9 framing: cinematic wide rule-of-thirds
        x_min, x_max = 0.08, 0.92
        y_min, y_max = 0.10, 0.92

    if scale == "wide":
        focal_quadrant = "center_lower"
        occupancy = 0.45
    elif scale == "close":
        focal_quadrant = "upper_thirds"
        occupancy = 0.70
    elif scale == "tactical":
        focal_quadrant = "full_canvas"
        occupancy = 0.80
    else:
        focal_quadrant = "rule_of_thirds"
        occupancy = 0.58

    return {
        "x_safe_min": x_min,
        "x_safe_max": x_max,
        "y_safe_min": y_min,
        "y_safe_max": y_max,
        "focal_quadrant": focal_quadrant,
        "subject_occupancy": occupancy,
    }


def audit_scene_repetition_from_frames(
    shots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Audit shot sequence for wallpaper repetition:
    Flags sequences where more than 2 consecutive non-tactical shots use
    identical (bg, time, seed) combinations.
    """
    repeats: List[str] = []
    prev_sig = None
    consecutive_matches = 0

    for idx, s in enumerate(shots):
        if s.get("tpl") == "top":
            continue

        args = s.get("args", {})
        bg = args.get("bg", "field")
        time_val = args.get("time", "day")
        seed_val = args.get("seed", 0)

        sig = (bg, time_val, seed_val)
        if sig == prev_sig:
            consecutive_matches += 1
            if consecutive_matches >= 2:
                repeats.append(f"Shot {s.get('id', idx)} repeats identical background signature {sig}")
        else:
            consecutive_matches = 0
            prev_sig = sig

    return {
        "passed": len(repeats) == 0,
        "repeat_violations": repeats,
        "total_violations": len(repeats),
    }
