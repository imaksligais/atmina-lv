# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Matcher / atribūcija

> Konsolidēts 2026-08-01 — kolīziju darbs bija izkaisīts pa trim sadaļām. Kodā ievieso vārtus tur `scripts/eval_matcher_collisions.py` (FP≤3, zelts≥1260); slēgtie per-gadījumi dzīvo CHANGELOG § 2026-08-01.

### [OPEN] Junction abu virzienu izmeklēšana: fantoma `mentioned` bez vārda tekstā UN pilnvārds tekstā bez junction

Divi spoguļdefekti vienā mehānismā; abiem vajag koda ceļa identifikāciju un lēmumu, vai tas ir apzināts.

**(a) Fantoma virziens — junction bez vārda tekstā.** Stendzenieks (id=60): 296 tvītu doki 90 dienās ar `role='mentioned'` bez „Stendz"/handle tekstā (metode: `dp.role='mentioned' AND content NOT LIKE '%Stendz%'`) — saites rada cits ceļš, visticamāk pieminējumu/atbilžu metadati. 08-06 sweep +5 pierādījumi tai pašai klasei: 65926→Pozņaks(28), 64353→Stendzenieks(60), 60163→Lindberga(184), 55472→Krištopans(9), 35740→Šnore(7); doc 78108 rāda abus virzienus (Krištopans fantoms, nosauktais Šlesers nesaistīts). Vajag mehānisma identifikāciju — kurš koda ceļš raksta `mentioned` no metadatiem. (Tukšo `name_forms` klase šeit vairs nedzīvo — Lindbergai id=184 šodien ir 5 formas, un pārējo 30 rindu ASCII variantu priekšlikums gaida operatora apstiprinājumu: `data/proposed_name_forms_2026-09-07.md`, CHANGELOG 2026-09-07 (6).)

**(b) Iztrūkstošais virziens — first-party `subject` dokiem NAV mention pass.** Minimālais pāris: doc 80165 (Liepnieka paša tvīts) nesaista tekstā nosaukto Rasimu; doc 80150 (tas pats teksts kā RT pa releja ceļu) saista abus. **Mehānisms APSTIPRINĀTS kodā (08-06):** `src/social.py:92-106` first_party zars nesauc teksta skenējumu; `src/matcher.py:895` noklusētais zars atlasa tikai dokus bez junction rindām, tāpēc autora-saites doks no skenējuma izkrīt uz visiem laikiem. Mērījums 30 d: reģistrēto kontu doki ar mention saitēm first_party 12,7 %, relay 8,5 %, nereģistrētie 84,4 %. Instances: Stepaņenko 8/15, Rajevska 3 doki/6 politiķi/0 saišu, 82146 `@suvajevs`, 82092/82094 `@RaivisZeltits`, 82077 "Raivis Dzintars". **IZPILDĪTS 2026-08-18** (verdikts 08-17): `_link_first_party_mentions()` `src/social.py` — loma cieti `mentioned`, matcher nemainīts, eval vārti nekustējās. **Paliek divi atlikumi:** (i) vēsturiskais backfill (30d novērtējums: 711 doki / 908 rindas, saucējs 3612) — atsevišķs lēmums; (ii) relay-atnests doks ar cross-feed autora `subject` saiti izkrīt no `matcher.py:895` atlases tāpat — tā pati klase pa relay ceļu, verdikts to nesedza.

### [OPERATOR] «`subject`» lomai vajag runātāja pierādījumu — palikušas divas instances no trim

> **Trīs ieraksti apvienoti 2026-09-05**; **(2) LETA apakšpunkts SLĒGTS 2026-09-07** (verdikti 36 + 38, CHANGELOG 2026-09-07 (7)). Klase joprojām ir **viens dizaina lēmums**: `role='subject'` tiek piešķirta pēc vārda klātbūtnes tekstā, ne pēc runas akta. Kas 09-07 mainījās — jauns modulis `src/roles.py` ir vienīgais īpašnieks jautājumam, kurš drīkst nest `subject`, un abi bulk-rakstītāji (`db.insert_document`, `matcher.link_politicians_to_documents`) iet caur to; divas klases vairs nerada `subject` rindas: releja mediju sloti (`relationship_type='organization'` UN `feed_type='relay'` — LETA un vēl 10) un kaili retvīti no biroja balss konta @Brivibas36. Mērījums pirms/pēc: nepārskatītie web doki 6 493 (nemainīgi); no tiem ar `subject` rindu **1 257 → 295** pēc sagatavotās vēsturiskās demotēšanas. Vārti: `tests/test_subject_role_guards.py` (4 no 6 krita pirms labojuma).
>
> **Vēsturiskās 3 027 rindas demotētas 2026-09-06 ar operatora lēmumu** (CHANGELOG «2026-09-06 (2)»; + 3 pāru papildinājums `data/fix_grupaE_subject_demote_addendum_2026-09-06.sql`). Bija: — `data/fix_grupaE_subject_demote_2026-09-07.sql` + rollback (pārbaudīti uz DB kopijas: 95 dzēstas, 2 932 demotētas, rollback atjauno baitu pa baitam). Rinda `BACKLOG.md` § Atliktais pēc 2026-09-06 verdiktiem.
>
> **NAV šeit apvienota, ar nolūku:** § Junction abu virzienu izmeklēšana. Tā ir SPOGUĻA klase (junction rinda BEZ vārda tekstā, un vārds tekstā BEZ junction rindas) — cits mehānisms, cits koda ceļš, cits saucējs; līdzīgi skan tikai risinājums.
>
> **Cena, kas abām atlikušajām instancēm kopīga:** `reviewed_at` ir per-DOKUMENTS, tāpēc nepareizi piešķirta `subject` loma aizver dokumentu arī īstajiem runātājiem, un neviena rinda to vairs nepiedāvā (CLAUDE.md § Schema invariants).

**(1) `subject` lomas inflācija — 6 instances vienā dienā (2026-08-24).** Politiķim tiek piešķirta `subject` loma uz garāmejošas pieminēšanas, kamēr dokumenta īstie runātāji paliek `mentioned`:

| doc | `subject` piešķirts | kas tur patiesībā runā |
|---|---|---|
| 93531 | pid=95 Jakovins (tikai balsojuma uzskaitē) | Ašeradens, Valainis, Kučinskis — visi trīs `mentioned` |
| 93487 | pid=167 Kalniete (viens teikums) | Eldara Mamedova viedokļraksts |
| 93488 | pid=225 LVM (viens piemērs) | Ilzes Rasas viedokļraksts |
| 93442 | pid=66 Čakša (viens teikums) | raksts ir par Abu Meri, kurš tur ir `mentioned` |
| 93534 | pid=10 Kulbergs (garāmejoša pieminēšana) | raksts par Zelenska uzrunu |
| 93437 | pid=82 Butāns (viens teikums) | biedrības pārstāvis par K2 Ventum |

Vārds tekstā katrā gadījumā ir īsts, tāpēc tā **nav** `negative_patterns` klase — tā ir lomas piešķiršanas klase, un 09-07 vārts to NEskar (tas sedz tikai releja slotus un biroja balss retvītus, ne personu lomu piešķiršanu). *Rīcība:* lēmums, vai `subject` lomai vajag runātāja pierādījumu arī personām, vai arī klase paliek segta ar citētā runātāja joslu. *Īpašnieks:* operators.

**(3) Junction lomas apgrieztas LETA pārstāstos — `mentioned` runātājs nekad nenonāk ekstrakcijas rindā.**

- **Sakne (doc 78085, 2026-08-01):** LETA-pārstāstā vienīgais runātājs ir `mentioned`, un ekstrakcijas rinda iet tikai pa `role='subject'` → runātāja pozīcija nekad nenonāk rindā; nav LETA-specifiska klase, bet vispārīga LV ziņu uzbūve (CHANGELOG arhīvs 2026-08-02). `reviewed_at` per-dokuments semantika zudumu maskē (kopš 2026-08-09 CLAUDE.md § Schema invariants).
- **09-07 vārts šo NEatrisina un pat sašaurina atgūstamību:** demotēšana notiek bez paaugstināšanas — nākamais kandidāts NETIEK pacelts par subjektu. Praksē **962** no 1 257 nepārskatītajiem web dokiem ar `subject` rindu ir tādi, kuros relejs bija VIENĪGAIS subjekts, un tie paliek tikai ar `mentioned` rindām. Tas ir mērķis (tie nekad nav devuši pozīciju), bet tas NEpadara tur citētos runātājus sasniedzamus — tieši šī apakšpunkta klase.
- **Rīks un mērogs — lieto rīku, ne pierakstīto procentu:** `scripts/audit_junction_role_inversion.py` + `/audit-integrity` 15. pārbaude; nominatīva forma ≤60 zīmes no citēšanas signāla, inversija = `mentioned` runā, neviens `subject` nerunā (naivā „visas formas" versija doc 78085 nepamana; 13 testi). Bāzlīnija 08-05: `checked=1288 flagged=263` (20,4 %); ~271 īsts zudums, ~1,4 doki dienā, ~92 % precizitāte.
- **Lēmums 2026-08-04: kandidāts (b) + backfill; plāna 1.–5. solis IEVIESTS** (`729aa27e`, dizains `docs/plans/2026-08-04-junction-inversion-queue-fix.md`). **1. vilnis 08-05** (8 claims #689187–#689194) un **2. vilnis 08-06** (5 claims #689250–#689254, rindā 339) izpildīti — pilnie pieraksti CHANGELOG 2026-08-05/06. **Detektora FP/empty klases nākamajiem viļņiem:** viens neizsekots komentētājs par daudziem politiķiem (klasterēti FP pa vienu doku — 76612); pasīvais saturs (`TIEK apsvērts` bez nostājas — 76611); cita medija pārpublicēts citāts ar divu lēcienu provenanci (73172); cross-source verbatim dublikāti (lielākais empty cēlonis).
- **Paliek 6. soļa turpinājums:** partijas pa ≤12 pāriem no `pending_quoted_mentioned(db, days=90)`, atsevišķi no dienas rutīnas. Nākamie mērķi: doc 76625 Rinkēvičs; Kulberga kokrūpnieku web trio 71412/71395/71371 (visos `mentioned`, 0 pid=10 claims — pozīcija DB tikai no X #553970, web provenance nav); doc 72401 Rokpelnis (`subject`, 0 claims) + 6 līdziesniedzēji `mentioned` (74, 109, 89, 73, 145, 162).
- **2026-08-16 mērījums: klase ir smagāka, nekā ~1,4 doku/dienā liek domāt.** Vienā rutīnas dienā ar roku pārbaudīti ~10 kandidāti un atgūtas **6 pozīcijas no 4 dokumentiem**, kur runātājs bija `mentioned`. Divi gadījumi ir ekstrēmi: **doc 88345** (KNAB sižets) nesa 4 pozīcijas, no kurām rindā nonāca **viena** — Kulbergs ×2 (#689701, #689702) un Latkovskis (#689703) būtu zuduši klusi; **doc 88820** (airBaltic) Kulbergs ir raksta GALVENAIS runātājs, arī virsrakstā, bet junction lomā `mentioned` — no tā nāca #689710, dienas augstākā salience (0,85). Vēl divi: Citskovskis #689711, Dombrava #689712, NBS #689713.
  - **Ekspozīcijas vaicājums (atkārtojams):** šodien zīmogotie web doki, kuros kāds tracked politiķis ir `mentioned` un no tā dokumenta viņam nav neviena claim → 2026-08-16 deva **26 pārus pār 10 dokiem, saucējs 18 web doku**. Lielākā daļa ir īsti pieminējumi; trāpījumu īpatsvars starp pārbaudītajiem bija ~3 no 10.
  - **Procedūras mācība atgūšanas aģentiem:** padod dokumenta ID un liec LASĪT, nekad nepadod satura kopsavilkumu izpildei. Trīs reizes no trim nodotais apraksts izrādījās nepilnīgs — Latkovskim trūka divu rindkopu, Kulbergam trīs, Citskovskim visa sistēmiskā prasība par Kārtības ruļļa grozījumiem.
- **Blakus klase, kuru 09-07 mērījums nosauca un kas NAV šī verdikta tvērumā:** `feed_type='relay'` ir arī **7 žurnālistiem un 6 neaktīvām personām**. Lapsa (pid=57) nes **3 219 twitter `subject` rindas**, augustā 486 — visas no kailiem RT, kuru tekstā ir `@Lato_Lapsa`, t.i. atbildes VIŅAM, ne viņa runa; pēc 2026-08-21 žurnālistu lēmuma šiem slotiem ir **0 pozīciju claims**. Vārta paplašināšana uz «jebkurš `feed_type='relay'` konts» ir viena rinda `scope.relay_media_pids()` vietā — cena ir tā, ka šo žurnālistu profila X apakšcilne pārstāj papildināties. *Īpašnieks:* operators.

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

### [OPEN] 2026-08-24 rutīnas matcher atradumi — divas uzvārda kolīzijas + `subject` lomas inflācijas saucējs

Iznākums no 23 aģentu ekstrakcijas viļņa (64 politiķi, 246 doku slotu, 246/246 apstrādāti). Neviens nav labots — visi prasa operatora `negative_patterns` vai junction lēmumu.

**(a) Arvis Zīle → pid=21 Roberts Zīle (T1, augoša ekspozīcija).** Doki 93457 un 93439 runā par Krīzes vadības centra vadītāju **pulkvedi Arvi Zīli**, ne par EP viceprezidentu Robertu Zīli; abos priekšvārds nav minēts, un pid=21 `name_forms` satur kailās formas `"Zīle"`, `"Zīles"`, `"Zīlem"`. Saucējs, kas padara klasi atkārtojošu: «Krīzes vadības centra vadītāj*» korpusā ir **16 doku**, kamēr «Roberts Zīle» kopš 08-20 — **0 doku**. **SAGATAVOTS 2026-09-07, gaida operatora apstiprinājumu** (verdikts 31, CHANGELOG 2026-09-07 (6)): `data/fix_grupaD_zile_negative_patterns_2026-09-07.sql` + pāra rollback. Pārmērīts pirms rakstīšanas — amata frāze korpusā ir **41 dokā, 0 no tiem satur īstu Roberta Zīles vārda formu**, un pid=21 nes 2 nepatiesas junction rindas; eval vārti abās pusēs vienādi (`B2D2H fp_links=1`, zelts 97,93 %). Blakus mērījums, kas ietekmē formulējumu: **`negative_patterns` ir reģistrjutīgs substring, ne regex**, tāpēc «vadītāj» ar aizstājējzīmi tas nestrādātu. *Īpašnieks:* operators — `negative_patterns` nekad neauto-pievieno.

**(b) Guna Puče → pid=189 Juris Pūce (T1, diakritikas variants) — ATLIKTS 2026-09-07** (verdikts 32). Doc 93527 (la.lv/TV24) ir par Latvijas Mākslīgā intelekta centra vadītāju **Gunu Puči** («Gunu Puči», «Puce norāda»); matcher to piesaistīja kā `subject`, jo ASCII forma `Puce` sakrīt ar pid=189 formu. Doks marķēts tukšs. Tā pati forma kā (a), tikai caur diakritiku locīšanu. **Viena instance nepamato eval vārtu palaidienu — pārmērīt, ja parādās otra.** *Īpašnieks:* operators.

**(c) `subject` lomas inflācija — 6 instances vienā dienā (93531, 93487, 93488, 93442, 93534, 93437).** PĀRCELTS 2026-09-05 uz šī faila § «`subject`» lomai vajag runātāja pierādījumu — sešu instanču tabula ar saviem saucējiem dzīvo tur, kopā ar otro atlikušo instanci (LETA apakšpunkts slēgts 2026-09-07).

**(d) Kandidātu saraksta raksti kā junction slodze — pieraksts, ne defekts.** Doc 93539 («Apvienotie dūži premjera vadībā: 15. Saeimas … saraksts nr. 7») nes **16 junction rindas**: 15 `mentioned` no vārdu uzskaitījuma un 1 `subject` (pid=69 Smiltēns) — un tieši tā viena rinda uzlika `reviewed_at` visam dokumentam. Junction sweep pārbaudīja 11 pārus: **11/11 tukši**, jo saraksta rinda nav pozīcija. Nākamā sesija lai to neskaita par matcher defektu. Blakus: raksts pārstāsta AS priekšvēlēšanu programmu, kas pieder `program_promise` ceļam (`scripts/ingest_url.py`), ne dienas slotam.

**(e) Fantoma `mentioned` — jauna instance § Junction abu virzienu izmeklēšana (a) klasei.** Doc 93561 nes `mentioned` rindu pid=29 Alvim Hermanim, kaut tekstā nav nevienas viņa vārda formas, arī ne apakšvirknes «Herman». Rinda radīta 9 s pēc pid=13 `subject` rindas — iespējams no citētā tvīta t.co saites.

### [OPEN] 2026-08-26 rutīnas matcher atradumi — palicis tikai īstais vārdabrālis

> **(b), (c) un (d) SLĒGTI 2026-09-05/07.** (b) @Brivibas36 relejs — SLĒGTS (verdikts 38, CHANGELOG 2026-09-07 (7)): kaili retvīti no biroja balss konta vairs nerada pid=10 `subject` rindas; mehānisms ir **satura vārts, ne `feed_type`** (konts pieder politiķim, tāpēc `relay` te nederētu), vēsturiskās rindas 34, no tām pid=10 ×22. (c) pid=234 Arigo Toro `Gobzem*` formas — SLĒGTS 2026-09-05: operatora fakts, Toro IR pārdēvētais Aldis Gobzems, tāpēc formas ir viņa paša un PALIEK; `negative_patterns` += «Gobzema sarakst» (rollback `data/rollback_toro_negative_pattern_2026-09-05.sql`). **Verdikta 09-06 rinda 29 (sašaurināt formas) ir pretrunā ar šo faktu un NAV izpildīta — stop beats write.** (d) Agris Freifalts — SLĒGTS 2026-09-07 (verdikts 28): iesēts kā pid=247, partija «Gobzema saraksts» verificēta pret CVK un LTV; apstiprināts arī, ka viņa vārdi līdz tam gāja pid=234 slotā (7 no 9 dokiem).

**(a) Viktors Valainis → pid=25 Viktors Valainis (T1, ĪSTS vārdabrālis, ne apakšvirkne) — PALIEK ATVĒRTS.** Doc 95063 (jauns.lv, LPV vēlēšanu saraksta apskats) piesaistīja pid=25 `mentioned` lomā, bet rindkopā par Zemgales sarakstu runa ir par **citu** Viktoru Valaini — LBTU docentu, kuru raksts pats apraksta kā «pašreizējā ekonomikas ministra vārda un uzvārda brāli». Junction pāris atzīmēts tukšs un `extracted_at` uzlikts, tāpēc šodienas cena ir nulle.

Kāpēc šī nav parastā T1 forma: vārds un uzvārds sakrīt **pilnībā**, tāpēc ne vārdu robežas (D2), ne priekšvārda veto, ne `negative_patterns` uz virknes to nešķir — abi cilvēki tekstā ir «Viktors Valainis». Vienīgais atšķirīgais signāls ir konteksta kolokācija (amata apzīmējums «ekonomikas ministrs» pret «docents»/«LBTU»). **Verdikts 33 (2026-09-06): NĒ atsevišķam labojumam, JĀ kopīgam risinājumam** — risināt kopā ar Meļņa un Bērziņa gadījumiem, sk. § Konteksta kolokācijas dizains. *Īpašnieks:* operators.

### [OPEN] Ārvalstu revīzijas iestādes sasaistās ar Valsts kontroli (id=241)
2026-07-31 seed rescan: 336 sasaistēs 2 bija kļūdainas — "Spānijas Valsts kontrole" (doc 36152) un "Krievijas Valsts kontroles jeb Skaitīšanas palātas" (doc 50888), abas noņemtas ar `data/fix_vk_foreign_audit_junctions_2026-07-31.sql`. Sakne: matcher daudzvārdu formas ir tīri substringi, tāpēc `<Valsts>ijas Valsts kontrole` satur formu. `negative_patterns` neder — tie noraidītu VISU dokumentu, un tad pazustu doc 20494 (PROVIDUS raksts ar 10 tiešām LV VK atsaucēm blakus Somijas/Igaunijas piemēriem). Pareizais risinājums būtu formas līmeņa prefiksa veto (ģenitīva ģeonīms tieši pirms daudzvārdu formas) `src/matcher.py::_occurrences` blakus D2 vārdu-robežu logikai. Līdz tam — periodiska pārbaude ar `grep -E '\w+(as|ijas) Valsts [Kk]ontrol'` pār jaunajām VK sasaistēm.

### [OPEN] Bērziņš false-link — monitorings, ne kampaņa

**Andris Bērziņš (id=146, ZZS)** ķer pilnvārda dvīņus, un pilns vārds sakrīt, tāpēc `negative_patterns` pa uzvārdu nepalīdz — der tikai konteksta kolokācijas; divas no trim klasēm ir slēgtas („Latvijas Ceļu būvētājs" vadītājs doc 62139 — 2026-07-27; aktieris doc 74402 — 2026-07-29, harness FP 2→1; pieraksts CHANGELOG 2026-07-27 un 2026-07-29). **Paliek atvērta un ir string-NEATRISINĀMA dziedātāja klase (doc 64681)** — vārds tur ir tikai solistu uzskaitījumā bez profesijas vārda blakus, tāpēc neviens virkņu līmeņa guard to neķer. **Šī klase kopš 2026-09-07 tiek risināta kopā ar Meļņa un Valaiņa gadījumiem — sk. § Konteksta kolokācijas dizains.** Rīcība šeit: neko nebūvē atsevišķi, agrīnā pamanīšana = `/audit-integrity` 1b B2-veto žurnāls; mērījums un plāns `docs/plans/2026-07-27-matcher-koliziju-plans.md`.

### [OPEN] NBS pid=204 slota piesārņojums — sašaurināts uz CVK domēna izņēmumu (32 doki, no tiem CVK 2)

> **Pārmērīts un sašaurināts 2026-09-07** (verdikts 37 NORAIDĪTS ar mērījumu, CHANGELOG 2026-09-07 (7)). Verdikts gribēja iekļaut pid=204 tajā pašā `organization|relay` vārtā, kas slēdza LETA klasi. **Tas nedrīkst notikt:** NBS ir `organization`, bet `feed_type='first_party'` un tam ir **40 pozīciju claims** (22 augustā, pēdējā 09-04) — vārts pār `relationship_type='organization'` nogrieztu dzīvu kanālu, tāpat kā LDDK, LVM, Valsts kontrolei un Latvijas Bankai. **Tas ir domēna, ne lomas jautājums.** Jaunais saucējs: slotā **32 nepārskatīti `subject` doki** (bija 38), no tiem CVK programmu doki — **2**.

**(1) Tēmas atslēgvārda apakšklase — CVK programmu doki (šodien 2 doki).** Matcher CVK programmu dokiem liek pid=204 «Latvijas armija (NBS)» kā `subject`, jo programmas tekstā ir vārds «armija» — tēmas piesaukums, ne institūcijas paziņojums. *Rīcība:* šaurs izņēmums CVK **domēnam** (`_is_cvk_domain()` jau eksistē `src/render/news.py` renderī — tas pats domēna kritērijs, ne virsraksts, jo CVK `<title>` mainās katru ciklu) keyword-org piešķiršanā, vai `negative_patterns`. Atkārtotai programmu ielādei: plūsma CLAUDE.md Datu kontraktā #4a; `ingest_url.py` ar .venv python; NEpadod `db=`.

**Ziņu plūsmas puse SLĒGTA 2026-08-18** (verdikts 08-17; CHANGELOG): CVK domēna dokumenti izslēgti `src/render/news.py` renderī; dokumenti un junction rindas DB paliek.

**(2) Amata-apzīmējuma apakšklase — Slaidiņš (izmērīts 2026-08-01/08-02).** pid=204 slotā nonāca `la.lv` raksti, kuros «NBS» un «Nacionālo bruņoto spēku» parādās TIKAI Jāņa Slaidiņa amata apzīmējumā — *«NBS majors un Zemessardzes štāba virsnieks Jānis Slaidiņš»* —, un runā privātpersona militārā analītiķa lomā. Visas četras reizes ekstrakcijas aģents dokumentu korekti atzīmēja tukšu. **Verdikts 2026-08-17: virziens (a) — sēt Slaidiņu kā atsevišķu entītiju** (`/seed-entity`). **Brīdinājums pirms alternatīvā (b) `negative_patterns` ceļa:** paterns pēc amata (`NBS majors`, `NBS virsnieks`) ir plašāks, nekā izskatās — «NBS komandieris» blakus ĪSTAM institucionālam paziņojumam trāpītu zem tā paša paterna.

**Trešā, atsevišķi pierakstītā forma (2026-08-16, doc 88352):** «NBS» tekstā ir **tieši vienu reizi** un kā cita teikuma objekts, bet visi četri citētie runātāji ir NATO vai industrijas pārstāvji. Simptoms cits, sekas identiskas: viens atslēgvārds → slots → tukšs doks. **Kontrastam, kas NAV kolīzija:** doc 88818 tajā pašā dienā piesaistīja Valsts kontroli (pid=241) pareizi — institūcijas slots dabiski saņem šādus rakstus; ja katru no tiem skaitītu par matcher defektu, `negative_patterns` sāktu graut īstos trāpījumus. *Īpašnieks:* operators.

### [OPERATOR] Konteksta kolokācijas dizains — Meļņa, Valaiņa un Bērziņa klase vienā mehānismā

> **Atvērts 2026-09-07** (verdikti 30 un 33, CHANGELOG 2026-09-07 (4)). Trīs gadījumi, kas līdz šim dzīvoja trīs vietās, ir viena klase ar vienu risinājumu; verdikts 33 to formulēja tieši: «NĒ atsevišķam labojumam, JĀ kopīgam risinājumam».

**Klase.** Virkņu līmenī neatrisināmas kolīzijas, kur atšķirīgais signāls ir NEVIS vārda forma, bet blakus stāvošais amata apzīmējums:

- **Meļņi.** pid=157 Kaspars Melnis (ZZS) nes kailo formu `Melnis`; pid=224 Raivis Melnis (aizsardzības ministrs) to nenes. Katrs teksts, kas ministru sauc kaili par «Melni», aizgāja uz nepareizo cilvēku. **Datu daļa SLĒGTA 2026-09-07:** 28 doki izlasīti pilnībā, 9 junction rindas pāratribuētas (`data/{fix,rollback}_melni_reattrib_2026-09-07.sql`); **neviena no 54 pid=157 pozīcijām nepieder Raivim Melnim**, tāpēc ne kolīzijas vaicājums, ne re-embed nebija vajadzīgi.
- **Valaiņi.** pid=25 Viktors Valainis (ekonomikas ministrs) pret LBTU docentu ar **pilnībā identisku vārdu un uzvārdu** — ne vārdu robežas (D2), ne priekšvārda veto, ne `negative_patterns` to nešķir (§ 2026-08-26 (a)).
- **Bērziņi.** pid=146 Andris Bērziņš (ZZS) pret dziedātāju doc 64681 — vārds tur ir tikai solistu uzskaitījumā bez profesijas vārda blakus (§ Bērziņš false-link).

**Mehānisma kandidāts, ko šie trīs kopīgi definē:** kails uzvārda trāpījums + **±1 teikumā amata apzīmējums, kas sakrīt ar CITA tracked politiķa `role`** → nesaistīt, bet pierakstīt kandidātu operatora izskatīšanai. Tas ir tas pats «stop beats write» zars, ko lieto attribūcijas nenoteiktībā, un tas neprasa `negative_patterns` maiņu.

**Kāpēc esošie vārti to nevar noķert — izmērīts 2026-09-07:** `scripts/eval_matcher_collisions.py` marķēto FP kopā ir **32 gadījumi, un neviens no tiem nav šī klase**. Tātad eval (FP≤3, zelts≥1260) pēc konstrukcijas rādīs «bez izmaiņām» arī tad, ja labojums klasi atrisina vai salauž. **Priekšnosacījums pirms jebkādas `negative_patterns` maiņas kailajai `Melnis` formai: eval korpusā jāieliek Meļņa gadījums** — citādi vārti sertificē neizmērītu izmaiņu.

*Rīcība:* dizains pirms koda (mērījums, cik doku korpusā nes kailu uzvārdu + sveša amata apzīmējumu ±1 teikumā), tad eval korpusa papildinājums, tad kods. *Īpašnieks:* operators.

### [OPERATOR] 2026-09-07 seedēšanas un junction blakuskarogi — trīs mazi, katrs ar savu saucēju

Atrasti, izpildot 2026-09-06 verdiktus (CHANGELOG 2026-09-07 (4) un (6)). Neviens nav labots — visi trīs ir `name_forms`/`negative_patterns`/junction lēmumi, t.i. operatora robeža.

- **(a) pid=174 Toms Lūsis — divas ≤4 zīmju ģenerētas formas (T1).** Matcher ģenerē `Lūsi` un `Lūša`; abas ir apakšvirkņu bumbas tieši tā, kā apraksta CLAUDE.md § Īsās ģenerētās formas. Slots ir `inactive`, tāpēc šodienas cena ir zema, bet reaktivācija to uzreiz paceltu. *Rīcība:* karogot operatora izskatīšanai, nekad neauto-noņemt.
- **(b) pid=246 Guntis Pujāts vs kardināls Jānis Pujāts.** Seedēšanas kohortas audits (T13) atrada **2 nepatiesas junction rindas no 26** — doki 6820 un 26974 runā par kardinālu, ne par ģenerāli; abas dzēstas. Korpusā ir vēl divi vārdabrāļi (Edgars, Jānis Pujāts), kurus priekšvārda veto noturēja pareizi. *Rīcība:* `negative_patterns` kandidāts `"kardināl"` (2 doki korpusā) — šaurs, amata apzīmējums stabils. *Īpašnieks:* operators.
- **(c) Četras svešas junction rindas pid=157 slotā.** Doki **6344, 31977, 38789, 40173** palika pid=157 (Kaspars Melnis) rindās pēc 09-07 pāratribūcijas — tie nav ne Kaspara, ne Raivja gadījumi. *Rīcība:* izlasīt četrus dokus un izlemt dzēšanu ar pāra rollback; četras rindas nav sweep, bet tās nedrīkst pazust no redzesloka. *Īpašnieks:* operators.

### [OPEN] Deep-check 2026-08-17 blakus atradumi — 9 claim/datu karogi

Atrasti `/deep-check` skrējienā (6 politiķi, 0 apstiprinātu pretrunu). **Gandrīz viss izpildīts 2026-08-18** (CHANGELOG): #20557 + #689627 stance, T4 kvartets #6954/#7019/#7022/#7397 diakritika (§ Citātu integritātes (b)), abi izpildes blakuskarogi (#6954 „ārzemniekiem" izņemts + re-embed, #7397 `NEEDS_REVIEW: ` marķieris) un #6658/#7043 dublikāts (dedup 3 grupas). #20597 (Švinka) karogs ATSAUKTS — sk. § 2026-08-15 rutīnas datu defekti (a); Vītola `relationship_type` → § Ne-darīt. **Atvērts paliek viens:**

- **#555726 (Valainis) citēšanas brīdinājums — IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): MK protokols Nr. 40 (27. §, 26-TA-1067) 14 milj. EUR **nepiešķir** — brīdinājums ierakstīts claim `reasoning` (`data/{fix,rollback}_claim555726_citation_note_2026-08-21.sql`); pārskatiem jācitē ar atrunu.

### [OPEN] Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts

Substring-defekts (`raksta` iekš `saraksta`, doc 80038 klase) SLĒGTS 2026-08-05 — signāli vārda sākumā + pilnais teksts (`src/quoted_speaker.py`, 3 regresijas testi); bāzlīnija pēc fiksa 1288/263. Paliek nemērīts kandidāts: **bezpersonisko atribūciju veto** — `teikts … programmā/paziņojumā` citē dokumentu, ne cilvēku, tāpēc tuvumā esošs nominatīvs nav runātājs. Pirms ieviešanas izmērīt biežumu ar audita rīku.
