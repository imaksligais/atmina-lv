"""Tests for src/extraction_plan.py — @claim-extractor batching planner.

Fixture follows tests/test_analyze.py (mkstemp + init_db); tests/conftest.py
has no DB factory. Shape mirrors the 2026-09-23 evening queue: one big queue
split across rounds, small queues packed, pure RTs (incl. one doc with two
subject politicians) moved to a last-round RT agent.
"""

import os
import tempfile
from datetime import timedelta

import pytest

from src.db import get_db, init_db, now_lv_dt

SMALL1, SMALL2, MID, BIG, HUGE = 1, 2, 3, 4, 5
RT_SHARED = 900


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def plan_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    names = {SMALL1: "Mazais Viens", SMALL2: "Mazais Divi", MID: "Vidējais",
             BIG: "Lielais", HUGE: "Milzīgais"}
    for pid, name in names.items():
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (?, ?, 'X')",
                   (pid, name))
    base = now_lv_dt()
    seq = [0]

    def doc(doc_id, content, pids):
        seq[0] += 1
        ts = (base - timedelta(minutes=seq[0])).strftime("%Y-%m-%d %H:%M:%S")
        db.execute("INSERT INTO documents (id, content, content_hash, scraped_at, platform) "
                   "VALUES (?, ?, ?, ?, 'twitter')", (doc_id, content, f"h{doc_id}", ts))
        for pid in pids:
            db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
                       "VALUES (?, ?, 'subject')", (doc_id, pid))

    counts = {SMALL1: 1, SMALL2: 2, MID: 5, BIG: 14, HUGE: 25}
    next_id = 100
    for pid, n in counts.items():
        for _ in range(n):
            doc(next_id, f"Paša teksts {next_id} par budžetu", [pid])
            next_id += 1
    doc(RT_SHARED, "RT @LTV: kopīgs pārpublicējums", [SMALL1, SMALL2])
    doc(901, "  RT @x: vidējā pārpublicējums", [MID])
    doc(902, "RT @y: lielā pārpublicējums", [BIG])
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def plan(plan_db):
    from src.extraction_plan import plan_extraction_batches
    return plan_extraction_batches(days=1, db=plan_db)


def test_no_pid_twice_in_same_round(plan):
    for rnd in {a["round"] for a in plan["agents"]}:
        pids = [it["pid"] for a in plan["agents"] if a["round"] == rnd for it in a["items"]]
        assert len(pids) == len(set(pids))


def test_rt_agents_run_last(plan):
    last = max(a["round"] for a in plan["agents"])
    assert all(a["round"] == last for a in plan["agents"] if a["kind"] == "rt")
    assert all(a["kind"] == "rt" for a in plan["agents"] if a["round"] == last) or \
        not any(a["kind"] == "rt" for a in plan["agents"])
    assert any(a["kind"] == "rt" for a in plan["agents"])  # fixture has RTs


def test_big_queue_split_into_rounds(plan):  # 14 doki, cap=12 → 12 + 2
    rounds = sorted((a["round"], sum(len(i["doc_ids"]) for i in a["items"]))
                    for a in plan["agents"] if any(i["pid"] == BIG for i in a["items"])
                    and a["kind"] != "rt")
    assert [n for _, n in rounds] == [12, 2]


def test_queue_over_20_not_truncated(plan):  # get_politician_documents default cap = 20
    n = sum(len(i["doc_ids"]) for a in plan["agents"] if a["kind"] != "rt"
            for i in a["items"] if i["pid"] == HUGE)
    assert n == 25


def test_pack_respects_pack_docs(plan):
    for a in plan["agents"]:
        if a["kind"] == "pack":
            assert sum(len(i["doc_ids"]) for i in a["items"]) <= 8
    packed = {i["pid"] for a in plan["agents"] if a["kind"] == "pack" for i in a["items"]}
    assert packed == {SMALL1, SMALL2}


def test_rt_docs_only_in_rt_agents(plan):
    rt_ids = {RT_SHARED, 901, 902}
    for a in plan["agents"]:
        ids = {d for i in a["items"] for d in i["doc_ids"]}
        if a["kind"] == "rt":
            assert ids <= rt_ids
        else:
            assert not ids & rt_ids
    assert plan["summary"]["rt_docs"] == 3


def test_docs_newest_first(plan):
    mid = [i for a in plan["agents"] if a["kind"] == "solo" for i in a["items"]
           if i["pid"] == MID][0]
    assert mid["doc_ids"] == sorted(mid["doc_ids"])  # ids inserted newest → oldest


def test_summary_denominators(plan):
    s = plan["summary"]
    all_pairs = [(i["pid"], d) for a in plan["agents"] for i in a["items"] for d in i["doc_ids"]]
    assert s["pairs"] == len(all_pairs) == len(set(all_pairs))
    assert s["docs"] == len({d for _, d in all_pairs})   # kopīgais doks skaitās vienreiz
    assert s["agents"] == len(plan["agents"]) > 0
    assert s["politicians"] == 5
    assert s["rounds"] == max(a["round"] for a in plan["agents"])


def test_small_rt_pack_never_splits_pid_within_round(plan_db):
    from src.extraction_plan import plan_extraction_batches
    p = plan_extraction_batches(days=1, rt_pack=1, db=plan_db)
    for rnd in {a["round"] for a in p["agents"]}:
        pids = [it["pid"] for a in p["agents"] if a["round"] == rnd for it in a["items"]]
        assert len(pids) == len(set(pids))


def test_empty_queue(tmp_path):
    from src.extraction_plan import plan_extraction_batches
    path = str(tmp_path / "e.db")
    init_db(path)
    p = plan_extraction_batches(days=1, db=path)
    assert p["agents"] == [] and p["summary"]["agents"] == 0 and p["summary"]["rounds"] == 0


def test_is_pure_retweet():
    from src.extraction_plan import is_pure_retweet
    assert is_pure_retweet("RT @LTV: teksts") and is_pure_retweet("  RT @x: y")
    assert not is_pure_retweet("Piekrītu. RT @x") and not is_pure_retweet(None)


@pytest.mark.parametrize("status,shown", [("partial", True), ("missing", True),
                                          ("done", False), ("n/a", False)])
def test_print_routine_plan_line_only_when_analysis_open(status, shown, tmp_path,
                                                         monkeypatch, capsys):
    import src.db as dbmod
    import src.extraction_plan as ep
    import src.routine as routine
    path = str(tmp_path / "r.db")
    init_db(path)
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    monkeypatch.setattr(routine, "check_routine", lambda d: {
        "all_complete": False,
        "steps": {"analysis": {"status": status, "details": "x"}}})
    monkeypatch.setattr(ep, "plan_extraction_batches", lambda days=1, **k: {
        "agents": [], "summary": {"politicians": 49, "docs": 126, "pairs": 130,
                                  "rt_docs": 55, "agents": 9, "rounds": 3}})
    routine.print_routine("2026-09-23")  # past day → no afternoon gate
    out = capsys.readouterr().out
    line = "PLĀNS: 9 aģenti / 3 kārtas (49 politiķi, 126 doki, RT 55)"
    assert (line in out) is shown


def test_pending_politician_without_docs_is_reported_not_dropped(plan_db, monkeypatch):
    """Rindas lasītāji nesaskan (pid rindā, bet 0 doku) → `dropped`, ne klusums."""
    import src.analyze as an
    from src.extraction_plan import format_plan_line, plan_extraction_batches
    real = an.get_politician_documents

    def fake(pid, days, max_results=20):
        return [] if pid == MID else real(pid, days, max_results=max_results)

    monkeypatch.setattr(an, "get_politician_documents", fake)
    s = plan_extraction_batches(days=1, db=plan_db)["summary"]
    assert s["pending"] == 5 and s["politicians"] == 4
    assert [d["pid"] for d in s["dropped"]] == [MID]
    assert s["dropped"][0]["name"] == "Vidējais" and s["dropped"][0]["reason"]
    assert "IZMESTI 1 no 5" in format_plan_line(s)


def test_plan_line_silent_when_nothing_dropped(plan):
    from src.extraction_plan import format_plan_line
    assert plan["summary"]["dropped"] == [] and plan["summary"]["pending"] == 5
    assert "IZMESTI" not in format_plan_line(plan["summary"])
