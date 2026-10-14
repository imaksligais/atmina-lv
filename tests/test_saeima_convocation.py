"""15. Saeimas gatavība: dokumenta numuri jebkuram sasaukumam.

Kļūme, ko ķer: pēc 15. Saeimas sanākšanas (2026-11) numuri `/Lp15` klusi
netiek atpazīti — nav kļūdas, tikai tukšums (backlog/saeima.md)."""
import os
import tempfile

import pytest

from src.db import init_db
from src.saeima import init_saeima_bills, init_saeima_tables, upsert_bill
from src.saeima.bills import (
    SAEIMA_BASE_URL,
    _reading_from_motif,
    resolve_bill_from_motif,
)
from src.saeima.convocation import (
    SAEIMA_CONVOCATION,
    base_url,
    bill_kind,
    bill_type_from_nr,
    bill_type_sort_key,
    is_valid_bill_type,
)
from src.saeima.parsing import parse_agenda_snapshot
from src.saeima.votes import _BILL_LIKE_MOTIF


def test_current_convocation_is_still_14():
    # Apzināts atgādinājuma tests: pārslēgšana ir operatora solis pēc plāna
    # § Pārslēgšanas diena, ne automātika — tad šo testu atjauno uz 15.
    assert SAEIMA_CONVOCATION == 14


def test_base_url_follows_convocation():
    assert base_url(14) == "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"
    assert base_url(15) == "https://titania.saeima.lv/LIVS15/SaeimaLIVS2_DK.nsf"


@pytest.mark.parametrize("bt", ["Lp14", "Lm14", "P14", "Lp15", "Lm15", "P15"])
def test_valid_bill_types_any_convocation(bt):
    assert is_valid_bill_type(bt)


@pytest.mark.parametrize("bt", [None, "", "Lx15", "Lp1", "Lp150", "lp15", "P"])
def test_invalid_bill_types(bt):
    assert not is_valid_bill_type(bt)


@pytest.mark.parametrize("nr,expected", [
    ("1315/Lp14", "Lp14"),
    ("1/Lp15", "Lp15"),
    ("22/Lm15", "Lm15"),
    ("7/P15", "P15"),
    ("5/P140", None),
    ("5/Lp1", None),
    ("", None),
    (None, None),
])
def test_bill_type_from_nr(nr, expected):
    assert bill_type_from_nr(nr) == expected


def test_bill_kind():
    assert bill_kind("Lp15") == ("Likumprojekts", 15)
    assert bill_kind("Lm14") == ("Lēmuma projekts", 14)
    assert bill_kind("P15") == ("Paziņojums", 15)
    assert bill_kind("Lx15") is None
    assert bill_kind(None) is None


def test_bill_type_sort_key_newest_convocation_first_then_kind():
    types = ["P14", "Lm15", "Lp14", "Lp15", "Lm14", "P15"]
    assert sorted(types, key=bill_type_sort_key) == [
        "Lp15", "Lm15", "P15", "Lp14", "Lm14", "P14",
    ]


def test_base_url_constant_follows_convocation():
    # Vienīgais tests, kas sien SAEIMA_BASE_URL ar konstanti (ķer bills.py atkal iekodētu literāli).
    assert SAEIMA_BASE_URL == base_url()


@pytest.mark.parametrize("motif,expected", [
    ("Likumprojekts «Grozījumi» (1/Lp15)", "1/Lp15"),
    ("Lēmuma projekts (12 / Lm15), 1.lasījums", "12/Lm15"),
    ("Paziņojums 3/P15", "3/P15"),
    ("Likumprojekts (1315/Lp14)", "1315/Lp14"),
    ("Kaut kas (5/P140)", None),
])
def test_resolve_bill_any_convocation(motif, expected):
    assert resolve_bill_from_motif(motif) == expected


def test_reading_fallbacks_any_convocation():
    assert _reading_from_motif("Balsojums par (3/P15)") == "paziņojuma_balsojums"
    assert _reading_from_motif("Balsojums par (4/Lm15)") == "Lm14 cits"
    assert _reading_from_motif("Balsojums par (3/P14)") == "paziņojuma_balsojums"


def test_parse_agenda_snapshot_lp15():
    bills = parse_agenda_snapshot("Likumprojekts Grozījumi Pievienotās vērtības nodokļa likumā (1/Lp15)\n")
    assert [(b.document_nr, b.bill_type) for b in bills] == [("1/Lp15", "Lp15")]


def test_bill_like_motif_any_convocation():
    assert _BILL_LIKE_MOTIF.search("(1/Lp15)")
    assert _BILL_LIKE_MOTIF.search("(976/Lm14)")
    assert not _BILL_LIKE_MOTIF.search("(3/P15)")  # paziņojumi nav likumprojekti


def test_upsert_bill_accepts_lp15_rejects_garbage(tmp_path):
    # upsert_bill(db_path, document_nr, title, bill_type, ...) — pirmais arguments ir CEĻŠ.
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    assert upsert_bill(path, "1/Lp15", "Tests", "Lp15") > 0
    with pytest.raises(ValueError):
        upsert_bill(path, "1/Lx15", "Tests", "Lx15")
