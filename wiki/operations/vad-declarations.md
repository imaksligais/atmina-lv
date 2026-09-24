# VID amatpersonu deklarācijas (manuāla, mēneša cikls)

## Mērķis

Strukturēti ielādēt mūsu izsekoto politiķu (`relationship_type='tracked'`) amatpersonu
deklarācijas no [www6.vid.gov.lv/VAD](https://www6.vid.gov.lv/VAD) — pilna 11
sekciju datu kopa (amati, NĪ, kapitāldaļas, transports, naudas uzkrājumi, ienākumi,
darījumi, parādi, aizdevumi, ģimene + sec 12 pension flags).

## Tipisks cikls (mēneša rutīna)

1. Palaiž full sweep:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/ingest_vad_declarations.py
   ```
2. Apjēga: ~28 min steady-state (152 politiķi × 10s search + ~2 jauni detail × 3s).
   Peak aprīlis-maijs: ~33 min. Initial backfill (visu deklarāciju ielāde): ~48 min.
3. Output: per-politiķis rinda ar `new=N present=N skip_role=N skip_legacy=N skip_denylist=N errs=N`.
4. Pārbauda log entry `wiki/log-ingest/<gads-mēnesis>.md`.
5. Re-render publisko vietu — standarts ir šaurais renders, pilnais tikai release/baseline:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.render --only=politiki,personas
   # pilnais (~3 min, tikai release/baseline):
   # PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
   ```
6. Pārbauda 3-5 sample profilus: `output/atmina/politiki/<slug>.html` Deklarācijas tabā ir 1+ ieraksts.

## Bootstrap (vienreizējais)

Pirms pirmā sweep:

1. Pārliecinies, ka `tracked_politicians` satur visus politiķus, kurus gribi sekot.
2. Verificē hyphenated uzvārdus VID portālā (manuāls test):
   ```bash
   .venv/Scripts/python.exe -c "from src.vad import VadClient; print(len(VadClient().search('Agita', 'Zariņa-Stūre')))"
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
1. Vai `tracked_politicians.name` atbilst kanoniskam vārdam (matcher diakritikas nesalāgo — sk. CLAUDE.md § Schema invariants).
2. Vai politiķis ir amatpersona (žurnālisti, organizācijas — gaidāmi 0 rezultāti).
3. Vai vārds ir multi-token un naïve split kļūdains — pievieno `_NAME_OVERRIDES` dict `src/vad/matcher.py`.

### "skip_role=N" augsts skaits
VID atgrieza politiķim daudz amatu, kuriem mūsu `tracked_politicians.role` neatbilst. Pārbauda specific row-mismatches log warn'os (`grep vad-role-mismatch`). Ja false-positive skip — paplašina `role_matches` keyword sarakstu `src/vad/matcher.py`.

### Pagination warning ">100 rows"
Politiķim VID atgrieza neparasti daudz rindu. Pārbauda manuāli portālā — varbūt homonīms. Bounded loop apstājas pie 200; ja jāpieaugās, log warn ir signāls operatora intervencei.

### HTTP 429 / 5xx
Throttle ir per-client (10s search, 3s detail). Ja 429 atkārtoti — palielini throttle `src/vad/fetch.py:SEARCH_THROTTLE_S`. Ja 5xx atkārtoti — VID portāls down, palaiž nākamajā dienā.

### Homonīmu piesārņojums (sveši tādvārži deklarācijās)

VAD search atdod VISAS personas ar to pašu vārdu; `role_matches` nesargā pret
tādvārdi ar līdzīgu amatu (divi «Andris Bērziņš» pašvaldībās). Simptoms: vienam
pid deklarācijas ar nesaderīgiem ģimenes locekļiem vai savstarpēji izslēdzošu
karjeru. 2026-09-19 pilna verifikācija atrada 129 svešas deklarācijas pie ~20
izsekotajiem (trīs purge partijas, visas ar rollback SQL + denylist ierakstiem).

Verifikācijas secība (katra nākamā metode sedz iepriekšējā aklo zonu):

1. **Re-parse round-trip** — `raw_html` pārdzen caur `parse_declaration` un
   salīdzina pret DB apakštabelām (`scratchpad/vad_probe/verify_stored.py`).
   Ķer parser-drift/bugus, ne homonīmus.
2. **Ģimenes-paraksts** — vecāku (Māte/Tēvs) vārdi vienai personai NEKAD
   nemainās; divas dažādas mātes vienā pid = divi cilvēki. NEstrādā vecām
   (2002–2013) deklarācijām — tām ģimenes sadaļas vispār nav.
3. **Amata līnija** — tukšās-iestāžu (legacy) deklarācijas šķeļ pa
   `position_title` progresiju. Tukša iestāde ≠ svešs cilvēks: karjera var būt
   nepārtraukta (Citskovskis: «Jurists → Priekšnieka vietnieks» = tā pati PMLP
   līnija). Svešs = nesaderīga līnija (Mūrniecei ieplūda ministrijas lietvede
   2002–12, kad viņa bija žurnāliste).
4. **Ienākumu avoti kā identitātes pirksts** — `vad_income.source` glabā darba
   devēja nosaukumu; bieži atrisina identitāti ātrāk par Jev (Hermanis:
   BANKU AUGSTSKOLA 2002 → senators 2024; Toro/Gobzems: tieslietu/maksātnespējas
   sistēma pirms politikas).
5. **Jev same-person** — tikai strīdīgajiem klasteriem. Nenoteiktā zona
   (~0,3–0,55) = atstāt flagged, ne purge (Zalāns: 19 dekl. = ≥2 tādvārži,
   bet nevienu nevar ne apstiprināt, ne noraidīt).

Purge konvencija: `data/purge_vad_*.sql` (DELETE pa decl id sarakstam) +
`data/rollback_vad_*.sql` (pilna INSERT rezerve) + ieraksti
`data/vad_denylist.json` (`pid`, `vad_uuid`, `match`, `reason`), lai nākamais
sweep tos neievelk atpakaļ — ingest rāda tos `skip_denylist=N`. Denylist
papildināšana TIKAI ar operatora apstiprinājumu (readme laukā denylist failā).

Diakritikas: VAD search ir jutīgs pret tām — «Baranniks» atdod 0,
«Baraņņiks» 13. Nulle rezultātu ≠ deklarāciju nav; pārbaudi ar diakritikām.

### `httpx.ReadTimeout` uz search
Sub-second back-to-back searches izsaka ReadTimeout (F12 atklājums). Throttle 10s ir minimum; samazināt nedrīkst.

## Analīzes lapas `analizes/vad-2026` atsvaidzināšana

Lapa ir statisks Markdown ar rokām ieliktiem skaitļiem — pēc katras ielādes, tīrīšanas
vai parsera labojuma tie dreifē (2026-05-05 → 2026-09-20 nostāvēja četrus mēnešus ar
vienu tādvārža rindu § 4 un galveni 2262/144 pret DB 2254/159). Recepte:

1. `.venv/Scripts/python.exe scripts/vad_analysis_numbers.py --year YYYY` — visas
   tabulas ar lapā aprakstīto metodi (ienākumi: ikgadējās, EUR, unikāli
   `(politiķis, avots, veids, summa)`; uzņēmumi/NĪ: profila `compute_section_deltas`,
   kārtoti pēc PAŠREIZĒJIEM, «aizgāja» atsevišķi). Gads = jaunākais, kurā ikgadējo
   deklarāciju skaits ≥ iepriekšējam (2025: 133 pret 122).
2. Katram tabulu politiķim ģimenes-paraksta pārbaude (§ Homonīmu piesārņojums) un
   katram pārsteigumam — raw HTML (Abu Meri Libāna, Zemmers meža pārdošana bija īsti;
   Baltiņš nebija).
3. `content/analizes/vad-2026.md` — tabulas + galvene + `Atjaunots` + § 9 stāsts.
   Tabulu vārdi nāk kā profila saites `[Vārds](../politiki/<slug>.html)` (kopš 2026-09-20; ģenerators
   to dara pats, § 2 rokas sarakstā saites uzturamas ar roku); audits `_strip_md` saites noloba.
4. **Vārti:** `.venv/Scripts/python.exe -m src.render --only=politiki` (profili no tās pašas
   DB) → `scripts/audit_vad_profile_match.py --skip-render` = `[OK]` (60 skaitļi; gadus
   nolasa no lapas). Vārti ir redzēti sarkani: uz vecās lapas 12 nesakritības.
5. Renders `--only=analizes,dashboard` — hub `analizes.html` dzīvo `dashboard` domēnā un
   nes lapas aprakstu; `test_render_chars` REGEN; deploy.

## Pārbaudes vaicājumi

```bash
# Cik politiķiem ir vismaz 1 deklarācija?
.venv/Scripts/python.exe -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
print(con.execute('SELECT COUNT(DISTINCT opponent_id) FROM vad_declarations').fetchone())
"

# Politiķi BEZ deklarāciju (var būt nepareizs role-match)
.venv/Scripts/python.exe -c "
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

sec 9/10 formāti (2026-09-19 parsera labojums — iepriekš visas rindas klusi
krita, `vad_debts` bija tukša): publiskā daļa nerāda kreditora vārda —
tabulai ir 3 kolonnas (summa | valūta | summa ar vārdiem); vecajam formātam
(2002–2010) viena brīvteksta šūna, kas var saturēt vairākas valūtas
(«5 928 853 USD, 450 000 EUR, 7 813 LVL») — dalās pa valūtu rindām,
oriģināls paliek `amount_in_words`. `creditor_name` tukšs ir normāls stāvoklis,
ne trūkstošs datums.
- `vad_family` — sec 14 ģimene

## Spec atsauce

`docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` (master commit `dda5478` ar F11+F12 amendments)
