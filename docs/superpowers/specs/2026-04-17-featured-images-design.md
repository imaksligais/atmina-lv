# Featured Images — Dizaina specifikācija

**Datums:** 2026-04-17
**Statuss:** Brainstorming pabeigts, gaida review pirms implementācijas plāna
**Autors:** Claude Code brainstorming session

## Mērķis

Katram dienas (un vēlāk nedēļas) pārskatam pievienot AI-ģenerētu *featured image* — 16:9 vizuālu kartiņu ar tipogrāfisku izkārtojumu un tēmai atbilstošu metaforu. Attēli parādās:

1. **`blog/<slug>.html`** — full-bleed hero virs raksta satura, arī kā `og:image` sociālajai koplietošanai.
2. **`index.html`** (vai `index-v2.html`) — viens liels featured attēls jaunākajam brief'am, aizstājot esošo `brief-card` teksta preview.
3. **`analizes.html`** — thumbnail kolonnā katrā `daily-card` (sarakstā visi esošie brief'i).

## Principi

- **Transparency first** — AI ne drīkst halucinēt faktus. Teksts attēlā var būt tikai tas, ko brief-writer deterministiski padevis. Skaitliskās vērtības validētas pret brief body.
- **Bez cilvēkiem, bez karogiem, bez partijas logo** — atmina.lv ir kritisks, bet neitrāls rīks. Portrāti vai partiju simboli ievieš framing.
- **Cilvēks-in-the-loop pirms publicēšanas** — katrs ģenerētais attēls apstiprināms manuāli pirms `approved=1`. Noraidīti attēli paliek audit vēsturē.
- **Stilistiska konsekvence** — globāls `STYLE_GUIDE` un stabila `visual_map.py` (topic → metafora). Katra diena izskatās kā "atmina.lv", ne kā random AI output.

## Arhitektūra

### Jaunais Python pakotnes struktūra

```
src/graphics/
    __init__.py
    config.py         # load_gemini_key(), MONTHLY_BUDGET_USD, COST_PER_IMAGE_USD, budget_check()
    nanobanana.py     # generate_image(prompt, aspect_ratio="16:9") -> bytes + SafetyError
    visual_map.py     # VISUAL_MAP dict: topic → {metaphor, mood, accent} + get_visual()
    prompt.py         # STYLE_VARIANTS + DEFAULT_STYLE + build_prompt(visual_brief, visual_map_entry)
    storage.py        # save_image_row, approve/reject, get_approved_image, get_attempts, monthly_cost_usd
```

### Jaunie Claude Code aģenti

- `.claude/agents/graphics-designer.md` — kreatīvs subagent. Saņem `note_id`, lasa brief content + `visual_brief_json`, izvēlas konkrēto metaforu no `visual_map`, izsauc `nanobanana.generate_image()`, saglabā + atgriež `image_path`.

### Izmaiņas esošajiem aģentiem

- `.claude/agents/brief-writer.md` — promptu paplašinājums: brief teksta beigās obligāts `## Vizuālais brief` markdown bloks ar bulletiem:
  - **Tēma:** (no 26 kanoniskajām `src/topic_map.py` grupām)
  - **Galvenā tēze:** (max 60 simboli, dienas primārā fakta apraksts)
  - **Skaitlis:** (galvenais kvantitatīvais rādītājs dienai, vai `-`)
  - **Metaforas hint:** (max 40 simboli, brīva forma)

### DB shēma

**Jauna tabula `brief_images`:**

```sql
CREATE TABLE brief_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id     INTEGER NOT NULL REFERENCES context_notes(id),
    image_path  TEXT    NOT NULL,       -- relative: images/briefs/<slug>-<hash8>.png
    prompt      TEXT    NOT NULL,       -- full nanobanana prompt (audit)
    model       TEXT    NOT NULL,       -- e.g. 'gemini-3.1-flash-image-preview'
    seed        INTEGER,                -- nullable
    aspect      TEXT    NOT NULL DEFAULT '16:9',
    width       INTEGER,
    height      INTEGER,
    generated_at TEXT   NOT NULL,       -- ISO Latvia TZ via now_lv()
    cost_usd    REAL    NOT NULL DEFAULT 0.039,
    approved    INTEGER NOT NULL DEFAULT 0,  -- 0=pending, 1=approved, 2=rejected
    error_message TEXT                  -- SAFETY_BLOCKED, rate limit etc.
);
CREATE INDEX idx_brief_images_note_approved
    ON brief_images(note_id, approved, id DESC);
```

**Apzināti NAV `UNIQUE(note_id)`** — vairākas rindas per brief atļautas (attempt history). Site render lasa tikai `MAX(id) WHERE note_id=X AND approved=1`.

**Izmaiņa `context_notes`:**

```sql
ALTER TABLE context_notes ADD COLUMN visual_brief_json TEXT;
```

JSON blob ar `{topic, headline, stat, metaphor_hint}`. NULL veciem briefs — backfill skripts aizpilda.

### Secrets un konfigurācija

- `data/gemini_key.json` — `{"api_key": "...", "model": "gemini-3.1-flash-image-preview"}`. Jau automātiski gitignored caur `data/*.json`.
- `src/graphics/config.py` satur:
  - `MONTHLY_BUDGET_USD = 5.00` (pietiek ~128 attēliem/mēnesī)
  - `COST_PER_IMAGE_USD = 0.039` (hardcoded ar komentāru "last verified: 2026-04-17")
  - `budget_check(db)` — pirms katras API izsaukuma, `raise BudgetExceededError` ja pārsniegts
- `src/generate.py` — eksistē `BASE_URL = "https://atmina.lv"` (78. līnija); pievieno Jinja kontekstam kā `BASE_URL` visos render izsaukumos OG tagu absolūtiem URL. Nav jauns config fails.

## Datu plūsma

### Jaunais brief (parastais dienas cikls)

1. `@brief-writer` subagent ģenerē dienas pārskatu, beigās pievieno `## Vizuālais brief` bloku.
2. `src/briefs.py::parse_visual_brief(markdown) -> dict | None` izvelk lauku vērtības. Ja parsing fails vai bloks trūkst — `None`, brief tāpat tiek saglabāts.
3. `src/briefs.py::store_context_note(...)` — pieņem `visual_brief` dict, serializē JSON'ā uz `context_notes.visual_brief_json`.
4. Validācija: ja `visual_brief.stat` ir skaitliska vērtība (vai satur ciparus, piem. "30 milj."), `str(stat)` substring'am jāparādās brief `content` lauka (markdown raw) tekstā. Ja nē — `stat` tiek noņemts (atstāj attēlu bez skaitļa, nevis meli).
5. **11. solis dienas rutīnā** (`src/routine.py`) — pārbauda eksistē `daily_brief` ar `visual_brief_json` bet bez `approved=1` `brief_images` rindas → izsauc `@graphics-designer`.
6. Aģents lasa `note_id` → brief content + `visual_brief` → `visual_map.get_visual(topic)` → komponē nanobanana prompt (`prompt.build_prompt()` + DEFAULT_STYLE).
7. `nanobanana.generate_image()` — 3 retry ar exponential backoff pie 429/500, raise `SafetyError` pie `SAFETY_BLOCKED`.
8. Pie kļūdas: `storage.save_image_row(approved=2, error_message=...)`, rutīna parāda warning, brief renderējas bez attēla (fallback teksta kartīte).
9. Pie veiksmes: `compute_filename(slug, png_bytes)` ar sha256[:8] hash → saglabā `output/images/briefs/<slug>-<hash8>.png`, `storage.save_image_row(approved=0)`.
10. Claude Code `Read` tool parāda PNG konsolē. Lietotājs: "OK" → `approve_image(id)`, vai "pārģenerē ar X" → atpakaļ uz 6. ar papildu norādi. Iepriekšējā rinda paliek `approved=0` (pending) vai tiek manuāli noraidīta.

### Retroaktīvā backfill (vienreizējs)

`scripts/backfill_brief_images.py`:

1. Atrod visus `daily_brief` bez `visual_brief_json` (esošos 12).
2. Katram palaiž inline Claude SDK izsaukumu `scripts/backfill_brief_images.py` iekšpusē — vienkāršs promptu template ("izvelc topic/headline/stat/metaphor_hint no šī brief content"), nav jauns subagent. Rezultātu validē (stat pret body), saglabā `context_notes.visual_brief_json`.
3. Katram brief bez `approved=1` rindas — izsauc `nanobanana.generate_image()` ar `visual_map` metaforu, `approved=1` uzreiz (batch mode, bez cilvēka-in-the-loop).
4. 2s sleep starp izsaukumiem, exponential backoff pie rate limit.
5. Izmaksas: ~12 × $0.039 = ~$0.47.
6. Pēc pabeigšanas — parāda sarakstu `ID | slug | image_path`, lietotājs manuāli var noraidīt atsevišķus (`reject_image(id)` + regenerate).

### Test harness (PIRMS integrācijas)

`scripts/test_image_prompt.py`:

- **`--smoke`** režīms — viens hardcoded prompt ar latviešu virsrakstu, tmp output, eye-check (Fāze 0).
- **`--matrix --brief-ids 142,135,126`** — 3 stili × 3 reāli brief'i = 9 attēli, `tmp/image_tests/<YYYY-MM-DD-HHMM>/gallery.html` ar režģi. `visual_brief` paraugi manuāli uzrakstīti `tmp/visual_briefs/<brief_id>.json` — šos JSON failus Claude Code izveido Fāzes 1 sākumā, izlasot 3 brief content no DB un kopīgi ar lietotāju izspriežot topic/headline/stat/metaphor_hint pirms test matricas palaišanas.
- Katram iteration: `prompt.txt` + `<style>-<brief>.png` blakus. Lietotājs salīdzina, izvēlas uzvaroša stila key.

## Prompt struktūra

### Globālais stila slānis

`src/graphics/prompt.py::STYLE_VARIANTS` satur 3 estētikas testēšanai:

1. **`editorial`** — editorial poster, cream/beige textured paper background, monochrome black condensed serif typography, one accent color. The Economist / political poster feel.
2. **`scandi`** — off-white background, thin geometric shapes, Inter/Söhne-style sans-serif, generous negative space, muted accent. Modern Nordic.
3. **`constructivist`** — two contrasting colors (e.g. deep navy + ochre), bold geometric blocks, diagonal composition, display sans/slab-serif. Post-Soviet Bauhaus political poster.

Pēc testēšanas fāzes — `DEFAULT_STYLE = "..."` izvēlēts fix, nav runtime konfigurējams (vienkāršība).

### Tematiskais slānis

`src/graphics/visual_map.py::VISUAL_MAP` — dict no visām 26 kanoniskajām `topic_map.py` tēmām:

```python
VISUAL_MAP = {
    "transports": {
        "metaphor": "abstract aircraft silhouette OR parallel railway tracks converging to horizon",
        "mood": "motion, forward trajectory",
        "accent": "deep blue",
    },
    "veselība": {...},
    # ... 26 tēmas kopā
}

_DEFAULT = {
    "metaphor": "abstract geometric composition suggesting public discourse",
    "mood": "neutral observation",
    "accent": "charcoal",
}

def get_visual(topic: str) -> dict:
    return VISUAL_MAP.get(topic, _DEFAULT)
```

Unit test `tests/test_visual_map.py` garantē `set(VISUAL_MAP) >= set(topic_map.CANONICAL_TOPICS)` — nav drift.

### Prompt komponēšana

`build_prompt(visual_brief, visual_map_entry, style_key) -> str`:

```
[STYLE_GUIDE teksts izvēlētā stila]

Topic: {visual_brief['topic']}
Visual metaphor: {visual_map_entry['metaphor']}
Mood modifier: {visual_map_entry['mood']}
Accent color: {visual_map_entry['accent']}

Headline text (render exactly as shown, preserve diacritics):
"{visual_brief['headline']}"

[Key figure to display prominently: {stat}]  -- ja stat nav None

[NEGATIVE_CONSTRAINTS: no people, flags, logos, other text, photorealism, borders]
```

Diakritikas instrukcija + citāta pēdiņas = zināmais trick teksta precizitātei lielu valodu modeļiem.

## Šabloni un CSS

### `templates/base.html.j2` — OG meta bloks

```html
<meta property="og:title" content="{% block og_title %}{{ self.title() }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}{% endblock %}">
<meta property="og:image" content="{% block og_image %}{{ BASE_URL }}/images/og-default.png{% endblock %}">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
```

Default OG — `assets/og-default.png` (manuāli izveidots atmina brand kartīte).

### `templates/blog-post.html.j2` — full-bleed hero

```html
{% block og_image %}{% if featured_image %}{{ BASE_URL }}/images/briefs/{{ featured_image }}{% endif %}{% endblock %}

{% block content %}
{% if featured_image %}
<figure class="brief-hero">
  <img src="../images/briefs/{{ featured_image }}"
       alt="{{ visual_brief.headline if visual_brief else title }}"
       width="1408" height="768" loading="eager">
</figure>
{% endif %}
<article class="brief-content">
  {{ content_html|safe }}
</article>
{% endblock %}
```

CSS:

```css
.brief-hero {
  margin: 0 -50vw 2rem -50vw;
  width: 100vw;
  position: relative;
  left: 50%;
  transform: translateX(-50%);
  aspect-ratio: 16 / 9;
  overflow: hidden;
}
.brief-hero img { width: 100%; height: 100%; object-fit: cover; display: block; }
.brief-content { max-width: 720px; margin: 0 auto; }
```

### `templates/index.html.j2` (vai nākotnes `index-v2.html`) — viens featured attēls

Aizstāj esošo `brief-card` ar `brief-featured-card`:

```html
{% if latest_brief_with_image %}
<section class="container">
  <a href="blog/{{ latest_brief_with_image.slug }}.html" class="brief-featured-card">
    <img src="images/briefs/{{ latest_brief_with_image.image_filename }}"
         alt="{{ latest_brief_with_image.headline or latest_brief_with_image.title }}"
         loading="eager">
    <div class="brief-featured-body">
      <span class="brief-featured-type">{{ latest_brief_with_image.type_label }}</span>
      <span class="brief-featured-date">{{ latest_brief_with_image.date }}</span>
      <div class="brief-featured-preview">{{ latest_brief_with_image.preview }}</div>
    </div>
  </a>
</section>
{% endif %}
```

Attēls pāri visam container platumam (ne edge-to-edge, jo hero-v2 jau prasa attention), teksts zem tā.

### `templates/analizes.html.j2` — thumbnail daily-card

```html
<a href="blog/{{ post.slug }}.html" class="daily-card {% if post.image_path %}has-image{% endif %}">
  {% if post.image_path %}
  <img src="images/briefs/{{ post.image_filename }}"
       alt="{{ post.headline or post.title }}"
       class="daily-card-thumb" loading="lazy">
  {% endif %}
  <div class="daily-date-block">...</div>
  <div class="daily-body">...</div>
</a>
```

CSS:

```css
.daily-card.has-image { padding-left: 0; }
.daily-card-thumb {
  width: 140px; aspect-ratio: 16 / 9;
  object-fit: cover; flex-shrink: 0;
}
@media (max-width: 768px) { .daily-card-thumb { width: 80px; } }
```

## Failu nosaukumi

`src/graphics/storage.py::compute_filename(slug, png_bytes) -> str`:

```python
def compute_filename(slug: str, png_bytes: bytes) -> str:
    hash8 = hashlib.sha256(png_bytes).hexdigest()[:8]
    return f"{slug}-{hash8}.png"
```

Hash novērš cache issues regenerācijā — katrs jauns PNG = jauns faila nosaukums. Šabloni lasa `image_filename` no DB (`image_path` bāzes nosaukums), nekonstruē.

## Cilvēks-in-the-loop un regeneration

Rutīnas 11. solis (Claude Code interaktīvs):

1. Rāda PNG ar Read tool.
2. Lietotājs var teikt:
   - **"OK"** → `approve_image(id)`, iet tālāk.
   - **"pārģenerē"** (bez papildus) → atkārto ar to pašu promptu (nanobanana seed atšķiras).
   - **"pārģenerē ar X"** → aģents modificē promptu (piem. "ar siltāku toni", "ar bolder metaforu"), jauna rinda DB.
   - **"noraidi"** → `reject_image(id, reason)`, bez regenerate.
3. Attempt history paliek `brief_images` tabulā — audit trail, debug.

Budget cap (`MONTHLY_BUDGET_USD`) pārbaudīts pirms katras API izsaukuma. Pārsniegts → `BudgetExceededError`, rutīna warno, brief tāpat publicējas bez attēla.

## Error handling

| Kļūda | Rīcība |
|---|---|
| `SAFETY_BLOCKED` (content moderation) | `approved=2`, `error_message="SAFETY_BLOCKED"`, brief fallback teksta kartīte |
| Rate limit (429) | 3 retry ar exponential backoff (2s, 4s, 8s) |
| API nesasniedzams | 3 retry, pēc tam `approved=2`, `error_message="API_UNAVAILABLE"` |
| Budget exceeded | `BudgetExceededError`, pipeline apstādas pirms API izsaukuma |
| Parse fail (`visual_brief`) | `None`, brief tāpat saglabājas, nav image pipeline trigger |
| Stat validation fail | `stat=None` `visual_brief` dict, attēls ģenerējas bez skaitļa |

## Implementācijas fāzes

Saskaņā ar `CLAUDE.md` rule #1 (phased execution, max 5 faili, verification starp fāzēm).

### Fāze 0 — API smoke test (BLOĶĒJOŠS)

**Faili (~3):** `data/gemini_key.json` (manuāli), `src/graphics/config.py`, `src/graphics/nanobanana.py`, `scripts/smoke_test.py`.

**Verifikācija:** atveram `tmp/smoke_test_<timestamp>.png`, pārbaudām (a) attēls izveidojas, (b) latviešu diakritika atpazīstama, (c) faktiskais output izmērs.

**Bloks:** ja diakritika kritiski sabrūk — atgriežamies pie dizaina, apsveram alternatīvu (model switch, post-render text overlay utt.).

### Fāze 1 — Stila matrica

**Faili (~4):** `src/graphics/prompt.py` (3 STYLE_VARIANTS), `src/graphics/visual_map.py` (26 tēmas), `tmp/visual_briefs/{142,135,126}.json` (manuāli), `scripts/test_image_prompt.py`, `tests/test_visual_map.py`.

**Verifikācija:** `tmp/image_tests/<timestamp>/gallery.html` — 9 attēlu režģis. Lietotājs izvēlas `DEFAULT_STYLE`.

**Testi:** `pytest tests/test_visual_map.py` zaļš.

### Fāze 2 — DB shēma + storage

**Faili (~3):** `scripts/migrate_db.py`, `src/graphics/storage.py`, `tests/test_graphics_storage.py`.

**Verifikācija:** `pytest tests/test_graphics_storage.py` zaļš, migrācija idempotenta (`python scripts/migrate_db.py` var palaist atkārtoti).

### Fāze 3 — Brief-writer izmaiņas + parse

**Faili (~3):** `.claude/agents/brief-writer.md`, `src/briefs.py`, `tests/test_briefs_visual.py`.

**Verifikācija:** `pytest tests/test_briefs_visual.py`, manuāls brief-writer izsaukums → `## Vizuālais brief` bloks parādās output.

### Fāze 4 — Grafikas aģents + retroaktīvā backfill

**Faili (~2):** `.claude/agents/graphics-designer.md`, `scripts/backfill_brief_images.py` (ar inline Anthropic SDK izsaukumu `visual_brief` ekstrakcijai, bez atsevišķa subagent).

**Verifikācija:** palaiž backfill, 12 `brief_images` rindas ar `approved=1`, attēli `output/images/briefs/`.

### Fāze 5 — Rutīnas integrācija

**Faili (~2):** `src/routine.py` (11. solis), `tests/test_routine.py` atjauninājums.

**Verifikācija:** `pytest tests/test_routine.py`, `print_routine()` rāda jauno soli statusu.

### Fāze 6 — Template un site integrācija

**Faili (~5):** `src/generate.py` (pievieno `BASE_URL` Jinja kontekstam + `fetch_latest_brief_with_image()` + `image_path` uz `analizes`/`blog-post` kontekstiem), `templates/base.html.j2`, `templates/blog-post.html.j2`, `templates/index.html.j2` (vai `index-v2.html`), `templates/analizes.html.j2`, `assets/style.css`, `assets/og-default.png`.

**Verifikācija:** `python -c "from src.generate import generate_public_site; generate_public_site()"`, manuāla pārlūka pārbaude.

### Fāze 7 — Deploy

**Faili:** nav — izmanto esošo `scripts/deploy.sh`.

**Verifikācija:** `bash scripts/deploy.sh --dry-run` redz `output/images/briefs/` rsync list, pēc deploy `curl -I https://atmina.lv/images/briefs/<slug>-<hash>.png` → 200.

## Testēšanas matrica

| Līmenis | Ko testē | Kur |
|---|---|---|
| Unit | `visual_map.py` pret `topic_map.py` (drift) | `tests/test_visual_map.py` |
| Unit | `parse_visual_brief()` parser (ar/bez bloka, nederīgs stat) | `tests/test_briefs_visual.py` |
| Unit | `storage.py` DB helpers (save/approve/reject/get_approved) | `tests/test_graphics_storage.py` |
| Unit | `nanobanana.py` ar mock SDK (retry logic, SafetyError) | `tests/test_nanobanana.py` |
| Integration | Rutīnas 11. solis ar mock aģentu | `tests/test_routine.py` papildinājums |
| Manual | API output kvalitāte, diakritika | Fāze 0 smoke_test |
| Manual | Stila izvēle (3×3 matrica) | Fāze 1 gallery.html |
| Manual | Full render output | `generate_public_site()` → pārlūks |

## Izmaksu aprēķins

| Darbība | Attēli | Izmaksas |
|---|---|---|
| Smoke test | 1–3 | ~$0.10 |
| Stila matrica (3×3, varbūt 2 iterācijas) | 18 | ~$0.70 |
| Retroaktīvā backfill (12 esošie) | 12 | ~$0.47 |
| Nākotnes dienas rutīna (1 per dienu + ~1 regenerate) | ~60/mēn. | ~$2.34/mēn. |

**Kopā pirmajā mēnesī:** ~$3.50 vienreizēji + ~$2.34/mēnesī uz priekšu. MONTHLY_BUDGET_USD = $5.00 dod 2× drošības rezervi.

## Atklātie risku punkti

1. **Preview modeļa nestabilitāte** — `gemini-3.1-flash-image-preview` var mainīties / tikt deprekēts. Model lauks `data/gemini_key.json` dod ātru switch path.
2. **Latviešu diakritikas kvalitāte** — atklāts jautājums, risināms Fāzē 0. Ja kritiski slikti — alternatīva pieeja (abstract fons + HTML/SVG text overlay) jāpārskata.
3. **Content moderation refuses** — KNAB skandāli, vardarbība u.tml. var tikt bloķēti. Fallback uz teksta kartīti.
4. **Saeimas brief (vote-heavy) vs daily brief** — šobrīd atsevišķs `claim_type`, bet briefs var aptvert abus. Visual_brief ekstraktēšanas loģika agostiska.
5. **Nedēļas briefs** (pagaidām 0 eksistē) — viena metafora 7 dienām ir lossy. Fāze ārpus šī spec; atstāj `weekly_brief` bez attēla pagaidām, risinām kad pirmais tiks ģenerēts.

## Ārpus tvēruma (atlikti)

- **srcset / WebP** — perf optimizācija, var pievienot vēlāk.
- **Automatizēta diakritikas validācija** — grūti bez OCR; cilvēks-in-the-loop pietiek.
- **Nedēļas brief vizuāli** — atsevišķa sekcija kad relevants.
- **Stilu dinamiska izvēle** — DEFAULT_STYLE hardcoded pēc testēšanas, nav runtime switch.
- **API izmaksu real-time monitoring dashboard** — vienkāršs `monthly_cost_usd()` helper pietiek.

## Veiksmes kritēriji

- [ ] Fāze 0: viens PNG ar latviešu diakritiku izrādās lasāms.
- [ ] Fāze 1: stila izvēle pabeigta, 3×3 galerija ģenerēta.
- [ ] Fāze 2–5: visi `pytest` zaļi, 12 esošie briefs iegūst `approved=1` attēlus.
- [ ] Fāze 6: `generate_public_site()` renderē `blog/<slug>.html` ar hero + `og:image`, `analizes.html` ar thumbnails, `index.html` ar featured karti.
- [ ] Fāze 7: `https://atmina.lv/images/briefs/<slug>-<hash>.png` atgriež 200 + OG preview strādā Signal/Twitter/Facebook koplietošanā.

## Svarīgas piezīmes

- **`index-v2.html` apstāklis** — lietotājs testē jaunu homepage hero. Šis spec pieņem, ka kad `index-v2.html` vai atjaunināts `index.html` ir gatavs, `brief-featured-card` pattern iekļaujas ZEM hero sekcijas. Konkrētā integrācija `index-v2.html` notiks Fāze 6, kad homepage dizains ir iesaldēts.
- **Manuālā `visual_brief` ekstrakcija testa fāzei** — lietotājs un Claude kopā uzrakstīs JSON'u 3 paraugu brief'iem pirms Fāzes 1. Pilnā automatizācija (brief-writer iedod) notiek Fāzē 3.
- **Creative vs thin aģents** — izvēlēts kreatīvs (`@graphics-designer` kā pilnvērtīgs subagent), bet testēšanas fāzē lietotājs iteratīvi manuāli kontrolē output. Pēc stila iesaldēšanas aģenta "kreativitāte" paliek ierobežota līdz metaforas izvēlei un kompozīcijas variācijām.
