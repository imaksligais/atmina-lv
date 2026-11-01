# HANDOFF 2026-10-08 — VAD labojumi, X noklusējums, 40 X konti

Rutīna 10-08 vakarā: 1. ingest + visu doku analīze + pretrunu pārbaude (soļi 1–4); spriedzes, konteksta piezīmes, pārskats, deploy — NAV (operatora norāde). Kods commitots un pushots, `check.sh` 3440 passed. Pēdējais deploy — šīs sesijas beigās (skat. CHANGELOG 2026-10-08 (12)).

## Izdarīts
- `c5b3b2d6` X lapa noklusējumā «Tikai ieraksti»; profila «Pieminēts X» saite salabota (`tips=mention`).
- `6fbd760e` `save_analysis` vārti «tikai pieminē/minē» — tikai pie paša politiķa (CHANGELOG (9)).
- `cddce746`, `638f0819` VAD: lapošanas wrap pēc satura; ģenerators § 5/§ 6 = profils; dedup identitāte = etiķete + amats + iestāde (CHANGELOG (10), noteikums `operacijas.md` § VID).
- `79681dd8` + apply: 40 X konti (`data/seed_x_handles_grok_40_2026-10-08.sql`, rollback blakus). Katrs pārbaudīts dzīvi X (eksistē, bio/tvīti atbilst). Tvīti ienāks ar nākamo ingest.

## Gaida operatoru
1. ✓ **Deploy** — versija `09a1cc5f` (operators «pēc VID un docs»); live 200: `x.html` noklusējums «Tikai ieraksti», X saites profilos.
2. ✓ **Atliktie X konti** — operators 10-08: `@RSlesers` (īstais) un `@linda_matisone` (protected) pievienoti (`data/seed_x_handles_grok_2_2026-10-08.sql`); `@J_Urbanovics` (parodija) un `@Robertskipurs` (tikai boti) NEpievieno.
3. ✓ **VAD resweep** (10-08 vēlāk): 166 «jaunās» = 101 agrāk izņemti vārdabrāļi (denylist uuid kājas mirušas → labots ar identitātes kāju) + Bērziņš 7 + 5 jauni vārdabrāļi + 15 neskaidras + 38 īstas. Ielādētas 38 (2783 → 2821), rollback kokā; deployots `929e687c` (operators «Deploy»), `verify_host` 9/9.
4. ✓ **Zīle/Elksniņš + `vad-2026.md`** (operators «ok»): Zīles vārdabrāļa rinda izņemta, Elksniņa 2 rindas atjaunotas (kopā 2822); analīzes kopskaits 2822/202, tabulas nemainījās. Deployots.

5. ✓ **Neskaidrās** (operators «izskatiet kārtīgi»): Jenzis 14 + Žuravļevs 1 ielādēti, Ijabs 1 izņemts, Burovs svešs; `vad-2026.md` kopsummas pārrēķinātas (2836). CHANGELOG (13). Deploy `c167d4d6`, 9/9.

6. ✓ **CSS mobilās sīkās lietas** (operators «deploy»): CHANGELOG (14); atliktie punkti tur pat.

7. ✓ **Ingest + analīze** (operators «pirmo ingest … līdz visu doc analīzei, bez pārskata»): 113 doki + 42 jauno X kontu vēsture → plāns 79 aģenti / 8 kārtas / 790 pāri + atgūšana 10 = 800 pāri; 235 pozīcijas (730817–731051), 91 `needs_review` (lielākoties veci tvīti / RT ar citātu); 0 pretrunu, `contradiction_hunt` logs ar 11 noraidītiem kandidātiem. `data/fix_claim_730949_*` (reasoning drukas kļūda, rollback commitots pirms).

8. ✓ **Vakara rutīna** (operators «otrais ingest + 91 triāža + līdz galam»): 2. ingest → 52 pāri, 9 pozīcijas; Saeimas sēde 10-08 ielādēta (84 balsojumi, parity 0 trūkst); spriedzes 36 (+264 atjaunots pēc manas brīfa kļūdas); piezīmes 686, 687; pārskats 688 (quality-reviewer 2. kārta PASS pēc labojumiem `data/fix_qr_language_2026-10-08.sql`); wiki sync. Pretruna #56 (Siliņa, Arhitektūras likums) — devils-advocate SURVIVE; balsojumi 8389/8390 pārbaudīti saeima.lv (Siliņa «Par» abos, 47:8:18, JV 15/7/1); operators «publicē» → `confirmed=1`, pārskatā pievienota sadaļa «Pretrunas» (deploy `e369fe67`, publicēšanas karogs atjaunots); iepriekš deploy `f094b730`, `pretrunas/56.html` 200, `verify_host` 9/9. Vēlā partija 737389–737398 (Kulbergs + 10-01 stenogrammas: 9 pozīcijas, 3 dublikāti neglabāti). Attēls 365 (operators B), publicēts: deploy `0b0b2c24`, `verify_host` 9/9, varianti 4/4 200.

## Atvērts nākamajai sesijai
- **Spriedzes no veciem tvītiem:** 20 no 36 bija no 2013–2026-09 avotiem un publiski rādījās ar 10-08 datumu → operators «izņemt»: dzēstas (`data/fix_drop_old_tensions_2026-10-08.sql`, rollback blakus), deploy `337a01cc`, 9/9. Cēlonis paliek: spriedzei nav notikuma datuma, `saites_proposals` pieņem vecus tvītus — kandidāts BACKLOG (filtrs pēc avota `published_at` vai datuma kolonna). NB: 8 no 20 bija no 2026. gada septembra (464–466, 470, 477, 488–490) — dzēsti datuma attēlojuma dēļ, ne novecojuma; rollback tos atjauno, kad būs notikuma datums.
- **Kulberga citāts** (doc 129543, «teica politiķis» — aģentūras atribuēts tiešs citāts) glabāts kā paša vārdi (advisor 10-08).
- **NEEDS_REVIEW 10-08: 92 → 2 operatoram** (731045 Melnis, 731047 Sprindžuks — retvītoja cits cilvēks). 3 kārtas: `data/fix_needs_review_triage_2026-10-08_vakars{,2}.sql`, `data/fix_review_round3_2026-10-08.sql`; dzēsti kopā 8. Ekstrakcijas kandidāti (pirmavoti nav DB): LSM a665578 (Melnis, ASV karavīri, 10-01), Diena 2026-03-20 Smiltēna intervija («toreizējā valdība»).
- **Atkāpe, kandidāts noteikumam:** 7.–8. kārtā RT-paku aģentiem teicu, ka 12 doku robeža attiecas uz glabātām pozīcijām, ne tukšiem RT (prompts to nesaka; vairāki aģenti to atzīmēja kā novirzi, viens apstājās pie 12). Ierakstīt `claim-extractor.md` vai pārtraukt.
- **Iespējamie dublikāti** 730896↔689303, 730902↔718102, 731050↔730801 — dažādi izteikumi, paturēti. Pirmavota pārsiešana 730534/718036/555825 izdarīta 10-08 (kolīziju pārbaude 0, citāts burtiski tvītā, re-embed). Blakus: doc 125359 (Lienes A. RT) piesaistīts Putrai kā `subject` — X cilnē dubults.
- **Ingest:** `@D_Straubergs` twikit `KeyError: 'value'` (T12, viens konts); doks 128309 (Vīksna) saturs bojāts `<Field name='title'>`. TypeSafe ēna — zelta zudumi zem `enforce`: Inga Bērziņa p=0.58, Sruoģis p=0.43 (stenogramma); vakarā Smiltēns p=0.55, Gorkšs p=0.51, Tavars p=0.38, Kozlovskis p=0.35 (tvīti, kas viņus īsti piemin).
- **Atgūšana:** 5 web pāri (129585/129550→Tavars, 129561→Rinkēvičs, 129543/128132→Kulbergs) izskatīti 10-08 un tukši (dublikāti), bet `extracted_at` nav iestatīts — apsekojums tos rādīs atkal.
- **T6:** Circene role labots (mandāts beidzās 06-04), Šlesers/Klotiņš «(14. Saeima)». Krusts (Mārtiņš, id 45) — MMN izslēgšana vēl nav notikusi, pārbaudīt ~10-16; viņš `inactive`, X ielāde izslēgta kopš 04-27. Novembrī pēc 15. Saeimas sanākšanas — viens kopīgs role labojums pēc galīgajiem CVK datiem.
- **Vēstnesis:** 11 pāri (129516/129517) ir Saeimas 10-01 stenogrammas, ne MK protokoli → izskatīti 10-08 (paša runas, ±5 d dublikāti).
- VAD: tikai process — mēneša dry-run triāža (`operacijas.md` § VID); ģimenes paraksts — `scripts/vad_peek.py --pids`.
