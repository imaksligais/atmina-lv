"""titania posmu tabulas parsētājs.

Kļūme, ko tests noķer: parsētājs pazaudē vai sajauc «Rezultāts» rindu ar
posmu kolonnām — tad steidzama likumprojekta 2. lasījuma «Likums» netiek
atrasts, un `scripts/backfill_bill_stage_result_from_titania.py` neko nelabo
(vai labo nepareizu posmu). Fiksācija: 1269/Lp14 lapa, saglabāta 2026-10-19.
"""

from pathlib import Path

from src.saeima.titania import parse_stage_table

FIXTURE = Path(__file__).parent / "fixtures" / "titania_1269_Lp14.html"


def test_urgent_bill_second_reading_is_likums():
    stages = parse_stage_table(FIXTURE.read_bytes().decode("utf-8"))
    by_name = {s["name"]: s for s in stages}
    assert by_name["2. lasījums"] == {
        "name": "2. lasījums", "date": "2026-04-16", "result": "Likums"}
    assert by_name["1. lasījums"]["result"] == "Pieņemts"
    assert "3. lasījums" not in by_name
