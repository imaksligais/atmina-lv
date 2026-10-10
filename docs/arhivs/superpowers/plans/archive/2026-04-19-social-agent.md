# Social Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a manually-triggered CLI agent that surfaces top-3 post candidates from atmina.lv data (pretrunas / weekly stats / analīžu highlights), sends drafts to the operator on Telegram with a rendered image, and publishes approved drafts to `@atmina_lv` via twikit.

**Architecture:** New `src/social_agent/` Python package with clear module boundaries: `candidates` (SQL queries + interest score), `drafters` (text templates per pillar), `visuals` (chart / quote-card / illustration renderers), `publisher` (twikit), `telegram` (direct Bot API via httpx), `storage` (DB CRUD), `cli` (argparse entry points). State lives in a new `social_drafts` SQLite table registered in `src/db.py::init_db()`. No webhook, no public-site integration, no operator dashboard — flow is: `brainstorm` CLI → Telegram preview → reply command → `approve/skip/revise` CLI → tweet.

**Tech Stack:** Python 3.11+, SQLite (WAL) via `init_db()` migrations, twikit (posting), httpx (Telegram Bot API), matplotlib (charts), Playwright (HTML→PNG), existing `src/graphics/nanobanana.py` (illustrations), pytest.

**Spec:** `docs/superpowers/specs/2026-04-19-social-agent-design.md`

**Branch:** `master` (commit per task, no feature branch for MVP).

---

## Phase 1 — Foundation

### Task 1: Register `social_drafts` table in `init_db()`

**Files:**
- Modify: `src/db.py` (inside `init_db()`, after `political_tensions` block ~line 184)
- Test: `tests/test_db.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
class TestSocialDraftsTable:
    """Schema migration — social_drafts table for the X posting agent."""

    def test_social_drafts_columns_present(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            cols = {r[1]: r for r in db.execute("PRAGMA table_info(social_drafts)").fetchall()}
            for name in (
                "id", "pillar", "text", "image_path", "source_data_json",
                "score", "status", "telegram_msg_id", "telegram_chat_id",
                "revision_count", "parent_draft_id",
                "created_at", "posted_at", "tweet_id", "error_message",
            ):
                assert name in cols, f"social_drafts missing column {name}"
            # Indexes
            idx_names = {r[1] for r in db.execute(
                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='social_drafts'"
            ).fetchall()}
            assert "idx_social_drafts_status" in idx_names
            assert "idx_social_drafts_pillar" in idx_names
            db.close()
        finally:
            _safe_unlink(path)

    def test_social_drafts_idempotent(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            init_db(path)  # must not raise
            db = get_db(path)
            cnt = db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='social_drafts'"
            ).fetchone()[0]
            assert cnt == 1
            db.close()
        finally:
            _safe_unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/activate && python -m pytest tests/test_db.py::TestSocialDraftsTable -v
```

Expected: both tests FAIL — table does not exist.

- [ ] **Step 3: Add table DDL to `init_db()`**

In `src/db.py`, inside the `db.executescript(""" ... """)` block, immediately after the `political_tensions` `CREATE TABLE` (around line 184), insert:

```sql
        CREATE TABLE IF NOT EXISTS social_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pillar TEXT NOT NULL CHECK(pillar IN ('pretrunas', 'stats', 'highlights')),
            text TEXT NOT NULL,
            image_path TEXT,
            source_data_json TEXT NOT NULL,
            score REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'approved', 'rejected', 'revising', 'posted', 'failed')),
            telegram_msg_id TEXT,
            telegram_chat_id TEXT,
            revision_count INTEGER NOT NULL DEFAULT 0,
            parent_draft_id INTEGER REFERENCES social_drafts(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            posted_at TIMESTAMP,
            tweet_id TEXT,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_social_drafts_status ON social_drafts(status);
        CREATE INDEX IF NOT EXISTS idx_social_drafts_pillar ON social_drafts(pillar);
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_db.py::TestSocialDraftsTable -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add social_drafts table for X posting agent"
```

---

### Task 2: Add new credential keys and create data directory

**Files:**
- Modify: `src/credentials.py` (KNOWN_KEYS list)
- Create: `data/social/drafts/.gitkeep`
- Modify: `.gitignore` (add `data/social/drafts/*.png`)

- [ ] **Step 1: Add keys to `KNOWN_KEYS`**

In `src/credentials.py`, extend `KNOWN_KEYS` list:

```python
KNOWN_KEYS = [
    "x_username",
    "x_email",
    "x_password",
    "dashboard_password",
    "session_secret",
    "youtube_api_key",
    "facebook_page_token",
    "anthropic_api_key",
    "watchdog_smtp_host",
    "watchdog_smtp_user",
    "watchdog_smtp_pass",
    "watchdog_alert_to",
    "backup_target_path",
    # social_agent
    "telegram_bot_token",
    "telegram_operator_chat_id",
    "x_atmina_cookies_path",
]
```

- [ ] **Step 2: Create data directory placeholder**

```bash
mkdir -p data/social/drafts && touch data/social/drafts/.gitkeep
```

- [ ] **Step 3: Extend `.gitignore`**

Append to `.gitignore`:

```
# social agent draft images
data/social/drafts/*.png
data/x_cookies_atmina.json
```

- [ ] **Step 4: Verify credentials can be checked**

```bash
.venv/Scripts/activate && python -m src.credentials check
```

Expected output includes the three new keys as `NOT SET` (they will be populated manually before the first `brainstorm` run).

- [ ] **Step 5: Commit**

```bash
git add src/credentials.py .gitignore data/social/drafts/.gitkeep
git commit -m "chore(social-agent): register credentials and drafts directory"
```

---

### Task 3: Create package skeleton with explicit stub imports

**Files:**
- Create: `src/social_agent/__init__.py`
- Create: `src/social_agent/candidates.py`
- Create: `src/social_agent/drafters.py`
- Create: `src/social_agent/visuals.py`
- Create: `src/social_agent/publisher.py`
- Create: `src/social_agent/telegram.py`
- Create: `src/social_agent/storage.py`
- Create: `src/social_agent/cli.py`
- Create: `src/social_agent/__main__.py`
- Create: `tests/social_agent/__init__.py`

- [ ] **Step 1: Create stubs that fail loudly**

Each module starts as:

```python
# src/social_agent/candidates.py
"""Candidate selection + interest score ranking."""
```

```python
# src/social_agent/drafters.py
"""Pillar-specific text templates (≤280 chars)."""
```

```python
# src/social_agent/visuals.py
"""Three renderers: chart / quote_card / illustration → PNG files."""
```

```python
# src/social_agent/publisher.py
"""twikit wrapper — posts drafts to @atmina_lv."""
```

```python
# src/social_agent/telegram.py
"""Telegram Bot API wrapper (httpx, no MCP dependency)."""
```

```python
# src/social_agent/storage.py
"""social_drafts table CRUD: create / fetch / mark_* transitions."""
```

```python
# src/social_agent/cli.py
"""CLI entry points: brainstorm, approve, skip, revise, resend."""
```

```python
# src/social_agent/__init__.py
"""Social agent — draft posts for @atmina_lv, approved via Telegram."""
```

```python
# src/social_agent/__main__.py
from src.social_agent.cli import main

if __name__ == "__main__":
    main()
```

```python
# tests/social_agent/__init__.py
```

- [ ] **Step 2: Smoke test the package is importable**

```bash
.venv/Scripts/activate && python -c "import src.social_agent; import src.social_agent.candidates; import src.social_agent.drafters; import src.social_agent.visuals; import src.social_agent.publisher; import src.social_agent.telegram; import src.social_agent.storage; import src.social_agent.cli; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/social_agent/ tests/social_agent/
git commit -m "feat(social-agent): package skeleton"
```

---

## Phase 2 — Interest score + candidate queries

### Task 4: Interest score function

**Files:**
- Modify: `src/social_agent/candidates.py`
- Create: `tests/social_agent/test_candidates_score.py`

- [ ] **Step 1: Write failing tests**

`tests/social_agent/test_candidates_score.py`:

```python
from datetime import datetime, timedelta

from src.social_agent.candidates import interest_score


def test_interest_score_all_max():
    score = interest_score(
        salience=1.0,
        severity="critical",
        age_hours=0,
        candidate_topics={"a", "b"},
        recent_topics=set(),
    )
    assert abs(score - 1.0) < 0.001


def test_interest_score_all_zero():
    score = interest_score(
        salience=0.0,
        severity="none",
        age_hours=9999,
        candidate_topics=set(),
        recent_topics=set(),
    )
    # freshness clamps to 0; novelty with empty jaccard denominator → 1 by convention
    # salience 0 + severity 0 + freshness 0 + novelty 0.2 = 0.2
    # (empty candidate set has no overlap → novelty is 1.0; 0.2 * 1.0 = 0.2)
    assert abs(score - 0.2) < 0.001


def test_interest_score_severity_mapping():
    kw = dict(salience=0.0, age_hours=0, candidate_topics=set(), recent_topics=set())
    # freshness=1.0, novelty=1.0 → base = 0.4
    # severity_norm: critical=1.0 → +0.3 = 0.7
    assert abs(interest_score(severity="critical", **kw) - 0.7) < 0.001
    assert abs(interest_score(severity="major", **kw) - (0.4 + 0.3 * 0.7)) < 0.001
    assert abs(interest_score(severity="minor", **kw) - (0.4 + 0.3 * 0.4)) < 0.001
    assert abs(interest_score(severity="none", **kw) - 0.4) < 0.001
    # unknown → 0.6 default (treated as "default" for non-pretrunas pillars)
    assert abs(interest_score(severity=None, **kw) - (0.4 + 0.3 * 0.6)) < 0.001


def test_interest_score_freshness_decays_linearly():
    kw = dict(salience=0.0, severity="none", candidate_topics=set(), recent_topics=set())
    # freshness = max(0, 1 - age_hours/168)
    # age=0 → 1.0, age=84 → 0.5, age=168 → 0.0, age=200 → 0.0
    assert abs(interest_score(age_hours=0, **kw) - 0.4) < 0.001       # 0.2*1 + novelty 0.2
    assert abs(interest_score(age_hours=84, **kw) - 0.3) < 0.001      # 0.2*0.5 + 0.2
    assert abs(interest_score(age_hours=168, **kw) - 0.2) < 0.001     # 0 + 0.2
    assert abs(interest_score(age_hours=200, **kw) - 0.2) < 0.001     # clamp


def test_interest_score_novelty_jaccard():
    kw = dict(salience=0.0, severity="none", age_hours=0)
    # Full overlap → novelty 0 → base 0.2 (freshness only)
    s = interest_score(candidate_topics={"a", "b"}, recent_topics={"a", "b"}, **kw)
    assert abs(s - 0.2) < 0.001
    # Half overlap → jaccard = 1/3 → novelty = 2/3 → 0.2 + 0.2*(2/3)
    s = interest_score(candidate_topics={"a", "b"}, recent_topics={"a", "c"}, **kw)
    assert abs(s - (0.2 + 0.2 * (2/3))) < 0.01
```

- [ ] **Step 2: Run tests — expect FAIL (function not defined)**

```bash
python -m pytest tests/social_agent/test_candidates_score.py -v
```

- [ ] **Step 3: Implement `interest_score` in `src/social_agent/candidates.py`**

```python
"""Candidate selection + interest score ranking."""
from __future__ import annotations

SEVERITY_MAP = {
    "critical": 1.0,
    "major": 0.7,
    "minor": 0.4,
    "none": 0.0,
}
DEFAULT_SEVERITY_NORM = 0.6  # non-pretrunas pillars (None)


def interest_score(
    salience: float,
    severity: str | None,
    age_hours: float,
    candidate_topics: set[str],
    recent_topics: set[str],
) -> float:
    """Compute interest score ∈ [0, 1] for ranking draft candidates.

    score = 0.3*salience + 0.3*severity_norm + 0.2*freshness + 0.2*novelty
    """
    salience_c = max(0.0, min(1.0, salience))
    if severity is None:
        severity_norm = DEFAULT_SEVERITY_NORM
    else:
        severity_norm = SEVERITY_MAP.get(severity.lower(), DEFAULT_SEVERITY_NORM)

    freshness = max(0.0, 1.0 - (age_hours / 168.0))

    union = candidate_topics | recent_topics
    if not union:
        novelty = 1.0
    else:
        intersection = candidate_topics & recent_topics
        jaccard = len(intersection) / len(union)
        novelty = 1.0 - jaccard

    return 0.3 * salience_c + 0.3 * severity_norm + 0.2 * freshness + 0.2 * novelty
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/social_agent/test_candidates_score.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/candidates.py tests/social_agent/test_candidates_score.py
git commit -m "feat(social-agent): interest_score function + tests"
```

---

### Task 5: Pretrunas candidate query

**Files:**
- Modify: `src/social_agent/candidates.py`
- Create: `tests/social_agent/test_candidates_pretrunas.py`

- [ ] **Step 1: Write failing test with fixture DB**

`tests/social_agent/test_candidates_pretrunas.py`:

```python
import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_pretrunas_candidates


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Politician
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A Kariņš', 'JV')"
    )
    # Two claims (old + new) forming a contradiction
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (10, 1, 'budget', 'pret', 'Nekad', '2026-03-01', 'https://example.com/1'), "
        "       (11, 1, 'budget', 'par', 'Jā', '2026-04-15', 'https://example.com/2')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) VALUES "
        "(100, 1, 10, 11, 'budget', 'Reverse position', 'critical', 0.9, '2026-04-18 10:00:00')"
    )
    # Minor-severity contradiction should also be returned but sorted lower
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (20, 1, 'health', 'par', 'Jā', '2026-02-01', 'https://example.com/3'), "
        "       (21, 1, 'health', 'pret', 'Nē', '2026-04-17', 'https://example.com/4')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) VALUES "
        "(101, 1, 20, 21, 'health', 'minor flip', 'minor', 0.4, '2026-04-16 10:00:00')"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_pretrunas_returns_hydrated_rows(seeded_db):
    rows = fetch_pretrunas_candidates(db_path=seeded_db)
    assert len(rows) == 2
    row = next(r for r in rows if r["contradiction_id"] == 100)
    assert row["politician_name"] == "A Kariņš"
    assert row["topic"] == "budget"
    assert row["severity"] == "critical"
    assert row["salience"] == 0.9
    assert row["old_quote"] == "Nekad"
    assert row["new_quote"] == "Jā"
    assert row["old_stated_at"] == "2026-03-01"
    assert row["new_stated_at"] == "2026-04-15"


def test_fetch_pretrunas_excludes_already_posted(seeded_db):
    db = get_db(seeded_db)
    # Mark contradiction 100 as posted
    db.execute(
        "INSERT INTO social_drafts (pillar, text, source_data_json, score, status) "
        "VALUES ('pretrunas', 't', '{\"contradiction_id\": 100}', 0.8, 'posted')"
    )
    db.commit()
    db.close()
    rows = fetch_pretrunas_candidates(db_path=seeded_db)
    ids = {r["contradiction_id"] for r in rows}
    assert 100 not in ids
    assert 101 in ids
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/social_agent/test_candidates_pretrunas.py -v
```

- [ ] **Step 3: Implement `fetch_pretrunas_candidates`**

Append to `src/social_agent/candidates.py`:

```python
import json
from pathlib import Path

from src.db import DB_PATH, get_db


def fetch_pretrunas_candidates(db_path: str = DB_PATH) -> list[dict]:
    """Return unposted contradictions joined to both claims + politician name.

    Excludes contradictions whose `id` already appears in a posted social_drafts row
    (`source_data_json->>'contradiction_id'`).
    """
    db = get_db(db_path)
    rows = db.execute(
        """
        SELECT
            c.id            AS contradiction_id,
            c.opponent_id   AS politician_id,
            p.name          AS politician_name,
            p.party         AS party,
            c.topic         AS topic,
            c.summary       AS summary,
            c.severity      AS severity,
            c.salience      AS salience,
            c.detected_at   AS detected_at,
            co.quote        AS old_quote,
            co.stated_at    AS old_stated_at,
            co.source_url   AS old_source_url,
            cn.quote        AS new_quote,
            cn.stated_at    AS new_stated_at,
            cn.source_url   AS new_source_url
        FROM contradictions c
        LEFT JOIN tracked_politicians p ON p.id = c.opponent_id
        LEFT JOIN claims co ON co.id = c.claim_old_id
        LEFT JOIN claims cn ON cn.id = c.claim_new_id
        WHERE c.id NOT IN (
            SELECT CAST(json_extract(source_data_json, '$.contradiction_id') AS INTEGER)
            FROM social_drafts
            WHERE pillar = 'pretrunas' AND status IN ('approved', 'posted')
        )
        ORDER BY c.detected_at DESC
        """
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/social_agent/test_candidates_pretrunas.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/candidates.py tests/social_agent/test_candidates_pretrunas.py
git commit -m "feat(social-agent): fetch_pretrunas_candidates query"
```

---

### Task 6: Stats candidate query (weekly leaderboard)

**Files:**
- Modify: `src/social_agent/candidates.py`
- Create: `tests/social_agent/test_candidates_stats.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_candidates_stats.py`:

```python
import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_stats_candidate


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Three politicians
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party) VALUES (?, ?, ?)",
        [(1, "A", "JV"), (2, "B", "NA"), (3, "C", "ZZS")],
    )
    # Claims within the last 7 days
    db.executemany(
        "INSERT INTO claims (opponent_id, topic, stance, quote, stated_at, claim_type, source_url) "
        "VALUES (?, 'x', 'par', 'q', ?, 'position', ?)",
        [
            (1, "2026-04-18 10:00:00", "https://example.com/1"),
            (1, "2026-04-17 10:00:00", "https://example.com/2"),
            (1, "2026-04-16 10:00:00", "https://example.com/3"),
            (2, "2026-04-18 10:00:00", "https://example.com/4"),
            (2, "2026-04-17 10:00:00", "https://example.com/5"),
            (3, "2026-04-18 10:00:00", "https://example.com/6"),
        ],
    )
    # Old claim that should NOT appear in weekly counts
    db.execute(
        "INSERT INTO claims (opponent_id, topic, stance, quote, stated_at, claim_type, source_url) "
        "VALUES (3, 'x', 'par', 'q', '2026-01-01 10:00:00', 'position', 'https://example.com/old')"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_stats_candidate_returns_top_politicians(seeded_db):
    result = fetch_stats_candidate(db_path=seeded_db, now_iso="2026-04-19 12:00:00")
    assert result is not None
    leaders = result["leaderboard"]
    # Must be sorted desc by count
    assert [l["name"] for l in leaders[:3]] == ["A", "B", "C"]
    assert leaders[0]["count"] == 3
    assert leaders[1]["count"] == 2
    assert leaders[2]["count"] == 1
    assert result["iso_week"] == "2026-W16"  # 2026-04-19 is in ISO week 16


def test_fetch_stats_candidate_skip_if_week_already_posted(seeded_db):
    db = get_db(seeded_db)
    db.execute(
        "INSERT INTO social_drafts (pillar, text, source_data_json, score, status) "
        "VALUES ('stats', 't', '{\"iso_week\": \"2026-W16\"}', 0.8, 'approved')"
    )
    db.commit()
    db.close()
    result = fetch_stats_candidate(db_path=seeded_db, now_iso="2026-04-19 12:00:00")
    assert result is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/social_agent/test_candidates_stats.py -v
```

- [ ] **Step 3: Implement `fetch_stats_candidate`**

Append to `src/social_agent/candidates.py`:

```python
from datetime import datetime


def fetch_stats_candidate(db_path: str = DB_PATH, now_iso: str | None = None) -> dict | None:
    """Return weekly leaderboard payload, or None if this ISO week was already posted.

    Leaderboard counts `position` claims in the past 7 days, grouped by politician.
    Returns at most top 10.
    """
    if now_iso is None:
        now = datetime.utcnow()
    else:
        now = datetime.fromisoformat(now_iso.replace("Z", ""))

    iso_year, iso_week, _ = now.isocalendar()
    iso_week_str = f"{iso_year}-W{iso_week:02d}"

    db = get_db(db_path)
    # Skip if already posted/approved for this week
    already = db.execute(
        """
        SELECT 1 FROM social_drafts
        WHERE pillar = 'stats'
          AND status IN ('approved', 'posted')
          AND json_extract(source_data_json, '$.iso_week') = ?
        LIMIT 1
        """,
        (iso_week_str,),
    ).fetchone()
    if already:
        db.close()
        return None

    rows = db.execute(
        """
        SELECT p.id, p.name, p.party, COUNT(c.id) AS n
        FROM claims c
        JOIN tracked_politicians p ON p.id = c.opponent_id
        WHERE c.claim_type = 'position'
          AND c.stated_at >= datetime(?, '-7 days')
        GROUP BY p.id, p.name, p.party
        HAVING n > 0
        ORDER BY n DESC, p.name ASC
        LIMIT 10
        """,
        (now.strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()
    db.close()

    if not rows:
        return None

    return {
        "iso_week": iso_week_str,
        "leaderboard": [
            {"politician_id": r["id"], "name": r["name"], "party": r["party"], "count": r["n"]}
            for r in rows
        ],
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/social_agent/test_candidates_stats.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/candidates.py tests/social_agent/test_candidates_stats.py
git commit -m "feat(social-agent): fetch_stats_candidate weekly leaderboard"
```

---

### Task 7: Highlights candidate query (strongest_attacks + tensions)

**Files:**
- Modify: `src/social_agent/candidates.py`
- Create: `tests/social_agent/test_candidates_highlights.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_candidates_highlights.py`:

```python
import json
import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_highlights_candidates


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A', 'JV')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'B', 'NA')")
    # strongest_attacks JSON from oppo_briefs
    attacks = json.dumps([
        {"text": "A ir pretrunā pats ar sevi par budžetu"},
        {"text": "A maina viedokli par drošību"},
    ], ensure_ascii=False)
    db.execute(
        "INSERT INTO oppo_briefs (id, opponent_id, strongest_attacks, period_start, period_end, created_at) "
        "VALUES (1, 1, ?, '2026-04-12', '2026-04-19', '2026-04-19 09:00:00')",
        (attacks,),
    )
    # A political tension row
    db.execute(
        "INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, "
        "tension_type, created_at) VALUES "
        "(1, 1, 2, 'drošība', 'A uzbrūk B par drošības politiku', 'uzbrukums', '2026-04-18 15:00:00')"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_highlights_returns_attacks_and_tensions(seeded_db):
    rows = fetch_highlights_candidates(db_path=seeded_db)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"attack", "tension"}

    attack_row = next(r for r in rows if r["kind"] == "attack")
    assert attack_row["politician_name"] == "A"
    assert "pretrunā" in attack_row["text"]

    tension_row = next(r for r in rows if r["kind"] == "tension")
    assert tension_row["source_name"] == "A"
    assert tension_row["target_name"] == "B"
    assert tension_row["topic"] == "drošība"


def test_fetch_highlights_respects_lookback_days(seeded_db):
    # Very short lookback → only the 2026-04-19 brief remains (if within window)
    rows = fetch_highlights_candidates(db_path=seeded_db, lookback_days=0)
    assert rows == []
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/social_agent/test_candidates_highlights.py -v
```

- [ ] **Step 3: Implement `fetch_highlights_candidates`**

Append to `src/social_agent/candidates.py`:

```python
def fetch_highlights_candidates(db_path: str = DB_PATH, lookback_days: int = 7) -> list[dict]:
    """Return list of highlight candidates from recent oppo_briefs.strongest_attacks
    and political_tensions.

    Each row is a dict with `kind` ∈ {'attack', 'tension'} + pillar-specific fields.
    Skips rows already represented in approved/posted social_drafts.
    """
    db = get_db(db_path)

    attacks_raw = db.execute(
        """
        SELECT ob.id AS brief_id, ob.opponent_id, p.name AS politician_name,
               p.party, ob.strongest_attacks, ob.created_at
        FROM oppo_briefs ob
        JOIN tracked_politicians p ON p.id = ob.opponent_id
        WHERE ob.strongest_attacks IS NOT NULL
          AND ob.created_at >= datetime('now', ?)
        """,
        (f"-{lookback_days} days",),
    ).fetchall()

    attacks: list[dict] = []
    for r in attacks_raw:
        try:
            items = json.loads(r["strongest_attacks"]) or []
        except (TypeError, json.JSONDecodeError):
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict) or not item.get("text"):
                continue
            attacks.append({
                "kind": "attack",
                "brief_id": r["brief_id"],
                "attack_index": idx,
                "politician_id": r["opponent_id"],
                "politician_name": r["politician_name"],
                "party": r["party"],
                "text": item["text"],
                "created_at": r["created_at"],
            })

    tensions = db.execute(
        """
        SELECT t.id AS tension_id, t.source_pid, t.target_pid,
               ps.name AS source_name, pt.name AS target_name,
               t.topic, t.description, t.tension_type,
               t.source_url, t.created_at
        FROM political_tensions t
        LEFT JOIN tracked_politicians ps ON ps.id = t.source_pid
        LEFT JOIN tracked_politicians pt ON pt.id = t.target_pid
        WHERE t.created_at >= datetime('now', ?)
        """,
        (f"-{lookback_days} days",),
    ).fetchall()
    tension_rows = [
        {
            "kind": "tension",
            "tension_id": r["tension_id"],
            "source_name": r["source_name"],
            "target_name": r["target_name"],
            "topic": r["topic"],
            "description": r["description"],
            "tension_type": r["tension_type"],
            "source_url": r["source_url"],
            "created_at": r["created_at"],
        }
        for r in tensions
    ]

    posted = db.execute(
        """
        SELECT source_data_json FROM social_drafts
        WHERE pillar = 'highlights' AND status IN ('approved', 'posted')
        """
    ).fetchall()
    posted_keys: set[tuple[str, int, int | None]] = set()
    for p in posted:
        try:
            sd = json.loads(p["source_data_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if sd.get("kind") == "attack":
            posted_keys.add(("attack", sd.get("brief_id"), sd.get("attack_index")))
        elif sd.get("kind") == "tension":
            posted_keys.add(("tension", sd.get("tension_id"), None))
    db.close()

    out: list[dict] = []
    for a in attacks:
        if ("attack", a["brief_id"], a["attack_index"]) in posted_keys:
            continue
        out.append(a)
    for t in tension_rows:
        if ("tension", t["tension_id"], None) in posted_keys:
            continue
        out.append(t)
    return out
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/candidates.py tests/social_agent/test_candidates_highlights.py
git commit -m "feat(social-agent): fetch_highlights_candidates (attacks + tensions)"
```

---

### Task 8: Top-N selection with per-pillar cap

**Files:**
- Modify: `src/social_agent/candidates.py`
- Create: `tests/social_agent/test_candidates_selection.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_candidates_selection.py`:

```python
from src.social_agent.candidates import select_top_n


def test_select_top_n_respects_total_limit():
    pool = [
        {"pillar": "pretrunas", "score": 0.9, "payload": {"i": 1}},
        {"pillar": "pretrunas", "score": 0.85, "payload": {"i": 2}},
        {"pillar": "pretrunas", "score": 0.80, "payload": {"i": 3}},
        {"pillar": "stats", "score": 0.7, "payload": {"i": 4}},
        {"pillar": "highlights", "score": 0.6, "payload": {"i": 5}},
    ]
    top = select_top_n(pool, n=3, per_pillar_cap=2)
    assert len(top) == 3
    pretrunas_count = sum(1 for t in top if t["pillar"] == "pretrunas")
    assert pretrunas_count == 2, "pretrunas must cap at 2 per-pillar"
    # Bumped pretrunas #3 must be replaced by stats or highlights
    kinds = {t["pillar"] for t in top}
    assert "stats" in kinds or "highlights" in kinds


def test_select_top_n_sorts_by_score():
    pool = [
        {"pillar": "pretrunas", "score": 0.5, "payload": {"i": 1}},
        {"pillar": "stats", "score": 0.9, "payload": {"i": 2}},
        {"pillar": "highlights", "score": 0.7, "payload": {"i": 3}},
    ]
    top = select_top_n(pool, n=3, per_pillar_cap=2)
    assert [t["payload"]["i"] for t in top] == [2, 3, 1]


def test_select_top_n_empty_pool():
    assert select_top_n([], n=3, per_pillar_cap=2) == []
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `select_top_n`**

Append to `src/social_agent/candidates.py`:

```python
def select_top_n(pool: list[dict], n: int = 3, per_pillar_cap: int = 2) -> list[dict]:
    """Pick top-N candidates by score with a hard per-pillar cap.

    Each pool entry must have keys 'pillar' and 'score'. Ties broken by input order.
    """
    sorted_pool = sorted(
        enumerate(pool),
        key=lambda pair: (-pair[1]["score"], pair[0]),
    )
    picked: list[dict] = []
    pillar_counts: dict[str, int] = {}
    for _, entry in sorted_pool:
        if len(picked) >= n:
            break
        count = pillar_counts.get(entry["pillar"], 0)
        if count >= per_pillar_cap:
            continue
        picked.append(entry)
        pillar_counts[entry["pillar"]] = count + 1
    return picked
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/candidates.py tests/social_agent/test_candidates_selection.py
git commit -m "feat(social-agent): select_top_n with per-pillar cap"
```

---

## Phase 3 — Drafters (text generators)

### Task 9: Pretrunas drafter

**Files:**
- Modify: `src/social_agent/drafters.py`
- Create: `tests/social_agent/test_drafters.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_drafters.py`:

```python
from src.social_agent.drafters import draft_pretrunas


SAMPLE_CONTRADICTION = {
    "contradiction_id": 100,
    "politician_name": "Arturs Kariņš",
    "topic": "budžets",
    "old_quote": "Nekad neatbalstīšu nodokļu celšanu",
    "old_stated_at": "2026-03-01",
    "new_quote": "Šis budžets ir vienīgais iespējamais risinājums",
    "new_stated_at": "2026-04-15",
    "slug": "arturs-karins",
}


def test_draft_pretrunas_contains_required_elements():
    text = draft_pretrunas(SAMPLE_CONTRADICTION)
    assert "Arturs Kariņš" in text
    assert "budžets" in text
    assert "Nekad neatbalstīšu" in text
    assert "vienīgais iespējamais" in text
    assert "2026-03-01" in text
    assert "2026-04-15" in text
    assert "atmina.lv/" in text
    assert "Kurš ir īstais viedoklis?" in text


def test_draft_pretrunas_max_280_chars():
    long = {
        **SAMPLE_CONTRADICTION,
        "old_quote": "A" * 200,
        "new_quote": "B" * 200,
    }
    text = draft_pretrunas(long)
    assert len(text) <= 280, f"draft too long: {len(text)} chars"
    # Truncated quotes must end with ellipsis
    assert "…" in text


def test_draft_pretrunas_raises_on_missing_fields():
    import pytest
    with pytest.raises(KeyError):
        draft_pretrunas({"contradiction_id": 1})
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `draft_pretrunas`**

In `src/social_agent/drafters.py`:

```python
"""Pillar-specific text templates (≤280 chars)."""
from __future__ import annotations

MAX_LEN = 280
ELLIPSIS = "…"


def _shorten(s: str, budget: int) -> str:
    if len(s) <= budget:
        return s
    if budget <= 1:
        return ELLIPSIS
    return s[: budget - 1].rstrip() + ELLIPSIS


def draft_pretrunas(row: dict) -> str:
    """Generate a ≤280-char pretrunas draft in jautājums-stils."""
    name = row["politician_name"]
    topic = row["topic"]
    old_q = row["old_quote"]
    new_q = row["new_quote"]
    old_d = row["old_stated_at"][:10] if row.get("old_stated_at") else ""
    new_d = row["new_stated_at"][:10] if row.get("new_stated_at") else ""
    slug = row.get("slug") or ""
    link = f"atmina.lv/{slug}".rstrip("/")

    static = (
        f"{name} par {topic}:\n\n"
        f'"" — {old_d}\n'
        f'"" — {new_d}\n\n'
        "Kurš ir īstais viedoklis? 🧐\n\n"
        f"{link}"
    )
    budget = MAX_LEN - len(static)
    # Split remaining budget 50/50 between the two quotes
    half = max(10, budget // 2)
    old_short = _shorten(old_q, half)
    new_short = _shorten(new_q, budget - len(old_short))

    text = (
        f"{name} par {topic}:\n\n"
        f'"{old_short}" — {old_d}\n'
        f'"{new_short}" — {new_d}\n\n'
        "Kurš ir īstais viedoklis? 🧐\n\n"
        f"{link}"
    )
    # Safety clip in case of emoji byte-width surprises
    return text[:MAX_LEN]
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/drafters.py tests/social_agent/test_drafters.py
git commit -m "feat(social-agent): draft_pretrunas template"
```

---

### Task 10: Stats drafter

**Files:**
- Modify: `src/social_agent/drafters.py`
- Modify: `tests/social_agent/test_drafters.py`

- [ ] **Step 1: Append failing test**

Append to `tests/social_agent/test_drafters.py`:

```python
from src.social_agent.drafters import draft_stats


SAMPLE_STATS = {
    "iso_week": "2026-W16",
    "leaderboard": [
        {"politician_id": 1, "name": "Arturs Kariņš", "party": "JV", "count": 12},
        {"politician_id": 2, "name": "Edgars Rinkēvičs", "party": "JV", "count": 9},
        {"politician_id": 3, "name": "Juris Rancāns", "party": "JV", "count": 7},
    ],
}


def test_draft_stats_lists_top_three_names():
    text = draft_stats(SAMPLE_STATS)
    assert "Arturs Kariņš" in text
    assert "Edgars Rinkēvičs" in text
    assert "Juris Rancāns" in text
    assert "12" in text
    assert "atmina.lv/statistika" in text
    assert len(text) <= 280


def test_draft_stats_handles_short_leaderboard():
    result = draft_stats({
        "iso_week": "2026-W16",
        "leaderboard": [{"politician_id": 1, "name": "Alone", "party": "X", "count": 3}],
    })
    assert "Alone" in result
    assert len(result) <= 280
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `draft_stats`**

Append to `src/social_agent/drafters.py`:

```python
def draft_stats(payload: dict) -> str:
    """Generate the weekly leaderboard draft."""
    board = payload["leaderboard"][:3]
    lines = ["Aktīvākie deputāti šonedēļ:"]
    for i, entry in enumerate(board, start=1):
        lines.append(f"{i}. {entry['name']} — {entry['count']} pozīcijas")
    lines.append("")
    lines.append("Kas klusē? Skaties pilno sarakstu:")
    lines.append("atmina.lv/statistika")

    text = "\n".join(lines)
    # Budget guard — shouldn't trigger in practice with top-3 names
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1] + ELLIPSIS
    return text
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/drafters.py tests/social_agent/test_drafters.py
git commit -m "feat(social-agent): draft_stats weekly leaderboard"
```

---

### Task 11: Highlights drafter (attacks + tensions)

**Files:**
- Modify: `src/social_agent/drafters.py`
- Modify: `tests/social_agent/test_drafters.py`

- [ ] **Step 1: Append failing test**

Append to `tests/social_agent/test_drafters.py`:

```python
from src.social_agent.drafters import draft_highlight


def test_draft_highlight_attack():
    row = {
        "kind": "attack",
        "politician_name": "Arturs Kariņš",
        "text": "Kariņš pēdējā gada laikā ir mainījis viedokli par nodokļiem trīs reizes.",
        "slug": "arturs-karins",
    }
    text = draft_highlight(row)
    assert "Kariņš" in text
    assert "atmina.lv/" in text
    assert len(text) <= 280


def test_draft_highlight_tension():
    row = {
        "kind": "tension",
        "source_name": "A",
        "target_name": "B",
        "topic": "drošība",
        "description": "A publiski pārmet B par drošības dienestu reformu.",
        "tension_type": "uzbrukums",
    }
    text = draft_highlight(row)
    assert "A" in text
    assert "B" in text
    assert "drošība" in text
    assert "atmina.lv/" in text
    assert len(text) <= 280


def test_draft_highlight_unknown_kind_raises():
    import pytest
    with pytest.raises(ValueError):
        draft_highlight({"kind": "unknown"})
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `draft_highlight`**

Append to `src/social_agent/drafters.py`:

```python
def draft_highlight(row: dict) -> str:
    """Dispatch to attack or tension sub-renderer."""
    kind = row.get("kind")
    if kind == "attack":
        return _draft_attack(row)
    if kind == "tension":
        return _draft_tension(row)
    raise ValueError(f"Unknown highlight kind: {kind!r}")


def _draft_attack(row: dict) -> str:
    name = row["politician_name"]
    slug = row.get("slug") or ""
    body = row["text"]
    link = f"atmina.lv/{slug}".rstrip("/")
    static = f"\n\nPar ko runā atmina.lv: {link}"
    budget = MAX_LEN - len(static)
    body_short = _shorten(body, budget)
    return f"{body_short}{static}"


def _draft_tension(row: dict) -> str:
    src = row["source_name"]
    tgt = row["target_name"]
    topic = row["topic"]
    desc = row["description"]
    static = f"\n\n{src} ⇄ {tgt} — {topic}\natmina.lv/spriedzes"
    budget = MAX_LEN - len(static)
    desc_short = _shorten(desc, budget)
    return f"{desc_short}{static}"
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/drafters.py tests/social_agent/test_drafters.py
git commit -m "feat(social-agent): draft_highlight (attacks + tensions)"
```

---

## Phase 4 — Visuals

### Task 12: Chart renderer (matplotlib)

**Files:**
- Modify: `src/social_agent/visuals.py`
- Create: `tests/social_agent/test_visuals_chart.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_visuals_chart.py`:

```python
import os
import tempfile
from pathlib import Path

from src.social_agent.visuals import render_chart


def test_render_chart_produces_png(tmp_path):
    out = tmp_path / "chart.png"
    result = render_chart(
        {
            "leaderboard": [
                {"name": "A", "count": 5},
                {"name": "B", "count": 3},
                {"name": "C", "count": 1},
            ]
        },
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial PNG


def test_render_chart_rejects_empty_leaderboard(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        render_chart({"leaderboard": []}, out_path=tmp_path / "x.png")
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `render_chart`**

Replace contents of `src/social_agent/visuals.py`:

```python
"""Three renderers: chart / quote_card / illustration → PNG files."""
from __future__ import annotations

from pathlib import Path

# Brand tokens — must match atmina.lv
BG = "#0b0f19"
ACCENT = "#ff3b7f"
TEXT = "#ffffff"
TEXT_DIM = "#a0a7b8"


def render_chart(payload: dict, out_path: Path) -> Path:
    """Horizontal bar chart of `leaderboard` → 1200×675 PNG, atmina.lv palette."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    board = payload.get("leaderboard", [])
    if not board:
        raise ValueError("leaderboard is empty — nothing to chart")

    names = [e["name"] for e in board][::-1]
    counts = [e["count"] for e in board][::-1]

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.barh(names, counts, color=ACCENT, edgecolor="none", height=0.7)

    ax.tick_params(colors=TEXT_DIM, labelsize=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Pozīcijas šonedēļ", color=TEXT_DIM, fontsize=12)
    ax.set_title("Aktīvākie deputāti", color=TEXT, fontsize=22, loc="left", pad=20)
    for i, v in enumerate(counts):
        ax.text(v + max(counts) * 0.01, i, str(v),
                color=TEXT, va="center", fontsize=14, fontweight="bold")
    fig.text(0.99, 0.02, "atmina.lv", color=ACCENT, fontsize=12,
             ha="right", va="bottom", fontweight="bold")

    plt.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    return out_path
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/visuals.py tests/social_agent/test_visuals_chart.py
git commit -m "feat(social-agent): render_chart for stats pillar"
```

---

### Task 13: Quote card renderer (HTML → Playwright PNG)

**Files:**
- Create: `templates/social/quote_card.html.j2`
- Modify: `src/social_agent/visuals.py`
- Create: `tests/social_agent/test_visuals_quote_card.py`

- [ ] **Step 1: Write failing test (Playwright integration, skip in CI)**

`tests/social_agent/test_visuals_quote_card.py`:

```python
import os
from pathlib import Path

import pytest

from src.social_agent.visuals import render_quote_card


pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1",
    reason="Playwright not available in this environment",
)


def test_render_quote_card_produces_png(tmp_path):
    out = tmp_path / "card.png"
    result = render_quote_card(
        {
            "politician_name": "Arturs Kariņš",
            "topic": "budžets",
            "old_quote": "Nekad neatbalstīšu nodokļu celšanu",
            "old_date": "2026-03-01",
            "new_quote": "Šis budžets ir vienīgais risinājums",
            "new_date": "2026-04-15",
        },
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 5000
```

- [ ] **Step 2: Create Jinja template**

`templates/social/quote_card.html.j2`:

```html
<!DOCTYPE html>
<html lang="lv">
<head>
<meta charset="UTF-8">
<style>
  html, body { margin:0; padding:0; background:#0b0f19; color:#fff;
    font-family: Inter, system-ui, sans-serif; }
  .card { width: 1200px; height: 675px; padding: 60px 72px;
    display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box; }
  .header { display: flex; align-items: baseline; justify-content: space-between; }
  .header h1 { font-size: 44px; margin: 0; font-weight: 600; letter-spacing: -0.5px; }
  .header .topic { font-size: 22px; color: #ff3b7f; font-weight: 500; }
  .quotes { display: flex; flex-direction: column; gap: 28px; margin-top: 32px; }
  .quote { padding: 24px 28px; background: #151a2a; border-left: 4px solid #ff3b7f;
    border-radius: 8px; }
  .quote p { margin: 0 0 10px; font-size: 28px; line-height: 1.35; }
  .quote .meta { color: #a0a7b8; font-size: 16px; }
  .footer { display: flex; justify-content: space-between; align-items: center;
    color: #a0a7b8; font-size: 18px; }
  .brand { color: #ff3b7f; font-weight: 700; font-size: 22px; }
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>{{ politician_name }}</h1>
      <span class="topic">{{ topic }}</span>
    </div>
    <div class="quotes">
      <div class="quote"><p>"{{ old_quote }}"</p><span class="meta">{{ old_date }}</span></div>
      <div class="quote"><p>"{{ new_quote }}"</p><span class="meta">{{ new_date }}</span></div>
    </div>
    <div class="footer"><span>Kurš ir īstais viedoklis?</span><span class="brand">atmina.lv</span></div>
  </div>
</body>
</html>
```

- [ ] **Step 3: Implement `render_quote_card`**

Append to `src/social_agent/visuals.py`:

```python
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "social"


def render_quote_card(payload: dict, out_path: Path) -> Path:
    """Render quote_card.html.j2 with Playwright → 1200×675 PNG."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from playwright.sync_api import sync_playwright

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("quote_card.html.j2")
    html = tpl.render(**payload)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 675})
        page.set_content(html, wait_until="domcontentloaded")
        page.screenshot(path=str(out_path), full_page=False,
                        clip={"x": 0, "y": 0, "width": 1200, "height": 675})
        browser.close()
    return out_path
```

- [ ] **Step 4: Run tests — expect PASS (requires playwright installed)**

```bash
python -m pytest tests/social_agent/test_visuals_quote_card.py -v
```

If playwright browsers aren't installed: `python -m playwright install chromium`.

- [ ] **Step 5: Commit**

```bash
git add templates/social/ src/social_agent/visuals.py tests/social_agent/test_visuals_quote_card.py
git commit -m "feat(social-agent): render_quote_card via Playwright"
```

---

### Task 14: Illustration renderer (nanobanana wrapper)

**Files:**
- Modify: `src/social_agent/visuals.py`
- Create: `tests/social_agent/test_visuals_illustration.py`

**Note on the existing nanobanana interface.** `src/graphics/nanobanana.py::generate_image(prompt: str, aspect_ratio: str = "16:9") -> bytes` returns raw PNG bytes rather than writing to a path. The wrapper below writes those bytes to `out_path` itself.

- [ ] **Step 1: Write failing test with monkeypatched nanobanana**

`tests/social_agent/test_visuals_illustration.py`:

```python
from pathlib import Path

from src.social_agent import visuals


def test_render_illustration_delegates_to_nanobanana(monkeypatch, tmp_path):
    called = {}

    def fake_generate_bytes(prompt, **kwargs):
        called["prompt"] = prompt
        called["kwargs"] = kwargs
        return b"\x89PNG\r\n\x1a\nfake"

    monkeypatch.setattr(visuals, "_nanobanana_bytes", fake_generate_bytes)
    out = tmp_path / "illus.png"
    result = visuals.render_illustration(
        {"subject": "ideoloģiju sadursme", "style_hint": "editorial"},
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG")
    assert "ideoloģiju sadursme" in called["prompt"]
    assert "atmina" in called["prompt"].lower()
    # Brand must enforce no-text rule (per feedback_nanobanana_text_rule memory)
    assert "no text" in called["prompt"].lower()
    # Aspect ratio must be 16:9 for X optimal
    assert called["kwargs"].get("aspect_ratio") == "16:9"
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `render_illustration` + bytes indirection**

Append to `src/social_agent/visuals.py`:

```python
def _nanobanana_bytes(prompt: str, **kwargs) -> bytes:
    """Indirection so tests can monkeypatch. Delegates to src.graphics.nanobanana."""
    from src.graphics.nanobanana import generate_image
    return generate_image(prompt, **kwargs)


def render_illustration(payload: dict, out_path: Path) -> Path:
    """Compose nanobanana prompt for an abstract editorial illustration."""
    subject = payload["subject"]
    style = payload.get("style_hint") or "editorial illustration"
    prompt = (
        f"{style} of: {subject}. "
        "atmina.lv brand, dark background #0b0f19 with magenta accent #ff3b7f, "
        "cinematic lighting, no text, no letters, no words, no labels. "
        "16:9 composition, centered subject, depth of field."
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    png = _nanobanana_bytes(prompt, aspect_ratio="16:9")
    out_path.write_bytes(png)
    return out_path
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/visuals.py tests/social_agent/test_visuals_illustration.py
git commit -m "feat(social-agent): render_illustration wrapper around nanobanana"
```

---

## Phase 5 — Storage (DB CRUD)

### Task 15: `social_drafts` CRUD functions

**Files:**
- Modify: `src/social_agent/storage.py`
- Create: `tests/social_agent/test_storage.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_storage.py`:

```python
import json
import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.storage import (
    create_draft,
    get_draft,
    list_pending_drafts,
    mark_approved,
    mark_rejected,
    mark_posted,
    mark_failed,
    mark_revising,
)


@pytest.fixture
def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_create_draft_inserts_row(fresh_db):
    did = create_draft(
        pillar="pretrunas",
        text="Sample draft",
        image_path="/tmp/x.png",
        source_data={"contradiction_id": 100},
        score=0.87,
        db_path=fresh_db,
    )
    assert isinstance(did, int) and did > 0
    row = get_draft(did, db_path=fresh_db)
    assert row["pillar"] == "pretrunas"
    assert row["status"] == "pending"
    assert row["score"] == 0.87
    assert json.loads(row["source_data_json"])["contradiction_id"] == 100


def test_status_transitions(fresh_db):
    did = create_draft(
        pillar="stats", text="t", image_path=None, source_data={}, score=0.5, db_path=fresh_db
    )
    mark_approved(did, db_path=fresh_db)
    assert get_draft(did, db_path=fresh_db)["status"] == "approved"
    mark_posted(did, tweet_id="12345", db_path=fresh_db)
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "posted"
    assert row["tweet_id"] == "12345"
    assert row["posted_at"] is not None


def test_mark_failed_records_error(fresh_db):
    did = create_draft(
        pillar="highlights", text="t", image_path=None, source_data={}, score=0.5, db_path=fresh_db
    )
    mark_failed(did, error_message="rate limit", db_path=fresh_db)
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "failed"
    assert row["error_message"] == "rate limit"


def test_list_pending_drafts_returns_only_pending(fresh_db):
    ids = [
        create_draft(pillar="pretrunas", text=f"t{i}", image_path=None,
                     source_data={}, score=0.5, db_path=fresh_db)
        for i in range(3)
    ]
    mark_rejected(ids[0], db_path=fresh_db)
    pending = list_pending_drafts(db_path=fresh_db)
    pending_ids = {r["id"] for r in pending}
    assert ids[0] not in pending_ids
    assert ids[1] in pending_ids
    assert ids[2] in pending_ids


def test_mark_revising_creates_child_draft(fresh_db):
    parent_id = create_draft(
        pillar="pretrunas", text="original", image_path=None,
        source_data={"contradiction_id": 100}, score=0.8, db_path=fresh_db
    )
    child_id = mark_revising(parent_id, new_text="shorter", db_path=fresh_db)
    parent = get_draft(parent_id, db_path=fresh_db)
    child = get_draft(child_id, db_path=fresh_db)
    assert parent["status"] == "revising"
    assert child["parent_draft_id"] == parent_id
    assert child["revision_count"] == 1
    assert child["text"] == "shorter"
    assert child["status"] == "pending"
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement storage module**

Replace contents of `src/social_agent/storage.py`:

```python
"""social_drafts table CRUD: create / fetch / mark_* transitions."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from src.db import DB_PATH, get_db

_LV_OFFSET = timedelta(hours=3)


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def create_draft(
    pillar: str,
    text: str,
    image_path: str | None,
    source_data: dict,
    score: float,
    db_path: str = DB_PATH,
    parent_draft_id: int | None = None,
    revision_count: int = 0,
    telegram_chat_id: str | None = None,
) -> int:
    db = get_db(db_path)
    cur = db.execute(
        """
        INSERT INTO social_drafts (
            pillar, text, image_path, source_data_json, score, status,
            parent_draft_id, revision_count, telegram_chat_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            pillar, text, image_path, json.dumps(source_data, ensure_ascii=False),
            score, parent_draft_id, revision_count, telegram_chat_id, _now_lv(),
        ),
    )
    db.commit()
    draft_id = cur.lastrowid
    db.close()
    return draft_id


def get_draft(draft_id: int, db_path: str = DB_PATH) -> dict | None:
    db = get_db(db_path)
    row = db.execute("SELECT * FROM social_drafts WHERE id = ?", (draft_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_pending_drafts(db_path: str = DB_PATH) -> list[dict]:
    db = get_db(db_path)
    rows = db.execute(
        "SELECT * FROM social_drafts WHERE status = 'pending' ORDER BY score DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _set_status(draft_id: int, status: str, extras: dict, db_path: str) -> None:
    db = get_db(db_path)
    cols = ["status = ?"]
    vals: list = [status]
    for k, v in extras.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(draft_id)
    db.execute(f"UPDATE social_drafts SET {', '.join(cols)} WHERE id = ?", vals)
    db.commit()
    db.close()


def mark_approved(draft_id: int, db_path: str = DB_PATH) -> None:
    _set_status(draft_id, "approved", {}, db_path)


def mark_rejected(draft_id: int, db_path: str = DB_PATH) -> None:
    _set_status(draft_id, "rejected", {}, db_path)


def mark_posted(draft_id: int, tweet_id: str, db_path: str = DB_PATH) -> None:
    _set_status(draft_id, "posted", {"tweet_id": tweet_id, "posted_at": _now_lv()}, db_path)


def mark_failed(draft_id: int, error_message: str, db_path: str = DB_PATH) -> None:
    _set_status(draft_id, "failed", {"error_message": error_message}, db_path)


def mark_revising(parent_id: int, new_text: str, db_path: str = DB_PATH) -> int:
    """Mark the parent as 'revising' and create a new pending draft inheriting its context.

    Returns the new child draft id.
    """
    parent = get_draft(parent_id, db_path=db_path)
    if parent is None:
        raise ValueError(f"No draft #{parent_id}")
    child_id = create_draft(
        pillar=parent["pillar"],
        text=new_text,
        image_path=parent["image_path"],  # reuse same image unless re-rendered separately
        source_data=json.loads(parent["source_data_json"]),
        score=parent["score"],
        db_path=db_path,
        parent_draft_id=parent_id,
        revision_count=parent["revision_count"] + 1,
        telegram_chat_id=parent["telegram_chat_id"],
    )
    _set_status(parent_id, "revising", {}, db_path)
    return child_id
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/storage.py tests/social_agent/test_storage.py
git commit -m "feat(social-agent): storage CRUD for social_drafts"
```

---

## Phase 6 — Publisher (twikit)

### Task 16: twikit client loader with dedicated cookies

**Files:**
- Modify: `src/social_agent/publisher.py`
- Create: `tests/social_agent/test_publisher.py`

- [ ] **Step 1: Write failing test (mocked twikit)**

`tests/social_agent/test_publisher.py`:

```python
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.social_agent import publisher


def test_load_atmina_client_reads_cookies_path(tmp_path, monkeypatch):
    cookies = tmp_path / "cookies.json"
    cookies.write_text("[]")
    monkeypatch.setattr(publisher, "_cookies_path", lambda: str(cookies))

    fake_client = MagicMock()
    fake_client.load_cookies = MagicMock()
    with patch("src.social_agent.publisher.Client", return_value=fake_client) as ClientCls:
        c = publisher.load_atmina_client()
        ClientCls.assert_called_once_with("en-US")
        fake_client.load_cookies.assert_called_once_with(str(cookies))
        assert c is fake_client


def test_load_atmina_client_raises_when_no_cookies(monkeypatch):
    monkeypatch.setattr(publisher, "_cookies_path", lambda: "/nope/missing.json")
    with pytest.raises(FileNotFoundError):
        publisher.load_atmina_client()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement loader**

Replace contents of `src/social_agent/publisher.py`:

```python
"""twikit wrapper — posts drafts to @atmina_lv."""
from __future__ import annotations

import asyncio
from pathlib import Path

from twikit import Client

from src.credentials import get_credential


def _cookies_path() -> str:
    path = get_credential("x_atmina_cookies_path") or "data/x_cookies_atmina.json"
    return path


def load_atmina_client() -> Client:
    """Load a twikit Client authenticated with the dedicated @atmina_lv cookie file."""
    path = _cookies_path()
    if not Path(path).exists():
        raise FileNotFoundError(
            f"@atmina_lv cookies not found at {path}. "
            "Set via: python -m src.credentials set x_atmina_cookies_path"
        )
    client = Client("en-US")
    client.load_cookies(path)
    return client
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/publisher.py tests/social_agent/test_publisher.py
git commit -m "feat(social-agent): publisher — load_atmina_client"
```

---

### Task 17: `publish_draft()` (upload media + create_tweet)

**Files:**
- Modify: `src/social_agent/publisher.py`
- Modify: `tests/social_agent/test_publisher.py`

- [ ] **Step 1: Append failing test**

Append to `tests/social_agent/test_publisher.py`:

```python
from src.social_agent import publisher


def test_publish_draft_with_image(monkeypatch, tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")

    upload_mock = AsyncMock(return_value="media-123")
    tweet_mock = MagicMock()
    tweet_mock.id = "tweet-999"
    create_mock = AsyncMock(return_value=tweet_mock)

    fake_client = MagicMock()
    fake_client.upload_media = upload_mock
    fake_client.create_tweet = create_mock

    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)

    tweet_id = publisher.publish_draft(text="Hello", image_path=str(img))
    assert tweet_id == "tweet-999"
    upload_mock.assert_awaited_once_with(str(img))
    create_mock.assert_awaited_once()
    _, kwargs = create_mock.call_args
    assert kwargs["text"] == "Hello"
    assert kwargs["media_ids"] == ["media-123"]


def test_publish_draft_without_image(monkeypatch):
    tweet_mock = MagicMock()
    tweet_mock.id = "tweet-000"
    fake_client = MagicMock()
    fake_client.upload_media = AsyncMock()
    fake_client.create_tweet = AsyncMock(return_value=tweet_mock)
    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)

    tweet_id = publisher.publish_draft(text="Text only", image_path=None)
    assert tweet_id == "tweet-000"
    fake_client.upload_media.assert_not_awaited()
    fake_client.create_tweet.assert_awaited_once()
    _, kwargs = fake_client.create_tweet.call_args
    assert "media_ids" not in kwargs or kwargs["media_ids"] is None


def test_publish_draft_propagates_errors(monkeypatch):
    fake_client = MagicMock()
    fake_client.create_tweet = AsyncMock(side_effect=RuntimeError("rate limit"))
    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)
    with pytest.raises(RuntimeError, match="rate limit"):
        publisher.publish_draft(text="x", image_path=None)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `publish_draft`**

Append to `src/social_agent/publisher.py`:

```python
def publish_draft(text: str, image_path: str | None) -> str:
    """Upload media (if any) and post a tweet. Returns the tweet id as string.

    Raises any underlying twikit exception so callers can record status='failed'.
    """
    return asyncio.run(_publish_async(text, image_path))


async def _publish_async(text: str, image_path: str | None) -> str:
    client = load_atmina_client()
    kwargs: dict = {"text": text}
    if image_path:
        media_id = await client.upload_media(image_path)
        kwargs["media_ids"] = [media_id]
    tweet = await client.create_tweet(**kwargs)
    return str(tweet.id)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/publisher.py tests/social_agent/test_publisher.py
git commit -m "feat(social-agent): publish_draft — upload media + create_tweet"
```

---

## Phase 7 — Telegram (Bot API via httpx)

### Task 18: Telegram sendPhoto + sendMessage wrappers

**Files:**
- Modify: `src/social_agent/telegram.py`
- Create: `tests/social_agent/test_telegram.py`

- [ ] **Step 1: Write failing test with httpx mock**

`tests/social_agent/test_telegram.py`:

```python
from unittest.mock import MagicMock, patch

from src.social_agent import telegram as tg


def test_send_draft_with_image_calls_sendphoto(monkeypatch, tmp_path):
    img = tmp_path / "card.png"
    img.write_bytes(b"\x89PNG")
    monkeypatch.setattr(tg, "_bot_token", lambda: "BOT-TOKEN")
    monkeypatch.setattr(tg, "_operator_chat_id", lambda: "12345")

    fake_response = MagicMock()
    fake_response.json.return_value = {"ok": True, "result": {"message_id": 42}}
    fake_response.raise_for_status = MagicMock()

    with patch("src.social_agent.telegram.httpx.post", return_value=fake_response) as post:
        msg_id = tg.send_draft(
            draft_id=7,
            pillar="pretrunas",
            text="Sample text",
            image_path=str(img),
        )
    assert msg_id == "42"
    url, kwargs = post.call_args[0], post.call_args[1]
    assert "sendPhoto" in url[0]
    assert "BOT-TOKEN" in url[0]
    assert kwargs["data"]["chat_id"] == "12345"
    assert "Draft #7" in kwargs["data"]["caption"]
    assert "pretrunas" in kwargs["data"]["caption"]


def test_send_draft_without_image_calls_sendmessage(monkeypatch):
    monkeypatch.setattr(tg, "_bot_token", lambda: "T")
    monkeypatch.setattr(tg, "_operator_chat_id", lambda: "1")
    fake_response = MagicMock()
    fake_response.json.return_value = {"ok": True, "result": {"message_id": 7}}
    fake_response.raise_for_status = MagicMock()
    with patch("src.social_agent.telegram.httpx.post", return_value=fake_response) as post:
        msg_id = tg.send_draft(draft_id=3, pillar="stats", text="x", image_path=None)
    assert msg_id == "7"
    assert "sendMessage" in post.call_args[0][0]
    assert "Draft #3" in post.call_args[1]["data"]["text"]
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement Telegram module**

Replace contents of `src/social_agent/telegram.py`:

```python
"""Telegram Bot API wrapper (httpx, no MCP dependency)."""
from __future__ import annotations

import httpx

from src.credentials import get_credential


BASE = "https://api.telegram.org/bot"


def _bot_token() -> str:
    t = get_credential("telegram_bot_token")
    if not t:
        raise RuntimeError(
            "telegram_bot_token not set. Configure via: "
            "python -m src.credentials set telegram_bot_token"
        )
    return t


def _operator_chat_id() -> str:
    c = get_credential("telegram_operator_chat_id")
    if not c:
        raise RuntimeError(
            "telegram_operator_chat_id not set. Configure via: "
            "python -m src.credentials set telegram_operator_chat_id"
        )
    return c


def _caption(draft_id: int, pillar: str, text: str) -> str:
    return (
        f"Draft #{draft_id} · {pillar}\n\n"
        f"{text}\n\n—\n"
        f"Approve: `ok {draft_id}` · Skip: `skip {draft_id}` · "
        f"Revise: `{draft_id} <instruction>`"
    )


def send_draft(
    draft_id: int, pillar: str, text: str, image_path: str | None
) -> str:
    """Send a draft preview to the operator's Telegram chat.

    Returns the Telegram message_id as string so it can be stored in social_drafts.
    """
    token = _bot_token()
    chat_id = _operator_chat_id()
    caption = _caption(draft_id, pillar, text)

    if image_path:
        url = f"{BASE}{token}/sendPhoto"
        with open(image_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            resp = httpx.post(url, data=data, files=files, timeout=30.0)
    else:
        url = f"{BASE}{token}/sendMessage"
        data = {"chat_id": chat_id, "text": caption, "parse_mode": "Markdown"}
        resp = httpx.post(url, data=data, timeout=30.0)

    resp.raise_for_status()
    return str(resp.json()["result"]["message_id"])
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/telegram.py tests/social_agent/test_telegram.py
git commit -m "feat(social-agent): Telegram sendPhoto/sendMessage wrapper"
```

---

### Task 19: Reply command parser

**Files:**
- Modify: `src/social_agent/telegram.py`
- Modify: `tests/social_agent/test_telegram.py`

- [ ] **Step 1: Append failing test**

Append to `tests/social_agent/test_telegram.py`:

```python
def test_parse_ok_command():
    cmd = tg.parse_reply("ok 42")
    assert cmd == {"action": "ok", "draft_id": 42, "instruction": None}


def test_parse_skip_command():
    cmd = tg.parse_reply("skip 42")
    assert cmd == {"action": "skip", "draft_id": 42, "instruction": None}


def test_parse_revise_command():
    cmd = tg.parse_reply("42 pārraksti īsāk un bez emoji")
    assert cmd == {
        "action": "revise",
        "draft_id": 42,
        "instruction": "pārraksti īsāk un bez emoji",
    }


def test_parse_with_extra_whitespace():
    assert tg.parse_reply("  ok   42  ") == {
        "action": "ok", "draft_id": 42, "instruction": None
    }


def test_parse_returns_none_on_garbage():
    assert tg.parse_reply("hello there") is None
    assert tg.parse_reply("") is None
    assert tg.parse_reply("42") is None  # id without instruction is ambiguous
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement parser**

Append to `src/social_agent/telegram.py`:

```python
import re


_CMD_PREFIX_RE = re.compile(r"^\s*(ok|skip)\s+(\d+)\s*$", re.IGNORECASE)
_CMD_REVISE_RE = re.compile(r"^\s*(\d+)\s+(\S.*\S|\S)\s*$")


def parse_reply(text: str) -> dict | None:
    """Parse an operator reply into a command dict or None if unrecognized.

    Forms:
      - "ok <id>"              → {"action": "ok", "draft_id": N, "instruction": None}
      - "skip <id>"            → {"action": "skip", ...}
      - "<id> <freetext>"      → {"action": "revise", "instruction": "<freetext>"}
    """
    if not text:
        return None
    m = _CMD_PREFIX_RE.match(text)
    if m:
        return {"action": m.group(1).lower(), "draft_id": int(m.group(2)), "instruction": None}
    m = _CMD_REVISE_RE.match(text)
    if m:
        instruction = m.group(2).strip()
        # Guard: "ok 42" already handled above; revise instruction must not start with those
        return {"action": "revise", "draft_id": int(m.group(1)), "instruction": instruction}
    return None
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/telegram.py tests/social_agent/test_telegram.py
git commit -m "feat(social-agent): Telegram reply parser"
```

---

## Phase 8 — CLI glue

### Task 20: `brainstorm` subcommand

**Files:**
- Modify: `src/social_agent/cli.py`
- Create: `tests/social_agent/test_cli_brainstorm.py`

- [ ] **Step 1: Write failing test with full pipeline mocked**

`tests/social_agent/test_cli_brainstorm.py`:

```python
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.db import init_db
from src.social_agent import cli


@pytest.fixture
def fresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    monkeypatch.setattr("src.social_agent.storage.DB_PATH", path, raising=False)
    monkeypatch.setattr("src.social_agent.candidates.DB_PATH", path, raising=False)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_brainstorm_empty_db_exits_cleanly(fresh_db, capsys):
    with patch("src.social_agent.cli.send_draft") as send:
        rc = cli.brainstorm_cmd(db_path=fresh_db)
    assert rc == 0
    send.assert_not_called()
    out = capsys.readouterr().out
    assert "No candidates" in out or "nav kandidātu" in out.lower()


def test_brainstorm_with_seeded_contradictions_sends_drafts(fresh_db):
    # Seed one contradiction
    from src.db import get_db
    db = get_db(fresh_db)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'X', 'JV')")
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (10, 1, 't', 'par', 'A', '2026-04-01', 'u1'), "
        "       (11, 1, 't', 'pret', 'B', '2026-04-18', 'u2')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) "
        "VALUES (100, 1, 10, 11, 't', 's', 'critical', 0.9, '2026-04-18 10:00:00')"
    )
    db.commit()
    db.close()

    with patch("src.social_agent.cli.send_draft", return_value="777") as send, \
         patch("src.social_agent.cli.render_quote_card") as qc, \
         patch("src.social_agent.cli.render_chart"), \
         patch("src.social_agent.cli.render_illustration"):
        qc.side_effect = lambda payload, out_path: out_path.parent.mkdir(
            parents=True, exist_ok=True
        ) or out_path.write_bytes(b"PNG") or out_path
        rc = cli.brainstorm_cmd(db_path=fresh_db)
    assert rc == 0
    assert send.call_count == 1
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement brainstorm CLI**

Replace contents of `src/social_agent/cli.py`:

```python
"""CLI entry points: brainstorm, approve, skip, revise, resend."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from src.db import DB_PATH
from src.social_agent.candidates import (
    fetch_pretrunas_candidates,
    fetch_stats_candidate,
    fetch_highlights_candidates,
    interest_score,
    select_top_n,
)
from src.social_agent.drafters import draft_pretrunas, draft_stats, draft_highlight
from src.social_agent.visuals import render_chart, render_quote_card, render_illustration
from src.social_agent.storage import (
    create_draft,
    get_draft,
    mark_approved,
    mark_rejected,
    mark_posted,
    mark_failed,
    mark_revising,
    list_pending_drafts,
)
from src.social_agent.telegram import send_draft, parse_reply
from src.social_agent.publisher import publish_draft


DRAFTS_DIR = Path("data/social/drafts")


def _topics_posted_last_7d(db_path: str) -> set[str]:
    from src.db import get_db
    db = get_db(db_path)
    rows = db.execute(
        """
        SELECT source_data_json FROM social_drafts
        WHERE status IN ('approved', 'posted')
          AND created_at >= datetime('now', '-7 days')
        """
    ).fetchall()
    db.close()
    out: set[str] = set()
    for r in rows:
        try:
            sd = json.loads(r["source_data_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        t = sd.get("topic")
        if isinstance(t, str):
            out.add(t)
    return out


def _hours_since(ts_iso: str | None) -> float:
    if not ts_iso:
        return 9999.0
    try:
        t = datetime.fromisoformat(ts_iso.replace("T", " ").replace("Z", ""))
    except ValueError:
        return 9999.0
    return max(0.0, (datetime.utcnow() - t).total_seconds() / 3600.0)


def brainstorm_cmd(db_path: str = DB_PATH) -> int:
    recent = _topics_posted_last_7d(db_path)

    pool: list[dict] = []

    # Pretrunas
    for r in fetch_pretrunas_candidates(db_path=db_path):
        score = interest_score(
            salience=float(r.get("salience") or 0.5),
            severity=r.get("severity"),
            age_hours=_hours_since(r.get("detected_at")),
            candidate_topics={r.get("topic", "")} if r.get("topic") else set(),
            recent_topics=recent,
        )
        pool.append({"pillar": "pretrunas", "score": score, "payload": r})

    # Stats (single-candidate pillar)
    stats = fetch_stats_candidate(db_path=db_path)
    if stats is not None:
        score = interest_score(
            salience=0.6, severity=None, age_hours=0,
            candidate_topics={"aktivitāte"}, recent_topics=recent,
        )
        pool.append({"pillar": "stats", "score": score, "payload": stats})

    # Highlights
    for r in fetch_highlights_candidates(db_path=db_path):
        score = interest_score(
            salience=0.6, severity=None,
            age_hours=_hours_since(r.get("created_at")),
            candidate_topics={r.get("topic", "")} if r.get("topic") else set(),
            recent_topics=recent,
        )
        pool.append({"pillar": "highlights", "score": score, "payload": r})

    picked = select_top_n(pool, n=3, per_pillar_cap=2)
    if not picked:
        print("[social_agent] No candidates — nothing to draft.")
        return 0

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    for entry in picked:
        pillar = entry["pillar"]
        payload = entry["payload"]

        # Render text + visual
        if pillar == "pretrunas":
            text = draft_pretrunas(payload)
            source_data = {
                "contradiction_id": payload["contradiction_id"],
                "topic": payload["topic"],
            }
            image_out = DRAFTS_DIR / f"draft_pending_{id(payload)}.png"
            try:
                render_quote_card(
                    {
                        "politician_name": payload["politician_name"],
                        "topic": payload["topic"],
                        "old_quote": payload.get("old_quote") or "",
                        "old_date": (payload.get("old_stated_at") or "")[:10],
                        "new_quote": payload.get("new_quote") or "",
                        "new_date": (payload.get("new_stated_at") or "")[:10],
                    },
                    out_path=image_out,
                )
                image_path = str(image_out)
            except Exception as e:
                print(f"[social_agent] quote_card failed for pretrunas: {e}", file=sys.stderr)
                image_path = None
        elif pillar == "stats":
            text = draft_stats(payload)
            source_data = {"iso_week": payload["iso_week"], "topic": "aktivitāte"}
            image_out = DRAFTS_DIR / f"draft_pending_stats_{payload['iso_week']}.png"
            try:
                render_chart(payload, out_path=image_out)
                image_path = str(image_out)
            except Exception as e:
                print(f"[social_agent] chart failed: {e}", file=sys.stderr)
                image_path = None
        else:  # highlights
            text = draft_highlight(payload)
            if payload.get("kind") == "attack":
                source_data = {
                    "kind": "attack",
                    "brief_id": payload["brief_id"],
                    "attack_index": payload["attack_index"],
                    "topic": None,
                }
            else:
                source_data = {
                    "kind": "tension",
                    "tension_id": payload["tension_id"],
                    "topic": payload.get("topic"),
                }
            # Highlights default to illustration; skip if unavailable
            image_out = DRAFTS_DIR / f"draft_pending_hl_{id(payload)}.png"
            try:
                subject = payload.get("topic") or "politiska spriedze"
                render_illustration({"subject": subject}, out_path=image_out)
                image_path = str(image_out)
            except Exception as e:
                print(f"[social_agent] illustration failed: {e}", file=sys.stderr)
                image_path = None

        # Persist + send
        draft_id = create_draft(
            pillar=pillar,
            text=text,
            image_path=image_path,
            source_data=source_data,
            score=entry["score"],
            db_path=db_path,
        )
        # Rename the pending image file to its canonical draft_<id>.png
        if image_path:
            canonical = DRAFTS_DIR / f"draft_{draft_id}.png"
            try:
                Path(image_path).replace(canonical)
                from src.social_agent.storage import get_draft as _g
                # Patch DB to point at the renamed file
                from src.db import get_db
                db = get_db(db_path)
                db.execute(
                    "UPDATE social_drafts SET image_path = ? WHERE id = ?",
                    (str(canonical), draft_id),
                )
                db.commit()
                db.close()
                image_path = str(canonical)
            except OSError:
                pass

        try:
            msg_id = send_draft(
                draft_id=draft_id, pillar=pillar, text=text, image_path=image_path
            )
            from src.db import get_db
            db = get_db(db_path)
            db.execute(
                "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
                (msg_id, draft_id),
            )
            db.commit()
            db.close()
            print(f"[social_agent] Sent draft #{draft_id} ({pillar}) score={entry['score']:.2f}")
        except Exception as e:
            print(f"[social_agent] Telegram send failed for #{draft_id}: {e}", file=sys.stderr)

    return 0
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/cli.py tests/social_agent/test_cli_brainstorm.py
git commit -m "feat(social-agent): brainstorm CLI — pool→select→render→send"
```

---

### Task 21: `approve` / `skip` / `revise` / `resend` subcommands + `main()`

**Files:**
- Modify: `src/social_agent/cli.py`
- Create: `tests/social_agent/test_cli_actions.py`

- [ ] **Step 1: Write failing test**

`tests/social_agent/test_cli_actions.py`:

```python
import os
import tempfile
from unittest.mock import patch

import pytest

from src.db import init_db
from src.social_agent import cli
from src.social_agent.storage import create_draft, get_draft


@pytest.fixture
def fresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_approve_cmd_posts_and_marks(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="t", image_path=None,
        source_data={}, score=0.8, db_path=fresh_db,
    )
    with patch("src.social_agent.cli.publish_draft", return_value="tw-42"):
        rc = cli.approve_cmd(did, db_path=fresh_db)
    assert rc == 0
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "posted"
    assert row["tweet_id"] == "tw-42"


def test_approve_cmd_marks_failed_on_error(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="t", image_path=None,
        source_data={}, score=0.8, db_path=fresh_db,
    )
    with patch("src.social_agent.cli.publish_draft", side_effect=RuntimeError("boom")):
        rc = cli.approve_cmd(did, db_path=fresh_db)
    assert rc != 0
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "failed"
    assert "boom" in row["error_message"]


def test_skip_cmd(fresh_db):
    did = create_draft(
        pillar="stats", text="t", image_path=None,
        source_data={}, score=0.5, db_path=fresh_db,
    )
    rc = cli.skip_cmd(did, db_path=fresh_db)
    assert rc == 0
    assert get_draft(did, db_path=fresh_db)["status"] == "rejected"


def test_revise_cmd_creates_child_and_sends(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="original long version",
        image_path=None, source_data={"contradiction_id": 100}, score=0.8,
        db_path=fresh_db,
    )
    with patch("src.social_agent.cli.send_draft", return_value="mid-77") as send, \
         patch("src.social_agent.cli.llm_rewrite", return_value="short version") as llm:
        rc = cli.revise_cmd(did, instruction="pārraksti īsāk", db_path=fresh_db)
    assert rc == 0
    llm.assert_called_once()
    send.assert_called_once()
    # Parent is 'revising'; child exists with new text
    parent = get_draft(did, db_path=fresh_db)
    assert parent["status"] == "revising"


def test_main_dispatches_brainstorm():
    with patch("src.social_agent.cli.brainstorm_cmd", return_value=0) as bs:
        cli.main(argv=["brainstorm"])
        bs.assert_called_once()


def test_main_dispatches_approve():
    with patch("src.social_agent.cli.approve_cmd", return_value=0) as ap:
        cli.main(argv=["approve", "42"])
        ap.assert_called_once_with(42)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement remaining CLI**

Append to `src/social_agent/cli.py`:

```python
def llm_rewrite(original_text: str, instruction: str) -> str:
    """Regenerate a draft using the provided free-text instruction.

    MVP: minimal heuristic fallback — if the instruction includes "īs" (shorter)
    return the first sentence; if "bez emoji" strip common emoji chars; otherwise
    just prepend the instruction marker. A proper LLM call (Claude API) can replace
    this later — keeping the interface stable.
    """
    import re

    txt = original_text
    if "īs" in instruction.lower() or "short" in instruction.lower():
        # Take up to the first sentence break
        parts = re.split(r"(?<=[.!?])\s+", txt)
        if parts:
            txt = parts[0]
    if "bez emoji" in instruction.lower() or "no emoji" in instruction.lower():
        txt = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", txt)
    return txt.strip()[:280]


def approve_cmd(draft_id: int, db_path: str = DB_PATH) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    if draft["status"] != "pending":
        print(f"[social_agent] Draft #{draft_id} is {draft['status']}, not pending",
              file=sys.stderr)
        return 3
    mark_approved(draft_id, db_path=db_path)
    try:
        tweet_id = publish_draft(text=draft["text"], image_path=draft["image_path"])
    except Exception as e:
        mark_failed(draft_id, error_message=str(e), db_path=db_path)
        print(f"[social_agent] Publish failed: {e}", file=sys.stderr)
        return 1
    mark_posted(draft_id, tweet_id=tweet_id, db_path=db_path)
    print(f"[social_agent] Posted draft #{draft_id} → tweet {tweet_id}")
    return 0


def skip_cmd(draft_id: int, db_path: str = DB_PATH) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    mark_rejected(draft_id, db_path=db_path)
    print(f"[social_agent] Skipped draft #{draft_id}")
    return 0


def revise_cmd(draft_id: int, instruction: str, db_path: str = DB_PATH) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    new_text = llm_rewrite(draft["text"], instruction)
    child_id = mark_revising(draft_id, new_text=new_text, db_path=db_path)
    child = get_draft(child_id, db_path=db_path)
    try:
        msg_id = send_draft(
            draft_id=child_id, pillar=child["pillar"],
            text=child["text"], image_path=child["image_path"],
        )
        from src.db import get_db
        db = get_db(db_path)
        db.execute(
            "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
            (msg_id, child_id),
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[social_agent] Telegram send of revised draft failed: {e}",
              file=sys.stderr)
        return 1
    print(f"[social_agent] Revised draft #{draft_id} → new draft #{child_id}")
    return 0


def resend_cmd(draft_id: int, db_path: str = DB_PATH) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    try:
        msg_id = send_draft(
            draft_id=draft_id, pillar=draft["pillar"],
            text=draft["text"], image_path=draft["image_path"],
        )
    except Exception as e:
        print(f"[social_agent] Resend failed: {e}", file=sys.stderr)
        return 1
    from src.db import get_db
    db = get_db(db_path)
    db.execute(
        "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
        (msg_id, draft_id),
    )
    db.commit()
    db.close()
    print(f"[social_agent] Resent draft #{draft_id} (msg {msg_id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="social_agent", description="X posting agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("brainstorm", help="Select top-3 candidates and send drafts to Telegram")

    p_approve = sub.add_parser("approve", help="Post an approved draft to X")
    p_approve.add_argument("draft_id", type=int)

    p_skip = sub.add_parser("skip", help="Reject a draft without posting")
    p_skip.add_argument("draft_id", type=int)

    p_rev = sub.add_parser("revise", help="Regenerate a draft with an instruction")
    p_rev.add_argument("draft_id", type=int)
    p_rev.add_argument("instruction", nargs="+")

    p_rs = sub.add_parser("resend", help="Re-send an existing draft to Telegram")
    p_rs.add_argument("draft_id", type=int)

    args = parser.parse_args(argv)

    if args.command == "brainstorm":
        return brainstorm_cmd()
    if args.command == "approve":
        return approve_cmd(args.draft_id)
    if args.command == "skip":
        return skip_cmd(args.draft_id)
    if args.command == "revise":
        return revise_cmd(args.draft_id, instruction=" ".join(args.instruction))
    if args.command == "resend":
        return resend_cmd(args.draft_id)
    return 2
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/social_agent/ -v
```

All `tests/social_agent/` tests should pass.

- [ ] **Step 5: Commit**

```bash
git add src/social_agent/cli.py tests/social_agent/test_cli_actions.py
git commit -m "feat(social-agent): approve/skip/revise/resend CLI + main dispatch"
```

---

## Phase 9 — Manual smoke test

### Task 22: End-to-end smoke test against @atmina_lv

**Files:**
- Create: `scripts/social_agent_smoke.md` (a manual checklist, NOT code)

- [ ] **Step 1: Write the manual test checklist**

Create `scripts/social_agent_smoke.md`:

```markdown
# Social Agent — Manual Smoke Test

Run this checklist in order. Do NOT skip the test-account step.

## 1. Prereqs

- [ ] `data/x_cookies_atmina.json` exists (cookies for @atmina_lv; can be a burner account for this pass)
- [ ] Telegram bot token + operator chat id populated:
  - `python -m src.credentials set telegram_bot_token`
  - `python -m src.credentials set telegram_operator_chat_id`
  - `python -m src.credentials set x_atmina_cookies_path`
- [ ] Playwright chromium installed: `python -m playwright install chromium`

## 2. Unit tests

```bash
.venv/Scripts/activate
python -m pytest tests/social_agent/ -v
```

All must pass.

## 3. Dry brainstorm (burner X account)

```bash
python -m src.social_agent brainstorm
```

- [ ] Up to 3 drafts arrive on Telegram as separate messages, each with image + caption
- [ ] Each caption contains: `Draft #<N>`, pillar name, draft text (≤280 chars), the command hints

## 4. Skip path

```bash
python -m src.social_agent skip <draft_id_from_step_3>
```

- [ ] CLI prints `Skipped draft #<id>`
- [ ] `SELECT status FROM social_drafts WHERE id=<id>` returns `rejected`
- [ ] No tweet posted

## 5. Revise path

```bash
python -m src.social_agent revise <draft_id> pārraksti īsāk
```

- [ ] CLI prints `Revised draft #<id> → new draft #<N>`
- [ ] Parent status is `revising`; new child draft arrives on Telegram
- [ ] Child text is shorter than parent

## 6. Approve path (burner account)

```bash
python -m src.social_agent approve <draft_id>
```

- [ ] CLI prints `Posted draft #<id> → tweet <tweet_id>`
- [ ] Tweet is visible on the burner account with correct text + image
- [ ] `SELECT status, tweet_id FROM social_drafts WHERE id=<id>` returns `posted, <tweet_id>`

## 7. Failure path

- [ ] Deliberately break cookies (rename `data/x_cookies_atmina.json` to `.bak`)
- [ ] Run `python -m src.social_agent approve <another_pending_id>`
- [ ] CLI exits non-zero; status becomes `failed`; `error_message` is informative
- [ ] Restore cookies

## 8. Switch to @atmina_lv

- [ ] Replace `data/x_cookies_atmina.json` with real @atmina_lv cookies
- [ ] Re-run `brainstorm` → approve one pretrunas draft
- [ ] Verify on https://x.com/atmina_lv

## Rollback

If anything misbehaves, no data loss risk — draft rows can be marked `rejected` and the table is isolated. Revert the feature by dropping the table: `DROP TABLE social_drafts;` and removing the `src/social_agent/` package.
```

- [ ] **Step 2: Commit**

```bash
git add scripts/social_agent_smoke.md
git commit -m "docs(social-agent): manual smoke test checklist"
```

- [ ] **Step 3: Execute the smoke test (manual — operator-driven)**

Walk through `scripts/social_agent_smoke.md` step by step. Do NOT mark the plan complete until every checkbox in that file passes.

---

## Verification

Before declaring the MVP shipped, run:

```bash
.venv/Scripts/activate
python -m pytest tests/social_agent/ -v
python -m pytest tests/ -v --ignore=tests/social_agent  # regression: no other tests broken
```

Expected: all green. No new warnings in `tests/test_db.py`.

Then walk through `scripts/social_agent_smoke.md` as described in Task 22.
