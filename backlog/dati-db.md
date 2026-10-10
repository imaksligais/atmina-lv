# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Dati / DB

> Shēma, denormalizācijas dreifs, tēmu taksonomija, vektori, laikspiedoli.

### [OPERATOR] 15. Saeima — `parties.coalition_status` un `tracked_politicians` pēc jaunās Saeimas sanākšanas (2026-10-04)

Provizoriskie CVK dati 10-04 08:22 (1024/1059 iecirkņi, `data/cvk_sv2026_rezultati.yaml`): Saeimā AS 42, LPV 17, SV/AJ 14, NA 11, PRO 9, JV 7; ZZS 4,46 % — ārā. `coalition_status` 10-04 apzināti NEmainīts: 14. Saeima un valdība joprojām strādā. *Trigeris:* 15. Saeimas pirmā sēde (statusi `not_in_saeima`/`opposition`, SV/AJ (`parties.id`=19) ieiet Saeimā) un jaunās valdības apstiprināšana (`coalition`). Tad arī: ievēlēto deputātu saraksts pret `tracked_politicians` (jauni deputāti → `/seed-entity`; neievēlētie paliek, bet `role` jāpārbauda, T6). *Īpašnieks:* operators.

### [OPEN] 15. Saeimas 54 jaunie deputāti — seedēšana pirms pirmās LIVS15 balsojumu ielādes; plāns `docs/plans/2026-10-05-15-saeimas-deputati.md` (vārti B = CVK oficiālais saraksts)

**2026-10-05 vakarā: 52 seedēti un PUBLICĒTI** (deploy b2fb9095, `docs/arhivs/handoffs/HANDOFF-2026-10-05-15saeima-seed.md`; CVK bio 53/53, 14 X konti). Atvērts tikai: CVK oficiālā saraksta diff + Morozs/Plaude (kopš 2026-10-08 `saeima.html` viņus rāda ar «Profils vēl nav izveidots» — seedējot sēdvieta automātiski kļūst par saiti). Lūses 6 svešas saites un Stepaņenko `@StepanenkoJulij` izdarīti 2026-10-05 (saites — `data/rollback_fix_links_2026-10-05b.sql`; konts ir `social_accounts`). (2026-10-07: šis ieraksts bez statusa rindas ieveda kļūdu sociālajā melnrakstā — «plānā» par jau izdarīto.)

2026-10-05: Task 1–5 izpildīti (kohortas YAML `data/seed/15saeima_kohorta.yaml`, priekšskatījums `docs/drafts/15saeima_preview.md`, matcher kopīgo formu + sadzīves vārdu sargs, 3 vārdabrāļu saites dzēstas, 14 X konti). Atvērts: Task 6–8 pēc CVK oficiālā saraksta (`dati.cvk.lv/SV2026/ieveletie-deputati/` 10-05 — 404). *Īpašnieks:* operators (vārti B).

### [OPERATOR] 2026-10-07 rutīnas atlikumi — viltus junction, vecs claim, dublētas doc rindas

Atrasts 10-07 ekstrakcijas un atgūšanas aģentu atskaitēs.
- ~~Viltus junction 127450 → Maija Krastiņa~~ — dzēsts 2026-10-08 (`data/rollback_junction_claim_fix_2026-10-08.sql`); `negative_patterns` («Imant», 4 formas) piemērots 2026-10-08 ar operatora apstiprinājumu (`data/fix_krastina_negative_patterns_imants_2026-10-08.sql`).
- ~~Claim 20597 (Švinka)~~ — stance + citāts izlaboti, re-embed 2026-10-08 (tas pats rollback).
- ~~Dublētas doc rindas 127349 / 127395~~ — kods labots 2026-10-08 (`normalize_source_url`); 9 esošās grupas atstātas (nevienā nav vienas pozīcijas divreiz), CHANGELOG 2026-10-08 (2).
- **`subject` uz tīra pieminējuma**: Dombrovskis 126705, Butāns 127368.
- ~~Baško pāris (30, 126284)~~ — 2026-10-08 claim 730811, 0 pretrunu; Krusts tukšs. Paliek: LETA (195) pāris `extracted_at` NULL; Krusta `party` (id 45) — MMN vērtēs izslēgšanu, pārbaudīt (T6).
- ~~Pozīcijas ar `NEEDS_REVIEW` (17)~~ — triāža 2026-10-08, CHANGELOG 2026-10-08.

### [OPERATOR] LETA URL satura nomaiņa — vēsturisko title≠content kandidātu triāža (doc 72446 klase)

Koda daļa izpildīta (`src/db.py:318,399-409`: UPDATE zars pārraksta `title` un atiestata `reviewed_at`; doc 72446 `reviewed_at` = NULL, atgriezies rindā). **Paliek:** vēsturiskie kandidāti nav atpakaļejoši laboti. Paraksts `platform='web' AND reviewed_at IS NOT NULL AND scraped_at > reviewed_at` → **209** no 8 610 izvērtētiem web dokiem (2026-09-25; abas kolonnas LV, T17 neattiecas); heiristika «virsraksta 30 zīmes nav pirmajās 600 satura zīmēs» atlasa 59 — neverificēts klasifikators (T18). 08-06 «17 kandidāti» nav reproducējami (vaicājums nav pierakstīts). *Rīcība:* pirms triāžas pierakstīt vaicājumu un izlasīt paraugu; nekad nedzēst uz klasifikatora vārda. *Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_dati-db.md`.

### [OPERATOR] Deep-check stale-pol 1. viļņa (Jev) blakusatradumi — apgrieztas/pārspīlētas stances, nepareiza attiecināšana, ne-verbatim citāts (2026-09-18)

Vilnis (5 hunteri + DA, CHANGELOG 2026-09-18 (3)) deva 0 pretrunu, bet karogoja rindu-defektus. **Nekas nav labots — katram pāra rollback + re-embed, ja mainās `stance`:**

- **Pūpols #6929, #7072** — `stance` neatbilst / ir invertēta pret citātu (hunter 51); **#14320** pārspīlē retorisku jautājumu → `NEEDS_REVIEW` marķieris vai stance pēc avota.
- **Vītols #14534** — `stance`, visticamāk, apvērš tvīta jēgu («Un?» noraida oponentu satraukumu, ne pašu priekšlikumu); **#14535** pārspīlē ambivalentu tvītu; **#532244** «zaudētā tiesa» = Satversmes tiesas lieta 2025-14-01 par 2PL likmi, ne referendums (hunter 64). **#7519 `quote` nav verbatim** — saīsināts, zudis «ņ» (DA); citāts ir VERBATIM pēc noteikuma, jāatjauno no doc.
- **Rinkēvičs #103 (Droni)** — avotā apziņošanas noteikumu prasība ir Saeimas komisiju (Latkovskis, Bergmanis) lēmums, ne prezidenta — attiecināšana pārbaudāma; ja aplama, dzēst claim (dokuments paliek).
- **Hermanis #164** — `source_url` ir partijas konts `x.com/partijaMMN/…`, bet claim glabāts kā pirmās puses (speaker NULL); vai nu `speaker_id`/relay, vai atstāt ar piezīmi.
- **Braže #113 `reasoning`** min potenciālu spriedzi ar Sprūda retoriku — `political_tensions` kandidāts, nav pārbaudīts.
- **Pūpols K-B (#11253 → #14421, Ģertrūdes aplis)** — DA Weak, bet karogots OTRAI PĀRSKATĪŠANAI: ja operators pārspiež, `minor_shift` ≤0,25 ar #14421 kā «new» (logs #655318 `rejected_candidates`).

### [OPERATOR] 2026-08-25 rutīnas karogs — Rosļikovs (pid=211) `inactive`, reaktivācija gaida CVK

**pid=211 Aleksejs Rosļikovs — ATLIKTS.** `relationship_type='inactive'`, `party='Stabilitātei!'`; 0 balsojumu rindu pēdējā gadā (pēdējais 2025-06-05), tāpēc frakcijas krustpārbaudes nav, un pierādījums ir tikai kandidēšana «Stabilitātei!» Rīgas sarakstā. Doc **89625** («Tiesa negroza Rosļikovam piemēroto apcietinājumu», leta.lv) apzināti paliek `reviewed_at IS NULL` (pārbaudīts 2026-09-25). *Rīcība:* verificēt pret CVK sarakstu atsevišķi; reaktivācija maina, kas nonāk korpusā, tāpēc tā nav rutīnas solis. *Īpašnieks:* operators (§ Atliktais 14).

**Kāpēc klase pastāv:** `store_claim()` atsakās no `inactive` politiķiem (`src/db.py`), un `queue_politician_sql()` tos izslēdz pie JEBKURA loga, tāpēc viņu doki rindā neienāk nekad. Zīmogošana tos izņemtu no rindas uz visiem laikiem; stop beats write.

### [DEFERRED] "Aizsardzības industrija" topika splits

Tēmā `Aizsardzība un drošība` **810** pozīcijas (`SELECT COUNT(*) FROM claims WHERE claim_type='position' AND topic='Aizsardzība un drošība'`, 2026-09-25; 06-10 ~409). Industrijas/iepirkumu klasteris (ASCOD, lokalizācija, SAFE iegādes) pēc atslēgvārdu zondes (`industrij|ASCOD|SAFE|iepirkum|lokaliz|ražotn`) pa mēnešiem: 04 — 5, 05 — 11, 06 — 13, 07 — 13, 08 — 7, 09 (līdz 25.) — **19**. Trigeris «turpina augt vēlēšanu sezonā» izskatās izpildīts, bet tā ir zonde, ne lasīta kopa (T18). *Rīcība:* izlasīt septembra 19 rindas; ja klasteris apstiprinās — jauns kanoniskais topiks + aliasi + backfill + tēmas lapa (CHANGELOG 2026-06-10). *Īpašnieks:* operators.

### [DEFERRED] `claim_vectors` 7 010 + `document_vectors` 450 bāreņu rindas; ne-vote claims bez vektora 0 (vote — apzināti, 08-21)

Pārmērīts 2026-09-25 (kopu starpība, vec0 tabulai ne JOIN): `claim_vectors_rowids.rowid` − `claims.id` = **7 010** (nemainīts kopš 08-18); `document_vectors_rowids.rowid` − `document_chunks.id` = **450** (nemainīts). Ne-vote claims bez vektora **0**; `saeima_vote` bez vektora 18 525 — apzināti pēc 2026-08-21 verdikta. Ietekme kosmētiska: kNN var atgriezt mirušu `claim_id`/chunk. *Rīcība:* ja tīra — pāra rollback + pārbaude, ka neviens lasītājs uz bāreņiem nepaļaujas. *Īpašnieks:* operators.

### [OPEN] LSM slug dreifs — 40 raksta ID ar divām `documents` rindām (32 slugs, 8 `utm`)

- **Problēma:** izdevējs starp ievākumiem nomaina virsrakstu un slugu (vai pievieno `?utm_source=rss`), un URL-dedup (`src/db.py`) rindas uzskata par dažādiem rakstiem; `content_hash` dedup nenostrādā, ja teksts pārstrādāts. Instance: `a662064` → doki 102911/103500, 2026-09-07 pārskatā divas saites uz vienu rakstu.
- **Saucējs 2026-09-25:** regex `\.a(\d{6})` pār `documents.source_url LIKE '%lsm.lv%'` → 2 822 LSM doki, 2 773 atšķirīgi raksta ID; **40** ID ar >1 doku — 32 atšķirīgs slugs, 8 tikai query (`utm`). Tajā skaitā `utm` pāri 15297↔33398 un 23328↔33354 (no 09-23 backfill atskaites). ~1,4 % → triāža, ne koda dedup atslēga.
- **Jauna instance 2026-10-09:** doki 127349 (bez `utm`) ↔ 127395 (ar `utm`) — viens LSM raksts par Stambulas konvenciju (Rinkēvičs); pozīcija glabāta vienreiz (#730734), atrasta 10-09 veco pāru sweep.
- **Rīcība:** 40 pāru triāža (dublikātu claims, divas saites pārskatos) ar pāra rollback.
- **Īpašnieks:** operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_dati-db.md`.

### [OPERATOR] 2026-09-18 rutīnas atlikumi — TypeSafe ēnas veto zelta zaudējumi, Pabriks bez slota, Kozlovska pagrieziens, doc 110109 T1

Vakara rutīna 2026-09-18 (pārskats #613); slēgtās daļas — CHANGELOG 2026-09-19 (1). Pilnais dienu žurnāls (a)–(a10): [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md). (a8), (c), (g), (h) slēgti 2026-10-01 (D8; (h) junction labots): [`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md). Paliek:

**(a) TypeSafe veto — `enforce` NĒ** (`scripts/morning_ingest.py:23` joprojām `shadow`; § Atliktais Jev zara nosacījums norāda šurp). Pirmā ēnas nedēļa noslēgta 2026-09-26: 1 070 spriesti, 22 veto, 0 pozīciju zaudētu; pēc `text_windows` logu labojuma pārspriesti 22 → veto 11, kļūdaini 7 (CHANGELOG 2026-09-26 (2); [`docs/audits/2026-09-26-typesafe-enas-nedela.md`](../docs/audits/2026-09-26-typesafe-enas-nedela.md)). Atkārtota kļūdu klase: akuzatīva/ģenitīva uzvārds īsā vai satīriskā tekstā. *Nākamais:* otrā ēnas nedēļa → pilota pārlaide pie θ=0,3 → tikai tad sliekšņa maiņa. Otrās nedēļas žurnāls (`typesafe_veto_report.py --days 1`):

- 09-27: judged 56, vetoed 2 — abi kļūdaini (pid=214 Kariņš doc 117871, pid=236 Stepaņenko RT).
- 09-28: judged 119, vetoed 4, unavailable 5 — pareizs pid=109 Līdaka doc 118943 (zivs), kļūdains pid=61 Liepnieks doc 118666. Vakarā judged 106, vetoed 4 — pareizi pid=236 Stepaņenko doc 118380 un pid=21 Zīle doc 118994.
- 09-29: judged 89, vetoed 3 — kļūdains pid=29 Hermanis doc 119401; pareizi pid=146 Bērziņš 119964/119965 (Talsu «A. Bērziņš»; pattern + 14 junction dzēstas, CHANGELOG 2026-09-29).
- 09-30: judged 147, vetoed 3 (0 jaunu); vakarā judged 144, vetoed 4 — kļūdaini pid=15 Braže doc 120826 un RT 120825.
- 10-01: judged 170, vetoed 2 — abi pareizi pid=220 Jātnieks (izsoles sludinājums).
- 10-02: judged 170, vetoed 3 — pareizs pid=220 Jātnieks (izsole, p=0,11); **kļūdaini (zelta zaudējums, ja būtu `enforce`)** pid=82 Butāns (p=0,57, tvīts par «Butāna izglītības sertifikātu» — ģenitīvs, tā pati kļūdu klase) un pid=55 Brigmanis (p=0,56, Vēstneša 24.09 Saeimas stenogramma, kur viņš ir deputāts).
- 10-03: judged 234, vetoed 5, unavailable 0 (logs ietver 10-02 vakara 3) — jauni divi: pareizs pid=220 Jātnieks (izsole, p=0,09); **kļūdains** Rihards Kozlovskis (p=0,48, Seržanta tvīts 122963 «Kozlovska sarkanā seja fonā» — ģenitīvs, JV studijas viesis debatēs; tikai pieminējums, pozīcija nezaudēta).
- 10-04 (rīts): judged 263, vetoed 7, unavailable 0 (logs ietver 10-03 vakaru) — **kļūdains** Edmunds Zivtiņš ×2 (p=0,56/0,58, LETA 123722/123773 «visvairāk balsu ir … Edmundam Zivtiņam» — pilns vārds datīvā, ievēlēšanas ziņa); pārējie (Valaiņa vārdabrālis, Kleinbergs, Burovs) nav lasīti pret pozīcijām.
- 10-04 (vakars, `--days 1` logs 17:33–17:52): vetoed 1 d kopā 19 (judged 655, unavailable 1). Jaunie vakara veto: Edmunds Zivtiņš ×5 (LETA «provizoriskais 15. Saeimas sastāvs» — tā pati ziņu klase kā rītā; NB: CVK sarakstos ir divi Zivtiņi — Edmunds (Zemgale) un Eduards (Vidzeme), tāpēc tikai uzvārds IR divdomīgs, bet pilns vārds rakstā — nav), Kleinbergs ×1, **Kulbergs ×1 (RT @donis777 «priecīga par Kulbergu» — īsts politiķis, zelta zaudējums)**, **Burovs ×1 (RT @AndrejsUrbans par Burova kampaņu — īsts politiķis)**, Valainis ×1 («aiz muguras Valainis karājas» — neskaidrs). Neviens nav lasīts pret glabātām pozīcijām; nevienā no šiem tvītiem nebija pozīcijas (RT/joki).
- 10-04 (vēlais vakars, 23:32): **kļūdains** Ceriņš — īsts politiķis, zelta zaudējums (avots: 10-04 handoff, `docs/arhivs/handoffs/HANDOFF-2026-10-04-velesanu-rezultati.md`).
- 10-05 (rīts + pēcpusdiena, `--days 1`): judged 961, vetoed 23, unavailable 1 (logs ietver 10-04 vakaru). Jaunie 10-05: **kļūdaini (īsti politiķi)** Kulbergs ×2 (08:31 «Kulberga AS turpina JV un ZZS iesākto»; 16:24 «Siliņa argumentē JV palikšanu Kulberga valdībā»), Krauze («Siliņa atlaidusi Krauze»), Rosļikovs («Rosļikovs nolemj palikt Baltkrievijā»), Dombrovskis («ne Melni, ne Dombrovski» — pieminējums), Ņenaševa (RT, uzvārds daudzskaitlī — neskaidrs); Zivtiņš ×1 (tā pati LETA saraksta klase); pareizi — Klementjevs ×3 (tv24 anonsi, p≈0,07), Lāce (Balkānu raksts, p=0,28). Nevienā no kļūdainajiem nebija pozīcijas (virsraksti/joki), bet `enforce` režīmā saites būtu zudušas. Vakara ielāde (19:35–20:00, `--days 1` 20:00): judged 581, vetoed 13, unavailable 0; jauns kļūdains — Rosļikovs (19:52 Vaideres tvīts «Rosļikova brašie solījumi…», p=0,31 — Rosļikovs tur ir pieminēts mērķis; spriedze #447 Vaidere→Rosļikovs balstās uz šo doku).
- 10-06 (tikai vakara ielāde 20:47–21:20, `--days 1`): judged 225, vetoed 6, unavailable 0. Pareizi — Krasta ×2 (Ludzas teritorijas plānojums, p=0,03), Šlesers ×2 (Rīgas domes raksti, p=0,47/0,53 — tur runā Edvards Šlesers, ne Ainārs; atgūšanas aģents to pašu T1 pārbaudīja). Neskaidri — Brencis (RT @guntarsv «ierēdnis Brencis», p=0,57 — īsts politiķis, bet tikai pieminēts), Vītols (p=0,46, citāts «Vow, mēs, valdība…» — nav lasīts pret pozīcijām). Pozīciju zudumu nav.
- 10-07 (vakara ielāde 22:24–22:43, `--days 1`): judged 138, vetoed 5, unavailable 0. Pareizi — Pūce ×2 (Ropažu adrešu Vēstnesis, p=0,03/0,04), Krasta (Ludzas plānojums, p=0,03), Krastiņa (127450 — Ādažu deputāts Imants Krastiņš; ekstrakcijas aģents apstiprināja T1, junction rinda operatoram). **Kļūdains (zelta zaudējums `enforce` režīmā)** — Kulbergs (p=0,48, RT @MarisKaminskis 127730 «Kino nozares strīds ar Kulbergu» — ģenitīvs, īsts premjers; pozīcijas tur nav).
- 10-09 (vakara ielāde 21:25–21:50, `--days 1`): judged 84, vetoed 5, unavailable 0. Pareizi — Pūce (Ropažu adrešu Vēstnesis, p=0,03), Kalējs (Limbažu saistošie noteikumi, p=0,06). **Kļūdaini (īsti politiķi)** — Braže (p=0,58, RT @JolantaKublins1 «Dombravas un Bražes strīdā» — ģenitīvs), Gorkšs (p=0,53, «izvēlējās tieši Gorkšu» — LFF, akuzatīvs); neskaidrs — Kotello (p=0,41, «Kotello kantoris»). Pozīcijas nav lasītas pret šiem dokiem.
- 10-10 (vakara ielāde 19:46–20:09, `--days 1`): judged 133, vetoed 6, unavailable 0 (5 no tiem ir 10-09 vakara rindas). Jauns viens — **kļūdains** Kariņš (p=0,47, tvīts «Kariņa režīmam bija 8 mandāti» — ģenitīvs, īsts politiķis; tikai pieminējums).
- Zaudētas pozīcijas otrajā nedēļā: 0 (ēnā nekas netika nomests; 10-02 divi kļūdaini veto skaitās pret `enforce`).

### [OPERATOR] 2026-09-23 backfill atkārtotās ekstrakcijas atlikumi — `confidence>0.6` bez citāta, tēmu sadursmes, junction robi

Citātu, stance, dublikātu un biroja balss daļa izpildīta (CHANGELOG 2026-09-23 (2), (5)); tēmu sadursmes, junction robi, Siliņa 16435 un Krauze slēgti 2026-10-01 (D8): [`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md). Paliek:

- **Klase `confidence>0.6` bez citāta:** `claim_type='position' AND confidence>0.6 AND (quote IS NULL OR quote='')` → **647** no 7 615 pozīcijām (viss korpuss, 2026-09-25). *Lēmums:* vai tas ir defekts pēc 09-23 «skaidra atribuēta pārstāsta» definīcijas (0,65 bez marķiera), vai klase paliek. Pārmērīts 2026-10-01: 706 >0,6, 527 >0,65, 355 ≥0,75 (vietnē birka «laba»/«augsta»); pēc 0,65 griestiem (`07d32cb7`) tikai #724942, apzināti paaugstināts.

Pierādījumi: [`docs/audits/2026-09-23-backfill-trial48-reextract.md`](../docs/audits/2026-09-23-backfill-trial48-reextract.md), [`docs/audits/2026-09-23-backfill-batch1/README.md`](../docs/audits/2026-09-23-backfill-batch1/README.md). `utm` pāri pārcelti uz § LSM slug dreifs; 52682↔52696 (lsm.lv↔nra.lv) — uz `agenti-pipeline.md` § Krossavota dublikāti. *Īpašnieks:* operators.

### [OPERATOR] 2026-09-25 profila bio un NEEDS_REVIEW triāžas atlikumi — žurnālists-kandidāts, VID vārdabrāļa risks, Melņa vēstule

`x_mention` pašcitēšanas ceļš slēgts 2026-09-25 (`data/fix_project_account_x_mention_junctions_2026-09-25.sql` + rollback); ceturtais ceļš (RT) → `matcher.md` § @AtminaLV pašcitēšanas ceturtais ceļš. (d) Melnis izpildīts (`6edfaec1`); triāža 2026-10-01 (D8): [`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md).

**(b) Krišjānis Kļaviņš (pid=231, `journalist`, `feed_type='relay'`) kandidē NA sarakstā** (CVK SV2026 85450, nodarbošanās «Žurnālists»). Vai slots paliek `relay` vai kļūst `first_party` kā Seržantam — operatora lēmums (CLAUDE.md #11). Termiņš: vēlēšanas 2026-10-03; bez lēmuma paliek `relay`.

**(c) Zalāna (pid=186) VID amati** (Jēkabpils cietuma apsargs 2019, radiosakaru inženieris 2020) var piederēt vārdabrālim — CVK dati (ASL valdes priekšsēdētāja vietnieks, dz. 1987) to nedz apstiprina, nedz noliedz. 2026-10-01: deklarācijas sākas 2005-05-10 («stājoties amatā», apsargs) — 1987. gadā dzimušam tas būtu 17–18 gadu vecumā, kas vārdabrāļa iespēju palielina, bet nepierāda. **2026-10-01 ģimenes-paraksts (runbook `vad-declarations.md` § Homonīmu piesārņojums 2.–3. solis):** 19 deklarācijās ir DIVAS personas. (1) Apsargs/Jēkabpils cietums, decl 2208–2223 (16): māte Zinaīda, tēvs Alberts, sieva Lita jau 2005, pilngadīgs dēls Armands no deklarācijas par 2012. gadu, zeme Turku pag. — 1987. gadā dzimušam pilngadīgs dēls 2013. gadā nav iespējams → **pierādīts vārdabrālis**. (2) Radiosakaru inženieris SIA «Elektroniskie sakari», decl 2224–2226 (3): māte Silvija, sieva Inga — cits cilvēks nekā (1); vai tas ir kandidāts (CVK: dz. 1987, Ventspils 4. vsk. 2006, zeme Ventspils nov.), nav pierādāms. (1) **Izpildīts 2026-10-01** (operatora «jā»): 16 dekl. dzēstas, denylist +16 (14 stabili, 2 uuid), `data/{purge,rollback}_vad_zalans_2026-10-01.sql`. *Paliek:* (2) flagged — atrisināms tikai ar ārēju avotu par kandidāta darba vēsturi.

### [DEFERRED] Pilna amatu pārskatīšana pēc 15. Saeimas sanākšanas — komisiju un frakciju vadītāji

2026-09-28 apsekojums atrada komisiju priekšsēdētājus, kuru `tracked_politicians.role` vēl nes amatu, ko tagad ieņem cits: Cepurītis (76), Briškens (67; lsm.lv 15.09. Tautsaimniecības komisijas vadītāju sauc Ašeradenu), Zariņa-Stūre (143), Inga Bērziņa (144) — jaunais amats bez pierādījuma, tāpēc nerakstīts (T6, stop beats write). Deviņi citi amati izlaboti 2026-09-28 ar rollback (`data/rollback_roles_t6_2026-09-28.sql`, `data/rollback_roles_t6b_2026-09-28.sql`). 15. Saeima novembrī sadalīs visus komisiju un frakciju amatus no jauna, tāpēc pa vienam labot tagad nav jēgas.

*Trigeris:* 15. Saeimas komisiju sastāvu apstiprināšana. *Rīcība:* viena pilna `role` pārskatīšana visiem deputātiem pret saeima.lv komisiju/frakciju lapām (**2026-10-06: Playwright NAV vajadzīgs** — amati ar datumiem jau ir `saeima_deputy_positions`, `scripts/ingest_saeima_activity.py --what profiles`; pārskatīšana = lasošs diff `role` pret pašreizējiem amatiem, ne skrāpēšana), pārī ar rollback; pārbaudi `derive_profile_kind` iznākumu katram mainītajam. *Īpašnieks:* operators.

### [OPERATOR] Gorkšs (pid 300) — `role` pēc MK lēmuma par Valsts kancelejas direktoru (2026-10-08)
- **Problēma:** seedēts 2026-10-08 (`data/seed_gorkss_2026-10-08.sql`) ar `role` «LDDK ģenerāldirektors, konkursā izraudzītais kandidāts Valsts kancelejas direktora amatam»; MK lēmuma vēl nav. Pēc iecelšanas `role` noveco (T6). Blakus: LDDK (pid 193) pozīcijas, kas citē Gorkšu (~14 claims ar «Gork» citātā/stance), ir `speaker_id` sasaistes kandidāti (`wiki/operations/seeding.md` § Multi-voice); 6 `subject` pāri gaida ekstrakciju (3 no 10-07 — dienas rinda, 3 vecāki — `scripts/plan_stale_sweep.py`).
- **Rīcība:** trigeris — MK lēmums vai atteikums; `UPDATE tracked_politicians SET role=…` ar pārotu `data/rollback_*.sql`. `speaker_id`: operators 2026-10-08 — ja Gorkšs pāriet uz Valsts kanceleju (vairs nav LDDK), LDDK pozīcijas viņam NEsasaista; dublētie citāti (doc 112727: pid 193 #717822–717824 un pid 300 #730813–730815) paliek abos. **Īpašnieks:** operators.
