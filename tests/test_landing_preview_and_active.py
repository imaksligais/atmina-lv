"""Landing-page text that silently lied (2026-09-28 batch).

1. Brief preview (landing «Jaunākais», blog.html card, analizes.html) stripped
   only ``**bold**``: weekly brief #653 put the literal heading «Nedēļas stāsts»
   and a raw ``([Braže X](https://x.com/…))`` link group onto the landing card.
2. «N aktīvi politiķi» counted every ``opponent_id`` with a position claim —
   journalists, neutral outlets and organizations included — while the about
   page's «N politiķi» already used ``relationship_type='tracked'`` (operator
   decision 2026-08-15, 194 → 167).
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta

import pytest

from src.db import get_db, init_db, today_lv
from src.render.blog import _brief_preview
from src.saeima.schema import init_saeima_tables

_WEEKLY_BODY = """## Nedēļas stāsts

Nedēļa sākās ar ES sankciju strīdu. Ministre Baiba Braže (JV) rakstīja, ka Latvija nevar piekrist svītrošanai ([Braže X](https://x.com/Braze_Baiba/status/1)). Valdība noteica **nacionālās** sankcijas ([delfi.lv](https://www.delfi.lv/a)), bet [LSM](https://lsm.lv/b) ziņoja par atturēšanos.

## Pretrunas

- nekas
"""


def test_weekly_preview_has_no_markdown_links_or_heading():
    preview = _brief_preview(_WEEKLY_BODY)
    assert "](" not in preview
    assert "Nedēļas stāsts" not in preview
    assert "**" not in preview
    assert preview.startswith("Nedēļa sākās ar ES sankciju strīdu.")
    # Parenthesised source group is dropped entirely; a bare inline link keeps its label.
    assert "svītrošanai. Valdība noteica nacionālās sankcijas, bet LSM ziņoja" in preview


def test_daily_preview_still_reads_galvenais():
    body = "## Galvenais\n\nSaeima pieņēma **budžetu** ([saeima.lv](https://saeima.lv/x)).\n\n## Citi\n\nx"
    assert _brief_preview(body) == "Saeima pieņēma budžetu."


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    conn = get_db(path)
    ts = (today_lv() - timedelta(days=1)).strftime("%Y-%m-%d") + " 10:00:00"
    rows = [
        (1, "Deputāts", "tracked"),
        (2, "Žurnālists", "journalist"),
        (3, "Organizācija", "organization"),
        (4, "Neitrāls", "neutral"),
        (5, "Neaktīvs", "inactive"),
    ]
    for pid, name, rel in rows:
        conn.execute(
            "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (?, ?, ?)",
            (pid, name, rel),
        )
        conn.execute(
            "INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at) "
            "VALUES (?, ?, 't', 'c', ?, 'web', ?)",
            (pid, f"https://example.lv/{pid}", f"h{pid}", ts),
        )
        conn.execute(
            "INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, "
            "created_at, claim_type) VALUES (?, ?, 'Budžets un finanses', 's', ?, ?, ?, 'position')",
            (pid, pid, f"https://example.lv/{pid}", ts, ts),
        )
    # Two days ago only the journalist spoke — a tracked-only series is 0 there.
    # (Needed: the sparkline normalizes to its max, so a flat 5-vs-1 day alone
    # would draw the identical SVG and the test could not fail.)
    ts2 = (today_lv() - timedelta(days=2)).strftime("%Y-%m-%d") + " 10:00:00"
    conn.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, "
        "created_at, claim_type) VALUES (2, 2, 'Vēlēšanas', 's', 'https://example.lv/2b', ?, ?, 'position')",
        (ts2, ts2),
    )
    conn.commit()
    yield conn
    conn.close()
    try:
        os.remove(path)
    except OSError:
        pass


def test_active_politicians_counts_only_tracked(db):
    from src.render.dashboard import _fetch_stats

    assert _fetch_stats(db)["politicians_active"] == 1


def test_active_sparkline_counts_only_tracked(db):
    from src.render.dashboard import _fetch_hero_v2_data, _sparkline_svg

    expected = [0] * 28
    expected[-2] = 1  # yesterday: one tracked politician, four non-politicians
    # expected[-3] stays 0: only the journalist spoke that day
    assert _fetch_hero_v2_data(db)["spark_active"] == _sparkline_svg(expected, color="#90A4AE")
