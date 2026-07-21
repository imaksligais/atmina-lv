"""P3 Phase 2 — Saeimas vēsturisko balsojumu backfill year-by-year.

Embedded Playwright loop with JS-based DOM extraction. Reads
data/saeima_backfill_sessions.json, filters by --year, walks each session:
agenda page → extract vote URLs → per-vote JS extraction → construct
VoteResult → store_vote → generate_claims_from_votes (sentinel summary).

Idempotent via saeima_votes.url UNIQUE — re-runs skip already-stored votes.

Sentinel summary: "Kopsavilkums nav pieejams — historic backfill 2026-05-26"
  - generate_claims_from_votes detects this prefix and falls back to the
    motif-based stance so the UI doesn't surface the sentinel text.

Usage:
    python scripts/p3_backfill_year.py --year 2025
    python scripts/p3_backfill_year.py --year 2025 --limit 5  # smoke test
    python scripts/p3_backfill_year.py --year 2025 --session-uuid <UUID>

Per-year log: data/p3_backfill_{year}.log (append).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db import DB_PATH as _DEFAULT_DB_PATH, get_db, now_lv  # noqa: E402
from src.saeima import (  # noqa: E402
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    init_saeima_tables,
    match_deputies_to_politicians,
    store_vote,
    _motif_to_topic,
    _resolve_vote_url,
)

MANIFEST_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"
DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
SENTINEL_SUMMARY = "Kopsavilkums nav pieejams — historic backfill 2026-05-26"

SAEIMA_BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"

_VOTE_URL_RE = re.compile(r"\./0/[A-F0-9]{32}\?OpenDocument")
_DOC_NR_RE = re.compile(r"\((\d+/(?:Lp14|Lm14|P14))\)")
_BILL_LIKE_RE = re.compile(r"\(\d+/L[pm]14\)")


def _extract_doc_nr(motif: str) -> str | None:
    if not motif:
        return None
    m = _DOC_NR_RE.search(motif)
    return m.group(1) if m else None


def _is_bill_type(motif: str) -> bool:
    return bool(_BILL_LIKE_RE.search(motif or ""))


# JS extractor for vote pages — runs in browser context post-render.
# Returns: {motif, par, pret, atturas, date, time, result, deputies[]}
JS_VOTE_EXTRACT = r"""
() => {
  const allText = document.body.innerText;
  const motifMatch = allText.match(/Balsošanas\s*motīvs:\s*([^\n]+)/);
  const motif = motifMatch ? motifMatch[1].trim() : null;
  const totalsMatch = allText.match(/par\s+(\d+),\s*pret\s+(\d+),\s*atturas\s+(\d+)/);
  const dtMatch = allText.match(/Datums:\s*(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})/);
  const resultMatch = allText.match(/(Pieņemts|Noraidīts)/);

  const validVote = v => ['Par','Pret','Atturas','Nebalsoja'].includes(v);
  const deputies = [];
  const seen = new Set();

  document.querySelectorAll('table tr').forEach(r => {
    const cells = Array.from(r.querySelectorAll('td')).map(c => (c.innerText || '').trim());
    if (cells.some(c => c === 'Vārds' || c === 'Frakcija' || c === 'Balss')) return;
    for (let i = 0; i < cells.length; i++) {
      if (/^\d+\.$/.test(cells[i])) continue;
      if (/^(PAR|PRET|ATTURAS|NEBALSO):/.test(cells[i])) continue;
      if (cells[i] === '' || ['Vārds','Frakcija','Balss'].includes(cells[i])) continue;
      if (!/[a-zA-ZāčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ]/.test(cells[i])) continue;
      const name = cells[i];
      if (i+2 < cells.length && validVote(cells[i+2])) {
        const dedup = name + '|' + cells[i+1] + '|' + cells[i+2];
        if (!seen.has(dedup)) { seen.add(dedup); deputies.push({name, faction: cells[i+1] || null, vote: cells[i+2]}); }
        i += 2; continue;
      }
      if (i+1 < cells.length && validVote(cells[i+1])) {
        const dedup = name + '||' + cells[i+1];
        if (!seen.has(dedup)) { seen.add(dedup); deputies.push({name, faction: null, vote: cells[i+1]}); }
        i += 1; continue;
      }
    }
  });

  return {
    motif,
    par: totalsMatch ? parseInt(totalsMatch[1]) : 0,
    pret: totalsMatch ? parseInt(totalsMatch[2]) : 0,
    atturas: totalsMatch ? parseInt(totalsMatch[3]) : 0,
    date: dtMatch ? dtMatch[1] : null,
    time: dtMatch ? dtMatch[2] : null,
    result: resultMatch ? resultMatch[1] : null,
    deputies,
  };
}
"""

# JS extractor for agenda page — return list of vote URLs (relative).
JS_AGENDA_VOTE_URLS = r"""
() => {
  const set = new Set();
  document.querySelectorAll('a[href]').forEach(a => {
    const m = a.getAttribute('href').match(/^\.\/0\/[A-F0-9]{32}\?OpenDocument/);
    if (m) set.add(m[0]);
  });
  // Fallback: full body innerText if anchor scan empty
  if (set.size === 0) {
    const re = /\.\/0\/[A-F0-9]{32}\?OpenDocument/g;
    const text = document.body.innerHTML || '';
    let m;
    while ((m = re.exec(text)) !== null) set.add(m[0]);
  }
  return Array.from(set);
}
"""


def _log(log_file: Path, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _vote_already_stored(url: str) -> bool:
    """Idempotency check — saeima_votes.url is UNIQUE."""
    full = _resolve_vote_url(url)
    db = sqlite3.connect(DB_PATH)
    row = db.execute("SELECT 1 FROM saeima_votes WHERE url = ?", (full,)).fetchone()
    db.close()
    return row is not None


def _to_vote_result(data: dict, vote_url: str) -> VoteResult:
    """Build VoteResult from JS extractor output."""
    iso_date = None
    if data.get("date"):
        try:
            dd, mm, yyyy = data["date"].split(".")
            iso_date = f"{yyyy}-{mm}-{dd}"
        except ValueError:
            iso_date = None

    individual_votes: list[IndividualVote] = []
    nebalso_count = 0
    for d in data.get("deputies") or []:
        iv = IndividualVote(
            deputy_name=d["name"],
            faction=d.get("faction"),
            vote=d.get("vote") or "",
        )
        if iv.vote == "Nebalsoja":
            nebalso_count += 1
        individual_votes.append(iv)

    vote = VoteResult(
        motif=data.get("motif") or "",
        date=iso_date,
        time=data.get("time"),
        total_par=data.get("par", 0),
        total_pret=data.get("pret", 0),
        total_atturas=data.get("atturas", 0),
        total_nebalso=nebalso_count,
        result=data.get("result"),
        url=vote_url,
        individual_votes=individual_votes,
    )

    # Fallback result computation per Latvian rule (klātesošo vairākums)
    if not vote.result:
        present = (vote.total_par + vote.total_pret
                   + vote.total_atturas + vote.total_nebalso)
        threshold = present // 2
        vote.result = "Pieņemts" if vote.total_par > threshold else "Noraidīts"

    return vote


def _process_vote(vote_url: str, data: dict, log_file: Path) -> dict | None:
    """Construct VoteResult from JS extract, match deputies, store, emit claims."""
    vote = _to_vote_result(data, vote_url)
    if not vote.motif:
        _log(log_file, f"    SKIP {vote_url}: empty motif")
        return None
    if not vote.individual_votes:
        _log(log_file, f"    SKIP {vote_url}: 0 deputies extracted (likely paziņojuma page)")
        return None

    # 1. Match deputies
    match_deputies_to_politicians(vote.individual_votes, DB_PATH)

    # 2. Determine sentinel summary for bill-type votes
    summary = SENTINEL_SUMMARY if _is_bill_type(vote.motif) else None
    doc_nr = _extract_doc_nr(vote.motif)

    # 3. Store vote
    vote_db_id = store_vote(
        vote, agenda_item_id=None, db_path=DB_PATH,
        summary=summary,
        document_url=None,
        document_nr=doc_nr,
    )

    # 4. Generate claims
    claim_ids = generate_claims_from_votes(vote, vote_db_id, DB_PATH)

    matched = sum(1 for iv in vote.individual_votes if iv.politician_id)
    return {
        "vote_db_id": vote_db_id,
        "motif": vote.motif,
        "totals": (vote.total_par, vote.total_pret, vote.total_atturas, vote.total_nebalso),
        "total_deputies": len(vote.individual_votes),
        "matched": matched,
        "claims": len(claim_ids),
    }


def process_session(page, session: dict, year: int, log_file: Path) -> dict:
    """Process a single session end-to-end. Returns per-session report."""
    uuid = session["uuid"]
    date_str = f"{session['year']}-{session['month']:02d}-{session['day']:02d}"
    session_type = session["session_type"]

    if session_type == "jautajumi":
        _log(log_file, f"  SKIP jautājumi session {date_str} {uuid}")
        return {"skipped_jautajumi": True}

    # Step 1: agenda → extract vote URLs
    agenda_url = f"{SAEIMA_BASE}/DK?ReadForm&nr={uuid}"
    try:
        page.goto(agenda_url, timeout=45000, wait_until="load")
    except Exception as e:
        _log(log_file, f"  FAIL agenda goto {date_str} {uuid} err={e}")
        return {"agenda_failed": True}

    try:
        rel_urls = page.evaluate(JS_AGENDA_VOTE_URLS)
    except Exception as e:
        _log(log_file, f"  FAIL agenda evaluate {date_str} {uuid} err={e}")
        return {"agenda_failed": True}

    vote_urls = [f"{SAEIMA_BASE}{u[1:]}" for u in rel_urls]
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
            page.goto(vote_url, timeout=45000, wait_until="load")
            data = page.evaluate(JS_VOTE_EXTRACT)
        except Exception as e:
            report["votes_failed"] += 1
            _log(log_file, f"    FAIL idx={idx} url={vote_url} err={e}")
            continue

        try:
            res = _process_vote(vote_url, data, log_file)
        except Exception as e:
            report["votes_failed"] += 1
            _log(log_file, f"    FAIL process idx={idx} url={vote_url} err={e}")
            continue

        if res is None:
            continue

        report["votes_processed"] += 1
        report["individual_total"] += res["total_deputies"]
        report["individual_matched"] += res["matched"]
        report["claims_generated"] += res["claims"]

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
    ap.add_argument("--limit", type=int, default=0, help="Max sessions to process")
    ap.add_argument("--session-uuid", type=str, default=None, help="Single session by UUID")
    ap.add_argument("--no-headless", dest="headless", action="store_false", default=True)
    args = ap.parse_args()

    init_saeima_tables(DB_PATH)
    log_file = REPO_ROOT / "data" / f"p3_backfill_{args.year}.log"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sessions = [s for s in manifest if s["year"] == args.year]
    if args.session_uuid:
        sessions = [s for s in sessions if s["uuid"] == args.session_uuid]
    elif args.limit > 0:
        sessions = sessions[: args.limit]

    _log(log_file, f"==== P3 backfill year={args.year} sessions={len(sessions)} ====")
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

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        for s in sessions:
            try:
                rpt = process_session(page, s, args.year, log_file)
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

        browser.close()

    elapsed = time.time() - start_time
    _log(log_file, "")
    _log(log_file, f"==== {args.year} backfill DONE in {elapsed/60:.1f} min ====")
    for k, v in overall.items():
        _log(log_file, f"  {k}: {v}")
    if overall["individual_total"]:
        rate = 100.0 * overall["individual_matched"] / overall["individual_total"]
        _log(log_file, f"  match_rate: {rate:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
