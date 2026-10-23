"""scripts/seed_coalition_periods.py — valdība no uzticības balsojuma.

Kļūme, ko ķer: nepareizs vairākuma noteikums (frakcija, kuras daļa balsoja Par,
vai bezfrakciju deputāti ielikti koalīcijā) un neidempotents `--apply`
(otrais palaidiens dublē vai pārraksta periodu).
"""
import sqlite3

from scripts.seed_coalition_periods import main


def _db(tmp_path):
    from src.db import init_db
    from src.saeima.schema import init_saeima_tables

    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    db = sqlite3.connect(path)
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, result) VALUES "
               "(7, 'Uzticības izteikšana Ministru kabinetam (Siliņa)', '2023-09-15', '17:10:11', 'Pieņemts')")
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, result) VALUES "
               "(8, 'Uzticības izteikšana Ministru kabinetam (X)', '2024-01-01', '10:00:00', 'Noraidīts')")
    ballots = ([("JV", "Par")] * 3 + [("PRO", "Par")] * 2 + [("PRO", "Pret")]
               + [("AS", "Par")] + [("AS", "Pret")] * 2 + [(None, "Par")] * 2 + [("", "Par")])
    for fac, vote in ballots:
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                   "VALUES (7, 'd', ?, ?)", (fac, vote))
    db.commit()
    db.close()
    return path


def _rows(path):
    db = sqlite3.connect(path)
    try:
        return db.execute("SELECT valid_from_date, valid_from_time, factions, source_vote_id "
                          "FROM coalition_periods").fetchall()
    finally:
        db.close()


def test_apply_derives_majority_par_factions_once(tmp_path):
    path = _db(tmp_path)
    assert main(["--db", path]) == 0
    assert _rows(path) == [], "dry-run neraksta"
    assert main(["--db", path, "--apply"]) == 0
    expected = [("2023-09-15", "17:10:11", "JV,PRO", 7)]   # AS 1/3 nav; bez frakcijas nav
    assert _rows(path) == expected
    assert main(["--db", path, "--apply"]) == 0
    assert _rows(path) == expected, "otrais --apply nedublē"
