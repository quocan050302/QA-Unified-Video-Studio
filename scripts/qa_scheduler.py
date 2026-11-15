"""scripts/qa_scheduler.py — Async + Bounded Parallel Testing & Resource Scheduler (V14.7.5).

Provides:
- inspect_resource_budget: Checks free disk, free inodes, available RAM, and CPU count; returns BLOCKED_RESOURCE if unsafe.
- choose_bounded_parallelism: Profiles light_cpu, visual_decode, heavy_render; caps 1080p heavy renders to 1 when RAM < 4 GiB.
- build_dependency_dag: Rejects duplicate IDs, unknown deps, cycles, and non-canonical 'command' keys; returns deterministic topological waves.
- run_isolated_job: Enforces canonical 'cmd' or 'fn', process-group isolation + timeout tree kill, artifact & return-value validation (fail-closed on None/missing status).
- run_dag: Executes waves with real bounded concurrency, interval overlap measurement, dependency failure propagation, and zero-job fail-closed guard.
- TelemetrySampler: Recursive process-tree RSS (Python + Node/Playwright/Chromium/FFmpeg children), CPU/RAM/disk/inodes, bounded sample buffer with loss accounting, and active child process-group termination on resource floor breach.
- publish_atomic_evidence: Unique per-run/per-thread temp file, schema validation, fsync, collision guard, and atomic os.replace.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import psutil

ROOT_DIR = Path(__file__).resolve().parent.parent

DISK_MIN_RESERVE_GB = 6.0
RAM_MIN_RESERVE_GB = 1.0

KNOWN_PASS_STATUSES = {
    "PASS",
    "PRODUCED",
    "CACHE_HIT_VERIFIED",
    "VISUAL_TECH_PASS",
    "REPAIRED",
    "FLOW_READY",
}
KNOWN_BLOCKED_STATUSES = {
    "BLOCKED",
    "BLOCKED_RESOURCE",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_MANUAL_REVIEW",
    "BLOCKED_NO_SPEECH_PROVIDER",
}
KNOWN_SPECIAL_STATUSES = {
    "NOT_AVAILABLE",
    "NOT_VERIFIED",
}
KNOWN_FAIL_STATUSES = {
    "FAIL",
    "TECH_FAILED",
    "FLOW_HOLD",
    "COVERAGE_INCOMPLETE",
}

_INFLIGHT_EVIDENCE_LOCK = threading.Lock()
_INFLIGHT_EVIDENCE_PATHS: Set[Path] = set()
_RUN_EVIDENCE_CLAIMS: Dict[Tuple[str, Path], str] = {}


def _utc_iso(ts: Optional[float] = None) -> str:
    val = time.time() if ts is None else ts
    return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()


def _get_free_inodes(path: Path) -> Optional[int]:
    try:
        st = os.statvfs(str(path))
        return int(st.f_favail)
    except Exception:
        return None


def inspect_resource_budget(
    min_disk_gb: float = DISK_MIN_RESERVE_GB,
    min_ram_gb: float = RAM_MIN_RESERVE_GB,
    estimated_scratch_gb: float = 0.0,
    extra_margin_gb: float = 0.0,
    target_path: Optional[Path | str] = None,
    _override_disk_free_gb: Optional[float] = None,
    _override_ram_available_gb: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Inspect current host resource budget: disk free space, free inodes, available RAM, and CPU cores.
    Enforces non-negotiable minimum floors: min_disk_gb >= 6.0 GiB and min_ram_gb >= 1.0 GiB.
    Preflight floor requires free >= min_disk_gb + estimated_scratch_gb + extra_margin_gb.
    """
    eff_min_disk_gb = max(DISK_MIN_RESERVE_GB, float(min_disk_gb))
    eff_min_ram_gb = max(RAM_MIN_RESERVE_GB, float(min_ram_gb))
    check_dir = Path(target_path) if target_path else ROOT_DIR
    if not check_dir.exists():
        check_dir = ROOT_DIR

    disk = shutil.disk_usage(check_dir)
    disk_free_gb = (
        float(_override_disk_free_gb)
        if _override_disk_free_gb is not None
        else round(disk.free / (1024**3), 3)
    )

    vm = psutil.virtual_memory()
    ram_avail_gb = (
        float(_override_ram_available_gb)
        if _override_ram_available_gb is not None
        else round(vm.available / (1024**3), 3)
    )
    ram_total_gb = round(vm.total / (1024**3), 2)
    cpu_count = os.cpu_count() or 2
    free_inodes = _get_free_inodes(check_dir)

    required_disk_gb = round(
        eff_min_disk_gb + max(0.0, float(estimated_scratch_gb)) + max(0.0, float(extra_margin_gb)),
        3,
    )

    reasons: List[str] = []
    if disk_free_gb < required_disk_gb:
        reasons.append(
            f"Disk free ({disk_free_gb:.2f} GiB) < required reserve ({required_disk_gb:.2f} GiB = "
            f"floor {eff_min_disk_gb:.2f} + scratch {estimated_scratch_gb:.2f} + margin {extra_margin_gb:.2f})"
        )
    if ram_avail_gb < eff_min_ram_gb:
        reasons.append(
            f"Available RAM ({ram_avail_gb:.2f} GiB) < minimum reserve ({eff_min_ram_gb:.2f} GiB)"
        )
    if free_inodes is not None and free_inodes < 10000:
        reasons.append(f"Free inodes critically low ({free_inodes} < 10000)")

    healthy = len(reasons) == 0
    return {
        "status": "PASS" if healthy else "BLOCKED_RESOURCE",
        "healthy": healthy,
        "message": "OK" if healthy else "; ".join(reasons),
        "disk_free_gb": disk_free_gb,
        "disk_min_reserve_gb": eff_min_disk_gb,
        "disk_required_gb": required_disk_gb,
        "estimated_scratch_gb": float(estimated_scratch_gb),
        "extra_margin_gb": float(extra_margin_gb),
        "free_inodes": free_inodes,
        "ram_available_gb": ram_avail_gb,
        "ram_total_gb": ram_total_gb,
        "ram_min_reserve_gb": eff_min_ram_gb,
        "cpu_count": cpu_count,
        "timestamp": time.time(),
    }


def normalize_job_profile(profile: Optional[str]) -> str:
    p = (profile or "light_cpu").strip().lower()
    if p in ("heavy", "heavy_render", "render_1080p"):
        return "heavy_render"
    if p in ("visual_decode", "decode", "medium"):
        return "visual_decode"
    return "light_cpu"


def choose_bounded_parallelism(
    budget: Dict[str, Any],
    job_profile: str = "light_cpu",
    max_workers_cap: int = 4,
    historical_peak_rss_mb: float = 0.0,
    estimated_scratch_gb: float = 0.25,
) -> int:
    """
    Determine safe bounded worker concurrency based on real-time RAM, CPU, disk scratch,
    historical peak worker RSS, and workload profile (light_cpu, visual_decode, heavy_render).
    """
    if not budget.get("healthy", False):
        return 0

    profile = normalize_job_profile(job_profile)
    ram_avail = float(budget.get("ram_available_gb", 1.0))
    ram_floor = float(budget.get("ram_min_reserve_gb", RAM_MIN_RESERVE_GB))
    disk_free = float(budget.get("disk_free_gb", 6.0))
    disk_floor = float(budget.get("disk_min_reserve_gb", DISK_MIN_RESERVE_GB))
    cpus = int(budget.get("cpu_count", 2))

    usable_ram = max(0.0, ram_avail - ram_floor)
    usable_disk = max(0.0, disk_free - disk_floor)

    if ram_avail < ram_floor or disk_free < disk_floor:
        return 0

    hist_rss_gb = max(0.0, float(historical_peak_rss_mb) / 1024.0)
    scratch_per_worker = max(0.05, float(estimated_scratch_gb))
    disk_cap = max(1, int(usable_disk // scratch_per_worker)) if usable_disk >= scratch_per_worker else 1

    if profile == "heavy_render":
        # Mandatory C1 safety rule: 1080p render max 1 by default if RAM < 4 GiB
        if ram_avail < 4.0:
            return 1
        est_worker_ram = max(1.6, hist_rss_gb)
        ram_cap = max(1, int(usable_ram // est_worker_ram))
        cpu_cap = max(1, cpus // 4)
        return max(1, min(max_workers_cap, 2, ram_cap, cpu_cap, disk_cap))

    if profile == "visual_decode":
        est_worker_ram = max(0.65, hist_rss_gb)
        ram_cap = max(1, int(usable_ram // est_worker_ram))
        cpu_cap = max(1, cpus // 2)
        return max(1, min(max_workers_cap, ram_cap, cpu_cap, disk_cap))

    # light_cpu
    est_worker_ram = max(0.35, hist_rss_gb)
    ram_cap = max(1, int(usable_ram // est_worker_ram))
    cpu_cap = max(1, cpus - 2 if cpus > 2 else 1)
    return max(1, min(max_workers_cap, ram_cap, cpu_cap, disk_cap))


def sample_process_tree(root_pid: Optional[int] = None) -> Dict[str, Any]:
    """Measure RSS and process names across root_pid and all recursive descendants."""
    pid = root_pid if root_pid is not None else os.getpid()
    parent_rss_mb = 0.0
    children_rss_mb = 0.0
    child_entries: List[Dict[str, Any]] = []
    try:
        parent = psutil.Process(pid)
        parent_rss_mb = parent.memory_info().rss / (1024**2)
        for ch in parent.children(recursive=True):
            try:
                rss_mb = ch.memory_info().rss / (1024**2)
                children_rss_mb += rss_mb
                child_entries.append({
                    "pid": ch.pid,
                    "name": ch.name(),
                    "rss_mb": round(rss_mb, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

    total_rss_mb = parent_rss_mb + children_rss_mb
    return {
        "root_pid": pid,
        "parent_rss_mb": round(parent_rss_mb, 2),
        "children_rss_mb": round(children_rss_mb, 2),
        "tree_rss_mb": round(total_rss_mb, 2),
        "child_count": len(child_entries),
        "children": child_entries[:25],
    }


def terminate_process_group_safely(proc: subprocess.Popen, grace_sec: float = 1.5) -> Dict[str, Any]:
    """Terminate a spawned subprocess group (started with start_new_session=True) with grace then SIGKILL."""
    info = {"pid": proc.pid, "terminated": False, "killed": False, "error": None}
    if proc.poll() is not None:
        return info
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        info["terminated"] = True
    except ProcessLookupError:
        return info
    except Exception as exc:
        info["error"] = str(exc)
        try:
            proc.terminate()
            info["terminated"] = True
        except Exception:
            pass

    deadline = time.perf_counter() + max(0.1, grace_sec)
    while time.perf_counter() < deadline:
        if proc.poll() is not None:
            return info
        time.sleep(0.05)

    if proc.poll() is None:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
            info["killed"] = True
        except ProcessLookupError:
            pass
        except Exception:
            try:
                proc.kill()
                info["killed"] = True
            except Exception:
                pass
    return info


class TelemetrySampler:
    """Background resource telemetry sampler with recursive process-tree RSS and breach termination."""

    def __init__(
        self,
        interval_sec: float = 0.5,
        min_disk_gb: float = DISK_MIN_RESERVE_GB,
        min_ram_gb: float = RAM_MIN_RESERVE_GB,
        max_samples: int = 10000,
        target_path: Optional[Path | str] = None,
        budget_inspector: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        self.interval_sec = max(0.05, float(interval_sec))
        self.min_disk_gb = max(DISK_MIN_RESERVE_GB, float(min_disk_gb))
        self.min_ram_gb = max(RAM_MIN_RESERVE_GB, float(min_ram_gb))
        self.max_samples = max(100, int(max_samples))
        self.target_path = Path(target_path) if target_path else ROOT_DIR
        self._budget_inspector = budget_inspector
        self.spawned_pids: Set[int] = set()

        self.samples: List[Dict[str, Any]] = []
        self.total_samples_recorded: int = 0
        self.dropped_samples_count: int = 0

        self.peak_rss_mb: float = 0.0
        self.peak_children_rss_mb: float = 0.0
        self.peak_child_count: int = 0
        self.peak_cpu_percent: float = 0.0
        self.min_disk_free_gb: float = 999999.0
        self.min_ram_available_gb: float = 999999.0
        self.min_free_inodes: Optional[int] = None

        self.breach_detected: bool = False
        self.breach_reason: Optional[str] = None
        self.breach_timestamp: Optional[float] = None
        self.terminated_on_breach: List[Dict[str, Any]] = []

        self._stop_event = threading.Event()
        self._breach_event = threading.Event()
        self._proc_lock = threading.Lock()
        self._active_procs: Dict[int, subprocess.Popen] = {}
        self._thread: Optional[threading.Thread] = None

    def register_process(self, proc: subprocess.Popen) -> None:
        with self._proc_lock:
            self._active_procs[proc.pid] = proc
            self.spawned_pids.add(proc.pid)

    def unregister_process(self, proc: subprocess.Popen) -> None:
        with self._proc_lock:
            self._active_procs.pop(proc.pid, None)

    def _terminate_registered_children(self) -> None:
        with self._proc_lock:
            procs = list(self._active_procs.values())
        for p in procs:
            res = terminate_process_group_safely(p, grace_sec=1.0)
            self.terminated_on_breach.append(res)

    def _sample_once(self) -> None:
        tree = sample_process_tree(os.getpid())
        # Also include any registered subprocess trees in case start_new_session detached parent linkage on some platforms
        with self._proc_lock:
            reg_pids = list(self._active_procs.keys())
        seen_pids = {os.getpid()} | {c["pid"] for c in tree.get("children", [])}
        extra_rss = 0.0
        extra_children = 0
        for rpid in reg_pids:
            if rpid not in seen_pids:
                sub_tree = sample_process_tree(rpid)
                extra_rss += sub_tree["tree_rss_mb"]
                extra_children += 1 + sub_tree["child_count"]

        total_tree_rss = round(tree["tree_rss_mb"] + extra_rss, 2)
        children_rss = round(tree["children_rss_mb"] + extra_rss, 2)
        child_count = tree["child_count"] + extra_children

        if self._budget_inspector is not None:
            b = self._budget_inspector()
            disk_gb = float(b.get("disk_free_gb", 0.0))
            ram_gb = float(b.get("ram_available_gb", 0.0))
            inodes = b.get("free_inodes")
        else:
            disk = shutil.disk_usage(self.target_path)
            disk_gb = round(disk.free / (1024**3), 3)
            vm = psutil.virtual_memory()
            ram_gb = round(vm.available / (1024**3), 3)
            inodes = _get_free_inodes(self.target_path)

        cpu_pct = round(psutil.cpu_percent(interval=None), 1)
        now = time.time()

        self.peak_rss_mb = max(self.peak_rss_mb, total_tree_rss)
        self.peak_children_rss_mb = max(self.peak_children_rss_mb, children_rss)
        self.peak_child_count = max(self.peak_child_count, child_count)
        self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_pct)
        self.min_disk_free_gb = min(self.min_disk_free_gb, disk_gb)
        self.min_ram_available_gb = min(self.min_ram_available_gb, ram_gb)
        if inodes is not None:
            self.min_free_inodes = inodes if self.min_free_inodes is None else min(self.min_free_inodes, inodes)

        sample = {
            "ts": round(now, 3),
            "iso": _utc_iso(now),
            "tree_rss_mb": total_tree_rss,
            "parent_rss_mb": tree["parent_rss_mb"],
            "children_rss_mb": children_rss,
            "child_count": child_count,
            "cpu_percent": cpu_pct,
            "disk_free_gb": disk_gb,
            "ram_available_gb": ram_gb,
            "free_inodes": inodes,
        }
        self.total_samples_recorded += 1
        if len(self.samples) >= self.max_samples:
            self.samples.pop(0)
            self.dropped_samples_count += 1
        self.samples.append(sample)

        if not self.breach_detected:
            breach_msgs = []
            if disk_gb < self.min_disk_gb:
                breach_msgs.append(f"Disk free {disk_gb:.2f} GiB < floor {self.min_disk_gb:.2f} GiB")
            if ram_gb < self.min_ram_gb:
                breach_msgs.append(f"Available RAM {ram_gb:.2f} GiB < floor {self.min_ram_gb:.2f} GiB")
            if breach_msgs:
                self.breach_detected = True
                self.breach_reason = "; ".join(breach_msgs)
                self.breach_timestamp = now
                self._breach_event.set()
                self._terminate_registered_children()

    def start(self) -> None:
        psutil.cpu_percent(interval=None)
        self._stop_event.clear()
        self._sample_once()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sample_once()
            except Exception:
                pass
            self._stop_event.wait(self.interval_sec)

    def stop(self) -> Dict[str, Any]:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            self._sample_once()
        except Exception:
            pass
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        return {
            "peak_rss_mb": round(self.peak_rss_mb, 2),
            "peak_children_rss_mb": round(self.peak_children_rss_mb, 2),
            "peak_child_count": self.peak_child_count,
            "peak_cpu_percent": round(self.peak_cpu_percent, 1),
            "min_disk_free_gb": round(self.min_disk_free_gb, 3) if self.min_disk_free_gb < 999990 else None,
            "min_ram_available_gb": round(self.min_ram_available_gb, 3) if self.min_ram_available_gb < 999990 else None,
            "min_free_inodes": self.min_free_inodes,
            "samples_count": len(self.samples),
            "total_samples_recorded": self.total_samples_recorded,
            "dropped_samples_count": self.dropped_samples_count,
            "max_samples_cap": self.max_samples,
            "breach_detected": self.breach_detected,
            "breach_reason": self.breach_reason,
            "breach_timestamp": self.breach_timestamp,
            "terminated_on_breach": self.terminated_on_breach,
            "samples": self.samples,
        }


def build_dependency_dag(jobs: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Build deterministic topological execution waves from job specifications.
    Rejects:
      - non-list input
      - missing or duplicate job 'id'
      - non-canonical 'command' key (must be 'cmd')
      - missing both 'cmd' and 'fn'
      - unknown dependencies
      - dependency cycles (including self-dependencies)
    """
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list of job dictionaries")
    if len(jobs) == 0:
        return []

    job_map: Dict[str, Dict[str, Any]] = {}
    deps_map: Dict[str, Set[str]] = {}

    for raw in jobs:
        if not isinstance(raw, dict):
            raise ValueError(f"Each job must be a dict, got {type(raw).__name__}")
        jid = str(raw.get("id") or "").strip()
        if not jid:
            raise ValueError("Job specification missing non-empty 'id'")
        if jid in job_map:
            raise ValueError(f"Duplicate job id in DAG: '{jid}'")
        if "command" in raw:
            raise ValueError(
                f"Job '{jid}' uses non-canonical key 'command'; canonical key 'cmd' is required"
            )
        has_cmd = raw.get("cmd") is not None
        has_fn = callable(raw.get("fn"))
        if not has_cmd and not has_fn:
            raise ValueError(f"Job '{jid}' must specify either 'cmd' or callable 'fn'")
        if has_cmd and not isinstance(raw.get("cmd"), list) or (has_cmd and len(raw.get("cmd")) == 0):
            raise ValueError(f"Job '{jid}' 'cmd' must be a non-empty list of strings")

        raw_deps = raw.get("deps")
        if raw_deps is None:
            raw_deps = raw.get("dependencies", [])
        if not isinstance(raw_deps, (list, tuple, set)):
            raise ValueError(f"Job '{jid}' deps must be a list")
        dep_list = sorted({str(d).strip() for d in raw_deps if str(d).strip()})
        if jid in dep_list:
            raise ValueError(f"Self-dependency cycle detected in job '{jid}'")

        norm_job = dict(raw)
        norm_job["id"] = jid
        norm_job["deps"] = dep_list
        norm_job["job_profile"] = normalize_job_profile(
            raw.get("job_profile") or raw.get("kind") or "light_cpu"
        )
        norm_job["timeout_sec"] = float(raw.get("timeout_sec", raw.get("timeout", 300.0)))
        norm_job["mandatory"] = bool(raw.get("mandatory", True))
        norm_job["expected_artifacts"] = [str(p) for p in (raw.get("expected_artifacts") or [])]

        job_map[jid] = norm_job
        deps_map[jid] = set(dep_list)

    # Validate unknown dependencies
    all_ids = set(job_map.keys())
    for jid, dset in deps_map.items():
        unknown = sorted(dset - all_ids)
        if unknown:
            raise ValueError(f"Job '{jid}' references unknown dependencies: {unknown}")

    remaining = set(all_ids)
    stages: List[List[Dict[str, Any]]] = []

    while remaining:
        ready = sorted(jid for jid in remaining if deps_map[jid].issubset(all_ids - remaining))
        if not ready:
            raise ValueError(f"Dependency cycle detected in DAG among jobs: {sorted(remaining)}")
        stages.append([job_map[jid] for jid in ready])
        remaining -= set(ready)

    return stages


def extract_dag_edges(stages: List[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    for stage in stages:
        for job in stage:
            jid = job["id"]
            for dep in job.get("deps", []):
                edges.append({"from": dep, "to": jid})
    return edges


def _verify_expected_artifacts(expected_artifacts: List[str]) -> Tuple[bool, List[str], List[str]]:
    verified: List[str] = []
    missing: List[str] = []
    for raw_p in expected_artifacts:
        p = Path(raw_p)
        if not p.is_absolute():
            p = ROOT_DIR / p
        if p.is_file() and p.stat().st_size > 0:
            verified.append(str(p))
        elif p.is_dir() and any(p.iterdir()):
            verified.append(str(p))
        else:
            missing.append(str(p))
    return len(missing) == 0, verified, missing


def _evaluate_callable_return(
    res: Any,
    validator: Optional[Callable[[Any], Any]] = None,
) -> Tuple[str, Optional[str]]:
    """Fail-closed evaluation of Python callable return payloads."""
    if validator is not None:
        v_out = validator(res)
        if isinstance(v_out, tuple) and len(v_out) == 2:
            ok, msg = bool(v_out[0]), str(v_out[1] or "")
            return ("PASS" if ok else "FAIL"), (None if ok else (msg or "Validator rejected result"))
        ok = bool(v_out)
        return ("PASS" if ok else "FAIL"), (None if ok else "Validator returned False")

    if res is None:
        return "NOT_VERIFIED", "Callable returned None without explicit validator"

    if not isinstance(res, dict):
        return "NOT_VERIFIED", f"Callable returned {type(res).__name__} instead of structured status dict"

    if "status" in res and isinstance(res["status"], str):
        st = res["status"].strip().upper()
        if st in KNOWN_PASS_STATUSES:
            return "PASS", None
        if st in KNOWN_BLOCKED_STATUSES:
            return st, res.get("error") or res.get("message") or f"Job blocked: {st}"
        if st in KNOWN_SPECIAL_STATUSES:
            return st, res.get("error") or res.get("message") or f"Job status: {st}"
        if st in KNOWN_FAIL_STATUSES:
            return "FAIL", res.get("error") or res.get("message") or f"Job reported failure status: {st}"
        return "NOT_VERIFIED", f"Unrecognized callable status '{res['status']}'"

    if "valid" in res and isinstance(res["valid"], bool):
        return ("PASS", None) if res["valid"] else ("FAIL", res.get("error") or "valid=False")

    if "passed" in res and isinstance(res["passed"], bool):
        return ("PASS", None) if res["passed"] else ("FAIL", res.get("error") or "passed=False")

    return "NOT_VERIFIED", "Callable dict missing mandatory 'status', 'valid', or 'passed' key"


def run_isolated_job(
    job: Dict[str, Any],
    default_timeout: float = 300.0,
    sampler: Optional[TelemetrySampler] = None,
) -> Dict[str, Any]:
    """
    Execute an isolated QA job with canonical 'cmd' or 'fn', strict timeout & child process-tree kill,
    artifact validation, and fail-closed result evaluation.
    """
    jid = str(job.get("id") or "unknown")
    started_ts = time.time()
    perf_t0 = time.perf_counter()
    timeout = float(job.get("timeout_sec", job.get("timeout", default_timeout)))
    expected_artifacts = [str(p) for p in (job.get("expected_artifacts") or [])]
    validator = job.get("validator")

    def _finish(
        status: str,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
        error: Optional[str] = None,
        result_payload: Any = None,
        peak_rss_mb: float = 0.0,
        disk_min_gb: Optional[float] = None,
        process_tree: Optional[Dict[str, Any]] = None,
        evidence_paths: Optional[List[str]] = None,
        timed_out: bool = False,
    ) -> Dict[str, Any]:
        ended_ts = time.time()
        elapsed = round(time.perf_counter() - perf_t0, 4)
        if disk_min_gb is None:
            try:
                disk_min_gb = round(shutil.disk_usage(ROOT_DIR).free / (1024**3), 3)
            except Exception:
                disk_min_gb = None
        return {
            "id": jid,
            "job_profile": normalize_job_profile(job.get("job_profile") or job.get("kind")),
            "mandatory": bool(job.get("mandatory", True)),
            "deps": list(job.get("deps", job.get("dependencies", []))),
            "status": status,
            "returncode": returncode,
            "timed_out": timed_out,
            "started_at": round(started_ts, 4),
            "started_iso": _utc_iso(started_ts),
            "ended_at": round(ended_ts, 4),
            "ended_iso": _utc_iso(ended_ts),
            "elapsed_sec": elapsed,
            "peak_rss_mb": round(peak_rss_mb, 2),
            "disk_min_gb": disk_min_gb,
            "process_tree": process_tree or {"child_count": 0, "children": []},
            "evidence_paths": evidence_paths if evidence_paths is not None else [],
            "cmd": job.get("cmd"),
            "stdout_tail": (stdout or "")[-2000:],
            "stderr_tail": (stderr or "")[-2000:],
            "result": result_payload,
            "error": error,
        }

    # Reject non-canonical 'command' key explicitly (B1 / C1)
    if "command" in job:
        return _finish(
            status="FAIL",
            returncode=-2,
            error="Rejected non-canonical key 'command'; canonical key 'cmd' is required",
        )

    if sampler is not None and sampler.breach_detected:
        return _finish(
            status="BLOCKED_RESOURCE",
            returncode=-3,
            error=f"Resource floor breached prior to job dispatch: {sampler.breach_reason}",
        )

    prof = normalize_job_profile(job.get("job_profile") or job.get("kind"))
    pre_launch_inspector = job.get("budget_inspector") or (sampler._budget_inspector if sampler is not None else None)
    if prof == "heavy_render" or pre_launch_inspector is not None:
        if callable(pre_launch_inspector):
            pre_b = pre_launch_inspector()
        else:
            pre_b = inspect_resource_budget(
                min_disk_gb=sampler.min_disk_gb if sampler is not None else DISK_MIN_RESERVE_GB,
                min_ram_gb=sampler.min_ram_gb if sampler is not None else RAM_MIN_RESERVE_GB,
                estimated_scratch_gb=float(job.get("estimated_scratch_gb", 0.5 if prof == "heavy_render" else 0.0)),
                extra_margin_gb=1.0 if prof == "heavy_render" else 0.0,
            )
        if not pre_b.get("healthy", False):
            return _finish(
                status="BLOCKED_RESOURCE",
                returncode=-3,
                disk_min_gb=pre_b.get("disk_free_gb"),
                error=f"Pre-launch resource guard blocked job '{jid}': {pre_b.get('message', 'resource floor breach')}",
            )

    # Path A: Python callable job
    if callable(job.get("fn")):
        fn = job["fn"]
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        fut = executor.submit(fn)
        try:
            res = fut.result(timeout=timeout)
            tree_snap = sample_process_tree(os.getpid())
            st, err = _evaluate_callable_return(res, validator=validator)
            verified_paths: List[str] = []
            if st == "PASS" and expected_artifacts:
                art_ok, verified_paths, missing_paths = _verify_expected_artifacts(expected_artifacts)
                if not art_ok:
                    st = "FAIL"
                    err = f"Missing or empty expected artifacts: {missing_paths}"
            elif expected_artifacts:
                _, verified_paths, _ = _verify_expected_artifacts(expected_artifacts)
            rc = 0 if st == "PASS" else 1
            return _finish(
                status=st,
                returncode=rc,
                error=err,
                result_payload=res,
                peak_rss_mb=tree_snap["tree_rss_mb"],
                process_tree=tree_snap,
                evidence_paths=verified_paths,
            )
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return _finish(
                status="FAIL",
                returncode=-1,
                error=f"Callable job '{jid}' timed out after {timeout}s",
                timed_out=True,
            )
        except Exception as exc:
            executor.shutdown(wait=False)
            return _finish(
                status="FAIL",
                returncode=1,
                stderr=str(exc),
                error=f"Callable raised {type(exc).__name__}: {exc}",
            )
        finally:
            executor.shutdown(wait=False)

    # Path B: Canonical subprocess command job
    cmd = job.get("cmd")
    if not isinstance(cmd, list) or len(cmd) == 0:
        return _finish(
            status="NOT_VERIFIED",
            returncode=-2,
            error=f"Job '{jid}' missing valid non-empty 'cmd' list or callable 'fn'",
        )

    cwd = Path(job.get("cwd") or ROOT_DIR)
    env = os.environ.copy()
    if isinstance(job.get("env"), dict):
        for k, v in job["env"].items():
            if v is None:
                env.pop(k, None)
            else:
                env[str(k)] = str(v)

    try:
        proc = subprocess.Popen(
            [str(x) for x in cmd],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except Exception as exc:
        return _finish(
            status="FAIL",
            returncode=-1,
            error=f"Failed to spawn subprocess for '{jid}': {exc}",
        )

    if sampler is not None:
        sampler.register_process(proc)

    comm_holder: Dict[str, Any] = {"stdout": "", "stderr": "", "exc": None}

    def _drain_pipes() -> None:
        try:
            out_s, err_s = proc.communicate()
            comm_holder["stdout"] = out_s or ""
            comm_holder["stderr"] = err_s or ""
        except Exception as exc:
            comm_holder["exc"] = exc

    drain_thread = threading.Thread(target=_drain_pipes, daemon=True)
    drain_thread.start()

    job_peak_rss = 0.0
    job_disk_min: Optional[float] = None
    last_tree: Dict[str, Any] = {"root_pid": proc.pid, "child_count": 0, "children": []}
    timed_out = False
    breached_mid_run = False

    try:
        while drain_thread.is_alive():
            sub_tree = sample_process_tree(proc.pid)
            if sub_tree["tree_rss_mb"] >= job_peak_rss:
                job_peak_rss = sub_tree["tree_rss_mb"]
                last_tree = sub_tree
            try:
                cur_disk = round(shutil.disk_usage(cwd).free / (1024**3), 3)
                job_disk_min = cur_disk if job_disk_min is None else min(job_disk_min, cur_disk)
            except Exception:
                pass

            if (time.perf_counter() - perf_t0) > timeout:
                timed_out = True
                terminate_process_group_safely(proc, grace_sec=0.4)
                break

            if sampler is not None and sampler.breach_detected:
                breached_mid_run = True
                terminate_process_group_safely(proc, grace_sec=0.5)
                break

            drain_thread.join(timeout=0.05)

        drain_thread.join(timeout=2.0)
    finally:
        if sampler is not None:
            sampler.unregister_process(proc)
        if proc.poll() is None:
            terminate_process_group_safely(proc, grace_sec=0.2)

    stdout_txt = comm_holder["stdout"]
    stderr_txt = comm_holder["stderr"]

    if timed_out:
        return _finish(
            status="FAIL",
            returncode=-1,
            stdout=stdout_txt,
            stderr=stderr_txt,
            error=f"Command timed out after {timeout}s; process group terminated",
            peak_rss_mb=job_peak_rss,
            disk_min_gb=job_disk_min,
            process_tree=last_tree,
            timed_out=True,
        )

    if breached_mid_run or (sampler is not None and sampler.breach_detected):
        return _finish(
            status="BLOCKED_RESOURCE",
            returncode=proc.returncode if proc.returncode is not None else -3,
            stdout=stdout_txt,
            stderr=stderr_txt,
            error=f"Terminated due to resource floor breach: {sampler.breach_reason if sampler else 'resource breach'}",
            peak_rss_mb=job_peak_rss,
            disk_min_gb=job_disk_min,
            process_tree=last_tree,
        )

    rc = proc.returncode if proc.returncode is not None else -1
    if rc != 0:
        return _finish(
            status="FAIL",
            returncode=rc,
            stdout=stdout_txt,
            stderr=stderr_txt,
            error=f"Command exited with non-zero code {rc}",
            peak_rss_mb=job_peak_rss,
            disk_min_gb=job_disk_min,
            process_tree=last_tree,
        )

    # Command exit 0 is NOT enough: check expected_artifacts + optional validator
    verified_paths = []
    if expected_artifacts:
        art_ok, verified_paths, missing_paths = _verify_expected_artifacts(expected_artifacts)
        if not art_ok:
            return _finish(
                status="FAIL",
                returncode=rc,
                stdout=stdout_txt,
                stderr=stderr_txt,
                error=f"Command exited 0 but missing/empty expected artifacts: {missing_paths}",
                peak_rss_mb=job_peak_rss,
                disk_min_gb=job_disk_min,
                process_tree=last_tree,
                evidence_paths=verified_paths,
            )

    parsed_json = None
    stripped_out = stdout_txt.strip()
    if stripped_out.startswith("{") and stripped_out.endswith("}"):
        try:
            parsed_json = json.loads(stripped_out)
        except Exception:
            parsed_json = None

    if callable(validator):
        v_input = {
            "returncode": rc,
            "stdout": stdout_txt,
            "stderr": stderr_txt,
            "json": parsed_json,
            "evidence_paths": verified_paths,
        }
        v_out = validator(v_input)
        if isinstance(v_out, tuple) and len(v_out) == 2:
            v_ok, v_msg = bool(v_out[0]), str(v_out[1] or "")
        else:
            v_ok, v_msg = bool(v_out), ""
        if not v_ok:
            return _finish(
                status="FAIL",
                returncode=rc,
                stdout=stdout_txt,
                stderr=stderr_txt,
                error=v_msg or "Post-command validator rejected output",
                result_payload=parsed_json,
                peak_rss_mb=job_peak_rss,
                disk_min_gb=job_disk_min,
                process_tree=last_tree,
                evidence_paths=verified_paths,
            )

    return _finish(
        status="PASS",
        returncode=0,
        stdout=stdout_txt,
        stderr=stderr_txt,
        result_payload=parsed_json,
        peak_rss_mb=job_peak_rss,
        disk_min_gb=job_disk_min,
        process_tree=last_tree,
        evidence_paths=verified_paths,
    )


def compute_concurrency_overlap(job_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute pairwise temporal overlap intervals across executed jobs to prove real concurrency."""
    executed = [
        r for r in job_results
        if isinstance(r.get("started_at"), (int, float))
        and isinstance(r.get("ended_at"), (int, float))
        and r.get("ended_at", 0) > r.get("started_at", 0)
        and r.get("status") not in ("BLOCKED_DEPENDENCY",)
    ]
    overlaps: List[Dict[str, Any]] = []
    for i in range(len(executed)):
        for j in range(i + 1, len(executed)):
            a, b = executed[i], executed[j]
            ov = min(float(a["ended_at"]), float(b["ended_at"])) - max(float(a["started_at"]), float(b["started_at"]))
            if ov > 0.005:
                overlaps.append({
                    "job_a": a["id"],
                    "job_b": b["id"],
                    "overlap_sec": round(ov, 4),
                })
    return {
        "overlapping_pairs_count": len(overlaps),
        "max_overlap_sec": max((o["overlap_sec"] for o in overlaps), default=0.0),
        "overlapping_pairs": overlaps[:30],
    }


def _is_safe_run_owned_scratch_dir(scratch_dir: Path) -> bool:
    resolved = scratch_dir.resolve()
    safe_roots = [
        (ROOT_DIR / ".test-runs").resolve(),
        (ROOT_DIR / "tests" / "evidence").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    for sr in safe_roots:
        try:
            resolved.relative_to(sr)
            if resolved != sr:
                return True
        except ValueError:
            continue
    return False


def run_dag(
    stages: List[List[Dict[str, Any]]],
    max_workers: int = 4,
    min_disk_gb: float = DISK_MIN_RESERVE_GB,
    min_ram_gb: float = RAM_MIN_RESERVE_GB,
    estimated_scratch_gb: float = 0.0,
    extra_margin_gb: float = 0.0,
    run_id: Optional[str] = None,
    budget_inspector: Optional[Callable[[], Dict[str, Any]]] = None,
    scratch_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Execute topological DAG waves with bounded concurrency, live resource telemetry,
    prerequisite failure propagation, and zero-job fail-closed protection.
    Enforces min_disk_gb >= 6.0 GiB and min_ram_gb >= 1.0 GiB.
    """
    min_disk_gb = max(DISK_MIN_RESERVE_GB, float(min_disk_gb))
    min_ram_gb = max(RAM_MIN_RESERVE_GB, float(min_ram_gb))
    dag_run_id = run_id or f"dag_{int(time.time())}_{os.getpid()}"
    dag_t0 = time.perf_counter()
    started_ts = time.time()

    all_stage_jobs = [j for st in (stages or []) for j in st]
    total_jobs = len(all_stage_jobs)
    edges = extract_dag_edges(stages or [])

    if total_jobs == 0:
        return {
            "run_id": dag_run_id,
            "status": "FAIL",
            "all_succeeded": False,
            "total_jobs": 0,
            "passed_jobs": 0,
            "failed_jobs": 0,
            "blocked_jobs": 0,
            "not_verified_jobs": 0,
            "max_active_workers": 0,
            "edges": [],
            "results": {},
            "jobs": [],
            "concurrency_proof": {"overlapping_pairs_count": 0, "max_overlap_sec": 0.0, "overlapping_pairs": []},
            "telemetry": {},
            "elapsed_sec": 0.0,
            "error": "Zero-job DAG cannot succeed (fail-closed)",
        }

    def _inspect_budget(scratch_gb: float = estimated_scratch_gb) -> Dict[str, Any]:
        if budget_inspector is not None:
            return budget_inspector()
        return inspect_resource_budget(
            min_disk_gb=min_disk_gb,
            min_ram_gb=min_ram_gb,
            estimated_scratch_gb=scratch_gb,
            extra_margin_gb=extra_margin_gb,
        )

    sampler = TelemetrySampler(
        interval_sec=0.2,
        min_disk_gb=min_disk_gb,
        min_ram_gb=min_ram_gb,
        budget_inspector=budget_inspector,
    )
    sampler.start()

    results: Dict[str, Dict[str, Any]] = {}
    ordered_jobs: List[Dict[str, Any]] = []
    active_lock = threading.Lock()
    active_workers = 0
    max_active_workers = 0
    historical_peak_rss_mb = 0.0

    try:
        for stage_idx, stage in enumerate(stages):
            if not stage:
                continue

            wave_scratch = max(
                float(estimated_scratch_gb),
                sum(float(j.get("estimated_scratch_gb", 0.1)) for j in stage),
            )
            budget = _inspect_budget(scratch_gb=wave_scratch)

            if not budget.get("healthy", False) or sampler.breach_detected:
                reason = sampler.breach_reason or budget.get("message", "Resource floor breach")
                now = time.time()
                for rem_stage in stages[stage_idx:]:
                    for j in rem_stage:
                        jid = j["id"]
                        if jid not in results:
                            rec = {
                                "id": jid,
                                "job_profile": normalize_job_profile(j.get("job_profile") or j.get("kind")),
                                "mandatory": bool(j.get("mandatory", True)),
                                "deps": list(j.get("deps", j.get("dependencies", []))),
                                "status": "BLOCKED_RESOURCE",
                                "returncode": -3,
                                "timed_out": False,
                                "started_at": round(now, 4),
                                "started_iso": _utc_iso(now),
                                "ended_at": round(now, 4),
                                "ended_iso": _utc_iso(now),
                                "elapsed_sec": 0.0,
                                "peak_rss_mb": 0.0,
                                "disk_min_gb": budget.get("disk_free_gb"),
                                "process_tree": {"child_count": 0, "children": []},
                                "evidence_paths": [],
                                "cmd": j.get("cmd"),
                                "stdout_tail": "",
                                "stderr_tail": "",
                                "result": None,
                                "error": reason,
                            }
                            results[jid] = rec
                            ordered_jobs.append(rec)
                break

            runnable: List[Dict[str, Any]] = []
            for j in stage:
                jid = j["id"]
                deps = j.get("deps", j.get("dependencies", []))
                unmet = [
                    f"{d}:{results.get(d, {}).get('status', 'MISSING')}"
                    for d in deps
                    if results.get(d, {}).get("status") != "PASS"
                ]
                if unmet:
                    now = time.time()
                    rec = {
                        "id": jid,
                        "job_profile": normalize_job_profile(j.get("job_profile") or j.get("kind")),
                        "mandatory": bool(j.get("mandatory", True)),
                        "deps": list(deps),
                        "status": "BLOCKED_DEPENDENCY",
                        "returncode": -4,
                        "timed_out": False,
                        "started_at": round(now, 4),
                        "started_iso": _utc_iso(now),
                        "ended_at": round(now, 4),
                        "ended_iso": _utc_iso(now),
                        "elapsed_sec": 0.0,
                        "peak_rss_mb": 0.0,
                        "disk_min_gb": budget.get("disk_free_gb"),
                        "process_tree": {"child_count": 0, "children": []},
                        "evidence_paths": [],
                        "cmd": j.get("cmd"),
                        "stdout_tail": "",
                        "stderr_tail": "",
                        "result": None,
                        "error": f"Blocked by prerequisite non-PASS dependencies: {unmet}",
                    }
                    results[jid] = rec
                    ordered_jobs.append(rec)
                else:
                    runnable.append(j)

            if not runnable:
                continue

            # Determine strictest profile in this runnable wave & per-profile semaphores
            profiles_present = {normalize_job_profile(j.get("job_profile") or j.get("kind")) for j in runnable}
            if "heavy_render" in profiles_present and len(profiles_present) == 1:
                dominant_profile = "heavy_render"
            elif "visual_decode" in profiles_present and "light_cpu" not in profiles_present:
                dominant_profile = "visual_decode"
            else:
                dominant_profile = "light_cpu"

            wave_workers = choose_bounded_parallelism(
                budget=budget,
                job_profile=dominant_profile,
                max_workers_cap=max_workers,
                historical_peak_rss_mb=historical_peak_rss_mb,
                estimated_scratch_gb=max(0.1, wave_scratch / max(1, len(runnable))),
            )
            wave_workers = max(1, min(wave_workers, len(runnable), max_workers))

            heavy_limit = choose_bounded_parallelism(
                budget=budget,
                job_profile="heavy_render",
                max_workers_cap=max_workers,
                historical_peak_rss_mb=historical_peak_rss_mb,
                estimated_scratch_gb=1.0,
            )
            heavy_sem = threading.Semaphore(max(1, heavy_limit))

            def _worker_entry(job_spec: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal active_workers, max_active_workers
                prof = normalize_job_profile(job_spec.get("job_profile") or job_spec.get("kind"))
                if prof == "heavy_render":
                    heavy_sem.acquire()
                try:
                    with active_lock:
                        active_workers += 1
                        if active_workers > max_active_workers:
                            max_active_workers = active_workers
                    try:
                        return run_isolated_job(job_spec, sampler=sampler)
                    finally:
                        with active_lock:
                            active_workers -= 1
                finally:
                    if prof == "heavy_render":
                        heavy_sem.release()

            stage_res_by_id: Dict[str, Dict[str, Any]] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=wave_workers) as pool:
                future_to_id = {pool.submit(_worker_entry, j): j["id"] for j in runnable}
                for fut in concurrent.futures.as_completed(future_to_id):
                    jid = future_to_id[fut]
                    res = fut.result()
                    stage_res_by_id[jid] = res
                    historical_peak_rss_mb = max(historical_peak_rss_mb, float(res.get("peak_rss_mb", 0.0)))

            for j in runnable:
                jid = j["id"]
                results[jid] = stage_res_by_id[jid]
                ordered_jobs.append(stage_res_by_id[jid])
    finally:
        telemetry_summary = sampler.stop()

    passed_jobs = sum(1 for r in ordered_jobs if r["status"] == "PASS")
    blocked_jobs = sum(1 for r in ordered_jobs if r["status"].startswith("BLOCKED"))
    not_verified_jobs = sum(1 for r in ordered_jobs if r["status"] in ("NOT_VERIFIED", "NOT_AVAILABLE"))
    failed_jobs = sum(
        1 for r in ordered_jobs
        if r["status"] not in ("PASS", "NOT_VERIFIED", "NOT_AVAILABLE") and not r["status"].startswith("BLOCKED")
    )

    mandatory_non_pass = [
        r["id"] for r in ordered_jobs if r.get("mandatory", True) and r["status"] != "PASS"
    ]
    resource_blocked = any(r["status"] == "BLOCKED_RESOURCE" for r in ordered_jobs) or telemetry_summary.get("breach_detected", False)

    if resource_blocked:
        dag_status = "BLOCKED_RESOURCE"
    elif mandatory_non_pass:
        dag_status = "FAIL"
    else:
        dag_status = "PASS"

    scratch_cleaned = False
    if resource_blocked and scratch_dir is not None:
        s_path = Path(scratch_dir)
        if s_path.exists() and _is_safe_run_owned_scratch_dir(s_path):
            shutil.rmtree(s_path, ignore_errors=True)
            scratch_cleaned = True

    orphan_pids: List[int] = []
    for spid in sorted(sampler.spawned_pids):
        try:
            proc_check = psutil.Process(spid)
            if proc_check.is_running() and proc_check.status() != psutil.STATUS_ZOMBIE:
                orphan_pids.append(spid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    concurrency_proof = compute_concurrency_overlap(ordered_jobs)
    elapsed_total = round(time.perf_counter() - dag_t0, 4)

    return {
        "run_id": dag_run_id,
        "started_at": round(started_ts, 4),
        "started_iso": _utc_iso(started_ts),
        "ended_at": round(time.time(), 4),
        "ended_iso": _utc_iso(),
        "elapsed_sec": elapsed_total,
        "status": dag_status,
        "all_succeeded": (dag_status == "PASS") and (total_jobs > 0),
        "total_jobs": total_jobs,
        "passed_jobs": passed_jobs,
        "failed_jobs": failed_jobs,
        "blocked_jobs": blocked_jobs,
        "not_verified_jobs": not_verified_jobs,
        "mandatory_non_pass_ids": mandatory_non_pass,
        "max_active_workers": max_active_workers,
        "orphan_worker_processes_after_run": len(orphan_pids),
        "orphan_worker_pids": orphan_pids,
        "scratch_cleaned_on_breach": scratch_cleaned,
        "min_disk_reserve_gb": min_disk_gb,
        "min_ram_reserve_gb": min_ram_gb,
        "edges": edges,
        "concurrency_proof": concurrency_proof,
        "results": results,
        "jobs": ordered_jobs,
        "telemetry": telemetry_summary,
    }


def publish_atomic_evidence(
    path: Path | str,
    payload: Any,
    run_id: Optional[str] = None,
    writer_job_id: Optional[str] = None,
    required_keys: Optional[List[str]] = None,
) -> Path:
    """
    Validate JSON schema/serializability and write atomically via unique temp file + fsync + os.replace.
    Prevents concurrent parallel jobs from clobbering the same target file.
    """
    p = Path(path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)

    if required_keys is not None:
        if not isinstance(payload, dict):
            raise ValueError(f"Evidence payload for {p.name} must be a dict when required_keys is set")
        missing = [k for k in required_keys if k not in payload]
        if missing:
            raise ValueError(f"Evidence payload for {p.name} missing required schema keys: {missing}")

    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    # Re-parse to guarantee strict JSON validity
    json.loads(serialized)

    with _INFLIGHT_EVIDENCE_LOCK:
        if p in _INFLIGHT_EVIDENCE_PATHS:
            raise RuntimeError(f"Concurrent parallel write collision detected on evidence file: {p}")
        if run_id and writer_job_id:
            claim_key = (run_id, p)
            prev_job = _RUN_EVIDENCE_CLAIMS.get(claim_key)
            if prev_job is not None and prev_job != writer_job_id:
                raise RuntimeError(
                    f"Duplicate target evidence path '{p}' claimed by both '{prev_job}' and '{writer_job_id}' in run '{run_id}'"
                )
            _RUN_EVIDENCE_CLAIMS[claim_key] = writer_job_id
        _INFLIGHT_EVIDENCE_PATHS.add(p)

    tmp_fd = -1
    tmp_name = ""
    try:
        prefix = f".{p.name}.{run_id or os.getpid()}.{threading.get_ident()}."
        tmp_fd, tmp_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=str(p.parent))
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            tmp_fd = -1
            f.write(serialized + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, p)
        tmp_name = ""
        return p
    finally:
        if tmp_fd >= 0:
            try:
                os.close(tmp_fd)
            except Exception:
                pass
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
        with _INFLIGHT_EVIDENCE_LOCK:
            _INFLIGHT_EVIDENCE_PATHS.discard(p)


if __name__ == "__main__":
    budget = inspect_resource_budget()
    print(json.dumps(budget, indent=2))
