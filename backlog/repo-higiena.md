# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Repo higiēna / kods

### [OPEN] Vārtu saucēju atlikums — 13. pārbaudes kandidātu kopa un Dienas pārskata #7 bez nesēja publicēšanas brīdī

2026-08-09 audita četri vārti izpildīti (CHANGELOG 2026-08-09 (3), (4)); 17. pārbaude → citātu triāža 2026-09-30 (`docs/audits/2026-09-30-citatu-triaza.md`), 6. pārbaude → § Atliktais 57, 8. pārbaude → `avoti.md` truncated kampaņa. Paliek divi:

- **(a) `/audit-integrity` 13. pārbaude (stale vektori) ziņo arī `saeima_vote` rindas**, kuras Escalation 8 aizliedz labot (2026-08-21 verdikts jaunām balsojumu rindām vektoru nedod). Mērījums 2026-09-07: 171 karogota rinda, no tām 150 `saeima_vote`, actionable — **21 `position`**. *Rīcība:* izslēgt `claim_type='saeima_vote'` no kandidātu kopas un pārpublicēt bāzlīniju kā `checked=… flagged=21`.
- **(b) quality-bars Dienas pārskata #7** (attēla varianti + dzīvs HTTP 200) publicēšanas brīdī nav neviena nesēja — ne `brief-writer.md`, ne `dienas-rutina.md`; `graphics-designer.md` `make_variants` kļūmi aprij («never block approval on variant gen»), paliek tikai `/audit-integrity` pēc-fakta diska pārbaude. Saistīts: bijušais `dati-db.md` § 2026-09-22 (f), slēgts 2026-10-01 ([`docs/audits/2026-10-01-rutinas-atlikumi-triaza.md`](../docs/audits/2026-10-01-rutinas-atlikumi-triaza.md)).

*Īpašnieks:* operators (katrai rindai savs lēmums). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_repo-higiena.md`.

### [OPEN] Testu mutāciju izlases robi — 5 neaizsegti zari (2026-09-24)

Izlase (`docs/audits/2026-09-24-test-mutation-sample/README.md`, privāts): 20 biežāk mainītie testu faili, 81 tests, 95 mutācijas → **80/81 testu nogalina mutantu**. **Atlikušie robi — trūkst testa, ne jādzēš:** (1) `test_utc_column_is_never_read_bare` neķer UTC kolonnu, kas salīdzināta bez datuma funkcijas (`t.created_at >= ?`); (2) dubultie sargi, kur testi sasniedz tikai ārējo: `link_audit_row` otrā pārbaude, `backfill_truncated_docs` glabātās rindas pārbaude, pavediena stila pārbaude; (3) `_fetch_topics` neaktīvo politiķu izslēgšana (docstring sola, tests nav). **Nepārbaudīts apgalvojums:** `TestTensionDayBoundaryTimezone` publiskajā CI (UTC runneris) varētu izlaisties; CI kopš 09-24 liek `TZ=Europe/Riga` — pārbaudīt ar `-rs` nākamajā sync (skipu skaits CI 15 pret lokāli 3). *Īpašnieks:* orķestrators.

### [OPEN] Attēla paraksta pēcapstrādes vārts — (b) OCR/stūru heiristika (prompta aizliegums ieviests 2026-09-05)

2026-09-04 modelis brief attēlā (`brief_images` #310) apakšējā labajā stūrī uzzīmēja **izdomātu kursīvu mākslinieka parakstu**, lai gan `--no-text` prompts aizliedza tekstu. Anonīmai vietnei autorības zīme attēlā ir fabricēta atribūcija, un vārtos to neviens nemeklē. (a) prompta aizliegums ieviests (`src/graphics/prompt.py::TEXT_FREE_CONSTRAINTS` + `tests/test_graphics_prompt.py::test_text_free_constraints_forbid_authorship_marks`; CHANGELOG 2026-09-05 (4)), bet tas paļaujas uz modeļa paklausību.

*Rīcība (b):* pēcapstrādes vārts — OCR vai malu/stūru heiristika pār ģenerēto PNG pirms `save_image_row()`, kas karogo tumšus sīkstruktūras blāķus tukšajā malā. Līdz tam manuālā stūru apskate pirms apstiprināšanas paliek obligāta. *Īpašnieks:* operators (vai būvēt OCR).
