from pathlib import Path

import pytest

from src.vad.parsing import parse_declaration_html, ALLOWED_CURRENCIES

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "vad"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.html").read_text(encoding="utf-8")


def test_parse_slesers_2024_header():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    h = parsed.header
    assert h.full_name == "AINĀRS ŠLESERS"
    assert h.declaration_kind == "annual"
    assert h.declaration_year == 2024
    assert h.institution == "Latvijas Republikas Saeima"
    assert h.position_title == "Saeimas deputāts"
    assert h.submitted_at == "2025-03-27"
    assert h.published_at == "2025-04-17"


def test_parse_slesers_2024_positions():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    titles = [p.position_title for p in parsed.positions]
    assert "Likvidators" in titles
    assert "Valdes loceklis" in titles
    lpv = next(p for p in parsed.positions if p.entity_name == "LATVIJA PIRMAJĀ VIETĀ")
    assert lpv.entity_reg_number == "40008310156"
    assert lpv.entity_address is not None
    assert "Mazā Smilšu" in lpv.entity_address


def test_parse_slesers_2024_real_estate():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.real_estate) == 4
    types = [r.property_type for r in parsed.real_estate]
    assert "Zeme" in types
    assert "Dzīvoklis" in types


def test_parse_slesers_2024_companies():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.companies) == 1
    avadel = parsed.companies[0]
    assert avadel.company_name.startswith("Sabiedrība ar ierobežotu atbildību")
    assert avadel.reg_number == "40003555683"
    assert avadel.units == 1000.0
    assert avadel.total_value == 10000.0
    assert avadel.currency == "EUR"


def test_parse_slesers_2024_vehicles():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert len(parsed.vehicles) == 1
    v = parsed.vehicles[0]
    assert v.vehicle_type == "Automašīna"
    assert v.brand == "MERCEDES BENZ AMG GLS 63"
    assert v.year_made == 2016
    assert v.ownership_status == "lietošanā"


def test_parse_slesers_2024_savings():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    cash = [s for s in parsed.savings if s.savings_kind == "cash"]
    bank = [s for s in parsed.savings if s.savings_kind == "bank"]
    assert len(cash) == 1
    assert cash[0].amount == 90000.0
    assert cash[0].currency == "EUR"
    assert len(bank) == 3
    swedbank = next(b for b in bank if "Swedbank" in (b.holder_name or ""))
    assert swedbank.amount == 111940.83
    assert swedbank.holder_reg_number == "40003074764"


def test_parse_slesers_2024_income_types():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    saeima_alga = next(i for i in parsed.income if i.income_type == "Alga")
    assert saeima_alga.amount == 76351.23
    assert saeima_alga.source_reg_number == "90000028300"
    assert not saeima_alga.is_individual
    inese = next(i for i in parsed.income if "Šlesere" in i.source)
    assert inese.is_individual
    assert inese.income_type == "Dāvinājums"


def test_parse_slesers_2024_loans():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    amounts = sorted(loan.amount for loan in parsed.loans_given)
    assert amounts == [31500.0, 61000.0]


def test_parse_slesers_2024_pension_flags():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    assert parsed.has_private_pension is False
    assert parsed.has_life_insurance is False


def test_parse_slesers_2024_family():
    parsed = parse_declaration_html(_load_fixture("slesers-2024"))
    by_relation = {r.relation for r in parsed.family}
    assert by_relation == {"Dēls", "Laulātais", "Māsa", "Māte"}
    spouse = next(f for f in parsed.family if f.relation == "Laulātais")
    assert spouse.full_name == "INESE ŠLESERE"


def test_parse_currency_validation():
    assert "EUR" in ALLOWED_CURRENCIES
    assert "RUB" in ALLOWED_CURRENCIES


def test_parse_raises_on_missing_header():
    with pytest.raises(ValueError):
        parse_declaration_html("<html><body>nothing here</body></html>")


# ---------------------------------------------------------------------------
# T7: intra-declaration income dedup
# HTML with two identical income rows must yield only one VadIncomeRow.
# Reproduces defect found in DB audit (decl 786 Braže 2002, decl 926
# Zemmers 2022, decl 2905-2909 Bergmanis 2007-2010).
# ---------------------------------------------------------------------------

_INCOME_DUP_HTML = """<!DOCTYPE html>
<html>
<body>
<table>
  <tr><td>Deklarācijas veids:</td><td>Kārtējā gada deklarācija - par 2002. gadu</td></tr>
  <tr><td>Vārds, uzvārds</td><td>TESTA PERSONA</td></tr>
  <tr><td>Darbavieta vai valsts amatpersonu saraksta iesniedzējas institūcija</td><td>Testinstitūcija</td></tr>
  <tr><td>Valsts amatpersonas amats</td><td>Direktors</td></tr>
  <tr><td>Iesniegta VID</td><td>01.04.2003.</td></tr>
  <tr><td>Publicēta</td><td>10.04.2003.</td></tr>
</table>
<h2>7. Ienākumi</h2>
<table>
  <thead><tr>
    <th>Ienākumu gūšanas vieta</th>
    <th>Ienākumu veids</th>
    <th>Summa</th>
    <th>Valūta</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>LATVIJAS REPUBLIKAS ĀRLIETU MINISTRIJA, 90000069065, Latvija, Rīga, Krišjāņa Valdemāra 3</td>
      <td>Alga</td>
      <td class="money">9589.59</td>
      <td>LVL</td>
    </tr>
    <tr>
      <td>LATVIJAS REPUBLIKAS ĀRLIETU MINISTRIJA, 90000069065, Latvija, Rīga, Krišjāņa Valdemāra 3</td>
      <td>Alga</td>
      <td class="money">9589.59</td>
      <td>LVL</td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""


def test_parse_income_dedup_identical_rows():
    """Parser must deduplicate identical income rows within a declaration.

    Source HTML for several real declarations (786, 887, 926, 2905-2909) contains
    duplicate <tr> entries with the same (source, income_type, amount, currency).
    The parser should emit only one VadIncomeRow per unique tuple.
    """
    parsed = parse_declaration_html(_INCOME_DUP_HTML)
    assert len(parsed.income) == 1, (
        f"Expected 1 income row after dedup, got {len(parsed.income)}: {parsed.income}"
    )
    row = parsed.income[0]
    assert row.source_reg_number == "90000069065"
    assert row.income_type == "Alga"
    assert row.amount == 9589.59
    assert row.currency == "LVL"
