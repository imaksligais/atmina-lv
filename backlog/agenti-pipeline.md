# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Aģenti / pipeline

### [OPEN] Aģentu promptu optimizācija pēc claim-extractor v4 — audit-integrity → skripts, quality-reviewer uz RUBRIKA

Mērīts 2026-09-30 (`wc -c`, `grep` pēc datumiem/incidentu atsaucēm). v4 mācība (`docs/eval/claim-extractor-prompt-v4-2026-09-30.md`): garais prompts jau bija precīzs (A+B 0/24); pierādīts ieguvums bija **noteikums kodā** (`support`) + atrastās pozīcijas 24 → 28, ne pats saīsinājums. Tāpēc īsina tikai tur, kur ir izmērīta problēma vai reālas izmaksas, un katram prompta nesējam — eval pirms ieviešanas.

1. **IZPILDĪTS 2026-09-30** (CHANGELOG 2026-09-30 (3); prompts 315 → 58 rindas, 20/20 pārbaudes sakrīt dzīvajā DB). **`/audit-integrity` (36 KB, 57 datumu/vēstures atsauces) — pirmais.** SQL pārbaudes → `scripts/audit_integrity.py` ar testu katrai pārbaudei (denominators + mutācija); prompts tikai palaiž un nolasa. Eval nevajag — testi. Risks mazs.
2. **`@quality-reviewer` (29 KB) — otrais.** § A Pozīcijas (9 KB) dublē ekstraktora noteikumus; jālieto tā pati `docs/audits/2026-09-30-stance-izlase/RUBRIKA.md` definīcija (ekstraktors = vērtētājs = publicēšanas vārts), `support` tagad pārbauda kods. Vajag eval kā v4 (~15 Opus).
3. **`/dienas-rutina` (19 KB, 31) — ielādē katrā rutīnā.** Vēstures teikumi ārā kā CLAUDE.md 09-25 (`git show` rinda); noteikumi paliek.
4. **`@brief-writer` (29 KB, Self-Check 7 KB).** Daļu paškontroles → lint (`scripts/check_output.py` vai jauns); zema steidzamība, jo pārskatu operators pārlasa.
5. **Neaiztikt bez izmērītas problēmas:** `@saeima-tracker` (36 KB; Step 2 11 KB regex apraksts — kods jau ir `p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda`, bet kļūda maksā dārgi, T8), `@contradiction-hunter` (33 KB, lieto reti). Pārējie ≤14 KB — kārtībā.

6. **Noteikumi, kas gaida operatora «jā» vai «nē»:** (a) ~~`claim-extractor.md:80` «≤12 dokumentu pasē» neizšķir tukšus RT~~ — 2026-10-14 atkārtojās (#22 apstājās pie 11 no 20), tāpēc rindā ielikts `rt` paketes izņēmums (20 doki, bez «3 tukši pēc kārtas» STOP); operators apstiprināja 2026-10-14; (b) redakcionālais noteikums «bijušā PRO deputāta uzvārdu mūsu tekstos nelieto, kamēr apsūdzība nav celta» — ratificēts 2026-11-09, ierakstīts `claim-extractor.md` § 5 un `brief-writer.md` pašpārbaudes 19. punktā. (c) Astras 10-14 ieteikumi: citāta beigu pārbaude jau ir (`quote_end_mismatch`, kopš 2026-10-14; `tests/test_quote_end.py`); signāls «Informē/ziņo, ka» noraidīts 2026-11-09 (viena instance). Mērījums 2026-11-10: `quote_end_mismatch` karogo 129 web un 117 twitter citātus, un izlasē 7 no 20 web un 4 no 20 twitter karogiem bija pareizi citāti — precizējums (atribūcija aiz komata; jauns teikums ar lielo burtu) dotu 3 no 20 un 0 no 20; nav ieviests, operatora lēmums. Piezīme: `support` DB netiek glabāts, tāpēc izlases to nevar pārbaudīt.

*Īpašnieks:* operators. **Operatora lēmums 2026-09-30: secība pieņemta** — sākt ar 1. (audit-integrity → skripts); 2. (quality-reviewer) ar eval pirms ieviešanas, palīgu skaitu pasaka pirms palaišanas.

### [DEFERRED] Stance-fidelity atlikums: matcher neskenē `title`; tvnet maksas ievadi nav atšķirami (2026-11-10)

- **(b6) matcher neskenē `title`.** `src/matcher.py` skenē tikai `content`. Pārmērīts 2026-09-25: `match_politicians(title)` pret junction, web, `scraped_at>=2026-08-26` → **23 pāri / 22 doki no 3 011** web dokiem ar virsrakstu — NElasīti (T18). Instances: doc 4909 (vārds tikai virsrakstā), doki 80022/79087. *Rīcība:* 2. fāze ar `mentioned` lomu (`docs/plans/2026-07-27-matcher-koliziju-plans.md` § 4). *Trigeris (operators 2026-11-09):* skaits aug virs ~23 pāriem mēnesī.
- **(c) paywall vārti ieviesti 2026-11-10** (`src.quality.paywall_marker`, CHANGELOG 2026-11-10 (1)). *Atlikums:* tvnet maksas ievadus pēc teksta atšķirt nevar (266 vecie `is_paywall` karogi bez redzama marķiera, 1 doks ar frāzi) — vajadzētu lapas HTML. *Trigeris:* pozīcija no tvnet maksas ievada, ko noķer `@stance-checker`.

*Īpašnieks:* operators. Rīks: `scripts/audit_quote_fidelity.py` (read-only).

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

### [OPEN] Krossavota/divvalodu dublikāti — `possible_duplicate` tīkls kopš 2026-09-24; atliek pārmērīt 6. pārbaudes 101 grupu

- **Problēma:** viens izteikums ienāk korpusā vairākas reizes ar atšķirīgu `source_url` (divvalodu tvīts; viens notikums vairākos izdevumos, arī dažādos datumos; paša RT par savu tvītu), tāpēc idempotences trijnieks `(opponent_id, source_url, topic)` to nesedz. 08-25 vienā dienā noķerti 12 dublikāti; 08-12 #689553/#689555 (LETA → diena.lv) uzpūta pārskata sadaļu. Jauna instance: 52682 (lsm.lv) ↔ 52696 (nra.lv) no 09-23 backfill atskaites.
- **Kas ir:** koda tīkls `src/analyze.py:743–790` `possible_duplicate` (`stated_at` ±5 d + vektors; `beac0d35`, 2026-09-24, `tests/test_possible_duplicate.py`); `logs` nostrādāšanu neglabā, tāpēc dzīvā pierādījuma vēl nav.
- **Pirmā reālā nostrādāšana 2026-09-30:** Bražes 3 tās pašas dienas tvīti par Krievijas pilsoņa uzturēšanās atļauju — #725120 un #725121 pret #725119 (vektora attālums 0,373/0,374); aģents izvērtēja, ka saturs atšķiras (kompetence / «4 mēneši» / konkrēta prasība), un glabāja visus trīs. Tīkls ziņo, nebloķē — kā paredzēts.
- **2026-10-10:** Gorkšs #737551 pret #737520 (attālums 0,33) — aģents izvērtēja, ka saturs atšķiras, glabāja abus. Tīkla aklā zona: Bergholca #737561 (doc 130723, angļu valodas atkārtojums 10-09) dublēja #731042 (09-30) — 9 dienas, ārpus ±5 d loga; noķēra tikai pretrunu meklēšana, dzēsts ar `data/rollback_rutina_vakars_2026-10-10.sql`.
- **Rīcība:** pārmērīt `/audit-integrity` 6. pārbaudes 101 grupu (§ Atliktais 57) ar līdzības filtru.
- **Īpašnieks:** operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_agenti-pipeline.md`.

### [OPEN] `find_inversions` — `speaks()` nosaka lomu pēc pieminējuma; aklās zonas raža nav triāžēta

- **(b) Viltus inversija:** `speaks()` joprojām nosaka lomu pēc pieminējuma, ne pēc runas akta (doc 99611: runājošs subjekts Hermanis atgriezts kā inversija). `find_inversions(days=7)` 2026-09-25 → **39 inversijas / 342 kandidāti** (nelasīti).
- **(a) Aklā zona — doki ar `mentioned`, bet bez neviena `subject`:** tagad skaitīta (`recovery_survey` `blind_no_subject`, `ae9d926d`, 09-24) → **543 doki / 7 d**; ražas triāža nav izdarīta. Blakus: ATGŪŠANA 7 dienās 34 pāri (web 32, vestnesis 2, twitter 0, x_mention 0) — pārbaudīt, vai josla vispār var trāpīt tvītam.
- **Secība:** vispirms labot (b), tad (a) ražas triāža uz 543 dokiem — citādi triāžā skaitās tie paši viltus pozitīvie. Ja raža < ~10 %, verdikts uz § Ne-darīt ar skaitli.
- **Raža izmērīta 2026-10-15 (D4, joslas ar subjektu, ne aklā zona):** `inversion`+`beside_subject`, web, ≥2 signāli, 90 d — 303 pāri → 155 pozīcijas (51 %). Atlikums (web 1 signāls 196, twitter 60, vestnesis 76) — operators. [`docs/audits/2026-10-15-d4-atgusana/`](../docs/audits/2026-10-15-d4-atgusana/README.md)
- **(f) IZPILDĪTS 2026-10-18:** `recovery_survey` un `pending_quoted_mentioned` izlaiž (doc, pid) pāri, kam claim ar to pašu `opponent_id` + `source_url` jau ir; skaits `already_claimed` ATGŪŠANA rindā. Dzīvajā DB 90 d: 1/142 atgrieztajiem (doc 96603 pid 189 — stampēts subjekts ar vēlāk pieliktu NULL `mentioned` saiti), izlaisti 3. `find_inversions` (audita pārbaude 15) tos joprojām skaita. **Atlikums:** izlaistie pāri netiek zīmogoti, tāpēc 15. pārbaudes bāzlīnija tos joprojām skaita (piezīme pie tās). *Īpašnieks:* koda darbs.
- **(d) IZPILDĪTS 2026-11-10:** `mark_recovery_evaluated(doc, pid, iemesls)` ieraksta `logs` zīmi; apsekojums tādu pāri izlaiž, kamēr zīme ir jaunāka par doka `scraped_at` (`tests/test_recovery_survey.py`). Dzīvajā DB zīmju vēl nav — pirmā īstā pārbaude nākamajā rutīnā.
- **(e) Rindā nonāk pāri, kur politiķis tikai `mentioned`** (2026-10-11: doc 131135 Stendzenieks, 131197/131200/131202 Tavars) — `plan_extraction` tvēruma jautājums, nav labots.
- **Īpašnieks:** operators (izmeklēšana pirms koda). Pašcitēšanas daļa (c) slēgta 2026-10-14 (verdikts C8, `0429f5f0`).

### [OPEN] Stance šūnas pārskata tabulās arvien garākas — 26/41 pārsniedz 30 vārdus
- **Problēma:** 2026-10-25 26 no 41 dienas pozīcijas stance ir > 30 vārdi (10-24: 12). Pārskata proza tiek pārbaudīta (§ H), šūnas — nē; tās nāk no `claims.stance`. Vaicājums: `SELECT count(*), sum(length(trim(stance))-length(replace(trim(stance),' ',''))+1 > 30) FROM claims WHERE claim_type='position' AND id BETWEEN 747481 AND 747524 AND stated_at >= '2026-10-25'`.
- **Rīcība (operators 2026-11-09):** garuma robeža ekstraktorā — NĒ (§ Ne-darīt, 2026-08-22). Risināt pārskata tabulā: īsāka šūna vai izvēršams teksts (`@brief-writer` vai veidne). *Īpašnieks:* koda darbs nākamajā UI kārtā.
