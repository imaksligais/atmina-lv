"""Emit data/sg-index.json — the homepage typeahead suggestion sidecar.

Small (~16-18 KB raw) index of politicians, topics and parties consumed by
``assets/sgv1.js`` (hero search suggestions). Tuple shapes are a load-bearing
convention — the JS reads positional indexes, so any reorder here must update
the ``P_*``/``T_*``/``G_*`` constants in sgv1.js and the arity lock in
``tests/test_search_index.py``.

Schema (compact arrays, pzv1 style)::

    {"v": 3,
     "p": [[name, slug, party_short, party_color, has_photo, claims, contras, cat], ...],
     "t": [[topic, color, claims], ...],
     "g": [[name, short, color, claims], ...],
     "c": [[label, id, politician_name, severity, topic], ...]}

``cat`` (v2, 2026-06-09) groups the typeahead sections and derives from
``_persona_category``: 0 = politiķis (Deputāti/Amatpersonas),
1 = komentētājs (Žurnālisti/Analītiķi/Ietekmētāji/Citi),
2 = iestāde/medijs (Mediji, Iestādes; vēsturiski "Iestādes un mediji").

``c`` (v3, 2026-07-04) is the pretrunas suggestion list — the site's flagship
content, now searchable from every page's nav search. ``label`` is the
contradiction summary truncated on a word boundary (~80 chars); ``id`` targets
``pretrunas/<id>.html``. Sorted by ``id`` DESC (recent first).

Counting contracts:
- politicians exclude ``relationship_type IN ('inactive', 'commentator')``;
- ``claims`` counts are ``claim_type='position'`` only (matches the public
  Pozīcijas feed scope in ``positions.py::_fetch_claims``);
- ``contras`` counts apply ``COALESCE(confirmed, 1) = 1`` — the same filter as
  every public pretrunas surface (NOT the unfiltered count in
  ``politicians.py::_fetch_politicians``; see BACKLOG);
- the ``c`` list applies the same ``COALESCE(confirmed, 1) = 1`` filter and
  excludes inactive politicians (matches every public pretrunas surface).

Sub-page boundary: imports only from ``src.render._common`` and stdlib.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.render._common import (
    ASSETS_DIR,
    PARTY_COLORS,
    TOPIC_COLORS,
    _emit_json_compressed,
    _outlet_feed_map,
    _party_short_name,
    _persona_category,
    _slugify,
    _split_org_category,
)

logger = logging.getLogger(__name__)

_FALLBACK_COLOR = "#8b8fa3"
_CONTRA_LABEL_MAX = 80

# _persona_category label → sgv1.js section bucket (P_CAT tuple field).
_CATEGORY_TO_CAT = {
    "Deputāti": 0,
    "Amatpersonas": 0,
    "Žurnālisti": 1,
    "Analītiķi": 1,
    "Ietekmētāji": 1,
    "Citi": 1,
    "Iestādes un mediji": 2,
    "Mediji": 2,
    "Iestādes": 2,
}


def _truncate_label(text: str, limit: int = _CONTRA_LABEL_MAX) -> str:
    """Collapse whitespace and clip to ``limit`` chars on a word boundary."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _fetch_search_index(db: sqlite3.Connection) -> dict[str, Any]:
    """Build the three suggestion lists (politicians / topics / parties)."""
    # Batch count maps (two GROUP BY queries instead of N+1 per politician).
    claims_by_pol = dict(db.execute("""
        SELECT opponent_id, COUNT(*) FROM claims
        WHERE claim_type = 'position'
        GROUP BY opponent_id
    """).fetchall())
    contras_by_pol = dict(db.execute("""
        SELECT opponent_id, COUNT(*) FROM contradictions
        WHERE COALESCE(confirmed, 1) = 1
        GROUP BY opponent_id
    """).fetchall())
    try:
        votes_by_pol = dict(db.execute("""
            SELECT politician_id, COUNT(*) FROM saeima_individual_votes
            GROUP BY politician_id
        """).fetchall())
    except sqlite3.OperationalError:  # minimal/test DBs without vote ledger
        votes_by_pol = {}

    media_feed_ids = set(_outlet_feed_map(db))

    politicians: list[list[Any]] = []
    for r in db.execute("""
        SELECT id, name, party, role, relationship_type FROM tracked_politicians
        WHERE relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY name
    """).fetchall():
        slug = _slugify(r["name"])
        party = r["party"] or ""
        category = _persona_category(
            votes_by_pol.get(r["id"], 0), r["relationship_type"], r["party"], r["role"]
        )
        category = _split_org_category(category, r["id"], media_feed_ids)
        politicians.append([
            r["name"],
            slug,
            _party_short_name(party) if party else "—",
            PARTY_COLORS.get(party, _FALLBACK_COLOR),
            1 if (ASSETS_DIR / "photos" / f"{slug}.jpg").exists() else 0,
            claims_by_pol.get(r["id"], 0),
            contras_by_pol.get(r["id"], 0),
            _CATEGORY_TO_CAT.get(category, 1),
        ])

    # Topics — same scope as the Pozīcijas rail counts.
    topics = [
        [row["topic"], TOPIC_COLORS.get(row["topic"], _FALLBACK_COLOR), row["cnt"]]
        for row in db.execute("""
            SELECT c.topic, COUNT(*) AS cnt
            FROM claims c
            JOIN tracked_politicians tp ON c.opponent_id = tp.id
            WHERE c.claim_type = 'position'
              AND tp.relationship_type != 'inactive'
              AND c.topic IS NOT NULL AND c.topic != ''
            GROUP BY c.topic
            ORDER BY cnt DESC
        """).fetchall()
    ]

    # Parties — short/full double-match per invariant 10.
    parties: list[list[Any]] = []
    try:
        party_rows = db.execute("SELECT name, short_name FROM parties ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        party_rows = []
    for p in party_rows:
        short = p["short_name"]
        cnt = db.execute("""
            SELECT COUNT(*) FROM claims c
            JOIN tracked_politicians tp ON c.opponent_id = tp.id
            WHERE (tp.party = ? OR tp.party = ?)
              AND tp.relationship_type NOT IN ('inactive', 'commentator')
              AND c.claim_type = 'position'
        """, (p["name"], short)).fetchone()[0]
        parties.append([
            p["name"],
            short,
            PARTY_COLORS.get(p["name"]) or PARTY_COLORS.get(short, _FALLBACK_COLOR),
            cnt,
        ])

    # Pretrunas — flagship content, searchable site-wide (v3). Same public
    # scope as every pretrunas surface: confirmed + active politician only.
    contradictions: list[list[Any]] = []
    for r in db.execute("""
        SELECT ct.id, ct.summary, ct.severity, ct.topic, tp.name AS pol_name
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        WHERE COALESCE(ct.confirmed, 1) = 1
          AND tp.relationship_type != 'inactive'
        ORDER BY ct.id DESC
    """).fetchall():
        contradictions.append([
            _truncate_label(r["summary"]),
            r["id"],
            r["pol_name"],
            r["severity"] or "",
            r["topic"] or "",
        ])

    return {"v": 3, "p": politicians, "t": topics, "g": parties, "c": contradictions}


def _emit_sg_index_json(
    payload_data: dict[str, Any], atmina_dir: Path, basename: str = "sg-index"
) -> Path:
    """Write the suggestion index to ``atmina/data/<basename>.json``.

    Pre-compressed ``.br``/``.gz`` siblings are served by the same htaccess
    ``*.json`` rewrite. Idempotent. Mirrors ``links.py::_emit_saites_json``.
    """
    data_dir = atmina_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / f"{basename}.json"
    payload = json.dumps(
        payload_data, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    _emit_json_compressed(payload, dest)
    logger.info(
        "Wrote sg-index sidecar → %s (%d raw, %d br, %d gz)",
        dest,
        dest.stat().st_size,
        (data_dir / f"{basename}.json.br").stat().st_size,
        (data_dir / f"{basename}.json.gz").stat().st_size,
    )
    return dest


def render_search_index(db: sqlite3.Connection, atmina_dir: Path) -> None:
    """Fetch + emit the typeahead suggestion sidecar."""
    _emit_sg_index_json(_fetch_search_index(db), atmina_dir)
