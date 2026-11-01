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


_HEADER = """<table>
	<tr><td>Deklarācijas veids:</td><td>Kārtējā gada deklarācija - par 2006. gadu</td></tr>
	<tr><td>Vārds, uzvārds:</td><td>TESTA PERSONA</td></tr>
</table>
"""


def test_debts_three_column_format():
    """Reālais §9 formāts (Summa/Valūta/Ar vārdiem) bez kreditora kolonnām.
    Regresija: līdz 2026-09-19 parseris prasīja >=4 šūnas → vad_debts=0 rindas."""
    html = _HEADER + """
<h2>9. Deklarācijas iesniedzēja parādsaistības, kuru apmērs pārsniedz 20 Ministru kabineta
	noteiktās minimālās mēnešalgas</h2>
<table>
	<thead><tr><th>Summa ar cipariem</th><th>Valūta</th><th>Summa ar vārdiem</th></tr></thead>
	<tbody><tr><td class="money">30000.00</td><td>LVL</td><td>trīsdesmit tūkstoši</td></tr></tbody>
</table>
"""
    parsed = parse_declaration_html(html)
    assert len(parsed.debts) == 1
    assert parsed.debts[0].amount == 30000.0
    assert parsed.debts[0].currency == "LVL"
    assert parsed.debts[0].amount_in_words == "trīsdesmit tūkstoši"


def test_debts_freeform_single_cell_multi_currency():
    """Vecais §9/§10 formāts: viena šūna ar brīvtekstu, ieskaitot vairākas valūtas.
    Regresija: '5 928 853 USD, 450 000 EUR, 7813 LVL' agrāk krita visām trim summām."""
    html = _HEADER + """
<h2>9. Parādsaistības</h2>
<table>
	<thead><tr><th>Publicējamā daļa</th></tr></thead>
	<tbody><tr><td>520 000 USD</td></tr></tbody>
</table>
<h2>10. Izsniegtie aizdevumi</h2>
<table>
	<thead><tr><th>Publicējamā daļa</th></tr></thead>
	<tbody><tr><td>5 928 853 USD, 450 000 EUR, 7813 LVL</td></tr></tbody>
</table>
"""
    parsed = parse_declaration_html(html)
    assert [(d.amount, d.currency) for d in parsed.debts] == [(520000.0, "USD")]
    assert [(l.amount, l.currency) for l in parsed.loans_given] == [
        (5928853.0, "USD"), (450000.0, "EUR"), (7813.0, "LVL"),
    ]
    # raw teksts saglabājas provenancai
    assert parsed.loans_given[0].amount_in_words == "5 928 853 USD, 450 000 EUR, 7813 LVL"


def test_debts_empty_section_and_freeform_without_money():
    """§9 bez tabulas → []. §9 ar tekstu bez summas → [] (nav ko saglabāt
    skaitliskajā shēmā — nav melnais caurums, tikai nav deklarētu parādu)."""
    html = _HEADER + """
<h2>9. Parādsaistības</h2>
<h2>10. Izsniegtie aizdevumi</h2>
<table>
	<thead><tr><th>Publicējamā daļa</th></tr></thead>
	<tbody><tr><td>atmaksāts pilnībā</td></tr></tbody>
</table>
"""
    parsed = parse_declaration_html(html)
    assert parsed.debts == []
    assert parsed.loans_given == []
