# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## Matcher / atribūcija

> Konsolidēts 2026-08-01 — kolīziju darbs bija izkaisīts pa trim sadaļām. Kodā ievieso vārtus tur `scripts/eval_matcher_collisions.py` (FP≤3, zelts≥1260); slēgtie per-gadījumi dzīvo CHANGELOG § 2026-08-01.

### [OPEN] Junction abu virzienu izmeklēšana: fantoma `mentioned` bez vārda tekstā UN pilnvārds tekstā bez junction

Divi spoguļdefekti vienā mehānismā; abiem vajag koda ceļa identifikāciju un lēmumu, vai tas ir apzināts.

**(a) Fantoma virziens — junction bez vārda tekstā.** Stendzenieks (id=60): 296 tvītu doki 90 dienās ar `role='mentioned'` bez „Stendz"/handle tekstā (metode: `dp.role='mentioned' AND content NOT LIKE '%Stendz%'`) — saites rada cits ceļš, visticamāk pieminējumu/atbilžu metadati. 08-06 sweep +5 pierādījumi tai pašai klasei: 65926→Pozņaks(28), 64353→Stendzenieks(60), 60163→Lindberga(184), 55472→Krištopans(9), 35740→Šnore(7); doc 78108 rāda abus virzienus (Krištopans fantoms, nosauktais Šlesers nesaistīts). Vajag mehānisma identifikāciju — kurš koda ceļš raksta `mentioned` no metadatiem. **Sēšanas robs pa ceļam: Lindbergas (id=184) `name_forms` ir TUKŠS `[]`** — operatora review kandidāts.

**(b) Iztrūkstošais virziens — first-party `subject` dokiem NAV mention pass.** Minimālais pāris: doc 80165 (Liepnieka paša tvīts) nesaista tekstā nosaukto Rasimu; doc 80150 (tas pats teksts kā RT pa releja ceļu) saista abus. **Mehānisms APSTIPRINĀTS kodā (08-06):** `src/social.py:92-106` first_party zars nesauc teksta skenējumu; `src/matcher.py:895` noklusētais zars atlasa tikai dokus bez junction rindām, tāpēc autora-saites doks no skenējuma izkrīt uz visiem laikiem. Mērījums 30 d: reģistrēto kontu doki ar mention saitēm first_party 12,7 %, relay 8,5 %, nereģistrētie 84,4 %. Instances: Stepaņenko 8/15, Rajevska 3 doki/6 politiķi/0 saišu, 82146 `@suvajevs`, 82092/82094 `@RaivisZeltits`, 82077 "Raivis Dzintars". **IZPILDĪTS 2026-08-18** (verdikts 08-17): `_link_first_party_mentions()` `src/social.py` — loma cieti `mentioned`, matcher nemainīts, eval vārti nekustējās. **Paliek divi atlikumi:** (i) vēsturiskais backfill (30d novērtējums: 711 doki / 908 rindas, saucējs 3612) — atsevišķs lēmums; (ii) relay-atnests doks ar cross-feed autora `subject` saiti izkrīt no `matcher.py:895` atlases tāpat — tā pati klase pa relay ceļu, verdikts to nesedza.

### [OPEN] T1 locījumu kolīziju klase (2026-08 gadījumi)

**(a) Lāce/Lācis, (b) Uģis Krastiņš un (d) Ceriņš/„ceriņu sfinga" SLĒGTI 2026-08-05** — visas trīs saites dzēstas ar satura pierādījumu + šauri `negative_patterns`; harness FP 1 / zelts 1339; pēda CHANGELOG 2026-08-05, rollback `data/rollback_t1_collisions_lace_krastina_cerins_2026-08-05.sql`.

**Paliek atvērts — sistēmiskais kandidāts:** `scripts/audit_matcher_name_forms.py` sweep pār fem `-e` / masc `-is` pāriem (`_latvian_surname_inflections('Lāce')` dod `Lāci` ≡ `Lācis` akuzatīvs; B2+D2+H šo klasi strukturāli neķer — korekts vārds, korektas robežas — tāpēc tā atkārtosies ar citiem pāriem).

(c) **Daģis (id=81) ↔ Jelgavas mērs — guardi ieviesti 2026-08-04 (CHANGELOG), brīdinājumi paliek:** tie ir divi cilvēki (id=81 = JV deputāts ar 6 473 `faction='JV'` balsojumiem) — **NEPĀRRAKSTI partiju uz „Par!"**; mērs NETIEK sēts (operatora lēmums); doc 79730 ir `reviewed_at`, tāpēc, ja mēru kādreiz iesēj, dokumentu atvērt ar roku.

### [OPEN] 2026-08-15 rutīnas matcher atradumi — sugasvārda kolīzija, RSS sānjosla, nereģistrēts handle

Trīs neatkarīgi atradumi no 38 aģentu ekstrakcijas viļņa; neviens nav labots (visi trīs prasa operatora apstiprinājumu vai koda lēmumu).

**(a) Krasta pid=108 sugasvārda kolīzija — `negative_patterns` IEVIESTI 2026-08-18** (verdikts 08-17; CHANGELOG): 5 paterni (`Krastu mač`, `labā krasta`, `kreisā krasta`, `Daugavas krast`, `Krasta iela`), korpusa mērījums 19 no 85 formu-dokiem noraidīti / 0 kolaterāla uz 23 īstajiem Agneses dokiem; eval vārti nemainīgi (FP 1, zelts 1508 — pid=108 eval komplektos nav pārstāvēts, tāpēc nulles kustība = nav regresijas). `data/{fix,rollback}_krasts_negative_patterns_2026-08-18.sql`. **Paliek divi operatora lēmumi:** (i) `Krasta iela` → stems `Krasta iel` (noraidītu 31/85, ne 19, joprojām 0 kolaterāla; atbilst mājas konvencijai `Vītolu iel`) — verdiktā bija burtiskā forma, paplašinājums prasa savu JĀ; (ii) 5 esošās `document_politicians` rindas, kas tagad trāpa paterniem (55065, 55071, 87609, 87873, 88350 — visas `subject`, 0 claims), paliek DB — tīrīšanai atsevišķs verdikts + rollback. Klase atkārtojas ik gadu («Krastu mačs» 17. sezona; arī doc 88350 08-16).

**(b) diena.lv RSS ievāc saistīto virsrakstu sānjoslu → viltus `subject`.** Doc **87866** ir laika prognozes raksts, kurā Rinkēviča vārds parādās TIKAI navigācijas blokā ar saistītajiem virsrakstiem, tomēr junction rinda ir `subject`. Tā nav namesake kolīzija, tāpēc `negative_patterns` te neder — sakne ir skrāpēšanas satura robeža (RSS ceļš ievāc lapas sānjoslu kopā ar korpusu). Radniecīgs § Avoti truncated klasei, bet pretējā virzienā: te korpusā ir par daudz, ne par maz. Ja klase atkārtojas, lēmums ir `_clean_extracted_text` / trafilatura robežu pastiprināšana, ne matcher.

**(c) `@Krisjanis_K` — SLĒGTS 2026-08-17;** konvencija → § Ne-darīt.

**(d) `platform` nav autorības pierādījums (piezīme, ne defekts).** Doc **88328** ir `platform='x_mention'`, lai gan tas ir Kulberga paša tvīts no `@AndrisKulbergs` (`feed_type='first_party'`) — ienācis caur pieminējumu ceļu, jo atzīmē izsekotus organizāciju kontus. Ekstrakcijas aģents autorību pareizi pārbaudīja pret `source_url` + `social_accounts`, ne pret `platform`. Nākamajam lasītājam `x_mention` var likties trešās puses dokuments; ja kāds būvē heiristiku uz `platform`, šī ir tā slazda vieta.

### [OPEN] 2026-08-16 rutīnas matcher atradumi — trīs kolīzijas, viena atkārtojoša

Trīs neatkarīgi gadījumi no 57 aģentu viļņa; neviens nav labots (visi prasa operatora `negative_patterns` lēmumu).

**(a) Krasta (pid=108) — SLĒGTS 2026-08-18, sk. § 2026-08-15 (a)** (paterni ievesti; doc 88350 bija otrā instance, kas klasi pierādīja kā atkārtojošu).

**(b) Liepiņa (pid=107) — SLĒGTS 2026-08-18** (4 paterni abām apakšklasēm: `"Liepiņa"`, `"Liepiņas"`, `Aldis Liepiņš`, `A. Liepiņa`; 6/168 kolīziju doku noraidīti, 0 kolaterāla uz 79 īstajiem; eval vārti identiski FP 1 / zelts 1508; `data/{fix,rollback}_liepina_negative_patterns_2026-08-18.sql`; CHANGELOG). **Paliek trīs blakuskarogi (operatora lēmumi):** (i) VECIE paterni paši maksā 3 īstus Lindas dokus (33417, 54279 — `Korupcijas novēršanas…`; 34376 — `izsludināta par mirušu`) — pārskatīšanas kandidāts; (ii) ~85 doku virsma ar CITIEM Liepiņiem (Sanda 19, Zaiga 17, Modris 13, Jānis 9, Kristīne 6 u.c.) — pilnvārdu paternu verdikts atsevišķi, katram ko-okurences pārbaude ar Lindu; (iii) 6 esošās junction rindas paliek DB (88353, 89005, 20944, 69298, 74346, 50651; 0 claims) — tīrīšanai atsevišķs verdikts kā Krastai.

**(c) NBS (pid=204) — TREŠĀ klase blakus jau zināmajām divām.** Līdz šim pierakstītas: amata-apzīmējuma klase (Slaidiņš) un CVK programmu leakage. Doc 88352 (LSM par «Baltic Trust 26») nav ne viena, ne otra: «NBS» tekstā ir **tieši vienu reizi** un kā cita teikuma objekts — *«Savas tehnoloģijas sazobē ar NBS un sabiedroto karavīriem testē arī vairāki vietējie uzņēmumi»* —, bet visi četri citētie runātāji ir NATO vai industrijas pārstāvji. Simptoms cits, sekas identiskas: viens atslēgvārds → slots → tukšs doks.

**Kontrastam, kas NAV kolīzija:** doc 88818 tajā pašā dienā piesaistīja Valsts kontroli (pid=241) pareizi — tekstā ir Latvijas VK, tikai kā žurnālista retrospektīva atsauce uz ~2022. gada revīziju, ne kā runātājs. Institūcijas slots dabiski saņem šādus rakstus; ja katru no tiem skaitītu par matcher defektu, `negative_patterns` sāktu graut īstos trāpījumus.

### [OPEN] Ārvalstu revīzijas iestādes sasaistās ar Valsts kontroli (id=241)
2026-07-31 seed rescan: 336 sasaistēs 2 bija kļūdainas — "Spānijas Valsts kontrole" (doc 36152) un "Krievijas Valsts kontroles jeb Skaitīšanas palātas" (doc 50888), abas noņemtas ar `data/fix_vk_foreign_audit_junctions_2026-07-31.sql`. Sakne: matcher daudzvārdu formas ir tīri substringi, tāpēc `<Valsts>ijas Valsts kontrole` satur formu. `negative_patterns` neder — tie noraidītu VISU dokumentu, un tad pazustu doc 20494 (PROVIDUS raksts ar 10 tiešām LV VK atsaucēm blakus Somijas/Igaunijas piemēriem). Pareizais risinājums būtu formas līmeņa prefiksa veto (ģenitīva ģeonīms tieši pirms daudzvārdu formas) `src/matcher.py::_occurrences` blakus D2 vārdu-robežu logikai. Līdz tam — periodiska pārbaude ar `grep -E '\w+(as|ijas) Valsts [Kk]ontrol'` pār jaunajām VK sasaistēm.

### [OPEN] Bērziņš false-link — monitorings, ne kampaņa

**Andris Bērziņš (id=146, ZZS)** ķer pilnvārda dvīņus, un pilns vārds sakrīt, tāpēc `negative_patterns` pa uzvārdu nepalīdz — der tikai konteksta kolokācijas; divas no trim klasēm ir slēgtas („Latvijas Ceļu būvētājs" vadītājs doc 62139 — 2026-07-27; aktieris doc 74402 — 2026-07-29, harness FP 2→1; pieraksts CHANGELOG 2026-07-27 un 2026-07-29). **Paliek atvērta un ir string-NEATRISINĀMA dziedātāja klase (doc 64681)** — vārds tur ir tikai solistu uzskaitījumā bez profesijas vārda blakus, tāpēc neviens virkņu līmeņa guard to neķer. Rīcība: neko nebūvē, agrīnā pamanīšana = `/audit-integrity` 1b B2-veto žurnāls; mērījums un plāns `docs/plans/2026-07-27-matcher-koliziju-plans.md`.

### [OPEN] NBS pid=204 keyword subject-leakage uz CVK programmu dokiem — partiju programmu darba palieka
Konteksts: partiju 2026 programmas pabeigtas 14/14 (07-08/07-09, ieskaitot „Solījumu kartes" sintēzi un lapas redesign; vēsture CHANGELOG + git). Atlikusī palieka: matcher CVK programmu dokiem liek pid=204 „Latvijas armija (NBS)" kā `subject` (keyword-org uz programmas tekstu; novērots 07-04 un atkārtoti 07-06 uz doc 64220) — subject-leakage klase, operatora review (negative_patterns vai keyword-org izņēmums programmu platformas dokiem). Amata-apzīmējuma apakšklase (Slaidiņš) ir atsevišķs ieraksts sadaļā § Aģenti / pipeline. Atkārtotai programmu ielādei: plūsma dokumentēta CLAUDE.md Datu kontraktā #4a; `ingest_url.py` ar .venv python; NEpadod `db=` — `store_claim` commit tikai owns_connection ceļā.

**Ziņu plūsmas puse SLĒGTA 2026-08-18** (verdikts 08-17; CHANGELOG): CVK domēnu dokumenti izslēgti `src/render/news.py` renderī ar `_is_cvk_domain()` (domēna, ne virsraksta kritērijs — CVK `<title>` mainās katru ciklu), dokumenti un junction rindas DB paliek. Šīs sadaļas atlikums ir tikai augšējais keyword-org `subject`-leakage jautājums (pid=204 uz programmu dokiem).

### [OPEN] Deep-check 2026-08-17 blakus atradumi — 9 claim/datu karogi

Atrasti `/deep-check` skrējienā (6 politiķi, 0 apstiprinātu pretrunu). **Gandrīz viss izpildīts 2026-08-18** (CHANGELOG): #20557 + #689627 stance, T4 kvartets #6954/#7019/#7022/#7397 diakritika (§ Citātu integritātes (b)), abi izpildes blakuskarogi (#6954 „ārzemniekiem" izņemts + re-embed, #7397 `NEEDS_REVIEW: ` marķieris) un #6658/#7043 dublikāts (dedup 3 grupas). #20597 (Švinka) karogs ATSAUKTS — sk. § 2026-08-15 rutīnas datu defekti (a); Vītola `relationship_type` → § Ne-darīt. **Atvērts paliek viens:**

- **#555726 (Valainis) citēšanas brīdinājums — IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): MK protokols Nr. 40 (27. §, 26-TA-1067) 14 milj. EUR **nepiešķir** — brīdinājums ierakstīts claim `reasoning` (`data/{fix,rollback}_claim555726_citation_note_2026-08-21.sql`); pārskatiem jācitē ar atrunu.

### [OPEN] Junction lomas apgrieztas LETA pārstāstos — `mentioned` runātājs nekad nenonāk ekstrakcijas rindā

- **Sakne (doc 78085, 2026-08-01):** LETA-pārstāstā vienīgais runātājs ir `mentioned`, un ekstrakcijas rinda iet tikai pa `role='subject'` → runātāja pozīcija nekad nenonāk rindā; nav LETA-specifiska klase, bet vispārīga LV ziņu uzbūve (CHANGELOG arhīvs 2026-08-02). `reviewed_at` per-dokuments semantika zudumu maskē (kopš 2026-08-09 CLAUDE.md § Schema invariants).
- **Rīks un mērogs — lieto rīku, ne pierakstīto procentu:** `scripts/audit_junction_role_inversion.py` + `/audit-integrity` 15. pārbaude; nominatīva forma ≤60 zīmes no citēšanas signāla, inversija = `mentioned` runā, neviens `subject` nerunā (naivā „visas formas" versija doc 78085 nepamana; 13 testi). Bāzlīnija 08-05: `checked=1288 flagged=263` (20,4 %); ~271 īsts zudums, ~1,4 doki dienā, ~92 % precizitāte.
- **Lēmums 2026-08-04: kandidāts (b) + backfill; plāna 1.–5. solis IEVIESTS** (`729aa27e`, dizains `docs/plans/2026-08-04-junction-inversion-queue-fix.md`). **1. vilnis 08-05** (8 claims #689187–#689194) un **2. vilnis 08-06** (5 claims #689250–#689254, rindā 339) izpildīti — pilnie pieraksti CHANGELOG 2026-08-05/06. **Detektora FP/empty klases nākamajiem viļņiem:** viens neizsekots komentētājs par daudziem politiķiem (klasterēti FP pa vienu doku — 76612); pasīvais saturs (`TIEK apsvērts` bez nostājas — 76611); cita medija pārpublicēts citāts ar divu lēcienu provenanci (73172); cross-source verbatim dublikāti (lielākais empty cēlonis).
- **Paliek 6. soļa turpinājums:** partijas pa ≤12 pāriem no `pending_quoted_mentioned(db, days=90)`, atsevišķi no dienas rutīnas. Nākamie mērķi: doc 76625 Rinkēvičs; Kulberga kokrūpnieku web trio 71412/71395/71371 (visos `mentioned`, 0 pid=10 claims — pozīcija DB tikai no X #553970, web provenance nav); doc 72401 Rokpelnis (`subject`, 0 claims) + 6 līdziesniedzēji `mentioned` (74, 109, 89, 73, 145, 162).

- **2026-08-16 mērījums: klase ir smagāka, nekā ~1,4 doku/dienā liek domāt.** Vienā rutīnas dienā ar roku pārbaudīti ~10 kandidāti un atgūtas **6 pozīcijas no 4 dokumentiem**, kur runātājs bija `mentioned`. Divi gadījumi ir ekstrēmi: **doc 88345** (KNAB sižets) nesa 4 pozīcijas, no kurām rindā nonāca **viena** — Kulbergs ×2 (#689701 par KNAB vadītāja vakanci, #689702) un Latkovskis (#689703) būtu zuduši klusi; **doc 88820** (airBaltic) Kulbergs ir raksta GALVENAIS runātājs, arī virsrakstā, bet junction lomā `mentioned` — no tā nāca #689710, dienas augstākā salience (0,85). Vēl divi: Citskovskis #689711, Dombrava #689712, NBS #689713.
  - **Ekspozīcijas vaicājums (atkārtojams):** sodien zīmogotie web doki, kuros kāds tracked politiķis ir `mentioned` un no tā dokumenta viņam nav neviena claim → 2026-08-16 deva **26 pārus pār 10 dokiem, saucējs 18 web doku**. Lielākā daļa ir īsti pieminējumi; trāpījumu īpatsvars starp pārbaudītajiem bija ~3 no 10.
  - **Procedūras mācība atgūšanas aģentiem:** padod dokumenta ID un liec LASĪT, nekad nepadod satura kopsavilkumu izpildei. Trīs reizes no trim nodotais apraksts izrādījās nepilnīgs — Latkovskim trūka divu rindkopu, Kulbergam trīs (t.sk. kvalifikatora, ka maksātnespēja **paliek** kā variants), Citskovskim visa sistēmiskā prasība par Kārtības ruļļa grozījumiem.

### [OPEN] Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts

Substring-defekts (`raksta` iekš `saraksta`, doc 80038 klase) SLĒGTS 2026-08-05 — signāli vārda sākumā + pilnais teksts (`src/quoted_speaker.py`, 3 regresijas testi); bāzlīnija pēc fiksa 1288/263. Paliek nemērīts kandidāts: **bezpersonisko atribūciju veto** — `teikts … programmā/paziņojumā` citē dokumentu, ne cilvēku, tāpēc tuvumā esošs nominatīvs nav runātājs. Pirms ieviešanas izmērīt biežumu ar audita rīku.

### [OPERATOR] `NEEDS_REVIEW` rinda: paliek 6 kodola lēmumi (+ dienas jaunie karogi)

**Infrastruktūra SLĒGTA 2026-08-03:** `claims.review_status` — atvasināta kolonna ar diviem trigeriem; vaicājumi neparsē tekstu (rollback `data/rollback_claims_review_status_2026-08-03.sql`).

**Stāvoklis 2026-08-12: rinda TUKŠA** — `SELECT COUNT(*) FROM claims WHERE review_status='needs_review'` = 0 (skaitlis kustas ar katru ekstrakciju — lieto vaicājumu). Vēsturisko triāžu pēdas: 08-05 60 rindas (`data/{fix,rollback}_needs_review_*_2026-08-05.sql`), reputācijas trio 08-09 (CHANGELOG (5)), 08-11 94→33, 08-12 fināls trīs partijās — #689359/#689387/#689307 dzēsti, #689485 stance+re-embed (`rollback_nr_triage_grp3_grp6_2026-08-11.sql`, `rollback_nbs_slots_lemums_2026-08-12.sql`, `rollback_nr_triage_final19_2026-08-12.sql`).

**Paliek konvencija:** atvērto rindu triāža = strukturēts nedēļas rutīnas bloks (keep/fix/delete ar ieteikumu), ne ad-hoc (operatora lēmums 2026-08-04). `@quality-reviewer` Pass criteria jau satur 14 dienu vārtu — nepiedāvā vēlreiz. Marķiera forma ir kosmētika: `Izvērtēts`/`REVIEWED`/`IZSKATĪTS` visas atvasinās uz `reviewed`.

