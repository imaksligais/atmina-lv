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
        bills=[],
        bill_topics=[],
        laws_index_count=0,
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
    """Krāsu nosaukumi tekstā novecotu līdz ar tēmu; paraugi nevar."""
    html = _render()
    assert 'class="vote-legend"' in html
    assert "faction-chip is-coalition is-sample" in html
    assert "faction-chip is-opposition is-sample" in html
    assert "faction-chip is-split is-sample" in html
    for colour_word in ("zaļa", "Zaļa", "dzeltena", "sarkana"):
        assert colour_word not in html.split('class="vote-legend"')[1][:900], colour_word


def test_legend_states_that_abstention_is_not_neutral():
    html = _render()
    legend = html.split('class="vote-legend"')[1][:900]
    assert "Atturas" in legend
    assert "neitralitāte" in legend


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
        _vote(4, "2026-08-20", "Grozījumi Krimināllikumā (1502/Lp14), nodošana komisijām", "Nod. kom.", doc_nr="1502/Lp14"),
        _vote(5, "2026-08-20", "Grozījumi Notariāta likumā (1320/Lp14), 3.lasījums", "Likums", doc_nr="1320/Lp14"),
        _vote(6, "2026-08-20", "Grozījumi Šengenas likumā (1482/Lp14), 2.lasījums, steidzams", "Pieņemts", doc_nr="1482/Lp14"),
    ],
    "factions": [
        {"f": "JV", "c": "#3b82f6", "cs": "coalition", "m": [1]},
        {"f": "ZZS", "c": "#84cc16", "cs": "coalition", "m": [2]},
    ],
    "politicians": {
        "1": {"n": "Anna Ābele", "f": "JV", "s": "anna-abele", "v": "PPPPPPP",
              "sum": [7, 0, 0, 0], "att": 100, "dis": []},
        "2": {"n": "Cilda Cīrule", "f": "ZZS", "s": "cilda-cirule", "v": "..PPPPP",
              "sum": [5, 0, 0, 0], "att": 71, "dis": []},
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

eval(src);

(async () => {
  const out = [];
  for (const c of calls) {
    out.push(await new Promise((res, rej) => {
      window.balsojumiArchiveRender(
        'recent.json', 'full.json', c.filters, c.opts,
        (r) => res(r), (m) => rej(new Error(m)),
      );
    }));
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
            [node, str(tmp / "driver.js"), str(_BMV1), str(tmp / "data.json"), str(tmp / "calls.json")],
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


def test_split_only_filter_keeps_exactly_the_non_uniform_factions():
    res = _one(filters={"splitOnly": True})
    assert res["total"] == 1, "tikai priekšlikuma balsojumam JV ir 3/3/2"
    assert "1467/Lp14" in res["html"]


def test_split_filter_and_card_chip_agree():
    """Viena definīcija: filtra rezultātam jābūt tam pašam, ko čips iezīmē."""
    split_res = _one(filters={"splitOnly": True})
    all_res = _one()
    chip_cards = all_res["html"].count("faction-chip is-coalition is-split")
    assert chip_cards == split_res["total"] == 1


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
        # Iznākuma nozīmīte ir PIRMĀ vote-badges blokā; Par/Pret/Atturas skaitļu
        # nozīmītes aiz tās ir krāsainas pēc nozīmes un šeit nav vērtējamas.
        result_badge = html.split('class="vote-badges">')[1].split("</span>")[0]
        assert "badge-muted" in result_badge, result_badge
        assert "badge-red" not in result_badge
        assert "badge-green" not in result_badge
        assert label in result_badge, "etiķete rādās burtiski"
