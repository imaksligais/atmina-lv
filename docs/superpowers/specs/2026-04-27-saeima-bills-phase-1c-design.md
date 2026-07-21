# Saeima Bills Tracker — Phase 1C Design (Orchestration & Glue)

> **Status:** Spec, 2026-04-27. Phase 1A/B-i/B-ii merged on master @ `c991de5` + post-fix `f8a9ff8`. This spec brainstormed in conversation, written here for review and to anchor the implementation plan.
> **Open questions resolved:**
> - `/likumi.html` index lapa **iekļauta** Phase 1C scope; top main nav entry **atstāts** (defer).
> - Step 2 numerācija: paplašināt esošo Step 2 (variants A), nevis pievienot Step 2.5.
> - Failure mode disciplīna: tier sistēma (variants B) — STOP+report tikai persistent corruption gadījumiem.
> - Auto-link implementation: Jinja2 filtrs (variants A), nevis preprocess.
> - `/likumi.html` saturs: mirror `/balsojumi.html#bills-list` pattern (variants B) + footer cross-link no `/balsojumi.html`.

---

## 0. Konteksts un mērķis

Phase 1A (`scripts/backfill_saeima_bills.py` + 5 helper funkcijas) un Phase 1B (UI templeiti + cross-linki) jau ir uz master. **Phase 1C nav new code path** — tas ir glue layer, kas pieslēdz jau gatavos helperus aģenta plūsmā un atklāj rezultātu UI, ko 1B templeiti jau pieņem.

Pēc 1C laidiena `@saeima-tracker` katra jauna sesija automātiski:
- Ievada `saeima_bills` rindas no agenda snapshot
- Aizpilda `saeima_bill_politicians` junction tabulu
- Saista katru balsojumu ar bill stage timeline
- Rezultējās politiķa profila Likumprojekti tabs un publiskās lapas atklāj saturu bez manuālas iejaukšanās.

---

## 1. Architecture overview

```
┌─ Operatorinstrukcija ──────────────────────────────────────────┐
│ .claude/agents/saeima-tracker.md   — Step 2 expand + Step 5    │
│ wiki/operations/saeima-bills.md    — runbook (jauns)           │
│ CLAUDE.md § Pipeline Invariants    — Invariant 12              │
└────────────────────────────────────────────────────────────────┘
                              ↓ aģents palaiž ar šo prompt
┌─ Datu plūsma ──────────────────────────────────────────────────┐
│ agenda snapshot ─→ parse_agenda_snapshot() → upsert_bill() ×N  │
│                  match_submitters_to_politicians() → junction  │
│ vote snapshot   ─→ store_vote() (jau strādā)                   │
│                  resolve_bill_from_motif() → append_bill_stage │
└────────────────────────────────────────────────────────────────┘
                              ↓ piepilda DB; UI to renderē
┌─ UI atklāšana ─────────────────────────────────────────────────┐
│ src/generate.py     — autolink_bills Jinja2 filtrs             │
│ output/atmina/      — /likumi.html index lapa (jauna)          │
│ /balsojumi.html     — footer link "Visi pamatlikumi (33)"      │
└────────────────────────────────────────────────────────────────┘
```

**Atomic order** (mazākā → lielākā riska): Invariant 12 → auto-link filtrs → /likumi.html → runbook → agent prompt. Agent prompt last, jo kods jāpaliek stabils, kad operators pārbauda live.

---

## 2. Agent prompt izmaiņas (`.claude/agents/saeima-tracker.md`)

### 2.1 Step 2 paplašinājums

Esošais Step 2 (`grep -oE '\./0/...' snapshot`) saglabājas kā **2.B**; **2.A** ievieto bills parse.

````markdown
### Step 2: Parse agenda — extract bills + voting URLs

The agenda snapshot from Step 1 holds BOTH:
  (a) the list of likumprojekti scheduled for this session (with submitters)
  (b) the URLs of the actual vote results pages.
Process both before moving to Step 3.

**Step 2.A: Parse bills + match submitters**

```python
from src.saeima import parse_agenda_snapshot, upsert_bill, match_submitters_to_politicians

with open('path/to/agenda_snapshot.md', encoding='utf-8') as f:
    snapshot_text = f.read()

agenda_bills = parse_agenda_snapshot(snapshot_text)
if not agenda_bills:
    print("WARN: parse_agenda_snapshot returned []. Likely HTML structure changed.")
    print("STOP — abort session, report to operator before proceeding.")
    raise SystemExit(1)

for ab in agenda_bills:
    bill_id = upsert_bill(
        db_path='data/atmina.db',
        document_nr=ab.document_nr,
        title=ab.title,
        bill_type=ab.bill_type,                      # 'Lp14' / 'Lm14' / 'P14'
        institutional_submitter=ab.institutional_submitter,
        # topic + base_law_slug auto-resolved by upsert_bill from title
    )
    matched, unmatched = match_submitters_to_politicians(
        db_path='data/atmina.db',
        bill_id=bill_id,
        submitter_names=ab.individual_submitters,
    )
    if unmatched:
        print(f"  unmatched submitters for {ab.document_nr}: {unmatched}")
        # Tier-2 deputy STOP rule (existing prompt §155) covers individuals.
        # Institutional submitter validation is prompt-side: see § 2.A.bis below.

    # Validate institutional submitter against canonical list (prompt rule).
    if ab.institutional_submitter and ab.institutional_submitter not in KNOWN_INSTITUTIONAL_SUBMITTERS:
        print(f"  STOP: unknown institutional submitter {ab.institutional_submitter!r} for {ab.document_nr}")
        print("  Add to agent prompt's canonical list before continuing.")
        raise SystemExit(1)
```

**Step 2.A.bis: Known institutional submitters (canonical list)**

Aģentam promptā fiksētais saraksts. Ja `parse_agenda_snapshot` atgriež citu vērtību, agents APSTĀJ un ziņo. Saraksts paplašināms tikai ar operatorā apstiprinājumu.

```python
KNOWN_INSTITUTIONAL_SUBMITTERS = {
    "Ministru kabinets",
    "Saeimas Prezidijs",
    # Saeimas komisijas
    "Tautsaimniecības, agrārās, vides un reģionālās politikas komisija",
    "Juridiskā komisija",
    "Sociālo un darba lietu komisija",
    "Aizsardzības, iekšlietu un korupcijas novēršanas komisija",
    "Cilvēktiesību un sabiedrisko lietu komisija",
    "Izglītības, kultūras un zinātnes komisija",
    "Valsts pārvaldes un pašvaldības komisija",
    "Budžeta un finanšu (nodokļu) komisija",
    "Eiropas lietu komisija",
    "Mandātu, ētikas un iesniegumu komisija",
    "Publisko izdevumu un revīzijas komisija",
    "Pieprasījumu komisija",
    "Ārlietu komisija",
    "Ilgtspējīgas attīstības komisija",
    # Konstit. iestādes
    "Latvijas Bankas padome",
    "Augstākā tiesa",
    "Valsts kontrole",
}
```

Šis saraksts dzīvo aģenta promptā kā **prompt rule**, nevis Python kods (master spec § 4.4 "agent discipline lemma" — diskpilīna ir aģenta atbildība, nevis koda guard). Operators paplašina prompt + (vajadzības gadījumā) `_parse_institutional_submitter` regex `src/saeima.py:490`, kad STOP signalizē.

**Step 2.B: Extract voting URLs (existing)**
```bash
grep -oE '\./0/[A-F0-9]{32}\?OpenDocument' agenda_snapshot.md | sort -u
```
````

### 2.2 Jauns Step 5: Link vote → bill stage

Pievieno PĒC esošā Step 4 (Parse and store vote):

````markdown
### Step 5: Link vote to bill stage

After each store_vote() returns vote_id, resolve which bill it advances and
write the stage row. This keeps `saeima_bills.current_stage` and the
denormalized timeline accurate.

```python
from src.saeima import resolve_bill_from_motif, append_bill_stage, _reading_from_motif
from src.db import get_db

db = get_db('data/atmina.db')

# vote_db_id is the integer returned by store_vote() in Step 4
doc_nr = resolve_bill_from_motif(vote.motif)
if doc_nr is None:
    print(f"  no bill match for motif {vote.motif!r} — vote stored without bill_id")
else:
    bill = db.execute("SELECT id FROM saeima_bills WHERE document_nr=?", (doc_nr,)).fetchone()
    if bill is None:
        print(f"  WARN: motif resolved to {doc_nr} but no bill row — Step 2 may have skipped it")
    else:
        stage_name = _reading_from_motif(vote.motif)  # may return 'nezināms'
        append_bill_stage(
            db_path='data/atmina.db',
            bill_id=bill['id'],
            stage_name=stage_name,
            stage_result=vote.result,
            stage_date=vote.date,
            vote_id=vote_db_id,
        )
        # append_bill_stage atomically links saeima_votes.bill_id and
        # updates saeima_bills.current_stage / current_status. Do NOT
        # write those columns by hand (CLAUDE.md Pipeline Invariant 12).
```

`stage_name='nezināms'` is acceptable — it's the visible signal that
the motif's reading wasn't classified. Don't invent a stage to fix it;
report unusual motifs back so the vocabulary can grow.
````

### 2.3 Failure mode tier (jauna sekcija pirms `## DO / DON'T`)

| Situation                                                     | Action                |
|---------------------------------------------------------------|-----------------------|
| Unknown institutional submitter (not in `KNOWN_INSTITUTIONAL_SUBMITTERS` prompt list) | STOP, ask operator    |
| Unknown deputy (not in `tracked_politicians.name_forms`)      | STOP, ask operator    |
| `parse_agenda_snapshot()` returns []                          | STOP, abort session   |
| `resolve_bill_from_motif()` returns None                      | log, store vote w/o bill_id |
| `_reading_from_motif()` returns 'nezināms'                    | log, append stage as-is |
| `upsert_bill()` raises ValueError on bill_type                | STOP, report          |

The first three create persistent silent corruption if ignored. The last three are recoverable per-row — the agent flow continues, operator reviews logs after the run.

### 2.4 Numerācijas plāns

| Esošais | Pēc 1C |
|---|---|
| Step 1: Open agenda | Step 1 (nemainās) |
| Step 2: Extract URLs | **Step 2: Parse agenda → bills + URLs** (A+B) |
| Step 3: For each URL | Step 3 (nemainās) |
| Step 3.5: Bill summary | Step 3.5 (nemainās) |
| Step 4: Parse and store | Step 4 (nemainās) |
| — | **Step 5: Link vote → bill stage** (jauns) |

DO/DON'T sekcija (rinda 157+) un Faction Codes / Law Reference Wiki paliek nemainīgas.

---

## 3. Auto-link Jinja2 filtrs (`src/generate.py`)

### 3.1 Filter implementation

```python
import re

_BILL_REF_RE = re.compile(r"\b(\d+)/(Lp14|Lm14|P14)\b")

def _autolink_bills_filter(text: str, bill_slugs: set[str] | None = None) -> str:
    """Wrap '1288/Lp14' style references in <a href="likumprojekti/<slug>.html">.

    Unknown document_nr (slug not in bill_slugs) preserved as plain text —
    no broken links. Caller must ensure input is trusted (claim summaries are
    plain Latvian text, not user-controlled HTML); template uses `| safe` after
    this filter. bill_slugs=None is graceful (no links); never crash on
    missing context.
    """
    if not text:
        return text or ""
    bill_slugs = bill_slugs or set()

    def _sub(m: re.Match) -> str:
        nr, suffix = m.group(1), m.group(2)
        slug = f"{nr}-{suffix.lower()}"
        if slug not in bill_slugs:
            return m.group(0)
        return f'<a href="likumprojekti/{slug}.html">{m.group(0)}</a>'

    return _BILL_REF_RE.sub(_sub, text)


# Register near existing filter setup (lines ~2990-2992):
env.filters["autolink_bills"] = _autolink_bills_filter
```

### 3.2 Templeit kontekstā padod `bill_slugs`

Build vienreiz `_render_atmina_pages()` sākumā:

```python
bill_slugs = {_bill_slug(b["document_nr"]) for b in bills}
# ... padod {"bill_slugs": bill_slugs, ...} katram render kontekstā kur claim summary parādās
```

### 3.3 Templeit lietojums

```jinja
{# Pirms #}
<p>{{ claim.summary }}</p>

{# Pēc #}
<p>{{ claim.summary | autolink_bills(bill_slugs) | safe }}</p>
```

Vietas, kur jāatjaunina (precīzs saraksts veidojas plānā):
- `templates/pretruna-detail.html.j2`
- `templates/politician.html.j2`
- `templates/pretrunas.html.j2`
- `templates/personas.html.j2`
- `templates/partija.html.j2`

### 3.4 Tests (`tests/test_autolink_bills.py`, jauns fails)

```python
def test_single_bill_match():
    out = _autolink_bills_filter("Atbalsta 1288/Lp14 likumprojektu", {"1288-lp14"})
    assert '<a href="likumprojekti/1288-lp14.html">1288/Lp14</a>' in out

def test_unknown_doc_nr_preserved():
    out = _autolink_bills_filter("Atbalsta 9999/Lp14", set())
    assert out == "Atbalsta 9999/Lp14"
    assert "<a" not in out

def test_multiple_bills_one_summary():
    out = _autolink_bills_filter("1288/Lp14 un 934/Lm14", {"1288-lp14", "934-lm14"})
    assert out.count("<a href=") == 2

def test_surrounding_punctuation():
    out = _autolink_bills_filter("(1288/Lp14), 934/Lm14.", {"1288-lp14", "934-lm14"})
    assert '>1288/Lp14</a>' in out
    assert '>934/Lm14</a>' in out

def test_word_boundary_no_partial_match():
    out = _autolink_bills_filter("abc1288/Lp14def", {"1288-lp14"})
    assert "<a" not in out

def test_empty_text():
    assert _autolink_bills_filter("", set()) == ""
    assert _autolink_bills_filter(None, set()) == ""
```

---

## 4. `/likumi.html` index lapa

### 4.1 Datu sagatavošana — jauna funkcija `_fetch_law_index_page()`

```python
def _fetch_law_index_page(db: sqlite3.Connection, laws_dir: Path = Path("wiki/laws")) -> list[dict]:
    """Build sortable index of base laws for /likumi.html.

    For each wiki/laws/<slug>.md (skipping likumi.md), join saeima_bills via
    base_law_slug to count attached likumprojekti and find the most recent
    activity date. Empty bill_count is OK — it signals the law has no
    pending amendments this term.
    """
    laws = load_laws_index(laws_dir)  # existing helper, returns dict[slug, title]
    rows = db.execute("""
        SELECT base_law_slug,
               COUNT(*) AS bill_count,
               MAX(last_updated_at) AS last_activity
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL
        GROUP BY base_law_slug
    """).fetchall()
    counts = {r["base_law_slug"]: dict(r) for r in rows}

    # Topic atvasinās no bills, ne wiki frontmatter (wiki/laws/*.md nav YAML
    # frontmatter — sākas tieši ar # H1). Likumiem bez bills topic paliek "".
    # Ja vienam likumam bills nāk no dažādām tēmām, ņem visbiežāk lietoto.
    topic_rows = db.execute("""
        SELECT base_law_slug, topic, COUNT(*) AS n
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL AND topic IS NOT NULL
        GROUP BY base_law_slug, topic
        ORDER BY base_law_slug, n DESC
    """).fetchall()
    topics: dict[str, str] = {}
    for r in topic_rows:
        if r["base_law_slug"] not in topics:  # first row per slug = highest count
            topics[r["base_law_slug"]] = r["topic"]

    out = []
    for slug, title in sorted(laws.items(), key=lambda kv: kv[1]):
        c = counts.get(slug, {})
        out.append({
            "slug": slug,
            "title": title,
            "topic": topics.get(slug, ""),
            "bill_count": c.get("bill_count", 0),
            "last_activity": c.get("last_activity", ""),
        })
    return out
```

### 4.2 Render zvans `generate_public_site()`

Pēc `_generate_law_pages()`:

```python
laws_index = _fetch_law_index_page(db)
law_topics = sorted({l["topic"] for l in laws_index if l["topic"]})
_render_page(env, "likumi-index.html.j2", atmina_dir / "likumi.html", {
    "laws": laws_index,
    "law_topics": law_topics,
    "metrics": {
        "total": len(laws_index),
        "with_bills": sum(1 for l in laws_index if l["bill_count"] > 0),
    },
})
```

### 4.3 Templeits `templates/likumi-index.html.j2`

Mirror `/balsojumi.html#bills-list` ārējā struktūra (`bill-card-grid` + `bill-card` klases, CSS reused), bet ar law-card datu shape:

```jinja
{% extends "base.html.j2" %}
{% block title %}Pamatlikumi — atmīna.lv{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Pamatlikumi</h1>
  <p class="muted">{{ metrics.total }} likumi · {{ metrics.with_bills }} ar aktīviem likumprojektiem</p>
</div>

<div class="filter-row">
  <select id="law-topic-filter" onchange="window.applyLawsFilters()">
    <option value="">Visas tēmas</option>
    {% for t in law_topics %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
  </select>
  <input type="search" id="law-search" placeholder="Meklēt nosaukumā..." oninput="window.applyLawsFilters()">
</div>

<div class="bill-card-grid" id="laws-grid">
  {% for law in laws %}
  <a class="bill-card" href="likumi/{{ law.slug }}.html"
     data-topic="{{ law.topic }}" data-title="{{ law.title|lower }}">
    <div class="bill-card-title">{{ law.title }}</div>
    {% if law.topic %}<span class="topic-chip">{{ law.topic }}</span>{% endif %}
    <div class="bill-card-meta">
      {% if law.bill_count > 0 %}
        <span>{{ law.bill_count }} likumproj.</span>
        {% if law.last_activity %}<span class="muted">· {{ law.last_activity[:10] }}</span>{% endif %}
      {% else %}
        <span class="muted">nav aktīvu likumprojektu</span>
      {% endif %}
    </div>
  </a>
  {% endfor %}
</div>

<script>
window.applyLawsFilters = function() {
  var topic = document.getElementById('law-topic-filter').value;
  var q = (document.getElementById('law-search').value || '').toLowerCase();
  document.querySelectorAll('#laws-grid .bill-card').forEach(function(c) {
    var matchTopic = !topic || c.dataset.topic === topic;
    var matchQ = !q || c.dataset.title.indexOf(q) !== -1;
    c.style.display = (matchTopic && matchQ) ? '' : 'none';
  });
};
</script>
{% endblock %}
```

### 4.4 Footer cross-link `/balsojumi.html`

Pievieno `templates/balsojumi.html.j2` `bills-list-tab` div beigās (līnija ~310):

```jinja
<div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border); font-size: 0.9rem;">
  <a href="likumi.html" class="muted-link">Visi pamatlikumi ({{ laws_index_count }}) →</a>
</div>
```

`laws_index_count` padodas templeit kontekstā (skaitlis jāatslogo dinamiski no `len(laws_index)` — nepanaglo statiski "33", lai wiki/laws/ paplašinot count atjauninās automātiski).

### 4.5 Tests (`tests/test_likumi_index.py`, jauns fails)

```python
def test_fetch_law_index_page_includes_all_wiki_laws(tmp_db_with_laws):
    rows = _fetch_law_index_page(tmp_db_with_laws, laws_dir=Path("wiki/laws"))
    assert len(rows) == len(load_laws_index(Path("wiki/laws")))  # match wiki count dynamically
    assert all("slug" in r and "title" in r for r in rows)

def test_law_with_attached_bills_has_count(tmp_db_with_laws):
    rows = _fetch_law_index_page(tmp_db_with_laws, laws_dir=Path("wiki/laws"))
    saeimas_velesanu = next(r for r in rows if r["slug"] == "saeimas-velesanu-likums")
    assert saeimas_velesanu["bill_count"] >= 1

def test_law_without_bills_renders_zero(tmp_db_with_laws):
    rows = _fetch_law_index_page(tmp_db_with_laws, laws_dir=Path("wiki/laws"))
    no_bills = [r for r in rows if r["bill_count"] == 0]
    assert len(no_bills) > 0  # 77 laws with no bill linkage as of phase 1B-ii

def test_likumi_index_html_generated(generated_site):
    assert (generated_site / "likumi.html").exists()
    content = (generated_site / "likumi.html").read_text(encoding="utf-8")
    assert "Pamatlikumi" in content
    assert 'href="likumi/saeimas-velesanu-likums.html"' in content

def test_balsojumi_footer_link_to_likumi(generated_site):
    content = (generated_site / "balsojumi.html").read_text(encoding="utf-8")
    assert 'href="likumi.html"' in content
    assert "Visi pamatlikumi" in content
```

---

## 5. Runbook + Pipeline Invariant 12

### 5.1 `CLAUDE.md` Pipeline Invariant 12

Pievieno pēc esošās 11. invariant `## Pipeline Invariants` sadaļā:

> **12. `saeima_votes.bill_id` un `saeima_bills.current_stage` atjauno tikai caur `append_bill_stage()`.** Nekādi citi `UPDATE` šajiem laukiem nav atļauti. Aizstāv denormalizācijas sinhroniju — vote→stage→bill timeline ir atomic, un manuāla rakstīšana plēš vēstures integritāti. [CHANGELOG § Phase 1C](wiki/CHANGELOG.md#2026-04-XX--saeima-bills-phase-1c-orchestration--glue).

(Datums un anchor nokomplektējami pēc 1C merge.)

### 5.2 `wiki/operations/saeima-bills.md` runbook

Jauns fails ~150 rindas. Struktūra (nokopējot no `wiki/operations/agenti/saeima-tracker.md` patternu):

```markdown
# Saeima bills — operatorinstrukcija

## Mērķis
Ko likumprojektu izsekošana dod atmīnai un kā operators palaiž jauno sesiju.

## Tipisks ciklis (jauna sēde)
1. Atver Saeimas kalendāru, atrod nesenas balsojumu sesijas URL
2. Palaiž `@saeima-tracker` ar sesijas URL
3. Aģents:
   - Step 1-2: snapshot agenda, parse bills + URLs (jauns)
   - Step 3-4: ievāc balsojumu rezultātus
   - Step 5: link vote → bill stage (jauns)
4. Pārskata logus — STOP signāli (zem Failure modes) prasa operatorā darbību
5. Palaiž `python -c "from src.generate import generate_public_site; generate_public_site()"`
6. Pārbauda `/likumprojekti/`, `/likumi.html` un `/balsojumi.html#bills-list`

## Manuālā iesniedzēja pievienošana
Ja agents ziņo "unknown institutional submitter" — pievieno aģenta prompta
`KNOWN_INSTITUTIONAL_SUBMITTERS` sarakstam (§ 2.A.bis). Ja jaunā vērtība
nav atpazīta arī `parse_agenda_snapshot()` plūsmā, paplašini regex
`_parse_institutional_submitter()` (`src/saeima.py:490`). Re-run aģentu.

## Backfill atkārtošana
`python scripts/backfill_saeima_bills.py` un `backfill_base_law_slug.py`
ir idempotenti (WHERE base_law_slug IS NULL filter aizsargā). Drošs
re-run ja kāda lauka aizpilde palika nepilna.

## Troubleshooting

### Agenda parse atgriež []
HTML struktūra mainīta. Atver sesijas URL pārlūkprogrammā, salīdzina ar
`parse_agenda_snapshot` regex (`src/saeima.py:504`). Ja .html mainījies,
fix parser pirms re-run.

### base_law_slug=NULL spītīgi
title var nesatur kanonisku likuma nosaukumu. Pārbauda wiki/laws/
mapju — vai pareizais base law file eksistē? Manuāli var iestatīt:
`UPDATE saeima_bills SET base_law_slug='...' WHERE document_nr='...'`
(viens no maziem izņēmumiem, kas NEIET caur Invariant 12, jo nav
denormalizācija).

### Junction empty pēc agent run
match_submitters_to_politicians fail-loud — pārbaudi unmatched logus.
Visdrīzāk submitter_names lauka parsēšana neizdevās — pārbauda
parse_agenda_snapshot output.

## Saistītie faili
- `src/saeima.py` — visas helper funkcijas
- `.claude/agents/saeima-tracker.md` — agenta operatorinstrukcija
- `tests/test_saeima_bills*.py` — Phase 1A unit + integration
- `wiki/CHANGELOG.md` — Phase 1A/B/C lēmumu vēsture
```

---

## 6. Acceptance kritēriji un scope robežas

### 6.1 Funkcionālie kritēriji

| # | Pārbaude | Pieņemts ja |
|---|---|---|
| 1 | `@saeima-tracker` palaiž jaunu sesiju | Step 2 ievada bills `saeima_bills`, junction populates, Step 5 piesien `bill_id` katram votei (kur motif resolvable) |
| 2 | Politiķa profila Likumprojekti tabs | Renderē saturu, kad junction nav tukšs (1B-ii ready, gaida tikai Step 1 datus) |
| 3 | Pozīcijas claim summary `1288/Lp14` reference | Renderē kā `<a href="likumprojekti/1288-lp14.html">` _ja_ slug eksistē; plain text ja nē |
| 4 | `/likumi.html` | 33 cards rāda alfabēta secībā ar topic chip + bill_count; topic filter strādā; meklēšana strādā |
| 5 | `/balsojumi.html#bills-list` footera link | Link uz `likumi.html` redzams |

### 6.2 Datu kritēriji (pēc pirmā live agent run pret jaunu sesiju)

- `saeima_bill_politicians` rindu count > 0 (pirmais junction populated run)
- `saeima_votes WHERE bill_id IS NOT NULL` count pieaug par cik balsojumu motifs rezolvē uz bills (gaidāms ~80%+, atlikušie 'nezināms' stage_name OK)
- `saeima_bills.current_stage` reflektē pēdējo `append_bill_stage` zvanu (ne raw INSERT)

### 6.3 Test kritēriji

- 224 esošie testi (Phase 1B suite + saeima) joprojām pass
- Jauni testi:
  - `tests/test_autolink_bills.py` — 6 testi (no § 3.4)
  - `tests/test_likumi_index.py` — 5 testi (no § 4.5)
  - **Kopā: 11 jauni testi → 235 total**

Manuālo prompt validāciju (agent prompt) nedarīsim ar pytest — tas ir prompt change, pārbauda ar nākamo live `@saeima-tracker` palaišanu (smoke step).

### 6.4 Commit struktūra (foundation-first)

| # | Commit | Faili | Tests |
|---|---|---|---|
| 1 | `docs(claude): add Pipeline Invariant 12` | `CLAUDE.md` | — |
| 2 | `feat(generate): autolink_bills Jinja filter` | `src/generate.py` + 5 templeiti + tests | 6 |
| 3 | `feat(generate): /likumi.html base-law index` | `src/generate.py`, `templates/likumi-index.html.j2`, `templates/balsojumi.html.j2` | 5 |
| 4 | `docs(operations): saeima-bills runbook` | `wiki/operations/saeima-bills.md` | — |
| 5 | `feat(saeima-tracker): Step 2 expand + Step 5 link` | `.claude/agents/saeima-tracker.md` | — |
| 6 | `chore(changelog): Phase 1C — orchestration glue` | `wiki/CHANGELOG.md`, `wiki/index.md` | — |

Worktree: `.worktrees/saeima-bills-phase-1c`. Smoke test pēc commit 6 ir live `@saeima-tracker` palaišana, lai apstiprinātu funkcionālos kritērijus 1+2 punktus.

### 6.5 Scope robežas (out-of-scope)

- **Top nav entry uz `/likumi.html`** — atlikts (Phase 1D vai vēlāk)
- **Phase 1.5** vēsturisks re-scrape — atsevišķs paks
- **Phase 2** priekšlikumu autori, **Phase 3** debates — atsevišķi paki
- **Backfill jaunajiem submitters esošajos 91 bills** — junction paliks tukšs vēsturiskajam datumkopumam; tikai jauni runs piepildīs (nav re-scrape no 1A bills)

---

## 7. Atsauces

- Master spec (visi posmi): [`docs/superpowers/specs/2026-04-22-saeima-bills-design.md`](2026-04-22-saeima-bills-design.md) — § 4.4 (agenta prompt), § 6.3 (cross-linking), § 11 (docs).
- Phase 1A spec + plan: [`2026-04-22-saeima-bills-phase-1a-implementation.md`](../plans/2026-04-22-saeima-bills-phase-1a-implementation.md)
- Phase 1B-i spec + plan: [`2026-04-27-saeima-bills-phase-1b-i-design.md`](2026-04-27-saeima-bills-phase-1b-i-design.md), [implementation](../plans/2026-04-27-saeima-bills-phase-1b-i-implementation.md)
- Phase 1B-ii spec + plan: [`2026-04-27-saeima-bills-phase-1b-ii-design.md`](2026-04-27-saeima-bills-phase-1b-ii-design.md), [implementation](../plans/2026-04-27-saeima-bills-phase-1b-ii-implementation.md)
- HANDOFF: [`HANDOFF-saeima-bills-next-phases.md`](../plans/HANDOFF-saeima-bills-next-phases.md)
- CHANGELOG: [`wiki/CHANGELOG.md`](../../../wiki/CHANGELOG.md)
