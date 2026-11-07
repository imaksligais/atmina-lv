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
from datetime import date
from pathlib import Path

import pytest

from src.saeima.convocation import base_url

REPO = Path(__file__).resolve().parent.parent


def _manifest(sessions: list[dict], generated_at: str | None = None) -> str:
    """Manifesta apvalks ar ģenerēšanas datumu (forma kopš 2026-09-02).

    Šie testi pārbauda GADA un FETCH vārtus, tāpēc manifestam te jābūt svaigam
    — citādi manifesta VECUMA vārti (sk. tests/test_saeima_parity_manifest_gate.py)
    apturētu skrējienu agrāk un šie testi pārbaudītu ne to, ko sola.
    """
    return json.dumps({
        "generated_at": generated_at or date.today().isoformat(),
        "sessions": sessions,
    })


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


def test_continuation_attaches_date_to_base_uuid():
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(As)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e7]:
    - cell "Septembris" [ref=e8]
    - cell [ref=e9]:
      - link "23 / 3(As)" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert unparsed == []
    assert [(s["month"], s["day"], s["continued_on"]) for s in sessions] == [(7, 23, ["2026-09-03"])]


def test_continuation_without_base_sitting_is_unparsed_not_dropped():
    # Līdz 2026-09-25 šī šūna tika izlaista klusi — tieši tā 2026-09-03 sēde
    # kļuva neredzama datuma auditam. Bez bāzes rindas → apstāties, ne izdomāt.
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
    assert [u["uuid"] for u in unparsed] == ["55555555-5555-5555-5555-555555555555"]
    assert unparsed[0]["why"] == "turpinājums bez bāzes sēdes šajā momentuzņēmumā"


def test_one_sitting_continued_on_two_dates_keeps_both_sorted():
    """Viena UUID divi turpinājumi — abi datumi, sakārtoti, bez dublikātiem.
    Kalendāra secībā vēlākais turpinājums stāv PIRMS agrākā, lai kārtošana
    būtu pārbaudīta, ne nejauši pareiza."""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(As)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e7]:
    - cell "Septembris" [ref=e8]
    - cell [ref=e9]:
      - link "23 / 10(As)" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
    - cell [ref=e11]:
      - link "23 / 3(As)" [ref=e12] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert unparsed == []
    assert len(sessions) == 1
    assert sessions[0]["continued_on"] == ["2026-09-03", "2026-09-10"]


def test_chain_label_attaches_last_day_to_owner():
    """`29 / 5 / 12`: pirmais = bāzes diena (01-29), pēdējais = šī šūna (02-12);
    vidējais (02-05) ir savā šūnā `29 / 5`."""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Janvāris" [ref=e4]
    - cell [ref=e5]:
      - link "29" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=99999999-9999-9999-9999-999999999999
  - row [ref=e7]:
    - cell "Februāris" [ref=e8]
    - cell [ref=e9]:
      - link "29 / 5" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=99999999-9999-9999-9999-999999999999
    - cell [ref=e11]:
      - link "29 / 5 / 12" [ref=e12] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=99999999-9999-9999-9999-999999999999
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert unparsed == []
    assert [(s["month"], s["day"], s["continued_on"]) for s in sessions] == [
        (1, 29, ["2026-02-05", "2026-02-12"])]


@pytest.mark.parametrize("label,month_cell", [
    ("22 / 3(As)", "Septembris"),  # pirmais skaitlis ≠ īpašnieka dienai (23)
    ("23 / 3(As)", "Jūlijs"),      # „turpinājums" 07-03 ir PIRMS bāzes 07-23
])
def test_continuation_that_contradicts_its_owner_is_unparsed_not_attached(label, month_cell):
    snap = f"""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(As)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e7]:
    - cell "{month_cell}" [ref=e8]
    - cell [ref=e9]:
      - link "{label}" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert len(sessions) == 1 and "continued_on" not in sessions[0]
    assert len(unparsed) == 1
    assert "semantika nolasīta nepareizi" in unparsed[0]["why"]


def test_same_label_in_two_months_keeps_both_dates():
    """Dedup atslēgā jābūt gadam + mēnesim: `23 / 3` augustā UN septembrī ir
    divas dažādas dienas, ne atkārtots mezgls. Ar atslēgu (uuid, etiķete)
    otrā diena pazuda klusi (`unparsed == []`)."""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e7]:
    - cell "Augusts" [ref=e8]
    - cell [ref=e9]:
      - link "23 / 3" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e11]:
    - cell "Septembris" [ref=e12]
    - cell [ref=e13]:
      - link "23 / 3" [ref=e14] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
"""
    sessions, unparsed = p3.parse_calendar(snap)
    assert unparsed == []
    assert sessions[0]["continued_on"] == ["2026-08-03", "2026-09-03"]


def test_repeated_orphan_continuation_node_is_reported_once():
    """Turpinājumi iet garām `seen`, tāpēc atkārtots mezgls nedrīkst dubultot."""
    node = """
    - cell [ref=e5]:
      - link "15 / 22" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=55555555-5555-5555-5555-555555555555
"""
    snap = """
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Janvāris" [ref=e4]""" + node + node
    sessions, unparsed = p3.parse_calendar(snap)
    assert sessions == []
    assert len(unparsed) == 1


def test_ordinary_entry_has_no_continued_on_key():
    """Bez turpinājuma rinda paliek baitu-identiska vecajai formai."""
    sessions, _ = p3.parse_calendar(SNAPSHOT_NEW_FORMAT)
    assert all("continued_on" not in s for s in sessions)


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


def test_generator_prints_the_continuation_denominator(tmp_path, capsys):
    """Turpinājumu skaits jāredz izdrukā: „0 piesaistīti" ir signāls, ne klusums."""
    snap = tmp_path / "page-test.yml"
    snap.write_text("""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Jūlijs" [ref=e4]
    - cell [ref=e5]:
      - link "23(As)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
  - row [ref=e7]:
    - cell "Septembris" [ref=e8]
    - cell [ref=e9]:
      - link "23 / 3(As)" [ref=e10] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=66666666-6666-6666-6666-666666666666
    - cell [ref=e11]:
      - link "9 / 17" [ref=e12] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=77777777-7777-7777-7777-777777777777
""", encoding="utf-8")
    out = tmp_path / "sessions.json"
    rc = p3.main(["--snapshot", str(snap), "--out", str(out), "--max-year", "2026"])
    assert rc == 1, "turpinājums bez bāzes sēdes = nepilnīgs manifests"
    assert "Turpinājumi: piesaistīti 1, neparsēti 1" in capsys.readouterr().out


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
    manifest.write_text(_manifest([
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
    manifest.write_text(_manifest([]), encoding="utf-8")
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
    manifest.write_text(_manifest([
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
    manifest.write_text(_manifest([
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


# ---------------------------------------------------------------------------
# Dzīvā (tās pašas dienas) sēde kalendārā — 2026-09-16
# ---------------------------------------------------------------------------
#
# Trešais klusais robs, tā pati forma: 2026-09-10 sēdē bija 16 balsojumi, bet
# `audit_saeima_agenda_parity.py --dates 2026-09-10` izdrukāja „DK=0, trūkst 0".
# Cēlonis nav auditā — kalendārs KĀRTĒJAI dienai renderē `./DK?ReadForm&active=1`
# (nav `nr={UUID}`), `_URL_RE` to nesatvēra, un diena manifestā neiekļuva vispār.
# Diena bez manifesta rindas auditam neeksistē, tāpēc svaiguma vārti izgāja
# cauri ar nepareizu saucēju — tieši tā klase, pret kuru vārti pastāv.


class TestLiveSessionInCalendar:
    @staticmethod
    def _snap(url: str) -> str:
        return f"""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Septembris" [ref=e4]
    - cell [ref=e5]:
      - link "16" [ref=e6] [cursor=pointer]:
        - /url: {url}
"""

    @pytest.mark.parametrize("param", ["active", "actual"])
    def test_live_session_is_parsed_not_dropped(self, param):
        sessions, unparsed = p3.parse_calendar(self._snap(f"./DK?ReadForm&{param}=1"))
        assert unparsed == []
        assert len(sessions) == 1, "dzīvā diena nedrīkst pazust no manifesta"
        s = sessions[0]
        assert (s["year"], s["month"], s["day"]) == (2026, 9, 16)
        assert s["session_type"] == "regular"
        assert s["uuid"] is None, "dzīvajai sēdei UUID vēl NAV — to nedrīkst izdomāt"
        assert s["live"] is True
        assert s["url"] == f"{base_url()}/DK?ReadForm&{param}=1"

    def test_live_row_does_not_disturb_the_normal_rows(self):
        snap = self._snap("./DK?ReadForm&active=1") + """
  - row [ref=e9]:
    - cell "Septembris" [ref=e10]
    - cell [ref=e11]:
      - link "10" [ref=e12] [cursor=pointer]:
        - /url: ./DK?ReadForm&nr=77777777-7777-7777-7777-777777777777
"""
        sessions, unparsed = p3.parse_calendar(snap)
        assert unparsed == []
        assert _key(sessions) == [(2026, 9, 10, "regular"), (2026, 9, 16, "regular")]
        by_day = {s["day"]: s for s in sessions}
        assert by_day[10]["uuid"] == "7" * 8 + "-7777-7777-7777-" + "7" * 12
        assert "live" not in by_day[10], "parastā rinda paliek baitu-identiska"
        assert by_day[16]["uuid"] is None

    def test_two_live_days_in_one_year_are_both_kept(self):
        """`seen` dedup atslēga ir (gads, uuid) — bez labojuma otrā dzīvā diena
        sakristu ar pirmo un pazustu klusi."""
        snap = self._snap("./DK?ReadForm&active=1") + """
  - row [ref=e9]:
    - cell "Oktobris" [ref=e10]
    - cell [ref=e11]:
      - link "2" [ref=e12] [cursor=pointer]:
        - /url: ./DK?ReadForm&actual=1
"""
        sessions, unparsed = p3.parse_calendar(snap)
        assert unparsed == []
        assert _key(sessions) == [(2026, 9, 16, "regular"), (2026, 10, 2, "regular")]

    def test_live_session_keeps_its_label_suffix(self):
        sessions, _ = p3.parse_calendar("""
- generic [ref=e1]: 2026. gads.
  - row [ref=e3]:
    - cell "Septembris" [ref=e4]
    - cell [ref=e5]:
      - link "16(J)" [ref=e6] [cursor=pointer]:
        - /url: ./DK?ReadForm&active=1
""")
        assert len(sessions) == 1
        assert sessions[0]["session_type"] == "jautajumi"
        assert sessions[0]["uuid"] is None
