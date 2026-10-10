"""`wiki/log-ingest.md` § Mēneši drifts silently — this is the gate that stops it.

Kāpēc šis eksistē. Mēneša faili (`wiki/log-ingest/<YYYY-MM>.md`) rotē
automātiski, bet indekss blakus tiem bija rakstīts ar roku. Faila paša piezīme
to jau bija fiksējusi: trīs mēnešus (05–07) tas rādīja tikai aprīli, tātad trīs
no četriem žurnāla failiem no turienes nebija sasniedzami. 2026-08-27 tas atkal
bija par vienu mēnesi atpalicis. Prasība «kad `append_ingest_entry()` atver
jaunu mēnesi, pievieno rindu arī šeit» ir vārti, kas paļaujas uz cilvēka atmiņu.

Šie testi būvē savu fixtūru `tmp_path` mapē, tāpēc tie nostrādā arī tad, kad
`wiki/log-ingest/` uz diska nav (mape ir gitignorēta kopš 2026-08-01) — citādi
šis būtu tieši tāds «vārts, kas nevar nokrist», kādu CLAUDE.md aizliedz.

Mutācijas pārbaude: izņem `_ensure_index_entry(p, year_month)` izsaukumu no
`_resolve_log_file()` → `test_new_month_adds_index_line` un
`test_existing_month_missing_from_index_is_healed` kļūst sarkani.
"""

from src.db import now_lv
from src.ingest_log import _ensure_index_entry, _resolve_log_file, append_ingest_entry

INDEX_HEADER = "# Ingest Log\n\n## Mēneši\n\n- [[log-ingest/2026-04|2026. gada aprīlis]]\n"


def _mk(tmp_path, index_body=INDEX_HEADER):
    d = tmp_path / "log-ingest"
    d.mkdir()
    (tmp_path / "log-ingest.md").write_text(index_body, encoding="utf-8")
    return d


def test_new_month_adds_index_line(tmp_path):
    """Atverot mēnesi caur _resolve_log_file, indeksā parādās rinda."""
    d = _mk(tmp_path)
    ym = now_lv()[:7]
    _resolve_log_file(str(d))
    text = (tmp_path / "log-ingest.md").read_text(encoding="utf-8")
    assert f"[[log-ingest/{ym}|" in text, text


def test_index_line_carries_latvian_month_label(tmp_path):
    d = _mk(tmp_path)
    assert _ensure_index_entry(d, "2026-08") is True
    text = (tmp_path / "log-ingest.md").read_text(encoding="utf-8")
    assert "- [[log-ingest/2026-08|2026. gada augusts]]" in text


def test_is_idempotent(tmp_path):
    """Otrais izsaukums nedublē rindu — un neraksta failu vispār."""
    d = _mk(tmp_path)
    assert _ensure_index_entry(d, "2026-08") is True
    assert _ensure_index_entry(d, "2026-08") is False
    text = (tmp_path / "log-ingest.md").read_text(encoding="utf-8")
    assert text.count("[[log-ingest/2026-08|") == 1


def test_existing_month_missing_from_index_is_healed(tmp_path):
    """Pašārstēšanās: mēneša fails jau ir, indeksā tā nav — nākamais ingest to pieliek.

    Tieši šī ir 2026-08-27 situācija: `2026-08.md` uz diska bija, indeksā nebija.
    """
    d = _mk(tmp_path)
    ym = now_lv()[:7]
    (d / f"{ym}.md").write_text("# Ingest Log — jau eksistē\n\n", encoding="utf-8")
    append_ingest_entry(log_path=str(d), source_name="tests", documents_added=1)
    text = (tmp_path / "log-ingest.md").read_text(encoding="utf-8")
    assert f"[[log-ingest/{ym}|" in text, text
    # Mēneša faila saturs nav pārrakstīts.
    assert "jau eksistē" in (d / f"{ym}.md").read_text(encoding="utf-8")


def test_month_lines_stay_in_order(tmp_path):
    """Jaunā rinda iet aiz pēdējās esošās mēneša rindas, ne faila beigās."""
    body = INDEX_HEADER + "\n> Piezīme, kas paliek zem saraksta.\n"
    d = _mk(tmp_path, body)
    _ensure_index_entry(d, "2026-05")
    lines = (tmp_path / "log-ingest.md").read_text(encoding="utf-8").splitlines()
    months = [i for i, ln in enumerate(lines) if ln.startswith("- [[log-ingest/")]
    note = next(i for i, ln in enumerate(lines) if ln.startswith("> Piezīme"))
    assert months == sorted(months) and max(months) < note


def test_missing_index_file_is_a_noop(tmp_path):
    """Bez indeksa faila mape strādā normāli — vārti neuzspiež jaunu failu."""
    d = tmp_path / "log-ingest"
    d.mkdir()
    assert _ensure_index_entry(d, "2026-08") is False
    assert not (tmp_path / "log-ingest.md").exists()
    f = _resolve_log_file(str(d))
    assert f.exists()


def test_legacy_single_file_mode_untouched(tmp_path):
    """Mantotais `.md` ceļš indeksu neaiztiek."""
    legacy = tmp_path / "single.md"
    f = _resolve_log_file(str(legacy))
    assert f == legacy and f.exists()
    assert not (tmp_path / "single.md.md").exists()
