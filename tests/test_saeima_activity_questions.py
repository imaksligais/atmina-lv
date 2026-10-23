"""Deputātu jautājumi un pieprasījumi no titania LIVS (src/saeima/activity.py, 3. uzdevums).

Nosauktās kļūmes, ko šie testi ķer:
  1. Saraksta nosaukumā paliek HTML entītijas («bud&#382;eta») vai iekavas
     («(iesniegts …)») nogriež rindu — rinda pazūd vai doc_nr nobīdās.
  2. kind sajaukts: pieprasījums glabājas kā jautājums.
  3. Adresāta amata prefikss netiek nogriezts («Iekšlietu ministrs Jānis
     Dombrava» nekad nesaskaņojas) vai iestāde tiek uzskatīta par personu.
  4. Saliktais amats ar komatu («Ministru prezidenta biedrs, tieslietu
     ministrs …») sadalās divos adresātos.
  5. Pieprasījumā tiek nolasīts pirmais addBlock (atbildīgā komisija), nevis
     adresāti; otrās sēdes «Rezultāts» tiek pazaudēts.
  6. Apgriezta iesniedzēja secība («Šuvajevs Andris») nesaskaņojas; T1: līdzīgs,
     bet cits uzvārds saskaņojas pēc apakšvirknes.
  7. Nesaskaņots vārds pazūd klusi (nav failures ar role + doc_nr).
  8. Atkārtots skrējiens dublē jautājumu vai saites; statusa maiņa netiek
     ierakstīta; nosaukums tiek pārrakstīts.
  9. T8/T12: saraksts ar 0 ierakstiem tiek pieņemts kā «nav jautājumu».
 10. Neparsējama detaļa pazūd klusi (nav fetch_error).
 11. Trīsdaļīgs adresāta vārds («Artūrs Toms Plešs») apgriezts līdz pēdējiem
     diviem un saskaņots ar citu cilvēku («Toms Plešs»; `_exact_match` puse —
     test_saeima_activity_positions.py).

Tīkls ir httpx.MockTransport; tikai tmp DB, ne produkcijas.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

import scripts.ingest_saeima_activity as ingest
from src.db import get_db, init_db
from src.saeima.activity import (
    addressee_person_name,
    question_detail_url,
    question_list_url,
    split_addressees,
)

FIXTURES = Path(__file__).parent / "fixtures" / "saeima"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# Detaļas: trīs reālas lapas; 1/J14 = pārveidota lapa, 3/J14 un 2/P14 → 404.
PAGES = {
    question_list_url("jautajums", 14): _read("questions_list.html"),
    question_list_url("pieprasijums", 14): _read("requests_list.html"),
    question_detail_url("BCB8BAD2B5EAB639C2258912002DAEE8", 14): _read("question_2_J14.html"),
    question_detail_url("B0DA0DFA5424B572C2258E7C0044A389", 14): _read("question_257_J14.html"),
    question_detail_url("205C179FC2DCD9B1C225894F004AE505", 14): _read("request_1_P14.html"),
    question_detail_url("99D8ECF1FD1A6069C2258912002D21A1", 14): "<html>pārveidots</html>",
}

_REAL_CLIENT = httpx.Client   # pirms jebkura monkeypatch — _mock_http drīkst saukt atkārtoti


def _mock_http(monkeypatch, pages: dict[str, str]) -> list[str]:
    """Atgriež pieprasīto URL sarakstu (lai pārbaudītu, kas NETIKA ielādēts)."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        body = pages.get(str(request.url))
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    monkeypatch.setattr(ingest.httpx, "Client",
                        lambda *a, **k: _REAL_CLIENT(transport=httpx.MockTransport(handler)))
    return requested


def _db(tmp_path, politicians: list[str]) -> str:
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    for name in politicians:
        db.execute("INSERT INTO tracked_politicians (name, name_forms) VALUES (?, ?)",
                   (name, json.dumps([name], ensure_ascii=False)))
    db.commit()
    db.close()
    return path


def _query(path, sql):
    db = get_db(path)
    rows = [dict(r) for r in db.execute(sql)]
    db.close()
    return rows


# ── tīrā parsēšana ─────────────────────────────────────────────────────

def test_addressee_person_name_and_split():
    """3., 4., 11."""
    assert split_addressees(
        "Ministru prezidenta biedrs, tieslietu ministrs Jānis Bordāns, Valsts kontrole"
    ) == ["Ministru prezidenta biedrs, tieslietu ministrs Jānis Bordāns", "Valsts kontrole"]
    assert addressee_person_name("Ministru prezidenta biedrs, tieslietu ministrs Jānis Bordāns") \
        == "Jānis Bordāns"
    assert addressee_person_name("Valsts kontrole") is None
    assert addressee_person_name("Ministru kabinets") is None
    assert addressee_person_name("Labklājības ministre Inese Skujiņa-Rubene") \
        == "Inese Skujiņa-Rubene"
    assert addressee_person_name("Vides aizsardzības un reģionālās attīstības ministrs "
                                 "Artūrs Toms Plešs") == "Artūrs Toms Plešs"
    assert addressee_person_name("Veselības ministrs Hosams Abu Meri") == "Hosams Abu Meri"
    assert addressee_person_name("Latvijas Bankas prezidents Mārtiņš Kazāks") == "Mārtiņš Kazāks"


# ── caur skripta ieeju ─────────────────────────────────────────────────

def test_ingest_end_to_end(tmp_path, monkeypatch, capsys):
    """1., 2., 3., 5.–8., 10. Izsekoti: Šuvajevs (apgriezts iesniedzējs), Dombrava
    (adresāts ar amatu), Čudars (pieprasījuma adresāts pēc etiķetes), Briškensons
    (apakšvirknes slazds «Briškens Kaspars» — NEdrīkst saistīties)."""
    path = _db(tmp_path, ["Andris Šuvajevs", "Jānis Dombrava", "Raimonds Čudars",
                          "Kaspars Briškensons"])
    results = []

    def _spy(*a, **k):
        res = _real_store(*a, **k)
        results.append(res)
        return res
    _real_store = ingest.store_questions
    monkeypatch.setattr(ingest, "store_questions", _spy)
    _mock_http(monkeypatch, PAGES)

    assert ingest.main(["--what", "questions", "--db", path, "--convocation", "14"]) == 1
    out = capsys.readouterr().out
    assert "parsed=3 stored=3 skipped_existing=0" in out
    res = results[-1]
    assert sorted(f["doc_nr"] for f in res.failures if f["kind"] == "fetch_error") == [
        "1/J14", "2/P14", "3/J14"]
    unmatched = [f for f in res.failures if f["kind"] == "unmatched_name"]
    assert len(res.failures) == len(unmatched) + 3
    assert len(unmatched) == 22
    assert {"kind": "unmatched_name", "name": "Briškens Kaspars", "role": "submitter",
            "doc_nr": "257/J14"} in unmatched
    assert {"kind": "unmatched_name", "name": "Baiba Braže", "role": "addressee",
            "doc_nr": "257/J14"} in unmatched

    q = {r["doc_nr"]: r for r in _query(path, "SELECT * FROM saeima_questions")}
    assert sorted(q) == ["1/P14", "2/J14", "257/J14"]
    assert (q["2/J14"]["kind"], q["2/J14"]["status"], q["2/J14"]["submitted_date"],
            q["2/J14"]["result"]) == ("jautajums", "Izskatīts", "2022-12-08", "Atbildēts rakstveidā")
    assert q["2/J14"]["title"].startswith("Par valsts budžeta 2023.gadam")
    assert q["2/J14"]["title"].endswith("(iesniegts 08.12.2022.)")
    assert (q["1/P14"]["kind"], q["1/P14"]["submitted_date"], q["1/P14"]["result"]) == (
        "pieprasijums", "2023-02-07", "Nodots Pieprasījumu komisijai; Atsaukts")
    assert q["257/J14"]["result"].startswith("Atbilde pārcelta uz nākamo sēdi")
    assert len(q["257/J14"]["unid"]) == 32

    links_sql = """SELECT q.doc_nr, p.name, qp.role FROM saeima_question_politicians qp
                   JOIN saeima_questions q ON q.id = qp.question_id
                   JOIN tracked_politicians p ON p.id = qp.politician_id
                   ORDER BY q.doc_nr, p.name"""
    expected_links = [
        {"doc_nr": "1/P14", "name": "Andris Šuvajevs", "role": "submitter"},
        {"doc_nr": "1/P14", "name": "Raimonds Čudars", "role": "addressee"},
        {"doc_nr": "257/J14", "name": "Andris Šuvajevs", "role": "submitter"},
        {"doc_nr": "257/J14", "name": "Jānis Dombrava", "role": "addressee"},
    ]
    assert _query(path, links_sql) == expected_links

    # Atkārtots skrējiens: 257/J14 statuss, rezultāts un (sarakstā) nosaukums mainījušies.
    pages = dict(PAGES)
    lst = question_list_url("jautajums", 14)
    pages[lst] = pages[lst].replace('dvRow_LPView("Iesniegts","Par R&#299;gas',
                                    'dvRow_LPView("Izskat&#299;ts","CITS NOSAUKUMS Par R&#299;gas')
    det = question_detail_url("B0DA0DFA5424B572C2258E7C0044A389", 14)
    pages[det] = pages[det].replace("Atbilde p&#257;rcelta uz n&#257;kamo s&#275;di:", "Atbild&#275;ts:")
    assert pages[lst] != PAGES[lst] and pages[det] != PAGES[det]
    _mock_http(monkeypatch, pages)

    assert ingest.main(["--what", "questions", "--db", path, "--convocation", "14"]) == 1
    assert "parsed=3 stored=0 skipped_existing=3" in capsys.readouterr().out
    q = {r["doc_nr"]: r for r in _query(path, "SELECT * FROM saeima_questions")}
    assert len(q) == 3
    assert q["257/J14"]["status"] == "Izskatīts"
    assert q["257/J14"]["result"].startswith("Atbildēts:")
    assert q["257/J14"]["title"].startswith("Par Rīgas domes deputātes")
    assert _query(path, links_sql) == expected_links


def test_empty_list_is_stop(tmp_path, monkeypatch, capsys):
    """9. Tukšs pieprasījumu skats → STOP, exit 1, detaļas netiek ielādētas, nekas neierakstīts."""
    path = _db(tmp_path, [])
    requested = _mock_http(monkeypatch, {**PAGES, question_list_url("pieprasijums", 14): "<html></html>"})

    assert ingest.main(["--what", "questions", "--db", path, "--convocation", "14"]) == 1
    out = capsys.readouterr().out
    assert "STOP" in out and "pieprasijums" in out
    assert sorted(requested) == sorted([question_list_url("jautajums", 14),
                                        question_list_url("pieprasijums", 14)])
    assert _query(path, "SELECT COUNT(*) n FROM saeima_questions") == [{"n": 0}]
