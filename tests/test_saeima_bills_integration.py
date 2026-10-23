"""Phase 1A integration tests — parse real agenda snapshot fixtures.

The 2026-04-16 snapshot at data/saeima_snapshots/2026-04-16/agenda.md
is the canonical fixture for parser regression detection.
"""

import os
from pathlib import Path

import pytest

from src.saeima import (
    parse_agenda_snapshot,
)


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


# Fixture lives in the parent main checkout (data/ is gitignored, not in worktree).
# Resolve from CWD: prefer worktree-relative, fall back to ../../ parent.
def _find_fixture():
    candidates = [
        Path("data/saeima_snapshots/2026-04-16/agenda.md"),
        Path("../../data/saeima_snapshots/2026-04-16/agenda.md"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


FIXTURE_AGENDA = _find_fixture()


@pytest.mark.skipif(
    FIXTURE_AGENDA is None,
    reason="agenda.md fixture missing — run @saeima-tracker first to populate",
)
class TestParseAgenda20260416:
    def test_extracts_at_least_one_bill(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        assert len(bills) >= 1, "agenda fixture should contain bills"

    def test_extracted_bills_have_valid_types(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        for b in bills:
            assert b.bill_type in {"Lp14", "Lm14", "P14"}, f"unknown bill_type {b.bill_type!r}"
            assert b.document_nr.endswith(b.bill_type), \
                f"document_nr suffix mismatch: {b.document_nr!r} vs {b.bill_type!r}"
            assert b.title, "every bill should have a title"

    def test_titles_are_clean(self):
        """Titles must not contain accessibility-tree noise (newlines, ref tags)."""
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        for b in bills:
            assert "\n" not in b.title, f"title has newline: {b.document_nr} {b.title!r}"
            assert "[ref=" not in b.title, f"title has ref tag: {b.document_nr} {b.title!r}"
            # Most titles are short; legitimate Lm14 procedural titles can run long
            # but should never exceed 400 chars (anything bigger is a parse error)
            assert len(b.title) <= 400, \
                f"title suspiciously long ({len(b.title)} chars): {b.document_nr}"

    # Both submitter tests below used to only `print()` their counts, with the
    # comment "real agenda may or may not have submitters — accept 0 or more".
    # That reasoning holds for a LIVE agenda, but these read a FIXED snapshot,
    # so the counts are deterministic and a test that accepts any number cannot
    # fail — it looked like submitter coverage while asserting nothing
    # (CLAUDE.md § "a gate that cannot fail is not evidence"). Pinned to the
    # measured fixture values 2026-08-15; if the parser regresses on either
    # submitter field, these now go red instead of printing a smaller number.
    def test_some_bills_have_individual_submitters(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_individual = [b for b in bills if b.individual_submitters]
        assert len(bills) == 46, f"fixture changed: {len(bills)} bills, expected 46"
        assert len(with_individual) == 13, (
            f"individual_submitters parsed for {len(with_individual)}/{len(bills)} bills, "
            "expected 13 — parser regression or fixture change"
        )

    def test_some_bills_have_institutional_submitter(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_inst = [b for b in bills if b.institutional_submitter]
        assert len(with_inst) == 5, (
            f"institutional_submitter parsed for {len(with_inst)}/{len(bills)} bills, "
            "expected 5 — parser regression or fixture change"
        )
        assert {b.institutional_submitter for b in with_inst} == {"Ministru kabinets"}
