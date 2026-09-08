# Zinas Title Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reliably populate `documents.title` at ingest time for ALL web news sources (LSM, Delfi, NRA, TVNet, LETA, Diena, LA.lv, jauns.lv, rus.delfi.lv) plus backfill the 2402 existing rows where title is NULL/empty, so `zinas.html` can drop its content[0:140] heuristic and conform to LV Autortiesību likuma 20. panta "darba nosaukuma" prasībai.

**Architecture:** New pure utility `src/title_extract.py` extracts a canonical title from any HTML using a priority cascade: `og:title` → `twitter:title` → JSON-LD `headline` → `<title>` → `<h1>`. Output is normalized: HTML entities decoded, whitespace collapsed, known site suffixes (` - LSM.lv`, ` | Delfi`, ` - LA.lv`, ` - Latvijas Avīze`, ` - Jauns.lv`, ` - tvnet.lv`, ` - Diena`, ` - NRA`, ` - LETA`, ` - rus.delfi.lv`) stripped, length-capped at 250 chars. Wired into all three live scrape paths in `src/ingest.py`: RSS (`_parse_rss_items` already has title in XML — just pass it through), tier-2 crawl4ai (`_scrape_tier2` has `r.html`), web_scraper trafilatura (`_scrape_web_articles` has full HTML). `insert_document()` in `src/db.py` accepts a new `title` kwarg and persists it via the existing `documents.title` column. A one-shot `scripts/backfill_titles.py` walks legacy rows: when `archive_path` exists it re-extracts from stored HTML; otherwise it derives title from content head (first non-empty line) with the same suffix-strip + entity-decode pipeline. `src/render/news.py:_fetch_news` is simplified: prefer DB title, content fallback only when title is NULL after backfill (very rare).

**Tech Stack:** Python stdlib (`re`, `html`, `json`), BeautifulSoup4 (already in use at `src/ingest.py:13`), pytest. No new dependencies.

---

## Files

**Create:**
- `src/title_extract.py` — pure title extraction utility
- `tests/test_title_extract.py` — unit tests for extractor (8 cases covering all signal sources + suffix variants)
- `scripts/backfill_titles.py` — one-shot DB migration script

**Modify:**
- `src/db.py:231-302` — `insert_document()` accepts `title: Optional[str] = None`, INSERT writes the column
- `src/ingest.py:656-711` — `_parse_rss_items` returns `title` per item dict
- `src/ingest.py:561-600` — `_scrape_tier2` extracts title from `r.html` per article
- `src/ingest.py:502-558` — `_scrape_web_articles` extracts title from per-article HTML
- `src/ingest.py:765-895` — `_ingest_source` plumbs `item.get("title")` into `insert_document(title=...)`
- `src/render/news.py:26-105` — `_fetch_news` drops the content[0:140] fallback once title is reliable; keeps a short safety net for NULL
- `tests/test_db.py` — extend `insert_document` test coverage for title param round-trip

---

## Tasks

### Task 1: Title extractor utility — failing test

**Files:**
- Create: `tests/test_title_extract.py`

- [ ] **Step 1: Write the failing test file**

```python
"""Tests for src.title_extract — title extraction from HTML.

Covers signal priority cascade, site-suffix stripping, entity decoding,
length capping, and graceful handling of missing/empty input.
"""
from src.title_extract import extract_title


def test_og_title_wins_over_html_title():
    html = '''<html><head>
        <meta property="og:title" content="Saeimas budžeta debates">
        <title>Saeimas budžeta debates - LSM.lv</title>
    </head></html>'''
    assert extract_title(html) == "Saeimas budžeta debates"


def test_twitter_title_when_no_og():
    html = '''<html><head>
        <meta name="twitter:title" content="Premjere par vēlēšanām">
        <title>Premjere par vēlēšanām | Delfi</title>
    </head></html>'''
    assert extract_title(html) == "Premjere par vēlēšanām"


def test_jsonld_headline_when_no_meta():
    html = '''<html><head>
        <script type="application/ld+json">
        {"@type":"NewsArticle","headline":"Felss par budžetu"}
        </script>
        <title>Felss par budžetu - NRA</title>
    </head></html>'''
    assert extract_title(html) == "Felss par budžetu"


def test_html_title_with_lsm_suffix_stripped():
    html = '<html><head><title>Saeima atbalsta likumprojektu - LSM.lv</title></head></html>'
    assert extract_title(html) == "Saeima atbalsta likumprojektu"


def test_html_title_with_la_suffix_stripped():
    html = '<html><head><title>Kapsētu likums stājas spēkā - Latvijas Avīze</title></head></html>'
    assert extract_title(html) == "Kapsētu likums stājas spēkā"


def test_h1_fallback_when_no_title_tag():
    html = '<html><body><h1>Vēlēšanu IT problēmas</h1><p>...</p></body></html>'
    assert extract_title(html) == "Vēlēšanu IT problēmas"


def test_html_entities_decoded():
    html = '<html><head><title>Siliņa: &quot;Tas ir nepieņemami&quot;</title></head></html>'
    assert extract_title(html) == 'Siliņa: "Tas ir nepieņemami"'


def test_returns_none_for_empty_or_garbage():
    assert extract_title("") is None
    assert extract_title("<html></html>") is None
    assert extract_title(None) is None


def test_length_capped_at_250():
    long = "x" * 400
    html = f'<html><head><title>{long}</title></head></html>'
    out = extract_title(html)
    assert out is not None
    assert len(out) <= 250


def test_strips_whitespace_and_collapses():
    html = '<html><head><title>  Daudz   atstarpju\n\n\nun rindu  </title></head></html>'
    assert extract_title(html) == "Daudz atstarpju un rindu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_title_extract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.title_extract'`

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_title_extract.py
git commit -F .git-commit-msg.tmp
```

(Commit message in `.git-commit-msg.tmp`:)

```
test(title): add failing tests for HTML title extractor

Covers cascade og:title → twitter:title → JSON-LD headline → <title> → <h1>,
site-suffix stripping (LSM/Delfi/LA/Jauns/TVNet/Diena/NRA/LETA), entity
decode, whitespace collapse, length cap.
```

---

### Task 2: Title extractor utility — implementation

**Files:**
- Create: `src/title_extract.py`

- [ ] **Step 1: Write `src/title_extract.py`**

```python
"""Extract canonical article title from HTML.

Used at ingest time so ``documents.title`` is reliably populated for all
web news sources (LSM, Delfi, NRA, TVNet, LETA, Diena, LA.lv, jauns.lv,
rus.delfi.lv). Same pipeline is reused by scripts/backfill_titles.py for
legacy rows.

Signal priority:
    1. <meta property="og:title">       (most reliable, set by all majors)
    2. <meta name="twitter:title">
    3. JSON-LD NewsArticle.headline
    4. <title>
    5. First <h1>

Output is normalized: HTML entities decoded, whitespace collapsed, known
site suffixes stripped, capped at 250 chars. Returns None if no signal
yields a non-empty result.
"""
from __future__ import annotations

import html
import json
import re
from typing import Optional

# Site-suffix patterns to strip from <title> tags. Ordered most-specific first
# so e.g. " - LSM.lv" matches before " - LSM". Case-insensitive match.
_SITE_SUFFIXES = [
    " - LSM.lv", " | LSM.lv", " - LSM",
    " | Delfi", " - Delfi", " | DELFI", " - DELFI",
    " - Latvijas Avīze", " - LA.lv", " | LA.lv",
    " - Jauns.lv", " | Jauns.lv",
    " - TVNet", " | TVNet", " - tvnet.lv", " | tvnet.lv",
    " - Diena", " | Diena", " - diena.lv",
    " - NRA", " | NRA", " - nra.lv",
    " - LETA", " | LETA",
    " - rus.delfi.lv", " | rus.delfi.lv",
]

_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TWITTER_TITLE_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TITLE_TAG_RE = re.compile(
    r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL
)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

_MAX_LEN = 250


def extract_title(raw_html: Optional[str]) -> Optional[str]:
    """Return the article's canonical title or None.

    Tries og:title → twitter:title → JSON-LD headline → <title> → <h1>.
    Strips known site suffixes, decodes HTML entities, collapses whitespace,
    caps length at 250 chars.
    """
    if not raw_html or not isinstance(raw_html, str):
        return None

    candidate = (
        _try_meta(raw_html, _OG_TITLE_RE)
        or _try_meta(raw_html, _TWITTER_TITLE_RE)
        or _try_jsonld_headline(raw_html)
        or _try_tag(raw_html, _TITLE_TAG_RE)
        or _try_tag(raw_html, _H1_RE)
    )
    if not candidate:
        return None

    return _normalize(candidate)


def _try_meta(raw_html: str, pattern: re.Pattern[str]) -> Optional[str]:
    m = pattern.search(raw_html)
    return m.group(1) if m else None


def _try_tag(raw_html: str, pattern: re.Pattern[str]) -> Optional[str]:
    m = pattern.search(raw_html)
    if not m:
        return None
    inner = _TAG_STRIP_RE.sub(" ", m.group(1))
    return inner.strip() or None


def _try_jsonld_headline(raw_html: str) -> Optional[str]:
    """Search every <script type=application/ld+json> block for a `headline`."""
    for m in _JSONLD_RE.finditer(raw_html):
        block = m.group(1).strip()
        if not block:
            continue
        # JSON-LD may be a single object, an array, or have @graph wrapper.
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        for headline in _walk_jsonld_headline(data):
            if headline:
                return headline
    return None


def _walk_jsonld_headline(node):
    if isinstance(node, dict):
        h = node.get("headline")
        if isinstance(h, str) and h.strip():
            yield h
        for key in ("@graph", "mainEntity"):
            child = node.get(key)
            if child is not None:
                yield from _walk_jsonld_headline(child)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_jsonld_headline(item)


def _normalize(text: str) -> Optional[str]:
    decoded = html.unescape(text)
    collapsed = _WHITESPACE_RE.sub(" ", decoded).strip()
    if not collapsed:
        return None
    stripped = _strip_site_suffix(collapsed)
    if not stripped:
        return None
    return stripped[:_MAX_LEN].rstrip()


def _strip_site_suffix(text: str) -> str:
    lower = text.lower()
    for suffix in _SITE_SUFFIXES:
        if lower.endswith(suffix.lower()):
            return text[: -len(suffix)].rstrip()
    return text
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_title_extract.py -v`
Expected: 10 passed

- [ ] **Step 3: Run lint**

Run: `.venv/Scripts/python -m ruff check src/title_extract.py tests/test_title_extract.py`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add src/title_extract.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(title): add HTML title extractor with cascade + site-suffix strip

Pure utility — og:title → twitter:title → JSON-LD headline → <title> → <h1>.
Strips known LV news suffixes (LSM/Delfi/LA/Jauns/TVNet/Diena/NRA/LETA),
decodes HTML entities, collapses whitespace, caps at 250 chars. Reused by
ingest pipeline + backfill script.
```

---

### Task 3: Persist title in `insert_document` — failing test

**Files:**
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add a failing test for title round-trip**

Append to `tests/test_db.py`:

```python
def test_insert_document_persists_title(tmp_path, monkeypatch):
    """insert_document writes the title kwarg to the documents.title column."""
    from src import db as db_module

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    doc_id = db_module.insert_document(
        content="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        source_id=None,
        platform="web",
        source_url="https://example.lv/article-1",
        title="Saeima atbalsta budžetu",
        db_path=db_path,
    )
    assert doc_id is not None

    conn = db_module.get_db(db_path)
    row = conn.execute(
        "SELECT title FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    assert row["title"] == "Saeima atbalsta budžetu"


def test_insert_document_title_optional(tmp_path, monkeypatch):
    """insert_document accepts no title — column stays NULL."""
    from src import db as db_module

    db_path = str(tmp_path / "test2.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    doc_id = db_module.insert_document(
        content="Another article body with enough words to pass any filter.",
        source_id=None,
        source_url="https://example.lv/article-2",
        db_path=db_path,
    )
    assert doc_id is not None

    conn = db_module.get_db(db_path)
    row = conn.execute(
        "SELECT title FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    assert row["title"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_db.py::test_insert_document_persists_title -v`
Expected: FAIL with `TypeError: insert_document() got an unexpected keyword argument 'title'`

---

### Task 4: Persist title in `insert_document` — implementation

**Files:**
- Modify: `src/db.py:231-302`

- [ ] **Step 1: Add `title` parameter to `insert_document` signature**

In `src/db.py`, replace the `insert_document` definition (lines 231-302). Find:

```python
def insert_document(
    content: str,
    source_id: Optional[int],
    platform: str = "web",
    language: str = "lv",
    is_auto_caption: bool = False,
    source_url: Optional[str] = None,
    published_at: Optional[str] = None,
    reply_count: Optional[int] = None,
    retweet_count: Optional[int] = None,
    favorite_count: Optional[int] = None,
    politician_links: Optional[list[tuple[int, str]]] = None,
    db_path: str = DB_PATH,
) -> Optional[int]:
```

Replace with:

```python
def insert_document(
    content: str,
    source_id: Optional[int],
    platform: str = "web",
    language: str = "lv",
    is_auto_caption: bool = False,
    source_url: Optional[str] = None,
    published_at: Optional[str] = None,
    reply_count: Optional[int] = None,
    retweet_count: Optional[int] = None,
    favorite_count: Optional[int] = None,
    politician_links: Optional[list[tuple[int, str]]] = None,
    title: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Optional[int]:
```

- [ ] **Step 2: Add `title` to the INSERT SQL**

Find the existing INSERT (lines 281-289):

```python
    db.execute(
        """INSERT INTO documents (content, content_hash, simhash, source_id,
           platform, is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
           published_at, scraped_at, reply_count, retweet_count, favorite_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (content, content_hash, sim, source_id, platform,
         is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
         published_at, now_lv(), reply_count, retweet_count, favorite_count),
    )
```

Replace with:

```python
    db.execute(
        """INSERT INTO documents (content, content_hash, simhash, source_id,
           platform, is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
           published_at, scraped_at, reply_count, retweet_count, favorite_count, title)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (content, content_hash, sim, source_id, platform,
         is_auto_caption, near_dupe_of, source_domain, source_url, word_count, language,
         published_at, now_lv(), reply_count, retweet_count, favorite_count, title),
    )
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_db.py::test_insert_document_persists_title tests/test_db.py::test_insert_document_title_optional -v`
Expected: 2 passed

- [ ] **Step 4: Run full db test suite to confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/test_db.py -v`
Expected: all green

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(db): insert_document persists title to documents.title column

Adds optional title kwarg threaded into the INSERT. Column already exists
on the schema (added in earlier migration); only the writer was missing.
Tests cover both populated and NULL paths.
```

---

### Task 5: Wire title into RSS path (`_parse_rss_items`)

**Files:**
- Modify: `src/ingest.py:656-711`

- [ ] **Step 1: Verify current RSS handling**

Read `src/ingest.py:656-711`. Note that `title` is already extracted at line 676 but only used to build the `text` field. Atom path at line 691 has the same pattern.

- [ ] **Step 2: Add per-item title to RSS branch**

In `src/ingest.py`, find (line 685-687, in the RSS 2.0 branch):

```python
            if parts and _is_relevant_section(item_url):
                items.append({"text": " — ".join(parts), "url": item_url,
                              "published_at": pub_dt.isoformat() if pub_dt else None})
```

Replace with:

```python
            if parts and _is_relevant_section(item_url):
                items.append({"text": " — ".join(parts), "url": item_url,
                              "published_at": pub_dt.isoformat() if pub_dt else None,
                              "title": title or None})
```

- [ ] **Step 3: Add per-item title to Atom branch**

In `src/ingest.py`, find (line 705-708, in the Atom branch):

```python
                if parts:
                    items.append({"text": " — ".join(parts),
                                  "url": (link.strip() if link else None) or base_url,
                                  "published_at": pub_dt.isoformat() if pub_dt else None})
```

Replace with:

```python
                if parts:
                    items.append({"text": " — ".join(parts),
                                  "url": (link.strip() if link else None) or base_url,
                                  "published_at": pub_dt.isoformat() if pub_dt else None,
                                  "title": title or None})
```

- [ ] **Step 4: Add a unit test for RSS title pass-through**

Append to `tests/test_ingest.py` (create the file if it doesn't exist; if it does, add to the bottom):

```python
def test_parse_rss_items_passes_title_through():
    """_parse_rss_items emits a 'title' key per item from <title> tag."""
    from src.ingest import _parse_rss_items
    from datetime import datetime, timedelta

    future = (datetime.now() + timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item>
        <title>Saeima atbalsta budžetu</title>
        <description>Saeima šodien pieņēma budžeta likumprojektu.</description>
        <link>https://www.lsm.lv/raksts/zinas/latvija/saeima-atbalsta.a000001/</link>
        <pubDate>{future}</pubDate>
    </item>
    </channel></rss>"""
    items = _parse_rss_items(rss, "https://www.lsm.lv/feed/")
    assert len(items) == 1
    assert items[0]["title"] == "Saeima atbalsta budžetu"
```

- [ ] **Step 5: Run the new test**

Run: `.venv/Scripts/python -m pytest tests/test_ingest.py::test_parse_rss_items_passes_title_through -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/ingest.py tests/test_ingest.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(ingest): RSS path emits per-item title from <title> tag

_parse_rss_items already parsed <title> for the joined text field —
now also surfaces it as a dedicated `title` key for downstream
insert_document() to persist. Covers both RSS 2.0 and Atom branches.
```

---

### Task 6: Wire title into web_scraper path (`_scrape_web_articles`)

**Files:**
- Modify: `src/ingest.py:502-558`

- [ ] **Step 1: Capture HTML for title extraction in the per-article loop**

In `src/ingest.py`, find (line 538-553):

```python
        # Step 2: Fetch and extract each article (limit to max_articles)
        items = []
        for article_url in article_urls[:max_articles]:
            try:
                html = await _fetch_page(client, article_url)
                if not html:
                    continue
                text = _clean_extracted_text(trafilatura.extract(
                    html, include_comments=False, include_tables=False, deduplicate=True))
                if not text:
                    continue
                items.append({"text": text[:50000], "url": article_url,
                              "published_at": _extract_published_at(html)})

            except Exception:
                continue

            # Brief pause between requests to be respectful
            await asyncio.sleep(0.5)
```

Replace with:

```python
        # Step 2: Fetch and extract each article (limit to max_articles)
        from src.title_extract import extract_title
        items = []
        for article_url in article_urls[:max_articles]:
            try:
                html = await _fetch_page(client, article_url)
                if not html:
                    continue
                text = _clean_extracted_text(trafilatura.extract(
                    html, include_comments=False, include_tables=False, deduplicate=True))
                if not text:
                    continue
                items.append({"text": text[:50000], "url": article_url,
                              "published_at": _extract_published_at(html),
                              "title": extract_title(html)})

            except Exception:
                continue

            # Brief pause between requests to be respectful
            await asyncio.sleep(0.5)
```

- [ ] **Step 2: Also wire the homepage fallback branch (line 530-535)**

Find:

```python
        if not article_urls:
            # Last resort: extract whatever text we can from the homepage
            fallback_html = await _fetch_page(client, url)
            text = trafilatura.extract(fallback_html, include_comments=False) if fallback_html else None
            if text and len(text) >= 100:
                return [{"text": text, "url": url}]
            return None
```

Replace with:

```python
        if not article_urls:
            # Last resort: extract whatever text we can from the homepage
            fallback_html = await _fetch_page(client, url)
            text = trafilatura.extract(fallback_html, include_comments=False) if fallback_html else None
            if text and len(text) >= 100:
                from src.title_extract import extract_title
                return [{"text": text, "url": url,
                         "title": extract_title(fallback_html)}]
            return None
```

- [ ] **Step 3: Commit**

```bash
git add src/ingest.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(ingest): web_scraper path extracts title from per-article HTML

_scrape_web_articles already has full HTML in scope (used for
_extract_published_at). Adds parallel extract_title() call so LA.lv,
NRA, Delfi, jauns.lv articles get titles persisted at ingest time.
```

---

### Task 7: Wire title into tier-2 crawl4ai path (`_scrape_tier2`)

**Files:**
- Modify: `src/ingest.py:561-600`

- [ ] **Step 1: Add title extraction to the tier-2 article loop**

In `src/ingest.py`, find (line 585-595):

```python
            items = []
            for article_url in article_urls[:30]:
                try:
                    r = await crawler.arun(url=article_url, config=run_config)
                    text = (getattr(r, 'fit_markdown', None) or r.markdown) if r.success else None
                    if text and len(text) >= 100:
                        items.append({"text": text[:50000], "url": article_url,
                                      "published_at": _extract_published_at(getattr(r, "html", None))})
                except Exception:
                    pass
                await asyncio.sleep(1)
```

Replace with:

```python
            from src.title_extract import extract_title
            items = []
            for article_url in article_urls[:30]:
                try:
                    r = await crawler.arun(url=article_url, config=run_config)
                    text = (getattr(r, 'fit_markdown', None) or r.markdown) if r.success else None
                    if text and len(text) >= 100:
                        article_html = getattr(r, "html", None)
                        items.append({"text": text[:50000], "url": article_url,
                                      "published_at": _extract_published_at(article_html),
                                      "title": extract_title(article_html)})
                except Exception:
                    pass
                await asyncio.sleep(1)
```

- [ ] **Step 2: Also wire the homepage-fallback branch (line 580-583)**

Find:

```python
            if not article_urls:
                # Fallback: if no article links found, return homepage markdown as single item
                if homepage.markdown:
                    return [{"text": homepage.markdown, "url": url,
                             "published_at": _extract_published_at(homepage.html)}]
                return None
```

Replace with:

```python
            if not article_urls:
                # Fallback: if no article links found, return homepage markdown as single item
                if homepage.markdown:
                    from src.title_extract import extract_title
                    return [{"text": homepage.markdown, "url": url,
                             "published_at": _extract_published_at(homepage.html),
                             "title": extract_title(homepage.html)}]
                return None
```

- [ ] **Step 3: Commit**

```bash
git add src/ingest.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(ingest): tier2 crawl4ai path extracts title from r.html

Same pattern as web_scraper — crawl4ai response object exposes the raw
HTML, which extract_title() consumes for the cascade lookup. Brings
TVNet (the live tier-2 source) up to par with RSS sources.
```

---

### Task 8: Plumb item title through `_ingest_source` to `insert_document`

**Files:**
- Modify: `src/ingest.py:765-895` (the `_ingest_source` function, specifically the `insert_document` call near line 859)

- [ ] **Step 1: Pass `item.get("title")` into insert_document**

In `src/ingest.py`, find (line 859-867):

```python
                doc_id = insert_document(
                    item_text,
                    politician_links=politician_links or None,
                    source_id=db_source_id,
                    platform=src_platform,
                    language=detected_lang,
                    source_url=article_url,
                    published_at=item.get("published_at"),
                )
```

Replace with:

```python
                doc_id = insert_document(
                    item_text,
                    politician_links=politician_links or None,
                    source_id=db_source_id,
                    platform=src_platform,
                    language=detected_lang,
                    source_url=article_url,
                    published_at=item.get("published_at"),
                    title=item.get("title"),
                )
```

- [ ] **Step 2: Run full test suite to confirm no regressions**

Run: `bash scripts/check.sh`
Expected: ruff clean, all pytest green, generate_public_site smoke OK

- [ ] **Step 3: Commit**

```bash
git add src/ingest.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(ingest): plumb per-item title from scrape paths into insert_document

Closes the forward-fix path: from now on, every newly-ingested web
article persists documents.title. Backfill of historical 2402 NULL rows
handled in scripts/backfill_titles.py (next commit).
```

---

### Task 9: Backfill script — failing test

**Files:**
- Create: `tests/test_backfill_titles.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/backfill_titles.py — title derivation from existing content."""
from scripts.backfill_titles import derive_title_from_content


def test_first_line_extracted_as_title():
    content = "Saeima atbalsta budžetu\n\nŠodien Saeima trešajā lasījumā..."
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu"


def test_site_suffix_stripped_from_first_line():
    content = "Saeima atbalsta budžetu - LSM.lv\n\nŠodien Saeima..."
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu"


def test_skips_too_short_first_line():
    content = "FOTO\n\nSaeima atbalsta budžetu šodien plkst. 14.00."
    # First line "FOTO" is too short — falls through to next non-empty line
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu šodien plkst. 14.00."


def test_skips_too_long_first_line():
    long_line = "x" * 500
    content = f"{long_line}\n\nReāls virsraksts šeit"
    out = derive_title_from_content(content)
    # Skip the 500-char line; pick the next reasonable one
    assert out == "Reāls virsraksts šeit"


def test_returns_none_for_empty_content():
    assert derive_title_from_content("") is None
    assert derive_title_from_content(None) is None


def test_strips_trailing_zero_count_marker():
    """LA.lv content often ends first line with ' 0' (comment count). Strip it."""
    content = "Premjeres VIP tēriņi Amsterdamā: atbilde 0\n\nVairāk nekā 4000 eiro..."
    assert derive_title_from_content(content) == "Premjeres VIP tēriņi Amsterdamā: atbilde"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_backfill_titles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.backfill_titles'`

---

### Task 10: Backfill script — implementation

**Files:**
- Create: `scripts/backfill_titles.py`

- [ ] **Step 1: Write `scripts/backfill_titles.py`**

```python
"""One-shot backfill: populate documents.title for legacy web rows.

Strategy: for every documents row where platform='web' AND title IS NULL/empty,
derive a title from the first reasonable content line, applying the same
suffix-strip + entity-decode pipeline as src/title_extract.

Run once after the title-extraction forward-fix lands. Idempotent — safe to
re-run; only updates rows still missing a title.

Usage:
    python -m scripts.backfill_titles                  # dry-run summary
    python -m scripts.backfill_titles --apply          # write to DB
    python -m scripts.backfill_titles --limit 100      # cap rows touched
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from typing import Optional

from src.db import DB_PATH, get_db
from src.title_extract import _normalize  # reuse suffix-strip + entity decode

# First content line is candidate. Reject lines outside [10, 250] chars.
_MIN_LEN = 10
_MAX_LEN = 250

# LA.lv content often ends headline with " 0" (comment count). Strip.
_LA_COMMENT_COUNT_RE = re.compile(r"\s+0\s*$")


def derive_title_from_content(content: Optional[str]) -> Optional[str]:
    """Pick the first non-trivial content line as a title candidate."""
    if not content or not isinstance(content, str):
        return None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Strip LA.lv comment-count suffix before length check
        line = _LA_COMMENT_COUNT_RE.sub("", line).strip()
        if _MIN_LEN <= len(line) <= _MAX_LEN:
            return _normalize(line)
    return None


def backfill(db_path: str = DB_PATH, apply: bool = False, limit: Optional[int] = None) -> dict:
    """Walk title-less web docs and either preview or apply derived titles."""
    db = get_db(db_path)
    where = "platform='web' AND (title IS NULL OR title = '')"
    sql = f"SELECT id, content FROM documents WHERE {where}"
    if limit:
        sql += f" LIMIT {int(limit)}"

    rows = db.execute(sql).fetchall()
    derived = 0
    skipped = 0
    updates: list[tuple[str, int]] = []
    for r in rows:
        title = derive_title_from_content(r["content"])
        if title:
            derived += 1
            updates.append((title, r["id"]))
        else:
            skipped += 1

    if apply and updates:
        db.executemany("UPDATE documents SET title = ? WHERE id = ?", updates)
        db.commit()

    db.close()
    return {
        "scanned": len(rows),
        "derived": derived,
        "skipped": skipped,
        "applied": len(updates) if apply else 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="write updates to DB")
    p.add_argument("--limit", type=int, default=None, help="cap rows scanned")
    args = p.parse_args()

    summary = backfill(apply=args.apply, limit=args.limit)
    print(f"Scanned:  {summary['scanned']}")
    print(f"Derived:  {summary['derived']}")
    print(f"Skipped:  {summary['skipped']}")
    print(f"Applied:  {summary['applied']}")
    if not args.apply:
        print("\n(dry-run — re-run with --apply to persist)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run unit tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_backfill_titles.py -v`
Expected: 6 passed

- [ ] **Step 3: Dry-run on real DB to preview impact**

Run: `.venv/Scripts/python -m scripts.backfill_titles`
Expected: prints summary like `Scanned: 2402, Derived: ~2200, Skipped: ~200, Applied: 0`

- [ ] **Step 4: Apply the backfill**

Run: `.venv/Scripts/python -m scripts.backfill_titles --apply`
Expected: prints summary with non-zero `Applied:` count

- [ ] **Step 5: Verify title coverage with the same probe used in plan prep**

Run:

```bash
.venv/Scripts/python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
total = db.execute(\"SELECT COUNT(*) FROM documents WHERE platform='web'\").fetchone()[0]
nulls = db.execute(\"SELECT COUNT(*) FROM documents WHERE platform='web' AND (title IS NULL OR title = '')\").fetchone()[0]
print(f'web docs total: {total}, missing title: {nulls} ({100*nulls/total:.1f}%)')"
```

Expected: missing-title share drops from ~58% to <10%.

- [ ] **Step 6: Commit**

```bash
git add scripts/backfill_titles.py tests/test_backfill_titles.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
feat(backfill): one-shot title backfill for legacy web docs

Derives title from first reasonable content line (10-250 chars), reuses
src.title_extract._normalize for suffix-strip + entity decode. Strips
LA.lv " 0" comment-count noise. Idempotent. Run once with --apply
after the forward-fix lands.
```

---

### Task 11: Simplify `_fetch_news` to read DB title

**Files:**
- Modify: `src/render/news.py:46-65`

- [ ] **Step 1: Drop the content[0:140] heuristic when title is reliable**

In `src/render/news.py`, find (lines 46-65):

```python
        # Headline: prefer DB title field, then first line of content, then URL slug
        content = d.get("content") or ""
        headline = d.get("title") or ""
        if not headline and content:
            first_line = content.split("\n")[0].strip()
            if 10 < len(first_line) < 300:
                headline = first_line
            else:
                for sep in (". ", "! ", "? "):
                    idx = content.find(sep)
                    if 20 < idx < 200:
                        headline = content[:idx].strip()
                        break
            if not headline:
                headline = content[:140].strip()
                if len(content) > 140:
                    headline = headline.rsplit(" ", 1)[0] + "…"
        if not headline:
            headline = d["source_url"].split("/")[-1].replace("-", " ").replace(".htm", "")[:100]
```

Replace with:

```python
        # Headline: prefer DB title (populated at ingest + by backfill).
        # Last-resort fallback to URL slug for the rare row that escaped
        # both forward-fix and backfill (e.g. content too short to derive).
        content = d.get("content") or ""
        headline = (d.get("title") or "").strip()
        if not headline:
            headline = d["source_url"].split("/")[-1].replace("-", " ").replace(".htm", "")[:100]
```

- [ ] **Step 2: Smoke-test the static-site generator**

Run: `.venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"`
Expected: completes without error, `output/atmina/zinas.html` regenerated.

- [ ] **Step 3: Spot-check rendered titles for previously-broken sources**

Run:

```bash
.venv/Scripts/python -c "
import re
with open('output/atmina/zinas.html', encoding='utf-8') as f:
    html = f.read()
# Print first 30 article cards' titles
matches = re.findall(r'<h3[^>]*class=\"news-headline[^\"]*\"[^>]*>([^<]+)</h3>', html)
for h in matches[:30]:
    print(h.strip())
"
```

Expected: real article titles visible (not URL slugs or content fragments). Specifically check that LA.lv articles render proper titles like "Premjeres VIP tēriņi Amsterdamā" rather than "Premjeres VIP tēriņi Amsterdamā: Valsts kanc…".

- [ ] **Step 4: Run full check.sh**

Run: `bash scripts/check.sh`
Expected: ruff clean, all pytest green, generate smoke OK.

- [ ] **Step 5: Commit**

```bash
git add src/render/news.py
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
refactor(render): zinas.html reads documents.title directly

Drops the content[0:140] heuristic now that title is reliably populated
at ingest (forward-fix) and by backfill (legacy rows). Only fallback
that remains is URL-slug, for the rare row where content is too short
to derive a candidate.
```

---

### Task 12: Wiki documentation

**Files:**
- Modify: `wiki/CHANGELOG.md` — add a dated entry summarizing the change
- Modify: `wiki/index.md` — bump status counts only if relevant (likely no change)

- [ ] **Step 1: Add CHANGELOG entry**

Append to `wiki/CHANGELOG.md` under the most recent date heading (or create a new `## 2026-04-30 — title extraction across all news sources` section). Content:

```markdown
## 2026-04-30 — `documents.title` reliably populated for all news sources

Forward-fix + backfill landed. `src.title_extract.extract_title()` runs at ingest
on every web scrape path (RSS in `_parse_rss_items`, crawl4ai in `_scrape_tier2`,
trafilatura in `_scrape_web_articles`); persisted via `insert_document(title=...)`
into the existing `documents.title` column. One-shot `scripts/backfill_titles.py`
walked legacy rows (~2402 web docs missing title) and derived from content head.

Result: `zinas.html` no longer falls back to `content[0:140]` heuristic — it
reads the DB column directly. Aligns atmina.lv with Autortiesību likuma 20. panta
"darba nosaukuma" prasību (sk. arī source_url un source_domain ka avota norādei).

Signal cascade: og:title → twitter:title → JSON-LD headline → <title> → <h1>.
Suffix strip: " - LSM.lv", " | Delfi", " - Latvijas Avīze", " - Jauns.lv",
" - tvnet.lv", " - Diena", " - NRA", " - LETA", " - rus.delfi.lv".
Author name (likuma 20. panta otra prasība) joprojām nav DB shēmā — see
follow-up plan `docs/superpowers/plans/2026-04-30-document-author-extraction.md`
when prioritized.
```

- [ ] **Step 2: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -F .git-commit-msg.tmp
```

(Commit message:)

```
docs(wiki): CHANGELOG — title extraction across news sources

Documents the forward-fix + backfill pair, signal cascade, suffix-strip
list, and the remaining gap (author name) for the follow-up plan.
```

---

## Verification

After all 12 tasks land:

1. **Test suite**: `bash scripts/check.sh` — must be green (ruff + pytest + generate smoke)
2. **Title coverage probe**: web docs missing title <10% (down from 58% baseline)
3. **Visual spot-check**: `output/atmina/zinas.html` renders proper titles for LA.lv, Delfi, NRA, jauns.lv articles (not content fragments or URL slugs)
4. **Idempotence**: re-running `scripts/backfill_titles.py --apply` reports `Applied: 0` (already done)
5. **No regressions in dependent renders**: `python -c "from src.render import generate_public_site; generate_public_site()"` completes; spot-check `output/atmina/index.html` and a politician profile page render unchanged

---

## Out of scope (follow-up plans)

- **Author name extraction** (Autortiesību likuma 20. panta otra prasība). Requires `documents.author` column + `with_metadata=True` extraction. Tracked separately as `docs/superpowers/plans/2026-04-30-document-author-extraction.md` — only created when user prioritizes it.
- **Title normalization for X/Twitter docs**: `platform='x'` and `platform='x_mention'` use a different content model (no HTML, no concept of title); zinas.html already filters to `platform='web'` only.
- **Saeima/video docs**: have their own ingestion paths (`src/saeima/`, `src/video_ingest/`) that already populate title via different routes; this plan does not touch them.
