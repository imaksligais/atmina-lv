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

import json
import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.db import now_lv_dt
from src.render._common import (
    _bill_slug,
    _emit_json_compressed,
    _render_page,
    _slugify,
)

logger = logging.getLogger(__name__)


# Vote-string encoding for the compact matrix JSON.
# See docs/superpowers/plans/2026-05-28-balsojumi-virtualization.md § "Datu formāts".
_VOTE_CHAR_MAP = {
    "Par": "P",
    "Pret": "N",
    "Atturas": "A",
    "Nebalsoja": "X",
}


def _encode_vote_char(vote_type: str | None) -> str:
    """Map full vote-type label to single-char encoding for the compact JSON.

    None → '.' (absent — no saeima_individual_votes row).
    Any non-standard value collapses to 'X' (Nebalsoja).
    """
    if vote_type is None:
        return "."
    return _VOTE_CHAR_MAP.get(vote_type, "X")


# Recent-shard window. The matrix range buttons go up to "1 gads" (365 d), so the
# recent shard must cover ≥365 d; 400 gives a boundary buffer. The full archive
# (balsojumi-matrica.json) is fetched only for "Visa vēsture" / old-vote deep-links.
# Recent stays ~constant (~1 year of votes) as the archive grows — that is the point.
RECENT_WINDOW_DAYS = 400


def _recent_cutoff_iso(days: int = RECENT_WINDOW_DAYS) -> str:
    """ISO date `days` before today (Latvia local) — the recent-shard cutoff."""
    return (date.today() - timedelta(days=days)).isoformat()


def _filter_recent_votes(
    votes: list[dict[str, Any]], cutoff_iso: str
) -> list[dict[str, Any]]:
    """Keep votes whose vote_date (YYYY-MM-DD) is on/after cutoff. Null dates drop."""
    return [v for v in votes if str(v.get("vote_date") or "")[:10] >= cutoff_iso]


# Motif prefixes for procedural Saeima votes — attendance registration,
# session breaks, agenda + bill-referral mechanics, committee composition,
# deputy mandate housekeeping. These dominate session counts but carry no
# policy substance, so by default the JS matrix hides them. Toggleable.
_PROCEDURAL_PREFIXES = (
    "Deputātu klātbūtnes reģistrācija",
    "Par sēdes pārtraukumu",
    "Par sēdes pārcelšanu",
    "Par sēdes slēgšanu",
    "Par darba kārtības",
    "Par nodošanu komisij",
    "Par nodošanu papildus",
    "Par atteikšanos no deputāta",
    "Par deputāta pilnvaru",
    "Par deputāta mandāta",
    "Par neapmaksāta atvaļinājuma",
    "Par neapm. atvaļinājuma",
    "Par balsojuma rezultāta",
    "Par Saeimas komisiju sastāva",
    "Par Saeimas pastāvīgo komisiju",
)
# Explicitly NOT marked procedural (each is substantive even if it sounds
# administrative):
# - "Par lēmuma projekta ..."           — vote on the resolution itself
# - "Par Saeimas izmeklēšanas komisiju" — establishing an investigation
# - "Par likumprojekta atzīšanu ..."    — declares bill as urgent (substantive)


def _is_procedural_vote(vote: dict[str, Any]) -> bool:
    """Mark procedural Saeima votes (attendance, breaks, referrals, mandates).

    Two-pronged: motif prefix match against ``_PROCEDURAL_PREFIXES``, plus a
    zero-total fallback (``total_par+total_pret+total_atturas == 0`` means
    nothing happened beyond presence registration regardless of motif).
    Conservative — false positives waste a matrix column but never hide a
    policy vote that has any actual cast ballots.
    """
    motif = (vote.get("motif") or "").strip()
    for prefix in _PROCEDURAL_PREFIXES:
        if motif.startswith(prefix):
            return True
    total = (
        (vote.get("total_par") or 0)
        + (vote.get("total_pret") or 0)
        + (vote.get("total_atturas") or 0)
    )
    return total == 0


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


def _build_matrix_data(db: sqlite3.Connection, votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build vote matrix data for the balsojumi matrix visualization.

    Returns a dict with vote_columns (chronological ASC), politicians (grouped
    by faction, sorted by name), and a sorted factions list.
    """
    # Preferred faction order; anything else sorts alphabetically after these
    FACTION_ORDER = ["AS", "JV", "LPV", "NA", "PRO", "ZZS"]

    # Coalition status per faction — carried into the compact faction objects so
    # the client-side TAB-1 archive cards can colour the faction strip identically
    # to the SSR cards (see balsojumi.html.j2 faction-chip is-coalition/is-opposition).
    from src.coalition import get_coalition_map
    _coalition_map = get_coalition_map(db)

    # --- vote_columns: chronological ASC (oldest first → newest on the right) ---
    sorted_votes = sorted(
        votes,
        key=lambda v: (v.get("vote_date") or "", v.get("vote_time") or ""),
    )
    vote_columns: list[dict[str, Any]] = []
    vote_id_order: list[int] = []
    for v in sorted_votes:
        vid = v["id"]
        vote_id_order.append(vid)
        vote_columns.append({
            "id": vid,
            "motif": v.get("motif") or "",
            "summary": v.get("summary") or "",
            "date": v.get("vote_date") or "",
            "time": v.get("vote_time") or "",
            "result": v.get("result") or "",
            "topic": v.get("topic") or "",
            "total_par": v.get("total_par") or 0,
            "total_pret": v.get("total_pret") or 0,
            "total_atturas": v.get("total_atturas") or 0,
            "url": v.get("url") or "",
            "document_url": v.get("document_url") or "",
            "document_nr": v.get("document_nr") or "",
            # Bill link target for TAB-1 archive cards (likumprojekti/<slug>.html).
            "bill_slug": v.get("bill_slug") or "",
            "bill_doc_nr": v.get("bill_doc_nr") or "",
            "faction_breakdown": [
                {"faction": fb["faction"], "par": fb["par"], "pret": fb["pret"],
                 "atturas": fb["atturas"], "nebalso": fb["nebalso"]}
                for fb in v.get("faction_breakdown", [])
            ],
            "is_unanimous": (v.get("total_pret") or 0) == 0 and (v.get("total_atturas") or 0) == 0,
        })

    # --- gather individual votes for tracked politicians ---
    iv_rows = db.execute("""
        SELECT siv.vote_id, siv.vote, siv.politician_id, siv.faction,
               tp.name
        FROM saeima_individual_votes siv
        JOIN tracked_politicians tp ON siv.politician_id = tp.id
        WHERE siv.politician_id IS NOT NULL
        ORDER BY tp.name
    """).fetchall()

    # Build per-politician data: {pid: {name, faction, votes_by_vid}}
    politician_map: dict[int, dict[str, Any]] = {}
    for row in iv_rows:
        pid = row["politician_id"]
        if pid not in politician_map:
            politician_map[pid] = {
                "pid": pid,
                "name": row["name"],
                "faction": row["faction"] or "",
                "votes_by_vid": {},
            }
        politician_map[pid]["votes_by_vid"][row["vote_id"]] = row["vote"]

    # --- build politician entries with full vote arrays and summaries ---
    def faction_sort_key(faction: str) -> tuple:
        try:
            return (0, FACTION_ORDER.index(faction))
        except ValueError:
            return (1, faction)

    sorted_politicians = sorted(
        politician_map.values(),
        key=lambda p: (faction_sort_key(p["faction"]), p["name"]),
    )

    factions_seen: set[str] = set()
    politicians: list[dict[str, Any]] = []
    for p in sorted_politicians:
        faction = p["faction"]
        if faction:
            factions_seen.add(faction)
        vote_list: list[dict[str, Any]] = []
        par = pret = atturas = nebalso = 0
        for vid in vote_id_order:
            vtype = p["votes_by_vid"].get(vid)
            vote_list.append({"vote_id": vid, "vote_type": vtype})
            if vtype == "Par":
                par += 1
            elif vtype == "Pret":
                pret += 1
            elif vtype == "Atturas":
                atturas += 1
            elif vtype is not None:
                # Nebalsoja or any other non-standard vote type
                nebalso += 1
        total = par + pret + atturas + nebalso
        total_votes = len(vote_id_order)
        attendance_pct = round(total / total_votes * 100) if total_votes else 0
        politicians.append({
            "pid": p["pid"],
            "name": p["name"],
            "slug": _slugify(p["name"]),
            "faction": faction,
            "votes": vote_list,
            "summary": {
                "par": par,
                "pret": pret,
                "atturas": atturas,
                "nebalso": nebalso,
                "total": total,
                "attendance_pct": attendance_pct,
            },
        })

    # --- build faction objects with members, for the template ---
    FACTION_COLORS = {
        "JV": "#3b82f6", "ZZS": "#84cc16", "NA": "#22c55e",
        "PRO": "#a855f7", "LPV": "#ef4444", "AS": "#06b6d4",
        "ST": "#f97316", "S!": "#f97316", "LA": "#14b8a6",
        "K": "#f59e0b",
    }
    factions_sorted = sorted(factions_seen, key=lambda f: faction_sort_key(f))
    faction_objects = []
    # Index politicians by faction
    pols_by_faction: dict[str, list] = {}
    for p in politicians:
        pols_by_faction.setdefault(p["faction"], []).append(p)

    # Also build a pid→politician lookup for JS
    politicians_by_pid: dict[int, dict] = {}
    for p in politicians:
        # Find dissenting votes (where politician voted differently from faction majority)
        dissenting = []
        for i, ventry in enumerate(p["votes"]):
            vtype = ventry["vote_type"]
            if not vtype or vtype == "Nebalsoja":
                continue
            # Get faction breakdown for this vote
            vc = vote_columns[i]
            fb = vc.get("faction_breakdown", [])
            faction_fb = next((f for f in fb if f["faction"] == p["faction"]), None)
            if faction_fb:
                # Determine faction majority
                counts = {"Par": faction_fb["par"], "Pret": faction_fb["pret"], "Atturas": faction_fb["atturas"]}
                majority = max(counts, key=lambda k: counts[k])
                if vtype != majority and counts[majority] > 1:
                    dissenting.append({
                        "motif": vc["motif"][:80],
                        "date": vc["date"],
                        "vote": vtype,
                        "faction_majority": majority,
                    })
        politicians_by_pid[p["pid"]] = {
            "name": p["name"],
            "faction": p["faction"],
            "slug": p["slug"],
            "par": p["summary"]["par"],
            "pret": p["summary"]["pret"],
            "atturas": p["summary"]["atturas"],
            "nebalso": p["summary"]["nebalso"],
            "attendance_pct": p["summary"]["attendance_pct"],
            "dissenting_votes": dissenting,
        }

    for f in factions_sorted:
        members = []
        for p in pols_by_faction.get(f, []):
            # Flatten votes to simple list of vote_type strings for Jinja2
            members.append({
                "id": p["pid"],
                "name": p["name"],
                "slug": p["slug"],
                "votes": [v["vote_type"] for v in p["votes"]],
            })
        faction_objects.append({
            "name": f,
            "short": f,
            "color": FACTION_COLORS.get(f, "#8b8fa3"),
            "coalition_status": _coalition_map.get(f, "other"),
            "members": members,
        })

    return {
        "votes": vote_columns,
        "factions": faction_objects,
        "politicians": politicians_by_pid,
    }


def _build_matrix_compact(
    matrix_data: dict[str, Any], all_dates: list[str] | None = None
) -> dict[str, Any]:
    """Transform _build_matrix_data() output into the compact JSON shape.

    The compact form is designed for client-side virtualization: each tracked
    deputy's votes collapse from a list of strings (one per vote column) into
    a single string of `len(votes)` chars (P/N/A/X/.). Faction breakdowns and
    vote metadata get shorter key names. See plan
    docs/superpowers/plans/2026-05-28-balsojumi-virtualization.md § Datu formāts.

    Pure transform — no DB access. Tested in isolation via
    tests/test_render_votes_matrix_json.py.
    """
    votes_in = matrix_data.get("votes", [])
    factions_in = matrix_data.get("factions", [])
    politicians_in = matrix_data.get("politicians", {})

    votes_compact: list[dict[str, Any]] = []
    for v in votes_in:
        fb_compact = [
            {
                "f": fb.get("faction", ""),
                "p": fb.get("par", 0) or 0,
                "n": fb.get("pret", 0) or 0,
                "a": fb.get("atturas", 0) or 0,
                "x": fb.get("nebalso", 0) or 0,
            }
            for fb in v.get("faction_breakdown", []) or []
        ]
        entry: dict[str, Any] = {
            "i": len(votes_compact),
            "vid": v.get("id"),
            "d": v.get("date") or "",
            "t": v.get("time") or "",
            "m": v.get("motif") or "",
            "r": v.get("result") or "",
            "tp": v.get("topic") or "",
            "tot": [
                v.get("total_par", 0) or 0,
                v.get("total_pret", 0) or 0,
                v.get("total_atturas", 0) or 0,
            ],
            "uni": bool(v.get("is_unanimous")),
            "f": fb_compact,
        }
        if _is_procedural_vote(v):
            entry["proc"] = True
        # Optional fields — only emit when non-empty to save bytes.
        if v.get("summary"):
            entry["s"] = v["summary"]
        if v.get("url"):
            entry["url"] = v["url"]
        if v.get("document_url"):
            entry["doc_url"] = v["document_url"]
        if v.get("document_nr"):
            entry["doc_nr"] = v["document_nr"]
        # Bill link target for TAB-1 archive cards. bsl = bill slug
        # (likumprojekti/<slug>.html), bnr = bill document number label.
        if v.get("bill_slug"):
            entry["bsl"] = v["bill_slug"]
        if v.get("bill_doc_nr"):
            entry["bnr"] = v["bill_doc_nr"]
        votes_compact.append(entry)

    # Faction → member-id lookup. Members' full details (name, slug, vote
    # string) live in the politicians dict; factions just enumerate members
    # in their canonical display order.
    factions_compact = [
        {
            "f": f.get("name", ""),
            "c": f.get("color", ""),
            "cs": f.get("coalition_status", "other"),
            "m": [m["id"] for m in f.get("members", []) if m.get("id") is not None],
        }
        for f in factions_in
    ]

    # Build per-politician vote string from the faction-member list (which
    # carries `votes: [vote_type_str, ...]` in vote-column order).
    pid_to_votes: dict[int, list[str | None]] = {}
    for f in factions_in:
        for m in f.get("members", []):
            pid = m.get("id")
            if pid is None:
                continue
            pid_to_votes[pid] = m.get("votes", [])

    # Index votes by date for O(1) dissent lookup. The dissenting_votes entries
    # from _build_matrix_data carry only date + motif-prefix-80 — we re-locate
    # the vote column index here. Pre-bucketing by date turns ~11M comparisons
    # at full scale (5703 votes × 100 deputies × ~20 dissents) into ~2k.
    votes_by_date: dict[str, list[dict[str, Any]]] = {}
    for vc in votes_compact:
        votes_by_date.setdefault(vc["d"], []).append(vc)

    politicians_compact: dict[str, dict[str, Any]] = {}
    n_vote_cols = len(votes_compact)
    for pid_str, pol in politicians_in.items():
        pid = int(pid_str) if isinstance(pid_str, str) else pid_str
        vote_list = pid_to_votes.get(pid, [])
        vote_str = "".join(_encode_vote_char(vt) for vt in vote_list)
        # Defensive pad — if for any reason the per-politician list is shorter
        # than vote_columns (shouldn't happen, but guards regressions), fill
        # with '.' so client-side index alignment never breaks.
        if len(vote_str) < n_vote_cols:
            vote_str += "." * (n_vote_cols - len(vote_str))
        elif len(vote_str) > n_vote_cols:
            vote_str = vote_str[:n_vote_cols]

        dis_compact: list[dict[str, Any]] = []
        for dv in pol.get("dissenting_votes", []) or []:
            idx = _find_vote_index_by_date_motif(
                votes_compact, dv.get("date"), dv.get("motif"), votes_by_date
            )
            if idx < 0:
                continue
            dis_compact.append({
                "i": idx,
                "v": _VOTE_CHAR_MAP.get(dv.get("vote", ""), "X"),
                "fm": _VOTE_CHAR_MAP.get(dv.get("faction_majority", ""), "X"),
            })

        politicians_compact[str(pid)] = {
            "n": pol.get("name", ""),
            "f": pol.get("faction", ""),
            "s": pol.get("slug", ""),
            "v": vote_str,
            "sum": [
                pol.get("par", 0) or 0,
                pol.get("pret", 0) or 0,
                pol.get("atturas", 0) or 0,
                pol.get("nebalso", 0) or 0,
            ],
            "att": pol.get("attendance_pct", 0) or 0,
            "dis": dis_compact,
        }

    # Full session-date list (newest-first) for the matrix session dropdown.
    # Passed in so BOTH shards (recent + full) advertise every session — the
    # recent shard otherwise lists only its own ~400-day window, leaving older
    # sessions unselectable until the full archive loads. When absent, derive
    # from the shard's own votes (keeps unit tests / standalone use working).
    if all_dates is None:
        all_dates = sorted(
            {v["d"] for v in votes_compact if v.get("d")}, reverse=True
        )

    return {
        "meta": {
            "version": 1,
            "generated_at": now_lv_dt().isoformat(timespec="seconds"),
            "votes_total": n_vote_cols,
            "encoding": "P=Par,N=Pret,A=Atturas,X=Nebalsoja,.=absent",
            "all_dates": all_dates,
        },
        "votes": votes_compact,
        "factions": factions_compact,
        "politicians": politicians_compact,
    }


def _find_vote_index_by_date_motif(
    votes_compact: list[dict[str, Any]],
    date_str: str | None,
    motif: str | None,
    votes_by_date: dict[str, list[dict[str, Any]]] | None = None,
) -> int:
    """Locate a vote index in the compact list by date + motif prefix match.

    `_build_matrix_data` stores `dissenting_votes` entries with motif truncated
    to 80 chars and only `date` (no vote id). To convert to compact form we
    re-derive the column index. Optional ``votes_by_date`` pre-bucket reduces
    the search from O(votes) per dissent to O(votes_per_date) (~1–5).
    """
    if not date_str:
        return -1
    motif_prefix = (motif or "")[:80]
    if votes_by_date is not None:
        candidates = votes_by_date.get(date_str, [])
    else:
        candidates = [v for v in votes_compact if v.get("d") == date_str]
    for v in candidates:
        if (v.get("m") or "").startswith(motif_prefix):
            return v["i"]
    return -1


def _emit_matrix_json(
    matrix_data: dict[str, Any],
    atmina_dir: Path,
    basename: str = "balsojumi-matrica",
    all_dates: list[str] | None = None,
) -> Path:
    """Write the compact matrix JSON to ``atmina/data/<basename>.json``.

    ``basename`` defaults to the full archive; the recent shard passes
    ``basename="balsojumi-matrica-recent"``. ``all_dates`` (full session-date
    list, newest-first) is threaded into ``meta.all_dates`` so the recent
    shard's session dropdown still advertises every session. Side effect:
    creates the `data/` subdir if missing. Idempotent — overwrites file each
    render. SSR matrix in the template is unaffected (parallel artifact).
    """
    compact = _build_matrix_compact(matrix_data, all_dates=all_dates)
    data_dir = atmina_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / f"{basename}.json"
    payload = json.dumps(
        compact, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    # Pre-compress for serving via .htaccess rewrite — LiteSpeed shared host
    # does not auto-compress application/json. Brotli + gzip variants let
    # the rewrite rule pick the best for the Accept-Encoding header.
    # See assets/htaccess.template — the same pattern serves pozicijas-data.json.
    _emit_json_compressed(payload, dest)
    logger.info(
        "Wrote matrix JSON: %d votes × %d politicians → %s (%d raw, %d br, %d gz)",
        compact["meta"]["votes_total"],
        len(compact["politicians"]),
        dest,
        dest.stat().st_size,
        (data_dir / f"{basename}.json.br").stat().st_size,
        (data_dir / f"{basename}.json.gz").stat().st_size,
    )
    return dest


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
    # docs/superpowers/plans/2026-06-03-balsojumi-archive-filter.md.
    vote_topics = sorted(set(v["topic"] for v in votes if v.get("topic")))
    # Deputy filter options: every tracked politician who has cast a vote. Same
    # source table as the matrix JSON politicians (`n` field), so the names the
    # filter emits match the archive cards' data-deputies exactly. (Was derived
    # from per-vote tracked_votes before the Option-2 SSR-card removal.)
    deputies = [
        row["name"] for row in db.execute("""
            SELECT DISTINCT tp.name FROM saeima_individual_votes siv
            JOIN tracked_politicians tp ON tp.id = siv.politician_id
            ORDER BY tp.name
        """).fetchall()
    ]
    vote_sessions = sorted(
        {str(v["vote_date"])[:10] for v in votes if v.get("vote_date")},
        reverse=True,
    )
    # Step 2 of balsojumi virtualization: the SSR matrix block + matrix_json
    # embed are removed from the template. Only the compact JSON artifact
    # is emitted; the client (assets/bmv1.js) fetches it lazily when the user
    # opens the Matrica subtab. See docs/superpowers/plans/2026-05-28-...md.
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
    vote_accepted = 0
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
        if v.get("result") == "Pieņemts":
            vote_accepted += 1
    vote_accepted_pct = round(100 * vote_accepted / vote_total) if vote_total else 0

    vote_metrics = {
        "total": vote_total,
        "last_week": vote_last_week,
        "accepted_pct": vote_accepted_pct,
    }

    bill_topics = sorted({b["topic"] for b in bills if b["topic"]})

    _render_page(env, "balsojumi.html.j2", atmina_dir / "balsojumi.html", {
        "vote_topics": vote_topics,
        "deputies": deputies,
        "vote_sessions": vote_sessions,
        "metrics": vote_metrics,
        "bills": bills,
        "bill_topics": bill_topics,
        "laws_index_count": laws_index_count,
    })
