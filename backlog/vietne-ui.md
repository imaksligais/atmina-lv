# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Publiskā vietne — renderēšana un veiktspēja

### [DEFERRED] balsojumi «Visa vēsture» kolonnu virtualizācija — ~1,06 milj. šūnu

TAB 1 kartiņu daļa izpildīta (`13e1cd06`; 2026-09-25 `balsojumi.html` 532 884 B, `<details>` 0). Paliek A: `balsojumi-matrica.json` 7 640 × 139 ≈ **1,06 milj.** šūnu (bija 770 k), `bmv1.js` virtualizācijas nav. Plāns: `docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md` (spacer + absolūti pozicionētas šūnas, redzamo kolonnu diapazons pēc ritināšanas; ARIA `aria-rowcount`). *Trigeris:* lasītāja signāls par mobilo ātrumu. *Īpašnieks:* operators.

## Profili / UI

### [OPEN] Sava vizuālā identitāte — unikāls fonts (2026-10-08, zema prioritāte)
- **Signāls:** lasītāja komentārs Reddit: lapa izskatās pēc «noklusējuma Claude izvades», tāpēc dati šķiet mazāk ticami. Fakts: Styrene netiek lietots (sistēmas sans + Georgia + JetBrains Mono), bet Georgia virsraksti + mono etiķetes + krēmīgi toņi + sepijas attēli veido atpazīstamu AI-ģenerētu stilu.
- **Rīcība (operators 2026-10-08: «vēlāk darīsim ar savu unikālo fontu»):** savs burtveidolu pāris (LV diakritika!), krāsa, logotips. Paralēli — redzamāka «Kā mēs strādājam» un labojumu žurnāls. *Īpašnieks:* operators.

### [OPEN] UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
Pabeigtais darbs — trīs fāzes, sākumlapas pārveide un visi commit heši — pārcelts uz [CHANGELOG arhīvu § 2026-07-04 UI dizaina audits](../wiki/CHANGELOG-arhivs.md) 2026-08-03. Šeit paliek TIKAI atlikums.

- **[NESKAIDRS 2026-10-09] Gala revīzijas minoru paliekas:** pretrunu fakta datums = `new_date` nevis `detected_at`. Sākumlapas pretrunu kartītē rūts «Pašlaik» rāda `new_date` = izteikuma datumu — izskatās apzināti; operatoram jānosauc, kas tieši ir defekts, citādi izsvītrot. (Līderu joslas saite → «Visi profili →» un `initials` no `rankings.py` — izpildīts 2026-09-23, CHANGELOG 2026-09-23 (4).)
- ~~`analizes.html` 360 px ritinās horizontāli par 15 px~~ — IZDARĪTS 2026-10-09 (CHANGELOG 2026-10-09 (2)). Vainīgā nebija `.pagehead-tabs`, bet `.daily-card`: telefonā virsrakstam palika ~81 px.
- **Reviewer-nits (07-07 uzmanības centrs):** paliek `#8b8fa3` fallback literālis — kandidāts konstantei paketē `src/render/_common/`, tīri mehānisks. **Pārmērīts 2026-09-25: 31 trāpījums 15 failos** (08-15: 30/15; vaicājums: `grep -rio '#8b8fa3' src templates assets --exclude-dir=__pycache__ | wc -l` un tas pats ar `-ril` failiem). Ņem vērā: `src/render/dashboard.py:53` jau tur `_TRENDS_FALLBACK_COLOR`, tāpēc konsolidācija ir esošas konstantes pacelšana uz `src/render/_common/`, ne jaunas radīšana. (`_fetch_tensions` dubultizsaukums un `#c25e5e` atrisināti.)
- **Dizaina parāda paliekas:** font-size/line-height TOKENIZĀCIJA (apzināti atlikta — simtiem deklarāciju, mazs redzamais ieguvums); vēsturiskie breakpointi 480/560/640/700 (dokumentēti pie :root, migrē tikai pieskaroties komponentei); statistika-detail "N ieraksti" lv_plural (curated re-freeze vārti).
- **A11y paliekas (no 2. fāzes):** nav `aria-label="Galvenā izvēlne"` prasa `_CHROME_SPECS` regex paplašināšanu `<nav class="nav"[^>]*>` (`_orchestrator.py:176-177`, backward-compatible — vajag operatora svētību frozen-regex maiņai); statistika canvas sparklines teksta alternatīva (curated); zinas/pretrunas feed-item virsraksti; skip-link + typeahead nav uz curated lapām (nav sgv1.js → plain GET fallback, apzināti pieņemts).
### [OPEN] Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3

Trīs ieraksti, apvienoti 2026-08-05, skar vienu virsmu — **pārbaudi, kas jau izdarīts, pirms sākt.** 2. līmeņa plāns: `docs/plans/2026-07-26-profila-ux-tier2.md`; ātrviežu pakete DONE (CHANGELOG § 2026-07-26). Plāna 2. punkts (tēmu čipu deep-link) IZPILDĪTS 2026-09-05 (`60665b11`, `tests/test_profile_topic_deeplink.py`); 1. un 3. punkts (citāts Pozīciju cilnē, `Atturas` skaidrojums) IZPILDĪTI 2026-10-09 (`tests/test_profile_positions_quote.py`); atvērts — pretrunu flags. Agrākais pilnais teksts: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

- **Wiki sintēzes bloku ports uz publisko UI:** `wiki_sync()` raksta synthesis bloku (top tēmas / 30 d / spriedzes / pretrunas) starp `<!-- SYNC-AUTO -->` markeriem (plāns `docs/superpowers/plans/archive/2026-04-20-wiki-synthesis-block.md`) — tos pašus datus parādīt **publiskajās politiķu profila lapās**.
- **Bloks 3** (slāņi 1+2+3 MERGED 2026-05-14): Saeimā cilnes redizains (prasa „svarīga balsojuma" definīciju); Saites story-driven sub-summaries; Publikācijas filtri žurnālistiem (prasa documents metadata paplašinājumu); data freshness + citation/share poga; URL hash deeplink no ārpuses; VAD delta bloks Pārskatā (atsevišķs spec). Review saturs: `git show c03ce566^:wiki/profile-page-review.md`.
- **Pārskats cilne tieva** lielākajai daļai profilu (Bloks B prasa `confirmed=1 AND salience≥0.5`). Izdarīts: aktivitātes grafiks (`monthly`), «Balso kopā ar savu frakciju» (CHANGELOG 2026-10-09 (8)). Atvērts: Par/Pret/Atturas mini-bar — operatora lēmums (ieteikums nedarīt: rāda koalīciju/opozīciju, ne cilvēku); žurnālistiem/analītiķiem Pārskata nav (`politicians.py` izslēdz) — dominējošās komentāru tēmas + visvairāk komentētie politiķi.
- **Personas lapa:** partiju rail grupēts pēc koalīcijas statusa — **ATLIKTS 2026-10-09 (operators)** līdz 15. Saeimas koalīcijas pārslēgšanai (`backlog/saeima.md` § 15. Saeima): `parties.coalition_status` ir 14. Saeimas stāvoklī, lapa pēc noklusējuma rāda 15. Saeimā ievēlētos → SV (13 ievēlēti) zem «Bez Saeimas frakcijas», ZZS (0) zem «Koalīcijā». Ieviešana bija ~12 rindas `render_personas()` (grupas coalition → opposition → other ar `get_coalition_map`, vārdi kā «Koalīcija» railā) + `.pnv1-rail-subtitle`; netika komitēta; ~~aktīvo filtru čipi desktopam~~ (jau ir — 1280 px čips «15. Saeimā ievēlētie ×», pārbaudīts 2026-10-09); meklētājs neatrod tēmas („kurš runā par airBaltic?"); ~~foto placeholderi — iniciāļi ar partijas krāsas toni~~ (nav vajadzīgs: 253/253 kartītēm ir foto fails, visi md5 atšķirīgi, pārbaudīts 2026-10-09). ~~Metriku kolonnas nelīdzinās~~ — IZDARĪTS 2026-10-09 (CHANGELOG (7)).
- **Saeimā cilne:** ~~motīfu apcirpšana vārda vidū~~ (izdarīts 2026-10-09); frakcijas-diverģences highlight (alignment SQL eksistē); grupēšana pa sēdēm.
- **Timeline cilne:** mēnešu grupu virsraksti + tipa filtru čipi (pozīcijas/balsojumi/pretrunas). (Ārējās recenzijas «laika ass profilā», verdikts 45 — ATLIKTA.)
- **Dalīšanās kartiņas** (verdikts 45 — ATLIKTS; plāns `docs/superpowers/plans/archive/2026-04-21-shareable-pretrunu-kartinas.md`).
- ~~**Citāts Pozīciju cilnē**~~ — IZDARĪTS 2026-10-09 (CHANGELOG 2026-10-09 (3)).
- ~~**Pozīciju tabula telefonā šaura**~~ — IZDARĪTS 2026-10-09: ≤768 px rinda = kartīte (CHANGELOG 2026-10-09 (4), tests `test_profile_tabs_mobile.py::test_mobile_positions_table_rows_are_cards`).
- **Saites mini-grafs:** vote alignment top/bottom 3 → pilna tabula. **Mediju/iestāžu profiliem** trūkst „kāpēc mēs to izsekojam" explainer + cross-link uz `mediji.html`.

### [DEFERRED] Tēmu direktorija un tēmas lapa — 2. kārta (meklēšana, kārtošana, jautājumu salīdzinājums)

Pirmā kārta izpildīta 2026-09-06 (`2b48c541`; `docs/arhivs/handoffs/HANDOFF-2026-09-06-temas-airbaltic.md`). **Verdikts 46: ATLIKTS līdz lasītāju signālam** — vēlēšanu sezonā datu integritāte atmaksājas vairāk nekā UI. Paliek produkta virziens:

- **Direktorija (`temas.html`):** meklēšana pēc tēmas/sinonīma (`pzv1.js` jau lasa `q` parametru), kārtošana alfabētiski / pēc jaunākās aktivitātes / pēc apjoma, pēdējās pozīcijas datums kartītē. Saistīts ar § Profilu UI parāds «meklētājs neatrod tēmas».
- **Tēmas lapa:** tvērums un periods → konkrētie jautājumi → analīzes → filtrējamas pozīcijas → balsojumi / programmu solījumi atsevišķi → saistītās tēmas. `RELATED_TOPICS` sedz 2 no 33 tēmām — paplašināt, kad tēma tiek lasīta.
- **Lielākais iespējamais papildinājums:** konkrēta jautājuma salīdzinājums pa personām/partijām ar nosacījumiem, datumu, avotu un «nav fiksētas pozīcijas» šūnu. `program_promise` nejaukt ar pozīcijām; balsojumus — ar mediju izteikumiem. Bez auto-sintēzes, bez konsekvences reitinga (§ Ne-darīt).

*Trigeris:* lasītāju signāls. *Īpašnieks:* operators.

### [OPEN] Statiskās analīžu lapas dreifē — `vad-2026` klase pārējām `content/analizes/*.md` (2026-09-20)

`vad-2026` skaitļi četrus mēnešus (05-05 → 09-20) stāvēja ar tādvārža rindu un galveni 2262/144 pret DB 2254/159, un neviens vārts to neredzēja, kamēr operators nepajautāja. Tagad tai ir ģenerators (`scripts/vad_analysis_numbers.py`) + vārti (`audit_vad_profile_match.py`) + recepte (`wiki/operations/vad-declarations.md` § Analīzes lapas atsvaidzināšana). **Pārējām statiskajām lapām nav ne ģeneratora, ne vārtu, ne `Atjaunots` datuma:** `deklaracijas-2026` (KNAB partiju finansējums, 2026-04-08), `amatpersonas-un-biedribas` (08-12), `nvo-dotacijas-2025` (07-28), `nvo-valsts-maksajumi` (08-09), `partiju-tests` (09-10). Rīcība: katrai — (a) kas ir datu avots un vai tas kopš publicēšanas mainījies; (b) ja skaitļi atvasināti no DB — ģenerators + vārti pēc `vad-2026` parauga; ja no ārēja XLSX — `Atjaunots` datums un avota versija tekstā. Lēmums, kuras lapas ir dzīvas un kuras — datēts momentuzņēmums: operatora.

### [SLĒGTS 2026-10-09] Dienas pārskata Pretrunu tabulā pilnais apraksts — īsā šūna + saite kā nedēļas pārskatā

**Izdarīts 2026-10-09** (CHANGELOG 2026-10-09 (1)): `generate_daily_brief` lieto `contradiction_excerpt` (pārdēvēts no `weekly_contradiction_excerpt`); tests `tests/test_briefs.py::TestPretrunasSection::test_pretrunas_cell_is_excerpt_with_page_link` (bez labojuma krīt). Publicētie pārskati nav pārrakstīti.

Nedēļas pārskats kopš 2026-09-27 rāda ≤50 vārdu izvilkumu + saiti `/pretrunas/<id>.html` (`src/briefs.py::contradiction_excerpt`); dienas tabula joprojām ieliek visu pirmo rindkopu (pretruna #53 — 213 vārdi vienā šūnā, telefonā teksta siena). 2026-06-10 «negriezt tabulas tekstu» noteikums radās, kad šūna bija vienīgā teksta kopija; tagad katrai apstiprinātai pretrunai ir sava lapa. Operatora virziens 2026-09-28: JĀ, nav steidzami.

*Rīcība:* `generate_daily_brief` Pretrunu rindā lietot to pašu helperi; tests pēc `test_weekly_pretrunas_cell_uses_excerpt` parauga; jau publicētos pārskatus nepārraksta. *Īpašnieks:* koda darbs.
