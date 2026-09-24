# Weekly brief redesign — design spec

_Datums: 2026-06-01 · Statuss: apstiprināts dizains, gaida spec review_

## 1. Konteksts un mērķis

Nedēļas pārskats (`context_notes.note_type='weekly_brief'`) šobrīd ir 7-dienu daily klons: tas pats markdown skelets, tas pats `blog-post.html.j2` template, tikai cita slug prefiksa (`nedela-`) un datumu diapazona galvene. Mērķis — padarīt nedēļas pārskatu par patiesi atšķirīgu produktu: **viegli lasāmu, mobile-first, ar avotiem, gramatiski/stilistiski precīzu**, ar **sintēzi pār 7 dienām** (ko daily nevar), atšķirīgu **featured image stilu** un vienu **precīzu datu vizualizāciju** brief vidū.

Apstiprinātie lēmumi:
- **Akcents:** ink-navy deterministiskajā template chrome (badge, malas, grafika joslas) + featured-image rāmī; per-tēmas metaforas saglabājas attēlā.
- **Grafiks:** "Kas kustējās" — movers leaderboard (absolūti skaitļi + Δ pret iepriekšējo nedēļu) ar plānu koalīcija-vs-opozīcija joslu apakšā.
- **Aģents:** atsevišķs `weekly-brief-writer`, koplietotos žurnālistikas noteikumus izvelkot atsevišķā dokumentā.
- **Fāzes:** abas.

## 2. Atslēgas atklājums (arhitektūras pamats)

`generate_weekly_brief()` (`src/briefs.py:371`) **jau eksistē, bet ir orphaned** (nav izsaucēju). Tas jau rēķina deterministiskos datus no DB: `doc/position/vote/contradiction` skaitus (confirmed-only), top-12 aktīvāko leaderboard, top-7 tēmu sadalījumu. Tas izvada plānu daily-klona skeletu.

**Princips:** mēs **paplašinām esošo skeletu**, nevis būvējam jaunu pipeline — precīzi atspoguļojot daily arhitektūru (`generate_daily_brief()` skelets → aģents bagātina prozā). Tas garantē precīzus skaitļus (nāk no skeleta, ne no AI), uztur arhitektūras simetriju un samazina jauna koda apjomu.

## 3. Non-goals

- Daily pārskata formāts/stils — **netiek aiztikts**.
- Sentiment, jaunas DB tabulas/kolonnas — nav.
- `brief_images` shēmas izmaiņas — nav (sk. bug #1 risinājumu).
- Vēsturisko nedēļas pārskatu re-render uz jauno formātu — ārpus tvēruma (jaunie pārskati lieto jauno; vecie paliek).

## 4. Jaunā nedēļas markdown struktūra (sekciju kontrakts)

Secībā, kā `weekly-brief-writer` to izvada (skelets sniedz `<!-- … -->` markerus + deterministiskos datus; aģents raksta prozu):

| Sekcija | Saturs | Avots |
|---|---|---|
| `# Nedēļas analīze — START līdz END` | H1 (render to strip, lieto kā title) | skelets |
| `## Nedēļas stāsts` | 2–3 īsas prozas rindkopas — nedēļas arka/dominējošais pavediens | **aģents** (proza) |
| `## Nedēļā skaitļos` | Stat-strip marker → template kartītes (pozīcijas, balsojumi, jaunas pretrunas, top tēma, aktīvākā partija) | skelets (`<!-- WEEKLY_STATS: … -->`) |
| `## Kas kustējās` | Movers grafika `![](…)` + 1 teikuma paraksts | skelets (grafiks) + aģents (paraksts) |
| `## Nedēļas galvenās tēmas` | 3–4 tēmas; katra = īsa sintēze + 2–3 avot-linkotas pozīcijas kā kompakts saraksts (NE platas tabulas) | aģents (sintēze) + skelets (pozīciju kandidāti ar avotiem) |
| `## Pretrunas` | Tikai confirmed, aprakstoši (bez DB ID/enum) | skelets + aģents |
| `## Skats uz priekšu` | 1–2 teikumi (neobligāti) | aģents |
| `## Vizuālais brief` | Tēma/Galvenā tēze/Skaitlis/Metaforas hint (baro featured image) | aģents |

Mobile: bez per-tēmas context-box (mazāks scroll); pozīcijas kā saraksts, ne platas tabulas.

## 5. Fāze 1 — satura dzinējs

### 5.1 `generate_weekly_brief()` paplašinājums (`src/briefs.py`)
- **Δ aprēķins:** salīdzina šīs nedēļas position-claim skaitu pa politiķim/tēmai pret iepriekšējo 7-dienu logu. Edge-case kontrakts:
  - Nav baseline (jauns politiķis vai pirmā nedēļa) → `delta = "jauns"`, nekad nedalīt ar 0.
  - Δ rāda **absolūtus skaitļus** kā galveno; bultiņa ↑/↓/— kā anotācija. **Procentus nelietot** (maldina pie maza N).
- **Stat-strip marker:** emit `<!-- WEEKLY_STATS: positions=… votes=… contradictions=… top_topic=… top_party=… -->` zem `## Nedēļā skaitļos`. Template to parsē kartītēs (render-time, deterministiski).
- **Tēmu scaffold:** zem `## Nedēļas galvenās tēmas` katrai top tēmai emit 2–3 augstākās salience pozīcijas ar `name|party|stance|source_url` (aģents pārvērš sintēzē + saglabā avotus).
- **Grafika hook:** izsauc `weekly_chart.make_movers_svg(...)`, ieraksta failu, emit `![Kas kustējās](…)` zem `## Kas kustējās`.

### 5.2 `weekly-brief-writer` aģents (`.claude/agents/weekly-brief-writer.md`)
- Single-responsibility: tikai nedēļas struktūra. **Nesatur** daily verbatim-tabulu noteikumus (Spriedzes, Koalīcija vs Opozīcija 5-kolonnu, DIENAS STATS) — tie ir daily-specifiski un to noplūde uz weekly ir reāls failure mode.
- SAGLABĀ/PAPILDINI kontrakts pielāgots jaunajai struktūrai (saglabā skeleta markerus, grafika `![]()`, avotu linkus; raksta prozu).

### 5.3 Koplietoto noteikumu izvilkšana (`wiki/operations/agenti/brief-shared-rules.md`)
- Izvelk no `brief-writer.md`: LV-style lint (`lint_lv_style`), per-speaker atribūcija (`feedback_synthesis_attribution`), source-URL disciplīna, NO-DB-ID/enum, `store_context_note`-only mutācija, diakritika.
- Gan `brief-writer.md`, gan `weekly-brief-writer.md` atsaucas uz šo dokumentu. Daily aģenta struktūras noteikumi paliek savā failā.

### 5.4 Validācija (`src/tools.py::_validate_brief_structure`)
- `weekly_brief` zars: prasa `## Nedēļas stāsts` un `## Nedēļas galvenās tēmas` (vietā `## Aktīvākie politiķi`), `len ≥ 3000`, H1, `## Vizuālais brief` bloks. **Jāships kopā ar 5.1/5.2**, citādi store noraida.

## 6. Fāze 2 — vizuālais slānis

### 6.1 SVG movers grafiks (`src/graphics/weekly_chart.py`)
- `make_movers_svg(db, week_start, week_end) -> (svg_bytes, out_path)`. Roku-rakstīts SVG (≈40 rindas, horizontālas joslas, **bez jaunas heavy atkarības**). Editorial palete (krēms fons, ink-navy joslas). Top ~6 politiķi pēc position-claims + Δ anotācija; plāna koalīcija-vs-opozīcija josla apakšā (`src.coalition.get_coalition_map`).
- **Bug #1 risinājums:** grafiks **netiek glabāts `brief_images`** (nav `kind` kolonnas; `get_approved_image` to sajauktu ar featured image). Tas ir deterministiski dati, ne radošs darbs → izlaiž approval loop. Fails → `output/images/briefs/<date>-nedelas-movers.svg` (+ vajadzības gadījumā PNG).
- **Bug #3 risinājums:** atsauce caur `<img>`/`![]()`, **ne inline SVG** (renderis bez `md_in_html` var sabojāt inline SVG).
- **Bug #5 risinājums:** Δ edge-case kontrakts kā 5.1.

### 6.2 Render branch + partial (`src/render/blog.py`, `templates/_weekly_body.html.j2`)
- `render_blog`: ja `note_type=='weekly_brief'` → izmanto `_weekly_body.html.j2` partial; citādi `blog-post.html.j2`. **Neforkot** visu blog-post (dublētu og/hero/nav loģiku — maintenance debt).
- Partial parsē `<!-- WEEKLY_STATS -->` marker uz stat-strip kartītēm; renderē cover hero ar datumu-diapazona + "Nedēļa NN" badge; `<figure>` grafikam ar parakstu.

### 6.3 `.weekly-*` CSS (`assets/style.css`)
- **Atkārtoti izmanto** esošos responsīvos paternus (`.brief-card`, `.prv2-*` grid auto-fit, esošo `@media (max-width:768px)` bloku). Pievieno plānu `.weekly-*` slāni: cover, stat kartītes (flex-wrap), figure+caption, tēmu bloki ar ink-navy kreiso malu, pull-quote. Mobile-first viena kolonna, `<picture>` webp varianti.

### 6.4 `WEEKLY_STYLE` featured rāmis (`src/graphics/prompt.py`, `graphics-designer.md`)
- Jauns `WEEKLY_STYLE` style-key: tāda pati editorial DNA, bet ink-navy rāmis + "Nedēļa NN" framing. `graphics-designer` izvēlas to, kad `note_type='weekly_brief'`.
- **Bug #4 piezīme:** AI akcenta pielietojums ir nekonsekvents (calibration note) → nedēļas vizuālā identitāte balstās uz **deterministisko CSS chrome**, ne AI attēlu; attēls ir bonuss.

## 7. Iebūvētie bug-fix (no analīzes)

1. Otrā-attēla kolīzija → grafiks ārpus `brief_images`.
2. Validācija noraida jauno struktūru → atjaunot weekly validācijas zaru (ship kopā).
3. SVG-markdown sabojāšana → atsauce kā fails, ne inline.
4. Fragila AI-attēla diferenciācija → identitāte CSS chrome.
5. Δ baseline edge-cases → absolūti skaitļi + "jauns", nekad %.
6. Kosmētika: attēla faila datums (`created_at`) vs slug datums (title) — atzīmēts, ne-blocking.

## 8. Skartie faili

**Fāze 1:** `src/briefs.py` (skeleta paplašinājums), `.claude/agents/weekly-brief-writer.md` (jauns), `wiki/operations/agenti/brief-shared-rules.md` (jauns), `.claude/agents/brief-writer.md` (atsauce uz shared-rules), `src/tools.py` (validācija).

**Fāze 2:** `src/graphics/weekly_chart.py` (jauns), `src/render/blog.py` (branch), `templates/_weekly_body.html.j2` (jauns), `assets/style.css` (`.weekly-*`), `src/graphics/prompt.py` (`WEEKLY_STYLE`), `.claude/agents/graphics-designer.md` (weekly style izvēle).

**Abām:** `wiki/operations/weekly-routine.md` (atsauce uz skeletu + jauno struktūru), `wiki/CHANGELOG.md` (formāta izmaiņas ieraksts ar pamatojumu — projekts to prasa).

## 9. Testēšana

- `generate_weekly_brief()`: unit testi par Δ aprēķinu (baseline, no-baseline, pirmā nedēļa), stat-strip markera formātu, tēmu scaffold ar avotiem. Fixtura DB.
- `weekly_chart.make_movers_svg`: SVG well-formedness, joslu skaits, Δ anotācija, tukša-nedēļa degradācija.
- Validācija: jaunā struktūra iziet, vecā/nepilnā noraida.
- Render smoke: `generate_public_site()` ar weekly note → partial renderē, grafiks `<img>` atrisinās, mobile `@media` nesalūst.
- `bash scripts/check.sh` (ruff + pytest + site smoke) zaļš.

## 10. Atvērtie jautājumi

Nav — visi četri lēmumi apstiprināti (akcents, grafiks, aģents, fāzes).
