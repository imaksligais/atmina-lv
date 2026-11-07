"""scripts/append_titania_decision_stages.py — viens gals-galā tests.

Kļūme, ko tas ķer: Saeimas lēmums bez balsojuma (titania «Atsaukts»,
«Pieņemts») nekad nekļūst par posmu, tāpēc dokuments mūžīgi «procesā».
Skriptam (1) dry run nedrīkst mainīt DB, bet jāuzraksta atgriešanas SQL;
(2) `--apply` jāieraksta `stage_kind='decision'` posms caur `append_bill_stage()`
un statusam jāseko titanijai; balsojuma dienā lēmums jāatsaka (tas ir
balsojums); (3) atgriešanas SQL jāatjauno PRECĪZI iepriekšējais stāvoklis.
"""

import csv
import json
import sqlite3

from src.db import init_db
from src.saeima import init_saeima_bills, init_saeima_tables, upsert_bill

import scripts.append_titania_decision_stages as dec

OLD_TS = "2025-01-01 00:00:00"


def _bills(path):
    db = sqlite3.connect(path)
    rows = db.execute("SELECT document_nr, current_stage, current_status, last_updated_at "
                      "FROM saeima_bills ORDER BY document_nr").fetchall()
    db.close()
    return rows


def _stages(path):
    db = sqlite3.connect(path)
    n = db.execute("SELECT COUNT(*) FROM saeima_bill_stages WHERE stage_kind='decision'").fetchone()[0]
    db.close()
    return n


def test_dry_run_apply_rollback_roundtrip(tmp_path):
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    for nr, bt in (("994/Lm14", "Lm14"), ("1056/Lm14", "Lm14"), ("990/Lm14", "Lm14"),
                   ("1118/Lm14", "Lm14"), ("1525/Lp14", "Lp14")):
        upsert_bill(path, nr, "Tests", bt)
    db = sqlite3.connect(path)
    # 990: titanijā «Pieņemts» tajā pašā dienā, kad ir balsojums → atteikt
    db.execute("INSERT INTO saeima_votes (motif, vote_date, result, document_nr) "
               "VALUES ('Par … (990/Lm14)', '2026-06-11', 'Pieņemts', '990/Lm14')")
    # 1118: balsojums piesaistīts saistītajam Lp — numurs tikai motīvā → atteikt
    db.execute("INSERT INTO saeima_votes (motif, vote_date, result, document_nr) "
               "VALUES ('Par termiņa pagarināšanu (Nr.947/Lp14) (1118/Lm14)', '2026-09-17', "
               "'Pieņemts', '947/Lp14')")
    db.execute("UPDATE saeima_bills SET last_updated_at=?", (OLD_TS,))
    db.commit()
    db.close()
    titania = tmp_path / "t.csv"
    with titania.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["document_nr", "bill_type", "titania_status", "stages", "error"])
        w.writeheader()
        for nr, bt, name, res, d in (
                ("994/Lm14", "Lm14", "Saeimas sēde", "Atsaukts", "2026-06-03"),
                ("1056/Lm14", "Lm14", "Saeimas sēde", "Pieņemts", "2026-06-11"),
                ("990/Lm14", "Lm14", "Saeimas sēde", "Pieņemts", "2026-06-11"),
                ("1118/Lm14", "Lm14", "Saeimas sēde", "Pieņemts", "2026-09-17"),
                ("1525/Lp14", "Lp14", "Nodošana komis.", "Atsaukts", "2026-09-10")):
            w.writerow({"document_nr": nr, "bill_type": bt, "titania_status": "x", "error": "",
                        "stages": json.dumps([{"name": "Iesniegts", "date": "2026-05-01", "result": None},
                                              {"name": name, "date": d, "result": res}])})
    before = _bills(path)
    rb = tmp_path / "rollback.sql"
    args = ["--db", path, "--csv", str(titania), "--rollback", str(rb),
            "--document-nr", "994/Lm14", "--document-nr", "1056/Lm14",
            "--document-nr", "990/Lm14", "--document-nr", "1118/Lm14",
            "--document-nr", "1525/Lp14"]

    assert dec.main(args) == 0
    assert _bills(path) == before and _stages(path) == 0
    assert "plan-hash:" in rb.read_text(encoding="utf-8")

    assert dec.main(args + ["--apply"]) == 0
    status = {r[0]: r[2] for r in _bills(path)}
    assert status == {"994/Lm14": "atsaukts", "1056/Lm14": "pieņemts",
                      "990/Lm14": "procesā", "1118/Lm14": "procesā",
                      "1525/Lp14": "atsaukts"}
    assert _stages(path) == 3
    # Vēsturisks lēmums nav jauna aktivitāte — saraksta kārtība nemainās.
    assert {r[3] for r in _bills(path)} == {OLD_TS}

    db = sqlite3.connect(path)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.close()
    assert _stages(path) == 0
    assert _bills(path) == before
