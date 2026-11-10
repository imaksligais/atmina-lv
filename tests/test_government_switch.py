"""scripts/government_switch.py — valdības maiņas diena no plāna līdz rollback.

Kļūmes, ko ķer: (1) piemērošana atstāj partiju statusus nesaskaņotus ar jauno
`coalition_periods` rindu (audit 24) vai rollback neatjauno iepriekšējās vērtības
(nepareizi eskeipotas pēdiņas, aizmirsta rinda); (2) novecojis plāns — DB mainījusies
pēc `--write-sql` — tik un tā tiek piemērots.
"""
import sqlite3

import yaml

import scripts.government_switch as gs
from scripts.audit_integrity import Ctx, check_24
from scripts.seed_coalition_periods import main as seed_main

NEW_ROLE = "Bijušais ekonomikas ministrs; «ZZS» valdes loceklis ('citāts' pēdiņās)"


def _db(tmp_path):
    from src.db import init_db
    from src.saeima.schema import init_saeima_tables

    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    db = sqlite3.connect(path)
    db.executemany(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?, ?, ?)",
        [("Jaunā Vienotība", "JV", "coalition"), ("Zaļo un Zemnieku savienība", "ZZS", "coalition"),
         ("Nacionālā apvienība", "NA", "coalition"), ("Progresīvie", "PRO", "opposition"),
         ("Stabilitātei!", "ST", "opposition")])
    # vecā valdība (14. Saeima, frakcijas zināmas) un jaunā (15. Saeima, faction NULL visām rindām)
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, result) VALUES "
               "(5, 'Uzticības izteikšana Ministru kabinetam', '2026-05-28', '17:20:31', 'Pieņemts')")
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, result) VALUES "
               "(9, 'Uzticības izteikšana Ministru kabinetam', '2026-11-20', '12:00:00', 'Pieņemts')")
    for fac in ("JV", "ZZS", "NA"):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                   "VALUES (5, 'd', ?, 'Par')", (fac,))
    for i, (party, vote) in enumerate([("Jaunā Vienotība", "Par")] * 2 + [("NA", "Par")] * 2
                                      + [("Progresīvie", "Pret")] * 2, start=1):
        pid = db.execute("INSERT INTO tracked_politicians (name, party, role) VALUES (?, ?, ?)",
                         (f"Deputāts {i}", party, "Saeimas deputāts")).lastrowid
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote, "
                   "politician_id) VALUES (9, ?, NULL, ?, ?)", (f"Deputāts {i}", vote, pid))
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES "
               "(100, 'Viktors Valainis', 'Zaļo un Zemnieku savienība', 'Ekonomikas ministrs')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES "
               "(101, 'Baiba Braže', NULL, 'Ārlietu ministre')")
    db.commit()
    db.close()
    return path


def _snapshot(path):
    db = sqlite3.connect(path)
    try:
        return (db.execute("SELECT id, coalition_status FROM parties ORDER BY id").fetchall(),
                db.execute("SELECT id, name, party, role, name_forms FROM tracked_politicians "
                           "ORDER BY id").fetchall(),
                db.execute("SELECT * FROM coalition_periods ORDER BY id").fetchall())
    finally:
        db.close()


def _prepare(tmp_path):
    """DB → seed --apply → sagatave → viena loma labota → --write-sql. → (path, plan, sqldir)."""
    path = _db(tmp_path)
    assert seed_main(["--db", path, "--apply"]) == 0
    plan_file = tmp_path / "plan.yaml"
    assert gs.main(["--db", path, "--template", "--out", str(plan_file)]) == 0
    plan = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
    assert plan["coalition"] == ["JV", "NA"], plan["coalition"]
    proposed = {p["short_name"]: p["new_status"] for p in plan["parties"]}
    assert proposed == {"JV": "coalition", "NA": "coalition", "PRO": "opposition",
                        "ZZS": "not_in_saeima", "ST": "not_in_saeima"}, proposed
    assert {r["id"] for r in plan["roles"]} == {100, 101}, "ministri sagatavē, deputāti nē"
    next(r for r in plan["roles"] if r["id"] == 100)["new_role"] = NEW_ROLE
    plan_file.write_text(yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8")
    sqldir = tmp_path / "sql"
    args = ["--db", path, "--plan", str(plan_file), "--out-dir", str(sqldir), "--date", "2026-11-20"]
    assert gs.main(args) == 0, "dry-run"
    assert gs.main(args + ["--write-sql"]) == 0
    assert gs.main(args + ["--write-sql"]) == 1, "esošus failus nepārraksta"
    return path, args, sqldir


def test_switch_apply_then_rollback_restores(tmp_path, monkeypatch):
    path, args, sqldir = _prepare(tmp_path)
    before = _snapshot(path)
    monkeypatch.setattr(gs, "_git_tracked", lambda p: True)
    assert gs.main(args + ["--apply"]) == 0

    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    status = dict(db.execute("SELECT short_name, coalition_status FROM parties").fetchall())
    assert status == {"JV": "coalition", "NA": "coalition", "PRO": "opposition",
                      "ZZS": "not_in_saeima", "ST": "not_in_saeima"}, status
    assert db.execute("SELECT role FROM tracked_politicians WHERE id = 100").fetchone()[0] == NEW_ROLE
    assert db.execute("SELECT role FROM tracked_politicians WHERE id = 101").fetchone()[0] == "Ārlietu ministre"
    assert check_24(Ctx(db=db, db_path=path)).flagged == 0, "audit 24 pēc piemērošanas"
    db.executescript((sqldir / "rollback_valdiba_2026-11-20.sql").read_text(encoding="utf-8"))
    db.close()
    restored = _snapshot(path) == before
    assert restored, "rollback neatjauno parties/tracked_politicians/coalition_periods"


def test_stale_plan_is_stop(tmp_path, monkeypatch):
    path, args, _ = _prepare(tmp_path)
    db = sqlite3.connect(path)
    db.execute("UPDATE tracked_politicians SET role = 'Ekonomikas ministrs (demisionējis)' WHERE id = 100")
    db.commit()
    db.close()
    before = _snapshot(path)
    monkeypatch.setattr(gs, "_git_tracked", lambda p: True)
    assert gs.main(args + ["--apply"]) == 1
    unchanged = _snapshot(path) == before
    assert unchanged, "novecojis plāns neko neieraksta"
