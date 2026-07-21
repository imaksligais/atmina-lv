"""Render the Tēmas (topic) destination pages.

New ``temas`` render domain (attention-redesign 2026-06-08). Turns the
32 canonical topic groups from ``src.topic_map.TOPIC_GROUPS`` from a mere
filter parameter into browsable destinations: one directory page plus one
detail page per non-empty group.

Sub-page boundary: imports flow strictly from ``src.render._common`` +
``src.db`` + stdlib (+ jinja2). No peer sub-page imports (F4 leaf rule —
see ``src/render/_orchestrator.py`` docstring "Cycle safety").

Outputs:
- ``output/atmina/temas.html`` — directory grid of topic cards.
- ``output/atmina/temas/<slug>.html`` — per-topic page: top politicians,
  latest positions, in-topic contradictions, related bills (graceful),
  related syntheses, and a generic "Turpini rakt" block.

Topic membership is a direct equality on the canonical group name —
``claims.topic`` / ``contradictions.topic`` already store the normalized
canonical name (CLAUDE.md §Output Conventions: ``store_claim`` /
``store_contradiction`` auto-normalize). Colors come from
``_common.TOPIC_COLORS`` (the single source of truth promoted out of
``positions.py``). Slugs use ``_common._slugify``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    BASE_URL,
    PARTY_COLORS,
    TOPIC_COLORS,
    _confidence_tier,
    _domain_from_url,
    _enrich_contradiction,
    _party_short_name,
    _render_page,
    _slugify,
)
from src.topic_map import TOPIC_GROUPS


def _fetch_topics(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """One entry per ``TOPIC_GROUPS`` key with ≥1 position claim OR ≥1
    contradiction, for the directory grid.

    Returns ``{name, slug, color, position_count, contradiction_count,
    politician_count}`` per non-empty group, ordered by descending
    position count then name (the busy topics surface first). Position
    counts exclude inactive politicians, mirroring the Pozīcijas feed.
    """
    # Position claim counts + distinct active speakers, grouped by topic.
    pos_rows = db.execute("""
        SELECT c.topic AS topic,
               COUNT(*) AS position_count,
               COUNT(DISTINCT c.opponent_id) AS politician_count
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.claim_type = 'position'
          AND tp.relationship_type != 'inactive'
          AND c.topic IS NOT NULL
        GROUP BY c.topic
    """).fetchall()
    pos_by_topic = {r["topic"]: r for r in pos_rows}

    contra_rows = db.execute("""
        SELECT topic, COUNT(*) AS contradiction_count
        FROM contradictions
        WHERE COALESCE(confirmed, 1) = 1
          AND topic IS NOT NULL
        GROUP BY topic
    """).fetchall()
    contra_by_topic = {r["topic"]: r["contradiction_count"] for r in contra_rows}

    topics: list[dict[str, Any]] = []
    for name in TOPIC_GROUPS:
        pos = pos_by_topic.get(name)
        position_count = pos["position_count"] if pos else 0
        contradiction_count = contra_by_topic.get(name, 0)
        if position_count == 0 and contradiction_count == 0:
            continue
        topics.append({
            "name": name,
            "slug": _slugify(name),
            "color": TOPIC_COLORS.get(name, "#8b8fa3"),
            "position_count": position_count,
            "contradiction_count": contradiction_count,
            "politician_count": pos["politician_count"] if pos else 0,
        })

    topics.sort(key=lambda t: (-t["position_count"], t["name"]))
    return topics


def _fetch_topic_detail(
    db: sqlite3.Connection,
    name: str,
    *,
    syntheses: list[dict[str, Any]],
    all_topics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the full render context for a single topic group ``name``.

    Returns ``top_politicians``, ``latest_positions``, ``contradictions``,
    ``related_bills``, ``related_syntheses`` and ``keep_digging`` (the
    generic ``{"columns": [...]}`` shape). All lists are graceful (empty
    when the topic has no rows of that kind).

    ``syntheses`` (orchestrator-preloaded) and ``all_topics`` (computed once
    by ``render_topics``) are threaded in rather than re-loaded per page —
    keeps this a leaf module (no sibling ``syntheses`` import) and avoids
    N disk reads + N×2 topic queries across the per-topic loop.
    """
    # Top politicians by position count on this topic (active only, desc).
    top_politicians: list[dict[str, Any]] = []
    for r in db.execute("""
        SELECT tp.name AS name, tp.party AS party, COUNT(*) AS count
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.claim_type = 'position'
          AND c.topic = ?
          AND tp.relationship_type != 'inactive'
        GROUP BY tp.id
        ORDER BY count DESC, tp.name
        LIMIT 10
    """, (name,)).fetchall():
        party = r["party"] or ""
        top_politicians.append({
            "name": r["name"],
            "slug": _slugify(r["name"]),
            "party": party,
            "party_short": _party_short_name(party) if party else "—",
            "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
            "count": r["count"],
        })

    # Latest positions on this topic (active only, newest first).
    latest_positions: list[dict[str, Any]] = []
    for r in db.execute("""
        SELECT tp.name AS politician_name, tp.party AS party,
               c.stance AS stance, c.stated_at AS stated_at,
               c.source_url AS source_url, c.confidence AS confidence
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.claim_type = 'position'
          AND c.topic = ?
          AND tp.relationship_type != 'inactive'
        ORDER BY c.stated_at DESC
        LIMIT 15
    """, (name,)).fetchall():
        party = r["party"] or ""
        latest_positions.append({
            "politician_name": r["politician_name"],
            "slug": _slugify(r["politician_name"]),
            "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
            "stance": r["stance"] or "",
            "stated_at": (r["stated_at"] or "")[:10],
            "source_url": r["source_url"] or "",
            "source_domain": _domain_from_url(r["source_url"]),
            "confidence": _confidence_tier(r["confidence"]),
        })

    # In-topic contradictions, enriched the same way as the Pretrunas feed.
    contradictions: list[dict[str, Any]] = []
    for r in db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_old.claim_type AS old_claim_type,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote,
            c_new.claim_type AS new_claim_type
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        WHERE COALESCE(ct.confirmed, 1) = 1
          AND ct.topic = ?
        ORDER BY ct.detected_at DESC
    """, (name,)).fetchall():
        d = dict(r)
        _enrich_contradiction(d, db)
        contradictions.append(d)

    # Related bills: no clean topic linkage on saeima_bills (no topic column
    # tying a bill to a canonical group), so we do NOT invent a join — empty
    # by contract. Revisit if/when bills carry a normalized topic.
    related_bills: list[dict[str, Any]] = []

    # Related syntheses — frontmatter ``topics`` list contains this group name.
    related_syntheses = [
        s for s in syntheses
        if name in (s.get("topics") or [])
    ]

    # "Turpini rakt" — generic columns shape consumed by _keep_digging.html.j2.
    columns: list[dict[str, Any]] = []
    if top_politicians:
        columns.append({
            "title": "Top politiķi",
            "links": [
                {
                    "label": p["name"],
                    "href": f"../politiki/{p['slug']}.html",
                    "sub": f"{p['count']} poz.",
                }
                for p in top_politicians[:5]
            ],
        })
    if contradictions:
        columns.append({
            "title": "Saistītās pretrunas",
            "links": [
                {
                    "label": c["politician_name"],
                    "href": f"../pretrunas/{c['id']}.html",
                    "sub": c["severity_lv"],
                }
                for c in contradictions[:5]
            ],
        })
    # "Cita tēma" — a couple of sibling topics to keep the session going.
    other_topics = [t for t in all_topics if t["name"] != name][:5]
    if other_topics:
        columns.append({
            "title": "Citas tēmas",
            "links": [
                {
                    "label": t["name"],
                    "href": f"{t['slug']}.html",
                    "sub": f"{t['position_count']} poz.",
                }
                for t in other_topics
            ],
        })
    keep_digging = {"columns": columns}

    return {
        "name": name,
        "slug": _slugify(name),
        "color": TOPIC_COLORS.get(name, "#8b8fa3"),
        "top_politicians": top_politicians,
        "latest_positions": latest_positions,
        "contradictions": contradictions,
        "related_bills": related_bills,
        "related_syntheses": related_syntheses,
        "keep_digging": keep_digging,
    }


def render_topics(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    syntheses: list[dict[str, Any]] | None = None,
) -> int:
    """Write ``temas.html`` (directory) + ``temas/<slug>.html`` per non-empty
    canonical topic group. Returns the page count (index + per-topic).

    ``syntheses`` is the orchestrator's pre-loaded list (used for the per-topic
    "Saistītās sintēzes" block); ``None`` → no synthesis cross-links (tests).
    """
    syntheses = syntheses or []
    topics = _fetch_topics(db)

    _render_page(env, "temas.html.j2", atmina_dir / "temas.html", {
        "topics": topics,
        "BASE_URL": BASE_URL,
    })

    temas_dir = atmina_dir / "temas"
    temas_dir.mkdir(parents=True, exist_ok=True)
    for t in topics:
        detail = _fetch_topic_detail(
            db, t["name"], syntheses=syntheses, all_topics=topics
        )
        _render_page(
            env,
            "tema.html.j2",
            temas_dir / f"{t['slug']}.html",
            {
                "topic": detail,
                "digging": detail["keep_digging"],
                "BASE_URL": BASE_URL,
            },
        )

    return 1 + len(topics)
