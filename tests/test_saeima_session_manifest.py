"""Sesiju manifests un parity audits nedrīkst klusi izlaist sēdi.

Divi klusie robi, atrasti 2026-08-01, abi vienā formā — rīks ziņo par gadu,
kurā nav paskatījies:

1. `_p3_extract_sessions_2026-05-26.py` pazina tikai trīs etiķešu formas no
   piecām. `(As)` (ārkārtas SESIJAS sēde) un `(S)` (svinīgā sēde) neizturēja
   `int()` un tika izlaisti bez pēdām — 16 sēdes 2022.–2026. gadā, to skaitā
   **2026-07-23 ar 65 balsojumiem DB**.
2. `audit_saeima_agenda_parity.py` filtrēja manifestu pēc gada un, saņēmis
   tukšu sarakstu, izdrukāja „KOPĀ: darba kārtībā 0, trūkst 0" — tīru pārskatu
   par gadu, kuram manifestā nebija nevienas rindas. Tas ir T8 paša rīka līmenī.

Klāt vēl formāta maiņa (T12): Playwright momentuzņēmumā dienas etiķete pārcēlās
no `cell` mezgla uz `link` mezglu, tāpēc parseris pēkšņi atgrieza NULLI. Šeit ir
paraugi abos formātos — parseris nedrīkst prast tikai jaunāko.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


p3 = _load("p3_extract_sessions", "_p3_extract_sessions_2026-05-26.py")


# Vecais formāts (līdz 2026-05): dienas etiķete stāv uz `cell` mezgla.
SNAPSHOT_OLD_FORMAT = """
- generic [ref=e1]: 2025. gads.
  - table [ref=e2]:
    - row [ref=e3]:
      - cell "Janvāris" [ref=e4]
      - cell "16" [ref=e5]:
        - link "16" [ref=e6] [cursor=pointer]:
          - /url: ./DK?ReadForm&nr=11111111-1111-1111-1111-111111111111
      - cell "23(J)" [ref=e7]:
        - link "23(J)" [ref=e8] [cursor=pointer]:
          - /url: ./DK?ReadForm&nr=22222222-2222-2222-2222-222222222222
"""

# Jaunais formāts (2026-08): etiķete pārcēlusies uz `link`; `cell` ir tukšs.
SNAPSHOT_NEW_FORMAT = """
- generic [ref=e1]: 2025. gads.
  - table [ref=e2]:
    - row [ref=e3]:
      - cell "Janvāris" [ref=e4]
      - cell [ref=e5]:
        - link "16" [ref=e6] [cursor=pointer]:
          - /url: ./DK?ReadForm&nr=11111111-1111-1111-1111-111111111111
      - cell [ref=e7]:
        - link "23(J)" [ref=e8] [cursor=pointer]:
          - /url: ./DK?ReadForm&nr=22222222-2222-2222-2222-222222222222
"""


def _key(sessions):
    return sorted((s["year"], s["month"], s["day"], s["session_type"]) for s in sessions)


def test_both_snapshot_formats_parse_identically():
    """T12: formāta maiņa, ne izzušana — parserim jāprot abas formas."""
    old, old_bad = p3.parse_calendar(SNAPSHOT_OLD_FORMAT)
    new, new_bad = p3.parse_calendar(SNAPSHOT_NEW_FORMAT)
    assert not old_bad and not new_bad
    assert _key(old) == _key(new) == [
        (2025, 1, 16, "regular"),
        (2025, 1, 23, "jautajumi"),
    ]


@pytest.mark.parametrize(
    "label,expected",
    [
        ("16", "regular"),
        ("23(J)", "jautajumi"),
        ("24(A)", "arkartas"),
        ("23(As)", "arkartas_sesija"),
        ("18(S)", "sviniga"),
    ],
)
def test_every_calendar_label_form_is_recognised(label, expected):
    """`(As)` un `(S)` reiz izkrita cauri — 2026-07-23 ar 65 balsojumiem DB."""
    day = label.split("(")[0]
    snap = f"""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "{label}" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=33333333-3333-3333-3333-333333333333
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert not unparsed, f"{label!r} netika nolasīta"
    assert len(sessions) == 1
    assert sessions[0]["session_type"] == expected
    assert sessions[0]["day"] == int(day)


def test_unknown_label_is_reported_not_dropped():
    """Klusa izlaišana ir tieši tā klase, kuras dēļ manifests bija nepilnīgs."""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(Zz)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=44444444-4444-4444-4444-444444444444
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert sessions == []
    assert len(unparsed) == 1
    assert "Zz" in unparsed[0]["why"]
    assert unparsed[0]["uuid"] == "44444444-4444-4444-4444-444444444444"


def test_continued_session_cell_is_skipped_by_design():
    """„15 / 22" norāda uz agrāku UUID, kas parādās savā datuma rindā."""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Janvāris" [ref=e4]
    - cell [ref=e5]:
      - link "15 / 22" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=55555555-5555-5555-5555-555555555555
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert sessions == []
    assert unparsed == [], "turpinājuma šūna ir apzināta izlaišana, ne robs"


def test_generator_exits_nonzero_when_a_label_is_unreadable(tmp_path, capsys):
    snap = tmp_path / "page-test.yml"
    snap.write_text("""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(Zz)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
""", encoding="utf-8")
    out = tmp_path / "sessions.json"
    rc = p3.main(["--snapshot", str(snap), "--out", str(out), "--max-year", "2026"])
    assert rc == 1, "nenolasīta etiķete nedrīkst iziet ar 0"
    assert "NENOLASĪTAS ETIĶETES" in capsys.readouterr().err


def test_generator_stops_when_snapshot_is_missing(tmp_path, capsys):
    """`.playwright-mcp/` ir gitignorēta skrāpes mape — trūkstošs fails ir norma."""
    rc = p3.main(["--snapshot", str(tmp_path / "nav.yml"),
                  "--out", str(tmp_path / "o.json")])
    assert rc == 1
    assert "momentuzņēmums nav atrasts" in capsys.readouterr().err.lower()


def test_parity_audit_refuses_a_year_the_manifest_never_saw(tmp_path, monkeypatch, capsys):
    """T8 paša rīka līmenī: 0 sēžu iekšā nav tīrs gads."""
    parity = _load("audit_parity", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps([
        {"year": 2025, "month": 1, "day": 16, "session_type": "regular",
         "uuid": "1" * 36, "url": "https://example.invalid"},
    ]), encoding="utf-8")
    monkeypatch.setattr(parity, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2026"])

    rc = parity.main()
    err = capsys.readouterr().err
    assert rc == 2, "tukšs gads jāapstādina, ne jāziņo par tīru"
    assert "MANIFESTA ROBS" in err
    assert "2025" in err, "kļūdai jānosauc, kuri gadi manifestā TIEŠĀM ir"


def test_parity_audit_does_not_hit_the_network_for_a_missing_year(tmp_path, monkeypatch):
    """Apstāšanās notiek PIRMS pirmās lapas ielādes."""
    parity = _load("audit_parity2", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr(parity, "MANIFEST_PATH", manifest)

    def _boom(*_a, **_kw):
        raise AssertionError("audits nedrīkst pieskarties tīklam pie tukša gada")

    monkeypatch.setattr(parity, "_fetch", _boom)
    monkeypatch.setattr(parity, "_db_index", lambda: (set(), set()))
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2026"])
    assert parity.main() == 2


def test_parity_audit_exits_nonzero_when_an_agenda_cannot_be_fetched(
    tmp_path, monkeypatch, capsys
):
    """Neizdevies fetch NEDRĪKST ieskaitīties kā sēde bez robiem.

    `audit_session()` kļūmes ceļā atgriežas ar `agenda_votes: 0, missing: []`,
    tāpēc tāda sēde dod nulli visiem kopskaitļiem un apakšā stāv „trūkst 0" —
    un tieši to skaitli BACKLOG citē kā pierādījumu, ka gads ir pilns.
    """
    parity = _load("audit_parity3", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps([
        {"year": 2025, "month": 1, "day": 16, "session_type": "regular",
         "uuid": "1" * 36, "url": "https://example.invalid"},
        {"year": 2025, "month": 1, "day": 23, "session_type": "regular",
         "uuid": "2" * 36, "url": "https://example.invalid"},
    ]), encoding="utf-8")
    monkeypatch.setattr(parity, "MANIFEST_PATH", manifest)

    def _boom(*_a, **_kw):
        raise OSError("titania nokrita")

    monkeypatch.setattr(parity, "_fetch", _boom)
    monkeypatch.setattr(parity, "_db_index", lambda: (set(), set()))
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2025", "--delay", "0"])

    rc = parity.main()
    out = capsys.readouterr().out
    assert rc == 2, "nepilns audits nedrīkst iziet ar 0"
    assert "SEGUMS: nolasītas 0/2" in out, out
    assert "trūkst 0" in out, "vecā kopsavilkuma rinda paliek — to citē 4 vietās"


def test_parity_audit_walks_every_session_before_stopping(tmp_path, monkeypatch, capsys):
    """STOP nāk BEIGĀS: `_fetch` ir kails urlopen bez atkārtojuma, tāpēc
    pārtraukums pirmajā kļūmē noslēptu pārējo sēžu stāvokli."""
    parity = _load("audit_parity4", "audit_saeima_agenda_parity.py")
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps([
        {"year": 2025, "month": 1, "day": d, "session_type": "regular",
         "uuid": str(i) * 36, "url": "https://example.invalid"}
        for i, d in enumerate((16, 23, 30))
    ]), encoding="utf-8")
    monkeypatch.setattr(parity, "MANIFEST_PATH", manifest)

    seen = []

    def _fetch(url, *_a, **_kw):
        seen.append(url)
        raise OSError("nokrita")

    monkeypatch.setattr(parity, "_fetch", _fetch)
    monkeypatch.setattr(parity, "_db_index", lambda: (set(), set()))
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2025", "--delay", "0"])

    assert parity.main() == 2
    assert len(seen) == 3, f"visām 3 sēdēm jābūt apstaigātām, ne tikai {len(seen)}"
