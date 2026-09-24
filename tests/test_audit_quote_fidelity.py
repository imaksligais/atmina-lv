"""`scripts/audit_quote_fidelity.py` saucēji jālasa no tā, ko raksta ĪSTAIS rakstītājs.

Divi defekti, abi atrasti 2026-08-09 vārtu auditā:

1. **Skaitītājs bija piesiets nullē.** Parafrāzes likums bija TIKAI prefikss
   (`quote.startswith(name)`), tāpēc `paraphrase: 0` bija fakts par likuma
   tvērumu, ne par korpusu — atstāsti ar uzvārdu teikuma vidū palika neredzami.
2. **Saucēja nebija vispār**, tāpēc „0" nebija atšķirams no „vaicājums neko
   neatdeva". Saucējs BEZ skaitītāja pārbaudes būtu padarījis nepatieso zaļo
   gaismu pārliecinošāku, ne godīgāku — tāpēc abi laboti vienā piegājienā.

Fikstūra raksta caur `store_claim()`, nevis ar roku rakstītiem `INSERT`, tieši
tāpēc, ka pretējā gadījumā tests apstiprinātu paša izdomātu formu — CLAUDE.md
(a) korolārijs, kura paraugs ir
`tests/test_wiki_lint.py::test_lint_reads_keys_wiki_sync_actually_writes`.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

from src.db import get_db, init_db, store_claim

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "audit_quote_fidelity", REPO / "scripts" / "audit_quote_fidelity.py"
)
aqf = importlib.util.module_from_spec(_spec)
sys.modules["audit_quote_fidelity"] = aqf
_spec.loader.exec_module(aqf)

DAY = "2026-08-09"
URL = "https://example.invalid/raksts"


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (1, 'Andris Kulbergs', 'Apvienotais saraksts', 'opponent')"
    )
    db.execute(
        """INSERT INTO documents (id, content, content_hash, source_url, scraped_at,
                                  platform, title)
           VALUES (1, 'raksta saturs', 'h1', ?, ?, 'web', 'Kāds virsraksts')""",
        (URL, f"{DAY} 10:00:00"),
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role)"
        " VALUES (1, 1, 'subject')"
    )
    db.commit()
    db.close()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _store(db_path: str, topic: str, quote: str | None) -> int:
    """Raksta caur ĪSTO rakstītāju — tas ir šī faila jēgas kodols."""
    return store_claim(
        opponent_id=1,
        topic=topic,
        stance="kaut kāda nostāja",
        quote=quote,
        source_url=URL,
        confidence=0.9,
        reasoning="tests",
        salience=0.6,
        stated_at=f"{DAY} 10:00:00",
        document_id=1,
        db_path=db_path,
    )


def test_denominators_match_what_the_real_writer_wrote(db_path):
    _store(db_path, "Budžets un finanses", 'Mēs to izdarīsim, saka viņš.')
    _store(db_path, "Pensijas", None)
    _store(db_path, "Veselība", "")

    _found, denom = aqf.audit(db_path, 0.0)
    assert denom["quoted"] == 1, denom
    assert denom["no_quote"] == 2, "citāta klasēm neredzamās rindas jāskaita atsevišķi"
    assert denom["titled"] == 3, denom


def test_surname_mid_quote_is_caught_as_its_own_class(db_path):
    """Šī rinda ir tieši tā, ko prefiksa likums palaida garām.

    Paraugs no dzīvās DB (#20529): „Valsts prezidenta nominētais premjera amata
    kandidāts Andris Kulbergs…" — žurnālista atstāsts `quote` laukā.
    """
    _store(db_path, "Valsts pārvalde",
           "Valsts prezidenta nominētais premjera amata kandidāts Andris Kulbergs sola reformas.")
    found, _denom = aqf.audit(db_path, 0.0)
    assert found["paraphrase"] == [], "prefiksa likums šo NEķer — tā ir cita klase"
    assert [e["id"] for e in found["paraphrase_mid"]], found


def test_prefix_paraphrase_stays_in_the_stronger_class(db_path):
    """Prefiksa forma nedrīkst noslīdēt jaunajā, vājākajā klasē."""
    _store(db_path, "Ekonomika", "Kulbergs norādīja, ka budžets ir jāpārskata.")
    found, _denom = aqf.audit(db_path, 0.0)
    assert [e["id"] for e in found["paraphrase"]], found
    assert found["paraphrase_mid"] == []


def test_genuine_first_person_quote_is_not_flagged(db_path):
    """Īsts citāts bez sava uzvārda nedrīkst nokļūt nevienā parafrāzes klasē."""
    _store(db_path, "Izglītība", 'Es uzskatu, ka skolotājiem jāmaksā vairāk.')
    found, _denom = aqf.audit(db_path, 0.0)
    assert found["paraphrase"] == []
    assert found["paraphrase_mid"] == []


def test_min_confidence_filter_moves_the_denominator_too(db_path):
    """Saucējs jāmēra pret TO PAŠU filtru, ko lieto klases — citādi tas melo."""
    cid = _store(db_path, "Sports", "kaut kas")
    db = get_db(db_path)
    db.execute("UPDATE claims SET confidence = 0.4 WHERE id = ?", (cid,))
    db.commit()
    db.close()

    _f_all, denom_all = aqf.audit(db_path, 0.0)
    _f_hi, denom_hi = aqf.audit(db_path, 0.85)
    assert denom_all["quoted"] == 1
    assert denom_hi["quoted"] == 0


def test_verbatim_catches_punctuation_drift(db_path):
    """(e) kodolklase: vienīgā novirze ir pieturzīme — normalizējošie testi to
    nekad neredz, burtiskais testam jāķer."""
    db = get_db(db_path)
    db.execute(
        "UPDATE documents SET content = 'Pilns raksta teksts: Mēs to izdarīsim "
        "saka viņš, un vēl cits teksts.' WHERE id = 1"
    )
    db.commit()
    db.close()
    _store(db_path, "Budžets un finanses", "Mēs to izdarīsim, saka viņš.")
    found, denom = aqf.audit(db_path, 0.0)
    assert denom["verbatim_checkable"] == 1, denom
    assert [e["id"] for e in found["verbatim"]], (
        "komata novirze no avota ir verbatim klase — rīks to nedrīkst nokavēt"
    )


def test_verbatim_passes_exact_substring(db_path):
    """Burtiski precīzs citāts dokumentā nedrīkst nokļūt verbatim klasē."""
    db = get_db(db_path)
    db.execute(
        "UPDATE documents SET content = 'Pilns raksta teksts: Mēs to izdarīsim, "
        "saka viņš. Un vēl cits teksts.' WHERE id = 1"
    )
    db.commit()
    db.close()
    _store(db_path, "Budžets un finanses", "Mēs to izdarīsim, saka viņš.")
    found, _denom = aqf.audit(db_path, 0.0)
    assert found["verbatim"] == [], found["verbatim"]


def test_verbatim_denominator_excludes_dead_document(db_path):
    """Claim bez dzīva dokumenta ir 'quoted', bet NAV verbatim pārbaudāms —
    SEGUMS rādā abus skaitļus, lai starpību nevar sajaukt ar datu zudumu."""
    _store(db_path, "Budžets un finanses", "Mēs to izdarīsim, saka viņš.")
    db = get_db(db_path)
    # FK neļauj dzēst dokumentu — claim bez dzīva dokumenta simulējam ar
    # document_id=NULL (datu kontrakts #6 to atļauj; LEFT JOIN dod NULL content).
    db.execute("UPDATE claims SET document_id = NULL")
    db.commit()
    db.close()
    found, denom = aqf.audit(db_path, 0.0)
    assert denom["quoted"] == 1
    assert denom["verbatim_checkable"] == 0
    assert found["verbatim"] == [], "bez dokumenta nav ko pārbaudīt — ne defekts"
