"""A/B strategy panel view helper.

Surfaces three things:
1. Which X_MENTIONS_STRATEGY the running operator shell selected
   ("search" vs "timeline" — see `src.x_mentions._resolve_strategy`).
2. Last 7 ``mentions_fetch`` runs as a small SVG bar chart of stored counts.
3. Count of guardrail trips (`mentions_fetch_guardrail`) in the last 24 h,
   so degraded slot pools surface here before they become silent.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.db import get_db

_DEFAULT_STRATEGY = "timeline"


def _parse_details(blob: str | None) -> dict[str, Any]:
    if not blob:
        return {}
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return {}


def get_strategy_context(db_path: str | None = None) -> dict[str, Any]:
    """Return strategy panel context.

    Reads X_MENTIONS_STRATEGY from the process environment — `serve.py` is
    expected to be launched from a shell that inherits the user-scope env
    var (`setx` on Windows or shell rc on POSIX). The runbook documents
    this.
    """
    strategy = os.environ.get("X_MENTIONS_STRATEGY", _DEFAULT_STRATEGY).lower()

    db = get_db(db_path) if db_path else get_db()
    try:
        run_rows = db.execute(
            "SELECT id, timestamp, status, details "
            "FROM logs WHERE action='mentions_fetch' "
            "ORDER BY id DESC LIMIT 7"
        ).fetchall()
        trip_row = db.execute(
            "SELECT COUNT(*) AS cnt FROM logs "
            "WHERE action='mentions_fetch_guardrail' "
            "  AND timestamp >= datetime('now', '-24 hours')"
        ).fetchone()
    finally:
        db.close()

    runs = []
    for r in run_rows:
        details = _parse_details(r["details"])
        runs.append(
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "status": r["status"],
                "stored": details.get("stored", 0),
                "fetched": details.get("fetched", 0),
                "errors": details.get("errors", 0),
            }
        )

    # Chart payload — newest first in the DB, but the visual reads left→right
    # as oldest→newest, so reverse for the macro.
    chart_data = [
        {"label": str(r["id"]), "value": r["stored"]}
        for r in reversed(runs)
    ]

    return {
        "strategy": strategy,
        "runs": runs,
        "chart_data": chart_data,
        "guardrail_trips_24h": int(trip_row["cnt"]) if trip_row else 0,
    }
