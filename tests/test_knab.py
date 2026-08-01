"""Tests for KNAB tables in init_db()."""

import sqlite3
import tempfile
import os
import sys
from unittest.mock import patch

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class _SafeConnection:
    """Wrapper around sqlite3.Connection that silently skips vec0 operations."""

    def __init__(self, real_conn):
        self._conn = real_conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def execute(self, sql, *args, **kwargs):
        if "vec0" in sql:
            return self._conn.cursor()
        return self._conn.execute(sql, *args, **kwargs)

    def enable_load_extension(self, flag):
        pass  # no-op


def _init_db_to_temp():
    """Run init_db() against a temp database,
    mocking out sqlite-vec which may not be installed in CI."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    # Patch sqlite_vec so tests don't require the native extension
    fake_vec = type(sys)("sqlite_vec")
    fake_vec.load = lambda conn: None

    # Wrap get_db to return our safe connection wrapper
    from src import db as db_module
    _real_get_db = db_module.get_db

    def _patched_get_db(path=None, _allow_empty=False):
        # Forward _allow_empty: init_db() opens the fresh 0-byte temp file
        # through this wrapper, and the real get_db refuses 0-byte files
        # unless told the caller is the legitimate initializer.
        conn = _real_get_db(path or db_path, _allow_empty=_allow_empty)
        return _SafeConnection(conn)

    with patch.dict(sys.modules, {"sqlite_vec": fake_vec}), \
         patch.object(db_module, "get_db", _patched_get_db):
        db_module.init_db(db_path)

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db, db_path


def _get_tables(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return {r[0] for r in rows}


def _get_indexes(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {r[0] for r in rows}


def _get_columns(db, table):
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


class TestKnabTables:
    def setup_method(self):
        self.db, self.db_path = _init_db_to_temp()

    def teardown_method(self):
        self.db.close()
        # On Windows, WAL mode keeps -wal/-shm files that may lock the db.
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            try:
                os.unlink(p)
            except OSError:
                pass

    def test_knab_donors_table_exists(self):
        tables = _get_tables(self.db)
        assert "knab_donors" in tables

    def test_knab_donations_table_exists(self):
        tables = _get_tables(self.db)
        assert "knab_donations" in tables

    def test_knab_declarations_table_exists(self):
        tables = _get_tables(self.db)
        assert "knab_declarations" in tables

    def test_knab_alerts_table_exists(self):
        tables = _get_tables(self.db)
        assert "knab_alerts" in tables

    def test_knab_donors_columns(self):
        cols = _get_columns(self.db, "knab_donors")
        expected = {"id", "name", "personal_id_masked", "politician_id", "created_at"}
        assert expected.issubset(cols)

    def test_knab_donations_columns(self):
        cols = _get_columns(self.db, "knab_donations")
        expected = {
            "id", "knab_id", "donor_id", "party", "donation_type",
            "amount_eur", "currency", "original_amount", "donor_name",
            "donor_pid_masked", "date", "detail_url", "scraped_at",
        }
        assert expected.issubset(cols)

    def test_knab_declarations_columns(self):
        cols = _get_columns(self.db, "knab_declarations")
        expected = {
            "id", "knab_id", "party", "declaration_type", "year", "date",
            "detail_url", "income_total", "income_donations", "income_membership",
            "income_state_budget", "expenses_total", "expenses_advertising",
            "expenses_salaries", "raw_data", "scraped_at",
        }
        assert expected.issubset(cols)

    def test_knab_alerts_columns(self):
        cols = _get_columns(self.db, "knab_alerts")
        expected = {
            "id", "alert_type", "severity", "party", "donor_id",
            "politician_id", "title", "description", "data",
            "reviewed", "created_at",
        }
        assert expected.issubset(cols)

    def test_knab_indexes_exist(self):
        indexes = _get_indexes(self.db)
        expected_indexes = {
            "idx_knab_donations_party",
            "idx_knab_donations_donor",
            "idx_knab_donations_date",
            "idx_knab_donors_politician",
            "idx_knab_declarations_party",
            "idx_knab_alerts_type",
        }
        assert expected_indexes.issubset(indexes), (
            f"Missing indexes: {expected_indexes - indexes}"
        )

    def test_knab_donors_unique_constraint(self):
        """Insert two donors with same name+pid and expect UNIQUE violation."""
        self.db.execute(
            "INSERT INTO knab_donors (name, personal_id_masked) VALUES (?, ?)",
            ("Jānis Bērziņš", "010180-1XXXX"),
        )
        self.db.commit()
        try:
            self.db.execute(
                "INSERT INTO knab_donors (name, personal_id_masked) VALUES (?, ?)",
                ("Jānis Bērziņš", "010180-1XXXX"),
            )
            self.db.commit()
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass  # expected

    def test_knab_donations_knab_id_unique(self):
        """knab_id should be unique in knab_donations."""
        self.db.execute(
            "INSERT INTO knab_donors (name) VALUES (?)", ("Test",)
        )
        donor_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.execute(
            """INSERT INTO knab_donations
               (knab_id, donor_id, party, donation_type, amount_eur, donor_name, date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("K001", donor_id, "TestParty", "money", 100.0, "Test", "2026-01-01"),
        )
        self.db.commit()
        try:
            self.db.execute(
                """INSERT INTO knab_donations
                   (knab_id, donor_id, party, donation_type, amount_eur, donor_name, date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("K001", donor_id, "TestParty", "money", 200.0, "Test", "2026-02-01"),
            )
            self.db.commit()
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass


# ---------------------------------------------------------------------------
# Donation page HTML parsing tests
# ---------------------------------------------------------------------------


def test_parse_donations_page():
    """Parse a real KNAB donations HTML page into structured data."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_donations_page
    donations = parse_donations_page(html)
    assert len(donations) > 0
    assert len(donations) <= 50
    d = donations[0]
    assert "party" in d
    assert "donation_type" in d
    assert "amount_eur" in d
    assert "donor_name" in d
    assert "date" in d
    assert isinstance(d["amount_eur"], float)
    assert d["amount_eur"] > 0


def test_parse_donations_page_fields_complete():
    """Every donation dict has all expected keys."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_donations_page
    donations = parse_donations_page(html)
    expected_keys = {
        "knab_id", "party", "donation_type", "amount_eur", "currency",
        "original_amount", "donor_name", "donor_pid_masked", "date", "detail_url",
    }
    for d in donations:
        assert expected_keys.issubset(d.keys()), f"Missing keys: {expected_keys - d.keys()}"


def test_parse_donations_page_date_format():
    """Dates should be in ISO yyyy-mm-dd format."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_donations_page
    import re as _re
    donations = parse_donations_page(html)
    for d in donations:
        assert _re.match(r"\d{4}-\d{2}-\d{2}$", d["date"]), f"Bad date: {d['date']}"


def test_parse_donations_page_knab_id():
    """Each donation should have a non-empty knab_id."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_donations_page
    donations = parse_donations_page(html)
    for d in donations:
        assert d["knab_id"], f"Empty knab_id for {d['donor_name']}"


def test_parse_amount():
    """Unit test for _parse_amount helper."""
    from src.knab import _parse_amount
    assert _parse_amount("EUR 200.00") == (200.0, "EUR")
    assert _parse_amount("LVL 50.00") == (50.0, "LVL")
    assert _parse_amount("EUR 3000.00") == (3000.0, "EUR")


def test_parse_date_lv():
    """Unit test for _parse_date_lv helper."""
    from src.knab import _parse_date_lv
    assert _parse_date_lv("30.03.2026") == "2026-03-30"
    assert _parse_date_lv("01.01.2020") == "2020-01-01"


def test_extract_donor_pid():
    """Unit test for _extract_donor_pid helper."""
    from src.knab import _extract_donor_pid
    name, pid = _extract_donor_pid("Aleksejs Stecs\n060880*****")
    assert name == "Aleksejs Stecs"
    assert pid == "060880*****"
    # No PID case
    name2, pid2 = _extract_donor_pid("SIA Kompānija")
    assert name2 == "SIA Kompānija"
    assert pid2 == ""


# ---------------------------------------------------------------------------
# Declaration page HTML parsing tests
# ---------------------------------------------------------------------------


def test_parse_declarations_page():
    """Parse a real KNAB declarations HTML page."""
    fixture_path = os.path.join("tests", "fixtures", "knab_declarations_page.html")
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


def test_parse_declarations_page_fields_complete():
    """Every declaration dict has all expected keys."""
    fixture_path = os.path.join("tests", "fixtures", "knab_declarations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_declarations_page
    declarations = parse_declarations_page(html)
    expected_keys = {"knab_id", "party", "declaration_type", "year", "date", "detail_url"}
    for d in declarations:
        assert expected_keys.issubset(d.keys()), f"Missing keys: {expected_keys - d.keys()}"


def test_parse_declarations_page_date_format():
    """Dates should be in ISO yyyy-mm-dd format."""
    fixture_path = os.path.join("tests", "fixtures", "knab_declarations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_declarations_page
    import re as _re
    declarations = parse_declarations_page(html)
    for d in declarations:
        assert _re.match(r"\d{4}-\d{2}-\d{2}$", d["date"]), f"Bad date: {d['date']}"


def test_parse_declarations_page_knab_id():
    """Each declaration should have a non-empty knab_id."""
    fixture_path = os.path.join("tests", "fixtures", "knab_declarations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_declarations_page
    declarations = parse_declarations_page(html)
    for d in declarations:
        assert d["knab_id"], f"Empty knab_id for {d['party']}"


# ---------------------------------------------------------------------------
# Fetch engine tests (Task 4)
# ---------------------------------------------------------------------------


def test_build_url():
    from src.knab import _build_url, DONATIONS_URL
    url = _build_url(DONATIONS_URL, page=3, per_page=500)
    assert "page=3" in url
    assert "recordsPerPage=500" in url


def test_build_url_with_filters():
    from src.knab import _build_url, DONATIONS_URL
    url = _build_url(DONATIONS_URL, page=0, per_page=500, party="JV")
    assert "party=JV" in url or "party=" in url


def test_get_total_pages_from_fixture():
    """_get_total_pages extracts correct page count from fixture HTML."""
    fixture_path = os.path.join("tests", "fixtures", "knab_donations_page.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import _get_total_pages
    # Fixture has recordsPerPage=50, last page link is page=1466 → 1467 pages
    pages = _get_total_pages(html, per_page=50)
    assert pages == 1467


def test_upsert_donor_creates_and_deduplicates(tmp_path):
    """_upsert_donor creates new donor then returns same id for duplicate."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _upsert_donor
    id1 = _upsert_donor(db, "Jānis Bērziņš", "120680*****")
    id2 = _upsert_donor(db, "Jānis Bērziņš", "120680*****")
    id3 = _upsert_donor(db, "Anna Bērziņa", "150790*****")
    assert id1 == id2  # same person
    assert id1 != id3  # different person
    db.close()


def test_store_donations_deduplicates(tmp_path):
    """_store_donations skips donations with duplicate knab_id."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations
    donations = [{
        "knab_id": "test-001",
        "party": "Test Party",
        "donation_type": "Nauda",
        "amount_eur": 100.0,
        "currency": "EUR",
        "original_amount": 100.0,
        "donor_name": "Test Person",
        "donor_pid_masked": "010190*****",
        "date": "2026-01-15",
        "detail_url": "",
    }]
    new1 = _store_donations(db, donations)
    new2 = _store_donations(db, donations)  # duplicate
    assert new1 == 1
    assert new2 == 0
    db.close()


# ---------------------------------------------------------------------------
# Declaration fetch engine tests (Task 5)
# ---------------------------------------------------------------------------


def test_is_tracked_party_matches():
    from src.knab import _is_tracked_party
    assert _is_tracked_party("Jaunā VIENOTĪBA") is True
    assert _is_tracked_party("\"PROGRESĪVIE\"") is True
    assert _is_tracked_party("LATVIJA PIRMAJĀ VIETĀ") is True


def test_is_tracked_party_prefix_match():
    """APVIENOTAIS SARAKSTS matches with prefix since full name is longer."""
    from src.knab import _is_tracked_party
    assert _is_tracked_party("\"APVIENOTAIS SARAKSTS - Latvijas Zaļā partija, Latvijas Reģionu Apvienība, Liepājas partija\"") is True


def test_is_tracked_party_rejects_unknown():
    from src.knab import _is_tracked_party
    assert _is_tracked_party("Kāda nedzirdēta partija") is False
    assert _is_tracked_party("Random party") is False


def test_store_declarations_deduplicates(tmp_path):
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_declarations
    decls = [{
        "knab_id": "dcl-test-001",
        "party": "Test Party",
        "declaration_type": "Gada pārskats",
        "year": 2025,
        "date": "2026-03-15",
        "detail_url": "",
    }]
    new1 = _store_declarations(db, decls)
    new2 = _store_declarations(db, decls)
    assert new1 == 1
    assert new2 == 0
    db.close()


# ---------------------------------------------------------------------------
# KNAB cross-referencing & anomaly detection tests (Task 6)
# ---------------------------------------------------------------------------


def test_normalize_name():
    from src.knab_analyze import _normalize_name
    assert _normalize_name("JĀNIS BĒRZIŅŠ") == "janis berzins"
    assert _normalize_name("  Artūrs  Krišjānis  ") == "arturs krisjanis"


def test_detect_multi_party_donors(tmp_path):
    """Detects donors giving to multiple parties."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations
    # Same person, two parties
    donations = [
        {"knab_id": "mp-1", "party": "Party A", "donation_type": "Nauda",
         "amount_eur": 500.0, "currency": "EUR", "original_amount": 500.0,
         "donor_name": "Jānis Tests", "donor_pid_masked": "010190*****",
         "date": "2026-01-15", "detail_url": ""},
        {"knab_id": "mp-2", "party": "Party B", "donation_type": "Nauda",
         "amount_eur": 300.0, "currency": "EUR", "original_amount": 300.0,
         "donor_name": "Jānis Tests", "donor_pid_masked": "010190*****",
         "date": "2026-02-15", "detail_url": ""},
    ]
    _store_donations(db, donations)
    db.close()

    from src.knab_analyze import detect_multi_party_donors
    multi = detect_multi_party_donors(db_path)
    assert len(multi) >= 1
    assert multi[0]["donor_name"] == "Jānis Tests"
    assert multi[0]["party_count"] == 2


def test_detect_family_clusters(tmp_path):
    """Detects same-surname donors to same party."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations
    donations = [
        {"knab_id": "fc-1", "party": "MMN", "donation_type": "Nauda",
         "amount_eur": 5000.0, "currency": "EUR", "original_amount": 5000.0,
         "donor_name": "Pauls Dandzbergs", "donor_pid_masked": "010190*****",
         "date": "2026-01-15", "detail_url": ""},
        {"knab_id": "fc-2", "party": "MMN", "donation_type": "Nauda",
         "amount_eur": 5000.0, "currency": "EUR", "original_amount": 5000.0,
         "donor_name": "Marts Dandzbergs", "donor_pid_masked": "020290*****",
         "date": "2026-02-15", "detail_url": ""},
    ]
    _store_donations(db, donations)
    db.close()

    from src.knab_analyze import detect_family_clusters
    families = detect_family_clusters(db_path)
    assert len(families) >= 1
    assert families[0]["member_count"] == 2
    assert families[0]["total_eur"] == 10000.0


# ---------------------------------------------------------------------------
# Convenience entry point tests (Task 7)
# ---------------------------------------------------------------------------


def test_get_party_summary(tmp_path):
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations, get_party_summary
    donations = [
        {"knab_id": "ps-1", "party": "Test A", "donation_type": "Nauda",
         "amount_eur": 100.0, "currency": "EUR", "original_amount": 100.0,
         "donor_name": "Person 1", "donor_pid_masked": "010190*****",
         "date": "2026-01-15", "detail_url": ""},
        {"knab_id": "ps-2", "party": "Test A", "donation_type": "Nauda",
         "amount_eur": 200.0, "currency": "EUR", "original_amount": 200.0,
         "donor_name": "Person 2", "donor_pid_masked": "020290*****",
         "date": "2026-02-15", "detail_url": ""},
    ]
    _store_donations(db, donations)
    db.close()
    result = get_party_summary(db_path=db_path)
    assert len(result) == 1
    assert result[0]["party"] == "Test A"
    assert result[0]["donation_count"] == 2
    assert result[0]["total_eur"] == 300.0


# ---------------------------------------------------------------------------
# Live integration test (Task 8)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_live_fetch_one_page(tmp_path):
    """Integration test: fetch one real page from KNAB and store in DB."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)

    from src.knab import fetch_all_donations
    # max_pages counts fetched pages, including a tracked party with zero
    # payments (SV/AJ, founded 2026-06, sits first in the API party order) —
    # 5 pages guarantees at least one populated party page.
    new = fetch_all_donations(db_path=db_path, max_pages=5)
    assert new > 0

    db = get_db(db_path)
    donations = db.execute("SELECT COUNT(*) FROM knab_donations").fetchone()[0]
    donors = db.execute("SELECT COUNT(*) FROM knab_donors").fetchone()[0]
    db.close()
    assert donations > 0
    assert donors > 0
    print(f"Live test: {donations} donations, {donors} donors from 1 page")


# ---------------------------------------------------------------------------
# Declaration detail page parsing tests (Task 9)
# ---------------------------------------------------------------------------


def test_parse_euro():
    """Unit test for _parse_euro helper."""
    from src.knab import _parse_euro
    assert _parse_euro("\u20ac 291937.00") == 291937.0
    assert _parse_euro("\u20ac -127.00") == -127.0
    assert _parse_euro("\u20ac 0.00") == 0.0
    assert _parse_euro("-") == 0.0
    assert _parse_euro("") == 0.0
    assert _parse_euro("  \u20ac  52185.00  ") == 52185.0


def test_parse_declaration_detail():
    """Parse a real KNAB declaration detail HTML page."""
    # No skip-if-missing branch: the fixture is tracked in git (29 KB, since
    # 2026-04-07), so "not yet captured" cannot happen — and if it ever does go
    # missing, this test must go RED, not quietly green. A skip reads as
    # coverage in the summary while asserting nothing.
    fixture_path = os.path.join("tests", "fixtures", "knab_declaration_detail.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_declaration_detail
    result = parse_declaration_detail(html)
    assert result["income_total"] is not None
    assert isinstance(result["income_total"], float)
    assert result["expenses_total"] is not None
    assert "raw_data" in result
    import json
    raw = json.loads(result["raw_data"])
    assert len(raw) > 10  # should have many fields


def test_parse_declaration_detail_specific_values():
    """Verify specific financial values from the PROGRESIVIE fixture."""
    # No skip-if-missing branch: the fixture is tracked in git (29 KB, since
    # 2026-04-07), so "not yet captured" cannot happen — and if it ever does go
    # missing, this test must go RED, not quietly green. A skip reads as
    # coverage in the summary while asserting nothing.
    fixture_path = os.path.join("tests", "fixtures", "knab_declaration_detail.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
    from src.knab import parse_declaration_detail
    result = parse_declaration_detail(html)
    assert result["income_total"] == 582466.0
    assert result["income_donations"] == 54222.0
    assert result["income_membership"] == 21698.0
    assert result["income_state_budget"] == 506426.0
    assert result["expenses_total"] == 530281.0
    assert result["expenses_advertising"] == 100537.0
    assert result["expenses_salaries"] == 218837.0


def test_parse_declaration_detail_empty_html():
    """Gracefully handle empty/invalid HTML."""
    from src.knab import parse_declaration_detail
    result = parse_declaration_detail("")
    assert result["raw_data"] == "{}"
    assert result.get("income_total") is None


# ---------------------------------------------------------------------------
# JSON API migration tests (2026-07 rebuild: HTML scrape -> JSON API)
# ---------------------------------------------------------------------------


def test_payment_to_donation_eur():
    """_payment_to_donation maps an EUR payment record to the store dict."""
    from src.knab import _payment_to_donation
    pay = {
        "public_id": "37632fbd2e92f703a79b5242740d5ded",
        "party_public_id": "6363c9bba09da347fa751945487a2fe1",
        "party": "LATVIJA PIRMAJĀ VIETĀ",
        "typeId": 1, "type": "Nauda",
        "amountDisplay": "3900.00", "currency": "EUR",
        "firstName": "JURIJS", "lastName": "ČIRKOVS",
        "person": "JURIJS ČIRKOVS", "personCode": "040158*****",
        "date": "20.07.2026",
    }
    d = _payment_to_donation(pay)
    assert d["knab_id"] == "37632fbd2e92f703a79b5242740d5ded"
    assert d["party"] == "LATVIJA PIRMAJĀ VIETĀ"
    assert d["donation_type"] == "Nauda"
    assert d["currency"] == "EUR"
    assert d["date"] == "2026-07-20"
    assert d["donor_name"] == "JURIJS ČIRKOVS"
    assert d["donor_pid_masked"] == "040158*****"
    assert d["original_amount"] == 3900.0
    assert d["amount_eur"] == 3900.0
    assert d["detail_url"] == (
        "https://info.knab.gov.lv/donations/show?public_id=37632fbd2e92f703a79b5242740d5ded"
    )


def test_payment_to_donation_lvl_conversion():
    """LVL payments convert to EUR via /0.702804; original_amount keeps display."""
    from src.knab import _payment_to_donation
    pay = {
        "public_id": "lvl-001", "party": "Partija \"Gods kalpot Rīgai\"",
        "type": "Nauda", "amountDisplay": "500.00", "currency": "LVL",
        "person": "GUNTIS ROZĪTIS", "personCode": "010180*****",
        "date": "30.07.2011",
    }
    d = _payment_to_donation(pay)
    assert d["currency"] == "LVL"
    assert d["original_amount"] == 500.0
    assert d["amount_eur"] == 711.44  # round(500 / 0.702804, 2)
    assert d["date"] == "2011-07-30"


def test_payment_to_donation_negative_amount():
    """Negative amounts (returned donations) map through unchanged for EUR."""
    from src.knab import _payment_to_donation
    pay = {
        "public_id": "neg-001", "party": "LATVIJA PIRMAJĀ VIETĀ",
        "type": "Nauda", "amountDisplay": "-127.00", "currency": "EUR",
        "person": "ANNA TESTE", "personCode": "020290*****",
        "date": "01.03.2026",
    }
    d = _payment_to_donation(pay)
    assert d["amount_eur"] == -127.0
    assert d["original_amount"] == -127.0


def test_legacy_dedup_guard_skips_legacy_row(tmp_path):
    """A pre-cutoff donation already present under a legacy synthetic key is
    NOT re-inserted when it arrives from the API with a public_id key.

    Legacy rows use mixed-case donor names; API returns UPPERCASE, so the
    guard must compare case-insensitively.
    """
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    # Seed one legacy-format row (synthetic knab_id, date <= cutoff, mixed case)
    db.execute(
        """INSERT INTO knab_donations
           (knab_id, party, donation_type, amount_eur, currency,
            original_amount, donor_name, donor_pid_masked, date, detail_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("2025-12-16-Vilis Krištopans-100-LATVIJA PIRMAJĀ VIE", "LATVIJA PIRMAJĀ VIETĀ",
         "Nauda", 100.0, "EUR", "EUR 100.00", "Vilis Krištopans", "010160*****",
         "2025-12-16", "", "2026-04-08 00:00:00"),
    )
    db.commit()

    # Same donation from API JSON (public_id key, UPPERCASE name)
    api_dup = [{
        "knab_id": "abc123public",
        "party": "LATVIJA PIRMAJĀ VIETĀ",
        "donation_type": "Nauda",
        "amount_eur": 100.0,
        "currency": "EUR",
        "original_amount": 100.0,
        "donor_name": "VILIS KRIŠTOPANS",
        "donor_pid_masked": "010160*****",
        "date": "2025-12-16",
        "detail_url": "",
    }]
    new1 = _store_donations(db, api_dup)
    assert new1 == 0, "legacy dedup guard should skip the pre-cutoff duplicate"

    # A post-cutoff record cannot exist in the legacy DB -> inserts
    api_new = [{
        "knab_id": "def456public",
        "party": "LATVIJA PIRMAJĀ VIETĀ",
        "donation_type": "Nauda",
        "amount_eur": 55.0,
        "currency": "EUR",
        "original_amount": 55.0,
        "donor_name": "JAUNS ZIEDOTĀJS",
        "donor_pid_masked": "030390*****",
        "date": "2026-07-20",
        "detail_url": "",
    }]
    new2 = _store_donations(db, api_new)
    assert new2 == 1, "post-cutoff record must insert"

    # Re-running the post-cutoff record is idempotent on public_id
    new3 = _store_donations(db, api_new)
    assert new3 == 0, "public_id INSERT OR IGNORE must prevent re-insert"
    db.close()


def test_legacy_dedup_guard_lvl_conversion_drift(tmp_path):
    """LVL-era rows: legacy HTML scrape converted LVL->EUR with different
    rounding than LVL_TO_EUR_RATE (20000 LVL -> 28457.60 legacy vs 28457.44
    API), so amount_eur alone drifts past the cent tolerance. The guard must
    fall back to comparing the ORIGINAL amount + currency — the 2026-07-24
    first refresh duplicated 1221 rows before this branch existed.
    """
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    db.execute(
        """INSERT INTO knab_donations
           (knab_id, party, donation_type, amount_eur, currency,
            original_amount, donor_name, donor_pid_masked, date, detail_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("2011-08-03-Dace Pūce-20000-Jaunā VIENOTĪ", "Jaunā VIENOTĪBA",
         "Nauda", 28457.60, "LVL", "LVL 20000.00", "Dace Pūce", "010160*****",
         "2011-08-03", "", "2026-04-08 00:00:00"),
    )
    db.commit()

    api_dup = [{
        "knab_id": "a9d4859b0a9941a8c82fa3e5812292e0",
        "party": "Jaunā VIENOTĪBA",
        "donation_type": "Nauda",
        "amount_eur": 28457.44,  # 20000 / 0.702804 — 0.16 EUR drift vs legacy
        "currency": "LVL",
        "original_amount": 20000.0,
        "donor_name": "DACE PŪCE",
        "donor_pid_masked": "010160*****",
        "date": "2011-08-03",
        "detail_url": "",
    }]
    new = _store_donations(db, api_dup)
    assert new == 0, "original-amount match must catch the LVL conversion drift"
    db.close()


def _donation_row(knab_id, donation_type="Nauda", amount_eur=316309.12,
                  date="2026-05-07"):
    """Build a LATVIJA PIRMĀ association donation dict for dedup tests."""
    return {
        "knab_id": knab_id,
        "party": "LATVIJA PIRMAJĀ VIETĀ",
        "donation_type": donation_type,
        "amount_eur": amount_eur,
        "currency": "EUR",
        "original_amount": amount_eur,
        "donor_name": "Biedrība LATVIJA PIRMĀ",
        "donor_pid_masked": "40008308560",
        "date": date,
        "detail_url": "",
    }


def _raw_insert_donation(db, d):
    """Insert *d* directly into knab_donations, bypassing reconciliation.

    Used to seed a pre-existing (corrupt) state that the store logic must later
    converge from — e.g. the stale same-content duplicate an old partial batch
    left beside a re-keyed row.
    """
    donor = db.execute(
        "SELECT id FROM knab_donors WHERE name = ? AND personal_id_masked = ?",
        (d["donor_name"], d.get("donor_pid_masked", "")),
    ).fetchone()
    if donor is None:
        db.execute(
            "INSERT INTO knab_donors (name, personal_id_masked) VALUES (?, ?)",
            (d["donor_name"], d.get("donor_pid_masked", "")),
        )
        donor_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    else:
        donor_id = donor[0]
    db.execute(
        """INSERT INTO knab_donations
           (knab_id, donor_id, party, donation_type, amount_eur, currency,
            original_amount, donor_name, donor_pid_masked, date, detail_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (d["knab_id"], donor_id, d["party"], d["donation_type"], d["amount_eur"],
         d.get("currency", "EUR"), d.get("original_amount"), d["donor_name"],
         d.get("donor_pid_masked", ""), d["date"], d.get("detail_url", ""),
         "2026-08-14 00:00:00"),
    )


def _latvija_pirma_scenario():
    """(old_snapshot, current_api) for the 24-row LATVIJA PIRMĀ reconciliation.

    Mirrors the research 2026-08-14 finding: on 2026-07-24 the three positive
    rows were stored as 'Nauda' under old public_ids, and KNAB later re-keyed
    them (new public_id + type 'Manta vai pakalpojums'); one negative −10000.00
    row (2026-07-18) was also re-keyed; the other 20 negative rows kept their
    ids.  3 positive + 21 negative = 24 rows, net 0.00.
    """
    party = "LATVIJA PIRMAJĀ VIETĀ"
    donor = "Biedrība LATVIJA PIRMĀ"
    code = "40008308560"

    def row(knab_id, donation_type, amount_eur, date):
        return {
            "knab_id": knab_id,
            "party": party,
            "donation_type": donation_type,
            "amount_eur": amount_eur,
            "currency": "EUR",
            "original_amount": amount_eur,
            "donor_name": donor,
            "donor_pid_masked": code,
            "date": date,
            "detail_url": "",
        }

    positive_old = [
        row("P1-OLD", "Nauda", 316309.12, "2026-05-07"),
        row("P2-OLD", "Nauda", 24200.00, "2026-05-11"),
        row("P3-OLD", "Nauda", 145.20, "2026-06-19"),
    ]
    positive_new = [
        row("P1-NEW", "Manta vai pakalpojums", 316309.12, "2026-05-07"),
        row("P2-NEW", "Manta vai pakalpojums", 24200.00, "2026-05-11"),
        row("P3-NEW", "Manta vai pakalpojums", 145.20, "2026-06-19"),
    ]
    # (old_id, new_id, amount, date); only the 18.07 -10000 is re-keyed.
    neg_specs = [
        ("R1", "R1", -30000.00, "2026-05-11"),
        ("R2", "R2", -30000.00, "2026-05-11"),
        ("N1", "N1", -145.20, "2026-06-19"),
        ("N4-OLD", "N4-NEW", -10000.00, "2026-07-18"),
        ("N5", "N5", -20000.00, "2026-06-05"),
        ("N6", "N6", -20000.00, "2026-06-06"),
        ("N7", "N7", -20000.00, "2026-06-07"),
        ("N8", "N8", -20000.00, "2026-06-08"),
        ("N9", "N9", -20000.00, "2026-06-09"),
        ("N10", "N10", -20000.00, "2026-06-10"),
        ("N11", "N11", -20000.00, "2026-06-11"),
        ("N12", "N12", -20000.00, "2026-06-12"),
        ("N13", "N13", -20000.00, "2026-06-13"),
        ("N14", "N14", -20000.00, "2026-06-14"),
        ("N15", "N15", -20000.00, "2026-06-15"),
        ("N16", "N16", -20000.00, "2026-06-16"),
        ("N17", "N17", -10000.00, "2026-06-20"),
        ("N18", "N18", -10000.00, "2026-06-21"),
        ("N19", "N19", -5000.00, "2026-07-01"),
        ("N20", "N20", -5000.00, "2026-07-05"),
        ("N21", "N21", -509.12, "2026-07-10"),
    ]
    old = positive_old + [row(o, "Nauda", a, d) for o, n, a, d in neg_specs]
    new = positive_new + [row(n, "Nauda", a, d) for o, n, a, d in neg_specs]
    return old, new


def test_store_donations_reconciles_rekeyed_public_id(tmp_path):
    """A donation re-keyed by KNAB (new public_id + changed type) is reconciled
    in place on content identity, not duplicated via INSERT OR IGNORE.

    Regression for the LATVIJA PIRMĀ case (research 2026-08-14): four rows'
    public_id and three rows' type changed after the 2026-07-24 import; a
    public_id-only INSERT OR IGNORE would re-insert them and invent a false
    +330654.32 net.
    """
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("old-public-id", "Nauda")]) == 1
    # KNAB reclassifies the record: new public_id, type -> Manta vai pakalpojums.
    assert _store_donations(
        db, [_donation_row("new-public-id", "Manta vai pakalpojums")]
    ) == 0

    rows = db.execute(
        "SELECT knab_id, donation_type, amount_eur FROM knab_donations"
    ).fetchall()
    assert len(rows) == 1, f"expected 1 row after re-key, got {len(rows)}"
    assert rows[0]["knab_id"] == "new-public-id"
    assert rows[0]["donation_type"] == "Manta vai pakalpojums"
    assert rows[0]["amount_eur"] == 316309.12
    db.close()


def test_store_donations_preserves_genuine_same_day_duplicates(tmp_path):
    """Two DISTINCT KNAB records with identical content (same party/donor/
    date/amount) but different public_ids are both kept — e.g. the two
    −30000.00 refund rows on 2026-05-11 for LATVIJA PIRMĀ."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    new = _store_donations(
        db,
        [
            _donation_row("dup-a", "Nauda", -30000.0, "2026-05-11"),
            _donation_row("dup-b", "Nauda", -30000.0, "2026-05-11"),
        ],
    )
    assert new == 2, "genuine same-content records must both insert"
    n = db.execute("SELECT COUNT(*) FROM knab_donations").fetchone()[0]
    assert n == 2, f"expected 2 distinct rows, got {n}"
    db.close()


def test_store_donations_refreshes_type_on_same_id(tmp_path):
    """A record reclassified in place (same public_id, new type) has its type
    refreshed, not left stale by INSERT OR IGNORE."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("id-1", "Nauda")]) == 1
    assert _store_donations(
        db, [_donation_row("id-1", "Manta vai pakalpojums")]
    ) == 0

    rows = db.execute(
        "SELECT knab_id, donation_type FROM knab_donations"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["knab_id"] == "id-1"
    assert rows[0]["donation_type"] == "Manta vai pakalpojums"
    db.close()


def test_get_top_donors_nets_positive_and_refund(tmp_path):
    """Reader-facing aggregation nets signed amounts: a donor whose single
    positive row is fully refunded nets to zero and is not surfaced as a
    large positive donor (no single-positive-row highlight)."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations, get_top_donors

    _store_donations(
        db,
        [
            _donation_row("pos-1", "Manta vai pakalpojums", 316309.12, "2026-05-07"),
            _donation_row("neg-1", "Nauda", -316309.12, "2026-05-07"),
        ],
    )
    db.close()

    top = get_top_donors(db_path=db_path)
    donor = next((t for t in top if t["donor_name"] == "Biedrība LATVIJA PIRMĀ"), None)
    assert donor is not None
    assert donor["total_eur"] == 0.0, "positive must net against its refund"


def test_store_donations_partial_batch_skips_ambiguous_candidate(tmp_path):
    """F1: a partial/truncated batch never destructively re-keys AND never
    inserts a persistent duplicate for an ambiguous candidate.

    ``live-x`` is still live upstream but sits on an unfetched page; the
    incoming batch only carries the re-keyed ``arrived-y`` whose content
    matches ``live-x``.  On a partial batch that candidate is ambiguous (it may
    be a re-key of ``live-x`` or a genuine duplicate), so it is skipped — the
    decision is deferred to a later complete batch.
    """
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("live-x", "Nauda")]) == 1
    new = _store_donations(
        db, [_donation_row("arrived-y", "Manta vai pakalpojums")], complete=False
    )
    rows = db.execute(
        "SELECT knab_id, donation_type FROM knab_donations ORDER BY id"
    ).fetchall()
    assert new == 0, "ambiguous candidate must be skipped, not duplicated"
    assert [(r["knab_id"], r["donation_type"]) for r in rows] == [("live-x", "Nauda")]
    db.close()


def test_store_donations_partial_batch_inserts_genuinely_new(tmp_path):
    """F1: a partial batch still stores a genuinely new record (its content
    matches nothing stored), so partial runs keep making progress."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("live-x", "Nauda")]) == 1
    new = _store_donations(
        db, [_donation_row("new-z", "Nauda", 999.99, "2026-05-08")], complete=False
    )
    rows = db.execute("SELECT knab_id FROM knab_donations ORDER BY id").fetchall()
    assert new == 1, "a genuinely new record must insert even on a partial batch"
    assert {r["knab_id"] for r in rows} == {"live-x", "new-z"}
    db.close()


def test_store_donations_converges_after_partial_batch(tmp_path):
    """F5: after a partial batch skips a re-keyed record, a later COMPLETE batch
    reconciles to exactly the authoritative one-row state with the correct net."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("live-x", "Nauda")]) == 1
    # Partial batch sees only the re-keyed id; it must skip, not duplicate.
    assert _store_donations(
        db, [_donation_row("arrived-y", "Manta vai pakalpojums")], complete=False
    ) == 0
    # Later complete batch carries the authoritative id and reconciles.
    assert _store_donations(
        db, [_donation_row("arrived-y", "Manta vai pakalpojums")]
    ) == 0
    rows = db.execute(
        "SELECT knab_id, donation_type, amount_eur FROM knab_donations"
    ).fetchall()
    assert len(rows) == 1, f"expected 1 authoritative row, got {len(rows)}"
    assert rows[0]["knab_id"] == "arrived-y"
    assert rows[0]["donation_type"] == "Manta vai pakalpojums"
    assert rows[0]["amount_eur"] == 316309.12
    total = db.execute("SELECT SUM(amount_eur) FROM knab_donations").fetchone()[0]
    assert total == 316309.12
    db.close()


def test_store_donations_complete_batch_removes_stale_duplicate(tmp_path):
    """F5: a stale same-content row left beside the re-keyed row is deleted by a
    later complete batch (the exact corruption the old partial-batch path left)."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("live-x", "Nauda")]) == 1
    _raw_insert_donation(db, _donation_row("arrived-y", "Manta vai pakalpojums"))
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM knab_donations").fetchone()[0]
    assert n == 2, "corruption state: stale row + re-keyed duplicate"

    assert _store_donations(
        db, [_donation_row("arrived-y", "Manta vai pakalpojums")]
    ) == 0
    rows = db.execute(
        "SELECT knab_id, donation_type, amount_eur FROM knab_donations"
    ).fetchall()
    assert len(rows) == 1, f"expected 1 row after convergence, got {len(rows)}"
    assert rows[0]["knab_id"] == "arrived-y"
    assert rows[0]["donation_type"] == "Manta vai pakalpojums"
    total = db.execute("SELECT SUM(amount_eur) FROM knab_donations").fetchone()[0]
    assert total == 316309.12
    db.close()


def test_store_donations_count_mismatch_pair_to_one(tmp_path):
    """F6: a stored old-pair (2 same-content rows) converges to the current
    single row when a complete batch carries only one new id — one dead row is
    re-keyed and the excess stale row is removed."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [
        _donation_row("old-a", "Nauda", -30000.0, "2026-05-11"),
        _donation_row("old-b", "Nauda", -30000.0, "2026-05-11"),
    ]) == 2
    assert _store_donations(
        db, [_donation_row("new-a", "Nauda", -30000.0, "2026-05-11")]
    ) == 0
    rows = db.execute("SELECT knab_id, amount_eur FROM knab_donations").fetchall()
    assert len(rows) == 1, f"expected 1 row, got {len(rows)}"
    assert rows[0]["knab_id"] == "new-a"
    assert rows[0]["amount_eur"] == -30000.0
    db.close()


def test_store_donations_count_mismatch_one_to_pair(tmp_path):
    """F6: a stored single row converges to the current pair when a complete
    batch carries two new ids — one dead row is re-keyed, the excess incoming is
    inserted."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(
        db, [_donation_row("old-a", "Nauda", -30000.0, "2026-05-11")]
    ) == 1
    new = _store_donations(db, [
        _donation_row("new-a", "Nauda", -30000.0, "2026-05-11"),
        _donation_row("new-b", "Nauda", -30000.0, "2026-05-11"),
    ])
    rows = db.execute(
        "SELECT knab_id, amount_eur FROM knab_donations ORDER BY id"
    ).fetchall()
    assert len(rows) == 2, f"expected 2 rows, got {len(rows)}"
    assert {r["knab_id"] for r in rows} == {"new-a", "new-b"}
    assert sum(r["amount_eur"] for r in rows) == -60000.0
    assert new == 1, "one of the pair is a re-key (not new), the other inserts"
    db.close()


def test_latvija_pirma_24_row_reconciliation(tmp_path):
    """End-to-end regression for the LATVIJA PIRMĀ case (research 2026-08-14):
    reconciling the 2026-07-24 snapshot against the current API yields exactly
    24 rows, net 0.00, 3 rows of type 'Manta vai pakalpojums' (the corrected
    positive rows), and the current API id set — no fabricated +330654.32."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    old, new = _latvija_pirma_scenario()
    assert _store_donations(db, old, complete=True) == 24

    assert _store_donations(db, new, complete=True) == 0, (
        "reconciliation must re-key/refresh in place, not re-insert"
    )

    rows = db.execute(
        "SELECT knab_id, donation_type, amount_eur FROM knab_donations ORDER BY id"
    ).fetchall()
    net = sum(r["amount_eur"] for r in rows)
    manta = [r for r in rows if r["donation_type"] == "Manta vai pakalpojums"]
    print(
        f"LATVIJA PIRMĀ reconciliation: rows={len(rows)} net={net!r} "
        f"manta_count={len(manta)}"
    )
    assert len(rows) == 24, f"expected 24 rows, got {len(rows)}"
    assert abs(net) < 0.01, f"net must be 0.00, got {net!r}"
    assert len(manta) == 3, f"expected 3 'Manta vai pakalpojums' rows, got {len(manta)}"
    assert sorted(r["amount_eur"] for r in manta) == [145.20, 24200.00, 316309.12]
    assert {r["knab_id"] for r in rows} == {d["knab_id"] for d in new}
    db.close()


def test_store_donations_reconciles_rekeyed_duplicate_pair(tmp_path):
    """F2: two content-identical stored rows whose old ids are BOTH dead are
    re-keyed 1:1 (deterministic) when an equal-count group of new ids arrives —
    not silently duplicated into 4 rows."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [
        _donation_row("old-a", "Nauda", -30000.0, "2026-05-11"),
        _donation_row("old-b", "Nauda", -30000.0, "2026-05-11"),
    ]) == 2
    assert _store_donations(db, [
        _donation_row("new-a", "Nauda", -30000.0, "2026-05-11"),
        _donation_row("new-b", "Nauda", -30000.0, "2026-05-11"),
    ]) == 0, "re-keyed duplicate pair must reconcile, not insert"
    rows = db.execute("SELECT knab_id FROM knab_donations ORDER BY id").fetchall()
    assert len(rows) == 2, f"expected 2 rows after re-key, got {len(rows)}"
    assert {r["knab_id"] for r in rows} == {"new-a", "new-b"}
    db.close()


def test_store_donations_skips_same_public_id_different_content(tmp_path):
    """F3: the same public_id carrying different content in one batch must not
    silently mutate the first row's type — the conflicting record is skipped."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    a = _donation_row("shared-id", "Nauda", 100.0)
    b = _donation_row("shared-id", "Manta vai pakalpojums", 200.0)
    b["donor_name"] = "Cits donors"
    b["donor_pid_masked"] = "99999999999"
    new = _store_donations(db, [a, b])
    rows = db.execute(
        "SELECT knab_id, donation_type, amount_eur, donor_name FROM knab_donations"
    ).fetchall()
    assert new == 1, "the conflicting record must not fabricate or overwrite"
    assert len(rows) == 1
    assert rows[0]["donation_type"] == "Nauda"
    assert rows[0]["amount_eur"] == 100.0
    assert rows[0]["donor_name"] == "Biedrība LATVIJA PIRMĀ"
    db.close()


def test_store_donations_skips_falsy_public_id(tmp_path):
    """F4: a missing/falsy public_id must not null out a stored row's identity
    via the re-key path — it is skipped, leaving the row untouched."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_donations

    assert _store_donations(db, [_donation_row("live-x", "Nauda")]) == 1
    assert _store_donations(db, [_donation_row(None, "Manta vai pakalpojums")]) == 0
    assert _store_donations(db, [_donation_row("", "Manta vai pakalpojums")]) == 0
    rows = db.execute("SELECT knab_id, donation_type FROM knab_donations").fetchall()
    assert len(rows) == 1
    assert rows[0]["knab_id"] == "live-x"
    assert rows[0]["donation_type"] == "Nauda"
    db.close()


def test_fetch_all_donations_marks_truncated_batch_incomplete(tmp_path, monkeypatch):
    """F1 (fetch wiring): a party batch cut by max_pages is stored with
    complete=False so the re-key step is disabled for it."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db
    init_db(db_path)
    from src import knab

    captured = []

    def fake_store(db, donations, complete=True):
        captured.append((len(donations), complete))
        return 0

    monkeypatch.setattr(
        knab, "_fetch_all_parties",
        lambda client: [{"public_id": "party-1", "name": "LATVIJA PIRMAJĀ VIETĀ"}],
    )

    def fake_fetch_json(url, client):
        return {
            "payments": [{
                "public_id": "p1", "party": "LATVIJA PIRMAJĀ VIETĀ",
                "type": "Nauda", "amountDisplay": "100.00", "currency": "EUR",
                "person": "X", "personCode": "1", "date": "15.01.2026.",
            }],
            "pagination": {"totalPages": 3},
        }

    monkeypatch.setattr(knab, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(knab, "_store_donations", fake_store)

    knab.fetch_all_donations(db_path=db_path, max_pages=1, delay=0)
    assert captured == [(1, False)], captured


def test_fetch_all_donations_marks_empty_page_incomplete(tmp_path, monkeypatch):
    """F1 (fetch wiring): an unexpected empty page while totalPages claims more
    marks the party batch incomplete, disabling re-key."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db
    init_db(db_path)
    from src import knab

    captured = []

    def fake_store(db, donations, complete=True):
        captured.append((len(donations), complete))
        return 0

    monkeypatch.setattr(
        knab, "_fetch_all_parties",
        lambda client: [{"public_id": "party-1", "name": "LATVIJA PIRMAJĀ VIETĀ"}],
    )
    payment = {
        "public_id": "p1", "party": "LATVIJA PIRMAJĀ VIETĀ", "type": "Nauda",
        "amountDisplay": "100.00", "currency": "EUR", "person": "X",
        "personCode": "1", "date": "15.01.2026.",
    }

    def fake_fetch_json(url, client):
        if "page=1" in url:
            return {"payments": [payment], "pagination": {"totalPages": 3}}
        return {"payments": [], "pagination": {"totalPages": 3}}

    monkeypatch.setattr(knab, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(knab, "_store_donations", fake_store)

    knab.fetch_all_donations(db_path=db_path, delay=0)
    assert captured == [(1, False)], captured


def test_fetch_all_donations_marks_full_final_page_incomplete(tmp_path, monkeypatch):
    """F1 (fetch wiring, fail-closed): a FULL final page (len == per_page) with
    page == totalPages means the server may have capped `limit` below `per_page`
    while reporting totalPages for the requested size — the batch is marked
    incomplete so the destructive re-key/delete never runs on a truncated set."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db
    init_db(db_path)
    from src import knab

    captured = []

    def fake_store(db, donations, complete=True):
        captured.append((len(donations), complete))
        return 0

    monkeypatch.setattr(
        knab, "_fetch_all_parties",
        lambda client: [{"public_id": "party-1", "name": "LATVIJA PIRMAJĀ VIETĀ"}],
    )
    payment = {
        "public_id": "p1", "party": "LATVIJA PIRMAJĀ VIETĀ", "type": "Nauda",
        "amountDisplay": "100.00", "currency": "EUR", "person": "X",
        "personCode": "1", "date": "15.01.2026.",
    }

    def fake_fetch_json(url, client):
        return {"payments": [payment], "pagination": {"totalPages": 1}}

    monkeypatch.setattr(knab, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(knab, "_store_donations", fake_store)

    knab.fetch_all_donations(db_path=db_path, per_page=1, delay=0)
    assert captured == [(1, False)], captured


def test_declaration_detail_rows_field_map():
    """_declaration_detail_from_rows maps annual-report rows to fields and
    gates FIELD_MAP on the income/expenses section so the cash-flow section's
    '5. Reklāmas pakalpojumi' does NOT clobber expenses_advertising.
    """
    from src.knab import _declaration_detail_from_rows
    rows = [
        {"label": "Ieņēmumu un izdevumu pārskats", "amount": "", "section": True},
        {"label": "I. Biedru nauda un iestāšanās nauda.", "amount": "€ 11602.00", "level": 0},
        {"label": "II. Saņemtie dāvinājumi (ziedojumi).", "amount": "€ 88847.00", "level": 0},
        {"label": "V. Valsts budžeta finansējums.", "amount": "€ 1120000.00", "level": 0},
        {"label": "VII. Ieņēmumi kopā.", "amount": "€ 1316749.00", "level": 0, "total": True},
        {"label": "5. Reklāmas pakalpojumi.", "amount": "€ 482102.00", "level": 1},
        {"label": "7. Darba algas un citi maksājumi fiziskām personām.", "amount": "€ 139244.00", "level": 1},
        {"label": "X. Izdevumi kopā.", "amount": "€ 1487443.00", "level": 0, "total": True},
        # --- cash-flow section: MUST NOT map into FIELD_MAP fields ---
        {"label": "Naudas plūsmas pārskats", "amount": "", "section": True},
        {"label": "5. Reklāmas pakalpojumi.", "amount": "€ 473636.00", "level": 1},
        {"label": "XVIII. Naudas izdevumi kopā.", "amount": "€ 1485987.00", "level": 0, "total": True},
    ]
    result = _declaration_detail_from_rows(rows)
    assert result["income_membership"] == 11602.0
    assert result["income_donations"] == 88847.0
    assert result["income_state_budget"] == 1120000.0
    assert result["income_total"] == 1316749.0
    assert result["expenses_total"] == 1487443.0
    # Collision guard: the income/expenses '5. Reklāmas' wins, not the cash-flow one
    assert result["expenses_advertising"] == 482102.0
    assert result["expenses_salaries"] == 139244.0
    # raw_data holds every euro row (including cash-flow), keyed by label
    import json
    raw = json.loads(result["raw_data"])
    assert raw["VII. Ieņēmumi kopā."] == 1316749.0


def test_declaration_detail_rows_election_declaration():
    """Election-declaration rows (I. Ieņēmumi / II. Izdevumi layout) do not
    match FIELD_MAP prefixes -> income_total stays None, raw_data populated.
    Matches legacy behaviour (Vēlēšanu deklarācija never got income_total).
    """
    from src.knab import _declaration_detail_from_rows
    rows = [
        {"label": "I. Ieņēmumi", "amount": "", "section": True},
        {"label": "1. Biedru naudas un iestāšanās naudas veidā saņemtie finanšu līdzekļi", "amount": "€ 374.00"},
        {"label": "IEŅĒMUMI KOPĀ (1 + 2 + 3)", "amount": "€ 3511.69", "total": True},
        {"label": "II. Izdevumi", "amount": "", "section": True},
        {"label": "IZDEVUMI KOPĀ (1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9)", "amount": "€ 5392.01", "total": True},
    ]
    result = _declaration_detail_from_rows(rows)
    assert result["income_total"] is None
    assert result["expenses_total"] is None
    import json
    raw = json.loads(result["raw_data"])
    assert raw["IEŅĒMUMI KOPĀ (1 + 2 + 3)"] == 3511.69


def test_declaration_detail_rows_all_zero_template():
    """KNAB's SPA serves an all-zero template for pre-2019 declarations it
    has no detail data for. An all-zero form must map to None financials
    (not 0.0) so the mismatch detector's IS NOT NULL filter skips it —
    0.0-as-declared raised 15 false criticals on 2026-07-24.
    """
    from src.knab import _declaration_detail_from_rows
    rows = [
        {"label": "Ieņēmumu un izdevumu pārskats", "amount": "", "section": True},
        {"label": "I. Biedru naudas un iestāšanās naudas.", "amount": "€ 0.00"},
        {"label": "II. Saņemtie dāvinājumi (ziedojumi).", "amount": "€ 0.00"},
        {"label": "VII. Ieņēmumi kopā.", "amount": "€ 0.00"},
        {"label": "X. Izdevumi kopā.", "amount": "€ 0.00"},
    ]
    result = _declaration_detail_from_rows(rows)
    assert result["income_total"] is None
    assert result["income_donations"] is None
    assert result["expenses_total"] is None
    import json
    assert json.loads(result["raw_data"])["VII. Ieņēmumi kopā."] == 0.0


def test_store_declarations_content_dedup(tmp_path):
    """Declarations dedup on (party, declaration_type, year): a legacy row with
    an old-format knab_id blocks a same-content API row with a public_id key.
    """
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    from src.knab import _store_declarations

    # Legacy-format row
    db.execute(
        """INSERT INTO knab_declarations
           (knab_id, party, declaration_type, year, date, detail_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("02042026-13692333", "\"PROGRESĪVIE\"", "Gada pārskats", 2024,
         "2026-04-02", "", "2026-04-08 00:00:00"),
    )
    db.commit()

    api_dup = [{
        "knab_id": "48eec15da32929cbac7ead9b9540cfe2",
        "party": "\"PROGRESĪVIE\"",
        "declaration_type": "Gada pārskats",
        "year": 2024,
        "date": "2026-04-02",
        "detail_url": "",
    }]
    new1 = _store_declarations(db, api_dup)
    assert new1 == 0, "content dedup on (party, type, year) must skip"

    # Different year -> inserts
    api_new = [{
        "knab_id": "newpublicid2025",
        "party": "\"PROGRESĪVIE\"",
        "declaration_type": "Gada pārskats",
        "year": 2025,
        "date": "2026-06-01",
        "detail_url": "",
    }]
    new2 = _store_declarations(db, api_new)
    assert new2 == 1
    db.close()


# `integration` was declared in pyproject.toml and applied to ZERO tests, while
# CI runs `-m "not integration and not slow"` — so half that filter selected
# nothing. This test is the one that genuinely hits a live external API, so it
# carries the marker and the filter clause becomes true (2026-08-15).
@pytest.mark.slow
@pytest.mark.integration
def test_live_fetch_one_declaration_page(tmp_path):
    """Integration: fetch a small slice of declarations from the live API."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    from src.knab import fetch_all_declarations
    new = fetch_all_declarations(db_path=db_path, per_page=50, max_pages=1)
    db = get_db(db_path)
    total = db.execute("SELECT COUNT(*) FROM knab_declarations").fetchone()[0]
    db.close()
    # `new >= 0` was always true for a count — an assertion that cannot fail.
    # On a FRESH db every stored row is new, so stored-count == reported-count
    # is the real invariant, and it is exactly the "silent success" check
    # CLAUDE.md asks for (a fetch that stores rows it does not report, or
    # reports rows it did not store, fails here). 0 is a valid value for both:
    # the tracked-party filter may legitimately match nothing in one page slice.
    assert total == new, (
        f"fetch reported {new} new declarations but {total} rows are stored — "
        "the counts must agree on a fresh database"
    )
