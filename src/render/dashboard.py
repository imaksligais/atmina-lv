"""Render index.html (homepage hero) + analizes.html (combined index).

Phase F3f.1 carve-out from ``src/generate.py``. The homepage `index.html`
shows the hero with stats + sparklines + live ticker + trends; the
combined `analizes.html` index lists analyses + syntheses + blog posts
+ trends + context_notes side-by-side.

Both pages share orchestrator-fetched data (``stats``, ``contradictions``,
``votes``, ``blog_posts``, ``syntheses``, ``analyses``, ``trends_data``,
``context_notes``) — pre-fetching once and threading through avoids
duplicate DB work. ``render_dashboard`` takes the data via 9
positional args (matching peer F3 sub-page pass-through pattern); the
list is long but each value is meaningful at the call site.

Sub-page boundary: imports only from ``src.render._common``,
``src.db`` (``today_lv``, ``CLEAN_START_DATE``), and stdlib + extern
(``markupsafe.Markup``, ``jinja2.Environment``).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment
from markupsafe import Markup

from src.db import CLEAN_START_DATE, today_lv
from src.render._common import (
    BASE_URL,
    PARTY_COLORS,
    TOPIC_COLORS,
    _render_page,
    _slugify,
    hero_excerpt,
)
from src.render.focus import _hot_topic, _quote_of_day, assemble_focus, hero_feed
from src.render.tensions import _fetch_tensions

# Brand-palette fallback for topics/parties absent from the color maps
# (unknown canonical topics, JKP + other parties without a PARTY_COLORS
# entry). Same neutral slate used across render (rankings, mediji, personas).
_TRENDS_FALLBACK_COLOR = "#8b8fa3"


def _fetch_stats(db: sqlite3.Connection) -> dict[str, int]:
    """Dashboard stats. ``claims`` is now restricted to position-type rows
    (media/X first-person stances). The old definition counted Saeima
    voting records too, which made the headline metric misleading — 88%
    of "claims" were legislative votes, not rhetorical positions.
    """
    cutoff_7d = (today_lv() - timedelta(days=7)).strftime("%Y-%m-%d")
    return {
        "politicians": db.execute(
            "SELECT COUNT(*) FROM tracked_politicians "
            "WHERE relationship_type NOT IN ('inactive', 'commentator')"
        ).fetchone()[0],
        "parties": db.execute("SELECT COUNT(*) FROM parties").fetchone()[0],
        "politicians_active": db.execute(
            "SELECT COUNT(DISTINCT opponent_id) FROM claims WHERE claim_type = 'position'"
        ).fetchone()[0],
        "claims": db.execute(
            "SELECT COUNT(*) FROM claims WHERE claim_type = 'position'"
        ).fetchone()[0],
        "saeima_claims": db.execute(
            "SELECT COUNT(*) FROM claims WHERE claim_type = 'saeima_vote'"
        ).fetchone()[0],
        "contradictions": db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0],
        "votes": db.execute("SELECT COUNT(*) FROM saeima_votes").fetchone()[0],
        "claims_7d": db.execute(
            "SELECT COUNT(*) FROM claims WHERE stated_at >= ? AND claim_type = 'position'",
            (cutoff_7d,),
        ).fetchone()[0],
        "votes_7d": db.execute("SELECT COUNT(*) FROM saeima_votes WHERE vote_date >= ?", (cutoff_7d,)).fetchone()[0],
        "tensions": db.execute("SELECT COUNT(*) FROM political_tensions").fetchone()[0],
        "documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
    }


def week_fact(count: int, last_date: str | None, label: str) -> dict[str, str] | None:
    """0-vērtības vietā cilvēcīgs fakts ("Saeima brīvlaikā" sajūtas novēršana).

    ``label`` ir pilna etiķetes frāze ar dzimtei atbilstošu locījumu
    (``"pēdējie balsojumi"`` / ``"pēdējās pretrunas"``) — tā saskan ar
    lietvārda dzimti, ko fiksēts prefikss nespētu.

    Atgriež ``{"label", "date"}``, lai strip stat saglabātu to pašu
    divu-līniju anatomiju kā skaitliskie stati (vērtība + etiķete), nevis
    vienu pelēku vidēja-izmēra rindu. ``None``, ja skaitītājs > 0 (tad
    rāda parasto ciparu) vai nav datuma.
    """
    if count or not last_date:
        return None
    d = f"{last_date[8:10]}.{last_date[5:7]}.{last_date[:4]}" if len(last_date) >= 10 else last_date
    return {"label": label, "date": d}


def _sparkline_svg(series: list[int], width: int = 140, height: int = 28, color: str = "#90A4AE") -> Markup:
    if not series or len(series) < 2:
        return Markup("")
    mx = max(series) or 1
    step = width / (len(series) - 1)
    pts = [(i * step, height - (v / mx) * (height - 3) - 1.5) for i, v in enumerate(series)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = "M 0," + f"{height}" + " L " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L {width},{height} Z"
    last_x, last_y = pts[-1]
    svg = (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
        f'<path d="{area}" fill="{color}" fill-opacity="0.14"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" '
        f'stroke-linejoin="round" points="{line}"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.2" fill="{color}"/>'
        f"</svg>"
    )
    return Markup(svg)


def _fetch_hero_v2_data(db: sqlite3.Connection) -> dict[str, Any]:
    """28-day sparklines + live ticker rows for the hero v2 test layout."""
    from datetime import datetime, timedelta
    today = today_lv()
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(27, -1, -1)]
    start = days[0]

    def series(sql: str, params: tuple = ()) -> list[int]:
        rows = db.execute(sql, params).fetchall()
        by_day = {r["d"]: r["n"] for r in rows}
        return [by_day.get(d, 0) for d in days]

    positions = series(
        "SELECT date(created_at) d, COUNT(*) n FROM claims "
        "WHERE claim_type='position' AND date(created_at) >= ? GROUP BY d",
        (start,),
    )
    contradictions = series(
        "SELECT date(detected_at) d, COUNT(*) n FROM contradictions "
        "WHERE date(detected_at) >= ? GROUP BY d",
        (start,),
    )
    active = series(
        "SELECT date(created_at) d, COUNT(DISTINCT opponent_id) n FROM claims "
        "WHERE claim_type='position' AND date(created_at) >= ? GROUP BY d",
        (start,),
    )

    contradictions_7d = sum(contradictions[-7:])

    # Ticker — 6 most recent claims
    rows = db.execute(
        "SELECT c.id, c.topic, c.stance, c.source_url, c.stated_at, c.created_at, "
        "tp.name, tp.party "
        "FROM claims c JOIN tracked_politicians tp ON c.opponent_id=tp.id "
        "WHERE c.claim_type='position' "
        "ORDER BY COALESCE(c.stated_at, c.created_at) DESC LIMIT 6"
    ).fetchall()
    now = datetime.now()
    ticker = []
    for r in rows:
        d = dict(r)
        d["slug"] = _slugify(d["name"])
        d["party_color"] = PARTY_COLORS.get(d.get("party") or "") or "#8b8fa3"
        stated_raw = d.get("stated_at") or ""
        created_raw = d.get("created_at") or ""
        # Prefer stated_at only if it has real time-of-day; otherwise created_at is more precise
        stated_is_midnight = stated_raw.endswith("00:00:00") or len(stated_raw) == 10
        ts_raw = created_raw if (stated_is_midnight and created_raw) else (stated_raw or created_raw)
        rel = ""
        try:
            ts = datetime.strptime(ts_raw[:10], "%Y-%m-%d") if len(ts_raw) == 10 else datetime.strptime(ts_raw[:19], "%Y-%m-%d %H:%M:%S")
            delta = now - ts
            if delta.days >= 1:
                rel = f"pirms {delta.days}d"
            elif delta.seconds // 3600 >= 1:
                rel = f"pirms {delta.seconds//3600}h"
            else:
                rel = f"pirms {max(1, delta.seconds//60)}m"
        except Exception:
            pass
        d["rel_time"] = rel
        stance = (d.get("stance") or "").strip()
        if len(stance) > 95:
            stance = stance[:93].rsplit(" ", 1)[0] + "…"
        d["stance_short"] = stance
        ticker.append(d)

    accent = "#90A4AE"
    return {
        "spark_positions": _sparkline_svg(positions, color=accent),
        "spark_contradictions": _sparkline_svg(contradictions, color=accent),
        "spark_active": _sparkline_svg(active, color=accent),
        "contradictions_7d": contradictions_7d,
        "hero_ticker": ticker,
    }


def _fetch_trends_data(db: sqlite3.Connection) -> dict[str, Any]:
    """Chart data: topics, politicians, timeline for last 14 days.

    All queries are restricted to claim_type='position' so the trend
    visualization reflects rhetorical activity rather than the spiky
    pattern of weekly Saeima vote batches.

    Window narrowed from 30d → 14d and additionally clamped to CLEAN_START_DATE
    so test-era (pre-2026-04-05) MMN-biased ingestion is excluded from the
    public trend charts.
    """
    window_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    cutoff = max(window_cutoff, CLEAN_START_DATE)

    # Topics by position claims
    topic_rows = db.execute("""
        SELECT topic, COUNT(*) AS cnt
        FROM claims WHERE stated_at >= ? AND topic IS NOT NULL
          AND claim_type = 'position'
        GROUP BY topic ORDER BY cnt DESC LIMIT 15
    """, (cutoff,)).fetchall()

    # Most active politicians (positions only)
    pol_rows = db.execute("""
        SELECT tp.name, tp.party, COUNT(*) AS cnt
        FROM claims c JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.stated_at >= ? AND c.claim_type = 'position'
          AND tp.relationship_type NOT IN ('inactive', 'commentator')
        GROUP BY c.opponent_id ORDER BY cnt DESC LIMIT 15
    """, (cutoff,)).fetchall()

    # Timeline: daily position counts
    timeline_claims = db.execute("""
        SELECT DATE(stated_at) AS day, COUNT(*) AS cnt
        FROM claims WHERE stated_at >= ? AND claim_type = 'position'
        GROUP BY day ORDER BY day
    """, (cutoff,)).fetchall()

    timeline_docs = db.execute("""
        SELECT DATE(scraped_at) AS day, COUNT(*) AS cnt
        FROM documents WHERE scraped_at >= ?
        GROUP BY day ORDER BY day
    """, (cutoff,)).fetchall()

    # Merge timelines into aligned arrays
    all_days = sorted(set(
        [r["day"] for r in timeline_claims if r["day"]] +
        [r["day"] for r in timeline_docs if r["day"]]
    ))
    claims_by_day = {r["day"]: r["cnt"] for r in timeline_claims if r["day"]}
    docs_by_day = {r["day"]: r["cnt"] for r in timeline_docs if r["day"]}

    return {
        "topics": {
            "labels": [r["topic"] for r in topic_rows],
            "values": [r["cnt"] for r in topic_rows],
            # Stabiņu krāsas no kanoniskās tēmu paletes; nezināmas tēmas →
            # neitrālais fallback. Krāsu masīvs paralēls ``labels``.
            "colors": [
                TOPIC_COLORS.get(r["topic"], _TRENDS_FALLBACK_COLOR)
                for r in topic_rows
            ],
        },
        "politicians": {
            "labels": [r["name"] for r in pol_rows],
            "values": [r["cnt"] for r in pol_rows],
            "slugs": [_slugify(r["name"]) for r in pol_rows],
            # Katra politiķa stabiņš savas partijas krāsā; ``tp.party`` var būt
            # pilnā vai īsā formā — tiešā .get() sakrīt ar rankings.py praksi
            # (pilnvārdi + "MMN" ir atslēgas; pārējie → fallback).
            "colors": [
                PARTY_COLORS.get(r["party"] or "", _TRENDS_FALLBACK_COLOR)
                for r in pol_rows
            ],
        },
        "timeline": {
            "labels": all_days,
            "claims": [claims_by_day.get(d, 0) for d in all_days],
            "documents": [docs_by_day.get(d, 0) for d in all_days],
        },
    }


def render_dashboard(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    stats: dict[str, int],
    contradictions: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    blog_posts: list[dict[str, Any]],
    syntheses: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
    trends_data: dict[str, Any],
    context_notes: list[dict[str, Any]],
    days_until: int,
    rankings: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    """Emit ``atmina_dir/index.html`` (homepage hero) + ``analizes.html``
    (combined index for analyses + syntheses + blog posts + trends).

    Mirrors the inline blocks previously at ``src/generate.py`` lines
    498-511 (index) + 553-566 (analizes combined index). Long arg list
    matches peer F3 sub-page pass-through pattern (orchestrator pre-fetches
    shared data once); F3g may bundle into a context object once
    ``generate_public_site`` lifts to ``src/render/__init__.py``.

    ``rankings`` (from ``src.render.rankings.fetch_rankings``) drives the
    homepage "Atklāj" discovery block; ``None`` renders the page without it.
    """
    # 1. Index (hero with metrics + sparklines + live ticker)
    hero_data = _fetch_hero_v2_data(db)

    # "Šonedēļ" strip — factual 7-day recap reusing already-fetched counts
    # + a link to the most recent weekly brief (return-habit hook).
    latest_weekly = next(
        (p for p in blog_posts if p.get("note_type") == "weekly_brief"), None
    )
    week_summary = {
        "claims_7d": stats.get("claims_7d", 0),
        "votes_7d": stats.get("votes_7d", 0),
        "contradictions_7d": hero_data.get("contradictions_7d", 0),
        "votes_fact": week_fact(
            stats.get("votes_7d", 0),
            (votes[0].get("vote_date") if votes else None),
            "pēdējie balsojumi",
        ),
        "contradictions_fact": week_fact(
            hero_data.get("contradictions_7d", 0),
            (contradictions[0].get("new_date") if contradictions else None),
            "pēdējās pretrunas",
        ),
        "weekly_brief": latest_weekly,
    }

    # Hero cards: build smart excerpts at sentence/clause boundaries instead
    # of the template's old |truncate(120), which chopped quotes mid-word
    # ("Esmu…", "…un tikai…"). Copy each row so we never mutate the shared
    # `contradictions` list that the pretrunas page and the focus composite
    # below both reuse.
    hero_cards = []
    for c in contradictions[:5]:
        c = dict(c)
        c["old_excerpt"], c["old_is_quote"] = hero_excerpt(c.get("old_quote"), c.get("old_stance"))
        c["new_excerpt"], c["new_is_quote"] = hero_excerpt(c.get("new_quote"), c.get("new_stance"))
        hero_cards.append(c)

    # Uzmanības centrā composite (spec 2026-07-07) — visi dati re-compute
    # katrā renderā; contradictions = jau padotais enriched saraksts.
    focus = assemble_focus(
        _hot_topic(db), contradictions, _fetch_tensions(db), _quote_of_day(db)
    )

    # Hero karuselis: jauktais saturs (spec 2026-07-07) — pretrunas no
    # hero_cards, balsojumi no jau nofetčotā votes, pozīcijas dedupē pret
    # kompozīta citātiem.
    hero_items = hero_feed(db, hero_cards, votes, focus)

    _render_page(env, "index.html.j2", atmina_dir / "index.html", {
        "stats": stats,
        "days_until_election": days_until,
        "focus": focus,
        "hero_items": hero_items,
        "rankings": rankings or {},
        "week_summary": week_summary,
        "recent_votes": votes[:5],
        "recent_briefs": blog_posts[:3],
        "latest_synthesis": syntheses[0] if syntheses else None,
        "latest_analysis": analyses[0] if analyses else None,
        "trends_data": trends_data,
        "BASE_URL": BASE_URL,
        **hero_data,
    })

    # 6. Analīzes (tematiskās + dienas pārskati + tendences apvienoti)
    analizes_metrics = {
        "daily": sum(1 for p in blog_posts if p.get("note_type") == "daily_brief"),
        "weekly": sum(1 for p in blog_posts if p.get("note_type") == "weekly_brief"),
        "tematic": len(analyses),
        "sintezes": len(syntheses),
    }
    _render_page(env, "analizes.html.j2", atmina_dir / "analizes.html", {
        "analyses": analyses,
        "syntheses": syntheses,
        "posts": blog_posts,
        "trends_data": trends_data,
        "context_notes": context_notes,
        "metrics": analizes_metrics,
    })
