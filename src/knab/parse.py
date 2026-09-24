"""KNAB konstantes un tīrie parseri (bez tīkla, bez DB).

Šeit dzīvo `src/knab/` pakotnes datu slānis: bāzes URL, izsekojamo partiju
saraksts, valūtas konstantes un HTML/JSON parsēšanas palīgi.  Neviena funkcija
šajā modulī neatver savienojumu un neraksta datubāzē — tāpēc to var importēt
gan `ingest.py`, gan testi bez blakusefektiem.

VĒSTURE: HTML parseri (``parse_donations_page``, ``parse_declarations_page``,
``parse_declaration_detail``) ir LEGACY — KNAB 2026-07-23 pārbūvēja
info.knab.gov.lv par JS SPA, un dzīvā ielāde tagad iet caur JSON API
(sk. ``src/knab/ingest.py``).  Parseri paliek atsaucei un to vienībtestiem.
"""

import json
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNAB_BASE = "https://info.knab.gov.lv"
# Legacy server-rendered HTML endpoints (dead since the 2026-07 SPA rebuild;
# kept only so the legacy parsers/tests still reference the same base).
DONATIONS_URL = f"{KNAB_BASE}/lv/db/ziedojumi/"
DECLARATIONS_URL = f"{KNAB_BASE}/lv/db/deklaracijas/"

# New JSON API (2026-07 rebuild). Pages are 1-INDEXED (page=0 behaves as 1).
API_BASE = f"{KNAB_BASE}/api"

RATE_LIMIT_SECONDS = 2

# LVL->EUR fixed conversion (Latvia adopted the euro 2014-01-01 at this rate).
# Historical KNAB rows may still carry currency == "LVL".
LVL_TO_EUR_RATE = 0.702804

# Last date covered by the legacy HTML-scrape backfill (last scraped_at was
# 2026-04-08).  API records dated on/before this MAY already be in the DB under
# a legacy synthetic knab_id -- see LEGACY_CUTOFF_DATE dedup guard below.
LEGACY_CUTOFF_DATE = "2026-04-08"

TRACKED_PARTIES = [
    # Tier 1: Currently in Saeima
    "Jaunā VIENOTĪBA",
    "Partija \"VIENOTĪBA\"",           # JV old name (pre-rebrand)
    "Nacionālā apvienība \"Visu Latvijai!\"-\"Tēvzemei un Brīvībai/LNNK\"",
    "\"PROGRESĪVIE\"",
    "Zaļo un Zemnieku savienība",
    "\"APVIENOTAIS SARAKSTS",
    "LATVIJA PIRMAJĀ VIETĀ",
    # Tier 2: Running in 2026
    "\"Mēs mainām noteikumus\"",
    "\"Stabilitātei!\"",
    "Austošā Saule Latvijai",           # ASL, atmina-tracked since 2026
    "SUVERĒNĀ VARA",                    # SV/AJ joint list (atmina party id=19)
    "APVIENĪBA JAUNLATVIEŠI",           # SV/AJ component, also standalone in KNAB
    "\"SARAUJ, LATGALE!\"",             # in the 2026-04 Deklare2 verified set; was missing here
    "\"Latvijas attīstībai\"",
    "PLI",                              # LA + Par! + Izaugsme alliance
    "Politisko partiju apvienība \"Saskaņas Centrs\"",
    "\"Saskaņa\" sociāldemokrātiskā partija",
    "\"Centra Partija\"",              # Saskaņas Centra component
    "\"Platforma 21\"",                # ex-Gobzems, active
    # Tier 3: Active / significant donors
    "Latvijas Zaļā partija",
    "\"LATVIJAS ZEMNIEKU SAVIENĪBA\"",
    "Latvijas Reģionu apvienība",
    "\"Gods kalpot Rīgai\"",
    "JKP Jaunā konservatīvā partija",
    "Kustība \"Par!\"",
    "Latvijas Sociāldemokrātiskā strādnieku partija",
]

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_amount(text: str) -> tuple[float, str]:
    """Parse 'EUR 200.00' or 'LVL 50.00' into (amount, currency).

    Returns (amount_float, currency_code).
    """
    text = text.strip()
    match = re.match(r"([A-Z]{3})\s+(-?[\d\s,.]+)", text)
    if not match:
        raise ValueError(f"Cannot parse amount: {text!r}")
    currency = match.group(1)
    # Normalise: remove spaces, replace comma with dot
    amount_str = match.group(2).replace(" ", "").replace(",", ".")
    return float(amount_str), currency


def _parse_date_lv(text: str) -> str:
    """Convert 'dd.mm.yyyy' to 'yyyy-mm-dd' for SQLite sorting."""
    text = text.strip()
    match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not match:
        raise ValueError(f"Cannot parse date: {text!r}")
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def _extract_donor_pid(text: str) -> tuple[str, str]:
    """Split 'Jānis Bērziņš120680*****' or 'Jānis Bērziņš\\n120680*****'
    into (name, pid_masked).

    The KNAB HTML uses a <br> tag between name and PID, which BS4
    .get_text(separator="\\n") converts to a newline.
    """
    # Try newline separator first (from BS4 get_text)
    parts = text.strip().split("\n")
    if len(parts) >= 2:
        name = parts[0].strip()
        pid = parts[-1].strip()
        return name, pid

    # Fallback: PID pattern directly after name (no separator)
    match = re.search(r"(\d{6}\*{5})$", text.strip())
    if match:
        pid = match.group(1)
        name = text[: match.start()].strip()
        return name, pid

    # No PID found — return entire text as name
    return text.strip(), ""


def parse_donations_page(html: str) -> list[dict]:
    """Parse a KNAB donations list page into structured dicts.

    Expects the HTML from info.knab.gov.lv/lv/db/ziedojumi/ which
    contains a <table id="donations"> with columns:
      Partija | Veids | Vērtība | Persona | Datums
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="donations")
    if table is None:
        return []

    tbody = table.find("tbody")
    if tbody is None:
        return []

    donations: list[dict] = []
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # --- Party + detail link ---
        party_cell = cells[0]
        party_link = party_cell.find("a")
        party = party_link.get_text(strip=True) if party_link else party_cell.get_text(strip=True)

        # Extract knab_id from href like "?id=31032026-33652683"
        knab_id = ""
        detail_url = ""
        if party_link and party_link.get("href"):
            href = party_link["href"]
            qs = parse_qs(urlparse(href).query)
            if "id" in qs:
                knab_id = qs["id"][0]
            # Build full detail URL
            detail_url = f"{DONATIONS_URL}{href}" if href.startswith("?") else href

        # --- Donation type ---
        donation_type = cells[1].get_text(strip=True)

        # --- Amount ---
        amount_text = cells[2].get_text(strip=True)
        amount_eur, currency = _parse_amount(amount_text)

        # --- Person ---
        person_text = cells[3].get_text(separator="\n", strip=True)
        donor_name, donor_pid_masked = _extract_donor_pid(person_text)

        # --- Date ---
        date_text = cells[4].get_text(strip=True)
        date_iso = _parse_date_lv(date_text)

        # If currency is not EUR, store original but keep amount_eur
        # as the value (caller can convert later if needed).
        original_amount = amount_eur

        donations.append({
            "knab_id": knab_id,
            "party": party,
            "donation_type": donation_type,
            "amount_eur": amount_eur,
            "currency": currency,
            "original_amount": original_amount,
            "donor_name": donor_name,
            "donor_pid_masked": donor_pid_masked,
            "date": date_iso,
            "detail_url": detail_url,
        })

    return donations


def parse_declarations_page(html: str) -> list[dict]:
    """Parse a KNAB declarations list page into structured dicts.

    Expects the HTML from info.knab.gov.lv/lv/db/deklaracijas/ which
    contains a <table id="declarations"> with columns:
      Partija | Veids | Gads | Datums
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="declarations")
    if table is None:
        return []

    tbody = table.find("tbody")
    if tbody is None:
        return []

    declarations: list[dict] = []
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # --- Party + detail link ---
        party_cell = cells[0]
        party_link = party_cell.find("a")
        party = party_link.get_text(strip=True) if party_link else party_cell.get_text(strip=True)

        # Extract knab_id from href like "?id=24032026-91540490&type=1"
        knab_id = ""
        detail_url = ""
        if party_link and party_link.get("href"):
            href = party_link["href"]
            qs = parse_qs(urlparse(href).query)
            if "id" in qs:
                knab_id = qs["id"][0]
            # Build full detail URL
            detail_url = f"{DECLARATIONS_URL}{href}" if href.startswith("?") else href

        # --- Declaration type ---
        declaration_type = cells[1].get_text(strip=True)

        # --- Year ---
        year_text = cells[2].get_text(strip=True)
        try:
            year = int(year_text)
        except ValueError:
            year = 0

        # --- Date ---
        date_text = cells[3].get_text(strip=True)
        date_iso = _parse_date_lv(date_text)

        declarations.append({
            "knab_id": knab_id,
            "party": party,
            "declaration_type": declaration_type,
            "year": year,
            "date": date_iso,
            "detail_url": detail_url,
        })

    return declarations


# ---------------------------------------------------------------------------
# Declaration detail parsing
# ---------------------------------------------------------------------------

FIELD_MAP = {
    "i. biedru nauda": "income_membership",
    "ii. saņemtie dāvinājumi": "income_donations",
    "v. valsts budžeta": "income_state_budget",
    "vii. ieņēmumi kopā": "income_total",
    "5. reklāmas": "expenses_advertising",
    "7. darba algas": "expenses_salaries",
    "x. izdevumi kopā": "expenses_total",
}


def _parse_euro(text: str) -> float:
    """Parse euro value like '€ 291937.00' or '€ -127.00' into float."""
    text = text.strip()
    text = text.replace("\u20ac", "").replace("\xa0", "").strip()
    if not text or text == "-":
        return 0.0
    return float(text.replace(" ", "").replace(",", "."))


def parse_declaration_detail(html: str) -> dict:
    """Parse a KNAB declaration detail page into financial fields.

    Returns a dict with target financial fields plus raw_data (JSON string
    of all label-value pairs found in the table).
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="declaration")
    if table is None:
        table = soup.find("table")
    if table is None:
        return {"raw_data": "{}"}

    raw: dict[str, float] = {}
    result: dict[str, float | str | None] = {
        "income_total": None,
        "income_donations": None,
        "income_membership": None,
        "income_state_budget": None,
        "expenses_total": None,
        "expenses_advertising": None,
        "expenses_salaries": None,
    }

    in_income_expenses = False

    for row in table.find_all("tr"):
        ths = row.find_all("th")
        tds = row.find_all("td")

        # Section header detection
        if ths:
            header_text = ths[0].get_text(strip=True).lower()
            in_income_expenses = "ieņēmumu un izdevumu" in header_text
            continue

        # Sub-header row (single td with colspan or only 1 td)
        if len(tds) == 1:
            continue
        if len(tds) >= 2 and tds[0].get("colspan"):
            continue

        if len(tds) >= 2:
            label = tds[0].get_text(strip=True)
            value_text = tds[1].get_text(strip=True)

            # Only parse rows that look like euro values
            if "\u20ac" in value_text or value_text.strip() in ("-", ""):
                try:
                    value = _parse_euro(value_text)
                except (ValueError, TypeError):
                    continue

                raw[label] = value

                # Match to target fields (only in the income/expenses section)
                if in_income_expenses:
                    label_lower = label.lower().lstrip("*").strip()
                    for prefix, field in FIELD_MAP.items():
                        if label_lower.startswith(prefix):
                            result[field] = value
                            break

    result["raw_data"] = json.dumps(raw, ensure_ascii=False)
    return result


def _declaration_detail_from_rows(rows: list[dict]) -> dict:
    """JSON-API analogue of ``parse_declaration_detail``.

    ``rows`` are the label/amount pairs from ``/api/declarations/{id}`` or
    ``/api/reports/{id}`` (amount format ``"€ 374.00"``, empty on section
    rows).  Mirrors the legacy parser's section-gating: FIELD_MAP is applied
    ONLY inside the annual-report income/expenses section
    ("Ieņēmumu un izdevumu pārskats"), because the cash-flow section
    ("Naudas plūsmas pārskats") repeats colliding labels such as
    "5. Reklāmas pakalpojumi" that would otherwise clobber
    ``expenses_advertising``.  Election-declaration layouts
    ("I. Ieņēmumi"/"II. Izdevumi", "IEŅĒMUMI KOPĀ (1+2+3)") match no FIELD_MAP
    prefix, so those fields stay None -- matching legacy behaviour.

    Returns the same dict shape as ``parse_declaration_detail`` (financial
    fields defaulting to None + raw_data JSON of every euro row).
    """
    raw: dict[str, float] = {}
    result: dict[str, float | str | None] = {
        "income_total": None,
        "income_donations": None,
        "income_membership": None,
        "income_state_budget": None,
        "expenses_total": None,
        "expenses_advertising": None,
        "expenses_salaries": None,
    }

    in_income_expenses = False

    for row in rows:
        label = (row.get("label") or "").strip()
        amount_text = row.get("amount") or ""

        # Section header rows carry an empty amount + section flag; use them to
        # gate FIELD_MAP the way the old parser gated on <th> headers.
        if row.get("section"):
            in_income_expenses = "ieņēmumu un izdevumu" in label.lower()
            continue

        # Skip pure sub-section / non-value rows (empty amount, e.g. subsection
        # headers or file links).
        if "€" not in amount_text:
            continue

        try:
            value = _parse_euro(amount_text)
        except (ValueError, TypeError):
            continue

        raw[label] = value

        if in_income_expenses:
            label_lower = label.lower().lstrip("*").strip()
            for prefix, field in FIELD_MAP.items():
                if label_lower.startswith(prefix):
                    result[field] = value
                    break

    # KNAB's SPA serves an all-zero TEMPLATE for declarations it has no
    # detail data for (everything pre-2019, verified 2026-07-24: JV 2018
    # annual report = 76 rows, all "€ 0.00"). Storing those zeros as real
    # values made the mismatch detector read "declared: 0.00" and raise 15
    # false criticals — treat an all-zero form as no-data: financial fields
    # stay None (mismatch check filters on IS NOT NULL), raw_data keeps the
    # zeros for audit.
    if raw and all(v == 0 for v in raw.values()):
        for field in list(result):
            result[field] = None

    result["raw_data"] = json.dumps(raw, ensure_ascii=False)
    return result
