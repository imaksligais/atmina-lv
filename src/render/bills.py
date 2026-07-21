"""Render Saeimas likumprojekti (bill) detail pages.

Phase F3e (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` and
``src.saeima`` (leaf) — no peer-module dependencies on laws/votes.

Outputs:
- ``output/atmina/likumprojekti/<slug>.html`` — per-bill timeline page
  with stages, submitters, amendment authors, vote summary and (when
  ``base_law_slug`` is set) a back-link to the parent law page.

Bill index data (``_fetch_bills``) is also reused by the orchestrator
in ``src/generate.py`` to populate ``env.globals["bill_slugs"]`` for
``_autolink_bills_filter`` and to feed the ``balsojumi.html`` footer.
The function therefore stays importable from this module rather than
being inlined into ``render_bills``.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment

from src.render._common import _bill_slug, _slugify

logger = logging.getLogger(__name__)


# Cache: wiki_dir → {slug: title}. Keyed so test fixtures with distinct
# tmp_paths never collide with the production cache.
_LAW_TITLES_CACHE: dict[Path, dict[str, str]] = {}


def _get_law_titles(wiki_dir: Path = Path("wiki")) -> dict[str, str]:
    """Lazy cache of slug → title from wiki/laws/. Single read per process per wiki_dir."""
    if wiki_dir not in _LAW_TITLES_CACHE:
        from src.saeima import load_laws_index
        _LAW_TITLES_CACHE[wiki_dir] = load_laws_index(wiki_dir)
    return _LAW_TITLES_CACHE[wiki_dir]


def _fetch_bills(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch all bills with denormalized current_stage/status + counts.

    Returns list ordered by last_updated_at DESC (newest first).
    Used both for /balsojumi.html#bills-list grid and as index for detail page generation.
    """
    rows = db.execute("""
        SELECT
            b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
            b.current_stage, b.current_status,
            b.first_seen_at, b.last_updated_at,
            b.institutional_submitter,
            (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
            (SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=b.id) AS stage_count,
            (SELECT COUNT(*) FROM saeima_votes WHERE bill_id=b.id) AS vote_count
        FROM saeima_bills b
        ORDER BY b.last_updated_at DESC, b.id DESC
    """).fetchall()
    return [
        {
            "id": r["id"],
            "document_nr": r["document_nr"],
            "slug": _bill_slug(r["document_nr"]),
            "bill_type": r["bill_type"],
            "title": r["title"],
            "summary": r["summary"],
            "topic": r["topic"],
            "current_stage": r["current_stage"],
            "current_status": r["current_status"],
            "first_seen_at": r["first_seen_at"],
            "last_updated_at": r["last_updated_at"],
            "institutional_submitter": r["institutional_submitter"],
            "submitter_count": r["submitter_count"],
            "stage_count": r["stage_count"],
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]


def _fetch_bill_detail(
    db: sqlite3.Connection,
    bill_id: int,
    wiki_dir: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    """Fetch one bill ar pilnu stages timeline + submitters + amendment_authors.

    Returns None ja bill_id neeksistē. Stages ordered chronologiski (stage_date ASC, id ASC).
    wiki_dir: override for testing (passed to _get_law_titles).
    """
    bill_row = db.execute("""
        SELECT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
               b.current_stage, b.current_status,
               b.first_seen_at, b.last_updated_at, b.institutional_submitter,
               b.base_law_slug
        FROM saeima_bills b WHERE b.id=?
    """, (bill_id,)).fetchone()
    if bill_row is None:
        return None

    stages = []
    for s in db.execute("""
        SELECT
            st.id, st.stage_name, st.stage_result, st.stage_date, st.amendment_nr, st.vote_id,
            v.summary AS vote_summary, v.total_par, v.total_pret, v.total_atturas
        FROM saeima_bill_stages st
        LEFT JOIN saeima_votes v ON v.id = st.vote_id
        WHERE st.bill_id=? ORDER BY st.stage_date ASC, st.id ASC
    """, (bill_id,)).fetchall():
        stages.append({
            "stage_name": s["stage_name"],
            "stage_result": s["stage_result"],
            "stage_date": s["stage_date"],
            "amendment_nr": s["amendment_nr"],
            "vote_id": s["vote_id"],
            "vote_summary": s["vote_summary"],
            "total_par": s["total_par"],
            "total_pret": s["total_pret"],
            "total_atturas": s["total_atturas"],
        })

    submitters = []
    for s in db.execute("""
        SELECT tp.name, tp.party
        FROM saeima_bill_politicians j
        JOIN tracked_politicians tp ON tp.id = j.politician_id
        WHERE j.bill_id=? AND j.role='submitter'
        ORDER BY tp.name ASC
    """, (bill_id,)).fetchall():
        submitters.append({"slug": _slugify(s["name"]), "name": s["name"], "party": s["party"]})

    ext = db.execute("""
        SELECT v.document_url FROM saeima_votes v
        WHERE v.bill_id=? AND v.document_url IS NOT NULL
        ORDER BY v.vote_date DESC, v.vote_time DESC, v.id DESC LIMIT 1
    """, (bill_id,)).fetchone()

    base_law_slug = bill_row["base_law_slug"]
    base_law_title: Optional[str] = None
    if base_law_slug:
        kw = {"wiki_dir": wiki_dir} if wiki_dir is not None else {}
        titles = _get_law_titles(**kw)
        base_law_title = titles.get(base_law_slug, base_law_slug.replace("-", " ").title())

    return {
        "id": bill_row["id"],
        "document_nr": bill_row["document_nr"],
        "slug": _bill_slug(bill_row["document_nr"]),
        "bill_type": bill_row["bill_type"],
        "title": bill_row["title"],
        "summary": bill_row["summary"],
        "topic": bill_row["topic"],
        "current_stage": bill_row["current_stage"],
        "current_status": bill_row["current_status"],
        "first_seen_at": bill_row["first_seen_at"],
        "last_updated_at": bill_row["last_updated_at"],
        "institutional_submitter": bill_row["institutional_submitter"],
        "stages": stages,
        "submitters_individual": submitters,
        "amendment_authors": [],  # Phase 2 — see master spec § 7.1 (priekšlikumu scrape)
        "external_document_url": ext["document_url"] if ext else None,
        "base_law_slug": base_law_slug,
        "base_law_title": base_law_title,
    }


def _generate_bill_pages(db: sqlite3.Connection, env: Environment, output_dir: Path) -> int:
    """Render likumprojekti/<slug>.html katram bill. Returns count.

    Uzcel mapi `output_dir/likumprojekti/`. Pieņem env ar filters jau registered.
    """
    bills_dir = output_dir / "likumprojekti"
    bills_dir.mkdir(parents=True, exist_ok=True)
    template = env.get_template("likumprojekts.html.j2")
    bills = _fetch_bills(db)
    count = 0
    for b in bills:
        detail = _fetch_bill_detail(db, b["id"])
        if detail is None:
            logger.warning("_generate_bill_pages: bill_id=%s detail returned None — skip", b["id"])
            continue
        html = template.render(bill=detail)
        target = bills_dir / f"{detail['slug']}.html"
        target.write_text(html, encoding="utf-8")
        count += 1
    logger.info("_generate_bill_pages: wrote %d bill pages to %s", count, bills_dir)
    return count


def render_bills(env: Environment, db: sqlite3.Connection, atmina_dir: Path) -> int:
    """Render every likumprojekti/<slug>.html. Returns the page count.

    Thin orchestrator over ``_generate_bill_pages``. Kept separate so the
    orchestrator-level shape (``render_<page>(env, db, atmina_dir)``) stays
    consistent across F3 sub-modules. ``balsojumi.html`` rendering — the
    bill list grid that links to these pages — lives in ``src.render.votes``.
    """
    return _generate_bill_pages(db, env, atmina_dir)
