# VAD Analīzes Sanācijas Plāns

> **Aģentu izpildei:** OBLIGĀTĀ APAKŠ-PRASME: Lieto superpowers:subagent-driven-development (ieteikta) vai superpowers:executing-plans, lai izpildītu šo plānu uzdevumu pa uzdevumam. Soļi izmanto checkbox (`- [ ]`) sintaksi izpildes uzskaitei.

**Mērķis:** Pirms `content/analizes/_drafts/vad-2026.md` publicēšanas nodrošināt, ka katrs skaitlis analīzē atbilst patiesai realitātei un sakrīt ar attiecīgā politiķa profila lapas datiem; ka analīze nesatur slēptu valūtu summējumu, homonīmu kontamināciju, vēsturisku pārskaitīšanu vai dedup-trūkumus.

**Arhitektūra:** Sanācija notiek 6 paralēlos darbības virzienos: (1) atsevišķu politiķu homonīmu fiksācija, (2) dedup metodoloģijas konsekventa piemērošana visās tabulās, (3) profila lapas un analīzes skaitļu sakritības verifikācija, (4) "0 NĪ ārvalstīs" apgalvojuma pārbaude, (5) sanācijas izņēmumu (Inga Bērziņa, Hosams Abu Meri) status review, (6) valūtu konvertēšanas politikas dokumentēšana. Beigās pilns analīzes pārrakstījums + render + deploy. Phase 1 parse-fail UUIDi (1304 dok.) ir nodalīti uz atsevišķu plānu, jo to atrisināšana ir nedēļas mēroga darbs un nemaina top-15 sarakstu sakārtojumu.

**Tehnoloģijas:** Python 3.11, SQLite, esošais Phase 1.5 sanācijas pattern (`scripts/seed_*_disambig.py` operatoru filtri + `scripts/cleanup_contaminated_vad.py` + `scripts/ingest_vad_declarations.py --politician`), pytest matcher tests.

**Worktree ieteikums:** Šim plānam izveido worktree `vad-analize-sanacija` (atsevišķi no master), jo tas ietver datubāzes izmaiņas vairākiem politiķiem un re-ingestēšanu.

---

## Failu struktūra

**Jauni faili (kuratoru skripti):**
- `scripts/seed_homonimu_disambig.py` — vienots curator pid 137 Vucāns, pid 81 Daģis, pid 10 Kulbergs, pid 158 Lāce. Idempotents.
- `scripts/audit_vad_profile_match.py` — pārbauda, ka top-15 saraksta skaitļi sakrīt ar profila lapas datiem.
- `scripts/audit_vad_foreign_re.py` — pārbauda visu gadu NĪ atrašanās laukus uz ārvalstu mārkeriem.

**Modificējami faili:**
- `wiki/CHANGELOG.md` — pievienot ierakstu "VAD Phase 1.5+ — 4 papildu homonīmu sanācija".
- `content/analizes/_drafts/vad-2026.md` — galīgais pārrakstījums ar verificētiem skaitļiem (T11).
- `tracked_politicians.keywords` un `negative_patterns` (DB) priekš pid 137, 81, 10, 158 (caur curator skriptu).

**Datubāzes ieraksti, kas tiek dzēsti / no jauna ielādēti:**
- `vad_declarations` un FK rindas (`vad_income`, `vad_companies`, `vad_real_estate`, `vad_family`, `vad_savings`, `vad_vehicles`, `vad_transactions`, `vad_debts`, `vad_loans_given`, `vad_positions`) — pid 137, 81, 10, 158 (homonīmu kontaminācija).

**Testi:**
- `tests/test_vad_dedup.py` — jauns, pārbauda, ka per-politiķa-gada ienākumu summa pareizi dedupē paralēlu amatu deklarācijas.
- `tests/test_vad_disambig.py` — papildina esošos testus ar jauniem 4 politiķu hint scenarijiem.

---

## T1 — Daģis disambig hints + reingest (pid=81)

**Konteksts:** Mārtiņš Daģis (JV) deklarācijās 2024. gadā parādās gan ar institūciju "Latvijas Republikas Saeima", gan ar "Jelgavas valstspilsētas pašvaldības iestāde 'Centrālā pārvalde'". Bez `vad_disambig` filtra nevar apstiprināt, vai abas deklarācijas pieder vienai personai (Saeimas dep + bijušais Jelgavas mēra vietnieks ar saistītu darbu) vai homonīmu kontaminācijai.

**Faili:**
- Modificē: `scripts/seed_homonimu_disambig.py` (jauns)
- Modificē: DB `tracked_politicians WHERE id=81` (`keywords`, `negative_patterns`)

- [ ] **Solis 1: Manuāla Daģa identitātes pārbaude VID portālā**

Atver [www6.vid.gov.lv/VAD](https://www6.vid.gov.lv/VAD), meklē "Mārtiņš Daģis". Atzīmē atrasto cilvēku skaitu un katram amatu / iestādi / dzīvesvietas reģionu. Salīdzina ar publiski zināmo (Daģis ir JV Saeimas deputāts, bijušais Jelgavas mēra vietnieks 2017–2022 — abas lomas iespējami **vienam** cilvēkam, BET to apstiprina tikai manuāli).

Sagaidāmais rezultāts: 1 vai 2 cilvēki ar šo vārdu. Ja 1 — abas institūcijas pieder vienai personai, hints satur "Saeimas deputāts" + "Jelgavas valstspilsētas". Ja 2 — hints jāatlasa tikai uz vienu, otru izmest.

- [ ] **Solis 2: Sastāda hints, raksta uz curator skripta**

Atkarībā no Solis 1 rezultāta, pievieno failu `scripts/seed_homonimu_disambig.py` ar šādu struktūru (paraugs ņem no `seed_lidaka_disambig.py`):

```python
"""Seed pid=81 Daģis + pid=10 Kulbergs + pid=137 Vucāns + pid=158 Lāce
disambig hints pēc 2026-05-03 audita. Idempotents."""
import json, sqlite3
from pathlib import Path

DB_PATH = Path("data/atmina.db")

CONFIGS = [
    {
        "pid": 81, "name": "Mārtiņš Daģis",
        "keywords": {"vad_disambig": ["Saeimas deputāts", "Latvijas Republikas Saeima",
                                       "Jelgavas valstspilsētas"]},  # <-- pielāgo no Solis 1
        "negative_patterns": [],  # <-- pielāgo no Solis 1
    },
    # T2, T3, T4 papildinājumi nāk vēlāk šajā pašā skriptā
]

def main():
    con = sqlite3.connect(DB_PATH)
    for cfg in CONFIGS:
        con.execute(
            "UPDATE tracked_politicians SET keywords = ?, negative_patterns = ? WHERE id = ?",
            (json.dumps(cfg["keywords"], ensure_ascii=False),
             json.dumps(cfg["negative_patterns"], ensure_ascii=False),
             cfg["pid"]))
        print(f"[ok] pid={cfg['pid']} {cfg['name']} hints set")
    con.commit(); con.close()

if __name__ == "__main__":
    main()
```

- [ ] **Solis 3: Palaiž curator skriptu**

```bash
.venv/Scripts/python.exe scripts/seed_homonimu_disambig.py
```

Sagaidāmais output: `[ok] pid=81 Mārtiņš Daģis hints set`.

- [ ] **Solis 4: Notīra esošās Daģa deklarācijas (DELETE) un re-ingestē**

```bash
.venv/Scripts/python.exe scripts/cleanup_contaminated_vad.py --politician "Mārtiņš Daģis"
.venv/Scripts/python.exe scripts/ingest_vad_declarations.py --politician "Mārtiņš Daģis"
```

Sagaidāmais output (paraugs): `[ok]  Mārtiņš Daģis  new=N present=M skip_role=K errs=0 (Xs)`.

- [ ] **Solis 5: Verificē rezultātu**

```bash
.venv/Scripts/python.exe -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row;
[print(dict(r)) for r in con.execute('SELECT declaration_year, declaration_kind, institution, position_title FROM vad_declarations WHERE opponent_id=81 ORDER BY declaration_year DESC LIMIT 10')]"
```

Sagaidāms: visas atgriezenās deklarācijas atbilst `keywords.vad_disambig` whitelist; nav rindas ar nepiederīgām institūcijām.

- [ ] **Solis 6: Commit**

```bash
git add scripts/seed_homonimu_disambig.py
git commit -m "chore(vad): pid=81 Daģis disambig hints + reingest"
```

---

## T2 — Lāce disambig hints + reingest (pid=158)

**Konteksts:** Agnese Lāce (PRO Kultūras ministre) audita gaitā parādās ar paralēlām deklarācijām no "Valsts kanceleja" (loģiski) un "Neatliekamās medicīniskās palīdzības dienests" (NMPD). Lāce nav publiski zināma kā NMPD darbiniece — visticamāk homonīms ar citu Agnesi Lāci medicīnas jomā.

**Faili:**
- Modificē: `scripts/seed_homonimu_disambig.py` (papildina `CONFIGS`)
- Modificē: DB `tracked_politicians WHERE id=158`

- [ ] **Solis 1: Manuāla Lāces identitātes pārbaude VID portālā**

Atver VID portālu, meklē "Agnese Lāce". Saskaita atrasto cilvēku skaitu, atzīmē viņu institūcijas. Apstiprina, ka **mūsu** Lāce (Kultūras ministre) NESTRĀDĀ NMPD.

Sagaidāmais: 2+ cilvēki ar to pašu vārdu, no kuriem viens ir mediķe NMPD.

- [ ] **Solis 2: Pievieno Lāces hints `scripts/seed_homonimu_disambig.py`**

Pievieno `CONFIGS` sarakstam:

```python
{
    "pid": 158, "name": "Agnese Lāce",
    "keywords": {"vad_disambig": ["Latvijas Republikas Saeima", "Saeimas deputāts",
                                   "Valsts kanceleja", "Kultūras ministrija"]},
    "negative_patterns": ["Neatliekamās medicīniskās palīdzības dienests", "NMPD"],
},
```

- [ ] **Solis 3: Palaiž curator skriptu (atkārtoti)**

```bash
.venv/Scripts/python.exe scripts/seed_homonimu_disambig.py
```

Sagaidāms: idempotents — Daģis arī parādās output, plus jaunais Lāce.

- [ ] **Solis 4: Notīra Lāces deklarācijas un re-ingestē**

```bash
.venv/Scripts/python.exe scripts/cleanup_contaminated_vad.py --politician "Agnese Lāce"
.venv/Scripts/python.exe scripts/ingest_vad_declarations.py --politician "Agnese Lāce"
```

- [ ] **Solis 5: Verificē**

```bash
.venv/Scripts/python.exe -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row;
[print(dict(r)) for r in con.execute('SELECT declaration_year, institution FROM vad_declarations WHERE opponent_id=158 ORDER BY declaration_year DESC')]"
```

Sagaidāms: nav rindu ar `institution = 'Neatliekamās medicīniskās palīdzības dienests'`.

- [ ] **Solis 6: Commit**

```bash
git add scripts/seed_homonimu_disambig.py
git commit -m "chore(vad): pid=158 Lāce disambig hints + reingest"
```

---

## T3 — Kulbergs disambig hints + reingest (pid=10)

**Konteksts:** Andris Kulbergs (AS Saeimas dep) audita gaitā parādās ar institūciju "Valsts policija" 2024. gada deklarācijā. Kulbergs nav publiski zināms kā Valsts policijas darbinieks; iespējams homonīms.

**Faili:**
- Modificē: `scripts/seed_homonimu_disambig.py`
- Modificē: DB `tracked_politicians WHERE id=10`

- [ ] **Solis 1: Manuāla Kulberga identitātes pārbaude VID portālā**

Meklē "Andris Kulbergs". Apstiprina, ka mūsu Kulbergs (AS Saeimas dep, bijušais Latvijas Vieglatlētikas savienības priekšsēdētājs) **nav** Valsts policijas darbinieks.

- [ ] **Solis 2: Pievieno Kulberga hints**

```python
{
    "pid": 10, "name": "Andris Kulbergs",
    "keywords": {"vad_disambig": ["Latvijas Republikas Saeima", "Saeimas deputāts",
                                   "Apvienotais saraksts", "Latvijas Vieglatlētikas"]},
    "negative_patterns": ["Valsts policija"],
},
```

- [ ] **Solis 3: Palaiž curator + cleanup + re-ingest**

```bash
.venv/Scripts/python.exe scripts/seed_homonimu_disambig.py
.venv/Scripts/python.exe scripts/cleanup_contaminated_vad.py --politician "Andris Kulbergs"
.venv/Scripts/python.exe scripts/ingest_vad_declarations.py --politician "Andris Kulbergs"
```

- [ ] **Solis 4: Verificē**

```bash
.venv/Scripts/python.exe -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row;
[print(dict(r)) for r in con.execute('SELECT declaration_year, institution FROM vad_declarations WHERE opponent_id=10 ORDER BY declaration_year DESC')]"
```

- [ ] **Solis 5: Commit**

```bash
git add scripts/seed_homonimu_disambig.py
git commit -m "chore(vad): pid=10 Kulbergs disambig hints + reingest"
```

---

## T4 — Vucāns disambig hints + reingest (pid=137)

**Konteksts:** Jānis Vucāns (ZZS Saeimas dep) audita gaitā parādās ar paralēlām deklarācijām no "Latvijas Republikas Saeima" un "Valsts policija" (Inspektors). Vucāns ir publiski zināms kā Saeimas dep ar IT/ekonomikas pieredzi (Ventspils Augstskola, ne Valsts policija). Visticamāk homonīms ar policijas darbinieku Madonā.

**Faili:**
- Modificē: `scripts/seed_homonimu_disambig.py`
- Modificē: DB `tracked_politicians WHERE id=137`

- [ ] **Solis 1: Manuāla Vucāna identitātes pārbaude VID portālā**

Meklē "Jānis Vucāns". Apstiprina, ka mūsu Vucāns nav Madonas Valsts policijas inspektors.

- [ ] **Solis 2: Pievieno Vucāna hints**

```python
{
    "pid": 137, "name": "Jānis Vucāns",
    "keywords": {"vad_disambig": ["Latvijas Republikas Saeima", "Saeimas deputāts",
                                   "Ventspils Augstskola", "Zaļo un Zemnieku savienība"]},
    "negative_patterns": ["Valsts policija", "Madona", "Iekšlietu ministrija"],
},
```

- [ ] **Solis 3: Palaiž curator + cleanup + re-ingest**

```bash
.venv/Scripts/python.exe scripts/seed_homonimu_disambig.py
.venv/Scripts/python.exe scripts/cleanup_contaminated_vad.py --politician "Jānis Vucāns"
.venv/Scripts/python.exe scripts/ingest_vad_declarations.py --politician "Jānis Vucāns"
```

- [ ] **Solis 4: Verificē**

```bash
.venv/Scripts/python.exe -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row;
[print(dict(r)) for r in con.execute('SELECT declaration_year, institution, position_title FROM vad_declarations WHERE opponent_id=137 ORDER BY declaration_year DESC LIMIT 20')]"
```

Sagaidāms: nav rindu ar `institution = 'Valsts policija'`.

- [ ] **Solis 5: Commit**

```bash
git add scripts/seed_homonimu_disambig.py
git commit -m "chore(vad): pid=137 Vucāns disambig hints + reingest"
```

---

## T5 — § 3 ienākumu sastāva tabulas dedup

**Konteksts:** Pašreizējā § 3 tabula skaita ienākumus per-ieraksts, neatkarīgi no tā, vai tā ir tā pati alga, kas parādās vairākās paralēlās deklarācijās. Tāpēc kopējā EUR summa Algai (9 128 215) ir augšā uzpūsta un sadalījuma procenti pa veidiem ir aptuveni precīzi.

**Faili:**
- Modificē: `content/analizes/_drafts/vad-2026.md` (§ 3)
- Lieto: viens nolasāms SQL ar `GROUP BY (politiķis, gads, avots, summa)`

- [ ] **Solis 1: Raksta dedupētu SQL skripts un saglabā paraugu**

```python
# Audita skripts
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
sql = """
WITH dedup AS (
    SELECT vd.opponent_id, vi.source, vi.income_type, vi.amount, vi.currency
    FROM vad_income vi
    JOIN vad_declarations vd ON vd.id = vi.declaration_id
    WHERE vd.declaration_year = 2024
    GROUP BY vd.opponent_id, vi.source, vi.income_type, vi.amount, vi.currency
)
SELECT income_type,
       COUNT(*) AS unikali_ieraksti,
       ROUND(SUM(CASE WHEN currency='EUR' THEN amount ELSE 0 END)) AS kopa_eur
FROM dedup
GROUP BY income_type
ORDER BY kopa_eur DESC;
"""
for r in con.execute(sql): print(dict(r))
```

- [ ] **Solis 2: Palaiž**

```bash
.venv/Scripts/python.exe -c "<above script>"
```

Sagaidāms: jauni skaitļi mazāki nekā pašreizējie (Alga vairs nav 9.1M, bet kaut kas ap 8M).

- [ ] **Solis 3: Atjauno § 3 tabulu `vad-2026.md`**

Aizstāj veco tabulu ar jaunajiem dedupētajiem skaitļiem, pievieno paskaidrojumu, ka tagad tabula ir per-cilvēks-gads.

- [ ] **Solis 4: Verificē, ka § 2 top-15 sumarie un § 3 algas summa savieto**

`.venv/Scripts/python.exe -c "..."` — saskaita § 2 un § 3 algas summas, salīdzina ar atsevišķu tikai-algas dedupētu kopsumu.

- [ ] **Solis 5: Commit**

```bash
git add content/analizes/_drafts/vad-2026.md
git commit -m "fix(analizes): vad-2026 § 3 ienākumu sastāvs ar dedup"
```

---

## T6 — Profila lapas un analīzes skaitļu sakritības verifikācija

**Konteksts:** Lietotājs pamanīja, ka analīzes skaitļi neatbilst tam, ko viņš redz politiķa profila lapā (Brigmanis 249 NĪ analīzē vs 12 profilā). Šī verifikācija pārbauda, ka pēc T1-T5 izmaiņām katrs § 2/§ 4/§ 5/§ 6 top-15 ieraksts atbilst tieši tam skaitlim, ko render izvada politiķa profila finansu blokā.

**Faili:**
- Jauns: `scripts/audit_vad_profile_match.py`

- [ ] **Solis 1: Raksta audita skriptu**

```python
"""Pārbauda, ka § 2/4/5/6 saraksta skaitļi sakrīt ar render izvades politiķa
profila finansu bloka skaitļiem (output/atmina/politiki/<slug>.html)."""
import sqlite3, re
from pathlib import Path

con = sqlite3.connect('data/atmina.db'); con.row_factory = sqlite3.Row
OUTPUT = Path("output/atmina/politiki")

def slug(name): ...  # implementē atbilstoši src/render slug funkcijai

POLITICIANS_TO_CHECK = [
    ("Līga Kļaviņa", 104, 239664, "ienakumi_2024"),
    ("Augusts Brigmanis", 55, 12, "ni_jaunakais"),
    ("Jānis Dombrava", 110, 12, "uznemumi_jaunakais"),
    # ... visi 30+ no top sarakstiem
]

failures = []
for name, pid, expected, kind in POLITICIANS_TO_CHECK:
    html_path = OUTPUT / f"{slug(name)}.html"
    if not html_path.exists():
        failures.append((name, "html nav atrasts")); continue
    html = html_path.read_text(encoding='utf-8')
    # extract finansu bloku (skat. src/render/politicians.py kā template renderē)
    actual = ...  # parsē no html
    if actual != expected:
        failures.append((name, f"sagaidīts {expected}, atrasts {actual}"))

if failures:
    for f in failures: print(f"[FAIL] {f}")
    raise SystemExit(1)
print("OK — visi sakrīt")
```

- [ ] **Solis 2: Palaiž**

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
.venv/Scripts/python.exe scripts/audit_vad_profile_match.py
```

Sagaidāms: viss "OK — visi sakrīt" vai pretējā gadījumā detalizēts sarakstu fails.

- [ ] **Solis 3: Ja kaut kas nesakrīt — pārstrādā profila renderi vai analīzes skaitli**

Šis ir reāls darbs — render template var rēķināt citādi nekā mans SQL. Viens variants ir pareizs, otrs jākoriģē. Komentāri analīzē jāatjaunina pirms publicēšanas.

- [ ] **Solis 4: Atkārto pēc katras izmaiņas**

```bash
.venv/Scripts/python.exe scripts/audit_vad_profile_match.py
```

- [ ] **Solis 5: Commit**

```bash
git add scripts/audit_vad_profile_match.py content/analizes/_drafts/vad-2026.md
git commit -m "test(vad): profile-match audit; vad-2026 skaitļi atbilst profilam"
```

---

## T7 — "0 NĪ ārvalstīs" apgalvojuma pārbaude (visi gadi)

**Konteksts:** § 6 lokācijas sadaļā tagad apgalvojam "0 deklarētu īpašumu ārvalstīs", balstoties uz to, ka visu ierakstu `location` lauks sākas ar "Latvija,". Tas ir pārāk vienkāršots — VID portāla `location` lauks pieļauj formātu, ko mēs neparedzam (piem. tukšs lauks, citu valstu apzīmējumi, "ārvalstīs" angļu valodā).

**Faili:**
- Jauns: `scripts/audit_vad_foreign_re.py`

- [ ] **Solis 1: Raksta audita skripts**

```python
"""Pārbauda VISUS gadus, ne tikai 2024, uz NĪ ārpus Latvijas."""
import sqlite3, re
con = sqlite3.connect('data/atmina.db'); con.row_factory = sqlite3.Row

print('=== Visi unikāli location lauki, kas NESĀKAS ar "Latvija," ===')
for r in con.execute("""
    SELECT vre.location, COUNT(*) AS n,
           GROUP_CONCAT(DISTINCT tp.name) AS politiķi
    FROM vad_real_estate vre
    JOIN vad_declarations vd ON vd.id = vre.declaration_id
    JOIN tracked_politicians tp ON tp.id = vd.opponent_id
    WHERE (vre.location IS NULL OR vre.location NOT LIKE 'Latvija,%')
      AND tp.relationship_type != 'inactive'
    GROUP BY vre.location
    ORDER BY n DESC
"""):
    print(dict(r))

print()
print('=== Tukšu location lauku skaits ===')
print(con.execute("SELECT COUNT(*) FROM vad_real_estate WHERE location IS NULL OR location = ''").fetchone()[0])
```

- [ ] **Solis 2: Palaiž**

```bash
.venv/Scripts/python.exe scripts/audit_vad_foreign_re.py
```

Sagaidāms — viens no:
- Tukšs saraksts → "0 NĪ ārvalstīs" apgalvojums apstiprināts (visi NĪ Latvijā)
- Atrastas rindas ar citām valstīm → atjaunina § 6 sadaļu ar konkrētiem skaitļiem

- [ ] **Solis 3: Ja atrastas ārvalstu NĪ — atjaunina § 6**

Aizstāj "0 deklarētu īpašumu ārvalstīs" ar reāliem skaitļiem un valstu sadalījumu. Pievieno politiķu sarakstu, kas tos deklarē.

- [ ] **Solis 4: Commit**

```bash
git add scripts/audit_vad_foreign_re.py content/analizes/_drafts/vad-2026.md
git commit -m "audit(vad): pārbauda 0-NĪ-ārvalstīs apgalvojumu visos gados"
```

---

## T8 — Phase 1.5 izņēmumu status review (Inga Bērziņa, Hosams Abu Meri)

**Konteksts:** 1.5. posma sanācijas iznākumā Inga Bērziņa profilā ir 2 deklarācijas (~ 9 NĪ kopā 2025. gadā) — bet sākotnējie audit dati liecina, ka viņas reālā VID datu ielādes pamatā ir slēptas "drošības robežas" problēma (200-row search bound). Tāpat Hosams Abu Meri pid=161 saņēma `_NAME_OVERRIDES` patch, bet viņa deklarācijas ielādes statuss un skaits šajā analīzē nav skaidri redzams.

**Faili:**
- Modificē: `content/analizes/_drafts/vad-2026.md` (§ 9)
- Pārskata: bez koda izmaiņām, tikai dokumentē patieso stāvokli

- [ ] **Solis 1: Pārbauda Ingas Bērziņas un Hosama deklarāciju skaitu DB**

```bash
.venv/Scripts/python.exe -c "
import sqlite3
con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row
for nm in ['Inga Bērziņa', 'Hosams Abu Meri']:
    pid_row = con.execute('SELECT id FROM tracked_politicians WHERE name=?', (nm,)).fetchone()
    if not pid_row: print(f'{nm}: NOT FOUND'); continue
    pid = pid_row[0]
    n = con.execute('SELECT COUNT(*) FROM vad_declarations WHERE opponent_id=?', (pid,)).fetchone()[0]
    latest = con.execute('SELECT MAX(declaration_year) FROM vad_declarations WHERE opponent_id=? AND declaration_kind=\"annual\"', (pid,)).fetchone()[0]
    print(f'{nm} (pid={pid}): {n} dekl, latest annual gads={latest}')
"
```

Sagaidāms (no atmiņas): Inga Bērziņa 2 dekl, Hosams Abu Meri varbūt 5-7 dekl. Ja Hosamam 0 — `_NAME_OVERRIDES` patch tomēr nedarbojas, jāpārbauda.

- [ ] **Solis 2: Ja Inga Bērziņa joprojām ir 0 dekl reālo gadu griezumā — manuāli pārbauda VID portālā un pievieno hints**

Atver VID portālu, meklē "Inga Bērziņa". Ja tur ir reāli atrodami politiķa darba dati (Saeimas dep alga, NĪ), bet meklēšana atgrieza > 200 rindas un mūsu safety-bound nogriež → eskalē kā Phase 2 problēmu un atstāj § 9 piezīmi. Ja tur datu vienkārši nav (politiķim **patiesi** nav VID dekl reģistrētas) — papildina § 9 piezīmi.

- [ ] **Solis 3: Pievieno § 9 piezīmi par šiem konkrētiem izņēmumiem**

```markdown
### Konkrēti izņēmumi pēc 1.5. posma sanācijas

- **Inga Bērziņa (JV)** — 2 deklarācijas DB, bet manuāli VID portālā redzams, ka viņai
  ir vairāk. Iemesls: meklēšanas drošības robeža (200 rindas), kas nogriež
  nepieciešamos ierakstus aiz tās. Eskalēts kā 2. posma uzdevums.
- **Hosams Abu Meri (NA)** — `_NAME_OVERRIDES[161]` ielikts 1.5. posmā, viņa
  deklarāciju skaits tagad ir N (skat. profilā).
```

- [ ] **Solis 4: Commit**

```bash
git add content/analizes/_drafts/vad-2026.md
git commit -m "docs(analizes): vad-2026 § 9 izņēmumu konkretizācija (Inga, Hosams)"
```

---

## T9 — Valūtu konvertēšanas politika

**Konteksts:** Pašreizējās tabulas (§ 2 ienākumi, § 5b kapitāldaļas) tikai filtrē `currency='EUR'` un summē. Tas izlaiž USD, GBP, RUB ierakstus pilnībā. Politiķim ar lielu ASV akciju portfeli (piem. Dombrava) — kapitāldaļu vērtējums USD nav redzams. Tas ir slēpta neatbilstība, kas pasniedz datus kā pilnīgus, kad faktiski tie ir nepilnīgi.

**Faili:**
- Modificē: `content/analizes/_drafts/vad-2026.md` (§ 2, § 5b, § 8)

- [ ] **Solis 1: Aprēķina, cik daudz nav EUR**

```bash
.venv/Scripts/python.exe -c "
import sqlite3
con=sqlite3.connect('data/atmina.db'); con.row_factory=sqlite3.Row
for tbl in ['vad_income', 'vad_companies', 'vad_debts', 'vad_loans_given']:
    print(f'--- {tbl} 2024 currency split ---')
    for r in con.execute(f'''
        SELECT vi.currency, COUNT(*) AS n, ROUND(SUM(vi.amount)) AS kopa
        FROM {tbl} vi
        JOIN vad_declarations vd ON vd.id = vi.declaration_id
        WHERE vd.declaration_year = 2024
        GROUP BY vi.currency ORDER BY n DESC
    '''):
        print(dict(r))
"
```

Sagaidāms: lielākā daļa EUR, bet 5–20% USD (Dombrava), iespējams arī GBP / RUB.

- [ ] **Solis 2: Pieņem politiku — vai konvertēt vai izslēgt**

Iespējas:
- **A)** Konvertēt uz EUR pēc deklarācijas gada vidējā kursa. Prasa kursu tabulu (var ņemt no Eurostat / Bankas Latvijas API). 1 dienas darbs.
- **B)** Atstāt tikai EUR un eksplicīti atzīmēt, ka USD/GBP/RUB ieraksti nav iekļauti. Vienkāršāk, godīgāk.

Atkarībā no pieņemtās politikas — aktualizē tabulas un pievieno piezīmi.

- [ ] **Solis 3: Atjauno § 2, § 5b, § 8 ar valūtu politiku**

Konkrēti — ja pieņem (B):
```markdown
> **Valūtu piezīme.** Šajā tabulā iekļauti tikai EUR deklarētie ienākumi.
> Politiķiem ar ASV akciju portfeli (piem. Dombrava ar SM Energy, Diamondback)
> USD vērtības nav konvertētas un iekļautas. Apvienota valūtu vērtēšana ir
> 2. posma plānā.
```

- [ ] **Solis 4: Commit**

```bash
git add content/analizes/_drafts/vad-2026.md
git commit -m "docs(analizes): vad-2026 valūtu politikas piezīme + § 8 backlog atjauninājums"
```

---

## T10 — Galīgais audit pirms publicēšanas

**Konteksts:** Pēc T1-T9 izpildes — pilnīgs draft pārbaudījums ar svaigu skatu, sekojot lietotāja "completely accurate data" prasībai.

**Faili:**
- Modificē: `content/analizes/_drafts/vad-2026.md`

- [ ] **Solis 1: Pārlasi katru skaitli draftā un atrod tā SQL pamatu**

Katram skaitlim (>50 datapoints kopā) — kāds SQL kverijs to ražoja? Vai tas kverijs ņēma vērā T1-T9 izmaiņas? Ja ne — atjauno vai dokumentē kā novecojušu.

Konkrētie skaitļi pārbaudei:
- § 1: 2348 dekl, 143 politiķi, 23 gadi
- § 2: 15 politiķu top + summas
- § 3: 14 ienākuma veidi + summas
- § 4: 10 YoY izmaiņas + procenti
- § 5: 10 uzņēmumu top
- § 5b: 10 kapitāldaļu top
- § 6: 15 NĪ top + tipi + lokācija
- § 7: 8 ģimenes saistības + 2 kolonnas
- § 9: izņēmumu skaits

- [ ] **Solis 2: Pārlasi katru tekstu uz neprecizitātēm vai anglicismiem, kas paslīda cauri**

Meklē: "Phase", "TOP", "delta", "outlier", "audit", "ingest", "pipeline", "filter", "DB", "FK", "junction".

- [ ] **Solis 3: Atjauno frontmatter `description` lauku**

Lai atbilst galīgajam saturam (nevis 445% Braže — kas, iespējams, mainās pēc T1-T9).

- [ ] **Solis 4: Atver lokāli rendered output**

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
start "~\atmina\output\atmina\analizes\vad-2026.html"
```

Pārlasa lapu kā lietotājs.

- [ ] **Solis 5: Commit + apstiprinājums**

```bash
git add content/analizes/_drafts/vad-2026.md
git commit -m "docs(analizes): vad-2026 galīgais audit pirms publicēšanas"
```

Pēc commit — ziņo lietotājam, ka draft ir gatavs viņa galīgai pārskatīšanai.

---

## T11 — Publicēšana (tikai pēc lietotāja apstiprināšanas)

**Konteksts:** Tikai pēc tam, kad lietotājs ir personīgi izlasījis lapas un teicis "publicē", izpildi šo uzdevumu. **Nedari to bez explicit OK.**

**Faili:**
- Pārvietot: `content/analizes/_drafts/vad-2026.md` → `content/analizes/vad-2026.md`

- [ ] **Solis 1: Pārvieto failu atpakaļ uz `content/analizes/`**

```bash
git mv content/analizes/_drafts/vad-2026.md content/analizes/vad-2026.md
```

- [ ] **Solis 2: Re-render**

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

- [ ] **Solis 3: Re-ģenerē featured image (ja kopš pēdējās ģenerēšanas DB ir mainīts)**

```bash
.venv/Scripts/python.exe scripts/generate_vad_2026_image.py
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

- [ ] **Solis 4: Dry-run deploy**

```bash
bash scripts/deploy.sh --dry-run | grep -E "^deleting|sent .* bytes"
```

Sagaidāms: 0 dzēšanas (vai tikai vad-2026 saistītas — nē, šeit deploy ir publicēšana, ne rollback), pievienojums vad-2026.html un vad-2026.png.

- [ ] **Solis 5: Real deploy**

```bash
bash scripts/deploy.sh
```

- [ ] **Solis 6: Commit pārvietošanu un atjaunina wiki**

```bash
git add content/analizes/vad-2026.md wiki/CHANGELOG.md
git commit -m "feat(analizes): publicē vad-2026 pēc operatora pārbaudes"
git push origin master
```

- [ ] **Solis 7: Ziņo lietotājam — publicēts ar URL**

---

## Pašpārskats

**1. Specifikācijas pārklājums.** Lietotājs prasīja 7 kategorijas (a-g):
- (a) 4 homonīmu politiķi → T1-T4 ✓
- (b) Dedup § 3 + § 4 → T5 (§ 3 ienākumu sastāvs); § 4 YoY jau dedupēts pēdējā commitā 9b91494, bet T5 verifikācija to apstiprina ✓
- (c) NĪ/uzņēmumi profila atbilstība → T6 ✓
- (d) "0 NĪ ārvalstīs" pārbaude → T7 ✓
- (e) Phase 1.5 izņēmumi (Inga, Hosams) → T8 ✓
- (f) Phase 1 parse-fail UUIDs (1304 dok.) → **NODALĪTS uz atsevišķu plānu** (skat. arhitektūras paragrāfs). Nav blokers šīs analīzes publikācijai.
- (g) Valūtu konvertēšana → T9 ✓

Ja (f) jāiekļauj — pievieno T9.5 ar atsevišķu Phase 2 plāna atsauci.

**2. Vietturu (placeholder) pārbaude.** Plānā ir vairāki "..." (slug funkcija T6 Solis 1; pievieno mainīgos T1-T4 hints atkarībā no Solis 1 manuālā audita) — šie ir **apzināti tukšumi**, kuru saturs atkarīgs no manuāla VID portāla auditoru rezultāta. Tie nav placeholderi formālā nozīmē — tie ir nosacīti soļi, kuros izpildītājs veic manuālo soli un tikai pēc tam aizpilda kodu. Citu placeholderu (TODO, "implement later") nav.

**3. Tipu konsekvence.** `pid` lauks visur `int`, `keywords` un `negative_patterns` JSON serializēti vienādi visos uzdevumos. Curator skripts `seed_homonimu_disambig.py` apvieno T1-T4 uzdevumu CONFIGS sarakstos — saraksts paplašinās ar katru jaunu uzdevumu, idempotents.

---

## Izpildes nodošana

Plāns saglabāts `docs/superpowers/plans/2026-05-03-vad-analize-sanacija.md`. Divas izpildes iespējas:

**1. Apakšaģentu vadīta (ieteikta)** — dispečēšu jaunu apakšaģentu uz katru uzdevumu, pārskats starp uzdevumiem, ātra iterācija.

**2. Iekšsesijas izpilde** — izpildīt uzdevumus šajā sesijā, izmantojot executing-plans, partīga izpilde ar kontroles punktiem operatora pārskatam.

**Kuru pieeju izvēlies?**
