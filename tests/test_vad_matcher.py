import pytest

from src.vad.matcher import (
    split_name, ascii_fallback, candidate_name_pairs, role_matches,
)


def test_split_simple():
    assert split_name(1, "Ainārs Šlesers") == ("Ainārs", "Šlesers")


def test_split_hyphenated_surname():
    assert split_name(1, "Agita Zariņa-Stūre") == ("Agita", "Zariņa-Stūre")


def test_split_multi_token_first_name():
    assert split_name(1, "Dāvis Mārtiņš Daugavietis") == ("Dāvis Mārtiņš", "Daugavietis")


def test_split_three_token_naive_default():
    # "Hosams Abu Meri" naïve dod ("Hosams Abu", "Meri") — kļūdains, bet bez override
    # tas ir noklusējuma uzvedība. Override jāpievieno _NAME_OVERRIDES dictā.
    assert split_name(99999, "Hosams Abu Meri") == ("Hosams Abu", "Meri")


def test_split_raises_on_single_token():
    with pytest.raises(ValueError):
        split_name(1, "Šlesers")


def test_ascii_fallback():
    assert ascii_fallback("Šlesers") == "Slesers"
    assert ascii_fallback("Zariņa-Stūre") == "Zarina-Sture"
    assert ascii_fallback("Edgars Rinkēvičs") == "Edgars Rinkevics"


def test_candidate_pairs_yields_diacritic_first():
    pairs = list(candidate_name_pairs(1, "Ainārs Šlesers"))
    assert pairs[0] == ("Ainārs", "Šlesers")
    assert pairs[1] == ("Ainars", "Slesers")


def test_candidate_pairs_no_dup_when_ascii_only():
    pairs = list(candidate_name_pairs(1, "Janis Kalnins"))
    assert pairs == [("Janis", "Kalnins")]


def test_split_hosams_override():
    """pid 161 Hosams Abu Meri — naïve dotu ('Hosams Abu', 'Meri') kas ir nepareizi.
    Override pid-keyed _NAME_OVERRIDES dictā labos uz ('Hosams', 'Abu Meri').
    """
    assert split_name(161, "Hosams Abu Meri") == ("Hosams", "Abu Meri")


def test_role_matches_always_true():
    """Post-2026-05-02 fix: trust full Vārds+Uzvārds search uniqueness, ne
    role-keyword overlap. role_matches return True jebkurā kombinācijā līdz
    novērojam reālus homonīmu false-positives.
    """
    assert role_matches("Saeimas deputāts", "Latvijas Republikas Saeima", "Saeimas deputāts")
    assert role_matches("Ministre", "Aizsardzības ministrija", "Ministrs")
    assert role_matches("LPV priekšsēdētājs", "Latvijas Republikas Saeima", "Saeimas deputāts")
    assert role_matches("Rīgas mērs", "Rīgas valstspilsētas pašvaldība", "Valstspilsētas domes priekšsēdētājs")
    assert role_matches("EP deputāts", "Rīgas valstspilsētas pašvaldība", "Valstspilsētas domes deputāts")
    assert role_matches(None, "X", "Y")
    assert role_matches("", "X", "Y")
