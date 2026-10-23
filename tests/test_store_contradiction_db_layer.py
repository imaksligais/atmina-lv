"""`src.db.store_contradiction` validē pats un pieņem `party_id` (2026-10-18).

Kļūme, ko šie testi nosauc: validācija dzīvoja tikai `src.tools` apvalkā, tāpēc
tiešs `src.db.store_contradiction(severity='nepareizs')` klusi ierakstīja rindu;
partiju pretrunu 4. solis (`party_id=...`) krita ar `TypeError`.
"""

import json
import sqlite3
import sys

import pytest

import src.db as db_module
from src.db import get_db, init_db, store_contradiction


@pytest.fixture
def seeded(tmp_path):
    path = str(tmp_path / "t.db")
    init_db(path)
    raw = sqlite3.connect(path)
    raw.execute("INSERT INTO tracked_politicians (id, name) VALUES (1, 'Test')")
    raw.execute("INSERT INTO parties (id, name, short_name) VALUES (7, 'Testa partija', 'TP')")
    raw.execute("INSERT INTO claims (id, opponent_id, topic, stance) "
                "VALUES (1, 1, 'NATO', 'a'), (2, 1, 'NATO', 'b')")
    raw.commit()
    raw.close()
    return path


def _count(path):
    db = get_db(path)
    n = db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
    db.close()
    return n


OK = dict(opponent_id=1, old_claim_id=1, new_claim_id=2, topic="NATO",
          summary="Mainīja nostāju", severity="reversal", salience=0.5)


@pytest.mark.parametrize("bad", [
    {"severity": "nepareizs"},
    {"salience": 5.0},
    {"headline": "x" * 61},
    {"headline": "rinda\notrā"},
])
def test_invalid_row_raises_before_insert(seeded, bad):
    with pytest.raises(ValueError):
        store_contradiction(**{**OK, **bad}, db_path=seeded)
    assert _count(seeded) == 0


def test_party_id_is_stored_and_row_stays_unconfirmed(seeded):
    cid = store_contradiction(**OK, db_path=seeded, party_id=7)
    db = get_db(seeded)
    row = db.execute("SELECT party_id, confirmed FROM contradictions WHERE id=?",
                     (cid,)).fetchone()
    db.close()
    assert row["party_id"] == 7
    assert row["confirmed"] == 0  # eskalācija 3: nekad automātiski neapstiprina


def test_tools_wrapper_passes_party_id_and_reports_db_error(seeded, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", seeded)
    import src.tools as tools
    ok = json.loads(tools.store_contradiction(**OK, party_id=7))
    assert ok["status"] == "success", ok
    bad = json.loads(tools.store_contradiction(**{**OK, "severity": "nepareizs"}))
    assert bad["status"] == "error"
    assert _count(seeded) == 1


def test_partiju_pretrunas_script_runs_on_temp_db(seeded, monkeypatch, capsys):
    """Smoke: piltuves skripts palaižas uz pagaidu DB (tas pats nekā neraksta)."""
    monkeypatch.setattr(db_module, "DB_PATH", seeded)
    import scripts.partiju_pretrunas as script
    monkeypatch.setattr(sys, "argv", ["partiju_pretrunas.py", "--json"])
    script.main()
    out = json.loads(capsys.readouterr().out)
    assert "stats" in out and out["candidates"] == []
    assert _count(seeded) == 0
