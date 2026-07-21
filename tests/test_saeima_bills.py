"""Phase 1A unit tests — saeima_bills schema, helpers, and backfill prep."""

import os
import sqlite3
import tempfile

import pytest

from src.db import init_db, get_db
from src.saeima import (
    init_saeima_bills,
    init_saeima_tables,
    _VALID_BILL_TYPES,
    _VALID_STAGE_NAMES,
    _canonicalize_stage_name,
    resolve_bill_from_motif,
    _reading_from_motif,
    _resolve_base_law_slug,
    upsert_bill,
    append_bill_stage,
    match_submitters_to_politicians,
    parse_agenda_snapshot,
    AgendaBill,
)


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)  # sessions, agenda_items, votes, individual_votes
    yield path
    _safe_unlink(path)


class TestSchema:
    def test_init_saeima_bills_creates_three_tables(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('saeima_bills', 'saeima_bill_stages', 'saeima_bill_politicians')"
        ).fetchall()}
        db.close()
        assert tables == {"saeima_bills", "saeima_bill_stages", "saeima_bill_politicians"}

    def test_init_saeima_bills_adds_bill_id_to_votes(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        cols = [row[1] for row in db.execute("PRAGMA table_info(saeima_votes)").fetchall()]
        db.close()
        assert "bill_id" in cols

    def test_init_saeima_bills_creates_indexes(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        indexes = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name IN ('idx_bills_document_nr', 'idx_bills_topic', 'idx_bills_status', "
            "'idx_bill_stages_bill_id', 'idx_bill_stages_vote_id', 'idx_bill_stages_kind', "
            "'idx_bill_politicians_bill_id', 'idx_bill_politicians_politician_id', "
            "'idx_saeima_votes_bill_id')"
        ).fetchall()}
        db.close()
        assert len(indexes) == 9

    def test_init_saeima_bills_idempotent(self, empty_db):
        init_saeima_bills(empty_db)
        init_saeima_bills(empty_db)  # second call should not raise
        db = get_db(empty_db)
        count = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
        db.close()
        assert count == 0

    def test_stage_kind_default_is_vote(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        db.execute(
            "INSERT INTO saeima_bills (document_nr, bill_type, title) "
            "VALUES ('1/Lp14', 'Lp14', 'Test')"
        )
        bill_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO saeima_bill_stages (bill_id, stage_name, stage_date) "
            "VALUES (?, 'iesniegts', '2026-01-01')",
            (bill_id,)
        )
        kind = db.execute(
            "SELECT stage_kind FROM saeima_bill_stages WHERE bill_id=?",
            (bill_id,)
        ).fetchone()[0]
        db.commit()
        db.close()
        assert kind == "vote"


class TestValidation:
    def test_valid_bill_types(self):
        assert _VALID_BILL_TYPES == frozenset({"Lp14", "Lm14", "P14"})

    def test_valid_stage_names_includes_all_canonical(self):
        expected = {
            "iesniegts", "1.lasījums", "2.lasījums", "2.lasījums priekšlikums",
            "3.lasījums", "3.lasījums priekšlikums", "atgriezts komisijā",
            "atsaukts", "tiesneša_amats", "procesuāls", "Lm14 cits",
            "paziņojuma_balsojums", "nezināms",
        }
        assert _VALID_STAGE_NAMES == frozenset(expected)

    def test_canonicalize_stage_name_passes_canonical(self):
        assert _canonicalize_stage_name("1.lasījums") == "1.lasījums"
        assert _canonicalize_stage_name("tiesneša_amats") == "tiesneša_amats"

    def test_canonicalize_stage_name_strips_whitespace(self):
        assert _canonicalize_stage_name("  iesniegts ") == "iesniegts"

    def test_canonicalize_stage_name_rejects_unknown(self):
        with pytest.raises(ValueError, match="Unknown stage_name"):
            _canonicalize_stage_name("not_a_stage")

    def test_canonicalize_stage_name_rejects_empty(self):
        with pytest.raises(ValueError):
            _canonicalize_stage_name("")


class TestResolveBillFromMotif:
    @pytest.mark.parametrize("motif,expected", [
        # --- baseline positive cases ---
        ("Grozījumi Valsts aizsardzības finansēšanas likumā (1315/Lp14), 3.lasījums", "1315/Lp14"),
        ("Kapsētu likums (1032/Lp14), 3.lasījums", "1032/Lp14"),
        ("Par Madaras Šenbrūnas iecelšanu par tiesnesi (939/Lm14)", "939/Lm14"),
        ("Par dronu uzbrukumiem (125/P14)", "125/P14"),
        # --- optional-paren variants ---
        ("Par paziņojumu par dronu uzbrukumiem 127/P14", "127/P14"),       # unparenthesized P14
        ("Grozījumi Imigrācijas likumā (1315/Lp14)", "1315/Lp14"),          # parenthesized Lp14 (regression)
        ("Lēmums par tiesneša iecelšanu 952 / Lm14", "952/Lm14"),           # whitespace around slash
        ("Par paziņojumu (127/P14", "127/P14"),                             # asymmetric: opening paren only
        ("Par paziņojumu 127/P14)", "127/P14"),                             # asymmetric: closing paren only
        ("127/P14X", "127/P14"),                                            # trailing letter outside fixed alternation
        # --- negative cases ---
        ("motif bez document_nr", None),
        ("Lp14 in text but not parenthesized", None),
        ("Procedurāls bez doc_nr", None),
        ("abc127/P14", None),                                               # left-boundary: leading word chars block match
        ("about /P14 maybe", None),                                         # no digits before slash
    ])
    def test_extracts_document_nr(self, motif, expected):
        assert resolve_bill_from_motif(motif) == expected


class TestReadingFromMotif:
    @pytest.mark.parametrize("motif,expected", [
        ("Grozījumi X (1315/Lp14), 1.lasījums", "1.lasījums"),
        ("Grozījumi X (1315/Lp14), 2.lasījums, steidzams", "2.lasījums"),
        ("Grozījumi X (1315/Lp14), 3.lasījums", "3.lasījums"),
        ("Grozījumi X (1315/Lp14), 2. lasījums, priekšlikums Nr.5", "2.lasījums priekšlikums"),
        ("Par Madaras Šenbrūnas iecelšanu par tiesnesi (939/Lm14)", "tiesneša_amats"),
        ("Par tiesneša X atbrīvošanu no amata (940/Lm14)", "tiesneša_amats"),
        ("Par termiņa pagarināšanu likumprojektam X (123/Lm14)", "procesuāls"),
        ("Par līdzatbildīgās komisijas noteikšanu (124/Lm14)", "procesuāls"),
        ("Par X paziņojumu (125/P14)", "paziņojuma_balsojums"),
        ("Par Air Baltic aizdevumu (953/Lm14)", "Lm14 cits"),
        ("Grozījumi Izglītības likumā (1278/Lp14), nodošana komisijām", "iesniegts"),
        ("Grozījumi X (777/Lp14), nodošana komisijai", "iesniegts"),
        ("motif bez atbilstības", "nezināms"),
    ])
    def test_classification(self, motif, expected):
        assert _reading_from_motif(motif) == expected

    def test_priority_lasijum_wins_over_lm14(self):
        # Hypothetical motif containing both '3.lasījums' and '/Lm14' — rule 1 wins
        assert _reading_from_motif("Lēmuma X (501/Lm14), 3.lasījums") == "3.lasījums"


class TestResolveBaseLawSlug:
    @pytest.fixture
    def laws_index(self):
        return {
            "udens-apsaimniekosanas-likums": "Ūdens apsaimniekošanas likums",
            "celu-satiksmes-likums": "Ceļu satiksmes likums",
            "valsts-aizsardzibas-finansesanas-likums": "Valsts aizsardzības finansēšanas likums",
        }

    def test_exact_title_match(self, laws_index):
        assert _resolve_base_law_slug(
            "Ūdens apsaimniekošanas likuma jautājumā", laws_index
        ) == "udens-apsaimniekosanas-likums"

    def test_grozijumi_pattern_match(self, laws_index):
        assert _resolve_base_law_slug(
            "Grozījumi Ceļu satiksmes likumā (1234/Lp14)", laws_index
        ) == "celu-satiksmes-likums"

    def test_unknown_law_returns_none(self, laws_index):
        assert _resolve_base_law_slug("Jauns nezināms likums", laws_index) is None

    def test_case_insensitive(self, laws_index):
        assert _resolve_base_law_slug(
            "GROZĪJUMI VALSTS AIZSARDZĪBAS FINANSĒŠANAS LIKUMĀ", laws_index
        ) == "valsts-aizsardzibas-finansesanas-likums"


@pytest.fixture
def bills_db(empty_db):
    """DB with bills schema initialized + a known politician.

    Reuses the `empty_db` fixture which already calls init_saeima_tables.
    Adds init_saeima_bills + one politician row.
    """
    init_saeima_bills(empty_db)
    db = get_db(empty_db)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) VALUES "
        "(1, 'Test Deputāts', 'JV')"
    )
    db.commit()
    db.close()
    return empty_db


class TestUpsertBill:
    def test_inserts_new_bill(self, bills_db):
        bid = upsert_bill(bills_db, "1315/Lp14", "Grozījumi X likumā", "Lp14")
        assert bid > 0
        db = get_db(bills_db)
        row = db.execute("SELECT * FROM saeima_bills WHERE id=?", (bid,)).fetchone()
        db.close()
        assert row["document_nr"] == "1315/Lp14"
        assert row["bill_type"] == "Lp14"

    def test_idempotent_on_document_nr(self, bills_db):
        bid1 = upsert_bill(bills_db, "1315/Lp14", "Title v1", "Lp14")
        bid2 = upsert_bill(bills_db, "1315/Lp14", "Title v2", "Lp14")
        assert bid1 == bid2
        db = get_db(bills_db)
        count = db.execute(
            "SELECT COUNT(*) FROM saeima_bills WHERE document_nr=?", ("1315/Lp14",)
        ).fetchone()[0]
        title = db.execute(
            "SELECT title FROM saeima_bills WHERE document_nr=?", ("1315/Lp14",)
        ).fetchone()[0]
        db.close()
        assert count == 1
        assert title == "Title v2"

    def test_validates_bill_type(self, bills_db):
        with pytest.raises(ValueError, match="bill_type"):
            upsert_bill(bills_db, "1/Xx99", "Bad", "Xx99")

    def test_accepts_p14(self, bills_db):
        bid = upsert_bill(bills_db, "127/P14", "Par dronu uzbrukumiem", "P14")
        db = get_db(bills_db)
        bt = db.execute("SELECT bill_type FROM saeima_bills WHERE id=?", (bid,)).fetchone()[0]
        db.close()
        assert bt == "P14"


class TestAppendBillStage:
    def test_appends_stage_and_updates_current(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        sid = append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-04-01")
        assert sid > 0
        db = get_db(bills_db)
        bill = db.execute(
            "SELECT current_stage, current_status FROM saeima_bills WHERE id=?",
            (bid,)
        ).fetchone()
        db.close()
        assert bill["current_stage"] == "1.lasījums"
        # 1.lasījums + pieņemts → still 'procesā' (only 3.lasījums + pieņemts marks final)
        assert bill["current_status"] == "procesā"

    def test_validates_stage_name(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        with pytest.raises(ValueError, match="Unknown stage_name"):
            append_bill_stage(bills_db, bid, "bogus_stage", "pieņemts", "2026-04-01")

    def test_status_mapping_case_insensitive(self, bills_db):
        """stage_result is stored capitalized ('Pieņemts'/'Noraidīts') by the parser;
        the denorm logic must compare case-insensitively or the final-status mapping
        silently fails (regression discovered post-merge backfill)."""
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "3.lasījums", "Pieņemts", "2026-04-01")
        db = get_db(bills_db)
        status = db.execute(
            "SELECT current_status FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert status == "pieņemts"

    def test_status_mapping_noraidits_capitalized(self, bills_db):
        bid = upsert_bill(bills_db, "2/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "1.lasījums", "Noraidīts", "2026-04-01")
        db = get_db(bills_db)
        status = db.execute(
            "SELECT current_status FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert status == "noraidīts"

    def test_current_stage_follows_latest_by_date(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-03-01")
        append_bill_stage(bills_db, bid, "2.lasījums", "pieņemts", "2026-04-01")
        append_bill_stage(bills_db, bid, "3.lasījums", "pieņemts", "2026-05-01")
        db = get_db(bills_db)
        cs = db.execute(
            "SELECT current_stage FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert cs == "3.lasījums"

    def test_atomic_writes_vote_bill_id(self, bills_db):
        """CLAUDE.md invariant #12: append_bill_stage is the SOLE writer to
        saeima_votes.bill_id. When vote_id is supplied, the vote's bill_id
        is bound to the parent bill atomically (same transaction as the stage
        row + bill UPDATE). Pre-2026-05-16 the function wrote stages and
        bills.current_stage but silently skipped saeima_votes.bill_id, forcing
        @saeima-tracker to manually fix up after every run."""
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        db = get_db(bills_db)
        cur = db.execute(
            "INSERT INTO saeima_votes (motif, vote_date, result) "
            "VALUES ('Par testa balsojumu', '2026-04-01', 'Pieņemts')"
        )
        vote_id = cur.lastrowid
        db.commit()
        # Pre-condition: vote.bill_id is NULL (just inserted, no binding yet)
        pre = db.execute(
            "SELECT bill_id FROM saeima_votes WHERE id=?", (vote_id,)
        ).fetchone()["bill_id"]
        db.close()
        assert pre is None

        append_bill_stage(
            bills_db, bid, "1.lasījums", "pieņemts", "2026-04-01",
            vote_id=vote_id,
        )

        db = get_db(bills_db)
        post = db.execute(
            "SELECT bill_id FROM saeima_votes WHERE id=?", (vote_id,)
        ).fetchone()["bill_id"]
        db.close()
        assert post == bid

    def test_skips_vote_bill_id_when_vote_id_none(self, bills_db):
        """No vote_id supplied (e.g. a debate/commission stage) → no UPDATE
        on saeima_votes. Verify by inserting an unrelated vote row and
        confirming its bill_id stays NULL after a no-vote-id stage append."""
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        db = get_db(bills_db)
        cur = db.execute(
            "INSERT INTO saeima_votes (motif, vote_date) "
            "VALUES ('Cits balsojums', '2026-04-01')"
        )
        unrelated_vote = cur.lastrowid
        db.commit()
        db.close()

        append_bill_stage(
            bills_db, bid, "1.lasījums", "pieņemts", "2026-04-01",
            # vote_id intentionally None
        )

        db = get_db(bills_db)
        bid_col = db.execute(
            "SELECT bill_id FROM saeima_votes WHERE id=?", (unrelated_vote,)
        ).fetchone()["bill_id"]
        db.close()
        assert bid_col is None  # not touched

    def test_atomic_rollback_on_invalid_stage(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-03-01")
        with pytest.raises(ValueError):
            append_bill_stage(bills_db, bid, "bogus", "pieņemts", "2026-04-01")
        db = get_db(bills_db)
        cs = db.execute(
            "SELECT current_stage FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        rows = db.execute(
            "SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert cs == "1.lasījums"
        assert rows == 1  # bogus row not persisted


@pytest.fixture
def submitter_db(bills_db):
    """Adds 3 known politicians with name_forms to bills_db."""
    db = get_db(bills_db)
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party, name_forms) VALUES (?, ?, ?, ?)",
        [
            (10, "Maija Armaņeva", "PRO", '["Maija Armaņeva", "Armaņeva"]'),
            (11, "Andris Šuvajevs", "PRO", '["Andris Šuvajevs", "Šuvajevs"]'),
            (12, "Krišjānis Feldmans", "JV", '["Krišjānis Feldmans", "Feldmans"]'),
        ],
    )
    db.commit()
    db.close()
    return bills_db


class TestMatchSubmitters:
    def test_matches_known_deputies(self, submitter_db):
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        matched, unmatched = match_submitters_to_politicians(
            submitter_db, bid, ["Maija Armaņeva", "Šuvajevs", "Feldmans"]
        )
        assert matched == 3
        assert unmatched == []
        db = get_db(submitter_db)
        rows = db.execute(
            "SELECT politician_id, role FROM saeima_bill_politicians WHERE bill_id=?",
            (bid,),
        ).fetchall()
        db.close()
        assert len(rows) == 3
        assert {r["politician_id"] for r in rows} == {10, 11, 12}
        assert all(r["role"] == "submitter" for r in rows)

    def test_reports_unmatched(self, submitter_db):
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        matched, unmatched = match_submitters_to_politicians(
            submitter_db, bid, ["Maija Armaņeva", "Nezināms Deputāts"]
        )
        assert matched == 1
        assert unmatched == ["Nezināms Deputāts"]

    def test_idempotent_via_explicit_check(self, submitter_db):
        # Idempotency comes from SELECT-before-INSERT (not from UNIQUE constraint).
        # SQLite UNIQUE with NULL amendment_nr treats each NULL as distinct, so
        # the constraint alone wouldn't prevent duplicate (bill_id, politician_id, role) rows.
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        match_submitters_to_politicians(submitter_db, bid, ["Maija Armaņeva"])
        match_submitters_to_politicians(submitter_db, bid, ["Maija Armaņeva"])
        db = get_db(submitter_db)
        count = db.execute(
            "SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert count == 1  # UNIQUE(bill_id, politician_id, role, amendment_nr) wins


class TestParseAgendaSynthetic:
    def test_extracts_lp14_bill_with_individual_submitters(self):
        snapshot = """
        [some agenda noise]
        Likumprojekts Grozījumi Imigrācijas likumā (1234/Lp14)
        Iesniedzēji: Deputāti Maija Armaņeva, Andris Šuvajevs
        [more noise]
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        b = bills[0]
        assert b.document_nr == "1234/Lp14"
        assert b.bill_type == "Lp14"
        assert "Imigrācijas" in b.title
        assert "Maija Armaņeva" in b.individual_submitters
        assert "Andris Šuvajevs" in b.individual_submitters
        assert b.institutional_submitter is None

    def test_extracts_lm14_with_institutional_submitter(self):
        snapshot = """
        Lēmuma projekts Par Air Baltic aizdevumu (953/Lm14)
        Iesniedzējs: Ministru kabinets
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        b = bills[0]
        assert b.document_nr == "953/Lm14"
        assert b.bill_type == "Lm14"
        assert b.institutional_submitter == "Ministru kabinets"
        assert b.individual_submitters == []

    def test_extracts_p14_bill(self):
        snapshot = """
        Paziņojums Par dronu uzbrukumiem (125/P14)
        Iesniedzēji: Deputāti Imants Parādnieks
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        assert bills[0].bill_type == "P14"

    def test_skips_unknown_document_nr_suffix(self):
        snapshot = "Some doc (999/Xx99)\nIesniedzējs: Test"
        bills = parse_agenda_snapshot(snapshot)
        assert bills == []


def test_mk_bill_followed_by_deputy_bill_does_not_inherit_deputies():
    """Regression: parse_agenda_snapshot's 500-char lookahead window must NOT
    cross into the next bill's text. 2026-04-27 live smoke caught 4 MK bills
    incorrectly receiving the deputy submitters of the following bill.
    """
    from src.saeima import parse_agenda_snapshot

    # MK bill (1320) immediately followed by a deputy-submitted bill (1322).
    # MK bill window must NOT pick up "Deputāti A, B, C" from 1322.
    snapshot = (
        "Likumprojekts Grozījumi Notariāta likumā (1320/Lp14)\n"
        "Iesniedzējs: Ministru kabinets\n"
        "Likumprojekts Grozījumi Valsts fondēto pensiju likumā (1322/Lp14)\n"
        "Deputāti Nauris Puntulis, Ilze Indriksone, Artūrs Butāns\n"
    )

    bills = parse_agenda_snapshot(snapshot)
    assert len(bills) == 2
    bill_1320 = next(b for b in bills if b.document_nr == "1320/Lp14")
    bill_1322 = next(b for b in bills if b.document_nr == "1322/Lp14")

    # 1320 (MK) should NOT have any individual submitters.
    assert bill_1320.institutional_submitter == "Ministru kabinets"
    assert bill_1320.individual_submitters == [], (
        f"MK bill 1320 leaked submitters from 1322: {bill_1320.individual_submitters!r}"
    )
    # 1322 (deputies) should still have its own list intact.
    assert bill_1322.institutional_submitter is None
    assert "Nauris Puntulis" in bill_1322.individual_submitters
    assert len(bill_1322.individual_submitters) == 3
