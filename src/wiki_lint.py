"""
Wiki lint engine for atmina.
Detects orphaned pages, broken wikilinks, stale frontmatter, and isolated topics.
"""

import re
from pathlib import Path
from typing import Optional

import yaml


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _extract_wikilinks(text: str) -> list[str]:
    """Extract all [[target|label]] or [[target\\|label]] wikilinks."""
    return re.findall(r"\[\[([^\]|\\]+?)(?:\\?\|[^\]]+?)?\]\]", text)


def _extract_md_links(text: str) -> list[str]:
    """Extract all [label](target.md) markdown links, returning target without .md."""
    return [m.removesuffix(".md") for m in re.findall(r"\[[^\]]*\]\(([^)]+\.md)\)", text)]


_INDEX_NAMES = {"index", "personas", "partijas", "temas", "likumi", "operacijas", "sinteze"}

def _collect_pages(wiki_dir: Path, subdir: str) -> dict[str, Path]:
    """Map slug -> file path for all .md files in a subdirectory (excludes index files)."""
    d = wiki_dir / subdir
    if not d.exists():
        return {}
    return {p.stem: p for p in d.glob("*.md") if p.stem not in _INDEX_NAMES}


def lint_wiki(
    wiki_dir: str,
    db_counts: Optional[dict[str, int]] = None,
) -> dict:
    """Run all lint checks on the wiki.

    Args:
        wiki_dir: Path to the wiki/ directory.
        db_counts: Optional dict mapping person slug -> claim count from DB.
                   If None, stale frontmatter check is skipped.

    Returns:
        {"issues": [...], "stats": {...}}
    """
    wiki = Path(wiki_dir)
    issues: list[dict] = []

    index_path = wiki / "index.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    index_links = _extract_wikilinks(index_text)
    index_targets: set[tuple[str, str]] = set()
    for link in index_links:
        parts = link.split("/", 1)
        if len(parts) == 2:
            index_targets.add((parts[0], parts[1]))

    # 1. Orphan detection & 2. Broken links
    # For each subdir, use the Latvian-named sub-index (e.g. persons/personas.md) as the link source
    # Subfolder index file names — Latvian semantic equivalents of folder
    # names, for Obsidian graph readability. Must stay in sync with
    # src/wiki.py::wiki_sync().
    _SUBDIR_INDEX = {
        "persons": "personas.md",
        "topics": "temas.md",
        "parties": "partijas.md",
        "laws": "likumi.md",
    }
    for subdir in ["persons", "topics", "parties", "laws"]:
        sub_index_name = _SUBDIR_INDEX.get(subdir, "index.md")
        sub_index_path = wiki / subdir / sub_index_name
        if sub_index_path.exists():
            sub_text = sub_index_path.read_text(encoding="utf-8")
            # Wikilinks: [[topics/slug|Label]]
            sub_links = _extract_wikilinks(sub_text)
            linked_slugs = {
                link.split("/", 1)[1]
                for link in sub_links
                if link.startswith(f"{subdir}/") and "/" in link
            }
            # Markdown links: [Label](slug.md)
            md_links = _extract_md_links(sub_text)
            linked_slugs.update(md_links)
            source_label = f"{subdir}/{sub_index_name}"
        else:
            linked_slugs = {slug for cat, slug in index_targets if cat == subdir}
            source_label = "index.md"

        pages = _collect_pages(wiki, subdir)

        # Orphans: pages not linked from the index
        for slug, path in pages.items():
            if slug not in linked_slugs:
                issues.append({
                    "type": "orphan_page",
                    "path": str(path.relative_to(wiki)),
                    "detail": f"Page exists but not linked from {source_label}",
                })

        # Broken links: index links to non-existent pages
        for slug in linked_slugs:
            if slug not in pages:
                issues.append({
                    "type": "broken_link",
                    "target": f"{subdir}/{slug}",
                    "detail": f"{source_label} links to {subdir}/{slug} but file does not exist",
                })

    # 3. Stale frontmatter
    if db_counts is not None:
        persons = _collect_pages(wiki, "persons")
        for slug, path in persons.items():
            text = path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            wiki_count = fm.get("claims_count")
            db_count = db_counts.get(slug)
            if wiki_count is not None and db_count is not None and wiki_count != db_count:
                issues.append({
                    "type": "stale_frontmatter",
                    "path": str(path.relative_to(wiki)),
                    "detail": {"wiki_count": wiki_count, "db_count": db_count},
                })

    # 4. Isolated topics
    topic_pages = _collect_pages(wiki, "topics")
    persons = _collect_pages(wiki, "persons")
    referenced_topics: set[str] = set()
    for _slug, path in persons.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        topics = fm.get("topics", [])
        if isinstance(topics, list):
            for t in topics:
                if isinstance(t, str):
                    referenced_topics.add(t.lower())

    for slug, path in topic_pages.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        claims_count = fm.get("claims_count", 0)
        if claims_count and claims_count > 0 and slug not in referenced_topics:
            issues.append({
                "type": "isolated_topic",
                "path": str(path.relative_to(wiki)),
                "detail": f"Topic has {claims_count} claims but no person page references it",
            })

    stats = {
        "total_issues": len(issues),
        "orphans": len([i for i in issues if i["type"] == "orphan_page"]),
        "broken_links": len([i for i in issues if i["type"] == "broken_link"]),
        "stale": len([i for i in issues if i["type"] == "stale_frontmatter"]),
        "isolated": len([i for i in issues if i["type"] == "isolated_topic"]),
    }

    return {"issues": issues, "stats": stats}


def lint_wiki_with_db(
    wiki_dir: str = "wiki",
    db_path: str = "data/atmina.db",
) -> dict:
    """Run lint with live DB counts."""
    from src.db import get_db

    db = get_db(db_path)

    rows = db.execute("""
        SELECT p.name, COUNT(c.id) AS cnt
        FROM tracked_politicians p
        LEFT JOIN claims c ON c.opponent_id = p.id
        GROUP BY p.id
    """).fetchall()
    db.close()

    from src.wiki import _slugify
    db_counts = {_slugify(r["name"]): r["cnt"] for r in rows}

    return lint_wiki(wiki_dir, db_counts=db_counts)
