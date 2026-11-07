"""Tests for parse_visual_brief() — extracts Vizualais brief markdown block."""
from src.briefs import parse_visual_brief


FULL_VALID = """
# Dienas analīze — 2026-04-17

## Galvenais

Some narrative body text. 30 milj. aizdevums apstiprināts.

## Spriedzes

| x | y |

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** Saeima lemj par 30 milj. airBaltic aizdevumu
- **Skaitlis:** 30 milj.
- **Metaforas hint:** lidmašīna ar plaisu
"""


def test_parse_returns_dict_with_four_fields():
    vb = parse_visual_brief(FULL_VALID)
    assert vb == {
        "topic": "airBaltic",
        "headline": "Saeima lemj par 30 milj. airBaltic aizdevumu",
        "stat": "30 milj.",
        "metaphor_hint": "lidmašīna ar plaisu",
    }


def test_parse_missing_block_returns_none():
    content = "# Brief without visual block.\n\nJust body text.\n"
    assert parse_visual_brief(content) is None


def test_parse_dash_stat_becomes_none():
    content = """
Body text.

## Vizuālais brief

- **Tēma:** Koalīcija un partijas
- **Galvenā tēze:** JV Milānas seminārs
- **Skaitlis:** -
- **Metaforas hint:** puzzle gabaliņi
"""
    vb = parse_visual_brief(content)
    assert vb["stat"] is None


def test_parse_empty_stat_becomes_none():
    content = """
Body text here.

## Vizuālais brief

- **Tēma:** Ārpolitika
- **Galvenā tēze:** Orbāna sakāve
- **Skaitlis:**
- **Metaforas hint:** karte
"""
    vb = parse_visual_brief(content)
    assert vb["stat"] is None


def test_stat_validation_drops_stat_not_in_body():
    content = """
Body text without specific numbers — general commentary only.

## Vizuālais brief

- **Tēma:** Budžets un finanses
- **Galvenā tēze:** budžeta lēmums
- **Skaitlis:** +999 milj.
- **Metaforas hint:** bar chart
"""
    vb = parse_visual_brief(content)
    # "+999 milj." substring is NOT in body → dropped
    assert vb["stat"] is None


def test_stat_validation_keeps_stat_in_body():
    content = """
Diena pilna ar ziņām. Saeima apstiprināja 30 milj. aizdevumu.

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** aizdevums
- **Skaitlis:** 30 milj.
- **Metaforas hint:** lidmašīna
"""
    vb = parse_visual_brief(content)
    assert vb["stat"] == "30 milj."


def test_parse_tolerates_missing_metaphor_hint():
    content = """
Body.

## Vizuālais brief

- **Tēma:** Ārpolitika
- **Galvenā tēze:** x
- **Skaitlis:** -
- **Metaforas hint:**
"""
    vb = parse_visual_brief(content)
    assert vb["metaphor_hint"] == ""


def test_parse_returns_none_if_topic_missing():
    content = """
Body.

## Vizuālais brief

- **Galvenā tēze:** x
- **Skaitlis:** -
"""
    assert parse_visual_brief(content) is None


def test_parse_returns_none_if_headline_missing():
    content = """
Body.

## Vizuālais brief

- **Tēma:** airBaltic
- **Skaitlis:** -
"""
    assert parse_visual_brief(content) is None


def test_parse_preserves_diacritics():
    content = """
Body.

## Vizuālais brief

- **Tēma:** Ārpolitika
- **Galvenā tēze:** Orbāna sakāve — politiķu atbalsis
- **Skaitlis:** -
- **Metaforas hint:** globuss un tilts
"""
    vb = parse_visual_brief(content)
    assert "Ārpolitika" in vb["topic"]
    assert "Orbāna" in vb["headline"]
    assert "politiķu" in vb["headline"]


def test_parse_ignores_vizualais_brief_inside_code_block():
    """If brief-writer accidentally shows the template inside a code fence,
    parser should still find the real block if it appears later, or return
    None if no real block exists. This test documents the conservative
    behaviour — we parse the FIRST occurrence outside of code fences
    OR the last occurrence overall (whatever the implementation picks,
    lock it in)."""
    content = """
Body.

Example:

```
## Vizuālais brief

- **Tēma:** example-topic
- **Galvenā tēze:** example
- **Skaitlis:** -
- **Metaforas hint:** demo
```

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** Saeima lemj par 30 milj. airBaltic aizdevumu
- **Skaitlis:** -
- **Metaforas hint:** lidmašīna
"""
    vb = parse_visual_brief(content)
    # The real (last) block should win — `airBaltic`, not `example-topic`
    assert vb["topic"] == "airBaltic"


def test_parse_skips_placeholder_stub_after_real_block():
    """If a placeholder example block appears AFTER a real one, parser must
    pick the real block, not the stub. Guards against parsing postscripts."""
    content = """
Body with 30 milj. figure.

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** Saeima lemj par 30 milj. airBaltic aizdevumu
- **Skaitlis:** 30 milj.
- **Metaforas hint:** lidmašīna

(reminder to self — next time:)

## Vizuālais brief

- **Tēma:** <topic>
- **Galvenā tēze:** <headline>
- **Skaitlis:** -
- **Metaforas hint:** <hint>
"""
    vb = parse_visual_brief(content)
    assert vb is not None
    assert vb["topic"] == "airBaltic"
    assert vb["stat"] == "30 milj."


def test_parse_skips_trailing_empty_stub():
    """An empty/malformed trailing block must not override an earlier valid one."""
    content = """
Body.

## Vizuālais brief

- **Tēma:** Ārpolitika
- **Galvenā tēze:** Orbāna sakāve
- **Skaitlis:** -
- **Metaforas hint:** globuss

## Vizuālais brief

- **Tēma:**
- **Galvenā tēze:**
"""
    vb = parse_visual_brief(content)
    assert vb is not None
    assert vb["topic"] == "Ārpolitika"


def test_parse_handles_crlf_line_endings():
    """CRLF inputs (Windows-style) must parse identically to LF."""
    content = (
        "# Body with 30 milj.\r\n\r\n"
        "## Vizuālais brief\r\n\r\n"
        "- **Tēma:** airBaltic\r\n"
        "- **Galvenā tēze:** aizdevums\r\n"
        "- **Skaitlis:** 30 milj.\r\n"
        "- **Metaforas hint:** lidmašīna\r\n"
    )
    vb = parse_visual_brief(content)
    assert vb is not None
    assert vb["topic"] == "airBaltic"
    assert vb["stat"] == "30 milj."


# ---------------------------------------------------------------------------
# Integration tests: store_context_note() → visual_brief_json persistence
# ---------------------------------------------------------------------------

import json
import sqlite3
from unittest.mock import patch
import pytest


@pytest.fixture
def fresh_db(tmp_path):
    """Isolated DB for integration tests — avoids polluting real data/atmina.db."""
    from src.db import init_db
    db_path = str(tmp_path / "test_atmina.db")
    init_db(db_path)
    return db_path


_PADDING = (
    "Saeima šodien pieņēma lēmumu par valsts atbalstu airBaltic. "
    "Diskusijas ilga vairākas stundas, deputāti no dažādām frakcijām pauda atšķirīgus viedokļus. "
    "Koalīcijas pārstāvji uzsvēra stratēģisko nozīmi, savukārt opozīcija kritizēja procesa caurspīdīgumu. "
    "Finanšu ministrs norādīja, ka aizdevuma nosacījumi ir tirgus atbilstoši. "
    "Transports un loģistika ir galvenā ekonomiskā nozare, kas ietekmē valsts konkurētspēju. "
) * 20  # repeat to meet the 4000-char minimum


def test_store_context_note_auto_extracts_visual_brief(fresh_db):
    """daily_brief content with Vizualais brief block is auto-parsed and stored."""
    from src.tools import store_context_note
    content = (
        "# Dienas analīze — 2026-04-17\n\n"
        "## Galvenais\n\n"
        "Lielais notikums: 30 milj. aizdevums airBaltic.\n\n"
        + _PADDING
        + "\n\n## Aktīvākie politiķi\n\n"
        "| Politiķis | Partija |\n|---|---|\n| Siliņa | JV |\n\n"
        "## Galvenās tēmas\n\n"
        "### airBaltic\n\nSaturs\n\n"
        "## Koalīcija vs Opozīcija\n\nSaturs\n\n"
        "## Vizuālais brief\n\n"
        "- **Tēma:** airBaltic\n"
        "- **Galvenā tēze:** Saeima lemj par 30 milj. aizdevumu\n"
        "- **Skaitlis:** 30 milj.\n"
        "- **Metaforas hint:** lidmašīna\n"
    )
    with patch("src.tools.get_db", return_value=sqlite3.connect(fresh_db)):
        result = store_context_note(
            note_type="daily_brief",
            content=content,
            topic="dienas analīze 2026-04-17",
            source="atmina.lv",
        )
    assert "note_id" in result  # success response contains note_id

    # Verify visual_brief_json stored correctly
    db = sqlite3.connect(fresh_db)
    row = db.execute(
        "SELECT visual_brief_json FROM context_notes WHERE note_type='daily_brief'"
    ).fetchone()
    assert row is not None
    assert row[0] is not None
    vb = json.loads(row[0])
    assert vb["topic"] == "airBaltic"
    assert vb["stat"] == "30 milj."
    assert vb["headline"].startswith("Saeima lemj")


def test_store_context_note_without_visual_block_stores_null(fresh_db):
    """daily_brief without visual block still saves, visual_brief_json is NULL."""
    from src.tools import store_context_note
    content = (
        "# Dienas analīze — 2026-04-17\n\n"
        "## Galvenais\n\n"
        + _PADDING
        + "\n\n## Aktīvākie politiķi\n\n| Politiķis | Partija |\n|---|---|\n| X | Y |\n\n"
        "## Galvenās tēmas\n\n### X\n\nSaturs\n\n"
        "## Koalīcija vs Opozīcija\n\nSaturs\n"
    )
    with patch("src.tools.get_db", return_value=sqlite3.connect(fresh_db)):
        store_context_note(
            note_type="daily_brief",
            content=content,
            topic="x",
            source="s",
        )
    db = sqlite3.connect(fresh_db)
    row = db.execute(
        "SELECT visual_brief_json FROM context_notes WHERE note_type='daily_brief'"
    ).fetchone()
    assert row is not None
    assert row[0] is None  # no visual_brief block → NULL


def test_store_context_note_explicit_visual_brief_overrides_parsing(fresh_db):
    """If caller passes visual_brief explicitly, auto-parse is skipped."""
    from src.tools import store_context_note
    content = (
        "# Dienas analīze — 2026-04-17\n\n"
        "## Galvenais\n\n"
        + _PADDING
        + "\n\n## Aktīvākie politiķi\n\n| Politiķis | Partija |\n|---|---|\n| X | Y |\n\n"
        "## Galvenās tēmas\n\n### X\n\nSaturs\n\n"
        "## Koalīcija vs Opozīcija\n\nSaturs\n\n"
        "## Vizuālais brief\n\n"
        "- **Tēma:** ignored-topic-from-markdown\n"
        "- **Galvenā tēze:** ignored\n"
        "- **Skaitlis:** -\n"
        "- **Metaforas hint:** x\n"
    )
    explicit = {"topic": "airBaltic", "headline": "explicit", "stat": None, "metaphor_hint": ""}
    with patch("src.tools.get_db", return_value=sqlite3.connect(fresh_db)):
        store_context_note(
            note_type="daily_brief",
            content=content,
            topic="x",
            source="s",
            visual_brief=explicit,
        )
    db = sqlite3.connect(fresh_db)
    row = db.execute(
        "SELECT visual_brief_json FROM context_notes WHERE note_type='daily_brief'"
    ).fetchone()
    vb = json.loads(row[0])
    assert vb["topic"] == "airBaltic"  # caller's explicit dict won
    assert vb["headline"] == "explicit"
