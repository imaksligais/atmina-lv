"""End-to-end test for scripts/vote_candidates.py (balsojumu īsais saraksts medniekam).

Failures named first:
1. The bill the politician actually voted on, about the very thing the position
   speaks of, is not at the top — the hunter reads the wrong bills first.
2. A bill with only procedural ballots, or one the politician never cast a
   ballot on, is offered as a candidate (T14: procedure is not a stance).
3. On a sitting day the new thing is the vote, and an older statement about the
   same bill is never put next to it (#56: statement 16.09., vote 08.10.).
"""

import struct

import numpy as np
import pytest

import src.db
from scripts import vote_candidates as script
from src import vote_candidates as vc
from src.db import get_db, init_db, store_claim
from src.saeima.schema import init_saeima_bills, init_saeima_tables

DIM = 384


def _axis(i: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[i] = 1.0
    return v


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (1, 'Testa Deputāts'), (2, 'Cits Deputāts')")
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (10, 'teksts', 'h10')")
    votes = [  # id, motif, date, url, document_nr, summary
        (1, "Grozījumi ministriju likumā (11/Lp14), 2.lasījums", "2026-03-01", "u1", "11/Lp14", "Izveido jaunu klimata ministriju."),
        (2, "Grozījumi mežu likumā (22/Lp14), 2.lasījums", "2026-03-01", "u2", "22/Lp14", "Maina mežu ciršanas noteikumus."),
        (3, "Grozījumi klimata likumā (33/Lp14), nodošana komisijām", "2026-03-01", "u3", "33/Lp14", "Klimata ministrijas pilnvaras."),
        (4, "Grozījumi klimata fonda likumā (44/Lp14), 2.lasījums", "2026-03-01", "u4", "44/Lp14", "Klimata ministrijas fonds."),
        # Sēdes vadība bez numura: 13.11. rutīnā tādi ierindojās Šlesera sarakstā.
        (5, "Par sēdes pārtraukumu", "2026-03-01", "u5", None, "Pārtraukums pirms klimata ministrijas likuma."),
    ]
    for vid, motif, day, url, nr, summary in votes:
        db.execute("INSERT INTO saeima_votes (id, motif, vote_date, url, document_nr, summary, topic) VALUES (?,?,?,?,?,?,'Vide')",
                   (vid, motif, day, url, nr, summary))
    for vid, pid in ((1, 1), (2, 1), (3, 1), (4, 2), (5, 1)):  # 44/Lp14 balsoja tikai cits deputāts
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote, politician_id) VALUES (?, 'x', 'TP', 'Par', ?)",
                   (vid, pid))
    db.commit()
    db.close()
    cid = store_claim(
        opponent_id=1, topic="Vide", stance="Bija pret klimata ministrijas izveidi.", quote=None, confidence=0.8,
        reasoning="Tests.", salience=0.5, document_id=10, source_url="https://x/1", stated_at="2026-03-10",
        embedding_bytes=struct.pack(f"{DIM}f", *_axis(0)), db_path=path,
    )
    store_claim(
        opponent_id=1, topic="Vide", stance="Atbalsta stingrākus mežu ciršanas noteikumus.", quote=None, confidence=0.8,
        reasoning="Tests.", salience=0.5, document_id=10, source_url="https://x/2", stated_at="2026-01-10",
        embedding_bytes=struct.pack(f"{DIM}f", *_axis(1)), db_path=path,
    )
    monkeypatch.setattr(src.db, "DB_PATH", path)
    monkeypatch.setattr(vc, "CACHE_PATH", tmp_path / "vec.npz")
    # Viltus embedētājs: viss par klimata ministriju ir pozīcijas virzienā, mežs — perpendikulāri.
    monkeypatch.setattr(vc, "_embed", lambda texts: np.stack([_axis(0) if "limata" in t else _axis(1) for t in texts]))
    return cid


def test_the_bill_the_position_speaks_of_comes_first_and_procedure_is_left_out(env, capsys):
    assert script.main(["1", "--claims", str(env)]) == 0
    out = capsys.readouterr().out
    assert "likumprojekti ar paša nodotu balsi 2" in out  # 11 un 22; 33 un sēdes pārtraukums ir procedūra, 44 nav paša balss
    first, second = out.index("1. 11/Lp14"), out.index("2. 22/Lp14")
    assert first < second and "paša balsis: Par×1" in out
    assert "33/Lp14" not in out and "44/Lp14" not in out and "vote:5" not in out


def test_sitting_day_votes_are_put_next_to_the_older_positions_they_touch(env, capsys):
    assert script.main(["1", "--votes-day", "2026-03-01"]) == 0
    out = capsys.readouterr().out
    assert "likumprojekti ar paša saturisku balsi 2" in out and "33/Lp14" not in out
    climate, forest = out.split("LIKUMPROJEKTS 22/Lp14")
    assert "LIKUMPROJEKTS 11/Lp14" in climate
    assert climate.index("klimata ministrijas izveidi") < climate.index("mežu ciršanas")
    assert forest.index("mežu ciršanas") < forest.index("klimata ministrijas izveidi")
