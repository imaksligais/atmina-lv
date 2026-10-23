"""`claims.quote` is verified against the SOURCE, not against a diacritic ratio.

CLAUDE.md is explicit that `claims.quote` is VERBATIM and that the LV grammar /
diacritic gate "applies to OUR words (stance, reasoning, summary), never to
cited ones" — a politician's own spelling stays (the Kulbergs "Steidamas"
ruling). Running `validate_lv_diacritics` over `quote` therefore asked the
wrong question, and it failed in both directions:

  * FALSE REJECT — claim #555664 (Hermanis) carried an authentic low-diacritic
    Latvian sentence. The gate refused it, and because a quote may not be
    edited, the only legal move left was to store no quote at all. The gate
    silently removed provenance. The 2026-08-02 tightening took rejected quotes
    from 1 to 8, so this is the common case now, not the rare one.
  * FALSE PASS — the gate is a RATIO test, so a sentence with one damaged word
    sails through. Measured over the live DB (2026-08-03): 31 stored quotes
    match their source document only after diacritic folding.

The replacement asks the right question: is this text in the document? Measured
on the same 4735 checkable rows, 4219 (89.1 %) match verbatim, 31 match only
after folding, and 485 (10.2 %) are not found at all. That last group is mostly
legitimate — English quotes, elisions marked `(..)`, and re-fetched bodies that
no longer contain the original wording — so "not found" must NOT reject. Only
the folded-only class is provably our corruption, and it is rejected.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.db import get_db, init_db, store_claim

URL = "https://www.la.lv/testa-raksts"

# Authentic, diacritic-light Latvian — 1 diacritic in ~70 letters (~1.4 %),
# under the 1.5 % ratio floor. This is the #555664 shape.
LOW_DIACRITIC_QUOTE = (
    "Kulbergs ir tas pats Briškens, tikai citai auditorijai. "
    "Garu garie teikumi, nulle darbu."
)

# Diacritic-RICH, so the ratio gate passes it happily; one word is damaged.
SOURCE_SENTENCE = (
    "Viņi ir pievīluši savu doto solījumu un tagad meklē attaisnojumus "
    "sabiedrības priekšā."
)
CORRUPTED_QUOTE = SOURCE_SENTENCE.replace("pievīluši", "pieviluši")

DOC_CONTENT = (
    "Intervija ar politiķi.\n\n"
    f"{LOW_DIACRITIC_QUOTE}\n\n"
    f"{SOURCE_SENTENCE}\n\n"
    "Raksta beigas."
)


@pytest.fixture
def db_path(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Testa Politiķis', 'Testa partija', 'opponent')"
    )
    db.execute(
        """INSERT INTO documents (id, content, content_hash, source_url, scraped_at, platform)
           VALUES (1, ?, 'h1', ?, '2026-08-03 10:00:00', 'web')""",
        (DOC_CONTENT, URL),
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


def _store(db_path, **over):
    kwargs = dict(
        opponent_id=1,
        document_id=1,
        topic="Valsts pārvalde",
        stance="Politiķis kritizē valdības rīcību šajā jautājumā un prasa skaidrojumu.",
        quote=None,
        confidence=0.8,
        reasoning="Pozīcija ir tieši formulēta intervijas tekstā, bez starpniekiem.",
        salience=0.5,
        source_url=URL,
        stated_at="2026-08-03",
        db_path=db_path,
    )
    kwargs.update(over)
    return store_claim(**kwargs)


def test_authentic_low_diacritic_quote_is_accepted_when_verbatim_in_source(db_path):
    """The #555664 false reject. The sentence is really in the document, so it
    is really what the person said — the ratio is irrelevant."""
    claim_id = _store(db_path, quote=LOW_DIACRITIC_QUOTE, topic="Koalīcija un partijas")
    db = get_db(db_path)
    stored = db.execute("SELECT quote FROM claims WHERE id = ?", (claim_id,)).fetchone()
    db.close()
    assert stored["quote"] == LOW_DIACRITIC_QUOTE


def test_quote_matching_source_only_after_diacritic_folding_is_rejected(db_path):
    """Our corruption: one macron dropped from an otherwise diacritic-rich
    sentence. The ratio gate passes this; the source comparison must not."""
    with pytest.raises(ValueError, match="quote"):
        _store(db_path, quote=CORRUPTED_QUOTE, topic="Budžets un finanses")


def test_rejection_names_the_source_wording(db_path):
    """The fix is to restore the document's text, so the error has to show it."""
    with pytest.raises(ValueError) as exc:
        _store(db_path, quote=CORRUPTED_QUOTE, topic="Budžets un finanses")
    assert "pievīluši" in str(exc.value)


def test_quote_absent_from_source_is_accepted(db_path):
    """Measured 10.2 % of live rows and mostly legitimate (English, elisions,
    re-fetched bodies). Rejecting here would block real claims."""
    claim_id = _store(
        db_path,
        quote="We want Moldova to succeed and to become an EU member soon.",
        topic="Ārpolitika",
    )
    assert isinstance(claim_id, int)


def test_stance_is_still_diacritic_gated(db_path):
    """The gate must keep protecting OUR words — this is context-drift output."""
    with pytest.raises(ValueError, match="stance"):
        _store(
            db_path,
            stance="Politikis kritize valdibas ricibu saja jautajuma un prasa skaidrojumu.",
            topic="Tieslietas",
        )


def test_reasoning_is_still_diacritic_gated(db_path):
    with pytest.raises(ValueError, match="reasoning"):
        _store(
            db_path,
            reasoning="Pozicija ir tiesi formuleta intervijas teksta, bez starpniekiem.",
            topic="Izglītība",
        )
