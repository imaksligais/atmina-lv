# Tendences → Konteksts formatēšana + datu higiēna — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Padarīt `analizes.html` Tendences→Konteksts sadaļu lasāmu un skaistu (desktop+mobile, bez gļukiem), un izbeigt JSON audit-rindu noplūdi publiskajā UI ar saknes labojumu.

**Architecture:** (1) Jauns helper `_clean_context_note()` `_common.py` — strip kailos claim-ID + render markdown → sanitized HTML. (2) `_fetch_context_notes()` filtrē tikai `note_type='context'` ne-JSON rindas un pievieno `content_html`. (3) Template + CSS — editoriāls chip, `align-items:start` grid, responsīvs. (4) Datu higiēna — jauns `note_type='asset'` audit-rindām (4 skripti + backfill). (5) Dual-viewport Playwright verifikācija.

**Tech Stack:** Python 3.12, sqlite3, `markdown` + `bleach` (esošie `_common._sanitize_html`), Jinja2, CSS, Playwright (verifikācija).

**Spec:** `docs/superpowers/specs/2026-06-04-tendences-konteksts-formatesana-design.md`

**Vide (Windows):** Python = `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"` ar `$env:PYTHONPATH=".venv\Lib\site-packages"` un `$env:PYTHONIOENCODING="utf-8"`. Testi: `bash scripts/check.sh` vai tiešs `pytest`.

---

## File Structure

| Fails | Atbildība | Darbība |
|---|---|---|
| `src/render/_common.py` | `_clean_context_note()` helper | Modify (pievieno funkciju + regex const) |
| `src/render/blog.py:107` | `_fetch_context_notes()` filtrs + `content_html` | Modify |
| `templates/analizes.html.j2:188-192` | Konteksta kartiņu markup | Modify |
| `assets/style.css` | `.ctx-grid`/`.ctx-chip`/`.ctx-meta`/`.ctx-body` + mobile | Modify |
| `data/backfill_asset_note_type.sql` | esošo 9 rindu pārvietošana → `'asset'` | Create |
| `data/rollback_asset_note_type.sql` | rollback | Create |
| `tests/test_context_notes.py` | unit testi helper + fetch | Create |

> **Vienkāršošana (post-review 2026-06-04):** 4 `scripts/gen_*` + `models.py` rediģējumi **izmesti** — skripti ir hardcoded vienreizēji (jau nostrādājuši, neviens `src/` tos nesauc), `models.py` Literal nekad netiek validēts (backfill = raw SQL, apiet Pydantic). Vienīgā dzīvā higiēna ir backfill UPDATE, kas centralizēti salabo visus lasītājus (reader, `routine._check_tendences`, `briefs.py`) bez to koda aiztikšanas. Nav neviena dzīva JSON-audit rakstītāja, tāpēc writer-fix dotu nulli vērtības.

---

## Task 1: `_clean_context_note()` helper

**Files:**
- Modify: `src/render/_common.py`
- Test: `tests/test_context_notes.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_context_notes.py`:

```python
from src.render._common import _clean_context_note


def test_strips_bare_claim_ids():
    out = _clean_context_note("Švinka ierosina pārbaudi (claim #208) un kritizē #6757 projektu.")
    assert "#208" not in out
    assert "#6757" not in out
    assert "claim" not in out  # "claim " prefiks notverts kopā ar ID
    assert "Švinka ierosina pārbaudi" in out


def test_strips_parenthesised_claim_ids():
    out = _clean_context_note("Naratīvs trim mērķiem (#14411) un (#20534).")
    assert "#14411" not in out
    assert "#20534" not in out
    assert "()" not in out  # nepaliek tukšas iekavas


def test_renders_markdown_bold():
    out = _clean_context_note("**Tendence:** libertārisms paplašinās.")
    assert "<strong>" in out
    assert "**" not in out


def test_empty_and_none_safe():
    assert _clean_context_note("") == ""
    assert _clean_context_note(None) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_context_notes.py -v`
Expected: FAIL — `ImportError: cannot import name '_clean_context_note'`

- [ ] **Step 3: Write the helper**

In `src/render/_common.py`, near the existing `_BILL_REF_RE` (line ~158) add the regex const, and add the function after `_sanitize_html` (line ~135). `markdown`, `re`, and `_sanitize_html` are already imported/defined in this module.

```python
# Bare claim-ID citations (e.g. "claim #208", "(#6757)", "(#14411)") lead
# nowhere in the public UI — strip them per house citation style. Optional
# "claim " prefix is consumed with the ID so no orphan word remains.
_CLAIM_ID_RE = re.compile(r"\s*\(?(?:claim\s+)?#\d{3,6}\)?")


def _clean_context_note(content: str | None) -> str:
    """Clean a context-note body for public display.

    Strips bare claim-ID citations, renders markdown (bold/italic/lists),
    and sanitizes the resulting HTML. Returns ``""`` for empty/None input.
    """
    if not content:
        return ""
    text = _CLAIM_ID_RE.sub("", content)
    # Collapse only space/tab runs left where an ID was removed — NOT newlines,
    # which markdown needs for paragraph breaks. Then drop any space stranded
    # before punctuation (e.g. "pārbaudi (#208)." -> "pārbaudi.").
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    return _sanitize_html(md.convert(text.strip()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_context_notes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/render/_common.py tests/test_context_notes.py
git commit -m "feat(tendences): _clean_context_note helper — strip claim-ID + render markdown"
```

---

## Task 2: `_fetch_context_notes()` filter + `content_html`

**Files:**
- Modify: `src/render/blog.py:107-113`
- Test: `tests/test_context_notes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_context_notes.py`:

```python
import sqlite3
from src.render.blog import _fetch_context_notes


def _seed_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT,
            note_type TEXT, content TEXT, created_at TEXT
        )
    """)
    db.executemany(
        "INSERT INTO context_notes (topic, note_type, content, created_at) VALUES (?,?,?,?)",
        [
            ("Rail Baltica", "context", "**Tendence:** kritika (claim #208).", "2026-06-02 10:00:00"),
            (None, "context", '{"kind": "synthesis_featured_image", "slug": "x"}', "2026-06-03 10:00:00"),
            (None, "polling", "Aptauja 42%.", "2026-06-01 10:00:00"),
        ],
    )
    db.commit()
    return db


def test_fetch_excludes_json_and_polling():
    db = _seed_db()
    notes = _fetch_context_notes(db)
    assert len(notes) == 1
    assert notes[0]["topic"] == "Rail Baltica"


def test_fetch_adds_clean_content_html():
    db = _seed_db()
    note = _fetch_context_notes(db)[0]
    assert "content_html" in note
    assert "<strong>" in note["content_html"]
    assert "#208" not in note["content_html"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_context_notes.py -v`
Expected: FAIL — `test_fetch_excludes_json_and_polling` (polling+JSON still returned), `test_fetch_adds_clean_content_html` (no `content_html` key)

- [ ] **Step 3: Update `_fetch_context_notes`**

Replace `src/render/blog.py:107-113` with:

```python
def _fetch_context_notes(db: sqlite3.Connection) -> list[dict[str, Any]]:
    # Only first-party context tendences. 'polling' is foreign to this
    # surface; JSON audit rows (note_type='asset', or legacy '{...}' content
    # written before the asset split) must never leak into the public UI.
    rows = db.execute("""
        SELECT * FROM context_notes
        WHERE note_type = 'context'
          AND TRIM(content) NOT LIKE '{%'
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    notes = []
    for r in rows:
        note = dict(r)
        note["content_html"] = _clean_context_note(note.get("content"))
        notes.append(note)
    return notes
```

Add the import at the top of `blog.py` (line ~42, alongside `from src.render._common import BASE_URL, _render_page`):

```python
from src.render._common import BASE_URL, _clean_context_note, _render_page
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_context_notes.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/render/blog.py tests/test_context_notes.py
git commit -m "feat(tendences): _fetch_context_notes filters context-only + adds content_html"
```

---

## Task 3: Template + CSS (editoriāls chip, responsīvs grid)

**Files:**
- Modify: `templates/analizes.html.j2:187-194`
- Modify: `assets/style.css` (pievieno `.ctx-*` blokus + mobile)

- [ ] **Step 1: Update the template**

Replace `templates/analizes.html.j2:187-194` (the `<div class="grid-3"> ... {% for note %} ... {% endfor %} </div>` blokā) with:

```html
    <div class="grid-3 ctx-grid">
      {% for note in context_notes %}
      <div class="card ctx-card">
        <div class="ctx-meta">
          {% if note.topic %}<span class="ctx-chip">{{ note.topic }}</span>{% endif %}
          <span class="ctx-date">{{ note.created_at[:10] if note.created_at else '' }}</span>
        </div>
        <div class="ctx-body">{{ note.content_html | safe }}</div>
      </div>
      {% endfor %}
    </div>
```

- [ ] **Step 2: Add CSS**

Append to `assets/style.css` (use existing vars: `--surface2 #242838`, `--border`, `--text-muted`, `--radius`, `--accent`):

```css
/* Tendences → Konteksts cards */
.ctx-grid { align-items: start; }          /* variable-height cards size to content, no stretch gaps */
.ctx-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem;
  margin-bottom: 0.6rem;
}
.ctx-chip {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: var(--accent);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 999px;
  white-space: nowrap;
}
.ctx-date { font-size: 0.78rem; color: var(--text-muted); }
.ctx-body { font-size: 0.9rem; line-height: 1.55; overflow-wrap: anywhere; }
.ctx-body > :first-child { margin-top: 0; }
.ctx-body > :last-child { margin-bottom: 0; }
.ctx-body p { margin: 0 0 0.6rem; }
.ctx-body strong { color: var(--text); }
```

Then add mobile tweaks inside the existing `@media (max-width: 768px)` block (style.css:2051):

```css
  .ctx-card { padding: 1rem; }
  .ctx-body { font-size: 0.88rem; }
```

> Note: `.grid-3` already collapses to 1 column at ≤768px (style.css:2052) — no extra column rule needed.

- [ ] **Step 3: Smoke-render the dashboard page**

Run:
```
$env:PYTHONPATH=".venv\Lib\site-packages"; $env:PYTHONIOENCODING="utf-8"; & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m src.render --only=dashboard
```
Expected: completes without error; `output/atmina/analizes.html` regenerated.

- [ ] **Step 4: Grep the output for leaks**

Run: `grep -c '"kind"' output/atmina/analizes.html; grep -Eo '#[0-9]{3,6}' output/atmina/analizes.html | head`
Expected: `0` for `"kind"`; no bare `#NNNNN` in the Konteksts section (claim-ID strip works).

- [ ] **Step 5: Commit**

```bash
git add templates/analizes.html.j2 assets/style.css
git commit -m "feat(tendences): editoriāls Konteksts chip + align-items:start grid + mobile"
```

---

## Task 4: Datu higiēna — backfill 9 JSON audit-rindas → `'asset'`

**Files:**
- Create: `data/backfill_asset_note_type.sql`, `data/rollback_asset_note_type.sql`

> Vienkāršots: nav skriptu/`models.py` rediģējumu (skat. piezīmi File Structure sadaļā). Tikai backfill + rollback — viens UPDATE centralizēti salabo visus lasītājus.

- [ ] **Step 1: Write the rollback SQL (capture before mutating)**

Create `data/rollback_asset_note_type.sql`:

```sql
-- Rollback for backfill_asset_note_type.sql (2026-06-04).
-- Reverts the 9 image-audit rows back to note_type='context'.
-- Safe because only JSON-content rows were touched.
UPDATE context_notes
   SET note_type = 'context'
 WHERE note_type = 'asset' AND TRIM(content) LIKE '{%';
```

- [ ] **Step 2: Write the backfill SQL**

Create `data/backfill_asset_note_type.sql`:

```sql
-- Move legacy image-audit rows (JSON content stored as note_type='context')
-- to the dedicated note_type='asset' so they never reach public readers.
-- brief_images.note_id FK is unaffected (id unchanged). 2026-06-04.
UPDATE context_notes
   SET note_type = 'asset'
 WHERE note_type = 'context' AND TRIM(content) LIKE '{%';
```

- [ ] **Step 3: Run the backfill against the DB**

Run:
```
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -c "import sqlite3; db=sqlite3.connect('data/atmina.db'); n=db.execute(open('data/backfill_asset_note_type.sql').read()).rowcount; db.commit(); print('rows moved:', n)"
```
Expected: `rows moved: 9`

- [ ] **Step 4: Verify no JSON context rows remain**

Run:
```
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -c "import sqlite3; db=sqlite3.connect('data/atmina.db'); print('json context left:', db.execute(\"SELECT COUNT(*) FROM context_notes WHERE note_type='context' AND TRIM(content) LIKE '{%'\").fetchone()[0]); print('asset rows:', db.execute(\"SELECT COUNT(*) FROM context_notes WHERE note_type='asset'\").fetchone()[0])"
```
Expected: `json context left: 0`, `asset rows: 9`

- [ ] **Step 5: Commit**

```bash
git add data/backfill_asset_note_type.sql data/rollback_asset_note_type.sql
git commit -m "feat(tendences): datu higiēna — backfill 9 JSON audit-rindas uz note_type=asset"
```

---

## Task 5: Vizuālā verifikācija (desktop + mobile) — galvenais akcepta kritērijs

**Files:** (nav koda izmaiņu, ja viss kārtībā)

- [ ] **Step 1: Re-render with clean data**

Run:
```
$env:PYTHONPATH=".venv\Lib\site-packages"; $env:PYTHONIOENCODING="utf-8"; & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m src.render --only=dashboard
```
Expected: success.

- [ ] **Step 2: Playwright — desktop snapshot**

Use the Playwright MCP browser: navigate to `file:///~/atmina/output/atmina/analizes.html`, resize to 1280×900, click the "Tendences" tab, scroll to the "Konteksts" heading, take a screenshot.
Expected: 3-column grid, cards aligned to top (no stretched empty cards), chips render as pills, no `{"kind"`, no bare `#NNNNN`, bold renders as `<strong>`.

- [ ] **Step 3: Playwright — mobile snapshot**

Resize to 390×844, take a screenshot of the same Konteksts section.
Expected: single column, chip+date wrap cleanly, no horizontal overflow/scroll, readable font sizes, card padding comfortable.

- [ ] **Step 4: Full verification suite**

Run: `bash scripts/check.sh`
Expected: ruff clean, pytest green (incl. new `tests/test_context_notes.py`), generate_public_site smoke passes.

- [ ] **Step 5: Final commit (if any visual tweaks were needed)**

```bash
git add -A
git commit -m "fix(tendences): vizuālie pielāgojumi pēc dual-viewport verifikācijas"
```

---

## Notes for the implementer

- **No raw `{{ note.content }}` anymore** — template uses `{{ note.content_html | safe }}`; `_clean_context_note` already sanitizes via bleach, so `| safe` is correct.
- **`briefs.py:183` JSON filter stays** as defense-in-depth — do NOT remove it.
- **FK safety:** the backfill only changes `note_type`, not `id`, so `brief_images.note_id` references stay valid.
- **`store_context_note` (`tools.py:262`) is not in scope** — agents write `note_type='context'` for real notes; only the 4 image scripts write asset rows.
