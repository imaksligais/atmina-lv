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
            negative_patterns TEXT,
            x_handle TEXT
        )"""
    )
    # Registered-handle matching (H) reads social_accounts ∪ x_handle; the
    # snapshot carries x_handle, and the empty table keeps the real query
    # path exercised (no OperationalError fallback) in hermetic runs.
    db.execute(
        """CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            platform TEXT,
            handle TEXT,
            feed_type TEXT
        )"""
    )
    db.executemany(
        """INSERT INTO tracked_politicians
           (id, name, party, role, relationship_type, name_forms, negative_patterns, x_handle)
           VALUES (:id, :name, :party, :role, :relationship_type, :name_forms, :negative_patterns, :x_handle)""",
        [
            {
                "id": r["id"],
                "name": r["name"],
                "party": r.get("party"),
                "role": r.get("role"),
                "relationship_type": r.get("relationship_type"),
                "name_forms": r.get("name_forms") or "[]",
                "negative_patterns": r.get("negative_patterns"),
                "x_handle": r.get("x_handle"),
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
    # Must still reject — including at document start. (The B2 veto forgives
    # sentence-initial capitals only for the CLOSED-class stop set; a blanket
    # positional exemption was rejected in the 2026-07-27 package because it
    # reopens exactly this "foreign full name opens the sentence" class.)
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


@pytest.mark.parametrize(
    "surname,text",
    [
        # 2026-09-22 DB audits: šīs trīs piesaistes bija DB (dzēstas, rollback
        # data/rollback/20260922-*.sql). Uzvārds tekstā parādās TIKAI kā
        # apakšvirkne garākā vārdā — vietvārdā, tautas nosaukumā vai citā uzvārdā.
        ("Baško", "Uzbrukumā cietusi Bašņeftj rūpnīca Baškortostānas galvaspilsētā."),
        ("Baško", "Latviskuma pēdas: Baškorstāna, kur baškīriem vēl atceras kolonistus."),
        ("Daudze", "Būvdarbi sāksies Daudzevas pagastā, teikts pašvaldības ziņojumā."),
        ("Rajevs", "Interviju vadīja Filips Rajevskis, saruna ilga stundu."),
        # 2. partija (49 rindas, dzēstas 2026-09-22): tie paši slazdi citos vārdos.
        ("Kols", "Kolumbijas sprādzienā cietuši desmit cilvēki."),
        ("Kols", "Mēneša skolotājs strādā ar bērniem jau divdesmit gadus."),
        ("Daudze", "Daudzi atzina, ka produktu daudzums veikalos ir sarucis."),
        ("Lāce", "Pēdējie vārdi telefonā bija: lācis, lācis!"),
        ("Vilks", "Mežā redzēti vilki, teic mednieki."),
        ("Lūsis", "Rakstu komentēja Andris Lūsija kungs."),
        ("Liepiņš", "Pie Liepiņas tilta notiks remontdarbi."),
    ],
)
def test_surname_substring_in_longer_word_is_not_a_match(surname, text):
    """Uzvārds kā apakšvirkne garākā vārdā nav sakritība.

    Vārda robežas noteikums ir vienīgais, kas neļauj politiķim piekabināt
    rakstu par pavisam citu tēmu: "Baško" ⊂ "Baškortostāna" 2026. g. pavasarī
    ielika Jāzepa Baško profilā rakstu par Ukrainas delegāciju Maiami, un
    "Daudze" ⊂ "Daudzeva" — ceļu būvniecības ziņas Gundara Daudzes profilā.
    Rindas dzēstas 2026-09-22; šis tests tur ciet, lai nākamais ingest tās
    nepieliek atpakaļ.
    """
    from src.matcher import _occurrences

    assert _occurrences(text, surname) == [], (
        f"{surname!r} nedrīkst sakrist garāka vārda iekšienē: {text!r}"
    )


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


# --- B2+D2+H package (2026-07-27) — hermetic branch tests --------------------
# Fixture-DB cases for the same package live in matcher_docs.json (d2-*/b2-*/h-*
# names); these three cover branches the snapshot roster cannot reach.


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

    def __iter__(self):
        return iter(self._items)


def _stub_db_factory(politician_rows, social_rows=()):
    """get_db stub: PRAGMA reports the full column set; the politician SELECT
    returns politician_rows; any social_accounts SELECT returns social_rows."""

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
                        (5, "x_handle", "TEXT"),
                    ])
                if "FROM social_accounts" in sql:
                    return _StubCursor(list(social_rows))
                if "SELECT id, name, name_forms" in sql:
                    return _StubCursor(list(politician_rows))
                return _StubCursor([])

            def close(self):
                pass

        return _StubDB()

    return _stub_db


def test_institutional_acronym_exempt_from_foreign_firstname_veto(monkeypatch):
    """Institutional voices (relationship_type journalist/organization) do not
    participate in the foreign-first-name veto — their "first name" is not a
    person name. 'Valdība LDDK aicināja...' must keep the LDDK match even
    though the acronym form lacks the name's first token and the preceding
    word is a capitalised non-name (pre-B2D2H veto shape would reject it)."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory([
        _StubRow(id=900, name="Latvijas Darba devēju konfederācija",
                 name_forms='["LDDK", "Darba devēju konfederācija"]',
                 negative_patterns=None, relationship_type="organization",
                 x_handle=None),
    ]))

    text = "Valdība LDDK aicināja uz sarunām par nodokļiem."
    assert match_politicians(text) == [(900, "subject")]

    _clear_politician_cache()


def test_handle_from_social_accounts_matches_without_name_in_text(monkeypatch):
    """H: a registered social_accounts twitter handle in the text is a
    match form of its own — a doc whose only trace of the politician is
    '@handle' (no name form present, ASCII text) must link. Case-insensitive:
    the stored handle is mixed-case, the text lowercase."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory(
        [
            _StubRow(id=901, name="Jānis Paraudziņš",
                     name_forms='["Jānis Paraudziņš", "Paraudziņš"]',
                     negative_patterns=None, relationship_type="tracked",
                     x_handle=None),
        ],
        social_rows=[_StubRow(opponent_id=901, handle="JParaudzins")],
    ))

    text = "Atbildot @jparaudzins, ministrija solīja skaidrojumu."
    assert match_politicians(text) == [(901, "subject")]

    _clear_politician_cache()


def test_veto_log_records_discarded_candidates():
    """The veto observability hook: match_politicians(text, veto_log=[]) must
    append one entry per veto-discarded candidate with pid, the matched form,
    the foreign preceding token, and a text snippet — the /audit-integrity
    B2-veto journal is built on this. Runs against the snapshot roster."""
    from src.ingest import match_politicians

    log: list[dict] = []
    text = "Hokejists Alberts Šmits pagarināja līgumu ar klubu."
    assert match_politicians(text, veto_log=log) == []
    assert any(e["pid"] == 150 and e["preceding"] == "Alberts" for e in log), log
    for e in log:
        assert {"pid", "form", "preceding", "snippet"} <= set(e)
    # The hook must be pure observation: same text without the kwarg
    # produces the same (empty) result.
    assert match_politicians(text) == []


# --- Masculine -e surname dative -em (2026-09-22) --------------------------
# -e surnames split the dative by gender: fem. -ei (Mūrniece→Mūrniecei) vs
# masc. -em (Šnore→Šnorem). The generator sees only the surname, so it emits
# BOTH for every -e surname — deliberate over-generation, justified in
# _latvian_surname_inflections' docstring. The motivating miss was doc 71307
# (vestnesis protokols: "E. Šnorem pārstāvēt…").


@pytest.mark.parametrize(
    "surname,expected_em",
    [
        ("Šnore", "Šnorem"),
        ("Zīle", "Zīlem"),
        ("Krauze", "Krauzem"),
        # Over-generated for female -e surnames too — phantom form, kept
        # safe by the B2 veto / shared-surname machinery (see below).
        ("Mūrniece", "Mūrniecem"),
        ("Braže", "Bražem"),
    ],
)
def test_e_surname_generates_masculine_dative_em(surname, expected_em):
    """Every -e surname yields stem+'em' alongside the fem. -ei forms."""
    from src.matcher import _latvian_surname_inflections

    forms = _latvian_surname_inflections(surname)
    stem = surname[:-1]
    assert forms == [stem + "es", stem + "ei", stem + "em", stem + "i"]


def test_em_dative_reaches_forms_for_male_e_surname(monkeypatch):
    """_load_politician_forms must add 'Šnorem' to pid 7's forms — the stub
    mirrors his REAL row: name_forms carry palatalized ņ-variants
    ('Šņorem') that corpus text never writes, so only the auto-derived
    plain-n 'Šnorem' can match 'E. Šnorem'."""
    import src.matcher as m
    from src.matcher import _load_politician_forms, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory([
        _StubRow(id=7, name="Edvīns Šnore",
                 name_forms='["Šņore", "Šņores", "Šņorem", "Edvīns Šnore", "Šnore"]',
                 negative_patterns=None, relationship_type="tracked",
                 x_handle=None),
    ]))

    forms = {pid: f for pid, f, _, _ in _load_politician_forms()}[7]
    assert "Šnorem" in forms    # masculine dative — the missing piece
    assert "Šnores" in forms    # genitive (unchanged)
    assert "Šnori" in forms     # accusative (unchanged)
    assert "Šnorei" in forms    # fem. dative still emitted (pre-existing
    # over-generation, now symmetric)

    _clear_politician_cache()


def test_em_dative_matches_doc71307_shape(monkeypatch):
    """'E. Šnorem' — the literal doc 71307 case — must match pid 7.

    The preceding token 'E.' ends in a sentence-final char, so the B2 veto
    scan skips it: no foreign-name signal, bare-surname match survives."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            (7, ["Edvīns Šnore", "Šnore", "Šnores", "Šnorem", "Šnorei", "Šnori"],
             "Edvīns", []),
        ],
    )

    text = ("Iekšlietu ministrijas parlamentārajam sekretāram E. Šnorem "
            "pārstāvēt Latvijas Republiku Eiropas Savienības ministriju "
            "padomes sanāksmē.")
    assert match_politicians(text) == [(7, "subject")]

    _clear_politician_cache()


def test_female_em_overgeneration_does_not_hijack_male_mention(monkeypatch):
    """The phantom '-em' on a female -e surname must not attribute a
    same-surname MAN's mention to her: 'Edgaru Mūrniecem' names a man —
    the B2 foreign-first-name veto rejects pid 73. This is the same
    machinery that has always governed the genitive '-es' shared by both
    genders."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(
        m,
        "_load_politician_forms",
        lambda: [
            (73, ["Ināra Mūrniece", "Mūrniece", "Mūrnieces", "Mūrniecei",
                  "Mūrniecem", "Mūrneci"], "Ināra", []),
        ],
    )

    # Male Mūrniece in the dative, first name directly before the surname.
    text = "Atalgojumu palielināja arī domes deputātam Edgaram Mūrniecem."
    assert match_politicians(text) == []

    _clear_politician_cache()


# --- C: ALL-CAPS surnames (2026-10-01) ---------------------------------------
# Failure named: doc 120742 (Mežals, 2026-09-30) — «KULBERGS … INDRIKSONE»
# written in caps-lock emphasis linked nobody; the same text in Title case
# links both. The guards below keep the caps pass from reopening the classes
# the Title-case matcher already closed (acronyms, namesakes, negpatterns).

_CAPS_FORMS = [
    (10, ["Kulbergs", "Kulberga", "Kulbergam", "Kulbergu"], "Andris", []),
    (72, ["Indriksone", "Indriksones", "Indriksonei", "Indriksoni"], "Ilze", []),
]


def _patch_forms(monkeypatch, forms):
    import src.matcher as m

    m._clear_politician_cache()
    monkeypatch.setattr(m, "_load_politician_forms", lambda: forms)


def test_caps_surnames_match_doc120742_shape(monkeypatch):
    from src.matcher import match_politicians

    _patch_forms(monkeypatch, _CAPS_FORMS)
    text = ("🟥 KULBERGS no Apvienotā saraksta un INDRIKSONE no Nacionālās "
            "apvienības atkal NODOD savus vēlētājus tieši pirms vēlēšanām!")
    assert match_politicians(text) == [(10, "subject"), (72, "mentioned")]


def test_caps_foreign_first_name_still_vetoes(monkeypatch):
    """Before a caps surname hit, an all-caps preceding token is the name
    slot: a foreign one vetoes, the politician's own one confirms."""
    from src.matcher import match_politicians

    _patch_forms(monkeypatch, _CAPS_FORMS)
    assert match_politicians("MĀRTIŅŠ KULBERGS vakar paziņoja.") == []
    assert match_politicians("ANDRIS KULBERGS vakar paziņoja.") == [(10, "subject")]


def test_caps_pass_skips_short_forms(monkeypatch):
    """≤4-letter caps tokens are usually acronyms (LETA, NATO, KNAB), so a
    short form never matches in caps — only in its stored spelling."""
    from src.matcher import _caps_form, match_politicians

    assert _caps_form("Kols") is None
    assert _caps_form("Kulbergs") == "KULBERGS"
    _patch_forms(monkeypatch, [(24, ["Kols"], "Rihards", [])])
    assert match_politicians("KOLS ir jauns pakalpojums.") == []


def test_caps_negative_pattern_rejects(monkeypatch):
    from src.matcher import match_politicians

    forms = [(146, ["Andris Bērziņš", "Bērziņš"], "Andris", ["bijušais prezidents"])]
    _patch_forms(monkeypatch, forms)
    assert match_politicians("BIJUŠAIS PREZIDENTS ANDRIS BĒRZIŅŠ atklāja izstādi.") == []
    assert match_politicians("DEPUTĀTS ANDRIS BĒRZIŅŠ atklāja izstādi.") == [(146, "subject")]


def test_caps_pass_does_not_casefold(monkeypatch):
    """Only the fully upper-case word matches — a lower-case common noun
    («vītols» = willow) stays invisible, as before the caps pass."""
    from src.matcher import match_politicians

    _patch_forms(monkeypatch, [(40, ["Vītols", "Vītola"], "Jānis", [])])
    assert match_politicians("Pie upes aug vecs vītols un VĒJŠ šalc.") == []


def test_caps_heading_before_titlecase_repeat_keeps_match(monkeypatch):
    """Doc 106119: a caps headline word before «KULBERGS» is not a foreign
    first name when the text also names him in Title case — the pre-C
    rule stands whenever any hit is Title case."""
    from src.matcher import match_politicians

    _patch_forms(monkeypatch, _CAPS_FORMS)
    text = ("RT @ErlendsBB: TUKSMULDĒTĀJS KULBERGS\n\nKulbergs, kļūstot par "
            "premjeru, paziņoja, ka jābeidzas tukšmuldēšanas laikam.")
    assert match_politicians(text) == [(10, "subject")]


def test_handle_keeps_match_unique_despite_shared_caps_surname(monkeypatch):
    """Doc 119705: «ŠLESERS» is a surname two tracked people share, which
    made the candidate shared-only and dropped it — though the registered
    @handle in the same text identifies him uniquely."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory(
        [
            _StubRow(id=3, name="Ainārs Šlesers", name_forms='["Šlesers", "Šlesera"]',
                     negative_patterns=None, relationship_type="tracked", x_handle=None),
            _StubRow(id=56, name="Kristaps Šlesers", name_forms='["Šlesers", "Šlesera"]',
                     negative_patterns=None, relationship_type="tracked", x_handle=None),
        ],
        social_rows=[_StubRow(opponent_id=3, handle="SlesersAinars")],
    ))
    text = "RT @SlesersAinars: KURŠ ATBALSTA?KULBERGS PAR❗️\nŠLESERS PRET❗️"
    assert match_politicians(text) == [(3, "subject")]
    _clear_politician_cache()


def test_vestnesis_strict_filter_keeps_signatory(monkeypatch):
    """Acts are signed «Ministru prezidente E. Siliņa» — never the full name.
    The 2026-10-01 sample (docs/audits/2026-10-01-vestnesis-saites-izlase.md)
    read 16/30 failing links as signatories, so a full-name-only filter drops
    exactly the act's author. The signature line keeps the politician; the
    same initial form outside a signature line still does not."""
    from src.matcher import _filter_vestnesis_strict

    _patch_forms(monkeypatch, [(2, ["Evika Siliņa", "Siliņa"], "Evika", []),
                               (64, ["Viktors Valainis", "Valainis"], "Viktors", [])])
    signed = "Grozījumi noteikumos.\nMinistru prezidente E. Siliņa\nVides ministrs A. Bērziņš"
    assert _filter_vestnesis_strict([(2, "subject")], signed) == [(2, "subject")]
    other_initial = "Ekonomikas ministrs J. Valainis"
    assert _filter_vestnesis_strict([(64, "subject")], other_initial) == []
    not_a_signature = "Iesniedzējs: V. Valainis, Rīga."
    assert _filter_vestnesis_strict([(64, "mentioned")], not_a_signature) == []


def test_vestnesis_strict_filter_uses_canonical_name(monkeypatch):
    """30 politicians (Kulbergs, Siliņa, …) have only bare-surname name_forms;
    the canonical name must still count as the full form, or their own full
    name in an act is filtered out."""
    import src.matcher as m
    from src.matcher import _filter_vestnesis_strict

    _patch_forms(monkeypatch, [(10, ["Kulbergs", "Kulberga"], "Andris", [])])
    monkeypatch.setattr(m, "_politician_aux_cache", {10: {"name": "Andris Kulbergs"}})
    assert _filter_vestnesis_strict([(10, "subject")], "Saeimas deputāts Andris Kulbergs") == [(10, "subject")]
    assert _filter_vestnesis_strict([(10, "subject")], "Kulberga ielā 5") == []


def test_vestnesis_strict_filter_stays_case_sensitive(monkeypatch):
    """Vēstnesis notices print private people's names in caps («Mantojuma
    atstājējs: JĀNIS ZARIŅŠ»). The matcher now sees them; the Vēstnesis
    full-name filter must not — it is what keeps namesakes out."""
    from src.matcher import _filter_vestnesis_strict, match_politicians

    _patch_forms(monkeypatch, [(138, ["Jānis Zariņš", "Zariņš", "Zariņa"], "Jānis", [])])
    text = "Mantojuma atstājējs: JĀNIS ZARIŅŠ, miršanas datums 08.06.2026."
    links = match_politicians(text)
    assert links == [(138, "subject")]
    assert _filter_vestnesis_strict(links, text) == []


def test_handle_is_matched_whole_not_as_prefix(monkeypatch):
    """«@Krusts3» (Edvarts Krusts) must not confirm «@krusts» (Mārtiņš
    Krusts): a handle counts only when it ends where the tag ends."""
    import src.matcher as m
    from src.matcher import _handle_in, match_politicians, _clear_politician_cache

    assert _handle_in("@krusts3 nē", "krusts3")
    assert not _handle_in("@krusts3 nē", "krusts")
    assert _handle_in("paldies @krusts.", "krusts")
    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory(
        [
            _StubRow(id=41, name="Edvarts Krusts", name_forms='["Krusts", "Krusta"]',
                     negative_patterns=None, relationship_type="tracked", x_handle="Krusts3"),
            _StubRow(id=45, name="Mārtiņš Krusts", name_forms='["Krusts", "Krusta"]',
                     negative_patterns=None, relationship_type="tracked", x_handle="krusts"),
        ],
    ))
    assert match_politicians("@Krusts3 Masu imigrācija nekur nenovērš.") == [(41, "subject")]
    _clear_politician_cache()


# --- Shared forms across DIFFERENT nominatives (2026-10-05) ------------------
# 15. Saeimas kohorta: a man's genitive can be a woman's nominative.


def test_form_shared_across_different_nominatives_is_ambiguous(monkeypatch):
    """Failure named: Viesturs Kleinbergs (5) stores 'Kleinberga' (gen.), which
    is the nominative of Nellija Kleinberga. Nominatives differ, so the old
    shared_set missed it and a bare 'Kleinberga' linked both (Kļaviņš↔Kļaviņa
    class, 2026-05-31)."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory([
        _StubRow(id=5, name="Viesturs Kleinbergs",
                 name_forms='["Kleinbergs","Kleinberga","Kleinbergam"]',
                 negative_patterns=None, relationship_type="tracked", x_handle=None),
        _StubRow(id=950, name="Nellija Kleinberga",
                 name_forms='["Nellija Kleinberga"]',
                 negative_patterns=None, relationship_type="tracked", x_handle=None),
    ]))
    assert match_politicians("Kleinberga paziņoja, ka budžets jāpārskata.") == []
    assert match_politicians("Nellija Kleinberga paziņoja, ka budžets jāpārskata.") == [(950, "subject")]
    assert match_politicians("Viesturs Kleinbergs paziņoja, ka budžets jāpārskata.") == [(5, "subject")]
    _clear_politician_cache()


def test_identical_nominative_pair_needs_first_name(monkeypatch):
    """Failure named: 10-04 elected-list articles about Eduards Zivtiņš linked
    Edmunds (153). With both seeded, a bare surname must link nobody."""
    import src.matcher as m
    from src.matcher import match_politicians, _clear_politician_cache

    _clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory([
        _StubRow(id=153, name="Edmunds Zivtiņš", name_forms='["Edmunds Zivtiņš", "Zivtiņš"]',
                 negative_patterns=None, relationship_type="tracked", x_handle=None),
        _StubRow(id=952, name="Eduards Zivtiņš", name_forms='["Eduards Zivtiņš", "Zivtiņš"]',
                 negative_patterns=None, relationship_type="tracked", x_handle=None),
    ]))
    assert match_politicians("Zivtiņš balsoja par grozījumiem.") == []
    assert match_politicians("Edmunds Zivtiņš balsoja par grozījumiem.") == [(153, "subject")]
    _clear_politician_cache()


# --- Common-word surnames, 15. Saeimas kohorta (operatora lēmums 2026-10-05) --


def test_common_word_surname_needs_person_context(monkeypatch):
    _patch_forms(monkeypatch, [(951, ["Pēteris Dimants", "Dimants", "Dimanta",
                                      "Dimantam", "Dimantu"], "Pēteris", [])])
    from src.matcher import match_politicians
    assert match_politicians("Dimants ir cietākais minerāls dabā.") == []
    assert match_politicians("Pēteris Dimants norādīja, ka…") == [(951, "subject")]


def test_common_word_female_surname_needs_person_context(monkeypatch):
    """«ābola» = gen. of ābols (apple) and the nominative of Natālija Ābola."""
    _patch_forms(monkeypatch, [(953, ["Natālija Ābola", "Ābola", "Natalija Abola", "Abola",
                                      "Ābolas", "Ābolai", "Ābolu"], "Natālija", [])])
    from src.matcher import match_politicians
    assert match_politicians("Ābola sula ir salda.") == []
    assert match_politicians("Natālija Ābola norādīja, ka…") == [(953, "subject")]


def test_common_word_surname_with_speaking_verb_still_links(monkeypatch):
    """The guard must not cost the ordinary news shape «Putniņš paziņoja»."""
    _patch_forms(monkeypatch, [(954, ["Renārs Putniņš", "Putniņš", "Renars Putnins",
                                      "Putnins", "Putniņa", "Putniņam", "Putniņu"],
                                "Renārs", [])])
    from src.matcher import match_politicians
    assert match_politicians("Putniņš paziņoja, ka budžets jāpārskata.") == [(954, "subject")]
    assert match_politicians("Putniņš lidoja pār mežu.") == []


# --- Full-name-only politicians, 15. Saeimas kohorta (operatora lēmums 2026-10-05) --
# Failure named: T13 audit — Māris Ozoliņš ~58 % and Andrejs Jakovļevs ~41 %
# of links were namesakes (journalist Aivars Ozoliņš, a property-company head
# Māris Ozoliņš; an airBaltic board member, a retail shareholder Jakovļevs).
# For them the bare surname and its inflections must never be match forms.

_OZOLINS_ROW = dict(id=960, name="Māris Ozoliņš",
                    name_forms='["Māris Ozoliņš", "Ozoliņš", "Maris Ozolins", "Ozolins"]',
                    negative_patterns=None, relationship_type="tracked", x_handle=None)
_JAKOVLEVS_ROW = dict(id=961, name="Andrejs Jakovļevs",
                      name_forms='["Andrejs Jakovļevs", "Jakovļevs", "Andrejs Jakovlevs", "Jakovlevs"]',
                      negative_patterns=None, relationship_type="tracked", x_handle=None)


def _stub_full_name_only(monkeypatch, *rows):
    import src.matcher as m

    m._clear_politician_cache()
    monkeypatch.setattr(m, "get_db", _stub_db_factory([_StubRow(**r) for r in rows]))


def test_full_name_only_ozolins_bare_surname_does_not_link(monkeypatch):
    """Failure named: a bare «Ozoliņš» (any Ozoliņš) linked the deputy Māris
    Ozoliņš; so did a namesake's full name «Aivars Ozoliņš» via the bare-
    surname substring. Only his full name may link."""
    from src.matcher import match_politicians, _clear_politician_cache

    _stub_full_name_only(monkeypatch, _OZOLINS_ROW)
    assert match_politicians("Ozoliņš paziņoja, ka budžets jāpārskata.") == []
    assert match_politicians("Ozoliņa uzņēmums paziņoja par peļņu.") == []
    assert match_politicians("Aivars Ozoliņš raksta, ka valdība kļūdās.") == []
    assert match_politicians("Māris Ozoliņš paziņoja, ka budžets jāpārskata.") == [(960, "subject")]
    assert match_politicians("Maris Ozolins pazinoja, ka budzets japarskata.") == [(960, "subject")]
    _clear_politician_cache()


def test_full_name_only_jakovlevs_bare_surname_and_genitive_do_not_link(monkeypatch):
    """Failure named: «Jakovļevs» / gen. «Jakovļeva» (airBaltic board member,
    retail shareholder) linked the deputy Andrejs Jakovļevs."""
    from src.matcher import match_politicians, _clear_politician_cache

    _stub_full_name_only(monkeypatch, _JAKOVLEVS_ROW)
    assert match_politicians("Jakovļevs paziņoja, ka valde atkāpjas.") == []
    assert match_politicians("Jakovļeva akcijas pārdotas, paziņoja uzņēmums.") == []
    assert match_politicians("Andrejs Jakovļevs paziņoja, ka budžets jāpārskata.") == [(961, "subject")]
    assert match_politicians("Andrejs Jakovlevs pazinoja, ka budzets japarskata.") == [(961, "subject")]
    _clear_politician_cache()


def test_full_name_only_forms_contain_no_single_token(monkeypatch):
    """Load-level check: no single-token form survives for either politician —
    stored bare surnames are dropped and none are auto-derived."""
    from src.matcher import _load_politician_forms, _clear_politician_cache

    _stub_full_name_only(monkeypatch, _OZOLINS_ROW, _JAKOVLEVS_ROW)
    forms = {pid: f for pid, f, _, _ in _load_politician_forms()}
    assert sorted(forms[960]) == ["Maris Ozolins", "Māris Ozoliņš"]
    assert sorted(forms[961]) == ["Andrejs Jakovlevs", "Andrejs Jakovļevs"]
    _clear_politician_cache()


def test_politician_outside_full_name_only_set_keeps_bare_surname(monkeypatch):
    """Control: the guard is per-name — an ordinary politician still links by
    bare surname and its auto-derived inflection."""
    from src.matcher import match_politicians, _clear_politician_cache

    _stub_full_name_only(monkeypatch, dict(
        id=962, name="Jānis Paraudziņš", name_forms='["Jānis Paraudziņš", "Paraudziņš"]',
        negative_patterns=None, relationship_type="tracked", x_handle=None))
    assert match_politicians("Paraudziņš paziņoja, ka budžets jāpārskata.") == [(962, "subject")]
    assert match_politicians("Paraudziņa priekšlikums paziņots vakar.") == [(962, "subject")]
    _clear_politician_cache()
