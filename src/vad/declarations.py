"""High-level orchestrator: fetch + parse + role-disambiguate + store.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 6, § 7

Public API:
    fetch_for_politician(opponent_id, db, client) -> StoreResult
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote_plus

from src.vad.fetch import VadClient, SearchResultRow, BASE_URL
from src.vad.matcher import candidate_name_pairs, role_matches
from src.vad.parsing import (
    ParsedDeclaration, parse_declaration_html,
)

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"par\s+(\d{4})\.\s*gadu")


@dataclass
class StoreResult:
    opponent_id: int
    politician_name: str
    rows_found: int       # search rows after role-match filter
    rows_skipped_role: int = 0
    rows_skipped_legacy: int = 0
    new_inserted: int = 0
    already_present: int = 0
    errors: list[str] = field(default_factory=list)


def _norm_kind_from_label(declaration_type: str) -> str:
    """Mirror of src.vad.parsing._norm_kind — applied to search-row label."""
    t = declaration_type.lower()
    if "kārtējā gada" in t or "ikgadējā" in t:
        return "annual"
    if "darba sākuma" in t:
        return "start"
    if "beidzot pildīt" in t:
        return "end"
    if "par pirmo gadu" in t:
        return "post_year_1"
    if "par otro gadu" in t:
        return "post_year_2"
    return "interim"


def _year_from_label(declaration_type: str) -> int | None:
    m = _YEAR_RE.search(declaration_type or "")
    return int(m.group(1)) if m else None


def _load_disambig_config(
    db: sqlite3.Connection, opponent_id: int
) -> tuple[list[str], list[str]]:
    """Load (vad_disambig hints, negative_patterns) for a politician.

    vad_disambig dzīvo ``tracked_politicians.keywords`` JSON kā ``vad_disambig``
    lauks. negative_patterns dzīvo savā kolonnā kā JSON list. Abi tukši → ([], []).
    Tukšs disambig saraksts → trust full-name search (skip filtra).

    Phase 1.5 — homonīmu V+U kontaminācija pret 11 pids; skat. spec § 15.2 F13.
    """
    row = db.execute(
        "SELECT keywords, negative_patterns FROM tracked_politicians WHERE id=?",
        (opponent_id,),
    ).fetchone()
    if row is None:
        return [], []
    hints: list[str] = []
    if row["keywords"]:
        try:
            kw = json.loads(row["keywords"])
            if isinstance(kw, dict):
                hints = list(kw.get("vad_disambig") or [])
            # Legacy formāts (saraksts) — nav vad_disambig, hints paliek []
        except (json.JSONDecodeError, TypeError):
            pass
    neg: list[str] = []
    if row["negative_patterns"]:
        try:
            np_ = json.loads(row["negative_patterns"])
            if isinstance(np_, list):
                neg = list(np_)
        except (json.JSONDecodeError, TypeError):
            pass
    return hints, neg


def _row_passes_disambig(
    row: SearchResultRow, hints: list[str], neg_patterns: list[str]
) -> bool:
    """True iff row tiek pieņemts pēc disambig filter rules.

    Rule 1: ja hints tukši → True (no filter).
    Rule 2: ja kāds neg_pattern (case-ins substring) atrasts inst+pos → False.
    Rule 3: vismaz viens hint (case-ins substring) jābūt inst vai pos → True; citādi False.
    """
    if not hints:
        return True
    haystack = f"{row.institution} {row.position_title}".lower()
    for neg in neg_patterns:
        if neg and neg.lower() in haystack:
            return False
    for hint in hints:
        if hint and hint.lower() in haystack:
            return True
    return False


def _make_accept_row(
    hints: list[str], neg_patterns: list[str]
) -> Callable[[SearchResultRow], bool] | None:
    """Predikāts priekš VadClient.search() institūcijas-aware lapošanas.

    Atgriež None, ja hints tukši (trust full-name search → search apstājas pie
    parastā PAGE_SAFETY_BOUND, kā vienmēr). Citādi atgriež predikātu, kas True
    tikai politiķim piederīgām rindām — search to izmanto, lai turpinātu lapot
    pāri 200. rindai homonīmu robā (BACKLOG [FIX] Inga Bērziņa: 368 "Vidzemes
    slimnīca" rindas iebīda viņas reālās Saeimas deklarācijas aiz bound).
    """
    if not hints:
        return None
    return lambda row: _row_passes_disambig(row, hints, neg_patterns)


def fetch_for_politician(
    opponent_id: int,
    db: sqlite3.Connection,
    client: VadClient,
    *,
    include_legacy: bool = False,
    dry_run: bool = False,
) -> StoreResult:
    """Search VID, filter by role, fetch+parse+store new declarations.

    Idempotent on natural key (opponent_id, kind, year, position_title);
    submitted_at not pre-checkable (only in detail HTML), so submitted_at-only
    revisions of the same declaration may insert twice — tolerable edge case.
    """
    pol = db.execute(
        "SELECT name, role FROM tracked_politicians WHERE id=?", (opponent_id,)
    ).fetchone()
    if pol is None:
        raise ValueError(f"opponent_id={opponent_id} not in tracked_politicians")
    name = pol["name"]
    role = pol["role"]

    result = StoreResult(opponent_id=opponent_id, politician_name=name, rows_found=0)

    # Phase 1.5 — disambig filter (homonīmu kontaminācija) ielādē per-pid hints.
    # Ielādējam PIRMS search, lai institūcijas-aware lapošana (accept_row) var
    # iet pāri PAGE_SAFETY_BOUND, kad homonīms iebīda reālās deklarācijas aiz
    # bound (BACKLOG [FIX] Inga Bērziņa).
    disambig_hints, disambig_neg = _load_disambig_config(db, opponent_id)
    accept_row = _make_accept_row(disambig_hints, disambig_neg)

    rows: list[SearchResultRow] = []
    for given, family in candidate_name_pairs(opponent_id, name):
        rows = client.search(given, family, accept_row=accept_row)
        if rows:
            break

    # Pre-load existing natural keys for cheap dedup (no detail fetch).
    existing_keys = {
        (r["declaration_kind"], r["declaration_year"], r["position_title"])
        for r in db.execute(
            "SELECT declaration_kind, declaration_year, position_title "
            "FROM vad_declarations WHERE opponent_id=?",
            (opponent_id,),
        )
    }

    # Phase 1.5 F14 — retry-search cache + abandon threshold.
    # _retry_map kešo natural-key → fresh-row mapping, lai vairāku rindu
    # parse-fail nedotu O(n²) re-searches (10s throttle × 200 rindas = 33 min).
    # _retry_fail_count abandono visus atlikušos rindas pēc N secīgiem fail'iem.
    _retry_map: dict[tuple, SearchResultRow] | None = None
    _retry_fail_count = 0
    _RETRY_FAIL_THRESHOLD = 3

    for r in rows:
        if r.is_legacy and not include_legacy:
            result.rows_skipped_legacy += 1
            continue
        if not _row_passes_disambig(r, disambig_hints, disambig_neg):
            log.warning(
                "vad-disambig-skip: pid=%d name=%r vid_inst=%r vid_pos=%r hints=%r neg=%r",
                opponent_id, name, r.institution, r.position_title,
                disambig_hints, disambig_neg,
            )
            result.rows_skipped_role += 1
            continue
        if not role_matches(role, r.institution, r.position_title):
            log.warning(
                "vad-role-mismatch: pid=%d name=%r role=%r vid_inst=%r vid_pos=%r",
                opponent_id, name, role, r.institution, r.position_title,
            )
            result.rows_skipped_role += 1
            continue
        result.rows_found += 1

        kind = _norm_kind_from_label(r.declaration_type)
        year = _year_from_label(r.declaration_type)
        natural_key = (kind, year, r.position_title)
        if natural_key in existing_keys:
            # Already in DB — refresh vad_uuid (latest seen) but skip detail fetch
            if not dry_run:
                db.execute(
                    "UPDATE vad_declarations SET vad_uuid=? "
                    "WHERE opponent_id=? AND declaration_kind=? "
                    "AND declaration_year IS ? AND position_title IS ?",
                    (r.vad_uuid, opponent_id, kind, year, r.position_title),
                )
                db.commit()
            result.already_present += 1
            continue

        if dry_run:
            result.new_inserted += 1
            continue
        try:
            html = client.fetch_detail(r.vad_uuid)
            parsed = parse_declaration_html(html)
        except ValueError as e:
            if "nav header table" not in str(e):
                msg = f"uuid={r.vad_uuid}: ValueError: {e}"
                log.warning("vad-fetch-fail %s", msg)
                result.errors.append(msg)
                continue
            # Phase 1.5 F14 — VID anti-scrape invalidates UUID nonce.
            # Lazy build retry-map ONCE per pid (reset+re-search), tad lookup pa natural key.
            if _retry_map is None:
                log.warning(
                    "vad-parse-fail first; reset+re-search to build retry map for pid=%d",
                    opponent_id,
                )
                client.reset_session()
                rows_retry: list[SearchResultRow] = []
                for given, family in candidate_name_pairs(opponent_id, name):
                    rows_retry = client.search(given, family, accept_row=accept_row)
                    if rows_retry:
                        break
                _retry_map = {
                    (
                        _norm_kind_from_label(rr.declaration_type),
                        _year_from_label(rr.declaration_type),
                        rr.position_title,
                    ): rr
                    for rr in rows_retry
                }
            fresh = _retry_map.get(natural_key)
            if fresh is None:
                msg = f"uuid={r.vad_uuid}: parse fail; retry map nav atbilstības"
                log.warning("vad-fetch-fail %s", msg)
                result.errors.append(msg)
                _retry_fail_count += 1
                if _retry_fail_count >= _RETRY_FAIL_THRESHOLD:
                    log.warning(
                        "vad-abandon-pid: pid=%d %d secīgi parse-fails; pārtraucu",
                        opponent_id, _retry_fail_count,
                    )
                    break
                continue
            try:
                html = client.fetch_detail(fresh.vad_uuid)
                parsed = parse_declaration_html(html)
                r = fresh  # use fresh row for storage (vad_uuid)
            except Exception as e2:
                msg = f"uuid={r.vad_uuid}->retry={fresh.vad_uuid}: {type(e2).__name__}: {e2}"
                log.warning("vad-fetch-fail-after-retry %s", msg)
                result.errors.append(msg)
                _retry_fail_count += 1
                if _retry_fail_count >= _RETRY_FAIL_THRESHOLD:
                    log.warning(
                        "vad-abandon-pid: pid=%d %d secīgi parse-fails; pārtraucu",
                        opponent_id, _retry_fail_count,
                    )
                    break
                continue
        except Exception as e:
            msg = f"uuid={r.vad_uuid}: {type(e).__name__}: {e}"
            log.exception("vad-fetch-fail %s", msg)
            result.errors.append(msg)
            continue

        try:
            _store(db, opponent_id, r, parsed, html, name)
            existing_keys.add(natural_key)
            result.new_inserted += 1
        except Exception as e:
            msg = f"uuid={r.vad_uuid}: store {type(e).__name__}: {e}"
            log.exception("vad-store-fail %s", msg)
            result.errors.append(msg)

    return result


def _store(
    db: sqlite3.Connection,
    opponent_id: int,
    row: SearchResultRow,
    parsed: ParsedDeclaration,
    raw_html: str,
    politician_name: str,
) -> int:
    """Insert vad_declarations + all section rows in one transaction."""
    parts = politician_name.split()
    given = " ".join(parts[:-1])
    family = parts[-1]
    source_url = (
        f"{BASE_URL}/VAD?Name={quote_plus(given)}&Surname={quote_plus(family)}"
    )
    cur = db.cursor()
    cur.execute(
        "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
        "declaration_kind, declaration_year, institution, position_title, "
        "submitted_at, published_at, other_info, financial_instruments_text, "
        "other_benefits_text, trust_agreement_text, has_private_pension, "
        "has_life_insurance, source_url, raw_html) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            opponent_id, row.vad_uuid,
            parsed.header.declaration_type, parsed.header.declaration_kind,
            parsed.header.declaration_year,
            parsed.header.institution, parsed.header.position_title,
            parsed.header.submitted_at, parsed.header.published_at,
            parsed.other_info, parsed.financial_instruments_text,
            parsed.other_benefits_text, parsed.trust_agreement_text,
            int(parsed.has_private_pension) if parsed.has_private_pension is not None else None,
            int(parsed.has_life_insurance) if parsed.has_life_insurance is not None else None,
            source_url, raw_html,
        ),
    )
    decl_id = cur.lastrowid
    for p in parsed.positions:
        cur.execute(
            "INSERT INTO vad_positions(declaration_id, position_title, entity_name, "
            "entity_reg_number, entity_address, is_individual) VALUES (?,?,?,?,?,?)",
            (decl_id, p.position_title, p.entity_name, p.entity_reg_number,
             p.entity_address, int(p.is_individual)),
        )
    for re_ in parsed.real_estate:
        cur.execute(
            "INSERT INTO vad_real_estate(declaration_id, property_type, location, "
            "ownership_status) VALUES (?,?,?,?)",
            (decl_id, re_.property_type, re_.location, re_.ownership_status),
        )
    for c in parsed.companies:
        cur.execute(
            "INSERT INTO vad_companies(declaration_id, company_name, reg_number, "
            "address, capital_kind, units, total_value, currency) VALUES (?,?,?,?,?,?,?,?)",
            (decl_id, c.company_name, c.reg_number, c.address, c.capital_kind,
             c.units, c.total_value, c.currency),
        )
    for v in parsed.vehicles:
        cur.execute(
            "INSERT INTO vad_vehicles(declaration_id, vehicle_type, brand, "
            "year_made, year_registered, ownership_status) VALUES (?,?,?,?,?,?)",
            (decl_id, v.vehicle_type, v.brand, v.year_made, v.year_registered,
             v.ownership_status),
        )
    for s in parsed.savings:
        cur.execute(
            "INSERT INTO vad_savings(declaration_id, savings_kind, amount, currency, "
            "amount_in_words, holder_name, holder_reg_number, holder_address) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (decl_id, s.savings_kind, s.amount, s.currency, s.amount_in_words,
             s.holder_name, s.holder_reg_number, s.holder_address),
        )
    for i in parsed.income:
        cur.execute(
            "INSERT INTO vad_income(declaration_id, source, source_reg_number, "
            "is_individual, income_type, amount, currency) VALUES (?,?,?,?,?,?,?)",
            (decl_id, i.source, i.source_reg_number, int(i.is_individual),
             i.income_type, i.amount, i.currency),
        )
    for t in parsed.transactions:
        cur.execute(
            "INSERT INTO vad_transactions(declaration_id, transaction_description, "
            "amount, currency) VALUES (?,?,?,?)",
            (decl_id, t.transaction_description, t.amount, t.currency),
        )
    for d in parsed.debts:
        cur.execute(
            "INSERT INTO vad_debts(declaration_id, creditor_name, creditor_reg_number, "
            "creditor_address, amount, currency, amount_in_words) VALUES (?,?,?,?,?,?,?)",
            (decl_id, d.creditor_name, d.creditor_reg_number, d.creditor_address,
             d.amount, d.currency, d.amount_in_words),
        )
    for ln in parsed.loans_given:
        cur.execute(
            "INSERT INTO vad_loans_given(declaration_id, amount, currency, amount_in_words) "
            "VALUES (?,?,?,?)",
            (decl_id, ln.amount, ln.currency, ln.amount_in_words),
        )
    for fm in parsed.family:
        cur.execute(
            "INSERT INTO vad_family(declaration_id, full_name, relation) VALUES (?,?,?)",
            (decl_id, fm.full_name, fm.relation),
        )
    db.commit()
    return decl_id
