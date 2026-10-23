# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Avoti

### [OPEN] Vēsturisko dokumentu backlogi atsevišķai sweep sesijai

> **2026-10-05 — `subject` backlogs iztukšots** ([`docs/audits/2026-10-05-backlog-sweep/`](../docs/audits/2026-10-05-backlog-sweep/README.md)). Darba saraksts: 2 178 (pid, doc) pāri, `role='subject'`, aktīvs pēc `queue_politician_sql`, bez claim, doks `reviewed_at IS NULL` (vai 15. Saeimas jaunais deputāts), `scraped_at < 2026-10-04 05:00` vai publicēts pirms 10-03 — web 717, twitter 571, vestnesis 872, x_mention 18. Izpildīja 223 Opus `claim-extractor` aģenti (izmēģinājums 2 + galvenā 63 + atlikums 30 + Vēstnesis 78 + atgūšana 47 + stale28 3): **614 glabātas pozīcijas, 2 dublikāti dzēsti ar rollback** (`SELECT COUNT(*) FROM claims WHERE claim_type='position'` 8 105 → 8 717). Pāru pārklājums pēc tam: `src.routine.stale_extraction_pairs(db, '2026-10-05')` → main 0, Vēstnesis 0. Zemāk esošie 09-25 skaitļi ir vēsture. **Lai neuzkrātos atkal:** [`docs/plans/2026-10-05-backlog-uzkrasanas-varti.md`](../docs/plans/2026-10-05-backlog-uzkrasanas-varti.md).

Dienas rutīna šos dokus nekad nesasniedz; tie prasa mērķētu sweep pa politiķim (pa ≤12 sesijā) vai `historic-backfill` loga paplašinājumu. Neizlasītu dokumentu nekad nezīmogo ar `empty_doc_ids` (T5/T11). Pārmērīts 2026-09-25:

- **Nepārskatīti pa politiķim** (`COUNT(DISTINCT d.id)` pār `documents d JOIN document_politicians dp ON dp.document_id=d.id WHERE dp.politician_id=? AND d.reviewed_at IS NULL`): Šnore 124 → **170**, Staķis 139 → **157**, Ozols 64 → **179**, Pūpols 829 → **1 196**, Lindberga 194 → **267**. Rinda lielākoties ir pieminējumu josla; izskatīšanas vērta ir `mentioned` (+ `vestnesis`) apakškopa.
- **Nepārskatīti `subject` doki aktīvajiem** (`… JOIN document_politicians dp ON dp.document_id=d.id AND dp.role='subject' JOIN tracked_politicians tp ON tp.id=dp.politician_id WHERE d.reviewed_at IS NULL AND tp.relationship_type!='inactive'`, bez `data/backfill_batch3_updated_ids_2026-09-24.txt` dokiem): **1 363** (vestnesis 801, twitter 355, web 189, x_mention 18); Kulbergs 136 → **284**, Lapsa 106 → **99**. 3. backfill partijas 400 doki nav šeit — tie ir truncated ieraksta darbs.
- **Vecā `subject`-aste** (1. sweep izpildīts 2026-08-06): Lapsa, Velps (51433, 47607, 47608 + 3 vecāki), Stendzenieks, Kulbergs (vecāki `web subject`), Judins doc 26496 (pārlāde, ne ekstrakcija), doc 64398 (atvēršana = operatora lēmums). Neizšķirts noteikuma kandidāts: **retvīts par sevi** — ja pirmavots jau DB → tukšs; ja nav, anonss ir vienīgais pierādījums.
- **15. Saeimas 30 jaunie deputāti bez neviena `subject` doka** (2026-10-05) — vajag vēsturisko meklēšanu (`/historic-backfill`, operatora laiks).
- **Pozīcijas pēc izvēles (no handoffiem 10-04…10-12):** Kulberga 2022. gada citāts doc 118396 un doc 85876 («Iekārtas iepirkām…»); Valaiņa «ZZS vērsies Satversmes tiesā» doc 120027; Rinkēviča JEF detaļa #725099; Zeltīta #725159 avots ir Velpa RT; Šlesera LSM citāts doc 123761 (#729876 to nesatur). Pirmavoti nav DB: LSM a665578 (Melnis, ASV karavīri, 10-01), Diena 2026-03-20 Smiltēna intervija.
- **Doc 128309 (Vīksna) saturs bojāts** — `<Field name='title'>` + saite (2026-10-08); pārlādēt vai atzīmēt.

*Īpašnieks:* operators (sesijas laiks). Quote-tweet/atbilžu satura robeža → `wiki/operations/content-pipeline.md` § Zināmās ievākšanas robežas.

### [OPEN] lsm/diena/tvnet truncated backfill — novecojuši chunki, ievads «pilnajiem» dokiem

Sargs (`src/soft_404.py`) un skripts (`scripts/backfill_truncated_docs.py`) darbojas; izmēģinājums un 1.–2. partija izpildīti (`docs/audits/2026-09-23-backfill-batch1/`, `docs/audits/2026-09-23-backfill-batch2/`). Paliek:

- **(a) 3. partijas ekstrakcija — IZPILDĪTA 2026-10-05** kā daļa no vēsturiskā sweep (`docs/audits/2026-10-05-backlog-sweep/`): 10-05 pirms sweep pārmērīts 400/400 `reviewed_at IS NULL`, 416 pāri / 62 politiķi; pēc sweep `SELECT COUNT(*) FROM documents WHERE id IN (<data/backfill_batch3_updated_ids_2026-09-24.txt>) AND reviewed_at IS NULL` → 0. Ko tas izpildīja: `main` + `main_left` kārtu `claim-extractor` aģenti (žurnāli `main_journal.jsonl`, `main_left_journal.jsonl`).
- **(b) Chunki novecojuši:** 398 no 399 pārlādēto doku chunki sedz <50 % pašreizējā teksta (`document_chunks` `SUM(LENGTH)` pret `LENGTH(documents.content)`); skripts chunkus apzināti neatjauno. Tas pats pārchunkošanas darbs sedz arī 418 `scripts/ingest_url.py` web dokus, kuri nekad nav embedoti (`wiki/operations/operacijas.md`) — ja pārchunko, tad abas kopas vienā darbā.
- **(c) Ievads trūkst arī «pilnajiem» dokiem** (augusts–septembris, `word_count≥90`, lsm/diena; 7/8 izlasē): ingests salabots 2026-09-23 (CHANGELOG 2026-09-23 (3)), vēsturiskie nav — ievadu var atgūt no lapas `description`/RSS. **2026-10-15:** `backfill_truncated_docs.py` to NElabo — sausais skrējiens uz 4 diena.lv dokiem (71014, 81946, 99493, 105284) → `not_longer` 4/4 (pārlāde dod tikpat vārdu, bez ievada; doc 81946 ievads ar runātāja vārdu ir lapas `og:description`). Apakšējā robeža: 63/1 270 diena.lv web doku kopš 07-15 sākas ar atsauces vārdu («Viņš», «Vienlaikus», «Līdztekus», «Tāpat», «Savukārt», «Tos,»). Labojums: backfill ceļā pievienot `description` kā ievadu (`docs/audits/2026-10-15-d4-atgusana/needs-review-ieteikumi.md`).

*Īpašnieks:* operators ((a) laiks, (b) un (c) — atsevišķi lēmumi). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [DEFERRED] diena.lv RSS ievāc saistīto virsrakstu sānjoslu → viltus `subject` (doc 87866)

Doc 87866 ir laika prognozes raksts; Rinkēviča vārds tajā ir tikai navigācijas blokā ar saistītajiem virsrakstiem (`instr(content,'Rinkēvič')` = 720), bet junction rinda ir `subject`, un `match_politicians` to atjaunotu (pārbaudīts 2026-09-25). Tā nav namesake kolīzija (`negative_patterns` neder) — korpusā ir par daudz, ne par maz. *Trigeris:* otrā instance. *Rīcība:* `_clean_extracted_text` / trafilatura robežu pastiprināšana, ne matcher; rindas dzēšana ar rollback. *Īpašnieks:* operators. Pārcelts no `matcher.md` 2026-08-15 (b).

## Video ingest

### [DEFERRED] Video ingest — pirmais reālais ievākums (Kola LTV intervija) + diarizācijas crosstalk sanity-check

- **Stāvoklis:** `SELECT COUNT(*) FROM documents WHERE platform='video'` → **0** (2026-09-25). Ceļš pārbaudīts tikai ar vienu E2E testu (2026-07-22, KNL klips): `@video-extractor` STOP vārti nostrādāja (0 claims), bet diarizācijas robežas uz crosstalk asiņo abos virzienos (CLAUDE.md #13).
- **Rīcība:** pirmais reālais ievākums = **Kola LTV intervija** (mierīgs formāts); Briškena airBaltic debašu video NĒ. Pirms rakstīšanas: (a) brīdinājums, ja `suggested_speakers.json` confidence 0.0; (b) per-segment pārbaude «saturs atbilst runātājam?» (ministra pirmās personas frāzes pret intervētāja «Jūs sakāt»).
- **Trigeris:** operatora atsevišķa sesija (verdikts 51, § Atliktais 51). **Īpašnieks:** operators.
