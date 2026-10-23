"""`scripts/migrate_db.py` must not be able to destroy the live database.

Why this test exists (2026-08-22 audit, `docs/audits/2026-08-22-slop-un-bloat-audits.md`
kāpnes #1): the script is a one-off migration that ran on 2026-04-06 and is kept as
documented history (CHANGELOG-arhivs 2026-07-29 § Politracker tīrīšana). Its first
step is `shutil.copy2(SRC_DB, DST_DB)` — the only whole-file DB overwrite in
``scripts/`` — and until this guard landed, a bare ``python scripts/migrate_db.py``
fell through to ``main()`` and ran it. Both paths were live on the maintainer machine,
so the copy would have SUCCEEDED, replacing a multi-GB ``data/atmina.db`` with a 32 MB
2026-04 legacy file. ``.gitignore`` excludes ``*.db``, so there is no git recovery path.

Two properties are locked here, both of which regress silently if someone "tidies"
the ``__main__`` block back to its old shape:

1. a bare invocation performs no work at all, and
2. ``step_copy()`` refuses when the destination already exists.

The test never touches the real database — it points the module's ``DST_DB`` at a
tmp file. `tests/conftest.py` carries a production-DB tripwire for the same reason.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "migrate_db.py"


def _load():
    spec = importlib.util.spec_from_file_location("migrate_db", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bare_invocation_does_no_work():
    """No argv -> usage text on stderr, non-zero exit, nothing copied."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode != 0, (
        "A bare `python scripts/migrate_db.py` exited 0 — it is doing something "
        "again. The whole point of the guard is that it does nothing."
    )
    combined = proc.stdout + proc.stderr
    assert "full-migrate" in combined, combined
    # step_copy() announces itself before copying; its absence proves we never got there.
    assert "Copying" not in combined, combined


def test_step_copy_refuses_existing_destination(tmp_path, monkeypatch):
    mod = _load()

    src = tmp_path / "politracker.db"
    src.write_bytes(b"source-db-payload")
    dst = tmp_path / "atmina.db"
    dst.write_bytes(b"LIVE DATABASE - must survive")

    monkeypatch.setattr(mod, "SRC_DB", src)
    monkeypatch.setattr(mod, "DST_DIR", tmp_path)
    monkeypatch.setattr(mod, "DST_DB", dst)

    with pytest.raises(SystemExit) as excinfo:
        mod.step_copy()

    assert "REFUSED" in str(excinfo.value)
    assert dst.read_bytes() == b"LIVE DATABASE - must survive", (
        "step_copy() overwrote the destination despite refusing — the guard has "
        "to come BEFORE shutil.copy2, not after."
    )


def test_step_copy_still_works_when_destination_absent(tmp_path, monkeypatch):
    """The guard must not break a legitimate first-run migration."""
    mod = _load()

    src = tmp_path / "politracker.db"
    src.write_bytes(b"source-db-payload")
    dst = tmp_path / "out" / "atmina.db"

    monkeypatch.setattr(mod, "SRC_DB", src)
    monkeypatch.setattr(mod, "DST_DIR", dst.parent)
    monkeypatch.setattr(mod, "DST_DB", dst)

    mod.step_copy()
    assert dst.read_bytes() == b"source-db-payload"


def test_explicit_override_is_the_only_way_through(tmp_path, monkeypatch):
    mod = _load()

    src = tmp_path / "politracker.db"
    src.write_bytes(b"source-db-payload")
    dst = tmp_path / "atmina.db"
    dst.write_bytes(b"LIVE DATABASE")

    monkeypatch.setattr(mod, "SRC_DB", src)
    monkeypatch.setattr(mod, "DST_DIR", tmp_path)
    monkeypatch.setattr(mod, "DST_DB", dst)

    mod.step_copy(allow_overwrite=True)
    assert dst.read_bytes() == b"source-db-payload"
