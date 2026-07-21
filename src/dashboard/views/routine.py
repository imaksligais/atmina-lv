"""Routine panel view helper — thin wrapper over `check_routine()`.

The wrapper augments each step with LV-language `label` + status `icon`
so the partial template stays declarative. Morning-window awareness
itself lives in `src.routine.check_routine` (single source of truth);
this module only wires display-side concerns.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.db import now_lv_dt, today_lv
from src.routine import check_routine

_STATUS_ICONS = {
    "done": "✓",
    "partial": "◐",
    "missing": "✗",
    "stale": "◐",
    "waiting": "⏳",
}

_STEP_LABELS = {
    "ingest": "Ielāde",
    "analysis": "Pozīciju analīze",
    "contradictions": "Pretrunu pārbaude",
    "devils_advocate": "Devils-advocate",
    "tensions": "Spriedzes",
    "tendences": "Konteksta piezīmes",
    "daily_brief": "Dienas pārskats",
    "featured_image": "Featured image",
    "wiki_sync": "Wiki sync",
    "generate": "Statiskā vietne",
}


def _default_now() -> datetime:
    """Module-level seam so tests can monkeypatch the wall clock."""
    return now_lv_dt()


def get_routine_context(
    date: str | None = None,
    db_path: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return routine status augmented with display metadata.

    Args:
        date: ISO date. Defaults to today's LV date.
        db_path: Optional override for tests.
        now: Optional LV-time datetime override for morning-window logic.

    Returns:
        dict with keys: date, all_complete, steps. Each step has the
        original status/details plus `label` (LV) and `icon` (glyph).
    """
    if date is None:
        date = today_lv().isoformat()
    if now is None:
        now = _default_now()

    result = check_routine(date, db_path=db_path, now=now)

    for key, step in result["steps"].items():
        step["label"] = _STEP_LABELS.get(key, key)
        step["icon"] = _STATUS_ICONS.get(step["status"], "?")

    return result
