# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Aģenti / pipeline

### [OPEN] Stance precizitāte rutīnā: neatkarīga pārbaude atrod 10–20 % defektu, aģenta pašpārbaude ne

2026-10-15 izlase 40 rutīnas pozīcijas → 8 defekti (4 precizitāte, 4 LV gramatika; `data/rollback_routine_sample40_2026-10-15.sql`); D4 partijā ~21 % (`docs/audits/2026-10-15-d4-atgusana/README.md`). Noteikumi promptā jau bija — teksts vien to nelabo. Izmēģinājums: `@stance-checker` (rubrika `docs/audits/2026-09-30-stance-izlase/RUBRIKA.md`) + `scripts/apply_stance_fixes.py` rutīnā pirms pretrunu soļa; Opus pēc noklusējuma, tas pats fails derīgs citam modelim (operators 10-15). Pastāvīgs solis `dienas-rutina.md` — tikai pēc operatora «jā» pēc izmēģinājuma. Atšķiras no `@quality-reviewer` § A: tas skatās izlasi (LIMIT 20) un pēc pārskata.

### [OPEN] Aģentu promptu optimizācija pēc claim-extractor v4 — audit-integrity → skripts, quality-reviewer uz RUBRIKA

Mērīts 2026-09-30 (`wc -c`, `grep` pēc datumiem/incidentu atsaucēm). v4 mācība (`docs/eval/claim-extractor-prompt-v4-2026-09-30.md`): garais prompts jau bija precīzs (A+B 0/24); pierādīts ieguvums bija **noteikums kodā** (`support`) + atrastās pozīcijas 24 → 28, ne pats saīsinājums. Tāpēc īsina tikai tur, kur ir izmērīta problēma vai reālas izmaksas, un katram prompta nesējam — eval pirms ieviešanas.

1. **IZPILDĪTS 2026-09-30** (CHANGELOG 2026-09-30 (3); prompts 315 → 58 rindas, 20/20 pārbaudes sakrīt dzīvajā DB). **`/audit-integrity` (36 KB, 57 datumu/vēstures atsauces) — pirmais.** SQL pārbaudes → `scripts/audit_integrity.py` ar testu katrai pārbaudei (denominators + mutācija); prompts tikai palaiž un nolasa. Eval nevajag — testi. Risks mazs.
2. **`@quality-reviewer` (29 KB) — otrais.** § A Pozīcijas (9 KB) dublē ekstraktora noteikumus; jālieto tā pati `docs/audits/2026-09-30-stance-izlase/RUBRIKA.md` definīcija (ekstraktors = vērtētājs = publicēšanas vārts), `support` tagad pārbauda kods. Vajag eval kā v4 (~15 Opus).
3. **`/dienas-rutina` (19 KB, 31) — ielādē katrā rutīnā.** Vēstures teikumi ārā kā CLAUDE.md 09-25 (`git show` rinda); noteikumi paliek.
4. **`@brief-writer` (29 KB, Self-Check 7 KB).** Daļu paškontroles → lint (`scripts/check_output.py` vai jauns); zema steidzamība, jo pārskatu operators pārlasa.
5. **Neaiztikt bez izmērītas problēmas:** `@saeima-tracker` (36 KB; Step 2 11 KB regex apraksts — kods jau ir `p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda`, bet kļūda maksā dārgi, T8), `@contradiction-hunter` (33 KB, lieto reti). Pārējie ≤14 KB — kārtībā.

6. **Noteikumi, kas gaida operatora «jā» vai «nē»:** (a) ~~`claim-extractor.md:80` «≤12 dokumentu pasē» neizšķir tukšus RT~~ — 2026-10-14 atkārtojās (#22 apstājās pie 11 no 20), tāpēc rindā ielikts `rt` paketes izņēmums (20 doki, bez «3 tukši pēc kārtas» STOP); operators apstiprināja 2026-10-14; (b) redakcionālais noteikums «bijušā PRO deputāta uzvārdu mūsu tekstos nelieto, kamēr apsūdzība nav celta» ievērots kopš 10-05, bet nav ierakstīts nevienā promptā — ratificēt vai atsaukt. (c) Astras 10-14 izlases ieteikumi (virs 5 rindu sliekšņa, nav ieviesti): `quote` beigu pieturzīmes pārbaude `save_analysis` validatorā (noķertu 737776); signāls «Informē/ziņo, ka» + citas institūcijas lēmums (737765 — relejs, dzēsts). Piezīme: `support` DB netiek glabāts, tāpēc izlases to nevar pārbaudīt.

*Īpašnieks:* operators. **Operatora lēmums 2026-09-30: secība pieņemta** — sākt ar 1. (audit-integrity → skripts); 2. (quality-reviewer) ar eval pirms ieviešanas, palīgu skaitu pasaka pirms palaišanas.

### [OPEN] Stance-fidelity atlikums: matcher neskenē `title`, paywall stop-gate nevar balstīties uz `is_paywall`

- **(b6) matcher neskenē `title`.** `src/matcher.py:977–1008` skenē tikai `content`. Pārmērīts 2026-09-25: `match_politicians(title)` pret junction, web, `scraped_at>=2026-08-26` → **23 pāri / 22 doki no 3 011** web dokiem ar virsrakstu (07-27: 33 pāri / 5 088) — NElasīti (T18). Instances: doc 4909 (vārds tikai virsrakstā), doki 80022/79087 (ķermenī tikai «Valsts prezidents»). *Rīcība:* 2. fāze ar `mentioned` lomu (`docs/plans/2026-07-27-matcher-koliziju-plans.md` § 4), tajā pašā reizē izlemt `d.title` pievienošanu `get_politician_documents()` SELECT-am.
- **(c) paywall stop-gate nevar balstīties uz `is_paywall`.** Neviens ingest ceļš kolonnu neraksta (`grep -rn is_paywall src scripts` → raksta tikai `video_ingest`; lasa `backfill_truncated_docs.py`, `audit_quote_fidelity.py`); `SELECT is_paywall, COUNT(*), MIN(scraped_at), MAX(scraped_at) FROM documents GROUP BY 1` → 351 rinda ar `1`, visas 2026-03-25…04-06 (no 103 394). Vārts uz šīs kolonnas nekad nenostrādātu. Paraksta doki («Lai turpinātu lasīt» / «Pilno rakstu lasiet») kopš 09-10 → 0, tātad «0 nemarķētu» ir tukšs rezultāts, ne pierādījums; #704199 (§ Atliktais 63) ir paywall stubs bez paraksta. *Rīcība:* koda vārts uz teksta/garuma pazīmes, analogs truncated-stub vārtiem (prompta noteikums «paywall stubam `confidence` reti > 0,6» jau ir).

*Īpašnieks:* operators. Rīks paliek atkārtojams: `scripts/audit_quote_fidelity.py` (read-only). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_agenti-pipeline.md`.

### [OPEN] Medību pēdas @contradiction-hunter (07-25 adversārā pārbaude + 08-03 ekstrakcija)

Neviena nav saglabāta kā pretruna (`contradictions` ar #69556, #10375, #615846, #615879, #10983, #527892, #689515, #17916, #95 → 0 no 35 pretrunām, 2026-09-25); visas prasa strukturālu, ne embedding pārbaudi. Valaiņa #17807 inversija labota 08-10 (`272952a6`).

1. **Krištopans airBaltic balsojumu pāris** — #69556 `Balsoja PAR: Par iespējamajiem valsts papildus nepieciešamajiem ieguldījumiem AS "AirBaltic"` (2025-06-19) pret #10375 `Balsoja PRET: ... valsts īstermiņa aizdevuma izsniegšanai` (2026-04-16). PIRMS citēšanas obligāta pilna `document_nr` ķēde (T14).
2. **Kulbergs solījums-pret-izpildi** — #615846: jūnijā «tūlīt šo birokrātisko murgu beidzam», augustā kavējas bez termiņa. T9 klase.
3. **Abu Meri pret savas ministrijas slieksni** — VM: drošai dzemdību palīdzībai vajag ≥500 dzemdības/gadā; Balvos 140/gadā, un ministrs aicina turpināt (#615879). Ministrs-pret-iestādi spriedze, ne personīga pretruna.
4. **Vītols #10983 (2026-04-16) ↔ #527892 (2026-06-11)** — kritizē airBaltic padomes priekšsēdētāju Martinovu par riska vērtējuma maiņu pēc iecelšanas, septiņas nedēļas vēlāk aizstāv neierobežotu personisku iecelšanas brīvību, pats pievienojoties valdībai. DA vērtē kā *a priori* vāju, bet prasa mednieka caurlaidi.
5. **Kulbergs NVO retorika↔rīcība** — «negribēju finansējumu atņemt» (07-20/07-22) pret faktiskajiem finansējuma lēmumiem; T9 klases pārbaude, iznākuma datu DB pagaidām nav.
6. **Šlesers Rail Baltica interešu leņķis** (2026-08-12) — pretruna 2019↔2026 atspēkota, bet paliek iespējams **interešu stāsts** (ģimenes tranzīta biznesa plāns 2019, doc 85794, pret #17916); nesējs būtu analīze/sintēze, ne pretrunu virsma.
7. **Hermanis (pid=29) MMN pašdefinīcijas maiņa** — #95 (2026-03-24) «nacionālisti, ar kristīgām vērtībām» pret 2026-07-14 «nevis kā konservatīvu labēji nacionālistisku spēku»; pirms citēšanas pārbaudīt, vai tās nav divas savietojamas asis.
8. **No handoffiem 10-04…10-10 (nav glabāts):** Smiltēns #729887 — iespējams `minor_shift`; Čulkova par Rosļikova neatgriešanos pret #704157 — pozīcija nav izvilkta; Siliņa / 1380/Lp14 — vai JV atmeta savu 3 % priekšlikumu (handoffā minētais #655815 ir cita deputāta balsojums — ID neder); sv#1739 (217/Lp14 Nr. 16) — vai tas ir DUS alkohola aizliegums, kas skar Bērziņa #532031.
9. **Braže #113 `reasoning`** min iespējamu spriedzi ar Sprūda retoriku — `political_tensions` kandidāts no 09-18 Jev viļņa, nav pārbaudīts (slēgtā ieraksta atlikums, verdikts B8).
10. **Vērot pēc valdības veidošanas:** Jurēvics #729904 (JV nebūs koalīcijā ar LPV) un Kulbergs #729943/#730584 pret faktisko koalīciju.

*Īpašnieks:* operators — kurš punkts iet `/deep-check`, kurš uz analīzi, kurš tiek izmests.

### [DEFERRED] `visual_brief_json` renderam miris, bet `@graphics-designer` to joprojām lasa — attēls un virsraksts var atšķirties

Kopš 2026-09-16 `src/render/blog.py` virsrakstu ņem no `content` bloka «## Vizuālais brief» (CHANGELOG 2026-09-16 (4)); sešu pārskatu jaunais virsraksts jau ir publicēts (2026-09-25: 6/6 lokāli un 3/3 pārbaudīti live ar jauno `og:title`). Kolonnu joprojām raksta `src/tools.py`, un `@graphics-designer` to lasa attēla promptam (`graphics-designer.md:14,38`), tāpēc pēc `content` labojuma attēls var sekot vecajam tekstam. *Rīcība:* (i) `@graphics-designer` pāriet uz `parse_visual_brief(content)` vai (ii) kolonnu izmest. *Īpašnieks:* operators.

### [OPEN] Vēstneša ingest pienāk PĒC analīzes loga — septembrī 16 no 18 dienām pēc 15:00

Akta uzrādīšanas vārts ieviests 2026-09-07 (`src/routine.py::vestnesis_acts_for()`, CHANGELOG 2026-09-07 (5)). Atvērts paliek tikai ievākuma LAIKS: Vēstnesis ir `scripts/morning_ingest.py` 4. solis (`:76`), tāpēc tas ienāk ar `morning_ingest` palaidienu. `MIN(TIME(scraped_at))` pa dienām, `platform='vestnesis'`: septembrī **16 no 18** dienām pēc 15:00 (izņēmumi 09-03 06:56, 09-23 10:20; augustā 32/34); oktobrī **11 no 13** dienām (2026-10-21; izņēmumi 10-05 08:33, 10-20 01:01).

*Rīcība:* izvēlēties — palaist Vēstneša soli atsevišķi pirms analīzes (ar roku; § Ne-darīt aizliedz ieplānotu ielādi), vai pieņemt «akts pārskatā nākamajā dienā» un ierakstīt `.claude/commands/dienas-rutina.md`. *Īpašnieks:* operators.

### [OPEN] Krossavota/divvalodu dublikāti — `possible_duplicate` tīkls kopš 2026-09-24; atliek pārmērīt 6. pārbaudes 101 grupu

- **Problēma:** viens izteikums ienāk korpusā vairākas reizes ar atšķirīgu `source_url` (divvalodu tvīts; viens notikums vairākos izdevumos, arī dažādos datumos; paša RT par savu tvītu), tāpēc idempotences trijnieks `(opponent_id, source_url, topic)` to nesedz. 08-25 vienā dienā noķerti 12 dublikāti; 08-12 #689553/#689555 (LETA → diena.lv) uzpūta pārskata sadaļu. Jauna instance: 52682 (lsm.lv) ↔ 52696 (nra.lv) no 09-23 backfill atskaites.
- **Kas ir:** koda tīkls `src/analyze.py:743–790` `possible_duplicate` (`stated_at` ±5 d + vektors; `beac0d35`, 2026-09-24, `tests/test_possible_duplicate.py`); `logs` nostrādāšanu neglabā, tāpēc dzīvā pierādījuma vēl nav.
- **Pirmā reālā nostrādāšana 2026-09-30:** Bražes 3 tās pašas dienas tvīti par Krievijas pilsoņa uzturēšanās atļauju — #725120 un #725121 pret #725119 (vektora attālums 0,373/0,374); aģents izvērtēja, ka saturs atšķiras (kompetence / «4 mēneši» / konkrēta prasība), un glabāja visus trīs. Tīkls ziņo, nebloķē — kā paredzēts.
- **2026-10-10:** Gorkšs #737551 pret #737520 (attālums 0,33) — aģents izvērtēja, ka saturs atšķiras, glabāja abus. Tīkla aklā zona: Bergholca #737561 (doc 130723, angļu valodas atkārtojums 10-09) dublēja #731042 (09-30) — 9 dienas, ārpus ±5 d loga; noķēra tikai pretrunu meklēšana, dzēsts ar `data/rollback_rutina_vakars_2026-10-10.sql`.
- **Neizlemts pāris (2026-10-05):** Augulis #725139 (doc 120027) ↔ #717891 (doc 113544), abi «PVN samazināšana degvielai» — dublikāts vai divi izteikumi.
- **Rīcība:** pārmērīt `/audit-integrity` 6. pārbaudes 101 grupu (§ Atliktais 57) ar līdzības filtru.
- **Īpašnieks:** operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_agenti-pipeline.md`.

### [OPEN] `find_inversions` — `speaks()` nosaka lomu pēc pieminējuma; aklās zonas raža nav triāžēta

- **(b) Viltus inversija:** `speaks()` joprojām nosaka lomu pēc pieminējuma, ne pēc runas akta (doc 99611: runājošs subjekts Hermanis atgriezts kā inversija). `find_inversions(days=7)` 2026-09-25 → **39 inversijas / 342 kandidāti** (nelasīti).
- **(a) Aklā zona — doki ar `mentioned`, bet bez neviena `subject`:** tagad skaitīta (`recovery_survey` `blind_no_subject`, `ae9d926d`, 09-24) → **543 doki / 7 d**; ražas triāža nav izdarīta. Blakus: ATGŪŠANA 7 dienās 34 pāri (web 32, vestnesis 2, twitter 0, x_mention 0) — pārbaudīt, vai josla vispār var trāpīt tvītam.
- **Secība:** vispirms labot (b), tad (a) ražas triāža uz 543 dokiem — citādi triāžā skaitās tie paši viltus pozitīvie. Ja raža < ~10 %, verdikts uz § Ne-darīt ar skaitli.
- **Raža izmērīta 2026-10-15 (D4, joslas ar subjektu, ne aklā zona):** `inversion`+`beside_subject`, web, ≥2 signāli, 90 d — 303 pāri → 155 pozīcijas (51 %). Atlikums (web 1 signāls 196, twitter 60, vestnesis 76) — operators. [`docs/audits/2026-10-15-d4-atgusana/`](../docs/audits/2026-10-15-d4-atgusana/README.md)
- **(f) IZPILDĪTS 2026-10-18:** `recovery_survey` un `pending_quoted_mentioned` izlaiž (doc, pid) pāri, kam claim ar to pašu `opponent_id` + `source_url` jau ir; skaits `already_claimed` ATGŪŠANA rindā. Dzīvajā DB 90 d: 1/142 atgrieztajiem (doc 96603 pid 189 — stampēts subjekts ar vēlāk pieliktu NULL `mentioned` saiti), izlaisti 3. `find_inversions` (audita pārbaude 15) tos joprojām skaita. **Atlikums:** filtrs (`src/quoted_speaker.py:280`, `:422`) pieņem jebkuru `claim_type`, tāpēc `commentary` vai `program_promise` par pid noslēpj pid paša pāri — sašaurināt uz `claim_type='position' AND COALESCE(speaker_id, opponent_id) = opponent_id`; izlaistie pāri netiek zīmogoti, tāpēc 15. pārbaudes bāzlīnija tos joprojām skaita (piezīme pie tās). *Īpašnieks:* koda darbs.
- **(d) Atgūšanas apsekojums neatceras izvērtēto:** pāri, ko atgūšanas aģents izlasīja un apzināti neglabāja (dublikāts / cita runa), paliek `print_routine` «ATGŪŠANA N pāri» rindā (2026-09-30: 3 no 6). Vajag izvērtējuma zīmi (piem. `logs` ieraksts pa (doc, pid)), citādi rinda nekad nenonāk līdz 0.
- **(e) Rindā nonāk pāri, kur politiķis tikai `mentioned`** (2026-10-11: doc 131135 Stendzenieks, 131197/131200/131202 Tavars) — `plan_extraction` tvēruma jautājums, nav labots.
- **Īpašnieks:** operators (izmeklēšana pirms koda). Pašcitēšanas daļa (c) slēgta 2026-10-14 (verdikts C8, `0429f5f0`).

### [OPEN] Sociālo melnrakstu kandidāti neņem vērā `confirmed` — arī atsauktas pretrunas

2026-10-23: `src/social_agent/candidates.py::fetch_pretrunas_candidates` atlasa VISAS pretrunas bez `confirmed` filtra: DB 2026-10-23 — 33 `confirmed=1`, 7 `=0` (nepārbaudītas), 3 `=-1` (atsauktas, `withdraw_contradiction`). Tātad pretrunu pavediena melnrakstā var nonākt atsaukta vai nepārbaudīta pretruna. *Rīcība:* pievienot `COALESCE(c.confirmed,1)=1` (kā `fetch_contradictions()`), tests ar `=-1` rindu. Publicēto melnrakstu no `confirmed<>1` pretrunām 2026-10-23: 0 (`social_drafts` `pillar='pretrunas' AND status='posted'` JOIN `contradictions`). Atrada Astra, pārbaudīts ar SQL.

### [OPEN] `morning_ingest.py --help` palaiž pilnu ielādi — skriptam nav argparse
- **Problēma:** skriptam nav argparse, tāpēc jebkurš arguments tiek ignorēts un sākas īstā ielāde (22.10. `--help | head -20` palaida ielādi, un `head` to nogalināja pēc 2. soļa — RSS + X ielādēti, pieminējumi/Vēstnesis/backstop nē; atkārtots palaidiens 5/5).
- **Rīcība:** argparse ar `--help` un nezināma argumenta atteikumu pirms jebkura soļa; tests, ka `--help` neizsauc nevienu soli. *Trigeris:* nākamais darbs `morning_ingest.py`.
