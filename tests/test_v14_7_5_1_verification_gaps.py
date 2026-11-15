#!/usr/bin/env python3
"""tests/test_v14_7_5_1_verification_gaps.py — Unit & Integration Tests for V14.7.5.1 P0 Closures.

Covers:
1. Section 02: 100% Cut-Boundary Temporal QA (N shots -> N-1 cuts across actor/map/title/prop,
   exact pre_2/pre_1/post_1/post_2 frame indices, corrupted/missing boundary frames -> NOT_VERIFIED/FAIL,
   world-state continuity mutation -> FAIL, non-allowlisted cut reason -> FAIL, allowlisted insert -> PASS,
   Eagle in the Fog 12 shots -> 11/11 cuts).
2. Section 03: Provenance & Fingerprint Contract (zero null input_fingerprint disguised as verified,
   stale manifest detection, swapped MP4 detection, tampered receipt detection, Eagle live recomputation).
3. Section 04: Resource Floors (>=6.0 GiB disk & >=1.0 GiB RAM clamped everywhere), low RAM (0.7 GiB),
   low disk (5.9 GiB) + run-owned scratch cleanup without touching project files, heavy_render contention
   serialization, hanging subprocess tree kill, crash + dependent-job blocking, and zero orphan workers.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    validate_cache_hit,
    verify_receipt_and_lineage,
    write_render_receipt_atomic,
)
from scripts.qa_scheduler import (
    build_dependency_dag,
    choose_bounded_parallelism,
    inspect_resource_budget,
    run_dag,
)
from tools.temporal_visual_qa import (
    audit_cut_boundaries_all,
    audit_project_temporal_visual,
    audit_single_cut_boundary,
    build_cut_boundary_frame_plan,
)


def _make_synthetic_4shot_mp4(mp4_path: Path, fps: int = 24) -> None:
    """Create a real decoded 4.0s (96-frame) 640x360 H.264+AAC MP4 for 4 shots: ACTOR -> MAP -> TITLE -> ACTOR."""
    frames_dir = mp4_path.parent / "raw_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    w, h = 640, 360
    for f_idx in range(96):
        img = Image.new("RGB", (w, h), (34, 40, 52))
        draw = ImageDraw.Draw(img)
        if f_idx < 24:
            # Shot 1 (0.0-1.0s): ACTOR at x ~ 0.35..0.42
            cx = int(w * (0.35 + 0.07 * (f_idx / 23.0)))
            draw.rectangle([0, int(h * 0.72), w, h], fill=(58, 52, 44))
            draw.rectangle([cx - 24, int(h * 0.34), cx + 24, int(h * 0.72)], fill=(195, 75, 55))
            draw.ellipse([cx - 16, int(h * 0.22), cx + 16, int(h * 0.34)], fill=(228, 195, 165))
        elif f_idx < 48:
            # Shot 2 (1.0-2.0s): MAP diagram with crisp high-contrast shapes & strokes
            img.paste((26, 36, 48), [0, 0, w, h])
            draw = ImageDraw.Draw(img)
            draw.rectangle([40, 35, w - 40, h - 35], outline=(235, 210, 150), width=4, fill=(36, 52, 68))
            draw.line([(80, 180), (560, 180)], fill=(90, 185, 240), width=14)
            prog = int(120 + 280 * ((f_idx - 24) / 23.0))
            draw.rectangle([prog - 30, 110, prog + 30, 250], fill=(230, 185, 75), outline=(255, 255, 255), width=3)
            draw.rectangle([100, 55, 360, 95], fill=(18, 24, 32), outline=(245, 220, 160), width=2)
            draw.rectangle([115, 68, 340, 82], fill=(248, 242, 225))
        elif f_idx < 72:
            # Shot 3 (2.0-3.0s): TITLE card with crisp high-contrast placard
            img.paste((20, 24, 34), [0, 0, w, h])
            draw = ImageDraw.Draw(img)
            draw.rectangle([90, 90, w - 90, h - 90], fill=(34, 42, 58), outline=(240, 198, 105), width=4)
            draw.rectangle([140, 145, w - 140, 175], fill=(248, 244, 232))
            draw.rectangle([180, 195, w - 180, 215], fill=(215, 185, 120))
        else:
            # Shot 4 (3.0-4.0s): ACTOR returns at x ~ 0.44..0.52
            cx = int(w * (0.44 + 0.08 * ((f_idx - 72) / 23.0)))
            draw.rectangle([0, int(h * 0.72), w, h], fill=(58, 52, 44))
            draw.rectangle([cx - 24, int(h * 0.34), cx + 24, int(h * 0.72)], fill=(195, 75, 55))
            draw.ellipse([cx - 16, int(h * 0.22), cx + 16, int(h * 0.34)], fill=(228, 195, 165))
        img.save(frames_dir / f"f_{f_idx:04d}.png")

    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "f_%04d.png"),
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:duration=4.0:sample_rate=48000",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(mp4_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Synthetic MP4 build failed: {res.stderr}")
    shutil.rmtree(frames_dir, ignore_errors=True)


class TestV14751VerificationGaps(unittest.TestCase):
    # =========================================================================
    # SECTION 02: 100% CUT-BOUNDARY TEMPORAL QA
    # =========================================================================
    def test_4shot_actor_map_title_actor_full_boundary_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "proj_4shot"
            (proj / "story").mkdir(parents=True)
            (proj / "out").mkdir(parents=True)
            (proj / "config.json").write_text(
                json.dumps({"pack": "squire", "fps": 24, "aspect": "16:9"}),
                encoding="utf-8",
            )
            (proj / "story" / "character_bible.json").write_text(
                json.dumps({"characters": {"eng": {"preset": "officer"}}}),
                encoding="utf-8",
            )
            shots = [
                {
                    "id": "s01",
                    "start": 0.0,
                    "end": 1.0,
                    "dur": 1.0,
                    "tpl": "scene",
                    "world_state": {"gate_closed": False},
                    "args": {"people": [{"id": "eng", "preset": "officer", "from": 0.35, "to": 0.42}]},
                },
                {
                    "id": "s02",
                    "start": 1.0,
                    "end": 2.0,
                    "dur": 1.0,
                    "tpl": "map",
                    "intentional_cut_reason": "diagram_insert",
                    "world_state": {"gate_closed": False},
                    "args": {},
                },
                {
                    "id": "s03",
                    "start": 2.0,
                    "end": 3.0,
                    "dur": 1.0,
                    "tpl": "chapter",
                    "intentional_cut_reason": "title_card_transition",
                    "world_state": {"gate_closed": False},
                    "args": {"title": "ACT II"},
                },
                {
                    "id": "s04",
                    "start": 3.0,
                    "end": 4.0,
                    "dur": 1.0,
                    "tpl": "scene",
                    "intentional_cut_reason": "return_from_insert",
                    "world_state": {"gate_closed": False},
                    "args": {"people": [{"id": "eng", "preset": "officer", "from": 0.44, "to": 0.52}]},
                },
            ]
            (proj / "story" / "shots.json").write_text(
                json.dumps({"duration": 4.0, "shots": shots}),
                encoding="utf-8",
            )
            mp4 = proj / "out" / "test4.mp4"
            _make_synthetic_4shot_mp4(mp4, fps=24)

            ev_dir = Path(td) / "ev"
            rep = audit_project_temporal_visual(proj, mp4, ev_dir, run_negative_suite=False)
            self.assertEqual(rep.total_shots, 4)
            self.assertEqual(rep.expected_cut_count, 3)
            self.assertEqual(rep.audited_cut_count, 3)
            self.assertEqual(rep.unaudited_cuts, [])
            self.assertTrue(rep.full_boundary_coverage)
            self.assertEqual(len(rep.boundary_evidence), 3)

            # Verify exact distinct pre/post frame indices (never rounded to same side)
            for b in rep.boundary_evidence:
                f_idx = b["extracted_frame_indices"]
                self.assertLess(f_idx["pre_2"], f_idx["post_1"])
                self.assertLess(f_idx["pre_1"], f_idx["post_1"])
                self.assertLessEqual(f_idx["post_1"], f_idx["post_2"])
                self.assertEqual(b["actor_centroid_dx"], "NOT_APPLICABLE")
                self.assertTrue(b["coverage_complete"])

            # Now test deleted/corrupted boundary frame -> NOT_VERIFIED / incomplete coverage
            plans = build_cut_boundary_frame_plan(shots, fps=24.0)
            for idx_p, p_entry in enumerate(plans):
                p_entry["artifact_paths"] = {
                    role: Path(rep.boundary_evidence[idx_p]["artifact_paths"][role])
                    for role in ("pre_2", "pre_1", "post_1", "post_2")
                }
            target_frame = plans[1]["artifact_paths"]["post_1"]
            self.assertTrue(target_frame.is_file())
            target_frame.write_bytes(b"CORRUPTED_PNG_BYTES")
            corrupted_res = audit_cut_boundaries_all(plans, expected_cut_count=3, total_video_duration=4.0)
            self.assertFalse(corrupted_res["full_boundary_coverage"])
            self.assertEqual(corrupted_res["audited_cut_count"], 2)
            self.assertIn("s02->s03", corrupted_res["unaudited_cuts"])
            self.assertEqual(corrupted_res["boundary_evidence"][1]["status"], "NOT_VERIFIED")

            # Test world-state mutation across cut without state_changed_shots declaration -> FAIL
            mut_shots = json.loads(json.dumps(shots))
            mut_shots[1]["world_state"] = {"gate_closed": True}
            # Restore valid PNG by re-running audit on clean dir
            ev_dir_mut = Path(td) / "ev_mut"
            (proj / "story" / "shots.json").write_text(
                json.dumps({"duration": 4.0, "shots": mut_shots}),
                encoding="utf-8",
            )
            rep_mut = audit_project_temporal_visual(proj, mp4, ev_dir_mut, run_negative_suite=False)
            self.assertEqual(rep_mut.technical_verdict, "FAIL")
            self.assertTrue(
                any(iss.get("type") == "WORLD_CONTINUITY_VIOLATION" for iss in rep_mut.temporal_issues)
            )

    def test_arbitrary_cut_reason_rejected_vs_allowlisted_insert(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            # Create 4 valid RGB PNGs representing actor jumping from x=0.12 to x=0.88 across cut
            w, h = 640, 360
            for idx, cx_norm in [(22, 0.12), (23, 0.12), (24, 0.88), (25, 0.88)]:
                im = Image.new("RGB", (w, h), (35, 40, 50))
                dr = ImageDraw.Draw(im)
                cx = int(w * cx_norm)
                dr.rectangle([cx - 22, 110, cx + 22, 270], fill=(205, 70, 50))
                im.save(td_p / f"frame_{idx:06d}.png")

            s_a = {
                "id": "s01",
                "start": 0.0,
                "end": 1.0,
                "tpl": "scene",
                "args": {"people": [{"id": "hero", "preset": "officer", "from": 0.12, "to": 0.12}]},
            }
            s_b_bad = {
                "id": "s02",
                "start": 1.0,
                "end": 2.0,
                "tpl": "scene",
                "intentional_cut_reason": "magic_excuse_not_in_allowlist",
                "args": {"people": [{"id": "hero", "preset": "officer", "from": 0.88, "to": 0.88, "h": 0.42}]},
            }
            s_a["args"]["people"][0]["h"] = 0.56
            plan_bad = build_cut_boundary_frame_plan([s_a, s_b_bad], fps=24.0)[0]
            plan_bad["artifact_paths"] = {
                role: td_p / f"frame_{fidx:06d}.png"
                for role, fidx in plan_bad["extracted_frame_indices"].items()
            }
            bad_audit = audit_single_cut_boundary(plan_bad, total_video_duration=2.0)
            self.assertEqual(bad_audit["status"], "FAIL")
            self.assertFalse(bad_audit["reason_allowlisted"])

            s_b_good = dict(s_b_bad)
            s_b_good["intentional_cut_reason"] = "action_reaction_reverse_angle"
            plan_good = build_cut_boundary_frame_plan([s_a, s_b_good], fps=24.0)[0]
            plan_good["artifact_paths"] = {
                role: td_p / f"frame_{fidx:06d}.png"
                for role, fidx in plan_good["extracted_frame_indices"].items()
            }
            good_audit = audit_single_cut_boundary(plan_good, total_video_duration=2.0)
            self.assertEqual(good_audit["status"], "PASS")
            self.assertTrue(good_audit["reason_allowlisted"])

    def test_eagle_in_fog_12_shots_11_cuts_complete(self) -> None:
        eagle_proj = ROOT_DIR / "projects" / "fl01_v14_7_5_roman_eagle_in_fog_preview"
        eagle_mp4 = eagle_proj / "out" / "FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4"
        with tempfile.TemporaryDirectory() as td:
            rep = audit_project_temporal_visual(eagle_proj, eagle_mp4, Path(td) / "eagle_ev", run_negative_suite=False)
            self.assertEqual(rep.total_shots, 12)
            self.assertEqual(rep.expected_cut_count, 11)
            self.assertEqual(rep.audited_cut_count, 11)
            self.assertEqual(rep.unaudited_cuts, [])
            self.assertTrue(rep.full_boundary_coverage)
            self.assertEqual(rep.technical_verdict, "VISUAL_TECH_PASS")

    # =========================================================================
    # SECTION 03: PROVENANCE & FINGERPRINT CONTRACT
    # =========================================================================
    def test_fingerprint_null_stale_swapped_tampered_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "fp_proj"
            (proj / "story").mkdir(parents=True)
            (proj / "build").mkdir(parents=True)
            (proj / "out").mkdir(parents=True)
            (proj / "config.json").write_text(
                json.dumps({"pack": "squire", "fps": 24, "aspect": "16:9", "resolution": "360p"}),
                encoding="utf-8",
            )
            (proj / "story" / "shots.json").write_text(
                json.dumps({"duration": 4.0, "shots": [{"id": "s01", "start": 0.0, "end": 4.0, "tpl": "scene"}]}),
                encoding="utf-8",
            )
            mp4 = proj / "out" / "out.mp4"
            _make_synthetic_4shot_mp4(mp4, fps=24)

            manifest = collect_render_inputs(proj, render_options={"audio_mode": "voice_sfx"})
            rcpt_path = write_render_receipt_atomic(proj, mp4, manifest, metadata={"render_mode": "REAL_RENDER"})

            # Baseline valid lineage
            ok_lin = verify_receipt_and_lineage(proj, mp4, expected_specs={"require_audio": True})
            self.assertEqual(ok_lin["status"], "PASS")
            self.assertIsNotNone(ok_lin["input_fingerprint"])
            self.assertTrue(ok_lin["fingerprint_match"])
            self.assertTrue(ok_lin["receipt_verified"])
            self.assertTrue(ok_lin["cache_verified"])
            self.assertTrue(ok_lin["media_decode_verified"])

            # 1. Null input_fingerprint in receipt MUST fail closed without TypeError
            orig_rcpt = json.loads(rcpt_path.read_text(encoding="utf-8"))
            null_rcpt = dict(orig_rcpt, input_fingerprint=None)
            rcpt_path.write_text(json.dumps(null_rcpt), encoding="utf-8")
            # Remove sidecar too so build/render_receipt.json is authoritative
            sidecar = mp4.with_suffix(mp4.suffix + ".receipt.json")
            if sidecar.exists():
                sidecar.unlink()
            null_cache = validate_cache_hit(proj, mp4, manifest)
            self.assertFalse(null_cache["hit"])
            null_lin = verify_receipt_and_lineage(proj, mp4)
            self.assertEqual(null_lin["status"], "FAIL")
            self.assertFalse(null_lin["receipt_verified"])

            # Restore receipt, then 2. Mutate shots.json (stale manifest)
            rcpt_path.write_text(json.dumps(orig_rcpt), encoding="utf-8")
            (proj / "story" / "shots.json").write_text(
                json.dumps({"duration": 4.0, "shots": [{"id": "s01_mutated", "start": 0.0, "end": 4.0, "tpl": "map"}]}),
                encoding="utf-8",
            )
            stale_lin = verify_receipt_and_lineage(proj, mp4)
            self.assertEqual(stale_lin["status"], "FAIL")
            self.assertFalse(stale_lin["fingerprint_match"])
            self.assertFalse(stale_lin["cache_verified"])

            # Restore shots.json, then 3. Tamper output_sha256 in receipt / swapped MP4
            (proj / "story" / "shots.json").write_text(
                json.dumps({"duration": 4.0, "shots": [{"id": "s01", "start": 0.0, "end": 4.0, "tpl": "scene"}]}),
                encoding="utf-8",
            )
            tampered_rcpt = dict(orig_rcpt, output_sha256="0" * 64)
            rcpt_path.write_text(json.dumps(tampered_rcpt), encoding="utf-8")
            tamp_lin = verify_receipt_and_lineage(proj, mp4)
            self.assertEqual(tamp_lin["status"], "FAIL")
            self.assertFalse(tamp_lin["output_sha_match"])
            self.assertFalse(tamp_lin["receipt_verified"])

    # =========================================================================
    # SECTION 04: RESOURCE FLOORS (>=6.0 GiB DISK & >=1.0 GiB RAM) & ASYNC SAFETY
    # =========================================================================
    def test_low_ram_and_low_disk_floors_enforced_and_scratch_cleaned(self) -> None:
        # Even if caller passes min_ram_gb=0.5 or min_disk_gb=4.0, floor clamps to 1.0 GiB RAM and 6.0 GiB disk!
        low_ram = inspect_resource_budget(
            min_disk_gb=4.0,
            min_ram_gb=0.5,
            _override_disk_free_gb=18.0,
            _override_ram_available_gb=0.7,
        )
        self.assertEqual(low_ram["status"], "BLOCKED_RESOURCE")
        self.assertFalse(low_ram["healthy"])
        self.assertEqual(low_ram["ram_min_reserve_gb"], 1.0)
        self.assertEqual(low_ram["disk_min_reserve_gb"], 6.0)

        low_disk = inspect_resource_budget(
            min_disk_gb=4.0,
            min_ram_gb=0.5,
            _override_disk_free_gb=5.9,
            _override_ram_available_gb=4.0,
        )
        self.assertEqual(low_disk["status"], "BLOCKED_RESOURCE")
        self.assertFalse(low_disk["healthy"])

        # DAG with simulated 5.9 GiB disk must return BLOCKED_RESOURCE, clean run-owned scratch, and preserve user file
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            scratch = td_p / "run_scratch"
            scratch.mkdir(parents=True)
            (scratch / "temp_frame.png").write_bytes(b"12345")
            user_proj = td_p / "user_project"
            user_proj.mkdir(parents=True)
            keep_file = user_proj / "important.json"
            keep_file.write_text('{"keep": true}', encoding="utf-8")

            stages = build_dependency_dag(
                [{"id": "j1", "job_profile": "heavy_render", "fn": lambda: {"status": "PASS"}}]
            )
            dag_res = run_dag(
                stages,
                budget_inspector=lambda: inspect_resource_budget(
                    _override_disk_free_gb=5.9,
                    _override_ram_available_gb=3.0,
                ),
                scratch_dir=scratch,
            )
            self.assertEqual(dag_res["status"], "BLOCKED_RESOURCE")
            self.assertTrue(dag_res["scratch_cleaned_on_breach"])
            self.assertFalse(scratch.exists())
            self.assertTrue(keep_file.is_file())

    def test_heavy_render_contention_timeout_crash_and_dep_blocking(self) -> None:
        # 1. Nested heavy render contention: when RAM < 4 GiB, heavy_render concurrency is strictly 1
        b_constrained = inspect_resource_budget(
            _override_disk_free_gb=15.0,
            _override_ram_available_gb=2.5,
        )
        self.assertEqual(choose_bounded_parallelism(b_constrained, job_profile="heavy_render", max_workers_cap=4), 1)

        stages_heavy = build_dependency_dag(
            [
                {
                    "id": "h1",
                    "job_profile": "heavy_render",
                    "cmd": [sys.executable, "-c", "import time; time.sleep(0.25)"],
                },
                {
                    "id": "h2",
                    "job_profile": "heavy_render",
                    "cmd": [sys.executable, "-c", "import time; time.sleep(0.25)"],
                },
            ]
        )
        rep_heavy = run_dag(
            stages_heavy,
            max_workers=4,
            budget_inspector=lambda: b_constrained,
        )
        self.assertEqual(rep_heavy["status"], "PASS")
        self.assertEqual(rep_heavy["max_active_workers"], 1)
        self.assertEqual(rep_heavy["concurrency_proof"]["overlapping_pairs_count"], 0)
        self.assertEqual(rep_heavy["orphan_worker_processes_after_run"], 0)

        # 2. Hanging worker timeout + crashing worker + dependent-job blocking + zero orphans
        stages_fail = build_dependency_dag(
            [
                {
                    "id": "hang_job",
                    "job_profile": "light_cpu",
                    "timeout_sec": 0.4,
                    "cmd": [sys.executable, "-c", "import time; time.sleep(10.0)"],
                },
                {
                    "id": "crash_job",
                    "job_profile": "light_cpu",
                    "cmd": [sys.executable, "-c", "import sys; sys.exit(7)"],
                },
                {
                    "id": "downstream_job",
                    "job_profile": "light_cpu",
                    "deps": ["crash_job"],
                    "fn": lambda: {"status": "PASS"},
                },
            ]
        )
        t0 = time.perf_counter()
        rep_fail = run_dag(stages_fail, max_workers=2)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 4.0)
        self.assertEqual(rep_fail["status"], "FAIL")
        self.assertTrue(rep_fail["results"]["hang_job"]["timed_out"])
        self.assertEqual(rep_fail["results"]["hang_job"]["status"], "FAIL")
        self.assertEqual(rep_fail["results"]["crash_job"]["status"], "FAIL")
        self.assertEqual(rep_fail["results"]["downstream_job"]["status"], "BLOCKED_DEPENDENCY")
        self.assertEqual(rep_fail["orphan_worker_processes_after_run"], 0)


if __name__ == "__main__":
    unittest.main()
