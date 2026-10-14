"""Pending-action banner + footer telemetry view.

Computes a single list of operator-attention items and a small bundle of
footer metadata (image-budget bar, build SHA). The dashboard `/` route
composes this alongside the panel contexts and threads `pending.count`
into the browser title.

Item shape:
    {level: 'warning'|'info', message: str, action_link: str|None}
"""
from __future__ import annotations

import os
import subprocess
from datetime import date, datetime
from typing import Any

from src.db import get_db, now_lv_dt, today_lv

# Cost-budget ceiling for the calendar month. Today's prompt cost is
# $0.039/image (gemini-3.1-flash-image-preview); the project's monthly cap is
# a soft target that the footer surfaces so operator notices runaway spend.
IMAGE_BUDGET_USD_PER_MONTH = 5.00

_MORNING_WINDOW_HOUR = 15


def _sum_image_cost_current_month(db, target_date: date) -> float:
    month_prefix = target_date.strftime("%Y-%m")
    row = db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM brief_images "
        "WHERE substr(generated_at, 1, 7) = ?",
        (month_prefix,),
    ).fetchone()
    return float(row["total"] or 0.0)


def get_build_sha() -> str:
    """Return short git SHA of the current checkout, or 'unknown' if unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or "unknown"
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return "unknown"


def get_pending_actions(
    date: str | None = None,
    db_path: str | None = None,
    now: datetime | None = None,
    slots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build pending-actions + footer metadata for the dashboard.

    Args:
        date: ISO date. Defaults to today's LV date.
        db_path: Optional override for tests.
        now: Wall-clock override; defaults to ``now_lv_dt()``.
        slots: Optional slot snapshot — passed in by the route after it
            already called `get_slot_snapshot()`. Avoids triggering a second
            probe just to count guardrail status here.

    Returns:
        dict with keys: actions, count, image_budget, build_sha, scheduled.
    """
    if date is None:
        date = today_lv().isoformat()
    if now is None:
        now = now_lv_dt()
    target_date = datetime.strptime(date, "%Y-%m-%d").date()

    db = get_db(db_path) if db_path else get_db()
    try:
        pending_images = db.execute(
            "SELECT COUNT(*) AS cnt FROM brief_images bi "
            "JOIN context_notes cn ON cn.id = bi.note_id "
            "WHERE bi.approved = 0 "
            "  AND cn.note_type = 'daily_brief' "
            "  AND substr(cn.topic, -10) = ?",
            (date,),
        ).fetchone()["cnt"]

        brief_today = db.execute(
            "SELECT COUNT(*) AS cnt FROM context_notes "
            "WHERE note_type = 'daily_brief' "
            "  AND substr(topic, -10) = ?",
            (date,),
        ).fetchone()["cnt"]

        image_cost = _sum_image_cost_current_month(db, target_date)
    finally:
        db.close()

    actions: list[dict[str, Any]] = []

    if pending_images > 0:
        actions.append({
            "level": "warning",
            "message": f"{pending_images} image gaida apstiprinājumu",
            "action_link": "#brief-panel",
        })

    if brief_today == 0 and now.hour >= _MORNING_WINDOW_HOUR:
        actions.append({
            "level": "warning",
            "message": f"Brief vēl nav uzrakstīts ({now.hour:02d}:{now.minute:02d} jau)",
            "action_link": "#backlog-panel",
        })

    if slots and slots.get("guardrail_tripped"):
        h = slots["healthy_search_count"]
        t = slots["total_slots"]
        actions.append({
            "level": "warning",
            "message": (
                f"slot health: {h}/{t} healthy on search_tweet "
                "— guardrail falling back to timeline"
            ),
            "action_link": "#slot-panel",
        })

    # Soft "next scheduled" hints — deferred from Task 1.3's routine panel.
    scheduled: list[dict[str, Any]] = []
    if now.hour < _MORNING_WINDOW_HOUR:
        scheduled.append({"time_label": "pēc 15:00", "message": "claim extraction"})
        scheduled.append({"time_label": "pēc 17:00", "message": "dienas pārskats"})
    if brief_today and pending_images == 0:
        scheduled.append({"time_label": "vakarā", "message": "social drafts (@atmina_lv)"})
        scheduled.append({"time_label": "vakarā", "message": "Telegram brief"})

    return {
        "actions": actions,
        "count": len(actions),
        "scheduled": scheduled,
        "image_budget": {
            "used_usd": image_cost,
            "max_usd": IMAGE_BUDGET_USD_PER_MONTH,
            "percent": int(min(100, image_cost / IMAGE_BUDGET_USD_PER_MONTH * 100))
                       if IMAGE_BUDGET_USD_PER_MONTH > 0 else 0,
        },
        "build_sha": get_build_sha(),
    }
