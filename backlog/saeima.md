# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Saeima

### [DAĻĒJI SLĒGTS 2026-08-17] 562 `saeima_votes.result` vērtības nāca no backfill fallback, ne no avota

- **Ko rāda vārti:** `scripts/audit_saeima_vote_results.py` → `audited=7837 mismatches=562 (of which no-ballot rows carrying a result: 540)`. Vārti bija sarkani jau ilgāk; 2026-08-17 tika izmeklēts, nevis atkal noskatīts.
- **Cēlonis (izlabots kodā 2026-08-17):** abu backfill skriptu (`scripts/p3_backfill_year.py`, `scripts/p3_backfill_year_urllib.py`) compute-from-totals fallback (a) ieskaitīja `total_nebalso` klātesošajos un (b) fabricēja `Noraidīts` rindām, kur neviens nav balsojis (`0 > 0` = False). Fallback nostrādā, kad lapas sarkanais `<span>` ir tukšs — titania rezultātu ieraksta ar JS, tāpēc urllib ceļam tas ir tukšs **vienmēr**; Playwright ceļš (@saeima-tracker) dabū īsto vērtību.
- **Kāpēc formulai bez `Nebalsoja` var ticēt:** korpusā tikai **25 rindas** vispār šķir abus lasījumus. Tās **3**, kas ienāca dzīvajā tracker ielādē (balsojumi 183, 194, 213 — rezultāts no renderētās lapas), atbilst formulai **bez** `Nebalsoja`; pārējās **22** atbilst formulai **ar** `Nebalsoja`, bet tās visas ir tā paša kļūdainā fallback izvads — pierādījums pats sev, ne liecība no saeima.lv.
- **Datu atlikums (NAV labots, prasa operatora lēmumu + pāra rollback):**
  - **22 reāli balsojumi ar nepareizu `result`** (piem. 6035: 47/40/0 → glabāts `Noraidīts`, pareizi `Pieņemts`). Uz tiem norāda **1915 claims**, no kuriem **86** min iznākumu `stance` tekstā (labojot tos, obligāts re-embed), un **7** balsojumiem iznākums ir arī `summary` laukā; **3** ir piesaistīti `bill_id` (stage denormalizācija — tikai caur `append_bill_stage()`).
  - **540 procedurālas rindas** (klātbūtnes reģistrācija, kvoruma pārbaude, amatpersonu vēlēšanas) ar fabricētu `Noraidīts`, kur avotam rezultāta nav vispār. Claims uz tām: **0** (inv. #4b tur nostrādāja).
- **Nepārtaisi par „vārtu kļūdu".** 2026-08-17 sesijā šis vispirms tika diagnosticēts otrādi (it kā audits būtu par striktu) — tas lasījums balstījās uz fallback izvadu kā „avotu". Pierādījuma ass ir provenance (`created_at` tracker vs backfill vilnis), ne balsu aritmētika.

**IZDARĪTS 2026-08-17** (rollback `data/rollback_saeima_vote_results_2026-08-17.sql`, 562 rindas):

- **Avots pārbaudīts renderētā pārlūkā, ne pārrēķināts.** Iznākuma etiķete **nedzīvo** balsojuma lapā (sarkanais `<span>` tukšs visos 22 gadījumos) — tā ir tikai darba kārtības lapas `drawDKP_*(...)` 9. argumentā un piesaistīta **darba kārtības PUNKTAM**, ne balsojumam. Apakšpunktu balsojumiem („Par priekšlikumu Nr.N", „Par debašu laika pagarināšanu", „Par sēdes turpināšanu") etiķetes nav vispār.
- **Nevienam no 22 avotā nav `Noraidīts`.** 15 bez etiķetes; 7 ar punkta etiķeti: `Nod. kom.` ×4 (id 1435, 905, 956, 6192), `Pieņemts` ×2 (id 6954, 6459), `Paziņojums` ×1 (id 1199, Stambulas konvencijas kolektīvais iesniegums).
- **Piemērots:** id 6459 → `Pieņemts` (etiķete burtiska + skaitļi sakrīt); pārējie 21 → NULL; 540 procedurālās rindas → NULL. Audits tagad: `rows=7837 asserted=7276 unknown=561 mismatches=0`, exit 0.
- **Cēlonis izlabots TRĪS vietās:** `scripts/p3_backfill_year.py`, `scripts/p3_backfill_year_urllib.py` un — galvenais ielādes ceļš — `src/saeima/votes.py::parse_vote_snapshot`. Visi trīs (a) izmeta `total_nebalso` no saucēja, (b) beidz fabricēt rezultātu, kad neviena balss nav nodota. Testi: `tests/test_saeima.py::…::test_no_ballot_cast_leaves_result_empty`, `tests/test_audit_saeima_vote_results.py::test_nebalsoja_is_not_in_the_denominator`.
- **Audita semantika mainīta:** tukšs `result` = „mēs neko neapgalvojam" un vairs nav neatbilstība; vārti rāda `asserted/unknown/mismatches` saucējus.

**PALIEK ATVĒRTS: nekas.** Visi trīs atlikumi slēgti — 1. `Nod. kom.` un 2. `result` izcelsme 2026-08-18 (paliekošā konvencija par `result_source` → `BACKLOG.md` § Ne-darīt), 3. id 6954 «punktam divi balsojumi» 2026-08-21 (otrais balsojums korpusā IR kopš 2026-05-27 kā id 333; 08-17 piezīmes premisa bija nepareiza, jo meklēts pēc URL/punkta, ne `(vote_date, vote_time)`). Pilnās pēdas: CHANGELOG 2026-08-18 un 2026-08-21 (8).

### [DEFERRED] Priekšlikumu (amendment) balsojumu pipeline

Titania **publicē** amendment balsojumus parastajā vote-URL formātā: DB jau ir 1452 rindas ar motīvu `Par priekšlikumu Nr.N`, un 2026-07-25 parity audits atrada vēl neielādētus (piem. `Par priekšlikumu Nr.2/4/6/10. Grozījumi Trauksmes celšanas likumā (1051/Lp14), 2.lasījums`, 2025-12-11 — ielādēti). Stenogrammu parse tāpēc NAV vajadzīgs, lai tos iegūtu — pietiek ar pilnīgu agendas URL ūniju.

Paliek derīgs: `saeima_votes.parent_vote_id` (priekšlikums→bāzes balsojums) linkage un politiskā vērtība — NA valodas-amendmenti citos likumprojektos, kur bāzes likums iet vienprātīgi cauri un slēpj iekšējo spriedzi; atklājas tikai, kad operators manuāli pamana.

> Ieraksta sākotnējā premisa („Saeima amendment balsojumus nepublicē indeksējamā URL formātā; visi DB balsojumi ir lasījumu balsojumi, 0 amendment-tipa") bija nepatiesa jau tā tapšanas brīdī — atspēkota 2026-07-25.


### [OPEN] Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

- **Trigeris:** Čulkovas «pret» airBaltic likumprojektam Budžeta komisijā (19.08., diena.lv reportāža) nefiksējas nekur — nav retorikas (`position` neder) un nav plenārsēdes (`saeima_vote` neder); komisijās notiek reāla politiskā darbība, ko plenārsēžu vienbalsība mēdz slēpt.
- **Rīcība:** izpētīt avotus (komisiju sēžu protokoli/audio saeima.lv, mediju reportāžas) un datu modeli — visticamāk jauna `claim_type` vērtība vai atsevišķa tabula ar savu provenance ķēdi; NEjaukt ar `saeima_vote` (inv. #4b semantika ir plenārsēdes balsis). Mediju reportāžās nosaukti komisiju balsojumi pa vidu var iet kā `position` tikai tad, ja deputāts pats komentē — pats balsojuma fakts prasa strukturētu avotu.
- **Lēmuma īpašnieks:** operators (avota izvēle + apjoms); dizains pirms koda ar plāna dokumentu.

### [FIX] Dzīvās sēdes darba kārtība: 4. paterna helperis lasa 21. argumentu, dzīvā `drawDKP_*` forma nes 34 — 2026-09-17 pirmais dzīvais mērījums deva 0 URL

**Trigeris (2026-09-17, `/saeima-ingest` dzīvai kārtējai sēdei).** CHANGELOG 2026-09-16 (4) 4. paternu ielika kodā ar piebildi «kas to izpildīja: tikai testi — pirmais dzīvais mērījums ir nākamā sēde». Mērījums: `scripts/p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda` uz `active=1` / `actual=1` / `nr=1f916d52…` atgrieza **0** no 37 balsojumiem. Dzīvās lapas `drawDKP_*(...)` izsaukumiem ir **34** argumenti (fikstūrai `tests/test_saeima_live_agenda_pattern4.py` — 21): indekss `[20]` tur ir `urgentDep` (tukšs), balsojuma GUID ir `[5]` `unid` (= `[21]` `DKPid`), un vārti ir `[28]` `voteType`. Apakšpunktu balsojumi (5 no 37) dzīvajā dienā nāk tikai no `getTechDKP?OpenAgent&dkp={unid}&tLevel=1&actual=1` (`hasTechChilds` = `[29]`) — neviena DK forma tos nerenderē. Aģents sēdi ielādēja pilnībā ar roku (87/87, paritāte 0 trūkst), tāpēc datu roba nav; **helperis dzīvai dienai ir akls**, un tests to nesaka.

*Rīcība:* (1) helperim lasīt GUID pēc argumenta NOSAUKUMA vai no `[5]`, ne pēc fiksēta indeksa, un ņemt `voteType` vārtus; (2) `getTechDKP` apakšpunktu josla helperī; (3) fikstūra ar īstu 34 argumentu dzīvās dienas izsaukumu (mutācijas tests: 21 argumentu forma turpina strādāt). *Īpašnieks:* operators (koda darbs). Blakus tajā pašā ielādē, katrs mazs: (a) `parse_agenda_snapshot` iesniedzēju laukā ienāk troksnis (`" [ref=…`, `DKP izskatīšanas gaita`, `(Referents: …)`) — `src/saeima/parsing.py:48-56`; (b) `append_bill_stage` verbatim etiķeti `Likums` nekad nepārvērš `current_status='pieņemts'` — 21 šodien pieņemtie likumi paliek `procesā` (vēsturiski 30 `Likums` posmu rindas), `src/saeima/bills.py:368-374`; (c) **daļēja rakstīšana paralēlā ingesta dēļ** — balsojumam 8211 `store_vote` nostrādāja, `generate_claims_from_votes` nomira ar «attempt to write a readonly database» (rīta ingests tajā pašā DB) → 16/74 claims, salabots ar idempotento atkārtojumu (74/74); paralēla Saeimas ielāde un `morning_ingest.py` vienā DB ir riska klase, kamēr claim ģenerēšana nav vienā transakcijā ar `store_vote`.

### [OPEN] Paritātes audits ir VILTUS ZAĻŠ tās pašas dienas sēdei

> **Daļēji slēgts 2026-09-16 (CHANGELOG 2026-09-16 (4)).** Manifests dzīvo dienu tagad REDZ (`_LIVE_URL_RE`, rinda ar `uuid=null, live=true`), un audits par to apstājas ar exit 2 (`_live_session_stop()`, 4. vārti) — viltus zaļais vairs nav iespējams. **Kas paliek atvērts:** tās pašas dienas paritāte joprojām ir rokas darbs pret `DK?ReadForm&nr={actualXML_DkId}` (sk. otro instanci zemāk) — automātisks saucējs dzīvai dienai nav uzbūvēts. Blakus: pretējais ieraksts «Paterns 4 dzīvo tikai promptā» SLĒGTS tajā pašā commit (helperis lasa `drawDKP_*` 21. argumentu; mutācijas tests `tests/test_saeima_live_agenda_pattern4.py`).

**Trigeris (2026-09-10).** `scripts/audit_saeima_agenda_parity.py --dates 2026-09-10` rāda `DK=0, trūkst 0`, kaut sēdē bija 16 balsojumi. Cēlonis: kalendārs kārtējai dienai renderē `./DK?ReadForm&active=1`, nevis `nr={UUID}`, un manifesta `_URL_RE` to nesatver — manifestā šai dienai iekļuva tikai ATCELTĀ jautājumu sēde. Tātad **katra tajā pašā dienā ielādētā sēde ir paritātes auditam neredzama**, un svaiguma vārti (manifesta vecums) iet cauri ar nepareizu saucēju — tieši tā klase, pret kuru vārti pastāv (sal. 2026-08-20, 13 dienas slēpta sēde).

**Rīcība.** `_URL_RE` jāsatver arī `active=1` forma, vai audits jāapstādina ar exit 2, kad pieprasītajam datumam manifestā nav neviena UUID, bet kalendārā ir dzīva sēde. Līdz tam tās pašas dienas paritāti pārbauda ar roku pret darba kārtības iznākuma etiķetēm (2026-09-10: 14 etiķetes + 2 reģistrācijas = 16, zaļš).

**Īpašnieks:** operators (koda darbs).

**Otrā instance 2026-09-14 — viltus zaļais slēpa 5 balsojumus, ne 0.** 09-10 rokas paritāte «14 etiķetes + 2 reģistrācijas = 16» skaitīja tikai PUNKTU līmeni; `nr={DkId}` formā sēdei ir **21** balsojums. Pieci trūkstošie ir *apakšpunktu* balsojumi (2 papildu reģistrācijas 10:42/12:37; «iekļaut nākamās sēdes DK» 1104/Lm14 16:17 un 1108/Lm14 16:30 — LSM minētais 64/16; «nodot komisijai» 1104/Lm14 16:18), kurus titania savieno ar `addVotesLink(APAKŠPUNKTA_HEX, VOTE_HEX)` un rāda TIKAI `nr=` formā — dzīvās `active=1`/`actual=1` lapas apakšpunktus nerenderē, un 4. paterna punkta lapa (`Voting?ReadForm&parentID=`) tādam balsojumam ir tukša (`voteFullListByNames=[""]`). Tātad dzīvai dienai vajag `nr={actualXML_DkId}` (DkId nolasāms no lapas `var actualXML_DkId`) apvienībā ar 4. paternu, un rokas paritāte pret punktu etiķetēm nav pietiekams saucējs — apakšpunktu balsojumiem etiķetes nav. Ielāde ar operatora atļauju 2026-09-14 (CHANGELOG 2026-09-14). Blakus: 16 agrāk glabātās 09-10 rindas nes `parentID=` URL, kas datus dod tikai, kamēr sēde «actual»; stabilā forma ir `/0/{HEX}?OpenDocument`.

### [OPEN] 2026-09-03 trūkst 4 balsojumu — otrā sēde ar turpinājuma etiķeti

**Trigeris (2026-09-10).** Datumam 2026-09-03 ir otra sēde `886631a9-c2b2-4de0-9d9d-34adbcf3d4ae` ar kalendāra etiķeti `23 / 3(As)` — 2026-07-23 ārkārtas sesijas turpinājums. Tās darba kārtībā 113 balsojumi: 109 no 07-23 (DB ir) un **4 no 09-03, kuru DB nav** (DB pēdējais 09-03 balsojums 14:33:09): 15:08:38 priekšlikums Nr.46 (947/Lp14) · 15:09:15 947/Lp14 2. lasījums · 15:10:48 1421/Lp14 1. lasījums · 15:12:57 klātbūtnes reģistrācija.

**Kāpēc audits tos neatrod:** turpinājuma etiķeti `23 / 3` manifests attiecina uz 23. jūliju, ne uz 3. septembri — tā pati klase kā 2026-08-20.

**Rīcība.** Ielādēt četrus trūkstošos balsojumus (UNID saraksts bija sesijas scratchpad-ā, atkārtoti iegūstams no sēdes darba kārtības) un izlemt, vai manifests jāmāca lasīt turpinājuma etiķetes.

**Īpašnieks:** operators.

### [OPERATOR] `_motif_to_topic()` — komisijas nosaukums izvēlas tēmu; nodošanas klauzulas nogriešana skartu 26 no 952 vēsturiskajiem balsojumiem

**Kas slēgts 2026-09-15 (CHANGELOG 2026-09-15 (1)):** 09-10 ielādes četri nepareizie `topic` (8144 `Klimats` ← «ets» apakšvirkne vārdā «pretstatā»; 8136 fallback; 8148 fallback; 8149 `Kultūra` ← komisijas nosaukums) laboti datos (`data/fix_vote_topics_2026-09-15.sql`, 332 claims, kolīzijas 0, bez re-embed) un kodā (`pacientu tiesīb`, `medicīnisk`, `mācīšan` celmi virs Kultūras bloka; `topic_map._SAEIMA_KEYWORD_MAP` tagad sakrīt tikai vārda sākumā). Testi: `tests/test_saeima.py::TestMotifToTopic20260910Load`, `tests/test_topic_map.py::TestSaeimaKeywordWordBoundary`.

**Kas paliek — sistēmiskais cēlonis.** Nodošanas motīvs nes komisijas nosaukumu («Par nodošanu Izglītības, kultūras un zinātnes komisijai. Par …»), un pirmais sakrītošais celms bieži ir komisijas, ne likumprojekta vārds. Mērījums 2026-09-15: ja pirms kartēšanas nogriež klauzulu `nodošan\w* … komisij\w*`, **26 no 952** balsojumiem ar «komisij» motīvā maina atvasināto tēmu — lielākoties uz precīzāku (Krievijas graudu tranzīts → `Ukraina un Krievija`, Valsts valodas centrs → `Valodu politika`, pedagogu streiks → `Izglītība`), daļa uz `Valsts pārvalde` fallback (komisijas vārds bija vienīgais signāls). Tas ir ~2 300 `saeima_vote` claims migrācija ar kolīziju vaicājumu (`topic` ir idempotences atslēgā) un bez re-embed — nav rutīnas solis. **Lēmums operatoram:** (a) nogriezt klauzulu kodā + migrēt 26 balsojumus ar pāra rollback; (b) nogriezt tikai jauniem ielādējumiem (vēsture paliek nekonsekventa vienam un tam pašam likumprojektam); (c) atstāt. Vaicājums, kas atražo sarakstu: `SELECT id, motif, topic FROM saeima_votes WHERE motif LIKE '%komisij%'` + `_motif_to_topic(re.sub(pat, '', motif))`.

