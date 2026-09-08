"""Vote matrix pipeline for the balsojumi page (carve-out of ``src.render.votes``).

Phase 5.5 of docs/plans/2026-09-05-strukturas-tirisanas-plans.md — a pure
move of the matrix data pipeline (former ``votes.py`` L253-690) plus the
vote-char / faction-order / procedural-motif leaves it depends on. No
behaviour change; ``src.render.votes`` re-imports every name below so the
historical import path ``from src.render.votes import _build_matrix_data``
keeps working (tests and scripts rely on it).

Builds the deputy attendance matrix consumed by ``assets/bmv1.js``:
``balsojumi-matrica.json`` (full archive) + ``balsojumi-matrica-recent.json``
(the ~400-day shard). Imports only ``src.render._common`` (leaf) and
``src.db`` — never a peer page module, so the partial-init contract in
``src/render/__init__.py`` holds.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.db import now_lv_dt
from src.render._common import (
    _emit_json_compressed,
    _slugify,
)

logger = logging.getLogger(__name__)



# Vote-string encoding for the compact matrix JSON.
# See docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md § "Datu formāts".
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

# Matrix group for politicians who never sat in any faction for a recorded vote.
# Everyone else groups under their LATEST non-empty per-vote faction — see
# politician_map construction in _build_matrix_data.
OUTSIDE_FACTION = "Ārpus frakcijām"

# Canonical faction display order — coalition-ish alphabetical grouping used by
# BOTH the matrix rows and the TAB-1 deputy filter's group headers, so a deputy
# sits in the same place in both surfaces. Anything unlisted sorts after,
# alphabetically (OUTSIDE_FACTION included).
FACTION_ORDER = ["AS", "JV", "LPV", "NA", "PRO", "ZZS"]


def _faction_sort_key(faction: str) -> tuple:
    """(rank, name) — canonical factions first in FACTION_ORDER, rest A→Z."""
    try:
        return (0, FACTION_ORDER.index(faction))
    except ValueError:
        return (1, faction)

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

def _build_matrix_data(db: sqlite3.Connection, votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build vote matrix data for the balsojumi matrix visualization.

    Returns a dict with vote_columns (chronological ASC), politicians (grouped
    by faction, sorted by name), and a sorted factions list.
    """
    # Preferred faction order; anything else sorts alphabetically after these
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

    # Build per-politician data: {pid: {name, faction, votes_by_vid}}.
    # Faction = the politician's LATEST non-empty per-vote faction, not the
    # first row's — first-row-wins dropped ministers with suspended mandates and
    # non-attached deputies (first row faction NULL → faction "" → excluded from
    # every faction member list → their ENTIRE vote string emitted as '.'; the
    # Siliņa/Ašeradens class, fixed 2026-08-21). Latest beats most-common so
    # faction switchers (Ābrama PRO→ZZS, Šmits AS→ST) group under their current
    # faction. Politicians with no non-empty faction anywhere get the synthetic
    # OUTSIDE_FACTION group so they stay in the matrix. Per-vote faction truth
    # still lives in each individual row.
    latest_faction: dict[int, str] = {
        row["politician_id"]: row["faction"]
        for row in db.execute("""
            SELECT siv.politician_id, siv.faction
            FROM saeima_individual_votes siv
            JOIN saeima_votes sv ON sv.id = siv.vote_id
            WHERE siv.politician_id IS NOT NULL
              AND siv.faction IS NOT NULL AND siv.faction != ''
            ORDER BY sv.vote_date ASC, sv.vote_time ASC
        """).fetchall()
    }  # ASC scan → the dict keeps each pid's LAST (newest) faction
    politician_map: dict[int, dict[str, Any]] = {}
    for row in iv_rows:
        pid = row["politician_id"]
        if pid not in politician_map:
            politician_map[pid] = {
                "pid": pid,
                "name": row["name"],
                "faction": latest_faction.get(pid, OUTSIDE_FACTION),
                "votes_by_vid": {},
            }
        politician_map[pid]["votes_by_vid"][row["vote_id"]] = row["vote"]

    # --- build politician entries with full vote arrays and summaries ---
    faction_sort_key = _faction_sort_key

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
        "K": "#f59e0b", OUTSIDE_FACTION: "#8b8fa3",
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
    docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md § Datu formāts.

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
