"""End-to-end test for scripts/resolve_needs_review.py (/dienas-rutina solis 2c).

Failures named first:
1. An uncommitted plan reaches live rows — `--apply` runs with no rollback
   file, an uncommitted one, or one written for a different id set.
2. A resolved row stays in the review queue, or the resolution cannot be
   undone — the marker word survives in the new text (the trigger would flag
   the row again), `stance` is touched, or the rollback does not restore the
   marker and the queue status.
"""

import json

import pytest

import src.db
from scripts import resolve_needs_review as rnr
from src.db import get_db, init_db

FLAGGED = "NEEDS_REVIEW: ļoti īss teksts. Paša atbilde pavedienā."
PLAIN = "Paša tvīts, tiešs apgalvojums."
EVIDENCE = "paša atbilde uz jautājumu «kāpēc?» (doc 10); stance paliek tvīta vārdos"


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Politiķis', 'X')")
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (10, 'teksts', 'h10')")
    # 104: an old tweet extracted today — stated_at is outside the brief window,
    # created_at is inside the routine day (2026-11-18: 3 such rows were missed).
    for cid, reasoning, stated in ((101, FLAGGED, "2026-11-12 12:00:00"), (102, FLAGGED, "2026-11-12 12:00:00"),
                                   (103, PLAIN, "2026-11-12 12:00:00"), (104, FLAGGED, "2022-05-01 09:00:00")):
        db.execute(
            """INSERT INTO claims (id, opponent_id, document_id, topic, stance, reasoning, source_url,
                                   stated_at, created_at)
               VALUES (?, 1, 10, 'Budžets', 'Stance.', ?, ?, ?, '2026-11-12 16:00:00')""",
            (cid, reasoning, f"https://x/{cid}", stated),
        )
    db.commit()
    db.close()
    monkeypatch.setattr(src.db, "DB_PATH", path)
    monkeypatch.setattr(rnr, "DATA_DIR", tmp_path)
    monkeypatch.setattr(rnr, "current_routine_day", lambda: "2026-11-12")
    monkeypatch.setattr(rnr, "now_lv", lambda: "2026-11-12 22:00:00")
    decisions = tmp_path / "d.json"
    decisions.write_text(json.dumps([{"id": 101, "evidence": EVIDENCE}, {"id": 102, "evidence": EVIDENCE}]),
                         encoding="utf-8")
    return {"path": path, "decisions": decisions, "rollback": tmp_path / "rollback_needs_review_rutina_2026-11-12.sql"}


def _rows(path):
    db = get_db(path)
    rows = {r["id"]: dict(r) for r in db.execute("SELECT id, stance, reasoning, review_status FROM claims")}
    db.close()
    return rows


def test_apply_refuses_without_committed_matching_rollback(env, monkeypatch):
    before = _rows(env["path"])
    args = ["--decisions", str(env["decisions"])]
    monkeypatch.setattr(rnr, "is_committed", lambda p: True)  # isolate the missing-file guard
    assert rnr.main([*args, "--apply"]) == 2  # no rollback file

    monkeypatch.setattr(rnr, "is_committed", lambda p: False)
    assert rnr.main([*args, "--write-rollback"]) == 0
    assert rnr.main([*args, "--apply"]) == 2  # file present, not committed

    monkeypatch.setattr(rnr, "is_committed", lambda p: True)
    env["decisions"].write_text(json.dumps([{"id": 101, "evidence": EVIDENCE}]), encoding="utf-8")
    assert rnr.main([*args, "--apply"]) == 2  # rollback covers another id set

    # A row that carries no marker refuses the whole batch, not just itself.
    env["decisions"].write_text(
        json.dumps([{"id": 101, "evidence": EVIDENCE}, {"id": 103, "evidence": EVIDENCE}]), encoding="utf-8")
    assert rnr.main([*args, "--apply"]) == 2
    assert _rows(env["path"]) == before


def test_apply_resolves_the_queue_rows_and_rollback_restores_them(env, monkeypatch, capsys):
    before = _rows(env["path"])
    assert before[101]["review_status"] == "needs_review"
    assert rnr.main(["--list", "--day", "2026-11-12"]) == 0  # the rows to decide, with their source
    listed = capsys.readouterr().out
    assert "===== 101 |" in listed and "===== 102 |" in listed and "===== 103" not in listed
    assert "===== 104 |" in listed, "backdated row created today is missing from --list"
    assert "teksts:    teksts" in listed
    args = ["--decisions", str(env["decisions"])]
    monkeypatch.setattr(rnr, "is_committed", lambda p: False)
    assert rnr.main([*args, "--write-rollback"]) == 0
    monkeypatch.setattr(rnr, "is_committed", lambda p: True)
    assert rnr.main([*args, "--apply"]) == 0

    rows = _rows(env["path"])
    expected = f"Izvērtēts 2026-11-12: {EVIDENCE}. Sākotnēji: ļoti īss teksts. Paša atbilde pavedienā."
    assert rows[101]["reasoning"] == rows[102]["reasoning"] == expected
    assert rows[101]["review_status"] == rows[102]["review_status"] == "reviewed"
    assert rows[103] == before[103]
    assert rows[101]["stance"] == "Stance."

    db = get_db(env["path"])
    db.executescript(env["rollback"].read_text(encoding="utf-8"))  # must run and restore
    db.close()
    assert _rows(env["path"]) == before
