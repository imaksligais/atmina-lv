"""Vote matrix pipeline for the balsojumi page (carve-out of ``src.render.votes``).

Phase 5.5 of docs/plans/2026-09-05-strukturas-tirisanas-plans.md — a pure
move of the matrix data pipeline (former ``votes.py`` L253-690) plus the
vote-char / faction-order / procedural-motif leaves it depends on. No
behaviour change; ``src.render.votes`` re-imports every name below so the
historical import path ``from src.render.votes import _build_matrix_data``
keeps working (tests and scripts rely on it).

Builds the compact vote JSON consumed by the vote list (``assets/bmv1.js``;
the deputy×vote Matrica tab that gave these names was removed 2026-10-16):
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
from src.saeima.claims import is_urgency_declaration
from src.render._common import (
    FALLBACK_COLOR,
    PUBLIC_PROFILE_WHERE,
    _emit_json,
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

# Per-VOTE faction-breakdown bucket for ballots cast with no faction (NULL or
# ''; T6 — a deputy may legitimately sit outside every faction). Distinct from
# OUTSIDE_FACTION above, which groups DEPUTIES in the matrix by their latest
# faction. Same label and semantics as src/briefs.py::_NO_FACTION_LABEL (the
# weekly brief's vote breakdown) — tests/test_votes_no_faction_bucket.py keeps
# the two, and the literal in assets/bmv1.js, from drifting apart.
NO_FACTION_LABEL = "ārpusfrakciju"


def vote_faction_label(raw: str | None) -> str:
    """Viena balsojuma frakcijas etiķete: NULL/tukša → ``NO_FACTION_LABEL``.

    VIENĪGĀ normalizācija abām virsmām — balsojuma frakciju joslām (``fb``,
    ``votes.py::_fetch_votes``) un deputāta frakcijai pie balsojuma (``fr``).
    Ja tās atšķirtos, saraksta frakcija nesakristu ar joslas skaitļiem.
    Kanonizāciju (``src.saeima.votes.normalize_faction``) šeit NEatkārto: tā
    notiek ierakstot (T6), un ``fb`` SQL grupēšana to arī neatkārto.
    """
    return (raw or "").strip() or NO_FACTION_LABEL

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

# Klātbūtnes ieraksti (Reģistrējies/Nereģistrējies, totāli 0) nav balsojumi —
# izslēgti no VISĀM balsojumu virsmām (operatora lēmums 2026-07-17): saraksta
# arhīvs (votes.py) un saites.html balsojumu sadaļa (links.py) lieto šo pašu
# filtru, lai katra `balsojumi.html#vote-N` saite vestu uz esošu kartīti.
# Prefiksa filtrs, ne '%reģistrācij%' — tas noķertu īstus balsojumus
# (Civilstāvokļa aktu reģistrācijas likums).
PRESENCE_MOTIF_PREFIXES = ("Deputātu klātbūtnes reģistrācija", "Kvoruma pārbaude")


def presence_motif_exclusion_sql(column: str) -> str:
    """SQL WHERE fragment that drops presence rows by ``column`` (a motif column)."""
    return " AND ".join(f"{column} NOT LIKE '{p}%'" for p in PRESENCE_MOTIF_PREFIXES)


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
    if is_urgency_declaration(motif):  # verdikti 2026-10-14 § C2
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
    from src.coalition import coalition_periods, get_coalition_map
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
                "faction_by_vid": {},
            }
        politician_map[pid]["votes_by_vid"][row["vote_id"]] = row["vote"]
        politician_map[pid]["faction_by_vid"][row["vote_id"]] = vote_faction_label(row["faction"])

    # Publiskais profils — tā pati atlase kā politicians.py::_fetch_politicians.
    public_pids = {
        r[0] for r in db.execute(f"SELECT id FROM tracked_politicians WHERE {PUBLIC_PROFILE_WHERE}")
    }

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
        # Frakcija pie katra balsojuma (None, ja ieraksta nav) — kolonnu secībā.
        vote_factions: list[str | None] = []
        par = pret = atturas = nebalso = 0
        for vid in vote_id_order:
            vtype = p["votes_by_vid"].get(vid)
            vote_list.append({"vote_id": vid, "vote_type": vtype})
            vote_factions.append(p["faction_by_vid"].get(vid))
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
            "vote_factions": vote_factions,
            "public_profile": p["pid"] in public_pids,
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
        "K": "#f59e0b", OUTSIDE_FACTION: FALLBACK_COLOR,
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
        politicians_by_pid[p["pid"]] = {
            "name": p["name"],
            "faction": p["faction"],
            "slug": p["slug"],
            "par": p["summary"]["par"],
            "pret": p["summary"]["pret"],
            "atturas": p["summary"]["atturas"],
            "nebalso": p["summary"]["nebalso"],
            "attendance_pct": p["summary"]["attendance_pct"],
            "vote_factions": p["vote_factions"],
            "public_profile": p["public_profile"],
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
            "color": FACTION_COLORS.get(f, FALLBACK_COLOR),
            "coalition_status": _coalition_map.get(f, "other"),
            "members": members,
        })

    return {
        "votes": vote_columns,
        "factions": faction_objects,
        "politicians": politicians_by_pid,
        # Valdības pēc laika — kartītes «Koalīcija»/«Opozīcija» (_build_matrix_compact → co).
        "coalition_periods": coalition_periods(db),
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
    from src.coalition import coalition_period_index

    votes_in = matrix_data.get("votes", [])
    factions_in = matrix_data.get("factions", [])
    politicians_in = matrix_data.get("politicians", {})
    # Koalīcija balsojuma brīdī: `coalitions` = VISS periodu saraksts (abās
    # šķembās vienāds, lai `co` indekss nozīmē to pašu), `co` = perioda indekss
    # vai None (pirms pirmā zināmā perioda — koalīciju nenosaucam).
    periods = matrix_data.get("coalition_periods") or []

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
            "co": coalition_period_index(periods, v.get("date") or "", v.get("time") or ""),
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

        # Frakcija PIE BALSOJUMA (T6 corollary) kā izpildes kodējums
        # [[startIdx, "FRAKCIJA"], …], indeksēts kā `v`: jauns ieraksts tikai
        # pie maiņas; kolonnas bez ieraksta (`.`) izpildi nepārtrauc. `f` paliek
        # jaunākā frakcija (deputātu grupēšanai), per-vote apgalvojumiem — `fr`.
        fr: list[list[Any]] = []
        for idx, fac in enumerate((pol.get("vote_factions") or [])[:n_vote_cols]):
            if fac is not None and (not fr or fr[-1][1] != fac):
                fr.append([idx, fac])

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
        }
        if fr:
            politicians_compact[str(pid)]["fr"] = fr
        if pol.get("public_profile"):
            politicians_compact[str(pid)]["pp"] = 1

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
        "coalitions": [sorted(p.factions) for p in periods],
    }


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
    _emit_json(payload, dest)
    logger.info(
        "Wrote matrix JSON: %d votes × %d politicians → %s (%d bytes)",
        compact["meta"]["votes_total"],
        len(compact["politicians"]),
        dest,
        dest.stat().st_size,
    )
    return dest
