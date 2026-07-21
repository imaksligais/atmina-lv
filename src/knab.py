"""KNAB political finance fetch layer.

Fetches donation and declaration data from Latvia's anti-corruption
bureau (KNAB) at info.knab.gov.lv.

HISTORY: KNAB rebuilt info.knab.gov.lv as a JS SPA around 2026-07-23.
The old server-rendered HTML tables are gone (pages are now ~730-byte
shells), and data is served from a JSON API under ``/api``.  The live
fetch engine (``fetch_all_donations`` / ``fetch_all_declarations``) now
talks to that JSON API.  The HTML-parsing helpers (``parse_donations_page``,
``parse_declarations_page``, ``parse_declaration_detail``, ``_get_total_pages``,
``_build_url``, ``_fetch_page``) are LEGACY: kept for reference and their
unit tests until the operator decides to remove them.  They are no longer
reached by any live fetch.
"""

import json
import re
import time
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

from src.db import get_db, now_lv, log_action

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


# ---------------------------------------------------------------------------
# Paginated fetch engine
# ---------------------------------------------------------------------------


def _build_url(base: str, page: int = 0, per_page: int = 500, **filters) -> str:
    """Build paginated KNAB URL with query params."""
    params = {"page": page, "recordsPerPage": per_page}
    params.update(filters)
    return f"{base}?{urlencode(params)}"


def _fetch_page(url: str, client: httpx.Client) -> str:
    """Fetch one page with 3-retry logic and exponential backoff."""
    for attempt in range(3):
        try:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == 2:
                raise
            wait = 2 ** (attempt + 1)
            print(f"[KNAB] Error ({exc}), retrying in {wait}s...")
            time.sleep(wait)
    # Unreachable, but keeps type checker happy
    raise RuntimeError("_fetch_page: exhausted retries")


# ---------------------------------------------------------------------------
# JSON API client (2026-07 SPA rebuild)
# ---------------------------------------------------------------------------


def _fetch_json(url: str, client: httpx.Client) -> dict:
    """GET *url* and return parsed JSON, with the same 3-retry/backoff shape
    as ``_fetch_page``.
    """
    for attempt in range(3):
        try:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as exc:
            if attempt == 2:
                raise
            wait = 2 ** (attempt + 1)
            print(f"[KNAB] API error ({exc}), retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("_fetch_json: exhausted retries")


def _get_total_pages(html: str, per_page: int = 500) -> int:  # noqa: ARG001 - per_page accepted for API consistency; callers pass it, pagination extracted from HTML directly
    """Extract total page count from pagination.

    KNAB pagination uses 0-indexed page params in the last <li><a> before
    the "next" arrow.  The displayed text is 1-indexed (e.g. "1467" means
    page=1466).  We find the highest page number in the pagination links
    and add 1 to get the total page count.
    """
    soup = BeautifulSoup(html, "lxml")
    pagination = soup.find("ul", class_="pagination")
    if pagination is None:
        return 1

    max_page = 0
    for link in pagination.find_all("a"):
        href = link.get("href", "")
        qs = parse_qs(urlparse(href).query)
        if "page" in qs:
            try:
                p = int(qs["page"][0])
                # Exclude "next" arrow links — they point to page+1, not the last page
                # We only want the numbered page links
                if p > max_page:
                    max_page = p
            except ValueError:
                continue

    return max_page + 1  # 0-indexed → count


def _upsert_donor(db, name: str, pid_masked: str) -> int:
    """Get or create donor record in knab_donors, return donor_id."""
    row = db.execute(
        "SELECT id FROM knab_donors WHERE name = ? AND personal_id_masked = ?",
        (name, pid_masked),
    ).fetchone()
    if row:
        return row[0]

    db.execute(
        "INSERT INTO knab_donors (name, personal_id_masked) VALUES (?, ?)",
        (name, pid_masked),
    )
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def _legacy_donation_exists(db, d: dict) -> bool:
    """Return True if *d* is already in the DB under a LEGACY synthetic key.

    The pre-2026-07 HTML scrape stored ``knab_id`` as a synthetic
    ``{date}-{donor}-{amount}-{party}`` string, so the new API's ``public_id``
    key can never collide with it via INSERT OR IGNORE.  Without this guard a
    full API re-fetch would re-insert every one of the ~30k legacy donations.

    Only records dated on/before ``LEGACY_CUTOFF_DATE`` can possibly be legacy
    duplicates (the last legacy scrape ran 2026-04-08); anything newer is safe
    to insert directly.  Legacy donor names are stored mixed-case while the API
    returns UPPERCASE, so the name/party match is case-insensitive.

    Amount matches on EITHER of two signals: ``amount_eur`` within a cent, OR
    the ORIGINAL amount (pre-conversion) being equal with the same currency.
    The second signal is required for LVL-era rows: the legacy HTML scrape
    converted LVL->EUR with slightly different rounding than
    ``LVL_TO_EUR_RATE`` (20000 LVL -> 28457.60 legacy vs 28457.44 API), so any
    LVL donation over ~1400 LVL drifts past the cent tolerance — on the first
    API refresh (2026-07-24) that duplicated 1221 rows before this branch
    existed (cleanup: data/fix_knab_lvl_dupe_donations_2026-07-24.sql).
    """
    if d["date"] > LEGACY_CUTOFF_DATE:
        return False
    # Narrow with SQL on the date, then compare text fields in Python:
    # SQLite's built-in UPPER() folds ASCII only, so "Krištopans" vs
    # "KRIŠTOPANS" would not match at the SQL layer.
    rows = db.execute(
        """SELECT party, donor_name, amount_eur, currency, original_amount
           FROM knab_donations WHERE date = ?""",
        (d["date"],),
    ).fetchall()
    party_u = d["party"].upper()
    name_u = d["donor_name"].upper()
    orig = d.get("original_amount")
    for r in rows:
        if r["party"].upper() != party_u or r["donor_name"].upper() != name_u:
            continue
        if abs(r["amount_eur"] - d["amount_eur"]) < 0.01:
            return True
        if (
            orig is not None
            and (r["currency"] or "EUR") == d.get("currency", "EUR")
            and _parse_original_amount(r["original_amount"]) == round(float(orig), 2)
        ):
            return True
    return False


def _parse_original_amount(value) -> float | None:
    """Parse a stored ``original_amount`` into a rounded float.

    Legacy HTML-era rows stored display strings like ``'LVL 20000.00'``;
    API-era rows store plain floats.  Returns None when unparseable.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    m = re.search(r"-?[\d.]+", str(value).replace("\xa0", "").replace(" ", "").replace(",", "."))
    try:
        return round(float(m.group(0)), 2) if m else None
    except ValueError:
        return None


def _store_donations(db, donations: list[dict]) -> int:
    """Store list of parsed donations, upsert donors, INSERT OR IGNORE for dedup.

    Applies the legacy-cutoff dedup guard (``_legacy_donation_exists``) before
    each insert so a JSON-API re-fetch does not duplicate rows that the old
    HTML scrape already stored under synthetic keys.

    Returns count of new records.
    """
    total_new = 0
    for d in donations:
        if _legacy_donation_exists(db, d):
            continue
        donor_id = _upsert_donor(db, d["donor_name"], d.get("donor_pid_masked", ""))
        db.execute(
            """INSERT OR IGNORE INTO knab_donations
               (knab_id, donor_id, party, donation_type, amount_eur, currency,
                original_amount, donor_name, donor_pid_masked, date, detail_url, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                d["knab_id"],
                donor_id,
                d["party"],
                d["donation_type"],
                d["amount_eur"],
                d.get("currency", "EUR"),
                d.get("original_amount"),
                d["donor_name"],
                d.get("donor_pid_masked", ""),
                d["date"],
                d.get("detail_url", ""),
                now_lv(),
            ),
        )
        total_new += db.execute("SELECT changes()").fetchone()[0]
    db.commit()
    return total_new


def _fetch_all_parties(client: httpx.Client) -> list[dict]:
    """Fetch ALL parties from /api/parties, following pagination.

    The endpoint is paginated like every other list endpoint (default limit
    20, ~113 parties total) — reading only the first response silently
    dropped 16 of the 21 tracked parties on the first API-era refresh
    (2026-07-24: "5/20 tracked"). Request a large limit AND follow
    totalPages defensively in case the server caps the limit.
    """
    parties: list[dict] = []
    page = 1
    while True:
        data = _fetch_json(f"{API_BASE}/parties?page={page}&limit=500", client)
        parties.extend(data.get("parties", []))
        total_pages = data.get("pagination", {}).get("totalPages", page)
        if page >= total_pages:
            return parties
        page += 1


def _payment_to_donation(pay: dict) -> dict:
    """Map one ``/api/payments`` record to the ``_store_donations`` dict shape.

    ``amountDisplay`` is the display value in the record's own currency; for
    non-EUR (historical LVL) rows ``amount_eur`` is converted, while
    ``original_amount`` keeps the display value.  ``knab_id`` is the API's
    stable ``public_id``.
    """
    original = float(pay["amountDisplay"])
    currency = pay.get("currency", "EUR")
    if currency == "EUR":
        amount_eur = original
    else:
        # Only LVL is known to appear; convert at the fixed adoption rate.
        amount_eur = round(original / LVL_TO_EUR_RATE, 2)

    public_id = pay["public_id"]
    detail_url = f"{KNAB_BASE}/donations/show?public_id={public_id}"

    return {
        "knab_id": public_id,
        "party": pay["party"],
        "donation_type": pay.get("type", ""),
        "amount_eur": amount_eur,
        "currency": currency,
        "original_amount": original,
        "donor_name": pay.get("person", ""),
        "donor_pid_masked": pay.get("personCode", ""),
        "date": _parse_date_lv(pay["date"]),
        "detail_url": detail_url,
    }


def fetch_all_donations(
    db_path: str | None = None,
    per_page: int = 500,
    delay: float = RATE_LIMIT_SECONDS,
    max_pages: int = 0,
) -> int:
    """Main entry point: page through the KNAB JSON payments API per party.

    Fetches ``/api/parties``, keeps only tracked parties, then pages through
    ``/api/payments?party_public_id=...`` (1-indexed) for each.  ``max_pages``,
    when > 0, caps the TOTAL number of payment pages fetched across the whole
    run (its "quick test" purpose is preserved).  Logs action when done.
    Returns total count of newly inserted records.
    """
    db = get_db(db_path)

    headers = {"User-Agent": "atmina.lv political transparency research"}
    total_new = 0
    pages_fetched = 0

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        parties = _fetch_all_parties(client)
        tracked = [p for p in parties if _is_tracked_party(p.get("name", ""))]
        print(
            f"[KNAB] Donations: {len(tracked)}/{len(parties)} tracked parties, "
            f"limit {per_page}/page"
        )

        for party in tracked:
            pid = party["public_id"]
            page = 1
            while True:
                if max_pages > 0 and pages_fetched >= max_pages:
                    break
                if pages_fetched > 0 and delay > 0:
                    time.sleep(delay)

                url = (
                    f"{API_BASE}/payments?party_public_id={pid}"
                    f"&page={page}&limit={per_page}"
                )
                data = _fetch_json(url, client)
                pages_fetched += 1

                payments = data.get("payments", [])
                donations = [_payment_to_donation(p) for p in payments]
                total_new += _store_donations(db, donations)

                total_pages = data.get("pagination", {}).get("totalPages", page)
                if page >= total_pages or not payments:
                    break
                page += 1

            if max_pages > 0 and pages_fetched >= max_pages:
                break

    db.close()

    log_action(
        action="knab_fetch_donations",
        status="success",
        details={
            "pages": pages_fetched,
            "new_records": total_new,
            "per_page": per_page,
            "tracked_parties": len(tracked),
        },
        db_path=db_path,
    )

    print(f"[KNAB] Done: {total_new} new donations from {pages_fetched} pages")
    return total_new


# ---------------------------------------------------------------------------
# Declaration fetch engine
# ---------------------------------------------------------------------------


def _is_tracked_party(party_name: str) -> bool:
    """Check if *party_name* matches any entry in TRACKED_PARTIES.

    Uses case-insensitive comparison with both prefix and contains
    matching because KNAB party names can be longer than what we store
    (e.g. ``"APVIENOTAIS SARAKSTS"`` is a prefix of the full coalition
    name that includes partner parties).
    """
    party_lower = party_name.lower()
    for tracked in TRACKED_PARTIES:
        tracked_lower = tracked.lower()
        if tracked_lower in party_lower or party_lower.startswith(tracked_lower):
            return True
    return False


def _declaration_content_exists(db, d: dict) -> bool:
    """True if a declaration with the same ``(party, declaration_type, year)``
    already exists.  Legacy rows keep their old synthetic knab_id, so the API's
    ``public_id`` key would slip past INSERT OR IGNORE; this content-level guard
    is what actually deduplicates a re-fetch.  Party match is case-insensitive
    for the same reason as donations.
    """
    # Narrow on the exact-match fields in SQL; fold party case in Python
    # (SQLite UPPER() is ASCII-only, so diacritic party names would slip past).
    rows = db.execute(
        """SELECT party FROM knab_declarations
           WHERE declaration_type = ? AND year = ?""",
        (d["declaration_type"], d["year"]),
    ).fetchall()
    party_u = d["party"].upper()
    return any(r[0].upper() == party_u for r in rows)


def _store_declarations(db, declarations: list[dict]) -> int:
    """Store parsed declarations with content-level dedup on
    ``(party, declaration_type, year)``.

    Each dict may carry the financial detail fields (income_*/expenses_*/
    raw_data); when present they are written on INSERT so no separate detail
    pass is required.  Returns count of new records inserted.
    """
    total_new = 0
    for d in declarations:
        if _declaration_content_exists(db, d):
            continue
        db.execute(
            """INSERT OR IGNORE INTO knab_declarations
               (knab_id, party, declaration_type, year, date, detail_url,
                income_total, income_donations, income_membership,
                income_state_budget, expenses_total, expenses_advertising,
                expenses_salaries, raw_data, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                d["knab_id"],
                d["party"],
                d["declaration_type"],
                d["year"],
                d.get("date", ""),
                d.get("detail_url", ""),
                d.get("income_total"),
                d.get("income_donations"),
                d.get("income_membership"),
                d.get("income_state_budget"),
                d.get("expenses_total"),
                d.get("expenses_advertising"),
                d.get("expenses_salaries"),
                d.get("raw_data"),
                now_lv(),
            ),
        )
        total_new += db.execute("SELECT changes()").fetchone()[0]
    db.commit()
    return total_new


# SPA detail route + list-endpoint config per declaration source. Annual
# reports live in /api/reports (NOT /api/declarations); both share the row
# shape and detail endpoints.
_DECL_SOURCES = [
    # (list_endpoint, list_key, detail_endpoint, spa_show_route)
    ("declarations", "declarations", "declarations", "declarations/show"),
    ("reports", "reports", "reports", "annual-reports/show"),
]


def _record_to_declaration(rec: dict, spa_show_route: str) -> dict:
    """Map a ``/api/declarations`` or ``/api/reports`` list record to the base
    ``_store_declarations`` dict (financial fields filled in later from detail).
    """
    public_id = rec["public_id"]
    return {
        "knab_id": public_id,
        "party": rec["party"],
        "declaration_type": rec.get("type", ""),
        "year": rec.get("year", 0),
        "date": _parse_date_lv(rec["date"]) if rec.get("date") else "",
        "detail_url": f"{KNAB_BASE}/{spa_show_route}?public_id={public_id}",
    }


def fetch_all_declarations(
    db_path: str | None = None,
    per_page: int = 500,
    delay: float = RATE_LIMIT_SECONDS,
    max_pages: int = 0,
) -> int:
    """Page through both KNAB declaration JSON endpoints, storing only tracked
    parties with their full financial detail.

    Election declarations come from ``/api/declarations`` and annual reports
    from ``/api/reports``.  These endpoints have no server-side party filter, so
    tracked parties are selected client-side via ``_is_tracked_party``.  For
    each tracked record the detail endpoint is fetched and its ``rows`` mapped
    to income_*/expenses_*/raw_data (section-gated FIELD_MAP), then written on
    INSERT.  ``max_pages`` caps the TOTAL list pages fetched across BOTH
    endpoints.  Returns count of newly inserted records.
    """
    db = get_db(db_path)

    headers = {"User-Agent": "atmina.lv political transparency research"}
    total_new = 0
    total_seen = 0
    total_filtered = 0
    pages_fetched = 0

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for list_ep, list_key, detail_ep, spa_route in _DECL_SOURCES:
            page = 1
            while True:
                if max_pages > 0 and pages_fetched >= max_pages:
                    break
                if pages_fetched > 0 and delay > 0:
                    time.sleep(delay)

                url = f"{API_BASE}/{list_ep}?page={page}&limit={per_page}"
                data = _fetch_json(url, client)
                pages_fetched += 1

                records = data.get(list_key, [])
                total_seen += len(records)
                tracked_recs = [r for r in records if _is_tracked_party(r.get("party", ""))]
                total_filtered += len(records) - len(tracked_recs)

                for rec in tracked_recs:
                    d = _record_to_declaration(rec, spa_route)
                    # Skip the detail fetch when we already have this content.
                    if _declaration_content_exists(db, d):
                        continue
                    if delay > 0:
                        time.sleep(delay)
                    detail = _fetch_json(
                        f"{API_BASE}/{detail_ep}/{rec['public_id']}", client
                    )
                    # /api/declarations/{id} -> {"declaration": {...}},
                    # /api/reports/{id}      -> {"report": {...}}
                    obj = detail.get(detail_ep[:-1], {})
                    financials = _declaration_detail_from_rows(obj.get("rows", []))
                    d.update(financials)
                    total_new += _store_declarations(db, [d])

                total_pages = data.get("pagination", {}).get("totalPages", page)
                if page >= total_pages or not records:
                    break
                page += 1

            if max_pages > 0 and pages_fetched >= max_pages:
                break

    db.close()

    log_action(
        action="knab_fetch_declarations",
        status="success",
        details={
            "pages": pages_fetched,
            "new_records": total_new,
            "total_seen": total_seen,
            "filtered_out": total_filtered,
            "per_page": per_page,
        },
        db_path=db_path,
    )

    print(
        f"[KNAB] Done: {total_new} new declarations from {pages_fetched} pages "
        f"({total_filtered}/{total_seen} filtered)"
    )
    return total_new


# ---------------------------------------------------------------------------
# Declaration detail fetch engine
# ---------------------------------------------------------------------------


def fetch_declaration_details(
    db_path: str | None = None,
    delay: float = RATE_LIMIT_SECONDS,
    max_count: int = 0,
) -> int:
    """Fetch detail pages for declarations missing financial data.

    LEGACY: superseded by the JSON-API ``fetch_all_declarations``, which now
    writes income_*/expenses_*/raw_data inline on INSERT.  This function still
    targets the old server-rendered HTML detail pages via ``parse_declaration_detail``
    and ``_fetch_page``; against the current SPA those URLs return empty shells.
    Kept for reference / historical backfill of any legacy NULL rows only.

    Queries all rows with NULL income_total and a non-empty detail_url,
    fetches each detail page, parses financials, and UPDATEs the row.

    If *max_count* > 0, stop after that many (useful for testing).
    Returns count of successfully updated declarations.
    """

    db = get_db(db_path)
    rows = db.execute(
        "SELECT id, detail_url FROM knab_declarations "
        "WHERE income_total IS NULL AND detail_url != ''"
    ).fetchall()

    if not rows:
        print("[KNAB] No declarations need detail fetching.")
        db.close()
        return 0

    total = len(rows)
    if max_count > 0:
        rows = rows[:max_count]
        total = len(rows)

    print(f"[KNAB] Fetching details for {total} declarations...")

    headers = {"User-Agent": "atmina.lv political transparency research"}
    updated = 0

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for i, row in enumerate(rows):
            decl_id = row[0]
            url = row[1]

            try:
                html = _fetch_page(url, client)
                data = parse_declaration_detail(html)

                db.execute(
                    """UPDATE knab_declarations SET
                       income_total = ?,
                       income_donations = ?,
                       income_membership = ?,
                       income_state_budget = ?,
                       expenses_total = ?,
                       expenses_advertising = ?,
                       expenses_salaries = ?,
                       raw_data = ?
                    WHERE id = ?""",
                    (
                        data.get("income_total"),
                        data.get("income_donations"),
                        data.get("income_membership"),
                        data.get("income_state_budget"),
                        data.get("expenses_total"),
                        data.get("expenses_advertising"),
                        data.get("expenses_salaries"),
                        data.get("raw_data", "{}"),
                        decl_id,
                    ),
                )
                db.commit()
                updated += 1

            except Exception as exc:
                print(f"[KNAB] Error fetching detail id={decl_id}: {exc}")

            if (i + 1) % 20 == 0:
                print(f"[KNAB] Detail progress: {i + 1}/{total}, {updated} updated")

            if delay > 0 and i < len(rows) - 1:
                time.sleep(delay)

    db.close()

    log_action(
        action="knab_fetch_declaration_details",
        status="success",
        details={"total_queued": total, "updated": updated},
        db_path=db_path,
    )

    print(f"[KNAB] Done: {updated}/{total} declaration details fetched")
    return updated


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------


def fetch_all(db_path: str | None = None, delay: float = RATE_LIMIT_SECONDS) -> dict:
    """Full KNAB refresh: init DB, fetch donations + declarations, run checks.

    Prints a banner summarising results.  Returns a summary dict.
    """
    from src.db import init_db
    from src.knab_analyze import run_all_checks

    init_db(db_path)
    new_donations = fetch_all_donations(db_path=db_path, delay=delay)
    new_declarations = fetch_all_declarations(db_path=db_path, delay=delay)
    checks = run_all_checks(db_path)

    summary = {
        "new_donations": new_donations,
        "new_declarations": new_declarations,
        "checks": checks,
    }

    print("=" * 60)
    print("[KNAB] Full update complete")
    print(f"  New donations:      {new_donations}")
    print(f"  New declarations:   {new_declarations}")
    print(f"  Checks:             {checks}")
    print("=" * 60)

    return summary


def get_party_summary(party: str | None = None, db_path: str | None = None) -> list[dict]:
    """Query donation summary per party.

    If *party* is given, filter to that party only.
    Returns list of dicts with: party, donation_count, total_eur,
    unique_donors, first_donation, last_donation, avg_donation.
    Ordered by total_eur DESC.
    """
    db = get_db(db_path)
    sql = """
        SELECT
            party,
            COUNT(*)          AS donation_count,
            SUM(amount_eur)   AS total_eur,
            COUNT(DISTINCT donor_name) AS unique_donors,
            MIN(date)         AS first_donation,
            MAX(date)         AS last_donation,
            ROUND(AVG(amount_eur), 2) AS avg_donation
        FROM knab_donations
    """
    params: list = []
    if party:
        sql += " WHERE party = ? "
        params.append(party)
    sql += " GROUP BY party ORDER BY total_eur DESC"

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_top_donors(
    limit: int = 20,
    party: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Top donors by total amount, optionally filtered by party (LIKE %party%).

    Returns list of dicts with: donor_name, donor_pid_masked, total_eur,
    donation_count, parties (GROUP_CONCAT DISTINCT).
    """
    db = get_db(db_path)
    sql = """
        SELECT
            donor_name,
            donor_pid_masked,
            SUM(amount_eur)   AS total_eur,
            COUNT(*)          AS donation_count,
            GROUP_CONCAT(DISTINCT party) AS parties
        FROM knab_donations
    """
    params: list = []
    if party:
        sql += " WHERE party LIKE ? "
        params.append(f"%{party}%")
    sql += " GROUP BY donor_name, donor_pid_masked ORDER BY total_eur DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_alerts(
    alert_type: str | None = None,
    severity: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Query knab_alerts with optional filters.

    Returns list of dicts ordered by created_at DESC.
    """
    db = get_db(db_path)
    clauses: list[str] = []
    params: list = []
    if alert_type:
        clauses.append("alert_type = ?")
        params.append(alert_type)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)

    sql = "SELECT * FROM knab_alerts"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(r) for r in rows]
