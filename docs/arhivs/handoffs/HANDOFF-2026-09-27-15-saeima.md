# Handoff 2026-09-27 (rīta sesija) — 15. Saeimas gatavība, 09-24 sēdes pārbaude

**Stāvoklis (vakars):** rutīna 2026-09-27 publicēta (pēdējais deploy `ffd0bec2`, līdzi 28.04. labojums); `verify_host` 9/9, varianti 4/4 → 200. Pushots. Dienas gaita — `git log` 2026-09-27 (katram labojumam skripts + rollback).

**Nākamā sesija:** nedēļas pārskats 2026-09-21 līdz 2026-09-27 (`@weekly-brief-writer`, `wiki/operations/weekly-routine.md`; iepriekšējais — #625, 09-14…09-20).

## Izdarīts (rīta sesija)

- **09-24 sēdes pilnīgums** (09-25 handoff § Gaida operatoru 2): savas darba kārtības balsojumi 11/11 ir DB (rokas paritāte pret `nr={actualXML_DkId}` — kalendārs svētdien sēdi vēl rādīja kā `active=1`); 09-17 turpinājums 107/107. Apakšpunktu balsojumu pilnīgumu šis audits neredz (DB 168 rindas pret 118 redzamiem) — `backlog/saeima.md` § Dzīvās sēdes apakšpunktu balsojumi.
- **15. Saeimas gatavība** — commiti „15. Saeimas gatavība, 1/5–5/5” + noslēguma labojumi, CHANGELOG 2026-09-27 (1). Sasaukums vienā vietā `src/saeima/convocation.py` (paliek 14). `check.sh` zaļš: 3131 passed, 3 skipped; `check_output` 1073 lapas.
- **Birku CSS pārsaukts** (`bill-pill-lp14` → `bill-pill-lp` u.c.). Lokāli pārrenderēts `bills,balsojumi,politiki,static` — vecās klases 0 lapās. Live kopš vakara deploy.

## Gaida operatoru

- **Pārslēgšana uz 15. Saeimu** — `docs/plans/2026-09-27-15-saeima-sasaukums.md` § Pārslēgšanas diena (trigeris: `LIVS15` kalendārs → 200; 2026-09-27 atbild 401). Pārbaudīts tikai ar konstantes pārslēgšanu testos.
- **Backlogā jau izsekotie lēmumi** no arhivētajiem handoffiem: F5 `migrations/` (`BACKLOG.md` § Atliktais), @AtminaLV retvīti, Zīles doc 93439 un laika joslas `mentioned` saites (`backlog/matcher.md`). Katra punkta pēda: `docs/arhivs/handoffs/README.md` § 2026-09-27.

_Atvērtie punkti no 12 arhivētajiem handoffiem, kas nav pierakstīti nekur citur (pārbaudīts 2026-09-27; iekavās — avota handoffs):_

- **Doc 95002** — pid=1 Rinkēvičs ir `subject`, bet viņa vārda tekstā nav (T1); junction rindu dzēst ar rollback (09-02 doc-audit).
- **Pretrunas #51 un #52 izskatītas 2026-09-27 — abas NEpublicēt, `confirmed=0` paliek:** #52 (Kulbergs/LPV) — «pirms» puse ir LETA pārstāsts bez citāta, LSM to pašu raidierakstu sauc par «skeptisku», Kulbergs 23.08. apstrīd interpretāciju; tā ir precizēšana, ne pretruna. #51 (Pūpols/Ģertrūdes aplis) — maiņa īsta, bet jau aprakstīta 28.04. dienas un 03.05. nedēļas pārskatā; atsevišķa pretrunas lapa neko nepievieno. Piezīme: 28.04. pārskatā virziens apgriezts («no kompromisa uz apturēšanu» — pēc tvītiem 22.04. apturēšana → 24.04. kompromiss) — LABOTS un live 2026-09-27 (`scripts/fix_brief_174_pupols_2026-09-27.py` + rollback).
- **Citāti pozīcijām bez `quote`:** #718013 Kučinskis — rediģētajā LSM rakstā (doc 114519) tagad ir burtisks citāts (09-24); #718005 Abu Meri — burtisks citāts nra.lv (doc 117622) (09-26 vakars).
- **Datumi:** #724919 Braže `stated_at`, iespējams, 09-25, ne 09-26 («Globuss» ēterā 25.09.) (09-26 vakars); doc 114881 (leta.lv) bez `published_at` (09-23 nakts).
- **Pārklājošās pozīcijas:** #718086 Smiltēns daļēji atkārto #718085; Baško partiju finansēšanas tēze stāv divās tēmās — #615866 (Korupcija un KNAB) un #718100 (Koalīcija un partijas) (09-23 nakts).
- **Saeimas kods:** `append_bill_stage()` noraida posmu `1.lasījums priekšlikums` — balsojumu 8258/8293/8294 posms ierakstīts kā `nezināms`; `Lm` dokumentu iznākums glabājas kā «Paziņojums» arī pieņemtam balsojumam (8305, 1108/Lm14, 57:17:1) (09-24).
- **Saeimas dati:** balsojuma 7190 (977/Lp14, 2025-06-12, iekļaušana darba kārtībā) kopsavilkums nokopēts no balsojuma 771 (nodošana komisijām), tāpēc nepareizs; 1168/Lp14 balsojumam 6192 nav kopsavilkuma; sv#1739 (217/Lp14 priekšlikums Nr. 16, 2024-05-09) — satura DB nav; ja tas ir DUS alkohola aizliegums, tas skar Bērziņa #532031 (09-24, 09-26 vakars).
- **Atgūšana:** 9 Vēstneša pāri (MK protokoli, doki 116793/116794) (09-26); Latkovskis doc 115440 — pid 114 `mentioned`, 0 pozīciju (09-24); 80 politiķi, kurus 09-23 piesaistu pārrēķins pazemināja uz `mentioned` — daļai pilnajā tekstā var būt sava pozīcija, pāri `data/rollback_backfill_relink_2026-09-23.sql` (09-23 diena2).
- **Aklās zonas josla rutīnā?** 09-26 mērījums: pozīciju deva 5 no 18 pāriem ar runas signālu, 0 no 16 bez tā (`docs/audits/2026-09-26-akla-zona/`). Lēmums — vai `recovery_survey()` atgriezt signāla pārus kā rindu; saistīts ar `backlog/agenti-pipeline.md` § `find_inversions` (09-26 pēcpusdiena).
- **`print_routine()` pēc pusnakts** noklusē uz kalendāra dienu — rutīnas dienu padod ar roku (apzināti nemainīts, runbookā nav pierakstīts) (09-25).
- **Sīkumi kodā, nav steidzami (09-25):** nedēļas loga kortežs būvēts divreiz, un divi pretrunu skaita palīgi dala SQL (`src/briefs.py`); promptu vārts neķer `strftime('%Y-%m-%d', col) = ?` / `substr(col,1,10) = ?` formas (šobrīd 0); pārgadu turpinājums (dec. → jan.) audita 3. vārtos iziet ar 2 un maldinošu padomu; `src/render/blog.py` kājenes komentāra pirmais teikums apraksta pāreju pa pārskata datumu, kods — pa rindu.
