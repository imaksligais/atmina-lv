"""Tas pats balsojums ar citu saiti nedrīkst radīt otru rindu.

Kļūme, ko ķer: titania to pašu balsojumu rāda ar `parentID=` saiti un pēc tam ar
pastāvīgo; sēdes atkārtota ielāde pēc saites nomaiņas uztaisīja otru
`saeima_votes` rindu un divkāršus deputātu claim. Saite vien nav identitāte, identitāte
ir (datums, laiks ar sekundēm).

`test_saeima.py` sedz tikai dedup pēc tās pašas saites.
"""

from __future__ import annotations

import json

import pytest

from src.db import get_db, init_db
from src.saeima import IndividualVote, VoteResult, generate_claims_from_votes, init_saeima_tables, store_vote

PARENT = "https://titania.saeima.lv/LIVS15/SaeimaLIVS2_DK.nsf/Voting?ReadForm&parentID=00000001-0000-0000-0000-000000000000"
PERMANENT = "https://titania.saeima.lv/LIVS15/SaeimaLIVS2_DK.nsf/0/" + "A" * 32 + "?OpenDocument"


def _vote(url: str, *, time: str = "10:30:15", par: int = 50) -> VoteResult:
    return VoteResult(
        motif="Grozījumi Testa likumā (9999/Lp15), 1.lasījums",
        date="2026-11-12", time=time,
        total_par=par, total_pret=30, total_atturas=5, total_nebalso=15,
        result="Pieņemts", url=url,
        individual_votes=[IndividualVote(deputy_name="Test Deputāts", faction="JV", vote="Par", politician_id=1)],
    )


def _count(path, sql, *args):
    db = get_db(path)
    try:
        return db.execute(sql, args).fetchone()[0]
    finally:
        db.close()


@pytest.fixture
def saeima_db(tmp_path, monkeypatch):
    path = str(tmp_path / "votes.db")
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Deputāts', 'JV')")
    db.commit()
    db.close()
    # log_action un claim rakstītāji iekšēji sauc get_db() ar noklusējuma ceļu.
    import src.db as db_mod
    import src.saeima as saeima_mod
    monkeypatch.setattr(db_mod, "DB_PATH", path)
    monkeypatch.setattr(saeima_mod, "DB_PATH", path)
    return path


@pytest.fixture
def _no_topic(monkeypatch):
    monkeypatch.setattr("src.saeima.votes.topic_for_new_vote", lambda *a, **k: None)
    monkeypatch.setattr("src.saeima.votes.ingest_input_text", lambda *a, **k: "")


def test_reingest_under_new_url_keeps_one_vote_and_its_claims(saeima_db, _no_topic):
    first = _vote(PARENT)
    vote_id = store_vote(first, db_path=saeima_db)
    assert len(generate_claims_from_votes(first, vote_id, db_path=saeima_db)) == 1

    again = _vote(PERMANENT)
    assert store_vote(again, db_path=saeima_db) == vote_id
    generate_claims_from_votes(again, vote_id, db_path=saeima_db)

    assert _count(saeima_db, "SELECT COUNT(*) FROM saeima_votes") == 1
    assert _count(saeima_db, "SELECT COUNT(*) FROM saeima_individual_votes") == 1
    assert _count(saeima_db, "SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote'") == 1
    # Saiti maina tikai scripts/fix_parentid_vote_urls.py (kopā ar claims.source_url).
    assert _count(saeima_db, "SELECT COUNT(*) FROM saeima_votes WHERE url=?", PARENT) == 1
    assert again.url == PARENT

    db = get_db(saeima_db)
    row = db.execute("SELECT details FROM logs WHERE action='saeima_vote_same_moment'").fetchone()
    db.close()
    assert row is not None, "nomestā saite jāredz žurnālā"
    details = json.loads(row["details"])
    assert (details["vote_db_id"], details["kept_url"], details["dropped_url"]) == (vote_id, PARENT, PERMANENT)


def test_same_moment_with_different_totals_stops(saeima_db, _no_topic):
    store_vote(_vote(PARENT), db_path=saeima_db)
    with pytest.raises(ValueError, match="kopsumm"):
        store_vote(_vote(PERMANENT, par=51), db_path=saeima_db)
    assert _count(saeima_db, "SELECT COUNT(*) FROM saeima_votes") == 1


def test_minute_precision_is_not_identity(saeima_db, _no_topic):
    """Minūtes precizitātē divi īsti balsojumi var sakrist, tāpēc tie paliek atsevišķi."""
    store_vote(_vote(PARENT, time="10:30"), db_path=saeima_db)
    store_vote(_vote(PERMANENT, time="10:30"), db_path=saeima_db)
    assert _count(saeima_db, "SELECT COUNT(*) FROM saeima_votes") == 2
