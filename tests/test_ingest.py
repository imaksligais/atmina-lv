"""Tests for src.ingest — currently focused on politician name matching.

The 2026-04-10 backlog diagnosis found four name-match false positives
that had gone undetected: "Linda Abu Meri" → Hosams Abu Meri, "Ieva
Siliņa" and "Inta Siliņa" → Evika Siliņa. Those cases are locked in
here so the fix cannot regress silently.
"""
from __future__ import annotations

import pytest


# Fixture DB with the politicians involved in the false-positive cases
# plus a few controls. We avoid touching the real DB by building a
# fresh sqlite file and pointing src.ingest at it via module reload.
def _build_fixture_db(path):
    import json
    import sqlite3

    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            role TEXT,
            relationship_type TEXT DEFAULT 'neutral',
            name_forms TEXT DEFAULT '[]'
        )
    """)
    rows = [
        # pid, name, party, role, name_forms
        (1, "Edgars Rinkēvičs", "Bezpartejisks", "Valsts prezidents",
         json.dumps(["Edgars Rinkēvičs", "Rinkēvičs", "Rinkēvičam"])),
        (2, "Evika Siliņa", "Jaunā Vienotība", "Ministru prezidente",
         json.dumps(["Siliņa", "Siliņas", "Siliņai", "Evika Siliņa"])),
        (16, "Andris Sprūds", "Progresīvie", "Aizsardzības ministrs",
         json.dumps(["Andris Sprūds", "Sprūds", "Sprūda"])),
        (66, "Anda Čakša", "Jaunā Vienotība", "Izglītības ministre",
         json.dumps([])),  # empty forms — tests the derivation fallback
        (72, "Ilze Indriksone", "Nacionālā apvienība", "Ekonomikas ministre",
         json.dumps([])),  # empty forms
        (161, "Hosams Abu Meri", "Jaunā Vienotība", "Veselības ministrs",
         json.dumps(["Hosams Abu Meri", "Abu Meri"])),
    ]
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party, role, name_forms) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    db.commit()
    db.close()


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _build_fixture_db(str(db_path))

    # Point src.db.get_db at the fixture DB and reset the matcher module
    # caches so they reload from the fixture. Phase 1 (2026-04-29) moved
    # the caches from src.ingest to src.matcher; assigning to src.ingest
    # attributes only creates phantom names without touching the real
    # cache. _clear_politician_cache() resets all 3 globals at the home
    # module — guaranteed-correct regardless of any future cache splits.
    import src.db as db_mod
    from src.matcher import _clear_politician_cache
    original_path = db_mod.DB_PATH
    monkeypatch.setattr(db_mod, "DB_PATH", str(db_path))
    _clear_politician_cache()
    yield
    _clear_politician_cache()
    db_mod.DB_PATH = original_path


# -- Negative cases: must NOT match the wrong politician --------------------

NEGATIVE_CASES = [
    # (text, wrong_pid, description)
    (
        "Linda Abu Meri, Bauskas novada domes deputāte, pusgada laikā nopelnīja 22 673 eiro.",
        161,
        "wife-of-minister must not match minister (compound surname)",
    ),
    (
        "Ieva Siliņa sniedza komentāru par jauno projektu.",
        2,
        "different first name with shared surname",
    ),
    (
        "Inta Siliņa piedalījās konferencē par lauksaimniecību.",
        2,
        "different first name with shared surname",
    ),
]


@pytest.mark.parametrize("text,wrong_pid,description", NEGATIVE_CASES)
def test_name_match_rejects_foreign_first_name(fixture_db, text, wrong_pid, description):
    from src.ingest import match_politicians

    matches = match_politicians(text)
    matched_pids = [m[0] for m in matches]
    assert wrong_pid not in matched_pids, (
        f"{description}: {text!r} should NOT match pid={wrong_pid}. "
        f"Got: {matches}"
    )


# -- Positive cases: correct matches must still fire ------------------------

POSITIVE_CASES = [
    ("Veselības ministrs Hosams Abu Meri izteica neapmierinātību.", 161,
     "full name with title"),
    ("Ministrs Abu Meri komentēja reformu.", 161,
     "surname with title, no foreign first name"),
    ("Premjerministre Evika Siliņa paziņoja par prioritātēm.", 2,
     "full name with title"),
    ("Siliņa: reformas turpināsies.", 2,
     "bare surname at sentence start"),
    ("Ministrs Sprūds apmeklēja Kijivu.", 16,
     "surname with title"),
    ("Valsts prezidents Edgars Rinkēvičs iesniedza likumprojektu.", 1,
     "full name with multi-word title"),
    ("Anda Čakša komentēja veselības politiku.", 66,
     "politician with empty name_forms (derivation fallback)"),
    ("Ilze Indriksone atbalstīja budžeta grozījumus.", 72,
     "politician with empty name_forms"),
]


@pytest.mark.parametrize("text,expected_pid,description", POSITIVE_CASES)
def test_name_match_accepts_correct_politician(fixture_db, text, expected_pid, description):
    from src.ingest import match_politicians

    matches = match_politicians(text)
    matched_pids = [m[0] for m in matches]
    assert expected_pid in matched_pids, (
        f"{description}: {text!r} should match pid={expected_pid}. "
        f"Got: {matches}"
    )


# -- Form derivation edge cases ---------------------------------------------

def test_form_derivation_does_not_inject_compound_surname_tail(fixture_db):
    """Regression: _load_politician_forms used to add parts[-1] for every
    politician, which injected "Meri" into Hosam Abu Meri's form list and
    caused substring collisions with unrelated people named Abu Meri."""
    from src.ingest import _load_politician_forms

    forms_list = _load_politician_forms()
    hosam = next(entry for entry in forms_list if entry[0] == 161)
    forms = hosam[1]
    # Full name and compound surname are both valid forms
    assert "Hosams Abu Meri" in forms
    assert "Abu Meri" in forms
    # Bare "Meri" must NOT be present (it was the bug)
    assert "Meri" not in forms


def test_form_derivation_fallback_for_empty_forms(fixture_db):
    """Politicians with empty name_forms should get the full name and the
    bare surname derived automatically."""
    from src.ingest import _load_politician_forms

    forms_list = _load_politician_forms()
    cakša = next(entry for entry in forms_list if entry[0] == 66)
    forms = cakša[1]
    assert "Anda Čakša" in forms
    assert "Čakša" in forms


import pytest
from src.ingest import extract_twitter_author_handle


@pytest.mark.parametrize("url,expected", [
    ("https://x.com/KasparsH/status/2045853390337405314", "kasparsh"),
    ("https://x.com/BensLatkovskis/status/2045830485486535043", "benslatkovskis"),
    ("https://twitter.com/guntarsv/status/12345", "guntarsv"),
    ("https://x.com/3DCADLV/status/2045881576060285028", "3dcadlv"),
    ("https://x.com/Braze_Baiba/status/2045782645716537801?s=20", "braze_baiba"),
    ("https://x.com/Braze_Baiba/status/2045782645716537801/", "braze_baiba"),
    ("https://www.la.lv/par-partiku-maksasim", None),
    ("", None),
    (None, None),
])
def test_extract_twitter_author_handle(url, expected):
    assert extract_twitter_author_handle(url) == expected


# --- link_politicians_to_documents — URL author handle downgrade ------------


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Give the test a clean DB with the full atmina schema, and redirect
    src.db.get_db / src.ingest.get_db to open it. Yields a writable
    sqlite3.Connection the test can INSERT into directly.

    The fixture also nukes the cached politician-forms map so each test's
    tracked_politicians rows are reloaded fresh.
    """
    import sqlite3
    import src.db as db_mod
    import src.ingest as ing_mod
    import src.matcher as matcher_mod

    db_path = str(tmp_path / "atmina_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        # Ignore whatever default the caller captured at import time;
        # always open the test DB.
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(ing_mod, "get_db", _redirected_get_db)
    # Phase 1 (2026-04-29): matcher functions live in src.matcher; their
    # get_db reference is captured at import time and must be patched
    # separately. The src.ingest re-export shim doesn't help here because
    # the imported matcher functions resolve get_db via matcher_mod, not
    # ingest_mod, so the existing ing_mod patch alone leaves real-DB lookups
    # leaking through.
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    # Caches that would otherwise hold real-DB forms — both ingest (legacy
    # attr re-binding tolerated) and matcher (real cache home) cleared.
    matcher_mod._politician_forms_cache = None
    matcher_mod._SURNAME_DISAMBIGUATION = {}
    matcher_mod._shared_surname_set = set()

    conn = orig_get_db(db_path)
    try:
        yield conn
    finally:
        conn.close()
        matcher_mod._politician_forms_cache = None
        matcher_mod._SURNAME_DISAMBIGUATION = {}
        matcher_mod._shared_surname_set = set()


def test_insert_document_url_dedup_updates_in_place(tmp_db):
    """Web doc re-fetched with edited content (same URL, different content_hash)
    must UPDATE the existing row, not create a duplicate. 2026-05-13 Delfi
    edge case: article was rescraped 4h later with 87-char-shorter content;
    pre-fix this created doc#33208 alongside doc#32748 with the same URL.
    """
    from src.db import insert_document

    db_path = tmp_db.execute("PRAGMA database_list").fetchone()["file"]
    url = "https://www.delfi.lv/test/some-article"

    doc_id_1 = insert_document(
        content="Original content version A with more text 1234567890",
        source_id=None,
        source_url=url,
        platform="web",
        language="lv",
        db_path=db_path,
    )
    assert doc_id_1 is not None

    # Re-insert same URL with shorter (edited) content
    doc_id_2 = insert_document(
        content="Edited content version B shorter",
        source_id=None,
        source_url=url,
        platform="web",
        language="lv",
        db_path=db_path,
    )
    # Returns the SAME doc id — updated in place
    assert doc_id_2 == doc_id_1, "URL dedup should return existing doc id"

    rows = tmp_db.execute(
        "SELECT id, content FROM documents WHERE source_url=?", (url,)
    ).fetchall()
    assert len(rows) == 1, f"expected 1 row for URL, got {len(rows)}"
    assert rows[0]["content"] == "Edited content version B shorter"


def test_insert_document_url_dedup_skips_when_content_identical(tmp_db):
    """Same URL + same content_hash → existing content_hash dedup short-circuits
    before URL-dedup runs. Returns None (existing skip semantics). No row UPDATE."""
    from src.db import insert_document

    db_path = tmp_db.execute("PRAGMA database_list").fetchone()["file"]
    url = "https://www.delfi.lv/test/another-article"
    content = "Identical content across both fetches"

    doc_id_1 = insert_document(
        content=content, source_id=None, source_url=url,
        platform="web", language="lv", db_path=db_path,
    )
    doc_id_2 = insert_document(
        content=content, source_id=None, source_url=url,
        platform="web", language="lv", db_path=db_path,
    )
    assert doc_id_1 is not None
    assert doc_id_2 is None, "Exact content-hash duplicate must skip (return None)"

    rows = tmp_db.execute(
        "SELECT id FROM documents WHERE source_url=?", (url,)
    ).fetchall()
    assert len(rows) == 1


def test_insert_document_url_dedup_skips_for_non_web_platforms(tmp_db):
    """Twitter and vestnesis docs must NOT use URL-dedup (their URL→content
    contract is platform-stable; same URL = same content forever)."""
    from src.db import insert_document

    db_path = tmp_db.execute("PRAGMA database_list").fetchone()["file"]
    url = "https://x.com/someuser/status/123"

    doc_id_1 = insert_document(
        content="First tweet snapshot",
        source_id=None, source_url=url,
        platform="twitter", language="lv", db_path=db_path,
    )
    # Same URL with different content — for twitter platform, content_hash dedup
    # is the only gate; new content → new row. We accept this trade-off.
    doc_id_2 = insert_document(
        content="Different content for same tweet URL (hypothetical)",
        source_id=None, source_url=url,
        platform="twitter", language="lv", db_path=db_path,
    )
    assert doc_id_1 is not None
    assert doc_id_2 is not None and doc_id_2 != doc_id_1


def test_link_downgrades_subject_when_author_handle_does_not_match(tmp_db):
    """@KasparsH tweet mentioning Krusts — Krusts should be 'mentioned', not 'subject'.

    KasparsH is NOT a tracked politician, so the pre-fix code (which only
    downgraded when the URL author was tracked) leaves Krusts at 'subject'.
    """
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) "
        "VALUES (45, 'Mārtiņš Krusts', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) "
        "VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Pensiju 2. līmenis Lietuvā. Komentārs Mārtiņš Krusts par to.",
        source_id=None,
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        platform="twitter",
        language="lv",
        politician_links=[],
        db_path=tmp_db.execute("PRAGMA database_list").fetchone()["file"],
    )

    link_politicians_to_documents(days=30)

    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchone()
    assert row is not None, "Krusts should be linked to the doc"
    assert row["role"] == "mentioned", f"expected 'mentioned', got '{row['role']}'"


def test_link_keeps_subject_when_author_handle_matches(tmp_db):
    """@krusts own tweet — Krusts should stay as 'subject'."""
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) "
        "VALUES (45, 'Mārtiņš Krusts', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) "
        "VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Mārtiņš Krusts savas pozīcijas izklāsts par Hormuzu.",
        source_id=None,
        source_url="https://x.com/krusts/status/2045849970868179440",
        platform="twitter",
        language="lv",
        politician_links=[],
        db_path=tmp_db.execute("PRAGMA database_list").fetchone()["file"],
    )

    link_politicians_to_documents(days=30)
    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchone()
    assert row is not None, "Krusts should be linked"
    assert row["role"] == "subject"


def test_link_downgrades_even_when_author_is_tracked_non_match(tmp_db):
    """@BensLatkovskis tweet attacking Stendzenieks — Stendzenieks should be
    downgraded to 'mentioned'; Latkovskis (the URL author, tracked) stays
    'subject' because his handle matches.

    Latkovskis gets extra forms + multiple mentions so match_politicians
    ranks him first (subject) independently of row order. This keeps the
    assertion about the AUTHOR's role meaningful.
    """
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) "
        "VALUES (60, 'Ēriks Stendzenieks', "
        "'[\"Ēriks Stendzenieks\", \"Stendzenieks\"]')"
    )
    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) "
        "VALUES (114, 'Bens Latkovskis', "
        "'[\"Bens Latkovskis\", \"Latkovskis\", \"B. Latkovskis\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) "
        "VALUES (60, 'twitter', 'stendzenieks')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) "
        "VALUES (114, 'twitter', 'benslatkovskis')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content=(
            "B. Latkovskis raksta: Bens Latkovskis komentē — "
            "Ēriks Stendzenieks ar Dalniņu ir dvīņi. "
            "Stendzenieks turpina par JV politiku."
        ),
        source_id=None,
        source_url="https://x.com/BensLatkovskis/status/2045830485486535043",
        platform="twitter",
        language="lv",
        politician_links=[],
        db_path=tmp_db.execute("PRAGMA database_list").fetchone()["file"],
    )

    link_politicians_to_documents(days=30)

    stz_row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=60",
        (doc_id,),
    ).fetchone()
    lat_row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=114",
        (doc_id,),
    ).fetchone()
    assert stz_row is not None, "Stendzenieks should be linked"
    assert lat_row is not None, "Latkovskis should be linked"
    assert stz_row["role"] == "mentioned", "Stendzenieks mentioned, not subject"
    assert lat_row["role"] == "subject", "Latkovskis is the author — handle matches"


# --- negative_patterns — name-collision rejection ---------------------------


def test_match_rejects_when_negative_pattern_present(tmp_db):
    """Andris Bērziņš (ZZS deputy) should NOT match when text references
    former president context."""
    import json
    from src.ingest import match_politicians, _clear_politician_cache

    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, negative_patterns)
           VALUES (146, 'Andris Bērziņš', ?, ?)""",
        (
            json.dumps(["Andris Bērziņš", "Bērziņš"]),
            json.dumps([
                "bijušais Valsts prezidents",
                "bijušais prezidents",
                "eks-prezidents",
                "biedrība \"Latvijas Ceļu būvētājs\"",
                "Latvijas Ceļu būvētājs",
            ]),
        ),
    )
    tmp_db.commit()
    _clear_politician_cache()

    text_about_former_president = (
        "Par pārtiku maksāsim vēl vairāk. Andris Bērziņš, bijušais Valsts "
        "prezidents un biedrības \"Latvijas Ceļu būvētājs\" priekšsēdētājs, "
        "paredz, ka cenas turpinās kāpt."
    )
    matches = match_politicians(text_about_former_president)
    # pid=146 must NOT appear in matches
    assert not any(pid == 146 for pid, _ in matches), (
        f"expected pid=146 to be rejected; got matches={matches}"
    )


def test_match_accepts_when_no_negative_pattern(tmp_db):
    """Same politician should match when text is about them (no former-president context)."""
    import json
    from src.ingest import match_politicians, _clear_politician_cache

    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, negative_patterns)
           VALUES (146, 'Andris Bērziņš', ?, ?)""",
        (
            json.dumps(["Andris Bērziņš", "Bērziņš"]),
            json.dumps(["bijušais Valsts prezidents", "bijušais prezidents"]),
        ),
    )
    tmp_db.commit()
    _clear_politician_cache()

    text_about_zzs_deputy = "ZZS deputāts Andris Bērziņš uzstājās Saeimā par lauksaimniecību."
    matches = match_politicians(text_about_zzs_deputy)
    assert any(pid == 146 for pid, _ in matches), f"expected pid=146 match, got {matches}"


def test_link_relay_author_downgrades_quoted_politician_to_mentioned(tmp_db):
    """An LTV-authored (relay) tweet mentioning Krusts — Krusts is linked with
    role='mentioned', NOT 'subject'. The relay-handle→subject exemption was
    deliberately removed in the 2026-04-25 commentator demotion (matcher.py;
    wiki/CHANGELOG.md) because it mislabeled commentator-targeted politicians as
    subjects. The link still exists (politician reaches extraction); only the
    role is correct now."""
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type, name_forms) "
        "VALUES (70, 'LTV Ziņas', 'journalist', '[\"LTV Ziņas\", \"LTV\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (70, 'twitter', 'ltvzinas', 'relay')"
    )
    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type, name_forms) "
        "VALUES (71, 'Mārtiņš Krusts', 'tracked', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (71, 'twitter', 'krusts', 'first_party')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Pensiju 2. līmenis Lietuvā. Komentārs Mārtiņš Krusts par to.",
        source_id=None,
        source_url="https://x.com/ltvzinas/status/9003",
        platform="twitter",
        language="lv",
        politician_links=[],  # simulates relay _store_tweets
        db_path=tmp_db.execute("PRAGMA database_list").fetchone()["file"],
    )

    link_politicians_to_documents(days=30)

    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=71",
        (doc_id,),
    ).fetchone()
    assert row is not None, "Krusts must be linked to the LTV-authored doc"
    assert row["role"] == "mentioned", (
        f"expected 'mentioned' (relay author downgrade per 2026-04-25 demotion), got '{row['role']}'"
    )


def test_store_tweets_first_party_links_author_as_subject(tmp_db):
    """Default feed_type='first_party': author is marked as subject of the tweet."""
    from src.social import _store_tweets

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (50, 'Test Politician', 'tracked')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (50, 'twitter', 'testpol', 'first_party')"
    )
    tmp_db.commit()

    tweets = [{
        "id": "9001",
        "text": "Mans viedoklis par inflāciju ir, ka mums jādara vairāk lai to apkarotu.",
        "created_at": "2026-04-23T10:00:00+00:00",
        "platform": "twitter",
        "lang": "lv",
        "source_url": "https://x.com/testpol/status/9001",
    }]

    _store_tweets(tweets, opponent_id=50)

    row = tmp_db.execute(
        "SELECT role FROM document_politicians dp "
        "JOIN documents d ON d.id = dp.document_id "
        "WHERE d.source_url = 'https://x.com/testpol/status/9001'"
    ).fetchone()
    assert row is not None, "politician_id=50 must be linked to the doc"
    assert row["role"] == "subject"


def test_store_tweets_relay_skips_author_subject_link(tmp_db):
    """feed_type='relay': no politician_links at insert time, so link
    function can later assign subject role to quoted politicians."""
    from src.social import _store_tweets

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (60, 'LTV Ziņas', 'journalist')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (60, 'twitter', 'ltvzinas', 'relay')"
    )
    tmp_db.commit()

    tweets = [{
        "id": "9002",
        "text": "Valdība strādā avārijas režīmā, sacīja Saeimas deputāts Test Politiķis.",
        "created_at": "2026-04-23T10:00:00+00:00",
        "platform": "twitter",
        "lang": "lv",
        "source_url": "https://x.com/ltvzinas/status/9002",
    }]

    _store_tweets(tweets, opponent_id=60)

    rows = tmp_db.execute(
        "SELECT dp.politician_id, dp.role FROM document_politicians dp "
        "JOIN documents d ON d.id = dp.document_id "
        "WHERE d.source_url = 'https://x.com/ltvzinas/status/9002'"
    ).fetchall()
    assert rows == [], f"relay tweet must have NO junction links at store time, got {list(rows)}"


# =============================================================================
# _extract_published_at — meta tag parser for tier-2 web scrape
# Sources: NRA/Delfi/LA/LETA bypass RSS path and lost published_at; the helper
# parses common date metadata so tier-2 docs match RSS-fed sources.
# =============================================================================

class TestExtractPublishedAt:
    def test_article_published_time(self):
        from src.ingest import _extract_published_at
        html = '<html><head><meta property="article:published_time" content="2026-04-25T07:25:00+03:00"></head></html>'
        assert _extract_published_at(html) == "2026-04-25T07:25:00+03:00"

    def test_og_published_time(self):
        from src.ingest import _extract_published_at
        html = '<meta property="og:published_time" content="2026-04-25T07:25:00Z">'
        assert _extract_published_at(html) == "2026-04-25T07:25:00Z"

    def test_jsonld_date_published(self):
        from src.ingest import _extract_published_at
        html = '<script type="application/ld+json">{"@type":"Article","datePublished":"2026-04-25T07:25:00.000Z","author":"X"}</script>'
        assert _extract_published_at(html) == "2026-04-25T07:25:00.000Z"

    def test_itemprop_date_published(self):
        from src.ingest import _extract_published_at
        html = '<meta itemprop="datePublished" content="2026-04-25">'
        assert _extract_published_at(html) == "2026-04-25"

    def test_time_datetime(self):
        from src.ingest import _extract_published_at
        html = '<time datetime="2026-04-25T10:00:00" pubdate>April 25</time>'
        assert _extract_published_at(html) == "2026-04-25T10:00:00"

    def test_priority_article_over_og(self):
        from src.ingest import _extract_published_at
        html = '''<meta property="og:published_time" content="2026-01-01T00:00:00Z">
                  <meta property="article:published_time" content="2026-04-25T07:25:00Z">'''
        # article: is more specific; should win
        assert _extract_published_at(html) == "2026-04-25T07:25:00Z"

    def test_returns_none_when_no_date(self):
        from src.ingest import _extract_published_at
        html = '<html><head><title>No date here</title></head></html>'
        assert _extract_published_at(html) is None

    def test_returns_none_for_empty_html(self):
        from src.ingest import _extract_published_at
        assert _extract_published_at("") is None
        assert _extract_published_at(None) is None

    def test_returns_none_for_malformed_date(self):
        from src.ingest import _extract_published_at
        html = '<meta property="article:published_time" content="not-a-date">'
        assert _extract_published_at(html) is None

    def test_real_nra_jsonld_pattern(self):
        """Live NRA fetch returns this shape."""
        from src.ingest import _extract_published_at
        html = '<html>... "datePublished":"2026-04-02T03:00:00+03:00","dateModified":"2026-04-02T05:00:00" ...</html>'
        assert _extract_published_at(html) == "2026-04-02T03:00:00+03:00"

    def test_real_delfi_pattern(self):
        """Live Delfi has both article: meta and JSON-LD."""
        from src.ingest import _extract_published_at
        html = '''<meta property="article:published_time" content="2026-03-25T12:43:15.000Z" />
                  <script type="application/ld+json">{"datePublished":"2026-03-25T12:43:15.000Z"}</script>'''
        assert _extract_published_at(html) == "2026-03-25T12:43:15.000Z"

    def test_lsm_articledate_eet(self):
        """LSM.lv puts publication time in `<meta name="articledate">` with `EET` suffix."""
        from src.ingest import _extract_published_at
        html = '<meta name="articledate" content="2022-02-22T16:27:00EET" />'
        assert _extract_published_at(html) == "2022-02-22T16:27:00+02:00"

    def test_lsm_articledate_eest(self):
        """LSM.lv switches to `EEST` during DST (summer)."""
        from src.ingest import _extract_published_at
        html = '<meta name="articledate" content="2021-05-12T07:05:48EEST" />'
        assert _extract_published_at(html) == "2021-05-12T07:05:48+03:00"

    def test_jsonld_eet_normalized(self):
        """JSON-LD `datePublished` with `EET` suffix (LSM emits both meta + JSON-LD)."""
        from src.ingest import _extract_published_at
        html = '<script>{"datePublished":"2020-09-28T07:53:00EET"}</script>'
        assert _extract_published_at(html) == "2020-09-28T07:53:00+02:00"

    def test_lsm_articledate_single_digit_hour_eet(self):
        """LSM emits a NON-zero-padded hour for times before 10:00 (`T8:36`, not `T08:36`).

        ISO 8601 requires `08`, so datetime.fromisoformat rejected the bare `8` and the
        date was silently dropped — the real cause of dateless LSM docs in historic ingest.
        """
        from src.ingest import _extract_published_at
        html = '<meta name="articledate" content="2021-12-13T8:36:00EET" />'
        assert _extract_published_at(html) == "2021-12-13T08:36:00+02:00"

    def test_lsm_articledate_single_digit_hour_eest(self):
        """Same single-digit-hour quirk during DST (EEST)."""
        from src.ingest import _extract_published_at
        html = '<meta name="articledate" content="2021-05-20T9:59:00EEST" />'
        assert _extract_published_at(html) == "2021-05-20T09:59:00+03:00"


def test_parse_rss_items_passes_title_through():
    """_parse_rss_items emits a 'title' key per item from <title> tag."""
    from src.ingest import _parse_rss_items
    from datetime import datetime, timedelta

    future = (datetime.now() + timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item>
        <title>Saeima atbalsta budžetu</title>
        <description>Saeima šodien pieņēma budžeta likumprojektu.</description>
        <link>https://www.lsm.lv/raksts/zinas/latvija/saeima-atbalsta.a000001/</link>
        <pubDate>{future}</pubDate>
    </item>
    </channel></rss>"""
    items = _parse_rss_items(rss, "https://www.lsm.lv/feed/")
    assert len(items) == 1
    assert items[0]["title"] == "Saeima atbalsta budžetu"


# =============================================================================
# _enrich_rss_items_fulltext — tier-1 RSS lede -> full-text upgrade
# Regression: LSM/Diena tier-1 RSS ingest stored only the RSS <description>
# lede (~30-70 words), truncating every doc. This step fetches the article body
# and, on failure, keeps the lede but marks it `truncated` (loud, not silent).
# =============================================================================

import asyncio


class TestEnrichRssItemsFulltext:
    FEED = "https://www.lsm.lv/rss/?lang=lv&catid=20"
    ARTICLE = "https://www.lsm.lv/raksts/zinas/latvija/x.a654036/"

    def _run(self, items, monkeypatch, *, fetch_returns=None, extract_returns=None):
        import src.ingest as ing

        async def _fake_fetch_page(client, url):
            return fetch_returns

        def _fake_extract(html, **kwargs):
            return extract_returns

        monkeypatch.setattr(ing, "_fetch_page", _fake_fetch_page)
        monkeypatch.setattr(ing.trafilatura, "extract", _fake_extract)
        # No real sleeping in tests.
        async def _no_sleep(*a, **k):
            return None
        monkeypatch.setattr(ing.asyncio, "sleep", _no_sleep)
        return asyncio.run(ing._enrich_rss_items_fulltext(items, self.FEED))

    def test_success_replaces_lede_with_fulltext(self, monkeypatch):
        lede = "Saeima šodien pieņēma budžetu."
        full = "Saeima šodien pieņēma budžetu. " + ("Detalizēts pilns raksta teksts. " * 30)
        items = [{"text": lede, "url": self.ARTICLE, "published_at": None}]
        out = self._run(items, monkeypatch,
                        fetch_returns="<html>body</html>", extract_returns=full)
        assert out[0]["text"].startswith("Saeima")
        assert len(out[0]["text"]) > len(lede)
        assert not out[0].get("truncated")

    def test_fetch_failure_keeps_lede_and_marks_truncated(self, monkeypatch):
        lede = "Saeima šodien pieņēma budžetu."
        items = [{"text": lede, "url": self.ARTICLE, "published_at": None}]
        # _fetch_page returns None (fetch failed) -> extract never yields body.
        out = self._run(items, monkeypatch,
                        fetch_returns=None, extract_returns=None)
        assert out[0]["text"] == lede, "lede must be kept as fallback"
        assert out[0]["truncated"] is True, "truncation must be marked, not silent"

    def test_short_body_does_not_downgrade_lede(self, monkeypatch):
        # If the article page yields something no longer than the lede, keep lede
        # + mark truncated rather than storing a shorter/empty body.
        lede = "A reasonably long lede sentence that already carries the summary content."
        items = [{"text": lede, "url": self.ARTICLE, "published_at": None}]
        out = self._run(items, monkeypatch,
                        fetch_returns="<html></html>", extract_returns="tiny")
        assert out[0]["text"] == lede
        assert out[0]["truncated"] is True

    def test_feed_self_url_passed_through_untouched(self, monkeypatch):
        # RSS-fallback shape: item.url == feed url -> no per-article fetch.
        lede = "Whole feed dumped as one item."
        items = [{"text": lede, "url": self.FEED}]
        out = self._run(items, monkeypatch,
                        fetch_returns="<html>x</html>", extract_returns="x" * 5000)
        assert out[0]["text"] == lede
        assert not out[0].get("truncated")

    def test_social_url_passed_through_untouched(self, monkeypatch):
        lede = "Politiķis tvītoja par budžetu."
        items = [{"text": lede, "url": "https://x.com/Foo/status/123"}]
        out = self._run(items, monkeypatch,
                        fetch_returns="<html>x</html>", extract_returns="x" * 5000)
        assert out[0]["text"] == lede
        assert not out[0].get("truncated")

    def test_backfills_published_at_from_article_when_rss_missing(self, monkeypatch):
        lede = "Short lede."
        full = "Full article body. " * 40
        items = [{"text": lede, "url": self.ARTICLE, "published_at": None}]
        import src.ingest as ing
        monkeypatch.setattr(ing, "_extract_published_at",
                            lambda html: "2026-07-06T18:23:00+03:00")
        out = self._run(items, monkeypatch,
                        fetch_returns="<html>meta</html>", extract_returns=full)
        assert out[0]["published_at"] == "2026-07-06T18:23:00+03:00"
