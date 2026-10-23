"""Saeimas dokumentu tēmu klasifikatori (plāns 2026-10-21, 6. uzdevums).

Bez tīkla: `system_one` vienmēr aizstāts. Fikstūra `jev_choice_response.json`
ir viena reāla Jev atbilde (2026-10-22), tāpēc parsēšanas tests lasa to, ko
serviss tiešām atgriež.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import src.saeima.topic_classifiers as tc
from src.topic_map import TOPIC_GROUPS
from src.typesafe_client import TypeSafeUnavailable

FIXTURE = Path(__file__).parent / "fixtures" / "jev_choice_response.json"


@pytest.fixture(autouse=True)
def _tmp_cache(tmp_path, monkeypatch):
    # Neviens tests neraksta data/ — kešs uz tmp.
    monkeypatch.setattr(tc, "CACHE_PATH", tmp_path / "jev_topic_cache.db")


def test_jev_choice_parses_fixture(monkeypatch):
    resp = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(tc, "system_one", lambda *a, **k: resp)
    preds = tc.classify_jev([{"document_key": "412/Lp14", "input_text": "Notariāta likums"}])
    assert preds[0].topic in TOPIC_GROUPS and 0 <= preds[0].confidence <= 1
    assert preds[0].model and preds[0].model != "jev-latest"


def test_jev_unknown_label_is_none(monkeypatch):
    monkeypatch.setattr(tc, "system_one", lambda *a, **k: {"answers": {"q0": {"choice": "Nav"}}})
    assert tc.classify_jev([{"document_key": "k", "input_text": "x"}]) == [None]


def test_jev_unavailable_is_none(monkeypatch):
    def boom(*a, **k):
        raise TypeSafeUnavailable("down")
    monkeypatch.setattr(tc, "system_one", boom)
    assert tc.classify_jev([{"document_key": "k", "input_text": "x"}]) == [None]


def test_prompt_carries_no_labels(monkeypatch):
    """Zelta etiķetes / pašreizējā tēma nedrīkst nonākt Jev pieprasījumā.

    Rubrikas noteikumi un «Robeža» rindas ir pilnas ar `NNN/Lp14 → tēma`
    verdiktiem; kritērijos drīkst būt tikai «Ietver» rinda.
    """
    calls = []

    def fake(state, questions, **kw):
        calls.append((state, questions))
        return {"model": "jev-test", "answers": {}}
    monkeypatch.setattr(tc, "system_one", fake)
    row = {"document_key": "412/Lp14", "input_text": "Virsraksts: Notariāta likums",
           "current_topic": "Valsts pārvalde", "stratum": "chain", "split": "dev",
           "gold_topic": "Tieslietas"}
    tc.classify_jev([row])
    state, questions = calls[0]
    assert state == {"rows": [{"input_text": "Virsraksts: Notariāta likums"}]}
    q = questions["q0"]
    assert q["type"] == "choice" and set(q["criteria"]) == set(TOPIC_GROUPS)
    blob = json.dumps(questions, ensure_ascii=False)
    assert not re.search(r"\d+/(Lp|Lm|P)\d+", blob)
    assert "→" not in blob and "Robeža" not in blob and "Neietver" not in blob


def test_rubric_version_mismatch_raises(tmp_path):
    bad = tmp_path / "RUBRIKA.md"
    bad.write_text("RUBRIC_VERSION: 1999-01-01.0\n\n### Saeimas darbs\n- Ietver: x\n",
                   encoding="utf-8")
    with pytest.raises(ValueError, match="RUBRIC_VERSION"):
        tc.load_rubric_criteria(bad)


def test_jev_cache_reuses_resolved_model(monkeypatch):
    """Otrs skrējiens nāk no keša; atslēgā ir atbildējušais modelis, ne alias."""
    resp = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls = []

    def fake(state, questions, **kw):
        calls.append(kw.get("model"))
        return resp
    monkeypatch.setattr(tc, "system_one", fake)
    rows = [{"document_key": "412/Lp14", "input_text": "Notariāta likums"}]
    first = tc.classify_jev(rows, model="jev-latest")
    second = tc.classify_jev(rows, model=resp["model"])
    assert first == second and len(calls) == 1


def test_keyword_uses_ingest_path():
    # Komisijas teikums tiek izgriezts (ingest ceļš `_motif_to_topic`), tāpēc
    # «Tautsaimniecības, agrārās, vides…» komisija nenosaka tēmu.
    motif = ("Grozījumi Notariāta likumā (412/Lp14). Par nodošanu Tautsaimniecības, "
             "agrārās, vides un reģionālās politikas komisijai.")
    pred = tc.classify_keyword("", motif)
    assert pred.topic in TOPIC_GROUPS and pred.topic != "Vide"
    assert pred.confidence is None and pred.model is None
    # Bez īsta motīva nav rezerves uz virsrakstu.
    with pytest.raises(ValueError):
        tc.classify_keyword("Virsraksts: " + motif, "")


def test_live_rubric_criteria_have_no_rule_refs():
    crit = tc.load_rubric_criteria()
    assert len(crit) == 35
    assert not [t for t, v in crit.items() if "noteikum" in v]


def test_prompt_change_misses_cache(monkeypatch):
    """INSTRUCTIONS ir keša atslēgā — mainīts prompts nesaņem vecu atbildi."""
    resp = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls = []

    def fake(state, questions, **kw):
        calls.append(1)
        return resp
    monkeypatch.setattr(tc, "system_one", fake)
    rows = [{"input_text": "Notariāta likums"}]
    tc.classify_jev(rows, model=resp["model"])
    monkeypatch.setattr(tc, "INSTRUCTIONS", tc.INSTRUCTIONS + " Papildu norāde.")
    tc.classify_jev(rows, model=resp["model"])
    assert len(calls) == 2


def test_chunk_size_is_in_cache_key(monkeypatch):
    """Atbilde no vairāku rindu pieprasījuma netiek dota viena dokumenta zvanam."""
    resp = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls = []

    def fake(state, questions, **kw):
        calls.append(len(state["rows"]))
        return {**resp, "answers": {f"q{i}": resp["answers"]["q0"]
                                    for i in range(len(state["rows"]))}}
    monkeypatch.setattr(tc, "system_one", fake)
    rows = [{"input_text": "Notariāta likums"}, {"input_text": "Sporta likums"}]
    tc.classify_jev(rows, model=resp["model"], batch_size=2)
    tc.classify_jev(rows[:1], model=resp["model"], batch_size=1)
    assert calls == [2, 1]
    assert tc.cached_prediction(tc.input_hash("Sporta likums"), resp["model"]) is None


def test_own_code_error_is_not_unavailable(monkeypatch):
    """ValueError/TypeError no mūsu koda nav «nepieejams» — tā jāredz."""
    def bug(*a, **k):
        raise TypeError("mūsu kļūda")
    monkeypatch.setattr(tc, "system_one", bug)
    with pytest.raises(TypeError):
        tc.classify_jev([{"input_text": "x"}])
