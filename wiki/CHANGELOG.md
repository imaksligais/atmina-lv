# atmina — lēmumu žurnāls

Šeit dzīvo **tikai lēmumi un invariantu izmaiņas**: kas izlemts, kāpēc, kad un kur tas dzīvo (commit, fails, tests). Viens ieraksts — **ne vairāk par 5 rindām**.

Šeit **nedzīvo sesiju hronika** — tā ir `git log`. Konkrētas dienas darbu meklē ar `git log --since=2026-09-13 --until=2026-09-15` vai `git log --grep=<atslēgvārds>`; ierakstus, kas agrāk stāvēja šeit kā dienas apraksts, sk. [CHANGELOG-arhivs-2026-09.md](CHANGELOG-arhivs-2026-09.md) § Izlaistie sesiju ieraksti.

Skaitlis bez vaicājuma nav skaitlis: ja ieraksts nes skaitli, tajā pašā rindā stāv arī tā izcelsme.

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
- `_SINGLE_VOTE_FINAL` = `tiesneša_amats`, `Lm14 cits`: «Pieņemts» → `pieņemts` (33 tiesneši + 38 lēmumi, `1d8c1adf`, `b62c6b40`). Pirms tam klasifikators: teikuma sākuma «Par nodošanu … komisijai» → `iesniegts`, «Par iekļaušanu … darba kārtībā» → `procesuāls` (1104/Lm14 «Pieņemts» bija nodošana komisijai, ne lēmums).
- Audits: 904 posmi ar balsojumu pret jauno klasifikatoru → 7 atšķirības; 6 pārklasificētas (`data/fix_bill_stage_lm_procedural_2026-10-09.sql`), 1488/Lp14 (09-28 rokas labojums) atstāts. Plašāks regex trāpīja 20 — sašaurināts līdz teikuma sākumam.
- Rollback: `rollback_recompute_bill_status_{tiesnesi,lm}_2026-10-09.sql`, `rollback_bill_stage_lm_procedural_2026-10-09.sql`; atkārtots dry run 0. Testi `test_judge_decision_pieņemts_is_final`, `test_decision_pieņemts_is_final_but_referral_is_not` + 2 klasifikatora gadījumi (visi krita pirms labojuma).
- Likumprojekta lapa un Balsojumi: P3 marķieris «Kopsavilkums nav pieejams — historic backfill …» vairs netiek rādīts kā kopsavilkums (20 lapas; `_public_summary`, tests `test_backfill_sentinel_summary_not_shown_on_bill_page`).
- Arī «Par lēmuma projekta … iekļaušanu darba kārtībā» = `procesuāls` (`a16d6966`; 4 posmi, visi Noraidīts — statuss nemainās; `data/fix_bill_stage_lm_iekl_2026-10-09.sql` + 2 rollback).

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
