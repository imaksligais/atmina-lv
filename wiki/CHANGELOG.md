# atmina — CHANGELOG

Vēsturiskas datu modeļa un pipeline izmaiņas. Runbookiem un `CLAUDE.md` jāpaliek tīriem no datumu atzīmēm — jaunas izmaiņas loģē šeit un atsaucas no attiecīgā runbook vai invariant. Ieraksti līdz 2026-05 (ieskaitot) dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md); atsauktajiem ierakstiem šeit paliek enkuru-stubi (sadaļa "Arhīvs" faila beigās).

---

## 2026-07-23 — Stingrā CSP: drošības galvenes + viss inline JS uz assets/*.js

- **Kāpēc:** ārējs drošības audits atklāja, ka vietnei nav nevienas drošības galvenes; pēc to pievienošanas audits pamatoti iebilda pret `'unsafe-inline'` skriptiem CSP. Dziļākais pamatojums: vietne pārpublicē skrāpētu ziņu/X tekstu — stingrs `script-src` nozīmē, ka pat ja escaping kļūda kādreiz ielaistu ļaunprātīgu skriptu lapā, pārlūks to atsakās izpildīt (XSS aizsardzības tīkls zem mūsu koda).
- **Galvenes** (`assets/htaccess.template`, kopētas caur `static` render domēnu): HSTS (`max-age=31536000`, bez `includeSubDomains` — apakšdomēnu HTTPS pārklājums nav verificēts), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, un CSP ar `script-src 'self' https://cloud.umami.is https://d3js.org` — **BEZ `'unsafe-inline'`**. `style-src` apzināti patur `'unsafe-inline'` (style="" atribūti ir visā vietnē; auditi to nesoda). Jauns ārējs resurss = papildinājums CSP sarakstā, citādi tas klusi nolūst TIKAI produkcijā (lokālam priekšskatam galvenes nav).
- **Inline JS evakuācija (~2000 inline bloku 800+ lapās → 14 jauni `assets/*.js`):** `theme-init.js` (bloķējošais FOUC aizsargs + fontu media-swap uz `link[data-font-async]` — aizstāj `onload=` triku), `chrome-v1.js` (viss chrome IIFE; cuelume imports caur `document.currentScript`, ne vairs `{{ assets_prefix }}`; + vispārīgā `[data-card-href]` kartīšu delegācija), un pa lapu saimei ixv1/anv1/ppv1/ptv1/blv1/lkv1/prv1/spv1/znv1/sav1/stv1/fnv1. Per-lapas dati → ne-izpildāmi `<script type="application/json" id="…">` bloki (CSP tos neskar); visi `on*=` atribūti → `data-*` + delegācija. `ms-a11y.js` ieguva deleģēto multi-select meklēšanas filtru (24 `oninput=` noņemti; per-lapas `window.filterOptions` kopijas dzēstas).
- **Kārtības atkarības saglabātas:** `blv1.js` lādējas SINHRONI aiz `bmv1.js`; `sav1.js` — aiz d3; chart-atkarīgie faili `defer` aiz `chart.min.js` (defer saglabā secību). saites `renderNodeSection` innerHTML-`onclick` (zem stingrās CSP mirst KLUSI klikšķa brīdī) → `[data-section]` delegācija.
- **Chrome-sync kontrakts atjaunināts** (`_CHROME_SPECS`): bāzes fragments tagad = `<nav>` + ārējais `chrome-v1.js` src-tags; curated-mērķa regex ar opcionālu tieši sekojošu skriptu (negatīvs lookahead izslēdz application/json blokus) — idempotents UN izlabo **pre-eksistējošu bugu**: vecās iesaldētās curated lapas nesa novecojušu inline chrome skriptu, ko sync dublēja (`statistika.html` būvē bija DIVI chrome skripti). Fragments tagad renderē arī `{{ assets_version }}` (`_rendered_chrome` jauns parametrs). `_resolve_assets_version()` hardkodētais 7 failu saraksts → `style.css + glob("*.js")`.
- **Curated re-freeze:** statistika dashboard + 10 detaļlapas pārģenerētas no nemainīta `data/csp.db` un no jauna iesaldētas `curated/atmina/` (diff = tikai head/skripti/JSON bloki + ~3 mēnešu uzkrātā chrome novirze — favicon komplekts, SVG logo, skip-link); `finanses.html` rediģēts ar roku (3 `data-filter-table` ievades, theme-init tags).
- **Invariants noslēgts:** jauns `tests/test_no_inline_js.py` — neviens izpildāms `<script>` bez `src=`, neviens `on*=` atribūts templotēs, curated lapās un JS virknēs (innerHTML ceļš). Char bāzlīnijas pārģenerētas vienreiz. Verifikācija pirms deploy: lokāls serveris ar iešūtu jauno CSP galveni + Playwright pārstaigāja ~20 lapu saimes ar interakcijām — 0 pārkāpumu; tas pats atkārtots produkcijā pēc deploy.
- **Procesa mācība (dārga):** 9 paralēlie implementācijas sub-aģenti vienā darba kokā — viens patvaļīgi izpildīja `git stash`, noslaukot pārējo necommitēto darbu; atgūts no dangling stash commit (`git fsck --unreachable` → `git checkout <sha> -- .`) ar pilnu failu-pa-failam rekonsiliāciju. Turpmāk paralēlo sub-aģentu briefos: git TIKAI lasāmi (`status`/`diff`/`log`); stash/checkout/restore/reset/clean/commit AIZLIEGTI.

## 2026-07-22 — Bloku etiķete "Ārpus Saeimas" → "Bez Saeimas frakcijas"

- **Kāpēc:** bloks visās virsmās grupē pēc PARTIJAS statusa (`parties.coalition_status='not_in_saeima'`, personu lapā arī `other`), nevis pēc deputāta mandāta — tāpēc tajā nonāk arī ievēlēti deputāti, kuru partijai Saeimā nav frakcijas. Precedents, kas kļūdu padarīja redzamu: Oļegs Burovs (GKR, 5484 balsis, Valsts pārvaldes un pašvaldības komisijas priekšsēdētājs) 22.07 pārskatā stāvēja rindā "Ārpus Saeimas". Vecais nosaukums lasītājam meloja; jaunais ("Bez Saeimas frakcijas") ir patiess visiem bucketa iemītniekiem — gan ārpus-Saeimas partijām (ASL, MMN), gan deputātiem bez frakcijas (GKR), gan personu lapas bezpartijas personām.
- **Kur nomainīts:** `src/briefs.py` (dienas + nedēļas skeleta bloku tabula), `templates/personas.html.j2` + `assets/pnv1.js` (personu lapas sānu joslas grupa un filtra čips). DB statusa vērtības (`not_in_saeima`/`other`) NEmainās — tikai cilvēklasāmā etiķete.
- **Kas apzināti NAV mainīts:** vēsturiskie publicētie pārskati (DB `daily_brief`/`weekly_brief` rindas, `wiki/dailies`, `wiki/weeklies`, rollback SQL, testu fikstūras) — tie ir saglabāts teksts ar veco etiķeti; 22.07 pārskats atjaunināts, jo bija dienas aktuālais. Nākotnes ģenerācijas etiķeti ņem no koda.
- 22.07 pārskatam bloku sadaļā pievienots paskaidrojošs teikums par Burova gadījumu (deputāts bez frakcijas) — piemērs, kā bloka semantika lasāma.

## 2026-07-17 — Balsojumu sekcijas pārbūve (viens renderēšanas ceļš) + klātbūtnes reģistrāciju izslēgšana + UI skaņas + gaišās tēmas aizsardzība

- **"Deputātu klātbūtnes reģistrācija" izslēgta no balsojumu renderēšanas** (`13e1cd0`, operatora lēmums): 316 reģistrācijas notikumi (visi totāli 0, maldinošs `result='Noraidīts'`) nav balsojumi — tie aizsprostoja saraksta augšu, piepūta matricas JSON ar `.`/`X` kolonnām un kropļoja `total`/`accepted_pct`/`attendance_pct` saucējus. Filtrs `_fetch_votes` SQL līmenī ar **prefiksa** formu (`NOT LIKE 'Deputātu klātbūtnes reģistrācija%'`) — `%reģistrācij%` noķertu īstus balsojumus (Civilstāvokļa aktu reģistrācijas likums). **DB rindas paliek** — T8 pilnīguma auditi pēc `(vote_date, vote_time)` tās joprojām redz. Sedz `tests/test_votes_registration_filter.py`. Blakusatradums → BACKLOG: reģistrācijas individuālās rindas glabā HTML-entītiju garumzīmes (`Re&#291;istr&#275;jies`, ~30k rindu; pēc filtra nekur nerenderējas).
- **balsojumi.html "Option 2": SSR vote-card ceļš dzēsts, kartītes VIENMĒR renderē klients** (`13e1cd0`): lapa 6,4 MB → **425 KB (−93 %)**. Sakne: katra no 200 SSR kartītēm nesa slēptu `<details>` tabulu ar ~90 deputātu balsojumiem (~25 KB katra) — tie paši dati, ko `assets/bmv1.js` jau lādēja kompaktajā matricas JSON un mācēja renderēt SSR-identiski (`archiveBuildCard`). Tagad: sākums no recent-sharda (105 KB br; jauns `opts.wantFull` uz `balsojumiArchiveRender`), pilnais arhīvs tikai pie filtriem vai lappojot dziļāk par ~gadu (newest-first kārtība recent padara par pilnā prefiksu — offseti pārdzīvo eskalāciju). `_fetch_votes` N+1 (~11,4k vaicājumi/renderā) → 1 batchots `GROUP BY vote_id, faction`; deputātu filtra opcijas no `DISTINCT` vaicājuma; `votes` konteksta atslēga veidnei noņemta; neto −104 rindas. **Dziļie linki:** svaigs `#vote-N` izceļas sarakstā; ārpus renderētā — tūlītēja atkāpe uz Matricu pirmajā renderī (regress noķerts diff-reviewā; vecā SSR semantika saglabāta). `<noscript>` piezīme JS-atkarībai. Sedz `tests/test_balsojumi_client_render.py` + `tests/test_fetch_votes_batched.py`.
- **`<meta name="darkreader-lock">` + dinamisks `meta[name=color-scheme]`** (`eeeb271`): Brave iOS "Night Mode" (DarkReader-bāzēts) gaišo tēmu pārkrāsoja olīvbrūnā puskrāsojumā (silto nokrāsu saglabājošā tumšošana + daļēja apstrāde). Vietnei ir pati sava tumšā tēma → darkreader-lock ir DarkReader dokumentētais "neaiztikt" signāls. Statiskais `content="light"` meta (kas tumšajā tēmā aicināja auto-dark rīkus tumšot jau tumšu lapu) tagad sinhronizējas ar aktīvo tēmu (agrīnais bootstrap + pārslēga sync). Sedz `tests/test_base_theme_meta.py`. Papildina 2026-06-13 gaišās tēmas ierakstu.
- **Opt-in UI skaņas (cuelume)** (`1c3bb25`, `42038c2`): skaļruņa slēdzis navigācijā (tēmas sviras dizaina valoda, `--switch-*` mainīgie), noklusēti IZSLĒGTS, stāvoklis `localStorage['atmina:sound']`. `cuelume@0.1.2` (MIT, 0 atkarību, Web Audio sintezē) vendorēts **verbatim** `assets/cuelume/` (+LICENSE), lādējas TIKAI ar lazy `import()` pēc ieslēgšanas — `./{{ assets_prefix }}` prefikss obligāts (bez `./` saknes lapās bare-specifier `TypeError`; regresijas asserts testā). Skaņas: ready (ieslēdzot), toggle (tēmas svira), success (kopēšana; jauns `atmina:copied` notikums), tick (tabi), page (iekšējie satura linki; ārējie avoti/enkuri klusi). Visa loģika VIENĪGAJĀ chrome skriptā — chrome-sync to pārnes uz kurētajām lapām. Sedz `tests/test_base_sound.py`.

## 2026-07-04 — NEEDS_REVIEW pilnā triāža (126→0) + "Sports" kā 32. kanoniskā tēma

- **Viss NEEDS_REVIEW uzkrājums izvērtēts un iztīrīts: 126 → 0.** 7 program_promise atrisināti inline (sk. atsevišķo ierakstu zemāk pēc datuma); **119 vēsturiskie position/commentary** triažēti ar 9 paralēliem Opus sub-aģentiem (batči pa politiķiem, ≤15 claims; kopīgs noteikumu fails ar atļauto/aizliegto darbību sarakstu). Rezultāts: **110 CONFIRMED** (marķieris noņemts, reasoning papildināts ar "Izvērtēts 2026-07-04" lēmumu un pamatojumu), **4 RETOPICED** pēc topic_map kanona (532043 Stambulas konv.→Tieslietas, 532136 Goda ģimene→Sociālā politika, 532179 pieminekļi/vēsturiskā atmiņa→Ukraina un Krievija, 532385 politiskā filozofija→Koalīcija un partijas; visiem claim_vectors pārrēķināts), **5 eskalācijas** operatoram. Master rollback ar visu 119 oriģināliem `data/rollback_needs_review_historic_triage_2026-07-04.sql`. Dizaina princips: sub-aģentiem DELETE/stance-labojumi AIZLIEGTI (tikai eskalācija) — dzēšana ir operatora lēmums.
- **Eskalāciju izpilde (operatora lēmumi):** dzēsti 3 claims, kas pārkāpj ekstrakcijas doktrīnu — 531983 Jakovins (žurnālista otrās rokas konstatējums bez citāta), 532268 Madžiņš (insinuācija bez politikas nostājas), 532482 Liepnieks (stance = sarkasma interpretācija, citāts burtiski saka pretējo). Nevienam nebija atsauču pretrunās/piezīmēs. Rollback ar pilniem INSERT `data/rollback_needs_review_escalations_2026-07-04.sql`.
- **"Sports" pievienots kā 32. kanoniskā tēma** (operatora lēmums pēc 6 atkārtotas spiešanas gadījumiem: 06-18 ×2, programmas 07-02/04 ×2, triāžas eskalācijas ×2). Izmaiņas: `src/topic_map.py` (grupa + aliasi + `_SAEIMA_KEYWORD_MAP` ieraksts — apzināti daudzvārdu atslēgas, jo kails "sport" ir substring vārdos "tran**sport**a"/"ek**sport**a"), `src/render/_common.py` TOPIC_COLORS (#c9803d medaļu bronza), `src/graphics/visual_map.py` (skrejceļš + lauru vainags), CLAUDE.md 31→32, aģentu prompti (brief-writer, claim-extractor, contradiction-hunter). #532203 (Siliņa) un #532214 (Daugavietis) pārcelti uz Sports ar embedding pārrēķinu; `temas/sports.html` ģenerējas automātiski. "sporta infrastruktūra" alias apzināti PALIEK Pašvaldībās. Programmu konsolidētās kultūra+sports pozīcijas (AS #532831, JKP #532815) apzināti paliek Kultūrā — programmas pašas bundlē šīs jomas vienā sadaļā.
- **Procesa mācības:** (a) triāžas sub-aģentiem kopīgs noteikumu fails + master rollback PIRMS dispatch ir drošais paterns; (b) topic/stance maiņa VIENMĒR prasa claim_vectors pārrēķinu (embedding teksts = "topic: stance"); (c) viens marķieris bija "NEEDS_REVIEW " bez kola — strip loģikai jāsedz abi varianti.

## 2026-07-04 — save_analysis embedding precompute (lock fix) + get_existing_claims claim_type filtrs

- **"database is locked" zem paralēlā ekstrakcijas fan-out — atlikušā klase noņemta.** Diagnoze: `PRAGMA busy_timeout=30000` + `timeout=30.0` jau bija `get_db()` (2026-04), un `store_claim` standalone ceļš embedding skaitļoja pirms savas transakcijas — bet `save_analysis()` tur VIENU `with db:` transakciju pāri visam batčam, tāpēc pēc pirmā INSERT katrs nākamais `store_claim(db=db)` savu e5-small embedding (100ms–10s) skaitļoja jau ZEM turēta write-lock; N-claim batch = N embedding izmaksu lock-hold logā → paralēlie extractori gaidīja >30s (~4 reizes 2 dienās jūlija sākumā). Fix: `save_analysis` prekompilē visus batch embeddings PIRMS `with db:` (savienojums atvērts, bet transakcija nav sākta — lock netiek turēts) un padod tos caur jaunu opcionālu `embedding_bytes=` parametru (`db.store_claim` → `tools.store_claim`); lock-hold sarūk līdz tīriem INSERT. Atomicitāte (Data Contract #9) neskarta. **Kritiskā nianse:** prekompilētajam embedding tekstam jābūt baitu-identiskam iekšējam — topic vispirms caur `normalize_topic` (to `tools.store_claim` piemēro pirms db slāņa); pydantic `Claim` modelis topic/stance netransformē. Ekvivalences tests apzināti lieto topic, ko normalizācija maina (`NATO`→`Aizsardzība un drošība`), lai izlaista normalizācija kristu. Papildu mazināšana paliek pieejama: fan-out cap ≤8 orchestratorā.
- **`get_existing_claims` vairs neizgāž saeima_vote korpusu extractor-aģentu kontekstā.** Viss ~520k `saeima_vote` korpuss (2026-05-27 bulk imports) ir `created_at` <90d logā, tāpēc balsojumu-smagiem politiķiem funkcija atgrieza tūkstošiem rindu (~98% troksnis; pid=6 → 5060 rindas) katrā claim-extractor sub-aģentā. Jauns `claim_types=("position", "commentary")` default (SQL `IN` filtrs); `claim_types=None` = legacy visi tipi; atgrieztie dicti tagad satur `claim_type`. Iekšēju Python izsaucēju nav (tikai aģentu workflow) — droša default maiņa. Pretrunu detekciju neskar (tā iet caur `search_similar_claims` ar savu `claim_type_filter`).

## 2026-07-02 — Partiju programmu analīze: `claims.party_id` + `claim_type='program_promise'`

- **Jauna spēja: partijas vēlēšanu programmas kā partijas līmeņa saturs** (`c70bbfd`, merged master + pushots). Motivācija: 15. Saeimas kampaņā partijas publisko programmas; līdz šim tās varēja glabāt tikai kā līdera personīgās `position` pozīcijas (kā 07-01 ZZS/Valainis) — sajaucot partiju ar personu.
- **Datu modelis:** `claims.party_id` (nullable FK→`parties`) — migrācija `src/db.py` (idempotents PRAGMA guard, `speaker_id` paterns) + `schema.sql` kolonna. **Gotcha:** `idx_claims_party` TIKAI migrācijā, NE schema.sql — `executescript` izpildās pirms ALTER, indekss uz vēl-neesošu kolonnu gāž `init_db()` uz live DB. `opponent_id` paliek = saraksta līderis (carrier). Threaded caur `db.store_claim`/`tools.store_claim`/`analyze.save_analysis` (`party_id=` kwarg). Rollback: `data/rollback_claims_party_id_2026-07-02.sql`.
- **Konvencijas** (CLAUDE.md #4/#4a): `claim_type='program_promise'`; **viena konsolidēta pozīcija uz tēmu** uz programmas avotu (idempotences triple `(opponent_id, source_url, topic)` — vairāki solījumi vienā tēmā no viena URL sakristu). Izslēgšana no visām pozīciju virsmām ir **bezmaksas** — katrs render/brief/coverage vaicājums jau filtrē `claim_type='position'`; vienīgā jaunā virsma ir partijas lapas "Programma" cilne (`src/render/parties.py` fetch pēc `party_id` + tēmu grupēšana; `templates/partija.html.j2`). Jinja gotcha: dict atslēga `items` sadūrās ar `.items()` metodi → `promises`.
- **PDF ielādes ceļš** `scripts/ingest_url.py`: content-type/`.pdf` detektēšana → `pypdf` ekstrakcija (jau venv, 0 jaunu atkarību); `MAX_CHARS` 50k→200k (programmas garas; 50k klusi grieza asti).
- **YAGNI apgriezumi** (operatora "viss geniālais ir vienkāršs" revīzija): NAV atsevišķa `@program-extractor` aģenta (atkalizmanto `@claim-extractor` Opus ar programmas dispatch-promptu), NAV workflow failu (tiešs sub-aģentu dispatch), NAV bulk kandidātu loadera, NAV jauna `party_programs` galda.
- **Dati live:** ZZS 11 pozīcijas (party_id=3, carrier Valainis id=25, avots apollo.lv 07-01 raksts — kopsavilkums, ne pilnā programma; `zzs.lv/zzs-programma` 404) + NA 22 pozīcijas (party_id=4, carrier Indriksone id=72, oficiālā `nacionalaapvieniba.lv/programma/`). Deploy `--no-delete`, live verificēts. **Stale-avotu mācība:** web meklēšana atgriež vēsturiskās programmas (Providus=11. Saeima 2011, `apvienotaissaraksts.lv/programma`="divi pandēmijas gadi"=2022) — pirms ekstrakcijas verificē gada kontekstu saturā; abi stale doci dzēsti.

## 2026-06-22 — Nedēļas pārskata "Koalīcija vs Opozīcija" sadaļa + movers grafika opozīcijas joslas labojums

- **Movers grafika bloku josla rēķināja tikai top-6** (`src/briefs.py::generate_weekly_brief`): "Kas kustējās" SVG "Koalīcija / Opozīcija" josla summēja blokus tikai no top-6 kustētājiem, kas ir strukturāli koalīcijas pārsvarā (Kulbergam vien 31 pozīcija) → opozīcijas (sarkanais) segments vienmēr 0, pat nedēļās, kad opozīcija bija aktīva (15.–21.06.: opozīcija 19 pozīcijas). Labots: josla rēķinās pār VISĀM nedēļas pozīcijām (koalīcija 140 : opozīcija 19; audience konti izslēgti). Regresijas tests `test_weekly_bloc_bar_counts_opposition_outside_top6` (sēj opozīcijas deputātu ārpus top-6, pārbauda sarkano segmentu > 0).
- **Nedēļas skelets tagad emitē `## Koalīcija vs Opozīcija`** — tāda pati 5-kolonnu tabula kā daily (Bloks / Pozīcijas / Partijas / Galvenie runātāji / Dominējošās tēmas), rēķināta pār visu nedēļu. Iepriekš nedēļā nebija bloku sadaļas → opozīcija bija neredzama sintēzē, kaut tā runāja. `.claude/agents/weekly-brief-writer.md` atjaunots (skelets satur tabulu → saglabā verbatim + pievieno bloku sintēzi zem tās).
- **Note 289 (15.–21.06. nedēļas analīze)** manuāli papildināta ar opozīcijas balsīm (Šuvajevs «zelta vīzas» pretsvars imigrācijas tēmā) + bloku samēra sadaļu; grafiks pārģenerēts; šaurs re-render (`--only=dashboard,blog`) + deploy (`--no-delete`), live verificēts.

## 2026-06-13 — Gaišā tēma: pilna tokenizācija, WCAG AA, noklusējuma flip

- **Gaišais režīms + "vintage" nav slēdzis** (`83c6d1e`): pilna krāsu tokenizācija (CSS custom properties), WCAG AA mērķis; saišu krāsu palete centralizēta + statistikas reduced-motion (`5bee7db`). Konvencija: datu/krāsu tekstu emitē caur `--party-color` custom property (NE inline `color:`), lai gaišajā `color-mix` patumšina uz AA.
- **Noklusējuma flip uz gaišo** (`c634c47`): anonīmais apmeklētājs tagad redz `data-theme=light` (`localStorage.getItem('atmina:theme') !== 'dark'`), tumšais = opt-in; `color-scheme`/`theme-color` attiecīgi. JS-izslēgts fallback paliek tumšs (no-FOUC bootstrap; pieņemams JS-smagajā vietnē).
- **Kontrasts verificēts AA-clean** (2026-06-13): sākotnējais QA skans (`light_scan_results.json`) bija novecojis — tas mērīja pirms-polish tokenus (piem. `--text-dim #857b63`, tagad `#6e654f`) un stat-change pilu tumšās tēmas vērtības. Programmatiskā WCAG pārbaude pret pašreizējo CSS: visas 15 partiju krāsas (`color-mix(47%, #1f1b14)` uz papīra) iztur (zemākā ASL #fbbf24 = 4.72), 31 tēmu čips ≥5.01, visi minor findings (--text-dim 5.21, badge-green 6.37, prv2 sev 5.93, role-chip 5.40) un curated statistika pili (tokenizēti `var(--green)`/`var(--red-soft)` → ≥4.72). Verdikts: `docs/audits/light-theme-qa-2026-06-13/CONCLUSION.md`. CSS izmaiņas nebija vajadzīgas — kontrasta labojumi jau ielanda ar `83c6d1e`.

## 2026-06-13 — @Krisjanis_K vārdamāsas disentangle + Freidenfelda atvienošana + pārskata tīrīšana

- **Mis-seedētā id=191 "Krišjānis Kļaviņš" pilna privacy purge** (`ab1d582`, `0f25818`, `613b9be`): id=191 `x_handle` bija `@Krisjanis_K` (vārdamāsa, ne īstais žurnālists); zero-trace dzēšana (0 rindas claims/analyses/contradictions/context_notes/social_accounts/document_politicians). Īstais žurnālists izveidots id=231 `@kr_klavins`. id=190 Freidenfelds → `relationship_type='inactive'` (X sūdzības); `tensions.py` filtrē inactive.
- **06-12 dienas pārskata misatribūcijas tīrīšana** (`1552f6c`): purge atstāja 06-12 pārskatā dzēstos claims #531910/#531911, neeksistējošu "spriedzi #114" un atvienotu profilu citātus — purge mutēja DB rindas, NE ar roku rakstīto brief prozu. Iztīrīts visās 3 virsmās: DB note #274, `wiki/dailies/2026-06-12.md`, renderētais `blog/2026-06-12.html`; bloki pārrēķināti (Neitrāli 7→5, Ārpus Saeimas 3→2), Lato Lapsa paturēts. **Mācība:** retroaktīva profila atvienošana prasa arī ar roku rakstīto pārskatu un tvītu pārbaudi — DB purge tos neaiztiek (atkārtosies pie katra nākamā retro-retire).

## 2026-06-13 — claims↔votes topic drift fix + x_mentions slot drift diagnoze

- **claims↔votes topic drift** (`9b0e752`): BACKLOG [FIX] — 49 balsojumi / **4075 saeima_vote claims**, kur `claims.topic != saeima_votes.topic` (dominē budžeta-paketes claims ar vecāku `_motif_to_topic` versiju, klasterī 2026-03-26/04-01). `votes.topic` = autoritāte; idempotents UPDATE, neskar `bill_id`/`current_stage` (inv #12). Pāra rollback ar 4075 eksplicītiem per-claim UPDATE (`data/{fix,rollback}_claims_votes_topic_drift_2026-06-13.sql`). Atlikušie **7 motif-drift balsojumi** (id=218/219/1583…) → manuālā triāža (BACKLOG).
- **x_mentions 6.json/slot_count repo↔runtime drift diagnoze** (`1a57434`): commitētais `get_pool` default = 5 sloti (vienmēr — `git log -S`), bet `mentions_fetch_guardrail` logi rāda `total=6` kopš 2026-05-18 → dzīvais (lokālais) pipeline darbināts ar 6-slotu pūlu, ko commitētais kods neražo (necommitēts lokāls labojums, kopš atritināts). Salabots maldinošais komentārs + BACKLOG formulējums. Behaviorālais lēmums (6-slot oficiāls / palikt 5 + ct0 refresh slotiem 1.json/3.json) atvērts.

---

## 2026-06-12 — x_mentions default flips uz `search` + izpildītās stratēģijas logging

A/B noslēgts (06-10..06-12; BACKLOG [OPERATOR] ieraksts; operatora apstiprināts flip):

- **`_resolve_strategy` default `"timeline"` → `"search"`** (`src/x_mentions.py`). Pamatojums: 0 kļūdu visos A/B skrējienos, t.sk. pilnajā ingest ķēdē tūlīt pēc `fetch_all_twitter`; ~5–7× ātrāk (58s pret ~5 min); plašāks tvērums (netrackoti autori). Apjoma 3× kritērijs atzīts par novecojušu — rakstīts pie ~12 mentions/7d, bet timeline jau pati sasniedza ~200/dienā. `timeline` paliek guardrail fallback (slot-health probe ≥4/5) + opt-in (`X_MENTIONS_STRATEGY=timeline` / `strategy=` kwarg).
- **`x_mentions.last_run_strategy`** modulis-stāvoklis + **`"strategy"` lauks `mentions_fetch` log details** (`src/social.py`) — klusais guardrail fallback tagad redzams retrospektīvi (līdz šim search/timeline skrējienus logos nevarēja atšķirt; 06-11 datu punkti tāpēc nebija interpretējami).
- A/B blakus-atradumi: viena slota 404 uz strict-TID endpointiem = novecojis ct0, fix = ct0 refresh bez re-login (twikit-notes.md § 2026-06-12); `get_pool` default `slot_count=5` → `6.json` produkcijā netiek ielādēts (atvērts BACKLOG); rīta deģenerēta pūla guardrail trip bija ct0 artefakts, ne sistēmiska pēc-twitter problēma.
- Datu higiēna tajā pašā sesijā: `@KlucisD` feed deaktivēts (konts X neeksistē; `data/deactivate_klucisd_2026-06-12.sql` + rollback pārī).

---

## 2026-06-12 — Topic-pārklājuma revīzija (543 balsojumi), emit-helpera dedup, JSON-LD SEO

Trīs BACKLOG vienības vienā sesijā (operatora izvēle; paralēli Opus aģenti, orchestratora diff-review):

- **`_motif_to_topic` pārklājuma revīzija** (`src/saeima/claims.py`): no 2255 fallback "Valsts pārvalde" balsojumiem **543 saeima_votes + 47 843 saeima_vote claims** pārcelti uz 9 pareizajām kanoniskajām tēmām (Budžets 253, Pašvaldības 102, Degviela un enerģētika 42, Tieslietas 37, Aizsardzība 36, Veselības aprūpe 24, Valsts kapitālsabiedrības 17, Kultūra 16, Sociālā politika 16). Galvenais cēlonis: `nodokļ` stems (mīkstais ļ) izlaida akuzatīvu "nodokli" — 170+ nodokļu balsojumi krita fallback; risināts ar `_word("nodokli")`. Kārtošanas guard-i: `nekustamā īpašuma nodokl`→Pašvaldības PIRMS budžeta nodokļu stemiem; `ieslodzījuma viet`/`kapitāla daļu un kapitālsabiedr`/`covid-19` PIRMS generic `pārvald`. Backfill `data/fix_motif_topic_coverage_2026-06-12.sql` + rollback pārī (UPDATE filtrē `topic='Valsts pārvalde'`, neskar bill_id/current_stage). Atlikušie 1712 fallback leģitīmi (procesuālie, kārtības rullis, viensēriju likumi). +13 testi; chars-baseline pārģenerēts. Pēcpārbaudē atklāts pirms-eksistējošs claims↔votes drift (49 balsojumi / 4075 claims, revīzijas neskarts) → BACKLOG [FIX].
- **br/gz emit-helpera dedup** (`src/render/_common.py::_emit_json_compressed`): 4 compress-and-write kopijas (positions/votes/links/search_index) → 1 helpers leaf-modulī. Kopijas NEbija pilnīgi identiskas — positions bez `mkdir`/`logger.info`/`default=str`; nianses saglabātas call-site pusē, unificēts tikai bitu-identiskais kodols (br q11 + gz l9).
- **JSON-LD strukturētie dati** (templates): `Organization` (base.html.j2, visās lapās, `{% block jsonld %}` āķis), `NewsArticle` (blog-post + _weekly_body), `Person` (politician.html.j2; `memberOf`/`sameAs` no DB, tukšie lauki izlaisti). 2026-06-09 audita canonical-daļa izrādījās **novecojusi** — `_render_page` canonical auto-inject jau sedz visas lapas, query-param filtri korekti konsolidējas uz bāzes URL; nekas nebija jālabo. Zināms sīkums: `dateModified` izmanto DB `created_at` formātu (bez `T`/zonas — Google pieņem, strikti nav ISO 8601). 14 render-baseline fixtures pārģenerētas (Organization bloks skar katru lapu).

---

## 2026-06-12 — Backlog ātrie fixi + operatora darbi: topic guard, acronym-guard, ReadForm patterns, Priede, Krauze

2026-06-11 sēdes ielādes pēcdarbi (BACKLOG [FIX]+[OPERATOR] kopa, operatora apstiprinājums "izdari ātros un operator"):

- **`_motif_to_topic` guard "dzīvnieku aizsardzīb"/"dzīvnieku labturīb" → Lauksaimniecība** (`src/saeima/claims.py`): generic "aizsardzīb" fallback klasificēja Dzīvnieku aizsardzības likuma balsojumus kā "Aizsardzība un drošība". Backfill: **24 saeima_votes (2023-05-25..2026-06-11, t.sk. 5859) + 2103 saeima_vote claims** (`data/fix_dzivnieku_aizsardzibas_topic_2026-06-12.sql` + rollback pārī). NB: backlog teica "2023 vēsturiski claims" — 2023 izrādījās *skaits*, skartas visas balsošanas no 2023. līdz 2026. gadam. Atlikusī pārklājuma revīzija (22/47 fallback "Valsts pārvalde") → BACKLOG [DEFERRED].
- **Acronym-guard stance ģenerēšanā** (`src/saeima/votes.py::generate_claims_from_votes`): summary pirmo burtu vairs nelowercase-o, ja pirmie ≥2 burti ir lielie ("LPV deputātu…" paliek "LPV", ne "lPV"). Testi `TestGenerateClaimsAcronymGuard`.
- **`p3_backfill_year_urllib.py` — visi trīs agenda-URL paterni** (`_extract_vote_urls_from_agenda`): static `./0/HEX?OpenDocument`, `addVotesLink(...)`, **`./Voting?ReadForm&parentID={GUID}`** (2026-06-11+; bez rezultāta etiķetes → klātesošo-vairākuma fallback). **Jauns atklājums (verificēts dzīvē):** ReadForm lapas embedded balsojuma datus servē TIKAI kamēr sesija ir "aktuāla" — dienu vēlāk tas pats URL atgriež tukšu `voteFullListByNames` (arī `&tm=` neatslēdz). ReadForm-ēras sesijas JĀielādē sēdes dienā; vēlīns backfill URLus atrod, bet katrs fetch redzami FAILo ar `empty data` (ne kluss izlaidums). Dokumentēts skriptā + `saeima-tracker.md` 2.B.
- **Inga Priede seedēta (pid=230)** + 43 `saeima_individual_votes` pārsasaistītas no NULL + 43 saeima_vote claims (`data/fix_priede_seed_2026-06-12.py` + rollback SQL). Partija: **Apvienotais saraksts** (backlog minēja ZZS — verificēts: AS frakcija, Edgara Tavara vietā pēc iecelšanas Kulberga kabinetā; LZP valdes locekle). `x_handle` apzināti NULL — `@ingapriedev` visticamāk pieder vārdamāsai (ex-Vienotības Inga Priede, 2014. g. skandāls); risks fiksēts `notes`. "Priede" = sugasvārds → formas pievienotas `matcher._COMMON_WORD_FORMS` (person-context gate, Krasta/Lāces paterns).
- **Armandam Krauzem (pid=154) negative_patterns** "Ivars Krauze" + locījumi (`data/fix_krauze_negative_patterns_2026-06-12.sql` + rollback) — diriģents Ivars Krauze (doc 52304 FP, claims netika radīti).

---

## 2026-06-10 — Mediji ↔ feed-profilu savienojums: `x_feeds`, outlet čips, Mediji/Iestādes šķelšana

**Problēma:** viens medijs eksistēja divās nesavienotās sistēmās — `/mediji` caurskatāmības lapas (sources.yaml `outlets:`) un mediju X-feed org-profili (`politiki/ltv-zinas.html` ar "Nav norādīts" galvenē un tukšām cilnēm). LSM pieci feedi, LETA un NRA dubultojās bez nevienas saites; vakardienas "Iestādes un mediji" grozs jauca Panorāmu ar armiju. Spec: `docs/superpowers/specs/2026-06-10-mediji-feed-linkage-design.md`.

**Risinājums (savienojums dzīvo config, ne DB — nav migrācijas):**
- **`outlets.x_feeds`** (sources.yaml + `src/outlets.py`): outleta X kontu saraksts; join pret `social_accounts.handle` (autoritatīvais; NE `tp.x_handle`) caur jauno `_common._outlet_feed_map`. **NB: `social_accounts.platform` reālajā DB ir `'twitter'`** (vēsturiskais nosaukums) — vaicājumi lieto `IN ('twitter','x')`; tikai `'x'` būtu kluss 0-rindu join (atklāts Task 3 verifikācijā).
- **`mediji/<slug>.html`** — jauna sadaļa "X konti un raidījumi" (`_fetch_outlet_feeds`): feed kartes ar saiti uz profilu; handle bez DB rindas → stderr skip.
- **Feed-profila galvene** — partijas slots org-feediem tagad rāda outlet saiti (`mediji/<slug>.html`) "Nav norādīts" vietā; tas pats `profile-party-tag` paterns kā politiķu partijas saitei.
- **Personas grozs šķelts:** "Iestādes un mediji" → **Mediji** (9: LTV Ziņas, Panorāma, De Facto, Krustpunktā, KNL, LETA, NRA, TV3 Ziņas, IR žurnāls) + **Iestādes** (4: NBS, LVM, LDDK, Saeimas ziņas) caur `_split_org_category` + `media_feed_ids`; sg-index abas kartē uz `cat=2` (typeahead sekcija paliek apvienota). Railā zem "Mediji" CSS-only saite "Mediju caurskatāmība →". Personas baseline reģenerēts (`REGEN=1`).
- **Jauni outleti:** TV3 (`tv3`) un IR žurnāls (`ir`) — `@outlet-researcher`, visi 5 fakti sourced; TV3 `editorial_leadership` tikai portāla redaktors (TV ziņu dienesta vadītājs 2024–2026 nebija apstiprināms ar avotu). Kopā 11 outleti.
- **`wiki/mediji.md`** — jauna wiki_sync FULLY-overwritten lapa (konfigurācijas spogulis, bez DB joiniem); indeksā `[[mediji|Mediji]]` wikilink.

---

## 2026-06-10 — Topiku robežu precizēšana: Droni ↔ Aizsardzība, Vēlēšanas ↔ Koalīcija

**Konteksts:** topiku audits (26→31 pāreja 2026-04-25 apstiprināta kā apzināta un tīra; DB 0 nekanonisku vērtību) atrada vienu reālu robežas problēmu: 93 dronu-pieminoši claims sēdēja "Aizsardzība un drošība", un viens un tas pats notikums (drona notriekšana 06-08) aizgāja uz abiem topikiem.

- **`topic_map.py` Droni aliasi** +11 (dronu/drona notriekšana, pārtveršana, pretdronu aizsardzība/sadarbība/spējas/sistēmas, FPV droni, dronu operatori/siena/ražošana).
- **Claim-extractor boundary rindas** (kanoniskajā promptā): Droni↔Aizsardzība ("izņem vārdu drons — ja pozīcija sabrūk, tā ir Droni") un Vēlēšanas↔Koalīcija (kampaņa/kandidāti → Vēlēšanas; koalīcijas virtuve/partiju pārejas → Koalīcija; tests: vai izteikums paliktu aktuāls bez tuvajām vēlēšanām).
- **Sweep:** 12 dronu-kodola claims pārcelti uz Droni (`data/fix_drone_topic_boundary_2026-06-10.sql` + rollback; 18 kandidāti triāžēti manuāli — 3 atstāti pēc kodola testa, 3 atstāti `(opponent_id, source_url, topic)` idempotences kolīziju dēļ). Droni 123→135, Aizsardzība 421→409.
- **Lēmumi bez izmaiņām:** Vide (9) + Klimats (8) NEapvienot atpakaļ (CBAM/ETS diskurss augs; pārskatīt pēc vēlēšanām); "Aizsardzības industrija" splits atlikts — sk. BACKLOG, ja tendence #260 turpina augt.

---

## 2026-06-09 — Profilu taksonomija: "Iestādes un mediji" grozs + mediju kontu datu flips + nav "Profili"

**Problēma:** personas lapā institūcijas bija izkaisītas pa nejaušiem groziem (`_persona_category` organizācijas nepazina): LVM/LDDK → "Amatpersonas", NBS/Saeimas ziņas → "Citi", un mediju plūsmas (LTV Ziņas, LETA, Panorāma, De Facto, KNL) ar `relationship_type='journalist'` stāvēja "Žurnālisti" starp cilvēkiem. Nav poga "Politiķi" veda uz lapu "Profili" ar 24 ne-politiķiem.

**Risinājums:**
- **Datu migrācija:** 5 mediju plūsmu konti `journalist`→`organization` (`data/fix_media_feeds_organization_2026-06-09.sql`, rollback pārī). **2. kārta 2026-06-10:** vēl 4 izlaistas plūsmas (NRA, TV3 Ziņas, IR žurnāls, Krustpunktā — `data/fix_media_feeds_organization_2_2026-06-10.sql`). `journalist` tagad nozīmē tikai cilvēku (6: Lapsa, Kļaviņš, Seržants, Madžiņš, Kasems, Ozols); `journalist|relay` kombinācija DB vairs neeksistē. Atjaunotas claim-extractor slot-tabulas (wiki + kanoniskais prompts), t.sk. jauna `organization|first_party` rinda (NBS/LVM/LDDK — oficiāli paziņojumi).
- **`_persona_category` 2. noteikums:** `relationship_type='organization'` → **"Iestādes un mediji"** (pirms journalist/party/role pārbaudēm). Personas raila grozi pēc abām kārtām: Deputāti 118 · Amatpersonas 40 · Žurnālisti 6 · Analītiķi 5 · Iestādes un mediji 13; "Citi" iztukšojās. Raila secība tagad kanoniska (cilvēki pirms institūcijām), ne dict-nejaušība.
- **Nav: "Politiķi" → "Profili"** (atbilst lapas H1; poga vairs nesola tikai politiķus).
- **sg-index shēma v2:** `p` tuple +8. lauks `cat` (0=politiķis, 1=komentētājs, 2=iestāde/medijs; atvasināts no `_persona_category`); `sgv1.js` typeahead rāda trīs atsevišķas sekcijas **Politiķi / Komentētāji / Iestādes un mediji** — LVM/NBS/LETA vairs nestāv starp deputātiem.

---

## 2026-06-09 — Sākumlapas meklētāja typeahead (sg-index sidecars) + `?q=` ķēdes fix

**Problēma:** hero meklētāja forma sūtīja `pozicijas.html?q=...`, bet `pzv1.js::applyUrlParams` lasīja tikai `persona/tema/partija` — **`q` tika klusi ignorēts** (meklētājs izskatījās strādājošs, bet neko nedarīja). Ieteikumu (typeahead) nebija vispār.

**Risinājums:**
- **`data/sg-index.json`** (+`.br`/`.gz`) — jauns ieteikumu sidecars (~13 KB raw / ~4 KB br), emitē `src/render/search_index.py`, gated `_want("dashboard") or _want("pozicijas")` (abi dienas rutīnas narrow ceļi to atsvaidzina). **Tuple-shēma ir load-bearing konvencija** — `assets/sgv1.js` lasa pozicionāli: `p:[name,slug,party_short,party_color,has_photo,claims,contras]` (7), `t:[topic,color,claims]` (3), `g:[name,short,color,claims]` (4). Arity lock: `tests/test_search_index.py::test_sg_index_tuple_shape`. Skaitīšanas kontrakti: claims = `claim_type='position'`; pretrunas = `COALESCE(confirmed,1)=1` (kā publiskās lapas, NE kā `_fetch_politicians` — sk. BACKLOG).
- **`assets/sgv1.js`** — lazy fetch pie pirmā focus, NFD diakritiku folding ("jan"→"Jānis", "budž"→"Budžets"), prefikss>substring rangs ar count-desc, ARIA combobox + bultiņas/Enter/Escape, progressive enhancement (fetch-kļūda → parastā GET forma). Pievienots `_resolve_assets_version` versioned sarakstam.
- **`pzv1.js` `?q=` fix** — applyUrlParams tagad ieliek `pzState.query` + aizpilda rail meklētāju.
- **Mobilais hero-search bug:** `flex: 1 1 320px` kolonnas virzienā (≤768px) kļuva par 320px AUGSTUMU — meklētājs izstiepās par milzu ovālu. Fix: `flex: 0 0 auto` mobile blokā.
- Sīkie: `chart.min.js` defer + DOMContentLoaded init; inline `onmouseover` → `.vote-link` CSS; avatāru `width/height`+`loading=lazy` (CLS); `.votes-mini` tabula ≤600px slēpj Par/Pret/Atturas kolonnas.

---

## 2026-06-08 — Workflow-audita sanācija: invarianti, klusās kļūdas, attēlu CLI, pārklājums

Daudz-skatupunktu workflow audits (6 perspektīvas) → 10 commiti (`aa03aba`→`2c3bb9a`). Galvenā tēma: **klusās kļūdas** (darbs neizdodas bez signāla) + neiekapsulēta atkārtošanās + docs/atmiņas drift.

**Datu kontrakti / invarianti (`CLAUDE.md`):**
- **Jauns rollback-pairing noteikums:** no šī brīža katra hand-run datu migrācija (`data/*.sql` vai `scripts/fix_*.py`, kas mutē rindas) commitē pāra `data/rollback_*.sql` līdzās. Rationale: rollback tikai working-tree ir viens `git clean` no neatgriezeniska zuduma (Kļaviņa reattribution = 4161 balsis). Esošie 3 `fix_*.py` bez rollback = acknowledged-debt, ne paraugs.
- **Data Contract #2 pārformulēts:** claims bez `source_url` tiek nomests `save_analysis()` validācijā (`analyze.py`), NE "DB layer" — reģistrēts kā `missing_source_url` `failures` ierakstā (ne raised). `store_claim()` tiešs izsaukums ievieto NULL. Lock: `tests/test_invariants.py::test_inv2`. Pievienots arī invariant #10 smoke (coalition truth-source seko `parties.coalition_status`, ne `relationship_type`).

**Klusās kļūdas (0-rezultāts = trauksme):**
- `@saeima-tracker` Step 2.B tagad ekstrahē DIVUS vote-URL paternus: veco statisko `/0/HEX?OpenDocument` UN jauno JS `addVotesLink("DKP","VOTE")` (kanoniskais `_ADD_VOTES_RE`, `scripts/p3_backfill_year_urllib.py`). 2026-06-04 sēde (70 balsojumi) tika klusi palaista garām, jo tika pārbaudīts tikai pirmais. + OBLIGĀTS 0-vote STOP sargs. `saeima_summary_missing` log tagad parādās operatora dashboard aktivitātes lentē.
- Dienas brief `stated_at` scoping (`_BRIEF_DAY_CLAIM_SQL`): skelets iekļauj arī šodien-ekstrahētus claims (stated=diena VAI created=diena UN stated≥diena−7d) — vakar-teikts/šodien-ekstrahēts vairs neizkrīt. + 5. "Bezpartejiskie" bloks (bezpartejiskie tracked vairs neizkrīt cauri visiem blokiem). + `lint_lv_style` melīšana/konsenss/ol-trap noteikumi.

**Jaunie rīki:**
- `src/coverage.py` + `scripts/coverage_report.py` (read-only): "tumšās zonas" deputāti (balsojumi izsekoti, bet 0 analyses + 0 position claim + 0 X feed = 25) + bez-X-feed/never-analyzed/stale-pol. `print_routine()` rāda kopsavilkuma rindu.
- `python -m src.graphics.cli` (`brief` + `thread`): aizstāj per-dienas throwaway attēlu skriptus; kanoniskā `SEPIA_STYLE` (`prompt.py`); 20 throwaway skripti → `scripts/_scratch/` (gitignored). Sk. `commands.md`.
- `/deep-check stale-pol` scope (aktīvi ≥5 poz., pretrunu pārbaude nekad/>60d).

**Tests:** visi 3 `_BASELINE_XFAIL` baseline-2026-04-29 xfail triāžēti un atrisināti (neviens neslēpa regresiju — matplotlib genuine pass, highlights fixture laika-bug, relay-author obsolēts kontrakts). `check.sh` = **1340 passed, 0 xfailed, 0 xpassed**.

---

## 2026-06-03 — Saeimas balsojumu `summary` backfill (224 → 3079) + likumi.lv rekonsiliācija

**Problēma:** 5480 no 5704 `saeima_votes` (96%) bija tukšs vai placeholder `summary`
("Kopsavilkums nav pieejams — historic backfill 2026-05-26"), visi 2022–2025. P3 backfill
([2026-05-27](#2026-05-27--p3-pilns-14-saeimas-balsojumu-backfill-511k-saeima_vote-claims))
saglabāja balsu rindas + `motif`, bet NE `summary` — tas bloķēja retorika-vs-balsojums
pretrunu detektēšanu (FP3 prasa likumprojekta saturu, ne tikai motif). `summary` ir plain
`UPDATE` (NEattiecas uz invariantu #12, kas sargā tikai `bill_id`/`current_stage`).

**Phase 1 — 2176 votes, bez skrāpēšanas.** Pašaprakstošie balsojumi (Lm14 lēmumi, komisiju
vēlēšanas, kolektīvie iesniegumi, neuzticība, P14 lēmumprojekti, deputātu atvaļinājumi,
uzticība valdībai) kompozēti no `motif` + DB balsu skaita, 140-aģentu paralēls fan-out.
317 procesuāli (klātbūtnes reģistrācija, pārtraukumi) + 21 aģenta atrasti (kvorums/debašu
laiks/darba kārtība) godīgi apzīmēti. Integritātes vārti: katra tally verificēta pret DB
(0 neatbilstības), 0 fabricētu skaitļu, P14 ≠ kolektīvais iesniegums.

**Phase 2 — 118 salient grozījumu likumprojekti (679 votes), enacted-accurate.** Pilots
pierādīja, ka titania.saeima.lv anotācijas apraksta likumprojektu KĀ IESNIEGTU (≠ pieņemtais
likums; piem. 367/Lp14 "uz pusi samazināt likmi" → faktiski "0,5% nodeva + 30% kompensācija"),
turklāt ir lēnas/serial/~33% attēlu-PDF. Pārgāja uz **likumi.lv via WebFetch** (paralēli,
enacted-accurate): base law → konsolidētais id (DuckDuckGo meklē) → grozījums pēc pieņemšanas
datuma → faktiskais saturs. Targeted atlase pēc tēmas (imigrācija, aizsardzība, nodokļi,
valsts valoda, izglītība, enerģētika). 679/679 tally-verified pret DB, visi ar likumi.lv avotu.

**Atlikušais:** 898 distinct Lp14 bills vēl placeholder (galvenokārt tehniski grozījumi,
zemāka deep-check vērtība). Recepte + audit artefakti gatavi (`data/_p2_*.py`,
`_phase2_lawmap.json`, `_bf_*.py`) atkārtošanai ar paplašinātu atlasi.

**Deploy:** full render + `deploy.sh --no-delete` → atmina.lv (verificēts live
`balsojumi-matrica-recent.json`). Backup: `data/atmina.db.pre-summary-backfill-20260603.db`.
NB: pilnais render nejauši publicēja untracked melnraksta sintēzi (`imigracijas-konsenss-2026-06`),
kas pēc tam izlabota + papildināta ar featured image — turpmāk scoped `--only=` deploy.

## 2026-06-03 — Mediji: detaļlapas redizains + rus.delfi avota noņemšana

**Detaļlapas pulējums** (`templates/medijs.html.j2` + `assets/style.css`): caurskatāmības
fakti kā kartiņas (vietā tabulai), partiju pārklājums kā partiju-krāsu joslas ar
"vidējais visos medijos" atzīmi (rāda medija sliecienu pret vidējo), politiķu sakārtotas
joslas, tēmu chips, tīrāks jaunāko rakstu saraksts. **Partiju joslas tagad klikšķināmas**
uz profila lapu — `src/render/mediji.py` injicē `party_color` + `party_slug`; slug karte
keyota gan ar pilno nosaukumu, gan `short_name` (jo `tp.party` glabājas abās formās).
Rindas bez profila lapas (Bezpartejisks, joint lists) paliek neklikšķināmas.

**rus.delfi.lv noņemts** kā avots — `sources.yaml`: izņemts gan feed (`rus.delfi.lv`),
gan `delfi-ru` outlet. Mediju skaits 10 → **9**. 316 esošie rus.delfi dokumenti PALIEK
DB (vēsturiskā analīze nemainās), tikai vairs nav outlet lapas un netiek skrāpēts. Stale
`mediji/delfi-ru.html` manuāli noņemts no servera (`--no-delete` deploy to neattīra).
Commit `e62a487`, deployed atmina.lv. Avotu saraksti atjaunoti: `wiki/project-brief.md`,
`docs/data-policy.md`; `wiki/index.md` mediju skaits pārģenerēts ar `wiki_sync`.

## 2026-06-01 — Mediji: caurskatāmības profili (config-driven entity)

Jauna publiska sadaļa `/mediji` — mediju caurskatāmības profili, analogi
politiķu/partiju profiliem, bet medijiem (LSM, Delfi, TVNet, NRA, LETA, Diena,
Latvijas Avīze, Jauns.lv, Delfi-RU, Latvijas Vēstnesis). **Bez jaunām DB tabulām:**
reģistrs ir `sources.yaml` `outlets:` bloks (`src/outlets.py` to lasa); pārklājums
(kurus politiķus/partijas/tēmas medijs atspoguļo) aprēķināts render laikā no esošajiem
`documents`/`document_politicians`/`claims` — single-pass, host-keyed (NE per-medija N+1).

**Caurskatāmības fakti** (`outlets[].facts`): pa vienam avototam ierakstam laukiem
`owner` / `funding_model` / `legal_form` / `editorial_leadership` / `founded`. Katram
faktam savs `source_url` + `as_of`; **fakts bez `source_url` (vai `value`) tiek nomests
lasīšanas laikā** (`src/outlets.py`), atspoguļojot claims "nav source_url → nomests"
likumu (Data Contract #2). Faktus aizpilda jaunais `@outlet-researcher` aģents (pēc
pieprasījuma, viens medijs reizē, cilvēks pārskata YAML diff). Visi 10 mediji, 51 fakts
aizpildīts 2026-06-01 (`ea738ab`).

**Ētika — caurskatāmība, ne mērķēšana:** identiski lauki KATRAM medijam neatkarīgi no
uztvertās nostājas; nekādu `corrupt`/`bought`/`biased` etiķešu. Editorial `framing:`
lauks (uz `sources:` feed rindām) paliek INTERNS — `@claim-extractor` confidence signāls,
nepublicēts mediji lapās.

**Render:** `src/render/mediji.py` (mirror `parties.py`) + `templates/{mediji,medijs}.html.j2`;
`"mediji"` reģistrēts `KNOWN_DOMAINS`; nav link + sitemap. Fakta lauku nosaukumi medijs
lapā kartēti uz LV (`Īpašnieks` / `Finansējums` / `Juridiskā forma` / `Redakcijas vadība` /
`Dibināts`; `3aad7bd`). Spec/plāns:
`docs/superpowers/{specs,plans}/2026-06-01-media-outlet-profiles*`.

## 2026-06-01 — Nedēļas pārskats: atsevišķs formāts (saturs + vizuālais)

Nedēļas pārskats vairs nav daily klons. `generate_weekly_brief()` (iepriekš
orphaned, bez izsaucējiem) paplašināts ar week-over-week deltām, `<!-- WEEKLY_STATS -->`
marķieri un tēmu scaffold ar avotiem. Jauns `@weekly-brief-writer` aģents
(koplietotie noteikumi izvilkti `wiki/operations/agenti/brief-shared-rules.md`;
`@brief-writer` sašaurināts uz daily). Render caur `templates/_weekly_body.html.j2`
ar `.weekly-*` ink-navy chrome, mobile-first stat kartītēm un in-body movers
grafiku (`src/graphics/weekly_chart.py` — roku-rakstīts SVG). Featured image lieto
`WEEKLY_STYLE` rāmi. Validācija (`_validate_brief_structure`) atjaunota uz jauno
sekciju kontraktu (`## Nedēļas stāsts` + `## Nedēļas galvenās tēmas`).

**Kāpēc SVG, ne matplotlib:** matplotlib nav default venv (sk. conftest xfail
`test_visuals_chart`). **Kāpēc grafiks ārpus `brief_images`:** `get_approved_image()`
atgriež jaunāko approved rindu per note_id — otrs (grafika) attēls sajauktu
featured-image izvēli; tāpēc grafiks ir tīri DB-dati un neiet caur approval loop.
Spec/plāns: `docs/superpowers/{specs,plans}/2026-06-01-weekly-brief-redesign*`.

## Arhīvs (2026-04 — 2026-05)

Vecākie ieraksti pārcelti uz [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md) (2026-07-21; pilns saturs + visi enkuri tur). Zemāk enkuru-stubi ierakstiem, uz kuriem atsaucas `CLAUDE.md` / aģentu prompti — virsrakstu teksts saglabāts identisks, lai saites turpina strādāt.

## 2026-04-25 — Strukturālā sanācija: pub_at meta tag fix + Saeima vote-as-document anti-pattern noņemšana

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Strukturālā sanācija](CHANGELOG-arhivs.md#2026-04-25--strukturālā-sanācija-pub_at-meta-tag-fix--saeima-vote-as-document-anti-pattern-noņemšana)

## 2026-04-25 — Commentator demotion + profila X subtaba

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Commentator demotion](CHANGELOG-arhivs.md#2026-04-25--commentator-demotion--profila-x-subtaba)

## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § feed_type](CHANGELOG-arhivs.md#2026-04-23--social_accountsfeed_type-relay-vs-first_party)

## 2026-04-23 — Komentētāji (speaker_id on claims)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Komentētāji](CHANGELOG-arhivs.md#2026-04-23--komentētāji-speaker_id-on-claims)

## 2026-04-11 — claim_type split (`position` vs `saeima_vote`)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § claim_type split](CHANGELOG-arhivs.md#2026-04-11--claim_type-split-position-vs-saeima_vote)
