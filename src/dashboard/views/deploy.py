"""Deploy trigger view — wraps `scripts/deploy.sh` behind a confirm modal.

Two endpoints are wired by the route layer:
  - `GET /api/deploy/confirm` → modal HTML with last-deploy timestamp
  - `POST /api/deploy`        → runs `bash scripts/deploy.sh`, logs result

Subprocess timeout is 300 s — historically deploys take 30-60 s; longer
implies network trouble or a runaway. The route surfaces success / failure
/ timeout via the toast system; ``log_action('deploy', ...)`` persists the
outcome for the activity timeline + last-deploy lookup.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any

from src.db import get_db


# Path to repo root — `scripts/deploy.sh` lives there. We resolve it once
# at import time so the worker process doesn't fight cwd later.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

DEPLOY_TIMEOUT_SECONDS = 300


def get_last_deploy(db_path: str | None = None) -> dict[str, Any] | None:
    """Return the most recent deploy log row, or None if there's no history."""
    db = get_db(db_path) if db_path else get_db()
    try:
        row = db.execute(
            "SELECT id, timestamp, status, details "
            "FROM logs WHERE action='deploy' "
            "ORDER BY timestamp DESC, id DESC LIMIT 1"
        ).fetchone()
    finally:
        db.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "status": row["status"],
        "details": row["details"],
    }


def run_deploy_script(timeout: int = DEPLOY_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Execute ``bash scripts/deploy.sh`` and capture the outcome.

    Returns a dict so the route layer can format toasts + log entries
    uniformly. Never raises — subprocess failures and timeouts map to
    ``exit_code != 0`` and ``timed_out == True`` respectively.
    """
    try:
        result = subprocess.run(
            ["bash", "scripts/deploy.sh"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_REPO_ROOT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": -1,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace"),
            "stderr": exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace"),
            "timed_out": True,
        }
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "timed_out": False,
    }
