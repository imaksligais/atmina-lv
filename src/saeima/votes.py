"""Saeimas balsojumu pipeline: parse → match → store → claim → orchestrate.

F4.3 izvilkts no src/saeima.py monolīta. Satur:
- IndividualVote / VoteResult dataclases (vote snapshot output shape)
- parse_vote_snapshot — Playwright accessibility tree → VoteResult
- _build_name_index + match_deputies_to_politicians + match_submitters_to_politicians
  — politiķu name-to-id matching, koplietojams starp vote ledger un bill submitter linkage
- store_vote — saeima_votes + saeima_individual_votes insert
- generate_claims_from_votes — saeima-vote claims (saskaņā ar CLAUDE.md punkts 4
  un punkts 6: claim_type='saeima_vote', document_id=NULL)
- process_vote_snapshot — agenta-vērsts orchestrator (parse → match → store → claim)

DEVIATION NO PLĀNA: `match_submitters_to_politicians` un `generate_claims_from_votes`
plāns paredzēja attiecīgi `bills.py` un `claims.py` lokācijā. Pārvietoti šurp:
- `match_submitters_to_politicians` koplieto `_build_name_index` ar `match_deputies_to_politicians`,
  abi dabiski grupējas; turot `match_submitters_*` `bills.py` būtu prasījis cikla
  bills→votes→bills.
- `generate_claims_from_votes` operē uz `VoteResult` un izsauc visu vote pipeline-u;
  turot to `claims.py` būtu prasījis cikla votes ↔ claims pār `VoteResult` import.
  `claims.py` paliek tīrs leaf-modulis ar topic mapping helperiem.

Aģentu līgums (`@saeima-tracker` prompt + scripts/backfill_*.py) turpina importēt no
`src.saeima` top-level via __init__.py re-export — strukturālā pārvietošana
nemaina publisko API.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src.db import get_db, log_action, now_lv
from src.saeima.bills import _parse_vote_datetime, _resolve_vote_url
from src.saeima.claims import _motif_to_topic, _vote_salience


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class IndividualVote:
    """One deputy's vote in a single ballot."""
    deputy_name: str
    faction: Optional[str] = None             # LPV, ZZS, JV, NA, AS, PRO, etc.
    vote: str = ""                            # Par, Pret, Atturas, Nebalsoja
    politician_id: Optional[int] = None       # FK to tracked_politicians (if matched)


@dataclass
class VoteResult:
    """Full voting result for one agenda item."""
    motif: str                                # What was voted on
    date: Optional[str] = None                # dd.mm.yyyy
    time: Optional[str] = None                # hh:mm:ss
    total_par: int = 0
    total_pret: int = 0
    total_atturas: int = 0
    total_nebalso: int = 0
    result: Optional[str] = None              # Pieņemts/Noraidīts
    url: Optional[str] = None
    individual_votes: list[IndividualVote] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Vote snapshot parser
# ---------------------------------------------------------------------------

def parse_vote_snapshot(snapshot_text: str) -> VoteResult:
    """Parse a Playwright accessibility snapshot of a voting results page.

    Extracts the vote motif, totals, and each deputy's individual vote.
    """
    vote = VoteResult(motif="")

    # Extract motif. Playwright accessibility snapshots wrap the motif in
    # straight quotes; internal straight quotes are escaped as \". Greedy
    # match to the LAST quote on the line so motifs with embedded escaped
    # quotes (e.g. petition titles like "Goda ģimenes") aren't truncated
    # at the first internal \". Falls back to the old non-greedy form for
    # snapshots that lack a closing wrapper quote.
    motif_match = re.search(
        r'Balsošanas motīvs:\s*(.+)"\s*$',
        snapshot_text,
        re.MULTILINE,
    )
    if not motif_match:
        motif_match = re.search(
            r'Balsošanas motīvs:\s*(.+?)(?:\n|$)',
            snapshot_text,
        )
    if motif_match:
        raw = motif_match.group(1)
        # Unescape snapshot quote/backslash escapes
        vote.motif = raw.replace('\\"', '"').replace('\\\\', '\\').strip()

    # Extract date and time — store date as ISO YYYY-MM-DD
    dt_match = re.search(r'Datums:\s*(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})', snapshot_text)
    if dt_match:
        dd, mm, yyyy = dt_match.group(1).split(".")
        vote.date = f"{yyyy}-{mm}-{dd}"
        vote.time = dt_match.group(2)

    # Extract totals
    totals_match = re.search(
        r'par\s+(\d+),\s*pret\s+(\d+),\s*atturas\s+(\d+)',
        snapshot_text
    )
    if totals_match:
        vote.total_par = int(totals_match.group(1))
        vote.total_pret = int(totals_match.group(2))
        vote.total_atturas = int(totals_match.group(3))

    # Determine result from totals.
    # Latvian rule (Satversme 24.p, Saeimas kārtības rullis 138.p): ordinary
    # decisions pass with absolute majority of klātesošo deputātu — i.e.
    # par > (par+pret+atturas+nebalso) // 2. The 51-of-100 absolute majority
    # only applies to special cases (constitutional changes, no-confidence
    # motions, etc.) and is NOT the right default for legislative + Lm votes.
    #
    # First try to extract the result from snapshot text (authoritative when
    # present). Some Lm-type vote snapshots lack the label entirely, so we
    # fall back to the klātesošo computation.
    if "Noraidīts" in snapshot_text:
        vote.result = "Noraidīts"
    elif "Pieņemts" in snapshot_text or "pieņemts" in snapshot_text:
        vote.result = "Pieņemts"
    else:
        present = (vote.total_par + vote.total_pret
                   + vote.total_atturas + vote.total_nebalso)
        threshold = present // 2  # absolute majority = strictly more than half
        if vote.total_par > threshold:
            vote.result = "Pieņemts"
        else:
            vote.result = "Noraidīts"

    # Parse individual votes from the table rows
    # The snapshot has rows like:
    #   row "1. Maija Armaņeva LPV Par 7. Edmunds Cepurītis PRO Pret"
    # Each row contains TWO deputies (left and right columns)

    # Extract section markers to know current vote type
    # PAR section, PRET section, ATTURAS section, NEBALSO section
    sections = {
        'PAR': 'Par',
        'PRET': 'Pret',
        'ATTURAS': 'Atturas',
        'NEBALSO': 'Nebalsoja',
    }

    # Strategy: parse cell-by-cell from the YAML-like snapshot
    # Look for patterns like: cell "Maija Armaņeva" ... cell "LPV" ... cell "Par"
    # The table has 9 columns per row: [nr, name, faction, vote, spacer, nr, name, faction, vote]

    row_pattern = re.compile(
        r'row\s+"(.+?)"\s+\[ref=',
        re.DOTALL
    )

    nebalso_count = 0

    for row_match in row_pattern.finditer(snapshot_text):
        row_text = row_match.group(1)

        # Check for section headers
        for section_key, _vote_value in sections.items():
            if f'{section_key}:' in row_text:
                # Extract count if present (e.g., "NEBALSO: 1")
                count_match = re.search(rf'{section_key}:\s*(\d+)', row_text)
                if count_match and section_key == 'NEBALSO':
                    nebalso_count = int(count_match.group(1))
                    vote.total_nebalso = nebalso_count
                break

    # More reliable: extract from cell elements directly
    # Pattern: cell "Name" followed by cell "Faction" followed by cell "Vote"
    cell_pattern = re.compile(r'cell\s+"([^"]+)"\s+\[ref=\w+\]')
    cells = cell_pattern.findall(snapshot_text)

    # Filter out header cells and section markers
    skip_values = {'Vārds', 'Frakcija', 'Balss', ''}
    vote_values = {'Par', 'Pret', 'Atturas', 'Nebalsoja'}
    # ST/ST! = Stabilitātei! (Rosļikova frakcija, atdalījās no LPV 2024-01).
    # Snapshot cell formāts mainās laikā: 2025-12 sēdēs `cell "ST!"`,
    # 2026-03–04-01 — `cell "ST"`, no 2026-04-16 cell ir tukša.
    # Abi `ST` un `ST!` jāatpazīst, lai backfill no 14. Saeimas sākuma
    # (P3 2022-09→2025-12) korekti uztvertu Stabilitātei! deputātu vārdus
    # — citādi parser drops the deputy un saglabā "ST!" kā pseudo-deputy.
    faction_values = {'LPV', 'ZZS', 'JV', 'NA', 'AS', 'PRO', 'AP', 'LA', 'K', 'NP',
                      'ST', 'ST!'}

    i = 0
    while i < len(cells):
        cell = cells[i]

        # Skip numbered cells like "1.", "2.", section headers
        if re.match(r'^\d+\.$', cell) or cell in skip_values:
            i += 1
            continue

        # Skip section markers like "PAR: 42", "PRET: 47"
        if re.match(r'^(PAR|PRET|ATTURAS|NEBALSO):', cell):
            i += 1
            continue

        # Try to parse as deputy: Name [Faction] Vote
        name = cell

        # Validate it looks like a name (contains space or Latvian chars)
        if not re.search(r'[a-zA-ZāčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ]', name):
            i += 1
            continue

        # Look ahead for faction and vote
        faction = None
        deputy_vote = None

        if i + 1 < len(cells):
            next_cell = cells[i + 1]
            if next_cell in faction_values:
                faction = next_cell
                if i + 2 < len(cells) and cells[i + 2] in vote_values:
                    deputy_vote = cells[i + 2]
                    i += 3
                else:
                    i += 2
            elif next_cell in vote_values:
                deputy_vote = next_cell
                i += 2
            else:
                i += 1
                continue
        else:
            i += 1
            continue

        if deputy_vote:
            iv = IndividualVote(
                deputy_name=name,
                faction=faction,
                vote=deputy_vote,
            )
            vote.individual_votes.append(iv)

    return vote


# ---------------------------------------------------------------------------
# Politician name matching (deputies + bill submitters)
# ---------------------------------------------------------------------------

def _build_name_index(db_path: str | None = None) -> dict[str, int]:
    """Build a name → politician_id lookup from tracked_politicians.

    Uses both the canonical name and all name_forms for fuzzy matching.
    Returns a dict mapping lowercase name variants to politician IDs.
    """
    db = get_db(db_path)
    rows = db.execute(
        "SELECT id, name, name_forms FROM tracked_politicians"
    ).fetchall()
    db.close()

    index: dict[str, int] = {}
    for row in rows:
        pid = row["id"]
        # Canonical name
        index[row["name"].lower().strip()] = pid
        # Name forms (stored as JSON list)
        try:
            forms = json.loads(row["name_forms"] or "[]")
            for form in forms:
                index[form.lower().strip()] = pid
        except (json.JSONDecodeError, TypeError):
            pass

    return index


def match_deputies_to_politicians(
    votes: list[IndividualVote],
    db_path: str | None = None,
) -> list[IndividualVote]:
    """Match deputy names from voting records to tracked_politicians.

    Updates politician_id on each IndividualVote where a match is found.
    """
    name_index = _build_name_index(db_path)

    for iv in votes:
        key = iv.deputy_name.lower().strip()
        if key in name_index:
            iv.politician_id = name_index[key]
            continue

        # Older titania snapshots (2022-2024) sometimes invert name order:
        # "Brigmanis Augusts" vs canonical "Augusts Brigmanis". Try the
        # swapped 2-token form before falling through to partial match —
        # this single rule recovers ~38k attributions across the P3 backfill.
        parts = key.split()
        if len(parts) == 2:
            swapped = f"{parts[1]} {parts[0]}"
            if swapped in name_index:
                iv.politician_id = name_index[swapped]
                continue

        # Try partial match: "Jānis Dombrava" in name_index keys
        for name_key, pid in name_index.items():
            if key == name_key or name_key in key or key in name_key:
                iv.politician_id = pid
                break

    return votes


def match_submitters_to_politicians(
    db_path: str,
    bill_id: int,
    submitter_names: list[str],
) -> tuple[int, list[str]]:
    """Match submitter names to tracked_politicians via existing name_forms index.

    Inserts role='submitter' rows into saeima_bill_politicians.

    Idempotency note: uses SELECT-before-INSERT (not the UNIQUE constraint),
    because SQLite treats each NULL `amendment_nr` as distinct — so the
    UNIQUE(bill_id, politician_id, role, amendment_nr) constraint would
    permit duplicate (1, 5, 'submitter', NULL) rows. The explicit check
    is the actual idempotency guarantee.

    Returns (matched_count, unmatched_names) for caller logging.
    Reuses _build_name_index() — same matching logic as
    match_deputies_to_politicians.

    Spec § 4.3.
    """
    if not submitter_names:
        return 0, []

    name_index = _build_name_index(db_path)
    db = get_db(db_path)
    matched = 0
    unmatched: list[str] = []

    for raw in submitter_names:
        key = raw.lower().strip()
        pid = name_index.get(key)
        if pid is None:
            # Try partial match (same logic as match_deputies_to_politicians)
            for name_key, candidate_pid in name_index.items():
                if key == name_key or name_key in key or key in name_key:
                    pid = candidate_pid
                    break

        if pid is None:
            unmatched.append(raw)
            continue

        # Check for existing link before inserting (idempotency)
        existing = db.execute(
            "SELECT id FROM saeima_bill_politicians "
            "WHERE bill_id=? AND politician_id=? AND role='submitter'",
            (bill_id, pid),
        ).fetchone()
        if existing is not None:
            # Already linked, skip
            continue

        db.execute(
            "INSERT INTO saeima_bill_politicians "
            "(bill_id, politician_id, role) VALUES (?, ?, 'submitter')",
            (bill_id, pid),
        )
        matched += 1

    db.commit()
    db.close()
    return matched, unmatched


# ---------------------------------------------------------------------------
# DB storage
# ---------------------------------------------------------------------------

def store_vote(
    vote: VoteResult,
    agenda_item_id: Optional[int] = None,
    db_path: str | None = None,
    *,
    summary: Optional[str] = None,
    document_url: Optional[str] = None,
    document_nr: Optional[str] = None,
) -> int:
    """Store a vote result with all individual ballots. Returns vote DB id.

    Keyword-only `summary`, `document_url`, `document_nr` capture Step 3.5
    (bill substance) at INSERT time. Prior pattern was NULL on INSERT followed
    by a separate UPDATE — that update was being skipped, leaving 21 votes
    NULL across 07.05+14.05 sessions (sk. CHANGELOG 2026-05-16). Writing them
    in the same call eliminates the forgettable second step.
    """
    db = get_db(db_path)

    # Resolve to absolute URL before any DB operation. Playwright snapshot
    # parser yields relative anchors ('./0/HEX?OpenDocument'); persisting
    # those raw breaks the public-site "Balsojuma tabula" link (safe_url
    # filter rejects non-http(s) values, rendering href="#").
    vote.url = _resolve_vote_url(vote.url)

    # Check if already stored (by URL)
    if vote.url:
        existing = db.execute(
            "SELECT id FROM saeima_votes WHERE url = ?", (vote.url,)
        ).fetchone()
        if existing:
            db.close()
            return existing["id"]

    topic = _motif_to_topic(vote.motif)

    db.execute(
        """INSERT INTO saeima_votes
           (agenda_item_id, motif, vote_date, vote_time,
            total_par, total_pret, total_atturas, total_nebalso,
            result, url, topic, summary, document_url, document_nr, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (agenda_item_id, vote.motif, vote.date, vote.time,
         vote.total_par, vote.total_pret, vote.total_atturas, vote.total_nebalso,
         vote.result, vote.url, topic, summary, document_url, document_nr, now_lv()),
    )
    vote_db_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Store individual votes
    for iv in vote.individual_votes:
        db.execute(
            """INSERT INTO saeima_individual_votes
               (vote_id, deputy_name, faction, vote, politician_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vote_db_id, iv.deputy_name, iv.faction, iv.vote,
             iv.politician_id, now_lv()),
        )

    db.commit()
    db.close()
    return vote_db_id


# Matches "(1286/Lp14)" or "(976/Lm14)" patterns in vote motif — used to
# detect bill-type votes that should have a summary. Procedural votes
# without a bill reference are exempt.
_BILL_LIKE_MOTIF = re.compile(r"\(\d+/L[pm]14\)")


# ---------------------------------------------------------------------------
# Claim generation (saeima_vote claim_type)
# ---------------------------------------------------------------------------

def generate_claims_from_votes(
    vote: VoteResult,
    vote_db_id: int,
    db_path: str | None = None,
) -> list[int]:
    """Generate politracker claims from tracked politicians' votes.

    For each tracked politician who voted, creates a claim (their vote = their
    stance on the issue) directly — no synthetic document. Vote provenance is
    fully reconstructable from saeima_votes + saeima_individual_votes via
    (claims.opponent_id, claims.source_url, claims.stated_at). Storing the
    bill page as a "document" was an anti-pattern that grew documents-table
    by 8985 fake rows (8876 of them claim-linked) and skewed every
    documents-based statistic. See 2026-04-25 plan
    docs/superpowers/plans/2026-04-25-saeima-vote-doc-cleanup.md.

    Returns list of created claim IDs.

    Layer-1 of the Step 3.5 regress defense (sk. CHANGELOG 2026-05-16):
    when summary IS NULL on a bill-like motif, emit a single warning log
    row (action='saeima_summary_missing') so the routine post-check
    surfaces missed summaries. We do NOT refuse the call — image-only PDFs
    legitimately produce no machine-readable summary, and a hard block
    would strand agents in those cases. Discipline lives in the prompt;
    the log is the safety-net signal.
    """
    claim_ids = []

    # Only process votes from tracked politicians
    tracked_votes = [iv for iv in vote.individual_votes if iv.politician_id]
    if not tracked_votes:
        return claim_ids

    # Layer-1 warning: bill-like motif without a stored summary.
    _db_check = get_db(db_path)
    _summary_row = _db_check.execute(
        "SELECT summary FROM saeima_votes WHERE id = ?", (vote_db_id,)
    ).fetchone()
    _db_check.close()
    _has_summary = bool(_summary_row and _summary_row["summary"])
    if not _has_summary and _BILL_LIKE_MOTIF.search(vote.motif or ""):
        log_action(
            action="saeima_summary_missing",
            status="warning",
            error_message=(
                f"vote_db_id={vote_db_id} bill-like motif lacks summary — "
                f"Step 3.5 (read bill text + write summary) was likely skipped. "
                f"Generic 'Balsoja PAR: <motif>' stance will be produced for "
                f"{len(tracked_votes)} tracked deputies."
            ),
            details={
                "vote_db_id": vote_db_id,
                "motif": vote.motif,
                "tracked_count": len(tracked_votes),
            },
            db_path=db_path,
        )

    # Determine topic from vote motif
    topic = _motif_to_topic(vote.motif)

    full_url = _resolve_vote_url(vote.url)

    for iv in tracked_votes:
        # Map vote to stance — use bill summary if available
        _db = get_db(db_path)
        vote_row = _db.execute(
            "SELECT summary FROM saeima_votes WHERE id = ?", (vote_db_id,)
        ).fetchone()
        summary = vote_row["summary"] if vote_row and vote_row["summary"] else None

        # Sentinel summaries (P3 historic backfill) signal "summary not available"
        # — fall through to the motif-based stance so the UI doesn't surface
        # "Atbalsta: kopsavilkums nav pieejams …" as the deputy's position.
        # Sentinel format: "Kopsavilkums nav pieejams — …"
        _is_sentinel = bool(summary and summary.startswith("Kopsavilkums nav pieejams"))

        if summary and summary != vote.motif and not _is_sentinel:
            # Build meaningful stance from summary
            vote_prefix = {
                'Par': 'Atbalsta',
                'Pret': 'Iebilst pret',
                'Atturas': 'Atturējās balsojumā par',
                'Nebalsoja': 'Nebalsoja par',
            }
            prefix = vote_prefix.get(iv.vote, iv.vote)
            # Lowercase first char of summary for natural flow — unless the
            # summary opens with an acronym (≥2 leading uppercase letters,
            # e.g. "LPV deputātu…"), which lowercasing corrupts to "lPV".
            if summary[:2].isupper():
                summary_lower = summary
            else:
                summary_lower = summary[0].lower() + summary[1:] if summary else ""
            stance = f"{prefix}: {summary_lower}"
        else:
            # Fallback to old format
            vote_lv = {
                'Par': 'Balsoja PAR',
                'Pret': 'Balsoja PRET',
                'Atturas': 'ATTURĒJĀS',
                'Nebalsoja': 'NEBALSOJA',
            }
            stance = f"{vote_lv.get(iv.vote, iv.vote)}: {vote.motif}"

        # Determine salience based on vote type
        salience = _vote_salience(vote.motif)

        from src.db import store_claim
        claim_id = store_claim(
            opponent_id=iv.politician_id,
            document_id=None,
            topic=topic,
            stance=stance,
            quote=None,
            confidence=1.0,  # Voting records are factual, not interpreted
            reasoning=f"Saeimas balsojums {vote.date}: {iv.deputy_name} balsoja {iv.vote}. "
                      f"Kopējais rezultāts: par {vote.total_par}, pret {vote.total_pret}, "
                      f"atturas {vote.total_atturas}.",
            salience=salience,
            source_url=full_url,
            stated_at=_parse_vote_datetime(vote.date, vote.time),
            claim_type="saeima_vote",
            db_path=db_path,
        )
        claim_ids.append(claim_id)

        log_action(
            action="saeima_vote_claim",
            opponent_id=iv.politician_id,
            status="success",
            details={
                "vote_motif": vote.motif,
                "deputy_vote": iv.vote,
                "vote_db_id": vote_db_id,
                "claim_id": claim_id,
            },
            db_path=db_path,
        )

    return claim_ids


# ---------------------------------------------------------------------------
# High-level orchestration (called by sub-agent)
# ---------------------------------------------------------------------------

def process_vote_snapshot(
    snapshot_text: str,
    vote_url: str,
    agenda_item_id: Optional[int] = None,
    db_path: str | None = None,
    *,
    summary: Optional[str] = None,
    document_url: Optional[str] = None,
    document_nr: Optional[str] = None,
) -> dict:
    """Full pipeline: parse snapshot → match deputies → store → generate claims.

    Args:
        snapshot_text: Raw text from Playwright browser_snapshot
        vote_url: The URL of the voting page (for dedup and linking)
        agenda_item_id: Optional FK to saeima_agenda_items
        db_path: Database path
        summary: 1-2 sentence LV summary of the bill substance (Step 3.5).
                 Passing it here writes it atomically with the vote insert,
                 avoiding the NULL→UPDATE pattern that silently regressed in
                 May 2026 sessions. Skip only for procedural votes without
                 a bill reference.
        document_url: URL of the bill text page (titania.saeima.lv document).
        document_nr: Document number (e.g. '1286/Lp14').

    Returns:
        dict with vote_db_id, matched_politicians, claim_ids, summary
    """
    # 1. Parse
    vote = parse_vote_snapshot(snapshot_text)
    vote.url = vote_url

    # 2. Match deputies to tracked politicians
    match_deputies_to_politicians(vote.individual_votes, db_path)

    # 3. Store (with optional Step 3.5 fields written inline)
    vote_db_id = store_vote(
        vote, agenda_item_id, db_path,
        summary=summary, document_url=document_url, document_nr=document_nr,
    )

    # 4. Generate claims for tracked politicians
    claim_ids = generate_claims_from_votes(vote, vote_db_id, db_path)

    matched = [
        {"name": iv.deputy_name, "faction": iv.faction, "vote": iv.vote, "pid": iv.politician_id}
        for iv in vote.individual_votes
        if iv.politician_id
    ]

    return {
        "vote_db_id": vote_db_id,
        "motif": vote.motif,
        "date": vote.date,
        "totals": f"par {vote.total_par}, pret {vote.total_pret}, atturas {vote.total_atturas}",
        "total_deputies": len(vote.individual_votes),
        "matched_politicians": matched,
        "claim_ids": claim_ids,
    }
