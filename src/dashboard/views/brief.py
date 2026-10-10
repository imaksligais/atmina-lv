"""Brief panel view helper — assembles today's daily-brief context.

The panel surfaces what `@brief-writer` wrote into `context_notes` for a
given date plus the latest hero image from `brief_images`. The render-side
template handles active / empty / loading / error states; this helper only
produces the data dict.
"""
from __future__ import annotations

import json
import re
from typing import Any

from src.db import get_db, today_lv

# Regex constants — defined at module level for clarity + cheap re-use.
_RE_FIRST_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_RE_LIST_PREFIX = re.compile(r"^[-*]\s+")
_RE_GALVENAIS_SPLIT = re.compile(r"##\s+Galvenais\s*", re.I)
_RE_CLAIM_REF = re.compile(r"#(\d{5})")


def get_brief_context(
    date: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Return context dict for the brief panel.

    Args:
        date: ISO date string (YYYY-MM-DD). Defaults to today's LV date.
        db_path: Optional override for tests.

    Returns:
        dict with keys: brief, lede, cited_claim_ids, image, wiki_path, atmina_url.
        `brief` and `image` are None when no row exists for the date.
    """
    if date is None:
        date = today_lv().isoformat()

    db = get_db(db_path) if db_path else get_db()
    row = db.execute(
        "SELECT id, topic, content, source, created_at, visual_brief_json "
        "FROM context_notes "
        "WHERE note_type = 'daily_brief' "
        "  AND topic LIKE '%' || ? || '%' "
        "ORDER BY id DESC LIMIT 1",
        (date,),
    ).fetchone()

    if row is None:
        return {
            "brief": None,
            "lede": "",
            "cited_claim_ids": [],
            "image": None,
            "wiki_path": f"wiki/dailies/{date}.md",
            "atmina_url": f"https://atmina.lv/blog/{date}.html",
        }

    content = row["content"]
    title_match = _RE_FIRST_H1.search(content)
    visual_brief = None
    if row["visual_brief_json"]:
        try:
            visual_brief = json.loads(row["visual_brief_json"])
        except (json.JSONDecodeError, TypeError):
            visual_brief = None

    image_row = db.execute(
        "SELECT id, image_path, approved, cost_usd, generated_at, error_message "
        "FROM brief_images WHERE note_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (row["id"],),
    ).fetchone()

    return {
        "brief": {
            "id": row["id"],
            "topic": row["topic"],
            "title": title_match.group(1) if title_match else None,
            "char_count": len(content),
            "created_at": row["created_at"],
            "source": row["source"],
            "visual_brief": visual_brief,
        },
        "lede": _extract_lede(content),
        "cited_claim_ids": [int(m) for m in _RE_CLAIM_REF.findall(content)],
        "image": _image_dict(image_row) if image_row else None,
        "wiki_path": f"wiki/dailies/{date}.md",
        "atmina_url": f"https://atmina.lv/blog/{date}.html",
    }


def _extract_lede(content: str) -> str:
    """First bullet/paragraph after `## Galvenais`.

    @brief-writer emits the first key point as a one-line bullet. We strip
    HTML comments and ``**`` bold markers, then return the first non-empty
    line with its list marker removed. Subsequent bullets stay in the
    full-content view; they should not bleed into the panel preview.
    """
    parts = _RE_GALVENAIS_SPLIT.split(content, maxsplit=1)
    if len(parts) < 2:
        return ""
    body = _RE_HTML_COMMENT.sub("", parts[1])
    body = _RE_BOLD.sub(r"\1", body)
    for line in body.split("\n"):
        line = line.strip()
        if line:
            return _RE_LIST_PREFIX.sub("", line)
    return ""


def _image_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "image_path": row["image_path"],
        "approved": row["approved"],  # 0=pending, 1=approved, 2=rejected
        "cost_usd": row["cost_usd"],
        "generated_at": row["generated_at"],
        "error_message": row["error_message"],
    }
