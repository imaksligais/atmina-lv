# VID amatpersonu deklarācijas (manuāla, mēneša cikls)

## Mērķis

Strukturēti ielādēt mūsu izsekoto politiķu (`relationship_type='tracked'`) amatpersonu
deklarācijas no [www6.vid.gov.lv/VAD](https://www6.vid.gov.lv/VAD) — pilna 11
sekciju datu kopa (amati, NĪ, kapitāldaļas, transports, naudas uzkrājumi, ienākumi,
darījumi, parādi, aizdevumi, ģimene + sec 12 pension flags).

## Tipisks cikls (mēneša rutīna)

1. Palaiž full sweep:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_vad_declarations.py
   ```
2. Apjēga: ~28 min steady-state (152 politiķi × 10s search + ~2 jauni detail × 3s).
   Peak aprīlis-maijs: ~33 min. Initial backfill (visu deklarāciju ielāde): ~48 min.
3. Output: per-politiķis rinda ar `new=N present=N skip_role=N skip_legacy=N errs=N`.
4. Pārbauda log entry `wiki/log-ingest/<gads-mēnesis>.md`.
5. Re-render publisko vietu:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
   ```
6. Pārbauda 3-5 sample profilus: `output/atmina/politiki/<slug>.html` Deklarācijas tabā ir 1+ ieraksts.

## Bootstrap (vienreizējais)

Pirms pirmā sweep:

1. Pārliecinies, ka `tracked_politicians` satur visus politiķus, kurus gribi sekot.
2. Verificē hyphenated uzvārdus VID portālā (manuāls test):
   ```bash
   .venv/Scripts/python -c "from src.vad import VadClient; print(len(VadClient().search('Agita', 'Zariņa-Stūre')))"
   ```
   Expected: 1+ row (verificē, ka portāls pieņem defisi).
3. Palaiž ar `--limit 5 --dry-run` lai apstiprinātu plūsmu pirms full sweep.

## Idempotence

UNIQUE atslēga = dabīgais identifikators `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)` (skat. spec § 4.1, § 7).

`vad_uuid` rotē per-call (anti-scrape session-bound nonce — F11 atklājums spec § 15.1). NESALIETOJAMS idempotencei. Glabājas tikai audit/debug priekš (latest seen value, refresh ar katru sweep).

Pre-fetch dedup: orchestrator pārbauda DB pa `(kind, year, position_title)` no search-row label PIRMS detail fetch. Ja jau eksistē — refresh `vad_uuid`, SKIP detail fetch (saglabā VID throttle).

## Failure modes

### "STOP: 0 rows for {politician}"
Politiķa vārds VID portālā neiet caur. Pārbauda:
1. Vai `tracked_politicians.name` atbilst kanoniskam vārdam (skat. memory `feedback_matcher_no_diacritic_strip`).
2. Vai politiķis ir amatpersona (žurnālisti, organizācijas — gaidāmi 0 rezultāti).
3. Vai vārds ir multi-token un naïve split kļūdains — pievieno `_NAME_OVERRIDES` dict `src/vad/matcher.py`.

### "skip_role=N" augsts skaits
VID atgrieza politiķim daudz amatu, kuriem mūsu `tracked_politicians.role` neatbilst. Pārbauda specific row-mismatches log warn'os (`grep vad-role-mismatch`). Ja false-positive skip — paplašina `role_matches` keyword sarakstu `src/vad/matcher.py`.

### Pagination warning ">100 rows"
Politiķim VID atgrieza neparasti daudz rindu. Pārbauda manuāli portālā — varbūt homonīms. Bounded loop apstājas pie 200; ja jāpieaugās, log warn ir signāls operatora intervencei.

### HTTP 429 / 5xx
Throttle ir per-client (10s search, 3s detail). Ja 429 atkārtoti — palielini throttle `src/vad/fetch.py:SEARCH_THROTTLE_S`. Ja 5xx atkārtoti — VID portāls down, palaiž nākamajā dienā.

### `httpx.ReadTimeout` uz search
Sub-second back-to-back searches izsaka ReadTimeout (F12 atklājums). Throttle 10s ir minimum; samazināt nedrīkst.

## Pārbaudes vaicājumi

```bash
# Cik politiķiem ir vismaz 1 deklarācija?
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
print(con.execute('SELECT COUNT(DISTINCT opponent_id) FROM vad_declarations').fetchone())
"

# Politiķi BEZ deklarāciju (var būt nepareizs role-match)
.venv/Scripts/python -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
for r in con.execute('''
    SELECT tp.name, tp.role FROM tracked_politicians tp
    LEFT JOIN vad_declarations vd ON vd.opponent_id = tp.id
    WHERE tp.relationship_type = 'tracked' AND vd.id IS NULL
    ORDER BY tp.name
'''):
    print(f\"{r['name']:<35} role={r['role']!r}\")
"
```

## Datu modelis — atsauce

11 tabulas (skat. spec § 4 pilnam DDL):
- `vad_declarations` — header (UNIQUE pa natural key)
- `vad_positions` — sec 2 amati
- `vad_real_estate` — sec 3 NĪ
- `vad_companies` — sec 4 kapitāldaļas
- `vad_vehicles` — sec 5 transports
- `vad_savings` — sec 6 naudas uzkrājumi (cash + bank polymorphic)
- `vad_income` — sec 7 visi ienākumi
- `vad_transactions` — sec 8 darījumi >20 MMA
- `vad_debts` — sec 9 parādi >20 MMA
- `vad_loans_given` — sec 10 izsniegtie aizdevumi >20 MMA
- `vad_family` — sec 14 ģimene

## Spec atsauce

`docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` (master commit `dda5478` ar F11+F12 amendments)
