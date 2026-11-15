"""tests/test_mutation_truth_v14_7_5.py — Strict Mutation Truth & Fail-Closed QA Suite (V14.7.5 / C4 & C6)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.production_fingerprint as prod_fp
import tools.cinematic_camera as cine_cam
import tools.temporal_visual_qa as tvqa


class TestMutationTruthV1475(unittest.TestCase):
    def test_01_scoped_detector_breakage_must_fail_and_restore_cleanly(self):
        """Intentionally breaking each production detector causes negative suite to FAIL, then restores with zero state leakage."""
        orig_snap_fn = cine_cam.audit_camera_snap_keyframes
        orig_inspect_fn = prod_fp.inspect_media_file
        orig_cache_fn = prod_fp.validate_cache_hit
        orig_cont_fn = tvqa.audit_temporal_continuity

        # Baseline: unmutated negative fixtures must pass 15/15
        base = tvqa.run_negative_fixtures_tests()
        self.assertTrue(base["all_fixtures_passed"])
        self.assertEqual(base["total_fixtures"], 15)

        # 1. Break camera snap detector -> negative suite MUST FAIL on camera_snap
        with mock.patch.object(cine_cam, "audit_camera_snap_keyframes", return_value=(False, [])):
            broken_1 = tvqa.run_negative_fixtures_tests()
            self.assertFalse(broken_1["all_fixtures_passed"])
            self.assertFalse(broken_1["fixtures"]["camera_snap"]["passed"])

        # Verify restored cleanly
        self.assertIs(cine_cam.audit_camera_snap_keyframes, orig_snap_fn)

        # 2. Break silent audio guard -> negative suite MUST FAIL on silent_audio
        def _blind_silent_inspect(mp4_path, expected_specs=None, require_audio=False, full_decode=False):
            res = orig_inspect_fn(mp4_path, expected_specs=expected_specs, require_audio=False, full_decode=full_decode)
            res["valid"] = True
            res["errors"] = []
            res["error"] = None
            return res

        with mock.patch.object(prod_fp, "inspect_media_file", side_effect=_blind_silent_inspect):
            broken_2 = tvqa.run_negative_fixtures_tests()
            self.assertFalse(broken_2["all_fixtures_passed"])
            self.assertFalse(broken_2["fixtures"]["silent_audio"]["passed"])

        self.assertIs(prod_fp.inspect_media_file, orig_inspect_fn)

        # 3. Break stale cache validator -> negative suite MUST FAIL on stale_receipt
        with mock.patch.object(
            prod_fp,
            "validate_cache_hit",
            return_value={"hit": True, "status": "CACHE_HIT_VERIFIED", "reason": "forced"},
        ):
            broken_3 = tvqa.run_negative_fixtures_tests()
            self.assertFalse(broken_3["all_fixtures_passed"])
            self.assertFalse(broken_3["fixtures"]["stale_receipt"]["passed"])

        self.assertIs(prod_fp.validate_cache_hit, orig_cache_fn)

        # 4. Break disappearance detector -> negative suite MUST FAIL on actor_disappearance
        with mock.patch.object(tvqa, "audit_temporal_continuity", return_value=(False, False, 0.0, [])):
            broken_4 = tvqa.run_negative_fixtures_tests()
            self.assertFalse(broken_4["all_fixtures_passed"])
            self.assertFalse(broken_4["fixtures"]["actor_disappearance"]["passed"])

        self.assertIs(tvqa.audit_temporal_continuity, orig_cont_fn)

        # Post-restore: all 15 fixtures pass again with zero global state leakage
        restored = tvqa.run_negative_fixtures_tests()
        self.assertTrue(restored["all_fixtures_passed"])
        self.assertEqual(restored["passed_fixtures"], 15)

    def test_02_disposable_subprocess_mutations_all_killed(self):
        """run_mutation_tests executes real child subprocesses and kills all 4 mutants."""
        with tempfile.TemporaryDirectory() as tmp:
            mut_res = tvqa.run_mutation_tests(failure_logs_dir=Path(tmp))
            self.assertEqual(mut_res["status"], "PASS")
            self.assertTrue(mut_res["all_mutations_killed"])
            self.assertEqual(mut_res["total_mutations"], 4)
            self.assertEqual(mut_res["killed_mutations"], 4)
            for m in mut_res["mutations"]:
                self.assertEqual(m["normal_exit_code"], 0, f"Normal probe failed for {m['probe_id']}")
                self.assertNotEqual(m["mutant_exit_code"], 0, f"Mutant survived for {m['probe_id']}")
                self.assertTrue(len(m["output_diff"]) > 0)
                self.assertTrue(Path(m["failure_log_path"]).is_file())

    def test_03_fail_closed_on_missing_media_and_empty_shots(self):
        """audit_project_temporal_visual fails closed on missing MP4 or zero-shot storyboard."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            (proj / "story").mkdir(parents=True)
            (proj / "story" / "shots.json").write_text('{"shots": []}', encoding="utf-8")
            ev = Path(tmp) / "ev"

            # Missing MP4 -> FAIL
            rep_missing = tvqa.audit_project_temporal_visual(proj, proj / "missing.mp4", ev, run_negative_suite=False)
            self.assertFalse(rep_missing.all_passed)
            self.assertEqual(rep_missing.technical_verdict, "FAIL")

            # Valid MP4 but empty shots -> FAIL (never default PASS)
            import subprocess
            dummy_mp4 = proj / "dummy.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
                    "-c:v", "libx264", str(dummy_mp4),
                ],
                check=True,
                capture_output=True,
            )
            rep_empty = tvqa.audit_project_temporal_visual(proj, dummy_mp4, ev, run_negative_suite=False)
            self.assertFalse(rep_empty.all_passed)
            self.assertEqual(rep_empty.total_shots, 0)
            self.assertEqual(rep_empty.technical_verdict, "FAIL")

    def test_04_coverage_incomplete_when_dynamic_budget_insufficient(self):
        """build_shot_sample_timestamps marks coverage_complete=False if cap forces < 4.0 fps on dynamic shot."""
        ts_ok, cov_ok = tvqa.build_shot_sample_timestamps(0.0, 5.0, 5.0, "ADVANCE", fps=24.0, max_samples_per_shot=28)
        self.assertTrue(cov_ok)
        self.assertGreaterEqual(len(ts_ok) / 5.0, 4.0)

        ts_low, cov_low = tvqa.build_shot_sample_timestamps(0.0, 5.0, 5.0, "ADVANCE", fps=24.0, max_samples_per_shot=8)
        self.assertFalse(cov_low)


if __name__ == "__main__":
    unittest.main()
