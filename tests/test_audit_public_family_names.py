"""Vārti `scripts/audit_public_family_names.py` noķer radinieka vārdu arī tad, ja
to šķeļ HTML tagi, JSON to raksta \\uXXXX formā, secība apgriezta vai trūkst
garumzīmju (Astra pārskats 2026-11-27: iepriekšējā versija šos palaida garām)."""

from pathlib import Path

from scripts.audit_public_family_names import find_hits
from src.vad.family import name_variants


def test_gate_catches_spelling_and_markup_variants(tmp_path: Path):
    names = {v: {1} for v in name_variants("Anna Bērziņa/Ozola")}
    (tmp_path / "a.html").write_text("<td>Anna <b>Bērziņa</b></td>", encoding="utf-8")
    (tmp_path / "b.json").write_text('{"x": "Ozola Anna"}'.replace("Ozola", "\\u004fzola"),
                                     encoding="utf-8")
    (tmp_path / "c.html").write_text("dāvinājums no ANNA BERZINA, ,", encoding="utf-8")
    (tmp_path / "d.html").write_text("Anna Ozoliņa un Jānis Bērziņš", encoding="utf-8")
    n_files, hits = find_hits(tmp_path, names)
    assert n_files == 4
    assert sorted(f for f, _name, _ctx in hits) == ["a.html", "b.json", "c.html"]
