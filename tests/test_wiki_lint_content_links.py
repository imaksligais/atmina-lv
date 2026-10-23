"""The broken-link check must read CONTENT pages, not only the four indexes.

`wiki_lint`'s broken-link check walks the index pages (`personas.md`,
`temas.md`, `partijas.md`, `likumi.md`) and asks whether each link resolves. A
wikilink written INSIDE a person, party or topic page is never examined — and
those pages are the ones `wiki_sync` generates, so they are exactly where a
generator bug lands.

That gap is not hypothetical. On 2026-08-02 `_render_person_synthesis` was
emitting bare `[[Valsts pārvalde]]` (display name, not the `topics/<slug>`
path) in three places, producing 338 broken links across the vault while
`wiki/index.md` published "0 broken links". The instances were fixed that day;
the blindness that let them accumulate silently was not. An independent scan on
2026-08-03 still finds 4 real broken targets in content pages that the lint
reports as zero.

Two parsing details the checker must get right, both learned the hard way:
  * `[[target\\|Label]]` — inside a markdown table the alias pipe is
    backslash-escaped, and Obsidian resolves it. Treating the backslash as part
    of the target marks all 194 links in `persons/personas.md` broken. That is
    a false-positive machine, and a scan that does it will report hundreds of
    defects that do not exist.
  * A link target may point at a non-markdown vault file — `[[politiki.base]]`
    is a real Obsidian Base. Indexing only `*.md` marks those broken too.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.wiki_lint import lint_wiki


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    w = tmp_path / "wiki"
    (w / "persons").mkdir(parents=True)
    (w / "topics").mkdir()
    (w / "parties").mkdir()
    (w / "laws").mkdir()
    (w / "index.md").write_text("# Index\n", encoding="utf-8")
    (w / "topics" / "temas.md").write_text(
        "# Tēmas\n\n- [[topics/valsts-parvalde|Valsts pārvalde]]\n", encoding="utf-8"
    )
    (w / "topics" / "valsts-parvalde.md").write_text(
        "---\npositions: 3\n---\n# Valsts pārvalde\n", encoding="utf-8"
    )
    (w / "parties" / "partijas.md").write_text("# Partijas\n", encoding="utf-8")
    (w / "laws" / "likumi.md").write_text("# Likumi\n", encoding="utf-8")
    return w


def _write_persons_index(w: Path, *slugs: str) -> None:
    rows = "\n".join(f"| [[persons/{s}\\|{s}]] |" for s in slugs)
    (w / "persons" / "personas.md").write_text(f"# Personas\n\n{rows}\n", encoding="utf-8")


def _broken(w: Path) -> list[dict]:
    return [i for i in lint_wiki(str(w))["issues"] if i["type"] == "broken_link"]


def test_broken_wikilink_inside_a_person_page_is_reported(vault):
    """The 2026-08-02 shape: a generated page links a topic by display name."""
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "---\npositions: 2\ntop_topics:\n- Valsts pārvalde\n---\n"
        "# Anna Bērziņa\n\nTēmas: [[Valsts pārvalde]]\n",
        encoding="utf-8",
    )
    broken = _broken(vault)
    assert any("Valsts pārvalde" in str(i.get("target", "")) for i in broken), broken


def test_table_escaped_alias_pipe_is_not_broken(vault):
    """`[[t\\|Label]]` is valid inside a markdown table — must NOT be flagged.

    Getting this wrong marks every row of persons/personas.md broken.
    """
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\n| Tēma |\n|---|\n"
        "| [[topics/valsts-parvalde\\|Valsts pārvalde]] |\n",
        encoding="utf-8",
    )
    assert _broken(vault) == []


def test_non_markdown_vault_target_is_not_broken(vault):
    """`[[politiki.base]]` is a real Obsidian Base file, not a dangling link."""
    _write_persons_index(vault, "anna-berzina")
    (vault / "politiki.base").write_text("filters: {}\n", encoding="utf-8")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\nSkat. [[politiki.base]]\n", encoding="utf-8"
    )
    assert _broken(vault) == []


def test_alias_and_heading_suffixes_are_stripped(vault):
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\n[[topics/valsts-parvalde#Sadaļa|Tēma]]\n", encoding="utf-8"
    )
    assert _broken(vault) == []


def test_clean_vault_reports_zero(vault):
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\n[[topics/valsts-parvalde]]\n", encoding="utf-8"
    )
    assert _broken(vault) == []


def test_wikilink_inside_a_code_span_is_documentation_not_a_link(vault):
    """Prose explaining link syntax must not be counted as breakage.

    The 2026-08-03 CHANGELOG entry documenting the table-escape form was itself
    flagged as a broken link to `t`. A checker that counts its own
    documentation as a defect teaches people to ignore the number.
    """
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\n"
        "Tabulās lieto `[[t\\|Label]]` formu, ne `[[nonexistent-page]]`.\n\n"
        "```\n[[another-nonexistent-page]]\n```\n",
        encoding="utf-8",
    )
    assert _broken(vault) == []


def test_a_real_link_beside_a_code_span_is_still_checked(vault):
    """Stripping code must not blind the check to genuine links on the page."""
    _write_persons_index(vault, "anna-berzina")
    (vault / "persons" / "anna-berzina.md").write_text(
        "# Anna Bērziņa\n\nSintakse: `[[t\\|Label]]`. Tēma: [[Valsts pārvalde]]\n",
        encoding="utf-8",
    )
    broken = _broken(vault)
    assert [i["target"] for i in broken] == ["Valsts pārvalde"]
