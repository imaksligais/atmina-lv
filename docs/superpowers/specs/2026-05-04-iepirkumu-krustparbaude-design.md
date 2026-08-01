# Iepirkumu krustpārbaude (Phase 3a) — dizaina specifikācija

**Datums**: 2026-05-04
**Izcelsmes konteksts**: Lietotāja pieprasījums (Telegram 2026-05-04 19:35-19:41) — pēc VAD analīzes publikācijas 2026-05-03 noteikt nākamo fāzi. Piedāvāts un apstiprināts: politiķa paša un pirmās pakāpes ģimenes locekļu uzņēmumu krustpārbaude ar publiskā iepirkuma līgumiem (IUB OpenData).
**Saistītie specs**: `2026-05-02-vad-deklaracijas-design.md` (datu avots `vad_companies` un `vad_family`), `2026-04-22-saeima-bills-design.md` (atsauces patern strukturētiem datiem ārpus `documents`/`claims`)
**CHANGELOG atsauce pēc ieviešanas**: `wiki/CHANGELOG.md § Iepirkumu krustpārbaude (Phase 3a)`
**Statuss**: design draft — gaida lietotāja review

---

## 1. Mērķis

Atklāt lasītājam tos politiķus, kuru tieši turētie uzņēmumi vai pirmās pakāpes ģimenes locekļu uzņēmumi figurē kā piegādātāji publiskā iepirkuma līgumos (Iepirkumu uzraudzības biroja [IUB] atvērto datu kopa). Output ir konteksta sniegums, ne automātiska apsūdzība — politiķa SIA, kas saņem valsts līgumus, var būt pilnīgi tīrs gadījums (piem. universāli pieejams pakalpojums, kuru viņa SIA piegādā kopā ar 50 citiem konkurentiem). Mērķis ir **uzlikt skaitļus blakus**, lai lasītājs un žurnālists varētu ātri pārredzēt, vai pelnītā prīvilēģija eksistē.

UI līmenī — divas saskarnes:

1. **Jauna analīzes lapa** `atmina.lv/analizes/iepirkumi-2026.html` ar top-N politiķiem pēc viņu un ģimenes uzņēmumu kopējās iepirkuma līgumu vērtības, ar drill-down uz katru līgumu un saiti uz IUB oriģinālu.
2. **Per-politiķis sekcija** profila lapas Deklarāciju tab apakšā ("Iepirkumi") — saraksts ar viņa un ģimenes uzņēmumiem, kas saņēmuši valsts līgumus.

Kvalitātes mērķis: lasītājs uz politiķa profila redz vienu kopskatu — viņa deklarētie uzņēmumi + nekustamais īpašums + ienākumi (Phase 0+1) PAPILDU TAM kuri no šiem uzņēmumiem reāli saņem publisko naudu (Phase 3a).

**Tas ir komplementārs Phase 3 (sektoru-likumu sasaiste) signāls**, ne tā aizstājējs. Phase 3 atklās "Politiķis ar IT nozares SIA balso par IT iepirkuma likumu"; šī Phase 3a atklāj "Politiķa SIA reāli saņēmusi N EUR no Veselības ministrijas". Abas kustas, signāla raksturs atšķiras (skat. § 12 Atvērtie jautājumi Q1).

---

## 2. Scope

### Iekļauts (šis spec, Phase 3a MVP)

**M1 — Politiķa pašu uzņēmumi ↔ iepirkumi (eksakts match, augsta precizitāte)**

- Jauna `src/iepirkumi/` pakete: `schema.py` (DDL), `iub_client.py` (OpenData CSV ielādētājs), `links.py` (pamatojošais SQL crosswalk pār `vad_companies`), `__init__.py` (public API).
- 2 jaunas tabulas: `iub_contracts` (IUB OpenData mirror), `iub_politician_links` (politiķis × link_type × supplier_reg_number ar evidence + confidence).
- `scripts/ingest_iub_contracts.py` CLI ar `--years YYYY-YYYY`, `--limit N`, `--dry-run`, `--max-age-days D`.
- `scripts/compute_iub_links.py` CLI — re-computes `iub_politician_links` no esošā `vad_companies` + `iub_contracts` joinotā pāra. Pure SQL, no ārējā fetch.
- Linktype `'self_company'` — atsauce `vad_companies.id` ar exact `reg_number` match pret `iub_contracts.supplier_reg_number`.

**M2 — Ģimenes locekļi ↔ iepirkumi (zemāka precizitāte ar disambig pipeline)**

- Paplašinājums `src/iepirkumi/links.py` — `compute_family_links()`. Iemums: `vad_family.full_name` ir tikai vārds + uzvārds (UPPERCASE). Match strategy:
  - **Tier 1 (`'family_high_confidence'`)**: Lursoft / UR atvērto datu CSV `ur_amatpersonas` lookup pa pilna vārda match → ja vienīgais hit, marķē `confidence='high'`. Šis tier prasa UR ielādi (skat. § 13 Q3).
  - **Tier 2 (`'family_medium'`)**: Pilna vārda match `iub_contracts.supplier_name` ar SIA nosaukumu (gadījumā, kad ģimenes loceklis ir SIA "Vārds Uzvārds Konsultācijas" formātā — 23% no `vad_family` rindām saskaņā ar manuāli pārbaudi).
  - **Tier 3 (`'family_low'`)**: skip — pārāk daudzi false-positive (~5% kohorta filtra noise rate, manuāli pārbaudīts ar 20 sample).
- Disambiguation rules: `negative_patterns` per politiķis (sekot tracked_politicians paterns 2026-05-03 sanācijas darbā), kohorta filtrs (politiķa novads + vecuma logs ±15 g, ja UR atgriež dzimšanas gadu).

**M3 — Render + publikācija**

- Jauns `src/render/iepirkumi.py` — pre-loads visam politiķiem (one-batch-per-tabula F4 patern, sekot `src/render/vad.py`).
- Jauns `templates/_iepirkumi_panel.html.j2` fragments — sekcija ar 2 daļām (savi uzņēmumi + ģimenes uzņēmumi), confidence badges (M2 tier 2/3 marķēti).
- `templates/politician.html.j2` paplašinājums — Deklarāciju tab apakšā jauna sekcija (NE jauns tab, lai izvairītos no tab-skaita pieauguma; sekcija paslēpta ja nav datu).
- `content/analizes/iepirkumi-2026.md` — analīzes lapa ar top-N tabulām, metodikas piezīmēm un atvērtiem jautājumiem (pareizais žurnālistiskais konteksts: NĒ apsūdzība, JĀ skaitļi).
- Featured image (graphics-designer aģents pēc tam, kad analīze ir gatava).
- Daily brief un atminalv kanāla post — pēc operatora apstiprinājuma, ne automātisks.

### Ārpus Phase 3a (atsevišķi specs)

- **Phase 3b — Sektoru-likumu sasaiste** (oriģinālā Phase 3 no VAD spec § 2). Paliek atsevišķā specā; prasa NACE→topic_map crosswalk + balsojumu joinu. Vērtība: papildina Phase 3a ar nozaru-līmeņa signālu. Atstājam, jo procurement ir spēcīgāks pirmais slice (skat. § 12 Q1).
- **Sub-contracting tīkls**: ja politiķa SIA ir apakšuzņēmējs primāram piegādātājam — IUB OpenData reti satur sub-contractor datus, atstāt manuāliem case studies.
- **Politiķa balsojumu konteksts iepirkumam**: katra līguma līgumslēdzēja iestāde (piem. Veselības ministrija) → politiķa balsojumi par šīs ministrijas budžetu. Iespējams Phase 3b, bet UI rāda saites bez claims uz pretrunu — viss uz lasītāja interpretācijas.
- **Vecuma kohorta validation pa UR datiem**: prasa UR atvērto datu pilna ielāde + dzimšanas gada konfidencialitātes nianses; atstājam Phase 3a M2 ietvaros tikai ja ir ātrs ceļš.
- **Donoru krustpārbaude** (Phase 5+ jau VAD spec § 2): līdzīga loģika, bet pretī donoru sarakstam (KNAB datu kopa); sapludināt ar šo specifikāciju nav vērts — donori parasti nav SIA ar reg_number.

---

## 3. Avota analīze (IUB OpenData kontrakts)

### 3.1 Endpoint

**Statuss**: VERIFICĒTS 2026-05-04 (M0).

- **Portāls**: `https://www.iub.gov.lv/lv/atvertie-dati` (lapas indekss).
- **Datu portāls**: `https://open.iub.gov.lv/data/notice/<YYYY>/<MM>/<DD-MM-YYYY>.json` — dienas faili, organizēti pa gadiem un mēnešiem.
- **Formāts**: **JSON**, ne CSV (atbilst EU eForms 2024 standartam ar BT-koda lauku reference). XML arhīvs pieejams pirms 2026-01-01 transition perioda.
- **Vēstures dziļums**: **no 2023-10-25** (Līgumi datu kopa). Pirms tam — Publikācijas datu kopa no 2013, bet šī ir paziņojumi pirms-līguma stadijā (cn-standard etc.), nevis konkluzīvi piegādātāju ieraksti. **Phase 3a M1 darbs ar 2023-10 → tagadne kā ~2.5 gadu logu** (sākotnējās spec versijas 10 gadu pieņēmums NEDERĒJAS).
- **Atjaunināšana**: dienas, ~04:00 EET.
- **Apjēga**: 30-04-2025.json fails ir 1.6 MB ar 240 paziņojumiem. Ekstrapolējot: 1.6 MB × 365 d ≈ 580 MB/gads; 2.5 gadi ≈ 1.4 GB ielādēta JSON apjoma. Streaming ielāde ar per-day fetch + cache.
- **Licence**: atvērti dati, derīga atvasinātai publikācijai ar atsauci.

### 3.1.1 JSON schema (verificēta)

Top-level: `list[Notice]`. Katrs notice satur:

| Lauks | Tips | Apraksts |
|-------|------|----------|
| `identifier` | str | UUID — paziņojuma ID |
| `formType` | str | `competition` \| `result` \| `execution` \| `cont-modif` \| `planning` |
| `noticeType` | str | `pil-award`, `pil-concluded-contract`, `pil-award-social`, `sps-award` (formType='result' filtrs); `contract-execution` (formType='execution'); `contract-modification` (cont-modif) |
| `name` | str | Iepirkuma nosaukums |
| `cpvType` | str | CPV kods (8-cipari, piem. `90700000-4`) |
| `organizationData.name` | str | Pasūtītājs (piem. "Cēsu novada pašvaldība") |
| `organizationData.companyId` | str\|null | Pasūtītāja regnr |
| `lots[]` | list | Iepirkuma daļas (multi-lot iepirkumiem) |

Iegultā struktūra konkluzīva līguma datiem:

```
notice
└── lots[]
    └── contracts[]
        ├── id (int)                  — IUB iekšējais līguma ID
        ├── identifier (str)          — pasūtītāja līguma identifikators (piem. "2025-01.4-07/16")
        ├── title (str)               — līguma nosaukums
        ├── conclusionDate (str)      — DD/MM/YYYY formāts (NB: ne ISO)
        ├── status (str)              — "completed", etc.
        └── winners[]
            ├── tenderValue (number)  — līguma summa EUR (parasti)
            ├── winnerType (str)      — "person" | "organization"
            └── winnerBusinessParties[]
                ├── companyId (str)   — PIEGĀDĀTĀJA REGNR (KEY MATCH FIELD)
                ├── name (str)        — piegādātāja nosaukums
                ├── countryCode (str) — "LVA", "EST", etc.
                ├── isNaturalPerson (bool)
                └── winnerSize (str)  — "small", "medium", etc.
```

### 3.1.2 Notice type sadalījums (sample 30-04-2025.json, 240 ieraksti)

| formType / noticeType | Skaits | Mums vajag? |
|-----------------------|--------|-------------|
| `competition / pil-contract` | 48 | Nē — pirms-līguma stadija |
| `result / pil-award` | 42 | Jā — līguma piešķiršana |
| `execution / contract-execution` | 39 | Daļēji — līguma izpildes paziņojums (var saturēt summu pārmaiņas) |
| `competition / pil-planned-contract` | 35 | Nē |
| `planning / pil-discussion` | 23 | Nē |
| `result / pil-concluded-contract` | 15 | Jā — pamata mērķa tips |
| `planning / pil-prior-information` | 13 | Nē |
| `result / pil-award-social` | 5 | Jā |
| `cont-modif / contract-modification` | 5 | Jā — līguma grozījumi (summas izmaiņas) |
| `result / sps-award` | 5 | Jā |
| Pārējie | <5 | Atsevišķi |

**M1 filtrs**: `formType IN ('result', 'execution', 'cont-modif')`. Aptuveni 100/240 = ~42% paziņojumu satur supplier+value datus per dienu.

### 3.1.3 Apjoma korekcija

- **Notices/dienā**: ~240, no kuriem ~100 satur konkluzīvus piegādātāju ierakstus.
- **Vidēji 1-3 contracts × 1-2 winners per result-notice** → ~150-300 piegādātāju rindu dienā = ~55k-110k rindu gadā.
- **Pilns 2.5 gadu ingest**: ~140k-275k `iub_contracts` rindas. Storage: ~150-300 MB DB pieaugums (raw_payload JSON glabāšana). Pieņemams.

### 3.2 Throttling un anti-bot

OpenData portāls — statiski CSV faili, nav anti-bot. Lejupielāde notiek vienreiz katru palaišanu, ne per-rinda API zvanus. Throttle nav nepieciešams. User-Agent: `atmina.lv/1.0 (kontakts@atmina.lv)`.

### 3.3 Datu kvalitāte un freshness

- Iepirkumu publikācijas termiņš: līgumslēdzēja paziņojums par līgumu slēgšanu — 30 dienu laikā pēc līguma noslēgšanas (PIL § 36).
- Sub-contractor info reti pieejams; primāra fokusa: piegādātāja `reg_number`.
- Vēsturisks dziļums: IUB sistēma pieejama kopš ~2010; mūsu iemums — pēdējie 10 gadi (2016-2025), kas pārklāj visu mūsu tracked politiķu Saeimas mandātu vēsturi.
- Anomāliju iespēja: anulēti līgumi, līguma summa ≠ izmaksātā summa. Glabāt **noslēgtā līguma deklarēto summu**, atzīmēt kā saglabāto vērtību (nav reālā izpilde) lapas piezīmē.

---

## 4. Datu modelis

2 jaunas tabulas. `IF NOT EXISTS`, idempotenta `init_iepirkumi_tables()` funkcija `src/iepirkumi/schema.py`.

### 4.1 IUB līgumu mirror

```sql
CREATE TABLE IF NOT EXISTS iub_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_identifier TEXT NOT NULL,            -- paziņojuma UUID (notice.identifier)
    notice_type TEXT NOT NULL,                  -- "pil-award" | "pil-concluded-contract" | "pil-award-social" | "sps-award" | "contract-execution" | "contract-modification"
    form_type TEXT NOT NULL,                    -- "result" | "execution" | "cont-modif"
    contract_iub_id INTEGER,                    -- IUB iekšējais līguma ID (notice.lots[].contracts[].id)
    contract_authority_identifier TEXT,         -- pasūtītāja līguma ID (piem. "2025-01.4-07/16")
    lot_id INTEGER,                             -- notice.lots[].id (lota identifikators paziņojumā)
    contracting_authority TEXT NOT NULL,        -- organizationData.name (piem. "Veselības ministrija")
    authority_reg_number TEXT,                  -- organizationData.companyId (var būt NULL — daži paziņojumi nesatur)
    contract_subject TEXT NOT NULL,             -- notice.name vai notice.lots[].name
    cpv_code TEXT,                              -- CPV klasifikators (notice.cpvType, 8-digit)
    supplier_name TEXT NOT NULL,                -- winnerBusinessParties.name
    supplier_reg_number TEXT,                   -- winnerBusinessParties.companyId (KEY MATCH)
    supplier_country_code TEXT,                 -- "LVA", "EST", etc.
    supplier_size TEXT,                         -- "small", "medium", "large"
    contract_value REAL,                        -- winners.tenderValue (summa par šo winner+lot)
    currency TEXT NOT NULL DEFAULT 'EUR',
    contract_signed_at TEXT,                    -- ISO normalizēts no DD/MM/YYYY (conclusionDate)
    contract_status TEXT,                       -- "completed", etc.
    notice_published_at TEXT,                   -- dc:issued vai notice fetched-from filename DD-MM-YYYY
    raw_payload TEXT,                           -- pilna notice JSON (debug + re-parse)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(notice_identifier, lot_id, contract_iub_id, supplier_reg_number)
);
CREATE INDEX IF NOT EXISTS idx_iub_contracts_supplier_reg ON iub_contracts(supplier_reg_number);
CREATE INDEX IF NOT EXISTS idx_iub_contracts_signed ON iub_contracts(contract_signed_at);
CREATE INDEX IF NOT EXISTS idx_iub_contracts_authority ON iub_contracts(authority_reg_number);
CREATE INDEX IF NOT EXISTS idx_iub_contracts_notice ON iub_contracts(notice_identifier);
```

**Idempotency**: dabīgā atslēga `(notice_identifier, lot_id, contract_iub_id, supplier_reg_number)` — viens paziņojums var saturēt vairākus lotus, katrs lots vairākus contracts, katrs contracts vairākus winners. Re-run ar `INSERT OR IGNORE` ir drošs.

**Lēmums par contract-modification**: paziņojumi ar `formType='cont-modif'` raksta JAUNU rindu (ne UPDATE) — saglabā vēsturisku audit trail. Latest valuation tiek ņemta no jaunākās rindas pa `(notice_identifier, lot_id, contract_iub_id)` ar `notice_published_at` DESC.

**Storage**: ~150-300 MB DB pieaugums (skat. § 3.1.3 apjoma korekciju). Pieņemams.

### 4.2 Politiķis × piegādātājs sasaistes

```sql
CREATE TABLE IF NOT EXISTS iub_politician_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    supplier_reg_number TEXT NOT NULL,
    link_type TEXT NOT NULL,                    -- 'self_company' | 'family_high' | 'family_medium' | 'family_low'
    confidence TEXT NOT NULL,                   -- 'high' | 'medium' | 'low'
    evidence_source TEXT NOT NULL,              -- 'vad_companies' | 'vad_family+ur' | 'vad_family+name_match' | 'manual'
    evidence_decl_id INTEGER,                   -- FK uz vad_declarations.id (kuru deklarāciju izmantojām pierādījumam); NULL ja 'manual'
    evidence_family_id INTEGER,                 -- FK uz vad_family.id (kura ģimenes locekļa ieraksts); NULL ja self
    evidence_company_id INTEGER,                -- FK uz vad_companies.id; NULL ja netiešs match
    notes TEXT,                                 -- audit string: "Lursoft hit unique" / "name + cohort filter ok" / "manual override"
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(opponent_id, supplier_reg_number, link_type)
);
CREATE INDEX IF NOT EXISTS idx_iub_links_opponent ON iub_politician_links(opponent_id);
CREATE INDEX IF NOT EXISTS idx_iub_links_supplier ON iub_politician_links(supplier_reg_number);
```

**Idempotency**: dabīgā atslēga `(opponent_id, supplier_reg_number, link_type)`. Re-run `compute_iub_links.py` `INSERT OR REPLACE` — ja pierādījuma deklarācija ir mainījusies (jauna gada deklarācija), saites tiek atjaunotas, ne dublētas.

**Confidence tiers**:
- `high`: `link_type='self_company'` VAI `link_type='family_high'` (UR unique hit)
- `medium`: `link_type='family_medium'` (SIA "Vārds Uzvārds X" tipa exact name match)
- `low`: `link_type='family_low'` — neielādējam, atstājam Phase 3a backlogā

**Skip logika**: rindas, kur `iub_politician_links.confidence='low'`, nerāda UI bez manuāla `notes='reviewed_ok'` audit.

### 4.3 Kāpēc nav `documents` rindas

Tas pats arguments kā VAD spec § 4.3:
- IUB līgums nav cilvēka-lasāms raksts ar nozīmīgu tekstu — tā ir tabulas rinda.
- Junction (`document_politicians`) deģenerējas trivialitātē — viens līgums pieder vienam piegādātājam.
- Embedding pār līguma priekšmeta tekstu nav lietderīgs — semantiskā search atgrieztu troksni.
- `iub_politician_links` ir tās pašas semantikas tabula kā `saeima_individual_votes` — strukturēta atribūta-tabula, sasaistīta ar tracked_politicians, bez documents/claims pamatojuma.

### 4.4 Kāpēc nav `claims` rindas

Tas pats arguments kā VAD spec § 4.4:
- Iepirkuma fakts nav retoriska pozīcija — tā ir disclosure / akts. Politiķis nav teicis "es saņemu valsts naudu" — tā ir publiska faktiskā situācija.
- `topic` mapping nav saturīgs (līguma priekšmets ir CPV kods, ne topic_map.py). Mēģinājums to iespiest claims tabulā piesārņos esošu topic mapping.
- Phase 3b (sektoru-likumu sasaiste) varētu radīt **derivative** contradictions ("politiķis ar SIA X balsojis pret X regulēšanu" pretrunu tipam), bet tās ir Phase 3b lēmums, ne 3a.

### 4.5 Migration impact

- `init_iepirkumi_tables()` lazy aktivācija (saeima/vad paterns). Trīs aktivācijas vietas:
  1. `scripts/ingest_iub_contracts.py` palaidē kā pirmais step.
  2. `scripts/compute_iub_links.py` palaidē kā pirmais step.
  3. `src/render/iepirkumi.py` modulis — pirmais SELECT pār `iub_contracts` ietīts `try/except sqlite3.OperationalError` → atgriež tukšu dict (vad/saeima paterns).
- Citi tests (`scripts/check.sh`) — neaiztiek, jo render layer guard nodrošina backward compatibility.
- Storage: ~20 MB DB pieaugums (skat. § 4.1).

---

## 5. Politiķu sasaiste — match algoritma detaļa

### 5.1 M1: self_company match

```sql
INSERT OR REPLACE INTO iub_politician_links
    (opponent_id, supplier_reg_number, link_type, confidence,
     evidence_source, evidence_decl_id, evidence_company_id, notes)
SELECT
    d.opponent_id,
    c.reg_number AS supplier_reg_number,
    'self_company',
    'high',
    'vad_companies',
    d.id AS evidence_decl_id,
    c.id AS evidence_company_id,
    'reg_number=' || c.reg_number || ', units=' || COALESCE(c.units, 'NULL')
FROM vad_companies c
JOIN vad_declarations d ON d.id = c.declaration_id
WHERE c.reg_number IS NOT NULL
  AND c.reg_number IN (SELECT supplier_reg_number FROM iub_contracts WHERE supplier_reg_number IS NOT NULL)
  AND d.id = (
      -- Take only the latest annual declaration per politician (skat. VAD analīze § 5 paterns)
      SELECT id FROM vad_declarations d2
      WHERE d2.opponent_id = d.opponent_id AND d2.declaration_kind = 'annual'
      ORDER BY d2.declaration_year DESC LIMIT 1
  );
```

**Edge cases**:
- Politiķis pārdevis SIA pirms gada — `vad_companies` rindas vairs nebūs jaunākajā deklarācijā, link netiks ģenerēts. PARETZAI rīcībai (sk. § 12 Q4 — vai rādīt vēsturiskās piederības?).
- Politiķim foreign-listed akciju pakete (Diamondback, NVIDIA) — `reg_number` ir TICKER vai foreign tax ID, kas neuzrādīsies IUB. Link skaits = 0, kā paredzēts.

### 5.2 M2 Tier 1: family_high (UR lookup)

```python
def compute_family_high_links(db: sqlite3.Connection) -> int:
    """For each vad_family row, lookup full_name in ur_amatpersonas;
    if exactly 1 hit and that company has IUB contracts, create link."""
    cur = db.execute("""
        SELECT f.id, f.full_name, f.relation, f.declaration_id, d.opponent_id
        FROM vad_family f
        JOIN vad_declarations d ON d.id = f.declaration_id
        WHERE d.id = (
            SELECT id FROM vad_declarations d2
            WHERE d2.opponent_id = d.opponent_id AND d2.declaration_kind = 'annual'
            ORDER BY d2.declaration_year DESC LIMIT 1
        )
    """)
    inserted = 0
    for row in cur:
        ur_hits = ur_lookup(row["full_name"])
        if len(ur_hits) != 1:
            continue
        supplier_reg = ur_hits[0]["reg_number"]
        # Check if supplier has any IUB contracts
        if not db.execute(
            "SELECT 1 FROM iub_contracts WHERE supplier_reg_number = ? LIMIT 1",
            (supplier_reg,),
        ).fetchone():
            continue
        db.execute(
            "INSERT OR REPLACE INTO iub_politician_links (...) VALUES (...)",
            (row["opponent_id"], supplier_reg, "family_high", "high",
             "vad_family+ur", None, row["id"], None,
             f"Lursoft unique hit for {row['full_name']}, position={ur_hits[0].get('position', 'unknown')}"),
        )
        inserted += 1
    return inserted
```

**UR lookup — VERIFICĒTS 2026-05-04 (M0)**:

UR atvērto datu CSV pieejams un derīgs:
- **Slug**: `officers` (https://data.gov.lv/dati/lv/dataset/officers)
- **Download URL**: https://data.gov.lv/dati/dataset/096c7a47-33cd-4dc9-a876-2c86e86230fd/resource/e665114a-73c2-4375-9470-55874b4cfa6b/download/officers.csv
- **Izmērs**: ~38 MB (verificēts)
- **Atjaunināšana**: dienas
- **Licence**: CC0-1.0 (publiskie domēni)

**Schema (verificēta)**:

```
id;uri;at_legal_entity_registration_number;entity_type;position;
governing_body;name;latvian_identity_number_masked;birth_date;
legal_entity_registration_number;rights_of_representation_type;
representation_with_at_least;registered_on;last_modified_at
```

Galvenās kolonnas:
- `at_legal_entity_registration_number` — uzņēmuma regnr (KEY)
- `entity_type` — `NATURAL_PERSON` vai `LEGAL_ENTITY` (filtrs: tikai NATURAL_PERSON)
- `governing_body` — `EXECUTIVE_BOARD`, `COUNCIL`, etc.
- `name` — **vārda formāts: "Surname Firstname"** (piem. "Liberte Inese") — NB: vad_family ir "FIRSTNAME SURNAME" formātā ("INESE ŠLESERE"), nepieciešama normalizācija
- `latvian_identity_number_masked` — daļēji slēpts personas kods ("140777-*****") — pirmie 6 cipari = DDMMYY dzimšanas datums (≈ disambig pa kohortu)
- `birth_date` — pilns DOB ja sniegts (parasti tukšs)
- `registered_on` — amata sākuma datums

**M2 Tier 1 algoritms (uzlabots ar verificētu schema)**:

1. Ielādē officers.csv `.scratch/ur/officers.csv` (cache, force-redownload pēc 7 dienām)
2. Filtrs: `entity_type='NATURAL_PERSON'` (atmet legal-entity officers)
3. Indeksē `name` field, normalizējot abus formātus uz vienotu "FIRSTNAME LASTNAME" tuple
4. Per `vad_family` rindu: ja unikāls hit `name` indeksā → `family_high` link; ja vairāki, izmantot `latvian_identity_number_masked` pirmos 6 ciparus pret politiķa zināmo dzimšanas gadu (filtrs ±2 g) — ja tas atstāj 1 hit, vēl `family_high`; ja >1 — `family_medium`
5. Politiķa dzimšanas gads — TBD vai jau pieejams `tracked_politicians.notes`/`tracking_config`; ja ne, M2 sākas ar tier-2 (name match) un atstāj M2 Tier 1 līdz politicians DOB seeded

### 5.3 M2 Tier 2: family_medium (name match in supplier_name)

```sql
INSERT OR REPLACE INTO iub_politician_links (...)
SELECT
    d.opponent_id,
    c.supplier_reg_number,
    'family_medium',
    'medium',
    'vad_family+name_match',
    d.id, f.id, NULL,
    'family_name=' || f.full_name || ' matched in supplier_name=' || c.supplier_name
FROM vad_family f
JOIN vad_declarations d ON d.id = f.declaration_id
JOIN iub_contracts c ON UPPER(c.supplier_name) LIKE '%' || UPPER(f.full_name) || '%'
WHERE d.id = (latest annual per politician)
  AND LENGTH(f.full_name) >= 12;  -- avoid short common names creating noise
```

**Filters**:
- Vārda + uzvārda kopgarums ≥12 (atfiltrē "Anna Liepa" tipa noises).
- Supplier name `LIKE '%fullname%'` ar UPPER abām pusēm (vad_family ir UPPERCASE).
- Manuāls audit — operators pārbauda 100% no Tier 2 hits PIRMS publikācijas (nav fully automatic; `iub_politician_links.notes` operators atjauno ar `'reviewed_ok'` vai `'reviewed_rejected'`).

### 5.4 Negative_patterns paplašinājums

Sekot 2026-05-03 sanācijas paterns (skat. CHANGELOG): jauns lauks `tracked_politicians.iub_negative_patterns` (TEXT JSON list) — patterns, kas, ja tie atrasti supplier_name vai supplier_reg_number, izslēdz match. Sākotnējā curation: nulle, pievienots reaktīvi, kad publikācijā parādās false-positive.

---

## 6. Render layer

### 6.1 Pre-loader (`src/render/iepirkumi.py`)

Sekot `src/render/vad.py` paterns:
- `get_iepirkumi_for_politicians(db, pids) -> dict[pid] -> IepirkumiView`
- `IepirkumiView` dataclass ar `self_companies`, `family_links`, `total_value_eur`, `contract_count`.
- Try/except `sqlite3.OperationalError` guard.
- One-batch query per tabula — neviens N+1.

### 6.2 Profile sekcija (`templates/_iepirkumi_panel.html.j2`)

```jinja
{% if iepirkumi.contract_count > 0 %}
<section class="iepirkumi-panel">
  <h3>Iepirkumi</h3>
  <p class="muted">
    Iepirkumu līgumi piegādātājiem, kuros figurē politiķa vai viņa pirmās
    pakāpes ģimenes locekļa kapitāldaļa.
  </p>

  {% if iepirkumi.self_companies %}
  <h4>Politiķa uzņēmumi</h4>
  <table>
    <thead><tr><th>Uzņēmums</th><th>Līgumu skaits</th><th>Kopvērtība EUR</th></tr></thead>
    <tbody>
      {% for row in iepirkumi.self_companies %}
        <tr>
          <td>{{ row.supplier_name }} <span class="muted">({{ row.supplier_reg_number }})</span></td>
          <td>{{ row.contract_count }}</td>
          <td>{{ row.total_value_eur | format_eur }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if iepirkumi.family_links %}
  <h4>Ģimenes locekļu uzņēmumi</h4>
  <table>
    {# similar structure with confidence badges #}
  </table>
  {% endif %}

  <p class="metodika-piezime">
    Datu avots: <a href="https://www.iub.gov.lv/lv/atvertie-dati">IUB atvērtie dati</a>.
    Politiķa kapitāldaļas no VID amatpersonu deklarācijām (jaunākā ikgadējā).
    Sasaiste = piegādātāja reģistrācijas numura sakritība, ne nozares vai ģimenes
    locekļu prezumpcija. Konteksts, ne apsūdzība.
  </p>
</section>
{% endif %}
```

### 6.3 Profile tab integration

Lēmums: sekciju ievietot **Deklarāciju tab apakšā**, NE jaunu tab. Iemesls:
- Politiķim ar 0 līgumiem nav lietderīgi pievienot tab.
- Konteksts jāredz blakus deklarētajām kapitāldaļām (vad_companies sekcija).
- `_profile_tab_set()` paplašināt nav nepieciešams.

Implement: `templates/politician.html.j2` esošais Deklarāciju tab content block paplašināms ar `{% include '_iepirkumi_panel.html.j2' %}` zem VAD sekciju tabulām, conditional uz `iepirkumi.contract_count > 0`.

### 6.4 Analīzes lapa

`content/analizes/iepirkumi-2026.md` — frontmatter + Markdown ar 5 sekcijām:

1. **Datu kopa**: cik līgumu × cik unikālu politiķu × cik laika perioda.
2. **Top-N politiķi pēc kopvērtības** (savs uzņēmums + ģimenes pirmās pakāpes locekļi).
3. **Top-N atsevišķo SIA** kopvērtība (kāds politiķa SIA ir saņēmis visvairāk).
4. **Pasūtītāju ainava** — kuras ministrijas / pašvaldības visbiežāk slēdz līgumus ar tracked-politiķu uzņēmumiem.
5. **Metodika + atvērtie jautājumi** — eksplicits paskaidrojums, ka tas ir konteksta sniegums.

Atjaunošana: re-render mēneša rutīnā pēc IUB ingest sweep.

---

## 7. CLI skripti

### 7.1 `scripts/ingest_iub_contracts.py`

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_iub_contracts.py
    [--from 2023-10-25]            # default: pirmais pieejamais (2023-10-25)
    [--to 2026-05-04]              # default: tagadne
    [--limit N]                    # tikai N pirmās dienas (debug)
    [--dry-run]                    # neraksta DB, parāda rinda count
    [--force-redownload]           # neignorē cached file
```

Ielādes ceļš:
1. Iterē dienas no `--from` līdz `--to`.
2. Per dienai: lejupielādē `https://open.iub.gov.lv/data/notice/<YYYY>/<MM>/<DD-MM-YYYY>.json` uz `.scratch/iub/notice/<YYYY>-<MM>-<DD>.json` (cached).
3. Parser JSON: filtrs `formType IN ('result','execution','cont-modif')`.
4. Per filtered notice: iterē `lots[].contracts[].winners[].winnerBusinessParties[]` un izveido vienu rindu katram (notice, lot, contract, supplier) tuple.
5. Datumi: `conclusionDate` "DD/MM/YYYY" → "YYYY-MM-DD" ISO.
6. `INSERT OR IGNORE INTO iub_contracts` per rinda.

Output: `wiki/log-ingest/<gads-mēnesis>.md` ieraksts ar (jauni rindas, atjaunoti rindas, kopā tabulā, dienas pārklājums).

### 7.2 `scripts/compute_iub_links.py`

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/compute_iub_links.py
    [--politician slug]            # tikai 1 politiķi (debug)
    [--tier self|high|medium|all]  # default: self un high
    [--dry-run]
```

Pure SQL re-compute pār `vad_companies` × `vad_family` × `iub_contracts`. Bez ārējā fetch (UR lookup ir cached `.scratch/ur/cache.sqlite`).

### 7.3 Re-render

Pēc abu skriptu run — esošā komanda:
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
```

---

## 8. Rutīna un wiki integration

### 8.1 Wiki runbook

Jauns `wiki/operations/iepirkumu-krustparbaude.md` ar:
- Mēneša cikla soļiem (ingest IUB → recompute links → re-render).
- Failure modes (IUB CSV pieejamības, regnr formātu maiņas, false-positive triage).
- Pārbaudes vaicājumi (cik politiķiem ir self_company links, cik family_high, cik family_medium pēc audita).

### 8.2 Daily routine

NE iekļauts. Iepirkumu dati mainās lēni (nedēļa-mēnesis); daily brief un context_notes sistēma uz to nereaguje. Mēneša cikls pietiek.

### 8.3 Operācijas indeksu

Pievienot `wiki/operations/operacijas.md` Rokasgrāmatu tabulā:
```
| [Iepirkumu krustpārbaude](iepirkumu-krustparbaude.md) | Politiķu un ģimenes uzņēmumu IUB līgumu mēneša ingest + re-link |
```

### 8.4 commands.md

Pievienot `wiki/operations/commands.md`:
```bash
# Iepirkumu krustpārbaude (mēneša cikls)
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/ingest_iub_contracts.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/compute_iub_links.py
```

---

## 9. Test plan

- `tests/test_iepirkumi_schema.py` — `init_iepirkumi_tables()` idempotence, FK constraints.
- `tests/test_iepirkumi_ingest.py` — sample CSV → mock requests → row count + idempotency.
- `tests/test_iepirkumi_links.py` — vad_companies fixtures × iub_contracts fixtures → expected `iub_politician_links` rows.
- `tests/test_render_iepirkumi.py` — fixture politician with links → rendered HTML satur sekciju, bez links → nav sekcijas.
- Render baseline char fixture: `tests/render/iepirkumi_baseline.html` — pievienots REGEN paterns.

`bash scripts/check.sh` (ruff + pytest + generate_public_site smoke) jāpaliek zaļš.

---

## 10. Riski un mitigācijas

| Risk | Mitigācija |
|------|-----------|
| IUB CSV schema mainās laikā | Glabāt `raw_payload` JSON; re-parse no glabātā; warn pie unknown column |
| Family-high false-positive (UR unique hit, bet ne tas pats cilvēks) | Manuāls audit pirms publikācijas, `iub_negative_patterns` reaktīva curation |
| Politiķa SIA saņem līgumu pirms politiķa SIA piederības | Temporal alignment: `iub_contracts.contract_signed_at` jābūt LATER par `vad_declarations.declaration_year` (atstāt margin ±1 g); rāda "līgums laikā kad politiķis bija īpašnieks" piezīmi |
| Sākotnējā publikācijā nav atrodam "lielo" stāstu (visi politiķi tīri) | Publikācijas teksts uzsver: nullu rezultāts ir ziņa pati par sevi (proof of clean record). Operatora apstiprinājums pirms posting. |
| IUB OpenData portāls ir lēns / down | Lokāls cache `.scratch/iub/` ar manual force-redownload flag; M1 var palaist no cache vairākas dienas |
| UR atvērtie dati nav publiski | M2 Tier 1 atstāt M3 ja blocker, sākt ar self + Tier 2 vienreizēji |

---

## 11. Implementācijas plāns un milestones

| Milestone | Apjēga | DoD |
|-----------|--------|-----|
| M0 — Phase 0a verifikācija | ✅ DONE 2026-05-04 | IUB JSON endpoint dokumentēts § 3.1; UR officers.csv verificēts § 5.2; sample 30-04-2025.json + officers headers ielādēti `.scratch/iub/` |
| M1 — schema + IUB ingest + self_company links | 2-3 d (palielinājis no 2 d JSON parsēšanas dēļ) | `iub_contracts` ielādēts visam pieejamam logam (2023-10-25 → tagadne); `iub_politician_links` self_company hits redzami `compute_iub_links.py` output; render hidden līdz UI gatavs |
| M1.5 — proof-of-concept output | 0.5 d | Operators apskata `compute_iub_links.py` output (CSV/markdown); ja 0 hits → atgriežas pie scope; ja 3+ hits → turpina |
| M2 — family_medium (name match) + Tier 1 (UR officers) + audit pipeline | 3-4 d (politiķu DOB seed pievienots) | Manuālā audit kontroles saraksts; `iub_negative_patterns` curation ready; tracked_politicians.notes vai jauns `birth_year` lauks ar 152 politiķu DOB |
| M3 — render iepirkumi.py + templates + Deklarāciju tab + analīzes lapa | 2 d | atmina.lv/analizes/iepirkumi-2026.html publicējams; per-politiķis sekcija redzama; baseline tests passing |
| M4 — runbook + commands + log-ingest + wiki sync | 0.5 d | wiki/operations/iepirkumu-krustparbaude.md + commands.md atjaunoti |
| M5 — featured image + analizes promo + atminalv kanāla post | 0.5 d | graphics-designer aģents; operators apstiprina posting |

**Kopā: ~9-10 dienas** (no 9 d sākotnējās aplēses), ar 1 proof gate pēc M1.5.

---

## 12. Atvērtie jautājumi

**Q1**: Vai šī Phase 3a aizvieto VAD spec § 2 oriģinālo Phase 3 (sektoru-likumu sasaiste), vai paliek komplementāra (3a + 3b atsevišķi)?

**Atbilde**: Komplementāra. Phase 3b ir savādāks signāls (industriālā exposure, ne valsts maksājumi); to darīt **pēc** 3a, kad mums ir jauna analīzes lapa un labāk saprotama UI sekcija per-politiķis. Phase 3b spec atsevišķi (paredzams 2-3 nedēļas pēc 3a publikācijas).

**Q2**: Vai šī fāze prasa featured image hero plotu jaunajai analīzes lapai? Sekot vad-2026 paterns?

**Atbilde**: Jā, M5 — graphics-designer aģents pēc analīzes teksta gatavības.

**Q3**: ~~UR atvērto datu pieejamība — verificēt M0 fāzē.~~ **VERIFICĒTS 2026-05-04**: UR `officers` datu kopa publiska, CC0, dienas atjauninājums (skat. § 5.2). M2 Tier 1 viable. Galvenais šķērslis: politiķu DOB seedēšana, lai nodrošinātu cohort filter ar `latvian_identity_number_masked` pirmajiem 6 cipariem. Apjēga: ~152 politiķu DOB curation no Wikipedia / Saeimas profiliem ~1 d.

**Q4**: Vai rādīt vēsturiskās piederības (politiķis pārdevis SIA pirms gada, līgums noslēgts pirms tam)?

**Atbilde**: V1 — nē, tikai "jaunākā ikgadējā" piederības. V2 (Phase 3a.1) — pievienot vēsturiskās rindas no veco gadu deklarācijām, ja signāla kvalitāte pierāda.

**Q5**: Anti-pattern check — vai šī specifikācija ievēro CLAUDE.md invariants?

**Atbilde**:
- Inv #1 (Pydantic strict): N/A — šī fāze neizmanto save_analysis() sniegtās tipologijas.
- Inv #2 (claims need source_url): N/A — neģenerē claims.
- Inv #3 (store_claim idempotent): N/A.
- Inv #4-6 (claim_type, document_id Optional): N/A.
- Inv #7 (contradiction check): N/A — neģenerē claims.
- Inv #10 (parties.coalition_status truth): N/A — politiķa profila lapā jau lietots.
- Inv #11 (social_accounts feed_type): N/A.
- Inv #12 (saeima_votes.bill_id append-only): N/A — netiek ar tiem darīts.

Tīrs no invariant violations.

---

## 13. Decisions log

| # | Lēmums | Iemesls |
|---|--------|---------|
| D1 | Jauna `src/iepirkumi/` pakete, ne paplašinājums `src/vad/` | IUB ir savs datu avots ar savu auth + politiku; sapludināšana piesārņotu vad/ paketi |
| D2 | 2 tabulas (`iub_contracts` + `iub_politician_links`), ne viena | Idempotence pa abām dimensijām atsevišķi (CSV ielāde un crosswalk) |
| D3 | Sekcija profilā, ne jauns tab | Konteksts jāredz blakus kapitāldaļām; tabu skaits jau pārpildīts |
| D4 | Manuāls audit pirms publikācijas Tier 2 family hits | False-positive rate pārāk augsta (~5% sample) automātiskai publikācijai |
| D5 | Atstāj Tier 3 (low confidence) backlogā | Trokšņa attiecība par augstu, gaida UI eksperiments |
| D6 | Tikai jaunākā ikgadējā per politiķis (sākotnēji) | Konsekvence ar VAD analīzi § 5/§ 6 (kapitāldaļu saraksts no jaunākās) |
| D7 | NE atomāra automatizācija — manuāls re-run mēneša cikls | IUB datu freshness reti mainās; daily brief uz to nereaguje |
| D8 | JSON ielāde, ne CSV (M0 verifikācija pārrakstīja sākotnējo pieņēmumu) | IUB ir migrējis uz EU eForms 2024 — JSON ar BT-koda lauku referencēm |
| D9 | 2.5 g vēstures logs (no 2023-10-25) sākotnēji, ne 10 g | Līgumi (concluded contracts) datu kopa pieejama tikai no 2023-10-25; vēsturiski Publikācijas datu kopa no 2013 ir paziņojumu pirms-līguma stadija, ne piegādātāju ieraksti |
| D10 | UR officers.csv `name` formāts "Surname Firstname" — nepieciešama normalizācija pret vad_family "FIRSTNAME SURNAME" UPPERCASE | M0 verifikācijā konstatēts; piegādā normalizācijas helperi `src/iepirkumi/links.py` |
| D11 | Politiķu DOB seedēšana M2 priekšnoteikums | UR `latvian_identity_number_masked` pirmie 6 cipari = DDMMYY; bez politiķa zināmā dzimšanas gada cohort filter nav iespējams |

---

## 14. Saistītā literatūra

- VAD spec: `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md`
- Saeima bills spec (paterns): `docs/superpowers/specs/2026-04-22-saeima-bills-design.md`
- VAD analīze (datu avots): `content/analizes/vad-2026.md`, atmina.lv/analizes/vad-2026.html
- IUB OpenData portāls (M0 verificēts): https://www.iub.gov.lv/lv/atvertie-dati
- IUB notice JSON endpoint: https://open.iub.gov.lv/data/notice/<YYYY>/<MM>/<DD-MM-YYYY>.json
- IUB metadata: https://open.iub.gov.lv/data/publiskie_iepirkumi_metadata.json
- UR atvērtie dati `officers` (M0 verificēts): https://data.gov.lv/dati/lv/dataset/officers
- UR officers CSV download: https://data.gov.lv/dati/dataset/096c7a47-33cd-4dc9-a876-2c86e86230fd/resource/e665114a-73c2-4375-9470-55874b4cfa6b/download/officers.csv
- Likums "Par interešu konflikta novēršanu valsts amatpersonu darbībā": https://likumi.lv/ta/id/61913

---

*Pirmais melnraksts: 2026-05-04. Status: M0 PABEIGTS 2026-05-04 (IUB JSON + UR officers.csv verificēti). Gaida lietotāja apstiprinājumu pirms M1 sākuma.*
