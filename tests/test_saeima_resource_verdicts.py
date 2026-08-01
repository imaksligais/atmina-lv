"""End-to-end exercise of the two 2026-08-21 resource verdicts.

Both landed in commit `4c8c37c6` (2026-08-21 16:41:54) and were recorded IZPILDĪTS
in the CHANGELOG — but the 2026-08-22 audit measured that neither had ever RUN:
``MAX(created_at)`` on ``saeima_votes``, on ``saeima_vote`` claims, and
``MAX(timestamp)`` on ``logs.action='saeima_vote_claim'`` were all
``2026-08-21 01:08:13``, i.e. BEFORE the fix commit. Zero vote loads since.
"Done" meant "merged", not "exercised" — see
``docs/audits/2026-08-22-slop-un-bloat-audits.md`` § 4 point 5.

What existed already and what did not:

* ``tests/test_db.py::TestStoreClaimEmbeddingBytes::test_saeima_vote_not_auto_embedded``
  covers verdict (a) at the UNIT level — one direct ``store_claim`` call.
* Verdict (b), the log batching in ``src/saeima/votes.py``, had **no test at all**
  (``grep -rn saeima_vote_claim tests/`` returned only this file's absence).
* Neither was exercised through ``generate_claims_from_votes`` — the function a real
  Saeima ingest actually calls.

This file closes both gaps by running the real load path.

**Why three deputies and not one.** A single-deputy vote generates one claim, and
"one log row per claim" and "one log row per load" are indistinguishable at N=1 —
the assertion would pass identically against the pre-fix code. That is precisely the
"gate that cannot fail" class ``CLAUDE.md`` names. With N=3 the two behaviours differ
(3 rows vs 1), so the test can actually fail if the batching regresses.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.db import get_db, init_db
from src.saeima import (
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    init_saeima_tables,
)

DEPUTIES = [
    (1, "Anna Bērziņa", "JV", "Par"),
    (2, "Jānis Kalniņš", "ZZS", "Pret"),
    (3, "Ilze Ozoliņa", "NA", "Atturas"),
]


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def votes_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)

    db = get_db(path)
    for pid, name, party, _ballot in DEPUTIES:
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (?, ?, ?)",
            (pid, name, party),
        )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def generated(votes_db, monkeypatch):
    """Run the real vote→claims path once and hand back (db_path, claim_ids)."""
    import src.db as db_mod
    import src.saeima as saeima_mod

    monkeypatch.setattr(db_mod, "DB_PATH", votes_db)
    monkeypatch.setattr(saeima_mod, "DB_PATH", votes_db)

    vote = VoteResult(
        motif="Par likumprojekta pieņemšanu otrajā lasījumā",
        date="2026-08-22",
        time="10:30",
        total_par=50,
        total_pret=30,
        total_atturas=5,
        total_nebalso=15,
        result="Pieņemts",
        url="/voting/99001",
        individual_votes=[
            IndividualVote(
                deputy_name=name, faction=party, vote=ballot, politician_id=pid
            )
            for pid, name, party, ballot in DEPUTIES
        ],
    )
    claim_ids = generate_claims_from_votes(vote, vote_db_id=0, db_path=votes_db)
    return votes_db, claim_ids


def test_load_path_generates_one_claim_per_cast_ballot(generated):
    """Sanity denominator: all three ballots are cast values, so all three
    become claims (Data Contract #4b — attendance states never do)."""
    _db_path, claim_ids = generated
    assert len(claim_ids) == len(DEPUTIES) == 3, (
        f"expected {len(DEPUTIES)} claims, got {len(claim_ids)} — the rest of "
        f"this file's assertions depend on N>1 to be meaningful"
    )


def test_verdict_a_no_vectors_through_the_real_load_path(generated):
    """2026-08-21 verdict (a): saeima_vote claims are no longer auto-embedded.

    Exercised through generate_claims_from_votes, not a bare store_claim call —
    the unit test could stay green while the load path passed embedding_bytes
    or called a different writer.
    """
    import sqlite_vec

    db_path, claim_ids = generated
    db = get_db(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    placeholders = ",".join("?" * len(claim_ids))
    vectored = db.execute(
        f"SELECT COUNT(*) FROM claim_vectors WHERE claim_id IN ({placeholders})",
        claim_ids,
    ).fetchone()[0]
    db.close()

    assert vectored == 0, (
        f"{vectored} of {len(claim_ids)} vote claims got a vector — the "
        f"2026-08-21 no-embed verdict regressed in the load path. Vote vectors "
        f"were 98% of a 973 MB claim_vectors table and no kNN reader returns "
        f"them (T10); rhetoric-vs-vote needs structural SQL (T9)."
    )


def test_verdict_b_one_summary_log_row_per_load_not_per_claim(generated):
    """2026-08-21 verdict (b): one summary log row per load.

    Pre-fix this wrote one row per claim — 642 764 of 646 400 logs rows, ~163 MiB.
    With 3 claims the two behaviours are distinguishable; with 1 they are not.
    """
    db_path, claim_ids = generated
    db = get_db(db_path)
    rows = db.execute(
        "SELECT status, opponent_id, details FROM logs WHERE action = 'saeima_vote_claim'"
    ).fetchall()
    db.close()

    assert len(rows) == 1, (
        f"{len(rows)} 'saeima_vote_claim' log rows for {len(claim_ids)} claims — "
        f"expected exactly 1. Per-claim logging regressed."
    )

    row = rows[0]
    assert row["status"] == "success"
    assert row["opponent_id"] is None, (
        "the summary row covers a whole load, so it must not be attributed to a "
        "single politician"
    )

    details = json.loads(row["details"])
    assert details["claims_generated"] == len(claim_ids), (
        f"summary row claims_generated={details['claims_generated']} but "
        f"{len(claim_ids)} claims were written — the summary lies about its own load"
    )
    assert details["first_claim_id"] == claim_ids[0]
    assert details["last_claim_id"] == claim_ids[-1]
    assert details["vote_db_id"] == 0


def test_action_name_preserved_for_downstream_readers(generated):
    """The verdict deliberately kept the `saeima_vote_claim` action name so the
    dashboard activity filter (which skips this class on purpose) and historical
    queries keep working. A rename would silently un-hide 642k historical rows.
    """
    db_path, _claim_ids = generated
    db = get_db(db_path)
    actions = [r["action"] for r in db.execute("SELECT DISTINCT action FROM logs")]
    db.close()
    assert "saeima_vote_claim" in actions, actions
