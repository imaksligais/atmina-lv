# Matcher Role Integrity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate systematic `role='subject'` mis-attribution on Twitter documents authored by non-tracked accounts, sweep historical junction rows and claims for existing damage, and add disambiguation for the "Andris Bērziņš" name collision.

**Architecture:** Four sequential phases.
1. **Matcher fix (forward-looking):** in `link_politicians_to_documents()`, compare the URL-derived author handle directly against each candidate politician's registered Twitter handles (from `social_accounts`) instead of relying on the author being a tracked politician. Downgrades `subject → mentioned` whenever the politician is not the URL author, independent of whether the author is tracked.
2. **Junction sweep:** a `scripts/audit_junction_roles.py` script that detects + (with `--apply`) fixes existing `document_politicians` rows where the URL author handle does not match the politician's known handles.
3. **Claim audit:** `scripts/audit_claim_attribution.py` read-only report flagging claims whose `source_url` author does not match the opponent politician's registered handles — output for human review, no auto-delete.
4. **Name-collision disambiguation:** `tracked_politicians.negative_patterns` JSON column — phrases that reject a match when found in the document text. Populate for pid=146 (Andris Bērziņš) to exclude "bijušais Valsts prezidents", "eks-prezidents" etc.

**Tech Stack:** Python 3.11+, SQLite (WAL), pytest, regex URL parsing. No new external dependencies.

**Observed failures (2026-04-19 daily routine):**
- doc=22142 platform=twitter URL=`x.com/KasparsH/...` → Krusts (pid=45) as `subject` — KasparsH not in `social_accounts`
- doc=22146 platform=twitter URL=`x.com/BensLatkovskis/...` → Stendzenieks (pid=60) as `subject` — Latkovskis likely has no `social_accounts` row
- doc=22122 platform=twitter URL=`x.com/deduktors/...` → Krištopans (pid=9) as `subject` — untracked author
- doc=22153 platform=twitter URL=`x.com/3DCADLV/...` → Vītols (pid=64) as `subject` — untracked author
- doc=22118 platform=web la.lv → Andris Bērziņš (pid=146) as `subject` — article cites former President, name-collision with ZZS deputy

**Root-cause confirmation:** `src/ingest.py:1028`
```python
elif url_author_pid is not None and role == "subject" and pid != url_author_pid:
    role = "mentioned"
```
Condition requires `url_author_pid is not None`. `url_author_pid = handle_to_pid.get(url_parts[0].lower())` (line 1015) returns `None` whenever the URL author is not in `social_accounts`, so the downgrade never fires for non-tracked authors.

**Rollback:** Create DB backup at `data/atmina_backup_pre_matcher_fix.db` as Task 1 step 1. Plan touches one function + one column + three new scripts. Reverting = `git revert` + `cp` backup.

---

## File Structure

**Files to modify:**
- `src/ingest.py:992-1039` — replace `handle_to_pid` + `url_author_pid` logic with `pid_to_handles` + `author_handle` comparison; add `extract_twitter_author_handle()` helper
- `src/ingest.py:723-833` — add `_negative_pattern_rejects()` check in `match_politicians()`
- `src/db.py:50-70` — add `negative_patterns TEXT DEFAULT '[]'` column to `tracked_politicians`
- `tests/test_ingest.py` — new regression tests for matcher role assignment + negative patterns

**Files to create:**
- `scripts/audit_junction_roles.py` — report + `--apply` mode for retroactive junction cleanup
- `scripts/audit_claim_attribution.py` — read-only claim attribution report
- `tests/test_audit_junction_roles.py` — tests for the junction audit script
- `tests/test_audit_claim_attribution.py` — tests for the claim audit script

---

## Task 1: DB Backup + Helper `extract_twitter_author_handle()`

**Files:**
- Create: `data/atmina_backup_pre_matcher_fix.db` (one-time backup)
- Modify: `src/ingest.py` (add helper near top of file, after imports)
- Test: `tests/test_ingest.py` (add parametrized test)

- [ ] **Step 1.1: Back up the database**

```bash
cp "data/atmina.db" "data/atmina_backup_pre_matcher_fix.db"
ls -la data/atmina_backup_pre_matcher_fix.db
```

Expected: file listed, size ~same as atmina.db.

- [ ] **Step 1.2: Write the failing test**

In `tests/test_ingest.py`, add a new test block (after existing tests, before any helper defs):

```python
import pytest
from src.ingest import extract_twitter_author_handle


@pytest.mark.parametrize("url,expected", [
    ("https://x.com/KasparsH/status/2045853390337405314", "kasparsh"),
    ("https://x.com/BensLatkovskis/status/2045830485486535043", "benslatkovskis"),
    ("https://twitter.com/guntarsv/status/12345", "guntarsv"),
    ("https://x.com/3DCADLV/status/2045881576060285028", "3dcadlv"),
    ("https://x.com/Braze_Baiba/status/2045782645716537801?s=20", "braze_baiba"),
    ("https://x.com/Braze_Baiba/status/2045782645716537801/", "braze_baiba"),
    # Non-twitter URLs return None
    ("https://www.la.lv/par-partiku-maksasim", None),
    ("", None),
    (None, None),
])
def test_extract_twitter_author_handle(url, expected):
    assert extract_twitter_author_handle(url) == expected
```

- [ ] **Step 1.3: Run test to verify it fails**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py::test_extract_twitter_author_handle -v
```

Expected: `ImportError` — function not yet defined.

- [ ] **Step 1.4: Implement the helper**

In `src/ingest.py`, add this function near the top (after existing imports, before `_politician_forms_cache`):

```python
def extract_twitter_author_handle(source_url: str | None) -> str | None:
    """Parse the author screen_name from an x.com or twitter.com URL.

    Returns the handle in lowercase, or None if the URL is missing,
    not a Twitter/X URL, or malformed. Handles both x.com and
    twitter.com hosts, trailing slashes, and ?query params.

    Examples:
        x.com/KasparsH/status/123     -> "kasparsh"
        twitter.com/guntarsv/status/1 -> "guntarsv"
        x.com/Braze_Baiba/status/1?s=20 -> "braze_baiba"
        la.lv/article                 -> None
    """
    if not source_url:
        return None
    for prefix in ("https://x.com/", "https://twitter.com/", "http://x.com/", "http://twitter.com/"):
        if source_url.startswith(prefix):
            remainder = source_url[len(prefix):]
            handle = remainder.split("/", 1)[0].split("?", 1)[0].strip()
            return handle.lower() if handle else None
    return None
```

- [ ] **Step 1.5: Run test to verify it passes**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py::test_extract_twitter_author_handle -v
```

Expected: all 9 parametrized cases PASS.

- [ ] **Step 1.6: Commit**

```bash
git add tests/test_ingest.py src/ingest.py
git commit -m "feat(matcher): add extract_twitter_author_handle helper"
```

---

## Task 2: Replace `handle_to_pid` with `pid_to_handles` Set-Based Lookup

**Files:**
- Modify: `src/ingest.py:992-1039` (inside `link_politicians_to_documents()`)
- Test: `tests/test_ingest.py` (new regression test suite)

This is the core fix. Instead of asking "is the URL author a tracked politician whose pid we can compare?", ask "does the URL author handle match *this specific candidate politician's* known handles?".

- [ ] **Step 2.1: Re-read the current function body before editing**

Run:
```bash
.venv/Scripts/python.exe -c "print(open('src/ingest.py').read()[30000:32000])"
```

Verify lines 992-1039 match the code block in Step 2.3's `old_string`. (CLAUDE.md EDIT INTEGRITY rule.)

- [ ] **Step 2.2: Write the failing test**

In `tests/test_ingest.py`, add after the existing tests (use the existing fixture DB pattern — inspect `test_ingest.py:1-71` for the `tmp_db` fixture):

```python
def test_link_downgrades_subject_when_author_handle_does_not_match(tmp_db):
    """@KasparsH tweet mentioning Krusts — Krusts should be 'mentioned', not 'subject'."""
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    # Register Krusts with handle "krusts"
    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    # Insert doc authored by @KasparsH that mentions Krusts
    doc_id = insert_document(
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        content="Pensiju 2. līmenis Lietuvā. Komentārs Mārtiņam Krustam par to.",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[],  # no direct links; rely on matcher
    )

    result = link_politicians_to_documents(days=30)

    # The politician should be linked, but NOT as subject
    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchone()
    assert row is not None, "Krusts should be linked to the doc"
    assert row["role"] == "mentioned", f"expected 'mentioned', got '{row['role']}'"


def test_link_keeps_subject_when_author_handle_matches(tmp_db):
    """@krusts own tweet — Krusts should stay as 'subject'."""
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        source_url="https://x.com/krusts/status/2045849970868179440",
        content="Mārtiņš Krusts savas pozīcijas izklāsts par Hormuzu.",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[],
    )

    link_politicians_to_documents(days=30)
    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchone()
    assert row["role"] == "subject"


def test_link_downgrades_even_when_author_is_tracked_non_match(tmp_db):
    """@BensLatkovskis tweet attacking Stendzenieks — Stendzenieks is mentioned, Latkovskis is subject.

    Regression: previous code relied on handle_to_pid lookup, which worked
    only if author was tracked. This test ensures BOTH mechanisms work:
    author is tracked (Latkovskis pid=114) AND is different from the
    mentioned politician (Stendzenieks pid=60).
    """
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (60, 'Ēriks Stendzenieks', '[\"Ēriks Stendzenieks\", \"Stendzenieks\"]')"
    )
    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (114, 'Bens Latkovskis', '[\"Bens Latkovskis\", \"Latkovskis\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (60, 'twitter', 'stendzenieks')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (114, 'twitter', 'benslatkovskis')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        source_url="https://x.com/BensLatkovskis/status/2045830485486535043",
        content="Ēriks Stendzenieks ar Dalniņu ir dvīņi. Komentārs par JV politiku.",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[],
    )

    link_politicians_to_documents(days=30)

    stz_row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=60",
        (doc_id,),
    ).fetchone()
    lat_row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=114",
        (doc_id,),
    ).fetchone()
    assert stz_row["role"] == "mentioned", "Stendzenieks mentioned, not subject"
    assert lat_row["role"] == "subject", "Latkovskis is the author"
```

- [ ] **Step 2.3: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py::test_link_downgrades_subject_when_author_handle_does_not_match tests/test_ingest.py::test_link_keeps_subject_when_author_handle_matches tests/test_ingest.py::test_link_downgrades_even_when_author_is_tracked_non_match -v
```

Expected:
- test_link_downgrades_subject_when_author_handle_does_not_match: **FAIL** (role is "subject" not "mentioned" — the bug)
- test_link_keeps_subject_when_author_handle_matches: likely PASS (coincidental)
- test_link_downgrades_even_when_author_is_tracked_non_match: PASS (existing downgrade logic covers this)

- [ ] **Step 2.4: Replace the `handle_to_pid` + `url_author_pid` logic**

Replace lines 992-1034 of `src/ingest.py`. Use Edit tool with `old_string` covering the exact current block and `new_string` being:

```python
    # Build pid -> set of registered Twitter handles (lowercase).
    # Used to decide whether the URL author of a tweet matches a
    # candidate politician. Set-based lookup means a single politician
    # can have multiple handles (primary + official + historical).
    pid_to_handles: dict[int, set[str]] = {}
    sa_rows = db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall()
    for sa in sa_rows:
        pid_to_handles.setdefault(sa["opponent_id"], set()).add(sa["handle"].lower())

    linked: dict[int, list[int]] = {}
    for r in rows:
        matches = match_politicians(r["content"])
        if matches:
            doc_url = db.execute(
                "SELECT source_url, platform FROM documents WHERE id = ?", (r["id"],)
            ).fetchone()
            platform = doc_url["platform"] if doc_url else None
            source_url = doc_url["source_url"] if doc_url else None

            # For Twitter docs, extract the URL author handle. We compare
            # against each candidate politician's registered handles — no
            # dependency on the author being tracked. This catches tweets
            # by untracked authors (@KasparsH, @deduktors, @3DCADLV) that
            # mention a tracked politician.
            author_handle = (
                extract_twitter_author_handle(source_url)
                if platform == "twitter"
                else None
            )

            for pid, role in matches:
                # x_mention docs always store matches as mention_target. Their
                # author relationship is captured via documents.opponent_id at
                # ingest time (see src/x_mentions.py).
                if platform == "x_mention" and role == "subject":
                    role = "mention_target"
                # Twitter docs: downgrade subject -> mentioned when the URL
                # author handle is not among this politician's registered
                # handles. Applies whether or not the author is tracked.
                elif (
                    platform == "twitter"
                    and role == "subject"
                    and author_handle is not None
                    and author_handle not in pid_to_handles.get(pid, set())
                ):
                    role = "mentioned"
                db.execute(
                    """INSERT OR IGNORE INTO document_politicians
                       (document_id, politician_id, role) VALUES (?, ?, ?)""",
                    (r["id"], pid, role),
                )
            linked[r["id"]] = [pid for pid, _ in matches]
```

- [ ] **Step 2.5: Re-read the edited function to confirm the change applied**

Run:
```bash
.venv/Scripts/python.exe -c "import re; s=open('src/ingest.py').read(); m=re.search(r'pid_to_handles.*?linked\[r\[.id.\]\]', s, re.DOTALL); print(m.group()[:1500] if m else 'NO MATCH')"
```

Expected: prints the new code block starting with `pid_to_handles: dict[int, set[str]]`. (CLAUDE.md EDIT INTEGRITY rule.)

- [ ] **Step 2.6: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py -v
```

Expected: all existing tests still pass + three new tests pass.

- [ ] **Step 2.7: Commit**

```bash
git add src/ingest.py tests/test_ingest.py
git commit -m "fix(matcher): downgrade subject→mentioned when URL author handle does not match politician"
```

---

## Task 3: Add `negative_patterns` Column + Matcher Rejection

**Files:**
- Modify: `src/db.py` (schema add column + migration)
- Modify: `src/ingest.py` (match_politicians: reject when negative pattern hits)
- Test: `tests/test_ingest.py`

- [ ] **Step 3.1: Write the failing test**

In `tests/test_ingest.py`:

```python
def test_match_rejects_when_negative_pattern_present(tmp_db):
    """Andris Bērziņš (ZZS deputy) should NOT match when text references
    former president context."""
    import json
    from src.ingest import match_politicians, _clear_politician_cache

    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, negative_patterns)
           VALUES (146, 'Andris Bērziņš', ?, ?)""",
        (
            json.dumps(["Andris Bērziņš", "Bērziņš"]),
            json.dumps([
                "bijušais Valsts prezidents",
                "bijušais prezidents",
                "eks-prezidents",
                "biedrība \"Latvijas Ceļu būvētājs\"",
                "Latvijas Ceļu būvētājs",
            ]),
        ),
    )
    tmp_db.commit()
    _clear_politician_cache()

    text_about_former_president = (
        "Par pārtiku maksāsim vēl vairāk. Andris Bērziņš, bijušais Valsts "
        "prezidents un biedrības \"Latvijas Ceļu būvētājs\" priekšsēdētājs, "
        "paredz, ka cenas turpinās kāpt."
    )
    matches = match_politicians(text_about_former_president)
    assert matches == [], f"expected empty (rejected), got {matches}"


def test_match_accepts_when_no_negative_pattern(tmp_db):
    """Same politician should match when text is about them (no former-president context)."""
    import json
    from src.ingest import match_politicians, _clear_politician_cache

    tmp_db.execute(
        """INSERT INTO tracked_politicians (id, name, name_forms, negative_patterns)
           VALUES (146, 'Andris Bērziņš', ?, ?)""",
        (
            json.dumps(["Andris Bērziņš", "Bērziņš"]),
            json.dumps(["bijušais Valsts prezidents", "bijušais prezidents"]),
        ),
    )
    tmp_db.commit()
    _clear_politician_cache()

    text_about_zzs_deputy = "ZZS deputāts Andris Bērziņš uzstājās Saeimā par lauksaimniecību."
    matches = match_politicians(text_about_zzs_deputy)
    assert any(pid == 146 for pid, _ in matches), f"expected pid=146 match, got {matches}"
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py::test_match_rejects_when_negative_pattern_present tests/test_ingest.py::test_match_accepts_when_no_negative_pattern -v
```

Expected: both FAIL — column `negative_patterns` doesn't exist.

- [ ] **Step 3.3: Add column to schema**

In `src/db.py`, find the `tracked_politicians` CREATE TABLE block (around line 50). Add a new column before the closing `)`:

```sql
    negative_patterns TEXT DEFAULT '[]',
```

Also add a migration step in the `_migrate` function (or wherever columns get added to existing DBs). Look for existing migration pattern — if `_migrate_tracked_politicians()` or similar exists, add:

```python
def _ensure_negative_patterns_column(db):
    """2026-04-19: add negative_patterns column for name-collision rejection."""
    cols = {r["name"] for r in db.execute("PRAGMA table_info(tracked_politicians)").fetchall()}
    if "negative_patterns" not in cols:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN negative_patterns TEXT DEFAULT '[]'")
        db.commit()
```

Call it from `_init_db()` after the create-table phase.

- [ ] **Step 3.4: Expose `_clear_politician_cache()` for tests**

In `src/ingest.py`, near `_politician_forms_cache`, add:

```python
def _clear_politician_cache() -> None:
    """Testing hook. Do not call from production code."""
    global _politician_forms_cache, _shared_surname_set
    _politician_forms_cache = None
    _shared_surname_set = None
```

(Only add if these globals are used for caching. Adjust to match the actual caching in your file.)

- [ ] **Step 3.5: Load negative patterns + wire them into match_politicians()**

Find `_load_politician_forms()` in `src/ingest.py:723-771`. Extend it to also load negative patterns:

```python
# Replace existing tuple (pid, forms, first_name) with (pid, forms, first_name, negative_patterns)
rows = db.execute(
    "SELECT id, name, name_forms, negative_patterns FROM tracked_politicians WHERE relationship_type != 'inactive' OR relationship_type IS NULL"
).fetchall()
```

Then in the forms list comprehension, also parse `row["negative_patterns"]` as JSON and store alongside forms. Update the cache tuple structure and all readers.

In `match_politicians(text)` around line 855-948, after a candidate politician is matched but before appending to `matches`, check negative patterns:

```python
# If any negative pattern hits in the text, reject this match.
# Used for name-collision disambiguation (e.g. Andris Bērziņš ZZS
# deputy vs. former president).
if neg_patterns and any(p in text for p in neg_patterns):
    continue
```

- [ ] **Step 3.6: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_ingest.py -v
```

Expected: all tests pass including the two new ones.

- [ ] **Step 3.7: Populate pid=146 negative patterns in the real DB**

Run:
```bash
.venv/Scripts/python.exe -c "
from src.db import get_db
import json
db = get_db()
db.execute(
    'UPDATE tracked_politicians SET negative_patterns = ? WHERE id = 146',
    (json.dumps([
        'bijušais Valsts prezidents',
        'bijušais prezidents',
        'eks-prezidents',
        'biedrības \"Latvijas Ceļu būvētājs\"',
        'biedrība Latvijas Ceļu būvētājs',
        'Latvijas Ceļu būvētāji',
    ]),)
)
db.commit()
db.close()
print('OK')
"
```

- [ ] **Step 3.8: Commit**

```bash
git add src/db.py src/ingest.py tests/test_ingest.py
git commit -m "feat(matcher): negative_patterns column for name-collision rejection"
```

---

## Task 4: Junction Audit Script — Dry-Run Report

**Files:**
- Create: `scripts/audit_junction_roles.py`
- Create: `tests/test_audit_junction_roles.py`

- [ ] **Step 4.1: Write the failing test**

Create `tests/test_audit_junction_roles.py`:

```python
import pytest
from src.db import get_db, insert_document


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated DB per test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("ATMINA_DB_PATH", str(db_path))
    db = get_db()
    yield db
    db.close()


def test_audit_finds_mismatched_subject_rows(tmp_db):
    """A (doc, politician, subject) row where URL author != politician handles should be flagged."""
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    doc_id = insert_document(
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        content="Some content about Krusts.",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[(45, "subject")],
    )
    tmp_db.commit()

    mismatches = find_mismatched_rows(tmp_db)
    assert len(mismatches) == 1
    assert mismatches[0]["document_id"] == doc_id
    assert mismatches[0]["politician_id"] == 45
    assert mismatches[0]["current_role"] == "subject"
    assert mismatches[0]["proposed_role"] == "mentioned"
    assert mismatches[0]["url_author"] == "kasparsh"
    assert "krusts" in mismatches[0]["politician_handles"]


def test_audit_ignores_correctly_attributed_rows(tmp_db):
    """A (doc, politician, subject) row where URL author IS a politician handle should not be flagged."""
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    insert_document(
        source_url="https://x.com/krusts/status/12345",
        content="Own tweet.",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[(45, "subject")],
    )
    tmp_db.commit()

    mismatches = find_mismatched_rows(tmp_db)
    assert mismatches == []


def test_audit_ignores_non_twitter_platforms(tmp_db):
    """Web articles need separate handling; junction sweep only touches twitter."""
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (146, 'Andris Bērziņš', '[]')"
    )
    insert_document(
        source_url="https://www.la.lv/par-partiku-maksasim",
        content="Par bijušo prezidentu.",
        title="La.lv raksts",
        platform="web",
        language="lv",
        politician_links=[(146, "subject")],
    )
    tmp_db.commit()

    mismatches = find_mismatched_rows(tmp_db)
    assert mismatches == []


def test_audit_flags_x_mention_subject_as_mention_target(tmp_db):
    """x_mention docs with role='subject' should be flagged and proposed as 'mention_target'."""
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (60, 'Ēriks Stendzenieks', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (60, 'twitter', 'stendzenieks')"
    )
    insert_document(
        source_url="https://x.com/BensLatkovskis/status/2045830485486535043",
        content="Attack on Stendzenieks.",
        title=None,
        platform="x_mention",
        language="lv",
        politician_links=[(60, "subject")],
    )
    tmp_db.commit()

    mismatches = find_mismatched_rows(tmp_db)
    assert len(mismatches) == 1
    assert mismatches[0]["proposed_role"] == "mention_target"
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_audit_junction_roles.py -v
```

Expected: all fail with ImportError for `scripts.audit_junction_roles`.

- [ ] **Step 4.3: Implement the audit module**

Create `scripts/audit_junction_roles.py`:

```python
"""Audit document_politicians junction for role='subject' rows where the
URL author does not match the politician's registered handles.

Usage:
    python scripts/audit_junction_roles.py             # dry-run report (CSV to stdout)
    python scripts/audit_junction_roles.py --apply     # apply fixes
    python scripts/audit_junction_roles.py --limit 100 # first 100 rows only
"""

from __future__ import annotations

import argparse
import csv
import sys
from typing import Any

from src.db import get_db
from src.ingest import extract_twitter_author_handle


def _load_pid_to_handles(db) -> dict[int, set[str]]:
    m: dict[int, set[str]] = {}
    for row in db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall():
        m.setdefault(row["opponent_id"], set()).add(row["handle"].lower())
    return m


def find_mismatched_rows(db, limit: int | None = None) -> list[dict[str, Any]]:
    """Return list of junction rows whose role='subject' does not match URL author."""
    pid_to_handles = _load_pid_to_handles(db)

    query = """
        SELECT dp.document_id, dp.politician_id, dp.role, d.platform, d.source_url,
               tp.name AS politician_name
        FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        JOIN tracked_politicians tp ON tp.id = dp.politician_id
        WHERE dp.role = 'subject'
          AND d.platform IN ('twitter', 'x_mention')
        ORDER BY dp.document_id DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    results: list[dict[str, Any]] = []
    for row in db.execute(query).fetchall():
        platform = row["platform"]
        proposed_role: str | None = None

        if platform == "x_mention":
            # x_mention subject is always wrong — should be mention_target
            proposed_role = "mention_target"
        elif platform == "twitter":
            author_handle = extract_twitter_author_handle(row["source_url"])
            if author_handle is None:
                continue  # can't parse URL, skip
            pol_handles = pid_to_handles.get(row["politician_id"], set())
            if author_handle not in pol_handles:
                proposed_role = "mentioned"

        if proposed_role:
            results.append({
                "document_id": row["document_id"],
                "politician_id": row["politician_id"],
                "politician_name": row["politician_name"],
                "platform": platform,
                "source_url": row["source_url"],
                "url_author": extract_twitter_author_handle(row["source_url"]) or "",
                "politician_handles": ",".join(sorted(pid_to_handles.get(row["politician_id"], set()))),
                "current_role": row["role"],
                "proposed_role": proposed_role,
            })

    return results


def apply_fixes(db, mismatches: list[dict[str, Any]]) -> int:
    """Apply proposed role changes. Uses INSERT OR IGNORE + DELETE to respect PK."""
    count = 0
    for m in mismatches:
        # Insert new role (idempotent via PK)
        db.execute(
            """INSERT OR IGNORE INTO document_politicians
               (document_id, politician_id, role) VALUES (?, ?, ?)""",
            (m["document_id"], m["politician_id"], m["proposed_role"]),
        )
        # Delete the old subject row
        db.execute(
            """DELETE FROM document_politicians
               WHERE document_id=? AND politician_id=? AND role='subject'""",
            (m["document_id"], m["politician_id"]),
        )
        count += 1
    db.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="apply fixes (default: dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="limit rows scanned")
    args = parser.parse_args()

    db = get_db()
    mismatches = find_mismatched_rows(db, limit=args.limit)

    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "document_id", "politician_id", "politician_name", "platform",
        "source_url", "url_author", "politician_handles",
        "current_role", "proposed_role",
    ])
    writer.writeheader()
    for m in mismatches:
        writer.writerow(m)

    sys.stderr.write(f"\n{len(mismatches)} mismatches found.\n")

    if args.apply:
        if not mismatches:
            sys.stderr.write("Nothing to apply.\n")
            return
        sys.stderr.write("Applying fixes...\n")
        n = apply_fixes(db, mismatches)
        sys.stderr.write(f"Updated {n} rows.\n")

    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_audit_junction_roles.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 4.5: Run dry-run against real DB, inspect output**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_junction_roles.py --limit 50 2>&1 | head -30
```

Expected: CSV of up to 50 mismatched rows. Eyeball-verify that the 5 known failures (docs 22142, 22146, 22122, 22153, plus any similar) appear in the output.

- [ ] **Step 4.6: Commit**

```bash
git add scripts/audit_junction_roles.py tests/test_audit_junction_roles.py
git commit -m "feat(scripts): audit_junction_roles — detect mis-attributed subject rows"
```

---

## Task 5: Junction Audit Script — Apply Mode Integration Test + Full Sweep

**Files:**
- Modify: `tests/test_audit_junction_roles.py` (add apply-mode test)
- Execute: full DB sweep

- [ ] **Step 5.1: Write the apply-mode test**

Append to `tests/test_audit_junction_roles.py`:

```python
def test_apply_fixes_replaces_subject_with_proposed_role(tmp_db):
    from scripts.audit_junction_roles import find_mismatched_rows, apply_fixes

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    doc_id = insert_document(
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        content="mention of Krusts",
        title=None,
        platform="twitter",
        language="lv",
        politician_links=[(45, "subject")],
    )
    tmp_db.commit()

    mismatches = find_mismatched_rows(tmp_db)
    n = apply_fixes(tmp_db, mismatches)
    assert n == 1

    rows = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchall()
    roles = {r["role"] for r in rows}
    assert roles == {"mentioned"}, f"expected {{mentioned}}, got {roles}"
```

- [ ] **Step 5.2: Run tests to verify all pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_audit_junction_roles.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5.3: Generate dry-run report against production DB**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_junction_roles.py > /tmp/junction_audit_report.csv 2> /tmp/junction_audit_summary.txt
cat /tmp/junction_audit_summary.txt
wc -l /tmp/junction_audit_report.csv
```

Expected: N mismatches reported. Review the CSV manually — look at 10 random rows, confirm the diagnosis is correct.

- [ ] **Step 5.4: HUMAN CHECKPOINT — review report before applying**

Stop. The implementer must present the report to the user and get explicit approval before running with `--apply`. This is a destructive DB migration; dry-run results should be sanity-checked against known good cases (e.g. Braže's own tweets should NOT appear — she IS the author; Krusts in @KasparsH tweet SHOULD appear).

- [ ] **Step 5.5: Apply (ONLY after user approval)**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_junction_roles.py --apply
```

- [ ] **Step 5.6: Re-run the routine's generate step to refresh the site**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 5.7: Commit**

```bash
git add tests/test_audit_junction_roles.py
git commit -m "test(scripts): audit_junction_roles apply-mode test"
```

(No source changes to commit from this task — the sweep ran against the DB.)

---

## Task 6: Claim Attribution Audit Script

**Files:**
- Create: `scripts/audit_claim_attribution.py`
- Create: `tests/test_audit_claim_attribution.py`

This is **read-only**. It does NOT auto-delete claims — output is a CSV for human review, because claims may have already informed downstream analysis/wiki pages.

- [ ] **Step 6.1: Write the failing test**

Create `tests/test_audit_claim_attribution.py`:

```python
import pytest
from src.db import get_db, insert_document


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("ATMINA_DB_PATH", str(db_path))
    db = get_db()
    yield db
    db.close()


def test_audit_flags_claim_with_mismatched_author(tmp_db):
    """A claim on a tweet whose URL author is not the opponent's handle → flagged."""
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.execute("""
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (45, 'Degviela', 'Test stance', 'test quote', 0.8, 0.5,
                'https://x.com/KasparsH/status/2045853390337405314',
                '2026-04-18', 'position')
    """)
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert len(suspects) == 1
    assert suspects[0]["opponent_id"] == 45
    assert suspects[0]["url_author"] == "kasparsh"


def test_audit_ignores_claim_on_own_tweet(tmp_db):
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.execute("""
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (45, 'Degviela', 'Own stance', 'own quote', 0.8, 0.5,
                'https://x.com/krusts/status/12345',
                '2026-04-18', 'position')
    """)
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []


def test_audit_skips_non_twitter_sources(tmp_db):
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (146, 'Andris Bērziņš', '[]')"
    )
    tmp_db.execute("""
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (146, 'Ekonomika', 'stance', 'quote', 0.7, 0.5,
                'https://www.la.lv/par-partiku', '2026-04-18', 'position')
    """)
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []


def test_audit_skips_saeima_claims(tmp_db):
    """saeima_vote claims use a different URL scheme, skip."""
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (9, 'Krištopans', '[]')"
    )
    tmp_db.execute("""
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (9, 'Vēlēšanas', 'voted yes', NULL, 1.0, 0.5,
                'https://titania.saeima.lv/...', '2026-04-18', 'saeima_vote')
    """)
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []
```

- [ ] **Step 6.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_audit_claim_attribution.py -v
```

Expected: ImportError.

- [ ] **Step 6.3: Implement the audit module**

Create `scripts/audit_claim_attribution.py`:

```python
"""Audit claims whose source_url author does not match the opponent politician's handles.

Read-only. Output is a CSV for human review.

Usage:
    python scripts/audit_claim_attribution.py > /tmp/claim_audit.csv
"""

from __future__ import annotations

import csv
import sys
from typing import Any

from src.db import get_db
from src.ingest import extract_twitter_author_handle


def _load_pid_to_handles(db) -> dict[int, set[str]]:
    m: dict[int, set[str]] = {}
    for row in db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall():
        m.setdefault(row["opponent_id"], set()).add(row["handle"].lower())
    return m


def find_suspect_claims(db) -> list[dict[str, Any]]:
    """Return list of claims whose Twitter source_url author ≠ opponent handles."""
    pid_to_handles = _load_pid_to_handles(db)

    rows = db.execute("""
        SELECT c.id, c.opponent_id, tp.name AS opponent_name, c.topic,
               c.stance, c.source_url, c.stated_at, c.created_at, c.claim_type
        FROM claims c
        JOIN tracked_politicians tp ON tp.id = c.opponent_id
        WHERE c.claim_type = 'position'
          AND (c.source_url LIKE 'https://x.com/%' OR c.source_url LIKE 'https://twitter.com/%')
        ORDER BY c.id DESC
    """).fetchall()

    suspects: list[dict[str, Any]] = []
    for row in rows:
        author_handle = extract_twitter_author_handle(row["source_url"])
        if author_handle is None:
            continue
        pol_handles = pid_to_handles.get(row["opponent_id"], set())
        if not pol_handles:
            # Can't verify — politician has no registered Twitter handle
            suspects.append({
                "claim_id": row["id"],
                "opponent_id": row["opponent_id"],
                "opponent_name": row["opponent_name"],
                "topic": row["topic"],
                "stance": (row["stance"] or "")[:200],
                "url_author": author_handle,
                "politician_handles": "",
                "verdict": "unverifiable",
                "source_url": row["source_url"],
                "created_at": row["created_at"],
            })
            continue
        if author_handle not in pol_handles:
            suspects.append({
                "claim_id": row["id"],
                "opponent_id": row["opponent_id"],
                "opponent_name": row["opponent_name"],
                "topic": row["topic"],
                "stance": (row["stance"] or "")[:200],
                "url_author": author_handle,
                "politician_handles": ",".join(sorted(pol_handles)),
                "verdict": "mismatch",
                "source_url": row["source_url"],
                "created_at": row["created_at"],
            })

    return suspects


def main():
    db = get_db()
    suspects = find_suspect_claims(db)
    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "claim_id", "opponent_id", "opponent_name", "topic", "stance",
        "url_author", "politician_handles", "verdict", "source_url", "created_at",
    ])
    writer.writeheader()
    for s in suspects:
        writer.writerow(s)
    sys.stderr.write(f"\n{len(suspects)} suspect claims ({sum(1 for s in suspects if s['verdict']=='mismatch')} mismatches, {sum(1 for s in suspects if s['verdict']=='unverifiable')} unverifiable).\n")
    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6.4: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_audit_claim_attribution.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 6.5: Generate report against production DB**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_claim_attribution.py > /tmp/claim_audit.csv 2> /tmp/claim_audit_summary.txt
cat /tmp/claim_audit_summary.txt
head -20 /tmp/claim_audit.csv
```

- [ ] **Step 6.6: Commit**

```bash
git add scripts/audit_claim_attribution.py tests/test_audit_claim_attribution.py
git commit -m "feat(scripts): audit_claim_attribution — flag mis-attributed claims for human review"
```

---

## Task 7: Full Test Suite + Verification

- [ ] **Step 7.1: Run full test suite**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

Expected: ALL tests pass. If any pre-existing test regresses, stop and diagnose — do NOT layer fixes.

- [ ] **Step 7.2: Run type-checker (if configured)**

Run:
```bash
.venv/Scripts/python.exe -m mypy src/ingest.py scripts/audit_junction_roles.py scripts/audit_claim_attribution.py 2>&1 | tail -20 || echo "mypy not configured"
```

Expected: either passes cleanly or mypy is not configured. Do not add mypy if not already in use.

- [ ] **Step 7.3: Re-read `src/ingest.py:992-1055` to confirm final state**

Run:
```bash
.venv/Scripts/python.exe -c "s=open('src/ingest.py').read().split('\n'); print('\n'.join(s[990:1060]))"
```

Manually verify: `pid_to_handles`, `extract_twitter_author_handle`, `author_handle not in pid_to_handles.get(pid, set())` are all present.

- [ ] **Step 7.4: Manual spot-check with real failing docs**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
from src.db import get_db
db = get_db()
for doc_id in [22142, 22146, 22122, 22153, 22118]:
    rows = db.execute('SELECT dp.politician_id, tp.name, dp.role FROM document_politicians dp JOIN tracked_politicians tp ON tp.id=dp.politician_id WHERE dp.document_id=?', (doc_id,)).fetchall()
    print(f'doc={doc_id}:')
    for r in rows:
        print(f'    pid={r[\"politician_id\"]} {r[\"name\"]} role={r[\"role\"]}')
"
```

Expected (after `--apply` in Task 5.5 + `negative_patterns` update):
- doc=22142 Krusts role=mentioned
- doc=22146 Stendzenieks role=mentioned (or mention_target if platform=x_mention)
- doc=22122 Krištopans role=mentioned
- doc=22153 Vītols role=mentioned
- doc=22118 Andris Bērziņš: junction row may still exist (`negative_patterns` only affects future matches, not historical links). Document a manual `DELETE` if operator wants to remove it.

- [ ] **Step 7.5: Final commit — bookkeeping**

```bash
git add -A
git status  # verify nothing unexpected
git commit -m "chore(matcher): post-sweep verification notes" --allow-empty
```

---

## Self-Review Checklist

Run through before declaring done:

- **Spec coverage:**
  - [x] Task 1: URL author extraction helper — `extract_twitter_author_handle`
  - [x] Task 2: Matcher role fix — `pid_to_handles` + `author_handle` comparison
  - [x] Task 3: Negative patterns for name collision — `negative_patterns` column + `match_politicians()` rejection
  - [x] Task 4-5: Junction sweep script (dry-run + apply)
  - [x] Task 6: Claim audit script (read-only)
  - [x] Task 7: Full verification

- **Placeholders:** none — every step has exact code.

- **Type consistency:** `extract_twitter_author_handle` returns `str | None` consistently. `pid_to_handles: dict[int, set[str]]` consistently. `find_mismatched_rows` / `find_suspect_claims` both return `list[dict[str, Any]]`.

- **Risk gates:**
  - Task 1 Step 1.1: DB backup before any schema or data change.
  - Task 5 Step 5.4: **HUMAN CHECKPOINT** before `--apply`. Do not skip.
  - Task 6: Claim audit is read-only by design — no auto-delete. Human reviews the CSV and decides.

- **Known follow-ups (explicitly out of scope):**
  - Bērziņš historical junction row (doc=22118) is NOT auto-deleted by negative patterns. If operator wants to remove it, manual `DELETE FROM document_politicians WHERE document_id=22118 AND politician_id=146;` + `DELETE FROM claims WHERE id = X;` if any claim was extracted. The audit scripts will surface these.
  - Consider migrating `social_accounts.handle` to case-normalized storage (stored lowercase). Current code `.lower()`s on read which works but is fragile. Track as separate task.
  - Consider adding `relationship_type='historical_figure'` entries for former presidents / premieres to give name-collision a positive match target instead of just a negative rejection.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-19-matcher-role-integrity.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute in this session using executing-plans, batch execution with checkpoints.

Which approach?
