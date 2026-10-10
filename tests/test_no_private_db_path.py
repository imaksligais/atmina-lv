"""No module keeps its own copy of the production DB path.

A module-private path (``_DB_PATH = ... / "atmina.db"``) escapes both a test's
``monkeypatch.setattr(src.db, "DB_PATH", ...)`` and the conftest § 4 guard, so
tests read the live DB locally and fail only in DB-less public CI. That is how
src/confidence_drift.py broke the 2026-09-24 sync candidate (and briefs.py /
cross_check.py carried the same copy). Code must call ``get_db(db_path)`` with
``None`` and let ``src.db.DB_PATH`` decide.

The check reads string literals in code (docstrings and comments are prose and
exempt). Each allowlisted file says why it may name the file.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

ALLOWED = {
    # The one source of truth.
    "db.py",
    # Default-path constants that tests/conftest.py § 4 redirects explicitly.
    "render/_common/constants.py",
    "wiki_format.py",
    # CLI entry points: argparse defaults/help, resolved per process, not per call.
    "graphics/cli.py",
    "render/__main__.py",
}


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _offenders() -> list[str]:
    hits = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and "atmina.db" in node.value and id(node) not in docs
                    and rel not in ALLOWED):
                hits.append(f"src/{rel}:{node.lineno}: {node.value!r}")
    return hits


def test_no_module_hardcodes_the_production_db_path():
    offenders = _offenders()
    assert not offenders, (
        "Modulis nes savu DB ceļu — izmanto get_db(db_path) ar None:\n  "
        + "\n  ".join(offenders)
    )


def test_the_scan_actually_sees_src():
    # Denominator: a scan over zero files would pass forever.
    files = list(SRC.rglob("*.py"))
    assert len(files) > 100
    assert (SRC / "db.py").exists()
