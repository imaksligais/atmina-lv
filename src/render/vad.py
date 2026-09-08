"""Render-time pre-loader for VAD declarations.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.1

One-batch-per-tabula query strategy (F4 leaf-vs-fan-out paterns); avoids
N+1 queries when rendering 152 politician profile pages. Try/except
OperationalError guard for test DBs without init_vad_tables (saeima_bills
precedents src/render/politicians.py:503).
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from src.vad.diff import DeltaRow, compute_section_deltas

SECTION_NAMES = [
    "positions", "real_estate", "companies", "vehicles", "savings",
    "income", "transactions", "debts", "loans_given", "family",
]
SECTION_TABLES = {
    "positions": "vad_positions", "real_estate": "vad_real_estate",
    "companies": "vad_companies", "vehicles": "vad_vehicles",
    "savings": "vad_savings", "income": "vad_income",
    "transactions": "vad_transactions", "debts": "vad_debts",
    "loans_given": "vad_loans_given", "family": "vad_family",
}


@dataclass
class VadDeclarationView:
    declaration_id: int
    opponent_id: int
    year: Optional[int]
    kind: str
    type_label: str
    institution: str
    position_title: str
    submitted_at: Optional[str]
    published_at: Optional[str]
    source_url: str
    has_private_pension: Optional[bool]
    has_life_insurance: Optional[bool]
    other_info: Optional[str]
    sections: dict[str, list[DeltaRow]] = field(default_factory=dict)


def get_vad_data_for_politicians(
    db: sqlite3.Connection,
    pids: list[int],
) -> dict[int, list[VadDeclarationView]]:
    """Pre-load VAD data for given politicians.

    Returns: dict[pid] -> list[VadDeclarationView] sorted year DESC.
    Newest year gets delta marķieri vs second-newest; earlier years no delta.
    Idempotent + side-effect-free; safe to call from render path.

    Returns empty dict if vad_declarations table missing (Phase 0 not yet run).
    """
    if not pids:
        return {}
    try:
        decls_by_pid = _fetch_declarations(db, pids)
    except sqlite3.OperationalError:
        return {}

    if not decls_by_pid:
        return {}

    all_decl_ids = [d.declaration_id for views in decls_by_pid.values() for d in views]
    rows_by_section_decl = _fetch_section_rows(db, all_decl_ids)

    out: dict[int, list[VadDeclarationView]] = {}
    for pid, views in decls_by_pid.items():
        # views sorted year DESC; newest = views[0], second = views[1]
        for i, view in enumerate(views):
            for section in SECTION_NAMES:
                this_rows = rows_by_section_decl.get(section, {}).get(view.declaration_id, [])
                if i + 1 < len(views):
                    prev_rows = rows_by_section_decl.get(section, {}).get(
                        views[i + 1].declaration_id, []
                    )
                    view.sections[section] = compute_section_deltas(section, prev_rows, this_rows)
                else:
                    view.sections[section] = [DeltaRow(payload=r, delta="unchanged") for r in this_rows]
        out[pid] = views
    return out


def vad_count_per_politician(db: sqlite3.Connection) -> dict[int, int]:
    """COUNT(*) per opponent_id; tukšs dict ja tabula nepastāv."""
    try:
        rows = db.execute(
            "SELECT opponent_id, COUNT(*) FROM vad_declarations GROUP BY opponent_id"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r[0]: r[1] for r in rows}


def _fetch_declarations(db, pids):
    placeholders = ",".join("?" * len(pids))
    rows = db.execute(
        f"SELECT id, opponent_id, declaration_year, declaration_kind, declaration_type, "
        f"institution, position_title, submitted_at, published_at, source_url, "
        f"has_private_pension, has_life_insurance, other_info "
        f"FROM vad_declarations WHERE opponent_id IN ({placeholders}) "
        f"ORDER BY opponent_id, COALESCE(declaration_year, 0) DESC, published_at DESC",
        pids,
    ).fetchall()
    out: dict[int, list[VadDeclarationView]] = defaultdict(list)
    for r in rows:
        out[r["opponent_id"]].append(VadDeclarationView(
            declaration_id=r["id"], opponent_id=r["opponent_id"],
            year=r["declaration_year"], kind=r["declaration_kind"],
            type_label=r["declaration_type"], institution=r["institution"] or "",
            position_title=r["position_title"] or "",
            submitted_at=r["submitted_at"], published_at=r["published_at"],
            source_url=r["source_url"],
            has_private_pension=bool(r["has_private_pension"]) if r["has_private_pension"] is not None else None,
            has_life_insurance=bool(r["has_life_insurance"]) if r["has_life_insurance"] is not None else None,
            other_info=r["other_info"],
        ))
    return out


def _fetch_section_rows(db, decl_ids):
    """Returns nested dict[section][decl_id] -> list[row dict]."""
    if not decl_ids:
        return {}
    placeholders = ",".join("?" * len(decl_ids))
    out: dict[str, dict[int, list[dict]]] = {s: defaultdict(list) for s in SECTION_NAMES}
    for section, table in SECTION_TABLES.items():
        rows = db.execute(
            f"SELECT * FROM {table} WHERE declaration_id IN ({placeholders})",
            decl_ids,
        ).fetchall()
        for r in rows:
            d = dict(r)
            out[section][d["declaration_id"]].append(d)
    return out
