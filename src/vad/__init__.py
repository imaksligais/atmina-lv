"""VAD (Valsts amatpersonu deklarācijas) — strukturēta ielāde no www6.vid.gov.lv.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md

Public API:
    init_vad_tables — DDL (lazy, ne init_db)
    fetch_for_politician — orchestrator (search + parse + store)
    VadClient — HTTP layer
    parse_declaration_html — pure parser
"""

from src.vad.declarations import StoreResult, fetch_for_politician
from src.vad.fetch import SearchResultRow, VadClient
from src.vad.parsing import (
    ParsedDeclaration,
    parse_declaration_html,
)
from src.vad.schema import init_vad_tables

__all__ = [
    "init_vad_tables",
    "fetch_for_politician",
    "StoreResult",
    "VadClient",
    "SearchResultRow",
    "ParsedDeclaration",
    "parse_declaration_html",
]
