"""Zelta testa aprēķins — tīras funkcijas, bez DB rakstīšanas un bez API."""
from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

import pytest

from src.db import get_db, init_db


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


_spec = importlib.util.spec_from_file_location(
    "jev_contradiction_eval", Path(__file__).resolve().parent.parent / "scripts" / "jev_contradiction_eval.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def _gold(i, a, b, confirmed=1):
    return {"id": i, "opponent_id": 1, "old": a, "new": b, "confirmed": confirmed, "severity": "reversal"}


def test_summarize_counts_denominators_and_thresholds():
    gold = [_gold(1, 10, 11), _gold(2, 12, 13, confirmed=0), _gold(3, 14, 15)]   # #3 nav kandidātos
    probs = {frozenset((10, 11)): 0.92, frozenset((12, 13)): 0.55,
             frozenset((20, 21)): 0.10, frozenset((22, 23)): 0.70, frozenset((24, 25)): None}
    s = ev.summarize(gold, probs, [0.5, 0.9])
    assert s["gold_total"] == 3 and s["in_candidates"] == 2
    assert s["judged"] == 4 and s["unavailable"] == 1
    r05, r09 = s["rows"]
    assert (r05["threshold"], r05["gold_kept"], r05["gold_confirmed_kept"]) == (0.5, 2, 1)
    assert r05["candidates_kept"] == 3 and r05["kept_pct"] == pytest.approx(75.0)
    assert (r09["gold_kept"], r09["candidates_kept"]) == (1, 1)
    assert [d["id"] for d in s["gold_detail"]] == [1, 2, 3]
    assert s["gold_detail"][2]["p"] is None                       # ārpus kandidātiem = None


def test_select_sample_includes_gold_and_exactly_n_random_deterministic():
    all_pairs = [(i, i + 1) for i in range(0, 400, 2)]     # 200 unikāli pāri, stabila secība
    gold = [_gold(1, 0, 1), _gold(2, 100, 101)]             # abi ir all_pairs iekšā
    gold_keys = {frozenset((0, 1)), frozenset((100, 101))}

    sample = ev.select_sample(all_pairs, gold, n=10, seed=42)
    sample_keys = [frozenset(p) for p in sample]
    assert gold_keys <= set(sample_keys)                    # zelts vienmēr iekšā
    non_gold = [p for p in sample if frozenset(p) not in gold_keys]
    assert len(non_gold) == 10                              # tieši N nejauši
    assert len(sample) == len(set(sample))                  # nav dublikātu

    again = ev.select_sample(all_pairs, gold, n=10, seed=42)
    assert sample == again                                  # tas pats seed -> tas pats rezultāts

    other_seed = ev.select_sample(all_pairs, gold, n=10, seed=43)
    assert {frozenset(p) for p in other_seed} != {frozenset(p) for p in sample}


def test_question_tag_is_eight_hex_and_stable():
    tag = ev.question_tag()
    assert len(tag) == 8
    int(tag, 16)                                            # derīgs heksadecimāls
    assert tag == ev.question_tag()                          # stabils tajā pašā jautājumā


def test_render_puts_denominator_before_findings():
    gold = [_gold(1, 10, 11)]
    s = ev.summarize(gold, {frozenset((10, 11)): 0.9}, [0.5])
    from src.jev_filter import JevStats
    text = ev.render(s, JevStats(requests=1, input_tokens=1000))
    lines = text.splitlines()
    assert lines[0].startswith("Denominators:")
    assert "zelts 1, kandidātos 1" in lines[0]
    assert "0.5" in text and "1/1" in text


def test_gold_pairs_reads_only_position_pairs():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO documents (id, content, content_hash, scraped_at) "
               "VALUES (1, 'teksts', 'h1', '2025-01-01 00:00:00')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A B', 'P')")
    for cid, ct in ((1, "position"), (2, "position"), (3, "saeima_vote")):
        db.execute("INSERT INTO claims (id, opponent_id, topic, stance, source_url, claim_type, document_id) "
                   "VALUES (?, 1, 't', 's', 'https://x', ?, 1)", (cid, ct))
    db.execute("INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed) "
               "VALUES (1, 1, 1, 2, 't', 's', 'reversal', 1)")
    db.execute("INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed) "
               "VALUES (2, 1, 1, 3, 't', 's', 'minor_shift', 1)")
    db.commit()
    gold = ev.gold_pairs(db)
    db.close()
    _safe_unlink(path)
    assert [g["id"] for g in gold] == [1]
    assert gold[0] == {"id": 1, "opponent_id": 1, "old": 1, "new": 2, "confirmed": 1, "severity": "reversal"}
