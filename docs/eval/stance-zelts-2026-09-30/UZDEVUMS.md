# Eval v4 (2026-09-30) — palīgu uzdevumi

Recepte, lai kārtu var atkārtot. `build_gold.py` → `packs/pNN.json` + `gold.json`; ekstraktori → `out/<variants>_pNN.json`; `score.py prep` → `grade_in/gNN.json`; vērtētāji → `grade_out/gNN.json`; `score.py report`.

Varianti: `vecais` = `prompt-vecais/claim-extractor.md` (kopija no `f4dd442b`), `jaunais` = `prompt-jaunais/claim-extractor.md` + `.claude/references/claim-extractor/`.

## Ekstraktora uzdevums ({VARIANT}, {PACK})

```text
Tu esi @claim-extractor eval skrējienā (DRY-RUN). Darba mape E:\atmina.

1. Tavi noteikumi ir failā E:\atmina\docs\eval\stance-zelts-2026-09-30\prompt-{VARIANT}\claim-extractor.md — izlasi to pilnībā un ievēro kā savu aģenta promptu. Drīksti lasīt failus, uz kuriem noteikumi norāda (atsauces failus, rubriku, src/topic_map.py).
2. Ievade: E:\atmina\docs\eval\stance-zelts-2026-09-30\packs\{PACK}.json — dokumenti, katram norādīts politiķis (pid, vārds, slota tips), kura pozīcijas meklēt. Tas ir tas, ko tev būtu devis get_politician_documents().
3. DRY-RUN: DB neizmanto vispār — nekādu src.* importu, sqlite, save_analysis, get_*, search_similar_claims, store_*. Dublikātu un pretrunu soļus izlaid (nav pieejami). Nelasi nekādus citus failus mapē docs/eval/stance-zelts-2026-09-30 un docs/audits (izņemot RUBRIKA.md, ja noteikumi uz to norāda) — tur ir atbildes.
4. Katram dokumentam pieņem lēmumu tieši tā, kā to darītu īstā rutīnā, un pierakstī claim dict tieši tādus, kādus nodotu save_analysis (ar tiem laukiem, ko prasa TAVI noteikumi).
5. Raksti TIKAI failu E:\atmina\docs\eval\stance-zelts-2026-09-30\out\{VARIANT}_{PACK}.json: JSON masīvs, viens objekts katram dokumentam ievades secībā:
   {"doc_id": N, "pid": N, "decision": "extract"|"empty", "empty_reason": "…"|null, "claims": [ {claim dict}, … ]}
6. Aizliegts: git komandas, kas maina stāvokli (stash, checkout --, restore, reset, commit, add); jebkuru citu failu rakstīšana. Ja vajag Python: E:\atmina\.venv\Scripts\python.exe ar PYTHONUTF8=1.
Atbildē tikai viena rinda: cik dokumentu apstrādāts, cik claims, cik empty.
```

## Vērtētāja uzdevums ({G})

```text
Tu esi akls stance vērtētājs. Darba mape E:\atmina.

1. Izlasi E:\atmina\docs\audits\2026-09-30-stance-izlase\RUBRIKA.md — tā ir tava rubrika.
2. Ievade: E:\atmina\docs\eval\stance-zelts-2026-09-30\grade_in\{G}.json — dokumenti; katram doc_text, politiķis un saraksts ar stance (anonīmi id "sNNN", jaukta secība, dažādu autoru). Dažiem dokumentiem ir "reference" — operatora verificēta pareizā pozīcija.
3. Katram stance: grade (A_WITHDRAW|B_REWRITE|C_LANGUAGE|D_OK|U_UNVERIFIABLE) pēc rubrikas, vērtējot TIKAI pret doc_text (ne pret reference). Īss why (angliski, 1 teikums). Ja dokumentam ir reference: matches_reference = "yes" (izsaka to pašu pozīciju), "partial" (daļu), "no".
4. Vērtē katru stance neatkarīgi; nemeklē, kurš to uzrakstīja.
5. Raksti TIKAI E:\atmina\docs\eval\stance-zelts-2026-09-30\grade_out\{G}.json: JSON masīvs [{"sid": "sNNN", "grade": "…", "why": "…", "matches_reference": "yes"|"partial"|"no"|null}].
6. Tikai lasīšana; nekādas DB rakstīšanas; nekādu git mutāciju; neraksti citus failus; nelasi citus failus šajā mapē (out/, gold.json u.c.).
Atbildē tikai viena rinda: cik stance novērtēts un sadalījums pa pakāpēm.
```
