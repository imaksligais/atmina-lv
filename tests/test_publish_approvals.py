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


def _store_daily_brief(path, day, bloc_count):
    """Dienas pārskats ar 2 tēmu tabulu rindām (viena «Pārējās tēmās») un
    bloku tabulu, kuras «Pozīcijas» summa ir `bloc_count`."""
    content = (
        f"# Dienas analīze — {day}\n\n"
        "## Galvenās tēmas\n\n### Budžets (1 pozīcija)\n\n"
        "| Politiķis | Partija | Pozīcija | Avots |\n|---|---|---|---|\n"
        "| A | JV | x | [lsm.lv](https://lsm.lv/1) |\n\n"
        "### Pārējās tēmas (1 pozīcija 1 tēmā)\n\n"
        "| Politiķis | Partija | Tēma | Pozīcija | Avots |\n|---|---|---|---|---|\n"
        "| B | NA | Aizsardzība | y | [x.com](https://x.com/b/1) |\n\n"
        "## Koalīcija vs Opozīcija\n\n"
        "| Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas |\n"
        "|---|---|---|---|---|\n"
        f"| Koalīcija | {bloc_count - 1} | JV, NA | A (1) | Budžets |\n"
        "| Opozīcija | 1 | PRO | C (1) | Budžets |\n"
    )
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO context_notes (note_type, topic, content, created_at)"
        " VALUES ('daily_brief', ?, ?, ?)",
        (f"dienas analīze {day}", content, f"{day} 22:00:00"),
    )
    con.commit()
    con.close()


def test_approve_refuses_brief_whose_tables_disagree(db_file, capsys):
    """Kļūme (#672, 2026-10-06): brief-writer izņem rindu no tēmu tabulas, bloku
    tabula paliek vecā — lapa rāda divus pozīciju skaitļus. Vārti to atsaka un
    neko neieraksta; sakrītošs pārskats iet cauri."""
    _store_daily_brief(db_file, "2026-10-05", bloc_count=3)  # rindas 2, bloki 3
    assert approve_publish.approve("2026-10-05", db_path=db_file) == 1
    assert _keys(db_file) == []
    err = capsys.readouterr().err
    assert "tēmu tabulās 2" in err and "bloku tabulā 3" in err

    _store_daily_brief(db_file, "2026-10-06", bloc_count=2)
    assert approve_publish.approve("2026-10-06", db_path=db_file) == 0
    assert _keys(db_file) == ["2026-10-06"]


def test_list_prints_denominator(db_file, capsys):
    approve_publish.approve("2026-08-18", db_path=db_file)
    assert approve_publish.list_recent(db_path=db_file) == 0
    out = capsys.readouterr().out
    assert "2026-08-18" in out
    assert "1" in out  # kopskaits = saucējs
