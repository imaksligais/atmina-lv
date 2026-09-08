"""Regression: db.py functions must resolve DB_PATH at CALL time.

Functions previously declared ``db_path: str = DB_PATH`` bound the module
global at DEFINITION time, so ``monkeypatch.setattr(db, "DB_PATH", tmp)``
was a silent no-op for any caller that omitted the ``db_path`` argument —
the function kept reading the live production DB. The fix mirrors
``get_db``'s ``db_path: str | None = None`` + call-time resolution.

These tests call the functions with NO ``db_path`` argument, so they only
pass if the default resolves the monkeypatched global at call time.
"""

from src import db as db_module


def test_log_action_uses_monkeypatched_db_path(tmp_path, monkeypatch):
    db_path = str(tmp_path / "t.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    # No db_path arg — must land in the tmp DB, not the live one.
    db_module.log_action("test_action", status="success")

    row = db_module.get_last_log("test_action")  # also no db_path arg
    assert row is not None
    assert row["action"] == "test_action"

    # And it really went to the tmp DB.
    conn = db_module.get_db(db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM logs WHERE action = 'test_action'"
    ).fetchone()[0]
    conn.close()
    assert n == 1


def test_store_contradiction_uses_monkeypatched_db_path(tmp_path, monkeypatch):
    db_path = str(tmp_path / "t2.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    conn = db_module.get_db(db_path)
    conn.execute(
        "INSERT INTO tracked_politicians (id,name,relationship_type) "
        "VALUES (1,'Test Pol','tracked')"
    )
    # Seed two claims directly — store_contradiction only needs their ids.
    conn.execute(
        "INSERT INTO claims (id,opponent_id,topic,stance,claim_type,source_url,stated_at) "
        "VALUES (1,1,'Ekonomika','par','position','https://e.lv/1','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO claims (id,opponent_id,topic,stance,claim_type,source_url,stated_at) "
        "VALUES (2,1,'Ekonomika','pret','position','https://e.lv/2','2026-02-01')"
    )
    conn.commit()
    conn.close()

    # No db_path arg — must resolve the monkeypatched global at call time.
    cid = db_module.store_contradiction(
        1, 1, 2, "Ekonomika", "Mainīja nostāju",
        "reversal", 0.6,
    )
    assert cid > 0

    conn = db_module.get_db(db_path)
    n = conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
    conn.close()
    assert n == 1
