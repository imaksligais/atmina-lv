# atmina — Atvērtais backlog

Atvērtie tehniskā parāda + iezīmētie darbi, kas nav vēl pabeigti. Pārcelts no privātās auto-atmiņas 2026-06-08, lai būtu versionēts + atrodams visiem (atmiņa = privāta, neredzama citiem). Pabeigtais darbs dzīvo `wiki/CHANGELOG.md`; šis fails ir TIKAI atvērtais.

> Statusa tagi: **[BLOKĒTS]** ārējs šķērslis · **[WIP]** sākts, nepabeigts · **[OPEN]** atvērts, cēlonis zināms, risinājums nav sākts · **[DEFERRED]** apzināti atlikts, zema prioritāte · **[OPERATOR]** gaida manuālu operatora darbību · **[FIX]** mazs konkrēts labojums.

> **Uzturēšana (2026-08-01):** kad ieraksts ir pabeigts, tas iet uz `wiki/CHANGELOG.md`, **ne** ar svītrojumu šeit — 2026-08-01 audits atrada 92 no 356 rindām (25 %) aizņemtas ar jau pabeigtu darbu, un divi ieraksti bija tikai šeit, tāpēc tos nedrīkstēja vienkārši izdzēst. Pirms griešanas pārbaudi, ka saturs tiešām ir CHANGELOG-ā.
>
> **Un pārbaudi apgalvojumu pret failu, pirms rīkojies.** 2026-08-01 auditā 23 no 29 ieteikumiem pazemināti recenzijā; grep skaitītājs mēdz melot (105 „neatbilstības" = īsais/pilnais nosaukums; 9 no 25 „defektiem" = paša testa artefakts). Skaitlis nav atradums, kamēr neesi izlasījis rindu.

> **Ienākšanas bars (2026-08-19):** jauns ieraksts drīkst šeit tikai ar (trigeris + rīcība + lēmumu īpašnieks). Novērojumi bez rīcības → `wiki/operations/`, ne šeit. Ieraksta formāts: problēma + lēmums + pointeris; izmeklēšanas naratīvs dzīvo `docs/audits/`, ne ierakstā. Vecos ierakstus nemigrējam (08-15 lēmums par slēgto pārcelšanu paliek spēkā). **`docs/audits/` ir VERSIONĒTS kopš 2026-08-22** — līdz tam mape bija gitignorēta (08-14) un šis līgums sūtīja pierādījumus uz vietu, ko `git clean` iznīcina; 3 no 8 citētajiem audita dokumentiem bija jau pazuduši. Publiskajā spogulī mape nenonāk (izslēgumu saraksts), tāpēc sekošana nemaina anonimitāti.

> **Izaugsmes mērījums (2026-08-27).** Pēc 08-19 sadalīšanas fails bija 28,7 KB; nedēļu vēlāk 39,9 KB (**+39 %**). Sadalījums pa sadaļām (`git show bc52c358:BACKLOG.md` pret HEAD): § Ne-darīt **+4 868 B**, § Atvērto darbu indekss **+2 819 B**, § Operatora verdikti **+2 619 B**, galvene +305 B. **Divas no trim lielākajām aug pēc līguma:** § Ne-darīt ir apzināts izņēmums (pabeigta darba pieraksts, kas paliek), un indekss aug mehāniski līdz ar `backlog/*.md` ierakstiem — to sargā `tests/test_backlog_index_sync.py`. Tātad vienīgā sadaļa, kuras pieaugums ir īsts drifts, ir **verdiktu rinda: tā nedrenējas**. Pirms nākamās sadalīšanas mēri šo pašu griezumu — «fails aug» bez sadaļu sadalījuma noved pie tā, ka griež to, kas aug pēc līguma.

> **Attīrīts 2026-09-07, ar saucēju.** Pēc 2026-09-06 verdiktu izpildes (52 lēmumi, CHANGELOG `## 2026-09-07 (1)`–`(9)`) § Operatora verdikti 2026-08-17 saspiesta uz § Atliktais pēc 2026-09-06 verdiktiem — palika tikai atliktais un sagatavotais. Tēmu failos **izgriezti 11 ieraksti** (saeima 2, agenti-pipeline 3, matcher 2, dati-db 2, avoti 1, vietne-ui 1), **pārrakstīti 13** uz to daļu, kas tiešām palika atvērta, un **pievienoti 2 jauni** (`matcher.md`: konteksta kolokācijas dizains; 2026-09-07 seedēšanas un junction blakuskarogi). Ieraksti kopā **77 → 67**; `BACKLOG.md` + `backlog/*.md` **1 024 → 865 rindas (−15,5 %)**, 191 348 → 168 007 B (**−12,2 %**; `wc -l -c BACKLOG.md backlog/*.md` pirms un pēc). Tieši tā sadaļa, ko 08-27 mērījums nosauca par vienīgo īsto driftu («verdiktu rinda nedrenējas»), šoreiz nodrenēja. **Katras izgriešanas priekšnosacījums bija CHANGELOG pēda**, pārbaudīta ar grep pēc claim id vai atslēgvārda; kur pēdas nebija (piem. #704032 noraidījums), ieraksts nevis izdzēsts, bet pārcelts uz § Ne-darīt.

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

- **Pavediena attēlus git kokā NEGLABĀ — operatora lēmums 2026-08-27.** Mērījums, kas jautājumu uzdeva: `git ls-files | grep 'thread.*\.png'` → **0**; neviens pavediena attēls nekad nav bijis izsekots, jo `output/` ir gitignorēts (`.gitignore:108`). Zudums ir apzināts: ģenerēšana caur `src.graphics.cli thread` NAV deterministiska, tāpēc izsekotais promptu JSON (`docs/tweet_bank/{DATE}-thread-prompts.json`) attēlu **neatjauno** — tas saglabā nodomu, ne rezultātu. Publicētais attēls dzīvo platformā, kur tas postēts; lokālā kopija ir vienreizējs artefakts. Ieguvums no komitēšanas (~10 MB mēnesī repo svarā) nav samērīgs ar to, ka atkārtoti postēt to pašu attēlu praksē nevajag. **Neatver no jauna bez jauna fakta** — jauns fakts būtu, piemēram, prasība pārpublicēt vecu pavedienu identiski.
  - **Izņēmums, kas NAV pretruna: deterministiskiem ģeneratoriem kods iet kokā.** `scripts/oneoff-content/make_k2_timeline.py` (PIL hronoloģija) ir izsekots tieši tāpēc, ka tas attēlu atražo baitu precīzi — tur ģenerators ir pilnvērtīga attēla vietniece. Robeža ir determinisms, ne faila tips: AI ģenerēts attēls → prompts kokā, attēls ne; skripta zīmēts attēls → skripts kokā, attēls ne.

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
  - **Otrā instance 2026-08-27, un tā ir CITA forma — bet lēmumu neatver.** Rutīnā orkestrators pats uzrakstīja spriedzē #246 «Andris Kulbergs (LPV)», kaut `party='Apvienotais saraksts'` un `saeima_individual_votes.faction='AS'` **1322 no 1322** balsojumiem kopš 2025-09-01; blakus spriedze #244 to pašu personu raksta pareizi. Atrada `@brief-writer`, salīdzinot ar tabulas «Avots» aili — atkal lasīšana, ne vārti. Kāpēc tas NEATSPĒKO 08-15 noraidījumu: toreizējā vienīgā nesakritība bija T6 divdomība (novecojis `party`), tāpēc vārti būtu noraidījuši, iespējams, PAREIZU aprakstu; šeit lauks ir viennozīmīgs, tātad vārti būtu trāpījuši. Divas instances ar pretējām formām nav pietiekams saucējs, lai mainītu lēmumu — bet, ja parādās trešā viennozīmīgā, tas ir jauns fakts. Pēda: `data/{fix,rollback}_tension246_party_label_2026-08-27.sql`.
- **Trešais skaitlis („K šodienas pārskatā") `@quality-reviewer` vaicājumā — NORAIDĪTS 2026-08-15.** Skelets ievelk TĀS DIENAS pozīcijas, tāpēc K ≈ N pēc uzbūves (mērīts: 9/9 sakrita). § Ne-darīt jau aizliedz saucējus, kas nevienā vērtībā nemaina rīcību (sk. `audit_quote_fidelity.py` ierakstu).
- **`wiki/dailies/` kā otrs versionēts pārskatu nesējs — NORAIDĪTS 2026-08-15.** Mape ir `.gitignore`-ā un `git ls-files` dod 0 — tā ir APZINĀTI izņemta no indeksa kā lokāla operatora virsma. Variants „dzēst mapi" apgāž to lēmumu; variants „ģenerēt no DB" pievienotu kodu, lai uzturētu apzināti lokālu melnrakstu. Mērījums: no 20 jaunākajiem 17 identiski DB versijai, 1 atšķiras, 2 failu nav — dreifs reāls, bet nesējs ir DB, un tas jau tā ir.

- **`nra.lv/neatkariga/intervijas/` doku atkārtota ievākšana — NORAIDĪTA 2026-08-16, izmērīta.** BACKLOG § Avoti gadu ilgi turēja «re-ingest kandidātu sarakstu» 78788 / 78789 / 87900. Zonde ar `ingest_url.py::_default_fetch` (tas pats httpx + trafilatura ceļš, ko lieto īstā ievākšana) pret dzīvajām lapām deva **delta +0 zīmes visiem trim** — 859/552/889 zīmes glabātas, 859/552/889 ekstraktētas, beigu teksts baits pret baitu identisks. Intervijas korpuss vienkārši NAV publiskajā HTML: lapa nes tikai anonsu («…saruna ar M. Kučinski»), tāpēc tā nav svaiguma vai skrāpēšanas robeža, ko pārlāde varētu aizvērt. **Blakus atradums, kas padara veco ieteikumu neizpildāmu jebkurā gadījumā:** `ingest_one()` uz esoša `source_url` atgriež `already_present` un nekad nefetčo (`scripts/ingest_url.py:138-144`) — rīkam, ko ieraksts nosauca, nav pārlādes režīma. Ja klase kādreiz tiešām jāatver, tas ir avota piekļuves (abonements/print), ne ingest jautājums. Tā pati forma kā doc 77556 / 76622 / 80931 ierakstam augstāk.

- **pid=27 (Bordāns) `x_handle IS NULL` ir APZINĀTS — nekaro un neaizpildi.** (Verdikts 2026-08-25, ar ko klase slēdzas.) `relationship_type='inactive'`, un renderētajā kokā viņa profila lapas nav vispār (196 lapas, `bordans` nav starp tām), tāpēc aizpildīšana no `social_accounts.handle` nemainītu nevienu publisku virsmu. `/audit-integrity` 2. pārbaudes jaunā bāzlīnija ir `111 | 1 | 1`, un tas `1` NULL zarā ir tieši šī rinda; `0` tur nozīmētu, ka kāds to «salaboja». Otrs `1` (vērtību nesakritība) paliek pid=62 Svirskis — sk. nākamo punktu.
- **pid=62 (Svirskis) DIVAS `social_accounts` rindas ir APZINĀTAS — nedeaktivē `realNepareizais`.** (2026-07-16 operatora lēmums, CHANGELOG arhīvs; atkārtoti apstiprināts 2026-09-07, CHANGELOG 2026-09-07 (2) — verdikta 19. rinda slēgta pa «apstiprināt» zaru.) Šis ir turpinājums, kas iepriekšējā punktā bija apsolīts ar «sk. zemāk» un nekad nebija uzrakstīts. Trīs iemesli, katrs pietiekams: (a) 2026-07-16 lēmums abas rindas jau atzina par leģitīmām; (b) `/audit-integrity` 2. pārbaudes (c) zars **nefiltrē pēc `active`**, tāpēc `active=0` karogu nemaz nenoņemtu — pārbaude pēc konstrukcijas karo ikvienu politiķi ar >1 X kontu, tātad tas ir struktūras, ne datu defekts; (c) `src/social.py` fetch filtrē `active = TRUE`, tāpēc deaktivēšana apturētu **dzīvu kanālu** (1 689 doki 2026-04-01…09-05; satura pārklāšanās ar `@ESvirskis` pēc `content_hash` = **0**). Bāzlīnija `111 | 1 | 1` paliek pareiza abās pusēs — tāpat kā pid=27 Bordāns, šis `1` ir dokumentēts izņēmums, ne darbs.
- **#704032 (Kozlovskis) `stated_at` — NORAIDĪTS 2026-08-26, defekta nav.** Mednieks to uzrādīja, `@devils-advocate` pārbaudīja pret avotu: doc 93463 (LSM 08-23 retrospektīva «Galvas ripoja lēnām») citē agrāku izteikumu ar formulējumu «otrdienas rītā», un otrdiena bija 18. augusts — `stated_at='2026-08-18'` ir PAREIZS. Nekādu labojumu, rollback vai UPDATE. Nākamā sesija lai to neatver no jauna.
- **GKR `parties.coalition_status='not_in_saeima'` NAV novecojis — NEMAINI to uz `coalition`/`opposition`.** (Izmērīts 2026-08-25.) Karogs radās no pareiza novērojuma ar nepareizu secinājumu: Burovam (pid=74) tiešām ir 7250 balsojumi ar pēdējo 2026-08-20, tātad viņš Saeimā sēž. Bet lauks apraksta PARTIJU, ne deputātu, un `saeima_individual_votes.faction` viņam ir **NULL visos 2359 pēdējā gada balsojumos** — GKR frakcijas Saeimā nav (T6 korolārijs: partija ≠ frakcija; tā pati leģitīmā Kiršteina klase). Kods šo gadījumu jau pazīst pēc vārda: `src/briefs.py:546` komentārs nosauc tieši Burovu/GKR, un bloka etiķete 2026-07-22 pārsaukta no „Ārpus Saeimas" uz **„Bez Saeimas frakcijas"** tieši tāpēc, ka vecais nosaukums lasītājam meloja. Paliek tikai enum vārda neveiklība (`not_in_saeima` nozīmē „bez frakcijas"), un pārsaukšana skartu `src/coalition.py`, `src/briefs.py`, `src/render/{personas,votes,_common}.py` — nav vērts. Vaicājums, kas šo aizver: `SELECT iv.faction, COUNT(*) FROM saeima_individual_votes iv JOIN saeima_votes v ON v.id=iv.vote_id WHERE iv.politician_id=74 AND v.vote_date>='2025-09-01' GROUP BY 1`.
- **Biroja balss (padomnieks, sekretārs, preses dienests) nav amatpersonas pozīcija — konvencija uzrakstīta, nepārvērtē.** (Operatora lēmums 2026-08-05 + konvencija 2026-08-25.) Sedz abas formas: darbinieks runā savā vārdā (Krists Avots NTSP, doki 76582/76588/76600) UN darbinieks nodod amatpersonas viedokli („Kulbergs konceptuāli uzskata…, atzina padomniece" — #703861, doc 91814). Noklusējums `empty_doc_ids`; izņēmums tikai tad, ja tā pati pozīcija ±5 dienu logā ir amatpersonas pašas vārdos — tad glabā TO avotu (#703938 pret #703861). Pilnais teksts: `.claude/agents/claim-extractor.md` Step 3c § Biroja balss. `speaker_id` nav risinājums (commentary ceļš deprecated 2026-04-25). Biroja darbinieka sēšana kā atsevišķas entītijas paliek kandidāts **tikai tad, ja paterns kļūst regulārs** — tas ir 2026-08-05 lēmuma (b) variants, ne jauns priekšlikums.
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

## Atliktais pēc 2026-09-06 verdiktiem

Šī sadaļa aizstāj bijušo § Operatora verdikti 2026-08-17 — izpildes rindu. **2026-09-07 tika izpildīti 2026-09-06 operatora verdikti (52 lēmumi):** pilns saraksts ar per-rindas statusu — [`docs/verdikti-2026-09-06.md`](docs/verdikti-2026-09-06.md), izpildes pēdas — `wiki/CHANGELOG.md` ieraksti `## 2026-09-07 (1)`–`(9)`. Ar to pārgāja CHANGELOG-ā arī visas 08-17 verdiktu rindas, kas te vēl stāvēja: māsas `summary` dokumentēšana (23), Meļņa kailā formas klase (30, datu daļa), #689743 atsaukšana (1), 08-26/08-27 rutīnas karogi (2–10, 20–22, 27, 35), X pūla pārmērījums (48).

**Šeit paliek TIKAI tas, kas pēc 09-07 ir atvērts.** Katram datu labojumam pāra rollback ar unikālu scope sufiksu; `stance`/`topic` maiņai obligāts `reembed_claims.py`.

**Atlikts pēc paša verdikta ieteikuma (gaida ārēju avotu vai atsevišķu sesiju):**

- **11 — Bartaševičs (pid=181) `role`.** Gaida Rēzeknes valstspilsētas pašvaldības vai CVK apstiprinājumu; 0 Saeimas balsojumu, tāpēc frakcijas krustpārbaudes nav. → [`backlog/avoti.md`](backlog/avoti.md).
- **14 — Rosļikovs (pid=211) reaktivācija.** 0 balsojumu kopš 2025-06-05; gaida CVK saraksta verifikāciju. Doc 89625 (leta.lv) liecina par apcietinājumu — tas ir arī iemesls, kāpēc slots nav rutīnas jautājums. → [`backlog/dati-db.md`](backlog/dati-db.md).
- **32 — Guna Puče → pid=189 Pūce.** Viena instance nepamato eval vārtu palaidienu; pārmērīt, ja parādās otra. → [`backlog/matcher.md`](backlog/matcher.md).
- **43 — komisiju balsojumu ievilkšana.** Jauns datu avots; atgriezties pēc kampaņas. → [`backlog/saeima.md`](backlog/saeima.md).
- **45 / 46 — UI.** Ārējās recenzijas atlikušie trīs (konsekvences rādītājs = NĒ pēc § Ne-darīt) un tēmu direktorijas 2. kārta — abi līdz lasītāju signālam. → [`backlog/vietne-ui.md`](backlog/vietne-ui.md).
- **49a — repo tīrīšanas Brief (c) grupa.** c3 NVO, c4 publicēto attēlu apcirpšana, c5 plānu arhīvs, c7 sīkumi. → [`backlog/repo-higiena.md`](backlog/repo-higiena.md).
- **50 — citātu triāžas sesija (NAV palaista).** Forma apstiprināta 08-17, sesija joprojām nav notikusi. Apjoms precizēts 2026-09-07: **13 `paraphrase_mid` rindas** virs 0,85 + **179 termināļa pieturzīmes** + **37 vājie** (zem 50 % vārdu seguma) + **17. pārbaudes 7 jaunie citātu id** (615955, 689768, 704089, 704179, 704217, 704342, 709073). **615955 ir pieturzīmju klase, ne pārskrāpējums** — citāts doc 80022 IR, 251 no 252 zīmēm sakrīt zīme zīmē, atšķiras vienīgi noslēguma pieturzīme (CHANGELOG 2026-09-07 (1)). Rindu-pa-rindai, nekad batch; `claims.quote` ir VERBATIM, tāpēc labojums ir vai nu atgriešanās pie avota teksta, vai `quote`→NULL.
- **51 — video ingest (NAV palaists).** `SELECT COUNT(*) FROM documents WHERE platform='video'` joprojām = 0. Pirmais reālais ievākums = **Kola LTV intervija** (mierīgs formāts, Data Contract #13); Briškena airBaltic debašu video NĒ — diarizācijas robežas asiņo tieši uz crosstalk.
- **52 — NVO × VAD 24 jauno pāru triāža.** Gaida UR izrakstus; bez tiem sesija apstātos pirmajā pārī. → [`backlog/vad.md`](backlog/vad.md).

**Izpildīts 2026-09-06 vakarā ar operatora lēmumu (CHANGELOG «2026-09-06 (2)»):** 31 Zīles `negative_patterns` + 2 junction rindas; E1 vēsturiskā `subject` demotēšana (2 993 releja + 34 biroja balss rindas → 0; dubultpāri 3 376 → 3 278); 49b pirmais `csp --apply` (+28 rindas) ar atjaunotu `curated/atmina/statistika*` momentuzņēmumu. Noraidīts 09-06: 34 (17 ASCII `name_forms` — 5 doku vērtība) — **09-07 pārmērīts un atkārtoti sagatavots ar citu pamatojumu, sk. rindu 34 zemāk; lēmums atkal operatora.** Atlikts: 50 citātu triāža, 51 video.

**Sagatavots, gaida operatora apstiprinājumu (SQL uzrakstīts, NAV izpildīts):**

- **34 — tukšo `name_forms` ASCII varianti.** `data/proposed_name_forms_2026-09-07.md`, **17 rindas**. **Verdikta pamatojums nesakrita:** tukšas `name_forms` NEnozīmē trūkstošus locījumus — matcher tos ģenerē pats; trūkst tikai ASCII variantu, un tie 89 649 doku korpusā ir vērti **5 dokumentus** (61 no 66 ierosinātajām formām nedod nevienu trāpījumu).
- **35 — Žuravļevs (pid=187): `feed_type='relay'` NAV ieteicams.** Mērījums: RT ir 211 no 237 `subject` dokiem, bet **visas 28 pozīcijas nāk no viņa paša tvītiem**, un `relay` tās nogrieztu. RT troksnis pieder 36.–38. rindas mehānismam, ne šim slotam. Rinda paliek te tikai tāpēc, ka verdikta ieteikums ir atcelts, ne izpildīts.

**Infra mērījums, kas atjaunots 2026-09-07:**

- **X pūls ir vesels** — `scripts/probe_x_cookies.py`: 5 sloti × 4 endpointi = **20/20 OK**, 0 neveiksmju; `SearchTimeline` (tieši tas, kura dēļ pieminējumi krita atpakaļ uz `timeline`) atbild **visos piecos slotos**. **Lēmums par `search` pārplānošanu paliek operatoram** — mērījums to vairs nebloķē. Piezīme metodei: `get_pool().status()` šim nederētu — tas rāda tikai procesa iekšējo stāvokli un svaigā procesā vienmēr ziņo 5/5 «available»; pareizā pārbaude ir zonde. Seguma puse → [`backlog/avoti.md`](backlog/avoti.md) § X pieminējumu `timeline` fallback.

**Jauni operatora punkti no 2026-09-07 stāvokļa apskata (3 Opus aģenti, read-only; CHANGELOG «2026-09-07 (13)»):**

- **53 — nedēļas rutīnas § 1 `weekly_cross_check(0.80)` nav rinda.** Mērījums 56 871 pāri (Braže 8 543, Kulbergs 7 230, Dombrava 7 013); soli aizvērt vai pārrakstīt uz `/deep-check` — sk. `wiki/operations/weekly-routine.md` § 1 piezīmi.
- **54 — Latkovskis (pid 114): `x_handle='a_latkovskis'` bez `social_accounts` rindas.** Vienīgais šīs klases gadījums (199 aktīvie); kopš B2+D2+H trūkstošā rinda maksā gan X ievākšanu, gan pieminējumu segumu. `social_accounts` ir operatora-review izmaiņa (`/seed-entity` paterns).
- **55 — 17. pārbaude: 6 jaunas citātu zaudēšanas pēc re-scrape** (#615955, 689768, 704089, 704179, 704217, 709073; `checked=47 flagged=17`, 11 vecie pieņemtie paliek). Rindu pa rindai kopā ar 50.
- **56 — Reddit melnraksts `docs/social/2026-09-07-nedelas-parskats-reddit-atminalv.md` pārkāpj biežuma noteikumu** (`operacijas.md`: ne biežāk kā reizi ~2 nedēļās, tikai konkrēts atradums, ne kopsavilkums; pēdējie posti 09-06). Publicēt tikai ar apzinātu izņēmumu.
- **57 — 6. pārbaude: 101 vienas dienas dublikātu grupas 30 d logā** (`checked=1195`, augšējā robeža — bez stance-līdzības filtra). Pirms griešanas vajag otru filtru.
- **58 — r/latvia progresa + jautājumu posts AIZTURĒTS uzlabošanai** (`docs/social/2026-09-08-rlatvia-progress-un-jautajumi.md`, operatora lēmums 2026-09-08). Teksts pilns un skaitļi mērīti 09-08, bet pirms postēšanas gaida saturisku kārtu. Divi zināmie jautājumi tajā: (a) pārkāpj biežuma noteikumu — pēdējais PUBLICĒTAIS r/latvia posts ir 09-06, un šis ir kopsavilkuma, ne atraduma žanrā (pārklājas ar 56); (b) «27, nevis 2 700» ir ilustrācija, ne izmērīta attiecība — melnrakstā ir gatava pārbaudāma alternatīva. Skaitļi novecos: pirms postēšanas pārmērīt.
- Sīkumi bez lēmuma: `docs/HANDOFF-2026-09-08-…` nosaukums sola 09-08 darbu, bet fails slēgts; CHANGELOG `2026-09-07 (1)–(11)` stāv zem 09-06 ierakstiem (commit-oti 09-06) un divi saka «nav deployots», lai gan 09-06 rutīna deployoja pilnu koku.

## Atvērto darbu indekss

_Detalizētie ieraksti dzīvo tēmas failos `backlog/*.md` (sadale 2026-08-19). Pirms darba tēmā izlasi attiecīgo failu. „§ <Sadaļa>" atsauces no citiem dokumentiem rezolvējas caur šo indeksu._

> **Indeksa forma (2026-09-05): rinda ir tēmas faila `### ` virsraksts VERBATIM** — statusa tags un teksts abi. Agrāk rindas bija pārrakstīti kopsavilkumi, un tas ražoja divus driftus, ko skaitītājs pēc uzbūves neredzēja: `[DEFERRED]` indeksā pret `[SLĒGTS 2026-08-20]` failā, un trīs pārrakstīti nosaukumi. Kopš šī datuma `tests/test_backlog_index_sync.py` salīdzina **skaitu UN statusa tagu** katram ierakstam; pārrakstīts kopsavilkums indeksā tagad nokrīt kā tests. Ja gribi indeksā citu tekstu, maini virsrakstu tēmas failā.

**[`backlog/saeima.md`](backlog/saeima.md)** — 3 ieraksti:
- **[DAĻĒJI SLĒGTS 2026-08-17]** 562 `saeima_votes.result` vērtības nāca no backfill fallback, ne no avota
- **[DEFERRED]** Priekšlikumu (amendment) balsojumu pipeline
- **[OPEN]** Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

**[`backlog/agenti-pipeline.md`](backlog/agenti-pipeline.md)** — 16 ieraksti:
- **[FIX]** Partija ≠ frakcija — paliek tikai (c) UI formulējums
- **[OPEN]** Stance-fidelity atlikums: matcher neskenē `title`, paywall stop-gate, viena notikuma dublēšanās
- **[OPEN]** Medību pēdas @contradiction-hunter (07-25 adversārā pārbaude + 08-03 ekstrakcija)
- **[FIX]** Idempotences kluso merge — vairāki distinkti claims no viena (pid, url, topic)
- **[FIX]** Partijas piederības maiņa ziņās nesinhronizējas ar tracked_politicians.party
- **[FIX]** Pārskata virsraksta labojums ir ČETRU vietu labojums — `visual_brief_json` ir kluss ceturtais (2026-08-27)
- **[OPEN]** `get_pending_politicians(days=1)` neredz VECU doku, kas iegūst jaunu `subject` slotu (2026-09-06)
- **[OPEN]** Vēstneša ingest pienāk PĒC analīzes loga — 32 no 34 augusta palaidieniem pēc 15:00
- **[FIX]** Paralēlos ekstrakcijas aģentus dala PA POLITIĶIEM, nekad pa viena politiķa dokumentiem (2026-08-25)
- **[OPEN]** Divvalodu un daudzizdevumu dublikāti — `store_claim()` idempotence tos neredz pēc konstrukcijas (2026-08-25)
- **[OPEN]** Konteksta blokos nosaukti audience runātāji bez avota saites
- **[OPEN]** Tendenču piezīmēs kaili claim ID (`#NNNNNN`)
- **[FIX]** Divi mazāki matcher/konfigurācijas robi (2026-08-02)
- **[OPEN]** Ārpolitikas tēmas confidence drift +0,18 — 07-10 skaitlis joprojām nav pārmērīts
- **[OPEN]** `find_inversions` — trīs defekti vienā predikātā (aklā zona, viltus inversija, mūsu paša saturs)
- **[DEFERRED]** Pretrunu kandidātu retrospektīvs griezums — `contradiction_candidates` tabula, ja izrādās vajadzīga

**[`backlog/matcher.md`](backlog/matcher.md)** — 14 ieraksti:
- **[OPEN]** Junction abu virzienu izmeklēšana: fantoma `mentioned` bez vārda tekstā UN pilnvārds tekstā bez junction
- **[OPERATOR]** «`subject`» lomai vajag runātāja pierādījumu — palikušas divas instances no trim
- **[OPEN]** T1 locījumu kolīziju klase (2026-08 gadījumi)
- **[OPEN]** 2026-08-15 rutīnas matcher atradumi — sugasvārda kolīzija, RSS sānjosla, nereģistrēts handle
- **[OPEN]** 2026-08-16 rutīnas matcher atradumi — trīs kolīzijas, viena atkārtojoša
- **[OPEN]** 2026-08-24 rutīnas matcher atradumi — divas uzvārda kolīzijas + `subject` lomas inflācijas saucējs
- **[OPEN]** 2026-08-26 rutīnas matcher atradumi — palicis tikai īstais vārdabrālis
- **[OPEN]** Ārvalstu revīzijas iestādes sasaistās ar Valsts kontroli (id=241)
- **[OPEN]** Bērziņš false-link — monitorings, ne kampaņa
- **[OPEN]** NBS pid=204 slota piesārņojums — sašaurināts uz CVK domēna izņēmumu (32 doki, no tiem CVK 2)
- **[OPERATOR]** Konteksta kolokācijas dizains — Meļņa, Valaiņa un Bērziņa klase vienā mehānismā
- **[OPERATOR]** 2026-09-07 seedēšanas un junction blakuskarogi — trīs mazi, katrs ar savu saucēju
- **[OPEN]** Deep-check 2026-08-17 blakus atradumi — 9 claim/datu karogi
- **[OPEN]** Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts

**[`backlog/dati-db.md`](backlog/dati-db.md)** — 12 ieraksti:
- **[OPERATOR]** 2026-08-13/14 rutīnas atlikumi — nebloķējoši, katrs savs lēmums
- **[OPERATOR]** Citātu integritātes atlikums — klases (a)–(e)
- **[OPERATOR]** LETA URL satura nomaiņa pēc izvērtēšanas — doc 72446 title≠content, claim #553929 bez sava pierādījuma (2026-08-06)
- **[OPERATOR]** Deep-check 1. viļņa datu defekti — apgrieztas stances, aplams publicētas pretrunas datējums, name_forms robi (2026-08-06)
- **[FIX]** `review_status` trigera substring-kolīzijas — abi virzieni novēroti vienā dienā (2026-08-05)
- **[FIX]** Denormalizēto lauku novecojumu partija (2026-08-05 rutīnas atradumi)
- **[OPERATOR]** 2026-08-15 rutīnas datu defekti — viena apgriezta stance, divi `role` lauki
- **[OPERATOR]** 2026-08-25 rutīnas karogi — palicis viens `inactive` politiķis un Melbārdes `party`
- **[DEFERRED]** "Aizsardzības industrija" topika splits
- **[FIX]** Timestamp glabāšana nav standartizēta (mixed LV/UTC) — pusnakts-pārkares artefaktu saime
- **[DEFERRED]** `claim_vectors` bāreņi — 7 004 vektori bez `claims` rindas; claims bez vektora 0
- **[OPEN]** LSM slug dreifs — viens raksts, divas `documents` rindas, divas saites pārskatā (2026-09-08)

**[`backlog/avoti.md`](backlog/avoti.md)** — 7 ieraksti:
- **[OPEN]** X pieminējumu `timeline` fallback = diena bez publiskās sarunas seguma
- **[OPEN]** Vēsturisko dokumentu backlogi atsevišķai sweep sesijai
- **[OPEN]** lsm/diena/tvnet truncated doku backfill kampaņa gaida lsm soft-404 sargu
- **[BLOKĒTS]** pietiek.com
- **[OPEN]** Novērošanā (bez aktīvas darbības)
- **[OPEN]** Diarizācija uz crosstalk — per-segment satura sanity-check pirms labelled_transcript (2026-07-22)
- **[OPERATOR]** Bartaševičs (pid=181) — `role` iespējami novecojis, T6 klase (2026-09-04)

**[`backlog/vad.md`](backlog/vad.md)** — 1 ieraksti:
- **[DAĻĒJI SLĒGTS 2026-08-21]** NVO maksājumi × VAD deklarācijas — JOIN atkārtots; parsera robi aizvērti; paliek operatora triāža

**[`backlog/vietne-ui.md`](backlog/vietne-ui.md)** — 8 ieraksti:
- **[DEFERRED]** Render lazy pre-fetch — MVP fetcē politicians/claims/contradictions visos call ceļos
- **[DEFERRED]** balsojumi.html Step 3
- **[DEFERRED]** F5 — migrāciju formāts (`migrations/` + `schema_migrations`), atlikts līdz nākamajai DDL maiņai
- **[DEFERRED]** 2026-07-23 drošības audita apzināti pieņemtās paliekas
- **[OPEN]** UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
- **[OPEN]** Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3
- **[OPERATOR]** Ārējās recenzijas izraksts — no sešnieka trīs jau ieviesti, trīs nav
- **[OPEN]** Tēmu direktorija un tēmas lapa — 2. kārta (meklēšana, kārtošana, jautājumu salīdzinājums)

**[`backlog/repo-higiena.md`](backlog/repo-higiena.md)** — 8 ieraksti:
- **[OPERATOR]** Repo tīrīšana — IZPILDĪTS 2026-08-14 (CHANGELOG); paliek Brief (c) grupa
- **[OPEN]** Vārtu saucēju audits — 18 kandidāti verificēti; paliek četri saucēju jautājumi (pārmērīti 2026-09-07)
- **[OPERATOR]** `paraphrase_mid` — 13 rindas virs 0,85, ko vecais likums neredzēja
- **[OPEN]** Commit autora identitāte — turpmākie commiti nokārtoti, vēsture paliek
- **[FIX]** 418 web dokumenti no `ingest_url.py` ir bez chunkiem — semantiskajā meklēšanā tie neeksistē
- **[OPERATOR]** `data/csp.db` pirmais `--apply` — vienīgais atlikums pēc ieejas punkta pieslēgšanas
- **[FIX]** Pārskatu attēli ar `.png` paplašinājumu satur JPEG baitus
- **[OPEN]** Attēla paraksta pēcapstrādes vārts — (a) prompta aizliegums IEVIESTS 2026-09-05, paliek (b) OCR/stūru heiristika
