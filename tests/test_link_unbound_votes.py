"""scripts/link_unbound_votes_to_bills.py — viens gals-galā tests.

Kļūme, ko tas ķer: galīgā lasījuma balsojums ar `bill_id IS NULL` nekad
nekļūst par posmu, tāpēc likums rādās «procesā». Skriptam (1) dry run nedrīkst
mainīt DB, bet jāuzraksta atgriešanas SQL; (2) `--apply` jāpiesaista balsojums
caur `append_bill_stage()` un statusam jākļūst `pieņemts`; (3) atgriešanas SQL
jāatjauno PRECĪZI iepriekšējais stāvoklis, ieskaitot `last_updated_at`;
(4) `--apply` NEDRĪKST mainīt `last_updated_at` — pēc tā kārto `likumprojekti.html`,
un simtiem vecu likumprojektu citādi uzlēktu saraksta augšā (2026-10-20).
"""

import sqlite3

from src.db import init_db
from src.saeima import append_bill_stage, init_saeima_bills, init_saeima_tables, upsert_bill

import scripts.link_unbound_votes_to_bills as link

NR = "100/Lp14"
OLD_TS = "2025-01-01 00:00:00"


def _bill(path):
    db = sqlite3.connect(path)
    row = db.execute(
        "SELECT current_stage, current_status, last_updated_at FROM saeima_bills "
        "WHERE document_nr=?", (NR,)).fetchone()
    db.close()
    return row


def _q(path, sql, *a):
    db = sqlite3.connect(path)
    v = db.execute(sql, a).fetchone()[0]
    db.close()
    return v


def test_dry_run_apply_rollback_roundtrip(tmp_path):
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    bid = upsert_bill(path, NR, "Grozījumi Testa likumā", "Lp14")

    db = sqlite3.connect(path)
    v1 = db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, result, url, document_nr) "
        "VALUES (?, '2025-09-01', 'Pieņemts', 'u1', ?)",
        (f"Grozījumi Testa likumā ({NR}), 1.lasījums", NR)).lastrowid
    db.commit()
    db.close()
    append_bill_stage(path, bid, "1.lasījums", "Pieņemts", "2025-09-01", vote_id=v1)

    db = sqlite3.connect(path)
    v3 = db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, result, url, document_nr) "
        "VALUES (?, '2025-10-01', 'Pieņemts', 'u3', ?)",
        (f"Grozījumi Testa likumā ({NR}), 3.lasījums", NR)).lastrowid
    # Fiksēts vecs laiks — citādi atgriešana bez last_updated_at izskatītos
    # pareiza tikai tāpēc, ka abi ieraksti notika vienā sekundē.
    db.execute("UPDATE saeima_bills SET last_updated_at=? WHERE id=?", (OLD_TS, bid))
    db.commit()
    db.close()

    before = _bill(path)
    assert before == ("1.lasījums", "procesā", OLD_TS)
    rb = tmp_path / "rollback.sql"

    # 1) dry run: DB nemainās, atgriešanas fails uzrakstīts
    assert link.main(["--db", path, "--document-nr", NR, "--rollback", str(rb)]) == 0
    assert _bill(path) == before
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", v3) is None
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages") == 1
    assert rb.exists() and "plan-hash:" in rb.read_text(encoding="utf-8")

    # 2) apply: balsojums piesaistīts, likums pieņemts
    assert link.main(["--db", path, "--document-nr", NR, "--rollback", str(rb), "--apply"]) == 0
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", v3) == bid
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages WHERE vote_id=?", v3) == 1
    after = _bill(path)
    assert after == ("3.lasījums", "pieņemts", OLD_TS)

    # 3) atgriešana: posms prom, bill_id NULL, likumprojekts kā iepriekš
    db = sqlite3.connect(path)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.close()
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages WHERE vote_id=?", v3) == 0
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages") == 1
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", v3) is None
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", v1) == bid
    assert _bill(path) == before


def test_shared_vote_mode_adds_decision_stage_keeps_vote_on_lp(tmp_path):
    """--shared (2026-10-20): balsojums par lēmumu, kas jau piesaistīts saistītajam
    Lp (1056/Lm14 ↔ 1352/Lp14). Lm kļūst pieņemts, balsojums paliek pie Lp,
    atgriešana atjauno Lm un neaiztiek Lp posmu."""
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    lp = upsert_bill(path, "1352/Lp14", "Zemes likums", "Lp14")
    lm = upsert_bill(path, "1056/Lm14", "Par termiņa pagarināšanu", "Lm14")
    db = sqlite3.connect(path)
    vid = db.execute(
        "INSERT INTO saeima_votes (motif, vote_date, result, url, document_nr) VALUES "
        "('Par priekšlikumu iesniegšanas termiņa pagarināšanu (Nr.1352/Lp14) (1056/Lm14)', "
        "'2026-06-11', 'Pieņemts', 'u', '1352/Lp14')").lastrowid
    db.commit()
    db.close()
    append_bill_stage(path, lp, "procesuāls", "Pieņemts", "2026-06-11", vote_id=vid)
    db = sqlite3.connect(path)
    db.execute("UPDATE saeima_bills SET last_updated_at=?", (OLD_TS,))
    db.commit()
    db.close()
    before = _q(path, "SELECT current_status FROM saeima_bills WHERE id=?", lm)
    rb = tmp_path / "rb.sql"
    args = ["--db", path, "--document-nr", "1056/Lm14", "--rollback", str(rb), "--shared"]

    assert link.main(args) == 0
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages") == 1
    assert link.main(args + ["--apply"]) == 0
    assert _q(path, "SELECT current_status FROM saeima_bills WHERE id=?", lm) == "pieņemts"
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", vid) == lp

    db = sqlite3.connect(path)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.close()
    assert _q(path, "SELECT current_status FROM saeima_bills WHERE id=?", lm) == before
    assert _q(path, "SELECT last_updated_at FROM saeima_bills WHERE id=?", lm) == OLD_TS
    assert _q(path, "SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=?", lp) == 1
    assert _q(path, "SELECT bill_id FROM saeima_votes WHERE id=?", vid) == lp
