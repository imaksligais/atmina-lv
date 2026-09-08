"""Pretrunu KANDIDĀTU panelis — noraidītie kandidāti no `contradiction_hunt` logiem.

Operatora lūgums 2026-09-04: «would be interesting to see contradiction
candidates ... Just to check some myself and maybe sometimes publish what and
why.» Līdz šim `@contradiction-hunter` izvērtētie-un-noraidītie kandidāti
dzīvoja tikai apakšaģenta atskaitē, kas aiziet orkestratoram un pazūd; 09-04
tā pazuda seši pilnībā izvērtēti kandidāti.

Nesējs ir `logs.details` JSON lauks `rejected_candidates`, NEVIS jauna tabula:
`log_action('contradiction_hunt', ...)` jau tagad ir obligāts solis, kas iet
katru dienu, ieskaitot nulles ražas dienas — tas ir tieši tas, kas atšķir
godīgu nulli no «netika palaists». Piekabinot kandidātus tam, tvērums manto
jau ieviestu ieradumu; jauna tabula būtu jauns solis, ko zem slodzes var klusi
izlaist (T11).
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile

import pytest

from src.db import init_db


@pytest.fixture(autouse=True)
def _reset_cache():
    from src.dashboard.views import candidates

    candidates._CACHE.clear()
    candidates._CACHE.update({"key": None, "ts": None, "result": None})
    yield
    candidates._CACHE.clear()
    candidates._CACHE.update({"key": None, "ts": None, "result": None})


@pytest.fixture
def cand_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _seed_hunt(db, *, timestamp: str, details: dict, status: str = "success"):
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
        (timestamp, "contradiction_hunt", status, json.dumps(details, ensure_ascii=False)),
    )


def _candidate(**over):
    base = {
        "claim_old": 689413,
        "claim_new": 709028,
        "politician_id": 10,
        "politician": "Andris Kulbergs",
        "topic": "Aizsardzība un drošība",
        "kind": "position_over_time",
        "severity_guess": "minor_shift",
        "fp_class": "FP5",
        "why": "Fiziska apsardze nav tas pats, kas rīcības plānu segums.",
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------
# Reading what the writer actually writes
# --------------------------------------------------------------------------


def test_panel_reads_the_key_the_hunter_actually_writes(cand_db):
    """CLAUDE.md korolārijs (a): pārbaudītāja testam jāapliecina, ka tas lasa
    tieši to atslēgu, ko rakstītājs raksta. Šis tests ir vārts pret to, ka
    aģenta prompts un panelis aizdreifē uz dažādiem nosaukumiem."""
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    _seed_hunt(
        db,
        timestamp="2026-09-04 23:43:50",
        details={
            "date": "2026-09-04",
            "claims_checked": 46,
            "found": 0,
            "rejected_candidates": [_candidate()],
        },
    )
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")

    assert ctx["total"] == 1
    row = ctx["candidates"][0]
    assert row["politician"] == "Andris Kulbergs"
    assert row["claim_old"] == 689413
    assert row["claim_new"] == 709028
    assert row["fp_class"] == "FP5"
    assert "apsardze" in row["why"]
    assert row["date"] == "2026-09-04"


def test_denominator_is_reported_not_just_the_findings(cand_db):
    """Vārts bez saucēja nav pierādījums. Panelim jāziņo, cik medību palaidienu
    tas izskatīja, ne tikai cik kandidātu atrada — citādi tukšs panelis nozīmē
    gan «nebija kandidātu», gan «medības nepalaidās»."""
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    _seed_hunt(db, timestamp="2026-09-04 23:00:00",
               details={"date": "2026-09-04", "claims_checked": 46, "found": 0})
    _seed_hunt(db, timestamp="2026-09-03 23:00:00",
               details={"date": "2026-09-03", "claims_checked": 29, "found": 0,
                        "rejected_candidates": [_candidate(claim_new=706100)]})
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")

    assert ctx["hunts_scanned"] == 2
    assert ctx["hunts_with_candidates"] == 1
    assert ctx["claims_checked"] == 75
    assert ctx["total"] == 1


def test_empty_is_distinguishable_from_never_ran(cand_db):
    """Nulle kandidātu ar palaistām medībām != neviena medību palaidiena."""
    from src.dashboard.views.candidates import get_candidates_context

    ctx_never = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")
    assert ctx_never["hunts_scanned"] == 0
    assert ctx_never["never_ran"] is True

    db = sqlite3.connect(cand_db)
    _seed_hunt(db, timestamp="2026-09-04 23:00:00",
               details={"date": "2026-09-04", "claims_checked": 46, "found": 0})
    db.commit()
    db.close()

    from src.dashboard.views import candidates as _c
    _c._CACHE.update({"key": None, "ts": None, "result": None})

    ctx_ran = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")
    assert ctx_ran["hunts_scanned"] == 1
    assert ctx_ran["never_ran"] is False
    assert ctx_ran["total"] == 0


# --------------------------------------------------------------------------
# Robustness — the writer is an LLM agent, so the payload will drift
# --------------------------------------------------------------------------


def test_malformed_details_never_break_the_panel(cand_db):
    """`details` raksta aģents, tāpēc forma dreifēs. Slikta rinda drīkst pazust
    no saraksta, bet nedrīkst nogāzt paneli — un tā jāskaita atsevišķi, lai
    kluss zudums neizskatītos pēc tīras dienas."""
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
        ("2026-09-04 23:00:00", "contradiction_hunt", "success", "{not json"),
    )
    _seed_hunt(db, timestamp="2026-09-04 23:10:00",
               details={"date": "2026-09-04", "rejected_candidates": "not-a-list"})
    _seed_hunt(db, timestamp="2026-09-04 23:20:00",
               details={"date": "2026-09-04", "rejected_candidates": [{"why": "no ids"}]})
    _seed_hunt(db, timestamp="2026-09-04 23:30:00",
               details={"date": "2026-09-04", "rejected_candidates": [_candidate()]})
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")

    assert ctx["total"] == 1
    assert ctx["malformed"] == 3
    assert ctx["candidates"][0]["politician"] == "Andris Kulbergs"


def test_other_log_actions_are_ignored(cand_db):
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
        ("2026-09-04 23:00:00", "morning_ingest", "success",
         json.dumps({"rejected_candidates": [_candidate()]})),
    )
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")
    assert ctx["hunts_scanned"] == 0
    assert ctx["total"] == 0


def test_window_excludes_older_hunts(cand_db):
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    _seed_hunt(db, timestamp="2026-09-04 23:00:00",
               details={"date": "2026-09-04", "rejected_candidates": [_candidate()]})
    _seed_hunt(db, timestamp="2026-07-01 23:00:00",
               details={"date": "2026-07-01", "rejected_candidates": [_candidate()]})
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=7, today="2026-09-04")
    assert ctx["total"] == 1
    assert ctx["candidates"][0]["date"] == "2026-09-04"


def test_newest_candidate_first(cand_db):
    from src.dashboard.views.candidates import get_candidates_context

    db = sqlite3.connect(cand_db)
    _seed_hunt(db, timestamp="2026-09-02 23:00:00",
               details={"date": "2026-09-02",
                        "rejected_candidates": [_candidate(politician="Vecākais")]})
    _seed_hunt(db, timestamp="2026-09-04 23:00:00",
               details={"date": "2026-09-04",
                        "rejected_candidates": [_candidate(politician="Jaunākais")]})
    db.commit()
    db.close()

    ctx = get_candidates_context(db_path=cand_db, days=30, today="2026-09-04")
    assert [c["politician"] for c in ctx["candidates"]] == ["Jaunākais", "Vecākais"]


# --------------------------------------------------------------------------
# Panel is local-only by construction (unproven accusations about real people)
# --------------------------------------------------------------------------


def test_panel_renders_on_index_without_leaking_to_public_render(cand_db):
    """Noraidīts kandidāts ir nepierādīts apgalvojums par nosauktu cilvēku.
    Tas drīkst dzīvot TIKAI localhost dashboard-ā — nekad publiskajā renderī."""
    from src.dashboard.server import create_app

    db = sqlite3.connect(cand_db)
    _seed_hunt(db, timestamp="2026-09-04 23:00:00",
               details={"date": "2026-09-04", "rejected_candidates": [_candidate()]})
    db.commit()
    db.close()

    app = create_app(db_path=cand_db)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Andris Kulbergs" in body

    # The public render must have no reader for this key at all.
    import subprocess
    hits = subprocess.run(
        ["git", "grep", "-l", "rejected_candidates", "--", "src/render"],
        capture_output=True, text=True,
    )
    assert hits.stdout.strip() == "", (
        "rejected_candidates reached the public render path: " + hits.stdout
    )
