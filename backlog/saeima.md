# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Saeima

### [DEFERRED] `saeima_votes.parent_vote_id` — priekšlikuma balsojuma sasaiste ar bāzes balsojumu

Priekšlikumu balsojumi jau ienāk caur agendas URL apvienību: `SELECT COUNT(*) FROM saeima_votes WHERE motif LIKE 'Par priekšlikumu Nr%'` → **2 467** (2026-10-21; 09-25 — 2 437, 07-25 — 1 452). Trūkst tikai sasaistes: kolonnas `parent_vote_id` nav (`pragma_table_info('saeima_votes')`). Vērtība — priekšlikumos redzama spriedze, ko vienprātīgs bāzes likuma balsojums slēpj.

*Trigeris:* pirmā publikācija, kurai vajag priekšlikumu ķēdi. *Rīcība:* kolonna + aizpildīšana pēc `document_nr` un lasījuma. *Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [DEFERRED] Komisiju balsojumu ievilkšana — jauns datu avots (operatora lēmums 2026-08-20)

- **Problēma:** komisiju balsojumi nefiksējas nekur (piem., Čulkovas «pret» airBaltic likumprojektam Budžeta komisijā 19.08.) — tā nav retorika (`position` neder) un nav plenārsēde (`saeima_vote` neder).
- **Rīcība:** izpētīt avotus (komisiju protokoli/audio saeima.lv, mediju reportāžas) un datu modeli — jauna `claim_type` vērtība vai atsevišķa tabula ar savu provenance ķēdi; NEjaukt ar `saeima_vote` (inv. #4b ir plenārsēdes balsis). Dizains pirms koda, ar plāna dokumentu.
- **Trigeris:** pēc 2026-10-03 vēlēšanām (§ Atliktais 43 — «atgriezties pēc kampaņas»).
- **Lēmuma īpašnieks:** operators (avota izvēle + apjoms).

### [FIX] Saeimas ielādes sīkumi — paralēlas ielādes daļēja rakstīšana (c), T21 ierakstīšana (f)

34 argumentu forma salabota `a1a50da8` (2026-09-23); apakšpunktu (`getTechDKP`) josla pārcelta uz ierakstu «Dzīvās sēdes apakšpunktu balsojumi» zemāk. (a), (b), (d), (e) izdarīti 2026-10-09…10-20 (CHANGELOG 2026-10-09 (6), 2026-10-17 (5); `git log --grep`). Paliek:

- **(c)** Paralēla Saeimas ielāde un `morning_ingest.py` vienā DB var atstāt daļēju rakstīšanu: `store_vote` apstiprina balsojumu, bet `generate_claims_from_votes` nomirst ar «attempt to write a readonly database» (balsojums 8211, 09-17: 16/74 claims, salabots ar idempotento atkārtojumu uz 74/74). Risks paliek, kamēr claim ģenerēšana nav vienā transakcijā ar `store_vote`.
- **(f)** Kolektīvo iesniegumu polaritātes slazds (vārti kodā kopš 2026-10-08, `ddd901c0`) kā T21 CLAUDE.md nav ierakstīts — tikai ar operatora «jā».

*Īpašnieks:* operators (koda darbs). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [OPEN] Dzīvās sēdes apakšpunktu balsojumi — automātisks saucējs (`nr={actualXML_DkId}` ∪ `getTechDKP`); šobrīd tikai rokas paritāte

- **Problēma:** dzīvā sēdes dienā apakšpunktu balsojumi (priekšlikumi, «iekļaut nākamās sēdes DK», «nodot komisijai», papildu reģistrācijas) redzami tikai `DK?ReadForm&nr={actualXML_DkId}` formā vai caur `getTechDKP?OpenAgent&dkp={unid}&tLevel=1&actual=1` (`hasTechChilds` = `[29]`); `active=1`/`actual=1` lapas tos nerenderē. Helperis `getTechDKP` neseko (`scripts/p3_backfill_year_urllib.py:109-110` «NOT followed»), un `actualXML_DkId` kodā ir tikai STOP teksts (`scripts/audit_saeima_agenda_parity.py:174`). Viltus zaļais pats ir slēgts (`_live_session_stop()`, exit 2).
- **Instances:** 09-10 rokas paritāte pret punktu etiķetēm palaida garām 5 no 21 balsojuma (ielādēti 09-14); 09-17 — 5 no 37.
- **2026-09-27 (svētdiena):** kalendārs 09-24 sēdi joprojām rādīja kā `active=1` — UUID netiek piešķirts nākamajā dienā, tāpēc pēdējai sēdei rokas paritāte pret `nr={actualXML_DkId}` ir parastais ceļš, ne izņēmums. 09-24: 11/11 savas DK balsojumi ir DB; 09-17 turpinājums 107/107.
- **Rīcība:** izsaucēja pusē katram `hasTechChilds=1` punktam atsevišķs `getTechDKP` fetch (atbilde nes tos pašus 34 argumentu `drawDKP_*`, ko salabotais helperis jau parsē) un automātiska paritāte pret `nr={actualXML_DkId}`. Līdz tam — rokas paritāte pret `nr=` formu, ne pret punktu etiķetēm.
- **Īpašnieks:** operators (koda darbs). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [OPERATOR] 15. Saeima — kods gatavs sasaukuma maiņai; pārslēgšana ir operatora solis pēc LIVS15 atvēršanas

- **Problēma:** kods nav atkarīgs no sasaukuma (commiti „15. Saeimas gatavība, 1/5–5/5”), bet `SAEIMA_CONVOCATION = 14` — līdz pārslēgšanai ielāde iet uz `LIVS14`.
- **Rīcība:** `docs/plans/2026-09-27-15-saeima-sasaukums.md` § Pārslēgšanas diena.
- **Zināms ierobežojums:** `scripts/check_new_session_votes.py` pieņem tikai sēdes UUID un vienmēr lieto pašreizējā sasaukuma bāzi. Iepriekšējā sasaukuma UUID dod 0 balsojumu saišu — skripts tad apstājas (STOP, exit 2), nevis klusi ziņo „NAV JAUNU”.
- **Pēc pārslēgšanas:** atjaunini `parties.coalition_status` uz 15. Saeimas koalīciju un atgriez Personu lapas partiju rail grupēšanu (`backlog/vietne-ui.md`, atlikta 2026-10-09).
- **Īpašnieks:** operators. **Trigeris:** `LIVS15` kalendārs atbild 200 (2026-09-27: 401).

### [OPERATOR] `Nebalsoja` skaitīšana — reitingi to neskaita, pārējās virsmas skaita; viens noteikums vai divi (2026-10-11)

Kods savienots 2026-10-18: noteikums dzīvo `src/scope.py` (`NOT_ATTENDANCE_SQL`, `not_attendance_sql()`, `CAST_BALLOTS`), un to importē profils, Personas, partijas lapa, Saeimas pusloks, meklētājs un bio sargs; `_fetch_politicians` profila tipam lieto `current_term_vote_counts()` tāpat kā Personas un meklētājs. Fikstūras renders pirms un pēc ir baitu identisks. *Paliek:* `src/render/rankings.py` (un sakritības metrikas `src/render/_common/enrich.py`) skaita tikai Par/Pret/Atturas — apzināti, jo mēra sakritību, ne klātbūtni. Lēmums: vai `Nebalsoja` skaitīt vienādi visur; līdz tam `tests/test_vote_count_single_rule.py::test_rankings_sample` ir `xfail(strict=True)`. Blakus atradums (nav labots): `src/wiki_pages.py:45` un `current_term_vote_counts()` skaita arī klātbūtnes rindas; profila tipam tas ir tikai slieksnis «> 0», šodien bez sekām (0 no 255 profiliem mainās). *Trigeris:* pirms 15. Saeimas pārslēgšanas. *Īpašnieks:* operators. Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 4.

### [OPERATOR] Jurēvica «Pret» 1030/Lp14 galīgajā lasījumā — motīvs no 08.10. stenogrammas (2026-10-12)

Trigeris: stenogramma publicēta (saeima.lv/lv/transcripts/category/29). Rīcība: izlasīt Jurēvica (pid 14) runu — viņš vienīgais «Pret» (42:1:33, JV frakcija atturējās); /deep-check 10-12 noraidīja kā FP3 (ķēdē strīds par naudas sodiem, ne partnerības normām). Pat apstiprināts — labākajā gadījumā `minor_shift`, ne publicējams. Īpašnieks: operators, nākamajā nedēļas rutīnā.

### [OPERATOR] `_vote_salience` — jaunās rindas labotas 2026-10-18; vai pārrēķināt glabāto `saeima_vote` salience

Kods labots 2026-10-18: lasījuma zars (`\b([123])\.\s*lasījum`) tiek pārbaudīts pirms nodošanas zara, un nodošanu ķer arī forma «Par nodošanu … komisijai» (`_REFERRAL_CLAUSE_RE`). Tests: `tests/test_saeima.py::TestVerdikti20261014::test_salience_reads_real_reading_formats`. Glabātās rindas NAV pārrēķinātas. *Saucējs (tikai lasot, 2026-10-18):* no 685 769 `saeima_vote` ierakstiem jaunā funkcija 183 296 rindām dotu citu salience nekā vecā (0,7→0,8: 101 519; 0,7→0,9: 76 470; 0,7→0,5: 5 214; 0,9→0,5: 93). Pret glabāto vērtību atšķiras 228 677 rindas, jo 44 162 steidzamības atzīšanas balsojumu rindas joprojām glabā 0,9, nevis C2 noteikto 0,4. Skaitļus dod [`docs/audits/2026-10-18-vote-salience/salience_denominator.py`](../docs/audits/2026-10-18-vote-salience/salience_denominator.py) (tikai lasa; `claims.source_url` = `_resolve_vote_url(saeima_votes.url)`, vecā funkcija nokopēta skriptā). Arī jaunajām rindām atvērts rubrikas jautājums: 23 balsojumi «Par priekšlikumu iesniegšanas termiņu … 1.lasījums, steidzams» saņem 0,9 kā lasījums, kaut balsojums ir par termiņu (`SELECT id, motif FROM saeima_votes WHERE motif LIKE 'Par priekšlikumu iesniegšanas termiņu%'` → 36, no tiem `_vote_salience` = 0,9 — 23; 2026-10-19). *Lēmums:* pārrēķināt (ar pāra rollback, eskalācija 8) vai atstāt; termiņa balsojumiem — 0,9 vai zemāk. *Īpašnieks:* operators.

### [BLOKĒTS] «Atradums» par pilsonību ar atsevišķu Saeimas likumu — gaida 15.10. stenogrammu (2026-10-20)

- **Saturs:** 14. Saeima — 11 piešķīrumi (10 atzīšanas likumi + 874/Lm14), visus iesniedza komisija; kas ieteica (LOK, federācijas, LZA); «pret/atturas» pieaugums kopš 2025-12 (0 → līdz 14); vēsture pa Saeimām. Piezīmes, labotas pēc pārbaudes (30 apgalvojumi: 23 apstiprināti, 4 laboti, 3 nepārbaudāmi): `docs/drafts/pilsoniba-2026/`. Apvienot ar agrāko izpēti `docs/tweet_bank/2026-10-18-pilsonibas-par-nopelniem-izpete.md` (22 gadījumi 2018–2026, ieteicēji, procedūra) — saucēji atšķiras, saskaņot pirms rakstīšanas. Višvanatu raksts papildināts 2026-10-20 ar reakcijām — jaunajā rakstā tās neatkārtot, saite uz `visvanati-pilsoniba-2026`.
- **Bloķētājs:** 15.10. stenogramma saeima.lv (2026-10-20 jaunākā 1.–8.10.). No tās: steidzamības balsojumi 82:3:0 (1586) un 71:8:6 (1587) — ārēji pagaidām tikai mūsu DB; kas runāja debatēs (vai NA).
- **Pirms publicēšanas arī:** `faction` NULL 105/975 2026. gada rindās (T6; `src/saeima/votes.py` — titania šūna tukša kopš 2026-04-16) → partiju sadalījumu publicēt tikai pēc noskaidrošanas; Kūtri citēt tieši ar atrunu, ne «padziļināti nepārbauda»; NA paziņojums «vērsīsies tiesībsargājošās iestādēs», iesniedzējs-deputāts nenosaukts (nedrīkst likt domāt, ka NA); komisijas izskatīšanas iznākums (Kūtris: «šonedēļ vai nākamnedēļ»).
- **Īpašnieks:** operators (publicēšana); izpildītājs — sesija pēc stenogrammas. *Trigeris:* saeima.lv/lv/transcripts/category/29 parādās 15.10.2026.

### [OPEN] Saeimas balsojumu tēmas — klasifikācija pa dokumentiem, 34. tēma «Saeimas darbs», partiju pārrakstīšana (2026-10-21)

- **Problēma:** tēmu izvēlas pirmais atslēgvārds virsrakstā; «Valsts pārvalde» = 2 056 ne-klātbūtnes balsojumi (atkritumu kaste); «vide» ķer komisiju nosaukumus (18/142 «Vide»), «dabas» ķer «dabasgāze»; 239/8 407 saglabātās tēmas ≠ šodienas kods. Latenta T2: `generate_claims_from_votes()` pārrēķina tēmu (`src/saeima/votes.py:815`) → pēc pārklasifikācijas atkārtota ielāde ievietotu dublikātus.
- **Dizains:** [`docs/superpowers/specs/2026-10-21-saeimas-balsojumu-temas-design.md`](../docs/superpowers/specs/2026-10-21-saeimas-balsojumu-temas-design.md). Secība: 0. fāze koda labojums → zelta kopa (~250 dok.) → atslēgvārdi/Jev/Claude salīdzinājums → partijas pa ~300 dokumentiem ar snapshot + rollback.
- **Progress (2026-10-22):** 1.–4. uzd. masterā (rubrika + zelta izlase 253 dok., `data/saeima_topic_gold/`). Piezīme 8. uzd.: 5 `multi` atslēgas dublē balsojumus, kas jau ir zem pareizā numura (piem., `motif:5916ea6611c7` = `1225/Lp14`) — `document_key` precizējums.
- **Progress (2026-10-22, 5. uzd.):** zelta kopa iezīmēta, rubrika 2026-10-22.1, 35. tēma «Ekonomika un uzņēmējdarbība» (operatora lēmums). Audits: `data/saeima_topic_gold/AUDITS.md`.
- **Operatora lēmums vajadzīgs pirms 9. uzd.:** budžeta likumos 92 % balsojumu (342/370) pieder citai tēmai nekā dokuments (katrs priekšlikums — savai nozarei); parastajos likumos 4,0 % (13/324). Plāna «mazā» `saeima_vote_topic_overrides` tabula budžetiem nozīmē ~200 balsojumu katram budžetam — kurš un kad tos marķē, ir dizaina jautājums.
- **Noklusējums līdz lēmumam (2026-10-22):** `plan` 4 budžeta likumus (152/Lp14, 430/Lp14, 757/Lp14, 1130/Lp14) izslēdz pēc `is_budget_law` (`src/saeima/topics.py`), un `classify` lasa tikai `batches.csv`, tāpēc to balsojumi patur pašreizējās tēmas.
- **Datu defekti `saeima_votes.summary`** (klasifikatori lasa šo tekstu): 6664, 7441 — steidzamības balsojumi ar priekšlikuma/nodošanas tekstu; 255/Lp14, 871/Lp14, 121/P14 — kopsavilkums neatbilst anotācijai/iesniedzējiem. Labojums ar rollback, atsevišķi. Papildus (b01 pārskatīšana 2026-10-22) IZLABOTI 22/Lp14, 1106/Lp14, 1153/Lp14 un 1185/Lp14 (9 balsojumi, `data/rollback_vote_summaries_2026-10-22.sql`).
- **b02 atradumi (2026-10-22):** (1) `motif:` atslēga no kaila «Par priekšlikumu Nr.N» var apvienot nesaistītus balsojumus — `motif:264f72e241b8` (2609 + 6686) nav iesaldēta, bet tās Jev lēmums («Aizsardzība un drošība») paliek lēmumu tabulā — ielādes mantošana aizvērta 22.10. (`_BARE_AMENDMENT_RE`, tests `test_bare_amendment_motif_never_inherits_decision`); DB tāda daudzbalsojumu atslēga ir tikai šī (vaicājums: `document_key` reason `no-number` + motīvs «Par priekšlikumu…»); atliek 2609/6686 piesaistīt dokumentam (2609 → 698/Lp14) ar rollback. (2) Kļūdaini/tukši `summary`: 2609 (sauc par procesuālu; ir 698/Lp14 2. las. priekšlikums), 980/Lp14 (iesniedzējs — Valsts prezidents, ne MK; 2./3. las. «Pirmajā lasījumā»), 946/Lp14 3. las. (atkārto 2. las.), 967/Lp14 (steidzamības balsojumam 2. las. rezultāts), 1096/Lp14 2. las. («pirmajā lasījumā»), 111/P14 (motīvs «atzīšanu par steidzamu», bet tas ir pieprasījums); tukši 977, 207, 856, 760, 971/Lp14. (3) Rubrikas robi, ko izšķirt pirms b03: darba tiesības (1022/Lp14, 33/Lm14), mazākumtautības (727/Lm14), sabiedrības saliedētība (1572/Lp14), sabiedrības veselība (362/Lm14), kriminālsodi nozares likumā (337/Lm14), personu apliecinoši dokumenti (96, 1343/Lp14 → pagaidām «Valsts pārvalde»), pilsonības atņemšana drošības nolūkā (861/Lm14, 1574/Lp14 → pagaidām «Sociālā politika»). (4) **Ielādes risks:** b02 11 nepareizajos auto lēmumos Jev pārliecība 9 reizes ≥ 0,9 (3 reizes 1,0) — ielādes slieksnis 0,9 (8. uzd.) neaptur kļūdas, kas rodas no plāna kopsavilkuma vai likuma nosaukuma; jauniem balsojumiem tēmu pārbaudīt pēc ielādes vai dot Jev anotācijas tekstu. (5) Kārtības rullis jau otrajā partijā aiziet nepareizi (267, 975/Lp14) — noteikums pirms Jev.
- **Rubrikas robeža (b01):** politiski represētās personas statuss (1230/Lp14, 1232/Lp14) — «Sociālā politika» vai «Ukraina un Krievija»? IZLEMTS 2026-10-22: «Sociālā politika»; 676/Lp14 → «Tieslietas» (b01q; direktīva 2016/800).
- **35. tēmas sekas pozīcijām:** aliasi «Ekonomika»/«Inovācijas» tagad normalizējas uz jauno tēmu → ja dokumentu ar «Budžets un finanses» pozīciju ekstrahē no jauna, rodas otrs ieraksts (T2). Esošo ekonomikas pozīciju pārskatīšana — atsevišķs darbs ar rollback. `src/saeima/claims.py` karte vēl satur ne-kanonisko «Irāna» (normalizējas uz «Ārpolitika»).
- *Īpašnieks:* sesija pēc operatora apstiprināta plāna.
