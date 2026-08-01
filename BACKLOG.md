# atmina — Atvērtais backlog

Atvērtie tehniskā parāda + iezīmētie darbi, kas nav vēl pabeigti. Pārcelts no privātās auto-atmiņas 2026-06-08, lai būtu versionēts + atrodams visiem (atmiņa = privāta, neredzama citiem). Pabeigtais darbs dzīvo `wiki/CHANGELOG.md`; šis fails ir TIKAI atvērtais.

> Statusa tagi: **[BLOKĒTS]** ārējs šķērslis · **[WIP]** sākts, nepabeigts · **[OPEN]** atvērts, cēlonis zināms, risinājums nav sākts · **[DEFERRED]** apzināti atlikts, zema prioritāte · **[OPERATOR]** gaida manuālu operatora darbību · **[FIX]** mazs konkrēts labojums.

> **Uzturēšana (2026-08-01):** kad ieraksts ir pabeigts, tas iet uz `wiki/CHANGELOG.md`, **ne** ar svītrojumu šeit — 2026-08-01 audits atrada 92 no 356 rindām (25 %) aizņemtas ar jau pabeigtu darbu, un divi ieraksti bija tikai šeit, tāpēc tos nedrīkstēja vienkārši izdzēst. Pirms griešanas pārbaudi, ka saturs tiešām ir CHANGELOG-ā.
>
> **Un pārbaudi apgalvojumu pret failu, pirms rīkojies.** 2026-08-01 auditā 23 no 29 ieteikumiem pazemināti recenzijā; grep skaitītājs mēdz melot (105 „neatbilstības" = īsais/pilnais nosaukums; 9 no 25 „defektiem" = paša testa artefakts). Skaitlis nav atradums, kamēr neesi izlasījis rindu.

> **Ienākšanas bars (2026-08-19):** jauns ieraksts drīkst šeit tikai ar (trigeris + rīcība + lēmumu īpašnieks). Novērojumi bez rīcības → `wiki/operations/`, ne šeit. Ieraksta formāts: problēma + lēmums + pointeris; izmeklēšanas naratīvs dzīvo `docs/audits/`, ne ierakstā. Vecos ierakstus nemigrējam (08-15 lēmums par slēgto pārcelšanu paliek spēkā). **`docs/audits/` ir VERSIONĒTS kopš 2026-08-22** — līdz tam mape bija gitignorēta (08-14) un šis līgums sūtīja pierādījumus uz vietu, ko `git clean` iznīcina; 3 no 8 citētajiem audita dokumentiem bija jau pazuduši. Publiskajā spogulī mape nenonāk (izslēgumu saraksts), tāpēc sekošana nemaina anonimitāti.

## Ne-darīt (izmeklēts un noraidīts — nepārvērtē bez jauna fakta)

Šī sadaļa ir **izņēmums** no augšējā kontrakta: tā ir pabeigta darba pieraksts, kas paliek šeit ar nolūku. Iemesls — 2026-08-01 repo audits pats saražoja 6 „atradumus", kas izrādījās jau apzināti izlemti; noraidījumi, kas nav pierakstīti vienuviet, tiek atklāti no jauna aptuveni reizi mēnesī.

- **Render / veiktspēja:** vietne pa vadu iet brotli-saspiesta (~16–27×) — bloat nav first-paint problēma, reālās izmaksas = disk/build/deploy svars + DOM. NE pre-compress HTML uz `.br`; NE `zinas`/`x` pagination; NE SQLite-WASM; NE Cloudflare-for-compression; NE incremental-build-system (visi noraidīti 2026-05-30 / 06-02 auditos).
- **`opponent_id` pārsaukšana** — noraidīta pragmatiski: kolonna dzīvo 6 pamattabulās, 363 vietās 37 `src` failos, 37 vietās aģentu promptos/workflow, testos, wiki un vēsturiskajos `data/rollback_*.sql` (kas pēc pārsaukšanas vairs nedarbotos); idempotences trijnieks CLAUDE.md nosaukts vārdā `(opponent_id, source_url, topic)`. Ieguvums tīri kosmētisks — neviens ārējs lietotājs vārdu neredz. Uzskatām par etimoloģiju (kā `politracker.db` → `atmina.db`).
- **`analyses` UPSERT** — NEIEVIEST. Izmērītās 938 dublētās grupas (1612 liekas rindas) ir rutīnas RĪTA un VAKARA viļņi ar atšķirīgām tēmām, nevis pārrakstīšanas; atslēgas-līmeņa UPSERT tās apēstu klusi. Pilnais izmeklējums: [CHANGELOG arhīvs § 2026-07-24 `analyses` dublētās rindas](wiki/CHANGELOG-arhivs.md#2026-07-24--analyses-dublētās-rindas--upsert-neieviest).
- **`p3_backfill_year_urllib.py --year 2025`** — nelietot robu aizpildīšanai: tas dedublē tikai pēc URL (`src/saeima/votes.py:413`), un pārarhivētie UNID nozīmē, ka akls gada palaidiens ražotu dublikātus. Sk. § Saeima.
- **Doc 77556 (Abu Meri), Delfi paywall doki 76622/76623 un doc 80931 (diena.lv Rinkēvičs) — NEIEVĀC atkārtoti.** Dzīvās lapas ekstraktējas baits pret baitu identiskas glabātajam (77556 = video anonss, 76622/76623 = paywall, 80931 = saturs tikai virsrakstā/slugā → title-scan (b6) arguments); turklāt `ingest_one()` uz esoša URL ir `already_present` no-op. Pieraksti: CHANGELOG arhīvs 2026-08-02, CHANGELOG 2026-08-06.
- **Auto-sintēzes aģents** — `wiki/synthesis/` lapas ir ar roku rakstītas (standing lēmums 2026-04-22).
- **Sentimenta analīze** — noņemta kā neuzticama; `sentiment=0.0` paliek tikai shēmas saderībai.
- **Vēstures dokumenti `docs/specs|plans`** ar politracker/kampaņas kontekstu paliek — tā ir dokumentēta arhitektūras vēsture.
- **UI ne-defekti:** gaišais default ar dark `:root` = apzināts (`c634c47`); abi `!important` izsekoti un pamatoti (`802c6e8`). Sk. § Profili / UI.
- **NEATJAUNO `AGENTS.md`** (dzēsts 2026-08-01, operatora lēmums): novecojis starpharness fails ir bīstamāks par neesamību — svešs harness to ielādē un neredz ne Standing Decisions, ne trapus (dzēšanas brīdī 8 verificētas pretrunas ar `CLAUDE.md`; [CHANGELOG arhīvs § 2026-08-01](wiki/CHANGELOG-arhivs.md)). Svešiem izpildītājiem: `CLAUDE.md` + [`portability.md`](wiki/operations/portability.md).
- **`audit_quote_fidelity.py` virsrakstu klases 38 atlikušie ieraksti** — NEtaisīt batch-fix un neauditēt atkārtoti. LV ziņu virsraksts bieži **IR** politiķa citāts („Es neesmu un nebūšu politiķis!"); 2026-07-25 triāža pārbaudīja visus 50, laboja 12, un 38 atzina par leģitīmiem. Rīks tos rādīs mūžīgi, jo tests ir tikai virsraksta sakritība ar citātu. Tas pats attiecas uz `not_subject` klasi (104 rindas) — paraugu kopums, ne defektu saraksts.
- **`store_claim()` idempotences apiešana — NEMEKLĒT, tādas nav bijis.** Snapshot `atmina.db.pre-vote-url-fix-20260427` pierāda: dublēto grupu trijnieki rakstīšanas brīdī atšķīrās (`topic` vēlāk sapludināja 06-12 migrācija `fix_motif_topic_coverage`), tātad dedup SELECT strādāja pareizi. Kontrakts #3 nav pārkāpts. Pilna metode: CHANGELOG arhīvs 2026-08-02.
- **`store_contradiction()` dublikātu izmeklēšana** — kodā tā tiešām ir kails `INSERT` bez dedupa, un tas izskatās pēc defekta. Dzīvajā DB **0 dublikātu no 30 rindām un 0 karājošos atsauču** (mērīts 2026-08-01). Reālas problēmas nav; nepārmērī bez jauna fakta.
- **JAUNA `x_handle` ↔ `social_accounts` pārbaude** — jau sedz `/audit-integrity` 2. pārbaude (2026-08-03: `checked=97 flagged=1`, Svirskis id=62). Palaid prasmi, nebūvē dublikātu.
- **`ensure_embeddings_live()` visos rakstošajos skriptos** — vārti ir apzināti šauri: tikai bulk ieejas punkti, KAS TIEŠĀM embedo. `ingest_url.py` un parity audits ir noraidīti pēc vārda (CHANGELOG 2026-07-25) — tur vārti būtu tikai lieks modeļa ielādes kavējums.
- **`audit_matcher_name_forms` mūžīgais karogs 'Ilja Ivanovs' — NAV datu robs, neko nepievieno.** (2026-08-04) Forma jau ir pid=92, visas 6437 balsojumu rindas piesaistītas, korpusā 0 tikai-ASCII doku; `match_politician` atgriež None priekšvārda veto dēļ ('Ilja' pret 'Iļja') bez reālas ekspozīcijas. Veto-pret-glabātu-formu maiņa = koda darbs ar eval vārtiem, tikai ja parādās īsta ekspozīcija.

- **2026-08-22 slop/bloat audita NORAIDĪTIE — septiņas klases, katra izmērīta.** Pilni skaitļi + vaicājumi: [`docs/audits/2026-08-22-slop-un-bloat-audits.md`](docs/audits/2026-08-22-slop-un-bloat-audits.md) § 3. Kopsavilkumā, lai nākamais audits tos neatvasina no jauna:
  - **Stance garuma / „virziena verba" vārti — NĒ.** Mediānas 2,2× pieaugums enkurojas 2026-03 (n=92 = 1,5 % korpusa); no maija 188→186→204→229, pēdējās 3 nedēļas LEJUP (252→228→218). Pieaugums IR divu 08-03/08-11 pret-fabrikācijas guardrail izmērītais iznākums — garuma bars daļēji atgrieztu 11 dienas vecu noteikumu. Garās rindas nes ~8 pārbaudāmus apgalvojumus, ne pildījumu. Atlikums = tipogrāfija (`templates/politician.html.j2:318` bez clamp) → `backlog/vietne-ui.md`.
  - **Git vēstures pārrakstīšana / `gc --aggressive` — NĒ.** 79,1 % blob diska jau nesasniedzams, UN 243 īsti commit heši tiek citēti kā pierādījums (846 hex kandidāti pārbaudīti ar `git cat-file -e`). Publiskais spogulis ir bezvēstures squash — 99 MB nekad neaiziet.
  - **„Nepieslēgto" skriptu arhivēšana — NĒ.** 14 no 41 ir nosaukti `data/rollback_*.sql` galvenēs (atsauču karte izlaida `data/`: 452 .sql, 315 rollback). Ieguvums 242 kB un **0 konteksta tokenu**.
  - **VAD momentuzņēmuma eksports+dzēšana — NĒ.** Kaskāde ir 505 rindas 10 tabulās (ne 495/9 — priekšlikuma paša vārti būtu sertificējuši trūkstošas 10 `vad_companies` rindas); 3 pilnas kopijas jau uz diska; brīvā vieta +0,8 %.
  - **`.gitignore` tīrīšana — NĒ.** 29 no 66 pozitīvajiem likumiem sakrīt ar 0 failiem, jo tie ir aizsargi; faila 35 negācijas likumi „kuri trāpīja" skenējumam ir strukturāli neredzami, tātad skenējums pats ir salūzuši vārti.
  - **`tests/fixtures/render_fixture_data.sql` (4 MB), `lid.176.ftz`, testu komplekta vai audita ritma griešana — NĒ.** Fixture nogalināja dzīvās-DB dreifa dzirnavas; 4 MB maksātu 147-SHA regenerāciju.
  - **`claim-extractor.md` saīsināšana vai kopīgs noteikumu fails `.claude/` — NĒ.** Precīzo dublikātu skenējums 17 promptos: 9 rindas, visas `<!-- model: opus -->` galvene = 1,1 % no 3983. `/dienas-rutina` promptu jau amortizē ar batčošanu.
  - Turpat § 6 ir **11 NEVERIFICĒTU kandidātu rinda** — tie nav pierādījumi; lielākais ir `logs` 163 MiB / 646 400 rindas ar apgalvotiem 0 lasītājiem (vajag vienu verifikācijas pāreju pirms jebkāda priekšlikuma).

- **`*_report()` dvīņi `audit_quote_fidelity.py`, `check_output.py` un `audit_saeima_agenda_parity.py` — NORAIDĪTI 2026-08-09.** `lint_lv_style_report()` formu tur uzspieda ārējs ierobežojums (aģentu prompti citē atgriešanas tipu); šiem trim tāda nav (0 Python importētāju). Dvīnis tikai tāpēc, lai testi nav jārediģē, = mirušo `wiki_lint` čeku forma. Ja paraksts jāmaina, maini un izlabo izsaukuma rindas.
- **Saucēji `headline`, `not_subject` un `paywall` klasēm `audit_quote_fidelity.py` — NORAIDĪTI 2026-08-09.** § Ne-darīt jau aizliedz rīkoties ar pirmajām divām pie JEBKURAS vērtības (38 un 104 rindas = paraugu kopumi, ne defektu saraksti), un `paywall` docstring pats to sauc par „ne defektu pašu par sevi". `headline: 16/792` dod tieši to pašu bezdarbību, ko `headline: 16`. Skaitlis, kas nevienā vērtībā nemaina rīcību, ir skaitlis tukšumā. Saucēji ir `paraphrase`, `paraphrase_mid` un `misattributed_title` — tikai tie baro lēmumu.
- **`lint_lv_style` 196 mantojuma `%` rindas — NEMIGRĒ.** Vārti paplašināti 2026-08-09 (tabulu šūnas + saucējs; sk. CHANGELOG), tāpēc jaunās rindas atbilst normai. Vēsturiskās 196 no 214 `position` rindām ar `%` bez atstarpes paliek zināma klase: pilna migrācija prasītu pāra rollback + re-embed 196 rindām un mainītu jau publicētus pārskatus tīri tipogrāfiskas normas dēļ, bet daļējs labojums būtu sliktāks par neko (nekonsekvence bez ieguvuma). Tas pats attiecas uz 5 defektiem, ko jaunie vārti atrada pārskatos #427/#435 — tie ir publicēti, tos nelabo retroaktīvi.
- **Sintēžu saites un wikilinki — abi SLĒGTI, nepārbaudi no jauna.** (a) Bezpaplašinājuma saites pārskatā #184 NAV 404 — serveris `.html` formu atrisina pats (abas formas 200, identiska lapa); allowlist ieraksti paliek, jo `check_output.py` staigā pa uzbūvēto koku. (b) Sintēzes wikilinki salaboti (`f3c6e10a`), klasi sargā `tests/test_synthesis_no_wikilinks.py`.
- **Citātu labojumam NEplāno renderu pēc noklusējuma.** `templates/politician.html.j2:527` renderē `c.quote` tikai komentāru blokā, tāpēc pirmās puses pozīcijas citāts profila lapā neparādās vispār; no 2026-08-03 divdesmit labotajām rindām publiskā virsmā nonāca viena. Pārbaudi virsmu, pirms plāno uz āru vērstu soli.
- **Pārskatu auditorijas balsu ne-defekti (2026-08-03).** `generate_weekly_brief()` auditorijas balsis JAU iekļauj (bloku diagramma tās izslēdz pareizi — Neitrāli rinda); tēmu top-3 pēc `salience`, Aktīvākie/starppartiju/Koalīcija-vs-Opozīcija un `_BRIEF_DAY_CLAIM_SQL` 7 dienu logs — visi apzināta uzvedība, nepārtaisi par defektu.
- **„Sakārtosim BACKLOG, pārceļot slēgto uz CHANGELOG" — NORAIDĪTS 2026-08-15, izmērīts.** Premisa ir, ka fails ir pilns ar pabeigtu darbu. Nav: pilnībā slēgtas ir **tikai 3 sadaļas = 15 rindas no 457 (3,3 %)**, un **29 no 32 statusa marķieru rindām TAJĀ PAŠĀ rindā nes arī atvērto daļu** — tās nevar pārcelt, nesagriežot ierakstu uz pusēm. Turklāt vērtīgākā daļa slēgtajos ierakstos ir konvencija („nepārtaisi šo par defektu"), kas tieši tur pasargā no atkārtotas izmeklēšanas. Konteksta ietaupījums 3,3 %, risks — zaudēt brīdinājumu.
- **`store_tension()` regex vārti partijas etiķetei aprakstā — NORAIDĪTI 2026-08-15.** Ideja: pārbaudīt, vai „Uzvārds (TAG)" sakrīt ar `tracked_politicians.party`. Raža: **1 nesakritība no 77 pārbaudāmiem pāriem** (196 spriedzēs), un tā viena bija T6 divdomība — novecojis `party` lauks, ne aplams apraksts. Tātad vārti noraidītu, iespējams, PAREIZU aprakstu. Pārējie `store_tension` ValueError balstās uz pārbaudāmiem faktiem (vai URL eksistē `documents`), ne uz prozas parsēšanu; šis būtu pirmais, kas mēģina saprast tekstu. Vienreizējo nesakritību atrada lasīšana, ne vārti.
- **Trešais skaitlis („K šodienas pārskatā") `@quality-reviewer` vaicājumā — NORAIDĪTS 2026-08-15.** Skelets ievelk TĀS DIENAS pozīcijas, tāpēc K ≈ N pēc uzbūves (mērīts: 9/9 sakrita). § Ne-darīt jau aizliedz saucējus, kas nevienā vērtībā nemaina rīcību (sk. `audit_quote_fidelity.py` ierakstu).
- **`wiki/dailies/` kā otrs versionēts pārskatu nesējs — NORAIDĪTS 2026-08-15.** Mape ir `.gitignore`-ā un `git ls-files` dod 0 — tā ir APZINĀTI izņemta no indeksa kā lokāla operatora virsma. Variants „dzēst mapi" apgāž to lēmumu; variants „ģenerēt no DB" pievienotu kodu, lai uzturētu apzināti lokālu melnrakstu. Mērījums: no 20 jaunākajiem 17 identiski DB versijai, 1 atšķiras, 2 failu nav — dreifs reāls, bet nesējs ir DB, un tas jau tā ir.

- **`nra.lv/neatkariga/intervijas/` doku atkārtota ievākšana — NORAIDĪTA 2026-08-16, izmērīta.** BACKLOG § Avoti gadu ilgi turēja «re-ingest kandidātu sarakstu» 78788 / 78789 / 87900. Zonde ar `ingest_url.py::_default_fetch` (tas pats httpx + trafilatura ceļš, ko lieto īstā ievākšana) pret dzīvajām lapām deva **delta +0 zīmes visiem trim** — 859/552/889 zīmes glabātas, 859/552/889 ekstraktētas, beigu teksts baits pret baitu identisks. Intervijas korpuss vienkārši NAV publiskajā HTML: lapa nes tikai anonsu («…saruna ar M. Kučinski»), tāpēc tā nav svaiguma vai skrāpēšanas robeža, ko pārlāde varētu aizvērt. **Blakus atradums, kas padara veco ieteikumu neizpildāmu jebkurā gadījumā:** `ingest_one()` uz esoša `source_url` atgriež `already_present` un nekad nefetčo (`scripts/ingest_url.py:138-144`) — rīkam, ko ieraksts nosauca, nav pārlādes režīma. Ja klase kādreiz tiešām jāatver, tas ir avota piekļuves (abonements/print), ne ingest jautājums. Tā pati forma kā doc 77556 / 76622 / 80931 ierakstam augstāk.

- **Apakšaģenta atsauce uz instrukciju, kuru orkestrators neredz, NAV pierādījums pārkāpumam.** Operators var rakstīt tieši apakšaģentam — noklusējums ir „operators rakstījis", ne „aģents izdomāja"; pajautā, nevis pieraksti. Aģenta pretpienākums: tiešu operatora ziņu citēt atskaitē. Gadījums un `f0853761` atsaukums: CHANGELOG arhīvs 2026-08-02.

_Zemāk — slēgtās sadaļas, kas 2026-08-19 tīrīšanā saspiestas līdz konvencijai (pilnie pieraksti nosauktajos CHANGELOG ierakstos)._

- **Meļņa pārrēķins bloku tabulās — PIEŅEMTS kā vēsturisks** (operatora verdikts 2026-08-17; CHANGELOG 2026-08-18 § BACKLOG apkope). 26 publicēto pārskatu bloku skaitļus NEpārrēķina: skaitli citē apkārtējā proza, un maiņa bez teksta pārrakstīšanas radītu iekšēju pretrunu.
- **`saeima_individual_votes.faction` NULL jaunākajās sēdēs NAV skrāpera defekts** (izmeklēts 2026-08-06, CHANGELOG): ST frakcija titania lapās beidz eksistēt ap 2026-04-16 (`src/saeima/votes.py:185-190`), pārējie NULL ir frakciju pametušie vai aizvietotāji bez frakcijas šūnas. **Konvencija:** par ex-ST deputātiem 2026. gada vasarā raksti „bijušie „Stabilitātei!" frakcijas deputāti", nekad „ST frakcija balsoja" — per-balsojuma frakcijas apgalvojums tur nav iespējams pēc konstrukcijas.
- **Institūcijas slots: runas akts šķir, ne persona** (slēgts 2026-08-12; noteikums `.claude/agents/claim-extractor.md` Step 3c, pieraksts CHANGELOG 2026-08-05). Iestādes paziņojums un amatpersonas izteikums amata lomā par savas iestādes jomu = institūcijas pozīcija; individuāla eksperta komentārs = tukšs doks. Datu pēda: `data/rollback_nbs_slots_lemums_2026-08-12.sql`.
- **DeepSeek claim ekstrakcijai der tikai ar orkestratora QA** (izmēģinājums 2026-08-10, CHANGELOG 2026-08-10 (1)): kļūdu klase ir semantiska — amata fabrikācija, verba stiprums pāri avotam, RT ar citātu kā first-party —, un `lint_lv_style` to neķer, tikai lasīšana pret avotu. Der read-only izpētei un masveida empty-stamping; `.claude/agents/` neuzraudzītajiem palaidieniem paliek Opus grīda.
- **`saeima_votes.result` bez `result_source='agenda_label'` NAV citējams kā avota vārds** (kolonna ieviesta 2026-08-18, CHANGELOG). Vēsturiskajām rindām izcelsme paliek NULL, izņemot 5 pārlūkā verificētās (`data/{fix,rollback}_result_source_seed_2026-08-18.sql`); retrospektīvs backfill prasītu katras darba kārtības lapas pāršķiršanu, un helperis (`extract_agenda_result_labels()`) tam jau eksistē.
- **`@Krisjanis_K` NAV Kļaviņa konts** (operatora zināšana 2026-08-17, CHANGELOG 2026-08-18): anonīms konts ar nezināmu piederību — neko nepievieno.
- **Vītola (pid=64) `relationship_type='neutral'` — NEKO NEMAINĪT** (operatora gala verdikts 2026-08-17, CHANGELOG 2026-08-18): viņš ir finanšu ministra biroja ekonomists, ne politiķis, tāpēc AS etiķeti nelikt; AS saikne paliek redzama datu līmenī (#20376).
- **Matīss Žuravļevs (pid=187) `feed_type` nav defekts** (pārmērīts 2026-08-16; labojums CHANGELOG 2026-08-05): konts ir `first_party`, un no 19 `relay` kontiem neviens nepieder īstam politiķim — visi ir mediji, raidījumi vai handle-tipa sloti, t.i. tieši tas, kam `relay` domāts. Vaicājums: `SELECT sa.feed_type, sa.handle, tp.name FROM social_accounts sa JOIN tracked_politicians tp ON tp.id=sa.opponent_id WHERE sa.feed_type='relay'`.
- **Latkovska (pid=114) `role` ir PAREIZA** (T6 batch-verifikācija 2026-08-18, CHANGELOG): „Nacionālās drošības komisijas priekšsēdētājs" apstiprināts diviem neatkarīgiem avotiem; avota titrs par Aizsardzības, iekšlietu un korupcijas novēršanas komisiju ir otrs patiess fakts (viņš tur ir deputāts), ne pretruna.
- **CSP ārējo hostu allowlist vārti JAU IR** — `tests/test_csp_external_hosts.py` (2026-08-09; saucēja segums paplašināts 2026-08-15, abi CHANGELOG). Allowlists tiek parsēts no `assets/htaccess.template` kā vienīgā patiesības avota. Nebūvē dublikātu.
- **Partiju wiki `claims:` lauku NEpārsauc.** Programmas solījumiem kopš 2026-08-18 ir atsevišķs `program_promises:` lauks (CHANGELOG), tāpēc `claims:` nozīmē tikai pozīcijas, kā paredzēts. Pārsaukšana skartu `.base` failus, kas vaicā pēc lauka vārda.
- **Deploy publish-gate v2 ir pilnīgs — nepiedāvā jaunus vārtus** (2026-08-18, CHANGELOG; kontrakts CLAUDE.md T15): attēls UN eksplicīta `publish_approvals` rinda pēc lapas sluga, tāpēc pirms katra pārskata deploy jāizpilda `scripts/approve_publish.py <slug>`. Zināms troksnis, ne defekts: `check.sh` publish-gate paternus nesauc, tāpēc allowlist dzīvīguma ziņojumā tie vienmēr rāda „BEZ TRĀPĪJUMA".

## Operatora verdikti 2026-08-17 — izpildes rinda nākamajām sesijām

Operators 2026-08-17 vakarā atbildēja uz 46 lēmumu sarakstu, kas kompilēts no šī faila. **Attīrīts 2026-08-18:** rindas 5 izpildes viļņi + 3 sīkie verdikti izpildīti, izpildītās rindas izgrieztas (pieraksts CHANGELOG 2026-08-18; atvērtie atlikumi pārcelti uz avota sadaļām). Šeit paliek TIKAI neizpildītais. Katram datu labojumam pāra rollback ar unikālu scope sufiksu; `stance`/`topic` maiņai obligāts `reembed_claims.py`. Kad ieraksts izpildīts → pieraksts CHANGELOG + verdikta rindas dzēšana šeit un statusa atjaunošana avota sadaļā.

**Saeima:**
- ~~id 6954 → **ievākt trūkstošo otro balsojumu** (12:11:18) un tam `Pieņemts`~~ **SLĒGTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): otrais balsojums jau korpusā kā id 333 (`Pieņemts`, 92 iv + 92 claims) kopš 05-27 — premisa «korpusā nav» nepareiza; seedots tikai `result_source='agenda_label'` + audita alias paplašinājums (`Likums`/`Paziņojums`).
- ~~vote_id 3438 `summary` → **pārbaudīt pret titania un labot**~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): inversija apstiprināta ar stenogrammu — likumprojekts paredzēja SAMAZINĀT akcīzi; kopsavilkums labots ar pāra rollback, claims neskaroti.
- Māsas `summary` klases (b) konvencijas dokumentēšana pie stance ģenerēšanas + Step 3.5 labojums jauniem (§ Māsas balsojumu — klases lēmums tur).

**Matcher / seeding (paterni caur `eval_matcher_collisions.py` vārtiem FP≤3, zelts≥1260):**
- ~~NBS/Slaidiņš → **SĒT Slaidiņu kā atsevišķu entītiju**~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (9)): pid=245, `neutral`, party=NULL; vārti fp_links=1/gold=1557. Vēsturisko doku rescan NAV palaists (atsevišķs lēmums).
- ~~**Rasimas (id=151) X seeding**~~ **IZPILDĪTS 2026-08-21**: x_handle + social_accounts `leilarasima` (first_party; LSM saraksts + Threads bio verifikācija). **Meļņa kailā "Melnis"/"Meļņa" klase (doc 89013):** LSM tekstos aizsardzības ministrs ir TIKAI kails "Melnis" (pieder id=157) — virkņu līmenī neatrisināma kā Bērziņa dziedātājs; kandidāts ir konteksta kolokācija ("aizsardzības ministr…" tuvums), operatora lēmums.

**Claims labojumi:**
- ~~#555726 Valainis → **pieņemt citēšanas piezīmi**~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): brīdinājums (MK protokols Nr. 40 nepiešķir 14 milj.) ierakstīts `reasoning` ar pāra rollback.
- ~~#689539 Šnores `quote` → **bagātināt** no tvīta~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): quote aizpildīts burtiski ar paša tvīta tekstu (doc 86486) + provenance piezīme reasoning; pāra rollback.

**Rutīnas karogi (2026-08-17/18):**
- **[OPERATOR] #689743 (Sprūds) atsaukšanas kandidāts** — atkārto 3–5 dienas vecu pozīciju, izslīdēja caur ±2 dienu logu.
- ~~Rutīnas eksperimentu institucionalizācija~~ **IZPILDĪTS 2026-08-20** (CHANGELOG): ±5 d dublikātu logs `claim-extractor.md` Step 4 + abi soļi `dienas-rutina` 2. solī (junction-atgūšana ar plašā vaicājuma piezīmi).
- **[OPERATOR] #689736 `reasoning` pārrakstīšanās** (nav publiska) un #689752/#689753 Siliņas daļējais pārklājums — sīkumi no rutīnas atskaites, per-rindas lēmumi.
- ~~2026-08-19 rutīnas jaunie karogi~~ **VISI SLĒGTI 2026-08-20** (CHANGELOG): (a) doc 90310↔LVM junction dzēsts (`data/{fix,rollback}_doc90310_lvm_junction_2026-08-20.sql`; `negative_patterns` apzināti NAV — viens gadījums, ne paterns); (b)/(c)/(e) izpildīti (roster, #690438+#473, #690442→nra); (d) → pastāvīgs ieraksts `backlog/saeima.md` § Komisiju balsojumu ievilkšana.

**Atsevišķas sesijas (ne dienas rindā):**
- Citātu triāža → **forma APSTIPRINĀTA** (operators 08-17): VIENA atsevišķa sesija, apvienojot `paraphrase_mid` 13 rindas + 179 termināļa pieturzīmes + 37 vājos + 615955/80022 pārskrāpējumu. Rindu-pa-rindai (nekad batch), kārtot pēc `confidence` × publiskās ekspozīcijas, grupēt pa dokumentiem, katram labojumam avota salīdzinājums.
- LETA URL 17 title≠content kandidātu triāža (§ LETA URL satura nomaiņa).
- ~~Partiju pretrunu DA palaidiens top ~30 (§ Partiju pretrunas — piltuve).~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (10)): 30/30 KILL, 0 izdzīvojušo; verdikti [`docs/eval/party_funnel_da_verdicti_2026-08-21.md`](docs/eval/party_funnel_da_verdicti_2026-08-21.md).

**Infra / vietne:**
- ~~`brief_images` ceļu normalizācija + `approved` domēna dokumentēšana `src/schema.sql`~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (7)): 11/280 rindas normalizētas ar pāra rollback; DDL + domēns dokumentēti schema.sql; 4 rakstītāju skripti laboti.
- ~~VAD parsera robi / live pārbaude / pid=146 `vad_uuid` deny-saraksts~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (5)): live TĪRA — deploy nevajadzīgs; deny-list ieslēgta. Atlikums: parsera-robi FIX + re-JOIN paliek atvērts [`backlog/vad.md`](backlog/vad.md) § NVO maksājumi.
- Video kandidāti (Kola LTV, Briškena airBaltic) → **palaist `@video-extractor`** (verdikts 08-17: darīt 08-18).
- X `timeline` fallback → **(a) pārplānot `search`**, kad pūls atveseļojas (pūls izmērīts vesels 08-04; § Avoti X pieminējumu).

## Atvērto darbu indekss

_Detalizētie ieraksti dzīvo tēmas failos `backlog/*.md` (sadale 2026-08-19). Pirms darba tēmā izlasi attiecīgo failu. „§ <Sadaļa>" atsauces no citiem dokumentiem rezolvējas caur šo indeksu._

**[`backlog/saeima.md`](backlog/saeima.md)** — 7 ieraksti:
- **[DAĻĒJI SLĒGTS 2026-08-17]** 562 `saeima_votes.result` vērtības nāca no backfill fallback, ne no avota
- **[DAĻĒJI SLĒGTS 2026-08-19]** Agenda↔DB parity: 10 sēdes noauditētas; 2024-07-25 sēdē 9 balsojumi trūkst DB
- **[OPEN]** `/audit-integrity` 9. pārbaude nesedz neievēlētos ministrus — T6 aklā zona (atklāts 2026-08-07)
- **[OPERATOR→dokumentēšana]** Māsas balsojumu kopīgais `summary` uzliek 1. lasījuma iznākumu 246 priekšlikumu balsojumiem (~20k claims)
- **[SLĒGTS 2026-08-21]** Partiju pretrunas — piltuves (i) rangs IEVIESTS 2026-08-18; (ii) DA palaidiens izpildīts: 30/30 KILL (verdikti `docs/eval/party_funnel_da_verdicti_2026-08-21.md`). Nākamais cikls (jauns rangs) — tikai pēc operatora lēmuma.
- **[DEFERRED]** Priekšlikumu (amendment) balsojumu pipeline
- **[OPEN]** Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

**[`backlog/agenti-pipeline.md`](backlog/agenti-pipeline.md)** — 12 ieraksti:
- **[FIX]** Partija ≠ frakcija — paliek tikai (c) UI formulējums
- **[OPEN]** Stance-fidelity atlikums: matcher neskenē `title`, paywall stop-gate, viena notikuma dublēšanās
- **[OPEN]** Krists Avots kā premjera balss — atribūcijas lēmums
- **[OPEN]** Medību pēdas @contradiction-hunter (07-25 adversārā pārbaude + 08-03 ekstrakcija)
- **[SLĒGTS 2026-08-19]** fasttext lid-modeļa nepieejamība → LV-diacritics vārti vaļā
- **[FIX]** Idempotences kluso merge — vairāki distinkti claims no viena (pid, url, topic)
- **[FIX]** Partijas piederības maiņa ziņās nesinhronizējas ar tracked_politicians.party
- **[OPEN]** Konteksta blokos nosaukti audience runātāji bez avota saites
- **[OPEN]** Tendenču piezīmēs kaili claim ID (`#NNNNNN`)
- **[OPEN]** NBS amata-apzīmējuma klase: amats kā `name_form` trāpījums, viens un tas pats runātājs
- **[FIX]** Divi mazāki matcher/konfigurācijas robi (2026-08-02)
- **[OPEN]** Ārpolitikas tēmas confidence drift +0,18 — neizmeklēts

**[`backlog/matcher.md`](backlog/matcher.md)** — 11 ieraksti:
- **[OPEN]** Junction abu virzienu izmeklēšana: fantoma `mentioned` bez vārda tekstā UN pilnvārds tekstā bez junction
- **[OPEN]** T1 locījumu kolīziju klase (2026-08 gadījumi)
- **[OPEN]** 2026-08-15 rutīnas matcher atradumi — sugasvārda kolīzija, RSS sānjosla, nereģistrēts handle
- **[OPEN]** 2026-08-16 rutīnas matcher atradumi — trīs kolīzijas, viena atkārtojoša
- **[OPEN]** Ārvalstu revīzijas iestādes sasaistās ar Valsts kontroli (id=241)
- **[OPEN]** Bērziņš false-link — monitorings, ne kampaņa
- **[OPEN]** NBS pid=204 keyword subject-leakage uz CVK programmu dokiem — partiju programmu darba palieka
- **[OPEN]** Deep-check 2026-08-17 blakus atradumi — 9 claim/datu karogi
- **[OPEN]** Junction lomas apgrieztas LETA pārstāstos — `mentioned` runātājs nekad nenonāk ekstrakcijas rindā
- **[OPEN]** Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts
- **[OPERATOR]** `NEEDS_REVIEW` rinda: paliek 6 kodola lēmumi (+ dienas jaunie karogi)

**[`backlog/dati-db.md`](backlog/dati-db.md)** — 10 ieraksti:
- **[OPERATOR]** 2026-08-13/14 rutīnas atlikumi — nebloķējoši, katrs savs lēmums
- **[OPERATOR]** Citātu integritātes atlikums — klases (a)–(e)
- **[OPERATOR]** LETA URL satura nomaiņa pēc izvērtēšanas — doc 72446 title≠content, claim #553929 bez sava pierādījuma (202…
- **[OPERATOR]** Deep-check 1. viļņa datu defekti — apgrieztas stances, aplams publicētas pretrunas datējums, name_forms rob…
- **[FIX]** `review_status` trigera substring-kolīzijas — abi virzieni novēroti vienā dienā (2026-08-05)
- **[FIX]** Denormalizēto lauku novecojumu partija (2026-08-05 rutīnas atradumi)
- **[OPERATOR]** 2026-08-15 rutīnas datu defekti — viena apgriezta stance, divi `role` lauki
- **[DEFERRED]** "Aizsardzības industrija" topika splits
- **[FIX]** Timestamp glabāšana nav standartizēta (mixed LV/UTC) — pusnakts-pārkares artefaktu saime
- **[DEFERRED]** `claim_vectors` bāreņi — 7 004 vektori bez `claims` rindas; claims bez vektora 0

**[`backlog/avoti.md`](backlog/avoti.md)** — 6 ieraksti:
- **[OPEN]** X pieminējumu `timeline` fallback = diena bez publiskās sarunas seguma
- **[OPEN]** Vēsturisko dokumentu backlogi atsevišķai sweep sesijai
- **[OPEN]** lsm/diena/tvnet truncated doku backfill kampaņa gaida lsm soft-404 sargu
- **[BLOKĒTS]** pietiek.com
- **[OPEN]** Novērošanā (bez aktīvas darbības)
- **[OPEN]** Diarizācija uz crosstalk — per-segment satura sanity-check pirms labelled_transcript (2026-07-22)

**[`backlog/vad.md`](backlog/vad.md)** — 2 ieraksti:
- **[SLĒGTS 2026-08-21]** VAD homonīmu kontaminācija 6 politiķiem — DB tīrīta 08-12, live verificēts 08-21, pid=146 deny-list ieslēgta
- **[DAĻĒJI SLĒGTS 2026-08-21]** NVO maksājumi × VAD deklarācijas — parsera robi aizvērti + re-JOIN (+24 pāras); paliek operatora triāža

**[`backlog/vietne-ui.md`](backlog/vietne-ui.md)** — 6 ieraksti:
- **[FIX]** `brief_images` divi metadatu defekti (2026-08-04 kvalitātes pārbaude)
- **[DEFERRED]** Render self-join lēnās stadijas
- **[DEFERRED]** balsojumi.html Step 3
- **[DEFERRED]** 2026-07-23 drošības audita apzināti pieņemtās paliekas
- **[OPEN]** UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
- **[OPEN]** Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3

**[`backlog/repo-higiena.md`](backlog/repo-higiena.md)** — 7 ieraksti:
- **[OPERATOR]** Repo tīrīšana — IZPILDĪTS 2026-08-14 (CHANGELOG); paliek 3 atvērti lēmumi
- **[OPEN]** Vārtu saucēju audits 2026-08-09 — 3 apstiprināti atlikumi + 18 neverificēti kandidāti
- **[OPERATOR]** `paraphrase_mid` — 13 rindas virs 0,85, ko vecais likums neredzēja
- **[OPEN]** Commit autora identitāte — turpmākie commiti nokārtoti, vēsture paliek
- **[FIX]** 418 web dokumenti no `ingest_url.py` ir bez chunkiem — semantiskajā meklēšanā tie neeksistē
- **[OPEN]** `src/csp/` sync bez ieejas punkta — operators izlēmis PIESLĒGT (2026-08-15)
- **[FIX]** `brief_images` ceļu konvencijas + nedokumentēts `approved=2`
