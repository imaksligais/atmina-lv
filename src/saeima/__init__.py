"""src.saeima — Saeimas sēžu un balsojumu apstrāde.

Pakete pārmantota no src/saeima.py monolīta (1425 LOC) F4 refaktoringā 2026-04-29.
Eksponē tieši to pašu publisko + tests/agent-imported simbolu kopu, kas bija
pirms refaktoringa, lai @saeima-tracker prompts un scripts/backfill_*.py
turpina darboties bez izmaiņām.

Iekšējā struktūra:
- src.saeima.schema   — init_saeima_tables, init_saeima_bills (DDL)
- src.saeima.bills    — bill regexes + classification + ops + AgendaBill +
                        SAEIMA_BASE_URL + URL/datuma helperi
                        (leaf-modulis: nav saeima/ iekšējo importu)
- src.saeima.parsing  — parse_agenda_snapshot + helperi (no bills.AgendaBill)
- src.saeima.claims   — _stem, _word, _MOTIF_TOPIC_MAP, _motif_to_topic,
                        _vote_salience (leaf-modulis: pure topic mapping)
- src.saeima.votes    — vote dataclases + parse_vote_snapshot + name matching +
                        store_vote + generate_claims_from_votes +
                        process_vote_snapshot (depends on bills + claims)

Cikla pārvaldība: bills + claims ir leaf moduļi (nav saeima/ iekšējo importu).
votes importē no abiem. parsing importē no bills. saeima_legacy.py izdzēsts
F4.3+F4.4 atomic commitā.
"""

from src.db import DB_PATH
from src.saeima.bills import (
    LAW_TITLE_RE,
    SAEIMA_BASE_URL,
    AgendaBill,
    _canonicalize_stage_name,
    _parse_vote_datetime,
    _reading_from_motif,
    _resolve_base_law_slug,
    _resolve_vote_url,
    _VALID_BILL_TYPES,
    _VALID_STAGE_NAMES,
    append_bill_stage,
    load_laws_index,
    resolve_bill_from_motif,
    upsert_bill,
)
from src.saeima.claims import _motif_to_topic, _vote_salience
from src.saeima.parsing import parse_agenda_snapshot
from src.saeima.schema import init_saeima_bills, init_saeima_tables
from src.saeima.votes import (
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    match_deputies_to_politicians,
    match_submitters_to_politicians,
    parse_vote_snapshot,
    process_vote_snapshot,
    store_vote,
)

__all__ = [
    "DB_PATH",
    "LAW_TITLE_RE",
    "SAEIMA_BASE_URL",
    "AgendaBill",
    "IndividualVote",
    "VoteResult",
    "_VALID_BILL_TYPES",
    "_VALID_STAGE_NAMES",
    "_canonicalize_stage_name",
    "_motif_to_topic",
    "_parse_vote_datetime",
    "_reading_from_motif",
    "_resolve_base_law_slug",
    "_resolve_vote_url",
    "_vote_salience",
    "append_bill_stage",
    "generate_claims_from_votes",
    "init_saeima_bills",
    "init_saeima_tables",
    "load_laws_index",
    "match_deputies_to_politicians",
    "match_submitters_to_politicians",
    "parse_agenda_snapshot",
    "parse_vote_snapshot",
    "process_vote_snapshot",
    "resolve_bill_from_motif",
    "store_vote",
    "upsert_bill",
]
