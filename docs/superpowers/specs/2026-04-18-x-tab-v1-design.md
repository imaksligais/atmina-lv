# X tab V1 redizains — dizaina specifikācija

**Datums:** 2026-04-18
**Branch:** `design/x-tab-v1`
**Avots:** `atmina-handoff/atmina/project/src/x-v1.jsx` (Claude Design mock)
**Statuss:** Dizains apstiprināts, gatavs implementācijas plānam

---

## 1. Mērķis un scope

Aizstāt pašreizējo `templates/x.html.j2` vienkāršo karšu plūsmu ar V1 dizainu: divkolonnu layout ar metrisku headeri, kreisu aside (leaderboard + topiki), ticker stila galveno plūsmu. Pievienot persona/partija/topiks filtrus bez auto-atjauno indikatora (statiskais sites to nepiedāvā īsti).

**Iekļauts scope-ā:**
- `documents` tabulas migrācija — jaunas kolonnas `reply_count`, `retweet_count`, `favorite_count` (nullable). twikit jau šos laukus izvelk (`src/x_scraper.py:47-49`), bet datu bāze tos izmet.
- Insert path-a papildinājums: jauni tvīti un mention-i glabās engagement skaitliskos datus.
- Ticker item footer rāda engagement ikonas (`↩ ↻ ♡`) post-iem, kas ienāca pēc migrācijas.

**Ārpus scope:**
- **Engagement backfill** vecajiem dokumentiem (~3200 twitter + ~3400 mention). Prasītu twikit rerun visiem source_url — atsevišķs darbs. Veci dokumenti graceful degradācijā rādīs footer-u bez engagement ikonām.
- Thread clustering (nav kam veikt — izmantojam eksistējošos `claims.topic`).
- V2/V3 X tab varianti.
- Citu tabu (pretrunas, pozīcijas) redizains.
- `view_count`, `quote_count`, `bookmark_count` kolonnas — nav V1 displejā vajadzīgas; pievienos, ja nākotnē vajadzēs.

---

## 2. Arhitektūra

**Template:** `templates/x.html.j2` pilnīgi pārrakstīts.
**Python:** `src/generate.py::_fetch_x_data()` paplašināts ar 3 jaunām datu blokiem.
**CSS:** Jauna sekcija `/* X V1 */` `src/assets/style.css` ar `.xv1-*` klasēm, nejaucot ar esošajām `.x-card`.
**JS:** Clean-room filter loģika — 2 dropdowni (persona, partija) + 3 ticker tabs + topic filter no aside klikšķa.

---

## 3. Datu plūsma

### 3.1 `_fetch_x_data()` atgriež

```python
{
    # esošie
    "posts":      [post_dict, ...],   # 300 jaunākie; katrs bagātināts ar .topic + .party_color
    "mentions":   [mention_dict, ...],# 300 jaunākie; katrs bagātināts ar .topic + .party_color + .mentioned_by
    "parties":    [str, ...],         # persona filtra dropdown
    "politicians":[str, ...],         # persona filtra dropdown

    # jauni
    "metrics": {
        "posts_total":    int,  # COUNT(*) no documents WHERE platform IN ('twitter','x')
        "mentions_total": int,  # COUNT(*) no documents WHERE platform='x_mention'
        "last_24h":       int,  # COUNT(*) kur scraped_at > datetime('now','-1 day') platform IN ('twitter','x','x_mention')
    },
    "top_mentioned": [
        # Top 8 pēc pēdējām 7 dienām. Tikai tracked_politicians ar mention_target lomu.
        {
            "name":        str,   # "Elīna Treija"
            "slug":        str,
            "handle":      str,   # "@elina_treija" ja social_accounts ir, citādi None
            "party_short": str,   # "NA"
            "party_color": str,   # "#ca8a04"
            "count":       int,   # 7d mention count
            "trend":       str,   # "+12" / "-2" / "0"  (this_7d - prev_7d)
        }, ...
    ],
    "trending_topics": [
        # Top 5 no claims.topic pēdējās 7 dienās, JOIN documents uz source_url kur platform IN ('twitter','x','x_mention').
        {
            "topic":         str,      # "airBaltic"
            "mentions":      int,      # kopējais post+mention count ar šo topiku
            "party_colors":  [str...], # unikālās autora-partijas krāsas, max 5
        }, ...
    ],
}
```

### 3.2 Katra `post` / `mention` bagātināšana

- **`.topic`** — JOIN `claims` uz `source_url`. Ja vairāki claimi, ņem ar visaugstāko `importance` DESC, tad `created_at` DESC. Ja nav claim-a → `None`.
- **`.party_color`** — no `PARTY_COLORS` dict `generate.py` (jau eksistē). Ja partija nav mapēta → `#64748b` (neitrāls pelēks).
- **`.mentioned_by`** (tikai mentioniem) — pirmā `@handle` dokumenta content-a, kas nav mērķa pašrocīgais handle. Regex: `r'@([a-zA-Z0-9_]+)'`, atmest mērķa. Ja nav — `None`.
- **`.reply_count`, `.retweet_count`, `.favorite_count`** — ja DB rindā ir (post-migration dokumenti), nodod kā int. Ja `NULL` (pre-migration) → `None`. Template pārbauda `is not None` un attiecīgi renderē vai izlaiž engagement rindu.

### 3.3 Topic coverage sagaidāmais līmenis

- Posts (`platform='twitter'`): **~23%** ar topiku (758/3229 eksistošajos datos)
- Mentions: **~0%** ar topiku (claims netiek extractēti no mentioniem)

Tas ir apzināts — graceful degradation (skat. 5.2).

### 3.4 Trend aprēķins (`top_mentioned[].trend`)

```sql
-- Šī nedēļa:  mention counts per politician kur scraped_at > now-7d
-- Iepriekšējā: counts kur scraped_at IN [now-14d, now-7d]
-- trend = this_week - prev_week, formatēts kā "+N" / "-N" / "0"
```

Ja politiķis nav iepriekšējā nedēļā bija → trend ir visa šīs nedēļas count kā `+N`.

---

## 4. Template struktūra (`templates/x.html.j2`)

```jinja
{% extends "base.html.j2" %}
{% set active_page = "x" %}
{% block title %}X / Twitter{% endblock %}

{% block content %}
<section class="xv1-section">

  {# Header: kicker + h1 + 3 metric tiles #}
  <header class="xv1-header">
    <div class="xv1-header-title">
      <div class="xv1-kicker">X / Twitter ieraksti un pieminējumi</div>
      <h1 class="xv1-h1">Publiskās sarunas</h1>
    </div>
    <div class="xv1-metrics">
      <div class="xv1-metric"><span class="xv1-metric-label">Ieraksti</span>
                              <span class="xv1-metric-value">{{ metrics.posts_total }}</span></div>
      <div class="xv1-metric"><span class="xv1-metric-label">Pieminējumi</span>
                              <span class="xv1-metric-value">{{ metrics.mentions_total }}</span></div>
      <div class="xv1-metric"><span class="xv1-metric-label">Pēdējās 24h</span>
                              <span class="xv1-metric-value">{{ metrics.last_24h }}</span></div>
    </div>
  </header>

  {# 2-kolonnu layout: aside + main #}
  <div class="xv1-grid">

    <aside class="xv1-aside">
      <div class="xv1-rail-title">Pieminētākie · pēdējās 7 dienas</div>
      <div class="xv1-mention-list">
        {% for m in top_mentioned %}
        <button class="xv1-mention-row" data-persona="{{ m.name }}">
          <span class="xv1-rank">{{ "%02d" % loop.index }}</span>
          <div class="xv1-mention-name">
            <div class="xv1-mention-author">{{ m.name }}</div>
            <div class="xv1-mention-handle" style="color:{{ m.party_color }}">
              {{ m.handle or "" }} · {{ m.party_short }}
            </div>
          </div>
          <div class="xv1-mention-count">{{ m.count }}</div>
          <div class="xv1-mention-trend xv1-trend-{{ 'up' if m.trend[0]=='+' else 'down' if m.trend[0]=='-' else 'flat' }}">
            {{ m.trend }}
          </div>
        </button>
        {% endfor %}
      </div>

      <div class="xv1-rail-title">Topiki · pēdējās 7 dienas</div>
      <div class="xv1-topic-list">
        {% for t in trending_topics %}
        <button class="xv1-topic-row" data-topic="{{ t.topic }}">
          <div class="xv1-topic-mix">
            {% for c in t.party_colors %}<span class="xv1-topic-dot" style="background:{{ c }}"></span>{% endfor %}
          </div>
          <div class="xv1-topic-name">{{ t.topic }}</div>
          <div class="xv1-topic-meta">{{ t.mentions }} pieminējumi · {{ t.party_colors|length }} partijas</div>
        </button>
        {% endfor %}
      </div>
    </aside>

    <main class="xv1-main">
      {# Ticker bar: tabs pa kreisi + filtri pa labi #}
      <div class="xv1-ticker-bar">
        <div class="xv1-tabs">
          <button class="xv1-tab active" data-type="">Visi</button>
          <button class="xv1-tab" data-type="post">Tikai ieraksti</button>
          <button class="xv1-tab" data-type="mention">Tikai pieminējumi</button>
        </div>
        <div class="xv1-filters">
          {# Persona dropdown #}
          {# Partija dropdown #}
          {# Kad aktīvs topika filtrs — parādīt chip "airBaltic ×" #}
        </div>
      </div>

      {# Ticker items — apvienoti posts+mentions, sortēti pēc ts DESC #}
      <div id="xv1-feed" class="xv1-feed">
        {% for x in feed %}
        <article class="xv1-item" data-type="{{ x.kind }}"
                 data-persona="{{ x.persona }}" data-party="{{ x.party }}"
                 data-topic="{{ x.topic or '' }}" data-date="{{ x.date }}">
          {# ... 2-kolonnu struktūra (80px ts / 1fr content) ... #}
        </article>
        {% endfor %}
      </div>
    </main>

  </div>
</section>
{% endblock %}
```

**Piezīme:** `feed` ir iepriekš apvienots `posts + mentions` saraksts, sortēts pēc `scraped_at DESC`, un katram elementam pievienots `.kind = 'post' | 'mention'` un `.persona = politician_name` (posts) vai `.persona = target_name` (mentions). To pievieno `generate.py`, ne template.

---

## 5. Ticker item struktūra

### 5.1 Vispārīgais layout

```
┌──────────┬──────────────────────────────────────────────────────────┐
│ PIEMIN.  │ Elīna Treija  @elina_treija · NA  ↳ no @ozols_rigā       │
│ 13:48    │                                                          │
│ 2026-04-18│ @Elina_Treija Situācijas ir dažādas. Nevajag visus...    │
│          │                                                          │
│          │ [airBaltic] [NA] · ↳ no @ozols_rigā · atvērt X ↗         │
└──────────┴──────────────────────────────────────────────────────────┘
```

- Kreisā sleja: 80px, mono 10, kicker (`PIEMIN.` sarkanīgi neitrāls / `IERAKSTS` brand red), laiks, datums.
- Labā sleja: author/handle rinda, body (serif 15), footer ar chip-iem.

### 5.2 Footer — graceful degradation

Footer satur divas daļas: **chip-i** (topiks + partija) un **engagement/action** (counts + link).

| Tips | Topiks | Engagement | Footer |
|------|--------|------------|--------|
| post | ir | ir | `[topika chip] [partija chip] · ↩ N  ↻ N  ♡ N · atvērt X ↗` |
| post | ir | nav (pre-migration) | `[topika chip] [partija chip] · atvērt X ↗` |
| post | nav | ir | `[partija chip] · ↩ N  ↻ N  ♡ N · atvērt X ↗` |
| post | nav | nav | `[partija chip] · atvērt X ↗` |
| mention | nav | parasti nav | `[partija chip] · ↳ no @mentionedBy · atvērt X ↗` |
| mention | ir (rets) | parasti nav | `[topika chip] [partija chip] · ↳ no @mentionedBy · atvērt X ↗` |

**Piezīme:** mentioniem engagement ir reti (atbildes tvīti), bet tehniski kolonnas būs arī tur — ja ir, rādām kā post-iem.

### 5.3 Text truncācija

Atceļam pašreizējo 280-char `content_short`. V1 rāda `x.text` pilnā garumā. Ja tweet >700 char (reti), CSS `max-height: 12em + overflow: hidden + gradient fade` + "rādīt vairāk" JS toggle. Defoltā nekāda truncācija.

### 5.4 Hover efekts

No V1 mock-a: 3px left border politikas partijas krāsā + fona `surface` tint (`#161a22`). `margin-left: -3px` lai saturs nekustētos.

---

## 6. Filtru darbība

### 6.1 Filtru stāvokļi

3 neatkarīgi filtri, AND kombināciju (visi jāmatē, lai ticker item parādītos):

1. **Tips** — `""` (visi) / `"post"` / `"mention"`. Radio (tikai viens aktīvs).
2. **Persona** — multi-select, 0 vai vairāk.
3. **Partija** — multi-select, 0 vai vairāk.
4. **Topiks** — 0 vai 1 (vienkāršs chip `airBaltic ×`).

### 6.2 Filtru izcelsme

- **Tips**: ticker tabs (Visi / Tikai ieraksti / Tikai pieminējumi).
- **Persona + Partija**: dropdowni ticker bar labajā pusē, mono stils.
- **Topiks**: klikšķis uz aside `xv1-topic-row`. Pievieno URL kā `?tema=airBaltic`, rāda kā chip ar × ticker-a labajā malā. Nav atsevišķa dropdown-a — topic filtrs tiek nolasīts tikai no aside klikšķa vai URL parametra.

### 6.3 Aside reakcija uz filtriem

**Aside paliek globāls.** Leaderboards un topiki vienmēr rāda visu datu kopu pēdējām 7 dienām, neatkarīgi no ticker-a filtriem. Pamatojums — aside ir "kas notiek platformā kopumā" signāls, nevis "kas atbilst manam filtram".

**Izņēmums:** klikšķis uz aside `xv1-mention-row` iestata `persona` filtru uz to politiķi. Klikšķis uz `xv1-topic-row` iestata topic filtru.

### 6.4 URL parametri

- `?persona=Name` — preselect persona filtru (saglabā savietojamību ar pašreizējo linku no personas.html un cituviet).
- `?partija=NA` — preselect partija filtru.
- `?tips=post` vai `?tips=mention` — preselect ticker tab.
- `?tema=airBaltic` — preselect topika filtru.

Visi savienojami (`?persona=Šlesers&tips=post`).

---

## 7. Responsive breakpoints

| Platums | Layout |
|---------|--------|
| >900px | V1 2-kolonnu grid `340px 1fr` |
| 600–900px | Aside pārceļas uz augšu kā 2-kolonnu strip (Pieminētākie | Topiki), tad ticker zemāk vienā kolonnā |
| <600px | Aside kolapsē zem `"Pieminētākie ▾"` + `"Topiki ▾"` accordion-iem. Ticker pilnā platumā. Filtri ticker bar-ā wrap-ojas zem tabs rindas. |

---

## 8. CSS tokens (no `primitives.jsx`)

Atkārtoti izmantot eksistējošos CSS mainīgos `style.css` (`--bg`, `--text`, etc.). Pārliecināties, ka sekojošie pastāv vai pievienot:

```css
--xv1-border-soft: #1f2432;
--xv1-surface:     #161a22;
--xv1-surface-hi:  #242838;
--xv1-text-muted:  #8b8fa3;
--xv1-text-dim:    #5e6478;
--xv1-brand-red:   #B71C1C;
--xv1-green:       #22c55e;
--xv1-red:         #e25b5b;
--xv1-mono:        'JetBrains Mono', ui-monospace, monospace;
--xv1-serif:       'Newsreader', Georgia, serif;
```

Pārbaudīt, vai `Newsreader` fonts jau ir ielādēts base.html.j2-ā — ja nav, pievienot Google Fonts link. Pašreizējais site-s izmanto citu serif kā galveno; V1 izmanto Newsreader kā raksturīgu "redakcionālu" stilu.

---

## 9. Failu izmaiņas

| Fails | Izmaiņu veids |
|-------|---------------|
| `src/db.py` | Schema migration — pievienot `reply_count`, `retweet_count`, `favorite_count` kolonnas (INTEGER, nullable) `documents` tabulai. Migration idempotenta (ja kolonna jau ir, skip). |
| `src/ingest.py` (vai kur notiek insert) | Insert statement-s pieņem un saglabā engagement laukus no scraper dict-a. |
| `src/x_scraper.py` | Jau ekstrahē `reply_count`, `retweet_count`, `favorite_count` (`:47-49`). Pārbaudīt, ka insert call nodod šos laukus tālāk (šodien tos izmet). |
| `src/x_mentions.py` | Tāpat — jau ekstrahē (`:85-87`), pārbaudīt insert path-u. |
| `src/generate.py` | `_fetch_x_data()` paplašināt: `metrics` + `top_mentioned` + `trending_topics`; `.topic`/`.party_color`/`.mentioned_by`/`.reply_count`/`.retweet_count`/`.favorite_count` bagātināšana; feed sortēt un pārsūtīt template-ā. |
| `templates/x.html.j2` | Pilnīgi pārrakstīts V1 dizainā. Engagement rāda ar `{% if x.favorite_count is not none %}...{% endif %}`. |
| `src/assets/style.css` | Jauna sekcija `/* ===== X V1 ===== */` ar `.xv1-*` klasēm. Vecās `.x-card` klases sākotnēji neaiztiek — lai var ātri rollback-ot. |
| `templates/base.html.j2` | Pievienot Newsreader Google Fonts link (ja nav). |
| `tests/test_generate.py` | Jauns tests `test_fetch_x_data_v1_fields` — pārliecinās, ka `_fetch_x_data()` atgriež `metrics`, `top_mentioned`, `trending_topics` un ka `posts[0]` ir `topic` + `party_color` atslēgas. |
| `tests/test_db_migration.py` (ja nav) | Tests, ka migration idempotenta un ka jaunās kolonnas ir nullable. |

---

## 10. Deploy / verifikācija

1. `git checkout -b design/x-tab-v1` no master.
2. **Phase 1:** DB migration + scraper/ingest patch. Pārbaudīt ar `python -c "from src.db import get_db; db=get_db(); print([r['name'] for r in db.execute('PRAGMA table_info(documents)')])"` — redz jaunās kolonnas. Palaist vienu X scrape ciklu (manuāli), apstiprināt, ka jauni dokumenti glabā engagement (`SELECT reply_count, retweet_count, favorite_count FROM documents WHERE scraped_at > datetime('now','-10 minute')`).
3. **Phase 2:** `_fetch_x_data()` paplašināšana, tests.
4. **Phase 3:** Template + CSS pārrakstīšana, JS filtri.
5. `python -m pytest tests/ -v` — visi testi iziet.
6. `python -c "from src.generate import generate_public_site; generate_public_site()"` — ģenerē `output/atmina/x.html`.
7. Manuāla vizuāla pārbaude:
   - Desktop 1200px: aside kreisā + ticker labā.
   - Tablet 768px: aside strip augšā.
   - Mobile 375px: accordion aside, ticker pilnā platumā.
8. `?persona=Ainārs Šlesers` URL parametrs preselect-ē filtru pareizi.
9. Klikšķis uz aside `Pieminētākie` rindas filtrē ticker-u.
10. Klikšķis uz aside `Topiki` rindas pievieno topic chip + filtrē.
11. Jauni tvīti (post-deploy) rāda engagement (`↩ ↻ ♡`) footer-ā; vecie — bez engagement, bet citādi OK.
12. **Tikai pēc user apstiprinājuma:** `bash scripts/deploy.sh --dry-run`, tad `bash scripts/deploy.sh`.
13. Merge uz master kā atsevišķs commit pēc deploy verifikācijas.

---

## 11. Atklātie jautājumi / risks

- **Newsreader fonta pievienošana** — vai site-s jau izmanto, vai pievienot tikai X lapai? Izvēle sesijā.
- **Mentioned-by regex** — ja dokumenta content ir tukšs vai sākas ar mērķa handle, var atdot `None`. Graceful: rādīt tikai "↳ no ?".
- **`PARTY_COLORS` coverage** — ja tracked_politicians pievienots ar partiju, kurai nav krāsas mapes, rādīs neitrālu pelēku. Jāpārliecinās, ka visas aktīvās partijas ir mapētas.
- **Performance**: jauni JOIN-i + 7-dienu/14-dienu aggregationām uz `documents`+`claims`+`document_politicians` — ja palēnina `generate_public_site()`, pievienot indeksus vai cachēt.
- **Engagement „blakne"**: pirmās dienas/nedēļas pēc deploy ticker rādīs engagement tikai jaunākajos tvītos. Vecāki dokumenti (ko twikit nav piesaucis pēc migrācijas) rādīs bez engagement. Vizuāli jūtas kā „jauni vs veci". Graceful, bet uzmanīties — ja tas šķiet problemātiski, nākamais solis: palaist twikit rerun uz visiem source_url (atsevišķs darbs).
- **Engagement skaitļu aktualitāte**: twikit atdod *pašreizējo* snapshot vērtību, ne likuma. Ja tvīts iet viral pēc mūsu scrape, mūsu DB rādīs vecos skaitļus. Nenoteikti, vai periodic refresh ir vajadzīgs — to izlemj nākamajā iterācijā.
