"""Frakcijas etiķete, kas nonāk DB, ir `parties.short_name` forma — visos ceļos.

Konteksts (2026-09-04). `ST!` un `ST` ir viena frakcija (Stabilitātei!,
`parties.id=9`, `short_name='ST'`). Titania šūnas teksts driftē pa sezonām, un
`ST!` neatbilst NE `parties.name`, NE `parties.short_name` — tāpēc
`src.coalition.get_coalition_map()` to atrisināja kā `'other'`, nevis
`'opposition'`. Sekas bija redzamas publiskajā lapā: 7 448 balsu rindas /
**975 balsojumi (12,2 %)** rādīja Stabilitātei! bez opozīcijas iezīmes un
nepareizā secībā frakciju sadalījumā.

Cēlonis nebija trūkstoša normalizācija — tā EKSISTĒJA kopš 2026-08-04, bet
dzīvoja LOKĀLI `parse_vote_snapshot()` iekšienē. Abi backfill parseri
(`p3_backfill_year_urllib.py::_decode_entry` — JS `voteFullListByNames`, un
`p3_backfill_year.py` — Playwright šūnas) to nekad neredzēja un atkārtoti
ielika `ST!` rindas PĒC tam, kad datu migrācija tās bija iztīrījusi. Tas ir
`CLAUDE.md` „IZPILDĪTS nozīmē, ka kods ir kokā, ne ka tas jebkad nostrādāja"
klase: labojums bija merged, bet uz otra ceļa nekad neizpildījās.

Tāpēc šie vārti tur DIVAS lietas atsevišķi:
  1. Kanoniskums — katra atpazītā šūnas vērtība pēc normalizācijas atrisinās
     `get_coalition_map()`. Saucējs = `FACTION_CELL_VALUES` izmērs, un tests
     nosauc to, lai tukšs komplekts neizskatītos pēc tīra rezultāta.
  2. Ceļu paritāte — VISI scrape parseri dod vienu un to pašu kanonisko formu
     vienai un tai pašai avota šūnai. Tieši šis punkts nokrita ražošanā.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.coalition import get_coalition_map
from src.saeima.votes import (
    FACTION_CELL_VALUES,
    FACTION_NORMALIZE,
    normalize_faction,
    parse_vote_snapshot,
)


# ──────────────────────────────────────────────────────────────────
# 1. Kanoniskums pret parties.short_name
# ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def parties_db():
    """Minimāls `parties` — tikai tas, ko get_coalition_map lasa."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE parties (name TEXT, short_name TEXT, coalition_status TEXT)")
    db.executemany(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?,?,?)",
        [
            ("Jaunā VIENOTĪBA", "JV", "coalition"),
            ("Zaļo un Zemnieku savienība", "ZZS", "coalition"),
            ("Progresīvie", "PRO", "coalition"),
            ("Nacionālā apvienība", "NA", "opposition"),
            ("Apvienotais saraksts", "AS", "opposition"),
            ("Latvija Pirmajā Vietā", "LPV", "opposition"),
            ("Stabilitātei!", "ST", "opposition"),
            ("Latvijas Attīstībai", "LA", "opposition"),
            ("Konservatīvie", "K", "opposition"),
            ("Alternatīvā partija", "AP", "opposition"),
            ("Neatkarīgie", "NP", "opposition"),
        ],
    )
    return db


def test_cell_value_denominator_is_not_empty():
    """Tukšs komplekts padarītu visus zemāk esošos vārtus par nulles ciklu."""
    assert len(FACTION_CELL_VALUES) >= 10, FACTION_CELL_VALUES
    assert "ST" in FACTION_CELL_VALUES and "ST!" in FACTION_CELL_VALUES


def test_every_recognised_cell_resolves_in_the_coalition_map(parties_db):
    """Šie ir īstie vārti: `ST!` te nokrita, jo atrisinājās kā 'other'."""
    cmap = get_coalition_map(parties_db)
    unresolved = {}
    for cell in sorted(FACTION_CELL_VALUES):
        canon = normalize_faction(cell)
        if canon not in cmap:
            unresolved[cell] = canon
    assert not unresolved, (
        f"etiķetes, kas neatrisinās pret parties.short_name "
        f"(no {len(FACTION_CELL_VALUES)} pārbaudītām): {unresolved}"
    )


def test_st_bang_resolves_to_opposition_not_other(parties_db):
    """Regresijas enkurs tieši uz to defektu, kas aizbrauca live."""
    cmap = get_coalition_map(parties_db)
    assert cmap.get(normalize_faction("ST!")) == "opposition"
    assert cmap.get("ST!") is None, "neapstrādāta forma joprojām nav kartē — tāpēc normalizē"


# ──────────────────────────────────────────────────────────────────
# 2. normalize_faction uzvedība
# ──────────────────────────────────────────────────────────────────

def test_normalize_maps_known_drift():
    assert normalize_faction("ST!") == "ST"
    assert normalize_faction("  ST!  ") == "ST"


def test_normalize_passes_unknown_through_unchanged():
    """Klusi nomest nezināmu etiķeti nozīmētu pazaudēt jaunu frakciju."""
    assert normalize_faction("XYZ") == "XYZ"


def test_normalize_empty_becomes_none():
    """Prezidija locekļi balso bez frakcijas; no 2026-04-16 šūna ir tukša."""
    assert normalize_faction(None) is None
    assert normalize_faction("") is None
    assert normalize_faction("   ") is None


def test_normalize_map_targets_are_themselves_canonical():
    """Karte nedrīkst rādīt uz vērtību, kurai pašai vajag normalizāciju."""
    for src, dst in FACTION_NORMALIZE.items():
        assert dst not in FACTION_NORMALIZE, f"{src}->{dst} ir ķēde, ne kanonizācija"


# ──────────────────────────────────────────────────────────────────
# 3. Ceļu paritāte — šeit ražošanā nokrita
# ──────────────────────────────────────────────────────────────────

_SEP = "|"


def _snapshot_with(faction: str) -> str:
    """Playwright pieejamības snapshot, kādu lasa parse_vote_snapshot.

    Formāts ir `cell "TEKSTS" [ref=eN]` (nevis HTML) — sk.
    `src/saeima/votes.py::parse_vote_snapshot` cell_pattern.
    """
    cells = ["1.", "Aleksejs Rosļikovs", faction, "Par"]
    return "\n".join(f'cell "{c}" [ref=e{i}]' for i, c in enumerate(cells))


def test_html_table_parser_stores_canonical_label():
    res = parse_vote_snapshot(_snapshot_with("ST!"))
    factions = {iv.faction for iv in res.individual_votes}
    assert factions == {"ST"}, f"HTML parseris glabāja {factions}"


def test_js_backfill_parser_stores_canonical_label():
    """p3_backfill_year_urllib.py::_decode_entry — TAS ceļš, kas apgāja karti.

    Līdz 2026-09-04 tas ņēma `parts[2].strip()` verbatim un atkārtoti ielika
    7 448 `ST!` rindas pēc 2026-08-04 migrācijas.
    """
    from scripts.p3_backfill_year_urllib import _FIELD_SEP, _decode_entry

    entry = _FIELD_SEP.join(["1.", "Aleksejs+Rosl%C4%ABkovs", "ST!", "Par"])
    name, faction, vote = _decode_entry(entry)
    assert faction == "ST", f"JS backfill parseris glabāja {faction!r}"
    assert vote == "Par"
    assert "Ros" in name


def test_both_scrape_parsers_agree_on_every_recognised_cell():
    """Paritāte pār VISU atpazīto komplektu, ne tikai pār ST!."""
    from scripts.p3_backfill_year_urllib import _FIELD_SEP, _decode_entry

    mismatches = {}
    for cell in sorted(FACTION_CELL_VALUES):
        html_res = parse_vote_snapshot(_snapshot_with(cell))
        html_faction = next(iter({iv.faction for iv in html_res.individual_votes}), None)
        _, js_faction, _ = _decode_entry(_FIELD_SEP.join(["1.", "Deputats", cell, "Par"]))
        if html_faction != js_faction:
            mismatches[cell] = (html_faction, js_faction)
    assert not mismatches, (
        f"ingest ceļi nesakrīt (no {len(FACTION_CELL_VALUES)} pārbaudītām "
        f"šūnām): {mismatches}"
    )


def test_playwright_backfill_path_normalizes_too():
    """Trešais ceļš (p3_backfill_year.py) sauc to pašu palīgu.

    Tā šūnas nāk no pārlūkā izpildīta JS, tāpēc tur nav ko parsēt Python pusē —
    vārti ir tie, ka modulis importē kopīgo funkciju un lieto to pie
    IndividualVote būves.
    """
    from pathlib import Path

    src = Path("scripts/p3_backfill_year.py").read_text(encoding="utf-8")
    assert "from src.saeima.votes import normalize_faction" in src
    assert "faction=normalize_faction(d.get(\"faction\"))" in src
