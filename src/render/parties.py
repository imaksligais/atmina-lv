"""Render the Partijas (parties) pages.

Phase F3c (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs:
- ``output/atmina/partijas.html`` — party index with member/claim/
  contradiction counts
- ``output/atmina/partijas/<short_name>.html`` — per-party detail page
  (~15 pages: JV, ZZS, NA, PRO, LPV, AS, ST, MMN, LA, …) with members,
  positions, votes, tensions, KNAB summary, last news + last X post

All leaf helpers needed (`_titlecase_party_name`, `_get_last_activity`,
`_format_tweet_time`, `_date_sort_key`) are already in ``_common``
from F3-prep + F3b — no new promotions required.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    ASSETS_DIR,
    PARTY_COLORS,
    _date_sort_key,
    _format_tweet_time,
    _get_last_activity,
    _party_page_slug,
    _render_page,
    _slugify,
    _titlecase_party_name,
)


def _fetch_parties_page(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch party data with aggregated stats."""
    try:
        party_rows = db.execute("SELECT * FROM parties ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []

    parties = []
    for r in party_rows:
        p = dict(r)
        p["display_name"] = _titlecase_party_name(p["name"])
        short = p["short_name"]
        p["member_count"] = db.execute("""
            SELECT COUNT(*) FROM tracked_politicians
            WHERE (party = ? OR party = ?) AND relationship_type NOT IN ('inactive', 'commentator')
        """, (p["name"], short)).fetchone()[0]
        p["claims_count"] = db.execute("""
            SELECT COUNT(*) FROM claims c
            JOIN tracked_politicians tp ON c.opponent_id = tp.id
            WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type NOT IN ('inactive', 'commentator')
              AND c.claim_type = 'position'
        """, (p["name"], short)).fetchone()[0]
        p["contradictions_count"] = db.execute("""
            SELECT COUNT(*) FROM contradictions ct
            JOIN tracked_politicians tp ON ct.opponent_id = tp.id
            WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type NOT IN ('inactive', 'commentator')
        """, (p["name"], short)).fetchone()[0]
        parties.append(p)
    return parties


def _fetch_party_detail(db: sqlite3.Connection, party: dict) -> dict[str, Any]:
    """Fetch full detail for one party: members, claims, votes, tensions, KNAB."""
    name = party["name"]
    short = party["short_name"]

    # Members. claims_count counts claim_type='position' only (rhetorical
    # stances), matching the "pozīcijas" label in the party detail template.
    member_rows = db.execute("""
        SELECT tp.id, tp.name, tp.role, tp.x_handle,
               (SELECT COUNT(*) FROM claims
                WHERE opponent_id = tp.id AND claim_type = 'position') as claims_count,
               (SELECT COUNT(*) FROM contradictions WHERE opponent_id = tp.id) as contradictions_count,
               (SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = tp.id) as votes_count
        FROM tracked_politicians tp
        WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY tp.name
    """, (name, short)).fetchall()
    members = []
    _photos = ASSETS_DIR / "photos"
    for r in member_rows:
        m = dict(r)
        m["slug"] = _slugify(m["name"])
        m["has_photo"] = (_photos / f"{m['slug']}.jpg").exists() if _photos.exists() else False
        m["last_activity"] = _get_last_activity(db, m["id"], m["name"])
        m["party_color"] = PARTY_COLORS.get(name) or PARTY_COLORS.get(short)
        members.append(m)

    # Positions (latest 100 first-person stances). Saeima vote rows for
    # this party are represented by the aggregate vote breakdown further
    # below, not by listing each vote row individually in the positions
    # feed. Phase D2 may add a separate "Balsojumi" listing section.
    claim_rows = db.execute("""
        SELECT c.*, tp.name AS politician_name
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type NOT IN ('inactive', 'commentator')
          AND c.claim_type = 'position'
        ORDER BY c.stated_at DESC LIMIT 100
    """, (name, short)).fetchall()
    claims = []
    for r in claim_rows:
        d = dict(r)
        d["slug"] = _slugify(d["politician_name"])
        claims.append(d)
    claims.sort(key=lambda c: _date_sort_key(c.get("stated_at") or ""), reverse=True)

    # Party election-program promises (claim_type='program_promise'), attributed
    # to the party via party_id. These are deliberately EXCLUDED from every
    # position feed above (and site-wide) by the `claim_type = 'position'`
    # filter, so they surface only in the party's "Programma" section. Grouped
    # by topic, highest-salience first within each topic.
    program_rows = db.execute("""
        SELECT c.topic, c.stance, c.source_url, c.stated_at, c.salience,
               tp.name AS politician_name
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE c.party_id = ? AND c.claim_type = 'program_promise'
        ORDER BY c.topic, c.salience DESC
    """, (party["id"],)).fetchall()
    _program_topics: dict[str, list[dict]] = {}
    for r in program_rows:
        _program_topics.setdefault(r["topic"], []).append(dict(r))
    program_by_topic = [
        {"topic": t, "promises": items} for t, items in sorted(_program_topics.items())
    ]
    program_count = len(program_rows)

    # Votes (party aggregate)
    vote_rows = db.execute("""
        SELECT sv.id, sv.vote_date as date, sv.summary, sv.topic,
               SUM(CASE WHEN siv.vote = 'Par' THEN 1 ELSE 0 END) as par,
               SUM(CASE WHEN siv.vote = 'Pret' THEN 1 ELSE 0 END) as pret,
               SUM(CASE WHEN siv.vote = 'Atturas' THEN 1 ELSE 0 END) as atturas
        FROM saeima_votes sv
        JOIN saeima_individual_votes siv ON sv.id = siv.vote_id
        JOIN tracked_politicians tp ON siv.politician_id = tp.id
        WHERE (tp.party = ? OR tp.party = ?)
        GROUP BY sv.id
        ORDER BY sv.vote_date DESC LIMIT 50
    """, (name, short)).fetchall()
    votes = [dict(r) for r in vote_rows]

    # Tensions
    tension_rows = db.execute("""
        SELECT pt.*, s.name AS source_name, s.party AS source_party,
               t.name AS target_name, t.party AS target_party
        FROM political_tensions pt
        JOIN tracked_politicians s ON pt.source_pid = s.id
        JOIN tracked_politicians t ON pt.target_pid = t.id
        WHERE (s.party IN (?, ?) OR t.party IN (?, ?))
          AND s.relationship_type NOT IN ('inactive', 'commentator')
          AND t.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY pt.created_at DESC LIMIT 30
    """, (name, short, name, short)).fetchall()
    tensions = [dict(r) for r in tension_rows]

    # KNAB summary
    knab_summary = None
    try:
        total = db.execute("SELECT COALESCE(SUM(amount_eur), 0) FROM knab_donations WHERE party = ?", (name,)).fetchone()[0]
        donors = db.execute("SELECT COUNT(DISTINCT donor_id) FROM knab_donations WHERE party = ?", (name,)).fetchone()[0]
        alerts = db.execute("SELECT COUNT(*) FROM knab_alerts WHERE party = ?", (name,)).fetchone()[0]
        if total > 0 or donors > 0:
            knab_summary = {"total_donations": total, "donor_count": donors, "alert_count": alerts}
    except sqlite3.OperationalError:
        pass

    claims_count = sum(m["claims_count"] for m in members)
    contradictions_count = sum(m["contradictions_count"] for m in members)
    votes_count = sum(m["votes_count"] for m in members)

    # Latest news article and X post for the party
    member_ids = [m["id"] for m in members]
    last_news = None
    last_x = None
    if member_ids:
        placeholders = ",".join("?" * len(member_ids))
        news_row = db.execute(f"""
            SELECT d.source_url, d.content, d.scraped_at, p.name
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            JOIN tracked_politicians p ON dp.politician_id = p.id
            WHERE dp.politician_id IN ({placeholders})
              AND d.platform NOT IN ('twitter', 'x')
            ORDER BY d.scraped_at DESC LIMIT 1
        """, member_ids).fetchone()
        if news_row:
            full_text = (news_row["content"] or "").replace("\n", " ").strip()
            last_news = {
                "url": news_row["source_url"],
                "title": full_text[:80] + ("..." if len(full_text) > 80 else ""),
                "title_full": full_text[:300],
                "date": (news_row["scraped_at"] or "")[:10],
                "politician": news_row["name"],
            }
        # Prefer published_at (actual tweet post time) over scraped_at. The
        # partija.html card displays `last_x.date[5:]` — with YYYY-MM-DD
        # HH:MM format this becomes "MM-DD HH:MM" showing both real date
        # and time, matching `_get_last_activity` (src/render/_common.py)
        # and `_fetch_x_data` (src/render/x.py post-F3f.2).
        x_row = db.execute(f"""
            SELECT d.source_url, d.content, d.published_at, d.scraped_at, p.name
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            JOIN tracked_politicians p ON dp.politician_id = p.id
            WHERE dp.politician_id IN ({placeholders})
              AND d.platform IN ('twitter', 'x')
              AND d.content NOT LIKE 'RT @%%'
            ORDER BY COALESCE(d.published_at, d.scraped_at) DESC LIMIT 1
        """, member_ids).fetchone()
        if x_row:
            full_text_x = (x_row["content"] or "").replace("\n", " ").strip()
            last_x = {
                "url": x_row["source_url"],
                "title": full_text_x[:80] + ("..." if len(full_text_x) > 80 else ""),
                "title_full": full_text_x[:300],
                "date": _format_tweet_time(x_row["published_at"], x_row["scraped_at"]),
                "politician": x_row["name"],
            }

    return {
        "members": members,
        "claims": claims,
        "program_by_topic": program_by_topic,
        "program_count": program_count,
        "votes": votes,
        "tensions": tensions,
        "knab_summary": knab_summary,
        "claims_count": claims_count,
        "contradictions_count": contradictions_count,
        "votes_count": votes_count,
        "last_news": last_news,
        "last_x": last_x,
    }


def render_parties(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    parties: list[dict[str, Any]],
) -> None:
    """Render partijas.html + per-party detail pages.

    Mirrors the inline block previously at ``src/generate.py`` lines
    2186-2207. Self-contained post-F3g.2: takes pre-fetched ``parties``
    list (orchestrator pre-fetches via ``_fetch_parties_page`` once and
    threads it to both this and ``_generate_sitemap``). No return value.
    """
    partijas_dir = atmina_dir / "partijas"
    partijas_dir.mkdir(parents=True, exist_ok=True)
    partijas_metrics = {
        "total": len(parties),
        "coalition": sum(1 for p in parties if p.get("coalition_status") == "coalition"),
        "opposition": sum(1 for p in parties if p.get("coalition_status") == "opposition"),
    }
    _render_page(env, "partijas.html.j2", atmina_dir / "partijas.html", {
        "parties": parties,
        "metrics": partijas_metrics,
    })

    for party in parties:
        detail = _fetch_party_detail(db, party)
        _render_page(env, "partija.html.j2", partijas_dir / f"{_party_page_slug(party['short_name'])}.html", {
            "party": party,
            **detail,
        })
