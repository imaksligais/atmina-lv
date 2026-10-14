"""Partiju tests — U1 audits (`scripts/partiju_tests_audit.py`) un saraksti.yaml.

* `score()` ir § 3.4 tīrā funkcija — fikstūru testi pierāda rangu, vārtu un
  tukšo rezultātu pie < 4 atbildēm.
* Repo testi skipo, ja failu vai lokālās ražošanas DB nav (tā pati klase kā
  `test_repo_coding_file_if_present`).
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pta = _load("partiju_tests_audit", REPO / "scripts" / "partiju_tests_audit.py")
ptv = _load("partiju_tests_validate", REPO / "scripts" / "partiju_tests_validate.py")

Q_PATH = REPO / "content" / "partiju-tests" / "jautajumi.yaml"
K_PATH = REPO / "content" / "partiju-tests" / "kodejums.json"
S_PATH = REPO / "content" / "partiju-tests" / "saraksti.yaml"
DB = REPO / "data" / "atmina.db"

SARAKSTI = [{"short_name": sn} for sn in ("AAA", "BBB", "CCC")]
CODING_2Q = {
    "q01": {"AAA": {"nostaja": "par"}, "BBB": {"nostaja": "pret"},
            "CCC": {"nostaja": "klusē", "piezime": "nemin"}},
    "q02": {"AAA": {"nostaja": "par"}, "BBB": {"nostaja": "klusē", "piezime": "nemin"},
            "CCC": {"nostaja": "klusē", "piezime": "nemin"}},
    "q03": {"AAA": {"nostaja": "pret"}, "BBB": {"nostaja": "pret"},
            "CCC": {"nostaja": "par"}},
    "q04": {"AAA": {"nostaja": "par"}, "BBB": {"nostaja": "par"},
            "CCC": {"nostaja": "klusē", "piezime": "nemin"}},
}


def _repo_files_or_skip():
    if not (Q_PATH.exists() and K_PATH.exists() and S_PATH.exists()):
        pytest.skip("content/partiju-tests/ faili nav — lokāla pārbaude")


def test_score_perfect_match_ranks_first():
    answers = {"q01": "par", "q02": "par", "q03": "pret", "q04": "par"}
    ranked = pta.score(answers, CODING_2Q, SARAKSTI)
    assert ranked and ranked[0][0] == "AAA"
    assert ranked[0][1] == ranked[0][2] == 4  # N == M


def test_score_all_skipped_is_empty():
    answers = {qid: "izlaist" for qid in CODING_2Q}
    assert pta.score(answers, CODING_2Q, SARAKSTI) == []
    assert pta.score({"q01": "par"}, CODING_2Q, SARAKSTI) == []  # < 4 atbildes


def test_score_filters_thin_denominators():
    """CCC izsakās tikai vienā no 4 — M=1 < ⌈4/2⌉ → rangā nav (§ 3.4.4)."""
    answers = {"q01": "par", "q02": "par", "q03": "pret", "q04": "par"}
    names = [r[0] for r in pta.score(answers, CODING_2Q, SARAKSTI)]
    assert "CCC" not in names and set(names) == {"AAA", "BBB"}


def test_repo_audit_known_state():
    """§ 2 diagnoze šodienas kodējumam: 9 no 12 FAIL vecajam 09-10 kritērijam
    (≥6/≥2) un 11 no 12 FAIL § 3.3 vārtam (≥8/≥3) — kopš 2026-09-17 3. līmeņa
    5 šūnām q05 iziet; pēc D1b rubrikas audita (2026-09-22) q01 vairs neiziet,
    jo GS pārkodēta uz klusē un mazākums nokrita uz 2. Ja 0 — skripts salūzis."""
    _repo_files_or_skip()
    questions = yaml.safe_load(Q_PATH.read_text(encoding="utf-8"))
    coding = json.loads(K_PATH.read_text(encoding="utf-8"))
    saraksti = ptv.load_saraksti(S_PATH)
    old = pta.question_gate(questions, coding, saraksti, min_readable=6, min_minority=2)
    new = pta.question_gate(questions, coding, saraksti)
    n_old = sum(1 for r in old if not r["ok"])
    n_new = sum(1 for r in new if not r["ok"])
    print(f"\nsaucējs: {len(old)} jautājumi × {len(saraksti)} saraksti; "
          f"FAIL ≥6/≥2: {n_old}, ≥8/≥3: {n_new}")
    assert len(old) == 12 and n_old == 9 and n_new == 11


def test_saraksti_match_parties_with_promises():
    """saraksti.yaml short_name kopa == parties.short_name ar program_promise."""
    _repo_files_or_skip()
    if not DB.exists():
        pytest.skip("data/atmina.db nav — ražošanas DB tikai lokāli")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='claims'").fetchone():
            pytest.skip("data/atmina.db bez `claims` tabulas — ražošanas DB tikai lokāli")
        db_parties = {r[0] for r in conn.execute(
            "SELECT DISTINCT p.short_name FROM parties p JOIN claims c ON c.party_id = p.id "
            "WHERE c.claim_type = 'program_promise'")}
    finally:
        conn.close()
    yaml_parties = {s["short_name"] for s in ptv.load_saraksti(S_PATH)}
    print(f"\nsaucējs: saraksti.yaml {len(yaml_parties)} == DB program_promise {len(db_parties)}")
    assert yaml_parties == db_parties
