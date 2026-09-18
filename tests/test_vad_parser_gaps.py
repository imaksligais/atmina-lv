"""2026-08-21 parsera robu testi: 5-sērijas reģistrācijas numuri + §13 tabulas saturs.

Fons: backlog/vad.md § NVO maksājumi — (a) entity_reg_number NULL pie
is_individual=1, kaut raw_html numuru satur (50008… sērija); (b) other_info
NULL, kaut §13 saturs raw_html ir (205 no 1276 blokiem saturā <table> formā).
"""

from pathlib import Path

from src.vad.parsing import parse_declaration_html

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "vad"


def _load(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.html").read_text(encoding="utf-8")


def test_five_series_reg_number_extracted_and_flag_corrected():
    """5-sērijas numurs (50008…) institūcijai jāizgūst kā reg; is_individual
    drīkst palikt True TIKAI rindai bez numura."""
    parsed = parse_declaration_html(_load("regnum5-otherinfo"))
    inst = next(p for p in parsed.positions if p.entity_name == "Ilgtspējīgas sabiedrības institūts")
    assert inst.entity_reg_number == "50008156541"
    assert inst.entity_address == "Rīga"
    assert inst.is_individual is False
    person = next(p for p in parsed.positions if p.entity_name == "Jānis Bērziņš")
    assert person.entity_reg_number is None
    assert person.is_individual is True


def test_section13_table_content_lands_in_other_info():
    parsed = parse_declaration_html(_load("regnum5-otherinfo"))
    assert parsed.other_info is not None
    assert "bez atalgojuma" in parsed.other_info
    assert "SIF Padomes locekle" in parsed.other_info


def test_section13_empty_block_stays_none():
    """Tukšs §13 (h2 aiz sevis tikai nākamais h2) nedrīkst ražot tukšu virkni."""
    html = _load("regnum5-otherinfo").replace(
        "<table>\n\t<tr><td>Saeimas deputāte no 01/11/2022 bez atalgojuma</td><td>SIF Padomes locekle no Labklājības ministra amatā stāšanās brīža.</td></tr>\n</table>\n\n",
        "",
    )
    parsed = parse_declaration_html(html)
    assert parsed.other_info is None


def test_four_series_still_extracts_regression():
    """4-sērijas uzvedība nemainīga (slesers fiksčura — UR numurs)."""
    parsed = parse_declaration_html(_load("slesers-2024"))
    lpv = next(p for p in parsed.positions if p.entity_name == "LATVIJA PIRMAJĀ VIETĀ")
    assert lpv.entity_reg_number == "40008310156"
