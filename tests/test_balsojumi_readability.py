"""Balsojumu lapas pārskatāmības slānis (plāns 2026-09-04).

Sedz to, ko lasītājs redz, nevis to, kas kodā ir uzrakstīts:

* `_result_counts` — `result` vārdnīca NAV bināra, un trīs skaitļiem jāsaskaitās
  līdz kopskaitam. `Likums` izskatās pēc pieņemšanas, bet nav burtiskā etiķete,
  tāpēc paliek "citos" (tā pati robeža, kas neļauj nezināmu iznākumu krāsot
  sarkanu — tests/test_vote_result_non_binary.py).
* šablons — apzīmējumi, mēneša filtrs, "Tikai dalītie", frakciju grupas; un
  procents bez saucēja lapā vairs nedrīkst parādīties.
* `assets/bmv1.js` — sēžu dienu grupēšana, kartītes konteksta rinda un jaunie
  filtri tiek IZPILDĪTI node vidē pret sintētisku kompakto JSON, nevis
  meklēti ar grep. Grep pateiktu, ka funkcija eksistē; izpilde pasaka, ka tā
  strādā — un lapas robeža dienas vidū ir tieši tā vieta, kur "eksistē" un
  "strādā" atšķiras.

JS vārti krīt, ja `node` nav pieejams — klusa izlaišana nozīmētu, ka klienta
puse mēnešiem stāv nepārbaudīta (CLAUDE.md § vārti ar saucēju).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.render.votes import _faction_sort_key, _result_counts

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = Path("templates/balsojumi.html.j2")
_BMV1 = _ROOT / "assets" / "bmv1.js"


# ──────────────────────────────────────────────────────────────────
# Galvenes metrikas — trīs skaitļi, kas saskaitās
# ──────────────────────────────────────────────────────────────────

def test_result_counts_sum_to_total():
    votes = [
        {"result": "Pieņemts"}, {"result": "Pieņemts"},
        {"result": "Noraidīts"},
        {"result": "Nod. kom."}, {"result": "Likums"},
        {"result": "Paziņojums"}, {"result": None}, {},
    ]
    accepted, rejected, other = _result_counts(votes)
    assert (accepted, rejected, other) == (2, 1, 5)
    assert accepted + rejected + other == len(votes)


def test_likums_and_nod_kom_are_not_counted_as_accepted():
    """Neklasificēto neuzminam — `Likums` nav burtiskā `Pieņemts` etiķete."""
    accepted, rejected, other = _result_counts(
        [{"result": "Likums"}, {"result": "Nod. kom."}]
    )
    assert accepted == 0
    assert rejected == 0
    assert other == 2


def test_result_counts_empty_corpus():
    assert _result_counts([]) == (0, 0, 0)


def test_faction_sort_key_puts_canonical_first_then_alphabetical():
    order = sorted(["Ārpus frakcijām", "ZZS", "AS", "S!", "JV"], key=_faction_sort_key)
    assert order[:3] == ["AS", "JV", "ZZS"]
    assert set(order[3:]) == {"S!", "Ārpus frakcijām"}


# ──────────────────────────────────────────────────────────────────
# Šablons
# ──────────────────────────────────────────────────────────────────

def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["assets_version"] = "test"
    env.filters["lv_date"] = lambda s: s or ""
    env.filters["safe_url"] = lambda u: u or ""
    env.filters["safe_json"] = lambda v: v
    return env


def _render(**overrides) -> str:
    ctx = dict(
        votes=[],
        vote_topics=[],
        deputies=[
            {"name": "Anna Ābele", "faction": "JV"},
            {"name": "Bruno Bērzs", "faction": "JV"},
            {"name": "Cilda Cīrule", "faction": "ZZS"},
        ],
        vote_sessions=["2026-08-20", "2026-08-13", "2026-07-02"],
        vote_months=["2026-08", "2026-07"],
        metrics={
            "total": 8012, "last_week": 41,
            "accepted": 4695, "rejected": 2717, "other_result": 600,
        },
    )
    ctx.update(overrides)
    return _env().get_template("balsojumi.html.j2").render(**ctx)


def test_header_shows_three_result_counts_not_a_bare_percentage():
    html = _render()
    for label in ("Pieņemti", "Noraidīti", "Cits iznākums"):
        assert f">{label}<" in html or f'">{label}</span>' in html, label
    assert "4 695" in html and "2 717" in html and "600" in html
    # Procents bez saucēja lapā vairs nav — tieši to šis punkts noņēma.
    assert "%</span>" not in html


def test_legend_shows_colour_samples_rather_than_naming_colours():
    """Krāsu nosaukumi tekstā novecotu līdz ar tēmu; paraugi nevar. Paraugi
    lieto TĀS PAŠAS vietu klases, ko kartītes zāles josla (2026-10-16)."""
    html = _render()
    assert 'class="vote-legend"' in html
    legend = html.split('class="vote-legend"')[1][:1400]
    for cls, word in (("vs-p", "par"), ("vs-n", "pret"), ("vs-a", "atturas"),
                      ("vs-x", "nebalsoja"), ("vs-e", "bez ieraksta")):
        assert f'class="vote-seat {cls}"' in legend, cls
        assert word in legend, word
    for colour_word in ("zaļa", "Zaļa", "dzeltena", "sarkana"):
        assert colour_word not in html.split('class="vote-legend"')[1][:900], colour_word


def test_legend_states_that_abstention_is_not_neutral():
    html = _render()
    legend = html.split('class="vote-legend"')[1][:900]
    assert "Atturas" in legend
    assert "neitralitāte" in legend


def test_legend_says_no_record_is_not_proof_of_absence():
    """Kļūme (audits 2026-10-16): tukšā vieta «bez ieraksta» lasās kā «nepiedalījās»,
    bet tā nozīmē tikai, ka Saeimas datos šai vietai nav balss — neapmeklējumu
    tas nepierāda. Leģendai tas jāpasaka tieši."""
    html = _render()
    legend = html.split('class="vote-legend"')[1].split("</div>")[0]
    assert "<strong>Bez ieraksta</strong>" in legend
    assert "Saeimas datos" in legend
    assert "nepierāda" in legend


def test_month_filter_and_session_options_carry_month_scope():
    html = _render()
    assert 'id="month-select"' in html
    assert 'data-value="2026-08"' in html
    assert "2026. g. augusts" in html
    # Katrai sēdes opcijai jābūt data-month — bez tā sašaurināšana klusi neko nedara.
    session_opts = re.findall(r'data-value="(\d{4}-\d{2}-\d{2})"[^>]*', html)
    assert len(session_opts) == 3
    for d in ("2026-08-20", "2026-08-13", "2026-07-02"):
        assert f'data-value="{d}" data-month="{d[:7]}"' in html


def test_deputy_filter_has_faction_group_headers():
    html = _render()
    assert '<div class="multi-select-group" role="presentation" data-group="JV">JV</div>' in html
    assert 'data-group="ZZS">ZZS</div>' in html
    # Viens virsraksts uz frakciju, ne uz deputātu.
    assert html.count('class="multi-select-group"') == 2


def test_split_only_toggle_present():
    html = _render()
    assert 'id="vote-split-toggle"' in html
    assert "Tikai dalītie" in html


def test_template_stays_free_of_inline_js():
    """Papildu vārti tieši šai lapai — sk. tests/test_no_inline_js.py."""
    raw = (_ROOT / _TEMPLATE).read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)", raw)
    assert not re.search(r"""\son[a-z]+\s*=\s*["']""", raw)


# ──────────────────────────────────────────────────────────────────
# assets/bmv1.js — izpildīts, nevis grepēts
# ──────────────────────────────────────────────────────────────────

def _vote(i, date_str, motif, result, *, doc_nr=None, summary=None, factions=None,
          tot=(50, 10, 5)):
    v = {
        "i": i, "vid": 1000 + i, "d": date_str, "t": "10:00", "m": motif,
        "r": result, "tp": "Valsts pārvalde", "tot": list(tot), "uni": False,
        "f": factions if factions is not None else [{"f": "JV", "p": 5, "n": 0, "a": 0, "x": 0}],
        "co": 0,   # _FIXTURE["coalitions"][0] — valdība balsojuma brīdī
    }
    if doc_nr:
        v["doc_nr"] = doc_nr
    if summary:
        v["s"] = summary
    return v


# 5 votes on 20.08 (2 accepted, 1 rejected, 2 other) + 2 on 13.08.
# Index 0 is the OLDEST — the compact array is chronological ASC.
_SPLIT_FB = [
    {"f": "JV", "p": 3, "n": 3, "a": 2, "x": 0},   # 3/8 = 37,5% → dalīts
    {"f": "ZZS", "p": 6, "n": 0, "a": 0, "x": 0},
]
_FIXTURE = {
    "meta": {
        "version": 1, "generated_at": "2026-09-04T12:00:00",
        "votes_total": 7,
        "encoding": "P=Par,N=Pret,A=Atturas,X=Nebalsoja,.=absent",
        "all_dates": ["2026-08-20", "2026-08-13"],
    },
    "votes": [
        _vote(0, "2026-08-13", "Grozījumi Sporta likumā (900/Lp14), 1.lasījums", "Pieņemts", doc_nr="900/Lp14"),
        _vote(1, "2026-08-13", "Deputātu klātbūtnes reģistrācija", None),
        _vote(2, "2026-08-20", "Grozījumi Izglītības likumā (1467/Lp14), 1.lasījums", "Pieņemts", doc_nr="1467/Lp14"),
        _vote(3, "2026-08-20", "Par priekšlikumu Nr.1. Grozījumi Izglītības likumā (1467/Lp14), 2.lasījums",
              "Noraidīts", doc_nr="1467/Lp14",
              summary="Likumprojekts pirmajā lasījumā vienbalsīgi pieņemts (84 par).",
              factions=_SPLIT_FB),
        _vote(4, "2026-08-20", "Grozījumi Krimināllikumā (1502/Lp14), nodošana komisijām", "Nod. kom.", doc_nr="1502/Lp14",
              factions=[{"f": "JV", "p": 5, "n": 0, "a": 0, "x": 0},
                        {"f": "ārpusfrakciju", "p": 5, "n": 4, "a": 0, "x": 0}]),
        _vote(5, "2026-08-20", "Grozījumi Notariāta likumā (1320/Lp14), 3.lasījums", "Likums", doc_nr="1320/Lp14"),
        _vote(6, "2026-08-20", "Grozījumi Šengenas likumā (1482/Lp14), 2.lasījums, steidzams", "Pieņemts", doc_nr="1482/Lp14",
              factions=[{"f": "ZZS", "p": 0, "n": 0, "a": 19, "x": 1}]),
    ],
    "coalitions": [["JV", "NA", "ZZS"]],
    "factions": [
        {"f": "JV", "c": "#3b82f6", "cs": "coalition", "m": [1]},
        {"f": "ZZS", "c": "#84cc16", "cs": "coalition", "m": [2]},
    ],
    "politicians": {
        "1": {"n": "Anna Ābele", "f": "JV", "s": "anna-abele", "pp": 1, "v": "PPPPPPP",
              "sum": [7, 0, 0, 0], "att": 100},
        "2": {"n": "Cilda Cīrule", "f": "ZZS", "s": "cilda-cirule", "pp": 1, "v": "..PPPPP",
              "sum": [5, 0, 0, 0], "att": 71},
    },
}

_DRIVER = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const calls = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));

// Minimāls pārlūka kontūrs. bmv1.js ielādes brīdī tikai reģistrē funkcijas;
// document/location tiek aiztikti vēlāk, un arhīva ceļš tos neizmanto.
global.window = global;
global.document = {
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {},
};
global.location = { hash: '', search: '' };
global.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });

// Kā pārlūkā: sgv1.js (defer) jau izpildīts, kad bmv1 zīmē kartītes pēc
// datu ielādes — no tā nāk kopīgais window.atminaLvDate.
eval(fs.readFileSync(process.argv[5], 'utf8'));
eval(src);

(async () => {
  const out = [];
  for (const c of calls) {
    const r = await new Promise((res, rej) => {
      window.balsojumiArchiveRender(
        'recent.json', 'full.json', c.filters, c.opts,
        (r) => res(r), (m) => rej(new Error(m)),
      );
    });
    // Slinkais politiķu saraksts: tas, ko pārlūks ieliek <details> pirmajā
    // atvēršanā (blv1.js toggle klausītājs), pēc kartītes vid.
    r.tracked = {};
    const re = /<details class="vote-tracked" data-vid="(\d+)"/g;
    let m;
    while ((m = re.exec(r.html))) {
      r.tracked[m[1]] = window.balsojumiTrackedHtml
        ? window.balsojumiTrackedHtml(Number(m[1])) : '';
    }
    out.push(r);
  }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e && e.stack || String(e)); process.exit(1); });
"""


def _run_archive(calls: list[dict]) -> list[dict]:
    """Izpilda assets/bmv1.js::balsojumiArchiveRender node vidē."""
    node = shutil.which("node")
    if not node:
        pytest.fail(
            "node nav pieejams — klienta puses vārti nedrīkst klusi izlaisties; "
            "uzstādi Node.js vai palaid šo testu vidē, kur tas ir."
        )
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "driver.js").write_text(_DRIVER, encoding="utf-8")
        (tmp / "data.json").write_text(json.dumps(_FIXTURE, ensure_ascii=False), encoding="utf-8")
        (tmp / "calls.json").write_text(json.dumps(calls, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [node, str(tmp / "driver.js"), str(_BMV1), str(tmp / "data.json"), str(tmp / "calls.json"),
             str(_ROOT / "assets" / "sgv1.js")],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    assert proc.returncode == 0, f"node kļūda:\n{proc.stderr}"
    return json.loads(proc.stdout)


def _one(filters=None, opts=None) -> dict:
    return _run_archive([{"filters": filters or {}, "opts": opts or {"limit": 200, "offset": 0}}])[0]


def test_js_fixture_denominator():
    """Bez šī tukšs vai saplacis fixture izskatītos identisks tīram rezultātam."""
    res = _one()
    assert res["total"] == 7
    assert res["html"].count('class="vote-card"') == 7


def test_day_group_headers_appear_once_per_sitting():
    res = _one()
    assert _group_header_dates(res["html"]) == ["2026-08-20", "2026-08-13"], \
        "viens virsraksts uz sēdi, jaunākā pirmā"


def test_day_group_header_counts_use_the_non_binary_vocabulary():
    res = _one()
    head = res["html"].split('class="vote-day-group" data-date="2026-08-20"')[1].split("</div>")[0]
    # 5 balsojumi: 2 Pieņemts, 1 Noraidīts, 2 pārējie (Nod. kom. + Likums).
    assert "5 balsojumi" in head
    assert "2 pieņemti" in head
    assert "1 noraidīts" in head
    assert "2 ar citu iznākumu" in head


def test_day_group_header_uses_latvian_number_agreement():
    """41 balsojumS, ne "41 balsojumi" — 13.08 dienā ir tieši 2, 20.08 — 5."""
    res = _one(filters={"sessions": ["2026-08-13"]})
    head = res["html"].split('class="vote-day-group" data-date="2026-08-13"')[1].split("</div>")[0]
    assert "2 balsojumi" in head
    assert "1 pieņemts" in head and "1 pieņemti" not in head


def _group_header_dates(html: str) -> list[str]:
    """Tikai grupu virsraksti — `data-date` ir arī uz katras kartītes."""
    return re.findall(r'<div class="vote-day-group" data-date="([^"]+)"', html)


def test_page_boundary_does_not_repeat_a_day_header():
    """Diena, kas pārdalās starp divām "Rādīt vairāk" lapām, virsrakstu nedublē."""
    page1 = _one(opts={"limit": 3, "offset": 0})
    page2 = _one(opts={"limit": 3, "offset": 3})
    # 20.08 ir 5 balsojumi → lapa 1 nes 3 no tiem, lapa 2 turpina to pašu dienu.
    assert _group_header_dates(page1["html"]) == ["2026-08-20"]
    assert _group_header_dates(page2["html"]) == ["2026-08-13"], "atkārtots dienas virsraksts"


def test_page_boundary_counts_cover_the_whole_filtered_day_not_the_page():
    """Skaitlis virsrakstā ir par dienu, ne par lapā ietilpušo daļu."""
    page1 = _one(opts={"limit": 3, "offset": 0})
    head = page1["html"].split('class="vote-day-group" data-date="2026-08-20"')[1].split("</div>")[0]
    assert "5 balsojumi" in head


def test_card_kicker_carries_document_stage_and_chain_link():
    """Augšējā rinda nes dokumentu + stadiju; ķēdes saite kopš 2026-10-16 ir
    kājenes saišu rindā (blv1.js to atrod pēc klases, ne vietas)."""
    res = _one(filters={"q": "priekšlikumu"})
    assert res["total"] == 1
    html = res["html"]
    assert 'class="vote-kicker"' in html
    assert ">1467/Lp14<" in html
    assert ">2.lasījums<" in html
    assert 'class="vote-chain-link" data-doc-nr="1467/Lp14"' in html


def test_card_kicker_marks_urgent_bills():
    res = _one(filters={"q": "Šengenas"})
    assert ">steidzams<" in res["html"]


def test_card_without_document_number_still_renders():
    """Procedurāls balsojums bez dokumenta nedrīkst salūzt (nav nr., nav ķēdes)."""
    res = _one(filters={"q": "klātbūtnes"})
    assert res["total"] == 1
    assert 'class="vote-card"' in res["html"]
    assert "vote-chain-link" not in res["html"]


def test_amendment_summary_carries_the_sibling_caveat():
    """Māsas 1.lasījuma kopsavilkums nosaukts, nevis pārrakstīts."""
    res = _one(filters={"q": "priekšlikumu"})
    assert "Kopsavilkums apraksta likumprojekta virzību kopumā" in res["html"]


def test_non_amendment_summary_has_no_caveat():
    res = _one(filters={"q": "Sporta"})
    assert "Kopsavilkums apraksta" not in res["html"]


def test_search_ignores_diacritics_on_both_sides():
    """Lasītājs bieži raksta bez garumzīmēm: «izglitiba» → 0 bija 10-16 defekts.
    Arī otrādi — garumzīme vaicājumā atrod to pašu."""
    assert _one(filters={"q": "izglitibas"})["total"] == 2
    assert _one(filters={"q": "IZGLĪTĪBAS"})["total"] == 2
    assert _one(filters={"q": "sengenas"})["total"] == 1
    assert _one(filters={"q": "kriminallikuma"})["total"] == 1


def test_split_only_filter_keeps_exactly_the_non_uniform_factions():
    res = _one(filters={"splitOnly": True})
    assert res["total"] == 1, "tikai priekšlikuma balsojumam JV ir 3/3/2"
    assert "1467/Lp14" in res["html"]


def test_split_filter_and_card_chip_agree():
    """Viena definīcija: filtra rezultātam jābūt tam pašam, ko kartītes
    «dalīti» zīme iezīmē (skaita KARTĪTES, ne zīmes)."""
    split_res = _one(filters={"splitOnly": True})
    all_res = _one()
    tagged = [vid for vid in range(1000, 1007)
              if 'class="vote-faction-split"' in _card_html(all_res["html"], vid)]
    assert tagged == [1003]
    assert len(tagged) == split_res["total"] == 1


def test_month_filter_narrows_without_a_session_pick():
    assert _one(filters={"months": ["2026-08"]})["total"] == 7
    assert _one(filters={"months": ["2026-07"]})["total"] == 0


def test_month_and_session_filters_and_together():
    res = _one(filters={"months": ["2026-08"], "sessions": ["2026-08-13"]})
    assert res["total"] == 2


def test_unknown_result_never_renders_a_red_badge():
    """`Nod. kom.` / `Likums` nedrīkst izskatīties pēc noraidījuma."""
    for q, label in (("Krimināllikumā", "Nod. kom."), ("Notariāta", "Likums")):
        html = _one(filters={"q": q})["html"]
        # Iznākuma vārds ir rezultāta rindas sākumā; Par/Pret/Atturas skaitļi
        # aiz tā ir krāsaini pēc nozīmes un šeit nav vērtējami.
        word = html.split('<span class="vote-result-word ')[1].split("</span>")[0]
        assert word.startswith('is-other"'), word
        assert label in word, "etiķete rādās burtiski"
    # Tukšs iznākums nosaukts, nevis atstāts tukšs vai krāsots.
    html = _one(filters={"q": "klātbūtnes"})["html"]
    word = html.split('<span class="vote-result-word ')[1].split("</span>")[0]
    assert word == 'is-other">Iznākums nav norādīts', word


def test_unsplit_faction_chip_shows_minority_not_total():
    """ZZS 19 atturas + 1 nebalsoja (95 % — nav dalīta) agrāk rādījās kā
    «20 atturas»: vairākuma etiķete nesa kopskaitu (2026-09-28)."""
    html = _one(filters={"q": "Šengenas"})["html"]
    row = html.split('<div class="vote-frow"')[1].split("</div>")[0]
    assert ">19 atturas<" in row and ">1 nebalsoja<" in row
    assert "20 atturas" not in html


# ──────────────────────────────────────────────────────────────────
# 1. laidiens (plāns 2026-10-16): attēlojums mainās, dati — nē
# ──────────────────────────────────────────────────────────────────

def _card_html(html: str, vid: int) -> str:
    """Viena kartīte no saraksta HTML (līdz nākamajai kartītei)."""
    return html.split(f'id="vote-{vid}"')[1].split('<div class="vote-card"')[0]


def test_tracked_list_is_lazy_but_loses_no_politician():
    """Kartīte vairs nenes <table>; tabulu uzbūvē pirmajā atvēršanā, un
    kartīte + slinkā tabula kopā nes KATRU izsekoto politiķi ar vārdu,
    frakciju un balss etiķeti (operatora nosacījums: nezaudēt datus).

    Mutācijas pierādījums (2026-10-16): atjaunojot <table> kartītē → krīt
    uz `<table`; izmetot frakcijas šūnu no balsojumiTrackedHtml → krīt uz frakcijas
    pārbaudi.
    """
    res = _one()
    html = res["html"]
    assert "<table" not in html
    # Saucējs: 7 kartītes, katrā vismaz Anna → 7 slinkie saraksti.
    assert len(res["tracked"]) == 7
    expected = {
        # vid: [(vārds, frakcija, etiķete), …]
        1000: [("Anna Ābele", "JV", "Par")],
        1001: [("Anna Ābele", "JV", "Par")],
        1003: [("Anna Ābele", "JV", "Par"), ("Cilda Cīrule", "ZZS", "Par")],
    }
    for vid, rows in expected.items():
        card = _card_html(html, vid)
        assert f'Kā balsoja katrs deputāts <span class="vote-who-n">({len(rows)})</span>' in card
        lazy = res["tracked"][str(vid)]
        assert lazy.count("<tr ") == len(rows), lazy
        for name, faction, label in rows:
            assert f">{name}</a>" in lazy
            assert f">{faction}</td>" in lazy
            assert f">{label}</span>" in lazy
    # Cilda 0. balsojumā nav ieraksta → slinkajā sarakstā viņas nav (kā līdz šim).
    assert "Cilda" not in res["tracked"]["1000"]


def test_selected_deputy_vote_is_on_the_card():
    """Izvēlētā deputāta balss redzama kartītē bez atvēršanas; ja ieraksta
    nav (`.`), rāda «nav individuālā ieraksta», NEKAD «nepiedalījās».

    Mutācijas pierādījums (2026-10-16): izņemot izvēlēto rindu → krīt uz
    «vote-selected»; `.` caur VOTE_LABEL («Nepiedalījās») → krīt.
    """
    one = _one(filters={"deputies": ["Cilda Cīrule"], "q": "Sporta"})
    assert one["total"] == 0, "viena izvēle filtrē balsojumus bez ieraksta"
    one = _one(filters={"deputies": ["Cilda Cīrule"], "q": "Šengenas"})
    row = one["html"].split('class="vote-selected"')[1].split("</div>")[0]
    assert 'href="politiki/cilda-cirule.html">Cilda Cīrule</a>' in row
    assert "ZZS" in row
    assert ">Par</span>" in row

    two = _one(filters={"deputies": ["Anna Ābele", "Cilda Cīrule"], "q": "Sporta"})
    assert two["total"] == 1
    row = two["html"].split('class="vote-selected"')[1].split("</div>")[0]
    assert "Anna Ābele" in row and "Cilda Cīrule" in row
    assert "nav individuālā ieraksta" in row
    assert "nepiedalījās" not in two["html"].lower()

    # Bez deputātu filtra rindas nav.
    assert "vote-selected" not in _one(filters={"q": "Sporta"})["html"]


def test_card_redesign_loses_no_data():
    """Kartītes pārbūve (2026-10-16) maina izskatu, ne faktus: katras frakcijas
    katrs nenulles skaits ar savu vārdu, pilnais `title`, nebalsojušo kopsumma
    un zāles josla ar tieši 100 vietām pareizajās klasēs.

    Mutācijas pierādījums (2026-10-16): izmetot Atturas skaitu no frakcijas
    rindas → krīt uz «2 atturas»; zālē Atturas vietas ielaižot kā tukšas → krīt
    uz vietu skaitu; slēpjot ārpusfrakciju grupas «pret» → krīt uz «4 pret».
    """
    html = _one()["html"]
    card = _card_html(html, 1003)   # JV 3/3/2/0 (dalīts), ZZS 6/0/0/0; tot 50/10/5
    rows = {r.split('class="vote-fname"')[1].split(">", 1)[1].split("<")[0]: r
            for r in card.split('<div class="vote-frow"')[1:]}
    assert set(rows) == {"JV", "ZZS"}
    for name, parts in (("JV", ["3 par", "3 pret", "2 atturas"]), ("ZZS", ["6 par"])):
        for part in parts:
            assert f">{part}<" in rows[name], (name, part)
        assert ">0 " not in rows[name], "nulles nerāda"
    assert ('title="JV: par 3, pret 3, atturas 2, nebalsoja 0 — dalīts balsojums '
            '(38% vienotība)"') in rows["JV"]
    assert 'title="ZZS: par 6, pret 0, atturas 0, nebalsoja 0"' in rows["ZZS"]
    # Rezultāta rinda: trīs kopsummas + nebalsojušo summa no frakcijām.
    result = card.split('class="vote-result"')[1].split("</div>")[0]
    for n, word in ((50, "par"), (10, "pret"), (5, "atturas"), (0, "nebalsoja")):
        assert f">{n}</b> {word}" in result, (n, word)
    chamber = card.split('class="vote-chamber"')[1].split("</div>")[0]
    counts = {c: chamber.count(f'class="vote-seat {c}"') for c in ("vs-p", "vs-n", "vs-a", "vs-x", "vs-e")}
    assert counts == {"vs-p": 50, "vs-n": 10, "vs-a": 5, "vs-x": 0, "vs-e": 35}
    assert sum(counts.values()) == 100
    # Nebalsojušie (frakciju `x`) ir zālē un rindā: Šengenas ZZS 0/0/19/1.
    sch = _card_html(html, 1006)
    assert ">1</b> nebalsoja" in sch.split('class="vote-result"')[1]
    assert sch.split('class="vote-chamber"')[1].split("</div>")[0].count('class="vote-seat vs-x"') == 1
    # Deputāti bez frakcijas (tests/test_votes_no_faction_bucket.py): grupa
    # «Ārpus frakcijām», abi skaitļi atsevišķi — nekad «9 par».
    kr = _card_html(html, 1004)
    other = kr.split("Ārpus frakcijām")[1]
    assert '>ārpus<' in other and '>5 par<' in other and '>4 pret<' in other
    assert "9 par" not in kr and 'vote-faction-split' not in kr
    # Saites un datums ar laiku paliek.
    assert "20.08.2026, 10:00" in card
    assert 'class="vote-chain-link" data-doc-nr="1467/Lp14"' in card
