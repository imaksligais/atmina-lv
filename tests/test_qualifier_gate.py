"""A new `position` whose `support` holds a qualifier the stance lacks is REPORTED.

The failure this catches (the "Šnore class"): the extractor drops a condition
(«ja …»), a possibility («varētu») or a part («daļa») and states the position
flat. The `support` fragment is verbatim, so the support gate passes, and the
widened stance is stored with no trace. `save_analysis()` now compares the
qualifier words of `support` against the stance and lists the missing ones in
`failures` as `qualifier_dropped`. It only reports — the claim is stored.

Mutation proof (2026-10-16): with the `dropped_qualifiers` call in
`save_analysis` removed, `test_flat_stance_from_conditional_support_is_reported`
fails (claim stored, no `qualifier_dropped` entry); restored, it passes.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db
from src.support import dropped_qualifiers

DAY = "2026-10-16"
TEXT = "Mēs atbalstām reformu, ja tiks veikti aprēķini. Citādi nē."
SUPPORT = ["Mēs atbalstām reformu, ja tiks veikti aprēķini."]


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
    db.execute(
        """INSERT INTO documents (id, title, content, content_hash, source_url, scraped_at, platform)
           VALUES (1, 'Virsraksts par reformu', ?, 'h1', 'https://example.lv/1', ?, 'web')""",
        (TEXT, f"{DAY} 10:00:00"),
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')"
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


def _save(stance: str) -> dict:
    claim = {
        "document_id": 1, "topic": "Valsts pārvalde", "stance": stance,
        "support": SUPPORT, "quote": None, "confidence": 0.6,
        "reasoning": "tests", "salience": 0.5, "stated_at": DAY,
    }
    return save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Valsts pārvalde"],
        quotes=[], brief="tests", confidence=0.7, claims=[claim],
    )


def _stored(path: str) -> int:
    db = get_db(path)
    try:
        return db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    finally:
        db.close()


def test_flat_stance_from_conditional_support_is_reported(db_path):
    r = _save("Atbalsta reformu.")
    assert _stored(db_path) == 1  # reported, never blocked
    hits = [f for f in r["failures"] if f["type"] == "qualifier_dropped"]
    assert len(hits) == 1, r["failures"]
    assert hits[0]["qualifiers"] == ["ja"]
    assert hits[0]["claim_id"] == r["claim_ids"][0]


def test_stance_that_keeps_the_condition_is_not_reported(db_path):
    r = _save("Atbalsta reformu, ja tiks veikti aprēķini.")
    assert _stored(db_path) == 1
    assert r["status"] == "success", r["failures"]


@pytest.mark.parametrize("support,stance,expected", [
    # whole word: «jau», «jauns» are not «ja»
    ("Tas jau ir jauns likums.", "Likums ir jauns.", []),
    # case-insensitive; the word in the stance counts as kept
    ("Izskatās, ka JA kaut kas mainīsies.", "izskatās, ka ja mainīsies", []),
    ("Izskatās, ka mainīsies.", "Mainīsies.", ["izskatās"]),
    # any «daļ» form in the stance keeps any «daļ» form in the support
    ("Lielākā daļa deputātu iebilst.", "Daļēji iebilst deputātu daļā.", []),
    (["Atbalstu daļu", "priekšlikumu."], "Atbalsta priekšlikumu.", ["daļa"]),
    ("Tas ir daļēji pareizi.", "Tas ir pareizi.", ["daļa"]),
    # «daļiņa» is not a qualifier
    ("Tā ir tikai daļiņa.", "Tā ir.", []),
    ("Tas nav īsti tā, varētu būt.", "Tas nav tā.", ["varētu", "īsti"]),
])
def test_dropped_qualifiers_unit(support, stance, expected):
    assert dropped_qualifiers(support, stance) == expected
