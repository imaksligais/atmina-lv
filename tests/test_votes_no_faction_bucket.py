"""Balsojumu lapas frakciju sadalījums nedrīkst nomest deputātus bez frakcijas.

Failure (backlog/saeima.md, fixed 2026-09-28): ``_fetch_votes`` filtered
``faction IS NOT NULL AND faction != ''``, so ballots of non-attached deputies
(T6 — a legitimate state) vanished from the per-vote breakdown. The faction rows
then no longer summed to ``saeima_votes`` totals (1 191 of 7 048 ballots in the
week 2026-09-21…27), and the same gap produced a weekly-brief error («pret
balsoja ZZS un LPV (27)» when 9 of the 27 were non-attached).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.render.votes import _fetch_votes
from src.render.votes_matrix import NO_FACTION_LABEL, _build_matrix_compact, _build_matrix_data

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    conn.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Koalīcija','CO','coalition')")
    conn.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Opozīcija','OP','opposition')")
    # Totals reconcile with the individual ballots below: Par 4, Pret 3, Atturas 1.
    conn.execute(
        "INSERT INTO saeima_votes (id,motif,vote_date,vote_time,total_par,total_pret,total_atturas,"
        "total_nebalso,result,url) VALUES (1,'Balsojums','2026-09-24','10:00:00',4,3,1,1,'Pieņemts','u1')"
    )
    ballots = [
        ("CO 1", "CO", "Par"), ("CO 2", "CO", "Par"), ("CO 3", "CO", "Par"),
        ("OP 1", "OP", "Pret"),
        # Non-attached — both storage forms, plus a whitespace-only one.
        ("N 1", None, "Pret"), ("N 2", "", "Pret"), ("N 3", "  ", "Atturas"),
        ("N 4", None, "Par"), ("N 5", None, "Nebalsoja"),
    ]
    for name, fac, vote in ballots:
        conn.execute(
            "INSERT INTO saeima_individual_votes (vote_id,deputy_name,faction,vote) VALUES (1,?,?,?)",
            (name, fac, vote),
        )
    conn.commit()
    yield conn
    conn.close()


def test_no_faction_ballots_form_a_named_bucket_that_reconciles(db):
    (vote,) = _fetch_votes(db)
    fb = vote["faction_breakdown"]
    assert [r["faction"] for r in fb] == ["CO", "OP", NO_FACTION_LABEL]  # bucket sorted last
    nf = fb[-1]
    assert (nf["par"], nf["pret"], nf["atturas"], nf["nebalso"]) == (1, 2, 1, 1)
    assert nf["coalition_status"] == "other"
    # The point of the fix: per-vote rows sum to the ledger totals.
    assert sum(r["par"] for r in fb) == vote["total_par"]
    assert sum(r["pret"] for r in fb) == vote["total_pret"]
    assert sum(r["atturas"] for r in fb) == vote["total_atturas"]
    assert all(r["faction"] for r in fb), "tukšs vai None frakcijas nosaukums"


def test_bucket_reaches_the_matrix_json(db):
    votes = _fetch_votes(db)
    compact = _build_matrix_compact(_build_matrix_data(db, votes))
    names = [f["f"] for f in compact["votes"][0]["f"]]
    assert names[-1] == NO_FACTION_LABEL
    assert None not in names and "None" not in names


def test_label_is_one_vocabulary_across_python_and_js():
    """The weekly brief, the render and bmv1.js (which never flags the bucket
    as «dalīts») must use the same literal, or the JS split-suppression
    silently stops matching."""
    from src.briefs import _NO_FACTION_LABEL

    assert NO_FACTION_LABEL == _NO_FACTION_LABEL
    js = (ROOT / "assets" / "bmv1.js").read_text(encoding="utf-8")
    m = re.search(r'var NO_FACTION = "([^"]+)";', js)
    assert m and m.group(1) == NO_FACTION_LABEL
    assert "if (fb.f === NO_FACTION) return false;" in js


def test_bucket_sorts_after_every_status_even_when_larger():
    """Sorted last by rule, not by accident of size or status order: an
    'other' faction smaller than the bucket must still precede it."""
    from src.render.votes import _enrich_faction_breakdown

    rows = [
        {"faction": NO_FACTION_LABEL, "par": 20, "pret": 0, "atturas": 0, "nebalso": 0},
        {"faction": "Nav kart", "par": 5, "pret": 0, "atturas": 0, "nebalso": 0},
        {"faction": "JV", "par": 24, "pret": 0, "atturas": 0, "nebalso": 0},
    ]
    out = _enrich_faction_breakdown(rows, {"JV": "coalition"})
    assert [r["faction"] for r in out] == ["JV", "Nav kart", NO_FACTION_LABEL]


def test_js_card_shows_full_counts_for_the_bucket():
    """A non-split chip prints ONE number under the majority label; for the
    bucket that would turn 5 par + 4 pret into «9 par»."""
    js = (ROOT / "assets" / "bmv1.js").read_text(encoding="utf-8")
    assert "var fullCounts = isSplit || fb.f === NO_FACTION;" in js
    assert "if (fullCounts) {" in js
