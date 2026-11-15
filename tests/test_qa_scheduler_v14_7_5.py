"""tests/test_qa_scheduler_v14_7_5.py — Strict TDD Unit Suite for scripts/qa_scheduler.py (V14.7.5 / C1)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import psutil

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.qa_scheduler import (
    TelemetrySampler,
    build_dependency_dag,
    choose_bounded_parallelism,
    inspect_resource_budget,
    publish_atomic_evidence,
    run_dag,
    run_isolated_job,
)


class TestQASchedulerV1475(unittest.TestCase):
    def test_01_concurrent_jobs_measured_interval_overlap(self):
        """Two independent jobs run concurrently with verified interval overlap and max_active_workers >= 2."""
        with tempfile.TemporaryDirectory() as tmp:
            out_a = Path(tmp) / "a.json"
            out_b = Path(tmp) / "b.json"
            jobs = [
                {
                    "id": "job_a",
                    "cmd": [
                        sys.executable,
                        "-c",
                        f"import time, pathlib; time.sleep(0.40); pathlib.Path({str(out_a)!r}).write_text('{{\"ok\":1}}')",
                    ],
                    "job_profile": "light_cpu",
                    "expected_artifacts": [str(out_a)],
                },
                {
                    "id": "job_b",
                    "cmd": [
                        sys.executable,
                        "-c",
                        f"import time, pathlib; time.sleep(0.40); pathlib.Path({str(out_b)!r}).write_text('{{\"ok\":2}}')",
                    ],
                    "job_profile": "light_cpu",
                    "expected_artifacts": [str(out_b)],
                },
            ]
            stages = build_dependency_dag(jobs)
            self.assertEqual(len(stages), 1)
            res = run_dag(stages, max_workers=2, min_disk_gb=1.0, min_ram_gb=0.2)
            self.assertEqual(res["status"], "PASS")
            self.assertEqual(res["total_jobs"], 2)
            self.assertEqual(res["passed_jobs"], 2)
            self.assertGreaterEqual(res["max_active_workers"], 2)
            self.assertGreaterEqual(res["concurrency_proof"]["overlapping_pairs_count"], 1)
            self.assertGreater(res["concurrency_proof"]["max_overlap_sec"], 0.10)
            self.assertLess(res["elapsed_sec"], 0.78)

    def test_02_prerequisite_fail_blocks_dependent(self):
        """Failed prerequisite job blocks downstream dependent job and fails mandatory DAG."""
        marker = {"ran_child": False}

        def _child_fn():
            marker["ran_child"] = True
            return {"status": "PASS"}

        jobs = [
            {
                "id": "prereq_fail",
                "cmd": [sys.executable, "-c", "import sys; sys.exit(2)"],
                "deps": [],
                "mandatory": True,
            },
            {
                "id": "downstream_dep",
                "fn": _child_fn,
                "deps": ["prereq_fail"],
                "mandatory": True,
            },
        ]
        stages = build_dependency_dag(jobs)
        res = run_dag(stages, max_workers=2, min_disk_gb=1.0, min_ram_gb=0.2)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["all_succeeded"])
        self.assertEqual(res["results"]["prereq_fail"]["status"], "FAIL")
        self.assertEqual(res["results"]["downstream_dep"]["status"], "BLOCKED_DEPENDENCY")
        self.assertFalse(marker["ran_child"])

    def test_03_unknown_dep_duplicate_and_cycle_rejected(self):
        """Duplicate IDs, unknown dependencies, and cycles raise ValueError."""
        with self.assertRaises(ValueError):
            build_dependency_dag([
                {"id": "dup", "fn": lambda: {"status": "PASS"}},
                {"id": "dup", "fn": lambda: {"status": "PASS"}},
            ])

        with self.assertRaises(ValueError):
            build_dependency_dag([
                {"id": "a", "fn": lambda: {"status": "PASS"}, "deps": ["ghost_job"]},
            ])

        with self.assertRaises(ValueError):
            build_dependency_dag([
                {"id": "a", "fn": lambda: {"status": "PASS"}, "deps": ["b"]},
                {"id": "b", "fn": lambda: {"status": "PASS"}, "deps": ["a"]},
            ])

        with self.assertRaises(ValueError):
            build_dependency_dag([
                {"id": "self_loop", "fn": lambda: {"status": "PASS"}, "deps": ["self_loop"]},
            ])

    def test_04_command_key_mismatch_rejected(self):
        """Non-canonical 'command' key is rejected in both build_dependency_dag and run_isolated_job."""
        bad_job = {"id": "bad_cmd_key", "command": [sys.executable, "-c", "exit(0)"]}
        with self.assertRaises(ValueError):
            build_dependency_dag([bad_job])

        iso = run_isolated_job(bad_job)
        self.assertEqual(iso["status"], "FAIL")
        self.assertIn("command", iso["error"])

    def test_05_callable_none_or_unstructured_not_pass(self):
        """Callable returning None or dict without status/valid/passed returns NOT_VERIFIED, never PASS."""
        r_none = run_isolated_job({"id": "fn_none", "fn": lambda: None})
        self.assertEqual(r_none["status"], "NOT_VERIFIED")

        r_empty_dict = run_isolated_job({"id": "fn_empty", "fn": lambda: {"foo": "bar"}})
        self.assertEqual(r_empty_dict["status"], "NOT_VERIFIED")

        r_unknown_status = run_isolated_job({"id": "fn_unk", "fn": lambda: {"status": "MAYBE_OK"}})
        self.assertEqual(r_unknown_status["status"], "NOT_VERIFIED")

        # Explicit validator allows custom structured return
        r_valid = run_isolated_job({
            "id": "fn_validated",
            "fn": lambda: {"count": 5},
            "validator": lambda d: (d.get("count") == 5, "expected 5"),
        })
        self.assertEqual(r_valid["status"], "PASS")

    def test_06_missing_expected_artifact_fails_even_if_exit_zero(self):
        """Subprocess exiting 0 fails when expected_artifacts are missing or empty."""
        with tempfile.TemporaryDirectory() as tmp:
            missing_file = Path(tmp) / "never_written.json"
            empty_file = Path(tmp) / "empty.json"
            empty_file.write_text("", encoding="utf-8")

            r_miss = run_isolated_job({
                "id": "art_miss",
                "cmd": [sys.executable, "-c", "print('ok')"],
                "expected_artifacts": [str(missing_file)],
            })
            self.assertEqual(r_miss["status"], "FAIL")
            self.assertEqual(r_miss["returncode"], 0)
            self.assertIn("never_written.json", r_miss["error"])

            r_empty = run_isolated_job({
                "id": "art_empty",
                "cmd": [sys.executable, "-c", "print('ok')"],
                "expected_artifacts": [str(empty_file)],
            })
            self.assertEqual(r_empty["status"], "FAIL")

    def test_07_timeout_kills_child_process_tree(self):
        """Subprocess timeout terminates both parent subprocess and its spawned grandchild process."""
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "grandchild.pid"
            script = (
                "import subprocess, sys, time, pathlib; "
                "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
                f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); "
                "time.sleep(30)"
            )
            res = run_isolated_job({
                "id": "timeout_tree",
                "cmd": [sys.executable, "-c", script],
                "timeout_sec": 0.45,
            })
            self.assertEqual(res["status"], "FAIL")
            self.assertTrue(res["timed_out"])
            self.assertTrue(pid_file.is_file(), "Grandchild PID file should have been written before timeout")
            grandchild_pid = int(pid_file.read_text().strip())
            time.sleep(0.15)
            alive = psutil.pid_exists(grandchild_pid)
            if alive:
                try:
                    st = psutil.Process(grandchild_pid).status()
                    alive = st != psutil.STATUS_ZOMBIE
                except psutil.NoSuchProcess:
                    alive = False
            self.assertFalse(alive, f"Grandchild process {grandchild_pid} must be terminated on timeout")

    def test_08_low_disk_floor_blocks(self):
        """Disk below reserve floor triggers BLOCKED_RESOURCE without executing jobs."""
        budget = inspect_resource_budget(
            min_disk_gb=6.0,
            min_ram_gb=1.0,
            estimated_scratch_gb=2.0,
            extra_margin_gb=1.0,
            _override_disk_free_gb=7.5,  # < 6 + 2 + 1 = 9.0 GiB
        )
        self.assertFalse(budget["healthy"])
        self.assertEqual(budget["status"], "BLOCKED_RESOURCE")

        stages = build_dependency_dag([{"id": "j1", "fn": lambda: {"status": "PASS"}}])
        dag_res = run_dag(
            stages,
            budget_inspector=lambda: inspect_resource_budget(
                min_disk_gb=6.0, min_ram_gb=1.0, _override_disk_free_gb=4.5
            ),
        )
        self.assertEqual(dag_res["status"], "BLOCKED_RESOURCE")
        self.assertEqual(dag_res["results"]["j1"]["status"], "BLOCKED_RESOURCE")

    def test_09_low_ram_floor_blocks_and_terminates_breaching_worker(self):
        """Low RAM blocks DAG and heavy_render caps to 1 when RAM < 4 GiB; mid-run breach terminates child."""
        low_ram_budget = inspect_resource_budget(
            min_disk_gb=6.0, min_ram_gb=1.0, _override_ram_available_gb=0.6
        )
        self.assertEqual(low_ram_budget["status"], "BLOCKED_RESOURCE")
        self.assertEqual(choose_bounded_parallelism(low_ram_budget, "light_cpu"), 0)

        mid_ram_budget = inspect_resource_budget(
            min_disk_gb=6.0, min_ram_gb=1.0, _override_disk_free_gb=20.0, _override_ram_available_gb=3.2
        )
        self.assertEqual(choose_bounded_parallelism(mid_ram_budget, "heavy_render", max_workers_cap=4), 1)

        # Mid-run breach terminates active child process group
        calls = {"n": 0}

        def _dynamic_budget():
            calls["n"] += 1
            # Healthy on initial check, breaches on subsequent sample ticks
            ram = 3.0 if calls["n"] <= 2 else 0.4
            return inspect_resource_budget(
                min_disk_gb=6.0, min_ram_gb=1.0, _override_disk_free_gb=20.0, _override_ram_available_gb=ram
            )

        stages = build_dependency_dag([
            {
                "id": "long_worker",
                "cmd": [sys.executable, "-c", "import time; time.sleep(10)"],
                "timeout_sec": 15.0,
            }
        ])
        t0 = time.perf_counter()
        dag_res = run_dag(stages, min_disk_gb=6.0, min_ram_gb=1.0, budget_inspector=_dynamic_budget)
        elapsed = time.perf_counter() - t0
        self.assertEqual(dag_res["status"], "BLOCKED_RESOURCE")
        self.assertEqual(dag_res["results"]["long_worker"]["status"], "BLOCKED_RESOURCE")
        self.assertLess(elapsed, 4.0, "Mid-run breach should terminate worker promptly")

    def test_10_zero_job_dag_does_not_succeed(self):
        """Empty / zero-job DAG fails closed and never reports all_succeeded=True."""
        stages = build_dependency_dag([])
        self.assertEqual(stages, [])
        res = run_dag(stages)
        self.assertEqual(res["total_jobs"], 0)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["all_succeeded"])

    def test_11_atomic_evidence_schema_and_duplicate_claim_guard(self):
        """publish_atomic_evidence validates required keys and prevents duplicate job claims in one run."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ev.json"
            with self.assertRaises(ValueError):
                publish_atomic_evidence(p, {"a": 1}, required_keys=["a", "missing_key"])

            publish_atomic_evidence(
                p, {"a": 1, "b": 2}, run_id="run_test_11", writer_job_id="job_1", required_keys=["a", "b"]
            )
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["b"], 2)

            with self.assertRaises(RuntimeError):
                publish_atomic_evidence(
                    p, {"a": 3, "b": 4}, run_id="run_test_11", writer_job_id="job_2", required_keys=["a", "b"]
                )


if __name__ == "__main__":
    unittest.main()
