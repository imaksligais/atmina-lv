# Handoff 2026-09-24 (vakara rutīna) — pārskats publicēts, Saeimas pēcdarbi rīt

**Stāvoklis:** dienas rutīna 24.09. pabeigta 11/11. Pārskats #643 publicēts (deploy `bed43be2`, verify_host 9/9, attēla varianti 4/4 HTTP 200). Izmaiņas **nav komitētas** (sk. § Komitēt).

## Rīt (2026-09-25) — Saeima, obligāti

1. **Pilnīguma audits 24.09. kārtējai sēdei.** Ielādē bija dzīvā lapa (`actual=1`, `DkId=99609e32-ba8c-40be-8162-222cefebb63f`) — tā nerāda apakšpunktu balsojumus, un pastāvīgajā darba kārtībā sēdei vēl nebija UUID. Kad UUID parādās kalendārā:
   `.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year 2026 --dates 2026-09-24`
   (manifestam jābūt svaigam — pārģenerē `data/saeima_backfill_sessions.json`, ja rīks STOP). Trūkstošs balsojums → `/saeima-ingest 2026-09-24` (idempotents).
   DB tagad: 79 balsojumi ar `vote_date='2026-09-24'` (id 8238–8316; 70 no 17.09. turpinājuma sēdes `1f916d52-…`, 9 no kārtējās).
2. **Kalendāra parsētājs izlaiž turpinājuma sēdes ar `A / B` etiķeti** (piem. «17 / 24»). Manifestā tās neparādās pie vēlākā datuma — tā pati klase, kas 2026-08-20 incidentā paslēpa sēdi 13 dienas. Ierakstīt BACKLOG (`backlog/` Saeimas tēma) un salabot `scripts/_p3_extract_sessions_2026-05-26.py` etiķešu atpazīšanu.
3. Sīkumi no ielādes: `append_bill_stage()` atraida posmu `1.lasījums priekšlikums` (8293/8294/8258 ierakstīti kā `nezināms`); darba kārtības parsētājs palaida garām 1120/Lm14; `Lm` dokumentu rezultāts glabājas kā «Paziņojums» arī tad, ja balsojums pieņemts (8305: 57:17:1); balsojuma 7190 kopsavilkums nokopēts no 771 (nepareizs).

## Komitēt (neiekomitēts darbs)

- Rollback faili: `data/rollback_claim_718154_stance_2026-09-24.sql`, `data/rollback_claim_718165_reattrib_2026-09-24.sql`, `data/rollback_context_note_641_party_2026-09-24.sql`, `data/rollback_brief_qa_2026-09-24.sql`, `data/rollback_brief_qa_round2_2026-09-24.sql`, `data/rollback_brief_qa_round3_2026-09-24.sql`, `data/rollback_recovery_queue_clear_2026-09-25.sql`.
- `wiki/` (wiki_sync + `wiki/dailies/2026-09-24.md`), `tests/fixtures/render_baseline_laws.json` (REGEN — tests lasa īsto `wiki/laws/`, ko wiki_sync atjaunina ar Saeimas datiem; testa nehermētiskums ir atsevišķs BACKLOG kandidāts), `data/saeima_backfill_sessions.json`.

## Izlemts 2026-09-25

- **Kulberga dienasgrāmatu `stated_at`** = datums iekavām, ja 7 dienu logā; vēsturiskās nebīda (CHANGELOG 2026-09-25 (1), `claim-extractor.md`). Pārbaudīt nākamajā dienasgrāmatas ierakstā, vai aģents to ievēro.
- Atgūšanas rinda iztīrīta (19 izskatīti pāri iezīmēti ar `extracted_at`, 0 atlikuši).

## Citi atradumi (nav steidzami)

- TypeSafe ēna 24.09.: veto Stepaņenko sakritībai doc «Braže … iekļauj Stepaņenko tēvu» (p=0.12) — iespējams zelta zaudējums, pārbaudīt `typesafe_veto_report.py`.
- `tracked_politicians.role` Ašeradenam «finanšu ministrs (demisionējis)», avoti — Tautsaimniecības komisijas priekšsēdētājs (T6).
- Ceļapīters: `party`=ZZS, bet `faction` pārsvarā NULL/JV — `/audit-integrity` check 9.
- Kučinskis #718013: `quote=NULL`, rediģētajā LSM rakstā (doc 114519) tagad ir burtisks citāts.
- Latkovskis (doc 115440, «kurš nozaga 12 centus») — pārklājuma robs.
