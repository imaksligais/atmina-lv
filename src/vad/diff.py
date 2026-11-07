"""Year-over-year delta engine for VAD section rows.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.2
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Optional

DELTA_THRESHOLD_PCT = 5.0  # below this = "unchanged"


@dataclass
class DeltaRow:
    payload: dict
    delta: str  # "new" | "removed" | "unchanged" | "modified"
    diff_text: Optional[str] = None


def _norm_name(text: Optional[str]) -> str:
    """Iestādes nosaukums salīdzināšanai: bez reģistra, pēdiņām un liekām atstarpēm
    («Eiropas Parlaments» = «Eiropas parlaments»)."""
    return " ".join(re.sub(r"[\"'«»„“”]", " ", text or "").casefold().split())


def _position_entity(r: dict) -> str:
    return r.get("entity_reg_number") or _norm_name(r.get("entity_name"))


# Identity-key extractor per section. Each returns a hashable tuple.
IDENTITY_KEYS: dict[str, Callable[[dict], tuple]] = {
    "positions": lambda r: (r["position_title"], _position_entity(r)),
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


# Lasītājam redzamie lauku nosaukumi diff tekstā (kolonnu nosaukumi ir angliski).
FIELD_LABELS_LV = {"amount": "summa", "units": "skaits", "total_value": "vērtība"}


def _format_diff_text(section: str, prev: dict, curr: dict) -> Optional[str]:
    from src.render._common.filters import _lv_number

    parts = []
    for field in NUMERIC_FIELDS.get(section, []):
        pv, cv = prev.get(field), curr.get(field)
        if pv is None or cv is None:
            continue
        if pv != cv:
            label = FIELD_LABELS_LV.get(field, field)
            text = f"{label}: {_lv_number(pv)} → {_lv_number(cv)}"
            if pv != 0:  # no nulles procentu nav («+inf %»)
                sign = "+" if cv > pv else "−"
                text += f" ({sign}{_pct_change(pv, cv):.0f}\u00a0%)"
            parts.append(text)
    if section == "real_estate" and prev.get("ownership_status") != curr.get("ownership_status"):
        parts.append(f"statuss: {prev['ownership_status']} → {curr['ownership_status']}")
    return ", ".join(parts) if parts else None


def _pair_renamed_positions(rows: list[DeltaRow]) -> list[DeltaRow]:
    """Tajā pašā iestādē pārdēvēts amats ir viena «mainījies» rinda, ne «jauns» + «vairs nav».

    VID deklarācijā viens amats gadu no gada mēdz saukties citādi («Eiropas
    Parlamenta deputāte» → «Deputāts»). Pārī liek tikai tad, ja iestādē ir
    tieši viena jauna un viena izzudusi rinda — divas pret divām nevar
    sapārot droši, tās paliek kā ir.
    """
    new_by, removed_by = {}, {}
    for d in rows:
        if d.delta == "new":
            new_by.setdefault(_position_entity(d.payload), []).append(d)
        elif d.delta == "removed":
            removed_by.setdefault(_position_entity(d.payload), []).append(d)
    out = [d for d in rows if d.delta not in ("new", "removed")]
    for ent in set(new_by) | set(removed_by):
        news, gone = new_by.get(ent, []), removed_by.get(ent, [])
        if ent and len(news) == 1 and len(gone) == 1:
            prev_title = gone[0].payload["position_title"]
            out.append(DeltaRow(payload=news[0].payload, delta="modified",
                                diff_text=f"amats: {prev_title} → {news[0].payload['position_title']}"))
        else:
            out.extend(news + gone)
    return out


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
    # Multiset: vienāds atslēgu skaits abos gados atbilst pa pair; liekās
    # kopas ir "new"/"removed". Bez tā (plain dict) deklarācijas ar
    # vairākām vienādas atslēgas rindām (piem., divi parādi EUR) klusi
    # saliptu vienā — renderētā daļa būtu mazāka nekā DB.
    prev_by_key: dict[tuple, list[dict]] = {}
    for r in prev_year_rows:
        prev_by_key.setdefault(key_fn(r), []).append(r)
    this_by_key: dict[tuple, list[dict]] = {}
    for r in this_year_rows:
        this_by_key.setdefault(key_fn(r), []).append(r)

    out: list[DeltaRow] = []
    for k, rows in this_by_key.items():
        prevs = prev_by_key.get(k, [])
        for i, r in enumerate(rows):
            if i >= len(prevs):
                out.append(DeltaRow(payload=r, delta="new"))
                continue
            prev = prevs[i]
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
    for k, rows in prev_by_key.items():
        for r in rows[len(this_by_key.get(k, [])):]:
            out.append(DeltaRow(payload=r, delta="removed"))

    if section == "positions":
        out = _pair_renamed_positions(out)

    rank = {"modified": 0, "new": 1, "removed": 2, "unchanged": 3}
    out.sort(key=lambda d: rank[d.delta])
    return out
