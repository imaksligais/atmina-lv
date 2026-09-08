"""Tests for scripts.audit_junction_role_inversion (+ src.quoted_speaker).

Detektora primitīvi (nominative_forms, speaks) kopš 2026-08-04 dzīvo
src/quoted_speaker.py (junction inversijas plāna 4. solis); skripts no tā
importē, tāpēc find_inversions testi te apzināti iet caur skriptu — tā
pierāda, ka skripta ceļš paliek dzīvs.

The class under test (BACKLOG § "Junction lomas apgrieztas ... `mentioned`
runātājs nekad nenonāk ekstrakcijas rindā"): a document's only quoted speaker
is linked `mentioned`, while the `subject` slot holds someone the article is
merely *about*. `get_pending_politicians` walks `role='subject'`, so the real
speaker never enters the extraction queue and the document still ends up
`reviewed_at`-stamped with zero positions.

The discriminator is grammatical, not lexical: Latvian puts the speaker of
"X teica" in the NOMINATIVE. An oblique form near the same verb ("par Xu
teica") means the person is being talked about. The 2026-08-02 measurement
recorded that the naive all-forms version misses doc 78085 entirely, so the
nominative restriction is load-bearing and is tested here directly.
"""

import sqlite3

import pytest

import src.db as db_mod
import src.ingest as ing_mod
import src.matcher as matcher_mod
from src.db import insert_document
from src.matcher import _clear_politician_cache


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated DB per test (same idiom as tests/test_audit_junction_roles.py)."""
    db_path = str(tmp_path / "atmina_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(ing_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    _clear_politician_cache()

    conn = orig_get_db(db_path)
    yield conn
    conn.close()


# --------------------------------------------------------------------------
# nominative_forms — the grammatical filter
# --------------------------------------------------------------------------

def test_nominative_forms_keeps_base_name_and_bare_surname():
    from src.quoted_speaker import nominative_forms

    got = nominative_forms(
        "Jānis Jurēvics",
        ["Jānis Jurēvics", "Jurēvics", "Jurēvica", "Jurēvicam", "Jurēviču"],
    )
    assert set(got) == {"Jānis Jurēvics", "Jurēvics"}


def test_nominative_forms_keeps_ascii_folded_variant():
    """Sources that strip diacritics still name the speaker in the nominative."""
    from src.quoted_speaker import nominative_forms

    got = nominative_forms(
        "Jānis Jurēvics",
        ["Jānis Jurēvics", "Jurēvics", "Janis Jurevics", "Jurevics", "Jurēvica"],
    )
    assert "Jurevics" in got
    assert "Janis Jurevics" in got
    assert "Jurēvica" not in got


def test_nominative_forms_handles_feminine_surname():
    from src.quoted_speaker import nominative_forms

    got = nominative_forms(
        "Ilze Vergina", ["Ilze Vergina", "Vergina", "Verginas", "Verginai"]
    )
    assert set(got) == {"Ilze Vergina", "Vergina"}


def test_nominative_forms_handles_multiword_surname():
    from src.quoted_speaker import nominative_forms

    got = nominative_forms("Hosams Abu Meri", ["Hosams Abu Meri", "Abu Meri", "Abu Merim"])
    assert "Abu Meri" in got
    assert "Abu Merim" not in got


# --------------------------------------------------------------------------
# speaks — nominative form inside the citation window
# --------------------------------------------------------------------------

def test_speaks_true_when_nominative_precedes_citation_verb():
    from src.quoted_speaker import speaks

    text = "Konkurss ir obligāts, aģentūrai LETA norādīja Jurēvics."
    assert speaks(text, ["Jurēvics"]) is True


def test_speaks_false_when_only_oblique_form_near_verb():
    """'par Jurēvicu teica' — he is the topic, not the speaker. This is the
    exact discrimination the naive all-forms version fails."""
    from src.quoted_speaker import speaks

    text = "Premjers par Jurēvicu teica, ka konkurss notiks."
    assert speaks(text, ["Jurēvics"]) is False


def test_speaks_false_when_nominative_far_from_any_signal():
    from src.quoted_speaker import speaks

    text = "Jurēvics" + " x" * 80 + " teica kaut ko pavisam citu."
    assert speaks(text, ["Jurēvics"]) is False


def test_speaks_requires_a_citation_signal_at_all():
    from src.quoted_speaker import speaks

    assert speaks("Jurēvics bija klāt sēdē.", ["Jurēvics"]) is False


def test_speaks_false_when_signal_only_inside_longer_word():
    """`raksta` iekš `saraksta` — doc 80038 klase (BACKLOG #30, 2026-08-04):
    kandidātu sarakstu raksti nedrīkst padarīt katru pieminēto par runātāju.
    Signāls skaitās tikai vārda sākumā."""
    from src.quoted_speaker import speaks

    text = "Jurēvics iekļauts NA kandidātu saraksta augšgalā."
    assert speaks(text, ["Jurēvics"]) is False


def test_speaks_keeps_morphological_suffix_extensions():
    """Prefiksa sakritība ir apzināta: `pauž`→`paužot`, `skaidro`→`skaidrots`
    ir likumīga morfoloģija un tai jāpaliek (BACKLOG #30 mērījums)."""
    from src.quoted_speaker import speaks

    assert speaks("Paužot atbalstu, Jurēvics piedalījās.", ["Jurēvics"]) is True


def test_speaks_false_on_window_slice_artifact():
    """Loga izgriešana agrāk varēja pārcirst `laikrakstam` un fragmentā
    atstāt `rakstam`, kurā substrings `raksta` trāpīja bez vārda sākuma.
    Signāli jāmeklē pilnajā tekstā, ne izgrieztajā fragmentā."""
    from src.quoted_speaker import speaks

    # "laikrakstam" sākas pozīcijā 0; forma novietota tā, lai loga kreisā
    # robeža (idx-60=4) pārcērt vārdu aiz "laik" un vecais slice sāktos ar
    # "rakstam..." — tur substrings "raksta" trāpīja.
    text = "laikrakstam" + "y" * 52 + " Jurēvics ir klāt"
    idx = text.index("Jurēvics")
    assert idx - 60 == 4
    assert speaks(text, ["Jurēvics"]) is False


# --------------------------------------------------------------------------
# find_inversions — the detector, and its denominator
# --------------------------------------------------------------------------

def _seed_two_politicians(db):
    db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, relationship_type)
           VALUES (1, 'Andris Kulbergs', '["Andris Kulbergs","Kulbergs","Kulberga"]', 'tracked')"""
    )
    db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, relationship_type)
           VALUES (2, 'Jānis Jurēvics', '["Jānis Jurēvics","Jurēvics","Jurēvica"]', 'tracked')"""
    )
    db.commit()


def test_find_inversions_flags_doc_where_only_mentioned_speaks(tmp_db):
    from scripts.audit_junction_role_inversion import find_inversions

    _seed_two_politicians(tmp_db)
    doc_id = insert_document(
        content=(
            "Sāksies KNAB jaunā vadītāja meklēšana. Premjera komunikācijas "
            "padomniece apliecināja, ka process turpinās. Konkursa obligātumu "
            "aģentūrai LETA uzsvēra Jurēvics."
        ),
        source_id=None,
        platform="web",
        language="lv",
        source_url="https://nra.lv/knab-jauna-vaditaja-meklesana",
        politician_links=[(1, "subject"), (2, "mentioned")],
    )

    result = find_inversions(tmp_db)
    assert result["checked"] == 1
    ids = [inv["document_id"] for inv in result["inversions"]]
    assert ids == [doc_id]
    assert result["inversions"][0]["speaking_mentioned"] == [2]
    assert result["inversions"][0]["subject_ids"] == [1]


def test_find_inversions_ignores_doc_where_subject_also_speaks(tmp_db):
    from scripts.audit_junction_role_inversion import find_inversions

    _seed_two_politicians(tmp_db)
    insert_document(
        content=(
            "Kulbergs teica, ka konkurss nav vajadzīgs. Pretēju viedokli "
            "aģentūrai LETA uzsvēra Jurēvics."
        ),
        source_id=None,
        platform="web",
        language="lv",
        source_url="https://nra.lv/abi-runa",
        politician_links=[(1, "subject"), (2, "mentioned")],
    )

    result = find_inversions(tmp_db)
    assert result["checked"] == 1
    assert result["inversions"] == []


def test_find_inversions_excludes_organizations_from_the_speaking_side(tmp_db):
    """An institution named in a citation line is not a lost human speaker.

    The document IS a candidate (a human is also `mentioned`), so this exercises
    the exclusion itself rather than the candidate filter: the only entity that
    speaks is the organization, and that must not count as an inversion.
    """
    from scripts.audit_junction_role_inversion import find_inversions

    _seed_two_politicians(tmp_db)
    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, relationship_type)
           VALUES (3, 'Latvijas Banka', '["Latvijas Banka"]', 'organization')"""
    )
    tmp_db.commit()

    insert_document(
        content=(
            "Vadlīnijas skar arī Jurēvica pārraudzīto jomu. "
            "Par vadlīnijām aģentūrai LETA norādīja Latvijas Banka."
        ),
        source_id=None,
        platform="web",
        language="lv",
        source_url="https://nra.lv/lb-vadlinijas",
        politician_links=[(1, "subject"), (2, "mentioned"), (3, "mentioned")],
    )

    result = find_inversions(tmp_db)
    assert result["checked"] == 1
    assert result["inversions"] == []


def test_find_inversions_skips_docs_whose_only_mentioned_is_an_organization(tmp_db):
    """Such a document cannot produce a human-speaker inversion, so it must stay
    OUT of the denominator — padding it would flatter the flag rate."""
    from scripts.audit_junction_role_inversion import find_inversions

    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, relationship_type)
           VALUES (1, 'Andris Kulbergs', '["Andris Kulbergs","Kulbergs"]', 'tracked')"""
    )
    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, relationship_type)
           VALUES (3, 'Latvijas Banka', '["Latvijas Banka"]', 'organization')"""
    )
    tmp_db.commit()

    insert_document(
        content="Par vadlīnijām aģentūrai LETA norādīja Latvijas Banka.",
        source_id=None,
        platform="web",
        language="lv",
        source_url="https://nra.lv/lb-only",
        politician_links=[(1, "subject"), (3, "mentioned")],
    )

    result = find_inversions(tmp_db)
    assert result["checked"] == 0
    assert result["inversions"] == []


def test_find_inversions_reports_denominator_even_with_no_candidates(tmp_db):
    """A denominator of 0 must be visible, not implied by an empty finding list
    (CLAUDE.md: a gate that cannot fail is not evidence)."""
    from scripts.audit_junction_role_inversion import find_inversions

    result = find_inversions(tmp_db)
    assert result["checked"] == 0
    assert result["inversions"] == []
