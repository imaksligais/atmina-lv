# Saeima Bills Phase 1B-ii Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sasaista bills datus ar wiki/laws — `base_law_slug` retro-backfill, BILLS-SYNC-AUTO marķiera writeback wiki/laws/<slug>.md failos, `/likumi/<slug>.html` publiskā render (33 jaunas lapas), "Saistītais bāzes likums" bloks detail lapā, politiķa profila Likumprojekti sekcija (conditional), naming fix.

**Architecture:** Wiki sync raksta BILLS-SYNC-AUTO blokus diskā (Obsidian source of truth). `_generate_law_pages` lasa `wiki/laws/*.md` un renderē `/likumi/<slug>.html` ar markdown→HTML. Politiķa profila sekcija parādās tikai ja `saeima_bill_politicians` junction populēta priekš šī politiķa.

**Tech Stack:** Python 3.11+ · SQLite (WAL) · Jinja2 · markdown + bleach · pytest.

**Spec atsauce:** [`docs/superpowers/specs/2026-04-27-saeima-bills-phase-1b-ii-design.md`](../specs/2026-04-27-saeima-bills-phase-1b-ii-design.md)

---

## Task 0: Worktree setup + baseline verify

**Files:**
- Setup: jauns git worktree `.worktrees/saeima-bills-phase-1b-ii` uz branch `saeima-bills-phase-1b-ii`

- [ ] **Step 1: Izveido worktree no master**

```bash
git worktree add .worktrees/saeima-bills-phase-1b-ii -b saeima-bills-phase-1b-ii master
cd .worktrees/saeima-bills-phase-1b-ii
```

Verificē, ka esi `saeima-bills-phase-1b-ii` branch'ā ar tīru working tree.

- [ ] **Step 2: Aktivizē venv**

```bash
source ../../.venv/Scripts/activate
```

- [ ] **Step 3: Verificē baseline tests**

```bash
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py tests/test_generate_bills.py tests/test_generate.py -q
```

Sagaidāms: 162 passed (post-1B-i baseline).

- [ ] **Step 4: Kopē DB no master worktree (smoke testiem vēlāk)**

```bash
cp "~/atmina/data/atmina.db" data/atmina.db
ls -la data/atmina.db
```

Sagaidāms: ~127 MB.

- [ ] **Step 5: Verificē DB stāvokli**

```bash
python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Bills:', db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0])
print('base_law_slug populated:', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL').fetchone()[0])
print('Junction rows:', db.execute('SELECT COUNT(*) FROM saeima_bill_politicians').fetchone()[0])
db.close()
"
```

Sagaidāms: Bills=118, base_law_slug populated=0, Junction rows=0.

---

## Task 1: `base_law_slug` retro-backfill skripts

**Files:**
- Create: `scripts/backfill_base_law_slug.py`
- Test: `tests/test_phase_1b_ii.py` (jauns)

- [ ] **Step 1: Izveido testa failu ar fixture**

`tests/test_phase_1b_ii.py`:

```python
"""Phase 1B-ii — base_law_slug backfill, wiki/laws auto-render, profile section."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_bills, init_saeima_tables, upsert_bill, append_bill_stage


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def db_with_bills_for_backfill(tmp_path):
    """SQLite ar 3 bills, kuriem visiem base_law_slug=NULL."""
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    # Bill 1: title satur "Imigrācijas likumā" — vajadzētu match
    bid1 = upsert_bill(path, "1315/Lp14", "Grozījumi Imigrācijas likumā", "Lp14")
    # Bill 2: title satur "Farmācijas likumā"
    bid2 = upsert_bill(path, "1098/Lp14", "Grozījumi Farmācijas likumā", "Lp14")
    # Bill 3: nav atbilstoša wiki/laws — paliks NULL
    bid3 = upsert_bill(path, "127/P14", "Paziņojums par dronu uzbrukumiem", "P14")
    db.close()
    yield path
    _safe_unlink(path)
```

- [ ] **Step 2: Failing test — backfill matches known law**

```python
def test_backfill_base_law_slug_matches_known_law(db_with_bills_for_backfill):
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    # Pre-condition: visiem base_law_slug=NULL
    db = get_db(db_with_bills_for_backfill)
    null_count = db.execute("SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NULL").fetchone()[0]
    db.close()
    assert null_count == 3

    result = backfill_base_law_slug(db_with_bills_for_backfill)

    db = get_db(db_with_bills_for_backfill)
    rows = {r["document_nr"]: r["base_law_slug"] for r in db.execute("SELECT document_nr, base_law_slug FROM saeima_bills").fetchall()}
    db.close()

    assert rows["1315/Lp14"] == "imigracijas-likums"
    assert rows["1098/Lp14"] == "farmacijas-likums"
    assert rows["127/P14"] is None  # nav match
    assert result["matched"] == 2
    assert result["unmatched"] == 1
```

Run → FAIL ar `ImportError`.

- [ ] **Step 3: Implementē `scripts/backfill_base_law_slug.py`**

```python
"""Phase 1B-ii Step 0 — populate saeima_bills.base_law_slug retroactively.

Iterē pār bills WHERE base_law_slug IS NULL, izsauc _resolve_base_law_slug
ar title + jaunākā saistītā vote motif konkatenāciju. Idempotents:
re-run = same final state, jo WHERE filter aizsargā jau matched bills.
"""

import argparse
import logging
import sys
from pathlib import Path

# Permit running as script: ensure parent dir on sys.path
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from src.db import get_db
from src.saeima import _resolve_base_law_slug

logger = logging.getLogger(__name__)


def backfill_base_law_slug(db_path: str = "data/atmina.db") -> dict:
    """Returns {'matched': N, 'unmatched': M, 'coverage_pct': P}."""
    db = get_db(db_path)
    rows = db.execute("""
        SELECT b.id, b.document_nr, b.title,
               (SELECT motif FROM saeima_votes WHERE bill_id=b.id ORDER BY id DESC LIMIT 1) AS motif
        FROM saeima_bills b
        WHERE b.base_law_slug IS NULL
        ORDER BY b.id
    """).fetchall()

    matched, unmatched = 0, 0
    for r in rows:
        match_text = f"{r['title']} {r['motif'] or ''}"
        slug = _resolve_base_law_slug(match_text)
        if slug:
            db.execute("UPDATE saeima_bills SET base_law_slug=? WHERE id=?", (slug, r["id"]))
            matched += 1
        else:
            unmatched += 1
    db.commit()
    db.close()

    total = matched + unmatched
    coverage_pct = (matched / total * 100) if total else 0.0
    result = {"matched": matched, "unmatched": unmatched, "coverage_pct": coverage_pct}

    logger.info("backfill_base_law_slug: %s", result)
    if coverage_pct < 30 and total > 0:
        logger.warning("Low coverage (%.1f%%); apsver Phase 1.5 manuālo pārklasifikāciju", coverage_pct)

    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    args = parser.parse_args()
    result = backfill_base_law_slug(args.db)
    print(f"Matched: {result['matched']}, Unmatched: {result['unmatched']}, Coverage: {result['coverage_pct']:.1f}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verificē PASS**

```bash
python -m pytest tests/test_phase_1b_ii.py::test_backfill_base_law_slug_matches_known_law -v
```

Sagaidāms: PASS.

- [ ] **Step 5: Failing test — idempotency**

```python
def test_backfill_base_law_slug_idempotent(db_with_bills_for_backfill):
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    result1 = backfill_base_law_slug(db_with_bills_for_backfill)
    result2 = backfill_base_law_slug(db_with_bills_for_backfill)

    # Pirmais matches 2; otrais nemainās (jau populēts → WHERE IS NULL filter izlaiž)
    assert result1["matched"] == 2
    assert result2["matched"] == 0  # nekas vairs nav NULL match-able
    assert result2["unmatched"] == 1  # 127/P14 paliek NULL
```

Run → PASS (idempotency comes naturally from the `WHERE IS NULL` filter).

- [ ] **Step 6: Run live backfill uz worktree DB**

```bash
python scripts/backfill_base_law_slug.py
```

Verificē output:
```
Matched: <N>, Unmatched: <M>, Coverage: <P>%
```

Pārbauda DB:
```bash
python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('base_law_slug populated:', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL').fetchone()[0])
print('NULL:', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NULL').fetchone()[0])
for r in db.execute('SELECT base_law_slug, COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL GROUP BY base_law_slug ORDER BY 2 DESC LIMIT 10').fetchall():
    print(' ', r[0], '=', r[1])
db.close()
"
```

Sagaidāms: matched ≥ 30% no 118 bills (apzīmējam laukus pēc tēmas). Top likumi: Aizsardzības finansēšanas, Imigrācijas, Farmācijas u.c.

- [ ] **Step 7: Commit**

```bash
git add scripts/backfill_base_law_slug.py tests/test_phase_1b_ii.py
git commit -m "$(cat <<'EOF'
feat(saeima): backfill_base_law_slug retro-script

Iterē pār saeima_bills WHERE base_law_slug IS NULL, izsauc
_resolve_base_law_slug ar title + jaunākā vote motif. Idempotents
(WHERE NULL filter). Phase 1B-ii Step 0 — atbloķē wiki/laws
auto-render plūsmu un detail page Saistītais bāzes likums bloks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `upsert_bill` integrācija ar `_resolve_base_law_slug`

**Files:**
- Modify: `src/saeima.py::upsert_bill`
- Test: `tests/test_phase_1b_ii.py`

- [ ] **Step 1: Read existing `upsert_bill` signature**

```bash
grep -n "def upsert_bill" src/saeima.py
```

Read the function — note the existing parameters and SQL.

- [ ] **Step 2: Failing test — new bill auto-resolves base_law_slug**

```python
def test_upsert_bill_resolves_base_law_slug_for_new_bill(tmp_path):
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)

    bid = upsert_bill(path, "9999/Lp14", "Grozījumi Imigrācijas likumā par sezonāliem darbiniekiem", "Lp14")

    db = get_db(path)
    slug = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid,)).fetchone()[0]
    db.close()
    _safe_unlink(path)

    assert slug == "imigracijas-likums"
```

Run → FAIL (current upsert_bill doesn't auto-resolve).

- [ ] **Step 3: Patch `upsert_bill`**

In `src/saeima.py`, find `upsert_bill` and add base_law_slug auto-resolution. The patch:

1. Add `_resolve_base_law_slug` import (already present in module — verify)
2. In the function body, after determining `title`, compute:
   ```python
   if base_law_slug is None and title:
       base_law_slug = _resolve_base_law_slug(title)
   ```
3. Pass it through to the INSERT/UPDATE SQL.

Keep idempotency: existing bills with non-NULL `base_law_slug` should not be overwritten on subsequent `upsert_bill` calls.

The exact patch shape depends on existing function structure. **Read the function before patching.**

- [ ] **Step 4: Run, PASS**

```bash
python -m pytest tests/test_phase_1b_ii.py::test_upsert_bill_resolves_base_law_slug_for_new_bill -v
```

- [ ] **Step 5: Failing test — preserves existing base_law_slug on re-call**

```python
def test_upsert_bill_preserves_existing_base_law_slug_on_re_call(tmp_path):
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)

    # Create bill with explicit base_law_slug
    bid1 = upsert_bill(path, "9999/Lp14", "Grozījumi Imigrācijas likumā", "Lp14")
    db = get_db(path)
    slug_after_first = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid1,)).fetchone()[0]
    assert slug_after_first == "imigracijas-likums"
    db.close()

    # Re-call with title that would resolve differently — must NOT overwrite
    bid2 = upsert_bill(path, "9999/Lp14", "Grozījumi Farmācijas likumā", "Lp14")
    assert bid2 == bid1  # idempotency: same id

    db = get_db(path)
    slug_after_second = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid1,)).fetchone()[0]
    db.close()
    _safe_unlink(path)

    # Should still be the first match (preserves existing)
    assert slug_after_second == "imigracijas-likums"
```

Run → either PASS (already idempotent on UPDATE) or FAIL (overwrites).

If FAIL, fix `upsert_bill` so the UPDATE branch doesn't touch `base_law_slug` if already populated. Pattern:
```sql
UPDATE saeima_bills SET title=?, ..., base_law_slug=COALESCE(base_law_slug, ?) WHERE document_nr=?
```

- [ ] **Step 6: Run all tests, no regressions**

```bash
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py tests/test_phase_1b_ii.py -q
```

- [ ] **Step 7: Commit**

```bash
git add src/saeima.py tests/test_phase_1b_ii.py
git commit -m "$(cat <<'EOF'
feat(saeima): upsert_bill auto-resolves base_law_slug

Jaunie bills no live aģenta plūsmas (Phase 1C) automātiski
iegūst base_law_slug bez manuāla re-run. Idempotents: esošos
bills ar populated base_law_slug nepārraksta (COALESCE).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: BILLS-SYNC-AUTO marķiera writeback

**Files:**
- Modify: `src/wiki.py` — pievieno `_render_law_bills_block` + integrē ar esošo `wiki_sync` flow
- Test: `tests/test_phase_1b_ii.py`

- [ ] **Step 1: Read existing wiki.py SYNC-AUTO pattern**

```bash
grep -n "SYNC-AUTO\|_SYNC_START\|_SYNC_END\|wiki_sync" src/wiki.py | head -20
```

Read around the `_SYNC_START`/`_SYNC_END` constants (line ~99) to understand the marker handling pattern. Note any helper functions for marker replacement.

- [ ] **Step 2: Failing test — render with bills**

```python
def test_render_law_bills_block_with_bills(tmp_path, db_with_bills_for_backfill):
    """Likumam ar bills atbilstošu base_law_slug → marker bloks ar tabulas rindām."""
    from src.wiki import _render_law_bills_block

    # Backfill so bills get base_law_slug populated
    from scripts.backfill_base_law_slug import backfill_base_law_slug
    backfill_base_law_slug(db_with_bills_for_backfill)

    # Create a wiki/laws/imigracijas-likums.md fixture
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    md_path = laws_dir / "imigracijas-likums.md"
    md_path.write_text("# Imigrācijas likums\n\nApraksts.\n", encoding="utf-8")

    db = get_db(db_with_bills_for_backfill)
    _render_law_bills_block(slug="imigracijas-likums", db=db, md_path=md_path)
    db.close()

    content = md_path.read_text(encoding="utf-8")
    assert "<!-- BILLS-SYNC-AUTO -->" in content
    assert "<!-- /BILLS-SYNC-AUTO -->" in content
    assert "Aktuālie likumprojekti šajā likumā" in content
    assert "1315/Lp14" in content  # bill from fixture
    assert "Grozījumi Imigrācijas likumā" in content
```

Run → FAIL (function doesn't exist).

- [ ] **Step 3: Implementē `_render_law_bills_block`**

In `src/wiki.py`, add:

```python
_BILLS_SYNC_START = "<!-- BILLS-SYNC-AUTO -->"
_BILLS_SYNC_END = "<!-- /BILLS-SYNC-AUTO -->"


def _render_law_bills_block(slug: str, db: sqlite3.Connection, md_path: Path) -> bool:
    """Atjauno BILLS-SYNC-AUTO bloku wiki/laws/<slug>.md failā.
    
    Returns True ja saturs faktiski mainījies (ja False, fails nav skarts → idempotents).
    """
    rows = db.execute("""
        SELECT document_nr, title, current_stage, current_status, last_updated_at
        FROM saeima_bills
        WHERE base_law_slug = ?
        ORDER BY last_updated_at DESC, id DESC
    """, (slug,)).fetchall()

    if rows:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "| Bill nr | Nosaukums | Stadija | Datums |",
            "|---|---|---|---|",
        ]
        for r in rows:
            doc_slug = r["document_nr"].lower().replace("/", "-")
            stage_with_status = f"{r['current_stage']}"
            if r["current_status"]:
                stage_with_status += f" ({r['current_status']})"
            date = (r["last_updated_at"] or "")[:10]
            lines.append(f"| [{r['document_nr']}](/likumprojekti/{doc_slug}.html) | {r['title']} | {stage_with_status} | {date} |")
        lines.append(_BILLS_SYNC_END)
    else:
        lines = [
            _BILLS_SYNC_START,
            "## Aktuālie likumprojekti šajā likumā",
            "",
            "_Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā._",
            _BILLS_SYNC_END,
        ]
    new_block = "\n".join(lines)

    if not md_path.exists():
        return False  # Nav fails — neko nedara

    content = md_path.read_text(encoding="utf-8")

    if _BILLS_SYNC_START in content and _BILLS_SYNC_END in content:
        # Replace existing block
        before, _, rest = content.partition(_BILLS_SYNC_START)
        _, _, after = rest.partition(_BILLS_SYNC_END)
        new_content = before + new_block + after
    else:
        # Append at end (with newline separation)
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    if new_content == content:
        return False  # Idempotents: nav bytewise izmaiņu

    md_path.write_text(new_content, encoding="utf-8")
    return True
```

- [ ] **Step 4: Run, PASS**

```bash
python -m pytest tests/test_phase_1b_ii.py::test_render_law_bills_block_with_bills -v
```

- [ ] **Step 5: Failing test — empty state**

```python
def test_render_law_bills_block_empty_state(tmp_path, db_with_bills_for_backfill):
    """Likumam BEZ saistītu bills → marker bloks ar 'nav aktīvu' tekstu."""
    from src.wiki import _render_law_bills_block

    md_path = tmp_path / "buvniecibas-likums.md"
    md_path.write_text("# Būvniecības likums\n", encoding="utf-8")

    db = get_db(db_with_bills_for_backfill)
    _render_law_bills_block(slug="buvniecibas-likums", db=db, md_path=md_path)
    db.close()

    content = md_path.read_text(encoding="utf-8")
    assert "nav aktīvu likumprojektu Saeimā" in content
    assert "<!-- BILLS-SYNC-AUTO -->" in content
```

Run → PASS.

- [ ] **Step 6: Failing test — idempotent**

```python
def test_render_law_bills_block_idempotent(tmp_path, db_with_bills_for_backfill):
    """Re-call ar tādu pašu state nemaina failu (returns False)."""
    from src.wiki import _render_law_bills_block
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill)
    md_path = tmp_path / "imigracijas-likums.md"
    md_path.write_text("# Imigrācijas likums\n\nApraksts.\n", encoding="utf-8")

    db = get_db(db_with_bills_for_backfill)
    changed_first = _render_law_bills_block("imigracijas-likums", db, md_path)
    content_after_first = md_path.read_text(encoding="utf-8")
    changed_second = _render_law_bills_block("imigracijas-likums", db, md_path)
    content_after_second = md_path.read_text(encoding="utf-8")
    db.close()

    assert changed_first is True
    assert changed_second is False
    assert content_after_first == content_after_second
```

Run → PASS.

- [ ] **Step 7: Failing test — appends when marker missing**

```python
def test_render_law_bills_block_appends_when_marker_missing(tmp_path):
    """Fails bez BILLS-SYNC-AUTO marķiera → bloks pievieno faila beigās."""
    from src.wiki import _render_law_bills_block

    md_path = tmp_path / "test-likums.md"
    md_path.write_text("# Test likums\n\nDaži apraksti.\n", encoding="utf-8")

    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)

    _render_law_bills_block("test-likums", db, md_path)
    db.close()
    _safe_unlink(db_path)

    content = md_path.read_text(encoding="utf-8")
    assert "Daži apraksti." in content  # Esošais saturs paliek
    assert "<!-- BILLS-SYNC-AUTO -->" in content  # Marķieris pievienots
    assert content.index("Daži apraksti.") < content.index("<!-- BILLS-SYNC-AUTO -->")  # Pareizais order
```

Run → PASS.

- [ ] **Step 8: Integrē ar esošo `wiki_sync` flow**

Find `wiki_sync()` function in `src/wiki.py` (around line 954). Read it to understand the flow. Pievieno jaunu sub-step pirms vai pēc esošajām politiķu synthesis darbībām:

```python
# Phase 1B-ii — render BILLS-SYNC-AUTO blocks in wiki/laws/<slug>.md
laws_dir = Path("wiki") / "laws"
if laws_dir.exists():
    for md_file in laws_dir.glob("*.md"):
        if md_file.name == "likumi.md":
            continue  # Skip indekss
        slug = md_file.stem
        if _render_law_bills_block(slug, db, md_file):
            logger.info("wiki_sync: updated BILLS-SYNC-AUTO in %s", md_file.name)
```

- [ ] **Step 9: Manuālā wiki sync palaišana**

```bash
python -c "
from src.db import get_db
from src.wiki import wiki_sync
db = get_db('data/atmina.db')
wiki_sync(db)
db.close()
"
```

Verificē, ka 33 wiki/laws/<slug>.md failu ir atjaunoti:
```bash
grep -l "BILLS-SYNC-AUTO" wiki/laws/*.md | wc -l
```

Sagaidāms: ~30+ failu (visi izņemot `likumi.md` un, iespējams, daži, kuriem `wiki_sync` neatjaunina dēļ specifiskām kļūdām — uzpildīt logos).

- [ ] **Step 10: Commit**

```bash
git add src/wiki.py tests/test_phase_1b_ii.py wiki/laws/
git commit -m "$(cat <<'EOF'
feat(wiki): _render_law_bills_block + BILLS-SYNC-AUTO marķieris

Atjauno wiki/laws/<slug>.md failos BILLS-SYNC-AUTO bloku ar
tabulu (kad ir bills) vai empty state. Idempotents bytewise.
wiki_sync() iter pār 33 wiki/laws failiem un atjaunina.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `templates/likums.html.j2` + `_fetch_law_pages` + `_generate_law_pages`

**Files:**
- Create: `templates/likums.html.j2`
- Modify: `src/generate.py` — add `_fetch_law_pages`, `_generate_law_pages`, integrate in `generate_public_site`
- Test: `tests/test_phase_1b_ii.py`

- [ ] **Step 1: Failing test — `_fetch_law_pages` shape**

```python
def test_fetch_law_pages_shape(tmp_path):
    """_fetch_law_pages atgriež struktūru ar slug, title, body_html, likumi_lv_url, bills."""
    from src.generate import _fetch_law_pages

    # Setup: jauns wiki/laws fixture
    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "test-likums.md").write_text(
        "# Test likums\n\n"
        "**Pieņemts:** 2020-01-01\n"
        "**Likumi.lv:** https://likumi.lv/ta/id/12345-test-likums\n\n"
        "## Mērķis\n\nTestēšanas mērķim.\n",
        encoding="utf-8"
    )

    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)

    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    db.close()
    _safe_unlink(db_path)

    assert len(pages) == 1
    p = pages[0]
    assert p["slug"] == "test-likums"
    assert p["title"] == "Test likums"
    assert p["likumi_lv_url"] == "https://likumi.lv/ta/id/12345-test-likums"
    assert "Testēšanas mērķim" in p["body_html"]  # Markdown → HTML
    assert p["bills_count"] == 0
```

Run → FAIL.

- [ ] **Step 2: Implementē `_fetch_law_pages`**

In `src/generate.py`:

```python
import re as _re

_LAW_TITLE_RE = _re.compile(r"^#\s+(.+?)\s*$", _re.MULTILINE)
_LAW_LIKUMI_LV_RE = _re.compile(r"^\*\*Likumi\.lv:\*\*\s+(\S+)\s*$", _re.MULTILINE)


def _fetch_law_pages(db: sqlite3.Connection, laws_dir: Path = Path("wiki/laws")) -> list[dict[str, Any]]:
    """Iterē wiki/laws/*.md (skip likumi.md), parse, render markdown → HTML.
    
    Returns list ar slug, title, likumi_lv_url, body_html, bills_count, bills (linki + nr).
    """
    if not laws_dir.exists():
        return []

    pages = []
    for md_file in sorted(laws_dir.glob("*.md")):
        if md_file.name == "likumi.md":
            continue
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")

        title_m = _LAW_TITLE_RE.search(content)
        title = title_m.group(1) if title_m else slug.replace("-", " ").title()

        url_m = _LAW_LIKUMI_LV_RE.search(content)
        likumi_lv_url = url_m.group(1) if url_m else None

        # Markdown → HTML, sanitize
        body_html = _sanitize_html(markdown.markdown(content, extensions=["tables"]))

        # Bills count + summary
        bills = []
        for r in db.execute("""
            SELECT id, document_nr, title, current_stage, current_status, last_updated_at
            FROM saeima_bills
            WHERE base_law_slug = ?
            ORDER BY last_updated_at DESC
        """, (slug,)).fetchall():
            bills.append({
                "id": r["id"],
                "document_nr": r["document_nr"],
                "slug": _bill_slug(r["document_nr"]),
                "title": r["title"],
                "current_stage": r["current_stage"],
                "current_status": r["current_status"],
                "last_updated_at": r["last_updated_at"],
            })

        pages.append({
            "slug": slug,
            "title": title,
            "likumi_lv_url": likumi_lv_url,
            "body_html": body_html,
            "bills_count": len(bills),
            "bills": bills,
        })

    return pages
```

- [ ] **Step 3: Run, PASS**

```bash
python -m pytest tests/test_phase_1b_ii.py::test_fetch_law_pages_shape -v
```

- [ ] **Step 4: Failing test — likums template renderē**

```python
def test_likums_template_renders(tmp_path, db_with_bills_for_backfill):
    """Likuma lapa renderē ar pagehead + body + bills count."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_law_pages, _safe_url_filter
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill)

    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "imigracijas-likums.md").write_text(
        "# Imigrācijas likums\n\n"
        "**Likumi.lv:** https://likumi.lv/ta/id/68522\n\n"
        "## Mērķis\n\nLikuma apraksts.\n",
        encoding="utf-8"
    )

    db = get_db(db_with_bills_for_backfill)
    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    db.close()
    law = pages[0]

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    template = env.get_template("likums.html.j2")
    html = template.render(law=law)

    assert "Imigrācijas likums" in html
    assert "likumi.lv" in html
    assert 'href="https://likumi.lv/ta/id/68522"' in html
    assert "Likuma apraksts" in html
    assert 'class="pagehead-section"' in html
```

Run → FAIL ar `TemplateNotFound`.

- [ ] **Step 5: Izveido `templates/likums.html.j2`**

```jinja
{% extends "base.html.j2" %}
{% set active_page = "" %}
{% set assets_prefix = "../" %}

{% block title %}{{ law.title }}{% endblock %}

{% block content %}
<section class="pagehead-section">
  <header class="pagehead-header">
    <div class="pagehead-header-title">
      <div class="pagehead-kicker">Likums</div>
      <h1 class="pagehead-h1">{{ law.title }}</h1>
    </div>
    <div class="pagehead-metrics">
      {% if law.likumi_lv_url %}
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Avots</span>
        <a href="{{ law.likumi_lv_url | safe_url }}" target="_blank" rel="noopener" class="pagehead-metric-value">likumi.lv ↗</a>
      </div>
      {% endif %}
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Likumprojekti</span>
        <span class="pagehead-metric-value">{{ law.bills_count }}</span>
      </div>
    </div>
  </header>
</section>

<div class="law-content post-content">
  {{ law.body_html | safe }}
</div>
{% endblock %}
```

- [ ] **Step 6: Run, PASS**

- [ ] **Step 7: Failing test — `_generate_law_pages` writes files**

```python
def test_generate_law_pages_emits_files(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_law_pages, _safe_url_filter

    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "test1.md").write_text("# Test 1\n\nA.\n", encoding="utf-8")
    (laws_dir / "test2.md").write_text("# Test 2\n\nB.\n", encoding="utf-8")
    (laws_dir / "likumi.md").write_text("# Indekss\n", encoding="utf-8")  # SKIP

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter

    db = get_db(db_with_bills_for_backfill)
    count = _generate_law_pages(db, env, output_dir, laws_dir=laws_dir)
    db.close()

    assert count == 2  # Skipped likumi.md
    assert (output_dir / "likumi" / "test1.html").exists()
    assert (output_dir / "likumi" / "test2.html").exists()
    assert not (output_dir / "likumi" / "likumi.html").exists()
```

Run → FAIL.

- [ ] **Step 8: Implementē `_generate_law_pages`**

```python
def _generate_law_pages(db: sqlite3.Connection, env, output_dir: Path, laws_dir: Path = Path("wiki/laws")) -> int:
    """Renderē /likumi/<slug>.html katram wiki/laws/<slug>.md (izņemot likumi.md)."""
    out_laws = output_dir / "likumi"
    out_laws.mkdir(parents=True, exist_ok=True)
    template = env.get_template("likums.html.j2")
    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    count = 0
    for law in pages:
        html = template.render(law=law)
        target = out_laws / f"{law['slug']}.html"
        target.write_text(html, encoding="utf-8")
        count += 1
    logger.info("_generate_law_pages: wrote %d law pages to %s", count, out_laws)
    return count
```

- [ ] **Step 9: Run, PASS**

- [ ] **Step 10: Hook in `generate_public_site`**

In `generate_public_site`, add the call **PIRMS** `_generate_bill_pages` (so detail page back-links resolve to existing files):

```python
# Phase 1B-ii — Law pages from wiki/laws/
law_count = _generate_law_pages(db, env, atmina_dir)
```

- [ ] **Step 11: Manuālā smoke**

```bash
python -m src.generate 2>&1 | tail -20
```

```bash
ls output/atmina/likumi/ | wc -l
```

Sagaidāms: 33 failu (skip likumi.md indeksu, kas ir 34. fails).

- [ ] **Step 12: Commit**

```bash
git add src/generate.py templates/likums.html.j2 tests/test_phase_1b_ii.py
git commit -m "$(cat <<'EOF'
feat(generate): _fetch_law_pages + _generate_law_pages + likums template

Renderē 33 jaunas /likumi/<slug>.html lapas no wiki/laws/<slug>.md.
Markdown → HTML caur esošo bleach sanitize. Pagehead ar likumi.lv
linka un bills count metric. Hook'ots pirms _generate_bill_pages,
lai detail page Saistītais bāzes likums linki rezolvē.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Detail page "Saistītais bāzes likums" bloks

**Files:**
- Modify: `src/generate.py::_fetch_bill_detail` — pievieno `base_law_slug`, `base_law_title`
- Modify: `templates/likumprojekts.html.j2` — pievieno conditional sekciju
- Test: `tests/test_phase_1b_ii.py`

- [ ] **Step 1: Failing test — fetch_bill_detail returns base_law fields**

```python
def test_fetch_bill_detail_returns_base_law_fields(tmp_path, db_with_bills_for_backfill):
    """_fetch_bill_detail iekļauj base_law_slug + base_law_title."""
    from src.generate import _fetch_bills, _fetch_bill_detail
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill)

    db = get_db(db_with_bills_for_backfill)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    detail = _fetch_bill_detail(db, bid)
    db.close()

    assert detail["base_law_slug"] == "imigracijas-likums"
    # base_law_title nāk no wiki/laws/<slug>.md H1 (vai fallback uz slug formatētu)
    assert detail["base_law_title"]  # Jebkurā formātā non-empty
```

Run → FAIL (currently `_fetch_bill_detail` doesn't include these fields).

- [ ] **Step 2: Implementē `_load_law_titles_cache` helper**

In `src/generate.py`, add module-level cache:

```python
_LAW_TITLES_CACHE: Optional[dict[str, str]] = None


def _load_law_titles_cache(laws_dir: Path = Path("wiki/laws")) -> dict[str, str]:
    """Cache slug → title no wiki/laws/<slug>.md H1. Lazy single read."""
    global _LAW_TITLES_CACHE
    if _LAW_TITLES_CACHE is not None:
        return _LAW_TITLES_CACHE
    cache: dict[str, str] = {}
    if laws_dir.exists():
        for md_file in laws_dir.glob("*.md"):
            if md_file.name == "likumi.md":
                continue
            content = md_file.read_text(encoding="utf-8")
            m = _LAW_TITLE_RE.search(content)
            if m:
                cache[md_file.stem] = m.group(1)
    _LAW_TITLES_CACHE = cache
    return cache
```

- [ ] **Step 3: Patch `_fetch_bill_detail`**

In `_fetch_bill_detail`, after fetching the bill row, add:

```python
# Phase 1B-ii base_law fields
base_law_slug = bill_row["base_law_slug"] if "base_law_slug" in bill_row.keys() else None
base_law_title = None
if base_law_slug:
    titles = _load_law_titles_cache()
    base_law_title = titles.get(base_law_slug, base_law_slug.replace("-", " ").title())

return {
    ...,
    "base_law_slug": base_law_slug,
    "base_law_title": base_law_title,
}
```

(The exact integration depends on existing dict-build pattern.)

Also: the SELECT query for bill_row may need to include `base_law_slug`. Verify by reading the existing function and add it to the SELECT if missing.

- [ ] **Step 4: Run, PASS**

- [ ] **Step 5: Failing test — template renders block when base_law set**

```python
def test_likumprojekts_template_renders_base_law_section(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill)

    db = get_db(db_with_bills_for_backfill)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "1315/Lp14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Saistītais bāzes likums" in html
    assert 'href="../likumi/imigracijas-likums.html"' in html


def test_likumprojekts_template_no_base_law_when_null(db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills_for_backfill)
    # Bill 127/P14 nemēģina match, paliek NULL
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "127/P14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Saistītais bāzes likums" not in html
```

Run → both FAIL (template doesn't render the section yet).

- [ ] **Step 6: Patch `templates/likumprojekts.html.j2`**

Find the [Saites] section. Pievieno PIRMS tās (vai aiz [Iesniedzēji]):

```jinja
{% if bill.base_law_slug %}
<section class="bill-detail-base-law">
  <h2>Saistītais bāzes likums</h2>
  <p>Šis likumprojekts groza: <a href="../likumi/{{ bill.base_law_slug }}.html">{{ bill.base_law_title or bill.base_law_slug }}</a></p>
</section>
{% endif %}
```

- [ ] **Step 7: Run, both PASS**

- [ ] **Step 8: Smoke**

```bash
python -m src.generate
grep -l "Saistītais bāzes likums" output/atmina/likumprojekti/*.html | wc -l
```

Sagaidāms: ≥30 (visi bills, kuriem `base_law_slug` populated).

- [ ] **Step 9: Commit**

```bash
git add src/generate.py templates/likumprojekts.html.j2 tests/test_phase_1b_ii.py
git commit -m "$(cat <<'EOF'
feat(templates): detail page Saistītais bāzes likums bloks

_fetch_bill_detail papildināts ar base_law_slug + base_law_title
(no wiki/laws/<slug>.md H1 cached parse). Template conditional
render — tikai kad base_law_slug populēts. Linka uz
../likumi/<slug>.html.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Politiķa profila Likumprojekti sekcija (conditional)

**Files:**
- Modify: `src/generate.py::_fetch_politician_detail` — pievieno `bills_involved`
- Modify: `templates/politician.html.j2` — pievieno sekciju + profile-stat butonu (conditional)
- Test: `tests/test_phase_1b_ii.py`

- [ ] **Step 1: Failing test — empty junction, no section**

```python
def test_politician_profile_no_likumprojekti_section_when_empty(tmp_path, db_with_bills_for_backfill):
    """Junction empty for politiķa → sekcija + butons absent no DOM."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_politician_detail, _safe_url_filter

    # Setup: politiķis bez junction rindām
    db = get_db(db_with_bills_for_backfill)
    db.execute("INSERT INTO tracked_politicians (name, party) VALUES (?, ?)", ("Ieva Tests", "JV"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name='Ieva Tests'").fetchone()["id"]
    db.commit()

    detail = _fetch_politician_detail(db, pid)
    db.close()
    assert detail["bills_involved"] == []

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("politician.html.j2")
    # Render with minimal context
    html = template.render(
        politician={"id": pid, "name": "Ieva Tests", "slug": "ieva-tests", "party": "JV", "x_handle": None, "role": None},
        bills_involved=detail["bills_involved"],
        timeline=[], positions=[], contradictions=[], votes=[], tensions=[],
        x_posts=[], news=[], commentary_about=[], external_profiles=[], syntheses=[],
        wiki_profile=None, has_photo=False, party_meta=None,
    )
    assert 'id="profile-bills-section"' not in html
    assert 'data-tab="likumprojekti"' not in html
```

Run → FAIL (probably ImportError or rendering error if `bills_involved` not yet handled).

- [ ] **Step 2: Patch `_fetch_politician_detail`**

In `src/generate.py`, find `_fetch_politician_detail`. Add `bills_involved` query:

```python
bills_involved = []
for r in db.execute("""
    SELECT DISTINCT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
           b.current_stage, b.current_status, b.last_updated_at, b.first_seen_at,
           b.institutional_submitter,
           (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
           (SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=b.id) AS stage_count,
           (SELECT COUNT(*) FROM saeima_votes WHERE bill_id=b.id) AS vote_count
    FROM saeima_bills b
    JOIN saeima_bill_politicians bp ON bp.bill_id = b.id
    WHERE bp.politician_id = ?
    ORDER BY b.last_updated_at DESC
""", (pid,)).fetchall():
    bills_involved.append({
        **dict(r),
        "slug": _bill_slug(r["document_nr"]),
    })
```

Add `bills_involved` to the returned dict.

- [ ] **Step 3: Patch `templates/politician.html.j2` — add section**

After the existing sections (e.g., after `<section id="profile-zinas-section">` or wherever the last conditional section ends), add:

```jinja
{% if bills_involved %}
<section id="profile-bills-section" style="margin-top: 1.5rem;">
  <h2>Likumprojekti ({{ bills_involved|length }})</h2>
  <div class="bill-card-grid">
    {% from "_bill_card.html.j2" import bill_card %}
    {% for b in bills_involved %}{{ bill_card(b) }}{% endfor %}
  </div>
</section>
{% endif %}
```

Also add a profile-stat button in the existing profile-stats-bar (around line 73 in the template):

```jinja
{% if bills_involved %}
<button class="profile-stat" onclick="showProfileTab('likumprojekti', this)" data-tab="likumprojekti">
  <span class="profile-stat-value">{{ bills_involved|length }}</span>
  <span class="profile-stat-label">Likumprojekti</span>
</button>
{% endif %}
```

- [ ] **Step 4: Run, empty case PASS**

```bash
python -m pytest tests/test_phase_1b_ii.py::test_politician_profile_no_likumprojekti_section_when_empty -v
```

- [ ] **Step 5: Failing test — junction populated, section appears**

```python
def test_politician_profile_likumprojekti_section_when_data_present(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_politician_detail, _safe_url_filter

    db = get_db(db_with_bills_for_backfill)
    # Pievieno politiķi un junction rindu
    db.execute("INSERT INTO tracked_politicians (name, party) VALUES (?, ?)", ("Maija Armaņeva", "Progresīvie"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name=?", ("Maija Armaņeva",)).fetchone()["id"]
    bid = db.execute("SELECT id FROM saeima_bills WHERE document_nr='1315/Lp14'").fetchone()["id"]
    db.execute("INSERT INTO saeima_bill_politicians (bill_id, politician_id, role) VALUES (?, ?, 'submitter')", (bid, pid))
    db.commit()

    detail = _fetch_politician_detail(db, pid)
    db.close()
    assert len(detail["bills_involved"]) == 1
    assert detail["bills_involved"][0]["document_nr"] == "1315/Lp14"

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("politician.html.j2")
    html = template.render(
        politician={"id": pid, "name": "Maija Armaņeva", "slug": "maija-armaneva", "party": "Progresīvie", "x_handle": None, "role": None},
        bills_involved=detail["bills_involved"],
        timeline=[], positions=[], contradictions=[], votes=[], tensions=[],
        x_posts=[], news=[], commentary_about=[], external_profiles=[], syntheses=[],
        wiki_profile=None, has_photo=False, party_meta=None,
    )
    assert 'id="profile-bills-section"' in html
    assert 'data-tab="likumprojekti"' in html
    assert "1315/Lp14" in html
```

Run → PASS.

- [ ] **Step 6: Run all tests, no regressions**

```bash
python -m pytest tests/test_phase_1b_ii.py tests/test_generate_bills.py tests/test_generate.py -q
```

- [ ] **Step 7: Commit**

```bash
git add src/generate.py templates/politician.html.j2 tests/test_phase_1b_ii.py
git commit -m "$(cat <<'EOF'
feat(templates): politiķa profila Likumprojekti sekcija (conditional)

_fetch_politician_detail papildināts ar bills_involved JOIN no
saeima_bill_politicians junction. Politician.html sekcija +
profile-stat butons render TIKAI ja junction populēta priekš šī
politiķa. Šobrīd nevienam politiķim sekcija nav redzama (junction
tukša); 1C lights up automātiski, kad live aģents to populē.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: wiki naming fix

**Files:**
- Modify: kods, kas ģenerē `wiki/laws/likumi.md` un `wiki/index.md`

- [ ] **Step 1: Atrod likumi.md ģeneratoru**

```bash
grep -rn "Likumprojekti — Indekss\|likumprojekti\.md\|laws/likumi" src/ | head -10
```

Identificē kods, kas raksta:
- H1: "Likumprojekti — Indekss"
- Description: "**N** likumprojekti"

Visticamāk `src/wiki.py` vai `src/wiki_lint.py`. Atrod precīzi.

- [ ] **Step 2: Patch — likumi.md generator**

Aizvieto:
- "Likumprojekti — Indekss" → "Likumi — Indekss"
- "likumprojekti" → "likumi" (description tekstā)

Note: tabulas heading "Likums | Saistītie balsojumi" paliek.

- [ ] **Step 3: Atrod un labo wiki/index.md ģeneratoru**

```bash
grep -rn "Likumprojekti.*likumprojekti\|laws/likumi.*Likumprojekti" src/ | head -5
```

Identificē, kur tiek ģenerēts wiki/index.md rinda par likumiem. Aizvieto:
- "Likumprojekti" display → "Likumi"
- Skaitlis 34 → 33 (jo likumi.md indeksu paši nav likums)

- [ ] **Step 4: Re-run wiki sync**

```bash
python -c "
from src.db import get_db
from src.wiki import wiki_sync
db = get_db('data/atmina.db')
wiki_sync(db)
db.close()
"
```

- [ ] **Step 5: Verificē output**

```bash
head -10 wiki/laws/likumi.md
grep -A 2 "laws/likumi" wiki/index.md
```

Sagaidāms:
- `wiki/laws/likumi.md` rāda "# Likumi — Indekss" un "**33** likumi"
- `wiki/index.md` rāda "[[laws/likumi|Likumi]] — 33 likumi"

- [ ] **Step 6: Commit**

```bash
git add src/wiki.py wiki/laws/likumi.md wiki/index.md
git commit -m "$(cat <<'EOF'
fix(wiki): naming "Likumprojekti" → "Likumi" indeksā

wiki/laws/likumi.md un wiki/index.md saturēja semantiski nepareizu
"Likumprojekti — Indekss" lai gan saturā ir likumi (Imigrācijas,
Farmācijas u.c.). Atjauno generators + regen 33 likumiem
(nevis 34 kā iepriekš, kas iekļāva indeksa failu pašu).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: CHANGELOG + final smoke + commit

**Files:**
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Pievieno CHANGELOG ierakstu**

`wiki/CHANGELOG.md` augšā (zem H1):

```markdown
## 2026-04-27 — Saeima Bills Phase 1B-ii: wiki/laws + base_law_slug + politiķa profila sekcija

**Iemesls:** Phase 1B-i (commit `42b2375`) atvēra bills datus publikai (118 detail lapas + balsojumi 3. subtab + cross-link). 1B-ii sasaista bills ar wiki/laws — populē `base_law_slug`, raksta BILLS-SYNC-AUTO blokus, renderē 33 jaunas `/likumi/<slug>.html` lapas, pievieno detail lapā "Saistītais bāzes likums" linka, un sagatavo politiķa profila Likumprojekti sekciju conditional.

**Izmaiņas:**

- **`base_law_slug` retro-backfill**: `scripts/backfill_base_law_slug.py` — populē šo nullable kolonnu visiem 118 esošajiem bills. Match teritorija: title + jaunākā saistītā vote motif. `upsert_bill()` integrācija — jaunie bills no live aģenta plūsmas (Phase 1C) automātiski iegūst `base_law_slug`.
- **wiki/laws auto-render**: `src/wiki.py::_render_law_bills_block` raksta `<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->` blokus 33 wiki/laws/<slug>.md failos ar tabulu vai empty state. `wiki_sync()` flow integrēts. Idempotents bytewise.
- **Jaunas publiskas lapas**: `/likumi/<slug>.html` (33 failu) — markdown render no `wiki/laws/<slug>.md` ar likumi.lv linka, bills count metric, full body.
- **Detail page papildinājums**: "Saistītais bāzes likums" sekcija conditional render — parādās bills, kuriem `base_law_slug` populēts, ar linka uz attiecīgā likuma lapu.
- **Politiķa profila sekcija**: "Likumprojekti" sekcija + profile-stat butons render TIKAI ja `saeima_bill_politicians` junction populēta priekš šī politiķa. Šobrīd nevienam politiķim sekcija nav redzama (junction tukša pēc Phase 1A); 1C lights up automātiski, kad live aģents to populē.
- **Naming fix**: `wiki/laws/likumi.md` un `wiki/index.md` semantiski pareizi ("Likumi", ne "Likumprojekti"). 33 likumi (ne 34, jo indeksa fails pats nav likums).

**Atstāts 1C-am:**
- `.claude/agents/saeima-tracker.md` aģenta prompt update (steps 2/3/5.5)
- Pozīciju auto-link regex `NNNN/Lp14` summary tekstā
- `wiki/operations/saeima-bills.md` runbook
- CLAUDE.md Pipeline Invariant 12

**Datu deltas:**
- `saeima_bills.base_law_slug` populated: 0 → ≥30% no 118 (precīzs skaits atklāts backfill report'ā)
- Junction `saeima_bill_politicians`: paliek tukša līdz 1C live aģents to populē
- Jaunas HTML lapas: `output/atmina/likumi/*.html` × 33
```

- [ ] **Step 2: Run pilna testu suite**

```bash
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py tests/test_generate_bills.py tests/test_generate.py tests/test_phase_1b_ii.py -q
```

Sagaidāms: 162+ jauni testi (no Phase 1B-ii) PASS, 0 regressions.

- [ ] **Step 3: Pilna ģenerācija**

```bash
python -m src.generate 2>&1 | tail -10
```

Sagaidāms: 0 errors. Verificē:

```bash
ls output/atmina/likumi/ | wc -l
ls output/atmina/likumprojekti/ | wc -l
grep -c 'Saistītais bāzes likums' output/atmina/likumprojekti/*.html | grep -v ':0$' | wc -l
```

- 33 likumi
- 118+ likumprojekti
- ≥30 bills ar bāzes likums sekciju (proporcija atkarīga no backfill coverage)

- [ ] **Step 4: Manuāla acu pārbaude**

```bash
python serve.py
```

Atver browser un pārbauda:
- `/likumi/imigracijas-likums.html` rāda title + body + bills (ja saistīti)
- `/likumprojekti/<slug>.html` ar populated `base_law_slug` rāda "Saistītais bāzes likums" sekciju ar working linka
- Klikšķis no detail page uz law page strādā un atpakaļ
- `wiki/laws/likumi.md` rāda "Likumi" (ne "Likumprojekti") title
- Politiķa profile lapa ar tukšu junction NErāda Likumprojekti sekciju (nav DOM)

- [ ] **Step 5: Cleanup data/atmina.db worktree (gitignored, drošs)**

`data/atmina.db` worktree mapē tiek atstāts vai noņemts pirms commit (nav gitignored, bet šis ir transports). Verificē, ka NAV pievienots:

```bash
git status --short
```

Sagaidāms: tikai `wiki/CHANGELOG.md` modificēts.

- [ ] **Step 6: Commit CHANGELOG**

```bash
git add wiki/CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(changelog): Phase 1B-ii — wiki/laws + base_law_slug + profile section

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Verificē branch state**

```bash
git log --oneline master..HEAD | wc -l
git log --oneline master..HEAD
git diff --stat master..HEAD
```

Sagaidāms: ~9 commits uz branch'a (Tasks 0-8). Diff stat rāda visu darba apjomu.

---

## Self-Review Checklist

After all 9 tasks done, agentic worker apstiprina:

- [ ] Visi spec § 2.1 elementi ir ietverti vienā no Task 0-8
- [ ] Visi spec § 10 testi ir uzrakstīti
- [ ] Spec § 12 akceptances kritēriji izpildīti
- [ ] Phase 1B-i 162 esošie testi joprojām PASS (regression check)
- [ ] `python -m src.generate` 0 errors; 33 likumi + 118+ likumprojekti
- [ ] Manuāla pārbaude pa serve.py izpildīta

## Atkarības starp tasks

```
Task 0 (worktree) ─→ Task 1 (backfill) ─→ Task 2 (upsert_bill integ.)
                          ↓                       ↓
                          └──→ Task 3 (BILLS-SYNC-AUTO) ─→ Task 4 (likums template + generate)
                                                                  ↓
                                                                  └──→ Task 5 (detail bāzes likums bloks)
                                                                  
                                                                  Task 6 (politiķa sekcija) — neatkarīgs
                                                                  Task 7 (naming fix) — neatkarīgs
                                                                  
                                                                  Task 8 (CHANGELOG + smoke)
```

Tasks 6 un 7 var iet paralēli ar Task 4-5. Task 8 ir final.
