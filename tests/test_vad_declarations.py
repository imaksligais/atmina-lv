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


# ----- 2026-10-08: deklarācijas identitāte = etiķete + amats + iestāde -----
# Vecā atslēga (kind, year, position_title) bezgada deklarācijām deva year=None,
# tāpēc tā paša amata dažādu datumu deklarācijas saplūda (10-05 dry-run: 34/1136
# zaudētas). Identitāte tagad ir VID etiķete (nes datumu) + amats + iestāde.

_START_2009 = "Deklarācija, kuru iesniedz, stājoties amatā - 2009. gada 1. jūlijā"
_START_2011 = "Deklarācija, kuru iesniedz, stājoties amatā - 2011. gada 17. oktobrī"


def _seed_stored(db, label, institution, uuid):
    """Glabāta rinda tā, kā to atstāja vecā atslēga: kind='interim', year=NULL."""
    cur = db.execute(
        "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
        "declaration_kind, declaration_year, institution, position_title, "
        "submitted_at, source_url) VALUES (3, ?, ?, 'interim', NULL, ?, "
        "'Saeimas deputāts', ?, 'https://example.test')",
        (uuid, label, institution, uuid),
    )
    db.commit()
    return cur.lastrowid


def _row(label, uuid, institution="LATVIJAS REPUBLIKAS SAEIMA"):
    return SearchResultRow(vad_uuid=uuid, declaration_type=label, is_legacy=False,
                           institution=institution, position_title="Saeimas deputāts")


def test_undated_declarations_of_same_post_stay_distinct():
    """DB tur 2009. g. «stājoties amatā»; meklēšana dod to + 2011. g. tam pašam
    amatam → 2011. g. deklarācija ir JAUNA, nevis «jau ir»."""
    db, path = _make_db()
    try:
        _seed_stored(db, _START_2009, "Latvijas Republikas Saeima", "old-2009")
        client = MagicMock()
        client.search.return_value = [_row(_START_2009, "u1"), _row(_START_2011, "u2")]
        result = fetch_for_politician(3, db, client, dry_run=True)
        assert (result.already_present, result.new_inserted) == (1, 1), result
    finally:
        db.close()
        _safe_unlink(path)


def test_empty_stored_institution_matches_and_uuid_refresh_hits_only_that_row():
    """Vecākām deklarācijām glabātā iestāde ir '' (detaļu galvenē tās nebija), bet
    meklēšanas rindai iestāde ir → tā pati deklarācija, ne jauna. vad_uuid
    atsvaidzina TIKAI atbilstošo rindu, ne citu tā paša amata bezgada rindu."""
    db, path = _make_db()
    try:
        id_2009 = _seed_stored(db, _START_2009, "", "old-2009")
        id_2011 = _seed_stored(db, _START_2011, "", "old-2011")
        client = MagicMock()
        client.search.return_value = [_row(_START_2009, "fresh-2009")]
        client.fetch_detail.return_value = FIXTURE_HTML
        result = fetch_for_politician(3, db, client)
        assert (result.already_present, result.new_inserted) == (1, 0), result
        uuids = dict(db.execute(
            "SELECT id, vad_uuid FROM vad_declarations WHERE opponent_id=3").fetchall())
        assert uuids == {id_2009: "fresh-2009", id_2011: "old-2011"}
    finally:
        db.close()
        _safe_unlink(path)


def test_unresolvable_rows_are_counted_not_silent():
    """Viena glabātā rinda ar tukšu iestādi + divas meklēšanas rindas ar dažādām
    iestādēm → otrā ir neviennozīmīga; identiska bezdatuma rinda → dublikāts.
    Abas saskaitītas, un uzskaites vienādība sanāk."""
    db, path = _make_db()
    try:
        _seed_stored(db, _START_2009, "", "old-2009")
        client = MagicMock()
        client.search.return_value = [
            _row(_START_2009, "a", institution="IESTĀDE A"),
            _row(_START_2009, "b", institution="IESTĀDE B"),
            _row(_START_2009, "c", institution="IESTĀDE A"),
        ]
        result = fetch_for_politician(3, db, client, dry_run=True)
        assert result.already_present == 1
        assert result.rows_ambiguous == 1
        assert result.rows_duplicate_label == 1
        assert result.new_inserted == 0
        assert result.rows_found == 3
    finally:
        db.close()
        _safe_unlink(path)


def test_resweep_dryrun_script_reads_only_and_lists_new_labels(capsys):
    """scripts/vad_resweep_dryrun.py atver DB `mode=ro`; jebkurš raksts dry-run
    ceļā izmestu «readonly database» → [fail] + exit 1."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "vad_resweep_dryrun",
        Path(__file__).resolve().parents[1] / "scripts" / "vad_resweep_dryrun.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    db, path = _make_db()
    try:
        _seed_stored(db, _START_2009, "", "old-2009")
        db.close()
        client = MagicMock()
        client.search.return_value = [_row(_START_2009, "u1"), _row(_START_2011, "u2")]
        rc = mod.main(["--pids", "3"], client=client, db_path=path)
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "already_present=1 new_inserted=1" in out
        assert f"+ {_START_2011} |" in out
        assert _START_2009 not in out.split("[total]")[0].split("new_inserted=1")[1]
    finally:
        _safe_unlink(path)
