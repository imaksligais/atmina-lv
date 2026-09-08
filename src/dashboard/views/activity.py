"""Activity timeline view — the dashboard's memory layer.

UNIONs four source tables into one chronological feed:
  - ``logs``           — ingest/mentions/social/deploy events
  - ``brief_images``   — image generated / approved / rejected
  - ``context_notes``  — daily_brief / weekly_brief / context tendences
  - ``analyses``       — per-politician analysis runs

Rendered rows have a uniform shape:
    {ts, table, source_id, kind, summary, payload}

so the partial template stays agnostic about source tables. The "kind"
field doubles as both the display category (icon picker) and the filter
chip target.

Timestamps:
    All four source tables write timestamps via `now_lv()` or
    `CURRENT_TIMESTAMP`. In practice they're stored as naive LV-local
    `YYYY-MM-DD HH:MM:SS`. We parse with `datetime.fromisoformat()` and
    compare against the operator's wall clock (also LV) for relative
    time strings. Documented inconsistencies in stored timezones are
    acceptable here — the dashboard is operational visibility, not audit.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from src.db import get_db, now_lv_dt

# Maps a filter chip → set of kinds it includes.
FILTER_KINDS: dict[str, set[str]] = {
    "all": set(),  # empty = no filter
    "ingest": {"ingest", "mentions_fetch", "social_fetch", "social_fetch_all"},
    "brief": {"daily_brief", "weekly_brief"},
    "image": {"image_generated", "image_approved", "image_rejected", "image_superseded"},
    "analysis": {"analysis", "context"},
    "deploy": {"deploy"},
    "guardrail": {"mentions_fetch_guardrail"},
}

# Action prefixes for logs table — anything not in this set is dropped from
# the timeline (avoids spamming low-value rows like saeima_vote_claim, of
# which there are 16k+).
_INTERESTING_LOG_ACTIONS = {
    "ingest",
    "mentions_fetch",
    "social_fetch",
    "social_fetch_all",
    "deploy",
    "mentions_fetch_guardrail",
    # Saeima vote stored without a bill summary (Step 3.5 skipped). Written by
    # votes.py but previously had no consumer — surfaced here so the gap is
    # visible in the timeline instead of dying silently in the logs table.
    "saeima_summary_missing",
}


def lv_relative_time(ts: datetime, now: datetime) -> str:
    """Format ``ts`` as a Latvian relative-time string against ``now``."""
    delta = now - ts
    seconds = delta.total_seconds()
    if seconds < 0:
        # Future timestamps shouldn't happen in practice; render absolute.
        return ts.strftime("%Y-%m-%d %H:%M")
    if seconds < 60:
        return "tikko"
    if seconds < 3600:
        return f"pirms {int(seconds // 60)} min"
    if seconds < 86400 and ts.date() == now.date():
        return f"pirms {int(seconds // 3600)} h"
    yesterday = (now.date() - timedelta(days=1))
    if ts.date() == yesterday:
        return "vakar"
    return ts.strftime("%Y-%m-%d")


def _day_group_label(d: date, today: date) -> str:
    if d == today:
        return "Šodien"
    if d == today - timedelta(days=1):
        return f"Vakar ({d.isoformat()})"
    return d.isoformat()


def _summary_for_log(action: str, status: str, details_blob: str | None) -> str:
    details: dict[str, Any] = {}
    if details_blob:
        try:
            details = json.loads(details_blob)
        except (json.JSONDecodeError, TypeError):
            pass
    if action == "ingest":
        n = details.get("documents_stored", 0)
        src = details.get("source_name", "?")
        return f"{n} docs · {src}"
    if action == "mentions_fetch":
        return f"{details.get('stored', 0)}/{details.get('fetched', 0)} stored, {details.get('errors', 0)} err"
    if action in ("social_fetch", "social_fetch_all"):
        return f"{details.get('stored', 0)} tweets · {details.get('accounts', 0)} accounts"
    if action == "deploy":
        return f"deploy {status}"
    if action == "mentions_fetch_guardrail":
        h = details.get("healthy", "?")
        t = details.get("total", "?")
        return f"guardrail tripped — only {h}/{t} slots healthy, falling back to timeline"
    if action == "saeima_summary_missing":
        return f"Saeimas balsojums bez kopsavilkuma (vote #{details.get('vote_db_id', '?')}) — Step 3.5 izlaists"
    return f"{action} · {status}"


def _summary_for_image(approved: int, note_id: int, cost: float, error: str | None) -> tuple[str, str]:
    # approved: 0=pending/generated, 1=approved, 2=rejected (src/graphics/storage.py).
    # -1 is an operator "superseded" marker (an old variant replaced by a regen;
    # written manually, not by code). The .get() default keeps the whole activity
    # feed alive if an unexpected value ever appears again, instead of 500-ing the
    # entire dashboard on one malformed row.
    kind = {
        0: "image_generated",
        1: "image_approved",
        2: "image_rejected",
        -1: "image_superseded",
    }.get(approved, "image_generated")
    if approved == 1:
        return kind, f"image apstiprināts (brief #{note_id})"
    if approved == 2:
        msg = error or "noraidīts"
        return kind, f"image noraidīts (brief #{note_id}) — {msg[:60]}"
    if approved == -1:
        msg = error or "aizstāts"
        return kind, f"image aizstāts (brief #{note_id}) — {msg[:60]}"
    return kind, f"image ģenerēts (brief #{note_id}, ${cost:.3f})"


def get_activity_context(
    db_path: str | None = None,
    limit: int = 20,
    offset: int = 0,
    filter: str | None = None,
    since: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return activity rows for the timeline panel.

    Args:
        limit: row cap (default 20). The "load more" button increments offset.
        offset: pagination offset.
        filter: one of FILTER_KINDS keys; None or 'all' = no filter.
        since: optional cursor dict ``{table: row_id}`` — rows from each
            table where ``id > since[table]`` only. Used by the HTMX
            poll endpoint to avoid re-fetching already-visible rows.
        now: clock override for tests; defaults to ``now_lv_dt()``.
    """
    if now is None:
        now = now_lv_dt()
    today = now.date()

    kinds_filter = FILTER_KINDS.get(filter or "all", set())
    since = since or {}

    db = get_db(db_path) if db_path else get_db()
    try:
        rows: list[dict[str, Any]] = []

        # --- logs ---
        log_rows = db.execute(
            "SELECT id, timestamp, action, status, details "
            "FROM logs "
            "WHERE action IN ({}) AND id > ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?".format(
                ",".join("?" * len(_INTERESTING_LOG_ACTIONS))
            ),
            (*_INTERESTING_LOG_ACTIONS, since.get("logs", 0), limit, offset),
        ).fetchall()
        for r in log_rows:
            rows.append({
                "ts": r["timestamp"],
                "table": "logs",
                "source_id": r["id"],
                "kind": r["action"],
                "status": r["status"],
                "summary": _summary_for_log(r["action"], r["status"], r["details"]),
            })

        # --- brief_images ---
        img_rows = db.execute(
            "SELECT id, note_id, approved, cost_usd, generated_at, error_message "
            "FROM brief_images WHERE id > ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (since.get("brief_images", 0), limit, offset),
        ).fetchall()
        for r in img_rows:
            kind, summary = _summary_for_image(
                r["approved"], r["note_id"], r["cost_usd"], r["error_message"]
            )
            rows.append({
                "ts": r["generated_at"],
                "table": "brief_images",
                "source_id": r["id"],
                "kind": kind,
                "status": "ok",
                "summary": summary,
            })

        # --- context_notes ---
        cn_rows = db.execute(
            "SELECT id, note_type, topic, created_at FROM context_notes "
            "WHERE id > ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (since.get("context_notes", 0), limit, offset),
        ).fetchall()
        for r in cn_rows:
            rows.append({
                "ts": r["created_at"],
                "table": "context_notes",
                "source_id": r["id"],
                "kind": r["note_type"] or "context",
                "status": "ok",
                "summary": (r["topic"] or "(bez topica)")[:80],
            })

        # --- analyses ---
        an_rows = db.execute(
            "SELECT id, opponent_id, created_at FROM analyses "
            "WHERE id > ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (since.get("analyses", 0), limit, offset),
        ).fetchall()
        for r in an_rows:
            rows.append({
                "ts": r["created_at"],
                "table": "analyses",
                "source_id": r["id"],
                "kind": "analysis",
                "status": "ok",
                "summary": f"analīze politiķim #{r['opponent_id']}",
            })
    finally:
        db.close()

    # Filter by kinds chip
    if kinds_filter:
        rows = [r for r in rows if r["kind"] in kinds_filter]

    # Final chronological sort, trim to limit (each source is pre-limited so
    # we have at most 4 * limit candidates before trimming).
    rows.sort(key=lambda r: r["ts"] or "", reverse=True)
    rows = rows[:limit]

    # Augment with display fields
    for r in rows:
        try:
            ts_dt = datetime.fromisoformat(r["ts"]) if r["ts"] else now
        except (ValueError, TypeError):
            ts_dt = now
        r["ts_dt"] = ts_dt
        r["relative_time"] = lv_relative_time(ts_dt, now)
        r["date_str"] = ts_dt.date().isoformat()
        r["day_group_label"] = _day_group_label(ts_dt.date(), today)

    # Group by day for the template
    grouped: list[dict[str, Any]] = []
    if rows:
        current_date = rows[0]["date_str"]
        current_group = {
            "date_str": current_date,
            "label": rows[0]["day_group_label"],
            "rows": [],
        }
        for r in rows:
            if r["date_str"] != current_date:
                grouped.append(current_group)
                current_date = r["date_str"]
                current_group = {
                    "date_str": current_date,
                    "label": r["day_group_label"],
                    "rows": [],
                }
            current_group["rows"].append(r)
        grouped.append(current_group)

    # Cursor for HTMX poll — the highest id seen per table
    cursor = {}
    for r in rows:
        t = r["table"]
        cursor[t] = max(cursor.get(t, 0), r["source_id"])

    return {
        "rows": rows,
        "groups": grouped,
        "cursor": cursor,
        "current_filter": filter or "all",
        "offset": offset,
        "limit": limit,
        "has_more": len(rows) == limit,
    }
