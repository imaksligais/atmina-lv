"""Pārmantotais māsas kopsavilkums nedrīkst nest CITA balsojuma iznākumu.

`ingest_saeima_missing_votes.py` trūkstošam balsojumam ieliek tā paša
`document_nr` garāko kopsavilkumu. Divas instances pēc kārtas:

- 2026-09-25: 947/Lp14 priekšlikums Nr.46 un 2. lasījums mantoja «Pirmajā
  lasījumā Saeima atbalstīja (52 par, 14 pret, 1 atturas)» — 177 claims.
- 2026-09-26: 1117/Lm14 iekļaušana darba kārtībā mantoja 17.09. frakciju
  sadalījumu («AS atturējās, bet NA nebalsoja» — faktiski abas par);
  1553/Lp14 priekšlikums Nr.3 mantoja termiņa balsojuma teikumu. 145 claims.

Teksts nonāk katrā `saeima_vote` stancē, tāpēc kļūda pavairojas ×deputāti.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

_BASE_1117 = ("Desmit LPV deputātu lēmuma projekts, ar kuru Saeima paustu viedokli "
              "Satversmes tiesas lietā Nr. 2026-15-0103.")
_BASE_1553 = ("Komisijas likumprojekts uzliek enerģētikas sistēmu operatoriem pienākumu "
              "noteikt kritiski svarīgos amatus.")


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "ingest_missing_votes_sib", REPO / "scripts" / "ingest_saeima_missing_votes.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["ingest_missing_votes_sib"] = m
    spec.loader.exec_module(m)
    return m


def test_faction_breakdown_of_sibling_is_dropped(mod):
    inherited = (_BASE_1117 + " Šis balsojums izšķīra tikai jautājuma iekļaušanu sēdes darba "
                 "kārtībā; par balsoja ZZS, LPV, pret — Jaunā Vienotība, AS atturējās, bet NA nebalsoja.")
    motif = ("Par iekļaušanu nākamās kārtējās sēdes darba kārtībā. Par Saeimas viedokli "
             "saistībā ar ... lietu Nr. 2026-15-0103 (1117/Lm14)")
    out = mod._clean_inherited_summary(inherited, motif)
    assert "atturējās" not in out and "nebalsoja" not in out
    assert out == (_BASE_1117 + " Šis balsojums izšķīra tikai jautājuma iekļaušanu "
                   "nākamās kārtējās sēdes darba kārtībā.")


def test_proposal_vote_gets_its_own_procedure_sentence(mod):
    inherited = (_BASE_1553 + " Šis balsojums izšķīra tikai to, vai priekšlikumu iesniegšanas "
                 "termiņš otrajam lasījumam būtu viena diena.")
    motif = "Par priekšlikumu Nr.3. Grozījums Enerģētikas likumā (1553/Lp14), 2.lasījums, steidzams"
    out = mod._clean_inherited_summary(inherited, motif)
    assert "termiņš" not in out
    assert out == (_BASE_1553 + " Šis balsojums bija par otrā lasījuma priekšlikumu Nr. 3, "
                   "nevis par likumprojektu kopumā.")


def test_sibling_reading_tally_is_dropped(mod):
    inherited = _BASE_1553 + " Pirmajā lasījumā Saeima atbalstīja (52 par, 14 pret, 1 atturas)."
    out = mod._clean_inherited_summary(inherited, "Grozījums Enerģētikas likumā (1553/Lp14), 2.lasījums")
    assert out == _BASE_1553


def test_tally_inside_description_sentence_gives_null(mod):
    # iznākums ieausts pašā apraksta teikumā — griezt nevar, tāpēc NULL (@saeima-tracker aizpilda)
    inherited = "Grozījumi Saeimas kārtības rullī, ko Saeima atbalstīja (81 par, 1 pret) otrajā lasījumā."
    assert mod._clean_inherited_summary(inherited, "Grozījumi Saeimas kārtības rullī (857/Lp14), 3.lasījums") is None


def test_unknown_procedural_motif_gives_null(mod):
    # procedūra, kurai nav droša teikuma (termiņa vērtība, u.c.) — labāk NULL nekā minējums
    motif = "Par priekšlikumu iesniegšanas termiņu 1 diena. Grozījums Enerģētikas likumā (1553/Lp14), 1.lasījums"
    assert mod._clean_inherited_summary(_BASE_1553, motif) is None


@pytest.mark.parametrize("motif, sentence", [
    ("Grozījums Enerģētikas likumā (1553/Lp14), nodošana komisijām",
     "Šis balsojums izšķīra tikai likumprojekta nodošanu komisijām."),
    ("Par likumprojekta atzīšanu par steidzamu. Grozījums Enerģētikas likumā (1553/Lp14), 1.lasījums",
     "Šis balsojums izšķīra tikai to, vai likumprojektu atzīt par steidzamu."),
])
def test_known_procedures(mod, motif, sentence):
    assert mod._clean_inherited_summary(_BASE_1553, motif) == _BASE_1553 + " " + sentence


def test_sibling_summary_path_cleans_what_it_inherits(mod):
    # vārti pašam ceļam, ne tikai tīrīšanas funkcijai: skripts tiešām izsauc tīrīšanu
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE saeima_votes (document_nr TEXT, summary TEXT)")
    db.execute("INSERT INTO saeima_votes VALUES (?, ?)",
               ("1553/Lp14", _BASE_1553 + " Pirmajā lasījumā Saeima atbalstīja (52 par, 14 pret)."))
    out = mod._sibling_summary(db, "1553/Lp14", "Grozījums Enerģētikas likumā (1553/Lp14), 2.lasījums")
    assert out == _BASE_1553
