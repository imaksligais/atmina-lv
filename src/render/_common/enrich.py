"""``_common`` DB-lasošā bagātināšana — vienīgais klasteris, kas ņem
``sqlite3.Connection`` (audita § 1.3: "the odd one out in a leaf-helpers
module"). Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05
(plāna 5.8).

Importē tikai pakotnes iekšējos lapu-moduļus (``constants``, ``slugs``,
``dates``, ``text``) — nevienu ``src.render.<page>`` māsu-moduli, tātad
``src/render/__init__.py:22-30`` daļējās inicializācijas līgums turas.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Optional
from urllib.parse import quote as _quote

from src.render._common.constants import (
    ASSETS_DIR,
    CATEGORY_LV,
    CLAIM_TYPE_LABEL,
    PARTY_COLORS,
    SEVERITY_LV,
    _SEVERITY_GLYPHS,
)
from src.render._common.dates import (
    _delta_days,
    _domain_label,
    _format_tweet_time,
    _initials_from_name,
    _normalize_date,
)
from src.render._common.slugs import _party_short_name, _slugify
from src.render._common.text import _latvian_quotes, _split_summary

# ── Cross-page domain helpers ───────────────────────────────────────


def _activity_display_date(date_str: str, today: Optional[date] = None) -> str:
    """Kartītes kājenes datums: 'MM-DD' (šogad) vai 'YYYY-MM-DD' (vecāki gadi).

    Tweet kandidāti nes 'YYYY-MM-DD HH:MM' — laika daļa tiek saglabāta
    kārtējā gadā (atbilst iepriekšējai `date[5:]` uzvedībai), bet nomesta
    vecākiem gadiem, jo kartītē vietas maz. Bez gada norādes vecs ieraksts
    ('11-03' no 2025.) izlasās kā nesens.
    """
    if not date_str:
        return ""
    if today is None:
        from src.db import now_lv_dt
        today = now_lv_dt().date()
    if date_str[:4] == str(today.year):
        return date_str[5:]
    return date_str[:10]


def _get_last_activity(db: sqlite3.Connection, politician_id: int, politician_name: str = "") -> dict | None:
    """Get the most recent activity for a politician across all sources.

    Used by `_fetch_personas` (F3b personas.py target) and
    `_fetch_party_detail` (F3c parties.py target). Promoted to `_common`
    so personas + parties stay leaf-clean of each other.

    Returns the single most recent of: last claim, last Saeima vote,
    last X post (authored), last X mention, last news mention. None if
    none exists.
    """
    name_enc = _quote(politician_name, safe="")
    candidates: list[dict] = []

    # 1. Last claim (pozīcija) — TIKAI claim_type='position' (Datu kontrakts #4).
    # Bez šī filtra balsojumu claims (101:1 pārsvarā) uzvarēja svaiguma sacīkstē
    # 112 no 180 aktīvajiem politiķiem, un rinda renderējās kā 📌 pozīcija ar
    # saiti uz pozicijas.html, kas šo ierakstu nesatur — tā lapa filtrē pareizi.
    # Balsojumam turklāt JAU ir savs, pareizi marķēts kandidāts zemāk (#2).
    row = db.execute(
        "SELECT topic, source_url, stated_at FROM claims "
        "WHERE opponent_id = ? AND claim_type = 'position' "
        "ORDER BY stated_at DESC LIMIT 1",
        (politician_id,),
    ).fetchone()
    if row:
        candidates.append({
            "date": _normalize_date(row["stated_at"]),
            "type": "claim",
            "label": row["topic"] or "Pozīcija",
            "source_url": row["source_url"] or "",
            "href": f"pozicijas.html?persona={name_enc}",
            "icon": "📌",
        })

    # 2. Last Saeima vote
    vote = db.execute("""
        SELECT sv.vote_date, sv.summary, sv.topic, siv.vote
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY sv.vote_date DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if vote:
        v = vote["vote"] or ""
        vote_label = {"Par": "Balsoja par", "Pret": "Balsoja pret", "Atturas": "Atturējās"}.get(v, "Balsoja")
        summary = (vote["summary"] or vote["topic"] or "")
        if len(summary) > 50:
            summary = summary[:47] + "…"
        candidates.append({
            "date": _normalize_date(vote["vote_date"]),
            "type": "vote",
            "label": f"{vote_label}: {summary}" if summary else vote_label,
            "source_url": "",
            "href": f"balsojumi.html?deputats={name_enc}",
            "icon": "🗳",
        })

    # 3. Last X post (authored by politician). Uses published_at (UTC ISO from
    # twikit, actual tweet post time) converted to LV-local, so cards show the
    # real post time — not the scrape run HH:MM that would collapse many
    # tweets onto the same minute. Matches _fetch_x_data (now in
    # src/render/x.py post-F3f.2; original ordering shipped in c197827).
    xpost = db.execute("""
        SELECT d.published_at, d.scraped_at, d.source_url FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'twitter'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if xpost:
        candidates.append({
            "date": _format_tweet_time(xpost["published_at"], xpost["scraped_at"]),
            "type": "x_post",
            "label": "Rakstīja X",
            "source_url": xpost["source_url"] or "",
            "href": f"x.html?persona={name_enc}",
            "icon": "𝕏",
        })

    # 4. Last X mention — same published_at preference as xpost.
    xmention = db.execute("""
        SELECT d.published_at, d.scraped_at, d.source_url FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND dp.role = 'mention_target' AND d.platform = 'x_mention'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if xmention:
        candidates.append({
            "date": _format_tweet_time(xmention["published_at"], xmention["scraped_at"]),
            "type": "x_mention",
            "label": "Pieminēts X",
            "source_url": xmention["source_url"] or "",
            "href": f"x.html?persona={name_enc}&tab=mentions",
            "icon": "𝕏",
        })

    # 5. Last news mention
    news = db.execute("""
        SELECT d.scraped_at, d.source_url, d.source_domain FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'web'
        ORDER BY d.scraped_at DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if news:
        domain = (news["source_domain"] or "ziņas").replace("www.", "")
        candidates.append({
            "date": _normalize_date(news["scraped_at"]),
            "type": "news",
            "label": f"Pieminēts: {domain}",
            "source_url": news["source_url"] or "",
            "href": f"zinas.html?persona={name_enc}",
            "icon": "📰",
        })

    if not candidates:
        return None

    # Pick most recent by date
    candidates.sort(key=lambda c: c["date"], reverse=True)
    best = candidates[0]
    best["display"] = _activity_display_date(best["date"])
    return best


def _source_to_internal_link(source_url: str, politician_name: str, db: sqlite3.Connection) -> str | None:
    """Map an external source URL to an internal site link."""
    if not source_url:
        return None
    if "x.com" in source_url or "twitter.com" in source_url:
        return f"x.html?persona={_quote(politician_name)}"
    if "SaeimaLIVS" in source_url:
        vote = db.execute("SELECT id FROM saeima_votes WHERE url = ?", (source_url,)).fetchone()
        if vote:
            return f"balsojumi.html#vote-{vote['id']}"
    # Web news sources → ziņas page
    if source_url.startswith("http"):
        return f"zinas.html?persona={_quote(politician_name)}"
    return None


def _document_domain(db: sqlite3.Connection, source_url: str | None) -> str | None:
    """``documents.source_domain`` pēc URL, vai ``None``, ja dokumenta nav.

    Saeimas balsojumu URL un vēsturiskās rindas dokumenta rindu nemaz nenes —
    tad atgriež ``None``, un ``_domain_label()`` atkāpjas uz URL hostu.
    """
    if not source_url:
        return None
    row = db.execute(
        "SELECT source_domain FROM documents WHERE source_url = ? "
        "AND source_domain IS NOT NULL LIMIT 1",
        (source_url,),
    ).fetchone()
    return row[0] if row else None  # indekss, ne atslēga — arī bez Row factory


def _enrich_contradiction(d: dict[str, Any], db: sqlite3.Connection) -> None:
    """In-place enrichment for a contradiction row.

    Input dict must already contain: severity, politician_name, party,
    old_date, new_date, old_source, new_source. After this call the dict
    also has: severity_lv, slug, party_short, party_color, old_link,
    new_link, vote_summary, vote_id, severity_glyph, initials,
    old_source_domain, new_source_domain, delta_days. Dates are trimmed
    to 10-char ISO format.

    Safe to call on rows that already carry the SELECT-widened columns
    (salience, role, old_quote, new_quote) — those pass through.
    """
    # Contract: callers must supply the source columns this helper reads.
    for _k in ("severity", "politician_name", "old_date", "new_date"):
        if _k not in d:
            raise KeyError(f"_enrich_contradiction requires {_k!r} on input dict")
    d["severity_lv"] = SEVERITY_LV.get(d["severity"], d["severity"] or "")
    d["slug"] = _slugify(d["politician_name"])
    party = d.get("party") or ""
    d["party_short"] = _party_short_name(party) if party else ""
    d["party_color"] = PARTY_COLORS.get(party, "#8b8fa3")
    # Date trim must run before _delta_days so the delta uses normalized inputs.
    for key in ("old_date", "new_date"):
        if d[key] and len(d[key]) >= 10:
            d[key] = d[key][:10]
    # Chronological ordering: the left panel ("old" slot) must be the earlier
    # stated_at. DB old/new reflect detection order (contradiction-hunter pairs),
    # which can flip when saeima-tracker backfills a vote against an already-
    # stored public statement (e.g., pretruna #13 Mieriņa).
    old_d = d.get("old_date") or ""
    new_d = d.get("new_date") or ""
    if old_d and new_d and old_d > new_d:
        for k in ("stance", "date", "source", "quote", "claim_type"):
            ok, nk = f"old_{k}", f"new_{k}"
            d[ok], d[nk] = d.get(nk), d.get(ok)
    # Category label derived from the claim_type pair (order-independent).
    # Drives the main badge text; severity still drives color via CSS class.
    old_ct = d.get("old_claim_type") or "position"
    new_ct = d.get("new_claim_type") or "position"
    d["category"] = "_".join(sorted([old_ct, new_ct]))
    d["category_label"] = CATEGORY_LV.get(d["category"], d["severity_lv"])
    # Panel labels: chronological for same-type pairs, claim-type-named for mixed.
    if old_ct == new_ct:
        d["old_label"] = "Iepriekš"
        d["new_label"] = "Pašlaik"
    else:
        d["old_label"] = CLAIM_TYPE_LABEL.get(old_ct, "Iepriekš")
        d["new_label"] = CLAIM_TYPE_LABEL.get(new_ct, "Pašlaik")
    d["old_link"] = _source_to_internal_link(d.get("old_source"), d["politician_name"], db)
    d["new_link"] = _source_to_internal_link(d.get("new_source"), d["politician_name"], db)
    d["vote_summary"] = None
    d["vote_id"] = None
    if d.get("new_source") and "SaeimaLIVS" in (d["new_source"] or ""):
        vote = db.execute(
            "SELECT id, summary FROM saeima_votes WHERE url = ?",
            (d["new_source"],),
        ).fetchone()
        if vote:
            d["vote_summary"] = vote["summary"]
            d["vote_id"] = vote["id"]
    d["severity_glyph"] = _SEVERITY_GLYPHS.get(d["severity"], "·")
    d["initials"] = _initials_from_name(d["politician_name"])
    d["has_photo"] = (ASSETS_DIR / "photos" / f"{d['slug']}.jpg").exists()
    # Izdevēja etiķete no documents.source_domain, ne no URL hosta (verdikts 41,
    # 2026-09-06). Pretrunu vaicājumi nes tikai claim URL, tāpēc dokumenta rindu
    # meklē te — pretrunu ir desmiti, ne tūkstoši, tāpēc divi SELECT uz rindu ir
    # lētāk nekā JOIN pievienošana katrā no piecām pretrunu virsmām.
    d["old_source_domain"] = _domain_label(
        _document_domain(db, d.get("old_source")), d.get("old_source"))
    d["new_source_domain"] = _domain_label(
        _document_domain(db, d.get("new_source")), d.get("new_source"))
    d["delta_days"] = _delta_days(d.get("old_date"), d.get("new_date"))
    # Normalize paraphrase text to Latvian-style quotes; leave verbatim quotes alone.
    for key in ("summary", "old_stance", "new_stance"):
        if key in d:
            d[key] = _latvian_quotes(d[key])
    # Lift bracketed context notes out of summary so the UI can render them
    # as a distinct block rather than inline square brackets.
    clean, ctx = _split_summary(d.get("summary"))
    d["summary"] = clean
    d["context_note"] = ctx


def vote_alignment_data(
    db: sqlite3.Connection, min_total: int = 10
) -> dict[str, Any]:
    """Pairwise Saeima vote-agreement matrix for ALL politicians, in one pass.

    Replaces two SQL self-joins over ``saeima_individual_votes`` (~695k rows,
    ~22M intermediate pairs): the per-pid variant ran once per deputy profile
    (~60s across render_politicians) and the global variant once in
    ``links._fetch_graph_data`` (~41s). This computes the identical numbers
    via three indicator-matrix products in ~2s total (benchmarked 2026-08-20:
    0 mismatches across all 9034 qualifying pairs) — see BACKLOG
    § Render self-join lēnās stadijas.

    Only cast ballots count (Par/Pret/Atturas on BOTH sides) — presence and
    registration states are excluded so the metric measures vote agreement,
    not attendance (rankings.py::_vote_alignment_outliers fix, 2026-06-08).

    Returns ``{"pairs": {(lo, hi): (agree, total)}, "meta": {pid: row}}``
    where keys are politician-id tuples with ``lo < hi``, only pairs with
    ``total >= min_total`` are retained, and ``meta`` maps every tracked
    politician id to ``{"name", "party", "relationship_type"}``.

    Compute once per render domain and thread the result down — the data
    cannot change mid-render, and explicit data flow avoids cache
    invalidation semantics (sqlite3.Connection is not weakref-able).
    """
    import numpy as np  # lazy: only render paths that need the matrix pay the import

    raw = db.execute("""
        SELECT vote_id, politician_id, vote FROM saeima_individual_votes
        WHERE vote IN ('Par', 'Pret', 'Atturas')
    """).fetchall()

    meta: dict[int, dict[str, Any]] = {}
    for r in db.execute(
        "SELECT id, name, party, relationship_type FROM tracked_politicians"
    ):
        meta[r["id"]] = {
            "name": r["name"],
            "party": r["party"],
            "relationship_type": r["relationship_type"],
        }

    pairs: dict[tuple[int, int], tuple[int, int]] = {}
    if not raw:
        return {"pairs": pairs, "meta": meta}

    vote_idx: dict[int, int] = {}
    pol_idx: dict[int, int] = {}
    for r in raw:
        vote_idx.setdefault(r["vote_id"], len(vote_idx))
        pol_idx.setdefault(r["politician_id"], len(pol_idx))
    ballot_val = {"Par": 1, "Pret": 2, "Atturas": 3}
    m = np.zeros((len(pol_idx), len(vote_idx)), dtype=np.int8)
    for r in raw:
        m[pol_idx[r["politician_id"]], vote_idx[r["vote_id"]]] = ballot_val[r["vote"]]

    cast = (m > 0).astype(np.int32)
    total = cast @ cast.T
    agree = np.zeros_like(total)
    for v in (1, 2, 3):
        indicator = (m == v).astype(np.int32)
        agree += indicator @ indicator.T

    pids = list(pol_idx.keys())
    qualifying = np.argwhere(np.triu(total, k=1) >= min_total)
    for i, j in qualifying:
        p1, p2 = pids[i], pids[j]
        lo, hi = (p1, p2) if p1 < p2 else (p2, p1)
        pairs[(lo, hi)] = (int(agree[i, j]), int(total[i, j]))
    return {"pairs": pairs, "meta": meta}
