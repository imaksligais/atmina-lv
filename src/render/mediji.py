"""Render the Mediji (media outlets) pages.

Outlets are config-driven (``src/outlets.py`` reads ``sources.yaml``) — there is
no outlets DB table. Coverage is computed at render time from existing
documents/document_politicians/claims, grouped by outlet via a normalized host
map, in single-pass queries (NOT per-outlet N+1 — mirrors the anti-N+1
discipline in ``src/render/blog.py::_compute_brief_footers``).

Descriptive only: counts + shares, every figure derived from data. No tone, no
labels — see docs/superpowers/specs/2026-06-01-media-outlet-profiles-design.md.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.outlets import host_to_outlet
from src.render._common import (
    ASSETS_DIR,
    PARTY_COLORS,
    _party_page_slug,
    _render_page,
    _slugify,
    norm_source_domain_sql,
)
# Canonical audience/non-first-party roles excluded from "who an outlet covers".
from src.render.blog import _FOOTER_POSITION_EXCLUDED_ROLES

# Normalized host expression (strip leading www.) for grouping documents.
_NORM = norm_source_domain_sql("d.source_domain")

# Žurnālistikas platformas — ieskaita pārklājuma salīdzinājumos (politiķi/partijas/tēmas).
_COVERAGE_PLATFORMS = ("web", "web_scraper")
# Apjoms (kartītes skaitītājs) papildus ieskaita oficiālā izdevēja dokumentus
# (platform='vestnesis') — tie NAV žurnālistika un paliek ārpus salīdzinājumiem.
_VOLUME_PLATFORMS = _COVERAGE_PLATFORMS + ("vestnesis",)


def _empty_cov() -> dict[str, Any]:
    return {"volume": 0, "by_politician": {}, "by_party": {}, "by_topic": {}, "recent": []}


def _volume_phrase(n: int, plural: str) -> str:
    """'1421 dokuments' / '1422 dokumenti' — LV: vienskaitlis, ja skaitlis
    beidzas ar 1, bet ne ar 11; plural nominatīvs -i → vienskaitlis -s."""
    noun = plural[:-1] + "s" if n % 10 == 1 and n % 100 != 11 else plural
    return f"{n} {noun}"


def _party_slug_map(db: sqlite3.Connection) -> dict[str, str]:
    """Party identifier -> detail-page slug (short_name lowercased). Keyed by
    BOTH full name and short_name, because tp.party stores either form depending
    on how the politician was seeded (e.g. 'MMN' as short vs 'Jaunā Vienotība' as
    full). Coverage names absent from the parties table (e.g. 'Bezpartejisks',
    joint lists) get no link."""
    m: dict[str, str] = {}
    for name, short in db.execute(
            "SELECT name, short_name FROM parties WHERE short_name IS NOT NULL"):
        slug = _party_page_slug(short)
        m[name] = slug
        m[short] = slug
    return m


def _fetch_coverage(db: sqlite3.Connection,
                    outlets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-outlet coverage aggregates, keyed by short_name. Single-pass queries."""
    h2o = host_to_outlet(outlets)
    cov = {o["short_name"]: _empty_cov() for o in outlets}
    hosts = tuple(h2o)
    if not hosts:
        return cov
    hp = ",".join("?" * len(hosts))
    excl = _FOOTER_POSITION_EXCLUDED_ROLES
    ep = ",".join("?" * len(excl))
    cp = ",".join("?" * len(_COVERAGE_PLATFORMS))
    vp = ",".join("?" * len(_VOLUME_PLATFORMS))

    # Volume per outlet
    for host, n in db.execute(
        f"SELECT {_NORM} h, COUNT(*) FROM documents d "
        f"WHERE d.platform IN ({vp}) AND {_NORM} IN ({hp}) GROUP BY h",
            (*_VOLUME_PLATFORMS, *hosts)):
        cov[h2o[host]]["volume"] += n

    # Who they cover + by party (one pass; DISTINCT docs per politician)
    for host, name, party, c in db.execute(
        f"""SELECT {_NORM} h, tp.name, tp.party, COUNT(DISTINCT d.id)
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            JOIN tracked_politicians tp ON tp.id = dp.politician_id
            WHERE d.platform IN ({cp}) AND {_NORM} IN ({hp})
              AND tp.relationship_type NOT IN ({ep})
            GROUP BY h, tp.id""", (*_COVERAGE_PLATFORMS, *hosts, *excl)):
        o = cov[h2o[host]]
        o["by_politician"][name] = {"party": party, "count": c, "slug": _slugify(name)}
        if party:
            o["by_party"][party] = o["by_party"].get(party, 0) + c

    # Top topics (via claims on the outlet's journalism docs)
    for host, topic, n in db.execute(
        f"""SELECT {_NORM} h, c.topic, COUNT(*)
            FROM claims c JOIN documents d ON d.id = c.document_id
            WHERE d.platform IN ({cp}) AND {_NORM} IN ({hp}) AND c.claim_type='position'
            GROUP BY h, c.topic""", (*_COVERAGE_PLATFORMS, *hosts)):
        cov[h2o[host]]["by_topic"][topic] = n

    # Recent articles (top 5 per outlet) — newest first, bucketed in Python
    db.row_factory = sqlite3.Row
    rows = db.execute(
        f"""SELECT {_NORM} h, d.source_url AS url, d.content AS content,
                   d.scraped_at AS scraped_at
            FROM documents d
            WHERE d.platform IN ({vp}) AND {_NORM} IN ({hp})
            ORDER BY d.scraped_at DESC""", (*_VOLUME_PLATFORMS, *hosts)).fetchall()
    for r in rows:
        bucket = cov[h2o[r["h"]]]["recent"]
        if len(bucket) < 5:
            text = (r["content"] or "").replace("\n", " ").strip()
            bucket.append({
                "url": r["url"],
                "title": text[:90] + ("..." if len(text) > 90 else ""),
                "date": (r["scraped_at"] or "")[:10],
            })
    return cov


def _fetch_outlet_feeds(db: sqlite3.Connection,
                        outlets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """short_name -> outleta X feedu kartītes (vārds, slug, handle, publikāciju
    skaits, foto), kārtotas pēc publikācijām dilstoši. Join caur
    social_accounts.handle (case-insensitive); x_feeds handle bez DB rindas ->
    stderr brīdinājums + izlaists (validation-level skip, ne kļūda)."""
    handle_to_short: dict[str, str] = {}
    for o in outlets:
        for h in o.get("x_feeds") or []:
            handle_to_short.setdefault(h.lower(), o["short_name"])
    feeds: dict[str, list[dict[str, Any]]] = {o["short_name"]: [] for o in outlets}
    if not handle_to_short:
        return feeds
    photo_dir = ASSETS_DIR / "photos"
    matched: set[str] = set()
    for handle, name, pubs in db.execute(
        """SELECT sa.handle, tp.name,
                  (SELECT COUNT(*) FROM document_politicians dp
                   WHERE dp.politician_id = tp.id) AS pubs
           FROM social_accounts sa
           JOIN tracked_politicians tp ON tp.id = sa.opponent_id
           WHERE sa.platform IN ('twitter', 'x')"""):
        short = handle_to_short.get((handle or "").lower())
        if short is None:
            continue
        matched.add((handle or "").lower())
        slug = _slugify(name)
        feeds[short].append({
            "name": name, "slug": slug, "handle": handle, "pubs": pubs,
            "has_photo": (photo_dir / f"{slug}.jpg").exists(),
        })
    for h, short in handle_to_short.items():
        if h not in matched:
            print(f"[mediji] x_feeds @{h} ({short}) nav social_accounts rindas — izlaists",
                  file=sys.stderr)
    for lst in feeds.values():
        lst.sort(key=lambda f: -f["pubs"])
    return feeds


def _cross_outlet_avg_party_share(cov: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Mean per-party coverage share across outlets (reference line for the
    per-outlet share, so incumbency isn't misread as bias). Share = party's
    tag-count / outlet's total party tags."""
    shares: dict[str, list[float]] = {}
    for o in cov.values():
        total = sum(o["by_party"].values())
        if not total:
            continue
        for party, c in o["by_party"].items():
            shares.setdefault(party, []).append(c / total)
    n_outlets = sum(1 for o in cov.values() if sum(o["by_party"].values()) > 0) or 1
    # average over ALL covering outlets (absent party counts as 0 share)
    return {p: sum(v) / n_outlets for p, v in shares.items()}


def _party_shares(by_party: dict[str, int]) -> list[dict[str, Any]]:
    total = sum(by_party.values()) or 1
    rows = [{"party": p, "count": c, "share": c / total,
             "count_phrase": _volume_phrase(c, "raksti")}
            for p, c in by_party.items()]
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _top(d: dict[str, Any], n: int) -> list[dict[str, Any]]:
    return sorted(
        ({"key": k, **(v if isinstance(v, dict) else {"count": v})}
         for k, v in d.items()),
        key=lambda r: r["count"], reverse=True,
    )[:n]


def _outlet_detail(outlet: dict[str, Any], cov: dict[str, Any],
                   avg_share: dict[str, float],
                   party_slugs: dict[str, str]) -> dict[str, Any]:
    party_rows = _party_shares(cov["by_party"])
    for r in party_rows:
        r["avg_share"] = avg_share.get(r["party"], 0.0)
        r["party_color"] = PARTY_COLORS.get(r["party"], "#8b8fa3")
        r["party_slug"] = party_slugs.get(r["party"])
    top_politicians = _top(cov["by_politician"], 12)
    for p in top_politicians:
        p["party_color"] = PARTY_COLORS.get(p.get("party") or "", "#8b8fa3")
    return {
        "volume": cov["volume"],
        "top_politicians": top_politicians,
        "party_rows": party_rows,
        "top_topics": _top(cov["by_topic"], 10),
        "recent": cov["recent"],
    }


def render_mediji(env: Environment, db: sqlite3.Connection, atmina_dir: Path,
                  outlets: list[dict[str, Any]]) -> None:
    """Emit mediji.html (index) + mediji/<slug>.html per outlet.

    Mirrors src/render/parties.py::render_parties. Coverage is computed once for
    all outlets, then sliced per page."""
    cov = _fetch_coverage(db, outlets)
    feeds = _fetch_outlet_feeds(db, outlets)
    avg_share = _cross_outlet_avg_party_share(cov)
    party_slugs = _party_slug_map(db)

    index_rows = []
    for o in outlets:
        top_party = (_party_shares(cov[o["short_name"]]["by_party"]) or [{}])[0].get("party")
        volume = cov[o["short_name"]]["volume"]
        index_rows.append({
            **o,
            "volume": volume,
            "volume_phrase": _volume_phrase(volume, o.get("volume_label") or "raksti"),
            "top_party": top_party,
            "top_party_color": PARTY_COLORS.get(top_party or "", "#8b8fa3"),
        })

    _render_page(env, "mediji.html.j2", atmina_dir / "mediji.html", {
        "outlets": index_rows,
        "metrics": {"total": len(outlets),
                    "total_articles": sum(c["volume"] for c in cov.values())},
    })

    mediji_dir = atmina_dir / "mediji"
    mediji_dir.mkdir(parents=True, exist_ok=True)
    for o in outlets:
        detail = _outlet_detail(o, cov[o["short_name"]], avg_share, party_slugs)
        _render_page(env, "medijs.html.j2", mediji_dir / f"{o['slug']}.html", {
            "outlet": o,
            "feeds": feeds[o["short_name"]],
            "volume_phrase": _volume_phrase(detail["volume"], o.get("volume_label") or "raksti"),
            "volume_label": o.get("volume_label") or "raksti",
            **detail,
        })
