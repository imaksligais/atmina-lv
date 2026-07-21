"""Render blog.html (index) + blog/<slug>.html (per-post pages).

Phase F3f.4 carve-out from ``src/generate.py``. Blog posts are
daily + weekly briefs (``context_notes.note_type IN ('daily_brief',
'weekly_brief')``); the index page lists them all and per-post pages
get rendered via the shared ``blog-post.html.j2`` template alongside
analyses + syntheses (F3f.5).

``_fetch_blog_posts`` derives slugs from the brief's *subject date*
(topic field → title H1 → created_at[:10] last-resort) — see commit
history of the prior ``src/generate.py:_fetch_blog_posts`` for the
date-resolution bug fix that drove this. Slug stability matters
because the orphan cleanup at the end of ``render_blog`` deletes any
``blog/<stale>.html`` whose slug isn't in the current ``blog_posts``
list.

``_fetch_context_notes`` lives here too even though ``context_notes``
is consumed only by the orchestrator-owned ``analizes.html`` index
render — it fetches from the same ``context_notes`` table, so
co-locating with ``_fetch_blog_posts`` keeps both queries in one
place. The orchestrator still calls ``_fetch_context_notes`` directly
via the re-export shim.

Sub-page boundary: imports only from ``src.render._common``,
``src.briefs`` (``strip_visual_brief_block``), and stdlib + extern
(markdown, jinja2).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment

from src.briefs import strip_visual_brief_block
from src.render._common import BASE_URL, _clean_context_note, _render_page

_WEEKLY_STATS_RE = re.compile(
    r"<!--\s*WEEKLY_STATS:\s*positions=(?P<positions>\d+)\s+votes=(?P<votes>\d+)\s+"
    r"contradictions=(?P<contradictions>\d+)\s+top_topic=(?P<top_topic>.+?)\s+"
    r"top_party=(?P<top_party>.+?)\s*-->"
)


def _parse_weekly_stats(content: str) -> dict[str, str] | None:
    """Extract the deterministic WEEKLY_STATS marker into a dict, or None."""
    m = _WEEKLY_STATS_RE.search(content)
    return m.groupdict() if m else None


def _weekly_stats_html(stats: dict[str, str]) -> str:
    """Render the stat strip as a raw-HTML block (passes through markdown).

    Inlined where the WEEKLY_STATS marker sits, under the "Nedēļā skaitļos"
    heading — so the heading is never left orphaned."""
    from html import escape
    cards = [
        (stats["positions"], "pozīcijas"),
        (stats["votes"], "balsojumi"),
        (stats["contradictions"], "pretrunas"),
        (stats["top_topic"], "top tēma"),
        (stats["top_party"], "aktīvākā partija"),
    ]
    items = "".join(
        f'<div class="weekly-stat-card"><b>{escape(str(v))}</b>'
        f'<span>{escape(label)}</span></div>'
        for v, label in cards
    )
    return f'<section class="weekly-stats">{items}</section>'


_SHORTENER_CANONICAL: dict[str, str] = {
    "pmo.ee": "tvnet.lv",
}

_MD_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://([^/)\s]+)[^)\s]*)\)")


def _rewrite_shortener_link_labels(md_text: str) -> str:
    """Replace `[shortener](url)` markdown links with `[canonical](url)`.

    Daily briefs emitted by @brief-writer sometimes label a link with the
    raw URL host (e.g. `[pmo.ee](https://pmo.ee/...)`) even though the
    shortener expands to a known publisher (tvnet.lv). Rewrite at render
    time so both historical and future briefs show the destination.
    """
    if not md_text:
        return md_text

    def _sub(match: re.Match[str]) -> str:
        label, url, host = match.group(1), match.group(2), match.group(3).lower()
        host = host.removeprefix("www.")
        canonical = _SHORTENER_CANONICAL.get(host)
        if canonical and label.strip().lower().removeprefix("www.") == host:
            return f"[{canonical}]({url})"
        return match.group(0)

    return _MD_LINK_RE.sub(_sub, md_text)


def _fetch_context_notes(db: sqlite3.Connection) -> list[dict[str, Any]]:
    # Only first-party context tendences. 'polling' is foreign to this surface;
    # JSON audit rows (note_type='asset', or legacy '{...}' content written
    # before the asset backfill) must never leak into the public UI. Filtering
    # in SQL before LIMIT means up to 20 *real* notes show — the old query
    # limited first, so JSON rows could push real notes out of the top 20.
    rows = db.execute("""
        SELECT * FROM context_notes
        WHERE note_type = 'context'
          AND TRIM(content) NOT LIKE '{%'
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    notes = []
    for r in rows:
        note = dict(r)
        note["content_html"] = _clean_context_note(note.get("content"))
        notes.append(note)
    return notes


# Footer count fields, defaulted to 0 for a brief whose subject date has no
# activity rows (so the template always sees a complete dict).
_EMPTY_FOOTER_COUNTS = {
    "doc_count": 0, "web": 0, "twitter": 0, "mentions": 0,
    "positions": 0, "votes": 0, "contradictions": 0,
}

# relationship_type values excluded from the daily-brief "pozīcijas" count —
# audience/non-first-party roles. Mirrors the prior per-brief subquery filter.
_FOOTER_POSITION_EXCLUDED_ROLES = (
    "journalist", "influencer", "neutral", "inactive", "commentator", "organization",
)


def _compute_brief_footers(db: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """Per-subject-date daily-brief footer counts, computed in one pass each.

    Replaces the previous 7-subquery-per-brief N+1 (each subquery wrapped
    ``date(...)`` so SQLite could not use an index; 54 briefs over the 33k-row
    documents + 514k-row claims tables cost ~12.6s). Here each metric is a
    single ``GROUP BY date(...)`` scan, then briefs dict-lookup their date.
    Returns ``{subject_date: {doc_count, web, twitter, mentions, positions,
    votes, contradictions}}``; a date with no activity is simply absent
    (callers ``.get(date, _EMPTY_FOOTER_COUNTS)``). Output is count-equivalent
    to the old per-brief block — locked by tests/test_blog_footer_batch.py and
    the existing TestBlogPostFooter suite.
    """
    docs: dict[tuple[str, str], int] = {}
    for d_, platform, cnt in db.execute(
        "SELECT date(scraped_at), platform, COUNT(*) FROM documents "
        "WHERE platform IN ('web','twitter','x_mention') GROUP BY date(scraped_at), platform"
    ).fetchall():
        docs[(d_, platform)] = cnt

    placeholders = ",".join("?" * len(_FOOTER_POSITION_EXCLUDED_ROLES))
    positions = {
        d_: cnt for d_, cnt in db.execute(
            "SELECT date(c.stated_at), COUNT(*) FROM claims c "
            "JOIN tracked_politicians p ON c.opponent_id = p.id "
            f"WHERE c.claim_type = 'position' AND p.relationship_type NOT IN ({placeholders}) "
            "GROUP BY date(c.stated_at)",
            _FOOTER_POSITION_EXCLUDED_ROLES,
        ).fetchall()
    }
    votes = {
        d_: cnt for d_, cnt in db.execute(
            "SELECT vote_date, COUNT(*) FROM saeima_votes GROUP BY vote_date"
        ).fetchall()
    }
    contras = {
        d_: cnt for d_, cnt in db.execute(
            "SELECT date(detected_at), COUNT(*) FROM contradictions GROUP BY date(detected_at)"
        ).fetchall()
    }

    dates = set(positions) | set(votes) | set(contras) | {d for d, _ in docs}
    out: dict[str, dict[str, int]] = {}
    for ds in dates:
        web = docs.get((ds, "web"), 0)
        twitter = docs.get((ds, "twitter"), 0)
        mentions = docs.get((ds, "x_mention"), 0)
        out[ds] = {
            "doc_count": web + twitter + mentions,
            "web": web,
            "twitter": twitter,
            "mentions": mentions,
            "positions": positions.get(ds, 0),
            "votes": votes.get(ds, 0),
            "contradictions": contras.get(ds, 0),
        }
    return out


def _fetch_blog_posts(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch daily/weekly briefs as blog posts."""
    rows = db.execute("""
        SELECT * FROM context_notes
        WHERE note_type IN ('daily_brief', 'weekly_brief')
        ORDER BY created_at DESC
    """).fetchall()

    posts = []
    _DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
    # Footer stats for ALL subject dates in one batch (replaces a per-brief
    # 7-subquery N+1 — see _compute_brief_footers). Daily briefs dict-look-up
    # their date below.
    _footers = _compute_brief_footers(db)
    for r in rows:
        d = dict(r)
        created = d.get("created_at") or ""
        type_label = "Dienas pārskats" if d.get("note_type") == "daily_brief" else "Nedēļas pārskats"
        # Use first line as title, rest as content
        content = _rewrite_shortener_link_labels(d.get("content") or "")
        lines = content.strip().split("\n", 1)
        title = lines[0].lstrip("#").strip() if lines else "Pārskats"
        body = lines[1].strip() if len(lines) > 1 else ""

        # Slug derivation: prefer subject date (from topic or H1 title), NOT
        # creation timestamp. `created_at` shifts when a brief is regenerated
        # on a later day; the blog URL must stay at the brief's subject date.
        # Priority: topic field → title H1 → created_at[:10] (last-resort
        # backward-compat fallback).
        date_str = ""
        topic_val = d.get("topic") or ""
        m = _DATE_RE.search(topic_val)
        if m:
            date_str = m.group(1)
        else:
            m = _DATE_RE.search(title)
            if m:
                date_str = m.group(1)
            elif created:
                date_str = created[:10]
            else:
                date_str = "unknown"

        # Smart lead extraction: find the first narrative paragraph in
        # ## Galvenais (the story paragraph @brief-writer writes), skipping
        # bullet lists, tables, HTML comments, and headings.
        import re as _re
        preview = ""
        first_bullet = ""
        galvenais_match = _re.search(r'## Galvenais\s*\n', body)
        if galvenais_match:
            after = body[galvenais_match.end():]
            # Stop at next ## section so we don't bleed into other content
            next_section = _re.search(r'\n##\s', after)
            if next_section:
                after = after[:next_section.start()]
            for para in _re.split(r'\n{2,}', after):
                para = para.strip()
                if not para or para.startswith(('|', '#', '<', '!')):
                    continue
                # Capture first bullet as fallback (bullets-only briefs)
                if para.startswith(('-', '*')) and not first_bullet:
                    first_bullet = _re.sub(r'^[-*]\s*', '', para)
                    first_bullet = _re.sub(r'\*\*([^*]+)\*\*', r'\1', first_bullet)
                    first_bullet = _re.sub(r'\n+', ' ', first_bullet).strip()
                    continue
                if para.startswith(('-', '*')):
                    continue
                # Found a narrative paragraph — clean and use it
                clean = _re.sub(r'\*\*([^*]+)\*\*', r'\1', para)
                clean = _re.sub(r'\n+', ' ', clean).strip()
                preview = clean[:300] + "..." if len(clean) > 300 else clean
                break
            if not preview and first_bullet:
                preview = first_bullet[:300] + "..." if len(first_bullet) > 300 else first_bullet

        # Fallback: strip markdown and take first 300 chars
        if not preview:
            clean_body = _re.sub(r'<!--.*?-->', '', body, flags=_re.DOTALL)
            clean_body = _re.sub(r'^#+\s*', '', clean_body, flags=_re.MULTILINE)
            clean_body = _re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_body)
            clean_body = _re.sub(r'\n+', ' ', clean_body).strip()
            preview = clean_body[:300] + "..." if len(clean_body) > 300 else clean_body

        # Featured image + visual brief headline (None if not yet generated)
        image_row = db.execute(
            "SELECT image_path FROM brief_images "
            "WHERE note_id = ? AND approved = 1 ORDER BY id DESC LIMIT 1",
            (d["id"],),
        ).fetchone()
        image_path = image_row["image_path"] if image_row else None
        image_filename = image_path.rsplit("/", 1)[-1] if image_path else None
        headline = None
        vb_json = d.get("visual_brief_json")
        if vb_json:
            try:
                vb = json.loads(vb_json)
                headline = vb.get("headline")
            except (ValueError, TypeError):
                pass

        import re as _re2
        display_title = headline or _re2.sub(
            r"\s*[—–-]\s*\d{4}-\d{2}-\d{2}\s*$", "", title
        ).strip()
        weekday_lv = ""
        try:
            from datetime import date as _date
            _days_lv = ("Pirmdiena", "Otrdiena", "Trešdiena", "Ceturtdiena",
                        "Piektdiena", "Sestdiena", "Svētdiena")
            weekday_lv = _days_lv[_date.fromisoformat(date_str).weekday()]
        except (ValueError, TypeError):
            pass

        # Footer metadata — render-time aprēķins no DB. Tikai dienas pārskatiem
        # (nedēļas pārskati aptver 7 dienas; day-scoped stats nav piemēroti).
        footer = None
        if d.get("note_type") == "daily_brief":
            # Formatē created_at uz "DD.MM.YYYY HH:MM"
            updated_display = ""
            if created:
                try:
                    ts = created.replace("T", " ")[:16]  # "2026-04-16 23:34"
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
                    updated_display = dt.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    updated_display = created[:16] if created else ""

            footer = {
                **_footers.get(date_str, _EMPTY_FOOTER_COUNTS),
                "updated": updated_display,
            }

        # Weekly briefs prefix their slug to avoid collision with a daily
        # brief for the same subject date — both derive date_str from
        # topic/title and would otherwise clobber each other under the
        # dedup pass.
        slug = (f"nedela-{date_str}"
                if d.get("note_type") == "weekly_brief"
                else date_str)

        # Weekly briefs display a "start — end" range on cards/headers
        # (derived from the H1 title "Nedēļas analīze — START līdz END").
        # Daily briefs just use the single date_str.
        display_date = date_str
        if d.get("note_type") == "weekly_brief":
            dates_in_title = _DATE_RE.findall(title)
            if len(dates_in_title) >= 2:
                display_date = f"{dates_in_title[0]} — {dates_in_title[-1]}"

        posts.append({
            "id": d["id"],
            "slug": slug,
            "date": display_date,
            "date_slug": date_str,
            "created_at": created,
            "weekday": weekday_lv,
            "title": title,
            "display_title": display_title,
            "type_label": type_label,
            "note_type": d.get("note_type"),
            "preview": preview,
            "content": content,
            "image_path": image_path,
            "image_filename": image_filename,
            "headline": headline,
            "footer": footer,
        })
    # Deduplicate by slug — keep the newest (by created_at). Two briefs for
    # the same day (e.g. initial "pārskats" + next-day expanded "analīze")
    # both resolve to the same date_str slug; without dedup the render loop
    # writes both sequentially to the same file and the older version wins.
    # Posts are already ordered DESC by created_at, so first occurrence wins.
    seen_slugs: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for p in posts:
        if p["slug"] in seen_slugs:
            continue
        seen_slugs.add(p["slug"])
        deduped.append(p)
    return deduped


def render_blog(
    env: Environment,
    atmina_dir: Path,
    blog_posts: list[dict[str, Any]],
) -> None:
    """Emit ``atmina_dir/blog.html`` (index) + ``atmina_dir/blog/<slug>.html``
    per post.

    Mirrors the inline blocks previously at ``src/generate.py`` lines
    794-829: blog index render + per-post loop with prev/next navigation
    + orphan cleanup. Orphan cleanup deletes any
    ``blog/<stale>.html`` whose slug is not in the current
    ``blog_posts`` list (catches stale files from earlier runs where a
    brief's date_str resolved differently).
    """
    blog_dir = atmina_dir / "blog"
    blog_dir.mkdir(parents=True, exist_ok=True)

    # Blog index (keep for backwards compat — old URLs still work)
    _render_page(env, "blog.html.j2", atmina_dir / "blog.html", {
        "posts": blog_posts,
    })

    # Individual blog posts (with prev/next navigation)
    for i, post in enumerate(blog_posts):
        content = strip_visual_brief_block(post["content"])
        # Strip first heading — it's already shown in the template as <h1>
        lines = content.split("\n")
        if lines and lines[0].startswith("# "):
            content = "\n".join(lines[1:]).lstrip()
        is_weekly = post.get("note_type") == "weekly_brief"
        weekly_stats = _parse_weekly_stats(content) if is_weekly else None
        # Replace the invisible WEEKLY_STATS marker with the stat-card HTML so
        # the cards render INLINE under their "## Nedēļā skaitļos" heading,
        # instead of floating at the top and leaving the heading orphaned.
        if weekly_stats:
            cards = _weekly_stats_html(weekly_stats)
            content = _WEEKLY_STATS_RE.sub(lambda _m, c=cards: c, content)
        md_renderer = markdown.Markdown(extensions=["tables", "fenced_code"])
        content_html = md_renderer.convert(content)
        prev_post = blog_posts[i + 1] if i + 1 < len(blog_posts) else None
        next_post = blog_posts[i - 1] if i > 0 else None
        template_name = "_weekly_body.html.j2" if is_weekly else "blog-post.html.j2"
        _render_page(env, template_name, blog_dir / f"{post['slug']}.html", {
            "post": post,
            "content_html": content_html,
            "weekly_stats": weekly_stats,
            "prev_post": prev_post,
            "next_post": next_post,
            "back_href": "../analizes.html",
            "BASE_URL": BASE_URL,
        })

    # Clean up orphan blog HTML files (slugs no longer produced by
    # _fetch_blog_posts — e.g. leftover from earlier runs where a brief's
    # date_str resolved differently). Without this, stale files keep getting
    # deployed.
    current_slugs = {p["slug"] for p in blog_posts}
    for stale in blog_dir.glob("*.html"):
        if stale.stem not in current_slugs:
            stale.unlink()
