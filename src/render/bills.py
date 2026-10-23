"""Render Saeimas likumprojekti (bill) detail pages.

Phase F3e (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` and
``src.saeima`` (leaf) — no peer-module dependencies on laws/votes.

Outputs:
- ``output/atmina/likumprojekti/<slug>.html`` — per-bill timeline page
  with stages, submitters, amendment authors, vote summary and (when
  ``base_law_slug`` is set) a back-link to the parent law page.

Bill index data (``_fetch_bills``) is also reused by the orchestrator
in ``src/render/_orchestrator.py`` to populate ``env.globals["bill_slugs"]`` for
``_autolink_bills_filter``, and feeds the ``likumprojekti.html`` catalogue
(``render_bills_index``). The function therefore stays importable from this
module rather than being inlined into ``render_bills``.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment

from src.render._common import _bill_slug, _render_page, _slugify
from src.saeima.convocation import (
    bill_document_url, bill_kind, bill_type_filter_label, bill_type_sort_key)

logger = logging.getLogger(__name__)


# Cache: wiki_dir → {slug: title}. Keyed so test fixtures with distinct
# tmp_paths never collide with the production cache.
_LAW_TITLES_CACHE: dict[Path, dict[str, str]] = {}



def _public_summary(summary):
    """P3 vēsturiskās ielādes marķieris «Kopsavilkums nav pieejams — historic
    backfill …» nav kopsavilkums — lapā to nerāda (2026-10-09, 20 lapas)."""
    if summary and summary.startswith("Kopsavilkums nav pieejams"):
        return None
    return summary

def _get_law_titles(wiki_dir: Path | None = None) -> dict[str, str]:
    """Lazy cache of slug → title from wiki/laws/. Single read per process per wiki_dir."""
    if wiki_dir is None:
        from src.render import laws as _laws
        wiki_dir = _laws.LAWS_DIR.parent
    if wiki_dir not in _LAW_TITLES_CACHE:
        from src.saeima import load_laws_index
        _LAW_TITLES_CACHE[wiki_dir] = load_laws_index(wiki_dir)
    return _LAW_TITLES_CACHE[wiki_dir]


# Kartītes stadijas teksts. Atslēgas = saeima_bills.current_stage vērtības
# (2026-10-16: SELECT DISTINCT current_stage). Nezināmu vērtību rāda, kā ir.
# tiesneša_amats = iecelšana UN atbrīvošana (src/saeima/bills.py:146-148).
_STAGE_LABELS = {
    "1.lasījums": "1. lasījums",
    "2.lasījums": "2. lasījums",
    "3.lasījums": "3. lasījums",
    "tiesneša_amats": "lēmums par tiesneša amatu",
    "paziņojuma_balsojums": "balsojums par pieprasījumu",
    "procesuāls": "procedūras balsojums",
    "nezināms": None,
}
_LM_OTHER_RE = re.compile(r"^Lm\d+ cits$")


def _stage_label(stage: str | None) -> str | None:
    if not stage:
        return None
    if _LM_OTHER_RE.match(stage):
        return "lēmums"
    return _STAGE_LABELS.get(stage, stage)


# Josla «Kur likumprojekti ir tagad» — tikai Lp (lēmumiem/paziņojumiem nav
# lasījumu). Grupa = kur likumprojekts ir TAGAD, ne cik posmu tas izgāja:
# dati sākas 2026-04-27, agrākie posmi DB trūkst (67 Lp ar 3. bez 1. las.).
BUCKETS = [
    ("iesniegts", "Iesniegti"),
    ("pec1", "Pieņemti 1. lasījumā"),
    ("pec2", "Pieņemti 2. lasījumā"),
    ("pienemts", "Kļuvuši par likumu"),
    ("noraidits", "Noraidīti"),
    ("atsaukts", "Atsaukti"),
    ("nav", "Nav posma datu"),
]


def _stage_bucket(bill_type: str | None, stage: str | None, status: str | None) -> str:
    if not (bill_type or "").startswith("Lp"):
        return ""
    if status == "pieņemts":       # ietver steidzamos: likums jau 2. lasījumā
        return "pienemts"
    if status == "noraidīts":
        return "noraidits"
    if status == "atsaukts":
        return "atsaukts"
    return {"iesniegts": "iesniegts", "1.lasījums": "pec1",
            "2.lasījums": "pec2", "3.lasījums": "pec2"}.get(stage or "", "nav")


def card_status(bill_type: str | None, stage: str | None, status: str | None) -> str:
    """Kartītes statusa rinda. Lp ar statusu «pieņemts» = «kļuvis par likumu»
    arī steidzamam likumam 2. lasījumā (kā joslā «Kļuvuši par likumu»);
    citādi «posms · statuss». Atsaukts = tikai «atsaukts» (posms arī ir
    «atsaukts»; 2026-10-20)."""
    if (bill_type or "").startswith("Lp") and status == "pieņemts":
        return "kļuvis par likumu"
    if status == "atsaukts":
        return "atsaukts"
    return " · ".join(p for p in (_stage_label(stage), status) if p)


_LAW_QUOTED_RE = re.compile(r"^Grozījum[si] likumā [“\"](.+?)[”\"]$")
_LAW_LOCATIVE_RE = re.compile(r"^Grozījum[si] (.+likum)ā$")


def amended_law_name(title: str) -> str | None:
    """Grozāmā likuma nosaukums nominatīvā no «Grozījumi … likumā» virsraksta.
    Citas formas (Satversme, kārtības rullis, garš apraksts) → None."""
    t = (title or "").strip()
    m = _LAW_QUOTED_RE.match(t)
    if m:
        return f"«{m.group(1)}»"
    m = _LAW_LOCATIVE_RE.match(t)
    if m and " par " not in m.group(1):
        return m.group(1) + "s"
    return None


def _fetch_bills(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch all bills with denormalized current_stage/status + counts.

    Returns list ordered by last_updated_at DESC (newest first).
    Used both for the /likumprojekti.html grid and as index for detail page generation.
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
            "summary": _public_summary(r["summary"]),
            "topic": r["topic"],
            "current_stage": r["current_stage"],
            "stage_label": _stage_label(r["current_stage"]),
            "current_status": r["current_status"],
            "card_status": card_status(r["bill_type"], r["current_stage"], r["current_status"]),
            "bucket": _stage_bucket(r["bill_type"], r["current_stage"], r["current_status"]),
            "law": amended_law_name(r["title"]),
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
            st.stage_kind,
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
            "stage_kind": s["stage_kind"],
            "vote_summary": s["vote_summary"],
            "total_par": s["total_par"],
            "total_pret": s["total_pret"],
            "total_atturas": s["total_atturas"],
        })

    # relationship_type comes along because the politician renderer emits NO page
    # for 'inactive' people, while this template linked unconditionally — 17 dead
    # <a href> across 17 bill pages (2026-08-01 audit). The row is kept, because a
    # transparency record should not drop who submitted a bill; only the link goes.
    submitters = []
    for s in db.execute("""
        SELECT tp.name, tp.party, tp.relationship_type
        FROM saeima_bill_politicians j
        JOIN tracked_politicians tp ON tp.id = j.politician_id
        WHERE j.bill_id=? AND j.role='submitter'
        ORDER BY tp.name ASC
    """, (bill_id,)).fetchall():
        submitters.append({
            "slug": _slugify(s["name"]),
            "name": s["name"],
            "party": s["party"],
            "has_page": s["relationship_type"] != "inactive",
        })

    base_law_slug = bill_row["base_law_slug"]
    base_law_title: Optional[str] = None
    if base_law_slug:
        kw = {"wiki_dir": wiki_dir} if wiki_dir is not None else {}
        titles = _get_law_titles(**kw)
        base_law_title = titles.get(base_law_slug, base_law_slug.replace("-", " ").title())

    kind = bill_kind(bill_row["bill_type"])
    return {
        "id": bill_row["id"],
        "document_nr": bill_row["document_nr"],
        "slug": _bill_slug(bill_row["document_nr"]),
        "bill_type": bill_row["bill_type"],
        "kind_label": kind[0] if kind else "",
        "convocation": kind[1] if kind else None,
        "title": bill_row["title"],
        "summary": _public_summary(bill_row["summary"]),
        "topic": bill_row["topic"],
        "current_stage": bill_row["current_stage"],
        "current_status": bill_row["current_status"],
        "first_seen_at": bill_row["first_seen_at"],
        "last_updated_at": bill_row["last_updated_at"],
        "institutional_submitter": bill_row["institutional_submitter"],
        "stages": stages,
        "submitters_individual": submitters,
        "amendment_authors": [],  # Phase 2 — see master spec § 7.1 (priekšlikumu scrape)
        "external_document_url": bill_document_url(bill_row["document_nr"]),
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
    consistent across F3 sub-modules. The catalogue grid that links to
    these pages (``likumprojekti.html``) is ``render_bills_index`` below.
    """
    return _generate_bill_pages(db, env, atmina_dir)


def render_bills_index(
    env: Environment,
    bills: list[dict[str, Any]],
    laws_count: int,
    atmina_dir: Path,
) -> None:
    """Render likumprojekti.html — visu likumprojektu katalogs (līdz
    2026-10-16 paslēpta balsojumi.html cilne, 77 % no tās HTML)."""
    types = sorted({b["bill_type"] for b in bills if b.get("bill_type")}, key=bill_type_sort_key)
    # Veids («Likumprojekts») → cik sasaukumu tas aptver šajā sarakstā.
    kinds = Counter(k[0] for k in map(bill_kind, types) if k)
    lp = [b for b in bills if b.get("bucket")]
    counts = Counter(b["bucket"] for b in lp)
    law_counts = Counter(b["law"] for b in bills if b.get("law"))
    _render_page(env, "likumprojekti-index.html.j2", atmina_dir / "likumprojekti.html", {
        "bills": bills,
        "bill_types": [(t, bill_type_filter_label(t, bool(bill_kind(t)) and kinds[bill_kind(t)[0]] > 1))
                       for t in types],
        "bill_topics": sorted({b["topic"] for b in bills if b.get("topic")}),
        "laws_count": laws_count,
        "buckets": [(k, label, counts.get(k, 0)) for k, label in BUCKETS],
        "lp_total": len(lp),
        "top_laws": [(name, k) for name, k in law_counts.most_common(10) if k >= 3],
        "data_since": min((b["first_seen_at"] for b in bills if b.get("first_seen_at")), default=None),
    })
