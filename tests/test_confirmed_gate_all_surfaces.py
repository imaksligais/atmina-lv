"""`confirmed=0` contradictions are unpublished on EVERY public surface.

Escalation rule 3 (CLAUDE.md) stores @devils-advocate survivors and
operator-withdrawn rows with ``confirmed=0`` "for operator review", and the
CHANGELOG (arhīvs, 2026-07) claims "visas virsmas filtrē
``COALESCE(confirmed,1)=1``". Until 2026-09-20 that was true for the
pretrunas page, topics, the search index and the briefs — and false for
eight other readers, so four unconfirmed candidates (#40, #47, #48, #49)
were live on politician profiles as "≈ Pozīcijas maiņa" cards and the
homepage "Šonedēļ" strip showed "1 jauna pretruna" for a candidate the
operator had not approved.

One fixture, one unconfirmed row, one assertion per surface. A legacy
``confirmed IS NULL`` row is included because the public contract is
``COALESCE(confirmed, 1) = 1`` — NULL counts as published, 0 does not.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta

import pytest

from src.db import get_db, init_db, today_lv
from src.saeima.schema import init_saeima_bills, init_saeima_tables


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    today = today_lv()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    db.executescript(f"""
        INSERT INTO parties (id, name, short_name) VALUES (1, 'Jaunā Vienotība', 'JV');
        INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
            VALUES (1, 'Testa Politiķis', 'Jaunā Vienotība', 'Saeimas deputāts', 'tracked');
        INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at)
            VALUES (1, 'https://example.lv/a', 'A', 'teksts', 'h1', 'web', '{yesterday} 10:00:00');
        INSERT INTO claims (id, opponent_id, document_id, topic, stance, source_url, stated_at, claim_type)
            VALUES (1, 1, 1, 'Budžets un finanses', 'Atbalsta deficītu', 'https://example.lv/a', '{yesterday} 10:00:00', 'position'),
                   (2, 1, 1, 'Budžets un finanses', 'Iebilst deficītam', 'https://example.lv/a', '{yesterday} 11:00:00', 'position');
        -- #1 published, #2 UNCONFIRMED candidate (today), #3 legacy NULL = published
        INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, salience, reviewed, confirmed, detected_at)
            VALUES (1, 1, 1, 2, 'Budžets un finanses', 'Apstiprināta pretruna', 'reversal', 0.8, 1, 1, '{yesterday} 12:00:00'),
                   (2, 1, 1, 2, 'Budžets un finanses', 'Neapstiprināta kandidāte', 'minor_shift', 0.2, 1, 0, '{today} 09:00:00'),
                   (3, 1, 1, 2, 'Budžets un finanses', 'Mantota rinda bez confirmed', 'reversal', 0.5, 1, NULL, '{yesterday} 13:00:00');
    """)
    db.commit()
    db.close()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def db(db_path):
    conn = get_db(db_path)
    yield conn
    conn.close()


def test_homepage_total_excludes_unconfirmed(db):
    from src.render.dashboard import _fetch_stats

    assert _fetch_stats(db)["contradictions"] == 2


def test_homepage_7day_strip_excludes_unconfirmed(db):
    """The reported symptom: '1 jauna pretruna' for candidate #49 (2026-09-20)."""
    from src.render.dashboard import _fetch_hero_v2_data

    assert _fetch_hero_v2_data(db)["contradictions_7d"] == 2


def test_politician_profile_list_excludes_unconfirmed(db):
    """The count (line ~99) was gated since 2026-06-10; the LIST never was."""
    from src.render.politicians import _fetch_politician_detail

    detail = _fetch_politician_detail(db, 1)
    assert sorted(c["id"] for c in detail["contradictions"]) == [1, 3]


def test_links_graph_node_count_excludes_unconfirmed(db):
    from src.render.links import _fetch_graph_data

    nodes = {n["id"]: n for n in _fetch_graph_data(db)["nodes"]}
    assert nodes[1]["contradictions"] == 2


def test_links_detail_panel_excludes_unconfirmed(db, tmp_path, monkeypatch):
    import src.render.links as links_mod

    captured: dict = {}

    def _capture(env, template, out_path, ctx):
        captured.update(ctx)

    monkeypatch.setattr(links_mod, "_render_page", _capture)
    (tmp_path / "data").mkdir()
    links_mod.render_links(env=None, db=db, atmina_dir=tmp_path, tensions=[])
    contras = captured["saites_data"]["contrasByPid"]["1"]
    assert sorted(c["summary"] for c in contras) == [
        "Apstiprināta pretruna", "Mantota rinda bez confirmed",
    ]


def test_parties_page_count_excludes_unconfirmed(db):
    from src.render.parties import _fetch_parties_page

    assert _fetch_parties_page(db)[0]["contradictions_count"] == 2


def test_party_detail_member_count_excludes_unconfirmed(db):
    from src.render.parties import _fetch_party_detail

    party = dict(db.execute("SELECT * FROM parties WHERE id = 1").fetchone())
    members = _fetch_party_detail(db, party)["members"]
    assert members[0]["contradictions_count"] == 2


def test_personas_count_excludes_unconfirmed(db):
    from src.render.personas import _fetch_personas

    assert _fetch_personas(db)[0]["contradictions_count"] == 2


def test_brief_footer_histogram_excludes_unconfirmed(db):
    """The brief footer must agree with the brief body (briefs.py already gates)."""
    from src.render.blog import _compute_brief_footers

    today = today_lv().strftime("%Y-%m-%d")
    yesterday = (today_lv() - timedelta(days=1)).strftime("%Y-%m-%d")
    footers = _compute_brief_footers(db)
    assert footers[yesterday]["contradictions"] == 2
    assert footers.get(today, {}).get("contradictions", 0) == 0
