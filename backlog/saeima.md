# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Saeima

### [DEFERRED] `saeima_votes.parent_vote_id` — priekšlikuma balsojuma sasaiste ar bāzes balsojumu

Priekšlikumu balsojumi jau ienāk caur agendas URL apvienību: `SELECT COUNT(*) FROM saeima_votes WHERE motif LIKE 'Par priekšlikumu Nr%'` → **2 437** (2026-09-25; 07-25 bija 1 452). Trūkst tikai sasaistes: kolonnas `parent_vote_id` nav (`pragma_table_info('saeima_votes')`). Vērtība — priekšlikumos redzama spriedze, ko vienprātīgs bāzes likuma balsojums slēpj.

*Trigeris:* pirmā publikācija, kurai vajag priekšlikumu ķēdi. *Rīcība:* kolonna + aizpildīšana pēc `document_nr` un lasījuma. *Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [DEFERRED] Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

- **Problēma:** komisiju balsojumi nefiksējas nekur (piem., Čulkovas «pret» airBaltic likumprojektam Budžeta komisijā 19.08.) — tā nav retorika (`position` neder) un nav plenārsēde (`saeima_vote` neder).
- **Rīcība:** izpētīt avotus (komisiju protokoli/audio saeima.lv, mediju reportāžas) un datu modeli — jauna `claim_type` vērtība vai atsevišķa tabula ar savu provenance ķēdi; NEjaukt ar `saeima_vote` (inv. #4b ir plenārsēdes balsis). Dizains pirms koda, ar plāna dokumentu.
- **Trigeris:** pēc 2026-10-03 vēlēšanām (§ Atliktais 43 — «atgriezties pēc kampaņas»).
- **Lēmuma īpašnieks:** operators (avota izvēle + apjoms).

### [FIX] Saeimas ielādes sīkumi — iesniedzēja lauka troksnis, paralēlas ielādes daļēja rakstīšana; `Likums` izdarīts 2026-10-09

34 argumentu forma salabota `a1a50da8` (2026-09-23); apakšpunktu (`getTechDKP`) josla pārcelta uz ierakstu «Dzīvās sēdes apakšpunktu balsojumi» zemāk. Paliek mazi labojumi ((b) izdarīts 2026-10-09):

- **(a)** `parse_agenda_snapshot` iesniedzēju laukā ienāk troksnis (`" [ref=…`, `DKP izskatīšanas gaita`, `(Referents: …)`) — `src/saeima/parsing.py:48-56`.
- ~~**(b)**~~ **IZDARĪTS 2026-10-09** (`029e149d`): iznākums «Likums» → `pieņemts` jebkurā lasījumā (`src.saeima.bills.derive_bill_denorm()`); `scripts/recompute_bill_status.py` pārrēķināja 72 no 540 likumprojektiem — 65 «Likums» (39 3. lasījumā, 26 steidzami 2. lasījumā), 3 `noraidīts`→`procesā` (1302, 1286, 1349/Lp14 — priekšlikums vairs neaizstāj tās pašas dienas lasījumu), 4 tikai posma nosaukums. Vaicājums: jaunākā `stage_kind='vote'` posma `stage_result` pēc `derive_bill_denorm` kārtības; atkārtots dry run = 0. Rollback `data/rollback_recompute_bill_status_2026-10-09.sql`.
- **(d)** 5 balsojumi ar `result='Likums'` 2026-08-20 bez `bill_id` (7916 1066/Lp14, 7922 56/Lp14, 7924 1064/Lp14, 7925 1485/Lp14, 7926 1463/Lp14) — balsojums nav piesaistīts likumprojektam: 1066, 1064, 1485/Lp14 `saeima_bills` nav vispār; 1463/Lp14 ir, bet rāda `procesā`; 56/Lp14 ir un jau `pieņemts`. Piesaiste tikai caur `append_bill_stage()` (inv. #12). Vaicājums: `SELECT id, document_nr FROM saeima_votes WHERE result='Likums' AND bill_id IS NULL`.
- ~~**(e)**~~ **IZDARĪTS 2026-10-09** — `tiesneša_amats` (33) un `Lm14 cits` (38) «Pieņemts» → `pieņemts` (CHANGELOG 2026-10-09 (6)). Paliek:
  - ~~**(e1)**~~ **IZLEMTS 2026-10-09 (operators): atteikta iekļaušana = `noraidīts`** — projektu vairs neskata; posmu sarakstā redzams precīzais solis. Kods nemainās. Bija: Noraidīta iekļaušana darba kārtībā rāda lēmumu kā `noraidīts`: 1083, 1120/Lm14 (posms `procesuāls`/`iesniegts`, rezultāts Noraidīts) un «Par lēmuma projekta … iekļaušanu» rindas 1084, 1117, 1124/Lm14 (kopš 2026-10-09 visi posmi `procesuāls`/`iesniegts`; noraidījuma noteikumam nav procedūras izņēmuma). Vai «atteica iekļaut darba kārtībā» = «noraidīts»? Vaicājums: `SELECT b.document_nr, s.stage_name, v.motif FROM saeima_bills b JOIN saeima_bill_stages s ON s.bill_id=b.id JOIN saeima_votes v ON v.id=s.vote_id WHERE b.current_status='noraidīts' AND b.bill_type='Lm14' AND v.motif LIKE '%iekļaušanu%'`.
  - **(e2)** `Paziņojums` iznākums: 1108/Lm14 ķēde (Pieņemts→Paziņojums) un 16 `Paziņojums` rindas paliek `procesā` — kopā ar esošo 8305 jautājumu.
- **(c)** Paralēla Saeimas ielāde un `morning_ingest.py` vienā DB var atstāt daļēju rakstīšanu: `store_vote` apstiprina balsojumu, bet `generate_claims_from_votes` nomirst ar «attempt to write a readonly database» (balsojums 8211, 09-17: 16/74 claims, salabots ar idempotento atkārtojumu uz 74/74). Risks paliek, kamēr claim ģenerēšana nav vienā transakcijā ar `store_vote`.

*Īpašnieks:* operators (koda darbs). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [OPEN] Dzīvās sēdes apakšpunktu balsojumi — automātisks saucējs (`nr={actualXML_DkId}` ∪ `getTechDKP`); šobrīd tikai rokas paritāte

- **Problēma:** dzīvā sēdes dienā apakšpunktu balsojumi (priekšlikumi, «iekļaut nākamās sēdes DK», «nodot komisijai», papildu reģistrācijas) redzami tikai `DK?ReadForm&nr={actualXML_DkId}` formā vai caur `getTechDKP?OpenAgent&dkp={unid}&tLevel=1&actual=1` (`hasTechChilds` = `[29]`); `active=1`/`actual=1` lapas tos nerenderē. Helperis `getTechDKP` neseko (`scripts/p3_backfill_year_urllib.py:109-110` «NOT followed»), un `actualXML_DkId` kodā ir tikai STOP teksts (`scripts/audit_saeima_agenda_parity.py:174`). Viltus zaļais pats ir slēgts (`_live_session_stop()`, exit 2).
- **Instances:** 09-10 rokas paritāte pret punktu etiķetēm palaida garām 5 no 21 balsojuma (ielādēti 09-14); 09-17 — 5 no 37.
- **2026-09-27 (svētdiena):** kalendārs 09-24 sēdi joprojām rādīja kā `active=1` — UUID netiek piešķirts nākamajā dienā, tāpēc pēdējai sēdei rokas paritāte pret `nr={actualXML_DkId}` ir parastais ceļš, ne izņēmums. 09-24: 11/11 savas DK balsojumi ir DB; 09-17 turpinājums 107/107.
- **Rīcība:** izsaucēja pusē katram `hasTechChilds=1` punktam atsevišķs `getTechDKP` fetch (atbilde nes tos pašus 34 argumentu `drawDKP_*`, ko salabotais helperis jau parsē) un automātiska paritāte pret `nr={actualXML_DkId}`. Līdz tam — rokas paritāte pret `nr=` formu, ne pret punktu etiķetēm.
- **Īpašnieks:** operators (koda darbs). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [OPERATOR] `_motif_to_topic()` — komisijas nosaukums izvēlas tēmu; nodošanas klauzulas nogriešana skartu 25 no 973 vēsturiskajiem balsojumiem

**Problēma.** Nodošanas motīvs nes komisijas nosaukumu («Par nodošanu Izglītības, kultūras un zinātnes komisijai. Par …»), un pirmais sakrītošais celms bieži ir komisijas, ne likumprojekta vārds. Mērījums 2026-09-25: ja pirms kartēšanas nogriež klauzulu `nodošan\w*[^.]*?komisij\w*\.?`, **25 no 973** balsojumiem ar «komisij» motīvā maina atvasināto tēmu (09-15: 26 no 952); tie skar **2 181** `saeima_vote` claims, un 11 no 25 aiziet uz `Valsts pārvalde` fallback (komisijas vārds bija vienīgais signāls). Migrācija prasa kolīziju vaicājumu (`topic` ir idempotences atslēgā), bez re-embed.

**Lēmums operatoram:** (a) nogriezt klauzulu kodā + migrēt 25 balsojumus ar pāra rollback; (b) nogriezt tikai jauniem ielādējumiem (vēsture paliek nekonsekventa vienam likumprojektam); (c) atstāt. Vaicājums: `SELECT id, motif, topic FROM saeima_votes WHERE motif LIKE '%komisij%'` + `_motif_to_topic(re.sub(pat, '', motif))`.

**Saucējs, ne rīcība:** tajā pašā paraugā 104 no 973 glabātais `topic` ≠ pašreizējās `_motif_to_topic(motif)` izvads — funkcija kopš ielādes ir mainījusies; tas nav migrācijas saraksts (CLAUDE.md: `topic` ir idempotences atslēgā). Slēgtā 09-10 daļa: CHANGELOG 2026-09-15 (1).

### [OPERATOR] 15. Saeima — kods gatavs sasaukuma maiņai; pārslēgšana ir operatora solis pēc LIVS15 atvēršanas

- **Problēma:** kods nav atkarīgs no sasaukuma (commiti „15. Saeimas gatavība, 1/5–5/5”), bet `SAEIMA_CONVOCATION = 14` — līdz pārslēgšanai ielāde iet uz `LIVS14`.
- **Rīcība:** `docs/plans/2026-09-27-15-saeima-sasaukums.md` § Pārslēgšanas diena.
- **Zināms ierobežojums:** `scripts/check_new_session_votes.py` pieņem tikai sēdes UUID un vienmēr lieto pašreizējā sasaukuma bāzi. Iepriekšējā sasaukuma UUID dod 0 balsojumu saišu — skripts tad apstājas (STOP, exit 2), nevis klusi ziņo „NAV JAUNU”.
- **Pēc pārslēgšanas:** atjaunini `parties.coalition_status` uz 15. Saeimas koalīciju un atgriez Personu lapas partiju rail grupēšanu (`backlog/vietne-ui.md`, atlikta 2026-10-09).
- **Īpašnieks:** operators. **Trigeris:** `LIVS15` kalendārs atbild 200 (2026-09-27: 401).
