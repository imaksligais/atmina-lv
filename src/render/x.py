"""Render x.html — Twitter/X feed page (V1 with metrics + ticker).

Self-contained: re-fetches all data internally; no pass-through args.
Sub-page boundary: imports only from `src.render._common` and stdlib +
`src.db` (no peer sub-page imports — F4 leaf-vs-fan-out discipline).
"""

from __future__ import annotations

import re
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

from src.db import now_lv_dt
from src.render._common import (
    PARTY_COLORS,
    _format_tweet_time,
    _party_short_name,
    _render_page,
    _slugify,
)


def _fetch_x_data(db: sqlite3.Connection) -> dict[str, Any]:
    """Fetch X/Twitter posts and mentions separately."""
    handle_map = {
        r["opponent_id"]: r["handle"]
        for r in db.execute(
            "SELECT opponent_id, handle FROM social_accounts "
            "WHERE platform='twitter' AND active=1"
        ).fetchall()
    }
    # Posts (own tweets from tracked politicians)
    # LIMIT 1500 gives ~9 days of post history (and ~5 days for mentions),
    # which keeps the client-side persona/party/topic filter useful for
    # drilling into a specific politician's recent activity. Paint speed
    # is handled by content-visibility on .xv1-item, so the larger DOM
    # doesn't meaningfully slow initial render.
    # published_at is the actual tweet post time (UTC ISO from twikit);
    # scraped_at is only the fetch moment and collapses many tweets onto the
    # same HH:MM. Display prefers published_at — see _format_tweet_time below.
    post_rows = db.execute("""
        SELECT d.id, d.content, d.source_url, d.scraped_at, d.published_at,
               d.reply_count, d.retweet_count, d.favorite_count,
               p.id AS politician_id, p.name AS politician_name, p.party
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        JOIN tracked_politicians p ON dp.politician_id = p.id
        WHERE d.platform IN ('twitter', 'x')
          AND p.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
        LIMIT 1500
    """).fetchall()
    # Topic lookup: source_url → best-topic (highest salience, then most recent)
    topic_map = {}
    for r in db.execute("""
        SELECT c.source_url, c.topic
        FROM claims c
        WHERE c.source_url IS NOT NULL AND c.topic IS NOT NULL AND c.topic != ''
        ORDER BY COALESCE(c.salience, 0.5) DESC, c.created_at DESC
    """).fetchall():
        if r["source_url"] not in topic_map:
            topic_map[r["source_url"]] = r["topic"]

    posts = []
    for r in post_rows:
        d = dict(r)
        d["slug"] = _slugify(d["politician_name"])
        d["content_short"] = (d["content"] or "")[:280]
        d["date"] = _format_tweet_time(d.get("published_at"), d.get("scraped_at"))
        d["is_rt"] = (d["content"] or "").startswith("RT @")
        d["topic"] = topic_map.get(d["source_url"])
        d["party_color"] = PARTY_COLORS.get(d["party"], "#64748b")
        d["handle"] = handle_map.get(d["politician_id"])
        posts.append(d)

    # Mentions (others mentioning tracked politicians)
    mention_rows = db.execute("""
        SELECT d.id, d.content, d.source_url, d.scraped_at, d.published_at,
               d.reply_count, d.retweet_count, d.favorite_count,
               p.id AS target_id, p.name AS target_name, p.party AS target_party
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        JOIN tracked_politicians p ON dp.politician_id = p.id
        WHERE d.platform = 'x_mention' AND dp.role = 'mention_target'
          AND p.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
        LIMIT 1500
    """).fetchall()
    mentions = []
    target_handle_re = re.compile(r"@([A-Za-z0-9_]+)", re.IGNORECASE)
    for r in mention_rows:
        d = dict(r)
        d["target_slug"] = _slugify(d["target_name"])
        d["content_short"] = (d["content"] or "")[:280]
        d["date"] = _format_tweet_time(d.get("published_at"), d.get("scraped_at"))
        d["topic"] = topic_map.get(d["source_url"])
        d["party_color"] = PARTY_COLORS.get(d["target_party"], "#64748b")
        d["handle"] = handle_map.get(d["target_id"])
        # Extract mentioned_by: first @handle in content that isn't target's own handle
        target_slug = d["target_slug"].replace("-", "").lower()
        mentioned_by = None
        for match in target_handle_re.findall(d["content"] or ""):
            if match.lower().replace("_", "") != target_slug:
                mentioned_by = match
                break
        d["mentioned_by"] = mentioned_by
        mentions.append(d)

    # Combined persons list (from both posts and mentions). Sort key pushes
    # @handle-only names (demoted commentators @Heinrih5/@Kurmitis_ etc.) to
    # the bottom of the dropdown — they otherwise sort above 'A' because '@'
    # (0x40) < 'A' (0x41), placing low-relevance handles at the top of the
    # filter list. (False, ...) tuple sorts before (True, ...).
    all_persons = sorted(set(
        [p["politician_name"] for p in posts if p.get("politician_name")] +
        [m["target_name"] for m in mentions if m.get("target_name")]
    ), key=lambda n: (n.startswith("@"), n.lower()))
    all_parties = sorted(set(
        [p["party"] for p in posts if p.get("party")] +
        [m["target_party"] for m in mentions if m.get("target_party")]
    ))

    # V1: metrics tiles
    posts_total = db.execute(
        "SELECT COUNT(*) AS n FROM documents WHERE platform IN ('twitter','x')"
    ).fetchone()["n"]
    mentions_total = db.execute(
        "SELECT COUNT(*) AS n FROM documents WHERE platform = 'x_mention'"
    ).fetchone()["n"]
    cutoff_24h = (now_lv_dt() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    last_24h = db.execute(
        "SELECT COUNT(*) AS n FROM documents "
        "WHERE platform IN ('twitter','x','x_mention') "
        "AND scraped_at > ?",
        (cutoff_24h,)
    ).fetchone()["n"]
    metrics = {
        "posts_total": posts_total,
        "mentions_total": mentions_total,
        "last_24h": last_24h,
    }

    # V1: top mentioned politicians last 7 days (with trend vs prior 7d)
    this_week = {
        r["politician_id"]: r["n"]
        for r in db.execute("""
            SELECT dp.politician_id, COUNT(*) AS n
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            WHERE d.platform = 'x_mention'
              AND dp.role = 'mention_target'
              AND d.scraped_at > ?
            GROUP BY dp.politician_id
        """, ((now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),)).fetchall()
    }
    prev_week = {
        r["politician_id"]: r["n"]
        for r in db.execute("""
            SELECT dp.politician_id, COUNT(*) AS n
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            WHERE d.platform = 'x_mention'
              AND dp.role = 'mention_target'
              AND d.scraped_at > ?
              AND d.scraped_at <= ?
            GROUP BY dp.politician_id
        """, (
            (now_lv_dt() - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"),
            (now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        )).fetchall()
    }
    top_mentioned = []
    if this_week:
        placeholders = ",".join("?" * len(this_week))
        pid_meta = {
            r["id"]: (r["name"], r["party"])
            for r in db.execute(
                f"SELECT id, name, party FROM tracked_politicians "
                f"WHERE id IN ({placeholders}) "
                "AND relationship_type NOT IN ('journalist','influencer','neutral','inactive','commentator','organization')",
                list(this_week.keys())
            ).fetchall()
        }
        for pid, count in sorted(this_week.items(), key=lambda kv: -kv[1]):
            if pid not in pid_meta:
                continue
            name, party = pid_meta[pid]
            delta = count - prev_week.get(pid, 0)
            trend = f"+{delta}" if delta > 0 else f"{delta}" if delta < 0 else "0"
            top_mentioned.append({
                "name": name,
                "slug": _slugify(name),
                "party_short": _party_short_name(party) if party else "",
                "party_color": PARTY_COLORS.get(party, "#64748b"),
                "count": count,
                "trend": trend,
            })
            if len(top_mentioned) >= 8:
                break

    # V1: trending topics last 7 days — claims.topic counts on X documents
    cutoff_7d = (now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    topic_rows = db.execute("""
        SELECT c.topic,
               COUNT(DISTINCT d.id) AS n,
               GROUP_CONCAT(DISTINCT p.party) AS parties
        FROM claims c
        JOIN documents d ON d.source_url = c.source_url
        LEFT JOIN document_politicians dp
               ON dp.document_id = d.id AND dp.role = 'subject'
        LEFT JOIN tracked_politicians p ON p.id = dp.politician_id
        WHERE d.platform IN ('twitter','x','x_mention')
          AND d.scraped_at > ?
          AND c.topic IS NOT NULL
          AND c.topic != ''
        GROUP BY c.topic
        ORDER BY n DESC
        LIMIT 5
    """, (cutoff_7d,)).fetchall()
    trending_topics = []
    for r in topic_rows:
        parties = [p for p in (r["parties"] or "").split(",") if p]
        party_colors = []
        seen = set()
        for pty in parties:
            color = PARTY_COLORS.get(pty)
            if color and color not in seen:
                seen.add(color)
                party_colors.append(color)
            if len(party_colors) >= 5:
                break
        if not party_colors:
            party_colors = ["#64748b"]  # neutral gray fallback
        trending_topics.append({
            "topic": r["topic"],
            "mentions": r["n"],
            "party_colors": party_colors,
        })

    # Combined feed for V1 ticker: posts + mentions, unified shape, sorted newest-first
    feed = []
    for p in posts:
        feed.append({
            **p,
            "kind": "post",
            "persona": p["politician_name"],
            "party": p["party"] or "",
        })
    for m in mentions:
        feed.append({
            **m,
            "kind": "mention",
            "persona": m["target_name"],
            "party": m["target_party"] or "",
        })
    feed.sort(key=lambda x: x.get("date") or "", reverse=True)

    return {
        "posts": posts,
        "mentions": mentions,
        "politicians": all_persons,
        "parties": all_parties,
        "metrics": metrics,
        "top_mentioned": top_mentioned,
        "trending_topics": trending_topics,
        "feed": feed,
    }


def render_x(env, db: sqlite3.Connection, atmina_dir: Path) -> None:
    """Emit ``atmina_dir/x.html`` (Twitter/X feed page)."""
    x_data = _fetch_x_data(db)
    _render_page(env, "x.html.j2", atmina_dir / "x.html", {
        "posts": x_data["posts"],
        "mentions": x_data["mentions"],
        "parties": x_data["parties"],
        "politicians": x_data["politicians"],
        "metrics": x_data["metrics"],
        "top_mentioned": x_data["top_mentioned"],
        "trending_topics": x_data["trending_topics"],
        "feed": x_data["feed"],
    })
