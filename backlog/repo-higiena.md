# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Repo higiēna / kods

> Visa sadaļa nāk no 2026-08-01 audita.

### [OPERATOR] Repo tīrīšana — IZPILDĪTS 2026-08-14 (CHANGELOG); paliek Brief (c) grupa

Plāna izpilde pierakstīta CHANGELOG 2026-08-14 (19G → 15G). **ATLIKTS 2026-09-07** (verdikts 49a) — vēlēšanu sezonā datu integritāte ir priekšā repo higiēnai. Atvērts paliek:

- Brief (c) grupas atliktie: c3 NVO, c4 publicēto attēlu apcirpšana, c5 plānu arhīvs, c7 sīkumi, c8 `data/saeima_snapshots` NEAIZTIKT. **2026-08-19 papildus izpildīts:** 08-15 audita § A sīkā dzēšana (~6,3 MB: keši, 0 B db-artefakts, 7 `audit/*.png`, 2 sīkfaili) un abu saknes audita dokumentu (`ATMINA_TIRISANAS_BRIEFS_2026-08-13.md`, `REPO_HYGIENE_AUDIT_2026-08-15.md`) arhivēšana uz `E:/atmina-arhivs/2026-08/dokumenti/`.

### [OPEN] Vārtu saucēju audits — 18 kandidāti verificēti; paliek četri saucēju jautājumi (pārmērīti 2026-09-07)

12 aģentu read-only audits pār „vārti, kas nevar nokrist" klasi. **Saucējs: 116 kandidātu vārti 5 lēcās** — `scripts/` 27 (no ~87; vienreizējie `seed_*`/`render_*`/`backfill_*` NAV skatīti), `src/` 37, `tests/` **18 no 161 faila** (t.sk. neviens no četriem lielākajiem — atradumu neesamība tur nozīmē neskatīšanos, ne veselību), `/audit-integrity` 17/17 ar dzīviem saucējiem, promptu vārti 17/17 + 51 quality-bars kritērijs. Verificēti 6, izdzīvoja 5, atspēkots 1. Pilns pieraksts: CHANGELOG 2026-08-09 (3).

**VISI ČETRI IZPILDĪTI 2026-08-09** (A `964c8c86`; B/C/D pēc adversārās apjoma pārskatīšanas, kas apgāza divas no trim specifikācijām; pilnais specifikāciju apraksts un izpildes pēda — CHANGELOG 2026-08-09 (3) un (4)). Izpildē fiksētās atziņas, kas paliek spēkā: parity rīka `KOPĀ:` virkni neaiztikt (citē 4 vietas) un DK=0 nedrīkst būt kļūda (svinīgās sēdes leģitīmi 0); quote-fidelity saucēji tikai lēmumu barojošām klasēm (§ Ne-darīt); iepriekšējais apgalvojums „C noslēdz § Citātu integritātes (e) pirmo soli" bija NEPATIESS — (e) ir atsevišķs ieraksts.

### [OPERATOR] `paraphrase_mid` — 13 rindas virs 0,85, ko vecais likums neredzēja

Skaitītāja labojuma (2026-08-09) tiešais produkts: `audit_quote_fidelity.py` tagad uzrāda **13/2294 rindas pie `conf>=0.85`**, kur politiķa uzvārds stāv citāta VIDŪ. Lasītas 8 — vismaz 6 ir žurnālista trešās personas atstāsts `quote` laukā, t.i. tieši tā klase, kuras dēļ rīks tapa: **#119** (Valainis 0,95 — „LZS kongresā vienbalsīgi … izvirzīts"), **#20535** (Rinkēvičs 0,95), **#20529** un **#20528** (Kulbergs 0,90/0,85), **#7377** (Šuvajevs 0,90), **#275** (glabāts zem Bražes, bet teikums ir par Rinkēviča atļauju).

**ATLIKTS 2026-09-07** (verdikts 50): citātu triāžas sesija joprojām NAV palaista, un šīs 13 rindas ir tikai viena tās daļa — pilnais apjoms (13 `paraphrase_mid` + 179 pieturzīmes + 37 vājie + 17. pārbaudes 7 jaunie id) stāv `BACKLOG.md` § Atliktais pēc 2026-09-06 verdiktiem. **Rindu-pa-rindai triāža, NEKAD batch** — starp 13 ir arī leģitīmi gadījumi: **#14523** (Līdaka) ir īsts pirmās personas citāts, kurā uzvārds vienkārši parādās. Katram labojumam pāra rollback ar unikālu scope sufiksu; ja mainās `stance`, obligāts re-embed. Pilnais saraksts: `.venv/Scripts/python.exe scripts/audit_quote_fidelity.py --min-confidence 0.85`.

**18 neverificēti kandidāti — VERIFICĒTI 2026-08-19** (DeepSeek read-only aģents; atskaite `docs/audits/2026-08-19-vartu-saucedji-verifikacija.md` ar file:line pierādījumiem): no 8 uzskaitītajiem kandidātiem (9 pārbaudes vienības) — **8 APSTIPRINĀTI** (probe_x_cookies `[OK]` bez zondes · eval_matcher vārti deklarēti, bet nepiespiesti · quality.py degrades-open bez fasttext · routine.py pretrunu solis tikai done/n/a · cirkulārā vector-staleness fikstūra · 13. pārbaudes `WHERE id = N` regex palaiž garām bulk `IN` · 9. pārbaudes „viena etiķete" premisa nepatiesa — `ST!` atkal 7366 rindas · brief-writer `GROUP BY speaker_id` NULL kolonna), **1 ATSPĒKOTS** (quality-reviewer jau lieto `_daily_briefs_for`). **„Vidējie 7 un zemie 2" NAV verificējami — saraksts repo neeksistē:** atsauce ir apļveida (BACKLOG → CHANGELOG 2026-08-09 (3) → BACKLOG), git vēsturē nav, un 8+7+2=17≠18. Labojumi: CHANGELOG 2026-08-19 (vārtu vilnis).

**Blakus: quality-bars 9 nesakritības** (51 kritērijs pret nesējiem; Sociālais 5/5 un Seedēšana 7/7 sakrīt pilnībā). Smagākā — Dienas pārskata #7 (attēlu varianti + dzīvs HTTP 200, kritērijs, kas radās no slēgtā 7. pārbaudes incidenta) neparādās ne `brief-writer.md`, ne `dienas-rutina.md`, un `graphics-designer.md` `make_variants` kļūmi aprij ar „never block approval on variant gen" — kritērijam publicēšanas brīdī nav neviena nesēja, tikai `/audit-integrity` pēc-fakta diska pārbaude.

**Un datu jautājumi, kas nav vārtu defekti — pārmērīti 2026-09-07:**

- **17. pārbaude: 7 jauni citātu id ārpus pieņemto saraksta** — 615955, 689768, 704089, 704179, 704217, 704342, 709073. Tie iet **verdikta 50 citātu triāžas sesijā**, ne šeit. **615955 (dok. 80022) NAV pārskrāpējuma zudums** — 2026-09-07 pārbaude atrada, ka citāts avotā **IR**: 251 no 252 zīmēm sakrīt zīme zīmē pozīcijā 1327, atšķiras vienīgi noslēguma pieturzīme (claim `.`, avotā `,`, jo teikums turpinās). 09-06 `instr()` = 0 bija pilnas virknes meklējums kopā ar punktu, tātad tā ir **pieturzīmju klase**, ne pārskrāpēšana (CHANGELOG 2026-09-07 (1)). Vecais «svaigs pārskrāpējums» lasījums bija nepareizs — nepārmanto to.
- **13. pārbaude (stale vektori) ziņo 150 `saeima_vote` rindas, kuras Escalation 8 aizliedz labot.** `scripts/reembed_claims.py` nedrīkst iet pār `saeima_vote` rindu — 2026-08-21 verdikts jaunām balsojumu rindām vektoru NEdod, un rīka palaišana tur radītu tieši to vektoru, ko verdikts atturēja. Tātad kandidātu kopai ir jāizslēdz `claim_type='saeima_vote'`; **actionable atlikums ir 21 `position` rinda**. Vārts, kas nosauc 171 rindu, no kurām 150 aizliegts aiztikt, ir vārts, kas nevar nokrist pareizajā vietā. *Rīcība:* sašaurināt 13. pārbaudes kandidātu kopu un pārpublicēt bāzlīniju kā `checked=… flagged=21`.
- **6. pārbaude jāpārmēra ar līdzības filtru.** Plašais variants dod ~600 grupas — tā nav bāzlīnija, tas ir saucējs bez filtra. Pirms rīcības pārmērīt ar līdzības slieksni un pierakstīt vaicājumu blakus skaitlim.
- **8. pārbaude: 1 149 nogriezti stubi no 6 493** nepārskatītiem web dokiem. Skaitlis pats par sevi nav atradums (§ Ne-darīt aizliedz saucējus, kas nevienā vērtībā nemaina rīcību) — bet šis maina: tas nosaka, cik liela daļa no ekstrakcijas rindas vispār ir ekstraktējama. Saistīts ar § lsm/diena/tvnet truncated backfill kampaņu [`avoti.md`](avoti.md).

*Īpašnieks:* operators (katrai rindai savs lēmums; neviena no četrām nav batch-darbs).

### [OPEN] Commit autora identitāte — turpmākie commiti nokārtoti, vēsture paliek

**Izdarīts 2026-08-03:** repo-lokālais `user.email` = GitHub noreply forma `<id>+<login>@users.noreply.github.com` (id no publiskā API, ne uzminēts). **`.git/config` nav izsekots — pēc katras pārklonēšanas jāuzstāda no jauna; tieši tāpēc ieraksts paliek šeit.**

**NĒ vēstures pārrakstīšanai — apstiprināts 2026-09-07** (verdikts 49c): esošā vēsture nes veco adresi; vienīgais ceļš ir vēstures pārrakstīšana, kas salauztu commit hash-us, ko CHANGELOG/BACKLOG citē kā pierādījumus. Noreply pāreja aptur plūsmu, ne notīra pagātni. Ja tomēr dara — vispirms izmērīt lauztos hash-us.

### [FIX] 418 web dokumenti no `ingest_url.py` ir bez chunkiem — semantiskajā meklēšanā tie neeksistē

**(a) Sekas DOKUMENTĒTAS 2026-08-05** (`wiki/operations/operacijas.md` pie `ingest_url.py` komandas): 603 web doki bez chunkiem, no tiem **418 tāpēc, ka `scripts/ingest_url.py` vispār neembedo** — tie semantiskajā dokumentu meklēšanā neeksistē, lai gan `documents` tabulā ir (apzināts dizains, sk. § Ne-darīt — `ensure_embeddings_live` tur nav ar nolūku; claim vektori strādā, jo `store_claim()` embedo pats). Paliek izvēle, vai embedēšanu ceļam kādreiz pieslēgt — atsevišķs lēmums, ja `ingest_url` korpuss kļūst meklēšanai svarīgs.

**(b) SLĒGTS.** `insert_chunks` tagad dzēš esošos chunkus (un vispirms to vektorus — vec0 nekaskādējas) pirms rakstīšanas; 2 regresijas testi `tests/test_db.py::TestInsertChunksReplaces`; vēsturiskie 690+690 iztīrīti ar pāra rollback (CHANGELOG 2026-08-04).

**Blakus atklātā `document_vectors` bāreņu rinda (450) PĀRCELTA 2026-09-05** uz [`dati-db.md`](dati-db.md) § `claim_vectors` bāreņi — viena vec0 bāreņu klase, viens ieraksts, viens `[DEFERRED]`.

### [OPERATOR] `data/csp.db` pirmais `--apply` — vienīgais atlikums pēc ieejas punkta pieslēgšanas

**Ieejas punkts SLĒGTS 2026-09-07** (verdikts 49b, CHANGELOG 2026-09-07 (9)): `python -m src.csp` — noklusējums ir sauss palaidiens pret `data/csp.db` **KOPIJU** (kopija, ne tukša bāze: `upsert_rows` ir INSERT OR REPLACE, tāpēc tikai pret esošajiem datiem delta ir patiesa), `--apply` jāraksta ar roku, nulle atsvaidzinātu tabulu → exit 1. Vārti: `tests/test_csp_entrypoint.py` (6 testi, t.sk. «sausais palaidiens atstāj failu baitu-identisku»); runbook `wiki/operations/commands.md` § CSP statistikas datu atsvaidzināšana. Pirmais dzīvais sausais palaidiens: **10/10 tabulu, 1 489 fetčotas rindas, `csp_data` 1 481 → 1 509 (+28)** pret 2026-04-14 iesaldētajiem datiem; izsekotais binārais fails palika neskarts.

**SLĒGTS 2026-09-06 — pirmais `--apply` izpildīts** (commit `562b4ca8`, CHANGELOG «2026-09-06 (2)»: 10/10 tabulu, `csp_data` 1 481 → 1 509, `curated/atmina/statistika*` momentuzņēmums atjaunots). Ieraksts paliek kā konteksts nākamajam `--apply`; teksts zemāk ir vēsture. ~~Paliek atvērts tikai pirmais `--apply`.~~ Tā ir datu mutācija **izsekotā binārā failā**, kas aiziet arī publiskajā spogulī, tāpēc tas nav higiēna, bet lēmums. Konteksts, ko nepārvērtē par mirušu kodu: `src/csp/sync.py` ir vienīgais `data/csp.db` atsvaidzinātājs, un `data/csp.db` ir dzīvs renderēšanas ievads (`src/render/statistika.py:29-30`). *Īpašnieks:* operators — tagad tā ir viena komanda, ne projekts.

### [OPEN] Testu mutāciju izlases robi — 5 neaizsegti zari (2026-09-24)

Izlase (`docs/audits/2026-09-24-test-mutation-sample/README.md`, privāts): 20 biežāk mainītie testu faili, 81 tests, 95 mutācijas → **80/81 testu nogalina mutantu**; «zema signāla testu» hipotēze šeit neapstiprinājās. Izlabots uzreiz: `www.`-incidenta tests (vecā forma izturēja paša incidenta mutāciju) un `verify_host` drošības galveņu negatīvie testi (+3). **Atlikušie robi — trūkst testa, ne jādzēš:** (1) `test_utc_column_is_never_read_bare` neķer UTC kolonnu, kas salīdzināta bez datuma funkcijas (`t.created_at >= ?`); (2) dubultie sargi, kur testi sasniedz tikai ārējo: `link_audit_row` otrā pārbaude, `backfill_truncated_docs` glabātās rindas pārbaude, pavediena stila pārbaude; (3) `_fetch_topics` neaktīvo politiķu izslēgšana (docstring sola, tests nav). **Nepārbaudīts apgalvojums:** aģents raksta, ka `TestTensionDayBoundaryTimezone` publiskajā CI (UTC runneris) izlaižas; CI kopš 09-24 liek `TZ=Europe/Riga` — pārbaudīt ar `-rs` nākamajā sync (skipu skaits CI 15 pret lokāli 3). Dzēšanas kandidāti (2: konstantes garuma tests `test_lv_text`, dublēts stila teksta tests `test_graphics_cli`) apzināti atstāti — ieguvums ~0.

### [OPEN] Attēla paraksta pēcapstrādes vārts — (a) prompta aizliegums IEVIESTS 2026-09-05, paliek (b) OCR/stūru heiristika

`--no-text` režīmā prompts aizliedz «no text, no lettering, no numbers, no words, no captions, no logos» un `TEXT_FREE_CONSTRAINTS` to pastiprina — bet 2026-09-04 modelis brief attēlā (`brief_images` #310, `2026-09-04-dienas-parskats-a1e6d058.png`) apakšējā labajā stūrī uzzīmēja **izdomātu kursīvu mākslinieka parakstu**. Aizliegumu saraksts paraksta, autogrāfa, monogrammas un iniciāļu nesauc vārdā, un modelis to acīmredzot nelasa kā «text».

**Kāpēc tas nav kosmētika:** atmina.lv publicē ANONĪMI (standing decision). Autorības zīme attēlā ir tieši tas, ko šī vietne nedrīkst nest — turklāt paraksts ir izdomāts, t.i. fabricēta atribūcija. Ja tas aiziet live, to neviens nepamana, jo neviens vārtos parakstu nemeklē.

Noķēra tikai manuāla stūru apskate 2x palielinājumā pirms apstiprināšanas; `cli brief` pats attēlu neanalizē. Divi kandidāti:
- (a) papildināt `TEXT_FREE_CONSTRAINTS` ar eksplicītu «no artist signature, no autograph, no cursive monogram, no initials, no printed credit line, no plate-mark inscription, blank margins and corners» — #311 tieši ar šo formulējumu izdevās no pirmā mēģinājuma;
- (b) pēcapstrādes vārts: OCR vai malu/stūru heiristika pār ģenerēto PNG pirms `save_image_row()`, kas karogo tumšus sīkstruktūras blāķus tukšajā malā.

**(a) IEVIESTS 2026-09-05** (`src/graphics/prompt.py::TEXT_FREE_CONSTRAINTS` + `tests/test_graphics_prompt.py::test_text_free_constraints_forbid_authorship_marks`; CHANGELOG 2026-09-05 (4)). **Paliek (b)** — īstais vārts, jo (a) paļaujas uz modeļa paklausību; manuālā stūru apskate pirms apstiprināšanas paliek obligāta.
