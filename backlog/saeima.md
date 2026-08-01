# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## Saeima

### [ATVĒRTS 2026-08-21] airBaltic (1495/Lp14) 2. lasījuma balsojums titania vēl nav publicēts — retry gaida

- **Stāvoklis:** likumprojekta karte rāda `2. lasījums / Likums / 20.08.2026`, bet sēdes darba kārtībā (uuid `886631a9-c2b2-4de0-9d9d-34adbcf3d4ae`, 23.07 ārkārtas sēdes turpinājums 20.08) balsojuma lapas NAV. LETA ziņo 54 par / 21 pret / 1 atturas — **neverificēts**, necitēt kā faktu, kamēr titania nav publicējusi.
- **Pārbaudīts 2026-08-21:** visi 109 darba kārtības balsojumu URL pēc `(vote_date, vote_time)` jau ir DB; 61 URL-līmeņa "jaunie" ir T8 pārarhivēti dublikāti. DB 20.08 = 61 balsojums, pēdējais 18:58:29.
- **Rīks:** `.venv/Scripts/python.exe scripts/check_new_session_votes.py` (read-only; exit 2 + saraksts, ja parādās patiesi jauns balsojums). Sesijas cron (ik stundu, mirst ar sesiju) 2026-08-21 uzlikts; ja sesija beigusies — palaist skriptu ar roku vai `/saeima-ingest audit`.
- **Kad parādās:** ingests pēc `@saeima-tracker` Step 3, skaitļu verifikācija pret LETA 54/21/1, tad operatora apstiprināts renders+deploy. Ievēro T14 — pilna 1495 ķēde (nodošana 64/7/0, steidzamība 68/4/0, 1. las. 58/22/1 + jaunais).

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

**PALIEK ATVĒRTS:**

(1. `Nod. kom.` un 2. `result` izcelsme — SLĒGTI 2026-08-18, CHANGELOG; paliekošā konvencija par `result_source` → § Ne-darīt.)

1. ~~**id 6954 — punktam divi balsojumi.**~~ **SLĒGTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): otrais balsojums (12:11:18, 47/2/1) korpusā IR jau kopš 2026-05-27 kā **id 333** ar `result='Pieņemts'`, pilni 92 iv + 92 claims — 08-17 piezīmes premisa «kura korpusā nav» bija nepareiza (meklēts pēc URL/punkta, ne `(vote_date, vote_time)`). Izpildīts tikai atlikušais: `result_source='agenda_label'` seed id 333 (`data/{fix,rollback}_result_source_seed_333_2026-08-21.sql`; etiķete pārlūkā lasīta 08-17). id 6954 paliek `result=NULL` (`(pārbalsots)` — apzināti). Blakus: audita `_OUTCOME_ALIASES` paplašināts ar verbatim etiķetēm `Likums`/`Paziņojums` (7 rindas no 20.08 sēdes, visas `agenda_label`; vārti atkal `mismatches=0`).

### [DAĻĒJI SLĒGTS 2026-08-19] Agenda↔DB parity: 10 sēdes noauditētas; 2024-07-25 sēdē 9 balsojumi trūkst DB

- **Rīks:** `scripts/audit_saeima_agenda_parity.py` (read-only; salīdzina pēc `(vote_date, vote_time)`, ne URL). Visi gadi 2022–2026 pilni, trūkst 0 (pēdas CHANGELOG 2026-08-01 un 2026-08-05; 16 aizklātās vēlēšanas `src/saeima/unloadable.py`).
- **10 sēdes NOAUDITĒTAS 2026-08-19** (DeepSeek read-only aģents; orkestrators neatkarīgi pārbaudīja abas puses — DB `vote_date='2024-07-25'` = 0, titania DK lapa satur tieši 9 `addVotesLink`; atskaite `docs/audits/2026-08-19-saeima-parity-10-sedes.md`): 9 sēdes tīras (svinīgās = runu sēdes; 2023-07-08 = Rinkēviča inaugurācija, sēde beigusies 09:25). **Atradums: 2024-07-25 ārkārtas sēdē darba kārtībā 9 balsojumi (2 deputātu pilnvaru apstiprināšanas — Klotiņš 74/0/0, Stobova 77/0/0; 6 nodošanas komisijām; 1 klātbūtnes reģistrācija), DB = 0.** Sakne: `(As)` etiķetes parsera robs — sēde pazuda no sesiju manifesta, tāpēc nekad nav ielādēta.
- **IELĀDĒTS 2026-08-19** (operatora apstiprinājums sesijā): 9 balsojumi + 724 individuālās balsis (100% sasaiste) + 624 claims caur `ingest_saeima_missing_votes.py --parity data/parity_2024-07-25.json`; pēc-ielādes parity `trūkst 0`; `audit_saeima_vote_results` tīrs (7843 rindas, 0 mismatches). Rollback `data/rollback_saeima_missing_2024-07-25_2026-08-19.sql`. Atlikums: 2 mandātu balsojumiem (541/Lm14, 542/Lm14) `summary` NULL — @saeima-tracker Step 3.5 klase (pieskaitāma 2025 astes 50 rindu darbam).
- **2025 aste — 50 balsojumiem `summary` NULL** (nav māsas `document_nr` ieraksta), @saeima-tracker Step 3.5 darbs; atlase: `... WHERE vote_date LIKE '2025%' AND (summary IS NULL OR summary='') AND document_nr IS NOT NULL AND document_nr != ''` (pārbaudīts 08-05: tieši 50; vēl 179 NULL bez `document_nr` = procedūras rindas, kurām kopsavilkums nepienākas).
- **T8 uzmanībai:** ārkārtas sēde ar 0 DK balsojumu (2025-02-24, 2025-09-16) pārbaudāma ar aci, ne pieņemama. Teorētiskais robs — balsojums ne agenda lapās, ne DB — paliktu neredzams; 2025. gadā tāda nav.

### [OPEN] `/audit-integrity` 9. pārbaude nesedz neievēlētos ministrus — T6 aklā zona (atklāts 2026-08-07)

9. pārbaude verificē `party` pret `faction` pārklājumu sēžu logā — ministrs, kurš nav deputāts, dod 0 balsojumu rindu, un pārbaude par viņu klusi ziņo „tīrs". Tā R. Meļņa nepareizā partija (JV, patiesībā bezpartejisks) izdzīvoja 2 mēnešus un 26 publicētos pārskatos, turklāt pašapstiprinoties no mūsu pašu postiem (CHANGELOG 2026-08-07).

Kandidāti (nav izlemts, kurš):
- 9. pārbaudei atsevišķs zars „politiķis ar `role LIKE '%ministrs%'` UN 0 balsojumu rindu" → izvada kā **atsevišķu denominatoru** („N ministru bez balsojumu seguma — partija neverificējama automātiski"), nevis samet vienā „clean".
- Neatkarīgs krusteniskais tests: partijas apgalvojums pret korpusa formulējumiem, izslēdzot mūsu pašu `documents` rindas (`source_url LIKE '%AtminaLV%'`) — cirkulārā apstiprinājuma ķērājs, izmantojams arī citiem laukiem.

Šobrīd zināmie neievēlētie ministri, kuru partija balstās TIKAI seedēšanas lēmumā: R. Melnis (labots), Uzulnieks (ZZS — pārbaudīts 2026-08-07 pret 51 ārēju avota trāpījumu, pareizi), Braže un Abu Meri (abi JV — apstiprina LETA „No JV jaunajā valdībā amatus saglabās…", pareizi). Pārējos nav pārbaudīts neviens.

### [OPERATOR→dokumentēšana] Māsas balsojumu kopīgais `summary` uzliek 1. lasījuma iznākumu 246 priekšlikumu balsojumiem (~20k claims)

**Klases lēmums PIEŅEMTS (operators 08-17, atkārtoti apstiprināts 2026-08-18): (b) konvencija vēsturei + Step 3.5 labot jauniem.** Tas sedz arī 08-18 pārmērīto apakšklasi — **9 balsojumi / 789 claims ar cita balsojuma iznākumu stance tekstā** (t.sk. 6419 ar 86 claims; sākotnējā "86 claims" premisa neizturēja — izpildes aģents korekti apstājās pirms rakstīšanas): operators 2026-08-18 pārrakstīšanu NEautorizēja, paliek konvencija. **Atlikusī izpilde:** dokumentēt konvenciju pie stance ģenerēšanas (`generate_claims_from_votes`) un Step 3.5 kopsavilkuma noteikums jauniem ne-lasījumu balsojumiem bez iznākuma teikuma. **Saistīts solis 2026-08-21:** `saeima-tracker.md` 3.B tagad prasa INTERESANTAM priekšlikuma balsojumam (Noraidīts ar ≥10 par / frakcija pret savu bloku / dienas debašu temats) savu kopsavilkumu no priekšlikumu tabulas (references gadījums: 7900 Valaiņa zelta vīzas) — tas sašaurina jauno rindu daļu, kur māsas-summary klase vispār var rasties; Step 3.5 vēsturiskā puse paliek atvērta. Vēsturiskais apraksts:

Atrasts 2026-08-05 junction viļņa blakusatradumā (Petravičas aģents), verificēts galvenajā kontekstā. References pāris: balsojumi **6103** (1.lasījums, 84:0:0, Pieņemts) un **6916** (`Par priekšlikumu Nr.1 … 2.lasījums`, 29:6:42, **Noraidīts**) dala `document_nr` 1467/Lp14 un **identisku** `summary` — „…pirmajā lasījumā vienbalsīgi pieņemts (84 par)". Visi **84/84** claims uz 6916 URL ieauž šo tekstu stance laukā („Atturējās balsojumā par: … vienbalsīgi pieņemts (84 par)") — izšķirošais noraidītais priekšlikums aprakstīts ar cita balsojuma iznākumu.

Mērogs (read-only, 2026-08-05): balsojumi ar `summary` 7 295; ar iznākuma frāzi 2 828; **priekšlikumu balsojumi (`motif LIKE 'Par priekšlikumu%'`) ar lasījuma-iznākuma frāzi — 246**, katrs ar ~84–88 `saeima_vote` claims → aptuveni 20k skarto rindu. **Tas NAV viena balsojuma 84 rindu fix — lēmums par klasi ir operatora:** (a) Step 3.5 kopsavilkums ne-lasījumu balsojumiem bez iznākuma teikuma + vēsturisko pārrakstīšana (stance maiņa → obligāts `reembed_claims.py` + pāra rollback), vai (b) pieņemt kā bill-konteksta konvenciju un dokumentēt pie stance ģenerēšanas. Pirms jebkā — izlasīt, kā stance būvējas (`generate_claims_from_votes`) un kā Step 3.5 izvēlas māsas ierakstu.

### [OPERATOR] Partiju pretrunas — piltuves (i) rangs IEVIESTS 2026-08-18; atlicis DA palaidiens (ii)
1.–3. solis 2026-08-06 (`contradictions.party_id`, `src/party_contradictions.py`, dry-run CLI); **rangs 2026-08-18** (`--rank --top 30`, artefakts `docs/eval/party_funnel_2026-08-18.md`; detaļas § Operatora verdikti Klases lēmumi + CHANGELOG). **Atlicis:** DA palaidiens top ~30 ar bināro kill vārtu; izdzīvojušie `confirmed=0`; līdz tam nekas netiek glabāts. **DA piezīmes no ranga (2026-08-18):** ST "Pret" dienesta likumu var būt SASKAŅĀ ar solījumu to atcelt (virziena spriedums DA ziņā); NA budžetu "Pret" prasa per-balsojuma `faction` pārbaudi (T6). **Plašā versija (partijas retorika pret balsojumiem) paliek NORAIDĪTA** — koalīcijas disciplīna + procedurālie balsojumi ražo viltus pozitīvos rūpnieciskā apjomā (pirmais publicētais izskatītos kā 07-25 @AtlasDynam1cs tvīts, ko atspēkojām). Šaurās versijas cietie vārti: procedurāls motīvs (`darba kārtībā`, `nodošanu komisijai`, `steidzamīb`) nekad nevar būt pretrunas pamatā (T14); frakcijas nostāja = klātesošo Par/Pret/Atturas vairākums.

### [DEFERRED] Priekšlikumu (amendment) balsojumu pipeline

Titania **publicē** amendment balsojumus parastajā vote-URL formātā: DB jau ir 1452 rindas ar motīvu `Par priekšlikumu Nr.N`, un 2026-07-25 parity audits atrada vēl neielādētus (piem. `Par priekšlikumu Nr.2/4/6/10. Grozījumi Trauksmes celšanas likumā (1051/Lp14), 2.lasījums`, 2025-12-11 — ielādēti). Stenogrammu parse tāpēc NAV vajadzīgs, lai tos iegūtu — pietiek ar pilnīgu agendas URL ūniju.

Paliek derīgs: `saeima_votes.parent_vote_id` (priekšlikums→bāzes balsojums) linkage un politiskā vērtība — NA valodas-amendmenti citos likumprojektos, kur bāzes likums iet vienprātīgi cauri un slēpj iekšējo spriedzi; atklājas tikai, kad operators manuāli pamana.

> Ieraksta sākotnējā premisa („Saeima amendment balsojumus nepublicē indeksējamā URL formātā; visi DB balsojumi ir lasījumu balsojumi, 0 amendment-tipa") bija nepatiesa jau tā tapšanas brīdī — atspēkota 2026-07-25.


### [OPEN] Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

- **Trigeris:** Čulkovas «pret» airBaltic likumprojektam Budžeta komisijā (19.08., diena.lv reportāža) nefiksējas nekur — nav retorikas (`position` neder) un nav plenārsēdes (`saeima_vote` neder); komisijās notiek reāla politiskā darbība, ko plenārsēžu vienbalsība mēdz slēpt.
- **Rīcība:** izpētīt avotus (komisiju sēžu protokoli/audio saeima.lv, mediju reportāžas) un datu modeli — visticamāk jauna `claim_type` vērtība vai atsevišķa tabula ar savu provenance ķēdi; NEjaukt ar `saeima_vote` (inv. #4b semantika ir plenārsēdes balsis). Mediju reportāžās nosaukti komisiju balsojumi pa vidu var iet kā `position` tikai tad, ja deputāts pats komentē — pats balsojuma fakts prasa strukturētu avotu.
- **Lēmuma īpašnieks:** operators (avota izvēle + apjoms); dizains pirms koda ar plāna dokumentu.
