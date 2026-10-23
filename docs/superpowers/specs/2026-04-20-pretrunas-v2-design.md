# Pretrunas V2 — Dizaina specifikācija

**Datums**: 2026-04-20
**Branch**: `design/pretrunas-v2`
**Handoff avots**: `atmina-handoff/atmina/project/src/contradiction-v2.jsx`
**Stila atsauce**: FT/Bloomberg dense — split-screen ar cieto centrālo robežu
**Paraugs (iepriekšējie redizaini)**: Pozīcijas V2 (`pzv1-*`), X tabs V1 (`xv1-*`)

---

## 1. Mērķis

Pārveidot `/pretrunas.html` no esošās `pretruna-card` (vienkārša V1-stila vertikāla "iepriekš/tagad" kaudze ar smaguma kreiso joslu) uz V2 redakcijas blīvo split-screen formu ar:

- pilna platuma partijas krāsas joslu virspusē (4px),
- strukturētu header band (avatar + persona+loma | smaguma badge + tēma | ΔT data cell),
- atsevišķu "Kopsavilkums" sekciju ar mono kicker,
- cieto vertikālo 1px gutter starp "Iepriekš"/"Pašlaik" panelēm + smaguma diska ikonu (⇄/↺/≈) gutter centrā,
- citātu kā blockquote (vai fallback "Citāts nav pieejams — parafrāze no avota"),
- footer band ar `ID NNN · Konstatēts {date} · Nozīmīgums {salience}` + share row,
- shareable anchor ID katrai pretrunai (`#pretruna-NNN`),
- page-level explainer par metodoloģiju (vienreiz, nevis per-card expander),
- Georgia (serif) + JetBrains Mono (mono) tipogrāfiju — **ne Newsreader** (atmests, sk. commit `53a347a`),
- mobilo collapse uz vertikālu kaudzi pie ≤ 760px.

Kvalitātes mērķis: pretrunu lapa kļūst par primāro shareable artefaktu — katra kartiņa ir reading-object pirmkārt, share-object otrkārt. Tonis atbilst Pozīcijām/X.

---

## 2. Scope (ko DARĀM)

- `templates/pretrunas.html.j2` — pilnīgs `pretruna-card` markup pārrakstījums uz `prv2-card`. Filtru bāra struktūra (severity buttons + 2 multi-select) paliek nemainīga; izmaiņas tikai filter button selektoros, ja `data-severity` paliek tāds pats. Page-level explainer bloks pievienots zem `pagehead-metrics`.
- `assets/style.css` — noņemt rindas 352–511 (`.pretruna-card.*`) un 1581–1612 (`.alt-explanation`); pievienot jaunu `prv2-*` bloku (~250 rindas) ar mobilo `@media (max-width: 760px)` collapse.
- `src/generate.py` — `_fetch_contradictions` (l.478) papildināts ar:
  - `tp.role` SELECT,
  - `c_old.quote AS old_quote`, `c_new.quote AS new_quote`,
  - `ct.salience` SELECT,
  - Python enrichment: `delta_days`, `severity_glyph`, `initials`, `old_source_domain`/`new_source_domain` (parsēti no URL ja iztrūkst).
- `assets_version` bump `src/generate.py` virspusē (cache-buster).

### Ārpus scope

- **Dedicated `/pretrunas/<id>.html` detail page** — atstājam C plānam, kad pretrunu skaits pārsniedz ~50. Pagaidām anchor (`#pretruna-NNN`) pilnīgi pietiek shareability.
- **Sharing buttons funkcionalitāte** — `prv2-share` ir vizuālā stub (𝕏, ⎘ pogas), reuse stila šablonu no `xv1-item-link`. Klikšķa logika (X intent URL, `navigator.clipboard.writeText`) — nākamais solis, ja vajadzīgs.
- **Severity krāsu palete** — turam mūsu esošās (#dc2626/#f97316/#eab308), nevis V2 (#e25b5b/#e8a34a/#90A4AE). Iemesls: vizuālā konsistence ar pārējo lapu (homepage hero, briefs, balsojumi izmanto šīs krāsas).
- **`@claim-extractor` quote izvilkšana** — pieņemam `claims.quote` lauku tādu, kāds ir DB. Ja null → fallback strip. Atsevišķa iniciatīva quote backfill nav daļa no šī darba.
- **Filtru JS pārrakstīšana** — esošais inline `<script>` (templates/pretrunas.html.j2:130-221) paliek funkcionāli identisks. Vienīgā izmaiņa: CSS selektors `'#contradictions-grid .pretruna-card'` → `'#contradictions-grid .prv2-card'` (l.135). `data-severity/data-party/data-person` atribūti tiek saglabāti uz jaunās `prv2-card`, tāpēc filter logic strādā bez izmaiņām. Pievieno jaunu hash deep-link handler (~30 rindas, sk. 10. sekciju).

---

## 3. Datu stāvoklis (tikai lasīts, informatīvs)

DB snapshot 2026-04-20 (`contradictions` tabula):

| Metrika | Vērtība |
|---|---|
| Kopā pretrunu | ~10 |
| Tiešas (`direct_contradiction`) | maza daļa, sk. `_fetch_contradictions` |
| Pozīcijas maiņas (`reversal`) | lielākā daļa |
| Nianses maiņas (`minor_shift`) | mazs skaits |
| `salience` NOT NULL | jāpārbauda; ja masveidā null → `{% if %}` slēpj segmentu |
| `claims.quote` aizpildīts | mainīgi; daļai pretrunu old/new abi quote, daļai tikai stance — fallback strip pārklāj abus gadījumus |
| `tp.role` aizpildīts | nepilnīgi; ja null → render tikai `party_short` bez ` · ` separatora |

Kartiņas joprojām ir reading-object orientētas (lielas, ~700-800px wide), nevis skenējams saraksts. Apjoma pieaugot ~50+ → atvērt C plānu (kompakts saraksts + detail skats).

---

## 4. Template struktūra (`pretrunas.html.j2`)

```
.pagehead-section (paliek)
├── .pagehead-header (paliek — kicker + h1 + 3 metrics)
├── .prv2-explainer (JAUNS, ~2 teikumu kursīvā Georgia)
├── .filter-bar #severity-filter (paliek — 4 pogas)
├── .filter-bar (paliek — 2 multi-select dropdown)
└── .grid-2 #contradictions-grid
    └── article.prv2-card.sev-{severity} id="pretruna-NNN"
        ├── .prv2-partybar (4px, partijas krāsa, full-width)
        ├── header.prv2-head (3-col grid: persona | meta-mid | meta-right)
        │   ├── .prv2-persona (avatar + name + role/party)
        │   ├── .prv2-meta-mid (severity badge + topic chip)
        │   └── .prv2-meta-right (.prv2-datacell ΔT)
        ├── section.prv2-summary (kicker + paragraph)
        ├── .prv2-split (1fr 1px 1fr)
        │   ├── .prv2-pane.prv2-pane-old
        │   │   ├── .prv2-kicker "Iepriekš"
        │   │   ├── .prv2-pane-meta (date · source domain)
        │   │   ├── .prv2-stance (paraphrase)
        │   │   └── blockquote.prv2-quote OR .prv2-quote-fallback
        │   ├── .prv2-gutter
        │   │   └── .prv2-gutter-disc (severity color border + glyph)
        │   └── .prv2-pane.prv2-pane-new (highlight tinted bg)
        │       ├── .prv2-kicker "Pašlaik" (severity krāsā)
        │       ├── .prv2-pane-meta
        │       ├── .prv2-stance
        │       ├── blockquote.prv2-quote OR fallback
        │       └── .prv2-vote (TIKAI ja vote_summary; mono kicker "LIKUMPROJEKTS")
        └── footer.prv2-foot
            ├── .prv2-foot-meta (anchor link "ID NNN" · Konstatēts · Nozīmīgums)
            └── .prv2-share (𝕏, ⎘ pogas — vizuālā stub)
```

### Page-level explainer

```jinja
<div class="prv2-explainer">
  <em>Pretrunas tiek konstatētas automātiski, salīdzinot publiskās pozīcijas laika gaitā.
  Iespējami arī alternatīvi skaidrojumi — pozīcija evoluējusi, dažādas auditorijas,
  formulējuma maiņa. Iepazīstieties ar avotiem un izvērtējiet paši.</em>
</div>
```

Stilistika: italic Georgia, 14px, `var(--text-muted)`, padding `0.75rem 0` virs filter-bar.

---

## 5. Vizuālie tokens

Atkārtoti lieto `:root` mainīgos (definēti `style.css:29-44`):

| Tokens | Vērtība | Avots |
|---|---|---|
| Surface | `var(--surface)` `#161a22` | jau :root |
| Surface band (header/footer) | `var(--surface2)` `#242838` | jau :root |
| Soft border | `#1f2432` | **jauns**, lokāli `--prv2-border-soft` |
| Hard border | `var(--border)` `#2d3148` | jau :root |
| Text / muted | `var(--text)` / `var(--text-muted)` | jau :root |
| Serif | `Georgia, 'Times New Roman', serif` | tāds pats kā `pretruna-card` un Pozīcijās |
| Mono | `'JetBrains Mono', ui-monospace, monospace` | tāds pats |
| Severity colors (`--prv2-sev`) | `#dc2626 / #f97316 / #eab308` | mūsu esošais (≠ V2 #e25b5b/#e8a34a/#90A4AE) |
| Severity tinted bg | `rgba(<sev>, 0.03)` uz `prv2-pane-new` | no V2 |
| Severity glyphs | `⇄` tieša / `↺` maiņa / `≈` niansē | no V2 SEV map |

Lokālo tokenu deklarācija top-level `.prv2-card` blokā:

```css
.prv2-card {
  --prv2-serif: Georgia, 'Times New Roman', serif;
  --prv2-mono: 'JetBrains Mono', ui-monospace, monospace;
  --prv2-border-soft: #1f2432;
  --prv2-sev: var(--yellow);  /* default = minor_shift */
}
.prv2-card.sev-direct_contradiction { --prv2-sev: #dc2626; }
.prv2-card.sev-reversal             { --prv2-sev: #f97316; }
.prv2-card.sev-minor_shift          { --prv2-sev: #eab308; }
```

---

## 6. HTML skelets (Jinja2, abridged)

```jinja
<article class="prv2-card sev-{{ c.severity }}" id="pretruna-{{ c.id }}"
         data-severity="{{ c.severity }}" data-party="{{ c.party }}"
         data-person="{{ c.politician_name }}">

  <div class="prv2-partybar" style="background:{{ c.party_color }}"></div>

  <header class="prv2-head">
    <div class="prv2-persona">
      <span class="prv2-avatar" style="--pc:{{ c.party_color }}">{{ c.initials }}</span>
      <div>
        <a class="prv2-name" href="politiki/{{ c.slug }}.html">{{ c.politician_name }}</a>
        <div class="prv2-role">
          {%- if c.role -%}{{ c.role }} · {% endif -%}
          {{ c.party_short }}
        </div>
      </div>
    </div>
    <div class="prv2-meta-mid">
      <span class="prv2-sevbadge">{{ c.severity_glyph }} {{ c.severity_lv }}</span>
      {% if c.topic %}<span class="prv2-topic">{{ c.topic }}</span>{% endif %}
    </div>
    {% if c.delta_days is not none %}
    <div class="prv2-meta-right">
      <div class="prv2-datacell">
        <span class="prv2-datacell-l">ΔT</span>
        <span class="prv2-datacell-v">{{ c.delta_days }}d</span>
      </div>
    </div>
    {% endif %}
  </header>

  {% if c.summary %}
  <section class="prv2-summary">
    <div class="prv2-kicker">Kopsavilkums</div>
    <p>{{ c.summary }}</p>
  </section>
  {% endif %}

  <div class="prv2-split">
    {# Pane: Iepriekš #}
    <div class="prv2-pane prv2-pane-old">
      <div class="prv2-kicker">Iepriekš</div>
      <div class="prv2-pane-meta">
        <time>{{ c.old_date }}</time>
        {% if c.old_source %}
        · <a href="{{ c.old_source }}" target="_blank" rel="noopener">{{ c.old_source_domain }} ↗</a>
        {% endif %}
      </div>
      <div class="prv2-stance">{{ c.old_stance }}</div>
      {% if c.old_quote %}
      <blockquote class="prv2-quote">{{ c.old_quote }}</blockquote>
      {% else %}
      <div class="prv2-quote-fallback">Citāts nav pieejams — parafrāze no avota</div>
      {% endif %}
    </div>

    {# Gutter ar smaguma disku #}
    <div class="prv2-gutter">
      <span class="prv2-gutter-disc" aria-hidden="true">{{ c.severity_glyph }}</span>
    </div>

    {# Pane: Pašlaik #}
    <div class="prv2-pane prv2-pane-new">
      <div class="prv2-kicker prv2-kicker-sev">Pašlaik</div>
      <div class="prv2-pane-meta">
        <time>{{ c.new_date }}</time>
        {% if c.new_source %}
        · <a href="{{ c.new_source }}" target="_blank" rel="noopener">{{ c.new_source_domain }} ↗</a>
        {% endif %}
      </div>
      <div class="prv2-stance">{{ c.new_stance }}</div>
      {% if c.new_quote %}
      <blockquote class="prv2-quote">{{ c.new_quote }}</blockquote>
      {% else %}
      <div class="prv2-quote-fallback">Citāts nav pieejams — parafrāze no avota</div>
      {% endif %}
      {% if c.vote_summary %}
      <div class="prv2-vote">
        <span class="prv2-vote-kicker">Likumprojekts</span>
        {{ c.vote_summary }}
      </div>
      {% endif %}
    </div>
  </div>

  <footer class="prv2-foot">
    <div class="prv2-foot-meta">
      <a href="#pretruna-{{ c.id }}" class="prv2-foot-id">ID {{ '%03d' % c.id }}</a>
      · Konstatēts {{ c.detected_at[:10] }}
      {% if c.salience %} · Nozīmīgums {{ '%.2f' % c.salience }}{% endif %}
    </div>
    <div class="prv2-share" aria-hidden="true">
      <button title="Dalīties uz X (drīzumā)">𝕏</button>
      <button title="Kopēt saiti (drīzumā)">⎘</button>
    </div>
  </footer>
</article>
```

---

## 7. Mobilais collapse (≤ 760px)

**Header band** — 3-col grid kollapsē uz 2 rindu stack:
- Rinda 1: `prv2-persona` (avatar + name + role)
- Rinda 2: `prv2-meta-mid` + `prv2-meta-right` flex-wrap kopā (badge + topic + ΔT cell)
- Padding `18px 28px` → `14px 18px`

**Split body** — `gridTemplateColumns: 1fr 1px 1fr` → `display: block`:
- Vecā panele virspusē, jaunā apakšā
- `prv2-gutter` no vertikālas 1px joslas → horizontāls 1px liner ar centrētu severity disku starp panelēm
- Tinted "now" background paliek; padding `22px 18px`

**Footer** — flex paliek; `prv2-foot-meta` text wrap allowed; ShareRow shrinks (mazākas pogas).

**Page-level explainer** — font-size 14px → 13px; padding pielāgots.

---

## 8. Edge cases

| # | Gadījums | Rīcība |
|---|---|---|
| 1 | `delta_days` null (viens datums null) | `{% if c.delta_days is not none %}` slēpj ΔT cell. Kartiņa joprojām derīga. |
| 2 | `delta_days = 0` (tā pati diena) | Render `"0d"` — derīgs gadījums, ne edge. |
| 3 | `quote` null | `prv2-quote-fallback` strip ar tekstu "Citāts nav pieejams — parafrāze no avota". |
| 4 | `salience` null | `{% if c.salience %}` izlaiž segmentu no footer. |
| 5 | `summary` tukšs/null | `{% if c.summary %}` izlaiž visu `prv2-summary` sekciju. |
| 6 | `topic` tukšs | `{% if c.topic %}` izlaiž `prv2-topic` chip; `prv2-meta-mid` paliek tikai severity badge. |
| 7 | `role` (`tp.role`) null | Render tikai `party_short` bez ` · ` separatora. |
| 8 | `vote_summary` (Saeima vote new claim) | Render `prv2-vote` bloks zem stance/quote `prv2-pane-new` apakšā ar mono kicker "Likumprojekts". |
| 9 | `initials` aprēķina kļūme | Default `"?"`. |
| 10 | Hash deep-link bez match | `scrollIntoView` silent no-op; nav toast/error. |
| 11 | Hash + aktīvs filtrs konflikts | JS automātiski clear visus filtrus pirms scroll, lai shared link "vienmēr strādā". |
| 12 | Highlight pulse | 2s `box-shadow` glow ar `transition`. `prefers-reduced-motion: reduce` → instant outline tikai. |
| 13 | `party_color` null | Partijas josla render kā `var(--prv2-border-soft)`; avatara kreisā mala arī. |
| 14 | `severity` ārpus 3 known vērtībām | CSS `--prv2-sev` paliek default `var(--yellow)`; `severity_glyph` enrichment Python pusē defaults uz `"·"`. |

---

## 9. `_fetch_contradictions` Python papildinājumi

```python
# src/generate.py:478
def _fetch_contradictions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience,                            -- + salience
            tp.name AS politician_name, tp.party, tp.role,          -- + role
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,  -- + quote
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote   -- + quote
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        ORDER BY ct.detected_at DESC
    """).fetchall()

    SEVERITY_GLYPHS = {
        "direct_contradiction": "⇄",
        "reversal": "↺",
        "minor_shift": "≈",
    }

    results = []
    for r in rows:
        d = dict(r)
        # ... existing enrichment (severity_lv, slug, party_short, party_color,
        #     date trimming, old_link/new_link, vote_summary, vote_id) ...

        # JAUNI:
        d["severity_glyph"] = SEVERITY_GLYPHS.get(d["severity"], "·")
        d["initials"] = _initials_from_name(d["politician_name"])
        d["old_source_domain"] = _domain_from_url(d.get("old_source"))
        d["new_source_domain"] = _domain_from_url(d.get("new_source"))
        d["delta_days"] = _delta_days(d.get("old_date"), d.get("new_date"))

        results.append(d)
    return results


def _initials_from_name(name: str | None) -> str:
    if not name:
        return "?"
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return "".join(p[0].upper() for p in parts[:2])


def _delta_days(old_date: str | None, new_date: str | None) -> int | None:
    if not old_date or not new_date:
        return None
    try:
        from datetime import date
        d_old = date.fromisoformat(old_date[:10])
        d_new = date.fromisoformat(new_date[:10])
        return abs((d_new - d_old).days)
    except (ValueError, TypeError):
        return None


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return None
```

> **Piezīme:** ja `_domain_from_url` jau eksistē kā util citur (`src/utils.py` vai pat `generate.py`) — reuse, nedublē. Jāpārbauda implementācijā.

---

## 10. Hash deep-link JS (~30 rindas, inline `pretrunas.html.j2:130`)

```js
// Hash deep-link: scroll + 2s highlight pulse.
function _prv2HashJump() {
  const hash = location.hash;
  if (!hash || !hash.startsWith('#pretruna-')) return;
  const card = document.querySelector(hash);
  if (!card) return;

  // Clear filtrus, lai shared link vienmēr strādā
  document.querySelectorAll('#severity-filter .filter-btn').forEach(b => b.classList.remove('active'));
  const allBtn = document.querySelector('#severity-filter [data-filter="all"]');
  if (allBtn) allBtn.classList.add('active');
  selectedParties.clear();
  selectedPersons.clear();
  document.querySelectorAll('.multi-select-option.selected').forEach(o => o.classList.remove('selected'));
  activeSeverity = 'all';
  applyFilters();

  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  card.classList.add('prv2-card-pulse');
  setTimeout(() => card.classList.remove('prv2-card-pulse'), 2000);
}
window.addEventListener('hashchange', _prv2HashJump);
window.addEventListener('load', _prv2HashJump);
```

CSS `prv2-card-pulse` — `box-shadow: 0 0 0 3px var(--prv2-sev)` ar `transition: box-shadow 0.4s ease`. Attiecīgi `@media (prefers-reduced-motion: reduce)` — tikai outline bez transition.

---

## 11. Faili — pilns saraksts

| Fails | Izmaiņas | Aptuvenās rindas |
|---|---|---|
| `templates/pretrunas.html.j2` | Pārrakstīt `pretruna-card` markup → `prv2-card`. Atjaunot inline JS selektoru `.pretruna-card` → `.prv2-card`. Pievienot `prv2-explainer`. Pievienot hash deep-link JS. | -50 / +110 |
| `assets/style.css` | Noņemt `.pretruna-card.*` (354–511) un `.alt-explanation` (1581–1612). Pievienot `prv2-*` bloku ar mobilo. | -180 / +260 |
| `src/generate.py` | `_fetch_contradictions` SELECT papildinājums + Python enrichment (`severity_glyph`, `initials`, `delta_days`, `*_source_domain`). 3 jauni helper funkcijas (vai reuse esošos). Bump `assets_version`. | +60 |
| `tests/test_generate.py` (vai jauns) | Unit tests jaunajiem helperiem (`_initials_from_name`, `_delta_days`, `_domain_from_url`). | +40 |

**Kopā:** 4 faili, ~340 jaunās rindas, ~230 noņemtas.

---

## 12. Verifikācija (pirms PR)

- `python -m pytest tests/ -v` — viss zaļš
- `python -c "from src.generate import generate_public_site; generate_public_site()"` — bez kļūdām
- `python serve.py` → atvērt `http://127.0.0.1:8080/pretrunas.html`:
  - vizuālā parbaude: 5 slāņi katrā kartiņā, partijas krāsas joslas redzamas, gutter disc centrēts ar pareizu glyph
  - mobile (DevTools 360px): split kollapsē, header pārstrukturējas
  - hash deep-link: `#pretruna-1` scrollē + pulse, filtri attīrās
  - filtri (severity + party + person multi-select) joprojām strādā
  - explainer redzams, alt-explanation expander vairs nav
  - Saeima vote pretrunas (kur `vote_summary` ne null) — render `prv2-vote` bloks
- `npx eslint .` (ja konfigurēts) un `mypy` / `pyright` (ja konfigurēts) — pārbaudīt; ja nē, piezīmēt explicit.

---

## 13. Atvērti jautājumi (galvenokārt nākotnei)

1. **Sharing buttons funkcionalitāte** — vai pievienot X intent URL un clipboard copy klikšķim šajā plānā vai atstāt nākamajai iterācijai? *Šobrīd: vizuālā stub.*
2. **`@claim-extractor` quote backfill** — vai piesaistīt agentu, lai aizpildītu trūkstošos `claims.quote` laukus pretrunām? *Šobrīd: fallback strip.*
3. **C plāns (saraksts + detail page)** — kad pretrunu būs ~50+, atvērt jaunu spec dedicated `/pretrunas/<id>.html` lapām. *Šobrīd: anchor + scroll.*
4. **Mobilās gutter disc placement** — split kollapsē uz vertikālu, vai disc paliek horizontāli starp panelēm vai starp panelēm netiek render? *Šobrīd: paliek starp, horizontālā 1px liner.*
