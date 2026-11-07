"""`scripts/audit_integrity.py` 20., 22., 23. pārbaude — apspiestās junction saites (D2).

KĀPĒC atsevišķs fails: šīm pārbaudēm vajag ĪSTOS trigerus
(`src.db_migrations._apply_dp_suppressions`) un `document_politicians.created_at`,
kuru `tests/test_audit_integrity.py` minimālajā shēmā nav. Ka neviens neapiet
`link_document_politicians()`, pierāda tikai 20. pārbaude — tāpēc tai jāspēj
nokrist katrā zarā (trīskāršs, `scope='pair'`, trūkstošs trigeris, tukšs saucējs).
21. pārbaudei testa nav: tā ir viens SELECT ar UTC robežu, bez zariem.

Hermētiski: DB tiek būvēta tmp_path, ražošanas DB netiek aiztikta.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import scripts.audit_integrity as ai
from src.db_migrations import _apply_dp_suppressions

_BASE = """
CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT);
CREATE TABLE document_politicians (document_id INTEGER, politician_id INTEGER, role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (document_id, politician_id, role));
INSERT INTO documents (id, scraped_at) VALUES (1, '2026-01-01 00:00:00');
"""


def _mkdb(tmp_path: Path, sql: str = "", params: list[tuple[str, tuple]] = ()) -> str:
    path = tmp_path / "dp.db"
    db = sqlite3.connect(path)
    db.executescript(_BASE)
    _apply_dp_suppressions(db)
    db.executescript(sql)
    for stmt, args in params:
        db.execute(stmt, args)
    db.commit()
    db.close()
    return str(path)


def _run(path: str, num: str, **kw) -> ai.CheckResult:
    db = ai.connect_ro(path)
    try:
        return ai.CHECKS[num](ai.Ctx(db=db, db_path=path, **kw))
    finally:
        db.close()


_SUPPRESS = ("INSERT INTO document_politician_suppressions (document_id, politician_id, role, scope) "
             "VALUES ")


# --- 20. Apspiesta saite atkal junction tabulā (vārti) ----------------------

def test_check20_link_removed_and_kept_out_is_clean(tmp_path):
    """Normālais ceļš: labojums dzēš saiti, trigeris to apspiež, saite nav atpakaļ.
    Pid 6 — vecā stila rollback ievieto saiti atpakaļ tieši: apspiešana atcelta,
    rinda junction tabulā ir likumīga, ne atradums."""
    path = _mkdb(tmp_path, "INSERT INTO document_politicians (document_id, politician_id, role) "
                           "VALUES (1, 5, 'subject'), (1, 6, 'subject');"
                           "DELETE FROM document_politicians;"
                           "INSERT INTO document_politicians (document_id, politician_id, role) "
                           "VALUES (1, 6, 'subject');")
    r = _run(path, "20")
    assert (r.checked, r.flagged, r.broken, r.status()) == (1, 0, "", 0)


def test_check20_suppressed_triple_back_in_junction_is_flagged(tmp_path):
    """Apiešanas forma: rinda junction tabulā UN neatcelta apspiešana tam pašam
    trīskāršam (tieša INSERT to būtu atcēlusi, palīgs to nebūtu ievietojis)."""
    path = _mkdb(tmp_path, "INSERT INTO document_politicians (document_id, politician_id, role) "
                           "VALUES (1, 5, 'subject');" + _SUPPRESS + "(1, 5, 'subject', 'role');")
    r = _run(path, "20")
    assert (r.checked, r.flagged, r.status()) == (1, 1, 1)
    assert r.rows[0]["id"] == "d1/p5/subject"


def test_check20_pair_suppression_with_another_role_present_is_flagged(tmp_path):
    """`scope='pair'` aizliedz JEBKURU lomu: politiķis atgriezies kā `mentioned`,
    lai gan noņemts tika viss pāris — trīskāršu salīdzinājums to neredzētu."""
    path = _mkdb(tmp_path, "INSERT INTO document_politicians (document_id, politician_id, role) "
                           "VALUES (1, 5, 'mentioned');" + _SUPPRESS + "(1, 5, 'subject', 'pair');")
    assert _run(path, "20").flagged == 1


def test_check20_no_unlifted_suppression_is_broken_denominator(tmp_path):
    """0 neatceltu apspiešanu = nav ko pārbaudīt, ne «tīrs» → izejas kods 2."""
    path = _mkdb(tmp_path)
    r = _run(path, "20")
    assert (r.checked, r.broken) == (0, "")
    assert ai.main(["--db", path, "--only", "20"]) == 2


def test_check20_missing_trigger_is_broken(tmp_path):
    """Bez `dp_lift_ai` tieša INSERT apspiešanu vairs neatceļ, un «0» vairs
    nepierāda, ka palīgs nav apiets."""
    path = _mkdb(tmp_path, "INSERT INTO document_politicians (document_id, politician_id, role) "
                           "VALUES (1, 5, 'subject');"
                           "DELETE FROM document_politicians WHERE politician_id = 5;"
                           "DROP TRIGGER dp_lift_ai;")
    r = _run(path, "20")
    assert "dp_lift_ai" in r.broken and r.status() == 2


def test_check20_mode_left_off_is_broken(tmp_path):
    """Rollback ieslēdza 'off' un neatgrieza 'record': jauni dzēsumi vairs netiek
    pierakstīti, tātad «0» neko nepierāda."""
    path = _mkdb(tmp_path, _SUPPRESS + "(1, 5, 'subject', 'pair');"
                           "UPDATE dp_suppression_mode SET mode = 'off';")
    r = _run(path, "20")
    assert "off" in r.broken and r.status() == 2


# --- 22. Doks pārielādēts pēc apspiešanas (info) -----------------------------

def test_check22_compares_lv_scrape_with_suppression_in_local_time(tmp_path):
    """T17: `scraped_at` LV, apspiešanas `created_at` UTC. Pārielāde 1 h PIRMS
    apspiešanas (LV laikā) ir virkņu salīdzinājumā «vēlāka» par UTC vērtību —
    bez `'localtime'` tā tiktu uzrādīta. Nobīdi rēķina pati SQLite (tās
    `localtime` ir mašīnas zona), tāpēc tests der jebkurā zonā ar ≥2 h nobīdi."""
    created_utc = "2026-01-15 10:00:00"
    probe = sqlite3.connect(":memory:")
    local = probe.execute("SELECT datetime(?, 'localtime')", (created_utc,)).fetchone()[0]
    probe.close()
    local_dt = datetime.strptime(local, "%Y-%m-%d %H:%M:%S")
    if local_dt - datetime.strptime(created_utc, "%Y-%m-%d %H:%M:%S") < timedelta(hours=2):
        pytest.skip(f"mašīnas zonas nobīde < 2 h ({local}) — gadījumu nevar atšķirt")
    before, after = (str(local_dt + timedelta(hours=h)) for h in (-1, 1))
    assert before > created_utc   # virkņu salīdzinājums bez konversijas kļūdītos

    def run(scraped: str) -> ai.CheckResult:
        (tmp_path / "dp.db").unlink(missing_ok=True)
        return _run(_mkdb(tmp_path, params=[
            ("UPDATE documents SET scraped_at = ? WHERE id = 1", (scraped,)),
            ("INSERT INTO document_politician_suppressions (document_id, politician_id, role, "
             "scope, created_at) VALUES (1, 5, 'subject', 'pair', ?)", (created_utc,)),
        ]), "22")

    r = run(before)
    assert (r.checked, r.flagged) == (1, 0)
    assert run(after).flagged == 1


# --- 23. Vēsturiski atgriezumi (info) ----------------------------------------

_COMMIT = "2026-09-01 00:00:00"


def _run23(tmp_path: Path, rollback_sql: str, junction_sql: str) -> ai.CheckResult:
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "rollback_x_2026-09-01.sql").write_text(rollback_sql, encoding="utf-8")
    path = _mkdb(tmp_path, junction_sql)
    return _run(path, "23", data_dir=data, commit_time=lambda p: _COMMIT)


def test_check23_row_removed_by_fix_and_present_again_is_candidate(tmp_path):
    """Rollback atjauno (1,5,subject) un (1,7,subject) = forward labojums tās
    noņēma. (1,5) ir DB ar `created_at` pēc rollback commit → atgriezta;
    (1,7) joprojām nav; (1,6) rollback neskar."""
    r = _run23(
        tmp_path,
        "BEGIN;\n-- komentārs\nINSERT INTO document_politicians (document_id, politician_id, role) "
        "VALUES (1, 5, 'subject');\nINSERT INTO document_politicians (document_id, politician_id, role) "
        "VALUES (1, 7, 'subject');\nCOMMIT;\n",
        "INSERT INTO document_politicians VALUES (1, 5, 'subject', '2026-10-01 00:00:00');"
        "INSERT INTO document_politicians VALUES (1, 6, 'mentioned', '2026-10-01 00:00:00');",
    )
    assert (r.checked, r.flagged) == (2, 1)
    assert r.rows[0]["id"] == "d1/p5/subject" and r.rows[0]["fails"] == "rollback_x_2026-09-01.sql"
    assert (r.extra["joprojām noņemtas"], r.extra["SQL kļūdas"]) == (1, 0)


def test_check23_broken_rollback_statement_is_counted_not_swallowed(tmp_path):
    """`_d2_scope.py` pirmā versija norija katru SQL kļūdu — priekšraksts, kas
    neizpildās, klusi samazināja noņemto kopu. Tagad skaits + pirmais ziņojums."""
    r = _run23(
        tmp_path,
        "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 5, 'subject');\n"
        "INSERT INTO document_politicians (document_id, nav_tadas_kolonnas) VALUES (1, 9);\n",
        "",
    )
    assert r.extra["SQL kļūdas"] == 1
    assert "nav_tadas_kolonnas" in r.extra["faili ar kļūdām"]["rollback_x_2026-09-01.sql"]
