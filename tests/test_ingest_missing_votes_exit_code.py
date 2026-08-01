"""Bulk ielāde, kas daļu ievades zaudēja, nedrīkst iziet ar 0.

2026-08-01, pirmajā 2026. gada partijā: 459 balsojumi, viens izkrita ar tīkla
noildzi. `failed: 1` bija kopsavilkumā, un skripts izgāja ar **0**. Ja to būtu
palaidis kaut kas automatizēts, viens balsojums būtu pazudis klusi — un tieši
tas balsojums varēja būt jebkurš, arī 01-15 neuzticības balsojums premjerei.

Tā ir tā pati klase, kas `scripts/morning_ingest.py` (sk. `test_morning_ingest.py`):
virsma, kas ziņo par panākumu, ko nav izmērījusi.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def tool(tmp_path, monkeypatch):
    """Ielādē skriptu ar DB un tīklu novirzītiem uz testa dubultniekiem."""
    spec = importlib.util.spec_from_file_location(
        "ingest_missing_votes", REPO / "scripts" / "ingest_saeima_missing_votes.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_missing_votes"] = mod
    spec.loader.exec_module(mod)

    db_path = tmp_path / "test.db"
    from src.saeima import init_saeima_tables
    from src.db import init_db

    init_db(str(db_path))
    init_saeima_tables(str(db_path))
    monkeypatch.setattr(mod, "DB_PATH", str(db_path))
    # Embedding steka pārbaude ir īsta vārtu funkcija, bet testā tā tikai
    # ielādētu modeli — tās uzvedību sedz tests/test_preflight.py.
    monkeypatch.setattr(mod, "ensure_embeddings_live", lambda *a, **k: None)
    return mod


def _parity_file(tmp_path: Path, n: int = 2) -> Path:
    missing = [
        {
            "url": f"https://titania.saeima.lv/vote{i}",
            "vote_date": "2026-02-05",
            "vote_time": f"13:47:{i:02d}",
            "motif": f"Grozījumi kaut kādā likumā ({1000 + i}/Lp14), 1.lasījums",
            "par": 50, "pret": 30, "atturas": 10,
        }
        for i in range(n)
    ]
    p = tmp_path / "parity.json"
    p.write_text(json.dumps([{"date": "2026-02-05", "missing": missing}]),
                 encoding="utf-8")
    return p


def test_network_failure_exits_nonzero(tool, tmp_path, monkeypatch, capsys):
    """Tieši 2026-08-01 gadījums: urlopen noilgums vienam balsojumam."""
    parity = _parity_file(tmp_path)

    def _timeout(*_a, **_kw):
        raise OSError("[WinError 10060] A connection attempt failed")

    monkeypatch.setattr(tool, "_fetch", _timeout)
    monkeypatch.setattr(sys, "argv", [
        "ingest", "--parity", str(parity), "--apply",
        "--rollback-out", str(tmp_path / "rb.sql"),
    ])

    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1, "zaudēta ievade nedrīkst iziet ar 0"
    assert "failed: 2" in out
    assert "NEIELĀDĒTI" in out
    assert "atkārtojums ir drošs" in out, "ziņojumam jāpasaka, kā to atgūt"


def test_dry_run_stays_zero(tool, tmp_path, monkeypatch):
    """Sausā palaide neko neievāc, tāpēc tai nav ko zaudēt."""
    parity = _parity_file(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ingest", "--parity", str(parity)])
    assert tool.main() == 0


def test_apply_without_rollback_is_refused(tool, tmp_path, monkeypatch):
    """CLAUDE.md: katra datu mutācija nāk ar pāra rollback."""
    parity = _parity_file(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ingest", "--parity", str(parity), "--apply"])
    assert tool.main() == 2


def test_already_present_votes_are_skipped_not_refetched(tool, tmp_path, monkeypatch):
    """Atkārtojuma drošība, uz kuru atsaucas kļūdas ziņojums.

    Ja šis salūztu, ieteikums „palaid vēlreiz" ražotu dublikātus, nevis
    aizpildītu robu — tieši tas, kāpēc p3_backfill_year_urllib te neder.
    """
    parity = _parity_file(tmp_path, n=1)
    db = sqlite3.connect(tool.DB_PATH)
    db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, vote_time, url) VALUES (?,?,?,?)",
        ("jau ielādēts", "2026-02-05", "13:47:00", "https://titania.saeima.lv/cits"),
    )
    db.commit()
    db.close()

    def _must_not_fetch(*_a, **_kw):
        raise AssertionError("jau esošam balsojumam nedrīkst pieskarties tīklam")

    monkeypatch.setattr(tool, "_fetch", _must_not_fetch)
    monkeypatch.setattr(sys, "argv", [
        "ingest", "--parity", str(parity), "--apply",
        "--rollback-out", str(tmp_path / "rb.sql"),
    ])
    assert tool.main() == 0
