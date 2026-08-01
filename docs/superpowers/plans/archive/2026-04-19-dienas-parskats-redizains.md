# Dienas pārskata redizains — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refaktorēt dienas pārskatu uz skenējamu formātu — bullet-veida Galvenais, tabula Koalīcija vs Opozīcija sadaļā, adaptīva Pretrunas sadaļa ar tīru formātu, metadata footer ar stats un atjaunošanas laiku.

**Architecture:** Skelets `src/briefs.py` kļūst tīrāks (noņem publiskos skaitļus, pievieno iekšējo HTML komentāru, pārveido Koalīcija vs Opozīcija par tabulu, jauna conditional Pretrunas sadaļa). Render-time `src/generate.py` pievieno stats footer datus (ieskaitot `saeima_votes` skaits). Template `templates/blog-post.html.j2` renderē footer bloku. Aģenta `.claude/agents/brief-writer.md` instrukcijas aizliedz publisko DB enum/ID noplūdi.

**Tech Stack:** Python 3.11+, SQLite, pytest, Jinja2, `markdown` library (ar `tables`, `fenced_code`), CSS vanilla.

**Spec:** `docs/superpowers/specs/2026-04-19-dienas-parskats-redizains-design.md`

---

## Task 1: Atjaunina test fixtures un esošos testus

**Konteksts:** Esošie `tests/test_briefs.py` testi pārbauda stats rindu `## Galvenais` sadaļā (`"3 dokumenti"`, `"3 jaunas pozīcijas"`, `"0 Saeimas balsojumi"`, `"1 pretrunas"`). Pēc Task 2 skelets šos skaitļus vairs nerakstīs — testi salūzīs. Atjaunināšanai jāiet PIRMS skeleta izmaiņām, lai TDD cikls strādā: jauni testi izsaka jauno prasību, tad skelets pielāgots.

**Files:**
- Modify: `tests/test_briefs.py:130-160` (esošie stats testi)
- Modify: `tests/test_briefs.py:18-102` (fixture — pievieno `saeima_votes` tabulu)

- [ ] **Step 1: Pievieno `saeima_votes` tabulu briefs_db fixturei**

Modify `tests/test_briefs.py` `briefs_db` fixture `executescript` bloks — pievieno pirms pēdējā `);` (aptuveni 76. līnija):

```python
        CREATE TABLE saeima_votes (
            id INTEGER PRIMARY KEY,
            vote_date TEXT
        );
```

Un arī `empty_briefs_db` fixturei (aptuveni 117. līnija):

```python
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
```

- [ ] **Step 2: Aizvieto stats-bullet testus ar HTML komentāra testiem**

Replace `tests/test_briefs.py:130-144` — aizstāj `test_contains_document_counts`, `test_contains_claim_count`, `test_contains_contradiction_count`:

```python
    def test_galvenais_has_stats_comment(self, briefs_db):
        """Stats live in <!-- DIENAS STATS --> comment for agent context, not as
        a visible bullet. Comment is in DOM but not rendered to users."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "<!-- DIENAS STATS" in brief
        assert "3 dokumenti" in brief  # still in comment
        assert "2 web" in brief  # still in comment
        assert "3 pozīcijas" in brief  # still in comment
        assert "1 pretruna" in brief  # still in comment

    def test_galvenais_has_no_visible_stats_bullet(self, briefs_db):
        """The old stats bullet is gone — agent's bullet-point narrative
        replaces it. Skeleton leaves ## Galvenais empty (except comment)."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # No visible bullet with stats pattern
        assert "- **3 dokumenti**" not in brief
        assert "**3 jaunas pozīcijas**" not in brief
```

- [ ] **Step 3: Aizvieto `test_empty_day_returns_zeros`**

Replace `tests/test_briefs.py:151-154`:

```python
    def test_empty_day_has_zero_stats_comment(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2025-01-01")
        assert "<!-- DIENAS STATS" in brief
        assert "0 dokumenti" in brief
```

- [ ] **Step 4: Aizvieto `test_empty_db`**

Replace `tests/test_briefs.py:156-159`:

```python
    def test_empty_db_renders(self, empty_briefs_db):
        brief = generate_daily_brief(db_path=empty_briefs_db, date="2026-04-07")
        assert "Dienas analīze" in brief
        assert "<!-- DIENAS STATS" in brief
```

- [ ] **Step 5: Run tests, verify they FAIL (skelets vēl neizmainīts)**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py -v`

Expected: `test_galvenais_has_stats_comment` un līdzīgi FAIL ar `AssertionError: assert "<!-- DIENAS STATS" in brief`. Tas apstiprina, ka testi izsaka JAUNU prasību, ko Task 2 izpildīs.

- [ ] **Step 6: Commit failing tests**

```bash
git add tests/test_briefs.py
git commit -m "test(briefs): expect HTML stats comment instead of visible bullet"
```

---

## Task 2: Skelets — Galvenais bez stats, HTML komentārs, LIMIT 7

**Konteksts:** `src/briefs.py:118-122` raksta stats bulletu `## Galvenais` sadaļā. Pēc šīs task: šis tiek aizstāts ar HTML komentāru aģenta iekšējai orientācijai; stats paši parādīsies footer'ā no render-time query. Aktīvākie politiķi LIMIT mainās no 12 uz 7.

**Files:**
- Modify: `src/briefs.py:54-63` (LIMIT 12 → 7)
- Modify: `src/briefs.py:118-122` (stats bullet → HTML komentārs)

- [ ] **Step 1: Maina LIMIT Aktīvākie politiķi query**

Open `src/briefs.py:54-63`. Atrodi `active = db.execute("""` bloku. Maina `LIMIT 12` uz `LIMIT 7` (62. līnija):

```python
    active = db.execute("""
        SELECT p.name, p.party, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT c.topic) as topics
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) = ?
          AND c.claim_type = 'position'
          AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive')
        GROUP BY p.id ORDER BY cnt DESC LIMIT 7
    """, (date,)).fetchall()
```

- [ ] **Step 2: Noņem vote_count query — pārcelts uz render-time**

Open `src/briefs.py:43-46`. **Noņem** šīs 4 līnijas pilnīgi (vote_count tagad dzīvo render-time footer query):

```python
    vote_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE date(stated_at) = ? AND claim_type = 'saeima_vote'",
        (date,),
    ).fetchone()[0]
```

- [ ] **Step 3: Aizvieto Galvenais stats bullet ar HTML komentāru**

Open `src/briefs.py:118-122`. Replace:

```python
    lines = [f"# Dienas analīze — {date}\n"]
    lines.append("## Galvenais\n")
    lines.append(f"- **{doc_count} dokumenti** ({web_count} web + {x_count} Twitter/X), "
                 f"**{position_count} jaunas pozīcijas** + **{vote_count} Saeimas balsojumi**, "
                 f"**{contradiction_count} pretrunas**")
```

Ar:

```python
    lines = [f"# Dienas analīze — {date}\n"]
    lines.append("## Galvenais\n")
    # Iekšējs aģenta orientācijas signāls — HTML komentārs paliek DOM-ā, bet
    # browseris to nerāda. Publiskais skaitļu footer tiek renderēts template-
    # līmenī no src/generate.py:_fetch_blog_posts().
    plural_pos = "pozīcija" if position_count == 1 else "pozīcijas"
    plural_pret = "pretruna" if contradiction_count == 1 else "pretrunas"
    lines.append(
        f"<!-- DIENAS STATS (iekšēja piezīme aģentam; nav renderēta publikai): "
        f"{doc_count} dokumenti ({web_count} web + {x_count} Twitter/X) · "
        f"{position_count} {plural_pos} · "
        f"{contradiction_count} {plural_pret} -->"
    )
```

- [ ] **Step 4: Run tests from Task 1, verify they PASS**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py::TestGenerateDailyBrief -v`

Expected: visi PASS. `test_galvenais_has_stats_comment` iziet, jo HTML komentārs satur stats; `test_galvenais_has_no_visible_stats_bullet` iziet, jo nav vecās `- **N dokumenti**` līnijas.

- [ ] **Step 5: Commit**

```bash
git add src/briefs.py
git commit -m "feat(briefs): stats kā HTML komentārs (ne bullet), Aktīvākie top 7"
```

---

## Task 3: Skelets — Koalīcija vs Opozīcija tabulas formā

**Konteksts:** `src/briefs.py:225-257` ģenerē trīs `**Koalīcija (N):** name (party) — topics; ...` paragrāfus, kuri ir "garā desā". Pārveidojam par 4-rindu tabulu: Bloks, Pozīcijas, Partijas, Galvenie runātāji, Dominējošās tēmas.

**Files:**
- Modify: `src/briefs.py:225-257`
- Add tests: `tests/test_briefs.py` (jauns klases)

- [ ] **Step 1: Write failing test for coalition table**

Add to `tests/test_briefs.py` (pēc `TestDailyBriefStructure` klases):

```python
class TestCoalitionTable:
    """Koalīcija vs Opozīcija tagad ir tabula, ne 3 paragrāfi."""

    def test_koalicija_section_uses_table(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Koalīcija vs Opozīcija" in brief
        # Tabula header ar kolonnām Bloks, Pozīcijas
        assert "| Bloks |" in brief
        assert "| Pozīcijas |" in brief

    def test_koalicija_has_coalition_row(self, briefs_db):
        """JV Siliņa fixturē ir coalition. Tabulai jāietver Koalīcija rinda."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Tabulas rindā jāparādās "Koalīcija" bloka nosaukumam un "JV" īsajam
        # partijas nosaukumam.
        assert "| Koalīcija |" in brief
        assert "JV" in brief

    def test_koalicija_has_opposition_row(self, briefs_db):
        """LPV Šlesers fixturē ir opposition."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "| Opozīcija |" in brief
        assert "LPV" in brief

    def test_koalicija_no_old_paragraph_format(self, briefs_db):
        """Vecās `**Koalīcija (N pozīcijas):**` formāts ir pagājis."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "**Koalīcija (" not in brief
        assert "**Opozīcija (" not in brief
```

- [ ] **Step 2: Run tests, verify they FAIL**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py::TestCoalitionTable -v`

Expected: FAIL ar `AssertionError: assert "| Bloks |" in brief` — esošais skelets raksta `**Koalīcija (N):**` formātu, nevis tabulu.

- [ ] **Step 3: Aizvieto Koalīcija vs Opozīcija ģenerēšanu**

Open `src/briefs.py:238-257`. Atrodi `if koa_rows or opo_rows or out_rows:` bloku. Replace visu bloku (ieskaitot `_summarize` funkciju un trīs `**Bold (N):**` lines) ar:

```python
    # Neitrāli/audience politiķi (journalist, influencer, neutral) — tie
    # nav koalīcijas/opozīcijas daļa, bet publicē pozīcijas. Pievienojam
    # kā atsevišķu rindu, ja eksistē.
    neutral_rows = db.execute("""
        SELECT p.name, p.party, c.topic
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) = ?
          AND c.claim_type = 'position'
          AND p.relationship_type IN ('journalist','influencer','neutral')
        ORDER BY c.id
    """, (date,)).fetchall()

    if koa_rows or opo_rows or out_rows or neutral_rows:
        from src.briefs import _short_party  # local import lai izvairītos no ciklikā

        def _bloc_summary(rows, label):
            """Atgriež (pozīciju skaits, partiju īso nos. string,
            top 3 runātāji ar skaitu, top 3 tēmas) vienam blokam."""
            if not rows:
                return None
            # Politiķu skaits pa personām
            by_person: dict[tuple, int] = {}
            by_party: dict[str, int] = {}
            by_topic: dict[str, int] = {}
            for r in rows:
                key = (r["name"], r["party"] or "")
                by_person[key] = by_person.get(key, 0) + 1
                if r["party"]:
                    by_party[r["party"]] = by_party.get(r["party"], 0) + 1
                if r["topic"]:
                    by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1

            # Top 3 politiķi pēc pozīciju skaita
            top_people = sorted(by_person.items(), key=lambda x: (-x[1], x[0][0]))[:3]
            people_str = ", ".join(f"{name.split()[-1]} ({cnt})"
                                    for (name, _), cnt in top_people)

            # Partiju īsie nosaukumi, sakārtoti pēc aktivitātes
            parties_sorted = sorted(by_party.items(), key=lambda x: -x[1])
            parties_str = ", ".join(_short_party(p) for p, _ in parties_sorted) or "—"

            # Top 3 tēmas
            topics_sorted = sorted(by_topic.items(), key=lambda x: -x[1])[:3]
            topics_str = ", ".join(t for t, _ in topics_sorted) or "—"

            return (len(rows), parties_str, people_str or "—", topics_str)

        lines.append("\n## Koalīcija vs Opozīcija\n")
        lines.append("| Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas |")
        lines.append("|-------|-----------|----------|-------------------|-------------------|")

        for label, rows in [
            ("Koalīcija", koa_rows),
            ("Opozīcija", opo_rows),
            ("Ārpus Saeimas", out_rows),
            ("Neitrāli", neutral_rows),
        ]:
            summary = _bloc_summary(rows, label)
            if summary is None:
                continue
            cnt, parties, people, topics = summary
            lines.append(f"| {label} | {cnt} | {parties} | {people} | {topics} |")
        lines.append("")
```

- [ ] **Step 4: Run tests, verify they PASS**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py::TestCoalitionTable -v`

Expected: visi 4 testi PASS. Arī esošie testi `TestDailyBriefStructure::test_has_coalition_section` paliek zaļi (sadaļa eksistē).

- [ ] **Step 5: Run pilno test suite**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py -v`

Expected: visi PASS.

- [ ] **Step 6: Commit**

```bash
git add src/briefs.py tests/test_briefs.py
git commit -m "feat(briefs): Koalīcija vs Opozīcija kā tabula (Bloks/Pozīcijas/Partijas/Runātāji/Tēmas)"
```

---

## Task 4: Skelets — Pretrunas sadaļa ar tīru formātu

**Konteksts:** Pašreiz skelets neradara atsevišķu `## Pretrunas` sadaļu. Aģents to manuāli injektē Spriedžu tabulā ar raw `#NN (severity_enum)` formātu, kas noplūst publiskā. Šis task pievieno tīru, adaptīvu sadaļu.

**Files:**
- Modify: `src/briefs.py` (pēc `## Spriedzes` bloka, pirms `db.close()`)
- Modify: `tests/test_briefs.py` fixture (pievieno `claims.source_url` abām rindām kontradikcijai)
- Add tests: `tests/test_briefs.py::TestPretrunasSection`

- [ ] **Step 1: Write failing test for Pretrunas section**

Add to `tests/test_briefs.py` (pēc `TestCoalitionTable`):

```python
class TestPretrunasSection:
    """Jauna ## Pretrunas sadaļa — tikai ja dienā ir contradictions."""

    def test_pretrunas_section_rendered(self, briefs_db):
        """briefs_db fixturē ir 1 pretruna 2026-04-07 dienā."""
        # Pievieno pretrunas severity un summary
        db = sqlite3.connect(briefs_db)
        db.execute(
            "ALTER TABLE contradictions ADD COLUMN severity TEXT"
        )
        db.execute(
            "ALTER TABLE contradictions ADD COLUMN summary TEXT"
        )
        db.execute(
            "UPDATE contradictions SET severity='minor_shift', "
            "summary='Valainis 6.apr. kritizē valsts finansējumu; 13.apr. piedāvā valsts pārvaldību.' "
            "WHERE id = 1"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Pretrunas" in brief

    def test_pretrunas_severity_is_lv(self, briefs_db):
        """minor_shift → 'neliela novirze' (nav raw enum)."""
        db = sqlite3.connect(briefs_db)
        db.execute("ALTER TABLE contradictions ADD COLUMN severity TEXT")
        db.execute("ALTER TABLE contradictions ADD COLUMN summary TEXT")
        db.execute("UPDATE contradictions SET severity='minor_shift', summary='x' WHERE id = 1")
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "neliela novirze" in brief
        assert "minor_shift" not in brief

    def test_pretrunas_no_db_id_leak(self, briefs_db):
        """Raw DB ID #NN nav publiskā tekstā."""
        db = sqlite3.connect(briefs_db)
        db.execute("ALTER TABLE contradictions ADD COLUMN severity TEXT")
        db.execute("ALTER TABLE contradictions ADD COLUMN summary TEXT")
        db.execute("UPDATE contradictions SET severity='minor_shift', summary='x' WHERE id = 1")
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Nav `#1`, `Pretruna #1`, utt.
        assert "Pretruna #" not in brief
        assert "#1" not in brief.split("## Pretrunas")[1][:500]

    def test_pretrunas_section_absent_on_empty_day(self, briefs_db):
        """Diena bez pretrunām — sadaļa nav."""
        brief = generate_daily_brief(db_path=briefs_db, date="2025-01-01")
        assert "## Pretrunas" not in brief
```

- [ ] **Step 2: Atjaunina fixturi, lai atbalsta Pretrunas sadaļu**

Modify `tests/test_briefs.py` `briefs_db` fixture — atjaunina `contradictions` tabulu (aptuveni 45-52 līnijas), lai ietvertu `severity` un `summary` kolonnas no sākuma:

```python
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            claim_old_id INTEGER,
            claim_new_id INTEGER,
            topic TEXT,
            severity TEXT,
            summary TEXT,
            detected_at TEXT
        );
```

Un tāpat `empty_briefs_db` fixturei.

Tad atjaunina `INSERT INTO contradictions` 97. līnijā:

```python
        INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, severity, summary, detected_at)
            VALUES (1, 1, 1, 3, 'NATO', 'minor_shift',
                    'Siliņa 5.apr. atbalsta; 7.apr. iebilst pret to pašu.',
                    '2026-04-07');
```

Un noņem `ALTER TABLE` rindas no Step 1 testiem (tagad kolonnas ir fixture-level) — testu kodi kļūst vienkāršāki:

```python
class TestPretrunasSection:
    def test_pretrunas_section_rendered(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Pretrunas" in brief

    def test_pretrunas_severity_is_lv(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "neliela novirze" in brief
        assert "minor_shift" not in brief

    def test_pretrunas_no_db_id_leak(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "Pretruna #" not in brief

    def test_pretrunas_section_absent_on_empty_day(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2025-01-01")
        assert "## Pretrunas" not in brief
```

- [ ] **Step 3: Run tests, verify they FAIL**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py::TestPretrunasSection -v`

Expected: `test_pretrunas_section_rendered` FAIL ar `assert "## Pretrunas" in brief`.

- [ ] **Step 4: Pievieno Pretrunas sadaļu skeletam**

Open `src/briefs.py`. Pēc Spriedžu bloka (286. līnija, pirms `db.close()`), pievieno:

```python
    # Pretrunas — tīrs formāts bez raw DB ID un severity enum noplūdes.
    # Aģentam AIZLIEGTS ievelk šīs rindas Spriedžu tabulā vai rakstīt
    # "Pretruna #NN" redzamā tekstā (skat .claude/agents/brief-writer.md).
    _SEVERITY_LV = {
        "minor_shift": "neliela novirze",
        "direct_contradiction": "tieša pretruna",
        "reversal": "reversija",
    }
    contra_rows = db.execute("""
        SELECT c.id, c.topic, c.severity, c.summary,
               c.claim_old_id, c.claim_new_id,
               p.name, p.party,
               c_old.source_url AS old_url, c_old.stated_at AS old_date,
               c_new.source_url AS new_url, c_new.stated_at AS new_date
        FROM contradictions c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        LEFT JOIN claims c_old ON c.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON c.claim_new_id = c_new.id
        WHERE date(c.detected_at) = ?
        ORDER BY c.id
    """, (date,)).fetchall()

    if contra_rows:
        lines.append("\n## Pretrunas\n")
        lines.append("| Politiķis | Partija | Tēma | Veids | Apraksts | Avoti |")
        lines.append("|-----------|---------|------|-------|----------|-------|")
        for r in contra_rows:
            severity_lv = _SEVERITY_LV.get(r["severity"] or "", "pretruna")
            # Apraksts — pirmais paragrāfs, līdz 350 chars
            summary = (r["summary"] or "").split("\n\n", 1)[0].strip()
            if len(summary) > 350:
                summary = summary[:347].rstrip() + "…"
            # Avoti — formatē datumus no stated_at
            def _date_label(date_str: str | None) -> str:
                if not date_str:
                    return ""
                try:
                    parts = date_str[:10].split("-")
                    return f"{parts[2]}.{parts[1]}"
                except (IndexError, ValueError):
                    return ""
            old_label = _date_label(r["old_date"])
            new_label = _date_label(r["new_date"])
            old_link = f"[{old_label}]({r['old_url']})" if r["old_url"] and old_label else ""
            new_link = f"[{new_label}]({r['new_url']})" if r["new_url"] and new_label else ""
            if old_link and new_link:
                sources = f"{old_link} / {new_link}"
            elif old_link:
                sources = old_link
            elif new_link:
                sources = new_link
            else:
                sources = "—"
            lines.append(f"| {r['name']} | {r['party'] or ''} | {r['topic']} | "
                         f"{severity_lv} | {summary} | {sources} |")
        lines.append("")
```

- [ ] **Step 5: Run tests, verify they PASS**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py::TestPretrunasSection -v`

Expected: visi 4 PASS.

- [ ] **Step 6: Run pilno test suite un verify nekas nav salūzis**

Run: `.venv/Scripts/python -m pytest tests/test_briefs.py -v`

Expected: visi PASS.

- [ ] **Step 7: Commit**

```bash
git add src/briefs.py tests/test_briefs.py
git commit -m "feat(briefs): jauna ## Pretrunas sadaļa ar tīru formātu (severity LV, bez #ID)"
```

---

## Task 5: Render-time footer — `generate.py` stats query

**Konteksts:** `src/generate.py:1816-1909` `_fetch_blog_posts()` lasa context_notes, bet neaprēķina footer stats. Jāpievieno stats query pa katrai dienai + `updated_at_display` no `created_at`. Stats padod template.

**Files:**
- Modify: `src/generate.py:1816-1909` (`_fetch_blog_posts`)
- Add tests: `tests/test_generate.py` jauns klasas `TestBlogPostFooter`

- [ ] **Step 1: Write failing test for footer data**

Add to `tests/test_generate.py`:

```python
import sqlite3
import tempfile
import os
import pytest


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def generate_db():
    """Temp DB with schema needed for _fetch_blog_posts stats."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            scraped_at TEXT,
            platform TEXT
        );
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT, party TEXT, relationship_type TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            topic TEXT, stance TEXT, source_url TEXT,
            stated_at TEXT,
            claim_type TEXT NOT NULL DEFAULT 'position'
        );
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER, detected_at TEXT
        );
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY,
            note_type TEXT, content TEXT, topic TEXT,
            created_at TEXT, visual_brief_json TEXT
        );
        CREATE TABLE saeima_votes (
            id INTEGER PRIMARY KEY, vote_date TEXT
        );
        CREATE TABLE brief_images (
            id INTEGER PRIMARY KEY,
            note_id INTEGER, image_path TEXT, approved INTEGER
        );

        INSERT INTO tracked_politicians VALUES (1, 'X', 'JV', 'tracked');

        -- 2026-04-16 data: 3 docs (1 web, 1 twitter, 1 x_mention), 2 poz, 3 balsojumi, 1 pretr
        INSERT INTO documents VALUES (1, '2026-04-16', 'web');
        INSERT INTO documents VALUES (2, '2026-04-16', 'twitter');
        INSERT INTO documents VALUES (3, '2026-04-16', 'x_mention');
        INSERT INTO documents VALUES (4, '2026-04-16', 'saeima');  -- izslēgts
        INSERT INTO claims (opponent_id, topic, stated_at, claim_type)
            VALUES (1, 'NATO', '2026-04-16', 'position');
        INSERT INTO claims (opponent_id, topic, stated_at, claim_type)
            VALUES (1, 'ES', '2026-04-16', 'position');
        INSERT INTO contradictions (opponent_id, detected_at) VALUES (1, '2026-04-16');
        INSERT INTO saeima_votes (vote_date) VALUES ('2026-04-16'), ('2026-04-16'), ('2026-04-16');

        -- Brief ieraksts
        INSERT INTO context_notes (note_type, content, topic, created_at)
            VALUES ('daily_brief',
                '# Dienas analīze — 2026-04-16\n\nContent.\n\n## Aktīvākie politiķi\n| Politiķis |\n## Galvenās tēmas\n## Koalīcija vs Opozīcija\n',
                'dienas pārskats 2026-04-16',
                '2026-04-16 23:34:12');
    """)
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


class TestBlogPostFooter:
    def test_footer_has_doc_counts(self, generate_db):
        """3 docs (ne 4 — saeima izslēgta no doc_count)."""
        import sqlite3
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert len(posts) == 1
        post = posts[0]
        assert "footer" in post
        assert post["footer"]["doc_count"] == 3
        assert post["footer"]["web"] == 1
        assert post["footer"]["twitter"] == 1
        assert post["footer"]["mentions"] == 1

    def test_footer_has_position_count(self, generate_db):
        import sqlite3
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["positions"] == 2

    def test_footer_has_vote_count(self, generate_db):
        import sqlite3
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["votes"] == 3

    def test_footer_has_contradiction_count(self, generate_db):
        import sqlite3
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["contradictions"] == 1

    def test_footer_has_updated_display(self, generate_db):
        """created_at='2026-04-16 23:34:12' → '16.04.2026 23:34'."""
        import sqlite3
        from src.generate import _fetch_blog_posts
        db = sqlite3.connect(generate_db)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
        assert posts[0]["footer"]["updated"] == "16.04.2026 23:34"
```

- [ ] **Step 2: Run tests, verify they FAIL**

Run: `.venv/Scripts/python -m pytest tests/test_generate.py::TestBlogPostFooter -v`

Expected: FAIL ar `KeyError: 'footer'` — `_fetch_blog_posts` vēl nenoteic šo lauku.

- [ ] **Step 3: Pievieno stats query `_fetch_blog_posts` funkcijai**

Open `src/generate.py:1894`. Atrodi `posts.append({` bloku. Pirms tā pievieno stats query:

```python
        # Footer metadata — render-time aprēķins no DB. Skelets (briefs.py)
        # skaitļus nerada publiski; šie parādās zem satura template-līmenī.
        stats = db.execute("""
            SELECT
                (SELECT COUNT(*) FROM documents
                 WHERE date(scraped_at) = ?
                   AND platform IN ('web','twitter','x_mention')) AS doc_count,
                (SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ? AND platform = 'web') AS web_count,
                (SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ? AND platform = 'twitter') AS twitter_count,
                (SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ? AND platform = 'x_mention') AS mentions_count,
                (SELECT COUNT(*) FROM claims c JOIN tracked_politicians p ON c.opponent_id = p.id
                 WHERE date(c.stated_at) = ? AND c.claim_type = 'position'
                   AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive')
                ) AS position_count,
                (SELECT COUNT(*) FROM saeima_votes WHERE vote_date = ?) AS vote_count,
                (SELECT COUNT(*) FROM contradictions WHERE date(detected_at) = ?) AS contradiction_count
        """, (date_str,) * 7).fetchone()

        # Formatē created_at uz "DD.MM.YYYY HH:MM"
        updated_display = ""
        if created:
            try:
                from datetime import datetime as _dt
                # SQLite TEXT formāts: "2026-04-16 23:34:12" vai "2026-04-16T23:34:12"
                ts = created.replace("T", " ")[:16]  # "2026-04-16 23:34"
                dt = _dt.strptime(ts, "%Y-%m-%d %H:%M")
                updated_display = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                updated_display = created[:16] if created else ""

        footer = {
            "doc_count": stats["doc_count"],
            "web": stats["web_count"],
            "twitter": stats["twitter_count"],
            "mentions": stats["mentions_count"],
            "positions": stats["position_count"],
            "votes": stats["vote_count"],
            "contradictions": stats["contradiction_count"],
            "updated": updated_display,
        }
```

Tad `posts.append({...})` dict'ā pievieno `"footer": footer,` — piemēram, pēc `"headline": headline,`:

```python
        posts.append({
            "id": d["id"],
            "slug": date_str,
            "date": date_str,
            "weekday": weekday_lv,
            "title": title,
            "display_title": display_title,
            "type_label": type_label,
            "note_type": d.get("note_type"),
            "preview": preview,
            "content": content,
            "image_path": image_path,
            "image_filename": image_filename,
            "headline": headline,
            "footer": footer,
        })
```

- [ ] **Step 4: Run tests, verify they PASS**

Run: `.venv/Scripts/python -m pytest tests/test_generate.py::TestBlogPostFooter -v`

Expected: visi 5 PASS.

- [ ] **Step 5: Run pilno test suite**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`

Expected: visi PASS vai skip. Ja kāds neizturās — diagnose pirms iet tālāk.

- [ ] **Step 6: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): footer stats + atjaunots laiks render-time no DB"
```

---

## Task 6: Template + CSS footer bloks

**Konteksts:** Jaunais `post["footer"]` dict jārenderē HTML apakšā pirms prev/next navigation. CSS stilizē kā muted, mazāks fonts.

**Files:**
- Modify: `templates/blog-post.html.j2:55-58`
- Modify: `assets/style.css` (jauns bloks beigās vai pie `.brief-content`)

- [ ] **Step 1: Pievieno footer bloku template**

Open `templates/blog-post.html.j2:55`. Pēc `<div class="post-content">...</div>` bloka (56-57 līnijas), pirms `<div class="brief-footnav">` (59. līnija), pievieno:

```html
  {% if post.footer %}
  <hr class="brief-footer-sep">
  <p class="brief-footer">
    <strong>Pamatā:</strong>
    {{ post.footer.doc_count }} dokumenti ({{ post.footer.web }} web · {{ post.footer.twitter }} X · {{ post.footer.mentions }} mentions) ·
    {{ post.footer.positions }} {{ "jauna pozīcija" if post.footer.positions == 1 else "jaunas pozīcijas" }}
    {% if post.footer.votes %}
    · {{ post.footer.votes }} {{ "Saeimas balsojums" if post.footer.votes == 1 else "Saeimas balsojumi" }}
    {% endif %}
    ·
    {{ post.footer.contradictions }} {{ "pretruna" if post.footer.contradictions == 1 else "pretrunas" }}
    <br>
    <strong>Atjaunots:</strong> {{ post.footer.updated }} (Latvijas laiks)
  </p>
  {% endif %}
```

- [ ] **Step 2: Pievieno CSS klases**

Open `assets/style.css`. Atrodi `.brief-footnav` klasi (aptuveni 2677. līnija). Tieši PIRMS šīs klases pievieno:

```css
.brief-footer-sep {
  margin: 2.5rem 0 1rem;
  border: none;
  border-top: 1px solid var(--border);
}

.brief-footer {
  color: var(--text-muted);
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0 0 2rem;
}

.brief-footer strong {
  color: var(--text);
  font-weight: 600;
}
```

- [ ] **Step 3: Bump assets_version, lai cache nerādās**

Atrodi kur `assets_version` tiek uzstādīts. Run grep:

```bash
.venv/Scripts/python -c "import src.generate as g; print([x for x in dir(g) if 'version' in x.lower()])"
```

Tad atrodi `assets_version` izmantošanu:

```
grep -n assets_version src/generate.py | head
```

Ja tas ir uz `int(time.time())`, bump notiek automātiski nākamā `generate_public_site()` palaišanā — nav nekas jādara manuāli.

- [ ] **Step 4: Palaiž site generator un smoke-test blog post rendering**

Run:

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: `blog/: N blog posts` un nav exception'u.

- [ ] **Step 5: Manuāli pārbauda output/atmina/blog/2026-04-18.html**

Open `output/atmina/blog/2026-04-18.html` (diena bez Saeimas balsojumiem) un meklē `brief-footer`:

```bash
grep -A 4 "brief-footer" output/atmina/blog/2026-04-18.html | head -20
```

Expected: `<p class="brief-footer">` ar `Pamatā:` + `Atjaunots:` rindām. Saeimas balsojumu segments NAV šajā dienā (jo `votes == 0`).

- [ ] **Step 6: Manuāli pārbauda output/atmina/blog/2026-04-16.html (diena ar balsojumiem)**

```bash
grep -A 4 "brief-footer" output/atmina/blog/2026-04-16.html | head -20
```

Expected: satur `Saeimas balsojumi` segmentu (piem. "39 Saeimas balsojumi"). Precīzu skaitu pārbauda atsevišķi — pēc DB `SELECT COUNT(*) FROM saeima_votes WHERE vote_date='2026-04-16'`.

- [ ] **Step 7: Commit**

```bash
git add templates/blog-post.html.j2 assets/style.css
git commit -m "feat(templates): metadata footer bloks zem dienas pārskata (stats + atjaunots laiks)"
```

---

## Task 7: Brief-writer aģenta instrukciju atjauninājums

**Konteksts:** Aģents līdz šim rakstīja `## Galvenais` kā 3-5 teikumu paragrāfu, reizēm pārstrukturēja tabulas, reizēm izmantoja raw DB ID (`#24`) un severity enum (`minor_shift`). Jaunās instrukcijas: bullet-format, tabulu aizliegums, #NN/enum aizliegums.

**Files:**
- Modify: `.claude/agents/brief-writer.md:38-42`, `44-48`, `55-62`

- [ ] **Step 1: Maina Galvenais instrukcijas bullet-formātā**

Open `.claude/agents/brief-writer.md:39`. Replace:

```
- `## Galvenais` — after the stats bullet, write a **3-5 sentence paragraph** that tells the day's story. Use the `<!-- NARATĪVA MATERIĀLS -->` comment as raw material: which topics sparked cross-party conflict, who clashed with whom, what's the political significance. Delete the comment block when done.
```

Ar:

```
- `## Galvenais` — **3-5 bullet-punktus, katrs ar bold lead**. Skelets tagad ietver `<!-- DIENAS STATS -->` HTML komentāru (iekšēja piezīme par dienas apjomu — 533 dokumenti, 28 pozīcijas, utt.) un `<!-- NARATĪVA MATERIĀLS -->` bloku (tēmas, kas sparcināja konfliktu). Izmanto abus kā raw material. **SAGLABĀ** `<!-- DIENAS STATS -->` komentāru (tas ir daļa no brief metadata); **IZDZĒS** `<!-- NARATĪVA MATERIĀLS -->` kad esi to uzrakstījis par bullet-iem. Bullet format paraugs:
  - **Aizsardzība:** Braže (JV) un Sprūds (PRO) konsolidē 5% IKP līniju; Sprūds paplašina uz Mednieku savienības iesaisti.
  - **NA trīs paralēli naratīvi:** Pūpols atver airBaltic–Lufthansa, reemigrāciju pret trešvalstu darbaspēku un Ždanokas–Hezbollah saiti.
  - **Opozīcijas vienīgā balss:** Kulbergs (AS) kritizē Saeimu kā "balsošanas mašīnu".
```

- [ ] **Step 2: Aizliedz publiski rakstīt skaitļus un tabulu pārstrukturēšanu**

`brief-writer.md:31-37` (SAGLABĀ bloks). Replace:

```
- All `| Politiķis | Partija | Pozīcija | Avots |` tables — verbatim
- `## Koalīcija vs Opozīcija` section
- `## Spriedzes` table — verbatim
```

Ar:

```
- All `| Politiķis | Partija | Pozīcija | Avots |` tables — verbatim (NEVAR mainīt kolonnas)
- `## Koalīcija vs Opozīcija` tabula — verbatim (tagad ir 5-kolonnu tabula: Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas)
- `## Spriedzes` tabula — verbatim (6-kolonnu: Tips | Avots | Mērķis | Tēma | Apraksts | Saite)
- `## Pretrunas` tabula — verbatim (6-kolonnu: Politiķis | Partija | Tēma | Veids | Apraksts | Avoti). **AIZLIEGTS** pārveidot Spriedžu tabulā vai ievelk contradictions kā manuālas rindas.
```

Tad `brief-writer.md:41-42` (`PAPILDINI` bloks). Replace:

```
- `## Koalīcija vs Opozīcija` — rewrite the auto-generated lists into a **comparative synthesis** paragraph: where is the coalition internally divided, where does opposition find common ground, what are the fault lines.
```

Ar:

```
- `## Koalīcija vs Opozīcija` — **ZEM** skeleta tabulas pievieno 1-2 teikumu sintēzi: kur koalīcija iekšēji dalās, kur opozīcija atrod kopīgu pamatu, kādas partijas klusē. **NEPĀRRAKSTI** tabulu un **NEATMINIERĪBO** partiju politiķu sarakstus — tabula to jau rāda.
```

- [ ] **Step 3: Pievieno jaunas KRITISKAS SADAĻAS — aizliegums publiski rakstīt DB iekšējos laukus**

`brief-writer.md` 79-85 rinda (`**What is NOT in the brief:**` bloks). Pēc pēdējā `- No subjective adjectives...` pievieno:

```
- **NO DB iekšējiem ID vai enum vērtībām publiskā tekstā** (2026-04-19 papildu noteikums):
  - NEKAD: `Pretruna #24`, `#17`, `(minor_shift)`, `(direct_contradiction)`, `(reversal)`, `(6↔123)`, `(source_pid=65)`.
  - Ja jāatsaucas uz iepriekšēju pretrunu kontekstā — izmanto **aprakstošu** atsauci: "Valaiņa iepriekšējā airBaltic pretruna", NE "Pretruna #17".
  - `## Pretrunas` tabula tiek ģenerēta skeletā ar latviskiem severity nosaukumiem (neliela novirze / tieša pretruna / reversija) — NEIZMAINI tos.
- **NO skaitļiem par doc/position count publiskā tekstā** — tie nāk no render-time footer. Galvenais bullets fokusē uz naratīvu (kurš, ko, kāpēc), NE uz skaitļiem. Ja aģents grib izmantot skaitli, tas nāk no `<!-- DIENAS STATS -->` komentāra iekšējai kalibrācijai, NE rakstīts.
```

- [ ] **Step 4: Atjauno Self-Check sarakstu**

`brief-writer.md:50-60` (Self-Check Before Storing). Replace bullet `6`:

```
6. ✅ No `<!-- NARATĪVA MATERIĀLS` or `<!-- SINTĒZE:` comments remain (all consumed)
```

Ar:

```
6. ✅ No `<!-- NARATĪVA MATERIĀLS` or `<!-- SINTĒZE:` comments remain (all consumed)
6b. ✅ `<!-- DIENAS STATS -->` comment IS preserved (render-time footer relies on agent not deleting it; though technically render footer re-queries DB, the comment is agent's context and must stay)
6c. ✅ No `Pretruna #NN`, no raw enum (`minor_shift`, `reversal`, `direct_contradiction`), no `(a↔b)` DB reference syntax in any section
6d. ✅ `## Galvenais` contains ONLY bullet-points (lines starting `-`) + preserved HTML comment; NO prose paragraph under the heading
```

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/brief-writer.md
git commit -m "docs(agent): brief-writer — Galvenais bullets, tabulu aizliegums, DB enum/ID aizliegums"
```

---

## Task 8: Integration smoke-test un 2026-04-18 regenerate

**Konteksts:** Pēc skeleta + render izmaiņām, regenerate site un pārbauda, ka visi blog posti renderējas korekti. Manual review 2026-04-18 pārskatam — tekstuālā satura problēma (agrāk ierakstītais "Pretruna #24 (minor_shift)") paliks, kamēr aģents pārskatu pārraksta; bet skeleta + footer strādā jaunā formātā pār esošo saturu.

**Files:**
- Run: `generate_public_site()`
- Manual: atver blog posts

- [ ] **Step 1: Palaiž pilno site generator**

Run:

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: nav exception'u. Output: `blog/: 13+ blog posts`.

- [ ] **Step 2: Pārbauda footer 3 dienām (ar balsojumiem, bez, un robežgadījumu)**

Run:

```bash
for d in 2026-04-16 2026-04-18 2026-04-10; do
  echo "=== $d ==="
  grep -A 6 "brief-footer" "output/atmina/blog/$d.html" | head -10
done
```

Expected:
- `2026-04-16` — satur "Saeimas balsojumi"
- `2026-04-18` — NEsatur "Saeimas balsojumi"
- `2026-04-10` — robežgadījums (pārbaudām, ka renderējas)

- [ ] **Step 3: Pārbauda, ka 2026-04-18 vecais "Pretruna #24 (minor_shift)" bug PALIEK SATURĀ (agrākais aģenta saglabātais teksts)**

```bash
grep "Pretruna #24" output/atmina/blog/2026-04-18.html
```

Expected: satur — tas ir vecs aģenta saturs DB. Footer ir jauns (no render-time), bet aģenta kontents saglabāts. Lietotājam: kad aģents nākamo reizi ģenerē 2026-04-18 brief, tas tiks pārrakstīts ar tīru formātu.

Šī task punkts dokumentē: **skeleta + footer izmaiņas nepieskārs esošiem aģenta saglabātiem brief satura tekstiem**. Full regenerate prasa aģentu manuāli palaist.

- [ ] **Step 4: Verify HTML komentārs neparādās publiski (smoke check)**

```bash
grep "DIENAS STATS" output/atmina/blog/2026-04-18.html
```

Expected: **ja** 2026-04-18 brief ir re-generated pēc Task 2 → komentārs ir HTML avotā. Ja nav — esošais vecais saglabātais brief (pirms Task 2) HTML komentāru neietver. Tas ir OK — jauni briefi to ietvers.

- [ ] **Step 5: Run pilno test suite — end-to-end confirmation**

```bash
.venv/Scripts/python -m pytest tests/ -x -q
```

Expected: visi PASS.

- [ ] **Step 6: Final commit (ja output ir mainījies, piem. assets_version bump)**

```bash
git status
# Ja ir uncommitted changes output/ vai data/:
# output/ parasti NAV committed (pārbaudi .gitignore)
# Ja ir tikai assets/style.css cache bump — tā jau Task 6.
```

Ja nav nekā jauna — šis task beidzas tukšs. OK.

---

## Self-Review rezultāti

**Spec coverage:**
- §1 Galvenais bullets → Task 2 + Task 7
- §2 Aktīvākie top 7 → Task 2
- §3 Koalīcija vs Opozīcija tabula → Task 3 + Task 7
- §4 Spriedzes/Pretrunas adaptīvas → Task 4 + Task 7
- §5 Footer template-level → Task 5 + Task 6
- §Datu plūsma → Task 7 (aģenta atbildības)
- §Testēšanas kritēriji 1-8 → Task 1, 3, 4, 5, 8

**Gaps:** Nav.

**Type consistency:** `post["footer"]` dict keys (`doc_count`, `web`, `twitter`, `mentions`, `positions`, `votes`, `contradictions`, `updated`) konsekventi starp Task 5 (definēti), Task 6 (template lasa). `_SEVERITY_LV` mapping Task 4 (`minor_shift` → `neliela novirze`, utt.). Visi method signatures atbilst.

**Placeholder scan:** Nav TBD / TODO / "similar to..." / "add appropriate handling". Katrs code step satur pilnu kodu.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-19-dienas-parskats-redizains.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
