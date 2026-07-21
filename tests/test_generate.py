"""Tests for src/generate.py — pure utility functions."""

import sqlite3
import pytest

from src.generate import (
    _slugify,
    _initials_from_name,
    _delta_days,
    _domain_from_url,
    _parse_frontmatter,
    _enrich_faction_breakdown,
    _photo_data_uri,
    ASSETS_DIR,
    SEVERITY_LV,
    ELECTION_DATE,
)


class TestSlugify:
    def test_basic_name(self):
        assert _slugify("Evika Siliņa") == "evika-silina"

    def test_latvian_chars(self):
        assert _slugify("Āris Šķērslis") == "aris-skerslis"

    def test_all_latvian_diacritics(self):
        slug = _slugify("āčēģīķļņšūž")
        assert slug == "acegiklnsuz"

    def test_removes_special_chars(self):
        assert _slugify("Test (something)") == "test-something"

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_double_spaces(self):
        assert _slugify("Jānis  Bērziņš") == "janis--berzins"

    def test_uppercase_latvian(self):
        assert _slugify("ĀČĒĢĪĶĻŅŠŪŽ") == "acegiklnsuz"


class TestInitialsFromName:
    def test_two_word_name(self):
        assert _initials_from_name("Evika Siliņa") == "ES"

    def test_three_word_name_uses_first_two(self):
        assert _initials_from_name("Krišjānis Feldmans Juniors") == "KF"

    def test_single_word(self):
        assert _initials_from_name("Madonna") == "M"

    def test_none(self):
        assert _initials_from_name(None) == "?"

    def test_empty_string(self):
        assert _initials_from_name("") == "?"

    def test_whitespace_only(self):
        assert _initials_from_name("   ") == "?"

    def test_latvian_diacritics_preserved(self):
        assert _initials_from_name("Āris Šķērslis") == "ĀŠ"


class TestDeltaDays:
    def test_basic_diff(self):
        assert _delta_days("2026-01-01", "2026-01-11") == 10

    def test_same_day(self):
        assert _delta_days("2026-03-05", "2026-03-05") == 0

    def test_order_independent(self):
        # Reversed inputs still return positive diff (abs)
        assert _delta_days("2026-04-10", "2026-01-01") == 99

    def test_accepts_iso_with_time_suffix(self):
        assert _delta_days("2026-01-01T12:30:00", "2026-01-11T09:15:00") == 10

    def test_none_old(self):
        assert _delta_days(None, "2026-01-11") is None

    def test_none_new(self):
        assert _delta_days("2026-01-01", None) is None

    def test_both_none(self):
        assert _delta_days(None, None) is None

    def test_malformed_returns_none(self):
        assert _delta_days("not-a-date", "2026-01-11") is None


class TestDomainFromUrl:
    def test_basic_https(self):
        assert _domain_from_url("https://www.lsm.lv/raksts/foo") == "lsm.lv"

    def test_strips_www(self):
        assert _domain_from_url("https://www.delfi.lv/article/1") == "delfi.lv"

    def test_no_www(self):
        assert _domain_from_url("https://tvnet.lv/x") == "tvnet.lv"

    def test_subdomain_preserved(self):
        assert _domain_from_url("https://rus.delfi.lv/abc") == "rus.delfi.lv"

    def test_none(self):
        assert _domain_from_url(None) is None

    def test_empty(self):
        assert _domain_from_url("") is None

    def test_malformed(self):
        # urlparse is lenient; non-URL garbage → empty netloc → None guard
        assert _domain_from_url("not a url at all") is None


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = """---
title: Test
date: 2026-04-07
---
Body content here."""
        fm, body = _parse_frontmatter(text)
        assert fm["title"] == "Test"
        assert "Body content" in body

    def test_no_frontmatter(self):
        text = "Just plain markdown content."
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self):
        text = """---
---
Body."""
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert "Body" in body

    def test_complex_frontmatter(self):
        text = """---
title: Deklarāciju analīze
tags:
  - finanses
  - KNAB
url: /analizes/deklaracijas-2026
---
Content."""
        fm, body = _parse_frontmatter(text)
        assert fm["title"] == "Deklarāciju analīze"
        assert "KNAB" in fm["tags"]
        assert "Content" in body

    def test_malformed_yaml(self):
        text = """---
title: [broken yaml
  invalid: }}}
---
Body."""
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert "Body" in body

    def test_missing_closing_fence(self):
        text = """---
title: No closing
Body content."""
        fm, body = _parse_frontmatter(text)
        assert fm == {}


class TestConstants:
    def test_severity_translations(self):
        assert "direct_contradiction" in SEVERITY_LV
        assert "reversal" in SEVERITY_LV
        assert "minor_shift" in SEVERITY_LV
        # Values should be Latvian
        assert all(isinstance(v, str) for v in SEVERITY_LV.values())

    def test_election_date_future(self):
        from datetime import date
        assert ELECTION_DATE > date(2026, 1, 1)


class TestEnrichFactionBreakdown:
    """Faction-level aggregation used in the balsojumi card. Pure function,
    so we test it directly without DB fixtures."""

    COALITION = {
        "JV": "coalition",
        "ZZS": "coalition",
        "NA": "coalition",
        "PRO": "coalition",
        "AS": "opposition",
        "LPV": "opposition",
        "K": "other",
    }

    def test_unanimous_faction_is_discipline_1(self):
        rows = [{"faction": "JV", "par": 24, "pret": 0, "atturas": 0, "nebalso": 0}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["total"] == 24
        assert out[0]["majority_vote"] == "Par"
        assert out[0]["discipline"] == 1.0

    def test_split_faction_discipline_below_1(self):
        rows = [{"faction": "ZZS", "par": 13, "pret": 0, "atturas": 0, "nebalso": 3}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["majority_vote"] == "Par"
        assert abs(out[0]["discipline"] - 13 / 16) < 1e-6

    def test_majority_pret(self):
        rows = [{"faction": "LPV", "par": 0, "pret": 6, "atturas": 0, "nebalso": 1}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["majority_vote"] == "Pret"
        assert out[0]["total"] == 7

    def test_majority_nebalsoja_when_abstaining_block(self):
        """LPV nebalsoja protest — 0 par, 0 pret, 0 atturas, 6 nebalso.
        Seen in vote id=76 (LPV NA gun-permits for dual citizens)."""
        rows = [{"faction": "LPV", "par": 0, "pret": 0, "atturas": 0, "nebalso": 6}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["majority_vote"] == "Nebalsoja"
        assert out[0]["discipline"] == 1.0

    def test_empty_faction_returns_none_majority(self):
        rows = [{"faction": "K", "par": 0, "pret": 0, "atturas": 0, "nebalso": 0}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["total"] == 0
        assert out[0]["majority_vote"] is None
        assert out[0]["discipline"] == 0.0

    def test_coalition_sorted_before_opposition(self):
        """Coalition factions (JV, ZZS, NA, PRO) must render before
        opposition (AS, LPV) for a consistent visual ordering.
        """
        rows = [
            {"faction": "AS",  "par": 10, "pret": 0, "atturas": 0, "nebalso": 0},
            {"faction": "JV",  "par": 24, "pret": 0, "atturas": 0, "nebalso": 0},
            {"faction": "LPV", "par": 0,  "pret": 6, "atturas": 0, "nebalso": 0},
            {"faction": "ZZS", "par": 16, "pret": 0, "atturas": 0, "nebalso": 0},
            {"faction": "NA",  "par": 11, "pret": 0, "atturas": 0, "nebalso": 0},
            {"faction": "PRO", "par": 8,  "pret": 0, "atturas": 0, "nebalso": 0},
        ]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        ordered = [r["faction"] for r in out]
        # Coalition sorted by size desc, opposition sorted by size desc
        assert ordered == ["JV", "ZZS", "NA", "PRO", "AS", "LPV"]

    def test_unknown_party_falls_into_other_bucket(self):
        rows = [
            {"faction": "JV",     "par": 24, "pret": 0, "atturas": 0, "nebalso": 0},
            {"faction": "Nav kart", "par": 5, "pret": 0, "atturas": 0, "nebalso": 0},
        ]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert [r["faction"] for r in out] == ["JV", "Nav kart"]
        assert out[1]["coalition_status"] == "other"

    def test_coalition_status_attached_from_map(self):
        rows = [{"faction": "JV", "par": 24, "pret": 0, "atturas": 0, "nebalso": 0}]
        out = _enrich_faction_breakdown(rows, self.COALITION)
        assert out[0]["coalition_status"] == "coalition"


# ---------------------------------------------------------------------------
# DB-backed tests for _fetch_x_data (V1 metrics block)
# ---------------------------------------------------------------------------
import tempfile
import os

from src.db import init_db, insert_document, get_db


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _fixture_x_db():
    """Create temp DB with a tracked politician + 3 tweets + 2 mentions."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Insert politician
    db.execute(
        "INSERT INTO tracked_politicians (name, party, relationship_type) "
        "VALUES (?, ?, ?)",
        ("Elīna Treija", "Nacionālā apvienība", "tracked"),
    )
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    # Three posts, two mentions
    for i in range(3):
        insert_document(
            content=f"Test tweet number {i} " * 10,
            source_id=None, platform="twitter",
            source_url=f"https://x.com/elina_treija/status/{1000+i}",
            politician_links=[(pid, "subject")],
            reply_count=10 + i, retweet_count=5, favorite_count=100 + i,
            db_path=path,
        )
    for i in range(2):
        insert_document(
            content=f"@elina_treija some reply number {i} " * 10,
            source_id=None, platform="x_mention",
            source_url=f"https://x.com/other/status/{2000+i}",
            politician_links=[(pid, "mention_target")],
            db_path=path,
        )
    return path, pid


class TestFetchXDataV1:
    def test_metrics_block_present(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        try:
            db = get_db(path)
            result = _fetch_x_data(db)
            assert "metrics" in result
            m = result["metrics"]
            assert m["posts_total"] == 3
            assert m["mentions_total"] == 2
            assert m["last_24h"] == 5  # all 5 docs just inserted
            db.close()
        finally:
            _safe_unlink(path)

    def test_top_mentioned_block_present(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        try:
            db = get_db(path)
            result = _fetch_x_data(db)
            assert "top_mentioned" in result
            assert len(result["top_mentioned"]) >= 1
            row = result["top_mentioned"][0]
            assert row["name"] == "Elīna Treija"
            assert row["count"] == 2  # two mention docs in fixture
            assert row["trend"] == "+2"  # no prev-week data → delta == count == 2
            assert "party_short" in row
            assert "party_color" in row
            assert "slug" in row
            db.close()
        finally:
            _safe_unlink(path)

    def test_trending_topics_block_present(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        # Add a claim with a topic against one of the tweets
        db = get_db(path)
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url) "
            "VALUES (?, ?, ?, ?)",
            (pid, "airBaltic", "Par airBaltic kapitāla palielinājumu",
             "https://x.com/elina_treija/status/1000"),
        )
        db.commit()
        try:
            result = _fetch_x_data(db)
            assert "trending_topics" in result
            assert len(result["trending_topics"]) >= 1
            t = result["trending_topics"][0]
            assert t["topic"] == "airBaltic"
            assert t["mentions"] == 1
            assert isinstance(t["party_colors"], list)
            assert len(t["party_colors"]) >= 1
            db.close()
        finally:
            _safe_unlink(path)

    def test_post_enrichment_fields(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        db = get_db(path)
        # Add a topic claim linked to the first tweet
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, salience) "
            "VALUES (?, ?, ?, ?, ?)",
            (pid, "airBaltic", "Positive",
             "https://x.com/elina_treija/status/1000", 0.9),
        )
        db.commit()
        try:
            result = _fetch_x_data(db)
            # Find the post we claimed about
            p = next(x for x in result["posts"] if x["source_url"].endswith("/1000"))
            assert p["topic"] == "airBaltic"
            assert p["party_color"] == "#22c55e"  # NA green per PARTY_COLORS
            assert p["reply_count"] == 10
            assert p["retweet_count"] == 5
            assert p["favorite_count"] == 100
            # Post without a claim has topic=None
            p2 = next(x for x in result["posts"] if x["source_url"].endswith("/1002"))
            assert p2["topic"] is None
            db.close()
        finally:
            _safe_unlink(path)

    def test_mention_enrichment_fields(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        db = get_db(path)
        try:
            result = _fetch_x_data(db)
            assert result["mentions"], "expected at least one mention"
            m = result["mentions"][0]
            assert "mentioned_by" in m
            # Our fixture content: "@elina_treija some reply number X ..."
            # There's no *other* @handle so mentioned_by should be None
            assert m["mentioned_by"] is None
            assert m["party_color"] == "#22c55e"
            db.close()
        finally:
            _safe_unlink(path)

    def test_combined_feed_sorted_newest_first(self):
        from src.generate import _fetch_x_data
        path, pid = _fixture_x_db()
        try:
            db = get_db(path)
            result = _fetch_x_data(db)
            assert "feed" in result
            feed = result["feed"]
            # Fixture: 3 posts + 2 mentions = 5 items
            assert len(feed) == 5
            # Every item has kind/persona/party
            for x in feed:
                assert x["kind"] in ("post", "mention")
                assert "persona" in x and x["persona"]
                assert "party" in x
            # Sorted newest-first by date
            dates = [x["date"] for x in feed]
            assert dates == sorted(dates, reverse=True)
            # Post kind preserves original fields (politician_name)
            post_items = [x for x in feed if x["kind"] == "post"]
            assert all("politician_name" in p for p in post_items)
            db.close()
        finally:
            _safe_unlink(path)

    def test_top_mentioned_excludes_non_tracked(self):
        """Journalists/influencers/neutral are audience accounts — excluded
        from brief leaderboards per CLAUDE.md convention."""
        from src.generate import _fetch_x_data
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        # Insert one tracked politician + one journalist
        db.execute(
            "INSERT INTO tracked_politicians (name, party, relationship_type) "
            "VALUES (?, ?, ?)",
            ("Tracked Person", "Jaunā Vienotība", "tracked"),
        )
        pid_tracked = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO tracked_politicians (name, party, relationship_type) "
            "VALUES (?, ?, ?)",
            ("Journalist Name", None, "journalist"),
        )
        pid_journalist = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        db.close()
        # Journalist gets 5 mentions; tracked gets 1 mention
        for i in range(5):
            insert_document(
                content=f"@journalist some text number {i} " * 10,
                source_id=None, platform="x_mention",
                source_url=f"https://x.com/other/status/{3000+i}",
                politician_links=[(pid_journalist, "mention_target")],
                db_path=path,
            )
        insert_document(
            content="@tracked one mention " * 10,
            source_id=None, platform="x_mention",
            source_url="https://x.com/other/status/3999",
            politician_links=[(pid_tracked, "mention_target")],
            db_path=path,
        )
        try:
            db = get_db(path)
            result = _fetch_x_data(db)
            names = [m["name"] for m in result["top_mentioned"]]
            assert "Journalist Name" not in names, (
                "Journalists must not appear in top_mentioned (CLAUDE.md convention)"
            )
            assert "Tracked Person" in names, (
                "Tracked politicians should appear in top_mentioned"
            )
            db.close()
        finally:
            _safe_unlink(path)

    def test_feed_items_coerce_none_party_to_empty_string(self):
        """data-party must never be the string 'None' — it would break JS ===."""
        from src.generate import _fetch_x_data
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        # Politician with NO party
        db.execute(
            "INSERT INTO tracked_politicians (name, party, relationship_type) "
            "VALUES (?, ?, ?)",
            ("No Party Person", None, "tracked"),
        )
        pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        db.close()
        insert_document(
            content="A tweet from someone without party affiliation " * 5,
            source_id=None, platform="twitter",
            source_url="https://x.com/noparty/status/4000",
            politician_links=[(pid, "subject")],
            db_path=path,
        )
        try:
            db = get_db(path)
            result = _fetch_x_data(db)
            for item in result["feed"]:
                assert item["party"] != None, "party must be coerced from None"
                assert item["party"] != "None", "party must not be literal 'None' string"
                assert isinstance(item["party"], str), "party must always be str"
            db.close()
        finally:
            _safe_unlink(path)


@pytest.fixture
def generate_db():
    """Temp DB with schema for _fetch_blog_posts footer stats."""
    import tempfile as _tempfile
    fd, path = _tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            scraped_at TEXT,
            platform TEXT
        );
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT, party TEXT, relationship_type TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            topic TEXT, stance TEXT, source_url TEXT,
            stated_at TEXT,
            claim_type TEXT NOT NULL DEFAULT 'position'
        );
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER, detected_at TEXT
        );
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY,
            note_type TEXT, content TEXT, topic TEXT,
            created_at TEXT, visual_brief_json TEXT
        );
        CREATE TABLE saeima_votes (
            id INTEGER PRIMARY KEY, vote_date TEXT
        );
        CREATE TABLE brief_images (
            id INTEGER PRIMARY KEY,
            note_id INTEGER, image_path TEXT, approved INTEGER
        );

        INSERT INTO tracked_politicians VALUES (1, 'X', 'JV', 'tracked');

        -- 2026-04-16 data: 3 docs (1 web, 1 twitter, 1 x_mention) + 1 saeima (excluded),
        -- 2 positions, 3 balsojumi, 1 pretruna
        INSERT INTO documents VALUES (1, '2026-04-16', 'web');
        INSERT INTO documents VALUES (2, '2026-04-16', 'twitter');
        INSERT INTO documents VALUES (3, '2026-04-16', 'x_mention');
        INSERT INTO documents VALUES (4, '2026-04-16', 'saeima');
        INSERT INTO claims (opponent_id, topic, stated_at, claim_type)
            VALUES (1, 'NATO', '2026-04-16', 'position');
        INSERT INTO claims (opponent_id, topic, stated_at, claim_type)
            VALUES (1, 'ES', '2026-04-16', 'position');
        INSERT INTO contradictions (opponent_id, detected_at) VALUES (1, '2026-04-16');
        INSERT INTO saeima_votes (vote_date) VALUES ('2026-04-16'), ('2026-04-16'), ('2026-04-16');

        INSERT INTO context_notes (note_type, content, topic, created_at)
            VALUES ('daily_brief',
                '# Dienas analīze — 2026-04-16' || char(10) || char(10) ||
                'Content.' || char(10) || char(10) ||
                '## Aktīvākie politiķi' || char(10) || '| Politiķis |' || char(10) ||
                '## Galvenās tēmas' || char(10) ||
                '## Koalīcija vs Opozīcija' || char(10),
                'dienas pārskats 2026-04-16',
                '2026-04-16 23:34:12');
    """)
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


class TestBlogPostFooter:
    def test_footer_has_doc_counts(self, generate_db):
        """3 docs (saeima excluded — bulk-import, not a real source)."""
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert len(posts) == 1
        post = posts[0]
        assert "footer" in post
        assert post["footer"]["doc_count"] == 3
        assert post["footer"]["web"] == 1
        assert post["footer"]["twitter"] == 1
        assert post["footer"]["mentions"] == 1

    def test_footer_has_position_count(self, generate_db):
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["positions"] == 2

    def test_footer_has_vote_count(self, generate_db):
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["votes"] == 3

    def test_footer_has_contradiction_count(self, generate_db):
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["contradictions"] == 1

    def test_footer_has_updated_display(self, generate_db):
        """created_at='2026-04-16 23:34:12' → '16.04.2026 23:34'."""
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["updated"] == "16.04.2026 23:34"

    def test_slug_derived_from_topic_not_created_at(self):
        """Brief regenerated on a later day must still slug to its subject
        date. Bug 2: _fetch_blog_posts used created_at[:10] → /blog/<regen>.html
        instead of /blog/<subject>.html. Fix: parse date from topic."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
            CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
            CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT, source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position');
            CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT);
            CREATE TABLE context_notes (id INTEGER PRIMARY KEY, note_type TEXT, content TEXT, topic TEXT, created_at TEXT, visual_brief_json TEXT);
            CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
            CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);

            INSERT INTO context_notes (note_type, content, topic, created_at) VALUES (
                'daily_brief',
                '# Dienas analīze — 2026-04-15' || char(10) || char(10) || 'Saturs.',
                'dienas pārskats 2026-04-15',
                '2026-04-19 10:00:00');
        """)
        db.commit()
        db.close()
        try:
            from src.generate import _fetch_blog_posts
            db = sqlite3.connect(path)
            db.row_factory = sqlite3.Row
            posts = _fetch_blog_posts(db)
            db.close()
            assert posts[0]["slug"] == "2026-04-15", \
                f"slug must be subject 2026-04-15, got {posts[0]['slug']!r}"
            assert posts[0]["date"] == "2026-04-15"
            # "Atjaunots" joprojām rāda regen laiku no created_at
            assert posts[0]["footer"]["updated"] == "19.04.2026 10:00"
        finally:
            _safe_unlink(path)

    def test_slug_falls_back_to_h1_when_topic_missing(self):
        """Topic has no date → parse from content H1 line."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
            CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
            CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT, source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position');
            CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT);
            CREATE TABLE context_notes (id INTEGER PRIMARY KEY, note_type TEXT, content TEXT, topic TEXT, created_at TEXT, visual_brief_json TEXT);
            CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
            CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);

            INSERT INTO context_notes (note_type, content, topic, created_at) VALUES (
                'daily_brief',
                '# Dienas analīze — 2026-04-10' || char(10) || char(10) || 'Saturs.',
                'bez datuma topic',
                '2026-04-19 10:00:00');
        """)
        db.commit()
        db.close()
        try:
            from src.generate import _fetch_blog_posts
            db = sqlite3.connect(path)
            db.row_factory = sqlite3.Row
            posts = _fetch_blog_posts(db)
            db.close()
            assert posts[0]["slug"] == "2026-04-10", \
                f"slug must fall back to H1 date 2026-04-10, got {posts[0]['slug']!r}"
        finally:
            _safe_unlink(path)

    def test_footer_updated_handles_t_separator(self):
        """ISO 8601 with T separator (2026-04-16T23:34:12) also parses."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
            CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
            CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT, source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position');
            CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT);
            CREATE TABLE context_notes (id INTEGER PRIMARY KEY, note_type TEXT, content TEXT, topic TEXT, created_at TEXT, visual_brief_json TEXT);
            CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
            CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);

            INSERT INTO context_notes (note_type, content, topic, created_at)
                VALUES ('daily_brief', '# Hdr', 't', '2026-04-16T23:34:12');
        """)
        db.commit()
        db.close()

        try:
            from src.generate import _fetch_blog_posts
            db = sqlite3.connect(path)
            db.row_factory = sqlite3.Row
            posts = _fetch_blog_posts(db)
            db.close()
            assert posts[0]["footer"]["updated"] == "16.04.2026 23:34"
        finally:
            _safe_unlink(path)


class TestOgCardTemplate:
    def _env(self):
        from jinja2 import Environment, FileSystemLoader
        return Environment(loader=FileSystemLoader("templates"), autoescape=True)

    def test_renders_with_minimal_data(self):
        c = {
            "id": 1,
            "politician_name": "Test Persona",
            "role": "Deputāts",
            "party_short": "JV",
            "party_color": "#ff0000",
            "severity": "reversal",
            "severity_lv": "Apvērsums",
            "severity_glyph": "↺",
            "topic": "Test tēma",
            "initials": "TP",
            "old_date": "2026-01-01",
            "new_date": "2026-02-01",
            "old_stance": "Iepriekš stance",
            "new_stance": "Pašlaik stance",
            "old_quote": None,
            "new_quote": None,
            "summary": "Test summary",
            "photo_data_uri": None,
        }
        html = self._env().get_template("og-card.html.j2").render(c=c)
        assert "Test Persona" in html
        assert "↺" in html
        assert "Apvērsums" in html
        assert "TP" in html
        assert "Iepriekš stance" in html
        assert "Pašlaik stance" in html

    def test_photo_data_uri_rendered_when_present(self):
        c = {
            "id": 2,
            "politician_name": "P",
            "role": None,
            "party_short": "X",
            "party_color": "#00ff00",
            "severity": "minor_shift",
            "severity_lv": "Niansē",
            "severity_glyph": "≈",
            "topic": None,
            "initials": "P",
            "old_date": "2026-01-01",
            "new_date": "2026-01-02",
            "old_stance": "a",
            "new_stance": "b",
            "old_quote": None,
            "new_quote": None,
            "summary": None,
            "photo_data_uri": "data:image/jpeg;base64,AAA=",
        }
        html = self._env().get_template("og-card.html.j2").render(c=c)
        assert "data:image/jpeg;base64,AAA=" in html
        assert 'class="avatar-fallback"' not in html


class TestPretrunaDetailTemplate:
    def test_renders_with_og_meta(self):
        from jinja2 import Environment, FileSystemLoader
        from src.generate import _autolink_bills_filter
        env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
        env.filters["autolink_bills"] = _autolink_bills_filter
        env.globals["bill_slugs"] = set()
        c = {
            "id": 17,
            "politician_name": "Evika Siliņa",
            "slug": "evika-silina",
            "role": "Ministru prezidente",
            "party": "Jaunā Vienotība",
            "party_short": "JV",
            "party_color": "#0066cc",
            "severity": "reversal",
            "severity_lv": "Apvērsums",
            "severity_glyph": "↺",
            "topic": "Koalīcija un partijas",
            "initials": "ES",
            "has_photo": True,
            "old_date": "2025-10-31",
            "new_date": "2026-03-30",
            "old_stance": "iepriekš teksts",
            "new_stance": "pašlaik teksts",
            "old_source": "https://lsm.lv/raksts",
            "new_source": "https://delfi.lv/raksts",
            "old_source_domain": "lsm.lv",
            "new_source_domain": "delfi.lv",
            "old_quote": "Viņi ir pieviluši",
            "new_quote": None,
            "summary": "Test summary",
            "detected_at": "2026-04-05 12:00:00",
            "salience": 0.85,
            "delta_days": 150,
            "vote_summary": None,
            "vote_id": None,
        }
        html = env.get_template("pretruna-detail.html.j2").render(
            c=c, related=[], BASE_URL="https://atmina.lv",
            canonical_url="https://atmina.lv/pretrunas/17.html",
        )
        assert 'property="og:image" content="https://atmina.lv/assets/og/pretruna-17.png"' in html
        assert 'rel="canonical" href="https://atmina.lv/pretrunas/17.html"' in html
        assert "Evika Siliņa" in html
        assert "Visas pretrunas" in html
        assert "pretrunas/17.html" in html


class TestPhotoDataUri:
    def test_missing_returns_none(self):
        assert _photo_data_uri("this-slug-does-not-exist") is None

    def test_existing_returns_data_uri(self):
        photos = list((ASSETS_DIR / "photos").glob("*.jpg"))
        if not photos:
            pytest.skip("No photos available")
        slug = photos[0].stem
        uri = _photo_data_uri(slug)
        assert uri is not None
        assert uri.startswith("data:image/jpeg;base64,")
        assert len(uri) > 100


def test_fetch_commentary_about_returns_third_party_only(tmp_path):
    """Claims WHERE speaker_id IS NOT NULL AND speaker_id != opponent_id AND claim_type='commentary'."""
    from src.db import init_db, get_db
    from src.generate import _fetch_commentary_about

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    # init_db schema doesn't include x_handle on tracked_politicians — it's live in
    # production via ad-hoc migration. Add it here so the reader can return it.
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except sqlite3.OperationalError:
        pass  # column exists
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type, x_handle) VALUES (2, 'Komentētājs Ļūdzis', 'commentator', 'KomL')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, platform, published_at) VALUES (1, 'Komentārs ar garumzīmēm ā ē ī ū ņ.', 'hash-fetch-commentary-1', 'https://x.com/KomL/status/1', 'twitter', '2026-04-22T10:00:00+00:00')")
    # First-party claim about subject — MUST NOT appear
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (1, 1, 'savs temats', 'Pirmās puses pozīcija ar garumzīmēm ā ē ī ū.', 0.8, 'Pats runāja ar garumzīmēm ā ē ī ū ņ.', 0.5, 'https://news.lv/1', 'position', NULL)"
    )
    # Third-party commentary about subject — MUST appear
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (1, 1, 'korupcija', 'KomL apgalvo par subjektu ar garumzīmēm ā ē ī ū.', 0.7, 'Komentārs ar garumzīmēm ā ē ī ū ņ.', 0.5, 'https://x.com/KomL/status/1', 'commentary', 2)"
    )
    db.commit()

    rows = _fetch_commentary_about(db, 1)
    assert len(rows) == 1
    assert rows[0]["claim_type"] == "commentary"
    assert rows[0]["speaker_id"] == 2
    assert rows[0]["speaker_name"] == "Komentētājs Ļūdzis"
    assert rows[0]["speaker_handle"] == "KomL"
    assert rows[0]["topic"] == "korupcija"
    db.close()


def test_fetch_politicians_excludes_commentators(tmp_path):
    """The main politicians listing must NOT include relationship_type='commentator'."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politicians

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    # init_db doesn't create saeima_individual_votes — minimal stand-in so the
    # per-politician vote count subquery in _fetch_politicians can execute.
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
    )
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Īsts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.commit()

    rows = _fetch_politicians(db)
    names = [r["name"] for r in rows]
    assert "Īsts Politiķis" in names
    assert "Komentētājs Ļūdzis" not in names
    db.close()


def test_fetch_politicians_excludes_unconfirmed_contradictions(tmp_path):
    """contradictions_count must apply COALESCE(confirmed,1)=1 — neapstiprinātās
    (confirmed=0) pretrunas neskaitās, tāpat kā publiskajās pretrunu/tēmu/meklēšanas
    lapās. Citādi profila/typeahead skaitlis atšķirtos no publiskajām lapām."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politicians

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
    )
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Īsts Politiķis', 'tracked')")
    # One confirmed (publicēta), one unconfirmed (confirmed=0), one NULL (= publicēta).
    db.execute(
        "INSERT INTO contradictions (opponent_id, topic, summary, confirmed) "
        "VALUES (1, 'temats', 'Apstiprināta pretruna ar garumzīmēm ā ē ī ū.', 1)"
    )
    db.execute(
        "INSERT INTO contradictions (opponent_id, topic, summary, confirmed) "
        "VALUES (1, 'temats', 'Neapstiprināta pretruna ar garumzīmēm ā ē ī ū.', 0)"
    )
    db.execute(
        "INSERT INTO contradictions (opponent_id, topic, summary, confirmed) "
        "VALUES (1, 'temats', 'NULL-confirmed pretruna ar garumzīmēm ā ē ī ū.', NULL)"
    )
    db.commit()

    rows = _fetch_politicians(db)
    pol = next(r for r in rows if r["name"] == "Īsts Politiķis")
    # confirmed=1 + NULL count (2); confirmed=0 excluded.
    assert pol["contradictions_count"] == 2
    db.close()


def test_vote_alignment_for_ignores_non_vote_states(tmp_path):
    """_vote_alignment_for must filter vote IN ('Par','Pret','Atturas') on BOTH
    sides — klātbūtnes/reģistrācijas stāvokļi (Reģistrējies/Nebalsoja/
    Nereģistrējies) izslēgti, lai metrika mēra balsojumu sakritību, ne klātbūtni."""
    from src.db import init_db, get_db
    from src.render.politicians import _vote_alignment_for

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
    )
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (1, 'Deputāts Viens', 'A', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2, 'Deputāts Divi', 'B', 'tracked')")
    # 12 vote events. On the first 2 BOTH cast real, agreeing votes ('Par').
    # On the remaining 10, both are 'Nereģistrējies' (a non-vote state) — these
    # must be ignored entirely, so the pair shares only 2 countable votes and
    # falls below the HAVING total >= 10 threshold → no qualifying co-voter.
    for vid in range(1, 3):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 1, 'Par')", (vid,))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 2, 'Par')", (vid,))
    for vid in range(3, 13):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 1, 'Nereģistrējies')", (vid,))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 2, 'Nereģistrējies')", (vid,))
    db.commit()

    top, bottom = _vote_alignment_for(db, 1, top_n=3)
    # Only 2 real shared votes < 10 threshold → non-votes did not inflate the total.
    assert top == []
    assert bottom == []

    # Add 10 more real, agreeing votes so the pair now clears the threshold and
    # confirms only cast votes are counted (total == 12, 100% agreement).
    for vid in range(13, 23):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 1, 'Par')", (vid,))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, 2, 'Par')", (vid,))
    db.commit()
    top, _ = _vote_alignment_for(db, 1, top_n=3)
    assert len(top) == 1
    assert top[0]["total"] == 12  # 2 + 10 real votes; the 10 non-votes excluded
    assert top[0]["agree"] == 12
    assert top[0]["agree_pct"] == 100
    db.close()


class TestLastActivityTweetTime:
    """2026-04-24 regression: _get_last_activity for x_post / x_mention must
    use documents.published_at (actual tweet post time, UTC ISO from twikit,
    converted to LV-local +3h), not scraped_at. Before this fix, cards
    showed the scrape HH:MM and often the wrong DAY — a tweet posted
    22.04 19:09 UTC scraped 23.04 13:52 would display 23.04 on the card.
    """

    def _setup_db(self, tmp_path):
        from src.db import init_db, get_db
        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        db = get_db(db_path)
        db.executescript(
            "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
            "CREATE TABLE IF NOT EXISTS saeima_votes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_date TEXT, summary TEXT, topic TEXT);"
        )
        db.execute(
            "INSERT INTO tracked_politicians (id, name, relationship_type) "
            "VALUES (1, 'Test Politiķis', 'tracked')"
        )
        return db

    def test_x_post_uses_published_at_not_scraped_at(self, tmp_path):
        from src.generate import _get_last_activity

        db = self._setup_db(tmp_path)
        # Tweet posted 22.04 14:36 UTC = 17:36 LV, scraped 23.04 13:52 LV.
        # Card must show 22.04 17:36, not 23.04 anything.
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, "
            "source_url, published_at, scraped_at) VALUES "
            "(100, 'my tweet content', 'h1', 'twitter', "
            "'https://x.com/test/status/100', "
            "'2026-04-22T14:36:00+00:00', '2026-04-23 13:52:00')"
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (100, 1, 'subject')"
        )
        db.commit()

        la = _get_last_activity(db, 1, "Test Politiķis")
        assert la is not None
        assert la["type"] == "x_post"
        assert la["date"] == "2026-04-22 17:36", (
            f"expected 2026-04-22 17:36 (pub converted to LV), got {la['date']!r}"
        )
        db.close()

    def test_x_mention_uses_published_at_not_scraped_at(self, tmp_path):
        from src.generate import _get_last_activity

        db = self._setup_db(tmp_path)
        # Mention posted 22.04 19:09 UTC = 22:09 LV, scraped 23.04 13:52 LV.
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, "
            "source_url, published_at, scraped_at) VALUES "
            "(200, 'someone mentioning test', 'h2', 'x_mention', "
            "'https://x.com/other/status/200', "
            "'2026-04-22T19:09:00+00:00', '2026-04-23 13:52:00')"
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (200, 1, 'mention_target')"
        )
        db.commit()

        la = _get_last_activity(db, 1, "Test Politiķis")
        assert la is not None
        assert la["type"] == "x_mention"
        assert la["date"] == "2026-04-22 22:09", (
            f"expected 2026-04-22 22:09, got {la['date']!r}"
        )
        db.close()

    def test_order_by_prefers_published_over_scraped(self, tmp_path):
        """ORDER BY COALESCE(published_at, scraped_at) DESC must pick the
        genuinely latest post, not the last one scraped. Two tweets:
        A published later but scraped earlier; B published earlier but
        scraped later. A must win.
        """
        from src.generate import _get_last_activity

        db = self._setup_db(tmp_path)
        # A: published 23.04 10:00 UTC (13:00 LV), scraped 23.04 10:30
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, "
            "source_url, published_at, scraped_at) VALUES "
            "(300, 'tweet A', 'ha', 'twitter', "
            "'https://x.com/test/status/300', "
            "'2026-04-23T10:00:00+00:00', '2026-04-23 10:30:00')"
        )
        # B: published 22.04 20:00 UTC (23:00 LV), scraped 23.04 14:00
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, "
            "source_url, published_at, scraped_at) VALUES "
            "(301, 'tweet B', 'hb', 'twitter', "
            "'https://x.com/test/status/301', "
            "'2026-04-22T20:00:00+00:00', '2026-04-23 14:00:00')"
        )
        for d in (300, 301):
            db.execute(
                "INSERT INTO document_politicians (document_id, politician_id, role) "
                "VALUES (?, 1, 'subject')", (d,)
            )
        db.commit()

        la = _get_last_activity(db, 1, "Test Politiķis")
        assert la is not None
        assert la["type"] == "x_post"
        # A wins — pub 23.04 13:00 > B pub 22.04 23:00
        assert "/status/300" in la["source_url"]
        assert la["date"] == "2026-04-23 13:00"
        db.close()


def test_fetch_politician_detail_returns_x_posts(tmp_path):
    """X subtab data: documents WHERE platform='twitter' AND role='subject'.
    Excludes x_mention (third-party-authored mentions) and role='mentioned'
    (politician named in someone else's tweet). Web docs stay in news."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politician_detail

    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
        "CREATE TABLE IF NOT EXISTS saeima_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, motif TEXT, vote_date TEXT, vote_time TEXT, result TEXT, topic TEXT, url TEXT);"
    )
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except sqlite3.OperationalError:
        pass
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (157, 'Kaspars Melnis')")
    db.executescript(
        """
        INSERT INTO documents (id, content, content_hash, source_url, source_domain, platform, published_at, language)
        VALUES
            (1, 'Melnis own tweet', 'h1', 'https://x.com/MelnisKaspars/status/1', 'x.com', 'twitter', '2026-04-25', 'lv'),
            (2, 'Heinrih5 mocks Melnis', 'h2', 'https://x.com/Heinrih5/status/2', 'x.com', 'twitter', '2026-04-24', 'lv'),
            (3, 'x_mention reply about Melnis', 'h3', 'https://x.com/User/status/3', 'x.com', 'x_mention', '2026-04-23', 'lv'),
            (4, 'Web article', 'h4', 'https://lsm.lv/foo', 'lsm.lv', 'web', '2026-04-22', 'lv');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (1, 157, 'subject'),
            (2, 157, 'mentioned'),
            (3, 157, 'mention_target'),
            (4, 157, 'subject');
        """
    )
    db.commit()

    detail = _fetch_politician_detail(db, 157)
    assert "x_posts" in detail
    x_posts = detail["x_posts"]
    # Only doc 1 qualifies: twitter platform AND role='subject' AND not x_mention.
    assert len(x_posts) == 1, f"expected 1 X post (own only), got {len(x_posts)}"
    assert x_posts[0]["id"] == 1
    ids = [p["id"] for p in x_posts]
    assert 2 not in ids  # role='mentioned' on twitter — filtered
    assert 3 not in ids  # x_mention platform — filtered
    assert 4 not in ids  # web platform — belongs to news
    db.close()


def test_fetch_politician_detail_includes_external_profiles(tmp_path):
    """_fetch_politician_detail atgriež 'external_profiles' atslēgu ar FB/website rindām."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politician_detail

    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    # Create minimal saeima tables so votes query doesn't fail
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
        "CREATE TABLE IF NOT EXISTS saeima_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, motif TEXT, vote_date TEXT, vote_time TEXT, result TEXT, topic TEXT, url TEXT);"
    )
    # Add x_handle column for _fetch_commentary_about
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except sqlite3.OperationalError:
        pass  # column exists
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (10, 'Test')")
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, handle, active) "
        "VALUES (10, 'facebook', 'https://www.facebook.com/test.user', 'test.user', 1)"
    )
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, active) "
        "VALUES (10, 'website', 'https://testsite.lv', 1)"
    )
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, active) "
        "VALUES (10, 'website', 'https://oldsite.lv', 0)"
    )
    db.commit()
    detail = _fetch_politician_detail(db, 10)
    profiles = detail["external_profiles"]
    assert len(profiles) == 2  # tikai aktīvie
    platforms = {p["platform"] for p in profiles}
    assert platforms == {"facebook", "website"}
    fb = next(p for p in profiles if p["platform"] == "facebook")
    assert fb["url"] == "https://www.facebook.com/test.user"
    assert fb["handle"] == "test.user"
    db.close()
