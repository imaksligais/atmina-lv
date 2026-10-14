from __future__ import annotations

import importlib.util
from pathlib import Path

from src.jev_filter import JevStats

_spec = importlib.util.spec_from_file_location(
    "jev_contradiction_shortlist",
    Path(__file__).resolve().parent.parent / "scripts" / "jev_contradiction_shortlist.py")
sl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sl)


def test_format_shortlist_denominator_first_then_rows_desc_by_p():
    pairs = [
        {"old_id": 1, "new_id": 2, "p": 0.61, "old_date": "2025-01-10", "new_date": "2025-03-01",
         "old_topic": "Nodokļi", "new_topic": "Nodokļi", "old_stance": "Par", "new_stance": "Pret"},
        {"old_id": 3, "new_id": 4, "p": 0.93, "old_date": "2024-05-01", "new_date": "2025-06-01",
         "old_topic": "Rail Baltica", "new_topic": "Transports", "old_stance": "Jāceļ", "new_stance": "Jāaptur"},
        {"old_id": 5, "new_id": 6, "p": 0.20, "old_date": "2024-01-01", "new_date": "2024-02-01",
         "old_topic": "X", "new_topic": "X", "old_stance": "a", "new_stance": "b"},
    ]
    text = sl.format_shortlist("Testa Persona", 12, pairs, 0.6, JevStats(requests=1, input_tokens=2000))
    lines = text.splitlines()
    assert lines[0].startswith("# Testa Persona — Jev īsais saraksts")
    assert "pozīcijas 12, bez datuma izlaistas 0, kandidātu pāri 3, virs θ=0.6: 2" in text
    # rindas dilstoši pēc p; pāris zem θ nav tabulā
    i93, i61 = text.index("0.93"), text.index("0.61")
    assert i93 < i61 and "0.20" not in text
    assert "#3 → #4" in text and "2024-05-01 → 2025-06-01" in text
    assert "Rail Baltica → Transports" in text


def test_format_shortlist_undated_count_appears_in_denominator_line():
    text = sl.format_shortlist("Testa Persona", 12, [], 0.6, JevStats(), undated=5)
    assert "pozīcijas 12, bez datuma izlaistas 5, kandidātu pāri 0, virs θ=0.6: 0" in text
