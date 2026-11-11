# atmina — Atvērtais backlog

Atvērtie tehniskā parāda + iezīmētie darbi, kas nav vēl pabeigti. Pārcelts no privātās auto-atmiņas 2026-06-08, lai būtu versionēts + atrodams visiem (atmiņa = privāta, neredzama citiem). Pabeigtā darba pēda ir tā commit, kas to slēdz (`git log --grep=<atslēgvārds>`); šis fails ir TIKAI atvērtais.

> Statusa tagi: **[BLOKĒTS]** ārējs šķērslis · **[WIP]** sākts, nepabeigts · **[OPEN]** atvērts, cēlonis zināms, risinājums nav sākts · **[DEFERRED]** apzināti atlikts, zema prioritāte · **[OPERATOR]** gaida manuālu operatora darbību · **[FIX]** mazs konkrēts labojums.

> **Uzturēšana (2026-08-01, pārrakstīts 2026-09-16):** kad ieraksts ir pabeigts, to izgriež šeit — **ne** ar svītrojumu —, un tā pēda ir tas commit, kas darbu slēdz (`git log --grep=`). `wiki/CHANGELOG.md` ieraksts (≤5 rindas) pienākas tikai tad, ja mainījās kāds noteikums vai invariants. Pirms griešanas pārbaudi, ka saturs tiešām ir nolasāms no commit ziņas vai CHANGELOG ieraksta: 2026-08-01 audits atrada 92 no 356 rindām (25 %) aizņemtas ar jau pabeigtu darbu, un divi ieraksti bija tikai šeit, tāpēc tos nedrīkstēja vienkārši izdzēst.
>
> **Un pārbaudi apgalvojumu pret failu, pirms rīkojies.** 2026-08-01 auditā 23 no 29 ieteikumiem pazemināti recenzijā; grep skaitītājs mēdz melot (105 „neatbilstības" = īsais/pilnais nosaukums; 9 no 25 „defektiem" = paša testa artefakts). Skaitlis nav atradums, kamēr neesi izlasījis rindu.

> **Ienākšanas bars (2026-08-19):** jauns ieraksts drīkst šeit tikai ar (trigeris + rīcība + lēmumu īpašnieks). Novērojumi bez rīcības → `wiki/operations/`, ne šeit. Ieraksta formāts: problēma + lēmums + pointeris; izmeklēšanas naratīvs dzīvo `docs/audits/`, ne ierakstā. Vecos ierakstus nemigrējam (08-15 lēmums par slēgto pārcelšanu paliek spēkā). **`docs/audits/` ir VERSIONĒTS kopš 2026-08-22** — līdz tam mape bija gitignorēta (08-14) un šis līgums sūtīja pierādījumus uz vietu, ko `git clean` iznīcina; 3 no 8 citētajiem audita dokumentiem bija jau pazuduši. Publiskajā spogulī mape nenonāk (izslēgumu saraksts; vienīgais izņēmums — `docs/audits/2026-11-01-lsm/`, operatora lēmums 2026-11-01), tāpēc sekošana nemaina anonimitāti.

> **Pirms griešanas mēri pa sadaļām** (`wc -c` + sadaļu sadalījums; metode — CHANGELOG arhīvs 2026-08-27 (2)). § Ne-darīt un indekss aug pēc līguma; īsts drifts ir tikai rinda, kas nedrenējas (§ Atliktais). Iepriekšējās tīrīšanas: 2026-09-07 (`750f41cc`, 1 024 → 865 rindas), 2026-10-01 (CHANGELOG 2026-10-01 (4), 808 → 731 rindas).

## Ne-darīt (izmeklēts un noraidīts — nepārvērtē bez jauna fakta)

Šī sadaļa ir **izņēmums** no augšējā kontrakta: pabeigta darba pieraksts paliek šeit ar nolūku, jo izkaisīti noraidījumi tiek atklāti no jauna ik mēnesi. Forma: ko NEdarīt + iemesls + pointeris; pilnie pieraksti līdz 2026-10-01 — [`docs/audits/2026-10-01-ne-darit-pilnais.md`](docs/audits/2026-10-01-ne-darit-pilnais.md).

- **Render / veiktspēja:** vietne pa vadu iet brotli-saspiesta (~16–27×), bloat nav first-paint problēma. NE pre-compress uz `.br`; NE `zinas`/`x` pagination; NE SQLite-WASM; NE Cloudflare-for-compression (Workers hostings kopš 2026-09-16 ir CITS lēmums); NE incremental-build-system (auditi 2026-05-30 / 06-02).
- **Ieplānota (automātiska) ielāde** — NĒ (operators 2026-09-23): ielādi dažreiz palaiž ne-Claude aģenti, un Task Scheduler sadurtos ar tiem. `morning_ingest.py` argumenti — cits jautājums (`docs/plans/2026-09-23-rutinas-uzlabojumi.md` § 6).
- **`opponent_id` pārsaukšana** — noraidīta: kolonna ir 6 pamattabulās, simtiem vietu kodā, promptos un vēsturiskajos `data/rollback_*.sql`, kas pēc tam nedarbotos; ieguvums kosmētisks.
- **`analyses` UPSERT** — NEIEVIEST (2026-07-24): dublētās grupas ir RĪTA un VAKARA viļņi ar atšķirīgām tēmām, UPSERT tās apēstu klusi. [CHANGELOG arhīvs](wiki/CHANGELOG-arhivs.md#2026-07-24--analyses-dublētās-rindas--upsert-neieviest).
- **`p3_backfill_year_urllib.py --year 2025`** — robu aizpildīšanai lieto `ingest_saeima_missing_votes.py`. Dublikātus kopš 2026-11-07 aptur `store_vote()` pēc datuma un laika, bet bulk skrējiens pārlasa visu gadu. Sk. § Saeima.
- **Doc 77556 (Abu Meri), Delfi paywall 76622/76623 un doc 80931 (diena.lv Rinkēvičs) — NEIEVĀC atkārtoti.** Dzīvās lapas ir baits pret baitu identiskas glabātajam; `ingest_one()` uz esoša URL ir no-op. CHANGELOG arhīvs 2026-08-02, CHANGELOG 2026-08-06.
- **Auto-sintēzes aģents** — `wiki/synthesis/` raksta ar roku (standing lēmums 2026-04-22).
- **Sentimenta analīze** — noņemta kā neuzticama; `sentiment=0.0` tikai shēmas saderībai.
- **Vēstures dokumenti `docs/specs|plans`** ar politracker/kampaņas kontekstu paliek — arhitektūras vēsture.
- **UI ne-defekti:** gaišais default ar dark `:root` = apzināts (`c634c47`); abi `!important` pamatoti (`802c6e8`). Sk. § Profili / UI.
- **`migrations/` ietvars (F5) — NĒ** (verdikts D4, 2026-10-01): `src/db_migrations.py` `PRAGMA table_info` kāpnes pietiek — trīs DDL maiņas kopš 09-05 bez F5 (`1fbf37ee`, `e0cbe9aa`, `1775832c`). Jauns fakts būtu DDL maiņa, ko kāpnes nevar izteikt.
- **Politiķa konsekvences rādītājs — NĒ** (verdikts 45, 2026-09-07; [`docs/verdikti-2026-09-06.md`](docs/verdikti-2026-09-06.md)). Uz šo rindu atsaucas § Atliktais 45/46; līdz 2026-10-01 tā šeit trūka.
- **NEATJAUNO `AGENTS.md`** (dzēsts 2026-08-01, operatora lēmums): novecojis starpharness fails ir bīstamāks par neesamību — svešs harness neredz ne Standing Decisions, ne trapus ([CHANGELOG arhīvs](wiki/CHANGELOG-arhivs.md)). Svešiem izpildītājiem: `CLAUDE.md` + [`portability.md`](wiki/operations/portability.md).
- **`audit_quote_fidelity.py` virsrakstu klases 38 ieraksti** — NEtaisīt batch-fix, neauditēt atkārtoti: LV ziņu virsraksts bieži **IR** citāts (2026-07-25: 50 pārbaudīti, 12 laboti, 38 leģitīmi). Tas pats `not_subject` klasei (104 rindas) — paraugu kopums, ne defektu saraksts.
- **`store_claim()` idempotences apiešana — NEMEKLĒT, tādas nav bijis.** Snapshot `atmina.db.pre-vote-url-fix-20260427`: dublēto grupu trijnieki rakstīšanas brīdī atšķīrās (`topic` vēlāk sapludināja 06-12 migrācija). CHANGELOG arhīvs 2026-08-02.
- **`store_contradiction()` dublikātu izmeklēšana** — kods ir kails `INSERT`, bet DB 0 dublikātu un 0 karājošos atsauču (2026-08-01). Nepārmērī bez jauna fakta.
- **JAUNA `x_handle` ↔ `social_accounts` pārbaude** — to sedz `/audit-integrity` 2. pārbaude; nebūvē dublikātu.
- **`ensure_embeddings_live()` visos rakstošajos skriptos** — vārti apzināti tikai bulk ieejas punktos, kas embedo; `ingest_url.py` un parity audits noraidīti pēc vārda (CHANGELOG 2026-07-25).

- **Pavediena attēlus git kokā NEGLABĀ — operatora lēmums 2026-08-27.** Ģenerēšana NAV deterministiska: promptu JSON (`docs/tweet_bank/{DATE}-thread-prompts.json`) glabā nodomu, ne rezultātu; ~10 MB mēnesī nav samērīgi. Jauns fakts būtu prasība pārpublicēt vecu pavedienu identiski.
  - **Izņēmums, kas NAV pretruna: deterministiskam ģeneratoram kods iet kokā** (`scripts/oneoff-content/make_k2_timeline.py`). Robeža ir determinisms: AI attēlam — prompts, skripta attēlam — skripts; attēls nekad.

- **2026-08-22 slop/bloat audita NORAIDĪTIE — septiņas klases, katra izmērīta** ([`docs/audits/2026-08-22-slop-un-bloat-audits.md`](docs/audits/2026-08-22-slop-un-bloat-audits.md) § 3):
  - **Stance garuma / „virziena verba" vārti — NĒ.** Pieaugums ir 08-03/08-11 pret-fabrikācijas guardrail iznākums. Atlikums = tipogrāfija → `backlog/vietne-ui.md`.
  - **Git vēstures pārrakstīšana / `gc --aggressive` — NĒ.** Simtiem commit hešu citēti kā pierādījums; spogulī ir tikai sync līmeņa commiti (kopš 2026-11-11 bez force-push).
  - **„Nepieslēgto" skriptu arhivēšana — NĒ.** 14 no 41 nosaukti `data/rollback_*.sql` galvenēs; ieguvums 0 konteksta tokenu. Pārmērīts 2026-10-11: 33 vienreizējie skripti bez nevienas atsauces — operators: paturēt ([arhitektūras pārskats](docs/audits/2026-10-11-arhitekturas-parskats.md)).
  - **VAD momentuzņēmuma eksports+dzēšana — NĒ.** Kaskāde 505 rindas 10 tabulās (priekšlikums izlaida `vad_companies`); +0,8 % vietas.
  - **`.gitignore` tīrīšana — NĒ.** Likumi ar 0 failiem ir aizsargi; skenējums negācijas neredz.
  - **`tests/fixtures/render_fixture_data.sql.gz` (0,8 MB), `lid.176.ftz`, testu komplekta vai audita ritma griešana — NĒ.** Fixture nogalināja dzīvās-DB dreifu; mazāka maksātu 147-SHA regenerāciju.
  - **`claim-extractor.md` saīsināšana vai kopīgs noteikumu fails `.claude/` — NĒ.** Precīzo dublikātu 17 promptos ir 1,1 % (2026-10-11 pārmērīts: ≤ 0,3 % no katra prompta sakrīt ar CLAUDE.md); `/dienas-rutina` amortizē ar batčošanu.
  - Turpat § 6 — **11 neverificēti kandidāti**, pārmērīti 2026-11-07 ([`docs/audits/2026-11-07-koda-parskats/README.md`](docs/audits/2026-11-07-koda-parskats/README.md)). Lielākais, `logs` (~176 MiB), ir iesaldēts kopš 08-21, un verdikts jau ir CHANGELOG arhīvā 2026-08-23: tikai izmēra dēļ nerīkoties.

- **`*_report()` dvīņi `audit_quote_fidelity.py`, `check_output.py`, `audit_saeima_agenda_parity.py` — NORAIDĪTI 2026-08-09.** `lint_lv_style_report()` formu uzspieda prompti, kas citē atgriešanas tipu; šiem 0 importētāju. Ja paraksts jāmaina, izlabo izsaukumus.
- **Saucēji `headline`, `not_subject` un `paywall` klasēm `audit_quote_fidelity.py` — NORAIDĪTI 2026-08-09.** Pirmās divas jau aizliegtas pie JEBKURAS vērtības (38 un 104 rindas), `paywall` docstring to sauc par „ne defektu". Saucēji tikai `paraphrase`, `paraphrase_mid`, `misattributed_title` — tie baro lēmumu.
- **`lint_lv_style` 196 mantojuma `%` rindas — NEMIGRĒ.** Vārti paplašināti 2026-08-09 (CHANGELOG). Migrācija prasītu rollback + re-embed un mainītu publicētus pārskatus tipogrāfijas dēļ; daļējs labojums sliktāks par neko. Arī 5 defekti #427/#435 — nelabo retroaktīvi.
- **Sintēžu saites un wikilinki — SLĒGTI.** (a) Bezpaplašinājuma saites #184 NAV 404 (serveris atrisina `.html`). (b) Wikilinki salaboti (`f3c6e10a`), sargā `tests/test_synthesis_no_wikilinks.py`.
- **Citātu labojumam NEplāno renderu pēc noklusējuma.** Profils renderē `c.quote` tikai komentāru blokā (08-03: no 20 labotām rindām publiski nonāca viena). Pārbaudi virsmu pirms uz āru vērsta soļa.
- **Pārskatu auditorijas balsu ne-defekti (2026-08-03).** `generate_weekly_brief()` balsis JAU iekļauj (bloku diagramma izslēdz pareizi — Neitrāli); tēmu top-3 pēc `salience`, Aktīvākie/starppartiju/Koalīcija-vs-Opozīcija un `_BRIEF_DAY_CLAIM_SQL` 7 dienu logs — apzināti, nepārtaisi par defektu.
- **„Sakārtosim BACKLOG, pārceļot slēgto uz CHANGELOG" — NORAIDĪTS 2026-08-15.** Pilnībā slēgti bija tikai 3,3 % rindu, un 29 no 32 statusa rindām nes arī atvērto daļu; slēgtajos ierakstos vērtīgākā ir konvencija („nepārtaisi par defektu").
- **`store_tension()` regex vārti partijas etiķetei aprakstā — NORAIDĪTI 2026-08-15.** Raža **1/77**, un tā bija T6 divdomība (novecojis `party`) — vārti noraidītu, iespējams, PAREIZU aprakstu. Citi `store_tension` vārti pārbauda faktus, ne prozu.
  - **Otrā instance 2026-08-27 (cita forma) — lēmumu neatver.** Spriedzē #246 rakstīts «Andris Kulbergs (LPV)», kaut `party`/`faction` viennozīmīgi ir AS; atrada `@brief-writer`, lasot. Jauns fakts būtu trešā viennozīmīgā. `data/{fix,rollback}_tension246_party_label_2026-08-27.sql`.
- **Trešais skaitlis („K šodienas pārskatā") `@quality-reviewer` vaicājumā — NORAIDĪTS 2026-08-15.** Skelets ievelk TĀS DIENAS pozīcijas, tāpēc K ≈ N pēc uzbūves (9/9) — saucējs, kas nemaina rīcību.
- **`wiki/dailies/` kā otrs versionēts pārskatu nesējs — NORAIDĪTS 2026-08-15.** Mape apzināti `.gitignore`-ā kā lokāla operatora virsma; nesējs ir DB.

- **`nra.lv/neatkariga/intervijas/` atkārtota ievākšana — NORAIDĪTA 2026-08-16.** Zonde 78788 / 78789 / 87900: delta +0 zīmes, korpuss NAV publiskajā HTML (tikai anonss); `ingest_one()` uz esoša URL nefetčo (`scripts/ingest_url.py:138-144`). Atvērt var tikai kā avota piekļuves (abonements/print) jautājumu.

- **pid=27 (Bordāns) `x_handle IS NULL` ir APZINĀTS — nekaro un neaizpildi** (2026-08-25). `inactive`, profila lapas nav. `/audit-integrity` 2. pārbaudes bāzlīnija `111 | 1 | 1`: NULL zara `1` ir šī rinda (`0` = kāds to «salaboja»), otrs `1` ir pid=62 Svirskis.
- **pid=62 (Svirskis) DIVAS `social_accounts` rindas ir APZINĀTAS — nedeaktivē `realNepareizais`** (operators 2026-07-16; CHANGELOG 2026-09-07 (2)). 2. pārbaudes (c) zars nefiltrē `active`, tāpēc karogs paliktu, bet `src/social.py` apturētu dzīvu kanālu (pārklāšanās ar `@ESvirskis` = 0).
- **Uzulnieka (pid 159) `party` PALIEK `Zaļo un Zemnieku savienība` — operators 2026-09-15, nekaro T6.** Vairs nav LZS biedrs, bet ir ZZS Zemgales saraksta nr. 1 (doc 107798); `party` = saraksts/frakcija. Jauns fakts: izslēgšana no saraksta ar tiesas spriedumu vai paziņojums par citu sarakstu.
- **Konteksta piezīmes #557 (09-08) un #569 (09-10) ar «tarifs apstiprināts» PALIEK kā vēsture — operators 2026-09-15.** Pārskati #562/#570 laboti (CHANGELOG 2026-09-14 (1)); piezīmes ir append-only (inv. #8).
- **Reddit melnraksti `docs/social/2026-09-07-nedelas-parskats-reddit-atminalv.md` un `docs/social/2026-09-08-rlatvia-progress-un-jautajumi.md` NEPOSTĒ — operators 2026-09-15.** Biežuma noteikums (`operacijas.md`) + kopsavilkuma žanrs.
- **Priekšlikumu balsojumu `saeima_vote` stance ar CITA balsojuma iznākuma teikumu — NAV defekts, NEatver kā [FIX]** (2026-10-04 atkārtoti atrasts un atsaukts). Operatora konvencija 2026-08-17/18 (variants b, `src/saeima/votes.py` `generate_claims_from_votes` docstring, CHANGELOG § Māsas balsojumu kopsavilkums): `summary` pieder likumprojektam, vēsturiskās rindas netiek pārrakstītas; paša balsojuma iznākums = `saeima_votes.result`. Mērogs 2026-10-04: 2 446 priekšlikumu balsojumi, 214 381 claims (`SELECT COUNT(*) FROM claims c JOIN saeima_votes v ON v.url=c.source_url WHERE c.claim_type='saeima_vote' AND v.motif LIKE 'Par priekšlikumu Nr%'`); piem. `1058/Lp14` 24/26 rindas nes 1057 «atbalstīts 1. lasījumā (52:0, 1 atturas)» (1057 totāļi 52:0:1 — pareizi). Citējot pārskatā, iznākumu ņem no `result`, ne no stance. Sasaiste ar [DEFERRED] `parent_vote_id`.
- **#704032 (Kozlovskis) `stated_at` — NORAIDĪTS 2026-08-26, defekta nav.** Doc 93463 citē «otrdienas rītā» = 18. augusts; `stated_at='2026-08-18'` PAREIZS.
- **GKR `parties.coalition_status='not_in_saeima'` NAV novecojis — NEMAINI uz `coalition`/`opposition`** (2026-08-25). Burovs (pid=74) Saeimā sēž, bet lauks apraksta PARTIJU, un `faction` viņam ir NULL (T6: partija ≠ frakcija). Kods šo gadījumu pazīst (`src/briefs.py:546`, etiķete «Bez Saeimas frakcijas»); enum pārsaukšana skartu 5 failus — nav vērta. Vaicājums: `SELECT iv.faction, COUNT(*) FROM saeima_individual_votes iv JOIN saeima_votes v ON v.id=iv.vote_id WHERE iv.politician_id=74 AND v.vote_date>='2025-09-01' GROUP BY 1`.
- **Biroja balss (padomnieks, sekretārs, preses dienests) nav amatpersonas pozīcija — nepārvērtē** (operators 2026-08-05, konvencija 08-25). Darbinieks runā savā vārdā (doki 76582/76588/76600) vai nodod amatpersonas viedokli (#703861, doc 91814) → `empty_doc_ids`; izņēmums — tā pati pozīcija ±5 dienās amatpersonas vārdos (#703938). `.claude/references/claim-extractor/sloti.md` § Biroja balss.
- **Pārskatu attēlu `.png` faili ar JPEG baitiem — NELABO, operators 2026-09-23.** Lasītāji lasa pēc satura, publiski iet tikai varianti. PNG pārkodēšana (`d447f21d`, atsaukts) = ~1,9× lielāks fails; `.jpg` salauztu `*.png` glob → klusi 404 hero. Jauns fakts: klients, kas pasniedz oriģinālu ar `image/png`.
- **Apakšaģenta atsauce uz instrukciju, ko orkestrators neredz, NAV pārkāpuma pierādījums.** Noklusējums „operators rakstījis" — pajautā. Aģents tiešu operatora ziņu citē atskaitē. CHANGELOG arhīvs 2026-08-02 (`f0853761`).

- **Meļņa pārrēķins bloku tabulās — PIEŅEMTS kā vēsturisks** (operators 2026-08-17; CHANGELOG 2026-08-18). Publicēto pārskatu bloku skaitļus NEpārrēķina: tos citē proza, maiņa radītu iekšēju pretrunu.
- **`saeima_individual_votes.faction` NULL jaunākajās sēdēs NAV skrāpera defekts** (CHANGELOG 2026-08-06): ST frakcija titania lapās izzūd ap 2026-04-16 (`src/saeima/votes.py:185-190`). Raksti „bijušie „Stabilitātei!" frakcijas deputāti", nekad „ST frakcija balsoja".
- **Institūcijas slots: runas akts šķir, ne persona** (slēgts 2026-08-12; `sloti.md` § Iestāde pret amatpersonu; CHANGELOG 2026-08-05; `data/rollback_nbs_slots_lemums_2026-08-12.sql`).
- **DeepSeek claim ekstrakcijai der tikai ar orkestratora QA** (CHANGELOG 2026-08-10 (1)): kļūdas semantiskas, `lint_lv_style` tās neķer. Neuzraudzītiem palaidieniem Opus grīda.
- **`saeima_votes.result` bez `result_source='agenda_label'` NAV citējams kā avota vārds** (CHANGELOG 2026-08-18). Backfill prasītu katras darba kārtības lapas pāršķiršanu (helperis `extract_agenda_result_labels()` ir).
- **`@Krisjanis_K` NAV Kļaviņa konts** (CHANGELOG 2026-08-18) — neko nepievieno.
- **`@J_Urbanovics` (parodija) un `@Robertskipurs` (tikai botu ieraksti) — NEpievieno kā Urbanoviča / Ķipura kontus** (operators 2026-10-08; CHANGELOG 2026-10-08 (11)).
- **Vītola (pid=64) `relationship_type='neutral'` — NEKO NEMAINĪT** (CHANGELOG 2026-08-18): finanšu ministra biroja ekonomists, ne politiķis; AS saikne datos (#20376).
- **Matīss Žuravļevs (pid=187) `feed_type` nav defekts** (CHANGELOG 2026-08-05): `first_party`; neviens `relay` konts nepieder politiķim. `SELECT sa.feed_type, sa.handle, tp.name FROM social_accounts sa JOIN tracked_politicians tp ON tp.id=sa.opponent_id WHERE sa.feed_type='relay'`.
- **Latkovska (pid=114) `role` ir PAREIZA** (CHANGELOG 2026-08-18): apstiprināta diviem avotiem; otrā komisija ir otrs patiess fakts.
- **CSP ārējo hostu allowlist vārti JAU IR** — `tests/test_csp_external_hosts.py` (CHANGELOG 2026-08-09/15).
- **Partiju wiki `claims:` lauku NEpārsauc** — solījumiem ir `program_promises:` (2026-08-18); pārsaukšana salauztu `.base` failus.
- **Deploy publish-gate v2 ir pilnīgs — nepiedāvā jaunus vārtus** (CHANGELOG 2026-08-18; CLAUDE.md T15). Vienīgais paplašinājums: «Atradumu» lapas `analizes/<slug>` (2026-10-19 (4)) — jauna publiska lapu SADAĻA ir jauns fakts, ne jauni vārti. Troksnis: `check.sh` dzīvīguma ziņojumā publish-gate paterni vienmēr rāda „BEZ TRĀPĪJUMA".

- **Cloudflare Bot Fight Mode — NEIESLĒGT** (Security Insights #2, 2026-09-16): statiskai vietnei nav origin; `verify_host.py` (`httpx`) ir tieši izaicināmā klase un vienīgais deploy pierādījums; Free plānā apiet nevar. Izmēģinājums atļauts pēc [`cloudflare-security.md`](wiki/operations/cloudflare-security.md) § 5; jauns fakts būtu izmēģinājums ar pierakstītu denominatoru.
- **Cloudflare AI Labyrinth — NEIESLĒGT** (Security Insights #15, 2026-09-16): vietne grib būt lasāma, un injicēts saturs lauž paritāti, uz kuras stāv deploy vārti.
- **Pasta DNS ierakstu proksēšana (`mail`, `webmail`, `autoconfig`, `autodiscover`) — NEKAD** (Security Insights #11–14): proxy nes tikai HTTP(S), vārdi rāda uz pasta mašīnu. #5–10 (cPanel) dzēsti ar veco hostingu 2026-10-19 (CHANGELOG 2026-10-19 (2)).

_Pievienots 2026-09-25 backlog triāžā (pierādījumi: `docs/audits/2026-09-25-backlog-triaza/`):_

- **`saeima_votes.result` audita neatbilstības NEpārtaisi par «vārtu kļūdu»** (09-25: `mismatches=0`). Pierādījuma ass ir provenance, ne aritmētika; tukšs `result` = «neko neapgalvojam». CHANGELOG 2026-08-17/18, 2026-08-21 (8).
- NE render lazy pre-fetch: vieglie prefetchi kopā ~2,8 s; smagie jau aiz `_heavy_fetch_plan`.
- **Prefiksa veto Valsts kontroles (pid=241) formai NEbūvējam** — 8 nedēļās 0 jaunu ārvalstu kolīziju (doc 20494 leģitīms). Pārbaude pie jauna trāpījuma: `(\w+(as|ijas)) Valsts [Kk]ontrol` pār jaunajām piesaistēm. Jauns trāpījums 2026-10-14: doc 133481 → `backlog/matcher.md` § Lietuvas «Valsts kontrole».
- **NEAIZTIEC #1595** («…rudais gulbis») — zemā diakritika ir runātāja; diakritiku vārti to karos mūžīgi.
- **1 408 citāti ārpus pārbaudāmās klases nav defektu kopa** (2026-08-03). Apzināta cena: fabricētu citātu neverificējamā dokā vārti neķer.
- **Doc 76612 nulles-rindu korupcija («Vīķi-000…Freibergu») — NElabot.** 0 claims; nekaitīgs.
- **#20597 (Švinka) stance un `party` PAREIZI** (doc 38416: «koalīcijas partneri @Progresivie…»; `faction='PRO'`). Nelabot, ne-re-embedot.
- **Kiršteina `party` NElabot** — gada griezums (`NULL` 454 pret `LPV` 57) ir nepareizs lasījums; sēžu logā 03-26…04-01 LPV 57/70. `/audit-integrity` 9. pārbaudes leģitīmie karogi — Ābrama 77, Kiršteins 96, Ceļapīters 145 — karosies vienmēr.
- **Stance-hash idempotences atslēgā — NĒ** (mainītu Data Contract #3). `silent_dedup` iet tikai uz stderr; atvērt, ja to sāk glabāt `logs` un biežums kļūst redzams.
- **Ārpolitikas confidence drift +0,18 (2026-07-10) nereproducējas** — `SELECT DATE(created_at), COUNT(*), ROUND(AVG(confidence),2) FROM claims WHERE topic='Ārpolitika' AND claim_type='position' …`: 0,730 → 0,731. Pie n<5 detektors klusē (`_MIN_HALF_CLAIMS`).
- **#7308 un #11003 (Čudars → Balševica pārbaude, 10.04.2026) — viens notikums divās tēmās**; konsolidācija ir redakcionāla, ne defekts.
- **X pieminējumu `timeline` fallback — bez aktivizācijas kopš 2026-07-20** (pēdējais `mentions_fetch_guardrail` ieraksts `logs`). Atver, ja nostrādā atkārtoti; (a)/(c) lēmums operatoram.
- **`scripts/ingest_url.py` embedēšanu NEpieslēgt** — 418 web doki bez chunkiem ir dizains; pārchunkošana noraidīta 2026-11-09 (zemāk).
- **2026-07-23 drošības audita paliekas (a)–(e) pieņemtas** — `site.webmanifest` 404, tap-target, `<title>` 28 zīmes, robots meta, `style-src 'unsafe-inline'`. Viltus pozitīvi: leta.lv «timeouts», HTTP versijas zonde, «apple-touch-icon trūkst».

_Pievienots 2026-11-03 (verdikti [`docs/verdikti-2026-11-03.md`](docs/verdikti-2026-11-03.md)):_

- **Konteksta kolokācijas mehānisms vārdabrāļiem (Meļņi, Valaiņi, Bērziņi) — NĒ** (verdikts 10). Mērījums 2026-10-14 (CHANGELOG 2026-10-14 (13)): «cita politiķa amats ±1 teikumā» karogo 4 627 saites, izlasē visas pareizas; pilnvārda dvīņi ar neizsekotu vārdabrāli — pa vienam gadījumam. Jauns fakts: domēna leksikons vai eval korpusā klase, ko mehānisms kustina.
- **`negative_patterns` vienai instancei — NĒ** (verdikts 7): paterns veto VISU dokumentu (`src/matcher.py::match_politicians`), tāpēc doks, kas min abas iestādes vai abas personas, pazustu. Gadījumi: Lietuvas «Valsts kontrole» doc 133481 (pid 241), Bauskas Inese Kalniņa doc 138126 (pid 101; saite jau dzēsta, apspiešana ierakstīta). Jauns fakts: otrā instance.
- **Jurēvica (pid 14) «Pret» 1030/Lp14 — NEpārbaudīt** (verdikts 11): pat apstiprināts būtu `minor_shift`, nepublicējams; /deep-check 10-12 to noraidīja kā FP3.

_Pievienots 2026-11-07:_

- **Iestādes `subject` web dokos automātiski NEdemotē** (`first_party` organizācijas). Mērīts 987 dokos ar 142 iestādes pozīcijām: virsraksts vai citāta signāls ±120 zīmes patur tikai 98/142 (69 %), un ≤1 pieminējums trāpa 39 no pozitīvajiem pret 36 % negatīvo. Vārti zaudētu īstas pozīcijas, ko saka iestādes vadītāji. Cena, ko atstājam: 30 dienās 144 web doki bez iestādes pozīcijas, no tiem 7 ar cita pozīciju. Skripti: `docs/audits/2026-11-07-org-subject/`. Jauns fakts: noteikums, kas uz šīs kopas patur ≥97 %.

_Pievienots 2026-11-09:_

- **Saite uz pilnu UR akcionāru datu kopiju (arī mūsu Wayback kopija) — NĒ** (operators 2026-11-09; CHANGELOG 2026-11-09 (3)): Satversmes tiesa 2024-01-01 — dati nav publiski; kopija ir tikai pierādījums.

_Pievienots 2026-11-09 (verdikti [`docs/verdikti-2026-11-09.md`](docs/verdikti-2026-11-09.md); iekavās verdikta numurs):_

- **Bāreņu vektorus (`claim_vectors` 7 010, `document_vectors` 450) NETĪRĪT** (25): `search_similar_claims` filtrē ar `claim_id IN (…)` jau vaicājumā (`src/db.py`), tāpēc bāreņi rezultātos vietu neaizņem. Saucējs: `SELECT COUNT(*) FROM claim_vectors_rowids WHERE rowid NOT IN (SELECT id FROM claims)` → 7 010 no 669 192. Jauns fakts: lasītājs bez šī filtra.
- **Dokumentu pārchunkošana (398 pārlādētie + 418 `ingest_url.py` doki) — NĒ** (26), kamēr dokumentu vektorus neviens nelasa.
- **Attēla paraksta OCR vai stūru heiristika — NĒ** (29): prompta aizliegums ir (`TEXT_FREE_CONSTRAINTS`, 2026-09-05), un katru attēlu operators apstiprina; stūru apskate pirms apstiprināšanas paliek obligāta. Jauns fakts: otrs izdomāts paraksts.
- **Forma «Šleseri» `name_forms` — NEPIEVIENOT** (30): tā ir gan Danas Šleseres akuzatīvs, gan ģimenes daudzskaitlis.
- **Vēstneša 130 «tikai uzvārda» `mentioned` rindas — ATSTĀT, nelasīt pa vienai** (33): ekstrakcijas rinda tās nelasa. Izlase: `docs/audits/2026-10-01-vestnesis-saites-izlase.md`.
- **Tvīti pēc 52 pozīcijām, kas dzēstas 2026-10-06, — ATSTĀT cilnē «X ieraksti»** (34): tie ir paša politiķa publiski ieraksti; pozīcijas dzēšana dokumentu neizņem (CLAUDE.md § Working Conventions).
- **Par/Pret/Atturas mini josla profila Pārskatā — NĒ** (35): rāda koalīciju vai opozīciju, ne cilvēku.
- **«Vakardienas pozīcija nenonāk nevienā pārskatā» — defekta NAV** (41): `_BRIEF_DAY_WINDOW_SQL` ņem arī tajā kalendārajā dienā ielādētās pozīcijas ar `stated_at` līdz 7 dienām atpakaļ. 10-25 piemērs (#747484, #747489, #747495; ielādēti 26.10. 00:17) atlasās 26.10. skeletā, 25.10. skeletā ne — pārbaudīts 2026-11-09 ar pašu predikātu.
- **Auguļa #725139 ↔ #717891 (degvielas PVN) nav dublikāts** (31): divi izteikumi ar 8 dienu starpību dažādos raidījumos.
- **Pretrunas #40, #48, #49, #50, #51, #55 (`minor_shift`, atklātas pirms 2026-10-08) NEPUBLICĒT; #47 noraidīta 07-30** (23). Paliek `confirmed=0`. Kozlovska 521100 → 753374 paliek noraidīts (32).
- **Kļūdu komplektu v2 (§ Atliktais 50) neturpināt** (28): ne stiprāks mutants, ne 11 Opus; `@stance-checker` kopš 2026-11-09 ir pastāvīgs rutīnas solis.
- **saeima.lv amatu parseri NEBŪVĒT** (37): `deputy_unid` no šīm lapām nav iegūstams; gaidīt titania DepWeb.

## Atliktais pēc 2026-09-06 verdiktiem

Bijusī § Operatora verdikti. 2026-09-06 verdikti (52 lēmumi) izpildīti 2026-09-07: rindu statusi — [`docs/verdikti-2026-09-06.md`](docs/verdikti-2026-09-06.md), pēdas — `wiki/CHANGELOG.md` `## 2026-09-07 (1)`–`(9)`. Rindu numuri ir verdikta numuri; uz tiem atsaucas kods un tēmu faili.

**Šeit paliek TIKAI tas, kas pēc 09-07 ir atvērts.** Katram datu labojumam pāra rollback ar unikālu scope sufiksu; `stance`/`topic` maiņai obligāts `reembed_claims.py`.


**Atlikts pēc paša verdikta ieteikuma (gaida ārēju avotu vai atsevišķu sesiju):**

- **11 — Bartaševičs (pid=181) `role`.** Gaida Rēzeknes valstspilsētas pašvaldības vai CVK apstiprinājumu; 0 Saeimas balsojumu, tāpēc frakcijas krustpārbaudes nav. Kopā Latvijai kopējā saraksta fakts jau ir pid=180 `notes` un pid=181 `role` (2026-10-01 D8 triāža: [`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](docs/audits/2026-10-01-rutinas-atlikumi-triaza.md)).
- **32 — Guna Puče → pid=189 Pūce.** Viena instance nepamato eval vārtu palaidienu; pārmērīt, ja parādās otra. 2026-09-25: no 907 pid 189 dokiem 6 satur Puče/Puči (5 — TV24 vadītājs Armands Puče ar īstu Pūces klātbūtni, pareizi), kļūda tikai 93527 — joprojām viena instance. *Īpašnieks:* operators.
- **43 — komisiju balsojumu ievilkšana.** Jauns datu avots; atgriezties pēc kampaņas. → [`backlog/saeima.md`](backlog/saeima.md).
- **45 / 46 — UI.** Konsekvences rādītājs = NĒ (§ Ne-darīt); laika ass profilā un dalīšanās kartiņas → [`backlog/vietne-ui.md`](backlog/vietne-ui.md) § Profilu UI parāds; tēmu direktorijas 2. kārta → § Tēmu direktorija ([DEFERRED]). Abi līdz lasītāju signālam.
- **49a — repo tīrīšanas Brief (c) grupa.** c3 NVO, c4 publicēto attēlu apcirpšana, c5 plānu arhīvs, c7 sīkumi. c8 `data/saeima_snapshots` NEAIZTIKT. 08-19 papildus izpildīta § A sīkā dzēšana (~6,3 MB) un divu audita dokumentu arhivēšana.
- **50 — citātu un stance triāža: izpildīta 2026-09-30, paliek atlikums.** Atskaites: [`docs/audits/2026-09-30-citatu-triaza.md`](docs/audits/2026-09-30-citatu-triaza.md) (383 rindas; <90 % burtiskā seguma 356 → 69) un [`docs/audits/2026-09-30-stance-izlase/README.md`](docs/audits/2026-09-30-stance-izlase/README.md); rollback `data/rollback_{quotes_set{1..4},withdraw_unsound,stance_grades,stance_b_rewrite}_2026-09-30.sql`. **Paliek:** (b)–(d) izpildīti 2026-10-01 (verdikti C1–C7; atlikums → rinda «2026-10-01 verdiktu atlikums»); (e) **operatora lēmums 09-30: iziet cauri VISĀM atlikušajām pozīcijām** (later 5 315 + noquote 746 + jaunās) PĒC claim-extractor pārbūves — **noquote izpildīts 09-30, later tvīti (3 758) izpildīti 10-14** (CHANGELOG 2026-10-14 (2); 8 HOLD gaida operatoru; #42 pārsieta 10-14); **izlase v4 240 + later web 300 izpildīta 10-14** (CHANGELOG 2026-10-14 (4); v4 0/240 (akli 1/30), later web 05–07 virs 10 %, 08/09 3,3 %); **2. kārta izpildīta 10-14** (CHANGELOG 2026-10-14 (5); 05–07 pilnā 680, 08/09 < 5 %, vestnesis 1/75; 8 HOLD izšķirti) — **50(e) stance slānis pabeigts pēc sliekšņa noteikuma** (operators 10-14; aizstāj 09-30 «iziet cauri VISĀM»): 08/09 web 455 rindas un v4 tvīti/web ~1 400 rindas pa vienai NAV pārbaudītas; paliek: HOLD #20389, regulāra izlase; uzlabojums (c) kļūdu komplekts v2 uzbūvēts + bāzes skrējiens 10-14 (CHANGELOG 2026-10-14 (6)): jutība NAV pierādīta — pagaidu precizitātes screen; operators 2026-11-09: paturēt, kā ir (§ Ne-darīt); blakusatradums: akli vērtētāji palaida garām apmelojuma atrunas nomešanu (RUBRIKA 6. noteikums) — kādreiz deterministiska pārbaude šai klasei (NEatvērt darbu tagad); plāns un apjoms (~125 Opus palīgi, vajag «jā» ar skaitu): [`docs/arhivs/handoffs/HANDOFF-2026-09-30-claim-extractor-parbuve.md`](docs/arhivs/handoffs/HANDOFF-2026-09-30-claim-extractor-parbuve.md).
  - **Klase `confidence>0.65` bez citāta — 572 rindas izskatītas 2026-11-04, klase tukša** (verdikts 18; CHANGELOG 2026-11-04 (2)). Paliek: `open_review_queue()` 89 rindas (14 dienu robeža; marķieris 2026-11-04) un 9 izvērtētās rindas ar palīga šaubām: [`docs/audits/2026-11-04-c065-triaza/README.md`](docs/audits/2026-11-04-c065-triaza/README.md). *Īpašnieks:* operators (lēmumi), rutīna (rinda).
- **51 — video ingest (NAV palaists).** → [`backlog/avoti.md`](backlog/avoti.md) § Video ingest (`platform='video'` = 0, 2026-09-25).
- **52 — NVO × VAD 24 jauno pāru triāža.** Gaida UR izrakstus; bez tiem sesija apstātos pirmajā pārī. → [`backlog/vad.md`](backlog/vad.md).
- **2026-10-01 verdiktu atlikums** → Zalāna (pid=186) 3 radiosakaru deklarācijas: [`backlog/dati-db.md`](backlog/dati-db.md) § 2026-09-25 (c)(2). Pārējais: [`docs/verdikti-2026-10-01.md`](docs/verdikti-2026-10-01.md).


**Infra stāvoklis:**

- **X pūls vesels (2026-09-07, `scripts/probe_x_cookies.py` 20/20, `SearchTimeline` visos 5 slotos)** — mērīts pirms `69cd8e6c` (10-19, pūla maiņa); zonde jāatkārto. Lēmums par `search` pārplānošanu paliek operatoram. `get_pool().status()` tam neder (svaigā procesā vienmēr 5/5); pārbaude ir zonde.

**Jauni operatora punkti no 2026-09-07 stāvokļa apskata (3 Opus aģenti, read-only; CHANGELOG «2026-09-07 (13)»):**

- **57 — 6. pārbaude: 101 vienas dienas dublikātu grupas 30 d logā** (`checked=1195`, augšējā robeža — bez stance-līdzības filtra). Pirms griešanas vajag otru filtru. Tajā pašā triāžā — četri pāri no 09-17 (#7181/#7199, #11170/#11171, #689406/#689409, #689424/#689425). Koda tīkls `possible_duplicate` kopš 2026-09-24 → [`backlog/agenti-pipeline.md`](backlog/agenti-pipeline.md) § Krossavota/divvalodu dublikāti.

**Jauni operatora punkti no 2026-09-15 vakara rutīnas (CHANGELOG «2026-09-15 (2)»):**

- **63 — rīta triāžas atlikums:** Kozlovska #548462 «nav grozāms» (avotā «nevar tik vienkārši mainīt») — pārspīlējums (#555840 stance izlabota 10-21). #706172 dublē #704109 (Rinkēvičs, LSM KONTEKSTS boilerplate), bet to citē publicētais pārskats #532 — **atstāj abus** (operators 2026-11-03 uztic izlemt; orķestrators: pārskata rinda ir patiess LSM 09-03 atstāsts, dzēšana prasītu publicēta pārskata labojumu par labumu ~0). #704199 c 0,85→0,65 izpildīts 2026-11-03 (`data/rollback_verdikti_c16_704199_2026-11-03.sql`).
- **65 — junction/etiķešu sīkumi:** Vītols (64) NRA etiķete «finanšu ministra padomnieks, Apvienotais saraksts» vs DB `party=None`; Aizupietis (39, MMN) publiski ar datiem pret `@partijaMMN` (Krusta video) — iekšpartejisks, `party` paliek; Latkovska (114) jaunais konts deva tikai 2024. g. RT — konts, iespējams, neaktīvs.

## Atvērto darbu indekss

_Detalizētie ieraksti dzīvo tēmas failos `backlog/*.md` (sadale 2026-08-19). Pirms darba tēmā izlasi attiecīgo failu. „§ <Sadaļa>" atsauces no citiem dokumentiem rezolvējas caur šo indeksu._

> **Indeksa forma (2026-09-05): rinda ir tēmas faila `### ` virsraksts VERBATIM** — statusa tags un teksts abi. Agrāk rindas bija pārrakstīti kopsavilkumi, un tas ražoja divus driftus, ko skaitītājs pēc uzbūves neredzēja: `[DEFERRED]` indeksā pret `[SLĒGTS 2026-08-20]` failā, un trīs pārrakstīti nosaukumi. Kopš šī datuma `tests/test_backlog_index_sync.py` salīdzina **skaitu UN pilnu virsrakstu** (tags + teksts) katram ierakstam (tikai tagu kopš 2026-09-05, pilnu virsrakstu kopš 2026-09-25 — tagu salīdzinājums palaida garām 5/86 aizdreifējušus virsrakstus); pārrakstīts kopsavilkums indeksā tagad nokrīt kā tests. Ja gribi indeksā citu tekstu, maini virsrakstu tēmas failā.

**[`backlog/saeima.md`](backlog/saeima.md)** — 8 ieraksti:
- **[DEFERRED]** `saeima_votes.parent_vote_id` — priekšlikuma balsojuma sasaiste ar bāzes balsojumu
- **[DEFERRED]** Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)
- **[OPEN]** Komisiju priekšlikumu tabulas netiek ievāktas — deputātu iesniegtie grozījumi nav redzami
- **[FIX]** Saeimas ielādes sīkumi — paralēlas ielādes daļēja rakstīšana (c)
- **[OPEN]** Dzīvās sēdes apakšpunktu balsojumi — automātiskā paritāte (`--tech`) ieviesta 2026-11-10; dzīvā sēdē vēl nav darbināta
- **[OPEN]** «Atradums» par pilsonību ar Saeimas balsojumu — PUBLICĒTS 2026-11-01 (deploy b2035f72); atlikusi arhivēšana
- **[OPEN]** Saeimas balsojumu tēmas — klasifikācija pa dokumentiem, 34. tēma «Saeimas darbs», partiju pārrakstīšana (2026-10-21)
- **[OPEN]** Jaunu sēžu `parentID=` balsojumu saites kļūst tukšas — sēdes dienā pastāvīgās nav, labo pēc tam (2026-11-04)

**[`backlog/agenti-pipeline.md`](backlog/agenti-pipeline.md)** — 6 ieraksti:
- **[OPEN]** Aģentu promptu optimizācija pēc claim-extractor v4 — audit-integrity → skripts, quality-reviewer uz RUBRIKA
- **[DEFERRED]** Stance-fidelity atlikums: matcher neskenē `title`; tvnet maksas ievadi nav atšķirami (2026-11-10)
- **[OPEN]** Medību pēdas @contradiction-hunter (07-25 adversārā pārbaude + 08-03 ekstrakcija)
- **[OPEN]** Krossavota/divvalodu dublikāti — `possible_duplicate` tīkls kopš 2026-09-24; atliek pārmērīt 6. pārbaudes 101 grupu
- **[OPEN]** `find_inversions` — `speaks()` nosaka lomu pēc pieminējuma; aklās zonas raža nav triāžēta
- **[OPEN]** Stance šūnas pārskata tabulās arvien garākas — 26/41 pārsniedz 30 vārdus

**[`backlog/matcher.md`](backlog/matcher.md)** — 8 ieraksti:
- **[OPEN]** Stale junction atlikums — 52 rindas bez vārda tekstā, 28 vēlākas piesaistes; twitter un x_mention nav auditēti (2026-11-10)
- **[OPEN]** Releja kanāla dokuments ar citā plūsmā piesaistītu autoru (`subject`) netiek pārbaudīts pieminējumu meklēšanā
- **[OPERATOR]** Junction lomas apgrieztas pārstāstos — `mentioned` runātājs nesasniedz rindu
- **[OPERATOR]** Matcher plāna 2026-07-27 atlikums (B2+D2+H ieviests)
- **[OPEN]** T1 locījumu kolīziju klase (2026-08 gadījumi)
- **[OPERATOR]** Lūša ≤4 zīmju formas (T1) — `Lūsi` dala arī pid 206 Lūse
- **[OPEN]** Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts
- **[OPERATOR]** Četri VAD vajadzībām iesēti `negative_patterns` paterni aizliedz ziņas — pārcelt uz `vad_negative_patterns` (2026-11-10)

**[`backlog/dati-db.md`](backlog/dati-db.md)** — 9 ieraksti:
- **[OPERATOR]** 15. Saeima — `parties.coalition_status` un `tracked_politicians` pēc jaunās Saeimas sanākšanas (2026-10-04)
- **[OPERATOR]** Jev keša atslēga jaucē `jev-latest`, ne atbildējušo modeli — jaukti modeļi pēc aliasa maiņas (2026-10-17)
- **[OPERATOR]** LETA URL satura nomaiņa — vēsturisko title≠content kandidātu triāža (doc 72446 klase)
- **[DEFERRED]** "Aizsardzības industrija" topika splits
- **[OPEN]** LSM slug dreifs — 40 raksta ID ar divām `documents` rindām (32 slugs, 8 `utm`)
- **[OPERATOR]** 2026-09-25 profila bio un NEEDS_REVIEW triāžas atlikumi — Zalāna radiosakaru deklarācijas (3)
- **[DEFERRED]** Pilna amatu pārskatīšana pēc 15. Saeimas sanākšanas — komisiju un frakciju vadītāji
- **[OPERATOR]** 2026-10-20 rutīnas atlikums — Mieriņas partija
- **[OPEN]** Implicītie stāvokļu automāti — ~38 dzīves cikli bez noteiktām pārejām, 10 ar reālu risku (2026-11-02)

**[`backlog/avoti.md`](backlog/avoti.md)** — 7 ieraksti:
- **[OPEN]** Vēsturisko dokumentu backlogi atsevišķai sweep sesijai
- **[OPEN]** lsm/diena/tvnet truncated backfill — novecojuši chunki, ievads «pilnajiem» dokiem
- **[DEFERRED]** diena.lv RSS ievāc saistīto virsrakstu sānjoslu → viltus `subject` (doc 87866)
- **[OPEN]** Saeimas stenogrammas (Vēstnesis) — regulāra precīzu citātu un pozīciju ieguve (operatora lēmums 2026-10-30)
- **[OPEN]** X skrāpis nesaglabā citēto tvītu un tvītu, uz ko atbild (2026-10-30)
- **[OPEN]** Ingest atnes releja tvītu, bet ne rakstu, uz kuru tas rāda (2026-11-06)
- **[DEFERRED]** Video ingest — pirmais reālais ievākums (Kola LTV intervija) + diarizācijas crosstalk sanity-check

**[`backlog/vad.md`](backlog/vad.md)** — 3 ieraksti:
- **[OPEN]** VAD: 15. Saeimas «stājoties amatā» deklarācijas + dry-run saucējs
- **[DAĻĒJI SLĒGTS 2026-08-21]** NVO maksājumi × VAD deklarācijas — JOIN atkārtots; parsera robi aizvērti; paliek operatora triāža
- **[DEFERRED]** VAD: `_norm_kind` «stājoties amatā» / «Beidzot darbu» → `interim`; kartējums dublēts

**[`backlog/vietne-ui.md`](backlog/vietne-ui.md)** — 11 ieraksti:
- **[OPERATOR]** Nākamie «Atradumi» — Toca deklarācijas un tiesas lieta par policijas izpostītu dārzu (sadaļa kopš 2026-10-17)
- **[DEFERRED]** Wiki pārskati grafā izolēti — pārskatiem nav strukturēta dalībnieku saraksta (2026-10-18)
- **[OPEN]** Partiju krāsas — atlikums pēc 2026-11-11 (ārpus Saeimas partijas, kontrasts)
- **[OPEN]** Sava vizuālā identitāte — unikāls fonts (2026-10-08, zema prioritāte)
- **[OPEN]** Tēmu ikonas — Lucide SVG sprite, tēmas krāsā, tikai lielajās virsmās (2026-10-21)
- **[OPEN]** UI audits 2026-10-27 — atlikums (S1 nedēļas diagramma, kastes→līnijas, S2)
- **[OPEN]** UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
- **[OPEN]** Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3
- **[DEFERRED]** Tēmu direktorija un tēmas lapa — 2. kārta (meklēšana, kārtošana, jautājumu salīdzinājums)
- **[OPEN]** Statiskās analīžu lapas dreifē — `vad-2026` klase pārējām `content/analizes/*.md` (2026-09-20)
- **[OPEN]** good-css 5. kārtas atlikums — mazi mērķi un operatora jautājumi (2026-10-21)

**[`backlog/repo-higiena.md`](backlog/repo-higiena.md)** — 5 ieraksti:
- **[OPEN]** Testu vide pēc 2026-10-29 iekāršanās labojuma — atlikušais (2026-10-29)
- **[OPEN]** «Kurš un kas redzams vietnē» — noteikums ~90 vietās bez īpašnieka; paplašināt `src/scope.py` (2026-10-11)
- **[FIX]** Koda sīkumi no handoffiem 09-25…10-13 — divu pulksteņu daļa izlabota 2026-10-18 (2026-10-11)
- **[OPEN]** Svaigā klonā nav parauga DB — `check.sh` jaunam līdzautoram krīt (2026-10-11)
- **[OPEN]** 2026-11-07 koda pārskata atlikums — drošība, atkarības, mirušais kods (2026-11-07)
