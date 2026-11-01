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


# 2026-09-26 ēnas nedēļa: logi zināja tikai name_forms + pēdējā burta nogriešanu,
# tāpēc ģenitīvs «Kučinska» / datīvs «Ričardam Šleseram» nedeva trāpījumu, un
# modelis sprieda pēc dokumenta sākuma (docs/audits/2026-09-26-typesafe-enas-nedela.md).
_LEAD = "Sēdes vadītāja. Kolēģi! Sākam sēdi. " * 40


def test_text_windows_finds_matcher_inflection_not_the_lead():
    w = mv.text_windows(_LEAD + "1. – finanšu ministra Māra Kučinska priekšlikums.",
                        ["Māris Kučinskis", "Kučinskis", "Kučinskis, Māris"])
    assert any("Kučinska" in x for x in w)


def test_text_windows_finds_full_name_dative():
    w = mv.text_windows(_LEAD + "vada Ričardam Šleseram piederošo attīstītāju.", ["Ričards Šlesers"])
    assert any("Ričardam Šleseram" in x for x in w)


def test_text_windows_prefers_full_name_hits_over_bare_surname():
    namesake = " ".join(f"Ainārs Šlesers teica {i}. " + "x" * 800 for i in range(4))
    w = mv.text_windows(namesake + "Tur ir Ričardam Šleseram piederoša osta.", ["Ričards Šlesers"])
    assert any("Ričardam Šleseram" in x for x in w)


def test_text_windows_inflections_respect_word_boundary():
    # «Kolu» (Kols acc.) nedrīkst trāpīt «Kolumbija» iekšienē (T1 klasiskais gadījums);
    # ar trāpījumu logs sāktos ar «…», jo tas nav teksta sākumā
    text = "x" * 400 + " Kolumbija un Peru"
    assert mv.text_windows(text, ["Kols"]) == [text]


def test_text_windows_bare_first_name_is_not_a_needle():
    # «Uldis» viens pats nav Augulis; logs nedrīkst aiziet pie cita Ulda
    text = "x" * 400 + " Uldis Bērziņš runāja"
    assert mv.text_windows(text, ["Uldis Augulis"]) == [text]


def test_text_windows_finds_palatalized_full_name_genitive():
    w = mv.text_windows(_LEAD + "ministra Ulda Auguļa rakstveida atbilde", ["Augulis", "Uldis Augulis"])
    assert any("Ulda Auguļa" in x for x in w)
