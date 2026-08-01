# Saeima Bills Phase 1B-ii — wiki/laws auto-render + politiķa profila sekcija + base_law_slug backfill

**Datums**: 2026-04-27
**Vecāku spec**: [`2026-04-22-saeima-bills-design.md`](./2026-04-22-saeima-bills-design.md) — Saeima Bills tracker pilnais dizains
**Iepriekšējais paciņa**: Phase 1B-i (master @ `42b2375`, 2026-04-27) — bills detail page + bills-list 3. subtab + vote-card cross-link + Step 0 P14 motif fix
**Sekojošās paciņas**: Phase 1C (aģenta prompt + pozīciju auto-link + runbook), Phase 1.5 (selektīvs vēsturisks re-scrape iesniedzēju populēšanai)

---

## 1. Mērķis

Phase 1B-ii sasaista bills datus ar publisko likumu vidi (`wiki/laws/`):

- **`base_law_slug` retro-backfill** populē šo nullable kolonnu visiem 118 esošajiem bills, izsaucot `_resolve_base_law_slug()` (helperis no Phase 1A).
- **`wiki/laws/<slug>.md` saturs auto-paplašina** ar BILLS-SYNC-AUTO marķiera bloku, kas saraksto attiecīgā likuma aktīvos likumprojektus.
- **Publiskā vietne `/likumi/<slug>.html`** kļūst rendered no `wiki/laws/<slug>.md` (33 jaunas lapas) — sasniedzami caur "Saistītais bāzes likums" linka detail lapā un caur navigāciju.
- **Politiķa profila Likumprojekti sekcija** — conditional render (parādās tikai, kad `saeima_bill_politicians` junction populēta priekš šī politiķa). Šobrīd tukša visiem; lights up automātiski, kad Phase 1C live aģents ievada datus.
- **Naming fix**: `wiki/laws/likumi.md` un `wiki/index.md` semantiski pareizi ("Likumi", ne "Likumprojekti").
- **`upsert_bill()` integrācija**: turpmāk jaunie bills no aģenta plūsmas automātiski iegūst `base_law_slug` (idempotents — esoši bills nepieskaras).

## 2. Apjoms

### 2.1 Iekļauts Phase 1B-ii

| # | Komponente | Faili |
|---|---|---|
| 0 | `base_law_slug` retro-backfill skripts | `scripts/backfill_base_law_slug.py` (jauns) |
| 1 | `upsert_bill` integrācija ar `_resolve_base_law_slug` | `src/saeima.py` patch |
| 2 | wiki/laws BILLS-SYNC-AUTO marķiera writeback | `src/wiki.py` (`_render_law_bills_block` jauns + `wiki_sync` hook) |
| 3 | `templates/likums.html.j2` jauns + `_generate_law_pages` | `src/generate.py` + jauns templātais |
| 4 | "Saistītais bāzes likums" bloks detail lapā | `templates/likumprojekts.html.j2` + `_fetch_bill_detail` patch |
| 5 | Politiķa profila Likumprojekti sekcija (conditional) | `templates/politician.html.j2` + `_fetch_politician_detail` patch |
| 6 | wiki naming fix | `wiki/laws/likumi.md` + `wiki/index.md` (vai abu generators) |
| 7 | CHANGELOG + final smoke + commit | `wiki/CHANGELOG.md` |

### 2.2 Atstāts Phase 1C

- `.claude/agents/saeima-tracker.md` aģenta prompt update (steps 2/3/5.5)
- Pozīciju auto-link regex `NNNN/Lp14` pakas summary tekstā
- `wiki/operations/saeima-bills.md` runbook
- CLAUDE.md Pipeline Invariant 12 (bill_id/current_stage write-only via append_bill_stage)

### 2.3 Atstāts Phase 1.5 (optional)

- Selektīvs vēsturisks agendu re-scrape iesniedzēju populēšanai 30-50 politiski svarīgākajiem likumprojektiem
- Triggered by: pretrunu detektora vajadzība redzēt ilgtermiņa iesniedzēju paterni

### 2.4 Ārpus Phase 1 (Phase 2/3)

- Priekšlikumu autoru sekcija detail lapā (Phase 2 — priekšlikumu scrape)
- Debate stenogrammas (Phase 3)

## 3. Datu modelis (bez izmaiņām)

Phase 1B-ii **neievieš nekādas DB shēmas izmaiņas**. Visas tabulas un kolonnas eksistē kopš Phase 1A:

- `saeima_bills.base_law_slug TEXT` — nullable, šobrīd visiem 118 NULL
- `saeima_bill_politicians` junction — eksistē, tukša
- `_resolve_base_law_slug(motif)` helperis — eksistē, neizsaukts

## 4. Marķiera konvencija

### 4.1 Pattern

Esošais `src/wiki.py:99-100` SYNC-AUTO pattern (politiķu synthesis blocks):

```python
_SYNC_START = "<!-- SYNC-AUTO -->"
_SYNC_END = "<!-- /SYNC-AUTO -->"
```

Phase 1B-ii ievieš paralēlu pattern bills blokiem:

```python
_BILLS_SYNC_START = "<!-- BILLS-SYNC-AUTO -->"
_BILLS_SYNC_END = "<!-- /BILLS-SYNC-AUTO -->"
```

Atšķirīgs prefix novērš sajaukšanos. Pattern ir vienkāršs open + slash close (kā esošais) — atšķiras no master spec § 6.2.1 ieteiktā START/END style; spec atjauno tā, lai atbilst.

### 4.2 Bloka saturs

```markdown
<!-- BILLS-SYNC-AUTO -->
## Aktuālie likumprojekti šajā likumā

| Bill nr | Nosaukums | Stadija | Datums |
|---|---|---|---|
| [1315/Lp14](/likumprojekti/1315-lp14.html) | Grozījumi par 5% IKP | 3.lasījums (pieņemts) | 2026-04-23 |
| [1098/Lp14](/likumprojekti/1098-lp14.html) | Iepirkumu vienkāršošana | 1.lasījums (noraidīts) | 2026-04-25 |
<!-- /BILLS-SYNC-AUTO -->
```

Empty state (likumam nav saistītu bills):
```markdown
<!-- BILLS-SYNC-AUTO -->
## Aktuālie likumprojekti šajā likumā

_Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā._
<!-- /BILLS-SYNC-AUTO -->
```

### 4.3 Rakstīšanas plūsma

`src/wiki.py::_render_law_bills_block(slug, db)` (jauns):
1. SELECT bills WHERE `base_law_slug=?` ORDER BY `last_updated_at DESC`
2. Build markdown bloks (tabula vai empty state)
3. Read `wiki/laws/<slug>.md`
4. Replace existing `<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->` ar jauno saturu, vai pievieno faila beigās ja marķieris vēl nav
5. Write atpakaļ tikai ja saturs mainījies (idempotents bytewise)

`wiki_sync()` flow integrācija: pievieno iter pār 33 wiki/laws failiem (izņemot `likumi.md` indeksu) un izsauc `_render_law_bills_block` katram.

## 5. `base_law_slug` retro-backfill

### 5.1 Skripts `scripts/backfill_base_law_slug.py`

```python
def backfill_base_law_slug():
    """Iterē pār saeima_bills WHERE base_law_slug IS NULL.
    
    Match avots: title + motif teksts (no jaunākā saistītā saeima_votes.motif).
    Idempotents: re-run uz pilnu DB = same final state.
    """
    db = get_db()
    rows = db.execute("""
        SELECT b.id, b.document_nr, b.title, v.motif
        FROM saeima_bills b
        LEFT JOIN saeima_votes v ON v.bill_id = b.id
        WHERE b.base_law_slug IS NULL
        GROUP BY b.id
        ORDER BY b.id
    """).fetchall()
    
    matched, unmatched = 0, 0
    for r in rows:
        match_text = f"{r['title']} {r['motif'] or ''}"
        slug = _resolve_base_law_slug(match_text)  # Phase 1A helperis
        if slug:
            db.execute("UPDATE saeima_bills SET base_law_slug=? WHERE id=?", (slug, r['id']))
            matched += 1
        else:
            unmatched += 1
    db.commit()
    
    print(f"Matched: {matched}, Unmatched: {unmatched}")
    coverage_pct = matched / (matched + unmatched) * 100 if (matched + unmatched) else 0
    print(f"Coverage: {coverage_pct:.1f}%")
    if coverage_pct < 30:
        print("WARN: zema match coverage. Apsver Phase 1.5 manuālo pārklasifikāciju.")
```

### 5.2 Acceptance

- Skripts palaiž tīri uz dzīvās DB
- Matched count > 0; unmatched count atklāts info logā
- Coverage <30% rada warn (info-only, neradoš failure)
- Re-run produces identisku stāvokli (idempotents — `WHERE base_law_slug IS NULL` filter aizsargā jau matched rindas)

### 5.3 Aģenta integrācija

`src/saeima.py::upsert_bill()` patch:
- Pievieno `base_law_slug` kolonnu argumentam (Optional[str], default None)
- Ja `base_law_slug=None` un `title` pieejams, izsauc `_resolve_base_law_slug(title)` un saglabā tā rezultātu
- Idempotents: ja bill jau eksistē ar `base_law_slug`, neaizvieto

Tā jaunie bills no live aģenta plūsmas (Phase 1C) automātiski iegūst `base_law_slug` bez manuālā re-run.

## 6. wiki/laws → publiskais HTML

### 6.1 Templātais `templates/likums.html.j2`

```jinja
{% extends "base.html.j2" %}
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
      <a class="pagehead-metric pagehead-metric-link" href="{{ law.likumi_lv_url | safe_url }}" target="_blank" rel="noopener">
        <span class="pagehead-metric-label">Avots</span>
        <span class="pagehead-metric-value">likumi.lv ↗</span>
      </a>
      {% endif %}
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Likumprojekti</span>
        <span class="pagehead-metric-value">{{ law.bills | length }}</span>
      </div>
    </div>
  </header>
</section>

<div class="law-content">
  {{ law.body_html | safe }}
</div>
{% endblock %}
```

`law.body_html` — markdown rendered ar esošo `markdown` lib + sanitized ar `bleach` (drošības SEC-01 pattern). BILLS-SYNC-AUTO bloks ir markdown daļa, tāpēc renderē automātiski.

### 6.2 Datu fetcher

`src/generate.py::_fetch_law_pages(db) -> list[dict]`:
- Iterē `wiki/laws/*.md` (skip `likumi.md` indekss)
- Katram failam: extract title from H1 (`# Title` rinda; nav YAML frontmatter)
- Parse "Likumi.lv:" linka rindu (`**Likumi.lv:** https://...`)
- Read body, render markdown → sanitize ar `bleach` (esošais `_sanitize_html` pattern `src/generate.py`)
- SELECT bills WHERE `base_law_slug=slug` (count + minimālais bill data ar slug, document_nr) priekš metric un per-likuma sadaļas
- Return list ar slug, title, likumi_lv_url, body_html, bills (count + linki)

`_generate_law_pages(db, env, output_dir)`:
- mkdir `output_dir/likumi/`
- Iter `_fetch_law_pages` results
- Render `templates/likums.html.j2` katram, write `<slug>.html`

### 6.3 Hook secība `generate_public_site`

```
... existing ...
_generate_law_pages(db, env, atmina_dir)        # Phase 1B-ii — pirms bill pages
_generate_bill_pages(db, env, atmina_dir)        # Phase 1B-i
_generate_politician_pages(...)                   # ar bills_involved no Phase 1B-ii
... existing ...
```

Law pages PIRMS bills pages, lai detail page "Saistītais bāzes likums" linki rezolvē. Politician pages PĒC abiem, lai bills_involved data + linki rezolvē.

## 7. Detail page "Saistītais bāzes likums" bloks

### 7.1 `_fetch_bill_detail` patch

Pievieno divus laukus output dict:
- `base_law_slug` (jau pieejams `saeima_bills` kolonnā)
- `base_law_title` — lookup no filesystem `wiki/laws/<slug>.md` H1 rindas (cache māgusīgi pa procesu, jo 33 lapas × N bills citādi rada redundant disk I/O). Helperis `_load_law_titles_cache()` parse vienreiz un return dict[slug, title].

### 7.2 Template

`templates/likumprojekts.html.j2` papildu sekcija aiz [Iesniedzēji], pirms [Saites]:

```jinja
{% if bill.base_law_slug %}
<section class="bill-detail-base-law">
  <h2>Saistītais bāzes likums</h2>
  <p>Šis likumprojekts groza: <a href="../likumi/{{ bill.base_law_slug }}.html">{{ bill.base_law_title or bill.base_law_slug }}</a></p>
</section>
{% endif %}
```

## 8. Politiķa profila Likumprojekti sekcija

### 8.1 `_fetch_politician_detail` patch

Pievieno `bills_involved` lauku:
```python
bills_involved = []
for r in db.execute("""
    SELECT DISTINCT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
           b.current_stage, b.current_status, b.last_updated_at,
           bp.role, bp.amendment_nr,
           (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
           b.institutional_submitter
    FROM saeima_bills b
    JOIN saeima_bill_politicians bp ON bp.bill_id = b.id
    WHERE bp.politician_id = ?
    ORDER BY b.last_updated_at DESC
""", (pid,)).fetchall():
    bills_involved.append(dict(r) | {"slug": _bill_slug(r["document_nr"])})
```

### 8.2 Template

`templates/politician.html.j2` jauna sekcija (zem esošajām):

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

### 8.3 Profile-stats-bar conditional

Pievieno jauns butons profile-stats-bar, conditional:
```jinja
{% if bills_involved %}
<button class="profile-stat" onclick="showProfileTab('likumprojekti', this)" data-tab="likumprojekti">
  <span class="profile-stat-value">{{ bills_involved|length }}</span>
  <span class="profile-stat-label">Likumprojekti</span>
</button>
{% endif %}
```

(Šobrīd nevienam politiķim sekcija/butons neredzēs — junction tukša. 1C lights it up.)

## 9. wiki naming fix

### 9.1 `wiki/laws/likumi.md`

Šis fails tiek auto-regenerated. Fix avots ir generators (likely `src/wiki.py` vai `src/generate.py` build script). Atrod un atjauno:
- H1: "Likumprojekti — Indekss" → "Likumi — Indekss"
- Description: "**33** likumprojekti" → "**33** likumi"
- Tabulas heading "Likums | Saistītie balsojumi" — paliek nemainīgs

### 9.2 `wiki/index.md`

Indeksa rinda: "[[laws/likumi|Likumprojekti]] — 34 likumprojekti" → "[[laws/likumi|Likumi]] — 33 likumi". Šis fails arī auto-regenerated; atrod ģeneratoru un atjauno.

(Skaitlis "34" iekļāva `likumi.md` pašu indeksa failu; pareizais skaits ir 33 likumi.)

## 10. Testi (`tests/test_phase_1b_ii.py` jauns vai pievieno `test_generate_bills.py`)

### 10.1 base_law_slug backfill

- `test_backfill_base_law_slug_matches_known_law` — fixture ar bill ar title/motif, kas satur "Imigrācijas likumā" → backfilled `base_law_slug='imigracijas-likums'`
- `test_backfill_base_law_slug_idempotent` — re-run uz tiem pašiem datiem = nav UPDATE darbību
- `test_backfill_base_law_slug_no_match_logs` — bill bez atbilstoša likuma → paliek NULL, count'ē kā unmatched

### 10.2 wiki BILLS-SYNC-AUTO

- `test_render_law_bills_block_with_bills` — bills exist → marker bloks ar tabulas rindām
- `test_render_law_bills_block_empty_state` — no bills → marker bloks ar "nav aktīvu" tekstu
- `test_render_law_bills_block_idempotent_bytes` — divreiz palaists produces identisku content (no temp file noise)
- `test_render_law_bills_block_appends_when_marker_missing` — wiki/laws fails bez marķiera → tiek pievienots faila beigās

### 10.3 `_generate_law_pages`

- `test_generate_law_pages_emits_correct_count` — fixture wiki/laws/<slug>.md ar marker bloks → renderē N HTML failus
- `test_generate_law_pages_renders_likumi_lv_link` — fixture ar `Likumi.lv:` rindu → HTML satur target="_blank" linka
- `test_generate_law_pages_handles_missing_marker` — fails bez BILLS-SYNC-AUTO marķiera (vēl nav atjaunots) → renderē body bez bills sadaļas, no error

### 10.4 Detail page bāzes likums

- `test_likumprojekts_template_includes_base_law_link_when_set` — bill ar `base_law_slug` → section rendered ar pareizo linka
- `test_likumprojekts_template_no_base_law_when_null` — bill bez `base_law_slug` → section absent

### 10.5 Politiķa profila

- `test_politician_profile_likumprojekti_section_when_data_present` — junction populated priekš politiķa → section parādās ar bill_card grid
- `test_politician_profile_no_likumprojekti_section_when_empty` — junction empty → section absent (DOM nav `id="profile-bills-section"`)

### 10.6 `upsert_bill` integrācija

- `test_upsert_bill_resolves_base_law_slug_for_new_bill` — `upsert_bill` izsaukums ar title satur "Imigrācijas likumā" → DB rinda ar `base_law_slug='imigracijas-likums'`
- `test_upsert_bill_preserves_existing_base_law_slug_on_re_call` — re-call uz tā paša document_nr ar citu title nepārraksta esošo `base_law_slug`

### 10.7 Smoke

- `python scripts/backfill_base_law_slug.py` palaiž tīri ar matched/unmatched report
- `python -m src.wiki` (vai esošais wiki sync entry-point) atjaunina BILLS-SYNC-AUTO 33 wiki/laws failos
- `python -m src.generate` 0 errors, `output/atmina/likumi/*.html` ir 33 failu
- Detail page bills ar populated `base_law_slug` rāda working link
- Politiķa profile sekcija conditional render strādā

## 11. Riski un mitigācijas

| Risks | Mitigācija |
|---|---|
| `_resolve_base_law_slug` low coverage (<30%) zem nedaudz dažādo likuma nosaukumu variācijām | Backfill skripts ziņo coverage; manuāla pārklasifikācija ir Phase 1.5 darbs. Phase 1B-ii nepiedīsts ja zema coverage. |
| BILLS-SYNC-AUTO marķiera regen ievieš diff'us atomaiski citiem wiki sync rakstītājiem | `_render_law_bills_block` raksta tikai ja `base_law_slug` populēts; failu wiki/laws/likumi.md indeksu atstāj tukšu (nav per-bill referenced). Read-write ar `\n` newline normalization (CRLF tolerance Windows). |
| Politiķa profila tukšā sekcija piesārņo DOM esošajiem politikiem | Conditional `{% if bills_involved %}` aizsargā; profile-stats-bar butons arī conditional. Nav DOM rinda bez datiem. |
| Naming fix var saplīst esošos `[[wiki-link]]` references | Wiki linka mērķis ir `laws/likumi` slug, kas paliek nemainīgs; tikai display teksts mainās. Obsidian links neszbird. |
| `_generate_law_pages` failure ja wiki/laws/<slug>.md trūkst frontmatter vai nepareiza struktūra | Try/except per fails ar warn; skip uz nākamo. Smoke test pārbauda visu 33 failu produkciju. |
| `upsert_bill` integrācija ar `_resolve_base_law_slug` ievada neparedzētu I/O bibliotēkā | Helperis ir tīrs (regex match pret cached map); bez I/O bez DB hits. Performance neutral. |

## 12. Akceptances kritēriji

- `python scripts/backfill_base_law_slug.py` palaiž tīri; produces matched/unmatched report
- `python -m pytest tests/test_phase_1b_ii.py -q` — visi jaunie testi zaļi
- `python -m pytest tests/ -q` — 162+ esošie testi nesabrūk (Phase 1B-i regression check)
- `python -m src.generate` — 0 errors; `output/atmina/likumi/` ir 33 HTML failu; `output/atmina/likumprojekti/` joprojām 118 (vai vairāk)
- 33 `wiki/laws/<slug>.md` failos parādās BILLS-SYNC-AUTO bloks
- Manuāla acu pārbaude lokāli (`serve.py`):
  - `/likumi/imigracijas-likums.html` (vai cits) renderē body + bills tabula (ja bills saistīti)
  - `/likumprojekti/<slug>.html` ar populated base_law_slug rāda "Saistītais bāzes likums" sekciju ar working link
  - Klikšķis no detail page uz law page strādā un atpakaļ
  - `wiki/laws/likumi.md` un `wiki/index.md` rāda "Likumi" (ne "Likumprojekti")
  - Politiķa profile lapa ar tukšu junction nerāda Likumprojekti sekciju (no DOM artifacts)

## 13. Atkarības starp paciņām

```
Phase 1A (DONE) → Phase 1B-i (DONE @42b2375) → Phase 1B-ii (THIS) → Phase 1C
                                                       ↓
                                          base_law_slug populated → wiki/laws cross-ref live
                                                       ↓
                                          junction empty → politiķa sekcija slēpta līdz 1C
                                                       ↓
                                          Phase 1C: aģenta prompt populē junction live
```

Phase 1B-ii merge nepieprasa nekādu shēmas izmaiņu Phase 1A faili. Tikai jauni helperi un esošo skriptu integrācijas.

## 14. Dokumentācija

- `wiki/CHANGELOG.md` ieraksts ar shēmas/UI delta (jauni `/likumi/<slug>.html`, base_law_slug populated count, sekcija conditional)
- Master spec § 6.2.1 marķiera konvencija atjaunina (`<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->`, ne START/END)
- `wiki/operations/saeima-bills.md` runbook joprojām atlikts Phase 1C (aģenta plūsma + manuālas operācijas)
