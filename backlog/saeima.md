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
