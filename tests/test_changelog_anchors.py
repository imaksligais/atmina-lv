"""Every `CHANGELOG.md#anchor` / `CHANGELOG-arhivs.md#anchor` link must resolve.

`CLAUDE.md` and several agent prompts cite CHANGELOG sections by anchor as the
rationale for load-bearing invariants (Data Contract #4, #5, #6, the CSP rule,
T7, the matcher rewrite). Those links are the only path from "this rule exists"
to "here is the incident that produced it", so a dangling one silently costs a
future session the reasoning behind a rule it is being asked to honour.

The anchors are unusually fragile here for two reasons:

1. Headings are Latvian with diacritics, em dashes and backticks, so the slug is
   not guessable by eye — `## 2026-04-11 — claim_type split (position vs
   saeima_vote)` becomes `#2026-04-11--claim_type-split-position-vs-saeima_vote`
   (the em dash vanishes but its two surrounding spaces each become a hyphen).

2. The CHANGELOG is periodically split into `CHANGELOG-arhivs.md` to keep the
   live file small. Each split moves headings between files, and the documented
   procedure depends on spotting which anchors are referenced from elsewhere
   before moving them. Doing that by hand is exactly the step that gets skipped.

The 2026-08-01 June split found one already-dangling reference that had been
broken since April (a `2026-04-XX` placeholder date that was never filled in) —
nothing detected it for three months. This test is that detector.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CHANGELOGS = {
    "CHANGELOG": _ROOT / "wiki" / "CHANGELOG.md",
    "CHANGELOG-arhivs": _ROOT / "wiki" / "CHANGELOG-arhivs.md",
}

# Matches a link target like `CHANGELOG.md#some-anchor`, with or without a path
# prefix — we only care about which changelog and which anchor.
_LINK = re.compile(r"(CHANGELOG(?:-arhivs)?)\.md#([^\)\s\"'>]+)")


def _slug(heading: str) -> str:
    """Reproduce GitHub's heading -> anchor transform.

    Lowercase, drop every character that is not word/space/hyphen, then map
    EACH space to a hyphen. Runs are deliberately not collapsed: that is what
    turns ` — ` into `--`.
    """
    s = re.sub(r"[^\w\s-]", "", heading.strip().lower(), flags=re.UNICODE)
    return s.replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    if not path.exists():
        return set()
    headings = re.findall(r"(?m)^\#{2,}\s+(.+?)\s*$", path.read_text(encoding="utf-8"))
    return {_slug(h) for h in headings}


def _tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return [_ROOT / f for f in out if f.strip() and (_ROOT / f).is_file()]


def _references() -> list[tuple[Path, str, str]]:
    found = []
    for path in _tracked_markdown():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in _LINK.finditer(text):
            found.append((path, m.group(1), m.group(2)))
    return found


def test_every_changelog_anchor_reference_resolves():
    anchors = {name: _anchors(p) for name, p in _CHANGELOGS.items()}

    broken = []
    for path, target, anchor in _references():
        if anchor not in anchors.get(target, set()):
            broken.append(f"{path.relative_to(_ROOT)} -> {target}.md#{anchor}")

    assert not broken, (
        "Dangling CHANGELOG anchors — the cited section was renamed, or moved "
        "between CHANGELOG.md and CHANGELOG-arhivs.md without updating the "
        "reference (see the split procedure at the top of CHANGELOG.md):\n  "
        + "\n  ".join(broken)
    )


def test_the_check_is_actually_finding_references():
    """Guard the guard: a regex that matches nothing would pass vacuously."""
    refs = _references()
    assert len(refs) >= 10, f"expected many CHANGELOG anchor refs, found {len(refs)}"


@pytest.mark.parametrize(
    "heading,expected",
    [
        # The real CLAUDE.md targets — these encode the em-dash and bracket rules.
        ("2026-04-11 — claim_type split (`position` vs `saeima_vote`)",
         "2026-04-11--claim_type-split-position-vs-saeima_vote"),
        ("2026-04-23 — Komentētāji (speaker_id on claims)",
         "2026-04-23--komentētāji-speaker_id-on-claims"),
        ("2026-04-27 — Saeima Bills Phase 1C (orchestration & glue)",
         "2026-04-27--saeima-bills-phase-1c-orchestration--glue"),
    ],
)
def test_slug_matches_github_transform(heading, expected):
    assert _slug(heading) == expected
