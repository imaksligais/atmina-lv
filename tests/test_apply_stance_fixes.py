"""End-to-end test for scripts/apply_stance_fixes.py (stance-checker fixes).

Failures named first:
1. An unapproved plan reaches live rows — `--apply` runs without a committed
   rollback (missing file, or present but not git-tracked).
2. Apply touches more than it was approved for, or cannot be undone — it
   rewrites `quote`, re-embeds rows whose stance did not change, or the
   rollback file cannot restore the old stance / stated_at.
"""

import json
from pathlib import Path

import pytest

import src.db
from scripts import apply_stance_fixes as asf
from src.db import get_db, init_db

OLD = "Uzskata, ka 'Jaunās Vienotības' valdība ir pilnīgi izgāzusies"
NEW = "Uzskata, ka valdība nav izpildījusi solījumus"
QUOTE = "Valdība nav izpildījusi savus solījumus, viņi ir izgāzušies."


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Politiķis', 'X')")
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (10, 'teksts', 'h10')")
    for cid in (101, 102):
        db.execute(
            """INSERT INTO claims (id, opponent_id, document_id, topic, stance, quote, source_url,
                                   stated_at, created_at)
               VALUES (?, 1, 10, 'Budžets', ?, ?, 'https://x/1', '2026-10-01 12:00:00',
                       '2026-10-14 16:00:00')""",
            (cid, OLD, QUOTE),
        )
    db.commit()
    db.close()
    monkeypatch.setattr(src.db, "DB_PATH", path)
    monkeypatch.setattr(asf, "DATA_DIR", tmp_path)
    monkeypatch.setattr(asf, "current_routine_day", lambda: "2026-10-14")
    reembedded: list[list[int]] = []
    monkeypatch.setattr(asf, "reembed_ids", lambda ids: reembedded.append(list(ids)) or len(ids))
    fixes = tmp_path / "fixes.json"
    fixes.write_text(json.dumps([
        {"id": 101, "stance": NEW, "stated_at": None},
        {"id": 102, "stance": None, "stated_at": "2026-09-30"},
    ]), encoding="utf-8")
    return {"path": path, "fixes": str(fixes), "reembedded": reembedded,
            "rollback": tmp_path / "rollback_stance_2026-10-14_fixes.sql"}


def _rows(path):
    db = get_db(path)
    rows = {r["id"]: dict(r) for r in db.execute("SELECT id, stance, stated_at, quote FROM claims")}
    db.close()
    return rows


def test_apply_refuses_without_committed_rollback(env, monkeypatch):
    before = _rows(env["path"])
    monkeypatch.setattr(asf, "is_git_tracked", lambda p: True)  # isolate the missing-file guard
    assert asf.main(["--fixes", env["fixes"], "--apply"]) == 2  # no rollback file
    assert _rows(env["path"]) == before

    assert asf.main(["--fixes", env["fixes"], "--write-rollback"]) == 0
    monkeypatch.setattr(asf, "is_git_tracked", lambda p: False)
    assert asf.main(["--fixes", env["fixes"], "--apply"]) == 2  # file present, not committed
    assert _rows(env["path"]) == before

    monkeypatch.setattr(asf, "is_git_tracked", lambda p: True)
    fixes = Path(env["fixes"])
    fixes.write_text(json.dumps(json.loads(fixes.read_text(encoding="utf-8"))[:1]), encoding="utf-8")
    assert asf.main(["--fixes", env["fixes"], "--apply"]) == 2  # rollback covers another id set
    assert _rows(env["path"]) == before
    assert env["reembedded"] == []


def test_apply_updates_only_approved_fields_and_rollback_holds_old(env, monkeypatch):
    assert asf.main(["--fixes", env["fixes"], "--write-rollback"]) == 0
    monkeypatch.setattr(asf, "is_git_tracked", lambda p: True)
    assert asf.main(["--fixes", env["fixes"], "--apply"]) == 0

    rows = _rows(env["path"])
    assert rows[101]["stance"] == NEW and rows[101]["stated_at"] == "2026-10-01 12:00:00"
    assert rows[102]["stance"] == OLD and rows[102]["stated_at"] == "2026-09-30 00:00:00"
    assert rows[101]["quote"] == rows[102]["quote"] == QUOTE
    assert env["reembedded"] == [[101]]  # only the row whose stance changed

    rb = env["rollback"].read_text(encoding="utf-8")
    assert NEW not in rb
    db = get_db(env["path"])
    db.executescript(rb)  # the rollback must run and restore the old values
    db.close()
    rows = _rows(env["path"])
    assert rows[101]["stance"] == rows[102]["stance"] == OLD
    assert rows[102]["stated_at"] == "2026-10-01 12:00:00"
