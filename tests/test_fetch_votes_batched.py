"""_fetch_votes: batched faction-breakdown, no per-vote tracked_votes.

Option-2 refactor (2026-07-17): the SSR vote cards were deleted, so ``_fetch_votes``
no longer materializes a per-vote ``tracked_votes`` list, and the per-vote
faction-breakdown GROUP BY collapsed into ONE batched query. This locks the new
contract: no ``tracked_votes`` key, ``faction_breakdown`` rows carry correct
par/pret/atturas/nebalso counts (a 'Reģistrējies' ballot counts into ``nebalso``,
i.e. not Par/Pret/Atturas), coalition-first ordering, and votes date DESC.
"""

import pytest

from src.render.votes import _fetch_votes


@pytest.fixture()
def db_two_votes(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)

    # Coalition status so the enrich ordering is exercised: CO coalition, OP opposition.
    db.execute("INSERT INTO parties (name, short_name, coalition_status) "
               "VALUES ('Koalīcija','CO','coalition')")
    db.execute("INSERT INTO parties (name, short_name, coalition_status) "
               "VALUES ('Opozīcija','OP','opposition')")

    # Two tracked politicians so individual votes link.
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'A Alfa','CO','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (2,'B Beta','OP','tracked')")

    # Two votes; newer one second so we can assert DESC ordering.
    db.execute("INSERT INTO saeima_votes (id,motif,vote_date,vote_time,total_par,"
               "total_pret,total_atturas,total_nebalso,result,url) "
               "VALUES (1,'Vecais','2026-06-01','10:00:00',3,1,0,1,'Pieņemts','u1')")
    db.execute("INSERT INTO saeima_votes (id,motif,vote_date,vote_time,total_par,"
               "total_pret,total_atturas,total_nebalso,result,url) "
               "VALUES (2,'Jaunais','2026-06-10','11:00:00',2,0,0,0,'Pieņemts','u2')")

    # Individual votes for vote 1 across two factions. Faction CO: 2 Par, 1
    # Reģistrējies (→ nebalso). Faction OP: 1 Pret.
    rows = [
        (1, "A Alfa", "CO", "Par", 1),
        (1, "X CoTwo", "CO", "Par", None),
        (1, "Y CoThree", "CO", "Reģistrējies", None),  # not Par/Pret/Atturas → nebalso
        (1, "B Beta", "OP", "Pret", 2),
        (2, "A Alfa", "CO", "Par", 1),
        (2, "B Beta", "OP", "Atturas", 2),
    ]
    for vid, name, fac, vote, pid in rows:
        db.execute(
            "INSERT INTO saeima_individual_votes (vote_id,deputy_name,faction,vote,politician_id) "
            "VALUES (?,?,?,?,?)",
            (vid, name, fac, vote, pid),
        )
    db.commit()
    yield db
    db.close()


def test_no_tracked_votes_key(db_two_votes):
    votes = _fetch_votes(db_two_votes)
    for v in votes:
        assert "tracked_votes" not in v


def test_votes_ordered_date_desc(db_two_votes):
    votes = _fetch_votes(db_two_votes)
    assert [v["id"] for v in votes] == [2, 1]


def test_faction_breakdown_counts_and_ordering(db_two_votes):
    votes = _fetch_votes(db_two_votes)
    by_id = {v["id"]: v for v in votes}

    fb1 = by_id[1]["faction_breakdown"]
    # Coalition faction first (status order), then opposition.
    assert [f["faction"] for f in fb1] == ["CO", "OP"]

    co = next(f for f in fb1 if f["faction"] == "CO")
    assert (co["par"], co["pret"], co["atturas"], co["nebalso"]) == (2, 0, 0, 1)
    # 'Reģistrējies' counted into nebalso, so total includes it.
    assert co["total"] == 3
    assert co["coalition_status"] == "coalition"
    assert co["majority_vote"] == "Par"

    op = next(f for f in fb1 if f["faction"] == "OP")
    assert (op["par"], op["pret"], op["atturas"], op["nebalso"]) == (0, 1, 0, 0)
    assert op["coalition_status"] == "opposition"


def test_second_vote_breakdown(db_two_votes):
    votes = _fetch_votes(db_two_votes)
    fb2 = {v["id"]: v for v in votes}[2]["faction_breakdown"]
    co = next(f for f in fb2 if f["faction"] == "CO")
    op = next(f for f in fb2 if f["faction"] == "OP")
    assert (co["par"], co["pret"], co["atturas"], co["nebalso"]) == (1, 0, 0, 0)
    assert (op["par"], op["pret"], op["atturas"], op["nebalso"]) == (0, 0, 1, 0)
