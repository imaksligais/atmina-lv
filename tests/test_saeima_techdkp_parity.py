"""Apakšpunktu balsojumi (`getTechDKP`) paritātes auditā — `--tech`.

Robs, kas to prasīja: dzīvā sēdes dienā priekšlikumu, «nodot komisijai» un
līdzīgi apakšpunktu balsojumi nav redzami lapā, ko audits lasa; tie ir tikai
`getTechDKP` atbildē punktam ar `hasTechChilds`. Rokas paritāte 2026-09-10
palaida garām 5 no 21 balsojuma, 2026-09-17 — 5 no 37.

Fikstūras ir apgriezti īsti titania fragmenti (2026-09-17, 42. punkts,
1481/Lp14, 5 priekšlikumu balsojumi): `tests/fixtures/saeima/techdkp/`.
Tīkls testos ir aizvērts — `_fetch` aizstāj vārdnīca pēc URL.

Esošie testi to nesedz: `test_saeima_live_agenda_pattern4.py` pārbauda tikai
vienas lapas balsojumus (bez `getTechDKP`), `test_saeima_parity_manifest_gate.py`
un `test_saeima_parity_continuation.py` — manifesta vārtus bez `--tech`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures" / "saeima" / "techdkp"
BASE = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"
UUID = "1f916d52-b070-4078-b3b5-7e95872f1df8"
POINT = "05E7CEB658B136C6C2258E7C00459DBD"  # 42. punkts, [5] `nr=` formā

PARENT_VOTE = f"{BASE}/0/26DE8165E5521573C2258E7C00459DC5?OpenDocument"
SUB_VOTES = [f"{BASE}/0/{h}?OpenDocument" for h in (
    "BAB1544FD5D1456DC2258E7C00459DC7",   # 4. priekšlikums
    "5B95F51AB8DC8C3DC2258E7C00459DC9",   # 10.
    "11F7487671C0DFE7C2258E7C00459DD1",   # 15.
    "DFC4FAD0F4A7D09BC2258E7C00459DD3",   # 21.
    "2C4604D3860A467FC2258E7C00459DD5",   # 22. — šo DB «nav»
)]
# Sintētiska balsojuma lapa tikai trūkstošajam 22. priekšlikumam (datums, laiks, motīvs).
MISSING_VOTE_PAGE = (
    "<span>Balso&#353;anas mot&#299;vs: </span><b>Latgales vēstniecības GORS likums "
    "(1481/Lp14), 22. priekšlikums</b> par 17, pret 65, atturas 0 "
    "Datums: </span><b>17.09.2026 12:20:41 </b>"
)


def _fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def _tech_url(level: int = 1, actual: bool = False) -> str:
    return (f"{BASE}/getTechDKP?OpenAgent&dkp={POINT}&tLevel={level}"
            + ("&actual=1" if actual else ""))


def _audit(tmp_path, monkeypatch, pages: dict[str, str], session: dict,
           db_urls: set[str], argv: list[str]):
    spec = importlib.util.spec_from_file_location(
        f"audit_techdkp_{len(pages)}_{id(pages)}",
        REPO / "scripts" / "audit_saeima_agenda_parity.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    calls: list[str] = []

    def fetch(url, *_a, **_kw):
        calls.append(url)
        if url not in pages:
            raise OSError(f"tīkls testā ir aizvērts: {url}")
        return pages[url]

    monkeypatch.setattr(mod, "_fetch", fetch)
    monkeypatch.setattr(mod, "_db_index", lambda: (set(), set(db_urls)))
    monkeypatch.setattr(mod, "_db_url_moments", lambda: {})
    manifest = tmp_path / "sessions.json"
    manifest.write_text(json.dumps({"generated_at": date.today().isoformat(),
                                    "sessions": [session]}), encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(sys, "argv", ["audit", "--year", "2026", "--delay", "0", *argv])
    return mod.main(), calls


def _session(day: int = 17, uuid: str | None = UUID) -> dict:
    s = {"year": 2026, "month": 9, "day": day, "session_type": "regular",
         "uuid": uuid, "convocation": 14,
         "url": f"{BASE}/DK?ReadForm&" + (f"nr={uuid}" if uuid else "active=1")}
    if not uuid:
        s["live"] = True
    return s


def test_sub_item_vote_missing_from_db_is_found_only_through_getTechDKP(
        tmp_path, monkeypatch, capsys):
    """Lapa rāda tikai punkta balsojumu; 22. priekšlikums ir tikai getTechDKP atbildē.

    Bez `getTechDKP` sekošanas audits redz 1 balsojumu, tas ir DB, un iznākums
    ir zaļš «trūkst 0» — tieši rokas paritātes kļūda.
    """
    pages = {
        f"{BASE}/DK?ReadForm&nr={UUID}": _fx("agenda_item42_2026-09-17.html"),
        _tech_url(): _fx("getTechDKP_item42_2026-09-17.html"),
        SUB_VOTES[-1]: MISSING_VOTE_PAGE,
    }
    rc, calls = _audit(tmp_path, monkeypatch, pages, _session(),
                       {PARENT_VOTE, *SUB_VOTES[:-1]}, ["--dates", "2026-09-17", "--tech"])
    out = capsys.readouterr().out

    assert _tech_url() in calls, "getTechDKP punktam ar hasTechChilds netika atvērts"
    assert "KOPĀ: darba kārtībā 6, trūkst 1" in out, out[-600:]
    assert "2026-09-17 12:20:41" in out and "22. priekšlikums" in out, out[-600:]
    assert "tikai getTechDKP 5" in out
    assert rc == 0  # robi iet ar 0 + sarakstu (skripta līgums), ne ar 2


def test_flagged_point_whose_getTechDKP_renders_nothing_stops_with_exit_2(
        tmp_path, monkeypatch, capsys):
    """Punkts saka «ir apakšpunkti», atbildē nav nevienas rindas → STOP, ne «trūkst 0»."""
    pages = {
        f"{BASE}/DK?ReadForm&nr={UUID}": _fx("agenda_item42_2026-09-17.html"),
        _tech_url(): _fx("getTechDKP_no_rows.html"),
    }
    rc, _calls = _audit(tmp_path, monkeypatch, pages, _session(),
                        {PARENT_VOTE, *SUB_VOTES}, ["--dates", "2026-09-17", "--tech"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "getTechDKP" in captured.err and POINT in captured.err


@pytest.mark.parametrize("day, expect_rc", [(17, 0), (24, 2)])
def test_live_session_is_audited_through_dashed_dkid_for_its_own_date(
        tmp_path, monkeypatch, capsys, day, expect_rc):
    """Dzīvā rinda (`uuid=None`) ar `--tech`: DkId nāk bez domuzīmēm, un `nr=` bez
    tām atdod tukšu darba kārtību (mērīts 2026-11-10); `active=1` rīt rāda citu
    sēdi, tāpēc `nr={DkId}` punktu datumam jāsakrīt ar prasīto dienu."""
    live = _session(day=day, uuid=None)
    pages = {
        live["url"]: 'var actualXML_DkId="1f916d52b0704078b3b57e95872f1df8";\n'
                     'drawDKP_Hd("Saeimas sēde","","","IsActual","1");\n',
        f"{BASE}/DK?ReadForm&nr={UUID}": _fx("agenda_item42_2026-09-17.html"),
        _tech_url(actual=True): _fx("getTechDKP_item42_2026-09-17.html"),
    }
    rc, calls = _audit(tmp_path, monkeypatch, pages, live,
                       {PARENT_VOTE, *SUB_VOTES}, ["--dates", f"2026-09-{day}", "--tech"])
    captured = capsys.readouterr()

    assert rc == expect_rc, captured.err[-800:]
    if expect_rc == 0:
        assert "KOPĀ: darba kārtībā 6, trūkst 0" in captured.out
        assert _tech_url(actual=True) in calls
    else:
        assert "citu sēdi" in captured.err
