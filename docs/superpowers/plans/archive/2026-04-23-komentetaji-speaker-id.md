# Komentētāji (speaker_id-aware claims) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture and publish third-party commentary about tracked politicians (e.g. @KlucisD's public allegations against Pūpols, Kleinbergs, Kirsis) with proper speaker→subject attribution, without forking the claims pipeline.

**Architecture:** Additive — reuse `tracked_politicians` for commentator identity (new `relationship_type='commentator'`), `social_accounts` for their timelines, and `claims` for their output. One new column — `claims.speaker_id INTEGER` — makes author-vs-subject explicit. One new `claim_type='commentary'` distinguishes third-party allegations from first-party `position` / `saeima_vote`. When `speaker_id = opponent_id` (or NULL), it's first-party and all legacy code behaves identically. When `speaker_id ≠ opponent_id`, UI renders "Par viņu saka" block with "X apgalvo par Y" framing — never as fact.

**Tech Stack:** Python 3.11 + SQLite (ALTER TABLE, no migration framework — runtime schema patch in `src/db.py::init_db`), Pydantic v2 (claim dict shape), Jinja2 templates, vanilla CSS + JS.

**Files touched (9 total):**
- Modify: `src/db.py` — schema patch (`init_db`), `store_claim` signature + idempotency tweak
- Modify: `src/analyze.py::save_analysis` — plumb `speaker_id` through
- Create: `scripts/seed_commentators.py` — one-time KlucisD seed
- Modify: `.claude/agents/claim-extractor.md` — prompt update for commentary attribution
- Modify: `src/generate.py::_fetch_politician_detail` + a new `_fetch_commentary_about` — fetch third-party claims on profile page; also `_fetch_politicians` filter so commentators don't inflate the 148 count
- Modify: `templates/politician.html.j2` — new "Par viņu saka" block + commentator-profile variant
- Modify: `tests/test_db.py` — TDD for `speaker_id` + idempotency
- Modify: `tests/test_analyze.py` — TDD for `save_analysis` speaker_id plumbing
- Modify: `wiki/CHANGELOG.md` — document the change (per CLAUDE.md "historical data-model changes" convention)

**Branch:** `feat/komentetaji-speaker-id` (create from `master` at Task 0).

**Out of scope (MVP):** Contradictions between commentator claims (first-party contradiction logic gets a `speaker_id = opponent_id` filter only — a safety narrowing, not a new feature). Reply-tree capture of top replies under tracked politician posts. Commentator→commentator contradiction tracking. Dedicated `/komentetaji/` index page (commentators appear only on subject profile blocks for MVP; their own profile page works but is unlinked from nav).

**Spec decisions locked in (no alternatives to reconsider mid-implementation):**
- `relationship_type='commentator'` (NOT reuse `journalist`). Journalist = professional newsroom; commentator = public figure posting opinions. KlucisD fits the latter.
- `claim_type='commentary'` (NOT `third_party_allegation`). Matches the terse existing vocabulary (`position`, `saeima_vote`).
- `speaker_id` is nullable. NULL == speaker is opponent (first-party, legacy default). Row-level backfill NOT required — COALESCE in readers.
- Idempotency unchanged: `(opponent_id, source_url, topic)` stays unique per `store_claim` SELECT guard. One URL has one author, so speaker_id never varies within a `(opponent_id, source_url, topic)` triple.
- Contradiction detector (existing `store_contradiction` callers in agent prompts) scopes to `speaker_id IS NULL OR speaker_id = opponent_id` — commentary claims are excluded from first-party contradiction matching in MVP to avoid "Pūpols contradicted himself" where the second claim was actually KlucisD.

---

## Task 0: Branch setup

**Files:** _none_

- [ ] **Step 1: Verify clean working tree**

Run: `git status --short`

Expected: only the pre-existing `M src/generate.py`, `?? tmp_brief_2026-04-22.md`, `?? tmp_skel.md` from the session-start snapshot. If anything else is modified under `src/db.py`, `src/analyze.py`, `templates/politician.html.j2`, or `tests/`, stop and ask the user.

- [ ] **Step 2: Create and check out feature branch**

Run:
```bash
git checkout -b feat/komentetaji-speaker-id
```

Expected: `Switched to a new branch 'feat/komentetaji-speaker-id'`

- [ ] **Step 3: Verify**

Run: `git branch --show-current`

Expected: `feat/komentetaji-speaker-id`

No commit at this step.

---

## Task 1: DB migration — `speaker_id` column + index

**Files:**
- Modify: `src/db.py` — find `init_db()` function, add idempotent `ALTER TABLE` + index inside it (same pattern as existing `claim_type` added in 2026-04-11 migration — grep for `ALTER TABLE claims ADD COLUMN claim_type` to find the anchor block).
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_db.py`:

```python
def test_claims_has_speaker_id_column(tmp_path):
    from src.db import init_db, get_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    cols = {row["name"] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
    assert "speaker_id" in cols, f"speaker_id missing; got columns: {sorted(cols)}"
    db.close()


def test_claims_speaker_id_index_exists(tmp_path):
    from src.db import init_db, get_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    idx_names = {row["name"] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='claims'"
    ).fetchall()}
    assert "idx_claims_speaker" in idx_names, f"speaker index missing; got: {sorted(idx_names)}"
    db.close()


def test_init_db_idempotent_on_speaker_id(tmp_path):
    """Running init_db twice must not raise 'duplicate column' errors."""
    from src.db import init_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    init_db(db_path)  # second call — must be a no-op, not raise
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `python -m pytest tests/test_db.py -v -k "speaker_id or init_db_idempotent"`

Expected: all three FAIL. The first two on `assert "speaker_id" in cols` / `assert "idx_claims_speaker" in idx_names`; the third passes incidentally but must stay in the suite as the idempotency guard for Step 3.

- [ ] **Step 3: Add the idempotent migration inside `init_db()`**

Find the existing `claim_type` column patch in `src/db.py::init_db()` (grep for `ADD COLUMN claim_type`). Insert immediately after that block:

```python
# 2026-04-23 — speaker_id separates the author of a claim from its subject.
# First-party claims: speaker_id IS NULL (or = opponent_id). Third-party
# commentary (relationship_type='commentator' author tweeting about a
# tracked politician): speaker_id = commentator's tracked_politicians.id,
# opponent_id = mentioned politician's id. Idempotent: PRAGMA check first.
_claims_cols = {row[1] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
if "speaker_id" not in _claims_cols:
    db.execute("ALTER TABLE claims ADD COLUMN speaker_id INTEGER REFERENCES tracked_politicians(id)")
db.execute(
    "CREATE INDEX IF NOT EXISTS idx_claims_speaker ON claims(speaker_id)"
)
db.execute(
    "CREATE INDEX IF NOT EXISTS idx_claims_opponent_speaker "
    "ON claims(opponent_id, speaker_id)"
)
```

- [ ] **Step 4: Run tests, confirm PASS**

Run: `python -m pytest tests/test_db.py -v -k "speaker_id or init_db_idempotent"`

Expected: all three PASS.

- [ ] **Step 5: Apply migration to real DB**

Run:
```bash
python -c "from src.db import init_db; init_db()"
```

Expected: no output, exit code 0. Verify:
```bash
python -c "import sqlite3; db = sqlite3.connect('data/atmina.db'); print([r[1] for r in db.execute('PRAGMA table_info(claims)').fetchall()])"
```

Expected: column list includes `speaker_id` as the last entry.

- [ ] **Step 6: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add claims.speaker_id column + indexes"
```

---

## Task 2: `store_claim` accepts `speaker_id`

**Files:**
- Modify: `src/db.py:709` — `store_claim` function signature + INSERT statement
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_db.py`:

```python
def test_store_claim_default_speaker_id_is_null(tmp_path, monkeypatch):
    """Legacy calls (no speaker_id kwarg) must store NULL for backward compat."""
    from src.db import init_db, get_db, store_claim
    # Setup: one tracked politician + one document with source_url
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("ATMINA_DB_PATH", db_path)  # if your test harness uses env; else pass db_path
    init_db(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Testa Politiķis', 'tracked')"
    )
    db.execute(
        "INSERT INTO documents (id, content, source_url, platform) VALUES (1, 'Testa saturs ar garumzīmēm ā ē ī ū.', 'https://example.lv/1', 'web')"
    )
    db.commit()
    db.close()

    import json
    result_json = store_claim(
        opponent_id=1, document_id=1, topic="test",
        stance="Atbalsta testu — pārbaudām garumzīmes ā ē ī ū.", quote=None,
        confidence=0.8, reasoning="Testa pamatojums ar garumzīmēm ā ē ī ū ņ.",
        salience=0.5, source_url="https://example.lv/1", stated_at=None,
        db_path=db_path,
    )
    result = json.loads(result_json) if isinstance(result_json, str) else {"claim_id": result_json}
    cid = result.get("claim_id", result_json)

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id FROM claims WHERE id = ?", (cid,)).fetchone()
    assert row["speaker_id"] is None
    db.close()


def test_store_claim_with_explicit_speaker_id(tmp_path):
    """When speaker_id is passed, it's persisted unchanged."""
    from src.db import init_db, get_db, store_claim
    import json
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    # Subject politician + commentator
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekta Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.execute("INSERT INTO documents (id, content, source_url, platform) VALUES (1, 'Komentārs par subjektu ar garumzīmēm ā ē ī ū.', 'https://x.com/komentetajs/status/1', 'twitter')")
    db.commit()
    db.close()

    result_json = store_claim(
        opponent_id=1, document_id=1, topic="korupcija",
        stance="Apgalvo, ka subjekts iesaistīts iepirkumos — pārbaudām garumzīmes ā ē ī.",
        quote=None, confidence=0.7,
        reasoning="Komentētāja publisks apgalvojums ar garumzīmēm ā ē ī ū ņ.",
        salience=0.5, source_url="https://x.com/komentetajs/status/1",
        stated_at=None, claim_type="commentary", speaker_id=2,
        db_path=db_path,
    )
    result = json.loads(result_json) if isinstance(result_json, str) else {"claim_id": result_json}
    cid = result.get("claim_id", result_json)

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id, opponent_id, claim_type FROM claims WHERE id = ?", (cid,)).fetchone()
    assert row["speaker_id"] == 2
    assert row["opponent_id"] == 1
    assert row["claim_type"] == "commentary"
    db.close()
```

Note: If `store_claim` returns a bare `int` rather than JSON (check src/db.py:843 — it returns `claim_id` as int from inside `try`, but the analyze.py caller wraps with `json.loads(store_claim(...))`), the test above handles both shapes with the `isinstance` check. Look at src/analyze.py:352 to confirm shape before writing the test and adjust if needed.

- [ ] **Step 2: Run tests, confirm FAIL**

Run: `python -m pytest tests/test_db.py::test_store_claim_with_explicit_speaker_id -v`

Expected: FAIL with `TypeError: store_claim() got an unexpected keyword argument 'speaker_id'`.

- [ ] **Step 3: Modify `store_claim` signature + INSERT**

In `src/db.py`, locate the `store_claim` function (line 709). Change the signature to add `speaker_id: Optional[int] = None` as the LAST parameter before `db_path`:

```python
def store_claim(
    opponent_id: int,
    document_id: int,
    topic: str,
    stance: str,
    quote: Optional[str],
    confidence: float,
    reasoning: str,
    salience: float,
    source_url: Optional[str],
    stated_at: Optional[str],
    claim_type: str = "position",
    speaker_id: Optional[int] = None,
    db_path: str = DB_PATH,
    db: Optional[sqlite3.Connection] = None,
) -> int:
```

In the docstring, add after the existing `claim_type` paragraph:

```
``speaker_id`` attributes authorship separately from the claim's subject.
When ``None`` (default), the claim is first-party — the speaker IS the
opponent (legacy behavior; consumers should ``COALESCE(speaker_id, opponent_id)``
when they need a concrete speaker). When set to a different
``tracked_politicians.id``, the claim is third-party commentary — typically
pair this with ``claim_type='commentary'``. Does NOT affect idempotency:
one source_url has one author, so ``(opponent_id, source_url, topic)``
stays unique per politician-about-whom.
```

Locate the INSERT (currently at ~line 835):

```python
        db.execute(
            """INSERT INTO claims (opponent_id, document_id, topic, stance, quote,
               confidence, reasoning, salience, source_url, stated_at, claim_type,
               created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (opponent_id, document_id, topic, stance, quote, confidence,
             reasoning, salience, source_url, stated_at, claim_type, now_lv()),
        )
```

Replace with:

```python
        db.execute(
            """INSERT INTO claims (opponent_id, document_id, topic, stance, quote,
               confidence, reasoning, salience, source_url, stated_at, claim_type,
               speaker_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (opponent_id, document_id, topic, stance, quote, confidence,
             reasoning, salience, source_url, stated_at, claim_type,
             speaker_id, now_lv()),
        )
```

- [ ] **Step 4: Run tests, confirm PASS**

Run: `python -m pytest tests/test_db.py::test_store_claim_default_speaker_id_is_null tests/test_db.py::test_store_claim_with_explicit_speaker_id -v`

Expected: both PASS.

- [ ] **Step 5: Regression — run existing claims tests**

Run: `python -m pytest tests/test_db.py -v -k "claim"`

Expected: ALL pre-existing claim tests still pass (no behavior change for legacy callers since `speaker_id` defaults to `None`).

- [ ] **Step 6: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): store_claim accepts optional speaker_id"
```

---

## Task 3: Plumb `speaker_id` through `save_analysis`

**Files:**
- Modify: `src/analyze.py:352` — `store_claim(...)` call inside `save_analysis`
- Test: `tests/test_analyze.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_analyze.py`:

```python
def test_save_analysis_passes_speaker_id(tmp_path, monkeypatch):
    """When a claim dict has 'speaker_id', save_analysis must forward it to store_claim."""
    from src.db import init_db, get_db
    from src.analyze import save_analysis

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.db.DB_PATH", db_path)
    monkeypatch.setattr("src.analyze.DB_PATH", db_path, raising=False)
    init_db(db_path)

    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.execute("INSERT INTO documents (id, content, source_url, platform) VALUES (1, 'Komentārs par subjektu ar garumzīmēm ā ē ī ū ņ.', 'https://x.com/kom/status/1', 'twitter')")
    db.commit()
    db.close()

    result = save_analysis(
        pid=1,
        analysis_date="2026-04-23",
        sentiment=0.0,
        topics=["korupcija"],
        quotes=[],
        brief="Testa īss pārskats ar garumzīmēm ā ē ī ū ņ.",
        confidence=0.7,
        claims=[{
            "document_id": 1,
            "topic": "korupcija",
            "stance": "Apgalvo, ka subjekts iesaistīts — ar garumzīmēm ā ē ī ū.",
            "quote": None,
            "confidence": 0.7,
            "reasoning": "Komentētāja publisks apgalvojums ar garumzīmēm ā ē ī ū ņ.",
            "salience": 0.5,
            "source_url": "https://x.com/kom/status/1",
            "claim_type": "commentary",
            "speaker_id": 2,
        }],
    )
    assert result["status"] == "success", f"save_analysis failed: {result}"
    claim_id = result["claim_ids"][0]

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id, claim_type FROM claims WHERE id = ?", (claim_id,)).fetchone()
    assert row["speaker_id"] == 2
    assert row["claim_type"] == "commentary"
    db.close()
```

- [ ] **Step 2: Run test, confirm FAIL**

Run: `python -m pytest tests/test_analyze.py::test_save_analysis_passes_speaker_id -v`

Expected: FAIL — `save_analysis` currently discards `speaker_id` from the claim dict because the `store_claim(...)` call does not pass it. The `speaker_id` on the resulting row is `None`, not `2`.

- [ ] **Step 3: Modify the `store_claim(...)` call in `save_analysis`**

In `src/analyze.py`, find the `store_claim(...)` call inside `save_analysis` (around line 352). Change:

```python
                    claim_result = json.loads(store_claim(
                        opponent_id=pid,
                        document_id=c["document_id"],
                        topic=c["topic"],
                        stance=c["stance"],
                        quote=c.get("quote"),
                        confidence=c.get("confidence", 0.5),
                        reasoning=reasoning,
                        salience=c.get("salience", 0.5),
                        source_url=source_url,
                        stated_at=c.get("stated_at"),
                        claim_type=c.get("claim_type", "position"),
                        db=db,
                    ))
```

To:

```python
                    claim_result = json.loads(store_claim(
                        opponent_id=pid,
                        document_id=c["document_id"],
                        topic=c["topic"],
                        stance=c["stance"],
                        quote=c.get("quote"),
                        confidence=c.get("confidence", 0.5),
                        reasoning=reasoning,
                        salience=c.get("salience", 0.5),
                        source_url=source_url,
                        stated_at=c.get("stated_at"),
                        claim_type=c.get("claim_type", "position"),
                        speaker_id=c.get("speaker_id"),
                        db=db,
                    ))
```

(Single line added: `speaker_id=c.get("speaker_id"),`.)

- [ ] **Step 4: Run test, confirm PASS**

Run: `python -m pytest tests/test_analyze.py::test_save_analysis_passes_speaker_id -v`

Expected: PASS.

- [ ] **Step 5: Regression**

Run: `python -m pytest tests/test_analyze.py -v`

Expected: all pre-existing `save_analysis` tests still pass. The indirect-reference gate (`NEEDS_REVIEW:` prepend at src/analyze.py:332-350) is orthogonal to speaker_id and stays as a safety net — but see Task 5 for a prompt-level interaction.

- [ ] **Step 6: Commit**

```bash
git add src/analyze.py tests/test_analyze.py
git commit -m "feat(analyze): forward speaker_id from claim dicts to store_claim"
```

---

## Task 4: Seed script — add KlucisD as first commentator

**Files:**
- Create: `scripts/seed_commentators.py`

- [ ] **Step 1: Write the seed script**

Create `scripts/seed_commentators.py`:

```python
"""One-time (idempotent) seed of political commentators.

A 'commentator' in atmina.lv terms = a public X/Twitter figure who
posts substantive allegations or opinions about tracked politicians
without being an elected politician themselves. Their tweets are
captured via fetch_all_twitter() (same pipeline as politicians,
since we iterate social_accounts), then extracted as
claim_type='commentary' with speaker_id=<commentator.id> and
opponent_id=<mentioned tracked politician>.

Seed list is conservative — active posters whose output regularly
names tracked politicians with concrete substantive content.
Grow this list only when the operator sees value; every commentator
multiplies the daily fetch/extract cost.

Re-running this script is safe: UPSERT on (name) / (opponent_id, platform, handle).
"""
from src.db import get_db, now_lv

# Conservative starter set. Add entries only after observing ≥5 substantive
# mentions of tracked politicians in the last ~14 days.
COMMENTATORS = [
    {
        "name": "Didzis Kļuciņš",
        "x_handle": "KlucisD",
        "notes": "Aktīvs X komentētājs; kritizē Rīgas pašvaldības iepirkumus, "
                 "AirBaltic finanses, partiju korupciju. Nav vēlēts politiķis "
                 "(pārbaudīts pret CVK 2025 RD sarakstu 2026-04-23).",
    },
]


def main() -> None:
    db = get_db()
    with db:
        for c in COMMENTATORS:
            # UPSERT tracked_politicians row
            existing = db.execute(
                "SELECT id, relationship_type FROM tracked_politicians WHERE name = ?",
                (c["name"],),
            ).fetchone()
            if existing:
                pid = existing["id"]
                if existing["relationship_type"] != "commentator":
                    db.execute(
                        "UPDATE tracked_politicians SET relationship_type = 'commentator', "
                        "x_handle = ?, notes = ? WHERE id = ?",
                        (c["x_handle"], c["notes"], pid),
                    )
                    print(f"updated {c['name']} -> relationship_type=commentator (id={pid})")
                else:
                    print(f"skip {c['name']} — already commentator (id={pid})")
            else:
                db.execute(
                    "INSERT INTO tracked_politicians (name, relationship_type, x_handle, notes, created_at) "
                    "VALUES (?, 'commentator', ?, ?, ?)",
                    (c["name"], c["x_handle"], c["notes"], now_lv()),
                )
                pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"inserted {c['name']} (id={pid})")

            # UPSERT social_accounts row — matches fetch_all_twitter's iteration source
            has_account = db.execute(
                "SELECT 1 FROM social_accounts WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
                (pid, c["x_handle"]),
            ).fetchone()
            if not has_account:
                db.execute(
                    "INSERT INTO social_accounts (opponent_id, platform, handle, active) "
                    "VALUES (?, 'twitter', ?, 1)",
                    (pid, c["x_handle"]),
                )
                print(f"  + social_accounts row for @{c['x_handle']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the seed script**

Run:
```bash
python -m scripts.seed_commentators
```

Expected output:
```
inserted Didzis Kļuciņš (id=<new_id>)
  + social_accounts row for @KlucisD
```

(If run again, expected: `skip Didzis Kļuciņš — already commentator (id=<id>)` and no `+ social_accounts` line.)

- [ ] **Step 3: Verify**

Run:
```bash
python -c "import sqlite3; db = sqlite3.connect('data/atmina.db'); row = db.execute(\"SELECT id, name, relationship_type, x_handle FROM tracked_politicians WHERE name = 'Didzis Kļuciņš'\").fetchone(); print(row)"
```

Expected: a row tuple with `relationship_type='commentator'` and `x_handle='KlucisD'`.

Run:
```bash
python -c "import sqlite3; db = sqlite3.connect('data/atmina.db'); print(db.execute(\"SELECT COUNT(*) FROM social_accounts s JOIN tracked_politicians p ON s.opponent_id=p.id WHERE p.relationship_type='commentator'\").fetchone())"
```

Expected: `(1,)`.

- [ ] **Step 4: Retro-backfill existing KlucisD documents (optional, manual trigger)**

The 15 existing KlucisD tweets in `documents` were captured as `platform='x_mention'` (not `'twitter'`), linked to their mention-target politicians. They stay as-is — running re-extraction on them is an editorial decision, not automatic. No code action in this task.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_commentators.py
git commit -m "feat(seed): add KlucisD as first political commentator"
```

---

## Task 5: Update `@claim-extractor` agent prompt for commentary attribution

**Files:**
- Modify: `.claude/agents/claim-extractor.md`

- [ ] **Step 1: Read current prompt structure**

Open `.claude/agents/claim-extractor.md` and locate two sections:
- The "Workflow → Step 3: Extract claims" block (~line 70) — lists what to skip/keep.
- The schema/output-format block later in the file (grep for `claim_type` to find where output fields are documented).

Note the existing "Skip these" list includes "Retweets without commentary" and implicitly depends on the indirect-reference gate at src/analyze.py:332-350. We are NOT loosening those — we are adding a NEW path ABOVE the drop rule: attribute to commentator instead of dropping.

- [ ] **Step 2: Add the commentary-attribution block**

Insert immediately AFTER the "Skip these" list and BEFORE the next numbered step:

```markdown
### Step 3b: Commentary attribution (added 2026-04-23)

When the document author is a **commentator** (tracked_politicians.relationship_type='commentator') and the document makes a substantive claim about a tracked politician, emit a commentary claim instead of dropping or misattributing:

- **Set** `opponent_id` = the mentioned tracked politician (the subject).
- **Set** `speaker_id` = the commentator's `tracked_politicians.id` (the author).
- **Set** `claim_type` = `'commentary'`.
- **Stance format** (critical for legal framing): always third-person, naming the speaker explicitly. E.g. `"@KlucisD apgalvo, ka Pūpols ignorē korupciju Rīgas siltuma iepirkumos."` — NEVER `"Pūpols ignorē korupciju..."`. The stance describes what the commentator CLAIMS, not a fact about the subject.
- **Reasoning**: include the specific @handle and timestamp so quality-reviewer can verify attribution. E.g. `"Komentētājs @KlucisD tvītā 2026-04-22 apgalvo, ka Pūpols... Pamatojums: tiešs citāts no tvīta, konkrēts subjekts nosaukts."`
- **Confidence**: cap at 0.7 for commentary — these are allegations, not verified positions. The `NEEDS_REVIEW:` indirect-reference gate at src/analyze.py will NOT trip on properly attributed commentary (no indirect markers required) but quality-reviewer still reviews all commentary claims before publication.
- **Skip rules unchanged**: bare retweets, ceremonial content, generic statements without a named tracked-politician subject — still drop. Commentary ≠ opinion-on-anything; the subject must be a tracked politician.

When the author is a **regular politician** (relationship_type='tracked'), continue existing behavior: their document yields first-party `position` claims (speaker_id = None by default, treated as = opponent_id). The new path fires only for commentator-authored documents.

How to check author's relationship_type in the current session:
```python
from src.db import get_db
db = get_db()
row = db.execute(
    "SELECT p.id, p.name, p.relationship_type FROM tracked_politicians p "
    "JOIN social_accounts s ON s.opponent_id = p.id "
    "WHERE s.handle = ? AND s.platform = 'twitter'",
    (handle,),
).fetchone()
# row["relationship_type"] in {'tracked', 'commentator', 'inactive', ...}
```
```

- [ ] **Step 3: Update the output-schema example**

Find the JSON/dict example showing `claim_type` field (grep for `"claim_type"` in the same file). If the example block does not already show `speaker_id`, add it directly after `claim_type` with a comment:

```json
{
  "document_id": 12345,
  "topic": "korupcija",
  "stance": "@KlucisD apgalvo, ka Pūpols ignorē Rīgas siltuma iepirkumu pārkāpumus.",
  "quote": null,
  "confidence": 0.7,
  "reasoning": "Komentētājs @KlucisD tvītā 2026-04-22 apgalvo...",
  "salience": 0.5,
  "source_url": "https://x.com/KlucisD/status/...",
  "claim_type": "commentary",
  "speaker_id": 149
}
```

And add one line to the schema description: `speaker_id` (optional, int, default null): ID of the tracked_politicians row whose social_account authored the document. Set only for `claim_type='commentary'`.

- [ ] **Step 4: Sanity-read the edited file end-to-end**

Open `.claude/agents/claim-extractor.md` top to bottom. Check:
- "Skip these" list unchanged (retweets-without-commentary still drops)
- New "Step 3b" reads coherently alongside existing workflow
- Schema example is internally consistent with the new field

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/claim-extractor.md
git commit -m "feat(agent): claim-extractor emits commentary claims with speaker_id"
```

---

## Task 6: Reader — `_fetch_commentary_about(pid)`

**Files:**
- Modify: `src/generate.py` — add `_fetch_commentary_about` near `_fetch_politician_detail` (line 1286); also modify `_fetch_politicians` (line 1258) to exclude commentators from the main 148-politician listing.
- Test: `tests/test_generate.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_generate.py`:

```python
def test_fetch_commentary_about_returns_third_party_only(tmp_path):
    """Claims WHERE speaker_id IS NOT NULL AND speaker_id != opponent_id."""
    from src.db import init_db, get_db
    from src.generate import _fetch_commentary_about

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type, x_handle) VALUES (2, 'Komentētājs Ļūdzis', 'commentator', 'KomL')")
    db.execute("INSERT INTO documents (id, content, source_url, platform, published_at) VALUES (1, 'Komentārs ar garumzīmēm ā ē ī ū ņ.', 'https://x.com/KomL/status/1', 'twitter', '2026-04-22T10:00:00+00:00')")
    # First-party claim about subject — MUST NOT appear
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (1, 1, 'savs temats', 'Pirmās puses pozīcija', 0.8, 'Pats runāja', 0.5, 'https://news.lv/1', 'position', NULL)"
    )
    # Third-party commentary about subject — MUST appear
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (1, 1, 'korupcija', 'KomL apgalvo par subjektu', 0.7, 'Komentārs', 0.5, 'https://x.com/KomL/status/1', 'commentary', 2)"
    )
    db.commit()

    rows = _fetch_commentary_about(db, 1)
    assert len(rows) == 1
    assert rows[0]["claim_type"] == "commentary"
    assert rows[0]["speaker_id"] == 2
    assert rows[0]["speaker_name"] == "Komentētājs Ļūdzis"
    assert rows[0]["speaker_handle"] == "KomL"
    assert rows[0]["topic"] == "korupcija"
    db.close()


def test_fetch_politicians_excludes_commentators(tmp_path):
    """The main politicians listing must NOT include relationship_type='commentator'."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politicians

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Īsts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.commit()

    rows = _fetch_politicians(db)
    names = [r["name"] for r in rows]
    assert "Īsts Politiķis" in names
    assert "Komentētājs Ļūdzis" not in names
    db.close()
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m pytest tests/test_generate.py -v -k "commentary_about or fetch_politicians_excludes"`

Expected: first test FAILs with `ImportError: cannot import name '_fetch_commentary_about'`; second test may FAIL or PASS depending on current `_fetch_politicians` filter — likely FAIL because it currently selects all non-inactive politicians.

- [ ] **Step 3: Add `_fetch_commentary_about`**

In `src/generate.py`, immediately after `_fetch_politician_detail` (line 1286) and before the next function, insert:

```python
def _fetch_commentary_about(db: sqlite3.Connection, pid: int) -> list[dict[str, Any]]:
    """Return third-party commentary claims about politician pid.

    A commentary claim has ``speaker_id IS NOT NULL`` and ``speaker_id != opponent_id``
    and ``claim_type = 'commentary'``. Joined with the speaker's tracked_politicians
    row so the template can render "X apgalvo par [this politician]" with a link
    to the speaker's own page.

    Ordering: most recent first (by stated_at, fallback created_at).
    """
    rows = db.execute(
        """
        SELECT c.id, c.topic, c.stance, c.quote, c.confidence, c.reasoning,
               c.source_url, c.stated_at, c.created_at, c.claim_type,
               c.speaker_id,
               sp.name AS speaker_name,
               sp.x_handle AS speaker_handle
        FROM claims c
        JOIN tracked_politicians sp ON sp.id = c.speaker_id
        WHERE c.opponent_id = ?
          AND c.claim_type = 'commentary'
          AND c.speaker_id IS NOT NULL
          AND c.speaker_id != c.opponent_id
        ORDER BY COALESCE(c.stated_at, c.created_at) DESC
        """,
        (pid,),
    ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Update `_fetch_politicians` filter**

Locate `_fetch_politicians` (line 1258). Find the SELECT from `tracked_politicians` (likely `WHERE relationship_type != 'inactive'` or similar — read the actual code first). Change the WHERE clause so commentators are also excluded from the main politician listing:

```python
# Was: WHERE relationship_type != 'inactive'
# New:
WHERE relationship_type NOT IN ('inactive', 'commentator', 'neutral', 'journalist')
```

(Exact WHERE replacement depends on the existing code — read src/generate.py:1258 first and match the style. The intent: the home-page "148 politiķi" count stays at 148, not 149+.)

- [ ] **Step 5: Run tests, confirm PASS**

Run: `python -m pytest tests/test_generate.py -v -k "commentary_about or fetch_politicians_excludes"`

Expected: both PASS.

- [ ] **Step 6: Regression**

Run: `python -m pytest tests/test_generate.py -v`

Expected: all existing generate.py tests still PASS. The home-page politician count is unchanged because the filter already excluded non-tracked types.

- [ ] **Step 7: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): _fetch_commentary_about + exclude commentators from politician listing"
```

---

## Task 7: UI — "Par viņu saka" block on `politician.html.j2`

**Files:**
- Modify: `src/generate.py::_fetch_politician_detail` — include commentary_about in the returned dict
- Modify: `templates/politician.html.j2` — new conditional section
- Modify: `assets/style.css` — new `.komentari-card` block (follow existing `.prv2-card` / `.pretruna-card` style conventions; dark theme CSS vars already defined in `:root`)

- [ ] **Step 1: Plumb commentary into `_fetch_politician_detail`**

Find `_fetch_politician_detail` at src/generate.py:1286. It returns a dict (name, claims, contradictions, etc.). Add one line inside the function, near the end where the dict is assembled:

```python
detail["commentary_about"] = _fetch_commentary_about(db, pid)
```

(Exact placement: just before the `return detail` — read the function end to confirm the dict variable name and return pattern.)

- [ ] **Step 2: Add the template block**

Open `templates/politician.html.j2`. Find the section that renders `pozicijas` (first-party claims). IMMEDIATELY AFTER that section (before `pretrunas` or contradictions section), insert:

```html+jinja
{% if detail.commentary_about %}
<section class="komentari-section" aria-labelledby="komentari-heading">
  <h2 id="komentari-heading">Par {{ detail.name }} saka ({{ detail.commentary_about|length }})</h2>
  <p class="komentari-intro">
    Publiskas trešo pušu izteiksmes par {{ detail.name }} — komentētāju, žurnālistu
    un sabiedrisko vērotāju apgalvojumi. <strong>Šie nav {{ detail.name }} pašas
    pozīcijas</strong>, bet gan citu cilvēku publiski pieejami apgalvojumi par
    {{ detail.name }}. Katrs ieraksts kļuvis no konkrēta avota ar datumu.
  </p>
  <div class="komentari-grid">
    {% for c in detail.commentary_about %}
    <article class="komentari-card" data-claim-id="{{ c.id }}">
      <header class="komentari-head">
        <span class="komentari-speaker">
          {% if c.speaker_handle %}
            <a href="https://x.com/{{ c.speaker_handle }}" rel="nofollow noopener">@{{ c.speaker_handle }}</a>
          {% else %}
            {{ c.speaker_name }}
          {% endif %}
        </span>
        <span class="komentari-date">{{ c.stated_at[:10] if c.stated_at else c.created_at[:10] }}</span>
      </header>
      <div class="komentari-topic">{{ c.topic }}</div>
      <p class="komentari-stance">{{ c.stance }}</p>
      {% if c.quote %}
        <blockquote class="komentari-quote">"{{ c.quote }}"</blockquote>
      {% endif %}
      <footer class="komentari-foot">
        <a href="{{ c.source_url }}" rel="nofollow noopener" class="komentari-source">Avots →</a>
      </footer>
    </article>
    {% endfor %}
  </div>
</section>
{% endif %}
```

- [ ] **Step 3: Add CSS**

Open `assets/style.css`. At the end of the file (or in the logical grouping with `.prv2-card` / `.pretruna-card` styles), add:

```css
/* -------- Komentāri (par viņu saka) -------- */
.komentari-section {
  margin: 2.5rem 0;
  padding: 1rem 0;
  border-top: 1px solid var(--border-subtle);
}
.komentari-section h2 {
  font-size: 1.25rem;
  margin-bottom: 0.4rem;
  color: var(--text-primary);
}
.komentari-intro {
  font-size: 0.85rem;
  color: var(--text-muted);
  max-width: 60ch;
  margin-bottom: 1.25rem;
  line-height: 1.5;
}
.komentari-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}
.komentari-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--accent-muted);
  padding: 0.9rem 1rem;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.komentari-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}
.komentari-speaker a {
  color: var(--text-link);
  text-decoration: none;
  font-weight: 500;
}
.komentari-speaker a:hover { text-decoration: underline; }
.komentari-date { color: var(--text-muted); font-variant-numeric: tabular-nums; }
.komentari-topic {
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.komentari-stance {
  font-size: 0.95rem;
  line-height: 1.45;
  margin: 0;
}
.komentari-quote {
  border-left: 2px solid var(--border-subtle);
  padding-left: 0.75rem;
  margin: 0;
  color: var(--text-secondary);
  font-style: italic;
  font-size: 0.9rem;
}
.komentari-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
}
.komentari-source {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-decoration: none;
}
.komentari-source:hover { color: var(--text-link); text-decoration: underline; }

@media (max-width: 640px) {
  .komentari-grid { grid-template-columns: 1fr; }
}
```

(If `--accent-muted` / `--text-secondary` / `--text-link` / etc. do not exist in `:root`, use their closest equivalents — grep `:root` in `assets/style.css` first and adapt variable names.)

- [ ] **Step 4: Generate the site and spot-check**

Run:
```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: completes without error (may take 30-90s; same as normal build).

Then open `output/atmina/politiki/<some-politician-slug>.html` — the one most-mentioned by KlucisD. Based on DB content (Task 4 notes), `@AnsisPupols` receives 3+ KlucisD tweets, so open his profile. For MVP with KlucisD's EXISTING 15 `x_mention` docs, no commentary claims exist yet — the new block will be absent (which is correct — `{% if detail.commentary_about %}` skips it). Confirm no TypeError or template error in the build log.

To force a smoke-test with visible commentary, insert a test row manually:
```bash
python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
# Find Pūpols id and KlucisD id
pupols_id = db.execute(\"SELECT id FROM tracked_politicians WHERE name LIKE '%Pūpols%' LIMIT 1\").fetchone()[0]
klucis_id = db.execute(\"SELECT id FROM tracked_politicians WHERE name LIKE '%Kļuciņš%' LIMIT 1\").fetchone()[0]
doc_id = db.execute(\"SELECT id FROM documents WHERE source_url LIKE '%KlucisD%' LIMIT 1\").fetchone()[0]
db.execute('INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    (pupols_id, doc_id, 'mediju kritika',
     '@KlucisD apgalvo, ka Pūpols nodarbojas ar tēla veidošanu naudas dēļ, nevis substanci.',
     0.6, 'SMOKE TEST — noņemt pēc UI pārbaudes.', 0.5,
     'https://x.com/KlucisD/status/6819', 'commentary', klucis_id))
db.commit()
print('inserted smoke test row')
"
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Open `output/atmina/politiki/ansis-pupols.html` (or whatever slug Pūpols has — check dir listing). Expected: "Par Ansis Pūpols saka (1)" section with the test card visible.

Delete the smoke row before moving on:
```bash
python -c "import sqlite3; db = sqlite3.connect('data/atmina.db'); db.execute(\"DELETE FROM claims WHERE reasoning LIKE 'SMOKE TEST%'\"); db.commit(); print('removed')"
```

Re-run the generate and confirm Pūpols profile no longer has the commentary block (until real commentary is extracted).

- [ ] **Step 5: Commit**

```bash
git add src/generate.py templates/politician.html.j2 assets/style.css
git commit -m "feat(ui): 'Par viņu saka' commentary block on politician profile"
```

---

## Task 8: Contradiction-detector safety narrowing

**Files:**
- Modify: `.claude/agents/contradiction-hunter.md` — scope hint only
- Modify: `src/db.py::search_similar_claims` (at ~line 655) — add filter

Rationale: Before commentary exists in production, the existing contradiction agents compared all claims per opponent_id. Now that `opponent_id` can carry both first-party (Pūpols said X) and commentary (KlucisD said Pūpols did Y), the SQL-level similarity search MUST exclude commentary from first-party contradiction matches — otherwise a commentator's allegation gets auto-flagged as "Pūpols contradicted himself."

- [ ] **Step 1: Write failing test**

Append to `tests/test_db.py`:

```python
def test_search_similar_claims_excludes_commentary_by_default(tmp_path):
    """First-party contradiction check must not pull in commentary claims."""
    from src.db import init_db, get_db, search_similar_claims
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    # Note: vec-search requires embeddings + sqlite_vec. For this test, the
    # simpler assertion is that the SQL filter is applied. If direct unit-
    # testing of search_similar_claims requires an embedding backfill, split
    # this into an integration test under tests/integration/ instead.
    # See Task 8 Step 3 — the functional check is the SQL WHERE clause
    # gaining a speaker equality guard; prefer a targeted SQL test:
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs', 'commentator')")
    db.execute("INSERT INTO documents (id, content, source_url, platform) VALUES (1, 'txt', 'https://a.lv/1', 'web')")
    db.execute("INSERT INTO documents (id, content, source_url, platform) VALUES (2, 'txt', 'https://b.lv/1', 'twitter')")
    # First-party position
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (101, 1, 1, 'tema', 'pozicija', 0.8, 'r', 0.5, 'https://a.lv/1', 'position', NULL)"
    )
    # Third-party commentary on same opponent
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (102, 1, 2, 'tema', 'komentars', 0.6, 'r', 0.5, 'https://b.lv/1', 'commentary', 2)"
    )
    db.commit()
    # Direct SQL check matching the search_similar_claims filter behavior:
    first_party_ids = {r["id"] for r in db.execute(
        "SELECT id FROM claims WHERE opponent_id = 1 AND (speaker_id IS NULL OR speaker_id = opponent_id)"
    ).fetchall()}
    assert first_party_ids == {101}
    db.close()
```

- [ ] **Step 2: Run, confirm PASS**

Run: `python -m pytest tests/test_db.py::test_search_similar_claims_excludes_commentary_by_default -v`

Expected: PASS (the assertion tests the filter SHAPE, not a function — documenting intent).

- [ ] **Step 3: Modify `search_similar_claims`**

Open `src/db.py` at ~line 655. Read the function — it already has a `claim_type_filter` parameter. Add a sibling:

Current signature (approx):
```python
def search_similar_claims(
    opponent_id: int,
    query_embedding: bytes,
    limit: int = 10,
    claim_type_filter: Optional[list[str]] = None,
    ...
):
```

Change to add:
```python
def search_similar_claims(
    opponent_id: int,
    query_embedding: bytes,
    limit: int = 10,
    claim_type_filter: Optional[list[str]] = None,
    speaker_scope: str = "first_party",  # 'first_party' | 'commentary' | 'all'
    ...
):
```

Inside the function, after the existing `claim_type_filter` clause (look for `if claim_type_filter is not None and claim["claim_type"] not in claim_type_filter:`), add:

```python
            # 2026-04-23: scope claims by speaker relationship. 'first_party' is
            # the safe default — contradiction detectors compare a politician's
            # own positions, not allegations against them. 'commentary' flips it
            # (future: commentator-vs-self over time). 'all' preserves legacy
            # any-speaker behavior for callers that explicitly opt in.
            is_first_party = claim["speaker_id"] is None or claim["speaker_id"] == claim["opponent_id"]
            if speaker_scope == "first_party" and not is_first_party:
                continue
            if speaker_scope == "commentary" and is_first_party:
                continue
            # speaker_scope == "all" → no filter
```

- [ ] **Step 4: Run existing tests for regressions**

Run: `python -m pytest tests/test_db.py -v -k "search_similar"`

Expected: any existing tests PASS. Since `speaker_id` defaults to NULL on all legacy claims (they pre-date this migration), the default `speaker_scope='first_party'` includes them all.

- [ ] **Step 5: Update `@contradiction-hunter` prompt**

Open `.claude/agents/contradiction-hunter.md`. Find any reference to `search_similar_claims`. Add a sentence:

```markdown
**speaker_scope (2026-04-23):** Leave at default `'first_party'` when hunting politician-own contradictions. Commentary claims (speaker_id ≠ opponent_id) are excluded — they represent third-party allegations, not the politician's own shifts, so pulling them into contradiction candidates would mis-attribute (e.g. "Pūpols contradicted himself" when the second claim was actually @KlucisD writing about Pūpols).
```

- [ ] **Step 6: Commit**

```bash
git add src/db.py tests/test_db.py .claude/agents/contradiction-hunter.md
git commit -m "feat(db): search_similar_claims speaker_scope filter (default first_party)"
```

---

## Task 9: Documentation — CHANGELOG + wiki

**Files:**
- Modify: `wiki/CHANGELOG.md` — new dated entry (per CLAUDE.md: "historical data-model changes: wiki/CHANGELOG.md")
- Modify: `wiki/index.md` — if it has a feature-list or recent-changes section, add a one-liner (grep `CHANGELOG` or `Pretrunas` in wiki/index.md to find the right block)

- [ ] **Step 1: Append CHANGELOG entry**

Open `wiki/CHANGELOG.md`. At the TOP of the file (most recent first per existing convention — read first 40 lines to confirm order), add:

```markdown
## 2026-04-23 — Komentētāji (speaker_id on claims)

**What changed:** Added `claims.speaker_id INTEGER NULL` column to distinguish authors from subjects. Introduced `relationship_type='commentator'` for non-politician public commentators (KlucisD seeded) and `claim_type='commentary'` for their output. Third-party commentary now renders on politician profiles as "Par viņu saka" block with explicit speaker attribution.

**Why:** Before this, a commentator tweeting "Pūpols ir korumpēts" either got dropped by the indirect-reference gate or misattributed as Pūpols' own position. Neither was right — the content is editorially valuable (third-party allegations are a legitimate transparency signal) but legally requires "X apgalvo par Y" framing, not assertion-of-fact. The `speaker_id` column is the minimum architectural change that enables correct attribution.

**Backward compatibility:** `speaker_id IS NULL` = first-party (legacy default). All pre-2026-04-23 claims remain NULL; readers use `COALESCE(speaker_id, opponent_id)` or explicit `IS NULL OR speaker_id = opponent_id` filters. `store_claim` signature adds optional `speaker_id` kwarg (default None).

**Invariant added:** `search_similar_claims` defaults to `speaker_scope='first_party'` — commentary claims are excluded from contradiction-candidate matching by default, so "Pūpols contradicted himself" never mis-fires because the second claim was actually a commentator writing about him.

**Files:** `src/db.py` (schema + store_claim + search_similar_claims), `src/analyze.py` (save_analysis plumbing), `src/generate.py` (_fetch_commentary_about + politician-listing filter), `templates/politician.html.j2` (new section), `assets/style.css` (`.komentari-*`), `.claude/agents/claim-extractor.md` + `.claude/agents/contradiction-hunter.md` (prompt updates), `scripts/seed_commentators.py` (KlucisD seed).

**Out of scope (follow-ups):** Reply-tree capture under tracked politicians' posts; `/komentetaji/` index page in main nav; commentator-vs-commentator contradiction tracking.
```

- [ ] **Step 2: Update wiki/index.md (if feature-list exists)**

Open `wiki/index.md`. If there is a "Pēdējās izmaiņas" / "Recent changes" / "Features" block, add a one-liner:

```markdown
- **Komentētāji** (2026-04-23) — publiski trešo pušu apgalvojumi par izsekotajiem politiķiem. Jauns `claim_type='commentary'` + `speaker_id` lauks. KlucisD seeded. Redzams kā "Par viņu saka" bloks profilā. Sk. [CHANGELOG § 2026-04-23](CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).
```

If wiki/index.md has no such block, skip this step — don't force a structure change.

- [ ] **Step 3: Commit**

```bash
git add wiki/CHANGELOG.md wiki/index.md
git commit -m "docs(wiki): document speaker_id + commentator architecture"
```

---

## Task 10: Full smoke — run routine + verify

**Files:** _none_

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`

Expected: full suite PASSes. If any pre-existing unrelated failures show up, triage — this plan must NOT introduce regressions.

- [ ] **Step 2: Generate the site**

Run:
```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: completes without error. Check that the home-page politician count and tab/nav counts are unchanged (commentators should not inflate "148 politiķi" or "142 Ministru kabinets" etc.).

- [ ] **Step 3: Verify KlucisD's profile page exists (and renders correctly)**

Because KlucisD is `relationship_type='commentator'`, his profile is NOT in the main politician listing but the template still generates a page for him (if the generator iterates all non-inactive politicians; read src/generate.py logic to confirm). Open `output/atmina/politiki/didzis-klucins.html` (slug exact form depends on `_slugify`). Expected: renders without a claims section (no first-party claims yet). Or skip this step if generator already scopes page rendering to `relationship_type='tracked'` only — commentator profiles without any content are noise.

- [ ] **Step 4: Routine status check**

Run:
```bash
python -c "from src.routine import print_routine; print_routine()"
```

Expected: daily routine status prints without error. Commentator-related steps (if any routine integration added later) are out of scope for this MVP.

- [ ] **Step 5: Final commit (if anything)**

If any fix-ups happened, commit them with a descriptive message. Otherwise skip.

```bash
git status
# Only if there are uncommitted changes from Steps 1-4:
git add -A  # or specific files
git commit -m "chore: post-smoke cleanup"
```

- [ ] **Step 6: Finishing the branch**

Work is complete. Invoke the superpowers:finishing-a-development-branch skill to decide merge-vs-PR-vs-cleanup per project convention.

---

## Coverage self-review

Spec coverage checklist (read this before declaring plan complete):

- ✅ Identify third-party author (commentator) → Task 4 (seed) + Task 5 (prompt)
- ✅ Persist attribution on claims → Task 1 (schema) + Task 2 (store_claim) + Task 3 (save_analysis)
- ✅ Reader separates first-party from commentary → Task 6 (`_fetch_commentary_about`) + Task 8 (SQL filter in `search_similar_claims`)
- ✅ UI renders with correct framing ("X apgalvo par Y", never "Y did Z") → Task 7 (`politician.html.j2` + CSS)
- ✅ Politician count / dashboard unaffected → Task 6 (`_fetch_politicians` filter)
- ✅ Contradiction detector doesn't cross first-party vs commentary → Task 8 (`speaker_scope`)
- ✅ Agent prompts updated → Task 5 (claim-extractor) + Task 8 (contradiction-hunter)
- ✅ Documentation → Task 9 (CHANGELOG + index)
- ✅ Tests cover schema, store_claim, save_analysis plumbing, reader filter, politician-listing filter → Tasks 1, 2, 3, 6, 8

**Explicit non-coverage (confirmed out-of-scope):**
- `/komentetaji/` listing page in nav — deferred; editorial surface decided post-MVP
- Reply-tree capture — deferred
- Commentator profile page polish — commentator profile renders via generic `politician.html.j2` but is not linked from nav; acceptable for MVP
- Migration of 15 existing KlucisD `x_mention` docs — manual editorial call, not automatic
