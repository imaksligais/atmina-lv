import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.vad.declarations import fetch_for_politician
from src.vad.fetch import SearchResultRow
from src.vad.schema import init_vad_tables

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "vad" / "slesers-2024.html").read_text(encoding="utf-8")


def _safe_unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            keywords TEXT DEFAULT '[]',
            negative_patterns TEXT
        );
        INSERT INTO tracked_politicians(id, name, role) VALUES (3, 'Ainārs Šlesers', 'Saeimas deputāts');
    """)
    db.commit()
    init_vad_tables(path)
    return db, path


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
    db, path = _make_db()
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 1
        assert result.already_present == 0
        decl = db.execute("SELECT * FROM vad_declarations WHERE opponent_id=3").fetchone()
        assert decl is not None
        assert decl["vad_uuid"] == "uuid-2024"
        assert decl["declaration_kind"] == "annual"
        assert decl["declaration_year"] == 2024
        assert "%C5%A0lesers" in decl["source_url"] or "Šlesers" in decl["source_url"]
        n_pos = db.execute("SELECT COUNT(*) FROM vad_positions WHERE declaration_id=?", (decl["id"],)).fetchone()[0]
        assert n_pos == 4
        n_inc = db.execute("SELECT COUNT(*) FROM vad_income WHERE declaration_id=?", (decl["id"],)).fetchone()[0]
        assert n_inc == 4
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_for_politician_idempotent_on_natural_key():
    """Second call sees existing natural key, refreshes vad_uuid, skips detail fetch."""
    db, path = _make_db()
    try:
        client1 = _mock_client_with_one_row()
        fetch_for_politician(3, db, client1)
        # Second call returns search row with DIFFERENT vad_uuid (rotation)
        client2 = MagicMock()
        client2.search.return_value = [
            SearchResultRow(
                vad_uuid="uuid-rotated-XYZ",  # different UUID, same natural key
                declaration_type="Kārtējā gada deklarācija - par 2024. gadu",
                is_legacy=False, institution="Latvijas Republikas Saeima",
                position_title="Saeimas deputāts",
            )
        ]
        client2.fetch_detail.return_value = FIXTURE_HTML
        result2 = fetch_for_politician(3, db, client2)
        assert result2.new_inserted == 0
        assert result2.already_present == 1
        # detail must NOT be re-fetched
        client2.fetch_detail.assert_not_called()
        # Only ONE row exists (natural key dedup worked)
        n = db.execute("SELECT COUNT(*) FROM vad_declarations WHERE opponent_id=3").fetchone()[0]
        assert n == 1
        # vad_uuid was refreshed to latest seen
        uuid_now = db.execute("SELECT vad_uuid FROM vad_declarations WHERE opponent_id=3").fetchone()["vad_uuid"]
        assert uuid_now == "uuid-rotated-XYZ"
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_for_politician_lenient_role_post_2026_05_02_fix():
    """Post-2026-05-02 fix: role_matches always-True. Old test expected
    skip on "Žurnālists" role; production smoke (Pūpols, Kleinbergs)
    showed role-keyword overlap dod false-negatives. We trust full
    Vārds+Uzvārds search uniqueness.
    """
    db, path = _make_db()
    try:
        db.execute("UPDATE tracked_politicians SET role='Žurnālists' WHERE id=3")
        db.commit()
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.rows_skipped_role == 0
        assert result.new_inserted == 1
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_for_politician_skips_legacy():
    db, path = _make_db()
    try:
        client = MagicMock()
        client.search.return_value = [
            SearchResultRow(vad_uuid="legacy-1", declaration_type="par 2008. gadu",
                            is_legacy=True, institution="Latvijas Republikas Saeima",
                            position_title="Saeimas deputāts"),
        ]
        result = fetch_for_politician(3, db, client)
        assert result.rows_skipped_legacy == 1
        assert result.new_inserted == 0
    finally:
        db.close()
        _safe_unlink(path)


def test_dry_run_does_not_write():
    db, path = _make_db()
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client, dry_run=True)
        assert result.new_inserted == 1
        n = db.execute("SELECT COUNT(*) FROM vad_declarations").fetchone()[0]
        assert n == 0
    finally:
        db.close()
        _safe_unlink(path)


# ----- Phase 1.5: vad_disambig filter tests -----


def _make_db_with_keywords(keywords: list[str], negative_patterns: list[str] | None = None):
    """Like _make_db, but populates pid 3's vad_disambig + neg_patterns."""
    db, path = _make_db()
    db.execute(
        "UPDATE tracked_politicians SET keywords=?, negative_patterns=? WHERE id=3",
        (
            json.dumps({"vad_disambig": keywords}),
            json.dumps(negative_patterns) if negative_patterns else None,
        ),
    )
    db.commit()
    return db, path


def test_disambig_accepts_row_with_substring_match():
    """vad_disambig=['Saeimas deputāts'] → row ar position='Saeimas deputāts' tiek pieņemts."""
    db, path = _make_db_with_keywords(["Saeimas deputāts"])
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 1
        assert result.rows_skipped_role == 0
    finally:
        db.close()
        _safe_unlink(path)


def test_disambig_rejects_row_without_match():
    """vad_disambig=['Ministru kabinets'] (substring no row institution/position) → reject."""
    db, path = _make_db_with_keywords(["Ministru kabinets"])
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 0
        assert result.rows_skipped_role == 1
    finally:
        db.close()
        _safe_unlink(path)


def test_disambig_negative_pattern_overrides_positive():
    """vad_disambig match BUT negative_patterns also match → reject (negative wins)."""
    db, path = _make_db_with_keywords(
        keywords=["Saeimas deputāts"],
        negative_patterns=["Latvijas Republikas Saeima"],
    )
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 0
        assert result.rows_skipped_role == 1
    finally:
        db.close()
        _safe_unlink(path)


def test_disambig_empty_hints_passes_through():
    """vad_disambig=[] vai NULL → trust full-name search, accept all rows (current behaviour)."""
    db, path = _make_db_with_keywords([])  # explicit empty
    try:
        client = _mock_client_with_one_row()
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 1
        assert result.rows_skipped_role == 0
    finally:
        db.close()
        _safe_unlink(path)


def test_disambig_hints_pass_accept_row_to_search():
    """Ar vad_disambig hints → search() saņem accept_row predikātu (institūcijas-
    aware lapošana homonīmu robam, BACKLOG [FIX] Inga Bērziņa). Predikāts pieņem
    Saeimas rindu un noraida homonīmu."""
    db, path = _make_db_with_keywords(["Latvijas Republikas Saeima"])
    try:
        client = _mock_client_with_one_row()
        fetch_for_politician(3, db, client)
        # accept_row padots kā kwarg
        _, kwargs = client.search.call_args
        accept = kwargs.get("accept_row")
        assert accept is not None
        saeima = SearchResultRow(
            vad_uuid="x", declaration_type="par 2024. gadu", is_legacy=False,
            institution="Latvijas Republikas Saeima", position_title="deputāts",
        )
        homonym = SearchResultRow(
            vad_uuid="y", declaration_type="par 2024. gadu", is_legacy=False,
            institution="Vidzemes slimnīca", position_title="ārsts",
        )
        assert accept(saeima) is True
        assert accept(homonym) is False
    finally:
        db.close()
        _safe_unlink(path)


def test_no_disambig_hints_passes_none_accept_row():
    """Bez hints → accept_row=None (search apstājas pie parastā bound, kā vienmēr)."""
    db, path = _make_db_with_keywords([])  # explicit empty
    try:
        client = _mock_client_with_one_row()
        fetch_for_politician(3, db, client)
        _, kwargs = client.search.call_args
        assert kwargs.get("accept_row") is None
    finally:
        db.close()
        _safe_unlink(path)


# ----- Phase 1.5: parse-fail retry tests -----


def test_fetch_for_politician_retries_on_parse_fail():
    """Parse fail (no header table) → reset session, re-search, fetch with new UUID."""
    db, path = _make_db()
    try:
        client = MagicMock()
        first_row = SearchResultRow(
            vad_uuid="stale-uuid",
            declaration_type="Kārtējā gada deklarācija - par 2024. gadu",
            is_legacy=False, institution="Latvijas Republikas Saeima",
            position_title="Saeimas deputāts",
        )
        fresh_row = SearchResultRow(
            vad_uuid="fresh-uuid",
            declaration_type="Kārtējā gada deklarācija - par 2024. gadu",
            is_legacy=False, institution="Latvijas Republikas Saeima",
            position_title="Saeimas deputāts",
        )
        client.search.side_effect = [[first_row], [fresh_row]]
        broken_html = "<html><body>Anti-scrape redirect</body></html>"
        client.fetch_detail.side_effect = [broken_html, FIXTURE_HTML]
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 1, result
        assert client.reset_session.called
        assert client.search.call_count == 2
        # Stored row uses fresh UUID
        uuid = db.execute("SELECT vad_uuid FROM vad_declarations WHERE opponent_id=3").fetchone()[0]
        assert uuid == "fresh-uuid"
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_for_politician_retry_logs_warn_when_no_fresh_match():
    """Parse fail + retry search returns NO matching natural-key row → log warn, append error, continue."""
    db, path = _make_db()
    try:
        client = MagicMock()
        first_row = SearchResultRow(
            vad_uuid="stale-uuid",
            declaration_type="Kārtējā gada deklarācija - par 2024. gadu",
            is_legacy=False, institution="Latvijas Republikas Saeima",
            position_title="Saeimas deputāts",
        )
        # Retry search returns DIFFERENT position → natural-key mismatch
        unrelated_row = SearchResultRow(
            vad_uuid="unrelated-uuid",
            declaration_type="Kārtējā gada deklarācija - par 2023. gadu",
            is_legacy=False, institution="Latvijas Republikas Saeima",
            position_title="Saeimas deputāts",
        )
        client.search.side_effect = [[first_row], [unrelated_row]]
        client.fetch_detail.side_effect = [
            "<html><body>broken</body></html>",  # first parse fail
        ]
        result = fetch_for_politician(3, db, client)
        assert result.new_inserted == 0
        assert len(result.errors) == 1
        assert "stale-uuid" in result.errors[0]
    finally:
        db.close()
        _safe_unlink(path)
