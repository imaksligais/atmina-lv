"""Every reader must build the daily-brief `topic` the same way the writer does.

`context_notes.topic` encodes the brief's subject day as
``'dienas analīze YYYY-MM-DD'``. A reader that hand-rolls the literal drifts:
the (since removed) telegram path used ``'dienas pārskats {date}'`` — a form
nothing ever writes — so its lookup matched no row and its narrative bullets
were silently always empty. Nothing raised: a wrong topic string just returns
nothing, which is the repo's named silent-success failure mode. The telegram
brief was deleted 2026-08-03, but the constant it drifted from is the reason
this file exists — the next hand-rolled literal fails exactly the same way.
See BACKLOG 2026-07-16, fixed 2026-07-25.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from src.briefs import DAILY_BRIEF_TOPIC_PREFIX, daily_brief_topic
from src.db import get_db, init_db

DAY = "2026-07-24"
# Bullets are consecutive lines in one block, exactly as generate_daily_brief
# emits them — the reader takes bullet_blocks[0], so a fixture with blank lines
# between bullets would test a shape production never produces.
BRIEF_BODY = """# Dienas analīze — 2026-07-24

## Galvenais

<!-- DIENAS STATS (iekšēja piezīme aģentam; nav renderēta publikai): 737 dokumenti -->

- **Pirmā tēma:** premjers paziņo par vēršanos tiesā.
- **Otrā tēma:** ministre paziņo par protesta notu.

## Aktīvākie politiķi

| Politiķis | Partija |
|---|---|
| Kāds | Kaut kāda |
"""


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Testa Politiķis', 'Testa partija', 'opponent')"
    )
    db.execute(
        """INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at)
           VALUES (NULL, 'daily_brief', ?, ?, ?)""",
        (daily_brief_topic(DAY), BRIEF_BODY, f"{DAY} 22:52:51"),
    )
    db.commit()
    db.close()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_topic_helper_matches_the_documented_encoding():
    assert daily_brief_topic(DAY) == "dienas analīze 2026-07-24"
    assert DAILY_BRIEF_TOPIC_PREFIX == "dienas analīze "
    # The drifted form must not be produced by anyone.
    assert "pārskats" not in daily_brief_topic(DAY)


def test_stored_brief_topic_is_the_form_readers_look_for(db_path):
    """The row the writer stores must be findable with the helper — this is the
    join that silently failed."""
    db = sqlite3.connect(db_path)
    row = db.execute(
        "SELECT content FROM context_notes WHERE note_type='daily_brief' AND topic = ?",
        (daily_brief_topic(DAY),),
    ).fetchone()
    db.close()
    assert row is not None
    assert "Galvenais" in row[0]
