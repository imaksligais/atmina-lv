# Handoff 2026-09-23 (nakts sesija) — backlog FIX vilnis, apgriezto doku backfill, RSS ievads

**Stāvoklis:** viss komitēts un pushots (privātais `570828a2`), publiskais spogulis `ab8fe54`, CI zaļš. Nekas nav deployots.

## Izdarīts
- 6 backlog FIX (SWE-2 aģenti, pārskatīti): Saeimas 4. paterns 34-arg; ziņu saraksta dublikāti; `ingest_url --politician-id` = runātājs (+ matcher rescan glabātās lomas likums — CHANGELOG 2026-09-23 (1)); sintēžu `data-label`; `assets/nvv*.js`. `.png`→PNG pārkodēšana ATSAUKTA (§ Ne-darīt).
- `src/soft_404.py` (tikai lsm.lv dod mīksto 404), `scripts/backfill_truncated_docs.py`, izmēģinājums 48 doki → +16 claims, 33 citāti aizstāti ar burtisku tekstu (`scripts/replace_claim_quotes.py`, CHANGELOG 2026-09-23 (2)).
- RSS ingests vairs nemet ievadu (CHANGELOG 2026-09-23 (3)). **Šodienas pirmais ingests:** ~60 jau izskatītu doku vienreiz atgriezīsies ekstrakcijas rindā (gaidāms, ne defekts).

## Atvērts (operatora lēmumi)
- Pilnā apgriezto doku pārlāde ~2 600 (`backlog/avoti.md`); aģentiem brīfs `docs/plans/2026-09-23-quote-replacement-brief.md`.
- Aug–sep doki bez ievada ~3 400 (`backlog/avoti.md` (d)).
- Izmēģinājuma atlikums: 19 citāti bez politiķa vārdiem + ~27 stance atradumi, Siliņa doc 16435, LSM `utm` dublikāti, Krauze `minor_shift` kandidāts — `backlog/dati-db.md` 2026-09-23 + `docs/audits/2026-09-23-backfill-trial48-reextract.md`.
- DB momentuzņēmums `data/atmina.db.pre-backfill-trial48-20260923.db` (2,7 GB) — dzēst, kad izmēģinājums apstiprināts.
