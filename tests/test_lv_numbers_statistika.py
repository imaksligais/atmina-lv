"""Statistikas lapu redzamie skaitļi ir LV pierakstā (2026-10-28).

Kļūme, ko tests noķer: `src/csp/tables.py` formatētāji drukāja angliski —
«-1,291», «€1,946», «5.1%», «1.83M» — kartītēs, detaļu galvā un datu tabulā.
LV: tūkstoši ar NBSP, decimālkomats, «5,1 %», «1 946 €».

Pārbauda tikai redzamo tekstu (bez `<script>` JSON blokiem, kur skaitļi ir
mašīnlasāmi). Saucējs: vismaz viens LV-formas skaitlis katrā lapā, citādi
tukša lapa izietu cauri.
"""
from __future__ import annotations

import re

import pytest

bs4 = pytest.importorskip("bs4")

EN_THOUSANDS = re.compile(r"\d,\d{3}(?!\d)")
EN_PERCENT = re.compile(r"\d\.\d+\s?%")
LV_FORM = re.compile(r"\d \d{3}|\d,\d+ %|\d,\d+ (?:milj|mljrd)\.")


def _visible_text(path) -> str:
    soup = bs4.BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for s in soup.find_all(["script", "style"]):
        s.decompose()
    return soup.get_text(" ", strip=True)


def test_statistika_numbers_are_latvian(rendered_site):
    pages = [rendered_site / "statistika.html",
             *sorted((rendered_site / "statistika").glob("*.html"))]
    assert len(pages) == 11, f"gaidītas 11 statistikas lapas, atrastas {len(pages)}"
    errors = []
    for page in pages:
        text = _visible_text(page)
        bad = EN_THOUSANDS.findall(text) + EN_PERCENT.findall(text)
        if bad:
            errors.append(f"{page.name}: angliski {bad[:3]}")
        if not LV_FORM.search(text):
            errors.append(f"{page.name}: 0 LV-formas skaitļu — lapa neko nepārbauda")
    assert not errors, "\n".join(errors)
