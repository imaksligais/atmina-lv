# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Matcher / atribūcija

> Konsolidēts 2026-08-01 — kolīziju darbs bija izkaisīts pa trim sadaļām. Kodā ievieso vārtus tur `scripts/eval_matcher_collisions.py` (FP≤3, zelts≥1260); slēgtie per-gadījumi dzīvo CHANGELOG § 2026-08-01.

### [OPEN] Stale junction atlikums — 52 rindas bez vārda tekstā, 28 vēlākas piesaistes; twitter un x_mention nav auditēti (2026-11-10)

Apakšvirknes klase web dokos slēgta. `scripts/audit_stale_politician_links.py` 2026-11-10: 13 799 doki pārbaudīti, 647 rindas saistītājs vairs neradītu, no tām 244 «teksts nepamato», **DEFEKTI 0**. Izdarīts 2026-11-10 (verdikti 15 un 16; `data/rollback_verdikti_15_junction_2026-11-10.sql`, `data/rollback_verdikti_15_reload_2026-11-10.sql`, `data/rollback_verdikti_16_rajevs_2026-11-10.sql`): 35 `teksts_nomainits` rindām `suspect_at` (visas 81 tagad karogotas), 7 organizāciju saites CVK programmu lapās dzēstas, 86 pid 121 saites no «@Rajevskis» dzēstas. Paliek:

- **(1) `varda_nav_tekstā` — 52 rindas / 25 doki (mērījums pirms pārlādes).** Pārlāde gandrīz nepalīdz: `backfill_truncated_docs.py` 2026-11-10 atjaunoja 2 dokus (90333, 95768); 15 nav garāki, 1 avots atbild 404, 1 ir tiešraide (netiek pārrakstīta), 6 nav web. *Rīcība:* izlasīt; nekad nedzēst uz klasifikatora vārda (T19).
- **(2) `piesaiste_velak` — 28 rindas / 27 doki.** *Rīcība:* noskaidrot, kurš koda ceļš tās raksta.
- **(3) Audits izlaiž `twitter` un `x_mention`** (`SKIP_PLATFORMS`), tāpēc 86 Rajeva rindas tas neredzēja. *Rīcība:* tāds pats salīdzinājums šīm platformām tikai `mentioned` lomai (subjekts tur nāk no autora); izlasi lasīt pirms dzēšanas (T18). **Izmērīts 2026-11-10** (`docs/audits/2026-11-10-merijumi/` § 1): 29 580 `mentioned` rindas, 1 731 saistītājs vairs neradītu, lielākoties pēc noteikumiem (retvīti C4, vecās D5 saites, institūcijas). Atlikums: izlasīt 8 DEFEKTI rindas; 545 vecajām saitēm `suspect_at` vai lasīt katru. **Skripta kļūda:** `audit_stale_politician_links.py::forms_by_pid` skaita `negative_patterns` kā vārda formas, tāpēc 10.11. web skaitļi ir apšaubāmi.

*Īpašnieks:* koda darbs (3), operators (1, 2).

### [OPEN] Releja kanāla dokuments ar citā plūsmā piesaistītu autoru (`subject`) netiek pārbaudīts pieminējumu meklēšanā

Agrāk «Junction abu virzienu izmeklēšana» (divi spoguļdefekti vienā mehānismā). Pilnais naratīvs ar instanču vēsturi: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

**(b) Iztrūkstošais virziens — first-party `subject` dokiem nebija mention pass.** IZPILDĪTS 2026-08-18 (`_link_first_party_mentions()` `src/social.py`, loma cieti `mentioned`; `aa379211`); vēsturiskais backfill 2026-10-01 (CHANGELOG 2026-10-01 (2)). **Paliek atlikums:** relay-atnests doks ar cross-feed autora `subject` saiti izkrīt no `matcher.py:895` atlases tāpat — tā pati klase pa relay ceļu, verdikts to nesedza.

_(a) Fantoma `mentioned` (svešs tvīts laika joslā) — IZPILDĪTS, CHANGELOG 2026-10-14 (15)–(16)._

### [OPERATOR] Junction lomas apgrieztas pārstāstos — `mentioned` runātājs nesasniedz rindu

**2026-10-14 (verdikti):** (1) instances demotētas (120049, 120019, 120708/684/676, 124194, 124250, 129930, 125359, 126705, 127368; 123460 Valainis → `mentioned`); 120749 — pid 200 jau `mentioned`; 127358 Kulbergs → `subject`. `data/rollback_verdikti_h1_2026-10-14.sql`. Paliek (3).

> **Stāvoklis.** Klase ir **viens dizaina lēmums**: `role='subject'` tiek piešķirta pēc vārda klātbūtnes tekstā, ne pēc runas akta. Kopš 2026-09-07 `src/roles.py` ir vienīgais īpašnieks jautājumam, kurš drīkst nest `subject` (abi bulk-rakstītāji iet caur to); releja mediju sloti (`organization` + `relay`) un @Brivibas36 kailie retvīti `subject` vairs nerada (`tests/test_subject_role_guards.py`; CHANGELOG 2026-09-07 (7)). (2) LETA apakšpunkts SLĒGTS 2026-09-07. Vēsturiskās 3 027 rindas demotētas 2026-09-06 (CHANGELOG arhīvs 2026-09-06 (2); `data/fix_grupaE_subject_demote_*`). Spoguļa klase § Junction abu virzienu ar nolūku NAV apvienota — cits mehānisms un cits saucējs. **Cena:** `reviewed_at` ir per-DOKUMENTS, tāpēc nepareizs `subject` aizver dokumentu arī īstajiem runātājiem (CLAUDE.md § Schema invariants). Pilnais naratīvs: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

**(1) `subject` lomas inflācija personām — vispārīgais noteikums NAV ieviests (verdikts A1, 2026-10-01).** Mērījums: `speaks()` apstiprina tikai 84,3 % claim-ražojošo web `subject` pāru (1 492/1 770); variants «nomainīt, ja runā cits» 93,9 % (< 97 % vārti). Reālos runātājus jau atgūst rutīnas citētā runātāja josla (`quoted_speaker.recovery_survey`). 9 zināmās instances demotētas (`data/rollback_subject_inflation_9_2026-10-01.sql`); 384 atturētās rindas ievietotas kā `mentioned` (`data/rollback_held_subject_as_mentioned_2026-10-01.sql`).
**(3) Junction lomas apgrieztas pārstāstos — `mentioned` runātājs nekad nenonāk ekstrakcijas rindā.** Sakne doc 78085: rinda iet tikai pa `role='subject'`; tā ir vispārīga LV ziņu uzbūve, ne LETA klase. 09-07 vārts demotē bez paaugstināšanas, tāpēc 962 dokos, kur relejs bija vienīgais subjekts, citētie runātāji joprojām nav sasniedzami.

- **Rīks — lieto to, ne pierakstīto procentu:** `scripts/audit_junction_role_inversion.py` + `/audit-integrity` 15. pārbaude (bāzlīnija 2026-09-25, 90 d: `checked=2635 flagged=270`).
- **Lēmums 2026-08-04: (b) + backfill, 1.–5. solis ieviests** (`729aa27e`, `docs/plans/2026-08-04-junction-inversion-queue-fix.md`); viļņi 08-05 un 08-06 izpildīti (CHANGELOG arhīvs 2026-08-05/06). 2026-08-16 vienā dienā atgūtas 6 pozīcijas no 4 dokiem (88345, 88820) — klase ir smagāka, nekā ~1,4 doku dienā liek domāt.
- **Atvērts — 6. soļa turpinājums:** partijas pa ≤12 pāriem no `pending_quoted_mentioned(db, days=90)`, atsevišķi no dienas rutīnas. Nākamie mērķi: doc 76625 Rinkēvičs; Kulberga kokrūpnieku web trio 71412/71395/71371 (visos `mentioned`, 0 pid=10 claims); doc 72401 Rokpelnis (`subject`, 0 claims) + 6 līdziesniedzēji `mentioned` (74, 109, 89, 73, 145, 162).
- **Instances no handoffiem 10-05…10-09:** Rinkēvičs `mentioned` 121897 un 126730; Abu Meri `mentioned` 125775/125808/125829, kaut raksts ir par viņu; Pujāts (pid 246) `mentioned` 4 dokos, kur runā pats; Latkovskis doc 115440 `extracted_at` NULL; 80 politiķi, kurus 2026-09-23 pazemināja uz `mentioned`, nav atgūti.
- **Detektora FP/empty klases:** neizsekots komentētājs par daudziem politiķiem (76612); pasīvais saturs bez nostājas (76611); divu lēcienu pārpublicēts citāts (73172); cross-source verbatim dublikāti (lielākais empty cēlonis).
- **Ekspozīcijas vaicājums:** šodien zīmogotie web doki, kuros tracked politiķis ir `mentioned` un viņam no tā doka nav claim (08-16: 26 pāri pār 10 dokiem, trāpījumi ~3 no 10).
- **Procedūra atgūšanas aģentiem:** padod dokumenta ID un liec LASĪT, nekad nepadod satura kopsavilkumu — trīs reizes no trim nodotais apraksts bija nepilnīgs.
- **Blakus klase ārpus verdikta tvēruma:** `feed_type='relay'` ir arī 7 žurnālistiem un 6 neaktīvām personām. Lapsa (pid=57) nes 3 219 twitter `subject` rindas no kailiem RT ar `@Lato_Lapsa` (atbildes viņam, ne viņa runa). Vārta paplašināšana uz jebkuru `relay` kontu ir viena rinda `scope.relay_media_pids()` vietā; cena — šo žurnālistu profila X apakšcilne pārstāj papildināties. **IZPILDĪTS 2026-11-03 (verdikts 9):** lētais variants — `_QUEUE_POLITICIAN_TEMPLATE` izslēdz `journalist`+`relay` tikai `twitter`/`x_mention` dokiem; `relay_media_pids()` nemainīts, web viedokļraksta izņēmums paliek (`tests/test_scope_journalist.py`; tobrīd rindā 0 skartu pāru). Stenogrammu 657 `mentioned` — atstāt (operators). **Mērījums 2026-10-05** (backloga sweep): Lapsas 99 rindas `subject` pāri → 0 pozīciju (visi aģenti: «relay konts nekad nav runātājs»), ~6 aģentu darbs veltīgi. Variants ar mazāku cenu: paplašināt tikai rindas predikātu `src/scope.py::_QUEUE_POLITICIAN_TEMPLATE` uz `journalist`+`relay` (ne `relay_media_pids()`, ko lasa arī junction rakstītājs) — X apakšcilne nemainās, jo tā lasa junction bez šī predikāta; zaudē tikai parakstīta viedokļraksta izņēmumu (`sloti.md`), ko var atstāt `web` platformai.

**2026-10-21 (7):** stenogrammās 657 esoši runātāju pāri joprojām `mentioned` (jaunie kopš 10-21 — `subject`). Paaugstināt? UPDATE ierakstītu 657 apspiešanas ar `reason='auto-demote'` — vispirms izvēlēties ceļu. Noklusējums: atstāt.

### [OPERATOR] Matcher plāna 2026-07-27 atlikums (B2+D2+H ieviests)

Plāns `docs/plans/2026-07-27-matcher-koliziju-plans.md`. Paliek: (a) IZPILDĪTS 2026-11-10 — § 6 nosauktās 11 saites jau bija dzēstas, Rajeva klases atlikums (86) dzēsts (§ Stale junction atlikums); (b) vīriešu -a uzvārdu datīvi — ģeneratorā NEtaisa (2026-11-03): tas dzimumu nezina, un -am visiem -a uzvārdiem kolidētu ar vīriešu -š datīvu (Siliņa→«Siliņam» = Siliņš); -e zars jau dod abus (Krauzem), Putra/Dombrava/Švinka formas DB jau ir. Trūkstošās pievienotas 2026-11-03 ar operatora «jā» (`data/fix_name_forms_datives_2026-11-03.sql`; Lapsai tikai «Lato Lapsam»); (c) title skenēšanas 2. fāze (§ 5 7. solis, pilnvārda vārti, loma `mentioned`). Bērziņa pilnvārda dvīņi — neatrisināma klase. *Īpašnieks:* operators.

### [OPEN] T1 locījumu kolīziju klase (2026-08 gadījumi)

**(a) Lāce/Lācis, (b) Uģis Krastiņš un (d) Ceriņš/„ceriņu sfinga" SLĒGTI 2026-08-05** — visas trīs saites dzēstas ar satura pierādījumu + šauri `negative_patterns`; harness FP 1 / zelts 1339; pēda CHANGELOG 2026-08-05, rollback `data/rollback_t1_collisions_lace_krastina_cerins_2026-08-05.sql`.

**Paliek atvērts — sistēmiskais kandidāts:** `scripts/audit_matcher_name_forms.py` sweep pār fem `-e` / masc `-is` pāriem (`_latvian_surname_inflections('Lāce')` dod `Lāci` ≡ `Lācis` akuzatīvs; B2+D2+H šo klasi strukturāli neķer — korekts vārds, korektas robežas — tāpēc tā atkārtosies ar citiem pāriem). **Saucējs 2026-09-25:** `_latvian_surname_inflections` pār visiem ne-organizāciju `-e` uzvārdiem — **28 no 28** ģenerē `X-i`, kas ir `X-is` akuzatīvs (Lāci/Lācis, Pūci/Pūcis, Zīli/Zīlis, Priedi/Priedis, Kalnieti/Kalnietis…); sweep skriptā nav (`grep -n "pair\|masc" scripts/audit_matcher_name_forms.py` → nekā). *Rīcība:* sweep = korpusā skaitīt `X-i` trāpījumus, kuru tuvumā ir vīriešu priekšvārds, un tikai tad lemt par kodu. *Īpašnieks:* operators. Daģa (id=81) brīdinājumi pārcelti uz `wiki/operations/seeding.md`.

**2026-10-23 vēl viens gadījums:** «Lāci» (lietvārda *lācis* akuzatīvs) piesaistīja pid 158 Lāci rakstam par lāča nošaušanu (doc 140598) — saite dzēsta ar aizliegumu, rollback `data/rollback_lace_lacis_140598_2026-10-23.sql`. Tā pati `-e`/`-is` klase, bet ar sugasvārdu, ne cilvēku — `negative_patterns` neder, sweep jāskaita arī šis.
### [OPERATOR] Lūša ≤4 zīmju formas (T1) — `Lūsi` dala arī pid 206 Lūse

**2026-10-14 (verdikti):** pid 206 `negative_patterns` = 6 formas ieviestas; cena: nākamais rescan atmetīs 50079 (Lūse + Viesturs Lūsis, `mentioned`, 0 claims — INSERT rollback galvā). Paliek: ≤4 formas pie reaktivācijas.

pid=174 Toms Lūsis: `_latvian_surname_inflections('Lūsis')` ≤4 zīmēm → `['Lūsi', 'Lūša']` — apakšvirkņu bumbas (CLAUDE.md § Īsās ģenerētās formas). Slots ir `inactive` (`name_forms='[]'`), tāpēc šodienas cena ir zema, bet reaktivācija to uzreiz paceltu. `Lūsi` ģenerē arī pid 206 Mairita Lūse (arī `inactive`) — reaktivējot jebkuru no abiem, forma kolidē starp diviem izsekotiem cilvēkiem. *Rīcība:* karogot operatora izskatīšanai, nekad neauto-noņemt. *Īpašnieks:* operators. **2026-10-05:** Lūse (206) atkal `tracked` (15. Saeima); 6 svešas saites dzēstas (`data/rollback_fix_links_2026-10-05b.sql`: Toms Lūsis ×4, «Lūsija», «T. Lūse»).

### [OPEN] Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts

Substring-defekts (`raksta` iekš `saraksta`) slēgts 2026-08-05. Paliek kandidāts **bezpersonisko atribūciju veto**: `teikts … programmā/paziņojumā` citē dokumentu, ne cilvēku, tāpēc tuvumā esošs nominatīvs nav runātājs (`grep -n "programm\|paziņojum" src/quoted_speaker.py` → veto nav). Pirmais saucējs 2026-09-25: web doki 90 d = **7 933**, no tiem ar regex `teikts … (programmā|paziņojumā|dokumentā|ziņojumā|vēstulē)` = **193** (2,4 %). *Nākamais solis:* krustot 193 ar `audit_junction_role_inversion.py` karogiem (270), tad lemt par veto. *Īpašnieks:* operators.

**Otrs robs (2026-10-11):** `recovery_survey` nepamana runātāju bez nominatīva blakus («pauda ministrs» — Smiltēns doc 131912, pievienots ar roku).

### [OPERATOR] Četri VAD vajadzībām iesēti `negative_patterns` paterni aizliedz ziņas — pārcelt uz `vad_negative_patterns` (2026-11-10)

Kolonna `tracked_politicians.vad_negative_patterns` ieviesta 2026-11-10 (CHANGELOG 2026-11-10 (1)): VAD filtrs lasa abas kolonnas, ziņu matcher tikai `negative_patterns`. Glabātās vērtības nav pārvietotas.

- **Mērījums 2026-11-10** (read-only; 69 384 doki ar `scraped_at` pēdējās 90 dienās; 51 politiķis, 242 paterni, 142 bez neviena trāpījuma): četri paterni, ko VAD vajadzībām iesēja `scripts/seed_homonimu_disambig.py` un `seed_homonimu_phase2_disambig.py`, aizliedz ziņu dokus, kuros politiķis nosaukts pilnā vārdā — pid 104 «Finanšu ministrija» 6 no 24, pid 137 «Valsts policija» 4 no 26, pid 132 «Tieslietu ministrija» 4 no 11, pid 101 «Tiesu administrācija» 1 no 9. Vēl 8 iesētie paterni (pid 81, 101, 104, 116, 132, 158) 90 dienās neaizliedz nevienu. Klasifikatora iznākums, ne darba saraksts (T18).
- **Rīcība:** izlasīt 15 aizliegtos dokus; ja tie ir par politiķi — 12 iesētos paternus pārcelt uz `vad_negative_patterns` ar pāra rollback un pārskenēt skartos dokus. **Izlasīts 2026-11-10** (`docs/audits/2026-11-10-merijumi/` § 2): visi 15 doki ir par īsto politiķi. Ieteikums: pārcelt 11 no 12 paterniem, pid 81 Jelgavas paternu atstāt. Lēmums ir operatora.
- **Īpašnieks:** operators (`negative_patterns` vērtības bez operatora nemaina).
