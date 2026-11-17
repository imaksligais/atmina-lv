# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md) § Izlaistie sesiju ieraksti. Oktobra lēmumi: [CHANGELOG-arhivs-2026-10.md](CHANGELOG-arhivs-2026-10.md).

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

## 2026-11-16 (4) — 2d: ekstraktoru paš-atzīmes iet tajā pašā labojumu partijā
- **Mērīts** (16.11. rutīna, `.scratch/rutina-2026-11-16/`): ekstraktori atskaitēs nosauca 4 stance defektus, ko atkārtota saglabāšana nelabo (753951, 753933, 753984, 753980); `@stance-checker` no tiem atzīmēja 1 (753980).
- **Lēmums:** `/dienas-rutina` 2d — šādas atzīmes orķestrators pēc avota lasījuma liek tajā pašā `apply_stance_fixes.py` failā.

## 2026-11-16 (3) — Pārbaudes, kas palaida garām zināmu defektu: citāts, «norāda», `document_nr`
- **`apply_stance_fixes.py` raksta `quote`**, tikai ja tas burtiski (arī garumzīmes) ir pozīcijas dokumentā, citādi atsaka partiju; rollback atjauno arī `quote`. Abi sargi redzēti krītam (mutācijas). 753856 citāts ierakstīts.
- **RUBRIKA 6. klase:** faktu pasniedzošs verbs («norāda») uz pārmetumu nosauktai personai = B, arī aiz semikola; norāde `claim-extractor.md` § 3.6. Viens `@stance-checker` skrējiens (`docs/audits/2026-11-16-norada/`): zināmie 753546, 753867 noķerti, bet NE akli (noteikums bija rakstīts pēc tiem); 32 aklajās kontrolēs 1 jauns īsts (753843, izlabots), viltus 0; prognoze/skaitlis 0 no 3 — `backlog/agenti-pipeline.md`.
- **`document_nr`:** NULL ar numuru motīvā 118 (ne «daži»), visi no ielādēm 04–08. Labojums 138 rindām (ar 6449), tēmas atslēga nemainās (izņemot 6449), sagatavots ar rollback, izmēģināts uz kopijas; piemērots ar operatora «jā» (138 no 138). Audita 23. pārbaude: `DELETE` un `UPDATE` bez `role` vairs neizpilda — «SQL kļūdas» 9 → 0, citi skaitļi nemainīti (`tests/test_audit_dp_readds.py`).

## 2026-11-16 (2) — Atgūšanas josla `relay_quote` TV24 tvītiem
- **Mērīts** (`docs/audits/2026-11-16-relay-citati.md`): 2026-11-09…15 17 releja kontos 205 tvīti ar 251 `mentioned` pāri, izlasīti 118; žurnālistu kontos jaunu pozīciju 0, mediju kontos ar rakstu aiz saites politiķim pozīcija jau ir; TV24 — 6 no 7 ir citāts bez raksta.
- **Lēmums (operators 2026-11-16):** vispārīgu joslu nebūvēt; `recovery_survey` josla `relay_quote` tikai `RELAY_QUOTE_HANDLES` (`tv24_lv`), bez runas signāla prasības; jauns konts = operatora lēmums. Pirmais skrējiens (8 dienu logs): 1 pāris, doc 159050. `seeding.md`: relay tvītā pieminētie ir `mentioned`, ne `subject`.

## 2026-11-16 — Pārskata labojumu skripts un kopīgs nedēļas vārdu skaitītājs
- **Mērīts:** pirmais nedēļas skrējiens pēc 15.11. vārtiem — QR 5 + 0 + 0 (02.11.: 9, 09.11.: 13), nepareizu dienu 0, `unverbatim_quotes` 0; rakstītājs un QR ar vienu skaitītāju abi 974 (09.11.: 754 pret 618). `.scratch/` krājas 16 rokas `qr_fix*.py`.
- **`scripts/apply_brief_fixes.py`** aizstāj rokas skriptus (`/dienas-rutina`, `weekly-routine.md` § 2): vietas atrod pats (pārskats + rutīnas dienas vai nedēļas piezīmes un spriedzes), atsaka pie neatrasta teksta, jauna lint atraduma, publicētas piezīmes (inv. #8), necommitēta vai novecojuša rollback; agrākas dienas pārskatam patur `created_at`. Rollback teksts ir pa rindām ar `char(10)` — CRLF izrakstīts fails atjauno baitu baitā. 10 no 10 sargiem redzēti krītam (mutācijas).
- **`src.briefs.weekly_brief_word_counts`** + `scripts/weekly_brief_words.py`: viena definīcija rakstītājam un QR; tikai ziņo.

## 2026-11-15 (2) — Nedēļas pārskats: diena tikai no avota, citāti, dienas rutīnas vārti
- **Mērīts** (sesiju žurnāli `c6847bdc` 02.11., `56e83080` 09.11., QR atskaites): atradumi 9 un 13; diena ņemta no publicēšanas datuma 2 un 5 reizes; abās reizēs viena QR kārta un publicēts pēc labojumiem bez atkārtotas. `unverbatim_quotes` uz 09.11. melnraksta (`.scratch/weekly-2026-11-02/draft.md`, 26 no 29 saitēm DB): 2 trāpījumi, 1 no 3 QR citātu atradumiem.
- **`@weekly-brief-writer`:** diena tikai tvītam vai no avota teksta; citāts burtiski un nenogriezts; Self-check 11–12. **`weekly-routine.md` § 2:** dienas rutīnas labojumu un tīrās kārtas noteikumi attiecas arī uz nedēļas pārskatu.
- **`@brief-writer` Self-Check 21 precizēts:** izteikuma dienu raksta tikai tvītam vai no avota teksta — `stated_at` rakstam bieži ir publicēšanas diena. Vārti vēl nav redzēti krītam; pirmais nedēļas skrējiens 16.11.

## 2026-11-15 — Rutīnas vārti pēc 14.11. izvērtējuma: tīra QR kārta, datums «Galvenais» punktos, Jev saraksts
- **Mērīts** (sesiju žurnāli `74e93556`, `fcfe4a1e`; `claims` pēc `created_at` rutīnas dienas loga): 14.11. trešā QR kārta 22:42 — BLOCKED, 2 labojumi 22:43, apstiprināts 22:51 un deploy 22:57 bez ceturtās kārtas; 9 no 44 dienas pozīcijām ar `stated_at` 13.11., otrais «Galvenais» punkts tikai no tām; Jev izdruku nesaņēma 2 no 3 medniekiem.
- **`/dienas-rutina`:** operatoram jautā tikai pēc kārtas ar 0 § H atradumiem (atkārtotā kārta lasa visu prozu, labojumus pirms tās redz advisor; pēc piektās kārtas — stop un operatoram); Jev īso sarakstu katram balsotājam palaiž orķestrators (maksas zvani). **`@brief-writer` Self-Check 21:** punkts ar agrākas dienas avotiem nosauc dienu.
- Neviens no trim vārtiem vēl nav redzēts krītam — pirmais skrējiens 15.11. Mērķis salīdzināšanai: § H pirmajā kārtā ≤ 2 (14.11.: 5), 0 no orķestratora paša teksta (14.11.: vismaz 3).

## 2026-11-14 (5) — Docs sakārtoti: 46 arhivēti, 173 dzēsti, testēšanas recepte vienuviet
- **Atlase** (`.scratch/docs_inventory.py`, ārpus repo): docs vienība, uz kuru neatsaucas nekas dzīvs (kods, testi, `data/*.sql`, `content/`, backlogs, prasmes, aģenti, `wiki/operations`) vai tikai cits arhivējams dokuments. Pirmās kārtas nenoteiktie izlasīti; otrā kārta atlasīta pēc atsauču ķēdes, nelasot (T18). Atsauces no paliekošajiem dokumentiem nomainītas. Pierādījumu kopijas paliek bez atsaucēm. 46 dokumenti (63 faili, tīrs `git mv`) arhīvā tajā pašā spoguļa līmenī; saraksts `docs/arhivs/README.md` § 2026-11-14.
- **Dzēsti:** 172 sociālie melnraksti pirms 2026-10-15 bez atsaucēm (precedents 09-27); 12 ne-pārskatu melnraksti bez atzīmes «postēts» atjaunoti pēc statusa galvenes, `wiki/operations/monthly-routine.md`.
- **Vārti:** mirušo ceļu skaits dzīvajās virsmās (prasmes, aģenti, `wiki/operations`, backlog, CLAUDE.md) pirms 11 / pēc 13 no ~1000 (visi apzināti: plānots vai izņemts; 2 jaunie — arhīva README nosauc vecos ceļus); neizsekoto failu saraksts nemainīgs.
- **`commands.md` § Verifikācija:** «Testēšana īsumā» — iterē ar vienu failu, pilnais `check.sh` vienreiz fonā, ne reizē ar DB rakstītājiem vai otru Playwright.

## 2026-11-14 (4) — Rutīnas advisor vārti: pašu teksts, partijas, QR labojumi
- **Mērīts 14.11. rutīnā** (sesijas žurnāls, QR atskaites, `.scratch/qr_fix*_2026-11-14.py`): QR § H 5 + 1 + 2 atradumi trijās kārtās (13.11.: 7 divās) un 1 advisor labojums. Vismaz 3 no 9 radās orķestratora paša tekstā (spriedze #666, piezīmes 834 un 835), kas glabāts bez advisor; 1 radīja paša labojums; 2c 4 vakara rindas gāja bez advisor.
- **`/dienas-rutina`:** advisor pirms spriedžu un piezīmju glabāšanas (5. solis); 2c katrai partijai savs advisor izsaukums, skaitus atskaitē dala; QR labojumus piemēro pēc domas visās vietās, pēc labojuma lint + blakus teikumi, labojumus pēc pēdējās QR kārtas pirms operatora jautājuma parāda advisor.
- Strādāja: `vote_candidates` 0 procedūras rindu 11 sarakstos; Self-Check 20 — 0 locītu citātu atradumu (vārti šajā skrējienā nav redzēti krītam).

## 2026-11-14 (3) — Pretruna #69 atsaukta pēc Krištopana iebilduma
- **Operatora «jā» 14.11.** Krištopans X atbildē (doc 158160) iebilda; pilnā 1149/Lp14 ķēde (titania 2. lasījuma priekšlikumu tabula, dok. 4621): 16.04. «Par» apturēšanas priekšlikumiem Nr. 1, 17–20, viņš viens no pieciem pārvaldības priekšlikuma Nr. 10 iesniedzējiem (iekļauts Nr. 11). Publicētais teksts tos izlaida — T14 pārkāpums. `@devils-advocate`: ATSAUKT.
- `withdraw_contradiction(69)`, rollback `data/rollback_withdraw_contradiction_69_2026-11-14.sql`; claims 20702, 21177 paliek. Live `59692200`, `verify_host` 9/9, labojuma lapa izlasīta dzīvajā vietnē; 13.11. pārskatā vecais teksts paliek (precedents 13.11.).
- **Mācība:** `check_contradiction.py` ķēdē rāda priekšlikumu balsojumus ar likumprojekta aprakstu, ne priekšlikuma saturu — «Par priekšlikumu Nr. N» jāizlasa tabulā. Tāda paša ķēde ar paša balsīm vēl #65, #68 (`backlog/agenti-pipeline.md`).

## 2026-11-14 (2) — TV24 kā relay plūsma; pozīcija 18256; wiki pretrunu skaits
- **Operatora «jā» 14.11.** `tv24_lv` iesēts kā `relay` (pid 305, `organization`); `name_forms` — retas frāzes, jo tukšs saraksts liktu matcherim lietot vārdu «TV24». Tvīti ir atstāsti: pozīciju ietīt «TV24 atstāsta…» (kā 753760). Rollback `data/rollback_seed_tv24_relay_2026-11-14.sql`.
- **Pozīcija 18256** lasījās pretēji avotam (iebilst JV, ne autors) — pārrakstīta, pārembedota; `data/{fix,rollback}_claim_18256_stance_2026-11-14.sql`.
- **Wiki frontmatter `contradictions:`** skaita tikai `confirmed=1` (personas, partijas, tēmas; wiki ir spogulī). Spoguļa CI atkal zaļa (rerun 43048997029).

## 2026-11-14 (1) — X: viens garš tvīts pavediena vietā (izmēģinājums)
- **Operators 14.11.:** dienas pārskata pavedieni X «nav baigi populāri». Izmēģinājums: viens garš tvīts par vienu dienas stāstu (citāts pirmajās ~280 zīmēs, bez saites) + saite atbildē; posts kopā ar FB un Reddit par 13.11. pārskatu postēts 14.11.
- **Skatījumu skaitļu repo nav** — formāts ir spriedums, ne mērījums; operators salīdzina ar pēdējo pavedienu. Procedūra: `/social-thread` § 3a; 6 tvītu pavediens paliek kā otrs variants, līdz operators izlemj.
- Faili: `docs/tweet_bank/2026-11-14-dienas-parskats-social.md`, `docs/social/2026-11-14-dienas-parskats-{facebook,reddit-atminalv}.md`.

## 2026-11-13 (6) — Rutīna 13.11. (~103 min) un trīs labojumi 14.11. skrējienam
- **Rutīna publicēta** (live `46561b4b`): 57 pozīcijas, 6 spriedzes, 1 pretrunu kandidāts nepublicēts (operators: gaidīt). Saucēji: `docs/audits/2026-11-13-rutinas-merijumi/README.md`.
- **`src/vote_candidates.py`:** sēdes vadības balsojumi (pārtraukums, debašu laiks, kvorums, klātbūtne; 647 balsojumi) vairs nav īsajā sarakstā; zelta tests nemainīgs (top-10 12/15), 13.11. saraksti 6 → 0 procedūras rindu.
- **`@brief-writer` Self-Check 20:** citāts paša prozā burtiski (`unverbatim_quotes`), saiklis tikai no avota — 4 no 7 QR § H atradumiem 13.11. bija šīs klases.
- **`/dienas-rutina`:** operatoram QR pēdējais verdikts, kāds tas ir; rindas nemainoši labojumi drīkst iet `check.sh` laikā; sēdi pārbaudīt titania kalendārā. RT pakošana nav mainīta (31 pozīcija no 1 902 RT 30 d).

## 2026-11-13 (5) — Pretrunas #69 un #70 publicētas; #71 paliek kandidāts
- **Operatora «jā» 13.11.** pēc pārskata ar advisor: #69 Krištopans (Rail Baltica) un #70 Švinka (Rail Baltica valdes amatu savienošana) `confirmed=1`; rollback `data/rollback_confirm_69_70_2026-11-13.sql`. Live `676f8402`, `verify_host` 9/9, abas lapas izlasītas dzīvajā vietnē, `pretrunas/71.html` → 404.
- **Pirms publicēšanas pārbaudīts pirmavotos:** #70 datums likumi.lv/ta/id/369888, tvīta saite ved uz ministra priekšlikumu, debašu citāti ir Švinkas runā (doc 83269); #69 tvīts nav ne atbilde, ne citāts (X publiskais ieraksts), pozīcijas 20702 `stated_at` 21.05. → 20.05. Teksti pārrakstīti (`data/{fix,rollback}_pretrunas_69_70_71_2026-11-13.sql`): pirmais teikums pasaka, ko balsojums dara; lapas pirms «jā» renderētas no DB kopijas un izlasītas telefona platumā.
- **#71 Mieriņa nav publicēta** (`confirmed=0`): fakti pareizi, bet solījumu viņa daļēji izpildīja (atbalstīja šauro likumu, noraidīja lietderības revīzijas), un lapas «Darbi» kartīte priekšlikuma balsojumam nepasaka, ko priekšlikums paredzēja. Atvērts: `backlog/agenti-pipeline.md`.

## 2026-11-13 (4) — Vēsturiskais pārgājiens: vecās pozīcijas pret balsojumiem, 3 nepublicēti kandidāti
- **Ceļš:** īsais saraksts (top-10 likumprojekti pozīcijai) → Jev priekššķirotājs (`src/vote_candidates.py` `VOTE_INSTRUCTIONS` v2; zelta tests `eval_vote_jev.py`: pie θ = 0,3 zelts 8/13, nejaušo pāru paliek 1,6 %) → filtri (pieprasījumi `/P14`, procedūra) → `@contradiction-hunter` → `@devils-advocate` ar bināru verdiktu → `store_contradiction()`.
- **Mērīts:** 3 385 pozīcijas pirms 19.08., 30 412 pāri, Jev 0,93 USD; Opus lasīja 347 pārus divās kārtās (~1,4 milj. tokenu): 1. kārtā 2 no 187, 2. kārtā 1 no 160. Glabāti ar `confirmed=0`: #69 Krištopans, #70 Švinka, #71 Mieriņa (visi `minor_shift`). Skaitļi un rīki: `docs/audits/2026-11-13-pretrunu-faktu-parbaude/README.md` § 6.
- **Apstājos pie p 0,4;** slānis 0,3–0,4 (443 pāri) nav lasīts — lēmums operatoram pēc triju kandidātu izvērtēšanas. Dienas rutīnā Jev solis balsojumiem NAV iesiets (tikai īsais saraksts).
- **Faktu vārti pirmo reizi īstā glabāšanā:** 3 rindas, 0 atteikumu. `PĀRBAUDI [priekšlikums]` atdalīts no `[procedūra]` — priekšlikuma balsojums ir saturisks grozījums.

## 2026-11-13 (3) — Solījumu izmēģinājums: jaunu pretrunu nav, paliek gaidīšanas saraksts
- **Mērīts:** 15 amatpersonu 148 pozīcijas ar solījuma vai izslēgšanas vārdu, 4 `@contradiction-hunter` + 1 `@devils-advocate` (~1,05 milj. Opus tokenu): īsti solījumi 92, turēti 35, gaida notikumu 33, lauzts 1 (jau publicētā #39), jaunu pretrunu 0 (2 kandidāti, abi noraidīti). Tabula `docs/audits/2026-11-13-pretrunu-faktu-parbaude/solijumi_triage.json`, README § 5.
- **Lēmums pēc iepriekš noteikta kritērija:** medības pārējiem 79 politiķiem nepaplašina, kamēr 33 gaidošie nav pārbaudīti pie pirmā notikuma — jaunās valdības uzticības balsojuma (pēc tam 2027. gada budžets). Saraksts pa notikumiem: README § 5 «Gaida».

## 2026-11-13 (2) — Pretrunas faktu pārbaude ir pastāvīgs solis
- **`scripts/check_contradiction.py`** (`--draft` pirms glabāšanas, `--id` pirms jautājuma operatoram, `--published`) izdrukā faktu lapu — paša balss, frakcijas sadalījums tajā balsojumā, visa `document_nr` ķēde — un salīdzina ar kopsavilkumu. `KĻŪDA` aptur: izdomāts citāts, «visa frakcija» pie sadalītas frakcijas, nepieminēta atturēšanās.
- **Mērīts** (`docs/audits/2026-11-13-pretrunu-faktu-parbaude/replay.py`): veco tekstu 37, ar kļūdu 7. Viltus trāpījumu īpatsvars nav izmērīts (33 publicētās rakstītas pret to pašu pārbaudi); 13 atteiktie citāti izlasīti: 5 pārstāsti, 6 locīti vai saīsināti, 2 saīsināti nosaukumi. Mašīna noķer daļu, tāpēc faktu lapu lasa `@devils-advocate` arī pie tīra rezultāta.
- **Cietie vārti (operators 2026-11-13):** `src.db.store_contradiction()` rindu ar `KĻŪDU` atsaka (`ValueError`), `src.tools` apvalks atgriež `fact_check`; partiju pretrunām nepiemēro. Locīts citāts pēdiņās ir atteikums — stingrāk nekā `store_tension()` (12.11.), jo pretruna ir publisks apgalvojums par cilvēka vārdiem. Tests `tests/test_check_contradiction.py` (3), 5 mutācijas.
- **Balsojumu īsais saraksts** `scripts/vote_candidates.py`: dienas pozīcijai 10 tuvākie likumprojekti ar paša balsīm; sēdes dienā `--votes-day` likumprojektam 10 tuvākās pozīcijas. Zelta tests (`eval_vote_candidates.py`, 13 publicētās, mērīts paraugā): top-10 ir 10 un 12. Palaiž orķestrators, mednieks lasa pirmo; T9 strukturālā pārbaude paliek. Divas vecas puses (#65, #66, #68) saraksts pats neatrod. Tests `tests/test_vote_candidates.py` (2), 3 mutācijas.
- Medību raža (57 % noraidīto kandidātu ir «cits jautājums» vai «savienojamas pozīcijas») un kur vēl meklēt (706 solījumu pozīcijas, 276 programmu solījumi, 3 405 pozīcijas bez balsojumu pārbaudes): tā paša audita README § 2 un § 4.

## 2026-11-13 — Pretrunu teksti: vispirms «par ko», konteksts atsevišķi; 5 atsauktas
- **Operators par #68: «grūti saprast, nezinu, par ko tie balsojumi».** Visas 37 publicētās pretrunas pārskatītas (4 Opus palīgi + savstarpēja pārbaude pret avotiem, `.scratch/c-rewrite/check.py`, `facts_diff.py`): 32 pārrakstītas (12 ar kļūdainu publicētu faktu, piem. «visa frakcija atturējās»), 5 atsauktas ar `withdraw_contradiction()` pēc `@devils-advocate` (#4, #6, #15, #18, #24 — pamata nav). Rollback `data/rollback_pretrunas_parrakstitas_2026-11-13.sql`; live `3adbf092`.
- **Noteikums** `quality-bars.md` § Pretruna: pirmais teikums pasaka, par ko bija balsojums; konteksts tikai `[Konteksts: …]`. `src/models.py` atsaka tukšu «[Konteksts]» un kvadrātiekavas citātā (#68 renderējās ar tukšu kastīti).
- **Rūts «Likumprojekts»** abās pusēs, ne tikai jaunākajā; priekšlikuma balsojumam bloku nerāda (#65: «Pieņemts 89:0» blakus noraidītam priekšlikumam). Testi `test_og_card_vote_side.py` (2 jauni, mutācija).
- Saglabātajos pārskatos paliek vecie pretrunu teksti (labojums mainītu satura hešu un prasītu jaunu apstiprinājumu) — apzināti nelabots.

## 2026-11-12 (2) — Rutīna: 2c solim pastāvīgs rīks; spriedzes apraksta pēdiņas pret avotu
- **`scripts/resolve_needs_review.py`** aizstāj ikdienas vienreizējo skriptu (20 tādi `scripts/`): `--list` izdrukā dienas rindas ar avotu, `--decisions` → `--write-rollback` → commit → `--apply`; raksta tikai `claims.reasoning`, atsaka visu partiju, ja rinda nesākas ar marķieri vai rollback nav commitēts. Pārbaude: 11.11. izvērtējuma atkārtojums uz DB kopijas — 18 no 18 `reasoning` sakrīt ar produkciju; 2 testi, 4 mutācijas.
- **`store_tension()` ziņo (stderr, glabā tāpat)** par «…» fragmentu, kas nav burtiski avota vai mērķa dokumentā (`src.support.unverbatim_quotes`; nosaukumi — lielais sākumburts un ≤ 3 vārdi — izlaisti). Mērīts: seši no 12 `@quality-reviewer` spriedžu labojumiem četrās rutīnas dienās (05., 07., 08., 11.11.) bija šī klase; 30 dienās 15 karogi 140 spriedzēs, izlasē 3 no 5 ir locījums, tāpēc atteikuma nav.
- Mērījumi, ielādes laika sadalījums un neieviestais priekšlikums (RSS reizē ar X): `docs/audits/2026-11-12-rutinas-uzlabojumi/README.md`.

## 2026-11-12 — Atradumi: arhīva kopija ar 404 nav pazudusi; UR akcionāru datu kopa slēgta
- **Wayback kopiju, kas atbild 404, nenomaina un neizņem — pieliek otru blakus.** Četras kopijas, kas 08.–11.11. atbildēja 404 ar tukšu CDX, 12.11. atkal atvērās, tāpat 11 no 14 agrāk nomainītajām (`docs/audits/2026-11-12-arhivs/README.md`). Noteikums: `wiki/operations/deploy.md`. Saites rakstos atjaunotas blakus 11.11. kopijām.
- **UR datu kopa `stockholders` vietnē data.gov.lv 12.11. vairs nav publiska** (404; CKAN «Pieeja liegta»). Trijos rakstos un tāfelē piezīme ar atsauci uz Satversmes tiesas 09.11. spriedumu; cēlonību neapgalvojam, saites paliek. Jauniem atradumiem tas neko nemaina (CHANGELOG 2026-11-09 (3)).
- **Pilna avotu pārbaude:** 262 no 272 adresēm atbild 200; 84 lapām mainīts teksts, 76 pamatteksts identisks (`docs/audits/2026-11-12-avoti/README.md`, `check.py` + `retry.py` + `triage.py`).
- Abus labojumus pirms deploy lasīja advisor un Sol; live `f1fa7a28`.

## 2026-11-11 (2) — Balsojumu tēmas: visas partijas piemērotas; Jev neievēro 8. noteikumu nodokļos
- **Piemērots un live** (deploy `b49509f7`): b04–b10, b04k, kor1111 — 4 338 balsojumi, 380 629 pozīcijas snapshotā, visur `collisions=0`, `parity_mismatch=0`; `vote_topics.py status`: ar lēmumu 2 746 no 2 750 (bez lēmuma 4 budžeta likumi, `pending` 863/Lp14). Skaitļi un rollback: `data/saeima_topic_gold/BATCH_LOG.md`.
- **Jev auto nodokļu likumprojektos kļūdās 33/110** (vienas nozares PVN, akcīze, IIN atvieglojums → «Budžets un finanses» pret 8. noteikumu); visi laboti, atlikušie 52 auto ar nodokļu vārdiem izlasīti — 0. Ielādē tas paliek: priekšlikums `pending` nodokļu likumprojektiem — `backlog/saeima.md`.
- **Partijas pārbaudes kārtība** (rīki `docs/audits/2026-11-11-balsojumu-temas/`): pārskatāmie + 20 auto izlase + visi auto nodokļu dokumenti pret avotu; rubrikas piemēri pirms freeze (`rubcheck.py`, 116/116). 7 operatora jautājumi `backlog/saeima.md`.
- **Atradums Višvanati:** HEA reģistra 9. augusta Common Crawl kopija (pārbaudīja Sol un advisor; operatora «jā» 11.11.).
- **Operatora lēmumi (rubrika):** 863/Lp14, 74/P14 → «Budžets un finanses» (kor1111b); grupu nodokļu atvieglojumi, budžeta pārdales, 420/Lp14, 1240/Lp14, 570/Lp14 paliek; precedenti RUBRIKA.md § Operatora lēmumi 2026-11-11, `RUBRIC_VERSION` nemainās (Jev promptā tikai «Ietver»).

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
- Frontmatter `politicians:` (pilni slugi) tagad dod arī saiti + lodziņu PIRMAJAI pieminēšanai tekstā: `link_politicians()` (`src/render/_common/politician_links.py`, `assets/polpop.js`), tests `tests/test_politician_links.py`. Plāns `docs/superpowers/plans/archive/2026-11-01-politiku-lodzini.md`.
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
