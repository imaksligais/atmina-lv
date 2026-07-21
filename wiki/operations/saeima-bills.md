# Saeima bills — operatorinstrukcija

## Mērķis

Likumprojektu (saeima_bills) izsekošana ļauj atmīnai sekot deputātu balsojumiem
**lielākā kontekstā**: katrs balsojums tiek piesaistīts likumprojektam → likumprojekta
stadijai → pamatlikumam (`base_law_slug`). Politiķa profila Likumprojekti tabs un
publiskā `/likumi.html` lapa atklāj šo plūsmu.

## Tipisks cikls (jauna sēde)

1. Atver Saeimas kalendāru (`https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1`),
   atrod nesenas balsojumu sesijas URL.
2. Palaiž `@saeima-tracker` aģentu ar sesijas URL.
3. Aģents:
   - Step 1-2: snapshot agendu, parse bills + URLs (Phase 1C jaunievedums)
   - Step 3-4: ievāc balsojumu rezultātus
   - Step 5: link vote → bill stage (Phase 1C jaunievedums)
4. Pārskata aģenta logus — STOP signāli (zem § Failure modes) prasa operatora
   darbību pirms turpināšanas.
5. Palaiž site renderēšanu:
   ```bash
   PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
   ```
6. Pārbauda:
   - `output/atmina/likumprojekti/<slug>.html` — jauni bill detail lapas
   - `output/atmina/likumi.html` — pamatlikumu indekss ar atjauninātu bill_count
   - `output/atmina/balsojumi.html#bills-list` — bills grid ar 3rd subtab

## Manuālā iesniedzēja pievienošana

Ja agents ziņo "STOP: unknown institutional submitter ...":

1. Pievieno jauno vērtību aģenta prompta `KNOWN_INSTITUTIONAL_SUBMITTERS`
   sarakstam (`.claude/agents/saeima-tracker.md` § Step 2.A.bis).
2. Ja jaunā vērtība arī nav atpazīta `parse_agenda_snapshot()` plūsmā,
   paplašini regex `_parse_institutional_submitter()` (`src/saeima/parsing.py`).
3. Re-run aģentu.

## Backfill atkārtošana

Šie skripti ir idempotenti (`WHERE base_law_slug IS NULL` filter aizsargā):

```bash
python scripts/backfill_saeima_bills.py        # restore bills + stages from votes
python scripts/backfill_base_law_slug.py       # restore base_law_slug matches
```

Drošs re-run, ja kāda lauka aizpilde palika nepilna pēc DB restore vai migration.

## Troubleshooting

### Agenda parse atgriež `[]`
HTML struktūra titania.saeima.lv mainīta. Atver sesijas URL pārlūkprogrammā,
salīdzina ar `parse_agenda_snapshot` regex (`src/saeima/parsing.py`). Ja .html ir
mainījies, fix parser pirms re-run.

### `base_law_slug=NULL` spītīgi
`title` lauks varbūt nesatur kanonisku likuma nosaukumu. Pārbaudi vai pareizais
`wiki/laws/<slug>.md` fails eksistē. Manuāli var iestatīt:
```sql
UPDATE saeima_bills SET base_law_slug='...' WHERE document_nr='...';
```
Tas ir viens no maziem izņēmumiem, kas NEIET caur Pipeline Invariant 12, jo
`base_law_slug` nav denormalizācija — tā ir join key.

### Junction empty pēc agent run
`match_submitters_to_politicians` fail-loud — pārbaudi `unmatched submitters`
logus. Visdrīzāk submitter_names lauka parsēšana neizdevās — atver
`parse_agenda_snapshot` output un salīdzina pret faktisko agenda HTML.

### Vote stored, bet bill_id NULL
`resolve_bill_from_motif()` neatpazina motif (Tier-3 gadījums, log+turpina).
Pārbaudi vai bill ar šo `document_nr` jau eksistē DB — ja nē, Step 2 droši vien
izlaida to (vai parse_agenda_snapshot to nesaprata).

## Saistītie faili
- `src/saeima/` pakete — helper funkcijas pa moduļiem:
  - `parsing.py` — `parse_agenda_snapshot`
  - `bills.py` — `upsert_bill`, `append_bill_stage`, `resolve_bill_from_motif`
  - `votes.py` — `match_submitters_to_politicians`, `process_vote_snapshot`
  - `schema.py` — `init_saeima_tables`, `init_saeima_bills`
  - `claims.py` — `_motif_to_topic`, `_vote_salience`
  Visi pieejami ar `from src.saeima import …` (paketes __init__.py re-eksports).
- `.claude/agents/saeima-tracker.md` — aģenta operatorinstrukcija
- `tests/test_saeima_bills*.py` — Phase 1A unit + integration
- `wiki/CHANGELOG.md` — Phase 1A/B/C lēmumu vēsture
- `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` — master spec
