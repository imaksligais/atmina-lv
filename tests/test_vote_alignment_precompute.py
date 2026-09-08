"""vote_alignment_data — kopīgais balsojumu sakritības precompute.

Aizstāj divus SQL self-join (politicians._vote_alignment_for per-pid ×195 un
links._fetch_graph_data globālo) ar vienu numpy caurskrējienu. Šie testi tur
PARITĀTI: numpy rezultātam baits pret baitu jāsakrīt ar veco SQL formu, kas
šeit dzīvo tālāk kā orākuls (dzīvajā DB paritāte pārbaudīta 2026-08-20 —
0 nesakritību 9034 pāros).
"""
import random
import sqlite3

import pytest

from src.render._common import vote_alignment_data

_BALLOTS = ["Par", "Pret", "Atturas", "Nebalsoja", "Nereģistrējies"]

_ORACLE_SQL = """
    SELECT v1.politician_id AS pid1, v2.politician_id AS pid2,
           SUM(CASE WHEN v1.vote = v2.vote THEN 1 ELSE 0 END) AS agree,
           COUNT(*) AS total
    FROM saeima_individual_votes v1
    JOIN saeima_individual_votes v2
      ON v1.vote_id = v2.vote_id AND v1.politician_id < v2.politician_id
    WHERE v1.vote IN ('Par', 'Pret', 'Atturas')
      AND v2.vote IN ('Par', 'Pret', 'Atturas')
    GROUP BY v1.politician_id, v2.politician_id
    HAVING total >= 10
"""


@pytest.fixture
def db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE saeima_individual_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_id INTEGER, politician_id INTEGER, vote TEXT);
    """)
    yield con
    con.close()


def _seed_random(db, n_pols=25, n_votes=120, seed=42):
    rng = random.Random(seed)
    for pid in range(1, n_pols + 1):
        db.execute(
            "INSERT INTO tracked_politicians VALUES (?, ?, ?, ?)",
            (pid, f"Deputāts {pid}", f"P{pid % 4}",
             "inactive" if pid % 7 == 0 else "tracked"),
        )
    for vid in range(1, n_votes + 1):
        for pid in range(1, n_pols + 1):
            if rng.random() < 0.3:  # daļa sēžu izlaista — nevienādi total
                continue
            db.execute(
                "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote)"
                " VALUES (?, ?, ?)",
                (vid, pid, rng.choice(_BALLOTS)),
            )
    db.commit()


def test_parity_with_sql_oracle(db):
    """Katram kvalificētajam pārim (agree, total) sakrīt ar veco SQL formu."""
    _seed_random(db)
    oracle = {
        (r["pid1"], r["pid2"]): (r["agree"], r["total"])
        for r in db.execute(_ORACLE_SQL)
    }
    got = vote_alignment_data(db)["pairs"]
    assert got == oracle
    assert len(got) > 0  # tukšs orākuls = tests neko nepārbauda (saucēja princips)


def test_non_vote_states_excluded(db):
    """Klātbūtnes stāvokļi nepalielina ne agree, ne total (abas puses)."""
    db.execute("INSERT INTO tracked_politicians VALUES (1, 'A', 'X', 'tracked')")
    db.execute("INSERT INTO tracked_politicians VALUES (2, 'B', 'Y', 'tracked')")
    for vid in range(1, 13):
        vote = "Par" if vid <= 2 else "Nereģistrējies"
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 1, ?)", (vid, vote))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 2, ?)", (vid, vote))
    db.commit()
    assert vote_alignment_data(db)["pairs"] == {}  # 2 īstas balsis < 10 slieksnis

    for vid in range(13, 23):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 1, 'Par')", (vid,))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 2, 'Pret')", (vid,))
    db.commit()
    assert vote_alignment_data(db)["pairs"] == {(1, 2): (2, 12)}


def test_meta_covers_all_tracked_and_empty_votes(db):
    """meta nes visus politiķus arī bez balsīm; tukša balsu tabula → tukši pāri."""
    db.execute("INSERT INTO tracked_politicians VALUES (1, 'A', 'X', 'tracked')")
    db.execute("INSERT INTO tracked_politicians VALUES (2, 'B', NULL, 'inactive')")
    db.commit()
    data = vote_alignment_data(db)
    assert data["pairs"] == {}
    assert data["meta"][2]["relationship_type"] == "inactive"
    assert data["meta"][1]["party"] == "X"


def test_vote_alignment_for_uses_shared_bundle(db):
    """_vote_alignment_for ar padotu align dod to pašu, ko bez tā (pats aprēķina),
    un izslēdz inactive partnerus — vecā SQL JOIN filtra paritāte."""
    from src.render.politicians import _vote_alignment_for

    db.execute("INSERT INTO tracked_politicians VALUES (1, 'A', 'X', 'tracked')")
    db.execute("INSERT INTO tracked_politicians VALUES (2, 'B', 'Y', 'tracked')")
    db.execute("INSERT INTO tracked_politicians VALUES (3, 'C', 'Z', 'inactive')")
    for vid in range(1, 13):
        for pid, vote in ((1, "Par"), (2, "Par" if vid <= 6 else "Pret"), (3, "Par")):
            db.execute(
                "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote)"
                " VALUES (?, ?, ?)", (vid, pid, vote))
    db.commit()

    align = vote_alignment_data(db)
    with_bundle = _vote_alignment_for(db, 1, top_n=3, align=align)
    without = _vote_alignment_for(db, 1, top_n=3)
    assert with_bundle == without
    top, bottom = with_bundle
    names = [x["name"] for x in top + bottom]
    assert "C" not in names  # inactive partneris izslēgts
    assert top[0]["name"] == "B" and top[0]["agree"] == 6 and top[0]["total"] == 12
