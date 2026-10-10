import os
import sqlite3
import tempfile

import pytest

from src.render._common.filters import _lv_money
from src.render.vad import (
    get_vad_data_for_politicians,
    payer_name,
    vad_count_per_politician,
)
from src.vad.schema import init_vad_tables


def _safe_unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE tracked_politicians(id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X'), (2, 'Y')")
    db.commit()
    init_vad_tables(path)
    return db, path


def _insert_declaration(db, opp_id, year, uuid, position="Saeimas deputāts", submitted="2025-03-27"):
    cur = db.execute(
        "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
        "declaration_kind, declaration_year, position_title, submitted_at, source_url) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (opp_id, uuid, f"Kārtējā gada deklarācija - par {year}. gadu", "annual", year,
         position, submitted, "https://example/"),
    )
    db.commit()
    return cur.lastrowid


def test_returns_empty_when_no_data():
    db, path = _fresh_db()
    try:
        assert get_vad_data_for_politicians(db, [1]) == {}
    finally:
        db.close()
        _safe_unlink(path)


def test_returns_empty_when_table_missing():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        # No init_vad_tables — table doesn't exist
        assert get_vad_data_for_politicians(db, [1]) == {}
        db.close()
    finally:
        _safe_unlink(path)


def test_loads_declarations_with_year_desc():
    db, path = _fresh_db()
    try:
        # Use distinct submitted_at to satisfy natural-key UNIQUE
        _insert_declaration(db, 1, 2022, "u-2022", submitted="2023-03-27")
        _insert_declaration(db, 1, 2024, "u-2024", submitted="2025-03-27")
        _insert_declaration(db, 1, 2023, "u-2023", submitted="2024-03-27")
        data = get_vad_data_for_politicians(db, [1])
        assert 1 in data
        years = [v.year for v in data[1]]
        assert years == [2024, 2023, 2022]
    finally:
        db.close()
        _safe_unlink(path)


def test_sections_get_delta_markers():
    db, path = _fresh_db()
    try:
        d_2023 = _insert_declaration(db, 1, 2023, "u-2023", submitted="2024-03-27")
        d_2024 = _insert_declaration(db, 1, 2024, "u-2024", submitted="2025-03-27")
        db.execute(
            "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
            "VALUES (?,?,?,?,?,?)",
            (d_2023, "Saeima", 0, "Alga", 50000.0, "EUR"),
        )
        db.execute(
            "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
            "VALUES (?,?,?,?,?,?)",
            (d_2024, "Saeima", 0, "Alga", 76000.0, "EUR"),
        )
        db.commit()
        data = get_vad_data_for_politicians(db, [1])
        income_2024 = data[1][0].sections["income"]
        assert income_2024[0].delta == "modified"
        assert income_2024[0].diff_text is not None
        assert "76\u00a0000" in income_2024[0].diff_text
    finally:
        db.close()
        _safe_unlink(path)


def test_vad_count_per_politician():
    db, path = _fresh_db()
    try:
        # Distinct submitted_at to satisfy natural-key UNIQUE
        _insert_declaration(db, 1, 2024, "u1", submitted="2025-03-27")
        _insert_declaration(db, 1, 2023, "u2", submitted="2024-03-27")
        _insert_declaration(db, 2, 2024, "u3", submitted="2025-03-27")
        counts = vad_count_per_politician(db)
        assert counts == {1: 2, 2: 1}
    finally:
        db.close()
        _safe_unlink(path)


# ── declaration_label: VID teksta parsēšana (2026-10-07) ─────────────
# Nosauktā kļūme: cilnes rādīja kodu («start start», «post_year_2
# post_year_2»), un `interim` kods nes divas pretējas nozīmes — etiķete
# jālasa no teksta. Gads no teksta pēdējā datuma, citādi submitted_at.

import pytest  # noqa: E402

from src.render.vad import declaration_label  # noqa: E402


@pytest.mark.parametrize("text, submitted, expected", [
    ("Kārtējā gada deklarācija - par 2025. gadu", "2026-03-27", ("2025", "2025-12-31")),
    ("Darba sākuma deklarācija - 2022. gada 01. novembrī", "2022-11-02",
     ("Stājoties amatā · 2022", "2022-11-01")),
    ("Darba sākuma deklarācija", "2021-08-01", ("Stājoties amatā · 2021", "2021-08-01")),
    ("Deklarācija, kuru iesniedz, stājoties amatā - 2013. gada 17. jūnijā", "2013-07-01",
     ("Stājoties amatā · 2013", "2013-06-17")),
    ("Deklarācija, kuru iesniedz, stājoties amatā", None, ("Stājoties amatā", "")),
    ("Beidzot darbu - 2014. gada 03. novembrī", "2015-01-05",
     ("Atstājot amatu · 2014", "2014-11-03")),
    ("Deklarācija, kuru iesniedz, beidzot pildīt amata pienākumus - 2004. gada 1. jūlijā",
     "2004-07-20", ("Atstājot amatu · 2004", "2004-07-01")),
    ("Deklarācija, kuru iesniedz, beidzot pildīt amata pienākumus", "2006-02-01",
     ("Atstājot amatu · 2006", "2006-02-01")),
    ("Beidzot darbu - par pirmo gadu - no 2014. gada 04. novembra līdz 2015. gada 03. novembrim",
     "2015-07-25", ("1. gads pēc amata · 2015", "2015-11-03")),
    ("Deklarācija, kuru iesniedz pēc tam, kad amata pienākumu pildīšana ir izbeigta (par pirmo gadu)"
     " - no 2004. gada 1. jūlija līdz 2005. gada 1. jūlijam", "2005-08-01",
     ("1. gads pēc amata · 2005", "2005-07-01")),
    ("Beidzot darbu - par otro gadu - no 2015. gada 06. novembra līdz 2016. gada 05. novembrim",
     "2016-07-29", ("2. gads pēc amata · 2016", "2016-11-05")),
    ("Deklarācija, kuru iesniedz pēc tam, kad amata pienākumu pildīšana ir izbeigta (par otro gadu)",
     "2006-09-01", ("2. gads pēc amata · 2006", "2006-09-01")),
])
def test_declaration_label(text, submitted, expected):
    assert declaration_label(text, submitted) == expected


def test_declarations_sorted_by_real_date_not_year_column():
    """Ne-gada deklarācijai `declaration_year` ir NULL — tā nedrīkst nogrimt
    saraksta beigās; delta tiek rēķināta pret hronoloģisko kaimiņu."""
    db, path = _fresh_db()
    try:
        _insert_declaration(db, 1, 2021, "a21", submitted="2022-03-27")
        _insert_declaration(db, 1, 2023, "a23", submitted="2024-03-27")
        db.execute(
            "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
            "declaration_kind, declaration_year, position_title, submitted_at, source_url) "
            "VALUES (1, 's22', 'Darba sākuma deklarācija - 2022. gada 01. novembrī', "
            "'start', NULL, 'Saeimas deputāts', '2022-11-02', 'https://example/')"
        )
        db.commit()
        labels = [v.label for v in get_vad_data_for_politicians(db, [1])[1]]
        assert labels == ["2023", "Stājoties amatā · 2022", "2021"]
    finally:
        db.close()
        _safe_unlink(path)


@pytest.mark.parametrize("source, expected", [
    ("Latvijas Republikas Saeima, 90000028300, Latvija, Rīga, Jēkaba iela 11",
     "Latvijas Republikas Saeima"),
    # Komats pēdiņās nosaukuma iekšienē nav griešanas vieta.
    ('SIA "Izglītības, tālākizglītības centrs", 40003467249, Latvija, Jūrmala',
     'SIA "Izglītības, tālākizglītības centrs"'),
    ('A/S "ICA DANMARK", T0900000012, Dānija, ?', 'A/S "ICA DANMARK"'),
    ("MFA Financial, Inc., AJ, Amerikas Savienotās Valstis, New York",
     "MFA Financial, Inc."),
    ("Igors Šuvajevs, ,", "Igors Šuvajevs"),
    ("EDGARS BRĒMANIS", "EDGARS BRĒMANIS"),
    (", ,", ""),
    ("040481-18007, ,", ""),  # personas kods nosaukuma vietā — nerādām
])
def test_payer_name(source, expected):
    assert payer_name(source) == expected


@pytest.mark.parametrize("amount, currency, expected", [
    (80000, "EUR", "80\u00a0000,00\u00a0€"),
    (1200, "USD", "1\u00a0200,00\u00a0USD"),
    (999.5, "LVL", "999,50\u00a0LVL"),
    (1234567.891, "EUR", "1\u00a0234\u00a0567,89\u00a0€"),
    (500, "-", "500,00"),
    (500, None, "500,00"),
    (-2500, "EUR", "−2\u00a0500,00\u00a0€"),
])
def test_lv_money(amount, currency, expected):
    assert _lv_money(amount, currency) == expected


def test_analysis_generator_counts_match_profile_with_yearless_start():
    """`vad-2026` § 5/§ 6 ģenerators jāsalīdzina ar to pašu iepriekšējo
    deklarāciju kā profils — hronoloģisko, arī bezgada stāšanās deklarāciju.
    Ar `ORDER BY COALESCE(declaration_year,0)` stāšanās nogrima un 2023. gada
    «aizgāja» rēķinājās pret 2021 (0, ne 2), un lapa dreifēja no profila."""
    from scripts.vad_analysis_numbers import profile_counts

    db, path = _fresh_db()
    try:
        a21 = _insert_declaration(db, 1, 2021, "a21", submitted="2022-03-27")
        a23 = _insert_declaration(db, 1, 2023, "a23", submitted="2024-03-27")
        s22 = db.execute(
            "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
            "declaration_kind, declaration_year, position_title, submitted_at, source_url) "
            "VALUES (1, 's22', 'Darba sākuma deklarācija - 2022. gada 01. novembrī', "
            "'start', NULL, 'Saeimas deputāts', '2022-11-02', 'https://example/')"
        ).lastrowid
        for decl, locs in ((a21, "A"), (s22, "ABC"), (a23, "A")):
            for loc in locs:
                db.execute(
                    "INSERT INTO vad_real_estate(declaration_id, property_type, location, "
                    "ownership_status) VALUES (?, 'Dzīvoklis', ?, 'Īpašumā')",
                    (decl, loc),
                )
        db.commit()

        row = profile_counts(db, {1: {}})["real_estate"]
        assert row == [(1, 2023, 1, 2, 3, "Stājoties amatā · 2022")]
        # Tas pats skaitlis, ko profila sadaļas virsraksts rāda 2023. cilnē.
        profile_2023 = get_vad_data_for_politicians(db, [1])[1][0]
        assert profile_2023.year == 2023
        assert len(profile_2023.sections["real_estate"]) == row[0][4]
    finally:
        db.close()
        _safe_unlink(path)
