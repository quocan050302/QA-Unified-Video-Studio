#!/usr/bin/env python3
"""scripts/guard_work_branch.py — P0 Git Safety and Branch Integrity Guard for V14.2.

Asserts:
1. Working repository is quocan050302/QA-Unified-Video-Studio.
2. Current working branch is fix/Image-Shot (FAIL_CLOSED if any other branch).
3. Remote Production HEAD matches original pre-work baseline (80559d09d4b7bb72ee4c5acc6cc846e69abd65d1).
4. No commit or push is ever directed to Production.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MANDATORY_WORK_BRANCH = "fix/Image-Shot"
PRODUCTION_REMOTE_SHA_BASELINE = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"
FIX_IMAGE_SHOT_BASELINE = "f6a3926e87a886da42b8c8bc9861f883bbd184a1"


def run_git(args: list[str], timeout: int = 15) -> str:
    res = subprocess.run(
        ["git"] + args,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return res.stdout.strip()


def assert_work_branch(expected: str = MANDATORY_WORK_BRANCH, actual_override: Optional[str] = None) -> bool:
    cur = actual_override if actual_override is not None else run_git(["branch", "--show-current"])
    if cur != expected:
        print(f"❌ [BRANCH ASSERTION FAILED] Current branch '{cur}' != expected '{expected}'", file=sys.stderr)
        sys.exit(2)
    return True


def check_git_guard(phase: str = "preflight") -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    errors = []

    # 1. Check current branch
    try:
        current_branch = run_git(["branch", "--show-current"])
    except Exception as e:
        current_branch = "UNKNOWN"
        errors.append(f"Failed to detect git branch: {e}")

    if current_branch != MANDATORY_WORK_BRANCH:
        errors.append(
            f"BRANCH VIOLATION: Current branch is '{current_branch}', but mandatory branch is '{MANDATORY_WORK_BRANCH}'."
        )

    # 2. Check local HEAD
    try:
        local_head = run_git(["rev-parse", "HEAD"])
    except Exception as e:
        local_head = "UNKNOWN"
        errors.append(f"Failed to get local HEAD: {e}")

    # 3. Check remote Production SHA
    remote_prod_sha = "UNKNOWN"
    try:
        ls_prod = run_git(["ls-remote", "--heads", "origin", "Production"])
        if ls_prod:
            remote_prod_sha = ls_prod.split()[0]
    except Exception as e:
        errors.append(f"Failed to check remote Production SHA: {e}")

    if remote_prod_sha != PRODUCTION_REMOTE_SHA_BASELINE:
        # Note: if Production was modified upstream, we must report but NOT mutate
        errors.append(
            f"PRODUCTION INTEGRITY WARNING: Remote Production SHA is '{remote_prod_sha}', baseline was '{PRODUCTION_REMOTE_SHA_BASELINE}'."
        )

    # 4. Check remote fix/Image-Shot SHA
    remote_fix_sha = "UNKNOWN"
    try:
        ls_fix = run_git(["ls-remote", "--heads", "origin", MANDATORY_WORK_BRANCH])
        if ls_fix:
            remote_fix_sha = ls_fix.split()[0]
    except Exception as e:
        errors.append(f"Failed to check remote fix/Image-Shot SHA: {e}")

    if phase == "postpush":
        if remote_fix_sha != local_head:
            errors.append(f"POSTPUSH VERIFICATION FAILED: Remote fix/Image-Shot ({remote_fix_sha}) != local HEAD ({local_head})")

    # 5. Check working tree dirty status and sensitive files
    dirty_files = []
    sensitive_patterns = [".mp4", ".key", ".pem", ".env", "temp_frames", "build/"]
    try:
        status_lines = run_git(["status", "--porcelain=v1"]).splitlines()
        for line in status_lines:
            s_line = line.strip()
            if not s_line:
                continue
            dirty_files.append(s_line)
            # Check for sensitive staged files
            for pat in sensitive_patterns:
                if pat in s_line and s_line.startswith(("A", "M")):
                    errors.append(f"SECURITY VIOLATION: Attempting to commit sensitive/temporary pattern '{pat}' in '{s_line}'")
    except Exception as e:
        errors.append(f"Failed to check git status: {e}")

    is_valid = len(errors) == 0
    attestation = {
        "guard_version": "v14.3",
        "phase": phase,
        "timestamp": timestamp,
        "is_valid": is_valid,
        "current_branch": current_branch,
        "mandatory_branch": MANDATORY_WORK_BRANCH,
        "local_head": local_head,
        "remote_fix_sha": remote_fix_sha,
        "remote_prod_sha": remote_prod_sha,
        "production_baseline": PRODUCTION_REMOTE_SHA_BASELINE,
        "dirty_files_count": len(dirty_files),
        "dirty_files": dirty_files[:20],
        "errors": errors,
    }

    if not is_valid:
        print(f"❌ [GIT GUARD FAILED] Phase: {phase}")
        for err in errors:
            print(f"   - {err}")
    else:
        print(f"✅ [GIT GUARD OK] Phase: {phase} | Branch: {current_branch} | HEAD: {local_head[:10]}")

    return attestation


if __name__ == "__main__":
    phase_arg = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    att = check_git_guard(phase_arg)
    if not att["is_valid"]:
        sys.exit(1)
    sys.exit(0)
