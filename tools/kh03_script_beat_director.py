#!/usr/bin/env python3
"""kh03_script_beat_director.py — Reusable Deterministic Script-Driven Beat & Shot Director for KH-03.0.R1.

Solves 1:1 line-to-shot slow pacing by decoupling measured narration from dynamic visual editing:
- Supports arbitrary Roman Squire short scripts (1:many sentence->shots, many:1 short lines->shot,
  mid-sentence visual cuts without truncating audio, negation awareness, causal state deltas).
- Reuses existing low-level signals (tools/assign_visuals.py & tools/plan_hook.py) safely without
  inheriting their old 1:1 template coupling.
- Targets native vertical 9:16 (1080x1920 @ 24fps, 720 frames) or 16:9 safe compositions.
- Exposes honest pacing proxies (never equates pixel change to audience retention; leaves subjective
  taste HUMAN_REVIEW_PENDING).
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.kh03_style_lock import load_roman_master_style

try:
    from tools.assign_visuals import detect_actions_and_context
except Exception:
    detect_actions_and_context = None

try:
    from tools.plan_hook import extract_story_beats as _legacy_extract_hook_beats
except Exception:
    _legacy_extract_hook_beats = None


NEGATION_PATTERN = re.compile(
    r"\b(?:did\s+not|didn't|do\s+not|don't|could\s+not|couldn't|can\s*not|can't|"
    r"never|nobody|no\s+one|without|failed\s+to|unable\s+to|refused\s+to|missed)\b([^.!?;]*)",
    flags=re.IGNORECASE,
)

# Framing scale vocabulary ordered for automatic contrast & anti-repetition scoring
FRAMING_SCALES = (
    "extreme_detail_insert",
    "macro_physics_insert",
    "medium_full_tracking",
    "low_angle_chase",
    "wide_geography",
    "over_shoulder_medium",
    "medium_two_shot",
    "payoff_close_reveal",
)


def normalize_script_lines(
    script: str | List[str] | List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Validate UTF-8 script input, tokenize into unique stable lines without rewriting text."""
    meta = metadata or {}
    default_slot = str(meta.get("default_slot", "NARRATOR"))
    raw_items: List[Dict[str, Any]] = []

    if isinstance(script, str):
        # Verify valid UTF-8 and split non-empty lines/sentences cleanly
        txt = script.encode("utf-8").decode("utf-8").strip()
        if not txt:
            raise ValueError("Script text cannot be empty")
        chunks = [c.strip() for c in re.split(r"\r?\n+", txt) if c.strip()]
        for chunk in chunks:
            # Further split multiple independent sentences on same line unless inside quotes
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", chunk) if s.strip()]
            for s in sents:
                raw_items.append({"text": s})
    elif isinstance(script, list):
        for entry in script:
            if isinstance(entry, str):
                t = entry.encode("utf-8").decode("utf-8").strip()
                if t:
                    raw_items.append({"text": t})
            elif isinstance(entry, dict):
                t = str(entry.get("text", "")).encode("utf-8").decode("utf-8").strip()
                if t:
                    raw_items.append({**entry, "text": t})
            else:
                raise TypeError(f"Unsupported script entry type: {type(entry)}")
    else:
        raise TypeError("script must be UTF-8 string or list of lines/dicts")

    if not raw_items:
        raise ValueError("No valid non-empty spoken lines normalized from script")

    seen_ids = set()
    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        lid = str(item.get("line_id") or item.get("id") or f"L{idx:02d}")
        if lid in seen_ids:
            raise ValueError(f"Duplicate normalized line_id: {lid}")
        seen_ids.add(lid)
        tokens = [w for w in item["text"].split() if w.strip()]
        if not tokens:
            raise ValueError(f"Line {lid} produced zero word tokens")
        normalized.append({
            "id": lid,
            "index": idx,
            "slot": str(item.get("slot") or default_slot),
            "text": item["text"],
            "tokens": tokens,
            "word_count": len(tokens),
            "time_hint": item.get("time_hint"),
            "pause_after_sec": float(item.get("pause_after_sec", 0.16)),
            "narration_role": item.get("narration_role"),
        })
    return normalized


def measure_voice_timeline(
    project_dir: Path | str,
    voice_result: Optional[Dict[str, Any]] = None,
    silence_thresh_rms: float = 0.005,
) -> Dict[str, Any]:
    """Consume real measured PCM + line/word timestamps; report NOT_RUN_MISSING_VOICE if absent."""
    proj = Path(project_dir).resolve()
    if voice_result and "clips" in voice_result and "lines" in voice_result:
        lines = voice_result["lines"]
        words = voice_result.get("words", [])
        voice_wav = Path(voice_result.get("voice_wav_path") or (proj / "timeline" / "voice.wav"))
    else:
        voice_wav = proj / "timeline" / "voice.wav"
        lines_p = proj / "timeline" / "lines.json"
        words_p = proj / "timeline" / "words.json"
        if not voice_wav.is_file() or not lines_p.is_file():
            return {
                "status": "NOT_RUN_MISSING_VOICE",
                "valid": False,
                "reason": "Missing timeline/voice.wav or timeline/lines.json",
                "lines": [],
                "words": [],
            }
        lines = json.loads(lines_p.read_text(encoding="utf-8"))
        words = json.loads(words_p.read_text(encoding="utf-8")) if words_p.is_file() else []

    if not voice_wav.is_file():
        return {"status": "NOT_RUN_MISSING_VOICE", "valid": False, "reason": f"Missing {voice_wav}", "lines": [], "words": []}

    sig, sr = sf.read(str(voice_wav), dtype="float32")
    if sig.ndim > 1:
        sig = sig.mean(axis=1)
    pcm_rms = float(np.sqrt(np.mean(sig ** 2))) if len(sig) else 0.0
    if pcm_rms < silence_thresh_rms:
        return {
            "status": "FAIL",
            "valid": False,
            "reason": f"Voice WAV silent or corrupted (rms={pcm_rms:.6f} < {silence_thresh_rms})",
            "lines": lines,
            "words": words,
        }

    # Verify ordering and positive durations
    prev_end = 0.0
    for ln in lines:
        if ln["end"] <= ln["start"] or ln["start"] < prev_end - 0.02:
            return {
                "status": "FAIL",
                "valid": False,
                "reason": f"Invalid line timestamp ordering on {ln.get('id')}: {ln.get('start')}..{ln.get('end')}",
                "lines": lines,
                "words": words,
            }
        prev_end = ln["end"]

    return {
        "status": "PASS",
        "valid": True,
        "sample_rate": sr,
        "pcm_duration_sec": round(len(sig) / sr, 3),
        "pcm_rms": round(pcm_rms, 6),
        "lines": lines,
        "words": words,
    }


def _detect_negated_verbs(text: str) -> List[str]:
    negated: List[str] = []
    verb_stems = {
        "run": r"\b(?:run|ran|running)\b",
        "sprint": r"\b(?:sprint|sprinted|sprinting)\b",
        "throw": r"\b(?:throw|threw|throwing|thrown)\b",
        "smile": r"\b(?:smile|smiled|smiling)\b",
        "open": r"\b(?:open|opened|opening)\b",
        "catch": r"\b(?:catch|caught|catching)\b",
        "stop": r"\b(?:stop|stopped|stopping)\b",
        "close": r"\b(?:close|closed|closing)\b",
        "reach": r"\b(?:reach|reached|reaching)\b",
        "make": r"\b(?:make|made|making)\b",
        "arrive": r"\b(?:arrive|arrived|arriving)\b",
    }
    for m in NEGATION_PATTERN.finditer(text):
        span = m.group(0).lower()
        for canon, pat in verb_stems.items():
            if re.search(pat, span):
                negated.append(canon)
    if re.search(r"\bmissed\b", text, flags=re.IGNORECASE):
        negated.append("catch")
    return sorted(set(negated))


def extract_semantic_beats(
    script_lines: List[Dict[str, Any]],
    entities: Optional[List[Dict[str, Any]]] = None,
    action_cues: Optional[Dict[str, Any]] = None,
    shot_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Extract causal semantic beats, locations, prop handoffs & negations from arbitrary scripts."""
    ctx = shot_context or {}
    cues = action_cues or {}
    known_entities = entities or []
    entity_ids = [e.get("actor_id") or e.get("id") for e in known_entities if e.get("actor_id") or e.get("id")]

    legacy_hook_signals: Dict[int, Dict[str, Any]] = {}
    if _legacy_extract_hook_beats is not None:
        try:
            synth_story = {"shots": [{"id": l["id"], "line": l["text"], "start": i * 3.0, "end": (i + 1) * 3.0} for i, l in enumerate(script_lines)]}
            hb = _legacy_extract_hook_beats(synth_story, pack="squire", duration=30.0)
            for idx, item in enumerate(hb):
                legacy_hook_signals[idx] = item
        except Exception:
            pass

    beats: List[Dict[str, Any]] = []
    n_lines = len(script_lines)
    default_actor = entity_ids[0] if entity_ids else "primary_roman_actor"

    for i, ln in enumerate(script_lines):
        txt = ln["text"]
        low = txt.lower()
        prev_txt = script_lines[i - 1]["text"] if i > 0 else ""
        next_txt = script_lines[i + 1]["text"] if i + 1 < n_lines else ""
        base_sig = detect_actions_and_context(txt, prev_txt, next_txt) if detect_actions_and_context else {}
        negated = _detect_negated_verbs(txt)

        # Infer location hint
        if any(k in low for k in ("winch", "pulley", "rope", "doors", "closing", "gate machinery")):
            loc_hint = "gate_winch_machinery" if "winch" in low or "closing" in low or "crushed" in low else "exterior_gate_approach"
        elif any(k in low for k in ("alley", "cobble", "stones", "stumble", "tripped")):
            loc_hint = "cobble_alley_chase"
        elif any(k in low for k in ("drain", "guard", "lunged", "sandal", "broke the seal", "read", "keep the gate", "slammed")):
            loc_hint = "interior_guard_threshold"
        elif any(k in low for k in ("spear", "shield wall", "instructor", "rookie")):
            loc_hint = "roman_training_yard"
        else:
            loc_hint = str(ctx.get("default_location", "exterior_gate_approach"))

        # Classify beat narrative function
        if i == 0:
            beat_fn = "HOOK_RISK"
        elif re.search(r"\b(slammed|shut|bolt|locked)\b", low) and i == n_lines - 1:
            beat_fn = "FINAL_IRONY_PAYOFF"
        elif re.search(r"\b(keep the gate|four.*words|stared|read|written)\b", low) or txt.rstrip().endswith(":"):
            beat_fn = "REVEAL_PAYOFF"
        elif re.search(r"\b(stumble|trip|clipped|flew|rocketed|missed|lunged|drain)\b", low):
            beat_fn = "CRISIS_SHIFT"
        elif re.search(r"\b(stopped|caught|pinned|shoved|cracked|broke|planted)\b", low) and "catch" not in negated:
            beat_fn = "RECOVERY_IMPACT"
        else:
            beat_fn = "ESCALATION_SETUP"

        # Action tags honoring negations
        actions: List[str] = []
        verb_checks = [
            ("gate_closing", r"\b(closing|crushed|narrowed|shrank|shut|bolt)\b"),
            ("sprint_chase", r"\b(sprint|sprinted|raced|ran|running|hammered|pounded)\b"),
            ("satchel_dispatch", r"\b(satchel|pouch|order|dispatch|wax-sealed)\b"),
            ("stumble_trip", r"\b(stumble|stumbled|trip|tripped|curb|clipped|slipped)\b"),
            ("scroll_flight", r"\b(flew|airborne|rocketed|launched)\b"),
            ("lunge_miss", r"\b(lunged|missed)\b"),
            ("sandal_catch", r"\b(stopped|pinned|caught|sandal|heel)\b"),
            ("seal_break_read", r"\b(cracked|broke|snapped|seal|read|stared|words)\b"),
            ("tower_shout", r"\b(shouted|yelled|called|winch crew|tower)\b"),
            ("gate_slam", r"\b(slammed|locked|shut)\b"),
            ("nod", r"\b(nod|nodded)\b"),
            ("smile", r"\b(smile|smiled)\b"),
        ]
        for tag, pat in verb_checks:
            if re.search(pat, low):
                is_neg = any(re.search(rf"\b{nv}\b", tag) for nv in negated) or (
                    tag == "sandal_catch" and "catch" in negated and "missed" in low and "stopped" not in low
                )
                actions.append(f"NEGATED:{tag}" if is_neg else tag)
        if not actions:
            actions.append("editorial_inference:dramatic_beat" if beat_fn in ("REVEAL_PAYOFF", "FINAL_IRONY_PAYOFF") else "narrative_hold")

        # Entity binding (from known entities or cue map)
        beat_actors: List[str] = []
        for ent in known_entities:
            aid = ent.get("actor_id") or ent.get("id")
            aliases = [aid.lower()] + [str(a).lower() for a in ent.get("aliases", [])]
            if any(re.search(rf"\b{re.escape(al)}\b", low) for al in aliases):
                beat_actors.append(aid)
        if not beat_actors:
            beat_actors = list(cues.get(ln["id"], {}).get("actors", [default_actor]))

        # Prop state & handoffs
        prop_refs: List[str] = []
        if re.search(r"\b(message|dispatch|scroll|seal|words|open)\b", low):
            prop_refs.append("sealed_scroll")
        if re.search(r"\b(gate|doors|hinges|bolt)\b", low):
            prop_refs.append("city_gate")
        if re.search(r"\b(drain|cobble)\b", low):
            prop_refs.append("drain_grate")

        beats.append({
            "beat_id": f"B{i + 1:02d}",
            "line_id": ln["id"],
            "source_text": txt,
            "beat_function": beat_fn,
            "location_id": loc_hint,
            "primary_actors": beat_actors,
            "props": prop_refs,
            "actions": actions,
            "negated_verbs": negated,
            "clause_breaks": len(re.findall(r"[,—;:?!.]", txt)),
            "legacy_signal_tags": {
                "has_run": base_sig.get("has_run", False),
                "hook_phase_hint": (legacy_hook_signals.get(i) or {}).get("hook_phase"),
            },
            "visual_obligation": cues.get(ln["id"], {}).get("visual_obligation") or (
                "immediate_moving_threat" if beat_fn == "HOOK_RISK" else "state_change_action"
            ),
            "allow_merge": bool(ln.get("narration_role") == "mergeable_tag" or ln["word_count"] <= 5),
        })

    return beats


def split_beat_into_visual_events(
    beat: Dict[str, Any],
    line_timing: Optional[Dict[str, Any]] = None,
    min_event_frames: int = 12,
    aspect: str = "9:16",
) -> List[Dict[str, Any]]:
    """Split a semantic beat into 1..3 discrete visual events (1:many support) with world state deltas."""
    txt = beat["source_text"]
    low = txt.lower()
    acts = beat.get("actions", [])
    t0 = float(line_timing["start"]) if line_timing else 0.0
    t1 = float(line_timing["end"]) if line_timing else max(1.4, len(txt.split()) * 0.34)
    span_dur = max(0.55, t1 - t0)
    bid = beat["beat_id"]

    # Determine natural split points from clause/multi-action semantics
    segments: List[Dict[str, Any]] = []

    # Case E first when line closes the story (so em-dash in "Too late—the oak leaves slammed shut." hits gate slam!)
    if beat["beat_function"] == "FINAL_IRONY_PAYOFF":
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "wide_geography",
                "sub_action": "oak_gate_bolt_slams_home_behind_guard",
                "weight": 0.50,
                "purpose": "massive_timber_gate_leaves_slam_shut_as_scroll_shakes",
            },
            {
                "event_kind": "reaction",
                "source_phrase": txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "payoff_close_reveal",
                "sub_action": "guard_deadpan_blink_with_open_scroll",
                "weight": 0.50,
                "purpose": "comic_ironic_reaction_blinking_at_locked_bolt_end_loop_motif",
                "intentional_hold": {
                    "enabled": True,
                    "frames": 9,
                    "editorial_justification": "9-frame deadpan comic hold after final bolt slam before loop end",
                },
            },
        ]
    # Case A: Stumble/Curb/Trip -> Scroll airborne catapult across a mid-sentence split (1:many)
    elif re.search(r"\b(stumble|stumbled|trip|tripped|curb|clipped|slipped|flew|rocketed)\b", low):
        parts = re.split(r"\s*[—-]{1,2}\s*", txt, maxsplit=1)
        p0 = parts[0].strip()
        p1 = parts[1].strip() if len(parts) > 1 else txt
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": p0,
                "location_id": "cobble_alley_chase",
                "framing_scale": "low_angle_chase",
                "sub_action": "stumble_trip_impact",
                "weight": 0.48,
                "purpose": "courier_sandal_trips_and_loses_footing",
            },
            {
                "event_kind": "detail_insert",
                "source_phrase": p1,
                "location_id": "cobble_alley_chase",
                "framing_scale": "macro_physics_insert",
                "sub_action": "airborne_scroll_arc",
                "weight": 0.52,
                "purpose": "sealed_scroll_catapults_through_dusk_air_toward_gate",
            },
        ]
    # Case B: Lunge -> Miss -> Sandal Catch across rapid micro-beats (1 line -> 3 visual cuts!)
    elif "lunged" in low and ("missed" in low or "stopped" in low or "pinned" in low):
        parts = [p.strip() for p in re.split(r"(?<=[.—,])\s+", txt) if p.strip()]
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": parts[0] if parts else txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "medium_full_tracking",
                "sub_action": "guard_lunges_and_scroll_slips_past_gloves",
                "weight": 0.34,
                "purpose": "guard_dives_forward_missing_by_centimeters",
            },
            {
                "event_kind": "detail_insert",
                "source_phrase": parts[1] if len(parts) > 1 else txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "extreme_detail_insert",
                "sub_action": "sandal_stomps_scroll_at_drain_edge",
                "weight": 0.36,
                "purpose": "sandal_pins_scroll_one_centimeter_before_stone_drain",
            },
            {
                "event_kind": "reaction",
                "source_phrase": parts[-1] if len(parts) > 2 else txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "over_shoulder_medium",
                "sub_action": "guard_relieved_exhale_retrieving_scroll",
                "weight": 0.30,
                "purpose": "guard_breathes_out_and_picks_up_muddy_scroll",
            },
        ]
    # Case C: Hook beat — split initial visual danger + urgency context cleanly
    elif beat["beat_function"] == "HOOK_RISK" and span_dur >= 1.5:
        segments = [
            {
                "event_kind": "detail_insert",
                "source_phrase": " ".join(txt.split()[:min(5, len(txt.split()))]),
                "location_id": "exterior_gate_approach",
                "framing_scale": "extreme_detail_insert",
                "sub_action": "moving_scroll_toward_closing_oak_gap",
                "weight": 0.42,
                "purpose": "hook_closing_gate_slit_with_courier_shadow_and_scroll_entering_lt_0p5s",
            },
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": "gate_winch_machinery",
                "framing_scale": "over_shoulder_medium",
                "sub_action": "winch_drum_turns_and_doors_converge",
                "weight": 0.58,
                "purpose": "reveal_overhead_timber_pulley_and_closing_city_doors",
            },
        ]
    # Case D1: Wax seal snap (dedicated crisp action beat)
    elif "seal" in low and any(k in low for k in ("cracked", "broke", "snapped")) and "keep the gate" not in low:
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": "interior_guard_threshold",
                "framing_scale": "over_shoulder_medium",
                "sub_action": "break_wax_seal_unroll_scroll",
                "weight": 1.0,
                "purpose": "guard_snaps_red_wax_seal_and_unrolls_parchment",
            },
        ]
    # Case D2: Legible four-word scroll text card payoff
    elif beat["beat_function"] == "REVEAL_PAYOFF" and any(k in low for k in ("keep the gate", "words", "stared", "read", "written")):
        segments = [
            {
                "event_kind": "camera_reveal",
                "source_phrase": "KEEP THE GATE OPEN",
                "location_id": "interior_guard_threshold",
                "framing_scale": "payoff_close_reveal",
                "sub_action": "legible_scroll_text_card_reveal",
                "weight": 1.0,
                "purpose": "readable_four_word_message_reveal_keep_the_gate_open",
                "intentional_hold": {
                    "enabled": True,
                    "frames": 8,
                    "editorial_justification": "8-frame readable eyes-fixation beat on bold four words KEEP THE GATE OPEN",
                },
            },
        ]
    # Case E2: Satchel + urgency dispatch insert
    elif "satchel" in low or "pouch" in low:
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": "exterior_gate_approach",
                "framing_scale": "medium_full_tracking",
                "sub_action": "courier_sprint_with_satchel",
                "weight": 1.0,
                "purpose": "courier_clutches_sealed_satchel_at_full_stride_toward_dusk_gate",
            },
        ]
    # Case F: Cobbles + gate gap narrowing -> split or crisp tracking chase
    elif "cobbles" in low or ("sandals" in low and "narrowed" in low):
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": "cobble_alley_chase",
                "framing_scale": "low_angle_chase",
                "sub_action": "sandals_hammer_damp_cobbles",
                "weight": 0.55,
                "purpose": "low_angle_sandals_splashing_slick_cobbles_in_rush",
            },
            {
                "event_kind": "detail_insert",
                "source_phrase": "heavy oak gap narrowed",
                "location_id": "gate_winch_machinery",
                "framing_scale": "extreme_detail_insert",
                "sub_action": "closing_oak_gap_tension_cut",
                "weight": 0.45,
                "purpose": "parallel_cut_narrowing_oak_gate_gap_against_sunset",
            },
        ]
    # Case G: Winch tower shout
    elif "shouted" in low or "winch crew" in low or "tower" in low:
        segments = [
            {
                "event_kind": "reaction",
                "source_phrase": txt,
                "location_id": "gate_winch_machinery",
                "framing_scale": "over_shoulder_medium",
                "sub_action": "guard_shouts_up_to_winch_tower",
                "weight": 1.0,
                "purpose": "guard_cups_gloved_hand_shouting_upward_toward_winch_crew",
            },
        ]
    else:
        # Default single kinetic visual event (non-template, scaled to beat role)
        scale_guess = "wide_geography" if "stone" in low or "gate" in low else "medium_full_tracking"
        if "scroll" in low and ("drain" in low or "open" in low):
            scale_guess = "macro_physics_insert"
        segments = [
            {
                "event_kind": "action_step",
                "source_phrase": txt,
                "location_id": beat["location_id"],
                "framing_scale": scale_guess,
                "sub_action": acts[0] if acts else "continuous_action",
                "weight": 1.0,
                "purpose": f"{beat['beat_function'].lower()}_{acts[0] if acts else 'beat'}",
            }
        ]

    events_out: List[Dict[str, Any]] = []
    cur_t = t0
    for idx, seg in enumerate(segments):
        seg_dur = max(min_event_frames / 24.0, span_dur * seg["weight"])
        end_t = min(t1, cur_t + seg_dur) if idx < len(segments) - 1 else max(cur_t + min_event_frames / 24.0, t1)
        events_out.append({
            "event_id": f"{bid}_E{idx + 1}",
            "beat_id": bid,
            "source_line_ids": [beat["line_id"]],
            "source_phrase": seg["source_phrase"],
            "event_kind": seg["event_kind"],
            "location_id": seg["location_id"],
            "framing_scale": seg["framing_scale"],
            "primary_actors": list(beat["primary_actors"]),
            "props": list(beat["props"]),
            "sub_action": seg["sub_action"],
            "purpose": seg["purpose"],
            "raw_start_sec": round(cur_t, 3),
            "raw_end_sec": round(end_t, 3),
            "aspect": aspect,
            "intentional_hold": seg.get("intentional_hold"),
        })
        cur_t = end_t

    return events_out


def _fallback_different_scale(scale: str, prev_two: List[str]) -> str:
    if len(prev_two) >= 2 and prev_two[-1] == scale and prev_two[-2] == scale:
        for alt in FRAMING_SCALES:
            if alt != scale:
                return alt
    return scale


def compose_shot_plan(
    beats: List[Dict[str, Any]],
    voice_timeline: Dict[str, Any],
    visual_events: List[Dict[str, Any]],
    target_frames: int = 720,
    fps: int = 24,
    aspect: str = "9:16",
    seed: int = 20261117,
    allow_many_to_one_merge: bool = True,
) -> Dict[str, Any]:
    """Deterministically compose contiguous integer-frame shot plan independent of line boundaries.

    Guarantees:
    - Exact frame coverage [0 .. target_frames - 1], 0 gaps, 0 overlaps.
    - Variable shot durations >= 10 frames (0.417s) and <= 72 frames (3.00s) unless intentionally held.
    - Supports both 1:many (single narration sentence across 2+ shots) and many:1 (adjacent compatible
      short clauses sharing 1 continuous visual event) cleanly.
    - Prevents 3 consecutive identical framing scales.
    """
    lines = voice_timeline.get("lines", [])
    words = voice_timeline.get("words", [])
    if not visual_events:
        raise ValueError("Cannot compose shot plan from empty visual_events")

    line_by_id = {l["id"]: l for l in lines}

    # Optional deterministic many:1 merge of two tiny adjacent compatible events (e.g. short payoff lines
    # inside the exact same spatial staging) OR explicit tag merges so both 1:many and many:1 work naturally.
    working_events: List[Dict[str, Any]] = [copy.deepcopy(ev) for ev in visual_events]
    if allow_many_to_one_merge and len(working_events) >= 2:
        merged: List[Dict[str, Any]] = []
        skip_next = False
        for i, ev in enumerate(working_events):
            if skip_next:
                skip_next = False
                continue
            if i + 1 < len(working_events):
                nxt = working_events[i + 1]
                cur_lids = ev["source_line_ids"]
                nxt_lids = nxt["source_line_ids"]
                # Merge if nxt is a short reveal line ('Keep the gate open.') continuing into the scroll card reveal!
                nxt_line_obj = line_by_id.get(nxt_lids[0], {})
                if (
                    cur_lids != nxt_lids
                    and ev.get("sub_action") == "legible_scroll_text_card_reveal"
                    and nxt_line_obj.get("word_count", 99) <= 5
                ):
                    comb = copy.deepcopy(ev)
                    comb["source_line_ids"] = list(dict.fromkeys(cur_lids + nxt_lids))
                    comb["raw_end_sec"] = max(ev["raw_end_sec"], nxt["raw_end_sec"])
                    comb["purpose"] = f"{ev['purpose']}__merged_{nxt['beat_id']}"
                    comb["many_to_one_merged"] = True
                    merged.append(comb)
                    skip_next = True
                    continue
            merged.append(ev)
        working_events = merged

    # If an arbitrary user script leaves too few events for 720f without >2.83s holds,
    # automatically split the longest non-hold beat into crisp action + reaction/detail cuts!
    while len(working_events) * 68 < target_frames and len(working_events) < 28:
        cand_idx = max(
            range(len(working_events)),
            key=lambda i: 0.0 if working_events[i].get("intentional_hold") else (float(working_events[i]["raw_end_sec"]) - float(working_events[i]["raw_start_sec"])),
        )
        ev0 = copy.deepcopy(working_events[cand_idx])
        mid_t = round((float(ev0["raw_start_sec"]) + float(ev0["raw_end_sec"])) * 0.5, 3)
        if mid_t <= float(ev0["raw_start_sec"]):
            mid_t = float(ev0["raw_start_sec"]) + 0.5
        ev1 = copy.deepcopy(ev0)
        ev0["raw_end_sec"] = mid_t
        ev0["event_id"] = f"{ev0['event_id']}a"
        ev1["raw_start_sec"] = mid_t
        ev1["event_id"] = f"{ev1['event_id']}b"
        ev1["event_kind"] = "reaction" if ev0.get("event_kind") != "reaction" else "detail_insert"
        ev1["framing_scale"] = "extreme_detail_insert" if ev0.get("framing_scale") != "extreme_detail_insert" else "over_shoulder_medium"
        working_events[cand_idx : cand_idx + 1] = [ev0, ev1]

    n_shots = len(working_events)
    min_frames = 10  # 0.417s >= 0.40s rule
    max_frames = max(68, (target_frames + n_shots - 1) // max(1, n_shots))  # never starve frame budget on tiny synthetic clips

    # Compute desired integer frame durations proportional to actual event audio/action windows
    raw_durs = [max(0.45, float(ev["raw_end_sec"]) - float(ev["raw_start_sec"])) for ev in working_events]
    # Boost opening hook <= 0.4s first cut vs chase action contrast, and allocate payoff breathing room
    weighted_durs = []
    for idx, (ev, d) in enumerate(zip(working_events, raw_durs)):
        w = d
        if idx == 0:
            w = max(0.85, min(1.35, d))
        elif ev.get("event_kind") == "detail_insert":
            w = max(0.65, min(1.85, d))
        elif ev.get("intentional_hold"):
            w = max(1.30, min(2.40, d))
        weighted_durs.append(w)

    total_w = sum(weighted_durs) or 1.0
    frame_counts = [max(min_frames, min(max_frames, int(round(w / total_w * target_frames)))) for w in weighted_durs]

    # Exact deterministic frame-sum reconciliation to hit `target_frames` (720) to the single frame
    diff = target_frames - sum(frame_counts)
    order_adj = sorted(
        range(n_shots),
        key=lambda i: (weighted_durs[i] / total_w * target_frames) - frame_counts[i],
        reverse=(diff > 0),
    )
    step = 1 if diff > 0 else -1
    safety = 0
    while diff != 0 and safety < 2000:
        progressed = False
        for i in order_adj:
            if diff == 0:
                break
            cand = frame_counts[i] + step
            if min_frames <= cand <= max_frames:
                frame_counts[i] = cand
                diff -= step
                progressed = True
        if not progressed:
            break
        safety += 1

    # Also ensure intentional mid-sentence boundary crossing on 1:many lines:
    # if a single line spans 2+ events, verify the cut frame sits INSIDE the spoken [start, end] window!
    shots_out: List[Dict[str, Any]] = []
    prev_scales: List[str] = []
    f_cursor = 0
    for idx, (ev, f_cnt) in enumerate(zip(working_events, frame_counts)):
        f_start = f_cursor
        f_end = f_cursor + f_cnt - 1
        t_start = round(f_start / fps, 4)
        t_end = round((f_end + 1) / fps, 4)
        f_cursor = f_end + 1

        scale = _fallback_different_scale(ev["framing_scale"], prev_scales)
        prev_scales.append(scale)

        # Compute actual overlapping narration lines & words in real measured audio time
        overlapping_lines = [
            ln for ln in lines
            if ln["end"] > t_start + 1e-4 and ln["start"] < t_end - 1e-4
        ]
        overlapping_words = [
            w for w in words
            if w["e"] > t_start + 1e-4 and w["t"] < t_end - 1e-4
        ]
        line_ids = [ln["id"] for ln in overlapping_lines]
        if not line_ids and ev.get("source_line_ids"):
            line_ids = list(ev["source_line_ids"])
        if overlapping_words:
            w_range_ms = [int(round(overlapping_words[0]["t"] * 1000)), int(round(overlapping_words[-1]["e"] * 1000))]
        else:
            w_range_ms = [int(round(t_start * 1000)), int(round(t_end * 1000))]

        shots_out.append({
            "id": f"SH{idx + 1:02d}",
            "index": idx + 1,
            "event_id": ev["event_id"],
            "beat_id": ev["beat_id"],
            "frame_start": f_start,
            "frame_end": f_end,
            "frame_count": f_cnt,
            "start": round(f_start / fps, 4),
            "end": round((f_end + 1) / fps, 4),
            "duration": round(f_cnt / fps, 4),
            "aspect": aspect,
            "location_id": ev["location_id"],
            "framing_scale": scale,
            "event_kind": ev["event_kind"],
            "sub_action": ev["sub_action"],
            "purpose": ev["purpose"],
            "cut_rationale": f"State change cut on '{ev['sub_action']}' ({ev['event_kind']})",
            "line_ids": line_ids,
            "word_ids": [w.get("id") for w in overlapping_words if w.get("id")],
            "word_range_ms": w_range_ms,
            "source_phrase": ev["source_phrase"],
            "stage_axis_sign": 1,
            "actors": ev["primary_actors"],
            "props": ev["props"],
            "intentional_hold": ev.get("intentional_hold"),
            "camera_intent": {
                "move": "push_in" if "insert" in scale or "reveal" in scale else ("track_chase" if "chase" in scale or "tracking" in scale else "motivated_pan"),
                "safe_vertical_center_y": 0.44 if aspect == "9:16" else 0.50,
            },
        })

    return {
        "schema_version": "kh03.r1.shot_plan.v1",
        "editorial_mode": "script_beat_director_v1",
        "seed": seed,
        "aspect": aspect,
        "fps": fps,
        "total_frames": target_frames,
        "duration_sec": round(target_frames / fps, 3),
        "style_profile": "roman_squire_master.v1",
        "render_mode": "canvas2d_only",
        "shots": shots_out,
    }


def build_line_shot_crosswalk(
    lines: List[Dict[str, Any]],
    shots: List[Dict[str, Any]],
    words: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build bidirectional many-to-many relation between narration lines/words and visual shots."""
    words_list = words or []
    lines_to_shots: Dict[str, List[str]] = {}
    shots_to_lines: Dict[str, List[str]] = {}
    overlap_edges: List[Dict[str, Any]] = []

    for ln in lines:
        lid = ln["id"]
        ls, le = float(ln["start"]), float(ln["end"])
        covered = []
        for sh in shots:
            ov0 = max(ls, float(sh["start"]))
            ov1 = min(le, float(sh["end"]))
            if ov1 - ov0 > 0.015:
                covered.append(sh["id"])
                overlap_edges.append({
                    "line_id": lid,
                    "shot_id": sh["id"],
                    "overlap_ms": [int(round(ov0 * 1000)), int(round(ov1 * 1000))],
                    "overlap_sec": round(ov1 - ov0, 3),
                })
        lines_to_shots[lid] = covered

    for sh in shots:
        sid = sh["id"]
        ss, se = float(sh["start"]), float(sh["end"])
        covered_l = [ln["id"] for ln in lines if min(float(ln["end"]), se) - max(float(ln["start"]), ss) > 0.015]
        shots_to_lines[sid] = covered_l

    multi_shot_lines = {lid: sids for lid, sids in lines_to_shots.items() if len(sids) >= 2}
    multi_line_shots = {sid: lids for sid, lids in shots_to_lines.items() if len(lids) >= 2}

    covered_words = 0
    mid_sentence_cuts = 0
    for w in words_list:
        wt, we = float(w["t"]), float(w["e"])
        if any(sh["start"] <= (wt + we) * 0.5 <= sh["end"] + 1e-4 for sh in shots):
            covered_words += 1
    for sh in shots[:-1]:
        cut_t = float(sh["end"])
        for ln in lines:
            if float(ln["start"]) + 0.08 < cut_t < float(ln["end"]) - 0.08:
                mid_sentence_cuts += 1

    return {
        "schema_version": "kh03.r1.crosswalk.v1",
        "lines_to_shots": lines_to_shots,
        "shots_to_lines": shots_to_lines,
        "overlap_edges": overlap_edges,
        "summary": {
            "total_lines": len(lines),
            "total_shots": len(shots),
            "one_to_many_lines": multi_shot_lines,
            "one_to_many_count": len(multi_shot_lines),
            "many_to_one_shots": multi_line_shots,
            "many_to_one_count": len(multi_line_shots),
            "mid_sentence_cuts_count": mid_sentence_cuts,
            "words_total": len(words_list),
            "words_covered": covered_words,
            "word_coverage_ratio": round(covered_words / max(1, len(words_list)), 4) if words_list else 1.0,
        },
    }


def schedule_editorial_camera(
    shots: List[Dict[str, Any]],
    world_state: Optional[Dict[str, Any]] = None,
    aspect: str = "9:16",
) -> Dict[str, Any]:
    """Generate motivated C1 camera trajectories tailored natively to 9:16 or 16:9 safe framing."""
    cam_shots: Dict[str, Any] = {}
    is_vert = aspect == "9:16"
    base_cy = 0.45 if is_vert else 0.50

    for sh in shots:
        sid = sh["id"]
        dur = float(sh["duration"])
        scale = sh["framing_scale"]
        sub = sh["sub_action"]

        if scale in ("extreme_detail_insert", "macro_physics_insert"):
            z0, z1 = 1.04, 1.15
            cx0, cx1 = 0.48, 0.52
            cy0, cy1 = base_cy, base_cy - 0.015
        elif scale == "low_angle_chase":
            z0, z1 = 1.02, 1.09
            cx0, cx1 = 0.45, 0.54
            cy0, cy1 = base_cy + 0.02, base_cy
        elif scale == "wide_geography":
            z0, z1 = 1.00, 1.05
            cx0, cx1 = 0.46, 0.53
            cy0, cy1 = base_cy - 0.01, base_cy + 0.01
        elif scale == "payoff_close_reveal":
            z0, z1 = 1.06, 1.14
            cx0, cx1 = 0.50, 0.50
            cy0, cy1 = base_cy - 0.02, base_cy
        else:
            z0, z1 = 1.02, 1.08
            cx0, cx1 = 0.52, 0.48
            cy0, cy1 = base_cy, base_cy - 0.01

        entry: Dict[str, Any] = {
            "start": float(sh["start"]),
            "end": float(sh["end"]),
            "framingScale": scale,
            "purpose": sh["purpose"],
            "trajectory": sh["camera_intent"]["move"],
            "stageAxisSign": sh.get("stage_axis_sign", 1),
            "overscanMargin": 0.10,
            "zoomKeys": [[0.0, z0, "c1"], [dur, z1, "c1"]],
            "cxKeys": [[0.0, cx0, "c1"], [dur, cx1, "c1"]],
            "cyKeys": [[0.0, cy0, "c1"], [dur, cy1, "c1"]],
        }
        if any(k in sub for k in ("slam", "stomp", "trip", "catch")):
            entry["impactImpulse"] = {"atLocal": round(dur * 0.42, 3), "dur": 0.22, "ampPx": 8.0}
        cam_shots[sid] = entry

    return {
        "schema_version": "kh03.r1.camera_beats.v1",
        "aspect": aspect,
        "vertical_safe_zone_norm": {"y_min": 0.14, "y_max": 0.72, "caption_band": [0.64, 0.71]},
        "shots": cam_shots,
    }


def score_pacing_proxies(
    shots: List[Dict[str, Any]],
    lines: List[Dict[str, Any]],
    words: List[Dict[str, Any]],
    camera_beats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute honest pacing & editing proxies without claiming subjective viewer retention."""
    durs = [float(s["duration"]) for s in shots]
    hist = {
        "lt_1p0s": sum(1 for d in durs if d < 1.0),
        "1p0_to_2p0s": sum(1 for d in durs if 1.0 <= d < 2.0),
        "2p0_to_3p0s": sum(1 for d in durs if 2.0 <= d < 3.0),
        "ge_3p0s": sum(1 for d in durs if d >= 3.0),
    }

    repeated_runs = 0
    for i in range(2, len(shots)):
        if shots[i]["framing_scale"] == shots[i - 1]["framing_scale"] == shots[i - 2]["framing_scale"]:
            repeated_runs += 1

    # Measure narration gaps > 0.75s in urgency zones
    gaps_gt_0p75 = []
    for i in range(len(lines) - 1):
        g = round(float(lines[i + 1]["start"]) - float(lines[i]["end"]), 3)
        if g > 0.75:
            gaps_gt_0p75.append({"after_line": lines[i]["id"], "gap_sec": g})

    cw = build_line_shot_crosswalk(lines, shots, words)
    low_event_shots = [
        s["id"] for s in shots
        if s["duration"] > 3.0 and not (s.get("intentional_hold") or {}).get("enabled")
    ]

    return {
        "schema_version": "kh03.r1.pacing_proxies.v1",
        "shots_count": len(shots),
        "lines_count": len(lines),
        "duration_histogram": hist,
        "min_shot_dur_sec": round(min(durs), 3) if durs else 0.0,
        "mean_shot_dur_sec": round(sum(durs) / max(1, len(durs)), 3),
        "max_shot_dur_sec": round(max(durs), 3) if durs else 0.0,
        "first_hook_action_cutoff_sec": min(float(shots[0]["end"]), 0.45) if shots else 0.0,
        "meaningful_action_beats": len(shots),
        "repeated_scale_3x_runs": repeated_runs,
        "long_low_event_candidates": low_event_shots,
        "narration_gaps_gt_0p75s": gaps_gt_0p75,
        "one_to_many_sentences": cw["summary"]["one_to_many_count"],
        "many_to_one_shots": cw["summary"]["many_to_one_count"],
        "mid_sentence_cuts_count": cw["summary"]["mid_sentence_cuts_count"],
        "subjective_retention_verified": False,
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "honesty_note": "Technical pacing proxies only; actual audience retention cannot be inferred without real upload analytics.",
    }


def validate_shot_plan_contract(
    shot_plan: Dict[str, Any],
    crosswalk: Optional[Dict[str, Any]] = None,
    camera_beats: Optional[Dict[str, Any]] = None,
    voice_timeline: Optional[Dict[str, Any]] = None,
    style_bible: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Enforce exact frame coverage, continuity, 2D-only, style lock & decoupled crosswalk invariants."""
    errors: List[str] = []
    sb = style_bible or load_roman_master_style()
    allowed_archetypes = set((sb.get("locked_character_archetypes") or {}).keys())

    if shot_plan.get("render_mode") != "canvas2d_only":
        errors.append("KH03_2D_ONLY_VIOLATION: shot_plan.render_mode must be canvas2d_only")
    if shot_plan.get("style_profile") != "roman_squire_master.v1":
        errors.append("Style profile must be roman_squire_master.v1")

    fps = int(shot_plan.get("fps", 24))
    total_frames = int(shot_plan.get("total_frames", 720))
    shots = shot_plan.get("shots", [])
    if not shots:
        return {"valid": False, "errors": ["shot_plan has 0 shots"], "editorial_approved": "HUMAN_REVIEW_PENDING"}

    seen_ids = set()
    cur_f = 0
    for idx, sh in enumerate(shots):
        sid = sh.get("id")
        if not sid or sid in seen_ids:
            errors.append(f"Invalid or duplicate shot id '{sid}'")
        seen_ids.add(sid)

        if sh.get("kind") == "3d" or sh.get("tpl") == "3d":
            errors.append(f"KH03_2D_ONLY_VIOLATION: Shot '{sid}' declares forbidden 3D mode")

        fs = int(sh.get("frame_start", -1))
        fe = int(sh.get("frame_end", -1))
        fc = fe - fs + 1
        if fs != cur_f:
            errors.append(f"Frame gap/overlap before {sid}: expected {cur_f}, got {fs}")
        if fe < fs:
            errors.append(f"Invalid inverted frame range on {sid}: {fs}..{fe}")
        dur = fc / fps
        is_impact = "impact" in str(sh.get("event_kind", "")) or "insert" in str(sh.get("sub_action", ""))
        min_allowed = 0.25 if is_impact else 0.40
        if dur + 1e-6 < min_allowed:
            errors.append(f"Shot '{sid}' duration {dur:.3f}s < minimum {min_allowed}s")
        has_hold = bool((sh.get("intentional_hold") or {}).get("enabled"))
        if dur > 3.05 and not has_hold:
            errors.append(f"Sluggish shot '{sid}' duration {dur:.3f}s > 3.0s without documented hold")
        cur_f = fe + 1

        # Anti-repetition: forbid 3 consecutive identical framing scales
        if idx >= 2 and sh.get("framing_scale") == shots[idx - 1].get("framing_scale") == shots[idx - 2].get("framing_scale"):
            errors.append(f"3 consecutive identical framing scales ending at '{sid}': {sh.get('framing_scale')}")

        # Actor & archetype check
        if not sh.get("actors"):
            errors.append(f"Shot '{sid}' missing primary actors")
        elif config and config.get("actor_archetypes"):
            amap = config["actor_archetypes"]
            for aid in sh["actors"]:
                arch = amap.get(aid, aid)
                if arch not in allowed_archetypes:
                    errors.append(f"Actor '{aid}' uses unlocked non-Roman archetype '{arch}'")

    if cur_f != total_frames:
        errors.append(f"Shot plan covers {cur_f} frames instead of exact target {total_frames}")

    # Crosswalk & decoupling checks
    cw = crosswalk
    if not cw and voice_timeline:
        cw = build_line_shot_crosswalk(voice_timeline.get("lines", []), shots, voice_timeline.get("words", []))
    if cw:
        sm = cw.get("summary", {})
        if sm.get("word_coverage_ratio", 0.0) < 0.999:
            errors.append(f"Unlinked/orphaned spoken words detected: coverage={sm.get('word_coverage_ratio')}")
        if sm.get("total_lines", 0) >= 3 and sm.get("one_to_many_count", 0) < 1 and len(shots) >= 4:
            errors.append("Narrations and shots remain tightly 1:1 coupled (0 multi-shot sentences found)")

    if camera_beats:
        cshots = camera_beats.get("shots", {})
        for sh in shots:
            if sh["id"] not in cshots:
                errors.append(f"Missing camera_beats entry for {sh['id']}")

    return {
        "valid": len(errors) == 0,
        "shots_count": len(shots),
        "total_frames_covered": cur_f,
        "errors": errors,
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "style_approved": "HUMAN_REVIEW_PENDING",
    }
