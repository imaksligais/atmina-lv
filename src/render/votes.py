"""Render the Saeimas balsojumi page.

Phase F3e (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` and
``src.coalition`` (leaf) — no peer-module dependencies on bills/laws.

Outputs:
- ``output/atmina/balsojumi.html`` — single index page combining the
  vote list (with per-faction breakdown), the deputy attendance matrix
  (chronological columns × politician rows), and the bills-on-the-floor
  sidebar grid that links into ``likumprojekti/<slug>.html`` (rendered
  by ``src.render.bills``).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    _bill_slug,
    _render_page,
)

# Matrix pipeline — carved out to src/render/votes_matrix.py (phase 5.5).
# Re-imported here so the historical import path `from src.render.votes import
# _build_matrix_data` — used by tests/test_render_votes_matrix_json.py and
# tests/test_balsojumi_readability.py — keeps resolving.
# `render_votes` below calls `_build_matrix_data` / `_emit_matrix_json` through
# THIS module's globals, so monkeypatching them on `src.render.votes` still
# takes effect (tests/test_render_votes_matrix_json.py:404).
from src.render.votes_matrix import (  # noqa: F401  re-exported: historical import path
    FACTION_ORDER,
    OUTSIDE_FACTION,
    _PROCEDURAL_PREFIXES,
    _VOTE_CHAR_MAP,
    _build_matrix_compact,
    _build_matrix_data,
    _emit_matrix_json,
    _encode_vote_char,
    _faction_sort_key,
    _find_vote_index_by_date_motif,
    _is_procedural_vote,
)

logger = logging.getLogger(__name__)

# Recent-shard window. The matrix range buttons go up to "1 gads" (365 d), so the
# recent shard must cover ≥365 d; 400 gives a boundary buffer. The full archive
# (balsojumi-matrica.json) is fetched only for "Visa vēsture" / old-vote deep-links.
# Recent stays ~constant (~1 year of votes) as the archive grows — that is the point.
RECENT_WINDOW_DAYS = 400

def _result_counts(votes: list[dict[str, Any]]) -> tuple[int, int, int]:
    """(accepted, rejected, other) over ``saeima_votes.result``.

    The vocabulary is NOT binary — besides ``Pieņemts`` / ``Noraidīts`` the
    corpus carries ``Nod. kom.``, ``Likums``, ``Paziņojums`` and NULL. Only the
    two literal labels are counted; everything else falls into ``other``, which
    is NAMED on the page rather than folded into either bucket. ``Likums`` in
    particular reads like a pass but is not the literal label, so it stays in
    ``other`` by the same rule that keeps unknown results out of the red badge
    (tests/test_vote_result_non_binary.py).

    The three always sum to ``len(votes)`` — that is the point: a header number
    without a visible denominator is what this replaced.
    """
    accepted = sum(1 for v in votes if v.get("result") == "Pieņemts")
    rejected = sum(1 for v in votes if v.get("result") == "Noraidīts")
    return accepted, rejected, len(votes) - accepted - rejected


def _recent_cutoff_iso(days: int = RECENT_WINDOW_DAYS) -> str:
    """ISO date `days` before today (Latvia local) — the recent-shard cutoff."""
    return (date.today() - timedelta(days=days)).isoformat()


def _filter_recent_votes(
    votes: list[dict[str, Any]], cutoff_iso: str
) -> list[dict[str, Any]]:
    """Keep votes whose vote_date (YYYY-MM-DD) is on/after cutoff. Null dates drop."""
    return [v for v in votes if str(v.get("vote_date") or "")[:10] >= cutoff_iso]

def _enrich_faction_breakdown(
    fb_rows: list[dict[str, Any]], coalition_map: dict[str, str]
) -> list[dict[str, Any]]:
    """Compute majority_vote, discipline, total, coalition_status per faction
    row, then return sorted (coalition → opposition → other, size desc).

    Pure function over already-aggregated rows so it can be unit-tested
    without touching the DB. Discipline < 0.8 signals a split vote.
    """
    status_order = {"coalition": 0, "opposition": 1, "other": 2, "not_in_saeima": 3}
    enriched: list[dict[str, Any]] = []
    for fb in fb_rows:
        row = dict(fb)
        counts = {
            "Par": row.get("par", 0) or 0,
            "Pret": row.get("pret", 0) or 0,
            "Atturas": row.get("atturas", 0) or 0,
            "Nebalsoja": row.get("nebalso", 0) or 0,
        }
        total = sum(counts.values())
        row["total"] = total
        row["coalition_status"] = coalition_map.get(row["faction"], "other")
        if total == 0:
            row["majority_vote"] = None
            row["discipline"] = 0.0
        else:
            majority_key = max(counts, key=lambda k: counts[k])
            row["majority_vote"] = majority_key
            row["discipline"] = counts[majority_key] / total
        enriched.append(row)
    enriched.sort(key=lambda r: (status_order.get(r["coalition_status"], 9), -r["total"]))
    return enriched


def _fetch_votes(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch all Saeima votes with per-faction breakdown (majority/discipline).

    Per-vote tracked-politician lists are no longer materialized here — the
    Option-2 refactor (2026-07-17) deleted the SSR vote cards, so the client-side
    archive renderer (assets/bmv1.js) owns per-deputy rows from the matrix JSON.
    """
    from src.coalition import get_coalition_map
    _coalition_map = get_coalition_map(db)

    # Deputātu klātbūtnes reģistrācija nav balsojums (visi totāli 0, maldinošs
    # result='Noraidīts') — izslēgta no VISAS balsojumu sekcijas (saraksts,
    # matrica, metrikas) ar operatora lēmumu 2026-07-17. Prefiksa filtrs, ne
    # '%reģistrācij%' — pēdējais noķertu īstus balsojumus (Civilstāvokļa aktu
    # reģistrācijas likums). DB rindas paliek — T8 auditi tās joprojām redz.
    vote_rows = db.execute("""
        SELECT v.*, b.document_nr AS bill_doc_nr
        FROM saeima_votes v
        LEFT JOIN saeima_bills b ON b.id = v.bill_id
        WHERE v.motif NOT LIKE 'Deputātu klātbūtnes reģistrācija%'
        ORDER BY v.vote_date DESC, v.vote_time DESC
    """).fetchall()

    # Faction breakdown for ALL votes in ONE query, bucketed by vote_id.
    # Ordering per faction: coalition first (size desc), then opposition (size
    # desc), then other. Discipline = share of faction voting the majority
    # position — < 0.8 marks a split. Replaces the old per-vote N+1 GROUP BY
    # (~5.7k queries/render); row shape (faction/par/pret/atturas/nebalso) and
    # downstream _enrich_faction_breakdown behaviour are identical.
    fb_all = db.execute("""
        SELECT vote_id, faction,
               SUM(CASE WHEN vote = 'Par' THEN 1 ELSE 0 END) AS par,
               SUM(CASE WHEN vote = 'Pret' THEN 1 ELSE 0 END) AS pret,
               SUM(CASE WHEN vote = 'Atturas' THEN 1 ELSE 0 END) AS atturas,
               SUM(CASE WHEN vote NOT IN ('Par','Pret','Atturas') THEN 1 ELSE 0 END) AS nebalso
        FROM saeima_individual_votes
        WHERE faction IS NOT NULL AND faction != ''
        GROUP BY vote_id, faction
    """).fetchall()
    fb_by_vote: dict[int, list[dict[str, Any]]] = {}
    for fb in fb_all:
        fb_by_vote.setdefault(fb["vote_id"], []).append(dict(fb))

    results = []
    for vr in vote_rows:
        v = dict(vr)
        v["bill_slug"] = _bill_slug(v["bill_doc_nr"]) if v.get("bill_doc_nr") else None
        v["faction_breakdown"] = _enrich_faction_breakdown(
            fb_by_vote.get(v["id"], []), _coalition_map
        )
        v["topic"] = v.get("topic") or ""
        results.append(v)
    return results

def render_votes(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    votes: list[dict[str, Any]],
    bills: list[dict[str, Any]],
    laws_index_count: int,
) -> None:
    """Render balsojumi.html.

    ``votes`` and ``bills`` are passed in because both are also consumed
    by the index page (recent_votes) and as ``env.globals["bill_slugs"]``
    autolink source — the orchestrator fetches them once and threads
    them through. ``laws_index_count`` is the return value of
    ``render_laws`` and only stamps the balsojumi footer.
    """
    # Filter UI options span the FULL vote history. Since the Option-2 refactor
    # (2026-07-17) the vote list has a SINGLE rendering path — every card is
    # rendered client-side by assets/bmv1.js::balsojumiArchiveRender from the
    # matrix JSON, so every filter option is live against the whole corpus. See
    # docs/superpowers/plans/archive/2026-06-03-balsojumi-archive-filter.md.
    vote_topics = sorted(set(v["topic"] for v in votes if v.get("topic")))
    # Deputy filter options: every tracked politician who has cast a vote. Same
    # source table as the matrix JSON politicians (`n` field), so the names the
    # filter emits match the archive cards' data-deputies exactly. (Was derived
    # from per-vote tracked_votes before the Option-2 SSR-card removal.)
    # Faction per deputy for the filter's group headers (2026-09-04 readability
    # pass § E): an alphabetical ~100-name dropdown gave the reader no way to
    # find "everyone in ZZS". Faction = the LATEST non-empty per-vote faction,
    # the SAME derivation the matrix uses (see _build_matrix_data's
    # latest_faction) — a deputy must not land in one group here and another
    # there. Deputies who never sat in a faction group under OUTSIDE_FACTION.
    _latest_faction = {
        row["name"]: row["faction"]
        for row in db.execute("""
            SELECT tp.name, siv.faction
            FROM saeima_individual_votes siv
            JOIN tracked_politicians tp ON tp.id = siv.politician_id
            JOIN saeima_votes sv ON sv.id = siv.vote_id
            WHERE siv.politician_id IS NOT NULL
              AND siv.faction IS NOT NULL AND siv.faction != ''
            ORDER BY sv.vote_date ASC, sv.vote_time ASC
        """).fetchall()
    }  # ASC scan → each name keeps its LAST (newest) faction
    deputies = [
        {"name": row["name"], "faction": _latest_faction.get(row["name"], OUTSIDE_FACTION)}
        for row in db.execute("""
            SELECT DISTINCT tp.name FROM saeima_individual_votes siv
            JOIN tracked_politicians tp ON tp.id = siv.politician_id
            ORDER BY tp.name
        """).fetchall()
    ]
    deputies.sort(key=lambda d: (_faction_sort_key(d["faction"]), d["name"]))
    vote_sessions = sorted(
        {str(v["vote_date"])[:10] for v in votes if v.get("vote_date")},
        reverse=True,
    )
    # Month options (YYYY-MM, newest first) — first level of the two-step
    # session filter (2026-09-04 readability pass § E). A flat dropdown of every
    # sitting date is a usability defect at ~340 entries; picking months first
    # narrows the session list client-side (assets/blv1.js::applySessionOptionVisibility).
    # Derived from vote_sessions so the two lists can never disagree.
    vote_months = sorted({s[:7] for s in vote_sessions}, reverse=True)
    # Step 2 of balsojumi virtualization: the SSR matrix block + matrix_json
    # embed are removed from the template. Only the compact JSON artifact
    # is emitted; the client (assets/bmv1.js) fetches it lazily when the user
    # opens the Matrica subtab. See docs/superpowers/plans/archive/2026-05-28-...md.
    matrix_data = _build_matrix_data(db, votes)
    _emit_matrix_json(matrix_data, atmina_dir, all_dates=vote_sessions)  # full archive
    # Recent shard: same builder, date-filtered vote subset. The client loads this
    # by default; the full archive is fetched only on "Visa vēsture"/deep-link. The
    # recent shard stays ~constant (~1 year of votes) as the archive grows.
    # all_dates=vote_sessions (the FULL session list) so the recent shard's
    # session dropdown still lists every session; picking one outside the recent
    # window triggers the lazy full-archive fetch client-side.
    recent_votes = _filter_recent_votes(votes, _recent_cutoff_iso())
    recent_matrix = _build_matrix_data(db, recent_votes)
    _emit_matrix_json(
        recent_matrix, atmina_dir, basename="balsojumi-matrica-recent",
        all_dates=vote_sessions,
    )

    seven_days_ago = date.today() - timedelta(days=7)
    vote_total = len(votes)
    vote_last_week = 0
    for v in votes:
        vd = v.get("vote_date")
        if hasattr(vd, "isoformat"):
            vd_date = vd
        elif isinstance(vd, str):
            try:
                vd_date = date.fromisoformat(vd[:10])
            except ValueError:
                vd_date = None
        else:
            vd_date = None
        if vd_date and vd_date >= seven_days_ago:
            vote_last_week += 1

    # The old header metric was a bare "Pieņemti %" over the WHOLE corpus, which
    # silently read every non-Pieņemts row as a rejection and printed a
    # percentage with no visible denominator. Three counts that sum to `total`
    # instead — see _result_counts. Same vocabulary as the TAB-1 session group
    # headers (assets/bmv1.js::archiveGroupHeader) so both surfaces agree.
    vote_accepted, vote_rejected, vote_other_result = _result_counts(votes)

    vote_metrics = {
        "total": vote_total,
        "last_week": vote_last_week,
        "accepted": vote_accepted,
        "rejected": vote_rejected,
        "other_result": vote_other_result,
    }

    bill_topics = sorted({b["topic"] for b in bills if b["topic"]})

    _render_page(env, "balsojumi.html.j2", atmina_dir / "balsojumi.html", {
        "vote_topics": vote_topics,
        "deputies": deputies,
        "vote_sessions": vote_sessions,
        "vote_months": vote_months,
        "metrics": vote_metrics,
        "bills": bills,
        "bill_topics": bill_topics,
        "laws_index_count": laws_index_count,
    })
