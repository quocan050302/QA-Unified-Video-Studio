#!/usr/bin/env python3
"""guard_work_branch.py — Mandatory Branch Guard for QA-Unified-Video-Studio.

Asserts current git branch is strictly the expected working branch (default: fix/Image-Shot).
Provides runnable CLI and importable function for pre-execution guards.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_current_branch(cwd: Optional[Path] = None) -> str:
    """Get current git branch name."""
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to determine git branch: {exc}")


def assert_work_branch(
    expected: str = "fix/Image-Shot",
    actual_override: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Assert current branch strictly matches expected working branch.

    Raises SystemExit with BRANCH_GUARD_FAIL on mismatch.
    Supports actual_override for unit/negative testing without changing repository state.
    """
    actual = actual_override if actual_override is not None else get_current_branch(cwd)
    if actual != expected:
        sys.stderr.write(
            f"BRANCH_GUARD_FAIL: Branch '{actual}' does not match mandatory branch '{expected}'. "
            f"All writes, commits, and pushes are blocked.\n"
        )
        sys.exit(2)
    return actual


if __name__ == "__main__":
    expected_branch = sys.argv[1] if len(sys.argv) > 1 else "fix/Image-Shot"
    try:
        branch = assert_work_branch(expected=expected_branch)
        print(f"BRANCH_GUARD_OK: Currently on '{branch}' (expected '{expected_branch}')")
        sys.exit(0)
    except SystemExit as e:
        sys.exit(e.code)

