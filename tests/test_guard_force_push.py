"""`.claude/hooks/guard_force_push.py` — the PreToolUse hook that blocks force-push to master.

Drives the real hook as Claude Code does: hook JSON on stdin, deny JSON on stdout.
Failure named first (2026-11-07 koda pārskats): `git -C <path> push --force origin master`
slipped through because the hook only matched segments starting with `git push`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "guard_force_push.py"


def _denied(cmd: str) -> bool:
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    return bool(out) and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_force_push_to_master_is_denied_also_with_git_global_options():
    for cmd in (
        "git push --force origin master",
        'git -C "E:/atmina" push --force origin master',
        "git -C /e/atmina push -f origin master",
        "git -c http.curloptResolve=github.com:443:1.2.3.4 push --force origin master",
        "git --no-pager -C . push origin +master",
    ):
        assert _denied(cmd), f"not denied: {cmd}"


def test_safe_pushes_are_allowed():
    for cmd in (
        'git -C "E:/atmina" push origin master',
        "git -C . push --force-with-lease origin feature-x",
        "git -C . push --force origin feature-x",
        'echo "git -C . push -f origin master"',
    ):
        assert not _denied(cmd), f"denied: {cmd}"
