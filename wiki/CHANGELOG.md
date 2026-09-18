# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. § Izlaistie sesiju ieraksti.

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

Ieraksti līdz **2026-09-06** (ieskaitot) dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md), kas 2026-09-16 iesaldēts; atsauktajiem ierakstiem šeit paliek enkuru-stubi (§ Arhīvs faila beigās). `tests/test_changelog_anchors.py` sargā, lai katra ienākošā enkuru atsauce uz abiem failiem atrisinās; pirms virsraksta teksta maiņas palaid to.

Virsraksta forma `## YYYY-MM-DD (n) — …` ir atsauces atslēga (`BACKLOG.md`, `backlog/*.md` un runbooki citē to prozā) — `YYYY-MM-DD (n)` prefiksu nemaina.

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
