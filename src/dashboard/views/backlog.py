"""Extraction backlog panel view helper.

Surfaces:
1. Unreviewed-doc count by platform (today + cumulative).
2. Top 5 tracked politicians by unreviewed-doc count (excluding
   `relationship_type='inactive'`), to help the operator triage who
   to dispatch `@claim-extractor` for next.

30 s module cache, keyed on the (date, db_path) tuple — small enough
that operator manual refreshes feel snappy, large enough that the
panel doesn't re-aggregate on every panel-internal HTMX swap.
"""
from __future__ import annotations

import time
from typing import Any

from src.db import get_db, today_lv

_CACHE_TTL_SECONDS = 30
_CACHE: dict[str, Any] = {"key": None, "ts": None, "result": None}


def _compute_backlog(date: str, db_path: str | None) -> dict[str, Any]:
    db = get_db(db_path) if db_path else get_db()
    try:
        platform_rows = db.execute(
            """SELECT platform,
                      SUM(CASE WHEN DATE(scraped_at, 'localtime') = ? THEN 1 ELSE 0 END) AS today,
                      COUNT(*) AS total
                 FROM documents
                WHERE reviewed_at IS NULL
                GROUP BY platform
                ORDER BY total DESC""",
            (date,),
        ).fetchall()

        today_unrev = db.execute(
            "SELECT COUNT(*) AS cnt FROM documents "
            "WHERE reviewed_at IS NULL AND DATE(scraped_at, 'localtime') = ?",
            (date,),
        ).fetchone()["cnt"]

        total_unrev = db.execute(
            "SELECT COUNT(*) AS cnt FROM documents WHERE reviewed_at IS NULL"
        ).fetchone()["cnt"]

        top_pids_rows = db.execute(
            """SELECT tp.id AS pid, tp.name, tp.party,
                      COUNT(DISTINCT dp.document_id) AS doc_count
                 FROM tracked_politicians tp
                 JOIN document_politicians dp ON dp.politician_id = tp.id
                 JOIN documents d ON d.id = dp.document_id
                WHERE tp.relationship_type != 'inactive'
                  AND d.reviewed_at IS NULL
                GROUP BY tp.id
                ORDER BY doc_count DESC
                LIMIT 5"""
        ).fetchall()
    finally:
        db.close()

    return {
        "date": date,
        "platforms": [
            {"platform": r["platform"] or "?", "today": r["today"], "total": r["total"]}
            for r in platform_rows
        ],
        "top_pids": [
            {
                "pid": r["pid"],
                "name": r["name"],
                "party": r["party"],
                "doc_count": r["doc_count"],
            }
            for r in top_pids_rows
        ],
        "today_unreviewed": today_unrev,
        "total_unreviewed": total_unrev,
    }


def get_backlog_context(
    date: str | None = None,
    db_path: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if date is None:
        date = today_lv().isoformat()

    key = (date, db_path)
    now = time.time()
    if (
        not force
        and _CACHE["key"] == key
        and _CACHE["ts"] is not None
        and (now - _CACHE["ts"]) < _CACHE_TTL_SECONDS
        and _CACHE["result"] is not None
    ):
        return _CACHE["result"]

    result = _compute_backlog(date, db_path)
    _CACHE["key"] = key
    _CACHE["ts"] = now
    _CACHE["result"] = result
    return result
