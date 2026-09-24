"""Tests for src/quoted_speaker.py::recovery_survey — junction-atgūšanas apsekojums.

Reference 2026-09-23 evening: `pending_quoted_mentioned(days=2)` returned 0
pairs while a hand query found 31 web `mentioned` pairs with
`extracted_at IS NULL`, 18 with a speech signal; recovery then stored 9
positions from 11 pairs. The inversion band is blind to a speaking `mentioned`
politician whenever the `subject` ALSO speaks — that is the `beside_subject`
band this survey adds.

Fixture idiom follows tests/test_extraction_plan.py (init_db + raw fixture rows).
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from src.db import get_db, init_db, now_lv_dt

A, B, J, ORG, OLD = 1, 2, 3, 4, 5


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "survey.db")
    init_db(path)
    conn = get_db(path)
    rows = [
        (A, "Baiba Braže", '["Baiba Braže","Braže","Braži","Bražei"]', "tracked"),
        (B, "Andris Kulbergs", '["Andris Kulbergs","Kulbergs","Kulberga","Kulbergam","Kulbergu"]',
         "tracked"),
        (J, "Kārlis Žurnālists", '["Kārlis Žurnālists","Žurnālists"]', "journalist"),
        (ORG, "Latvijas armija (NBS)", '["NBS"]', "organization"),
        (OLD, "Vecais Deputāts", '["Vecais Deputāts","Deputāts"]', "inactive"),
    ]
    conn.executemany(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type, party) "
        "VALUES (?, ?, ?, ?, 'X')", rows)
    conn.commit()
    yield conn
    conn.close()


def _doc(db, doc_id, content, links, platform="web", age_hours=1, extracted=()):
    """links: [(pid, role)]; `extracted` = pids whose junction row is stamped."""
    ts = (now_lv_dt() - timedelta(hours=age_hours)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, platform, source_url) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, content, f"h{doc_id}", ts, platform, f"https://ex.lv/{doc_id}"))
    for pid, role in links:
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role, extracted_at) "
            "VALUES (?, ?, ?, ?)",
            (doc_id, pid, role, ts if pid in extracted else None))
    db.commit()


SPEAKING_BOTH = ("Ārlietu ministre Baiba Braže sacīja, ka sankcijas jāpagarina. "
                 "Opozīcijas deputāts Andris Kulbergs uzsvēra, ka valdība kavējas.")
SPEAKING_B_ONLY_SUBJECT_SILENT = ("Ministrijas darbu šonedēļ vērtēja arī Saeimā. "
                                  "Kulbergs sacīja, ka budžets ir nereāls.")
NO_SIGNAL = ("Baiba Braže sacīja, ka sankcijas jāpagarina. Komisijas sēde ilga "
             "vairāk nekā trīs stundas, un tajā piedalījās arī Andris Kulbergs "
             "un vairāki komisijas locekļi no dažādām frakcijām.")


def _survey(db, days=1):
    from src.quoted_speaker import recovery_survey
    return recovery_survey(db, days=days)


def _pairs(band):
    return [(p["document_id"], p["politician_id"]) for p in band]


def test_speaking_mentioned_beside_speaking_subject_is_found(db):
    _doc(db, 100, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")])
    res = _survey(db)
    assert _pairs(res["bands"]["beside_subject"]) == [(100, B)]
    pair = res["bands"]["beside_subject"][0]
    assert pair["name"] == "Andris Kulbergs"
    assert pair["platform"] == "web"
    assert pair["signals"] >= 1


def test_no_speech_signal_is_not_returned_but_is_counted(db):
    _doc(db, 101, NO_SIGNAL, [(A, "subject"), (B, "mentioned")])
    res = _survey(db)
    assert res["bands"]["beside_subject"] == []
    assert res["bands"]["inversion"] == []
    assert res["checked"] == 1


def test_extracted_pair_is_not_returned(db):
    _doc(db, 102, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")], extracted=(B,))
    res = _survey(db)
    assert res["bands"]["beside_subject"] == []
    assert res["checked"] == 0


def test_twitter_pair_is_found_and_counted_per_platform(db):
    _doc(db, 103, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")], platform="twitter")
    res = _survey(db)
    assert _pairs(res["bands"]["beside_subject"]) == [(103, B)]
    assert res["by_platform"]["twitter"]["beside_subject"] == 1


def test_doc_without_subject_is_counted_as_blind_zone_only(db):
    _doc(db, 104, SPEAKING_BOTH, [(B, "mentioned")])
    res = _survey(db)
    assert res["bands"]["blind_no_subject"] == {"docs": 1}
    assert res["checked"] == 0  # blind-zone pairs are NOT in the denominator
    assert 104 not in [p["document_id"] for p in res["bands"]["beside_subject"]]
    assert 104 not in [p["document_id"] for p in res["bands"]["inversion"]]


def test_excluded_relationship_types_never_enter(db):
    text = ("Baiba Braže sacīja, ka tā ir. Kārlis Žurnālists sacīja, ka nav. "
            "NBS sacīja, ka gatavi. Vecais Deputāts sacīja, ka redzēs.")
    _doc(db, 105, text, [(A, "subject"), (J, "mentioned"), (ORG, "mentioned"),
                         (OLD, "mentioned")])
    res = _survey(db)
    assert res["bands"]["beside_subject"] == []
    assert res["checked"] == 0


def test_outside_window_is_ignored(db):
    _doc(db, 106, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")], age_hours=72)
    res = _survey(db, days=1)
    assert res["checked"] == 0 and res["bands"]["beside_subject"] == []


def test_inversion_band_equals_pending_quoted_mentioned_and_bands_are_disjoint(db):
    from src.quoted_speaker import pending_quoted_mentioned
    _doc(db, 107, SPEAKING_B_ONLY_SUBJECT_SILENT, [(A, "subject"), (B, "mentioned")])
    res = _survey(db)
    expected = [(p["document_id"], p["politician_id"])
                for p in pending_quoted_mentioned(db, days=1)]
    assert expected == [(107, B)]
    assert _pairs(res["bands"]["inversion"]) == expected
    assert res["bands"]["beside_subject"] == []
    assert res["bands"]["inversion"][0]["signals"] >= 1
    assert res["by_platform"]["web"] == {"inversion": 1, "beside_subject": 0}


def test_checked_is_at_least_returned_pairs(db):
    _doc(db, 108, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")])
    _doc(db, 109, NO_SIGNAL, [(A, "subject"), (B, "mentioned")])
    _doc(db, 110, SPEAKING_B_ONLY_SUBJECT_SILENT, [(A, "subject"), (B, "mentioned")],
         platform="x_mention")
    res = _survey(db)
    returned = len(res["bands"]["inversion"]) + len(res["bands"]["beside_subject"])
    assert returned == 2
    assert res["checked"] >= returned
    assert res["checked"] == 3


def test_regression_2026_09_23_inversion_band_blind_where_subject_speaks(db):
    """Doc 114857 shape: subject Braže speaks, mentioned Kulbergs speaks.

    The inversion band requires a SILENT subject, so it returns 0 — the
    evening's recovered positions all came from this shape.
    """
    from src.quoted_speaker import pending_quoted_mentioned
    _doc(db, 114857, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")])
    assert pending_quoted_mentioned(db, days=2) == []
    res = _survey(db, days=2)
    assert len(res["bands"]["beside_subject"]) > 0


def test_oblique_form_near_signal_is_not_speech(db):
    text = ("Baiba Braže sacīja, ka par Kulbergu teica daudz, bet nekas netika "
            "pierādīts, un komisija lēmumu atlika uz nākamo nedēļu.")
    _doc(db, 111, text, [(A, "subject"), (B, "mentioned")])
    res = _survey(db)
    assert res["bands"]["beside_subject"] == []


def test_format_line(db):
    from src.quoted_speaker import format_recovery_line
    _doc(db, 112, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")])
    _doc(db, 113, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")], platform="twitter")
    _doc(db, 114, SPEAKING_BOTH, [(B, "mentioned")])
    line = format_recovery_line(_survey(db))
    assert line == ("ATGŪŠANA: 2 pāri (web 1 / twitter 1 / x_mention 0), "
                    "aklā zona 1 doks")


def test_print_routine_shows_recovery_line(tmp_path, monkeypatch, capsys):
    import src.db as dbmod
    import src.quoted_speaker as qs
    import src.routine as routine
    path = str(tmp_path / "r.db")
    init_db(path)
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    monkeypatch.setattr(routine, "check_routine", lambda d: {
        "all_complete": False,
        "steps": {"analysis": {"status": "done", "details": "x"}}})
    monkeypatch.setattr(qs, "recovery_survey", lambda db, days=1: {
        "checked": 40,
        "bands": {"inversion": [{}], "beside_subject": [{}, {}],
                  "blind_no_subject": {"docs": 4}},
        "by_platform": {"web": {"inversion": 1, "beside_subject": 1},
                        "twitter": {"inversion": 0, "beside_subject": 1}}})
    routine.print_routine("2026-09-23")  # past day → no afternoon gate
    out = capsys.readouterr().out
    assert ("ATGŪŠANA: 3 pāri (web 2 / twitter 1 / x_mention 0), aklā zona 4 doku"
            in out)


def test_recovery_extra_signals_find_a_questioning_deputy(db):
    """114870 shape: Šuvajevs only «jautāja»/«prasīja» — absent from
    CITATION_SIGNALS, present in RECOVERY_EXTRA_SIGNALS."""
    from src.quoted_speaker import CITATION_SIGNALS, RECOVERY_EXTRA_SIGNALS, speaks
    text = ("Baiba Braže sacīja, ka budžets ir sabalansēts. Komisijas sēdē "
            "vēlāk runāja par akcīzi. Kulbergs jautāja, vai koalīcija virzīs vēl ko.")
    _doc(db, 120, text, [(A, "subject"), (B, "mentioned")])
    assert _pairs(_survey(db)["bands"]["beside_subject"]) == [(120, B)]
    # The audit's own detector is untouched by the recovery-only set.
    assert "jautāja" in RECOVERY_EXTRA_SIGNALS and "jautāja" not in CITATION_SIGNALS
    assert not speaks(text[text.index("Kulbergs"):], ["Kulbergs"])


def test_null_relationship_type_is_kept(db):
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms, party) "
               "VALUES (9, 'Nulles Tips', '[\"Nulles Tips\",\"Tips\"]', 'X')")
    db.execute("UPDATE tracked_politicians SET relationship_type = NULL WHERE id = 9")
    db.commit()
    text = ("Baiba Braže sacīja, ka tā ir. Tālāk sēdē runāja par pavisam citu "
            "jautājumu. Nulles Tips uzsvēra, ka nav.")
    _doc(db, 121, text, [(A, "subject"), (9, "mentioned")])
    assert _pairs(_survey(db)["bands"]["beside_subject"]) == [(121, 9)]


def test_format_line_appends_non_default_platform(db):
    from src.quoted_speaker import format_recovery_line
    _doc(db, 122, SPEAKING_BOTH, [(A, "subject"), (B, "mentioned")], platform="vestnesis")
    assert format_recovery_line(_survey(db)) == (
        "ATGŪŠANA: 1 pāris (web 0 / twitter 0 / x_mention 0 / vestnesis 1), "
        "aklā zona 0 doku")


@pytest.mark.parametrize("n,word", [(0, "pāri"), (1, "pāris"), (4, "pāri"),
                                    (11, "pāri"), (21, "pāris"), (111, "pāri"),
                                    (141, "pāris")])
def test_lv_pairs_numeral_agreement(n, word):
    from src.quoted_speaker import lv_pairs
    assert lv_pairs(n) == word


def test_print_routine_prints_error_line_when_survey_raises(tmp_path, monkeypatch, capsys):
    import src.db as dbmod
    import src.quoted_speaker as qs
    import src.routine as routine
    path = str(tmp_path / "r.db")
    init_db(path)
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    monkeypatch.setattr(routine, "check_routine", lambda d: {
        "all_complete": False,
        "steps": {"analysis": {"status": "done", "details": "x"}}})

    def boom(db, days=1):
        raise RuntimeError("kolonna trūkst")

    monkeypatch.setattr(qs, "recovery_survey", boom)
    routine.print_routine("2026-09-23")
    out = capsys.readouterr().out
    assert ("ATGŪŠANA: KĻŪDA — RuntimeError: kolonna trūkst "
            "(palaid scripts/recovery_survey.py)") in out


def test_question_noun_is_not_a_speech_signal(db):
    """«jautājums» (noun) must not count; the verb «jautā» still does."""
    noun = ("Baiba Braže sacīja, ka tā ir. Pēc tam sēdē ilgi runāja par budžetu. "
            "Par šo jautājumu Kulbergs un citi deputāti tika informēti vēstulē.")
    _doc(db, 130, noun, [(A, "subject"), (B, "mentioned")])
    verb = ("Baiba Braže sacīja, ka tā ir. Pēc tam sēdē ilgi runāja par budžetu. "
            "Kulbergs jautā, kāpēc deputāti netika informēti vēstulē.")
    _doc(db, 131, verb, [(A, "subject"), (B, "mentioned")])
    assert _pairs(_survey(db)["bands"]["beside_subject"]) == [(131, B)]


@pytest.mark.parametrize("text,hit", [
    ("par šo jautājumu", False), ("jautājumā", False), ("jautājums", False),
    ("viņš jautā", True), ("viņš jautāja", True),
    ("prasamais apjoms", False), ("viņš prasa", True), ("viņš prasīja", True),
])
def test_recovery_regex_noun_continuations(text, hit):
    from src.quoted_speaker import _RECOVERY_SIGNAL_RE
    assert bool(_RECOVERY_SIGNAL_RE.search(text)) is hit
