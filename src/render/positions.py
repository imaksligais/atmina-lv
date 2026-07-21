"""Render the Pozīcijas (positions) feed page + embedded JSON.

Phase F3d (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs:
- ``output/atmina/pozicijas.html`` — Pozīcijas V2 feed (claim_type
  = 'position' rows, with topic / party / persona facets and
  confidence tier chips)
- ``output/atmina/pozicijas-data.json`` — embedded data for the JS
  client. Pre-compressed `.br` and `.gz` siblings are also written
  so LiteSpeed's rewrite rule can serve the best variant per
  Accept-Encoding header.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment

from src.db import now_lv_dt
from src.render._common import (
    PARTY_COLORS,
    TOPIC_COLORS,
    _confidence_tier,
    _date_sort_key,
    _emit_json_compressed,
    _party_short_name,
    _render_page,
    _slugify,
)


# 32 canonical topic groups → chip colors for the Pozīcijas V2 feed.
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
               tp.relationship_type
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.claim_type = 'position'
          AND tp.relationship_type != 'inactive'
        ORDER BY c.stated_at DESC
    """).fetchall()

    # Media accounts to exclude from Pozīcijas (not persons, just feeds)
    MEDIA_ACCOUNTS = {"Kas Notiek Latvijā", "Nepareizais"}

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
        d["party_color"] = PARTY_COLORS.get(party or "", "#8b8fa3")
        d["party_short"] = _party_short_name(party) if party else "—"
        d["confidence_tier"] = _confidence_tier(d.get("confidence"))
        src_url = d.get("source_url") or ""
        netloc = urlparse(src_url).netloc if src_url else ""
        d["source_domain"] = netloc.removeprefix("www.")
        d["date_iso"] = (d.get("stated_at") or "")[:10]
        results.append(d)
    results.sort(key=lambda c: _date_sort_key(c.get("stated_at") or ""), reverse=True)
    return results


def _fetch_pozicijas_metrics(db: sqlite3.Connection) -> dict[str, int]:
    """Three header metrics for Pozīcijas V2:
    - total position claims
    - count stated in the last 7 days (Latvia time)
    - % in augsta+laba tiers (confidence >= 0.75), rounded int.

    Excludes claim_type='saeima_vote' rows (Pozīcijas feed is position-only).
    """
    row = db.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN stated_at >= ? THEN 1 ELSE 0 END) AS last_week,
            SUM(CASE WHEN confidence >= 0.75 THEN 1 ELSE 0 END) AS good
        FROM claims
        WHERE claim_type = 'position'
    """, ((now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),)).fetchone()

    total = row["total"] or 0
    good = row["good"] or 0
    return {
        "total": total,
        "last_week": row["last_week"] or 0,
        "confidence_good_pct": round((good / total) * 100) if total else 0,
    }


def render_positions(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
) -> None:
    """Render pozicijas.html + pozicijas-data.json (+ .br + .gz).

    Mirrors the inline block previously at ``src/generate.py`` lines
    2051-2112. Self-contained: re-fetches claims, derives topic/party/
    politician facets, writes one HTML page + 3 JSON variants.
    """
    claims = _fetch_claims(db)
    metrics = _fetch_pozicijas_metrics(db)

    topic_counts = Counter(c["topic"] for c in claims if c.get("topic"))
    topics_with_counts = sorted(topic_counts.items(), key=lambda x: -x[1])
    topics_with_counts_colors = [
        (name, count, PZV1_TOPIC_COLORS.get(name, "#8b8fa3"))
        for name, count in topics_with_counts
    ]

    parties_with_counts = []
    for pname in sorted({c["party"] for c in claims if c.get("party")}):
        parties_with_counts.append((
            pname,
            _party_short_name(pname),
            PARTY_COLORS.get(pname, "#8b8fa3"),
            sum(1 for c in claims if c.get("party") == pname),
        ))
    bez_partijas = sum(1 for c in claims if not c.get("party"))
    if bez_partijas:
        parties_with_counts.append(("Bez partijas", "—", "#8b8fa3", bez_partijas))

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
    # Pre-compress for serving via .htaccess rewrite — LiteSpeed shared host
    # does not auto-compress application/json. Brotli + gzip variants let
    # the rewrite rule pick the best for the Accept-Encoding header.
    _emit_json_compressed(_pz_json_bytes, atmina_dir / "pozicijas-data.json")
