"""Tests for src.graphics.storage — brief_images CRUD helpers."""
import sqlite3
import pytest
from src.graphics import storage


@pytest.fixture
def memdb():
    """In-memory DB with the brief_images + minimal context_notes schema."""
    db = sqlite3.connect(":memory:")
    db.execute("""
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, note_type TEXT, created_at TEXT
        )
    """)
    db.execute("""
        CREATE TABLE brief_images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id       INTEGER NOT NULL,
            image_path    TEXT NOT NULL,
            prompt        TEXT NOT NULL,
            model         TEXT NOT NULL,
            seed          INTEGER,
            aspect        TEXT NOT NULL DEFAULT '16:9',
            width         INTEGER, height INTEGER,
            generated_at  TEXT NOT NULL,
            cost_usd      REAL NOT NULL DEFAULT 0.039,
            approved      INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)
    db.execute(
        "INSERT INTO context_notes (id, content, note_type, created_at) "
        "VALUES (1, 'c', 'daily_brief', '2026-04-17 10:00:00')"
    )
    db.commit()
    yield db
    db.close()


def test_compute_filename_produces_stable_hash():
    png = b"fake image bytes"
    name = storage.compute_filename("2026-04-17-test", png)
    assert name.startswith("2026-04-17-test-")
    assert name.endswith(".png")
    # hash segment is 8 hex chars
    hash_part = name[len("2026-04-17-test-"):-len(".png")]
    assert len(hash_part) == 8
    all_hex = all(c in "0123456789abcdef" for c in hash_part)
    assert all_hex, f"hash segment not hex: {hash_part!r}"


def test_compute_filename_same_input_same_output():
    name1 = storage.compute_filename("slug", b"bytes")
    name2 = storage.compute_filename("slug", b"bytes")
    assert name1 == name2


def test_compute_filename_different_bytes_different_hash():
    name1 = storage.compute_filename("slug", b"bytes-a")
    name2 = storage.compute_filename("slug", b"bytes-b")
    assert name1 != name2


def test_save_image_row_returns_id_and_sets_pending(memdb):
    image_id = storage.save_image_row(
        memdb, note_id=1, image_path="images/briefs/x-ab12cd34.png",
        prompt="prompt", model="test-model", seed=None,
        width=1408, height=768, cost=0.039,
    )
    assert isinstance(image_id, int) and image_id > 0
    row = memdb.execute(
        "SELECT approved, error_message, aspect FROM brief_images WHERE id=?",
        (image_id,),
    ).fetchone()
    assert row == (0, None, "16:9")


def test_save_image_row_populates_generated_at(memdb):
    image_id = storage.save_image_row(
        memdb, 1, "p.png", "pr", "m", None, 1, 1, 0.039,
    )
    row = memdb.execute(
        "SELECT generated_at FROM brief_images WHERE id=?", (image_id,)
    ).fetchone()
    assert row[0] is not None and len(row[0]) >= 10  # some ISO-like string


def test_approve_image_sets_approved_1(memdb):
    iid = storage.save_image_row(memdb, 1, "p", "pr", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid)
    row = memdb.execute("SELECT approved FROM brief_images WHERE id=?", (iid,)).fetchone()
    assert row[0] == 1


def test_reject_image_sets_approved_2_with_reason(memdb):
    iid = storage.save_image_row(memdb, 1, "p", "pr", "m", None, 1, 1, 0.039)
    storage.reject_image(memdb, iid, "poor diacritics")
    row = memdb.execute(
        "SELECT approved, error_message FROM brief_images WHERE id=?", (iid,)
    ).fetchone()
    assert row == (2, "poor diacritics")


def test_save_error_row_marks_approved_2(memdb):
    iid = storage.save_error_row(memdb, 1, "the prompt", "model-x", "SAFETY_BLOCKED")
    row = memdb.execute(
        "SELECT approved, error_message, image_path, cost_usd FROM brief_images WHERE id=?",
        (iid,),
    ).fetchone()
    assert row[0] == 2
    assert row[1] == "SAFETY_BLOCKED"
    assert row[2] == ""  # empty image_path for error rows
    assert row[3] == 0.0  # no cost for errored calls


def test_get_approved_image_returns_latest_approved(memdb):
    iid1 = storage.save_image_row(memdb, 1, "old.png", "p", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid1)
    iid2 = storage.save_image_row(memdb, 1, "new.png", "p", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid2)
    assert storage.get_approved_image(memdb, 1) == "new.png"


def test_get_approved_image_returns_none_when_no_approved(memdb):
    storage.save_image_row(memdb, 1, "pending.png", "p", "m", None, 1, 1, 0.039)
    assert storage.get_approved_image(memdb, 1) is None


def test_get_approved_image_ignores_rejected(memdb):
    iid = storage.save_image_row(memdb, 1, "bad.png", "p", "m", None, 1, 1, 0.039)
    storage.reject_image(memdb, iid, "too ugly")
    assert storage.get_approved_image(memdb, 1) is None


def test_get_attempts_returns_all_rows_newest_first(memdb):
    iid1 = storage.save_image_row(memdb, 1, "a.png", "p", "m", None, 1, 1, 0.039)
    iid2 = storage.save_image_row(memdb, 1, "b.png", "p", "m", None, 1, 1, 0.039)
    attempts = storage.get_attempts(memdb, 1)
    assert len(attempts) == 2
    assert attempts[0]["id"] == iid2  # newest first
    assert attempts[1]["id"] == iid1
    # Dict shape check
    keys_required = {"id", "image_path", "prompt", "approved", "error_message",
                     "generated_at", "cost_usd"}
    assert keys_required <= set(attempts[0].keys())


def test_monthly_cost_usd_sums_current_month(memdb):
    # Insert rows with explicit generated_at values in current Latvia month
    from src.db import now_lv
    this_month = now_lv()[:7]  # 'YYYY-MM'
    memdb.execute(
        "INSERT INTO brief_images "
        "(note_id, image_path, prompt, model, aspect, generated_at, cost_usd, approved) "
        "VALUES (1, 'a.png', 'p', 'm', '16:9', ?, 0.04, 1)",
        (this_month + "-10 12:00:00",),
    )
    memdb.execute(
        "INSERT INTO brief_images "
        "(note_id, image_path, prompt, model, aspect, generated_at, cost_usd, approved) "
        "VALUES (1, 'b.png', 'p', 'm', '16:9', ?, 0.05, 1)",
        (this_month + "-15 12:00:00",),
    )
    memdb.commit()
    total = storage.monthly_cost_usd(memdb)
    assert abs(total - 0.09) < 1e-9


def test_monthly_cost_usd_excludes_other_months(memdb):
    memdb.execute(
        "INSERT INTO brief_images "
        "(note_id, image_path, prompt, model, aspect, generated_at, cost_usd, approved) "
        "VALUES (1, 'x.png', 'p', 'm', '16:9', '2025-01-01 00:00:00', 0.10, 1)"
    )
    memdb.commit()
    total = storage.monthly_cost_usd(memdb)
    assert total == 0.0


def test_monthly_cost_usd_empty_table_returns_zero(memdb):
    assert storage.monthly_cost_usd(memdb) == 0.0


def test_monthly_cost_usd_uses_year_month_prefix_format(memdb, monkeypatch):
    """Guard against now_lv() format changes breaking the budget slice.

    If now_lv() ever returns something that doesn't start with 'YYYY-MM',
    the [:7] slice in monthly_cost_usd becomes meaningless. Pin the format
    by asserting that a row with an explicit 'YYYY-MM' prefix is picked up
    when now_lv() is patched to return a matching date.
    """
    from src.graphics import storage as storage_module
    monkeypatch.setattr(storage_module, "now_lv", lambda: "2026-04-17 12:00:00")
    memdb.execute(
        "INSERT INTO brief_images "
        "(note_id, image_path, prompt, model, aspect, generated_at, cost_usd, approved) "
        "VALUES (1, 'x.png', 'p', 'm', '16:9', '2026-04-01 08:00:00', 0.07, 1)"
    )
    memdb.execute(
        "INSERT INTO brief_images "
        "(note_id, image_path, prompt, model, aspect, generated_at, cost_usd, approved) "
        "VALUES (1, 'y.png', 'p', 'm', '16:9', '2026-05-01 08:00:00', 0.11, 1)"
    )
    memdb.commit()
    total = storage_module.monthly_cost_usd(memdb)
    assert abs(total - 0.07) < 1e-9, f"expected 0.07, got {total}"
