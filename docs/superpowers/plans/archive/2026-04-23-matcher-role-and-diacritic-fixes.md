# Matcher Role Integrity + Diacritic Validator Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs discovered during the 2026-04-23 daily routine diagnostic: (1) `_store_tweets` hardcodes `role='subject'` on every twitter fetch, polluting junction table when twikit surfaces retweets/quote-tweets/replies authored by other handles; (2) `validate_lv_diacritics` rejects short English tweet quotes as "stripped Latvian" because its token-matcher sees Latvian stopword `to` twice without matching counter-signal, blocking legitimate English-quote extractions.

**Architecture:** Two independent small patches landing together.

**Patch 1 (matcher, `src/social.py`):** Resolve the politician's registered twitter handles once at the top of `_store_tweets`, then for each tweet compare `extract_twitter_author_handle(source_url)` (helper already exists at `src/ingest.py:31`) against that set. Match → `role='subject'`, mismatch or unresolvable → `role='mentioned'`. This mirrors exactly the 2026-04-20 fix pattern that landed on the post-hoc scanner path (`src/ingest.py::link_politicians_to_documents`) but was never applied to the live-fetch path. Plus a one-shot idempotent backfill script for 83 existing mismatched rows.

**Patch 2 (diacritic, `src/quality.py`):** Add a fasttext-based early-exit at the top of `validate_lv_diacritics` — if `_detect_language` classifies text as a common non-LV language with ≥0.70 confidence, return `(True, "non-Latvian per fasttext")` immediately. Belt-and-suspenders: extend `EN_MARKERS` with ~30 common tokens the existing set misses (`at`, `more`, `already`, `six`, `times`, `remain`, `fall`, `every`, `continues`, etc.). Critically: stripped Latvian (`"Daudz tiek runats..."`) is classified by fasttext as low-confidence `fr`/`sr`/`hr` — the guardrail's primary use case — so it does NOT early-exit and falls through to the token matcher unchanged. Also add `logging.warning()` on every rejection so future false-positives leave an audit trail (currently zero observability — the `ValueError` raises at the caller site with no log line).

**Tech Stack:** Python 3.11, pytest, SQLite, existing fasttext dependency (model already downloaded at ingest time), existing `extract_twitter_author_handle` helper.

**Files touched (6 total):**
- Modify: `src/social.py` — `_store_tweets` role logic rewrite (~15 LOC net)
- Modify: `src/quality.py` — fasttext early-exit + EN_MARKERS expansion + logging.warning
- Modify: `tests/test_social.py` — 3 new tests for role assignment
- Modify: `tests/test_quality.py` — 4 new tests (English passes, stripped-LV still rejected, Russian passes, genuine-LV baseline unchanged)
- Create: `scripts/fix_subject_role_leakage.py` — one-shot idempotent backfill for 83 junction rows
- Modify: `wiki/CHANGELOG.md` — document both fixes

**Branch:** `fix/matcher-and-diacritic-2026-04-23`, created from current HEAD (`cc10664` on `feat/komentetaji-speaker-id`). The fixes logically stand alone but the branch base already has today's Komentētāji changes deployed to the DB — branching from elsewhere would fight the live data state. The merge target can still be master (cherry-pickable if needed) since neither patch touches Komentētāji files.

**Out of scope (deferred follow-ups):**
- Running `match_politicians(text)` inside `_store_tweets` to enrich `role='mentioned'` junction rows for OTHER tracked politicians named in tweets (nice-to-have enrichment, orthogonal to the regression).
- Separate `language='en'` opt-in kwarg on `store_claim` for agents that already know the quote is English (eliminates the heuristic entirely; defer until we see fasttext misses).
- `published_at` backfill for 55% NULL web docs (documented in Issue 3 diagnostic; independent of these two patches).
- Zīle-style "quiet user" label in `print_routine()` dashboard (Issue 4 diagnostic; UX polish, not a bug).
- Claim audit after backfill — extending 2026-04-20 sweep to delete any claims extracted from mis-tagged junction rows. Task 3 adds audit REPORTING only; deletion decisions stay manual.

**Spec decisions locked in (no re-deliberation mid-implementation):**
- Role mismatch default is `'mentioned'` (not `'subject'`, not skip). Rationale: (a) the politician IS mentioned by virtue of the tweet surfacing on their timeline (retweet/quote/reply-thread presence), (b) `mentioned` docs don't flow into `get_politician_documents(role='subject')` extractor queue, so no spurious claim-extraction, (c) consistent with `feedback_claim_extractor_indirect.md` memory — retrospective references aren't first-party.
- Backfill uses UPDATE (not DELETE). Rationale: downgrading role to `'mentioned'` preserves the linkage metadata; deletion would lose the "KlucisD was tagged here" evidence the mentions-monitor relies on.
- Backfill is idempotent by construction (`WHERE role='subject' AND handle_mismatch` — re-runs do nothing after first pass).
- fasttext early-exit threshold is `conf >= 0.70`. Rationale: subagent's empirical test shows stripped LV misclassifies at `fr 0.37` or `sr 0.42` — well under 0.70, preserving guardrail. Genuine English tweets score `en 0.85+` — clear pass. Mixed LV+EN with LV majority scores `lv 0.5-0.8` — falls through to existing ratio check (genuine LV with diacritics passes).
- fasttext failure (model download error, import error) is non-fatal: `try/except Exception: pass` and fall through to token matcher — matches existing `_get_ft_model` pattern at `src/ingest.py:50-67`.
- `logging.warning` message format: `"validate_lv_diacritics rejected: %s — text[:80]=%r"` — short, structured, without PII leakage (80-char prefix sufficient for triage).
- EN_MARKERS expansion does NOT remove any existing entries; only additions. Rationale: zero risk of regressing the stripped-LV-detection gate that already works.
- LV_STOPWORDS stays unchanged. Rationale: `to`/`no` are legitimate Latvian pronoun forms and removing them would weaken stripped-LV detection for Latvian text that happens to use them.

---

## Task 0: Branch setup

**Files:** _none_

- [ ] **Step 1: Verify current state**

Run: `git status --short && git log -1 --format='%h %s'`

Expected: pre-existing untracked files (`docs/superpowers/plans/...`, `tmp_*.md`) but no staged or unstaged changes in `src/`, `tests/`, `scripts/`, or `wiki/`. HEAD should be `cc10664 docs(wiki): document speaker_id + commentator architecture`.

If unexpected modifications exist in those directories, stop and ask the user.

- [ ] **Step 2: Create branch**

Run:
```bash
git checkout -b fix/matcher-and-diacritic-2026-04-23
```

Expected: `Switched to a new branch 'fix/matcher-and-diacritic-2026-04-23'`.

- [ ] **Step 3: Verify**

Run: `git branch --show-current`

Expected: `fix/matcher-and-diacritic-2026-04-23`

No commit at this step.

---

## Task 1: `_store_tweets` role fix (TDD)

**Files:**
- Modify: `src/social.py:30-56` — replace hardcoded role with handle-match logic
- Test: `tests/test_social.py` — append 3 new tests

- [ ] **Step 1: Inspect existing test file structure**

Run: `ls tests/ | grep -i social`

If `tests/test_social.py` exists, append tests there. If not, the file needs to be created. Read the first 30 lines of any existing `tests/test_*.py` to match the project's test scaffolding (imports, fixtures, UTF-8 handling, tmp_path patterns).

- [ ] **Step 2: Write failing tests**

Append to `tests/test_social.py` (create file if missing, mirror scaffolding from `tests/test_db.py`):

```python
import sqlite3
import pytest


def _setup_social_db(db_path: str) -> None:
    """Helper: init schema + seed one tracked politician with one twitter handle."""
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type, x_handle) "
        "VALUES (1, 'Testa Politiķis', 'tracked', 'TestaPolitikis')"
    )
    db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active) "
        "VALUES (1, 'twitter', 'TestaPolitikis', 1)"
    )
    db.commit()
    db.close()


def test_store_tweets_assigns_subject_when_author_matches(tmp_path, monkeypatch):
    """Tweet whose source_url author is the politician's registered handle → role='subject'."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.db.DB_PATH", db_path)
    _setup_social_db(db_path)

    from src.social import _store_tweets
    tweets = [{
        "text": "Šodien parlamentā runāju par budžeta grozījumiem — atbalsta veselības sektoram. " * 2,
        "source_url": "https://x.com/TestaPolitikis/status/1234567890",
        "created_at": "2026-04-23T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    from src.db import get_db
    db = get_db(db_path)
    role = db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    assert role is not None, "expected a document_politicians row to be created"
    assert role["role"] == "subject"
    db.close()


def test_store_tweets_assigns_mentioned_when_author_differs(tmp_path, monkeypatch):
    """Tweet surfaced via politician's timeline but authored by another handle
    (retweet, quote-tweet, reply thread) → role='mentioned'. This is the
    regression fix for 2026-04-23 — previously every such tweet was incorrectly
    tagged 'subject' in _store_tweets.
    """
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.db.DB_PATH", db_path)
    _setup_social_db(db_path)

    from src.social import _store_tweets
    tweets = [{
        # Content is from @OtherAuthor, surfaced via @TestaPolitikis's timeline
        "text": "Rīgas domes priekšsēdētājs ziņo par jauno iepirkumu — pilsētas budžets palielinās.",
        "source_url": "https://x.com/OtherAuthor/status/9999999999",
        "created_at": "2026-04-23T11:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    from src.db import get_db
    db = get_db(db_path)
    role = db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    assert role is not None
    assert role["role"] == "mentioned", (
        f"expected 'mentioned' for non-author tweet, got {role['role']!r}"
    )
    db.close()


def test_store_tweets_assigns_mentioned_when_source_url_missing(tmp_path, monkeypatch):
    """Defensive: missing or malformed source_url falls back to 'mentioned'.
    Safer than 'subject' because we cannot verify authorship.
    """
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.db.DB_PATH", db_path)
    _setup_social_db(db_path)

    from src.social import _store_tweets
    tweets = [{
        "text": "Kaut kāda saruna par politiku — pietiekami gara, lai nepaliktu zem 50 rakstzīmju sliekšņa.",
        "source_url": None,
        "created_at": "2026-04-23T12:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    from src.db import get_db
    db = get_db(db_path)
    role = db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    # Missing source_url means we cannot prove authorship — default to 'mentioned'
    if role is not None:
        assert role["role"] == "mentioned"
    # Or the doc may be skipped entirely if insert_document rejects NULL source_url —
    # either is acceptable behavior; the critical invariant is "NOT tagged subject
    # without author proof".
    db.close()
```

Notes:
- Test text must be ≥50 chars (current `_store_tweets` filter at line 35).
- Must include Latvian diacritics (ā, ē, ū, ņ, ī) to pass any downstream diacritic validation.
- Case-insensitive handle match — the helper `extract_twitter_author_handle` returns lowercase, so comparison must lowercase social_accounts.handle too.
- `insert_document` may dedupe if you run tests in the same DB twice; `tmp_path` per test avoids that.

- [ ] **Step 3: Run tests, confirm they FAIL**

Run:
```bash
source .venv/Scripts/activate && python -m pytest tests/test_social.py -v -k "store_tweets"
```

Expected: first two tests FAIL (current code assigns 'subject' unconditionally, so test_author_differs sees 'subject' instead of 'mentioned'). Third test may pass or fail depending on how `insert_document` handles NULL source_url.

- [ ] **Step 4: Implement the fix**

Open `src/social.py`. Replace the function body (lines 30-56) with:

```python
def _store_tweets(tweets: list[dict], opponent_id: int) -> list[dict]:
    """Store tweet dicts as documents with embeddings. Returns stored tweets.

    Role assignment (2026-04-23 fix): compare each tweet's source_url author
    against the politician's registered twitter handles in social_accounts.
    Match → role='subject' (the politician IS the author). Mismatch or
    unresolvable → role='mentioned' (twikit surfaced someone else's tweet via
    this politician's timeline — retweet/quote-tweet/reply context — so the
    politician is mentioned but not speaking). Prior to this fix the role was
    hardcoded 'subject' regardless of authorship, which polluted the
    extractor queue with non-speaker docs (see wiki/CHANGELOG 2026-04-23).
    """
    from src.ingest import extract_twitter_author_handle

    # Resolve the politician's registered handles ONCE for this call.
    # Stored in lowercase to match extract_twitter_author_handle's output.
    db = get_db()
    handles = {
        row["handle"].lower()
        for row in db.execute(
            "SELECT handle FROM social_accounts "
            "WHERE platform = 'twitter' AND opponent_id = ?",
            (opponent_id,),
        ).fetchall()
    }
    db.close()

    stored = []
    for tweet in tweets:
        text = tweet.get("text", "")
        if len(text) < 50:
            continue
        lang = tweet.get("lang")
        if lang not in ("lv", "ru", "en"):
            lang = "lv"
        source_url = tweet.get("source_url")
        author_handle = extract_twitter_author_handle(source_url)
        # role='subject' requires verified authorship: the source_url's
        # handle must be one of this politician's registered handles.
        # Anything else — different author, missing URL, malformed URL —
        # degrades to role='mentioned' so the extractor queue stays clean.
        role = "subject" if (author_handle and author_handle in handles) else "mentioned"
        doc_id = insert_document(
            content=text,
            politician_links=[(opponent_id, role)],
            source_id=None,
            platform="twitter",
            language=lang,
            source_url=source_url,
            published_at=tweet.get("created_at"),
            reply_count=tweet.get("reply_count"),
            retweet_count=tweet.get("retweet_count"),
            favorite_count=tweet.get("favorite_count"),
        )
        if doc_id:
            chunks = embed_document(text)
            insert_chunks(doc_id, chunks)
            stored.append(tweet)
    return stored
```

Key invariants:
- The handle set is resolved ONCE per `_store_tweets` call, not per-tweet (saves N DB roundtrips).
- `extract_twitter_author_handle` returns lowercase — the set is also lowercased for case-insensitive comparison.
- `author_handle and author_handle in handles` short-circuits on None.
- The function signature is unchanged — callers (`fetch_twitter`, `fetch_all_twitter`, `fetch_all_x_accounts`) don't need edits.

- [ ] **Step 5: Run tests, confirm they PASS**

Run:
```bash
python -m pytest tests/test_social.py -v -k "store_tweets"
```

Expected: all three tests PASS.

- [ ] **Step 6: Regression check**

Run:
```bash
python -m pytest tests/ -v -k "social or ingest or claim or analyze"
```

Expected: all pre-existing tests still pass. The change only affects role assignment inside `_store_tweets`; the rest of the ingest/analyze pipeline is untouched.

- [ ] **Step 7: Commit**

```bash
git add src/social.py tests/test_social.py
git commit -m "fix(social): _store_tweets assigns role by source_url author match"
```

---

## Task 2: Backfill script for 83 existing mismatched rows

**Files:**
- Create: `scripts/fix_subject_role_leakage.py`

Context: 83 `role='subject'` rows in `document_politicians` (all scraped 2026-04-21 / 2026-04-23) have `source_url` authored by a handle NOT in the politician's registered handles. Top affected: Stendzenieks 12, Kulbergs 10, Vītols 9, Krištopans 8, Kļuciņš 6, Pūpols 5, M.Krusts 5. This script downgrades them to `role='mentioned'` and AUDITS any claims that may have been extracted from those junction rows (for manual review — the script does NOT delete claims).

- [ ] **Step 1: Write the script**

Create `scripts/fix_subject_role_leakage.py`:

```python
"""One-shot backfill for 2026-04-23 matcher role-integrity regression.

Downgrades `document_politicians.role` from 'subject' to 'mentioned' for
twitter rows where source_url's author handle is NOT among the politician's
registered handles in social_accounts. This addresses 83 junction rows that
leaked through the live-fetch path (src.social._store_tweets) between the
2026-04-20 fix (which only patched the post-hoc scanner) and today's
complementary fix on the write path.

Idempotent: re-runs find nothing to update after the first pass.

Safety:
- UPDATE (not DELETE) — preserves the linkage metadata with the corrected
  role so mentions-monitor and downstream readers keep working.
- Read-only audit of claims potentially extracted from mis-tagged junction
  rows; DOES NOT auto-delete claims. Prints a report for operator review,
  mirroring the 2026-04-20 manual-delete pattern ('11 claims deleted' per
  project_matcher_role_integrity memory).
- Reports affected pids + counts so the operator can verify scope before/after.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.ingest import extract_twitter_author_handle  # noqa: E402


def main() -> None:
    db = get_db()
    db.row_factory = db.row_factory  # keep whatever get_db set

    # Build pid → lowercase handles map for all twitter social_accounts.
    pid_handles: dict[int, set[str]] = {}
    for row in db.execute(
        "SELECT opponent_id, handle FROM social_accounts "
        "WHERE platform = 'twitter' AND active = 1"
    ).fetchall():
        pid_handles.setdefault(row["opponent_id"], set()).add(row["handle"].lower())

    # Find mismatched junction rows: role='subject' on twitter docs where
    # the doc's URL author is NOT in the pid's registered handles.
    candidates = db.execute(
        """
        SELECT dp.rowid AS jrow, dp.document_id, dp.politician_id, d.source_url,
               tp.name AS politician_name
        FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        JOIN tracked_politicians tp ON tp.id = dp.politician_id
        WHERE dp.role = 'subject'
          AND d.platform = 'twitter'
          AND d.source_url IS NOT NULL
        """
    ).fetchall()

    to_fix: list[tuple[int, int, int, str, str]] = []  # (jrow, doc_id, pid, name, source_url)
    for r in candidates:
        author = extract_twitter_author_handle(r["source_url"])
        pid = r["politician_id"]
        registered = pid_handles.get(pid, set())
        if author and author not in registered:
            to_fix.append(
                (r["jrow"], r["document_id"], pid, r["politician_name"], r["source_url"])
            )

    if not to_fix:
        print("No mismatched subject rows found — nothing to fix.")
        return

    # Affected-by-pid summary
    pid_counts: dict[tuple[int, str], int] = {}
    for _, _, pid, name, _ in to_fix:
        pid_counts[(pid, name)] = pid_counts.get((pid, name), 0) + 1
    print(f"Found {len(to_fix)} mismatched subject rows across {len(pid_counts)} politicians:")
    for (pid, name), count in sorted(pid_counts.items(), key=lambda x: -x[1]):
        print(f"  pid={pid:3d} {name:30s} {count} rows")

    # Audit: any claims written against these (politician_id, document_id) pairs?
    # These are potential mis-attributions needing manual review.
    print("\n--- Claim audit (potential mis-attributions) ---")
    affected_pairs = {(pid, doc_id) for _, doc_id, pid, _, _ in to_fix}
    claim_count = 0
    for pid, doc_id in affected_pairs:
        claims = db.execute(
            "SELECT id, topic, substr(stance, 1, 80) AS stance_preview "
            "FROM claims WHERE opponent_id = ? AND document_id = ?",
            (pid, doc_id),
        ).fetchall()
        for c in claims:
            claim_count += 1
            print(f"  claim #{c['id']} pid={pid} doc={doc_id} topic={c['topic']!r}")
            print(f"    {c['stance_preview']}")
    if claim_count == 0:
        print("  No claims tied to mis-tagged rows — clean downgrade, no manual review needed.")
    else:
        print(f"\n  {claim_count} claim(s) may be mis-attributed. Review manually;")
        print("  this script DOES NOT auto-delete them.")

    # Apply the UPDATE
    print(f"\n--- Applying UPDATE ---")
    with db:
        for jrow, _doc_id, _pid, _name, _url in to_fix:
            db.execute(
                "UPDATE document_politicians SET role = 'mentioned' WHERE rowid = ?",
                (jrow,),
            )
    print(f"Updated {len(to_fix)} junction rows: role 'subject' → 'mentioned'.")

    # Post-run verification: the same SELECT should now return 0
    remaining = db.execute(
        """
        SELECT COUNT(*) FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        WHERE dp.role = 'subject' AND d.platform = 'twitter'
          AND d.source_url IS NOT NULL
        """
    ).fetchone()[0]
    # Re-count candidates where author mismatches after UPDATE
    still_bad = 0
    for r in db.execute(
        """
        SELECT dp.politician_id, d.source_url FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        WHERE dp.role = 'subject' AND d.platform = 'twitter' AND d.source_url IS NOT NULL
        """
    ).fetchall():
        author = extract_twitter_author_handle(r["source_url"])
        if author and author not in pid_handles.get(r["politician_id"], set()):
            still_bad += 1
    print(f"Post-update check: {remaining} twitter subject rows total, {still_bad} still mismatched.")
    assert still_bad == 0, f"Expected 0 mismatches after UPDATE, got {still_bad}"


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit the script (don't run yet — Task 3 runs it)**

```bash
git add scripts/fix_subject_role_leakage.py
git commit -m "fix(scripts): add backfill for mismatched subject role junction rows"
```

---

## Task 3: Execute backfill + verify

**Files:** _none_ (DB-only changes)

- [ ] **Step 1: Snapshot the DB**

Before running destructive ops, back up `data/atmina.db`:

```bash
cp data/atmina.db "data/backups/atmina_pre-role-fix-$(date +%Y-%m-%d-%H%M).db"
ls -la data/backups/ | tail -3
```

Expected: a fresh backup file with today's date in `data/backups/`.

- [ ] **Step 2: Pre-count mismatches**

Run:
```bash
source .venv/Scripts/activate && PYTHONIOENCODING=utf-8 python -c "
from src.db import get_db
from src.ingest import extract_twitter_author_handle
db = get_db()
pid_h = {}
for r in db.execute('SELECT opponent_id, handle FROM social_accounts WHERE platform=\"twitter\" AND active=1').fetchall():
    pid_h.setdefault(r['opponent_id'], set()).add(r['handle'].lower())
bad = 0
for r in db.execute('SELECT dp.politician_id, d.source_url FROM document_politicians dp JOIN documents d ON d.id=dp.document_id WHERE dp.role=\"subject\" AND d.platform=\"twitter\" AND d.source_url IS NOT NULL').fetchall():
    a = extract_twitter_author_handle(r['source_url'])
    if a and a not in pid_h.get(r['politician_id'], set()):
        bad += 1
print(f'Mismatched subject rows BEFORE backfill: {bad}')
"
```

Expected: `Mismatched subject rows BEFORE backfill: 83` (or thereabouts — may be ±2 depending on what got scraped between diagnosis and fix).

- [ ] **Step 3: Run the backfill**

```bash
PYTHONIOENCODING=utf-8 python -m scripts.fix_subject_role_leakage
```

Expected output shape:
```
Found 83 mismatched subject rows across 10 politicians:
  pid= 60 Ēriks Stendzenieks        12 rows
  pid= 10 Andris Kulbergs           10 rows
  ... (etc)

--- Claim audit (potential mis-attributions) ---
  No claims tied to mis-tagged rows — clean downgrade, no manual review needed.
  (OR a list of claim IDs if any — operator decides deletion manually.)

--- Applying UPDATE ---
Updated 83 junction rows: role 'subject' → 'mentioned'.
Post-update check: <N> twitter subject rows total, 0 still mismatched.
```

If the audit reports CLAIMS to review, capture the list — show it to the operator before deciding deletion. Do NOT auto-delete.

- [ ] **Step 4: Verify idempotency**

Re-run the same command:

```bash
PYTHONIOENCODING=utf-8 python -m scripts.fix_subject_role_leakage
```

Expected: `No mismatched subject rows found — nothing to fix.`

- [ ] **Step 5: Sanity-check specific politicians mentioned in today's session**

```bash
PYTHONIOENCODING=utf-8 python -c "
from src.db import get_db
db = get_db()
for pid, name in [(169, 'KlucisD'), (60, 'Stendzenieks'), (10, 'Kulbergs'), (9, 'Krištopans')]:
    subj = db.execute('SELECT COUNT(*) FROM document_politicians dp JOIN documents d ON d.id=dp.document_id WHERE dp.politician_id=? AND dp.role=\"subject\" AND d.platform=\"twitter\"', (pid,)).fetchone()[0]
    ment = db.execute('SELECT COUNT(*) FROM document_politicians dp JOIN documents d ON d.id=dp.document_id WHERE dp.politician_id=? AND dp.role=\"mentioned\" AND d.platform=\"twitter\"', (pid,)).fetchone()[0]
    print(f'  pid={pid:3d} {name:20s} subject={subj} mentioned={ment}')
"
```

Expected: the 'subject' counts for these politicians dropped by the amounts flagged in the diagnostic (KlucisD should now have ~3 subject rows instead of 9, etc.), and their `mentioned` counts grew correspondingly.

- [ ] **Step 6: No commit at this step**

The backfill is DB-only, no code changes from this task. Proceed to Task 4.

---

## Task 4: Diacritic validator fix — fasttext escape + EN_MARKERS + logging (TDD)

**Files:**
- Modify: `src/quality.py` — add fasttext early-exit, extend EN_MARKERS, add `logging.warning` on rejections
- Test: `tests/test_quality.py` — append 4 new tests

- [ ] **Step 1: Write failing tests**

Append to `tests/test_quality.py` (create if missing):

```python
def test_english_tweet_with_to_preposition_passes():
    """Regression for 2026-04-23: English tweet quoting LV export figures
    was rejected because LV_STOPWORDS includes 'to' (firing on 'exports to
    Russia' → lv_score=2) while EN_MARKERS missed common tokens like 'at',
    'more', 'already'. Should now pass via fasttext detection or expanded
    EN_MARKERS.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Latvian exports to Russia remain at 70.5 million euros. "
        "Six times more than Estonia already does at this level."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"English tweet should not be rejected, got: {reason}"


def test_stripped_latvian_still_rejected_despite_fasttext_drift():
    """Guardrail preservation: stripped Latvian must STILL be rejected.
    fasttext misclassifies stripped LV as fr/sr/hr at low confidence, so
    the early-exit (which fires only on conf >= 0.70) doesn't trigger.
    Falls through to the token matcher, which catches it via LV_STOPWORDS
    and the low-diacritic ratio.
    """
    from src.quality import validate_lv_diacritics
    # Real-world stripped LV: 'Daudz tiek runats par partija koalicija budzets
    # un tie netiek risinati tomer valsts parvalde turpinas ka ierasts.'
    text = (
        "Daudz tiek runats par partija koalicija un budzets bet tie netiek "
        "risinati tomer valsts parvalde turpinas ka ierasts — tas nav labi."
    )
    ok, reason = validate_lv_diacritics(text)
    assert not ok, f"Stripped Latvian should be rejected, got ok=True with reason: {reason}"
    assert "stripped" in reason.lower() or "diacritic" in reason.lower()


def test_russian_text_passes():
    """Cyrillic/Russian text must pass (already handled by Cyrillic-heavy
    early-return at src/quality.py:88-90). Fasttext would also say 'ru' with
    high confidence. Two independent signals converge on 'accept'.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Президент и премьер-министр обсудили вопросы безопасности "
        "на встрече в Риге в четверг, а также экспорт в Россию."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"Russian text should pass, got: {reason}"


def test_genuine_latvian_with_diacritics_passes():
    """Baseline: real Latvian text with proper diacritics must pass.
    No regression from the fasttext early-exit or EN_MARKERS expansion.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Šodien parlamentā notiek debates par budžeta grozījumiem. "
        "Ministru kabineta sēdē pieņemti lēmumi par ārpolitikas prioritātēm "
        "un sadarbību ar kaimiņvalstīm aizsardzības jomā."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"Genuine Latvian should pass, got: {reason}"
```

- [ ] **Step 2: Run tests, confirm the English test fails (others may already pass)**

Run:
```bash
python -m pytest tests/test_quality.py -v -k "english_tweet or stripped_latvian or russian or genuine_latvian"
```

Expected: `test_english_tweet_with_to_preposition_passes` FAILS with the "stripped Latvian" rejection message. The other three tests likely PASS on existing code (baseline).

- [ ] **Step 3: Implement the fix in `src/quality.py`**

Three changes:

**Change A — add fasttext early-exit:**

Insert a new block between lines 85 (`if letters < min_letters: return True, "too short..."`) and line 87 (Cyrillic check). After the short-text skip and BEFORE the Cyrillic check:

```python
    # Primary language-ID via fasttext (added 2026-04-23). Confident non-LV
    # classifications short-circuit the token-matcher, fixing false-positives
    # where short English tweets tripped the LV_STOPWORDS 'to'/'no' overlap.
    # Stripped Latvian ('Daudz tiek runats...') is misclassified by fasttext
    # as fr/sr/hr at LOW confidence (<0.50), so the 0.70 threshold preserves
    # the guardrail: stripped LV falls through to the token matcher and
    # gets correctly rejected below.
    try:
        from src.ingest import _detect_language
        lang, conf = _detect_language(text)
        if lang in ("en", "ru", "de", "fr", "es", "pl", "it") and conf >= 0.70:
            return True, f"non-Latvian per fasttext ({lang} {conf:.2f})"
    except Exception:
        # fasttext unavailable (model download error, import issue) —
        # silently fall through to the token matcher. Matches the tolerant
        # pattern used at src/ingest.py::_get_ft_model.
        pass
```

**Change B — extend EN_MARKERS:**

Locate lines 43-55. APPEND to the existing set (don't remove anything):

```python
EN_MARKERS = {
    "the", "and", "is", "are", "was", "were", "been", "being",
    "of", "for", "with", "from", "this", "that", "these", "those",
    "have", "has", "had", "will", "would", "could", "should",
    "which", "what", "when", "where", "who", "whose",
    "it", "its", "he", "his", "she", "her", "they", "them", "their",
    "we", "our", "you", "your", "my", "me",
    "or", "but", "not", "new", "now", "by", "as", "an",
    "if", "so", "do", "does", "did", "done",
    "there", "here", "such", "only", "also", "just",
    "about", "after", "before", "between", "into", "onto",
    "still", "then", "than", "because",
    # 2026-04-23 expansion: tokens missed by the original set that caused
    # false-positives on English tweets (e.g. M. Krusts's 'Latvian exports
    # to Russia remain at 70.5 million...' — contained 'to' twice hitting
    # LV_STOPWORDS but only 'this' as an EN marker).
    "at", "while", "already", "yet", "ever", "never",
    "most", "more", "less", "few", "many", "much", "some", "all",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "times", "time", "remain", "remains", "fall", "falls", "rise", "rises",
    "reach", "reaches", "become", "becomes", "continues", "continue",
    "keep", "keeps", "every", "each", "own", "same", "other", "another",
    "both", "per", "via", "against", "across", "during", "within",
    "without", "through", "over", "under", "above", "below",
}
```

**Change C — add logging.warning on rejections:**

At the top of `src/quality.py` (after existing docstring, before `LV_DIACRIT = set(...)`), add:

```python
import logging

logger = logging.getLogger(__name__)
```

Then modify the two False-returning branches at lines 135-139. Change:

```python
    if ratio < ratio_threshold:
        return False, (
            f"Latvian text but only {diacrit}/{letters} = {ratio:.1%} "
            f"diacritics — likely stripped (agent context-drift?)"
        )
```

To:

```python
    if ratio < ratio_threshold:
        reason = (
            f"Latvian text but only {diacrit}/{letters} = {ratio:.1%} "
            f"diacritics — likely stripped (agent context-drift?)"
        )
        logger.warning("validate_lv_diacritics rejected: %s — text[:80]=%r", reason, text[:80])
        return False, reason
```

(This is the only False-return branch in the current code — add the `logger.warning(...)` line and assign `reason` to a variable first.)

- [ ] **Step 4: Run the tests again, confirm all PASS**

Run:
```bash
python -m pytest tests/test_quality.py -v
```

Expected: all tests in the file pass (including the 4 new ones). Especially `test_english_tweet_with_to_preposition_passes` should now PASS.

- [ ] **Step 5: Regression check**

Run:
```bash
python -m pytest tests/ -v -k "quality or claim or analyze or store_claim"
```

Expected: all pre-existing tests pass. The two key guardrails — stripped Latvian detection + Cyrillic skip — remain intact. No existing store_claim tests should break.

- [ ] **Step 6: Commit**

```bash
git add src/quality.py tests/test_quality.py
git commit -m "fix(quality): fasttext early-exit + EN_MARKERS expansion + rejection logging"
```

---

## Task 5: Docs — CHANGELOG entry for both fixes

**Files:**
- Modify: `wiki/CHANGELOG.md` — add dated entry at top

- [ ] **Step 1: Append CHANGELOG entry**

Open `wiki/CHANGELOG.md`. At the TOP (most recent first per convention — same convention as the 2026-04-23 Komentētāji entry added earlier today). Add:

```markdown
## 2026-04-23 — Matcher role integrity + diacritic validator fixes

**What changed:**
- `src/social.py::_store_tweets` now assigns `role='subject'` only when the tweet's source_url author matches the politician's registered twitter handles; mismatch or unresolvable URL → `role='mentioned'`. Mirrors exactly the 2026-04-20 fix pattern that was applied only to the post-hoc scanner path.
- `src/quality.py::validate_lv_diacritics` adds a fasttext primary language-ID early-exit (`lang in {en, ru, de, fr, es, pl, it} and conf >= 0.70 → True`), extends `EN_MARKERS` with ~30 common tokens that were missed (`at`, `more`, `already`, `six`, `times`, `remain`, `fall`, etc.), and adds `logging.warning` on rejections for future observability.
- `scripts/fix_subject_role_leakage.py` one-shot idempotent backfill downgraded 83 mismatched junction rows from `subject` to `mentioned`, with a claim audit report (no auto-delete).

**Why:**
- Matcher: The 2026-04-20 fix patched `src/ingest.py::link_politicians_to_documents` but NOT `src/social.py::_store_tweets`. The live-fetch path continued hardcoding `subject` on every tweet, including retweets/quote-tweets/replies that twikit normalises to the ORIGINAL author's source_url. 83 rows accumulated between 2026-04-21 and 2026-04-23 before detection.
- Diacritic: M. Krusts English-language tweet quote was rejected because `LV_STOPWORDS` includes `to` (fires on every "exports to X" English construction) and `EN_MARKERS` missed common counter-tokens. Short English tweets tripped the gate. Agent had to drop the `quote` field to save the claim — lossy. Fix preserves stripped-LV detection via fallback-to-token-matcher design.

**Backward compatibility:**
- Matcher fix is forward-only; existing `mentioned` and `subject` semantics unchanged. Pre-fix extracted claims are not revisited automatically — the Task 3 backfill includes a claim audit report so the operator can manually delete any mis-attributed claims.
- Diacritic fix is additive: fasttext early-exit ADDS an accept path, EN_MARKERS expansion ADDS tokens. No existing acceptance path is removed. The stripped-LV rejection path is preserved unchanged (tested via `test_stripped_latvian_still_rejected_despite_fasttext_drift`).

**Files:** `src/social.py`, `src/quality.py`, `scripts/fix_subject_role_leakage.py`, `tests/test_social.py`, `tests/test_quality.py`.

**Out of scope (follow-ups):** `match_politicians(text)` enrichment of `_store_tweets` (`role='mentioned'` rows for OTHER tracked politicians named in the tweet). `published_at` backfill for 55% NULL web docs. `print_routine()` heuristic distinguishing "quiet user" from "scraper broken".
```

- [ ] **Step 2: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -m "docs(wiki): document matcher role + diacritic validator fixes"
```

---

## Task 6: Full smoke — pytest + site regen

**Files:** _none_ (verification only)

- [ ] **Step 1: Full pytest**

Run:
```bash
source .venv/Scripts/activate && python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: green across the suite. The baseline before these fixes was 610 passed; adding 3 social tests + 4 quality tests gives 617+ expected.

- [ ] **Step 2: Site regeneration smoke-test**

Run:
```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: completes cleanly, 148 active politician profile pages (same as post-Komentētāji baseline — the backfill doesn't change which politicians get pages).

- [ ] **Step 3: Spot-check post-backfill state on specific profiles**

The subagents today correctly marked KlucisD/Stendzenieks/Krištopans docs as `empty_doc_ids`, so site rendering should already be clean. Confirm KlucisD's profile still shows the correctly-attributed commentary (not any of the downgraded rows):

```bash
PYTHONIOENCODING=utf-8 python -c "
import re
for slug in ['ansis-pupols.html', 'viesturs-kleinbergs.html', 'martins-stakis.html']:
    with open(f'output/atmina/politiki/{slug}', 'r', encoding='utf-8') as f:
        html = f.read()
    m = re.search(r'<h2[^>]*id=\"komentari-heading\"[^>]*>([^<]+)</h2>', html)
    if m:
        print(f'{slug}: {m.group(1)}')
    else:
        print(f'{slug}: no komentari heading')
"
```

Expected: Pūpols shows "Trešo pušu komentāri par Ansis Pūpols (3)", Kleinbergs "...(1)", Staķis "...(1)". Matches the post-extraction state from today.

- [ ] **Step 4: Routine status**

```bash
PYTHONIOENCODING=utf-8 python -c "from src.routine import print_routine; print_routine()"
```

Expected: no Python errors; routine report shows Step 2 complete for today's analyzed politicians. Step 7 (daily brief) still shown as pending per operator's deferral.

- [ ] **Step 5: Branch completion**

Work is done. Hand off via `superpowers:finishing-a-development-branch` to pick merge-vs-PR.

---

## Coverage self-review

Checklist before declaring plan complete:

- ✅ Matcher live-fetch path fixed → Task 1
- ✅ Backfill of 83 existing mismatched rows → Tasks 2+3
- ✅ Claim audit (report, no auto-delete) → Task 2 (inside script)
- ✅ Tests for matcher: subject-match, mentioned-on-author-differ, null-url fallback → Task 1
- ✅ Diacritic validator English false-positive fix → Task 4 (Change A + B)
- ✅ Stripped-LV guardrail preserved → Task 4 test case
- ✅ Observability — logging.warning on rejections → Task 4 (Change C)
- ✅ Tests for diacritic: EN passes, stripped LV still rejected, RU passes, genuine LV passes → Task 4
- ✅ Documentation — CHANGELOG entry covering both fixes → Task 5
- ✅ Full regression — pytest + site regen + routine → Task 6

**Explicit non-coverage (confirmed out-of-scope, documented in CHANGELOG "Out of scope"):**
- `match_politicians(text)` content-scan enrichment in `_store_tweets`
- `published_at` backfill for NULL web docs
- `print_routine()` "quiet user" vs "scraper broken" heuristic
- `language=` explicit parameter on `store_claim` / `save_analysis`
- Deletion of any claims that the Task 3 audit flags — that's an editorial call, handled manually
