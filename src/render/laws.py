"""Render the Likumi (base-law) pages.

Phase F3e (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common``,
``src.saeima`` (leaf), and stdlib + ``markdown`` — no peer-module
dependencies on bills/votes.

Outputs:
- ``output/atmina/likumi.html`` — sortable index of base laws with
  attached likumprojekti counts + topic + last activity timestamp.
- ``output/atmina/likumi/<slug>.html`` — per-law page rendered from
  ``wiki/laws/<slug>.md`` (skipping the ``likumi.md`` index file)
  enriched with the SQL list of bills that touch the same base_law_slug.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment

from src.render._common import _bill_slug, _render_page, _sanitize_html
from src.saeima import LAW_TITLE_RE

logger = logging.getLogger(__name__)


_LAW_LIKUMI_LV_RE = re.compile(r"^\*\*Likumi\.lv:\*\*\s+(\S+)\s*$", re.MULTILINE)
_LAW_BODY_STRIP_RE = re.compile(
    r"^(#\s+.+?\s*$|\*\*(?:Pieņemts|Likumi\.lv|Saistītie balsojumi):\*\*\s*.*?\s*$)\n?",
    re.MULTILINE,
)


def _fetch_law_pages(db: sqlite3.Connection, laws_dir: Path = Path("wiki/laws")) -> list[dict[str, Any]]:
    """Iterē wiki/laws/*.md (skip likumi.md), parse, render markdown → HTML.

    Returns list ar slug, title, likumi_lv_url, body_html, bills_count, bills.
    """
    if not laws_dir.exists():
        return []

    pages = []
    for md_file in sorted(laws_dir.glob("*.md")):
        if md_file.name == "likumi.md":
            continue
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")

        title_m = LAW_TITLE_RE.search(content)
        title = title_m.group(1) if title_m else slug.replace("-", " ").title()

        url_m = _LAW_LIKUMI_LV_RE.search(content)
        likumi_lv_url = url_m.group(1) if url_m else None

        # Strip H1 + metadata lines from body so they don't duplicate the pagehead
        body_md = _LAW_BODY_STRIP_RE.sub("", content)
        # Markdown → HTML, sanitize
        body_html = _sanitize_html(markdown.markdown(body_md, extensions=["tables"]))

        # Bills count + summary list
        bills = []
        for r in db.execute("""
            SELECT id, document_nr, title, current_stage, current_status, last_updated_at
            FROM saeima_bills
            WHERE base_law_slug = ?
            ORDER BY last_updated_at DESC
        """, (slug,)).fetchall():
            bills.append({
                "id": r["id"],
                "document_nr": r["document_nr"],
                "slug": _bill_slug(r["document_nr"]),
                "title": r["title"],
                "current_stage": r["current_stage"],
                "current_status": r["current_status"],
                "last_updated_at": r["last_updated_at"],
            })

        pages.append({
            "slug": slug,
            "title": title,
            "likumi_lv_url": likumi_lv_url,
            "body_html": body_html,
            "bills_count": len(bills),
            "bills": bills,
        })

    return pages


def _generate_law_pages(db: sqlite3.Connection, env: Environment, output_dir: Path, laws_dir: Path = Path("wiki/laws")) -> int:
    """Renderē /likumi/<slug>.html katram wiki/laws/<slug>.md (izņemot likumi.md)."""
    out_laws = output_dir / "likumi"
    out_laws.mkdir(parents=True, exist_ok=True)
    template = env.get_template("likums.html.j2")
    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    count = 0
    for law in pages:
        html = template.render(law=law)
        target = out_laws / f"{law['slug']}.html"
        target.write_text(html, encoding="utf-8")
        count += 1
    logger.info("_generate_law_pages: wrote %d law pages to %s", count, out_laws)
    return count


def _fetch_law_index_page(
    db: sqlite3.Connection,
    laws_dir: Path = Path("wiki/laws"),
) -> list[dict[str, Any]]:
    """Build sortable index of base laws for /likumi.html.

    For each wiki/laws/<slug>.md (skipping likumi.md), join saeima_bills via
    base_law_slug to count attached likumprojekti and find the most recent
    activity date. Topic derives from saeima_bills.topic — most-frequent
    topic wins when a base law has bills across multiple topics. Empty
    bill_count is OK — signals no pending amendments.
    """
    from src.saeima import load_laws_index
    # load_laws_index expects the wiki root (it appends /laws internally).
    # _fetch_law_index_page accepts laws_dir=Path("wiki/laws") like _fetch_law_pages,
    # so pass the parent to maintain a consistent caller API.
    laws = load_laws_index(laws_dir.parent)
    if not laws:
        return []

    counts_rows = db.execute("""
        SELECT base_law_slug,
               COUNT(*) AS bill_count,
               MAX(last_updated_at) AS last_activity
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL
        GROUP BY base_law_slug
    """).fetchall()
    counts = {r["base_law_slug"]: dict(r) for r in counts_rows}

    topic_rows = db.execute("""
        SELECT base_law_slug, topic, COUNT(*) AS n
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL AND topic IS NOT NULL AND topic != ''
        GROUP BY base_law_slug, topic
        ORDER BY base_law_slug, n DESC, topic ASC
    """).fetchall()
    topics: dict[str, str] = {}
    for r in topic_rows:
        if r["base_law_slug"] not in topics:
            topics[r["base_law_slug"]] = r["topic"]

    out = []
    for slug, title in sorted(laws.items(), key=lambda kv: kv[1].casefold()):
        c = counts.get(slug, {})
        out.append({
            "slug": slug,
            "title": title,
            "topic": topics.get(slug, ""),
            "bill_count": c.get("bill_count", 0),
            "last_activity": c.get("last_activity", "") or "",
        })
    return out


def render_laws(env: Environment, db: sqlite3.Connection, atmina_dir: Path) -> int:
    """Render likumi.html + likumi/<slug>.html. Returns base-law index size.

    The return value (``laws_index_count``) is consumed by the
    ``balsojumi.html`` footer to stamp how many base laws are tracked,
    so it bubbles up via the orchestrator pass-through pattern (cf. F3c
    ``render_parties`` returning ``parties_data``).
    """
    _generate_law_pages(db, env, atmina_dir)
    laws_index = _fetch_law_index_page(db)
    law_topics = sorted({l["topic"] for l in laws_index if l["topic"]})
    _render_page(env, "likumi-index.html.j2", atmina_dir / "likumi.html", {
        "laws": laws_index,
        "law_topics": law_topics,
        "metrics": {
            "total": len(laws_index),
            "with_bills": sum(1 for l in laws_index if l["bill_count"] > 0),
        },
    })
    return len(laws_index)
