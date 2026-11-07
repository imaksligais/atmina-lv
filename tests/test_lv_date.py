"""`lv_date` — viens redzamā datuma formatētājs (good-css 5. kārta, D1; 2026-10-21).

Operatora lēmums 2026-10-21: lasītājs visur redz `16.10.2026`; `<time datetime>`
paliek ISO. Agrāk bija trīs kopijas ar atšķirīgu uzvedību uz ne-ISO ievadi:
`_orchestrator.py` lambda (`"-" in s` → sagrieza jebkuru tekstu ar defisi),
`saeima._lv_date` un `politicians._dmy` (nogrieza ne-ISO tekstu līdz 10 zīmēm).

Līgums:
- `None` / `""` → `""`;
- ISO datums vai datums+laiks (`T` vai atstarpe, ar vai bez laika joslas) →
  `DD.MM.YYYY` no UZRAKSTĪTĀS datuma daļas (bez laika joslas pārrēķina — kolonnu
  pulksteni izvēlas izsaucējs, CLAUDE.md T17);
- `date`/`datetime` objekts → `DD.MM.YYYY`;
- nedēļas periods `A — B` (abi ISO datumi) → `DD.MM.YYYY — DD.MM.YYYY`;
- viss pārējais (ne-ISO teksts, jau latviskots datums, neeksistējošs datums) →
  NEMAINĪTS teksts, nevis sagriezts vai salauzts.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from src.render._common.dates import lv_date, lv_date_short, lv_dates_in_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("", ""),
        ("2026-10-16", "16.10.2026"),
        ("2026-10-16 09:30:00", "16.10.2026"),
        ("2026-10-16T09:30:00", "16.10.2026"),
        ("2026-10-16T23:30:00+00:00", "16.10.2026"),
        ("2026-10-16T23:30:00Z", "16.10.2026"),
        # viencipara stunda — dzīvie documents.published_at (42770, 42775)
        ("2020-09-28T7:53:00+03:00", "28.09.2020"),
        ("2020-09-28 7:53", "28.09.2020"),
        (date(2026, 10, 6), "06.10.2026"),
        (datetime(2026, 10, 6, 23, 59), "06.10.2026"),
        # ne-ISO teksts — nemainīts (vecā lambda: «ab-cdefghij» → «hi.cd.ab-c»)
        ("ab-cdefghij", "ab-cdefghij"),
        ("Pirmdien, plkst. 10-12", "Pirmdien, plkst. 10-12"),
        ("2026", "2026"),
        # vecā saeima/_dmy: nogrieza līdz 10 zīmēm — «oktobra beigās» → «oktobra b»
        ("oktobra beigās", "oktobra beigās"),
        # jau latvisks — nemainīts (idempotents)
        ("16.10.2026", "16.10.2026"),
        # neeksistējošs datums / ISO prefikss bez atdalītāja — nemainīts
        ("2026-13-45", "2026-13-45"),
        ("2026-10-16abc", "2026-10-16abc"),
        # pēc atstarpes jābūt laikam — citādi tas ir teksts, ne datums+laiks
        ("2026-10-16 plkst. 10", "2026-10-16 plkst. 10"),
        # nedēļas pārskata periods (blog.py display_date «A — B») — abi gali
        ("2026-10-05 — 2026-10-11", "05.10.2026 — 11.10.2026"),
        ("2026-10-05 — vakar", "2026-10-05 — vakar"),
    ],
)
def test_lv_date_contract(raw, expected):
    assert lv_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("2026-10-20 20:07:00", "20.10."),
        ("2026-10-20", "20.10."),
        # ne-datums netiek griezts (vecais veidnes `(…|lv_date)[:6]` dotu «Pirmdi»)
        ("Pirmdien", "Pirmdien"),
        ("2026-10-05 — 2026-10-11", "05.10.2026 — 11.10.2026"),
    ],
)
def test_lv_date_short_contract(raw, expected):
    assert lv_date_short(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("Dienas analīze — 2026-10-20", "Dienas analīze — 20.10.2026"),
        ("Nedēļas analīze — 2026-10-05 līdz 2026-10-11",
         "Nedēļas analīze — 05.10.2026 līdz 11.10.2026"),
        ("Bez datuma", "Bez datuma"),
        ("Jau 20.10.2026", "Jau 20.10.2026"),
        ("Nr. 2026-13-45", "Nr. 2026-13-45"),
        ("ID 12026-10-200", "ID 12026-10-200"),
    ],
)
def test_lv_dates_in_text_contract(raw, expected):
    assert lv_dates_in_text(raw) == expected
