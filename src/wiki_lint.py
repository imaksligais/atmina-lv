"""
Wiki lint engine for atmina.
Detects orphaned pages, broken wikilinks, stale frontmatter, and isolated topics.

Trīs parsēšanas noteikumi, kas ir daļa no linku pārbaudes, ne detaļa — katrs
ražo masveida viltus pozitīvus, ja tajā kļūdās (vārti:
tests/test_wiki_lint_content_links.py):
  (a) ``[[t\\|Label]]`` ir tabulai drošā alias forma un atrisinās normāli; ja
      ``\\`` uzskata par mērķa daļu, par salauztām tiek atzītas visas rindas
      persons/personas.md tabulā;
  (b) mērķis var būt ne-markdown vault fails (``[[politiki.base]]``), tāpēc
      atrisināmo kopa jābūvē no VISIEM failiem, ne tikai ``*.md``;
  (c) koda spanos un ``` blokos esošie wikilinki ir DOKUMENTĀCIJA par
      sintaksi, ne saites — čekeris, kas savu dokumentāciju skaita par
      bojājumu, māca ignorēt skaitli.
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


_FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code spans before link extraction.

    A wikilink inside backticks is DOCUMENTATION about link syntax, not a link.
    Without this, prose that explains the syntax is reported as a defect — and
    it happened immediately: the 2026-08-03 CHANGELOG entry describing the
    `[[t\\|Label]]` table-escape form was itself flagged as a broken link to
    `t`, alongside two older CHANGELOG lines quoting the very bug they document.
    A checker that counts its own documentation as breakage trains people to
    ignore the number, which is the failure mode this whole check exists to
    prevent. Replaced with spaces, not removed, so offsets stay comparable.
    """
    text = _FENCED_RE.sub(lambda m: " " * len(m.group(0)), text)
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


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
    #
    #    The key is `positions`, NOT `claims_count`. wiki_sync has never
    #    written a `claims_count` key (it writes name/party/role/positions/
    #    votes/contradictions/mentioned_in/last_active/top_topics —
    #    wiki.py:321-333), so from the day this check was added until
    #    2026-08-02 `wiki_count` was always None and the check could not
    #    fire. Same class as the corrupt_page comment below: a green that
    #    is not evidence.
    #
    #    `positions` counts claim_type='position' only (wiki.py:281-284),
    #    so db_counts must be filtered the same way — see lint_wiki_with_db.
    if db_counts is not None:
        persons = _collect_pages(wiki, "persons")
        for slug, path in persons.items():
            text = path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            wiki_count = fm.get("positions")
            db_count = db_counts.get(slug)
            if wiki_count is not None and db_count is not None and wiki_count != db_count:
                issues.append({
                    "type": "stale_frontmatter",
                    "path": str(path.relative_to(wiki)),
                    "detail": {"wiki_count": wiki_count, "db_count": db_count},
                })

    # 4. Isolated topics
    #
    #    Dead on BOTH sides until 2026-08-02: the person key is `top_topics`,
    #    not `topics`, and the topic key is `positions`, not `claims_count`.
    #    Neither name has ever been written by wiki_sync, so the set stayed
    #    empty and the count stayed 0 — the check never emitted an issue.
    #
    #    Comparison must go through _slugify, not .lower(): topic page stems
    #    are slugs ("valsts-parvalde") while frontmatter holds display names
    #    ("Valsts pārvalde"), so a lowercase match would flag every
    #    multi-word or diacritic topic as isolated.
    from src.wiki import _slugify

    topic_pages = _collect_pages(wiki, "topics")
    persons = _collect_pages(wiki, "persons")
    referenced_topics: set[str] = set()
    for _slug, path in persons.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        topics = fm.get("top_topics", [])
        if isinstance(topics, list):
            for t in topics:
                if isinstance(t, str):
                    referenced_topics.add(_slugify(t))

    for slug, path in topic_pages.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        positions = fm.get("positions", 0)
        if positions and positions > 0 and slug not in referenced_topics:
            issues.append({
                "type": "isolated_topic",
                "path": str(path.relative_to(wiki)),
                "detail": f"Topic has {positions} positions but no person page references it",
            })

    # 5. Corrupt pages — the ONLY check that looks at page bodies, and the only
    #    one that walks the whole vault rather than the four indexed subdirs.
    #
    #    Checks 1-4 above read every body they touch solely to parse
    #    frontmatter, and they only ever visit persons/topics/parties/laws. So
    #    for two months (2026-05-31 → 2026-08-01) 22 tracked pages carried a
    #    NUL run where their body used to be, and this lint reported "0 broken
    #    links" the whole time — wiki/index.md published that all-clear, and
    #    CLAUDE.md tells every session to read index.md first. A checker whose
    #    green is not evidence is worse than no checker: it actively stops
    #    people looking. This check exists so that class of damage cannot be
    #    silently green again.
    for path in sorted(wiki.rglob("*.md")):
        try:
            raw = path.read_bytes()
        except OSError as exc:
            issues.append({
                "type": "corrupt_page",
                "path": str(path.relative_to(wiki)),
                "detail": f"unreadable: {exc}",
            })
            continue
        if b"\x00" in raw:
            issues.append({
                "type": "corrupt_page",
                "path": str(path.relative_to(wiki)),
                "detail": (
                    f"{raw.count(0)} NUL bytes of {len(raw)} — body was destroyed "
                    f"by a truncated write; re-run wiki_sync() to rebuild it"
                ),
            })

    # 6. Broken wikilinks in CONTENT pages.
    #
    #    The check above only asks whether the four index files link to pages
    #    that exist. A wikilink written INSIDE a person / party / topic page is
    #    never examined — and those pages are the generated ones, so they are
    #    exactly where a wiki_sync bug lands. On 2026-08-02
    #    `_render_person_synthesis` emitted bare `[[Valsts pārvalde]]` (display
    #    name instead of the `topics/<slug>` path) in three places: 338 broken
    #    links across the vault while wiki/index.md published "0 broken links".
    #    Those instances were fixed the same day; this closes the blindness that
    #    let them pile up unseen.
    #
    #    Two parsing rules, both of which produce mass false positives if wrong:
    #      * `[[t\|Label]]` is the table-safe alias form and resolves fine
    #        (_extract_wikilinks already strips it). Treating the backslash as
    #        part of the target marks all 194 rows of persons/personas.md
    #        broken — a scan that does this reports hundreds of phantom defects.
    #      * a target may be a non-markdown vault file (`[[politiki.base]]`), so
    #        the resolvable set is built from ALL files, not just *.md.
    valid_targets: set[str] = set()
    for f in wiki.rglob("*"):
        if not f.is_file():
            continue
        rel_path = f.relative_to(wiki).as_posix()
        valid_targets.add(f.stem)
        valid_targets.add(f.name)
        valid_targets.add(rel_path)
        valid_targets.add(rel_path.removesuffix(f.suffix) if f.suffix else rel_path)

    already_reported = {i.get("target") for i in issues if i["type"] == "broken_link"}
    for path in sorted(wiki.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # already reported by the corrupt_page check above
        for raw in _extract_wikilinks(_strip_code(text)):
            target = raw.split("#")[0].strip()
            if not target or target in valid_targets:
                continue
            if target.lstrip("./") in valid_targets or target in already_reported:
                continue
            issues.append({
                "type": "broken_link",
                "target": target,
                "path": str(path.relative_to(wiki)),
                "detail": f"{path.relative_to(wiki)} links to [[{target}]] but no such vault file exists",
            })

    stats = {
        "total_issues": len(issues),
        "orphans": len([i for i in issues if i["type"] == "orphan_page"]),
        "broken_links": len([i for i in issues if i["type"] == "broken_link"]),
        "stale": len([i for i in issues if i["type"] == "stale_frontmatter"]),
        "isolated": len([i for i in issues if i["type"] == "isolated_topic"]),
        "corrupt": len([i for i in issues if i["type"] == "corrupt_page"]),
    }

    return {"issues": issues, "stats": stats}


def lint_wiki_with_db(
    wiki_dir: str = "wiki",
    db_path: str = "data/atmina.db",
) -> dict:
    """Run lint with live DB counts."""
    from src.db import get_db

    db = get_db(db_path)

    # claim_type='position' must match _person_frontmatter's `positions`
    # (wiki.py:281-284). Counting every claim_type here would compare 336
    # positions against 5236 rows for a sitting MP and flag all 193 pages
    # stale on the first run.
    rows = db.execute("""
        SELECT p.name, COUNT(c.id) AS cnt
        FROM tracked_politicians p
        LEFT JOIN claims c ON c.opponent_id = p.id AND c.claim_type = 'position'
        GROUP BY p.id
    """).fetchall()
    db.close()

    from src.wiki import _slugify
    db_counts = {_slugify(r["name"]): r["cnt"] for r in rows}

    return lint_wiki(wiki_dir, db_counts=db_counts)
