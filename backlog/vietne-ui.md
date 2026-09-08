# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Publiskā vietne — renderēšana un veiktspēja

### [DEFERRED] Render lazy pre-fetch — MVP fetcē politicians/claims/contradictions visos call ceļos

Šis ir vienīgais atlikums no bijušā § Render self-join lēnās stadijas ieraksta. **Kodols SLĒGTS 2026-08-20** un no 2026-09-05 dzīvo tikai CHANGELOG-ā (§ 2026-08-20 un § 2026-09-05): abi balsojumu self-join aizstāti ar kopīgu numpy precompute `src/render/_common.py::vote_alignment_data` (~101 s → ~2 s; paritāte 0 nesakritību gan 9 034 pāros, gan visos 195 per-pid sarakstos; orākuls `tests/test_vote_alignment_precompute.py`), `politiki+saites` domēni ~48 s kopā.

**Kas paliek:** MVP renderēšanas ceļš joprojām fetcē `politicians`/`claims`/`contradictions` VISOS izsaukuma ceļos, arī tur, kur tie netiek lietoti. Zema prioritāte — pēc kodola labojuma tas vairs nav dominējošais laiks. *Īpašnieks:* operators.

### [DEFERRED] balsojumi.html Step 3
Plan: `docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md`. Steps 1+1.5+2 DONE (367 MB→142 KB br). Atlikušais, ja signāli par bottleneck:
- **A. Column virtualization "Visa vēsture":** šobrīd 770k DOM šūnu, render 2–5s mobilā. Spacer + absolūti pozicionētas šūnas, on-scroll visible col range (~150–200 rindas JS; ARIA `aria-rowcount` tricky).
- **B. TAB 1 cards (200×38 KB=7.6 MB):** B1 — drop SSR `<details>`, JS popover ar matrix JSON lookup (3.2 MB SSR, ~80 r. JS); B2 — tikai pirmie 50 ar details (~4.3 MB); B3 — pilna vote-list virtualizācija (daudz koda). Prioritāte ZEMA (8 MB OK desktop; mobilā 13s @5 Mbps).

### [DEFERRED] F5 — migrāciju formāts (`migrations/` + `schema_migrations`), atlikts līdz nākamajai DDL maiņai

Pārcelts šurp 2026-09-05 no `docs/plans/archive/refactor-plan-2026-04-29.md`, kad tas plāns tika arhivēts: **F5 bija tā vienīgā atvērtā rinda 62 KB failā**, un neatzīmētie čekboksi tur lasījās kā izpildāmas instrukcijas. Pārējās fāzes (0, 1, 2, 3a–3g, 4) ir PABEIGTAS un mergētas master (`generate.py` 4 250 → 173 LOC, 17 `src/render/*` moduļi, kanoniskais ceļš `from src.render import generate_public_site`). *Piezīme par vietu: tematiski tas ir shēmas/DB darbs, ne UI — šeit tas stāv tāpēc, ka nāk no render refaktoringa plāna un ir tā pēdējā rinda.*

**Kas atlicis (plāna § Fāze 5, 1 sesija):** `migrations/__init__.py` + `migrations/_runner.py`; `schema_migrations` tabula (`version` PK, `applied_at`, `checksum`) `src/schema.sql`; `init_db()` sauc `apply_migrations(conn)` pēc `executescript(schema.sql)`; pirmā reālā migrācija `migrations/0001_<nākamais DDL>.py`; tests `tests/test_migrations.py` (idempotence).

**Kāpēc tas joprojām nav darīts, un tas ir pareizi:** F5 pēc paša plāna ir NOSACĪTS — to sāk **tikai tad, kad nāk nākamā DDL maiņa**. Šodien `init_db()` DDL migrācijas nes Python conditional paterns (`if "col" not in PRAGMA table_info`) pēc `executescript`, jo SQLite < 3.35 nav `ALTER TABLE ADD COLUMN IF NOT EXISTS`; F5 tās absorbētu. Krustojas ar `docs/plans/2026-09-05-strukturas-tirisanas-plans.md` 5.3 (init_db migrāciju bloka izcelšana uz `src/db_migrations.py`) — ja 5.3 notiek pirmais, F5 forma jāizlemj tur, ne atsevišķi. *Īpašnieks:* operators.

## Profili / UI

### [DEFERRED] 2026-07-23 drošības audita apzināti pieņemtās paliekas
Galvenes + stingrā CSP DONE + live 07-23 (CHANGELOG § Stingrā CSP). Apzināti NErisinātās audita piezīmes, prioritātes secībā, ja operators kādreiz grib: (a) **web app manifests** (`site.webmanifest` 404 — PWA instalējamība; apple-touch-icon jau ir); (b) **tap-target izmēri** (24 elementi <48px — nav saites ~20px, hero karuseļa punkti 8×8px; reāls mobilais UX darbs, skar chrome); (c) **`<title>` 28 zīmes** (audita ieteikums 30–60 — kosmētika); (d) **robots meta taga neesamība** (noklusējums = index,follow; robots.txt + sitemap jau ir — tīri audita ķeksītis); (e) **`style-src 'unsafe-inline'`** paliek AR NOLŪKU (style="" atribūti visā vietnē; auditi nesoda). Viltus pozitīvi, NEatkārtot: leta.lv ārējo linku "timeouts" (abas saites 200 <0,3s — audita botu bloķē leta), "HTTP versijas zonde neizdevās" (301 uz HTTPS strādā), "apple-touch-icon trūkst" (ir, 200).

### [OPEN] UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
Pabeigtais darbs — trīs fāzes, sākumlapas pārveide un visi commit heši — pārcelts uz [CHANGELOG arhīvu § 2026-07-04 UI dizaina audits](../wiki/CHANGELOG-arhivs.md) 2026-08-03. Šeit paliek TIKAI atlikums.

- **Gala revīzijas minoru paliekas:** „Visas pretrunas →" saite zem Līderu joslas virsraksta (der neitrālāka), pretrunu fakta datums = `new_date` nevis `detected_at`, iniciāļu izteiksme templotē dublēta 4× (der `initials` no `rankings.py`).
- **Reviewer-nits (07-07 uzmanības centrs):** paliek `#8b8fa3` fallback literālis — kandidāts `_common.py` konstantei, tīri mehānisks. **Pārmērīts 2026-08-15: 30 trāpījumi 15 failos** (agrāk šeit stāvēja „24 vietās 12 failos" bez vaicājuma; vaicājums, kas deva jauno skaitli: `grep -rio '#8b8fa3' src templates assets | grep -v __pycache__ | wc -l` un tas pats ar `-ril` failiem). Ņem vērā: `src/render/dashboard.py:45` jau tur `_TRENDS_FALLBACK_COLOR`, tāpēc konsolidācija ir esošas konstantes pacelšana uz `_common.py`, ne jaunas radīšana. (`_fetch_tensions` dubultizsaukums un `#c25e5e` atrisināti.)
- **Dizaina parāda paliekas:** font-size/line-height TOKENIZĀCIJA (apzināti atlikta — simtiem deklarāciju, mazs redzamais ieguvums); vēsturiskie breakpointi 480/560/640/700 (dokumentēti pie :root, migrē tikai pieskaroties komponentei); `bmv1.js:220` inline gap kas prasa `!important` (JS fix); statistika-detail "N ieraksti" lv_plural (curated re-freeze vārti).
- **A11y paliekas (no 2. fāzes):** nav `aria-label="Galvenā izvēlne"` prasa `_CHROME_SPECS` regex paplašināšanu `<nav class="nav"[^>]*>` (`_orchestrator.py:176-177`, backward-compatible — vajag operatora svētību frozen-regex maiņai); statistika canvas sparklines teksta alternatīva (curated); pzv1/pnv1 rail pogām `aria-pressed`; `.link-filter-btn`/`.subtab-btn` aria-pressed; zinas/pretrunas feed-item virsraksti; skip-link + typeahead nav uz curated lapām (nav sgv1.js → plain GET fallback, apzināti pieņemts).
- NE-defekti (izmeklēts, neatkārtot): gaišais default ar dark `:root` = apzināts (c634c47); zinas/x mega-lapām pagination NErosinu (perf ne-darīt saraksts); abi `!important` izsekoti un pamatoti (802c6e8 ziņojums).

### [OPEN] Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3

Trīs agrāk atsevišķi ieraksti, apvienoti 2026-08-05, jo tie skar vienu virsmu un savstarpēji pārklājas — **pārbaudi, kas jau izdarīts, pirms sākt.** 2. līmenis ir noformēts kā plāns: `docs/plans/2026-07-26-profila-ux-tier2.md` (quote rādīšana Pozīciju cilnē, tēmu čipu deep-link ar filtru, Atturas semantikas nozīme, pretrunu flags kartītēm + filtrs — ar šķērsnoteikumiem un secību); ātrviežu pakete DONE + testēta (CHANGELOG § 2026-07-26). **No tā plāna 2. punkts (tēmu čipu deep-link ar filtru) IZPILDĪTS 2026-09-05** — čips ved uz `politiki/<slug>.html?tema=<tēma>#pozicijas`, `ppv1.js` validē tēmu pret profila filtra pogām un sinhronizē parametru, «Kopēt saiti» pārnes pašreizējo cilni + filtru; vārti: `tests/test_profile_topic_deeplink.py` + pārlūka pārbaude fikstūras renderī. Pārējie tā plāna punkti (citāts Pozīciju cilnē, `Atturas` semantika, pretrunu flags) paliek atvērti.

- **Wiki sintēzes bloku ports uz publisko UI:** `wiki_sync()` raksta conditional synthesis bloku (top tēmas / 30 d / spriedzes / pretrunas) starp `<!-- SYNC-AUTO -->` markeriem person profilos (76/148 ar saturu; plāns `docs/superpowers/plans/archive/2026-04-20-wiki-synthesis-block.md`) — operatora uzdevums ir parādīt tos pašus datus **publiskajās atmina.lv politiķu profila lapās**.
- **Bloks 3** (datu/UI slāņi 1+2+3 MERGED 2026-05-14, Pārskats cilne 149/176 profilos): Saeimā cilnes redizains (v1 „nesenākie 5 + pretdziedoši frakcijai" — prasa „svarīga balsojuma" definīciju); Saites story-driven sub-summaries; Publikācijas filtri žurnālistiem (atdalīt retweets/ziņas/oriģinālus — prasa documents metadata paplašinājumu); data freshness + citation/share poga; URL hash deeplink no ārpuses; VAD delta bloks Pārskatā (atsevišķs delta-loģikas spec). Review faili dzēsti 2026-07-20 (`c03ce566`), saturs atgūstams ar `git show c03ce566^:wiki/profile-page-review.md`.
- **Pārskats cilne tieva** lielākajai daļai profilu (Bloks B prasa `confirmed=1 AND salience≥0.5`; DB tikai 29 pretrunas) — kandidāti no esošajiem datiem: Par/Pret/Atturas sadalījums 3 mēnešos deputātiem (mini-bar), aktivitātes sparkline 6–12 mēn., frakcijas-sakritības % (alignment jau skaitļots Saišu cilnei). Žurnālistiem/analītiķiem Pārskats vispār neeksistē (`politicians.py:889` izslēdz) — dominējošās komentāru tēmas + visvairāk komentētie politiķi aizpildītu.
- **Personas lapa:** partiju rail grupēts pēc koalīcijas statusa; aktīvo filtru čipi desktopam (šobrīd tikai mobilajā); meklētājs neatrod tēmas („kurš runā par airBaltic?"); foto placeholderi — divi iniciāļi ar partijas krāsas toni.
- **Saeimā cilne:** motīfu apcirpšana 80 zīmēs pārtrauc vārda vidū; frakcijas-diverģences highlight (alignment SQL jau eksistē); grupēšana pa sēdēm.
- **Timeline cilne:** mēnešu grupu virsraksti + tipa filtru čipi (pozīcijas/balsojumi/pretrunas) — šobrīd plakana jaukta lente.
- **Saites mini-grafs:** vote alignment top/bottom 3 → pilna tabula (mezglu labeli vārdi→uzvārdi atrisināti 2026-07-29). **Mediju/iestāžu profiliem** trūkst „kāpēc mēs to izsekojam" explainer + cross-link uz `mediji.html` caurskatāmības lapu (personas rail to linko, pats profils — nē).

### [OPERATOR] Ārējās recenzijas izraksts — no sešnieka trīs jau ieviesti, trīs nav

`docs/audits/_analysis_extracted.txt` ir ārēja atmina.lv produkta recenzija (angliski). 2026-08-14 repo tīrīšanas plāns to **apzināti paturēja** (4. solis: visu pārējo no `docs/audits/` pārcēla uz auksto arhīvu), un 2026-08-22 tā ienāca gitā līdz ar mapes versionēšanu — bet tā nekad nav triažēta. Skaitļi tajā ir novecojuši: «2177 pozīcijas, 112 politiķi, 21 pretruna» pret 2026-08-23 stāvokli 5979 / 167 / 29; pēdējās 60 `wiki/index.md` revīzijās šie skaitļi neparādās, tāpēc dokumentu no repo datēt nevar.

Recenzijas «Highest ROI» sešnieks, pārbaudīts pret uzbūvēto koku 2026-08-23:

- **Jau ir (3):** sākumlapas meklēšana (`type="search"`, placeholder «Meklē politiķi, tēmu vai citātu…» — gandrīz burtiski recenzijas formulējums); izceltā pretruna jau pirmajā ekrānā — sākumlapas bloks «Uzmanības centrā» rāda politiķi, partiju, tēmu, ΔT un abus citātus ar datumiem; tēmu lapas (`temas.html`, 33 saites).
- **Nav (3):** politiķa konsekvences rādītājs (profila lapā 0 trāpījumu «sakritība/konsekvence»); laika ass profilā; dalīšanās kartiņas (plāns arhivēts — `docs/superpowers/plans/archive/2026-04-21-shareable-pretrunu-kartinas.md`).

**Verdikts 45 (2026-09-06, izpildīts 2026-09-07):** **konsekvences rādītājs — NĒ** (`BACKLOG.md` § Ne-darīt to jau aizliedz: reitings pār nepilnīgu korpusu ir apgalvojums par cilvēku, ne mērījums); **laika ass profilā un dalīšanās kartiņas — ATLIKTAS**, jo recenzijas skaitļi ir novecojuši (2 177 pozīcijas pret ~6 500 šodien), tāpēc pats izraksts vairs nav prioritāšu avots. **Izraksts paliek TIKAI kā vēstures pieraksts** — nākamā sesija lai to neatver kā uzdevumu sarakstu. *Īpašnieks:* operators.

### [OPEN] Tēmu direktorija un tēmas lapa — 2. kārta (meklēšana, kārtošana, jautājumu salīdzinājums)

Pirmā kārta IZPILDĪTA 2026-09-06 (`2b48c541`): sintēžu piesaiste pēc sluga (8/9 bija nepiesaistītas), arhīva saite uz `pozicijas.html?tema=`, `?tema=` uz profiliem, `RELATED_TOPICS` karte (airBaltic, Klimats), etiķetes; 10 testi `tests/test_topics.py`. Handoff + pierādījumi: `docs/HANDOFF-2026-09-06-temas-airbaltic.md`, `docs/TODO-2026-09-06-temas-airbaltic.md`.

Paliek produkta virziens, ko NEieviest bez lasītāju signāla:
- **Direktorija (`temas.html`):** meklēšana pēc tēmas/sinonīma (`pzv1.js` jau lasa `q` parametru — atkalizmantojams), kārtošana alfabētiski / pēc jaunākās aktivitātes / pēc apjoma, pēdējās pozīcijas datums kartītē. Saistīts ar § Profilu UI parāds rindu «meklētājs neatrod tēmas („kurš runā par airBaltic?")».
- **Tēmas lapa:** īss tvērums un periods → konkrētie jautājumi → analīzes → filtrējamas pozīcijas → balsojumi / programmu solījumi atsevišķi → saistītās tēmas. `RELATED_TOPICS` karte pagaidām sedz 2 no 33 tēmām — paplašināt, kad tēma tiek lasīta.
- **Lielākais iespējamais papildinājums:** konkrēta jautājuma salīdzinājums pa personām/partijām («papildu valsts finansējums airBaltic», ne «par/pret airBaltic») ar nosacījumiem, datumu, avotu un «nav fiksētas pozīcijas» šūnu. Programmu solījumus (`program_promise`) nejaukt ar pozīcijām; balsojumus — ar mediju izteikumiem. Bez auto-sintēzes, bez konsekvences reitinga (§ Ne-darīt).

**Verdikts 46 (2026-09-06): ATLIKTS līdz lasītāju signālam** — vēlēšanu sezonā datu integritāte atmaksājas vairāk nekā UI.

**Ārpus šī ieraksta, jau izdarīts un gaida deploy.** 2026-09-06: «Nozīmīgums 0.50» → vārds (`salience_label`, `tests/test_salience_label.py`). 2026-09-07: **`pmo.ee` avota etiķetes ieraksts SLĒGTS** (verdikts 41, CHANGELOG 2026-09-07 (9)) — `_domain_label()` ņem etiķeti no `documents.source_domain`, URL NAV migrēts (tas ir `store_claim()` idempotences trijnieka daļa); pieslēgtas visas claim virsmas vienā piegājienā, ieskaitot `src/render/topics.py:164`, ko šī rinda prasīja labot kopā. Šaurajā renderī `pozicijas-data.json` 176 → 0 `pmo.ee`, tēmu lapās 20 → 0. **Live tas vēl nav — aiziet ar nākamo rutīnas deploy** kopā ar Nozīmīguma vārdiem un profilu sintēžu sīktēliem. *Īpašnieks:* operators (prioritāte).
