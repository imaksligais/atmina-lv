# Veco neizskatīto pāru sweep — ekstrakcija pēc doc id (brīfs @claim-extractor)

Tu strādā repo `E:\atmina` (cd tur PIRMS jebkā). Python: `.venv/Scripts/python.exe` ar `PYTHONUTF8=1` un `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_DEACTIVATE_ASYNC_LOAD=1` (atmiņa — 2026-10-04 bija segfault pie embedding ielādes; ja `save_analysis` atgriež `transaction_rolled_back` vai process nokrīt, atkārto to pašu izsaukumu vienreiz). Nekad kails `python`. Ievēro `.claude/agents/claim-extractor.md` pilnībā — šis brīfs to papildina, ne aizstāj (īpaši § 4 confidence: 0.5–0.6 → `reasoning` sākas ar `NEEDS_REVIEW: <pazīme>`; skaidrs atstāsts bez citāta = 0.65 bez marķiera tikai, ja izpildās visi 4 nosacījumi).

## Konteksts

Šis brīfs pavada plānus, ko izdod `scripts/plan_stale_sweep.py` — tā ir rutīnas soļa «2b. Veci neizskatīti pāri» iztukšošanas komanda (`/dienas-rutina`; runbook `wiki/operations/operacijas.md` § Veci neizskatīti pāri). Tavi dokumenti ir vecāki par dienas rindas logu — **ņem tos TIKAI pēc id** ar tiešu SELECT (`SELECT id, platform, source_url, published_at, scraped_at, title, content FROM documents WHERE id IN (...)`), nekad no dienas rindas. Savu sarakstu saņem ar `scripts/sweep_unit.py <atslēga> <vienība> <gabals> --plan <ceļš>`. Apstrādā tikai sava saraksta (pid, doc) pārus. Pirmais šāds sweep bija 2026-10-05 (`docs/audits/2026-10-05-backlog-sweep/`).

Daži doki ir sarakstā `already_reviewed` — tos jau izskatīja CITAM politiķim (`reviewed_at` ir per-dokuments; piemēram, jauni deputāti dokos, kas jau bija izskatīti). Tos NEizlaid zīmoga dēļ: ekstraktē tieši savam pid.

## Uzdevums katram (pid, doc) pārim

1. Izlasi pilno `content`. T1/T13: pārliecinies, ka runā tieši šis izsekotais politiķis (vārdabrāļi, ģimenes locekļi ar to pašu uzvārdu, biroja/preses dienesta balss bez vārda → nav viņa pozīcija). Šaubas par atribūciju → nav pozīcijas, ieraksti `attribution_doubts`.
2. Pozīcijas glabā caur `src.analyze.save_analysis(pid, …)` — katram politiķim atsevišķs izsaukums tikai ar viņa claims. `stated_at` = `documents.published_at` datums (NEKAD šodiena), `analysis_date` = šodiena, `sentiment=0.0`, `source_url` obligāts (bez tā claim tiek klusi nomests).
3. **Dublikāti:** pirms `save_analysis` izsauc `get_existing_claims(pid, days=…, stated_around=<raksta datums>)` (days pietiekami liels, lai aptvertu raksta datumu). Tā pati nostāja citā avotā ±5 d jau DB → NEGLABĀ, ieraksti `duplicates_skipped`. Idempotence `(opponent_id, source_url, topic)`: divas nostājas vienā tēmā no viena doka apvieno vienā claim (T2).
4. **Visi tavi izlasītie doki bez pozīcijas → `empty_doc_ids`** tajā pašā politiķa `save_analysis` izsaukumā (T5). Ja politiķim nav nevienas pozīcijas, tik un tā izsauc `save_analysis` ar `claims=[]` un `empty_doc_ids`. Nekad nezīmogo dokumentu, ko neesi izlasījis. Beigās katram tavam pārim jābūt `document_politicians.extracted_at IS NOT NULL` (un katram tavam `subject` dokam `reviewed_at IS NOT NULL`) — pārbaudi ar SELECT.
5. Pēc katra `save_analysis` izlasi `failures` un salīdzini glabāto skaitu ar nodomāto (T3).
6. Pretrunas (inv. 7): katrai jaunajai pozīcijai `src.tools.search_similar_claims(pid, stance, claim_type_filter=['position'])` pret politiķa vēsturi. Kandidātus **tikai ziņo** — `store_contradiction` NESAUC.
7. Ja dokumentā runā CITS izsekots politiķis ar savu nostāju — neekstraktē, ieraksti `other_speakers` (doc id + vārds).

## Platformu specifika

- **twitter / x_mention:** satīras konti un izdomāti «citāti» ir bieži (vārti claim-extractor.md); RT ar trešās puses citātu nav paša pozīcija. Vēsturiski tvīti (līdz 2022) — `stated_at` = tvīta datums.
- **vestnesis** (MK sēžu protokoli, rīkojumi, paziņojumi): valdības kolektīvs lēmums, paraksts vai dalība sēdē NAV personīga pozīcija. Pozīcija tikai, ja protokols piefiksē TIEŠI šī politiķa paša teikto/iebildumu/atsevišķo viedokli. Sagaidāms, ka lielākā daļa ir `empty` — tas ir derīgs rezultāts; neizdomā pozīcijas. (Tikai paraksta pārus rutīnas aktos jau iepriekš atzīmē `scripts/stamp_vestnesis_signatures.py`.)
- **web vecie raksti:** ja teksts joprojām nogriezts (<~80 vārdu, «Lai turpinātu lasīt») → `empty` ar iemeslu vai pozīcija ar `NEEDS_REVIEW: nogriezts avots`.

## Noteikumi

- LV gramatikas + stilistikas vārti katrai stance/reasoning (locījumi, garumzīmes, bez kalkiem); `quote` VERBATIM. `brief` raksti pilnos latviešu teikumos.
- Neraksti DB ar rokām (tikai `save_analysis`). **Nekādu git komandu** (`commit`, `stash`, `checkout --`, `restore`, `reset`, `switch`) — paralēli strādā citi aģenti vienā kokā. Nerenderē, nedeployo, nepalaid ingest.
- Neraksti skaitļus, kurus neesi izmērījis.
