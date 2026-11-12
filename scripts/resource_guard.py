#!/usr/bin/env python3
"""resource_guard.py — CPU, RAM and Disk Guard for QA-Unified-Video-Studio test suite.

Ensures safety thresholds before running heavy browser rendering or video encoding.
Guards against running out of disk space (default >= 5.0 GB reserve) and memory starvation.
"""

import sys
import os
import shutil
import json
import threading
import time
import signal
import subprocess
from pathlib import Path

DEFAULT_MIN_DISK_GB = 4.0  # Safe reserve for tests
DEFAULT_MIN_RAM_GB = 0.8   # Available RAM reserve

def get_disk_info(path: str = ".") -> dict:
    total, used, free = shutil.disk_usage(path)
    return {
        "total_gb": round(total / (1024 ** 3), 2),
        "used_gb": round(used / (1024 ** 3), 2),
        "free_gb": round(free / (1024 ** 3), 2),
    }

def get_ram_info() -> dict:
    total_gb = 0.0
    free_gb = 0.0
    try:
        # Standard POSIX sysconf
        if hasattr(os, "sysconf"):
            pagesize = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            total_gb = round((phys_pages * pagesize) / (1024 ** 3), 2)
            if hasattr(os, "sysconf_names") and "SC_AVPHYS_PAGES" in os.sysconf_names:
                avail_pages = os.sysconf("SC_AVPHYS_PAGES")
                free_gb = round((avail_pages * pagesize) / (1024 ** 3), 2)
            else:
                free_gb = total_gb * 0.25  # conservative estimate
    except Exception:
        pass

    # Platform specific checks
    if sys.platform == "darwin":
        try:
            import subprocess, re
            out = subprocess.check_output(["vm_stat"], text=True)
            page_size = 4096
            m_ps = re.search(r"page size of (\d+) bytes", out)
            if m_ps:
                page_size = int(m_ps.group(1))
            pages = {}
            for line in out.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    v_str = v.strip().replace(".", "")
                    if v_str.isdigit():
                        pages[k.strip()] = int(v_str)
            free_p = pages.get("Pages free", 0) + pages.get("Pages inactive", 0) + pages.get("Pages speculative", 0)
            if free_p > 0:
                free_gb = round((free_p * page_size) / (1024 ** 3), 2)
        except Exception:
            pass

    return {
        "total_gb": total_gb,
        "available_gb": free_gb if free_gb > 0 else 2.0,
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
    subdirs = sorted([d for d in p.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
    if len(subdirs) > max_age_dirs:
        for old in subdirs[max_age_dirs:]:
            try:
                shutil.rmtree(old)
            except Exception as e:
                print(f"[ResourceGuard] Warning: could not delete {old}: {e}", file=sys.stderr)

def get_process_children(parent_pid: int) -> list[int]:
    """Return list of child PIDs for given parent PID."""
    children = []
    try:
        if sys.platform == "darwin" or sys.platform.startswith("linux"):
            res = subprocess.run(["pgrep", "-P", str(parent_pid)], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    p = line.strip()
                    if p.isdigit():
                        children.append(int(p))
    except Exception:
        pass
    return children

def kill_process_tree(pid: int, sig=signal.SIGTERM, timeout: float = 3.0):
    """Safely terminate a process and all its children."""
    if pid <= 0:
        return
    try:
        children = get_process_children(pid)
        for c in children:
            kill_process_tree(c, sig=sig, timeout=timeout)
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                return
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except Exception:
        pass

class ResourceMonitor:
    """Continuous background resource monitor for CPU, RAM, and Disk."""
    def __init__(self, workspace: str = ".", min_disk_gb: float = DEFAULT_MIN_DISK_GB, interval_sec: float = 1.0):
        self.workspace = workspace
        self.min_disk_gb = min_disk_gb
        self.interval_sec = interval_sec
        self.stop_event = threading.Event()
        self.thread = None
        self.min_free_disk_gb = float("inf")
        self.min_avail_ram_gb = float("inf")
        self.samples = 0
        self.breached = False
        self.breach_message = ""

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            try:
                disk = get_disk_info(self.workspace)
                ram = get_ram_info()
                self.samples += 1
                free_disk = disk["free_gb"]
                avail_ram = ram["available_gb"]
                if free_disk < self.min_free_disk_gb:
                    self.min_free_disk_gb = free_disk
                if avail_ram < self.min_avail_ram_gb:
                    self.min_avail_ram_gb = avail_ram

                if free_disk < self.min_disk_gb:
                    self.breached = True
                    self.breach_message = f"Disk dropped to {free_disk} GB (< {self.min_disk_gb} GB threshold)"
            except Exception:
                pass
            self.stop_event.wait(self.interval_sec)

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=2.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def get_stats(self) -> dict:
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

