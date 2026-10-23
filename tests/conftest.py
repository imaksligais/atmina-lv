"""Pytest collection guards.

1. **Optional-dependency skip** — some test files exercise heavy ML / fetch
   dependencies (faster-whisper, pyannote.audio, yt-dlp) not part of the
   default install. When absent, collection ImportError aborts the whole run.
   We skip those modules so the rest of the suite still runs locally.
   Re-enable simply by ``pip install faster-whisper pyannote.audio yt-dlp``.

2. **Pre-existing-failure xfail** — `docs/refactor/baseline-2026-04-29.md`
   tracked known-failing tests that existed BEFORE Phase 0 refactoring. We
   xfail them with strict=False so ``bash scripts/check.sh`` stays green on
   master while a NEW failure (any other test) still fails the script. As of
   2026-06-08 all three baseline entries were triaged and resolved, so
   ``_BASELINE_XFAIL`` is empty; the mechanism stays for future baselines.
   Removing an entry when it gets genuinely fixed is a deliberate one-line edit.
"""

from __future__ import annotations

import gc
import importlib.util
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

collect_ignore_glob: list[str] = []

# --- TypeSafe veto pin ------------------------------------------------------
#
# src/matcher.py reads ATMINA_TYPESAFE_VETO at import. If the operator ever
# sets it machine-wide (shadow/enforce), tests/test_matcher.py would call the
# paid API on every surname-only fixture. Pin "off" before any src import;
# tests that exercise the hook patch src.matcher.TYPESAFE_VETO_MODE directly.
os.environ["ATMINA_TYPESAFE_VETO"] = "off"

# Same reason for Saeima vote topics: `store_vote()` asks Jev for a new
# document's topic (src.saeima.topics.topic_for_new_vote) and this machine has
# the key, so every store_vote test would be a paid call. "off" = keyword
# fallback (today's topic, decision `pending`). Read at call time; tests that
# exercise the classifier path set it to "on" and stub classify_jev.
os.environ["ATMINA_VOTE_TOPIC_CLASSIFIER"] = "off"

# --- Parallel workers (pytest-xdist) on Windows ------------------------------
#
# check.sh runs the suite with `-n auto`. twikit resets the asyncio policy to
# the Selector loop on import, which cannot spawn subprocesses, so Playwright's
# sync API (render fixture) dies with NotImplementedError whenever a twikit
# import lands earlier in the same worker. Re-assert Proactor before each test.
@pytest.fixture(autouse=True)
def _win_proactor_policy():
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    yield


# --- 0. Pagaidu faili E diskā, pytest pārvaldītā mapē ----------------------
#
# 104 testu faili taisa `tempfile.mkstemp(suffix=".db")`; uz Windows `unlink`
# neizdodas, kamēr testējamais kods (`get_db()`) tur savienojumu atvērtu, un
# teardown to norij. Līdz 2026-09-02 tas bija noplūdinājis 26k failu / 13,7 GB
# lietotāja AppData/Local/Temp mapē C diskā (~1 GB dienā).
#
# Labojums: pirms jebkura testa Python pagaidu bāze tiek pārcelta uz
# `<repo>/.pytest-tmp`. Pytest savu numurēto mapi (`pytest-of-<user>/pytest-N`,
# glabā trīs pēdējos palaidienus, slēdzene pret paralēliem palaidieniem) taisa
# TAJĀ PAŠĀ bāzē, jo `getbasetemp()` lasa `tempfile.gettempdir()` lēni, pirmajā
# `tmp_path` pieprasījumā. Tāpēc gan pytest, gan `mkstemp` faili krīt vienā
# E diska mapē, ko pytest pats rotē. Apzināti NE `--basetemp=` addopts: fiksētu
# basetemp pytest iztīra katra palaidiena SĀKUMĀ, un divi pārklājoši palaidieni
# (check.sh fonā + aģenta pytest — 2026-09-02 tā notika) sabojātu viens otru.
_TMP_ROOT = Path(__file__).resolve().parent.parent / ".pytest-tmp"


# --- 4. The production DB is unreachable by default -------------------------
#
# Public CI has no data/atmina.db; this machine always does. So a test that
# forgets to pass its own DB silently READ the live DB here and failed only
# after a push (2026-09-13, 2026-09-23, and 2026-09-24 caught just before one:
# src/confidence_drift.py kept a private path that escaped the test's
# monkeypatch). The row-count tripwire below catches writes, never reads.
#
# Fix: before collection imports any src module, every default DB path points
# into a directory that does not exist, so sqlite fails with "unable to open
# database file" on a path that names the cause. Tests that genuinely read the
# production DB name it explicitly (_PROD_DB / PRODUCTION_DB_PATH) and are
# unaffected. Measured 2026-09-24: with this in place 3009 passed, 1 failed —
# a test asserting the old constant (fixed to read PRODUCTION_DB_PATH).
# Locked by tests/test_db_path_guard.py.
BLOCKED_DB_PATH = str(_TMP_ROOT / "__tests_must_not_use_production_db__" / "atmina.db")


def _block_default_db_paths() -> None:
    import src.db as db
    import src.render._common.constants as render_constants
    import src.wiki_format as wiki_format

    db.DB_PATH = BLOCKED_DB_PATH
    render_constants.DEFAULT_DB_PATH = BLOCKED_DB_PATH
    wiki_format.DEFAULT_DB_PATH = BLOCKED_DB_PATH


def pytest_configure(config):
    _TMP_ROOT.mkdir(exist_ok=True)
    tempfile.tempdir = str(_TMP_ROOT)
    _block_default_db_paths()
    import src.db as db
    _REAL_GET_DB.append(db.get_db)


# --- 5. Stale get_db binding guard ----------------------------------------
#
# Most src modules do `from src.db import get_db` — a by-name binding made at
# FIRST import. A fixture that patches src.db.get_db and only then imports a
# module (src.social → src.matcher, …) for the first time in the run binds
# that module to the test stub for good: monkeypatch.setattr on the module's
# own get_db records the stub as the "original" and "restores" it. Found
# 2026-10-01: tests/test_social.py run before tests/test_matcher.py left
# src.matcher reading a deleted 4-politician temp DB and 15 baseline cases
# failed — invisible in the alphabetical check.sh order. After every test
# (monkeypatch already undone) no src module may hold a non-real get_db; the
# guard repairs the binding so the leak cannot cascade, then fails the test
# that caused it.
_REAL_GET_DB: list = []


def repair_stale_get_db_bindings(real) -> list[str]:
    """Rebind every src module whose get_db is not `real`; return their names."""
    leaked = []
    for name, mod in list(sys.modules.items()):
        if (name == "src" or name.startswith("src.")) and mod is not None:
            bound = mod.__dict__.get("get_db")
            if bound is not None and bound is not real:
                leaked.append(name)
                mod.get_db = real
    return leaked


@pytest.fixture(autouse=True)
def _og_cards_without_chromium(request, monkeypatch):
    """OG kartīšu PNG (src/render/_common/og_render.py) testos neuzzīmē ar
    Chromium: ~15 testu faili renderē profilus/partijas/tēmas, un katrs
    palaistu pārlūku desmitiem kartīšu (xdist slodzē tas avarēja). Aizstājējs
    uzraksta failu, lai «PNG eksistē» pārbaudes paliek patiesas. Tests, kas
    pārbauda pašu Playwright šuvi, liek ``@pytest.mark.real_og``."""
    if request.node.get_closest_marker("real_og"):
        return
    from src.render._common import og_render

    def _fake_shoot(todo):
        for out_path, _html in todo:
            Path(out_path).write_bytes(b"png")
            yield out_path

    monkeypatch.setattr(og_render, "_shoot", _fake_shoot)


@pytest.fixture(autouse=True)
def _no_stale_get_db_binding():
    yield
    if not _REAL_GET_DB:
        return
    leaked = repair_stale_get_db_bindings(_REAL_GET_DB[0])
    if leaked:
        pytest.fail(
            "get_db left bound to a test stub in: " + ", ".join(sorted(leaked))
            + " — import these modules BEFORE patching src.db.get_db "
            "(tests/conftest.py § 5)", pytrace=False)


@pytest.fixture(scope="session", autouse=True)
def _tempfiles_live_under_repo_pytest_tmp(tmp_path_factory):
    d = tmp_path_factory.mktemp("sqlite")
    tempfile.tempdir = str(d)
    yield
    gc.collect()  # aizver pamestos sqlite3 savienojumus, pirms pytest rotē mapi
    tempfile.tempdir = str(_TMP_ROOT)


# --- 3. Production-DB tripwire -------------------------------------------
#
# Tests must never write to data/atmina.db. Nothing enforced that, and on
# 2026-08-02 it cost real rows: a summary `log_action()` was added to
# scripts/morning_ingest.py, and tests/test_morning_ingest.py calls main()
# with all five steps stubbed but had no reason to stub a sixth side effect
# that did not exist when it was written. Three pytest runs wrote 18 rows
# into the live `logs` table, and the only reason anyone noticed is that the
# routine reporter started reading that table the same afternoon.
#
# This is a tripwire, not a sandbox: it compares row counts before and after
# the session, so it stays out of the way of tests that legitimately READ the
# production DB, and it names the table that grew. Silent on a missing DB so
# hermetic CI is unaffected.
_PROD_DB = Path(__file__).resolve().parent.parent / "data" / "atmina.db"
# image_audit pievienota 2026-09-07 (verdikts 47b): tā ir attēlu MĒNEŠA BUDŽETA
# saucējs (griesti 5,00 USD), tāpēc testa ierakstīta rinda nav tikai troksnis —
# tā tērē reālu budžetu `budget_check()` acīs.
_WATCHED = ("logs", "claims", "documents", "context_notes", "contradictions",
            "political_tensions", "analyses", "tracked_politicians",
            "image_audit")


def _prod_counts() -> dict[str, int] | None:
    if not _PROD_DB.exists() or _PROD_DB.stat().st_size == 0:
        return None
    try:
        db = sqlite3.connect(f"file:{_PROD_DB.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _WATCHED}
    except sqlite3.Error:
        return None
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _production_db_is_not_a_test_fixture():
    before = _prod_counts()
    yield
    after = _prod_counts()
    if before is None or after is None:
        return
    grew = {t: (before[t], after[t]) for t in before if before[t] != after[t]}
    assert not grew, (
        "Testi ierakstīja ražošanas DB (data/atmina.db):\n  "
        + "\n  ".join(f"{t}: {b} -> {a}" for t, (b, a) in grew.items())
        + "\nStubo blakusefektu testā (piem. monkeypatch uz log_action) vai "
          "padod db_path uz pagaidu DB. Rindas jāizņem ar pāra rollback."
    )

_OPTIONAL = {
    "faster_whisper": ["test_video_ingest_asr.py"],
    "pyannote.audio": ["test_video_ingest_diarize.py"],
    "yt_dlp": ["test_video_ingest_fetch.py"],
}

for module, files in _OPTIONAL.items():
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ModuleNotFoundError, ValueError):
        spec = None
    if spec is None:
        collect_ignore_glob.extend(files)


# Pre-existing baseline failures — see docs/refactor/baseline-2026-04-29.md.
# Format: nodeid suffix → reason. Match is "endswith" so it survives Windows
# vs POSIX path separators.
# All three 2026-04-29 baseline failures were resolved 2026-06-08 (audit triage):
# matplotlib test now genuinely passes (importorskip guard added); the highlights
# test was a fixture time-bug (now seeds relative dates vs the rolling lookback
# window); the relay-author test encoded an OBSOLETE contract (rewritten to assert
# role='mentioned' per the 2026-04-25 commentator demotion — it was never a real
# regression). Mechanism kept (empty) for future baselines.
_BASELINE_XFAIL: dict[str, str] = {}


def pytest_collection_modifyitems(config, items):
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        for suffix, reason in _BASELINE_XFAIL.items():
            if nodeid.endswith(suffix):
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                break


# --- support vārti izslēgti testiem, kas pārbauda citu save_analysis uzvedību --
#
# Kopš 2026-09-30 save_analysis() neglabā `position` pozīciju bez burtiska
# `support` fragmenta no dokumenta teksta (src/support.py). Atomiskuma, dedup,
# NEEDS_REVIEW un junction testi nav par to; to fiksturi rakstīti pirms vārtiem.
# Moduļi, kas lieto šo fiksturu, to dara ar `pytestmark`. Pašus vārtus sargā
# tests/test_support_gate.py (bez šī fikstura).
@pytest.fixture
def support_gate_off(monkeypatch):
    monkeypatch.setattr("src.analyze.check_support", lambda support, text: (None, ""))


# ── Render fikstūras vietne (pārcelta no tests/test_render_chars.py 2026-10-21) ──
# Session-scope fikstūra conftest.py — vienreiz uz sesiju (un uz xdist darbinieku).
# Ja tā būtu importēta testu moduļos, pytest katram importētājam reģistrētu
# atsevišķu definīciju un vietni renderētu atkārtoti.

@pytest.fixture(scope="session")
def _stable_assets_version():
    """Pin assets_version to ``"test"`` for the whole session.

    pytest's built-in monkeypatch is function-scoped; we need session
    scope here because rendered_site is session-scoped.
    """
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    mpatch.setenv("ATMINA_ASSETS_VERSION", "test")
    yield
    mpatch.undo()


# Fikstūra glabājas gzipēta (6.3, 2026-09-05); atspiestais teksts ir
# baitu-identisks iepriekš komitētajam .sql — sk. tests/fixture_sql.py.
# After all fixture data; pins relative-time rendering ("pirms N dienām",
# 7/14/28-day windows) to a fixed point so baselines never drift on the wall
# clock. freezegun covers src.db.now_lv*/today_lv(), which every render
# window goes through (src/render/ has no bare date.today() since 2026-09-28).
FREEZE_INSTANT = "2026-06-01 12:00:00"


@pytest.fixture(scope="session")
def render_fixture_db(tmp_path_factory):
    """Build a tmp DB from the committed fixture SQL.

    Schema comes from init_db (static schema.sql + sqlite-vec vtabs) plus the
    Saeima tables (init_saeima_tables/init_saeima_bills — NOT created by
    init_db). Three columns present in the live prod DB but absent from the
    fresh init_db schema (tracked_politicians.x_handle, documents.is_paywall,
    documents.summary) are added so the test DB faithfully mirrors prod for
    render; see the schema-drift note in the plan. Data is then loaded from the
    committed .sql (data-only INSERTs).
    """
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path_factory.mktemp("render_fixture_db") / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            conn.execute(ddl)
        except Exception:  # noqa: BLE001 — column already present if schema.sql is later synced
            pass
    from tests.fixture_sql import load_render_fixture_sql

    conn.executescript(load_render_fixture_sql())
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="session")
def rendered_site(tmp_path_factory, _stable_assets_version, render_fixture_db):
    from freezegun import freeze_time

    from src.render import generate_public_site, generate_statistika
    from _pytest.monkeypatch import MonkeyPatch

    # Hermetic: the render path downloads chart.js + the annotation plugin
    # from a CDN, which made every pytest session go to the network — and
    # since 2026-08-04 a failed download RAISES (no silent stub), so an
    # offline run would kill the whole session fixture. Tests assert on
    # rendered HTML, not on the vendored JS payload; a marker file is enough.
    def _fake_download(dest, *a, **k):
        Path(dest).write_text("/* test asset stub */", encoding="utf-8")

    mpatch = MonkeyPatch()
    for mod in ("src.render._orchestrator", "src.render.statistika"):
        import importlib
        m = importlib.import_module(mod)
        mpatch.setattr(m, "_download_chart_js", _fake_download)
        if hasattr(m, "_download_annotation_plugin"):
            mpatch.setattr(m, "_download_annotation_plugin", _fake_download)
        if hasattr(m, "_download_d3"):
            mpatch.setattr(m, "_download_d3", _fake_download)

    # CVK vēlēšanu rezultāti (partijas.html bloks): fiksēta fixture kopija, lai
    # baseline nemainās ar katru scripts/fetch_cvk_results.py palaišanu.
    import src.render.parties as _parties
    mpatch.setattr(
        _parties, "ELECTION_RESULTS_PATH",
        Path(__file__).parent / "fixtures" / "cvk_sv2026_rezultati.yaml",
    )
    # personas.html «15. Saeima» rails: ievēlētie + jauno profilu kohorta —
    # fiksētas kopijas, lai oficiālā CVK saraksta nomaiņa nepārbīda baseline.
    import src.render.personas as _personas
    mpatch.setattr(
        _personas, "ELECTED_PATH",
        Path(__file__).parent / "fixtures" / "cvk_sv2026_ievēlētie.yaml",
    )
    mpatch.setattr(
        _personas, "COHORT_PATH",
        Path(__file__).parent / "fixtures" / "15saeima_kohorta.yaml",
    )
    # saeima.html (15. Saeimas pusloks): tās pašas fiksētās sastāva + rezultātu kopijas.
    import src.render.saeima as _saeima
    mpatch.setattr(
        _saeima, "ELECTED_PATH",
        Path(__file__).parent / "fixtures" / "cvk_sv2026_ievēlētie.yaml",
    )
    mpatch.setattr(
        _saeima, "RESULTS_PATH",
        Path(__file__).parent / "fixtures" / "cvk_sv2026_rezultati.yaml",
    )

    # Likumu lapas (likumi.html, likumi/*.html, likumprojektu tituli): fiksēta
    # wiki/laws kopija, lai rutīnas wiki sync nepārbīda baseline.
    import src.render.laws as _laws
    mpatch.setattr(_laws, "LAWS_DIR", Path(__file__).parent / "fixtures" / "laws")

    # Analīžu/atradumu md (analizes.html, analizes/*.html, sākumlapas un pārskatu
    # «jaunākā analīze»): fiksēta content/analizes kopija — citādi katrs jauns
    # publicēts atradums pārbīda 5 baseline (2026-10-17, pilsonību atradums).
    import src.render.analyses as _analyses
    mpatch.setattr(_analyses, "CONTENT_DIR", Path(__file__).parent / "fixtures" / "content")

    # OG kartīšu PNG (pretrunas/profili/partijas/tēmas/ievads, ~330) šie testi
    # nelasa — Playwright aizstāts ar failu-uzrakstītāju (tests/test_og_cards.py).
    from src.render._common import og_render

    def _fake_shoot(todo):
        for out_path, _html in todo:
            Path(out_path).write_bytes(b"png")
            yield out_path

    mpatch.setattr(og_render, "_shoot", _fake_shoot)

    out = tmp_path_factory.mktemp("render_chars_site")
    try:
        with freeze_time(FREEZE_INSTANT):
            generate_public_site(db_path=render_fixture_db, output_dir=str(out))
            # Statistika reads a SEPARATE CSP/events store (signature is
            # output_dir, csp_db_path, events_path), NOT the main atmina DB — no
            # statistika baseline was among the drifting char tests. Left on
            # defaults; wrapped in freeze_time only for any timestamp it emits.
            generate_statistika(output_dir=str(out))
    finally:
        mpatch.undo()
    return out / "atmina"
