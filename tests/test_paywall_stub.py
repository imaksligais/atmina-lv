"""Pozīcija no paywall ievada tiek atzīmēta NEEDS_REVIEW un ZIŅOTA, nekad bloķēta.

`documents.is_paywall` neraksta neviens ingest ceļš, tāpēc vārts lasa
pārklājuma tekstu, ko ekstrakcija saglabā aiz bezmaksas ievada (claim #704199,
doc 96438 — delfi.lv «Pielāgojam Tev piemērotāko abonēšanas piedāvājumu...»).
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db

pytestmark = pytest.mark.usefixtures("support_gate_off")

LEAD = (
    "\"Es teiktu, ka patiesība ir kaut kur pa vidu,\" – tā komandieris raidījumā "
    "komentēja politiķu strīdu par lādiņu iepirkumu."
)
PAYWALLED = (
    LEAD + "\nLūdzu, uzgaidi!\nPielāgojam Tev piemērotāko abonēšanas piedāvājumu..."
    "\nLoading...\nJautājumu gadījumā raksti konts@delfi.lv"
)


@pytest.fixture
def db_path(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Testa Politiķe', 'Testa partija', 'opponent')"
    )
    for doc_id, text in ((1, PAYWALLED), (2, LEAD)):
        db.execute(
            """INSERT INTO documents (id, content, content_hash, source_url,
                   scraped_at, platform)
               VALUES (?, ?, ?, ?, '2026-11-09 10:00:00', 'web')""",
            (doc_id, text, f"h{doc_id}", f"https://example.lv/{doc_id}"),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role)"
            " VALUES (?, 1, 'subject')", (doc_id,)
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


@pytest.mark.parametrize(("doc_id", "flagged"), [(1, True), (2, False)])
def test_claim_from_paywall_preview_is_marked_for_review_not_blocked(
    db_path, doc_id, flagged
):
    result = save_analysis(
        pid=1, analysis_date="2026-11-09", sentiment=0.0, topics=["Aizsardzība"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[{
            "document_id": doc_id,
            "topic": "Aizsardzība",
            "stance": "Uzskata, ka patiesība strīdā par lādiņu iepirkumu ir pa vidu.",
            "quote": "Es teiktu, ka patiesība ir kaut kur pa vidu",
            "confidence": 0.8,
            "reasoning": "Tiešs citāts raidījumā.",
            "salience": 0.5,
            "stated_at": "2026-11-09 10:00:00",
        }],
    )
    hits = [f for f in result["failures"] if f["type"] == "paywall_stub"]
    assert len(result["claim_ids"]) == 1, result  # vārts nekad nebloķē
    db = get_db(db_path)
    try:
        status = db.execute(
            "SELECT review_status FROM claims WHERE id = ?", (result["claim_ids"][0],)
        ).fetchone()[0]
    finally:
        db.close()
    if flagged:
        assert len(hits) == 1, result["failures"]
        assert hits[0]["claim_id"] == result["claim_ids"][0]
        assert hits[0]["document_id"] == 1
        assert status == "needs_review"
    else:
        assert hits == [], result["failures"]
        assert status is None
