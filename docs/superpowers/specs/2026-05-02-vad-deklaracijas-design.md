# VID amatpersonu deklarāciju (VAD) izsekotājs — Phase 0+1 dizaina specifikācija

**Datums**: 2026-05-02
**Izcelsmes konteksts**: Lietotāja pieprasījums (Telegram 2026-05-02 13:59) — automatizēt mūsu izsekoto politiķu amatpersonu deklarāciju ielādi, glabāšanu un publikāciju no [www6.vid.gov.lv/VAD](https://www6.vid.gov.lv/VAD).
**Saistītie specs**: `2026-04-22-saeima-bills-design.md` (strukturētu datu paketes paterns), `2026-04-09-document-politicians-junction-design.md` (junction patern, šeit nav lietots — VAD izvairās no `documents` rindas)
**CHANGELOG atsauce pēc ieviešanas**: `wiki/CHANGELOG.md § VAD declarations tracker (Phase 0+1)`
**Statuss**: design draft — gaida lietotāja review

---

## 1. Mērķis

Ieviest `src/vad/` paketi, kas regulāri (manuāli, ar mēneša cikla noklusējumu) izvilkts no VID amatpersonu deklarāciju portāla pilnu strukturētu ierakstu kopumu par mūsu 152 izsekoto politiķu (`relationship_type='tracked'`) deklarētajiem ienākumiem, mantu, amatiem, parādiem, aizdevumiem un ģimeni. Datus glabāt 11 normalizētās `vad_*` tabulās (saeima_* paterns), nesaistot ar `documents` (skat. invariants #6/#12 — strukturētiem datiem nav `documents` rindas) un nesaistot ar `claims` (deklarācijas ir faktu izpaušana, nevis retoriskas pozīcijas).

UI līmenī — pievienot **"Deklarācijas"** tab katram politiķim, kuram ir vismaz viena VAD ieraksts. Tabā renderē gads-pa-gadam tabulas par 7 galvenajām sekcijām (amati, NĪ, kapitāldaļas, transports, naudas uzkrājumi, ienākumi, parādi/aizdevumi) ar **delta marķieriem** (jauns šogad / mainījies / aizmuk salīdzinot ar iepriekšējo gadu). Ģimene un narratīvās sekcijas (cita info, trasta līgumi) parādās zem "Detalizēti" collapsed seciju.

Kvalitātes mērķis: lietotājs uz politiķa profila redz vienu kopskatu, kas saista deklarētos uzņēmumus + nekustamos īpašumus + ienākumus + ģimeni ar gada-pa-gadam dinamiku — bez tā jāstaigā pa VID portāla 6+ klikšķiem per gads.

---

## 2. Scope

### Phase 0 — Ingest + storage (šis spec, MVP I daļa)

- Jauna `src/vad/` pakete: `schema.py` (DDL), `fetch.py` (httpx + cookie session), `parsing.py` (BeautifulSoup section parsers), `declarations.py` (orchestrator), `__init__.py` (public API).
- 11 jaunas `vad_*` tabulas (skat. § 4).
- `scripts/ingest_vad_declarations.py` CLI ar `--politician {slug|all}`, `--year {YYYY|all}`, `--limit N`, `--dry-run`, `--max-age-days D`.
- Politiķu sasaiste — ar tracked-driven plūsmu (skat. § 6); NAV `match_politicians(body)` zvanu (deklarācijā politiķa vārds ir noteikti zināms).
- `wiki/log-ingest/<gads-mēnesis>.md` ieraksts ar deklarāciju skaitu + politiķu skaitu.
- Tikai **modernās deklarācijas** (`HrefVad` type "2", `/VAD/VADData` URL) — pre-2010 (`/VAD/VAD2002Data`) ir cita HTML struktūra, atstājam Phase 0.5 backlogā.

### Phase 1 — Publiskais arhīvs (šis spec, MVP II daļa)

- Jauns `src/render/vad.py` modulis — pre-loads VAD datus visiem politiķiem (one batch query per tabulu, in-memory grouping); follo F4 leaf-vs-fan-out paterns (sk. CHANGELOG 2026-04-29).
- `templates/_vad_panel.html.j2` — fragments, kas renderē 7 sekciju tabulas + delta marķierus.
- `templates/politician.html.j2` paplašinājums — jauns `{% if 'deklaracijas' in tab_set %}` tab content block + `<button>` `profile-stats-bar` rindā.
- `src/profile_kind.py` paplašinājums — `_profile_tab_set()` pievieno `'deklaracijas'` deputātiem, ministriem, regional, mep, former, politician (visiem, kuriem ir VAD amatpersonu obligation; **NEietver** journalist/analyst/organization/inactive — sk. § 9.3 sarakstu) — bet **tikai ja ir vismaz 1 stored deklarācija** (has_data konditionāls, tāpat kā `'pretrunas'`).
- Year-over-year diff helper `src/vad/diff.py` — `compute_section_deltas(prev_year_rows, this_year_rows)` atgriež `[{"row": ..., "delta": "new"|"removed"|"unchanged"|"modified", "diff_text": "..."}]` katras sekcijas tabulai.
- `wiki/operations/vad-declarations.md` runbook (operatorinstrukcija, troubleshooting, rate-limit politika).

### Ārpus Phase 0+1 (Phase 2-4, atsevišķi specs)

- **Phase 2 — Anomāliju detect** (B): delta-engine bāzēts daily brief trigeris + manuāla "Šomēnes deklarācijās" sekcija ar operatora-Claude apstiprinājumu pirms `context_notes` ierakstīšanas.
- **Phase 3 — Interest-conflict cross-link** (C): `vad_companies` × `saeima_bills.topic` → `vad_conflicts` jauna tabula vai `contradictions.contradiction_type='interest_conflict'` paplašinājums (lēmums Phase 3 specā). Prasa topic-mapping no uzņēmuma nozares (likely jauns `vad_industry_map.py` ar manuāli kuratoriem signāliem).
- **Phase 4 — Tīkla analīze** (D): query-only sloss virs Phase 0 tabulām (kuri politiķi kopīgi figurē tajā pašā SIA / biedrībā / aizdevumā). Iespējamais surface — paplašinājums `src/render/links.py` mini-grafam vai jauna `/saites.html#deklaracijas` apakšcilne.
- **Pre-2010 legacy declarations** (Phase 0.5): `/VAD/VAD2002Data` parser. Apjēga ~150 LOC + atsevišķs DDL adaptors. Atstājam, jo trekno datu (Saeimas atgriešanās 2022+) nav šajā periodā.
- **KNAB integrācija** (Phase 5): VAD sekcija 7 (ienākumi) → `knab_alerts.declaration_mismatch` reālā implementācija (šobrīd alert tipus eksistē, bet salīdzināmo datu nebija). Dabīgs cross-link, bet ne foundation darbs.
- **Family-relations cross-link**: kāds VAD ģimenes loceklis figurē kā **cits** politiķis vai donors. Phase 5+.
- **Auto-photos / wiki sync**: nav nepieciešams — VAD nesatur foto.

---

## 3. Avota analīze (VID portāla kontrakts)

Manuāli probed 2026-05-02 11:00 LV ar Playwright. Pilnais transkripts — Claude konteksts.

### 3.1 Search endpoint

```
POST https://www6.vid.gov.lv/VAD/Data
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Body: Name=<vārds>&Surname=<uzvārds>&From=<offset>
```

URL-encoded ar `Ā%C4%81`-formas diakritikiem (klients dara to standarta). Atgriež HTML fragment ar `<table>` ar zero+ rindām per amats (politiķim ar daudzām lomām var būt 6+ rindas — Šleseram bija 6: Saeimas deputāts, MK biedrs, ministrs, RD vietnieks, atkārtoti Saeimas deputāts, RD deputāts).

Katra deklarācijas link ir `<a href="#" onclick="return HrefVad('<UUID>', '<TYPE>');">`, kur:

- `UUID` = lowercase hex GUID (piem. `a7828ca0-a63c-41a6-9275-64d365652eb0`).
- `TYPE` = `'2'` modernai (post-~2010), `'0'` legacy (pre-~2010).

`From=` parameter ir lapošanas offset (testēts ar `From=0`; nav skaidrs, vai ir > 50 results paginācija — tracked politiķiem mazticams).

### 3.2 Detail endpoint

```
GET https://www6.vid.gov.lv/VAD/VADData
Cookie: VADData=<UUID>
```

Cookie iestatīts `setCookie("VADData", item, false, "/", false, false)` (path "/", non-secure, non-httpOnly — vaniļa dokumenta cookie). Servers atgriež pilnu HTML lapu ar 14 numurētajām `<h2>` sekcijām un `<table>` per sekciju (skat. § 5 parser layout).

Legacy URL: `/VAD/VAD2002Data` ar to pašu cookie paterns (Phase 0.5 backlogs).

### 3.3 Pre-flight token

```
GET https://www6.vid.gov.lv/ReqCode?check=true&pageName=VADList
Response: ~5 bytes (token kods)
```

Tiek izsaukts pirms POST `/VAD/Data`. Šobrīd nepieciešams session cookies kontekstā — bez tā 403 nav novērots, bet arī ne testēts. **Drošības margināls: vienmēr palaist pirms search**.

### 3.4 Anti-bot stāvoklis

- `recaptcha_ajax.js` GET tiek mēģināts no klienta JS, bet **ORB-blokēts** (nav `*.gstatic.com` SRI shara). Paliek "labākajā gadījumā nemēģinošs" reCAPTCHA — server-side enforcement netiek demonstrēts neapskataitos manuālos testos (1 search + 1 detail = 0 captcha challenge).
- `Content-Security-Policy` neatļauj third-party JS izņemot `www.vid.gov.lv` un `www.google.com` reCAPTCHA — bet politika ir headers-līmeņa, nav deklarētais enforcement.
- Servera `cache-control: no-cache, no-store` un `pragma: no-cache` — visi requests fresh.

**Throttling politika** (drošības margināls, atjaunots pēc F11/F12 atklājumiem 2026-05-02): **10 sekunžu** pause starp politiķiem (search calls), 3 sekundes starp deklarāciju detail fetchiem. Visi requests ar mūsu kanonisko User-Agent (`atmina.lv/1.0 (kontakts@atmina.lv)`). Iemesls 5s → 10s palielinājumam: empīriski tests 30s starpā same-session search atgriež reālus rezultātus, bet sub-second back-to-back search dod ReadTimeout. 10s drošības margināls.

**Reālā apjoma matemātika** (korekcija pēc spec review):
- **Initial backfill**: 152 search × 10s = 25 min + ~3 detail fetch per politiķis × 152 × 3s = 23 min = **~48 min**.
- **Mēneša sweep** (steady-state): 152 search × 10s = 25 min + 0-2 jauni detail × 152 × 3s avg = ~3 min = **~28 min**.
- **Peak aprīlis-maijs**: 152 search × 10s + ~1 jauns detail × 152 × 3s = **~33 min**.

Visiem scenārijiem pieņemami; uzbrukums VID portālam ir nulles.

**Retry politika**: maks 2 retries ar exponential backoff (5s, 30s) tikai `5xx` un `429` atbildēm. `403` un `404` — fail loud, write to log, neturpināt sweep. Šī ir VID portāls — uzbrukums tam ir reputational risk, droši brīdina pie pirmā signāla.

### 3.5 Datu kvalitāte un freshness

- "Iesniegta VID" + "Publicēta" datumi katrai deklarācijai — laba provenance.
- Deklarāciju iesniegšanas termiņš par iepriekšējo gadu — līdz 1. aprīlim. Publikācija parasti ~2-3 nedēļas pēc tam → mēneša rutīnai pieņemams (peak ingest aprīlis-maijs, citos mēnešos parasti 0-2 jauni ieraksti).
- HTML struktūra stabila kopš ~2020 (manuāla apskate 2022/2023/2024 deklarācijām — identiska).
- Nav PDF — viss HTML, BeautifulSoup pietiek.

---

## 4. Datu modelis

11 jaunas tabulas. Visas `IF NOT EXISTS`, idempotenta `init_vad_tables()` funkcija `src/vad/schema.py` (saeima/schema.py paterns).

### 4.1 Header tabula

```sql
CREATE TABLE IF NOT EXISTS vad_declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    vad_uuid TEXT,                              -- VID portāla session-bound nonce; rotē per-call (skat. § 15 F11). Glabājam pēdējo redzēto vērtību audit/debug priekš; NAV stable identifier
    declaration_type TEXT NOT NULL,             -- "Kārtējā gada deklarācija - par 2024. gadu" (raw label)
    declaration_kind TEXT NOT NULL,             -- normalized enum: "annual"|"start"|"end"|"post_year_1"|"post_year_2"|"interim"
    declaration_year INTEGER,                   -- gads, par kuru ir deklarācija (2024 priekš "par 2024. gadu"); NULL ja nav gads-bāzēta (sākuma/beigas)
    institution TEXT,                           -- "Latvijas Republikas Saeima"
    position_title TEXT,                        -- "Saeimas deputāts"
    submitted_at TEXT,                          -- ISO date "2025-03-27"
    published_at TEXT,                          -- ISO date "2025-04-17"
    -- narratīvās sekcijas, glabājam free-text
    other_info TEXT,                            -- sec 13 cita informācija
    financial_instruments_text TEXT,            -- sec 4b apraksts (parasti tukšs)
    other_benefits_text TEXT,                   -- sec 11 narratīvs
    trust_agreement_text TEXT,                  -- sec 11b narratīvs
    has_private_pension INTEGER,                -- sec 12: 1=ir, 0=nav, NULL=nav norādīts
    has_life_insurance INTEGER,                 -- sec 12: 1=ir, 0=nav, NULL=nav norādīts
    source_url TEXT NOT NULL,                   -- search-link priekš lasītāja: "https://www6.vid.gov.lv/VAD?Name=<vārds>&Surname=<uzvārds>" (verificējams ar GET; portāla deep-link uz konkrēto deklarāciju nav publiski pieejams cookie-protokola dēļ — UUID glabājas atsevišķi vad_uuid laukā)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_html TEXT,                              -- pilns detail HTML (nullable; debugošanai un re-parse'am)
    UNIQUE(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)
);
CREATE INDEX IF NOT EXISTS idx_vad_decl_opponent ON vad_declarations(opponent_id);
CREATE INDEX IF NOT EXISTS idx_vad_decl_year ON vad_declarations(declaration_year);
CREATE INDEX IF NOT EXISTS idx_vad_decl_published ON vad_declarations(published_at);
```

**UNIQUE atslēga — dabīgais identifikators (atjaunots pēc F11):** `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)`. Iemesls: `vad_uuid` rotē per-call (skat. § 15 F11), tāpēc nav lietojams idempotencei. Dabīgā atslēga sedz visus 6 deklarāciju veidus:
- **annual** — kind+year+position vienreiz per politiķis (var būt vairāki amati = vairākas atsevišķas deklarācijas par to pašu gadu)
- **start/end/post_year_*** — submitted_at datums identifikatorā (year=NULL).
- SQLite UNIQUE NULL semantika: divas `NULL` vērtības tiek uzskatītas par dažādām → multi-NULL deklarācijas tomēr unikalitāte. Aizsardzība — `submitted_at` parser obligāts visiem ne-annual deklarāciju veidiem (raises ValueError ja nav).

**Source URL politika** (precizēta pēc spec review 2026-05-02): `source_url` saglabā search-link formu `?Name=X&Surname=Y` — VID portāla GET-pieņemts (jāverificē Phase 0 implementācijā § 13 Q1), kas atver search ar pre-filled politiķa vārdu. `vad_uuid` ir nullable session-bound nonce, glabājas tikai audit/debug priekš (skat. § 15 F11).

`raw_html` — saglabājam pilnu HTML, lai re-parse būtu iespējams bez atkārtotas portāla apmeklēšanas. ~50-200 KB per deklarācija; 152 politiķi × ~3 deklarācijas = ~50 MB DB pieaugums. Pieņemams. **Lēmums**: saglabājam pirmajā ingest, brutāli `raw_html=NULL` UPDATE pēc 90 dienām (storage cleanup script Phase 0.5).

### 4.2 Sekciju tabulas

Visas FK uz `vad_declarations.id` ON DELETE CASCADE. Visas ar `id INTEGER PRIMARY KEY AUTOINCREMENT`. Kolonnas atspoguļo precīzu portāla tabulas kolonnu kopu (skat. § 5 parser).

```sql
-- Sec 2: Citi amati (board/NGO/party positions)
CREATE TABLE IF NOT EXISTS vad_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    position_title TEXT NOT NULL,               -- "Likvidators", "Valdes loceklis", "Izpildinstitūcija, tiesības pārstāvēt atsevišķi"
    entity_name TEXT NOT NULL,                  -- "LATVIJA PIRMAJĀ VIETĀ", "Biedrība \"LATVIJA PIRMĀ\""
    entity_reg_number TEXT,                     -- "40008310156" (Latvijas reģistrācijas Nr.)
    entity_address TEXT,                        -- "Latvija, Rīga, Mazā Smilšu iela 15"
    is_individual INTEGER NOT NULL DEFAULT 0    -- 0 = juridiska persona; 1 = fiziska persona (vārds+uzvārds entity_name)
);

-- Sec 3: Nekustamie īpašumi
CREATE TABLE IF NOT EXISTS vad_real_estate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    property_type TEXT NOT NULL,                -- "Zeme", "Dzīvoklis", "Zeme un ēkas"
    location TEXT NOT NULL,                     -- "Latvija, Annenieku pag."; "Latvija, Rīga"
    ownership_status TEXT NOT NULL              -- "īpašumā", "kopīpašumā", "valdījumā", "lietošanā"
);

-- Sec 4: Komercsabiedrību kapitāldaļas
CREATE TABLE IF NOT EXISTS vad_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    reg_number TEXT,
    address TEXT,
    capital_kind TEXT NOT NULL,                 -- "Kapitāla daļas", "Akcijas", "Sertifikāti"
    units REAL,                                 -- daļu / akciju / sertifikātu skaits (REAL nevis INTEGER, jo investīciju fondu apliecības var būt fractional)
    total_value REAL,                           -- summa
    currency TEXT                               -- "EUR", "USD"
);

-- Sec 5: Transportlīdzekļi
CREATE TABLE IF NOT EXISTS vad_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    vehicle_type TEXT NOT NULL,                 -- "Automašīna", "Motocikls"
    brand TEXT NOT NULL,                        -- "MERCEDES BENZ AMG GLS 63"
    year_made INTEGER,
    year_registered INTEGER,
    ownership_status TEXT NOT NULL              -- "īpašumā", "valdījumā", "lietošanā"
);

-- Sec 6: Naudas uzkrājumi (cash + bank holdings) — polymorphic
CREATE TABLE IF NOT EXISTS vad_savings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    savings_kind TEXT NOT NULL,                 -- "cash" | "bank"
    amount REAL NOT NULL,
    currency TEXT NOT NULL,                     -- "EUR", "USD"
    amount_in_words TEXT,                       -- raw label (cash only); NULL bankas rindām
    holder_name TEXT,                           -- bankas/turētāja nosaukums; NULL cash rindām
    holder_reg_number TEXT,                     -- NULL cash rindām
    holder_address TEXT                         -- NULL cash rindām
);

-- Sec 7: Visi ienākumi
CREATE TABLE IF NOT EXISTS vad_income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    source TEXT NOT NULL,                       -- "Latvijas Republikas Saeima, 90000028300, ..." (raw cell text, including reg+adrese inline)
    source_reg_number TEXT,                     -- ekstrakts no source ja juridiska persona (regex `\b[49]\d{10}\b` Latvijas reģ.nr.); NULL fiziskām personām
    is_individual INTEGER NOT NULL DEFAULT 0,   -- 0 = juridiska persona; 1 = fiziska persona (piem. "Inese Šlesere, ," — empty reg+adrese signāls)
    income_type TEXT NOT NULL,                  -- "Alga", "Dāvinājums", "Apdrošināšanas atlīdzība", "Dividendes", "Mantojums"
    amount REAL NOT NULL,
    currency TEXT NOT NULL
);

-- Sec 8: Darījumi >20 MMA
CREATE TABLE IF NOT EXISTS vad_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    transaction_description TEXT NOT NULL,      -- raw 1-2 col cell (struktūra mainīga, glabājam plain-text)
    amount REAL,
    currency TEXT
);

-- Sec 9: Parādsaistības >20 MMA
CREATE TABLE IF NOT EXISTS vad_debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    creditor_name TEXT NOT NULL,
    creditor_reg_number TEXT,
    creditor_address TEXT,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    amount_in_words TEXT
);

-- Sec 10: Izsniegtie aizdevumi >20 MMA
CREATE TABLE IF NOT EXISTS vad_loans_given (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    amount_in_words TEXT
);

-- Sec 14: Ģimene
CREATE TABLE IF NOT EXISTS vad_family (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,                    -- "INESE ŠLESERE"
    relation TEXT NOT NULL                      -- "Laulātais", "Dēls", "Māte", "Māsa", "Brālis", "Tēvs"
);

CREATE INDEX IF NOT EXISTS idx_vad_positions_decl ON vad_positions(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_positions_reg ON vad_positions(entity_reg_number);
CREATE INDEX IF NOT EXISTS idx_vad_real_estate_decl ON vad_real_estate(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_companies_decl ON vad_companies(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_companies_reg ON vad_companies(reg_number);
CREATE INDEX IF NOT EXISTS idx_vad_vehicles_decl ON vad_vehicles(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_savings_decl ON vad_savings(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_income_decl ON vad_income(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_transactions_decl ON vad_transactions(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_debts_decl ON vad_debts(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_loans_decl ON vad_loans_given(declaration_id);
CREATE INDEX IF NOT EXISTS idx_vad_family_decl ON vad_family(declaration_id);
```

**Indeksu komentārs**: `entity_reg_number` un `reg_number` ar indeksu — Phase 4 (tīkla analīze) prasa "kuri politiķi figurē tajā pašā SIA" — tas ir join pa `reg_number` pār vad_companies un vad_positions. Indeksi maksā ~10% storage, bet Phase 4 query bez tiem būs O(N²).

### 4.3 Kāpēc nav `documents` rindas

Saeima 2026-04-25 cleanup ieviesa invariant #6: "documents.platform='saeima' rows no longer allowed" jo strukturēti dati nav narrative documents. Tas pats arguments šeit:

- VAD deklarācija nav cilvēkam-lasāms raksts ar nozīmīgu tekstu — tā ir tabulas datu dump.
- Junction (`document_politicians`) deģenerējas trivialitātē — vienmēr 1:1 (deklarācija pieder vienam politiķim).
- Embedding pār deklarāciju saturu nav lietderīgs — deklarācija nesatur retorisku saturu, ko semantically search'ot. Jebkurš `search_similar_claims` zvans pār deklarāciju embedding'iem atgrieztu troksni.
- Render path pēc Saeimas cleanup vairs neuzskata `documents` par truth source — tas pats šeit.

### 4.4 Kāpēc nav `claims` rindas

Saeima 2026-04-11 ieviesa `claim_type='saeima_vote'` — strukturētie balsojumi tika reprezentēti kā claims, jo tie ir "akts, ko politiķis veicis" (subject + topic + stance + source_url). Vai VAD deklarētās ziņas to atbilst?

**Nē — un tas ir apzināts dizaina lēmums**:

- Claim semantika = retoriska/aktu pozīcija ("X teica/balsoja par Y attiecībā uz Z"). Deklarētais "man pieder 1000 daļas SIA AVADEL" nav pozīcija, tas ir disclosure.
- Claims tabula ir `topic`-orientēta (`src.topic_map`). Deklarētajam ienākumam vai NĪ nav saturīga `topic` — tāpēc to mēģinot iespiest claims, jāizdomā mākslīgs `topic='finanses'` vai pat 11 jauni topic'i (NĪ, transports utt.), kas piesārņo esošu topic-mapping.
- Dziļāka problēma: ja claim_type='vad_disclosure' tabulā piedalītos, tad `_fetch_politicians()` `claims_count` ar default `claim_type='position'` filtrs jau atrisina — bet visi citi readers (briefs, contradictions, wiki sync) saņem implicit drift. **YAGNI** — neveidojam claims par to, par ko nav nepieciešamas claims-features (cross-claim search, pretrunu detect, tendences).
- Phase 3 (interest-conflict) varētu radīt **derivative** claims vai contradictions, bet tās ir Phase 3 lēmums, ne Phase 0+1.

Saglabājam claims tabulu tīru: tā ir retorikai un balsojumiem.

### 4.5 Migration impact

- `init_vad_tables()` **netiek** izsaukts no `init_db()` boot path (saskaņā ar saeima/schema.py precedentu — `init_saeima_tables()` arī ir lazy; render layer guard ar try/except OperationalError, ja test DB nav palaidis init). Trīs aktivācijas vietas:
  1. `scripts/ingest_vad_declarations.py` palaidē kā pirmais step (skat. § 8).
  2. `src/render/vad.py` modulis — pirmais SELECT pār `vad_declarations` ietīts `try/except sqlite3.OperationalError`, ja tabula nepastāv → atgriež tukšu dict (sekot saeima_bills paterns `src/render/politicians.py:503`).
  3. `tests/conftest.py` — vai per-test fixture, kas palaiž `init_vad_tables(test_db)` pirms VAD-related testiem.
- Foreign key `ON DELETE CASCADE` strādā: `get_db()` jau iestata `PRAGMA foreign_keys = ON` (`src/db.py:209`).
- Nav backward-compat shim'u — VAD ir green-field. Nav arī rollback skripta — drop'osim `vad_*` tabulas, ja nepieciešams (visas dati atjaunojami no portāla).
- Pre-merge: `python -c "from src.vad.schema import init_vad_tables; init_vad_tables()"` smoke + `bash scripts/check.sh` pilna validācija.
- WAL implications `raw_html` glabāšanai: 50 MB DB pieaugumam atbilst ~50 MB WAL pieaugumam pie peak ingest. SQLite WAL automātiski checkpoint'os pie ~1000 lapām — pieņemams.

---

## 5. Parser layout (`src/vad/parsing.py`)

BeautifulSoup4 (jau projektā). HTML struktūra atklāj sekcijas pa numurētajām `<h2>` rindām. Algoritms:

1. `BeautifulSoup(html, "html.parser")`.
2. Header tabula = pirmā `<table>` pirms pirmās numurētās `<h2>` (sec 2).
3. Katra numurētā `<h2>` (regex `^\s*(\d+)\.\s+`) ieskicē sekciju. Iterē DOM nākamos siblings līdz nākamai `<h2>` vai dokumenta beigām.
4. Sekcijas saturs = visas `<table>` pirmajā `<rowgroup>` (header) + otrajā (rows). Daži dokumenti ir `<table>` katrai sub-tabulai (sec 6 = 2 tabulas: cash + bank).
5. Narratīvās sekcijas (4b, 11, 11b, 13) = `<h2>` + nākamie `<p>` siblings (parasti tukši iepriekš testētajā politiķī, bet glabājam plain-text ja ir).
6. Sekcija 14 (ģimene) = pēdējā tabula pirms "Atgriezties" linku saraksta.

```python
# src/vad/parsing.py public API
def parse_declaration_html(html: str) -> ParsedDeclaration:
    """Parsē detail HTML uz strukturētu pydantic objektu.

    ParsedDeclaration ir Pydantic v2 model ar fieldiem header + 11 list[SectionRow] sekciju.
    Raises ValueError ja header nav pilnīgs (Vārds, deklarācijas tips, iesniegta-datums).
    Tukšas sekcijas → tukši list (ne None) — vienkāršo store layer.
    """
```

**Sekciju kanonisks identifikators** = numurs no `<h2>` regex. Sec 11 ir _divas_ apakšsekcijas (11a un 11b, abas ar tādu pašu virsraksta prefix bet atšķirīgu otro daļu — ParsedDeclaration glabā kā divus atsevišķus tekstu fieldus). Sec 4 ir kapitāldaļas un sec 4b (zem ne-numurētas `<h2>` "Deklarācijas iesniedzējam piederošie finanšu instrumenti...") ir parāda vērtspapīri. 4b nav numurēts portālā — parser to identificē kā _nākamo_ `<h2>` pēc sec 4 tabulas, pirms sec 5.

**Edge cases**:
- Tukša sekcija = `<h2>` bez `<table>` pēc tā līdz nākamai `<h2>`. Output `[]`.
- Sec 6 ar tikai cash vai tikai bank — atkarīgs no tabulu klāsta. Output filtrēts pa kuram tabulai.
- Multi-line cells — saglabājam ar `\n` separatoru, neturpinām split'ot.
- "Latvija, Rīga, Andrejostas iela 29" — adresēs komatu skaits mainīgs; saglabājam `address` kā kopēju lauku, nepārveidojam strukturētu.
- Currency = trīs-burtu kods (EUR/USD/RUB/GBP). Validējam pret `{"EUR", "USD", "RUB", "GBP", "JPY", "CHF", "SEK", "NOK", "DKK"}` whitelist. Nezināmi → log warn + saglabā raw vērtību.

**Parser sample plašums** (precizējums pēc spec review): Phase 0 spike empīriski apskatīta tikai 1 deklarācijas HTML struktūra (Šlesers 2024). Pirms parser tiek committed kā stable, **obligāti** apskatīt vismaz 5 dažādu politiķu HTML strukturas (proposed: Šlesers, Siliņa, Pupols (MEP — citāda institūcija), kāds bijušais ministrs ar daudzām kapitāldaļām, kāds ar tukšu sec 2). Ja struktūras atšķiras non-trivially (sekciju numerācijas drift, kolonnu skaita atšķirības tabulās), parser jāmīkstina vai jāparametrize.

**Test fixtures**: `tests/fixtures/vad/` katalogs ar 5 saglabātām HTML lapām (Šlesers 2024, Siliņa 2024, vienu MEP 2024, vienu bijušo ministru 2023, vienu jaundeputātu sākuma deklarāciju). Fixtures = git-controlled (~50-200 KB katra; ~1 MB total). Test helper `assert_parsed_declaration(html_path)` automatiski compare'ē pret JSON snapshot ar tādu pašu nosaukumu. Bootstrap helper `scripts/dump_vad_fixture.py --pid X --year Y --out tests/fixtures/vad/<name>.html` (pirmo reizi, kad ingest darbojas, dump'o HTML fixture'iem).

---

## 6. Politiķu sasaiste

VAD īpatnība: **nav nepieciešama politician matcher pār saturu** — mēs zinām politiķi PIRMS search'a izsaucam VID portālu. Plūsma:

```python
# src/vad/declarations.py
def fetch_for_politician(opponent_id: int, db: Connection) -> list[StoredDeclaration]:
    pol = db.execute("SELECT name, name_forms FROM tracked_politicians WHERE id=?",
                     (opponent_id,)).fetchone()
    name_forms = json.loads(pol["name_forms"] or "[]")
    primary_name = pol["name"]  # "Ainārs Šlesers"
    candidates = _split_name_candidates(primary_name, name_forms)
    # candidates = [("Ainārs", "Šlesers"), ...] — multiple ja ir name variants
    rows = []
    for first, last in candidates:
        results = vid_search(first, last)  # POST /VAD/Data
        rows.extend(results)
        if rows:
            break  # pirmais successful match wins
    return [_fetch_and_store(opponent_id, r, db) for r in rows]
```

### 6.1 Vārdu split

**Korekcija pēc spec review (2026-05-02):** `tracked_politicians.name_forms` empīriski apskatīts — tā ir **deklinēto uzvārdu** lista (piem. Šleseram `["Šlesers", "Šlesera", "Šleseram"]`), kuru izmanto `match_politicians()` text-scanning. Tā **nav** alternative full-name list. Tāpēc VID search nevar iterēt pa `name_forms` — jāstrādā tikai ar `name` lauku.

Algoritms:

1. Split `tracked_politicians.name` pa whitespace.
2. Pēdējais token = `surname`. Pirmie N-1 tokens = `given_name` (joined ar single space). Hyphenated uzvārdi paliek monolīti (piem. `("Agita", "Zariņa-Stūre")`).
3. Edge case overrides — manuāli kuratori politiķi ar dubultnosacījuma uzvārdu, kur naïve split ir nepareizs:
   - `"Hosams Abu Meri"` — naïve dod `("Hosams Abu", "Meri")`, pareizi ir `("Hosams", "Abu Meri")`.
   - Aizsardzība: `src/vad/declarations.py` glabā `_NAME_OVERRIDES: dict[int, tuple[str, str]]` ar pid-keyed manuāliem split'iem. Phase 0 — pid 95 (Hosams Abu Meri) ir vienīgais zināmais case; verificēt sweep'a logos, vai citi politiķi atgriež 0 rezultātus, un pievienot līdz nepieciešamībai.
4. Diakritiku fallback — VID portāls saglabā diakritikus (testēts ar Šleseru — atgrieza ar pilnām diakritikām). Bet ja a) pirmais search ar diakritikām atgriež tukšu, **un** b) politiķis ir aktīvs amatpersona (≥1 saeima_individual_votes vai role nepatukšs), pamēģinām ASCII formu (`unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')`). Log warn par fallback'u (jāseko, vai VID kaut ko ir mainījis).
5. Hyphenated uzvārdu testēšana — DB ir 5 hyphenated examples (Kalniņa-Lukaševica, Marčenko-Jodko, Skujiņa-Rubene, Zariņa-Stūre, Lībiņa-Egnere). Phase 0 implementācijā jāverificē, ka VID portāls pieņem `Surname=Zariņa-Stūre` ar defisi (manuāls test pirms batch sweep).

Homonīmu identifikācija (5 pāri DB pēc identiska uzvārda — Šlesers Ainārs/Ričards, Judins Andrejs/Igors, Kļaviņa Jeļena/Līga, Kalniņa Inese/Irma, Zariņš Jānis/Viesturs) **nerada problēmu search-time**, jo mēs vienmēr passa abus First+Last → VID atgriež viens-uz-vienu match. Risks ir tikai pie tiesiska match (skat. § 6.2) — jāverificē institūcija/amats katrai atgrieztai rindai.

### 6.2 Multi-row disambiguation

Šlesers atgrieza 6 rindas par dažādām lomām (Saeimas deputāts, ministrs utt.). Visas pieder vienam un tam pašam politiķim — visus glabājam ar to pašu `opponent_id`. UNIQUE constraint `(opponent_id, vad_uuid)` aizsargā pret dublikātiem.

**Riska scenārijs**: politiķim ir vārda-saimnieks (cita persona ar tādu pašu Vārds+Uzvārds, piem. divi "Jānis Kalniņš"). VID portāls atgriezīs rindas par abiem. Mēs glabāsim **abas** zem mūsu `opponent_id`, kas ir kļūda.

**Aizsardzība**: pirms ierakstam saglabājam, salīdzinām VID-row institūciju + amatu pret mūsu zināmo politiķa kontekstu. Match-rule (vismaz **viens** no):
- Institūcija no VID-row (`Latvijas Republikas Saeima`, `Valsts kanceleja`, ministrijas, pašvaldības) sniedz substring match ar tracked politiķa **vēsturisko vai aktuālo** kontekstu — to iegūstam no `tracked_politicians.role` (case-insensitive substring) VAI no `name_forms` JSON `keywords` lauka (kuratoriem var pievienot `"saeima"`, `"ministrija"` palīginstrumentus).
- VAI VID-row `position_title` (`"Saeimas deputāts"`, `"Ministrs"`, `"Mērs"`) substring-matchojas pret mūsu politiķa `role`.
- Vēsturiskie ieraksti (>5 gadu veci) iziet match check ar relax'ētu politiku — politiķi, kas Saeimā nokļuva 2022, kā Rīgas vicemērs 2009, joprojām ir mūsu primāri tracked politiķis.

Ja neviens row no rezultāta nematch'o → log warn `[vad-match-fail] {pol.name}: ?? rows, no role match` un **skip** bez ieraksta. Manuāla resolution caur `name_forms` papildināšanu vai `negative_patterns` izmantošanu (skat. memory `project_matcher_role_integrity`).

### 6.3 Politiķi bez deklarācijām

Žurnālisti, analītiķi, pensionāri (retorika - bez amatpersonas statusa), `relationship_type IN ('journalist','neutral','organization','inactive')` → **skip**. CLI default `--politician all` filtrē `relationship_type='tracked'` un `relationship_type IS NULL` (legacy default). Žurnālisti var deklarēt VAD dažās retās kombinācijās (piem. ja ir koeficiētas amatu kombinācijas), bet tas nav mūsu primary kontekstā.

---

## 7. Idempotence

**UNIQUE atslēga = dabīgais identifikators** (atjaunots pēc F11 atklājuma 2026-05-02): `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)`. `vad_uuid` NEDODAS izmantot — tas rotē per-call (skat. § 15 F11), tāpēc katra ingest palaišana saņem jaunu UUID tai pašai deklarācijai.

**Idempotence plūsma katrai politiķim sweep'ā:**

1. Search → atgriež N declaration rindas (katra ar svaigu, sessijas-bound `vad_uuid`, parsed `declaration_kind`, `declaration_year`, `submitted_at`, `position_title` no search response label + indented context).
2. Pirms detail fetch — pārbauda DB: `SELECT id FROM vad_declarations WHERE opponent_id=? AND declaration_kind=? AND declaration_year=? AND submitted_at=? AND position_title=?`. Ja ROW jau pastāv → SKIP detail fetch (saglabā VID throttle, ne-pārkrāj HTML); UPDATE rindu ar svaigu `vad_uuid` (audit), bet sekciju datus neaiztiek.
3. Ja ROW nepastāv → fetch detail HTML → parse → INSERT vad_declarations + visi 10 sekciju INSERTs vienā transakcijā.

**Revisions handling:** ja VID publicē revidētu versiju, `submitted_at` reti mainās (parasti deklarācija revidēta ar to pašu submitted_at, jaunu published_at). Pa to dabīgais identifikators ne-atklās revision. Phase 0.5 backlog: pievienot `content_hash` (sha256 no parser-normalized JSON) kā opcionālu kolonnu; ja hash atšķiras pie sekundārās ingest, `DELETE FROM vad_<sec> WHERE declaration_id=?` un re-insert. Phase 0+1 prioritāte: dabīgā atslēga; revision detection ir later refinement.

**SQL idempotence semantika ar NULL gadiem:** SQLite UNIQUE NULL semantika treats two `NULL` as **distinct**. Tas nozīmē: divas start-deklarācijas ar `declaration_year=NULL` un dažādiem `submitted_at` būs unikalitāte automātiski. Bet ja kādreiz ir TWO start-deklarācijas ar SAME submitted_at (teorētiski kļūda), tās tiks treated kā unikalitāte (kļūdaini saglabās abas). Aizsardzība: parser obligāts izsaukt `submitted_at NOT NULL` priekš ne-annual deklarācijām (raise ValueError ja nav header'ā).

---

## 8. CLI un manuālā rutīna

```bash
# Pilna sweep visiem tracked politiķiem
PYTHONIOENCODING=utf-8 python scripts/ingest_vad_declarations.py

# Single politiķis, single gads (debug)
python scripts/ingest_vad_declarations.py --politician slesers-ainars --year 2024

# Dry-run (parsēšana, bet nav DB write)
python scripts/ingest_vad_declarations.py --dry-run

# Ierobežo līdz N politiķiem
python scripts/ingest_vad_declarations.py --limit 5

# Tikai politiķi ar aktivitāti pēdējās 90 dienās (peak-aprīlis-maijs ingest)
python scripts/ingest_vad_declarations.py --max-age-days 90
```

Iet uz `wiki/log-ingest/<gads-mēnesis>.md` ar formātu:

```
- VID amatpersonu deklarācijas (manuāls, mēneša cikls)
  - Politiķi sweep'ēti: 152
  - Jaunas deklarācijas: 12 (par 2024. gadu, +1 sākuma deklarācija)
  - Bez izmaiņām: 140
  - Skip ar role-match fail: 0
  - Kopā API requests: 152 (search) + 12 (detail) = 164
```

**Rutīnas vieta**: `wiki/operations/operacijas.md` § "Latvijas Vēstnesis (manuāla plūsma)" parāda paterns. Pievienosim § "VID amatpersonu deklarācijas (manuāla, mēneša cikls)" ar atsauci uz `wiki/operations/vad-declarations.md`. **NAV** daļa no `daily-routine.md` — palaiž operators reizi mēnesī (ieteicams 1. mēneša piektdiena), peak periodā (aprīlis-maijs) reizi nedēļā.

---

## 9. Render plūsma (Phase 1)

### 9.1 Datu plūsma

`src/render/vad.py` jauns modulis — eksportē `fetch_vad_data_for_politicians(db, pids: set[int]) -> dict[int, PoliticianVadData]`. PoliticianVadData satur sakārtotus deklarāciju ierakstus pa gadiem, ar pre-computed delta marķieriem.

```python
# src/render/vad.py public API
@dataclass
class VadDeclarationView:
    declaration_id: int
    year: int
    kind: str  # "annual", "start", ...
    institution: str
    position_title: str
    submitted_at: str
    published_at: str
    sections: dict[str, list[VadRowView]]  # "positions", "real_estate", ...

@dataclass
class VadRowView:
    payload: dict  # raw row dict
    delta: Literal["new", "removed", "unchanged", "modified"]
    diff_text: Optional[str]  # cilvēkam-lasāms diff: "summa: 76351 → 250000 (+228%)"

def fetch_vad_data_for_politicians(db, pids: set[int]) -> dict[int, list[VadDeclarationView]]:
    """Atgriež sortēts list per pid, jaunākā gada deklarācija pirmā.

    Iepriekšējā gada deklarācija sortēta nākamā un tiek izmantota delta aprēķinam
    JAUNĀKAJAI deklarācijai. Vecākām deklarācijām delta = NULL.
    """
```

### 9.2 Delta logika (`src/vad/diff.py`)

Identitātes hashing per sekcija:

| Sekcija | Identity key |
|---|---|
| positions | `(position_title, entity_reg_number or entity_name)` |
| real_estate | `(property_type, location, ownership_status)` |
| companies | `(reg_number or company_name, capital_kind)` |
| vehicles | `(brand, year_made, ownership_status)` |
| savings | `(savings_kind, currency, holder_reg_number or '_cash_')` — viens uzkrājums per kind+holder+currency |
| income | `(source, income_type, currency)` — gads ir implicit no deklarācijas |
| transactions | `(transaction_description, currency)` |
| debts | `(creditor_reg_number or creditor_name, currency)` |
| loans_given | `(currency, amount_in_words)` |
| family | `(full_name)` |

Delta types:
- **new**: identity-key nav iepriekšējā gadā
- **removed**: identity-key bija iepriekšējā gadā, šogad nav (renderē atsevišķā "Aizgāja" sekcijā ar tildi/strikethrough)
- **modified**: identity-key matched, bet kāds skaitlisks lauks (`amount`, `units`, `total_value`) atšķiras > 5%
- **unchanged**: identity-key matched un visi lauki atšķiras < 5%

`diff_text` cilvēkam-lasāms (LV):
- "summa: 76351 → 250000 (+228%)" income līnijai
- "kapitāldaļas: 500 → 1000 (+100%), vērtība 5000→10000" company līnijai
- "kategorija: lietošanā → īpašumā" real_estate ownership maiņai

Daudzgadīgs delta ne-viss vienkāršs (pārvaldnieka maiņas, sadalīšanas) — Phase 1 limit'ojams uz **divu blakusgadu delta**. Pilns timeline (3+ gadi) parādās kā statiska tabula bez delta marķieriem. Phase 2 var ieviest historizētas izmaiņas.

### 9.3 Tab integrācija

`src/profile_kind.py` paplašinājums — `_profile_tab_set()` add `'deklaracijas'` ja:
- `kind in {'deputy', 'minister', 'mep', 'regional', 'former', 'politician'}` (visi, kuriem ir VAD amatpersonu obligation pēc Likuma "Par interešu konflikta novēršanu valsts amatpersonu darbībā" 4. panta).
- **Skaidri izslēgti**: `journalist`, `analyst`, `inactive` (nav amatpersonas). `organization` — institucionāli pārstāvji, kas paši nedeklarē, izslēgti.
- AND `has_vad_data` (vismaz 1 deklarācija stored). Konditionāls tāpat kā `pretrunas` un `saites` — implementēts ar `_fetch_politicians()` `vad_count` aprēķinu (one-shot SELECT opponent_id, COUNT(*) FROM vad_declarations GROUP BY opponent_id, lookup-ā per pid).

`templates/politician.html.j2` jauns blok pēc `<!-- Saites tab -->`:

```jinja
<!-- Deklarācijas tab -->
{% if 'deklaracijas' in tab_set %}
<div class="profile-tab" id="tab-deklaracijas" style="display:none;">
  {% include "_vad_panel.html.j2" %}
</div>
{% endif %}
```

`templates/_vad_panel.html.j2` (jauns, ~150 LOC ar visu) — gada selector (chips ar pēdējiem 5 gadiem), sekciju akkordeoni, delta markeri (`<span class="vad-delta vad-delta-new">jauns</span>`, `vad-delta-modified`, `vad-delta-removed`). CSS `assets/style.css` add `.vad-delta-{new,modified,removed,unchanged}` ar zaļā/dzeltenā/sarkanā/bāla krāsu paleti (saskan ar timeline event krāsām).

Stat-button rindā `profile-stats-bar`:

```jinja
{% if 'deklaracijas' in tab_set %}
<button class="profile-stat" onclick="showProfileTab('deklaracijas', this)" data-tab="deklaracijas">
  <span class="profile-stat-value">{{ vad_data|length }}</span>
  <span class="profile-stat-label">Deklarācijas</span>
</button>
{% endif %}
```

### 9.4 Avota saites politika

Kā minēts § 4.1 — VID portāls neatļauj cookieless deep-links. Tab footers raksta:

> Avots: [VID Valsts amatpersonu deklarāciju portāls](https://www6.vid.gov.lv/VAD?Name=Ainārs&Surname=Šlesers) (atver search ar šo politiķi; izvēlies konkrēto deklarāciju no saraksta)
>
> Pēdējā automātiskā ielāde: 2026-05-02 13:59

Search-link ar `?Name=...&Surname=...` ir VID portāla GET-pieņemts (testējams, bet jāverificē Phase 0 implementācijā — ja portāls ignorē GET prefill, atstāt vienkāršu `https://www6.vid.gov.lv/VAD` saiti).

### 9.5 Privātums un ģimene

VAD portāls atklāj politiķa ģimenes locekļu pilnos vārdus. Tas ir publisks per **likuma "Par interešu konflikta novēršanu valsts amatpersonu darbībā" 25. pants** — bet etiska politika atmina.lv var būt ierobežotāka.

**Phase 1 default**: ģimenes sekcija renderēta zem **collapsed `<details>`** ar virsrakstu "Ģimene (publiska VID portālā — atvērt rādīšanai)". Šis nav UX gimmick — tas ir signāls lasītājam, ka mēs apzināmies sensitivitāti, vienlaicīgi nepaslēpjot publisku informāciju. Operators var izlemt mainīt politiku Phase 2 (paslēpt pilnībā) vai paplašināt (default open) atkarībā no atsauksmēm.

Citas sekcijas (visas kapitāldaļas, NĪ, ienākumi) — default open. Tās ir "kāpēc politiķis publiski ievēlējās" — pilnais publicēšanas intents.

---

## 10. Juridiskais

- **Primārais juridiskais avots**: likuma "Par interešu konflikta novēršanu valsts amatpersonu darbībā" 24. un 25. panti (publicēšanas pienākums un publiskais raksturs). VID portāls ir oficiālais publicēšanas kanāls.
- **Mūsu lietojums**: re-publishing strukturētā formā ar kontekstu (year-over-year diff, šobrīd Phase 0+1; Phase 3 cross-link ar balsojumiem). Tas ir transformatīvs, ne literāls portāla mirror — atbilst publiska intereses pamatojumam.
- **Nav personas datu aizsardzības problēma** šajā scope, jo a) viss VID publiski; b) tracked politiķi ir publiskas amatpersonas, c) ģimenes locekļiem mēs piedāvājam collapse-by-default UI gestu (skat. § 9.5).
- **`sources` tabulā** pievienojam rindu ar `tier=1`, `legal_status='approved'`, `legal_notes` atsauce uz konkrētiem panti, `last_tos_review='2026-05-02'`. Vēstnesis paterns.
- **NAV terms-of-service violation pārkāpumam** — `https://www6.vid.gov.lv/robots.txt` jāverificē Phase 0 implementācijā (ja `Disallow: /VAD`, tad apsverot palēnināt vai atteikties). Manuāla pārbaude tika veikta 2026-05-02 spike laikā: portāls neatklāj robots.txt restrictions specifiski VAD ceļam (jāverificē atkārtoti pirms ship).
- **Rate-limit ētika**: 10s+3s pause = ~28-48 min per pilna sweep (atjaunots pēc F12 — VID throttle agresīvāks nekā gaidīts), uzbrukums VID portālam = nulle.

---

## 11. Testēšana

### 11.1 Unit testi

`tests/test_vad_parsing.py`:
- `test_parse_modern_declaration_full()` — iet cauri Šlesers 2024 fixture, asertē 11 sekciju row count'us un kritisko lauku vērtības (Saeima alga 76351.23, AVADEL kapitāldaļas 1000 utt.).
- `test_parse_empty_sections()` — politiķis ar tikai header un 1-2 sekcijām (Phase 0 implementācijā izvēlas konkrētu kandidātu — meklē tracked politiķi ar minimālām deklarētajām aktīvām, piem. jaundeputātu ar darba sākuma deklarāciju).
- `test_parse_currency_validation()` — dažādas valūtas (EUR/USD/RUB).
- `test_parse_h2_section_numbering()` — robust regex, nereaģē uz paslēpiem `<h2>` līmeņos.
- `test_parse_multi_table_sec_6()` — cash-only, bank-only, cash+bank kombinācijas.

`tests/test_vad_diff.py`:
- `test_diff_new_company()` — 2023 nav AVADEL, 2024 ir → delta='new'.
- `test_diff_income_increase()` — 2023 alga 50000, 2024 alga 76000 → delta='modified', diff_text="alga: 50000 → 76000 (+52%)".
- `test_diff_removed_property()` — 2023 ir Jūrmalas dzīvoklis, 2024 nav.
- `test_diff_unchanged_under_5pct()` — alga 76000 → 76200 → delta='unchanged' (under threshold).

`tests/test_vad_matching.py`:
- `test_split_name_simple()` — "Ainārs Šlesers" → ("Ainārs", "Šlesers").
- `test_split_name_hyphenated_surname()` — "Agita Zariņa-Stūre" → ("Agita", "Zariņa-Stūre").
- `test_split_name_three_token()` — "Dāvis Mārtiņš Daugavietis" → ("Dāvis Mārtiņš", "Daugavietis").
- `test_role_match_disambiguation()` — duplikāts vārdā, viens row matchojas ar role keywords, otrs nē → tikai pirmais glabājas.

### 11.2 Integration testi

`tests/test_vad_integration.py`:
- `test_full_pipeline_dry_run()` — mock vid_search un vid_fetch_detail ar fixture HTML, palaiž `fetch_for_politician()`, asertē 11 tabulu populāciju in-memory DB.
- `test_idempotence_double_run()` — palaidam `fetch_for_politician()` 2x, asertē UNIQUE constraint nelaiž dubultus + section rows nepieaug.
- `test_render_smoke()` — `render_politician_page(slesers_pid)` dod HTML ar `id="tab-deklaracijas"` un visiem 11 sekciju headers.

### 11.3 Smoke testi

`scripts/check.sh` jau palaiž `generate_public_site()` smoke. Pievienosim:
- `python -c "from src.vad.schema import init_vad_tables; init_vad_tables()"` — ja DDL ir broken, pirms generate.

---

## 12. Implementācijas darba sadalījums

Sadalījums uz commit-able vienībām (writing-plans skill ieviesīs kā numurētas Tasks):

**Phase 0 — Ingest** (1 PR vai sērija):
1. `src/vad/schema.py` + `init_vad_tables()` + `tests/test_vad_schema.py` (DDL + smoke).
2. `src/vad/parsing.py` + 5 fixtures + `tests/test_vad_parsing.py`.
3. `src/vad/fetch.py` (httpx session, ReqCode pre-flight, search, detail-by-cookie, throttling) + `tests/test_vad_fetch.py` (mock httpx).
4. `src/vad/declarations.py` (orchestrator: name-split → search → role-disambiguation → fetch detail → parse → store) + `tests/test_vad_matching.py`, `tests/test_vad_integration.py`.
5. `src/vad/__init__.py` (public API: `fetch_for_politician`, `init_vad_tables`).
6. `scripts/ingest_vad_declarations.py` CLI.
7. `wiki/operations/vad-declarations.md` runbook.
8. `wiki/CHANGELOG.md` § "VAD declarations tracker (Phase 0)".

**Phase 1 — Render** (otra PR vai sērija):
9. `src/vad/diff.py` + `tests/test_vad_diff.py`.
10. `src/render/vad.py` orchestrator.
11. `templates/_vad_panel.html.j2` partial.
12. `templates/politician.html.j2` paplašinājums + `assets/style.css` `.vad-delta-*` + `.vad-section`.
13. `src/profile_kind.py` `_profile_tab_set()` extension + `src/render/politicians.py` `_fetch_politicians()` `vad_count` lauka pievienošana.
14. Smoke uz 5 sample profiliem (Šlesers, Siliņa, Pupols, Hermanis, Bartaševičs) — manual visual review.
15. `wiki/CHANGELOG.md` § "VAD declarations Phase 1 — UI tab".
16. Initial sweep palaišana (operatora rokas) + log entry.

---

## 13. Atklātie jautājumi (gaida Phase 0 implementāciju)

- **Q1**: Vai `https://www6.vid.gov.lv/VAD?Name=X&Surname=Y` GET respektē query string un atver pre-filled search? Jāverificē empīriski Phase 0 § 9.4 implementācijā. Ja nē, fallback uz vienkāršu portāla saiti.
- **Q2**: Vai `From=` parameter veic paginate'i, ja politiķim > 50 deklarācijas? Šlesers ar 6 amatu rindām atgrieza visu vienā response (POST atgriezās ar 6 rindām un nav `next`-tipa marker). Senatori vai daudz-amatu kandidāti var izmest šo limit. **Phase 0 implementē bounded loop**: `From=0`, `From=N` (kur N = response row count), atkārto līdz tukšam response vai max 200 rindas safety bound (loud log warn pie >100). Pagination signal = response row count == fixed page size (varbūt 50, jāverificē).
- **Q3**: Robots.txt VID portāla reālā politika — verificēt manuāli 2026-05-02 ingest skriptu pirmajā palaidienā.
- **Q4**: Pre-2010 (legacy `/VAD/VAD2002Data`) — vai vispār ietveram tracked politiķiem? Šleseram ir 2000-2009 ieraksti; tās ir 25 gadu vecas. **Phase 0+1 lēmums**: skip ar log warn. Phase 0.5 backlog.
- **Q5**: Storage cleanup `raw_html` — implementācijai Phase 0.5. Phase 0 saglabā visu (~50 MB max).
- **Q6**: Vai `/finanses.html` (KNAB partiju ziedojumi) lapai pievienot saiti uz "atsevišķi politiķu deklarācijas — skat. politiķa profilā"? Mazs cross-nav krūziņš UX bonus, bet nav obligāts Phase 1 ship'am.

---

## 14. Pēc Phase 0+1 — kā mērīt veiksmi

- **Coverage**: ≥90% no 152 tracked politiķiem ar ≥1 stored deklarāciju. Atskaitot ne-amatpersonas (žurnālisti, analītiķi), expected ≥130/152.
- **Diff signal-to-noise**: vismaz 80% no `delta='modified'` rindām cilvēkam-lasāmā review'ā ir reāls semantisks delta (ne vienkārši formatting drift).
- **Ingest reliability**: 0 failed sweeps mēneša cikla rutīnā pirmajos 3 mēnešos.
- **Render performance**: Phase 1 tab pielikums nepalielina `generate_public_site()` time > 10% (current ~30s; budget +3s).

---

> **Spec self-review (inline)**: nav placeholder'u; sekciju numerācija saskan; scope ir Phase 0+1 only ar Phase 2-4 backlogged § 2; storage = A approach; visi DDL kolonni ar tipu; visi atklātie jautājumi (Q1-Q6) ir empīriski verificējami implementācijas ietvaros, ne open-ended dizaina lūgumi.

---

## 15. Audit trail — spec review pārstrādes (2026-05-02)

Pēc lietotāja pieprasījuma "ultrathink vai viss ir pareizi, vai nav flaws un vai pārbaudīsim aprēķinus" (Telegram msg 1545) veikta empīriska verifikācija pār DB un kodu. Atklātās problēmas un to fixes:

| # | Problēma | Sekcija | Fix |
|---|---|---|---|
| F1 | `name_forms` apgalvots kā "alternative full names list", reāli ir deklinētu uzvārdu list (`['Šlesers', 'Šlesera', 'Šleseram']`). Sākotnējais § 6.1 algoritms iterētu nepareizus tokenus. | § 6.1 | Pārstrādāts uz `name`-driven split + manuālu `_NAME_OVERRIDES` ar pid-key + `unicodedata.normalize` ASCII fallback. |
| F2 | `source_url` definīcija pretrunīga: § 4.1 "synthetic `?id=<UUID>`" vs § 9.4 "search-link `?Name=...&Surname=...`". | § 4.1, § 9.4 | Vienots uz search-link formu (verificējams ar GET; UUID glabājas atsevišķi `vad_uuid` laukā). |
| F3 | Throttle matemātika kļūdaina: aprakstīts "~12 min pilns sweep", reāli initial backfill ir ~35 min, mēneša cikls ~16 min. | § 3.4 | Detalizēta apjoma matemātika 3 scenārijiem (initial / steady-state / peak). |
| F4 | `vad_companies.units INTEGER` — nesaderīgs ar fractional fund certificate units. | § 4.2 | Pārveidots uz `REAL`. |
| F5 | `vad_income` trūka `is_individual` flag; "Inese Šlesere, ," income rows (fiziska persona, empty reg) iestiprinātos kā juridiskas. | § 4.2 | Pievienots `is_individual` + `source_reg_number` kolonnas. |
| F6 | Edge case "Hosams Abu Meri" naïve 3-token split ir nepareizs (Abu Meri ir uzvārds, ne Meri). | § 6.1 | Pievienots `_NAME_OVERRIDES` mehānisms. |
| F7 | `init_vad_tables()` boot-vieta nepilna (atsauce uz nepastāvošu `ensure_db_initialized`). | § 4.5 | Saskaņā ar saeima_bills precedentu (`init_saeima_tables` = lazy, render guard ar try/except), specificēti 3 aktivācijas vietas. |
| F8 | § 9.3 / § 2 inconsistency par `organization` profile_kind iekļaušanu deklaracijas tab_set. | § 2, § 9.3 | Skaidri izslēgts (institucionāli pārstāvji nedeklarē kā amatpersonas) ar likuma atsauci. |
| F9 | Parser sample plašums = 1 politiķis (Šlesers) — risks, ka cita HTML strukturas drift'os. | § 5 | Pievienots obligāts ≥5 politiķu HTML sample apskate pirms parser commit; bootstrap helper `scripts/dump_vad_fixture.py`. |
| F10 | `From=` paginate handling neskaidrs ("noticing", bet ne loop). | § 13 Q2 | Specificēts bounded loop ar 200-row safety. |

Empīriski verificētais (no DB un kodu apskates):

- ✅ `get_db()` jau iestata `PRAGMA foreign_keys = ON` (`src/db.py:209`) — CASCADE strādā.
- ✅ Journal mode ir WAL.
- ✅ DB ir 5 hyphenated uzvārdi un 5 homonīmu pāri (Šlesers, Judins, Kļaviņa, Kalniņa, Zariņš) — risk apzinats, bet drošs jo search vienmēr passa abus First+Last.
- ✅ DB ir 3 multi-token vārdi: Selma Teodora Levrence, Dāvis Mārtiņš Daugavietis, Hosams Abu Meri — pirmie divi ir naïve-OK, trešais ir override case.
- ✅ Saeimas precedent (`init_saeima_tables` lazy + render guard) atklāts un dokumentēts.

Vēl atklāti jautājumi (nav fix'i, bet zināmas implementācijas pārbaudes):

- Q5 (jauns): Vai VID portāls pieņem `Surname=Zariņa-Stūre` ar defisi? Manuāla pirms-batch verifikācija Phase 0.
- Q6 (jauns): Vai ASCII fallback `unicodedata.normalize` ir nepieciešams? Šlesera test rādīja, ka diakritika strādā — fallback ir tikai aizsardzība pret VID staff datu typing inkonsekvenci. Phase 0 implementācija pārbauda log warn skaitu — ja 0, var noņemt.

---

## 15.1 Audit trail — Phase 0 implementation findings (2026-05-02 vēlās dienas)

Implementācijas T1-T2 spike laikā empīriski atklāti vēl divi kritiski fakti, kas izmaina spec contract:

| # | Atklājums | Sekcija | Fix |
|---|---|---|---|
| F11 | **VID `vad_uuid` rotē per-call**, ne tikai per-session. Empīriski tests: viena httpx sessija, divi search calls 30s starpā par "Ainārs Šlesers" → atgrieza 2 dažādas UUID tai pašai 2024. gada deklarācijai (`3896a5d6-...` vs `5d8cf3a0-...`); abi response 5554 bytes ar identiskiem 17 type=2 saitēm. UUID = anti-scrape session-bound nonce, NE stable identifier. Sākotnēji spec § 4.1 piedāvāja `UNIQUE(opponent_id, vad_uuid)` idempotencei — sabrūk: katra ingest palaišana radītu dublētas rindas. | § 4.1, § 7 | UNIQUE pārveidots uz dabīgo atslēgu `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)`. `vad_uuid` kļūst nullable session-bound audit lauks. Idempotence plūsma § 7: pre-fetch DB lookup pa dabīgo atslēgu → skip detail fetch ja jau eksistē. |
| F12 | **VID throttle agresīvāks nekā gaidīts.** Empīriski tests: divi sub-second back-to-back search calls vienā httpx sessijā (bez sleep) → `httpx.ReadTimeout` uz otrā. Ar 30s sleep starpā — abi succeed. Sākotnējais 5s search throttle var nepietikt. | § 3.4, § 10 | Throttle 5s → **10s** starp politiķiem (search calls). Apjēga matemātika: initial backfill ~48 min (no ~35 min), mēneša cikls ~28 min (no ~16 min). Joprojām pieņemams. |

**Saistītie spec atslēgvārdi atjaunoti:**
- `vad_uuid` līnija § 4.1 — nullable, ar komentāru "session-bound nonce; rotē per-call"
- UNIQUE constraint § 4.1 — dabīgā atslēga
- § 7 idempotence — pārstrādāts pilnais
- § 3.4 throttle politika — 10s+3s ar tabulu trim scenārijiem
- § 10 rate-limit ētika — atjaunoti minūšu skaitļi

**T1 implementation impact:** Phase 0 T1 commit `dd383cd` + fix `ed46424` ielikti DDL ar veco UNIQUE. Pēc F11 atklājuma palaists otrais fix commit (skat. T1 vad-deklaracijas branch). Visi nākamie tasks (T6 orchestrator īpaši) izmanto jauno idempotence kontraktu.

---

## 15.2 Audit trail — Phase 1 production smoke + full sweep findings (2026-05-02 vakars)

Pēc 24-commit merge uz master (`8744277`) palaists production smoke (5 sample politiķi) + full 152-politiķu sweep (215 min). Atklātie issues:

| # | Atklājums | Sekcija | Risinājums |
|---|---|---|---|
| Fpost1 | `role_matches` per-row keyword overlap dod false-negatives ar realistic DB role variation: Šlesera "LPV priekšsēdētājs" (partijas amats), Kleinberga "Rīgas mērs" ≠ VID "Valstspilsētas domes priekšsēdētājs" (sinonīmu paši label), Pūpola "EP deputāts" ≠ VID Rīgas dome (vēsturiskie amati). | § 6.2, § 7 | Pārveidots uz `return True` ar full rationale docstring (commit `986ece4`). Trust full Vārds+Uzvārds search uniqueness; per-row check re-introducē, ja kādreiz novērojam VID atgrieztus multiple distinct persons one search'ā. |
| **F13** | **Homonīmu kontaminācija beyond first-name.** Sākotnējais argument bija "DB ir 5 homonīmu pāri ar dažādiem PIRMAJIEM vārdiem". Production sweep atklāja, ka pat pilns Vārds+Uzvārds nav unikāls Latvijā: VID search "Andris Bērziņš" → 228 dekl (mix vairāku Andris Bērziņš), "Inese Kalniņa" 205, "Inga Bērziņa" 184, "Līga Kļaviņa" 137, "Dace Melbārde" 72. Mēs ielādējām visu zem viena pid → dati publiski sajaukti. Reputational risk pirms deploy. | § 4.1, § 6.2 | **Phase 1.5 prioritāte** — manuāla disambiguation: a) negative_patterns ar disambiguator (institūcija substring vai amata gads), b) DELETE + targeted re-ingest ar 3rd query parameter, vai c) hide kontaminētos no UI līdz Phase 1.5 fix. |
| **F14** | **Parse-fail uz daudziem UUIDs**: 1304 vad-fetch-fail "nav header table" sweep laikā. Iespējams VID anti-scrape mechanism — pēc N rapid sequential requests dažas UUID nonces tiek invalidated un detail returnē redirect/error page bez `<table>`. Sweep tāpat turpinājās per-UUID try/except, bet zaudētas potenciālas dekl. | § 3.4, § 7 | **Phase 1.5**: smart retry ar cookie refresh (visit /VAD again pēc 30s pauzes ja parse fails), backoff exponentiāls. Pēc Phase 1.5 re-run sweep — natural-key idempotence skip jau ielādētos. |
| F15 | `tee` redirect uz nepastāvošu `logs/` katalogu silent crash background process. Sweep nostrādāja ~15 min pirms tee mēģināja flush. | scripts/ | **Phase 1.5**: pievieno `mkdir -p logs/` skripta sākumā vai operatorinstrukcijā. Šobrīd workaround — palaiž bez `tee` (output uz background task file). |

**Sweep rezultāts (2026-05-02 19:30):** 143/152 tracked politiķi (94.1%) ar VAD datiem; 3376 deklarācijas; 9 politiķi bez datiem (8 nav amatpersonas + 1 Hosams Abu Meri name override gaida).

**Phase 1.5 explicit backlog (jaunā sesijā):**
1. Homonīmu cleanup — DELETE FROM vad_declarations WHERE opponent_id IN (kontaminētie pids); pievienot disambiguation funkciju `src/vad/declarations.py:_disambiguate_search_rows()` kas filtrē pa institūciju vai amata gads; targeted re-ingest.
2. Parse-fail retry — `VadClient.fetch_detail` paplašināt ar retry-on-no-header (max 2 attempts ar 30s + cookie refresh); log warn ja pēc retry joprojām fail.
3. `_NAME_OVERRIDES` papildināt ar pid 161 (Hosams Abu Meri → "Hosams", "Abu Meri").
4. `scripts/ingest_vad_declarations.py` paplašināt ar `--logs` flag, kas auto-create `logs/` directory.
5. Re-render + check.sh + deploy preview.
