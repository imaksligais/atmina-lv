"""TypeSafe veto hook inside match_politicians() (ATMINA_TYPESAFE_VETO).

Only surname-only candidates are judged: no first name, no @handle, and not
an institutional entity (journalist/organization — the A0 re-check showed the
person-shaped question rejecting Latvijas Banka, NBS, LVM as "not a person").
"""
import json
import os
import tempfile
from unittest.mock import patch

from src.db import init_db, get_db


def _db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms, party, role) VALUES (?,?,?,?,?)",
               (24, "Rihards Kols", json.dumps(["Rihards Kols", "Kols"]), "Nacionālā apvienība", "EP deputāts"))
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms, party, role, relationship_type) "
               "VALUES (?,?,?,?,?,?)",
               (300, "Latvijas Banka", json.dumps(["Latvijas Banka", "Latvijas Bankas"]), None,
                "Centrālā banka", "organization"))
    db.commit()
    db.close()
    return path


TEXT_SURNAME_ONLY = "Deputāts Kols šodien klusēja."
TEXT_FULL_NAME = "Rihards Kols šodien klusēja."
TEXT_ORG = "Latvijas Banka pazemināja prognozi."


def _match(mode, path, text, judged_p):
    from src import matcher
    calls = []

    def fake_judge(t, pid):
        calls.append(pid)
        return judged_p

    with patch("src.matcher.get_db", lambda: get_db(path)), \
         patch("src.matcher.TYPESAFE_VETO_MODE", mode), \
         patch("src.matcher.judge_candidate", fake_judge), \
         patch("src.matcher.record") as rec:
        matcher._clear_politician_cache()
        result = matcher.match_politicians(text)
    matcher._clear_politician_cache()
    return result, calls, rec


def test_off_mode_never_judges():
    path = _db_path()
    result, calls, rec = _match("off", path, TEXT_SURNAME_ONLY, 0.01)
    assert result == [(24, "subject")] and calls == [] and not rec.called


def test_shadow_mode_keeps_but_records():
    path = _db_path()
    result, calls, rec = _match("shadow", path, TEXT_SURNAME_ONLY, 0.01)
    assert result == [(24, "subject")] and calls == [24]
    ev = rec.call_args.args[0]
    assert ev["mode"] == "shadow" and ev["pid"] == 24 and ev["p_same"] == 0.01 and ev["vetoed"] is True


def test_enforce_mode_drops_vetoed():
    path = _db_path()
    result, calls, rec = _match("enforce", path, TEXT_SURNAME_ONLY, 0.01)
    assert result == [] and calls == [24]
    assert rec.call_args.args[0]["vetoed"] is True


def test_enforce_mode_keeps_confident():
    path = _db_path()
    result, calls, rec = _match("enforce", path, TEXT_SURNAME_ONLY, 0.97)
    assert result == [(24, "subject")]
    assert rec.call_args.args[0]["vetoed"] is False


def test_enforce_mode_keeps_when_unavailable():
    """Fail-open: judge returns None -> candidate kept, event records p_same=None."""
    path = _db_path()
    result, calls, rec = _match("enforce", path, TEXT_SURNAME_ONLY, None)
    assert result == [(24, "subject")] and calls == [24]
    ev = rec.call_args.args[0]
    assert ev["p_same"] is None and ev["vetoed"] is False


def test_full_name_match_is_never_sent():
    path = _db_path()
    result, calls, rec = _match("enforce", path, TEXT_FULL_NAME, 0.01)
    assert result == [(24, "subject")] and calls == []


def test_institutional_entity_is_never_sent():
    path = _db_path()
    result, calls, rec = _match("enforce", path, TEXT_ORG, 0.01)
    assert result == [(300, "subject")] and calls == [] and not rec.called
