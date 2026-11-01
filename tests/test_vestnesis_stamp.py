"""Tests for src/vestnesis_stamp.py — Vēstnesis signature-only pair stamp.

Failure named first: a stamp that marks a pair whose act carries the
politician's own words hides a position forever (T16), and a stamp that
touches `documents.reviewed_at` hides every OTHER politician in that act.
"""

import os
import tempfile

import pytest

from src.db import get_db, init_db
from src.vestnesis_stamp import stamp_signature_only_pairs

SIGNED = (
    "Ministru kabinets nolemj grozīt noteikumus.\n"
    "Ministru prezidente E. Siliņa\n"
    "Finanšu ministrs A. Ašeradens"
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Evika Siliņa', 'JV')")
    db.commit()
    db.close()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _doc(path, doc_id, title, content, *, pid=1, platform="vestnesis"):
    db = get_db(path)
    db.execute(
        """INSERT INTO documents (id, title, content, content_hash, platform, scraped_at)
           VALUES (?, ?, ?, ?, ?, '2026-10-01 22:00:00')""",
        (doc_id, title, content, f"h{doc_id}", platform),
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (?, ?, 'subject')",
        (doc_id, pid),
    )
    db.commit()
    db.close()


def _extracted(path, doc_id, pid=1):
    db = get_db(path)
    row = db.execute(
        "SELECT dp.extracted_at, d.reviewed_at FROM document_politicians dp "
        "JOIN documents d ON d.id = dp.document_id "
        "WHERE dp.document_id = ? AND dp.politician_id = ?",
        (doc_id, pid),
    ).fetchone()
    db.close()
    return row["extracted_at"], row["reviewed_at"]


def test_signature_only_routine_act_is_stamped(db_path):
    _doc(db_path, 10, "Grozījumi Ministru kabineta noteikumos Nr. 1", SIGNED)
    db = get_db(db_path)
    res = stamp_signature_only_pairs(db, dry_run=False)
    db.close()
    assert res["examined"] == 1 and res["stamped"] == 1, res
    extracted, reviewed = _extracted(db_path, 10)
    assert extracted is not None
    assert reviewed is None  # never the document-level stamp


def test_surname_twice_is_not_stamped(db_path):
    _doc(db_path, 10, "Grozījumi Ministru kabineta noteikumos Nr. 1",
         "Siliņa iebilda pret grozījumiem.\n" + SIGNED)
    db = get_db(db_path)
    res = stamp_signature_only_pairs(db, dry_run=False)
    db.close()
    assert res["examined"] == 1 and res["stamped"] == 0, res
    assert _extracted(db_path, 10)[0] is None


@pytest.mark.parametrize("title", ["Ministru kabineta sēdes protokols", "Par darba grupu"])
def test_non_routine_title_is_not_stamped(db_path, title):
    _doc(db_path, 10, title, SIGNED)
    db = get_db(db_path)
    res = stamp_signature_only_pairs(db, dry_run=False)
    db.close()
    assert res["stamped"] == 0, res
    assert _extracted(db_path, 10)[0] is None


def test_claim_bearing_pair_is_not_stamped(db_path):
    _doc(db_path, 10, "Grozījumi Ministru kabineta noteikumos Nr. 1", SIGNED)
    db = get_db(db_path)
    db.execute(
        """INSERT INTO claims (opponent_id, document_id, topic, stance, stated_at, created_at)
           VALUES (1, 10, 'Budžets', 'Atbalsta', '2026-10-01', '2026-10-01 23:00:00')"""
    )
    db.commit()
    res = stamp_signature_only_pairs(db, dry_run=False)
    db.close()
    assert res["examined"] == 0 and res["stamped"] == 0, res
    assert _extracted(db_path, 10)[0] is None


def test_dry_run_writes_nothing(db_path):
    _doc(db_path, 10, "Grozījumi Ministru kabineta noteikumos Nr. 1", SIGNED)
    db = get_db(db_path)
    res = stamp_signature_only_pairs(db, dry_run=True)
    db.close()
    assert res["stamped"] == 1 and [p["doc_id"] for p in res["pairs"]] == [10], res
    assert _extracted(db_path, 10) == (None, None)


def test_non_vestnesis_pair_is_never_examined(db_path):
    _doc(db_path, 10, "Grozījumi Ministru kabineta noteikumos Nr. 1", SIGNED, platform="web")
    db = get_db(db_path)
    res = stamp_signature_only_pairs(db, dry_run=False)
    db.close()
    assert res["examined"] == 0, res
    assert _extracted(db_path, 10)[0] is None
