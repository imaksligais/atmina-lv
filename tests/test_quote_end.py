"""Citāts, kas nogriezts teikuma vidū, tiek ZIŅOTS `failures`, nekad bloķēts.

claim-extractor § 3 q4: citāts ir nepārtraukts runātāja teksts. Ziņo tikai
īstu griezumu (avotā turpinās tā pati izteikuma daļa); tiešās runas komats
pirms atribūcijas («tiesā," pauda» — claim 737776 paraugs) un izmests beigu
punkts nav kļūda.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.analyze import save_analysis
from src.db import get_db, init_db

pytestmark = pytest.mark.usefixtures("support_gate_off")

SOURCE = (
    "Valdība apsver sankcijas. \"Sankcijas ir vajadzīgas. Nosakot tās, mēs "
    "riskējam, ka uzņēmumi var vērsties pret mums tiesā,\" pauda valdības "
    "vadītājs."
)
QUOTE = "Nosakot tās, mēs riskējam, ka uzņēmumi var vērsties pret mums tiesā"


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
    db.execute(
        """INSERT INTO documents (id, content, content_hash, source_url,
               scraped_at, platform)
           VALUES (1, ?, 'h1', 'https://example.lv/sankcijas',
                   '2026-10-14 10:00:00', 'web')""",
        (SOURCE,),
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


@pytest.mark.parametrize(
    ("quote", "flagged"),
    [
        # Teikums nogriezts: avotā seko « tiesā,"».
        (QUOTE.removesuffix(" tiesā"), True),
        # Tiešās runas komats pirms atribūcijas («tiesā," pauda») — nav kļūda.
        (QUOTE, False),
        # Pilns teikums bez beigu punkta, avotā seko nākamais — nekaitīgs.
        ("Sankcijas ir vajadzīgas", False),
    ],
)
def test_quote_cut_mid_utterance_is_reported_not_blocked(
    db_path, quote, flagged
):
    result = save_analysis(
        pid=1, analysis_date="2026-10-14", sentiment=0.0, topics=["Ārpolitika"],
        quotes=[], brief="tests", confidence=0.8,
        claims=[{
            "document_id": 1,
            "topic": "Ārpolitika",
            "stance": "Brīdina, ka sankciju noteikšana var novest pie tiesvedības pret valsti.",
            "quote": quote,
            "confidence": 0.8,
            "reasoning": "Valdības vadītāja tiešs citāts rakstā par sankcijām.",
            "salience": 0.6,
            "stated_at": "2026-10-14 10:00:00",
        }],
    )
    cuts = [f for f in result["failures"] if f["type"] == "quote_end_mismatch"]
    # Claim glabāts abos gadījumos — vārti tikai ziņo.
    assert len(result["claim_ids"]) == 1, result
    db = get_db(db_path)
    try:
        assert db.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 1
    finally:
        db.close()
    if flagged:
        assert len(cuts) == 1, result["failures"]
        assert cuts[0]["claim_id"] == result["claim_ids"][0]
        assert cuts[0]["document_id"] == 1
        assert cuts[0]["detail"].startswith(' tiesā,"')
        assert result["status"] == "partial"
    else:
        assert cuts == [], result["failures"]
        assert result["status"] == "success", result["failures"]
