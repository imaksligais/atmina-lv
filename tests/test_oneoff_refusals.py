"""Finished one-off scripts refuse to write (audit 2026-11-07 § 4).

Failure this catches: a bare (or ``--apply``) run of a finished one-off
overwrites later operator decisions — disambiguation lists, junction roles,
claim topics. Each script must exit non-zero BEFORE it opens any database.
Every DB entry point is redirected to a sentinel or a temp path, so a missing
refusal fails here instead of touching data/atmina.db.
"""

from __future__ import annotations

import importlib

import pytest


class _DbTouched(Exception):
    pass


def _no_db(*_a, **_k):
    raise _DbTouched("the script opened a database")


@pytest.mark.parametrize(
    "module, argv",
    [
        ("scripts.seed_homonimu_disambig", []),
        ("scripts.seed_homonimu_phase2_disambig", None),
        ("scripts.seed_vad_disambig", None),
        ("scripts.audit_junction_roles", ["--apply"]),
    ],
)
def test_get_db_scripts_refuse(monkeypatch, module, argv):
    mod = importlib.import_module(module)
    monkeypatch.setattr(mod, "get_db", _no_db)
    with pytest.raises(SystemExit) as exc:
        mod.main() if argv is None else mod.main(argv)
    assert isinstance(exc.value.code, str) and exc.value.code.startswith("ATTEIKTS")


def test_lidaka_refuses(monkeypatch, tmp_path):
    mod = importlib.import_module("scripts.seed_lidaka_disambig")
    db = tmp_path / "atmina.db"
    monkeypatch.setattr(mod, "DB_PATH", db)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert str(exc.value.code).startswith("ATTEIKTS")
    assert not db.exists(), "the script opened (created) the database"


def test_backfill_topic_apply_refuses(tmp_path):
    mod = importlib.import_module("scripts.backfill_topic_classification")
    db = tmp_path / "atmina.db"
    with pytest.raises(SystemExit) as exc:
        mod.main(["--db", str(db), "--apply"])
    assert str(exc.value.code).startswith("ATTEIKTS")
    assert not db.exists(), "the script opened (created) the database"


@pytest.mark.parametrize(
    "module, argv",
    [
        ("scripts.seed_homonimu_disambig", ["--dry-run"]),
        ("scripts.audit_junction_roles", []),
    ],
)
def test_read_only_modes_still_run(monkeypatch, module, argv):
    """The dry-run / report mode is not refused: it reaches the DB."""
    mod = importlib.import_module(module)
    monkeypatch.setattr(mod, "get_db", _no_db)
    with pytest.raises(_DbTouched):
        mod.main(argv)
