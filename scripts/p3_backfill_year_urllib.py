"""P3 Phase 2 — pure-urllib backfill (no Playwright dependency).

Discovered 2026-05-27 night: the JS-rendered titania pages serve their data
inside the source HTML — agenda page contains `addVotesLink("DKP","VOTE",...)`
calls, vote page contains `var voteFullListByNames = [...]` with all deputies
URL-encoded. So a plain urllib fetch + regex parse is sufficient.

This is the fallback for environments where Playwright cannot run (no chromium,
network sandboxing, etc.) and the preferred tool for unattended bulk runs
(no browser startup overhead, ~3x faster).

Same idempotency + sentinel-summary contract as p3_backfill_year.py — DB-side
behavior is identical, only the transport changes.

Usage:
    python scripts/p3_backfill_year_urllib.py --year 2025
    python scripts/p3_backfill_year_urllib.py --year 2024 --limit 5
    python scripts/p3_backfill_year_urllib.py --year 2025 --session-uuid <U>

Per-year log: data/p3_backfill_{year}.log (append, shared with Playwright tool).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.saeima import (  # noqa: E402
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    init_saeima_tables,
    match_deputies_to_politicians,
    store_vote,
    _resolve_vote_url,
)

MANIFEST_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"
DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
SENTINEL_SUMMARY = "Kopsavilkums nav pieejams — historic backfill 2026-05-26"

SAEIMA_BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"
USER_AGENT = "atmina/P3-backfill (+https://atmina.lv)"
HTTP_TIMEOUT = 30  # seconds

# Agenda vote links appear in THREE layouts (union all — checking only one is
# how the 2026-06-04 session was silently missed; sk. saeima-tracker.md 2.B):
#  1. static `./0/{HEX32}?OpenDocument` anchors (older sessions),
#  2. JS `addVotesLink("DKP","VOTE","hidden","cand","byCard")` calls (newer DK),
#  3. `./Voting?ReadForm&parentID={GUID}` links (2026-06-11+). NB: these vote
#     pages carry NO result label — `_to_vote_result` computes the result from
#     the attendance-majority fallback. NB2 (verified 2026-06-12): titania
#     serves the embedded vote data on these pages only while the session is
#     "actual" — one day later the same URL returns empty voteFullListByNames
#     (`&tm=` variants don't unlock it either). A late backfill therefore
#     DISCOVERS the votes but each fetch logs a visible `SKIP … empty data`
#     failure instead of silently missing the session. ReadForm-era sessions
#     must be ingested same-day (the daily @saeima-tracker flow does).
_STATIC_VOTE_RE = re.compile(r'\./0/([A-F0-9]{32})\?OpenDocument')
_ADD_VOTES_RE = re.compile(r'addVotesLink\("([A-F0-9]{32})","([A-F0-9]{32})"')
_VOTING_READFORM_RE = re.compile(
    r'\./Voting\?ReadForm&(?:amp;)?parentID=([A-Fa-f0-9-]{36})'
)

# Vote page embeds full deputy list in `var voteFullListByNames=["...","...",...]`
# Each entry URL-encoded with 0xFF byte separator (rendered as U+FFFD in UTF-8).
_VOTE_LIST_RE = re.compile(r'var\s+voteFullListByNames\s*=\s*(\[.*?\]);', re.DOTALL)
_VOTE_ENTRY_RE = re.compile(r'"([^"]*)"')
# Field separator: 0xFF byte → decoded as U+FFFD when force-utf8
_FIELD_SEP = "�"

# Motif extraction handles two layouts:
#  (a) inline after label:  "Balsošanas motīvs: <MOTIF_TEXT>\n"
#  (b) in next <b> tag:     "<span>Balsošanas motīvs: </span><b>MOTIF_TEXT</b>"
# We try (b) first because that's the standard titania form; (a) is a fallback
# for any older/variant pages.
_MOTIF_BTAG_RE = re.compile(
    r'Balso(?:&#353;|š)anas\s*mot(?:&#299;|ī)vs:?\s*</span>\s*<b>([^<]+)</b>',
    re.IGNORECASE,
)
_MOTIF_INLINE_RE = re.compile(
    r'Balso(?:&#353;|š)anas\s*mot(?:&#299;|ī)vs:?\s*([^<\n]+)', re.IGNORECASE,
)
_TOTALS_RE = re.compile(r'par\s+(\d+),\s*pret\s+(\d+),\s*atturas\s+(\d+)')
# Datums label is followed by HTML tags before the value: "Datums: </span><b>DD.MM.YYYY HH:MM:SS </b>".
# Allow up to ~50 chars of intermediate HTML between the label and the date.
_DATETIME_RE = re.compile(
    r'Datums:?\s*(?:<[^>]*>\s*){0,5}(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})'
)
# Result label lives in a dedicated red-text span next to "Balsošanas rezultāti".
# Generic Pieņemts/Noraidīts regex hits JS string literals (e.g. `hideSend2Com['Noraidīts']=true`),
# so we scope to the span. If span is empty, fall back to compute-from-totals.
_RESULT_RE = re.compile(
    r'<span[^>]*color\s*:\s*red[^>]*>\s*(Pieņemts|Noraidīts)\s*</span>',
    re.IGNORECASE,
)

_DOC_NR_RE = re.compile(r"\((\d+/(?:Lp14|Lm14|P14))\)")
_BILL_LIKE_RE = re.compile(r"\(\d+/L[pm]14\)")


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def _extract_vote_urls_from_agenda(agenda_html: str) -> list[str]:
    """Extract unique vote URLs from all three agenda layouts (union, deduped).

    Patterns 1–2 yield HEX32 ids → built as `/0/{HEX}?OpenDocument`; pattern 3
    yields a GUID → built as `/Voting?ReadForm&parentID={GUID}` (the `./` in
    the agenda anchor resolves against the .nsf base). Preserves first-on-page
    order within each pattern, patterns concatenated 1→2→3.
    """
    seen: set[str] = set()
    out: list[str] = []

    def _add(url: str) -> None:
        if url not in seen:
            seen.add(url)
            out.append(url)

    for m in _STATIC_VOTE_RE.finditer(agenda_html):
        _add(f"{SAEIMA_BASE}/0/{m.group(1)}?OpenDocument")
    for m in _ADD_VOTES_RE.finditer(agenda_html):
        _add(f"{SAEIMA_BASE}/0/{m.group(2)}?OpenDocument")
    for m in _VOTING_READFORM_RE.finditer(agenda_html):
        _add(f"{SAEIMA_BASE}/Voting?ReadForm&parentID={m.group(1)}")
    return out


def _decode_entry(entry: str) -> tuple[str, str | None, str]:
    """Decode one voteFullListByNames entry into (name, faction, vote).

    Entry format: "{idx}.{SEP}{name_urlenc}{SEP}{faction}{SEP}{vote}"
    Faction can be empty string (Saeima Prezidijs members vote without faction).
    """
    parts = entry.split(_FIELD_SEP)
    if len(parts) < 4:
        return ("", None, "")
    name_enc = parts[1].strip()
    faction = parts[2].strip()
    vote = parts[3].strip()
    name = urllib.parse.unquote(name_enc.replace("+", " "))
    return (name, faction or None, vote)


def _parse_vote_page(html: str) -> dict:
    """Parse vote results page HTML into structured dict.

    Returns: {motif, par, pret, atturas, nebalso, date, time, result, deputies[]}
    """
    out = {
        "motif": "",
        "par": 0, "pret": 0, "atturas": 0, "nebalso": 0,
        "date": None, "time": None, "result": None,
        "deputies": [],
    }

    # Motif — try the <b>...</b> form first (standard), fall back to inline.
    import html as _html
    text = _html.unescape(html)
    mm = _MOTIF_BTAG_RE.search(text)
    if not mm:
        mm = _MOTIF_INLINE_RE.search(text)
    if mm:
        out["motif"] = mm.group(1).strip().rstrip('"').rstrip(',').strip()

    tm = _TOTALS_RE.search(text)
    if tm:
        out["par"] = int(tm.group(1))
        out["pret"] = int(tm.group(2))
        out["atturas"] = int(tm.group(3))

    dm = _DATETIME_RE.search(text)
    if dm:
        out["date"] = dm.group(1)
        out["time"] = dm.group(2)

    rm = _RESULT_RE.search(text)
    if rm:
        out["result"] = rm.group(1)

    # Deputies
    vlm = _VOTE_LIST_RE.search(html)
    if vlm:
        raw = vlm.group(1)
        for entry in _VOTE_ENTRY_RE.findall(raw):
            name, faction, vote = _decode_entry(entry)
            if name and vote:
                out["deputies"].append({"name": name, "faction": faction, "vote": vote})
                if vote == "Nebalsoja":
                    out["nebalso"] += 1
    return out


def _to_vote_result(parsed: dict, vote_url: str) -> VoteResult:
    iso_date = None
    if parsed.get("date"):
        try:
            dd, mm, yyyy = parsed["date"].split(".")
            iso_date = f"{yyyy}-{mm}-{dd}"
        except ValueError:
            pass

    individual_votes: list[IndividualVote] = []
    for d in parsed["deputies"]:
        individual_votes.append(IndividualVote(
            deputy_name=d["name"],
            faction=d.get("faction"),
            vote=d.get("vote", ""),
        ))

    vote = VoteResult(
        motif=parsed["motif"],
        date=iso_date,
        time=parsed["time"],
        total_par=parsed["par"],
        total_pret=parsed["pret"],
        total_atturas=parsed["atturas"],
        total_nebalso=parsed["nebalso"],
        result=parsed["result"],
        url=vote_url,
        individual_votes=individual_votes,
    )

    if not vote.result:
        present = (vote.total_par + vote.total_pret
                   + vote.total_atturas + vote.total_nebalso)
        threshold = present // 2
        vote.result = "Pieņemts" if vote.total_par > threshold else "Noraidīts"
    return vote


def _vote_already_stored(url: str) -> bool:
    full = _resolve_vote_url(url)
    db = sqlite3.connect(DB_PATH)
    row = db.execute("SELECT 1 FROM saeima_votes WHERE url = ?", (full,)).fetchone()
    db.close()
    return row is not None


def _extract_doc_nr(motif: str) -> str | None:
    m = _DOC_NR_RE.search(motif or "")
    return m.group(1) if m else None


def _is_bill_type(motif: str) -> bool:
    return bool(_BILL_LIKE_RE.search(motif or ""))


def _log(log_file: Path, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def process_session(session: dict, year: int, log_file: Path) -> dict:
    uuid = session["uuid"]
    date_str = f"{session['year']}-{session['month']:02d}-{session['day']:02d}"
    session_type = session["session_type"]

    if session_type == "jautajumi":
        _log(log_file, f"  SKIP jautājumi session {date_str} {uuid}")
        return {"skipped_jautajumi": True}

    agenda_url = f"{SAEIMA_BASE}/DK?ReadForm&nr={uuid}"
    try:
        agenda_html = _fetch(agenda_url)
    except Exception as e:
        _log(log_file, f"  FAIL agenda fetch {date_str} {uuid} err={e}")
        return {"agenda_failed": True}

    vote_urls = _extract_vote_urls_from_agenda(agenda_html)
    if not vote_urls:
        _log(log_file, f"  empty agenda {date_str} {uuid} ({session_type}) — 0 votes")
        return {"empty_session": True, "votes": 0}

    _log(log_file, f"  {date_str} ({session_type}) — {len(vote_urls)} vote URLs")

    report = {
        "votes_total": len(vote_urls),
        "votes_processed": 0,
        "votes_skipped_existing": 0,
        "votes_failed": 0,
        "individual_total": 0,
        "individual_matched": 0,
        "claims_generated": 0,
    }

    for idx, vote_url in enumerate(vote_urls):
        if _vote_already_stored(vote_url):
            report["votes_skipped_existing"] += 1
            continue

        try:
            html = _fetch(vote_url)
            parsed = _parse_vote_page(html)
        except Exception as e:
            report["votes_failed"] += 1
            _log(log_file, f"    FAIL fetch idx={idx} url={vote_url} err={e}")
            continue

        if not parsed["motif"] or not parsed["deputies"]:
            report["votes_failed"] += 1
            _log(log_file, f"    SKIP idx={idx} empty data (motif='{parsed['motif'][:60]}' deputies={len(parsed['deputies'])})")
            continue

        vote = _to_vote_result(parsed, vote_url)
        match_deputies_to_politicians(vote.individual_votes, DB_PATH)

        summary = SENTINEL_SUMMARY if _is_bill_type(vote.motif) else None
        doc_nr = _extract_doc_nr(vote.motif)

        try:
            vote_db_id = store_vote(
                vote, agenda_item_id=None, db_path=DB_PATH,
                summary=summary, document_url=None, document_nr=doc_nr,
            )
            claim_ids = generate_claims_from_votes(vote, vote_db_id, DB_PATH)
        except Exception as e:
            report["votes_failed"] += 1
            _log(log_file, f"    FAIL store idx={idx} err={e}")
            continue

        matched = sum(1 for iv in vote.individual_votes if iv.politician_id)
        report["votes_processed"] += 1
        report["individual_total"] += len(vote.individual_votes)
        report["individual_matched"] += matched
        report["claims_generated"] += len(claim_ids)

    rate = (100.0 * report["individual_matched"] / report["individual_total"]) if report["individual_total"] else 0.0
    _log(
        log_file,
        f"  done {date_str}: processed={report['votes_processed']}/{report['votes_total']} "
        f"existing={report['votes_skipped_existing']} failed={report['votes_failed']} "
        f"indiv={report['individual_matched']}/{report['individual_total']} ({rate:.1f}%) "
        f"claims={report['claims_generated']}"
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--session-uuid", type=str, default=None)
    args = ap.parse_args()

    init_saeima_tables(DB_PATH)
    log_file = REPO_ROOT / "data" / f"p3_backfill_{args.year}.log"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sessions = [s for s in manifest if s["year"] == args.year]
    if args.session_uuid:
        sessions = [s for s in sessions if s["uuid"] == args.session_uuid]
    elif args.limit > 0:
        sessions = sessions[: args.limit]

    _log(log_file, f"==== P3 urllib backfill year={args.year} sessions={len(sessions)} ====")
    overall = {
        "sessions_total": len(sessions),
        "sessions_processed": 0,
        "sessions_skipped": 0,
        "votes_processed": 0,
        "votes_skipped_existing": 0,
        "votes_failed": 0,
        "individual_total": 0,
        "individual_matched": 0,
        "claims_generated": 0,
    }
    start_time = time.time()

    for s in sessions:
        try:
            rpt = process_session(s, args.year, log_file)
        except Exception as e:
            _log(log_file, f"  SESSION CRASH {s['uuid']} err={e}")
            continue
        if rpt.get("skipped_jautajumi") or rpt.get("empty_session"):
            overall["sessions_skipped"] += 1
            continue
        if rpt.get("agenda_failed"):
            continue
        overall["sessions_processed"] += 1
        overall["votes_processed"] += rpt.get("votes_processed", 0)
        overall["votes_skipped_existing"] += rpt.get("votes_skipped_existing", 0)
        overall["votes_failed"] += rpt.get("votes_failed", 0)
        overall["individual_total"] += rpt.get("individual_total", 0)
        overall["individual_matched"] += rpt.get("individual_matched", 0)
        overall["claims_generated"] += rpt.get("claims_generated", 0)

    elapsed = time.time() - start_time
    _log(log_file, "")
    _log(log_file, f"==== {args.year} urllib backfill DONE in {elapsed/60:.1f} min ====")
    for k, v in overall.items():
        _log(log_file, f"  {k}: {v}")
    if overall["individual_total"]:
        rate = 100.0 * overall["individual_matched"] / overall["individual_total"]
        _log(log_file, f"  match_rate: {rate:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
