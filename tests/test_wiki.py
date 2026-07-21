import sqlite3


def _create_test_db(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, role TEXT, relationship_type TEXT DEFAULT 'neutral', name_forms TEXT DEFAULT '[]')")
    db.execute("CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER, topic TEXT, stance TEXT, confidence REAL, salience REAL, source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position', created_at TEXT)")
    db.execute("CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_old_id INTEGER, claim_new_id INTEGER, topic TEXT, summary TEXT, severity TEXT, confirmed BOOLEAN DEFAULT 0, reviewed BOOLEAN DEFAULT 0, detected_at TEXT)")
    db.execute("CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY, vote_id INTEGER, deputy_name TEXT, faction TEXT, vote TEXT, politician_id INTEGER)")
    db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT, source_url TEXT, source_domain TEXT, platform TEXT DEFAULT 'web', scraped_at TEXT, reviewed_at TEXT)")
    db.execute("""CREATE TABLE document_politicians (
        document_id INTEGER NOT NULL,
        politician_id INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'subject',
        PRIMARY KEY (document_id, politician_id, role)
    )""")
    # political_tensions is queried by _gather_person_signal, which wiki_sync
    # now invokes per politician via _render_person_synthesis.
    db.execute("""CREATE TABLE political_tensions (
        id INTEGER PRIMARY KEY,
        source_pid INTEGER,
        target_pid INTEGER,
        topic TEXT,
        description TEXT,
        tension_type TEXT DEFAULT 'spriedze',
        source_url TEXT,
        created_at TEXT
    )""")
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES (1, 'Testa Politiķe', 'TP', 'Deputāte')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES (2, 'Otrs Tests', 'JV', 'Deputāts')")
    db.execute("INSERT INTO claims (opponent_id, topic, stance, confidence, salience, stated_at, created_at) VALUES (1, 'Budžets un finanses', 'Atbalsta nodokļu samazināšanu', 0.85, 0.7, '2026-04-01', datetime('now'))")
    db.commit()
    return db


# wiki_sync writes both per-person stubs AND a sub-index (persons/personas.md,
# a Latvian-named index file — see src.wiki_lint._INDEX_NAMES). Filtering only
# `stem != "index"` leaves personas.md in, and `glob()` order is unsorted and
# platform-dependent — so person_files[0] picked a real stub on Windows but the
# index on Linux/CI. Exclude the sub-index and sort for a deterministic pick.
def _person_stub_files(wiki_dir):
    return sorted(
        p
        for p in (wiki_dir / "persons").glob("*.md")
        if p.stem not in ("index", "personas")
    )


def test_wiki_sync_creates_index(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    result = wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    assert (wiki_dir / "index.md").exists()
    assert result["persons"] >= 1


def test_wiki_sync_creates_person_stub(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    person_files = _person_stub_files(wiki_dir)
    assert len(person_files) >= 1
    content = person_files[0].read_text(encoding="utf-8")
    assert "---" in content
    assert "name:" in content
    assert "party:" in content
    # Pēc 2026-04-25 sanācijas: position vs vote counts ir atsevišķi.
    # `claims:` lauks tika dropts, jo apvienoja position+saeima_vote un radīja parpratumu.
    assert "positions:" in content
    assert "votes:" in content


def test_wiki_sync_preserves_manual_content(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    person_file = _person_stub_files(wiki_dir)[0]
    original = person_file.read_text(encoding="utf-8")
    person_file.write_text(original + "\n\n## Mans profils\n\nŠī ir manuāla piezīme.\n", encoding="utf-8")
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    updated = person_file.read_text(encoding="utf-8")
    assert "Mans profils" in updated
    assert "manuāla piezīme" in updated


def test_index_groups_by_party(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    index = (wiki_dir / "index.md").read_text(encoding="utf-8")
    # Should link to sub-indexes (Latvian-named files for graph readability —
    # see project_wiki_index_naming memory).
    assert "[[persons/personas|" in index
    assert "[[parties/partijas|" in index
    # Sub-indexes should contain party names
    persons_index = (wiki_dir / "persons" / "personas.md").read_text(encoding="utf-8")
    assert "JV" in persons_index or "TP" in persons_index
    # Should NOT contain relationship_type groupings
    assert "Opozīcija" not in index


def test_index_party_count_excludes_null_party(tmp_path):
    """Index 'Struktūra' party count must exclude active entities with no party
    (journalists, news outlets, organizations) and match the partijas.md
    headline.

    Regression: _build_index grouped by tp.party WITHOUT the
    `AND tp.party IS NOT NULL` filter that its sibling _build_parties_index
    applies, so a NULL-party GROUP BY bucket leaked in and inflated
    len(party_rows) by one (prod showed 16 in index.md vs 15 in partijas.md).
    """
    import re
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    db = _create_test_db(db_path)  # politicians 1 (TP) + 2 (JV), both active
    # An active tracked entity with no party — e.g. a relayed news outlet.
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, role, relationship_type) "
        "VALUES (3, 'LTV Ziņas', NULL, 'Medijs', 'journalist')"
    )
    db.commit()
    db.close()

    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))

    index = (wiki_dir / "index.md").read_text(encoding="utf-8")
    parties_index = (wiki_dir / "parties" / "partijas.md").read_text(encoding="utf-8")

    index_count = int(re.search(r"Partijas\]\] — (\d+) partijas", index).group(1))
    parties_count = int(re.search(r"\*\*(\d+)\*\* partijas", parties_index).group(1))

    # Only TP and JV are real parties; the NULL-party outlet must not count.
    assert parties_count == 2
    assert index_count == 2, f"NULL-party bucket leaked: index says {index_count} partijas"
    assert index_count == parties_count


from pathlib import Path

from src.wiki import _update_page_with_sync_block


def test_sync_block_inserted_into_new_page(tmp_path):
    """New page gets frontmatter + sync block, nothing else."""
    page = tmp_path / "test.md"
    fm = {"name": "Test", "claims": 3}
    block = "- **Top tēmas:** [[A]] (50%), [[B]] (30%)\n"

    _update_page_with_sync_block(page, fm, block)

    text = page.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "<!-- SYNC-AUTO -->" in text
    assert "<!-- /SYNC-AUTO -->" in text
    assert "**Top tēmas:**" in text


def test_sync_block_empty_no_markers_written(tmp_path):
    """Empty block means no markers in output — body stays clean."""
    page = tmp_path / "test.md"
    fm = {"name": "Test", "claims": 0}

    _update_page_with_sync_block(page, fm, "")

    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" not in text
    assert "<!-- /SYNC-AUTO -->" not in text


def test_sync_block_replaces_existing(tmp_path):
    """Existing sync block is replaced with new content; manual text preserved."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\n"
        "Manuālais konteksts paliek.\n\n"
        "<!-- SYNC-AUTO -->\n"
        "- **vecs:** dati\n"
        "<!-- /SYNC-AUTO -->\n\n"
        "Vairāk manuāla teksta.\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(
        page,
        {"name": "Test"},
        "- **Top tēmas:** [[A]] (50%)\n",
    )

    text = page.read_text(encoding="utf-8")
    assert "Manuālais konteksts paliek." in text
    assert "Vairāk manuāla teksta." in text
    assert "vecs:" not in text
    assert "**Top tēmas:**" in text
    assert text.count("<!-- SYNC-AUTO -->") == 1
    assert text.count("<!-- /SYNC-AUTO -->") == 1


def test_sync_block_removed_when_empty(tmp_path):
    """If block becomes empty, existing markers + content are removed; manual preserved."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\n"
        "Manuālais konteksts.\n\n"
        "<!-- SYNC-AUTO -->\n"
        "- **vecs:** dati\n"
        "<!-- /SYNC-AUTO -->\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(page, {"name": "Test"}, "")

    text = page.read_text(encoding="utf-8")
    assert "Manuālais konteksts." in text
    assert "<!-- SYNC-AUTO -->" not in text
    assert "vecs:" not in text


def test_sync_block_appended_to_existing_body_without_markers(tmp_path):
    """Existing page with manual body but no markers: block is appended after body."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\nManuāls saturs.\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(
        page,
        {"name": "Test"},
        "- **Top tēmas:** [[A]] (50%)\n",
    )

    text = page.read_text(encoding="utf-8")
    manual_idx = text.index("Manuāls saturs.")
    marker_idx = text.index("<!-- SYNC-AUTO -->")
    assert manual_idx < marker_idx
    assert "**Top tēmas:**" in text


import sqlite3

import pytest

import src.db as db_mod
import src.wiki as wiki_mod
from src.wiki import _gather_person_signal


@pytest.fixture
def wiki_tmp_db(tmp_path, monkeypatch):
    """Fresh DB with schema, used for wiki signal tests."""
    db_path = str(tmp_path / "wiki_test.db")
    db_mod.init_db(db_path)
    # init_db does not create Saeima tables (they live in src/saeima.py).
    # wiki_sync() queries saeima_individual_votes, so we must create them.
    from src.saeima import init_saeima_tables
    init_saeima_tables(db_path)

    orig_get_db = db_mod.get_db

    def _redirected(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected)
    monkeypatch.setattr(wiki_mod, "get_db", _redirected, raising=False)

    conn = orig_get_db(db_path)
    yield conn
    conn.close()


def test_signal_empty_for_politician_with_no_data(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'Empty', '[]')"
    )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["top_topics"] == []
    assert signal["activity_30d"] is None
    assert signal["tensions"] == []
    assert signal["contradictions"] is None


def test_signal_top_topics_requires_3_topics_with_2_claims_each(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    for topic in ("Budžets", "Imigrācija"):
        for i in range(3):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, '2026-04-15', 'position')""",
                (topic, f"stance-{i}", f"https://x.com/p/status/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["top_topics"] == []


def test_signal_top_topics_populated_when_3_topics_have_2_claims(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    counts = {"Budžets": 5, "Imigrācija": 3, "Aizsardzība": 2, "Vēlēšanas": 2}
    for topic, n in counts.items():
        for i in range(n):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, '2026-04-15', 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/status/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert len(signal["top_topics"]) == 3
    assert signal["top_topics"][0]["topic"] == "Budžets"
    assert signal["top_topics"][0]["count"] == 5
    assert signal["top_topics"][0]["pct"] == 42


def test_signal_tensions_returns_top_3_by_count(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'A', '[]')"
    )
    for tpid, tname in ((10, "B"), (20, "C"), (30, "D"), (40, "E")):
        wiki_tmp_db.execute(
            "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?, ?, '[]')",
            (tpid, tname),
        )
    counts = {10: 3, 20: 2, 30: 1, 40: 1}
    for tpid, n in counts.items():
        for i in range(n):
            wiki_tmp_db.execute(
                """INSERT INTO political_tensions
                   (source_pid, target_pid, topic, description, tension_type, source_url)
                   VALUES (1, ?, 'T', 'd', 'uzbrukums', ?)""",
                (tpid, f"https://x.com/a/status/{tpid}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert len(signal["tensions"]) == 3
    assert signal["tensions"][0]["target_pid"] == 10
    assert signal["tensions"][0]["target_name"] == "B"
    assert signal["tensions"][0]["count"] == 3


def test_signal_contradictions_only_confirmed(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    for i in (1, 2, 3, 4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (id, opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (?, 1, 'T', ?, 0.8, 0.5, ?, '2026-04-15', ?)""",
            (i, f"s-{i}", f"https://x.com/p/{i}", "position" if i < 3 else "saeima_vote"),
        )
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 1, 2, 'Budžets', 'shift', 'reversal', 1, 1, '2026-04-10')"""
    )
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 1, 3, 'Aizsardzība', 'vote-gap', 'direct_contradiction', 0, 0, '2026-04-11')"""
    )
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 2, 4, 'Budžets', 'vote-gap', 'direct_contradiction', 1, 1, '2026-04-12')"""
    )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["contradictions"] is not None
    assert signal["contradictions"]["total"] == 2
    assert signal["contradictions"]["rhetoric_action"] == 1
    assert signal["contradictions"]["position_shift"] == 1
    assert signal["contradictions"]["last_topic"] == "Budžets"
    assert signal["contradictions"]["last_date"].startswith("2026-04-12")


def test_signal_activity_30d_with_and_without_baseline(wiki_tmp_db):
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    for i in range(4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (1, 'T', ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
            (f"r{i}", f"https://x.com/p/r{i}"),
        )
    for i in range(4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (1, 'T', ?, 0.8, 0.5, ?, date('now', '-45 days'), 'position')""",
            (f"o{i}", f"https://x.com/p/o{i}"),
        )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["activity_30d"] is not None
    assert signal["activity_30d"]["count"] == 4
    assert signal["activity_30d"]["ratio"] is None


from src.wiki import _render_person_synthesis, WikiSynthesisOverflow


def test_render_empty_signal_returns_empty_string():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    assert _render_person_synthesis(signal) == ""


def test_render_only_top_topics():
    signal = {
        "top_topics": [
            {"topic": "Budžets", "count": 5, "pct": 42},
            {"topic": "Imigrācija", "count": 3, "pct": 25},
            {"topic": "Aizsardzība", "count": 2, "pct": 17},
        ],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**Top tēmas:**" in out
    assert "[[Budžets]]" in out
    assert "(42%)" in out
    assert out.count("- **") == 1


def test_render_activity_with_ratio():
    signal = {
        "top_topics": [],
        "activity_30d": {"count": 8, "ratio": 1.3},
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**30d:** 8 claims, 1.3× bāzes līnija" in out


def test_render_activity_without_ratio():
    signal = {
        "top_topics": [],
        "activity_30d": {"count": 3, "ratio": None},
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**30d:** 3 claims" in out
    assert "bāzes līnija" not in out


def test_render_tensions_format():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [
            {"target_pid": 10, "target_name": "Andris Kulbergs", "count": 3, "tension_type": "uzbrukums"},
            {"target_pid": 20, "target_name": "Edmunds Cepurītis", "count": 2, "tension_type": "spriedze"},
        ],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**Spriedzes:**" in out
    assert "[[Andris Kulbergs]] (3 uzbrukumi)" in out
    assert "[[Edmunds Cepurītis]] (2 spriedzes)" in out


def test_render_contradictions_with_both_types():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": {
            "total": 2,
            "rhetoric_action": 1,
            "position_shift": 1,
            "last_topic": "airBaltic",
            "last_date": "2026-04-14 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert "**Pretrunas:**" in out
    assert "2 apstiprinātas" in out
    assert "1 retorika↔balsojums" in out
    assert "1 pozīciju maiņa" in out
    assert "[[airBaltic]]" in out
    assert "2026-04-14" in out


def test_render_contradictions_only_position_shift():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": {
            "total": 1,
            "rhetoric_action": 0,
            "position_shift": 1,
            "last_topic": "Budžets",
            "last_date": "2026-04-10 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert "1 apstiprināta" in out
    assert "retorika" not in out
    assert "pozīciju maiņa" not in out


def test_render_full_signal_all_four_bullets():
    signal = {
        "top_topics": [
            {"topic": "airBaltic", "count": 18, "pct": 23},
            {"topic": "Koalīcija", "count": 12, "pct": 16},
            {"topic": "Degviela", "count": 9, "pct": 12},
        ],
        "activity_30d": {"count": 8, "ratio": 1.3},
        "tensions": [
            {"target_pid": 10, "target_name": "A. Kulbergs", "count": 3, "tension_type": "uzbrukums"},
        ],
        "contradictions": {
            "total": 2,
            "rhetoric_action": 1,
            "position_shift": 1,
            "last_topic": "airBaltic",
            "last_date": "2026-04-14 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert out.count("- **") == 4
    assert "Top tēmas" in out
    assert "30d" in out
    assert "Spriedzes" in out
    assert "Pretrunas" in out


def test_render_overflow_raises():
    huge_topic = "X" * 2000
    signal = {
        "top_topics": [
            {"topic": huge_topic, "count": 5, "pct": 50},
            {"topic": "B", "count": 3, "pct": 30},
            {"topic": "C", "count": 2, "pct": 20},
        ],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    with pytest.raises(WikiSynthesisOverflow):
        _render_person_synthesis(signal)


def test_wiki_sync_writes_synthesis_block_when_signal_present(wiki_tmp_db, tmp_path, monkeypatch):
    """End-to-end: politician with signal gets sync block in their page."""
    from src.wiki import wiki_sync

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (1, 'Testa Politis', '[]', 'tracked')"
    )
    topics = {"Budžets": 5, "Imigrācija": 3, "Aizsardzība": 2}
    for topic, n in topics.items():
        for i in range(n):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir=str(wiki_dir))

    page = wiki_dir / "persons" / "testa-politis.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" in text
    assert "**Top tēmas:**" in text
    assert "[[Budžets]]" in text


def test_wiki_sync_empty_body_when_no_signal(wiki_tmp_db, tmp_path, monkeypatch):
    """Politician with no claims → page has frontmatter only, no markers."""
    from src.wiki import wiki_sync

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (2, 'Silent Politis', '[]', 'tracked')"
    )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir=str(wiki_dir))

    page = wiki_dir / "persons" / "silent-politis.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" not in text


def test_wiki_sync_preserves_manual_content_when_updating(wiki_tmp_db, tmp_path, monkeypatch):
    """Existing page with manual notes keeps them after sync."""
    from src.wiki import wiki_sync

    wiki_dir = tmp_path / "wiki"
    persons_dir = wiki_dir / "persons"
    persons_dir.mkdir(parents=True)
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    page = persons_dir / "testa-politis.md"
    page.write_text(
        "---\nname: Testa Politis\n---\n\n"
        "**Manuāls konteksts:** bijušais teātra režisors.\n",
        encoding="utf-8",
    )

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (1, 'Testa Politis', '[]', 'tracked')"
    )
    for topic in ("A", "B", "C"):
        for i in range(2):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir=str(wiki_dir))

    text = page.read_text(encoding="utf-8")
    assert "bijušais teātra režisors" in text
    assert "<!-- SYNC-AUTO -->" in text
