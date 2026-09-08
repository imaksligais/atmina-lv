# Render Char-Baseline Fixture Rework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple `tests/test_render_chars.py` from the live `data/atmina.db` so its 13 byte-identity tests only change when render *code* changes — killing the daily REGEN treadmill.

**Architecture:** Build a small, curated, FK-consistent subset of the live DB, committed as a text data-only SQL file (`tests/fixtures/render_fixture_data.sql`). The test session fixture builds a tmp DB via `init_db()` (full schema + sqlite-vec vtabs), loads the fixture data, freezes the clock with `freezegun`, and renders into a tmp dir. Baselines are regenerated once against this frozen input and stay stable across daily ingest.

**Tech Stack:** Python 3.12, pytest, sqlite3, sqlite-vec, freezegun (new dev dep), the existing `src/render` package.

---

## Session Handoff (READ FIRST)

**Where we are (2026-05-31):**
- `bash scripts/check.sh` is RED on exactly 13 tests, ALL in `tests/test_render_chars.py` (`*_byte_identical`). ruff + the other 1252 tests pass.
- These 13 fail because they render the **live** `data/atmina.db` and hash the HTML; every daily ingest/claim/brief changes the bytes → REGEN treadmill. This is a **pre-existing** known issue (documented in memory `project_2026-05-29_gate_restoration`, item "char baseline data-drift treadmill"), NOT a regression from recent work.
- The daily routine for 2026-05-30 is fully published & committed (`f5ac4f3`, `5ac40ae`, `8c88d89` on master, **unpushed**). A separate `wiki_sync` perf fix already landed in `f5ac4f3`.

**Why this rework:** Option chosen by the operator over (a) repeated REGEN (~7 min, recurs daily) and (b) gating the tests opt-in (loses the always-on byte safety net). This rework keeps the safety net and ends the treadmill.

**Start here:**
1. Create an isolated worktree (see superpowers:using-git-worktrees) off `master`, branch e.g. `render-char-fixture`.
2. Execute Tasks 1→7 below in order. TDD where applicable; commit after each task.
3. The single highest-risk task is **Task 4 + Task 5** (clock pinning + first green REGEN): expect byte-mismatch whack-a-mole if any render path injects "now" outside the frozen clock. The freezegun approach in Task 1 is chosen specifically to cover ALL date paths (incl. stdlib `datetime.now()`/`date.today()` in `contradictions.py`, `dashboard.py`, `news.py`, `votes.py`) without per-module monkeypatching.

**Definition of done:** `bash scripts/check.sh` green; a deliberate render-code edit still FAILS a char test (safety net intact); a DB data change does NOT fail it (treadmill dead). See Task 6.

**Key facts discovered (so you don't re-investigate):**
- `generate_public_site(db_path=None, output_dir=None)` — `src/render/_orchestrator.py:175`. Pass both.
- `generate_statistika(...)` — `src/render/statistika.py:61` (also called by the test fixture; pass the same db_path/output_dir).
- `init_db(db_path)` — `src/db.py:43` — runs `src/schema.sql` AND creates the `document_vectors`/`claim_vectors` vec0 vtabs (needs `sqlite_vec`, already installed in the venv). Use it to build the tmp DB schema; do NOT hand-dump schema (avoids vec0 DDL extension issues).
- `.gitignore` excludes `*.db`/`*.sqlite` (lines 2–6) → **commit `.sql` text, never a `.db`**.
- Clock sources: `src/db.py` `now_lv()`/`now_lv_dt()`/`today_lv()` (all derive from `datetime.now(timezone.utc)`); plus direct stdlib `datetime.now()`/`date.today()` in `src/render/{contradictions,dashboard,news,votes}.py`.
- Render uses `ATMINA_ASSETS_VERSION` cache-bust; the test already pins it to `"test"` via a session fixture (`_stable_assets_version`) — keep that.
- The 13 baselines live in `tests/fixtures/render_baseline_*.json` (contradictions, politicians, parties, misc, bills, laws, x, graph, analyses, blog, dashboard).

**Python invocation on this Windows box:** the `.venv` python is broken. Run python as:
`PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py <args>`. For pytest: `PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -m pytest ...`.

---

## File Structure

- **Create** `scripts/build_render_fixture.py` — one-shot builder: reads live `data/atmina.db`, writes `tests/fixtures/render_fixture_data.sql` (data-only INSERTs, deterministic order). Re-runnable; rerun only when you intentionally want different fixture coverage.
- **Create** `tests/fixtures/render_fixture_data.sql` — committed text fixture (the builder's output).
- **Modify** `tests/test_render_chars.py` — repoint the `rendered_site` session fixture at a tmp DB built from the fixture SQL, wrapped in a frozen clock.
- **Modify** `tests/fixtures/render_baseline_*.json` (13 files) — regenerated once against the fixture DB.
- **Modify** `requirements.txt` — add `freezegun`.
- **Modify** `tests/test_render_chars.py` docstring + memory `project_2026-05-29_gate_restoration` — record that the treadmill is dead.

**Freeze instant (constant used everywhere):** `FREEZE_INSTANT = "2026-06-01 12:00:00"` (LV-local, naive). Chosen to be after all current data so relative-time phrases ("pirms N dienām", 7/14/28-day windows) are computed against a fixed point. The builder includes only rows dated strictly before it (all current data qualifies as of 2026-05-31).

---

### Task 1: Add freezegun dev dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the dependency line**

Append to `requirements.txt` (near the test/dev section if one exists, else end of file):

```
freezegun>=1.5.0
```

- [ ] **Step 2: Install it into the venv site-packages**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" py -m pip install "freezegun>=1.5.0" --target ".venv/Lib/site-packages"
```
Expected: `Successfully installed freezegun-...` (or "already satisfied").

- [ ] **Step 3: Verify import**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" py -c "from freezegun import freeze_time; print('freezegun ok')"
```
Expected: `freezegun ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(test): add freezegun dev dependency for deterministic render fixtures"
```

---

### Task 2: Write the fixture builder script

**Files:**
- Create: `scripts/build_render_fixture.py`

**Design:** Select a FIXED set of politician ids covering multiple parties + an organization slot + a journalist. Copy each render-relevant table filtered to that set (and the rows they FK to), in a fixed order, emitting data-only `INSERT` statements. Determinism comes from `ORDER BY` on every SELECT and a fixed table order.

- [ ] **Step 1: Create the builder script**

Create `scripts/build_render_fixture.py`:

```python
"""Build tests/fixtures/render_fixture_data.sql — a small, FK-consistent
subset of the live DB for deterministic render characterization tests.

Re-run only to intentionally change fixture coverage:
    PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py scripts/build_render_fixture.py
Then REGEN the baselines (see plan Task 5).

Output is data-only INSERTs (no schema): the test rebuilds the schema via
src.db.init_db (which also creates the sqlite-vec vtabs), then loads this SQL.
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIVE_DB = "data/atmina.db"
OUT_SQL = Path("tests/fixtures/render_fixture_data.sql")

# Fixed politician set — multi-party + organization (204) + journalist (57).
# Chosen for rich, varied, stable coverage of every scoped render page.
FIXED_PIDS = [10, 72, 6, 15, 26, 189, 30, 182, 204, 57]

# Only include data dated strictly before the test freeze instant so relative
# time rendering is stable. All current data (<= 2026-05-31) qualifies.
DATE_CEILING = "2026-06-01"


def q(con, sql, params=()):
    return con.execute(sql, params).fetchall()


def emit_inserts(con, table, rows):
    """Yield deterministic INSERT statements for `rows` of `table`."""
    if not rows:
        return
    cols = [d[0] for d in con.execute(f"SELECT * FROM {table} LIMIT 0").description]
    collist = ", ".join(cols)
    for r in rows:
        vals = ", ".join(_lit(r[c]) for c in cols)
        yield f"INSERT INTO {table} ({collist}) VALUES ({vals});"


def _lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, bytes):
        return "X'" + v.hex() + "'"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def main():
    con = sqlite3.connect(LIVE_DB)
    con.row_factory = sqlite3.Row
    ids = ",".join(str(p) for p in FIXED_PIDS)

    lines = [
        "-- AUTO-GENERATED by scripts/build_render_fixture.py — do not hand-edit.",
        "-- Data-only INSERTs; schema is built by src.db.init_db in the test fixture.",
        "PRAGMA foreign_keys=OFF;",
        "BEGIN;",
    ]

    # 1. tracked_politicians (the anchor set)
    pol = q(con, f"SELECT * FROM tracked_politicians WHERE id IN ({ids}) ORDER BY id")
    lines += list(emit_inserts(con, "tracked_politicians", pol))

    # 2. parties referenced by those politicians
    parties = q(con, f"""
        SELECT * FROM parties WHERE party IN (
            SELECT DISTINCT party FROM tracked_politicians WHERE id IN ({ids})
        ) ORDER BY party
    """)
    lines += list(emit_inserts(con, "parties", parties))

    # 3. claims authored about/by the set (subject or speaker), dated < ceiling
    claims = q(con, f"""
        SELECT * FROM claims
        WHERE (opponent_id IN ({ids}) OR speaker_id IN ({ids}))
          AND (stated_at IS NULL OR DATE(stated_at) < '{DATE_CEILING}')
        ORDER BY id
    """)
    lines += list(emit_inserts(con, "claims", claims))
    claim_doc_ids = {r["document_id"] for r in claims if r["document_id"] is not None}

    # 4. documents backing those claims + linked as subject/mentioned to the set
    doc_ids = set(claim_doc_ids)
    linked = q(con, f"""
        SELECT DISTINCT document_id FROM document_politicians
        WHERE politician_id IN ({ids})
    """)
    doc_ids |= {r["document_id"] for r in linked}
    if doc_ids:
        idlist = ",".join(str(d) for d in sorted(doc_ids))
        docs = q(con, f"SELECT * FROM documents WHERE id IN ({idlist}) ORDER BY id")
        lines += list(emit_inserts(con, "documents", docs))
        dp = q(con, f"""
            SELECT * FROM document_politicians
            WHERE document_id IN ({idlist}) AND politician_id IN ({ids})
            ORDER BY document_id, politician_id, role
        """)
        lines += list(emit_inserts(con, "document_politicians", dp))

    # 5. contradictions for the set
    contras = q(con, f"SELECT * FROM contradictions WHERE opponent_id IN ({ids}) ORDER BY id")
    lines += list(emit_inserts(con, "contradictions", contras))

    # 6. analyses for the set
    analyses = q(con, f"SELECT * FROM analyses WHERE opponent_id IN ({ids}) ORDER BY id")
    lines += list(emit_inserts(con, "analyses", analyses))

    # 7. context_notes: set-owned + a few global (daily_brief/synthesis) for blog/analizes
    notes = q(con, f"""
        SELECT * FROM context_notes
        WHERE opponent_id IN ({ids})
           OR id IN (
              SELECT id FROM context_notes
              WHERE note_type IN ('daily_brief','weekly_brief','synthesis')
                AND DATE(created_at) < '{DATE_CEILING}'
              ORDER BY id DESC LIMIT 6
           )
        ORDER BY id
    """)
    lines += list(emit_inserts(con, "context_notes", notes))
    note_ids = {r["id"] for r in notes}

    # 8. brief_images for those notes
    if note_ids:
        nidlist = ",".join(str(n) for n in sorted(note_ids))
        imgs = q(con, f"SELECT * FROM brief_images WHERE note_id IN ({nidlist}) ORDER BY id")
        lines += list(emit_inserts(con, "brief_images", imgs))

    # 9. social_accounts + external_profiles for the set
    lines += list(emit_inserts(con, "social_accounts",
        q(con, f"SELECT * FROM social_accounts WHERE opponent_id IN ({ids}) ORDER BY id")))
    lines += list(emit_inserts(con, "external_profiles",
        q(con, f"SELECT * FROM external_profiles WHERE opponent_id IN ({ids}) ORDER BY id")))

    # 10. political_tensions involving the set (spriedzes page)
    lines += list(emit_inserts(con, "political_tensions",
        q(con, f"""
            SELECT * FROM political_tensions
            WHERE source_politician_id IN ({ids}) OR target_politician_id IN ({ids})
            ORDER BY id
        """)))

    # 11. Saeima votes for the set + their parent vote/bill/stage rows
    iv = q(con, f"""
        SELECT * FROM saeima_individual_votes
        WHERE politician_id IN ({ids})
          AND DATE(stated_at) < '{DATE_CEILING}'
        ORDER BY id LIMIT 4000
    """)
    lines += list(emit_inserts(con, "saeima_individual_votes", iv))
    vote_ids = sorted({r["vote_id"] for r in iv if "vote_id" in r.keys() and r["vote_id"] is not None})
    if vote_ids:
        vlist = ",".join(str(v) for v in vote_ids)
        votes = q(con, f"SELECT * FROM saeima_votes WHERE id IN ({vlist}) ORDER BY id")
        lines += list(emit_inserts(con, "saeima_votes", votes))
        bill_ids = sorted({r["bill_id"] for r in votes if r["bill_id"] is not None})
        if bill_ids:
            blist = ",".join(str(b) for b in bill_ids)
            lines += list(emit_inserts(con, "saeima_bills",
                q(con, f"SELECT * FROM saeima_bills WHERE id IN ({blist}) ORDER BY id")))
            lines += list(emit_inserts(con, "saeima_bill_stages",
                q(con, f"SELECT * FROM saeima_bill_stages WHERE bill_id IN ({blist}) ORDER BY id")))
        sess_ids = sorted({r["session_id"] for r in votes
                           if "session_id" in r.keys() and r["session_id"] is not None})
        if sess_ids:
            slist = ",".join(str(s) for s in sess_ids)
            lines += list(emit_inserts(con, "saeima_sessions",
                q(con, f"SELECT * FROM saeima_sessions WHERE id IN ({slist}) ORDER BY id")))
            lines += list(emit_inserts(con, "saeima_agenda_items",
                q(con, f"SELECT * FROM saeima_agenda_items WHERE session_id IN ({slist}) ORDER BY id")))
    lines += list(emit_inserts(con, "saeima_bill_politicians",
        q(con, f"SELECT * FROM saeima_bill_politicians WHERE politician_id IN ({ids}) ORDER BY bill_id, politician_id")))

    lines += ["COMMIT;", "PRAGMA foreign_keys=ON;", ""]

    OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    OUT_SQL.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_SQL} ({len(lines)} lines, {OUT_SQL.stat().st_size} bytes)")
    con.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity-check the table/column names against the live schema**

Run (confirms every table referenced above exists and the FK columns are named as assumed — fix the script if any differ, e.g. `saeima_individual_votes.vote_id`/`session_id`, `political_tensions.source_politician_id`):
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -c "
from src.db import get_db
db=get_db()
for t in ['saeima_individual_votes','saeima_votes','political_tensions','context_notes','brief_images','saeima_bill_politicians']:
    print(t, [r[1] for r in db.execute(f'PRAGMA table_info({t})').fetchall()])
"
```
Expected: prints columns. Adjust the builder's column references (`vote_id`, `session_id`, `source_politician_id`, `target_politician_id`, `note_id`) to match actual names before running.

- [ ] **Step 3: Commit the builder**

```bash
git add scripts/build_render_fixture.py
git commit -m "feat(test): add render fixture builder (curated FK-consistent DB subset)"
```

---

### Task 3: Generate and commit the fixture SQL

**Files:**
- Create: `tests/fixtures/render_fixture_data.sql`

- [ ] **Step 1: Run the builder**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py scripts/build_render_fixture.py
```
Expected: `wrote tests/fixtures/render_fixture_data.sql (N lines, M bytes)` — M should be well under ~3 MB. If it is much larger, lower the `LIMIT 4000` on `saeima_individual_votes` or trim `FIXED_PIDS`.

- [ ] **Step 2: Smoke-load it into a throwaway DB to prove integrity**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -c "
import tempfile, os
from src.db import init_db, get_db
tmp = tempfile.mktemp(suffix='.db')
init_db(tmp)
db = get_db(tmp)
db.executescript(open('tests/fixtures/render_fixture_data.sql', encoding='utf-8').read())
print('politicians:', db.execute('SELECT COUNT(*) FROM tracked_politicians').fetchone()[0])
print('claims:', db.execute('SELECT COUNT(*) FROM claims').fetchone()[0])
print('votes:', db.execute('SELECT COUNT(*) FROM saeima_individual_votes').fetchone()[0])
print('notes:', db.execute('SELECT COUNT(*) FROM context_notes').fetchone()[0])
db.close(); os.remove(tmp); print('LOAD OK')
"
```
Expected: counts > 0 and `LOAD OK` with no FK / syntax error. If an INSERT fails on a missing parent row, add that parent table's extraction to the builder (Task 2) and rerun Task 3.

- [ ] **Step 3: Commit the fixture**

```bash
git add tests/fixtures/render_fixture_data.sql
git commit -m "test(render): add committed fixture DB data for char baselines"
```

---

### Task 4: Repoint the test session fixture at the fixture DB under a frozen clock

**Files:**
- Modify: `tests/test_render_chars.py` (the `rendered_site` fixture, ~lines 112–120)

- [ ] **Step 1: Replace the `rendered_site` fixture body**

Find (around line 112):
```python
@pytest.fixture(scope="session")
def rendered_site(tmp_path_factory, _stable_assets_version):
    out = tmp_path_factory.mktemp("render_chars_site")
    generate_public_site(output_dir=str(out))
```
...through the `generate_statistika(output_dir=str(out))` call (~line 119).

Replace the whole fixture with:
```python
FIXTURE_SQL = Path(__file__).parent / "fixtures" / "render_fixture_data.sql"
FREEZE_INSTANT = "2026-06-01 12:00:00"  # after all fixture data; pins relative-time rendering


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory):
    """Build a tmp DB from the committed fixture SQL (schema via init_db)."""
    from src.db import init_db, get_db
    db_path = str(tmp_path_factory.mktemp("render_fixture_db") / "fixture.db")
    init_db(db_path)
    conn = get_db(db_path)
    conn.executescript(FIXTURE_SQL.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="session")
def rendered_site(tmp_path_factory, _stable_assets_version, fixture_db):
    from freezegun import freeze_time
    out = tmp_path_factory.mktemp("render_chars_site")
    with freeze_time(FREEZE_INSTANT):
        generate_public_site(db_path=fixture_db, output_dir=str(out))
        # generate_statistika reads a SEPARATE CSP/events store, NOT the main
        # atmina DB — its signature is (output_dir, csp_db_path, events_path).
        # Keep it on defaults; it is not part of the main-DB drift (no
        # statistika test was among the 13 drifting baselines). Wrapped in
        # freeze_time only for any timestamp it emits.
        generate_statistika(output_dir=str(out))
    return out / "atmina"
```

The original fixture returns `out / "atmina"` (verified) — the replacement keeps that exact return so the `_capture_observed*(atmina_dir)` helpers receive the same path.

- [ ] **Step 2: (verified during planning — no action) `generate_statistika` does not read the main DB**

`generate_statistika(output_dir, csp_db_path, events_path)` renders the statistika page from a separate CSP/events store, so it needs no fixture DB. Leave its call on defaults (as above). If the statistika baseline ever starts drifting, that is a *separate* hermeticity task — point `csp_db_path`/`events_path` at committed fixtures then; out of scope here.

- [ ] **Step 3: Verify the fixture renders without error (REGEN bootstrap)**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 REGEN=1 py -m pytest tests/test_render_chars.py -q
```
Expected: tests SKIP (REGEN writes baselines) with no render exception. If render raises (e.g., a page expects a row type absent from the fixture), extend `FIXED_PIDS` or the builder (Task 2), rebuild (Task 3), and rerun.

- [ ] **Step 4: Commit the fixture wiring (baselines come in Task 5)**

```bash
git add tests/test_render_chars.py
git commit -m "test(render): render char baselines from frozen fixture DB, not live DB"
```

---

### Task 5: Regenerate baselines against the fixture DB

**Files:**
- Modify: `tests/fixtures/render_baseline_*.json` (all 13)

- [ ] **Step 1: Regenerate**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 REGEN=1 py -m pytest tests/test_render_chars.py -q
```
Expected: all char tests SKIP ("Regenerated baseline"). This rewrites every `tests/fixtures/render_baseline_*.json` with hashes computed from the fixture DB under the frozen clock.

- [ ] **Step 2: Assert green WITHOUT REGEN**

Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -m pytest tests/test_render_chars.py -q
```
Expected: all 13 char tests PASS (0 failed).

- [ ] **Step 3: Re-run a second time to prove determinism**

Run the same command again. Expected: still all PASS (proves the render + frozen clock is byte-stable across runs).

- [ ] **Step 4: Commit the regenerated baselines**

```bash
git add tests/fixtures/render_baseline_*.json
git commit -m "test(render): regenerate char baselines against committed fixture DB"
```

---

### Task 6: Prove the safety net works and the treadmill is dead

**Files:** none (verification only)

- [ ] **Step 1: A render-code change STILL fails a char test (safety net intact)**

Temporarily edit a rendered string, e.g. in `src/render/positions.py` change a visible heading literal (pick any user-facing string). Run:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -m pytest tests/test_render_chars.py::test_pozicijas_index_byte_identical -q
```
Expected: FAIL (hash mismatch). Then `git checkout -- src/render/positions.py` to revert. Confirm it PASSES again.

- [ ] **Step 2: A DB data change does NOT fail the char tests (treadmill dead)**

The tests now read the committed fixture, not `data/atmina.db`, so live-DB changes are irrelevant. Confirm by running the full char suite — it must pass regardless of today's live DB state:
```bash
PYTHONPATH=".venv/Lib/site-packages" PYTHONIOENCODING=utf-8 py -m pytest tests/test_render_chars.py -q
```
Expected: all PASS. (Optional stronger proof: add a throwaway claim to the live DB, rerun — still PASS — then remove it.)

- [ ] **Step 3: Full gate green**

Run:
```bash
bash scripts/check.sh
```
Expected: ruff clean, pytest all pass (the 13 char tests included), smoke OK. Quote the final `passed` line.

---

### Task 7: Update docs + memory

**Files:**
- Modify: `tests/test_render_chars.py` (module docstring)
- Modify: `~\.claude\projects\C--Users-The-User-atmina\memory\project_2026-05-29_gate_restoration.md`

- [ ] **Step 1: Update the test docstring**

In `tests/test_render_chars.py` replace the "Refactor invariant" / live-DB framing with the new model:

```
Source of truth: tests render the COMMITTED fixture DB
(tests/fixtures/render_fixture_data.sql, built by scripts/build_render_fixture.py)
under a frozen clock (FREEZE_INSTANT), NOT the live data/atmina.db. Baselines
therefore change ONLY when render code changes — daily ingest no longer drifts
them. To intentionally change coverage: rerun the builder, then
REGEN=1 pytest tests/test_render_chars.py, then commit fixture + baselines.
```

- [ ] **Step 2: Update the memory**

In `project_2026-05-29_gate_restoration.md`, change the char-baseline "treadmill" line to record it RESOLVED: tests now render a committed frozen fixture DB (`tests/fixtures/render_fixture_data.sql`) under `freeze_time`, so daily data no longer drifts the baselines; REGEN only needed on intentional render-code or fixture-coverage changes. Update `MEMORY.md` hook line accordingly.

- [ ] **Step 3: Commit**

```bash
git add tests/test_render_chars.py
git commit -m "docs(test): document fixture-DB char baseline model (treadmill retired)"
```

- [ ] **Step 4: Finish the branch**

Use superpowers:finishing-a-development-branch to merge/PR. Do NOT push to master without the operator's explicit go-ahead (project rule: commits stay local until the operator pushes).

---

## Self-Review notes

- **Spec coverage:** fixture build (T2/T3), clock pin (T1/T4), repoint + REGEN (T4/T5), safety-net proof + treadmill-dead proof (T6), docs/memory (T7). All covered.
- **Determinism risk** is concentrated in T4/T5; freezegun covers `now_lv*` AND stdlib `datetime.now()`/`date.today()` in `contradictions/dashboard/news/votes`, which is why it's preferred over per-module monkeypatch.
- **Schema/column assumptions** (vote_id, session_id, source/target_politician_id, note_id) are verified in T2 Step 2 before first build — adjust the builder there if any differ.
- **Binary-in-git avoided:** fixture is text SQL; schema rebuilt via `init_db` (handles sqlite-vec vtabs).
- **Fallback if freezegun is rejected:** refactor the 4 stdlib-clock modules to use `today_lv()`/`now_lv_dt()`, then monkeypatch `src.db.now_lv`/`now_lv_dt`/`today_lv` + each render module's imported clock symbol in the session fixture. More invasive; freezegun is the recommended path.
