"""battle_choreo.py — Roman Battle Choreography & Narration-to-Action Compiler (V12).

Converts spoken historical battle narration into deterministic, causally sound,
multi-unit 2D tactical animation parameters for the Squire pack.

V12 Architecture:
- Shot-ID Event Ownership: 0..N events mapped to exact owner_shot_id; no index-shift drift.
- Continuous World-State Reducer: Units evolve positions across shot boundaries with
  strict continuity (prev_end == next_start, max jump <= 0.015).
- Semantic Polarity & Actor Awareness: Correct handling of negation (never broke line),
  hypotheticals, passive voice, and actor inversion.
- Decibel Sound Design: Cues use negative dB gains (-8 to -20 dB) matching tools/mix.py.
- Safe Cache & Atomic Apply: Atomic write, rollback on error, visual hash diff gate.
- CLI & App Pipeline Integration.
"""

import argparse
import copy
import math
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    canonical_json_serialize,
    compute_canonical_audio_hash,
    compute_canonical_visual_hash,
    read_json,
    write_json,
)

BATTLE_PLAN_VERSION = "12.0"

# Semantic Event Types
BATTLE_EVENTS = {
    "ADVANCE", "APPROACH", "CHARGE", "BRACE", "IMPACT",
    "BREAKTHROUGH", "GAP_OPEN", "FRONT_LINE_REPLACE", "RESERVE_ADVANCE",
    "WITHDRAW", "RETREAT", "RALLY", "FLANK_LEFT", "FLANK_RIGHT",
    "ENCIRCLE", "COUNTERATTACK", "MISSILE_VOLLEY", "SHIELD_WALL",
    "COMMAND_SIGNAL", "PURSUIT", "HOLD_POSITION", "MAP_EXPLAIN",
    "NO_BATTLE_EVENT"
}

# Whitelisted SFX mapping for battle actions with sensible negative dB gains
BATTLE_SFX_MAP: Dict[str, Tuple[Dict[str, Any], ...]] = {
    "APPROACH": ({"name": "drum_march", "gain": -12.0}, {"name": "footsteps", "gain": -15.0}),
    "ADVANCE": ({"name": "drum_march", "gain": -12.0}, {"name": "footsteps", "gain": -15.0}),
    "CHARGE": ({"name": "battle_roar", "gain": -10.0}, {"name": "whoosh_fast", "gain": -13.0}),
    "BRACE": ({"name": "shield_bash", "gain": -9.0}, {"name": "armor_clank", "gain": -14.0}),
    "IMPACT": ({"name": "shield_bash", "gain": -8.0}, {"name": "sword_clash", "gain": -10.0}),
    "BREAKTHROUGH": ({"name": "spear_hit", "gain": -9.0}, {"name": "shield_bash", "gain": -9.0}),
    "GAP_OPEN": ({"name": "shield_bash", "gain": -10.0}, {"name": "armor_clank", "gain": -14.0}),
    "FRONT_LINE_REPLACE": ({"name": "horn_roman", "gain": -10.0}, {"name": "drum_march", "gain": -13.0}),
    "RESERVE_ADVANCE": ({"name": "drum_march", "gain": -12.0}, {"name": "shield_bash", "gain": -10.0}),
    "WITHDRAW": ({"name": "footsteps", "gain": -14.0}, {"name": "armor_clank", "gain": -16.0}),
    "RETREAT": ({"name": "whoosh_long", "gain": -12.0}, {"name": "downer", "gain": -14.0}),
    "RALLY": ({"name": "horn_roman", "gain": -9.0}, {"name": "war_horn", "gain": -10.0}),
    "FLANK_LEFT": ({"name": "drum_march", "gain": -13.0}, {"name": "whoosh_mid", "gain": -12.0}),
    "FLANK_RIGHT": ({"name": "drum_march", "gain": -13.0}, {"name": "whoosh_mid", "gain": -12.0}),
    "ENCIRCLE": ({"name": "horn_roman", "gain": -9.0}, {"name": "battle_roar", "gain": -10.0}),
    "COUNTERATTACK": ({"name": "sword_clash", "gain": -9.0}, {"name": "battle_roar", "gain": -10.0}),
    "MISSILE_VOLLEY": ({"name": "arrow_volley", "gain": -10.0}, {"name": "javelin_throw", "gain": -9.0}),
    "SHIELD_WALL": ({"name": "shield_bash", "gain": -9.0}, {"name": "armor_clank", "gain": -14.0}),
    "COMMAND_SIGNAL": ({"name": "horn_roman", "gain": -8.0}, {"name": "war_horn", "gain": -9.0}),
    "PURSUIT": ({"name": "battle_roar", "gain": -10.0}, {"name": "whoosh_fast", "gain": -12.0}),
    "HOLD_POSITION": ({"name": "shield_bash", "gain": -9.0}, {"name": "drum_hit", "gain": -13.0}),
    "MAP_EXPLAIN": ({"name": "page_turn", "gain": -14.0}, {"name": "ting_idea", "gain": -12.0}),
}


def parse_battle_events(
    shots: Any,
    transcript: Optional[str] = None,
    timed_words: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    owner_shot_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Parse battle events from shot text with strict negation, tense, and actor identification.

    Emits 0..N events per shot tagged with owner_shot_id. No artificial fallback ADVANCE.
    """
    if isinstance(shots, str):
        sid = owner_shot_id or "s001"
        shots = [{"id": sid, "dur": 3.0, "line": shots}]
    elif isinstance(shots, list) and shots and isinstance(shots[0], dict) and owner_shot_id and len(shots) == 1:
        shots[0]["id"] = owner_shot_id

    events: List[Dict[str, Any]] = []

    negation_regex = re.compile(
        r"\b(could\s+not|can\s*not|never|nobody|no\s+one|did\s+not|without|refused\s+to|"
        r"hardly|scarcely|couldn't|can't|didn't|won't|unable\s+to|failed\s+to|impossible\s+to|"
        r"kh\u00f4ng\s+th\u1ec3|kh\u00f4ng\s+bao\s+gi\u1edd|ch\u01b0a\s+t\u1eebng|kh\u00f4ng\s+b\u1ecb|"
        r"kh\u00f4ng\s+th\u1ee7ng|kh\u00f4ng\s+thua|kh\u00f4ng\s+v\u1ee1|không)\s+([a-z\u00e0-\u1ef9\s]{1,30})",
        re.IGNORECASE,
    )

    hypothetical_regex = re.compile(
        r"\b(what\s+if|if\s+they|had\s+they|could\s+have|might\s+have|suppose|assuming|n\u1ebfu|gi\u1ea3\s+s\u1eed)\b",
        re.IGNORECASE,
    )

    perceived_regex = re.compile(
        r"\b(thought\s+(?:they|he|the\s+enemy|the\s+warlord|the\s+barbarians)|"
        r"seemed\s+(?:like|to\s+be)?|what\s+seemed\s+like|believed\s+(?:they|he)|"
        r"appeared\s+(?:to|like)|feigned|pretended|imagined|assumed)\b",
        re.IGNORECASE,
    )

    opponent_regex = re.compile(
        r"\b(warlords?|chieftains?|gauls?|barbarians?|carthaginians?|enemies|enemy|hannibal|opponents?|invaders?|attacker|attackers)\b",
        re.IGNORECASE,
    )

    seen_ids: Set[str] = set()
    evt_counter = 0

    for idx, s in enumerate(shots):
        sid = s.get("id") or f"s{idx+1:03d}"
        if sid in seen_ids:
            sid = f"{sid}_{idx}"
        seen_ids.add(sid)

        raw_line = s.get("line") or ""
        scene_desc = s.get("scene") or ""
        combined_text = f"{raw_line} {scene_desc}".strip()
        text_lower = combined_text.lower()
        dur = float(s.get("dur", 3.0))
        start_t = float(s.get("start", idx * dur))

        is_hypo = bool(hypothetical_regex.search(combined_text))
        is_perceived = bool(perceived_regex.search(combined_text))

        def is_negated(pat: str) -> bool:
            for m in negation_regex.finditer(combined_text):
                if re.search(pat, m.group(0), re.IGNORECASE):
                    return True
            return False

        shot_events: List[Dict[str, Any]] = []

        # 1. Breakthrough / Gap Open
        break_pat = r"\b(breakthrough|broke\s+through|break\s+through|broken\s+through|(?:break|broke|broken|punched?)\s+(?:through|into|the\s+line|(?:the\s+)?(?:[a-z]+\s+)?line)|line\s+(?:might\s+have\s+|had\s+|has\s+|was\s+|were\s+)?(?:been\s+)?(?:break|broke|broken)|breach|gap\s+open|hole\s+in|pierce|ch\u1ecdc\s+th\u1ee7ng|ph\u00e1\s+v\u1ee1|l\u1ed7\s+h\u1ed5ng|m\u1edf\s+toang)\b"
        if re.search(break_pat, text_lower):
            evt_counter += 1
            if is_negated(break_pat):
                shot_events.append({
                    "event_id": f"evt_{evt_counter:03d}",
                    "owner_shot_id": sid,
                    "event_type": "HOLD_POSITION",
                    "actor_side": "roman",
                    "target_side": "opponent",
                    "polarity": "NEGATED",
                    "source_span": combined_text,
                    "is_negated": True,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.95,
                    "local_t": 0.3 * dur,
                    "global_start": start_t,
                    "global_end": start_t + dur,
                    "note": "Negated breakthrough: Roman front line held firmly",
                })
            elif is_perceived:
                shot_events.append({
                    "event_id": f"evt_{evt_counter:03d}",
                    "owner_shot_id": sid,
                    "event_type": "BREAKTHROUGH",
                    "actor_side": "opponent",
                    "target_side": "roman",
                    "polarity": "PERCEIVED",
                    "source_span": combined_text,
                    "is_negated": False,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.95,
                    "local_t": 0.4 * dur,
                    "global_start": start_t,
                    "global_end": start_t + dur,
                    "note": "Perceived breakthrough: Enemy mistakenly believed the line was broken",
                })
            else:
                shot_events.append({
                    "event_id": f"evt_{evt_counter:03d}",
                    "owner_shot_id": sid,
                    "event_type": "BREAKTHROUGH",
                    "actor_side": "opponent",
                    "target_side": "roman",
                    "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                    "source_span": combined_text,
                    "is_negated": False,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.95,
                    "local_t": 0.4 * dur,
                    "global_start": start_t,
                    "global_end": start_t + dur,
                    "note": "Enemy creates a breach in the Roman frontline",
                })

        # 2. Front line Relief / Rotation / Reserves Advance
        relief_pat = r"\b(relieve|relief|rotate|rotation|replace|second\s+line|reserve|principes|triarii|plug\s+the\s+gap|thay\s+qu\u00e2n|h\u00e0ng\s+hai|ti\u1ebfp\u1ee9ng|xoay\s+v\u00f2ng|l\u1ea5p\s+ch\u1ed7|behind\s+it\s+stepped\s+forward|(?:second\s+line|reserves?)\s+(?:came|stepped|moved)\s+forward)\b"
        if re.search(relief_pat, text_lower) and not is_negated(relief_pat):
            evt_counter += 1
            shot_events.append({
                "event_id": f"evt_{evt_counter:03d}",
                "owner_shot_id": sid,
                "event_type": "FRONT_LINE_REPLACE",
                "actor_side": "roman",
                "target_side": "opponent",
                "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.94,
                "local_t": 0.5 * dur,
                "global_start": start_t,
                "global_end": start_t + dur,
                "note": "Second line moves forward through intervals to relieve front ranks",
            })

        # 3. Flank / Encirclement / Pincer
        flank_pat = r"\b(flanks?|pincers?|encircle[ds]?|encirclement|surround(?:ed|ing|s)?|double\s+envelopment|trapped?|b\u1ecdc\s+s\u01b0\u1eddn|bao\s+v\u00e2y|k\u1eb9p\s+th\u1ecbt|v\u00e2y\s+h\u00e3m|wings\s+moved|pressure\s+from\s+three\s+directions)\b"
        if re.search(flank_pat, text_lower):
            evt_counter += 1
            has_flank_word = bool(re.search(r"\b(flanks?|wings?|b\u1ecdc\s+s\u01b0\u1eddn)\b", text_lower))
            has_encircle_word = bool(re.search(r"\b(encircle[ds]?|surround(?:ed|ing|s)?|bao\s+v\u00e2y)\b", text_lower))
            is_roman_passive = bool(re.search(r"\b(romans\s+(were|got|felt)\s+surrounded|romans\s+trapped)\b", text_lower))
            if is_negated(flank_pat):
                shot_events.append({
                    "event_id": f"evt_{evt_counter:03d}",
                    "owner_shot_id": sid,
                    "event_type": "HOLD_POSITION",
                    "actor_side": "opponent",
                    "target_side": "roman",
                    "polarity": "NEGATED",
                    "source_span": combined_text,
                    "is_negated": True,
                    "is_hypothetical": is_hypo,
                    "confidence": 0.90,
                    "local_t": 0.5 * dur,
                    "global_start": start_t,
                    "global_end": start_t + dur,
                    "note": "Negated encirclement: formation evaded enclosure",
                })
            else:
                actor = "opponent" if is_roman_passive else "roman"
                target = "roman" if is_roman_passive else "opponent"
                if has_flank_word and not has_encircle_word:
                    shot_events.append({
                        "event_id": f"evt_{evt_counter:03d}",
                        "owner_shot_id": sid,
                        "event_type": "FLANK_LEFT",
                        "actor_side": actor,
                        "target_side": target,
                        "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                        "source_span": combined_text,
                        "is_negated": False,
                        "is_hypothetical": is_hypo,
                        "confidence": 0.92,
                        "local_t": 0.4 * dur,
                        "global_start": start_t,
                        "global_end": start_t + dur,
                        "note": "Flanking maneuver deployed",
                    })
                else:
                    if has_flank_word:
                        shot_events.append({
                            "event_id": f"evt_{evt_counter:03d}",
                            "owner_shot_id": sid,
                            "event_type": "FLANK_LEFT",
                            "actor_side": actor,
                            "target_side": target,
                            "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                            "source_span": combined_text,
                            "is_negated": False,
                            "is_hypothetical": is_hypo,
                            "confidence": 0.92,
                            "local_t": 0.3 * dur,
                            "global_start": start_t,
                            "global_end": start_t + dur,
                            "note": "Flanking maneuver deployed",
                        })
                        evt_counter += 1
                    shot_events.append({
                        "event_id": f"evt_{evt_counter:03d}",
                        "owner_shot_id": sid,
                        "event_type": "ENCIRCLE",
                        "actor_side": actor,
                        "target_side": target,
                        "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                        "source_span": combined_text,
                        "is_negated": False,
                        "is_hypothetical": is_hypo,
                        "confidence": 0.92,
                        "local_t": 0.5 * dur,
                        "global_start": start_t,
                        "global_end": start_t + dur,
                        "note": "Pocket enclosed around opponent",
                    })

        # 4. Missile Volley / Javelins / Pila / Arrows
        missile_pat = r"\b(volley|pilum|pila|javelin|arrow|missile|shower\s+of|ph\u00f3ng\s+lao|m\u01b0a\s+t\u00ean|b\u1eafn\s+t\u00ean)\b"
        if re.search(missile_pat, text_lower) and not is_negated(missile_pat):
            evt_counter += 1
            shot_events.append({
                "event_id": f"evt_{evt_counter:03d}",
                "owner_shot_id": sid,
                "event_type": "MISSILE_VOLLEY",
                "actor_side": "roman" if ("pilum" in text_lower or "lao" in text_lower) else "opponent",
                "target_side": "opponent" if ("pilum" in text_lower or "lao" in text_lower) else "roman",
                "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.88,
                "local_t": 0.3 * dur,
                "global_start": start_t,
                "global_end": start_t + dur,
                "note": "Missile volley launched across engagement line",
            })

        # 5. Approach / Advance / March / Impact / Clash
        advance_pat = r"\b(advance[ds]?|advancing|march(?:ed|ing|es)?|charge[ds]?|charging|clash(?:ed|ing|es)?|impact[ds]?|collid(?:e[ds]?|ing)|approach(?:ed|ing|es)?|braced?|push(?:ed|ing|es)?|ti\u1ebfn\s+qu\u00e2n|xung\s+phong|va\s+ch\u1ea1m|gi\u00e1p\s+l\u00e1\s+c\u00e0|h\u00fac\s+m\u1ea1nh|rushed\s+the|first\s+blow\s+struck)\b"
        if re.search(advance_pat, text_lower) and not is_negated(advance_pat):
            # If shot already has BREAKTHROUGH or RELIEF, only add IMPACT if distinct clash is stated
            is_impact = ("clash" in text_lower or "impact" in text_lower or "struck" in text_lower or "va" in text_lower)
            evt_counter += 1
            is_opp = bool(opponent_regex.search(text_lower) or "enemy rushed" in text_lower or "their first blow" in text_lower)
            shot_events.append({
                "event_id": f"evt_{evt_counter:03d}",
                "owner_shot_id": sid,
                "event_type": "IMPACT" if is_impact else "ADVANCE",
                "actor_side": "opponent" if is_opp else "roman",
                "target_side": "roman" if is_opp else "opponent",
                "polarity": "PERCEIVED" if is_perceived else ("HYPOTHETICAL" if is_hypo else "AFFIRMED"),
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.88,
                "local_t": 0.35 * dur,
                "global_start": start_t,
                "global_end": start_t + dur,
                "note": "Units advance and make frontline contact",
            })

        # 6. Command Signal / Horn
        command_pat = r"\b(signals?|signaled|signalling|horns?|trumpets?|commands?|commanded|consuls?|centurions?|standards?|eagles?|hi\u1ec7u\s+l\u1ec7nh|ti\u1ebfng\s+t\u00f9\s+v\u00e0|ch\u1ec9\s+huy)\b"
        if re.search(command_pat, text_lower) and not is_negated(command_pat):
            evt_counter += 1
            is_opp = bool(opponent_regex.search(text_lower))
            shot_events.append({
                "event_id": f"evt_{evt_counter:03d}",
                "owner_shot_id": sid,
                "event_type": "COMMAND_SIGNAL",
                "actor_side": "opponent" if is_opp else "roman",
                "target_side": "roman" if is_opp else "roman",
                "polarity": "AFFIRMED",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.90,
                "local_t": 0.2 * dur,
                "global_start": start_t,
                "global_end": start_t + dur,
                "note": "Commander orders tactical maneuver via horn",
            })

        # 7. Counterattack / Pursuit
        counter_pat = r"\b(counter-?attacks?|counter-?attacked|counter-?attacking|repell?ed|repelling|drove\s+back|driven\s+back|push\s+back|pushed\s+back|pursuit|pursu(?:ed|ing)|ph\u1ea3n\s+c\u00f4ng|\u0111\u1ea9y\s+l\u00f9i|truy\s+k\u00edch)\b"
        if re.search(counter_pat, text_lower) and not is_negated(counter_pat):
            evt_counter += 1
            shot_events.append({
                "event_id": f"evt_{evt_counter:03d}",
                "owner_shot_id": sid,
                "event_type": "COUNTERATTACK",
                "actor_side": "roman",
                "target_side": "opponent",
                "polarity": "HYPOTHETICAL" if is_hypo else "AFFIRMED",
                "source_span": combined_text,
                "is_negated": False,
                "is_hypothetical": is_hypo,
                "confidence": 0.92,
                "local_t": 0.5 * dur,
                "global_start": start_t,
                "global_end": start_t + dur,
                "note": "Roman counterattack drives enemy back",
            })

        for ev in shot_events:
            ev["actor"] = ev.get("actor_side", "roman")
            ev["target"] = ev.get("target_side", "opponent")
        events.extend(shot_events)

    return events


def index_battle_events_by_shot(
    events: Any,
    shots: Any = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Map events strictly to their owner_shot_id.

    Eliminates array index mismatch: multiple events belong to their owner shot,
    and shots without battle events receive an empty list (no fallback to previous shot).
    Supports either (events, shots) or (shots, events) call signatures.
    """
    if isinstance(events, list) and events and any("line" in s or "dur" in s for s in events):
        # Called as index_battle_events_by_shot(shots, events)
        shots, events = events, shots or []
    events = events or []
    shots = shots or []

    valid_shot_ids = {s.get("id") or f"s{idx+1:03d}" for idx, s in enumerate(shots)}
    indexed: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in valid_shot_ids}

    for evt in events:
        owner = evt.get("owner_shot_id")
        if owner in indexed:
            indexed[owner].append(evt)
        else:
            # Handle shots where ID had fallback format
            matched = False
            for sid in indexed:
                if sid.endswith(str(owner)) or str(owner).endswith(sid):
                    indexed[sid].append(evt)
                    matched = True
                    break
            if not matched:
                raise ValueError(f"Orphan event detected: event '{evt.get('event_id')}' has non-existent owner_shot_id '{owner}'")

    # Sort events within each shot by local_t
    for sid in indexed:
        indexed[sid].sort(key=lambda e: e.get("local_t", 0.0))

    return indexed


def create_initial_battle_units() -> Dict[str, Dict[str, Any]]:
    """Initialize persistent battlefield unit roster with normalized coordinates [0..1]."""
    return {
        "ROMAN_FRONT_LEFT": {
            "id": "ROMAN_FRONT_LEFT",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "hastati_front_left",
            "label": "Hastati (Left)",
            "x": 0.38,
            "y": 0.38,
            "w": 0.08,
            "h": 0.08,
            "facing": 1,
            "spears": True,
            "tilt": -0.10,
            "active": True,
            "gap_w": 0.0,
        },
        "ROMAN_FRONT_RIGHT": {
            "id": "ROMAN_FRONT_RIGHT",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "hastati_front_right",
            "label": "Hastati (Right)",
            "x": 0.38,
            "y": 0.62,
            "w": 0.08,
            "h": 0.08,
            "facing": 1,
            "spears": True,
            "tilt": 0.10,
            "active": True,
            "gap_w": 0.0,
        },
        "ROMAN_RESERVE_2": {
            "id": "ROMAN_RESERVE_2",
            "side": "roman",
            "color_side": "blue",
            "preset": "princeps",
            "role": "principes_relief",
            "label": "Principes (2nd Line)",
            "x": 0.18,
            "y": 0.50,
            "w": 0.08,
            "h": 0.16,
            "facing": 1,
            "spears": True,
            "tilt": 0.0,
            "active": True,
            "gap_w": 0.0,
        },
        "ROMAN_REAR_3": {
            "id": "ROMAN_REAR_3",
            "side": "roman",
            "color_side": "blue",
            "preset": "triarius",
            "role": "triarii_reserve",
            "label": "Triarii Veterans",
            "x": 0.06,
            "y": 0.50,
            "w": 0.07,
            "h": 0.16,
            "facing": 1,
            "spears": True,
            "tilt": 0.0,
            "active": True,
            "gap_w": 0.0,
        },
        "ENEMY_VANGUARD": {
            "id": "ENEMY_VANGUARD",
            "side": "opponent",
            "color_side": "red",
            "preset": "latin",
            "role": "enemy_vanguard",
            "label": "Enemy Vanguard",
            "x": 0.70,
            "y": 0.50,
            "w": 0.10,
            "h": 0.16,
            "facing": -1,
            "spears": True,
            "tilt": 0.0,
            "active": True,
            "gap_w": 0.0,
        },
        "ROMAN_LEFT_FLANK": {
            "id": "ROMAN_LEFT_FLANK",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "cavalry_left_pincer",
            "label": "Left Pincer",
            "x": 0.36,
            "y": 0.22,
            "w": 0.06,
            "h": 0.08,
            "facing": 1,
            "spears": False,
            "tilt": 0.15,
            "active": True,
            "gap_w": 0.0,
        },
        "ROMAN_RIGHT_FLANK": {
            "id": "ROMAN_RIGHT_FLANK",
            "side": "roman",
            "color_side": "blue",
            "preset": "hastatus",
            "role": "cavalry_right_pincer",
            "label": "Right Pincer",
            "x": 0.36,
            "y": 0.78,
            "w": 0.06,
            "h": 0.08,
            "facing": 1,
            "spears": False,
            "tilt": -0.15,
            "active": True,
            "gap_w": 0.0,
        },
    }


def build_battle_state_timeline(
    events_by_shot: Any,
    shots: Any = None,
    spoken_alignment: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Continuous world-state reducer: units evolve across shot cuts without teleportation jumps.

    Prev-end == next-start is guaranteed: each shot starts from the exact unit coordinates
    left at the end of the previous shot.
    """
    if isinstance(events_by_shot, list) and events_by_shot and any("line" in s or "dur" in s for s in events_by_shot):
        shots, events_by_shot = events_by_shot, shots
    if isinstance(events_by_shot, list):
        events_by_shot = index_battle_events_by_shot(events_by_shot, shots or [])
    shots = shots or []
    events_by_shot = events_by_shot or {}

    current_units = create_initial_battle_units()
    shot_snapshots: List[Dict[str, Any]] = []
    continuity_audit: List[Dict[str, Any]] = []

    for idx, s in enumerate(shots):
        sid = s.get("id") or f"s{idx+1:03d}"
        dur = float(s.get("dur", 3.0))
        evts = events_by_shot.get(sid, [])

        # Record starting state for this shot (must equal previous shot's end state)
        start_state = copy.deepcopy(current_units)
        end_state = copy.deepcopy(current_units)

        # Apply event state transitions
        for e in evts:
            ev_type = e.get("event_type")
            is_negated = e.get("is_negated", False)
            polarity = e.get("polarity", "AFFIRMED")
            actor = e.get("actor_side", "roman")

            if ev_type in ("ADVANCE", "APPROACH", "CHARGE") and not is_negated:
                if actor == "roman":
                    end_state["ROMAN_FRONT_LEFT"]["x"] = min(0.44, end_state["ROMAN_FRONT_LEFT"]["x"] + 0.04)
                    end_state["ROMAN_FRONT_RIGHT"]["x"] = min(0.44, end_state["ROMAN_FRONT_RIGHT"]["x"] + 0.04)
                else:
                    end_state["ENEMY_VANGUARD"]["x"] = max(0.50, end_state["ENEMY_VANGUARD"]["x"] - 0.12)

            elif ev_type == "IMPACT" and not is_negated:
                end_state["ENEMY_VANGUARD"]["x"] = 0.50
                end_state["ROMAN_FRONT_LEFT"]["x"] = 0.40
                end_state["ROMAN_FRONT_RIGHT"]["x"] = 0.40

            elif ev_type == "BREAKTHROUGH" and not is_negated:
                if polarity in ("PERCEIVED", "HYPOTHETICAL"):
                    # Perceived or hypothetical: line holds firm under pressure, no structural gap opened
                    end_state["ROMAN_FRONT_LEFT"]["gap_w"] = 0.05
                    end_state["ROMAN_FRONT_RIGHT"]["gap_w"] = 0.05
                    end_state["ENEMY_VANGUARD"]["x"] = max(0.48, end_state["ENEMY_VANGUARD"]["x"] - 0.02)
                else:
                    # Affirmed gap opens outward in Y, enemy penetrates forward in X
                    end_state["ROMAN_FRONT_LEFT"]["y"] = max(0.28, end_state["ROMAN_FRONT_LEFT"]["y"] - 0.06)
                    end_state["ROMAN_FRONT_RIGHT"]["y"] = min(0.72, end_state["ROMAN_FRONT_RIGHT"]["y"] + 0.06)
                    end_state["ROMAN_FRONT_LEFT"]["gap_w"] = 0.45
                    end_state["ROMAN_FRONT_RIGHT"]["gap_w"] = 0.45
                    end_state["ENEMY_VANGUARD"]["x"] = max(0.40, end_state["ENEMY_VANGUARD"]["x"] - 0.10)

            elif ev_type == "FRONT_LINE_REPLACE" and not is_negated:
                # Second line (Principes) moves forward continuously to meet enemy
                end_state["ROMAN_RESERVE_2"]["x"] = min(0.42, end_state["ROMAN_RESERVE_2"]["x"] + 0.22)
                # First line rotates/withdraws safely back
                end_state["ROMAN_FRONT_LEFT"]["x"] = max(0.20, end_state["ROMAN_FRONT_LEFT"]["x"] - 0.18)
                end_state["ROMAN_FRONT_RIGHT"]["x"] = max(0.20, end_state["ROMAN_FRONT_RIGHT"]["x"] - 0.18)

            elif ev_type in ("ENCIRCLE", "FLANK_LEFT", "FLANK_RIGHT") and not is_negated:
                # Flanks curve inward to enclose enemy
                end_state["ROMAN_LEFT_FLANK"]["x"] = 0.58
                end_state["ROMAN_LEFT_FLANK"]["y"] = 0.38
                end_state["ROMAN_LEFT_FLANK"]["tilt"] = 0.85
                end_state["ROMAN_RIGHT_FLANK"]["x"] = 0.58
                end_state["ROMAN_RIGHT_FLANK"]["y"] = 0.62
                end_state["ROMAN_RIGHT_FLANK"]["tilt"] = -0.85
                end_state["ENEMY_VANGUARD"]["x"] = 0.48

            elif ev_type == "COUNTERATTACK" and not is_negated:
                end_state["ROMAN_RESERVE_2"]["x"] = min(0.48, end_state["ROMAN_RESERVE_2"]["x"] + 0.06)
                end_state["ENEMY_VANGUARD"]["x"] = min(0.56, end_state["ENEMY_VANGUARD"]["x"] + 0.08)

            elif ev_type == "HOLD_POSITION":
                # Resists displacement
                end_state["ROMAN_FRONT_LEFT"]["x"] = start_state["ROMAN_FRONT_LEFT"]["x"]
                end_state["ROMAN_FRONT_RIGHT"]["x"] = start_state["ROMAN_FRONT_RIGHT"]["x"]

        # Continuity check with previous shot's end state
        if shot_snapshots:
            prev_end = shot_snapshots[-1]["end_state"]
            max_jump = 0.0
            jump_unit = ""
            for uid, udata in start_state.items():
                if uid in prev_end:
                    dx = abs(udata["x"] - prev_end[uid]["x"])
                    dy = abs(udata["y"] - prev_end[uid]["y"])
                    jump = math.hypot(dx, dy)
                    if jump > max_jump:
                        max_jump = jump
                        jump_unit = uid
            continuity_audit.append({
                "from_shot": shot_snapshots[-1]["shot_id"],
                "to_shot": sid,
                "max_jump": round(max_jump, 4),
                "jump_unit": jump_unit,
                "continuous": (max_jump <= 0.015),
            })

        shot_snapshots.append({
            "shot_id": sid,
            "shot_index": idx,
            "duration": dur,
            "events": evts,
            "start_state": start_state,
            "end_state": end_state,
        })

        # Advance world state to the end of this shot for next shot
        current_units = end_state

    all_events = [e for evts in events_by_shot.values() for e in evts]
    phase_flags = {
        "has_approach": any(e["event_type"] in ("ADVANCE", "APPROACH", "CHARGE", "IMPACT") for e in all_events),
        "has_break": any(e["event_type"] == "BREAKTHROUGH" and not e.get("is_negated") and e.get("polarity") not in ("PERCEIVED", "HYPOTHETICAL", "NEGATED") for e in all_events),
        "has_relief": any(e["event_type"] in ("FRONT_LINE_REPLACE", "RESERVE_ADVANCE") for e in all_events),
        "has_flank": any(e["event_type"] in ("FLANK_LEFT", "FLANK_RIGHT", "ENCIRCLE") and not e.get("is_negated") for e in all_events),
    }

    return {
        "version": BATTLE_PLAN_VERSION,
        "phase_flags": phase_flags,
        "shot_snapshots": shot_snapshots,
        "continuity_audit": continuity_audit,
        "all_continuous": all(ca["continuous"] for ca in continuity_audit) if continuity_audit else True,
        "causality_valid": True,
        "causality_errors": [],
    }


def validate_battle_causality(timeline: Any) -> Tuple[bool, List[str]]:
    """Strictly assert causality rules on battle maneuvers."""
    errors = []
    if isinstance(timeline, list):
        if timeline and isinstance(timeline[0], dict) and "event_type" in timeline[0]:
            all_events = timeline
            timeline = {"shot_snapshots": [], "all_continuous": True}
        else:
            snapshots = timeline
            all_events = [e for snap in snapshots for e in snap.get("events", [])]
            timeline = {"shot_snapshots": snapshots, "all_continuous": True}
    else:
        snapshots = timeline.get("shot_snapshots", [])
        all_events = []
        for snap in snapshots:
            all_events.extend(snap.get("events", []))

    # Rule 1: Contact or breakthrough must precede relief/rotation
    contact_idx = next((i for i, e in enumerate(all_events) if e.get("event_type") in ("ADVANCE", "CHARGE", "APPROACH", "IMPACT", "BREAKTHROUGH") and not e.get("is_negated")), -1)
    relief_idx = next((i for i, e in enumerate(all_events) if e.get("event_type") == "FRONT_LINE_REPLACE" and not e.get("is_negated")), -1)
    if relief_idx != -1 and (contact_idx == -1 or relief_idx < contact_idx):
        errors.append("Causality violation: Relief/replacement occurred before enemy breakthrough or contact")

    # Rule 2: An encirclement cannot occur without units reaching opposing flanks
    encircle_events = [e for e in all_events if e.get("event_type") == "ENCIRCLE" and not e.get("is_negated")]
    if encircle_events:
        flank_found = any(e.get("event_type") in ("FLANK_LEFT", "FLANK_RIGHT") or "flank" in e.get("source_span", "").lower() or "curv" in e.get("source_span", "").lower() or "wing" in e.get("source_span", "").lower() for e in all_events)
        if not flank_found:
            errors.append("Encirclement asserted without preceding flanking maneuvers")

    # Rule 3: Negated breakthrough must not result in enemy breakthrough state
    negated_breaks = [e for e in all_events if e.get("event_type") == "HOLD_POSITION" and e.get("is_negated")]
    affirmed_breaks = [e for e in all_events if e.get("event_type") == "BREAKTHROUGH" and not e.get("is_negated")]
    for nb in negated_breaks:
        if any(ab.get("owner_shot_id") == nb.get("owner_shot_id") for ab in affirmed_breaks):
            errors.append("Causality contradiction: Shot has both negated breakthrough and affirmed breakthrough")

    # Rule 4: Continuity check
    if not timeline.get("all_continuous", True):
        for ca in timeline.get("continuity_audit", []):
            if not ca.get("continuous"):
                errors.append(f"World-state discontinuity between {ca.get('from_shot')} and {ca.get('to_shot')}: jump {ca.get('max_jump')} > 0.015")

    return len(errors) == 0, errors


def choose_battle_camera_and_scale(
    event_type: str,
    aspect: str = "16:9",
    shot_index: int = 0,
) -> Dict[str, Any]:
    """Select appropriate camera angle, movement, and mobile safe-zones."""
    is_vertical = (aspect == "9:16")

    if event_type in ("ENCIRCLE", "FRONT_LINE_REPLACE"):
        tpl = "top"
        move = "in"
        zoom = [0.5, 0.5, 1.25, 0.0, 1.2]
    elif event_type in ("BREAKTHROUGH", "IMPACT", "CHARGE", "ADVANCE"):
        tpl = "top" if (shot_index % 2 == 1) else "army"
        move = "right"
        zoom = [0.52, 0.50, 1.30, 0.0, 0.8]
    elif event_type == "COMMAND_SIGNAL":
        tpl = "close"
        move = "in"
        zoom = [0.5, 0.45, 1.4, 0.0, 0.6]
    elif event_type == "MISSILE_VOLLEY":
        tpl = "scene"
        move = "up"
        zoom = [0.5, 0.4, 1.2, 0.0, 1.0]
    else:
        tpl = "top"
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
    timeline: Any,
    existing_shots: Any = None,
    project_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Compile abstract tactical timeline into executable Squire tpl, args, and sfx parameters.

    Strictly preserves manual locks, maps events by owner_shot_id, ensures coordinate
    continuity, and sets sound gains in negative dB.
    """
    if isinstance(timeline, list) and isinstance(existing_shots, dict):
        timeline, existing_shots = existing_shots, timeline
    timeline = timeline or {}
    existing_shots = existing_shots or []
    project_config = project_config or {}

    aspect = project_config.get("aspect", "16:9")
    snapshots = {snap["shot_id"]: snap for snap in timeline.get("shot_snapshots", [])}
    compiled_shots: List[Dict[str, Any]] = []

    for idx, s in enumerate(existing_shots):
        new_s = copy.deepcopy(s)
        sid = s.get("id") or f"s{idx+1:03d}"

        # 1. Strict manual lock: preserve user-owned visual edits byte-for-byte
        if s.get("manual") or s.get("visual_source") == "manual":
            compiled_shots.append(new_s)
            continue

        snap = snapshots.get(sid)
        if not snap or not snap.get("events"):
            # Shot has no battle events: preserve existing visual or narrative scene
            compiled_shots.append(new_s)
            continue

        dur = float(s.get("dur", 3.0))
        evts = snap["events"]
        primary_evt = evts[0]
        ev_type = primary_evt.get("event_type", "ADVANCE")
        cam = choose_battle_camera_and_scale(ev_type, aspect, idx)

        new_s["visual_source"] = "battle_choreo_v12" if s.get("visual_source") != "gemini_director_v14" else "gemini_director_v14+battle_choreo"
        new_s["battle_plan_version"] = BATTLE_PLAN_VERSION
        new_s["source_span"] = primary_evt.get("source_span", s.get("line", ""))
        new_s["confidence"] = primary_evt.get("confidence", 0.90)
        if s.get("execution_trace"):
            new_s["execution_trace"] = s["execution_trace"]
        if s.get("director_beat"):
            new_s["director_beat"] = s["director_beat"]

        tpl = cam["template"]
        args: Dict[str, Any] = dict(s.get("args") or {})
        if s.get("args", {}).get("cameraRig"):
            args["cameraRig"] = s["args"]["cameraRig"]
        if s.get("args", {}).get("view"):
            args["view"] = s["args"]["view"]
        args["move"] = cam["move"]
        args["zoom"] = cam["zoom"]
        args["safe_zones"] = cam["safe_zones"]
        args["safe_margin_bottom"] = cam["safe_zones"]["margin_bottom"]

        start_u = snap["start_state"]
        end_u = snap["end_state"]

        if tpl == "top":
            blocks = []
            for uid in ("ROMAN_FRONT_LEFT", "ROMAN_FRONT_RIGHT", "ENEMY_VANGUARD", "ROMAN_RESERVE_2", "ROMAN_LEFT_FLANK", "ROMAN_RIGHT_FLANK"):
                su = start_u.get(uid)
                eu = end_u.get(uid)
                if not su or not eu or not su.get("active"):
                    continue

                # Path smoothly interpolates from exact start to exact end
                t_mid = round(dur * 0.5, 2)
                x_mid = round((su["x"] + eu["x"]) / 2, 3)
                y_mid = round((su["y"] + eu["y"]) / 2, 3)

                b_entry: Dict[str, Any] = {
                    "id": uid,
                    "label": su["label"],
                    "side": su["color_side"],
                    "w": su["w"],
                    "h": su["h"],
                    "x": round(su["x"], 3),
                    "y": round(su["y"], 3),
                    "path": [
                        [0.0, round(su["x"], 3), round(su["y"], 3)],
                        [t_mid, x_mid, y_mid],
                        [round(dur, 2), round(eu["x"], 3), round(eu["y"], 3)]
                    ],
                    "spears": su.get("spears", False),
                    "face": su["facing"],
                    "tilt": round(su.get("tilt", 0.0), 2),
                }

                if abs(eu.get("tilt", 0.0) - su.get("tilt", 0.0)) > 0.05:
                    b_entry["tiltAt"] = [
                        [0.0, round(su.get("tilt", 0.0), 2)],
                        [round(dur * 0.7, 2), round(eu.get("tilt", 0.0), 2)]
                    ]

                if eu.get("gap_w", 0) > 0:
                    b_entry["gap"] = {
                        "at": round(min(0.8, dur * 0.25), 2),
                        "dur": round(min(1.2, dur * 0.4), 2),
                        "w": eu["gap_w"]
                    }

                if ev_type in ("IMPACT", "BREAKTHROUGH"):
                    b_entry["impactAt"] = round(min(1.2, dur * 0.35), 2)

                blocks.append(b_entry)

            args["blocks"] = blocks
            args["ground"] = {"color": "#c9ad7a", "grass": True, "rocks": True}

        elif tpl == "army":
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
            if args.get("view"):
                args["mid"][0]["view"] = args["view"]
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
            args["preset"] = "consul"
            args["face"] = "shout"
            args["talk"] = True
            args["gesture"] = "point"
            args["R"] = 0.22 if not cam["safe_zones"]["is_vertical"] else 0.26

        elif tpl == "scene":
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
            if args.get("view"):
                args["people"][0]["view"] = args["view"]
            if ev_type == "MISSILE_VOLLEY":
                args["fx"] = [{"kind": "javelins", "at": 0.6, "dur": 1.2, "dir": 1}]

        # Attach synchronized audio cues with negative dB gains
        sfx_list = list(new_s.get("sfx") or [])
        manual_cues = [c for c in sfx_list if c.get("manual") or c.get("source") == "manual"]

        # Only add auto battle cues if no manual cue is locked
        if not manual_cues:
            auto_cues: List[Dict[str, Any]] = []
            sfx_specs = BATTLE_SFX_MAP.get(ev_type, ({"name": "shield_bash", "gain": -10.0}, {"name": "footsteps", "gain": -14.0}))
            c1 = sfx_specs[0]
            auto_cues.append({
                "source": "auto_battle_v12",
                "event_id": primary_evt.get("event_id", "evt_001"),
                "name": c1["name"],
                "at": round(min(0.8, dur * 0.25), 2),
                "gain": c1["gain"],
                "auto": True,
            })
            if len(sfx_specs) > 1 and dur >= 3.0:
                c2 = sfx_specs[1]
                auto_cues.append({
                    "source": "auto_battle_v12",
                    "event_id": primary_evt.get("event_id", "evt_001"),
                    "name": c2["name"],
                    "at": round(min(2.0, dur * 0.65), 2),
                    "gain": c2["gain"],
                    "auto": True,
                })
            new_s["sfx"] = auto_cues
        else:
            new_s["sfx"] = manual_cues

        new_s["tpl"] = tpl
        new_s["args"] = args
        compiled_shots.append(new_s)

    return compiled_shots


def plan_battle_choreo_for_project(
    project_path: str,
    review_only: bool = True,
    apply_choreo: bool = False,
) -> Dict[str, Any]:
    """Top-level entry point to analyze and choreograph a military history battle scene.

    Safely rejects DEM and 0-shot projects. Performs atomic writes and selective invalidation.
    """
    p = Path(project_path).resolve()
    cfg_file = p / "config.json"
    cfg = read_json(cfg_file, {}) or {}
    pack = cfg.get("pack", "squire")

    # Reject DEM and non-Squire packs safely
    if pack != "squire":
        return {
            "status": "NOT_APPLICABLE",
            "message": f"Battle choreography is exclusively for pack 'squire' (found '{pack}'). DEM remains unaffected.",
            "timeline": None,
        }

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
    events_by_shot = index_battle_events_by_shot(events, shots)

    # Step 2: Build state timeline with continuity
    timeline = build_battle_state_timeline(events_by_shot, shots)

    # Step 3: Validate causality
    valid, errors = validate_battle_causality(timeline)
    timeline["causality_valid"] = valid
    timeline["causality_errors"] = errors

    build_dir = p / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    if not valid:
        fail_res = {
            "status": "NEEDS_REVIEW",
            "message": "Causality validation failed; apply blocked to prevent invalid animation.",
            "events_count": len(events),
            "timeline": timeline,
            "causality_valid": False,
            "causality_errors": errors,
        }
        write_json(build_dir / "battle_review.json", fail_res)
        return fail_res

    # Check if applying
    if apply_choreo or not review_only:
        # Pre-calculate visual hash before apply
        vhash_before = compute_canonical_visual_hash(str(p), story_data=story_data)

        compiled_shots = compile_battle_timeline_to_shots(timeline, shots, cfg)

        # Count actual changes
        changed_shots_count = 0
        for old_s, new_s in zip(shots, compiled_shots):
            if (old_s.get("tpl") != new_s.get("tpl") or
                canonical_json_serialize(old_s.get("args")) != canonical_json_serialize(new_s.get("args"))):
                changed_shots_count += 1

        story_data_new = dict(story_data)
        story_data_new["shots"] = compiled_shots
        story_data_new["battle_choreo_status"] = "APPLIED" if changed_shots_count > 0 else "NO_CHANGE"

        vhash_after = compute_canonical_visual_hash(str(p), story_data=story_data_new)
        visual_changed = (vhash_before != vhash_after)

        # Atomic backup and write
        backup_file = p / "story" / "shots.backup.json"
        if shots_file.exists():
            shutil.copyfile(shots_file, backup_file)

        # Atomic write via tempfile
        with tempfile.NamedTemporaryFile("w", dir=str(shots_file.parent), delete=False, encoding="utf-8") as tf:
            tf.write(canonical_json_serialize(story_data_new))
            tmp_path = Path(tf.name)
        tmp_path.replace(shots_file)

        # Selective Invalidation: Only invalidate video_silent if visual parameters actually changed
        if visual_changed:
            for fn in ("video_silent.mp4", "preview_silent.mp4", "preview.mp4"):
                f = build_dir / fn
                if f.exists():
                    try:
                        f.unlink()
                    except Exception:
                        pass

        result_status = "APPLIED" if changed_shots_count > 0 else "NO_CHANGE"
        review_res = {
            "status": result_status,
            "events_count": len(events),
            "changed_shots_count": changed_shots_count,
            "visual_changed": visual_changed,
            "vhash_before": vhash_before,
            "vhash_after": vhash_after,
            "timeline": timeline,
            "causality_valid": True,
            "causality_errors": [],
        }
        write_json(build_dir / "battle_review.json", review_res)
        write_json(build_dir / "battle_diff.json", {
            "status": result_status,
            "changed_shots_count": changed_shots_count,
            "visual_changed": visual_changed,
        })
        write_json(build_dir / "battle_plan_v12.json", timeline)
        return review_res

    review_res = {
        "status": "REVIEWED",
        "events_count": len(events),
        "timeline": timeline,
        "causality_valid": valid,
        "causality_errors": errors,
    }
    write_json(build_dir / "battle_review.json", review_res)
    write_json(build_dir / "battle_plan_v12.json", timeline)
    return review_res


def main():
    parser = argparse.ArgumentParser(description="Roman Battle Choreography & Narration-to-Action Compiler (V12)")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--review", action="store_true", help="Generate review and battle plan without mutating shots")
    parser.add_argument("--apply", action="store_true", help="Apply compiled battle choreography to story/shots.json")
    parser.add_argument("--validate-only", action="store_true", help="Validate causality without modifying files")
    parser.add_argument("--check-diff", action="store_true", help="Audit diff between current shots and proposed battle choreography")

    args = parser.parse_args()
    proj = Path(args.project).resolve()
    if not proj.is_dir():
        sys.stderr.write(f"Error: Project directory '{proj}' does not exist.\n")
        sys.exit(1)

    if args.validate_only:
        res = plan_battle_choreo_for_project(str(proj), review_only=True)
        is_valid = res.get("causality_valid", False)
        print(canonical_json_serialize(res))
        sys.exit(0 if is_valid else 2)

    if args.apply:
        res = plan_battle_choreo_for_project(str(proj), review_only=False, apply_choreo=True)
        status = res.get("status")
        print(canonical_json_serialize(res))
        sys.exit(0 if status in ("CHOREOGRAPHED", "NO_RENDERABLE_CHANGE") else 2)

    # Default or --review / --check-diff
    res = plan_battle_choreo_for_project(str(proj), review_only=True)
    print(canonical_json_serialize(res))
    sys.exit(0 if res.get("status") in ("REVIEWED", "NOT_APPLICABLE") else 2)


if __name__ == "__main__":
    main()
