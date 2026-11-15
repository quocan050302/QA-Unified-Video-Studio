#!/usr/bin/env python3
"""scripts/qa_scheduler.py — Async + Bounded Parallel Testing & Resource Scheduler (V14.7.4).

Features:
- inspect_resource_budget(): inspects available CPU, RAM, and Disk against mandatory reserves.
- choose_bounded_parallelism(): sets dynamic concurrency limit based on live headroom & job profile.
- build_dependency_dag(): stages independent tasks in topological waves with cycle & duplicate detection.
- enforce_resource_floor(): fail-closed check verifying minimum disk reserve (>= 6.0 GB).
- run_isolated_job(): executes job in isolated execution context, evaluates actual return values, captures duration, errors, output.
- run_dag(): executes staged dependency waves with bounded concurrency and fail-closed dependency tracking.
- TelemetrySampler: records time-series of CPU, RAM RSS, and disk headroom during asynchronous execution.
- publish_atomic_evidence(): atomically writes evidence reports without corrupting live runs.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.resource_guard import DEFAULT_MIN_DISK_GB, check_resources, get_disk_info, get_ram_info


class TelemetrySampler:
    """Continuous background resource sampler that records time-series metrics."""

    def __init__(self, workspace: str = ".", interval_sec: float = 0.5):
        self.workspace = workspace
        self.interval_sec = interval_sec
        self.samples: List[Dict[str, Any]] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.peak_rss_mb: float = 0.0
        self.min_disk_free_gb: float = 999999.0

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import psutil
            proc = psutil.Process()
        except ImportError:
            proc = None

        while not self._stop_event.is_set():
            t_now = round(time.time(), 3)
            budget = inspect_resource_budget(self.workspace)
            disk_free = budget.get("disk_free_gb", 0.0)
            ram_avail = budget.get("ram_available_gb", 0.0)
            
            rss_mb = 0.0
            if proc:
                try:
                    rss_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
                except Exception:
                    pass

            self.peak_rss_mb = max(self.peak_rss_mb, rss_mb)
            self.min_disk_free_gb = min(self.min_disk_free_gb, disk_free)

            self.samples.append({
                "timestamp": t_now,
                "disk_free_gb": disk_free,
                "ram_available_gb": ram_avail,
                "process_rss_mb": rss_mb,
            })
            time.sleep(self.interval_sec)

    def stop(self) -> Dict[str, Any]:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        
        return {
            "samples_count": len(self.samples),
            "peak_process_rss_mb": round(self.peak_rss_mb, 2),
            "min_disk_free_gb": round(self.min_disk_free_gb, 2) if self.min_disk_free_gb < 900000 else None,
            "samples": self.samples[-50:],  # preserve recent samples
        }


def inspect_resource_budget(
    workspace: str = ".",
    min_disk_gb: float = DEFAULT_MIN_DISK_GB,
    min_ram_gb: float = 1.0,
) -> Dict[str, Any]:
    """
    Check current host resource budget against safety minimums.
    Returns resource health dictionary.
    """
    ok, msg, info = check_resources(workspace, min_disk_gb=min_disk_gb, min_ram_gb=min_ram_gb)
    disk = info["disk"]
    ram = info["ram"]
    cpus = info["cpus"]

    return {
        "status": "PASS" if ok else "BLOCKED_RESOURCE",
        "healthy": ok,
        "message": msg,
        "disk_free_gb": disk["free_gb"],
        "disk_min_reserve_gb": min_disk_gb,
        "ram_available_gb": ram["available_gb"],
        "ram_min_reserve_gb": min_ram_gb,
        "cpu_count": cpus,
        "timestamp": time.time(),
    }


def choose_bounded_parallelism(
    requested_workers: Optional[int] = None,
    workspace: str = ".",
    job_profile: str = "general",
) -> int:
    """
    Calculate safe bounded concurrency limit based on headroom and job profile:
    - For 'heavy_render' jobs (1080p Playwright+FFmpeg): requires ~1.5 GB RAM headroom per worker.
      If RAM available < 3.5 GB or Disk < 8.0 GB: cap at 1.
    - For 'analysis' / 'general' jobs: min(4, max(2, cpu_count // 2)).
    """
    budget = inspect_resource_budget(workspace)
    ram_avail = budget.get("ram_available_gb", 2.0)
    disk_free = budget.get("disk_free_gb", 10.0)
    cpus = budget.get("cpu_count", 4)

    if not budget.get("healthy", True) or disk_free < 6.5 or ram_avail < 1.8:
        return 1

    if job_profile == "heavy_render":
        if ram_avail < 3.5 or disk_free < 8.0:
            return 1
        return min(2, max(1, cpus // 4))

    safe_cap = min(4, max(2, cpus // 2))
    if requested_workers is not None and requested_workers > 0:
        return min(requested_workers, safe_cap)
    return safe_cap


def enforce_resource_floor(
    workspace: str = ".",
    min_disk_gb: float = DEFAULT_MIN_DISK_GB,
) -> bool:
    """Fail-closed assertion verifying that disk headroom is strictly >= min_disk_gb."""
    budget = inspect_resource_budget(workspace, min_disk_gb=min_disk_gb)
    if not budget["healthy"]:
        raise RuntimeError(
            f"RESOURCE FLOOR BREACH: {budget['message']} (free={budget['disk_free_gb']} GB < min={min_disk_gb} GB)"
        )
    return True


def build_dependency_dag(jobs: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Partition a list of jobs with 'id' and 'dependencies' into topological execution stages.
    Enforces strict integrity:
    - Duplicate job IDs raise ValueError.
    - Unknown dependencies raise ValueError.
    - Cyclic or unresolvable dependencies raise ValueError.
    """
    # 1. Check duplicate IDs
    seen_ids: Set[str] = set()
    job_map: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        jid = job.get("id")
        if not jid:
            raise ValueError(f"Job missing mandatory 'id': {job}")
        if jid in seen_ids:
            raise ValueError(f"Duplicate job ID detected: '{jid}'")
        seen_ids.add(jid)
        job_map[jid] = job

    # 2. Check unknown dependencies
    for job in jobs:
        for dep in job.get("dependencies", []):
            if dep not in seen_ids:
                raise ValueError(f"Job '{job['id']}' has unknown dependency: '{dep}'")

    # 3. Topological stage partitioning
    completed_ids: Set[str] = set()
    remaining_jobs = list(jobs)
    stages: List[List[Dict[str, Any]]] = []

    while remaining_jobs:
        ready_stage = []
        for job in list(remaining_jobs):
            deps = set(job.get("dependencies", []))
            if deps.issubset(completed_ids):
                ready_stage.append(job)
                remaining_jobs.remove(job)

        if not ready_stage:
            unresolved = [j["id"] for j in remaining_jobs]
            raise ValueError(f"Cyclic or unresolvable dependencies detected in DAG: {unresolved}")

        stages.append(ready_stage)
        for j in ready_stage:
            completed_ids.add(j["id"])

    return stages


def run_isolated_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single task (either a callable or command) in an isolated context.
    Evaluates actual return values:
    - dict with status/valid/passed is inspected; failure values translate to FAIL/BLOCKED.
    - boolean False translates to FAIL.
    Captures duration, returncode, errors, and output.
    """
    job_id = job.get("id", "job_unknown")
    name = job.get("name", job_id)
    fn: Optional[Callable] = job.get("fn")
    cmd: Optional[List[str]] = job.get("cmd")
    timeout = job.get("timeout_sec", 120)
    validator: Optional[Callable[[Any], bool]] = job.get("validator")

    t0 = time.time()
    res: Dict[str, Any] = {
        "job_id": job_id,
        "name": name,
        "status": "RUNNING",
        "started_at": t0,
    }

    try:
        if fn:
            output = fn()
            res["output"] = output
            
            # Inspect actual return payload
            if isinstance(output, dict):
                st = output.get("status")
                is_valid = output.get("valid", True)
                is_passed = output.get("passed", True)
                
                if st in ("FAIL", "BLOCKED", "NOT_VERIFIED"):
                    res["status"] = st
                    res["error"] = output.get("error") or output.get("reason") or f"Explicit {st} returned by job"
                elif not is_valid or not is_passed:
                    res["status"] = "FAIL"
                    res["error"] = output.get("error") or output.get("reason") or "Job returned valid=False or passed=False"
                else:
                    res["status"] = st or "PASS"
            elif isinstance(output, bool):
                res["status"] = "PASS" if output else "FAIL"
                if not output:
                    res["error"] = "Callable returned False"
            else:
                res["status"] = "PASS"

            if validator and not validator(output):
                res["status"] = "FAIL"
                res["error"] = "Custom job validator rejected output"

        elif cmd:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            res["returncode"] = cp.returncode
            res["stdout"] = cp.stdout[-2000:] if cp.stdout else ""
            res["stderr"] = cp.stderr[-2000:] if cp.stderr else ""
            res["status"] = "PASS" if cp.returncode == 0 else "FAIL"
            if cp.returncode != 0:
                res["error"] = f"Command failed with exit code {cp.returncode}: {res['stderr'][-300:]}"
        else:
            res["status"] = "SKIPPED"
            res["error"] = "No command or function supplied"
    except subprocess.TimeoutExpired:
        res["status"] = "TIMEOUT"
        res["error"] = f"Job timed out after {timeout} seconds"
    except Exception as exc:
        res["status"] = "FAIL"
        res["error"] = str(exc)

    res["elapsed_sec"] = round(time.time() - t0, 3)
    return res


def run_dag(
    stages: List[List[Dict[str, Any]]],
    max_parallel: int = 2,
    sampler: Optional[TelemetrySampler] = None,
) -> Dict[str, Any]:
    """
    Execute DAG stages sequentially; jobs within each stage run under ThreadPoolExecutor(max_parallel).
    If a job fails, dependent jobs in subsequent stages fail-closed with BLOCKED_DEPENDENCY.
    """
    t_start = time.time()
    results: List[Dict[str, Any]] = []
    failed_job_ids: Set[str] = set()
    all_success = True

    if sampler:
        sampler.start()

    try:
        for stage_idx, stage_jobs in enumerate(stages):
            if not stage_jobs:
                continue

            # Check if any job in this stage depends on an already-failed job
            executable_jobs = []
            for j in stage_jobs:
                deps = set(j.get("dependencies", []))
                failed_deps = deps.intersection(failed_job_ids)
                if failed_deps:
                    r_blocked = {
                        "job_id": j.get("id"),
                        "name": j.get("name"),
                        "status": "BLOCKED_DEPENDENCY",
                        "error": f"Prerequisite job(s) failed: {sorted(list(failed_deps))}",
                        "elapsed_sec": 0.0,
                    }
                    results.append(r_blocked)
                    failed_job_ids.add(j.get("id"))
                    all_success = False
                else:
                    executable_jobs.append(j)

            if not executable_jobs:
                continue

            workers = min(max_parallel, len(executable_jobs))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(run_isolated_job, j) for j in executable_jobs]
                for f in futures:
                    r = f.result()
                    results.append(r)
                    if r.get("status") != "PASS":
                        failed_job_ids.add(r.get("job_id"))
                        all_success = False
    finally:
        telemetry_data = sampler.stop() if sampler else {}

    return {
        "status": "PASS" if all_success else "FAIL",
        "total_jobs": len(results),
        "passed_jobs": sum(1 for r in results if r.get("status") == "PASS"),
        "failed_jobs": sum(1 for r in results if r.get("status") != "PASS"),
        "total_elapsed_sec": round(time.time() - t_start, 3),
        "telemetry": telemetry_data,
        "results": results,
    }


def publish_atomic_evidence(evidence_data: Dict[str, Any], output_path: Path | str) -> Path:
    """Write evidence report atomically with .tmp staging and os.replace."""
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    temp_p = out_p.with_suffix(".tmp.json")
    with open(temp_p, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2, ensure_ascii=False)
    os.replace(temp_p, out_p)
    return out_p


if __name__ == "__main__":
    budget = inspect_resource_budget()
    parallelism = choose_bounded_parallelism()
    print("Resource Budget:", json.dumps(budget, indent=2))
    print(f"Bounded Concurrency Limit: {parallelism}")
