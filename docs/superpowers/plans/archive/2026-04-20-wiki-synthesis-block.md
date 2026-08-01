# Wiki Person Synthesis Block Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `wiki/persons/*.md` with a conditional auto-generated bullet list (between `<!-- SYNC-AUTO -->` / `<!-- /SYNC-AUTO -->` markers) that surfaces synthesis signal, while preserving any manual body content.

**Architecture:** `wiki_sync()` gains a post-frontmatter render step that computes 4 signal queries per politician (top topics, 30d activity, tensions, contradictions), composes a minimal bullet list where each bullet appears only if its threshold is met, and writes the block between sync markers in the body. When signal is below all thresholds, the block is absent entirely (empty body is a valid state). Manual content outside markers is never modified.

**Tech Stack:** Python 3.11+, SQLite (WAL), existing `src/wiki.py` infrastructure, pytest.

**Design decisions (locked in via brainstorm 2026-04-20):**
- **4 bullets max**, not 5. Rhetoric-vs-action gap is surfaced inside the contradictions bullet via claim_type labels — no separate bullet (avoids over-engineering for <11 total contradictions in the system).
- **No section headers** inside the block. Just `- **Label:** content` bullets.
- **Per-bullet threshold skip** — no "Nav spriedžu" padding; a bullet either has signal or is absent.
- **Hard-fail overflow** — render raises if block > 1500 chars. Visible, not silent.
- **Manual content preserved outside markers.** The auto block replaces content between markers; everything else stays.

**Rollback:** Single commit per task. Revert via `git revert <sha>`. No schema changes, no data migration.

---

## File Structure

**Files to modify:**
- `src/wiki.py` — three new helpers + wiki_sync integration:
  - `_gather_person_signal(db, pid) -> dict` — runs 4 SQL queries, returns signal dict
  - `_render_person_synthesis(signal) -> str` — composes bullet list with threshold checks
  - `_update_page_with_sync_block(path, frontmatter, sync_block)` — marker-aware writer
  - `wiki_sync()` integration: call the above for each politician

**Files to create:**
- (none — all logic lives in `src/wiki.py`; tests extend existing `tests/test_wiki.py`)

**Bullet rendering contract:**

| Bullet | Label | Threshold | Format |
|---|---|---|---|
| 1 | Top tēmas | ≥3 topics with ≥2 position claims each | `- **Top tēmas:** [[A]] (N%), [[B]] (N%), [[C]] (N%)` — max 3 |
| 2 | 30d | ≥1 position claim in last 30 days | `- **30d:** N claims, Mx bāzes līnija` OR `- **30d:** N claims` (if 90d avg < 2/month) |
| 3 | Spriedzes | ≥1 tension with target_pid | `- **Spriedzes:** [[Name]] (N tips), ...` — max 3 |
| 4 | Pretrunas | ≥1 confirmed contradiction | `- **Pretrunas:** N apstiprinātas (X retorika↔balsojums, Y pozīciju maiņa; pēdējā par [[topic]], DATE)` |

**Threshold queries return None/empty when signal insufficient. Render function skips bullets whose signal is None.**

---

## Task 1: Marker-aware Page Update Helper

**Files:**
- Modify: `src/wiki.py` — add `_update_page_with_sync_block()` function
- Test: `tests/test_wiki.py` — add tests for sync block insertion, replacement, removal

- [ ] **Step 1.1: Write the failing tests**

In `tests/test_wiki.py`, append (import at top if needed):

```python
from pathlib import Path

from src.wiki import _update_page_with_sync_block


def test_sync_block_inserted_into_new_page(tmp_path):
    """New page gets frontmatter + sync block, nothing else."""
    page = tmp_path / "test.md"
    fm = {"name": "Test", "claims": 3}
    block = "- **Top tēmas:** [[A]] (50%), [[B]] (30%)\n"

    _update_page_with_sync_block(page, fm, block)

    text = page.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "<!-- SYNC-AUTO -->" in text
    assert "<!-- /SYNC-AUTO -->" in text
    assert "**Top tēmas:**" in text


def test_sync_block_empty_no_markers_written(tmp_path):
    """Empty block means no markers in output — body stays clean."""
    page = tmp_path / "test.md"
    fm = {"name": "Test", "claims": 0}

    _update_page_with_sync_block(page, fm, "")

    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" not in text
    assert "<!-- /SYNC-AUTO -->" not in text


def test_sync_block_replaces_existing(tmp_path):
    """Existing sync block is replaced with new content; manual text preserved."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\n"
        "Manuālais konteksts paliek.\n\n"
        "<!-- SYNC-AUTO -->\n"
        "- **vecs:** dati\n"
        "<!-- /SYNC-AUTO -->\n\n"
        "Vairāk manuāla teksta.\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(
        page,
        {"name": "Test"},
        "- **Top tēmas:** [[A]] (50%)\n",
    )

    text = page.read_text(encoding="utf-8")
    assert "Manuālais konteksts paliek." in text
    assert "Vairāk manuāla teksta." in text
    assert "vecs:" not in text
    assert "**Top tēmas:**" in text
    # Verify markers still exist exactly once
    assert text.count("<!-- SYNC-AUTO -->") == 1
    assert text.count("<!-- /SYNC-AUTO -->") == 1


def test_sync_block_removed_when_empty(tmp_path):
    """If block becomes empty, existing markers + content are removed; manual preserved."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\n"
        "Manuālais konteksts.\n\n"
        "<!-- SYNC-AUTO -->\n"
        "- **vecs:** dati\n"
        "<!-- /SYNC-AUTO -->\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(page, {"name": "Test"}, "")

    text = page.read_text(encoding="utf-8")
    assert "Manuālais konteksts." in text
    assert "<!-- SYNC-AUTO -->" not in text
    assert "vecs:" not in text


def test_sync_block_appended_to_existing_body_without_markers(tmp_path):
    """Existing page with manual body but no markers: block is appended after body."""
    page = tmp_path / "test.md"
    page.write_text(
        "---\nname: Test\n---\n\nManuāls saturs.\n",
        encoding="utf-8",
    )

    _update_page_with_sync_block(
        page,
        {"name": "Test"},
        "- **Top tēmas:** [[A]] (50%)\n",
    )

    text = page.read_text(encoding="utf-8")
    # Manual content is before markers
    manual_idx = text.index("Manuāls saturs.")
    marker_idx = text.index("<!-- SYNC-AUTO -->")
    assert manual_idx < marker_idx
    assert "**Top tēmas:**" in text
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py::test_sync_block_inserted_into_new_page tests/test_wiki.py::test_sync_block_empty_no_markers_written tests/test_wiki.py::test_sync_block_replaces_existing tests/test_wiki.py::test_sync_block_removed_when_empty tests/test_wiki.py::test_sync_block_appended_to_existing_body_without_markers -v
```

Expected: all 5 FAIL with `ImportError` or `AttributeError: no attribute '_update_page_with_sync_block'`.

- [ ] **Step 1.3: Re-read current `_update_page` in `src/wiki.py`**

Read `src/wiki.py` lines 80-97 to remember the existing `_update_page` signature and body-preservation behavior. The new function must not interfere.

- [ ] **Step 1.4: Implement `_update_page_with_sync_block`**

Add this function to `src/wiki.py` **after** the existing `_update_page` (around line 98):

```python
_SYNC_START = "<!-- SYNC-AUTO -->"
_SYNC_END = "<!-- /SYNC-AUTO -->"


def _update_page_with_sync_block(
    path: Path,
    new_frontmatter: dict,
    sync_block: str,
) -> None:
    """Create or update a wiki page with a sync-marked auto block.

    Behavior:
      - Frontmatter is always replaced by `new_frontmatter`.
      - Any existing content between SYNC markers is replaced by `sync_block`
        (or removed entirely if `sync_block` is empty).
      - Manual body content outside the markers is preserved verbatim.
      - If page is new and `sync_block` is non-empty: creates frontmatter +
        markers + sync_block. If empty: creates frontmatter only.
      - If page exists without markers and `sync_block` is non-empty: appends
        markers + sync_block to end of body (manual content above).
    """
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        _old_fm, body = _parse_frontmatter(existing)
    else:
        body = ""

    # Strip any existing sync block from the body.
    body = _strip_sync_block(body)

    # Rebuild body: manual content + (optional) new sync block.
    if sync_block.strip():
        block_text = f"{_SYNC_START}\n{sync_block.rstrip()}\n{_SYNC_END}\n"
        if body.strip():
            body = body.rstrip() + "\n\n" + block_text
        else:
            body = block_text

    content = _render_frontmatter(new_frontmatter)
    if body:
        content += "\n" + body

    path.write_text(content, encoding="utf-8")


def _strip_sync_block(body: str) -> str:
    """Remove the SYNC-AUTO markers and their content from `body`.

    If no markers present, returns `body` unchanged. If multiple marker pairs
    exist (should not happen in practice), removes only the first pair and
    leaves subsequent markers intact — a follow-up sync call will re-normalize.
    """
    start_idx = body.find(_SYNC_START)
    if start_idx == -1:
        return body
    end_marker_idx = body.find(_SYNC_END, start_idx)
    if end_marker_idx == -1:
        # Malformed: start without end. Leave body untouched so operator can fix manually.
        return body
    end_idx = end_marker_idx + len(_SYNC_END)
    # Also consume one trailing newline if present.
    if end_idx < len(body) and body[end_idx] == "\n":
        end_idx += 1
    before = body[:start_idx].rstrip()
    after = body[end_idx:].lstrip()
    if before and after:
        return before + "\n\n" + after
    return before or after
```

- [ ] **Step 1.5: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k sync_block -v
```

Expected: all 5 new tests PASS. Full `tests/test_wiki.py` suite should still pass.

- [ ] **Step 1.6: Run full wiki test suite to check no regressions**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py tests/test_wiki_lint.py -v
```

Expected: all tests pass.

- [ ] **Step 1.7: Commit**

```bash
git add src/wiki.py tests/test_wiki.py
git commit -m "feat(wiki): marker-aware page update helper for sync blocks"
```

---

## Task 2: Signal Gathering Function

**Files:**
- Modify: `src/wiki.py` — add `_gather_person_signal()`
- Test: `tests/test_wiki.py` — fixture DB + 4-signal verification

- [ ] **Step 2.1: Write the failing tests**

Append to `tests/test_wiki.py`:

```python
import sqlite3

import pytest

import src.db as db_mod
import src.wiki as wiki_mod
from src.wiki import _gather_person_signal


@pytest.fixture
def wiki_tmp_db(tmp_path, monkeypatch):
    """Fresh DB with schema, used for wiki signal tests."""
    db_path = str(tmp_path / "wiki_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected)
    monkeypatch.setattr(wiki_mod, "get_db", _redirected, raising=False)

    conn = orig_get_db(db_path)
    yield conn
    conn.close()


def test_signal_empty_for_politician_with_no_data(wiki_tmp_db):
    """Politician with 0 claims returns empty signal — all fields None/empty."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'Empty', '[]')"
    )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["top_topics"] == []
    assert signal["activity_30d"] is None
    assert signal["tensions"] == []
    assert signal["contradictions"] is None


def test_signal_top_topics_requires_3_topics_with_2_claims_each(wiki_tmp_db):
    """With 2 topics × 3 claims each, top_topics stays empty (need ≥3 topics)."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    # 2 topics, 3 claims each
    for topic in ("Budžets", "Imigrācija"):
        for i in range(3):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, '2026-04-15', 'position')""",
                (topic, f"stance-{i}", f"https://x.com/p/status/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["top_topics"] == []


def test_signal_top_topics_populated_when_3_topics_have_2_claims(wiki_tmp_db):
    """3 topics × 2 claims each → top_topics has 3 entries with percentages."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    topics = ("Budžets", "Imigrācija", "Aizsardzība", "Vēlēšanas")
    counts = {"Budžets": 5, "Imigrācija": 3, "Aizsardzība": 2, "Vēlēšanas": 2}
    for topic in topics:
        for i in range(counts[topic]):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, '2026-04-15', 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/status/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    # Only top 3 returned, ordered by count desc
    assert len(signal["top_topics"]) == 3
    assert signal["top_topics"][0]["topic"] == "Budžets"
    assert signal["top_topics"][0]["count"] == 5
    assert signal["top_topics"][0]["pct"] == 42  # 5/12 = 41.67 → 42
    # All three topics each have ≥2 claims


def test_signal_tensions_returns_top_3_by_count(wiki_tmp_db):
    """Tensions bucket by target_pid, top 3 by count."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'A', '[]')"
    )
    for tpid, tname in ((10, "B"), (20, "C"), (30, "D"), (40, "E")):
        wiki_tmp_db.execute(
            "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?, ?, '[]')",
            (tpid, tname),
        )
    # A → B: 3 attacks, A → C: 2, A → D: 1, A → E: 1
    counts = {10: 3, 20: 2, 30: 1, 40: 1}
    for tpid, n in counts.items():
        for i in range(n):
            wiki_tmp_db.execute(
                """INSERT INTO political_tensions
                   (source_pid, target_pid, topic, description, tension_type, source_url)
                   VALUES (1, ?, 'T', 'd', 'uzbrukums', ?)""",
                (tpid, f"https://x.com/a/status/{tpid}_{i}"),
            )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert len(signal["tensions"]) == 3
    assert signal["tensions"][0]["target_pid"] == 10
    assert signal["tensions"][0]["target_name"] == "B"
    assert signal["tensions"][0]["count"] == 3


def test_signal_contradictions_only_confirmed(wiki_tmp_db):
    """Only confirmed=1 contradictions count; unreviewed are ignored."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    # Create two claims for FK
    for i in (1, 2, 3, 4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (id, opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (?, 1, 'T', ?, 0.8, 0.5, ?, '2026-04-15', ?)""",
            (i, f"s-{i}", f"https://x.com/p/{i}", "position" if i < 3 else "saeima_vote"),
        )
    # Confirmed pos-pos + unconfirmed pos-vote + confirmed pos-vote
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 1, 2, 'Budžets', 'shift', 'reversal', 1, 1, '2026-04-10')"""
    )
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 1, 3, 'Aizsardzība', 'vote-gap', 'direct_contradiction', 0, 0, '2026-04-11')"""
    )
    wiki_tmp_db.execute(
        """INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic,
           summary, severity, confirmed, reviewed, detected_at)
           VALUES (1, 2, 4, 'Budžets', 'vote-gap', 'direct_contradiction', 1, 1, '2026-04-12')"""
    )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    # 2 confirmed total: 1 pos-pos + 1 pos-vote
    assert signal["contradictions"] is not None
    assert signal["contradictions"]["total"] == 2
    assert signal["contradictions"]["rhetoric_action"] == 1
    assert signal["contradictions"]["position_shift"] == 1
    assert signal["contradictions"]["last_topic"] == "Budžets"
    assert signal["contradictions"]["last_date"].startswith("2026-04-12")


def test_signal_activity_30d_with_and_without_baseline(wiki_tmp_db):
    """Activity bullet: shows count. Ratio only when 90d baseline ≥ 6."""
    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (1, 'P', '[]')"
    )
    # 4 recent claims (last 30d), 4 older claims (30-90d ago)
    for i in range(4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (1, 'T', ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
            (f"r{i}", f"https://x.com/p/r{i}"),
        )
    for i in range(4):
        wiki_tmp_db.execute(
            """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                   source_url, stated_at, claim_type)
               VALUES (1, 'T', ?, 0.8, 0.5, ?, date('now', '-45 days'), 'position')""",
            (f"o{i}", f"https://x.com/p/o{i}"),
        )
    wiki_tmp_db.commit()

    signal = _gather_person_signal(wiki_tmp_db, 1)
    assert signal["activity_30d"] is not None
    assert signal["activity_30d"]["count"] == 4
    # 90d total = 8 → baseline avg = 8/3 ≈ 2.67. Below 6, so no ratio.
    assert signal["activity_30d"]["ratio"] is None
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k signal -v
```

Expected: all 6 tests fail with ImportError.

- [ ] **Step 2.3: Implement `_gather_person_signal`**

Add to `src/wiki.py` (after `_build_person_frontmatter`, around line 164):

```python
def _gather_person_signal(db: sqlite3.Connection, pid: int) -> dict:
    """Collect four signal categories for the auto synthesis block.

    Returns a dict with keys:
      - top_topics: list[dict(topic, count, pct)] — empty if <3 topics with ≥2 claims
      - activity_30d: dict(count, ratio) or None — None if 0 claims in 30d
      - tensions: list[dict(target_pid, target_name, count, tension_type)] — top 3
      - contradictions: dict(total, rhetoric_action, position_shift, last_topic, last_date) or None

    Each field follows the "null when insufficient signal" convention so the
    render function can skip bullets cleanly without threshold logic.
    """
    # --- 1. Top topics: need ≥3 topics with ≥2 position claims each ---
    topic_rows = db.execute(
        """
        SELECT topic, COUNT(*) AS cnt
        FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND topic IS NOT NULL
        GROUP BY topic
        HAVING cnt >= 2
        ORDER BY cnt DESC
        """,
        (pid,),
    ).fetchall()

    top_topics: list[dict] = []
    if len(topic_rows) >= 3:
        total_position_claims = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position'",
            (pid,),
        ).fetchone()[0]
        for row in topic_rows[:3]:
            pct = round(row["cnt"] * 100 / total_position_claims) if total_position_claims else 0
            top_topics.append({"topic": row["topic"], "count": row["cnt"], "pct": pct})

    # --- 2. Activity 30d + 90d baseline ratio ---
    count_30d = db.execute(
        """
        SELECT COUNT(*) FROM claims
        WHERE opponent_id = ? AND claim_type = 'position'
          AND stated_at >= date('now', '-30 days')
        """,
        (pid,),
    ).fetchone()[0]

    activity_30d: dict | None = None
    if count_30d >= 1:
        count_90d = db.execute(
            """
            SELECT COUNT(*) FROM claims
            WHERE opponent_id = ? AND claim_type = 'position'
              AND stated_at >= date('now', '-90 days')
            """,
            (pid,),
        ).fetchone()[0]
        # Baseline per 30d window = 90d count / 3.
        # Only compute ratio if baseline is meaningful (≥6 total over 90 days → ≥2/month avg).
        ratio: float | None = None
        if count_90d >= 6:
            baseline_30 = count_90d / 3.0
            ratio = round(count_30d / baseline_30, 1) if baseline_30 else None
        activity_30d = {"count": count_30d, "ratio": ratio}

    # --- 3. Tensions: top 3 targets by count ---
    tension_rows = db.execute(
        """
        SELECT pt.target_pid, tp.name AS target_name, pt.tension_type,
               COUNT(*) AS cnt
        FROM political_tensions pt
        JOIN tracked_politicians tp ON tp.id = pt.target_pid
        WHERE pt.source_pid = ? AND pt.target_pid IS NOT NULL
        GROUP BY pt.target_pid
        ORDER BY cnt DESC, pt.target_pid ASC
        LIMIT 3
        """,
        (pid,),
    ).fetchall()
    tensions = [
        {
            "target_pid": r["target_pid"],
            "target_name": r["target_name"],
            "count": r["cnt"],
            "tension_type": r["tension_type"],
        }
        for r in tension_rows
    ]

    # --- 4. Contradictions: confirmed only, split by rhetoric_action vs position_shift ---
    contra_total = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE opponent_id = ? AND confirmed = 1",
        (pid,),
    ).fetchone()[0]

    contradictions: dict | None = None
    if contra_total >= 1:
        # rhetoric_action = contradiction where claim_old and claim_new have different claim_type
        rhetoric_action = db.execute(
            """
            SELECT COUNT(*)
            FROM contradictions c
            JOIN claims old_c ON old_c.id = c.claim_old_id
            JOIN claims new_c ON new_c.id = c.claim_new_id
            WHERE c.opponent_id = ? AND c.confirmed = 1
              AND old_c.claim_type != new_c.claim_type
            """,
            (pid,),
        ).fetchone()[0]

        position_shift = contra_total - rhetoric_action

        last_row = db.execute(
            """
            SELECT topic, detected_at
            FROM contradictions
            WHERE opponent_id = ? AND confirmed = 1
            ORDER BY detected_at DESC, id DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()

        contradictions = {
            "total": contra_total,
            "rhetoric_action": rhetoric_action,
            "position_shift": position_shift,
            "last_topic": last_row["topic"] if last_row else None,
            "last_date": last_row["detected_at"] if last_row else None,
        }

    return {
        "top_topics": top_topics,
        "activity_30d": activity_30d,
        "tensions": tensions,
        "contradictions": contradictions,
    }
```

- [ ] **Step 2.4: Run tests**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k signal -v
```

Expected: all 6 new tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add src/wiki.py tests/test_wiki.py
git commit -m "feat(wiki): signal gathering for person synthesis block"
```

---

## Task 3: Render Function with Threshold Checks

**Files:**
- Modify: `src/wiki.py` — add `_render_person_synthesis()` + overflow constant
- Test: `tests/test_wiki.py` — render tests

- [ ] **Step 3.1: Write the failing tests**

Append to `tests/test_wiki.py`:

```python
from src.wiki import _render_person_synthesis, WikiSynthesisOverflow


def test_render_empty_signal_returns_empty_string():
    """No signal at all → empty string (no bullets, no markers)."""
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    assert _render_person_synthesis(signal) == ""


def test_render_only_top_topics():
    """Single bullet output when only top_topics present."""
    signal = {
        "top_topics": [
            {"topic": "Budžets", "count": 5, "pct": 42},
            {"topic": "Imigrācija", "count": 3, "pct": 25},
            {"topic": "Aizsardzība", "count": 2, "pct": 17},
        ],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**Top tēmas:**" in out
    assert "[[Budžets]]" in out
    assert "(42%)" in out
    # Only one bullet line
    assert out.count("- **") == 1


def test_render_activity_with_ratio():
    signal = {
        "top_topics": [],
        "activity_30d": {"count": 8, "ratio": 1.3},
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**30d:** 8 claims, 1.3× bāzes līnija" in out


def test_render_activity_without_ratio():
    """Baseline < 6 means no ratio shown — just count."""
    signal = {
        "top_topics": [],
        "activity_30d": {"count": 3, "ratio": None},
        "tensions": [],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**30d:** 3 claims" in out
    assert "bāzes līnija" not in out


def test_render_tensions_format():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [
            {"target_pid": 10, "target_name": "Andris Kulbergs", "count": 3, "tension_type": "uzbrukums"},
            {"target_pid": 20, "target_name": "Edmunds Cepurītis", "count": 2, "tension_type": "spriedze"},
        ],
        "contradictions": None,
    }
    out = _render_person_synthesis(signal)
    assert "**Spriedzes:**" in out
    assert "[[Andris Kulbergs]] (3 uzbrukumi)" in out
    assert "[[Edmunds Cepurītis]] (2 spriedzes)" in out


def test_render_contradictions_with_both_types():
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": {
            "total": 2,
            "rhetoric_action": 1,
            "position_shift": 1,
            "last_topic": "airBaltic",
            "last_date": "2026-04-14 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert "**Pretrunas:**" in out
    assert "2 apstiprinātas" in out
    assert "1 retorika↔balsojums" in out
    assert "1 pozīciju maiņa" in out
    assert "[[airBaltic]]" in out
    assert "2026-04-14" in out


def test_render_contradictions_only_position_shift():
    """No rhetoric_action count label when only position_shift exists."""
    signal = {
        "top_topics": [],
        "activity_30d": None,
        "tensions": [],
        "contradictions": {
            "total": 1,
            "rhetoric_action": 0,
            "position_shift": 1,
            "last_topic": "Budžets",
            "last_date": "2026-04-10 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert "1 apstiprināta" in out
    # No need to break down when there's only one type, just total
    assert "retorika" not in out
    assert "pozīciju maiņa" not in out


def test_render_full_signal_all_four_bullets():
    signal = {
        "top_topics": [
            {"topic": "airBaltic", "count": 18, "pct": 23},
            {"topic": "Koalīcija", "count": 12, "pct": 16},
            {"topic": "Degviela", "count": 9, "pct": 12},
        ],
        "activity_30d": {"count": 8, "ratio": 1.3},
        "tensions": [
            {"target_pid": 10, "target_name": "A. Kulbergs", "count": 3, "tension_type": "uzbrukums"},
        ],
        "contradictions": {
            "total": 2,
            "rhetoric_action": 1,
            "position_shift": 1,
            "last_topic": "airBaltic",
            "last_date": "2026-04-14 00:00:00",
        },
    }
    out = _render_person_synthesis(signal)
    assert out.count("- **") == 4
    assert "Top tēmas" in out
    assert "30d" in out
    assert "Spriedzes" in out
    assert "Pretrunas" in out


def test_render_overflow_raises():
    """Block > 1500 chars raises WikiSynthesisOverflow (fail-loud)."""
    # Artificially huge topic name to force overflow
    huge_topic = "X" * 2000
    signal = {
        "top_topics": [
            {"topic": huge_topic, "count": 5, "pct": 50},
            {"topic": "B", "count": 3, "pct": 30},
            {"topic": "C", "count": 2, "pct": 20},
        ],
        "activity_30d": None,
        "tensions": [],
        "contradictions": None,
    }
    with pytest.raises(WikiSynthesisOverflow):
        _render_person_synthesis(signal)
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k render -v
```

Expected: all 9 tests fail (ImportError).

- [ ] **Step 3.3: Implement `_render_person_synthesis`**

Add to `src/wiki.py` after `_gather_person_signal`:

```python
_SYNTHESIS_MAX_CHARS = 1500


class WikiSynthesisOverflow(Exception):
    """Raised when rendered synthesis block exceeds _SYNTHESIS_MAX_CHARS.

    Fail-loud design: silent truncation would hide a regression where a new
    bullet or an uncapped data source lets the block grow unboundedly. The
    operator must see and diagnose the overflow.
    """


def _render_person_synthesis(signal: dict) -> str:
    """Render the auto synthesis block from a signal dict.

    Returns either a bullet-list string (no leading/trailing newlines, no
    section headers) or an empty string when no bullet's threshold is met.

    Raises WikiSynthesisOverflow if the rendered block exceeds
    _SYNTHESIS_MAX_CHARS. This should never happen under normal data —
    if it does, diagnose before relaxing the limit.
    """
    lines: list[str] = []

    # --- 1. Top tēmas ---
    if signal["top_topics"]:
        parts = [
            f"[[{t['topic']}]] ({t['pct']}%)"
            for t in signal["top_topics"]
        ]
        lines.append(f"- **Top tēmas:** {', '.join(parts)}")

    # --- 2. 30d activity ---
    act = signal["activity_30d"]
    if act is not None:
        if act["ratio"] is not None:
            lines.append(f"- **30d:** {act['count']} claims, {act['ratio']}× bāzes līnija")
        else:
            lines.append(f"- **30d:** {act['count']} claims")

    # --- 3. Tensions ---
    if signal["tensions"]:
        parts = []
        for t in signal["tensions"]:
            tt = t["tension_type"]
            # Pluralize the tension_type label naturally when count > 1
            label = _pluralize_lv(tt, t["count"])
            parts.append(f"[[{t['target_name']}]] ({t['count']} {label})")
        lines.append(f"- **Spriedzes:** {', '.join(parts)}")

    # --- 4. Contradictions ---
    contra = signal["contradictions"]
    if contra is not None:
        total = contra["total"]
        count_label = "apstiprinātas" if total != 1 else "apstiprināta"
        breakdown = ""
        if contra["rhetoric_action"] > 0 and contra["position_shift"] > 0:
            breakdown = (
                f" ({contra['rhetoric_action']} retorika↔balsojums, "
                f"{contra['position_shift']} pozīciju maiņa)"
            )
        last_bit = ""
        if contra["last_topic"] and contra["last_date"]:
            date_only = contra["last_date"][:10]
            last_bit = f"; pēdējā par [[{contra['last_topic']}]], {date_only}"
        lines.append(f"- **Pretrunas:** {total} {count_label}{breakdown}{last_bit}")

    if not lines:
        return ""

    block = "\n".join(lines) + "\n"

    if len(block) > _SYNTHESIS_MAX_CHARS:
        raise WikiSynthesisOverflow(
            f"Synthesis block {len(block)} chars exceeds max {_SYNTHESIS_MAX_CHARS}"
        )

    return block


def _pluralize_lv(tension_type: str, count: int) -> str:
    """Return the Latvian plural form for tension_type label.

    Tension types used by the codebase: 'uzbrukums', 'spriedze', 'atbalsts'.
    Singular keeps the base word; plural follows normal LV rules.
    """
    if count == 1:
        return tension_type
    plurals = {
        "uzbrukums": "uzbrukumi",
        "spriedze": "spriedzes",
        "atbalsts": "atbalsti",
    }
    return plurals.get(tension_type, tension_type)
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k render -v
```

Expected: all 9 render tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add src/wiki.py tests/test_wiki.py
git commit -m "feat(wiki): render synthesis bullet block with thresholds"
```

---

## Task 4: Integrate into `wiki_sync()`

**Files:**
- Modify: `src/wiki.py` — `wiki_sync()` call chain for person pages
- Test: `tests/test_wiki.py` — integration test

- [ ] **Step 4.1: Read the current `wiki_sync()` person loop**

Read `src/wiki.py` lines 640-650 to refresh memory of the person sync loop location and the `_update_page(path, fm)` call.

- [ ] **Step 4.2: Write the failing integration test**

Append to `tests/test_wiki.py`:

```python
def test_wiki_sync_writes_synthesis_block_when_signal_present(wiki_tmp_db, tmp_path, monkeypatch):
    """End-to-end: politician with signal gets sync block in their page."""
    from src.wiki import wiki_sync

    # Redirect wiki to tmp
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (1, 'Testa Politis', '[]', 'tracked')"
    )
    # 3 topics × 2+ claims each (hits top_topics threshold)
    topics = {"Budžets": 5, "Imigrācija": 3, "Aizsardzība": 2}
    for topic, n in topics.items():
        for i in range(n):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir)

    page = wiki_dir / "persons" / "testa-politis.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" in text
    assert "**Top tēmas:**" in text
    assert "[[Budžets]]" in text


def test_wiki_sync_empty_body_when_no_signal(wiki_tmp_db, tmp_path, monkeypatch):
    """Politician with no claims → page has frontmatter only, no markers."""
    from src.wiki import wiki_sync

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (2, 'Silent Politis', '[]', 'tracked')"
    )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir)

    page = wiki_dir / "persons" / "silent-politis.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "<!-- SYNC-AUTO -->" not in text


def test_wiki_sync_preserves_manual_content_when_updating(wiki_tmp_db, tmp_path, monkeypatch):
    """Existing page with manual notes keeps them after sync."""
    from src.wiki import wiki_sync

    wiki_dir = tmp_path / "wiki"
    persons_dir = wiki_dir / "persons"
    persons_dir.mkdir(parents=True)
    monkeypatch.setattr("src.wiki.WIKI_DIR", wiki_dir, raising=False)

    page = persons_dir / "testa-politis.md"
    page.write_text(
        "---\nname: Testa Politis\n---\n\n"
        "**Manuāls konteksts:** bijušais teātra režisors.\n",
        encoding="utf-8",
    )

    wiki_tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES (1, 'Testa Politis', '[]', 'tracked')"
    )
    for topic in ("A", "B", "C"):
        for i in range(2):
            wiki_tmp_db.execute(
                """INSERT INTO claims (opponent_id, topic, stance, confidence, salience,
                                       source_url, stated_at, claim_type)
                   VALUES (1, ?, ?, 0.8, 0.5, ?, date('now', '-5 days'), 'position')""",
                (topic, f"s-{i}", f"https://x.com/p/{topic}_{i}"),
            )
    wiki_tmp_db.commit()

    wiki_sync(wiki_dir)

    text = page.read_text(encoding="utf-8")
    assert "bijušais teātra režisors" in text
    assert "<!-- SYNC-AUTO -->" in text
```

- [ ] **Step 4.3: Run tests to verify they fail**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -k "wiki_sync_writes_synthesis or wiki_sync_empty_body or wiki_sync_preserves_manual" -v
```

Expected: tests fail because `wiki_sync()` still calls `_update_page` (frontmatter only), not the new sync-block variant.

- [ ] **Step 4.4: Update `wiki_sync()` to call the new helpers**

In `src/wiki.py`, find the person loop (around lines 642-648):

```python
    persons_synced = 0
    for politician in politicians:
        slug = _slugify(politician["name"])
        page_path = persons_dir / f"{slug}.md"
        fm = _build_person_frontmatter(db, politician)
        _update_page(page_path, fm)
        persons_synced += 1
```

Replace the body of the loop with:

```python
    persons_synced = 0
    for politician in politicians:
        slug = _slugify(politician["name"])
        page_path = persons_dir / f"{slug}.md"
        fm = _build_person_frontmatter(db, politician)
        signal = _gather_person_signal(db, politician["id"])
        sync_block = _render_person_synthesis(signal)
        _update_page_with_sync_block(page_path, fm, sync_block)
        persons_synced += 1
```

- [ ] **Step 4.5: Run tests**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_wiki.py -v
```

Expected: all tests pass, including the 3 new integration tests and all pre-existing wiki tests.

- [ ] **Step 4.6: Run full test suite to check no regressions**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 525+ tests pass (previous baseline was 514 + 11 new tests from this plan).

- [ ] **Step 4.7: Commit**

```bash
git add src/wiki.py tests/test_wiki.py
git commit -m "feat(wiki): integrate person synthesis block into wiki_sync"
```

---

## Task 5: Production Sync + Spot-Check + Lint

- [ ] **Step 5.1: Run `wiki_sync()` against production DB**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from src.wiki import wiki_sync; r=wiki_sync(); print(r)" 2>&1 | tail -5
```

Expected: `{'persons': 148, 'topics': 26, 'parties': 11, 'updated_at': '...', 'lint': {...}}`.

- [ ] **Step 5.2: Spot-check 3 politicians at different signal levels**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
paths = [
    ('wiki/persons/evika-silina.md', 'heavy signal — expect 3-4 bullets'),
    ('wiki/persons/kristaps-kristopans.md', 'active — expect 2-3 bullets'),
    ('wiki/persons/gunars-kutris.md', 'sparse — expect empty body'),
]
for p, note in paths:
    print(f'--- {p} ({note}) ---')
    print(open(p, encoding='utf-8').read())
    print()
"
```

Eyeball: does each profile match its expected density? Any overflow exceptions? Any obviously wrong bullets?

- [ ] **Step 5.3: Run wiki lint**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from src.wiki_lint import lint_wiki; from pathlib import Path; r=lint_wiki(Path('wiki')); print(r['stats'])"
```

Expected: `{'total_issues': 0, ...}`.

- [ ] **Step 5.4: Commit the updated wiki files**

```bash
git add wiki/persons/
git commit -m "chore(wiki): refresh person pages with synthesis blocks"
```

---

## Self-Review Checklist

- **Spec coverage:**
  - ✅ Task 1: Marker-aware page update (`_update_page_with_sync_block`, `_strip_sync_block`)
  - ✅ Task 2: Signal gathering (4 categories, null-when-insufficient)
  - ✅ Task 3: Render function with 4 bullets, threshold skips, WikiSynthesisOverflow
  - ✅ Task 4: Integration into `wiki_sync()`
  - ✅ Task 5: Production sync + spot-check

- **Placeholder scan:** No TBDs, no "similar to X", no "add error handling" placeholders. Every step has exact code.

- **Type consistency:** `_gather_person_signal` returns a dict with keys `top_topics: list[dict]`, `activity_30d: dict | None`, `tensions: list[dict]`, `contradictions: dict | None`. Consumed identically in `_render_person_synthesis`. `_update_page_with_sync_block(path, frontmatter, sync_block)` signature matches call site in `wiki_sync()`.

- **Threshold precision:**
  - top_topics: need ≥3 topics with ≥2 claims each → return top 3
  - activity_30d: ≥1 claim in 30d; ratio only if 90d count ≥ 6
  - tensions: top 3, no minimum count (even 1 is signal)
  - contradictions: ≥1 confirmed; rhetoric/shift breakdown only when both >0
  - All pluralizations Latvian-correct (uzbrukums → uzbrukumi, spriedze → spriedzes)

- **Overflow safety:** `WikiSynthesisOverflow` raised at 1500 chars. Test covers this with a deliberately oversized topic name.

- **Empty body invariant:** Confirmed in Task 1 tests (`test_sync_block_empty_no_markers_written`, `test_sync_block_removed_when_empty`) and Task 4 integration test (`test_wiki_sync_empty_body_when_no_signal`). When signal is below all thresholds, no markers appear — body stays clean.

- **Manual content preservation:** Covered in Task 1 tests (`test_sync_block_replaces_existing`, `test_sync_block_appended_to_existing_body_without_markers`) and Task 4 (`test_wiki_sync_preserves_manual_content_when_updating`).

- **Out-of-scope (by design):**
  - Rhetoric-vs-action gap as a separate bullet — subsumed under Pretrunas bullet with `claim_type` breakdown.
  - Manual 1-sentence "political identity" above the auto block — deferred; the architecture leaves room (manual content above markers is preserved).
  - Topic pages and party pages synthesis — this plan only touches person pages. Topic/party pages can follow the same pattern later.
  - Live re-run trigger — operator runs `wiki_sync()` via daily routine step 9; no new scheduling needed.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-20-wiki-synthesis-block.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
