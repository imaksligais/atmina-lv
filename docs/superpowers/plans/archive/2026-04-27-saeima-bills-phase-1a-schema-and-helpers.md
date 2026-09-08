# Saeima Bills Phase 1A — Schema, Helpers & Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realizēt Saeima Bills tracker datu modeļa pamatu — 3 jaunas tabulas (`saeima_bills`, `saeima_bill_stages`, `saeima_bill_politicians`), `saeima_votes.bill_id` FK, parser/upsert/append helperi (`parse_agenda_snapshot`, `upsert_bill`, `append_bill_stage`, `match_submitters_to_politicians`, motif klasifikācijas regex) un retro-backfill skripts no 139 esošajiem `saeima_votes`. Pēc Phase 1A bills timeline ir queryable, bet UI ir Phase 1B atsevišķs darbs.

**Architecture:** Visi helperi paplašina esošo `src/saeima.py` (jaunas funkcijas, nelaužam esošās). Schema migrācija — jauna `init_saeima_bills(db_path)` funkcija blakus `init_saeima_tables()`; nepārveido esošo. Backfill ir atsevišķs skripts `scripts/backfill_saeima_bills.py`, ne automātiska migrācija. Visas validācijas notiek Python pusē (SQLite bez CHECK constraints).

**Tech Stack:** Python 3.11, SQLite (WAL), pytest. Dependencies: `tempfile` for fixtures, `re` for motif regex, `json` for name_forms parsing. No new dependencies.

**Spec sources:** `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` § 3.1 (schema), § 3.3 (vocabulary), § 4.3 (helpers), § 5 (backfill), § 8.1+8.2 (tests).

**Acceptance:** All 11 unit/integration tests from spec § 8.1+8.2 pass on parent venv. Backfill smoke test produces ≥80 unique bills from 139 votes (139 votes → ~91 unique document_nr → bills). `unknown_stages` after backfill <10% (≤14 of 139).

**Pre-requisites met by Phase 0:** `_VALID_STAGE_NAMES` and `_VALID_BILL_TYPES` design clarified, P14 in whitelist, audit script in place. Spec is Phase 1-ready.

---

## File Structure

| Fails | Atbildība | Status |
|---|---|---|
| `src/saeima.py` | Pievieno: `init_saeima_bills()`, `_VALID_BILL_TYPES`, `_VALID_STAGE_NAMES`, `_canonicalize_stage_name()`, `AgendaBill` dataclass, `parse_agenda_snapshot()`, `resolve_bill_from_motif()`, `_reading_from_motif()`, `_resolve_base_law_slug()`, `upsert_bill()`, `append_bill_stage()`, `match_submitters_to_politicians()` | Modify (additive) |
| `scripts/backfill_saeima_bills.py` | Read 139 `saeima_votes` → group by document_nr → upsert bills + append stages → set `saeima_votes.bill_id` | Create |
| `tests/test_saeima_bills.py` | All § 8.1 unit tests (9 tests) | Create |
| `tests/test_saeima_bills_integration.py` | § 8.2 integration tests (2 tests against 2026-04-16 fixture) | Create |

`tests/test_saeima.py` — leave existing tests untouched (they test claim generation, orthogonal to this work).

---

## Worktree Setup

Use `superpowers:using-git-worktrees` skill before Task 1. Branch: `saeima-bills-phase-1a`. Path: `.worktrees/saeima-bills-phase-1a`.

---

## Task 1: Schema migration — `init_saeima_bills()` + saeima_votes.bill_id ALTER

**Files:**
- Modify: `src/saeima.py` (add new function near `init_saeima_tables`)
- Create: `tests/test_saeima_bills.py` (start with schema tests)

- [ ] **Step 1: Write failing schema test**

```python
# tests/test_saeima_bills.py
"""Phase 1A unit tests — saeima_bills schema, helpers, and backfill prep."""

import os
import sqlite3
import tempfile

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_bills, init_saeima_tables


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)  # sessions, agenda_items, votes, individual_votes
    yield path
    _safe_unlink(path)


class TestSchema:
    def test_init_saeima_bills_creates_three_tables(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('saeima_bills', 'saeima_bill_stages', 'saeima_bill_politicians')"
        ).fetchall()}
        db.close()
        assert tables == {"saeima_bills", "saeima_bill_stages", "saeima_bill_politicians"}

    def test_init_saeima_bills_adds_bill_id_to_votes(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        cols = [row[1] for row in db.execute("PRAGMA table_info(saeima_votes)").fetchall()]
        db.close()
        assert "bill_id" in cols

    def test_init_saeima_bills_creates_indexes(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        indexes = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name IN ('idx_bills_document_nr', 'idx_bills_topic', 'idx_bills_status', "
            "'idx_bill_stages_bill_id', 'idx_bill_stages_vote_id', 'idx_bill_stages_kind', "
            "'idx_bill_politicians_bill_id', 'idx_bill_politicians_politician_id', "
            "'idx_saeima_votes_bill_id')"
        ).fetchall()}
        db.close()
        assert len(indexes) == 9

    def test_init_saeima_bills_idempotent(self, empty_db):
        init_saeima_bills(empty_db)
        init_saeima_bills(empty_db)  # second call should not raise
        # Schema unchanged
        db = get_db(empty_db)
        count = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
        db.close()
        assert count == 0

    def test_stage_kind_default_is_vote(self, empty_db):
        init_saeima_bills(empty_db)
        db = get_db(empty_db)
        # Insert a bill + stage without specifying stage_kind
        db.execute(
            "INSERT INTO saeima_bills (document_nr, bill_type, title) "
            "VALUES ('1/Lp14', 'Lp14', 'Test')"
        )
        bill_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO saeima_bill_stages (bill_id, stage_name, stage_date) "
            "VALUES (?, 'iesniegts', '2026-01-01')",
            (bill_id,)
        )
        kind = db.execute(
            "SELECT stage_kind FROM saeima_bill_stages WHERE bill_id=?",
            (bill_id,)
        ).fetchone()[0]
        db.commit()
        db.close()
        assert kind == "vote"
```

- [ ] **Step 2: Run test, confirm failure**

Run: `source ../../.venv/Scripts/activate && PYTHONIOENCODING=utf-8 python -m pytest tests/test_saeima_bills.py::TestSchema -v`
Expected: 5 FAILED with `ImportError: cannot import name 'init_saeima_bills'`.

- [ ] **Step 3: Implement `init_saeima_bills()` in `src/saeima.py`**

Add this function immediately after `init_saeima_tables()` (around line 143, before `# --- Snapshot parsers --- `):

```python
def init_saeima_bills(db_path: str = DB_PATH) -> None:
    """Create Saeima Bills tracker tables (Phase 1A schema).

    Creates saeima_bills, saeima_bill_stages, saeima_bill_politicians tables
    plus indexes. Adds bill_id column to saeima_votes if not present.

    Idempotent: safe to call multiple times. Distinct from init_saeima_tables()
    so existing code that initializes vote-only tables continues to work.

    See docs/superpowers/specs/2026-04-22-saeima-bills-design.md § 3.1.
    """
    db = get_db(db_path)

    # Add bill_id column to saeima_votes if not present
    cols = [row[1] for row in db.execute("PRAGMA table_info(saeima_votes)").fetchall()]
    if "bill_id" not in cols:
        db.execute(
            "ALTER TABLE saeima_votes ADD COLUMN bill_id INTEGER REFERENCES saeima_bills(id)"
        )

    db.executescript("""
        CREATE TABLE IF NOT EXISTS saeima_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_nr TEXT UNIQUE NOT NULL,
            bill_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            topic TEXT,
            base_law_slug TEXT,
            institutional_submitter TEXT,
            current_stage TEXT,
            current_status TEXT,
            first_seen_at TIMESTAMP,
            last_updated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_bill_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
            stage_name TEXT NOT NULL,
            stage_result TEXT,
            stage_date TEXT,
            vote_id INTEGER REFERENCES saeima_votes(id),
            session_id INTEGER REFERENCES saeima_sessions(id),
            amendment_nr TEXT,
            stage_kind TEXT NOT NULL DEFAULT 'vote',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_bill_politicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
            politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            role TEXT NOT NULL,
            amendment_nr TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bill_id, politician_id, role, amendment_nr)
        );

        CREATE INDEX IF NOT EXISTS idx_bills_document_nr ON saeima_bills(document_nr);
        CREATE INDEX IF NOT EXISTS idx_bills_topic ON saeima_bills(topic);
        CREATE INDEX IF NOT EXISTS idx_bills_status ON saeima_bills(current_status);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_bill_id ON saeima_bill_stages(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_vote_id ON saeima_bill_stages(vote_id);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_kind ON saeima_bill_stages(stage_kind);
        CREATE INDEX IF NOT EXISTS idx_bill_politicians_bill_id ON saeima_bill_politicians(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bill_politicians_politician_id ON saeima_bill_politicians(politician_id);
        CREATE INDEX IF NOT EXISTS idx_saeima_votes_bill_id ON saeima_votes(bill_id);
    """)
    db.commit()
    db.close()
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `source ../../.venv/Scripts/activate && PYTHONIOENCODING=utf-8 python -m pytest tests/test_saeima_bills.py::TestSchema -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "feat(saeima): bills schema — init_saeima_bills() + 3 tables + bill_id FK"
```

---

## Task 2: Validation constants + canonicalization helpers

**Files:**
- Modify: `src/saeima.py`
- Modify: `tests/test_saeima_bills.py` (add `TestValidation` class)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_saeima_bills.py` (after `TestSchema` class):

```python
from src.saeima import (
    _VALID_BILL_TYPES,
    _VALID_STAGE_NAMES,
    _canonicalize_stage_name,
)


class TestValidation:
    def test_valid_bill_types(self):
        assert _VALID_BILL_TYPES == frozenset({"Lp14", "Lm14", "P14"})

    def test_valid_stage_names_includes_all_canonical(self):
        expected = {
            "iesniegts", "1.lasījums", "2.lasījums", "2.lasījums priekšlikums",
            "3.lasījums", "3.lasījums priekšlikums", "atgriezts komisijā",
            "atsaukts", "tiesneša_amats", "procesuāls", "Lm14 cits",
            "paziņojuma_balsojums", "nezināms",
        }
        assert _VALID_STAGE_NAMES == frozenset(expected)

    def test_canonicalize_stage_name_passes_canonical(self):
        assert _canonicalize_stage_name("1.lasījums") == "1.lasījums"
        assert _canonicalize_stage_name("tiesneša_amats") == "tiesneša_amats"

    def test_canonicalize_stage_name_strips_whitespace(self):
        assert _canonicalize_stage_name("  iesniegts ") == "iesniegts"

    def test_canonicalize_stage_name_rejects_unknown(self):
        with pytest.raises(ValueError, match="Unknown stage_name"):
            _canonicalize_stage_name("not_a_stage")

    def test_canonicalize_stage_name_rejects_empty(self):
        with pytest.raises(ValueError):
            _canonicalize_stage_name("")
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills.py::TestValidation -v`
Expected: 6 FAILED with import errors.

- [ ] **Step 3: Implement constants + helper**

Add to `src/saeima.py`, in a new section after `SAEIMA_BASE_URL` (around line 24):

```python
# ---------------------------------------------------------------------------
# Bill type & stage validation (Phase 1A)
# ---------------------------------------------------------------------------

_VALID_BILL_TYPES: frozenset[str] = frozenset({"Lp14", "Lm14", "P14"})

_VALID_STAGE_NAMES: frozenset[str] = frozenset({
    "iesniegts",
    "1.lasījums", "2.lasījums", "2.lasījums priekšlikums",
    "3.lasījums", "3.lasījums priekšlikums",
    "atgriezts komisijā", "atsaukts",
    "tiesneša_amats", "procesuāls", "Lm14 cits",
    "paziņojuma_balsojums",
    "nezināms",
})


def _canonicalize_stage_name(name: str) -> str:
    """Strip whitespace and verify against _VALID_STAGE_NAMES.

    Raises ValueError if not in the closed vocabulary set.
    See spec § 3.3 stage vocabulary table.
    """
    cleaned = (name or "").strip()
    if cleaned not in _VALID_STAGE_NAMES:
        raise ValueError(f"Unknown stage_name: {name!r}")
    return cleaned
```

- [ ] **Step 4: Run, confirm pass**

Run: `pytest tests/test_saeima_bills.py::TestValidation -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "feat(saeima): bill type & stage vocabulary constants + canonicalize helper"
```

---

## Task 3: Motif classification helpers — `resolve_bill_from_motif`, `_reading_from_motif`, `_resolve_base_law_slug`

**Files:**
- Modify: `src/saeima.py`
- Modify: `tests/test_saeima_bills.py` (add `TestMotifClassification` class)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_saeima_bills.py`:

```python
from src.saeima import (
    resolve_bill_from_motif,
    _reading_from_motif,
    _resolve_base_law_slug,
)


class TestResolveBillFromMotif:
    @pytest.mark.parametrize("motif,expected", [
        ("Grozījumi Valsts aizsardzības finansēšanas likumā (1315/Lp14), 3.lasījums", "1315/Lp14"),
        ("Kapsētu likums (1032/Lp14), 3.lasījums", "1032/Lp14"),
        ("Par Madaras Šenbrūnas iecelšanu par tiesnesi (939/Lm14)", "939/Lm14"),
        ("Par dronu uzbrukumiem (125/P14)", "125/P14"),
        ("motif bez document_nr", None),
        ("Lp14 in text but not parenthesized", None),
    ])
    def test_extracts_document_nr(self, motif, expected):
        assert resolve_bill_from_motif(motif) == expected


class TestReadingFromMotif:
    @pytest.mark.parametrize("motif,expected", [
        ("Grozījumi X (1315/Lp14), 1.lasījums", "1.lasījums"),
        ("Grozījumi X (1315/Lp14), 2.lasījums, steidzams", "2.lasījums"),
        ("Grozījumi X (1315/Lp14), 3.lasījums", "3.lasījums"),
        ("Grozījumi X (1315/Lp14), 2. lasījums, priekšlikums Nr.5", "2.lasījums priekšlikums"),
        ("Par Madaras Šenbrūnas iecelšanu par tiesnesi (939/Lm14)", "tiesneša_amats"),
        ("Par tiesneša X atbrīvošanu no amata (940/Lm14)", "tiesneša_amats"),
        ("Par termiņa pagarināšanu likumprojektam X (123/Lm14)", "procesuāls"),
        ("Par līdzatbildīgās komisijas noteikšanu (124/Lm14)", "procesuāls"),
        ("Par X paziņojumu (125/P14)", "paziņojuma_balsojums"),
        ("Par Air Baltic aizdevumu (953/Lm14)", "Lm14 cits"),
        ("motif bez atbilstības", "nezināms"),
    ])
    def test_classification(self, motif, expected):
        assert _reading_from_motif(motif) == expected

    def test_priority_lasijum_wins_over_lm14(self):
        # Hypothetical motif containing both '3.lasījums' and '/Lm14' — rule 1 wins
        assert _reading_from_motif("Lēmuma X (501/Lm14), 3.lasījums") == "3.lasījums"


class TestResolveBaseLawSlug:
    @pytest.fixture
    def laws_index(self):
        # Mimic wiki/laws/likumi.md slug list
        return {
            "udens-apsaimniekosanas-likums": "Ūdens apsaimniekošanas likums",
            "celu-satiksmes-likums": "Ceļu satiksmes likums",
            "valsts-aizsardzibas-finansesanas-likums": "Valsts aizsardzības finansēšanas likums",
        }

    def test_exact_title_match(self, laws_index):
        assert _resolve_base_law_slug(
            "Ūdens apsaimniekošanas likuma jautājumā", laws_index
        ) == "udens-apsaimniekosanas-likums"

    def test_grozijumi_pattern_match(self, laws_index):
        assert _resolve_base_law_slug(
            "Grozījumi Ceļu satiksmes likumā (1234/Lp14)", laws_index
        ) == "celu-satiksmes-likums"

    def test_unknown_law_returns_none(self, laws_index):
        assert _resolve_base_law_slug("Jauns nezināms likums", laws_index) is None

    def test_case_insensitive(self, laws_index):
        assert _resolve_base_law_slug(
            "GROZĪJUMI VALSTS AIZSARDZĪBAS FINANSĒŠANAS LIKUMĀ", laws_index
        ) == "valsts-aizsardzibas-finansesanas-likums"
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills.py::TestResolveBillFromMotif tests/test_saeima_bills.py::TestReadingFromMotif tests/test_saeima_bills.py::TestResolveBaseLawSlug -v`
Expected: ImportError for the 3 new functions.

- [ ] **Step 3: Implement helpers in `src/saeima.py`**

Add new section after the validation constants:

```python
# ---------------------------------------------------------------------------
# Motif classification helpers (Phase 1A)
# ---------------------------------------------------------------------------

_DOCUMENT_NR_RE = re.compile(r"\((\d+/(?:Lp14|Lm14|P14))\)")
_READING_RE = re.compile(r"\b(\d)\.\s?lasījum", re.IGNORECASE)
_PRIEKSLIK_RE = re.compile(r"priekšlikum", re.IGNORECASE)
_TIESNESHA_RE = re.compile(
    r"iecelšanu par.*tiesnesi|apstiprināšanu par.*tiesnesi|atbrīvošanu no tiesneša|atbrīvošanu no.*tiesneša",
    re.IGNORECASE,
)
_PROCESUALS_RE = re.compile(
    r"termiņa pagarināšanu|komisijas noteikšanu|atsaukšanu no.*komisijas",
    re.IGNORECASE,
)


def resolve_bill_from_motif(motif: str) -> Optional[str]:
    """Extract document_nr (e.g. '1315/Lp14') from a parenthesized motif suffix.

    Returns None if the pattern '(NNN/{Lp14|Lm14|P14})' is not found.
    Spec § 4.3 helper signature.
    """
    if not motif:
        return None
    m = _DOCUMENT_NR_RE.search(motif)
    return m.group(1) if m else None


def _reading_from_motif(motif: str) -> str:
    """Canonical stage_name no motif (case-insensitive); pirmais piemērojamais
    noteikums uzvar (sk. spec § 3.3 priority list). Rules 4–5 substring-match
    motif (kas Saeimas agenda formātā satur document_nr).

    Returns one of _VALID_STAGE_NAMES. Falls back to 'nezināms'.
    Note: 'atgriezts komisijā' un 'atsaukts' netiek automātiski klasificēti
    (agent prompt-driven only).
    """
    if not motif:
        return "nezināms"

    # Rule 1: reading number wins (most specific lexical anchor)
    m = _READING_RE.search(motif)
    if m:
        n = m.group(1)
        if _PRIEKSLIK_RE.search(motif):
            return f"{n}.lasījums priekšlikums"
        return f"{n}.lasījums"

    # Rule 2: judicial appointment / removal
    if _TIESNESHA_RE.search(motif):
        return "tiesneša_amats"

    # Rule 3: procedural (termiņi, komisijas)
    if _PROCESUALS_RE.search(motif):
        return "procesuāls"

    # Rule 4-5: document_nr suffix-based fallback
    if "/P14" in motif:
        return "paziņojuma_balsojums"
    if "/Lm14" in motif:
        return "Lm14 cits"

    # Rule 6: default
    return "nezināms"


def _resolve_base_law_slug(
    motif: str, laws_index: dict[str, str]
) -> Optional[str]:
    """Match motif text against `wiki/laws/likumi.md` slug → title index.

    Priority (case-insensitive):
    1. Exact title substring match → return slug.
    2. 'Grozījumi {title} likumā' or '{title} likumā' pattern → return slug.
    3. None.

    Spec § 6.2 contract.
    """
    if not motif or not laws_index:
        return None

    motif_lower = motif.lower()
    for slug, title in laws_index.items():
        if title.lower() in motif_lower:
            return slug
    # Fallback: try matching just the law name without trailing 'likums'
    for slug, title in laws_index.items():
        # Strip trailing ' likums'/' likumam' inflections if present in title
        base = re.sub(r"\s+likum[saiu]?\s*$", "", title, flags=re.IGNORECASE)
        if base and base.lower() in motif_lower:
            return slug
    return None
```

- [ ] **Step 4: Run, confirm pass**

Run: `pytest tests/test_saeima_bills.py::TestResolveBillFromMotif tests/test_saeima_bills.py::TestReadingFromMotif tests/test_saeima_bills.py::TestResolveBaseLawSlug -v`
Expected: ~17 passed (6 motif resolve + 12 reading + 4 base_law).

- [ ] **Step 5: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "feat(saeima): motif classification helpers — resolve_bill, reading_from_motif, base_law_slug"
```

---

## Task 4: `upsert_bill` + `append_bill_stage` helpers (atomic, idempotent)

**Files:**
- Modify: `src/saeima.py`
- Modify: `tests/test_saeima_bills.py` (add `TestUpsertBill` and `TestAppendBillStage`)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_saeima_bills.py`:

```python
from src.saeima import upsert_bill, append_bill_stage


@pytest.fixture
def bills_db(empty_db):
    """DB with bills schema initialized + a known politician."""
    init_saeima_bills(empty_db)
    db = get_db(empty_db)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) VALUES "
        "(1, 'Test Deputāts', 'JV')"
    )
    db.commit()
    db.close()
    return empty_db


class TestUpsertBill:
    def test_inserts_new_bill(self, bills_db):
        bid = upsert_bill(bills_db, "1315/Lp14", "Grozījumi X likumā", "Lp14")
        assert bid > 0
        db = get_db(bills_db)
        row = db.execute("SELECT * FROM saeima_bills WHERE id=?", (bid,)).fetchone()
        db.close()
        assert row["document_nr"] == "1315/Lp14"
        assert row["bill_type"] == "Lp14"

    def test_idempotent_on_document_nr(self, bills_db):
        bid1 = upsert_bill(bills_db, "1315/Lp14", "Title v1", "Lp14")
        bid2 = upsert_bill(bills_db, "1315/Lp14", "Title v2", "Lp14")
        assert bid1 == bid2
        db = get_db(bills_db)
        count = db.execute(
            "SELECT COUNT(*) FROM saeima_bills WHERE document_nr=?", ("1315/Lp14",)
        ).fetchone()[0]
        # Title updated to v2 (later upsert wins on title)
        title = db.execute(
            "SELECT title FROM saeima_bills WHERE document_nr=?", ("1315/Lp14",)
        ).fetchone()[0]
        db.close()
        assert count == 1
        assert title == "Title v2"

    def test_validates_bill_type(self, bills_db):
        with pytest.raises(ValueError, match="bill_type"):
            upsert_bill(bills_db, "1/Xx99", "Bad", "Xx99")

    def test_accepts_p14(self, bills_db):
        bid = upsert_bill(bills_db, "127/P14", "Par dronu uzbrukumiem", "P14")
        db = get_db(bills_db)
        bt = db.execute("SELECT bill_type FROM saeima_bills WHERE id=?", (bid,)).fetchone()[0]
        db.close()
        assert bt == "P14"


class TestAppendBillStage:
    def test_appends_stage_and_updates_current(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        sid = append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-04-01")
        assert sid > 0
        db = get_db(bills_db)
        bill = db.execute(
            "SELECT current_stage, current_status FROM saeima_bills WHERE id=?",
            (bid,)
        ).fetchone()
        db.close()
        assert bill["current_stage"] == "1.lasījums"
        # current_status maps from latest stage_result via convention
        assert bill["current_status"] in ("procesā", "pieņemts")

    def test_validates_stage_name(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        with pytest.raises(ValueError, match="Unknown stage_name"):
            append_bill_stage(bills_db, bid, "bogus_stage", "pieņemts", "2026-04-01")

    def test_current_stage_follows_latest_by_date(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-03-01")
        append_bill_stage(bills_db, bid, "2.lasījums", "pieņemts", "2026-04-01")
        append_bill_stage(bills_db, bid, "3.lasījums", "pieņemts", "2026-05-01")
        db = get_db(bills_db)
        cs = db.execute(
            "SELECT current_stage FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert cs == "3.lasījums"

    def test_atomic_rollback_on_invalid_stage(self, bills_db):
        bid = upsert_bill(bills_db, "1/Lp14", "Test", "Lp14")
        append_bill_stage(bills_db, bid, "1.lasījums", "pieņemts", "2026-03-01")
        with pytest.raises(ValueError):
            append_bill_stage(bills_db, bid, "bogus", "pieņemts", "2026-04-01")
        # current_stage should still be the prior valid one
        db = get_db(bills_db)
        cs = db.execute(
            "SELECT current_stage FROM saeima_bills WHERE id=?", (bid,)
        ).fetchone()[0]
        rows = db.execute(
            "SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert cs == "1.lasījums"
        assert rows == 1  # bogus row not persisted
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills.py::TestUpsertBill tests/test_saeima_bills.py::TestAppendBillStage -v`
Expected: ImportError.

- [ ] **Step 3: Implement helpers in `src/saeima.py`**

Add new section after motif classification helpers:

```python
# ---------------------------------------------------------------------------
# Bill upsert & stage append (Phase 1A)
# ---------------------------------------------------------------------------

def upsert_bill(
    db_path: str,
    document_nr: str,
    title: str,
    bill_type: str,
    institutional_submitter: Optional[str] = None,
    topic: Optional[str] = None,
    base_law_slug: Optional[str] = None,
    summary: Optional[str] = None,
) -> int:
    """Insert or update a saeima_bills row by document_nr (idempotent).

    On re-upsert: title, topic, institutional_submitter, base_law_slug, summary
    are overwritten with new non-None values; first_seen_at is preserved.

    Returns the bill_id. Raises ValueError if bill_type not in _VALID_BILL_TYPES.
    Spec § 4.3 + § 5.2 backfill use.
    """
    if bill_type not in _VALID_BILL_TYPES:
        raise ValueError(
            f"bill_type must be one of {sorted(_VALID_BILL_TYPES)}, got {bill_type!r}"
        )

    db = get_db(db_path)
    now = now_lv()
    existing = db.execute(
        "SELECT id FROM saeima_bills WHERE document_nr=?", (document_nr,)
    ).fetchone()

    if existing:
        bid = existing["id"]
        db.execute(
            """UPDATE saeima_bills SET
                title = ?,
                bill_type = ?,
                topic = COALESCE(?, topic),
                institutional_submitter = COALESCE(?, institutional_submitter),
                base_law_slug = COALESCE(?, base_law_slug),
                summary = COALESCE(?, summary),
                last_updated_at = ?
              WHERE id = ?""",
            (title, bill_type, topic, institutional_submitter, base_law_slug,
             summary, now, bid),
        )
    else:
        cur = db.execute(
            """INSERT INTO saeima_bills (
                document_nr, bill_type, title, topic, institutional_submitter,
                base_law_slug, summary, current_status, first_seen_at,
                last_updated_at
              ) VALUES (?, ?, ?, ?, ?, ?, ?, 'procesā', ?, ?)""",
            (document_nr, bill_type, title, topic, institutional_submitter,
             base_law_slug, summary, now, now),
        )
        bid = cur.lastrowid

    db.commit()
    db.close()
    return bid


def append_bill_stage(
    db_path: str,
    bill_id: int,
    stage_name: str,
    stage_result: Optional[str],
    stage_date: str,
    vote_id: Optional[int] = None,
    session_id: Optional[int] = None,
    amendment_nr: Optional[str] = None,
) -> int:
    """Append a stage row + atomically update parent bill's denorm fields.

    stage_name validated via _canonicalize_stage_name (raises ValueError if invalid).
    Updates saeima_bills.current_stage to this stage_name (assumes caller appends
    in chronological order; if not, current_stage will reflect insertion order
    rather than max(stage_date) — see test_current_stage_follows_latest_by_date
    for the date-aware invariant).

    All-or-nothing transaction: stage row + bill update commit together,
    or both rollback. stage_kind defaults to 'vote' at DB level (Phase 1A
    only writes vote-kind stages).

    Returns the new stage row id. Spec § 4.3.
    """
    canonical = _canonicalize_stage_name(stage_name)  # raises before opening txn

    db = get_db(db_path)
    try:
        cur = db.execute(
            """INSERT INTO saeima_bill_stages (
                bill_id, stage_name, stage_result, stage_date,
                vote_id, session_id, amendment_nr, stage_kind
              ) VALUES (?, ?, ?, ?, ?, ?, ?, 'vote')""",
            (bill_id, canonical, stage_result, stage_date, vote_id,
             session_id, amendment_nr),
        )
        sid = cur.lastrowid

        # Recompute current_stage / current_status from latest stage by date
        latest = db.execute(
            """SELECT stage_name, stage_result FROM saeima_bill_stages
               WHERE bill_id=? AND stage_kind='vote'
               ORDER BY stage_date DESC, id DESC LIMIT 1""",
            (bill_id,),
        ).fetchone()
        new_stage = latest["stage_name"]
        new_result = latest["stage_result"]
        new_status = "pieņemts" if new_result == "pieņemts" and canonical.startswith("3.") \
                     else ("noraidīts" if new_result == "noraidīts" else "procesā")

        db.execute(
            "UPDATE saeima_bills SET current_stage=?, current_status=?, "
            "last_updated_at=? WHERE id=?",
            (new_stage, new_status, now_lv(), bill_id),
        )
        db.commit()
        return sid
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- [ ] **Step 4: Run, confirm pass**

Run: `pytest tests/test_saeima_bills.py::TestUpsertBill tests/test_saeima_bills.py::TestAppendBillStage -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "feat(saeima): upsert_bill (idempotent) + append_bill_stage (atomic + denorm)"
```

---

## Task 5: `match_submitters_to_politicians` helper

**Files:**
- Modify: `src/saeima.py`
- Modify: `tests/test_saeima_bills.py` (add `TestMatchSubmitters` class)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_saeima_bills.py`:

```python
from src.saeima import match_submitters_to_politicians


@pytest.fixture
def submitter_db(bills_db):
    db = get_db(bills_db)
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party, name_forms) VALUES (?, ?, ?, ?)",
        [
            (10, "Maija Armaņeva", "PRO", '["Maija Armaņeva", "Armaņeva"]'),
            (11, "Andris Šuvajevs", "PRO", '["Andris Šuvajevs", "Šuvajevs"]'),
            (12, "Krišjānis Feldmans", "JV", '["Krišjānis Feldmans", "Feldmans"]'),
        ],
    )
    db.commit()
    db.close()
    return bills_db


class TestMatchSubmitters:
    def test_matches_known_deputies(self, submitter_db):
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        matched, unmatched = match_submitters_to_politicians(
            submitter_db, bid, ["Maija Armaņeva", "Šuvajevs", "Feldmans"]
        )
        assert matched == 3
        assert unmatched == []
        db = get_db(submitter_db)
        rows = db.execute(
            "SELECT politician_id, role FROM saeima_bill_politicians WHERE bill_id=?",
            (bid,),
        ).fetchall()
        db.close()
        assert len(rows) == 3
        assert {r["politician_id"] for r in rows} == {10, 11, 12}
        assert all(r["role"] == "submitter" for r in rows)

    def test_reports_unmatched(self, submitter_db):
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        matched, unmatched = match_submitters_to_politicians(
            submitter_db, bid, ["Maija Armaņeva", "Nezināms Deputāts"]
        )
        assert matched == 1
        assert unmatched == ["Nezināms Deputāts"]

    def test_idempotent_via_unique_constraint(self, submitter_db):
        bid = upsert_bill(submitter_db, "9/Lp14", "Test", "Lp14")
        match_submitters_to_politicians(submitter_db, bid, ["Maija Armaņeva"])
        match_submitters_to_politicians(submitter_db, bid, ["Maija Armaņeva"])
        db = get_db(submitter_db)
        count = db.execute(
            "SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=?", (bid,)
        ).fetchone()[0]
        db.close()
        assert count == 1  # UNIQUE(bill_id, politician_id, role, amendment_nr) wins
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills.py::TestMatchSubmitters -v`
Expected: ImportError.

- [ ] **Step 3: Implement helper in `src/saeima.py`**

Add after `append_bill_stage`:

```python
def match_submitters_to_politicians(
    db_path: str,
    bill_id: int,
    submitter_names: list[str],
) -> tuple[int, list[str]]:
    """Match submitter names to tracked_politicians via existing name_forms index.

    Inserts role='submitter' rows into saeima_bill_politicians (idempotent
    via the UNIQUE(bill_id, politician_id, role, amendment_nr) constraint).
    Returns (matched_count, unmatched_names) for caller logging.

    Spec § 4.3.
    """
    if not submitter_names:
        return 0, []

    name_index = _build_name_index(db_path)  # already exists in this module
    db = get_db(db_path)
    matched = 0
    unmatched: list[str] = []

    for raw in submitter_names:
        key = raw.lower().strip()
        pid = name_index.get(key)
        if pid is None:
            # Try partial match (same logic as match_deputies_to_politicians)
            for name_key, candidate_pid in name_index.items():
                if key == name_key or name_key in key or key in name_key:
                    pid = candidate_pid
                    break

        if pid is None:
            unmatched.append(raw)
            continue

        try:
            db.execute(
                "INSERT INTO saeima_bill_politicians "
                "(bill_id, politician_id, role) VALUES (?, ?, 'submitter')",
                (bill_id, pid),
            )
            matched += 1
        except sqlite3.IntegrityError:
            # UNIQUE constraint — already linked, skip
            pass

    db.commit()
    db.close()
    return matched, unmatched
```

Note: Add `import sqlite3` at the top of the module if not already imported (it is — see line 17 area; verify).

- [ ] **Step 4: Run, confirm pass**

Run: `pytest tests/test_saeima_bills.py::TestMatchSubmitters -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "feat(saeima): match_submitters_to_politicians via name_forms index"
```

---

## Task 6: `parse_agenda_snapshot` parser + `AgendaBill` dataclass

**Files:**
- Modify: `src/saeima.py`
- Create: `tests/test_saeima_bills_integration.py`

- [ ] **Step 1: Write failing integration test (against real fixture)**

Create `tests/test_saeima_bills_integration.py`:

```python
"""Phase 1A integration tests — parse real agenda snapshot fixtures.

The 2026-04-16 snapshot at data/saeima_snapshots/2026-04-16/agenda.md
is the canonical fixture for parser regression detection.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.db import init_db
from src.saeima import (
    init_saeima_tables,
    init_saeima_bills,
    parse_agenda_snapshot,
)


FIXTURE_AGENDA = Path("data/saeima_snapshots/2026-04-16/agenda.md")


@pytest.mark.skipif(
    not FIXTURE_AGENDA.exists(),
    reason="agenda.md fixture missing — run @saeima-tracker first to populate",
)
class TestParseAgenda20260416:
    def test_extracts_at_least_one_bill(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        assert len(bills) >= 1, "agenda fixture should contain bills"

    def test_extracted_bills_have_valid_types(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        for b in bills:
            assert b.bill_type in {"Lp14", "Lm14", "P14"}, f"unknown bill_type {b.bill_type!r}"
            assert b.document_nr.endswith(b.bill_type), \
                f"document_nr suffix mismatch: {b.document_nr!r} vs {b.bill_type!r}"
            assert b.title, "every bill should have a title"

    def test_some_bills_have_individual_submitters(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_individual = [b for b in bills if b.individual_submitters]
        # Expect >=1 bill with deputy submitters in a real agenda
        assert with_individual, "expected at least one bill with individual_submitters"

    def test_some_bills_have_institutional_submitter(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_inst = [b for b in bills if b.institutional_submitter]
        assert with_inst, "expected at least one bill with institutional_submitter (Ministru kabinets, etc.)"
```

Also add a small unit-shaped test to `tests/test_saeima_bills.py`:

```python
from src.saeima import parse_agenda_snapshot, AgendaBill


class TestParseAgendaSynthetic:
    def test_extracts_lp14_bill_with_individual_submitters(self):
        snapshot = """
        [some agenda noise]
        Likumprojekts Grozījumi Imigrācijas likumā (1234/Lp14)
        Iesniedzēji: Deputāti Maija Armaņeva, Andris Šuvajevs
        [more noise]
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        b = bills[0]
        assert b.document_nr == "1234/Lp14"
        assert b.bill_type == "Lp14"
        assert "Imigrācijas" in b.title
        assert "Maija Armaņeva" in b.individual_submitters
        assert "Andris Šuvajevs" in b.individual_submitters
        assert b.institutional_submitter is None

    def test_extracts_lm14_with_institutional_submitter(self):
        snapshot = """
        Lēmuma projekts Par Air Baltic aizdevumu (953/Lm14)
        Iesniedzējs: Ministru kabinets
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        b = bills[0]
        assert b.document_nr == "953/Lm14"
        assert b.bill_type == "Lm14"
        assert b.institutional_submitter == "Ministru kabinets"
        assert b.individual_submitters == []

    def test_extracts_p14_bill(self):
        snapshot = """
        Paziņojums Par dronu uzbrukumiem (125/P14)
        Iesniedzēji: Deputāti Imants Parādnieks
        """
        bills = parse_agenda_snapshot(snapshot)
        assert len(bills) == 1
        assert bills[0].bill_type == "P14"

    def test_skips_unknown_document_nr_suffix(self):
        snapshot = "Some doc (999/Xx99)\nIesniedzējs: Test"
        bills = parse_agenda_snapshot(snapshot)
        assert bills == []
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills.py::TestParseAgendaSynthetic tests/test_saeima_bills_integration.py -v`
Expected: ImportError for `parse_agenda_snapshot`, `AgendaBill`.

- [ ] **Step 3: Implement parser + dataclass in `src/saeima.py`**

Add new section after motif classification helpers:

```python
# ---------------------------------------------------------------------------
# Agenda snapshot parser (Phase 1A)
# ---------------------------------------------------------------------------

@dataclass
class AgendaBill:
    """Single bill extracted from an agenda snapshot.

    Spec § 4.3.
    """
    document_nr: str                                # "1315/Lp14", "127/P14"
    bill_type: str                                  # "Lp14" | "Lm14" | "P14"
    title: str
    individual_submitters: list[str] = field(default_factory=list)
    institutional_submitter: Optional[str] = None
    reading_hint: Optional[str] = None
    vote_uuid: Optional[str] = None


_AGENDA_BILL_RE = re.compile(
    r"(Likumprojekts|Lēmuma projekts|Paziņojums)\s+(.+?)\s*\((\d+/(?:Lp14|Lm14|P14))\)",
    re.IGNORECASE | re.DOTALL,
)
_INST_SUBMITTER_RE = re.compile(
    r"Iesniedzējs:\s*([^\n]+?)(?=\n|$)",
    re.IGNORECASE,
)
_INDIVIDUAL_SUBMITTER_RE = re.compile(
    r"Deputāti?\s+([^\n]+?)(?=\n|$)",
    re.IGNORECASE,
)


def parse_agenda_snapshot(snapshot_text: str) -> list[AgendaBill]:
    """Izvelk visus Lp14/Lm14/P14 items no agenda snapshot.

    Regex pattern: 'Likumprojekts|Lēmuma projekts|Paziņojums' ... '(NNNN/(Lp14|Lm14|P14))'.
    For each bill found, looks within ~500 chars of the match for nearby
    'Iesniedzējs:' or 'Deputāti' lines to populate submitter fields.

    bill_type derivēts no document_nr sufiksa; jebkurš cits sufikss → log + skip.
    Spec § 4.3.
    """
    if not snapshot_text:
        return []

    bills: list[AgendaBill] = []
    for m in _AGENDA_BILL_RE.finditer(snapshot_text):
        kind, raw_title, doc_nr = m.group(1), m.group(2), m.group(3)
        if "/Lp14" in doc_nr:
            bill_type = "Lp14"
        elif "/Lm14" in doc_nr:
            bill_type = "Lm14"
        elif "/P14" in doc_nr:
            bill_type = "P14"
        else:
            # Defensive — regex already restricts to whitelist
            continue

        title = raw_title.strip().rstrip(",").strip()

        # Look ahead 500 chars for submitter info
        end = m.end()
        window = snapshot_text[end:end + 500]
        inst_match = _INST_SUBMITTER_RE.search(window)
        ind_match = _INDIVIDUAL_SUBMITTER_RE.search(window)

        institutional = inst_match.group(1).strip() if inst_match else None
        # Filter out 'Deputāti' from institutional capture (it's not institutional)
        if institutional and institutional.lower().startswith("deputāt"):
            institutional = None

        individual: list[str] = []
        if ind_match:
            raw_names = ind_match.group(1).strip()
            individual = [n.strip() for n in raw_names.split(",") if n.strip()]

        bills.append(AgendaBill(
            document_nr=doc_nr,
            bill_type=bill_type,
            title=title,
            individual_submitters=individual,
            institutional_submitter=institutional,
        ))

    return bills
```

Also add `from dataclasses import dataclass, field` import at the top (verify existing imports — `dataclass` already imported; ensure `field` is too).

- [ ] **Step 4: Run, confirm pass (synthetic + fixture)**

Run: `pytest tests/test_saeima_bills.py::TestParseAgendaSynthetic tests/test_saeima_bills_integration.py -v`
Expected: 4 + 4 = 8 passed (or 4 passed and 4 skipped if fixture missing).

- [ ] **Step 5: If fixture tests skip, manually run parser on fixture**

```bash
source ../../.venv/Scripts/activate && PYTHONIOENCODING=utf-8 python -c "
from pathlib import Path
from src.saeima import parse_agenda_snapshot
text = Path('data/saeima_snapshots/2026-04-16/agenda.md').read_text(encoding='utf-8')
bills = parse_agenda_snapshot(text)
print(f'Extracted {len(bills)} bills:')
for b in bills[:5]:
    print(f'  {b.document_nr}: {b.title[:60]}')
print(f'  with individual_submitters: {sum(1 for b in bills if b.individual_submitters)}')
print(f'  with institutional_submitter: {sum(1 for b in bills if b.institutional_submitter)}')
"
```

If 0 bills extracted, the fixture format may differ from the regex assumption. Stop and escalate — agenda format spike needed.

- [ ] **Step 6: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py tests/test_saeima_bills_integration.py
git commit -m "feat(saeima): parse_agenda_snapshot + AgendaBill dataclass"
```

---

## Task 7: Backfill script — `scripts/backfill_saeima_bills.py`

**Files:**
- Create: `scripts/backfill_saeima_bills.py`
- Modify: `tests/test_saeima_bills_integration.py` (add backfill test)

- [ ] **Step 1: Write failing integration test**

Add to `tests/test_saeima_bills_integration.py`:

```python
from src.saeima import init_saeima_bills


@pytest.fixture
def votes_db():
    """DB with 5 saeima_votes pre-populated (mimics retro state)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)

    db = get_db(path)
    db.executemany(
        """INSERT INTO saeima_votes (
            id, motif, vote_date, total_par, total_pret, total_atturas,
            total_nebalso, result, url, summary, document_nr, topic
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "Grozījumi X (1/Lp14), 1.lasījums", "2026-03-01", 60, 30, 5, 0,
             "pieņemts", "u1", "Test summary", "1/Lp14", "Aizsardzība"),
            (2, "Grozījumi X (1/Lp14), 2.lasījums", "2026-04-01", 65, 28, 4, 0,
             "pieņemts", "u2", "v2 summary", "1/Lp14", "Aizsardzība"),
            (3, "Par tiesneša Y iecelšanu (5/Lm14)", "2026-04-10", 80, 10, 5, 0,
             "pieņemts", "u3", "Tiesneša summary", "5/Lm14", "Tieslietas"),
            (4, "Par dronu uzbrukumiem (12/P14)", "2026-04-15", 90, 5, 1, 0,
             "pieņemts", "u4", "Drone summary", "12/P14", "Aizsardzība"),
            (5, "motif bez document_nr", "2026-04-20", 50, 30, 5, 0,
             "pieņemts", "u5", None, None, "Cits"),
        ],
    )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture(autouse=False)
def _isolated_db_path(monkeypatch, votes_db):
    """Route src.db.DB_PATH (used by backfill script) at the test DB."""
    import src.db as _dbm
    monkeypatch.setattr(_dbm, "DB_PATH", votes_db)
    return votes_db


class TestBackfill:
    def test_backfill_creates_bills_for_each_unique_doc_nr(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        report = backfill(db_path=_isolated_db_path)
        # 4 unique document_nrs (1/Lp14, 5/Lm14, 12/P14) — vote 5 has NULL doc_nr (skipped)
        assert report["bills_created"] == 3
        assert report["votes_with_bill_id"] == 4  # rows 1,2,3,4 linked
        assert report["votes_skipped_null_doc_nr"] == 1

    def test_backfill_appends_stages_per_vote(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        backfill(db_path=_isolated_db_path)
        db = get_db(_isolated_db_path)
        # vote 1 + vote 2 → 2 stages on bill 1/Lp14 (1.lasījums + 2.lasījums)
        rows = db.execute(
            """SELECT s.stage_name FROM saeima_bill_stages s
               JOIN saeima_bills b ON b.id = s.bill_id
               WHERE b.document_nr = '1/Lp14'
               ORDER BY s.stage_date"""
        ).fetchall()
        db.close()
        assert [r["stage_name"] for r in rows] == ["1.lasījums", "2.lasījums"]

    def test_backfill_unknown_threshold_under_10pct(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        report = backfill(db_path=_isolated_db_path)
        # Of 4 classifiable votes: 1.lasījums, 2.lasījums, tiesneša_amats, paziņojuma_balsojums = 0 unknowns
        unknown_pct = report["unknown_stages"] / max(report["votes_with_bill_id"], 1)
        assert unknown_pct <= 0.10

    def test_backfill_idempotent(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        backfill(db_path=_isolated_db_path)
        report2 = backfill(db_path=_isolated_db_path)
        # Re-run: same bills, no duplicate stage rows
        db = get_db(_isolated_db_path)
        bills = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
        # Note: stages MAY duplicate without a UNIQUE constraint on
        # (bill_id, stage_name, stage_date, vote_id). The backfill skript
        # SHOULD detect existing stages by vote_id and skip them.
        stages_total = db.execute("SELECT COUNT(*) FROM saeima_bill_stages").fetchone()[0]
        db.close()
        assert bills == 3
        assert stages_total == 4  # 1+2+3+4 votes → 4 stages, no doubling
```

- [ ] **Step 2: Run, confirm fail**

Run: `pytest tests/test_saeima_bills_integration.py::TestBackfill -v`
Expected: ImportError for `scripts.backfill_saeima_bills`.

- [ ] **Step 3: Implement `scripts/backfill_saeima_bills.py`**

```python
"""One-shot backfill of saeima_bills from existing saeima_votes rows.

Reads all saeima_votes WHERE document_nr IS NOT NULL, groups by document_nr,
upserts a bill per group, and appends one stage row per vote (using
_reading_from_motif for stage_name classification). Idempotent — safe to
re-run; existing bills are upserted, stages with the same vote_id are skipped.

Spec § 5. Acceptance: spec § 5.4.

Usage:
    python scripts/backfill_saeima_bills.py             # production DB
    python scripts/backfill_saeima_bills.py --dry-run   # report-only
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import DB_PATH, get_db, now_lv  # noqa: E402
from src.saeima import (  # noqa: E402
    init_saeima_bills,
    upsert_bill,
    append_bill_stage,
    resolve_bill_from_motif,
    _reading_from_motif,
)


def _extract_title_from_motif(motif: str) -> str:
    """Extract a human-readable title from a vote motif.

    Strips the trailing '(NNN/Lp14)' suffix and reading qualifier.
    """
    if not motif:
        return ""
    # Drop everything from '(NNN/' onward
    title = motif.split("(")[0].strip().rstrip(",").strip()
    return title or motif[:80]


def _bill_type_from_doc_nr(doc_nr: str) -> str | None:
    if "/Lp14" in doc_nr:
        return "Lp14"
    if "/Lm14" in doc_nr:
        return "Lm14"
    if "/P14" in doc_nr:
        return "P14"
    return None


def backfill(db_path: str = DB_PATH, dry_run: bool = False) -> dict:
    """Run the backfill. Returns a report dict for caller logging."""
    init_saeima_bills(db_path)

    db = get_db(db_path)
    rows = db.execute(
        """SELECT id, motif, document_nr, vote_date, result, summary, topic
           FROM saeima_votes
           ORDER BY vote_date ASC, id ASC"""
    ).fetchall()

    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    skipped_null = 0
    skipped_bad_type = 0
    for v in rows:
        if not v["document_nr"]:
            skipped_null += 1
            continue
        bt = _bill_type_from_doc_nr(v["document_nr"])
        if bt is None:
            skipped_bad_type += 1
            continue
        grouped[v["document_nr"]].append(v)

    report = {
        "bills_created": 0,
        "votes_with_bill_id": 0,
        "votes_skipped_null_doc_nr": skipped_null,
        "votes_skipped_bad_type": skipped_bad_type,
        "unknown_stages": 0,
        "total_stages_appended": 0,
    }

    for doc_nr, vote_list in grouped.items():
        bill_type = _bill_type_from_doc_nr(doc_nr)
        latest = vote_list[-1]
        title = _extract_title_from_motif(latest["motif"])
        topic = latest["topic"]
        summary = latest["summary"]

        if dry_run:
            report["bills_created"] += 1
            continue

        bid = upsert_bill(
            db_path, doc_nr, title, bill_type,
            topic=topic, summary=summary,
        )
        report["bills_created"] += 1

        # For each vote in this group, append a stage if not already present (idempotency)
        for v in vote_list:
            existing = db.execute(
                "SELECT id FROM saeima_bill_stages WHERE vote_id=?", (v["id"],)
            ).fetchone()
            if existing:
                # Already backfilled this vote; just ensure votes.bill_id is set
                db.execute(
                    "UPDATE saeima_votes SET bill_id=? WHERE id=? AND bill_id IS NULL",
                    (bid, v["id"]),
                )
                continue

            stage_name = _reading_from_motif(v["motif"] or "")
            if stage_name == "nezināms":
                report["unknown_stages"] += 1
            append_bill_stage(
                db_path, bid, stage_name, v["result"], v["vote_date"], vote_id=v["id"],
            )
            report["total_stages_appended"] += 1

            db.execute(
                "UPDATE saeima_votes SET bill_id=? WHERE id=?",
                (bid, v["id"]),
            )

        report["votes_with_bill_id"] += len(vote_list)

    if not dry_run:
        db.commit()
    db.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Report-only; no DB writes")
    args = ap.parse_args()
    report = backfill(dry_run=args.dry_run)
    print(f"Backfill report ({'dry-run' if args.dry_run else 'live'}):")
    for k, v in report.items():
        print(f"  {k}: {v}")
    if report["votes_with_bill_id"] > 0:
        unknown_pct = (report["unknown_stages"] / report["votes_with_bill_id"]) * 100
        print(f"  unknown_stages_pct: {unknown_pct:.1f}%")
        if unknown_pct > 10.0:
            print("  WARN: unknown_stages > 10% — consider agenda re-parse (spec § 5.4)")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run integration tests**

Run: `pytest tests/test_saeima_bills_integration.py::TestBackfill -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/backfill_saeima_bills.py tests/test_saeima_bills_integration.py
git commit -m "feat(saeima): backfill_saeima_bills script — votes → bills + stages"
```

---

## Task 8: End-to-end smoke — backfill on dev DB + sanity check

**Files:** No code changes; this is a manual verification step that produces a backfill report.

- [ ] **Step 1: Backup dev DB before live backfill**

```bash
cp data/atmina.db data/atmina.db.pre-bills-backfill-$(date +%Y%m%d-%H%M%S).backup
ls -lh data/atmina.db data/atmina.db.pre-bills-backfill-*.backup
```

- [ ] **Step 2: Dry-run backfill from main checkout (worktree may not have data/)**

If the worktree doesn't have `data/atmina.db` (gitignored), run the dry-run from the parent main checkout:

```bash
cd "~/atmina"  # main checkout
source .venv/Scripts/activate && PYTHONIOENCODING=utf-8 python scripts/backfill_saeima_bills.py --dry-run
```

Expected output:
```
Backfill report (dry-run):
  bills_created: ~91
  votes_with_bill_id: 0          # dry-run doesn't link
  votes_skipped_null_doc_nr: 34
  votes_skipped_bad_type: 0
  unknown_stages: 0              # dry-run doesn't classify
  total_stages_appended: 0
```

If `bills_created < 80` or `votes_skipped_null_doc_nr > 50`, stop and investigate.

- [ ] **Step 3: Live backfill (after dry-run sanity check)**

```bash
PYTHONIOENCODING=utf-8 python scripts/backfill_saeima_bills.py
```

Expected:
```
  bills_created: ~91
  votes_with_bill_id: 105
  votes_skipped_null_doc_nr: 34
  unknown_stages: <10
  unknown_stages_pct: <10%
```

If `unknown_stages_pct > 10%`, the script returns exit 1 and prints WARN. Stop and review which motifs aren't classified — may need to extend Phase 0 vocabulary.

- [ ] **Step 4: Manual sanity SQL queries**

```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Bills:', db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0])
print('Stages:', db.execute('SELECT COUNT(*) FROM saeima_bill_stages').fetchone()[0])
print('Votes linked:', db.execute('SELECT COUNT(*) FROM saeima_votes WHERE bill_id IS NOT NULL').fetchone()[0])
print()
print('Bill types:')
for r in db.execute('SELECT bill_type, COUNT(*) FROM saeima_bills GROUP BY bill_type').fetchall():
    print(f'  {r[0]}: {r[1]}')
print()
print('Stage names:')
for r in db.execute('SELECT stage_name, COUNT(*) FROM saeima_bill_stages GROUP BY stage_name ORDER BY 2 DESC').fetchall():
    print(f'  {r[0]}: {r[1]}')
"
```

Expected approximately:
- Bills: 91
- Stages: 105
- Bill types: Lp14 ~70, Lm14 ~16, P14 ~5
- Stage names: 1.lasījums ~36, 2.lasījums ~28, 3.lasījums ~18, priekšlikumi ~11, tiesneša_amats ~10, procesuāls ~3, paziņojuma_balsojums ~5, Lm14 cits ~7, nezināms ≤10

- [ ] **Step 5: Verify no regression in existing test_saeima.py**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/test_saeima.py tests/test_saeima_bills.py tests/test_saeima_bills_integration.py -v 2>&1 | tail -20
```

All tests should pass. The 19 pre-existing failures elsewhere in the suite (test_ingest, test_wiki) are unrelated.

- [ ] **Step 6: Commit smoke results (no code changes; just a brief note)**

This step has no commit. The smoke test result is reported back to the controller for human review.

---

## Self-Review

**Spec coverage check:**

| Spec § | Coverage |
|---|---|
| § 3.1 schema | Task 1 ✓ |
| § 3.3 vocabulary constants | Task 2 ✓ |
| § 4.3 helpers (`upsert_bill`, `append_bill_stage`, `parse_agenda_snapshot`, `match_submitters_to_politicians`, `resolve_bill_from_motif`, `_reading_from_motif`, `_resolve_base_law_slug`) | Tasks 3, 4, 5, 6 ✓ |
| § 5 backfill | Task 7 ✓ |
| § 8.1 unit tests (9 tests) | Tasks 1, 2, 3, 4, 5 ✓ — actually ~25 tests (more granular than spec's 9 named) |
| § 8.2 integration tests (2 tests) | Task 6 (parse_agenda fixture) + Task 7 (backfill) ✓ |
| § 5.4 acceptance | Task 8 ✓ |

**Out of scope (Phase 1B/1C):**
- UI (templates, generate functions) — Phase 1B
- Agent prompt updates — Phase 1C
- Cross-linking auto-link — Phase 1C
- BILLS-SYNC-AUTO render — Phase 1C
- Runbook (`wiki/operations/saeima-bills.md`) — Phase 1C

**Placeholder scan:** All code blocks are concrete; no TBDs, no "implement later". Function signatures match across tasks (e.g., `upsert_bill(db_path, document_nr, title, bill_type, ...)` consistent in Task 4 + Task 7).

**Type consistency:**
- `_VALID_BILL_TYPES`, `_VALID_STAGE_NAMES` are `frozenset[str]` (immutable) — referenced consistently
- `AgendaBill` dataclass — defined Task 6, used in `parse_agenda_snapshot` return type
- `db_path: str` parameter convention matches existing `init_saeima_tables` style
- `now_lv()` import from `src.db` matches CLAUDE.md output convention

**Dependencies between tasks:**
- Task 2 → 3 (motif helpers reference `_VALID_STAGE_NAMES` indirectly via `_reading_from_motif` returning canonical strings)
- Task 4 → uses Task 1 schema + Task 2 `_canonicalize_stage_name`
- Task 5 → uses Task 1 schema + existing `_build_name_index`
- Task 6 → defines `AgendaBill` used downstream
- Task 7 → uses Tasks 1, 3, 4 (schema + classification + upsert/append)
- Task 8 → manual smoke; no further code

Sequential execution required (not parallelizable) due to shared `src/saeima.py` file.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-27-saeima-bills-phase-1a-schema-and-helpers.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review, fast iteration. Tasks 1–7 are sequential (same file).

**2. Inline Execution** — execute tasks in this session via executing-plans skill.

**Kuru pieeju?**
