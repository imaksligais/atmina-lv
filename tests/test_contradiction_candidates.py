"""Kandidātu pāri no claim_vectors — bez API, uz pagaidu DB."""
from __future__ import annotations

import os
import struct
import tempfile

import numpy as np
import pytest

from src.contradiction_candidates import (
    OPPOSITE_CRITERIA,
    OPPOSITE_INSTRUCTIONS,
    PAIR_CONTEXT,
    candidate_pairs,
    load_position_vectors,
    pair_states,
    undated_positions,
)
from src.db import get_db, init_db
from src.party_contradictions import ensure_vec


def _unit(*vals: float) -> list[float]:
    vec = list(vals) + [0.0] * (384 - len(vals))
    n = float(np.linalg.norm(vec)) or 1.0
    return [v / n for v in vec]


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _claim(db, cid, pid, stance, stated_at, *, topic="Nodokļi", claim_type="position",
           speaker_id=None, vector=None, quote=None):
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, source_url, stated_at, "
        "claim_type, speaker_id, document_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (cid, pid, topic, stance, quote, f"https://x/{cid}", stated_at, claim_type, speaker_id),
    )
    if vector is not None:
        ensure_vec(db)
        db.execute("INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
                   (cid, struct.pack("384f", *vector)))


def _seed(db_path):
    db = get_db(db_path)                       # PRAGMA foreign_keys=ON → dokuments 1 jāeksistē
    db.execute("INSERT INTO documents (id, content, content_hash, scraped_at) "
               "VALUES (1, 'teksts', 'h1', '2025-01-01 00:00:00')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (7, 'Testa Persona', 'P')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (8, 'Cits Cilvēks', 'P')")
    # 1 ↔ 2 gandrīz vienādi; 3 tuvāks 1 nekā 2; 4 ortogonāls
    _claim(db, 1, 7, "Atbalsta nodokļu celšanu", "2025-01-10", vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 2, 7, "Pret nodokļu celšanu", "2025-03-01", vector=_unit(0.95, 0.1, 0.0), quote="Nē!")
    _claim(db, 3, 7, "Nodokļus jāceļ pakāpeniski", "2025-02-01", vector=_unit(0.8, 0.0, 0.3))
    _claim(db, 4, 7, "Rail Baltica jāaptur", "2025-04-01", topic="Rail Baltica", vector=_unit(0.0, 0.0, 1.0))
    _claim(db, 5, 7, "Bez vektora", "2025-05-01")                                   # nav vektora → ārā
    _claim(db, 6, 7, "Balsoja PAR", "2025-05-02", claim_type="saeima_vote", vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 9, 7, "Komentārs par 7", "2025-05-03", speaker_id=8, vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 10, 8, "Cita politiķa", "2025-05-04", vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 11, 7, "Bez datuma, gandrīz kā 1", None, vector=_unit(1.0, 0.0, 0.0))  # stated_at=None → ārā
    db.commit()
    db.close()


def test_load_position_vectors_filters_type_speaker_and_missing(db_path):
    _seed(db_path)
    db = get_db(db_path)
    ids, M = load_position_vectors(db, 7)
    db.close()
    assert ids == [1, 2, 3, 4]                    # 11 (bez stated_at) izlaista
    assert M.shape == (4, 384)
    assert np.allclose(np.linalg.norm(M, axis=1), 1.0)


def test_undated_positions_counted_not_paired(db_path):
    _seed(db_path)
    db = get_db(db_path)
    assert undated_positions(db, 7) == 1           # claim 11
    assert undated_positions(db, 8) == 0
    db.close()
    pairs = candidate_pairs(7, k=10, db_path=db_path)
    assert all(11 not in ab for ab in pairs)


def test_candidate_pairs_k1_are_nearest_neighbours_chronological(db_path):
    _seed(db_path)
    pairs = candidate_pairs(7, k=1, db_path=db_path)
    # kosinusi: (1,2)=0.99 (1,3)=0.94 (2,3)=0.93 (3,4)=0.35 (1,4)=(2,4)=0
    # k=1: 1→2, 2→1, 3→1, 4→3 → pāri {1,2} {1,3} {3,4}; hronoloģiski
    # 1 (01-10) < 3 (02-01) < 2 (03-01) < 4 (04-01), kārtoti pēc (old, new):
    assert pairs == [(1, 3), (1, 2), (3, 4)]
    # katrs pāris hronoloģisks: old.stated_at <= new.stated_at
    db = get_db(db_path)
    dates = dict(db.execute("SELECT id, stated_at FROM claims").fetchall())
    db.close()
    assert all(dates[a] <= dates[b] for a, b in pairs)


def test_candidate_pairs_k_large_gives_all_pairs(db_path):
    _seed(db_path)
    pairs = candidate_pairs(7, k=10, db_path=db_path)
    assert len(pairs) == 6                       # C(4,2)
    assert len(set(pairs)) == 6


def test_candidate_pairs_empty_for_unknown_or_single(db_path):
    _seed(db_path)
    assert candidate_pairs(999, db_path=db_path) == []
    assert candidate_pairs(8, db_path=db_path) == []      # viena pozīcija — nav pāru


def test_candidate_pairs_rejects_k_below_one(db_path):
    _seed(db_path)
    with pytest.raises(ValueError):
        candidate_pairs(7, k=0, db_path=db_path)


def test_pair_states_shape_and_privacy(db_path):
    _seed(db_path)
    db = get_db(db_path)
    states = pair_states(db, [(1, 2)])
    db.close()
    assert states == [{
        "old": {"stance": "Atbalsta nodokļu celšanu", "quote": None, "topic": "Nodokļi", "date": "2025-01-10"},
        "new": {"stance": "Pret nodokļu celšanu", "quote": "Nē!", "topic": "Nodokļi", "date": "2025-03-01"},
    }]
    # uz API neiet ne reasoning, ne politiķa vārds, ne id
    assert "reasoning" not in states[0]["old"] and "id" not in states[0]["old"]


def test_question_texts_are_latvian_and_reference_row():
    assert "{row}" in OPPOSITE_INSTRUCTIONS
    assert set(OPPOSITE_CRITERIA) == {"true", "false"}
    assert "politiķ" in PAIR_CONTEXT["politician"]
    for txt in (OPPOSITE_INSTRUCTIONS, *OPPOSITE_CRITERIA.values()):
        assert "ā" in txt or "ē" in txt or "ī" in txt   # garumzīmes — nav ASCII-nolobīts
