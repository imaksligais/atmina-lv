# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md) § Izlaistie sesiju ieraksti. Oktobra lēmumi: [CHANGELOG-arhivs-2026-10.md](CHANGELOG-arhivs-2026-10.md).

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

## 2026-11-11 (1) — Saeimas lapa: amati no kurēta YAML, iepriekšējās Saeimas lēca, partiju krāsas pēc logo
- **Amati** (Prezidijs, frakciju vadība, komisiju statuss): `data/saeima15_amati.yaml` no saeima.lv (kopijas ar SHA `docs/audits/2026-11-11-saeima-amati/`; 100/100 vārdi = CVK saraksts, 18/18 amati vārds vārdā); lapa `tracked_politicians.role` nelasa. Ielādētājs krīt pie neievēlēta vārda, saraksta bez frakcijas ieraksta vai cita komisiju statusa. § Ne-darīt 37 paliek. Dizains: `docs/superpowers/specs/2026-11-11-saeimas-lapa-amati-design.md`.
- **Lēca «Balsoja N. Saeimā» = `SAEIMA_CONVOCATION − 1`:** pēc 03.11. pārslēgšanas tā rādīja pašreizējo Saeimu (98/100), tagad iepriekšējo (41/100; skaits = deputāti ar ≥1 nodotu balsi titania URL `LIVS<N>`, renderētā `saeima.html` 11.11.). `tests/test_render_saeima.py`, pierādīts ar mutāciju.
- **Partiju krāsas pēc logo** (operators 11.11.): AS #f5ae00, LPV #d4264e, SV-AJ #6a55d0, NA #7e1c3a, PRO #f06a1c, JV #4cae5a — `data/{fix,rollback}_party_colors_2026-11-11.sql`; logo kopijas `docs/audits/2026-11-11-partiju-krasas/`. dataviz validators (visi pāri): normālai redzei ≥ 15,1, CVD 6,8 (iepriekš PRO↔JV 0,9).
- **Krāsu vai veidņu maiņai vajag pilnu `.venv/Scripts/python.exe -m src.render`:** `check.sh` renderē tikai `dashboard,blog,static` (11.11. pēc `check.sh` kokā vēl bija vecās krāsas).

## 2026-11-10 (3) — X: citētais tvīts un atbildes vecāks kā konteksts
- **Defekts:** `fetch_user_replies` no sarunas bloka ņēma tikai pirmo elementu (svešu vecāku), politiķa paša atbilde pazuda (pašu `@`-tvīti 56 no 8 251 / 30 d, plāns `docs/plans/2026-11-10-citetais-tvits.md`). Tagad atgriež tikai pašu tvītus; svešs vecāks, sarunas sākums un citētais tvīts glabājas `documents.context_json`, nekad `content` (matcher, `support`, embeddingi to neredz).
- **Operators (2026-11-10):** sveši vecāki vairs nav dokumenti (esošās rindas paliek); publiski tikai «↪ Atbild @x» / «Citē @x» ar saiti, bez svešā teksta; ekstraktors kontekstu redz `get_politician_documents()['context']`.
- **Dedup:** identisks tvīta teksts no cita autora vai ar citu vecāku tagad ir atsevišķs dokuments (URL-sālīts `content_hash`), agrāk to klusi nometa. `log_action` raksta `ctx_quote`, `ctx_reply`, `ctx_missing`, `foreign_parents_skipped`.
- **Pārbaude:** `tests/test_x_context_e2e.py`, pierādīts ar mutāciju. Īsta X ielāde DB kopijā (15 kontu): 74 dokumenti, 0 dubultu pēc tvīta ID, svešs teksts renderā 0 trāpījumu. Atbilžu ceļam ir fiksēta robeža `REPLIES_DATE_FLOOR` = 03.11. (`replies_before_floor`). Avota lasītāji (`@stance-checker`, `@devils-advocate`, 2c) lieto `get_claim_source()`. Kolonna produkcijā kopš 10.11. 20:00 (`data/rollback_context_json_2026-11-10.sql`). Atpakaļaizpilde (7. solis) nav darīta.

## 2026-11-10 (2) — Valdības maiņas diena: periods bez frakcijām un pārslēgšanas skripts
- **Defekts pirms notikuma:** `seed_coalition_periods.py` koalīciju atvasināja tikai pēc `faction`; 15. Saeimā tā ir NULL visām rindām, tāpēc jaunās valdības periods būtu ar tukšu koalīciju. Tagad šādā balsojumā grupē pēc `tracked_politicians.party` → `parties.short_name` un izdrukā saucēju; tukša koalīcija ir STOP.
- **`scripts/government_switch.py`:** partiju `coalition_status` un ministru `role` pēc plāna — sagatave, sausais skrējiens ar audit 24 simulāciju, fix + rollback SQL, piemērošana vienā transakcijā. Secība: `wiki/operations/seeding.md` § Valdības maiņas diena.
- **Pārbaude:** `tests/test_seed_coalition_periods.py` 3, `tests/test_government_switch.py` 2 passed, jaunie pierādīti ar mutāciju; ražošanā sausais skrējiens «3 periodi jau ir». Uz īsta 15. Saeimas balsojuma vēl nav darbināts.
- **Nav sagatavots:** ja titania vēlāk reģistrēs frakcijas ar citām etiķetēm nekā `short_name`, perioda rinda būs jāsaskaņo ar roku (audit 24 to parādīs).

## 2026-11-10 (1) — Verdikti 2026-11-09: četri jauni vārti un kolonna VAD paterniem
- **Saraksts un statusi:** [`docs/verdikti-2026-11-09.md`](../docs/verdikti-2026-11-09.md) (48 lēmumi; operators apstiprināja visus ieteikumus).
- **`store_tension()` atsaka avotu, kas vecāks par 7 dienām** (`TENSION_MAX_SOURCE_AGE_DAYS`; spriedze datējas ar izveides dienu). Mērīts: 587 no 588 spriedzēm ir avota `published_at`, pēdējās 30 dienās 0 no 123 būtu atteiktas. Bez nolasāma datuma — glabā ar brīdinājumu.
- **Paywall ievads pēc teksta, ne `is_paywall`:** `src.quality.paywall_marker()`; `save_analysis` tādai pozīcijai pieliek `NEEDS_REVIEW` un ziņo `paywall_stub`. Delfi frāze ir 456 no 2 119 delfi.lv web dokiem un 0 no 1 663 pārējiem; 38 izlasīti, 0 viltus trāpījumu.
- **`tracked_politicians.vad_negative_patterns`:** VAD filtrs lasa to kopā ar `negative_patterns`, ziņu matcher tikai `negative_patterns`. VAD tādvārža paternu turpmāk liek jaunajā kolonnā (`/seed-entity`, `vad-declarations.md`); esošās vērtības nav pārvietotas (`backlog/matcher.md`).
- **Atgūšanas zīme** `mark_recovery_evaluated()` (`logs`, derīga līdz doka `scraped_at` maiņai); attēla prompts no pašreizējā `content` (`current_visual_brief()`); noteikumi «retvīts par sevi» un «nozieguma pārmetums bez apsūdzības» promptos.

## 2026-11-09 (4) — Instrukciju pārskats: `@stance-checker` pastāvīgs, frakcijas pārbaude 15. Saeimā
- **`@stance-checker`** no izmēģinājuma (10-15) kļūst par `/dienas-rutina` soli 2d (operators). `print_routine` to nerāda; pēda — JSON fails un rollback commits.
- **Frakcijas disciplīna, kamēr `faction` NULL visām balsojuma rindām** (8643: 96/96, 8644: 98/98; handoff 09.11.): `faction IS NULL` atgriež visu Saeimu, tāpēc mednieks un `@devils-advocate` grupē pēc `tracked_politicians.party` un to pasaka kontekstā. Pagaidu izņēmums no T6 korolāra (operators); beidzas ar pirmo ne-NULL frakciju balsojumā.
- **No privātās atmiņas uz repo:** pārskats tikai pēc vakara ielādes (09-07) un Saeimas dienā pēc `/saeima-ingest` (`/dienas-rutina` 7. solis); Atradumu labojumiem advisor + Astra (`deploy.md`, 11-04); `CLAUDE.md` § Session Start nosauc `docs/HANDOFF-*.md`.
- Atsauču pārbaude: 778 ceļi un simboli 75 instrukciju failos, 15 neatrisināti, visi vēsturiskas piezīmes vai paraugi (skripts nav repo; vienreizējs).

## 2026-11-09 (3) — Satversmes tiesa: AS akcionāru dati vairs nav publisks avots
- **Fakts:** lieta Nr. 2024-01-01 (09.11.2026) — normas, kas ļauj ikvienam bez pamatojuma iegūt AS akcionāru (fizisko personu) datus, neatbilst Satversmes 96. pantam; zaudē spēku publicēšanas dienā.
- **Lēmums (operators):** uz pilnām UR `stockholders` kopām (arī mūsu Wayback kopija, izveidota pēc sprieduma publicēšanas) publiski NEsaitējam; Višvanati rakstā tikai ziņa par spriedumu un par saglabāto kontrolsummu. Pierādījums: `docs/audits/2026-11-09-akcionari/README.md`.
- **Sekas:** jauniem atradumiem (arī NVO×VAD) UR akcionāru atvērtie dati nav avots; privātus AS akcionārus vārdā nenosaucam.

## 2026-11-09 (2) — Ops panelis pieņem POST tikai no sevis
- **Lēmums:** `src/dashboard/server.py` atsaka POST bez `HX-Request: true` vai ar svešu `Origin` (403) un svešu `Host` (400, `TRUSTED_HOSTS`). Jaunai paneļa darbībai jābūt HTMX `hx-post`, parasta `<form method=post>` saņems 403. Audits 2026-11-07 § 1 (4): svešas lapas POST sasniedza deploy.
- **Aktivitāšu panelis:** kursors = tabulas `MAX(id)` pirms nolasīšanas, atbilde to nes `hx-swap-oob`; lapošana pēc apvienošanas, filtrs SQL pirms `LIMIT`. Budžets = `MONTHLY_BUDGET_USD` (20, ne 5).
- **Pārbaude:** `test_cross_site_post_cannot_trigger_deploy` un divi aktivitāšu testi pirms labojuma krita; dzīvais panelis: svešs POST 403, svešs Host 400, savs 404 (neesošs attēls), «guardrail» 0 → 20 rindas.

## 2026-11-09 (1) — B2 priekšvārda veto salīdzina vārdus bez garumzīmēm
- **Lēmums:** priekšvārda pārbaudes (B2 veto, kopīgā uzvārda izšķiršana, parastā vārda uzvārds) salīdzina arī diakritiku salocīto formu (`src/matcher.py::_fold_diacritics`): «Ainārs Latkovskis» tekstā apstiprina DB «Ainars» un otrādi (doc 148016; 6 doki / 5 saites kopš 09-01, `backlog/matcher.md` vēsture `git log --grep=B2`).
- **Pārbaude:** `tests/test_matcher.py::test_foreign_first_name_veto_folds_diacritics` pirms labojuma krita; `scripts/eval_matcher_collisions.py` (jauns `fold` slēdzis, rinda `B2D2HC_nofold`): fp_links 2 → 2, gold 3800 → 3803 / 3895, silver_added bez izmaiņām (1540 abās rindās), fidelity 943 doki / 0 neatbilstību. Kopīgā uzvārda zaru tests pierādīts ar mutāciju; parastā vārda zaram testa nav.
- Vēsturiskās saites nav pārskenētas; labojums darbojas uz jaunām ielādēm. Blakus: «Ilja Ivanovs» → pid 92 (agrāk `None`; vecais un jaunais `match_politician` salīdzināti), tāpēc § Ne-darīt rinda par `audit_matcher_name_forms` mūžīgo karogu izņemta — nākamajā `/audit-integrity` karogam jāpazūd.

## 2026-11-07 (2) — Koda pārskats: CI labojums, aģentu frontmatter, instrukciju drifts
- **Pārskats** (36 aģenti, tikai lasīšana): [`docs/audits/2026-11-07-koda-parskats/README.md`](../docs/audits/2026-11-07-koda-parskats/README.md); atlikums — `backlog/repo-higiena.md`.
- **CI sarkans kopš 04.11.:** `_TextFinder._pending` pārrakstīja Python 3.11.18/3.14 `HTMLParser` lauku (`5467998a`). **`@weekly-brief-writer` neielādējās kopš 01.11.:** `: ` aprakstā salauza YAML; vārti `tests/test_prompt_frontmatter.py` (bez labojuma krīt uz abiem failiem).
- **Noteikumi saskaņoti ar kodu:** T15 — renders pārskatu bez `publish_approvals` rindas kokā neliek, tāpēc atļauju ieraksta pirms rendera (`/dienas-rutina`); frakcijas disciplīnas noteikums (11-06) pārnests uz `/deep-check`, `@devils-advocate` un `historic-engine.js` (tur arī `reviewed=True`, `headline`); nesasaistīts deputāts = STOP un ziņojums operatoram (trīs pretrunīgas vietas → viens noteikums), `name_forms` aģents nepievieno.
- **Sīkumi:** `wiki-tools.md` paraksti, budžets = `MONTHLY_BUDGET_USD`, `file:line` → `file::simbols`, X sīkdatņu sloti 1–5; saraksts — audita beigās.

## 2026-11-07 (1) — `store_vote()` balsojuma identitāte ir arī (datums, laiks ar sekundēm)
- **Lēmums:** tas pats brīdis ar citu saiti = tas pats balsojums; patur esošo saiti, `logs` `saeima_vote_same_moment`; citas kopsummas → `ValueError`. Mērīts: `saeima_votes` 8 528 rindās 0 sakritību pēc (`vote_date`, `vote_time`).
- **Pārbaude:** `tests/test_saeima_vote_same_moment.py` pirms labojuma krita 2 no 3. Dzīvā darba kārtība pastāvīgo saiti nerāda, tāpēc `parentID=` sēdes dienā paliek (`backlog/saeima.md`).
- **Noraidīts ar mērījumu:** iestāžu `subject` demotēšana web dokos (`BACKLOG.md` § Ne-darīt).

## 2026-11-06 (3) — Rutīna: pretruna #66 nepublicēta; relay tvīts atnesa dienas galveno faktu
- **#66** (Šmits, `minor_shift`) `confirmed=0`; četri Kulberga 753287 pāri noraidīti, jo likumprojekta saturs nav zināms (`logs` `contradiction_hunt` 06.11.).
- **753284** `stated_at` → 2026-11-04 (intervija doc 150012); **role** Bartaševičam, Kozlovskai, Šmitam (`data/rollback_roles_2026-11-06.sql`). NEEDS_REVIEW rinda 92 → 1 (#123): 41 izvērtēta, 35 pārrakstītas un pārembedotas, 15 dzēstas (`docs/audits/2026-11-07-needs-review/plan.json`, `data/rollback_needs_review_queue_2026-11-07.sql`).
- **Mācība:** ingest atnesa TV3 tvītu (152184), ne rakstu; pozīciju atrada `@brief-writer` lasījums. Vārti nav uztaisīti, sk. `backlog/avoti.md`.

## 2026-11-06 (2) — Operatora lēmumi: frakcijas disciplīna, #65, balsojuma puse pretrunā
- **Noteikumu konflikts:** frakcijas disciplīna ierobežo smagumu līdz `minor_shift`, nevis noraida (`quality-bars.md`, precedents #58). Noraida, ja nav paša runātāja vārdu par to pašu jautājumu.
- **Balsojuma puse:** pretrunu kartītēs un saišu grafā `saeima_vote` pusē ir politiķa balss un rezultāts (`ballot_line()`), ne likumprojekta apraksts (T20 stance nemainās). Tests `test_detail_page_pane_shows_the_politicians_ballot_not_the_bill_line`.
- **#65** (Ņenaševa): stenogramma un balsojumi 8/8 pārbaudīti, konteksts papildināts, paliek `confirmed=0`, līdz operators atļauj publicēt. **Rancāne** paliek noraidīta; atvērt tikai, ja atrodas viņas pašas izteikums par atcelšanas atbalstu (FP6 izņēmums, 2026-10-23).
- **Dati:** Velps 753195 konteksts atrasts un izvērtēts; T1 saites: 4 noņemtas, 2 → `mentioned` (`data/rollback_lemumi_2026-11-06.sql`). Slēgti bez izmaiņām: Vītols 7322→14452, Kulbergs 20541→724941, Kulbergs 753176 (LSM apstiprina saturu), 8644, #602, Mūrniece 151221, Stepaņenko 151214.

## 2026-11-06 — Pārlūka testi: statiskās lapas no diska, viena vieta iestatījumiem
- **Cēlonis mērīts** (`saites.html`, 400 ielādes, 8 s limits; `.scratch/testdiag/goto_variants.py`): HTTP/1.0 serveris 50 noildzes, HTTP/1.1 0 un 1, bez TCP 0. Agrākais novērtējums «~1 uz 1000 lapu» bija par zemu; svešie saimnieki un slodze nav cēlonis (5/300 arī miera stāvoklī). Kļūst redzams arī `ERR_CONNECTION_RESET`.
- **`tests/_browser_env.py`** (viena vieta, ap 35 failu nepārraksta): vienkāršs statiskais serveris → atbildes no diska; pārējie HTTP/1.1 un rinda 128; `reduced_motion` pēc noklusējuma (`::details-content` pāreja kopš 10-23 sagāza `inner_text()`); `Page.goto` 1 atkārtojums ar pytest brīdinājumu. Testu nedzēsa, atkarības nepievienoja.
- **Pierādījums:** `tests/test_browser_env.py`; `check.sh` 2× pēc kārtas 4115 passed, 0 atkārtojumu, 6 min 15–45 s (pirms: 13–15 kļūmes, 10 min 54 s).
- Testu skaita griešana nav izlemta: vispirms jāmēra dublēšanās (24.09. mērījums mērīja mutāciju, ne pārklājumu pārklāšanos).

## 2026-11-05 — Arhīva saišu pārbaude: 8 citētas kopijas vairs neatveras
- 44 adreses (`docs/audits/2026-11-04-avoti/atkartojums/recheck.json` + `probe-lens.json`): 32 HTTP 200, 11 HTTP 302, 1 HTTP 404; citētas bojātas 8. Nomainītas Višvanatu un S-Baltic rakstos; iemesls nav zināms, tāpēc par izņemšanu neapgalvojam.
- archive.ph kopiju saturu skripts nevar atkārtoti apstiprināt (429): `e1SRB` un `s6Xx4` apstiprināja operators pārlūkā; pierādījums README.
- Pārbaude: advisor + Astra. Astras precizējumi rakstā: «licensed» palicis `alt` tekstā, «cheapest» sākumlapā, Counsel kopijas stunda.

## 2026-11-04 (10) — Pagājuša sasaukuma neaizvērts amats vairs nav «pašreizējs»; titania 15 stāvoklis
- Profils `date_to NULL` no pagājuša sasaukuma rāda kā beigušos līdz `CURRENT_TERM_START` (renderā, DB nemainīta): 489 amati (`SELECT COUNT(*) FROM saeima_deputy_positions WHERE date_to IS NULL AND level!='10'`) 97 profilos rādījās kā pašreizēji. Datums sakrīt ar saeima.lv (Butāns, 14. sasaukuma profils). Tests `tests/test_render_saeima_activity.py`.
- `Saeima15_DepWeb_Public` = Basic Auth 401, ne formāta maiņa; `ingest_saeima_activity` tagad dod STOP, ne traceback (`tests/test_saeima_activity_positions.py`). 14. Saeima avotā joprojām neaizvērta: pārbaudītas 1053 rindas, 0 aizvērtu no 589.
- Atvērts, bet tukšs: 15. Saeimas jautājumi 0; debates 1 fails bez `-dkp` (2 rindas, datums NULL) nav ielādētas. Balsojumos frakcija avotā tukša (`voteFullListByNames`). Atkārtot ap 18.11.; saeima.lv ceļš — `backlog/dati-db.md`.

## 2026-11-04 (9) — X konta uzmeklēšana vienreiz, ne divreiz
- `fetch_all_x_accounts` un `fetch_twitter` tvītiem un atbildēm izmanto vienu `get_user_by_screen_name`; neveiksmīgu uzmeklēšanu atkārto. Tests `tests/test_x_lookup_once.py`.
- Dzīvi 04.11. uz 3 kontiem: 6 → 3 uzmeklēšanas, tvītu un atbilžu ID kopas vienādas. 175 aktīvajiem kontiem tas ir par 175 pieprasījumiem mazāk skrējienā.
- Laika ietaupījums troksnī nav redzams: pirmajā īstajā skrējienā X solis 690,2 s, iepriekšējo žurnālu diapazons 564–892 s (`logs/ingest*.log`).

## 2026-11-04 (8) — Tier 2 avotus ielādē vienlaikus
- `_ingest_all_async`: tier 1, tad tier 2 vienlaikus; viens domēns joprojām apstrādā vienu avotu reizē, pārlūka avoti iet pa vienam. Tests `tests/test_ingest_concurrency.py`.
- `ingest_all(dry_run=True)` uz dzīvajiem avotiem 04.11.: 367,4 s → 161,9 s (11/11 avotu, 77 → 78 dokumenti). Pirmais īstais skrējiens 04.11.: 278,4 s ar 63 dokumentiem, 22.10. bija 451,6 s ar 19 (`logs/ingest*.log`).
- X pieprasījumi un rakstu ielāde vienā vietnē paliek apzināti secīgi: pirmie konta bloķēšanas riska dēļ, otrā pieklājības dēļ.

## 2026-11-04 (7) — 31 balsojuma `summary` izlabots pret pirmavotu
- 31 `saeima_votes.summary` un 2655 no tā atvasinātās `claims.stance` (fix ar sargu katram UPDATE, `total_changes` 2748 = 31 + 2655 + 62 sarga rindas). Procedurālie, neatbilstošie un saturiski tukšie: rindas un pirmavoti `docs/audits/2026-11-04-summary-defekti/README.md`. Rollback `data/rollback_vote_summaries_2026-11-04.sql`, uz kopijas atjauno 3 tabulas pa rindām pēc SHA-256.
- Dzīvē ar pilnu renderu un deploy `16a270f1` (operatora «jā» 04.11.; `verify_host` 9/9). `document_nr` 2609/6686 un 8 atlikuma punkti — tajā pašā README.

## 2026-11-04 (6) — `parentID=` saites: atkārtojams labojums un vārti; Kulberga medību robs slēgts
- `scripts/fix_parentid_vote_urls.py`: tikai lasa, `--write` raksta SQL pāri un kartējumu; DB nemaina. Paritātes audits dod kodu 1, ja `parentID=` saite vecāka par 7 dienām (`SELECT COUNT(*) FROM saeima_votes WHERE url LIKE '%parentID=%'` tagad 0). Tests `tests/test_saeima_parentid_vote_urls.py`; 04.11. rollback uz DB kopijas: 480/480 tīri, SQL vienāds ar 04.11. pāri. Jaunā sēdē vēl nav darbināts.
- Kulbergs: 03.11. medību robs (Jev HTTP 400) atkārtots ar dzīvu Jev: #753072 ar 61 pāri, bez atzinuma 0, virs θ=0,3 0 (augstākais 0,27). 400 cēlonis nav atkārtojies, nav noskaidrots.
- Rollback `data/rollback_vote_salience_2026-11-03.sql`: tabula atrasta 03.11. ārējā kopijā (236 016 rindu); kopija rotācijā izkrīt ~decembra sākumā.

## 2026-11-04 (5) — Budžeta likumu balsojumu tēma paliek «Budžets un finanses» (operators)
- 4 budžeta likumi (836 balsojumi) paliek izslēgti no partijām; pa balsojumiem nemarķējam. Vaicājums, cena un nākamā secība: `backlog/saeima.md` § Saeimas balsojumu tēmas.

## 2026-11-04 (4) — Operatora lēmumi: #17 atsaukta, stance, saites renderā
- Pretruna #17 → `confirmed=-1` (avotā nav Siliņas vārdu; divi citāti kopsavilkumā avotos nav atrasti). #123 → 0,6 + marķieris. #11210, #548302 dzēstas (biroja balss). 8644 → `Paziņojums`/`agenda_label`.
- 18 stance pārrakstīti un pārembedoti, 5 marķieri noņemti; `open_review_queue()` 111 → 89 (`SELECT COUNT(*) FROM claims WHERE review_status='needs_review'`). Rollback `data/rollback_c065_followups_2026-11-04.sql`; rindas `docs/audits/2026-11-04-c065-triaza/parbaude.md`.
- Render pārskatos nomaina `parentID=` saites pēc kartējuma, heši nemainās (`tests/test_blog_dead_vote_links.py`); 3 sintēzes laboto tieši, bāzlīnija `render_baseline_analyses.json` atjaunota (3 rindas).

## 2026-11-04 (3) — Balsojumu saites: 480 tukšās `parentID=` → pastāvīgās
- `SELECT COUNT(*) FROM saeima_votes WHERE url LIKE '%parentID=%'`: 480 → 0; `claims.source_url`: 38 733 → 0. Kartēts pēc `(vote_date, vote_time)`, kopsummas, deputātu skaits un motīvs sakrīt 480/480; rollback `data/rollback_vote_permanent_urls_2026-11-04.sql`.
- 17 publicētajos pārskatos un 3 sintēzēs saites nav mainītas (operatora lēmums). Jaunas sēdes atkal uzkrāj `parentID=` — `backlog/saeima.md`.

## 2026-11-04 (2) — 572 pozīcijas c>0,65 bez citāta: klase tukša
- Verdikts 18 izpildīts ar 12 Codex palīgiem: 414 → 0,65; 37 tvīti ar citātu; 111 → 0,6 + `NEEDS_REVIEW`; 10 → 0,65 bez marķiera. Vaicājums un rindu lēmumi: `docs/audits/2026-11-04-c065-triaza/`; rollback `data/rollback_c065_triaza_2026-11-04.sql`.
- Novirze: šaubu rindām 0,6, ne 0,65 (claim-extractor § 4). `open_review_queue()` 0 → 111. Operatora lēmumus gaida #123 (zem publicētas pretrunas #17), #11210, #548302.

## 2026-11-04 — Četri backlog koda labojumi
- Sociālo melnrakstu kandidāti ievēro `COALESCE(confirmed,1)=1`; atgūšanu aptur tikai paša politiķa `position` no tā paša URL.
- Matcher eval `--db` nosaka arī formu un reālā matcher DB; kešs pēc skrējiena notīrīts. `link_audit_row` pie 0 atjauninātām rindām atgriež `None`.
- Regresiju testi: `test_candidates_pretrunas`, `test_recovery_survey`, `test_eval_matcher_collisions`, `test_graphics_storage`; pirms labojuma defekti reproducēti.

## 2026-11-03 (6) — Operatora lēmumi par atvērtajiem punktiem; politiķu lodziņi dienas pārskatos
- Lodziņi: dienas pārskatā pirmā pilnā vārda pieminēšana ved uz profilu ar lodziņu (`link_politicians`, tikai renderētais HTML; apstiprinājumu heši nemainās). Saiti saņem tie, kam tajā dienā ir pozīcija vai publiska pretruna (`brief_day_politician_ids()`; pret skeleta predikātu 211 dienās 0 atšķirību). Pārskata renderā 6252 / 6216 / 4468 (listed / resolved / linked). Tests `tests/test_blog_politician_links.py`.
- Kājene: klātbūtnes reģistrācija un kvoruma pārbaude nav balsojumi (`src/render/blog.py`; 588 no 8528 `saeima_votes` rindām). Mainās arī vecās kājenes.
- Pretrunu robežgadījumi (`@devils-advocate`): Ņenaševa → #65 `minor_shift`, `confirmed=0`; Kūtris (FP2), Rancāne (FP6), Daugavietis (FP3) noraidīti, pēda `robezgadijumi-2026-11-03`. Vaļējs: `quality-bars.md` («nav koalīcijas disciplīna») nesakrīt ar smaguma rubriku («whole coalition abstained» → `minor_shift`).
- `party`: `Bezpartejisks` = pārbaudīts fakts, NULL = nav pārbaudīts (`wiki/operations/seeding.md`). 753070, 753101 paturētas; T1 saites doc 149332/149309 noņemtas (`data/rollback_junction_t1_2026-11-03.sql`).

## 2026-11-03 (5) — Pāreja uz 15. Saeimu (plāns `docs/plans/2026-09-27-15-saeima-sasaukums.md`)
- `SAEIMA_CONVOCATION = 15` (`01ea0218`), `CURRENT_TERM_START = 2026-11-03` (`a417d2cb`). `get_profile_kind_map`: deputy 165→91, politician 22→89, former 6→13; no 100 deputātiem, kas 03.11. reģistrēti: 91 deputy, 8 minister, 1 regional (Bartaševičs).
- 03.11. trīs sēdes: 5 atklāti balsojumi (`saeima_votes` 8641–8645), 194 balsojumu claims, 100/100 deputāti; piecas aizklātās vēlēšanas `src/saeima/unloadable.py` (`babe71e0`, 24 ieraksti). Paritāte: darba kārtībā 8, trūkst 0, neielādējami 5.
- `role`: `data/{fix,rollback}_roles_{prezidijs_frakcijas,14saeima_outgoing,15saeima_deputies}_2026-11-03.sql` (20+59+62 rindas). Operatora lēmums vakarā: SV-AJ `coalition_status` → `opposition` (`data/rollback_coalition_status_svaj_2026-11-03.sql`); ZZS un «Stabilitātei!» — pēc jaunās valdības.
- Nav izdarāms šovakar: `Saeima15_DepWeb_Public` atbild 401 (15. Saeimas amati), 14. Saeimas amati `closed=0` (589 atvērti `saeima_deputy_positions`).

## 2026-11-03 (4) — Likumprojekta lapa: procedūras balsojums nav lasījums
- Posms DB paliek `N.lasījums` (statusa noteikums 10-09 nemainās); lapā nosaukums nāk no balsojuma motīva: «Atzīšana par steidzamu» / «Iekļaušana darba kārtībā» (`src/render/bills.py::_timeline_stage_name`).
- Gadījums: 1521/Lp14 rādīja «1.lasījums Pieņemts» + 2× «Noraidīts». Pārbaudīti 1700 posmi, pārdēvēti 134 (127 steidzamība + 7 iekļaušana; visi motīvi sākas ar «Par »). Tests `tests/test_generate_bills.py::test_procedural_votes_not_labelled_as_reading` (redzēts krītam pirms labojuma).
- Vienas dienas posmi lapā balsošanas secībā (`vote_time`), ne ielādes (`id`); posms bez balsojuma — dienas beigās. Mainās 112/571 likumprojektu lapas (salīdzināta abu kārtojumu secība prod DB). Tests `test_same_day_stages_ordered_by_vote_time`; paraugs `render_baseline_bills.json` (1286/Lp14) atjaunots.

## 2026-11-03 (3) — Verdikti: noteikumu maiņas ([`docs/verdikti-2026-11-03.md`](../docs/verdikti-2026-11-03.md))
- `_vote_salience`: «Par priekšlikumu iesniegšanas termiņu/termiņa pagarināšanu…» = procedurāls 0,4 (`a5f7bae3`); glabātās `saeima_vote` vērtības pārrēķinātas — 236 016/694 604 rindu, 171 mantotā 0,3/0,6 atstāta (`scripts/recompute_vote_salience_2026-11-03.py`, rollback `data/rollback_vote_salience_2026-11-03.sql`).
- `Nebalsoja`: divi noteikumi — reitingi/sakritība to neskaita (prombūtne ≠ nepiekrišana), skaitītāji skaita (`1e3f87bd`, `tests/test_vote_count_single_rule.py::test_rankings_sample`).
- Ekstrakcijas rinda izlaiž `journalist`+`relay` twitter/x_mention dokus; `relay_media_pids()` nemainīts (`dfeb344c`). Paraksts zem iestādes dokumenta ≠ runas akts (`sloti.md`). T21 CLAUDE.md (`719241af`).
- 14. Saeima noslēgta, 15. Saeimas konstante vēl 14 (`6e639b21`); pārslēgšana — `docs/HANDOFF-2026-11-03.md`.

## 2026-11-03 (2) — Publicēšanas apstiprinājums attiecas uz saturu (audits A1)
- Operatora lēmums: jebkurš labojums pēc apstiprināšanas → atkārtoti `approve_publish.py <key>`. `publish_approvals.content_sha256` = `publish_content_hash()` (`src/briefs.py`; avota teksts, CRLF→LF); `check_output.py --publish-gate-only` atsaka, ja hešs mainījies vai ir NULL. `is_brief_published()` nemainīts. Testi `tests/test_check_output.py` (pierādīti ar mutāciju), `tests/test_publish_approvals.py`.
- Dzīvā DB kolonnu saņēma ar `init_db()` (idempotenta migrācija, to palaiž katra ielāde). Backfill `scripts/backfill_publish_approval_hashes.py --apply`: 250 rindas, 250 aizpildītas, 0 bez satura (`SELECT COUNT(*), COUNT(content_sha256) FROM publish_approvals` → 250, 250). Rollback `data/rollback_publish_approval_hashes_2026-11-03.sql`.
- Pēc backfill `--publish-gate-only`: 0 «saturs mainījies», 0 «bez satura heša» (236 pārskata lapas, 16 analīžu lapas) — pēc konstrukcijas: backfill pieņēma pašreizējo saturu par apstiprināto. Vārti krīt: DB kopijā viens bojāts hešs → bloķēta tieši viena lapa (`blog/2026-11-02.html`).

## 2026-11-03 — Rutīnas 11. solis skaita tikai veiksmīgu deploy (audits A2)
- `_check_deploy` (`src/routine.py`) lasa tikai `logs.status='success'`; paneļa `/api/deploy` pēc veiksmes vairs neraksta otru rindu (to dara `deploy.sh` ar `approved_slugs`). Testi `TestDeployStep::test_failed_deploy_*`, `test_deploy_endpoint_writes_no_success_row` — visi 3 krita pirms labojuma.
- Kļūda bija tikai iespējama, ne notikusi: `SELECT status, COUNT(*) FROM logs WHERE action='deploy'` → 243 rindas, visas `success` un no `deploy.sh`, neviena no paneļa. Audits: `docs/audits/2026-11-02-implicitie-stavoklu-automati.md`.

## 2026-11-02 — Atradums «Mākslīgā intelekta centrs» publicēts
- `content/analizes/maksliga-intelekta-centrs-2026.md` (deploy 06604f0a, operatora atļauja 11-02): 416 000 € ← Valsts kancelejas tabula (2 rindas); 6.03.2025. balsojums 73/9/0 ← titania (nav `saeima_votes`); forma 20 jautājumi / 18 obligāti ← `docs/audits/2026-11-02-mic/ms-forms-startup-2026-11-02.json`. Grafiki `scripts/oneoff-content/mic_2026_11_viz.py`.
- `@quality-reviewer` FAIL→labots: citāts «rezultāti pagaidām ir pieticīgi» bija piedēvēts Ašeradenam, stenogrammā runā Kalniņa-Lukaševica (64 apgalvojumi pret 27 avotiem; atkārtota pārbaude 13/13).
- Arhīvs `docs/audits/2026-11-02-mic/`: Wayback 14 (CDX), archive.today 5 (operators ar roku). Izņēmums: LETA 14.06.2026. nav arhivējama — tikai mūsu kopija.

## 2026-11-01 (6) — Nedēļas stāsti: nedēļas pārskats = 3–5 stāsti no koda kandidātiem
- `weekly_story_candidates()` (`src/briefs.py`) dod skeletā `STORY_CANDIDATES` komentāru (7 veidi); tēmu, bloku, «Pārējās tēmas» un pretrunu sadaļas skeletā izņemtas. Validators atsaka neaizpildītu skeletu; vecās formas pārskati paliek derīgi. Tests `tests/test_weekly_stories_e2e.py`.
- Raksta pirmdienas rītā par iepriekšējo nedēļu. Lint 7. likums «iezīmē» (`analytic-filler-iezime`) attiecas arī uz dienas pārskatiem — apzināti.
- Spec/plāns: `docs/superpowers/specs/2026-11-01-nedelas-stasti-design.md`, `docs/superpowers/plans/2026-11-01-nedelas-stasti.md`.
- 11-02: «atkārtojas» slieksnis 3 dienas. Pilots 10-26…11-01 = `context_notes` #777 (5 stāsti, 61 kandidāts → 27 izmantoti; 928 vārdi pret 1 452 #699, tas pats skaitīšanas veids; aģents ~225 tūkst. tokenu, 10-11 bāzes nav). Nepublicēts.
- 11-02: QR § H #777 (59 teikumi, FIX ne BLOCKED) + advisor → 18 labojumi saglabāti #777 (svarīgākie: izdevumi «par», ne «līdz» 500 milj.; Kučinska atruna). Attēlu stils `stories` (tinte + nedēļas zelts, bez teksta), kandidāti 427–430 `approved=0`.
- 11-02: operators izvēlējās #428 (trīs paneļi); `cli brief` nedēļas noklusējums = `stories`, bez teksta (`_resolve_style`, `graphics-designer.md`). Pārskats apstiprināts publicēšanai.

## 2026-11-01 (5) — Politiķu saites ar lodziņu Atradumos
- Frontmatter `politicians:` (pilni slugi) tagad dod arī saiti + lodziņu PIRMAJAI pieminēšanai tekstā: `link_politicians()` (`src/render/_common/politician_links.py`, `assets/polpop.js`), tests `tests/test_politician_links.py`. Plāns `docs/superpowers/plans/2026-11-01-politiku-lodzini.md`.
- Tikai pilnais vārds burtiski ar vārdu robežām; uzvārdu/locījumu meklēšanas nav (T1). Vārds, kas minēts tikai avota `<a>` iekšā, paliek bez saites. Neatrasts vārds = stderr ar saucēju (listed / resolved / linked), ne izņēmums — dienas pārskati to lietos tālāk.
- Lodziņā balsojumu skaits = profila čips (viss vēsturiskais bez klātbūtnes); «apmeklējuma» rādītāja vietnē nav, netiek izgudrots.

## 2026-11-01 (4) — Atradums «Sabiedriskais medijs skaitļos» (LSM) publicēts; dati publiskajā spogulī
- `content/analizes/lsm-2026-skaitlos.md` (operatora atļauja 11-01): finanses no LSM 2025. g. pārskata un SEPLP izpildes analīzes (SHA-256 sakrīt), TV/portāla skaitļi pārrēķināti no CSV, balsojumi `saeima_votes` 6076, 8518–8519, 8535–8538 (frakcijas pa `vote_id`). Grafiki `scripts/oneoff-content/lsm_2026_11_viz.py`.
- Operatora lēmums: `docs/audits/2026-11-01-lsm/` (ar `dati/`, `-text`) ir publiskajā spogulī — vienīgais izņēmums no `docs/audits` izslēguma.
- Atrasts: analīžu attēlu atvasinājumi netiek pārzīmēti pēc PNG maiņas (`backlog/vietne-ui.md` [FIX]); CI `runs-on: ubuntu-24.04` (26.04 bez Playwright).

## 2026-11-01 (3) — Atradums «Pilsonība ar Saeimas balsojumu» publicēts; Saeimas avotus nearhivē
- `content/analizes/pilsoniba-ar-likumu-14-saeima.md` (deploy b2035f72, operatora atļauja): 11 akti 14. Saeimā; galīgie balsojumi `saeima_votes` id 4364…8476, frakcijas pa `vote_id` (T6). Pārbaudes: Codex gpt-6.1-sol 191 PASS / 12 FIX (ievērsti), `@quality-reviewer` FAIL→labots. Grafiki `scripts/oneoff-content/pilsoniba_2026_11_viz.py`.
- Operatora lēmums: `*.saeima.lv`, «Latvijas Vēstnesis», likumi.lv skaitās oficiāls reģistrs — nearhivē (`wiki/operations/quality-bars.md`). Publicēts ar apzinātu izņēmumu: mediju avoti (LSM ×5, LETA, press.lv) vēl nav arhivēti — `backlog/saeima.md`.
- archive.ph automatizētam pārlūkam rāda CAPTCHA → mediju lapas saglabā operators ar roku; avotu kopijas + SHA-256 `docs/audits/2026-11-01-pilsoniba/`.

## 2026-11-01 (2) — Atradumu avotu pārbaude: S-Baltic portāls pārrakstīts 3. reizi, 6 jauni Zenodo ieraksti
- `docs/audits/2026-11-01-parbaude/` (`diff01.py` pret 31.10. kopijām): 152 salīdzinātas, 104 identiskas; būtiskas izmaiņas tikai euresidencies.com/sbaltic.com (Hoppstaedter vārds 0 no 12 lapām, «5-year» → «up to 2 years», /counsel → 301) un Zenodo (konts 24258, 6 ieraksti 31.10.). Pārējie 7 atradumi: 31/31 saite 200.
- S-Baltic: rindkopa «Portāla izmaiņas 1. novembrī», laika līnija, 3 teikumi pagātnē; Wayback 1.11. kopijas pārbaudītas ar CDX. Višvanatu raksts: rindkopa par 6 ierakstiem (PDF darbavieta = JRN Rajasthan Vidyapeeth). Abiem «Papildinājumi».
- Ārējās izpētes salīdzinājums (Codex gpt-6.1-sol, tikai lasīšana): 0 pretrunu; 1 formulējuma + 9 papildinājumu ierosinājumi lokālā piezīmē — operatora lēmums, nav ieviesti.

## 2026-11-01 — Rīta ielādes `--help` un rutīnas dienas robeža ielādes uzskaitē
- `scripts/morning_ingest.py` nolasa argumentus PIRMS jebkura soļa: `--help` → palīdzība, nezināms arguments → kods 2, nekas nesākas (22.10. un 31.10. `--help` palaida īstu ielādi). Tests `test_arguments_are_parsed_before_any_step` (pirms labojuma krita).
- 1. solis (`src/routine.py::_check_ingest`) un pārskata «DIENAS STATS» dokumentu skaits (`src/briefs.py`) skaita rutīnas dienu (`routine_day_window`, 05:00 LV), ne kalendāro: ielāde, kas beidzas 00:11, ir vakardienas darbs. Dzīvā DB 25.10.: tagad «5/5, 622 dokumenti (67 web + 540 Twitter/X + 15 vestnesis)», agrāk «nav palaists» un «0 Twitter/X». Testi `*_after_midnight_*`, `test_counts_the_routine_day_not_the_calendar_day`.
- Dokumentu ATLASE analīzei (2. solis, Vēstneša saraksts) paliek pie kalendārās `scraped_at` dienas — nemainīts.

## Arhīvs (2026-04 — 2026-10-31)

Ieraksti 2026-10-01 — 2026-10-31 (piem., citētie «CHANGELOG 2026-10-08 (6)») dzīvo [CHANGELOG-arhivs-2026-10.md](CHANGELOG-arhivs-2026-10.md), iesaldēts 2026-11-08.

Ieraksti 2026-09-07 — 2026-09-30 (piem., citētie «CHANGELOG 2026-09-24 (2)») dzīvo [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md), iesaldēts 2026-10-09.

Vecākie ieraksti dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md), kas **iesaldēts 2026-09-16** — tam vairs neko nepievieno. Zemāk enkuru-stubi ierakstiem, uz kuriem atsaucas `CLAUDE.md` un aģentu prompti; virsrakstu teksts saglabāts identisks, lai saites turpina strādāt.

## 2026-07-29 — Kurētās analīzes `standalone: true` paterns + NVO dotāciju lapa

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Kurētās analīzes](CHANGELOG-arhivs.md#2026-07-29--kurētās-analīzes-standalone-true-paterns--nvo-dotāciju-lapa)

## 2026-07-27 — Matcher B2+D2+H: vārda robežas, paplašinātais priekšvārda veto, @handle formas

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Matcher B2+D2+H](CHANGELOG-arhivs.md#2026-07-27--matcher-b2d2h-vārda-robežas-paplašinātais-priekšvārda-veto-handle-formas)

## 2026-07-24 — T7 slēgts: brief skelets vairs klusi nemet tēmas (Pārējās tēmas tabula)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § T7 slēgts](CHANGELOG-arhivs.md#2026-07-24--t7-slēgts-brief-skelets-vairs-klusi-nemet-tēmas-pārējās-tēmas-tabula)

## 2026-07-23 — Stingrā CSP: drošības galvenes + viss inline JS uz assets/*.js

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Stingrā CSP](CHANGELOG-arhivs.md#2026-07-23--stingrā-csp-drošības-galvenes--viss-inline-js-uz-assetsjs)

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
