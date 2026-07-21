"""Characterization tests for src.matcher (extracted in Phase 1).

Loads tests/fixtures/matcher_docs.json and asserts that match_politicians()
and extract_twitter_author_handle() produce identical output to the captured
baseline. This freezes behavior across the src.ingest → src.matcher move so
the refactor diff cannot silently change name-matching outcomes.

The fixture file documents each case's targeted code path; see its _doc /
_invariants headers for fixture maintenance rules.

Note: match_politicians() reads tracked_politicians + social_accounts from
the live DB via _load_politician_forms(). Adding a new politician with a
conflicting first/last name MAY shift expected_matches; in that case update
the fixture deliberately and document the change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "matcher_docs.json"

with FIXTURE_PATH.open(encoding="utf-8") as f:
    _FIXTURES = json.load(f)

# Snapshot of the matcher-relevant columns of the live tracked_politicians
# table. match_politicians() reads the WHOLE table (the shared-surname set is
# computed across every row, so a partial seed would change collision
# outcomes), so the baseline in matcher_docs.json can only be reproduced
# hermetically against the full roster. Public-safe: names + grammatical
# name_forms + collision-guard negative_patterns only — no claims, no private
# data. Refresh deliberately (alongside matcher_docs.json) when the roster
# changes a baseline case — see matcher_docs.json::_invariants.
_POLITICIANS_SNAPSHOT = Path(__file__).parent / "fixtures" / "matcher_politicians.json"


@pytest.fixture(scope="session")
def _matcher_db(tmp_path_factory) -> str:
    """Build a temp DB seeded with the tracked_politicians snapshot once per
    session. Only the columns the matcher reads are materialised."""
    import sqlite3

    rows = json.loads(_POLITICIANS_SNAPSHOT.read_text(encoding="utf-8"))
    db_path = str(tmp_path_factory.mktemp("matcher") / "politicians.db")
    db = sqlite3.connect(db_path)
    db.execute(
        """CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            role TEXT,
            relationship_type TEXT DEFAULT 'neutral',
            name_forms TEXT DEFAULT '[]',
            negative_patterns TEXT
        )"""
    )
    db.executemany(
        """INSERT INTO tracked_politicians
           (id, name, party, role, relationship_type, name_forms, negative_patterns)
           VALUES (:id, :name, :party, :role, :relationship_type, :name_forms, :negative_patterns)""",
        [
            {
                "id": r["id"],
                "name": r["name"],
                "party": r.get("party"),
                "role": r.get("role"),
                "relationship_type": r.get("relationship_type"),
                "name_forms": r.get("name_forms") or "[]",
                "negative_patterns": r.get("negative_patterns"),
            }
            for r in rows
        ],
    )
    db.commit()
    db.close()
    return db_path


@pytest.fixture(autouse=True)
def _use_matcher_db(_matcher_db, monkeypatch):
    """Point the matcher at the hermetic snapshot DB and reset its module
    caches around each test. Without this the matcher's no-arg get_db() would
    read the live (gitignored) data/atmina.db, which is absent in CI."""
    import src.db as db_mod
    from src.matcher import _clear_politician_cache

    monkeypatch.setattr(db_mod, "DB_PATH", _matcher_db)
    _clear_politician_cache()
    yield
    _clear_politician_cache()


@pytest.mark.parametrize(
    "case",
    _FIXTURES["match_politicians_cases"],
    ids=lambda c: c["name"],
)
def test_match_politicians_matches_baseline(case):
    """Every fixture case must produce identical (pid, role) tuples to the
    captured baseline. Refactor MUST NOT change matching behavior."""
    from src.ingest import match_politicians

    actual = match_politicians(case["text"])
    actual_normalized = [list(t) for t in actual]
    expected = case["expected_matches"]
    assert actual_normalized == expected, (
        f"Case {case['name']!r}: matcher behavior diverged from baseline.\n"
        f"  text: {case['text']!r}\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual_normalized}\n"
        f"  comment:  {case.get('comment', '')}"
    )


@pytest.mark.parametrize(
    "case",
    _FIXTURES["extract_twitter_author_handle_cases"],
    ids=lambda c: str(c.get("url"))[:60],
)
def test_extract_twitter_author_handle_matches_baseline(case):
    """URL helper baseline — handles x.com / twitter.com / non-twitter / None."""
    from src.ingest import extract_twitter_author_handle

    actual = extract_twitter_author_handle(case["url"])
    assert actual == case["expected"], (
        f"URL {case['url']!r}: expected {case['expected']!r}, got {actual!r}"
    )


def test_foreign_firstname_check_preserves_match_when_correct_firstname_elsewhere(monkeypatch):
    """Cross-occurrence first-name signal must override foreign-first-name reject.

    The foreign-first-name guard used to break on the first occurrence whose
    preceding word looked like an unrelated capitalised name — even when
    another occurrence in the same text was correctly preceded by the
    politician's own first name. That produced false rejects on dense
    multi-politician texts (e.g. "Evika Siliņa (JV) ... Melni, Siliņa
    uzsvēra ..." where the second 'Siliņa' has 'Melni,' before it).

    Reproduces the 2026-05-13 case-008/case-007 anomaly from
    tests/fixtures/eval_matcher_labeled.json: when name_forms lacks the
    full-name entry, the surname-only match must still survive if the
    first name appears as a preceding word at ANY occurrence.
    """
    from src.matcher import match_politicians, _clear_politician_cache
    import src.matcher as m

    _clear_politician_cache()
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            # Siliņa with NO full-name form — only surname inflections.
            # The fix must rely on cross-occurrence first-name scanning.
            (2, ["Siliņa", "Siliņas", "Siliņai", "Siliņu"], "Evika", []),
        ],
    )

    # Text where surname appears twice — once correctly preceded by 'Evika',
    # once preceded by an unrelated capitalised neighbour 'Melni,'.
    text_two_occurrences = (
        "Ministru prezidente Evika Siliņa (JV) šodien atklāja taktiku. "
        "Skaidrojot izvēli aizsardzības ministram pulkvedi Raivi Melni, "
        "Siliņa uzsvēra valsts intereses."
    )
    assert match_politicians(text_two_occurrences) == [(2, "subject")]

    # Self-surname repetition across sentences must not trigger foreign flag.
    # ("Sprūds. Sprūds sacīja...")
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            (16, ["Sprūds", "Sprūda", "Sprūdam", "Sprūdu"], "Andris", []),
        ],
    )
    text_self_repeat = (
        "Aizsardzības ministrs Andris Sprūds (P) papildināja. "
        "Apdzīvotā vietā nedrīkst notriekt dronus, sacīja Sprūds. "
        "Sprūds sacīja, ka tiek izskatīti visi varianti."
    )
    assert match_politicians(text_self_repeat) == [(16, "subject")]

    # Negative control: only a foreign first name, no correct one anywhere.
    # Must still reject (preserves existing 'foreign-firstname-kalnins' behavior).
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            (300, ["Rūdolfs Kalniņš", "Kalniņš", "Kalniņa", "Kalniņam"], "Rūdolfs", []),
        ],
    )
    text_only_foreign = "Krists Kalniņš teica, ka komiteja vēl nav lēmusi."
    assert match_politicians(text_only_foreign) == []

    _clear_politician_cache()


def test_institutional_voices_skip_last_token_autoderive(monkeypatch):
    """relationship_type IN ('journalist', 'organization') must NOT trigger
    the bare-last-token auto-derive or Latvian-inflection auto-add.

    Institutional voices like Saeimas ziņas, LTV Ziņas, IR žurnāls have
    a common-noun last token. The pre-2026-05-14 behaviour auto-derived
    bare 'ziņas' / 'žurnāls' / 'Panorāma' into the form list, so any
    document containing those common nouns matched the institutional
    voice — widespread FPs.

    Verifies that with empty name_forms, an institutional voice gets
    ONLY the full name as a form, no last-token-bare and no inflections.
    A regular (non-institutional) politician with the same shape still
    gets the full auto-derive (regression guard on prior behaviour).
    """
    import sqlite3
    import src.matcher as m
    from src.matcher import _load_politician_forms, _clear_politician_cache

    _clear_politician_cache()

    class _StubRow:
        def __init__(self, **kw):
            self._d = kw
        def __getitem__(self, k):
            return self._d.get(k)

    def _stub_db():
        class _StubDB:
            def execute(self, sql, *args):
                if "PRAGMA table_info" in sql:
                    # Pretend both negative_patterns and relationship_type exist.
                    cols = [
                        (0, "id", "INTEGER"),
                        (1, "name", "TEXT"),
                        (2, "name_forms", "TEXT"),
                        (3, "negative_patterns", "TEXT"),
                        (4, "relationship_type", "TEXT"),
                    ]
                    return _StubCursor(cols)
                if "SELECT id, name, name_forms" in sql:
                    return _StubCursor([
                        _StubRow(id=1001, name="Saeimas ziņas",
                                 name_forms=None, negative_patterns=None,
                                 relationship_type="organization"),
                        _StubRow(id=1002, name="LTV Ziņas",
                                 name_forms=None, negative_patterns=None,
                                 relationship_type="journalist"),
                        _StubRow(id=1003, name="Andris Sprūds",
                                 name_forms=None, negative_patterns=None,
                                 relationship_type="tracked"),
                    ])
                return _StubCursor([])
            def close(self):
                pass

        class _StubCursor:
            def __init__(self, items):
                self._items = items
            def fetchall(self):
                return self._items
        return _StubDB()

    monkeypatch.setattr(m, "get_db", _stub_db)
    forms_list = _load_politician_forms()
    forms_by_pid = {pid: forms for pid, forms, _, _ in forms_list}

    # Institutional: full name only, no bare last token, no inflections.
    assert forms_by_pid[1001] == ["Saeimas ziņas"], (
        f"organization voice must not auto-derive bare token; got {forms_by_pid[1001]}"
    )
    assert "ziņas" not in forms_by_pid[1001]
    assert forms_by_pid[1002] == ["LTV Ziņas"]
    assert "Ziņas" not in forms_by_pid[1002]

    # Regular politician: full auto-derive still works.
    assert "Andris Sprūds" in forms_by_pid[1003]
    assert "Sprūds" in forms_by_pid[1003]
    assert "Sprūda" in forms_by_pid[1003]   # genitive
    assert "Sprūdam" in forms_by_pid[1003]  # dative

    _clear_politician_cache()


def test_inflection_common_word_blocklist_daudzi(monkeypatch):
    """Auto-derived inflections colliding with common Latvian words are
    suppressed. Surname Daudze auto-inflects to "Daudzi", which at sentence
    start is indistinguishable from the adjective "daudzi" (= many) — and
    "Daudzi atzina, ka…" defeats the _COMMON_WORD_FORMS person-context gate
    because a speaking verb follows (doc 50893 FP, fixed 2026-06-11).
    The non-colliding inflections (Daudzes, Daudzei) must still derive.
    """
    import src.matcher as m
    from src.matcher import _load_politician_forms, _clear_politician_cache

    _clear_politician_cache()

    class _StubRow:
        def __init__(self, **kw):
            self._d = kw
        def __getitem__(self, k):
            return self._d.get(k)

    class _StubCursor:
        def __init__(self, items):
            self._items = items
        def fetchall(self):
            return self._items

    def _stub_db():
        class _StubDB:
            def execute(self, sql, *args):
                if "PRAGMA table_info" in sql:
                    return _StubCursor([
                        (0, "id", "INTEGER"),
                        (1, "name", "TEXT"),
                        (2, "name_forms", "TEXT"),
                        (3, "negative_patterns", "TEXT"),
                        (4, "relationship_type", "TEXT"),
                    ])
                if "SELECT id, name, name_forms" in sql:
                    return _StubCursor([
                        _StubRow(id=2001, name="Gundars Daudze",
                                 name_forms=None, negative_patterns=None,
                                 relationship_type="tracked"),
                    ])
                return _StubCursor([])
            def close(self):
                pass
        return _StubDB()

    monkeypatch.setattr(m, "get_db", _stub_db)
    forms_by_pid = {pid: forms for pid, forms, _, _ in _load_politician_forms()}

    assert "Daudzi" not in forms_by_pid[2001], (
        f"blocklisted common-word inflection must not derive; got {forms_by_pid[2001]}"
    )
    assert "Daudzes" in forms_by_pid[2001]
    assert "Daudzei" in forms_by_pid[2001]

    _clear_politician_cache()


def test_filter_vestnesis_strict_drops_surname_only(monkeypatch):
    """_filter_vestnesis_strict must drop politicians whose only match is a
    bare surname (no first+last full form in text). Mirrors 2026-05-13 cases
    where vestnesis tiesu nolēmumi/pavēles surname-match tracked politicians.
    """
    from src.matcher import _filter_vestnesis_strict, _clear_politician_cache
    import src.matcher as m

    # Stub the forms cache so the test is hermetic.
    _clear_politician_cache()
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            (107, ["Linda Liepiņa", "Liepiņa", "Liepiņas", "Liepiņai"], "Linda", []),
            (182, ["Otto Ozols", "Ozols", "Ozola"], "Otto", []),
            (2, ["Evika Siliņa", "Siliņa"], "Evika", []),
        ],
    )

    text_surname_only = "Tiesu nolēmumi: Liepiņa izsludināta par mirušu, civillietā."
    matches = [(107, "subject")]
    assert _filter_vestnesis_strict(matches, text_surname_only) == []

    text_full_name = "Saeimas deputāte Linda Liepiņa iesniedza priekšlikumu."
    assert _filter_vestnesis_strict([(107, "subject")], text_full_name) == [(107, "subject")]

    text_mixed = "Linda Liepiņa runā par Ozolu — surname-only otrais"
    assert _filter_vestnesis_strict(
        [(107, "subject"), (182, "mentioned")], text_mixed
    ) == [(107, "subject")]

    _clear_politician_cache()
