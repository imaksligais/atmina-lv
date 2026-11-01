"""Tests for `document_politicians.suspect_at` — the same-URL overwrite flag.

Coverage contract for `insert_document`'s URL-first UPDATE branch
(src/db.py::_reconcile_junction_suspects):

* A junction row the NEW content no longer justifies is FLAGGED, never
  deleted — including and especially when the new text is SHORTER (the
  truncated-extraction trap: audit 2026-09-22, docs 42838/44422, where the
  live article still contains every "stale" name).
* The flag clears when justification returns (name back in text, caller's
  fresh links, manual re-link, matcher rescan).
* Source-justified rows (institution relationship_type, surname in URL slug)
  are never flagged.
* The flag timestamp is first-detection — re-overwrites must not churn it.

Hermetic: temp DB via init_db; `src.db.DB_PATH` is monkeypatched so the
matcher's `_load_politician_forms()` resolves the fixture DB, and the
matcher cache is cleared around each test.
"""

import json
import sqlite3

import pytest

import src.db as db_mod
import src.matcher as matcher_mod
from src.db import (
    get_db,
    init_db,
    insert_document,
    link_politician_to_document,
)

URL = "https://www.lsm.lv/raksts/zinas/latvija/edited-article.a000000/"
URL_VIEDOKLIS = "https://nra.lv/viedokli/alvis-hermanis/517638-viedoklis.htm"

PID_TESTS = 10   # "Jānis Tests" — tracked, surname forms auto-derived
PID_ORG = 11     # "Mediju Aģentūra" — organization (source-justified)
PID_HERMANIS = 12  # "Alvis Hermanis" — surname in the viedokli URL slug

TEXT_WITH_TESTS = (
    "Saeimas debatēs Jānis Tests kritizēja valdības plānus. "
    "Par Testu izteicās arī opozīcija. " * 6
)
TEXT_WITHOUT_TESTS_LONG = (
    "Saeima ceturtdien apstiprināja budžeta likumprojektu bez debatēm. "
    "Frakciju pārstāvji runāja par nodokļiem, ceļiem un skolām. " * 10
)
TEXT_WITHOUT_TESTS_SHORT = "Saeima apstiprināja likumprojektu."


def _junction(db, doc_id):
    return db.execute(
        "SELECT politician_id, role, suspect_at FROM document_politicians "
        "WHERE document_id = ?",
        (doc_id,),
    ).fetchall()


@pytest.fixture
def pol_db(tmp_path, monkeypatch):
    """Temp DB seeded with three tracked rows; matcher reads THIS db."""
    path = str(tmp_path / "atmina_test.db")
    init_db(path)
    seed = get_db(path)
    seed.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (PID_TESTS, "Jānis Tests", json.dumps(["Jānis Tests", "Tests"]), "tracked"),
    )
    seed.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (PID_ORG, "Mediju Aģentūra", json.dumps(["Mediju Aģentūra"]), "organization"),
    )
    seed.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (PID_HERMANIS, "Alvis Hermanis",
         json.dumps(["Alvis Hermanis", "Hermanis"]), "tracked"),
    )
    seed.commit()
    seed.close()
    # get_db() inside _load_politician_forms / link_politician_to_document /
    # link_politicians_to_documents resolves DB_PATH at call time.
    monkeypatch.setattr(db_mod, "DB_PATH", path)
    matcher_mod._clear_politician_cache()
    yield path
    matcher_mod._clear_politician_cache()


def test_suspect_at_column_exists(pol_db):
    db = get_db(pol_db)
    cols = {r[1] for r in db.execute("PRAGMA table_info(document_politicians)")}
    db.close()
    assert "suspect_at" in cols


def test_shorter_overwrite_flags_but_never_deletes(pol_db):
    """THE TRUNCATION TRAP — the case that must never delete.

    v1 links pid 10 (text names him). v2 is a SHORTER, truncated extraction
    that lacks the name — exactly the doc-42838/44422 shape, where the live
    article still contains the person. The row must survive and be flagged.
    """
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    again = insert_document(
        content=TEXT_WITHOUT_TESTS_SHORT, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    assert again == doc_id

    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert [(r["politician_id"], r["role"]) for r in rows] == [(PID_TESTS, "subject")], (
        "a shorter re-fetch must NEVER delete a junction row"
    )
    assert rows[0]["suspect_at"] is not None


def test_longer_overwrite_flags_unjustified_row(pol_db):
    """Same rule when the new text is LONGER: flag, keep, no delete."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    content = db.execute(
        "SELECT content FROM documents WHERE id=?", (doc_id,)
    ).fetchone()["content"]
    db.close()
    assert content.startswith("Saeima ceturtdien"), "content must be overwritten"
    assert len(rows) == 1 and rows[0]["suspect_at"] is not None


def test_name_still_present_not_flagged(pol_db):
    """A row still backed by the new text keeps suspect_at NULL."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content="Labots raksts. " + TEXT_WITH_TESTS, source_id=None,
        platform="web", source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_caller_links_justify_unnamed_row(pol_db):
    """pid in the caller's fresh politician_links is justification — even
    when the name is absent from the new text (source/url attribution)."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_flag_clears_when_name_returns(pol_db):
    """v2 flags the row; v3 brings the name back → flag clears."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    insert_document(
        content="Trešā versija atkal par Testu. " * 10, source_id=None,
        platform="web", source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_institution_row_not_flagged(pol_db):
    """organization rows are source-justified — text absence is meaningless."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL,
        politician_links=[(PID_TESTS, "subject"), (PID_ORG, "mentioned")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = {r["politician_id"]: r for r in _junction(db, doc_id)}
    db.close()
    assert rows[PID_ORG]["suspect_at"] is None
    assert rows[PID_TESTS]["suspect_at"] is not None


def test_url_surname_row_not_flagged(pol_db):
    """Surname surviving in the URL slug justifies the row (viedokli class)."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL_VIEDOKLIS,
        politician_links=[(PID_HERMANIS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL_VIEDOKLIS, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_flag_first_detection_wins(pol_db):
    """A second name-absent overwrite must not churn suspect_at."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    first = _junction(db, doc_id)[0]["suspect_at"]
    db.close()
    assert first is not None

    insert_document(
        content="Vēl cita versija bez vārdiem. " * 10, source_id=None,
        platform="web", source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    second = _junction(db, doc_id)[0]["suspect_at"]
    db.close()
    assert second == first


def test_scan_logs_denominator(pol_db):
    """The flag event writes one logs row carrying the examined count —
    a gate that cannot report its denominator is not evidence."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL,
        politician_links=[(PID_TESTS, "subject"), (PID_ORG, "mentioned")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    db = get_db(pol_db)
    row = db.execute(
        "SELECT details FROM logs WHERE action='suspect_link_flag' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    db.close()
    assert row is not None
    details = json.loads(row["details"])
    assert details["document_id"] == doc_id
    assert details["junction_rows_examined"] == 2
    assert details["flagged_pids"] == [PID_TESTS]
    assert details["new_word_count"] == len(TEXT_WITHOUT_TESTS_LONG.split())


def test_manual_relink_clears_flag(pol_db):
    """link_politician_to_document is an explicit assertion → flag clears."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    link_politician_to_document(doc_id, PID_TESTS, "subject")
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_rescan_rederived_link_clears_flag(pol_db):
    """A matcher rescan that re-derives the link from current content clears
    the flag — the backfill-rewrite path (content replaced, then scanned)."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    insert_document(
        content=TEXT_WITHOUT_TESTS_LONG, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    # Simulate a content rewrite outside insert_document (e.g. a backfill
    # script), then a targeted rescan as in backfill_retweet_fulltext.
    db = get_db(pol_db)
    db.execute(
        "UPDATE documents SET content = ? WHERE id = ?",
        (TEXT_WITH_TESTS, doc_id),
    )
    db.commit()
    db.close()
    matcher_mod.link_politicians_to_documents(doc_ids=[doc_id])
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert len(rows) == 1 and rows[0]["suspect_at"] is None


def test_identical_refetch_sets_no_flag(pol_db):
    """Identical bytes short-circuit at content_hash — no flag churn."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=[(PID_TESTS, "subject")],
        db_path=pol_db,
    )
    again = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL, politician_links=None, db_path=pol_db,
    )
    assert again is None
    db = get_db(pol_db)
    rows = _junction(db, doc_id)
    db.close()
    assert rows[0]["suspect_at"] is None


def test_junction_row_survives_every_overwrite(pol_db):
    """Invariant across all scenarios: the UPDATE branch never shrinks the
    junction — flag or no flag, deletion is not in this code path."""
    doc_id = insert_document(
        content=TEXT_WITH_TESTS, source_id=None, platform="web",
        source_url=URL,
        politician_links=[(PID_TESTS, "subject"), (PID_ORG, "mentioned")],
        db_path=pol_db,
    )
    for variant in (
        TEXT_WITHOUT_TESTS_SHORT,
        TEXT_WITHOUT_TESTS_LONG,
        "Pilnīgi cits stāsts par neko citu. " * 8,
    ):
        insert_document(
            content=variant, source_id=None, platform="web",
            source_url=URL, politician_links=None, db_path=pol_db,
        )
        db = get_db(pol_db)
        n = len(_junction(db, doc_id))
        db.close()
        assert n == 2, f"junction rows lost after overwrite with {variant[:30]!r}"
