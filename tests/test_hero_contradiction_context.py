"""Sākumlapas izceltā pretruna: konteksts saglabājas (T1, 2026-09-05).

Problēma, ko T1 risina: hero kartīte rādīja tikai `old_excerpt`/`new_excerpt`,
un īss citāts nenosauca savu priekšmetu — pilnajā `/pretrunas/<id>.html` lapā
esošā analīzes atruna sākumlapā pazuda.

Pārbaudām tikai T1 uzvedību:
  1. `summary` renderējas PILNS un PIRMS citātu pāra;
  2. `context_note` ir savs, no kopsavilkuma nodalīts bloks;
  3. nav automātiskas īsināšanas — ne `truncate`, ne `line-clamp` klase,
     ne `<details>`;
  4. bez `summary` rūtis rāda pilnas `old_stance`/`new_stance` parafrāzes,
     un citāta/parafrāzes atšķīrums (pēdiņas) paliek;
  5. trūkstošs citāts nerada tukšas pēdiņas;
  6. vienai kartītei nav navigācijas punktu, bez kartītēm nav hero bloka;
  7. kartītē (viena <a>) nav ieliktu saišu vai pogu;
  8. `assets/ixv1.js` vairs nesatur automātisko pārslēgšanos.

Renderē ``index.html.j2`` tieši ar minimālu kontekstu (Jinja ``Undefined``
klusē pārējos blokus) — šablona līgums, ne pilna vietnes ģenerēšana. Dati ir
lokāli fixture, NEVIS mainīgs produkcijas pretrunas ID.
"""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.render._common import _safe_json_filter, _safe_url_filter

# Garš kopsavilkums — dzīvajā DB (confirmed=1) maksimums bija 1228 rakstzīmes,
# tāpēc pārbaudām šo kārtu, ne 120 rakstzīmju fragmentu.
LONG_SUMMARY = (
    "Politiķis 2024. gada rudenī publiski solīja, ka valsts budžetā netiks "
    "palielināti nodokļi mājsaimniecībām, un šo solījumu atkārtoja vairākās "
    "intervijās. 2026. gada pavasarī viņš atbalstīja grozījumus, kas paaugstina "
    "patēriņa nodokli, skaidrojot to ar mainījušos drošības situāciju un "
    "aizsardzības izdevumu pieaugumu. "
) * 3

CONTEXT_NOTE = (
    "Solījuma termiņš formāli nav pārkāpts — sākotnējā apņemšanās attiecās uz "
    "kārtējo budžeta gadu, un grozījumi stājas spēkā nākamajā periodā."
)

OLD_STANCE = (
    "Iebilst pret jebkādu nodokļu celšanu mājsaimniecībām kārtējā budžeta gadā "
    "un uzskata, ka ieņēmumi jāatrod, samazinot valsts pārvaldes izdevumus."
)
NEW_STANCE = (
    "Atbalsta patēriņa nodokļa paaugstināšanu, pamatojot to ar aizsardzības "
    "izdevumu pieaugumu un mainījušos drošības situāciju reģionā."
)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s or ""
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["image_variant"] = lambda s, *a, **k: s
    env.globals["assets_version"] = "test"
    return env


def _contradiction(**over) -> dict:
    c = {
        "id": 4242,
        "politician_name": "Testa Politiķis",
        "slug": "testa-politikis",
        "party_short": "TST",
        "party_color": "#334455",
        "initials": "TP",
        "has_photo": False,
        "topic": "Nodokļi",
        "severity_glyph": "▲",
        "severity_lv": "tieša pretruna",
        "category_label": "Solījums pret balsojumu",
        "delta_days": 540,
        "old_label": "Iepriekš",
        "new_label": "Pašlaik",
        "old_date": "2024-10-02",
        "new_date": "2026-03-25",
        "summary": LONG_SUMMARY,
        "context_note": CONTEXT_NOTE,
        "old_stance": OLD_STANCE,
        "new_stance": NEW_STANCE,
        "old_excerpt": "Nodokļus mājsaimniecībām mēs necelsim.",
        "old_is_quote": True,
        "new_excerpt": "Atbalsta patēriņa nodokļa paaugstināšanu.",
        "new_is_quote": False,
    }
    c.update(over)
    return c


def _render(hero_items) -> str:
    return _env().get_template("index.html.j2").render(
        stats={},
        days_until_election=10,
        focus={},
        hero_items=hero_items,
        rankings={},
        week_summary={},
        recent_votes=[],
        recent_briefs=[],
        trends_data={},
        BASE_URL="https://atmina.lv",
    )


def _hero_block(html: str) -> str:
    """Hero karuseļa bloks (no kickera līdz metriku joslai)."""
    start = html.find('<div class="hero-feature" id="heroFeature">')
    assert start != -1, "hero bloks nav izrenderēts"
    end = html.find('<div class="hero-v2-metrics', start)
    assert end != -1
    return html[start:end]


def _card(html: str) -> str:
    """Pirmās hero kartītes <a> saturs."""
    block = _hero_block(html)
    start = block.find('<a class="hero-feature-card')
    assert start != -1, "hero kartīte nav izrenderēta"
    end = block.find("</a>", start)
    assert end != -1
    return block[start:end]


# ── 1.–3. Kopsavilkums un konteksts ──────────────────────────────────


def test_long_summary_is_rendered_in_full():
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert LONG_SUMMARY.strip() in card, "kopsavilkums nav pilns"
    assert "…" not in card.split("hero-feature-split")[0], "kopsavilkums ir īsināts"


def test_summary_stands_before_the_quote_pair():
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert card.index("hero-feature-summary") < card.index("hero-feature-split")


def test_context_note_is_its_own_block_with_its_own_label():
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    m = re.search(r'<div class="hero-feature-context">(.*?)</div>\s*</div>', card, re.S)
    assert m, "konteksta bloks nav izrenderēts"
    ctx = m.group(1)
    assert "Konteksts" in ctx
    assert CONTEXT_NOTE in ctx
    # Konteksts NAV ielikts kopsavilkuma iekšā un nav sajaukts ar citātu.
    summary_block = card[card.index("hero-feature-summary"):card.index("hero-feature-context")]
    assert CONTEXT_NOTE not in summary_block


def test_no_clamp_no_details_no_truncation_markup_in_the_card():
    """Kompozīta clamp klase pieder CITAM blokam — hero kartītē tās nav."""
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert "contra-summary-clamp" not in card
    assert "<details" not in card
    assert "line-clamp" not in card


def test_context_note_absent_renders_no_context_block():
    card = _card(_render([
        {"kind": "contradiction", "item": _contradiction(context_note=None)}
    ]))
    assert "hero-feature-context" not in card
    assert "Konteksts" not in card
    assert "hero-feature-summary" in card


# ── 4.–5. Rūtis: parafrāzes, pēdiņas, trūkstošs citāts ───────────────


def test_without_summary_the_panes_show_full_stances_as_paraphrases():
    card = _card(_render([
        {"kind": "contradiction", "item": _contradiction(summary="", context_note=None)}
    ]))
    assert "hero-feature-summary" not in card
    assert OLD_STANCE in card and NEW_STANCE in card
    # Parafrāze — bez pēdiņām, arī tad, kad fragmentam `old_is_quote` bija True.
    assert "„" not in card and "”" not in card


def test_quote_vs_paraphrase_distinction_survives_when_summary_exists():
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert "„Nodokļus mājsaimniecībām mēs necelsim.”" in card
    assert "„Atbalsta patēriņa nodokļa paaugstināšanu.”" not in card
    assert "Atbalsta patēriņa nodokļa paaugstināšanu." in card


def test_missing_quote_falls_back_to_stance_without_empty_quote_marks():
    """`hero_excerpt` bez citāta atgriež parafrāzi (is_quote=False)."""
    card = _card(_render([{"kind": "contradiction", "item": _contradiction(
        old_excerpt=OLD_STANCE, old_is_quote=False,
    )}]))
    assert "„”" not in card
    assert "„" not in card, "bez citāta pēdiņas nedrīkst parādīties"
    assert OLD_STANCE in card


# ── 6. Navigācija un tukšs stāvoklis ─────────────────────────────────


def test_single_card_has_no_navigation():
    block = _hero_block(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert "hero-feature-dot" not in block
    assert "<button" not in block


def test_two_cards_keep_manual_navigation_dots():
    block = _hero_block(_render([
        {"kind": "contradiction", "item": _contradiction()},
        {"kind": "contradiction", "item": _contradiction(id=4243)},
    ]))
    assert block.count('<button type="button" class="hero-feature-dot') == 2


def test_no_hero_block_without_cards():
    html = _render([])
    assert 'id="heroFeature"' not in html
    assert "hero-feature-card" not in html


def test_card_is_one_link_without_nested_links_or_buttons():
    """Kartīte ir viena <a> — iekšā ne saites, ne pogas (T1 prasība)."""
    card = _card(_render([{"kind": "contradiction", "item": _contradiction()}]))
    assert "<button" not in card
    assert "<a " not in card[1:]
    assert not re.search(r"""\son[a-z]+\s*=\s*["']""", card, re.I)


# ── 7. JS: automātiskā pārslēgšanās noņemta ──────────────────────────


def _js_without_comments() -> str:
    src = Path("assets/ixv1.js").read_text(encoding="utf-8")
    return re.sub(r"//[^\n]*", "", src)


def test_hero_carousel_no_longer_auto_advances():
    code = _js_without_comments()
    assert "setInterval" not in code, "hero karuselis joprojām pārslēdzas pats"
    assert "setTimeout" not in code


def test_manual_dot_navigation_still_wired():
    code = _js_without_comments()
    assert "hero-feature-dot" in code
    assert "addEventListener('click'" in code
