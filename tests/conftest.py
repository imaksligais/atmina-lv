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
