"""Partiju tests — T3 validators (`scripts/partiju_tests_validate.py`).

Divi principi no CLAUDE.md:

* **Vārti, kas nekad nav krituši, nav vārti** — katrs tests šeit vispirms
  pierāda, ka validators zaļu failu pieņem, un tad to tīši salauž (nepareizs
  `claim_id`, izdomāts citāts, sveša partija, `klusē` bez piezīmes) un prasa,
  lai validators KRĪT.
* **Saucējs, ne tikai atradums** — pārskats vienmēr saka, cik šūnu pārbaudīts.

Fikstūra raksta caur `store_claim()` (īstais rakstītājs), nevis ar roku
rakstītiem `INSERT`, lai tests nepārbaudītu paša izdomātu formu.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from src.db import get_db, init_db, insert_document, store_claim

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "partiju_tests_validate", REPO / "scripts" / "partiju_tests_validate.py"
)
ptv = importlib.util.module_from_spec(_spec)
sys.modules["partiju_tests_validate"] = ptv
_spec.loader.exec_module(ptv)

_spec = importlib.util.spec_from_file_location(
    "render_partiju_tests", REPO / "scripts" / "render_partiju_tests.py"
)
ptr = importlib.util.module_from_spec(_spec)
sys.modules["render_partiju_tests"] = ptr
_spec.loader.exec_module(ptr)

URL_JV = "https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba"
URL_ST = "https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei"
CONTENT_JV = "Programma. Nodrošināsim aizsardzības finansējumu 5% apmērā no IKP.  Programma."
CONTENT_ST = "Programma. Atteiksimies no obligātā valsts aizsardzības dienesta."

PARTIES = [  # (id, short_name) — tie paši 14, ko validators prasa pilnus
    (1, "JV"), (2, "PRO"), (3, "ZZS"), (4, "NA"), (5, "LPV"), (6, "AS"), (7, "MMN"),
    (8, "LA"), (9, "ST"), (15, "JKP"), (16, "ASL"), (17, "SC"), (18, "GS"), (19, "SV-AJ"),
    (20, "KL"),  # tabulā ir, bet nestartē — validatoram jānoraida
]


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, sn in PARTIES:
        db.execute("INSERT INTO parties (id, name, short_name) VALUES (?, ?, ?)", (pid, f"Partija {sn}", sn))
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (101, 'Līderis JV', 'Jaunā Vienotība', 'opponent')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (109, 'Līderis ST', 'Stabilitātei!', 'opponent')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, scraped_at, platform, title) VALUES (1, ?, 'h1', ?, '2026-07-02 10:00:00', 'web', 'JV programma')", (CONTENT_JV, URL_JV))
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, scraped_at, platform, title) VALUES (2, ?, 'h2', ?, '2026-07-02 10:00:00', 'web', 'ST programma')", (CONTENT_ST, URL_ST))
    db.commit()
    db.close()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _promise(db_path, pid, party_id, doc_id, url, stance, topic="Aizsardzība un drošība", claim_type="program_promise"):
    return store_claim(opponent_id=pid, document_id=doc_id, topic=topic, stance=stance, quote=None,
                       confidence=0.9, reasoning="tests", salience=0.5, source_url=url,
                       stated_at="2026-07-02 00:00:00", claim_type=claim_type, party_id=party_id, db_path=db_path)


@pytest.fixture
def green(db_path):
    """Viens jautājums, 14 partijas: JV par, ST pret, pārējās klusē — validatoram jāpieņem."""
    jv = _promise(db_path, 101, 1, 1, URL_JV, "Sola 5% no IKP aizsardzībai.")
    st = _promise(db_path, 109, 9, 2, URL_ST, "Atteiksies no obligātā VAD.")
    questions = [{"id": "q01", "tema": "Aizsardzība un drošība", "quiz": False,
                  "apgalvojums": "Aizsardzībai jāatvēl vismaz 5 % no IKP.", "piekrit_nozime": "par = 5 % vai vairāk"}]
    coding = {"q01": {sn: {"nostaja": "klusē", "piezime": "CVK: nemin. Pilnā programma: nemin."}
                      for _pid, sn in PARTIES if sn != "KL"}}
    coding["q01"]["JV"] = {"nostaja": "par", "avots": "cvk", "claim_id": jv,
                           "citats": "aizsardzības finansējumu 5% apmērā no IKP", "url": URL_JV}
    coding["q01"]["ST"] = {"nostaja": "pret", "avots": "cvk", "claim_id": st,
                           "citats": "Atteiksimies no  obligātā valsts aizsardzības dienesta", "url": URL_ST}
    return questions, coding


def test_green_file_passes_and_reports_denominator(db_path, green):
    questions, coding = green
    rep = ptv.validate(questions, coding, db_path)
    assert rep.errors == [], rep.errors
    assert rep.cells == 14, "saucējs = 1 jautājums × 14 saraksti"
    assert rep.counts["JV"] == {"par": 1, "pret": 0, "klusē": 0}
    assert rep.counts["ST"] == {"par": 0, "pret": 1, "klusē": 0}
    assert rep.counts["GS"] == {"par": 0, "pret": 0, "klusē": 1}


def test_citation_with_different_whitespace_still_matches(db_path, green):
    """Fikstūras ST citātā ir dubulta atstarpe — CVK HTML tā mēdz būt; validators normalizē."""
    questions, coding = green
    assert ptv.validate(questions, coding, db_path).errors == []


@pytest.mark.parametrize("break_it, fragment", [
    (lambda c: c["q01"]["JV"].__setitem__("claim_id", 999999), "claim_id"),
    (lambda c: c["q01"]["JV"].__setitem__("citats", "šī frāze programmā nav"), "citāts"),
    (lambda c: c["q01"]["JV"].__setitem__("url", "https://example.invalid/cits"), "url"),
    (lambda c: c["q01"]["JV"].__setitem__("nostaja", "varbūt"), "nostaja"),
    (lambda c: c["q01"]["GS"].pop("piezime"), "piezime"),
    (lambda c: c["q01"].pop("LA"), "trūkst"),
    (lambda c: c["q01"].__setitem__("KL", {"nostaja": "klusē", "piezime": "x"}), "KL"),
    (lambda c: c.__setitem__("q99", {}), "q99"),
])
def test_mutations_make_the_gate_fail(db_path, green, break_it, fragment):
    questions, coding = green
    broken = deepcopy(coding)
    break_it(broken)
    errors = ptv.validate(questions, broken, db_path).errors
    assert errors, f"salauzts fails ({fragment}) izgāja cauri — vārti nestrādā"
    assert any(fragment in e for e in errors), errors


def test_claim_of_wrong_party_or_wrong_type_is_rejected(db_path, green):
    questions, coding = green
    # tā pati partija, bet parasta 'position' pozīcija — nav programmas pierādījums
    pos = _promise(db_path, 101, None, 1, URL_JV, "Retorika.", topic="Budžets un finanses", claim_type="position")
    broken = deepcopy(coding)
    broken["q01"]["JV"]["claim_id"] = pos
    assert any("program_promise" in e for e in ptv.validate(questions, broken, db_path).errors)
    # ST programmas rinda ielikta JV šūnā — partija nesakrīt
    broken = deepcopy(coding)
    broken["q01"]["JV"]["claim_id"] = coding["q01"]["ST"]["claim_id"]
    broken["q01"]["JV"]["url"] = URL_ST
    assert any("partija" in e for e in ptv.validate(questions, broken, db_path).errors)


def test_unknown_topic_in_questions_is_rejected(db_path, green):
    questions, coding = green
    q = deepcopy(questions)
    q[0]["tema"] = "Šāda tēma nav"
    assert any("tema" in e for e in ptv.validate(q, coding, db_path).errors)


def test_cli_exit_codes(db_path, green, tmp_path):
    questions, coding = green
    y = tmp_path / "jautajumi.yaml"
    j = tmp_path / "kodejums.json"
    y.write_text(json.dumps(questions), encoding="utf-8")  # JSON ir derīgs YAML
    j.write_text(json.dumps(coding, ensure_ascii=False), encoding="utf-8")
    assert ptv.main(["--questions", str(y), "--coding", str(j), "--db", db_path]) == 0
    coding["q01"]["JV"]["claim_id"] = 999999
    j.write_text(json.dumps(coding, ensure_ascii=False), encoding="utf-8")
    assert ptv.main(["--questions", str(y), "--coding", str(j), "--db", db_path]) == 1


def test_repo_coding_file_if_present():
    """Kad `content/partiju-tests/kodejums.json` parādās (T4), šis tests kļūst par īsto vārtu."""
    q = REPO / "content" / "partiju-tests" / "jautajumi.yaml"
    j = REPO / "content" / "partiju-tests" / "kodejums.json"
    if not (q.exists() and j.exists()):
        pytest.skip("kodejums.json vēl nav — T4 nav sācies")
    # Ražošanas DB nav publiskajā spogulī (CI): `data/atmina.db` tur vai nu nav,
    # vai ir tukšs fails → `no such table: claims` (2026-09-13 CI sarkans).
    # Tā pati klase kā `data/*.sql` eksistences skipi — vārts ir lokāls.
    db = REPO / "data" / "atmina.db"
    if not db.exists():
        pytest.skip("data/atmina.db nav — ražošanas DB tikai lokāli")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        has_claims = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='claims'"
        ).fetchone()
    finally:
        conn.close()
    if not has_claims:
        pytest.skip("data/atmina.db bez `claims` tabulas — ražošanas DB tikai lokāli")
    rc = ptv.main(["--questions", str(q), "--coding", str(j), "--db", str(db)])
    assert rc == 0


STARTING14 = ["JV", "PRO", "ZZS", "NA", "LPV", "AS", "MMN", "LA", "ST", "JKP", "ASL", "SC", "GS", "SV-AJ"]


def _render_fixture(n_questions: int = 3):
    questions = [{"id": f"q{i:02d}", "tema": "Aizsardzība un drošība",
                  "apgalvojums": f"Apgalvojums {i}.", "piekrit_nozime": "x"}
                 for i in range(1, n_questions + 1)]
    coding = {q["id"]: {sn: {"nostaja": "klusē", "piezime": "programma neizsakās"}
                        for sn in STARTING14}
              for q in questions}
    parties = {sn: {"name": f"Partija {sn}", "slug": sn.lower()} for sn in STARTING14}
    saraksti = [{"short_name": sn} for sn in STARTING14]
    return questions, coding, parties, saraksti


def test_render_uses_fixture_counts_not_hardcoded_12():
    """3 jautājumu fikstūra: izvadē „3 apgalvojumi”, ne cietkodētais „12”."""
    questions, coding, parties, saraksti = _render_fixture(3)
    html = ptr.build(questions=questions, coding=coding, parties=parties,
                     saraksti=saraksti, og_image_exists=False)
    assert "3 apgalvojumi" in html
    assert "12 apgalvojumi" not in html
    assert "no 3<" in html or "no 3 " in html


def test_og_image_meta_follows_flag():
    questions, coding, parties, saraksti = _render_fixture(1)
    kw = dict(questions=questions, coding=coding, parties=parties, saraksti=saraksti)
    with_og = ptr.build(**kw, og_image_exists=True)
    without = ptr.build(**kw, og_image_exists=False)
    assert 'property="og:image"' in with_og and 'name="twitter:image"' in with_og
    assert 'property="og:image"' not in without and 'name="twitter:image"' not in without


def test_og_image_file_exists_and_is_referenced():
    """Vārts: og variants jāeksistē PIRMS publicēšanas — mutācija `mv partiju-tests-og.jpg`
    padara šo testu sarkanu (meta tiek nomesta, fails pazūd)."""
    questions, coding, parties, saraksti = _render_fixture(1)
    if not ptr.OG_IMAGE.parent.exists():
        pytest.skip("output/images/analizes/ nav — attēlu koks tikai lokāli")
    assert ptr.OG_IMAGE.exists(), "partiju-tests-og.jpg nav — lapa publicētos ar 404 og:image"
    html = ptr.build(questions=questions, coding=coding, parties=parties, saraksti=saraksti)
    assert 'property="og:image"' in html, "fails ir, bet meta nav — renderers to nolaizētu"


# --- U2: trīs avotu līmeņi + quiz vārts -------------------------------------

URL_LA = "https://la.lv/programma"
URL_MMN = "https://mmn.lv/jaunumi/lideris-intervija"
CONTENT_LA = "Pilnā programma. Samazināsim pievienotās vērtības nodokli pārtikai."
CONTENT_MMN = "Intervija. Līderis: PVN pārtikai ir jābūt zemākam."

def _saraksti_u2():
    out = []
    for sn in STARTING14:
        s = {"short_name": sn}
        if sn == "LA":
            s["majaslapa"] = "https://la.lv"
        if sn == "MMN":
            s["lideris_id"] = 105
        out.append(s)
    return out


@pytest.fixture
def levels(db_path):
    """Viens jautājums ar visiem trim avotu līmeņiem: JV par (cvk), LA par
    (pilna_programma), MMN pret (izteikums), pārējie klusē jaunā formātā."""
    jv = _promise(db_path, 101, 1, 1, URL_JV, "Sola 5% no IKP aizsardzībai.")
    doc_la = insert_document(content=CONTENT_LA, source_id=None, source_url=URL_LA,
                             title="LA programma", db_path=db_path)
    doc_mmn = insert_document(content=CONTENT_MMN, source_id=None, source_url=URL_MMN,
                              title="MMN līdera intervija", db_path=db_path)
    questions = [{"id": "q01", "tema": "Budžets un finanses", "quiz": False,
                  "apgalvojums": "PVN pārtikai jāsamazina.", "piekrit_nozime": "x"}]
    coding = {"q01": {sn: {"nostaja": "klusē", "piezime": "CVK: nemin. Pilnā programma: nemin."}
                      for sn in STARTING14}}
    coding["q01"]["JV"] = {"nostaja": "par", "avots": "cvk", "claim_id": jv,
                           "citats": "aizsardzības finansējumu 5% apmērā no IKP", "url": URL_JV}
    coding["q01"]["LA"] = {"nostaja": "par", "avots": "pilna_programma", "document_id": doc_la,
                           "citats": "Samazināsim pievienotās vērtības nodokli pārtikai", "url": URL_LA}
    coding["q01"]["MMN"] = {"nostaja": "pret", "avots": "izteikums", "document_id": doc_mmn,
                            "runatajs": 105, "datums": "2026-08-12",
                            "citats": "PVN pārtikai ir jābūt zemākam", "url": URL_MMN}
    return questions, coding, _saraksti_u2()


def test_three_levels_green(db_path, levels):
    questions, coding, saraksti = levels
    rep = ptv.validate(questions, coding, db_path, saraksti=saraksti)
    assert rep.errors == [], rep.errors
    assert rep.cells == 14
    assert rep.levels == {"cvk": 1, "pilna_programma": 1, "izteikums": 1, "klusē": 11}
    assert rep.per_party_levels["LA"] == {"pilna_programma": 1}


@pytest.mark.parametrize("break_it, fragment", [
    (lambda c: c["q01"]["LA"].__setitem__("url", "https://svesums.lv/programma"), "domēns"),
    (lambda c: c["q01"]["MMN"].__setitem__("runatajs", 999), "runatajs"),
    (lambda c: c["q01"]["MMN"].__setitem__("datums", "2025-08-12"), "datums"),
    (lambda c: (c["q01"]["JV"].pop("claim_id"), c["q01"]["JV"].__setitem__("document_id", 1)), "claim_id"),
    (lambda c: c["q01"]["JV"].pop("avots"), "avots"),
    (lambda c: c["q01"]["GS"].__setitem__("piezime", "programma neizsakās"), "piezime"),
])
def test_level_mutations_fail(db_path, levels, break_it, fragment):
    questions, coding, saraksti = levels
    broken = deepcopy(coding)
    break_it(broken)
    errors = ptv.validate(questions, broken, db_path, saraksti=saraksti).errors
    assert errors, f"salauzts fails ({fragment}) izgāja cauri — vārti nestrādā"
    assert any(fragment in e for e in errors), errors


def test_pilna_programma_url_domain_must_match_majaslapa(db_path, levels):
    """saraksti.yaml: pilna_programma_url (ja ir) jābūt majaslapa domēnā."""
    questions, coding, saraksti = levels
    s = deepcopy(saraksti)
    next(x for x in s if x["short_name"] == "LA")["pilna_programma_url"] = "https://svesums.lv/p"
    assert any("pilna_programma_url" in e for e in
               ptv.validate(questions, coding, db_path, saraksti=s).errors)
    next(x for x in s if x["short_name"] == "LA")["pilna_programma_url"] = "https://la.lv/p"
    assert ptv.validate(questions, coding, db_path, saraksti=s).errors == []


def test_kluse_note_with_nav_parbaudita_fails(db_path, levels):
    """U4: 'nav pārbaudīta' ir starppagaidu forma — piezimē jābūt pilnās
    programmas rezultātam (vai 'nav publicējusi'/'nav pieejama')."""
    questions, coding, saraksti = levels
    broken = deepcopy(coding)
    broken["q01"]["GS"]["piezime"] = "CVK: nemin. Pilnā programma: nav pārbaudīta (U4)."
    assert any("nav pārbaudīta" in e for e in
               ptv.validate(questions, broken, db_path, saraksti=saraksti).errors)
    broken["q01"]["GS"]["piezime"] = "programma neizsakās"
    assert any("piezime" in e for e in
               ptv.validate(questions, broken, db_path, saraksti=saraksti).errors)


def _quiz_fixture(n_questions: int, par: int = 7, pret: int = 5):
    """n quiz: true jautājumi; `par` saraksti piekrīt, `pret` iebilst."""
    saraksti = [{"short_name": sn} for sn in STARTING14]
    questions = [{"id": f"q{i:02d}", "tema": "Aizsardzība un drošība",
                  "apgalvojums": f"A{i}.", "quiz": True}
                 for i in range(1, n_questions + 1)]
    cells = {}
    for i, sn in enumerate(STARTING14):
        if i < par:
            cells[sn] = {"nostaja": "par"}
        elif i < par + pret:
            cells[sn] = {"nostaja": "pret"}
        else:
            cells[sn] = {"nostaja": "klusē", "piezime": "x"}
    coding = {q["id"]: dict(cells) for q in questions}
    return questions, coding, saraksti


def test_quiz_gate_green_fixture():
    questions, coding, saraksti = _quiz_fixture(8, par=7, pret=5)
    assert ptv.quiz_gate(questions, coding, saraksti) == []


def test_quiz_gate_balance_6_4_passes():
    questions, coding, saraksti = _quiz_fixture(8, par=6, pret=4)
    assert ptv.quiz_gate(questions, coding, saraksti) == []


@pytest.mark.parametrize("n_q, par, pret, fragment", [
    (8, 8, 0, "mazākums"),            # quiz: true pie 8/0
    (8, 9, 1, "balanss"),             # 9:1 par:pret (90 % > 60 %)
    (8, 1, 9, "balanss"),             # 1:9 par:pret (spoguļattēls)
    (7, 9, 3, "quiz: true skaits"),   # tikai 7 quiz: true
])
def test_quiz_gate_mutations(n_q, par, pret, fragment):
    questions, coding, saraksti = _quiz_fixture(n_q, par=par, pret=pret)
    errors = ptv.quiz_gate(questions, coding, saraksti)
    assert errors, f"salauzta kopa ({fragment}) izgāja cauri"
    assert any(fragment in e for e in errors), errors
