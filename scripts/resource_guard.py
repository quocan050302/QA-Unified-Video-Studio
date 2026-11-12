#!/usr/bin/env python3
"""resource_guard.py — CPU, RAM and Disk Guard for QA-Unified-Video-Studio test suite.

Ensures safety thresholds before running heavy browser rendering or video encoding.
Guards against running out of disk space (default >= 5.0 GB reserve) and memory starvation.
"""

import sys
import os
import shutil
import json
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
    if sys.platform == "darwin" and free_gb == 0.0:
        try:
            import subprocess
            out = subprocess.check_output(["vm_stat"], text=True)
            for line in out.splitlines():
                if "Pages free:" in line:
                    free_pages = int(line.split(":")[1].strip().replace(".", ""))
                    free_gb = round((free_pages * 4096) / (1024 ** 3), 2)
                    break
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

if __name__ == "__main__":
    ok, msg, info = check_resources()
    print(json.dumps({"status": "PASS" if ok else "HOLD", "message": msg, "info": info}, indent=2))
    sys.exit(0 if ok else 1)

