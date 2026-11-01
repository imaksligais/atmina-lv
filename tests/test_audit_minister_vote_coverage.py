"""`scripts/audit_minister_vote_coverage.py` — /audit-integrity 9. pārbaudes
atsevišķais saucējs (verdikts 42, 2026-09-06).

KLASE. 9. pārbaude (partija ↔ Saeimas frakcijas ieraksts) grupē pēc
`saeima_individual_votes.faction`, tāpēc politiķis BEZ neviena frakcijas
etiķetēta balsojuma tajā vispār neparādās — ne kā atradums, ne kā pārbaudīta
rinda. Ministri, kas nav deputāti, ir tieši šī klase: viņu partiju nav ar ko
salīdzināt, un pārbaude par to klusē. Tā pid=224 R. Meļņa nepareizā partija
izdzīvoja divus mēnešus un 26 publicētus pārskatus.

Labojums nav jauns atradums, bet SAUCĒJS: «N no M aktīvajiem ar `ministr`
amatā nav frakcijas etiķetēta balsojuma — partija automātiski neverificējama».
Saraksts ar pid + vārdu, lai rinda ir izlasāma, nevis skaitlis.

`checked=0` ir salauzti vārti (izejas kods 2), ne tīrs rezultāts.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from scripts.audit_minister_vote_coverage import audit_minister_coverage, run_audit


def _mkdb(politicians, votes=()):
    """politicians: (id, name, party, role, relationship_type)
    votes: (politician_id, faction)"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, "
        "party TEXT, role TEXT, relationship_type TEXT)"
    )
    db.execute(
        "CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "politician_id INTEGER, faction TEXT)"
    )
    db.executemany("INSERT INTO tracked_politicians VALUES (?,?,?,?,?)", politicians)
    db.executemany(
        "INSERT INTO saeima_individual_votes (politician_id, faction) VALUES (?,?)", votes
    )
    db.commit()
    db.close()
    return path


@pytest.fixture
def cleanup():
    paths: list[str] = []
    yield paths
    for p in paths:
        try:
            os.unlink(p)
        except (PermissionError, FileNotFoundError):
            pass


def _audit(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        return audit_minister_coverage(db)
    finally:
        db.close()


def test_minister_with_labelled_ballots_is_checked_but_not_flagged(cleanup):
    path = _mkdb(
        [(1, "Deputāts Ministrs", "JV", "Tieslietu ministrs", "tracked")],
        [(1, "JV"), (1, "JV")],
    )
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 1
    assert res["flagged"] == 0


def test_minister_without_any_ballot_is_flagged_with_pid_and_name(cleanup):
    path = _mkdb([(224, "Raivis Meļņa Vietnieks", "Bezpartejisks", "Aizsardzības ministrs", "tracked")])
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 1
    assert res["flagged"] == 1
    row = res["rows"][0]
    assert (row["id"], row["name"]) == (224, "Raivis Meļņa Vietnieks")
    assert row["ballots"] == 0
    assert row["labelled"] == 0


def test_ballots_without_a_faction_label_still_count_as_no_coverage(cleanup):
    """Šī ir īstā 9. pārbaudes aklā zona: rindas ir, bet `faction IS NULL`,
    tāpēc GROUP BY tās izmet un pārbaude klusē."""
    path = _mkdb(
        [(5, "Bez Frakcijas", "LPV", "Labklājības ministrs", "tracked")],
        [(5, None), (5, None)],
    )
    cleanup.append(path)
    res = _audit(path)
    assert res["flagged"] == 1
    assert res["rows"][0]["ballots"] == 2
    assert res["rows"][0]["labelled"] == 0


def test_inactive_politicians_are_out_of_scope(cleanup):
    """9. pārbaude pati filtrē `relationship_type != 'inactive'` — saucējam
    jāsakrīt ar to, ko tas apgalvo, ka mēra."""
    path = _mkdb([(9, "Bijušais Ministrs", "ZZS", "Ekonomikas ministrs", "inactive")])
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 0
    assert res["flagged"] == 0


def test_role_match_is_case_insensitive_and_substring(cleanup):
    path = _mkdb(
        [
            (1, "A", "JV", "MINISTRU prezidents", "tracked"),
            (2, "B", "JV", "Saeimas deputāts", "tracked"),
            (3, "C", "JV", None, "tracked"),
        ]
    )
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 1
    assert res["rows"][0]["id"] == 1


def test_empty_denominator_is_a_broken_gate(cleanup):
    path = _mkdb([(2, "Deputāts", "JV", "Saeimas deputāts", "tracked")])
    cleanup.append(path)
    assert _audit(path)["checked"] == 0
    assert run_audit(path) == 2


def test_exit_codes(cleanup):
    clean = _mkdb([(1, "A", "JV", "Tieslietu ministrs", "tracked")], [(1, "JV")])
    dirty = _mkdb([(1, "A", "JV", "Tieslietu ministrs", "tracked")])
    cleanup.extend([clean, dirty])
    assert run_audit(clean) == 0
    assert run_audit(dirty) == 1
