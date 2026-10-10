# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Avoti

### [OPEN] Vēsturisko dokumentu backlogi atsevišķai sweep sesijai

> **2026-10-05 — `subject` backlogs iztukšots** ([`docs/audits/2026-10-05-backlog-sweep/`](../docs/audits/2026-10-05-backlog-sweep/README.md)). Darba saraksts: 2 178 (pid, doc) pāri, `role='subject'`, aktīvs pēc `queue_politician_sql`, bez claim, doks `reviewed_at IS NULL` (vai 15. Saeimas jaunais deputāts), `scraped_at < 2026-10-04 05:00` vai publicēts pirms 10-03 — web 717, twitter 571, vestnesis 872, x_mention 18. Izpildīja 223 Opus `claim-extractor` aģenti (izmēģinājums 2 + galvenā 63 + atlikums 30 + Vēstnesis 78 + atgūšana 47 + stale28 3): **614 glabātas pozīcijas, 2 dublikāti dzēsti ar rollback** (`SELECT COUNT(*) FROM claims WHERE claim_type='position'` 8 105 → 8 717). Pāru pārklājums pēc tam: `src.routine.stale_extraction_pairs(db, '2026-10-05')` → main 0, Vēstnesis 0. Zemāk esošie 09-25 skaitļi ir vēsture. **Lai neuzkrātos atkal:** [`docs/plans/2026-10-05-backlog-uzkrasanas-varti.md`](../docs/plans/2026-10-05-backlog-uzkrasanas-varti.md).

Dienas rutīna šos dokus nekad nesasniedz; tie prasa mērķētu sweep pa politiķim (pa ≤12 sesijā) vai `historic-backfill` loga paplašinājumu. Neizlasītu dokumentu nekad nezīmogo ar `empty_doc_ids` (T5/T11). Pārmērīts 2026-09-25:

- **Nepārskatīti pa politiķim** (`COUNT(DISTINCT d.id)` pār `documents d JOIN document_politicians dp ON dp.document_id=d.id WHERE dp.politician_id=? AND d.reviewed_at IS NULL`): Šnore 124 → **170**, Staķis 139 → **157**, Ozols 64 → **179**, Pūpols 829 → **1 196**, Lindberga 194 → **267**. Rinda lielākoties ir pieminējumu josla; izskatīšanas vērta ir `mentioned` (+ `vestnesis`) apakškopa.
- **Nepārskatīti `subject` doki aktīvajiem** (`… JOIN document_politicians dp ON dp.document_id=d.id AND dp.role='subject' JOIN tracked_politicians tp ON tp.id=dp.politician_id WHERE d.reviewed_at IS NULL AND tp.relationship_type!='inactive'`, bez `data/backfill_batch3_updated_ids_2026-09-24.txt` dokiem): **1 363** (vestnesis 801, twitter 355, web 189, x_mention 18); Kulbergs 136 → **284**, Lapsa 106 → **99**. 3. backfill partijas 400 doki nav šeit — tie ir truncated ieraksta darbs.
- **Vecā `subject`-aste** (1. sweep izpildīts 2026-08-06): Lapsa, Velps (51433, 47607, 47608 + 3 vecāki), Stendzenieks, Kulbergs (vecāki `web subject`), Judins doc 26496 (pārlāde, ne ekstrakcija), doc 64398 (atvēršana = operatora lēmums). Neizšķirts noteikuma kandidāts: **retvīts par sevi** — ja pirmavots jau DB → tukšs; ja nav, anonss ir vienīgais pierādījums.

*Īpašnieks:* operators (sesijas laiks). Quote-tweet/atbilžu satura robeža → `wiki/operations/content-pipeline.md` § Zināmās ievākšanas robežas.

### [OPEN] lsm/diena/tvnet truncated backfill — 3. partijas ekstrakcija (400 doki), novecojuši chunki, ievads «pilnajiem» dokiem

Sargs (`src/soft_404.py`) un skripts (`scripts/backfill_truncated_docs.py`) darbojas; izmēģinājums un 1.–2. partija izpildīti (`docs/audits/2026-09-23-backfill-batch1/`, `docs/audits/2026-09-23-backfill-batch2/`). Paliek:

- **(a) 3. partijas ekstrakcija — IZPILDĪTA 2026-10-05** kā daļa no vēsturiskā sweep (`docs/audits/2026-10-05-backlog-sweep/`): 10-05 pirms sweep pārmērīts 400/400 `reviewed_at IS NULL`, 416 pāri / 62 politiķi; pēc sweep `SELECT COUNT(*) FROM documents WHERE id IN (<data/backfill_batch3_updated_ids_2026-09-24.txt>) AND reviewed_at IS NULL` → 0. Ko tas izpildīja: `main` + `main_left` kārtu `claim-extractor` aģenti (žurnāli `main_journal.jsonl`, `main_left_journal.jsonl`).
- **(b) Chunki novecojuši:** 398 no 399 pārlādēto doku chunki sedz <50 % pašreizējā teksta (`document_chunks` `SUM(LENGTH)` pret `LENGTH(documents.content)`); skripts chunkus apzināti neatjauno. Tas pats pārchunkošanas darbs sedz arī 418 `scripts/ingest_url.py` web dokus, kuri nekad nav embedoti (`wiki/operations/operacijas.md`) — ja pārchunko, tad abas kopas vienā darbā.
- **(c) Ievads trūkst arī «pilnajiem» dokiem** (augusts–septembris, `word_count≥90`, lsm/diena; 7/8 izlasē): ingests salabots 2026-09-23 (CHANGELOG 2026-09-23 (3)), vēsturiskie nav — ievadu var atgūt no lapas `description`/RSS.

*Īpašnieks:* operators ((a) laiks, (b) un (c) — atsevišķi lēmumi). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_avoti-saeima-ui.md`.

### [DEFERRED] diena.lv RSS ievāc saistīto virsrakstu sānjoslu → viltus `subject` (doc 87866)

Doc 87866 ir laika prognozes raksts; Rinkēviča vārds tajā ir tikai navigācijas blokā ar saistītajiem virsrakstiem (`instr(content,'Rinkēvič')` = 720), bet junction rinda ir `subject`, un `match_politicians` to atjaunotu (pārbaudīts 2026-09-25). Tā nav namesake kolīzija (`negative_patterns` neder) — korpusā ir par daudz, ne par maz. *Trigeris:* otrā instance. *Rīcība:* `_clean_extracted_text` / trafilatura robežu pastiprināšana, ne matcher; rindas dzēšana ar rollback. *Īpašnieks:* operators. Pārcelts no `matcher.md` 2026-08-15 (b).

## Video ingest

### [DEFERRED] Video ingest — pirmais reālais ievākums (Kola LTV intervija) + diarizācijas crosstalk sanity-check

- **Stāvoklis:** `SELECT COUNT(*) FROM documents WHERE platform='video'` → **0** (2026-09-25). Ceļš pārbaudīts tikai ar vienu E2E testu (2026-07-22, KNL klips): `@video-extractor` STOP vārti nostrādāja (0 claims), bet diarizācijas robežas uz crosstalk asiņo abos virzienos (CLAUDE.md #13).
- **Rīcība:** pirmais reālais ievākums = **Kola LTV intervija** (mierīgs formāts); Briškena airBaltic debašu video NĒ. Pirms rakstīšanas: (a) brīdinājums, ja `suggested_speakers.json` confidence 0.0; (b) per-segment pārbaude «saturs atbilst runātājam?» (ministra pirmās personas frāzes pret intervētāja «Jūs sakāt»).
- **Trigeris:** operatora atsevišķa sesija (verdikts 51, § Atliktais 51). **Īpašnieks:** operators.

### [OPERATOR] Baško oriģinālais bezdeficīta budžeta tvīts — korpusā tikai J. Hermaņa RT

Baško tvīts par bezdeficīta budžetu (RT'ots @J_Hermanis 2026-09-11 19:37 UTC, doc 106763) nav @JazepsBasko laika joslas ievākumā — 288 `JazepsBasko/status/` doki, ar «deficīt» 3, neviens nav 09-11 oriģināls (pārbaudīts 2026-09-25). RT teksts oriģinālā ID nenes, un `src/social.py` viena tvīta ielādes pēc ID nav. **Rīcība:** ID no @JazepsBasko profila ar roku → `scripts/ingest_url.py --url https://x.com/JazepsBasko/status/<id> --politician-id 30`. **Īpašnieks:** operators (vai fakts profilā vajadzīgs; RT jau nes tekstu).

### [OPERATOR] Viena tvīta retvīts no diviem sekotiem kontiem — otrais retvītotājs zūd, kursors virzās (atrasts 2026-10-09)

- **Ķēde:** `src/x_scraper.py:109` būvē RT tekstu `RT @autors: <teksts>` bez retvītotāja → abiem retvītotājiem identisks `content_hash` → `src/db.py:400-423` UNIQUE `content_hash` atgriež `None` (apzināts copypasta vārts) → `src/social.py:190` izlaiž → `src/social.py:229-231, 296-300` kursors virzās pēc IELĀDĒTAJIEM, ne saglabātajiem tvītiem. Otrais retvītotājs nedabū ne dokumentu, ne `document_politicians` saiti; kļūdas nav.
- **Instances:** Ņenaševa (pid 92) — 07-31 (pirmais MStakis, doc 77594), 08-12 (suvajevs, doc 85885), 09-24 (MStakis, doc 115552). Saucējs: 19 no 140 aktīviem first_party kontiem kursora tvīts nav `documents` (kandidāti, ne mērīti zudumi — daļa var būt <50 zīmju tvīti).
- **Sekas:** maza (tīrs RT pozīciju nedod), bet kluss zudums. **Lēmums vajadzīgs:** tvītiem cita dedup atslēga (URL+teksts) / otra rinda ar `near_dupe_of` / retvītotāju pievienot esošajam RT dokumentam kā `mentioned`.
- **Blakus defekts (≤5 r.):** `src/social.py:307-313` žurnālā `documents_added` = ielādēto skaits, `documents_skipped=0`, kaut `total_stored` ir turpat (klusā panākuma klase); `fetch_all_mentions` (`:468`) to dara pareizi.
- **Īpašnieks:** operators.
