"""`claims.review_status` — a queryable review flag derived from `reasoning`.

WHY A COLUMN
The NEEDS_REVIEW marker lives inside `claims.reasoning` free text, which
produced three independent failure modes, only one of which is about spelling:

  1. The marker FORM drifted: REVIEWED -> Izvērtēts -> REVIEWED. Each drift
     blinded whichever query used the previous form.
  2. The marker POSITION drifted. CLAUDE.md's escalation rule 2 asks for a
     prefix, but agents mostly append: measured 2026-08-03, 20 of 119 open rows
     are prefixed, so the anchored `LIKE 'NEEDS_REVIEW%'` that the rule's own
     wording suggests sees 17 % of the queue and silently skips the rest.
  3. Nothing could measure age or count, so nothing did — 78 rows sat inside
     the 7-day window with none resolved.

Picking a marker fixes only (1). The column fixes all three, because after it
no reader parses prose.

WHY A TRIGGER AND NOT store_claim()
Deriving in `store_claim()` covers writes. It does NOT cover RESOLUTION, which
happens as `UPDATE claims SET reasoning = REPLACE(...)` in ad-hoc triage
scripts and never goes through a store function. A column maintained only on
the write path would therefore be correct at insert and wrong from the first
resolution onward — the same staleness bug, relocated. This repo already has
the scar: CLAUDE.md § "Write through the store_*() functions" records a raw
INSERT that reached a published brief in 2026-07-29 precisely because the
guardrail lived in a function.

So the derivation is a SQLite trigger on INSERT and on UPDATE OF reasoning.
Raw SQL cannot bypass it. These are the repo's first triggers.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.db import get_db, init_db, store_claim

URL = "https://www.la.lv/raksts"
DOC = "Politiķis kritizē valdības rīcību un prasa skaidrojumu par budžetu."


@pytest.fixture
def db_path(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Testa Politiķis', 'JV', 'opponent')"
    )
    db.execute(
        """INSERT INTO documents (id, content, content_hash, source_url, scraped_at, platform)
           VALUES (1, ?, 'h1', ?, '2026-08-03 10:00:00', 'web')""",
        (DOC, URL),
    )
    db.commit()
    db.close()

    from src import db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _status(db_path, claim_id):
    db = get_db(db_path)
    row = db.execute("SELECT review_status FROM claims WHERE id = ?", (claim_id,)).fetchone()
    db.close()
    return row["review_status"]


def _store(db_path, reasoning, topic="Valsts pārvalde"):
    return store_claim(
        opponent_id=1, document_id=1, topic=topic,
        stance="Kritizē valdības rīcību un prasa skaidrojumu par budžeta izpildi.",
        quote=None, confidence=0.6, reasoning=reasoning, salience=0.5,
        source_url=URL, stated_at="2026-08-03", db_path=db_path,
    )


def test_column_exists(db_path):
    db = get_db(db_path)
    cols = {r[1] for r in db.execute("PRAGMA table_info(claims)").fetchall()}
    db.close()
    assert "review_status" in cols


def test_clean_reasoning_gets_null(db_path):
    cid = _store(db_path, "Pozīcija ir tieši formulēta raksta tekstā, bez starpniekiem.")
    assert _status(db_path, cid) is None


def test_prefixed_marker_is_flagged(db_path):
    cid = _store(db_path, "NEEDS_REVIEW: tēmas robeža ir neskaidra, sk. avota kontekstu.")
    assert _status(db_path, cid) == "needs_review"


def test_suffixed_marker_is_flagged(db_path):
    """The 97-row class the anchored query silently skipped."""
    cid = _store(db_path, "Tēmas robeža ir neskaidra, sk. avota kontekstu. NEEDS_REVIEW")
    assert _status(db_path, cid) == "needs_review"


def test_raw_insert_is_still_classified(db_path):
    """A hand-rolled INSERT bypasses store_claim — the trigger must not care."""
    db = get_db(db_path)
    db.execute(
        """INSERT INTO claims (opponent_id, document_id, topic, stance, reasoning,
                               confidence, salience, source_url, stated_at, claim_type)
           VALUES (1, 1, 'Tieslietas', 'Nostāja', 'Kaut kas. NEEDS_REVIEW: šaubas.',
                   0.5, 0.5, ?, '2026-08-03', 'position')""",
        (URL,),
    )
    db.commit()
    cid = db.execute("SELECT id FROM claims WHERE topic='Tieslietas'").fetchone()["id"]
    db.close()
    assert _status(db_path, cid) == "needs_review"


def test_resolution_via_raw_update_flips_the_status(db_path):
    """This is the case store_claim-only derivation would get wrong.

    Triage resolves by REPLACING the marker in `reasoning` with `Izvērtēts
    <date>:` via ad-hoc SQL. The column has to follow that, or it starts lying
    on the first resolution.
    """
    cid = _store(db_path, "NEEDS_REVIEW: tēmas robeža ir neskaidra.")
    assert _status(db_path, cid) == "needs_review"

    db = get_db(db_path)
    db.execute(
        "UPDATE claims SET reasoning = ? WHERE id = ?",
        ("Izvērtēts 2026-08-03: tēmas robeža pārbaudīta pret avotu.", cid),
    )
    db.commit()
    db.close()
    assert _status(db_path, cid) == "reviewed"


def test_legacy_reviewed_marker_also_counts_as_resolved(db_path):
    """Both historical forms resolve — 56 rows carry REVIEWED, 169 Izvērtēts."""
    cid = _store(db_path, "REVIEWED 2026-06-13: tēma apstiprināta.")
    assert _status(db_path, cid) == "reviewed"


def test_izskatits_sweep_marker_also_counts_as_resolved(db_path):
    """Fourth historical form: the 07-19/07-29 sweeps resolved with
    `IZSKATĪTS (triāža …)`. Until 2026-08-04 the derivation did not know it,
    so all 31 such rows sat with review_status NULL — invisible to BOTH the
    open queue and the resolved count (BACKLOG § review_status derivācija)."""
    cid = _store(
        db_path,
        "Institūcijas pašas nostāja, avots pārbaudīts. IZSKATĪTS (triāža 2026-07-19).",
    )
    assert _status(db_path, cid) == "reviewed"


def test_lowercase_izskatits_prose_is_not_a_marker(db_path):
    """`izskatīts` is an everyday participle ("tiks izskatīts komisijā").
    The derivation may only match the uppercase marker form — SQLite LIKE
    folds case for ASCII only, so `Ī` ≠ `ī` keeps prose out. This pin exists
    so nobody "fixes" the pattern to lowercase and floods `reviewed`."""
    cid = _store(db_path, "Jautājums tiks izskatīts komisijā; pozīcija ir skaidra.")
    assert _status(db_path, cid) is None


def test_open_queue_is_countable_without_a_like(db_path):
    """The whole point: the queue has a denominator and an age, from a column."""
    _store(db_path, "NEEDS_REVIEW: pirmā šaubu rinda.", topic="Valsts pārvalde")
    _store(db_path, "NEEDS_REVIEW: otrā šaubu rinda.", topic="Tieslietas")
    _store(db_path, "Skaidra pozīcija bez šaubām.", topic="Izglītība")

    db = get_db(db_path)
    open_n = db.execute(
        "SELECT COUNT(*) FROM claims WHERE review_status = 'needs_review'"
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    db.close()
    assert (open_n, total) == (2, 3)


def test_migration_backfills_existing_rows(db_path):
    """A DB written before the column must classify on the next init_db()."""
    db = get_db(db_path)
    db.execute("DROP TRIGGER IF EXISTS claims_review_status_ai")
    db.execute("DROP TRIGGER IF EXISTS claims_review_status_au")
    db.execute(
        """INSERT INTO claims (opponent_id, document_id, topic, stance, reasoning,
                               confidence, salience, source_url, stated_at, claim_type)
           VALUES (1, 1, 'Vēsturiska', 'Nostāja', 'Veca rinda. NEEDS_REVIEW: šaubas.',
                   0.5, 0.5, ?, '2026-06-01', 'position')""",
        (URL,),
    )
    db.execute("UPDATE claims SET review_status = NULL WHERE topic = 'Vēsturiska'")
    db.commit()
    cid = db.execute("SELECT id FROM claims WHERE topic='Vēsturiska'").fetchone()["id"]
    db.close()
    assert _status(db_path, cid) is None  # pre-migration state

    init_db(db_path)  # re-running the migration must repair it
    assert _status(db_path, cid) == "needs_review"
