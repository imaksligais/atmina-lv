# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. § Izlaistie sesiju ieraksti.

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

## 2026-09-25 (1) — Kulberga dienasgrāmatu `stated_at` = datums iekavās, ne publicēšanas diena

- **Kāpēc:** 66 «Diena Nr. N» doki, 163 pozīcijas — visām `stated_at` = publicēšanas diena, lai gan kopš augusta ieraksti kavējas 3–7 dienas (vaicājums: `documents.content LIKE 'Diena Nr.%'` ⨝ `claims` pid 10). Pārskatā tas izskatās kā jaunums (09-24 noķerts tikai ar orkestratora norādi), pretrunu hronoloģija sajūk.
- **Noteikums** (`.claude/agents/claim-extractor.md` § 7 dienu logs): datums no iekavām, ja 7 dienu logā; numuru neizmanto (atkārtojas). Vēsturiskās rindas nebīda (daļa publicētos pārskatos). Koda vārta nav — prompta noteikums, ko pārbauda nākamais dienasgrāmatas ieraksts.

## 2026-09-24 (3) — Garumzīmju vārti: īsam tekstam (<100 burtu) pietiek ar vienu garumzīmi

- **Kāpēc:** pie 67–99 burtiem viena garumzīme ir zem 1,5 % sliekšņa, un pareizs latviešu teikums tika atteikts pie rakstīšanas robežas (09-23 pazuda `analyses` rinda). **Mērījums:** 32 765 īsti 40–99 burtu teikumi no web rakstiem — 29 (0,09 %) šajā zonā, vecais vārts atteica 5 no 14 paraugā; 100–149 burtiem zona 0,03 % → attiecība tur paliek.
- **Noteikums** (`src/quality.py::validate_lv_diacritics`, `short_letters=100`): zem 100 burtiem atsaka tikai ZERO garumzīmju (T4 paraksts); visi 11 vēsturiskie noņemto garumzīmju stance joprojām atteikti. Pieņemts kompromiss: daļēji noņemts īss teksts ar vienu garumzīmi iziet. Testi `tests/test_quality.py` (+3, krita pirms labojuma).
- **T6 pārbaudes bez izmaiņām:** Bartaševičs `role='Bijušais Rēzeknes mērs'` PAREIZA (atstādināts 2026-02-10, mērs kopš 10.04. J. Tutins — rezekne.lv, lsm.lv); Ceļapīters `party=ZZS` PAREIZA (LZS biedrs kopš 2025-12, ZZS Vidzemes saraksta nr. 7). Vītols bija slēgts jau 09-21.

## 2026-09-24 (2) — Testi nekad neaizsniedz ražošanas DB; testu noteikums: kļūme vispirms, pierādījums ar mutāciju

- **Cēlonis:** `src/confidence_drift.py` nesa savu `_DB_PATH`, kas apgāja testa `monkeypatch` — lokāli testi klusi lasīja dzīvo DB, publiskajā CI (bez DB) krita (09-13, 09-23 klase; 09-24 noķerts pirms push). Tā pati kopija bija `briefs.py`, `cross_check.py`, burtiski ceļi `dashboard/server.py`, `wiki_lint.py` — izņemti; viens avots `src.db.DB_PATH` (+ `PRODUCTION_DB_PATH`).
- **Vārti:** `tests/conftest.py` § 4 novirza visus noklusējuma DB ceļus uz neeksistējošu mapi (lokāli = CI bez DB; probe pirms tam: 3009 passed, 1 failed — konstantes tests); `tests/test_no_private_db_path.py` (AST, `src/`) aizliedz privātu ceļu. Abi mutācijas-testēti (privātais ceļš atgriezts → krīt). `check.sh` 3015 passed.
- **Testu noteikums** (CLAUDE.md Working Conventions): nosauc kļūmi pirms testa; incidentu testus nedzēš pēc lasījuma; dzēš tikai ar mutācijas pierādījumu. **Mērījums:** 20 biežāk mainītie testu faili, 81 tests, 95 mutācijas → 80/81 nogalina mutantu — «zema signāla testu» hipotēze šeit neapstiprinājās. Izlabots: `www.`-incidenta tests (vecais izturēja paša incidenta mutāciju), `verify_host` drošības galveņu negatīvie testi (+3, abi mutācijas-testēti). Atlikušie robi — `backlog/repo-higiena.md`.

## 2026-09-24 (1) — Rutīnas uzlabojumi: DST, sadalījuma plānotājs, atgūšanas apsekojums, deploy solis, dublikātu ziņojums

- **DST:** `now_lv()`/`utc_to_lv()` seko `Europe/Riga` (bija fiksēts +3 h līdz 2026-10-25); `review_status_at` trigeris lieto SQLite `localtime`, tāpēc DB rakstītājam jābūt uz Rīgas laika (CI `TZ=Europe/Riga`, `tests/test_lv_time.py`). Trigeri pārbūvējas nākamajā `init_db()`. Blakus efekts: ziemas laika tvītu laiki renderā −1 h (labojums, ne kļūda).
- **Plānotājs** `scripts/plan_extraction.py` (viens pid = viens aģents kārtā, >12 → kārtas, tīrie RT pa 20 pēdējā kārtā; `pending`/`dropped` saucēji) un **atgūšanas apsekojums** `scripts/recovery_survey.py` (bez platformu filtra; 23.09 koda josla 0, rokas vaicājums 18 pāri → +9 pozīcijas). Abi `print_routine`.
- **Deploy:** `deploy.sh` raksta `logs.action='deploy'` (`version_id`, `approved_slugs`); jauns solis «11. Deploy» — `done` tikai, ja jaunākais deploy pēc atļaujas nes pārskata slugu. Vēsturiskām dienām pēdu nav (✗ ir godīgs).
- **Dublikāti:** `save_analysis` ziņo `possible_duplicate` (tas pats pid, `stated_at` ±5 d, attālums ≤ 0,398; kalibrēts 6/10 recall, 0/40 FP, pāri nav neatkarīgi), nebloķē. `get_existing_claims(stated_around=…)`. Testi + mutācijas katram; `check.sh` 3013 passed. Plāns `docs/plans/2026-09-24-rutinas-uzlabojumi-plans.md`. Ieplānota ielāde — NĒ (operators, § Ne-darīt).

## 2026-09-23 (7) — Truncated backfill pēc pārlādes pārrēķina piesaistes; jauni politiķi dokā ar esošu runātāju = `mentioned`

- **Cēlonis:** `backfill_truncated_docs.py` rakstīja caur `insert_document` UPDATE zaru bez `politician_links`, un rīta backstop skenē tikai dokus bez junction rindām — runātājs, kas nosaukts tikai pilnajā tekstā, netika piesaistīts nekad (2. partija: 24 pāri; matcher pilnajā tekstā atrada 24/26, atlikušie 2 = apzināts kopīgā uzvārda izlaidums).
- **Labojums:** `--apply` pēc pārlādes palaiž `link_politicians_to_documents(doc_ids=<updated>)` (tikai pret dzīvo DB; citam ceļam jāinjicē `link_fn`), jaunās rindas raksta rollback kā DELETE, un jauns `subject` dokā, kam runātājs jau ir, kļūst `mentioned` (runātāja pierādījuma nav). Testi `tests/test_backfill_truncated_docs.py` +6 (visi krita pirms labojuma); `check.sh` 2931 passed.
- **Dati:** relink 286 šodien pārlādētajiem dokiem → 585 rindas, 80 `subject` → `mentioned`, + 3 roku piesaistes; 1 T1 viltus dzēsts (58187↔77 — «Ābrama lomu» ir teātra loma) un Ābramai `negative_patterns` `["Ābrama lom", "Ābramu Druvienā"]` (operatora deleģēts lēmums; `eval_matcher_collisions` B2D2H fp=1, gold 2142; rollback `data/rollback_abrama_negative_patterns_2026-09-23.sql`). Sākotnēji dzēstais 63393↔13 Jānis Hermanis bija PAREIZS (tekstā «eksperts Jānis Hermanis») — atjaunots kā `mentioned`. Rollback `data/rollback_backfill_relink_2026-09-23.sql`.

## 2026-09-23 (6) — `quote=null` griesti 0.6 → 0.65 skaidram atstāstam; karodziņš tikai šaubām

- **Kāpēc:** v3 griesti (`quote=null` ≤ 0.6, 09-22 (4)) + eskalācija 2 (0.5–0.6 → `NEEDS_REVIEW`) kopā karogoja katru atstāstu: 22.09. 31/78, 23.09. 38/104 pozīciju (14.–21.09.: 0). Karodziņš vairs nenošķīra šaubas no normas. Operatora lēmums 2026-09-23.
- **Noteikums:** skaidrs atstāsts (redakcionāls/oficiāls avots, runātājs vārdā ar atsauces verbu, pilns teksts, nostāja bez secinājuma) → 0.65 bez marķiera; jebkura nosaukta šaubu pazīme → ≤ 0.6 + `NEEDS_REVIEW:`. Nesēji: `claim-extractor.md` (§ Confidence + Critical Rules § 8), CLAUDE.md eskalācija 2, `quality-bars.md`, `scripts/eval_claim_extractor_score.py` (griesti 0.65).
- **Esošās 69 atzīmes** izskatītas pret avotu (4 lasītāji, DB neraksta; piemēro `scripts/fix_needs_review_triage_2026-09-23.py`): 44 skaidri (→ 0.65), 19 šaubas paliek (izvērtēts, conf nemainīts), 6 stance labojumi (pārspīlējums vai nomests kvalifikators; re-embed), 0 dzēsti. Rinda 69 → 0. Rollback `data/rollback_needs_review_triage_2026-09-23.sql`.

## 2026-09-23 (5) — Backfill 1. partijas atradumi vecajos claims izlaboti (operatora «jā»)

- `scripts/fix_backfill_batch1_old_claims_2026-09-23.py`: **15 dzēsti** (10 dublikāti — patur agrāko publikāciju vai paša tvītu; 5 biroja balss pēc 2026-08-25 konvencijas, #521116/#531904 nostāja paliek paša tvītos) un **8 pārrakstīti** (5 nepareizi nolasīti stance + 3 tēmu sadursmju nostājas apvienotas esošajā: #521078, #532213, #532226), visi 8 `Izvērtēts` + re-embed (8/8 MAINĪJĀS). Pārbaude: dzēsto atlikums 0, vektoru atlikums 0, pretrunu atsauces 0.
- Rollback `data/rollback_backfill_batch1_old_claims_2026-09-23.sql` (+ `.ids` re-embed pēc atjaunošanas). Dokumenti paliek ziņu sarakstā; X cilni neskar (visi dzēstie ir web raksti). Klase `confidence>0.6` bez citāta — apzināti neaiztikta (backlog/dati-db.md).

## 2026-09-23 (4) — Sākumlapa: viens saturs vienā vietā, līdzsvarots «Uzmanības centrā», telefona pieskāriena mērķi

- **Lapas līmeņa dedup** (`src/render/focus.py::_Shown`, secība `dashboard.py`): karuselis patur savas pretrunas; «Svaigā pretruna» ņem pirmo pretrunu ĀRPUS karuseļa (citādi esošais rezerves ceļš spriedze → citāts); karstās tēmas citāti, dienas citāts un karuseļa pozīcijas izlaiž jau redzamo pēc claim id / `source_url` / normalizēta teksta. Mērīts renderī 09-23: konteksta rindkopa 2 → 1, citāts «Tomēr valdībai…» 3 → 1; lapa 1440 px 7 427 → 6 065 px.
- Izkārtojums: pretrunas kartīte `slot_b` pilnā platumā, pamatteksts sans (`.focus-slot .prv2-card`); Līderu josla — viena rinda personai «Lielākajos apvērsumos», virsraksts «Zemākā sakritība ar Saeimas vairākumu» (SQL kārto `agree/total ASC`), saite «Visi profili →».
- Telefons: «atmina.lv» galvenē redzams, diagrammām ≤480 px visas 10 etiķetes (`ixv1.js`), `.week-strip-cta` vairs nespiež 360 px lapu ritināties; mērķi <24 px 31 → 0 (360 px, visi redzamie `a`/`button`).
- Izpilde: 4 Devin SWE-2 max aģenti paralēlos worktree (`wiki/operations/devin.md` § Paralēli), orķestrators pārskatīja diffus un sapludināja. Testi: +26 jauni (`test_homepage_dedup.py`, `test_index_focus_layout.py`, `test_rankings.py`), pilns komplekts 2915 passed; `render_baseline_dashboard.json` REGEN pēc sapludināšanas. Deploy 09-23: pilns renders (lai visas 1039 lapas saņem jauno `style.css?v=`), dry-run publish-gate 0 bloķētas, wrangler versija `322196ab` (2328 faili); dzīvi: konteksts 1×, citāts 1×, 360 px <24 px mērķi 0, diagrammas 10/10, bez horizontālās ritināšanas.

## 2026-09-23 (3) — RSS ingests vairs nemet ievadu: glabātais teksts = «virsraksts — ievads» + pilnais teksts, ja trafilatura ievadu izlaiž

- `src/ingest.py::_enrich_rss_items_fulltext`: ja RSS ievada pirmie ~25 normalizētie vārdi nav izvilktajā pilnajā tekstā, ievads (HTML-atkodēts) tiek pielikts priekšā, un `item["lede_prepended"]` skaitās ingest atskaitē un `logs` detaļās blakus `truncated_lede_fallback`. Tas pats noteikums kā `scripts/backfill_truncated_docs.py::_compose`.
- Mērījums, kas to izraisīja: 8 jaunākie lsm.lv/diena.lv doki pret dzīvās lapas aprakstu — **7 no 8 bez ievada** (piem. doc 110769 zaudēja «Apdraudējuma līmenis … nav mainījies»). «Nogrieztais ievads» skaitītājs (`Viņš/Viņa` sākums) šo klasi stipri nenovērtēja.
- **Vienreizēja pāreja (operatora lēmums pievienot uzreiz):** barotnēs vēl esošie jau glabātie raksti nākamajā ingestā mainīs `content` → URL-first UPDATE → `reviewed_at=NULL`, `scraped_at=now` (~60 izskatīti doki no pēdējām 2 dienām, ~30 ar claims) — tie atgriežas tās dienas ekstrakcijas rindā ar atgūtu ievadu. Commit ar SWE-2 aģentu; testi 5+1 jauni (krita pirms labojuma), `check.sh` 2899 passed. Augusta–septembra doki bez ievada (~3 400) NAV atpakaļejoši laboti — `backlog/avoti.md`.

## 2026-09-23 (2) — Citātu aizstāšana ar burtisku avota teikumu (operatora lēmums)

- Kad pozīcijas `quote` ir žurnālista ievads, virsraksts, `''` vai avotā neatrodams teksts, to drīkst aizstāt ar politiķa paša vārdiem no TĀ PAŠA dokumenta — ja jaunais citāts ir **burtiski** dokumentā un labojumam ir rollback. Abus nosacījumus kodā izpilda `scripts/replace_claim_quotes.py` (nepārtraukts fragments pēc atstarpju/HTML entītiju normalizācijas; rollback fsync pirms UPDATE; sauss pēc noklusējuma). Kas runā, kods nepārbauda — to dara Opus aģents pēc `docs/plans/2026-09-23-quote-replacement-brief.md`.
- Iemesls: truncated backfill izmēģinājumā ~41 no ~50 veco claims citāts bija ievads (stubā politiķa vārdu nebija); pilnajā tekstā burtisks citāts gandrīz vienmēr ir. `quote` nav embeddingā (`"{topic}: {stance}"`), tāpēc re-embed nevajag. Stance/topic/confidence labojumi joprojām ir atsevišķi operatora lēmumi.
- Vārti: `tests/test_replace_claim_quotes.py` (10; mutācija — verbatim pārbaude izņemta → 4 krīt).

## 2026-09-23 (1) — Matcher rescan vairs neliek otru lomu jau piesaistītam politiķim; `--politician-id` = runātājs

- `src/matcher.py::link_politicians_to_documents` (`rescan_all` / `doc_ids` zari): ja politiķim dokumentā JAU ir junction rinda, skenēšana viņam otru lomu nepievieno — glabātā loma uzvar (tas pats `already` likums kā `social._link_first_party_mentions`); svaigs teksta trāpījums tikai noņem `suspect_at`. Iemesls: PK `(document_id, politician_id, role)` ļāva `INSERT OR IGNORE` pievienot `mentioned` blakus `subject` (doc 111520 klase), un nākamais rescan atgrieza atpakaļ ar roku labotas lomas.
- **Cena, apzināti pieņemta:** rescan vairs nevar pats paaugstināt `mentioned` → `subject`; tas paliek manuāls (`link_politician_to_document` + pāra rollback). Jauni politiķi rescan pēc seedēšanas piesaistās kā līdz šim (viņu `already` kopā nav).
- `scripts/ingest_url.py --politician-id N` (un manifesta `politician_id`) tagad nozīmē «N ir raksta runātājs»: `insert_document(politician_links=[(N,'subject')])`; neeksistējošs pid krīt ar FK kļūdu, ne klusi. Commit `33debeff`; testi `tests/test_ingest_url.py` (+3, abi jaunie krita pirms labojuma), neighbour-komplekts 272 passed, `check.sh` 2832 passed. Kas to izpildīja: tikai testi — dzīvs ingests ar `--politician-id` vēl nav palaists.

## 2026-09-22 (8) — Rutīnas vārti: `check.sh` smoke ar `static`, veto atskaitei «NO EVIDENCE», ES Padomē atturēšanās ≠ bloķēšana

- `scripts/check.sh` smoke noklusējums `dashboard,blog` → **`dashboard,blog,static`**: tikai `static` emitē `sitemap.xml`, tāpēc katrā jauna pārskata dienā `check_output` krita «emitēta lapa nav sitemap -> blog/2026-09-22.html». Pēc labojuma: 2814 passed, sitemap 1052/1052 (commit `b3848d8a`).
- `scripts/typesafe_veto_report.py`: logs, kurā neviens izsaukums nav novērtēts (HTTP 402: judged 112, unavailable 112), rādīja «vetoed 0» kā tīru ēnas dienu → tagad `exit 2` + «NO EVIDENCE», diena ēnas nedēļā neskaitās (`shadow_verdict()`, `tests/test_typesafe_veto_report.py` — tests redzēts krītam pirms labojuma). Pēc apmaksas diena pārlaista: scored 97, vetoed 1 (zelta zaudējums, `backlog/dati-db.md` 09-18 (a2)).
- CLAUDE.md § Abstention: Saeimas «atturas = bloķē» likums NEattiecas uz ES Padomes vienprātību — tur atturēšanās lēmumu laiž cauri (pretruna #53, Kulbergs, publicēta `minor_shift` ar operatora lēmumu). CLAUDE.md eskalācija 2: «skaidra avota» izņēmuma 0,5–0,6 marķierim nav (junction-atgūšanas aģents to izlaida 6 rindām + 1 ekstraktors; laboti, `data/rollback_needs_review_conf06_2026-09-22.sql`).

## 2026-09-22 (7) — Same-URL pārrakstīšana: junction rindas KAROGAS (`suspect_at`), nekad nedzēš

- `insert_document` UPDATE zars (`src/db.py`) izsauc `_reconcile_junction_suspects`: rinda, ko JAUNAIS teksts nepamato (neviena vārda forma pie vārda robežas, pid nav izsauktāja links, nav institūcija/URL-slug), dabū `suspect_at` (LV laiks, pirmā konstatācija saglabājas). Migrācija `db_migrations.py` + `idx_dp_suspect`; skenēšanas notikums → `logs` (`action='suspect_link_flag'`, details nes izmeklēto rindu skaitu).
- **Dzēšana nav pierādāmi droša:** jaunā teksta pilnvērtīgumu nevar pierādīt (doc 44422 — 100 glabāti vārdi, bet dzīvajā jauns.lv rakstā visi 7 "novecojušie" vārdi IR, `curl` 2026-09-22; doc 42838 — 313 vārdi pret 16 ministriem dzīvajā), un junction provenance kolonnas nav (avots/URL/manuāli neatšķirami). `suspect_at` ir rinda pārskatīšanai pret dzīvo rakstu — vienīgo autoritāti.
- Karodziņu mazina jebkurš piesaistes rakstītājs: `link_politician_to_document`, matcher rescan, insert_document merge; nolaiž arī nākamā pārrakstīšana, kurā vārds atgriežas. Testi `tests/test_junction_suspect_flags.py` (14): īsāks teksts NEDZĒŠ, attaisnotās rindas nekarogojas, pirmā zīmoga nemainīgums, logs saucējs.

## 2026-09-22 (6) — `-em` formas pārlaistas pār korpusu: +17 piesaistes, viltus Zīle noraidīts

- Saistītājs pārlaists pār **51 dokumentu**, kuros parādās jaunā `-em` forma (`matcher.link_politicians_to_documents(doc_ids=…)` — oficiālais backfill ceļš ar lomu vārtiem). Rollback: `data/rollback/20260922-204021-document_politicians-em-relink.sql`.
- **Precizējums pret iepriekšējo ierakstu:** „54 dokumenti" bija 54 *dokuments×forma* pāri; unikālu dokumentu ir **51**. No tiem tikai **5** dokumentos trūka `-em` politiķa piesaistes — pārējos 46 rinda jau eksistēja pa citu ceļu (pilnvārds tekstā, URL, handle).
- **Pievienotas 17 rindas:** 6 `-em` politiķiem (Šnore ×2, Krauze ×3, Pūce ×1), 11 citiem, ko šodienas saistītājs redz, bet ingest brīdī neredzēja. Noņemtas 0.
- **Viltus kandidāti noraidīti, kā paredzēts:** doc 64701 „Indriķim **Zīlem**" (cits cilvēks), doc 93457 un 95612 (uzvārds bez priekšvārda) — nevienā Roberts Zīle netika piesaistīts. Vārda robežas + priekšvārda vārti strādā.
- **Blakus atradums → `backlog/vietne-ui.md`:** no 17 jaunajām rindām 8 radīja lomu pāri (`subject` + `mentioned` vienam cilvēkam vienā dokumentā). DB tādu jau ir **3 689** (3,6 %), un `src/render/politicians.py` ziņu vaicājums ir bez `DISTINCT` → dokuments var parādīties divreiz. Šobrīd redzams **4 lapās no 199**; neviena jaunā rinda TOP-10 logā neiekrita. Labojums pieder vaicājumam, ne datiem — rindas netiek dzēstas.

## 2026-09-22 (5) — `-e` uzvārdu vīriešu datīvs: atsauces robs aizvērts (SWE-2 aģents)

- `src/matcher.py::_latvian_surname_inflections` `-e` zars ģenerē arī `-em` (Šnore→**Šnorem**, Krauze→**Krauzem**). Iepriekš vīrieša `-e` uzvārds dabūja tikai sieviešu datīvu `-ei`, kas uz viņu nekad nevar attiekties — robs **slēpa īstas piesaistes**, nevis radīja viltus.
- **Ieguvums (orķestratora neatkarīgs mērījums, nevis aģenta ziņojums):** 54 dokumenti pāri 5 vīriešiem — Krauze 39, Šnore 6, Pūce 5, Zīle 3, Daudze 1. Aģents ziņoja tikai par Šnori (6) — tas ir piemērs, kāpēc apakšaģenta skaitļus pārbauda pats.
- **Drošība:** 22 sieviešu fantomformas (`Mūrniecem`) korpusā dod **nulli** trāpījumu. Viens viltus kandidāts pastāv — doc 64701 „Indriķim **Zīlem**" (cits cilvēks) — bet `match_politicians` to nepiesaista, jo priekšvārds nesakrīt. Aģenta apgalvojums „nulle viltus kandidātu" bija nepareizs; secinājums sakrita nejauši.
- Audits: dzēšamo defektu klase **1 → 0**. Testi **2801** (+8). Piesaistes vēsturiskajiem 54 dokumentiem **netiek** radītas — tas prasītu saistītāja pārlaišanu (DB raksts, gaida operatora vārdu).
- Izpilde: Devin CLI `swe-2-max`, `--permission-mode dangerous`; pirms palaišanas DB momentuzņēmums `data/atmina.db.pre-swe2-agent-20260922.db` (2 596 MB) — pēc darba rindu skaiti identiski, aģents DB neaiztika.

## 2026-09-22 (4) — Claim-extractor prompta v3: četri robi aizvērti, DeepSeek 11 → 12/12

- `.claude/agents/claim-extractor.md`: (1) **rituāls ir žanrs, ne notikums** — svinīgā sēdē teikta runa ar saturiskiem apgalvojumiem nav apsveikums (tests: izņem svētku ierāmējumu — vai paliek apgalvojums, ar ko var nepiekrist?); (2) `quote=null` → `confidence` ≤ 0.6 bez izņēmuma; (3) nogriezts/paywall avots → `reasoning` sākas ar `NEEDS_REVIEW:` (zemāka confidence nepietiek, triāža filtrē pēc `review_status`); (4) fragmentāram citātam divi mehāniski testi — sākums teikuma sākumā, noslēguma pieturzīme kā avotā.
- **Mērījums:** **Opus 11/12 → 12/12, 0 formas defektu** (aizvērti abi tā defekti — 7. gadījums un conf 0.65); DeepSeek v4.1-flash 11/12 → **12/12, 0 formas defektu**, ieskaitot 7. gadījumu (svinīgā sēde), ko 5 no 7 modeļiem v2 kārtā kļūdīja. SWE-2 max divi skrējieni: 12/12 abos, formas defekti 1 un 0 (pieturzīme = variance). Operatora lēmums: pastāvīgais panelis turpmāk **Opus + SWE-2**. Confidence griesti turējās visos trijos; 1. gadījuma apsveikums palika `empty`, t.i. robeža nesabruka pretējā virzienā.
- **Jauns rīks `scripts/eval_claim_extractor_score.py`** — citāts kā nepārtraukta apakšvirkne, pieturzīmju klase, conf griesti, `NEEDS_REVIEW` vārts. Validēts: atkārto visus sešus 09-16 roku vērtējumus. Rīka pirmā versija pati iekrita T16 slazdā (atslēgvārds «nogriezts paywall» trāpīja noliegumā «avots **nav** nogriezts») — tagad nogrieztību izlemj avota teksts.
- Detaļas un tas, ko mērījums NEPIERĀDA (tēmas netiek vērtētas mašīnā; Union Alpha/Kimi nav pārlaisti — `OPENROUTER_API_KEY` nav, Kimi Coding atbild HTTP 403): `docs/eval/claim-extractor-prompt-v3-2026-09-22.md`.

## 2026-09-22 (3) — Novecojušo piesaistu klase izmeklēta: 49 defekti no 242, pārējiem ir iemesls

- `audit_stale_politician_links.py` tagad katrai „teksts nepamato" rindai nosauc iemeslu: institūcija 64 · nogriezta ekstrakcija 51 · **apakšvirknes slazds 50** · teksts pārrakstīts pēc piesaistes 35 · vēlāka kārta 23 · URL ceļš 12 (kopā 242 no 608).
- Defektu klase ir tikai apakšvirknes slazds, un no tā atskaitāms 1: Šnore doc 71307 tekstā ir „Šnorem" — īsts vīriešu datīvs, ko `_latvian_surname_inflections` `-e` uzvārdiem negenerē (atsauces robs, atsevišķi no šīs rindas). **Dzēšamie: 49**, visi izveidoti 2026-04…07, **neviens pēc vārda robežas labojuma** (`d9eb4f9f`, 2026-07-27).
- Nogrieztās ekstrakcijas mehānisms pierādīts: doc 42838 glabā 313 vārdus ar vienu nosauktu politiķi, bet dzīvajā nra.lv rakstā pārējie ministri ir (`curl`), un 15 no 17 tās pašas minūtes rakstiem teksts pamato visas piesaistes — tātad ekstrakcijas robs, ne kontaminācija. → `backlog/avoti.md` truncated-backfill ieraksts.
- Otrs mehānisms kodā: `src/db.py:372` tā paša URL satura pārrakstīšana vecās junction rindas neizdzēš (35 rindas).
- **Izpildīts:** 49 rindas dzēstas (40 `subject` + 9 `mentioned`, 46 dokumenti; rollback `data/rollback/20260922-143025-*.sql`); pēc tam audita defektu klasē paliek 1 — apzināti saglabātā Šnore rinda. `check_output` 56 870 → 56 837 iekšējās atsauces (−33, ne −49: politiķa lapas rāda `LIMIT 50` logu). Regresijas tests paplašināts uz 11 parametriem (Kolumbija, skolotājs, daudzi, lācis, vilki, Lūsija, Liepiņas); 2793 testi zaļi.

## 2026-09-22 (2) — Uzvārds kā apakšvirkne: 7 viltus piesaistes dzēstas, vārts testā

- Pirms vārda robežas labojuma saistītājs ķēra uzvārdu kā apakšvirkni; 7 `document_politicians` rindas palika DB un divas no tām bija redzamas publiskos profilos: Baško (29954, 20954 — „Baškortostāna"/„Bašņeftj"), Daudze (2867, 2888, 3041 — ciems „Daudzeva"), Rajevs (3093, 3519 — „Rajevska").
- Pašreizējais saistītājs tās vairs neradītu (`match_politicians` palaists pār visiem 7). Dzēšana ar operatora atļauju; rollback `data/rollback/20260922-114435-document_politicians-substring-false-links.sql`.
- Vārts: `tests/test_matcher.py::test_surname_substring_in_longer_word_is_not_a_match` (4 parametri ar īsto tekstu). Pēc dzēšanas `check_output.py`: 1052 lapas, 56 870 iekšējās atsauces (bija 56 877 — par 7 mazāk).
- Jauns lasīšanas rīks `scripts/audit_stale_politician_links.py`: 608 rindas, ko saistītājs vairs neradītu, no tām 242 „teksts nepamato" (96 `subject`) — lēmums atlikts, sk. `backlog/matcher.md`. X/`x_mention` izslēgti: tur piesaiste nāk no handle, ne teksta.

## 2026-09-22 (1) — Partiju tests: D1b rubrikas audits, 14 šūnas → neizsakās

- D1b (brīfs `2026-09-20-partiju-tests-v2-briefi.md` § 84–96) pārbaudīja, vai katrs rubrikas zars izriet no apgalvojuma, ne no atslēgvārda. 7 zari mēra ko citu (q01 „neiesaistīties”, q04 „kontrolēt”/„kvotas”, q05 „stiprināt latviešu valodu”, q07 „lielāka daļa”, q11 „pārskatīt zaļo kursu”, q12 „starptautiskos dokumentos”); q08 „pret = nav” nav kodēšanas noteikums. Rubrikas pārrakstītas `jautajumi.yaml` (12/12).
- 14 par/pret šūnas → `klusē` ar 3 līmeņu piezīmi (q01/GS, q04/AS+LPV+JKP, q05/AS+JV, q07/MMN+LPV+JKP, q10/MMN, q11/AS+LPV, q12/SV-AJ+ASL); 3 maldinoši aprauti citāti paplašināti (q01/SV-AJ, q07/ASL, q09/GS) — visi verbatim `documents.content`.
- Skaitļi (avots `partiju_tests_audit.py`, renders no datiem): bilance 65:19 → **56:14**, nolasāmas 84 → **70 no 168**, avotu līmeņi cvk 61 / pilna 4 / izteikums 5, quiz vārts 2/12 → **1/12** (iztur tikai q05; q01 nokrita, jo mazākums 3 → 2). `test_repo_audit_known_state` momentuzņēmums 10 → 11 FAIL.
- Operatora lēmums pēc programmu pārbaudes: q01 LPV/ASL/SC paliek `par` (visos „Atbalstīsim … Ukrainas”), **q01/JKP → klusē** (vienīgais Ukrainas teikums ir par Latvijas ieguvumu — „pārņemot kara pieredzi”). Kopā 15 šūnas; gala skaitļi **55:14**, 69 nolasāmas, cvk 60 / pilna 4 / izteikums 5.
- Interaktīvais tests **pagaidām atcelts** (operators): lapas teikums „tiks pievienots” → „pagaidām nav plānots”; vārta skaitlis (1/12) paliek redzams. Metodoloģijā jauns D1b teikums; skaitļi nāk no `<!-- d1b: -->` komentāra `kodejums_draft.md` (`_d1b_note`, tests `test_d1b_note_comes_from_draft_comment`), ne literāļa.
- Lēmumu saraksts un pierādījumi: `docs/plans/2026-09-22-partiju-tests-d1b-rubrika.md`; aģentu atskaites `.scratch/d1b/report_A..D.md`. **PUBLICĒTS 2026-09-22**: pilns renders, `check_output` 1052 lapas tīrs, deploy versija `0badcb2d`, dzīvā lapa 200 un baitu identiska build.

---

## 2026-09-21 (3) — Vītols (pid 64) → AS kandidāts, `tracked`

- Operatora norāde + CVK SV2026 (Rīga 7. saraksts «Apvienotais saraksts», amats «Ministra padomnieks»): `party` NULL → `Apvienotais saraksts`, `relationship_type` `neutral` → `tracked`, `role` atjaunots. Rollback `data/rollback_vitols_64_tracked_as_2026-09-21.sql`; slēdz `backlog/dati-db.md` T6 (a). Profils jau eksistēja ar 200 pozīcijām (`neutral` renderā netiek slēpts) — mainās partijas etiķete, AS partijas lapa un turpmāko pārskatu bloku tabula (Neitrāli → Koalīcija); publicētie pārskati nav laboti. Renders `--only=politiki,personas,partijas,dashboard`; deploy gaida operatora atļauju.

---

## 2026-09-21 (2) — Nedēļas pārskata #625 frakciju labojums dzīvs; sociālo postu melnraksti

- Operatora «salabo»: `context_notes` #625 bloku komentārs pārrakstīts vietā (weekly_brief = UPSERT izņēmums) — 8204: «pret balsoja ZZS, LPV, daļa AS un ārpusfrakciju deputāti (27)» + AS sašķelšanās 4/3/4/0; 8201: balsojums bija par iekļaušanu darba kārtībā, NA 8/9 nebalsoja (QA sekundārais). Rollback `data/rollback_note_625_frakcijas_2026-09-21.sql`; renders `--only=dashboard,blog,static`; deploy `1569452c` (3 faili); live grep «AS sašķēlās» = 1. «Vienbalsīgi» pmo.ee piezīme atstāta (koroborē doc 109387).
- Sociālie melnraksti (NAV publicēti): X pavediens `docs/tweet_bank/2026-09-21-nedelas-parskats-social.md` (10 DB-verificēti handle, 0 `contradictions` pār citētajiem claim ID, 5 sepia attēli `output/images/threads/2026-09-21-thread-*`, $0.195), FB `docs/social/2026-09-21-nedelas-parskats-facebook.md`, Reddit r/atminaLV `…-reddit-atminalv.md`. Balsojumu skaits 82 pārbaudīts pret skeleta vaicājumu (87 `saeima_votes` rindas − 5 klātbūtnes reģistrācijas); sākotnējais «DB 87» bija nepareizs filtrs (`LIKE 'Reģistr%'` neķer motīvu `Deputātu klātbūtnes reģistrācija`).

---

## 2026-09-21 (1) — Attēlu mēneša budžets $5 → $20; nedēļas pārskats 09-14…20 publicēts

- `src/graphics/config.py` `MONTHLY_BUDGET_USD = 20.00` (operatora lēmums; septembris izsmelts: 136 ģenerācijas / $5.265 pret $5.00 — `image_audit` vaicājums pa mēnesi). Nedēļas pārskats `context_notes` #625 publicēts (deploy `c1a73abb`); attēls 338 sepia full-bleed — `weekly` stils ar tekstu un `editorial --no-text` abi operatora noraidīti, der `--style sepia` kā dienām. `@quality-reviewer` palaists pēc publicēšanas: PASS ar [JALABO] — bloku komentārā «pret balsoja ZZS un LPV (27)» noklūda AS 4 + ārpusfrakciju 9 pret balsis (vote_id=8204); labojums gaida operatora «labo» (`docs/arhivs/handoffs/HANDOFF-2026-09-21-nedelas-parskats.md` § 2).

---

## 2026-09-20 (19) — Partiju tests q10: rubrikas zars „pārcelt uz 1. līmeni” izņemts, ASL → klusē; mācība par aklo kodēšanu

- Operators pamanīja publicētajā lapā: ASL „uzkrājumus ieskaitot pensiju 1. līmenī” kodēta `par` apgalvojumam „brīvprātīgam, ar tiesībām izņemt” — tā ir valsts pārņemšana, ne indivīda izvēle. Cēlonis: `piekrit_nozime` OR-zars, ko apgalvojuma teksts neietver; oriģināls + K1–K3 visi to izpildīja vienprātīgi (kappa 0,893 te nozīmē konsekvenci, ne pareizību). Labots: rubrika `jautajumi.yaml` (likvidēšana/ieskaitīšana 1. līmenī bez izvēles = klusē), `kodejums.json` q10/ASL klusē ar lasītāja piezīmi; q10 tagad 4:1, klusē 84. Nākamais: D1b rubrikas pamatotības audits (`docs/plans/2026-09-20-partiju-tests-v2-briefi.md` § D1b) — pirmie kandidāti q10/MMN, q12, q04, q03.

---

## 2026-09-20 (18) — VAD analīzes politiķi saitēs uz profiliem; pārskata kartītei kopsavilkums

- `analizes/vad-2026`: 42 sekoto politiķu vārdi tabulās un § 2 sarakstā tagad ir saites `../politiki/<slug>.html` (64 saites; slugs = `src.lv_text.slugify`, tas pats, ko lieto profilu renders; 0 trūkstošu profilu pret `output/atmina/politiki/`). Ģenerators `vad_analysis_numbers.py` emitē saites (`plink()`), `audit_vad_profile_match.py::_strip_md` tās noloba — audits `[OK]` 60/60. Nav autolinka pār visu tekstu (T1 risks) — tikai ģeneratora tabulas un rokas saraksts.
- Sākumlapas josla „Jaunākais": pārskata kartīte rāda `preview` (pirmais „Galvenais" punkts, ≤300 z.) — līdz tam analīzei bija apraksts, pārskatam ne. Deploy versija `d9417046`; dzīvs: vad-2026 64 saites, index 2 `latest-card-desc`.

---

## 2026-09-20 (17) — Partiju tests PUBLICĒTS (B3 pabeigts)

- Operatora „publicē" + attēlu apstiprinājums sarunā 2026-09-20; `draft: true` noņemts, `render_partiju_tests.py --publish` → `curated/atmina/analizes/partiju-tests.html`, `image`/`image_light` frontmatterā, abi `audit.json` `approved: true`. Vārti: `check.sh` 2779 zaļi, `check_output --publish-gate-only` 0 bloķētas, dry-run 2297 faili → deploy versija `654d8871`; dzīvs 200/200, og:image 200, 375 px bez ritinājuma, konsole tīra. Sociālais pavediens nav publicēts (atsevišķa atļauja).

---

## 2026-09-20 (16) — Sākumlapa: josla „Jaunākais" zem meklētāja; karuselis bez veca pretrunu enkura

- Mērījums: karuseļa 1. kartīte bija jūlija pretruna (`hero_feed` bez svaigas ≤14 d pretrunas ņēma vecāko kā enkuru), svaigākā analīze — 7. sadaļa no 8. Lēmums (operators): starp sākumpunktiem un karuseli josla ar jaunāko pārskatu (`blog_posts[0]`) + jaunāko analīzi/sintēzi (`analysis_items()[0]`), zīme „Jauns" ≤7 d; nosaukums „Jaunākais", ne „Šodien" (no rīta tur ir vakardienas pārskats). Dublēšana: „Jaunākie pārskati" = `[1:4]`, „Vairāk analīžu" = `[1:3]`; `fresh-strip` izņemts; `hero_feed` bez svaigas pretrunas rāda 0 (tests apgriezts). Spec `docs/superpowers/specs/2026-09-20-landing-jaunakais-design.md`; `tests/test_dashboard_latest.py` 8 testi; 375 px `scrollWidth == innerWidth` lokāli un dzīvi.

---

## 2026-09-20 (15) — Partiju tests D1: 4 domstarpības apstiprinātas un pārkodētas; 21 atstāta

- Operatora „jā" 4 rindām: q01/SC + q01/LPV klusē→par (claim 532693 diplomātija suverenitātei / 532657 iestāšanās ES; citāti `instr` doc 62702/62698), q03/SC + q03/NA par→klusē (atlīdzība/atbalsts ≠ saglabāšana; NA pilnajā 1 VAD teikums — atbalsts, ne saglabāšana). Ietekme: q01 10:3, q03 4:2; vārts 2/12, bilance 66:19, 77 testi, noplūde 0.

---

## 2026-09-20 (14) — Partiju tests D1: P1 ingest caur recall-ķēdi + 3 akli kodētāji (kappa 0,893); 25 domstarpības operatoram

- P1 bloķētājs novērsts: trafilatura noklusējums abām lapām deva 0 z. (SV-AJ dublētie bloki + `deduplicate`, ST īsie bloki) — `ingest_url.py` jauna `_extract_article_text` atkāpšanās ķēde (recall tikai kad default < 150 z.; + 3 testi) → SV-AJ doc 112125 (22 907 z.), ST doc 112126 (6 040 z.), abi `variant: recall`; ID ierakstīti `d1/_PROTOKOLS.md` tabulā.
- K1/K2/K3: 168 šūnas katrs, aklums deklarēts (57/16/95 · 59/13/96 · 64/16/88; `instr` 73/72/80). Saskaņa: **143 no 168 vienbalsīgi (ar atsauci), Fleisa kappa 0,893**; pret atsauci 154/149/151 → `docs/plans/2026-09-21-partiju-tests-d1-saskana.md` (25 rindas: 6 izteikuma-līmeņa gaidītie + 14 stingrības izaicinājumi + 5 apgriezieni, t.sk. q01/SC 3/3 par). Metodoloģijā D1 teikums + tests. Vārti: 77 testi; noplūde 0; `kodejums.json` nemainīts.

---

## 2026-09-20 (14) — VAD izmeklēšana: uzkrājumu summēšanas kļūda labota (lasītāja ziņojums)

- Lasītājs pareizi: Burkāna 889k bija 19 deklarāciju atlikumu summa; pēdējā deklarācijā 137 510,16 € (`scratchpad/vad_probe/burkans/html`, interim subm 2018-06-25 — sakrīt līdz centam). `probe.py` summēja krājumu kā plūsmu; lapas "attīrītas no atkārtojumiem" neatbilda kodam.
- Labots: 6 uzkrājumu skaitļi → jaunākās deklarācijas atlikums (Lembergs ~246k, Bemhens ~17k, Truksnis ~40k, Razmusa ~238k, Grišins ~81k, Burkāns 137 510 €); Bemhens no Tier 1 uz §5 (deklarācijās karoga nav, KNAB konteksts paliek); `probe.py` raksta snapshot + krājuma/plūsmas komentārs; lapas metodoloģija + §8 pārrakstīti. Renders `--only=analizes`, `test_render_chars` REGEN (tikai šīs lapas hash), 24 zaļi.

---

## 2026-09-20 (13) — Partiju tests nodots B3 otram aģentam; docs sinhronizēti, valoda pārbaudīta

- Handoff sākumā jauns § B3 (saturs iesaldēts: 168 šūnas, 2/12, 0 karogu, 55 testi, noplūde 0; pirms B3 vajag attēla apstiprinājumu + `approve_publish.py` atļauju + tīru `blog/`; priekšskatījuma recepte) + § 0 dizaina mācība. BACKLOG WIP rinda atjaunināta.
- Pilna LV gramatikas/stilistiskas caurskate visiem 2026-09-20 jaunajiem tekstiem (kodējuma piezīmes, metodoloģija, kartītes apraksts, CHANGELOG 5–12); labots: teikuma plūdums, liekvārdība; citāti verbatim neskarti.

---

## 2026-09-20 (12) — Partiju tests: līderu saites uz profiliem, partiju nosaukumi klikšķināmi

- Kopsavilkuma tabulā „Līderis: Vārds" → `politiki/{slug}.html` (14/14 lapas pārbaudītas, `load_leaders()` no DB;
  šūnu partiju nosaukumi → partijas lapa). Tests `test_render_leader_links_come_from_data`; 36 zaļi failā.
   Priekšskatījumā iekšējās saites uz partijām/profiliem dos 404 (nav pilnais koks) — pēc konstrukcijas, ne defekts.

---

## 2026-09-20 (11) — Partiju tests: TOP-1..3 slēgts ar „nē"; saturs iesaldēts B3

- Operatora lēmums 2026-09-20 vakarā: TOP-1 (q10 NA+JKP→pret), TOP-2 (K4), TOP-3 (q03 pret-meklējums) netiek īstenoti; `kodejums.json` negrozīts, vārts 2/12, matrica bez testa. Ierakstīts analīzē (§ 7), handoff un BACKLOG. Atvērts paliek tikai: attēls + 2 „publicē".

---

## 2026-09-20 (10) — Partiju tests: otrā aģenta verdikts ieviests (higiēna + vārtu tabula); TOP-1..3 gaida operatoru

- Higiēna A: NA `pilna_programma_url` bija ziņu lapa (doc 112119) → `https://nacionalaapvieniba.lv/programma/` (doc 62113, 10 952 z.); visas 7 NA klusē šūnas pārbaudītas atkārtoti pret īsto programmu — verdikti paliek, pretrunu nav (`SELECT length`, atslēgvārdu skens 7 tēmām). Pārējie 10 DB dokumenti sākas ar programmas tekstu — NA bija vienīgā novirze.
- Higiēna B: A/B/C/D atskaites komitētas (`2026-09-20-partiju-tests-c2-zinojumi.md`) — § 5 krājums ar citātiem ir nākamā testa sēkla. Metodoloģijā vārtu tabula (12 rindas no `question_gate`) + „Programmas sola, neiebilst — 9 no 12" + `test_render_gate_table_comes_from_data`; handoff § 0 dizaina mācība („A vai B").
- Vārti: 168 šūnas (72/6/7/83), quiz 0<8; audits 2/12; 54 testi (6 faili); noplūde 0. Semantika nemainīta (`kodejums.json` neskarts — TOP-1..3 slēgšana ar „nē" ir operatora lēmums).

---

## 2026-09-20 (9) — Partiju tests: B3 atlikts (nepublicēt); pirms-B3 stāvoklis iesaldēts docs

- Operatora lēmums 2026-09-20 vakarā: matrica paliek melnraksts (`draft: true`, noplūde 0), publicēšana atlikta. Handoff + BACKLOG WIP atjaunināti; C-caurlaide (13 programmas pilnībā, 0 apgriezienu) ir galīgais saturs, ar ko B3 reiz ies.

---

## 2026-09-20 (8) — Partiju tests: q10/ASL citāts paplašināts (operatora „jā"); karogu vairs nav

- `kodejums.json` q10/ASL: citāts „2. pensiju līmenis jānovirza tautsaimniecībā" → pilns 223 zīmju teikums ar „uzkrājumus ieskaitot pensiju 1. līmenī" (`instr`-pārbaudīts doc 62700, `SELECT length`); `par` paliek via `pārcelt-uz-1.-līmeni`. Vārti nemainīgi: 168 šūnas, quiz 0<8; audits 2/12; 48 testi; noplūde 0.

---

## 2026-09-20 (7) — Partiju tests C: 13 programmas pārlasītas pilnībā, 0 apgriezienu; gaida B3

- Ingest (operatora „jā" ×10): 8 dokumenti 112117–112124 (10–11,7 tūkst. z., `SELECT length(content)`); SV-AJ/ST `thin` pie HTTP 200 atkārtoti — ekstrakcijas, ne satura kļūme (lapas atgriež 38–186 kB HTML), lasīts dzīvajā lapā. 13 lasītāji, vienots protokols, tikai lasīts: visas klusē šūnas apstiprinātas, 0 pretrunu programma↔CVK, SC prombūtne pārbaudīta (4 vietas).
- q10/ASL: pilnais teikums (223 z., `instr`-pārbaudīts doc 62700) atbalsta `par` tikai via `pārcelt-uz-1.-līmeni` — ieteikums paplašināt citātu, `kodejums.json` nemainīts bez operatora. `saraksti.yaml`: 13 `pilna_programma_parlasita` karodziņi → renderī „No atrastajām 13 ir pārlasītas pilnībā" + `test_render_fullread_sentence_comes_from_flags`.
- Vārti: 168 šūnas (72/6/7/83), quiz 0<8; audits 2/12 (q01, q05); 48 testi; `grep -rl partiju-tests output/atmina` = 0. Blakus: JV 107753 glabā 0 `claims` rindu (pp-šūnas validējas via `documents` — pēc konstrukcijas, ne defekts).

---

## 2026-09-20 (6) — Partiju tests B2: redakcija + quality-reviewer PASS (1 karogs); gaida B3

- Renderī 3 labojumi: „divi dokumenti” → trīs līmeņi (3 vietas), „276 pozīcijās 31 tēmā” → aprēķins no DB (`_pp_stats_live()`; 276/31 pārbaudīts ar `SELECT COUNT`), „vismaz piecām programmām” → bez nepārbaudāma sliekšņa; jauns `test_render_methodology_numbers_come_from_data` (`pytest` 33 zaļi failā).
- Rindu pa rindai 85/85 par/pret: 1 karogs q10/ASL par („jānovirza tautsaimniecībā” neadresē brīvprātīgumu — NElabots, operatora lēmums) + 2 robežgadījumi (q04/LPV izteikums bez preskripcijas; q04/AS-LA „kontrolēti/selektīvi” pie sliekšņa). Neitrālie vārdi 0/4 failos; `quiz`/`statement`/`lists` 0 lasītāja tekstā.
- Mobilais 375 px: pārplūde 0 abās tēmās, konsole 0 kļūdu (Playwright, `pt-b2/m375-*.png`); tumšā tēma verificēta atsevišķi (noklusējums gaišs ir `theme-init.js` koplietojums, ne lapas defekts). Vārti: 47 testi zaļi; noplūde 0. Attēli abi `approved: false` — B3 gaida attēla apstiprinājumu + 2 „publicē” atļaujas.

## 2026-09-20 (5) — Partiju tests B1: 3 ingesti + 5 kodētas šūnas; vārts 2/12 → matrica bez testa

- Ingest (`scripts/ingest_url.py`, operatora „jā”): doc 112114 LA programma (67 474 z., `SELECT length(content)`), 112115 PRO q01 izteikums (2026-01-29), 112116 PRO q10 pilns teksts (1 345 z.; stubs 29910 paliek, URL-first dedup). LA `majaslapa` → `attistibai.lv` + `pilna_programma_url` (`saraksti.yaml`).
- Kodētas 5 šūnas (citāti `instr`-pārbaudīti pret `documents.content`, mode=ro): LA q03/q04 par + q05 pret (`pilna_programma`), PRO q01 par + q10 pret (`izteikums`, runātājs 12); 7 LA klusē piezīmes atjaunotas ar 2026-09-20 pilno programmu. Vārti: `validate --quiz-gate` 168 šūnas (72/6/7/83), vienīgā kļūda quiz 0<8; `audit` 2/12 (q01, q05); 39 testi; `grep -rl partiju-tests output/atmina` = 0. Tālāk B2; U5–U7 nerakstīt.

---

Ieraksti līdz **2026-09-06** (ieskaitot) dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md), kas 2026-09-16 iesaldēts; atsauktajiem ierakstiem šeit paliek enkuru-stubi (§ Arhīvs faila beigās). `tests/test_changelog_anchors.py` sargā, lai katra ienākošā enkuru atsauce uz abiem failiem atrisinās; pirms virsraksta teksta maiņas palaid to.

Virsraksta forma `## YYYY-MM-DD (n) — …` ir atsauces atslēga (`BACKLOG.md`, `backlog/*.md` un runbooki citē to prozā) — `YYYY-MM-DD (n)` prefiksu nemaina.

---

## 2026-09-20 (4) — `analizes/vad-2026` pārrēķināta no šodienas DB (2025. gads); ģenerators + gadu-agnostiski vārti

- Operatora jautājums «vai lapa ir pārbaudīta?» — nebija: skaitļi statiski no 2026-05-05, DB pa to laiku 08-21 reparse + 09-19 tīrīšana (129 svešas dekl.) + 288 jaunas. `audit_vad_profile_match.py` uz vecās lapas: 12 nesakritības, t.sk. § 4 Jānis Zariņš 59 893→93 734 € = VMD mežziņa (tādvārža) deklarācijas, galvene 2262/144 pret DB 2254/159.
- Jauns `scripts/vad_analysis_numbers.py --year 2025` — visas tabulas ar lapā aprakstīto metodi; § 5/§ 6 kārto pēc PAŠREIZĒJIEM ierakstiem, «aizgāja» atsevišķā kolonnā (Štāls «7» bija 0 pašreizējo + 7 aizgājušo; Stepaņenko 23 = 11 + 12 pēc 4 gadu robā). Lapa pāriet uz 2025. gadu (133 ikgadējās pret 122 par 2024).
- Jauni atradumi lapā, pārbaudīti pret raw HTML: Abu Meri 35 Libānas NĪ ieraksti 2014–2025 (maijā «17 ieraksti 4 politiķiem» — tagad 53/6); Zemmers +149 % = 100 749 € meža pārdošana; Kalniete 2008 = 25 akciju paketes + 14 aizgāja. Katrs tabulu politiķis pārbaudīts pēc vecāku paraksta (visas maiņas = nāves gadījumi/rakstības varianti).
- `audit_vad_profile_match.py`: gadi tagad no lapas teksta (§ 2 virsraksts, § 4 kolonnas), ienākumu dedup atslēgā arī avots, zemsvītras marķieri ¹–⁵. Rezultāts uz jaunās lapas `[OK]` 60/60. Recepte `wiki/operations/vad-declarations.md` § Analīzes lapas atsvaidzināšana; renders `--only=analizes,dashboard` (hub `analizes.html` ir `dashboard` domēnā — šaurais renders to izlaida, noķerts pirms deploy).

---

## 2026-09-20 (3) — VAD izmeklēšanas lapa: homonīmu verifikācija 34/34 «nē»; Matisones statuss un Jaunzemes summa laboti

- Pēc Baltiņa katrai lapas personai (34 — § 2–6; Lūks 0 ierakstu) pārbaudīts, vai citētie skaitļi nāk no viena ģimenes paraksta (Māte/Tēvs) un vienas amata līnijas — runbook § Homonīmu piesārņojums soļi 2–4, bez Jev. Tabula ar rindu katrai: `docs/audits/2026-09-19-vad-interesantas-deklaracijas-sweep.md` § Homonīmu verifikācija pa personai. Rezultāts 34/34 — homonīms: nē; trīs lielajos klasteros (Vītoliņš 12/260, Jaunzeme 12/260, Krūmiņš 12/237 parsētās mērķpersonas rindas) lapas skaitļi pārrēķināti tikai no mērķpersonas klastera un turas.
- Blakusatradums FINDINGS līmenī: `finanse_FINDINGS.md` piedēvēja Jaunzemei «Bauskas vadītāja vietniece 2022–25» — tā ir Rundāles bērnudārza tādvārde (meita Beāte Baļuka); lapā nav.
- **Divas faktu kļūdas lapā, labotas ar operatora «jā»:** Matisone 2020.–2021. gadā bija Liepājas domes, ne «14. Saeimas» deputāte (DB `vad_declarations` pid 113); Jaunzemes «~232 000 €» nebija reproducējams — VID alga 2020–2024 = 274 286 € → «~274 000 € piecos gados». Tajā pašā reizē operators norādīja divus kalkus lapas tekstā — «neviendārtā» → «nevienmērīga», «dedupēts» → «attīrīts no atkārtojumiem» (4 vietas + 4 tādas pašas `vad-2026.md`; grep `dedup|neviendār` abās = 0). Renders `--only=analizes`, `test_render_chars` bāzlīnija REGEN (divi hash); deploy — operatora solis.

---

## 2026-09-20 (2) — VAD izmeklēšanas lapa: 18 amata statusi pārbaudīti, Baltiņš izņemts kā homonīms

- Operatora pamanītais «Lembergs — Ventspils mērs» izvērtās par klasi: sweep-laika etiķetes bija pieņēmumi, ne pārbaudīti statusi. Pārbaudīti visi 18 (VAD pirmavots + lsm.lv/iestāžu lapas, pilns saraksts `docs/audits/2026-09-19-vad-interesantas-deklaracijas-sweep.md` § Labojumi 2026-09-20); nepareizi bija 12: Stepaņenko (Rīgas dome, ne Saeima), Lembergs, Truksnis (mēra biroja vadītājs kopš 08-2026), Cīrule (pagaidu KNAB vadītāja, ne priekšniece), Keišs (AT senators, ne TP priekšsēdētājs), Rezevska un Razmusa (bijušās), Gaugers, Burkāns, Grišins (NMP priekšnieks kopš 2026-01), Purgaile (LB vietniece), Sesks.
- **Māris Baltiņš izņemts no lapas** — VAD "deputāta deklarācijas" ar SIA "OGN" 413,5k € dividendēm pieder Priekuļu novada deputātam, ne VVC direktoram; pati rinda «tikai deputāta deklarācijās, ne VVC direktora» bija homonīma paraksts pēc mūsu pašu metodes.
- Toca AAE dzīvokļi paliek AED (operators aizdomājās par USD): deklarāciju darījumu šūnās burtiski «432411.34 | AED», «715454.32 | AED» (pārlādēts no VAD 2026-09-20).
- Render baseline REGEN (`tests/test_render_chars.py`), lapa pārrenderēta `--only=analizes`; deploy — atsevišķs operatora solis.

---

## 2026-09-20 (1) — `confirmed=0` pretrunas bija publiskas astoņos lasītājos; visi tagad `COALESCE(confirmed,1)=1`

- Atradums (operators: «Šonedēļ nav jaunas pretrunas» pret sākumlapas «1 jauna pretruna»): skaitlis bija kandidāte #49 (Mūrniece, `confirmed=0`). Arhīva apgalvojums «visas virsmas filtrē `COALESCE(confirmed,1)=1`» (CHANGELOG-arhivs, 2026-07) bija patiess tikai pretrunu lapai, tēmām, meklēšanas indeksam un pārskatiem — sākumlapas kopskaits + 7 dienu josla + sparkline (`dashboard.py`), profila pretrunu SARAKSTS (`politicians.py` — skaits bija filtrēts kopš 2026-06-10, saraksts ne), saišu lapa ×2, partiju lapa ×2, personas, pārskata kājene (`blog.py`) rādīja arī `confirmed=0`. Dzīvajā vietnē visas četras kandidātes (#40 kopš jūnija, #47, #48, #49) stāvēja profilos kā «≈ Pozīcijas maiņa» kartītes.
- Labojums: 8 vaicājumi 6 failos ar to pašu klauzulu; vārti `tests/test_confirmed_gate_all_surfaces.py` (9 testi, pilna shēma ar `init_db`+`init_saeima_tables`; redzēti sarkani pirms labojuma un sarkans atkārtoti, atgriežot vienu labojumu). Pieci minimālie testu fixture ieguva `confirmed` kolonnu.
- Lēmums par kandidātēm (operators 2026-09-20): neviena netiek apstiprināta — #40/#47 jau `@devils-advocate` noraidītas; #48 Kulbergs (eksāmena termiņš) — pretruna ar valdības lēmumu, ne ar paša tekstu; #49 Mūrniece (SIF) — T14 klase (koalīcijas mēroga atturēšanās procedūras balsojumā, cits likvidācijas modelis). Sākumlapas «pēdējās pretrunas» tagad 16.07.2026 (#46 `new_date`).

---

## 2026-09-19 (3) — VAD profili rāda VISAS deklarācijas (bija 5); homonīmu verifikācijas metode; parādu/aizdevumu datu zudums salabts; deploy no WSL nedarbojas

- Profils: `templates/_vad_panel.html.j2` `vad_data[:5]` → `vad_data` — cilnēs visas deklarācijas (operatora lēmums: Šlesers kandidē, vecie dati pārbaudīti; max 28 cilnes — Kalniņa-Lukaševica). Šlesera 2002. gada deklarācija ar 5,93M USD aizdevumiem tagad publiska profilā.
- Homonīmu verifikācijas metode (pilns audits `docs/audits/2026-09-19-vad-interesantas-deklaracijas-sweep.md`, runbook `wiki/operations/vad-declarations.md` § Homonīmu piesārņojums): ģimenes-paraksts → amata līnija legacy deklarācijām → `vad_income.source` kā identitātes pirksts → Jev strīdīgajiem. Trīs purge partijas: 31+19+79 = 129 svešas deklarācijas, denylist 7→136, rollback SQL katrā. Jānis Zalāns paliek flagged (19 dekl., ≥2 tādvārži, nav pierādāms ne uz vienu pusi).
- Parseris+render: `vad_debts` bija tukša — `_parse_debts` prasīja ≥4 kolonnas, VAD dod 3-kolonnu (892 dekl.) un 1-šūnas brīvtekstu (105 dekl.); backfill 0→1499 debts / 365→458 loans; multiset-delta fix tukšam `creditor_name` (rindas salipa). Commiti `03fe769a`, `73cb9f35`; testi `tests/test_vad_parser_gaps.py`.
- Deploy: `bash scripts/deploy.sh` WSL shellī krīt ar «CLOUDFLARE_API_TOKEN missing» — `npx` iet caur Windows interop, Linux env nepropagējas (`WSLENV` nepalīdz). Deploy jātaisa no native Windows shell; WSL apdare `scratchpad/deploy_cf.ps1`. Dokumentēts `wiki/operations/deploy.md`.

---

## 2026-09-19 (2) — TypeSafe matcher veto: `morning_ingest.py` noklusējums ir ēnas režīms

- Lēmums (operators 2026-09-19): `scripts/morning_ingest.py` pats izpilda `os.environ.setdefault("ATMINA_TYPESAFE_VETO", "shadow")` pirms pirmā `src` importa (`src/matcher.py` mainīgo nolasa importa brīdī); `main()` žurnāla pirmā rinda `=== TypeSafe veto mode: … ===` ir saucējs. Gate: `tests/test_morning_ingest_veto_default.py` (tīra vide → shadow; `enforce` paliek; svīta `off`) — (a) redzēts sarkans pirms rindas.
- Kāpēc: ēnas nedēļai vajag 7 SECĪGAS dienas, un mainīgais ar roku katrā rutīnā ir trausls — viena aizmirsta diena atmet skaitīšanu (no 2026-09-18) uz sākumu.
- Kas nemainās: backfill skripti un testi paliek `off` (`tests/conftest.py` piesprauž pirms src importa; setdefault to nepārraksta); vides mainīgais `off|enforce` pārspēj; `enforce` tikai pēc 7 ēnas dienām bez zelta zaudējuma, mainot to pašu rindu — ne mašīnas līmenī. Runbook: `.claude/commands/dienas-rutina.md` § TypeSafe matcher veto.

---

## 2026-09-19 (1) — Projekta konts nav politiķis: @AtminaLV tvīti vairs nekļūst par dokumentiem; 09-18 atlikumi (b)(d)(e)(f) + Bērziņa T1 slēgti

- Kods: `src/matcher.py::PROJECT_X_HANDLES` + `is_project_account_url()`; `_store_tweets` projekta konta tvītu neglabā, `link_politicians_to_documents` to nelinko (abi rakstīšanas ceļi; `tests/test_social.py` ×3 — redzēti sarkani pirms labojuma). Iemesls: 8 @AtminaLV tvīti (05-14…09-18) ienāca kā `platform='twitter'` caur tagoto politiķu plūsmām, doc 110938 nonāca junction-atgūšanas kandidātos — pašcitēšanas cilpa. 27 vēsturiskās `mentioned` saites dzēstas, dokumenti paliek (`data/fix_project_account_junctions_2026-09-19.sql` + rollback; claims 0).
- Butāns (pid 82): `x_handle` + `social_accounts` `@ArtursButans` first_party (twikit-verificēts: id 126637083, «14.Saeimas deputāts | NA valdes loceklis»; `data/seed_butans_x_handle_2026-09-19.sql` + rollback); doc 110882 pārlinkots → 82 `mentioned`.
- Bērziņš (pid 146) T1: 8 `negative_patterns` celmi «Kaspars/Kaspara/Kasparam/Kasparu Bērziņ» + «sekretāra vietniek… Bērziņ»; viltus `subject` doc 71087 dzēsts (`data/update_berzins_kaspars_negative_patterns_2026-09-19.sql` + rollback). Pārbaudīts: 110795 un 71087 vairs nematcho, kontrole «deputāts Andris Bērziņš» matcho; doc 110049 (kails «Bērziņš», lede zudusi) celmi NEsedz — LSM lede klase.
- Šlesers #717712: `t.co/688LONh1LG` ved uz tvīta VIDEO, ne rakstu; LSM intervijas raksts (a663810, 19.09.) ingestēts kā doc 111520 un pozīciju apstiprina → marķieris «Izvērtēts 2026-09-19:», stance nemainās; doc 111520 lomu inversija (Kulbergs `subject`, Šlesers `mentioned`) labota ar roku (`data/fix_slesers_717712_review_and_doc111520_roles_2026-09-19.sql` + rollback). Blakus: `scripts/ingest_url.py --politician-id` ir NELIETOTS parametrs (`ingest_one` to nekur nepadod) — BACKLOG.
- Saites #1–#16 noraidīti (`saites_accept.py --reject` ×16; `data/rollback_saites_reject_1_16_2026-09-19.sql`); `pending` = 0. NEEDS_REVIEW rinda: 6 → 5 (Brigmanis, Zeltīts ×2, Kols, Krastiņa — nedēļas triāžā).

---

## 2026-09-18 (4) — TypeSafe ēnas nedēļa sākta ingestā; Saites priekšlikumu triāža kļūst par rutīnas 5. soļa daļu (pirmais dzīvais gājiens)

- Ēnas nedēļa: vakara `morning_ingest.py` pirmo reizi palaists ar `ATMINA_TYPESAFE_VETO=shadow` (per-process); `scripts/typesafe_veto_report.py --days 1`: judged 181, vetoed 2, no tiem 1 zelta zaudējuma kandidāts (Kučinskis vēsturiskā pieminējumā, `backlog/dati-db.md` § 2026-09-18 (a)). `enforce` tikai pēc 7 dienām bez šādas klases — skaitām no 2026-09-18.
- Saites: `scripts/saites_proposals.py --days 1` (docs 120, judged 120, 19 jauni priekšlikumi, 278 443 ievades tokeni) → triāža pret avota dokumentiem: 10 pieņemti (`political_tensions` #321–#330, tips un tēma — cilvēka izvēle, ne modeļa), 9 noraidīti; vecie #1–#16 (09-16/17 doki) apzināti palikuši `pending`, jo pieņemšana šodien radītu rindas ar šodienas `created_at` citas dienas notikumiem (rutīnas dienas logs).
- Pretrunu medības: 55 pozīcijas / 3 pases (logs 655334–655336, 24 noraidītie panelī); 1 kandidāts #49 (Mūrniece, SIF retorika↔atturēšanās) → `@devils-advocate` VILTUS (NA līnija publiska kopš 09.09. pirms balsojuma; JV *pret*, NA *atturas* — nav vienvirziena disciplīnas), `reviewed=1`, salience 0,2 (`data/rollback_da_contradictions_murniece_49_2026-09-18.sql`).
- Piezīmes #612 pirmspublicēšanas labojums (lielais burts) pēc inv. 8 otrā izņēmuma, ar rollback; `#717665` viltus NEEDS_REVIEW trigeris (frāze par trešo personu) izvērtēts ar rollback — ekstraktoriem: trigera frāzes nelietot arī par trešajām personām.

---

## 2026-09-18 (3) — Deep-check stale-pol 1. vilnis ar Jev īsajiem sarakstiem: 5 politiķi, 28 863 pāri, 4 kandidāti, 0 izdzīvo

- Tvērums: Braže (15), Pūpols (51), Vītols (64), Rinkēvičs (1), Hermanis (29) — `stale_pol_politicians()` top-5 pēc pozīciju skaita bez jebkad atrastas pretrunas; 1 048 pirmās puses pozīcijas. Jev: `scripts/jev_contradiction_shortlist.py <id> --all` × 5 → 28 863 kandidātu pāri, virs θ=0,3: 5 / 84 / 36 / 10 / 9 = 144; 725 pieprasījumi, 18,8 M ievades tokeni, ≈$0,78, modelis jev-1.13.0, 0 nepieejami.
- Hunteri (5 × `@contradiction-hunter`, Opus): Jev saraksts pirmais + pilna hronoloģija pa tēmām; ~330 pāri izvērtēti detalizēti, 87 noraidīti ar `why` (logs #655313–655317, dashboard panelis); 4 VIDĒJS kandidāti → `@devils-advocate`: Weak ×3, False ×1 (logs #655318) — **0 glabātu**, `contradictions` paliek 30 (3 neapstiprinātas). Divi orķestratora pieņēmumi datos neapstiprinājās un aģenti tos laboja: Rinkēvičam IR 102 `saeima_vote` (JV deputāts 2022-11-01…12-14, 72/102 procedurāli, 0 sakritību); Vītols NAV deputāts (`role` FM biroja ekonomists).
- Jev pret hunter: no 144 pāriem virs 0,3 hunteri par kandidātiem izvēlējās 4 un vēl ~20 no zem-sliekšņa lasījuma — saraksts strādāja kā lasīšanas secība (visi 4 kandidāti bija Jev top-10 sava politiķa sarakstā), bet «pretruna» šiem politiķiem galvenokārt izrādījās FP5 (tas pats viedoklis citiem vārdiem) un FP6 (leģitīma evolūcija).
- Blakusatradumi (rindu defekti, nekas nav labots): `backlog/dati-db.md` § Deep-check stale-pol 1. viļņa (Jev) blakusatradumi — Pūpols #6929/#7072/#14320, Vītols #14534/#14535/#532244/#7519 (citāts ne-verbatim), Rinkēvičs #103 (attiecināšana), Hermanis #164 (partijas konts kā pirmā puse), Pūpola K-B otrai pārskatīšanai.

---

## 2026-09-18 (2) — Jev pretrunu priekšfiltrs: zelta tests — iepriekš noteiktais vārts NAV izpildīts; operatora lēmums: v2 jautājums kā lasīšanas secība pie θ=0,3

- Ideja no pg-jev (Postgres paplašinājums; mums neder — SQLite), pārņemts tikai paterns: `src/jev_filter.py` (40 rindas/state ar `rows[i]` Noul, kešs `data/jev_cache.db`, `JevStats` denominators), `src/contradiction_candidates.py` (top-k kaimiņi no `claim_vectors`, pozīcijas bez `stated_at` izlaistas — virziens ir pretrunas priekšnoteikums), `scripts/jev_contradiction_eval.py`, `scripts/jev_contradiction_shortlist.py`. Jev DB neraksta; `confirmed` maina tikai operators.
- Kandidātu griesti: 23 zelta position↔position pāri, kandidātos 21/23 pie k=40 (57 139 pāri), 22/23 pie k=100 (126 199) — `jev_contradiction_eval.py --dry-run --k 40|100`; #4 (rank 132) un #37 (rank 82) ārpus — kNN, ne Jev.
- v1 «pretēja nostāja tajā pašā jautājumā» (`jev_contradiction_eval.py --k 40`, 1 428 pieprasījumi, 32,0 M tokeni, $1,35, `data/jev_eval_2026-09-18.json`): apstiprinātie ≥0,5 **2/18** — modelis atbild burtiski, atmina pretruna ir plašāka (vērtējums par partneri #17, nodoms→rīcība #44, šaubas→lēmums #38).
- v2 «nesavienojams — mainīta nostāja, vērtējums vai nodoms» izlasē 21 zelta + 1 000 nejauši pāri (`jev_contradiction_eval.py --k 40 --sample 1000 --seed 20260918`, modelis jev-1.13.0, ≈$0,03 pirmajā reizē, `data/jev_eval_2026-09-18_b998a2bd.json`; rinda «Nejaušo vien»): θ=0,3 → apstiprinātie **16/18**, nejaušo paliek **67/1000 = 6,7 %**; 18/18 tikai pie θ=0,22, kur paliek **32 %** (321/1000). Plāna vārts (visi apstiprinātie UN ≤30 %, θ∈0,5…0,9) tātad **nav izpildīts** — pirmajā ierakstā stāvēja «iztur» un «~26 %»; labots pēc gala pārskata (26 % bija `>` nevis `≥`). Zem 0,3: #36 (nosacījums ir tikai pretrunas kopsavilkumā, ne pozīcijās — datu robs) un #17 (0,28, robežgadījums). Pilns v2 atkārtojums par $1,35 apzināti izlaists.
- Operatora lēmums (sesijā, pēc skaitļu redzēšanas): v2 ir kanoniskais jautājums (`OPPOSITE_INSTRUCTIONS`/`OPPOSITE_CRITERIA`, `DEFAULT_THRESHOLD = 0.3`), `@contradiction-hunter` lasa Jev īso sarakstu PIRMO kā lasīšanas secību ar izmērītu 16/18, ne kā vārtus; balsojumu puse (T9) un `@devils-advocate` nemainās. Ja kāds nākotnē grib to saukt par vārtiem, jāpārmēra ar `--sample` un jāraksta jauns ieraksts.

---

## 2026-09-18 (1) — TypeSafe integrācija (1. kārta): matcher veto ēnas režīmā + Saites priekšlikumi cilvēka apstiprināšanai

- `src/typesafe_client.py` — System One (Jev) klients uz stdlib, atslēga `politracker/typesafe_api_key` (env `TYPESAFE_API_KEY` pārraksta); abi patērētāji krīt atvērti (`TypeSafeUnavailable` → līdzšinējā uzvedība). Plāns un piloti: `E:/typesafe/docs/superpowers/plans/2026-09-17-atmina-typesafe-integration.md`, `E:/typesafe/*_pilot*.py` (ārpus repo, lasa DB tikai ro).
- Matcher veto `ATMINA_TYPESAFE_VETO=off|shadow|enforce` (`src/matcher_veto.py`, āķis `match_politicians()`): sūta tikai uzvārda-vienīgi kandidātus (bez vārda, bez @handle, ne institucionālus). A0 pārbaude `matcher_pilot.py --gold 300 --seed 2`: 32/32 viltus saites noraidītas pie 0,6; zelta 286/300, no kurām 13 ir organizācijas (jautājums ir par personu → institucionālais izņēmums) un 1 kļūdains zelts (Kleinbergs, doc 188 — vārda tekstā nav). Slieksnis 0,6; sākam ar `shadow` nedēļu, ziņojums `scripts/typesafe_veto_report.py`; `tests/conftest.py` piesprauž `off`, lai testi nekad nesauc API.
- Saites priekšlikumi: tabulas `tension_proposals` + `tension_judged` (UTC), `scripts/saites_proposals.py` (viens pieprasījums dokumentam ar 2–5 personām, `p_link = 1 − p(none) ≥ 0,7` un `p_speaks ≥ 0,7`; `relation` ir tikai mājiens) + `scripts/saites_accept.py` (raksta `political_tensions` caur `store_tension`; `--type` pārraksta mājienu). Modelis `political_tensions` NERAKSTA. Dzīvais skrējiens `--days 2`: 119/119 dokumenti, 16 priekšlikumi, 0 kļūdu, 252 652 ievades tokeni (`logs` rinda `saites_proposals`).
- Rutīnas 5. solis (`dienas-rutina.md`) sākas ar priekšlikumu caurskati; `src/routine.py::_check_tensions` pievieno «N TypeSafe priekšlikumi gaida» rutīnas dienas logā. `ARCHITECTURE.md` tabulu skaits pārrēķināts: 43 (vecais 40 jau bija novecojis).

---

## 2026-09-17 (2) — Saeimas 4. paterns dzīvajā sēdē: 0 URL no 37; paralēls ingests + Saeimas ielāde = daļēja rakstīšana

- Pirmais dzīvais mērījums pēc 2026-09-16 (4): `_extract_vote_urls_from_agenda` uz `active=1`/`nr=` formas atgrieza 0 — dzīvais `drawDKP_*` nes 34 argumentus (fikstūra 21), GUID stāv `[5]`, vārti `[28]` `voteType`; apakšpunkti tikai `getTechDKP`. Sēde ielādēta ar roku pilnībā (87 balsojumi, 100/100 deputāti, paritāte 0 trūkst). Labojums: `backlog/saeima.md` [FIX].
- Balsojumam 8211 `store_vote` nostrādāja, claim ģenerēšana nomira ar «readonly database» (rīta ingests vienlaikus) → 16/74, idempotenti atkārtots 74/74. Līdz claims iet vienā transakcijā ar `store_vote`, Saeimas ielādi un `morning_ingest.py` nepalaiž paralēli.
- Datu lēmumi ar rollback: Uzulnieks (159) `party` → `Bezpartejisks` (Vergina precedents); #711070 dzēsts kā 10 dienu sindikācijas dublikāts (±5 d logs to neredz, Step 5 kNN ≤0,25 ir otrs dublikātu vārts); piezīmes #602–#605 un pārskats #608 laboti pirms publicēšanas (inv. #8 otrais izņēmums).

## 2026-09-17 (1) — Partiju tests 3. līmenis: 13 Opus aģenti, 93 klusē šūnas → 5 izteikumu šūnas; quiz vārts 1/12 → 2/12

Lēmums: līderu izteikumus kodē tikai tad, ja citāts apgalvojumu nolasa bez interpretācijas — 12 aģentu par/pret priekšlikumi → 5 pieņemti (LPV q04/q05, ASL q03, AS q02/q05; visi verbatim DB, `avots: izteikums`), 5 noraidīti uz klusē ar piezīmi (pagātnes forma, blakustēma, personiska nostāja), 2 gaida ingest (PRO q01 progresivie.lv, PRO q10 LSM stubs 29910). Saucējs: `partiju_tests_validate.py --quiz-gate` — cvk 72, pilna_programma 3, izteikums 5, klusē 88; `partiju_tests_audit.py` — vārtu iziet q01 + q05, par 63 : pret 17. Secinājums paliek: matrica tagad, quiz vēlāk. Blakus: LA pilnā programma dzīvo `attistibai.lv/programma2026/` (ne 403 domēnā) — 2. līmeņa ingest kandidāts; `lideris_id` 14/14 (LA = Ijabs, operatora lēmums). Faili: `content/partiju-tests/l3/`, `docs/plans/2026-09-17-partiju-tests-handoff.md`, tests `test_repo_audit_known_state` 11→10.

## 2026-09-16 (4) — Saeimas 4. paterns kodā; dzīvai sēdei paritātes audits apstājas; pārskata virsraksts no satura

- `scripts/p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda()` lasa `drawDKP_*(...)` 21. argumentu → `Voting?ReadForm&parentID={GUID}`; klase apzināti platāka par `drawDKP_Pr`, jo reģistrācijas zīmē `drawDKP_UT`. Mutācijas vārti: `tests/test_saeima_live_agenda_pattern4.py`.
- **Dzīvā sēde nekad nav zaļa:** `audit_saeima_agenda_parity.py` 4. vārti (`_live_session_stop()`, exit 2); abi backfill skripti dzīvo rindu izlaiž ar redzamu SKIP. Kas to izpildīja: tikai testi — pirmais dzīvais mērījums ir nākamā sēde.
- `src/render/blog.py` pārskata virsrakstu ņem no `parse_visual_brief(content)`; glabātais `visual_brief_json` ir fallback (`tests/test_blog_title_from_content.py`). Saucējs: 184 pārskati, 6 diverģē — operatora lēmums gaida `BACKLOG.md`.

## 2026-09-16 (3) — Cloudflare drošības ieteikumi: `security.txt`, SPF/DMARC, trīs «ne-darīt»

- `/.well-known/security.txt` (RFC 9116) renderējas no `static` domēna, `/security.txt` → 301 caur `assets/_redirects`; `verify_host.py` 8. pārbaude (`tests/test_security_txt.py`). Runbook: [`operations/cloudflare-security.md`](operations/cloudflare-security.md).
- SPF → `v=spf1 mx include:<…> ~all`: dzīvais ieraksts nesa 9 DNS vaicājumus no 10, un pie 10 visa SPF pārbaude atgriež `permerror`, t.i. nogāžas klusi. DMARC ieguva `rua=` + `fo=1`; `p=none` paliek, `p=quarantine` ir 2. solis pēc tīrām atskaitēm.
- Deploy tokenam ir tikai `Workers Scripts:Edit`, tāpēc neviens paneļa solis nav darāms no repo; zonas darbiem veido atsevišķu īslaicīgu tokenu un pēc darba to atsauc.
- **Noraidīts** (`BACKLOG.md` § Ne-darīt): Bot Fight Mode, AI Labyrinth, pasta ierakstu proksēšana.
- **Slazds:** bez adreses piesaistes (`--resolve`) `verify_host` var saņemt atbildi no lokālā DNS keša, t.i. no VECĀ hosta — piesaiste ir obligāta, kamēr kešs dzīvo.

## 2026-09-16 (2) — atmina.lv uz Workers custom domains; domēni paliek paneļa pārziņā

- `wrangler.json` ir **bez** `routes`, ar `workers_dev: false`; `tests/test_wrangler_config.py` invariants apgriezts (routes nedrīkst būt). Iemesls: `/zones/…/workers/routes` prasa zonas tiesības, un tās dot uz diska glabātam tokenam būtu solis atpakaļ drošībā.
- `www` → apex 301 un `http` → `https` ir Cloudflare paneļa kārtulas, ne repo konfigurācija.
- Vecais hostings paliek rezervē līdz **2026-10-16**; Task 9 (`htaccess.template` izņemšana) pēc tam. Atpakaļceļš pierakstīts `private/dns-atmina-2026-09-15.txt` (gitignorēts).

## 2026-09-16 (1) — Cloudflare Workers Static Assets: deploy, CSP galvenes, saknes pārrakste

- `scripts/deploy.sh` rsync/ssh zars → `npx wrangler deploy` (pilns koks; `--no-delete` / `--delete` ir no-op). CSP avots ir `assets/_headers`, kam jāsakrīt ar `assets/htaccess.template`, kamēr tas eksistē (`tests/test_headers_file.py`).
- `_copy_host_config()` (`src/render/_orchestrator.py`, 14a solis) kopē `.htaccess` + `_headers` + `_redirects` + `.assetsignore`; bez `.assetsignore` konfigurācijas faili atbild 200, jo Cloudflare servē visu koku.
- `html_handling: none` nozīmē, ka kailā `/` ir 404 — `assets/_redirects` rinda `/ /index.html 200` ir **rewrite**, ne redirect (`tests/test_redirects_file.py` aizliedz `.html` avotus).
- `scripts/verify_host.py` — 7 dzīvās pārbaudes, katra ar saucēju `n=`; nulles denominators ir FAIL, ne tīrs rezultāts (`tests/test_verify_host.py`).

## 2026-09-15 (4) — Servera koka audits: 12 tikai-serverī faili netiek pārnesti

Saucējs (`scripts/audit_remote_tree.sh`, tikai lasa): serverī 2 234, lokāli 2 222, tikai serverī **12**, tikai lokāli **0**. Visi 12 ir trīs pārskatu noraidīto attēlu varianti (`brief_images.approved ∈ {0, 2}`) ar **0 atsaucēm** kokā. **Lēmums: nepārnest** — uz Cloudflare tie vienkārši neeksistē, un 404 uz tiem nav regresija. Secinājums migrācijai: lokālais koks ir pilns deploy avots bez papildu kopēšanas.

## 2026-09-15 (3) — DNS zona pārnesta uz Cloudflare

25 ieraksti pārnesti 1:1 un pārslēgti uz `DNS only`; pasts pārbaudīts abos virzienos. Apzināti **nepārnesti** ~20 addon-domēna `*.atmina.lv` artefakti — tos nelieto neviens. Atpakaļceļš: reģistrā atlikt vecos vārdserverus (pierakstīti privātajā eksportā); Cloudflare zona paliek.

## 2026-09-15 (1) — Balsojumu tēmu vārda robeža, `image_audit` dublikāti, «Aktīvākie» pēc salience

- `topic_map._SAEIMA_KEYWORD_MAP` sakrīt tikai **vārda sākumā**: kaila apakšvirkne «ets» vārdā «pretstatā» bija ielikusi balsojumu zem `Klimats` (`tests/test_topic_map.py::TestSaeimaKeywordWordBoundary`). Celmi `mācīšan` / `pacientu tiesīb` / `medicīnisk` pacelti virs Kultūras bloka.
- `generate_image()` un `apply_migrations()` backfill rakstīja **divas** `image_audit` rindas vienam attēlam; sasaiste tagad iet caur `storage.link_audit_row()` abos ceļos (`tests/test_graphics_storage.py::TestLinkAuditRow`).
- «Aktīvākie politiķi» neizšķirtu izšķir `MAX(c.salience) DESC` pirms `p.name ASC` (`tests/test_briefs.py::TestAktivakieTieBreakBySalience`).
- Jauna `@claim-extractor` Step 3c klase: **simulācijas spēle** (izdomāts scenārijs) nav nostāja → `empty_doc_ids`.

## 2026-09-14 (5) — Divas rutīnas kārtulas, ko lints nesargā

- **`check.sh` nedrīkst iet paralēli ar `@graphics-designer`:** ražošanas-DB sargs skaita `image_audit` rindas un dod viltus ERROR. Secība ir attēls → `check.sh`, nekad vienlaikus.
- **Orkestratora prompta amatu etiķetes nav patiesības avots** — `role` pirms dispatch lasa no `tracked_politicians`, ne no atmiņas (divas nepareizas etiķetes 2026-09-14; aģenti pareizi paļāvās uz DB).

## 2026-09-14 (4) — Partiju tests: `saraksti.yaml` kā vienīgā sarakstu patiesība; matrica bez quiz

- `content/partiju-tests/saraksti.yaml` (14 CVK saraksti) ir vienīgais sarakstu avots; validators v2 šķiro trīs avotu līmeņus (`cvk` / `pilna_programma` / `izteikums`).
- Virziena balansu mēra **bez `bloks` lauka** — koalīcijas iedalījums nākamajām vēlēšanām nav jēgpilns (operatora lēmums).
- **Operatora lēmums: «matrica tagad, quiz vēlāk.»** Programmas sola, ne iebilst (par 59 : pret 16), tāpēc quiz vārts iziet 1 no 12 jautājumiem. Atsākšanas priekšnoteikums: `lideris_id` 14 sarakstiem + 3. līmeņa 2026. gada izteikumi.

## 2026-09-14 (3) — Pārskatu saraksts kārtojas pēc SATURA datuma, ne `created_at`

Tās pašas dienas pārskata UPSERT atsvaidzina `created_at` (kājenes «Atjaunots»), tāpēc `created_at DESC` izspieda svaigus pārskatus no sākumlapas. `src/render/blog.py` pēc slugu dedupa kārto pēc `(satura datums, nedēļas > dienas, created_at)`; nedēļas pārskata satura datums ir nedēļas **beigu** diena. Skartās virsmas: sākumlapas režģis, `analizes.html`, `dashboard.py`. Vārti: `tests/test_blog_posts_order.py`. Tā pati klase kā «brief identity = subject date», tikai saraksta pusē.

## 2026-09-14 (2) — Apakšpunktu balsojumi redzami TIKAI `nr={DkId}` formā

Dzīvās `active=1` / `actual=1` lapas apakšpunktus nerenderē, un 4. paterna punkta lapa tādam balsojumam ir tukša — tāpēc 2026-09-10 sēdei DB bija 16 balsojumi pret patiesajiem 21. **Rokas paritāte pret darba kārtības etiķetēm nav pietiekams saucējs:** apakšpunktiem etiķešu nav. Dzīvai dienai vajag `DK?ReadForm&nr={actualXML_DkId}` apvienībā ar 4. paternu. Blakus: `parentID=` URL dod datus tikai, kamēr sēde ir «actual» — stabilā forma ir `/0/{HEX}?OpenDocument`.

## 2026-09-14 (1) — Nedēļas statistika izslēdz klātbūtnes reģistrācijas; publicēta faktu kļūda labota

- `generate_weekly_brief` `votes=` vairs neskaita «Deputātu klātbūtnes reģistrācija» rindas (`_REGISTRATION_MOTIF_PREFIX` — DC #4b analogs publiskajai statistikai); `tests/test_briefs_weekly.py::test_weekly_votes_stat_excludes_attendance_registrations`. Vēsturiskie `WEEKLY_STATS` marķieri nav pārrēķināti.
- **Operatora lēmums:** publicētie pārskati #562/#570 laboti (nepatiess «valdība apstiprināja 300 % tarifu»), bet konteksta piezīmes #557/#569 **nav** — agrāka diena un jau publicētas, tātad inv. #8 append-only bez izņēmuma.
- Labošanas skripts nepārraksta jau esošu rollback failu un jau piemērotu labojumu izlaiž: atkārtots palaidiens citādi iesaldētu jau laboto tekstu kā «pre-image».

## 2026-09-13 (2) — `negative_patterns` ir divu patērētāju kolonna

- Kolonnu lasa **divi** filtri: `src/vad/declarations.py::_row_passes_disambig` (meklēšanas lauks = institūcija + amats, kam paterns bija domāts) un `src/matcher.py::match_politicians` (apakšvirknes salīdzina pret VISU dokumentu → viss doks veto). VAD homonīmam domāts paterns tāpēc klusi nogrieza ziņu junction.
- Mērījums, kas to izšķīra (60 dienas): 3 130 doki ar «Kulberg», 66 ar «Valsts policija», **66/66 par premjeru, 0 par inspektoru**. Veto noņemts, 9 junction rindas atgūtas; Vilkam paterns sašaurināts uz celmu «Dzelzs Vilk». Dizaina jautājums → `backlog/matcher.md`.
- Grafikā: LV + ES karogi atļauti kā vides elementi — `NEGATIVE_CONSTRAINTS` un `TEXT_FREE_CONSTRAINTS` dala kopīgu `_SUBJECT_EXCLUSIONS` prefiksu, lai nedreifētu. `cli brief` noklusējums ir `sepia` + `no_text`, ar jaunu `--with-text`.

## 2026-09-11 (2) — Medību tvērumu pārbauda ar skaitli, ne ar atmiņu

Pēc junction-atgūšanas pases glabāts claim var palikt ārpus visiem `@contradiction-hunter` tvērumiem. Vārts: `SUM(claims_checked)` pār dienas medību `logs` rindām **==** `COUNT(claims)` tajā dienā; nesakritība nozīmē, ka jāpalaiž vēl viens mednieks.

## 2026-09-11 (1) — NUL vārts skenē tikai teksta failus un prasa saucēju

`test_no_tracked_wiki_page_contains_nul_bytes` skenēja `git ls-files wiki` bez formāta filtra, tāpēc versionētie sintēžu PNG to turēja **pastāvīgi sarkanu**. Tagad tas skenē tikai `_WIKI_TEXT_SUFFIXES` **un** prasa ≥ 300 skenētus failus, lai filtrs pats nekļūtu par vārtiem, kas neko neskatās; abas mutācijas pierādītas krītošas. Blakus atradums, kas paliek klasei: kirilicas burts latīņu vārda vidū (`wiki/operations/video-setup.md` «stадijas») — tādu vārdu neatrod ne grep, ne vietnes meklēšana. Skenējums nav automatizēts.

## 2026-09-10 (2) — Saeimas 4. URL paterns (T12): dzīvā darba kārtība nerenderē balsojumu saites

Visi trīs kanoniskie paterni dzīvai sēdei atgrieza **0**, t.i. kanoniskā apvienība bija tukša un diena formāli nolasījās kā 2.B STOP. GUID stāv `drawDKP_Pr(...)` 21. argumentā; no tā būvējams `Voting?ReadForm&parentID={GUID}` (pieraksts `.claude/agents/saeima-tracker.md` Step 2.B; 76 kandidāti → 16 balsojumi). `DK?ReadForm&actual=1` ir bagātāks par `nr={uuid}` — ņem abus. Tolaik paterns dzīvoja tikai promptā, tāpēc tās pašas dienas paritātes audits bija **viltus zaļš** (kodā aizvērts 2026-09-16 (4)).

## 2026-09-10 (1) — `draft: true` vārts kurētajām analīzēm (T15 klase)

Šaurais renders bija ielicis nepublicētu melnrakstu `output/atmina/analizes/`, un nākamās rutīnas deploy to būtu aizvedis live. `src/render/analyses.py` tagad izlaiž kartītes ar `draft: true` (`tests/test_analyses_draft.py`, abi virzieni), un ģenerators noklusēti raksta ārpus `curated/` (`--publish` raksta uz curated).

## 2026-09-09 (1) — Data Contract #8 otrais izņēmums + nesēju asimetrija

- **Operatora lēmums, ierakstīts `CLAUDE.md`:** tās pašas rutīnas dienas, vēl nepublicētu `context` piezīmi drīkst labot uz vietas — abas robežas obligātas (tā pati diena **un** nav deployots), ar pāra rollback.
- **Nesēju asimetrija:** `context` piezīme renderējas `context-box` un drīkst būt aizzīmēs; `political_tensions.description` iet markdown tabulas šūnā un tam jābūt **vienā rindā** — jaunrinda tur sašķeļ rindu. Verificē renderētajā HTML, ne markdown avotā.
- Jauna T-klase: kails HTML tags CSS komentārā `<style>` iekšienē norij atlikušo CSS — lapa aizgāja live bez sava stila. Zonde, kas deva 0 abiem paterniem, bija salauzts vārts, ne tīrs rezultāts.
- `lint_lv_style` bija zaļš visās četrās `@quality-reviewer` bloķēšanas kārtās: lints nepareizas partiju birkas, pārspīlējumus un iekšēju pretrunu neredz.

## 2026-09-07 (13) — 13. pārbaude izslēdz `saeima_vote`; tēmas lapas saites uz Pozīciju cilni

- `scripts/audit_vector_staleness.py` izslēdz `saeima_vote` no kandidātu kopas un ziņo `saeima_vote_izslēgti=N`: audits citādi baroja rindas, ko 2026-08-21 verdikts aizliedz pārrēķināt (`tests/test_audit_vector_staleness.py`).
- Tēmas lapas «Turpini rakt» saites nes `?tema=<tēma>#pozicijas` — `ppv1.js` cilni ņem no hash, tāpēc bez tā profils atvērās Pārskatā (`tests/test_topics.py::test_profile_links_carry_the_tema_param_and_pozicijas_hash`, saucējs ≥ 2).
- Ražošanas-DB sargs neatšķir testu no fona ingest: **nelaid `check.sh` un ingest reizē.**

## 2026-09-07 (12) — Trīs precedenti no NEEDS_REVIEW triāžas

Rinda 55 → 0 (40 apstiprinātas, 1 pārkartota, 14 dzēstas). Precedenti, kas paliek: prezidenta formālie akti (komisiju sastāvi) glabājas kā pozīcijas; datu grafikas tvīts bez priekšlikuma ir derīga pozīcija (operatora lēmums 2026-09-05); politiķa retorisks apgalvojums par institūcijām glabājas ar atrunu. Dzēstajām claim rindām **dokumenti paliek** — profila X apakšcilne tos rāda joprojām («claim deleted ≠ content removed»).

## 2026-09-07 (11) — Profila tēmu filtrs: `[hidden]` prasa skaidru CSS

Pozīciju cilnes tēmu filtrs pārzīmēts «Saites» cilnes valodā (punkts tēmas krāsā, skaits pogā, secība pēc pozīciju skaita dilstoši); pogas aiz 12. tēmas nāk ar `hidden`, un tās atklāj poga «Vēl N tēmas». **Slazds:** `hidden` atribūtu pārraksta pogas `display: inline-flex`, tāpēc CSS vajag skaidru `[hidden] { display: none }`. `ppv1.js::revealTopicButtons()` gādā, ka aktīvā poga nekad nav neredzama (`tests/test_profile_topic_deeplink.py`).

## 2026-09-07 (10) — 2026-09-06 verdiktu kārta noslēgta

52 lēmumu rindas: **31 izpildīta**, **5 NESAKRĪT** (mērījums apgāza verdikta pamatojumu, DB nemainīts), 1 neizpildīta pretrunas dēļ, 2 sagatavotas operatora apstiprinājumam, 13 atliktas vai «nē». Per-rindas statuss: `docs/verdikti-2026-09-06.md`; izpilde — ierakstos (1)–(9).

## 2026-09-07 (9) — Avota etiķete no `source_domain`; viens attēlu budžeta saucējs; CSP ieejas punkts

- Claim virsmas etiķete nāk no `documents.source_domain` un uz URL hostu atkāpjas tikai rindām bez dokumenta (`saeima_vote`). **`source_url` nav migrēts** — tas ir `store_claim()` idempotences trijnieka daļa (`tests/test_source_domain_label.py`).
- Jauna `image_audit` tabula, ko raksta pati `generate_image()`: `brief_images` mērīja tikai `brief --note-id` ceļu, tāpēc `cli thread` un tiešie izsaukumi budžetā neparādījās. `brief_images` paliek apstiprināšanas darbplūsma (`tests/test_image_audit.py`).
- `python -m src.csp` — noklusējums ir sauss palaidiens pret `data/csp.db` **kopiju**, `--apply` jāraksta ar roku, nulle atsvaidzinātu tabulu → exit 1 (`tests/test_csp_entrypoint.py`).
- X pūls pārmērīts: 5 sloti × 4 endpointi = 20/20 OK. `get_pool().status()` šim nederētu — svaigā procesā tas vienmēr ziņo 5/5 «available».

## 2026-09-07 (8) — Divi jauni audita saucēji un `claims.review_status_at`

- `store_claim()` joprojām **apzināti nenormalizē** `topic` (`topic` ir idempotences atslēgas daļa; normalizācija bez sausa palaidiena ir tā pati klase, kas 2026-08-02 saražoja 4 087 dublikātus). Vietā stāv `/audit-integrity` 18. pārbaude — `scripts/audit_topic_canonical.py`; `checked=0` ir exit 2 ar tekstu «salauzti vārti».
- 9. pārbaude negrupē politiķus bez frakcijas etiķetes, tāpēc klusēšana lasījās kā «tīrs». `scripts/audit_minister_vote_coverage.py` nosauc klasi ar skaitli un sarakstu (bāzlīnija `checked=25 flagged=6`).
- `claims.review_status_at` — jauna kolonna, ko uztur **tie paši** divi trigeri, kas `review_status`. Vēsturiskajām rindām NULL, tāpēc lasītāji lieto `COALESCE(review_status_at, created_at)`; vārta forma pārcelta no promptiem uz kodu (`src.db.open_review_queue()`).

## 2026-09-07 (7) — `role='subject'` prasa runātāju

Jauns `src/roles.py` ir vienīgais īpašnieks jautājumam, kurš drīkst nest `role='subject'`; abi bulk-rakstītāji (`db.insert_document`, `matcher.link_politicians_to_documents`) iet caur to. Divas klases vairs nerada `subject` rindas: releja mediju sloti (`relationship_type='organization'` **un** `feed_type='relay'`) un kaili retvīti no biroja balss konta. **NBS (pid 204) apzināti nav vārtā** — tas ir `first_party` ar 40 pozīcijām, un vārts pār `organization` nogrieztu dzīvu kanālu, tāpat kā LDDK, LVM, Valsts kontrolei un Latvijas Bankai; tas ir domēna, ne lomas jautājums. Vārti: `tests/test_subject_role_guards.py`.

## 2026-09-07 (6) — Trīs mērīti «nē» matcher formu jautājumos

- Tukšas `name_forms` **nenozīmē** trūkstošus locījumus — matcher tos ģenerē pats; trūkst tikai ASCII variantu, un 89 649 doku korpusā 61 no 66 ierosinātajām formām nedeva nevienu trāpījumu.
- `negative_patterns` ir **reģistrjutīga apakšvirkne, ne regulārā izteiksme** — «vadītāj» ar aizstājējzīmi tur nestrādā.
- Releja slots RT trokšņa dēļ nav risinājums, ja pozīcijas nāk no paša tvītiem: pid 187 — 211 no 237 `subject` doku ir RT, bet **visas 28 pozīcijas ir viņa paša**.
- Iesēdināti pid 246 Pujāts un pid 247 Freifalts; kohortas audits (T13) atrada **2 nepatiesas rindas no 26** — vārdabrālis kardināls.

## 2026-09-07 (5) — Vēstneša akti uzrādāmi rutīnā; nogrieztais ievads tiek karogots

- Vēstneša izslēgšanu attaisnoja pārskata sadaļa, kas bija izmesta 2026-08-03 — kompensējošas virsmas nebija vispār. Vietā `src/routine.py::vestnesis_acts_for()` uzskaita dienas MK / Saeimas / Valsts prezidenta aktus ar saucēju «N no M Vēstneša dokiem dienā». Tā ir **rinda, ne solis**: solis te būtu mūžīgi zaļš (`tests/test_routine.py::TestVestnesisActsAreSurfaced`).
- `_looks_like_cut_lede()` (`src/ingest_rules.py`) **karogo, neatmet** — 56 trāpījumi 14 737 web dokos, 0 nepareizu atribūciju pārbaudītajos. Doc id iet `logs.details` (`cut_lede_doc_ids`), bez shēmas migrācijas; saucējs ielādes žurnālā arī tad, kad N = 0 (`tests/test_ingest_cut_lede.py`).

## 2026-09-07 (4) — Kailā «Melnis» klase: eval vārti to nevar noķert

Deviņas junction rindas pārceltas no pid 157 (Kaspars Melnis) uz pid 224 (Raivis); **neviena no 54 pid 157 pozīcijām Raivim nepiederēja.** Divās mūsu pašu `stance` rindās kailā avota forma «Melni» bija izvērsta uz nepareizo priekšvārdu — to pievienoja ekstrakcija, avota tvītos priekšvārda nav; abas izlabotas un pārvektorizētas, publicētie pārskati netiek pārrakstīti. **32 marķēto FP gadījumu kopā Meļņa klases nav**, tāpēc `scripts/eval_matcher_collisions.py` to nevar noķert — pirms jebkuras `negative_patterns` maiņas kailajai formai regresijas kopā jāieliek Meļņa gadījums.

## 2026-09-07 (3) — Trīs konvencijas nesējos + confidence-drift saucējs

- **`stated_at` ārpus 7 dienu loga:** ja izteikuma faktiskā diena ir ārpus dienas pārskata grīdas, `stated_at` ir publiskošanas diena, bet izteikuma īstais datums jāpasaka `stance` tekstā (`@claim-extractor` Step 4). Vēsturiskās rindas netiek bīdītas.
- **Māsas balsojumu kopsavilkums:** `summary` pieder likumprojektam, ne balsojumam, tāpēc jauniem ne-lasījumu balsojumiem iznākuma teikums kopsavilkumā ir aizliegts (`generate_claims_from_votes` docstring + `@saeima-tracker` 3.B). Koda loģika nemainīta; vēsturiskās rindas netiek pārrakstītas.
- **Laika apgalvojumi:** katrs laika apgalvojums spriedzē vai tendences piezīmē pārbaudāms pret avota datumiem tikpat stingri kā citāts pret avota tekstu (`@quality-reviewer` § C2; `TIME_PHRASES` 8 → 11 frāzes).
- `check_confidence_drift()` klusē, kad kādā pusē ir mazāk par 5 claims, un katra brīdinājuma rinda iet caur `format_drift_line()`, kas rāda n abās pusēs (`tests/test_confidence_drift.py`).

## 2026-09-07 (2) — T6 klase: `role` un `relationship_type` četrās rindās

Melbārdei, Labanovskim un Ruģēnam izlabots `role`; Štekerhofs `inactive` → `tracked` (514 `faction='ZZS'` balsojumi pēdējā gadā, pēdējais 2026-09-03), kas atgrieza doc 90283 ekstrakcijas rindā. **`party` apzināti nemainīta** tur, kur nav frakcijas krustpārbaudes (pid 155 — 0 balsojumu rindu). Apstiprināts arī, ka pid 62 Svirska **divas** `social_accounts` rindas paliek: deaktivēšana apturētu dzīvu kanālu, un `/audit-integrity` 2. pārbaude pēc `active` nefiltrē, tāpēc karogu tas nemaz nenoņemtu.

## 2026-09-07 (1) — Četras pozīcijas atsauktas; citāta «trūkums» izrādījās pieturzīme

Atsauktas #689743, #689646, #703870, #704024 (klastera atkārtojumi, pašas RT, gadadienas apsveikums bez instrumenta). Avota doki palikuši ar `reviewed_at` — **atsaukta ir atmina.lv apgalvojuma, ne cilvēka ieraksta klātbūtne**; publicētie pārskati netiek pārrakstīti. Divi verdikti atsaukti pēc avota izlasīšanas: #615955 citāts doc 80022 **ir** — 251 no 252 zīmēm sakrīt zīme zīmē, atšķiras vienīgi noslēguma pieturzīme, tātad tā ir pieturzīmju, ne pārskrāpēšanas klase.

### Izlaistie sesiju ieraksti

Šie ieraksti bija sesiju hronika bez lēmuma vai invariantu izmaiņas; saturs dzīvo `git log`.

- 2026-09-15 (2) → git log
- 2026-09-13 → git log
- 2026-09-12 (2) → git log
- 2026-09-12 (1) → git log
- 2026-09-08 (2) → git log
- 2026-09-08 (1) → git log

## Arhīvs (2026-04 — 2026-09-06)

Vecākie ieraksti dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md), kas **iesaldēts 2026-09-16** — tam vairs neko nepievieno. Zemāk enkuru-stubi ierakstiem, uz kuriem atsaucas `CLAUDE.md` un aģentu prompti; virsrakstu teksts saglabāts identisks, lai saites turpina strādāt.

## 2026-07-29 — Kurētās analīzes `standalone: true` paterns + NVO dotāciju lapa

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Kurētās analīzes](CHANGELOG-arhivs.md#2026-07-29--kurētās-analīzes-standalone-true-paterns--nvo-dotāciju-lapa)

## 2026-07-27 — Matcher B2+D2+H: vārda robežas, paplašinātais priekšvārda veto, @handle formas

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Matcher B2+D2+H](CHANGELOG-arhivs.md#2026-07-27--matcher-b2d2h-vārda-robežas-paplašinātais-priekšvārda-veto-handle-formas)

## 2026-07-24 — T7 slēgts: brief skelets vairs klusi nemet tēmas (Pārējās tēmas tabula)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § T7 slēgts](CHANGELOG-arhivs.md#2026-07-24--t7-slēgts-brief-skelets-vairs-klusi-nemet-tēmas-pārējās-tēmas-tabula)

## 2026-07-23 — Stingrā CSP: drošības galvenes + viss inline JS uz assets/*.js

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Stingrā CSP](CHANGELOG-arhivs.md#2026-07-23--stingrā-csp-drošības-galvenes--viss-inline-js-uz-assetsjs)

## 2026-04-25 — Strukturālā sanācija: pub_at meta tag fix + Saeima vote-as-document anti-pattern noņemšana

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Strukturālā sanācija](CHANGELOG-arhivs.md#2026-04-25--strukturālā-sanācija-pub_at-meta-tag-fix--saeima-vote-as-document-anti-pattern-noņemšana)

## 2026-04-25 — Commentator demotion + profila X subtaba

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Commentator demotion](CHANGELOG-arhivs.md#2026-04-25--commentator-demotion--profila-x-subtaba)

## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § feed_type](CHANGELOG-arhivs.md#2026-04-23--social_accountsfeed_type-relay-vs-first_party)

## 2026-04-23 — Komentētāji (speaker_id on claims)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Komentētāji](CHANGELOG-arhivs.md#2026-04-23--komentētāji-speaker_id-on-claims)

## 2026-04-11 — claim_type split (`position` vs `saeima_vote`)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § claim_type split](CHANGELOG-arhivs.md#2026-04-11--claim_type-split-position-vs-saeima_vote)
