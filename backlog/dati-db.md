# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Dati / DB

> Shēma, denormalizācijas dreifs, tēmu taksonomija, vektori, laikspiedoli.

### [OPERATOR] 15. Saeima — `parties.coalition_status` un `tracked_politicians` pēc jaunās Saeimas sanākšanas (2026-10-04)

Provizoriskie CVK dati 10-04 08:22 (1024/1059 iecirkņi, `data/cvk_sv2026_rezultati.yaml`): Saeimā AS 42, LPV 17, SV/AJ 14, NA 11, PRO 9, JV 7; ZZS 4,46 % — ārā. `coalition_status` 10-04 apzināti NEmainīts: 14. Saeima un valdība joprojām strādā. *Trigeris:* 15. Saeimas pirmā sēde (statusi `not_in_saeima`/`opposition`, SV/AJ (`parties.id`=19) ieiet Saeimā) un jaunās valdības apstiprināšana (`coalition`). Tad arī: ievēlēto deputātu saraksts pret `tracked_politicians` (jauni deputāti → `/seed-entity`; neievēlētie paliek, bet `role` jāpārbauda, T6). Pēc valdības apstiprināšanas arī `scripts/seed_coalition_periods.py --apply` (+ rollback), citādi balsojumu kartītes rāda veco koalīciju (audit 24). **Amati (operators 2026-10-24):** pēc pirmās sēdes (2026-11-03, Satversmes 13. p.) — `SAEIMA_CONVOCATION` 14→15 (`src/saeima/convocation.py`), `scripts/ingest_saeima_activity.py` amatiem (Saeima15 DepWeb līdz tam atgriež 401), tad Saeimas lapā ieslēdzas lēca «Amati» un Prezidija gredzeni (pārbaudi saucēju leģendā). Pirms 15. sasaukuma balsojumu ielādes: Saeimas lapas lēcas «Balsoja 14. Saeimā» vaicājums (`src/render/saeima.py`) nefiltrē sasaukumu — citādi 15. Saeimas balsis to sajauks. *Īpašnieks:* operators.

**2026-11-03:** pāreja uz 15. Saeimu izpildīta (CHANGELOG 2026-11-03 (5)); SV/AJ jau `opposition`. Atlikušais trigeris — jaunās valdības apstiprināšana: ZZS un «Stabilitātei!» → `not_in_saeima`, jaunā koalīcija, `seed_coalition_periods.py --apply`, ministru `role`, tad Personu lapas partiju rail grupēšana (`backlog/vietne-ui.md`, atlikta 2026-10-09). `scripts/check_new_session_votes.py` pieņem tikai pašreizējā sasaukuma UUID (citam dod STOP, exit 2). **2026-11-10:** valdības maiņas dienas soļi un skripts sagatavoti — `wiki/operations/seeding.md` § Valdības maiņas diena (CHANGELOG 2026-11-10 (2)).

Tajā pašā reizē (T6, no handoffiem 10-04…10-09; DB 2026-10-14 nemainīts): «Stabilitātei!» (`parties.id`=9) ir `opposition`, kaut frakcijas vairs nav; Štāls (pid 173) — JKP apsver likvidāciju vai zīmola maiņu; Siliņas (pid 2) `role` pēc JV ārkārtas kongresa.

### [OPERATOR] Jev keša atslēga jaucē `jev-latest`, ne atbildējušo modeli — jaukti modeļi pēc aliasa maiņas (2026-10-17)

`src/jev_filter.py::cache_key()` atslēgā liek PIEPRASĪTO nosaukumu. `data/jev_cache.db` 235 897 rindas (visas `jev-1.13.0`) ir zem `jev-latest`; kad alias pārslēgsies uz 1.14, vecās rindas turpinās atgriezt 1.13 atbildes, jaunās nāks no 1.14 — jaukums redzams tikai `JevStats.summary()` modeļu rindā. Veto žurnāls modeli neraksta vispār. Izvēle: eksplicīts modelis izsaukumos vai atbildējušais modelis atslēgā. Mērījums un 1.14 salīdzinājums: [`docs/audits/2026-10-17-jev-1.14/README.md`](../docs/audits/2026-10-17-jev-1.14/README.md) (1.14 nemaina nevienu lēmumu; `jev-latest` 10-17 = 1.13).

### [OPERATOR] LETA URL satura nomaiņa — vēsturisko title≠content kandidātu triāža (doc 72446 klase)

Koda daļa izpildīta (`src/db.py:318,399-409`: UPDATE zars pārraksta `title` un atiestata `reviewed_at`; doc 72446 `reviewed_at` = NULL, atgriezies rindā). **Paliek:** vēsturiskie kandidāti nav atpakaļejoši laboti. Paraksts `platform='web' AND reviewed_at IS NOT NULL AND scraped_at > reviewed_at` → **209** no 8 610 izvērtētiem web dokiem (2026-09-25; abas kolonnas LV, T17 neattiecas); heiristika «virsraksta 30 zīmes nav pirmajās 600 satura zīmēs» atlasa 59 — neverificēts klasifikators (T18). 08-06 «17 kandidāti» nav reproducējami (vaicājums nav pierakstīts). *Rīcība:* pirms triāžas pierakstīt vaicājumu un izlasīt paraugu; nekad nedzēst uz klasifikatora vārda. *Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_dati-db.md`.

### [DEFERRED] "Aizsardzības industrija" topika splits

Tēmā `Aizsardzība un drošība` **970** pozīcijas (`SELECT COUNT(*) FROM claims WHERE claim_type='position' AND topic='Aizsardzība un drošība'`, 2026-10-21; 09-25 — 810, 06-10 ~409). Industrijas/iepirkumu klasteris (ASCOD, lokalizācija, SAFE iegādes) pēc atslēgvārdu zondes (`industrij|ASCOD|SAFE|iepirkum|lokaliz|ražotn`) pa mēnešiem: 04 — 5, 05 — 11, 06 — 13, 07 — 13, 08 — 7, 09 (līdz 25.) — **19**. Trigeris «turpina augt vēlēšanu sezonā» izskatās izpildīts, bet tā ir zonde, ne lasīta kopa (T18). *Rīcība:* izlasīt septembra 19 rindas; ja klasteris apstiprinās — jauns kanoniskais topiks + aliasi + backfill + tēmas lapa (CHANGELOG 2026-06-10). **Operators 2026-11-09: pagaidām NĒ.** *Trigeris:* lasītāju signāls vai tēma pārsniedz 1 500 pozīciju. *Īpašnieks:* operators.

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

**(c) Zalāna (pid=186) VID deklarācijās — divas citas personas ar tādu pašu vārdu.** 2026-10-01 ģimenes paraksts (runbook `vad-declarations.md` § Homonīmu piesārņojums 2.–3. solis): decl 2208–2223 (16) — **pierādīts vārdabrālis**, jo ģimenes sastāvs nav savienojams ar kandidāta dzimšanas gadu (CVK: dz. 1987); decl 2224–2226 (3) — cita ģimene nekā pirmajai grupai, un vai tas ir kandidāts, nav pierādāms. Ģimenes un amatu detaļas ir tikai `data/vad_denylist.json` un purge skriptā (publiskajā spogulī tie nenonāk). (1) **Izpildīts 2026-10-01** (operatora «jā»): 16 dekl. dzēstas, denylist +16 (14 stabili, 2 uuid), `data/{purge,rollback}_vad_zalans_2026-10-01.sql`. *Paliek:* (2) flagged — atrisināms tikai ar ārēju avotu par kandidāta darba vēsturi.

### [DEFERRED] Pilna amatu pārskatīšana pēc 15. Saeimas sanākšanas — komisiju un frakciju vadītāji

2026-09-28 apsekojums atrada komisiju priekšsēdētājus, kuru `tracked_politicians.role` vēl nes amatu, ko tagad ieņem cits: Cepurītis (76), Briškens (67; lsm.lv 15.09. Tautsaimniecības komisijas vadītāju sauc Ašeradenu), Zariņa-Stūre (143), Inga Bērziņa (144) — jaunais amats bez pierādījuma, tāpēc nerakstīts (T6, stop beats write). Deviņi citi amati izlaboti 2026-09-28 ar rollback (`data/rollback_roles_t6_2026-09-28.sql`, `data/rollback_roles_t6b_2026-09-28.sql`). 15. Saeima novembrī sadalīs visus komisiju un frakciju amatus no jauna, tāpēc pa vienam labot tagad nav jēgas.

*Trigeris:* 15. Saeimas komisiju sastāvu apstiprināšana. *Rīcība:* viena pilna `role` pārskatīšana visiem deputātiem pret saeima.lv komisiju/frakciju lapām (**2026-10-06: Playwright NAV vajadzīgs** — amati ar datumiem jau ir `saeima_deputy_positions`, `scripts/ingest_saeima_activity.py --what profiles`; pārskatīšana = lasošs diff `role` pret pašreizējiem amatiem, ne skrāpēšana), pārī ar rollback; pārbaudi `derive_profile_kind` iznākumu katram mainītajam. *Īpašnieks:* operators.

**2026-11-04, rezerves avots:** saeima.lv `/lv/sasaukumi/15-saeima/{deputati,komisijas,frakcijas}/` jau rāda 15. Saeimas amatus ar datumiem (statisks HTML, «No … Līdz»), titania DepWeb tikmēr atbild 401. Parseri NEBŪVĒT (operators 2026-11-09, § Ne-darīt): lapās nav saites uz DepWeb (`deputy_unid` nav iegūstams), un `deputy_unid` ir UNIQUE atslēgā — aizvietots ID dotu dublikātus dienā, kad titania atveras.

### [OPERATOR] 2026-10-20 rutīnas atlikums — Mieriņas partija
- **Mieriņa (pid 17)** saka, ka līdz ZZS kongresam lems par dalību partijā (claim 743270) — pēc kongresa pārbaudīt `party` (T6).

### [OPEN] Implicītie stāvokļu automāti — ~38 dzīves cikli bez noteiktām pārejām, 10 ar reālu risku (2026-11-02)
- **Problēma:** statusi iekodēti kolonnās, NULL laikspiedolos, teksta marķieros un failu esamībā; pārejas izkaisītas un nesargātas. Smagākie: publicēšanas apstiprinājums pārdzīvo pārskata pārrakstīšanu; rutīnas deploy solis skaita arī neizdevušos deploy (viltus «done»); rediģēta raksta ielāde atiestata tikai `reviewed_at`; X kursors zaudē tvītus >20; deaktivēts avots nekad neatkopjas. Pilns saraksts ar `file:line`: [`docs/audits/2026-11-02-implicitie-stavoklu-automati.md`](../docs/audits/2026-11-02-implicitie-stavoklu-automati.md).
- **A2 daļēji 2026-11-03** (CHANGELOG 2026-11-03): `status=success` filtrs + panelis neraksta otru rindu — izdarīts. Atvērts: 11. solis pārbauda tikai dienas pārskata atslēgu, ne nedēļas un `analizes/<slug>` — skatīt kopā ar A1.
- **A1 izpildīts 2026-11-03** (CHANGELOG 2026-11-03 (2)): apstiprinājums nes satura hešu, deploy preflight atsaka pēc labojuma. Atvērts: hero attēla maiņa pēc apstiprināšanas (atsevišķi `brief_images` vārti); rutīnas 11. solis nedēļas un `analizes/` atslēgām (sk. A2).
- **Rīcība:** nākamais — pārējie audita punkti pēc riska (A3…). *Īpašnieks:* koda darbs.
