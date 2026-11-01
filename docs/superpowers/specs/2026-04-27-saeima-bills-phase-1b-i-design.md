# Saeima Bills Phase 1B-i — UI dizains (bills-list + detail + vote cross-link)

**Datums**: 2026-04-27
**Vecāku spec**: [`2026-04-22-saeima-bills-design.md`](./2026-04-22-saeima-bills-design.md) — Saeima Bills tracker pilnais dizains
**Iepriekšējais paciņa**: Phase 1A (commit `64f1790` master) — schema + helperi + backfill
**Sekojošās paciņas**: Phase 1B-ii (wiki/laws auto-render + politiķa profila Likumprojekti sekcija + `base_law_slug` retro-backfill), Phase 1C (aģenta prompt + pozīciju auto-link + runbook)

---

## 1. Mērķis

Phase 1B-i atver Saeimas likumprojektu DB publikai. Ražo:

- **Bills detail lapas** `/likumprojekti/<slug>.html` — viena lapa katram no 91+ ierakstītajiem `saeima_bills` ar pilnu stadiju timeline, iesniedzējiem un balsotāju partiju sadalījumu.
- **Bills-list 3. subtab** uz `/balsojumi.html#bills-list` — filtrējama grid kartiņu, kas atspoguļo visus likumprojektus, ar topic/status/bill_type filtriem un teksta meklēšanu.
- **Vote-card cross-link** — esošajās balsojumu kartiņās `document_nr` kļūst par iekšēju saiti uz attiecīgā bill detail lapu (papildus jau esošajai ārējai `titania.saeima.lv` saitei).

Šī ir vienīgā paciņa, kas atver bills datus publikai. Pirms Phase 1B-i atmina lietotāji datus var redzēt tikai caur SQL.

## 2. Apjoms

### 2.1 Iekļauts Phase 1B-i

| # | Komponente | Faili |
|---|---|---|
| 1 | Bills detail lapa | `templates/likumprojekts.html.j2` |
| 2 | Bills-list grid 3. subtab | `templates/balsojumi.html.j2` patch |
| 3 | Atkārtoti izmantojams kartiņas macro | `templates/_bill_card.html.j2` |
| 4 | Datu fetcher + lapu ģenerācija | `src/generate.py` (`_fetch_bills`, `_fetch_bill_detail`, `_generate_bill_pages`) |
| 5 | CSS klases | `assets/style.css` (~80 rindas) |
| 6 | P14 motif gap fix (Step 0) | `src/saeima.py` `_DOCUMENT_NR_RE` paplašināšana + `scripts/backfill_saeima_bills.py` re-run |
| 7 | Sitemap papildinājums | `src/generate.py` `_generate_sitemap` patch |
| 8 | Snapshot + struktūras testi | `tests/test_generate_bills.py` |

### 2.2 Nav iekļauts (atstāts Phase 1B-ii)

- "Saistītais bāzes likums" bloks detail lapā
- `wiki/laws/<slug>.md` auto-render uz `/likumi/<slug>.html` ar `BILLS-SYNC` markieri
- Politiķa profila "Likumprojekti" sekcija (junction `saeima_bill_politicians` patreiz tukša pēc Phase 1A backfill)
- `base_law_slug` retro-backfill esošajiem 91 bills no motif teksta
- Iesniedzēju retro-backfill no vēsturiskajām agendām

### 2.3 Nav iekļauts (Phase 1C / Phase 2 / vēlāk)

- Pozīciju auto-link regex `NNNN/Lp14` summary tekstā (1C)
- Aģenta prompt `.claude/agents/saeima-tracker.md` paplašinājums (1C)
- Runbook `wiki/operations/saeima-bills.md` (1C)
- Priekšlikumu autoru sekcija detail lapā (Phase 2 — junction patreiz nav populated)
- Selektīvs vēsturisks re-scrape (Phase 1.5)
- Debate stenogrammas (Phase 3)

## 3. URL un failu izkārtojums

```
output/atmina/
├── balsojumi.html              ← patched: 3. subtab #bills-list + vote-card iekšējs cross-link
├── likumprojekti/
│   ├── 1315-lp14.html
│   ├── 1098-lp14.html
│   ├── 952-lm14.html
│   └── ...                     ← 91+ HTML failu (pēc Step 0: 94+)
├── politiki/<slug>.html        ← bez izmaiņām šajā paciņā
└── sitemap.xml                 ← patched: pievienots /likumprojekti/*
```

**Slug formula**: `document_nr.lower().replace("/", "-")` → `"1315/Lp14"` → `"1315-lp14"`.

**Detail page assets prefiksa**: `{% set assets_prefix = "../" %}` (matches `templates/politician.html.j2:3` konvenciju). Saites uz politiķiem detail lapā: `../politiki/<slug>.html`.

## 4. Datu slānis (`src/generate.py`)

### 4.1 `_fetch_bills(db) -> list[dict]`

Returns visi bills, kas tiek renderēti gan grid'ā, gan kā index detail lapām:

```python
{
    "id": int,
    "document_nr": str,                  # "1315/Lp14"
    "slug": str,                         # "1315-lp14"
    "bill_type": str,                    # "Lp14" | "Lm14" | "P14"
    "title": str,
    "summary": str | None,
    "topic": str | None,
    "current_stage": str,
    "current_status": str,               # "procesā" | "pieņemts" | "noraidīts" | "atsaukts"
    "first_seen_at": str,                # ISO datetime
    "last_updated_at": str,
    "institutional_submitter": str | None,
    "submitter_count": int,              # no junction
    "stage_count": int,
    "vote_count": int,
}
```

SQL forma: viens SELECT no `saeima_bills` ar trim LEFT JOIN-counted aggregates (`saeima_bill_politicians`, `saeima_bill_stages`, `saeima_votes`) GROUP BY `bill_id`. ORDER BY `last_updated_at DESC`.

### 4.2 `_fetch_bill_detail(db, bill_id) -> dict`

Returns viss vajadzīgais detail lapai:

```python
{
    **fetch_bills_row,                   # visas pamata kolonnas
    "stages": [
        {
            "stage_name": str,
            "stage_result": str | None,
            "stage_date": str,
            "amendment_nr": str | None,
            "vote_id": int | None,
            "vote_summary": str | None,
            "total_par": int | None,
            "total_pret": int | None,
            "total_atturas": int | None,
            "faction_breakdown": [...]   # reuse compute_faction_breakdown()
        },
        ...
    ],
    "submitters_individual": [           # no junction WHERE role='submitter'
        {"slug": str, "name": str, "party": str | None}
    ],
    "amendment_authors": [],             # tukšs Phase 1
    "external_document_url": str | None, # no jebkura saistīta saeima_votes.document_url
}
```

`stages` ORDER BY `stage_date ASC, id ASC` (chronological).

### 4.3 `_generate_bill_pages(db, env, output_dir)`

Iterē pār `_fetch_bills`, katram izsauc `_fetch_bill_detail` un renderē `templates/likumprojekts.html.j2`. Raksta uz `output_dir / "likumprojekti" / f"{slug}.html"`. Maps `output_dir` (`Path` objekts) sanāca jau augstāk pieņemts `_generate_*` funkcijām.

### 4.4 Hook punkts

`generate_public_site(...)` izsauc `_generate_bill_pages(db, env, output_dir)` **pirms** `_generate_politician_pages(...)`. Phase 1B-i tas vēl nav strikti vajadzīgs (politician page Likumprojekti sekcijas nav), bet 1B-ii jau pieprasa šo secību, lai politician profila linki rezolvē.

### 4.5 `_fetch_votes` patch

Pievieno LEFT JOIN `saeima_bills` un select `bills.id AS bill_id`, `bills.document_nr AS bill_doc_nr`. `bill_slug` aprēķina Python pusē. Tas ļauj vote-card template render iekšējo cross-link.

## 5. UI: detail lapa (`templates/likumprojekts.html.j2`)

### 5.1 Layout (visiem bill_type)

```
┌────────────────────────────────────────────────────────────────┐
│ pagehead-section                                                │
│   pagehead-kicker: "14. Saeima · {Likumprojekts|Lēmuma proj.|Paziņojums}"
│   pagehead-h1: {title}                                          │
│   pagehead-metrics: [document_nr] [topic] [current_status]     │
└────────────────────────────────────────────────────────────────┘

[Summary block]                ← {% if bill.summary %}
  serif 18px, max 3 rindas

[Stadiju timeline]
  vertikāla, mono+kompakta:
  ─── iesniegts ─────────── 2026-02-10
   ●  1.lasījums  pieņemts  2026-03-05  [53/32]    ← klikšķ → ../balsojumi.html#vote-{id}
   ●  2.lasījums  pieņemts  2026-04-01  [67/20]
   ●  3.lasījums  pieņemts  2026-04-23  [71/18]

[Iesniedzēji]                 ← viena kolonna 1B-i
  · institucionāls (ja institutional_submitter ≠ NULL)
  · individuāli politiķi (linki uz ../politiki/<slug>.html)

[Balsotāju sadalījums]        ← {% if bill.stages[-1].faction_breakdown %}
  pēdējās stadijas frakciju strip (reuse balsojumi.html komponentes)

[Saites]
  · Oriģinālais dokuments titania.saeima.lv ↗
  · (Per-stadijas balsojumu linki jau ir timeline; atsevišķs "visi balsojumi" linka nav vajadzīgs 1B-i)
```

**Conditional rendering pēc `bill_type`:**
- **Lp14**: timeline pilna lasījumu sekvence; pagehead-kicker "Likumprojekts"
- **Lm14**: timeline parasti viena vai divas stadijas (`tiesneša_amats` / `procesuāls` / `Lm14 cits`); pagehead-kicker "Lēmuma projekts"
- **P14**: timeline 1-2 stadijas (`iesniegts` + `paziņojuma_balsojums`); pagehead-kicker "Paziņojums"

### 5.2 Mobilā (≤760px)

- Timeline paliek vertikāla (jau ir)
- Iesniedzēji un balsotāju strip dabīgi collapse uz vienu kolonnu

### 5.3 Empty states

- Bill bez summary: skip block
- Bill bez stadijām (theoretical, šāds neeksistē DB): "Stadiju nav reģistrētas"
- Bill bez individuāliem iesniedzējiem un bez `institutional_submitter`: "Iesniedzējs nav reģistrēts"
- Bill bez balsotāju strip pēdējā stadijā (procedurāls bez `vote_id`): skip block

## 6. UI: bills-list 3. subtab (`templates/balsojumi.html.j2` patch)

### 6.1 Subtab bāra

```html
<div class="subtab-bar">
  <button class="subtab-btn active" onclick="window.switchTab('votes-list')" data-tab="votes-list">Balsojumi</button>
  <button class="subtab-btn" onclick="window.switchTab('votes-matrix')" data-tab="votes-matrix">Matrica</button>
  <button class="subtab-btn" onclick="window.switchTab('bills-list')" data-tab="bills-list">Likumprojekti</button>
</div>
```

### 6.2 Filtru bāra (zem subtab, `bills-list-tab` div)

- **Tēmas** multi-select dropdown (reuse `setupMultiSelect` no esošā JS)
- **Statuss** severity-style buttons (visi / procesā / pieņemts / noraidīts / atsaukts)
- **Bill tips** pill toggles (Lp14 / Lm14 / P14)
- **Teksta meklēšana** input — substring match pa `title` + `document_nr`

Default sort: `last_updated_at DESC`. (Sort dropdown var atstāt 1B-ii — ne kritisks 1B-i.)

### 6.3 Grid

`{% from "_bill_card.html.j2" import bill_card %}` un iterē pār `bills` ar `data-*` atribūtiem filtru aplikācijai.

### 6.4 JS extension

Pievieno `applyBillsFilters()` funkciju, kas mimic `applyFilters()` patternu no esošā votes-list JS. `switchTab()` pievieno trešo case.

## 7. UI: vote-card cross-link (`templates/balsojumi.html.j2:131-140` patch)

**Pirms:**
```jinja
{% if v.document_url %}
<a href="{{ v.document_url | safe_url }}" target="_blank" rel="noopener">Likumprojekts{% if v.document_nr %} ({{ v.document_nr }}){% endif %} ↗</a>
{% endif %}
```

**Pēc:**
```jinja
{% if v.bill_id and v.bill_slug %}
<a href="likumprojekti/{{ v.bill_slug }}.html">{{ v.document_nr }}</a> ·
{% endif %}
{% if v.document_url %}
<a href="{{ v.document_url | safe_url }}" target="_blank" rel="noopener">titania.saeima.lv ↗</a>
{% endif %}
```

105 votes (ar `bill_id NOT NULL`) iegūst iekšējo linku. 34 procedurālie (NULL `document_nr`) saglabā tikai ārējo (vai nekādu, ja `document_url` arī NULL).

## 8. Step 0: P14 motif gap fix

### 8.1 Konteksts

Phase 1A backfill izveidoja 0 P14 bills, lai gan DB ir 5 P14 balsojumi (HANDOFF Phase 0.7 punkts 6). Iemesls: `_DOCUMENT_NR_RE` `src/saeima.py` prasa parenthesized formātu `(NNN/P14)`, bet daļa P14 motifu izmanto bez paēzēm.

### 8.2 Fix

`src/saeima.py` paplašināt `_DOCUMENT_NR_RE`:
```python
_DOCUMENT_NR_RE = re.compile(r"\(?(\d+)\s*/\s*(Lp14|Lm14|P14)\)?")
```

Atjaunināti unit testi:
- `test_resolve_bill_from_motif_parenthesized_p14`
- `test_resolve_bill_from_motif_unparenthesized_p14` ← jauns
- Mixed cases ar Lp14 paliek nemainīgi

### 8.3 Re-run backfill

`scripts/backfill_saeima_bills.py` ir idempotents (Phase 1A spec § 5.4). Re-run pēc fix:
- Pirms: 91 bills (80 Lp14 + 11 Lm14 + 0 P14), 105 stages
- Sagaidāms pēc: ≥1 P14 bill (precīzs skaits atkarīgs no unique document_nr count starp 5 P14 balsojumiem), atbilstošs jauns stages skaits
- Audit: `python scripts/audit_saeima_vote_results.py` 0 errors
- DB backup pirms re-run: jau eksistē (`data/atmina.db.pre-bills-backfill-20260427-102910.backup`)

## 9. CSS (~80 rindas, `assets/style.css`)

| Klase | Mērķis |
|---|---|
| `.bill-card-grid` | CSS Grid `auto-fill, minmax(320px, 1fr)`; gap matches `.vote-card` grid |
| `.bill-card` | padding, border, radius, hover state — match `.vote-card` |
| `.bill-card-header` | document_nr badge + bill_type pill + topic pill |
| `.bill-card-body` | h3 title (1.1rem) + summary (2-line ellipsis) |
| `.bill-card-footer` | current_stage badge + submitter line + counts |
| `.bill-pill-lp14` / `.bill-pill-lm14` / `.bill-pill-p14` | bill_type krāsu varianti |
| `.bill-detail-timeline` | vertikāla līnija + filled circles for completed stages |
| `.bill-detail-timeline-item` | datums + stadijas vārds + rezultāta badge + balsojuma counts |
| `.bill-detail-faction-grid` | reuse `.faction-strip` izkārtojumu — alias |

## 10. Sitemap (`src/generate.py::_generate_sitemap`)

Pievieno bills URLs sitemap.xml ģenerācijā. `lastmod` no `bill.last_updated_at`. `priority` 0.6 (zemāk par persons 0.8).

## 11. Testi (`tests/test_generate_bills.py`)

### 11.1 Datu funkcijas

- `test_fetch_bills_shape` — fixture DB ar 2 bills + stages + submitters → struct atgriezts pareizs, visi lauki present
- `test_fetch_bills_sort_by_last_updated` — kārtošana DESC pareiza
- `test_fetch_bill_detail_full_lp14` — Lp14 ar 4 stages + 2 submitters → pilna struktūra
- `test_fetch_bill_detail_handles_missing_summary` — bill bez summary → atgriež `summary=None`, citi lauki OK
- `test_fetch_bill_detail_handles_no_submitters` — bills bez junction rindām → `submitters_individual=[]`

### 11.2 Lapu ģenerācija

- `test_generate_bill_pages_emits_correct_count` — fixture ar N bills → N HTML failu pareizajā mapē
- `test_generate_bill_pages_uses_slug_filename` — `1315/Lp14` → `1315-lp14.html`

### 11.3 Template snapshots

- `test_likumprojekts_template_renders_lp14_full_lifecycle` — Lp14 ar visiem 4 stages snapshot
- `test_likumprojekts_template_renders_lm14_tiesneša` — Lm14 ar tiesneša_amats stadiju
- `test_likumprojekts_template_renders_p14_minimal` — P14 ar `iesniegts` + `paziņojuma_balsojums` (atkarīgs no Step 0 fix)

### 11.4 Balsojumi.html patch

- `test_balsojumi_renders_bills_subtab` — DOM contains `data-tab="bills-list"` + `id="bills-list-tab"`
- `test_vote_card_internal_link_when_bill_id` — vote ar `bill_id` → DOM contains `<a href="likumprojekti/...">`
- `test_vote_card_no_internal_link_when_null_bill_id` — vote ar NULL `bill_id` → tikai ārējais linka

### 11.5 Smoke

- `python -m src.generate` — 0 errors, `output/atmina/likumprojekti/` ir N+ failu
- Manuāli: `python serve.py` → atvērt `/balsojumi.html#bills-list`, klikšķēt detail, klikšķēt timeline → balsojums

## 12. Riski un mitigācijas

| Risks | Mitigācija |
|---|---|
| Step 0 P14 motif fix neatklāj visu — citi formāti var palikt | Audit `audit_saeima_vote_results.py` flag-ē unmatched. Ja >2 atlikušie, atvērt issue Phase 0.7 follow-up. |
| Vote-card cross-link rāda 404 ja bill nav ģenerēts | Conditional `{% if v.bill_id and v.bill_slug %}` aizsargā; tests verificē abus virzienus |
| 91 bills aug uz tūkstošiem (Phase 1.5) — server-rendered HTML kļūst liels | Pārmigrēt uz JSON-split arhitektūru, kā `pozicijas.html` (commits c424899/634d5af). Nav 1B-i risks. |
| Iesniedzēju junction tukša → detail lapā tukša sekcija | Empty state "Iesniedzējs nav reģistrēts"; 1B-ii pievieno `institutional_submitter` parsēšanu vēsturiskām ievadnēm |
| Esošais filtru JS (`setupMultiSelect`) konflikts ar jauno bills filter | Reuse esošo helperi; pārbaudīt nav globālo state collisions |
| Snapshot testi ir trausli pret CSS izmaiņām | Snapshot fokusē uz semantisko struktūru, ne pixel-perfect render. Asertē key DOM elementi un attribūti, nevis pilns HTML string. |

## 13. Akceptances kritēriji

- `python -m pytest tests/test_generate_bills.py -v` — visi testi zaļi
- `python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py -v` — 57+ esošie testi nesalūst
- `python scripts/audit_saeima_vote_results.py` — 0 errors
- `python -m src.generate` — 0 errors; `output/atmina/likumprojekti/*.html` N+ failu kur N≥91
- Manuāla acu pārbaude `serve.py`:
  - `/balsojumi.html#bills-list` rāda kartiņas, filtri strādā
  - klikšķis kartiņas → detail lapa rāda timeline + iesniedzējus
  - klikšķis timeline `1.lasījums` rinda → atgriež uz `/balsojumi.html#vote-{id}`
  - klikšķis vote-card `document_nr` linku → ved uz detail lapu
  - Lm14 detail (piem. `tiesneša_amats`) renderē bez Lp14 specifiskiem blokiem
  - P14 detail (pēc Step 0) renderē 2-stadiju timeline

## 14. Dokumentācija

`wiki/CHANGELOG.md` ieraksts tiek pievienots šajā paciņā ar īsu shēmas/UI delta. `wiki/operations/saeima-bills.md` runbook un `.claude/agents/saeima-tracker.md` aģenta prompt paliek 1C scope.

## 15. Atkarības starp paciņām

```
Phase 1A (DONE) → Phase 1B-i (THIS) → Phase 1B-ii → Phase 1C
                       ↓
              [base_law_slug=NULL accepted; UI "Saistītais bāzes likums" bloks tukšs]
                       ↓
                Phase 1B-ii backfills base_law_slug + writes wiki/laws BILLS-SYNC blocks
                       ↓
                Phase 1B-ii pievieno politiķa profila Likumprojekti sekciju
                       ↓
                Phase 1C raksta runbook + aģenta prompt + pozīciju auto-link
```

Phase 1B-i merge nepieprasa nevienu izmaiņu Phase 1A faili izņemot Step 0 `_DOCUMENT_NR_RE` paplašinājumu, kas ir backward-compatible ar esošajiem testiem.
