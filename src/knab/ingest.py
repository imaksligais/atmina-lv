"""KNAB politiskā finansējuma ielādes slānis (tīkls + glabāšana).

Ielādē ziedojumus un deklarācijas no info.knab.gov.lv JSON API un glabā tos
`knab_*` tabulās caur dedup kāpnēm.  Konstantes un tīrie parseri dzīvo
``src/knab/parse.py``; lasīšanas puses vaicājumi — ``src/knab/queries.py``.

VĒSTURE: KNAB 2026-07-23 pārbūvēja info.knab.gov.lv par JS SPA.  Vecās
servera renderētās HTML tabulas ir pazudušas (lapas tagad ir ~730 baitu
čaulas), un dati nāk no JSON API zem ``/api``.  Dzīvais ielādes dzinējs
(``fetch_all_donations`` / ``fetch_all_declarations``) runā ar to API.
HTML parsēšanas palīgi ``parse.py`` ir LEGACY un vairs netiek sasniegti.
"""

import re
import sys
import time
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

from src.db import get_db, log_action, now_lv
from src.knab.parse import (
    API_BASE,
    KNAB_BASE,
    LEGACY_CUTOFF_DATE,
    LVL_TO_EUR_RATE,
    RATE_LIMIT_SECONDS,
    TRACKED_PARTIES,
    _declaration_detail_from_rows,
    _parse_date_lv,
    parse_declaration_detail,
)

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


def _donation_content_key(
    party: str, donor_code: str, donor_name: str, date: str, amount_eur
) -> tuple:
    """Stable content identity for a donation.

    Returns ``(normalized party, donor code, date, signed amount in whole
    cents)``.  ``donor_code`` is ``donor_pid_masked`` (person code or reg.
    no.); when it is empty, the normalized donor name stands in so code-less
    rows do not collapse across different donors.  Party/name are folded to
    upper case in Python (Unicode-aware, unlike SQLite's ASCII-only UPPER) so
    legacy mixed-case and API UPPERCASE rows match; the signed amount is
    compared in whole cents to dodge float representation noise.
    """
    party_norm = " ".join((party or "").upper().split())
    code = (donor_code or "").strip()
    if not code:
        code = " ".join((donor_name or "").upper().split())
    amount_cents = int(round(float(amount_eur) * 100))
    return (party_norm, code, date, amount_cents)


def _content_rows_by_key(db, key: tuple) -> list:
    """Stored post-cutoff ``knab_donations`` rows whose content identity == *key*.

    The ``date > LEGACY_CUTOFF_DATE`` filter keeps legacy synthetic-key rows out
    of reconciliation: those are only ever deduplicated via
    ``_legacy_donation_exists``, never re-keyed or deleted.
    """
    rows = db.execute(
        "SELECT id, knab_id, party, donor_name, donor_pid_masked, date, amount_eur "
        "FROM knab_donations WHERE date = ? AND date > ?",
        (key[2], LEGACY_CUTOFF_DATE),
    ).fetchall()
    return [
        r for r in rows
        if _donation_content_key(
            r["party"], r["donor_pid_masked"], r["donor_name"],
            r["date"], r["amount_eur"],
        ) == key
    ]


def _refresh_mutable_fields(db, row_id: int, d: dict) -> None:
    """Adopt the mutable source fields of *d* onto an existing donation row.

    ``knab_id`` and ``donation_type`` are the fields KNAB is known to mutate
    (re-keying a record, or reclassifying its type); ``detail_url`` is derived
    from ``knab_id`` and refreshed alongside.  Content-identity fields (party,
    donor, date, amount) are intentionally left alone: had they changed, the
    row would not have matched on content identity in the first place.
    """
    db.execute(
        "UPDATE knab_donations SET knab_id = ?, donation_type = ?, detail_url = ? WHERE id = ?",
        (d["knab_id"], d["donation_type"], d.get("detail_url", ""), row_id),
    )


def _content_key_of(d: dict) -> tuple:
    """Content-identity key of an incoming donation dict."""
    return _donation_content_key(
        d["party"], d.get("donor_pid_masked", ""), d["donor_name"],
        d["date"], d["amount_eur"],
    )


def _row_content_matches(row, d: dict) -> bool:
    """True if stored *row* has the same content identity as incoming *d*."""
    return (
        _donation_content_key(
            row["party"], row["donor_pid_masked"], row["donor_name"],
            row["date"], row["amount_eur"],
        )
        == _content_key_of(d)
    )


def _warn_skipped(reason: str, d: dict) -> None:
    """Report a record ``_store_donations`` deliberately did not store."""
    print(
        f"[KNAB] skip donation ({reason}): party={d.get('party')!r} "
        f"knab_id={d.get('knab_id')!r} date={d.get('date')!r} "
        f"amount={d.get('amount_eur')!r}",
        file=sys.stderr,
    )


def _insert_donation(db, d: dict) -> int:
    """Insert *d* as a brand-new donation row; returns 1 if inserted, else 0."""
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
    return db.execute("SELECT changes()").fetchone()[0]


def _warn_deleted(row) -> None:
    """Report a stale same-content row the reconciliation deleted."""
    print(
        f"[KNAB] delete stale donation (id {row['id']}, knab_id={row['knab_id']!r}, "
        f"date={row['date']!r}, amount={row['amount_eur']!r}): superseded by the "
        f"complete incoming set",
        file=sys.stderr,
    )


def _store_donations(db, donations: list[dict], complete: bool = True) -> int:
    """Store parsed donations with authoritative multiset reconciliation.

    KNAB's ``public_id`` (stored as ``knab_id``) and ``donation_type`` are
    MUTABLE: KNAB re-keys a record (new ``public_id``) when it reclassifies it,
    so a plain ``INSERT OR IGNORE`` on ``knab_id`` duplicates a re-keyed row
    (the LATVIJA PIRMĀ 2026-08-14 case: four re-keyed rows + three type changes
    would have fabricated +330654.32 net).

    Per incoming record, in order:

      1. falsy ``knab_id`` -> skip (a record with no stable id must never
         re-key or null a stored row's identity);
      2. same ``knab_id`` stored and content identity matches -> refresh
         mutable fields in place (non-destructive: the id is unchanged);
      3. same ``knab_id`` stored but content identity DIFFERS -> skip and warn
         (KNAB re-using a public_id for different content is an anomaly, never
         a licence to mutate the wrong row);
      4. legacy-cutoff content guard -> skip (pre-2026-04-08 rows already
         stored under synthetic keys);
      5. otherwise the record is a *candidate* (a new id).

    Then, grouped by content key ``(normalized party, donor code, date, signed
    amount in whole cents)``:

    * **complete=True** — the incoming set is authoritative.  For each content
      key the stored post-cutoff rows are split into *live* (id still present
      in this batch, already refreshed) and *dead* (id gone upstream).  The
      candidate ids pair deterministically 1:1 with the dead rows (ascending
      row id), re-keying them in place; excess candidates insert; excess dead
      rows are deleted.  The result is exactly the complete incoming id
      multiset, so genuine duplicates are preserved and stale duplicates —
      including ones a previous partial batch left behind — converge away.

    * **complete=False** — fail safe.  No re-key and no delete ever run on
      incomplete data.  An *ambiguous* candidate (its content already matches a
      stored row — it may be a re-key whose old id sits on an unfetched page, or
      a genuine duplicate) is skipped and deferred to a later complete batch; a
      genuinely new candidate (content matches nothing) still inserts, so
      partial runs keep making progress.

    Reconciliation only touches post-cutoff rows (``date > LEGACY_CUTOFF_DATE``):
    legacy synthetic-key rows are never re-keyed or deleted, only deduplicated
    via the legacy guard above.

    Returns the count of newly inserted records (re-keys, refreshes and
    deletions are not counted).
    """
    if not donations:
        return 0

    live_ids = {d["knab_id"] for d in donations if d.get("knab_id")}

    # --- Read-only classification pass --------------------------------------
    # Classify every record against the DB BEFORE any mutation so the live/dead
    # split is planned against a stable state.
    refreshes = []     # (row_id, d): same knab_id + matching content
    cand_by_key = {}   # content key -> [candidate dicts in incoming order]
    incoming_keys = set()  # content keys of records counted in the multiset
    seen_ids = {}      # knab_id -> content key of first occurrence this batch

    for d in donations:
        knab_id = d.get("knab_id")
        if not knab_id:
            _warn_skipped("missing public_id", d)
            continue

        key = _content_key_of(d)
        if knab_id in seen_ids:
            if seen_ids[knab_id] != key:
                _warn_skipped("public_id reused with different content", d)
            continue
        seen_ids[knab_id] = key

        existing = db.execute(
            "SELECT id, party, donor_name, donor_pid_masked, date, amount_eur "
            "FROM knab_donations WHERE knab_id = ?",
            (knab_id,),
        ).fetchone()
        if existing:
            if _row_content_matches(existing, d):
                refreshes.append((existing["id"], d))
                incoming_keys.add(key)
            else:
                _warn_skipped("public_id content collision", d)
            continue

        if _legacy_donation_exists(db, d):
            continue

        cand_by_key.setdefault(key, []).append(d)
        incoming_keys.add(key)

    # --- Apply refreshes (same-id; always safe) -----------------------------
    for row_id, d in refreshes:
        _refresh_mutable_fields(db, row_id, d)

    # --- Reconcile candidates ----------------------------------------------
    total_new = 0
    if complete:
        for key in incoming_keys:
            dead = sorted(
                (r for r in _content_rows_by_key(db, key)
                 if r["knab_id"] not in live_ids),
                key=lambda r: r["id"],
            )
            cands = cand_by_key.get(key, [])
            n = min(len(cands), len(dead))
            for i in range(n):
                _refresh_mutable_fields(db, dead[i]["id"], cands[i])
            for d in cands[n:]:
                total_new += _insert_donation(db, d)
            for r in dead[n:]:
                db.execute("DELETE FROM knab_donations WHERE id = ?", (r["id"],))
                _warn_deleted(r)
    else:
        for key, cands in cand_by_key.items():
            if _content_rows_by_key(db, key):
                for d in cands:
                    _warn_skipped("ambiguous candidate on partial batch", d)
            else:
                for d in cands:
                    total_new += _insert_donation(db, d)

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
            party_donations: list[dict] = []
            complete = True
            while True:
                if max_pages > 0 and pages_fetched >= max_pages:
                    complete = False
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
                party_donations.extend(_payment_to_donation(p) for p in payments)

                total_pages = data.get("pagination", {}).get("totalPages", page)
                if page >= total_pages:
                    # Fail-closed completeness check: a FULL final page means the
                    # server may have capped `limit` below `per_page` while
                    # reporting totalPages for the requested size, silently
                    # truncating the set.  Treat as incomplete so the destructive
                    # re-key/delete never runs against a truncated batch.
                    if len(payments) == per_page:
                        complete = False
                    break
                if not payments:
                    # An empty page while totalPages still claims more is a
                    # transient API response; the batch is incomplete, so the
                    # content re-key step must not run against it.
                    complete = False
                    break
                page += 1

            # Store one party at a time so ``_store_donations``' live_ids span
            # the party's whole page set, and pass the completeness signal so a
            # partial batch (cut by max_pages or an empty page) never re-keys.
            total_new += _store_donations(db, party_donations, complete=complete)

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
    from src.knab.analyze import run_all_checks

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
