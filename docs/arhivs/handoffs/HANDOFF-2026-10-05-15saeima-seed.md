# Handoff 2026-10-05 — 15. Saeimas jaunie deputāti (Task 1–5)

> **Statuss:** plāna `docs/plans/2026-10-05-15-saeimas-deputati.md` Task 1–5 izpildīti un pārskatīti (task review katram + gala review «Ready»). **Vārti B ciet:** `https://dati.cvk.lv/SV2026/ieveletie-deputati/` 2026-10-05 — 404 (CVK indeksa saite uz šo slug apstiprināta). DB jaunie deputāti NAV ievadīti.

## Izdarīts

- **Kohorta** `data/seed/15saeima_kohorta.yaml` — 54 rindas no provizoriskā aprēķina; dzimums pārbaudīts visām 54; `role` «15. Saeimā ievēlēts/ievēlēta — <saraksts>, <apgabals>».
- **`scripts/cohort_15saeima.py`** `build` / `preview` / `emit-sql`. emit-sql STOP pie vārda (ASCII-locīts) vai X handle (bez reģistra) sadursmes; `WHERE NOT EXISTS`. Priekšskatījums `docs/drafts/15saeima_preview.md` (docs_scanned 61 028; ~2 min — palaid fonā).
- **Matcher** (CHANGELOG 2026-10-05): kopīgo formu noteikums + `_COMMON_WORD_FORMS` 5 uzvārdiem.
- **3 vārdabrāļu saites dzēstas** (123724, 124096 → pid 5; 122050 → pid 236), rollback `data/rollback_fix_15saeima_homonym_links_2026-10-05.sql`, 128 259 → 128 256.
- **X konti:** 14 pieņemti (orķestrators pārbaudīja 20/20 kandidātus caur fxtwitter), 6 vāji → null (operatora lēmums).
- `check.sh` uz HEAD (pēc visiem commitiem): «all checks passed»; iepriekšējais kritums (BACKLOG indeksa sinhronizācija no plāna commit) labots 8c3d47d8.

## Operatora lēmumi 2026-10-05

Matcher izmaiņu paturēt · 3 saites dzēst · sadzīves vārdu sargs 5 (ne 11) · 6 vājos X kontus nepievienot. Pieņemts bez jautāšanas: žurnālistu fona ievēlētie (Ločmele, Šafraneka, Ābola, Āboliņš, M. Ozoliņš) → `tracked` / `first_party` (ievēlēti deputāti, Seržanta precedents).

## Nākamais (vārti B)

1. CVK oficiālais saraksts → Task 6: `parse-official` + diff pret aprēķinu `(name, region, list_nr)`; ≠100 = STOP; `emit-sql`; dry-run kopijā; operatora «jā».
2. **Līdz vārtiem B kļūdainās saites krājas** (gala review I1): «Kleinberga» → 5, «Stepaņenko» → 236, «Zivtiņš» → 153, «Klementjevs» → 97, «Ivanova» → 92. Tieši pirms/pēc seedēšanas atkārto Task 4 lasīšanu VISIEM pieciem pāriem (pirms rescan).
3. Operatoram vārtu B kārtā pateikt: pēc seedēšanas Kleinbergs zaudē kailo «Kleinberga/u» (59 dok./90 d), Ivanovs «Ivanova/u» (35).
4. Neizlemts: **«Šleseri»** (Danas akuz. = ģimenes daudzskaitlis, 3 dok.).
5. Blakus: Jūlijai Stepaņenko (236) nav X handle — `@StepanenkoJulij` (atsevišķs labojums ar rollback). Raimonds Vējonis (AS, Latgale) = bijušais prezidents, `@Vejonis`.
6. Task 7 (rescan kopijā + T13 visiem 54) — tā diff parādīs arī 92 dokus, kuros matcher izmaiņa noņemtu esošas saites (Bērziņa/Liepiņa/Kozlovska/Lūsi; saraksts nav saglabāts, atjaunojas ar rescan diff). Task 8 (bio, render, deploy — ar atļauju).

## Atjauninājums 10-05 dienā (operatora lēmums: seedot pirms CVK oficiālā saraksta)

- **Seedēti 52** (Morozs, Plaude gaida oficiālo — cīņa 7/15 balsis), Lūse (206) atpakaļ `tracked`; 14 X konti; CVK bio 53/53; 1588 vēsturiskās saites (T13: 41 nepareiza izslēgta); `_FULL_NAME_ONLY` Ozoliņam/Jakovļevam; «Keiss» forma noņemta; pid 97 4 saites dzēstas. Visam rollback `data/*_2026-10-05.sql`.
- **VAD:** 538 deklarācijas 42 pid ar `vad_disambig` filtriem; ģimenes audits 42/42 OK (`docs/drafts/vad_15saeima_*`). 2 ielādes defekti → `backlog/vad.md`.
- **Publicēts:** neatkarīgs audits PASS WITH NOTES (0 bloķētāju, `docs/drafts/15saeima_prepublish_audit.md`), check.sh 3308 passed, deploy `b2fb9095`, verify_host 9/9.
- **Atvērts:** CVK oficiālais saraksts → diff + Morozs/Plaude; Lūses 6 vecas svešas saites («Lūsis», «T. Lūse») — fix ar rollback + negative_patterns pēc operatora; Dimants — vājākā VAD sasaiste (Jev pārbaude pēc izvēles); VAD gada cilnēs angļu «annual/start» (bija arī agrāk); Jūlijas Stepaņenko handle `@StepanenkoJulij`; «Šleseri» lēmums.

## Nākamajai sesijai (operatora uzdevums 10-05: «salabot + backlog saites + palaist analīzi»)

**A. Saites — labot (ar pāra rollback, pēc operatora «jā» par paterniem)**
1. **Lūse (206), 6 svešas saites:** 25955, 26219 (Toms Lūsis), 47635, 67543 («Lūsis»), 42842 («Lūsija Šmoldasova»), 45468 (Vēstnesis, «T. Lūse»). Kopā ar `backlog/matcher.md` § «Lūša ≤4 zīmju formas» — Lūse tagad aktīva, tāpēc `Lūsi` forma kolidē ar Lūsi (174, inactive); izlemt `negative_patterns`/formu. Doc 122050 renderējas Lūses lapā, bet teksts vairs viņu nesauc (tiešraide pārrakstīta) → `suspect_at`, nedzēst (T19).
2. **10-04 handoff atlikumi:** Šlesera 7 nepiesaistītie web doki (123400, 123423, 123433, 123435, 124192, 124198, 124226 — lasīt, vai runā Ainārs); `subject` lomu inversijas 123749, 124250, 124194, 124191, 124209, 124168.
3. **`backlog/matcher.md`:** stale junction 50 rindas / 23 doki (mērķēta pārlāde, nedzēst uz klasifikatora vārda); fantoma `mentioned` no laika joslas (dizaina lēmums); «Šleseri» (Danas akuz.) lēmums.

**B. Analīze — palaist (fan-out = operatora «jā» ar aģentu skaitu)**
1. **Jauno deputātu vēsturiskās pozīcijas:** 1 478 vēsturiskās saites, bet doki jau `reviewed_at` → dienas rinda tos nepiedāvā; pozīciju 0 (arī Lūsei). Ceļš: `/historic-backfill` vai mērķēta ekstrakcija pa ≤12 politiķiem (`get_politician_documents(pid, days=N)`), sākot ar aktīvākajiem (Brencis, Kleinberga, Šlesere, Ločmele, Vējonis).
2. **Nepārskatīti `subject` doki aktīvajiem:** 1 363 (09-25; Kulbergs 284) — `backlog/avoti.md` § Vēsturisko dokumentu backlogi.
3. **Truncated backfill 3. partija:** 400 doki / 415 pāri ≈ 27 Opus aģenti (`docs/audits/2026-09-24-backfill-batch3/groups.json`) — operators teica «nedēļas beigās».
4. **BACKLOG 50(e):** visu atlikušo pozīciju pārskats (~6 000, ~125 aģenti) — tikai PĒC claim-extractor pārbūves.

**C. Sīkumi no 10-04/10-05**
- Indriksones `saeima_vote` «Iebilst pret» pie «atbalstīts 1. lasījumā (52:0)» (piem., 649045–651002) — pārbaudīt.
- Smiltēns 729887 iespējams `minor_shift` (serve.py «Pretrunu kandidāti»).
- Quality WARN: #729877, #729878, #729934 conf 0.6 bez `NEEDS_REVIEW`.
- TypeSafe ēnas 10-05 rīts: Kulbergs, Krauze, Dombrovskis vetoti, bet īsti → zelta zaudējumi `backlog/dati-db.md` žurnālā.
- Dimants (260) VAD — Jev same-person pēc izvēles; Jūlijai Stepaņenko `@StepanenkoJulij`; CVK oficiālais saraksts → Morozs, Plaude.

**D. Personu lapas filtrs «15. Saeima» — kodā, NAV deployots** (commit pēc 6b9f41c2): Ievēlētie 98, Jaunie profili 52, zīme «15. Saeima» kartītē. Pirms deploy: apskatīt lapu pārlūkā (desktop + mobilais filtrs) un operatora lēmumi — (1) galvenes «Deputāti» skaits 122 → 179, jo ievēlētie bez balsojumiem (arī Kulbergs, «Ministru prezidents») tagad «Deputāti»; (2) profila lapās kategorija nemainās. Deploy: `render --only=personas,static` + `deploy.sh --no-delete` ar atļauju. Pēc CVK oficiālā saraksta atjaunot `data/cvk_sv2026_ievēlētie.yaml`.

## Atjauninājums 10-05 pēcpusdienā — vēsturiskā backloga sweep + vārts 2b (ingest un rutīna NAV palaistas)

> **Nākamajai sesijai (operators: ingest + dienas pārskatu taisīs vēlāk):** šodienas rutīna (10-05) vēl nav sākta pēc pusdienlaika; zemāk ir viss, kas to ietekmē.

**Izdarīts** (sīkāk `docs/audits/2026-10-05-backlog-sweep/README.md`, CHANGELOG 2026-10-05 (2)):
- **Backlogs iztukšots:** 2 178 (pid, doc) pāri → 0 (`stale_extraction_pairs(db,'2026-10-05')` main 0, Vēstnesis 0). 223 Opus `claim-extractor` aģenti; **614 glabātas pozīcijas, 2 dublikāti dzēsti** (DB `position` 8 105 → 8 717; katras kārtas DB id = atskaišu summa). 3. truncated partija (400 doki) — 0 neizskatīti.
- **15. Saeimas jaunie deputāti:** 23 no 53 tagad ar pozīcijām (111 kopā; bija 0). Pārējiem 30 korpusā nav neviena `subject` doka — vajag vēsturisko meklēšanu (`/historic-backfill`, tā ir ielāde → operatora laiks).
- **Pretrunu medības** visām 604 sweep pozīcijām: 39 `contradiction-hunter` + 6 `devils-advocate` → **0 izdzīvojušu**, 360 noraidīti (`hunt_result.json`; `logs` rinda `contradiction_hunt` ar `date="backlog-2026-10-05"` — panelī «Pretrunu kandidāti» redzama (`src/dashboard/views/candidates.py` filtrē pēc `timestamp`), rutīnas 3. soli NEzaļo, pārbaudīts `_hunt_logged_for(db,'2026-10-05')` = False). `pending_contradictions.json` nav vajadzīgs.
- **Labojumi ar rollback** (`data/rollback_*_2026-10-05*.sql`, katrs commitēts pirms piemērošanas): Lūses 6 svešas saites; Šlesera 7 saites; 6 lomu inversijas; 226 atgūtie runātāji `mentioned` → `subject`; NBS viltus saite 31797 («NBS» t.co saitē); Kola vārdabrālis 107774 (ASV sūtnis Coale); Stepaņenko `@StepanenkoJulij` (pievienots `social_accounts` — nākamā ielāde viņu ievāks); NEEDS_REVIEW 4 pozīcijām; confidence 0.65 #730145, #730153; Dārznieka #729967 stance + reembed; dublikāti #730228, #730569 dzēsti.
- **Vārts 2b** (`src/routine.py::stale_extraction_pairs`, slieksnis 20, bāzlīnija 0) + `scripts/plan_stale_sweep.py` + `wiki/operations/stale-sweep-brief.md`; Vēstneša paraksta-pāru zīmogs `scripts/stamp_vestnesis_signatures.py` (`/dienas-rutina` solis 1b); `/seed-entity` 10. solis. `check.sh` HEAD: 3323 passed, «all checks passed».
- **DB kopijas** (4 × 2,7 GB) no rīta sesijas scratchpad pārvietotas uz `E:\atmina\.scratch\2026-10-05-db-kopijas\` (operatora lūgums; C diskā 11 → 22 GB brīvi). Dzēst, ja vairs nevajag.

**Šodienas (10-05) rutīnai ZINĀT:**
1. **3. solis «N pozīcijas šodien»** ietver ~612 sweep pozīcijas (id 729966–730579, `created_at` šodien). Medībām pietiek ar ŠODIENAS ekstrakcijas pozīcijām (id > 730579).
2. **5. solis «136 politiķiem jaunas pozīcijas»** — tāpat uzpūsts ar sweep; spriedzes meklē tikai jaunajās šodienas pozīcijās.
3. **Dienas pārskata skeletā** (created_at zars) iekritīs 15 backloga pozīcijas ar `stated_at` 09-28…10-03: #730002, 730003, 730016, 730040, 730067, 730088, 730163–730166, 730256, 730257, 730259, 730298, 730315 — tas ir backlogs (jauno deputātu pirmsvēlēšanu tvīti u.c.), nevis 10-05 ziņas; `@brief-writer` jāpasaka.
4. **Personu filtrs «15. Saeima»** jau ir lokālajā `output/` (renderēts 10-05 rītā, apskatīts pārlūkā desktop + mobilais — strādā). Nākamais deploy to aizsūtīs live: galvenē «Deputāti» 122 → 179. Operatora lēmums pirms deploy. (Mobilajā šķirošanas rindas «POZ» nogriešana ir jau live lapā — vecs sīkums.) `check.sh` render 15:02 `output/` kokā ielika arī visas 614 sweep pozīcijas (arī `NEEDS_REVIEW` — render tās nefiltrē) un 226 lomu maiņas; tas ir paredzētais stāvoklis, bet deploy to visu aiznesīs.
5. ~~T9 3 `stale28` pozīcijām~~ — IZDARĪTS 10-05 vakarpusē (`@contradiction-hunter`: 0 kandidātu, 7 noraidīti; `logs` `contradiction_hunt` `date=backlog-2026-10-05`).
6. **Rutīnas 1b:** pirms ekstrakcijas plāna `stamp_vestnesis_signatures.py` (dry-run → `--write-rollback` → commit → `--apply`).

**Operatoram (lēmumi, nav darīts):**
- Lūses `negative_patterns` priekšlikums — `backlog/matcher.md` § Lūša formas.
- Releju žurnālistu tvīti rindā (Lapsa 99 pāri → 0 pozīciju) — `backlog/matcher.md` § «subject» lomai (3), papildināts ar lētāku variantu.
- «Šleseri» (Danas akuz.); Morozs/Plaude un ievēlēto saraksts pēc CVK oficiālā (10-05 15:00 vēl 404); Smiltēns 729887 `minor_shift` panelī.
- Doc 85876: Kulbergs runā («Iekārtas iepirkām, lādiņus aizmirsām nopirkt»), bet claim nav — doks rediģēts pēc izskatīšanas (`scraped_at` > `reviewed_at`); mērķēta ekstrakcija pēc izvēles.
- Indriksones «Iebilst pret … 52:0» = māsas balsojuma kopsavilkuma konvencija (BACKLOG § Ne-darīt), slēgts bez darbības.

## Deploy 10-05 vakarpusē (operatora atļauja čatā: «deploy tagad pirms nākamās sesijas un dienas rutīnas»)

- Pilns renders (`python -m src.render`, 252 profili) → `deploy.sh --dry-run` (check_output tīrs, 1154 lapas; publish-gate 0 bloķētas — 2 neapstiprinātās ir vecās 05-19/05-22, allowlist) → **deploy `0790b530`**, `verify_host` 9/9. Live tagad: personu filtrs «15. Saeima» (galvenē «Deputāti» 179), 614 sweep pozīcijas, lomu labojumi. Šodienas rutīnas 11. solis rādīsies kā ◐ pēc jaunākiem datiem — tas attieksies tikai uz rutīnas paša jaunajiem datiem.

- **Vēlāk 10-05:** personu lapa — noklusējuma filtrs «15. Saeimā ievēlētie» (98), aktīvo filtru čipi arī datorā, 15. Saeima filtru augšā, fasešu skaitļi (`b19a6fad`); deploy `12269d54`, `verify_host` 9/9. Atvērts operatoram: `--xv1-*` CSS mainīgie nav definēti `.pnv1-section` (viena rinda `assets/style.css`, maina lapas izskatu).

## Pārcelts no arhivētajiem handoffiem (10-05)

_Atvērtie punkti no 10 handoffiem, kas 2026-10-05 pārvietoti uz `docs/arhivs/handoffs/` un nav pierakstīti nekur citur (pārbaudīts pret git vēsturi, CHANGELOG, backlogu un DB, tikai lasot; iekavās — avota handoffa datums). Kur pārējie punkti — `docs/arhivs/handoffs/README.md` § 2026-10-05._

- **Junction lomas (DB 10-05 nemainītas):** doc 120049 — `subject` ir Rinkēvičs, bet runā Kulbergs (`mentioned`; viņa pozīcija #725109 glabāta); doc 120019 — Stepaņenko `subject`, bet tikai pieminēta; doc 120172 — pid 60 Stendzenieks bez vārda tekstā (T1?); doc 120749 → pid 200 «Krustpunktā» (T1?); doki 120708, 120684, 120676 — Abu Meri `subject`, bet nerunā (09-30). Vēstneša doc 121897 — `subject` Latvijas Banka, Rinkēvičs `mentioned` (10-01). Klase — `backlog/matcher.md` § «`subject`» lomai.
- **Vārdabrālis:** doc 123460 piesaistīts pid 25 kā `subject`, bet tajā ir CITS Viktors Valainis («Latvija pirmajā vietā» sarakstā); 0 pozīciju. Klase — `backlog/matcher.md` § Valaiņi (10-03).
- **Iespējams dublikāts:** #725139 Augulis (PVN degvielai, «Rīta Panorāma») pret #717891, attālums 0,409 (09-30).
- **Pozīcijas pēc izvēles:** Kulberga 2022. gada debašu citāts doc 118396 — ievadīt ar īsto datumu vai atstāt (09-28); Valaiņa «ZZS vērsies Satversmes tiesā» (Re:Check 120027) (09-30); Rinkēviča JEF detaļa trūkst #725099 (10-02); Zeltīta #725159 avots ir Velpa RT (doc 120751) — ja ielādē oriģinālo tvītu, pārlikt `source_url` (09-30).
- **Apzīmējumi runātāju atrunās:** 729761, 729767, 729770 nav izlemti (729744 un 729777 laboti 10-03) (10-02).
- **Redakcionālais noteikums nav ratificēts:** bijušā Progresīvo deputāta uzvārds izņemts no MŪSU stance tekstiem un pārskata #669 (apsūdzība nav celta); 10-02 tas pats izdarīts vēl 3 stance. Noteikums nav ierakstīts nevienā promptā vai runbookā. Ratificēt → ierakstīt `brief-writer.md` / `claim-extractor.md`; atsaukt → `data/rollback_<uzvārds>_anon_2026-10-0{1,2}.sql` + re-embed. Tvīti 121412 un 121286 X cilnē nav tīrīti (10-01).
- **Saeima:** 10-01 sēdes paritāte nav auditēta — 57 balsojumiem joprojām 0 `nr={UUID}` (DB 10-05); pēc manifesta pārģenerēšanas `audit_saeima_agenda_parity.py --dates 2026-10-01` (10-01, 10-02). Siliņa / sporta fonds 1380/Lp14 — pret 01.10. stenogrammu pārbaudīt, vai JV atmeta savu 3 % priekšlikumu (`rejected_candidates` #655815) (10-01).
- **Saeimas dati:** 1168/Lp14 balsojumam 6192 joprojām nav kopsavilkuma; sv#1739 (217/Lp14 priekšlikums Nr. 16, 2024-05-09) — satura DB nav, un, ja tas ir DUS alkohola aizliegums, tas skar Bērziņa #532031; `Lm` dokumentu iznākums glabājas kā «Paziņojums» arī pieņemtam balsojumam (8305, 1108/Lm14, 57:17:1) (09-24, 09-26).
- **Atgūšana:** 80 politiķi, kurus 09-23 pārrēķins pazemināja uz `mentioned` (pāri `data/rollback_backfill_relink_2026-09-23.sql`), un Latkovskis doc 115440 (pid 114 `mentioned`, `extracted_at` NULL). 10-05 sweep sedza tikai `subject` pārus, tāpēc šie nav pārbaudīti (09-23, 09-24).
- **Datums:** doc 114881 (leta.lv) joprojām bez `published_at` (09-23).
- **Sīkumi kodā (nav steidzami):** `print_routine()` bez argumenta joprojām ņem kalendāra dienu (`today_lv()`), ne rutīnas dienu — pēc pusnakts dienu padod ar roku, runbookā tas nav ierakstīts (09-25); nedēļas loga kortežs būvēts divreiz, un divi pretrunu skaita palīgi dala SQL (`src/briefs.py`); promptu vārts neķer `strftime('%Y-%m-%d', col) = ?` / `substr(col,1,10) = ?`; pārgadu turpinājums audita 3. vārtos iziet ar 2 un maldinošu padomu (09-25); balsojumu kartītes čips nedalītai frakcijai rāda kopskaitu zem vairākuma etiķetes (19 atturas + 1 nebalsoja → «20 atturas») (09-28); `src/quality.py` garumzīmju vārti noraidīja pareizu īsu teikumu bez garumzīmēm (pid 167, #11270) (10-01); `test_likumi_detail_pages_byte_identical` nav hermētisks — lasa dzīvos `wiki/laws/*.md` un krīt pēc katras sēdes wiki sync (10-01); Ņenaševas (pid 118) RT netiek glabāti, bet kursors virzās — klusa zuduma klase, ietekme zema (10-02).
- **Nedēļas pārskatam 28.09.–04.10.** (vēl nav uzrakstīts; pēdējais `weekly_brief` ir #653): tas aptver vēlēšanu dienu; 9 pozīcijas par Rinkēviča pārvēlēšanu (#729808–#729816, `stated_at=2026-10-02`) nav nevienā pārskatā; iemesla teikuma izgriešana #653 sadaļā «Kas kustējās» nav precedents (09-28, 10-03).
- **Tavars (pid 52):** `@Edgars_T` nav ne `social_accounts`, ne `x_handle` (DB 10-05) — seedēšanas kandidāts (09-30).
- **Operatora soļi:** publiskā spoguļa sinhronizācija (10-01 vakarā spogulis bija `c7e6eda`, stāvoklis līdz `59d81eca`); DMARC `p=quarantine` pēc 09-30 tīrām atskaitēm (10-01).
