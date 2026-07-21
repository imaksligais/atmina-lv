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

import importlib.util

import pytest

collect_ignore_glob: list[str] = []

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
