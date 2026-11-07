# Pozīcijas V2 — Dizaina specifikācija

**Datums**: 2026-04-18
**Branch**: `design/pozicijas-v2`
**Handoff avots**: `atmina-handoff/atmina/project/src/pozicijas-v2.jsx`
**Paraugs (iepriekšējais redizains)**: X tabs V1 (`xv1-*` scope)

---

## 1. Mērķis

Pārveidot `/pozicijas.html` no status-quo vienkāršās tabulas + 3 multi-select dropdowna uz V2 redakcijas dzīvo blīvo tabulu ar:

- kreiso sticky filter rail (Tēma · Partija · Persona · Periods · Ticamība),
- galveni ar trīs dinamiskām metrikām,
- Georgia (serif) + JetBrains Mono (mono) tipogrāfiju — **ne Newsreader** (tas atmests no projekta, jo nepareizi renderē LV diakritikas; sk. commit `53a347a`),
- redzamu ticamības rādītāju katrā rindā (`Augsta ≥0.9 / Laba ≥0.75 / Mērena <0.75` + 3 punktu indikators),
- klienta puses paginēta UI ar 50 rindām lapā.

Kvalitātes mērķis: pozīciju lapa kļūst par primāro skenējamo ieejas punktu pētniekiem, kuri grib atlasīt pēc tēmas × partijas × perioda. Dizaina tonis atbilst X tabam.

---

## 2. Scope (ko DARĀM)

- `templates/pozicijas.html.j2` — pilnīgs pārrakstījums V2 layout
- `assets/style.css` — jauns `.pzv1-*` bloks, vienas rindas CSS mainīgo selektora paplašinājums (`.xv1-section, .pzv1-section`)
- `assets/pzv1.js` — jauns fails, filter + paging + rail logika
- `src/generate.py` — `_fetch_claims` rindu enrichment (party_color, party_short, confidence_tier, source_domain), jauns helper `_fetch_pozicijas_metrics`, jauns `PZV1_TOPIC_COLORS` dict (26 topiku palete), papildināts render call
- `tests/` — unit tests jauniem helperiem

### Ārpus scope

- **Nostāja klasifikācija** (par/pret/kritika/nianses). DB `claims.stance` ir brīvs teksts, ne kategorisks. Filter rail šo grupu neiekļauj. Iespējama nākotnes iniciatīva ar atsevišķu klasifikācijas piegājienu vai `@claim-extractor` revīziju.
- **X tabs uzvedība** — neaiztiekam. `.xv1-*` vērtības paliek identiskas; mainās tikai selektors CSS tokenu blokā.
- **Persona profila lapa** (`politiki/<slug>.html`), citas cilnes, hero, OG image
- **Server-side paginācija** — neieviešam, paliek klienta pusē
- **Saeima balsojumu rindas** — jau izfiltrētas DB slānī (`_fetch_claims` ar `claim_type='position'`), nekas jādara papildus

---

## 3. Datu stāvoklis (tikai lasīts, informatīvs)

DB snapshot 2026-04-18 (`claims WHERE claim_type='position'`):

| Metrika | Vērtība |
|---|---|
| Kopā | 1 132 |
| Augsta (confidence ≥ 0.9) | 272 |
| Laba (0.75 ≤ c < 0.9) | 623 |
| Mērena (c < 0.75) | 237 |
| NULL confidence | 0 |
| Unikālas tēmas | 26 (visas kanoniskās grupas pārstāvētas) |
| Unikālas partijas | 11 nosauktas + NULL (146 rindu = Komentētāji/žurnālisti/neitrāli bez partijas; `Bezpartejisks` kā nosaukts 55 rindas) |

Tēmu ieraksti ir garas serif frāzes (30–90 vārdi), ne īsi kategoriski marķieri. Blīvuma variants A (12px padding, 14px teksts, 1.45 lh) apstiprināts uz šiem datiem.

---

## 4. Template struktūra (`pozicijas.html.j2`)

```
.pzv1-section
├── .pzv1-header
│   ├── .pzv1-header-title (kicker + H1 "Pozīcijas")
│   └── .pzv1-metrics (3× .pzv1-metric)
└── .pzv1-grid [240px | 1fr]
    ├── aside.pzv1-aside (sticky, top:0)
    │   ├── .pzv1-rail-group "Tēma"
    │   │   ├── 10 row (top-10 pēc skaita)
    │   │   └── button "+ rādīt visas 26 →" → atkļauj vēl 16
    │   ├── .pzv1-rail-group "Partija" (12 + "Bez partijas")
    │   ├── details.pzv1-rail-group "Persona" (kolapsējams, ar iekšēju search + scrollable)
    │   ├── .pzv1-rail-group "Periods" (4 fiksēti: Pēdējā nedēļa / Šomēnes / Šogad / Visi)
    │   └── .pzv1-rail-group "Ticamība" (3: Augsta / Laba / Visas)
    └── main.pzv1-main
        ├── .pzv1-searchbar (input + optional "Notīrīt ✕" chip)
        ├── .pzv1-sortbar ("Rāda N no M" · Kārtot: datums ↓ / ticamība / tēma)
        ├── .pzv1-thead (mono 9px UPPERCASE: Persona · Tēma · Pozīcija · Datums · Ticamība/avots)
        ├── .pzv1-rows (renderēts no JS)
        └── .pzv1-pagination (← prev · 1 · 2 · 3 · … · N · next →)
```

Grid kolonnas: `160px 120px 1fr 80px 100px`, gap 14px, padding 12px 18px.

`aside.pzv1-aside` ir `position: sticky; top: 0; align-self: start` lai tā paliek redzama, skrolljoties caur garo rindu sarakstu. Tā vertikāli skrolljās neatkarīgi no main, ja rail pārsniedz viewport (`max-height: 100vh; overflow-y: auto`).

### Rindas struktūra

| Kolonna | Saturs |
|---|---|
| Persona | Serif 13px vārds + zem tā mono 9px partijas saīsinājums (`party_color`) |
| Tēma | Mono 9px chip ar topika krāsas border + 11% alpha fill |
| Pozīcija | Serif 14px, 1.45 lh teksts (brīvs `stance`) |
| Datums | Mono 10px, `YYYY-MM-DD` |
| Ticamība/avots | `ConfidenceDots` (3 punkti) + label ("Augsta/Laba/Mērena") + mono 10px `source_domain ↗` |

Hover: `background: var(--xv1-surface)` + 2px kreisais `border-left` partijas krāsā.

---

## 5. CSS arhitektūra

### 5.1 Tokenu koplietošana

`.xv1-section` selektors CSS tokenu blokā paplašinās uz:

```css
.xv1-section,
.pzv1-section {
  --xv1-border-soft: #1f2432;
  --xv1-border:      #2d3148;
  --xv1-surface:     #161a22;
  /* ... visi pārējie tokens paliek identiski ... */
}
```

Viena rinda maiņas, nulles dublikāts. X tabs turpina darboties identiski.

### 5.2 Jaunais `.pzv1-*` bloks

Struktūra (grupas ~LOC):
- Header + metrics (~40)
- Grid + aside (~60)
- Rail group + row primitives (~80)
- Persona details + search (~40)
- Search bar + sort bar + thead (~50)
- Data rows + hover states (~80)
- Confidence dots (~30)
- Pagination (~30)
- Responsive `@media (max-width: 900px)` (~30)

Kopā ~440–500 LOC. Ievietots `style.css` beigās, aiz `.xv1-*` bloka.

---

## 6. Datu kontrakts (`src/generate.py`)

### 6.1 `_fetch_claims` papildinājumi

Katrai rindai pievieno:
- `party_color` — `PARTY_COLORS.get(party) or "#8b8fa3"`
- `party_short` — `_party_short_name(party)` vai `"—"` ja nav partijas
- `confidence_tier` — `"augsta"` (c ≥ 0.9) / `"laba"` (0.75 ≤ c < 0.9) / `"merena"` (c < 0.75 **vai `None`**, konservatīvs default)
- `source_domain` — `urlparse(source_url).netloc` ja ir URL

### 6.2 Jauns `_fetch_pozicijas_metrics(db) -> dict`

```python
{
  "total": int,                   # kopā position claims
  "last_week": int,               # stated_at >= now_lv() - 7 days
  "confidence_good_pct": int,     # round((augsta+laba) / total * 100)
}
```

### 6.3 Jauns `PZV1_TOPIC_COLORS: dict[str, str]`

26 kanoniskām grupām pieskaņotas eksplicītas krāsas (dict konstante `src/generate.py` augšā). Pirmie 16 — pārkopēti no handoff `TOPICS` paletes (sk. `atmina-handoff/atmina/project/src/pozicijas-data.jsx:3-20`). Atlikušajiem 10 grupām — krāsas atvasinātas no HSL 36° roteri ar L=62%, S=52%, un manuāli pārbaudītas, lai nesakristu ar partiju krāsām (`PARTY_COLORS`). Plāna fāzē — eksplicīti uzstādīt visas 26 krāsas kodā; nav runtime atvasināšanas.

### 6.4 Render call

```python
claims = _fetch_claims(db)  # enriched
metrics = _fetch_pozicijas_metrics(db)

# topic_counts un all_parties jau aprēķinās augšā (esošās rindas 1960-1962)
# šeit tās tikai bagātinām ar krāsām un papildu laukiem
topics_with_counts_colors = [
    (name, count, PZV1_TOPIC_COLORS.get(name, "#8b8fa3"))
    for name, count in topic_counts.most_common()
]
parties_with_counts = [
    (name, _party_short_name(name), PARTY_COLORS.get(name, "#8b8fa3"),
     sum(1 for c in claims if c.get("party") == name))
    for name in sorted(set(c.get("party") for c in claims if c.get("party")))
]
# "Bez partijas" kategorija NULL party rindām
bez_partijas_count = sum(1 for c in claims if not c.get("party"))
if bez_partijas_count:
    parties_with_counts.append(("Bez partijas", "—", "#8b8fa3", bez_partijas_count))

politicians_with_counts = sorted(
    ((n, _slugify(n), sum(1 for c in claims if c.get("politician_name") == n))
     for n in {c["politician_name"] for c in claims}),
    key=lambda x: -x[2]
)

_render_page(env, "pozicijas.html.j2", atmina_dir / "pozicijas.html", {
    "claims": claims,
    "topics": topics_with_counts_colors,
    "parties_with_counts": parties_with_counts,
    "politicians_with_counts": politicians_with_counts,
    "metrics": metrics,
})
```

Šī render call **aizvieto** esošo render call, kas pievadīja `topics` (tuples), `parties`, `persons`. Vecā `parties` un `persons` keys vairs nav vajadzīgas — jaunais template prasa `parties_with_counts` un `politicians_with_counts`.

### 6.5 JS datu feed

Template emitē:
```js
var _pzData = [
  [topic, party, partyShort, partyColor, person, slug, stanceText, dateISO, sourceUrl, sourceDomain, confidence, confidenceTier],
  ...
];
```

**Pa 12 laukiem**, indeksi:
`IDX_TOPIC=0, IDX_PARTY=1, IDX_PARTY_SHORT=2, IDX_PARTY_COLOR=3, IDX_PERSON=4, IDX_SLUG=5, IDX_STANCE=6, IDX_DATE=7, IDX_SOURCE_URL=8, IDX_SOURCE_DOMAIN=9, IDX_CONF=10, IDX_CONF_TIER=11`.

`party` (pilns nosaukums) indeksā 1 ir *nepieciešams* filter loģikai — rail state salīdzina pilno nosaukumu ar `data-value` atribūtu pilno nosaukumu, un "Bez partijas" check lasa `!c[IDX_PARTY]` (tukša virkne NULL rindām, NEVIS `!c[IDX_PARTY_SHORT]` kas būtu `"—"` un vienmēr truthy).

Pa 12 laukiem × 1132 rindas ≈ 260 KB uncompressed, ~35 KB gzip.

---

## 7. Klienta puses uzvedība (`assets/pzv1.js`)

### 7.1 State

```js
const pzState = {
  topic: 'visas',
  party: 'Visas',
  persons: new Set(),
  period: 'visi',        // 'visi' | 'nedela' | 'menesis' | 'gads'
  confidence: 'visas',   // 'visas' | 'augsta' | 'laba'
  query: '',
  sort: 'date',          // 'date' | 'confidence' | 'topic'
  page: 1,
};
const PAGE_SIZE = 50;
```

### 7.2 Filtrēšana

`Array.filter` pār `_pzData`. Pārbaudes kārta:
1. **Topic**: `pzState.topic === 'visas' || topic === pzState.topic`
2. **Party**: `pzState.party === 'Visas' || (pzState.party === 'Bez partijas' && !partyShort) || party === pzState.party` (partijas pilns nosaukums salīdzināts ar state)
3. **Persons**: `pzState.persons.size === 0 || pzState.persons.has(person)`
4. **Period**: datums ≥ noteikta robeža (`nedela` → -7d, `menesis` → kalendārā mēneša sākums, `gads` → kalendārā gada sākums, `visi` → pass)
5. **Confidence**: `augsta` → `confidenceTier === 'augsta'`, `laba` → `confidenceTier in ('augsta', 'laba')`, `visas` → pass. **Piezīme**: nav atsevišķas "Mērena" opcijas — "Visas" ir vienīgais veids, kā redzēt Mērena rindas; tas atbilst handoff izvēlei.
6. **Query**: case-insensitive `includes` match uz JEBKURA no `person`, `topic`, `stanceText`

Kārtošana pēc `sort` axis (`date` → `dateISO.localeCompare` dilstoši; `confidence` → `confidence` dilstoši; `topic` → `topic.localeCompare` augošs). Tad slice uz `page` logu.

### 7.3 Faceted counts

Katrai rail rindai — rēķina, cik rindu atbilst state **izņemot šo asi**. Rezultāts parādās sadaļas labajā malā mono 10px.

Implementācija: viena `filterExceptAxis(axis)` funkcija, katra rail rinda izsauc ar savu asi.

### 7.4 Paginācija

- Filtra/kārtošanas/meklēšanas maiņa → `page = 1`
- Lapu skaits = `Math.ceil(filtered.length / PAGE_SIZE)`
- Rindas: `filtered.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE)`
- Paginācijas render — elipsis loģika: vienmēr rāda 1, pēdējo, un pašreizējo ±1; cits ar ellipsis

### 7.5 URL param starts

Pie ielādes (pirms pirmā render):
- `?persona=<Pilns Vārds>` — `pzState.persons.add(decodeURIComponent(v))`, atzīmē attiecīgo checkbox. **Saglabā esošo uzvedību** — persona profila `politiki/<slug>.html` joprojām linko šurp ar pilno vārdu.
- `?tema=<Tēmas nosaukums>` — `pzState.topic = decodeURIComponent(v)`; jāatbilst kādam no 26 kanoniskās grupām
- `?partija=<Pilns nosaukums>` — `pzState.party = decodeURIComponent(v)` (vai `"Bez partijas"`); **lietojam pilno nosaukumu, nevis short_name**, lai state salīdzinājumi paliek konsekventi rail klikšķu un URL params starpā
- Nekādas URL izmaiņas pēc ielādes (tāpat kā xv1 — deep link vienvirziena)

### 7.6 Interakcija

- Rail rindas klikšķ → uzstāda attiecīgo state
- Pēc tam, kad uzstādīts, klikšķis uz tās pašas aktīvās rindas → atceļ (atgriežas uz "visas")
- Persona details: `<details>` ar search input, search filtrē `<div>` rindas; klikšķis uz rindas toggle persons set
- Tēmas chip rindā → `pzState.topic = chip.dataset.topic` (klientā, nav URL maiņas)
- Avota domain → `window.open(sourceUrl, '_blank')`
- "Notīrīt ✕" chip → viss state uz noklusējumu

### 7.7 Keyboard

- `Escape` → aizver visus atvērtos `<details>` rail
- `/` → fokusē `.pzv1-search input` (nice-to-have, neblokē ship)

---

## 8. Responsive

@media (max-width: 900px):
- Grid stekojas: rail virs main (nav sticky uz mobilā)
- Header metrikas stekojas vertikāli
- Rindu grid kolonnas kolapsē uz divām: persona/datums virsū, tēma+teksts zem

Mobilais nav nulles prioritāte, bet nedrīkst būt lauzts.

---

## 9. Testi

### 9.1 Jauni unit tests (`tests/test_pozicijas_v2.py`)

- `test_fetch_pozicijas_metrics_totals` — mock DB ar 4 rindām, pārbauda total/last_week/confidence_good_pct
- `test_fetch_claims_enrichment` — ka katrai rindai ir party_color, party_short, confidence_tier, source_domain
- `test_confidence_tier_boundaries` — 0.9, 0.89, 0.75, 0.74, 0.0 → pareizas kategorijas
- `test_topic_colors_cover_all_26` — `PZV1_TOPIC_COLORS` atslēgas satur visas 26 kanoniskās grupas
- `test_party_short_bez_partijas` — NULL party → "—"

### 9.2 Manuālā regress pārbaude

1. `python -c "from src.generate import generate_public_site; generate_public_site()"`
2. `python serve.py` → `http://127.0.0.1:8080/pozicijas.html`
3. Pārbaudes saraksts:
   - Header metrikas atbilst realitātei (kopā/pēdējā nedēļā/ticamība ≥ laba)
   - Filter rail katra grupa strādā, counts atjaunojas
   - Rindu klikšķ uz persona → atver `politiki/<slug>.html`
   - `?persona=Evika Siliņa` deep-link izfiltrē pareizi
   - Paginācija strādā (prev/next/lapas numuri)
   - Search filtrē pēc teksta
   - "Notīrīt ✕" nomet visu state
   - Responsive zem 900px nav lauzts
4. X tabs (`/x.html`) joprojām strādā identiski (selektora maiņa)

---

## 10. Akceptkritēriji

- [ ] Visas 1132 position claim rindas pieejamas pēc filtrēšanas
- [ ] Nav NULL `confidence_tier` rindu renderējumā
- [ ] Filter counts sniedz pareizus faceted skaitļus visām 5 asīm
- [ ] `?persona=` un `?tema=` deep-linki darbojas kā līdz šim
- [ ] 3 header metrikas dinamiskas, balstītas uz DB
- [ ] 26 tēmām ir atšķirams topic-color chip
- [ ] X tabs nav nekādu regresijas simptomu
- [ ] Unit testi caur (`python -m pytest tests/test_pozicijas_v2.py -v`)
- [ ] Lighthouse tekošais score nepasliktinās
