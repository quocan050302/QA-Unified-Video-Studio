#!/usr/bin/env python3
"""Unit + real disposable video repair tests for tools/shot_repair.py (V14.7.5 / C5)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.shot_repair import (
    _normalize_qa_report,
    classify_failed_shots,
    test_defect_injection_and_repair,
)
from tools.temporal_visual_qa import TemporalQAReport, TemporalShotAudit


class TestShotRepairV1475(unittest.TestCase):
    def test_01_typed_adapter_and_fail_closed_unknown_status(self) -> None:
        """Typed adapter accepts TemporalQAReport Pydantic model and rejects empty/unknown status."""
        empty_rep = TemporalQAReport(project_id="empty_proj", mp4_path="/tmp/x.mp4", total_shots=0)
        norm_empty = _normalize_qa_report(empty_rep)
        self.assertFalse(norm_empty["valid_report"])
        self.assertEqual(norm_empty["technical_verdict"], "NOT_VERIFIED")

        unknown_dict = {
            "total_shots": 1,
            "technical_verdict": "MYSTERY_VERDICT",
            "shot_audits": {"s01": {"passed": True, "technical_verdict": "MYSTERY_VERDICT"}},
        }
        norm_unk = _normalize_qa_report(unknown_dict)
        self.assertFalse(norm_unk["valid_report"])
        self.assertEqual(norm_unk["technical_verdict"], "NOT_VERIFIED")

        pydantic_rep = TemporalQAReport(
            project_id="p1",
            mp4_path="/tmp/p1.mp4",
            total_shots=1,
            passed_shots=0,
            all_passed=False,
            technical_verdict="FAIL",
            shot_audits={
                "s01": TemporalShotAudit(
                    shot_id="s01",
                    action_kind="ADVANCE",
                    tpl="scene",
                    expected_subject="actor",
                    duration=2.0,
                    start_time=0.0,
                    end_time=2.0,
                    passed=False,
                    technical_verdict="FAIL",
                    sudden_disappearance=True,
                    diagnostics=["Temporal defect: Actor suddenly disappeared at t=0.80s without shot cut"],
                )
            },
        )
        classified = classify_failed_shots(pydantic_rep)
        self.assertEqual(len(classified), 1)
        self.assertEqual(classified[0]["shot_id"], "s01")
        self.assertEqual(classified[0]["category"], "continuity")

    def test_02_real_disposable_video_repair_and_manual_lock_protection(self) -> None:
        """Full end-to-end disposable 3-shot Squire render -> defect QA -> repair -> rerender -> mux -> QA."""
        res = test_defect_injection_and_repair()
        self.assertEqual(res["test_status"], "PASS")
        self.assertEqual(res["initial_verdict"], "FAIL")
        self.assertEqual(res["final_verdict"], "VISUAL_TECH_PASS")
        self.assertTrue(res["mp4_rebuilt_and_changed"])
        self.assertTrue(res["receipt_verified"])
        self.assertTrue(res["manual_locked_preserved"])
        self.assertEqual(res["locked_defect_status"], "BLOCKED_MANUAL_REVIEW")
        self.assertTrue(res["locked_defect_hash_preserved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
