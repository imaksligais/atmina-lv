"""CVK rezultātu parseris: formāta maiņa → STOP, nekad tukšs/daļējs rezultāts (T12).

Nosauktā kļūme: CVK pārveido lapu (noņem iecirkņu tooltip vai sarakstu tabulu),
un skripts klusi uzraksta YAML bez provizoriskuma norādes vai ar 0 sarakstiem —
partijas.html tad rādītu nepilnīgus datus kā gala rezultātu. Bez tīkla, bez DB.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_cvk_results.py"
_spec = importlib.util.spec_from_file_location("fetch_cvk_results", _SCRIPT)
fcr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fcr)


def _row(nr, name, votes_txt, votes_order, pct_txt, pct_order, seats, tip=True):
    span = (
        '<span data-bs-toggle="tooltip" data-bs-title="Dati par 1024 no 1059 iecirkņiem">{}</span>'
        if tip else "{}"
    )
    return (
        f'<tr><td data-order="{nr}">{nr}</td><td><a href="#">{name}</a></td>'
        f'<td data-order="{votes_order}">{span.format(votes_txt)}</td>'
        f'<td data-order="{pct_order}">{span.format(pct_txt)}</td>'
        f'<td data-order="{seats}">{seats}</td></tr>'
    )


def _page(rows: str, *, updated: bool = True, seats_total: int = 100) -> str:
    upd = (
        '<div class="mt-2"><span class="fw-lighter fst-italic">'
        "Pēdējais atjauninājums veikts: 04.10.2026. plkst. 08:22</span></div>"
        if updated else ""
    )
    return f"""<html><body><main class="container p-4">
<blockquote>
<p><strong>Balsstiesīgie: </strong><em>1 557 615</em></p>
<p><strong>Nobalsojušie: </strong><em>788 154 (50,60%)</em></p>
<p><strong>Derīgās aploksnes: </strong><em>787 627 (50,57%)</em></p>
<p><strong>Derīgās zīmes: </strong><em>777 143 (98,67%)</em></p>
<p><strong>Ievēlamo deputātu skaits:
      </strong><em>{seats_total}</em></p>
</blockquote>
<table id="result-candidate-table"><thead><tr><th>Nr.</th></tr></thead>
<tbody>{rows}</tbody></table>
{upd}</main></body></html>"""


_VALID_ROWS = (
    _row(7, '"APVIENOTAIS SARAKSTS"', "278 338", "278338", "35,338%", "35.338", 58)
    + _row(8, "LATVIJA PIRMAJĀ VIETĀ", "102993", "102993", "13,076%", "13.076", 42)
)


def test_parses_minimal_valid_page_with_latvian_number_formats():
    r = fcr.parse_results(_page(_VALID_ROWS))
    assert (r["precincts_counted"], r["precincts_total"]) == (1024, 1059)
    assert r["cvk_updated_at"] == "2026-10-04 08:22"
    assert r["eligible_voters"] == 1557615
    assert (r["voted"], r["turnout_percent"]) == (788154, 50.60)
    assert r["valid_marks"] == 777143
    assert r["seats_total"] == 100
    first = r["lists"][0]
    assert first == {
        "list_nr": 7, "cvk_name": '"APVIENOTAIS SARAKSTS"',
        "votes": 278338, "percent": 35.338, "seats": 58,
    }
    # Pozitīvais validācijas gadījums: numuri 1..2, vietu summa 58+42 = 100.
    r["lists"] = [{**x, "list_nr": i + 1} for i, x in enumerate(r["lists"])]
    fcr.validate(r, expected_lists=2)


def test_nbsp_thousands_separator_parses():
    assert fcr.parse_lv_int("1\xa0557\xa0615") == 1557615


def test_hard_fails_without_precinct_tooltip():
    rows = (
        _row(7, "A", "278338", "278338", "35,338%", "35.338", 58, tip=False)
        + _row(8, "B", "102993", "102993", "13,076%", "13.076", 42, tip=False)
    )
    with pytest.raises(fcr.CvkFormatError, match="iecirkņu"):
        fcr.parse_results(_page(rows))


def test_hard_fails_without_update_timestamp():
    with pytest.raises(fcr.CvkFormatError, match="atjauninājums"):
        fcr.parse_results(_page(_VALID_ROWS, updated=False))


def test_hard_fails_without_list_table():
    html = _page(_VALID_ROWS).replace('id="result-candidate-table"', 'id="cits"')
    with pytest.raises(fcr.CvkFormatError, match="sarakstu tabula"):
        fcr.parse_results(html)


def test_validate_rejects_wrong_row_count_and_seat_sum():
    r = fcr.parse_results(_page(_VALID_ROWS))
    with pytest.raises(fcr.CvkFormatError, match="rindas"):
        fcr.validate(r)  # 2 rindas, gaidītas 14
    r_bad = fcr.parse_results(_page(_VALID_ROWS, seats_total=101))
    r_bad["lists"] = [{**x, "list_nr": i + 1} for i, x in enumerate(r_bad["lists"])]
    with pytest.raises(fcr.CvkFormatError, match="Vietu summa"):
        fcr.validate(r_bad, expected_lists=2)


def test_text_vs_data_order_mismatch_is_caught():
    rows = _row(7, "A", "278 338", "999", "35,338%", "35.338", 100)
    with pytest.raises(fcr.CvkFormatError, match="data-order"):
        fcr.parse_results(_page(rows))


def test_unknown_party_id_fails_loudly():
    lists = [{"list_nr": 7}]
    with pytest.raises(fcr.CvkFormatError, match="parties.id=6"):
        fcr.attach_party_ids(lists, known_party_ids={1, 2})
