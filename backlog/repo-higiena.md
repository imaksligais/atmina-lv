# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Repo higiēna / kods

### [OPEN] Testu vide pēc 2026-10-29 iekāršanās labojuma — atlikušais (2026-10-29)

Iekāršanos novērsa testu `socketpair` aizvietotājs (`tests/_socketpair_shim.py`) un 3 darbinieki (CHANGELOG 2026-10-29). Atlikušais:
- **`embed_text` autouse aizstājējs testos** — katrs xdist darbinieks ielādē iegulšanas modeli (≈2 GB); aizstājējs ļautu atkal vairāk darbinieku. *Pirms:* atrast testus, kam vajag īsto modeli.
- **Ražošanas kodam tā pati vaina:** jebkurš jauns asyncio cikls (`src/render/_common/og_render.py` caur `sync_playwright()`, `src/ingest.py`, `src/x_pool.py`, `src/social*.py`) var iekārties uz pazudušu loopback savienojumu. Labojums ražošanā = tas pats aizvietotājs, uzstādīts ieejas punktos; vispirms operatora draivera eksperiments (`docs/arhivs/handoffs/HANDOFF-2026-10-29.md` § Testi un vide).
- `pytest-timeout` / `pytest-rerunfailures` — **operators 2026-10-29 atteica** (jaunas atkarības); atgriezties tikai, ja iekāršanās atkārtojas ar aizvietotāju.
- `Page.goto` noildzes testos izlabotas 2026-11-06 (`tests/_browser_env.py`, CHANGELOG). Īstais savienojumu zudums datorā paliek; WAIT vērtības nepalielina. Ja pytest brīdinājumos atkal parādās «Page.goto atkārtots», mēri ar `.scratch/testdiag/goto_variants.py` metodi.

*Īpašnieks:* koda darbs (pirmie divi), operators (draiveris).

### [OPEN] Attēla paraksta pēcapstrādes vārts — (b) OCR/stūru heiristika (prompta aizliegums ieviests 2026-09-05)

2026-09-04 modelis brief attēlā (`brief_images` #310) apakšējā labajā stūrī uzzīmēja **izdomātu kursīvu mākslinieka parakstu**, lai gan `--no-text` prompts aizliedza tekstu. Anonīmai vietnei autorības zīme attēlā ir fabricēta atribūcija, un vārtos to neviens nemeklē. (a) prompta aizliegums ieviests (`src/graphics/prompt.py::TEXT_FREE_CONSTRAINTS` + `tests/test_graphics_prompt.py::test_text_free_constraints_forbid_authorship_marks`; CHANGELOG 2026-09-05 (4)), bet tas paļaujas uz modeļa paklausību.

*Rīcība (b):* pēcapstrādes vārts — OCR vai malu/stūru heiristika pār ģenerēto PNG pirms `save_image_row()`, kas karogo tumšus sīkstruktūras blāķus tukšajā malā. Līdz tam manuālā stūru apskate pirms apstiprināšanas paliek obligāta. *Īpašnieks:* operators (vai būvēt OCR).

### [OPEN] «Kurš un kas redzams vietnē» — noteikums ~90 vietās bez īpašnieka; paplašināt `src/scope.py` (2026-10-11)

Aktīvā politiķa filtrs render slānī 31 kopijā trijās formās, 7 auditorijas saraksti ar 4 dažādiem saturiem, «publicēta pretruna» trijos pierakstos. Latentas novirzes: `render/contradictions.py`, `topics.py:200`, `links.py:286` nefiltrē neaktīvos (10-08 kopijā 0 skartu rindu); `render/focus.py:26` izlaiž `influencer`, `briefs.py:817` to iekļauj; `src/dashboard/views/backlog.py:57` apiet `scope.queue_politician_sql()`.

*Rīcība:* `src/scope.py` papildināt ar `profile_exists_sql`, `AUDIENCE_TYPES`, `published_contradiction_sql`; pozīcijām DIVI predikāti (redzama vietnē / derīga pārskatam — operatora lēmums #689559, #704196); `claim_type='position'` atstāt inline. Viens uzvedības tests ar neaktīvu politiķi un influenceri visās virsmās. Vairāku failu darbs — plāns pirms diff. *Trigeris:* nākamā sesija vai jauna `relationship_type` vērtība. *Īpašnieks:* koda darbs. Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 1.

### [FIX] Koda sīkumi no handoffiem 09-25…10-13 — divu pulksteņu daļa izlabota 2026-10-18 (2026-10-11)

**Izlabots 2026-10-18:** `_check_diacritic_health` tagad skaita rutīnas dienu (`routine_day_window`), `stale_pol_politicians` robežu rēķina no LV pulksteņa (`now_lv_dt`), ne `date('now')` (T17). Testi: `tests/test_routine.py::TestDiacriticHealthRoutineDay`, `tests/test_coverage.py::test_stale_pol_cutoff_uses_lv_clock` (bez labojuma krīt).

**Atlikušie sīkumi (nav steidzami):** `TestTensionDayBoundaryTimezone` publiskajā CI (UTC runneris) varētu izlaisties — CI kopš 09-24 liek `TZ=Europe/Riga`; nākamajā sync pārbaudīt ar `-rs` (skipu skaits CI 15 pret lokāli 3; mutāciju izlase 2026-09-24); `src/briefs.py` nedēļas loga kortežs būvēts divreiz, divi pretrunu skaita palīgi dala SQL; promptu vārts neķer `strftime('%Y-%m-%d', col) = ?` / `substr(col,1,10) = ?` (šobrīd 0 tādu); audita 3. vārti pārgadu turpinājumā (dec. → jan.) iziet ar 2 un maldinošu padomu; `src/quality.py` garumzīmju vārti noraidīja pareizu īsu teikumu bez garumzīmēm (pid 167, #11270); skeletā SV-AJ/SV/AJ apzīmējums, tēmu secība. **Slēgti (pārbaudīts 2026-10-19):** čips «20 atturas» — `c8b22197`/`96acaf31`, tests `test_unsplit_faction_chip_shows_minority_not_total`; «Abu Meri» — `0429f5f0`, `test_bloc_speakers_keep_two_word_surname`; pmo.ee = «tvnet.lv» ir PAREIZI (verdikts 41), spriedzes saskaņotas `0429f5f0`, `tests/test_source_domain_label.py`. *Īpašnieks:* koda darbs. Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 9.

**No 2026-10-18 zara recenzijām (nav labots):** ~~`search_index.py` balsojumu `OperationalError` aizsargs~~ izlabots 2026-10-19 (`test_fetch_raises_when_vote_ledger_is_broken`; līdzīgs aizsargs `parties` vaicājumam ~160. rindā paliek); laika zonas vārti (`tests/test_timestamp_timezone_gate.py`) neredz `:vārds` parametrus, daļu `BETWEEN` formu, ar `sql +=` saliktus literāļus un komatu JOIN otro tabulu; `check.sh` — `test_toggle_aria_pressed` reizēm krīt zem xdist, un pytest izdod 648–1 296 brīdinājumus (atkarīgs no xdist darbinieku skaita; 2026-10-19 ar 3 darbiniekiem 648, no tiem 645 — `js2py` `co_lnotab`, 3 — `pydub` `audioop`; trešo pušu, nav šķiroti). *Trigeris:* nākamā koda sesija šajos failos.

**No HANDOFF-2026-10-19 (nav labots):** `check.sh` 10-19 divreiz atstāja novecojušu `.git/index.lock` (07:37, 07:55) — kāds tests nogalina git procesu; atkārtojas → izmeklēt, kurš tests sauc `git`. «Testi ierakstīja ražošanas DB», kad paralēli strādā ekstrakcija, ir procesu sacīkste, ne regresija — testus palaiž, kad DB neviens neraksta.

### [OPEN] Svaigā klonā nav parauga DB — `check.sh` jaunam līdzautoram krīt (2026-10-11)

Norādes izkaisītas (README:87, CONTRIBUTING:24, dev-setup:36); `init_db()` dod tukšu shēmu. *Rīcība:* izvērtēt, vai `tests/fixtures/render_fixture_data.sql.gz` der par sēklu, un aprakstīt vienā vietā, ko var palaist bez operatora DB. *Īpašnieks:* operators (vai publicēt sēklas datus). Pierādījumi: [`docs/audits/2026-10-11-arhitekturas-parskats.md`](../docs/audits/2026-10-11-arhitekturas-parskats.md) § 8.

### [OPEN] 2026-11-07 koda pārskata atlikums — drošība, atkarības, mirušais kods (2026-11-07)

Pārskats (36 aģenti, tikai lasīšana; katru atradumu pārbaudīja vēl viens aģents) — pilns saraksts ar `file:line` un pierādījumiem: [`docs/audits/2026-11-07-koda-parskats/README.md`](../docs/audits/2026-11-07-koda-parskats/README.md). Tajā pašā dienā izlabots: CI kļūme (`HTMLParser._pending`), divi salauzti frontmatter, instrukciju drifts (audita beigās). Atlikušais:
- **Operatora lēmumi:** audita § 1, 3. punkts (viens datu fails publiskajā spogulī; detaļas tikai audita failā); DB kopija ārpus šī datora (visas 7 kopijas ir tajā pašā datorā); KNAB partiju finanses (redzamas 2 no 19 partijām, plūsma stāv kopš 07-24) — atjaunot vai iesaldēt; `src/social_agent` — apturēt vai arhivēt.
- **Koda labojumi (S):** ops paneļa `POST` maršrutiem nav izcelsmes pārbaudes (`src/dashboard/server.py`); aktivitāšu panelis slēpj ~35 % notikumu, un 30 s atjaunošana dublē rindas; `src/dashboard/views/pending.py:23` budžets 5 USD (īstais `MONTHLY_BUDGET_USD`); CI pytest bez `-n` (654 s no 20 min limita); `guard_force_push.py` neredz `git -C … push`; trīs vienreizēji skripti bez atteikuma atsauktu operatora lēmumus.
- **Atkarības un mirušais kods (S):** `crawl4ai` nesasniedzams (249 MB), video steks galvenajā `requirements.txt` (374 MB), `anthropic` un 11 neizmantotas keyring atslēgas, novecojis `requirements.lock`, matcher uzvārdu rezerves ceļš, KNAB HTML ceļš, `lemmatize`, `og-image.png`, lieki DB indeksi.

*Trigeris:* nākamā koda sesija vai operatora lēmums par § 1, 3. punktu. *Īpašnieks:* operators (lēmumi), koda darbs (pārējais).
