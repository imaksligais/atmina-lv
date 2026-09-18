# Dienas pārskata redizains — spec

**Datums:** 2026-04-19
**Statuss:** Apstiprināts dizains (gaida implementācijas plānu)
**Apjoms:** A-scope — mērķtiecīgi labojumi (~1 sesija, ~5 faili)

## Konteksts

Dienas pārskats (`blog/YYYY-MM-DD.html`, ģenerēts no `src/briefs.py` skeleta un brief-writer aģenta naratīva) pašreizējā formātā cieš no trim problēmām:

1. **`## Galvenais` — blīva proza.** Pēc skaitļu bulleta seko 4-teikumu paragrāfs ar visu dienas naratīvu. Grūti skenēt, grūti kopīgot.
2. **"Garā desā" metadata sadaļās.** `## Koalīcija vs Opozīcija` ir viens milzīgs paragrāfs + 3 bullet rindas ar politiķu sarakstiem, kas atkārto informāciju no Aktīvākie tabulas.
3. **Tehnisko DB lauku noplūde publiskā tekstā.** 2026-04-18 pārskatā Spriedžu tabula satur `Pretruna #24 (minor_shift): ...` — brief-writer manuāli pārstrukturēja skeleta tabulu un iebāza `contradictions` rindu ar raw DB ID un severity enum. Paralēli konteksta boksos parādās `Pretruna #17 (6↔123)` atsauces sintakse.

Papildus — 12 rindu Aktīvākie tabula + 10+ tēmu sadaļas rada blīvumu bez vizuāla ritma; statistika (dokumenti, pozīcijas) ir labāk pasniedzama kā footer metadata, nevis kā lead.

## Mērķi

- Padarīt `## Galvenais` skenējamu (bullet-points ar bold lead).
- Padarīt `## Koalīcija vs Opozīcija` kompaktu (tabula, ne prozas siena).
- Novērst visu tehnisko DB lauku (`#NN`, `minor_shift`, `6↔123`) parādīšanos publiskā tekstā.
- Nodrošināt, ka Spriedzes/Pretrunas sadaļas pielāgojas dienas datiem (dažas dienas ir uzbrukumi, citas — pretrunas, retāk atbalsts).
- Pārcelt dokumentu/pozīciju skaitu + atjaunošanas laiku uz footer (kā metadata, ne kā lead).
- Samazināt Aktīvākie tabulu no 12 uz 7 rindām.

## Ne-mērķi

- Nepārstrādā skelets-to-HTML pipeline (markdown → Jinja paliek).
- Neaiztiek pēc-tēmas 1-2 teikumu sintēzes (`## Galvenās tēmas` apakšsadaļu stāstījumu) — apzināti saglabāti.
- Neaiztiek konteksta boksus (`<div class="context-box">`).
- Neaiztiek Vizuālā brief bloku (featured image pipeline).
- Nemaina Telegram brief (`generate_telegram_brief` pieies jaunajam formātam, ja sentence-split regex pieņem bullet-list; jāpārbauda, bet ne šī spec daļa).

## Izmaiņas pa sadaļām

### 1. `## Galvenais` — no prozas uz naratīva bullets

**Pirms:**
```markdown
## Galvenais

- **533 dokumenti** (63 web + 152 X + 318 mentions), **28 jaunas pozīcijas** + **0 Saeimas balsojumi**, **1 pretruna**

Sestdienas politiskā darba kārtība … paplašinājās no rīta redzētā šaurā koalīcijas-MMN loka uz plašāku spektru. Aizsardzības un ārpolitikas līnijā Braže un Sprūds konsolidēja koalīcijas pozīciju … [4 teikumi]
```

**Pēc:**
```markdown
## Galvenais

<!-- DIENAS STATS (aģenta iekšējai orientācijai, nav renderēts publikai):
533 dokumenti (63 web + 152 X + 318 mentions) · 28 pozīcijas · 0 Saeimas balsojumi · 1 pretruna -->

- **Aizsardzība:** Braže (JV) un Sprūds (PRO) konsolidē 5% IKP līniju; Sprūds paplašina uz Mednieku savienības iesaisti.
- **NA trīs paralēli naratīvi:** Pūpols atver airBaltic–Lufthansa, reemigrāciju pret trešvalstu darbaspēku un Ždanokas–Hezbollah saiti.
- **Opozīcijas vienīgā balss:** Kulbergs (AS) kritizē Saeimu kā "balsošanas mašīnu".
- **Ārpus Saeimas:** MMN paralēlās līnijas — Hermanis/Baško par vēlēšanu sistēmu, Krusts par Hormuzas šaurumu.
```

**Skelets (`briefs.py`):**
- Noņem esošo stats bullet zem `## Galvenais` (119-122 līnija).
- Pievieno HTML komentāru ar stats kā aģenta iekšējo piezīmi. Komentārs **netiek** strip'ots pirms rendering — markdown-renderis to atstāj neizmainītu HTML komentāra formā (browseris to neparāda, DOM-ā ir).
- `## Galvenais` sadaļas virsraksts paliek; zem tā aģents raksta naratīvus bullet-punktus.

**Aģenta instrukcija (`brief-writer.md`):**
- `## Galvenais` prasība maina no "3-5 sentence paragraph" uz "3-5 bullet-punktus, katrs ar **bold lead** (tēma vai naratīva līnija) + 1 teikums paskaidrojums".
- `<!-- DIENAS STATS -->` komentārs ir **iekšējs kontekstuāls signāls**, lai aģents saprastu dienas apjomu, stāstījumu kalibrētu. Aģents **neraksta skaitļus redzamā saturā** — skaitļus renderē template footer.

### 2. `## Aktīvākie politiķi` — top 7

**Skelets:** `LIMIT 12` → `LIMIT 7` `briefs.py:62`.

Vienīgā izmaiņa — SQL. Tabulas formāts paliek (`| Politiķis | Partija | Pozīcijas | Galvenās tēmas |`).

### 3. `## Koalīcija vs Opozīcija` — no 3 paragrāfiem uz tabulu + sintēze

**Pirms:**
```markdown
## Koalīcija vs Opozīcija

Pēc pēcpusdienas refresh rutīnas koalīcijas un opozīcijas balanss sestdienā kļūst daudz nianšātāks … [garš paragrāfs]

**Koalīcija (20 pozīcijas):** Baiba Braže (Jaunā Vienotība) — Aizsardzība; Ansis Pūpols (Nacionālā apvienība) — Imigrācija; …

**Opozīcija (1 pozīcija):** Andris Kulbergs (Apvienotais saraksts) — Valsts pārvalde

**Ārpus Saeimas (5 pozīcijas):** Alvis Hermanis (MMN) — Vēlēšanas; …

**Neitrāli/žurnālisti (2 pozīcijas):** Filips Rajevskis — Budžets; Lato Lapsa — Aizsardzība
```

**Pēc:**
```markdown
## Koalīcija vs Opozīcija

| Bloks | Pozīcijas | Partijas | Galvenie runātāji | Dominējošās tēmas |
|-------|-----------|----------|-------------------|-------------------|
| Koalīcija | 20 | JV, NA, PRO | Braže (6), Pūpols (5), Sprūds (3) | Aizsardzība, Ārpolitika, Imigrācija |
| Opozīcija | 1 | AS | Kulbergs (1) | Valsts pārvalde |
| Ārpus Saeimas | 5 | MMN | Hermanis (2), Krusts (2), Baško (1) | Vēlēšanas, Enerģētika |
| Neitrāli | 2 | — | Rajevskis, Lapsa | Nodokļi, Aizsardzība |

*ZZS šodien publiski klusē; NA un PRO dala vienu tēmu bez pretrunām; Kulbergs ir vienīgā Saeimas opozīcijas balss šajā dienā.*
```

**Skelets (`briefs.py`):**
- Maina 238-257 līnijas: trīs paragrāfu `**Bold:** name (party) — topics; …` rindu vietā ģenerē 4-rindu tabulu ar kolonnām Bloks/Pozīcijas/Partijas/Galvenie runātāji/Dominējošās tēmas.
- "Galvenie runātāji" = top 3 politiķi pēc pozīciju skaita, formatēti kā `Vārds (N)`.
- "Dominējošās tēmas" = top 3 tēmas pēc pozīciju skaita bloka iekšienē.
- "Partijas" = partiju īsie nosaukumi (JV, NA, PRO, ZZS utt.), izmantojot `_PARTY_SHORT` mapi.
- "Neitrāli" rinda pievienojas, ja pastāv politiķi ar `relationship_type IN ('journalist', 'influencer', 'neutral')` un pozīcijām šajā dienā.
- Aiz tabulas tukša rinda — aģents zem tabulas pievieno 1-2 teikumu sintēzi (konsekventi ar `## Galvenās tēmas` apakšsadaļu stilu).

**Aģenta instrukcija:** `## Koalīcija vs Opozīcija` — zem skeleta tabulas pievieno 1-2 teikumu sintēzi (kur koalīcija iekšēji dalās, kur opozīcija atrod kopīgu pamatu, kādas partijas klusē). **Ne** prozas siena, **ne** pārrakstīšana.

### 4. Spriedzes un Pretrunas — adaptīvas sadaļas

**Skelets (`briefs.py`):**

Pašreizējā `## Spriedzes` sadaļa (260-286) paliek, bet:

- **`## Spriedzes`** rāda tikai, ja `political_tensions` > 0. Esošā 6-kol tabula (`Tips | Avots | Mērķis | Tēma | Apraksts | Saite`). "Tips" kolonnā — `tension_type` vērtības jau ir latviski (`uzbrukums`, `spriedze`, `atbalsts`).
- **`## Pretrunas`** — jauna sadaļa, rāda tikai, ja `contradictions` > 0.

**Pretrunas tabula:**
```markdown
## Pretrunas

| Politiķis | Partija | Tēma | Veids | Apraksts | Avoti |
|-----------|---------|------|-------|----------|-------|
| Viktors Valainis | ZZS | airBaltic | neliela novirze | 6.apr. kritizē "valsts finansējumā balstītu" stratēģiju kā nepieļaujamu; 13.apr. piedāvā ZZS pārņemt pārvaldību "pēc Latvenergo modeļa" (100% valsts kapitāls). Iespējams skaidrojums — nošķir ārkārtas aizdevumu no stabila valsts akcionāra. | [06.04](url1) / [13.04](url2) |
```

**Kolonnu definīcijas:**
- **Politiķis, Partija** — `JOIN tracked_politicians p ON c.opponent_id = p.id`.
- **Tēma** — `contradictions.topic` (jau normalizēta).
- **Veids** — `contradictions.severity` ar tulkošanas mapi:
  - `minor_shift` → `neliela novirze`
  - `direct_contradiction` → `tieša pretruna`
  - `reversal` → `reversija`
  - Nezināmas vērtības → `pretruna` (fallback).
- **Apraksts** — `contradictions.summary`, pirmais paragrāfs (līdz pirmajam `\n\n`), max 350 chars ar elipsi, ja pārsniedz. **Bez** `#NN` prefiksa, **bez** severity enum tekstā.
- **Avoti** — lasa `claim_old.source_url` un `claim_new.source_url` no `claims` pa `claim_old_id` / `claim_new_id`. Datumi formatā `DD.MM` no `claims.stated_at`. Ja viens trūkst — rāda tikai vienu saiti; ja abi trūkst — `—`.

**Secība:** Spriedzes virs Pretrunas, ja abas ir. Ja tikai vienas — tikai tā sadaļa.

**Aģenta instrukcija (`brief-writer.md`):**
- **AIZLIEGTS** pārstrukturēt `## Spriedzes` vai `## Pretrunas` tabulu kolonnas. Ja aģents grib pievienot kontekstu — raksta **zem** tabulas kā 1-2 teikumu piezīmi, **ne** jaunu tabulu.
- **AIZLIEGTS** rakstīt `#NN`, `Pretruna #NN`, vai raw DB enum vērtības (`minor_shift`, `direct_contradiction`, `reversal`, `6↔123`) brief tekstā, konteksta boksos vai tabulās. Šie ir iekšēji DB lauki, nevis publikas terminoloģija.
- Ja kontekstā nepieciešams atsaukties uz iepriekšējo pretrunu — izmanto aprakstošu atsauci ("Valaiņa iepriekšējā airBaltic pretruna"), **ne** `Pretruna #17`.

### 5. Metadata footer — template-level

**Plūsma:**
- Skelets **neraksta** stats redzamā saturā (paliek tikai HTML komentārs aģentam).
- `src/generate.py:_fetch_blog_posts()` pēc katras brief ieraksta veic DB count queries (dokumenti pa platformām, pozīcijas, pretrunas) un pievieno `post["footer"]` ar formatētiem datiem.
- `created_at` formatē kā `"18.04.2026 23:34"` → `post["updated_at_display"]`.
- `templates/blog-post.html.j2` renderē footer bloku pirms prev/next navigācijas.

**HTML forma (render-time):**
```html
<hr class="brief-footer-sep">
<p class="brief-footer">
  <strong>Pamatā:</strong> 533 dokumenti (63 web · 152 X · 318 mentions) · 28 jaunas pozīcijas · 1 pretruna<br>
  <strong>Atjaunots:</strong> 18.04.2026 23:34 (Latvijas laiks)
</p>
```

**CSS (`assets/style.css`):**
```css
.brief-footer-sep {
  margin: 2rem 0 1rem;
  border: none;
  border-top: 1px solid var(--border);
}
.brief-footer {
  color: var(--text-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}
```

**Stats DB queries (render-time `_fetch_blog_posts`):**

Autoritatīvās `documents.platform` vērtības (DB audits): `'web'`, `'twitter'`, `'x_mention'`, `'saeima'`, `'facebook'`, `'stub'`, `'irrelevant'`. Footer rāda avotu plūsmas pa trim galvenajām kategorijām; Saeimas bulk-imports un marginālās platformas izslēgtas no `doc_count`.

```python
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
```

`post["footer"]` = `{"doc_count": 533, "web": 63, "twitter": 152, "mentions": 318, "positions": 28, "votes": 0, "contradictions": 1, "updated": "18.04.2026 23:34"}`.

**Saeimas balsojumu skaits** — no `saeima_votes.vote_date` (unikāli lēmumi, piemēram 39 tajā dienā), **nevis** no `claims.claim_type='saeima_vote'` COUNT (kas ir politiķu × balsojumu cell skaits, piemēram 3418). Autoritatīvais avots — `saeima_votes` tabula.

**Footer HTML forma — conditional saeimas segments:**
- Ja `votes > 0`: `Pamatā: 533 dokumenti (63 web · 152 X · 318 mentions) · 28 jaunas pozīcijas · 39 Saeimas balsojumi · 1 pretruna`
- Ja `votes == 0`: `Pamatā: 533 dokumenti (63 web · 152 X · 318 mentions) · 28 jaunas pozīcijas · 1 pretruna`

`twitter` rāda kā "X" (lietotāja terminoloģija, konsekventi ar iepriekšējo stats bulletu).

**Pluralizācija:** `1 balsojums` / `2-N balsojumi` / `1 pozīcija` / `N pozīcijas` / `1 pretruna` / `N pretrunas`. Jinja helper `lv_plural(n, singular, plural)` vai tieši template conditional — pielāgo implementācijā.

## Datu plūsma / atbildības

| Sadaļa / lauks | Kurš raksta | Kad |
|----------------|-------------|-----|
| `# Dienas analīze — YYYY-MM-DD` | Skelets | `generate_daily_brief()` |
| `<!-- DIENAS STATS -->` komentārs | Skelets | `generate_daily_brief()` |
| `## Galvenais` bullets | Aģents (brief-writer) | Naratīva rakstīšana |
| `## Aktīvākie politiķi` tabula (top 7) | Skelets | SQL query |
| `## Galvenās tēmas` sub-struktūra | Skelets | SQL query |
| Konteksta boksi (`<div class="context-box">`) | Skelets no DB vai aģents | Mixed |
| Tēmu tabulas | Skelets | SQL query |
| Per-tēmas 1-2 teikumu sintēze | Aģents | Naratīva rakstīšana |
| `## Koalīcija vs Opozīcija` tabula | Skelets | SQL query |
| K/O sintēzes teikumi (zem tabulas) | Aģents | Naratīva rakstīšana |
| `## Spriedzes` tabula | Skelets | SQL query + `tension_type` |
| `## Pretrunas` tabula | Skelets | SQL query + `severity` mapping |
| `## Vizuālais brief` bloks | Aģents | Obligāts, pēc satura |
| **Footer (stats + laiks)** | **`generate.py` template** | **Render-time** |

## Testēšanas kritēriji

1. **Struktūras validators (`tools.py:_validate_brief_structure`) pieņem jauno formātu** — trīs obligātās sadaļas (Aktīvākie politiķi, Galvenās tēmas, Koalīcija vs Opozīcija) + `| Politiķis |` tabula + 4000+ chars. Nemainām validatoru, bet pārbaudām, ka jaunais skelets + tipisks aģenta naratīvs joprojām to iztur.
2. **Regression 2026-04-18 pārskatā** — pēc regenerate'a `## Spriedzes` vai `## Pretrunas` sadaļā **nav** `#24`, `minor_shift`, `Pretruna #` vai `#17`.
3. **Galvenais skenējamība** — `## Galvenais` sadaļa satur tikai bullet-punktus (`-` sākas katra rinda) + HTML komentāru; nav prozas paragrāfu.
4. **Koalīcija vs Opozīcija** — satur markdown tabulu ar vismaz 2 rindām (Koalīcija + vismaz 1 cits bloks); aiz tabulas 1-3 teikumi sintēzes.
5. **Footer render** — katrs `blog/YYYY-MM-DD.html` satur `<p class="brief-footer">` ar `Pamatā:` + `Atjaunots:` laukiem. Saeimas balsojumu segments parādās **tikai** dienās ar `saeima_votes.vote_date = ?` > 0 (piem. 2026-04-16 ar 39 balsojumiem); tukšās dienās (2026-04-18) segments izlaists.
6. **Aktīvākie politiķi** — tabulā ne vairāk par 7 rindām.
7. **HTML komentārs neredzams** — `<!-- DIENAS STATS -->` ir DOM-ā, bet browseris to neparāda. Manuāls pārbaudījums.
8. **Empty-state** — diena bez tensions + bez contradictions — ne `## Spriedzes`, ne `## Pretrunas` sadaļas netiek renderētas (ne tukša tabula, ne "Nav datu" tekstā).

## Faili un aptuvenais apjoms

| Fails | Izmaiņas |
|-------|----------|
| `src/briefs.py` | ~80 līniju diff: noņem stats bullet, pievieno komentāru; Koalīcija vs Opozīcija kā tabula; jauna `## Pretrunas` sadaļa ar severity mapping; `LIMIT 12` → `LIMIT 7` |
| `.claude/agents/brief-writer.md` | ~20 līniju diff: Galvenais bullet instrukcija; tabulas aizliegums; `#NN`/enum aizliegums |
| `src/generate.py` | ~25 līniju diff: `_fetch_blog_posts()` pievieno stats query + `updated_at_display` |
| `templates/blog-post.html.j2` | ~6 līniju diff: footer bloks pirms prev/next nav |
| `assets/style.css` | ~10 līniju diff: `.brief-footer`, `.brief-footer-sep` klases |
| `src/tools.py` | **Nav izmaiņu** (validators pieņem jauno formātu) |

## Atklāti jautājumi / riski

1. **Telegram brief regex** — atsevišķa sesija. `generate_telegram_brief` 463-466 līnija split'o `## Galvenais` paragrāfu pa teikumiem. Jauns bullet-list formāts iznāks kā `- **Lead:** text` rindas; esošais regex tos neatpazīs. Pielāgo pēc tam, kad galvenais dizains ir deployed.
2. **HTML komentāra drošība — atrisināts.** Pārbaudīts `generate.py:2510-2511`: blog post renders izmanto tieši `md_renderer.convert(content)` bez `_sanitize_html` wrap'a. `markdown` library ar `tables` + `fenced_code` extensions atstāj HTML komentārus neizmainītus. Komentārs būs DOM-ā, browseris neparādīs — kā plānots.
3. **`platform` vērtības — atrisināts.** DB audits parādīja, ka autoritatīvās vērtības ir `'web'` / `'twitter'` / `'x_mention'` / `'saeima'` (nevis `'x'` / `'mentions'`). Spec stats query atjaunota; Saeimas bulk-imports apzināti izslēgti no `doc_count`, jo tie ir balsošanas protokoli, ne jaunu avotu plūsma.

## Nākamais solis

Apstiprinājums → `writing-plans` skill ģenerēs faila-līmeņa implementācijas plānu ar konkrētām rindām un secību.
