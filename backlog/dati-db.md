# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Dati / DB

> Shēma, denormalizācijas dreifs, tēmu taksonomija, vektori, laikspiedoli.

### [OPERATOR] 15. Saeima — `parties.coalition_status` un `tracked_politicians` pēc jaunās Saeimas sanākšanas (2026-10-04)

Provizoriskie CVK dati 10-04 08:22 (1024/1059 iecirkņi, `data/cvk_sv2026_rezultati.yaml`): Saeimā AS 42, LPV 17, SV/AJ 14, NA 11, PRO 9, JV 7; ZZS 4,46 % — ārā. `coalition_status` 10-04 apzināti NEmainīts: 14. Saeima un valdība joprojām strādā. *Trigeris:* 15. Saeimas pirmā sēde (statusi `not_in_saeima`/`opposition`, SV/AJ (`parties.id`=19) ieiet Saeimā) un jaunās valdības apstiprināšana (`coalition`). Tad arī: ievēlēto deputātu saraksts pret `tracked_politicians` (jauni deputāti → `/seed-entity`; neievēlētie paliek, bet `role` jāpārbauda, T6). Pēc valdības apstiprināšanas arī `scripts/seed_coalition_periods.py --apply` (+ rollback), citādi balsojumu kartītes rāda veco koalīciju (audit 24). *Īpašnieks:* operators.

Tajā pašā reizē (T6, no handoffiem 10-04…10-09; DB 2026-10-14 nemainīts): «Stabilitātei!» (`parties.id`=9) ir `opposition`, kaut frakcijas vairs nav; Štāls (pid 173) — JKP apsver likvidāciju vai zīmola maiņu; Siliņas (pid 2) `role` pēc JV ārkārtas kongresa.

### [OPERATOR] 2026-10-07 rutīnas atlikums — LETA (195) `mentioned` pāris doc 126284, LDDK rubrikas autors

**2026-10-14 (verdikti):** Dombrovskis 126705, Butāns 127368 → `mentioned`; doc 114881 `published_at`=2026-09-23 (datelīnija); LDDK #729892 — autors LDDK («LDDK ieskatā»), bez marķiera. Krusta (pid 45) `party` = «Bezpartejisks» (CHANGELOG 2026-10-15 (6)). Paliek: LETA (195) pāris.

Atrasts 10-07 ekstrakcijas un atgūšanas aģentu atskaitēs.
- ~~Viltus junction 127450 → Maija Krastiņa~~ — dzēsts 2026-10-08 (`data/rollback_junction_claim_fix_2026-10-08.sql`); `negative_patterns` («Imant», 4 formas) piemērots 2026-10-08 ar operatora apstiprinājumu (`data/fix_krastina_negative_patterns_imants_2026-10-08.sql`).
- ~~Claim 20597 (Švinka)~~ — stance + citāts izlaboti, re-embed 2026-10-08 (tas pats rollback).
- ~~Dublētas doc rindas 127349 / 127395~~ — kods labots 2026-10-08 (`normalize_source_url`); 9 esošās grupas atstātas (nevienā nav vienas pozīcijas divreiz), CHANGELOG 2026-10-08 (2).
- ~~Baško pāris (30, 126284)~~ — 2026-10-08 claim 730811, 0 pretrunu; Krusts tukšs. Paliek: LETA (195, `mentioned`) pāris doc 126284 `extracted_at` NULL.
- ~~Pozīcijas ar `NEEDS_REVIEW` (17)~~ — triāža 2026-10-08, CHANGELOG 2026-10-08.
- **LDDK rubrikas «Bizness par biznesu» autors nav norādīts** (2026-10-09): doc 129933 atzīmēts tukšs; tas pats var attiekties uz 10-04 claim #729892 (glabāts LDDK, pid 193).

### [OPERATOR] Jev keša atslēga jaucē `jev-latest`, ne atbildējušo modeli — jaukti modeļi pēc aliasa maiņas (2026-10-17)

`src/jev_filter.py::cache_key()` atslēgā liek PIEPRASĪTO nosaukumu. `data/jev_cache.db` 235 897 rindas (visas `jev-1.13.0`) ir zem `jev-latest`; kad alias pārslēgsies uz 1.14, vecās rindas turpinās atgriezt 1.13 atbildes, jaunās nāks no 1.14 — jaukums redzams tikai `JevStats.summary()` modeļu rindā. Veto žurnāls modeli neraksta vispār. Izvēle: eksplicīts modelis izsaukumos vai atbildējušais modelis atslēgā. Mērījums un 1.14 salīdzinājums: [`docs/audits/2026-10-17-jev-1.14/README.md`](../docs/audits/2026-10-17-jev-1.14/README.md) (1.14 nemaina nevienu lēmumu; `jev-latest` 10-17 = 1.13).

### [OPERATOR] LETA URL satura nomaiņa — vēsturisko title≠content kandidātu triāža (doc 72446 klase)

Koda daļa izpildīta (`src/db.py:318,399-409`: UPDATE zars pārraksta `title` un atiestata `reviewed_at`; doc 72446 `reviewed_at` = NULL, atgriezies rindā). **Paliek:** vēsturiskie kandidāti nav atpakaļejoši laboti. Paraksts `platform='web' AND reviewed_at IS NOT NULL AND scraped_at > reviewed_at` → **209** no 8 610 izvērtētiem web dokiem (2026-09-25; abas kolonnas LV, T17 neattiecas); heiristika «virsraksta 30 zīmes nav pirmajās 600 satura zīmēs» atlasa 59 — neverificēts klasifikators (T18). 08-06 «17 kandidāti» nav reproducējami (vaicājums nav pierakstīts). *Rīcība:* pirms triāžas pierakstīt vaicājumu un izlasīt paraugu; nekad nedzēst uz klasifikatora vārda. *Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_dati-db.md`.

### [DEFERRED] "Aizsardzības industrija" topika splits

Tēmā `Aizsardzība un drošība` **970** pozīcijas (`SELECT COUNT(*) FROM claims WHERE claim_type='position' AND topic='Aizsardzība un drošība'`, 2026-10-21; 09-25 — 810, 06-10 ~409). Industrijas/iepirkumu klasteris (ASCOD, lokalizācija, SAFE iegādes) pēc atslēgvārdu zondes (`industrij|ASCOD|SAFE|iepirkum|lokaliz|ražotn`) pa mēnešiem: 04 — 5, 05 — 11, 06 — 13, 07 — 13, 08 — 7, 09 (līdz 25.) — **19**. Trigeris «turpina augt vēlēšanu sezonā» izskatās izpildīts, bet tā ir zonde, ne lasīta kopa (T18). *Rīcība:* izlasīt septembra 19 rindas; ja klasteris apstiprinās — jauns kanoniskais topiks + aliasi + backfill + tēmas lapa (CHANGELOG 2026-06-10). *Īpašnieks:* operators.

### [DEFERRED] `claim_vectors` 7 010 + `document_vectors` 450 bāreņu rindas; ne-vote claims bez vektora 0 (vote — apzināti, 08-21)

Pārmērīts 2026-09-25 (kopu starpība, vec0 tabulai ne JOIN): `claim_vectors_rowids.rowid` − `claims.id` = **7 010** (nemainīts kopš 08-18); `document_vectors_rowids.rowid` − `document_chunks.id` = **450** (nemainīts). Ne-vote claims bez vektora **0**; `saeima_vote` bez vektora 18 525 — apzināti pēc 2026-08-21 verdikta. Ietekme kosmētiska: kNN var atgriezt mirušu `claim_id`/chunk. *Rīcība:* ja tīra — pāra rollback + pārbaude, ka neviens lasītājs uz bāreņiem nepaļaujas. *Īpašnieks:* operators.

### [OPEN] LSM slug dreifs — 40 raksta ID ar divām `documents` rindām (32 slugs, 8 `utm`)

- **Problēma:** izdevējs starp ievākumiem nomaina virsrakstu un slugu (vai pievieno `?utm_source=rss`), un URL-dedup (`src/db.py`) rindas uzskata par dažādiem rakstiem; `content_hash` dedup nenostrādā, ja teksts pārstrādāts. Instance: `a662064` → doki 102911/103500, 2026-09-07 pārskatā divas saites uz vienu rakstu.
- **Saucējs 2026-09-25:** regex `\.a(\d{6})` pār `documents.source_url LIKE '%lsm.lv%'` → 2 822 LSM doki, 2 773 atšķirīgi raksta ID; **40** ID ar >1 doku — 32 atšķirīgs slugs, 8 tikai query (`utm`). Tajā skaitā `utm` pāri 15297↔33398 un 23328↔33354 (no 09-23 backfill atskaites). ~1,4 % → triāža, ne koda dedup atslēga. **2026-10-21:** 3 457 LSM doki / 3 393 ID, **51** ID ar >1 doku.
- **Jauna instance 2026-10-09:** doki 127349 (bez `utm`) ↔ 127395 (ar `utm`) — viens LSM raksts par Stambulas konvenciju (Rinkēvičs); pozīcija glabāta vienreiz (#730734), atrasta 10-09 veco pāru sweep.
- **`utm` daļa IZPILDĪTA 2026-10-08:** `normalize_source_url()` (`src/db.py`, 90a85126); kopš 2026-10-09 `platform='web'` 927 doki, ar `utm_` URL 0. Slugu maiņu kods nesedz.
- **Rīcība:** pāru triāža (51 ID, 2026-10-21) (dublikātu claims, divas saites pārskatos) ar pāra rollback.
- **Īpašnieks:** operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_dati-db.md`.

### [OPERATOR] 2026-09-25 profila bio un NEEDS_REVIEW triāžas atlikumi — Zalāna radiosakaru deklarācijas (3)

`x_mention` pašcitēšanas ceļš slēgts 2026-09-25 (`data/fix_project_account_x_mention_junctions_2026-09-25.sql` + rollback); ceturtais ceļš (RT) slēgts 2026-10-14 (verdikts C8, `0429f5f0`). (d) Melnis izpildīts (`6edfaec1`); triāža 2026-10-01 (D8): [`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md).

**(b) SLĒGTS 2026-10-14 (verdikts A4): nav ievēlēts, paliek `relay`.** ~~Krišjānis Kļaviņš (pid=231, `journalist`, `feed_type='relay'`) kandidē NA sarakstā~~ (CVK SV2026 85450, nodarbošanās «Žurnālists»). Vai slots paliek `relay` vai kļūst `first_party` kā Seržantam — operatora lēmums (CLAUDE.md #11). Termiņš: vēlēšanas 2026-10-03; bez lēmuma paliek `relay`.

**(c) Zalāna (pid=186) VID amati** (Jēkabpils cietuma apsargs 2019, radiosakaru inženieris 2020) var piederēt vārdabrālim — CVK dati (ASL valdes priekšsēdētāja vietnieks, dz. 1987) to nedz apstiprina, nedz noliedz. 2026-10-01: deklarācijas sākas 2005-05-10 («stājoties amatā», apsargs) — 1987. gadā dzimušam tas būtu 17–18 gadu vecumā, kas vārdabrāļa iespēju palielina, bet nepierāda. **2026-10-01 ģimenes-paraksts (runbook `vad-declarations.md` § Homonīmu piesārņojums 2.–3. solis):** 19 deklarācijās ir DIVAS personas. (1) Apsargs/Jēkabpils cietums, decl 2208–2223 (16): māte Zinaīda, tēvs Alberts, sieva Lita jau 2005, pilngadīgs dēls Armands no deklarācijas par 2012. gadu, zeme Turku pag. — 1987. gadā dzimušam pilngadīgs dēls 2013. gadā nav iespējams → **pierādīts vārdabrālis**. (2) Radiosakaru inženieris SIA «Elektroniskie sakari», decl 2224–2226 (3): māte Silvija, sieva Inga — cits cilvēks nekā (1); vai tas ir kandidāts (CVK: dz. 1987, Ventspils 4. vsk. 2006, zeme Ventspils nov.), nav pierādāms. (1) **Izpildīts 2026-10-01** (operatora «jā»): 16 dekl. dzēstas, denylist +16 (14 stabili, 2 uuid), `data/{purge,rollback}_vad_zalans_2026-10-01.sql`. *Paliek:* (2) flagged — atrisināms tikai ar ārēju avotu par kandidāta darba vēsturi.

### [DEFERRED] Pilna amatu pārskatīšana pēc 15. Saeimas sanākšanas — komisiju un frakciju vadītāji

2026-09-28 apsekojums atrada komisiju priekšsēdētājus, kuru `tracked_politicians.role` vēl nes amatu, ko tagad ieņem cits: Cepurītis (76), Briškens (67; lsm.lv 15.09. Tautsaimniecības komisijas vadītāju sauc Ašeradenu), Zariņa-Stūre (143), Inga Bērziņa (144) — jaunais amats bez pierādījuma, tāpēc nerakstīts (T6, stop beats write). Deviņi citi amati izlaboti 2026-09-28 ar rollback (`data/rollback_roles_t6_2026-09-28.sql`, `data/rollback_roles_t6b_2026-09-28.sql`). 15. Saeima novembrī sadalīs visus komisiju un frakciju amatus no jauna, tāpēc pa vienam labot tagad nav jēgas.

*Trigeris:* 15. Saeimas komisiju sastāvu apstiprināšana. *Rīcība:* viena pilna `role` pārskatīšana visiem deputātiem pret saeima.lv komisiju/frakciju lapām (**2026-10-06: Playwright NAV vajadzīgs** — amati ar datumiem jau ir `saeima_deputy_positions`, `scripts/ingest_saeima_activity.py --what profiles`; pārskatīšana = lasošs diff `role` pret pašreizējiem amatiem, ne skrāpēšana), pārī ar rollback; pārbaudi `derive_profile_kind` iznākumu katram mainītajam. *Īpašnieks:* operators.

### [OPEN] Spriedzei nav notikuma datuma — veci tvīti nonāk dienas pārskatā (2026-10-08)

- **Problēma:** `political_tensions` datējas ar izveides dienu (notikuma datuma kolonnas nav), un saišu priekšlikumi pieņem arī vecus tvītus. 2026-10-08 20 no 36 spriedzēm bija no 2013.–2026-09 avotiem un publiski rādījās ar 10-08 datumu → dzēstas (`data/fix_drop_old_tensions_2026-10-08.sql`, rollback blakus; 8 no tām — 2026. gada septembris, 464–466, 470, 477, 488–490 — dzēstas datuma attēlojuma dēļ, ne novecojuma). 2026-10-12 tā paša iemesla dēļ noraidīti 15 veci priekšlikumi.
- **Rīcība:** filtrs pēc avota `published_at` vai notikuma datuma kolonna; pēc tam izvērtēt, vai rollback atjauno 8 septembra spriedzes.
- **Īpašnieks:** operators (shēmas vai filtra izvēle).

### [OPERATOR] 2026-10-20 rutīnas atlikumi — T1 vārdabrāle, Mieriņas partija
- **T1: doc 138126 → Inese Kalniņa (pid 101, `subject`)** — rakstā runā Bauskas novada Sociālā dienesta nodaļas vadītāja Inese Kalniņa, ne deputāte. Pāris atzīmēts tukšs (0 claims). ~~Saite~~ dzēsta 2026-10-20 pēc operatora lēmuma (`data/rollback_dp_kalnina_138126_2026-10-20.sql`; apspiešana ierakstīta). **Paliek:** vai vajag `negative_patterns` (operators).
- **Mieriņa (pid 17)** saka, ka līdz ZZS kongresam lems par dalību partijā (claim 743270) — pēc kongresa pārbaudīt `party` (T6).

### [OPERATOR] Gorkšs (pid 300) — LDDK pozīciju `speaker_id` jautājums
- **Problēma:** seedēts 2026-10-08 (`data/seed_gorkss_2026-10-08.sql`) ar `role` «LDDK ģenerāldirektors, konkursā izraudzītais kandidāts Valsts kancelejas direktora amatam»; MK lēmuma vēl nav. Pēc iecelšanas `role` noveco (T6). Blakus: LDDK (pid 193) pozīcijas, kas citē Gorkšu (~14 claims ar «Gork» citātā/stance), ir `speaker_id` sasaistes kandidāti (`wiki/operations/seeding.md` § Multi-voice); 6 `subject` pāri gaida ekstrakciju (3 no 10-07 — dienas rinda, 3 vecāki — `scripts/plan_stale_sweep.py`).
- **2026-10-20:** trigeris iestājies — avoti (doc 138095, 138135) raksta «Valsts kancelejas direktora amatā apstiprinātais»; `role` → «Valsts kancelejas direktors» 2026-10-20 (`data/rollback_qr_fixes_2026-10-20.sql`), live. Paliek tikai `speaker_id` jautājums.
- **Rīcība:** `speaker_id`: operators 2026-10-08 — ja Gorkšs pāriet uz Valsts kanceleju (vairs nav LDDK), LDDK pozīcijas viņam NEsasaista; dublētie citāti (doc 112727: pid 193 #717822–717824 un pid 300 #730813–730815) paliek abos. **Īpašnieks:** operators.

### [FIX] `backup_db.py` ssh/scp izsaukumiem nav laika limita (2026-10-21)
- **Problēma:** `zstd | gpg` posmiem kopš 2026-10-21 ir `BACKUP_PIPE_TIMEOUT_S` (CHANGELOG 2026-10-21 (2)), bet attālā galamērķa `ssh`/`scp` izsaukumi joprojām var gaidīt mūžīgi (nereaģējošs serveris → iknedēļas kopija klusi iesprūst).
- **Rīcība:** tas pats paraugs — `subprocess` `timeout` + `BackupError` ar LV ziņu; tests ar viltus `ssh`, kas guļ. *Trigeris:* nākamais darbs `backup_db.py` vai attālā galamērķa ieslēgšana. *Īpašnieks:* koda darbs.

### [FIX] `test_ingest::test_store_tweets_first_party_links_author_as_subject` krīt teardown (2026-10-21)
- **Problēma:** «get_db left bound to a test stub in: src.social» (`tests/conftest.py` § 5 sargs). Ir jau `8eb7829a` (pārbaudīts ar `git archive` 2026-10-21); visticamāk kopš `69cd8e6c` (X pūls, 10-19) `src.social` piesaista `get_db` pēc ielāpa.
- **Rīcība:** importēt/piesaistīt `src.social` pirms `src.db.get_db` ielāpa testā vai labot `src/social.py` importa formu; tests zaļš, sargs paliek. *Trigeris:* nākamais darbs X ielādē. *Īpašnieks:* koda darbs.
