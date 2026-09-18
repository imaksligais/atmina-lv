"""A silent idempotency merge must show up in `failures`, not just in claim_ids.

`store_claim()` is idempotent on (opponent_id, source_url, topic) and is
first-write-wins (Data Contract #3). A document carrying several DISTINCT
stances in one topic therefore collapses them into the first claim — the later
stance is discarded, `store_claim` reports success, and `failures` stays EMPTY.
That is trap T2, observed repeatedly (06-17/06-18: Vītols, Krusts, Rokpelnis,
Abu Meri, Tāvars). The only trace used to be a repeated id inside `claim_ids`,
which no caller inspects.

The merge itself is NOT changed here — consolidating is often the right answer.
What changes is that the loss becomes visible.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db

DAY = "2026-07-25"
URL = "https://x.com/testa/status/123"


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
        """INSERT INTO documents (id, content, content_hash, source_url, scraped_at, platform)
           VALUES (1, 'garš tvīts ar divām pozīcijām', 'h1', ?, ?, 'twitter')""",
        (URL, f"{DAY} 10:00:00"),
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role)"
        " VALUES (1, 1, 'subject')"
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


def _claim(stance: str, topic: str = "Pensijas") -> dict:
    return {
        "document_id": 1,
        "topic": topic,
        "stance": stance,
        "quote": stance,
        "confidence": 0.8,
        "reasoning": "tests",
        "salience": 0.6,
        "stated_at": f"{DAY} 10:00:00",
    }


def test_two_stances_one_topic_are_reported_as_silent_dedup(db_path):
    result = save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Pensijas"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[
            _claim("Atbalsta otrā pensiju līmeņa saglabāšanu"),
            _claim("Atbalsta otrā pensiju līmeņa likvidāciju"),
        ],
    )

    dedups = [f for f in result["failures"] if f["type"] == "silent_dedup"]
    assert len(dedups) == 1, result["failures"]

    d = dedups[0]
    assert d["topic"] == "Pensijas"
    assert d["kept_stance"] == "Atbalsta otrā pensiju līmeņa saglabāšanu"
    assert d["dropped_stance"] == "Atbalsta otrā pensiju līmeņa likvidāciju"
    assert d["source_url"] == URL
    # The loss must not be dressed up as an unqualified success.
    assert result["status"] == "partial"


def test_distinct_topics_do_not_trigger_the_warning(db_path):
    """Differentiating the topic is the documented way around the merge — it
    must not then be flagged as a loss."""
    result = save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Pensijas", "Budžets un finanses"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[
            _claim("Atbalsta otrā līmeņa saglabāšanu", topic="Pensijas"),
            _claim("Prasa bezdeficīta budžetu", topic="Budžets un finanses"),
        ],
    )

    assert [f for f in result["failures"] if f["type"] == "silent_dedup"] == []
    assert result["status"] == "success"
    assert len(set(result["claim_ids"])) == 2


def test_rerunning_the_same_day_is_not_reported_as_a_loss(db_path):
    """Plain idempotence: the same single claim stored twice across two calls
    returns the existing id and loses nothing."""
    first = save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Pensijas"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[_claim("Atbalsta otrā līmeņa saglabāšanu")],
    )
    second = save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Pensijas"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[_claim("Atbalsta otrā līmeņa saglabāšanu")],
    )

    assert [f for f in second["failures"] if f["type"] == "silent_dedup"] == []
    assert first["claim_ids"] == second["claim_ids"]


def test_three_stances_report_two_losses(db_path):
    result = save_analysis(
        pid=1, analysis_date=DAY, sentiment=0.0, topics=["Pensijas"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[_claim("Pirmā nostāja"), _claim("Otrā nostāja"), _claim("Trešā nostāja")],
    )

    dedups = [f for f in result["failures"] if f["type"] == "silent_dedup"]
    assert len(dedups) == 2
    assert {d["dropped_stance"] for d in dedups} == {"Otrā nostāja", "Trešā nostāja"}
    assert {d["kept_stance"] for d in dedups} == {"Pirmā nostāja"}
