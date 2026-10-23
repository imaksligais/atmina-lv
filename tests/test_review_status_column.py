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


def test_lowercase_izvertets_prose_is_not_a_marker(db_path):
    """`izvērtēts` is ordinary prose ("tiek izvērtēts rīcības algoritms").
    LIKE folded the ASCII `I`/`i`, so this resolved rows on the live DB
    (#17964, #20846 measured 2026-09-05). The derivation is case-sensitive."""
    cid = _store(db_path, "Pēc katra incidenta tiek izvērtēts rīcības algoritms.")
    assert _status(db_path, cid) is None


def test_reviewed_at_column_name_in_prose_is_not_a_marker(db_path):
    """`reviewed_at` is a column name that triage notes quote in backticks.
    LIKE folded it onto the REVIEWED marker (#709064 on the live DB)."""
    cid = _store(db_path, "Dokumentam `reviewed_at` jau bija uzlikts, tāpēc rindā neienāca.")
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


# --------------------------------------------------------------------------
# review_status_at — KAD marķieris tika uzlikts (verdikts 44, 2026-09-07)
#
# 14 dienu vārti (@quality-reviewer § A, quality-bars.md) mērīja vecumu no
# `claims.created_at`, tāpēc tie nešķīra «pūst rindā kopš aprīļa» no «vakar
# retro-marķēts». 2026-08-22 tie ziņoja BAR BREACH par 19 rindām, kas rindā
# bija nokļuvušas iepriekšējā dienā. Vārti nosauca reālu darbu ar nepareizu
# pamatojumu un būtu to atkārtojuši pie katras nākamās retro-marķēšanas.
#
# Kolonnu uztur TIE PAŠI divi trigeri, kas `review_status` — ar roku to neraksta
# tāpat kā `review_status`. Otrais variants (parsēt `Izvērtēts`-datumu no
# prozas) atgriež tieši to, ko 2026-08-03 lēmums aizliedza.
# --------------------------------------------------------------------------


def _stamp(db_path, claim_id):
    db = get_db(db_path)
    row = db.execute(
        "SELECT review_status, review_status_at, created_at FROM claims WHERE id = ?",
        (claim_id,),
    ).fetchone()
    db.close()
    return row


def test_review_status_at_column_exists(db_path):
    db = get_db(db_path)
    cols = {r[1] for r in db.execute("PRAGMA table_info(claims)").fetchall()}
    db.close()
    assert "review_status_at" in cols


def test_clean_row_gets_no_stamp(db_path):
    """`review_status` NULL -> nekas nav mainījies -> nav ko zīmogot."""
    cid = _store(db_path, "Pozīcija ir tieši formulēta raksta tekstā, bez starpniekiem.")
    row = _stamp(db_path, cid)
    assert row["review_status"] is None
    assert row["review_status_at"] is None


def test_insert_with_marker_is_stamped_in_lv_time(db_path):
    from src.db import now_lv

    before = now_lv()
    cid = _store(db_path, "NEEDS_REVIEW: tēmas robeža ir neskaidra.")
    after = now_lv()
    row = _stamp(db_path, cid)
    assert row["review_status"] == "needs_review"
    # Formāts un josla: tāds pats kā now_lv() ("YYYY-MM-DD HH:MM:SS", LV laiks).
    # Ja trigeris rakstītu UTC, šis salīdzinājums kristu par trim stundām.
    assert before <= row["review_status_at"] <= after, row["review_status_at"]


def test_resolution_moves_the_stamp_forward(db_path):
    """Retro-marķēšanas klase: veca rinda, šodien atrisināta -> jauns zīmogs."""
    cid = _store(db_path, "NEEDS_REVIEW: tēmas robeža ir neskaidra.")
    first = _stamp(db_path, cid)["review_status_at"]

    db = get_db(db_path)
    db.execute("UPDATE claims SET review_status_at = '2026-04-01 09:00:00' WHERE id = ?", (cid,))
    db.execute(
        "UPDATE claims SET reasoning = ? WHERE id = ?",
        ("Izvērtēts 2026-09-07: tēmas robeža pārbaudīta pret avotu.", cid),
    )
    db.commit()
    db.close()

    row = _stamp(db_path, cid)
    assert row["review_status"] == "reviewed"
    assert row["review_status_at"] > "2026-04-01 09:00:00"
    assert first is not None


def test_reasoning_edit_that_does_not_change_the_status_keeps_the_stamp(db_path):
    """Stilistisks labojums NEdrīkst atiestatīt rindas vecumu — citādi katrs
    pieskāriens nomazgā to pašu, ko vārti mēra."""
    cid = _store(db_path, "NEEDS_REVIEW: tēmas robeža ir neskaidra.")
    db = get_db(db_path)
    db.execute("UPDATE claims SET review_status_at = '2026-04-01 09:00:00' WHERE id = ?", (cid,))
    db.execute(
        "UPDATE claims SET reasoning = ? WHERE id = ?",
        ("NEEDS_REVIEW: tēmas robeža ir neskaidra; avots pārbaudāms.", cid),
    )
    db.commit()
    db.close()
    row = _stamp(db_path, cid)
    assert row["review_status"] == "needs_review"
    assert row["review_status_at"] == "2026-04-01 09:00:00"


def test_raw_insert_is_stamped_too(db_path):
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
    assert _stamp(db_path, cid)["review_status_at"] is not None


def test_backfill_leaves_the_stamp_null_because_we_do_not_know_when(db_path):
    """Vēsturiskām rindām īsto marķēšanas brīdi neviens nav pierakstījis.
    NULL + COALESCE fallback uz `created_at` ir konservatīvā puse (vecāks =
    drīzāk pārkāpj vārtus), nevis šodienas datums, kas rindu klusi attaisnotu."""
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

    init_db(db_path)
    row = _stamp(db_path, cid)
    assert row["review_status"] == "needs_review"
    assert row["review_status_at"] is None


def test_open_review_queue_ages_from_the_marker_not_the_claim(db_path):
    """Vārtu forma: `COALESCE(review_status_at, created_at)`.

    Rinda, kas radīta aprīlī un marķēta šodien, ir 0 dienas veca rindā;
    rinda bez zīmoga krīt atpakaļ uz `created_at` un paliek veca.
    """
    from src.db import open_review_queue

    fresh = _store(db_path, "NEEDS_REVIEW: šodien marķēta.", topic="Valsts pārvalde")
    stale = _store(db_path, "NEEDS_REVIEW: sena rinda.", topic="Tieslietas")

    db = get_db(db_path)
    # Abas radītas aprīlī; svaigajai zīmogs paliek šodienas, senajai to noņemam
    # (= pirms-migrācijas rinda).
    db.execute("UPDATE claims SET created_at = '2026-04-01 09:00:00'")
    db.execute("UPDATE claims SET review_status_at = NULL WHERE id = ?", (stale,))
    db.commit()
    db.close()

    ages = {r["id"]: r["age_days"] for r in open_review_queue(db_path=db_path)}
    assert set(ages) == {fresh, stale}
    assert ages[fresh] == 0, "šodien marķēta rinda nedrīkst skaitīties par vecu"
    assert ages[stale] > 14, "rinda bez zīmoga krīt atpakaļ uz created_at"


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
