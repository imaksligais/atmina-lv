"""Year-over-year delta engine for VAD section rows.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

DELTA_THRESHOLD_PCT = 5.0  # below this = "unchanged"


@dataclass
class DeltaRow:
    payload: dict
    delta: str  # "new" | "removed" | "unchanged" | "modified"
    diff_text: Optional[str] = None


# Identity-key extractor per section. Each returns a hashable tuple.
IDENTITY_KEYS: dict[str, Callable[[dict], tuple]] = {
    "positions": lambda r: (r["position_title"], r.get("entity_reg_number") or r["entity_name"]),
    "real_estate": lambda r: (r["property_type"], r["location"], r["ownership_status"]),
    "companies": lambda r: (r.get("reg_number") or r["company_name"], r["capital_kind"]),
    "vehicles": lambda r: (r["brand"], r.get("year_made"), r["ownership_status"]),
    "savings": lambda r: (r["savings_kind"], r["currency"], r.get("holder_reg_number") or "_cash_"),
    "income": lambda r: (r["source"], r["income_type"], r["currency"]),
    "transactions": lambda r: (r["transaction_description"], r.get("currency")),
    "debts": lambda r: (r.get("creditor_reg_number") or r["creditor_name"], r["currency"]),
    "loans_given": lambda r: (r["currency"], r.get("amount_in_words") or ""),
    "family": lambda r: (r["full_name"],),
}

# Numerical fields per section to compare for "modified" detection.
NUMERIC_FIELDS: dict[str, list[str]] = {
    "positions": [],
    "real_estate": [],
    "companies": ["units", "total_value"],
    "vehicles": [],
    "savings": ["amount"],
    "income": ["amount"],
    "transactions": ["amount"],
    "debts": ["amount"],
    "loans_given": [],
    "family": [],
}


def _pct_change(prev: float, curr: float) -> float:
    if prev == 0:
        return float("inf") if curr != 0 else 0.0
    return abs((curr - prev) / prev) * 100.0


def _format_diff_text(section: str, prev: dict, curr: dict) -> Optional[str]:
    parts = []
    for field in NUMERIC_FIELDS.get(section, []):
        pv, cv = prev.get(field), curr.get(field)
        if pv is None or cv is None:
            continue
        if pv != cv:
            pct = _pct_change(pv, cv)
            sign = "+" if cv > pv else "-"
            parts.append(f"{field}: {pv:.0f} → {cv:.0f} ({sign}{pct:.0f}%)")
    if section == "real_estate" and prev.get("ownership_status") != curr.get("ownership_status"):
        parts.append(f"statuss: {prev['ownership_status']} → {curr['ownership_status']}")
    return ", ".join(parts) if parts else None


def compute_section_deltas(
    section: str,
    prev_year_rows: list[dict],
    this_year_rows: list[dict],
) -> list[DeltaRow]:
    """Compute delta markieri vienai sekcijai.

    Atgriezs visu THIS-year rindas + REMOVED rindas (kas bija prev bet nav this).
    Sorteta: modified > new > removed > unchanged.
    """
    if section not in IDENTITY_KEYS:
        return [DeltaRow(payload=r, delta="unchanged") for r in this_year_rows]

    key_fn = IDENTITY_KEYS[section]
    prev_by_key = {key_fn(r): r for r in prev_year_rows}
    this_by_key = {key_fn(r): r for r in this_year_rows}

    out: list[DeltaRow] = []
    for k, r in this_by_key.items():
        if k not in prev_by_key:
            out.append(DeltaRow(payload=r, delta="new"))
        else:
            prev = prev_by_key[k]
            modified = False
            for field in NUMERIC_FIELDS.get(section, []):
                pv, cv = prev.get(field), r.get(field)
                if pv is None or cv is None:
                    continue
                if _pct_change(pv, cv) >= DELTA_THRESHOLD_PCT:
                    modified = True
                    break
            if section == "real_estate" and prev.get("ownership_status") != r.get("ownership_status"):
                modified = True
            if modified:
                out.append(DeltaRow(payload=r, delta="modified",
                                    diff_text=_format_diff_text(section, prev, r)))
            else:
                out.append(DeltaRow(payload=r, delta="unchanged"))
    for k, r in prev_by_key.items():
        if k not in this_by_key:
            out.append(DeltaRow(payload=r, delta="removed"))

    rank = {"modified": 0, "new": 1, "removed": 2, "unchanged": 3}
    out.sort(key=lambda d: rank[d.delta])
    return out
