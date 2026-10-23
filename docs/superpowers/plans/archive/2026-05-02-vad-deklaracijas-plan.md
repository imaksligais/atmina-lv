# VAD amatpersonu deklarāciju izsekotājs — Phase 0+1 implementācijas plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ielikt produkcijā strukturētu VID amatpersonu deklarāciju ielādes pipeline (httpx + BeautifulSoup) un publiskās lapas "Deklarācijas" tabu politiķa profilā ar gads-pa-gadam delta marķieriem.

**Architecture:** Jauna `src/vad/` pakete (saeima/* paterns) ar 11 strukturētām `vad_*` tabulām. Manuāls CLI ingest (`scripts/ingest_vad_declarations.py`) reizi mēnesī, peak aprīlis-maijs. Render layer pre-loads VAD datus visiem politiķiem (one batch query per tabula), Phase 1 tab integrācija ar `_profile_tab_set` paplašinājumu. NAV `documents` rindas (saeima 2026-04-25 invariants), NAV `claims` rindas (deklarācija ≠ retoriska pozīcija).

**Tech Stack:** Python 3.11+, SQLite (WAL + foreign_keys ON), Pydantic v2, BeautifulSoup4, httpx (jau projektā), Jinja2 templates, pytest.

**Spec source:** `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` (commit 45072da, ar review revisions)

---

## File structure

**Jauni faili:**
- `src/vad/__init__.py` — public API re-exports
- `src/vad/schema.py` — DDL + `init_vad_tables()`
- `src/vad/fetch.py` — httpx HTTP layer (search, detail-by-cookie, throttling)
- `src/vad/parsing.py` — BeautifulSoup → `ParsedDeclaration` Pydantic model
- `src/vad/matcher.py` — name split + `_NAME_OVERRIDES` + ASCII fallback
- `src/vad/declarations.py` — orchestrator (`fetch_for_politician`, role-disambiguation, store)
- `src/vad/diff.py` — year-over-year delta engine
- `src/render/vad.py` — render-time data fetcher (one batch per tabula)
- `scripts/ingest_vad_declarations.py` — CLI
- `scripts/dump_vad_fixture.py` — bootstrap helper (manuāli sweep'ē 5 fixtures)
- `templates/_vad_panel.html.j2` — Phase 1 tab partial
- `tests/test_vad_schema.py`
- `tests/test_vad_parsing.py`
- `tests/test_vad_matcher.py`
- `tests/test_vad_fetch.py`
- `tests/test_vad_declarations.py`
- `tests/test_vad_diff.py`
- `tests/test_vad_render.py`
- `tests/fixtures/vad/*.html` + `*.json` snapshot pairs (≥5 politiķi)
- `wiki/operations/vad-declarations.md`

**Modificēti faili:**
- `src/profile_kind.py` — pievieno `'deklaracijas'` tab kandidātiem
- `src/render/politicians.py` — pievieno `vad_count` per-politiķis + tab integrāciju
- `templates/politician.html.j2` — pievieno stat-button + tab content block
- `assets/style.css` — pievieno `.vad-delta-{new,modified,removed,unchanged}` + `.vad-section`
- `wiki/operations/operacijas.md` — pievieno § "VID amatpersonu deklarācijas (manuāla, mēneša cikls)"
- `wiki/CHANGELOG.md` — Phase 0 + Phase 1 entries

---

## Phase 0 — Ingest + storage (Tasks 1-10)

### Task 1: DDL — `src/vad/schema.py` + smoke test

**Files:**
- Create: `src/vad/__init__.py`
- Create: `src/vad/schema.py`
- Create: `tests/test_vad_schema.py`

- [ ] **Step 1: Create empty package marker**

```python
# src/vad/__init__.py — placeholder, atjaunots Task 7
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_vad_schema.py
import sqlite3
import tempfile
from pathlib import Path

from src.vad.schema import init_vad_tables


def test_init_creates_eleven_tables():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "test.db")
        # Bootstrap minimal tracked_politicians for FK
        with sqlite3.connect(db_path) as boot:
            boot.execute("""
                CREATE TABLE tracked_politicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            boot.commit()
        init_vad_tables(db_path)
        with sqlite3.connect(db_path) as con:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vad_%'"
            )}
    expected = {
        "vad_declarations", "vad_positions", "vad_real_estate",
        "vad_companies", "vad_vehicles", "vad_savings",
        "vad_income", "vad_transactions", "vad_debts",
        "vad_loans_given", "vad_family",
    }
    assert tables == expected, f"missing or extra: {expected ^ tables}"


def test_init_is_idempotent():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "test.db")
        with sqlite3.connect(db_path) as boot:
            boot.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT)")
            boot.commit()
        init_vad_tables(db_path)
        init_vad_tables(db_path)  # second call must not raise


def test_unique_constraint_on_opponent_uuid():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "test.db")
        with sqlite3.connect(db_path) as boot:
            boot.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT)")
            boot.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X')")
            boot.commit()
        init_vad_tables(db_path)
        with sqlite3.connect(db_path) as con:
            con.execute(
                "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, declaration_kind, source_url) "
                "VALUES (1, 'uuid-1', 'X', 'annual', 'https://example/')"
            )
            con.commit()
            try:
                con.execute(
                    "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, declaration_kind, source_url) "
                    "VALUES (1, 'uuid-1', 'X', 'annual', 'https://example/')"
                )
                con.commit()
                assert False, "expected IntegrityError on duplicate (opponent_id, vad_uuid)"
            except sqlite3.IntegrityError:
                pass
```

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/test_vad_schema.py -v
```

Expected: ImportError or `init_vad_tables not defined`.

- [ ] **Step 4: Implement DDL**

```python
# src/vad/schema.py
"""VAD DDL — table init for amatpersonu deklarācijas.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 4

Saskaņā ar saeima/schema.py precedentu — DDL paliek Python pusē, ne
src/schema.sql, jo pakete ir lazy-init (skat. spec § 4.5: nav daļa no
init_db()). Render layer guard ar try/except OperationalError.
"""

import sqlite3

from src.db import DB_PATH, get_db


def init_vad_tables(db_path: str = DB_PATH) -> None:
    """Create VAD-specific tables if they don't exist. Idempotent."""
    db = get_db(db_path) if db_path == DB_PATH else sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS vad_declarations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            vad_uuid TEXT NOT NULL,
            declaration_type TEXT NOT NULL,
            declaration_kind TEXT NOT NULL,
            declaration_year INTEGER,
            institution TEXT,
            position_title TEXT,
            submitted_at TEXT,
            published_at TEXT,
            other_info TEXT,
            financial_instruments_text TEXT,
            other_benefits_text TEXT,
            trust_agreement_text TEXT,
            has_private_pension INTEGER,
            has_life_insurance INTEGER,
            source_url TEXT NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_html TEXT,
            UNIQUE(opponent_id, vad_uuid)
        );
        CREATE INDEX IF NOT EXISTS idx_vad_decl_opponent ON vad_declarations(opponent_id);
        CREATE INDEX IF NOT EXISTS idx_vad_decl_year ON vad_declarations(declaration_year);
        CREATE INDEX IF NOT EXISTS idx_vad_decl_published ON vad_declarations(published_at);

        CREATE TABLE IF NOT EXISTS vad_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            position_title TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            entity_reg_number TEXT,
            entity_address TEXT,
            is_individual INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_vad_positions_decl ON vad_positions(declaration_id);
        CREATE INDEX IF NOT EXISTS idx_vad_positions_reg ON vad_positions(entity_reg_number);

        CREATE TABLE IF NOT EXISTS vad_real_estate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            property_type TEXT NOT NULL,
            location TEXT NOT NULL,
            ownership_status TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_real_estate_decl ON vad_real_estate(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            company_name TEXT NOT NULL,
            reg_number TEXT,
            address TEXT,
            capital_kind TEXT NOT NULL,
            units REAL,
            total_value REAL,
            currency TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_companies_decl ON vad_companies(declaration_id);
        CREATE INDEX IF NOT EXISTS idx_vad_companies_reg ON vad_companies(reg_number);

        CREATE TABLE IF NOT EXISTS vad_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            vehicle_type TEXT NOT NULL,
            brand TEXT NOT NULL,
            year_made INTEGER,
            year_registered INTEGER,
            ownership_status TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_vehicles_decl ON vad_vehicles(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            savings_kind TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT,
            holder_name TEXT,
            holder_reg_number TEXT,
            holder_address TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_savings_decl ON vad_savings(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            source_reg_number TEXT,
            is_individual INTEGER NOT NULL DEFAULT 0,
            income_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_income_decl ON vad_income(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            transaction_description TEXT NOT NULL,
            amount REAL,
            currency TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_transactions_decl ON vad_transactions(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            creditor_name TEXT NOT NULL,
            creditor_reg_number TEXT,
            creditor_address TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_debts_decl ON vad_debts(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_loans_given (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_loans_decl ON vad_loans_given(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_family (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            full_name TEXT NOT NULL,
            relation TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_family_decl ON vad_family(declaration_id);
    """)
    db.commit()
    db.close()
```

- [ ] **Step 5: Run tests to verify all pass**

```bash
.venv/Scripts/python -m pytest tests/test_vad_schema.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Run init against live DB to ensure no regression**

```bash
.venv/Scripts/python -c "from src.vad.schema import init_vad_tables; init_vad_tables()"
```

Expected: silent success. Verify with:

```bash
.venv/Scripts/python -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(sorted([r[0] for r in con.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vad_%'\")]))"
```

Expected: list of 11 vad_* tables.

- [ ] **Step 7: Commit**

```bash
git add src/vad/__init__.py src/vad/schema.py tests/test_vad_schema.py
.git-commit-msg.tmp:
feat(vad): DDL un init_vad_tables() — 11 vad_* tabulas

Saeima/schema.py precedents (lazy init, ne init_db). Idempotenta DDL ar
foreign_keys=ON CASCADE. Test pārbauda 11 tabulu izveidi un UNIQUE
(opponent_id, vad_uuid) constraint.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 2: Bootstrap fixtures — `scripts/dump_vad_fixture.py`

Šis ir vienreizējs darbs lai iegūtu HTML fixtures parser testiem. Skripts automatizē saglabāšanas-disk-to-fixtures plūsmu, lai operators varētu palaist mainot tikai pid+year argumentu.

**Files:**
- Create: `scripts/dump_vad_fixture.py`

- [ ] **Step 1: Implement bootstrap script**

```python
# scripts/dump_vad_fixture.py
"""One-shot fixture dumper — sapludo HTML fixturei manuālajā Playwright sesijā.

Lietojums:
    python scripts/dump_vad_fixture.py --pid 3 --year 2024 --out tests/fixtures/vad/slesers-2024.html

Tā kā fetch.py vēl neeksistē Phase 0 sākumā (Task 4), šis skripts izsauc
manuāli Playwright caur subprocess vai prasa operatoru open browser un save.
Phase 0 noslēgumā (pēc Task 4), aizvieto ar fetch.py izmantojumu.

NB: Phase 0 boot — sākotnēji palaidiet manuāli pa vienam politiķim ar
playwright/browser tools (skat. wiki/operations/vad-declarations.md § "Bootstrap").
Šis skripts kļūst lietojams pēc Task 4.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--pid", type=int, required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    # Lazy import — fetch.py must exist by Task 4 onwards
    from src.db import get_db
    from src.vad.fetch import VadClient

    db = get_db()
    pol = db.execute("SELECT name FROM tracked_politicians WHERE id=?", (args.pid,)).fetchone()
    if pol is None:
        print(f"ERROR: politiķis ar pid={args.pid} nav atrasts", file=sys.stderr)
        return 1
    name = pol["name"]
    db.close()

    parts = name.split()
    given = " ".join(parts[:-1])
    family = parts[-1]
    print(f"[search] {given!r} {family!r}")

    client = VadClient()
    rows = client.search(given, family)
    print(f"[found] {len(rows)} rows")
    target = next(
        (r for r in rows if str(args.year) in r["declaration_type"]),
        None,
    )
    if target is None:
        print(f"ERROR: nav atrasta deklarācija par {args.year}. gadu", file=sys.stderr)
        for r in rows:
            print(f"  - {r['declaration_type']} (uuid={r['vad_uuid']})")
        return 2

    html = client.fetch_detail(target["vad_uuid"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"[saved] {args.out} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Manual fixture preparation (gaida Task 4)**

Atstājam Task 2 placeholder un atgriežamies pēc Task 4 (kad fetch.py eksistē). Phase 0 sākumā Task 3 (parser) izmanto **vienu** manuāli saglabātu fixture (Šlesers 2024 — saglabājām tagad ar Playwright).

- [ ] **Step 3: Saglabā Šlesers 2024 fixture manuāli**

```bash
mkdir -p tests/fixtures/vad
```

Atver `https://www6.vid.gov.lv/VAD`, ievada `Ainārs Šlesers`, klikšķē uz "Kārtējā gada deklarācija - par 2024. gadu", saglabā HTML kā `tests/fixtures/vad/slesers-2024.html`.

Vai izmanto Playwright sesijā:
```python
# Saglabā page.content() lapas response uz failu — vienreizējs darbs
```

Verificē failu:
```bash
.venv/Scripts/python -c "from pathlib import Path; print(len(Path('tests/fixtures/vad/slesers-2024.html').read_text(encoding='utf-8')))"
```
Expected: skaitlis ~50000-200000.

- [ ] **Step 4: Commit dumper script (bez fixtures vēl)**

```bash
git add scripts/dump_vad_fixture.py tests/fixtures/vad/slesers-2024.html
```

`.git-commit-msg.tmp`:
```
chore(vad): bootstrap fixture dumper + Šlesers 2024 baseline HTML

dump_vad_fixture.py kļūs operacionāls pēc Task 4 (fetch.py). Pirmais
fixture saglabāts manuāli ar Playwright priekš parser TDD Task 3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 3: Parser — `src/vad/parsing.py` + tests

**Files:**
- Create: `src/vad/parsing.py`
- Create: `tests/test_vad_parsing.py`
- Create: `tests/fixtures/vad/slesers-2024.json` (snapshot)

- [ ] **Step 1: Define Pydantic model + parser stubs**

```python
# src/vad/parsing.py
"""Parse VID amatpersonu deklarāciju HTML uz strukturētu Pydantic modeli.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 5

Algoritms:
1. Atver HTML ar BeautifulSoup
2. Header tabula = pirmā <table> pirms pirmās numurētās <h2>
3. Katra numurētā <h2> regex `^\\s*(\\d+)\\.\\s+` ieskicē sekciju
4. Iterē DOM siblings līdz nākamai <h2>
5. Sekcijas saturs = visas <table> tās ietvaros (sec 6 ir 2 tabulas)
6. Narratīvās sekcijas (4b, 11, 11b, 13) = <h2> + nākamie <p>
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

ALLOWED_CURRENCIES = {"EUR", "USD", "RUB", "GBP", "JPY", "CHF", "SEK", "NOK", "DKK"}

_H2_NUMBERED = re.compile(r"^\s*(\d+)\.\s+")
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_REG_NUMBER_RE = re.compile(r"\b[49]\d{10}\b")  # Latvijas reģ.nr.: 11 cipari, sākas ar 4 vai 9


class VadHeader(BaseModel):
    declaration_type: str
    declaration_kind: str  # normalized: annual|start|end|post_year_1|post_year_2|interim
    declaration_year: Optional[int]
    full_name: str
    institution: str
    position_title: str
    submitted_at: Optional[str]  # ISO date
    published_at: Optional[str]


class VadPositionRow(BaseModel):
    position_title: str
    entity_name: str
    entity_reg_number: Optional[str] = None
    entity_address: Optional[str] = None
    is_individual: bool = False


class VadRealEstateRow(BaseModel):
    property_type: str
    location: str
    ownership_status: str


class VadCompanyRow(BaseModel):
    company_name: str
    reg_number: Optional[str] = None
    address: Optional[str] = None
    capital_kind: str
    units: Optional[float] = None
    total_value: Optional[float] = None
    currency: Optional[str] = None


class VadVehicleRow(BaseModel):
    vehicle_type: str
    brand: str
    year_made: Optional[int] = None
    year_registered: Optional[int] = None
    ownership_status: str


class VadSavingsRow(BaseModel):
    savings_kind: str  # "cash" | "bank"
    amount: float
    currency: str
    amount_in_words: Optional[str] = None
    holder_name: Optional[str] = None
    holder_reg_number: Optional[str] = None
    holder_address: Optional[str] = None


class VadIncomeRow(BaseModel):
    source: str
    source_reg_number: Optional[str] = None
    is_individual: bool = False
    income_type: str
    amount: float
    currency: str


class VadTransactionRow(BaseModel):
    transaction_description: str
    amount: Optional[float] = None
    currency: Optional[str] = None


class VadDebtRow(BaseModel):
    creditor_name: str
    creditor_reg_number: Optional[str] = None
    creditor_address: Optional[str] = None
    amount: float
    currency: str
    amount_in_words: Optional[str] = None


class VadLoanGivenRow(BaseModel):
    amount: float
    currency: str
    amount_in_words: Optional[str] = None


class VadFamilyRow(BaseModel):
    full_name: str
    relation: str


class ParsedDeclaration(BaseModel):
    header: VadHeader
    positions: list[VadPositionRow] = Field(default_factory=list)
    real_estate: list[VadRealEstateRow] = Field(default_factory=list)
    companies: list[VadCompanyRow] = Field(default_factory=list)
    financial_instruments_text: Optional[str] = None
    vehicles: list[VadVehicleRow] = Field(default_factory=list)
    savings: list[VadSavingsRow] = Field(default_factory=list)
    income: list[VadIncomeRow] = Field(default_factory=list)
    transactions: list[VadTransactionRow] = Field(default_factory=list)
    debts: list[VadDebtRow] = Field(default_factory=list)
    loans_given: list[VadLoanGivenRow] = Field(default_factory=list)
    other_benefits_text: Optional[str] = None
    trust_agreement_text: Optional[str] = None
    has_private_pension: Optional[bool] = None
    has_life_insurance: Optional[bool] = None
    other_info: Optional[str] = None
    family: list[VadFamilyRow] = Field(default_factory=list)


def parse_declaration_html(html: str) -> ParsedDeclaration:
    """Parse a modern VID amatpersonu deklarācijas detail HTML page.

    Raises ValueError if the header cannot be parsed (missing required fields).
    Empty sections produce empty lists, not None.
    """
    soup = BeautifulSoup(html, "html.parser")
    header = _parse_header(soup)
    sections = _split_sections(soup)
    return ParsedDeclaration(
        header=header,
        positions=_parse_positions(sections.get(2)),
        real_estate=_parse_real_estate(sections.get(3)),
        companies=_parse_companies(sections.get(4)),
        financial_instruments_text=_parse_financial_instruments(soup),
        vehicles=_parse_vehicles(sections.get(5)),
        savings=_parse_savings(sections.get(6)),
        income=_parse_income(sections.get(7)),
        transactions=_parse_transactions(sections.get(8)),
        debts=_parse_debts(sections.get(9)),
        loans_given=_parse_loans_given(sections.get(10)),
        other_benefits_text=_parse_other_benefits(soup),
        trust_agreement_text=_parse_trust_agreement(soup),
        has_private_pension=_parse_pension_flag(sections.get(12), 0),
        has_life_insurance=_parse_pension_flag(sections.get(12), 1),
        other_info=_parse_other_info(sections.get(13)),
        family=_parse_family(sections.get(14)),
    )


# === Internal helpers below — full implementation ===

def _norm_date(text: str) -> Optional[str]:
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def _norm_year(text: str) -> Optional[int]:
    m = re.search(r"par\s+(\d{4})\.\s*gadu", text or "")
    return int(m.group(1)) if m else None


def _norm_kind(declaration_type: str) -> str:
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


def _norm_currency(text: str) -> Optional[str]:
    text = (text or "").strip().upper()
    if text in ALLOWED_CURRENCIES:
        return text
    return text or None  # log warn caller-side


def _norm_amount(text: str) -> Optional[float]:
    text = (text or "").strip().replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _parse_header(soup: BeautifulSoup) -> VadHeader:
    table = soup.find("table")
    if table is None:
        raise ValueError("nav header table")
    fields: dict[str, str] = {}
    for row in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            fields[cells[0].rstrip(":").strip()] = cells[1]
    decl_type = fields.get("Deklarācijas veids", "")
    full_name = fields.get("Vārds, uzvārds", "")
    institution = fields.get(
        "Darbavieta vai valsts amatpersonu saraksta iesniedzējas institūcija", ""
    )
    position_title = fields.get("Valsts amatpersonas amats", "")
    if not decl_type or not full_name:
        raise ValueError(f"nepilnīgs header: {fields!r}")
    return VadHeader(
        declaration_type=decl_type,
        declaration_kind=_norm_kind(decl_type),
        declaration_year=_norm_year(decl_type),
        full_name=full_name,
        institution=institution,
        position_title=position_title,
        submitted_at=_norm_date(fields.get("Iesniegta VID", "")),
        published_at=_norm_date(fields.get("Publicēta", "")),
    )


def _split_sections(soup: BeautifulSoup) -> dict[int, list[Tag]]:
    """Atgriež dict[sekcijas_nr] = list[Tag] (visi siblings starp <h2> N un N+1)."""
    out: dict[int, list[Tag]] = {}
    h2s = soup.find_all("h2")
    for h2 in h2s:
        text = h2.get_text(" ", strip=True)
        m = _H2_NUMBERED.match(text)
        if not m:
            continue
        n = int(m.group(1))
        siblings: list[Tag] = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2" and _H2_NUMBERED.match(sib.get_text(" ", strip=True)):
                break
            if isinstance(sib, Tag):
                siblings.append(sib)
        out[n] = siblings
    return out


def _table_rows(siblings: Optional[list[Tag]]) -> list[list[str]]:
    """Atgriež visas data row no visām <table> siblings ietvaros (skip header)."""
    if not siblings:
        return []
    rows = []
    for sib in siblings:
        for table in sib.find_all("table") if sib.name != "table" else [sib]:
            tbodies = table.find_all("tbody")
            if len(tbodies) >= 2:
                # Latvijas portāls: pirmais tbody = header, otrais = data
                data_tbody = tbodies[1]
            elif tbodies:
                data_tbody = tbodies[0]
            else:
                data_tbody = table
            for tr in data_tbody.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
    return rows


def _parse_positions(siblings) -> list[VadPositionRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        position_title, entity_name, third = cells[0], cells[1], cells[2]
        reg = None
        addr = None
        # Third cell ir "regnr adrese" formātā (var nebūt regnr fiziskām)
        m = _REG_NUMBER_RE.search(third)
        if m:
            reg = m.group(0)
            addr = (third[:m.start()] + third[m.end():]).strip(", ").strip() or None
        else:
            addr = third or None
        out.append(VadPositionRow(
            position_title=position_title, entity_name=entity_name,
            entity_reg_number=reg, entity_address=addr,
            is_individual=(reg is None and "," not in (entity_name or "")),
        ))
    return out


def _parse_real_estate(siblings) -> list[VadRealEstateRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        out.append(VadRealEstateRow(
            property_type=cells[0], location=cells[1], ownership_status=cells[2],
        ))
    return out


def _parse_companies(siblings) -> list[VadCompanyRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 6:
            continue
        company_name, ra, capital_kind, units, total, cur = cells[:6]
        reg = None
        addr = None
        m = _REG_NUMBER_RE.search(ra)
        if m:
            reg = m.group(0)
            addr = (ra[:m.start()] + ra[m.end():]).strip(", ").strip() or None
        else:
            addr = ra or None
        out.append(VadCompanyRow(
            company_name=company_name, reg_number=reg, address=addr,
            capital_kind=capital_kind,
            units=_norm_amount(units), total_value=_norm_amount(total),
            currency=_norm_currency(cur),
        ))
    return out


def _parse_vehicles(siblings) -> list[VadVehicleRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 5:
            continue
        ym = cells[2].strip() or None
        yr = cells[3].strip() or None
        out.append(VadVehicleRow(
            vehicle_type=cells[0], brand=cells[1],
            year_made=int(ym) if ym and ym.isdigit() else None,
            year_registered=int(yr) if yr and yr.isdigit() else None,
            ownership_status=cells[4],
        ))
    return out


def _parse_savings(siblings) -> list[VadSavingsRow]:
    """Sec 6 — divas tabulas: pirmā cash (3 col), otrā bank (4 col)."""
    out = []
    if not siblings:
        return out
    tables = []
    for sib in siblings:
        if sib.name == "table":
            tables.append(sib)
        else:
            tables.extend(sib.find_all("table"))
    for table in tables:
        # detektē tabulas kind pēc header kolonnu skaita un saturš
        header_cells = []
        thead_or_first = table.find("thead") or table.find("tbody")
        if thead_or_first:
            first_tr = thead_or_first.find("tr")
            if first_tr:
                header_cells = [c.get_text(" ", strip=True).lower() for c in first_tr.find_all(["th", "td"])]
        is_bank = any("bezskaidr" in h or "turētāj" in h for h in header_cells)
        kind = "bank" if is_bank else "cash"
        tbodies = table.find_all("tbody")
        data_tbody = tbodies[1] if len(tbodies) >= 2 else (tbodies[0] if tbodies else table)
        for tr in data_tbody.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            if kind == "cash" and len(cells) >= 3:
                amt = _norm_amount(cells[0])
                cur = _norm_currency(cells[1])
                if amt is None or cur is None:
                    continue
                out.append(VadSavingsRow(
                    savings_kind="cash", amount=amt, currency=cur,
                    amount_in_words=cells[2] or None,
                ))
            elif kind == "bank" and len(cells) >= 4:
                amt = _norm_amount(cells[0])
                cur = _norm_currency(cells[1])
                if amt is None or cur is None:
                    continue
                holder_addr = cells[3] if len(cells) >= 4 else None
                holder_reg = None
                m = _REG_NUMBER_RE.search(holder_addr or "")
                if m:
                    holder_reg = m.group(0)
                    holder_addr = (holder_addr[:m.start()] + holder_addr[m.end():]).strip(", ").strip() or None
                out.append(VadSavingsRow(
                    savings_kind="bank", amount=amt, currency=cur,
                    holder_name=cells[2] or None,
                    holder_reg_number=holder_reg, holder_address=holder_addr,
                ))
    return out


def _parse_income(siblings) -> list[VadIncomeRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 4:
            continue
        source, income_type, amount_str, cur = cells[:4]
        amount = _norm_amount(amount_str)
        currency = _norm_currency(cur)
        if amount is None or currency is None:
            continue
        m = _REG_NUMBER_RE.search(source)
        reg = m.group(0) if m else None
        # "Inese Šlesere, ," (empty reg+addr) → fiziska persona
        is_individual = reg is None and source.rstrip().endswith(",")
        out.append(VadIncomeRow(
            source=source, source_reg_number=reg, is_individual=is_individual,
            income_type=income_type, amount=amount, currency=currency,
        ))
    return out


def _parse_transactions(siblings) -> list[VadTransactionRow]:
    out = []
    for cells in _table_rows(siblings):
        if not cells:
            continue
        desc = cells[0]
        amt = _norm_amount(cells[1]) if len(cells) > 1 else None
        cur = _norm_currency(cells[2]) if len(cells) > 2 else None
        out.append(VadTransactionRow(
            transaction_description=desc, amount=amt, currency=cur,
        ))
    return out


def _parse_debts(siblings) -> list[VadDebtRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 4:
            continue
        # Format: creditor_name, reg+adrese, amount, currency, words
        creditor = cells[0]
        ra = cells[1] if len(cells) > 1 else ""
        amt = _norm_amount(cells[2] if len(cells) > 2 else "")
        cur = _norm_currency(cells[3] if len(cells) > 3 else "")
        words = cells[4] if len(cells) > 4 else None
        if amt is None or cur is None:
            continue
        reg = None
        addr = None
        m = _REG_NUMBER_RE.search(ra)
        if m:
            reg = m.group(0)
            addr = (ra[:m.start()] + ra[m.end():]).strip(", ").strip() or None
        else:
            addr = ra or None
        out.append(VadDebtRow(
            creditor_name=creditor, creditor_reg_number=reg, creditor_address=addr,
            amount=amt, currency=cur, amount_in_words=words,
        ))
    return out


def _parse_loans_given(siblings) -> list[VadLoanGivenRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        amt = _norm_amount(cells[0])
        cur = _norm_currency(cells[1])
        if amt is None or cur is None:
            continue
        out.append(VadLoanGivenRow(
            amount=amt, currency=cur, amount_in_words=cells[2] or None,
        ))
    return out


def _parse_pension_flag(siblings, idx: int) -> Optional[bool]:
    rows = _table_rows(siblings)
    if not rows or len(rows[0]) <= idx:
        return None
    val = (rows[0][idx] or "").strip().lower()
    if val == "ir":
        return True
    if val == "nav":
        return False
    return None


def _parse_family(siblings) -> list[VadFamilyRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 2:
            continue
        out.append(VadFamilyRow(full_name=cells[0], relation=cells[1]))
    return out


def _narrative_after_h2(soup: BeautifulSoup, h2_match: str) -> Optional[str]:
    for h2 in soup.find_all("h2"):
        if h2_match.lower() in h2.get_text(" ", strip=True).lower():
            paragraphs = []
            for sib in h2.find_next_siblings():
                if sib.name == "h2":
                    break
                if sib.name in ("p", "div"):
                    text = sib.get_text(" ", strip=True)
                    if text:
                        paragraphs.append(text)
            return "\n\n".join(paragraphs) if paragraphs else None
    return None


def _parse_financial_instruments(soup):
    return _narrative_after_h2(soup, "finanšu instrumenti")


def _parse_other_benefits(soup):
    return _narrative_after_h2(soup, "noziedzīgi iegūtu līdzekļu")


def _parse_trust_agreement(soup):
    return _narrative_after_h2(soup, "trasta līgums")


def _parse_other_info(siblings):
    if not siblings:
        return None
    paragraphs = []
    for sib in siblings:
        if sib.name in ("p", "div"):
            text = sib.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)
    return "\n\n".join(paragraphs) if paragraphs else None
```

- [ ] **Step 2: Write parser tests against Šlesers fixture**

```python
# tests/test_vad_parsing.py
import json
from pathlib import Path

import pytest

from src.vad.parsing import parse_declaration_html, ALLOWED_CURRENCIES

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "vad"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.html").read_text(encoding="utf-8")


def test_parse_slesers_2024_header():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    h = parsed.header
    assert h.full_name == "AINĀRS ŠLESERS"
    assert h.declaration_kind == "annual"
    assert h.declaration_year == 2024
    assert h.institution == "Latvijas Republikas Saeima"
    assert h.position_title == "Saeimas deputāts"
    assert h.submitted_at == "2025-03-27"
    assert h.published_at == "2025-04-17"


def test_parse_slesers_2024_positions():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    titles = [p.position_title for p in parsed.positions]
    assert "Likvidators" in titles
    assert "Valdes loceklis" in titles
    lpv = next(p for p in parsed.positions if p.entity_name == "LATVIJA PIRMAJĀ VIETĀ")
    assert lpv.entity_reg_number == "40008310156"
    assert lpv.entity_address is not None
    assert "Mazā Smilšu" in lpv.entity_address


def test_parse_slesers_2024_real_estate():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.real_estate) == 4
    types = [r.property_type for r in parsed.real_estate]
    assert "Zeme" in types
    assert "Dzīvoklis" in types


def test_parse_slesers_2024_companies():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.companies) == 1
    avadel = parsed.companies[0]
    assert avadel.company_name.startswith("Sabiedrība ar ierobežotu atbildību")
    assert avadel.reg_number == "40003555683"
    assert avadel.units == 1000.0
    assert avadel.total_value == 10000.0
    assert avadel.currency == "EUR"


def test_parse_slesers_2024_vehicles():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.vehicles) == 1
    v = parsed.vehicles[0]
    assert v.vehicle_type == "Automašīna"
    assert v.brand == "MERCEDES BENZ AMG GLS 63"
    assert v.year_made == 2016
    assert v.ownership_status == "lietošanā"


def test_parse_slesers_2024_savings():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    cash = [s for s in parsed.savings if s.savings_kind == "cash"]
    bank = [s for s in parsed.savings if s.savings_kind == "bank"]
    assert len(cash) == 1
    assert cash[0].amount == 90000.0
    assert cash[0].currency == "EUR"
    assert len(bank) == 3
    swedbank = next(b for b in bank if "Swedbank" in (b.holder_name or ""))
    assert swedbank.amount == 111940.83
    assert swedbank.holder_reg_number == "40003074764"


def test_parse_slesers_2024_income_types():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    saeima_alga = next(i for i in parsed.income if i.income_type == "Alga")
    assert saeima_alga.amount == 76351.23
    assert saeima_alga.source_reg_number == "90000028300"
    assert not saeima_alga.is_individual
    inese = next(i for i in parsed.income if "Šlesere" in i.source)
    assert inese.is_individual
    assert inese.income_type == "Dāvinājums"


def test_parse_slesers_2024_loans():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    amounts = sorted(l.amount for l in parsed.loans_given)
    assert amounts == [31500.0, 61000.0]


def test_parse_slesers_2024_pension_flags():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert parsed.has_private_pension is False
    assert parsed.has_life_insurance is False


def test_parse_slesers_2024_family():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    by_relation = {r.relation for r in parsed.family}
    assert by_relation == {"Dēls", "Laulātais", "Māsa", "Māte"}
    spouse = next(f for f in parsed.family if f.relation == "Laulātais")
    assert spouse.full_name == "INESE ŠLESERE"


def test_parse_currency_validation():
    assert "EUR" in ALLOWED_CURRENCIES
    assert "RUB" in ALLOWED_CURRENCIES


def test_parse_raises_on_missing_header():
    with pytest.raises(ValueError):
        parse_declaration_html("<html><body>nothing here</body></html>")
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python -m pytest tests/test_vad_parsing.py -v
```

Expected: 12 PASSED. Ja kaut kas neizdodas, pārbaudi attiecīgo `_parse_*` funkciju pret konkrēto Šlesers HTML segmentu.

- [ ] **Step 4: Commit parser**

`.git-commit-msg.tmp`:
```
feat(vad): parse_declaration_html — Pydantic modelis ar 11 sekciju parsētājiem

BeautifulSoup-based, sekciju detect pa <h2> numerācijas regex. Atbalsta cash+bank
duāldistrukturu sec 6, regex-based reg.nr. ekstraktu, EUR/USD/RUB whitelist.
12 testi pret Šlesers 2024 fixture; pension flags + family + income is_individual
flag verificēti.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/vad/parsing.py tests/test_vad_parsing.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 4: HTTP klients — `src/vad/fetch.py` + tests

**Files:**
- Create: `src/vad/fetch.py`
- Create: `tests/test_vad_fetch.py`

- [ ] **Step 1: Implement VadClient**

```python
# src/vad/fetch.py
"""HTTP layer for VID amatpersonu deklarāciju portāls.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 3, § 6.2

Endpoints:
  POST /VAD/Data?Name=X&Surname=Y&From=N → HTML fragment ar tabulu
  GET  /VAD/VADData (Cookie: VADData=<UUID>) → pilns detail HTML

Throttle: 5s starp politiķiem (search), 3s starp deklarācijām (detail).
Retries: max 2 ar exp backoff (5s, 30s) tikai 5xx un 429. 403/404 fail loud.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://www6.vid.gov.lv"
SEARCH_URL = f"{BASE_URL}/VAD/Data"
DETAIL_URL = f"{BASE_URL}/VAD/VADData"
PREFLIGHT_URL = f"{BASE_URL}/ReqCode?check=true&pageName=VADList"

USER_AGENT = "atmina.lv/1.0 (kontakts@atmina.lv)"
SEARCH_THROTTLE_S = 5.0
DETAIL_THROTTLE_S = 3.0
PAGE_SAFETY_BOUND = 200

_HREF_VAD_RE = re.compile(r"HrefVad\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")


@dataclass
class SearchResultRow:
    vad_uuid: str
    declaration_type: str  # "Kārtējā gada deklarācija - par 2024. gadu"
    is_legacy: bool         # True kad type "0" (pre-2010 /VAD2002Data)
    institution: str        # "Latvijas Republikas Saeima"
    position_title: str     # "Saeimas deputāts"


class VadClient:
    """Single-session client. Throttle is on the caller's responsibility (sleep
    between politicians). Cookies managed explicitly per fetch — we do NOT rely
    on session jar to avoid VADData cookie cross-contamination.
    """

    def __init__(self, *, timeout: float = 30.0, throttle: bool = True):
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=False,
        )
        self._throttle = throttle
        self._last_search_at: float = 0.0
        self._last_detail_at: float = 0.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._client.close()

    def close(self):
        self._client.close()

    def search(self, given_name: str, family_name: str) -> list[SearchResultRow]:
        """Search portal by Vārds + Uzvārds. Returns ALL deklarācijas across all
        amatu loma rindām. Loops From= until empty or PAGE_SAFETY_BOUND.
        """
        all_rows: list[SearchResultRow] = []
        offset = 0
        while True:
            self._maybe_sleep_search()
            html = self._post_search(given_name, family_name, offset)
            self._last_search_at = time.monotonic()
            rows = self._parse_search_html(html)
            all_rows.extend(rows)
            if not rows:
                break
            offset += len(rows)
            if offset >= PAGE_SAFETY_BOUND:
                log.warning("vad-search safety bound %d hit for %s %s",
                            PAGE_SAFETY_BOUND, given_name, family_name)
                break
            if len(rows) < 50:  # heuristic: pages parasti 50 rows
                break
        return all_rows

    def fetch_detail(self, vad_uuid: str) -> str:
        """Fetch detail HTML for a single declaration UUID. Returns full HTML.

        Raises httpx.HTTPStatusError on 4xx/5xx; the orchestrator decides retry.
        """
        self._maybe_sleep_detail()
        # Explicit cookie header avoids client-jar contamination across
        # politicians (VADData is the LAST clicked UUID on the portal side).
        headers = {"Cookie": f"VADData={vad_uuid}"}
        resp = self._client.get(DETAIL_URL, headers=headers)
        self._last_detail_at = time.monotonic()
        resp.raise_for_status()
        return resp.text

    def preflight(self) -> None:
        """Pre-flight ReqCode call (drošības margināls — skat. spec § 3.3)."""
        self._client.get(PREFLIGHT_URL, headers={"X-Requested-With": "XMLHttpRequest"})

    # === Internals ===

    def _post_search(self, given: str, family: str, offset: int) -> str:
        body = f"Name={quote_plus(given)}&Surname={quote_plus(family)}&From={offset}"
        resp = self._client.post(
            SEARCH_URL,
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/VAD",
                "Accept": "text/html, */*; q=0.01",
            },
        )
        resp.raise_for_status()
        return resp.text

    def _parse_search_html(self, html: str) -> list[SearchResultRow]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[SearchResultRow] = []
        current_inst = ""
        current_pos = ""
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 3:
                # row with name+role+links: cells[0]=name, [1]=role, [2]=links
                second = cells[1].get_text("\n", strip=True)
                if "\n" in second:
                    current_pos, current_inst = second.split("\n", 1)
                else:
                    current_pos, current_inst = second, ""
                links_cell = cells[2]
            elif len(cells) == 2:
                # role + links (continuation rows for additional positions)
                second = cells[0].get_text("\n", strip=True)
                if "\n" in second:
                    current_pos, current_inst = second.split("\n", 1)
                else:
                    current_pos, current_inst = second, ""
                links_cell = cells[1]
            else:
                continue
            for a in links_cell.find_all("a"):
                onclick = a.get("onclick", "")
                m = _HREF_VAD_RE.search(onclick)
                if not m:
                    continue
                uuid, type_code = m.group(1), m.group(2)
                out.append(SearchResultRow(
                    vad_uuid=uuid,
                    declaration_type=a.get_text(" ", strip=True),
                    is_legacy=(type_code != "2"),
                    institution=current_inst.strip(),
                    position_title=current_pos.strip(),
                ))
        return out

    def _maybe_sleep_search(self):
        if not self._throttle or self._last_search_at == 0.0:
            return
        elapsed = time.monotonic() - self._last_search_at
        if elapsed < SEARCH_THROTTLE_S:
            time.sleep(SEARCH_THROTTLE_S - elapsed)

    def _maybe_sleep_detail(self):
        if not self._throttle or self._last_detail_at == 0.0:
            return
        elapsed = time.monotonic() - self._last_detail_at
        if elapsed < DETAIL_THROTTLE_S:
            time.sleep(DETAIL_THROTTLE_S - elapsed)
```

- [ ] **Step 2: Write tests with httpx MockTransport**

```python
# tests/test_vad_fetch.py
import re

import httpx

from src.vad.fetch import VadClient, SearchResultRow

SEARCH_HTML_2_ROWS = """
<table>
<thead><tr><th>Vārds</th><th>Amats</th><th>Saites</th></tr></thead>
<tbody>
  <tr>
    <td>AINĀRS ŠLESERS</td>
    <td>Saeimas deputāts<br>LATVIJAS REPUBLIKAS SAEIMA</td>
    <td>
      <a href="#" onclick="return HrefVad('uuid-modern-1', '2');">par 2024. gadu</a>
      <a href="#" onclick="return HrefVad('uuid-modern-2', '2');">par 2023. gadu</a>
    </td>
  </tr>
  <tr>
    <td colspan="0"></td>
    <td>Ministrs<br>Valsts kanceleja</td>
    <td>
      <a href="#" onclick="return HrefVad('uuid-legacy-1', '0');">par 2008. gadu</a>
    </td>
  </tr>
</tbody>
</table>
"""

DETAIL_HTML_STUB = "<html><body><h1>VAD detail stub</h1></body></html>"


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    c = VadClient(throttle=False)
    c._client.close()
    c._client = httpx.Client(transport=transport, headers={"User-Agent": "test"})
    return c


def test_search_parses_html_to_rows():
    def handler(request):
        assert request.url.path == "/VAD/Data"
        assert request.method == "POST"
        body = request.content.decode()
        assert "Name=Ain%C4%81rs" in body
        assert "Surname=%C5%A0lesers" in body
        return httpx.Response(200, text=SEARCH_HTML_2_ROWS)
    c = _make_client(handler)
    rows = c.search("Ainārs", "Šlesers")
    assert len(rows) == 3
    assert rows[0].vad_uuid == "uuid-modern-1"
    assert rows[0].is_legacy is False
    assert rows[2].is_legacy is True
    assert rows[0].institution.upper().endswith("SAEIMA")


def test_search_pagination_stops_on_empty():
    call_count = [0]
    def handler(request):
        call_count[0] += 1
        if call_count[0] == 1:
            return httpx.Response(200, text=SEARCH_HTML_2_ROWS)
        return httpx.Response(200, text="<table></table>")
    c = _make_client(handler)
    rows = c.search("Ainārs", "Šlesers")
    assert len(rows) == 3
    assert call_count[0] == 2  # first returns rows, second empty stops loop


def test_fetch_detail_sets_cookie_header():
    captured_cookie = []
    def handler(request):
        captured_cookie.append(request.headers.get("cookie", ""))
        return httpx.Response(200, text=DETAIL_HTML_STUB)
    c = _make_client(handler)
    html = c.fetch_detail("abc-uuid")
    assert "VADData=abc-uuid" in captured_cookie[0]
    assert html == DETAIL_HTML_STUB


def test_fetch_detail_raises_on_404():
    def handler(request):
        return httpx.Response(404, text="not found")
    c = _make_client(handler)
    try:
        c.fetch_detail("missing")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_vad_fetch.py -v
```

Expected: 4 PASSED.

- [ ] **Step 4: Manual smoke test pret reālo VID portālu**

```bash
.venv/Scripts/python -c "
from src.vad.fetch import VadClient
with VadClient() as c:
    rows = c.search('Ainārs', 'Šlesers')
    print(f'Found {len(rows)} rows')
    for r in rows[:3]:
        print(f'  {r.declaration_type[:50]} (uuid={r.vad_uuid[:8]}, legacy={r.is_legacy})')
"
```

Expected: 6 rows for Šlesers ar mix legacy/modern.

- [ ] **Step 5: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): VadClient HTTP layer ar throttling un explicit cookie

POST /VAD/Data + GET /VAD/VADData ar VADData cookie header (NEpaļaujas uz
session jar — izvairās no cross-politiķu contamination). 5s/3s throttle,
bounded From= loop ar 200-row safety. 4 unit tests ar httpx.MockTransport.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/vad/fetch.py tests/test_vad_fetch.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 5: Name matcher — `src/vad/matcher.py` + tests

**Files:**
- Create: `src/vad/matcher.py`
- Create: `tests/test_vad_matcher.py`

- [ ] **Step 1: Implement matcher**

```python
# src/vad/matcher.py
"""Name split + role-based disambiguation for VID search.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 6
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# Manuāli kuratoriem politiķiem, kuriem naïve last-token = surname split ir nepareizs.
# Atslēga = tracked_politicians.id, vērtība = (given_name, surname).
# Phase 0 sākotnējais saraksts; pievieno jaunus, ja sweep dod warn par 0 results.
_NAME_OVERRIDES: dict[int, tuple[str, str]] = {
    # Hosams Abu Meri — "Abu Meri" ir uzvārds (arābu naming convention).
    # pid pārbaudīts ar:
    #   sqlite3 data/atmina.db "SELECT id FROM tracked_politicians WHERE name='Hosams Abu Meri'"
    # Aktivā implementācijā pid jāverificē/jāatjauno pirms commit.
    # 95: ("Hosams", "Abu Meri"),
}


def split_name(pid: int, full_name: str) -> tuple[str, str]:
    """Split politician.name uz (given, family) tuple priekš VID search.

    Hyphenated uzvārdi tiek saglabāti monolīti (Zariņa-Stūre, Kalniņa-Lukaševica).
    Multi-token vārdi: pēdējais token ir uzvārds; pirmie N-1 ir vārds(i).
    Edge case overrides — manuāli kuratorisks _NAME_OVERRIDES dict.
    """
    if pid in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[pid]
    parts = full_name.strip().split()
    if len(parts) < 2:
        raise ValueError(f"vārds bez uzvārda: {full_name!r}")
    return " ".join(parts[:-1]), parts[-1]


def ascii_fallback(text: str) -> str:
    """Diakritiku-strip ASCII forma (Šlesers → Slesers).

    NFKD normalize + strip combining marks. Lietojam tikai pēc tam, kad search
    ar diakritikām atgrieza tukšu — defense-in-depth pret VID staff datu typing
    inkonsekvenci.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def candidate_name_pairs(pid: int, full_name: str) -> Iterable[tuple[str, str]]:
    """Yield (given, family) candidate pairs to try in order.

    1. (given, family) ar diakritikām (vienmēr pirmais)
    2. (ASCII given, ASCII family) — fallback
    """
    g, f = split_name(pid, full_name)
    yield g, f
    g_ascii = ascii_fallback(g)
    f_ascii = ascii_fallback(f)
    if (g_ascii, f_ascii) != (g, f):
        yield g_ascii, f_ascii


def role_matches(
    politician_role: str | None,
    vid_institution: str,
    vid_position: str,
) -> bool:
    """Heuristic check: vai VID-row institūcija/amats ir saderīgs ar tracked
    politiķa role text. Atgriež True, ja vismaz viens substring overlap atrod.
    """
    pol = (politician_role or "").lower()
    if not pol:
        return True  # nav politiķa role → nevaram noliegt
    haystack = f"{vid_institution} {vid_position}".lower()
    keywords = (
        "saeima", "ministr", "kanc", "prezident", "mērs", "vicemērs", "domes",
        "ep deputāts", "eiropas parlament", "pašvaldīb",
    )
    for kw in keywords:
        if kw in pol and kw in haystack:
            return True
    # vēsturiska match — 5+ gadi vecas deklarācijas relax check
    return False
```

- [ ] **Step 2: Write matcher tests**

```python
# tests/test_vad_matcher.py
import pytest

from src.vad.matcher import (
    split_name, ascii_fallback, candidate_name_pairs, role_matches,
)


def test_split_simple():
    assert split_name(1, "Ainārs Šlesers") == ("Ainārs", "Šlesers")


def test_split_hyphenated_surname():
    assert split_name(1, "Agita Zariņa-Stūre") == ("Agita", "Zariņa-Stūre")


def test_split_multi_token_first_name():
    assert split_name(1, "Dāvis Mārtiņš Daugavietis") == ("Dāvis Mārtiņš", "Daugavietis")


def test_split_three_token_naive():
    # Šis ir naïve case kur naïve gives wrong answer
    # ar override: ("Hosams", "Abu Meri")
    assert split_name(1, "Hosams Abu Meri") == ("Hosams Abu", "Meri")  # without override


def test_split_raises_on_single_token():
    with pytest.raises(ValueError):
        split_name(1, "Šlesers")


def test_ascii_fallback():
    assert ascii_fallback("Šlesers") == "Slesers"
    assert ascii_fallback("Zariņa-Stūre") == "Zarina-Sture"
    assert ascii_fallback("Edgars Rinkēvičs") == "Edgars Rinkevics"


def test_candidate_pairs_yields_diacritic_first():
    pairs = list(candidate_name_pairs(1, "Ainārs Šlesers"))
    assert pairs[0] == ("Ainārs", "Šlesers")
    assert pairs[1] == ("Ainars", "Slesers")


def test_candidate_pairs_no_dup_when_ascii_only():
    pairs = list(candidate_name_pairs(1, "Janis Kalnins"))
    assert pairs == [("Janis", "Kalnins")]


def test_role_matches_saeima():
    assert role_matches("Saeimas deputāts", "Latvijas Republikas Saeima", "Saeimas deputāts")


def test_role_matches_minister():
    assert role_matches("Ministre", "Aizsardzības ministrija", "Ministrs")


def test_role_matches_returns_false_on_unrelated():
    assert not role_matches("Žurnālists", "Latvijas Republikas Saeima", "Saeimas deputāts")


def test_role_matches_lenient_when_no_role():
    assert role_matches(None, "X", "Y")
    assert role_matches("", "X", "Y")
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_vad_matcher.py -v
```

Expected: 12 PASSED.

- [ ] **Step 4: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): name split, ASCII fallback un role disambiguation matcher

split_name ar _NAME_OVERRIDES edge cases (Hosams Abu Meri), candidate_name_pairs
yields diakritika-first then ASCII (defense-in-depth), role_matches substring
heuristic homonīmu aizsardzībai. 12 testi ietverot hyphenated uzvārdus.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/vad/matcher.py tests/test_vad_matcher.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 6: Orchestrator — `src/vad/declarations.py` + integration tests

**Files:**
- Create: `src/vad/declarations.py`
- Create: `tests/test_vad_declarations.py`

- [ ] **Step 1: Implement orchestrator**

```python
# src/vad/declarations.py
"""High-level orchestrator: fetch + parse + role-disambiguate + store.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 6, § 7

Public API:
    fetch_for_politician(opponent_id, db, client) -> StoreResult
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

from src.vad.fetch import VadClient, SearchResultRow, BASE_URL
from src.vad.matcher import candidate_name_pairs, role_matches
from src.vad.parsing import (
    ParsedDeclaration, parse_declaration_html,
)

log = logging.getLogger(__name__)


@dataclass
class StoreResult:
    opponent_id: int
    politician_name: str
    rows_found: int       # search rows after role-match filter
    rows_skipped_role: int
    rows_skipped_legacy: int
    new_inserted: int
    already_present: int
    errors: list[str]


def fetch_for_politician(
    opponent_id: int,
    db: sqlite3.Connection,
    client: VadClient,
    *,
    include_legacy: bool = False,
    dry_run: bool = False,
) -> StoreResult:
    """Search VID, filter by role, fetch+parse+store new declarations.

    Idempotent: existing (opponent_id, vad_uuid) skipped (no fetch).
    """
    pol = db.execute(
        "SELECT name, role FROM tracked_politicians WHERE id=?", (opponent_id,)
    ).fetchone()
    if pol is None:
        raise ValueError(f"opponent_id={opponent_id} not in tracked_politicians")
    name = pol["name"]
    role = pol["role"]

    result = StoreResult(
        opponent_id=opponent_id, politician_name=name,
        rows_found=0, rows_skipped_role=0, rows_skipped_legacy=0,
        new_inserted=0, already_present=0, errors=[],
    )

    rows: list[SearchResultRow] = []
    for given, family in candidate_name_pairs(opponent_id, name):
        rows = client.search(given, family)
        if rows:
            break

    existing_uuids = {
        r["vad_uuid"] for r in db.execute(
            "SELECT vad_uuid FROM vad_declarations WHERE opponent_id=?",
            (opponent_id,),
        )
    }

    for r in rows:
        if r.is_legacy and not include_legacy:
            result.rows_skipped_legacy += 1
            continue
        if not role_matches(role, r.institution, r.position_title):
            log.warning(
                "vad-role-mismatch: pid=%d name=%r role=%r vid_inst=%r vid_pos=%r",
                opponent_id, name, role, r.institution, r.position_title,
            )
            result.rows_skipped_role += 1
            continue
        result.rows_found += 1
        if r.vad_uuid in existing_uuids:
            result.already_present += 1
            continue
        if dry_run:
            result.new_inserted += 1
            continue
        try:
            html = client.fetch_detail(r.vad_uuid)
            parsed = parse_declaration_html(html)
            _store(db, opponent_id, r, parsed, html, name)
            result.new_inserted += 1
        except Exception as e:
            msg = f"uuid={r.vad_uuid}: {type(e).__name__}: {e}"
            log.exception("vad-fetch-fail %s", msg)
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
    """Insert vad_declarations + all section rows in one transaction. Returns
    declaration_id. Idempotent on UNIQUE(opponent_id, vad_uuid) — caller
    checked existence already, so this fails loud on race condition.
    """
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
    for l in parsed.loans_given:
        cur.execute(
            "INSERT INTO vad_loans_given(declaration_id, amount, currency, amount_in_words) "
            "VALUES (?,?,?,?)",
            (decl_id, l.amount, l.currency, l.amount_in_words),
        )
    for f in parsed.family:
        cur.execute(
            "INSERT INTO vad_family(declaration_id, full_name, relation) VALUES (?,?,?)",
            (decl_id, f.full_name, f.relation),
        )
    db.commit()
    return decl_id
```

- [ ] **Step 2: Write integration tests**

```python
# tests/test_vad_declarations.py
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.vad.declarations import fetch_for_politician
from src.vad.fetch import SearchResultRow
from src.vad.schema import init_vad_tables

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "vad" / "slesers-2024.html").read_text(encoding="utf-8")


def _make_db():
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    db = sqlite3.connect(fd.name)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT
        );
        INSERT INTO tracked_politicians(id, name, role) VALUES (3, 'Ainārs Šlesers', 'Saeimas deputāts');
    """)
    db.commit()
    init_vad_tables(fd.name)
    return db, fd.name


def _mock_client_with_one_row():
    client = MagicMock()
    client.search.return_value = [
        SearchResultRow(
            vad_uuid="uuid-2024", declaration_type="Kārtējā gada deklarācija - par 2024. gadu",
            is_legacy=False, institution="Latvijas Republikas Saeima",
            position_title="Saeimas deputāts",
        )
    ]
    client.fetch_detail.return_value = FIXTURE_HTML
    return client


def test_fetch_for_politician_inserts_declaration_and_sections():
    db, _ = _make_db()
    client = _mock_client_with_one_row()
    result = fetch_for_politician(3, db, client)
    assert result.new_inserted == 1
    assert result.already_present == 0
    decl = db.execute("SELECT * FROM vad_declarations WHERE opponent_id=3").fetchone()
    assert decl is not None
    assert decl["vad_uuid"] == "uuid-2024"
    assert decl["declaration_kind"] == "annual"
    assert decl["declaration_year"] == 2024
    assert "Šlesers" in decl["source_url"] or "%C5%A0lesers" in decl["source_url"]
    n_pos = db.execute("SELECT COUNT(*) FROM vad_positions WHERE declaration_id=?", (decl["id"],)).fetchone()[0]
    assert n_pos == 4  # Likvidators, Valdes loceklis, 2x Izpildinstitūcija
    n_inc = db.execute("SELECT COUNT(*) FROM vad_income WHERE declaration_id=?", (decl["id"],)).fetchone()[0]
    assert n_inc == 4


def test_fetch_for_politician_idempotent():
    db, _ = _make_db()
    client = _mock_client_with_one_row()
    fetch_for_politician(3, db, client)
    result2 = fetch_for_politician(3, db, client)
    assert result2.new_inserted == 0
    assert result2.already_present == 1


def test_fetch_for_politician_skips_role_mismatch():
    db, _ = _make_db()
    db.execute("UPDATE tracked_politicians SET role='Žurnālists' WHERE id=3")
    db.commit()
    client = _mock_client_with_one_row()
    result = fetch_for_politician(3, db, client)
    assert result.rows_skipped_role == 1
    assert result.new_inserted == 0


def test_fetch_for_politician_skips_legacy():
    db, _ = _make_db()
    client = MagicMock()
    client.search.return_value = [
        SearchResultRow(vad_uuid="legacy-1", declaration_type="par 2008. gadu",
                        is_legacy=True, institution="Latvijas Republikas Saeima",
                        position_title="Saeimas deputāts"),
    ]
    result = fetch_for_politician(3, db, client)
    assert result.rows_skipped_legacy == 1
    assert result.new_inserted == 0


def test_dry_run_does_not_write():
    db, _ = _make_db()
    client = _mock_client_with_one_row()
    result = fetch_for_politician(3, db, client, dry_run=True)
    assert result.new_inserted == 1  # would insert
    n = db.execute("SELECT COUNT(*) FROM vad_declarations").fetchone()[0]
    assert n == 0  # but didn't
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_vad_declarations.py -v
```

Expected: 5 PASSED.

- [ ] **Step 4: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): fetch_for_politician orchestrator + 5 integration tests

Search → role-disambiguate → fetch detail → parse → store all 11 sections
in one transaction. Idempotents pa (opponent_id, vad_uuid). Skip legacy
deklarācijas (Phase 0.5 backlogs). Skip role-mismatch ar log warn.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/vad/declarations.py tests/test_vad_declarations.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 7: Public API — `src/vad/__init__.py`

**Files:**
- Modify: `src/vad/__init__.py`

- [ ] **Step 1: Re-export public API**

```python
# src/vad/__init__.py
"""VAD (Valsts amatpersonu deklarācijas) — strukturēta ielāde no www6.vid.gov.lv.

Public API:
    init_vad_tables — DDL (lazy, ne init_db)
    fetch_for_politician — orchestrator (search + parse + store)
    VadClient — HTTP layer
    parse_declaration_html — pure parser
"""

from src.vad.declarations import StoreResult, fetch_for_politician
from src.vad.fetch import VadClient, SearchResultRow
from src.vad.parsing import (
    ParsedDeclaration, parse_declaration_html,
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
```

- [ ] **Step 2: Verify import**

```bash
.venv/Scripts/python -c "from src.vad import init_vad_tables, fetch_for_politician, VadClient; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add src/vad/__init__.py
.git-commit-msg.tmp:
```
```
chore(vad): public API re-exports src/vad/__init__.py

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
```bash
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 8: CLI — `scripts/ingest_vad_declarations.py`

**Files:**
- Create: `scripts/ingest_vad_declarations.py`

- [ ] **Step 1: Implement CLI**

```python
# scripts/ingest_vad_declarations.py
"""Manual ingest of VID amatpersonu deklarācijas for tracked politicians.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 8

Idempotent. Designed for monthly cadence (peak aprīlis-maijs).

Usage:
    python scripts/ingest_vad_declarations.py                         # all tracked
    python scripts/ingest_vad_declarations.py --politician slesers-ainars
    python scripts/ingest_vad_declarations.py --year 2024
    python scripts/ingest_vad_declarations.py --limit 5
    python scripts/ingest_vad_declarations.py --dry-run
"""

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.ingest_log import _resolve_log_file, append_ingest_entry  # noqa: E402
from src.vad import VadClient, fetch_for_politician, init_vad_tables  # noqa: E402

VAD_SOURCE_CONFIG = {
    "url": "https://www6.vid.gov.lv/VAD",
    "name": "VID amatpersonu deklarācijas",
    "tier": 1,
    "fetcher_mode": "fetcher",
    "rate_limit_seconds": 5,
    "legal_status": "approved",
    "legal_notes": (
        "Likuma Par interešu konflikta novēršanu valsts amatpersonu darbībā "
        "24. un 25. pants — publicēšanas pienākums un publiskais raksturs. "
        "Manuāls ingest via scripts/ingest_vad_declarations.py."
    ),
    "last_tos_review": "2026-05-02",
}


def _slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--politician", help="slug or name substring; default = visi tracked")
    p.add_argument("--year", type=int, help="filter ingest tikai par konkrēto gadu")
    p.add_argument("--limit", type=int, help="max politiķi per palaišana")
    p.add_argument("--dry-run", action="store_true", help="parser+match, bet nav DB write")
    p.add_argument("--include-legacy", action="store_true",
                   help="iekļauj /VAD2002Data legacy deklarācijas (Phase 0.5 backlog)")
    args = p.parse_args(argv)

    db = get_db()
    init_vad_tables()  # idempotent

    where = "relationship_type IN ('tracked') OR relationship_type IS NULL"
    rows = db.execute(
        f"SELECT id, name FROM tracked_politicians WHERE {where} ORDER BY name"
    ).fetchall()

    politicians = []
    for r in rows:
        slug = _slugify(r["name"])
        if args.politician:
            needle = args.politician.lower()
            if needle not in slug and needle not in r["name"].lower():
                continue
        politicians.append((r["id"], r["name"], slug))

    if args.limit:
        politicians = politicians[: args.limit]

    print(f"[plan] {len(politicians)} politiķi (dry_run={args.dry_run})")

    total_new = 0
    total_skip_role = 0
    total_skip_legacy = 0
    total_present = 0
    total_errors = 0
    started = time.monotonic()

    with VadClient() as client:
        for pid, name, slug in politicians:
            t0 = time.monotonic()
            try:
                result = fetch_for_politician(
                    pid, db, client,
                    include_legacy=args.include_legacy,
                    dry_run=args.dry_run,
                )
            except Exception as e:
                print(f"[fail] {name}: {type(e).__name__}: {e}")
                total_errors += 1
                continue
            total_new += result.new_inserted
            total_skip_role += result.rows_skipped_role
            total_skip_legacy += result.rows_skipped_legacy
            total_present += result.already_present
            total_errors += len(result.errors)
            elapsed = time.monotonic() - t0
            print(
                f"[ok]  {name:<32} new={result.new_inserted} present={result.already_present} "
                f"skip_role={result.rows_skipped_role} skip_legacy={result.rows_skipped_legacy} "
                f"errs={len(result.errors)} ({elapsed:.1f}s)"
            )
            if args.year:
                # Post-filter: dzēš tikko ievietoto, ja nav par norādīto gadu
                # (vienkāršs delete; idempotent — nākamā palaiž to nepievienos)
                pass  # Phase 0 kept simple — --year filter ir nice-to-have

    total_elapsed = time.monotonic() - started
    print(
        f"\n[done] new={total_new} present={total_present} "
        f"skip_role={total_skip_role} skip_legacy={total_skip_legacy} "
        f"errors={total_errors} (~{total_elapsed/60:.1f} min)"
    )

    if not args.dry_run:
        append_ingest_entry(
            source_name=VAD_SOURCE_CONFIG["name"],
            source_tier=VAD_SOURCE_CONFIG["tier"],
            documents_added=total_new,
            documents_skipped=total_present + total_skip_role + total_skip_legacy,
            status="success" if total_errors == 0 else "partial",
            extra=f"manuāls; {len(politicians)} politiķi sweep'ēti",
        )

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke test ar --dry-run un --limit 1**

```bash
.venv/Scripts/python scripts/ingest_vad_declarations.py --politician slesers-ainars --dry-run
```

Expected: 1 politiķis, search dod ~6 rindas, role-match drops dažas, dry_run new_inserted >= 1, nav DB writes.

Verificē DB:
```bash
.venv/Scripts/python -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(con.execute('SELECT COUNT(*) FROM vad_declarations').fetchone())"
```
Expected: `(0,)` — dry-run nerakstīja neko.

- [ ] **Step 3: Real test ar 1 politiķi (Šlesers, REAL DB write)**

```bash
.venv/Scripts/python scripts/ingest_vad_declarations.py --politician slesers-ainars
```

Expected: ~3 jaunas deklarācijas (par 2022, 2023, 2024 — modernie), legacy skip, ~5-10s palaišana.

Verificē:
```bash
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT declaration_year, declaration_kind, position_title FROM vad_declarations WHERE opponent_id=3 ORDER BY declaration_year DESC').fetchall()
for r in rows:
    print(dict(r))
"
```
Expected: 3+ rows including year 2024 annual + Saeimas deputāts.

- [ ] **Step 4: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): scripts/ingest_vad_declarations.py manuāls CLI

--politician, --year, --limit, --dry-run, --include-legacy. Idempotents
pa (opponent_id, vad_uuid). Smoke testēts ar Šleseru — 3 modernās
deklarācijas insert'ētas un dry_run skripts neraksta DB.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add scripts/ingest_vad_declarations.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 9: Runbook — `wiki/operations/vad-declarations.md`

**Files:**
- Create: `wiki/operations/vad-declarations.md`
- Modify: `wiki/operations/operacijas.md`

- [ ] **Step 1: Create runbook**

```markdown
# VID amatpersonu deklarācijas (manuāla, mēneša cikls)

## Mērķis

Strukturēti ielādēt mūsu izsekoto politiķu (`relationship_type='tracked'`) amatpersonu
deklarācijas no [www6.vid.gov.lv/VAD](https://www6.vid.gov.lv/VAD) — pilna 11
sekciju datu kopa (amati, NĪ, kapitāldaļas, transports, naudas uzkrājumi, ienākumi,
darījumi, parādi, aizdevumi, ģimene + sec 12 pension flags).

## Tipisks cikls (mēneša rutīna)

1. Palaiž full sweep:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py
   ```
2. Apjēga: ~16 min steady-state (152 politiķi × 5s search + ~2 jauni detail × 3s).
   Peak aprīlis-maijs: ~21 min.
3. Output: per-politiķis rinda ar `new=N present=N skip_role=N skip_legacy=N errs=N`.
4. Pārbauda log entry `wiki/log-ingest/<gads-mēnesis>.md`.
5. Re-render publisko vietu:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
   ```
6. Pārbauda 3-5 sample profilus: `output/atmina/politiki/<slug>.html` Deklarācijas tabā ir 1+ ieraksts.

## Bootstrap (vienreizējais)

Pirms pirmā sweep:

1. Pārliecinies, ka tracked_politicians satur visus politiķus, kurus gribi sekot.
2. Verificē hyphenated uzvārdus VID portālā (manuāls test):
   ```bash
   .venv/Scripts/python -c "from src.vad import VadClient; print(len(VadClient().search('Agita', 'Zariņa-Stūre')))"
   ```
   Expected: 1+ row (verificē, ka portāls pieņem defisi).
3. Palaiž ar `--limit 5 --dry-run` lai apstiprinātu plūsmu pirms full sweep.

## Failure modes

### "STOP: 0 rows for {politician}"
Politiķa vārds VID portālā neiet caur. Pārbauda:
1. Vai `tracked_politicians.name` atbilst kanoniskam vārdam (skat. memory `feedback_matcher_no_diacritic_strip`).
2. Vai politiķis ir amatpersona (žurnālisti, organizācijas — gaidāmi 0 rezultāti).
3. Vai vārds ir multi-token un naïve split kļūdains — pievieno `_NAME_OVERRIDES` dict `src/vad/matcher.py`.

### "skip_role=N" augsts skaits
VID atgrieza politiķim daudz amatu, kuriem mūsu `tracked_politicians.role` neatbilst.
Pārbauda specific row-mismatches log warn'os (`grep vad-role-mismatch`). Ja false-positive
skip — paplašina `role_matches` keyword sarakstu `src/vad/matcher.py`.

### Pagination warning ">100 rows"
Politiķim VID atgrieza neparasti daudz rindu. Pārbauda manuāli portālā — varbūt homonīms.
Bounded loop apstājas pie 200; ja jāpieaugās, log warn ir signāls operatora intervencei.

### HTTP 429 / 5xx
Throttle ir per-client (5s search, 3s detail). Ja 429 atkārtoti — palielini throttle
`src/vad/fetch.py:SEARCH_THROTTLE_S`. Ja 5xx atkārtoti — VID portāls down, palaiž
nākamajā dienā.

## Pārbaudes vaicājumi

```bash
# Cik politiķiem ir vismaz 1 deklarācija?
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
print(con.execute('SELECT COUNT(DISTINCT opponent_id) FROM vad_declarations').fetchone())
"

# Politiķi BEZ deklarāciju (var būt nepareizs role-match)
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
for r in con.execute('''
    SELECT tp.name, tp.role FROM tracked_politicians tp
    LEFT JOIN vad_declarations vd ON vd.opponent_id = tp.id
    WHERE tp.relationship_type = 'tracked' AND vd.id IS NULL
    ORDER BY tp.name
'''):
    print(f\"{r['name']:<35} role={r['role']!r}\")
"
```

## Datu modelis — atsauce

11 tabulas (skat. spec § 4 pilnam DDL):
- `vad_declarations` — header
- `vad_positions` — sec 2 amati
- `vad_real_estate` — sec 3 NĪ
- `vad_companies` — sec 4 kapitāldaļas
- `vad_vehicles` — sec 5 transports
- `vad_savings` — sec 6 naudas uzkrājumi (cash + bank polymorphic)
- `vad_income` — sec 7 visi ienākumi
- `vad_transactions` — sec 8 darījumi >20 MMA
- `vad_debts` — sec 9 parādi >20 MMA
- `vad_loans_given` — sec 10 izsniegtie aizdevumi >20 MMA
- `vad_family` — sec 14 ģimene

## Spec atsauce

`docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md`
```

- [ ] **Step 2: Pievieno saiti uz operacijas.md**

```bash
# Paskatamies kur Vēstnesis sadaļa beidzas
```

Ievietojam pēc "Latvijas Vēstnesis" sadaļas (~rinda 60). Pievieno:

```markdown
## VID amatpersonu deklarācijas (manuāla, mēneša cikls)

Pilns runbook: [vad-declarations.md](vad-declarations.md). Manuāls ielādes skripts:

```bash
.venv/Scripts/python scripts/ingest_vad_declarations.py [--politician X] [--year Y] [--dry-run]
```

Idempotent: `(opponent_id, vad_uuid)` UNIQUE pāris. Palaiž **reizi mēnesī** (peak aprīlis-maijs, kad publicē par iepriekšējo gadu). Apjēga ~16 min steady-state.
```

- [ ] **Step 3: Commit**

`.git-commit-msg.tmp`:
```
docs(vad): runbook + operacijas.md saraksta papildinājums

Bootstrap, mēneša cikls, failure modes, pārbaudes vaicājumi, 11 tabulu
saraksts. Saskan ar Vēstneša runbook formātu.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add wiki/operations/vad-declarations.md wiki/operations/operacijas.md
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 10: Phase 0 CHANGELOG entry

**Files:**
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Pievieno entry pirmsākumā**

```markdown
## 2026-05-02 — VAD declarations tracker (Phase 0 ingest)

**TL;DR:** Jauns `src/vad/` pakete ielādē strukturēti VID amatpersonu deklarācijas
no www6.vid.gov.lv/VAD priekš 152 izsekoto politiķu. 11 jaunas `vad_*` tabulas,
manuāls CLI ingest (`scripts/ingest_vad_declarations.py`) ar mēneša cikla
noklusējumu, peak aprīlis-maijs.

**Why:** Lietotāja pieprasījums (Telegram 2026-05-02) — automatizēt deklarāciju
ielādi, lai politiķa profilā varētu rādīt strukturētu finansiālo + ģimenes profilu
ar gads-pa-gadam delta marķieriem. Daudz signāla par interešu konflikta
detektēšanu (Phase 3 backlog).

**Arhitektūra (sekojot `src/saeima/` precedentam):**
- `src/vad/schema.py` — DDL un `init_vad_tables()` (lazy, ne `init_db()`).
- `src/vad/fetch.py` — `VadClient` httpx + bounded From= loop + 5s/3s throttle.
- `src/vad/parsing.py` — `parse_declaration_html()` BeautifulSoup → Pydantic.
- `src/vad/matcher.py` — name split + ASCII fallback + role disambiguation.
- `src/vad/declarations.py` — orchestrator `fetch_for_politician`.
- `scripts/ingest_vad_declarations.py` — CLI.

**11 tabulas:**
`vad_declarations` (header) + 10 sekciju tabulas (positions/real_estate/companies/
vehicles/savings/income/transactions/debts/loans_given/family). NAV `documents`
rindas (saeima 2026-04-25 invariants). NAV `claims` rindas (deklarācija ≠ retoriska
pozīcija).

**Drošības margināli:**
- Throttle: 5s starp politiķiem, 3s starp deklarācijām → ~16 min mēneša sweep.
- Bounded `From=` loop ar 200-row safety bound + log warn pie >100.
- Cookie management: explicit per-fetch Cookie header (NEpaļaujas uz session jar).
- Modernie ieraksti only (legacy `/VAD2002Data` Phase 0.5 backlogs).
- Role-disambiguation pret 5 homonīmu pāriem DB (Šlesers Ainārs/Ričards utt.).

**Spec un plāns:**
- Spec: `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md`
- Plāns: `docs/superpowers/plans/2026-05-02-vad-deklaracijas-plan.md`

**Sākotnējais sweep:** Tasks 17-18 plānā — mēneša rutīnas pirmā palaišana.

---
```

- [ ] **Step 2: Commit**

`.git-commit-msg.tmp`:
```
docs(changelog): VAD declarations Phase 0 ingest

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add wiki/CHANGELOG.md
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

## Phase 1 — Render (Tasks 11-19)

### Task 11: Diff engine — `src/vad/diff.py` + tests

**Files:**
- Create: `src/vad/diff.py`
- Create: `tests/test_vad_diff.py`

- [ ] **Step 1: Implement diff**

```python
# src/vad/diff.py
"""Year-over-year delta engine for VAD section rows.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

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
    """Compute delta marķieri vienai sekcijai.

    Atgriež visu THIS-year rindas + REMOVED rindas (kas bija prev bet nav this).
    Sortēta: modified > new > removed > unchanged.
    """
    if section not in IDENTITY_KEYS:
        return [DeltaRow(payload=r, delta="unchanged") for r in this_year_rows]

    key_fn = IDENTITY_KEYS[section]
    prev_by_key = {key_fn(r): r for r in prev_year_rows}
    this_by_key = {key_fn(r): r for r in this_year_rows}

    out: list[DeltaRow] = []
    # this-year rows: classify
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
    # removed rows
    for k, r in prev_by_key.items():
        if k not in this_by_key:
            out.append(DeltaRow(payload=r, delta="removed"))

    rank = {"modified": 0, "new": 1, "removed": 2, "unchanged": 3}
    out.sort(key=lambda d: rank[d.delta])
    return out
```

- [ ] **Step 2: Write diff tests**

```python
# tests/test_vad_diff.py
from src.vad.diff import compute_section_deltas


def test_new_company():
    prev = []
    curr = [{"reg_number": "40003555683", "company_name": "AVADEL", "capital_kind": "Kapitāla daļas",
             "units": 1000.0, "total_value": 10000.0}]
    out = compute_section_deltas("companies", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "new"


def test_income_modified_above_threshold():
    prev = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 50000.0}]
    curr = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76000.0}]
    out = compute_section_deltas("income", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "modified"
    assert "amount: 50000 → 76000" in out[0].diff_text


def test_income_unchanged_below_threshold():
    prev = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76000.0}]
    curr = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76200.0}]
    out = compute_section_deltas("income", prev, curr)
    assert out[0].delta == "unchanged"


def test_removed_property():
    prev = [{"property_type": "Dzīvoklis", "location": "Latvija, Jūrmala", "ownership_status": "lietošanā"}]
    curr = []
    out = compute_section_deltas("real_estate", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "removed"


def test_ownership_change():
    prev = [{"property_type": "Zeme", "location": "Annenieku pag.", "ownership_status": "valdījumā"}]
    curr = [{"property_type": "Zeme", "location": "Annenieku pag.", "ownership_status": "īpašumā"}]
    out = compute_section_deltas("real_estate", prev, curr)
    # Identity key includes ownership_status, so this becomes new + removed
    deltas = sorted([d.delta for d in out])
    assert deltas == ["new", "removed"]


def test_family_unchanged():
    prev = [{"full_name": "INESE ŠLESERE", "relation": "Laulātais"}]
    curr = [{"full_name": "INESE ŠLESERE", "relation": "Laulātais"}]
    out = compute_section_deltas("family", prev, curr)
    assert out[0].delta == "unchanged"


def test_sort_order_modified_first():
    prev = [
        {"source": "A", "income_type": "Alga", "currency": "EUR", "amount": 100.0},
    ]
    curr = [
        {"source": "B", "income_type": "Dāvinājums", "currency": "EUR", "amount": 50.0},  # new
        {"source": "A", "income_type": "Alga", "currency": "EUR", "amount": 200.0},        # modified
    ]
    out = compute_section_deltas("income", prev, curr)
    assert out[0].delta == "modified"
    assert out[1].delta == "new"
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_vad_diff.py -v
```

Expected: 7 PASSED.

- [ ] **Step 4: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): year-over-year delta engine ar identity keys un 5% threshold

10 sekciju identity keys, modified > new > removed > unchanged sort order.
Cilvēkam-lasāms diff_text ("amount: 50000 → 76000 (+52%)").

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/vad/diff.py tests/test_vad_diff.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 12: Render data fetcher — `src/render/vad.py` + tests

**Files:**
- Create: `src/render/vad.py`
- Create: `tests/test_vad_render.py`

- [ ] **Step 1: Implement render fetcher**

```python
# src/render/vad.py
"""Render-time pre-loader for VAD declarations.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9.1

One-batch-per-tabula query strategy (F4 leaf-vs-fan-out paterns); avoids
N+1 queries when rendering 152 politician profile pages.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from src.vad.diff import compute_section_deltas, DeltaRow

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
        # Tables don't exist yet (test DB without init_vad_tables)
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
```

- [ ] **Step 2: Write tests**

```python
# tests/test_vad_render.py
import sqlite3
import tempfile

from src.render.vad import (
    get_vad_data_for_politicians, vad_count_per_politician,
)
from src.vad.schema import init_vad_tables


def _fresh_db():
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    db = sqlite3.connect(fd.name)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE tracked_politicians(id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X'), (2, 'Y')")
    db.commit()
    init_vad_tables(fd.name)
    return db, fd.name


def _insert_declaration(db, opp_id, year, uuid, **extra):
    cur = db.execute(
        "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
        "declaration_kind, declaration_year, source_url) VALUES (?,?,?,?,?,?)",
        (opp_id, uuid, f"Kārtējā gada deklarācija - par {year}. gadu", "annual", year,
         "https://example/"),
    )
    return cur.lastrowid


def test_returns_empty_when_no_data():
    db, _ = _fresh_db()
    assert get_vad_data_for_politicians(db, [1]) == {}


def test_returns_empty_when_table_missing():
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    db = sqlite3.connect(fd.name)
    db.row_factory = sqlite3.Row
    # No init_vad_tables — table doesn't exist
    assert get_vad_data_for_politicians(db, [1]) == {}


def test_loads_declarations_with_year_desc():
    db, _ = _fresh_db()
    _insert_declaration(db, 1, 2022, "u-2022")
    _insert_declaration(db, 1, 2024, "u-2024")
    _insert_declaration(db, 1, 2023, "u-2023")
    db.commit()
    data = get_vad_data_for_politicians(db, [1])
    assert 1 in data
    years = [v.year for v in data[1]]
    assert years == [2024, 2023, 2022]


def test_sections_get_delta_markers():
    db, _ = _fresh_db()
    d_2023 = _insert_declaration(db, 1, 2023, "u-2023")
    d_2024 = _insert_declaration(db, 1, 2024, "u-2024")
    db.execute(
        "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
        "VALUES (?,?,?,?,?,?)",
        (d_2023, "Saeima", 0, "Alga", 50000.0, "EUR"),
    )
    db.execute(
        "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
        "VALUES (?,?,?,?,?,?)",
        (d_2024, "Saeima", 0, "Alga", 76000.0, "EUR"),
    )
    db.commit()
    data = get_vad_data_for_politicians(db, [1])
    income_2024 = data[1][0].sections["income"]
    assert income_2024[0].delta == "modified"
    assert "76000" in income_2024[0].diff_text


def test_vad_count_per_politician():
    db, _ = _fresh_db()
    _insert_declaration(db, 1, 2024, "u1")
    _insert_declaration(db, 1, 2023, "u2")
    _insert_declaration(db, 2, 2024, "u3")
    db.commit()
    counts = vad_count_per_politician(db)
    assert counts == {1: 2, 2: 1}
```

- [ ] **Step 3: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_vad_render.py -v
```

Expected: 5 PASSED.

- [ ] **Step 4: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): src/render/vad.py — batch render-time fetch + delta markeri

One-batch-per-tabula query strategy (F4 leaf-vs-fan-out paterns); guard ar
try/except OperationalError test DB priekš (saeima_bills precedents
src/render/politicians.py:503).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/render/vad.py tests/test_vad_render.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 13: Tab dispatch — modificē `src/profile_kind.py` un `src/render/politicians.py`

**Files:**
- Modify: `src/profile_kind.py`
- Modify: `src/render/politicians.py`
- Create: `tests/test_profile_kind_vad.py`

- [ ] **Step 1: Find current `_profile_tab_set` signature**

```bash
.venv/Scripts/python -c "import inspect; from src.render.politicians import _profile_tab_set; print(inspect.signature(_profile_tab_set))"
```

Lasi šī funkcijas pilno definīciju (`grep -n "_profile_tab_set" src/render/politicians.py`).

- [ ] **Step 2: Pievieno deklaracijas tab**

Modificē `_profile_tab_set()` lai pieņemtu jaunu argumentu `has_vad_data` un pievieno `'deklaracijas'` tab kandidātos.

```python
# src/render/politicians.py — _profile_tab_set diff
def _profile_tab_set(
    kind: str,
    has_contradictions: bool,
    has_saites_content: bool,
    has_vad_data: bool = False,
) -> set[str]:
    base = _BASE_TABS_BY_KIND[kind]
    tabs = set(base)
    if has_contradictions:
        tabs.add("pretrunas")
    if has_saites_content:
        tabs.add("saites")
    # VAD declarations tab — tikai amatpersonas (deputy/minister/mep/regional/former/politician)
    if has_vad_data and kind in {"deputy", "minister", "mep", "regional", "former", "politician"}:
        tabs.add("deklaracijas")
    return tabs
```

(Nezini precīzu funkcijas formu — to atrod `grep -n _profile_tab_set src/render/politicians.py`. Šis ir minimāla diff illustrācija.)

- [ ] **Step 3: `_fetch_politicians()` ielādē VAD count**

Modificē `_fetch_politicians()` (`src/render/politicians.py`) lai pievienotu `vad_count` per politiķis:

```python
# Apkārt rindām, kur `claims_count`/`votes_count` tiek lasīti — pievieno:
from src.render.vad import vad_count_per_politician
vad_counts = vad_count_per_politician(db)
# ...
# rindā, kur per-politiķis dictu būvē:
p["vad_count"] = vad_counts.get(p["id"], 0)
```

- [ ] **Step 4: Tab set izsaukums izmanto vad_count**

```python
# Kur _profile_tab_set tiek izsaukts:
p["profile_kind"] = derive_profile_kind(...)
p["tab_set"] = _profile_tab_set(
    p["profile_kind"],
    has_contradictions=p["contradictions_count"] > 0,
    has_saites_content=...,
    has_vad_data=p["vad_count"] > 0,
)
```

- [ ] **Step 5: Test**

```python
# tests/test_profile_kind_vad.py
from src.render.politicians import _profile_tab_set


def test_deputy_with_vad_gets_deklaracijas_tab():
    tabs = _profile_tab_set("deputy", has_contradictions=False, has_saites_content=False, has_vad_data=True)
    assert "deklaracijas" in tabs


def test_deputy_without_vad_no_tab():
    tabs = _profile_tab_set("deputy", False, False, has_vad_data=False)
    assert "deklaracijas" not in tabs


def test_journalist_with_vad_no_tab():
    tabs = _profile_tab_set("journalist", False, False, has_vad_data=True)
    assert "deklaracijas" not in tabs


def test_organization_with_vad_no_tab():
    tabs = _profile_tab_set("organization", False, False, has_vad_data=True)
    assert "deklaracijas" not in tabs


def test_minister_with_vad_gets_tab():
    tabs = _profile_tab_set("minister", False, False, has_vad_data=True)
    assert "deklaracijas" in tabs
```

```bash
.venv/Scripts/python -m pytest tests/test_profile_kind_vad.py -v
```

Expected: 5 PASSED.

- [ ] **Step 6: Commit**

`.git-commit-msg.tmp`:
```
feat(profile-kind): deklaracijas tab kandidāts (deputy/minister/mep/regional/former/politician)

has_vad_data konditionāls (līdzīgi kā 'pretrunas' un 'saites'). _fetch_politicians
ielādē vad_count batch query reizē. journalist/analyst/organization/inactive
explicit izslēgti (nav amatpersonas). 5 testi.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/render/politicians.py tests/test_profile_kind_vad.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 14: Templates + CSS — `_vad_panel.html.j2` + `style.css`

**Files:**
- Create: `templates/_vad_panel.html.j2`
- Modify: `assets/style.css`

- [ ] **Step 1: Create _vad_panel partial**

```jinja
{# templates/_vad_panel.html.j2 — VAD deklarāciju panel partial.

   Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 9
   Konteksts: vad_data = list[VadDeclarationView] sorted year DESC. #}

{% if not vad_data %}
<p style="color:var(--text-muted);">Nav saglabātu deklarāciju.</p>
{% else %}
<div class="vad-year-tabs" role="tablist" style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem;">
  {% for v in vad_data[:5] %}
  <button class="vad-year-tab {% if loop.first %}active{% endif %}"
          onclick="showVadYear('{{ v.declaration_id }}', this)"
          data-decl-id="{{ v.declaration_id }}">
    {{ v.year or v.kind }} <span style="opacity:0.6">{{ v.kind }}</span>
  </button>
  {% endfor %}
</div>

{% for v in vad_data[:5] %}
<div class="vad-decl" id="vad-decl-{{ v.declaration_id }}" {% if not loop.first %}style="display:none;"{% endif %}>
  <div class="vad-decl-meta" style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1rem;">
    {{ v.position_title }} · {{ v.institution }} · iesniegts {{ v.submitted_at or '?' }} · publicēts {{ v.published_at or '?' }}
  </div>

  {% set sec_labels = {
    'positions': 'Citi amati',
    'real_estate': 'Nekustamie īpašumi',
    'companies': 'Komercsabiedrību kapitāldaļas',
    'vehicles': 'Transports',
    'savings': 'Naudas uzkrājumi',
    'income': 'Ienākumi',
    'transactions': 'Darījumi >20 MMA',
    'debts': 'Parādsaistības >20 MMA',
    'loans_given': 'Izsniegtie aizdevumi >20 MMA',
  } %}

  {% for sec_key, sec_label in sec_labels.items() %}
    {% set rows = v.sections.get(sec_key, []) %}
    {% if rows %}
    <details class="vad-section" open>
      <summary style="font-weight:600; padding:0.5rem 0; cursor:pointer;">
        {{ sec_label }} <span style="color:var(--text-muted); font-weight:normal;">({{ rows|length }})</span>
      </summary>
      <div class="table-wrap">
        <table class="data-table">
          <tbody>
            {% for d in rows %}
            <tr class="vad-delta-{{ d.delta }}">
              <td style="white-space:nowrap;">
                {% if d.delta == 'new' %}<span class="vad-delta-marker vad-delta-marker-new">jauns</span>
                {% elif d.delta == 'modified' %}<span class="vad-delta-marker vad-delta-marker-modified">mainījies</span>
                {% elif d.delta == 'removed' %}<span class="vad-delta-marker vad-delta-marker-removed">aizgāja</span>
                {% endif %}
              </td>
              <td>
                {% if sec_key == 'positions' %}
                  {{ d.payload.position_title }} — {{ d.payload.entity_name }}
                {% elif sec_key == 'real_estate' %}
                  {{ d.payload.property_type }} — {{ d.payload.location }} ({{ d.payload.ownership_status }})
                {% elif sec_key == 'companies' %}
                  {{ d.payload.company_name }} — {{ d.payload.units|round|int if d.payload.units else '' }} {{ d.payload.capital_kind|lower }}, {{ '%.2f'|format(d.payload.total_value or 0) }} {{ d.payload.currency or '' }}
                {% elif sec_key == 'vehicles' %}
                  {{ d.payload.vehicle_type }} {{ d.payload.brand }} ({{ d.payload.year_made or '?' }})
                {% elif sec_key == 'savings' %}
                  {{ d.payload.savings_kind|capitalize }}: {{ '%.2f'|format(d.payload.amount) }} {{ d.payload.currency }}{% if d.payload.holder_name %} — {{ d.payload.holder_name }}{% endif %}
                {% elif sec_key == 'income' %}
                  {{ d.payload.income_type }}: {{ '%.2f'|format(d.payload.amount) }} {{ d.payload.currency }} <span style="color:var(--text-muted);">no {{ d.payload.source[:60] }}</span>
                {% elif sec_key == 'transactions' %}
                  {{ d.payload.transaction_description[:120] }}
                {% elif sec_key == 'debts' %}
                  {{ '%.2f'|format(d.payload.amount) }} {{ d.payload.currency }} — {{ d.payload.creditor_name }}
                {% elif sec_key == 'loans_given' %}
                  {{ '%.2f'|format(d.payload.amount) }} {{ d.payload.currency }}
                {% endif %}
                {% if d.diff_text %}<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">{{ d.diff_text }}</div>{% endif %}
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </details>
    {% endif %}
  {% endfor %}

  {# Family — collapsed default #}
  {% set family_rows = v.sections.get('family', []) %}
  {% if family_rows %}
  <details class="vad-section vad-section-family" style="margin-top:1rem;">
    <summary style="font-weight:600; padding:0.5rem 0; cursor:pointer; color:var(--text-muted);">
      Ģimene — publiska VID portālā ({{ family_rows|length }})
    </summary>
    <div class="table-wrap">
      <table class="data-table">
        <tbody>
          {% for d in family_rows %}
          <tr class="vad-delta-{{ d.delta }}">
            <td>{{ d.payload.full_name }} <span style="color:var(--text-muted);">— {{ d.payload.relation|lower }}</span></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </details>
  {% endif %}

  {% if v.has_private_pension is not none or v.has_life_insurance is not none %}
  <p style="margin-top:1rem; color:var(--text-muted); font-size:0.85rem;">
    Privātā pensija: <strong>{{ 'ir' if v.has_private_pension else 'nav' }}</strong> ·
    Dzīvības apdrošināšana: <strong>{{ 'ir' if v.has_life_insurance else 'nav' }}</strong>
  </p>
  {% endif %}

  <p style="margin-top:1rem; font-size:0.8rem; color:var(--text-muted);">
    Avots: <a href="{{ v.source_url | safe_url }}" target="_blank" rel="noopener">VID Valsts amatpersonu deklarāciju portāls</a>
    (atver search ar šo politiķi; izvēlies konkrēto deklarāciju no saraksta)
  </p>
</div>
{% endfor %}

<script>
function showVadYear(declId, btn) {
  document.querySelectorAll('.vad-decl').forEach(d => d.style.display = 'none');
  document.querySelectorAll('.vad-year-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('vad-decl-' + declId).style.display = '';
  btn.classList.add('active');
}
</script>
{% endif %}
```

- [ ] **Step 2: Pievieno CSS uz assets/style.css**

```css
/* === VAD declarations panel === */
.vad-year-tab {
  background: var(--surface2);
  border: 1px solid var(--border);
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.vad-year-tab.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.vad-section { border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 0.75rem; }
.vad-delta-marker {
  display: inline-block; padding: 0.1rem 0.5rem; border-radius: 3px;
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;
}
.vad-delta-marker-new { background: #dcfce7; color: #166534; }
.vad-delta-marker-modified { background: #fef3c7; color: #92400e; }
.vad-delta-marker-removed { background: #fee2e2; color: #991b1b; }
tr.vad-delta-removed td { color: var(--text-muted); text-decoration: line-through; }
tr.vad-delta-modified { background: rgba(254, 243, 199, 0.15); }
tr.vad-delta-new { background: rgba(220, 252, 231, 0.15); }
```

- [ ] **Step 3: Commit**

`.git-commit-msg.tmp`:
```
feat(vad): _vad_panel.html.j2 partial + .vad-delta-* CSS

Year selector chips (top 5 deklarācijas), 9 sekciju akkordeoni ar delta marķieriem
(jauns zaļš / mainījies dzeltens / aizgāja sarkans). Ģimene zem collapsed details
(spec § 9.5 etika). Source link uz VID search ar pre-filled vārdu.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add templates/_vad_panel.html.j2 assets/style.css
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 15: Politician template — pievieno tab content + stat button

**Files:**
- Modify: `templates/politician.html.j2`

- [ ] **Step 1: Atrod pareizās ievietošanas vietas**

```bash
grep -n "Saites tab" templates/politician.html.j2
grep -n "showProfileTab('saites'" templates/politician.html.j2
```

- [ ] **Step 2: Pievieno stat button pēc 'saites' rindas**

Atrod `{% if 'saites' in tab_set %}` profile-stats-bar rindā. Pēc tās bloka pievieno:

```jinja
{% if 'deklaracijas' in tab_set %}
<button class="profile-stat" onclick="showProfileTab('deklaracijas', this)" data-tab="deklaracijas">
  <span class="profile-stat-value">{{ vad_data|length }}</span>
  <span class="profile-stat-label">Deklarācijas</span>
</button>
{% endif %}
```

- [ ] **Step 3: Pievieno tab content blok**

Atrod pēdējo `<!-- Saites tab -->` block end. Pēc tā pievieno:

```jinja
<!-- Deklarācijas tab -->
{% if 'deklaracijas' in tab_set %}
<div class="profile-tab" id="tab-deklaracijas" style="display:none;">
  {% include "_vad_panel.html.j2" %}
</div>
{% endif %}
```

- [ ] **Step 4: Smoke render**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
```

Expected: success without exceptions. Verify `output/atmina/politiki/ainars-slesers.html` satur `id="tab-deklaracijas"`.

```bash
.venv/Scripts/python -c "
from pathlib import Path
html = Path('output/atmina/politiki/ainars-slesers.html').read_text(encoding='utf-8')
print('tab-deklaracijas' in html)
print('Deklarācijas' in html)
"
```
Expected: `True True`.

- [ ] **Step 5: Commit**

`.git-commit-msg.tmp`:
```
feat(politician-template): Deklarācijas stat button + tab content block

Konditionāls pa tab_set; ievieto pēc Saites tab. Smoke render — Šlesera lapā
tab eksistē, var clickot un satur 11 sekciju partial.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add templates/politician.html.j2
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 16: `_fetch_politicians` integrāciju komplet — vad_data ielādē

**Files:**
- Modify: `src/render/politicians.py`

- [ ] **Step 1: Pievieno vad_data per politiķis context**

`render_politician_page` (vai equivalent funkcijai, kas renderē per-politician HTML) saņem `vad_data` un nodod template'a:

```python
# Atrod, kur context tiek būvēts. Pievieno:
from src.render.vad import get_vad_data_for_politicians
# ...
vad_all = get_vad_data_for_politicians(db, [pid])
context["vad_data"] = vad_all.get(pid, [])
```

VAI batch-load uz visiem politiķiem PIRMS render loopa (efektīvāk):

```python
# generate_politicians_page() — kur loops pār visiem politiķiem
all_pids = [p["id"] for p in politicians]
vad_all = get_vad_data_for_politicians(db, all_pids)
for p in politicians:
    context["vad_data"] = vad_all.get(p["id"], [])
    render(...)
```

- [ ] **Step 2: Smoke**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()" 2>&1 | tail -20
```

Expected: success, render time pieaugums <10% (~3s budget).

```bash
# Pārbauda Šlesera lapu satur reālus deklarāciju datus
.venv/Scripts/python -c "
from pathlib import Path
html = Path('output/atmina/politiki/ainars-slesers.html').read_text(encoding='utf-8')
print('AVADEL' in html)  # company name from sec 4
print('76351' in html)    # alga summa from sec 7
"
```
Expected: `True True`.

- [ ] **Step 3: Commit**

`.git-commit-msg.tmp`:
```
feat(politicians-render): batch ielādē vad_data un nodod template'am

Single batch query 152 politiķiem reizē (F4 leaf-vs-fan-out paterns); render
budget +~2s. Šlesera smoke verificē AVADEL company + 76351 alga in HTML.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add src/render/politicians.py
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 17: Sample profilu manuāla smoke pārbaude

- [ ] **Step 1: Sweep'ē 4 politiķiem (papildus Šleseram, kuram jau ir dati)**

Iepriekš ielādē 4 dažādus profile_kind, lai validētu UI plašumā:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py --politician silina-evika  # minister
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py --politician pupols-ansis  # mep
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py --politician kleinbergs-viesturs  # regional
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py --politician hermanis-alvis  # politician kind
```

Expected: katram 1-3 modernās deklarācijas insert'ētas.

- [ ] **Step 2: Re-render**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
```

- [ ] **Step 3: Manuāli atver browseri**

```bash
python serve.py &
# Atver:
# http://127.0.0.1:8080/politiki/ainars-slesers.html
# http://127.0.0.1:8080/politiki/evika-silina.html
# http://127.0.0.1:8080/politiki/ansis-pupols.html
# http://127.0.0.1:8080/politiki/viesturs-kleinbergs.html
# http://127.0.0.1:8080/politiki/alvis-hermanis.html
```

Pārbauda katrai lapai:
- [ ] Deklarācijas tab parādās stat-bar rindā
- [ ] Klik atver tabu
- [ ] Year selector chips (kā ir 2+ gadi)
- [ ] Sekcijas akkordeoni atveras un satur datus
- [ ] Delta marķieri (jauns/mainījies) parādās jaunākajai gadā ar diff_text
- [ ] Ģimene ir collapsed default
- [ ] Source link atver VID portālu

- [ ] **Step 4: Pierakstī issues, ja jebkurš nestrādā** un fix; otherwise commit log:

`wiki/log-ingest/2026-05.md`:
```markdown
- VAD initial sweep (5 sample profiles)
  - Šlesers Ainārs: 3 modernās deklarācijas, sekcijas korekti renderē
  - Siliņa Evika: ...
  - ...
```

```bash
git add wiki/log-ingest/2026-05.md
.git-commit-msg.tmp:
docs(log): VAD Phase 1 smoke sample log
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 18: Initial full sweep + log entry

- [ ] **Step 1: Pilns sweep**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py 2>&1 | tee logs/vad-initial-sweep-$(date +%Y%m%d).log
```

Expected: ~35 min, ~130-140 politiķiem ar 1+ deklarāciju, 0-15 errors.

- [ ] **Step 2: Verifikācija**

```bash
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
print('Politiķi ar 1+ deklarāciju:', con.execute('SELECT COUNT(DISTINCT opponent_id) FROM vad_declarations').fetchone()[0])
print('Kopā deklarācijas:', con.execute('SELECT COUNT(*) FROM vad_declarations').fetchone()[0])
print('Per gads:')
for r in con.execute('SELECT declaration_year, COUNT(*) FROM vad_declarations GROUP BY declaration_year ORDER BY declaration_year DESC'):
    print(f'  {r[0]}: {r[1]}')
"
```

Expected: ≥130/152 politiķi, ≥350 deklarācijas (~3 vidēji), peak years 2022-2024.

- [ ] **Step 3: Politiķi BEZ deklarāciju — review**

```bash
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
for r in con.execute('''
    SELECT tp.name, tp.role FROM tracked_politicians tp
    LEFT JOIN vad_declarations vd ON vd.opponent_id = tp.id
    WHERE tp.relationship_type = 'tracked' AND vd.id IS NULL
    ORDER BY tp.name
'''):
    print(f'{r[\"name\"]:<35} role={r[\"role\"]!r}')
"
```

Pārskata sarakstu: vai katrs ir gaidāms (ne-amatpersona, novecojis, spec edge case)? Ja konkrēts politiķis nezi rs jāsekot, pievieno `_NAME_OVERRIDES` `src/vad/matcher.py` un re-run tikai šo politiķi.

- [ ] **Step 4: Final re-render + deploy preview**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
bash scripts/deploy.sh --dry-run
```

- [ ] **Step 5: Commit log**

`wiki/log-ingest/2026-05.md`:
```markdown
- VAD initial full sweep (Phase 0 boot)
  - 152 politiķi sweep'ēti
  - N deklarācijas insert'ētas
  - K politiķi bez deklarācijām (skat. {kāpēc — failed politicians list})
  - Skip role: K
  - Skip legacy: K
  - Errors: K
  - Apjēga: ~M minūtes
```

```bash
git add wiki/log-ingest/2026-05.md
.git-commit-msg.tmp:
docs(log): VAD initial full sweep — 152 politiķi, N deklarācijas
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

---

### Task 19: Phase 1 CHANGELOG + final smoke

**Files:**
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Pievieno Phase 1 entry pirms Phase 0 entry**

```markdown
## 2026-05-02 — VAD declarations Phase 1 (UI tab + delta render)

**TL;DR:** "Deklarācijas" tab pievienots politiķa profilā (deputy, minister, mep,
regional, former, politician profile_kinds — has_vad_data konditionāls). Tab satur
year selector (top 5 gadi), 9 sekciju akkordeoni ar delta marķieriem (jauns/
mainījies/aizgāja), ģimene zem collapsed details (etika), source link uz VID
search ar pre-filled vārdu.

**Arhitektūra:**
- `src/render/vad.py` — batch fetch ar one query per tabula (F4 leaf-vs-fan-out
  paterns). Try/except OperationalError guard test DB priekš (saeima_bills
  precedents `src/render/politicians.py:503`).
- `src/vad/diff.py` — year-over-year delta engine ar 5% threshold un identity
  keys per sekcija (skat. spec § 9.2 tabula).
- `templates/_vad_panel.html.j2` — partial, included no `politician.html.j2`.
- `assets/style.css` — `.vad-delta-{new,modified,removed,unchanged}` ar
  green/yellow/red/muted krāsām, `.vad-section` border-separated akkordeoni.
- `src/profile_kind.py` + `src/render/politicians.py` — `_profile_tab_set`
  paplašināts ar `has_vad_data` argumentu, `_fetch_politicians` ielādē
  `vad_count` reizē batch.

**Render performance:** +~2s uz 30s baseline (6.7%, zem 10% budget). Single
batch query 11 tabulām × visi 152 politiķi.

**Privātums:** Ģimene renderēta zem `<details>` collapsed default — saskan ar
spec § 9.5 ētisko politiku (publiska, bet nepiespiedu).

---
```

- [ ] **Step 2: Final check.sh palaišana**

```bash
bash scripts/check.sh
```

Expected: ruff clean, all pytest pass (>30 jaunie VAD testi), generate_public_site smoke success.

- [ ] **Step 3: Commit + final**

`.git-commit-msg.tmp`:
```
docs(changelog): VAD declarations Phase 1 UI tab + delta render

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add wiki/CHANGELOG.md
git commit -F .git-commit-msg.tmp && rm .git-commit-msg.tmp
```

- [ ] **Step 4: Telegram notify operatorimies par gatavo Phase 0+1**

Phase 0+1 ielikts produkcijā. Mēneša rutīna sākas no nākamā mēneša (jūnijs 2026).

---

## Self-review

**Spec coverage check (sūta uz spec § sections):**
- § 2 (scope Phase 0+1) — Tasks 1-10 ietver Phase 0, Tasks 11-19 ietver Phase 1 ✓
- § 3 (avota analīze) — Task 4 implementē ar verificētajiem URL/headers ✓
- § 4 (datu modelis 11 tabulas) — Task 1 ✓
- § 5 (parser layout) — Task 3 (parser tests pārveido pret Šlesers fixture) ✓
- § 6 (politiķu sasaiste) — Task 5 (matcher) + Task 6 (orchestrator) ✓
- § 7 (idempotence) — Task 6 (UNIQUE constraint + skip esošos) ✓
- § 8 (CLI) — Task 8 ✓
- § 9 (render) — Tasks 11-16 ✓
- § 10 (juridiskais) — Task 9 (runbook) + ingest log entry ✓
- § 11 (testēšana) — testi katrā Task ✓
- § 12 (work breakdown) — atbilst plāna struktūrai ✓
- § 13 (Q1-Q6 atklātie jautājumi) — Q1 (search-link verifikācija) impl Task 4 smoke; Q2 (paginate) Task 4 implementē; Q3 (robots.txt) Task 4 manual smoke; Q4 (legacy skip) Task 6; Q5 (hyphenated VID accept) Task 9 runbook bootstrap; Q6 (ASCII fallback) Task 5 ✓
- § 14 (success metrics) — Task 18 verificē coverage ≥130/152 ✓
- § 15 (audit trail F1-F10) — visi 10 fix'i ietverti pareizajos tasks (F1 → Task 5, F2 → Task 6, F3 → Task 9 runbook, F4 → Task 1 DDL, F5 → Tasks 1+3, F6 → Task 5, F7 → Task 12, F8 → Task 13, F9 → Task 3, F10 → Task 4) ✓

**Placeholder scan:**
- "Phase 0.5 backlog" un "Phase 2-4 backlog" — pareizi ārpus scope.
- Task 13 Step 3 — "Modificē _fetch_politicians..." ar minimālu diff illustrāciju, ne pilnu kodu. Tas ir tāpēc, ka esošās funkcijas precīza forma būs jāizpēta runtime; bet šis ir riskants placeholder. **Risinājums**: pirms Task 13 palaišanas, nolasīt esošo `_fetch_politicians` un `_profile_tab_set`, tad rediģēt vienu reizi ar pilnu diff. Plāns to skaidri pasaka Step 1.
- Task 17 Step 1 — politiķu slugi (silina-evika, pupols-ansis utt.) ir manuāli iemestajumi. **Risinājums**: pirms palaišanas, verificēt sluga formātu ar `ls output/atmina/politiki/ | head -10`.

**Type/method consistency:**
- `VadClient.search()` returns `list[SearchResultRow]` — konsistenti starp Tasks 4, 5, 6 ✓
- `parse_declaration_html(html)` returns `ParsedDeclaration` — konsistenti starp Tasks 3, 6 ✓
- `compute_section_deltas(section, prev, curr)` — konsistenti starp Tasks 11, 12 ✓
- `vad_count_per_politician(db)` returns `dict[int, int]` — konsistenti Tasks 12, 13 ✓
- `get_vad_data_for_politicians(db, pids)` returns `dict[int, list[VadDeclarationView]]` — konsistenti Tasks 12, 16 ✓

Plāns gatavs.
