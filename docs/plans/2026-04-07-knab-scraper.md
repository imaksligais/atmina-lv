# KNAB Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape all donations (~73K) and active party declarations from info.knab.gov.lv, store in SQLite, cross-reference with tracked_politicians/saeima_votes, detect anomalies.

**Architecture:** Single module `src/knab.py` following the same patterns as `src/saeima.py` — dataclasses for structured data, httpx + BeautifulSoup for HTML parsing, direct SQLite storage via `src/db.py` helpers. New tables added to `init_db()`. A separate `src/knab_analyze.py` handles cross-referencing and anomaly detection. Site integration via new template + generate.py additions.

**Tech Stack:** Python 3.11+, httpx, BeautifulSoup4, SQLite (existing atmina.db), Pydantic validation.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/knab.py` | KNAB scraper — fetch, parse, store donations + declarations |
| `src/knab_analyze.py` | Cross-referencing, anomaly detection, report generation |
| `src/db.py` | Add new tables (knab_donations, knab_declarations, knab_donors, knab_alerts) to `init_db()` |
| `tests/test_knab.py` | Unit tests for parsing + anomaly detection |
| `tests/fixtures/knab_donations_page.html` | Sample HTML fixture for donation list page |
| `tests/fixtures/knab_declarations_page.html` | Sample HTML fixture for declaration list page |
| `templates/finanses.html.j2` | New page template for party finance data on atmina.lv |
| `src/generate.py` | Add `_generate_finanses_page()` to site generator |

---

## Task 1: Database Schema — New KNAB Tables

**Files:**
- Modify: `src/db.py:22-224` (inside `init_db()`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knab.py
import sqlite3
import os
import tempfile

def test_knab_tables_created():
    """init_db creates all four KNAB tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from src.db import init_db
        init_db(db_path)
        db = sqlite3.connect(db_path)
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'knab_%'"
        ).fetchall()]
        db.close()
        assert "knab_donors" in tables
        assert "knab_donations" in tables
        assert "knab_declarations" in tables
        assert "knab_alerts" in tables
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_knab_tables_created -v`
Expected: FAIL — tables don't exist yet.

- [ ] **Step 3: Add KNAB tables to init_db()**

Add this SQL block inside `init_db()` in `src/db.py`, right after the `mention_classifications` table creation (before the sqlite-vec section at line ~226):

```python
        -- KNAB: Donors (unique persons)
        CREATE TABLE IF NOT EXISTS knab_donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            personal_id_masked TEXT,
            politician_id INTEGER REFERENCES tracked_politicians(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, personal_id_masked)
        );

        -- KNAB: Donations
        CREATE TABLE IF NOT EXISTS knab_donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knab_id TEXT UNIQUE,
            donor_id INTEGER REFERENCES knab_donors(id),
            party TEXT NOT NULL,
            donation_type TEXT NOT NULL,
            amount_eur REAL NOT NULL,
            currency TEXT DEFAULT 'EUR',
            original_amount TEXT,
            donor_name TEXT NOT NULL,
            donor_pid_masked TEXT,
            date TEXT NOT NULL,
            detail_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- KNAB: Declarations (annual reports + election declarations)
        CREATE TABLE IF NOT EXISTS knab_declarations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knab_id TEXT UNIQUE,
            party TEXT NOT NULL,
            declaration_type TEXT NOT NULL,
            year INTEGER NOT NULL,
            date TEXT,
            detail_url TEXT,
            income_total REAL,
            income_donations REAL,
            income_membership REAL,
            income_state_budget REAL,
            expenses_total REAL,
            expenses_advertising REAL,
            expenses_salaries REAL,
            raw_data TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- KNAB: Alerts (anomalies detected by cross-referencing)
        CREATE TABLE IF NOT EXISTS knab_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            party TEXT,
            donor_id INTEGER REFERENCES knab_donors(id),
            politician_id INTEGER REFERENCES tracked_politicians(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            data TEXT,
            reviewed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_knab_donations_party ON knab_donations(party);
        CREATE INDEX IF NOT EXISTS idx_knab_donations_donor ON knab_donations(donor_id);
        CREATE INDEX IF NOT EXISTS idx_knab_donations_date ON knab_donations(date);
        CREATE INDEX IF NOT EXISTS idx_knab_donors_politician ON knab_donors(politician_id);
        CREATE INDEX IF NOT EXISTS idx_knab_declarations_party ON knab_declarations(party, year);
        CREATE INDEX IF NOT EXISTS idx_knab_alerts_type ON knab_alerts(alert_type, severity);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_knab_tables_created -v`
Expected: PASS

- [ ] **Step 5: Run type check**

Run: `cd "~/atmina" && python -c "from src.db import init_db; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
cd "~/atmina"
git add src/db.py tests/test_knab.py
git commit -m "feat(knab): add database tables for donations, declarations, donors, alerts"
```

---

## Task 2: HTML Parsing — Donation List Page

**Files:**
- Create: `src/knab.py`
- Create: `tests/fixtures/knab_donations_page.html`

- [ ] **Step 1: Capture a real HTML fixture**

Fetch one page from KNAB and save as test fixture:

```python
# Run once manually:
import httpx
resp = httpx.get("https://info.knab.gov.lv/lv/db/ziedojumi/?page=0&recordsPerPage=50", timeout=30)
with open("tests/fixtures/knab_donations_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
```

- [ ] **Step 2: Write the failing test for parsing donations**

```python
# tests/test_knab.py (append)
import os

def test_parse_donations_page():
    """Parse a real KNAB donations HTML page into structured data."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    if not os.path.exists(fixture_path):
        import pytest
        pytest.skip("Fixture not yet captured")

    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    from src.knab import parse_donations_page
    donations = parse_donations_page(html)

    assert len(donations) > 0
    assert len(donations) <= 50  # default page size

    d = donations[0]
    assert "party" in d
    assert "donation_type" in d
    assert "amount_eur" in d
    assert "donor_name" in d
    assert "date" in d
    assert isinstance(d["amount_eur"], float)
    assert d["amount_eur"] > 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_parse_donations_page -v`
Expected: FAIL — `src.knab` doesn't exist.

- [ ] **Step 4: Implement src/knab.py with parse_donations_page**

```python
"""
KNAB political finance scraper for atmina.

Scrapes donations and declarations from info.knab.gov.lv.
Stores structured data in SQLite for cross-referencing with
tracked politicians and Saeima voting records.

Data flow:
  1. Fetch paginated HTML from KNAB website
  2. Parse HTML tables into structured dicts
  3. Upsert donors, donations, declarations into knab_* tables
  4. Link donors to tracked_politicians by name matching
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.db import DB_PATH, get_db, now_lv, log_action

KNAB_BASE = "https://info.knab.gov.lv"
DONATIONS_URL = f"{KNAB_BASE}/lv/db/ziedojumi/"
DECLARATIONS_URL = f"{KNAB_BASE}/lv/db/deklaracijas/"

# Rate limit: polite 2 second delay between requests
RATE_LIMIT_SECONDS = 2

# Active parties for declaration scraping (Tier 1 + Tier 2)
TRACKED_PARTIES = [
    # Tier 1: Currently in Saeima
    "Jaunā VIENOTĪBA",
    "Nacionālā apvienība \"Visu Latvijai!\"-\"Tēvzemei un Brīvībai/LNNK\"",
    "\"PROGRESĪVIE\"",
    "Zaļo un Zemnieku savienība",
    "\"APVIENOTAIS SARAKSTS",  # prefix match — full name includes coalition partners
    "LATVIJA PIRMAJĀ VIETĀ",
    # Tier 2: Planning to run in 2026
    "\"Mēs mainām noteikumus\"",
    "\"Stabilitātei!\"",
    "\"Latvijas attīstībai\"",
    "Politisko partiju apvienība \"Saskaņas Centrs\"",
    "\"Saskaņa\" sociāldemokrātiskā partija",
    # Tier 2: Active at municipal level / significant donors
    "Latvijas Zaļā partija",
    "\"LATVIJAS ZEMNIEKU SAVIENĪBA\"",
    "Latvijas Reģionu apvienība",
    "\"Gods kalpot Rīgai\"",
    "JKP Jaunā konservatīvā partija",
    "Kustība \"Par!\"",
    "Latvijas Sociāldemokrātiskā strādnieku partija",
]


def _parse_amount(text: str) -> tuple[float, str]:
    """Parse 'EUR 200.00' or 'LVL 50.00' into (amount, currency)."""
    text = text.strip()
    match = re.match(r"(EUR|LVL)\s+([\d\s,.]+)", text)
    if not match:
        return 0.0, "EUR"
    currency = match.group(1)
    amount_str = match.group(2).replace(" ", "").replace(",", "")
    try:
        return float(amount_str), currency
    except ValueError:
        return 0.0, currency


def _parse_date_lv(text: str) -> str:
    """Convert 'dd.mm.yyyy' to 'yyyy-mm-dd' for SQLite sorting."""
    text = text.strip()
    match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return text


def _extract_donor_pid(text: str) -> tuple[str, str]:
    """Split 'Jānis Bērziņš120680*****' into (name, pid_masked)."""
    match = re.match(r"^(.+?)(\d{6}\*{5})$", text.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return text.strip(), ""


def parse_donations_page(html: str) -> list[dict]:
    """Parse a KNAB donations list page into structured dicts."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.data-table") or soup.select_one("table")
    if not table:
        return []

    rows = table.select("tbody tr")
    if not rows:
        # Try without tbody
        rows = table.select("tr")[1:]  # skip header

    donations = []
    for row in rows:
        cells = row.select("td")
        if len(cells) < 5:
            continue

        party = cells[0].get_text(strip=True)
        donation_type = cells[1].get_text(strip=True)
        amount_text = cells[2].get_text(strip=True)
        persona_text = cells[3].get_text(strip=True)
        date_text = cells[4].get_text(strip=True)

        amount_eur, currency = _parse_amount(amount_text)
        donor_name, donor_pid = _extract_donor_pid(persona_text)

        # Extract detail link if present
        link = cells[0].select_one("a") or row.select_one("a")
        detail_url = None
        if link and link.get("href"):
            href = link["href"]
            if not href.startswith("http"):
                detail_url = f"{KNAB_BASE}{href}"
            else:
                detail_url = href

        # Generate a stable ID from party+donor+date+amount
        knab_id = f"d-{party[:20]}-{donor_name[:20]}-{date_text}-{amount_text}".replace(" ", "_")

        donations.append({
            "knab_id": knab_id,
            "party": party,
            "donation_type": donation_type,
            "amount_eur": amount_eur,
            "currency": currency,
            "original_amount": amount_text,
            "donor_name": donor_name,
            "donor_pid_masked": donor_pid,
            "date": _parse_date_lv(date_text),
            "detail_url": detail_url,
        })

    return donations
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_parse_donations_page -v`
Expected: PASS (or SKIP if fixture not yet captured)

- [ ] **Step 6: Commit**

```bash
cd "~/atmina"
git add src/knab.py tests/test_knab.py tests/fixtures/
git commit -m "feat(knab): donation page parser with HTML table extraction"
```

---

## Task 3: HTML Parsing — Declaration List Page

**Files:**
- Modify: `src/knab.py`
- Create: `tests/fixtures/knab_declarations_page.html`

- [ ] **Step 1: Capture a real declarations HTML fixture**

```python
import httpx
resp = httpx.get("https://info.knab.gov.lv/lv/db/deklaracijas/?page=0&recordsPerPage=50", timeout=30)
with open("tests/fixtures/knab_declarations_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_knab.py (append)
def test_parse_declarations_page():
    """Parse a real KNAB declarations HTML page."""
    fixture_path = os.path.join("tests", "fixtures", "knab_declarations_page.html")
    if not os.path.exists(fixture_path):
        import pytest
        pytest.skip("Fixture not yet captured")

    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    from src.knab import parse_declarations_page
    declarations = parse_declarations_page(html)

    assert len(declarations) > 0
    d = declarations[0]
    assert "party" in d
    assert "declaration_type" in d
    assert "year" in d
    assert isinstance(d["year"], int)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_parse_declarations_page -v`
Expected: FAIL — `parse_declarations_page` not defined.

- [ ] **Step 4: Implement parse_declarations_page**

Add to `src/knab.py`:

```python
def parse_declarations_page(html: str) -> list[dict]:
    """Parse a KNAB declarations list page into structured dicts."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.data-table") or soup.select_one("table")
    if not table:
        return []

    rows = table.select("tbody tr")
    if not rows:
        rows = table.select("tr")[1:]

    declarations = []
    for row in rows:
        cells = row.select("td")
        if len(cells) < 4:
            continue

        party = cells[0].get_text(strip=True)
        decl_type = cells[1].get_text(strip=True)
        year_text = cells[2].get_text(strip=True)
        date_text = cells[3].get_text(strip=True)

        try:
            year = int(year_text)
        except ValueError:
            year = 0

        link = cells[0].select_one("a") or row.select_one("a")
        detail_url = None
        knab_id = None
        if link and link.get("href"):
            href = link["href"]
            if not href.startswith("http"):
                detail_url = f"{KNAB_BASE}{href}"
            else:
                detail_url = href
            # Extract ID from URL: ?id=DDMMYYYY-NNNNNNNN
            id_match = re.search(r"[?&]id=([^&]+)", href)
            if id_match:
                knab_id = id_match.group(1)

        if not knab_id:
            knab_id = f"dcl-{party[:20]}-{year}-{decl_type[:10]}".replace(" ", "_")

        declarations.append({
            "knab_id": knab_id,
            "party": party,
            "declaration_type": decl_type,
            "year": year,
            "date": _parse_date_lv(date_text),
            "detail_url": detail_url,
        })

    return declarations
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_parse_declarations_page -v`
Expected: PASS (or SKIP)

- [ ] **Step 6: Commit**

```bash
cd "~/atmina"
git add src/knab.py tests/test_knab.py tests/fixtures/
git commit -m "feat(knab): declaration page parser"
```

---

## Task 4: Fetch Engine — Paginated Scraping with Progress

**Files:**
- Modify: `src/knab.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knab.py (append)
def test_build_donations_url():
    """URL builder produces correct paginated KNAB URLs."""
    from src.knab import _build_url, DONATIONS_URL
    url = _build_url(DONATIONS_URL, page=3, per_page=500)
    assert "page=3" in url
    assert "recordsPerPage=500" in url

def test_build_filtered_url():
    """URL builder handles party filter."""
    from src.knab import _build_url, DONATIONS_URL
    url = _build_url(DONATIONS_URL, page=0, per_page=500, party="Jaunā VIENOTĪBA")
    assert "page=0" in url
    assert "recordsPerPage=500" in url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_build_donations_url tests/test_knab.py::test_build_filtered_url -v`
Expected: FAIL

- [ ] **Step 3: Implement URL builder and fetch engine**

Add to `src/knab.py`:

```python
from urllib.parse import urlencode


def _build_url(base: str, page: int = 0, per_page: int = 500, **filters) -> str:
    """Build a paginated KNAB URL with optional filters."""
    params = {"page": page, "recordsPerPage": per_page}
    for key, value in filters.items():
        if value is not None:
            params[key] = value
    return f"{base}?{urlencode(params)}"


def _fetch_page(url: str, client: httpx.Client) -> str:
    """Fetch one page with retry logic."""
    for attempt in range(3):
        try:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    return ""


def _get_total_pages(html: str, per_page: int = 500) -> int:
    """Extract total page count from KNAB pagination footer."""
    soup = BeautifulSoup(html, "lxml")
    # Look for pagination links — last page number
    pager = soup.select("a.page-link, a[href*='page=']")
    max_page = 0
    for link in pager:
        href = link.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page


def fetch_all_donations(
    db_path: str = DB_PATH,
    per_page: int = 500,
    delay: float = RATE_LIMIT_SECONDS,
    max_pages: int = 0,
) -> int:
    """
    Fetch ALL donations from KNAB and store in knab_donations table.

    Args:
        db_path: SQLite database path
        per_page: Records per page (max 500)
        delay: Seconds between requests
        max_pages: If >0, stop after this many pages (for testing)

    Returns:
        Total number of new donations inserted.
    """
    db = get_db(db_path)
    client = httpx.Client(
        headers={"User-Agent": "atmina.lv political transparency research"},
        follow_redirects=True,
    )

    total_new = 0
    page = 0

    try:
        # Fetch first page to determine total pages
        url = _build_url(DONATIONS_URL, page=0, per_page=per_page)
        html = _fetch_page(url, client)
        total_pages = _get_total_pages(html, per_page)
        if max_pages > 0:
            total_pages = min(total_pages, max_pages - 1)

        print(f"[KNAB] Ziedojumi: {total_pages + 1} lapas ar {per_page} ierakstiem")

        # Process first page
        donations = parse_donations_page(html)
        new = _store_donations(db, donations)
        total_new += new
        print(f"  Lapa 0: {len(donations)} ieraksti, {new} jauni")

        # Fetch remaining pages
        for page in range(1, total_pages + 1):
            time.sleep(delay)
            url = _build_url(DONATIONS_URL, page=page, per_page=per_page)
            html = _fetch_page(url, client)
            donations = parse_donations_page(html)
            new = _store_donations(db, donations)
            total_new += new
            if page % 10 == 0 or page == total_pages:
                print(f"  Lapa {page}/{total_pages}: {len(donations)} ieraksti, {new} jauni")

    finally:
        client.close()
        log_action(db, "knab_fetch_donations", status="success",
                   details=f"pages={page+1}, new={total_new}")
        db.close()

    print(f"[KNAB] Ziedojumi pabeigti: {total_new} jauni ieraksti")
    return total_new


def _store_donations(db, donations: list[dict]) -> int:
    """Store parsed donations, upsert donors. Returns count of new records."""
    new_count = 0
    for d in donations:
        # Upsert donor
        donor_id = _upsert_donor(db, d["donor_name"], d["donor_pid_masked"])

        # Insert donation (skip if knab_id already exists)
        try:
            db.execute(
                """INSERT OR IGNORE INTO knab_donations
                   (knab_id, donor_id, party, donation_type, amount_eur, currency,
                    original_amount, donor_name, donor_pid_masked, date, detail_url, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d["knab_id"], donor_id, d["party"], d["donation_type"],
                 d["amount_eur"], d["currency"], d["original_amount"],
                 d["donor_name"], d["donor_pid_masked"], d["date"],
                 d["detail_url"], now_lv()),
            )
            if db.execute("SELECT changes()").fetchone()[0] > 0:
                new_count += 1
        except Exception:
            pass  # Skip duplicates silently
    db.commit()
    return new_count


def _upsert_donor(db, name: str, pid_masked: str) -> int:
    """Get or create a donor record. Returns donor_id."""
    row = db.execute(
        "SELECT id FROM knab_donors WHERE name = ? AND personal_id_masked = ?",
        (name, pid_masked),
    ).fetchone()
    if row:
        return row[0]

    db.execute(
        "INSERT INTO knab_donors (name, personal_id_masked, created_at) VALUES (?, ?, ?)",
        (name, pid_masked, now_lv()),
    )
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]
```

- [ ] **Step 4: Run tests**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "~/atmina"
git add src/knab.py tests/test_knab.py
git commit -m "feat(knab): paginated donation fetch engine with donor upsert"
```

---

## Task 5: Declaration Fetcher — Filtered by Active Parties

**Files:**
- Modify: `src/knab.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knab.py (append)
def test_is_tracked_party():
    """Party filter matches tracked parties including prefix matches."""
    from src.knab import _is_tracked_party
    assert _is_tracked_party("Jaunā VIENOTĪBA") is True
    assert _is_tracked_party("\"PROGRESĪVIE\"") is True
    assert _is_tracked_party("\"APVIENOTAIS SARAKSTS - Latvijas Zaļā partija, ...\"") is True
    assert _is_tracked_party("Kāda nedzirdēta partija") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_is_tracked_party -v`
Expected: FAIL

- [ ] **Step 3: Implement party filter and declaration fetcher**

Add to `src/knab.py`:

```python
def _is_tracked_party(party_name: str) -> bool:
    """Check if a party name matches our tracked parties list (prefix match)."""
    name_lower = party_name.lower()
    for tracked in TRACKED_PARTIES:
        if name_lower.startswith(tracked.lower()) or tracked.lower() in name_lower:
            return True
    return False


def fetch_all_declarations(
    db_path: str = DB_PATH,
    per_page: int = 500,
    delay: float = RATE_LIMIT_SECONDS,
    max_pages: int = 0,
) -> int:
    """
    Fetch declarations for tracked parties only.

    Paginates through all declarations but only stores those
    matching TRACKED_PARTIES. Returns count of new declarations stored.
    """
    db = get_db(db_path)
    client = httpx.Client(
        headers={"User-Agent": "atmina.lv political transparency research"},
        follow_redirects=True,
    )

    total_new = 0
    page = 0

    try:
        url = _build_url(DECLARATIONS_URL, page=0, per_page=per_page)
        html = _fetch_page(url, client)
        total_pages = _get_total_pages(html, per_page)
        if max_pages > 0:
            total_pages = min(total_pages, max_pages - 1)

        print(f"[KNAB] Deklarācijas: {total_pages + 1} lapas, filtrējam {len(TRACKED_PARTIES)} partijas")

        # Process first page
        declarations = parse_declarations_page(html)
        filtered = [d for d in declarations if _is_tracked_party(d["party"])]
        new = _store_declarations(db, filtered)
        total_new += new
        print(f"  Lapa 0: {len(declarations)} kopā, {len(filtered)} atbilstošas, {new} jaunas")

        for page in range(1, total_pages + 1):
            time.sleep(delay)
            url = _build_url(DECLARATIONS_URL, page=page, per_page=per_page)
            html = _fetch_page(url, client)
            declarations = parse_declarations_page(html)
            filtered = [d for d in declarations if _is_tracked_party(d["party"])]
            new = _store_declarations(db, filtered)
            total_new += new
            if page % 5 == 0 or page == total_pages:
                print(f"  Lapa {page}/{total_pages}: {len(filtered)} atbilstošas, {new} jaunas")

    finally:
        client.close()
        log_action(db, "knab_fetch_declarations", status="success",
                   details=f"pages={page+1}, new={total_new}")
        db.close()

    print(f"[KNAB] Deklarācijas pabeigtas: {total_new} jauni ieraksti")
    return total_new


def _store_declarations(db, declarations: list[dict]) -> int:
    """Store parsed declarations. Returns count of new records."""
    new_count = 0
    for d in declarations:
        try:
            db.execute(
                """INSERT OR IGNORE INTO knab_declarations
                   (knab_id, party, declaration_type, year, date, detail_url, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (d["knab_id"], d["party"], d["declaration_type"],
                 d["year"], d["date"], d["detail_url"], now_lv()),
            )
            if db.execute("SELECT changes()").fetchone()[0] > 0:
                new_count += 1
        except Exception:
            pass
    db.commit()
    return new_count
```

- [ ] **Step 4: Run tests**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "~/atmina"
git add src/knab.py tests/test_knab.py
git commit -m "feat(knab): declaration fetcher filtered by tracked parties"
```

---

## Task 6: Donor ↔ Politician Cross-Referencing

**Files:**
- Create: `src/knab_analyze.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knab.py (append)
def test_normalize_name():
    """Name normalization for matching donors to politicians."""
    from src.knab_analyze import _normalize_name
    assert _normalize_name("JĀNIS BĒRZIŅŠ") == "janis berzins"
    assert _normalize_name("  Artūrs  Krišjānis  ") == "arturs krisjianis"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_normalize_name -v`
Expected: FAIL

- [ ] **Step 3: Implement knab_analyze.py with cross-referencing**

```python
"""
KNAB data cross-referencing and anomaly detection for atmina.

Analyzes scraped KNAB data to find:
1. Donors who are tracked politicians (or their name matches)
2. Multi-party donors
3. Family clusters (same surname, same period)
4. Donation limit violations
5. Donation sum vs declaration discrepancies
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from src.db import DB_PATH, get_db, now_lv

# Latvia donation limit: 50x minimum monthly salary
# As of 2026: EUR 700 * 50 = EUR 35,000 per year per party
# (was EUR 21,343 based on old min wage — verify current rate)
ANNUAL_DONATION_LIMIT_EUR = 35_000

# Latvian character transliteration
_LV_TRANS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)


def _normalize_name(name: str) -> str:
    """Normalize a Latvian name for fuzzy matching."""
    name = name.strip().lower()
    name = name.translate(_LV_TRANS)
    name = re.sub(r"\s+", " ", name)
    return name


def link_donors_to_politicians(db_path: str = DB_PATH) -> int:
    """
    Match knab_donors to tracked_politicians by name.

    Uses name_forms from tracked_politicians for matching.
    Returns count of newly linked donors.
    """
    db = get_db(db_path)

    # Build lookup: normalized name -> politician_id
    politicians = db.execute(
        "SELECT id, name, name_forms FROM tracked_politicians"
    ).fetchall()

    name_to_pid = {}
    for p in politicians:
        name_to_pid[_normalize_name(p["name"])] = p["id"]
        try:
            forms = json.loads(p["name_forms"]) if p["name_forms"] else []
            for form in forms:
                name_to_pid[_normalize_name(form)] = p["id"]
        except (json.JSONDecodeError, TypeError):
            pass

    # Match unlinked donors
    donors = db.execute(
        "SELECT id, name FROM knab_donors WHERE politician_id IS NULL"
    ).fetchall()

    linked = 0
    for donor in donors:
        norm = _normalize_name(donor["name"])
        if norm in name_to_pid:
            db.execute(
                "UPDATE knab_donors SET politician_id = ? WHERE id = ?",
                (name_to_pid[norm], donor["id"]),
            )
            linked += 1

    db.commit()
    db.close()
    print(f"[KNAB] Saistīti {linked} ziedotāji ar politiķiem")
    return linked


def detect_multi_party_donors(db_path: str = DB_PATH) -> list[dict]:
    """
    Find donors who gave to 2+ different parties.

    Returns list of {donor_name, donor_pid, parties: [{party, total_eur}], total_eur}.
    Also stores alerts in knab_alerts.
    """
    db = get_db(db_path)

    rows = db.execute("""
        SELECT donor_name, donor_pid_masked, party, SUM(amount_eur) as total
        FROM knab_donations
        GROUP BY donor_name, donor_pid_masked, party
        ORDER BY donor_name, total DESC
    """).fetchall()

    # Group by donor
    donors = defaultdict(list)
    for r in rows:
        key = (r["donor_name"], r["donor_pid_masked"])
        donors[key].append({"party": r["party"], "total_eur": r["total"]})

    multi = []
    for (name, pid), parties in donors.items():
        if len(parties) >= 2:
            total = sum(p["total_eur"] for p in parties)
            entry = {
                "donor_name": name,
                "donor_pid": pid,
                "parties": parties,
                "party_count": len(parties),
                "total_eur": total,
            }
            multi.append(entry)

            # Store alert
            db.execute(
                """INSERT OR IGNORE INTO knab_alerts
                   (alert_type, severity, title, description, data, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("multi_party_donor",
                 "warning" if len(parties) >= 3 else "info",
                 f"{name} ziedo {len(parties)} partijām",
                 f"Kopā EUR {total:.2f} sadalīti starp: {', '.join(p['party'] for p in parties)}",
                 json.dumps(entry, ensure_ascii=False),
                 now_lv()),
            )

    db.commit()
    db.close()

    multi.sort(key=lambda x: x["total_eur"], reverse=True)
    print(f"[KNAB] Atrasti {len(multi)} ziedotāji vairākām partijām")
    return multi


def detect_family_clusters(db_path: str = DB_PATH) -> list[dict]:
    """
    Find family clusters: same surname, same party, multiple donors.

    Returns list of {surname, party, members: [{name, total_eur}], total_eur}.
    """
    db = get_db(db_path)

    rows = db.execute("""
        SELECT donor_name, party, SUM(amount_eur) as total
        FROM knab_donations
        GROUP BY donor_name, party
    """).fetchall()

    # Group by surname + party
    clusters = defaultdict(list)
    for r in rows:
        parts = r["donor_name"].split()
        if len(parts) >= 2:
            surname = parts[-1]  # Last word is surname in Latvian
            key = (_normalize_name(surname), r["party"])
            clusters[key].append({
                "name": r["donor_name"],
                "total_eur": r["total"],
            })

    families = []
    for (surname, party), members in clusters.items():
        if len(members) >= 2:
            total = sum(m["total_eur"] for m in members)
            if total >= 1000:  # Only flag significant clusters
                entry = {
                    "surname": surname,
                    "party": party,
                    "members": sorted(members, key=lambda x: x["total_eur"], reverse=True),
                    "member_count": len(members),
                    "total_eur": total,
                }
                families.append(entry)

                db.execute(
                    """INSERT OR IGNORE INTO knab_alerts
                       (alert_type, severity, party, title, description, data, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("family_cluster",
                     "warning" if total >= 10000 else "info",
                     party,
                     f"Ģimene '{surname}': {len(members)} ziedotāji → {party}",
                     f"Kopā EUR {total:.2f} no {len(members)} personām ar uzvārdu '{surname}'",
                     json.dumps(entry, ensure_ascii=False),
                     now_lv()),
                )

    db.commit()
    db.close()

    families.sort(key=lambda x: x["total_eur"], reverse=True)
    print(f"[KNAB] Atrasti {len(families)} ģimeņu klasteri")
    return families


def detect_limit_violations(
    db_path: str = DB_PATH,
    limit_eur: float = ANNUAL_DONATION_LIMIT_EUR,
) -> list[dict]:
    """
    Find donors who exceeded annual donation limits per party.

    Returns list of {donor_name, party, year, total_eur, limit_eur, excess_eur}.
    """
    db = get_db(db_path)

    rows = db.execute("""
        SELECT donor_name, donor_pid_masked, party,
               SUBSTR(date, 1, 4) as year,
               SUM(amount_eur) as total
        FROM knab_donations
        WHERE currency = 'EUR'
        GROUP BY donor_name, donor_pid_masked, party, year
        HAVING total > ?
    """, (limit_eur,)).fetchall()

    violations = []
    for r in rows:
        entry = {
            "donor_name": r["donor_name"],
            "donor_pid": r["donor_pid_masked"],
            "party": r["party"],
            "year": r["year"],
            "total_eur": r["total"],
            "limit_eur": limit_eur,
            "excess_eur": r["total"] - limit_eur,
        }
        violations.append(entry)

        db.execute(
            """INSERT OR IGNORE INTO knab_alerts
               (alert_type, severity, party, title, description, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("limit_violation",
             "critical",
             r["party"],
             f"{r['donor_name']} pārsniedz limitu {r['year']}",
             f"EUR {r['total']:.2f} (limits: EUR {limit_eur:.2f}, pārsniegums: EUR {r['total'] - limit_eur:.2f})",
             json.dumps(entry, ensure_ascii=False),
             now_lv()),
        )

    db.commit()
    db.close()

    print(f"[KNAB] Atrasti {len(violations)} limita pārkāpumi")
    return violations


def detect_donation_declaration_mismatch(db_path: str = DB_PATH) -> list[dict]:
    """
    Compare sum of individual donations per party/year against
    declared donation income in annual reports.

    Returns list of mismatches with discrepancy amounts.
    """
    db = get_db(db_path)

    # Sum donations per party per year
    donation_sums = db.execute("""
        SELECT party, SUBSTR(date, 1, 4) as year, SUM(amount_eur) as donation_total
        FROM knab_donations
        WHERE currency = 'EUR'
        GROUP BY party, year
    """).fetchall()

    # Get declared income from declarations
    mismatches = []
    for ds in donation_sums:
        decl = db.execute("""
            SELECT income_donations, income_total
            FROM knab_declarations
            WHERE party = ? AND year = ? AND income_donations IS NOT NULL
        """, (ds["party"], int(ds["year"]))).fetchone()

        if decl and decl["income_donations"]:
            diff = abs(ds["donation_total"] - decl["income_donations"])
            pct = (diff / decl["income_donations"] * 100) if decl["income_donations"] > 0 else 0

            if pct > 10:  # Only flag >10% discrepancy
                entry = {
                    "party": ds["party"],
                    "year": ds["year"],
                    "knab_donations_sum": ds["donation_total"],
                    "declared_donations": decl["income_donations"],
                    "discrepancy_eur": diff,
                    "discrepancy_pct": round(pct, 1),
                }
                mismatches.append(entry)

                db.execute(
                    """INSERT OR IGNORE INTO knab_alerts
                       (alert_type, severity, party, title, description, data, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("declaration_mismatch",
                     "critical" if pct > 30 else "warning",
                     ds["party"],
                     f"{ds['party']} {ds['year']}: ziedojumu neatbilstība {pct:.0f}%",
                     f"KNAB ziedojumu summa: EUR {ds['donation_total']:.2f}, "
                     f"Deklarēts: EUR {decl['income_donations']:.2f}, "
                     f"Starpība: EUR {diff:.2f}",
                     json.dumps(entry, ensure_ascii=False),
                     now_lv()),
                )

    db.commit()
    db.close()

    print(f"[KNAB] Atrasti {len(mismatches)} neatbilstības starp ziedojumiem un deklarācijām")
    return mismatches


def run_all_checks(db_path: str = DB_PATH) -> dict:
    """Run all cross-reference checks. Returns summary."""
    print("[KNAB] Sāku visas pārbaudes...")

    linked = link_donors_to_politicians(db_path)
    multi = detect_multi_party_donors(db_path)
    families = detect_family_clusters(db_path)
    violations = detect_limit_violations(db_path)
    mismatches = detect_donation_declaration_mismatch(db_path)

    summary = {
        "donors_linked_to_politicians": linked,
        "multi_party_donors": len(multi),
        "family_clusters": len(families),
        "limit_violations": len(violations),
        "declaration_mismatches": len(mismatches),
    }

    print(f"\n[KNAB] Pārbaudes pabeigtas:")
    print(f"  Ziedotāji saistīti ar politiķiem: {linked}")
    print(f"  Ziedotāji vairākām partijām: {len(multi)}")
    print(f"  Ģimeņu klasteri: {len(families)}")
    print(f"  Limitu pārkāpumi: {len(violations)}")
    print(f"  Deklarāciju neatbilstības: {len(mismatches)}")

    return summary
```

- [ ] **Step 4: Run tests**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "~/atmina"
git add src/knab_analyze.py tests/test_knab.py
git commit -m "feat(knab): cross-referencing and anomaly detection engine"
```

---

## Task 7: Convenience Entry Points

**Files:**
- Modify: `src/knab.py`

- [ ] **Step 1: Add top-level orchestration functions**

Add to end of `src/knab.py`:

```python
def fetch_all(db_path: str = DB_PATH, delay: float = RATE_LIMIT_SECONDS) -> dict:
    """
    Full KNAB data refresh: donations + declarations.

    Usage:
        from src.knab import fetch_all
        fetch_all()
    """
    from src.db import init_db
    init_db(db_path)

    print("=" * 60)
    print("[KNAB] Sāku pilnu datu ielādi no info.knab.gov.lv")
    print("=" * 60)

    donations = fetch_all_donations(db_path=db_path, delay=delay)
    declarations = fetch_all_declarations(db_path=db_path, delay=delay)

    # Run cross-referencing
    from src.knab_analyze import run_all_checks
    checks = run_all_checks(db_path)

    summary = {
        "new_donations": donations,
        "new_declarations": declarations,
        **checks,
    }

    print("\n" + "=" * 60)
    print("[KNAB] Pabeigts!")
    print(f"  Jauni ziedojumi: {donations}")
    print(f"  Jaunas deklarācijas: {declarations}")
    print("=" * 60)

    return summary


def get_party_summary(party: str = None, db_path: str = DB_PATH) -> list[dict]:
    """
    Get donation summary per party (or for one party).

    Usage:
        from src.knab import get_party_summary
        get_party_summary()  # all parties
        get_party_summary("Jaunā VIENOTĪBA")  # one party
    """
    db = get_db(db_path)

    if party:
        rows = db.execute("""
            SELECT party,
                   COUNT(*) as donation_count,
                   SUM(amount_eur) as total_eur,
                   COUNT(DISTINCT donor_name) as unique_donors,
                   MIN(date) as first_donation,
                   MAX(date) as last_donation,
                   AVG(amount_eur) as avg_donation
            FROM knab_donations
            WHERE party = ?
            GROUP BY party
        """, (party,)).fetchall()
    else:
        rows = db.execute("""
            SELECT party,
                   COUNT(*) as donation_count,
                   SUM(amount_eur) as total_eur,
                   COUNT(DISTINCT donor_name) as unique_donors,
                   MIN(date) as first_donation,
                   MAX(date) as last_donation,
                   AVG(amount_eur) as avg_donation
            FROM knab_donations
            GROUP BY party
            ORDER BY total_eur DESC
        """).fetchall()

    result = [dict(r) for r in rows]
    db.close()
    return result


def get_top_donors(limit: int = 20, party: str = None, db_path: str = DB_PATH) -> list[dict]:
    """
    Get top donors by total amount.

    Usage:
        from src.knab import get_top_donors
        get_top_donors(10)  # top 10 overall
        get_top_donors(10, party="MMN")  # top 10 for MMN
    """
    db = get_db(db_path)

    if party:
        rows = db.execute("""
            SELECT donor_name, donor_pid_masked,
                   SUM(amount_eur) as total_eur,
                   COUNT(*) as donation_count,
                   GROUP_CONCAT(DISTINCT party) as parties
            FROM knab_donations
            WHERE party LIKE ?
            GROUP BY donor_name, donor_pid_masked
            ORDER BY total_eur DESC
            LIMIT ?
        """, (f"%{party}%", limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT donor_name, donor_pid_masked,
                   SUM(amount_eur) as total_eur,
                   COUNT(*) as donation_count,
                   GROUP_CONCAT(DISTINCT party) as parties
            FROM knab_donations
            GROUP BY donor_name, donor_pid_masked
            ORDER BY total_eur DESC
            LIMIT ?
        """, (limit,)).fetchall()

    result = [dict(r) for r in rows]
    db.close()
    return result


def get_alerts(alert_type: str = None, severity: str = None, db_path: str = DB_PATH) -> list[dict]:
    """
    Get anomaly alerts, optionally filtered.

    Usage:
        from src.knab import get_alerts
        get_alerts()  # all
        get_alerts(alert_type="limit_violation")
        get_alerts(severity="critical")
    """
    db = get_db(db_path)

    query = "SELECT * FROM knab_alerts WHERE 1=1"
    params = []
    if alert_type:
        query += " AND alert_type = ?"
        params.append(alert_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    query += " ORDER BY created_at DESC"

    rows = db.execute(query, params).fetchall()
    result = [dict(r) for r in rows]
    db.close()
    return result
```

- [ ] **Step 2: Run full test suite**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py -v`
Expected: PASS

- [ ] **Step 3: Verify module loads correctly**

Run: `cd "~/atmina" && python -c "from src.knab import fetch_all, get_party_summary, get_top_donors, get_alerts; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Commit**

```bash
cd "~/atmina"
git add src/knab.py
git commit -m "feat(knab): convenience entry points for querying and full refresh"
```

---

## Task 8: Integration Test — Small Live Fetch

**Files:**
- Modify: `tests/test_knab.py`

- [ ] **Step 1: Write integration test (marked slow)**

```python
# tests/test_knab.py (append)
import pytest
import tempfile

@pytest.mark.slow
def test_live_fetch_one_page():
    """Integration test: fetch one real page from KNAB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from src.db import init_db
        from src.knab import fetch_all_donations
        init_db(db_path)
        new = fetch_all_donations(db_path=db_path, max_pages=1)
        assert new > 0  # At least some donations on page 0

        from src.db import get_db
        db = get_db(db_path)
        count = db.execute("SELECT COUNT(*) FROM knab_donations").fetchone()[0]
        donor_count = db.execute("SELECT COUNT(*) FROM knab_donors").fetchone()[0]
        db.close()
        assert count > 0
        assert donor_count > 0
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run integration test**

Run: `cd "~/atmina" && python -m pytest tests/test_knab.py::test_live_fetch_one_page -v -m slow`
Expected: PASS (requires internet)

- [ ] **Step 3: Commit**

```bash
cd "~/atmina"
git add tests/test_knab.py
git commit -m "test(knab): integration test with live KNAB fetch"
```

---

## Task 9: Site Integration — Finanses Page

**Files:**
- Create: `templates/finanses.html.j2`
- Modify: `src/generate.py`

- [ ] **Step 1: Create the finanses template**

Create `templates/finanses.html.j2`:

```html
{% extends "base.html.j2" %}
{% block title %}Partiju finanses — atmina.lv{% endblock %}
{% block content %}
<section class="page-header">
    <h1>Partiju finanses</h1>
    <p class="subtitle">KNAB dati: ziedojumi, deklarācijas un anomālijas</p>
    <p class="meta">Atjaunots: {{ updated_at }} | Kopā: {{ total_donations }} ziedojumi, EUR {{ "%.2f"|format(total_eur) }}</p>
</section>

<section class="card">
    <h2>Partijas pēc ziedojumu apjoma</h2>
    <div class="table-responsive">
        <table class="data-table sortable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Partija</th>
                    <th>Ziedojumu skaits</th>
                    <th>Kopā (EUR)</th>
                    <th>Unikāli ziedotāji</th>
                    <th>Vid. ziedojums</th>
                    <th>Pirmais</th>
                    <th>Pēdējais</th>
                </tr>
            </thead>
            <tbody>
                {% for p in parties %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ p.party }}</td>
                    <td>{{ p.donation_count }}</td>
                    <td>{{ "%.2f"|format(p.total_eur) }}</td>
                    <td>{{ p.unique_donors }}</td>
                    <td>{{ "%.2f"|format(p.avg_donation) }}</td>
                    <td>{{ p.first_donation }}</td>
                    <td>{{ p.last_donation }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

<section class="card">
    <h2>TOP ziedotāji</h2>
    <div class="table-responsive">
        <table class="data-table sortable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Persona</th>
                    <th>Kopā (EUR)</th>
                    <th>Ziedojumu skaits</th>
                    <th>Partijas</th>
                </tr>
            </thead>
            <tbody>
                {% for d in top_donors %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ d.donor_name }}</td>
                    <td>{{ "%.2f"|format(d.total_eur) }}</td>
                    <td>{{ d.donation_count }}</td>
                    <td>{{ d.parties }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

{% if alerts %}
<section class="card">
    <h2>Anomālijas un brīdinājumi</h2>
    <div class="alerts-list">
        {% for a in alerts %}
        <div class="alert alert-{{ a.severity }}">
            <span class="alert-badge">{{ a.severity|upper }}</span>
            <strong>{{ a.title }}</strong>
            <p>{{ a.description }}</p>
        </div>
        {% endfor %}
    </div>
</section>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Add generator function to src/generate.py**

Add this function to `src/generate.py` and call it from `export_dashboard()`:

```python
def _generate_finanses_page(env, db, output_dir: str) -> None:
    """Generate the party finances page from KNAB data."""
    # Check if KNAB tables exist
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='knab_donations'"
    ).fetchall()]
    if not tables:
        logger.info("KNAB tables not found, skipping finanses page")
        return

    parties = [dict(r) for r in db.execute("""
        SELECT party,
               COUNT(*) as donation_count,
               SUM(amount_eur) as total_eur,
               COUNT(DISTINCT donor_name) as unique_donors,
               MIN(date) as first_donation,
               MAX(date) as last_donation,
               AVG(amount_eur) as avg_donation
        FROM knab_donations
        GROUP BY party
        ORDER BY total_eur DESC
    """).fetchall()]

    top_donors = [dict(r) for r in db.execute("""
        SELECT donor_name,
               SUM(amount_eur) as total_eur,
               COUNT(*) as donation_count,
               GROUP_CONCAT(DISTINCT party) as parties
        FROM knab_donations
        GROUP BY donor_name, donor_pid_masked
        ORDER BY total_eur DESC
        LIMIT 30
    """).fetchall()]

    alerts = [dict(r) for r in db.execute("""
        SELECT * FROM knab_alerts
        ORDER BY
            CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
            created_at DESC
        LIMIT 50
    """).fetchall()]

    total_donations = sum(p["donation_count"] for p in parties)
    total_eur = sum(p["total_eur"] for p in parties)

    template = env.get_template("finanses.html.j2")
    html = template.render(
        parties=parties,
        top_donors=top_donors,
        alerts=alerts,
        total_donations=total_donations,
        total_eur=total_eur,
        updated_at=datetime.now().strftime("%Y-%m-%d"),
        nav_active="finanses",
    )

    out_path = Path(output_dir) / "atmina" / "finanses.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info(f"Generated {out_path}")
```

- [ ] **Step 3: Add "Finanses" link to navigation in base.html.j2**

Add to the nav section in `templates/base.html.j2`:

```html
<a href="/atmina/finanses.html" class="nav-link{% if nav_active == 'finanses' %} active{% endif %}">Finanses</a>
```

- [ ] **Step 4: Test site generation still works**

Run: `cd "~/atmina" && python -c "from src.generate import export_dashboard; export_dashboard()"`
Expected: No errors (finanses page skipped if no KNAB data yet)

- [ ] **Step 5: Commit**

```bash
cd "~/atmina"
git add templates/finanses.html.j2 src/generate.py templates/base.html.j2
git commit -m "feat(knab): add Finanses page to atmina.lv site"
```

---

## Task 10: CLAUDE.md Update + Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add KNAB section to CLAUDE.md**

Append after the "Daily Routine" section:

```markdown
## KNAB Political Finance Data

KNAB scraper fetches donations and declarations from info.knab.gov.lv.

### Commands
```bash
# Full refresh (first run ~30 min, incremental ~5 min)
python -c "from src.knab import fetch_all; fetch_all()"

# Query helpers
python -c "from src.knab import get_party_summary; import json; print(json.dumps(get_party_summary(), indent=2, ensure_ascii=False))"
python -c "from src.knab import get_top_donors; import json; print(json.dumps(get_top_donors(10), indent=2, ensure_ascii=False))"
python -c "from src.knab import get_alerts; import json; print(json.dumps(get_alerts(severity='critical'), indent=2, ensure_ascii=False))"

# Run cross-reference checks only (no fetching)
python -c "from src.knab_analyze import run_all_checks; run_all_checks()"
```

### Tables
- `knab_donors` — unique persons (linked to tracked_politicians by name)
- `knab_donations` — all individual donations (~73K records)
- `knab_declarations` — annual reports for tracked parties
- `knab_alerts` — detected anomalies (multi-party donors, family clusters, limit violations)

### Alert Types
- `multi_party_donor` — person donates to 2+ parties
- `family_cluster` — same surname, same party, multiple donors
- `limit_violation` — annual per-party limit exceeded
- `declaration_mismatch` — KNAB donation sum vs declared income >10% discrepancy
```

- [ ] **Step 2: Commit**

```bash
cd "~/atmina"
git add CLAUDE.md
git commit -m "docs: add KNAB scraper documentation to CLAUDE.md"
```

---

## Execution Summary

| Task | What it does | Est. time |
|---|---|---|
| 1 | DB schema — 4 new tables | 5 min |
| 2 | Parse donation HTML | 10 min |
| 3 | Parse declaration HTML | 5 min |
| 4 | Paginated fetch engine | 10 min |
| 5 | Declaration fetcher with party filter | 5 min |
| 6 | Cross-referencing + anomaly detection | 15 min |
| 7 | Convenience query functions | 5 min |
| 8 | Live integration test | 5 min |
| 9 | Site template + generate.py | 10 min |
| 10 | CLAUDE.md docs | 3 min |

**First full scrape** will take ~30 minutes (147 pages * 2s delay). Subsequent runs are incremental (only new records).
