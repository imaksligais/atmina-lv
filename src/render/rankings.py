"""Site-wide discovery rankings for the homepage "Atklāj" block.

Phase P1-R (attention-redesign plan 2026-06-08 § Task P1-R). A leaf
sub-page helper: imports only from ``src.render._common`` + ``src.db`` +
stdlib (no sibling sub-page imports — see ``src/render/_orchestrator.py``
docstring "Cycle safety").

``fetch_rankings`` is pure aggregation. Two of its four ranks reuse the
orchestrator's already-enriched ``contradictions`` list (slug, party_color,
delta_days, severity_* already present) and add NO new query; the other two
run one small DB query each. Framing is neutral throughout — counts and
percentages, never a "score" or value judgement (CLAUDE.md §Neitralitātes
sargs; audit warning #6).
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import timedelta
from typing import Any

from src.db import today_lv
from src.render._common import ASSETS_DIR, PARTY_COLORS, _slugify


def _has_photo(slug: str) -> bool:
    """True when a tracked photo exists at ``assets/photos/<slug>.jpg``.

    Mirrors the enrichment in ``_common`` (contradiction rows) so the Rangi
    "Līderu josla" can show a face for #1 and a 20px avatar for the rest,
    falling back to initials when no photo is present."""
    return (ASSETS_DIR / "photos" / f"{slug}.jpg").exists()


def fetch_rankings(
    db: sqlite3.Connection,
    contradictions: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> dict[str, list[dict[str, Any]]]:
    """Site-wide discovery ranks. Pure aggregation; reuses already-enriched
    contradictions (slug/party_color/delta_days/severity_* present) and runs
    two small DB queries. Neutral framing — counts and %, never a 'score'."""
    return {
        "most_contradictions": _most_contradictions(contradictions, limit),
        "biggest_reversals": _biggest_reversals(contradictions, limit),
        "most_active_7d": _most_active_7d(db, limit),
        "vote_alignment_outliers": _vote_alignment_outliers(db, limit),
    }


def _most_contradictions(
    contradictions: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Politicians by total contradiction count, desc. No new query —
    aggregates the passed-in enriched list."""
    counts: Counter[str] = Counter()
    meta: dict[str, dict[str, Any]] = {}
    for c in contradictions:
        name = c.get("politician_name")
        if not name:
            continue
        counts[name] += 1
        if name not in meta:
            meta[name] = {
                "slug": c.get("slug") or _slugify(name),
                "party": c.get("party") or "",
                "party_color": c.get("party_color") or "#8b8fa3",
            }
    out: list[dict[str, Any]] = []
    for name, count in counts.most_common(limit):
        m = meta[name]
        out.append({
            "name": name,
            "slug": m["slug"],
            "party": m["party"],
            "party_color": m["party_color"],
            "has_photo": _has_photo(m["slug"]),
            "count": count,
        })
    return out


def _biggest_reversals(
    contradictions: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Contradictions with the largest day-gap between the two stances, desc.
    No new query — filters/sorts the passed-in enriched list."""
    eligible = [c for c in contradictions if c.get("delta_days") is not None]
    eligible.sort(key=lambda c: c["delta_days"], reverse=True)
    out: list[dict[str, Any]] = []
    for c in eligible[:limit]:
        slug = c.get("slug") or _slugify(c.get("politician_name") or "")
        out.append({
            "id": c.get("id"),
            "name": c.get("politician_name"),
            "slug": slug,
            "party_color": c.get("party_color") or "#8b8fa3",
            "has_photo": _has_photo(slug),
            "topic": c.get("topic"),
            "delta_days": c["delta_days"],
            "severity_lv": c.get("severity_lv") or "",
            "severity_glyph": c.get("severity_glyph") or "·",
        })
    return out


def _most_active_7d(db: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    """Most active politicians by position claims in the trailing 7 days.

    Mirrors the cutoff_7d pattern in ``dashboard._fetch_stats``: only
    ``claim_type='position'`` (rhetorical stances, not vote batches),
    ``stated_at >= cutoff``, excludes inactive politicians.
    """
    cutoff_7d = (today_lv() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = db.execute(
        """
        SELECT tp.name, tp.party, COUNT(*) AS cnt
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.claim_type = 'position'
          AND c.stated_at >= ?
          AND tp.relationship_type != 'inactive'
        GROUP BY c.opponent_id
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (cutoff_7d, limit),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        party = r["party"] or ""
        slug = _slugify(r["name"])
        out.append({
            "name": r["name"],
            "slug": slug,
            "party": party,
            "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
            "has_photo": _has_photo(slug),
            "count": r["cnt"],
        })
    return out


def _vote_alignment_outliers(
    db: sqlite3.Connection, limit: int
) -> list[dict[str, Any]]:
    """Current deputies ranked by how often their CAST vote matches the
    chamber majority.

    Only substantive cast ballots count — ``vote IN ('Par','Pret','Atturas')``
    in BOTH the majority computation and the per-deputy denominator. Attendance
    /registration states (``Reģistrējies``, ``Nebalsoja``, ``Nereģistrējies``)
    are excluded so the metric measures vote-matching, not presence (otherwise a
    seat-warmer with mostly non-votes spuriously tops the list). Per ``vote_id``
    the majority is the most-common cast value; per current deputy
    (``relationship_type != 'inactive'``) we compute the share of their cast
    votes matching it, restricted to ``sample >= 50``, lowest agreement first.

    Neutral metric (UI: "Sakritība ar Saeimas vairākumu") — a factual
    percentage, never a "rebel"/"loyalist" judgement. Low alignment is the
    norm for opposition deputies and is not an evaluation.

    Returns ``[]`` gracefully if the query yields no qualifying rows.
    """
    rows = db.execute(
        """
        WITH majority AS (
            SELECT vote_id, vote AS maj_vote
            FROM (
                SELECT vote_id, vote, COUNT(*) AS n,
                       ROW_NUMBER() OVER (
                           PARTITION BY vote_id ORDER BY COUNT(*) DESC, vote
                       ) AS rn
                FROM saeima_individual_votes
                WHERE vote IN ('Par', 'Pret', 'Atturas')
                GROUP BY vote_id, vote
            )
            WHERE rn = 1
        )
        SELECT tp.id, tp.name, tp.party,
               SUM(CASE WHEN siv.vote = m.maj_vote THEN 1 ELSE 0 END) AS agree,
               COUNT(*) AS total
        FROM saeima_individual_votes siv
        JOIN majority m ON m.vote_id = siv.vote_id
        JOIN tracked_politicians tp ON siv.politician_id = tp.id
        WHERE tp.relationship_type != 'inactive'
          AND siv.vote IN ('Par', 'Pret', 'Atturas')
        GROUP BY siv.politician_id
        HAVING total >= 50
        ORDER BY (CAST(agree AS REAL) / total) ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        party = r["party"] or ""
        slug = _slugify(r["name"])
        out.append({
            "name": r["name"],
            "slug": slug,
            "party": party,
            "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
            "has_photo": _has_photo(slug),
            "agree_pct": round(r["agree"] * 100 / r["total"]),
            "sample": r["total"],
        })
    return out
