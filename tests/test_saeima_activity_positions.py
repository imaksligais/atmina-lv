"""Deputātu amati no titania profila (src/saeima/activity.py, 1. uzdevums).

Nosauktās kļūmes, ko šie testi ķer:
  1. Draudzības grupas (DG1/DG2) nonāk DB — plāns tās apzināti izmet.
  2. Datums glabājas titania formā `DD.MM.YYYY` vai tukšs dtT kļūst par ''
     (nevis NULL = «amats turpinās»).
  3. Apgriezta vārda secība («Bērziņa Inga») nesaskaņojas.
  4. T1: kails uzvārds vai cits vārds ar to pašu uzvārdu («Anna Bērziņa»)
     piesaistās «Inga Bērziņa» — apakšvirkņu fallback, kas ir votes.py.
  5. Nesaskaņots deputāts pazūd klusi (nav failures) vai pazūd viņa rindas.
  6. Atkārtots skrējiens dublē rindas vai neskaita skipped_existing.
  7. T8/T12: saraksts ar < 90 deputātiem tiek pieņemts kā derīgs.
  8. Amats, kas pirmajā ielādē ilga (date_to NULL), pēc beigām paliek «pašreizējs»,
     jo date_to nav UNIQUE atslēgā.
  9. Neielādēts vai tukšs profils pazūd klusi (nav fetch_error / empty_profile).

Tīkls ir httpx.MockTransport; tikai tmp DB, ne produkcijas.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

import scripts.ingest_saeima_activity as ingest
from src.db import get_db, init_db
from src.saeima.activity import _exact_match, deputy_profile_url
from src.saeima.schema import init_saeima_tables

FIXTURES = Path(__file__).parent / "fixtures" / "saeima"
PROFILE_HTML = (FIXTURES / "dep_profile.html").read_text(encoding="utf-8")
LIST_HTML = (FIXTURES / "dep_list.html").read_text(encoding="utf-8")
INGA = "33EEA91F4258FD2FC22588E0002AE037"
ANNA = "A5791F8E6A227453C22588E0002AE051"
SRUOGIS = "7187B8382EC82785C22588E0002AE1E0"   # tukšs profils; Ašeradens → 404
# Otrs deputāts = tā pati reālā lapa ar nomainītu vārdu un unid (nesaskaņots).
ANNA_HTML = (PROFILE_HTML.replace(INGA, ANNA).replace('sname:"Bērziņa"', 'sname:"Rancāne"')
             .replace('name:"Inga"', 'name:"Anna"'))

_REAL_CLIENT = httpx.Client   # pirms jebkura monkeypatch — _mock_http drīkst saukt atkārtoti


def _mock_http(monkeypatch, pages: dict[str, str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(str(request.url))
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    monkeypatch.setattr(ingest.httpx, "Client",
                        lambda *a, **k: _REAL_CLIENT(transport=httpx.MockTransport(handler)))


def _db(tmp_path, politicians: list[tuple[str, list[str]]]) -> str:
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    for name, forms in politicians:
        db.execute("INSERT INTO tracked_politicians (name, name_forms) VALUES (?, ?)",
                   (name, json.dumps(forms, ensure_ascii=False)))
    db.commit()
    db.close()
    return path


def _stored(path):
    db = get_db(path)
    rows = [dict(r) for r in db.execute("SELECT * FROM saeima_deputy_positions ORDER BY id")]
    db.close()
    return rows


# ── tīrā loģika ────────────────────────────────────────────────────────

def test_exact_match_swaps_order_but_never_substring():
    """3. + 4. T1 — pat ja kails uzvārds IR indeksa atslēga (name_forms to mēdz nest)."""
    index = {"inga bērziņa": 1, "bērziņa": 1, "anna rancāne": 2, "toms plešs": 3}
    assert _exact_match(index, "Inga Bērziņa") == 1
    assert _exact_match(index, "Bērziņa Inga") == 1
    assert _exact_match(index, "  inga   BĒRZIŅA ") == 1
    assert _exact_match(index, "Anna Bērziņa") is None
    assert _exact_match(index, "Bērziņa") is None
    assert _exact_match(index, "Inga Bērziņa-Kalniņa") is None
    assert _exact_match(index, "Artūrs Toms Plešs") is None
    assert _exact_match(index, "") is None


# ── caur skripta ieeju ─────────────────────────────────────────────────

def test_ingest_end_to_end(tmp_path, monkeypatch, capsys):
    """1., 2., 4.–6., 8., 9. Saraksts: Bērziņa (izsekota), Rancāne (nav), Ašeradens
    (404), Sruoģis (tukšs profils). Otrais skrējiens: Bērziņas turpinātie amati beigušies."""
    path = _db(tmp_path, [("Inga Bērziņa", ["Ingai Bērziņai"]),
                          ("Anna Bērziņa", ["Bērziņa", "Rancāne"])])
    monkeypatch.setattr(ingest, "MIN_DEPUTIES", 4)
    monkeypatch.setattr(ingest, "fetch_deputy_list", lambda client, conv: LIST_HTML)
    pages = {deputy_profile_url(INGA, 14): PROFILE_HTML,
             deputy_profile_url(ANNA, 14): ANNA_HTML,
             deputy_profile_url(SRUOGIS, 14): "<html></html>"}
    _mock_http(monkeypatch, pages)

    assert ingest.main(["--what", "profiles", "--db", path, "--convocation", "14"]) == 1
    out = capsys.readouterr().out
    assert "parsed=18 stored=18 skipped_existing=0 closed=0" in out
    assert "unmatched: Anna Rancāne" in out and "unmatched: Inga Bērziņa" not in out
    assert "'kind': 'fetch_error'" in out and "Arvils Ašeradens" in out
    assert "'kind': 'empty_profile'" in out and "Vilis Sruoģis" in out
    assert out.count("failure:") == 2

    stored = _stored(path)
    assert len(stored) == 18
    assert {r["level"] for r in stored} == {"2", "3", "5", "6", "10"}
    assert not any("grupa" in r["body"] for r in stored)
    inga = [r for r in stored if r["deputy_unid"] == INGA]
    assert {r["politician_id"] for r in inga} == {1}
    assert {r["politician_id"] for r in stored if r["deputy_unid"] == ANNA} == {None}
    assert {r["source_url"] for r in inga} == {deputy_profile_url(INGA, 14)}
    assert [(r["date_from"], r["date_to"]) for r in inga if r["level"] == "10"] == [
        ("2022-11-01", "2023-09-20"), ("2025-06-19", None)]

    # Atkārtots skrējiens: Bērziņas 3 turpinātie amati (mandāts + 2 komisijas) beigušies.
    pages[deputy_profile_url(INGA, 14)] = PROFILE_HTML.replace('dtT:""', 'dtT:"02.11.2026"')
    _mock_http(monkeypatch, pages)
    assert ingest.main(["--what", "profiles", "--db", path, "--convocation", "14"]) == 1
    out = capsys.readouterr().out
    assert "parsed=18 stored=0 skipped_existing=18 closed=3" in out
    stored = _stored(path)
    assert len(stored) == 18
    assert all(r["date_to"] is not None for r in stored if r["deputy_unid"] == INGA)
    assert sum(r["date_to"] is None for r in stored if r["deputy_unid"] == ANNA) == 3


def test_short_deputy_list_stops_and_writes_nothing(tmp_path, monkeypatch, capsys):
    """7. Saraksts ar 4 deputātiem (fixture) = STOP, exit 1, profili neielādēti."""
    path = _db(tmp_path, [("Inga Bērziņa", [])])
    monkeypatch.setattr(ingest, "fetch_deputy_list", lambda client, conv: LIST_HTML)

    def _no_profiles(*a, **k):
        raise AssertionError("profilus nedrīkst ielādēt pēc STOP")

    monkeypatch.setattr(ingest, "fetch_deputy_positions", _no_profiles)
    assert ingest.main(["--what", "profiles", "--db", path]) == 1
    assert "STOP" in capsys.readouterr().out
    assert _stored(path) == []
