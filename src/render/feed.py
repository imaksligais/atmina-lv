"""RSS 2.0 plūsma ``feed.xml``: jaunākie pārskati un analīzes (arī «Atradumi»).

Plūsma ņem TOS PAŠUS sarakstus, ko lapas: ``blog_posts`` jau ir izfiltrēts pēc
``publish_approvals`` un ``analyses`` ir bez ``draft: true`` (T15), tāpēc
nepublicēts saturs plūsmā nenonāk pēc uzbūves.

``pubDate`` ir satura datums (pārskata subjekta diena, nedēļai — tās beigas),
nevis ``created_at``: labots pārskats lasītājam neuzlec kā jauns.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from src.render._common.constants import BASE_URL

logger = logging.getLogger(__name__)

FEED_LIMIT = 30
_RIGA = ZoneInfo("Europe/Riga")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _stamp(date_str: str, hour: int) -> datetime | None:
    try:
        day = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return day.replace(hour=hour, tzinfo=_RIGA)


def _feed_items(
    blog_posts: list[dict[str, Any]], analyses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    undated: list[str] = []
    for p in blog_posts:
        weekly = p["note_type"] == "weekly_brief"
        dates = _DATE_RE.findall(p["date"]) if weekly else []
        # Nedēļas pārskats iznāk pēc tās pašas dienas dienas pārskata (21 pret 20).
        when = _stamp(dates[-1] if dates else p["date_slug"], 21 if weekly else 20)
        url = f"{BASE_URL}/blog/{p['slug']}.html"
        if when is None:
            undated.append(url)
            continue
        items.append({
            "title": p.get("display_title") or p["title"],
            "url": url,
            "summary": p.get("preview") or "",
            "when": when,
        })
    for a in analyses:
        when = _stamp(a["date"], 12)
        url = f"{BASE_URL}/{a['url']}"
        if when is None:
            undated.append(url)
            continue
        items.append({
            "title": a["title"],
            "url": url,
            "summary": a.get("description") or "",
            "when": when,
        })
    if undated:
        logger.warning("feed.xml: %d lapas bez datuma izlaistas: %s", len(undated), undated)
    items.sort(key=lambda i: (i["when"], i["url"]), reverse=True)
    return items[:FEED_LIMIT]


def write_feed(
    atmina_dir: Path, blog_posts: list[dict[str, Any]], analyses: list[dict[str, Any]]
) -> int:
    """Uzraksta ``feed.xml``; atgriež ierakstu skaitu."""
    items = _feed_items(blog_posts, analyses)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        "  <title>atmina.lv</title>",
        f"  <link>{BASE_URL}/</link>",
        f'  <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>',
        "  <description>Dienas un nedēļas pārskati un analīzes par Latvijas politiķu "
        "pozīcijām un balsojumiem.</description>",
        "  <language>lv</language>",
    ]
    for i in items:
        lines += [
            "  <item>",
            f"    <title>{escape(i['title'])}</title>",
            f"    <link>{escape(i['url'])}</link>",
            f"    <guid>{escape(i['url'])}</guid>",
            f"    <pubDate>{format_datetime(i['when'])}</pubDate>",
            f"    <description>{escape(i['summary'])}</description>",
            "  </item>",
        ]
    lines += ["</channel>", "</rss>", ""]
    (atmina_dir / "feed.xml").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Generated feed.xml with %d items", len(items))
    return len(items)
