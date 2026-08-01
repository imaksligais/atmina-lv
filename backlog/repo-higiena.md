# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## Repo higiēna / kods

> Visa sadaļa nāk no 2026-08-01 audita.

### [OPERATOR] Repo tīrīšana — IZPILDĪTS 2026-08-14 (CHANGELOG); paliek 3 atvērti lēmumi

Plāna izpilde pierakstīta CHANGELOG 2026-08-14 (19G → 15G). Atvērts paliek:

- ~~47 tracked `docs/tweet_bank` bināriji + 2 tracked `docs/audits` dokumenti~~ — **IZPILDĪTS jau 2026-08-14** (`4283120d`, `git rm --cached` + aukstais arhīvs; abas mapes publiskā spoguļa izslēgumu sarakstā, tāpēc publiskā diffa nebija). Verdikta rinda un šī bija novecojušas jau rakstīšanas brīdī; konstatēts un izgriezts 2026-08-19 (CHANGELOG).
- Brief (c) grupas atliktie: c3 NVO, c4 publicēto attēlu apcirpšana, c5 plānu arhīvs, c7 sīkumi, c8 `data/saeima_snapshots` NEAIZTIKT. **2026-08-19 papildus izpildīts:** 08-15 audita § A sīkā dzēšana (~6,3 MB: keši, 0 B db-artefakts, 7 `audit/*.png`, 2 sīkfaili) un abu saknes audita dokumentu (`ATMINA_TIRISANAS_BRIEFS_2026-08-13.md`, `REPO_HYGIENE_AUDIT_2026-08-15.md`) arhivēšana uz `E:/atmina-arhivs/2026-08/dokumenti/`.

### [OPEN] Vārtu saucēju audits 2026-08-09 — 3 apstiprināti atlikumi + 18 neverificēti kandidāti

12 aģentu read-only audits pār „vārti, kas nevar nokrist" klasi. **Saucējs: 116 kandidātu vārti 5 lēcās** — `scripts/` 27 (no ~87; vienreizējie `seed_*`/`render_*`/`backfill_*` NAV skatīti), `src/` 37, `tests/` **18 no 161 faila** (t.sk. neviens no četriem lielākajiem — atradumu neesamība tur nozīmē neskatīšanos, ne veselību), `/audit-integrity` 17/17 ar dzīviem saucējiem, promptu vārti 17/17 + 51 quality-bars kritērijs. Verificēti 6, izdzīvoja 5, atspēkots 1. Pilns pieraksts: CHANGELOG 2026-08-09 (3).

**VISI ČETRI IZPILDĪTI 2026-08-09** (A `964c8c86`; B/C/D pēc adversārās apjoma pārskatīšanas, kas apgāza divas no trim specifikācijām; pilnais specifikāciju apraksts un izpildes pēda — CHANGELOG 2026-08-09 (3) un (4)). Izpildē fiksētās atziņas, kas paliek spēkā: parity rīka `KOPĀ:` virkni neaiztikt (citē 4 vietas) un DK=0 nedrīkst būt kļūda (svinīgās sēdes leģitīmi 0); quote-fidelity saucēji tikai lēmumu barojošām klasēm (§ Ne-darīt); iepriekšējais apgalvojums „C noslēdz § Citātu integritātes (e) pirmo soli" bija NEPATIESS — (e) ir atsevišķs ieraksts.

### [OPERATOR] `paraphrase_mid` — 13 rindas virs 0,85, ko vecais likums neredzēja

Skaitītāja labojuma (2026-08-09) tiešais produkts: `audit_quote_fidelity.py` tagad uzrāda **13/2294 rindas pie `conf>=0.85`**, kur politiķa uzvārds stāv citāta VIDŪ. Lasītas 8 — vismaz 6 ir žurnālista trešās personas atstāsts `quote` laukā, t.i. tieši tā klase, kuras dēļ rīks tapa: **#119** (Valainis 0,95 — „LZS kongresā vienbalsīgi … izvirzīts"), **#20535** (Rinkēvičs 0,95), **#20529** un **#20528** (Kulbergs 0,90/0,85), **#7377** (Šuvajevs 0,90), **#275** (glabāts zem Bražes, bet teikums ir par Rinkēviča atļauju).

**Rindu-pa-rindai triāža, NEKAD batch** — starp 13 ir arī leģitīmi gadījumi: **#14523** (Līdaka) ir īsts pirmās personas citāts, kurā uzvārds vienkārši parādās. Katram labojumam pāra rollback ar unikālu scope sufiksu; ja mainās `stance`, obligāts re-embed. Pilnais saraksts: `.venv/Scripts/python.exe scripts/audit_quote_fidelity.py --min-confidence 0.85`.

**18 neverificēti kandidāti — VERIFICĒTI 2026-08-19** (DeepSeek read-only aģents; atskaite `docs/audits/2026-08-19-vartu-saucedji-verifikacija.md` ar file:line pierādījumiem): no 8 uzskaitītajiem kandidātiem (9 pārbaudes vienības) — **8 APSTIPRINĀTI** (probe_x_cookies `[OK]` bez zondes · eval_matcher vārti deklarēti, bet nepiespiesti · quality.py degrades-open bez fasttext · routine.py pretrunu solis tikai done/n/a · cirkulārā vector-staleness fikstūra · 13. pārbaudes `WHERE id = N` regex palaiž garām bulk `IN` · 9. pārbaudes „viena etiķete" premisa nepatiesa — `ST!` atkal 7366 rindas · brief-writer `GROUP BY speaker_id` NULL kolonna), **1 ATSPĒKOTS** (quality-reviewer jau lieto `_daily_briefs_for`). **„Vidējie 7 un zemie 2" NAV verificējami — saraksts repo neeksistē:** atsauce ir apļveida (BACKLOG → CHANGELOG 2026-08-09 (3) → BACKLOG), git vēsturē nav, un 8+7+2=17≠18. Labojumi: CHANGELOG 2026-08-19 (vārtu vilnis).

**Blakus: quality-bars 9 nesakritības** (51 kritērijs pret nesējiem; Sociālais 5/5 un Seedēšana 7/7 sakrīt pilnībā). Smagākā — Dienas pārskata #7 (attēlu varianti + dzīvs HTTP 200, kritērijs, kas radās no slēgtā 7. pārbaudes incidenta) neparādās ne `brief-writer.md`, ne `dienas-rutina.md`, un `graphics-designer.md` `make_variants` kļūmi aprij ar „never block approval on variant gen" — kritērijam publicēšanas brīdī nav neviena nesēja, tikai `/audit-integrity` pēc-fakta diska pārbaude.

**Un viens datu jautājums, ne vārtu defekts:** 17. pārbaude šodien dod `checked=31 flagged=12` (1447 web citāti), un 12. rinda — claim 615955 / dok. 80022 (diena.lv; claim 08-04 22:25, dokuments pārskrāpēts 08-05 21:59) — nav pieņemto 11 sarakstā. Pēc pašas pārbaudes triāžas likuma tas ir svaigs pārskrāpējums, kas apēdis citātu. [OPERATOR].

### [OPEN] Commit autora identitāte — turpmākie commiti nokārtoti, vēsture paliek

**Izdarīts 2026-08-03:** repo-lokālais `user.email` = GitHub noreply forma `<id>+<login>@users.noreply.github.com` (id no publiskā API, ne uzminēts). **`.git/config` nav izsekots — pēc katras pārklonēšanas jāuzstāda no jauna; tieši tāpēc ieraksts paliek šeit.**

**Paliek atvērts, apzināti nerisināts:** esošā vēsture nes veco adresi; vienīgais ceļš ir vēstures pārrakstīšana, kas salauztu commit hash-us, ko CHANGELOG/BACKLOG citē kā pierādījumus. Noreply pāreja aptur plūsmu, ne notīra pagātni. Ja tomēr dara — vispirms izmērīt lauztos hash-us.

### [FIX] 418 web dokumenti no `ingest_url.py` ir bez chunkiem — semantiskajā meklēšanā tie neeksistē

**(a) Sekas DOKUMENTĒTAS 2026-08-05** (`wiki/operations/operacijas.md` pie `ingest_url.py` komandas): 603 web doki bez chunkiem, no tiem **418 tāpēc, ka `scripts/ingest_url.py` vispār neembedo** — tie semantiskajā dokumentu meklēšanā neeksistē, lai gan `documents` tabulā ir (apzināts dizains, sk. § Ne-darīt — `ensure_embeddings_live` tur nav ar nolūku; claim vektori strādā, jo `store_claim()` embedo pats). Paliek izvēle, vai embedēšanu ceļam kādreiz pieslēgt — atsevišķs lēmums, ja `ingest_url` korpuss kļūst meklēšanai svarīgs.

**(b) SLĒGTS.** `insert_chunks` tagad dzēš esošos chunkus (un vispirms to vektorus — vec0 nekaskādējas) pirms rakstīšanas; 2 regresijas testi `tests/test_db.py::TestInsertChunksReplaces`; vēsturiskie 690+690 iztīrīti ar pāra rollback (CHANGELOG 2026-08-04).

**Blakus atklāts, PIRMS-eksistējošs (nav tīrīšanas produkts):** `document_vectors` tur **450 bāreņu rindas** (chunk_id bez `document_chunks` rindas) — identitāte 97 066 − 96 616 = 450 pastāvēja jau pirms dzēšanas. Tā pati kosmētiskā klase, kas 7 004 `claim_vectors` bāreņi: kNN var atgriezt mirušu chunk_id. Ja kādreiz tīra — ar pāra rollback.

### [OPEN] `src/csp/` sync bez ieejas punkta — operators izlēmis PIESLĒGT (2026-08-15)

**Lēmums pieņemts, dilemma slēgta.** Agrāk šeit stāvēja „vai nu pieslēgt, vai izmest abus". Operatora atbilde 2026-08-15: **CSP dati TIKS atsvaidzināti**, tāpēc `src/csp/{sync,client,db}.py` paliek. 2026-08-15 repo audits tos bija ieteicis dzēst kā mirušu kodu (286 rindas, 0 importētāju) — **ieteikums noraidīts**: `sync.py` ir vienīgais `data/csp.db` atsvaidzinātājs, un `data/csp.db` ir dzīvs renderēšanas ievads (`src/render/statistika.py:29-30` importē `src.csp.insights` + `src.csp.tables`). Nepārvērtē par mirušu kodu bez jauna fakta.

**Kas tiešām atlicis:** `sync_all(conn)` ņem gatavu savienojumu un `src/csp/db.py` tur shēmu, bet **ieejas punkta nav** — ne CLI, ne izsaucēja, tāpēc atsvaidzināšana pašlaik nav izpildāma. Trūkst ~15 rindu vadu (`python -m src.csp` ar `--dry-run`), runbook rinda `wiki/operations/commands.md`, un tikai tad pirmais reālais palaidiens.

**Uzmanīgi ar pirmo palaidienu:** `data/csp.db` ir **izsekots binārs**, tāpēc refresh ir datu mutācija, ne higiēna — `--dry-run` vispirms, un jārēķinās, ka izsekota binārā faila diff aiziet arī publiskajā spogulī. Dati iesaldēti kopš 2026-04-14, tāpēc pirmais atsvaidzinājums būs liels.

### [SLĒGTS 2026-08-21] `brief_images` ceļu konvencijas + nedokumentēts `approved=2`

**IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (7)): 11 no 280 rindām normalizētas uz site-relatīvu konvenciju (`data/{fix,rollback}_brief_image_paths_2026-08-21.sql`; pirms: 269 site-relatīvas, 10 ar lieku `atmina/` prefiksu, 1 Windows repo ceļš, 3 tukšas — pieaugums pret 08-04 mērījumu ir jaunas rindas, ne klases maiņa). `approved` domēns + `image_path` konvencija dokumentēti pie kolonnām `src/schema.sql` (DDL promovēts no db.py); 4 sintēžu attēlu rakstītāji laboti, lai vecā konvencija neatgriežas. Tukšās rindas (id 54/72/275) paliek — API-kļūdu audita pēdas.

_Vēsturiskais ieraksts (2026-08-04 mērījums):_

`brief_images.image_path` nes **trīs savstarpēji nesavietojamas ceļu konvencijas** (site-relatīvā 230 rindās, output-relatīvā ar lieku `atmina/` segmentu 7 rindās, un viens Windows repo ceļš) plus nedokumentētu `approved=2` — **pārmērīts 2026-08-04: 71 rinda / 44 notes, ne „divas rindas"**; semantika no datiem: 40 no 44 notēm ir arī `approved=1` rinda (= atcelts/aizstāts kandidāts), 4 ir atceltas bez aizstājēja (tostarp #93/#96, kuru lapas tāpēc korekti rāda fallback `og:image` — dzīva defekta nav). Pilnais domēns: `-1` ×4, `0` ×32, `1` ×138, `2` ×71. Jebkurš jauns lasītājs, kas šo kolonnu savieno ar izvades koku (piem. salabotā 7. pārbaude), bez dokumentācijas kļūdīsies. Normalizēt ceļus ar pāra rollback un dokumentēt `approved` domēnu pie kolonnas `src/schema.sql`.

**Noraidīto plakātu vārtu sprauga — SLĒGTA 2026-08-16** (sakne, mērogs 269 rindu saucējā, koda labojums un 108 failu izņemšana no servera: CHANGELOG 2026-08-16 (2); datu pēda `data/{fix,rollback}_brief_image_270_reject_2026-08-16.sql`). Paliek trīs lietas, kas jāzina lasītājam: `_rejected_brief_stems()` sedz visus trīs noraidījuma kodējumus (`approved=2`; `-1` ar «superseded by id=N»; `0` ar apstiprinātu brāli — operatora dabiskā darbība ir UN-APPROVE `1 → 0`, ne `1 → 2`) un tiek padots ABIEM soļiem, ģenerēšanai un kopēšanai; **divas tukšā `image_path` rindas (id 54, 72) APZINĀTI nav dzēstas** (atcelta kandidāta audita pēda; tukšā stema risks ir aizvērts vārtā un testā); un vispārīgā forma — **additīvais deploy neko nedzēš, tāpēc vārtiem jānostrādā PIRMS sūtīšanas**, bet pēc-fakta tīrīšana vienmēr ir atsevišķs `ssh` solis.

