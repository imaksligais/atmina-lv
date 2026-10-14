# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Repo higiēna / kods

### [OPEN] Vārtu saucēju atlikums — 13. pārbaudes kandidātu kopa un Dienas pārskata #7 bez nesēja publicēšanas brīdī

2026-08-09 audita četri vārti izpildīti (CHANGELOG 2026-08-09 (3), (4)); 17. pārbaude → citātu triāža 2026-09-30 (`docs/audits/2026-09-30-citatu-triaza.md`), 6. pārbaude → § Atliktais 57, 8. pārbaude → `avoti.md` truncated kampaņa. Paliek divi:

- **(a) `/audit-integrity` 13. pārbaude (stale vektori) ziņo arī `saeima_vote` rindas**, kuras Escalation 8 aizliedz labot (2026-08-21 verdikts jaunām balsojumu rindām vektoru nedod). Mērījums 2026-09-07: 171 karogota rinda, no tām 150 `saeima_vote`, actionable — **21 `position`**. *Rīcība:* izslēgt `claim_type='saeima_vote'` no kandidātu kopas un pārpublicēt bāzlīniju kā `checked=… flagged=21`.
- **(b) quality-bars Dienas pārskata #7** (attēla varianti + dzīvs HTTP 200) publicēšanas brīdī nav neviena nesēja — ne `brief-writer.md`, ne `dienas-rutina.md`; `graphics-designer.md` `make_variants` kļūmi aprij («never block approval on variant gen»), paliek tikai `/audit-integrity` pēc-fakta diska pārbaude. Saistīts: bijušais `dati-db.md` § 2026-09-22 (f), slēgts 2026-10-01 ([`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md)).

*Īpašnieks:* operators (katrai rindai savs lēmums). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_repo-higiena.md`.

### [OPEN] Testu mutāciju izlases robi — 5 neaizsegti zari (2026-09-24)

Izlase (`docs/audits/2026-09-24-test-mutation-sample/README.md`, privāts): 20 biežāk mainītie testu faili, 81 tests, 95 mutācijas → **80/81 testu nogalina mutantu**. **Atlikušie robi — trūkst testa, ne jādzēš:** (1) `test_utc_column_is_never_read_bare` neķer UTC kolonnu, kas salīdzināta bez datuma funkcijas (`t.created_at >= ?`); (2) dubultie sargi, kur testi sasniedz tikai ārējo: `link_audit_row` otrā pārbaude, `backfill_truncated_docs` glabātās rindas pārbaude, pavediena stila pārbaude; (3) `_fetch_topics` neaktīvo politiķu izslēgšana (docstring sola, tests nav). **Nepārbaudīts apgalvojums:** `TestTensionDayBoundaryTimezone` publiskajā CI (UTC runneris) varētu izlaisties; CI kopš 09-24 liek `TZ=Europe/Riga` — pārbaudīt ar `-rs` nākamajā sync (skipu skaits CI 15 pret lokāli 3). *Īpašnieks:* orķestrators.

### [OPEN] Attēla paraksta pēcapstrādes vārts — (b) OCR/stūru heiristika (prompta aizliegums ieviests 2026-09-05)

2026-09-04 modelis brief attēlā (`brief_images` #310) apakšējā labajā stūrī uzzīmēja **izdomātu kursīvu mākslinieka parakstu**, lai gan `--no-text` prompts aizliedza tekstu. Anonīmai vietnei autorības zīme attēlā ir fabricēta atribūcija, un vārtos to neviens nemeklē. (a) prompta aizliegums ieviests (`src/graphics/prompt.py::TEXT_FREE_CONSTRAINTS` + `tests/test_graphics_prompt.py::test_text_free_constraints_forbid_authorship_marks`; CHANGELOG 2026-09-05 (4)), bet tas paļaujas uz modeļa paklausību.

*Rīcība (b):* pēcapstrādes vārts — OCR vai malu/stūru heiristika pār ģenerēto PNG pirms `save_image_row()`, kas karogo tumšus sīkstruktūras blāķus tukšajā malā. Līdz tam manuālā stūru apskate pirms apstiprināšanas paliek obligāta. *Īpašnieks:* operators (vai būvēt OCR).

### [OPEN] «Kurš un kas redzams vietnē» — noteikums ~90 vietās bez īpašnieka; paplašināt `src/scope.py` (2026-10-11)

Aktīvā politiķa filtrs render slānī 31 kopijā trijās formās, 7 auditorijas saraksti ar 4 dažādiem saturiem, «publicēta pretruna» trijos pierakstos. Latentas novirzes: `render/contradictions.py`, `topics.py:200`, `links.py:286` nefiltrē neaktīvos (10-08 kopijā 0 skartu rindu); `render/focus.py:26` izlaiž `influencer`, `briefs.py:817` to iekļauj; `src/dashboard/views/backlog.py:57` apiet `scope.queue_politician_sql()`.

*Rīcība:* `src/scope.py` papildināt ar `profile_exists_sql`, `AUDIENCE_TYPES`, `published_contradiction_sql`; pozīcijām DIVI predikāti (redzama vietnē / derīga pārskatam — operatora lēmums #689559, #704196); `claim_type='position'` atstāt inline. Viens uzvedības tests ar neaktīvu politiķi un influenceri visās virsmās. Vairāku failu darbs — plāns pirms diff. *Trigeris:* nākamā sesija vai jauna `relationship_type` vērtība. *Īpašnieks:* koda darbs. Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 1.

### [FIX] Divu pulksteņu atlikumi — `routine.py:553` kalendāra diena, `coverage.py:111` UTC pret LV (2026-10-11)

`_check_diacritic_health` filtrē claims ar `DATE(created_at)=?` (jālieto `routine_day_window`); `coverage.py:111` salīdzina `date('now')` (UTC) ar LV kolonnu `detected_at` (T17). *Rīcība:* katram labojumam tests, kas bez labojuma krīt.

**Citi koda sīkumi no handoffiem 09-25…10-13 (nav steidzami):** `src/briefs.py` nedēļas loga kortežs būvēts divreiz, divi pretrunu skaita palīgi dala SQL; promptu vārts neķer `strftime('%Y-%m-%d', col) = ?` / `substr(col,1,10) = ?` (šobrīd 0 tādu); audita 3. vārti pārgadu turpinājumā (dec. → jan.) iziet ar 2 un maldinošu padomu; balsojumu kartītes čips nedalītai frakcijai rāda kopskaitu zem vairākuma etiķetes (19 atturas + 1 nebalsoja → «20 atturas»); `src/quality.py` garumzīmju vārti noraidīja pareizu īsu teikumu bez garumzīmēm (pid 167, #11270); skeletā SV-AJ/SV/AJ apzīmējums, tēmu secība, pmo.ee avots pozīciju tabulās apzīmēts «tvnet.lv» (spriedžu tabulā «pmo.ee»), «Aktīvākie» kolonna saīsina divvārdu uzvārdus («Meri» — jābūt «Abu Meri»). *Īpašnieks:* koda darbs. Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 9.

### [OPEN] Svaigā klonā nav parauga DB — `check.sh` jaunam līdzautoram krīt (2026-10-11)

Norādes izkaisītas (README:87, CONTRIBUTING:24, dev-setup:36); `init_db()` dod tukšu shēmu. *Rīcība:* izvērtēt, vai `tests/fixtures/render_fixture_data.sql` der par sēklu, un aprakstīt vienā vietā, ko var palaist bez operatora DB. *Īpašnieks:* operators (vai publicēt sēklas datus). Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 8.
