import json
import os
import tempfile
from unittest.mock import patch

from src.db import init_db, get_db
from src import saites_proposals as sp


def _db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, name, party, role in [(10, "Andris Kulbergs", "Apvienotais saraksts", "Ministru prezidents"),
                                   (6, "Jānis Dombrava", "Nacionālā apvienība", "Iekšlietu ministrs"),
                                   (2, "Evika Siliņa", "Jaunā Vienotība", "Saeimas deputāte")]:
        db.execute("INSERT INTO tracked_politicians (id, name, name_forms, party, role, relationship_type) "
                   "VALUES (?,?,?,?,?,'tracked')", (pid, name, json.dumps([name.split()[-1]]), party, role))
    db.execute("INSERT INTO documents (id, content, content_hash, platform, source_url, scraped_at) "
               "VALUES (?,?,?,?,?, datetime('now'))",
               (1, "Kulbergs: pilnībā atbalstu iekšlietu ministru Dombravu. Siliņa to kritizē.", "h1", "web",
                "https://lsm.test/1"))
    db.execute("INSERT INTO documents (id, content, content_hash, platform, source_url, scraped_at) "
               "VALUES (?,?,?,?,?, datetime('now'))",
               (2, "RT @Latvian_MFA: Foreign Minister met the President.", "h2", "twitter", "https://x.com/Braze_Baiba/status/1"))
    db.execute("INSERT INTO documents (id, content, content_hash, platform, source_url, scraped_at) "
               "VALUES (?,?,?,?,?, datetime('now'))",
               (3, "Kulbergs un Dombrava tikās.", "h3", "web", "https://lsm.test/3"))
    for doc, pid, role in [(1, 10, "subject"), (1, 6, "mentioned"), (1, 2, "mentioned"),
                           (2, 10, "mentioned"), (2, 6, "mentioned"), (3, 10, "subject"), (3, 6, "mentioned")]:
        db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (?,?,?)", (doc, pid, role))
    db.execute("INSERT INTO tension_judged (document_id) VALUES (3)")
    db.commit()
    return db


def test_candidate_docs_skips_bare_rt_and_already_judged():
    db = _db()
    assert sp.candidate_docs(db, days=1) == [1]


def _answers(p_none_10_6, speaks_10):
    return {"answers": {
        "rel_10_6": {"type": "choice", "choice": "atbalsts", "confidence": 0.9,
                     "probabilities": {"atbalsts": 0.9, "uzbrukums": 0.02, "spriedze": 0.03, "none": p_none_10_6}},
        "rel_10_2": {"type": "choice", "choice": "none", "confidence": 0.6,
                     "probabilities": {"atbalsts": 0.1, "uzbrukums": 0.1, "spriedze": 0.2, "none": 0.6}},
        "speaks_10": {"type": "noul", "noul": speaks_10},
    }, "usage": {"input_tokens": 1200, "output_tokens": 40}}


def test_judge_document_keeps_only_confident_pairs_and_marks_judged():
    db = _db()
    captured = {}

    def fake(state, questions, **kw):
        captured.update(state=state, questions=questions)
        return _answers(0.05, 0.97)

    with patch("src.saites_proposals.system_one", fake):
        props = sp.judge_document(db, 1)
    assert set(captured["questions"]) == {"rel_10_6", "rel_10_2", "speaks_10"}
    assert captured["state"]["politicians"]["10"]["name"] == "Andris Kulbergs"
    assert len(props) == 1
    p = props[0]
    assert (p["source_pid"], p["target_pid"], p["relation"]) == (10, 6, "atbalsts")
    assert p["p_link"] == 0.95 and p["p_relation"] == 0.9 and p["p_speaks"] == 0.97
    assert db.execute("SELECT COUNT(*) FROM tension_judged WHERE document_id = 1").fetchone()[0] == 1


def test_judge_document_drops_when_speaker_uncertain():
    db = _db()
    with patch("src.saites_proposals.system_one", lambda s, q, **k: _answers(0.05, 0.4)):
        assert sp.judge_document(db, 1) == []


def test_write_proposals_is_idempotent():
    db = _db()
    p = {"document_id": 1, "source_pid": 10, "target_pid": 6, "relation": "atbalsts",
         "p_link": 0.95, "p_relation": 0.9, "p_speaks": 0.97, "snippet": "Kulbergs: …"}
    assert sp.write_proposals(db, [p]) == 1
    assert sp.write_proposals(db, [p]) == 0
    assert db.execute("SELECT status FROM tension_proposals").fetchone()[0] == "pending"


def test_run_fails_open_per_document():
    db = _db()
    from src.typesafe_client import TypeSafeUnavailable

    def boom(*a, **k):
        raise TypeSafeUnavailable("down")

    with patch("src.saites_proposals.system_one", boom):
        s = sp.run(db, days=1)
    assert s == {"docs": 1, "judged": 0, "proposed": 0, "errors": 1, "input_tokens": 0}
    assert db.execute("SELECT COUNT(*) FROM tension_judged WHERE document_id = 1").fetchone()[0] == 0
