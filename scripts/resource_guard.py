#!/usr/bin/env python3
"""resource_guard.py — CPU, RAM, Disk Guard and Real-Time Telemetry Monitor.
QA-Unified-Video-Studio V14.2 (Backward compatible with V10-V14.1).

Features:
- Telemetry: CPU %, RAM %, RAM available (MB/GB), Disk free space (GB), Process tree tracking.
- Pre-flight checks: check_resources, clean_old_runs, get_disk_info, get_ram_info.
- Process safety: kill_process_tree, fail-safe termination on resource breach.
- Continuous background sampler (<= 1.0s interval) with get_summary() and get_stats().
"""

from __future__ import annotations

import json
import os
import psutil
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

DEFAULT_MIN_DISK_GB = 6.0  # Conservative safe reserve (V14.3 production)
DEFAULT_MIN_RAM_GB = 1.0   # Available RAM reserve (1.0 GB)


def get_disk_info(path: str = ".") -> dict:
    total, used, free = shutil.disk_usage(path)
    return {
        "total_gb": round(total / (1024 ** 3), 2),
        "used_gb": round(used / (1024 ** 3), 2),
        "free_gb": round(free / (1024 ** 3), 2),
    }


def get_ram_info() -> dict:
    try:
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "available_gb": round(vm.available / (1024 ** 3), 2),
            "ram_percent": vm.percent,
            "ram_avail_mb": round(vm.available / (1024 ** 2), 1),
        }
    except Exception:
        du = shutil.disk_usage(".")
        return {
            "total_gb": 8.0,
            "available_gb": 2.0,
            "ram_percent": 50.0,
            "ram_avail_mb": 2048.0,
        }


def check_resources(workspace: str = ".", min_disk_gb: float = DEFAULT_MIN_DISK_GB, min_ram_gb: float = DEFAULT_MIN_RAM_GB) -> tuple[bool, str, dict]:
    disk = get_disk_info(workspace)
    ram = get_ram_info()
    cpus = os.cpu_count() or 2

    info = {
        "disk": disk,
        "ram": ram,
        "cpus": cpus,
        "workspace": str(Path(workspace).resolve()),
    }

    if disk["free_gb"] < min_disk_gb:
        msg = f"DISK SPACE LOW: {disk['free_gb']} GB free is below safety reserve {min_disk_gb} GB"
        return False, msg, info

    if ram["available_gb"] > 0 and ram["available_gb"] < min_ram_gb:
        msg = f"RAM LOW: {ram['available_gb']} GB available is below safety reserve {min_ram_gb} GB"
        return False, msg, info

    return True, "OK", info


def clean_old_runs(test_runs_dir: str = ".test-runs", max_age_dirs: int = 1):
    p = Path(test_runs_dir)
    if not p.exists():
        return
    subdirs = sorted([d for d in p.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)
    for d in subdirs[max_age_dirs:]:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


def get_process_children(parent_pid: int) -> list[int]:
    children = []
    try:
        proc = psutil.Process(parent_pid)
        for c in proc.children(recursive=True):
            children.append(c.pid)
    except Exception:
        pass
    return children


def kill_process_tree(pid: int, sig=signal.SIGTERM, timeout: float = 3.0):
    """Safely terminate a process and all its children across platforms."""
    if pid <= 0:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=timeout)
        except Exception:
            pass
        return

    try:
        proc = psutil.Process(pid)
        children = proc.children(recursive=True)
        for c in children:
            try:
                c.terminate()
            except Exception:
                pass
        proc.terminate()
        _, alive = psutil.wait_procs(children + [proc], timeout=timeout)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
    except Exception:
        pass


class ResourceExhaustionError(RuntimeError):
    pass


class ResourceMonitor:
    """Continuous background resource monitor (V14.2 + V10/V12 compatible)."""
    def __init__(
        self,
        workspace: str = ".",
        target_path: Optional[Path] = None,
        min_disk_gb: float = DEFAULT_MIN_DISK_GB,
        min_disk_free_gb: Optional[float] = None,
        min_ram_gb: float = DEFAULT_MIN_RAM_GB,
        min_ram_avail_mb: float = 300.0,
        max_ram_percent: float = 95.0,
        interval_sec: float = 0.5,
        sample_interval_sec: Optional[float] = None,
        enforce_limits: bool = True,
    ):
        target = target_path or Path(workspace)
        self.target_path = Path(target).resolve()
        self.workspace = str(self.target_path)
        
        # Unify arguments
        self.sample_interval_sec = min(1.0, max(0.1, sample_interval_sec or interval_sec))
        self.interval_sec = self.sample_interval_sec
        self.min_disk_free_gb = min_disk_free_gb if min_disk_free_gb is not None else min_disk_gb
        self.min_disk_gb = self.min_disk_free_gb
        self.max_ram_percent = max_ram_percent
        self.min_ram_avail_mb = min_ram_avail_mb
        self.min_ram_gb = min_ram_gb
        self.enforce_limits = enforce_limits

        self.stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Telemetry stats
        self.samples = 0
        self.samples_count = 0
        self.violations_count = 0
        self.peak_cpu_percent = 0.0
        self.peak_ram_percent = 0.0
        self.min_disk_free_gb_observed = 999999.0
        self.min_free_disk_gb = float("inf")
        self.min_avail_ram_gb = float("inf")
        self.breached = False
        self.breach_message = ""
        self.breach_reason = None
        self.tracked_pids: Set[int] = {os.getpid()}
        self._registered_pids = self.tracked_pids
        self.last_telemetry: Dict[str, Any] = {}

    def register_pid(self, pid: int):
        if pid and pid > 0:
            with self._lock:
                self.tracked_pids.add(pid)

    def unregister_pid(self, pid: int):
        with self._lock:
            self.tracked_pids.discard(pid)

    def _sample(self) -> Dict[str, Any]:
        du = shutil.disk_usage(self.target_path)
        disk_free_gb = round(du.free / (1024**3), 3)
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)

        telem = {
            "timestamp": time.time(),
            "cpu_percent": cpu_pct,
            "ram_percent": vm.percent,
            "ram_avail_mb": round(vm.available / (1024**2), 1),
            "disk_free_gb": disk_free_gb,
            "tracked_pids_count": len(self.tracked_pids),
        }

        with self._lock:
            self.samples += 1
            self.samples_count = self.samples
            self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_pct)
            self.peak_ram_percent = max(self.peak_ram_percent, vm.percent)
            self.min_disk_free_gb_observed = min(self.min_disk_free_gb_observed, disk_free_gb)
            self.min_free_disk_gb = self.min_disk_free_gb_observed
            avail_ram_gb = round(vm.available / (1024**3), 2)
            self.min_avail_ram_gb = min(self.min_avail_ram_gb, avail_ram_gb)
            self.last_telemetry = telem

            breach = None
            if disk_free_gb < self.min_disk_free_gb:
                breach = f"Disk free space ({disk_free_gb:.2f} GiB) breached minimum safety floor ({self.min_disk_free_gb:.2f} GiB)"
            elif vm.percent > self.max_ram_percent:
                breach = f"RAM usage ({vm.percent:.1f}%) breached maximum safety threshold ({self.max_ram_percent:.1f}%)"
            elif (vm.available / (1024**2)) < self.min_ram_avail_mb:
                breach = f"Available RAM ({telem['ram_avail_mb']:.1f} MB) breached minimum safety floor ({self.min_ram_avail_mb:.1f} MB)"

            if breach:
                self.violations_count += 1
                self.breached = True
                self.breach_reason = breach
                self.breach_message = breach
                if self.enforce_limits:
                    self._terminate_registered()

        return telem

    def _terminate_registered(self):
        with self._lock:
            pids = list(self.tracked_pids)
        my_pid = os.getpid()
        for p in pids:
            if p != my_pid:
                kill_process_tree(p, timeout=2.0)

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            try:
                self._sample()
            except Exception:
                pass
            time.sleep(self.sample_interval_sec)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ResourceGuardThread")
        self._thread.start()
        return self

    def stop(self) -> Dict[str, Any]:
        self.stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return self.get_summary()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "samples_count": self.samples_count,
                "violations_count": self.violations_count,
                "sample_interval_sec": self.sample_interval_sec,
                "peak_cpu_percent": self.peak_cpu_percent,
                "peak_ram_percent": self.peak_ram_percent,
                "min_disk_free_gb_observed": (
                    self.min_disk_free_gb_observed if self.min_disk_free_gb_observed != 999999.0 else 0.0
                ),
                "last_telemetry": self.last_telemetry,
                "breach_reason": self.breach_reason,
                "healthy": (self.violations_count == 0),
            }

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "samples": self.samples,
                "min_free_disk_gb": round(self.min_free_disk_gb, 2) if self.min_free_disk_gb != float("inf") else None,
                "min_avail_ram_gb": round(self.min_avail_ram_gb, 2) if self.min_avail_ram_gb != float("inf") else None,
                "breached": self.breached,
                "breach_message": self.breach_message,
            }


if __name__ == "__main__":
    ok, msg, info = check_resources()
    print(json.dumps({"status": "PASS" if ok else "HOLD", "message": msg, "info": info}, indent=2))
    sys.exit(0 if ok else 1)
