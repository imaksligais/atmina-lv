import json
import os
import tempfile
from unittest.mock import patch

from src.db import init_db, get_db
from src import matcher_veto as mv


def _db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms, party, role) VALUES (?,?,?,?,?)",
               (158, "Agnese Lāce", json.dumps(["Agnese Lāce", "Lāce"]), "Progresīvie", "Kultūras ministre"))
    db.commit()
    db.close()
    return path


def test_text_windows_finds_stem_hits():
    w = mv.text_windows("xxx Lāces vārds yyy", ["Lāce"])
    assert len(w) == 1 and "Lāces" in w[0]


def test_text_windows_falls_back_to_lead():
    assert mv.text_windows("nothing here", ["Lāce"]) == ["nothing here"]


def test_judge_candidate_builds_state_and_returns_probability():
    path = _db_path()
    captured = {}

    def fake_system_one(state, questions, **kw):
        captured.update(state=state, questions=questions)
        return {"answers": {"same_person": {"type": "noul", "noul": 0.05}}}

    mv.clear_cache()
    with patch("src.matcher_veto.get_db", lambda: get_db(path)), \
         patch("src.matcher_veto.system_one", fake_system_one):
        p = mv.judge_candidate("Lācis Bilskas pagastā uzlauž būrus.", 158)
    assert p == 0.05
    assert captured["state"]["tracked_politician"]["name"] == "Agnese Lāce"
    assert "Lācis" in captured["state"]["document"]["passages_mentioning_the_name"][0]
    assert "CURRENT role" in captured["questions"]["same_person"]["instructions"]


def test_judge_candidate_fails_open():
    path = _db_path()
    from src.typesafe_client import TypeSafeUnavailable

    def boom(*a, **k):
        raise TypeSafeUnavailable("no key")

    mv.clear_cache()
    with patch("src.matcher_veto.get_db", lambda: get_db(path)), \
         patch("src.matcher_veto.system_one", boom):
        assert mv.judge_candidate("text", 158) is None


def test_record_appends_json_line(tmp_path):
    with patch("src.matcher_veto.LOG_PATH", tmp_path / "veto.jsonl"):
        mv.record({"pid": 158, "p_same": 0.05})
        mv.record({"pid": 24, "p_same": 0.9})
    lines = (tmp_path / "veto.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(l) ["pid"] for l in lines] == [158, 24]
    assert "ts" in json.loads(lines[0])
