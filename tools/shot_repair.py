#!/usr/bin/env python3
"""tools/shot_repair.py — Selective Shot Repair Engine & Closed-Loop Video Healer (FL-01 / V14.7.5).

Implements bounded, causal defect remediation for video studio projects:
1. _normalize_qa_report(): typed adapter supporting both TemporalQAReport Pydantic models and dicts;
   fails closed (NOT_VERIFIED) on missing mandatory fields, zero shots, or unknown verdicts.
2. classify_failed_shots(): classifies defects into continuity, camera, actor_preset, pose, prop,
   blank_frame, map_diagram, while preserving manual_locked flags so locked defects are never silently ignored.
3. compute_impacted_shot_dependencies(): computes dependency graph while strictly protecting manual_locked shots.
4. plan_minimal_repair() & apply_generated_only_repairs(): mutates only generated fields without touching manual locks.
5. rerender_affected_shots(): runs real `node render.mjs` (honestly recording FULL_RERENDER_FALLBACK,
   never falsely claiming SELECTIVE_RENDER), muxes real audio atomically, inspects media with full decode,
   and writes cryptographic render_receipt.json.
6. run_targeted_qa() & run_full_final_qa(): passes all 3 canonical arguments to audit_project_temporal_visual.
7. execute_repair_loop(): bounded closed loop returning CLEAN_PASS, REPAIR_SUCCESS, BLOCKED_MANUAL_REVIEW,
   NOT_VERIFIED, or FAIL.
8. test_defect_injection_and_repair(): builds a real disposable 3-shot Squire video with spoken English voice,
   injects real visual + preset + prop defects on generated s02 next to manual_locked s01, renders defective MP4,
   heals via execute_repair_loop, verifies s01 JSON SHA256 preservation, new MP4 SHA256, audio/video decode,
   receipt integrity, and BLOCKED_MANUAL_REVIEW when a locked shot itself is defective.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    inspect_media_file,
    sha256_file,
    validate_cache_hit,
    write_render_receipt_atomic,
)
from tools.temporal_visual_qa import TemporalQAReport, audit_project_temporal_visual

KNOWN_QA_VERDICTS = {
    "VISUAL_TECH_PASS",
    "PASS",
    "FAIL",
    "NOT_VERIFIED",
    "COVERAGE_INCOMPLETE",
}


def canonical_json_sha256(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_qa_report(qa_report: Any) -> Dict[str, Any]:
    """
    Typed adapter converting TemporalQAReport Pydantic model or dict into a validated canonical dict.
    Missing mandatory fields, zero shots, or unknown verdicts return valid_report=False with verdict='NOT_VERIFIED'.
    """
    if isinstance(qa_report, TemporalQAReport):
        raw = qa_report.model_dump()
    elif hasattr(qa_report, "model_dump") and callable(qa_report.model_dump):
        raw = qa_report.model_dump()
    elif isinstance(qa_report, dict):
        raw = dict(qa_report)
    else:
        return {
            "valid_report": False,
            "technical_verdict": "NOT_VERIFIED",
            "reason": f"Unsupported QA report type: {type(qa_report).__name__}",
            "total_shots": 0,
            "shot_audits": {},
            "temporal_issues": [],
            "global_issues": ["Unsupported QA report object"],
        }

    shot_audits = raw.get("shot_audits")
    if not isinstance(shot_audits, dict) or len(shot_audits) == 0:
        return {
            "valid_report": False,
            "technical_verdict": "NOT_VERIFIED",
            "reason": "Missing or empty mandatory field 'shot_audits'",
            "total_shots": int(raw.get("total_shots") or 0),
            "shot_audits": {},
            "temporal_issues": raw.get("temporal_issues") or raw.get("issues") or [],
            "global_issues": raw.get("global_issues") or ["Empty shot_audits"],
        }

    total_shots = int(raw.get("total_shots") if raw.get("total_shots") is not None else len(shot_audits))
    verdict = str(raw.get("technical_verdict") or "NOT_VERIFIED")
    if total_shots <= 0 or verdict not in KNOWN_QA_VERDICTS:
        return {
            "valid_report": False,
            "technical_verdict": "NOT_VERIFIED",
            "reason": f"Invalid total_shots={total_shots} or unknown technical_verdict='{verdict}'",
            "total_shots": total_shots,
            "shot_audits": shot_audits,
            "temporal_issues": raw.get("temporal_issues") or raw.get("issues") or [],
            "global_issues": raw.get("global_issues") or [f"Unrecognized verdict: {verdict}"],
        }

    issues = raw.get("temporal_issues")
    if issues is None:
        issues = raw.get("issues", [])

    expected_cuts = int(raw.get("expected_cut_count", max(0, total_shots - 1)))
    audited_cuts = int(raw.get("audited_cut_count", expected_cuts if "full_boundary_coverage" not in raw else 0))
    full_boundary = bool(raw.get("full_boundary_coverage", audited_cuts == expected_cuts))
    global_issues = list(raw.get("global_issues", []))
    if "full_boundary_coverage" in raw and not full_boundary:
        if verdict == "VISUAL_TECH_PASS":
            verdict = "COVERAGE_INCOMPLETE"
        global_issues.append(f"Cut boundary coverage incomplete: {audited_cuts}/{expected_cuts}")

    return {
        "valid_report": True,
        "technical_verdict": verdict,
        "total_shots": total_shots,
        "passed_shots": int(raw.get("passed_shots", 0)),
        "all_passed": bool(raw.get("all_passed", False)),
        "expected_cut_count": expected_cuts,
        "audited_cut_count": audited_cuts,
        "full_boundary_coverage": full_boundary,
        "shot_audits": shot_audits,
        "temporal_issues": list(issues) if isinstance(issues, list) else [],
        "global_issues": global_issues,
    }


def _get_locked_shot_ids(project_dir: Optional[Path | str]) -> Set[str]:
    locked: Set[str] = set()
    if not project_dir:
        return locked
    shots_file = Path(project_dir).resolve() / "story" / "shots.json"
    if not shots_file.is_file():
        return locked
    try:
        data = json.loads(shots_file.read_text(encoding="utf-8"))
        shots = data.get("shots", []) if isinstance(data, dict) else data
        for s in shots:
            if isinstance(s, dict) and (s.get("manual_locked") or s.get("visual_source") == "manual"):
                if s.get("id"):
                    locked.add(str(s["id"]))
    except Exception:
        pass
    return locked


def _infer_categories_from_audit(
    diags: List[str],
    teleport: bool,
    disap: bool,
    non_empty: bool,
) -> List[str]:
    """Identify all defect categories present on a shot so compound defects are repaired in one pass."""
    diag_text = " ".join(diags).lower()
    cats: List[str] = []

    if not non_empty or "blank" in diag_text or "black frame" in diag_text or ("top_ink=" in diag_text and "bot_ink=" in diag_text):
        cats.append("blank_frame")
    if teleport or disap or "teleport" in diag_text or "disappear" in diag_text:
        cats.append("continuity")
    if "camera snap" in diag_text or "snap" in diag_text:
        cats.append("camera")
    if "preset" in diag_text or "unknown_actor_preset" in diag_text or "missing_actor_preset" in diag_text:
        cats.append("actor_preset")
    if "weapon" in diag_text or "shield" in diag_text or "duplicate" in diag_text:
        cats.append("prop")
    if "posture" in diag_text or "acting" in diag_text or "pose" in diag_text or "center of mass" in diag_text:
        cats.append("pose")
    if "map" in diag_text or "diagram" in diag_text or "tactical" in diag_text or "mobile downscale" in diag_text:
        cats.append("map_diagram")

    if not cats:
        cats.append("unknown")
    return cats


def classify_failed_shots(
    qa_report: Any,
    project_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    """
    Classify failures from Temporal QA / Visual QA into actionable root causes.
    Unknown verdicts != PASS. Failed manual_locked shots are flagged explicitly (`manual_locked=True`)
    rather than silently dropped.
    """
    norm = _normalize_qa_report(qa_report)
    if not norm["valid_report"]:
        return [
            {
                "shot_id": "__REPORT_INVALID__",
                "category": "not_verified",
                "categories": ["not_verified"],
                "verdict": "NOT_VERIFIED",
                "manual_locked": False,
                "diagnostics": [norm.get("reason", "Invalid QA report")],
            }
        ]

    locked_ids = _get_locked_shot_ids(project_dir)
    classified: List[Dict[str, Any]] = []

    for sid, audit in norm["shot_audits"].items():
        if isinstance(audit, dict):
            passed = bool(audit.get("passed", False))
            diags = list(audit.get("diagnostics", []))
            teleport = bool(audit.get("teleport_detected", False))
            disap = bool(audit.get("sudden_disappearance", False))
            non_empty = bool(audit.get("non_empty_content", True))
            verdict = str(audit.get("technical_verdict") or "NOT_VERIFIED")
        else:
            passed = bool(getattr(audit, "passed", False))
            diags = list(getattr(audit, "diagnostics", []))
            teleport = bool(getattr(audit, "teleport_detected", False))
            disap = bool(getattr(audit, "sudden_disappearance", False))
            non_empty = bool(getattr(audit, "non_empty_content", True))
            verdict = str(getattr(audit, "technical_verdict", "NOT_VERIFIED"))

        # Strict truth: ONLY passed=True AND verdict=='VISUAL_TECH_PASS' counts as clean pass
        if passed and verdict == "VISUAL_TECH_PASS":
            continue

        cats = _infer_categories_from_audit(diags, teleport, disap, non_empty)
        classified.append(
            {
                "shot_id": str(sid),
                "category": cats[0],
                "categories": cats,
                "verdict": verdict if verdict in KNOWN_QA_VERDICTS else "NOT_VERIFIED",
                "manual_locked": str(sid) in locked_ids,
                "diagnostics": diags,
            }
        )

    return classified


def compute_impacted_shot_dependencies(
    project_dir: Path | str,
    failed_shot_ids: List[str],
) -> List[str]:
    """
    Identify impacted shot IDs for repair, including adjacent cuts for continuity,
    while strictly excluding manually locked shots from modification.
    """
    p_path = Path(project_dir).resolve()
    shots_file = p_path / "story" / "shots.json"
    if not shots_file.is_file():
        return list(failed_shot_ids)

    try:
        data = json.loads(shots_file.read_text(encoding="utf-8"))
        shots = data.get("shots", []) if isinstance(data, dict) else data
    except Exception:
        return list(failed_shot_ids)

    shot_order = [str(s.get("id")) for s in shots if isinstance(s, dict) and s.get("id")]
    locked_shots = _get_locked_shot_ids(p_path)

    impacted: Set[str] = set()
    for fid in failed_shot_ids:
        if fid in locked_shots:
            continue
        impacted.add(fid)
        if fid in shot_order:
            idx = shot_order.index(fid)
            if idx > 0 and shot_order[idx - 1] not in locked_shots:
                impacted.add(shot_order[idx - 1])
            if idx < len(shot_order) - 1 and shot_order[idx + 1] not in locked_shots:
                impacted.add(shot_order[idx + 1])

    return [sid for sid in shot_order if sid in impacted]


def _resolve_bible_preset(diag_str: str, chars: Dict[str, Any]) -> str:
    for cid, cinfo in chars.items():
        if isinstance(cinfo, dict) and cid.lower() in diag_str:
            return str(cinfo.get("preset", "legionary"))
    if "marcus" in diag_str or "valeria" in diag_str or "centurio" in diag_str or "command" in diag_str:
        return "centurio"
    if "gaius" in diag_str or "aquilifer" in diag_str or "standard" in diag_str:
        return "aquilifer"
    if "hastat" in diag_str or "front" in diag_str:
        return "hastatus"
    if "princep" in diag_str or "reserve" in diag_str:
        return "principes"
    if "celtic" in diag_str or "barbarian" in diag_str:
        return "celtic"
    return "legionary"


def plan_minimal_repair(
    project_dir: Path | str,
    classified_issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a minimal, validated patch plan for classified defects on non-locked generated shots.
    """
    p_path = Path(project_dir).resolve()
    shots_file = p_path / "story" / "shots.json"
    bible_file = p_path / "story" / "character_bible.json"

    char_bible: Dict[str, Any] = {}
    if bible_file.is_file():
        try:
            char_bible = json.loads(bible_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    chars = char_bible.get("characters", {}) if isinstance(char_bible, dict) else {}

    parent_hash = sha256_file(shots_file) if shots_file.is_file() else ""
    patches: List[Dict[str, Any]] = []

    for issue in classified_issues:
        if issue.get("manual_locked") or issue.get("shot_id") == "__REPORT_INVALID__":
            continue

        sid = str(issue["shot_id"])
        cats = issue.get("categories") or [issue.get("category", "unknown")]
        diags = issue.get("diagnostics", [])
        diag_str = " ".join(diags).lower()

        for cat in cats:
            patch: Dict[str, Any] = {
                "shot_id": sid,
                "category": cat,
                "action": "noop",
                "reason": diags[0] if diags else f"Fix {cat} defect in {sid}",
                "changes": {},
            }

            if cat == "blank_frame":
                patch["action"] = "restore_non_blank_scene"
                patch["changes"] = {"tpl": "scene", "bg": "plain", "clear_dark": True}

            elif cat == "actor_preset":
                resolved_preset = _resolve_bible_preset(diag_str, chars)
                patch["action"] = "fix_actor_preset"
                patch["changes"] = {
                    "preset": resolved_preset,
                    "body": "roman",
                }

            elif cat == "continuity":
                patch["action"] = "smooth_actor_trajectory"
                patch["changes"] = {
                    "from": 0.42,
                    "to": 0.52,
                    "clear_exit": True,
                    "smooth": True,
                }

            elif cat == "prop":
                patch["action"] = "remove_duplicate_prop"
                patch["changes"] = {"weapon2": None, "shield2": None}

            elif cat == "camera":
                patch["action"] = "smooth_camera_keyframes"
                patch["changes"] = {"camera_snap_smoothed": True}

            elif cat == "pose":
                patch["action"] = "ground_actor_posture"
                patch["changes"] = {"y": 0.88, "pose": "brace"}

            elif cat == "map_diagram":
                patch["action"] = "enhance_diagram_contrast"
                patch["changes"] = {
                    "ensure_diagram_kind": "roman_manipular_formation_diagram",
                    "contrast_boost": True,
                    "show_unit_badges": True,
                }

            patches.append(patch)

    return {
        "timestamp": time.time(),
        "project_id": p_path.name,
        "parent_hash": parent_hash,
        "total_patches": len(patches),
        "patches": patches,
    }


def apply_generated_only_repairs(
    project_dir: Path | str,
    repair_plan: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Apply minimal patches strictly to generated-only fields in story/shots.json.
    Never modifies manually locked shots.
    """
    p_path = Path(project_dir).resolve()
    shots_file = p_path / "story" / "shots.json"
    if not shots_file.is_file():
        return False, ["Missing story/shots.json"]

    try:
        raw_data = json.loads(shots_file.read_text(encoding="utf-8"))
        shots = raw_data.get("shots", []) if isinstance(raw_data, dict) else raw_data
    except Exception as exc:
        return False, [f"Failed to read shots.json: {exc}"]

    expected_parent = repair_plan.get("parent_hash")
    if expected_parent:
        cur_hash = sha256_file(shots_file)
        if cur_hash != expected_parent:
            return False, [f"Parent hash mismatch on shots.json: expected {expected_parent}, got {cur_hash}"]

    logs: List[str] = []
    shots_by_id = {str(s.get("id")): s for s in shots if isinstance(s, dict) and s.get("id")}

    for p in repair_plan.get("patches", []):
        sid = str(p.get("shot_id"))
        shot = shots_by_id.get(sid)
        if not shot:
            logs.append(f"Shot {sid} not found in project")
            continue

        if shot.get("manual_locked") or shot.get("visual_source") == "manual":
            logs.append(f"Shot {sid} is manually locked; repair skipped to preserve user content")
            continue

        action = p.get("action")
        changes = p.get("changes", {})
        args = shot.setdefault("args", {})

        if action == "restore_non_blank_scene":
            if shot.get("tpl") == "black":
                shot["tpl"] = changes.get("tpl", "scene")
            args.pop("dark", None)
            args.setdefault("bg", changes.get("bg", "plain"))
            if not args.get("people"):
                args["people"] = [{"id": "guard_01", "preset": "legionary", "x": 0.5, "y": 0.88, "h": 0.46}]
            logs.append(f"Shot {sid}: restored non-blank scene content")

        elif action == "fix_actor_preset":
            for person in args.get("people", []):
                cur_pr = str(person.get("preset") or "")
                if not cur_pr or "corrupt" in cur_pr or "unknown" in cur_pr or cur_pr not in ("centurio", "legionary", "hastatus", "principes", "aquilifer", "optio", "triarius"):
                    person["preset"] = changes.get("preset", "legionary")
                person.setdefault("body", changes.get("body", "roman"))
            logs.append(f"Shot {sid}: repaired actor preset to '{changes.get('preset')}'")

        elif action == "smooth_actor_trajectory":
            for person in args.get("people", []):
                if changes.get("clear_exit"):
                    person.pop("exit", None)
                    person.pop("gone", None)
                person["from"] = changes.get("from", 0.42)
                person["to"] = changes.get("to", 0.52)
                person["x"] = changes.get("from", 0.42)
                person["dur"] = float(shot.get("dur", 2.0))
            logs.append(f"Shot {sid}: cleared abrupt exit and smoothed actor trajectory [{changes.get('from')} -> {changes.get('to')}]")

        elif action == "remove_duplicate_prop":
            for person in args.get("people", []):
                person.pop("weapon2", None)
                person.pop("shield2", None)
            # Also resolve simultaneous held + ground standard duplication if present
            props = args.get("props", [])
            has_ground_std = any(
                isinstance(pr, dict) and str(pr.get("kind") or pr.get("type") or "") in ("standard", "eagle")
                for pr in props
            )
            if has_ground_std:
                for person in args.get("people", []):
                    if person.get("preset") == "aquilifer" and person.get("weapon", "standard") == "standard":
                        person["weapon"] = "gladius"
            logs.append(f"Shot {sid}: enforced single-held-prop exclusivity")

        elif action == "smooth_camera_keyframes":
            rig = args.get("cameraRig", {})
            kfs = rig.get("keyframes", [])
            if isinstance(kfs, list) and len(kfs) >= 2:
                dur = float(shot.get("dur", 2.5))
                rig["keyframes"] = [
                    {"t": 0.0, "x": 0.48, "y": 0.50, "z": 1.04},
                    {"t": round(dur, 2), "x": 0.52, "y": 0.50, "z": 1.10},
                ]
            logs.append(f"Shot {sid}: smoothed abrupt cameraRig keyframes")

        elif action == "ground_actor_posture":
            for person in args.get("people", []):
                person["y"] = changes.get("y", 0.88)
                person["pose"] = changes.get("pose", "brace")
            logs.append(f"Shot {sid}: grounded BRACE actor posture")

        elif action == "enhance_diagram_contrast":
            args["show_unit_badges"] = True
            args["contrast_boost"] = True
            props = args.setdefault("props", [])
            for pr in props:
                if isinstance(pr, dict) and not pr.get("kind") and pr.get("type"):
                    pr["kind"] = pr["type"]
                if isinstance(pr, dict) and pr.get("s") is None and pr.get("scale") is not None:
                    pr["s"] = pr["scale"]
            if not props:
                props.append(
                    {
                        "kind": changes.get("ensure_diagram_kind", "roman_manipular_formation_diagram"),
                        "x": 0.5,
                        "y": 0.52,
                        "s": 1.0,
                    }
                )
            logs.append(f"Shot {sid}: normalized diagram prop kind/scale and contrast badges")

    out_dict = raw_data if isinstance(raw_data, dict) else {"shots": shots}
    out_dict["shots"] = shots
    temp_p = shots_file.with_suffix(f".{os.getpid()}.tmp.json")
    with open(temp_p, "w", encoding="utf-8") as fh:
        json.dump(out_dict, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp_p, shots_file)

    return True, logs


def _resolve_project_audio_track(p_path: Path) -> Optional[Path]:
    for rel in (
        "build/soundtrack_mixed.wav",
        "build/mix.wav",
        "timeline/voice.wav",
        "build/voice_track.wav",
        "voice.wav",
    ):
        cand = p_path / rel
        if cand.is_file() and cand.stat().st_size > 200:
            return cand
    return None


def _default_output_mp4(p_path: Path) -> Path:
    out_dir = p_path / "out"
    if out_dir.is_dir():
        mp4s = sorted(p for p in out_dir.glob("*.mp4") if not p.name.endswith(".partial.mp4"))
        if mp4s:
            return mp4s[-1]
    return p_path / "out" / f"{p_path.name}_repaired.mp4"


def rerender_affected_shots(
    project_dir: Path | str,
    impacted_ids: List[str],
    output_mp4_path: Optional[Path | str] = None,
    workers: int = 1,
) -> Dict[str, Any]:
    """
    Re-render project video, mux audio track atomically, inspect decoded output,
    and update cryptographic render_receipt.json.
    Honestly records `FULL_RERENDER_FALLBACK` (never falsely claims selective segment render).
    """
    p_path = Path(project_dir).resolve()
    target_mp4 = Path(output_mp4_path).resolve() if output_mp4_path else _default_output_mp4(p_path)
    target_mp4.parent.mkdir(parents=True, exist_ok=True)
    build_dir = p_path / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    rec: Dict[str, Any] = {
        "timestamp": time.time(),
        "project_id": p_path.name,
        "impacted_ids": list(impacted_ids),
        "render_mode": "FULL_RERENDER_FALLBACK",
        "selective_segment_supported": False,
        "full_rerender_fallback": True,
        "reason": "Continuous camera and audio-visual timeline synchronization require full timeline rerender",
        "output_mp4_path": str(target_mp4),
    }

    env = dict(os.environ)
    env.pop("QA_STUDIO_TEST_MODE", None)

    cmd = ["node", "render.mjs", "--project", str(p_path), "--workers", str(max(1, int(workers)))]
    res = subprocess.run(cmd, cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    render_log = build_dir / "render.log"
    render_log.write_text((res.stdout or "") + "\n" + (res.stderr or ""), encoding="utf-8")

    rec["render_returncode"] = res.returncode
    if res.returncode != 0:
        rec["elapsed_sec"] = round(time.perf_counter() - t0, 3)
        rec["success"] = False
        rec["error"] = f"render.mjs exited with code {res.returncode}: {(res.stderr or res.stdout)[-400:]}"
        return rec

    silent_mp4 = build_dir / "video_silent.mp4"
    if not silent_mp4.is_file() or silent_mp4.stat().st_size < 100:
        rec["elapsed_sec"] = round(time.perf_counter() - t0, 3)
        rec["success"] = False
        rec["error"] = "Missing or empty build/video_silent.mp4 after render.mjs"
        return rec

    audio_wav = _resolve_project_audio_track(p_path)
    partial_mp4 = target_mp4.with_suffix(".partial.mp4")
    if partial_mp4.exists():
        partial_mp4.unlink()

    if audio_wav is not None:
        mux_cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(silent_mp4),
            "-i",
            str(audio_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(partial_mp4),
        ]
        mux_res = subprocess.run(mux_cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        if mux_res.returncode != 0:
            rec["elapsed_sec"] = round(time.perf_counter() - t0, 3)
            rec["success"] = False
            rec["error"] = f"FFmpeg audio mux failed: {mux_res.stderr[-400:]}"
            return rec
        require_audio = True
    else:
        shutil.copy2(silent_mp4, partial_mp4)
        require_audio = False

    media_check = inspect_media_file(partial_mp4, require_audio=require_audio, full_decode=True)
    if not media_check.get("valid", False):
        rec["elapsed_sec"] = round(time.perf_counter() - t0, 3)
        rec["success"] = False
        rec["media_inspection"] = media_check
        rec["error"] = f"Repaired partial MP4 failed media inspection: {media_check.get('error')}"
        return rec

    os.replace(partial_mp4, target_mp4)
    manifest = collect_render_inputs(
        p_path,
        render_options={"audio_mode": "voice_sfx" if require_audio else "silent"},
    )
    receipt_path = write_render_receipt_atomic(
        p_path,
        target_mp4,
        manifest,
        metadata={
            "action": "shot_repair_rerender",
            "wall_sec": round(time.perf_counter() - t0, 3),
            "render_mode": "FULL_RERENDER_FALLBACK",
            "ai_director_mode": "OFFLINE_ONLY",
            "ai_director_live_used": False,
            "repaired_impacted_ids": list(impacted_ids),
        },
    )
    cache_verify = validate_cache_hit(p_path, target_mp4, manifest)

    rec["elapsed_sec"] = round(time.perf_counter() - t0, 3)
    rec["audio_muxed"] = audio_wav is not None
    rec["audio_source"] = str(audio_wav) if audio_wav else None
    rec["output_sha256"] = sha256_file(target_mp4)
    rec["receipt_path"] = str(receipt_path)
    rec["receipt_verified"] = bool(cache_verify.get("hit", False))
    rec["media_inspection"] = media_check
    rec["success"] = bool(cache_verify.get("hit", False))
    return rec


def run_targeted_qa(
    project_dir: Path | str,
    impacted_ids: List[str],
    mp4_path: Optional[Path | str] = None,
    output_evidence_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Execute targeted Temporal Visual QA on decoded MP4 frames focusing on impacted shots."""
    p_path = Path(project_dir).resolve()
    target_mp4 = Path(mp4_path).resolve() if mp4_path else _default_output_mp4(p_path)
    ev_dir = (
        Path(output_evidence_dir).resolve()
        if output_evidence_dir
        else (p_path / "build" / "repair_qa_targeted")
    )

    qa_rep = audit_project_temporal_visual(
        p_path,
        target_mp4,
        ev_dir,
        run_negative_suite=False,
    )
    norm = _normalize_qa_report(qa_rep)
    if not norm["valid_report"]:
        return {
            "status": "NOT_VERIFIED",
            "impacted_shots": list(impacted_ids),
            "targeted_issues_count": 0,
            "targeted_issues": [],
            "reason": norm.get("reason"),
        }

    impacted_set = set(impacted_ids)
    targeted_issues = [
        iss for iss in norm["temporal_issues"]
        if iss.get("shot_id") in impacted_set
    ]
    # Also ensure every impacted shot actually exists and has VISUAL_TECH_PASS
    missing_or_unverified = [
        sid for sid in impacted_set
        if sid not in norm["shot_audits"]
        or (
            norm["shot_audits"][sid].get("technical_verdict")
            if isinstance(norm["shot_audits"][sid], dict)
            else getattr(norm["shot_audits"][sid], "technical_verdict", "NOT_VERIFIED")
        )
        != "VISUAL_TECH_PASS"
    ]

    if len(targeted_issues) == 0 and len(missing_or_unverified) == 0 and len(norm["global_issues"]) == 0:
        status = "PASS"
    elif any("NOT_VERIFIED" in str(s) for s in missing_or_unverified):
        status = "NOT_VERIFIED"
    else:
        status = "FAIL"

    return {
        "status": status,
        "impacted_shots": list(impacted_ids),
        "targeted_issues_count": len(targeted_issues),
        "targeted_issues": targeted_issues,
        "missing_or_unverified_shots": missing_or_unverified,
    }


def run_full_final_qa(
    project_dir: Path | str,
    mp4_path: Optional[Path | str] = None,
    output_evidence_dir: Optional[Path | str] = None,
) -> TemporalQAReport:
    """Execute full movie Temporal Visual QA across all shots on the rendered MP4."""
    p_path = Path(project_dir).resolve()
    target_mp4 = Path(mp4_path).resolve() if mp4_path else _default_output_mp4(p_path)
    ev_dir = (
        Path(output_evidence_dir).resolve()
        if output_evidence_dir
        else (p_path / "build" / "repair_qa_full")
    )
    return audit_project_temporal_visual(
        p_path,
        target_mp4,
        ev_dir,
        run_negative_suite=False,
    )


def execute_repair_loop(
    project_dir: Path | str,
    mp4_path: Optional[Path | str] = None,
    output_evidence_dir: Optional[Path | str] = None,
    max_attempts: int = 2,
    workers: int = 1,
) -> Dict[str, Any]:
    """
    Execute bounded closed repair loop on a real rendered MP4:
    full QA -> classify -> manual_lock check -> dependencies -> plan -> patch -> rerender+mux -> targeted QA -> full QA.
    """
    p_path = Path(project_dir).resolve()
    target_mp4 = Path(mp4_path).resolve() if mp4_path else _default_output_mp4(p_path)
    ev_root = (
        Path(output_evidence_dir).resolve()
        if output_evidence_dir
        else (p_path / "build" / "repair_loop_evidence")
    )
    ev_root.mkdir(parents=True, exist_ok=True)

    before_mp4_sha = sha256_file(target_mp4) if target_mp4.is_file() else None
    qa_initial_obj = run_full_final_qa(p_path, target_mp4, ev_root / "attempt_0_initial")
    norm_initial = _normalize_qa_report(qa_initial_obj)

    if not norm_initial["valid_report"]:
        return {
            "status": "NOT_VERIFIED",
            "attempts": 0,
            "initial_verdict": "NOT_VERIFIED",
            "final_verdict": "NOT_VERIFIED",
            "reason": norm_initial.get("reason"),
            "ledger": [],
        }

    if (
        norm_initial["technical_verdict"] == "VISUAL_TECH_PASS"
        and len(norm_initial["temporal_issues"]) == 0
        and len(norm_initial["global_issues"]) == 0
    ):
        return {
            "status": "CLEAN_PASS",
            "attempts": 0,
            "initial_verdict": "VISUAL_TECH_PASS",
            "final_verdict": "VISUAL_TECH_PASS",
            "before_mp4_sha256": before_mp4_sha,
            "after_mp4_sha256": before_mp4_sha,
            "ledger": [],
        }

    qa_current_obj = qa_initial_obj
    norm_current = norm_initial
    ledger: List[Dict[str, Any]] = []

    for attempt in range(1, max_attempts + 1):
        step_rec: Dict[str, Any] = {"attempt": attempt}

        classified = classify_failed_shots(qa_current_obj, project_dir=p_path)
        step_rec["classified"] = classified
        if not classified:
            break

        if any(c.get("shot_id") == "__REPORT_INVALID__" for c in classified):
            ledger.append(step_rec)
            return {
                "status": "NOT_VERIFIED",
                "attempts": attempt,
                "initial_verdict": norm_initial["technical_verdict"],
                "final_verdict": "NOT_VERIFIED",
                "ledger": ledger,
            }

        locked_failures = [c for c in classified if c.get("manual_locked")]
        if locked_failures:
            step_rec["blocked_locked_shots"] = [c["shot_id"] for c in locked_failures]
            ledger.append(step_rec)
            return {
                "status": "BLOCKED_MANUAL_REVIEW",
                "attempts": attempt,
                "initial_verdict": norm_initial["technical_verdict"],
                "final_verdict": norm_current["technical_verdict"],
                "blocked_locked_shots": [c["shot_id"] for c in locked_failures],
                "reason": "Defect detected inside manually locked shot(s); refusing to overwrite user-locked content",
                "before_mp4_sha256": before_mp4_sha,
                "after_mp4_sha256": sha256_file(target_mp4) if target_mp4.is_file() else None,
                "ledger": ledger,
            }

        failed_ids = [c["shot_id"] for c in classified]
        impacted = compute_impacted_shot_dependencies(p_path, failed_ids)
        step_rec["impacted"] = impacted

        plan = plan_minimal_repair(p_path, classified)
        step_rec["plan"] = plan

        ok, apply_logs = apply_generated_only_repairs(p_path, plan)
        step_rec["apply_success"] = ok
        step_rec["apply_logs"] = apply_logs
        if not ok:
            ledger.append(step_rec)
            return {
                "status": "FAIL",
                "attempts": attempt,
                "initial_verdict": norm_initial["technical_verdict"],
                "final_verdict": "FAIL",
                "error": f"Failed to apply repair patches: {apply_logs}",
                "ledger": ledger,
            }

        render_res = rerender_affected_shots(
            p_path,
            impacted,
            output_mp4_path=target_mp4,
            workers=workers,
        )
        step_rec["render_result"] = render_res
        if not render_res.get("success", False):
            ledger.append(step_rec)
            return {
                "status": "FAIL",
                "attempts": attempt,
                "initial_verdict": norm_initial["technical_verdict"],
                "final_verdict": "FAIL",
                "error": render_res.get("error", "Rerender failed"),
                "ledger": ledger,
            }

        qa_targeted = run_targeted_qa(
            p_path,
            impacted,
            mp4_path=target_mp4,
            output_evidence_dir=ev_root / f"attempt_{attempt}_targeted",
        )
        step_rec["qa_targeted"] = qa_targeted

        qa_current_obj = run_full_final_qa(
            p_path,
            mp4_path=target_mp4,
            output_evidence_dir=ev_root / f"attempt_{attempt}_full",
        )
        norm_current = _normalize_qa_report(qa_current_obj)
        step_rec["qa_final"] = {
            "verdict": norm_current["technical_verdict"],
            "passed_shots": norm_current.get("passed_shots", 0),
            "total_shots": norm_current.get("total_shots", 0),
            "issues_count": len(norm_current["temporal_issues"]),
            "issues": norm_current["temporal_issues"],
        }
        ledger.append(step_rec)

        if (
            qa_targeted.get("status") == "PASS"
            and norm_current["valid_report"]
            and norm_current["technical_verdict"] == "VISUAL_TECH_PASS"
            and len(norm_current["temporal_issues"]) == 0
            and len(norm_current["global_issues"]) == 0
        ):
            after_mp4_sha = sha256_file(target_mp4)
            return {
                "status": "REPAIR_SUCCESS",
                "attempts": attempt,
                "initial_verdict": norm_initial["technical_verdict"],
                "final_verdict": "VISUAL_TECH_PASS",
                "render_mode": render_res.get("render_mode"),
                "before_mp4_sha256": before_mp4_sha,
                "after_mp4_sha256": after_mp4_sha,
                "mp4_changed": before_mp4_sha != after_mp4_sha,
                "receipt_verified": render_res.get("receipt_verified", False),
                "ledger": ledger,
            }

    return {
        "status": "FAIL",
        "attempts": max_attempts,
        "initial_verdict": norm_initial["technical_verdict"],
        "final_verdict": norm_current.get("technical_verdict", "FAIL"),
        "error": "Unresolved defects after maximum repair attempts",
        "before_mp4_sha256": before_mp4_sha,
        "after_mp4_sha256": sha256_file(target_mp4) if target_mp4.is_file() else None,
        "ledger": ledger,
    }


def _synthesize_spoken_test_wav(wav_path: Path, duration_sec: float) -> Dict[str, Any]:
    """Generate a real spoken English voice WAV padded cleanly to duration_sec (macOS `say` or Windows SAPI)."""
    say_bin = shutil.which("say")
    raw_src = wav_path.with_suffix(".raw_tts.wav")
    spoken_text = "Cohort hold the ridge. Rescue team advance and secure the standard."
    if say_bin:
        aiff_tmp = wav_path.with_suffix(".aiff")
        subprocess.run(
            [say_bin, "-v", "Daniel", "-r", "175", "-o", str(aiff_tmp), spoken_text],
            check=True,
            capture_output=True,
        )
        raw_src = aiff_tmp
    elif sys.platform == "win32":
        from scripts.tts_helper import synthesize_speech

        if not synthesize_speech(spoken_text, raw_src):
            return {"ok": False, "status": "BLOCKED_NO_SPEECH_PROVIDER"}
    else:
        return {"ok": False, "status": "BLOCKED_NO_SPEECH_PROVIDER"}

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(raw_src),
            "-af",
            f"apad=whole_dur={duration_sec:.2f}",
            "-t",
            f"{duration_sec:.2f}",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ],
        check=True,
        capture_output=True,
    )
    if raw_src.exists():
        raw_src.unlink()
    return {"ok": True, "status": "SPOKEN_VOICE_READY"}


def test_defect_injection_and_repair(evidence_out_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """
    End-to-end real video repair test on a disposable 3-shot Squire project:
    1. Renders initial 3-shot MP4 + spoken voice audio where s01 is manual_locked and s02 (generated)
       has real injected visual + preset + duplicate-prop defects (abrupt mid-shot exit causing frame-level
       actor disappearance, unknown preset, and duplicate weapon2).
    2. Verifies initial QA fails on s02.
    3. Runs execute_repair_loop() -> rerenders real MP4, muxes audio, re-issues receipt, runs targeted & full QA.
    4. Asserts s01 manual_locked canonical JSON SHA256 is 100% preserved, MP4 SHA256 changed, media decode & audio valid,
       and final QA == VISUAL_TECH_PASS.
    5. Also verifies that a defect injected into manual_locked s01 returns BLOCKED_MANUAL_REVIEW without touching s01.
    """
    t_start = time.perf_counter()
    # Place disposable workspace inside ROOT_DIR/.test-runs so render.mjs relative imports/assets work cleanly
    scratch_parent = ROOT_DIR / ".test-runs"
    scratch_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="shot_repair_v1475_", dir=str(scratch_parent)) as tmp_dir:
        tmp_p = Path(tmp_dir)
        for sub in ("story", "timeline", "build", "out"):
            (tmp_p / sub).mkdir(parents=True, exist_ok=True)

        cfg = {
            "name": "disposable_shot_repair_v14_7_5",
            "pack": "squire",
            "width": 960,
            "height": 540,
            "fps": 24,
        }
        (tmp_p / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        bible = {
            "characters": {
                "marcus": {"preset": "centurio", "role": "commander"},
                "decimus": {"preset": "legionary", "role": "frontline"},
                "titus": {"preset": "principes", "role": "reserve"},
            }
        }
        (tmp_p / "story" / "character_bible.json").write_text(json.dumps(bible, indent=2), encoding="utf-8")

        shots = [
            {
                "id": "s01",
                "tpl": "scene",
                "start": 0.0,
                "end": 1.8,
                "dur": 1.8,
                "action": "STAND",
                "desc": "Commander Marcus holds the ridge line.",
                "visual_source": "manual",
                "manual_locked": True,
                "args": {
                    "bg": "plain",
                    "time": "day",
                    "people": [{"id": "marcus", "preset": "centurio", "x": 0.48, "y": 0.88, "h": 0.46, "pose": "stand"}],
                },
            },
            {
                "id": "s02",
                "tpl": "scene",
                "start": 1.8,
                "end": 3.6,
                "dur": 1.8,
                "action": "ADVANCE",
                "desc": "Decimus advances across the stony gap.",
                "visual_source": "generated",
                "manual_locked": False,
                "args": {
                    "bg": "plain",
                    "time": "day",
                    "dark": 0.99,
                    "people": [
                        {
                            "id": "decimus",
                            "preset": "corrupted_blue_peasant",
                            "x": 0.45,
                            "to": 0.54,
                            "y": 0.88,
                            "h": 0.46,
                            "weapon": "pilum",
                            "weapon2": "spear",
                        }
                    ],
                },
            },
            {
                "id": "s03",
                "tpl": "scene",
                "start": 3.6,
                "end": 5.4,
                "dur": 1.8,
                "action": "STAND",
                "desc": "Reserves reform behind the cohort standard.",
                "visual_source": "generated",
                "manual_locked": False,
                "args": {
                    "bg": "plain",
                    "time": "day",
                    "people": [{"id": "titus", "preset": "principes", "x": 0.50, "y": 0.88, "h": 0.46, "pose": "stand"}],
                },
            },
        ]
        shots_file = tmp_p / "story" / "shots.json"
        shots_file.write_text(json.dumps({"shots": shots}, indent=2), encoding="utf-8")
        s01_hash_before = canonical_json_sha256(shots[0])

        voice_wav = tmp_p / "timeline" / "voice.wav"
        voice_status = _synthesize_spoken_test_wav(voice_wav, duration_sec=5.4)
        if not voice_status.get("ok"):
            return {
                "test_status": voice_status.get("status", "BLOCKED_NO_SPEECH_PROVIDER"),
                "error": "macOS speech provider unavailable",
            }

        mp4_out = tmp_p / "out" / "disposable_repair_test.mp4"
        initial_render = rerender_affected_shots(tmp_p, ["s01", "s02", "s03"], output_mp4_path=mp4_out, workers=1)
        assert initial_render.get("success") is True, f"Initial render failed: {initial_render}"
        before_mp4_sha = initial_render["output_sha256"]

        loop_res = execute_repair_loop(
            tmp_p,
            mp4_path=mp4_out,
            output_evidence_dir=tmp_p / "build" / "repair_ev",
            max_attempts=2,
            workers=1,
        )
        assert loop_res["status"] == "REPAIR_SUCCESS", f"Expected REPAIR_SUCCESS, got: {loop_res}"
        assert loop_res["initial_verdict"] == "FAIL"
        assert loop_res["final_verdict"] == "VISUAL_TECH_PASS"
        assert loop_res["mp4_changed"] is True
        assert loop_res["before_mp4_sha256"] == before_mp4_sha
        assert loop_res["after_mp4_sha256"] != before_mp4_sha
        assert loop_res["render_mode"] == "FULL_RERENDER_FALLBACK"

        repaired_shots = json.loads(shots_file.read_text(encoding="utf-8"))["shots"]
        s01_hash_after = canonical_json_sha256(repaired_shots[0])
        assert s01_hash_before == s01_hash_after, "Manual-locked s01 was modified!"
        assert "dark" not in repaired_shots[1]["args"]
        assert repaired_shots[1]["args"]["people"][0]["preset"] == "legionary"
        assert "weapon2" not in repaired_shots[1]["args"]["people"][0]

        final_media = inspect_media_file(mp4_out, require_audio=True, full_decode=True)
        assert final_media["valid"] is True, f"Repaired media invalid: {final_media}"

        # Sub-test B: Defect inside manual_locked s01 MUST return BLOCKED_MANUAL_REVIEW without mutating s01
        repaired_shots[0]["args"]["people"][0]["weapon"] = "sword"
        repaired_shots[0]["args"]["people"][0]["weapon2"] = "axe"
        shots_file.write_text(json.dumps({"shots": repaired_shots}, indent=2), encoding="utf-8")
        locked_defect_hash_before = canonical_json_sha256(repaired_shots[0])

        blocked_res = execute_repair_loop(
            tmp_p,
            mp4_path=mp4_out,
            output_evidence_dir=tmp_p / "build" / "repair_ev_locked",
            max_attempts=2,
            workers=1,
        )
        after_locked_shots = json.loads(shots_file.read_text(encoding="utf-8"))["shots"]
        locked_defect_hash_after = canonical_json_sha256(after_locked_shots[0])
        assert blocked_res["status"] == "BLOCKED_MANUAL_REVIEW", f"Expected BLOCKED_MANUAL_REVIEW, got {blocked_res}"
        assert locked_defect_hash_before == locked_defect_hash_after, "Blocked manual-locked shot was mutated!"

        summary = {
            "test_status": "PASS",
            "elapsed_sec": round(time.perf_counter() - t_start, 3),
            "render_mode": loop_res["render_mode"],
            "selective_segment_supported": False,
            "initial_verdict": loop_res["initial_verdict"],
            "final_verdict": loop_res["final_verdict"],
            "attempts_used": loop_res["attempts"],
            "before_mp4_sha256": loop_res["before_mp4_sha256"],
            "after_mp4_sha256": loop_res["after_mp4_sha256"],
            "mp4_rebuilt_and_changed": loop_res["mp4_changed"],
            "receipt_verified": loop_res["receipt_verified"],
            "manual_locked_s01_hash_before": s01_hash_before,
            "manual_locked_s01_hash_after": s01_hash_after,
            "manual_locked_preserved": (s01_hash_before == s01_hash_after),
            "locked_defect_status": blocked_res["status"],
            "locked_defect_hash_preserved": (locked_defect_hash_before == locked_defect_hash_after),
            "final_media_inspection": {
                "valid": final_media["valid"],
                "duration": final_media["duration"],
                "width": final_media["width"],
                "height": final_media["height"],
                "fps": final_media["fps"],
                "video_codec": final_media["video_codec"],
                "audio_codec": final_media["audio_codec"],
                "mean_volume_db": final_media.get("mean_volume_db"),
            },
            "ledger": loop_res["ledger"],
        }

        if evidence_out_path:
            out_p = Path(evidence_out_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            tmp_out = out_p.with_suffix(f".{os.getpid()}.tmp")
            tmp_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            os.replace(tmp_out, out_p)

        return summary


if __name__ == "__main__":
    out_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = test_defect_injection_and_repair(evidence_out_path=out_arg)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("test_status") == "PASS" else 1)
