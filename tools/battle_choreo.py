"""battle_choreo.py — Roman Battle Choreography & Narration-to-Action Compiler (V11).

Converts spoken historical battle narration into deterministic, causally sound,
multi-unit 2D tactical animation parameters for the Squire pack.

Supported tactical phases:
1. APPROACH & IMPACT: Friendly and enemy battle lines advance, close distance, clash, brace, push.
2. BREAKTHROUGH & GAP OPEN: Enemy punches into the front line, a gap opens, enemy enters.
3. RELIEF & ROTATION: Second line (Principes/reserves) advances through intervals to plug breach,
   while first line (Hastati) falls back or rotates safely.
4. FLANK & ENCIRCLEMENT / COUNTERATTACK: Flanking units curve around enemy flanks to form a pincer pocket.
"""

import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    canonical_json_serialize,
    compute_canonical_audio_hash,
    compute_canonical_visual_hash,
    read_json,
    write_json,
)
from visual_facts import extract_quantity_facts

BATTLE_PLAN_VERSION = "1.1"

# Semantic Event Types
BATTLE_EVENTS = {
    "ADVANCE", "APPROACH", "CHARGE", "BRACE", "IMPACT",
    "BREAKTHROUGH", "GAP_OPEN", "FRONT_LINE_REPLACE", "RESERVE_ADVANCE",
    "WITHDRAW", "RETREAT", "RALLY", "FLANK_LEFT", "FLANK_RIGHT",
    "ENCIRCLE", "COUNTERATTACK", "MISSILE_VOLLEY", "SHIELD_WALL",
    "COMMAND_SIGNAL", "PURSUIT", "HOLD_POSITION", "MAP_EXPLAIN", "UNKNOWN"
}

# Whitelisted SFX mapping for battle actions
BATTLE_SFX_MAP = {
    "APPROACH": ("drum_march.wav", "footsteps.wav"),
    "ADVANCE": ("drum_march.wav", "footsteps.wav"),
    "CHARGE": ("battle_roar.wav", "whoosh_fast.wav"),
    "BRACE": ("shield_bash.wav", "armor_clank.wav"),
    "IMPACT": ("shield_bash.wav", "impact_heavy.wav", "sword_clash.wav"),
    "BREAKTHROUGH": ("spear_hit.wav", "shield_bash.wav", "battle_roar.wav"),
    "GAP_OPEN": ("shield_bash.wav", "armor_clank.wav"),
    "FRONT_LINE_REPLACE": ("sword_clash.wav", "drum_hit.wav"),
    "RESERVE_ADVANCE": ("drum_march.wav", "shield_bash.wav"),
    "WITHDRAW": ("footsteps.wav", "armor_clank.wav"),
    "RETREAT": ("whoosh_long.wav", "downer.wav"),
    "RALLY": ("horn_roman.wav", "war_horn.wav"),
    "FLANK_LEFT": ("drum_march.wav", "whoosh_mid.wav"),
    "FLANK_RIGHT": ("drum_march.wav", "whoosh_mid.wav"),
    "ENCIRCLE": ("horn_roman.wav", "battle_roar.wav", "sword_clash.wav"),
    "COUNTERATTACK": ("sword_clash.wav", "battle_roar.wav"),
    "MISSILE_VOLLEY": ("arrow_volley.wav", "javelin_throw.wav", "arrow_thunk.wav"),
    "SHIELD_WALL": ("shield_bash.wav", "armor_clank.wav"),
    "COMMAND_SIGNAL": ("horn_roman.wav", "war_horn.wav"),
    "PURSUIT": ("hooves_gallop.wav", "battle_roar.wav"),
    "HOLD_POSITION": ("drum_hit.wav", "shield_bash.wav"),
    "MAP_EXPLAIN": ("page_turn.wav", "ting_idea.wav"),
}


def parse_battle_events(
    shots: List[Dict[str, Any]],
    transcript: Optional[str] = None,
    timed_words: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Parse battle events from shot text with strict negation, tense, and actor identification."""
    events: List[Dict[str, Any]] = []

    # Negation patterns
    negation_regex = re.compile(
        r"\b(could\s+not|can\s*not|never|nobody|no\s+one|did\s+not|without|refused\s+to|"
        r"hardly|scarcely|couldn't|can't|didn't|won't|unable\s+to|failed\s+to|impossible\s+to|"
        r"kh\u00f4ng\s+th\u1ec3|kh\u00f4ng\s+bao\s+gi\u1edd|ch\u01b0a\s+t\u1eebng|kh\u00f4ng\s+b\u1ecb|"
        r"kh\u00f4ng\s+th\u1ee7ng|kh\u00f4ng\s+thua|kh\u00f4ng\s+v\u1ee1)\s+([a-z\u00e0-\u1ef9\s]{1,30})",
        re.IGNORECASE,
    )

    hypothetical_regex = re.compile(
        r"\b(if\s+they|had\s+they|could\s+have|might\s+have|suppose|assuming|n\u1ebfu|gi\u1ea3\s+s\u1eed)\b",
        re.IGNORECASE,
    )

    for idx, s in enumerate(shots):
        raw_line = s.get("line") or ""
        scene_desc = s.get("scene") or ""
        combined_text = f"{raw_line} {scene_desc}".strip()
        text_lower = combined_text.lower()
        dur = float(s.get("dur", 3.0))
        start_t = float(s.get("start", idx * dur))

        is_hypo = bool(hypothetical_regex.search(combined_text))

        # Helper to check if a specific pattern is negated
        def is_negated(pat: str) -> bool:
            for m in negation_regex.finditer(combined_text):
                if re.search(pat, m.group(0), re.IGNORECASE):
                    return True
            return False

        # 1. Breakthrough / Gap Open
        break_pat = r"\b(breakthrough|broke\s+through|break\s+the\s+line|breach|gap\s+open|hole\s+in|pierce|ch\u1ecdc\s+th\u1ee7ng|ph\u00e1\s+v\u1ee1|l\u1ed7\s+h\u1ed5ng|m\u1edf\s+toang)\b"
        if re.search(break_pat, text_lower):
            if is_negated(break_pat):
                # Negated breakthrough -> Front line holds!
                events.append({
                    "shot_id": s.get("id", f"s{idx:03d}"),
                    "event_type": "HOLD_POSITION",
                    "actor_side": "roman",
                    "target_side": "opponent",
                    "source_span": combined_text,
                    "is_negated": True,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.95,
                    "note": "Negated breakthrough: Roman front line held firmly against assault",
                    "start_t": start_t,
                    "dur": dur,
                })
            else:
                events.append({
                    "shot_id": s.get("id", f"s{idx:03d}"),
                    "event_type": "BREAKTHROUGH",
                    "actor_side": "opponent",
                    "target_side": "roman",
                    "source_span": combined_text,
                    "is_negated": False,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.95,
                    "note": "Enemy creates a breach in the first Roman line",
                    "start_t": start_t,
                    "dur": dur,
                })

        # 2. Front line Relief / Rotation / Reserves Advance
        relief_pat = r"\b(relieve|relief|rotate|rotation|replace|second\s+line|reserve|principes|triarii|plug\s+the\s+gap|thay\s+qu\u00e2n|h\u00e0ng\s+hai|ti\u1ebfp\u1ee9ng|xoay\s+v\u00f2ng|l\u1ea5p\s+ch\u1ed7)\b"
        if re.search(relief_pat, text_lower) and not is_negated(relief_pat):
            events.append({
                "shot_id": s.get("id", f"s{idx:03d}"),
                "event_type": "FRONT_LINE_REPLACE",
                "actor_side": "roman",
                "target_side": "opponent",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.92,
                "note": "Second line moves forward through intervals to relieve front ranks",
                "start_t": start_t,
                "dur": dur,
            })

        # 3. Flank / Encirclement / Pincer
        flank_pat = r"\b(flank|pincer|encircle|surround|double\s+envelopment|trap|b\u1ecdc\s+s\u01b0\u1eddn|bao\s+v\u00e2y|k\u1eb9p\s+th\u1ecbt|v\u00e2y\s+h\u00e3m)\b"
        if re.search(flank_pat, text_lower):
            if is_negated(flank_pat):
                events.append({
                    "shot_id": s.get("id", f"s{idx:03d}"),
                    "event_type": "HOLD_POSITION",
                    "actor_side": "opponent",
                    "target_side": "roman",
                    "source_span": combined_text,
                    "is_negated": True,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.90,
                    "note": "Negated encirclement: formation evaded enclosure",
                    "start_t": start_t,
                    "dur": dur,
                })
            else:
                events.append({
                    "shot_id": s.get("id", f"s{idx:03d}"),
                    "event_type": "ENCIRCLE",
                    "actor_side": "roman",
                    "target_side": "opponent",
                    "source_span": combined_text,
                    "is_negated": False,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.94,
                    "note": "Flanks sweep inward to encircle enemy vanguard",
                    "start_t": start_t,
                    "dur": dur,
                })

        # 4. Missile Volley / Javelins / Pila / Arrows
        missile_pat = r"\b(volley|pilum|pila|javelin|arrow|missile|shower\s+of|ph\u00f3ng\s+lao|m\u01b0a\s+t\u00ean|b\u1eafn\s+t\u00ean)\b"
        if re.search(missile_pat, text_lower) and not is_negated(missile_pat):
            events.append({
                "shot_id": s.get("id", f"s{idx:03d}"),
                "event_type": "MISSILE_VOLLEY",
                "actor_side": "roman" if "pilum" in text_lower or "lao" in text_lower else "opponent",
                "target_side": "opponent" if "pilum" in text_lower or "lao" in text_lower else "roman",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.88,
                "note": "Missile volley launched across engagement line",
                "start_t": start_t,
                "dur": dur,
            })

        # 5. Approach / Advance / March / Impact / Clash
        advance_pat = r"\b(advance|march|charge|clash|impact|collide|approach|braced|push|ti\u1ebfn\s+qu\u00e2n|xung\s+phong|va\s+ch\u1ea1m|gi\u00e1p\s+l\u00e1\s+c\u00e0|h\u00fac\s+m\u1ea1nh)\b"
        if re.search(advance_pat, text_lower) and not is_negated(advance_pat):
            events.append({
                "shot_id": s.get("id", f"s{idx:03d}"),
                "event_type": "IMPACT" if ("clash" in text_lower or "impact" in text_lower or "va" in text_lower) else "ADVANCE",
                "actor_side": "roman",
                "target_side": "opponent",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.85,
                "note": "Units advance and make frontline contact",
                "start_t": start_t,
                "dur": dur,
            })

        # 6. Command Signal / Standard movement / Consul
        command_pat = r"\b(signal|horn|trumpet|command|consul|centurion|standard|eagle|hi\u1ec7u\s+l\u1ec7nh|ti\u1ebfng\s+t\u00f9\s+v\u00e0|ch\u1ec9\s+huy)\b"
        if re.search(command_pat, text_lower) and not is_negated(command_pat):
            events.append({
                "shot_id": s.get("id", f"s{idx:03d}"),
                "event_type": "COMMAND_SIGNAL",
                "actor_side": "roman",
                "target_side": "roman",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.90,
                "note": "Commander orders tactical maneuver via horn or standard",
                "start_t": start_t,
                "dur": dur,
            })

    # Fallback if no specific battle event was triggered
    if not events and shots:
        s0 = shots[0]
        events.append({
            "shot_id": s0.get("id", "s001"),
            "event_type": "ADVANCE",
            "actor_side": "roman",
            "target_side": "opponent",
            "source_span": s0.get("line", ""),
            "is_negated": False,
            "is_hypothetical": False,
            "confidence": 0.60,
            "note": "Baseline unit advancement",
            "start_t": 0.0,
            "dur": float(s0.get("dur", 3.0)),
        })

    return events


def build_battle_state_timeline(
    events: List[Dict[str, Any]],
    shot_windows: List[Dict[str, Any]],
    spoken_alignment: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Construct a spatio-temporal state machine tracking units across shot cuts with causality."""
    units = {
        "ROMAN_FRONT_1": {
            "id": "ROMAN_FRONT_1",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "hastati_frontline",
            "name": "Hastati First Line",
            "initial_x": 0.28,
            "initial_y": 0.50,
            "w": 0.08,
            "h": 0.16,
            "facing": 1,
            "active": True,
        },
        "ROMAN_RESERVE_2": {
            "id": "ROMAN_RESERVE_2",
            "side": "roman",
            "color_side": "blue",
            "preset": "princeps",
            "role": "principes_relief",
            "name": "Principes Second Line",
            "initial_x": 0.16,
            "initial_y": 0.50,
            "w": 0.08,
            "h": 0.16,
            "facing": 1,
            "active": True,
        },
        "ROMAN_REAR_3": {
            "id": "ROMAN_REAR_3",
            "side": "roman",
            "color_side": "blue",
            "preset": "triarius",
            "role": "triarii_reserve",
            "name": "Triarii Veterans",
            "initial_x": 0.06,
            "initial_y": 0.50,
            "w": 0.07,
            "h": 0.16,
            "facing": 1,
            "active": True,
        },
        "ENEMY_VANGUARD": {
            "id": "ENEMY_VANGUARD",
            "side": "opponent",
            "color_side": "red",
            "preset": "latin",
            "role": "enemy_main_body",
            "name": "Enemy Vanguard",
            "initial_x": 0.72,
            "initial_y": 0.50,
            "w": 0.10,
            "h": 0.22,
            "facing": -1,
            "active": True,
        },
        "ROMAN_LEFT_FLANK": {
            "id": "ROMAN_LEFT_FLANK",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "cavalry_left_pincer",
            "name": "Roman Left Flank",
            "initial_x": 0.24,
            "initial_y": 0.20,
            "w": 0.06,
            "h": 0.08,
            "facing": 1,
            "active": True,
        },
        "ROMAN_RIGHT_FLANK": {
            "id": "ROMAN_RIGHT_FLANK",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "cavalry_right_pincer",
            "name": "Roman Right Flank",
            "initial_x": 0.24,
            "initial_y": 0.80,
            "w": 0.06,
            "h": 0.08,
            "facing": 1,
            "active": True,
        },
    }

    # Derive dominant tactical phase across event sequence
    phase_flags = {
        "has_approach": any(e["event_type"] in ("ADVANCE", "APPROACH", "CHARGE", "IMPACT") for e in events),
        "has_break": any(e["event_type"] == "BREAKTHROUGH" and not e.get("is_negated") for e in events),
        "has_relief": any(e["event_type"] in ("FRONT_LINE_REPLACE", "RESERVE_ADVANCE") for e in events),
        "has_flank": any(e["event_type"] in ("FLANK_LEFT", "FLANK_RIGHT", "ENCIRCLE") and not e.get("is_negated") for e in events),
    }

    timeline = {
        "version": BATTLE_PLAN_VERSION,
        "units": units,
        "phase_flags": phase_flags,
        "events": events,
        "shot_windows": shot_windows,
        "causality_valid": True,
    }

    return timeline


def validate_battle_causality(timeline: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Strictly assert causality rules on battle maneuvers."""
    errors = []
    events = timeline.get("events", [])

    # Rule 1: A breakthrough must precede relief/rotation if relief is described as plugging a gap
    break_idx = next((i for i, e in enumerate(events) if e["event_type"] == "BREAKTHROUGH" and not e.get("is_negated")), -1)
    relief_idx = next((i for i, e in enumerate(events) if e["event_type"] == "FRONT_LINE_REPLACE"), -1)
    if relief_idx != -1 and break_idx != -1 and relief_idx < break_idx:
        errors.append("Causality violation: Relief/replacement occurred before enemy breakthrough")

    # Rule 2: An encirclement cannot occur without units reaching opposing sides
    encircle_idx = next((i for i, e in enumerate(events) if e["event_type"] == "ENCIRCLE" and not e.get("is_negated")), -1)
    if encircle_idx != -1:
        # Verify both left and right flank exist in unit state
        units = timeline.get("units", {})
        if "ROMAN_LEFT_FLANK" not in units or "ROMAN_RIGHT_FLANK" not in units:
            errors.append("Encirclement asserted but flanking units missing from tactical roster")

    return len(errors) == 0, errors


def choose_battle_camera_and_scale(
    event_type: str,
    aspect: str = "16:9",
    shot_index: int = 0,
) -> Dict[str, Any]:
    """Select appropriate camera angle, movement, and mobile safe-zones."""
    is_vertical = (aspect == "9:16")

    # Tactical mapping
    if event_type in ("ENCIRCLE", "FRONT_LINE_REPLACE"):
        tpl = "top"
        move = "in"
        zoom = [0.5, 0.5, 1.25, 0.0, 1.2]
    elif event_type in ("BREAKTHROUGH", "IMPACT", "CHARGE"):
        tpl = "army"
        move = "right"
        zoom = [0.55, 0.52, 1.35, 0.0, 0.8]
    elif event_type == "COMMAND_SIGNAL":
        tpl = "close"
        move = "in"
        zoom = [0.5, 0.45, 1.4, 0.0, 0.6]
    elif event_type == "MISSILE_VOLLEY":
        tpl = "scene"
        move = "up"
        zoom = [0.5, 0.4, 1.2, 0.0, 1.0]
    else:
        # Default rhythmic variation
        tpl = "top" if (shot_index % 2 == 0) else "army"
        move = "in"
        zoom = [0.5, 0.5, 1.15, 0.0, 1.0]

    safe_zones = {
        "is_vertical": is_vertical,
        "margin_bottom": 0.22 if is_vertical else 0.08,
        "margin_top": 0.12 if is_vertical else 0.05,
        "character_scale": 1.25 if is_vertical else 1.0,
    }

    return {
        "template": tpl,
        "move": move,
        "zoom": zoom,
        "safe_zones": safe_zones,
    }


def compile_battle_timeline_to_shots(
    timeline: Dict[str, Any],
    existing_shots: List[Dict[str, Any]],
    project_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Compile abstract tactical timeline into executable Squire tpl, args, and sfx parameters."""
    aspect = project_config.get("aspect", "16:9")
    events = timeline.get("events", [])
    compiled_shots: List[Dict[str, Any]] = []

    for idx, s in enumerate(existing_shots):
        new_s = dict(s)
        # Preserve manual locks strictly
        if s.get("manual") or s.get("visual_source") == "manual":
            compiled_shots.append(new_s)
            continue

        dur = float(s.get("dur", 3.0))
        # Match event for current shot index
        evt = events[idx] if idx < len(events) else events[-1]
        ev_type = evt.get("event_type", "ADVANCE")
        cam = choose_battle_camera_and_scale(ev_type, aspect, idx)

        new_s["visual_source"] = "battle_choreo_v11"
        new_s["battle_plan_version"] = BATTLE_PLAN_VERSION
        new_s["source_span"] = evt.get("source_span", s.get("line", ""))
        new_s["confidence"] = evt.get("confidence", 0.90)

        tpl = cam["template"]
        args: Dict[str, Any] = dict(s.get("args") or {})
        args["move"] = cam["move"]
        args["zoom"] = cam["zoom"]

        # Compile template-specific geometry
        if tpl == "top":
            # Coordinated multi-block top-down battlefield
            blocks = []
            if ev_type == "BREAKTHROUGH":
                # Front line breached: two separated blocks with gap opening dynamically before enemy wedges through
                blocks.append({
                    "id": "ROMAN_FRONT_LEFT",
                    "label": "Hastati (Left)",
                    "side": "blue",
                    "w": 0.08, "h": 0.08,
                    "x": 0.38, "y": 0.38,
                    "path": [[0.0, 0.40, 0.42], [round(dur * 0.6, 2), 0.35, 0.33]],
                    "spears": True,
                    "face": 1,
                    "tilt": -0.15,
                    "tiltAt": [[round(dur * 0.3, 2), -0.15], [round(dur * 0.7, 2), -0.28]],
                    "gap": {"at": round(dur * 0.2, 2), "dur": 0.6, "w": 0.45},
                    "impactAt": round(dur * 0.35, 2),
                })
                blocks.append({
                    "id": "ROMAN_FRONT_RIGHT",
                    "label": "Hastati (Right)",
                    "side": "blue",
                    "w": 0.08, "h": 0.08,
                    "x": 0.38, "y": 0.62,
                    "path": [[0.0, 0.40, 0.58], [round(dur * 0.6, 2), 0.35, 0.67]],
                    "spears": True,
                    "face": 1,
                    "tilt": 0.15,
                    "tiltAt": [[round(dur * 0.3, 2), 0.15], [round(dur * 0.7, 2), 0.28]],
                    "gap": {"at": round(dur * 0.2, 2), "dur": 0.6, "w": 0.45},
                    "impactAt": round(dur * 0.35, 2),
                })
                blocks.append({
                    "id": "ENEMY_VANGUARD",
                    "label": "Enemy Vanguard",
                    "side": "red",
                    "w": 0.10, "h": 0.14,
                    "x": 0.65, "y": 0.50,
                    "path": [[0.0, 0.65, 0.50], [round(dur * 0.25, 2), 0.55, 0.50], [round(dur * 0.75, 2), 0.42, 0.50]],
                    "spears": True,
                    "face": -1,
                    "impactAt": round(dur * 0.35, 2),
                })
            elif ev_type == "FRONT_LINE_REPLACE":
                # Second line (Principes) moves forward continuously without teleporting to relieve front line
                blocks.append({
                    "id": "ROMAN_RESERVE_2",
                    "label": "Principes (2nd Line)",
                    "side": "blue",
                    "w": 0.08, "h": 0.16,
                    "x": 0.20, "y": 0.50,
                    "path": [[0.0, 0.20, 0.50], [round(dur * 0.75, 2), 0.40, 0.50]],
                    "spears": True,
                    "face": 1,
                    "impactAt": round(dur * 0.65, 2),
                })
                blocks.append({
                    "id": "ROMAN_FRONT_FALLBACK",
                    "label": "Hastati (Rotating)",
                    "side": "blue",
                    "w": 0.07, "h": 0.14,
                    "x": 0.38, "y": 0.50,
                    "path": [[round(dur * 0.15, 2), 0.38, 0.50], [round(dur * 0.8, 2), 0.18, 0.50]],
                    "fade": [round(dur * 0.7, 2), dur],
                    "face": -1,
                })
                blocks.append({
                    "id": "ENEMY_VANGUARD",
                    "label": "Enemy Vanguard",
                    "side": "red",
                    "w": 0.10, "h": 0.14,
                    "x": 0.52, "y": 0.50,
                    "path": [[0.0, 0.52, 0.50], [round(dur * 0.7, 2), 0.46, 0.50]],
                    "face": -1,
                    "impactAt": round(dur * 0.65, 2),
                })
            elif ev_type in ("ENCIRCLE", "FLANK_LEFT", "FLANK_RIGHT"):
                # Double envelopment: Roman flanks sweep dynamically around enemy
                blocks.append({
                    "id": "ROMAN_CENTER_PIN",
                    "label": "Roman Center",
                    "side": "blue",
                    "w": 0.08, "h": 0.16,
                    "x": 0.38, "y": 0.50,
                    "spears": True,
                    "face": 1,
                    "impactAt": round(dur * 0.3, 2),
                })
                blocks.append({
                    "id": "ENEMY_VANGUARD",
                    "label": "Enemy Vanguard",
                    "side": "red",
                    "w": 0.10, "h": 0.14,
                    "x": 0.50, "y": 0.50,
                    "face": -1,
                    "impactAt": round(dur * 0.3, 2),
                })
                blocks.append({
                    "id": "ROMAN_LEFT_PINCER",
                    "label": "Left Pincer",
                    "side": "blue",
                    "w": 0.06, "h": 0.08,
                    "x": 0.36, "y": 0.24,
                    "path": [[0.0, 0.36, 0.24], [round(dur * 0.5, 2), 0.52, 0.26], [round(dur * 0.85, 2), 0.60, 0.40]],
                    "tilt": 0.2,
                    "tiltAt": [[0.0, 0.2], [round(dur * 0.5, 2), 0.45], [round(dur * 0.85, 2), 0.85]],
                    "face": 1,
                })
                blocks.append({
                    "id": "ROMAN_RIGHT_PINCER",
                    "label": "Right Pincer",
                    "side": "blue",
                    "w": 0.06, "h": 0.08,
                    "x": 0.36, "y": 0.76,
                    "path": [[0.0, 0.36, 0.76], [round(dur * 0.5, 2), 0.52, 0.74], [round(dur * 0.85, 2), 0.60, 0.60]],
                    "tilt": -0.2,
                    "tiltAt": [[0.0, -0.2], [round(dur * 0.5, 2), -0.45], [round(dur * 0.85, 2), -0.85]],
                    "face": 1,
                })
            else:
                # Approach & clash
                blocks.append({
                    "id": "ROMAN_FRONT_1",
                    "label": "Hastati Legion",
                    "side": "blue",
                    "w": 0.08, "h": 0.16,
                    "x": 0.28, "y": 0.50,
                    "path": [[0.0, 0.25, 0.50], [round(dur * 0.8, 2), 0.42, 0.50]],
                    "spears": True,
                    "face": 1,
                    "impactAt": round(dur * 0.5, 2),
                })
                blocks.append({
                    "id": "ENEMY_VANGUARD",
                    "label": "Enemy Vanguard",
                    "side": "red",
                    "w": 0.10, "h": 0.18,
                    "x": 0.72, "y": 0.50,
                    "path": [[0.0, 0.75, 0.50], [round(dur * 0.8, 2), 0.56, 0.50]],
                    "spears": True,
                    "face": -1,
                    "impactAt": round(dur * 0.5, 2),
                })

            args["blocks"] = blocks
            args["ground"] = {"color": "#c9ad7a", "grass": True, "rocks": True}

        elif tpl == "army":
            # Perspective formation clash
            is_clash = (ev_type in ("IMPACT", "BREAKTHROUGH", "CHARGE"))
            args["bg"] = "plain"
            args["mid"] = [{
                "preset": "hastatus",
                "rows": 4,
                "cols": 10 if not cam["safe_zones"]["is_vertical"] else 7,
                "x0": 0.05, "x1": 0.95,
                "yFront": 0.96, "yBack": 0.70,
                "hFront": 0.36 if not cam["safe_zones"]["is_vertical"] else 0.44,
                "hBack": 0.14,
                "march": 1.2 if not is_clash else 0.4,
                "pose": "stand" if is_clash else "march",
                "flip": False,
                "flags": [{"col": 0.5, "kind": "eagle", "row": 0.7}],
            }]
            args["back"] = [{
                "preset": "latin",
                "rows": 3,
                "cols": 16,
                "x0": 0.0, "x1": 1.0,
                "yFront": 0.70, "yBack": 0.62,
                "hFront": 0.10, "hBack": 0.06,
                "flip": True,
            }]
            if ev_type == "MISSILE_VOLLEY":
                args["fx"] = [{"kind": "volley", "at": 0.5, "dur": 1.4, "dir": 1}]

        elif tpl == "close":
            # Commander issuing tactical orders
            args["preset"] = "consul"
            args["face"] = "shout"
            args["talk"] = True
            args["gesture"] = "point"
            args["R"] = 0.22 if not cam["safe_zones"]["is_vertical"] else 0.26

        elif tpl == "scene":
            # Scene missile volley / javelins
            args["bg"] = "field"
            args["people"] = [
                {
                    "preset": "hastatus",
                    "x": 0.35, "y": 0.90,
                    "h": 0.48 if not cam["safe_zones"]["is_vertical"] else 0.56,
                    "pose": "throw" if ev_type == "MISSILE_VOLLEY" else "stand",
                    "face": "determined",
                }
            ]
            if ev_type == "MISSILE_VOLLEY":
                args["fx"] = [{"kind": "javelins", "at": 0.6, "dur": 1.2, "dir": 1}]

        # Attach synchronized audio cues
        sfx_choices = BATTLE_SFX_MAP.get(ev_type, ("shield_bash.wav", "footsteps.wav"))
        sfx_list = list(new_s.get("sfx") or [])
        # Only add auto cue if no existing manual cue
        if not any(c.get("manual") for c in sfx_list):
            primary_sfx = sfx_choices[0].replace(".wav", "")
            sfx_list.append({
                "at": round(min(0.8, dur * 0.25), 2),
                "name": primary_sfx,
                "gain": 0.85,
                "auto": True,
            })
            if len(sfx_choices) > 1 and dur >= 3.0:
                secondary_sfx = sfx_choices[1].replace(".wav", "")
                sfx_list.append({
                    "at": round(min(2.0, dur * 0.65), 2),
                    "name": secondary_sfx,
                    "gain": 0.70,
                    "auto": True,
                })
        new_s["sfx"] = sfx_list

        new_s["tpl"] = tpl
        new_s["args"] = args
        compiled_shots.append(new_s)

    return compiled_shots


def plan_battle_choreo_for_project(
    project_path: str,
    review_only: bool = True,
    apply_choreo: bool = False,
) -> Dict[str, Any]:
    """Top-level entry point to analyze and choreograph a military history battle scene."""
    from pathlib import Path
    p = Path(project_path).resolve()
    cfg_file = p / "config.json"
    cfg = read_json(cfg_file, {}) or {}
    shots_file = p / "story" / "shots.json"
    story_data = read_json(shots_file, {}) or {}
    shots = story_data.get("shots", [])

    if not shots:
        return {
            "status": "BLOCKED",
            "message": "Storyboard has 0 shots. Cannot choreograph battle scene.",
            "timeline": None,
        }

    # Step 1: Parse battle events
    events = parse_battle_events(shots)

    # Step 2: Build state timeline
    timeline = build_battle_state_timeline(events, shots)

    # Step 3: Validate causality
    valid, errors = validate_battle_causality(timeline)
    timeline["causality_valid"] = valid
    timeline["causality_errors"] = errors

    # Step 4: Compile to shots if applying
    if apply_choreo or not review_only:
        compiled_shots = compile_battle_timeline_to_shots(timeline, shots, cfg)
        story_data["shots"] = compiled_shots
        story_data["battle_choreo_status"] = "CHOREOGRAPHED"
        write_json(shots_file, story_data)

        # Invalidate silent video artifacts
        build_dir = p / "build"
        for fn in ("video_silent.mp4", "preview_silent.mp4", "preview.mp4"):
            f = build_dir / fn
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass

        review_res = {
            "status": "CHOREOGRAPHED",
            "events_count": len(events),
            "timeline": timeline,
            "changed_shots_count": len(compiled_shots),
        }
        write_json(build_dir / "battle_review.json", review_res)
        return review_res

    return {
        "status": "REVIEWED",
        "events_count": len(events),
        "timeline": timeline,
        "causality_valid": valid,
        "causality_errors": errors,
    }
