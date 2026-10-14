# Document-Politicians Junction Table: Full Migration

**Date:** 2026-04-09
**Status:** Draft
**Scope:** Replace `documents.opponent_id` and `documents.mention_target_id` with a many-to-many junction table `document_politicians`.

## Problem

Each document can reference only one politician (`opponent_id`) and one mention target (`mention_target_id`). In practice, news articles frequently mention multiple politicians. This causes:

1. **Lost attribution** — article about Šlesers AND Sprindžuks is assigned to only one
2. **Duplicate documents** — x_mentions system stores the same tweet N times (once per mention target) with a hash hack (`content_hash` includes `mention_target_id`)
3. **Zero-claim politicians** — 14 politicians have 0 claims because documents mentioning them were assigned to someone else
4. **Split model** — `opponent_id` and `mention_target_id` represent the same concept (politician-document link) but live in separate columns with different semantics

## Design

### New Table

```sql
CREATE TABLE document_politicians (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    role TEXT NOT NULL DEFAULT 'subject',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, politician_id, role)
);

CREATE INDEX idx_dp_politician ON document_politicians(politician_id, role);
CREATE INDEX idx_dp_document ON document_politicians(document_id);
```

### Roles

| Role | Meaning | Replaces |
|------|---------|----------|
| `subject` | Document is about/by this politician (their tweet, article about them) | `documents.opponent_id` |
| `mention_target` | Politician is @mentioned in a tweet by someone else | `documents.mention_target_id` |
| `mentioned` | Politician appears in the document text but is not the primary subject | *new capability* |

A single document can have multiple politicians with different roles, or multiple politicians with the same role.

### Columns Removed from `documents`

- `opponent_id` — migrated to `document_politicians` with `role='subject'`
- `mention_target_id` — migrated to `document_politicians` with `role='mention_target'`

### What Does NOT Change

- `claims.opponent_id` — stays 1:1, a claim always belongs to one politician
- `contradictions.opponent_id` — stays 1:1
- `analyses.opponent_id` — stays 1:1
- `context_notes.opponent_id` — stays 1:1
- `social_accounts.opponent_id` — stays 1:1
- `oppo_briefs.opponent_id` — stays 1:1
- `logs.opponent_id` — stays 1:1

The junction table only replaces the document-level politician link. All analytical entities (claims, contradictions, analyses) keep their direct `opponent_id` FK.

## Migration

### Step 1: Create junction table

Add `document_politicians` table to schema in `db.py`.

### Step 2: Populate from existing data

```sql
-- Migrate opponent_id
INSERT INTO document_politicians (document_id, politician_id, role)
SELECT id, opponent_id, 'subject' FROM documents WHERE opponent_id IS NOT NULL;

-- Migrate mention_target_id
INSERT INTO document_politicians (document_id, politician_id, role)
SELECT id, mention_target_id, 'mention_target'
FROM documents WHERE mention_target_id IS NOT NULL;
```

### Step 3: Deduplicate x_mention documents

Currently, the same tweet mentioning 3 politicians is stored as 3 separate documents with different `mention_target_id` values. After migration:

1. Identify duplicates: same `content` + `platform='x_mention'` + same `source_url`
2. Keep one document, merge all `mention_target` junction rows to it
3. Update any `mention_classifications` and `claims` referencing deleted duplicate doc IDs
4. Delete duplicate documents

### Step 4: Drop columns

```sql
ALTER TABLE documents DROP COLUMN opponent_id;
ALTER TABLE documents DROP COLUMN mention_target_id;
```

### Step 5: Remove hash hack

In `insert_document()`, remove the special case where `content_hash` includes `mention_target_id` for x_mention documents. Hash is now purely content-based.

## Code Changes by File

### `src/db.py` (~15 changes)

- **Schema:** Add `document_politicians` table, drop `opponent_id` and `mention_target_id` from documents
- **`insert_document()`**: Replace `opponent_id` and `mention_target_id` params with `politician_links: list[tuple[int, str]]` where each tuple is `(politician_id, role)`. After inserting the document, INSERT into `document_politicians`. Remove hash hack.
- **`search_similar()`**: Replace `WHERE d.opponent_id = ?` filter with `JOIN document_politicians dp ON dp.document_id = d.id WHERE dp.politician_id = ?`
- **`search_similar_claims()`**: No change (uses `claims.opponent_id`)
- **`store_claim()`**: No change (uses `claims.opponent_id`)
- **`store_contradiction()`**: No change
- **`delete_politician_data()`**: Replace `DELETE FROM documents WHERE opponent_id = ?` with: delete from `document_politicians` where `politician_id = ?`, then delete orphaned documents (documents with no remaining junction rows)
- **Migration code**: Remove `mention_target_id` ALTER migration (lines 324-327)
- **Indexes**: Remove `idx_documents_opponent`, `idx_documents_mention_target`. Add new junction indexes.

### `src/ingest.py` (~5 changes)

- **`match_politician()` → `match_politicians()`**: Return `list[int]` instead of `int | None`. Find ALL politicians mentioned in text, not just the best one. Keep disambiguation logic for shared surnames but return all unambiguous matches.
- **`assign_unmatched_documents()`**: Rewrite to scan documents and INSERT into `document_politicians` for each matched politician. Should also scan documents that already have some politician links (to find additional mentions). Rename to `link_politicians_to_documents()`.
- **`store_content()`**: Pass `politician_links` list to `insert_document()`
- **`_ingest_source()`**: Call `match_politicians()` and pass all results

### `src/social.py` (~8 changes)

- **`_store_tweets()`**: Use `insert_document()` with `politician_links=[(opponent_id, 'subject')]`
- **`fetch_twitter()`** and related: Pass politician links through
- **x_mention storage (line ~408-416)**: Instead of looping and creating one document per target, create ONE document with multiple junction entries: `[(author_pid, 'subject'), (target1, 'mention_target'), (target2, 'mention_target')]`

### `src/x_mentions.py` (~3 changes)

- **`_normalize_mention()`**: Already returns `mention_target_ids` (plural). Remove the single-target workaround. Return full list for junction insertion.
- Remove `mention_target_id` references

### `src/x_scraper.py` (~2 changes)

- Pass `politician_links` instead of `opponent_id` to insert_document

### `src/generate.py` (~12 changes)

- **Politician profile page**: Query documents via `JOIN document_politicians` instead of `WHERE opponent_id = ?`. Show all documents where politician appears as subject OR mentioned.
- **Homepage stats**: `COUNT(DISTINCT dp.document_id)` via junction
- **Topic aggregations**: JOIN through junction for document counts
- **Mention/X timeline**: Replace `mention_target_id` queries with junction `WHERE role='mention_target'`
- **Political tensions**: Update JOINs

### `src/tools.py` (~6 changes)

- **`retrieve_context()`**: JOIN via junction to fetch documents for a politician
- **`get_opponent_summary()`**: Document count via junction
- Other functions that query documents by politician

### `src/analyze.py` (~3 changes)

- Document fetching for analysis: JOIN via junction
- Recent document count: via junction

### `src/wiki.py` (~3 changes)

- **`_build_person_frontmatter()`**: Add `mentioned_in` count (documents where politician appears with any role, minus their own subject docs)
- Document-based stats: via junction

### `src/routine.py` (~3 changes)

- Politicians with recent documents: JOIN via junction
- Distinct politician counts: via junction

### `src/briefs.py` (~2 changes)

- Document JOINs for brief generation

### `src/cross_check.py` (~1 change)

- No change expected (works on claims, not documents)

### `src/saeima.py` (~2 changes)

- Pass politician_links to insert_document for voting record documents

### `src/wiki_lint.py` (~1 change)

- Update LEFT JOIN if it references documents.opponent_id

### `src/models.py`

- No change (models reference claims/analyses opponent_id, not documents)

## Helper: Common Query Pattern

Before:
```sql
SELECT d.* FROM documents d WHERE d.opponent_id = ?
```

After:
```sql
SELECT d.* FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ?
```

With role filter:
```sql
SELECT d.* FROM documents d
JOIN document_politicians dp ON dp.document_id = d.id
WHERE dp.politician_id = ? AND dp.role = 'subject'
```

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Junction JOIN performance | Indexes on both columns; 10K docs is tiny for SQLite |
| x_mention dedup breaks references | Migration script updates all FKs before deleting dupes |
| Partial migration leaves inconsistent state | Wrap entire migration in single transaction |
| `match_politicians()` returns too many false positives | Keep existing disambiguation logic; `mentioned` role is lower priority than `subject` |
| Rollback needed | DB backup at `data/atmina_backup_20260409_120904.db`; git state pushed to GitHub at `97f4f2c` |

## Implementation Phases

| Phase | Files | Can Parallelize |
|-------|-------|-----------------|
| 1. Schema + migration script | db.py, scripts/migrate_db.py | No — foundation |
| 2. Core DB functions | db.py | No — depends on phase 1 |
| 3. Ingest pipeline | ingest.py | No — depends on phase 2 |
| 4. Social/Twitter | social.py, x_mentions.py, x_scraper.py | No — depends on phase 2 |
| 5. Analysis + tools | tools.py, analyze.py, briefs.py, cross_check.py | Yes — parallel with phase 6 |
| 6. Generation + wiki | generate.py, wiki.py, wiki_lint.py, routine.py, saeima.py | Yes — parallel with phase 5 |
| 7. Tests + verification | tests/ | No — after all phases |

## Verification

After all phases:
1. `python -m pytest tests/ -v` — all green
2. `python -c "from src.generate import generate_public_site; generate_public_site()"` — generates without errors
3. Spot-check politician profile pages show documents from junction
4. Verify x_mention dedup: count documents with `platform='x_mention'` before vs after
5. `python -c "from src.routine import print_routine; print_routine()"` — routine status OK
