"""Junction inversijas rindas fikss — plāna vārti (2026-08-04).

Plāns: docs/plans/2026-08-04-junction-inversion-queue-fix.md. Četri vārti:
(a) citēts `mentioned` runātājs nonāk rindā ARĪ PĒC subject apstrādes;
(b) `extracted_at` uzliekas abos iznākumos (claims + empty), un mentioned
    joslas apstrāde NEuzliek dokumenta `reviewed_at`;
(c) subject josla uzvedas identiski līdzšinējam (reviewed_at semantika);
(d) audita skripta bāzlīnija pēc detektora refaktora — dzīvās DB salīdzinājums
    (checked/flagged identisks tajā pašā dienā), šeit funkcionālais minimums:
    koplietotais detektors atpazīst fixture inversiju.
"""
import os
import tempfile

import pytest
from datetime import datetime

from src.db import init_db, get_db
from src.quoted_speaker import find_inversions, pending_quoted_mentioned


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


CONTENT_10 = (
    'Valdība apsprieda Kārļa Bērza plānu nodokļu jomā. '
    '"Šis plāns ir jāaptur," teica Jānis Ozols intervijā portālam.'
)
CONTENT_11 = (
    'Ministrija publicēja Kārļa Bērza ziņojumu. '
    '"Ziņojums ir nepilnīgs," norādīja Jānis Ozols preses konferencē.'
)


@pytest.fixture
def lane_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type, name_forms) "
        "VALUES (1, 'Kārlis Bērzs', 'X', 'tracked', '[\"Kārlis Bērzs\", \"Bērzs\"]')"
    )
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type, name_forms) "
        "VALUES (2, 'Jānis Ozols', 'Y', 'tracked', '[\"Jānis Ozols\", \"Ozols\"]')"
    )

    for doc_id, content, url in (
        (10, CONTENT_10, "https://ex.lv/a"),
        (11, CONTENT_11, "https://ex.lv/b"),
    ):
        db.execute(
            "INSERT INTO documents (id, content, content_hash, scraped_at, "
            "platform, source_url) VALUES (?, ?, ?, ?, 'web', ?)",
            (doc_id, content, f"h{doc_id}", now, url),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, 1, 'subject')", (doc_id,)
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, 2, 'mentioned')", (doc_id,)
        )

    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def patched(lane_db, monkeypatch):
    import src.analyze as analyze_mod
    import src.tools as tools_mod
    import src.db as db_mod

    monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(lane_db))
    monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(lane_db))
    monkeypatch.setattr(db_mod, "DB_PATH", lane_db)
    return lane_db


def _junction_extracted(path, doc_id, pid):
    db = get_db(path)
    row = db.execute(
        "SELECT extracted_at FROM document_politicians "
        "WHERE document_id=? AND politician_id=?",
        (doc_id, pid),
    ).fetchone()
    db.close()
    return row["extracted_at"] if row else None


def _doc_reviewed(path, doc_id):
    db = get_db(path)
    row = db.execute(
        "SELECT reviewed_at FROM documents WHERE id=?", (doc_id,)
    ).fetchone()
    db.close()
    return row["reviewed_at"]


class TestDetector:
    def test_shared_detector_flags_fixture_inversion(self, lane_db):
        """(d) funkcionālais minimums: koplietotais modulis redz inversiju."""
        db = get_db(lane_db)
        result = find_inversions(db, days=3)
        db.close()
        assert result["checked"] == 2
        flagged = {inv["document_id"] for inv in result["inversions"]}
        assert flagged == {10, 11}
        for inv in result["inversions"]:
            assert inv["speaking_mentioned"] == [2]

    def test_pending_pairs_filter_extracted(self, lane_db):
        db = get_db(lane_db)
        pairs = pending_quoted_mentioned(db, days=3)
        assert {(p["document_id"], p["politician_id"]) for p in pairs} == {
            (10, 2), (11, 2),
        }
        db.execute(
            "UPDATE document_politicians SET extracted_at='2026-08-04 20:00:00' "
            "WHERE document_id=10 AND politician_id=2"
        )
        db.commit()
        pairs = pending_quoted_mentioned(db, days=3)
        assert {(p["document_id"], p["politician_id"]) for p in pairs} == {(11, 2)}
        db.close()


class TestQueueSecondLane:
    def test_quoted_mentioned_enters_queue_after_subject_processing(self, patched):
        """(a) Subject apstrāde doku no B joslas NEizņem."""
        import src.analyze as analyze_mod

        res = analyze_mod.save_analysis(
            pid=1, analysis_date="2026-08-04", sentiment=0.0, topics=[],
            quotes=[], brief="tukšs", confidence=0.5,
            claims=[], empty_doc_ids=[10, 11],
        )
        assert res["status"] == "success"
        assert _doc_reviewed(patched, 10) is not None  # (c) subject semantika

        pending = analyze_mod.get_pending_politicians(days=3)
        by_id = {p["id"]: p for p in pending}
        assert 2 in by_id, "citētais mentioned runātājs nav rindā pēc subject apstrādes"
        assert by_id[2]["mentioned_doc_count"] == 2

        docs = analyze_mod.get_politician_documents(2, days=3)
        got = {d["id"] for d in docs}
        assert got == {10, 11}
        for d in docs:
            assert d["role"] == "mentioned"
            assert d.get("quoted_mentioned_lane") is True

    def test_mentioned_processing_stamps_pair_not_reviewed(self, patched):
        """(b) B apstrāde zīmogo pāri, bet NE dokumenta reviewed_at."""
        import src.analyze as analyze_mod

        res = analyze_mod.save_analysis(
            pid=2, analysis_date="2026-08-04", sentiment=0.0, topics=[],
            quotes=[], brief="tukšs", confidence=0.5,
            claims=[], empty_doc_ids=[10],
        )
        assert res["status"] == "success"
        assert _junction_extracted(patched, 10, 2) is not None
        assert _doc_reviewed(patched, 10) is None, (
            "mentioned joslas apstrāde nedrīkst zīmogot dokumenta reviewed_at — "
            "tas maskētu subject joslu"
        )
        # Pāris izgājis no joslas; otrs doks paliek.
        db = get_db(patched)
        pairs = pending_quoted_mentioned(db, days=3)
        db.close()
        assert {(p["document_id"], p["politician_id"]) for p in pairs} == {(11, 2)}

    def test_extracted_at_set_on_claims_outcome(self, patched):
        """(b) claims iznākums arī zīmogo pāri."""
        import src.analyze as analyze_mod

        res = analyze_mod.save_analysis(
            pid=2, analysis_date="2026-08-04", sentiment=0.0, topics=["Budžets"],
            quotes=[], brief="pozīcija", confidence=0.7,
            claims=[{
                "document_id": 11, "topic": "Budžets un finanses",
                "stance": "Uzskata, ka ziņojums ir nepilnīgs.",
                "quote": "Ziņojums ir nepilnīgs", "confidence": 0.7,
                "reasoning": "tiešs citāts", "salience": 0.5,
                "stated_at": "2026-08-04",
            }],
        )
        assert res["status"] == "success", res
        assert res["claim_ids"], res
        assert _junction_extracted(patched, 11, 2) is not None
        assert _doc_reviewed(patched, 11) is None

    def test_subject_lane_unchanged_and_stamps_pair(self, patched):
        """(c) Subject apstrāde: reviewed_at kā līdz šim + pāra zīmogs."""
        import src.analyze as analyze_mod

        res = analyze_mod.save_analysis(
            pid=1, analysis_date="2026-08-04", sentiment=0.0, topics=[],
            quotes=[], brief="tukšs", confidence=0.5,
            claims=[], empty_doc_ids=[10],
        )
        assert res["status"] == "success"
        assert _doc_reviewed(patched, 10) is not None
        assert _junction_extracted(patched, 10, 1) is not None
        # B pāris neskarts — viņa josla dzīva.
        assert _junction_extracted(patched, 10, 2) is None
