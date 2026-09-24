# Profila Pārskats cilne — dizaina specifikācija

**Datums**: 2026-05-14
**Izcelsmes konteksts**: `wiki/profile-page-review.md` (review 2026-05-14) + `wiki/profile-page-review-response.md`. Bloks 1 ir merged (master `b1afe18`); šis spec sedz Bloks 2 — Pārskata cilnes ieviešanu. **Iteration 2**: pēc empīriskās DB pārbaudes 5-bloku struktūra reducēta uz 3, atmesti pārklājošie un sparse signāli.
**Saistītie specs**: `2026-04-09-document-politicians-junction-design.md` (politiķu DB joins), `2026-04-17-featured-images-design.md` (atsauces UI komponenti).
**Saistītie izpildes invariants**: CLAUDE.md §4 (claim_type), §5 (speaker_id).
**Wiki saturs**: `wiki/persons/<slug>.md` paliek `wiki_profile` HTML avots caur `_common._load_wiki_profile()` — Pārskats cilne to **rāda**, ne pārveido.
**CHANGELOG atsauce pēc ieviešanas**: `wiki/CHANGELOG.md § Profila Pārskats cilne (Bloks 2)`
**Statuss**: design draft v2 — gaida lietotāja review

---

## 1. Mērķis

Profila pirmajam ekrānam jāatbild **"kas par šo cilvēku šobrīd ir svarīgi?"**. Pašreizējais default `timeline` cilne 15 profilos ir tukša, citos sākas ar veciem ierakstiem, nereprezentējot to, kas patreiz aktīvs.

Risinājums: **jauna `Pārskats` cilne** kā default politiķiem ar 3 curatētiem signāla blokiem — pēdējā aktivitāte ar saturu, ievērojamākā pretruna, dominējošās tēmas. Tukšs bloks netiek renderēts; visi 3 tukši → Pārskats cilnes nav, fallback uz timeline.

Žurnālisti / analītiķi / organizācijas saglabā `Publikācijas` kā default (paplašinājums Bloks 1 work) — Pārskats viņiem netiek izveidots, jo politiska signāla bloku saturs nav primārā vērtība.

---

## 2. Scope

### Iekļauts

**M1 — Pārskats cilne ar 3 signāla blokiem** (skat. § 3)

- Cilne `parskats` `_profile_tab_set` base mapping prefiksā politikiem (deputy / minister / mep / regional / politician / former)
- Trīs bloki: pēdējā aktivitāte, ievērojamākā pretruna, dominējošās tēmas
- Empty Pārskats (visi 3 zem threshold) → cilne netiek pievienota; fallback uz timeline

**M2 — Wiki + sintēžu pārvietošana**

- `templates/politician.html.j2:104-108` (`wiki_profile`) un `:110-127` (`related-syntheses`) pārvieto Pārskats cilnes apakšā
- Risina scroll-starp-tab-joslu-un-tab-saturu (review #1, response M3)

**M3 — Default cilne pa profile_kind**

| profile_kind | Default |
|---|---|
| deputy / minister / mep / regional / politician / former | `parskats` ja netukšs, citādi `timeline` |
| journalist / analyst | `publikacijas` ja netukšs, citādi `timeline` |
| organization | `publikacijas` ja netukšs, citādi `saites` ja netukšs, citādi `timeline` |
| inactive | `parskats` ja netukšs, citādi `timeline` |

Implementācija — `_profile_tab_set` saraksta **pirmais elements** = default. Konstruēšanas laikā jau veikta data-presence filtrācija; template lieto `tab_set[0]` taisni.

**M4 — URL hash atbalsts**

- `#parskats`, `#timeline`, `#pozicijas`, `#saeima`, `#pretrunas`, `#komentari-by`, `#publikacijas`, `#saites`, `#deklaracijas` page-load laikā
- Ja hash atbilst `tab_set` cilnei → aktivē to (overrides default)
- Ja hash nav `tab_set` → silent fallback uz default (NE paziņojums — vienkāršāk; lietotājs vienkārši redz default cilni)
- Tab klikšķis aktualizē URL hash ar `history.replaceState`

### Ārpus

- **Saišu bilance bloks** (review § 6 atbalsts, response M1) — empīriski DB rāda tikai 15 (politiķis, tension_type) pārus ar count≥2 pēdējos 180d. ~10 profili. Pārskatā tas būtu redzams 6% gadījumos — nepamato bloka eksistenci. Saites cilne **jau eksistē** šim. Atstāj.
- **VAD delta bloks** — prasa atsevišķu delta loģikas spec (`vad_declarations` diff šobrīd nav implementēts). Skat. Bloks 3.
- **Topic-chip → filter pre-aktivācija** — Bloks C topic-chips saites uz plain `#pozicijas`. Lietotājs filtrē manuāli. Drops JS sarežģījumu.
- **Saeimā cilnes redizains, Saites story-driven sub-summaries, Publikācijas filtri, ARIA tab roles, data freshness, citation pogas, visual hero hierarchy** — visi Bloks 3.
- **Pozīcijas tukšo cilņu apstrāde (58 profili)** — risināts netieši: Pārskats ir default, "Pozīcijas 0" vairs nav pirmais ekrāns. Pati cilne paliek redzama (satur nested X/news fallback non-žurnālistiem).
- **Saites label-precizitāte** (90 profili rāda "Saites 0" ar vote_alignment saturu) — Bloks 3.

---

## 3. Pārskata signālu loģika

### 3.1 Bloks A — Pēdējā aktivitāte ar saturu

Apvienots "jaunākā pozīcija" + "pēdējā aktivitāte" — empīriski tas ir tas pats datu punkts vairumam politiķu.

- **Datu avots**: jaunākais no:
  - `claims` ar `claim_type='position'`, `opponent_id = pid`, `stated_at IS NOT NULL`
  - `saeima_individual_votes` joined `saeima_votes` ar `politician_id = pid`
- **Threshold**: nav. Bloks redzams, ja eksistē kāda aktivitāte vispār.
- **UI render**: relatīvais laiks ("vakar", "pirms 3 dienām", "pirms mēneša") + tips ("pozīcija" / "balsojums") + topic + truncated content (max 200 zīmes) + avota link.
- **Empty fallback**: bloks netiek renderēts.

### 3.2 Bloks B — Ievērojamākā pretruna

- **Datu avots**: `contradictions` JOIN `claims` (old + new), `opponent_id = pid`.
- **Threshold**:
  - `confirmed = 1` (slēpj nepubliskotās — `store_contradiction()` default ir 0)
  - `salience >= 0.5` (empīriski: 12/17 confirmed atbilst; mediāns 0.55)
  - ORDER BY `salience DESC, detected_at DESC`, LIMIT 1
- **UI render**: severity badge + topic + summary (max 240 zīmes) + ΔT delta-days + saite uz `pretrunas.html#ct-<id>`.
- **Empty fallback**: bloks netiek renderēts.

### 3.3 Bloks C — Dominējošās tēmas

- **Datu avots**: `claims` ar `claim_type='position'`, `opponent_id = pid`, `stated_at >= date('now', '-180 days')`. GROUP BY `topic`, ORDER BY `COUNT(*) DESC`, LIMIT 3.
- **Threshold**: tēma redzama tikai ja `count >= 3` pēdējos 180 dienās. Empīriski: 226 (politiķis, tēma) pāri 69 politiķiem — Bloks C redzams 40% profilos.
- **UI render**: 3 topic-chips ar count badge ("Aizsardzība un drošība · 12"). Klikšķis vada uz `#pozicijas` (bez pre-filtra).
- **Empty fallback**: bloks netiek renderēts.

### 3.4 Empty Pārskats — fallback uz timeline

Ja nevienam no A/B/C nav datu virs threshold:

- `_profile_tab_set` Pārskata cilni nepievieno
- Default cilne kļūst `timeline` (esošā uzvedība)

---

## 4. Default cilne un URL hash

### 4.1 Lēmuma secība (vienkāršota — 3 līmeņi)

```
1. Ja URL hash atbilst kādai `tab_set` cilnei → aktivē hash
2. Citādi → aktivē tab_set[0] (default, jau curated _profile_tab_set'ā)
3. Ja tab_set tukšs (nedrīkstētu notikt) → timeline
```

Lēmums "vai Pārskats ir default" notiek `_profile_tab_set` būves laikā (Pārskats pievieno tikai ja `has_parskats=True`). Template loģika paliek triviāla.

### 4.2 URL hash JS

`{% block scripts %}` paplašinājums:

```javascript
const hash = window.location.hash.replace('#', '');
const validTabs = new Set([{{ tab_set | map('tojson') | join(',') }}]);
if (hash && validTabs.has(hash)) {
  const btn = document.querySelector(`[data-tab="${hash}"]`);
  if (btn) showProfileTab(hash, btn);
}

const origShow = window.showProfileTab;
window.showProfileTab = function(tab, btn) {
  origShow(tab, btn);
  history.replaceState(null, '', '#' + tab);
};
```

Silent fallback (M8 caveat): ja hash mērķē uz neredzamu cilni → vienkārši default cilne aktīva, bez explicit paziņojuma. Vienkāršāk; lietotājs to viegli pamana.

---

## 5. Datu prepacking

### 5.1 Helper

`src/render/politicians.py`:

```python
def _build_parskats_data(
    db: sqlite3.Connection,
    pid: int,
    positions: list[dict],
    contradictions: list[dict],
) -> dict[str, Any]:
    """Compose Pārskats cilne signal blocks.

    Returns dict with optional keys: latest_activity, top_contradiction,
    dominant_topics. Each key is omitted if its block is below threshold,
    so the template can render conditionally without further checks.
    """
    ...
```

### 5.2 Threshold konstantes

Modulā eksponētas testiem un nākotnes koriģēšanai:

```python
PARSKATS_CONTRADICTION_SALIENCE_MIN = 0.5
PARSKATS_TOPIC_COUNT_MIN = 3
PARSKATS_TOPIC_WINDOW_DAYS = 180
```

Empīriskā ground: pretrunu mediāns confirmed=1 ir 0.55 (12/17 ≥ 0.5); tēmu count ≥3 / 180d aptver 40% profilus (69 / 174).

### 5.3 `_profile_tab_set` paplašinājums

Jauns parametrs `has_parskats: bool`:

```python
base = {
    "deputy":       ["parskats", "timeline", "pozicijas", "saeima", "pretrunas", "saites"],
    "minister":     ["parskats", "timeline", "pozicijas", "pretrunas", "saites"],
    "mep":          ["parskats", "timeline", "pozicijas", "pretrunas", "saites"],
    "regional":     ["parskats", "timeline", "pozicijas", "pretrunas", "saites"],
    "politician":   ["parskats", "timeline", "pozicijas", "pretrunas", "saites"],
    "former":       ["parskats", "timeline", "pozicijas", "saeima", "pretrunas", "saites"],
    "journalist":   ["timeline", "komentari-by", "publikacijas"],  # nemainīts
    "analyst":      ["timeline", "komentari-by", "publikacijas"],
    "organization": ["timeline", "pozicijas", "saites"],
    "inactive":     ["parskats", "timeline"],
}
tabs = [t for t in base.get(kind, ["timeline"]) if not (t == "parskats" and not has_parskats)]
# ... esošā journalist/analyst pievienošanas loģika + vad
```

---

## 6. Mērāmie kritēriji

Pytest tests (NE atsevišķs skripts) `tests/test_render_politicians_parskats.py`:

1. **Non-empty default tab**: 5 reference profilu fixture (deputy aktīvs, deputy klusais, žurnālists, organization, former). Render profila lapu, parse default tab content, assert `len(text.strip()) > 0`.
2. **Pārskats threshold**: feed test fixture ar tieši `salience=0.49` pretrunu → bloks B nav. Pacelt uz 0.50 → bloks B ir.
3. **Empty Pārskats fallback**: politiķis bez claims/contradictions → `tab_set[0] == "timeline"`.
4. **URL hash**: smoke test, ka template JS bloks ir injecēts, `validTabs` set satur visus `tab_set` elementus.

---

## 7. Implementācijas secība

3 commits:

1. **Commit 1**: `_build_parskats_data` helper + threshold konstantes + `_profile_tab_set` paplašinājums + jaunais `has_parskats` parametrs + tests (§ 6 1-3). Politiķi nesaņem Pārskata cilni vēl — template nelieto.
2. **Commit 2**: Template — `parskats` cilnes saturs (3 bloki) + `wiki_profile` + `related-syntheses` pārvietošana Pārskata iekšienē + URL hash JS (§ 4.2) + smoke test (§ 6.4). Baseline regen.
3. **Commit 3** (opcionāls): CSS polish — Pārskata bloku spacing, mobile responsiveness, visual hierarchy (ne hero, vienkārši padding/gaps).

Katrs commit atstāj sistēmu **renderable un testable**.

---

## 8. Atvērti jautājumi

**Q1**: Bloks A relatīvais laiks ("vakar" / "pirms 3 dienām" / "pirms mēneša") — paši formatējam Python pusē, vai izmantojam JS klienta-puses bibliotēku? **Atbilde**: Python pusē — vienkāršs `(now - stated_at).days` → formatēta string. Stabils, prediktīvs HTML.

**Q2**: Pārskata cilnes saturu var dalīt ar URL caur `#parskats`. Bet `#parskats` tieši kopēts no Pārskata sniega — vai pievienojam permalink poga pie katra bloka (Q-share)? **Atbilde**: nē Bloks 2. Permalink ir Bloks 3 polish (data-freshness + share/citation poga).

**Q3**: Vai Bloks C topic-chips vajadzīgi tooltip ar pēdējo claim tās tēmā? **Atbilde**: nē sākotnēji. Lietotājs klikšķē uz `#pozicijas` un redz pilnu sarakstu.

---

## 9. Riski

**R1** — Bloku ordering fiksēts (A → B → C). Politiķim, kuram pretruna ir svarīgāka par jaunāko pozīciju, B vēlams pirmais. Akceptēts: fixed ordering vienkāršāks, prediktīvs. Dynamic ordering paliek vēlākai polish iterācijai.

**R2** — Empty Pārskats (visi 3 zem threshold) noved pie timeline fallback. Jaunpienākušie politiķi, kuriem nav vēl claims/contradictions, joprojām redz Pārskata-nepieejamību. Sagaidāmais.

**R3** — Threshold cipari ir DB-snapshot-2026-05-14 kalibrēti. Ja gada laikā contradictions count palielinās 10×, mediāns var pārvietoties. Konstantes eksponētas modulē — koriģēt vienā vietā.

---

## 10. CHANGELOG entry (rakstīt pēc merge)

```markdown
### 2026-05-XX — Profila Pārskats cilne (Bloks 2)

**Konteksts**: profilu lapu review Bloks 2 — risina default-tab tukšuma problēmu (15 profili) un pirmā ekrāna signāla prioritāti.

**Izmaiņas**:
- Jauna `parskats` cilne politiķiem (deputy/minister/mep/regional/politician/former/inactive) ar 3 signāla blokiem: pēdējā aktivitāte ar saturu, ievērojamākā pretruna (salience≥0.5, confirmed=1), top 3 dominējošās tēmas (count≥3 / 180d).
- Default cilne pa profile_kind: politiķi → Pārskats (ja netukšs); žurnālisti/analītiķi → Publikācijas; organizācijas → Publikācijas/Saites.
- `wiki_profile` un `related-syntheses` pārvietoti Pārskata cilnes apakšā (atrisina scroll-starp-tab-joslu-un-saturu).
- URL hash atbalsts (`#parskats`, `#pozicijas` utt.) ar silent fallback uz default, ja hash mērķē uz neredzamu cilni.
- Pytest tests `tests/test_render_politicians_parskats.py`.

**Risks**: Pārskats ir tukšs politiķiem ar veciem datiem (>180d klusē) → fallback uz timeline. Bloks F (VAD delta) un D (saites bilance) atstāti Bloks 3 — pirmais prasa atsevišķu spec, otrais ir DB-sparse.
```

---

**Apstiprināšanas signāls operatoram**: § 3 threshold cipari ir empīriski kalibrēti pret 2026-05-14 DB snapshot. § 4.1 default-tab loģika ir vienkāršota 3 līmeņos. Pirms koda — pārskatīt § 3 un § 4. Tās ir vietas, kur pēc merge maiņa prasa baseline regen.
