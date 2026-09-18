# Weekly Brief Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the weekly brief from a 7-day daily-clone into a distinct, mobile-first, source-linked product with cross-day synthesis, an accurate in-body movers chart, and ink-navy weekly chrome.

**Architecture:** Extend the existing orphaned `generate_weekly_brief()` skeleton (deterministic DB data + markers) and let a new `weekly-brief-writer` agent enrich it with prose — mirroring the daily `generate_daily_brief()` + enrich split. The in-body chart is a deterministic hand-rolled SVG that lives as a file (never in `brief_images`). A dedicated weekly render partial + `.weekly-*` CSS carry the visual identity; the AI featured image is a bonus in a new `WEEKLY_STYLE` frame.

**Tech Stack:** Python 3.12, SQLite, `python-markdown`, Jinja2, hand-rolled SVG (no matplotlib — it is not in the default venv, per `conftest.py`), pytest.

**Branch:** `weekly-brief-redesign` (already created; spec at `docs/superpowers/specs/2026-06-01-weekly-brief-redesign-design.md`).

**Verification command (run after each phase):** `bash scripts/check.sh` (ruff + pytest + site smoke).

---

## File Structure

**Phase 1 — content engine**
- Modify `src/briefs.py` — extend `generate_weekly_brief()`: week-over-week deltas, `<!-- WEEKLY_STATS -->` marker, theme scaffold with source-linked positions, `## Nedēļas stāsts` placeholder.
- Modify `src/tools.py` — `_validate_brief_structure` weekly branch → new required sections.
- Create `.claude/agents/weekly-brief-writer.md` — weekly-only structure agent.
- Create `wiki/operations/agenti/brief-shared-rules.md` — shared journalism rules.
- Modify `.claude/agents/brief-writer.md` — reference shared-rules doc.
- Create/extend `tests/test_briefs_weekly.py`, extend `tests/test_tools.py`.

**Phase 2 — visual layer**
- Create `src/graphics/weekly_chart.py` — `make_movers_svg()`.
- Modify `src/briefs.py` — hook chart into `generate_weekly_brief()`.
- Modify `src/render/blog.py` — branch weekly → partial; parse `<!-- WEEKLY_STATS -->`.
- Create `templates/_weekly_body.html.j2` — weekly post body.
- Modify `assets/style.css` — `.weekly-*` layer reusing existing responsive patterns.
- Modify `src/graphics/prompt.py` — add `WEEKLY_STYLE` variant.
- Modify `.claude/agents/graphics-designer.md` — pick weekly style for `weekly_brief`.
- Create `tests/test_weekly_chart.py`; extend `tests/test_graphics_prompt.py` (or create).
- Modify `wiki/operations/weekly-routine.md`, `wiki/CHANGELOG.md`.

---

# PHASE 1 — Content engine

## Task 1: Week-over-week deltas helper

**Files:**
- Modify: `src/briefs.py` (add `_weekly_movers()` near `generate_weekly_brief`, ~line 443)
- Test: `tests/test_briefs_weekly.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_briefs_weekly.py
from src.db import init_db, get_db
from src.briefs import _weekly_movers


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Test', 'T', 'coalition')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (1,'Aļģis','Test','tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2,'Bērziņš','Test','tracked')")
    # documents needed for FK on position claims
    for did in (10, 11, 12, 13):
        db.execute("INSERT INTO documents (id, platform, source_url, content, scraped_at) VALUES (?, 'web', ?, 'x', '2026-05-20')",
                   (did, f"https://e.lv/{did}"))
    # this week (2026-05-26..06-01): pid1=3 claims, pid2=1 claim
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,10,'A','s','https://e.lv/10','2026-05-27','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,11,'A','s','https://e.lv/11','2026-05-28','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,12,'A','s','https://e.lv/12','2026-05-29','position')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (2,13,'A','s','https://e.lv/13','2026-05-30','position')")
    # previous week (2026-05-19..25): pid1=1 claim (baseline), pid2=0 (no baseline)
    db.execute("INSERT INTO documents (id, platform, source_url, content, scraped_at) VALUES (20, 'web', 'https://e.lv/20', 'x', '2026-05-20')")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, claim_type) VALUES (1,20,'A','s','https://e.lv/20','2026-05-20','position')")
    db.commit()
    return db


def test_weekly_movers_counts_and_deltas(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    movers = _weekly_movers(db_path, "2026-05-26", "2026-06-01")
    by_name = {m["name"]: m for m in movers}
    # absolute counts this week
    assert by_name["Aļģis"]["count"] == 3
    assert by_name["Bērziņš"]["count"] == 1
    # delta vs prior week: Aļģis 1->3 = +2; Bērziņš no baseline => "jauns"
    assert by_name["Aļģis"]["delta"] == 2
    assert by_name["Bērziņš"]["delta"] == "jauns"
    # sorted by count desc
    assert movers[0]["name"] == "Aļģis"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py::test_weekly_movers_counts_and_deltas -v`
Expected: FAIL with `ImportError: cannot import name '_weekly_movers'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/briefs.py` (after `generate_weekly_brief`):

```python
def _weekly_movers(db_path: str, week_start: str, week_end: str, limit: int = 6) -> list[dict]:
    """Top `limit` politicians by position-claims this week, with delta vs the
    prior 7-day window. delta is an int, or the string "jauns" when the prior
    window has zero baseline. Absolute counts only — never percentages."""
    from datetime import datetime, timedelta
    db = get_db(db_path)
    prev_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_end = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    def counts(start, end):
        rows = db.execute("""
            SELECT p.id, p.name, p.party, COUNT(*) AS cnt
            FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
              AND p.relationship_type != 'inactive'
            GROUP BY p.id
        """, (start, end)).fetchall()
        return {r["id"]: r for r in rows}

    cur = counts(week_start, week_end)
    prev = counts(prev_start, prev_end)
    movers = []
    for pid, r in cur.items():
        base = prev.get(pid)
        delta = (r["cnt"] - base["cnt"]) if base else "jauns"
        movers.append({"id": pid, "name": r["name"], "party": r["party"],
                       "count": r["cnt"], "delta": delta})
    movers.sort(key=lambda m: m["count"], reverse=True)
    db.close()
    return movers[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py::test_weekly_movers_counts_and_deltas -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/briefs.py tests/test_briefs_weekly.py
git commit -m "feat(weekly): add _weekly_movers delta helper"
```

---

## Task 2: Extend `generate_weekly_brief()` skeleton (stats marker, story placeholder, theme scaffold)

**Files:**
- Modify: `src/briefs.py:420-442` (the `lines` assembly inside `generate_weekly_brief`)
- Test: `tests/test_briefs_weekly.py`

- [ ] **Step 1: Write the failing test**

```python
def test_weekly_skeleton_has_new_sections(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    md = generate_weekly_brief(db_path, week_start="2026-05-26")
    assert md.startswith("# Nedēļas analīze — 2026-05-26 līdz 2026-06-01")
    assert "## Nedēļas stāsts" in md
    assert "## Nedēļā skaitļos" in md
    assert "<!-- WEEKLY_STATS:" in md
    assert "positions=4" in md          # 4 position claims seeded this week
    assert "## Kas kustējās" in md
    assert "## Nedēļas galvenās tēmas" in md
    # theme scaffold includes a source-linked candidate position
    assert "https://e.lv/" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py::test_weekly_skeleton_has_new_sections -v`
Expected: FAIL (old skeleton has `## Galvenais` / `## Aktīvākie politiķi nedēļā`, not the new sections).

- [ ] **Step 3: Replace the `lines` assembly in `generate_weekly_brief`**

Replace `src/briefs.py` lines 420-441 (from `lines = [...]` through the `return`) with:

```python
    top_topic = by_topic[0]["topic"] if by_topic else "—"
    top_party_row = db.execute("""
        SELECT p.party, COUNT(*) AS cnt FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type='position'
          AND p.relationship_type != 'inactive' AND p.party IS NOT NULL
        GROUP BY p.party ORDER BY cnt DESC LIMIT 1
    """, (week_start, week_end)).fetchone()
    top_party = top_party_row["party"] if top_party_row else "—"

    lines = [f"# Nedēļas analīze — {week_start} līdz {week_end}\n"]

    # Prose section — agent fills. Placeholder keeps validation + structure stable.
    lines.append("## Nedēļas stāsts\n")
    lines.append("<!-- AGENT: 2-3 īsas prozas rindkopas par nedēļas arku. "
                 "Aizvāc šo komentāru. -->\n")

    # Deterministic stat strip (render-time parsed into cards).
    lines.append("## Nedēļā skaitļos\n")
    lines.append(
        f"<!-- WEEKLY_STATS: positions={position_count} votes={vote_count} "
        f"contradictions={contradiction_count} top_topic={top_topic} "
        f"top_party={top_party} -->\n"
    )

    # Movers — Phase 2 replaces this comment with an SVG image reference.
    lines.append("## Kas kustējās\n")
    movers = _weekly_movers(db_path, week_start, week_end)
    for m in movers:
        d = m["delta"]
        arrow = "jauns" if d == "jauns" else (f"↑{d}" if isinstance(d, int) and d > 0
                 else (f"↓{abs(d)}" if isinstance(d, int) and d < 0 else "—"))
        lines.append(f"- **{m['name']}** ({m['party'] or '—'}) — {m['count']} ({arrow})")

    # Theme scaffold — top topics with source-linked candidate positions.
    if by_topic:
        lines.append("\n## Nedēļas galvenās tēmas\n")
        for t in by_topic[:4]:
            lines.append(f"### {t['topic']} — {t['cnt']} pozīcijas\n")
            cands = db.execute("""
                SELECT p.name, p.party, c.stance, c.source_url
                FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
                WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type='position'
                  AND c.topic = ? AND p.relationship_type != 'inactive'
                ORDER BY c.salience DESC LIMIT 3
            """, (week_start, week_end, t["topic"])).fetchall()
            for c in cands:
                url = c["source_url"] or ""
                lines.append(f"- {c['name']} ({c['party'] or '—'}): {c['stance']} {url}")
            lines.append("")

    db.close()
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add src/briefs.py tests/test_briefs_weekly.py
git commit -m "feat(weekly): new skeleton sections + stats marker + theme scaffold"
```

---

## Task 3: Update weekly validation in `src/tools.py`

**Files:**
- Modify: `src/tools.py:246-258` (`weekly_brief` branch of `_validate_brief_structure`)
- Test: `tests/test_tools.py` (extend; create if absent)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py  (append)
import pytest
from src.tools import _validate_brief_structure


def test_weekly_validation_requires_new_sections():
    good = ("# Nedēļas analīze — 2026-05-26 līdz 2026-06-01\n\n"
            "## Nedēļas stāsts\n" + ("proza " * 600) +
            "\n## Nedēļas galvenās tēmas\n- x\n## Vizuālais brief\n- **Tēma:** A\n")
    _validate_brief_structure(good, "weekly_brief")  # should not raise

    missing_story = good.replace("## Nedēļas stāsts", "## Kaut kas")
    with pytest.raises(ValueError) as e:
        _validate_brief_structure(missing_story, "weekly_brief")
    assert "Nedēļas stāsts" in str(e.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_tools.py::test_weekly_validation_requires_new_sections -v`
Expected: FAIL (current branch requires `## Aktīvākie politiķi`, not `## Nedēļas stāsts`).

- [ ] **Step 3: Replace the weekly branch (`src/tools.py:246-258`)**

```python
    elif note_type == "weekly_brief":
        missing = []
        if not content.startswith("# "):
            missing.append("Jāsākas ar '# ' (H1, ne '##')")
        for section in ["## Nedēļas stāsts", "## Nedēļas galvenās tēmas"]:
            if section not in content:
                missing.append(f"Trūkst sekcija: {section}")
        if len(content) < 3000:
            missing.append(f"Pārāk īss: {len(content)} chars (min 3000)")
        if missing:
            raise ValueError(
                "Nedēļas pārskats neatbilst formāta prasībām:\n- "
                + "\n- ".join(missing)
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_tools.py::test_weekly_validation_requires_new_sections -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tools.py tests/test_tools.py
git commit -m "feat(weekly): validation requires new weekly section contract"
```

---

## Task 4: Extract shared journalism rules doc

**Files:**
- Create: `wiki/operations/agenti/brief-shared-rules.md`
- Modify: `.claude/agents/brief-writer.md` (add a reference line near the top, after line 8)

- [ ] **Step 1: Create `wiki/operations/agenti/brief-shared-rules.md`**

```markdown
# Brief shared rules (daily + weekly)

Koplietotie žurnālistikas noteikumi `brief-writer` un `weekly-brief-writer`
aģentiem. Katrs aģents pievieno savu struktūras kontraktu; šie noteikumi ir
kopīgi.

## Mutācija
- Vienīgā atļautā DB rakstīšana ir `store_context_note()`. NEKAD DELETE/DROP/
  destruktīvs UPDATE uz `claims`, `contradictions`, `analyses`, `documents`,
  `document_politicians`, `tracked_politicians`, `saeima_*`.

## Avoti
- Katram pieminētam apgalvojumam jābūt `source_url`. Formāts: `[domēns.lv](pilns_url)`.
  Ja nav URL — `—`, nefabricē.

## Per-speaker atribūcija (OBLIGĀTI)
- Teikumā formā "X un Y [darbība] Z" katram nosauktajam runātājam DB jābūt
  vismaz vienam `claims` ierakstam par tieši TO substanci. Bucket-grupēšana un
  co-occurrence NAV pierādījums. Sk. memory `feedback_synthesis_attribution`.

## NO DB iekšējiem ID/enum publiskā tekstā
- NEKAD `Pretruna #24`, `(minor_shift)`, `(6↔123)`. Lieto aprakstošas atsauces.

## LV-stilistika
- Pirms saglabāt palaid `lint_lv_style(content)` un izlabo visu. `5 %` (ar
  atstarpi), `eiro`, NE `ataka/polemika/aksi/startā`. Saglabā diakritiku.

## Neitralitāte
- Bez ieteikumiem, partijas perspektīvas, subjektīviem īpašības vārdiem.
  Proporcionāli substancei, ne mākslīgam balansam.
```

- [ ] **Step 2: Add reference in `.claude/agents/brief-writer.md`**

After line 8 (the intro paragraph), insert:

```markdown
> **Koplietotie noteikumi:** avotu disciplīna, per-speaker atribūcija, LV-stilistika,
> NO-DB-ID, `store_context_note`-only mutācija — sk. [`wiki/operations/agenti/brief-shared-rules.md`](../../wiki/operations/agenti/brief-shared-rules.md). Zemāk tikai dienas struktūras kontrakts.
```

- [ ] **Step 3: Verify both files exist and lint passes**

Run: `bash scripts/check.sh`
Expected: ruff + pytest green (doc-only change does not break anything).

- [ ] **Step 4: Commit**

```bash
git add wiki/operations/agenti/brief-shared-rules.md .claude/agents/brief-writer.md
git commit -m "docs(weekly): extract shared brief rules; reference from brief-writer"
```

---

## Task 5: Create `weekly-brief-writer` agent

**Files:**
- Create: `.claude/agents/weekly-brief-writer.md`
- Create: `wiki/operations/agenti/weekly-brief-writer.md` (human-readable description)

- [ ] **Step 1: Create `.claude/agents/weekly-brief-writer.md`**

```markdown
---
name: weekly-brief-writer
description: Neutral WEEKLY brief generator — cross-day synthesis, mobile-first, source-linked. Enriches generate_weekly_brief() skeleton; never restructures it.
---

# Weekly Brief Writer

Tu raksti neitrālu **nedēļas** politisko analīzi atmina.lv. Koplietotie
žurnālistikas noteikumi — sk. `wiki/operations/agenti/brief-shared-rules.md`
(avoti, per-speaker atribūcija, LV-stilistika, NO-DB-ID, mutācija). Šis fails
satur TIKAI nedēļas struktūras kontraktu. **Nelieto daily noteikumus** (nav
Spriedžu tabulas, nav Koalīcija-vs-Opozīcija 5-kolonnu tabulas, nav DIENAS STATS).

## Ievaddati
`generate_weekly_brief(week_start='YYYY-MM-DD')` skelets ar markeriem un
deterministiskiem datiem. Tavs darbs — bagātināt prozā, NE pārstrukturēt.

## SAGLABĀ (verbatim)
- `# Nedēļas analīze — START līdz END` (H1).
- `<!-- WEEKLY_STATS: … -->` marker (template to parsē kartītēs).
- `## Kas kustējās` grafika `![](…)` atsauce (ja skelets to ir ievietojis).
- Visi `source_url` linki tēmu kandidātos.

## PAPILDINI
- `## Nedēļas stāsts` — 2-3 īsas prozas rindkopas par nedēļas arku
  (dominējošais pavediens). Aizvāc `<!-- AGENT: … -->` komentāru.
- `## Kas kustējās` — 1 teikuma paraksts zem grafika.
- `## Nedēļas galvenās tēmas` — katrai tēmai pārvērt kandidātu pozīcijas
  īsā sintēzē (2-3 teikumi), saglabājot avotu linkus kā kompaktu sarakstu.
- `## Pretrunas` — tikai confirmed, aprakstoši.
- `## Skats uz priekšu` — 1-2 teikumi (neobligāti).
- `## Vizuālais brief` — Tēma/Galvenā tēze/Skaitlis/Metaforas hint.

## Self-check pirms store
1. ✅ Sākas ar `# `; satur `## Nedēļas stāsts` un `## Nedēļas galvenās tēmas`.
2. ✅ ≥3000 simboli.
3. ✅ `<!-- WEEKLY_STATS -->` saglabāts; `<!-- AGENT: … -->` aizvākts.
4. ✅ `lint_lv_style(content)` == [] (citādi labo).
5. ✅ Per-speaker atribūcija pārbaudīta visiem "X un Y" teikumiem.
6. ✅ `## Vizuālais brief` bloks beigās.

## Storage
```python
from src.tools import store_context_note
store_context_note(topic="nedēļas analīze START līdz END",
    note_type="weekly_brief", content=md, source="atmina analīze")
```
```

- [ ] **Step 2: Create the human-readable wiki description**

```markdown
# @weekly-brief-writer

Nedēļas pārskatu ģenerators — sintēze pār 7 dienām, mobile-first, ar avotiem.
Bagātina `generate_weekly_brief()` skeletu prozā. Koplietotie noteikumi:
[[operations/agenti/brief-shared-rules|brief-shared-rules]]. Atšķirībā no
[[operations/agenti/brief-writer|@brief-writer]] (daily) — bez Spriedžu/
Koalīcija-vs-Opozīcija tabulām; proza-vadīts.
```

Save to `wiki/operations/agenti/weekly-brief-writer.md`.

- [ ] **Step 3: Verify**

Run: `bash scripts/check.sh`
Expected: green (doc-only).

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/weekly-brief-writer.md wiki/operations/agenti/weekly-brief-writer.md
git commit -m "feat(weekly): dedicated weekly-brief-writer agent"
```

**Phase 1 checkpoint:** Run `bash scripts/check.sh` — must be green before Phase 2.

---

# PHASE 2 — Visual layer

## Task 6: SVG movers chart generator

**Files:**
- Create: `src/graphics/weekly_chart.py`
- Test: `tests/test_weekly_chart.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_weekly_chart.py
import xml.dom.minidom
from src.graphics.weekly_chart import make_movers_svg


def test_make_movers_svg_wellformed():
    movers = [
        {"name": "Aļģis", "party": "AS", "count": 20, "delta": 5},
        {"name": "Bērziņš", "party": "JV", "count": 12, "delta": "jauns"},
        {"name": "Cīrulis", "party": "NA", "count": 8, "delta": -3},
    ]
    coalition = {"coalition": 30, "opposition": 10}
    svg = make_movers_svg(movers, coalition).decode("utf-8")
    # well-formed XML
    xml.dom.minidom.parseString(svg)
    assert svg.startswith("<?xml") or svg.lstrip().startswith("<svg")
    # one bar per mover (rects with class bar)
    assert svg.count('class="bar"') == 3
    # names + counts rendered; delta annotations present
    assert "Aļģis" in svg and "20" in svg
    assert "jauns" in svg          # no-baseline label
    assert "↓3" in svg or "−3" in svg
    # coalition vs opposition strip present
    assert "Koalīcija" in svg and "Opozīcija" in svg


def test_make_movers_svg_empty_week():
    svg = make_movers_svg([], {"coalition": 0, "opposition": 0}).decode("utf-8")
    xml.dom.minidom.parseString(svg)   # still well-formed
    assert "Nav datu" in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_weekly_chart.py -v`
Expected: FAIL with `ModuleNotFoundError: src.graphics.weekly_chart`.

- [ ] **Step 3: Implement `src/graphics/weekly_chart.py`**

```python
"""Deterministic weekly movers chart as hand-rolled SVG.

No matplotlib (not in the default venv — see tests/conftest.py). The chart is
DATA, not creative work: it never enters the brief_images approval loop. The
caller writes the returned bytes to output/images/briefs/<date>-nedelas-movers.svg
and references it from the markdown via <img>/![]().

Palette: cream background, ink-navy bars (weekly chrome accent).
"""
from __future__ import annotations
from xml.sax.saxutils import escape

_CREAM = "#f4efe4"
_NAVY = "#1f2d4d"
_INK = "#222222"
_W = 720
_ROW_H = 34
_PAD = 16
_LABEL_W = 150
_BAR_MAX = 380


def _delta_label(d) -> str:
    if d == "jauns":
        return "jauns"
    if isinstance(d, int) and d > 0:
        return f"↑{d}"
    if isinstance(d, int) and d < 0:
        return f"↓{abs(d)}"
    return "—"


def make_movers_svg(movers: list[dict], coalition: dict[str, int]) -> bytes:
    """Render a horizontal-bar movers chart. `movers` = list of
    {name, party, count, delta}. `coalition` = {"coalition": n, "opposition": n}."""
    rows = movers[:6]
    chart_h = _PAD * 2 + max(1, len(rows)) * _ROW_H + 60  # +strip
    parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {chart_h}" '
        f'font-family="Georgia, serif">',
        f'<rect width="{_W}" height="{chart_h}" fill="{_CREAM}"/>',
    ]
    if not rows:
        parts.append(f'<text x="{_W/2}" y="{chart_h/2}" text-anchor="middle" '
                     f'fill="{_INK}" font-size="18">Nav datu</text>')
    else:
        max_count = max(m["count"] for m in rows) or 1
        for i, m in enumerate(rows):
            y = _PAD + i * _ROW_H
            bar_w = int(_BAR_MAX * m["count"] / max_count)
            name = escape(f'{m["name"]} ({m["party"] or "—"})')
            parts.append(f'<text x="{_PAD}" y="{y + 20}" fill="{_INK}" '
                         f'font-size="14">{name}</text>')
            parts.append(f'<rect class="bar" x="{_LABEL_W}" y="{y + 6}" '
                         f'width="{bar_w}" height="20" fill="{_NAVY}"/>')
            label = escape(f'{m["count"]}  {_delta_label(m["delta"])}')
            parts.append(f'<text x="{_LABEL_W + bar_w + 8}" y="{y + 21}" '
                         f'fill="{_INK}" font-size="13">{label}</text>')
        # coalition vs opposition strip
        total = (coalition.get("coalition", 0) + coalition.get("opposition", 0)) or 1
        sy = _PAD + len(rows) * _ROW_H + 20
        coal_w = int(_BAR_MAX * coalition.get("coalition", 0) / total)
        parts.append(f'<text x="{_PAD}" y="{sy + 14}" fill="{_INK}" font-size="13">'
                     f'Koalīcija vs Opozīcija</text>')
        parts.append(f'<rect x="{_LABEL_W}" y="{sy}" width="{coal_w}" height="16" fill="{_NAVY}"/>')
        parts.append(f'<rect x="{_LABEL_W + coal_w}" y="{sy}" width="{_BAR_MAX - coal_w}" '
                     f'height="16" fill="#b9402f"/>')
    parts.append("</svg>")
    return "\n".join(parts).encode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_weekly_chart.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/graphics/weekly_chart.py tests/test_weekly_chart.py
git commit -m "feat(weekly): hand-rolled SVG movers chart"
```

---

## Task 7: Hook chart into `generate_weekly_brief()`

**Files:**
- Modify: `src/briefs.py` (the `## Kas kustējās` block from Task 2)
- Test: `tests/test_briefs_weekly.py`

- [ ] **Step 1: Write the failing test**

```python
def test_weekly_skeleton_embeds_chart(tmp_path):
    from src.briefs import generate_weekly_brief
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    out_dir = tmp_path / "imgs"
    md = generate_weekly_brief(db_path, week_start="2026-05-26",
                               chart_dir=str(out_dir))
    assert "![Kas kustējās](" in md
    files = list(out_dir.glob("*-nedelas-movers.svg"))
    assert len(files) == 1
    assert files[0].read_bytes().startswith(b"<?xml")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py::test_weekly_skeleton_embeds_chart -v`
Expected: FAIL (`chart_dir` param missing; no image reference).

- [ ] **Step 3: Update `generate_weekly_brief` signature + `## Kas kustējās` block**

Change the signature to:

```python
def generate_weekly_brief(db_path: str = None, week_start: str = None,
                          chart_dir: str = "output/images/briefs") -> str:
```

Replace the `## Kas kustējās` block (added in Task 2) with:

```python
    lines.append("## Kas kustējās\n")
    movers = _weekly_movers(db_path, week_start, week_end)
    from src.coalition import get_coalition_map
    cmap = get_coalition_map(db)
    coalition = {"coalition": 0, "opposition": 0}
    for m in movers:
        status = cmap.get(m["party"], "other")
        if status in coalition:
            coalition[status] += m["count"]
    from pathlib import Path
    from src.graphics.weekly_chart import make_movers_svg
    svg = make_movers_svg(movers, coalition)
    out_dir = Path(chart_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{week_start}-nedelas-movers.svg"
    (out_dir / fname).write_bytes(svg)
    lines.append(f"![Kas kustējās](images/briefs/{fname})\n")
    for m in movers:
        d = m["delta"]
        arrow = "jauns" if d == "jauns" else (f"↑{d}" if isinstance(d, int) and d > 0
                 else (f"↓{abs(d)}" if isinstance(d, int) and d < 0 else "—"))
        lines.append(f"- **{m['name']}** ({m['party'] or '—'}) — {m['count']} ({arrow})")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_briefs_weekly.py -v`
Expected: PASS (all weekly tests).

- [ ] **Step 5: Commit**

```bash
git add src/briefs.py tests/test_briefs_weekly.py
git commit -m "feat(weekly): embed movers SVG into weekly skeleton"
```

---

## Task 8: Weekly render branch + partial + stat-strip parsing

**Files:**
- Modify: `src/render/blog.py:362-380` (the per-post render loop in `render_blog`)
- Create: `templates/_weekly_body.html.j2`
- Test: `tests/test_render_weekly.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_weekly.py
import re
from src.render.blog import _parse_weekly_stats


def test_parse_weekly_stats():
    md = ("## Nedēļā skaitļos\n"
          "<!-- WEEKLY_STATS: positions=173 votes=94 contradictions=1 "
          "top_topic=Koalīcija un partijas top_party=Apvienotais saraksts -->\n")
    stats = _parse_weekly_stats(md)
    assert stats["positions"] == "173"
    assert stats["votes"] == "94"
    assert stats["top_topic"] == "Koalīcija un partijas"
    assert stats["top_party"] == "Apvienotais saraksts"


def test_parse_weekly_stats_absent_returns_none():
    assert _parse_weekly_stats("no marker here") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_weekly.py -v`
Expected: FAIL (`cannot import name '_parse_weekly_stats'`).

- [ ] **Step 3: Add `_parse_weekly_stats` to `src/render/blog.py`** (near other helpers, ~line 52)

```python
import re as _re_stats

_WEEKLY_STATS_RE = _re_stats.compile(
    r"<!--\s*WEEKLY_STATS:\s*positions=(?P<positions>\d+)\s+votes=(?P<votes>\d+)\s+"
    r"contradictions=(?P<contradictions>\d+)\s+top_topic=(?P<top_topic>.+?)\s+"
    r"top_party=(?P<top_party>.+?)\s*-->"
)


def _parse_weekly_stats(content: str) -> dict[str, str] | None:
    """Extract the deterministic WEEKLY_STATS marker into a dict, or None."""
    m = _WEEKLY_STATS_RE.search(content)
    return m.groupdict() if m else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_weekly.py -v`
Expected: PASS.

- [ ] **Step 5: Branch the render loop** — in `render_blog`, inside the per-post loop (`src/render/blog.py:363`), replace the single `_render_page(... "blog-post.html.j2" ...)` call with:

```python
        is_weekly = post.get("note_type") == "weekly_brief"
        template_name = "_weekly_body.html.j2" if is_weekly else "blog-post.html.j2"
        weekly_stats = _parse_weekly_stats(post["content"]) if is_weekly else None
        _render_page(env, template_name, blog_dir / f"{post['slug']}.html", {
            "post": post,
            "content_html": content_html,
            "weekly_stats": weekly_stats,
            "prev_post": prev_post,
            "next_post": next_post,
            "back_href": "../analizes.html",
            "BASE_URL": BASE_URL,
        })
```

(Keep the existing `strip_visual_brief_block` + first-heading-strip + `md_renderer` lines above it unchanged.)

- [ ] **Step 6: Create `templates/_weekly_body.html.j2`** (extends base, weekly chrome)

```jinja
{% extends "base.html.j2" %}
{% block og_image %}{% if post.image_filename %}{{ BASE_URL|default('https://atmina.lv') }}/images/briefs/{{ post.image_filename|image_variant('og') }}{% else %}{{ BASE_URL|default('https://atmina.lv') }}/assets/og-image.png{% endif %}{% endblock %}
{% block content %}
<article class="weekly-post">
  <header class="weekly-cover">
    {% if post.image_filename %}
    <img class="weekly-hero" src="../images/briefs/{{ post.image_filename|image_variant('hero') }}" alt="">
    {% endif %}
    <span class="weekly-badge">Nedēļas analīze · {{ post.date }}</span>
    <h1>{{ post.display_title|default(post.title) }}</h1>
  </header>

  {% if weekly_stats %}
  <section class="weekly-stats">
    <div class="weekly-stat-card"><b>{{ weekly_stats.positions }}</b><span>pozīcijas</span></div>
    <div class="weekly-stat-card"><b>{{ weekly_stats.votes }}</b><span>balsojumi</span></div>
    <div class="weekly-stat-card"><b>{{ weekly_stats.contradictions }}</b><span>pretrunas</span></div>
    <div class="weekly-stat-card"><b>{{ weekly_stats.top_topic }}</b><span>top tēma</span></div>
    <div class="weekly-stat-card"><b>{{ weekly_stats.top_party }}</b><span>aktīvākā partija</span></div>
  </section>
  {% endif %}

  <div class="weekly-body">{{ content_html | safe }}</div>

  <nav class="weekly-nav">
    {% if prev_post %}<a href="{{ prev_post.slug }}.html">← {{ prev_post.date }}</a>{% endif %}
    {% if next_post %}<a href="{{ next_post.slug }}.html">{{ next_post.date }} →</a>{% endif %}
  </nav>
</article>
{% endblock %}
```

- [ ] **Step 7: Render smoke**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without error; `output/atmina/blog/nedela-*.html` exists and contains `weekly-stats`.

- [ ] **Step 8: Commit**

```bash
git add src/render/blog.py templates/_weekly_body.html.j2 tests/test_render_weekly.py
git commit -m "feat(weekly): dedicated render partial + stat-strip parsing"
```

---

## Task 9: `.weekly-*` CSS (mobile-first, reuse existing patterns)

**Files:**
- Modify: `assets/style.css` (append a `.weekly-*` block; add mobile rules inside the existing `@media (max-width: 768px)` block at the file end)

- [ ] **Step 1: Append the weekly layer** (end of `assets/style.css`, before the final `@media` block)

```css
/* ---- Weekly brief ---- */
.weekly-post { max-width: 820px; margin: 0 auto; }
.weekly-cover { position: relative; margin-bottom: 1.5rem; }
.weekly-hero { width: 100%; border-radius: 6px; }
.weekly-badge {
  display: inline-block; margin-top: 1rem; padding: 0.25rem 0.7rem;
  background: #1f2d4d; color: #f4efe4; font-size: 0.85rem; letter-spacing: 0.03em;
  border-radius: 3px; text-transform: uppercase;
}
.weekly-stats {
  display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1.5rem 0;
}
.weekly-stat-card {
  flex: 1 1 140px; min-width: 140px; padding: 0.9rem 1rem;
  background: #f4efe4; border-left: 4px solid #1f2d4d; border-radius: 4px;
  display: flex; flex-direction: column;
}
.weekly-stat-card b { font-size: 1.25rem; color: #1f2d4d; }
.weekly-stat-card span { font-size: 0.8rem; color: #555; }
.weekly-body h3 { border-left: 4px solid #1f2d4d; padding-left: 0.6rem; }
.weekly-body img { width: 100%; border-radius: 4px; margin: 1rem 0; }
.weekly-body blockquote {
  border-left: 3px solid #1f2d4d; padding-left: 1rem; font-style: italic; color: #333;
}
.weekly-nav { display: flex; justify-content: space-between; margin-top: 2rem; flex-wrap: wrap; gap: 0.5rem; }
```

- [ ] **Step 2: Add mobile rules** — inside the existing `@media (max-width: 768px)` block at the end of `assets/style.css`, add:

```css
  .weekly-stats { gap: 0.5rem; }
  .weekly-stat-card { flex: 1 1 100%; }
  .weekly-post { padding: 0 1rem; }
```

- [ ] **Step 3: Render smoke + eyeball**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`
Then open `output/atmina/blog/nedela-2026-05-26.html` (if a weekly note exists) and confirm the stat cards stack on a narrow viewport.

- [ ] **Step 4: Commit**

```bash
git add assets/style.css
git commit -m "feat(weekly): ink-navy weekly CSS, mobile-first stat cards"
```

---

## Task 10: `WEEKLY_STYLE` featured-image frame

**Files:**
- Modify: `src/graphics/prompt.py` (add a `weekly` entry to `STYLE_VARIANTS`)
- Modify: `.claude/agents/graphics-designer.md` (pick `weekly` style for `note_type='weekly_brief'`)
- Test: `tests/test_graphics_prompt.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_graphics_prompt.py
from src.graphics.prompt import build_prompt, STYLE_VARIANTS


def test_weekly_style_exists_and_builds():
    assert "weekly" in STYLE_VARIANTS
    vb = {"topic": "Koalīcija un partijas", "headline": "Apstiprināta valdība",
          "stat": "5 % IKP", "metaphor_hint": "puzzle"}
    vm = {"metaphor": "interlocking puzzle pieces", "mood": "tension", "accent": "ink navy"}
    prompt = build_prompt(vb, vm, style_key="weekly")
    assert "Apstiprināta valdība" in prompt
    assert "navy" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_graphics_prompt.py -v`
Expected: FAIL (`"weekly" not in STYLE_VARIANTS`).

- [ ] **Step 3: Add the `weekly` style variant** to `STYLE_VARIANTS` in `src/graphics/prompt.py`:

```python
    "weekly": (
        "Editorial weekly-digest poster. Textured cream/beige paper background. "
        "Monochrome black condensed serif display typography. A thin ink-navy "
        "frame border runs just inside the edges, with a small ink-navy corner "
        "wordmark block (no text inside it). Ink-navy is the single accent color. "
        "Rule-of-thirds composition, generous negative space. 16:9. "
        "Mood: reflective, summarizing, analytical."
    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_graphics_prompt.py -v`
Expected: PASS.

- [ ] **Step 5: Update `graphics-designer.md`** — in step 3 ("Uzmeklē metaforu un sagatavo prompt"), replace the `build_prompt` call guidance with:

```python
from src.graphics.prompt import build_prompt, DEFAULT_STYLE
style_key = "weekly" if note_type == "weekly_brief" else DEFAULT_STYLE
prompt_text = build_prompt(visual_brief, vm, style_key=style_key)
```

Add a one-line note: "Nedēļas pārskatiem lieto `weekly` stilu (ink-navy rāmis); identitāte tomēr balstās CSS chrome — attēls ir bonuss."

- [ ] **Step 6: Commit**

```bash
git add src/graphics/prompt.py .claude/agents/graphics-designer.md tests/test_graphics_prompt.py
git commit -m "feat(weekly): WEEKLY_STYLE featured-image frame"
```

---

## Task 11: Wiki + CHANGELOG

**Files:**
- Modify: `wiki/operations/weekly-routine.md`
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Update `wiki/operations/weekly-routine.md`** — replace the "## 2. Nedēļas pārskats" section body with:

```markdown
## 2. Nedēļas pārskats

```python
from src.briefs import generate_weekly_brief
skeleton = generate_weekly_brief(week_start="YYYY-MM-DD")  # markers + deterministic data + movers SVG
```

Skeletu bagātina `@weekly-brief-writer` aģents (NE `@brief-writer` — tas ir daily).
Struktūra: Nedēļas stāsts → Nedēļā skaitļos → Kas kustējās (grafiks) → Nedēļas
galvenās tēmas → Pretrunas → Skats uz priekšu → Vizuālais brief. Saglabā ar
`store_context_note(note_type="weekly_brief", …)`.
```

- [ ] **Step 2: Prepend a CHANGELOG entry** to `wiki/CHANGELOG.md` (top of the entries):

```markdown
## 2026-06-01 — Nedēļas pārskats: atsevišķs formāts (saturs + vizuālais)

Nedēļas pārskats vairs nav daily klons. `generate_weekly_brief()` (iepriekš
orphaned) paplašināts ar week-over-week deltām, `<!-- WEEKLY_STATS -->` marķieri
un tēmu scaffold ar avotiem. Jauns `@weekly-brief-writer` aģents (koplietotie
noteikumi izvilkti `brief-shared-rules.md`). Render caur `_weekly_body.html.j2`
ar `.weekly-*` ink-navy chrome, mobile-first stat kartītēm un in-body movers
grafiku (roku-rakstīts SVG, `src/graphics/weekly_chart.py` — NE `brief_images`,
NE AI skaitļi). Featured image lieto `WEEKLY_STYLE` rāmi. Validācija
(`_validate_brief_structure`) atjaunota uz jauno sekciju kontraktu.

**Kāpēc SVG, ne matplotlib:** matplotlib nav default venv (sk. conftest xfail).
**Kāpēc grafiks ārpus brief_images:** `get_approved_image()` atgriež jaunāko
approved rindu per note_id — otrs attēls sajauktu featured-image izvēli.
```

- [ ] **Step 3: Final verification**

Run: `bash scripts/check.sh`
Expected: ruff clean, all pytest green (incl. new weekly tests), site smoke passes.

- [ ] **Step 4: Commit**

```bash
git add wiki/operations/weekly-routine.md wiki/CHANGELOG.md
git commit -m "docs(weekly): update routine + CHANGELOG for weekly redesign"
```

---

## Self-Review (completed by plan author)

**Spec coverage:** Story/stats/movers/themes/pretrunas/skats sections → Tasks 2,7. Distinct featured style → Task 10. Visual template + mobile CSS → Tasks 8,9. Separate agent + shared rules → Tasks 4,5. Validation → Task 3. Chart-outside-`brief_images` (bug 1) → Task 6 docstring + Task 7. Validation-together (bug 2) → Task 3. SVG-as-file (bug 3) → Tasks 6,7. CSS identity not AI (bug 4) → Tasks 9,10. Delta edge cases (bug 5) → Task 1. Wiki/CHANGELOG → Task 11. All covered.

**Placeholder scan:** No TBD/TODO; every code step has complete code. The `<!-- AGENT: -->` string is intentional skeleton content, not a plan placeholder.

**Type consistency:** `_weekly_movers` returns `{id,name,party,count,delta}` — used identically in Tasks 2,7 and the chart (`{name,party,count,delta}` subset) in Task 6. `make_movers_svg(movers, coalition)` signature consistent Tasks 6,7. `_parse_weekly_stats` keys (`positions/votes/contradictions/top_topic/top_party`) match the marker emitted in Task 2 and consumed in Task 8 template. Consistent.
```
