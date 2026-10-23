# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md) § Izlaistie sesiju ieraksti.

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

## 2026-10-23 (2) — Pretrunu kartīte bez bēšām kastēm; dalīšanās pogas; viens pretrunu vaicājums (operators)
- Pretrunu kartīte (`prv2_card`, 4 vietas) = viena `--paper` virsma ar hairline atdalītājiem; augšējā josla 3 px smaguma krāsā (partijas krāsa paliek avatāra rāmī). «Citas šī politiķa pretrunas» = plakans saraksts ar `headline` un datumiem (iepriekš divas kartītes rādīja vienādu tēmu + kopsavilkumu). Tests `test_pretrunas_mobile.py` (abi sarkani pirms labojuma).
- `share_buttons` makro visur (profils, tēma, pretrunas): klusa teksta rinda ar CSS maskas ikonām; telefonā (`pointer: coarse` + `navigator.share`) — sistēmas dalīšanās izvēlne, datorā X. Tests `test_share_button_opens_phone_share_sheet` (krīt, ja JS atslēgts).
- Profila pretrunu vaicājums neņēma `claim_type`, tāpēc 10/33 «vārdi pret balsojumu» pretrunas profilā rādīja «Retorikas maiņa» (skaits: profilu HTML «Vārdi pret darbiem» 0 → 10). Tagad viens `fetch_contradictions()` (`src/render/_common/contradictions.py`), un `_enrich_contradiction` met KeyError bez `old/new_claim_type`. Tests `test_profile_contradiction_labels.py`.
- Partiju cilņu etiķetes telefonā: burts seko pogas platumam (`min(…rem, 14cqi)`), jo ar platāku fontu (Linux CI, daļa Android) «PROGRAMMA» izlīda pāri pogai; `test_party_tab_bar_has_no_lone_tab_on_phone` tagad mēra arī ar platu fontu (sarkans pirms labojuma).

## 2026-10-23 — Profila galvene divās kolonnās un biogrāfijas paneļi (operators)
- Identitāte un biogrāfija ir atsevišķas, pēc platuma salokāmas kolonnas; foto blakus vārdam un lomai, saites zem tiem (`templates/politician.html.j2`, `assets/style.css`).
- «Vēl» un VID amati atveras ar HTML `popover`, nepārbīdot cilnes; kopīga izvēršanas bultiņa, aizvēršanas poga un ritināms panelis. Bez CSS enkura atbalsta panelis atveras centrā; jauns JS nav vajadzīgs.
- `test_long_bio_hero_columns_and_popover_keep_tabs_still` pirms labojuma krita: cilnes pārbīdījās par 377 px; pēc labojuma pārbīde 0 px. Saglabāti bio satura un kopīgā izvēršanas stila testi.

## 2026-10-23 — Profila galvenes biogrāfija īsa (operators)
- `templates/politician.html.j2`: galvenē 1 izglītības ieraksts + 3 CVK darbavietas; pārējais izvēršamā «Vēl: N darbavietas, M izglītības ieraksti» (`.profile-bio-rest`). Iemesls: Brēmanim 14 darbavietas izstiepa labo joslu; 66/225 profiliem > 3 darbavietas (skaitīts renderētajā `output/atmina/politiki`).
- Tests `tests/test_bio.py::test_long_bio_keeps_header_short` (sarkans pirms labojuma).

## 2026-10-23 — Vienota izvēršana un deklarāciju gadu čipi (operators)
- `assets/style.css` «Izvēršana»: visi `details > summary` lieto vienu bultiņu rindas beigās, fokusu, nospiešanas stāvokli un kustības izvēlei pakļautu animāciju; komponentes saglabā izkārtojumu. Datorā «Saturs» joprojām vienmēr redzams.
- Deklarāciju gadi lieto `.chip` un `.chip-row`; telefonā viena ritināma rinda, `ppv1.js` āķi saglabāti. Noņemtas arī veidņu un saglabāto statistikas lapu trijstūru kopijas.
- Tests `test_disclosures_and_declaration_years_share_one_look`: īstais renderētājs ar sintētisku DB, abas tēmas un 390/1280 px; krīt ar iepriekšējo CSS (marķieri un čipu forma).

## 2026-10-23 — «Saturs» telefonā aizvērts, avīzes izskats (operators)
- `templates/blog-post.html.j2` `.post-toc` = `<details>`: telefonā rinda «Saturs · N sadaļas» (aizvērta, ≥ 44 px), datorā saraksts vienmēr atvērts (`::details-content` pārraksts, ≤ 600 px robeža); numurēts `01…`, serifs, bez pelēkās kastes.
- Iemesls: telefonā atvērtais saraksts aizņēma pirmo ekrānu. Tests `tests/test_analysis_toc.py` (390 px aizvērts / 1280 px atvērts; sarkans ar `open` pēc noklusējuma), `test_phone_tap_targets.py` «saturs» mēra arī rindu.

## 2026-10-23 — Pamatelementi: viens čips, viens segmentu slēdzis, viens meklēšanas lauks (operators)
- `assets/style.css` sadaļa «Pamatelementi»: `.chip`/`.chip-row`, `.seg-ctl`, `.field` — izskats tikai tur; lapu klases (`.filter-btn`, `.link-filter-btn`, `.prv2-chip`, `.slv-lens`, `.bill-search-input` …) paliek HTML tikai JS un izkārtojumam. Aktīvais = `.active` vai `aria-pressed="true"`.
- Pirms: 8 čipu, 5 lauku, 2 slēdžu formas (`tests/test_ui_basics_one_look.py`, 9 lapas × 2 tēmas × 1280/390 px, sarkans uz vecā koka); pēc: pa vienai. Paraugs — Pretrunu čips.
- Tajā pašā dienā (operators «dari tā ar visu»): arī Pozīcijas/Personas/X čipi un meklēšana, izvēlne čipu rindā čipa augstumā (`multi_select compact`), visas tabulas — viens izskats (`tests/test_ui_tables_one_look.py`, galvenes 5→1). Paliek atsevišķi: pasvītrotās cilnes, sānjoslas rindas. Klase `.seg` aizņemta NVO diagrammās — tāpēc `.seg-ctl`.

## 2026-10-22 (7) — Pilsonības pozīcijas → «Sociālā politika»; kails «Par priekšlikumu Nr.N» nemanto lēmumu (operators)
- Operatora «par tēmām izlem» (22.10.): Višvanatas lietas pozīcijas tēmā «Imigrācija» pārliktas uz «Sociālā politika» (`src/topic_map.py`: pilsonība; RUBRIKA 15. noteikums) — 25 rindas, pārrēķināti vektori; rollback `data/rollback_claims_topic_pilsoniba*_2026-10-22.sql`.
- `topic_for_new_vote`: kails «Par priekšlikumu [Nr.N]» bez dokumenta numura nemanto `motif:` lēmumu (atslēga apvienoja 2609 + 6686); tests `test_bare_amendment_motif_never_inherits_decision` (bez labojuma krīt).
- b02n: 22.10. sēdes 7 dokumentu cilvēka lēmumi piemēroti balsojumiem (`BATCH_LOG.md`).

## 2026-10-22 (6) — Balsojumu tēmas: Saeimas kārtības rullis → «Valsts pārvalde» ar noteikumu, bez Jev
- RUBRIKA 2026-10-22.2 robežu Jev b01/b02 kļūdīja (267, 975/Lp14), tāpēc `src/saeima/topics.py::rule_topic` (ielāde un `classify`) dod tēmu bez zvana, kā klātbūtnes reģistrācijai.
- Ķer tikai «kārtības rullī/rullis»: «(Saeimas kārtības ruļļa 39.p. kārtībā)» ir procedūra 40+ citos likumos (DB vaicājums `motif LIKE '%kārtības ru%'`, 22.10.) — tiem tēmu dod Jev.
- Testi `test_rules_of_procedure_is_public_admin_without_classifier` (mutācija «ru» → krīt), `test_cli_classify_then_review_list`.

## 2026-10-22 (5) — Balsojumu tēmas: viens dokuments Jev pieprasījumā, partijām slieksnis 0,8 (labo (4))
- Jev atbilde atkarīga no citiem dokumentiem tajā pašā pieprasījumā (565/Lp14 viens: Tieslietas 0,72; 16 dokumentu paketē: Budžets 0,27), bet zelts un `classify` sūtīja pa 16, ielāde pa 1. Tāpēc (4) sliekšņi neder nevienam režīmam. Visur `JEV_CHUNK_SIZE = 1`; keša atslēgā pieprasījuma izmērs.
- Pārmērīts pa vienam (`pred_jev_1_14_single.csv`, `ATSKAITE.md` § Jev 1.14, viens dokuments pieprasījumā): `test` acc_doc 136/150 (paketēs 124/150). Tas pats dev likums dod 0,8: dev 71/77, `test` 119/130; ielādei max(likums, 0,9) = 0,9 (`test` 105/110).
- Likums stāv uz viena dokumenta robežas (atkārtojumā 0,75), izvēlēts stingrākais. Testi `test_cli_classify_then_review_list`, `test_chunk_size_is_in_cache_key` (mutācijas → krīt).

## 2026-10-22 (4) — Balsojumu tēmas: partijām slieksnis 0,7, ielādei 0,9, Jev piesaistīts `jev-1.14.0` (operators)
- Vēsturiskās partijas (plāna 9. uzd.) lieto 0,7 (`BATCH_CONFIDENCE_THRESHOLD`), ielāde paliek pie 0,9 (`INGEST_CONFIDENCE_THRESHOLD`); abi `src/saeima/topics.py`.
- Kāpēc: slieksnis der tikai tam modelim, uz kura mērīts, un tas pats dev likums `jev-1.14.0` dod 0,7 (`test` precizitāte 104/114, `ATSKAITE.md` § Jev 1.14 pārmērījums), bet ielādē, kur lēmumu neviens nepārskata, paliek stingrākais 0,9.
- `JEV_MODEL = "jev-1.14.0"` — ielāde un partijas to sūta līdz `system_one` (ne `jev-latest`), keša atslēgā tas pats modelis. Tests `test_ingest_sends_pinned_jev_model` (4 mutācijas → krīt); dzīvs zvans 2026-10-22 atbildēja ar `jev-1.14.0`.

## 2026-10-22 (3) — Balsojumu tēmas: Jev 1.14 pārmērījums, likumu tēmu sinhronizācija, partiju plāns
- Jev 1.14 uz tiem pašiem 253 dokumentiem (`pred_jev_1_14.csv`, `ATSKAITE.md` § Jev 1.14 pārmērījums): `test` acc_doc 124/150 (1.13 — 128/150). Pie 0,9 precizitāte 78/83, bet ar roku ~1 276 dokumentu (1.13 — ~909); dev likums dod 0,7 (`test` 104/114). Konstante kodā nav mainīta — izlemj operators.
- `saeima_bills.topic` no lēmumiem: `scripts/vote_topics.py bills-sync` (snapshot + pašpietiekams `data/rollback_bill_topics_<id>.sql`) → `bills-apply` (atsaka bez komitēta rollback vai pie drift) → `bills-rollback`. Ražošanā nav palaists.
- `plan --size 300` → `data/saeima_topic_gold/batches.csv` (no DB kopijas): 10 partijas, 2 715 dokumenti; 4 budžeta likumi (152/Lp14, 430/Lp14, 757/Lp14, 1130/Lp14; 836 balsojumi) izslēgti līdz operatora lēmumam (`backlog/saeima.md`). Testi `test_sync_bill_topics_from_decisions`, `test_plan_orders_by_impact_*` (6 mutācijas → krīt).

## 2026-10-22 (2) — Saeimas balsojumu tēmas ielādē: Jev, slieksnis 0,9 (operators)
- Izvēle pēc `data/saeima_topic_gold/ATSKAITE.md` (plāna 7. uzd.): Jev; `test` pusē pie 0,9 segums 103/150, precizitāte 95/103. Konstantes `INGEST_METHOD`, `INGEST_CONFIDENCE_THRESHOLD` — `src/saeima/topics.py`.
- `store_vote()` tēmu ņem no `saeima_document_topics` (`topic_for_new_vote`, viens Jev zvans dokumentam). Zem sliekšņa, Jev kļūme vai vairāku numuru motīvs → atslēgvārdu tēma, `review_status='pending'`, `logs` rinda `vote_topic_fallback`; klātbūtnes reģistrācija → «Saeimas darbs». `ATMINA_VOTE_TOPIC_CLASSIFIER=off` zvanu izslēdz (testos vienmēr).
- Tests `TestStoreVoteTopicDecision` (mutācija bez `pending` → 4 no 6 krīt). Slieksnis mērīts ar `jev-1.13.0`; dzīvais zvans DB kopijā 2026-10-22 atbildēja jau ar `jev-1.14.0`.

## 2026-10-22 — 35. kanoniskā tēma «Ekonomika un uzņēmējdarbība» (operators)
- Uzņēmējdarbības vide, eksports, jaunuzņēmumi, inovācijas, tūrisms un ēdināšana, patērētāju tiesības, preču atbilstība, konkurence, pasts. «Budžets un finanses» paliek budžets, vispārīgie nodokļi, finanšu sektors. Tūrisms nav atsevišķa tēma (4 gadījumi zelta kopā); «Novadi» nav — tas ir «Pašvaldības».
- Kods: 93c32822, f6a39ad8 (Saeimas motīvu kartē nākotnē → jaunā tēma 148 no 8 407 balsojumiem, `.scratch/t35_motif_map.py`). Esošās rindas DB NAV pārrakstītas; ekonomikas pozīciju pārskatīšana un T2 risks no aliasu maiņas — `backlog/saeima.md`.

## 2026-10-21 (9) — Stenogrammu pozīcijām `stated_at` = sēdes diena (operators)
- Atceļ (8) brīfa «`stated_at` = publicēšana» stenogrammām: ar to 15 8. oktobra runas nonāca 21.10. dienas pārskatā un «Aktīvāko politiķu» skaitļos (`@quality-reviewer` 2026-10-21). Turpmāk sēdes diena no stenogrammas galvenes, arī ārpus 7 dienu loga.
- Nesēji: `.claude/references/claim-extractor/datumi-dublikati.md` § `stated_at` 3. p., `wiki/operations/stale-sweep-brief.md` (d). Esošās 42 rindas (743302–743343) nav bīdītas.

## 2026-10-21 (8) — Vēstneša stenogrammu sweep: 55/55 pāri izskatīti, +42 pozīcijas
- 5 Opus @claim-extractor pēc `plan_stale_sweep.py --include-vestnesis` (44 stenogrammu + 11 citi pāri); stenogrammām papildbrīfs `docs/audits/2026-10-21-stale-sweep/brief-stenogrammas.md` (dala pēc runātāju rindām, sēdes diena stance tekstā, `stated_at` = publicēšana, dublikātu logs sēde→publicēšana).
- Vārti: `extracted_at` 55/55, `reviewed_at` 20/20, `claims` +42 = aģentu summa; 2 NEEDS_REVIEW izvērtēti (`data/rollback_review_sweep_2026-10-21.sql`). Atskaite `docs/audits/2026-10-21-stale-sweep/atskaite.md`.

## 2026-10-21 (7) — Stenogrammas runātājs = `subject` (operators; atceļ 2026-10-17 (4) «loma netiek mainīta»)
- `src.roles.enforce_subject_guards(..., platform=)`: uz `platform='vestnesis'` pārbaudīts runātājs («E. Jurēvics (JV).», `matcher.transcript_speaker_pids` — viens aktīvs īpašnieks) kļūst par `subject`, pirms relay pazemināšanas; visi rakstītāji padod `platform`. Tests `TestTranscriptSpeakerIsSubject` (krita pirms; 4 mutācijas krīt).
- Dati (`beacdfe6`, `data/rollback_speakers_subject_2026-10-21.sql`): +42 `subject` pāri 9 stenogrammās (41 no 10-17 sausās palaides + Kalējs, doks 129516), 0 apspiesti, visi `extracted_at IS NULL`. Rutīnas 2b solis Vēstnesi neņem — tos sasniedz tikai `scripts/plan_stale_sweep.py --include-vestnesis` (`stale_extraction_pairs()['vestnesis']` 13 → 55).
- NEaiztikts: 657 esoši runātāju pāri ar `mentioned` 30 stenogrammās — atsevišķs operatora lēmums (UPDATE uz `subject` ierakstītu 657 apspiešanas ar maldinošu `auto-demote`).

## 2026-10-21 (6) — Latvijas Banka (pid 243): Vēstneša izvēlne vairs nav saite
- `negative_patterns` = «Latvijas Banka
Noteikumi Informācija u.c.», «Latvijas Banka Latvijas Nacionālais arhīvs» (divas izvēlnes formas); 35 kļūdainas saites dzēstas (15 `mentioned`, 20 `subject`; 0 claims), 51 īstā paliek. pid 243 rindas 840 → 805, apspiešanas +35. Rollback `data/rollback_lb243_vestnesis_2026-10-21.sql`.
- `eval_matcher_collisions` pirms = pēc (fp 2, gold 3379/3441), mērīts uz kopijas ar pārliktu `DB_PATH` (rīka `--db` defekts — `backlog/repo-higiena.md`). Pieņemts risks: paraugs pārbauda VISU doku — lapa ar izvēlni UN īstu LB pieminējumu zaudētu saiti (šodien 0/35).

## 2026-10-21 (5) — VAD neskaidrie 5: 3 vārdabrāļi, 2 atvērti
- Dārznieks NBS (UR: cits dzimšanas datums), Hiršs NBS (17 g. stājoties dienestā), Ignatjevs policijā (amati/īpašumi pretrunā) — NEPIEDER; Āboliņš NBS 2010 un Ozoliņš BKSB 2009–2010 — nepietiek pierādījumu (`backlog/vad.md`). DB nemainās — rindas nekad nav ielādētas.

## 2026-10-21 (4) — Datums ar gadu: «2026. gada 17. oktobrī» (operators)
- `lv_date_locative(with_year=True)` — vienīgais avots (pretrunu un «Atradumu» OG kartītes); «17. oktobrī, 2026» bija kalks. Tests `test_lv_card_date_labels` (krita pirms). 8/29 pretrunu kartītes pārzīmētas (`a0909422`). Pretrunu attēliem nav `?v=` — X/FB var rādīt veco (`backlog/vietne-ui.md`).

## 2026-10-21 (3) — Saites lapa + profila Saites cilne: plakans saraksts ar veida malu
- Operators: pelēkbēšās kartītes kastē «nav foršas». Pāris tagad = rinda bez fona; kreisā mala = jaunākās saiknes veids (`data-tone` no `TENSION_LINK_CLASS`), zem vārdiem tās `description` (2 rindas), skaits vairs nav lielākais elements. Tikai `links.py` +2 lauki, veidne, esošie `.saites-pair*` stili (good-css).
- Tests `test_default_view_is_readable_without_graph` pārbauda aprakstu un toni (krita pirms labojuma); `render_baseline_graph.json` pārģenerēts (citi baseline nemainījās).
- Profila cilne «Saites»: tās pašas kartītes (veida mala, bez bēšās kastes, tēma kā mazs virsrakstiņš); 3 vienādas kopijas → makro `tension_card` (`politician.html.j2` −22 rindas, inline stili ārā). `render_baseline_politicians.json` pārģenerēts — veidnes diff skar tikai kartītes.

## 2026-10-21 (2) — Rezerves kopija vairs neiesprūst; check.sh iesprūšanas cēloņi
- Iesprūdis `gpg-agent` (kopš 10-17, neatbildēja `gpg-connect-agent`) iesaldēja `scripts/backup_db.py` `zstd | gpg` caurules — arī īsto iknedēļas kopiju — un ar to `test_backup_db` visu pytest. Tagad katram posmam limits `BACKUP_PIPE_TIMEOUT_S` (noklusējums 1800 s; mērīts uz 2,95 GB kopijas: 19 s / 8 s), pēc tam abi procesi nogalināti un LV kļūda; nepilnīga kopija nekad netiek augšupielādēta un neskaitās retencijā (`760c1f9c`, `d8982886`).
- Otrs cēlonis (mašīnas, ne koda) — ATRASTS: Windows TCP dinamisko portu diapazons bija nomainīts uz 3000–11999 (9 000; daļa vēl Hyper-V/WSL izslēgta, noklusējums 49152 + 16 384). Pārlūka testi to izsmeļ → `connect` saņem WSAEADDRINUSE (10048), bet Python `socket._fallback_socketpair` kļūdu ignorē un `accept()` gaida mūžīgi (arī `asyncio.run` ražošanā). Operators atjaunoja noklusējumu (`netsh int ipv4|ipv6 set dynamicport tcp start=49152 num=16384`) → 20 000× `socketpair()` tīrs (pirms: iesprūda pie 36–7 633). NordVPN/Npcap nav vainīgi. [commands.md](operations/commands.md) § check.sh iesprūst.

## 2026-10-21 (1) — good-css 5. kārta: visas atlikušās lapas + kopīgie elementi vienuviet
- Lasītājam: partiju balsojumu tabula ietilpst telefonā (bija 3 325 px), `#pretruna-N` un balsojumu dienas galvene zem nav, X garš tēmturis vairs neizstiepj lapu, tukšie filtri saka «Nekas neatbilst…» ar skaitītāju, iesaldētās analīzes tumšajā, statistikas 4. kolonna, tumšais `--text-dim` #7e849a (≥4,5:1; bija 2,96), partiju/mediju kartītes = īstas saites (dzēsts `data-card-href` apdarinātājs), ≥44 px mērķi telefonā (balsojumi 998 → 0), redzamie datumi visur `16.10.2026` (operators 10-21; `<time datetime>` ISO), «Kopēt saiti», `:target` izcēlums (JS pulss dzēsts), «Saturs» garajām analīzēm.
- Vienuviet: `--mono`/`--sans`/`--tap-target` saknē, 66 miruši noteikumi dzēsti (`docs/audits/2026-10-21-good-css-5/dead-css-manifest.txt`), makro `prv2_card`/`multi_select`/`share_buttons`, Likumi uz `msv1.js`. **Noteikumi:** `lv_date` (`src/render/_common/dates.py`) ir vienīgais datuma formatētājs; `multi_select` id jābeidzas ar `-select` (citādi renders krīt); `window.atminaFold`/`atminaLvDate`/`atminaFmtN`/`atminaShowCount` dzīvo `sgv1.js` (`defer`) — lietotājs ielādējas pēc tā vai sauc pēc `DOMContentLoaded`.
- Auditi + Astra recenzija + plāns: `docs/audits/2026-10-21-good-css-5/`, `docs/plans/archive/2026-10-21-good-css-5-karta.md`; katrs no 6 uzdevumiem ar neatkarīgu recenziju. Atlikums un operatora jautājumi: `backlog/vietne-ui.md` § good-css 5. kārtas atlikums.

## 2026-10-20 (11) — Ārējā drošības testa triāža
- 7 atradumi → 1 operatora paneļa solis (Minimum TLS = 1.2 — izpildīts tajā pašā dienā; `openssl s_client` 8/8: 1.0/1.1 atteikti, 1.2/1.3 strādā), DMARC 2. solis (`p=quarantine`) izpildīts tajā pašā dienā pēc 3 Google atskaitēm (pašu hosts 8/8 pass), 5 bez darbības. Pilnā tabula: `wiki/operations/cloudflare-security.md` § 7.
- „WAF neaktīvs" = Free plāna pārpratums (pilnais Managed/OWASP ruleset ir Pro+). HSTS `includeSubDomains`/`preload` noraidīts: `webmail.` 443 rāda sertifikātu ar citu vārdu.
- Pārbaudīja Codex (Astra) un advisor. Testa fails `/.well-known/security-test.txt` izdzēsts no koka; dzīvē pazudīs ar nākamo deploy.

## 2026-10-20 (10) — Iesaldētās lapas: dzīvā ?v=, fnv1.js; politiķa profils: good-css 4. kārta
- 15 `curated/` lapas (statistika + 10, finanses, 3 analīzes) nesa `?v=1`/senu mtime → `_sync_curated_chrome` ieraksta dzīvo versiju. `assets/fnv1.js` (finanšu filtrs) atjaunots — 2026-09-05 dzēsts kā bārenis, bet `finanses.html` to lieto (dzīvais tikai no vecā `output/`); sargs `test_curated_pages_reference_only_assets_in_repo`.
- Profils 390 px: 551 atsevišķos mērķos <44 px 436 → 1 (4 profili × visas cilnes; `::after` vai `min-height`, tikai ≤600 px); saišu kartītes galvene vairs nelūst «2026-10-/05» (`.saites-card-head`); deklarāciju aktīvais gads tumšajā 2,56:1 → 7,36:1. Tests `test_phone_profile_links_are_tappable_and_saites_header_fits` (bija sarkans: 17 px).
- Profila selektoros hover ārpus vaicājuma 35 → 0, fiziskās īpašības 60 → 0, josla `top: var(--nav-block-size)`; visā failā hover 155 → 123. Pretrunas/saites/tēma pārbaudītas (pikseļos nemainītas, tēmā dalīšanās pogas 44 px). Plāns `docs/plans/archive/2026-10-20-good-css-4-karta-profils.md`.
- Telefonā cilņu josla izbalē tikai tajā malā, aiz kuras vēl ir cilnes (`animation-timeline: scroll(self inline)` + `mask-image`, bez JS; Firefox bez izbalēšanas); tests `test_phone_tab_bar_fades_only_toward_hidden_tabs`. Chromium patur pēdējo vērtību, ja josla tajā pašā lapā no pārplūdes kļūst ietilpstoša (tikai loga maiņa). Pilns render + deploy 5c9a0966, verify_host 9/9.

## 2026-10-20 (9) — Galvenā izvēlne planšetē: viena rinda vai izvēlnes poga
- 769–1149 px saites aplauzās 2–3 rindās (nav 117–196 px). Tagad izvēlnes poga līdz 960 px (bija 768); 961–1200 px saišu atstarpes, `.nav .container` gap un meklētāja platums saspiežas ar `clamp()` (pilns izmērs vienā rindā prasa 1148 px).
- Mērīts 7 lapas × 13 platumi (390–1440): 91/91 nav ≤ 69 px, lapa nav platāka par ekrānu. Tests `tests/test_nav_tablet.py` (bija sarkans: 800 px → 196 px).
- `--nav-block-size` + `chrome-v1.js` ResizeObserver paliek (izvēlnes pogas režīmā nav 69 px). `--slv-sticky-top: 64px` joprojām otrs tokens — atstāts. Pilns render + deploy 4a5eb087, verify_host 9/9.

## 2026-10-20 (8) — Pozīciju lapa: good-css 3. kārta
- Galvene «Kopā» rēķināta no tā paša filtrētā saraksta kā tabula (`_fetch_pozicijas_metrics(claims)`; bija 9 852 pret 9 801 — galvene skaitīja `inactive` un mediju kontus); skaitļi ar tūkstošu atstarpi; lapošana «← Iepriekšējā / Nākamā →»; ievada teikums (kas ir pozīcija, ko nozīmē ticamība).
- Lipīgā filtru josla `inset-block-start: var(--nav-block-size)` (bija zem nav: aside 0 pret nav 57 px); `chrome-v1.js` ResizeObserver raksta izmērīto, jo 901–1149 px nav ir 2–3 rindas (mērīts 1280/1024/960 → 57/117/177 = aside top). Telefonā kārtošanas josla kā Personām, pieskāriena mērķi ≥44 px.
- Noteikumi: hover media vaicājumā, `:active`, kustība tikai `no-preference`, rindas hover mala CSS (`--party-color`, bez JS klausītājiem), `#0b0d14` → `var(--bg)`, loģiskās īpašības. srgb partiju/tēmu mix apzināti NEmainīts (sk. (7)).
- Testi: `test_counts_and_percentage` (+inactive/media, bija sarkans 6≠4), `test_pozicijas_phone_layout_in_browser`. Plāns `docs/plans/archive/2026-10-20-good-css-3-karta-pozicijas.md`. Pilns render + deploy c70028da, verify_host 9/9.

## 2026-10-20 (7) — good-css 2. kārta: kopīgie stila noteikumi
- Redzamie: `.muted` noteikums (piezīmes bija pamatteksta krāsā — mediji, medijs, likumprojekti); ķeksis `color: var(--bg)` (tumšajā bija 2,6:1); `.multi-select-trigger` 44 px (arī pretrunas, spriedzes, ziņas); tēmu izvēlne likumi/likumprojekti `min(100%, 22rem)` (telefonā pilna, datorā 220 → 352 px).
- Noteikumi: `:hover` media vaicājumā (`a:hover` visā vietnē), `:active`, kustība tikai `prefers-reduced-motion: no-preference`, `--transition` `ease-out`, 7× `outline: none` → `2px solid transparent`, režģis `minmax(min(100%, 20rem), 1fr)` bez 768 px noteikuma, loģiskās īpašības, `.pagehead-h1` `overflow-wrap`.
- Tintes un gaišās tēmas badge hex → oklch ar TIEM PAŠIEM toņiem: `color-mix` ar tēmas `--green/--yellow` gaišajā režīmā tos padarīja duļķainus. Mērīts 15 lapas × 390/1280 × gaišs/tumšs: kartītes pikseļos nemainītas. check.sh zaļš; pilns render (1196 lapas jauns `?v=`), deploy 3b06d2f3, verify_host 9/9.
- Nav darīts: multi-select uz `popover`, balsojumu 42 px trigeris (sava ID pārrakstīšana), 15 standalone lapu fiksētais `?v=`.

## 2026-10-20 (6) — Likumu/likumprojektu lapas: good-css 1. kārta
- Posmu atzīmes: veidne salīdzina `stage_result|lower` (Pieņemts/Likums/Paziņojums zaļš, Noraidīts sarkans) — iepriekš visas pelēkas. Laika līnija: punkts uz līnijas, datums savā kolonnā (grid), tabular-nums, ≥44 px pieskāriena zona saitēm (`::after`), mazāk tukšuma virs kopsavilkuma (`:has()`), meklēšana savā rindā.
- Likuma lapas tabula: `_label_table_cells()` (telefonā kartītes ar etiķetēm), galvene «Nr.», posmu etiķetes kā likumprojekta lapā; wiki/laws 25 faili pārģenerēti caur `_render_law_bills_block`. Mērīts 390/1280 px: pārplūde 0, 84/84 šūnas ar etiķeti.
- `likumi.html` pēc likumprojektu lapas parauga (operatora lūgums): ievads, meklēšana savā rindā, filtrs «Ar/Bez likumprojektiem» (`aria-pressed`), «Rāda N no M», kartītes header/body/footer ar `lv_plural` un `lv_date`; tests `test_likumi_filters_in_browser` (Playwright, pierādīts sarkans).
- 2. kārta — sk. (7).

## 2026-10-20 (5) — «Atradumu» papildinājumi: Tocs, Višvanati
- `vad-izmeklesana-2026`: Toca sadaļā UR ieraksts — «Latvijas Drošības biznesa asociācijas» valdē kopš 2025-12-12 (tas pats maskētais personas kods kā 5 uzņēmumos; agrākie sastāvi atvērtajos datos nav). Avots `docs/audits/2026-10-20-tocs-turpinajums.md`.
- `visvanati-pilsoniba-2026`: Višvanatas atbilde sadaļā «Zinātniskais profils» (mājaslapas teksts tagad pagātnē ar datumu 17.10.) + sadaļa «Pēc publikācijas» (komisija, Valsts policija, Kūtris ar atrunu, NA, Melnalksnis, Kalviņš abas puses, Satversmes 75. p.); avoti LSM 19.10., LETA 19.10.
- Pilsonības piešķiršanas izpēte → `docs/drafts/pilsoniba-2026/` (ārpus publiskā spoguļa), 4 labojumi pēc pārbaudes; nākamā daļa `backlog/saeima.md` [BLOKĒTS] līdz 15.10. stenogrammai.

## 2026-10-20 (4) — Likumprojektu lapu labojumi + atlikušie «Likums» balsojumi
- 1019/Lp14 un 1142/Lp14: galīgais otrreizējās caurlūkošanas balsojums bija DB bez numura motīvā (183, 7 — titania lapa to nenes) → posms caur `append_bill_stage()` + `document_nr` ierakstīts; `/saeima-ingest` a3 tagad apstājas pie kaila otrreizējās caurlūkošanas motīva; 1019 tagad `pieņemts` kā titanijā (ielāde nav vajadzīga). 1064, 1066, 1485/Lp14 rindas izveidotas (`upsert_bill`, datumi = balsojumu laiki) + 17 balsojumi. `SELECT … WHERE result='Likums' AND bill_id IS NULL` → 0. Rollback `data/rollback_{otrreizeja_1019_1142,create_bills_1064_1066_1485,link_unbound_votes}_2026-10-20*.sql`.
- Titania saite no `document_nr` (`bill_document_url()`), ne no balsojuma — trūka 87 lapām, 1056/Lm14 rādīja Lp dokumentu. «P» = «Pieprasījums». Agendas parsētājs atsoļo `\"` (14 nosaukumi salaboti, rollback `…bill_title_quotes…`).
- 25 likumprojekti, ko šīrīta skrējieni pacēla saraksta augšā, atjaunoti uz iepriekšējo `last_updated_at` no to rollback failiem (`data/restore_last_updated_at_25_2026-10-20.sql`; `… LIKE '2026-10-20%'` → 0). `append_titania_decision_stages.py` arī `touch_updated_at=False`. 56/Lp14 un 1019/Lp14 kopsavilkumi/nosaukums aprakstīja termiņa pagarinājumu, ne likumu — pārrakstīti (Lp vaicājums `summary LIKE 'Termiņ%' OR …` → 1 + 56).

## 2026-10-20 (3) — 553 nepiesaistīti balsojumi + «otrreizēja caurlūkošana»
- `append_bill_stage(touch_updated_at=False)`: vēsturiska posma iepildīšana `last_updated_at` neceļ (pēc tā kārto `likumprojekti.html`); `link_unbound_votes_to_bills.py` to lieto vienmēr. Ielāde paliek `True`.
- Jauni posmi «otrreizēja caurlūkošana» (+ priekšlikums) — Valsts prezidenta atdots likums krita uz «nezināms»; galīgais «Pieņemts» = pieņemts. Noraidīts priekšlikums likumprojektu nenoraida. Testi `test_second_review_final_vote_and_rejected_amendment` + 2 klasifikācijas (mutācija pierādīta); pārrēķins pirms/pēc: 552 likumprojekti, mainās 0.
- Dati: 553/553 balsojumi (182 likumprojekti, ieskaitot 1019/Lp14) piesaistīti; statusi nemainījās nevienam, posms 5; `last_updated_at` kontrolsumma pirms=pēc. Vaicājums `backlog/saeima.md` → 0. Rollback `data/rollback_link_unbound_votes_2026-10-20b.sql`.
- `/saeima-ingest` vārti a3: nepiesaistīti balsojumi sēdes datumā → STOP.

## 2026-10-20 (2) — Lēmumu/pieprasījumu statusi + jauns statuss «atsaukts»
- «Paziņojums» ir Saeimas iznākuma vārds pieņemtam lēmumam (titania 1112/Lm14), ne parsētāja kļūda: `saeima_votes.result` nemainīts (08-18 lēmums), `derive_bill_denorm()` to lasa kā «pieņemts»; ne-Lp `procesuāls`/`paziņojuma_balsojums`/`nezināms` + Pieņemts = galīgs, `procesuāls` tikai ja motīvs nav darba kārtība/iekļaušana/nodošana komisijai. Iznākums «Atsaukts…» → `atsaukts`.
- `stage_kind='decision'` = Saeimas lēmums bez balsojuma (avots titania), raksta tikai `append_bill_stage(stage_kind=…)`; `scripts/append_titania_decision_stages.py`. UI: badge, filtrs, josla «Atsaukti», «Lēmums (bez balsojuma)».
- Dati: pārrēķins 31 + piesaiste 2 (990/Lm14, 135/P14) + lēmumi 5 + kopīgs balsojums 4 → 44 Lm/P14 = 37 pieņemts / 1 noraidīts / 3 atsaukts / 3 procesā, + 1525/Lp14 atsaukts (vaicājums: `current_status` tiem `document_nr`, kam `data/titania_bill_stages_2026-10-19.csv` `bill_type IN ('Lm14','P14') AND titania_status='Izskatīts'` → 44); `last_updated_at` mainījās 11. Rollback `data/rollback_lmp14_*_2026-10-20.sql`.
- Viens balsojums, divi dokumenti (operatora lēmums): 1056, 1118, 1133, 1134/Lm14 balsojums piesaistīts saistītajam Lp — `append_bill_stage(keep_vote_bill_id=True)` (`link_unbound_votes_to_bills.py --shared`) dod Lm posmu, `saeima_votes.bill_id` nemainās; atsaka, ja motīvā nav «(<nr>)».

## 2026-10-20 — Likumprojektu kopsavilkumi 2. kārta + nepiesaistīti balsojumi
- 2. kārta (pieņemts+noraidīts): 206/206 ierakstīti caur `set_bill_summary()` (174 PASS + 29 PASS pēc labojuma + 3 pēc otrā pārbaudītāja; 2 no tiem — pārbaudītāja paša teksts, atkārtoti nepārbaudīts). Visos 552 kopsavilkumos iznākuma paterns: 0. Rollback `data/rollback_bill_summaries_k2_2026-10-19.sql`.
- 15 «Izsludināts» likumi rādīja «procesā», jo galīgie balsojumi bija DB bez `bill_id` (ielāde izlaida `@saeima-tracker` Step 4). Jauns `scripts/link_unbound_votes_to_bills.py` (tikai `append_bill_stage()`, saraksts obligāts, plan-hash) + titania «Likums» + pārrēķins → 14 `pieņemts`; 1019/Lp14 apzināti atstāts. Kopā DB 601 šāds balsojums — operatora lēmums (`backlog/saeima.md`).
- `scripts/backfill_saeima_bills.py` izdzēsts (operators 2026-10-20) kopā ar 4 tā testiem: `upsert_bill(summary=…)` pārrakstītu kopsavilkumus; piesaistei — `link_unbound_votes_to_bills.py`.

## 2026-10-19 (6) — Likumprojektu kopsavilkumi: «par ko un ko maina», 1. kārta
- Kopsavilkums nes tikai saturu, ne balsojuma iznākumu/lasījumu: raksta tikai `src.saeima.set_bill_summary()` (atsaka iznākuma paternus, tukšu, daudzrindu; `last_updated_at` nemaina); tests `TestSetBillSummary`, pierādīts ar 2 mutācijām. Esošie 263: paterns atsaka 98 (vaicājums `docs/plans/2026-10-19-likumprojektu-kopsavilkumi.md`).
- 1. kārta `procesā`: 181/181 ierakstīti (160 pārbaudītājs PASS + 16 pēc labojuma PASS + 5 orķestratora labojumi pēc pārbaudītāja iebildumiem); avots — titania anotācija/teksts (PDF). Rollback `data/rollback_bill_summaries_k1_2026-10-19.sql`.
- Atradums: 88/181 «procesā» titanijā ir «Izsludināts» (51) vai «Izskatīts» (37) — `backlog/saeima.md` [FIX] statusa sinhronizācija.

## 2026-10-19 (5) — JSON blakusfaili bez `.br`/`.gz`
- Renderis raksta tikai `.json` (`_emit_json_compressed` → `_emit_json`, `src/render/_common/assets.py`): Cloudflare saspiež pats, `.htaccess` pārrakstīšanas vairs nav. Neviens `assets/*.js`/veidne `.br`/`.gz` URL neprasīja (grep). `.json` baiti nemainās.
- 14 veci `.json.br/.gz` izdzēsti no `output/atmina/` — pilnais deploy tos noņems no vietnes (citādi paliktu novecojis saturs). `verify_host.py` `json_compressed` pārbaude paliek: tā mēra Cloudflare `Content-Encoding`, ne failus.

## 2026-10-19 (4) — Publicēšanas vārti arī «Atradumu» lapām
- Operatora lūgums (BACKLOG 68): `deploy.sh` preflight atsaka, ja kokā ir `analizes/<slug>.html` bez `publish_approvals` rindas `analizes/<slug>` (`scripts/approve_publish.py analizes/<slug>`). Analīzei tikai atļauja — attēla zara nav.
- 9 jau publicētās analīzes iesētas kā apstiprinātas (visas HTTP 200 atmina.lv; `SELECT COUNT(*) FROM publish_approvals WHERE subject_key LIKE 'analizes/%'` → 9); rollback `data/rollback_publish_approvals_analizes_2026-10-19.sql`.
- Tests `tests/test_check_output.py::test_publish_gate_blocks_unapproved_analysis_until_approved` — bez labojuma krīt.

## 2026-10-19 (3) — Patreon kā atbalsta kanāls (atbalsts.atmina.lv)
- Operatora lēmums: atbalsts sedz izmaksas, **saturs paliek bez maksas visiem**; līmenis viens (3 €), nekādu priekšrocību, kas slēptu informāciju; atbalstītāji neietekmē tēmu vai politiķu izvēli. Discord/bots NEsolīts (plāns `docs/plans/2026-07-29-monetizacija-patreon-discord.md`).
- Domēns `atbalsts.atmina.lv` (CNAME + TXT Cloudflare; atmina.lv/www neskarti) — ieraksti un atsaukšana `docs/funding/patreon.md`. Patreon prasīja sakni atmina.lv — NEDRĪKST, tas aizstātu vietni.
- Vietnē saite: kājene (`templates/base.html.j2`), Kontakti 4. kartīte, Par mums sadaļa «Atbalsts». Piespraustais X pavediens 4/4 ved uz atbalstu (`docs/tweet_bank/2026-10-19-pinned-post.md`, postēts 2026-10-19).

## 2026-10-19 (2) — Vecais hostings: koda daļa ārā, `_headers` vienīgais galveņu avots
- Izņemti `assets/htaccess.template`, `scripts/audit_remote_tree.sh`, `wiki/operations/deploy-namecheap-arhivs.md` (dzēšanas nonāca paralēlās sesijas komitā `1d885295`); `_copy_host_config` vairs neraksta `.htaccess` (`.assetsignore` to joprojām izslēdz). Plāns `docs/superpowers/plans/archive/2026-10-19-cloudflare-task9-vecais-hostings.md`.
- Salīdzinājumu ar šablonu aizstāj `test_root_rule_carries_every_security_header` (5 nosaukumi; mutācija bez `X-Frame-Options` → krīt). Noplūdes vārti `test_no_deploy_credentials.py` sargā `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` (mutācija: ID izsekotā failā → krīt), jo `DEPLOY_*` pēc izņemšanas skipotu mūžīgi.
- `.br/.gz` koda komentāri «see htaccess» apzināti paliek — tas ir atsevišķais BACKLOG uzdevums (`.json.br/.gz` izņemšana).
- Noslēgts tajā pašā dienā: hostings anulēts, 14 DNS ieraksti izdzēsti (`nslookup` 1.1.1.1: 14/14 nav, pasta ieraksti paliek), `verify_host.py` 9/9 (BACKLOG 67).

## 2026-10-19 — Viens balsu skaitīšanas noteikums; jaunā salience tikai jaunām rindām; OG kartītē balss
- Nodots balsojums = `src/scope.py` (`CAST_BALLOTS`, `not_attendance_sql()`): profils, Personas, partijas lapa, pusloks, meklētājs un bio sargs to importē; fikstūras renders pirms = pēc (baitu identisks). Reitingi un sakritības metrikas `Nebalsoja` apzināti neskaita — vai vienādot, lemj operators (`backlog/saeima.md`); `current_term_vote_counts()` skaita arī klātbūtni, nekaitīgi («> 0»). Tests `tests/test_vote_count_single_rule.py`.
- `_vote_salience`: lasījuma zars pirms nodošanas, «Par nodošanu … komisijai» atpazīts (`test_salience_reads_real_reading_formats`). Tikai JAUNĀM `saeima_vote` rindām — glabātās nav pārrēķinātas: mainītos 183 296 no 685 769 (`docs/audits/2026-10-18-vote-salience/salience_denominator.py`); pārrēķins — operatora jautājums.
- OG kartīte «Vārdi pret darbiem»: balsojuma pusē politiķa balss, motīvs un kopskaits, ne likumprojekta apraksts (T20); balsi meklē balsojuma claim politiķim, jo partijas pretrunā tas nav pretrunas `opponent_id` (`tests/test_og_card_vote_side.py`). Formulējums «Balsoja «Par»: Par …» gaida operatoru (`backlog/vietne-ui.md`).
- `src.db.store_contradiction()` validē ar `Contradiction` modeli PIRMS INSERT (nederīgs `severity`/`salience`/`headline` → `ValueError`, 0 rindu) un pieņem `party_id`; `confirmed` paliek 0 (eskalācija 3). Tests `tests/test_store_contradiction_db_layer.py`.

## 2026-10-18 — Saites lapa sākas no partijas/politiķa; pilnais tīkls pēc pogas
- Spec/plāns `docs/superpowers/specs/2026-10-18-saites-redizains-design.md`, `docs/superpowers/plans/archive/2026-10-18-saites-redizains.md`; vārts T18 `docs/audits/2026-10-18-kulbergs-saites-paraugs.md` (10/10). Pele NEizmanto (ego-tīkls jau ir profila Saites cilnē).
- `saites.html` 1 217 522 → ~245 000 B; D3 + `data/saites-graph.json` tikai pēc pogas; tabula → `spriedzes.html`, kas lasa `?type&party&person`, partija = autors VAI adresāts.
- Pāra saite → profils, kur kartīte redzama (prod 282 enkuri, 0 bez elementa, 6 pāri → `#saites`); pogas tikai tipiem ar saitēm (Balsojumi 0 — 9 034 pāri, neviens virs sliekšņa).
- Wiki: grafa filtrs bez operations/CHANGELOG; tēmu `top_politicians` → wikilinki (lint 628 lapas, 0 salauztu). Pārbaudīja: 3 e2e faili + Astra 2. kārta (8/10, 3. labots, 7. noraidīts).

## 2026-10-17 (5) — Likumprojektu iesniedzēji tikai precīzi; parsētāja aste nogriezta
- `match_submitters_to_politicians()` lieto `_exact_match` (kā balsojumi, (3)); kails uzvārds vai neizsekots vārdabrālis → `unmatched`. Tests `test_namesake_and_bare_surname_stay_unmatched`.
- Vaļīgā atkāpe maskēja parsētāja defektu: pēdējais iesniedzējs nesa asti «DKP izskatīšanas gaita" [ref=…]» vai `" [ref=…]`; `_parse_individual_submitters` to nogriež (tests `test_last_submitter_drops_dkp_link_text`, mutācija krīt).
- Vārti (`.scratch/_gate_submitters.py`, 169 snapshot faili, 115 vārdi): vecais = jaunais 115/115. Klātbūtnes rinda «Skujiņa Zane» 2022-11-01 → pid 133 (`data/fix_skujina_vote_link_2026-10-17.sql` + rollback); NULL paliek 1 (Tretjakova, neizsekota).

## 2026-10-17 (4) — Vēstneša filtrs patur stenogrammas runātāju «E. Jurēvics (JV).»
- `_filter_vestnesis_strict()` pieņem arī runātāja rindu (`src.vestnesis.extract_transcript_speakers`), ja (iniciālis, uzvārds) pieder TIEŠI vienam izsekotam politiķim un tas nav `inactive`; loma netiek mainīta (`src.roles` vienīgais lemj `subject`). Doc 135704 pazaudēja 5 runātājus. Tests `test_vestnesis_strict_filter_keeps_transcript_speaker` (3 mutācijas krīt).
- Rinda der tikai stenogrammā (rinda «Sēdes vadītāj…») ar frakcijas/amata etiķeti («A. Bērziņš (SIA Test).» — nē); vairāki iniciāļi («D. M. Daugavietis») sakrīt pēc pirmā (Astra 2. kārta). Sausā palaide (DB kopija, `.scratch/_tirisana_dryrun_speakers.py`): 30 stenogrammas, +217 saites pret veco filtru, no tām 176 jau junction, **41 jauna** (visas `mentioned`, 0 apspiestas); etiķešu/konteksta vārti 3038 Vēstneša dokos nomet 0 no 821 runātāja atslēgām. Izlaistas: «E. Zivtiņš» (153/279, 20×); neaktīvie Brante, Dzintars, Jātnieks.
- `eval_matcher_collisions.py` pirms = pēc: fp_links 2/43, gold 3324/3386, fidelity 943/0 (šo ceļu eval gandrīz nemēra — mērs ir sausā palaide). Pārsaistīšana nav palaista.

## 2026-10-17 (3) — Balsojumu vārdi tikai precīzi; nesaskaņotie redzami `unmatched_deputies`
- `match_deputies_to_politicians()` apakšvirkņu atkāpe (pirmais trāpījums uzvar) dzēsta: neizsekots «Bērziņš Kārlis» saņēma Andra Bērziņa balsis un pozīcijas (T1). Tagad `src.saeima.votes._exact_match` (kopīgs ar `activity.py`) + 3 vārdu rotācijas, divdomīgs → None. Īstā problēma nebija «Uzvārds Vārds» secība (HANDOFF-2026-10-17 p. 12) — to kods jau apstrādāja.
- Nesaskaņotie: `process_vote_snapshot()["unmatched_deputies"]`, `ingest_saeima_missing_votes.py` kopsavilkums, p3 skriptu žurnāls; `/saeima-ingest` vārti b. Tests `TestDeputyNameMatchingIsExact` (krīt, atjaunojot atkāpi).
- Vārti pret prod DB (`mode=ro`, `.scratch/_tirisana_gate_votes.py`): 272/273 (vārds, pid) pāri nemainās; 4 atkāpes pāri atgūti ar rotāciju; «Edvīns Šņore» (pid 7, 101 rinda) → None. Operators: pareizi «Šnore», «ņ» ir Saeimas kļūda 03-26…04-16 — variantu nepievieno (esošās rindas paliek pid 7, jaunie ieraksti ar «n»).

## 2026-10-17 (2) — VAD jaunie deputāti: agrāko amatu deklarācijas tikai pēc identitātes pārbaudes
- 13 deputāti bez VAD rindām (10-05 kohorta + Plaude/Morozs): Saeimas deklarāciju vēl nav nevienam; `vad_disambig` tikai ar Saeimas iestādi aizsedza agrāko amatu rindas (dry-run rāda `rows_found=0`, kaut Ozoliņam 185 atrastas). Triāža 3 Opus palīgi + Astra neatkarīgi (`docs/audits/2026-10-17-vad-jaunie/`).
- Ielādētas 37/37: Kotāns VID 9, Āboliņš NEPLP 10, Plaude VID 18 (`ingest --pids 266,296,301`, `id>4565`); 2836 → 2873 (`SELECT COUNT(*) FROM vad_declarations`). `vad_disambig` papildināts ar iestādi; Plaudei/Morozam ielikti Saeimas hinti kā kohortai. Rollback `data/rollback_vad_jaunie_2026-10-17.sql`.
- Pārējiem 10 nekas: vārdabrāļi vai neskaidri (Ignatjevs, Dārznieks NBS, Hiršs — cilvēkam). Saeimas «stājoties amatā» deklarācijas vēl jāgaida → atkārtot dry-run visiem 13.

## 2026-10-17 (1) — «Atradumi»: pirmais publicēts; OG kartīte ar zīmogiem; baseline no fiksētas kopijas
- Atradums = `content/analizes/*.md` ar `kind: atradums`; vārti (atruna «Ko mēs neapgalvojam», ≥2 ārēji avoti, `lint_analysis.py`) aptur renderu. Plāns `docs/superpowers/plans/2026-10-16-atradumi-sadala.md`. Pirmais: `visvanati-pilsoniba-2026` (deploy 8310def2, verify_host 9/9).
- OG kartīte `assets/og/atradumi/<slug>.png` sepijas stilā; neobligāts frontmatter `og:` (2 zīmogi + starplaiks + ≤2 skaitļi) kā pretrunu kartītē, nepilns bloks = STOP. `og:image` nes `?v=<hash>` — X kešo pēc URL. Tests `test_atradumi.py` (16).
- `test_render_chars.py` lasīja dzīvo `content/analizes` → katrs jauns atradums lauza 5 baseline bez koda izmaiņām. Tagad `tests/fixtures/content/analizes` (kā `fixtures/laws`); ar atradumu kopijā 5 krīt, bez tā 28/28.

## 2026-10-16 (7) — Matrica izņemta; saraksts pats atver #vote-; kvadrātiņš rāda deputātu
- Saraksts atver jebkuru `#vote-N` (sēdes diena + lapošana), Matricas atkāpe dzēsta. Saišu audits pret build: 961/961 HTML mērķi atrasti pārlūkā (197 pirmajā renderā, 764 caur dienu), + 8 `sav1.js` mērķi; 566 `sav1.js` klātbūtnes mērķi → «nav atrasts» (esoša neatbilstība, BACKLOG). Skripti `docs/audits/2026-10-16-matrica-likumprojekti/{audit_vote_links,audit_paging,gate_fr}.py`, Astras skripts `astra-plans-matrica.md`. Esošs defekts labots: novēlota recent atbilde pazemināja pilno arhīvu (`loadInto`).
- Matrica izņemta: `bmv1.js` 1630 → 823 rindas, `style.css` −498; `?tab=matrix` → saraksts. `balsojumi.html` 117 882 B. JSON paliek (saraksta avots; ar `fr`/`pp` recent 3 394 876 B / br 264 906, pilnais 9 045 193 / br 625 832 — `stat` pēc pilnā rendera, audita bāze 3,39 MB / 264 KB); virtualizācijas BACKLOG punkts slēgts.
- Deputātu saraksts: frakcija PIE BALSOJUMA (`fr`; `(fr, balss)` == frakciju joslas 7829/7829 + 2788/2788, `gate_fr.py` tajā pašā mapē), agrāk jaunākā; profila saite tikai 122 publiskajiem (17 neaktīvajiem agrāk 404). Kārtošana «Pēc vārda/frakcijas/balss», `Intl.Collator("lv")` («Ā» pie A).
- Kvadrātiņš zālē/frakcijas joslā → lodziņš «Vārds · frakcija · balss» (good-css: `position-area` iekš `@supports`, hover tikai `(hover: hover)`). Testi `test_balsojumi_vote_deeplink.py`, `test_balsojumi_seats.py` (mutācijas m1–m7 krīt). Recenzijas `docs/audits/2026-10-16-matrica-likumprojekti/astra-plans-{matrica,task2b}.md`.

## 2026-10-16 (6) — Likumprojekti savā lapā; sadaļa «Likumi»
- Paslēptā cilne bija 77 % no `balsojumi.html` (433 934 no 565 921 B, audita `kritika.md`) → sava lapa `likumprojekti.html` (552 = `COUNT(*) saeima_bills`); `balsojumi.html` tagad 119 KB. Josla «Pamatlikumi | Likumprojekti» abās lapās.
- «Kur likumprojekti ir tagad» = pašreizējais posms, ne piltuve (dati kopš 27.04.2026; 67 Lp ar 3. bez 1. lasījuma). Steidzamie (2. las. + pieņemts) = «Kļuvuši par likumu». 21/59/93/146/61/19 = 399 Lp14 (pogas pret `saeima_bills`).
- `?tab=bills` → `likumprojekti.html` (JS). «Kvoruma pārbaude» izslēgta kā klātbūtne (kā reģistrācija 2026-07-17): 7836 → 7829 balsojumu, profila skaits = `?deputats=` skaits.
- Testi `test_likumprojekti_page.py`, `test_bill_stage_bucket.py`, `test_votes_registration_filter.py`. Audits `docs/audits/2026-10-16-matrica-likumprojekti/`.

## 2026-10-16 (5) — Balsojuma kartīte: koalīcija balsojuma brīdī
- Kartīte grupēja frakcijas pēc ŠODIENAS `coalition_status` (Siliņas laikā PRO «opozīcijā», AS «koalīcijā»); pēc 15. Saeimas sanākšanas pārkrāsotos visas 14. Saeimas kartītes. Tagad `coalition_periods` + `src.coalition.coalition_at()`, JSON `coalitions` + `v.co`; (2) makets «šodienas statuss» ar to aizstāts.
- Sēkla `scripts/seed_coalition_periods.py --apply` 2026-10-16: 3 rindas no uzticības balsojumiem 5623/4411/5754 (frakcijas vairākums Par); rollback `data/rollback_coalition_periods_2026-10-16.sql`. 101 balsojums pirms 2022-12-14 16:42 → «Frakcijas» bez dalījuma (`co` skaits no renderētā JSON).
- Jaunai valdībai — sēklu palaid vēlreiz; audit 24 brīdina. Termiņa vidus iziešana sēklai neredzama → roku rinda + rollback. Matricas «pēdējā frakcija» apzināti nemainīta.
- Testi: `test_balsojumi_coalition_at_vote.py` (mutācija ar veco `csMap()` krīt), `test_render_votes_matrix_json.py` (4), `test_seed_coalition_periods.py`, audit 24.

## 2026-10-16 (4) — Balsojumu meklēšana bez garumzīmēm, filtri URL adresē
- Meklētājs salīdzina tekstu bez garumzīmēm abās pusēs («izglitiba» = «Izglītība»), `bmv1.js::foldText`. Tests: `test_search_ignores_diacritics_on_both_sides`.
- Filtri adresē: `?q=…&tema=…&deputats=…&menesis=…&sede=…&dalitie=1` (atkārtots parametrs = vairākas vērtības) — **publisks līgums, nosaukumus nemainīt**. `replaceState`, ne `pushState` (taustiņi nekļūst par vēstures soļiem), tāpēc `popstate` nav vajadzīgs — nepievieno. Neesoša vērtība → noklusējums, nekad «0 balsojumu». Tests: `tests/test_balsojumi_url_filters.py` (mutācija: bez vērtību pārbaudes krīt).

## 2026-10-16 (3) — Balsojuma kartīte pārveidota: 100 sēdvietu josla, frakcijas pa koalīcijai/opozīcijai
- Operatora apstiprināts makets (`.scratch/balsojumi_redesign/mock/`): serif virsraksts, iznākuma rinda ar par/pret/atturas/nebalsoja, 100 sēdvietu josla, frakciju rindas zem «Koalīcija»/«Opozīcija»/«Ārpus frakcijām» (statuss — šodienas `coalition_status`, kā agrāk), «dalīti» no `factionIsSplit`, poga «Kā balsoja katrs deputāts (N)». Meklētājs pirmais ar ikonu, vienāda augstuma filtru pogas, «Tikai dalītie» aktīvais stāvoklis. Leģenda — sēdvietu krāsas, Atturas teikums nemainīts.
- Paritāte pret dzīvo lapu pirms izmaiņām (200 kartītes): saites 0, frakciju `title` 0, kopskaitļi 0, deputātu rindas 0, datums+laiks 0 neatbilstību. DOM 58 132 (115 563 sākotnēji, 15 677 pēc 1. laidiena — sēdvietu kvadrātiņu dēļ).

## 2026-10-16 (2) — Balsojumi cilne, 1. laidiens: tas pats saturs, labāks attēlojums
- Izsekoto politiķu saraksts kartītē tiek uzbūvēts tikai atverot (atslēga `vid`, jo recent/full šardu indeksi nesakrīt); DOM sākumā 115 563 → 15 677. Paritāte pret dzīvo lapu: 200/200 kartīšu teksts, `title` un saites identiski (ar atvērtiem sarakstiem).
- Izvēlētā deputāta balss katrā kartītē; bez ieraksta — «nav individuālā ieraksta», nekad «nepiedalījās». Iznākuma mala: zaļa tikai Pieņemts, sarkana tikai Noraidīts, citādi neitrāla. Mobilajā (≤600 px) meklētājs pirmais, izvēlnes 2×2, datums virs motīva. `#votes-archive-info` `aria-live`.
- Labots esošs defekts: `?deputats=` lapa rādīja 400 kartītes (nefiltrētā sākuma ielāde pievienojās filtrētajai) — paaudzes skaitītājs `blv1.js`. Plāns `docs/superpowers/plans/archive/2026-10-16-balsojumi-1-laidiens.md`.
- Telefonā (≤600 px, tikai šai lapai, `pagehead--balsojumi`) galvenes 5 skaitļi vienā kompaktā rindā; pirmā kartīte 849 → 741 px (operators 2026-10-16).

## 2026-10-16 (1) — Atrunu vārti `save_analysis`: `qualifier_dropped`
- Jauna pozīcija, kuras `support` satur «ja», «varētu», «iespējams», «šķiet», «izskatās», «daļa» (locījumi, «daļēji») vai «īsti», bet stance — ne → `failures` ieraksts `qualifier_dropped` (tikai ziņo, glabāšanu nebloķē). Mērķis — Šnores klase (izmests nosacījums). `src/support.py::dropped_qualifiers`, `tests/test_qualifier_gate.py` (mutācija: bez izsaukuma e2e tests krīt).
- Atkārtota saglabāšana stance nemaina (first-write-wins), tāpēc aģents nosauc `claim_id` + `qualifiers`, stance labo orķestrators (`claim-extractor.md` § 5, `glabasana.md`).
- Viltus trauksmju mērījums (prod tikai lasot, 200 pozīcijas 737764–738070 ar atgūtu `support`): 17/200 (8,5 %), «ja» 11; izlasot — īsti trāpījumi ~1–3, pārējie: atruna citā fragmentā, frāze, jautājums. Vakara rutīnā izmēģina; ja troksnis traucē, sašaurināt uz pirmo fragmentu.

## 2026-10-15 (6) — Vakara rutīna: pirmais 3. solis ar `hunt_scope`, `@stance-checker` izmēģinājums, Saeima 15.10.
- Ingest 5/5; ekstrakcija 172/172 pāri (21 aģents, 3 kārtas) + atgūšana 15 pāri → 58 pozīcijas (738013–738070). 2c: 9/10 NEEDS_REVIEW izvērtētas ar advisor, 738036 operatoram (`rollback_nr_rutina_2026-10-15.sql`, stance 738054/738061 `rollback_stance_2026-10-15_rutina.sql`).
- `@stance-checker` (Opus) un Astra neatkarīgi 58/58: abi 57 D_OK; tās pašas dienas rīta izlasē 8/40 defektu → T16 risks, pirms pastāvīga soļa operators izlasa ~10. 3. solis: 8 hunteri, 38/38 balsotāji, 0 pretrunu, 65 noraidīti; papildu pāreja pret 15.10. balsojumiem 30 pāri, 0.
- Saeima 15.10.: 60/60 balsojumi (8465–8524), 5035 claims, summary 58/58, paritāte ar roku 60/60; `KNOWN_INSTITUTIONAL_SUBMITTERS` + Pilsonības, migrācijas un sabiedrības saliedētības komisija. Spriedzes #526–#531, piezīmes #714/#715.
- Pārskats #716 + QR § H 13 labojumi, 6 stance (`rollback_brief_notes_qr_2026-10-15.sql`, `rollback_stance_2026-10-15_qr.sql`), Grasbergs role (`rollback_role_grasbergs_2026-10-15.sql`). Attēls #383. Deploy 2cafd85d, verify_host 9/9, attēli 12/12 → 200.
- Operators 10-16: 738036 pārrakstīts bez referenta (Izvērtēts), Krusts (45) → Bezpartejisks; 3 kopsavilkumu žargons (FAME, MiCA, 1370/Lp14 teikums) — 9 balsojumi, 1 likumprojekts, 747 claims (`rollback_operatora_lemumi_2026-10-15.sql`, `rollback_stance_2026-10-15_op.sql`). Deploy b184fcb5, verify_host 9/9.

## 2026-10-15 (5) — Mūsu vērtējums no balsojuma teksta; 4 beigušies mīkstie mandāti
- `saeima_votes` #213 + `saeima_bills` #182 (1359/Lp14) + 90 `saeima_vote` claims: noņemts «— vēl viens LPV iniciatīvu paciets, ko koalīcija nebloķē sākumposmā» (atrada @devils-advocate). Skenēti 8 347 kopsavilkumi pēc vērtējuma vārdiem: 1 īsts trāpījums. `rollback_vote213_vertejums_2026-10-15.sql`.
- `tracked_politicians.role` (T6): Liepiņš, V. Zariņš → «Bijušais 14. Saeimas deputāts (mandāts beidzās 2026-06-11)», Zemmers (2026-05-21), Maslovskim datums 06-25 → 06-11. Avots: Saeimas stenogrammas (Vēstnesis 369232, 368660); 15. Saeimā neviens nav ievēlēts. `rollback_role_miikstie_mandati_2026-10-15.sql`.
- Deploy dfcacd2b, verify_host 9/9. Papildus Jānis Zariņš (138) → mandāts beidzās 2026-06-04 (LSM 06-04: Čudara atgriešanās; eng.lsm.lv 06-11; balsojumi līdz 05-28), `rollback_role_janis_zarins_2026-10-15.sql`, deploy d05e35b4, verify_host 9/9.

## 2026-10-15 (4) — Rutīnas 3. solis: tvērums no datiem, «pārbaudīti N no M»
- `src.routine.hunt_scope(db, day)` (dienas pozīcijas + balsotāji) un `log_hunt_trace(...)` (vienīgais rutīnas pēdas ceļš; `date` no `current_routine_day()`, `claim_ids`/`politician_ids` obligāti). Plāns `docs/superpowers/plans/archive/2026-10-15-pretrunu-pedas-parklajums.md`.
- `_check_contradictions`: jaunā formāta rindām «pozīcijas N/M, balsotāji K/L», `partial` ar nepārbaudīto vārdiem; vecās rindas — kā līdz šim. Pēdu atrod arī pēc `details.date` (ne tikai ±1 d timestamp). Mutācija pierādīta.
- `dienas-rutina.md` 3. solis: ⌈balsotāji/5⌉ hunteri ar skaidriem pid sarakstiem; `contradiction-hunter.md`: skaidrs saraksts pārspēj «aktīvāko» atlasi un ≥5 slieksni; `claim_new` vienmēr `position`. Smaga diena (10-14: 43 balsotāji) = 9 hunteri.

## 2026-10-15 (3) — Pretrunu pārbaudes pārklājums: mērījums + izmēģinājums
- 30 d: 184 politiķi ar jaunām pozīcijām; hunt rindas nosauca 166, pozīcijas pēc id 1 698 / 2 799 (pārējais — tikai pašziņots `claims_checked`). 13 balsotāji nenosaukti (`docs/audits/2026-10-15-pretrunu-parklajums/`).
- Izmēģinājums (3 hunteri + DA, operators «jā»): 13/13 pārbaudīti, 1 kandidāts (Kļaviņa, 139/P14) → KILL, 0 pretrunu; `logs` #656438. Robs bija pēdā, ne atradumos.
- `logs` #656431 `date` 10-15 → 10-14 (D4 rinda lika 10-15 rutīnas 3. solim izskatīties izpildītam; `rollback_logs_656431_date_2026-10-15.sql`). Priekšlikums ieviests — (4).
- 2. kārta (10 balsotāji ar lielāko jauno pozīciju skaitu): 3 kandidāti → 3 KILL, 0 pretrunu. Kopā 23 politiķi, ~1,3 M Opus tokenu; 16 mazie balsotāji atstāti jaunajai rutīnai.

## 2026-10-15 (2) — OG kartītes sepijā: pretrunas, sākumlapa, profili, partijas, tēmas
- Operatora izvēle: sepijas «arhīva» dizains (paraugi tumšs pret sepiju). Kopīgs renderētājs `src/render/_common/og_render.py` + `templates/_og_base.html.j2`; pārzīmē pēc satura hash (`output/og-hashes.json`), ne pēc `detected_at` — stance/virsraksta labojums tagad atjauno kartīti.
- `contradictions.headline` (≤60 zīmes, `store_contradiction(headline=…)`), 29 aizpildīti (`rollback_contradictions_headline_2026-10-15.sql`). Profila kartītes skaitļi = profila lapas `stat_tiles`.
- Sākumlapas kartīte jaunā vārdā `assets/og-atmina.png` (X/FB kešo pēc URL); `og-image.png` vairs netiek lietots. Deploy fda42c2a, verify_host 9/9. Atvērts: «Vārdi pret darbiem» kartītē likumprojekta apraksts (`backlog/vietne-ui.md`).

## 2026-10-15 — D4 pabeigts; stance precizitāte mērīta; `@stance-checker` izmēģinājums
- D4 web 1 signāls: 184 pāri → 43 pozīcijas; twitter 60 / vestnesis 76 atlikti (operators). 10 D4 NEEDS_REVIEW paturēti (`rollback_nr_d4_2026-10-15.sql`). Deploy a11c688f.
- Neatkarīga pārbaude (Astra + Opus pret avotu): D4 ≥2 signāli 32/155 laboti (`rollback_d4_155_astra_2026-10-15.sql`); rutīnas nejauša izlase 8/40 (seed 20261015, `rollback_routine_sample40_2026-10-15.sql`). Noteikumi promptā bija — teksts vien to nelabo.
- Izmēģinājums: `@stance-checker` (RUBRIKA.md, Opus pēc noklusējuma, modeļa-neitrāls) + `scripts/apply_stance_fixes.py` (tests `tests/test_apply_stance_fixes.py`, 8/8 mutācijas). Pastāvīgs rutīnas solis — tikai pēc operatora «jā» pēc izmēģinājuma.

## 2026-10-14 (16) — D5 vecās laika joslas saites dzēstas (2 660)
- Dzēstas `mentioned` saites uz twitter dokiem, kuru tekstā nav ne īpašnieka @konta, ne matcher vārda formas — `rollback_d5_timeline_mentions_2026-10-14.sql`; trigeris ierakstīja 2 660 apspiešanas.
- No 3 182 kandidātiem izlaisti 522: vārda sakne bez uzvārda («Jurģim») vai amata vārds («premjers»). Izlases: 20/20, tad 1/30 un 2/30 pieminējumi (filtrs paplašināts), beigās 0/30.
- Atrasts testa dokuments 24343 («Test Politiķis», 2026-04-23) ražošanas DB; saišu un claim 0 — nav redzams vietnē, atstāts.

## 2026-10-14 (15) — Operatora lēmumi: 7 NEEDS_REVIEW, D5 laika joslas saites, D8 slēgts, citātu nogriešanas brīdinājums
- 7 NEEDS_REVIEW: 5 izvērtēti (737774 pārrakstīts + re-embed), 737766 un 737781 dzēsti — `rollback_nr_operator_2026-10-14.sql`. 737776 citāts atjaunots: komats pirms «pauda» pieder tiešās runas piebildei.
- D5 `src/social.py`: svešs tvīts īpašnieka laika joslā dod `mentioned` tikai, ja tekstā ir viņa @konts vai matcher vārda forma; vecās 3 182 rindas — tikai priekšlikums (`suspect_at` nelasa neviens skaitītājs). Zudums: kopīgs uzvārds bez vārda (~9 %). Tests `test_store_tweets_non_author_tweet_links_owner_only_when_named`.
- `save_analysis` `quote_end_mismatch` (nebloķē): citāts nogriezts izteikuma vidū; DB 251/6 874 (3,7 %), izlasē 9/14 īsti. Tests `tests/test_quote_end.py`, abi pierādīti ar mutāciju. D8 slēgts (vakara analīze). RT-paketes robeža apstiprināta.

## 2026-10-14 (14) — `claim-extractor.md`: RT paketei robeža 20, § 1 «darītājs un adresāts»
- Noteikums «≤12 dokumentu pasē» un «3 tukši pēc kārtas → STOP» neattiecas uz plāna `rt` paketi (20 doki, `src/extraction_plan.py`): rutīnā #22 apstājās pie 11/20. Operators apstiprināja 2026-10-14 (`backlog/agenti-pipeline.md` 6(a)).
- § 1 «apgriezts … darītājs un adresāts»: Astras izlasē 737777 «pret žurnālistiku jāizturas piesardzīgi» kļuva par «žurnālistikai jāizturas»; labots ar `rollback_claim_fixes_2026-10-14.sql`.

## 2026-10-14 (13) — Vārdabrāļi: eval korpuss +11, amata kolokācijas mērījums
- `scripts/eval_matcher_collisions.py` FP 32 → 43 (9 Meļņi, 95063, 110049). B2D2HC fp_links 1 → 2 (tikai 95063 Valainis-docents), gold 3055/3116 nemainīgs, fidelity 943/0. Meļņus un 110049 matcher nepiesaista arī bez `negative_patterns`.
- Mērījums `_homonym_role_scan.py`: amata kolokācija kā automātisks sargs nederīgs (4 627 / 946 karogi, izlasēs 0 kļūdainu saišu). Sīkāk `backlog/matcher.md` § Konteksta kolokācija. Kods `src/matcher.py` un `negative_patterns` neskarti.

## 2026-10-14 (12) — D2 6. solis: pievienošanas rollback ar slēdzi `off`…`record`
- `scripts/backfill_truncated_docs.py` (vienīgais dzīvais ģenerators; meklēts `DELETE FROM document_politicians` + «rollback»×junction `scripts/`, `src/`, `wiki/operations/`): relink-pievienojumu DELETE ietīti `dp_suppression_mode` `off`…`record`. Tests `test_rollback_of_relink_leaves_no_suppression` krīt uz HEAD (1 apspiešana) un bez `record` rindas (režīms paliek `off`).
- `/seed-entity` 8. solis: rescan-pievienojumu un seed rollback DELETE tāpat ietin.
- 25 vecie tikai-DELETE rollback faili NElaboti apzināti: palaisti tie rada pārliekas apspiešanas (droša puse), redzamas 20.–22. pārbaudes saucējā. Rollback netiek ietīts transakcijā — pusizpildīts fails ar `off` ir tieši tas, ko 20. pārbaude ziņo kā `broken`.

## 2026-10-14 (11) — D2 audits: `/audit-integrity` pārbaudes 20–23 (plāna 5. solis)
- 20 (vārti): neatcelta apspiešana, kuras saite atkal junction tabulā (`scope='pair'` — jebkura loma); `broken`, ja trūkst trigera/tabulas vai `dp_suppression_mode` ≠ `record`. 21/22/23 [info]: atcelšanas 14 d (UTC); pārielāde pēc apspiešanas — salīdzina pilnu `datetime(created_at,'localtime')`, ne `DATE()` (stingrāk, redz tās pašas dienas pārielādi); vēsturiskie atgriezumi `scripts/audit_dp_readds.py` (`_d2_scope` metode, kļūdas vairs netiek norītas).
- Prod (ro): 20 9/0, 21 9/0, 22 9/0, 23 4 229/0 (88 faili, 4 SQL kļūdas — neviena nesamazina atjaunojamo kopu). Labots `_d2_scope` slēptais defekts: relatīvs ceļš → git klusi tukšs → mtime (1 viltus kandidāts).
- Testi `tests/test_audit_dp_suppressions.py` 9; 7 mutācijas katra krīt. `audit_dp_readds.py` ir junction-INSERT atļauto sarakstā: raksta tikai savā `:memory:` kopijā.

## 2026-10-14 (10) — D2 pilnais risinājums: soļi 1–2 (operatora «jā»)
- `cea6ad92`: tabula `document_politician_suppressions` + 4 trigeri + slēdzis `dp_suppression_mode` (`src/db_migrations.py`); viens rakstītājs `link_document_politicians()` visos `src/` ceļos un 2 skriptos; strukturāls tests pret citiem INSERT. Tests `tests/test_dp_suppressions.py` 8/8 krīt uz HEAD; 7 mutācijas katra krīt; check.sh 3 545 passed.
- Plāna kļūda: kaskādē no `documents` trigerim vajag sargu (citādi FK kļūda). Trigeri produkcijā ieslēdzas nākamajā `init_db()`. Pievienošanas rollback → slēdzis `off` (CLAUDE.md Schema invariants).
- 3. solis (operatora «jā»): rezerves kopija D: (integrity ok); shēma produkcijā + 9 rindas dzēstas `scripts/fix_d2_revived_links_2026-10-14.py` → 9/9, apspiešanas aktīvas 9/9 (8 `role`, 1 `pair`); rollback `data/rollback_{dp_suppressions_schema,d2_revived_links}_2026-10-14.sql` commitoti pirms (88ce12bb). Pozīcijas neskartas. Lasīšanas ceļš izmēģināts produkcijā ar transakcijas zondi (90310/225 abas lomas, 124191/6 subject → apspiests, 0 rindu, rollback). check.sh 3 545 passed; render `politiki,zinas,dashboard,static`. Publicēts 90d4c991 (verify_host 9/9).
- Atlikuši: 5. solis (audits: neatcelta apspiešana junction = 0; atcelšanas 14 d; pārielādes pēc apspiešanas; vēsturiskie atgriezumi), rollback-ģeneratoru slēdzis.

## 2026-10-14 (9) — D2: dzēstās saites atgriežas — mehānisms, 0. solis, plāns
- Izpēte `docs/audits/2026-10-14-datu-kvalitate/D2-saites-atgriezas.md`: 2 ceļi (same-URL pārielāde `insert_document`; matcher backstop/rescan), neviens rakstītājs nekonsultē dzēsumus. `_d2_scope.py`: 4 229 vēsturiski noņemti trīskārši, 9 atkal DB.
- 0. solis `19b5cd92`: jau piesaistīts politiķis pārielādē patur savu lomu (`_linked_pids`, kā matcher rescan); tests `test_refetch_keeps_corrected_role`, mutācija 2/2 krīt.
- Pilnais risinājums (apspiešanas tabula + trigeri + viens rakstītājs) — plāns `docs/superpowers/plans/archive/2026-10-14-saisu-apspiesana.md` (advisor + Astra); gaida operatora lēmumu par pievienošanas rollback slēdzi.

## 2026-10-14 (8) — LETA datelīnija → `documents.published_at` (D1)
- `src/ingest.py::parse_leta_dateline` («Rīga, 24. marts, LETA.»; gads no `scraped_at`, logs 7 d) un `leta_published_at` ieslēgts `_ingest_source`, kad lapa datumu nedod. Atstarpe scrape−datelīnija korpusā: 0 d 1 988 · 1 d 548 · 2 d 33 · 3 d 3 · 4 d 6 · >4 d 0. Tests `tests/test_leta_dateline.py` (31; logs 400 → 2 krīt).
- Backfill `scripts/backfill_leta_published_at.py`: 2 577/2 578 aizpildīti (`updated == intended`, 1 jau bija), formāts `YYYY-MM-DDT00:00:00`; rollback `data/rollback_leta_published_at_2026-10-14.sql` commitots pirms `--apply` (1da6a7e4). Dedup to nenodzēš (`COALESCE`, `src/db.py`).
- Ingest ceļš NEIZMĒĢINĀTS līdz nākamajai ielādei — pārbaude: `SELECT COUNT(*), SUM(published_at IS NULL) FROM documents WHERE source_domain LIKE '%leta.lv' AND scraped_at > '2026-10-14 17:00'` → NULL 0.
- Apzināti NAV `scripts/ingest_url.py`: vēsturiskā ielāde ar šodienas scrape datumu → gada kļūda iziet cauri logam.
- Redzams Ziņās: LETA kartītes (pusnakts) dienas ietvaros nokrīt zemāk; 10 kartīšu saite pāriet uz pārpublicētāju («jaunākā kopija uzvar»). Operatora lēmums pirms deploy.

## 2026-10-14 (7) — Datu kvalitāte (1): partiju karogi, kailie ID pārskatos
- Audits 5 (T6) 3 karogi = LIKE viltus trauksmes, partija nav mainīta: 729721 Krusts («izstāj» ← Stambulas konvencija), 730619 Pagors («nepametam»), 729888 Urbanovičs (paliek «Saskaņā», 21.11 kongresā rosinās pašlikvidēšanos — doks 132852). `ACCEPTED_5` nav ieviests (operatora lēmums).
- `scripts/check_output.py` 5. pārbaude: kailie iekšējie ID `blog/*.html` redzamajā tekstā (saites un komentāri atļauti); `BARE_ID_IS_FAILURE=False` — tikai brīdinājums, kamēr netīrie pārskati nav laboti. Saucējs 215 lapas, 20 atradumi 6 lapās (05-04, 05-12, 05-18, 06-04, 06-09, 07-22); tests `test_bare_internal_id_in_brief_prose_is_reported`, mutācija 3/3 krīt.
- Pārskats 2026-08-10 (#446) «Konteksts» pārrakstīts lasītāja valodā; rollback `data/rollback_brief446_kaili_id_2026-10-14.sql` commitots pirms UPDATE; render `dashboard,blog,static`, HTML pārbaudīts (0 ID).
- Pēc operatora «jā»: pārējie 6 pārskati laboti (iekavu ID izņemti, pretruna #39 → saite), rollback `data/rollback_briefs_kaili_id_2026-10-14.sql` (375bcc2c, pirms UPDATE), 6/6; `BARE_ID_IS_FAILURE=True` — 215 lapas, 0 atradumi; vārts pierādīts ar ieliktu «claim #12345» → exit 1.

## 2026-10-14 (6) — Claim-extractor kļūdu komplekts v2 (BACKLOG 50(e) uzlabojums (c))
- 38 gadījumi (viss dokuments, `must`/`forbidden`, pārklājoši tagi: attribution, party_text, hedge, allegation, scope, outside_fact, question/tense/cause, EMPTY, positive, 2 stenogrammas, clean) no 10-14 verificētajām rindām; iesaldēti `docs/audits/kludu-komplekts-v2/` (ārpus publiskā spoguļa), recepte `docs/eval/kludu-komplekts/README.md`.
- Skripti `freeze.py` · `contamination.py` (ID + ≥40 zīmju teksts, arī atsauču faili) · `score.py` (3 neatkarīgi akli vērtētāji + recall; screen ≥2 vairāk krītošu vai EMPTY/allegation regresija; apstiprina 2/3 atkārtojumi; support ≥ 95 % un 0 garumzīmju kļūdu = cietie vārti). Plāns `docs/plans/archive/2026-10-14-kludu-komplekts-v2.md`; Astra pārskatīja 3×, advisor 2×.
- Bāzes skrējiens (operatora «jā», 25 Opus; HEAD, HEAD-2, mutants bez 3 noteikumiem): visi IZTUR, **mutants NAV izķerts** — jutība NAV pierādīta. HEAD kritumi bija pārklājums, ne kļūdas → noteikums tikai pēc precizitātes, bez netošanas; c23 (zelta kļūda) izņemts → 37 gadījumi. Vērtētāji palaida garām mutanta atrunas nomešanu (c30). Komplekts = pagaidu precizitātes screen; noteikums aģenta promptā netiek ielikts (`runs/2026-10-14-baze/ANALIZE.md`).

## 2026-10-14 (5) — 50(e) 2. kārta: later web 05–07 pilnā, 08/09 dubultā izlase, vestnesis; 8 HOLD
- Operatora «jā» (25 Opus): 18 vērtētāji + 7 verifikatori, 875 rindas (`docs/audits/2026-10-14-stance-izlase/parbaude/`). Vērtētāja A+B: 05 32 % · 06 31 % · 07 21 % (pilnā); 08 apvienoti 5/120 = 4,2 %, 09 4/120 = 3,3 % (< 5 % → regulāras izlases); vestnesis 1/75.
- Piemērots ar rollback `data/rollback_stance_parbaude_1014_2026-10-14.sql` (commitots pirms `--apply`): 282 stance (282/282), vektori 282/282, dzēsts 1 (#20170). HOLD 1 (#20389 Indriksone — NA programma vai viņas vārdi). 9 publicētās pretrunas ar pārrakstītu pusi izlasītas — kopsavilkumi atbilst.
- 8 HOLD (later tvīti) pēc operatora: 4 atsaukti, 2 pārrakstīti (#548470 ar citētā tvīta uzņēmumu, nolasīts ar twikit), 2 paturēti; rollback `data/rollback_stance_later_tviti_hold_2026-10-14.sql`. RUBRIKA 7. noteikums: paša pavediena glabātās daļas = viens teksts.
- Publicēts: pirmā izlase (versija bd2024f7) un 2. kārta + HOLD (versija d5a4a0d9), abas reizes verify_host 9/9.

## 2026-10-14 (4) — 50(e) izlase: v4 240 + later web 300
- 540 pozīcijas, 12 Opus (10 vērtētāji + 2 verifikatori), rubrika `RUBRIKA.md`; plāns, Astras un advisor labojumi, rezultāti `docs/audits/2026-10-14-stance-izlase/` (`PLANS.md`, `REZULTATI.md`).
- Vērtētāja A+B: v4 tvīti 0/100 · web 0/110 · vestnesis 0/30 (akla D pārbaude 30 v4 rindām atrada 1 B, #730538); later web 05 42 % · 06 23 % · 07 17 % · 08 3,3 % · 09 3,3 %.
- Piemērots ar rollback `data/rollback_stance_izlase_1014_2026-10-14.sql` (commitots pirms `--apply`): 75 stance (75/75), vektori 75/75, dzēsts 0. #548363 orķestrators sašaurināja (Astra). Publicētā #38 kopsavilkums joprojām atbilst. Render lokāli, check.sh zaļš (3 504), Publicēts 90d4c991 (verify_host 9/9).
- Gaida operatoru: pilna pārbaude 05–07 (680), dubulta izlase 08/09, vestnesis 55 — palīgu skaits handoff; 8 HOLD ieteikumi `hold_ieteikumi.md`.

## 2026-10-14 (3) — Pretruna #42 pārsieta; 50(e) analīze
- Operatora lēmums: #42 (Kulbergs, `minor_shift`) jaunā puse 527887 (tvīts bez «stulbs»/«bez konkursa») → 527891 (LSM 11.06, kur abi ir); kopsavilkumā pievienots, ka viņš kopumā atbalsta konkursus un ka konkurss 19.06 (pēc izteikuma) beidzās bez rezultāta. `data/fix_`/`rollback_contradiction_42_repoint_2026-10-14.sql`, changes 1.
- Analīze (advisor + GPT-6-Astra): 3 758 bija publicētas pirms-v4 pozīcijas, ne neanalizēti doki; mentions 2 %. A+B pēc mēneša 42 → 8 % (05 → 09). Nākamais solis: izlase v4 240 + later web 300 ar sliekšņiem (`docs/arhivs/handoffs/HANDOFF-2026-10-14.md`).

## 2026-10-14 (2) — Stance pret avotu: `later` slāņa tvīti (BACKLOG 50(e))
- 3 758 tvītu pozīcijas, 82 Opus palīgi (65 vērtētāji + 17 verifikatori; rubrika `RUBRIKA.md`). Vērtējumi A 10 · B 783 · C 180 · D 2 771 · U 14; verifikācija ACCEPT 641 · ADJUST 313 · WITHDRAW 11 · HOLD 8.
- Piemērots ar rollback `data/rollback_stance_later_tviti_2026-10-14.sql`: 954 stance + re-embed (954/954), 11 claims dzēsti (11/11). Commit `d5e1426d`; check.sh zaļš.
- `_fix_stance_verdicts_2026_09_30.py`: rollback faila datums = piemērošanas datums. 8 HOLD + pretruna #42 → operatoram (`docs/audits/2026-09-30-stance-izlase/README.md`). Atlicis web 1 555. Publicēts 10-14 (versija 21a1717f, verify_host 9/9).

## 2026-10-14 (1) — Operatora lēmumu sesija: 26 `[OPERATOR]` ieraksti izšķirti
- Ieteikumi ar advisor, operators apstiprina visus (`docs/verdikti-2026-10-14.md`). Noteikumu maiņas: NEEDS_REVIEW nosaka šaubu pazīme, ne skaitlis (CLAUDE.md eskalācija 2 → `claim-extractor.md` § 4; 19. pārbaude karo tikai <0.5); ASR kļūda video citātā ir mūsu (VERBATIM izņēmums); steidzamība procedurāla tikai atzīšanas balsojumam (`is_urgency_declaration`); CVK lapās organizācijas nesaista; RT @AtminaLV nav avots.
- Dati ar rollback (`data/rollback_verdikti_h{1..4}_2026-10-14.sql`, `changes()` == plāns visos četros: 13, 37, 54, 2 206): 26 junction labojumi + 5 jauni `subject` pāri; 10 claims; 25 balsojumu un 2 181 claims tēma (nodošanas klauzula).
- Pēc: `eval_matcher_collisions` B2D2H FP 1 / gold 3055 nemainīts; audits 19 flagged 0 (0.5–0.6 bez marķiera 87). Kods `0429f5f0`, `bd8a2715`; check.sh zaļš (3506 passed).

## 2026-10-12 (8) — TypeSafe matcher veto izslēgts
- Operatora lēmums: `scripts/morning_ingest.py` noklusējums `shadow` → `off`; `enforce` neieviests. Iemesls: divās ēnas nedēļās kļūdaini veto īstiem politiķiem gandrīz katrā ielādes dienā (akuzatīvs/ģenitīvs/datīvs īsos tekstos; žurnāls `backlog/dati-db.md` § 2026-09-18 (a)).
- Vārts `tests/test_morning_ingest_veto_default.py::test_clean_env_defaults_to_off` redzēts sarkans pirms koda maiņas. Ikdienas veto atskaite izņemta no `/dienas-rutina`; `saites_proposals.py` (TypeSafe saišu priekšlikumi) nemainīts.

## 2026-10-12 (7) — `@claim-extractor` pretrunu kandidātus tikai ziņo
- (6) saskaņoja hunter, DA, deep-check un dienas-rutina, bet `claim-extractor.md` § 2.8 + § 5 un `glabasana.md` joprojām lika `store_contradiction` saukt pašam — apietu DA. Tagad ekstraktors tikai ziņo `claim_old`/`claim_new`/kāpēc, glabā orķestrators pēc DA (kā jau `stale-sweep-brief.md`). Atklāts 10-12 vakara rutīnā; tur visiem 19 ekstrakcijas aģentiem tas tika aizliegts dispatch brīfā.

## 2026-10-12 (6) — Pretrunas: vispirms @devils-advocate, tad glabā; `contradiction-hunter.md` 33 → 22 KB
- Operatora lēmums: hunter sūta kandidātus @devils-advocate PIRMS glabāšanas, glabā tikai izdzīvojušos ar `src.tools.store_contradiction(..., reviewed=True)` (`confirmed=0`); jauns `reviewed` arguments (`src/db.py`, `src/tools.py`; tests `test_tools.py::test_da_survivor_stored_as_reviewed`, krita bez labojuma), lai rutīnas 4. solis nerāda izdzīvojušos kā nepārbaudītus. Limits — 5 politiķi solī.
- Prompts saskaņots ar kodu: pirmās personas filtrs visos SQL paraugos, frakcija no konkrētā balsojuma (`siv.faction`, NULL ar `IS ?`), `claim_old/new` pēc `stated_at`, Atturas formula kā `src/saeima/votes.py:205`; pievienots petīciju polaritātes noteikums (2026-10-07 atsauktās pretrunas) un T20 `summary` brīdinājums. Pārbaude: 16/16 datumi, 6/6 ID, 4/4 T, 11/11 koda atsauces, 13/13 ārējie enkuri. Rindu numuru atsauces vecos CHANGELOG/rollback failos (`:69–70`, `:411`, `:122–126`) tagad novecojušas.

## 2026-10-12 (5) — `brief-writer.md` saīsināts (29,9 → ~15 KB)
- Codex pārskats + advisor; incidentu datumi un ID saglabāti (17/18 datumi, 8/8 ID, 3/3 T — iztrūkstošais 2026-04-09 bija novecojusī «Galvenais rindkopa» atsauce). Noteikumu maiņas: pretrunu parauga SQL ieguva `COALESCE(confirmed,1)=1` kā skeletā (`src/briefs.py:929–932`); izņemts novecojis pozīciju skaita paraugs un rindkopa «nebūtiskas rindas drīkst izmest» (pretrunā ar T7). Tēmai bez kastītes — prozas bloks, ne `context-box` div (kā praksē).

## 2026-10-12 (4) — Tiešraižu lapu teksts netiek pārrakstīts
- `insert_document()`: ja web URL ceļā ir `tiesraid`, atkārtota ielāde NEpārraksta saglabāto tekstu un `reviewed_at`, tikai pievieno saites (izņēmums 2026-08-17 «URL-first» noteikumam). Iemesls: jauns.lv tiešraides pārskrāpējums paturēja 10 jaunākos ierakstus, 729912/729930 citāti pazuda.
- Saucējs: 39 web dokumenti ar `tiesraid` URL, 4 ar pozīcijām (`SELECT … WHERE lower(source_url) LIKE '%tiesraid%'`); daļa ir raksti PAR tiešraidēm (TikTok u. c.) — tiem labojumi vairs netiek ielādēti, apzināti piesardzīgi. Vēlākie tiešraides ieraksti netiek saglabāti. Tests: `test_db.py::test_live_blog_refetch_keeps_stored_text` (krita pirms labojuma).

## 2026-10-12 (3) — Iknedēļas šifrēta DB kopija uz cita diska
- `scripts/backup_db.py`: SQLite backup API → zstd → gpg AES256 → atjaunošanas pārbaude KATRĀ skrējienā (integrity_check + 4 tabulu skaiti) → kopija + sha256 galamērķī; paturēt 4; ne biežāk kā reizi 7 dienās (exit 3). Galamērķis un paroles fails tikai `.env.backup` (gitignorēts); noklusējums `local:D:/atmina-backups` (cits fiziskais disks). Pirmais skrējiens 2026-10-12: 2,9 GB → 0,56 GB, 92 s.
- `print_routine` rinda «Ārējā DB kopija: N d» brīdina, ja kopijas nav vai tā > 8 d. Vārti: `tests/test_backup_db.py` (3 testi, 6 mutācijas). Atvērts: ārpus mašīnas kopija (Namecheap/cits — operatora lēmums), paroles frāze jāglabā arī paroļu pārvaldniekā.

## 2026-10-12 (2) — Deploy bez Python apstājas; DA prompts atsauc publicētu pretrunu ar `withdraw_contradiction()`
- `scripts/deploy.sh`: ja `.venv` Python nav, preflight (check_output + publish-gate) agrāk tika klusi izlaists un wrangler gāja — tagad exit 1; apiešana tikai `--no-output-check`. Vārts: `tests/test_deploy_script.py::test_preflight_without_python_refuses_to_deploy` (krīt bez labojuma: exit 0).
- `.claude/agents/devils-advocate.md`: «clearly false» piemērs šķiro publicētu (`confirmed=1` → `withdraw_contradiction()`, `-1`) no nepublicēta (`reviewed=1, confirmed=0`); agrāk tas lika `confirmed=0` arī publicētām. Avots: Codex Astra projekta pārskats 2026-10-12.

## 2026-10-12 — Audita 17. un 9b vārtu metode
- 17. pārbaude vairs neuzskata citāta beigu pieturzīmi par zudumu (karogi 18 → 5, `scripts/audit_integrity.py --only 17`); teksta tiešraižu citāti 729912/729930 pieņemti (T12, `backlog/avoti.md`). 9b ieguva `ACCEPTED_9B` (6 ar roku pārbaudīti). Vārti: `tests/test_audit_integrity.py` (17 trailing-punctuation, 9b hand-verified). Bāzlīnija: `.claude/references/audit-integrity/bazes-linijas.md` § 2026-10-12.

## 2026-10-11 (12) — Spriedžu tipu etiķetes no viena avota
- `TENSION_TYPE_LV` / `TENSION_BADGE` / `TENSION_LINK_CLASS` (`src/render/_common/constants.py`) ir vienīgais kartējums: `_fetch_tensions` `type_lv`, saites.html (padots `#saites-data` JSON → `assets/sav1.js`, savs kartējums izņemts), profila mini-grafs. «Nostāju konflikts» tagad ar nosaukumu un zilu toni arī saitēs un 7 profilos. Vārts: `test_multiselect_dropdown.py::test_fourth_tension_type_named_on_saites_and_profile` (krīt bez kartējuma).

## 2026-10-11 (11) — Pretrunu un spriedžu lapas: saturs pirms vadības
- `pretrunas.html` (operators: «nepatīk»): rindā pretrunas kopsavilkums (`src.briefs.contradiction_excerpt_text`, 2 rindas) nogriezta pirmā izteikuma vietā; glifa ≈/↺ vietā smaguma vārds; Grupēt/Kārtot kā Saeimas lapas cilnes (bez sarkana); ievads `pagehead` lead — «iziet pretargumentu pārbaudi, un to apstiprina cilvēks» (pārbaudīts: 28/28 `confirmed=1` ar `reviewed=1`), agrākais «konstatētas automātiski» bija nepatiess.
- `spriedzes.html`: «vārds [partijas saīsinājums] → vārds [..]» ar `.pp-party-chip`, apraksts = galvenais teksts, apakšā avota domēns + datums, viena teikuma ievads; 4. tips «Nostāju konflikts» ar etiķeti un `badge-blue` (`TENSION_TYPE_LV`/`TENSION_BADGE`). Vārts: `test_multiselect_dropdown.py::test_spriedzes_names_fourth_tension_type` (krīt bez kartējuma).
- Partijas lapā spriedžu datums LV laikā (`date(created_at,'localtime')`, T17), bija UTC.
- Paliek: `saites.html` un profili rāda 4. tipu neapstrādātu (`_fetch_tensions` `type_lv` — otrs kartējums; saites bāzlīnija iesaldēta) → backlog.

## 2026-10-11 (10) — Likumprojektu tēmu filtrs caur msv1.js; tumšās tēmas josla bez uzplaiksnījuma
- Balsojumu Likumprojektu cilnes `#bill-topic-select` bija vienīgais roku rakstītais dropdown (etiķete palika «Visas tēmas», citus sarakstus neaizvēra) → `atminaMultiSelect` (`assets/blv1.js`). Vārts: `test_multiselect_dropdown.py::test_bill_topic_select_updates_label` (krita: `'Visas tēmas' == 'Izglītība'`).
- `theme-init.js` (bloķējošs) tumšajai tēmai uzreiz uzliek `theme-color` `#0d1014` — josla vairs nemirgo gaiša līdz `chrome-v1.js`. Vārts: `test_base_theme_meta.py::test_theme_init_sets_dark_theme_color_before_paint` (krita). Pārlūkā ar bloķētu chrome-v1.js: tumšā `#0d1014`, gaišā `#f7f3e8`.

## 2026-10-11 (9) — Cilnes ar vienu ARIA kontraktu; theme-color no `--bg`
- Analīžu, Balsojumu un partijas lapu cilnes iegūst profila `pp-tabs` kontraktu (role=tablist/tab/tabpanel, aria-selected, roving tabindex, bultas/Home/End) caur `assets/tabs-v1.js` (`atminaTabs`); profils un `ppv1.js` netiek aiztikti (fikstūrā 0 no 10 profilu lapām mainās). Balsojumu apakšcilnēm `aria-pressed` → `aria-selected`.
- X lapas «Tikai ieraksti / pieminējumi / Visi» nav cilnes (filtrē vienu plūsmu) → `aria-pressed` kā pārējie filtri, `role=tab` noņemts. Vārti: `tests/test_tabs_keyboard.py` (krita uz visām 3 lapām), `test_toggle_aria_pressed.py` X bloks (krita); 9 bāzlīnijas heši = tikai ARIA atribūti + `<script>`.
- `chrome-v1.js` theme-color nolasa `--bg`; statiskais `base.html.j2` literālis = gaišās tēmas `--bg` (`test_base_theme_meta.py`, krīt pie 1 zīmes mutācijas).

## 2026-10-11 (8) — Kopīga lapas galvene un viens filtru dropdown skripts
- `templates/_macros.html.j2` `pagehead`/`metric`: 12 lapas pārceltas ar baitu identisku izvadi (fikstūras renders `diff -rq` = 0; 1 atstarpes mutācija = 94 faili); `blog.html` un `spriedzes.html` no vecā `section-header` pāriet uz to pašu galveni (spriedzes iegūst h1). about/kontakti/analizes/statistika apzināti nē (apakšvirsraksti vai kurēta lapa).
- `assets/msv1.js` (`atminaMultiSelect`) aizstāj 6 `setupMultiSelect` kopijas (blv1, prv1, sav1, spv1, x-v1, znv1); klases `.open`/`.selected` nemainītas ms-a11y dēļ. Vārts: `tests/test_multiselect_dropdown.py` (krīt bez klikšķa-ārpusē apstrādes); 18 dropdowni 6 lapās pārbaudīti pārlūkā, 0 konsoles kļūdu.

## 2026-10-11 (7) — Partiju krāsas no viena avota (`parties.color`)
- `partijas.html` un `saeima.html` rādīja citas krāsas nekā profili un pārējās lapas (8 no 9 partijām, piem. NA zaļa profilā, sarkana pusaplī). Tagad visas lapas lasa `parties.color` caur `src.coalition.party_color_map(db)`; `PARTY_COLORS` izņemts, viens `FALLBACK_COLOR` aizstāj `#8b8fa3`/`#64748b` literāļus Python kodā.
- DB: vietnes palete ierakstīta `parties.color` (12 rindas; MMN, LZP, LRA, SL jauni toņi, lai nav dublikātu); rollback `data/rollback_party_colors_2026-10-11.sql`. Vārts: `test_render_chars.py::test_party_colour_identical_on_personas_and_partijas` (krita pirms labojuma); 20 bāzlīnijas heši pārģenerēti (tikai krāsas).
- Paliek: `votes_matrix.py` `FACTION_COLORS` un `social_agent/visuals.py` savas paletes; tēmu-pret-partiju krāsu sadursmju tests tagad lasa produkcijas DB (CI izlaiž).

## 2026-10-11 (6) — Profilā partijas saīsinājums punkta vietā
- Operators: zilais aplis ar apmali pie partijas nosaukuma lasījās kā «tiešsaistē» statuss. Tagad `parties.short_name` rāmītī partijas krāsā (`.pp-party-chip`, `templates/politician.html.j2`); teksts `--text` krāsā, jo LPV/ASL dzeltenais uz krēmīgā fona nav salasāms. Žurnālistiem un bezpartejiskajiem — tikai teksts.
- Partiju logo apzināti NĒ: 19 partijas (arī bijušie saraksti bez logo), CSP prasa pašmitinātus failus, mazā izmērā nesalasāmi, oficiāls zīmols neitrālā vietnē rada saistības iespaidu.

## 2026-10-11 (5) — Wiki: pārskatu kopijas ģenerē `wiki_sync()`; sintēžu vārdabrāļi netiek saistīti
- `wiki/dailies/` un `wiki/weeklies/` raksta `wiki_sync()` no `context_notes` (faila vārds = `brief_subject_date()`); brief-writer vairs neraksta ar roku (bija 170/187 un 5/24 failu). `weeklies/` gitignorēts kā `dailies/`.
- Sintēzes `politicians:` žetons, kas atbilst >1 aktīvam politiķim, netiek saistīts ne ar vienu un brīdina (`src/render/syntheses.py`, eskalācija 1); `judins` gaida operatora izvēli.
- Personu frontmatter: `relationship_type` + `last_active` kā datums; Bases rāda tikai `tracked`. Vecais 2026-04-11 indeksa baneris noņemts.
- `weekly-routine.md`: pārembedošana caur `scripts/reembed_claims.py` (bija DELETE+INSERT pret eskalāciju 8); `monthly-routine.md` — nav praktizēta kopš 2026-04.

## 2026-10-11 (4) — Arhitektūras pārskats: @devils-advocate vārti «visām», viena rutīnas rokasgrāmata, audita 19. pārbaude
- @devils-advocate vārti: VISĀM rutīnas dienas jaunajām pretrunām jābūt `reviewed=1` (operators 2026-10-11); kods agrāk bloķēja tikai pie 0 pārskatītām (`.claude/agents/quality-reviewer.md`).
- `wiki/operations/daily-routine.md` → norāde uz `/dienas-rutina` (4 pretrunas ar kanonisko); divas ārpus-rutīnas plūsmas pārceltas uz `operacijas.md`.
- `/audit-integrity` 19. pārbaude (informatīva): `position` ar `confidence < 0.6` un `review_status IS NULL` — 10-08 kopijā 91 (`--only 19`); tests ar mutāciju pierādījumu.
- CSP tests lasa `assets/_headers`, ne `htaccess.template` (izņem pēc 10-16). Pārskats un atvērtie darbi: `docs/audits/2026-10-11-arhitekturas-parskats.md`, `backlog/*.md` (10 ieraksti).

## 2026-10-11 (3) — Profila galvene telefonā; lupas logo kurētajās lapās
- Operatora izvēle «B» (≤600px): blakus 120 px bildei tikai vārds + amats; partija, X un dalīšanās pogas pilnā platumā zem — zem bildes vairs nav tukšuma (`.pp-id { display: contents }`, `assets/style.css`). Planšete un desktops nemainīti (ekrānuzņēmumi 390/768/1280).
- Kurētajām lapām (nvo-dotacijas-2025, nvo-valsts-maksajumi, partiju-tests) nebija `<symbol id="atm-logo">`, tāpēc lupa izvēlnē bija tukša; `_sync_curated_chrome` to ieliek no `base.html.j2`. Vārts: `test_copy_curated_resyncs_chrome_from_base` (krita pirms labojuma).
- NEEDS_REVIEW izvērtēšanai Jev neizmanto (operators piekrita 2026-10-11) — paliek advisor + pierādījums `reasoning` laukā (Jev dod varbūtību, ne pierādījumu; TypeSafe ēnā locījumu kļūdas).

## 2026-10-11 (2) — Tīrs sepia stils pavedienu un pārskatu attēliem
- Operatora izvēle pēc salīdzinājuma: ar Codex vecā formula (gravīras svītrojums + «textured aged paper») deva graudainu virsmu; `SEPIA_STYLE` tagad prasa gludu virsmu bez graudiem un papīra tekstūras (`src/graphics/prompt.py`).
- Pārtaisīti 10-10 pārskata pavediena 5 attēli un pārskatu attēli 10-09/10-10 (brief_images 367/368 → 369/370; rollback `data/rollback_brief_images_clean_sepia_2026-10-11.sql`). Codex stūrī ielika sīku zīmi — nogriezti 5 % malas.
- Deploy versija 86ebcf15; live `blog/2026-10-09|10.html` un sākumlapa rāda jaunos attēlus (HTTP 200).

## 2026-10-11 — Serifs = pašmitināts Source Serif 4; sākumlapā bez «Partiju programmas»
- Operatora izvēle pēc salīdzinājuma (Georgia / Android šodien / Source Serif 4 / Literata): Georgia nav Android ierīcēs un tai ir «lēkājoši» cipari; Source Serif 4 latviešu «ī»/«ģ» zīmē pareizi (Newsreader 2026-04-18 nē).
- Viens token `--serif` (`assets/style.css` `:root`), sekciju tokeni un literāļi norāda uz to; 4 woff2 (tikai wght ass, latin+latin-ext, ~189 KB kopā), licence `assets/fonts/OFL-SourceSerif4.txt`. OG attēli (Arial/Georgia) — vēl nav pārcelti.
- Sākumlapā zem meklētāja paliek divi sākumpunkti; `partijas.html` — caur izvēlni. `tests/test_index_entry_points.py` krīt, ja saiti atgriež.
- Pārbaude: pilns render, Playwright 5 lapās ielādē Source Serif 4 (HTTP 200), render bāzlīnijas pārģenerētas (`REGEN=1`, 27 passed).

## 2026-10-10 (4) — Pārskata marķiera vārti neskata HTML komentārus
- Pirmajā dzīvajā palaidienā skeleta komentārs `<!-- NEEDS_REVIEW IZLAISTAS -->` (10-10 (2)) saskrēja ar `store_context_note()` marķiera vārtiem — vakara pārskatu nevarēja saglabāt. Vārti tagad skata tekstu bez HTML komentāriem (renders tos izmet, `src/render/blog.py`); marķieris prozā joprojām tiek atteikts (`76f8a553`).
- Tests `tests/test_briefs.py::test_skeleton_with_needs_review_comment_can_be_stored` krita pirms labojuma ar «brief contains NEEDS_REVIEW marker». Pārskats #695 saglabāts pēc labojuma; operators publicēšanu atteica.

## 2026-10-10 (3) — Likumu lapu bāzlīnija vairs nelasa dzīvo `wiki/laws/`
- Viens ceļa punkts `src/render/laws.py::LAWS_DIR` (nolasa izsaukuma brīdī): likumu lapas, `likumi.html`, likumprojektu titulu kešs (`bills.py::_get_law_titles`) un sitemap. `rendered_site` to aizstāj ar `tests/fixtures/laws/` (33 faili no HEAD 4e62ec82, bez `likumi.md`).
- Bāzlīnija pārģenerēta vienreiz (7 lapas — tieši tās, ko mainīja 10-09 wiki sync). Izolācija pārbaudīta: maiņa dzīvajā `wiki/laws/meza-likums.md` → tests zaļš; maiņa fixture kopijā → tests krīt.

## 2026-10-10 (2) — NEEDS_REVIEW pozīcijas pārskatu skeletos neiekļūst
- Dienas un nedēļas skeleta pozīciju vaicājumi izslēdz `review_status='needs_review'` ar `_NOT_NEEDS_REVIEW_SQL` (`src/briefs.py`; `IS NOT`, jo lielākajai daļai rindu statuss ir NULL). Dienas skelets izlaistās nosauc komentārā `<!-- NEEDS_REVIEW IZLAISTAS -->`; agrāk tās izņēma `@brief-writer` ar roku. Cietu vārtu nav (operatora lēmums).
- `print_routine()` rāda «Jāpārbauda šodien: N»; `/dienas-rutina` solis 2c — izvērtē ar advisor pirms pārskata.
- Testi `tests/test_briefs.py::test_needs_review_position_is_left_out_of_the_{daily,weekly}_skeleton`; krīt bez filtra un ar `<>` (pārbaudīts). Nedēļas tests nesargā top partiju un diagrammas bloku joslu (viena partija datos).

## 2026-10-10 (1) — Attēlu dzinēji: --backend gemini|codex
- `src.graphics.cli brief|thread --backend gemini|codex` (vai `ATMINA_IMAGE_BACKEND`); reģistrs `src/graphics/backends.py`, jauns dzinējs = viena funkcija. Iemesls: Gemini 429 (10-09 (11)); `.scratch/codex_*.py` recepte pārcelta kodā.
- Codex: `image_audit` rinda katram izsaukumam (ok vai error), `model='codex-gpt-image'`, `cost_usd=0`; `brief` Codex ceļā neizsauc `budget_check()`. Citi `generate_image()` izsaucēji paliek uz Gemini.
- Testi `tests/test_graphics_cli.py::test_cli_*_backend_codex_*` (3), audita rakstīšanas noņemšana tos nogāž (pārbaudīts).

## 2026-10-09 (11) — Pārskata attēls caur Codex, kad Gemini limits izsmelts
- Gemini projekts atgrieza `429 RESOURCE_EXHAUSTED` (mēneša tēriņu limits), kaut `image_audit` oktobrī rāda 2,22 USD (`SUM(cost_usd)` no 10-01) — limits zemāks vai projekts dalīts; arī `gemini-nano-banana-2.1` (ir API sarakstā) atdūrās pret to pašu.
- 10-09 attēls #367 ģenerēts ar Codex gpt-image: `brief_images.model='codex-gpt-image'`, `image_audit` rinda `cost_usd=0`, saistīta ar `link_audit_row`; variantu ģenerēšana un deploy strādāja bez izmaiņām (4/4 varianti, live 4/4 HTTP 200).
- Recepte `.scratch/codex_brief_image.py` (gitignored, atkārto `cli.py::_run_brief` bez `generate_image`); vai pārcelt uz `scripts/` — operatora lēmums. Deploy `022c60bb`, `verify_host` 9/9.

## 2026-10-09 (10) — A11y: filtru pogām `aria-pressed`
- Pozīcijas, Personas, Balsojumi, Saites: filtru, kārtošanas un apakšciļņu pogām `aria-pressed` kopā ar aktīvo klasi (veidnēs + visos JS pārslēgšanas punktos; `setActive()` pzv1/pnv1). `.matrix-range-bar` izkārtojums no inline stila uz CSS, bez `!important` (atstarpe 6,4 px pirms/pēc).
- `pozicijas.html?tema=`/`?partija=` ar neesošu vērtību → paliek noklusējums (agrāk neviena atzīmēta rinda un 0 rezultātu).
- Tests `tests/test_toggle_aria_pressed.py` (krita pirms abām daļām); baseline REGEN 4 indeksa lapas. Deploy `386d8744`, `?tema=` labojums `1bda5668`; `verify_host` 9/9.

## 2026-10-09 (9) — Saeimā cilne: kāpēc balsojumi beidzas
- 25 aktīvi profili ar pēdējo nodoto balsi < 2026-09-01 (pēdējā sēde 10-08) saņem teikumu zem «Balsojumu ieraksti»: 12 ministri (mandāts nolikts), 5 cits amats (prezidents, EP, Rīgas dome), 8 pagaidu deputāti. Dati `data/bio/saeima_mandats.yaml`, 25/25 pārbaudīti pret titania.saeima.lv (3 izpētes aģenti + paraugpārbaude Dombrava/Rinkēvičs/Kols).
- `since` = Saeimas puses datums (ministri amatā 05-28, mandātu nolika 06-04…06-18), teikumi dzimtes neitrāli. Sargs `load_mandate_notes()` (`src/render/bio.py`): nodota balss pēc `since` → teikums slēpts + stderr; ja sarga vaicājums krīt — neviena teikuma.
- Testi `tests/test_profile_mandate_note.py` (2, sargs pierādīts ar mutāciju); baseline REGEN 3 lapas. check.sh 3460 passed. Deploy `946353e7` (`67cf7c69`), `verify_host` 9/9, live Dombrava/Rinkēvičs/Circene.

## 2026-10-09 (8) — Profila Pārskats: «Balso kopā ar savu frakciju»
- Deputāta Par/Pret/Atturas pret pārējo TĀ balsojuma frakcijas (T6) deputātu biežāko balsi; pats neskaitās; < 3 citi, neizšķirts, ārpusfrakciju rinda → izkrīt; logs `CURRENT_TERM_START`; bloks ar ≥ 20 balsojumiem. Procedūras balsojumi NAV izslēgti (A/B atšķirība < 0,2 pp); `pct` = floor (round 19 deputātiem rādītu «100 %» ar nesakritībām).
- `faction_alignment_data(db)` (`src/render/_common/enrich.py`) vienreiz visiem, ~4 s (per-pid būtu ~60 s); 139 deputāti ar ≥ 20, bloks 122 lapās. Patmalnieks 96 % (7 258 no 7 520).
- Testi `test_render_politicians_parskats.py::test_faction_alignment_*` + e2e; 5 mutācijas — katra krīt. Blakus: `vote_alignment_data` izlaiž `politician_id IS NULL`. Deploy `70a6d0ae`, `verify_host` 9/9.

## 2026-10-09 (7) — Personas: 4 metriku kolonnas visām kartītēm; partiju grupēšana atlikta
- Ne-balsotājam «bals.» šūna = «—» (nav attiecināms, ne «0»), `.pnv1-card-stats` `repeat(4, 1fr)`: 1280 px šūnu x nobīdes 16/84/152/220 visām 6 pārbaudītajām kartītēm (agrāk Braže 3 šūnas pret 4); `scrollWidth` 1280/360. Deploy `52d54ab0`, `verify_host` 9/9, live 131 «— bals.» šūnas. Tests `test_every_card_has_four_stat_slots` (krita pirms).
- Partiju rail grupēšana pēc koalīcijas ieviesta un izņemta — operators: atlikt līdz 15. Saeimas pārslēgšanai (`backlog/vietne-ui.md`). Iniciāļu punkts slēgts: 253/253 foto, visi atšķirīgi.

## 2026-10-09 (6) — Viena balsojuma lēmumi: «Pieņemts» = galīgs; procedūra atdalīta
- Deploy `4a120c9c` (operators «jā»), `verify_host` 9/9; live 939/953/Lm14 «pieņemts», 1104/Lm14 «procesā». Operators: atteikta iekļaušana darba kārtībā = `noraidīts` (backlog (e1) slēgts).
- `_SINGLE_VOTE_FINAL` = `tiesneša_amats`, `Lm14 cits`: «Pieņemts» → `pieņemts` (33 tiesneši + 38 lēmumi, `1d8c1adf`, `b62c6b40`). Pirms tam klasifikators: teikuma sākuma «Par nodošanu … komisijai» → `iesniegts`, «Par iekļaušanu … darba kārtībā» → `procesuāls` (1104/Lm14 «Pieņemts» bija nodošana komisijai, ne lēmums); arī «Par lēmuma projekta … iekļaušanu darba kārtībā» → `procesuāls` (`a16d6966`, 4 posmi, statuss nemainās).
- Audits: 904 posmi ar balsojumu pret jauno klasifikatoru → 7 atšķirības; 6 pārklasificētas (`data/fix_bill_stage_lm_procedural_2026-10-09.sql`), 1488/Lp14 (09-28 rokas labojums) atstāts. Plašāks regex trāpīja 20 — sašaurināts līdz teikuma sākumam.
- Rollback: `rollback_recompute_bill_status_{tiesnesi,lm}_2026-10-09.sql`, `rollback_bill_stage_lm_procedural_2026-10-09.sql`; atkārtots dry run 0. Testi `test_judge_decision_pieņemts_is_final`, `test_decision_pieņemts_is_final_but_referral_is_not` + 2 klasifikatora gadījumi (visi krita pirms labojuma).
- Likumprojekta lapa un Balsojumi: P3 marķieris «Kopsavilkums nav pieejams — historic backfill …» vairs netiek rādīts kā kopsavilkums (20 lapas; `_public_summary`, tests `test_backfill_sentinel_summary_not_shown_on_bill_page`).

## 2026-10-09 (5) — Likumprojekta statuss: «Likums» = pieņemts; Pozīciju kārtošana telefonā 44 px
- Saeimas iznākums «Likums» → `pieņemts` jebkurā lasījumā (steidzamiem — 2.); noteikums vienā vietā `derive_bill_denorm()`, ko lieto `append_bill_stage()` un `scripts/recompute_bill_status.py` (inv. #12 izņēmums). Tests `test_likums_result_marks_adopted_in_any_reading` (pirms labojuma krita).
- Pārrēķins: 72/540 likumprojekti (65 Likums, 3 noraidīts→procesā, 4 posma nosaukums), `last_updated_at` nemainīts; rollback `data/rollback_recompute_bill_status_2026-10-09.sql`; atkārtots dry run 0. Atvērtais — `backlog/saeima.md` (d), (e).
- `.pzv1-sortbtn`/`-mobile-toggle`/`-chip` ≤600 px ≥44 px kā `pnv1` (izmērīts 360 px: 17→44). Deploy `d846ea9b` (operators «publicē»), `verify_host` 9/9, live 1380/Lp14 «pieņemts».

## 2026-10-09 (4) — Profila Pozīciju tabula telefonā = kartītes
- ≤768 px katra `#claims-table` rinda ir kartīte: tēma + datums augšā, pozīcija ar citātu zem tiem, «Avots» apakšā (tikai CSS; `ppv1.js` tēmu filtrs nemainīts, pārbaudīts 266→45→266 rindas). Iepriekš 360 px datums bija nogriezts un «Avots» aiz ritināšanas.
- «Citāts» pieskāriena laukums ar polsterējumu (42 px), trīsstūris saglabāts. Tests `test_profile_tabs_mobile.py::test_mobile_positions_table_rows_are_cards` (pirms CSS krita: galva redzama). Ekrānuzņēmumi `.scratch/ui-2026-10-09/`.
- Deploy (ar (2)–(4)): `render --only=analizes,politiki` + `deploy.sh --no-delete`, versija `2722e69b`, `verify_host` 9/9; live 360 px: `scrollWidth` 360 profilā un `analizes.html`.

## 2026-10-09 (3) — Profils: citāts Pozīciju cilnē, «Atturas» skaidrojums Saeimā cilnē
- Pozīciju rindā izvēršams «Citāts» (`<details>`, bez JS) ar `claims.quote` VERBATIM — pilns, escapēts, bez pēdiņu ietinuma; bez citāta kontroles nav. 7831 no 9140 pozīcijām ir citāts (vaicājums uz `claims`, `claim_type='position'`).
- Saeimā cilnē piezīme: «Atturas» nav neitrāla balss, lēmumam vajag klātesošo vairākumu; badge `title`. Vērtība nemainīta. Motīvs griezts uz vārda robežas (`truncate`), ne 80. zīmē.
- Tests `tests/test_profile_positions_quote.py` (pirms labojuma krita); `render_baseline_politicians.json` REGEN (8 lapas). Plāns `docs/plans/2026-07-26-profila-ux-tier2.md` § Statuss. Pārskata balsojumu bloks atlikts — 15. Saeimai vēl nav balsojumu.

## 2026-10-09 (2) — `analizes.html` telefonā: dienas pārskatu kartītes teksts pilnā platumā
- ≤480 px `.daily-card` pārlaužas: attēls + datums augšā, virsraksts un apraksts nākamajā rindā (`assets/style.css`). Iepriekš virsrakstam palika ~81 px — vārds rindā, «kiberuzbrukuma» izspieda lapu par 15 px (09-23 atradums; vainīgā nebija `.pagehead-tabs`).
- Playwright: `scrollWidth` = ekrāna platums pie 360/390/480/768/1280; datora izskats nemainīts (ekrānuzņēmums 1280).

## 2026-10-09 (1) — Dienas pārskata Pretrunu šūna = izvilkums + saite uz pretrunas lapu
- Dienas `## Pretrunas` «Apraksts» tagad ir ≤50 vārdu izvilkums ar «…» un saiti «pilnā pretruna» uz `/pretrunas/<id>.html`, kā nedēļas pārskatā kopš 09-27; avotu kolonna nemainīta. Helperis pārdēvēts `weekly_contradiction_excerpt` → `contradiction_excerpt` (`src/briefs.py`).
- 2026-06-10 «negriezt» noteikums paliek pārējām dienas tabulām; pretrunām pilnais teksts ir savā lapā. Publicētie pārskati nav pārrakstīti.
- Tests `test_briefs.py::TestPretrunasSection::test_pretrunas_cell_is_excerpt_with_page_link` — pirms labojuma krita (0 rindu ar saiti).

## 2026-10-08 (14) — CSS mobilās sīkās lietas (good-css.com)
- `3f32027f`: skārienierīcēs ievadlauki 16px (iOS vairs nepietuvina meklēšanu); gluda ritināšana + `@view-transition` lapu pāreja tikai bez «samazināt kustību»; `text-wrap: pretty`/`balance`; `100svh`; `touch-action: manipulation`. Dators nemainās (sākumlapas meklēšana 14,7px), mobilā pārbaudīts Playwright 390px (sākumlapa, `personas.html`, profils). Deploy `4e979c3b`, `verify_host` 9/9.
- Atlikts: `:hover` tikai `(hover: hover)` ierīcēm (186 noteikumi), tap-highlight noņemšana (vajag `:active` stāvokļus — ir 2), globāls `:target` `scroll-margin-top`.

## 2026-10-08 (13) — VAD neskaidrās: Jenzis 14 + Žuravļevs 1 ielādēti, Ijabs 1 izņemts, Burovs apstiprināts svešs; `vad-2026.md` kopsummas
- Ģimenes/amatu paraksts no VID detaļām (`scripts/vad_peek.py`, tikai lasa): Jenzis 14 LLU/LBTU rindas — tie paši viesnīcu uzņēmumi, Inčukalna garāža, ģimene = 2020 RTAB; Žuravļevs CSP 2025 — «Austošā Saule» amats, tā pati ģimene. Burovs «Rīgas satiksme» — ģimene Šaburova/Rostova ≠ Burova (paliek denylist).
- Glabātās: Ijabs id 1838 (2002 «Automehāniķis», šofera alga + NBS) izņemts, denylist +1; «Senators» 2010–2013 — paša (Politologu biedrība, LU, Sigulda). Zemmers post-year — paša (Limbažu NĪ). Bērziņš 2006–2011 — 08-12 adjudikācija PIEDER.
- 2822 → 2836 (15/15); rollback `data/rollback_vad_neskaidras_2026-10-08.sql`. Deploy `c167d4d6`, `verify_host` 9/9.
- `vad-2026.md`: § 1 grupas, § 3 ienākumu sastāvs, § 6b–6d NĪ, § 7 ģimene pārrēķināti (bija novecojuši jau pirms 10-08); rangu tabulas nemainījās. `vad_analysis_numbers.py`: § 1 grupas pēc etiķetes, § 6d top 20.

## 2026-10-08 (12) — VAD resweep: denylist identitātes kāja, +38 deklarācijas, Zīle/Elksniņš; X cilņu secība
- Resweep «166 jaunās» = 101 jau izņemts vārdabrālis (uuid kājas klusi mirušas) → denylist kāja `identity` (etiķete + iestāde + amats); 150 ierakstiem atjaunota, +7 jauni (`d028a392`, tests redzēts krītam). Triāža: `docs/audits/2026-10-08-vad-resweep-triaza/`.
- Ielāde `ingest_vad_declarations.py --pids` (jauns karogs) 28 pid: 38/38. Zīle id 3053 izņemts (ģimenē «KINTIJA ZĪLE, māte»), Elksniņa 2 VP 2004 rindas atjaunotas (paša 2005 deklarācijā tās pašas pārvaldes pabalsts). Kopā 2783 → 2822; rollback `data/rollback_vad_{resweep_load,zile_elksnins}_2026-10-08.sql`.
- `vad-2026.md` kopskaits 2776/201 → 2822/202; salīdzinātas tikai rangu tabulas (kopsummu tabulas bija novecojušas — labots (13)), `audit_vad_profile_match` [OK].
- X: cilnes «Tikai ieraksti» → «Tikai pieminējumi» → «Visi»; jebkura filtra maiņa (arī «Pieminētākie») atgriež «Tikai ieraksti» (`2aa89f34`, aizstāj (11)).
- Deploy `929e687c`, `31380b55`, `d01bea7c`; neskaidrās — (13).

## 2026-10-08 (11) — X lapa noklusējumā «Tikai ieraksti»; 42 X konti no grok saraksta
- `x.html` atveras ar «Tikai ieraksti» (`c5b3b2d6`); «Visi» — `?tips=visi`, pieminējumi — `?tips=mention`. «Pieminētākie» klikšķis pārslēdza uz «Visi» (aizstāts ar (12)). Profila «Pieminēts X» saite sūtīja `tab=mentions`, ko JS nelasa — labots.
- 42 politiķiem `x_handle` + `social_accounts` first_party (grok saraksts 44; katrs pārbaudīts dzīvi X — eksistē, bio/tvīti atbilst): `data/seed_x_handles_grok_{40,2}_2026-10-08.sql` + rollback. NEpievieno: `@J_Urbanovics` (parodija), `@Robertskipurs` (tikai botu ieraksti) — operators 10-08.

## 2026-10-08 (10) — VAD deklarācijas identitāte = etiķete + amats + iestāde (wrap, dedup, ģenerators)
- Lapošanas wrap-detekcija pēc satura, ne rotējošā `vad_uuid` (`cddce746`): Brencis 212 → 53 rindas (10-05 dry-run, 53 × 4 cikls). Ģenerators § 5/§ 6 skaita ar `src/render/vad.py::latest_annual_counts()` tāpat kā profils (`audit_vad_profile_match`: § 5 10/10, § 6 15/15).
- `fetch_for_politician` dedup: atslēga `(kind, year, amats)`, kurā bezgada deklarācijām `year=NULL`, aizstāta ar `src.vad.fetch.declaration_identity()`; tukša glabātā iestāde der kā atbilstība; `vad_uuid` atsvaidzināts pēc rindas `id`. Vecā atslēga izlaida 34/1 136 deklarācijas (10-05 dry-run; Jenzis 24 → 10).
- Neizšķiramās rindas skaita `rows_ambiguous`/`rows_duplicate_label`; ja `rows_found` ≠ iznākumu summai, brīdinājums `vad-accounting-mismatch`. Noteikums: `wiki/operations/operacijas.md` § VID deklarācijas.
- Testi `tests/test_vad_declarations.py` (3 dedup + resweep skripta tests) redzēti krītam; 6 mutācijas noķertas. Iztrūkstošo ielāde — `backlog/vad.md` [OPERATOR] (`scripts/vad_resweep_dryrun.py`, tikai lasa).

## 2026-10-08 (9) — Netiešās atsauces vārti: «tikai pieminē/minē» tikai pie paša politiķa
- `src/analyze.py::_indirect_marker_in(reasoning, politician_name)`: šie divi marķieri skaitās tikai tad, ja to teikuma daļā ir pats politiķis (vārda celms), vietniekvārds vai amata vārds, vai arī teikuma priekšmets nav nosaukts. Neskaitās: frāze pēdiņās, cits dokuments («Doc 85859»), cits personvārds, lietvārds kā priekšmets («sižets»). Bez vārda — vecā uzvedība. `save_analysis` padod `tracked_politicians.name`.
- Saucējs: prod (tikai lasīšana) 8894 `position` claims; šie marķieri pēc saglabātā `reasoning` 6 → 0 (visi 6 bija viltus pozitīvi vai paša vārtu citāts); 2 citi marķieri nemainīti.
- Testi `tests/test_analyze.py::TestIndirectReferenceGate` (5 FP formas + TP formas, `save_analysis` caur pid) redzēti krītam; 8 mutācijas, katru noķer vismaz viens tests. Backlog `[FIX]` slēgts.

## 2026-10-08 (8) — Operators «ok» trim ieteikumiem: īpašvārdu migrācija, FP7, deploy
- Īpašvārdu reģistra migrācija piemērota: 255 668 `saeima_vote` stance / 2928 balsojumi; atkārtots dry-run `claims_planned: 0`, `stance GLOB '*: ministru kabineta*'` → 0. Rollback `data/rollback_saeima_stance_propnoun_case_2026-10-08.sql` (commitots pirms apply).
- FP7: pretrunas #37/#41 (Kulbergs, Rail Baltica) `reversal` → `minor_shift` — nostājas maiņa sakrīt ar lomas maiņu; noteikums `contradiction-hunter.md` FP7. Rollback `data/rollback_fp7_kulbergs_37_41_2026-10-08.sql`. 05-25 pārskata teksts nemainīts (vēsturisks), sintēzes etiķete labota.
- Pilns renders + deploy `e0ce83ff` (preflight tīrs, 1161 lapa); live 200: Ijabs EP avots, Kulberga Saites piezīme, #37/#41 «Neliela novirze».

## 2026-10-08 (7) — Profili: Saites kopskaits, tukšie profili, «Pēdējā aktivitāte», EP deputātu bio
- Saites cilne skaita visas spriedzes (tas pats predikāts bez LIMIT), saraksts paliek 20 jaunākās + piezīme «Rādīti jaunākie N no M…». 33 profili bez pozīcijām/balsojumiem atveras uz Publikācijām, nulles cilnes slēptas. «Pēdējā aktivitāte» balsojumam = sēdes dienas rinda (T14), ne viena motīva teksts.
- `data/bio/ep_deputati.yaml`: 7 EP deputāti, dzimšanas gads visiem, izglītība 3 (Kols, Staķis, Vaidere; pārējiem EP lapā CV «nav pieejams»), avots europarl. `derive_profile_kind`: «EP deputāta palīgs» (Mežals) vairs nav `mep`.
- Testi redzēti krītam: `tests/test_profile_activity.py` (3), `tests/test_bio.py::test_mep_bio_from_europarl_file_with_source_link`, `tests/test_profile_kind.py`. Baseline `render_baseline_politicians.json` pārģenerēts (tikai atstarpes 10 lapās).

## 2026-10-08 (6) — Kolektīvo iesniegumu polaritāte ielādē + īpašvārdu reģistrs stance
- `src/saeima/petitions.py`: `petition_decision_verb()` nolasa «nolemj:» darbības vārdu; `generate_claims_from_votes(petition_decision=)` žurnalē `saeima_petition_decision|polarity`; Step 5 vārti `petition_votes_polarity()` (saeima-tracker.md, saeima-ingest.md 2.a2). Pār DB: 89 lēmuma balsojumi, 3 `rejection_wording` → salaboti (218, 2105, 4387; 271 stance; rollback `data/rollback_kolektivie_iesniegumi_polaritate_3_2026-10-08.sql`).
- `stance_summary_case()`: īpašvārdu sākumi (saraksts, apzināti konservatīvs) paliek ar lielo burtu. Vēsturiskā migrācija `scripts/fix_saeima_stance_propnoun_case.py` gatava (dry-run uz kopijas: 2928 balsojumi / 255 668 stance, apply+rollback checksum sakrīt) — NAV palaista, gaida operatoru.
- Testi `tests/test_saeima_petitions.py`, `tests/test_saeima.py` redzēti krītam (4 mutācijas).

## 2026-10-08 (5) — `saeima.html`: 15. Saeimas pusloks (operators: «piekrītu», deploy atļauts)
- Jauna lapa: 100 sēdvietas, 4 lēcas (Saraksts, Balsoja 14. Saeimā, Pozīcijas 90 d, Pretrunas), kartīte (desktop panelis / mobilais bottom sheet), saraksts ar `<details>`. Spec `docs/superpowers/specs/2026-10-08-saeimas-pusloks-design.md`.
- Sasaiste tikai precīzs pilnais vārds (T1); render KRĪT, ja sastāvā ≠ 100 vai saraksta nr. nav rezultātu failā. Mērīts render izvadē: `sēdvietas=100 izsekoti=98 bez_profila=2`, balsoja 14. Saeimā 41/100.
- Izvēlne: «Saeima» aizstāj «Tēmas» augšējā joslā, «Tēmas» → «Vairāk». Koalīcija un frakcijas disciplīna atliktas līdz vārtiem C / LIVS15 balsojumiem.
- Tests `tests/test_render_saeima.py` redzēts krītam (3 mutācijas); JS `assets/slv1.js`. Commit 9d7817e9, deploy 1bbc8ef9 (live 200, konsolē 0 kļūdu).

## 2026-10-08 (4) — Krastiņas (239) `negative_patterns` + Imants Krastiņš (operators: «ok»)
- 4 formas (Imants/Imanta/Imantam/Imantu Krastiņ…); forma «Krastiņa» ⊂ «Krastiņam» piesaistīja doc 127450. Pārbaude ar `match_politicians` pār 4 korpusa dokiem ar «Imant…Krastiņ»: 127394/127450 → 239 vairs nesaista, 91773 (īsta saite) paliek. Rollback `data/rollback_krastina_negative_patterns_imants_2026-10-08.sql`.

## 2026-10-08 (3) — indekss `documents(source_url)` (operators: «jā»)
- Indeksa nebija: katra `insert_document()` URL pārbaude pārlasīja visas 115 323 rindas. Mērīts uz dzīvās DB (`_find_web_doc_by_url` pār 20 jaunākajiem web URL): 185 ms → 0,09 ms vienam meklējumam; DB 2 731,7 → 2 739,4 MB; būve 0,4 s. Ne-unikāls (9 utm dublikātu grupas).
- `schema.sql` + `db_migrations.py`; `_find_web_doc_by_url` `substr` aizstāts ar diapazonu (`base?` ≤ url < `base@`), plāns `MULTI-INDEX OR`. Tests `test_url_lookup_uses_an_index_not_a_table_scan` redzēts krītam (SCAN).
- Rakstīšanas cena nav mērīta dzīvajā DB; analogs `idx_claims_source_url` 2026-08-03: +~10 % rindai. Rollback `data/rollback_documents_source_url_index_2026-10-08.sql` (atsauc arī kodu, citādi `init_db()` indeksu atjauno).

## 2026-10-08 (2) — ≤10 ekstrakcijas aģenti kārtā; `utm_*` URL dedup; Baško pāris
- `plan_extraction_batches(max_agents=10)`: 10-07 kārtā 19 aģenti (katrs ielādē embedding modeli) → atmiņas trūkums; pārpalikums pāriet uz nākamo kārtu, viens pid kārtā vienreiz, RT pēdējās. Tests `test_max_agents_caps_every_round` redzēts krītam (2 mutācijas).
- `insert_document`: `normalize_source_url()` nomet `utm_*`; meklēšana atrod arī ~5 000 vecās rindas ar `utm` URL, to `source_url` nepārraksta (Data Contract #3). Testi `test_normalize_source_url`, `test_utm_variant_*` redzēti krītam.
- 9 esošās utm dublikātu grupas (vaicājums: `documents.source_url` grupēts pēc normalizētā URL) atstātas: nevienā nav vienas pozīcijas divreiz.
- Baško pāris (30, 126284): claim 730811, 0 pretrunu; Krusts — `empty_doc_ids`. «Imant» paterni Krastiņai sagatavoti, NAV piemēroti (`data/fix_krastina_negative_patterns_imants_2026-10-08.sql`).

## 2026-10-08 — 10-07 NEEDS_REVIEW triāža (17 → 0); viltus junction, claim 20597 un wiki saite labotas
- Operators («dari visu») pieņēma advisor ieteikumus: 9 izvērtēti, 3 izvērtēti + stance precizēts (730744, 730748, 730806; re-embed), 6 dzēsti — 730745 (bez satura), 730759/730760 (svinīgs/rituāls ierāmējums, kā 10-06), 730774 (sarkasms bez tēmas), 730810 (nenosaukta «politika»), 730773 (tā pati klase kā 10-06 dzēstais 725157). Rollback `data/rollback_needs_review_triage_2026-10-08.sql`; tvīti X cilnē paliek.
- Junction 127450 → Maija Krastiņa dzēsts (Imants Krastiņš, T1); claim 20597 (Švinka) stance + citāts izlabots; rollback `data/rollback_junction_claim_fix_2026-10-08.sql`.
- `src/wiki_pages.py`: spriedze uz `inactive` politiķi bez `persons/…` saites (tam lapas nav); tests `test_render_tensions_inactive_target_has_no_link` redzēts krītam; wiki lint broken 1 → 0.
- Deploy 8ca03f97 (profili, pozīcijas, tēmas); pārskats #685 netika mainīts.

## 2026-10-07 (10) — Dienas rutīna: pretrunas #52/#54 publicētas, 7 kandidāti noraidīti (operators)
- Operators publicēja #52 (Kulbergs, LPV, neliela novirze) un #54 (Kulbergs, «Netflix» nodeva, apvērsums); rollback `data/rollback_publish_contradictions_52_54_2026-10-07.sql`.
- Izvērtēti un NOraidīti publicēšanai (paliek `confirmed=0, reviewed=1` — neatvērt atkārtoti): #40 (formulējums starp lasījumiem), #47 (DA noraidīts), #48 (atstāstīts valdības lēmums), #49 (procesuāls balsojums, T14), #50 (atklātības robeža, ne nostāja), #51 (kodols nemainīts), #55 (AS toņa maiņa — ziņa, ne pretruna).
- Hermanis (pid 29) role → «Ierindas biedrs» (T6); Tavara 730724/730725 pie 0,65 paliek bez marķiera (ārpus 0,5–0,6 joslas); rollback `data/rollback_rutina_labojumi_2026-10-07.sql`.
- Pārskats #685 publicēts (deploy 8ec39cc1); 87 pozīcijas (170/170 plāna pāri + 42 atgūšanas), 17 NEEDS_REVIEW operatora rindā.

## 2026-10-07 (9) — Profila lapa pārzīmēta; personu grupas bez «Amatpersonas»; ministra noteikums precizēts
- Profils (`templates/politician.html.j2`, plāns `docs/plans/2026-10-07-profilu-dizains.md`): serif hero, teksta cilnes, skaitļu josla pēc `profile_kind` (nulles slēptas), vienots aktivitātes avots `_fetch_activity_timeline` — balsojumi sakļauti pa sēdes dienām (T14), + uzstāšanās un jautājumi; mēnešu SVG grafiks bez balsojumiem. Viss esošais saturs paliek. Publikāciju cilnes skaitlis = reālie kopskaiti (`pub_totals`), ne sarakstu griesti (bija 51 pret 498).
- Personas: «Amatpersonas» → Valdība / EP deputāti / Pašvaldības / Citi politiķi no `derive_profile_kind`. Strādājošs ministrs → Valdība PIRMS Deputāti (mandāts uz amata laiku nolikts). Reālā DB pēc 15. Saeimas karoga: Deputāti 165, Valdība 14, Citi politiķi 26, Pašvaldības 11, EP 7; Valsts prezidents → Citi politiķi (`_fetch_personas` + `_apply_saeima15`).
- `derive_profile_kind`: «ministr» vairs neskaita padomniekus, parl. sekretārus, amata kandidātus; «atkāpies/demisionējis/atbrīvots» → `former` (`tests/test_profile_kind.py`, mutācija: 4 krīt).

## 2026-10-07 (8) — Visiem Saeimas balsojumiem ir kopsavilkums (382 pēdējie); īpašvārdu mazā burta defekts atklāts
- 382 atlikušie: 227 klātbūtne (kanoniskā frāze), 122 procedurāli + 33 priekšlikumi (3 Opus `@saeima-tracker`, `data/saeima_summaries_drafts_2026-10-07b/`). Apply: 382 summary + 13 589 stance, rollback `data/rollback_saeima_summaries_2026-10-07b.sql`. Pēc tam `summary` tukšs 0, «Balsoja PAR: <motif>» stance 0.
- 5 objekti, kas noteikti pēc laika (7062, 7494, 7111, 7287, 6686), pārbaudīti pret kaimiņu balsojumiem `vote_time` secībā — visi starp tā paša `document_nr` balsojumiem.
- Advisor: ģenerators pārvērš īpašvārdu kopsavilkuma sākumā mazajā burtā. Šodienas 33 pārfrāzēti (24 jau DB → 2 106 stance; rollback `data/rollback_saeima_summaries_propnoun_2026-10-07.sql`). Vēsturiskie 2006 balsojumi / 175 684 claims → `backlog/saeima.md` [FIX]; noteikums `saeima-tracker.md` 3.B.
- Precizējums: `saeima_vote` stance profilos NErenderējas (cilne rāda `motif`); redzams ir `summary` balsojumu matricā un stance tikai «vārdi pret darbiem» pretrunu lapās (5, neviena nav skarta). Šodienas stance darbs uzlabo pretrunu meklēšanu, ne profilus.

## 2026-10-07 (7) — 126 Saeimas balsojumiem kopsavilkumi; vēl 10 apgriezti kolektīvo iesniegumu balsojumi
- 126 būtiski balsojumi (2025-01…2026-08) bez `summary` → 3 Opus `@saeima-tracker` melnraksti (`data/saeima_summaries_drafts_2026-10-07/`), `scripts/apply_saeima_summaries_2026-09-02.py --drafts-glob` (vārti OK): 126 summary + 10 618 stance; rollback `data/rollback_saeima_summaries_2026-10-07.sql`. Paliek 382 bez summary: 227 klātbūtne, 122 procedurāli, 33 priekšlikumi (13 589 «Balsoja PAR: <motif>» stance).
- Visu 90 kolektīvo iesniegumu lēmumprojekti nolasīti (`.scratch/petitions/read_drafts.py`): vēl 10 ar «noraidīt»/«atstāt bez virzības», bet summary «virzīts tālāk» (25, 26, 121, 124, 190, 220, 362, 364, 514, 717/Lm14) → «Komisijas priekšlikums …», 852 stance; rollback `data/rollback_kolektivie_iesniegumi_polaritate_2_2026-10-07.sql`. Pretrunas uz tiem: 0.
- 6359/6360 (neuzticība Siliņai 05.02, 0:46:1, 34 nebalsoja) NAV datu kļūda — opozīcija norāva kvorumu (LSM 05.02.2026).

## 2026-10-07 (6) — Kolektīvo iesniegumu balsojumu polaritāte; pretrunas #10/#11 (Armaņeva) atsauktas
- 936/937/Lm14 lēmumprojekti skan «noraidīt»; Armaņeva balsoja pret noraidīšanu = iesnieguma pusē, tātad «saka vienu, balso otrādi» nebija. Balsojumu 14/19 summary → «Komisijas priekšlikums noraidīt …», 167 stance pārrakstīti (prefikss nemainīts); 7514 nepamatots «noraidīts» → neitrāls (87 stance). #10/#11 `withdraw_contradiction()`.
- Pārbaudīti lēmumprojekti 855/973/219/526/Lm14 — «nodot», pareizi. Atlikušie ~90 + ielādes labojums → `backlog/saeima.md` [FIX]. Rollback `data/rollback_kolektivie_iesniegumi_polaritate_2026-10-07.sql`.
- Operators: #29/#30 (Siliņa) atstāt; #37/#41 (Kulbergs) atstāti — «Nostājas maiņa» burtiski precīza, #41 summary nosauc lomas maiņu.

## 2026-10-07 (5) — Pretruna #33 (Šuvajevs) pazemināta uz «Neliela novirze» pēc lasītāja iebilduma
- Reddit r/latvia lasītājs: aprīļa vērtējums par valdības darbaspēju un maija kritika pēc Sprūda krīzes ir pārvērtējums mainīgā situācijā, ne pretruna. Mūsu rubrika (`.claude/agents/contradiction-hunter.md`:69-70) to pašu saka: liels notikums starplaikā → `minor_shift`.
- `severity` reversal → minor_shift, summary teikums pārrakstīts; rollback `data/rollback_contradiction_33_2026-10-07.sql`. Renderētā `pretrunas/33.html` rāda «Neliela novirze».
- Pārējās 12 publicētās stiprās pretrunas pārbaudītas ar to pašu testu. Operators: #32 (Indriksone, prognoze pirms Sprūda krīzes) → `minor_shift` (rollback `data/rollback_contradiction_32_2026-10-07.sql`); #17 un #38 NEatsaukt (operatora lēmums, atsaukums atjaunots pirms deploy). Atvērti operatoram: #29/#30 (pašas izraisīts notikums), #37/#41 (lomas maiņa), #10/#11 (balsojumu ķēde).

## 2026-10-07 (4) — VAD analīze pārrēķināta visa: 2776 deklarācijas / 201 politiķis (bija 2238/159)
- § 1–4, § 5b–c, § 6b–e, § 7: `scripts/vad_analysis_numbers.py --year 2025` (2025 ikgadējo 164 ≥ 2024. g. 142); § 1 veidi pēc `vad.declaration_label()` (kods `interim` = stāšanās 130 + atstāšana 74, «starpposma» nebija). § 2 jauni Putniņš, V. Stepaņenko; § 4 Biķe, Kraps, Džeriņš; ministru alga galvenais avots 6/15 (bija 7). Melnalksnim dāvinājumi 31 000 € no 4 ģimenes locekļiem (lapā bija 21 000/2).
- § 5/§ 6 no `src.render.vad.get_vad_data_for_politicians` (kopš `ed608159` delta pret hronoloģiski iepriekšējo deklarāciju, arī stāšanās): Treija 5→3 un ārpus desmitnieka (vienāds 3/0/3 ar Brēmani, Pucenu — kārto pēc uzvārda); V. Stepaņenko NĪ 19, ne 26. Ģenerators un `compute_vad_profile_counts.py` joprojām `ORDER BY COALESCE(declaration_year,0)` → atvērts. Teksts: multiset (kopš `73cb9f35`), ne «unikāli».
- Vārti: `audit_vad_profile_match.py --skip-render` § 5/§ 6 25/25 OK, bet § 2/§ 4 35/35 «actual=0» — audits akls pret jauno profila formātu (`ed608159`/`a9c402b8`: cilnei nav `annual` span, viena `<td>`, «25 430,44 €»); ar jaunā formāta skripta pārbaudi 35/35 sakrīt (mutācija redzēta krītam). Audits NAV labots — operatora lēmums.

## 2026-10-07 (3) — VAD analīze: ārvalstu īpašumi sadalīti «pieder» / «īrē vai lieto»
- `content/analizes/vad-2026.md` § 6e: 69 ieraksti, 9 politiķi (`scripts/vad_analysis_numbers.py` § 6e; agrāk 53/6). Vecā tabula Kola un Zīles nomu un Melbārdes lietošanu Briselē rādīja kā īpašumu; tagad statuss = VID vārds, gadi = iesniegšanas gads. Katrs jaunais ieraksts salīdzināts ar `raw_html`.
- Ģenerators § 6e drukā `ownership_status` un `submitted_at` gadu (start/interim/post rindām `declaration_year` ir NULL → agrāk «?–?»).
- Pārējās sadaļas NAV pārrēķinātas: lapā 2238/159, DB 2776/201; audits `audit_vad_profile_match.py` → 1 nesakritība § 5 (Treija, uzņēmumi 5 pret 3).

## 2026-10-07 (2) — Profili: Saeimā cilne pēc datiem, ne lomas; deklarācijas latviski; telefonā cilņu režģis (operatora «dari tā»)
- **Vārti:** Saeimā cilne un Saites balsojumu sakritība — `has_saeima_content` / balsojumu esamība, ne `profile_kind` (loma «ministr…» uzvar balsojumus → 10 deputāti bija bez cilnes, Šuvajevam 701 balsojums kopš 06-01). Kind kārtība NEmainīta. Tests `tests/test_profile_saeima_tab_minister.py` (3 mutācijas).
- **Klātbūtne nav balsojums (DC 4b):** `Reģistrējies`/`Nereģistrējies` izslēgti no profila saraksta, skaita, datumu loga un laika līnijas (`_NOT_ATTENDANCE_SQL`); laika līnijas cilnē reālais kopskaits, ne `LIMIT 50`.
- **Deklarācijas:** `vad.declaration_label()` no VID teksta (`interim` kods nozīmē gan stāšanos, gan beigšanu), hronoloģiski, «vēl N»; `lv_money` «80 000,00 €»; `payer_name()` bez reģ. nr./adreses, personas kodi slēpti; «vairs nav», «Bankā/Skaidrā naudā», «summa:». Testi `tests/test_vad_render.py`, `test_vad_diff.py`.
- **Telefonā** (≤600 px) profila cilnes režģī pa 4 — ritināmā josla nogrieza pirmo cilni. Commits `ed608159`, `a9c402b8`; deploy `f0ec4985`. Atlikums: Publikāciju/Saišu cilņu skaitļi no griestotiem sarakstiem (`backlog/vietne-ui.md`).

## 2026-10-07 — Pārskata kājene skaita redzamās pozīcijas; `approve_publish` atsaka bloku tabulas nesakritību
- #682 kājene rādīja DIENAS STATS marķiera 79, tabulās 72 (7 NEEDS_REVIEW rindas izņemtas ar roku). Kājene tagad = `count_brief_position_rows()` (tēmu tabulu rindas ar avotu), marķieris tikai fallback; maina ~87 vecu pārskatu kājenes (operators: atstāt). `approve_publish.py` atsaka dienas pārskatu, ja rindas ≠ bloku tabulas summa (#672: 47/48). Commit `8169b151`; brief-writer.md +1 rinda.

## 2026-10-06 (2) — Saeimas aktivitāte: amati, debašu runātāji, deputātu jautājumi (operatora «jā» trim avotiem)
- **Avoti:** titania `Saeima{N}_DepWeb_Public` (amati ar datumiem; DG draudzības grupas apzināti NEglabā), data.gov.lv `saeimas-sedes` `-deb`+`-dkp` (CC0; runātājs, ilgums, dokuments — priekšlikumu runām numurs no vecākpunkta vai nosaukuma), titania `SaeimaLIVS_LmP` jautājumi/pieprasījumi (iesniedzēji + adresāti, bez PDF). `src/saeima/activity.py`, 4 tabulas `src/saeima/schema.py`, `scripts/ingest_saeima_activity.py` (nedēļas rutīna); plāns `docs/plans/2026-10-06-saeimas-aktivitate.md`.
- **Lēmumi (advisor):** `DEBATE_OPINION` NAV nostāja (aizpildīts 16/78 un 0/384) — glabā, nerāda, pretrunām nelieto; vārdi tikai precīzi (bez apakšvirknes, T1); `tracked_politicians.role` netiek rakstīts (T6); `bill_id` netiek likts (#12). Debašu atslēga `(session_name, dkp_id, speaker_order)` — vecā `(dkp_id, speaker_order)` klusi nometa 2 runas pārnestā punktā (`data/fix_saeima_debate_key_2026-10-06.sql`).
- **14. Saeimas ielāde:** amati 1053 (0 nesaskaņotu), jautājumi 401 / saites 3281 (15 neizsekotu adresātu — bijušie ministri), debates 9262 runas (160 runātāji; 51 bez dokumenta numura; 20 avota atkārtojumi izlaisti). Rollback `data/rollback_saeima_activity_backfill_2026-10-06.sql`. Renders: 3 bloki Saeimas cilnē (`src/render/politicians.py`), tests `tests/test_render_saeima_activity.py`.

## 2026-10-06 — Profila bildes tikai īsts JPEG; partiju nosaukumi latviskā reģistrā; deploy runbook bez rsync
- **Bildes:** `scripts/fetch_profile_photos.py::_to_jpeg_bytes` pārkodē X avatāru (10-05 Latvijas Banka atnāca kā PNG `.jpg` failā → og-card `data:image/jpeg` salūzt). Sargs `tests/test_profile_photos_jpeg.py` pārbauda visus `assets/photos/*.jpg` (254, magic `FF D8 FF`); abas mutācijas redzētas krītam. `assets/photos/_trukst.md` dzēsts — tika kopēts uz live vietni.
- **Partijas:** `display_name` = `parties.name` (Title Case tikai VISU-LIELO-BURTU nosaukumiem) — kartītes rakstīja «Apvienotais Saraksts», tabula tajā pašā lapā «Apvienotais saraksts»; kartītes pēc 2026. g. balsīm. `coalition_status` NEmainīts — 14. Saeima strādā līdz 15. sanākšanai (`backlog/dati-db.md`). Tests `test_card_names_keep_lv_case_and_order_by_votes` (2 mutācijas), baseline REGEN (as/la/na + indekss).
- **Runbook:** `deploy.md` 343 → 163 rindas; Namecheap/rsync/SSH → `wiki/operations/deploy-namecheap-arhivs.md` (dzēšams pēc Task 9); `atmina-ops.md`, `quality-bars.md`, `profile-photos.md` vairs nesauc deploy par aditīvu. `repo-sync.md` `Users[/\]` bāzlīnija 6 → 0.

## 2026-10-05 (2) — Rutīnas solis «2b» `backlog`: veci neizskatīti pāri vairs neuzkrājas klusi
- **Vārts:** `src/routine.py::stale_extraction_pairs` — `subject` pāri ar `extracted_at IS NULL`, bez claim, `queue_politician_sql()`, `scraped_at` < vakardienas rutīnas dienas sākums; virs `STALE_PAIRS_MAX` = 20 solis ◐ un rutīna nav pabeigta. Bāzlīnija **0** (`stale_extraction_pairs(db, '2026-10-05')`, robeža `2026-10-04 05:00:00`, pēc vēsturiskā sweep `docs/audits/2026-10-05-backlog-sweep/`); Vēstnesis atsevišķi, tikai informācijai. `unreviewed_subject_docs_before` dzēsts (vairs neviens to nelasīja). Mutācija redzēta (bez `extracted_at` nosacījuma krīt `test_extracted_pair_is_not_counted`).
- **Iztukšošana:** `scripts/plan_stale_sweep.py` (gabali ≤12 doku, `sweep_unit.py --plan`), brīfs `wiki/operations/stale-sweep-brief.md`, tikai Opus @claim-extractor; `/seed-entity` 10. solis rāda jaunā pid pāru skaitu.
- **Vēstneša paraksta-pāri:** `src/vestnesis_stamp.py` (rutīnas akta virsraksts + uzvārds tieši vienreiz uzreiz pēc iniciāļa) raksta tikai pāra `extracted_at`, nekad `reviewed_at`. Mērīts 10-05 (`vestnesis_signature_rule_eval.py`): 423 no 851 tukšajiem pāriem noķerti, 0/21 un 0/49 pozīciju pāru kļūdaini; atkārtots pēc sweep — 0 no 90 Vēstneša pozīciju pāriem. CLI `scripts/stamp_vestnesis_signatures.py` (`--apply` tikai ar commitētu rollback), `/dienas-rutina` 1b.

## 2026-10-05 — Matcher: kopīga forma arī pie dažādiem nominatīviem; sadzīves vārdu sargs 5 jauniem deputātiem (operatora «paturēt»)
- **Kopīgā forma:** uzvārda forma, kas pēc locījumu ģenerēšanas pieder ≥2 profiliem, kailā veidā nevienu nepiesaista bez vārda (`src/matcher.py::_load_politician_forms`; vīrieša ģenitīvs «Kleinberga» = Nellijas Kleinbergas nominatīvs). Cena tagad: 6 formas (Bērziņa/u, Kozlovska, Liepiņa/u, Lūsi), 90 d pārmačā 92/566 doki mainītos, 136 saites zustu, 0 claim-segtu (commit e7e616a8 per-doka pārmača; `eval_matcher_collisions` šai izmaiņai nevar nokrist). Pēc seedēšanas zudīs arī Kleinbergs «Kleinberga/u» (59 dok.), Ivanovs «Ivanova/u» (35).
- **`_COMMON_WORD_FORMS`:** Dimants, Ābola, Āboliņš, Dārznieks, Putniņš (+ASCII); Ozoliņš, Lazdiņš, Kārkliņš, Caunītis, Apine, Kraps — bez sarga, ķer T13 audits. Plāns `docs/plans/2026-10-05-15-saeimas-deputati.md`; kohorta `data/seed/15saeima_kohorta.yaml`; vārti B (CVK oficiālais saraksts) vēl ciet.

## 2026-10-01 (8) — VAD: Zalāna (pid=186) 16 vārdabrāļa deklarācijas izņemtas (operatora «jā»)
- Ģimenes-paraksts: Jēkabpils cietuma apsargs (decl 2208–2223) ar pilngadīgu dēlu no 2012 — kandidāts dzimis 1987 → cita persona. Radiosakaru inženieris (2224–2226, cita māte) paliek flagged.
- Purge + rollback `data/{purge,rollback}_vad_zalans_2026-10-01.sql`; denylist 136 → 152 (14 stabili `annual` 2005–2018, 2 uuid). `vad-2026` kopskaits 2254 → 2238 + Zalāna teikums; `audit_vad_profile_match` [OK]; render baseline REGEN (tikai `vad-2026.html`, `analizes.html`). **Deployots** (versija `6f140620`, verify_host 9/9; dzīvē apsarga amatu 0).

## 2026-10-01 (7) — Verdiktu atvērtie jautājumi 1–5 un 9 izpildīti (operatora «yes»)
- **Claims:** 17 atsaukti (15 tvītu stubi bez konteksta, #7040 dublikāts, #6650 līdzjūtība); #7391, #7420, #19 stance pārrakstīta + re-embed; 14 žurnālista teksti kā citāts → `quote=NULL`, #11081 apgriezts līdz burtiskam teikumam. Avota dokumenti paliek (X apakšcilne tos joprojām rāda).
- **Vēstnesis:** 54 «tikai uzvārda» `subject` saites dzēstas (ielas, pagasti, vārdabrāļi), 7 nepārbaudāmas → `suspect_at`; 0 sakritību ar 10 803 rollback pāriem. Paliek 130 `mentioned` lasīšanai.
- Rollback `data/rollback_open_questions_2026-10-01.sql`; slēgti 5–7, atvērts tikai 8 (Zalāns). **Deployots 2026-10-01** (pilns renders, 199 profili; Cloudflare versija `f5fb5177`; verify_host 9/9) — dzīvē arī visas šīs dienas iepriekšējās DB izmaiņas.

## 2026-10-01 (6) — Verdikti 2026-10-01 izpildīti: `subject` noteikums NEieviests, Vēstneša filtrs atgūst parakstītājus, `cross_check` izņemts
- **`subject` tikai ar runātāju — NĒ, izmērīts:** `speaks()` recall 84,3 % (1 492/1 770 claim-ražojoši web pāri), «nomaini, ja runā cits» 93,9 % (< 97 % vārti); runātājus jau atgūst `quoted_speaker.recovery_survey`. Tikai 9 zināmās instances + 384 atturētās rindas kā `mentioned`.
- **`_filter_vestnesis_strict`** paturēja tikai `name_forms` pilnās formas: nogrieza parakstītāju «E. Siliņa» un 30 politiķu (Kulbergs, Siliņa …) pilno vārdu. Tagad kanoniskais vārds + «I. Uzvārds» no `vestnesis.extract_signers` (2 testi, mutācija redzēta; izlase 28/30 pareizi — `docs/audits/2026-10-01-vestnesis-saites-izlase.md`). Dzīvā ielāde ar to vēl NAV bijusi.
- **Izņemts `src/cross_check.py`** (vienīgais izsaucējs bija nedēļas runbook; 56 871 pāris neizskatāmi) → `/deep-check`. Jev paliek tikai `/deep-check` rīks. `sepia_photo` = izvēle, ne noklusējums (19/20 apstiprināto hero ir sepia).
- Dati ar rollback: citāti/stance C1–C7, 396/Lp14 kopsavilkums (183 stances), 17 ASCII + Svirskis formas (eval FP 1, gold 2274). Per-rinda: `docs/verdikti-2026-10-01.md`.

## 2026-10-01 (5) — Testi paralēli (`pytest-xdist`); CLAUDE.md uz pusi; testu masveida dzēšana NĒ (operatora lēmums)
- **Mērījums** (`docs/audits/2026-10-01-testu-segums.md`): 360 testi nesedz Python rindas (tie pārbauda HTML/JS/galvenes — tuvākais E2E), 1 657 pārklājas segumā (robežtesti), 0 tikai-testu moduļu → segums nedod pamatu dzēst; noteikums «dzēš tikai ar mutācijas pierādījumu» paliek.
- **`check.sh`** palaiž pytest ar `-n auto`, ja `xdist` ir instalēts (`CHECK_PYTEST_WORKERS=0` = secīgi): 3281 passed 2 min 08 s pret ~6 min. `tests/conftest.py` pirms katra testa atjauno Windows Proactor cilpu (twikit imports to nomaina; bez tā 26 renderēšanas kļūdas — redzēts).
- **CLAUDE.md** 42 179 → ~22,5 KB (`c95ccd91` + šis): kodā/promptā dzīvojošais → pointeri; `store_tension()` atsaka aprakstu ar jaunu rindu.

## 2026-10-01 (4) — Dokumentu tīrīšana: backlog −26 %, CLAUDE.md −8 % (operatora uzdevums)
- **Mērījums** (LF, `git show c99e0041~1:<f> | wc -c` pret darba koku): `BACKLOG.md` + `backlog/*.md` 160 997 → 118 852 B, 808 → 731 rindas; `CLAUDE.md` 45 981 → 42 179 B. Handoff skaitlis «207 870 B» kļūdaini ieskaitīja `CLAUDE.md` un CR baitus.
- **Izgriezts tikai ar pēdu:** 4 `[IZPILDĪTS]` tēmu ieraksti un 6 § Atliktais rindas (pēdas commit ziņā `c99e0041`). § Ne-darīt 33,7 → 17,9 KB un 5 lielākie tēmu ieraksti saspiesti, ne izgriezti — ierakstu skaits nemainīts; verbatim kopijas `docs/audits/2026-10-01-{ne-darit-pilnais,backlog-narativi}.md`.
- **`CLAUDE.md`:** virsraksti, numerācija, treknie ievadi, enkuri un citētās frāzes nemainīti; pirms-tīrīšanas teksts `git show 196490a6:CLAUDE.md`. Tālākais −4 KB prasītu sadaļu pārbūvi — operatora lēmums.

## 2026-10-01 (3) — Testu vārti: `get_db` piesaistes noplūde (conftest § 5)
- **Sakne:** fikstūra aizvietoja `src.db.get_db` un TIKAI TAD pirmo reizi importēja `src.social` → `src.matcher`/`src.matcher_veto`; to `from src.db import get_db` paturēja aizstājēju visu skrējienu. `test_social.py` pirms `test_matcher.py` → 15 krituši (alfabētiskā secība to slēpa; vecs, pārbaudīts pirms `ffcba51f`).
- **Lēmums:** importi faila augšā (`test_social.py`, `test_subject_role_guards.py`); `tests/conftest.py` § 5 pēc katra testa salabo un krīt, ja kāds `src.*` modulis tur ne-īsto `get_db`. Redzēts krītam uz īstā defekta; `tests/test_get_db_binding_guard.py`; check.sh 3280 passed (`271f3009`).

## 2026-10-01 (2) — Pilns junction pārskenējums: +6 580 pieminējumu rindas (operatora «start the scan»)
- **Pirms tam labots:** `link_politicians_to_documents` projekta konta filtrs strādā uz VISĀM platformām (136 @AtminaLV pavedieni ir `x_mention`); tests krīt ar veco nosacījumu (`b1468a6a`).
- **Sausais skrējiens DB kopijā** (`rescan_all=True`, visi 108 282 doki): +6 970, −0. Ievietotas tikai `mentioned`/`mention_target` — **6 580** rindas (116 127 → 122 707 = plānotais; `data/{fix,rollback}_rescan_mentions_2026-10-01.sql`, rollback kopijā atjauno identisku tabulu). Izlasīti ~40 paraugi pa klasēm.
- **Izslēgts:** 6 agrāk apzināti dzēsti viltus pāri (pārskenējums tos atjaunotu — `data/rollback_*.sql` krustpārbaude) un **384 `subject` rindas** — operatora lēmums (`docs/audits/2026-10-01-rescan-subject-held.json`).
- **Mācība:** pilns `rescan_all` NAV drošs bez krustpārbaudes pret dzēstajiem pāriem — matcher joprojām atrod daļu agrāk dzēsto viltus saišu (piem., 64681 Bērziņš).

## 2026-10-01 — Matcher C: uzvārdi LIELAJIEM BURTIEM + divi @handle labojumi (operatora uzdevums)
- **Lēmums:** forma atbilst arī savam LIELO burtu pierakstam (tikai forma ar ≥5 burtu vārdu; ≤4 burtu tokeni = akronīmi); lielo burtu vārds pirms uzvārda ir vārda signāls tikai tad, ja VISAS atrastās vietas ir lielajiem burtiem; `negative_patterns` strādā arī lielajiem burtiem. @handle skaitās tikai vesels (`@krusts` ≠ `@krusts3`), un ar handle apstiprināts kandidāts nekad nav «tikai kopīgs uzvārds». `scripts/ingest_vestnesis.py` tagad lieto `_filter_vestnesis_strict` (Vēstneša paziņojumos privātpersonu vārdi ir lielajiem burtiem).
- **Pierādījums:** `scripts/eval_matcher_collisions.py` (jauna rinda B2D2HC = produkcija, fidelitāte 932/0): FP 1 (vārti ≤3), gold 2277 (≥1260) — nemainīti. Jauna «caps lane» (pēdējie 40 000 doki, 3621 ar lielo burtu vārdu): +14 saites, −0, visas izlasītas (T18): 11 nepārprotamas, 2 pid 200 «Krustpunktā» (atvērtais T1 jautājums no 09-30), 1 LETA ģenitīvā «LETAS». Silver paraugs (3000): +44 pret B2D2H, 42 — pareizs handle īpašnieks (Hermanis, Melnis, Krusts), −0.
- **Testi:** 9 jauni (`tests/test_matcher.py`), katrs redzēts krītam ar mutāciju. `ingest_vestnesis.py` filtru darbina tikai tests — dzīvas Vēstneša ielādes vēl nav bijis.
- **Vēsture (operatora «jā» tajā pašā dienā):** sausais skrējiens pār 108 282 dokiem → 140 kandidāti, katrs izlasīts: 117 ievietoti kā `mentioned` (`data/{fix,rollback}_caps_handle_junctions_2026-10-01.sql`, rindas 116 010 → 116 127, +117 = plānotais), 13 noraidīti, 10 operatoram. Atskaite `docs/audits/2026-10-01-caps-handle-junction-dryrun.md`.

## Arhīvs (2026-04 — 2026-09-30)

Ieraksti 2026-09-07 — 2026-09-30 (piem., citētie «CHANGELOG 2026-09-24 (2)») dzīvo [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md), iesaldēts 2026-10-09.

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
