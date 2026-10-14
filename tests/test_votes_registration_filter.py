"""Deputātu klātbūtnes reģistrācija ir izslēgta no balsojumu renderēšanas.

Operatora lēmums 2026-07-17: reģistrācijas notikumi (316 rindas DB, visi
totāli 0, maldinošs result='Noraidīts') nav balsojumi — tie aizsprosto
balsojumu saraksta augšu, piepūš matricas JSON ar '.'/'X' kolonnām un
kropļo metriku saucējus (total, accepted_pct, attendance_pct). Filtrs ir
RENDER līmenī (``_fetch_votes``) — DB rindas paliek neaiztiktas (T8
pilnīguma auditi turpina redzēt visu sesiju pēc (vote_date, vote_time)).

Filtram jābūt PREFIKSA formā ('Deputātu klātbūtnes reģistrācija%'), ne
'%reģistrācij%' — pēdējais noķertu arī īstus balsojumus, piem.,
"Grozījumi Civilstāvokļa aktu reģistrācijas likumā".
"""

import sqlite3

import pytest

from src.render.votes import _fetch_votes


@pytest.fixture()
def db_with_registration(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    rows = [
        # (motif, date, time, par, pret, att, nebalso, result)
        ("Deputātu klātbūtnes reģistrācija", "2026-06-18", "10:31:02",
         0, 0, 0, 0, "Noraidīts"),
        ("Grozījumi Civilstāvokļa aktu reģistrācijas likumā (557/Lp14), 3.lasījums",
         "2026-06-18", "11:00:00", 60, 10, 5, 15, "Pieņemts"),
        ("Grozījumi Krimināllikumā (1374/Lp14), 2.lasījums", "2026-06-18",
         "17:19:55", 44, 0, 0, 16, "Pieņemts"),
    ]
    for i, (motif, d, t, p, n, a, x, res) in enumerate(rows):
        db.execute(
            "INSERT INTO saeima_votes (motif, vote_date, vote_time, total_par,"
            " total_pret, total_atturas, total_nebalso, result, url)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (motif, d, t, p, n, a, x, res, f"https://example.test/{i}"),
        )
    db.commit()
    yield db
    db.close()


def test_registration_rows_excluded(db_with_registration):
    votes = _fetch_votes(db_with_registration)
    motifs = [v["motif"] for v in votes]
    assert "Deputātu klātbūtnes reģistrācija" not in motifs


def test_real_registration_law_votes_survive(db_with_registration):
    """Prefiksa filtrs nedrīkst noķert īstus balsojumus ar 'reģistrācija' nosaukumā."""
    votes = _fetch_votes(db_with_registration)
    motifs = [v["motif"] for v in votes]
    assert any("Civilstāvokļa aktu reģistrācijas" in m for m in motifs)
    assert any("Krimināllikumā" in m for m in motifs)
    assert len(votes) == 2
