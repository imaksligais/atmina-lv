#!/usr/bin/env bash
# Phase 0 safety net — every refactor phase must end with this green.
# Steps:
#   1. ruff lint (config in pyproject.toml; ignores documented there)
#   2. pytest -q (full suite; pre-existing failures listed in
#      docs/refactor/baseline-2026-04-29.md are tolerated, NEW failures fail)
#   3. generate_public_site() smoke — confirms templates + DB read path
#      stay wired after any module split
#
# Usage: bash scripts/check.sh
# Windows: activate the venv first: .venv/Scripts/activate
set -e

# Resolve python: prefer local .venv, walk up parent dirs to support
# git-worktree workflows (refactor-plan-2026-04-29.md F1+ runs check.sh
# from .worktrees/<branch>/ where .venv lives in the master worktree).
# Falls back to POSIX layout, then bare PATH python.
PY=""
dir="$(pwd)"
while [ -n "$dir" ]; do
    if [ -x "$dir/.venv/Scripts/python.exe" ]; then
        PY="$dir/.venv/Scripts/python.exe"; break
    elif [ -x "$dir/.venv/bin/python" ]; then
        PY="$dir/.venv/bin/python"; break
    fi
    parent="$(dirname "$dir")"
    [ "$parent" = "$dir" ] && break
    dir="$parent"
done
[ -z "$PY" ] && PY="python"

echo "==> ruff check"
"$PY" -m ruff check src scripts tests

echo "==> pytest -q"
"$PY" -m pytest tests -q

# Narrow render smoke — confirms templates + DB read path + REAL output/ write
# stay wired. Defaults to the dashboard+blog domains (the most refactor-fragile
# shared-data paths); pytest's char-baseline fixture already full-renders every
# domain into tmp, so this only needs to exercise the live output dir.
# Override the scope with CHECK_RENDER_ONLY (comma list, or "all" for a full
# render). See src.render KNOWN_DOMAINS for valid names.
echo "==> generate_public_site smoke (only=${CHECK_RENDER_ONLY:-dashboard,blog})"
"$PY" - "${CHECK_RENDER_ONLY:-dashboard,blog}" <<'PYSMOKE'
import sys
from src.render import generate_public_site
spec = sys.argv[1]
only = None if spec in ("all", "full", "*") else {d for d in spec.split(",") if d}
generate_public_site(only=only)
PYSMOKE

echo "==> all checks passed"
