"""Render the Pozīcijas (positions) feed page + embedded JSON.

Phase F3d (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs:
- ``output/atmina/pozicijas.html`` — Pozīcijas V2 feed (claim_type
  = 'position' rows, with topic / party / persona facets and
  confidence tier chips)
- ``output/atmina/pozicijas-data.json`` — embedded data for the JS
  client.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.db import now_lv_dt
from src.render._common import (
    FALLBACK_COLOR,
    TOPIC_COLORS,
    _confidence_tier,
    _date_sort_key,
    _domain_label,
    _emit_json,
    _party_short_name,
    _render_page,
    _slugify,
    party_color_map,
)


# 35 canonical topic groups → chip colors for the Pozīcijas V2 feed.
# Single source of truth lives in ``_common.TOPIC_COLORS`` (promoted there
# 2026-06-08 so the Tēmas destination pages can share the same map without a
# sibling import). This module-level alias preserves the historical
# ``positions.PZV1_TOPIC_COLORS`` name for existing readers/tests.
PZV1_TOPIC_COLORS: dict[str, str] = TOPIC_COLORS


def _fetch_claims(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Feed the public Pozīcijas page. Restricted to claim_type='position'.

    Historically this function used string-matching on stance text to flag
    vote rows (``stance.startswith("atbalsta:")`` etc.) via an ``is_vote``
    property. With the Phase A claim_type split that heuristic is no longer
    needed — vote rows are simply excluded from this query.
    """
    rows = db.execute("""
        SELECT c.*, tp.name AS politician_name, tp.party,
               tp.relationship_type, d.source_domain AS doc_source_domain
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE c.claim_type = 'position'
          AND tp.relationship_type != 'inactive'
        ORDER BY c.stated_at DESC
    """).fetchall()

    # Media accounts to exclude from Pozīcijas (not persons, just feeds)
    MEDIA_ACCOUNTS = {"Kas Notiek Latvijā", "Nepareizais"}
    party_colors = party_color_map(db)

    results = []
    for r in rows:
        d = dict(r)
        # Skip media accounts — they belong in X feed only
        if d["politician_name"] in MEDIA_ACCOUNTS:
            continue
        d["slug"] = _slugify(d["politician_name"])
        # Label: Komentētājs for journalists/influencers/neutrals without party
        if d.get("relationship_type") in ("journalist", "influencer", "neutral", "commentator", "organization") and not d.get("party"):
            d["persona_type"] = "Komentētājs"
        else:
            d["persona_type"] = "Politiķis"
        # Pozīcijas V2 enrichment
        party = d.get("party")
        d["party_color"] = party_colors.get(party or "", FALLBACK_COLOR)
        d["party_short"] = _party_short_name(party) if party else "—"
        d["confidence_tier"] = _confidence_tier(d.get("confidence"))
        # Izdevēja etiķete no documents.source_domain, ne no URL hosta —
        # sk. _domain_label() (verdikts 41, 2026-09-06).
        d["source_domain"] = _domain_label(
            d.pop("doc_source_domain", None), d.get("source_url"),
        ) or ""
        d["date_iso"] = (d.get("stated_at") or "")[:10]
        results.append(d)
    results.sort(key=lambda c: _date_sort_key(c.get("stated_at") or ""), reverse=True)
    return results


def _fetch_pozicijas_metrics(claims: list[dict[str, Any]]) -> dict[str, int]:
    """Three header metrics for Pozīcijas V2, from the ``_fetch_claims()`` list:
    - total position claims
    - count stated in the last 7 days (Latvia time)
    - % in augsta+laba tiers (confidence >= 0.75), rounded int.

    Reads the same filtered list the table shows (no inactive politicians,
    no media accounts) — until 2026-10-20 a separate COUNT(*) made the
    header say «Kopā 9 852» above «Rāda 9801 no 9801».
    """
    cutoff = (now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    total = len(claims)
    last_week = sum(1 for c in claims if (c.get("stated_at") or "") >= cutoff)
    good = sum(1 for c in claims if (c.get("confidence") or 0.0) >= 0.75)
    return {
        "total": total,
        "last_week": last_week,
        "confidence_good_pct": round((good / total) * 100) if total else 0,
    }


def render_positions(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
) -> None:
    """Render pozicijas.html + pozicijas-data.json.

    Mirrors the inline block previously at ``src/generate.py`` lines
    2051-2112. Self-contained: re-fetches claims, derives topic/party/
    politician facets, writes one HTML page + one JSON file.
    """
    claims = _fetch_claims(db)
    metrics = _fetch_pozicijas_metrics(claims)

    topic_counts = Counter(c["topic"] for c in claims if c.get("topic"))
    topics_with_counts = sorted(topic_counts.items(), key=lambda x: -x[1])
    topics_with_counts_colors = [
        (name, count, PZV1_TOPIC_COLORS.get(name, FALLBACK_COLOR))
        for name, count in topics_with_counts
    ]

    party_colors = party_color_map(db)
    parties_with_counts = []
    for pname in sorted({c["party"] for c in claims if c.get("party")}):
        parties_with_counts.append((
            pname,
            _party_short_name(pname),
            party_colors.get(pname, FALLBACK_COLOR),
            sum(1 for c in claims if c.get("party") == pname),
        ))
    bez_partijas = sum(1 for c in claims if not c.get("party"))
    if bez_partijas:
        parties_with_counts.append(("Bez partijas", "—", FALLBACK_COLOR, bez_partijas))

    # sorted by count desc so the rail surfaces the busy parties first
    parties_with_counts.sort(key=lambda p: -p[3])

    politicians_with_counts = sorted(
        (
            (n, _slugify(n), sum(1 for c in claims if c.get("politician_name") == n))
            for n in {c["politician_name"] for c in claims if c.get("politician_name")}
        ),
        key=lambda x: (-x[2], x[0]),
    )

    _render_page(env, "pozicijas.html.j2", atmina_dir / "pozicijas.html", {
        "claims": claims,
        "topics": topics_with_counts_colors,
        "parties_with_counts": parties_with_counts,
        "politicians_with_counts": politicians_with_counts,
        "metrics": metrics,
    })

    # Pozīcijas data — split from HTML 2026-04-25 to drop HTML weight
    # 616KB→78KB. LiteSpeed dynamic-compression latency on shared host
    # was the dominant cost (warm-cache loads 6-10s). Tuple shape MUST
    # match assets/pzv1.js IDX_* constants.
    _pz_data = [
        [c["topic"], c.get("party") or "", c["party_short"], c["party_color"],
         c["politician_name"], c["slug"], c.get("stance") or "", c["date_iso"],
         c.get("source_url") or "", c["source_domain"],
         c.get("confidence") or 0.0, c["confidence_tier"],
         c.get("quote") or ""]
        for c in claims
    ]
    _pz_json_bytes = json.dumps(_pz_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _emit_json(_pz_json_bytes, atmina_dir / "pozicijas-data.json")
