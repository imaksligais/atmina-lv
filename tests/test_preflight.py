"""Regression test for the preflight DB-path default.

The old default was the legacy ``politracker.db``: ``preflight_check()`` ran
``init_db()`` on it (creating an empty legacy file) and then validated the
tables it had just created, never inspecting the real operational DB. Because
``src/ingest.py`` calls ``preflight_check()`` with no argument, a no-arg call
must resolve the canonical ``DB_PATH`` (``data/atmina.db``).

The signature default is now ``None`` (late-bound, resolved at CALL time via
``get_db`` — so ``monkeypatch.setattr(db, "DB_PATH", ...)`` is honored rather
than baked in at import). This test therefore asserts the *behavior* — a
no-arg call targets whatever ``DB_PATH`` resolves to at call time, and never
the legacy ``politracker.db`` — instead of the def-time default value.
"""
from __future__ import annotations

import inspect

import pytest

from src import preflight as preflight_module
from src.db import DB_PATH
from src.preflight import ensure_analysis_env, preflight_check, repo_python


def test_preflight_default_is_late_bound_none():
    # Default is None (call-time resolution), NOT a baked-in path.
    default = inspect.signature(preflight_check).parameters["db_path"].default
    assert default is None
    # The canonical target is still atmina.db, never the legacy file.
    assert DB_PATH == "data/atmina.db"
    assert "politracker" not in DB_PATH


def test_preflight_no_arg_targets_monkeypatched_db(tmp_path, monkeypatch):
    """A no-arg preflight_check() must init/read the resolved DB_PATH, not a
    legacy politracker.db. Patching DB_PATH must take effect (late binding)."""
    from src import db as db_module

    db_path = tmp_path / "atmina.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    # No db_path argument — exercises the late-bound default.
    preflight_check()

    # init_db ran against the patched path, creating THAT file (and never a
    # legacy politracker.db in cwd).
    assert db_path.exists()
    assert not (tmp_path / "politracker.db").exists()


# --- ensure_analysis_env: the silent zero-claim "success" guard -------------
#
# In an interpreter without the embedding stack, save_analysis() WITH claims
# fails honestly (atomic rollback), but a zero-claim call succeeds — it never
# reaches embed_text. "0 pozīciju" then looks identical to a correct empty
# result. Six agents hit this 2026-07-24; see BACKLOG § Nepareizs interpretators.


@pytest.fixture(autouse=True)
def _reset_env_cache(monkeypatch):
    """The check memoizes its pass; each test starts from an unchecked state."""
    monkeypatch.setattr(preflight_module, "_analysis_env_checked", False)


def test_ensure_analysis_env_passes_in_a_working_venv():
    # The suite itself runs under an interpreter that can embed.
    ensure_analysis_env()


def test_ensure_analysis_env_raises_when_embedding_stack_missing(monkeypatch):
    monkeypatch.setattr(
        preflight_module.importlib.util, "find_spec",
        lambda name: None if name == "sentence_transformers" else object(),
    )

    with pytest.raises(RuntimeError) as exc:
        ensure_analysis_env()

    message = str(exc.value)
    assert "sentence_transformers" in message
    # Must name the interpreter that failed AND the way out.
    assert "python" in message.lower()
    hint = repo_python()
    if hint:
        assert hint in message


def test_save_analysis_zero_claims_stops_in_a_broken_env(monkeypatch):
    """The exact regression: no claims, no embeddings needed — must still stop."""
    from src import analyze

    monkeypatch.setattr(
        preflight_module.importlib.util, "find_spec",
        lambda name: None if name in preflight_module._EMBEDDING_DEPS else object(),
    )

    with pytest.raises(RuntimeError, match="Incomplete analysis environment"):
        analyze.save_analysis(
            pid=1, analysis_date="2026-07-24", sentiment=0.0, topics=[],
            quotes=[], brief="Nav ekstraktējamu pozīciju.", confidence=0.2,
            claims=[], empty_doc_ids=[123],
        )


def test_ensure_analysis_env_memoizes_the_pass(monkeypatch):
    """A guard on every save_analysis() call must not re-walk sys.path each time."""
    calls = []

    def counting_find_spec(name):
        calls.append(name)
        return object()

    monkeypatch.setattr(preflight_module.importlib.util, "find_spec",
                        counting_find_spec)

    ensure_analysis_env()
    first = len(calls)
    ensure_analysis_env()

    assert first > 0
    assert len(calls) == first
