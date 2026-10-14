"""Render-time pre-loader for VAD declarations.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.1

One-batch-per-tabula query strategy (F4 leaf-vs-fan-out paterns); avoids
N+1 queries when rendering 152 politician profile pages. Try/except
OperationalError guard for test DBs without init_vad_tables (saeima_bills
precedents src/render/politicians.py:503).
"""

from __future__ import annotations

import re
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
    label: str = ""
    sort_date: str = ""


# VID `declaration_type` teksta tips — NE `declaration_kind` kods: kods
# `interim` nes gan «stājoties amatā» (125), gan «Beidzot darbu - <datums>»
# (74), tāpēc nozīmi lasām no teksta. Secība svarīga: «par pirmo gadu»
# jāpārbauda pirms vispārīgā «beidzot».
_DECL_TYPE_RULES = (
    ("par pirmo gadu", "1. gads pēc amata"),
    ("par otro gadu", "2. gads pēc amata"),
    ("darba sākuma", "Stājoties amatā"),
    ("stājoties amatā", "Stājoties amatā"),
    ("beidzot", "Atstājot amatu"),
)
_LV_MONTHS = (
    ("janvār", 1), ("februār", 2), ("mart", 3), ("aprīl", 4), ("maij", 5),
    ("jūnij", 6), ("jūlij", 7), ("august", 8), ("septembr", 9),
    ("oktobr", 10), ("novembr", 11), ("decembr", 12),
)
_LV_DATE_RE = re.compile(r"(\d{4})\. gada (\d{1,2})\. (\w+)")
_ANNUAL_RE = re.compile(r"par (\d{4})\. gadu")


def declaration_label(
    type_text: Optional[str], submitted_at: Optional[str],
) -> tuple[str, str]:
    """(cilnes etiķete, kārtošanas datums ISO) vienai VID deklarācijai.

    Gada deklarācija → «2025» (kārtošanā perioda beigas, 2025-12-31).
    Pārējās → «<tips> · <gads>»; gads no teksta PĒDĒJĀ datuma (pēc-amata
    periodam «līdz 2015. gada …» → 2015), citādi no ``submitted_at``,
    citādi bez gada. Nezināms teksts → ``submitted_at`` gads vai
    «Deklarācija».
    """
    text = type_text or ""
    low = text.lower()
    fallback = submitted_at or ""
    annual = _ANNUAL_RE.search(text)
    if "kārtējā gada" in low and annual:
        return annual.group(1), f"{annual.group(1)}-12-31"

    date = ""
    for y, d, month_word in _LV_DATE_RE.findall(text):
        mw = month_word.lower()
        m = next((n for stem, n in _LV_MONTHS if mw.startswith(stem)), None)
        date = f"{y}-{m:02d}-{int(d):02d}" if m else f"{y}-12-31"
    sort_date = date or fallback
    year = sort_date[:4]

    kind_label = next((lbl for key, lbl in _DECL_TYPE_RULES if key in low), "")
    if not kind_label:
        return (year or "Deklarācija"), sort_date
    return (f"{kind_label} · {year}" if year else kind_label), sort_date


# Ienākuma avots VID tekstā: «<maksātājs>, <reģ. nr.>, <valsts>, <adrese>».
# Reģ. nr. ir ciparu virkne, ārvalstu «T0900000012» vai vietturis «AJ»
# (ārvalstu juridiska persona); fiziskām personām numura nav («Igors Šuvajevs, ,»).
_REG_NR_CUT_RE = re.compile(r",\s*(?:[A-Z]?\d{5,}|AJ)\s*(?:,|$)")
# Daži avoti nosaukuma vietā nes personas kodu («040481-18007, ,») — to nerādām.
_PERSONAL_CODE_RE = re.compile(r"\d{6}-\d{5}")


def payer_name(source: Optional[str]) -> str:
    """Tikai maksātāja nosaukums no VID ienākuma avota teksta — daļa pirms
    reģistrācijas numura, bez adreses un tukšajiem «, ,» laukiem. Nav
    nosaukuma (tukšs vai tikai personas kods) → tukša virkne."""
    text = (source or "").strip()
    m = _REG_NR_CUT_RE.search(text)
    if m:
        text = text[:m.start()]
    text = text.rstrip(" ,")
    return "" if _PERSONAL_CODE_RE.fullmatch(text) else text


def get_vad_data_for_politicians(
    db: sqlite3.Connection,
    pids: list[int],
) -> dict[int, list[VadDeclarationView]]:
    """Pre-load VAD data for given politicians.

    Returns: dict[pid] -> list[VadDeclarationView] sorted newest first by
    ``sort_date`` (sk. declaration_label). Katra deklarācija saņem delta
    marķierus pret hronoloģiski iepriekšējo; vecākajai delta nav.
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
        # views sorted sort_date DESC; newest = views[0], second = views[1]
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


@dataclass
class LatestAnnualCount:
    year: Optional[int]
    current: int        # rindas, kas ir jaunākajā ikgadējā deklarācijā
    removed: int        # iepriekšējās deklarācijas rindas, kuru te vairs nav
    prev_label: str     # hronoloģiski iepriekšējās deklarācijas etiķete ("" ja nav)

    @property
    def total(self) -> int:
        """Profila skaitlis sadaļas virsrakstā (pašreizējie + aizgājušie)."""
        return self.current + self.removed


def latest_annual_counts(
    db: sqlite3.Connection, pids: list[int], sections: list[str],
) -> dict[str, dict[int, LatestAnnualCount]]:
    """Profila skaiti jaunākajai ikgadējai deklarācijai: section -> pid -> count.

    Tā pati secība un delta kā profilam (``get_vad_data_for_politicians``) —
    salīdzina ar hronoloģiski iepriekšējo deklarāciju, arī bezgada stāšanās.
    Analīzes lapas ģenerators lieto šo, lai tā § 5/§ 6 nedreifētu no profila.
    """
    out: dict[str, dict[int, LatestAnnualCount]] = {s: {} for s in sections}
    for pid, views in get_vad_data_for_politicians(db, pids).items():
        i = next((i for i, v in enumerate(views) if v.kind == "annual"), None)
        if i is None:
            continue
        prev_label = views[i + 1].label if i + 1 < len(views) else ""
        for section in sections:
            deltas = views[i].sections.get(section, [])
            removed = sum(1 for d in deltas if d.delta == "removed")
            out[section][pid] = LatestAnnualCount(
                views[i].year, len(deltas) - removed, removed, prev_label,
            )
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
        label, sort_date = declaration_label(r["declaration_type"], r["submitted_at"])
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
            label=label, sort_date=sort_date,
        ))
    # Jaunākā pirmā pēc reālā datuma — SQL `declaration_year` ne-gada
    # deklarācijām ir NULL, tāpēc tās agrāk nogrima saraksta beigās.
    # Stabila kārtošana: vienāda datuma gadījumā paliek SQL secība.
    for views in out.values():
        views.sort(key=lambda v: (v.sort_date, v.submitted_at or ""), reverse=True)
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
            if section == "income":
                d["payer_name"] = payer_name(d.get("source"))
            out[section][d["declaration_id"]].append(d)
    return out
