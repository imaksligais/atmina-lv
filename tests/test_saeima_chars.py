"""Characterization tests for src.saeima — frozen behavioral baseline.

Phase F4 refactor safety net: snapshots the observable output of
parse_agenda_snapshot, parse_vote_snapshot, resolve_bill_from_motif,
_reading_from_motif, and _motif_to_topic on real snapshot files +
representative motif strings. Tests assert that current output equals
the frozen baseline in tests/fixtures/saeima_chars_expected.json.

Refactor invariant: F4 (saeima.py → src/saeima/ pakete) preserves
behavior, not changes it. If a code change intentionally alters output,
regenerate the baseline via REGEN=1 pytest tests/test_saeima_chars.py
(writes the new observed output as the new frozen expected). Without
REGEN, mismatches fail the test.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path

import pytest

from src.saeima import (
    _motif_to_topic,
    _reading_from_motif,
    parse_agenda_snapshot,
    parse_vote_snapshot,
    resolve_bill_from_motif,
)

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOTS = FIXTURES / "saeima_snapshots"
MOTIFS_FILE = FIXTURES / "saeima_motifs.json"
EXPECTED_FILE = FIXTURES / "saeima_chars_expected.json"


def _serialize(obj):
    """Recursively convert dataclasses (incl. nested lists) to plain dicts/lists."""
    if is_dataclass(obj):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    if isinstance(obj, tuple):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _capture_observed() -> dict:
    motif_data = json.loads(MOTIFS_FILE.read_text(encoding="utf-8"))
    motifs = motif_data["motifs"]

    agenda_text = (SNAPSHOTS / "agenda_2026-04-16.md").read_text(encoding="utf-8")
    agenda_bills = parse_agenda_snapshot(agenda_text)

    vote_results = {}
    for name in ("vote_a.md", "vote_b.md", "vote_c.md"):
        text = (SNAPSHOTS / name).read_text(encoding="utf-8")
        vote_results[name] = parse_vote_snapshot(text)

    return {
        "motifs": [
            {
                "motif": m,
                "resolve_bill_from_motif": resolve_bill_from_motif(m),
                "_reading_from_motif": _reading_from_motif(m),
                "_motif_to_topic": _motif_to_topic(m),
            }
            for m in motifs
        ],
        "parse_agenda_snapshot": _serialize(agenda_bills),
        "parse_vote_snapshot": {k: _serialize(v) for k, v in vote_results.items()},
    }


def _load_expected() -> dict:
    if not EXPECTED_FILE.exists():
        pytest.fail(
            f"Expected fixture {EXPECTED_FILE} missing. "
            "Bootstrap with REGEN=1 pytest tests/test_saeima_chars.py."
        )
    return json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))


def test_motif_helpers_match_baseline():
    observed = _capture_observed()
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected()
    assert observed["motifs"] == expected["motifs"]


def test_parse_agenda_snapshot_matches_baseline():
    observed = _capture_observed()
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by sibling test.")
    expected = _load_expected()
    assert observed["parse_agenda_snapshot"] == expected["parse_agenda_snapshot"]


def test_parse_vote_snapshot_matches_baseline():
    observed = _capture_observed()
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by sibling test.")
    expected = _load_expected()
    assert observed["parse_vote_snapshot"] == expected["parse_vote_snapshot"]
