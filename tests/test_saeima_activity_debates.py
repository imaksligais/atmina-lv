"""Debašu uzstāšanās no data.gov.lv `-deb.xml` (src/saeima/activity.py, 2. uzdevums).

Nosauktās kļūmes, ko šie testi ķer:
  1. Tukšā sēde (182 B, `DK_STATUS 8`, nav `<DEBATES>`) tiek uzskatīta par kļūdu
     — tā ir «debašu nebija», skaita empty_sessions.
  2. `#`-masīvu garuma nesakritība glabā daļēju DKP — indeksu nobīde piesaistītu
     runu citam deputātam. Jāiet failures, NEVIENA tā rinda neglabājas.
  3. `MM:SS` / `H:MM:SS` nepārvēršas sekundēs; nesaprotams laiks kļūst par skaitli.
  4. Ministram (tukša frakcija) glabājas '' nevis NULL (normalize_faction apiets — T6).
  5. Nesaskaņots runātājs pazūd klusi vai pazūd viņa rinda.
  6. Atkārtots skrējiens dublē rindas vai neskaita skipped_existing.
  7. session_date netiek aizpildīts no blakus `-dkp.xml` DKDATE vai tiek ņemts
     no CITAS sēdes dkp (pāris pēc vārda nav pārbaudīts pret DK_ID).
  8. T8/T12: 0 `-deb` resursu CKAN atbildē tiek pieņemts kā tukšs rezultāts.
  9. Punkts pārnests uz citu sēdi (tas pats dkp_id): avota atkārtota runa tiek
     dublēta, VAI cita runātāja runa tajā pašā vietā pazūd klusi (23.07.2026 ārkārtas sesija).
 10. Apakšpunkts (`00021.0000.901`, tukšs LIVSDOCUMENTID) glabājas bez likumprojekta
     numura un ar bezjēdzīgu nosaukumu — vecāks jāizšķir no pilnā `-dkp.xml`
     (2026-10-06: 42 % runu); bez dkp → paliek kā ir un tiek skaitīts.
 11. Iknedēļas skrējiens atkal lejupielādē sen glabātas sēdes (desmitiem MB).

Tīkls ir httpx.MockTransport; tikai tmp DB, ne produkcijas.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

import scripts.ingest_saeima_activity as ingest
from src.db import get_db, init_db
from src.saeima.activity import CKAN_PACKAGE_URL, _duration_sec, parse_debates

FIXTURES = Path(__file__).parent / "fixtures" / "saeima"
SESSION_XML = (FIXTURES / "deb_session.xml").read_bytes()
MISMATCH_DKP = "00000000-crafted-mismatch"   # konstruēts bloks fixture beigās
RESOURCES = [
    {"name": "14.Saeimas 2026.gada rudens sesija-2-deb", "url": "https://x/2-deb.xml",
     "dkp_url": "https://x/2-dkp.xml"},
    {"name": "14.Saeimas 2022.gada rudens sesija-5-deb", "url": "https://x/5-deb.xml",
     "dkp_url": "https://x/5-dkp.xml"},
    # Tie paši punkti pārnesti uz citu sēdi; vienā vietā runā cits deputāts (9.).
    {"name": "14.Saeimas 2026.gada 23.jūlija ārkārtas sesija-1-deb", "url": "https://x/a1-deb.xml",
     "dkp_url": None},
]
FILES = {
    "https://x/2-deb.xml": SESSION_XML,
    "https://x/5-deb.xml": (FIXTURES / "deb_empty.xml").read_bytes(),
    "https://x/2-dkp.xml": (FIXTURES / "dkp_session.xml").read_bytes(),   # reāls, apgriezts
    # Pārnesē: 1. punktā cits 1. runātājs; 2. punktā Pleškāne runā vēlreiz, cits ilgums.
    "https://x/a1-deb.xml": SESSION_XML.replace(b"<DEBATE_SURNAME>Petravi", b"<DEBATE_SURNAME>Ozoli", 1)
                                       .replace(b"<DEBATE_TIME>03:38#", b"<DEBATE_TIME>07:00#", 1)
    # KONSTRUĒTS: pārnesei nav dkp, bet procedūras punkta nosaukums nes numuru (.9999 klase).
                                       .replace("darba kārtībā</TITLE>".encode(), "darba kārtībā (1104/Lm14)</TITLE>".encode(), 1),
}


_REAL_CLIENT = httpx.Client   # pirms jebkura monkeypatch — _mock_http drīkst saukt atkārtoti


def _mock_http(monkeypatch, files: dict[str, bytes]) -> list[str]:
    """Atgriež pieprasīto URL sarakstu (aizpildās skrējiena laikā)."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = files.get(str(request.url))
        return httpx.Response(200, content=body) if body is not None else httpx.Response(404)

    monkeypatch.setattr(ingest.httpx, "Client",
                        lambda *a, **k: _REAL_CLIENT(transport=httpx.MockTransport(handler)))
    return seen


def _db(tmp_path) -> str:
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (name, name_forms) VALUES ('Ramona Petraviča', '[]')")
    db.commit()
    db.close()
    return path


# ── tīrā parsēšana ─────────────────────────────────────────────────────

def test_duration_parses_to_seconds():
    """3."""
    assert _duration_sec("35:26") == 2126
    assert _duration_sec("1:02:03") == 3723
    assert _duration_sec("") is None
    assert _duration_sec("ap. 5 min") is None


def test_array_mismatch_drops_whole_dkp():
    """2. Konstruētais DKP: frakciju 2, pārējo 3 → viens failure, 0 rindu."""
    _dk_id, rows, failures = parse_debates(SESSION_XML)
    assert failures == [{"kind": "array_length_mismatch", "dkp_id": MISMATCH_DKP,
                         "lengths": {"DEBATE_NAME": 3, "DEBATE_SURNAME": 3, "DEBATE_FRACTION": 2,
                                     "DEBATE_TIME": 3, "DEBATE_INFO": 3, "DEBATE_OPINION": 3}}]
    assert not any(r["dkp_id"] == MISMATCH_DKP for r in rows)


# ── caur skripta ieeju ─────────────────────────────────────────────────

def test_ingest_end_to_end(tmp_path, monkeypatch, capsys):
    """1., 2., 4.–7., 9.–11. Trīs faili: reāla sēde (11 + 2 + 1 apakšpunkta runātājs,
    konstruēts nesakritības un tukšs punkts), 182 B tukšā sēde un tās pašas sēdes
    pārnese ar vienu citu runātāju. Nesakritība = failure → exit 1."""
    path = _db(tmp_path)
    monkeypatch.setattr(ingest, "list_debate_resources", lambda client, conv: RESOURCES)
    _mock_http(monkeypatch, FILES)

    assert ingest.main(["--what", "debates", "--db", path]) == 1
    out = capsys.readouterr().out
    assert "parsed=28 stored=16 skipped_existing=12" in out   # 12 atkārtotas, 2 citas runas
    assert "files_skipped_known=0" in out
    assert "parent_unresolved=0" in out   # pārnesei nav dkp, numurs nolasīts no nosaukuma
    assert "empty_sessions=1" in out
    assert MISMATCH_DKP in out and "array_length_mismatch" in out
    assert "unmatched: Hosams Abu Meri" in out and "unmatched: Ramona Petraviča" not in out

    db = get_db(path)
    carried = db.execute("SELECT speaker_name, session_date FROM saeima_debate_speeches "
                         "WHERE session_name LIKE '%ārkārtas%'").fetchall()
    rows = {r["speaker_name"]: dict(r) for r in db.execute(
        "SELECT * FROM saeima_debate_speeches WHERE session_name NOT LIKE '%ārkārtas%'")}
    count = db.execute("SELECT COUNT(*) FROM saeima_debate_speeches").fetchone()[0]
    db.close()
    assert count == 16
    assert {(r["speaker_name"].split()[-1], r["session_date"]) for r in carried} == {
        ("Ozoliča", None), ("Pleškāne", None)}
    assert {r["session_date"] for r in rows.values()} == {"2026-09-10"}
    minister = rows["Hosams Abu Meri"]
    assert (minister["faction"], minister["info"], minister["politician_id"]) == (None, "VesM", None)
    first = rows["Ramona Petraviča"]
    assert (first["politician_id"], first["faction"], first["duration_sec"], first["document_nr"]) == (
        1, "LPV", 2126, "1105/Lm14")
    child = rows["Mārcis Jencītis"]   # 10.
    assert (child["document_nr"], child["item_title"]) == (
        "1104/Lm14", "Par vēstures prioritāru mācīšanu — Par iekļaušanu nākamās kārtējās sēdes darba kārtībā")

    # Sēde ir svaiga (< 30 d) → 2. skrējiens to ielādē vēlreiz; datums relatīvs, lai tests nenovecotu.
    db = get_db(path)
    db.execute("UPDATE saeima_debate_speeches SET session_date = date('now') WHERE session_date IS NOT NULL")
    db.commit()
    db.close()

    # Atkārtots skrējiens; šoreiz dkp galva ir no CITAS sēdes → sibling_mismatch.
    other = FILES["https://x/2-dkp.xml"].replace(b"ac98bfc2-1cdd-4fba-b646-8bae0629117a", b"other-sitting")
    _mock_http(monkeypatch, {**FILES, "https://x/2-dkp.xml": other})
    assert ingest.main(["--what", "debates", "--db", path]) == 1
    out = capsys.readouterr().out
    assert "parsed=28 stored=0 skipped_existing=28" in out
    assert "sibling_mismatch" in out

    # 11. Glabātā sēde vecāka par 30 d → fails netiek ne ielādēts, ne parsēts.
    db = get_db(path)
    db.execute("UPDATE saeima_debate_speeches SET session_date = date('now', '-31 days') "
               "WHERE session_date IS NOT NULL")
    db.commit()
    db.close()
    seen = _mock_http(monkeypatch, FILES)
    assert ingest.main(["--what", "debates", "--db", path]) == 1   # nesakritība pārnesē paliek
    out = capsys.readouterr().out
    assert "files_skipped_known=1" in out
    assert "parsed=14 stored=0 skipped_existing=14" in out
    assert not {"https://x/2-deb.xml", "https://x/2-dkp.xml"} & set(seen)
    assert "https://x/a1-deb.xml" in seen   # pārneses datums NULL → ielādē vēlreiz


def test_zero_deb_resources_stops(tmp_path, monkeypatch, capsys):
    """8. CKAN bez neviena 14. sasaukuma `-deb` → STOP, exit 1, nekas neierakstīts."""
    path = _db(tmp_path)
    ckan = json.dumps({"result": {"resources": [
        {"name": "13.Saeimas 2021.gada rudens sesija-1-deb", "url": "https://x/a"},
        {"name": "14.Saeimas 2026.gada rudens sesija-2-vote", "url": "https://x/b"},
    ]}}).encode()
    _mock_http(monkeypatch, {CKAN_PACKAGE_URL: ckan})

    assert ingest.main(["--what", "debates", "--db", path]) == 1
    assert "STOP" in capsys.readouterr().out
    db = get_db(path)
    assert db.execute("SELECT COUNT(*) FROM saeima_debate_speeches").fetchone()[0] == 0
    db.close()
