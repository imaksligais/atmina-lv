import tempfile
from pathlib import Path
from src.wiki_lint import lint_wiki


def _make_wiki(tmp: Path, persons: list[str], index_links: list[str]) -> Path:
    """Create minimal wiki structure for testing."""
    wiki = tmp / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    for name in persons:
        (wiki / "persons" / f"{name}.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    index_lines = ["# atmina — Indekss\n"]
    for link in index_links:
        index_lines.append(f"- [[persons/{link}|{link}]]\n")
    (wiki / "index.md").write_text("".join(index_lines), encoding="utf-8")
    return wiki


def test_orphan_person_detected():
    """Person page exists but is not linked from index.md."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins", "anna-kalve"],
            index_links=["janis-berzins"],
        )
        result = lint_wiki(str(wiki))
        orphans = [i for i in result["issues"] if i["type"] == "orphan_page"]
        assert len(orphans) == 1
        assert "anna-kalve" in orphans[0]["path"]


def test_no_orphans_when_all_linked():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins", "anna-kalve"],
            index_links=["janis-berzins", "anna-kalve"],
        )
        result = lint_wiki(str(wiki))
        orphans = [i for i in result["issues"] if i["type"] == "orphan_page"]
        assert len(orphans) == 0


def test_broken_wikilink_detected():
    """Index references a person page that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins"],
            index_links=["janis-berzins", "ghost-politician"],
        )
        result = lint_wiki(str(wiki))
        broken = [i for i in result["issues"] if i["type"] == "broken_link"]
        assert len(broken) == 1
        assert "ghost-politician" in broken[0]["target"]


def test_stale_page_detected(tmp_path):
    """Person page with frontmatter claims_count but DB has different count."""
    wiki = tmp_path / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    page = wiki / "persons" / "janis-berzins.md"
    page.write_text("---\nname: Jānis Bērziņš\nclaims_count: 50\n---\n", encoding="utf-8")
    (wiki / "index.md").write_text("- [[persons/janis-berzins|Jānis Bērziņš]]\n", encoding="utf-8")
    result = lint_wiki(str(wiki), db_counts={"janis-berzins": 12})
    stale = [i for i in result["issues"] if i["type"] == "stale_frontmatter"]
    assert len(stale) == 1
    assert stale[0]["detail"]["wiki_count"] == 50
    assert stale[0]["detail"]["db_count"] == 12


def test_missing_cross_reference():
    """Topic page exists but no person page references that topic."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp) / "wiki"
        (wiki / "persons").mkdir(parents=True)
        (wiki / "topics").mkdir(parents=True)
        (wiki / "topics" / "imigracija.md").write_text("---\ntopic: Imigrācija\nclaims_count: 5\n---\n", encoding="utf-8")
        (wiki / "persons" / "janis-berzins.md").write_text("---\nname: Jānis Bērziņš\ntopics: []\n---\n", encoding="utf-8")
        (wiki / "index.md").write_text("- [[persons/janis-berzins|J]]\n\n## Tēmas\n- [[topics/imigracija|Imigrācija]]\n", encoding="utf-8")
        result = lint_wiki(str(wiki))
        isolated = [i for i in result["issues"] if i["type"] == "isolated_topic"]
        assert len(isolated) == 1


def test_lint_summary_format():
    """lint_wiki returns printable summary."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins"],
            index_links=["janis-berzins", "ghost"],
        )
        result = lint_wiki(str(wiki))
        assert "stats" in result
        assert result["stats"]["total_issues"] == result["stats"]["orphans"] + result["stats"]["broken_links"] + result["stats"]["stale"] + result["stats"]["isolated"]
