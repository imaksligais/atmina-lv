# Document-Politicians Junction Table — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `documents.opponent_id` and `documents.mention_target_id` with a many-to-many `document_politicians` junction table so documents can reference multiple politicians.

**Architecture:** New junction table `document_politicians(document_id, politician_id, role)` absorbs both columns. Migration script populates it from existing data, deduplicates x_mention documents, then drops old columns. Consumer code updated to JOIN through junction.

**Tech Stack:** Python 3.11+, SQLite (WAL), Pydantic v2

**Spec:** `docs/superpowers/specs/2026-04-09-document-politicians-junction-design.md`

**Rollback:** DB backup at `data/atmina_backup_20260409_120904.db`, git at `97f4f2c`

---

## Blast Radius Clarification

**Queries that MUST change** (reference `documents.opponent_id` or `documents.mention_target_id`):
- `db.py`: schema, `insert_document()`, `search_similar()`, `delete_politician_data()`, indexes, migration code
- `generate.py`: lines 88, 104, 120, 302-308, 847, 866, 1289-1290, 1306-1307 (~10 queries)
- `tools.py`: lines 62, 146 (2 queries)
- `analyze.py`: lines 49, 87 (2 queries)
- `routine.py`: lines 172-175, 185 (2 queries)
- `social.py`: lines 34-46, 82, 230, 298, 364-416 (~8 places)
- `ingest.py`: lines 906-932, 939-956, 1053-1077 (~4 functions)
- `x_mentions.py`: lines 59-93, 162 (~3 places)
- `x_scraper.py`: lines 192-208 (~2 places)
- `saeima.py`: line 594 (1 call)

**Queries that DON'T change** (reference `claims.opponent_id`, `contradictions.opponent_id`, etc.):
- `generate.py`: lines 49, 213, 223, 231, 266, 926, 945, 1029-1034, 1091-1092, 1186-1207, 1227 (~17 queries — untouched)
- `tools.py`: lines 86-105, 124-159, 169-382, 396-409 (~30 references — untouched)
- `wiki.py`: lines 117-225, 373-396 (~11 queries — untouched, but we ADD one new query)
- `briefs.py`: lines 36, 84, 153 (all on claims — untouched)
- `cross_check.py`: lines 28-50 (all on claims — untouched)
- `wiki_lint.py`: line 153 (on claims — untouched)
- `models.py`: all (claims/analyses models — untouched)

---

## Task 1: Schema + Migration Script

**Files:**
- Modify: `src/db.py:20-210` (schema), `src/db.py:315-330` (migration)
- Modify: `scripts/migrate_db.py` (add migration step)

### Step 1.1: Add `document_politicians` table to schema

- [ ] In `src/db.py`, inside the `_init_db()` `executescript()` block (after the `documents` table definition around line 87), add:

```sql
CREATE TABLE IF NOT EXISTS document_politicians (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    role TEXT NOT NULL DEFAULT 'subject',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, politician_id, role)
);
```

- [ ] Add indexes after the existing index block (around line 210):

```sql
CREATE INDEX IF NOT EXISTS idx_dp_politician ON document_politicians(politician_id, role);
CREATE INDEX IF NOT EXISTS idx_dp_document ON document_politicians(document_id);
```

### Step 1.2: Write migration step in `scripts/migrate_db.py`

- [ ] Add a new migration step function. Read the file first to find the last step number, then add:

```python
def step_migrate_document_politicians(conn: sqlite3.Connection) -> None:
    """Migrate documents.opponent_id and mention_target_id to document_politicians junction table."""
    c = conn.cursor()

    # 1. Create junction table if not exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS document_politicians (
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            role TEXT NOT NULL DEFAULT 'subject',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (document_id, politician_id, role)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_politician ON document_politicians(politician_id, role)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_document ON document_politicians(document_id)")

    # 2. Populate from existing opponent_id
    c.execute("""
        INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
        SELECT id, opponent_id, 'subject', COALESCE(scraped_at, CURRENT_TIMESTAMP)
        FROM documents WHERE opponent_id IS NOT NULL
    """)
    migrated_subject = c.rowcount
    print(f"  Migrated {migrated_subject} opponent_id -> document_politicians (subject)")

    # 3. Populate from existing mention_target_id
    c.execute("""
        INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
        SELECT id, mention_target_id, 'mention_target', COALESCE(scraped_at, CURRENT_TIMESTAMP)
        FROM documents WHERE mention_target_id IS NOT NULL
    """)
    migrated_mt = c.rowcount
    print(f"  Migrated {migrated_mt} mention_target_id -> document_politicians (mention_target)")

    # 4. Deduplicate x_mention documents
    # Find groups of duplicate x_mention docs (same source_url, same content)
    dupes = c.execute("""
        SELECT source_url, MIN(id) AS keep_id, GROUP_CONCAT(id) AS all_ids, COUNT(*) AS cnt
        FROM documents
        WHERE platform = 'x_mention' AND source_url IS NOT NULL
        GROUP BY source_url, content
        HAVING COUNT(*) > 1
    """).fetchall()

    total_deleted = 0
    for dupe in dupes:
        keep_id = dupe[1]
        all_ids = [int(x) for x in dupe[2].split(",")]
        delete_ids = [did for did in all_ids if did != keep_id]

        if not delete_ids:
            continue

        # Merge junction rows to the kept document
        for did in delete_ids:
            c.execute("""
                INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role, created_at)
                SELECT ?, politician_id, role, created_at
                FROM document_politicians WHERE document_id = ?
            """, (keep_id, did))

            # Update mention_classifications references
            c.execute("UPDATE OR IGNORE mention_classifications SET document_id = ? WHERE document_id = ?",
                      (keep_id, did))

            # Update claims references
            c.execute("UPDATE claims SET document_id = ? WHERE document_id = ?", (keep_id, did))

        # Delete junction rows for dupes
        placeholders = ",".join("?" * len(delete_ids))
        c.execute(f"DELETE FROM document_politicians WHERE document_id IN ({placeholders})", delete_ids)

        # Delete duplicate documents
        c.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", delete_ids)
        total_deleted += len(delete_ids)

    print(f"  Deduplicated x_mentions: removed {total_deleted} duplicate documents")

    # 5. Drop old columns
    c.execute("ALTER TABLE documents DROP COLUMN opponent_id")
    c.execute("ALTER TABLE documents DROP COLUMN mention_target_id")
    print("  Dropped opponent_id and mention_target_id columns from documents")

    # 6. Clean up old indexes (they auto-drop with columns in SQLite, but be safe)
    c.execute("DROP INDEX IF EXISTS idx_documents_opponent")
    c.execute("DROP INDEX IF EXISTS idx_documents_mention_target")

    conn.commit()
```

- [ ] Register the step in the `STEPS` list at the bottom of `migrate_db.py`.

### Step 1.3: Run migration

- [ ] Run:

```bash
python scripts/migrate_db.py
```

- [ ] Verify:

```bash
python -c "
from src.db import get_db
db = get_db()
# Check junction table exists and has data
count = db.execute('SELECT COUNT(*) FROM document_politicians').fetchone()[0]
print(f'Junction rows: {count}')
# Check columns dropped
cols = [r[1] for r in db.execute('PRAGMA table_info(documents)').fetchall()]
assert 'opponent_id' not in cols, 'opponent_id still exists!'
assert 'mention_target_id' not in cols, 'mention_target_id still exists!'
print(f'Columns OK: opponent_id and mention_target_id removed')
# Check roles
for role, cnt in db.execute('SELECT role, COUNT(*) FROM document_politicians GROUP BY role').fetchall():
    print(f'  {role}: {cnt}')
"
```

Expected: ~8500 subject rows, ~500 mention_target rows, columns dropped.

### Step 1.4: Commit

```bash
git add src/db.py scripts/migrate_db.py
git commit -m "feat: add document_politicians junction table and migrate data"
```

---

## Task 2: Core DB Functions (`src/db.py`)

**Files:**
- Modify: `src/db.py:377-438` (`insert_document`), `src/db.py:471-511` (`search_similar`), `src/db.py:672-730` (`delete_politician_data`), `src/db.py:315-330` (migration code)

### Step 2.1: Update `insert_document()`

- [ ] Read `src/db.py` lines 377-438. Replace the function signature and body:

**Change signature from:**
```python
def insert_document(
    content: str,
    opponent_id: Optional[int] = None,
    source_id: Optional[int] = None,
    platform: str = "web",
    language: str = "lv",
    is_auto_caption: bool = False,
    mention_target_id: Optional[int] = None,
    ...
```

**To:**
```python
def insert_document(
    content: str,
    politician_links: Optional[list[tuple[int, str]]] = None,
    source_id: Optional[int] = None,
    platform: str = "web",
    language: str = "lv",
    is_auto_caption: bool = False,
    ...
```

Where `politician_links` is a list of `(politician_id, role)` tuples, e.g. `[(5, 'subject'), (12, 'mention_target')]`.

**Remove the hash hack** (lines 390-393):
```python
# DELETE THIS:
if platform == "x_mention" and mention_target_id:
    content_hash = _compute_content_hash(f"{content}::mention_target::{mention_target_id}")
```

Hash should be purely content-based now.

**Remove `opponent_id` and `mention_target_id` from the INSERT** statement (lines 427-434). The documents INSERT should no longer include these columns.

**After the INSERT, add junction rows:**
```python
    if politician_links:
        for pid, role in politician_links:
            db.execute(
                """INSERT OR IGNORE INTO document_politicians
                   (document_id, politician_id, role) VALUES (?, ?, ?)""",
                (doc_id, pid, role),
            )
```

- [ ] Also add a convenience wrapper to maintain backward compat during migration:

```python
def link_politician_to_document(document_id: int, politician_id: int, role: str = "subject") -> None:
    """Add a politician link to an existing document."""
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role) VALUES (?, ?, ?)",
        (document_id, politician_id, role),
    )
    db.commit()
```

### Step 2.2: Update `search_similar()`

- [ ] Read `src/db.py` lines 471-511. Find the `opponent_id` filter (around lines 497-502).

**Change parameter** from `opponent_id: Optional[int] = None` to `politician_id: Optional[int] = None`.

**Replace the filter logic.** Where it currently does:
```python
if opponent_id is not None:
    results = [r for r in results if r["opponent_id"] == opponent_id]
```

Change to:
```python
if politician_id is not None:
    linked_doc_ids = {
        r[0] for r in db.execute(
            "SELECT document_id FROM document_politicians WHERE politician_id = ?",
            (politician_id,),
        ).fetchall()
    }
    results = [r for r in results if r["id"] in linked_doc_ids]
```

### Step 2.3: Update `delete_politician_data()`

- [ ] Read `src/db.py` lines 672-730. The function currently collects document IDs via:
```python
doc_ids = [r[0] for r in db.execute("SELECT id FROM documents WHERE opponent_id = ?", (pid,)).fetchall()]
```

**Replace with:**
```python
# Get documents exclusively owned by this politician (no other links)
exclusive_doc_ids = [r[0] for r in db.execute("""
    SELECT dp.document_id FROM document_politicians dp
    WHERE dp.politician_id = ?
    AND NOT EXISTS (
        SELECT 1 FROM document_politicians dp2
        WHERE dp2.document_id = dp.document_id
        AND dp2.politician_id != ?
    )
""", (pid, pid)).fetchall()]

# Remove all junction rows for this politician
db.execute("DELETE FROM document_politicians WHERE politician_id = ?", (pid,))
```

Then use `exclusive_doc_ids` for cascading document chunk and document deletes (replacing the old `doc_ids`).

**Also remove** the line `DELETE FROM documents WHERE opponent_id = ?` from the cascade block (around line 719). Replace with:
```python
if exclusive_doc_ids:
    placeholders = ",".join("?" * len(exclusive_doc_ids))
    db.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", exclusive_doc_ids)
```

### Step 2.4: Remove old migration code

- [ ] Read `src/db.py` around lines 315-330. Remove the migration block that adds `mention_target_id`:
```python
# DELETE THIS BLOCK:
if "mention_target_id" not in cols:
    db.execute("ALTER TABLE documents ADD COLUMN mention_target_id INTEGER REFERENCES tracked_politicians(id)")
```

- [ ] Add migration for the junction table in the same area:
```python
# Add document_politicians table if missing (for existing DBs)
db.execute("""
    CREATE TABLE IF NOT EXISTS document_politicians (
        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
        role TEXT NOT NULL DEFAULT 'subject',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (document_id, politician_id, role)
    )
""")
db.execute("CREATE INDEX IF NOT EXISTS idx_dp_politician ON document_politicians(politician_id, role)")
db.execute("CREATE INDEX IF NOT EXISTS idx_dp_document ON document_politicians(document_id)")
```

### Step 2.5: Verify and commit

- [ ] Run: `python -m pytest tests/test_db.py -v` — expect failures (tests still use old API)
- [ ] Commit:

```bash
git add src/db.py
git commit -m "refactor: update db.py core functions for document_politicians junction"
```

---

## Task 3: Update Ingest Pipeline (`src/ingest.py`)

**Files:**
- Modify: `src/ingest.py:820-932` (`match_politician`, `assign_unmatched_documents`), `src/ingest.py:939-956` (`store_content`), `src/ingest.py:1053-1077` (`_ingest_source`)

### Step 3.1: Convert `match_politician()` to `match_politicians()`

- [ ] Read `src/ingest.py` lines 820-903. The function currently returns the single best match.

**Rename** to `match_politicians()` and change return type to `list[tuple[int, str]]` (list of `(politician_id, role)` tuples).

**Logic change:** Instead of returning only the best candidate, return ALL unambiguous candidates:
- First candidate (highest match count) gets `role='subject'`
- Additional candidates get `role='mentioned'`
- Ambiguous surname matches still skipped

```python
def match_politicians(text: str) -> list[tuple[int, str]]:
    """Match text to politicians by name forms. Returns list of (politician_id, role)."""
    forms_list = _load_politician_forms()
    candidates: list[tuple[int, int, bool]] = []  # (pid, count, has_unique)

    for pid, forms, pol_first_name in forms_list:
        matched_forms = [f for f in forms if f in text]
        count = len(matched_forms)
        if count > 0:
            # Keep all existing filtering logic (common words, foreign first names, etc.)
            # ... (preserve lines 844-875 as-is) ...
            has_unique = any(f not in _shared_surname_set for f in matched_forms)
            candidates.append((pid, count, has_unique))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[1], reverse=True)

    results = []
    for pid, count, has_unique in candidates:
        if not has_unique:
            # Try disambiguation for shared surnames
            resolved = _disambiguate_shared_surname(text, [(pid, count, has_unique)])
            if resolved is not None:
                role = "subject" if not results else "mentioned"
                results.append((resolved, role))
            continue
        role = "subject" if not results else "mentioned"
        results.append((pid, role))

    return results
```

- [ ] Keep the old `match_politician()` as a thin wrapper for callers that need single result:

```python
def match_politician(text: str) -> int | None:
    """Legacy wrapper — returns single best match."""
    matches = match_politicians(text)
    return matches[0][0] if matches else None
```

### Step 3.2: Rewrite `assign_unmatched_documents()` → `link_politicians_to_documents()`

- [ ] Read `src/ingest.py` lines 906-932. Replace with:

```python
def link_politicians_to_documents(days: int = 1, rescan_all: bool = False) -> dict[int, list[int]]:
    """Scan documents and link politicians via document_politicians junction.

    If rescan_all=True, scans ALL documents (not just unlinked ones).
    Returns dict of {doc_id: [politician_ids]} for newly linked docs.
    """
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    if rescan_all:
        rows = db.execute(
            "SELECT id, content FROM documents WHERE scraped_at >= ?", (cutoff,)
        ).fetchall()
    else:
        # Documents with no junction rows at all
        rows = db.execute("""
            SELECT d.id, d.content FROM documents d
            LEFT JOIN document_politicians dp ON dp.document_id = d.id
            WHERE dp.document_id IS NULL AND d.scraped_at >= ?
        """, (cutoff,)).fetchall()

    linked: dict[int, list[int]] = {}
    for r in rows:
        matches = match_politicians(r["content"])
        if matches:
            for pid, role in matches:
                db.execute(
                    """INSERT OR IGNORE INTO document_politicians
                       (document_id, politician_id, role) VALUES (?, ?, ?)""",
                    (r["id"], pid, role),
                )
            linked[r["id"]] = [pid for pid, _ in matches]

    db.commit()
    db.close()
    return linked
```

- [ ] Keep `assign_unmatched_documents` as an alias for backward compat if called elsewhere:

```python
def assign_unmatched_documents(days: int = 1) -> dict[int, int]:
    """Legacy wrapper. Returns {doc_id: politician_id} for first match only."""
    result = link_politicians_to_documents(days=days)
    return {doc_id: pids[0] for doc_id, pids in result.items() if pids}
```

### Step 3.3: Update `store_content()` and `_ingest_source()`

- [ ] Read `src/ingest.py` around line 939. Change `store_content()`:

**From:** `opponent_id: int | None` parameter passed to `insert_document(opponent_id=opponent_id)`

**To:** `politician_links: list[tuple[int, str]] | None = None` parameter passed to `insert_document(politician_links=politician_links)`

- [ ] Read `src/ingest.py` around lines 1053-1077. In `_ingest_source()`:

**From:**
```python
matched_pid = match_politician(text)
insert_document(..., opponent_id=matched_pid, ...)
```

**To:**
```python
politician_links = match_politicians(text)
insert_document(..., politician_links=politician_links or None, ...)
```

### Step 3.4: Commit

```bash
git add src/ingest.py
git commit -m "refactor: ingest pipeline uses document_politicians junction"
```

---

## Task 4: Social/Twitter Pipeline (`src/social.py`, `src/x_mentions.py`, `src/x_scraper.py`)

**Files:**
- Modify: `src/social.py:34-46,82,230,298,364-416`
- Modify: `src/x_mentions.py:59-93,162`
- Modify: `src/x_scraper.py:192-208`

### Step 4.1: Update `_store_tweets()` in `social.py`

- [ ] Read `src/social.py` lines 34-46. Change:

**From:**
```python
def _store_tweets(tweets: list, opponent_id: int) -> int:
    ...
    insert_document(..., opponent_id=opponent_id, ...)
```

**To:**
```python
def _store_tweets(tweets: list, politician_id: int) -> int:
    ...
    insert_document(..., politician_links=[(politician_id, "subject")], ...)
```

### Step 4.2: Update all `opponent_id=account["opponent_id"]` calls in social.py

- [ ] Read `src/social.py` lines 75-312. Every place that passes `opponent_id=account["opponent_id"]` to `insert_document()` must change to `politician_links=[(account["opponent_id"], "subject")]`. This applies to lines ~82, ~230, ~298.

- [ ] For `_store_tweets()` calls (line ~82, ~142), change:
```python
_store_tweets(tweets, account["opponent_id"])
```
to:
```python
_store_tweets(tweets, account["opponent_id"])  # _store_tweets internally uses politician_links now
```
(No change needed here since we updated the function itself.)

- [ ] For `log_action()` calls — these use `opponent_id` on the `logs` table which is NOT changing. Leave all `log_action(..., opponent_id=...)` calls as-is.

### Step 4.3: Rewrite x_mention storage loop

- [ ] Read `src/social.py` lines 364-416. This is the critical change. Currently:

```python
for target_pid in mention["mention_target_ids"]:
    insert_document(
        content=...,
        opponent_id=mention.get("opponent_id"),
        mention_target_id=target_pid,
        ...
    )
```

**Replace with single insert:**
```python
# Build politician_links: author as subject, targets as mention_target
politician_links = []
if mention.get("opponent_id"):
    politician_links.append((mention["opponent_id"], "subject"))
for target_pid in mention["mention_target_ids"]:
    politician_links.append((target_pid, "mention_target"))

if politician_links:
    insert_document(
        content=...,
        politician_links=politician_links,
        ...
    )
```

This eliminates the duplication — one document, multiple junction rows.

### Step 4.4: Update `x_scraper.py`

- [ ] Read `src/x_scraper.py` lines 192-208. Change:

```python
opponent_id = account["opponent_id"]
...
results.setdefault(opponent_id, []).extend(all_posts)
```

The `results` dict is consumed by `_store_tweets()` in `social.py`. Since `_store_tweets()` now takes `politician_id` (same value, renamed), no logic change needed — just ensure the calling code passes the right value. If `x_scraper.py` calls `insert_document()` directly, change to use `politician_links`.

### Step 4.5: Verify x_mentions.py needs no code changes

- [ ] Read `src/x_mentions.py` lines 59-93. The `_normalize_mention()` function already returns `mention_target_ids` (plural) and `opponent_id`. These are consumed by `social.py` in the loop we just rewrote. The x_mentions module itself doesn't call `insert_document()`, so it likely needs no changes. Verify by reading the full file.

### Step 4.6: Commit

```bash
git add src/social.py src/x_scraper.py src/x_mentions.py
git commit -m "refactor: social/twitter pipeline uses document_politicians junction"
```

---

## Task 5: Site Generator (`src/generate.py`)

**Files:**
- Modify: `src/generate.py:88,104,120,302-308,847,866,1289-1290,1306-1307`

### Step 5.1: Update politician timeline queries (lines 88, 104, 120)

- [ ] Read `src/generate.py` lines 80-130. These three queries fetch documents for a politician's activity timeline.

**Line 88 — X posts:**
```sql
-- FROM:
SELECT scraped_at, source_url FROM documents WHERE opponent_id = ? AND platform = 'twitter'
-- TO:
SELECT d.scraped_at, d.source_url FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND d.platform IN ('twitter', 'x')
```

**Line 104 — X mentions:**
```sql
-- FROM:
SELECT scraped_at, source_url FROM documents WHERE mention_target_id = ? AND platform = 'x_mention'
-- TO:
SELECT d.scraped_at, d.source_url FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND dp.role = 'mention_target' AND d.platform = 'x_mention'
```

**Line 120 — Web articles:**
```sql
-- FROM:
SELECT scraped_at, source_url, source_domain FROM documents WHERE opponent_id = ? AND platform = 'web'
-- TO:
SELECT d.scraped_at, d.source_url, d.source_domain FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND d.platform = 'web'
```

### Step 5.2: Update homepage recent documents (lines 302-308)

- [ ] Read `src/generate.py` lines 295-315.

**Replace the JOIN:**
```sql
-- FROM:
FROM documents d LEFT JOIN tracked_politicians tp ON d.opponent_id = tp.id
... AND d.opponent_id IS NOT NULL
-- TO:
FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
JOIN tracked_politicians tp ON dp.politician_id = tp.id
```

Note: Changed LEFT JOIN to JOIN since we're filtering for linked docs anyway.

### Step 5.3: Update X feed queries (lines 847, 866)

- [ ] Read `src/generate.py` lines 840-875.

**Line 847 — politician tweets:**
```sql
-- FROM:
JOIN tracked_politicians p ON d.opponent_id = p.id WHERE d.platform IN ('twitter', 'x')
-- TO:
JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
JOIN tracked_politicians p ON dp.politician_id = p.id
WHERE d.platform IN ('twitter', 'x')
```

**Line 866 — x_mentions:**
```sql
-- FROM:
JOIN tracked_politicians p ON d.mention_target_id = p.id WHERE d.platform = 'x_mention'
-- TO:
JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'mention_target'
JOIN tracked_politicians p ON dp.politician_id = p.id
WHERE d.platform = 'x_mention'
```

### Step 5.4: Update filtered document queries (lines 1289-1307)

- [ ] Read `src/generate.py` lines 1285-1310.

**Replace both blocks** (lines 1289-1290 and 1306-1307):
```sql
-- FROM:
JOIN tracked_politicians p ON d.opponent_id = p.id WHERE d.opponent_id IN ({placeholders})
-- TO:
JOIN document_politicians dp ON dp.document_id = d.id
JOIN tracked_politicians p ON dp.politician_id = p.id
WHERE dp.politician_id IN ({placeholders})
```

### Step 5.5: Verify and commit

- [ ] Run: `python -c "from src.generate import generate_public_site; generate_public_site()"`
- [ ] Spot-check `output/politiki/ainars-slesers.html` renders correctly
- [ ] Commit:

```bash
git add src/generate.py
git commit -m "refactor: generate.py queries use document_politicians junction"
```

---

## Task 6: Tools, Analyze, Routine, Saeima, Wiki

**Files:**
- Modify: `src/tools.py:62,146`
- Modify: `src/analyze.py:49,87`
- Modify: `src/routine.py:172-175,185`
- Modify: `src/saeima.py:594`
- Modify: `src/wiki.py:148-159` (add `mentioned_in`)

### Step 6.1: Update `src/tools.py` (2 queries)

- [ ] Read `src/tools.py` lines 58-68. Line 62:
```sql
-- FROM:
WHERE opponent_id = ? AND scraped_at >= ?
-- TO (on documents table, need JOIN):
FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND d.scraped_at >= ?
```

- [ ] Read `src/tools.py` lines 140-150. Line 146:
```sql
-- FROM:
SELECT COUNT(*) FROM documents WHERE opponent_id = ?
-- TO:
SELECT COUNT(DISTINCT dp.document_id) FROM document_politicians dp WHERE dp.politician_id = ?
```

### Step 6.2: Update `src/analyze.py` (2 queries)

- [ ] Read `src/analyze.py` lines 45-55. Line 49:
```sql
-- FROM:
SELECT COUNT(*) FROM documents WHERE opponent_id = ? AND scraped_at >= ? AND scraped_at > ?
-- TO:
SELECT COUNT(*) FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND d.scraped_at >= ? AND d.scraped_at > ?
```

- [ ] Read `src/analyze.py` lines 83-93. Line 87:
```sql
-- FROM:
WHERE opponent_id = ? AND scraped_at >= ?
-- TO:
FROM documents d JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND d.scraped_at >= ?
```

### Step 6.3: Update `src/routine.py` (2 queries)

- [ ] Read `src/routine.py` lines 168-190. Lines 172-175:
```sql
-- FROM:
SELECT DISTINCT d.opponent_id, tp.name
FROM documents d
JOIN tracked_politicians tp ON tp.id = d.opponent_id
WHERE DATE(d.scraped_at) = ? AND d.opponent_id IS NOT NULL
-- TO:
SELECT DISTINCT dp.politician_id AS opponent_id, tp.name
FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id AND dp.role = 'subject'
JOIN tracked_politicians tp ON tp.id = dp.politician_id
WHERE DATE(d.scraped_at) = ?
```

Note: Keep the output column aliased as `opponent_id` if downstream code references `p["opponent_id"]` (line 185).

### Step 6.4: Update `src/saeima.py` (1 call)

- [ ] Read `src/saeima.py` around line 594:
```python
# FROM:
insert_document(..., opponent_id=iv.politician_id, ...)
# TO:
insert_document(..., politician_links=[(iv.politician_id, "subject")], ...)
```

### Step 6.5: Add `mentioned_in` stat to `src/wiki.py`

- [ ] Read `src/wiki.py` lines 148-159 (`_build_person_frontmatter`). After the existing stats, add:

```python
    mentioned_in = db.execute(
        "SELECT COUNT(DISTINCT document_id) FROM document_politicians WHERE politician_id = ?",
        (pid,),
    ).fetchone()[0]
    fm["mentioned_in"] = mentioned_in
```

### Step 6.6: Commit

```bash
git add src/tools.py src/analyze.py src/routine.py src/saeima.py src/wiki.py
git commit -m "refactor: tools/analyze/routine/saeima/wiki use document_politicians junction"
```

---

## Task 7: Update Tests

**Files:**
- Modify: `tests/test_db.py:168-209`
- Modify: `tests/test_analyze.py:33-51`
- Modify: `tests/test_routine.py:27-33,138-148`
- Modify: `tests/test_tools.py:49-77`
- Modify: `tests/test_briefs.py:27-31,66`
- Modify: `tests/test_wiki.py:9-14`

### Step 7.1: Update test DB schemas

- [ ] Every test file that creates a `documents` table in a test fixture must remove `opponent_id` and `mention_target_id` columns and add the `document_politicians` table.

**Pattern to apply in all test files:**

Where tests have:
```sql
CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT, ..., opponent_id INTEGER, ..., mention_target_id INTEGER, ...)
```

Change to:
```sql
CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT, ..., ...)
-- (remove opponent_id and mention_target_id columns)
```

And add:
```sql
CREATE TABLE IF NOT EXISTS document_politicians (
    document_id INTEGER NOT NULL REFERENCES documents(id),
    politician_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'subject',
    PRIMARY KEY (document_id, politician_id, role)
);
```

Where test data inserts use `opponent_id`:
```sql
INSERT INTO documents (..., opponent_id, ...) VALUES (..., 1, ...)
```

Change to insert the document without opponent_id, then add a junction row:
```sql
INSERT INTO documents (...) VALUES (...)
INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')
```

### Step 7.2: Update `tests/test_db.py`

- [ ] Read `tests/test_db.py` lines 160-215. Update `insert_document()` test calls:

```python
# FROM:
insert_document(content="test", opponent_id=None)
# TO:
insert_document(content="test")

# FROM:
insert_document(content="test", opponent_id=5)
# TO:
insert_document(content="test", politician_links=[(5, "subject")])
```

- [ ] Add a test for multi-politician linking:

```python
def test_insert_document_multiple_politicians(db):
    doc_id = insert_document(
        content="Article about A and B",
        politician_links=[(1, "subject"), (2, "mentioned")],
    )
    links = db.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id = ?",
        (doc_id,),
    ).fetchall()
    assert len(links) == 2
    assert (1, "subject") in [(r[0], r[1]) for r in links]
    assert (2, "mentioned") in [(r[0], r[1]) for r in links]
```

### Step 7.3: Update remaining test files

- [ ] Apply the same pattern to `test_analyze.py`, `test_routine.py`, `test_tools.py`, `test_briefs.py`, `test_wiki.py`. Each file that references `opponent_id` on documents needs the schema and insert changes.

Note: `test_models.py` and `test_tools.py` references to `opponent_id` on **claims**, **analyses**, **contradictions**, and **context_notes** do NOT change — only document-level references change.

### Step 7.4: Run full test suite

- [ ] Run:
```bash
python -m pytest tests/ -v
```

- [ ] Fix any remaining failures.

### Step 7.5: Commit

```bash
git add tests/
git commit -m "test: update tests for document_politicians junction table"
```

---

## Task 8: Full Verification

### Step 8.1: Run all verification commands

- [ ] Tests:
```bash
python -m pytest tests/ -v
```

- [ ] Generate site:
```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] Wiki sync:
```bash
python -c "from src.wiki import wiki_sync; print(wiki_sync())"
```

- [ ] Routine check:
```bash
python -c "from src.routine import print_routine; print_routine()"
```

### Step 8.2: Data integrity checks

- [ ] Run:
```python
from src.db import get_db
db = get_db()

# Junction table stats
total = db.execute("SELECT COUNT(*) FROM document_politicians").fetchone()[0]
by_role = db.execute("SELECT role, COUNT(*) FROM document_politicians GROUP BY role").fetchall()
print(f"Total junction rows: {total}")
for role, cnt in by_role:
    print(f"  {role}: {cnt}")

# Verify no orphaned documents (docs with no junction row that should have one)
orphaned = db.execute("""
    SELECT COUNT(*) FROM documents d
    LEFT JOIN document_politicians dp ON dp.document_id = d.id
    WHERE dp.document_id IS NULL AND d.platform != 'web'
""").fetchone()[0]
print(f"Orphaned non-web documents: {orphaned}")

# Verify columns are gone
cols = [r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()]
assert "opponent_id" not in cols
assert "mention_target_id" not in cols
print("Columns verified: opponent_id and mention_target_id removed")

# Verify x_mention dedup worked
x_mention_count = db.execute("SELECT COUNT(*) FROM documents WHERE platform = 'x_mention'").fetchone()[0]
x_mention_targets = db.execute("SELECT COUNT(*) FROM document_politicians WHERE role = 'mention_target'").fetchone()[0]
print(f"x_mention documents: {x_mention_count}, mention_target links: {x_mention_targets}")
```

### Step 8.3: Run `link_politicians_to_documents()` for new politicians

- [ ] Run the full scan to link all politicians to existing documents:

```python
from src.ingest import link_politicians_to_documents
result = link_politicians_to_documents(days=9999, rescan_all=True)
print(f"Linked {len(result)} documents to politicians")
```

### Step 8.4: Regenerate site with new links

- [ ] Run:
```bash
python -c "from src.wiki import wiki_sync; wiki_sync()"
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] Spot-check politician profiles that previously had 0 documents.

### Step 8.5: Final commit

```bash
git add -A
git commit -m "feat: complete document_politicians junction migration

Documents now support multiple politician links via junction table.
x_mention dedup eliminates duplicate documents. New politicians
(Mežals, Elksniņš, Ķirsis, Sprindžuks, Kalniete) linked to
existing documents via text matching."
git push
```
