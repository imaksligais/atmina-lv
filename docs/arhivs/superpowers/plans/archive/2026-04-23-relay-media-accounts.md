# Relay Media X Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable institutional media X accounts (LTV Ziņas, future: Delfi/TVNET/LSM X, ministry accounts) to feed politician quotes into the pipeline as *first-party* claims attributed to the quoted politician — not as commentary by the media outlet. The outlet's tweet serves as a source URL, not a speaker.

**Architecture:** One new column — `social_accounts.feed_type TEXT DEFAULT 'first_party'` with values `'first_party'` | `'relay'` — splits account behavior without renaming any existing `relationship_type`. Two pipeline branches read the flag:

1. `src/social.py::_store_tweets` — when `feed_type='relay'`, skip the hardcoded `(opponent_id, 'subject')` junction link. Document gets inserted with `politician_links=[]`.
2. `src/ingest.py::link_politicians_to_documents` — when the URL author's handle belongs to a `feed_type='relay'` account, **skip** the Twitter author-handle downgrade. Otherwise, quoted politicians would be downgraded from `'subject'` to `'mentioned'` (because LTV's handle isn't in their handle sets) and never enter the extraction queue.

Net effect: an LTV tweet "Kariņš: X notiks šogad" → Kariņš gets `role='subject'` via text-scan → Kariņš's extraction bucket picks up the doc → claim stored as `opponent_id=Kariņš, speaker_id=NULL, claim_type='position', source_url=<LTV tweet URL>`. Contradiction detection works identically to Kariņš's direct tweets.

**Tech Stack:** Python 3.11 + SQLite (runtime `ALTER TABLE` in `src/db.py::init_db`, same idempotent PRAGMA-guarded pattern as existing migrations at `db.py:449-467`), pytest with `tmp_db` fixture.

**Files touched (6 total):**

- Modify: `src/db.py::init_db` — ALTER TABLE block + index (idempotent, PRAGMA-guarded, matches existing pattern at db.py:449-467)
- Modify: `src/social.py::_store_tweets` — looks up `feed_type` from `social_accounts` internally, skips `(opponent_id, 'subject')` link when relay. `fetch_twitter` / `fetch_all_twitter` / `fetch_all_x_accounts` untouched — they don't need to carry feed_type because `_store_tweets` reads it from the DB row it already has access to.
- Modify: `src/ingest.py::link_politicians_to_documents` — precompute `relay_handles` set; skip Twitter downgrade when author is a relay handle
- Modify: `scripts/seed_media_sources.py` — declare `feed_type='relay'` for LTV; UPDATE existing social_accounts rows when flag differs
- Modify: `tests/test_db.py` — two column/idempotency tests appended to `TestSocialDraftsTable`
- Modify: `tests/test_ingest.py` — three new tests: first-party store_tweets (regression guard), relay store_tweets skips author link, relay link step keeps quoted politician as subject
- Modify: `wiki/CHANGELOG.md` — 2026-04-23 entry (NB: "6 total" excludes CHANGELOG since it's doc-only)

**Branch:** `feat/relay-media-accounts` (create from current `feat/komentetaji-speaker-id` at Task 0 — this builds on speaker_id architecture).

**Spec decisions locked in (do not reconsider mid-implementation):**

- `feed_type` lives on `social_accounts`, **not** `tracked_politicians`. A single person could hypothetically own both a first-party account (personal X) and a relay account (institutional role). Per-account flag is cleanest. Default `'first_party'` preserves all existing account behavior.
- `relationship_type` stays untouched. LTV Ziņas remains `'journalist'`. No new UI category for "media" in this plan — the UI can iterate separately if needed.
- `_store_tweets` reads `feed_type` from the `social_accounts` row by looking it up (one extra SELECT per fetch batch is cheap and avoids plumbing it through every caller). Alternative considered: pass feed_type through `fetch_all_x_accounts` → rejected as more surface for identical outcome.
- Retweets (posts whose text starts with `RT @...`) are **out of scope** for this plan. They get stored as relay docs and will mostly fail to match politicians due to truncated text. A follow-up may add an RT filter in `_store_tweets`; left for now because the user's confirmed goal is politician-quote capture, and RT filter is independent.
- `x_mentions` pipeline (`src/x_mentions.py`) is **unaffected**. Mentions use `platform='x_mention'` and a different ingestion path; relay accounts don't receive mention queries.

**Out of scope (MVP):**

- UI-level "Mediju avoti" section separate from "Žurnālisti"
- Retweet filtering at fetch time
- Migration of existing non-LTV journalist accounts (Lato Lapsa) — they legitimately are speakers and stay `feed_type='first_party'`
- Automatic relay detection from account metadata
- Claim-extractor prompt changes — the existing `relationship_type='commentator'` → commentary path logic remains; relay accounts don't trigger it because relay docs end up in the QUOTED politician's bucket, not the outlet's bucket

---

## Task 0: Branch setup

**Files:** _none_

- [ ] **Step 1: Verify clean working tree (minus expected untracked files)**

Run: `git status --short`

Expected output lines are only:
- `?? scripts/seed_media_sources.py` (created earlier this session; will travel with the branch)
- `?? docs/superpowers/plans/2026-04-23-komentetaji-speaker-id.md` (pre-existing untracked)
- `?? docs/superpowers/plans/2026-04-23-relay-media-accounts.md` (this plan)
- `?? tmp_brief_2026-04-22.md`, `?? tmp_skel.md` (pre-existing)

If anything else is modified under `src/db.py`, `src/social.py`, `src/ingest.py`, `src/x_scraper.py`, or `tests/`, stop and ask the user.

- [ ] **Step 2: Create and check out feature branch**

Run:
```bash
git checkout -b feat/relay-media-accounts
```

Expected: `Switched to a new branch 'feat/relay-media-accounts'`

- [ ] **Step 3: Verify branch**

Run: `git branch --show-current`

Expected: `feat/relay-media-accounts`

No commit at this step.

---

## Task 1: Schema migration — `social_accounts.feed_type` column

**Files:**
- Modify: `src/db.py:452` (insert new migration block after `negative_patterns` migration, before the 2026-04-23 speaker_id block at line 453)
- Test: `tests/test_db.py` (append new test, follow existing `test_social_*` naming pattern at `test_db.py:691`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py` inside the same class that contains `test_social_drafts_columns_present` (around line 691):

```python
    def test_social_accounts_feed_type_column_present(self):
        """feed_type column exists on social_accounts with correct default."""
        from src.db import get_db, init_db
        init_db()
        db = get_db()
        cols = {r[1]: r for r in db.execute("PRAGMA table_info(social_accounts)").fetchall()}
        assert "feed_type" in cols, "feed_type column must exist on social_accounts"
        default = cols["feed_type"][4]  # PRAGMA column 4 = dflt_value
        assert default == "'first_party'", f"expected default 'first_party', got {default!r}"
        db.close()

    def test_social_accounts_feed_type_idempotent(self):
        """Running init_db twice must not fail or duplicate the column."""
        from src.db import init_db, get_db
        init_db()
        init_db()  # second run is the idempotency check
        db = get_db()
        cols = [r[1] for r in db.execute("PRAGMA table_info(social_accounts)").fetchall()]
        assert cols.count("feed_type") == 1
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py::TestSocialDraftsTable::test_social_accounts_feed_type_column_present tests/test_db.py::TestSocialDraftsTable::test_social_accounts_feed_type_idempotent -v`

Expected: FAIL with `KeyError: 'feed_type'` or `AssertionError: feed_type column must exist`.

- [ ] **Step 3: Implement the migration**

Open `src/db.py`. After the `negative_patterns` migration block (ending at `db.py:451`), and BEFORE the existing `# 2026-04-23 — speaker_id` comment at `db.py:453`, insert:

```python
    # 2026-04-23 — feed_type on social_accounts distinguishes first-party
    # speaker accounts (politician's own X, commentator, individual journalist
    # posting opinions) from relay accounts (institutional media X accounts
    # that post third-party quotes — LTV Ziņas, Delfi, TVNET). Relay accounts
    # must NOT be marked as subject of their own tweets — see src/social.py::
    # _store_tweets and src/ingest.py::link_politicians_to_documents. Default
    # 'first_party' preserves all existing account behavior.
    _sa_cols = {row[1] for row in db.execute("PRAGMA table_info(social_accounts)").fetchall()}
    if "feed_type" not in _sa_cols:
        db.execute("ALTER TABLE social_accounts ADD COLUMN feed_type TEXT DEFAULT 'first_party'")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_social_feed_type ON social_accounts(feed_type)"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py::TestSocialDraftsTable::test_social_accounts_feed_type_column_present tests/test_db.py::TestSocialDraftsTable::test_social_accounts_feed_type_idempotent -v`

Expected: PASS for both.

- [ ] **Step 5: Run full test_db.py to catch regressions**

Run: `python -m pytest tests/test_db.py -v`

Expected: all existing tests pass, plus the two new ones.

- [ ] **Step 6: Verify migration fired on the real dev DB**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.db import get_db, init_db; init_db(); db=get_db(); r=db.execute('PRAGMA table_info(social_accounts)').fetchall(); print([c[1] for c in r])"
```

Expected: output includes `feed_type` in the column list.

- [ ] **Step 7: Commit**

```bash
git add src/db.py tests/test_db.py scripts/seed_media_sources.py docs/superpowers/plans/2026-04-23-relay-media-accounts.md
git commit -m "$(cat <<'EOF'
feat(db): social_accounts.feed_type column for relay vs first_party

Institutional media X accounts (LTV Ziņas, future Delfi/TVNET) need
different ingestion semantics than speaker accounts — they relay
politician quotes rather than expressing their own positions.

Default 'first_party' preserves all existing account behavior. Relay
behavior wired up in src/social.py and src/ingest.py in follow-up
commits.

Also pulls in scripts/seed_media_sources.py (LTV Ziņas seed, created
earlier this session) and the implementation plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `_store_tweets` — skip author-subject link for relay accounts

**Files:**
- Modify: `src/social.py:30-56` (function `_store_tweets`)
- Test: `tests/test_ingest.py` (append new test following patterns at lines 240-303)

- [ ] **Step 1: Write the failing test for first-party behavior (regression guard)**

Append to `tests/test_ingest.py`:

```python
def test_store_tweets_first_party_links_author_as_subject(tmp_db):
    """Default feed_type='first_party': author is marked as subject of the tweet."""
    from src.social import _store_tweets

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (50, 'Test Politician', 'tracked')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (50, 'twitter', 'testpol', 'first_party')"
    )
    tmp_db.commit()

    tweets = [{
        "id": "9001",
        "text": "Mans viedoklis par inflāciju ir, ka mums jādara vairāk lai to apkarotu.",
        "created_at": "2026-04-23T10:00:00+00:00",
        "platform": "twitter",
        "lang": "lv",
        "source_url": "https://x.com/testpol/status/9001",
    }]

    _store_tweets(tweets, opponent_id=50)

    row = tmp_db.execute(
        "SELECT role FROM document_politicians dp "
        "JOIN documents d ON d.id = dp.document_id "
        "WHERE d.source_url = 'https://x.com/testpol/status/9001'"
    ).fetchone()
    assert row is not None, "politician_id=50 must be linked to the doc"
    assert row["role"] == "subject"


def test_store_tweets_relay_skips_author_subject_link(tmp_db):
    """feed_type='relay': no politician_links at insert time, so link
    function can later assign subject role to quoted politicians."""
    from src.social import _store_tweets

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (60, 'LTV Ziņas', 'journalist')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (60, 'twitter', 'ltvzinas', 'relay')"
    )
    tmp_db.commit()

    tweets = [{
        "id": "9002",
        "text": "Valdība strādā avārijas režīmā, sacīja Saeimas deputāts Test Politiķis.",
        "created_at": "2026-04-23T10:00:00+00:00",
        "platform": "twitter",
        "lang": "lv",
        "source_url": "https://x.com/ltvzinas/status/9002",
    }]

    _store_tweets(tweets, opponent_id=60)

    rows = tmp_db.execute(
        "SELECT dp.politician_id, dp.role FROM document_politicians dp "
        "JOIN documents d ON d.id = dp.document_id "
        "WHERE d.source_url = 'https://x.com/ltvzinas/status/9002'"
    ).fetchall()
    assert rows == [], f"relay tweet must have NO junction links at store time, got {list(rows)}"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_ingest.py::test_store_tweets_first_party_links_author_as_subject tests/test_ingest.py::test_store_tweets_relay_skips_author_subject_link -v`

Expected: `test_store_tweets_first_party_links_author_as_subject` PASSES (current behavior). `test_store_tweets_relay_skips_author_subject_link` FAILS with `assert rows == []` — current code links (60, 'subject') regardless of feed_type.

- [ ] **Step 3: Implement relay branch in `_store_tweets`**

Open `src/social.py`. Replace the function (currently lines 30-56) with:

```python
def _store_tweets(tweets: list[dict], opponent_id: int) -> list[dict]:
    """Store tweet dicts as documents with embeddings. Returns stored tweets.

    feed_type behavior (looked up once per call from social_accounts):
    - 'first_party' (default): doc gets (opponent_id, 'subject') link so the
      account owner is recognized as the speaker/subject of their own tweet.
    - 'relay': no politician_links inserted. link_politicians_to_documents
      later scans the text and assigns subject to the most-mentioned politician
      (the quoted speaker). Used for institutional media accounts that relay
      third-party quotes.
    """
    db = get_db()
    row = db.execute(
        "SELECT feed_type FROM social_accounts "
        "WHERE opponent_id = ? AND platform = 'twitter' "
        "ORDER BY id LIMIT 1",
        (opponent_id,),
    ).fetchone()
    db.close()
    feed_type = (row["feed_type"] if row else "first_party") or "first_party"

    if feed_type == "relay":
        politician_links: list[tuple[int, str]] = []
    else:
        politician_links = [(opponent_id, "subject")]

    stored = []
    for tweet in tweets:
        text = tweet.get("text", "")
        if len(text) < 50:
            continue
        lang = tweet.get("lang")
        if lang not in ("lv", "ru", "en"):
            lang = "lv"
        doc_id = insert_document(
            content=text,
            politician_links=politician_links,
            source_id=None,
            platform="twitter",
            language=lang,
            source_url=tweet.get("source_url"),
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

- [ ] **Step 4: Run the two tests**

Run: `python -m pytest tests/test_ingest.py::test_store_tweets_first_party_links_author_as_subject tests/test_ingest.py::test_store_tweets_relay_skips_author_subject_link -v`

Expected: PASS for both.

- [ ] **Step 5: Run full test_ingest.py to catch regressions**

Run: `python -m pytest tests/test_ingest.py -v`

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/social.py tests/test_ingest.py
git commit -m "$(cat <<'EOF'
feat(social): _store_tweets reads feed_type, skips author-subject for relay

Relay accounts (LTV Ziņas etc.) insert documents with no politician
links. link_politicians_to_documents then picks the subject from
text analysis, matching how RSS articles flow. first_party accounts
(default) keep the hardcoded (opponent_id, 'subject') link — no
behavior change for existing politicians/commentators/individual
journalists.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `link_politicians_to_documents` — don't downgrade quoted politicians for relay authors

**Files:**
- Modify: `src/ingest.py:1046-1098` (function `link_politicians_to_documents`, Twitter-downgrade block at lines 1084-1093)
- Test: `tests/test_ingest.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ingest.py`:

```python
def test_link_relay_author_keeps_quoted_politician_as_subject(tmp_db):
    """An LTV-authored tweet mentioning Krusts — Krusts must become
    subject (not downgraded to 'mentioned'), because LTV is a relay.
    This is what makes quoted politicians reach their extraction bucket."""
    from src.ingest import link_politicians_to_documents
    from src.db import insert_document

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type, name_forms) "
        "VALUES (70, 'LTV Ziņas', 'journalist', '[\"LTV Ziņas\", \"LTV\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (70, 'twitter', 'ltvzinas', 'relay')"
    )
    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type, name_forms) "
        "VALUES (71, 'Mārtiņš Krusts', 'tracked', '[\"Mārtiņš Krusts\", \"Krusts\"]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (71, 'twitter', 'krusts', 'first_party')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Pensiju 2. līmenis Lietuvā. Komentārs Mārtiņš Krusts par to.",
        source_id=None,
        source_url="https://x.com/ltvzinas/status/9003",
        platform="twitter",
        language="lv",
        politician_links=[],  # simulates relay _store_tweets
        db_path=tmp_db.execute("PRAGMA database_list").fetchone()["file"],
    )

    link_politicians_to_documents(days=30)

    row = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=71",
        (doc_id,),
    ).fetchone()
    assert row is not None, "Krusts must be linked to the LTV-authored doc"
    assert row["role"] == "subject", (
        f"expected 'subject' (relay author → no downgrade), got '{row['role']}'"
    )
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_ingest.py::test_link_relay_author_keeps_quoted_politician_as_subject -v`

Expected: FAIL with `assert 'mentioned' == 'subject'` — current Twitter-downgrade logic fires regardless of author feed_type.

- [ ] **Step 3: Modify `link_politicians_to_documents` to skip downgrade for relay authors**

Open `src/ingest.py`. Find the `link_politicians_to_documents` function (starts at line 1026). Two changes:

**Change A** (around line 1050-1055, where `pid_to_handles` is built): add `relay_handles` set. Modify the `sa_rows` query to include `feed_type`:

Replace:
```python
    pid_to_handles: dict[int, set[str]] = {}
    sa_rows = db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall()
    for sa in sa_rows:
        pid_to_handles.setdefault(sa["opponent_id"], set()).add(sa["handle"].lower())
```

With:
```python
    pid_to_handles: dict[int, set[str]] = {}
    relay_handles: set[str] = set()  # lowercase handles of relay-type accounts
    sa_rows = db.execute(
        "SELECT handle, opponent_id, feed_type FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall()
    for sa in sa_rows:
        h = sa["handle"].lower()
        pid_to_handles.setdefault(sa["opponent_id"], set()).add(h)
        if (sa["feed_type"] or "first_party") == "relay":
            relay_handles.add(h)
```

**Change B** (the Twitter-downgrade elif at ~line 1087): skip downgrade when author_handle is relay.

Replace:
```python
                elif (
                    platform == "twitter"
                    and role == "subject"
                    and author_handle is not None
                    and author_handle not in pid_to_handles.get(pid, set())
                ):
                    role = "mentioned"
```

With:
```python
                elif (
                    platform == "twitter"
                    and role == "subject"
                    and author_handle is not None
                    and author_handle not in relay_handles  # relay authors don't "own" their tweet's subject
                    and author_handle not in pid_to_handles.get(pid, set())
                ):
                    role = "mentioned"
```

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_ingest.py::test_link_relay_author_keeps_quoted_politician_as_subject -v`

Expected: PASS.

- [ ] **Step 5: Regression test — first-party downgrade still works**

Run: `python -m pytest tests/test_ingest.py::test_link_downgrades_subject_when_author_handle_does_not_match tests/test_ingest.py::test_link_keeps_subject_when_author_handle_matches tests/test_ingest.py::test_link_downgrades_even_when_author_is_tracked_non_match -v`

(Existing tests at lines 233-350 that exercise the downgrade path for non-relay authors.)

Expected: all PASS.

- [ ] **Step 6: Run full test_ingest.py**

Run: `python -m pytest tests/test_ingest.py -v`

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/ingest.py tests/test_ingest.py
git commit -m "$(cat <<'EOF'
feat(ingest): relay authors skip Twitter subject-downgrade

link_politicians_to_documents now precomputes relay_handles from
social_accounts.feed_type='relay'. When a Twitter doc's URL author
is a relay handle, quoted politicians keep their subject role
instead of being downgraded to 'mentioned'. This lets quoted
speakers reach the extraction queue via the normal subject-role
pending-politicians path.

For first-party Twitter accounts the downgrade still fires as
before — regression-tested.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Seed script — set `feed_type='relay'` for LTV, UPDATE existing row

**Files:**
- Modify: `scripts/seed_media_sources.py` (currently created earlier this session, does not yet set feed_type)

- [ ] **Step 1: Read current seed script to confirm structure**

Run: `cat scripts/seed_media_sources.py`

Expected: contains `MEDIA_SOURCES` list with one entry (LTV Ziņas), inserts into `tracked_politicians` + `social_accounts` with no feed_type field.

- [ ] **Step 2: Add `feed_type` field to MEDIA_SOURCES and propagate**

Replace the entire file contents (from `MEDIA_SOURCES = [` through the end) with:

```python
MEDIA_SOURCES = [
    {
        "name": "LTV Ziņas",
        "x_handle": "ltvzinas",
        "feed_type": "relay",
        "notes": "Latvijas Televīzijas ziņu dienesta oficiālais X konts. "
                 "Publicē ziņas ar politiķu citātiem — citāti jāekstraktē "
                 "kā first-party claims attiecīgajam politiķim (speaker_id=NULL), "
                 "nevis kā LTV komentāri. feed_type='relay' izlaiž autora-subject "
                 "junction link _store_tweets un atļauj citētajiem politiķiem "
                 "kļūt subject caur link_politicians_to_documents teksta skenēšanu.",
    },
]


def main() -> None:
    db = get_db()
    with db:
        for m in MEDIA_SOURCES:
            feed_type = m.get("feed_type", "first_party")

            existing = db.execute(
                "SELECT id, relationship_type FROM tracked_politicians WHERE name = ?",
                (m["name"],),
            ).fetchone()
            if existing:
                pid = existing["id"]
                if existing["relationship_type"] != "journalist":
                    db.execute(
                        "UPDATE tracked_politicians SET relationship_type = 'journalist' WHERE id = ?",
                        (pid,),
                    )
                    print(f"updated {m['name']} -> relationship_type=journalist (id={pid})")
                else:
                    print(f"skip {m['name']} — already journalist (id={pid})")
            else:
                db.execute(
                    "INSERT INTO tracked_politicians (name, relationship_type, x_handle, notes, created_at) "
                    "VALUES (?, 'journalist', ?, ?, ?)",
                    (m["name"], m["x_handle"], m["notes"], now_lv()),
                )
                pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"inserted {m['name']} (id={pid})")

            account = db.execute(
                "SELECT id, feed_type FROM social_accounts "
                "WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
                (pid, m["x_handle"]),
            ).fetchone()
            if account is None:
                db.execute(
                    "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
                    "VALUES (?, 'twitter', ?, 1, ?)",
                    (pid, m["x_handle"], feed_type),
                )
                print(f"  + social_accounts row for @{m['x_handle']} (feed_type={feed_type})")
            else:
                existing_ft = (account["feed_type"] or "first_party")
                if existing_ft != feed_type:
                    db.execute(
                        "UPDATE social_accounts SET feed_type = ? WHERE id = ?",
                        (feed_type, account["id"]),
                    )
                    print(f"  ~ @{m['x_handle']} feed_type: {existing_ft} -> {feed_type}")
                else:
                    print(f"  skip @{m['x_handle']} — social_accounts row exists (feed_type={feed_type})")


if __name__ == "__main__":
    main()
```

Leave the docstring and imports at the top of the file unchanged.

- [ ] **Step 3: Run seed script against the dev DB**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/seed_media_sources.py
```

Expected output (first time after schema patch):
```
skip LTV Ziņas — already journalist (id=170)
  ~ @ltvzinas feed_type: first_party -> relay
```

- [ ] **Step 4: Re-run to verify idempotency**

Run the same command again.

Expected:
```
skip LTV Ziņas — already journalist (id=170)
  skip @ltvzinas — social_accounts row exists (feed_type=relay)
```

- [ ] **Step 5: Verify DB state**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.db import get_db; db=get_db(); r=db.execute('SELECT handle, feed_type FROM social_accounts WHERE handle=\"ltvzinas\"').fetchone(); print(dict(r))"
```

Expected: `{'handle': 'ltvzinas', 'feed_type': 'relay'}`

- [ ] **Step 6: Commit**

```bash
git add scripts/seed_media_sources.py
git commit -m "$(cat <<'EOF'
feat(scripts): seed_media_sources sets feed_type='relay' for LTV

Idempotently UPDATEs existing social_accounts rows when feed_type
differs from the seed-declared value, so re-running the script
after the schema patch is all that's needed to migrate LTV.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Clean up pre-patch LTV test data

**Context:** The fetch test run during planning produced 17 LTV documents (IDs 23957-23973) with stale `(170, 'subject')` junction rows. Those rows were inserted before the schema+code changes and now incorrectly prevent `link_politicians_to_documents` from re-scanning the docs (the `LEFT JOIN dp WHERE dp IS NULL` guard excludes them).

We fix this by **deleting the stale LTV-subject junctions only for LTV-authored docs**, then running `link_politicians_to_documents(rescan_all=True, days=7)` so every such doc gets re-evaluated under the new relay logic.

**Files:** _none_ (operational — no code/test changes)

- [ ] **Step 1: Inspect candidate junction rows to delete**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db()
rows = db.execute('''
    SELECT dp.document_id, d.source_url
    FROM document_politicians dp
    JOIN documents d ON d.id = dp.document_id
    WHERE dp.politician_id = 170 AND dp.role = 'subject'
      AND d.source_url LIKE 'https://x.com/ltvzinas/%'
    ORDER BY dp.document_id
''').fetchall()
print(f'{len(rows)} LTV-subject junctions for ltvzinas-authored docs')
for r in rows[:5]:
    print(f'  doc={r[\"document_id\"]} url={r[\"source_url\"]}')
"
```

Expected: count ~17 (matches the pre-patch fetch). Verify all URLs start with `https://x.com/ltvzinas/`.

- [ ] **Step 2: Delete the stale subject junctions**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db()
with db:
    cur = db.execute('''
        DELETE FROM document_politicians
        WHERE politician_id = 170 AND role = 'subject'
          AND document_id IN (
              SELECT id FROM documents WHERE source_url LIKE 'https://x.com/ltvzinas/%'
          )
    ''')
    print(f'deleted {cur.rowcount} rows')
"
```

Expected: `deleted ~17 rows` (matches count from Step 1).

- [ ] **Step 3: Re-run link step with rescan_all to populate quoted politicians**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.ingest import link_politicians_to_documents
result = link_politicians_to_documents(days=7, rescan_all=True)
ltv_docs = {doc_id: pids for doc_id, pids in result.items() if pids}
print(f'linked {len(result)} docs total; non-empty matches: {len(ltv_docs)}')
"
```

Expected: output with non-zero linked counts. Actual counts depend on which of the 17 tweets contain tracked politician name matches (likely 3-6).

- [ ] **Step 4: Inspect resulting junction roles on former LTV-subject docs**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db()
rows = db.execute('''
    SELECT d.id, d.source_url,
           COALESCE(GROUP_CONCAT(tp.name || \":\" || dp.role, \" | \"), \"(no links)\") AS links
    FROM documents d
    LEFT JOIN document_politicians dp ON dp.document_id = d.id
    LEFT JOIN tracked_politicians tp ON tp.id = dp.politician_id
    WHERE d.source_url LIKE 'https://x.com/ltvzinas/%'
    GROUP BY d.id
    ORDER BY d.id
''').fetchall()
for r in rows:
    print(f'  doc={r[\"id\"]}: {r[\"links\"]}')
"
```

Expected: at least some docs now show `<Politician Name>:subject` (not LTV). Docs without politician mentions (crime news, international) will show `(no links)` — that's correct; they have nothing to extract.

- [ ] **Step 5: Confirm LTV no longer appears in pending extraction queue**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.analyze import get_pending_politicians
pending = get_pending_politicians(days=7)
ltv = [p for p in pending if p['id'] == 170]
print(f'LTV Ziņas in pending: {ltv}')
"
```

Expected: `LTV Ziņas in pending: []` (empty — LTV no longer has subject-role docs in its bucket).

- [ ] **Step 6: No commit for this task (operational-only — no file changes).**

If any file WAS changed by accident, stop and investigate before proceeding.

---

## Task 6: End-to-end smoke test

**Context:** Refetch LTV tweets to confirm the new pipeline stores them correctly from scratch. Since `last_post_id` cursor was not updated by the earlier raw fetch (which stored via old path), repeated fetches may hit cached/stored tweets — `insert_document` dedup will skip already-stored content hashes.

**Files:** _none_ (operational)

- [ ] **Step 1: Reset LTV `last_post_id` cursor to re-fetch the same window**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db()
with db:
    db.execute(\"UPDATE social_accounts SET last_post_id = NULL WHERE handle = 'ltvzinas'\")
print('reset cursor')
"
```

- [ ] **Step 2: Call fetch_twitter for LTV account id 94**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.social import fetch_twitter
posts = fetch_twitter(94)
print(f'fetched {len(posts)} posts')
"
```

Expected: `fetched N posts` where N ≤ 30 (ranges of tweets+replies). Most are deduped at `insert_document` (content hash collision) — that is fine. The ones that slip through the dedup create new docs with empty politician_links.

- [ ] **Step 3: Inspect junction roles for newly-inserted LTV docs**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db()
# Docs whose only junction source is from the new link step (no 170/subject)
rows = db.execute('''
    SELECT d.id, d.source_url,
           (SELECT GROUP_CONCAT(tp.name || \":\" || dp.role, \" | \")
              FROM document_politicians dp
              JOIN tracked_politicians tp ON tp.id = dp.politician_id
              WHERE dp.document_id = d.id) AS links
    FROM documents d
    WHERE d.source_url LIKE 'https://x.com/ltvzinas/%'
      AND d.scraped_at >= datetime('now','-1 day')
    ORDER BY d.id DESC LIMIT 10
''').fetchall()
for r in rows:
    print(f'  doc={r[\"id\"]}: {r[\"links\"] or \"(no links)\"}')
"
```

Expected: no row contains `LTV Ziņas:subject`. Rows either show quoted politicians with `subject` / `mentioned` roles, or `(no links)` for tweets without tracked politician names.

- [ ] **Step 4: Inspect pending extraction queue for a quoted politician**

Pick a politician who appears as subject of an LTV doc from Step 3 (e.g. if the output shows `Test Name:subject` at doc 23xxx, use that politician's name).

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.analyze import get_pending_politicians
pending = get_pending_politicians(days=7)
for p in pending:
    print(f\"  id={p['id']:4d} {p['name']:30s} docs={p['doc_count']}\")
" | head -20
```

Expected: at least one politician whose `doc_count` includes LTV docs. (Cross-check by inspecting their subject docs via the DB.)

- [ ] **Step 5: No commit (operational)**

---

## Task 7: CHANGELOG entry

**Files:**
- Modify: `wiki/CHANGELOG.md` (prepend new entry at top of 2026-04 section)

- [ ] **Step 1: Read CHANGELOG front matter + first entry to match style**

Run: `head -50 wiki/CHANGELOG.md`

Note the date-header format (e.g. `## 2026-04-23 — …`) and body conventions.

- [ ] **Step 2: Prepend the new entry**

Insert immediately after the CHANGELOG title/intro and above the first dated entry, using the same `## YYYY-MM-DD — <title>` format seen in the file:

```markdown
## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

Institutional media X accounts (LTV Ziņas; future Delfi, TVNET, LSM, ministriju konti) now ingest as `feed_type='relay'`. Effect:

- `src/social.py::_store_tweets` — skips the hardcoded `(opponent_id, 'subject')` junction link for relay accounts. Documents are inserted with empty `politician_links`.
- `src/ingest.py::link_politicians_to_documents` — precomputes `relay_handles`; when a Twitter doc's URL author is a relay handle, quoted tracked politicians keep their subject role instead of being downgraded to `'mentioned'`. Quoted speakers therefore reach the normal extraction queue via `get_pending_politicians()`.
- Claims extracted from relay-sourced docs remain first-party (`speaker_id=NULL`, `claim_type='position'`) of the quoted politician, with `source_url` pointing to the outlet tweet. `search_similar_claims` (default `speaker_scope='first_party'`) can contradict them against the politician's direct posts.

Behavior for `feed_type='first_party'` (default; all existing accounts) is unchanged: politician's own X, commentator, and individual-journalist accounts continue to mark the author as subject. The `relationship_type='commentator'` commentary path (added 2026-04-23) fires independently of feed_type and is unaffected.

Schema patch at `src/db.py::init_db`; seeded via `scripts/seed_media_sources.py` (UPDATE-on-differ for existing rows). Idempotent.
```

- [ ] **Step 3: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(wiki): CHANGELOG entry for social_accounts.feed_type

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Verification and finish

**Files:** _none_

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v 2>&1 | tail -40`

Expected: all tests pass (there may be pre-existing unrelated failures — note them but do not block on them unless caused by this plan's changes).

- [ ] **Step 2: Quote and verify the passing summary line**

Look for a line like `===== N passed in X.Xs =====` at the bottom of pytest output. Quote it in the finish message.

- [ ] **Step 3: Summarize branch state**

Run: `git log feat/komentetaji-speaker-id..HEAD --oneline`

Expected: 5 commits (Tasks 1, 2, 3, 4, 7) — Task 5 and 6 are operational, no commits.

- [ ] **Step 4: Report completion**

Tell the user:
- Branch name: `feat/relay-media-accounts`
- Number of commits, test-suite status line
- Whether any tests not related to this change already failed
- That LTV Ziņas is now seeded with `feed_type='relay'` and the pre-patch test docs have been cleaned up
- That the next daily routine `fetch_all_twitter()` will naturally pick up LTV tweets via the new path

Do not merge or PR without explicit user request.
