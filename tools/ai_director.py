#!/usr/bin/env python3
"""
tools/ai_director.py - Gemini AI Story & Battle Director (V13)
QA-Unified-Video-Studio V13

- Grounded AI Director generating shot-level visual choreography, camera intent, and SFX cues.
- Strict source-grounding against spoken script text (no hallucinated events).
- Semantic polarity tagging: AFFIRMED, NEGATED, HYPOTHETICAL, PERCEIVED.
- Actor attribution: roman vs opponent vs neutral.
- Offline rule-based fallback when Gemini API is unconfigured or unavailable.
- Manual shot protection: Shots marked with visual_source='manual' are 100% immutable.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic import BaseModel, Field, ValidationError

from tools.common import canonical_json_serialize, read_json, write_json
from tools.gemini_client import (
    classify_gemini_failure,
    list_supported_director_models,
    request_structured_with_fallback,
)
from tools.global_settings import get_api_key_securely, load_global_settings, redact_secrets
from tools.cinematic_camera import (
    CinematicShotPlan,
    plan_camera_sequence,
    compile_camera_keyframes,
    validate_camera_sequence,
    audit_camera_grammar,
    camera_plan_digest,
)

DIRECTOR_PLAN_VERSION = "14.2"


class SfxIntent(BaseModel):
    intent: str
    time_offset: float = 0.0
    intensity: Literal["low", "medium", "high"] = "medium"
    priority: int = 1


class DirectorShot(BaseModel):
    shot_id: str
    script_span: str
    polarity: Literal["AFFIRMED", "NEGATED", "HYPOTHETICAL", "PERCEIVED"] = "AFFIRMED"
    actor: Literal["roman", "opponent", "neutral", "unknown"] = "unknown"
    action_beat: str
    camera_intent: str = "medium"  # close, medium, wide, top, dynamic_follow
    body_motion: str = "stand"     # charge, collision, stand, retreat, encircle, relief, hold, advance
    sfx_intents: List[SfxIntent] = Field(default_factory=list)
    uncertainty: float = 0.0
    source_grounding: Dict[str, Any] = Field(default_factory=dict)
    camera_plan: Optional[CinematicShotPlan] = None


class DirectorPlan(BaseModel):
    version: str = DIRECTOR_PLAN_VERSION
    project_id: str
    generation_source: str  # gemini_live | gemini_fallback | offline_grounded_rule_fallback
    model_used: Optional[str] = None
    created_at: float
    shots: List[DirectorShot]


# Semantic Polarity and Actor Patterns
_PERCEIVED_PATTERN = re.compile(
    r"\b(thought\s+(?:they|he|the\s+enemy|the\s+warlord|the\s+barbarians)|"
    r"seemed\s+(?:like|to\s+be)?|what\s+seemed\s+like|believed\s+(?:they|he)|"
    r"appeared\s+(?:to|like)|feigned|pretended|imagined|assumed)\b",
    re.IGNORECASE,
)

_HYPOTHETICAL_PATTERN = re.compile(
    r"\b(what\s+if|if\s+they|had\s+they|could\s+have|might\s+have|suppose|assuming|n\u1ebfu|gi\u1ea3\s+s\u1eed)\b",
    re.IGNORECASE,
)

_NEGATION_PATTERN = re.compile(
    r"\b(could\s+not|can\s*not|never|nobody|no\s+one|did\s+not|without|refused\s+to|"
    r"hardly|scarcely|couldn't|can't|didn't|won't|unable\s+to|failed\s+to|impossible\s+to|"
    r"not\s+a|line\s+held|firmly|kh\u00f4ng\s+th\u1ec3|kh\u00f4ng\s+bao\s+gi\u1edd|ch\u01b0a\s+t\u1eebng|kh\u00f4ng)\b",
    re.IGNORECASE,
)

_OPPONENT_PATTERN = re.compile(
    r"\b(warlords?|chieftains?|gauls?|barbarians?|carthaginians?|enemies|enemy|hannibal|opponents?|invaders?|attacker|attackers)\b",
    re.IGNORECASE,
)

_ROMAN_PATTERN = re.compile(
    r"\b(romans?|legion(?:naires?|s)?|consuls?|centurions?|hastati|principes|triarii|cohorts?|defenders?)\b",
    re.IGNORECASE,
)


def extract_grounded_story_facts(shots: List[Dict[str, Any]], script_text: str) -> List[Dict[str, Any]]:
    """Extract grounded factual and polarity statements from shot lines and script text."""
    facts = []
    text_clean = script_text.lower()
    
    for s in shots:
        sid = s.get("id", "")
        line = s.get("line", "")
        scene = s.get("scene", "")
        combined = f"{line} {scene}".strip()
        combined_lower = combined.lower()
        
        # Determine polarity
        polarity = "AFFIRMED"
        if _PERCEIVED_PATTERN.search(combined):
            polarity = "PERCEIVED"
        elif _NEGATION_PATTERN.search(combined):
            polarity = "NEGATED"
        elif _HYPOTHETICAL_PATTERN.search(combined):
            polarity = "HYPOTHETICAL"
            
        # Determine actor
        has_opp = bool(_OPPONENT_PATTERN.search(combined_lower))
        has_rom = bool(_ROMAN_PATTERN.search(combined_lower))
        if has_opp and not has_rom:
            actor = "opponent"
        elif has_rom and not has_opp:
            actor = "roman"
        elif has_opp and has_rom:
            # Check who is the grammatical subject / first mentioned actor
            opp_match = _OPPONENT_PATTERN.search(combined_lower)
            rom_match = _ROMAN_PATTERN.search(combined_lower)
            actor = "opponent" if (opp_match and rom_match and opp_match.start() < rom_match.start()) else "roman"
        else:
            actor = "unknown"

        # Find grounding offset in full script text
        quote = line if line else combined
        start_char = text_clean.find(quote.lower()[:30]) if quote else -1
        end_char = start_char + len(quote) if start_char != -1 else -1

        is_bt_claim = bool(re.search(r"\b(break|broke|broken|breakthrough|gap)\b", combined_lower))
        facts.append({
            "shot_id": sid,
            "script_span": quote,
            "polarity": polarity,
            "actor": actor,
            "quote": quote,
            "start_char": max(0, start_char),
            "end_char": max(0, end_char),
            "is_breakthrough_claim": is_bt_claim,
            "is_literal_fact": (polarity == "AFFIRMED"),
        })
    return facts


def build_director_context(project_path: Union[str, Path], shot_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Gather project story, script, config, and manual locks for AI Director context."""
    p = Path(project_path).resolve()
    cfg_file = p / "config.json"
    cfg = read_json(cfg_file, {}) or {}
    
    story_file = p / "story" / "shots.json"
    story = read_json(story_file, {}) or {}
    all_shots = story.get("shots", [])
    
    if shot_ids:
        shots = [s for s in all_shots if s.get("id") in shot_ids]
    else:
        shots = all_shots

    # Read script texts
    script_text = ""
    for cand in (p / "input" / "voice_script.txt", p / "input" / "01-PHIM.txt"):
        if cand.exists():
            script_text = cand.read_text(encoding="utf-8", errors="replace")
            break
            
    manual_locked_ids = [s.get("id") for s in all_shots if s.get("visual_source") == "manual"]
    
    return {
        "project_id": p.name,
        "project_path": str(p),
        "pack": cfg.get("pack", "squire"),
        "aspect": cfg.get("aspect", "16:9"),
        "resolution": cfg.get("resolution", "1080p"),
        "title": cfg.get("title", ""),
        "total_duration": float(story.get("duration", 30.0)),
        "shots": shots,
        "manual_locked_ids": manual_locked_ids,
        "script_text": script_text,
    }


def _generate_offline_grounded_plan(ctx: Dict[str, Any]) -> DirectorPlan:
    """Deterministic offline director plan grounded in script semantics."""
    shots = ctx.get("shots", [])
    script_text = ctx.get("script_text", "")
    facts = extract_grounded_story_facts(shots, script_text)
    facts_by_id = {f["shot_id"]: f for f in facts}
    pack = ctx.get("pack", "squire")
    aspect = ctx.get("aspect", "16:9")
    camera_plans = plan_camera_sequence(shots, config={"pack": pack, "aspect": aspect})
    camera_plans_by_id = {cp.shot_id: cp for cp in camera_plans}
    
    director_shots: List[DirectorShot] = []
    
    for idx, s in enumerate(shots):
        sid = s.get("id", f"s{idx+1:03d}")
        f = facts_by_id.get(sid, {
            "polarity": "AFFIRMED",
            "actor": "unknown",
            "script_span": s.get("line", ""),
            "quote": s.get("line", ""),
            "start_char": 0,
            "end_char": 0,
        })
        
        line_lower = (s.get("line", "") + " " + s.get("scene", "")).lower()
        
        # Determine body motion & camera intent
        body_motion = "stand"
        camera_intent = "medium"
        sfx_intents = []
        
        if "charge" in line_lower or "rush" in line_lower or "advance" in line_lower:
            body_motion = "charge" if "charge" in line_lower else "advance"
            camera_intent = "wide" if idx % 2 == 0 else "dynamic_follow"
            sfx_intents.append(SfxIntent(intent="armor_movement", time_offset=0.2, intensity="medium"))
        elif "clash" in line_lower or "impact" in line_lower or "struck" in line_lower:
            body_motion = "collision"
            camera_intent = "close"
            sfx_intents.append(SfxIntent(intent="shield_bash", time_offset=0.3, intensity="high", priority=1))
        elif "break" in line_lower or "gap" in line_lower:
            body_motion = "hold" if f["polarity"] in ("PERCEIVED", "NEGATED") else "breakthrough"
            camera_intent = "top"
            sfx_intents.append(SfxIntent(intent="spear_hit", time_offset=0.4, intensity="high"))
        elif "relie" in line_lower or "reserve" in line_lower or "second line" in line_lower:
            body_motion = "relief"
            camera_intent = "wide"
            sfx_intents.append(SfxIntent(intent="war_horn", time_offset=0.1, intensity="medium"))
        elif "flank" in line_lower or "surround" in line_lower or "encircle" in line_lower:
            body_motion = "encircle"
            camera_intent = "top"
            sfx_intents.append(SfxIntent(intent="swords_clashing", time_offset=0.3, intensity="high"))
        else:
            body_motion = "hold" if f["polarity"] == "NEGATED" else "stand"
            camera_intent = "medium" if pack == "squire" else "focus"

        cp_for_shot = camera_plans_by_id.get(sid)

        director_shots.append(DirectorShot(
            shot_id=sid,
            script_span=f["script_span"],
            polarity=f["polarity"],
            actor=f["actor"],
            action_beat=s.get("scene", s.get("line", body_motion)),
            camera_intent=camera_intent,
            body_motion=body_motion,
            sfx_intents=sfx_intents,
            uncertainty=0.1 if f["actor"] != "unknown" else 0.4,
            source_grounding={"quote": f["quote"], "start_char": f["start_char"], "end_char": f["end_char"]},
            camera_plan=cp_for_shot,
        ))

    return DirectorPlan(
        version=DIRECTOR_PLAN_VERSION,
        project_id=ctx.get("project_id", "project"),
        generation_source="offline_grounded_rule_fallback",
        model_used=None,
        created_at=time.time(),
        shots=director_shots,
    )


def generate_director_plan(
    project_path: Union[str, Path],
    shot_ids: Optional[List[str]] = None,
    mock_provider: Optional[Callable[[str, str, Any, int], Dict[str, Any]]] = None,
    offline: bool = False,
) -> Dict[str, Any]:
    """
    Generate structured AI Director plan for a project using Gemini with 3-strike fallback.
    Falls back gracefully to offline grounded rule generator if Gemini API is unavailable.
    """
    ctx = build_director_context(project_path, shot_ids=shot_ids)
    shots = ctx.get("shots", [])
    if not shots:
        return {"status": "NO_SHOTS", "plan": None, "message": "No storyboard shots found."}

    if offline:
        offline_plan = _generate_offline_grounded_plan(ctx)
        return {
            "status": "FALLBACK_OFFLINE",
            "source": offline_plan.generation_source,
            "model_used": None,
            "model_path": [],
            "attempts": 0,
            "retries": 0,
            "reason_codes": [],
            "plan": offline_plan.model_dump(),
        }

    facts = extract_grounded_story_facts(shots, ctx.get("script_text", ""))
    
    prompt = f"""You are the AI Director for a historical battle animation studio.
Project: {ctx.get('project_id')} | Pack: {ctx.get('pack')} | Aspect: {ctx.get('aspect')}
Total shots: {len(shots)}

Grounding Rules:
1. ONLY describe actions mentioned or implied by the spoken script. Do NOT hallucinate fantasy events.
2. POLARITY:
   - If narration says 'They thought they had broken the line' or 'What seemed like a breakthrough', set polarity='PERCEIVED'.
   - If narration contains 'not', 'never', 'did not break', set polarity='NEGATED'.
   - If conditional 'if they broke', set polarity='HYPOTHETICAL'.
   - Else set polarity='AFFIRMED'.
3. ACTOR:
   - 'The warlord orders full charge' -> actor='opponent'.
   - 'Legionnaires' or 'Roman reserve' -> actor='roman'.
   - Neutral or uncertain -> actor='unknown'.
4. CAMERA INTENT: choose from 'close', 'medium', 'wide', 'top', 'dynamic_follow'.
5. BODY MOTION: choose from 'charge', 'collision', 'stand', 'retreat', 'encircle', 'relief', 'hold', 'advance'.

Story facts:
{json.dumps(facts, indent=2)}

Output JSON adhering to the DirectorPlan schema.
"""

    # Attempt structured request via Gemini client
    res = request_structured_with_fallback(prompt, DirectorPlan, ctx=ctx, mock_provider=mock_provider)
    
    if res.get("status") == "SUCCESS" and res.get("plan"):
        plan_dict = res["plan"]
        plan_dict["generation_source"] = "gemini_live" if mock_provider is None else "gemini_mock"
        plan_dict["model_used"] = res.get("used_model")
        return {
            "status": "SUCCESS",
            "source": plan_dict["generation_source"],
            "model_used": res.get("used_model"),
            "model_path": res.get("model_path"),
            "attempts": res.get("attempts"),
            "retries": res.get("retries"),
            "plan": plan_dict,
        }
    else:
        # Fallback to offline rule-based generator
        print(f"[ai_director] Gemini call unavailable ({res.get('error')}). Using offline grounded fallback plan.", file=sys.stderr)
        offline_plan = _generate_offline_grounded_plan(ctx)
        return {
            "status": "FALLBACK_OFFLINE",
            "source": offline_plan.generation_source,
            "model_used": None,
            "model_path": res.get("model_path", []),
            "attempts": res.get("attempts", 0),
            "retries": res.get("retries", 0),
            "reason_codes": res.get("reason_codes", []),
            "plan": offline_plan.model_dump(),
        }


def validate_director_plan(plan: Union[Dict[str, Any], DirectorPlan], project_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """Validate DirectorPlan against project constraints, shot existence, and manual protections."""
    errors = []
    if isinstance(plan, DirectorPlan):
        p_dict = plan.model_dump()
    else:
        p_dict = plan
        
    p = Path(project_path).resolve()
    story = read_json(p / "story" / "shots.json", {}) or {}
    project_shots = {s.get("id"): s for s in story.get("shots", [])}
    
    plan_shots = p_dict.get("shots", [])
    if not isinstance(plan_shots, list) or not plan_shots:
        errors.append("Director plan must contain a non-empty list of shots.")
        return False, errors
        
    for idx, ps in enumerate(plan_shots):
        sid = ps.get("shot_id")
        if not sid or sid not in project_shots:
            errors.append(f"Shot {idx}: shot_id '{sid}' does not exist in project storyboard.")
        pol = ps.get("polarity")
        if pol not in ("AFFIRMED", "NEGATED", "HYPOTHETICAL", "PERCEIVED"):
            errors.append(f"Shot {sid}: Invalid polarity '{pol}'.")
        actor = ps.get("actor")
        if actor not in ("roman", "opponent", "neutral", "unknown"):
            errors.append(f"Shot {sid}: Invalid actor '{actor}'.")
            
    return len(errors) == 0, errors


def compile_director_plan_to_visuals(
    plan_dict: Any,
    project_path: Any,
    aspect: str = "16:9",
    pack: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Compile DirectorPlan into storyboard shot parameters with real executable motion args.
    CRITICAL: Preserves manual shots (visual_source == 'manual' or manual == True) byte-for-byte!
    Returns: (compiled_shots, changed_count)
    """
    if hasattr(plan_dict, "model_dump"):
        plan_dict = plan_dict.model_dump()

    if isinstance(project_path, (list, tuple)):
        shots = copy.deepcopy(list(project_path))
        detected_pack = pack or (shots[0].get("pack") if shots and isinstance(shots[0], dict) else None)
        if not detected_pack:
            # Check if shots have dem characteristics
            is_dem = any(
                isinstance(s, dict) and (s.get("id", "").startswith("d") or "actors" in s.get("args", {}) or s.get("args", {}).get("set"))
                for s in shots
            )
            detected_pack = "dem" if is_dem else "squire"
        cfg = {"aspect": aspect, "pack": detected_pack}
    else:
        p = Path(project_path).resolve()
        story_file = p / "story" / "shots.json"
        story = read_json(story_file, {}) or {}
        shots = copy.deepcopy(story.get("shots", []))
        cfg = read_json(p / "config.json", {})
        if pack:
            cfg["pack"] = pack
        aspect = cfg.get("aspect", aspect)
    
    plan_shots_by_id = {s.get("shot_id"): s for s in plan_dict.get("shots", [])}
    changed_count = 0
    plan_hash = hashlib.sha256(canonical_json_serialize(plan_dict).encode("utf-8")).hexdigest()[:12]
    
    pack = cfg.get("pack", "squire")
    
    # Detect genre for appropriate aesthetic/presets (Samurai, Knight, Roman)
    raw_genre = (str(cfg.get("genre") or "") + " " + str(cfg.get("theme") or "")).lower()
    script_snippet = " ".join([
        (s.get("line") or "") + " " + (s.get("scene") or "")
        for s in shots
    ]).lower()

    if any(k in raw_genre or k in script_snippet for k in ("samurai", "katana", "shogun", "bushido", "ashigaru", "ronin", "daimyo", "sengoku", "edo")):
        genre = "samurai"
    elif any(k in raw_genre or k in script_snippet for k in ("knight", "medieval", "crusade", "chivalry", "feudal", "castle", "french", "norman", "english")):
        genre = "knight"
    else:
        genre = "roman"

    # Plan holistic camera sequence across the ENTIRE sequence of shots once upfront
    full_camera_plans = plan_camera_sequence(
        shots,
        director_plan=plan_dict,
        config=cfg,
        aspect=aspect,
    )
    full_camera_plans_by_id = {cp.shot_id: cp for cp in full_camera_plans}

    for s in shots:
        sid = s.get("id")
        # 1. Byte-for-byte manual lock protection
        if s.get("visual_source") == "manual" or s.get("manual") is True or s.get("camera_manual_lock") is True:
            continue
            
        if sid in plan_shots_by_id or sid in full_camera_plans_by_id:
            ps = plan_shots_by_id.get(sid, {})
            bm = ps.get("body_motion", "stand")
            cam = ps.get("camera_intent", "medium")
            pol = ps.get("polarity", "AFFIRMED")
            act = ps.get("actor", "unknown")
            dur = float(s.get("dur", 3.0))
            
            # Extract or synthesize full-video cinematic camera plan
            cp_plan = ps.get("camera_plan")
            if not cp_plan and sid in full_camera_plans_by_id:
                cp_plan = full_camera_plans_by_id[sid].model_dump()
            elif hasattr(cp_plan, "model_dump"):
                cp_plan = cp_plan.model_dump()

            cp_view = cp_plan.get("viewpoint", "front") if isinstance(cp_plan, dict) else "front"
            cp_scale = cp_plan.get("scale", "medium") if isinstance(cp_plan, dict) else "medium"

            # Map camera intent and viewpoint to template based on pack
            if pack == "squire":
                if cp_view == "top_down" or cam == "top" or bm in ("relief", "encircle"):
                    chosen_tpl = "top"
                    s["camera"] = "in"
                elif cp_scale in ("close", "extreme_close") or (cam == "close" and not cp_view.startswith("profile")):
                    chosen_tpl = "close"
                    s["camera"] = "pan"
                elif cp_scale in ("wide", "extreme_wide") or (bm in ("charge", "advance") and cp_view in ("front", "profile_left", "profile_right")):
                    chosen_tpl = "army"
                    s["camera"] = "right"
                else:
                    chosen_tpl = s.get("tpl") or s.get("template") or "scene"
            else:
                # DEM / other pack
                chosen_tpl = s.get("tpl") or s.get("template") or "scene"
                
            s["tpl"] = chosen_tpl
            s["template"] = chosen_tpl
            
            # Build real executable animation args
            args = copy.deepcopy(s.get("args") or {})
            if cp_plan and isinstance(cp_plan, dict):
                compiled_cam = compile_camera_keyframes(
                    CinematicShotPlan(**cp_plan),
                    dur=dur,
                    aspect=cfg.get("aspect", aspect),
                )
                args["cameraRig"] = compiled_cam["cameraRig"]
                args["view"] = cp_view
                args["move"] = compiled_cam["move"]
                args["moveAmt"] = compiled_cam["moveAmt"]
            if pack == "squire":
                args["bg"] = args.get("bg", "plain")
                args["time"] = args.get("time", "golden")
                
                if chosen_tpl == "top":
                    # Tactical bird's-eye blocks with paths and continuous kinematics
                    blocks = []
                    # Blue ally block
                    if genre == "samurai":
                        ally_label = "SHOGUN"
                        enemy_label = "RONIN" if act == "opponent" else "CLAN"
                    elif genre == "knight":
                        ally_label = "CHIVALRY"
                        enemy_label = "INVADER" if act == "opponent" else "BARON"
                    else:
                        ally_label = "LEGIO"
                        enemy_label = "WARLORD" if act == "opponent" else "ENEMY"

                    blocks.append({
                        "side": "blue",
                        "label": ally_label,
                        "w": 0.32,
                        "h": 0.10,
                        "path": [[0.0, 0.48, 0.62], [dur, 0.48, 0.58]],
                        "gap": {"at": round(0.35 * dur, 2), "w": 0.08} if pol == "PERCEIVED" else None,
                    })
                    # Red opposing block
                    opp_path = [[0.0, 0.52, 0.28], [dur, 0.52, 0.45]] if bm in ("charge", "advance") else [[0.0, 0.52, 0.35], [dur, 0.52, 0.38]]
                    blocks.append({
                        "side": "red",
                        "label": enemy_label,
                        "w": 0.35,
                        "h": 0.12,
                        "path": opp_path,
                        "impactAt": round(0.4 * dur, 2) if bm in ("collision", "charge") else None,
                    })
                    args["blocks"] = blocks
                    
                    if bm in ("flank", "encircle"):
                        args["arrows"] = [{
                            "kind": "curve",
                            "pts": [[0.22, 0.62], [0.12, 0.45], [0.32, 0.36]],
                            "color": "#e63c32",
                            "dur": round(0.7 * dur, 2),
                        }]
                    if bm == "collision":
                        args["dust"] = [{"x": 0.50, "y": 0.48, "s": 0.14, "at": round(0.38 * dur, 2)}]
                        
                elif chosen_tpl == "army":
                    # Moving army formations with front/side marching
                    march_mode = "front" if bm in ("advance", "charge") else ("side" if cam in ("wide", "right") else True)
                    if genre == "samurai":
                        mid_preset = "samurai" if act != "opponent" else "ronin"
                        back_preset = "ashigaru"
                    elif genre == "knight":
                        mid_preset = "knight14" if act != "opponent" else "frenchKnight"
                        back_preset = "englishArcher"
                    else:
                        mid_preset = "hastatus" if act != "opponent" else "warlord"
                        back_preset = "warlord" if act == "roman" else "latin"

                    args["mid"] = [{
                        "preset": mid_preset,
                        "rows": 4,
                        "cols": 10,
                        "x0": 0.04,
                        "x1": 0.96,
                        "yFront": 0.96,
                        "yBack": 0.74,
                        "hFront": 0.38,
                        "hBack": 0.18,
                        "march": march_mode,
                        "flip": False if act != "opponent" else True,
                        "face": "fierce" if bm in ("charge", "collision") else "neutral",
                    }]
                    args["back"] = [{
                        "preset": back_preset,
                        "rows": 3,
                        "cols": 20,
                        "x0": 0.0,
                        "x1": 1.0,
                        "yFront": 0.72,
                        "yBack": 0.64,
                        "hFront": 0.08,
                        "hBack": 0.05,
                        "flip": True if act != "opponent" else False,
                    }]
                    if bm in ("throw", "advance"):
                        args["fx"] = [{"kind": "javelins", "at": round(0.3 * dur, 2)}]
                    elif bm == "collision":
                        args["fx"] = [{"kind": "dust", "at": round(0.35 * dur, 2)}]
                    args["move"] = "right" if cam == "pan" else "in"
                    
                elif chosen_tpl == "close":
                    # Close hero bust with true 2D viewpoint
                    if genre == "samurai":
                        hero_preset = "samurai" if act != "opponent" else "ronin"
                        other_preset = "ronin" if act == "roman" else "samurai"
                    elif genre == "knight":
                        hero_preset = "knight15" if act != "opponent" else "frenchKnight"
                        other_preset = "frenchKnight" if act == "roman" else "knight14"
                    else:
                        hero_preset = "centurion" if act == "roman" else ("warlord" if act == "opponent" else "hastatus")
                        other_preset = "warlord" if act == "roman" else "hastatus"

                    args["preset"] = hero_preset
                    args["face"] = "fierce" if bm in ("charge", "collision") else ("shock" if pol == "PERCEIVED" else "neutral")
                    args["pose"] = "attack" if bm == "collision" else ("defend" if bm == "shield_wall" else "stand")
                    args["talk"] = bool(len(s.get("line", "")) > 18)
                    args["view"] = cp_view

                    if cp_view.startswith("over_shoulder"):
                        # True Over-The-Shoulder cinematic staging
                        # Balanced Over-The-Shoulder cinematic staging (unobscured view, no giant helmet)
                        if cp_view == "over_shoulder_right":
                            args["x"] = 0.84
                            args["y"] = 0.78
                            args["R"] = 0.24
                            args["view"] = "rear"
                            args["others"] = [{
                                "preset": other_preset,
                                "x": 0.36,
                                "y": 0.48,
                                "R": 0.22,
                                "view": "front",
                                "main": False,
                                "face": "fierce",
                            }]
                        else:
                            args["x"] = 0.16
                            args["y"] = 0.78
                            args["R"] = 0.24
                            args["view"] = "rear"
                            args["others"] = [{
                                "preset": other_preset,
                                "x": 0.64,
                                "y": 0.48,
                                "R": 0.22,
                                "view": "front",
                                "main": False,
                                "face": "fierce",
                            }]
                    if bm == "collision":
                        args["fx"] = [{"kind": "sparks", "at": round(0.3 * dur, 2)}]
                    args["move"] = "in"
                    
                else:
                    # Scene: foreground moving character + depth formations
                    move_pose = "march" if bm in ("advance", "march") else ("run" if bm == "charge" else ("attack" if bm == "collision" else "stand"))
                    from_x = 0.30 if act != "opponent" else 0.70
                    to_x = 0.55 if act != "opponent" else 0.45
                    args["view"] = cp_view
                    if genre == "samurai":
                        scene_preset = "samurai" if act != "opponent" else "ronin"
                        scene_weapon = "katana"
                        back_preset = "ashigaru"
                    elif genre == "knight":
                        scene_preset = "knight15" if act != "opponent" else "frenchKnight"
                        scene_weapon = "sword" if bm != "throw" else "pollaxe"
                        back_preset = "knight14"
                    else:
                        scene_preset = "hastatus" if act != "opponent" else "warlord"
                        scene_weapon = "pilum" if bm == "throw" else "gladius"
                        back_preset = "hastatus"

                    args["people"] = [{
                        "preset": scene_preset,
                        "x": from_x,
                        "y": 0.88,
                        "h": 0.58,
                        "pose": move_pose,
                        "walk": True if bm in ("advance", "charge", "march") else None,
                        "from": from_x,
                        "to": to_x,
                        "moveAt": round(0.15 * dur, 2),
                        "dur": round(0.65 * dur, 2),
                        "face": "fierce" if bm in ("charge", "collision") else "neutral",
                        "weapon": scene_weapon,
                        "flip": bool(act == "opponent"),
                        "view": cp_view,
                    }]
                    args["back"] = [{
                        "preset": back_preset,
                        "rows": 3,
                        "cols": 16,
                        "x0": 0.0,
                        "x1": 1.0,
                        "yFront": 0.75,
                        "yBack": 0.65,
                        "hFront": 0.12,
                        "hBack": 0.06,
                        "march": True,
                    }]
                    if bm == "collision":
                        args["fx"] = [{"kind": "dust", "at": round(0.35 * dur, 2)}]
                    elif bm == "throw":
                        args["fx"] = [{"kind": "javelins", "at": round(0.25 * dur, 2)}]
            else:
                # DEM pack (Self-Improvement SILENT)
                args["set"] = args.get("set", "void")
                dem_pose = "stand" if bm == "stand" else ("phone" if bm == "phone" else ("slump" if bm == "slump" else "walk"))
                
                if cp_view.startswith("over_shoulder"):
                    if cp_view == "over_shoulder_right":
                        bg_actor = {
                            "who": "hero",
                            "x": 0.36,
                            "y": 0.72,
                            "h": 0.40,
                            "pose": dem_pose,
                            "view": "three_quarter_right",
                            "face": "neutral" if pol == "AFFIRMED" else "tired",
                        }
                        fg_actor = {
                            "who": "other",
                            "x": 0.80,
                            "y": 0.84,
                            "h": 0.62,
                            "pose": "stand",
                            "view": "rear",
                            "face": "neutral",
                        }
                    else:
                        bg_actor = {
                            "who": "hero",
                            "x": 0.64,
                            "y": 0.72,
                            "h": 0.40,
                            "pose": dem_pose,
                            "view": "three_quarter_left",
                            "face": "neutral" if pol == "AFFIRMED" else "tired",
                        }
                        fg_actor = {
                            "who": "other",
                            "x": 0.20,
                            "y": 0.84,
                            "h": 0.62,
                            "pose": "stand",
                            "view": "rear",
                            "face": "neutral",
                        }
                    args["actors"] = [bg_actor, fg_actor]
                else:
                    actor_obj = {
                        "who": "hero",
                        "x": 0.35,
                        "y": 0.76,
                        "h": 0.42,
                        "pose": dem_pose,
                        "view": cp_view,
                        "face": "neutral" if pol == "AFFIRMED" else "tired",
                    }
                    if bm in ("walk", "advance", "charge"):
                        actor_obj["walk"] = {
                            "to": 0.65,
                            "at": round(0.15 * dur, 2),
                            "dur": round(0.65 * dur, 2),
                            "speed": 1.0,
                        }
                    args["actors"] = [actor_obj]

                args["view"] = cp_view
                if cp_plan and isinstance(cp_plan, dict):
                    compiled_cam = compile_camera_keyframes(
                        CinematicShotPlan(**cp_plan),
                        dur=dur,
                        aspect=cfg.get("aspect", aspect),
                    )
                    args["cameraRig"] = compiled_cam["cameraRig"]
                    first_kf = compiled_cam["cameraRig"]["keyframes"][0]
                    last_kf = compiled_cam["cameraRig"]["keyframes"][-1]
                    args["cam"] = {
                        "from": [first_kf["x"], first_kf["y"], first_kf["z"]],
                        "to": [last_kf["x"], last_kf["y"], last_kf["z"]],
                        "at": 0,
                        "dur": dur,
                    }
                    args["move"] = compiled_cam["move"]
                    args["moveAmt"] = compiled_cam["moveAmt"]
                beat_text = ps.get("action_beat") or s.get("line", "")[:45]
                args["texts"] = [{"kind": "narr", "t": beat_text, "at": round(0.2 * dur, 2)}]
                
            s["args"] = args
            s["action"] = bm
            s["polarity"] = pol
            s["actor"] = act
            s["visual_source"] = "gemini_director_v14"
            s["ai_plan_hash"] = plan_hash
            s["director_beat"] = ps.get("action_beat", "")
            s["execution_trace"] = {
                "source_quote": ps.get("source_quote", s.get("line", "")),
                "shot_id": sid,
                "actor": act,
                "polarity": pol,
                "action": bm,
                "template": chosen_tpl,
                "viewpoint": cp_view,
                "camera_scale": cp_scale,
                "camera_rig_active": ("cameraRig" in args),
                "has_motion_args": True,
            }
            
            # If SFX intents present, attach metadata
            if ps.get("sfx_intents"):
                s["director_sfx_cues"] = ps["sfx_intents"]
                
            changed_count += 1
            
    return shots, changed_count


def apply_director_plan_generated_only(
    plan_dict: Dict[str, Any],
    project_path: Union[str, Path],
) -> Dict[str, Any]:
    """
    Atomically apply DirectorPlan to project shots, backing up previous shots.
    Rolls back on error.
    """
    p = Path(project_path).resolve()
    is_valid, errors = validate_director_plan(plan_dict, p)
    if not is_valid:
        return {"status": "VALIDATION_FAILED", "errors": errors, "changed_shots_count": 0}
        
    story_file = p / "story" / "shots.json"
    backup_file = p / "story" / "shots.json.bak_director"
    
    try:
        story = read_json(story_file, {}) or {}
        # Backup original
        write_json(backup_file, story)
        
        compiled_shots, changed_count = compile_director_plan_to_visuals(plan_dict, p)
        story["shots"] = compiled_shots
        story["director_metadata"] = {
            "applied_at": time.time(),
            "generation_source": plan_dict.get("generation_source"),
            "model_used": plan_dict.get("model_used"),
            "changed_shots_count": changed_count,
        }
        
        # Atomic write
        write_json(story_file, story)
        
        # Save build artifacts
        build_dir = p / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        write_json(build_dir / "director_plan.json", plan_dict)
        write_json(build_dir / "director_review.json", {
            "status": "APPLIED",
            "applied_at": time.time(),
            "model_used": plan_dict.get("model_used"),
            "generation_source": plan_dict.get("generation_source"),
            "changed_shots_count": changed_count,
        })
        
        return {
            "status": "APPLIED",
            "changed_shots_count": changed_count,
            "model_used": plan_dict.get("model_used"),
            "generation_source": plan_dict.get("generation_source"),
        }
    except Exception as exc:
        # Rollback
        if backup_file.exists():
            shutil.copyfile(backup_file, story_file)
        return {"status": "ERROR", "error": str(exc), "changed_shots_count": 0}


def build_full_video_cinematic_camera_plan(
    project_path: Union[str, Path],
    director_plan: Optional[Dict[str, Any]] = None,
) -> List[CinematicShotPlan]:
    """
    Author and validate a holistic, narrative-motivated camera plan across the entire timeline.
    Works for both Gemini and offline plan.
    """
    p = Path(project_path).resolve()
    story_file = p / "story" / "shots.json"
    story = read_json(story_file, {}) or {}
    shots = story.get("shots", [])
    cfg = read_json(p / "config.json", {})
    return plan_camera_sequence(shots, director_plan=director_plan, config=cfg)


def review_director_plan(project_path: Union[str, Path]) -> Dict[str, Any]:
    """Generate and review DirectorPlan without mutating storyboard files."""
    p = Path(project_path).resolve()
    res = generate_director_plan(p)
    if res.get("status") in ("SUCCESS", "FALLBACK_OFFLINE") and res.get("plan"):
        plan = res["plan"]
        valid, errors = validate_director_plan(plan, p)
        return {
            "status": "REVIEWED" if valid else "VALIDATION_ERROR",
            "generation_source": res.get("source"),
            "model_used": res.get("model_used"),
            "valid": valid,
            "errors": errors,
            "plan": plan,
        }
    return {
        "status": "AI_UNAVAILABLE",
        "error": res.get("error", "Unable to generate director plan"),
        "plan": None,
    }


def main():
    parser = argparse.ArgumentParser(description="Gemini AI Story & Battle Director (V13)")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--review", action="store_true", help="Generate and review plan without applying")
    parser.add_argument("--apply", action="store_true", help="Generate and apply plan to storyboard")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing build/director_plan.json")
    args = parser.parse_args()
    
    p = Path(args.project).resolve()
    if args.validate_only:
        plan_file = p / "build" / "director_plan.json"
        if not plan_file.exists():
            print(f"Error: {plan_file} does not exist.")
            sys.exit(1)
        plan = read_json(plan_file)
        valid, errors = validate_director_plan(plan, p)
        print(f"Valid: {valid}, Errors: {errors}")
        sys.exit(0 if valid else 1)
        
    if args.review:
        rev = review_director_plan(p)
        print(json.dumps(rev, indent=2))
        sys.exit(0 if rev.get("valid") else 1)
        
    if args.apply:
        gen = generate_director_plan(p)
        if gen.get("plan"):
            res = apply_director_plan_generated_only(gen["plan"], p)
            print(json.dumps(res, indent=2))
            sys.exit(0 if res.get("status") == "APPLIED" else 1)
        else:
            print("Failed to generate plan.")
            sys.exit(1)

    print("Please specify --review, --apply, or --validate-only.")


if __name__ == "__main__":
    main()
