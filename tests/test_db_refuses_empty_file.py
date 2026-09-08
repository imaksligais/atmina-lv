"""`get_db()` must refuse an existing 0-byte DB file.

BACKLOG 2026-08-03 (§ Repo higiēna): eleven 0-byte `.db` files proved that a
connect with a wrong path silently creates an empty DB and work dies in it —
the same defect class as the bare `python` interpreter trap. SQLite treats a
0-byte file as a perfectly valid new database, so nothing downstream fails
loudly; the refusal has to live at open time.

`init_db()` is the one legitimate writer of an empty file (fixtures do
mkstemp → init_db), so it opts out explicitly.
"""

import os
import tempfile

import pytest

from src.db import get_db, init_db


def _safe_unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def test_get_db_refuses_existing_zero_byte_file():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # exists, 0 bytes — the accident state
    try:
        with pytest.raises(RuntimeError, match="0-byte"):
            get_db(path)
    finally:
        _safe_unlink(path)


def test_init_db_still_initializes_a_fresh_empty_file():
    """mkstemp → init_db is every fixture's setup path; it must keep working."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        init_db(path)  # must not raise: initialization is the legitimate writer
        db = get_db(path)  # non-empty now, opens normally
        tables = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        db.close()
        assert "claims" in tables
    finally:
        _safe_unlink(path)


def test_get_db_still_creates_nonexistent_path():
    """A path that does not exist yet is not the accident state — sqlite
    creates it lazily and init_db/schema writes follow. Only an EXISTING
    empty file is refused."""
    path = os.path.join(tempfile.gettempdir(), "atmina_test_fresh_9b1.db")
    _safe_unlink(path)
    try:
        db = get_db(path)
        db.close()
    finally:
        _safe_unlink(path)
