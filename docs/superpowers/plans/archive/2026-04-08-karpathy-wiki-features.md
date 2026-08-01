# Karpathy LLM Wiki Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three ideas from Karpathy's LLM Wiki pattern — wiki lint, query writeback, and ingest log — to strengthen atmina's knowledge management.

**Architecture:** Three independent modules in `src/`: `wiki_lint.py` (cross-reference integrity checker), `ingest_log.py` (chronological ingest journal), and a writeback hook in `src/tools.py`. Each integrates into the existing daily routine as new steps. Wiki lint becomes a pre-generation check alongside @quality-reviewer. Ingest log writes to `wiki/log-ingest.md`. Query writeback enriches wiki pages during interactive analysis.

**Tech Stack:** Python 3.11, SQLite (existing `data/atmina.db`), pathlib, yaml, existing `src/wiki.py` helpers.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/wiki_lint.py` | Wiki integrity checker: orphans, broken links, stale pages, cross-ref gaps |
| Create | `tests/test_wiki_lint.py` | Tests for all lint checks |
| Create | `src/ingest_log.py` | Chronological ingest journal writer/reader |
| Create | `tests/test_ingest_log.py` | Tests for ingest log |
| Modify | `src/ingest.py:1126-1178` | Hook ingest_log after ingest_all completes |
| Modify | `src/social.py:117,343` | Hook ingest_log after twitter/mentions fetch |
| Modify | `src/tools.py:197-235` | Add writeback hook to store_context_note for wiki enrichment |
| Modify | `src/wiki.py:304-400` | Add lint call option to wiki_sync |
| Create | `wiki/log-ingest.md` | Chronological ingest journal (auto-generated) |

---

## Task 1: Wiki Lint — Core Engine

**Files:**
- Create: `src/wiki_lint.py`
- Create: `tests/test_wiki_lint.py`

### Step 1.1: Write failing tests for orphan detection

- [ ] **Write test: detect orphaned person pages**

```python
# tests/test_wiki_lint.py
import tempfile
from pathlib import Path
from src.wiki_lint import lint_wiki


def _make_wiki(tmp: Path, persons: list[str], index_links: list[str]) -> Path:
    """Create minimal wiki structure for testing."""
    wiki = tmp / "wiki"
    (wiki / "persons").mkdir(parents=True)
    (wiki / "topics").mkdir(parents=True)
    for name in persons:
        (wiki / "persons" / f"{name}.md").write_text(f"---\nname: {name}\n---\n")
    index_lines = ["# atmina — Indekss\n"]
    for link in index_links:
        index_lines.append(f"- [[persons/{link}|{link}]]\n")
    (wiki / "index.md").write_text("".join(index_lines))
    return wiki


def test_orphan_person_detected():
    """Person page exists but is not linked from index.md."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(
            Path(tmp),
            persons=["janis-berzins", "anna-kalve"],
            index_links=["janis-berzins"],  # anna-kalve missing from index
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
```

- [ ] **Run test to verify it fails**

Run: `cd ~/atmina && python -m pytest tests/test_wiki_lint.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.wiki_lint'`

### Step 1.2: Write failing tests for broken links and stale pages

- [ ] **Write tests for broken wikilinks and stale frontmatter**

```python
# Append to tests/test_wiki_lint.py

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
    page.write_text("---\nname: Jānis Bērziņš\nclaims_count: 50\n---\n")
    (wiki / "index.md").write_text("- [[persons/janis-berzins|Jānis Bērziņš]]\n")

    # lint_wiki with db_counts override for testing
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
        (wiki / "topics" / "imigracija.md").write_text("---\ntopic: Imigrācija\nclaims_count: 5\n---\n")
        # Person page does NOT mention imigracija
        (wiki / "persons" / "janis-berzins.md").write_text("---\nname: Jānis Bērziņš\ntopics: []\n---\n")
        (wiki / "index.md").write_text("- [[persons/janis-berzins|J]]\n\n## Tēmas\n- [[topics/imigracija|Imigrācija]]\n")

        result = lint_wiki(str(wiki))
        # Topic with claims but no person referencing it is an isolation warning
        isolated = [i for i in result["issues"] if i["type"] == "isolated_topic"]
        assert len(isolated) == 1
```

- [ ] **Run tests to verify they fail**

Run: `cd ~/atmina && python -m pytest tests/test_wiki_lint.py -v`
Expected: FAIL — same ModuleNotFoundError

### Step 1.3: Implement wiki_lint.py

- [ ] **Create `src/wiki_lint.py`**

```python
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
    """Extract all [[target|label]] or [[target]] wikilinks."""
    return re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]", text)


def _collect_pages(wiki_dir: Path, subdir: str) -> dict[str, Path]:
    """Map slug -> file path for all .md files in a subdirectory."""
    d = wiki_dir / subdir
    if not d.exists():
        return {}
    return {p.stem: p for p in d.glob("*.md")}


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

    # Collect all wikilinks from index
    index_links = _extract_wikilinks(index_text)
    # Normalize: "persons/janis-berzins" -> ("persons", "janis-berzins")
    index_targets = set()
    for link in index_links:
        parts = link.split("/", 1)
        if len(parts) == 2:
            index_targets.add((parts[0], parts[1]))

    # 1. Orphan detection: pages that exist but aren't linked from index
    for subdir in ["persons", "topics", "parties"]:
        pages = _collect_pages(wiki, subdir)
        linked_slugs = {slug for cat, slug in index_targets if cat == subdir}
        for slug, path in pages.items():
            if slug not in linked_slugs:
                issues.append({
                    "type": "orphan_page",
                    "path": str(path.relative_to(wiki)),
                    "detail": f"Page exists but not linked from index.md",
                })

    # 2. Broken links: index references pages that don't exist
    for subdir in ["persons", "topics", "parties"]:
        pages = _collect_pages(wiki, subdir)
        linked_slugs = {slug for cat, slug in index_targets if cat == subdir}
        for slug in linked_slugs:
            if slug not in pages:
                issues.append({
                    "type": "broken_link",
                    "target": f"{subdir}/{slug}",
                    "detail": f"index.md links to {subdir}/{slug} but file does not exist",
                })

    # 3. Stale frontmatter: wiki claims_count != DB count
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

    # 4. Isolated topics: topic page with claims but no person page mentions it
    topic_pages = _collect_pages(wiki, "topics")
    persons = _collect_pages(wiki, "persons")
    referenced_topics: set[str] = set()
    for slug, path in persons.items():
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
    import sqlite3

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    rows = db.execute("""
        SELECT p.name, COUNT(c.id) AS cnt
        FROM tracked_politicians p
        LEFT JOIN claims c ON c.opponent_id = p.id
        GROUP BY p.id
    """).fetchall()
    db.close()

    # Build slug -> count map using same transliteration as wiki.py
    from src.wiki import _slugify
    db_counts = {_slugify(r["name"]): r["cnt"] for r in rows}

    return lint_wiki(wiki_dir, db_counts=db_counts)
```

- [ ] **Run tests to verify they pass**

Run: `cd ~/atmina && python -m pytest tests/test_wiki_lint.py -v`
Expected: All 5 tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/wiki_lint.py tests/test_wiki_lint.py
git commit -m "feat: add wiki lint engine — orphans, broken links, stale frontmatter, isolated topics"
```

---

## Task 2: Wiki Lint — Integration with Daily Routine

**Files:**
- Modify: `src/wiki.py:304-400`
- Modify: `.claude/agents/quality-reviewer.md`

### Step 2.1: Write failing test for wiki_sync lint integration

- [ ] **Write test**

```python
# Append to tests/test_wiki_lint.py

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
```

- [ ] **Run test — should pass immediately** (already implemented in Task 1)

Run: `cd ~/atmina && python -m pytest tests/test_wiki_lint.py::test_lint_summary_format -v`
Expected: PASS

### Step 2.2: Add lint option to wiki_sync

- [ ] **Modify `src/wiki.py`** — add import and lint call at end of `wiki_sync()`

Add at the top of `src/wiki.py` (after existing imports):

```python
from src.wiki_lint import lint_wiki_with_db
```

Add at the end of the `wiki_sync()` function, before the `return` statement:

```python
    # Run wiki lint check
    lint_result = lint_wiki_with_db(wiki_dir, db_path)
    if lint_result["stats"]["total_issues"] > 0:
        _append_log(wiki, f"wiki_lint: {lint_result['stats']['total_issues']} issues found — "
                    f"{lint_result['stats']['orphans']} orphans, "
                    f"{lint_result['stats']['broken_links']} broken links, "
                    f"{lint_result['stats']['stale']} stale, "
                    f"{lint_result['stats']['isolated']} isolated topics")
    else:
        _append_log(wiki, "wiki_lint: CLEAN — no issues found")
```

Add `lint_result` to the return dict:

```python
    return {
        "persons": persons_synced,
        "topics": topics_synced,
        "parties": parties_synced,
        "updated_at": _now_lv(),
        "lint": lint_result["stats"],
    }
```

- [ ] **Run existing wiki tests to verify no regression**

Run: `cd ~/atmina && python -m pytest tests/test_wiki.py -v`
Expected: All existing tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/wiki.py
git commit -m "feat: integrate wiki lint into wiki_sync — reports issues in log.md"
```

### Step 2.3: Update quality-reviewer agent checklist

- [ ] **Add lint check to `.claude/agents/quality-reviewer.md`**

Add a new check section after the existing F (Wiki sync) section:

```markdown
### G. Wiki integritāte (wiki lint)

| # | Pārbaude | Komanda | Rezultāts |
|---|----------|---------|-----------|
| G1 | Orphaned pages | `from src.wiki_lint import lint_wiki_with_db; r = lint_wiki_with_db(); print(r['stats'])` | 0 orphans |
| G2 | Broken links | (same as G1) | 0 broken_links |
| G3 | Stale frontmatter | (same as G1) | 0 stale |

**Ja lint atrod problēmas:** Jāfiksē pirms site generation. Orphaned pages = vai politiķis ir inactive? Broken links = vai trūkst wiki_sync? Stale = jāpalaiž wiki_sync vēlreiz.
```

- [ ] **Commit**

```bash
cd ~/atmina
git add .claude/agents/quality-reviewer.md
git commit -m "feat: add wiki lint checks to quality-reviewer agent checklist"
```

---

## Task 3: Chronological Ingest Log

**Files:**
- Create: `src/ingest_log.py`
- Create: `tests/test_ingest_log.py`
- Create: `wiki/log-ingest.md`
- Modify: `src/ingest.py:1126-1178`
- Modify: `src/social.py:117,343`

### Step 3.1: Write failing tests for ingest log

- [ ] **Write tests**

```python
# tests/test_ingest_log.py
import tempfile
from pathlib import Path
from src.ingest_log import append_ingest_entry, read_ingest_log


def test_append_single_entry():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(
            log_path=str(log_path),
            source_name="LSM.lv Latvija",
            source_tier=1,
            documents_added=5,
            documents_skipped=12,
            status="success",
        )
        text = log_path.read_text(encoding="utf-8")
        assert "LSM.lv Latvija" in text
        assert "5 new" in text
        assert "12 skipped" in text
        assert "success" in text


def test_append_preserves_existing():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        log_path.write_text("# Ingest Log\n\n", encoding="utf-8")
        append_ingest_entry(str(log_path), "LSM", 1, 3, 0, "success")
        append_ingest_entry(str(log_path), "Delfi", 2, 7, 2, "success")
        text = log_path.read_text(encoding="utf-8")
        assert "# Ingest Log" in text
        assert "LSM" in text
        assert "Delfi" in text


def test_append_with_error():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(str(log_path), "LETA", 2, 0, 0, "failure", error="Timeout")
        text = log_path.read_text(encoding="utf-8")
        assert "FAILURE" in text or "failure" in text.lower()
        assert "Timeout" in text


def test_append_twitter_batch():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(
            str(log_path),
            source_name="X/Twitter",
            source_tier=0,
            documents_added=23,
            documents_skipped=45,
            status="success",
            extra="12 politiķi",
        )
        text = log_path.read_text(encoding="utf-8")
        assert "X/Twitter" in text
        assert "12 politiķi" in text


def test_read_ingest_log_last_n():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        for i in range(5):
            append_ingest_entry(str(log_path), f"Source-{i}", 1, i, 0, "success")
        entries = read_ingest_log(str(log_path), last_n=3)
        assert len(entries) == 3
        assert "Source-4" in entries[0]  # most recent first
```

- [ ] **Run tests to verify failure**

Run: `cd ~/atmina && python -m pytest tests/test_ingest_log.py -v`
Expected: FAIL — ModuleNotFoundError

### Step 3.2: Implement ingest_log.py

- [ ] **Create `src/ingest_log.py`**

```python
"""
Chronological ingest journal for atmina.
Appends timestamped entries to wiki/log-ingest.md.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_LOG_PATH = "wiki/log-ingest.md"

_LV_OFFSET = timedelta(hours=3)  # EEST


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def append_ingest_entry(
    log_path: str = DEFAULT_LOG_PATH,
    source_name: str = "",
    source_tier: int = 0,
    documents_added: int = 0,
    documents_skipped: int = 0,
    status: str = "success",
    error: str | None = None,
    extra: str | None = None,
) -> None:
    """Append one ingest entry to the log."""
    path = Path(log_path)
    if not path.exists():
        path.write_text("# Ingest Log\n\n", encoding="utf-8")

    ts = _now_lv()
    status_icon = "+" if status == "success" else "x" if status == "failure" else "~"
    parts = [
        f"- `{ts}` [{status_icon}] **{source_name}** (tier {source_tier})",
        f"— {documents_added} new, {documents_skipped} skipped",
    ]
    if extra:
        parts.append(f"— {extra}")
    if error:
        parts.append(f"— ERROR: {error}")

    line = " ".join(parts) + "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def append_ingest_batch_summary(
    results: list[dict],
    log_path: str = DEFAULT_LOG_PATH,
) -> None:
    """Append a batch summary after ingest_all completes."""
    path = Path(log_path)
    if not path.exists():
        path.write_text("# Ingest Log\n\n", encoding="utf-8")

    ts = _now_lv()
    total_docs = sum(r.get("documents", 0) for r in results)
    successes = sum(1 for r in results if r.get("status") == "success")
    failures = sum(1 for r in results if r.get("status") == "failure")

    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n### {ts} — Ingest batch: {len(results)} sources, {total_docs} docs, {successes} ok, {failures} failed\n\n")

    for r in results:
        append_ingest_entry(
            log_path=log_path,
            source_name=r.get("source", "unknown"),
            source_tier=r.get("tier", 0),
            documents_added=r.get("documents", 0),
            documents_skipped=r.get("skipped", 0),
            status=r.get("status", "unknown"),
            error=r.get("error"),
        )


def read_ingest_log(log_path: str = DEFAULT_LOG_PATH, last_n: int = 20) -> list[str]:
    """Read last N entry lines from the log (most recent first)."""
    path = Path(log_path)
    if not path.exists():
        return []
    lines = [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    return list(reversed(lines[-last_n:]))
```

- [ ] **Run tests to verify they pass**

Run: `cd ~/atmina && python -m pytest tests/test_ingest_log.py -v`
Expected: All 5 tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/ingest_log.py tests/test_ingest_log.py
git commit -m "feat: add chronological ingest log — appends to wiki/log-ingest.md"
```

### Step 3.3: Create initial log file

- [ ] **Create `wiki/log-ingest.md`**

```markdown
# Ingest Log

_Hronoloģisks žurnāls — katrs dokuments, kad apstrādāts, no kura avota._

```

- [ ] **Commit**

```bash
cd ~/atmina
git add wiki/log-ingest.md
git commit -m "chore: initialize ingest log file"
```

### Step 3.4: Hook into ingest_all

- [ ] **Modify `src/ingest.py`** — add import at top of file:

```python
from src.ingest_log import append_ingest_batch_summary
```

Add after `print(f"\nIngestion complete: ...")` line (after line 1172), before `return results`:

```python
    if not dry_run:
        append_ingest_batch_summary(results)
```

- [ ] **Modify `src/social.py`** — add import at top:

```python
from src.ingest_log import append_ingest_entry
```

Add at end of `fetch_all_twitter()`, before return:

```python
    total_added = sum(len(tweets) for tweets in result.values())
    append_ingest_entry(
        source_name="X/Twitter",
        source_tier=0,
        documents_added=total_added,
        documents_skipped=0,
        status="success",
        extra=f"{len(result)} politiķi",
    )
```

Add at end of `fetch_all_mentions()`, before return:

```python
    append_ingest_entry(
        source_name="X/Mentions",
        source_tier=0,
        documents_added=len(result),
        documents_skipped=0,
        status="success",
    )
```

- [ ] **Run existing ingest tests to check for regressions**

Run: `cd ~/atmina && python -m pytest tests/ -v -k "not calibration and not embeddings"`
Expected: All tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/ingest.py src/social.py
git commit -m "feat: hook ingest log into ingest_all and social fetchers"
```

---

## Task 4: Query Writeback

**Files:**
- Modify: `src/tools.py:197-235`
- Create: `tests/test_writeback.py`

### Step 4.1: Write failing test for writeback mechanism

- [ ] **Write test**

```python
# tests/test_writeback.py
import tempfile
from pathlib import Path
from src.wiki_writeback import enrich_person_page


def test_enrich_adds_insight_to_body():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text(
            "---\nname: Jānis Bērziņš\nparty: JV\n---\n\n## Piezīmes\n\nExisting note.\n",
            encoding="utf-8",
        )
        enrich_person_page(
            str(page),
            insight="Mainījis pozīciju par Rail Baltica 2x pēdējo 3 mēnešu laikā.",
            source="query writeback",
        )
        text = page.read_text(encoding="utf-8")
        assert "Rail Baltica" in text
        assert "query writeback" in text
        # Frontmatter preserved
        assert "name: Jānis Bērziņš" in text


def test_enrich_does_not_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text("---\nname: J\n---\n\n## Writeback\n\n- insight A\n", encoding="utf-8")
        enrich_person_page(str(page), insight="insight A", source="test")
        text = page.read_text(encoding="utf-8")
        assert text.count("insight A") == 1  # no duplicate


def test_enrich_creates_section_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "janis-berzins.md"
        page.write_text("---\nname: J\n---\n\nSome body text.\n", encoding="utf-8")
        enrich_person_page(str(page), insight="New insight", source="query")
        text = page.read_text(encoding="utf-8")
        assert "## Writeback" in text
        assert "New insight" in text
```

- [ ] **Run to verify failure**

Run: `cd ~/atmina && python -m pytest tests/test_writeback.py -v`
Expected: FAIL — ModuleNotFoundError

### Step 4.2: Implement wiki_writeback.py

- [ ] **Create `src/wiki_writeback.py`**

```python
"""
Query writeback: enrich wiki person/topic pages with insights
discovered during interactive analysis sessions.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

_LV_OFFSET = timedelta(hours=3)

WRITEBACK_SECTION = "## Writeback"


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d")


def enrich_person_page(
    page_path: str,
    insight: str,
    source: str = "query",
) -> bool:
    """Append an insight to a wiki person/topic page.

    Adds under a '## Writeback' section. Creates section if missing.
    Skips if the exact insight text already exists in the page.

    Returns True if the page was modified.
    """
    path = Path(page_path)
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")

    # Dedup: skip if insight already present
    if insight in text:
        return False

    date = _now_lv()
    entry = f"- _{date}_ ({source}): {insight}\n"

    if WRITEBACK_SECTION in text:
        # Append to existing section
        idx = text.index(WRITEBACK_SECTION)
        # Find end of section header line
        newline_after = text.index("\n", idx)
        # Insert after any existing content in the section
        # Find next ## or end of file
        next_section = text.find("\n## ", newline_after + 1)
        if next_section == -1:
            # Append at end
            if not text.endswith("\n"):
                text += "\n"
            text += entry
        else:
            text = text[:next_section] + entry + text[next_section:]
    else:
        # Create section at end
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n{WRITEBACK_SECTION}\n\n{entry}"

    path.write_text(text, encoding="utf-8")
    return True


def enrich_topic_page(
    wiki_dir: str,
    topic_slug: str,
    insight: str,
    source: str = "query",
) -> bool:
    """Enrich a topic page by slug."""
    page = Path(wiki_dir) / "topics" / f"{topic_slug}.md"
    return enrich_person_page(str(page), insight, source)
```

- [ ] **Run tests to verify they pass**

Run: `cd ~/atmina && python -m pytest tests/test_writeback.py -v`
Expected: All 3 tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/wiki_writeback.py tests/test_writeback.py
git commit -m "feat: add query writeback — enrich wiki pages with analysis insights"
```

### Step 4.3: Add writeback tool function

- [ ] **Modify `src/tools.py`** — add new tool function after `store_context_note`:

```python
def writeback_insight(
    politician_name: str | None = None,
    topic: str | None = None,
    insight: str = "",
    source: str = "analysis",
) -> str:
    """Write back an insight to a wiki person or topic page.

    At least one of politician_name or topic must be provided.
    """
    try:
        from src.wiki import _slugify
        from src.wiki_writeback import enrich_person_page, enrich_topic_page

        results = []
        if politician_name:
            slug = _slugify(politician_name)
            page_path = f"wiki/persons/{slug}.md"
            ok = enrich_person_page(page_path, insight, source)
            results.append(f"person/{slug}: {'written' if ok else 'skipped (duplicate or missing)'}")

        if topic:
            slug = _slugify(topic)
            ok = enrich_topic_page("wiki", slug, insight, source)
            results.append(f"topic/{slug}: {'written' if ok else 'skipped (duplicate or missing)'}")

        if not results:
            return _json_error("At least one of politician_name or topic required")

        return _json_success({"writeback": results})
    except Exception as e:
        return _json_error(str(e))
```

- [ ] **Run all tests**

Run: `cd ~/atmina && python -m pytest tests/ -v -k "not calibration and not embeddings"`
Expected: All tests PASS

- [ ] **Commit**

```bash
cd ~/atmina
git add src/tools.py
git commit -m "feat: add writeback_insight tool for interactive analysis sessions"
```

---

## Task 5: Documentation & Routine Update

**Files:**
- Modify: `wiki/operations/daily-routine.md`

### Step 5.1: Update daily routine

- [ ] **Add lint and writeback to daily routine**

Add after Step 8 (Wiki sync), renumber subsequent steps:

```markdown
### 8.5. Wiki lint

Pēc wiki_sync automātiski palaists wiki lint. Pārbaudi rezultātu `wiki/log.md` — ja ir issues:
- **orphan_page**: vai politiķis ir inactive? Ja jā, ignorē. Ja nē, pievieno index.
- **broken_link**: palaid `wiki_sync()` vēlreiz vai noņem saiti no index.
- **stale_frontmatter**: palaid `wiki_sync()` vēlreiz.
- **isolated_topic**: pārbaudi vai tēma ir aktīva. Ja jā, pievieno person lapām.

### 8.6. Query writeback

Analīzes laikā (2.-6. soļi), ja atklāj netriviālu ieskatu par politiķi vai tēmu:
```python
from src.tools import writeback_insight
writeback_insight(politician_name="Evika Siliņa", insight="...", source="daily analysis 2026-04-08")
```
Neraksti triviālas lietas. Raksti tikai to, ko nevar noņemt no DB ar SQL query — kontekstu, modeļus, novērojumus.
```

- [ ] **Add ingest log reference**

Add to Step 1 (Ingest) description:

```markdown
Pēc ingest automātiski tiek papildināts `wiki/log-ingest.md`. Pārbaudi ar:
```python
from src.ingest_log import read_ingest_log
print("\n".join(read_ingest_log(last_n=10)))
```
```

- [ ] **Commit**

```bash
cd ~/atmina
git add wiki/operations/daily-routine.md
git commit -m "docs: update daily routine with wiki lint, writeback, and ingest log steps"
```

### Step 5.2: Final verification

- [ ] **Run full test suite**

Run: `cd ~/atmina && python -m pytest tests/ -v -k "not calibration and not embeddings"`
Expected: All tests PASS

- [ ] **Run type check if configured**

Run: `cd ~/atmina && python -m py_compile src/wiki_lint.py && python -m py_compile src/ingest_log.py && python -m py_compile src/wiki_writeback.py && echo "OK"`
Expected: OK
