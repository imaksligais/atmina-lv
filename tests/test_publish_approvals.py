"""`scripts/approve_publish.py` — operatora eksplicītais publicēšanas karogs.

Kāpēc šis fails eksistē: publish-gate v1 (2026-08-09) pieņēma attēla
apstiprinājumu par publicēšanas atļauju. Attēls pierāda tikai to, ka attēls ir
izvēlēts — korektūra un operatora atļauja tur nav. Šis CLI ir vienīgais rakstītājs
`publish_approvals` tabulā, tāpēc tam jābūt pierādāmi krītošam: nederīga atslēga
neraksta neko, atsaukšana tiešām dzēš, un atkārtots apstiprinājums nav dublikāts.
"""

from __future__ import annotations

import gc
import importlib.util
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

from src.db import init_db

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "approve_publish", REPO / "scripts" / "approve_publish.py"
)
approve_publish = importlib.util.module_from_spec(_spec)
sys.modules["approve_publish"] = approve_publish
_spec.loader.exec_module(approve_publish)


@pytest.fixture
def db_file():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    gc.collect()
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _keys(path):
    con = sqlite3.connect(path)
    rows = [r[0] for r in con.execute("SELECT subject_key FROM publish_approvals")]
    con.close()
    return rows


def test_approve_writes_row_with_lv_timestamp(db_file):
    assert approve_publish.approve("2026-08-18", db_path=db_file) == 0
    con = sqlite3.connect(db_file)
    row = con.execute(
        "SELECT subject_key, approved_at FROM publish_approvals"
    ).fetchone()
    con.close()
    assert row[0] == "2026-08-18"
    assert len(row[1]) == 19 and row[1][4] == "-", row  # now_lv() forma


def test_approve_accepts_weekly_key(db_file):
    assert approve_publish.approve("nedela-2026-08-10", db_path=db_file) == 0
    assert _keys(db_file) == ["nedela-2026-08-10"]


def test_approve_rejects_garbage_key(db_file):
    assert approve_publish.approve("rītdien", db_path=db_file) == 1
    assert _keys(db_file) == []


def test_approve_is_idempotent(db_file):
    approve_publish.approve("2026-08-18", db_path=db_file)
    approve_publish.approve("2026-08-18", db_path=db_file)
    assert _keys(db_file) == ["2026-08-18"]


def test_revoke_removes_row(db_file):
    approve_publish.approve("2026-08-18", db_path=db_file)
    assert approve_publish.revoke("2026-08-18", db_path=db_file) == 0
    assert _keys(db_file) == []


def test_revoke_missing_row_reports_failure(db_file):
    """Klusa veiksme ir defektu klase: atsaukšana, kas neko neatsauca, nedrīkst
    izskatīties kā izdevusies."""
    assert approve_publish.revoke("2026-08-18", db_path=db_file) == 1


def test_list_prints_denominator(db_file, capsys):
    approve_publish.approve("2026-08-18", db_path=db_file)
    assert approve_publish.list_recent(db_path=db_file) == 0
    out = capsys.readouterr().out
    assert "2026-08-18" in out
    assert "1" in out  # kopskaits = saucējs
