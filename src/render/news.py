"""Render the Ziņas (news) page.

Phase F3d (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Output:
- ``output/atmina/zinas.html`` — web-article feed (platform='web' docs)
  with ONE card per article; each card carries a ``persons`` list
  (politicians alphabetical, then commentators flagged
  ``is_commentator``) plus topic facets.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import _render_page, _slugify


def _fetch_news(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch web articles for the Ziņas page — ONE entry per article.

    Rindas nāk pa (dokuments, politiķis) pārim; salokām vienā dictā ar
    ``persons`` sarakstu. Pāravotu republikācijas (viens kanoniskais
    virsraksts, strip+lower) apvieno personu + tēmu ūnijā jaunākajā
    eksemplārā. Dokumenti, kam VISI linki ir inactive, paliek tikai tad,
    ja tiem ir claims (un renderējas bez personu tagiem).
    """
    rows = db.execute("""
        SELECT d.id, d.source_url, d.source_domain, d.published_at, d.scraped_at,
               d.title, tp.name AS politician_name, tp.party, tp.relationship_type
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        JOIN tracked_politicians tp ON dp.politician_id = tp.id
        WHERE d.platform = 'web' AND d.word_count > 30
              AND d.source_domain != 'rus.delfi.lv'
              AND (tp.party IS NOT NULL
                   OR tp.relationship_type IN ('inactive', 'journalist', 'influencer', 'neutral', 'commentator'))
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC, d.id, tp.name
    """).fetchall()

    # Divi kopvaicājumi bijušo per-dokumenta vaicājumu vietā (N+1 fix).
    topics_by_doc: dict[int, list[str]] = {}
    for doc_id, topic in db.execute(
        "SELECT DISTINCT document_id, topic FROM claims "
        "WHERE document_id IS NOT NULL AND topic IS NOT NULL "
        "ORDER BY document_id, topic"
    ).fetchall():
        topics_by_doc.setdefault(doc_id, []).append(topic)
    docs_with_claims = {
        r[0] for r in db.execute(
            "SELECT DISTINCT document_id FROM claims WHERE document_id IS NOT NULL"
        ).fetchall()
    }

    docs: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for r in rows:
        d = dict(r)
        doc = docs.get(d["id"])
        if doc is None:
            # Headline: DB title; pēdējais fallback — URL slug (rets gadījums,
            # kas izbēdzis gan forward-fix, gan backfill).
            headline = (d.get("title") or "").strip()
            if not headline:
                headline = d["source_url"].split("/")[-1].replace("-", " ").replace(".htm", "")[:100]
            doc = {
                "id": d["id"],
                "source_url": d["source_url"],
                "source_domain": d["source_domain"],
                "published_at": d["published_at"],
                "scraped_at": d["scraped_at"],
                "headline": headline,
                "date": (d["published_at"] or "")[:10],
                "persons": [],
                "topics_list": topics_by_doc.get(d["id"], []),
                "only_inactive": True,
            }
            docs[d["id"]] = doc
            order.append(d["id"])
        rel = d.get("relationship_type")
        if rel == "inactive":
            continue  # dokuments var palikt (claims gate zemāk), bet bez taga
        doc["only_inactive"] = False
        if all(p["name"] != d["politician_name"] for p in doc["persons"]):
            doc["persons"].append({
                "name": d["politician_name"],
                "slug": _slugify(d["politician_name"]),
                "party": d["party"],
                "is_commentator": rel in ("journalist", "influencer", "neutral", "commentator"),
            })

    # Republikāciju merge: viens kanoniskais virsraksts = viena kartīte;
    # personas + tēmas ūnijā paliek jaunākajā (pirmajā, jo ORDER BY DESC).
    seen_titles: dict[str, dict[str, Any]] = {}
    deduped: list[dict[str, Any]] = []
    for doc_id in order:
        doc = docs[doc_id]
        if doc["only_inactive"] and doc["id"] not in docs_with_claims:
            continue
        canonical = doc["headline"].strip().lower()
        if not canonical:
            continue
        kept = seen_titles.get(canonical)
        if kept is None:
            seen_titles[canonical] = doc
            deduped.append(doc)
        else:
            have = {p["name"] for p in kept["persons"]}
            kept["persons"].extend(p for p in doc["persons"] if p["name"] not in have)
            kept["topics_list"] = sorted(set(kept["topics_list"]) | set(doc["topics_list"]))

    for doc in deduped:
        doc["persons"].sort(key=lambda p: (p["is_commentator"], p["name"]))
        doc["persons_str"] = "|".join(p["name"] for p in doc["persons"])
        doc["parties_str"] = "|".join(sorted({
            p["party"] for p in doc["persons"] if p["party"] and not p["is_commentator"]
        }))
        doc["topics_str"] = ",".join(doc["topics_list"])
        doc["has_commentator"] = any(p["is_commentator"] for p in doc["persons"])
    return deduped


def render_news(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
) -> None:
    """Render zinas.html.

    Mirrors the inline block previously at ``src/generate.py`` lines
    2195-2236. Self-contained: re-fetches news + computes facet sets
    + emits one HTML page.
    """
    news = _fetch_news(db)
    news_sources = sorted(set(n["source_domain"] for n in news if n.get("source_domain")))
    news_topics = sorted(set(t for n in news for t in n["topics_list"]))
    real_parties = sorted(set(
        p["party"] for n in news for p in n["persons"]
        if p["party"] and not p["is_commentator"]
    ))
    all_persons = sorted(set(p["name"] for n in news for p in n["persons"]))
    week_cutoff = (date.today() - timedelta(days=7)).isoformat()
    last_week = sum(
        1 for n in news
        if ((n.get("published_at") or n.get("scraped_at") or "") >= week_cutoff)
    )
    zinas_metrics = {
        "total": len(news),
        "last_week": last_week,
        "sources": len(news_sources),
    }
    _render_page(env, "zinas.html.j2", atmina_dir / "zinas.html", {
        "news": news,
        "sources": news_sources,
        "topics": news_topics,
        "mentioned_parties": real_parties,
        "mentioned_persons": all_persons,
        "metrics": zinas_metrics,
    })
