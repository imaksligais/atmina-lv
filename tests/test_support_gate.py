"""A `position` claim is stored only when its `support` is verbatim in THIS document.

The failure this catches (2026-09-30 stance audit, 1 696 positions): the
extractor widened stances past the source — a dropped hedge, a question turned
into an assertion, a fact carried over from a sibling document packed into the
same agent. The prompt already forbade all three; the rule did not act at the
moment of decision. `save_analysis()` now refuses a position whose `support`
fragments are absent from the document text, and REPORTS the refusal in
`failures` (a gate that drops silently would be a new silent-success defect).

Mutation proof: remove the `check_support` call in `save_analysis` and
`test_fragment_from_another_document_is_refused` + `test_missing_support_is_refused`
fail (a claim is stored, `failures` is empty).
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db
from src.support import check_support

DAY = "2026-09-30"
TEXT = "Izskatās, ka valdība varētu atlikt reformu. Es to neatbalstu, kamēr nav aprēķinu."
OTHER = "Blakus dokuments: ministrs paziņoja, ka reforma sāksies janvārī."


@pytest.fixture
def db_path(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Testa Politiķis', 'Testa partija', 'opponent')"
    )
    for doc_id, text in ((1, TEXT), (2, OTHER)):
        db.execute(
            """INSERT INTO documents (id, title, content, content_hash, source_url, scraped_at, platform)
               VALUES (?, 'Virsraksts par reformu', ?, ?, ?, ?, 'web')""",
            (doc_id, text, f"h{doc_id}", f"https://example.lv/{doc_id}", f"{DAY} 10:00:00"),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (?, 1, 'subject')",
            (doc_id,),
        )
    db.commit()
    db.close()

    from src import analyze, db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", path)
    monkeypatch.setattr(analyze, "get_db", lambda: get_db(path))
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _save(claim: dict) -> dict:
    return save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Valsts pārvalde"],
        quotes=[], brief="tests", confidence=0.7, claims=[claim],
    )


def _claim(**kw) -> dict:
    c = {
        "document_id": 1, "topic": "Valsts pārvalde",
        "stance": "Neatbalsta reformas atlikšanu, kamēr nav aprēķinu.",
        "quote": None, "confidence": 0.6, "reasoning": "tests", "salience": 0.5,
        "stated_at": DAY,
    }
    c.update(kw)
    return c


def _stored(path: str) -> int:
    db = get_db(path)
    try:
        return db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    finally:
        db.close()


def test_verbatim_support_is_stored(db_path):
    r = _save(_claim(support=["Es to neatbalstu, kamēr nav aprēķinu."]))
    assert r["status"] == "success", r["failures"]
    assert _stored(db_path) == 1


def test_support_matches_title_and_ignores_typographic_quotes_and_spacing(db_path):
    r = _save(_claim(support=["Virsraksts  par reformu", "Izskatās, ka valdība varētu atlikt reformu."]))
    assert r["status"] == "success", r["failures"]


def test_fragment_from_another_document_is_refused(db_path):
    r = _save(_claim(support=["ministrs paziņoja, ka reforma sāksies janvārī"]))
    assert r["status"] == "partial"
    assert [f["type"] for f in r["failures"]] == ["support_not_in_source"]
    assert _stored(db_path) == 0


def test_missing_support_is_refused(db_path):
    r = _save(_claim())
    assert [f["type"] for f in r["failures"]] == ["missing_support"]
    assert _stored(db_path) == 0


def test_dropped_hedge_paraphrase_is_refused(db_path):
    # "Izskatās, ka … varētu" compressed into an assertion is not verbatim text.
    r = _save(_claim(support=["valdība atliks reformu"]))
    assert [f["type"] for f in r["failures"]] == ["support_not_in_source"]


def test_program_promise_is_not_gated(db_path):
    r = _save(_claim(claim_type="program_promise"))
    assert r["status"] == "success", r["failures"]


def test_refused_doc_is_still_marked_reviewed_only_if_listed_empty(db_path):
    # A refused claim must not stamp reviewed_at on its own: otherwise the
    # document leaves the queue with no position and no trace (T5 inverse).
    _save(_claim(support=["nav tekstā vispār šāda teikuma"]))
    db = get_db(db_path)
    try:
        assert db.execute("SELECT reviewed_at FROM documents WHERE id=1").fetchone()[0] is None
    finally:
        db.close()


@pytest.mark.parametrize("support,expected", [
    (None, "missing_support"),
    ([], "missing_support"),
    (["  "], "missing_support"),
    (["īss"], "support_not_in_source"),
    ("Es to neatbalstu", None),
])
def test_check_support_unit(support, expected):
    assert check_support(support, TEXT)[0] == expected
