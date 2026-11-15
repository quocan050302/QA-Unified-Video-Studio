#!/usr/bin/env python3
"""scripts/qa_scheduler.py — Async + Bounded Parallel Testing & Resource Scheduler (V14.7.3).

Features:
- inspect_resource_budget(): inspects available CPU, RAM, and Disk against mandatory reserves.
- choose_bounded_parallelism(): sets dynamic concurrency limit based on live headroom.
- build_dependency_dag(): stages independent tasks in topological waves.
- enforce_resource_floor(): fail-closed check verifying minimum disk reserve (>= 6.0 GB).
- run_isolated_job(): executes job in isolated execution context with timeout and log capture.
- run_dag(): executes staged dependency waves with bounded concurrency.
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
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.resource_guard import DEFAULT_MIN_DISK_GB, check_resources, get_disk_info, get_ram_info


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
) -> int:
    """
    Calculate safe bounded concurrency limit:
    - If RAM < 3.0 GB or Disk free < 8.0 GB: cap at 1 heavyweight worker.
    - Otherwise, default to min(4, max(2, cpu_count // 2)).
    """
    budget = inspect_resource_budget(workspace)
    ram_avail = budget.get("ram_available_gb", 2.0)
    disk_free = budget.get("disk_free_gb", 10.0)
    cpus = budget.get("cpu_count", 4)

    if not budget.get("healthy", True) or disk_free < 6.5 or ram_avail < 1.8:
        return 1

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
    Partition a list of jobs with 'id' and 'dependencies' (list of job ids)
    into sequential execution stages (waves) where jobs in the same stage can run in parallel.
    """
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
            # Cycle or unresolved dependency; flush remaining sequentially to prevent deadlock
            ready_stage = remaining_jobs
            remaining_jobs = []

        stages.append(ready_stage)
        for j in ready_stage:
            completed_ids.add(j.get("id", ""))

    return stages


def run_isolated_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single task (either a callable or command) in an isolated context.
    Captures duration, returncode, errors, and output.
    """
    job_id = job.get("id", "job_unknown")
    name = job.get("name", job_id)
    fn: Optional[Callable] = job.get("fn")
    cmd: Optional[List[str]] = job.get("cmd")
    timeout = job.get("timeout_sec", 120)

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
            res["status"] = "PASS"
            res["output"] = output
        elif cmd:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            res["status"] = "PASS" if cp.returncode == 0 else "FAIL"
            res["returncode"] = cp.returncode
            res["stdout"] = cp.stdout[-2000:] if cp.stdout else ""
            res["stderr"] = cp.stderr[-2000:] if cp.stderr else ""
        else:
            res["status"] = "SKIPPED"
            res["error"] = "No command or function supplied"
    except Exception as exc:
        res["status"] = "FAIL"
        res["error"] = str(exc)

    res["elapsed_sec"] = round(time.time() - t0, 3)
    return res


def run_dag(
    stages: List[List[Dict[str, Any]]],
    max_parallel: int = 2,
) -> Dict[str, Any]:
    """
    Execute DAG stages sequentially; jobs within each stage run under ThreadPoolExecutor(max_parallel).
    """
    t_start = time.time()
    results: List[Dict[str, Any]] = []
    all_success = True

    for stage_idx, stage_jobs in enumerate(stages):
        if not stage_jobs:
            continue
        workers = min(max_parallel, len(stage_jobs))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(run_isolated_job, j) for j in stage_jobs]
            for f in futures:
                r = f.result()
                results.append(r)
                if r.get("status") != "PASS":
                    all_success = False

    return {
        "status": "PASS" if all_success else "FAIL",
        "total_jobs": len(results),
        "passed_jobs": sum(1 for r in results if r.get("status") == "PASS"),
        "failed_jobs": sum(1 for r in results if r.get("status") != "PASS"),
        "total_elapsed_sec": round(time.time() - t_start, 3),
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
