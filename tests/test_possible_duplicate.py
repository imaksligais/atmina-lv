"""Gandrīz-dublikāts glabāšanas brīdī tiek ZIŅOTS `failures`, nekad bloķēts.

2026-09-23 backfill 1. partijā atrasti 10 dublikātu pāri: tas pats politiķis,
tas pats notikums, divi avoti, divi claims. Idempotences atslēga
`(opponent_id, source_url, topic)` tos nenoķer (cits URL), un ±5 d pārbaude
ekstraktora promptā ir tikai konvencija. `save_analysis()` tagad katram jaunam
`position` claim meklē tā paša politiķa tuvāko `position` claim ar `stated_at`
±5 d un, ja vektora attālums ≤ `DUP_DISTANCE_MAX`, pievieno `possible_duplicate`
ierakstu. Claim tiek glabāts jebkurā gadījumā — lēmums paliek cilvēkam.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db

STANCE = "Atbalsta otrā pensiju līmeņa saglabāšanu un iebilst pret tā likvidāciju"
STANCE_TWIN = "Atbalsta otrā pensiju līmeņa saglabāšanu un iebilst pret tā likvidēšanu"


@pytest.fixture
def db_path(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid in (1, 2):
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
            " VALUES (?, ?, 'Testa partija', 'opponent')",
            (pid, f"Testa Politiķis {pid}"),
        )
    for doc_id in (1, 2, 3):
        db.execute(
            """INSERT INTO documents (id, content, content_hash, source_url,
                   scraped_at, platform)
               VALUES (?, 'raksts', ?, ?, '2026-07-25 10:00:00', 'web')""",
            (doc_id, f"h{doc_id}", f"https://example.lv/raksts-{doc_id}"),
        )
        for pid in (1, 2):
            db.execute(
                "INSERT INTO document_politicians (document_id, politician_id, role)"
                " VALUES (?, ?, 'subject')",
                (doc_id, pid),
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


def _claim(doc_id: int, stance: str, stated_at: str, **extra) -> dict:
    return {
        "document_id": doc_id,
        "topic": "Pensijas",
        "stance": stance,
        "quote": None,
        "confidence": 0.8,
        "reasoning": "tests",
        "salience": 0.6,
        "stated_at": stated_at,
        **extra,
    }


def _save(pid: int, claims: list[dict]) -> dict:
    return save_analysis(
        pid=pid, analysis_date="2026-07-25", sentiment=0.0, topics=["Pensijas"],
        quotes=[], brief="tests", confidence=0.8, claims=claims,
    )


def _dups(result: dict) -> list[dict]:
    return [f for f in result["failures"] if f["type"] == "possible_duplicate"]


def _claim_count(path: str) -> int:
    db = get_db(path)
    try:
        return db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    finally:
        db.close()


def test_near_identical_stance_two_days_apart_is_reported_not_blocked(db_path):
    first = _save(1, [_claim(1, STANCE, "2026-07-23 10:00:00")])
    assert first["status"] == "success", first
    old_id = first["claim_ids"][0]

    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00")])

    dups = _dups(second)
    assert len(dups) == 1, second["failures"]
    d = dups[0]
    new_id = second["claim_ids"][0]
    assert d["opponent_id"] == 1
    assert d["claim_id"] == new_id
    assert d["similar_claim_id"] == old_id
    assert isinstance(d["distance"], float)
    assert d["stated_at"].startswith("2026-07-25")
    assert d["similar_stated_at"].startswith("2026-07-23")
    assert d["hint"]
    assert second["status"] == "partial"
    # Nekas nav bloķēts: abi claims glabāti.
    assert new_id != old_id
    assert _claim_count(db_path) == 2


def test_nine_days_apart_is_outside_the_window(db_path):
    _save(1, [_claim(1, STANCE, "2026-07-16 10:00:00")])
    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00")])
    assert _dups(second) == []
    assert second["status"] == "success"


def test_other_politician_is_not_compared(db_path):
    _save(2, [_claim(1, STANCE, "2026-07-24 10:00:00")])
    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00")])
    assert _dups(second) == []
    assert second["status"] == "success"


def test_idempotent_rerun_is_not_a_duplicate_of_itself(db_path):
    first = _save(1, [_claim(1, STANCE, "2026-07-25 10:00:00")])
    again = _save(1, [_claim(1, STANCE, "2026-07-25 10:00:00")])
    assert again["claim_ids"] == first["claim_ids"]
    assert _dups(again) == []
    assert again["status"] == "success"


def test_same_call_siblings_are_compared(db_path):
    """Backfill dublikāti radās vienā izsaukumā — tie jāsalīdzina savā starpā."""
    result = _save(1, [
        _claim(1, STANCE, "2026-07-24 10:00:00"),
        _claim(2, STANCE_TWIN, "2026-07-25 10:00:00"),
    ])
    first_id, second_id = result["claim_ids"]
    assert first_id != second_id
    dups = _dups(result)
    assert len(dups) == 1, result["failures"]
    assert dups[0]["claim_id"] == second_id
    assert dups[0]["similar_claim_id"] == first_id
    assert _claim_count(db_path) == 2


def test_idempotent_rereturn_is_not_checked_against_later_twin(db_path):
    """Atkārtots izsaukums, kas atdod esošu id, nav jauns claim: tam pārbaudi
    nedara, pat ja ±5 d logā tagad ir cits gandrīz-dvīnis (sargā
    `pre_call_max_id`)."""
    first = _save(1, [_claim(1, STANCE, "2026-07-24 10:00:00")])
    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00")])
    assert len(_dups(second)) == 1
    again = _save(1, [_claim(1, STANCE, "2026-07-24 10:00:00")])
    assert again["claim_ids"] == first["claim_ids"]
    assert _dups(again) == [], again["failures"]
    assert again["status"] == "success"


def test_saeima_vote_claim_is_not_checked(db_path, monkeypatch):
    from src import analyze

    _save(1, [_claim(1, STANCE, "2026-07-24 10:00:00")])

    calls: list = []
    real = analyze._nearest_position_claim

    def _record(*a, **k):
        calls.append(k)
        return real(*a, **k)

    monkeypatch.setattr(analyze, "_nearest_position_claim", _record)
    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00",
                              claim_type="saeima_vote")])
    assert calls == []
    assert _dups(second) == []
    assert second["status"] == "success", second["failures"]


def test_vector_query_error_never_fails_the_save(db_path, monkeypatch):
    from src import analyze

    _save(1, [_claim(1, STANCE, "2026-07-23 10:00:00")])

    def _boom(*a, **k):
        raise RuntimeError("vec0 nav pieejams")

    monkeypatch.setattr(analyze, "_nearest_position_claim", _boom)
    second = _save(1, [_claim(2, STANCE_TWIN, "2026-07-25 10:00:00")])
    assert second["status"] != "failed", second["failures"]
    assert len(second["claim_ids"]) == 1
    assert _claim_count(db_path) == 2


def test_get_existing_claims_stated_around_filters_by_stated_at(db_path):
    from src.analyze import get_existing_claims

    _save(1, [
        _claim(1, STANCE, "2026-07-21 10:00:00"),
        _claim(2, "Prasa bezdeficīta budžetu", "2026-07-10 10:00:00",
               topic="Budžets un finanses"),
    ])
    rows = get_existing_claims(1, stated_around="2026-07-25")
    assert [r["stance"] for r in rows] == [STANCE]
    # Bez kwarg — vecā uzvedība (created_at logs), abi redzami.
    assert len(get_existing_claims(1)) == 2
