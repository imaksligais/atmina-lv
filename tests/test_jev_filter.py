"""Pakešu Noul vērtētājs — testi bez API (system_one vienmēr aizstāts)."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src import jev_filter
from src.jev_filter import JevCache, JevStats, cache_key, judge_rows
from src.typesafe_client import TypeSafeUnavailable

INSTR = "Vai `{row}.new` nostāja ir pretēja `{row}.old` nostājai?"
CRIT = {"true": "pretēja", "false": "nav pretēja"}


def _rows(n: int) -> list[dict]:
    return [{"old": f"vecā {i}", "new": f"jaunā {i}"} for i in range(n)]


def _fake_answers(calls: list[dict]):
    """system_one aizstājējs: reģistrē izsaukumus, atbild i/10 katrai rindai."""
    def fake(state, questions, **kw):
        calls.append({"state": state, "questions": questions, "kw": kw})
        answers = {}
        for qid in questions:
            i = int(qid[1:])
            answers[qid] = {"type": "noul", "noul": min(0.99, i / 10)}
        return {"model": "jev-1.13.0", "answers": answers,
                "usage": {"input_tokens": 100 * len(questions), "output_tokens": len(questions)}}
    return fake


@pytest.fixture
def tmp_cache():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield JevCache(Path(path))
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def test_batches_and_aligns_probabilities(tmp_cache):
    calls: list[dict] = []
    stats = JevStats()
    with patch("src.jev_filter.system_one", _fake_answers(calls)):
        probs = judge_rows(_rows(5), INSTR, CRIT, context={"politician": "tas pats"},
                           batch_size=2, workers=1, cache=tmp_cache, stats=stats)
    assert len(calls) == 3                                   # 2 + 2 + 1
    assert [len(c["questions"]) for c in calls] == [2, 2, 1]
    # katra pakete: konteksts + tikai savas rindas; jautājums atsaucas uz rows[i]
    assert calls[0]["state"] == {"politician": "tas pats", "rows": _rows(5)[:2]}
    assert calls[0]["questions"]["r1"]["instructions"] == INSTR.replace("{row}", "rows[1]")
    assert calls[0]["questions"]["r1"]["criteria"] == CRIT
    assert calls[0]["questions"]["r1"]["type"] == "noul"
    # rezultāts izlīdzināts ar ievadi: paketes lokālais indekss, ne globālais
    assert probs == pytest.approx([0.0, 0.1, 0.0, 0.1, 0.0])
    assert stats.requests == 3
    assert stats.input_tokens == 500
    assert stats.output_tokens == 5
    assert stats.cache_hits == 0


def test_per_batch_cache_write_survives_later_failure(tmp_cache):
    """Kešā jāraksta pēc KATRAS paketes, ne tikai skrējiena beigās — citādi
    nogalināts skrējiens (SIGKILL, avārija) pazaudē jau samaksātās atbildes,
    kaut arī paketes iekšā TypeSafeUnavailable tiek notverts un neizraisa krišanu.
    """
    calls: list[dict] = []
    real = _fake_answers(calls)
    rows = _rows(2)
    key0 = cache_key("jev-test", None, INSTR, CRIT, rows[0])
    invocations = 0

    def fake(state, questions, **kw):
        nonlocal invocations
        invocations += 1
        if invocations == 2:
            # 2. pakete: ThreadPoolExecutor(max_workers=1) pieprasījumus sūta
            # secīgi VIENĀ worker pavedienā, kas nekavējoties turpina uz 2. paketi,
            # negaidot, kamēr galvenais pavediens paņem 1. paketes rezultātu —
            # neliela pauze dod tam iespēju paspēt ierakstīt kešā, pirms pārbaudām.
            time.sleep(0.05)
            assert len(tmp_cache.get_many([key0])) == 1
            raise TypeSafeUnavailable("down")
        return real(state, questions, **kw)

    with patch("src.jev_filter.system_one", fake):
        probs = judge_rows(rows, INSTR, CRIT, model="jev-test", batch_size=1, workers=1,
                           cache=tmp_cache)
    assert invocations == 2
    assert probs == [0.0, None]


def test_cache_hit_skips_request(tmp_cache):
    calls: list[dict] = []
    with patch("src.jev_filter.system_one", _fake_answers(calls)):
        first = judge_rows(_rows(3), INSTR, CRIT, batch_size=40, workers=1, cache=tmp_cache)
        stats = JevStats()
        second = judge_rows(_rows(3), INSTR, CRIT, batch_size=40, workers=1,
                            cache=tmp_cache, stats=stats)
    assert len(calls) == 1
    assert second == first
    assert stats.requests == 0 and stats.cache_hits == 3


def test_cache_key_changes_with_question_and_context():
    row = {"old": "a", "new": "b"}
    k1 = cache_key("jev-latest", None, INSTR, CRIT, row)
    assert k1 == cache_key("jev-latest", None, INSTR, CRIT, {"new": "b", "old": "a"})
    assert k1 != cache_key("jev-latest", {"x": 1}, INSTR, CRIT, row)
    assert k1 != cache_key("jev-latest", None, INSTR + " ?", CRIT, row)
    assert k1 != cache_key("jev-1.13.0", None, INSTR, CRIT, row)


def test_unavailable_batch_yields_none_others_fine(tmp_cache):
    calls: list[dict] = []
    real = _fake_answers(calls)

    def flaky(state, questions, **kw):
        if state["rows"][0]["old"] == "vecā 2":
            raise TypeSafeUnavailable("down")
        return real(state, questions, **kw)

    stats = JevStats()
    with patch("src.jev_filter.system_one", flaky):
        probs = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1,
                           cache=tmp_cache, stats=stats)
    assert probs[:2] == pytest.approx([0.0, 0.1])
    assert probs[2:] == [None, None]
    assert stats.unavailable == 2
    # nepieejamais NAV kešā — nākamreiz mēģina vēlreiz
    with patch("src.jev_filter.system_one", real):
        again = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1, cache=tmp_cache)
    assert again[2:] == pytest.approx([0.0, 0.1])


def test_bad_body_batch_yields_none_others_cached(tmp_cache):
    """system_one drīkst mest arī raw ValueError (nederīgs JSON ķermenis 200 atbildē,
    src/typesafe_client.py:53) — tam jākrīt atvērti tāpat kā TypeSafeUnavailable, un
    citu paku maksātās atbildes nedrīkst pazust."""
    calls: list[dict] = []
    real = _fake_answers(calls)

    def bad_json(state, questions, **kw):
        if state["rows"][0]["old"] == "vecā 2":
            raise ValueError("bad json")
        return real(state, questions, **kw)

    stats = JevStats()
    with patch("src.jev_filter.system_one", bad_json):
        probs = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1,
                           cache=tmp_cache, stats=stats)
    assert probs[:2] == pytest.approx([0.0, 0.1])
    assert probs[2:] == [None, None]

    # otrā rindu paketē samaksātās atbildes NAV pazudušas — tās ir kešā
    stats2 = JevStats()
    with patch("src.jev_filter.system_one", real):
        again = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1,
                           cache=tmp_cache, stats=stats2)
    assert len(calls) == 2                        # 1. skrējiena + 2. skrējiena 1 pieprasījums, ne 2
    assert stats2.cache_hits == 2
    assert again[:2] == pytest.approx([0.0, 0.1])
    assert again[2:] == pytest.approx([0.0, 0.1])


def test_malformed_answer_is_none_not_crash(tmp_cache):
    def bad(state, questions, **kw):
        return {"model": "x", "answers": {"r0": {"type": "noul"}}, "usage": {}}
    stats = JevStats()
    with patch("src.jev_filter.system_one", bad):
        result = judge_rows(_rows(1), INSTR, CRIT, workers=1, cache=tmp_cache, stats=stats)
    assert result == [None]
    assert stats.requests == 1 and stats.malformed == 1 and stats.unavailable == 0


def test_stats_summary_reports_denominator_and_cost():
    s = JevStats(requests=2, input_tokens=1_000_000, output_tokens=10, cache_hits=3,
                 unavailable=1, malformed=2, models={"jev-1.13.0"})
    assert s.est_usd == pytest.approx(jev_filter.USD_PER_M_INPUT)
    text = s.summary()
    for needle in ("pieprasījumi 2", "kešs 3", "nepieejamas 1", "kļūdainas 2", "1 000 000", "$0.04",
                   "modelis jev-1.13.0"):
        assert needle in text, text


def test_instructions_must_contain_row_placeholder(tmp_cache):
    with pytest.raises(ValueError):
        judge_rows(_rows(1), "bez viettura", CRIT, cache=tmp_cache)


def test_context_must_not_contain_rows_key(tmp_cache):
    with pytest.raises(ValueError):
        judge_rows(_rows(1), INSTR, CRIT, context={"rows": []}, cache=tmp_cache)


def test_duplicate_rows_sent_once_with_workers(tmp_cache):
    calls: list[dict] = []
    a, b = {"old": "sāls", "new": "cukurs"}, {"old": "ūdens", "new": "eļļa"}
    rows = [a, b, a, b, a, b]
    stats = JevStats()
    with patch("src.jev_filter.system_one", _fake_answers(calls)):
        probs = judge_rows(rows, INSTR, CRIT, batch_size=1, workers=4,
                           cache=tmp_cache, stats=stats)
    assert len(calls) == 2                         # tikai 2 unikālas rindas, sūtītas vienreiz
    assert all(isinstance(p, float) for p in probs)
    assert probs[0] == probs[2] == probs[4]
    assert probs[1] == probs[3] == probs[5]


def test_non_dict_body_is_unavailable_not_crash(tmp_cache):
    """Derīgs JSON, bet ne vārdnīca (T12 formāta maiņa) — pakete nepieejama, ne izņēmums."""
    stats = JevStats()
    with patch("src.jev_filter.system_one", lambda s, q, **kw: ["nav", "vārdnīca"]):
        assert judge_rows(_rows(2), INSTR, CRIT, workers=1, cache=tmp_cache, stats=stats) == [None, None]
    assert stats.requests == 0 and stats.unavailable == 2 and stats.malformed == 0
