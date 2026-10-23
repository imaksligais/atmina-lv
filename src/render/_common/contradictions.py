"""Shared confirmed contradiction rows for profiles, topics and the register."""
from __future__ import annotations

import sqlite3
from typing import Any

from .enrich import _enrich_contradiction


def fetch_contradictions(
    db: sqlite3.Connection, *, opponent_id: int | None = None, topic: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch and enrich the same columns on every contradiction card surface.

    The register adds its OG-only vote text separately, after chronology is set.
    Keep confirmed for the profile overview's top-contradiction selector.
    """
    # headline kolonna var vēl nebūt vecākā DB — tad NULL.
    cols = {r[1] for r in db.execute("PRAGMA table_info(contradictions)")}
    headline = "ct.headline" if "headline" in cols else "NULL AS headline"
    filters = ["COALESCE(ct.confirmed, 1) = 1"]
    params: list[int | str] = []
    if opponent_id is not None:
        filters.append("ct.opponent_id = ?")
        params.append(opponent_id)
    if topic is not None:
        filters.append("ct.topic = ?")
        params.append(topic)
    rows = db.execute(f"""
        SELECT
            ct.id, ct.opponent_id, ct.claim_old_id, ct.claim_new_id,
            ct.topic, {headline}, ct.summary, ct.severity,
            ct.detected_at, ct.salience, ct.confirmed,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_old.claim_type AS old_claim_type,
            c_old.opponent_id AS old_opponent_id,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote,
            c_new.claim_type AS new_claim_type,
            c_new.opponent_id AS new_opponent_id
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        WHERE {" AND ".join(filters)}
        ORDER BY ct.detected_at DESC
    """, params).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        _enrich_contradiction(d, db)
        results.append(d)
    return results
