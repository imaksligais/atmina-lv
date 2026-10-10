# Saeima Bills Tracker — Dizaina specifikācija

**Datums**: 2026-04-22
**Izcelsmes konteksts**: 2026-04-23. Saeimas sēdes agenda (`titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&nr=c4679c5e-cc20-46e2-b7be-f1a9d152459c`) — darba kārtība bez balsojumiem, ar likumprojektiem daudzos lasījumu statusos, deputātu pieprasījumiem, priekšlikumiem.
**Saistītie specs**: `2026-04-09-document-politicians-junction-design.md` (junction pattern), `2026-04-20-pretrunas-v2-design.md` (UI stila atsauce)
**CHANGELOG atsauce pēc ieviešanas**: `wiki/CHANGELOG.md § Saeima bills tracker`

---

## 1. Mērķis

Paplašināt `@saeima-tracker` aģentu no "tikai pabeigtu balsojumu" skrāpera uz pilnu **likumprojekta dzīves cikla sekotāju**. Datu modeļa līmenī — ieviest `saeima_bills` kā stabilu entītiju, kas apvieno likumprojekta dzīves ciklu (iesniegts → 1./2./3. lasījums → pieņemts/noraidīts) ar politiķu lomām (iesniedzējs, priekšlikuma autors, balsotājs) un publisko vides līniju.

UI līmenī — katram likumprojektam iegūst savu **detail lapu** `/likumprojekti/{document_nr}.html` ar kopsavilkumu, stadiju timeline un iesaistīto politiķu sarakstu. Publiskajā vietnē `/balsojumi.html` tabā iegūst trešo apakšcilni "Likumprojekti" ar filtrējamu grid.

Kvalitātes mērķis: kad politiķis publiski izsakās par likumu, atmina lietotājs var vienā klikšķī nokļūt uz konkrēto likumprojekta kartiņu un redzēt, kā šis politiķis (un viņa partija) reāli balsoja vai grozīja tekstu — pilns pretrunu detektors iegūst likumprojekta-saistītas pretrunas, ne tikai tēmas.

---

## 2. Scope

### Darām Phase 1 (MVP, droši ship-able)

- Jauna `saeima_bills` tabula + `saeima_bill_stages` tabula + `saeima_bill_politicians` junction.
- Jauna kolonna `saeima_votes.bill_id FK`.
- `@saeima-tracker` aģenta workflow paplašinājums: pirms balsojumu skrāpēšanas capture agenda → upsert bills → append stages → link iesniedzējus.
- **bill_type whitelist:** `{'Lp14', 'Lm14', 'P14'}`. Validēts pret `_VALID_BILL_TYPES` konstanti `src/saeima.py`. Nezināmi prefiksi (piem. nākotnes `/Lp15`) → log + skip ar warn, neraksta DB.
- Retro-backfill no 113 esošajām `saeima_votes` rindām (tikai tas, ko var atgūt no pieejamajiem datiem).
- UI: jauna apakšcilne `#bills-list` zem `/balsojumi.html` + detail template `templates/likumprojekts.html.j2`.
- Parsētāju helpers: `parse_agenda_snapshot()`, `match_submitters_to_politicians()`, `append_bill_stage()`.
- `wiki/operations/saeima-bills.md` runbook.

### Darām Phase 2 (atsevišķs darba paka pēc Phase 1 land)

- Priekšlikumu scrape (`webSasaiste?OpenView&restricttocategory={nr}` lapu parsēšana). Prasa spike, lai verificētu, vai priekšlikumu tabulas ir Playwright-snapshotable vai PDF-only.
- Deputātu pieprasījumu pipeline — ekstrakcija uz `claim_type='saeima_inquiry'` ar pielāgotu `@claim-extractor` prompt variantu.
- Atbilstošie readers updates 4 failos (`src/wiki.py`, `src/briefs.py`, `src/generate.py`, `src/contradictions.py`).

### Ārpus scope (abām fāzēm)

- **Debates / stenogrammas** — nav Phase 1 vai 2 daļa. Phase 3 specs definēs stenogrammu skrāpēšanu un per-utterance ekstrakciju. Phase 1 schema *jau* rezervē hook: `saeima_bill_stages.stage_kind='debate'` ļauj Phase 3 pievienot debate ierakstus tajā pašā timeline tabulā bez migrācijas. Phase 1 nedrīkst pievienot Lp14 nosaukumu vai motif-based debate detection, kamēr nav Phase 3 spec.
- **Komisijas slēdzieni** — atsevišķs scrape no citas `saeimalivs14.nsf` apakšsadaļas. Phase 3+.
- **Bill teksta strukturēts entītiju indekss** — pagaidām `summary` ir cilvēkam lasāma rinda. Strukturēts "kuri panti groza ko" ir Phase 3+.
- **`saeima_agenda_items` tabulas izmantošana** — esošā tukša tabula netiek aizstāta vai dzēsta. `saeima_bills` ir atšķirīgs entītijs (stable per-bill, ne per-session-slot). Agenda items var atdzīvoties nākotnē, ja rodas per-session slot analīzes vajadzība.
- **Politiķu profila timeline** — tabs "runāja-iesniedza-balsoja" laika josla uz personas lapas. Atsevišķs spec, pēc šī.

---

## 3. Datu modelis

### 3.1 Jaunas tabulas

```sql
CREATE TABLE IF NOT EXISTS saeima_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_nr TEXT UNIQUE NOT NULL,       -- "1315/Lp14", "952/Lm14"
    bill_type TEXT NOT NULL,                -- "Lp14" (likumprojekts) | "Lm14" (lēmuma projekts) | "P14" (paziņojums / rezolūcija / deputāta pieprasījums)
    title TEXT NOT NULL,                    -- "Grozījumi Valsts aizsardzības finansēšanas likumā"
    summary TEXT,                           -- 1-2 teikumi plain-language; no anotācijas vai pēdējā vote summary
    topic TEXT,                             -- kanonisks no src.topic_map.TOPIC_GROUPS
    base_law_slug TEXT,                     -- nullable, atbilst wiki/laws/*.md slug (e.g. "imigracijas-likums")
    institutional_submitter TEXT,           -- nullable, "Ministru kabinets" / "Saeimas Prezidijs" / komisijas nosaukums
    current_stage TEXT,                     -- denormalized no pēdējās saeima_bill_stages rindas
    current_status TEXT,                    -- "procesā" | "pieņemts" | "noraidīts" | "atsaukts"
    first_seen_at TIMESTAMP,                -- kad pirmoreiz parādījās agendā vai DB
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saeima_bill_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
    stage_name TEXT NOT NULL,               -- skat. vocabulary zemāk
    stage_result TEXT,                      -- "pieņemts" | "noraidīts" | NULL (procedurāls)
    stage_date TEXT,                        -- ISO YYYY-MM-DD
    vote_id INTEGER REFERENCES saeima_votes(id),     -- nullable; saiste uz konkrēto balsojumu
    session_id INTEGER REFERENCES saeima_sessions(id), -- nullable; sēde, kurā notika
    amendment_nr TEXT,                      -- nullable; "Nr.5" ja šī ir priekšlikuma stage
    stage_kind TEXT NOT NULL DEFAULT 'vote',  -- 'vote' (Phase 1) | 'debate' (Phase 3) | 'commission' (Phase 3+)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saeima_bill_politicians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
    politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    role TEXT NOT NULL,                     -- "submitter" | "amendment_author"
    amendment_nr TEXT,                      -- nullable; ja role='amendment_author', kura priekšlikuma
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bill_id, politician_id, role, amendment_nr)
);

CREATE INDEX IF NOT EXISTS idx_bills_document_nr ON saeima_bills(document_nr);
CREATE INDEX IF NOT EXISTS idx_bills_topic ON saeima_bills(topic);
CREATE INDEX IF NOT EXISTS idx_bills_status ON saeima_bills(current_status);
CREATE INDEX IF NOT EXISTS idx_bill_stages_bill_id ON saeima_bill_stages(bill_id);
CREATE INDEX IF NOT EXISTS idx_bill_stages_vote_id ON saeima_bill_stages(vote_id);
CREATE INDEX IF NOT EXISTS idx_bill_stages_kind ON saeima_bill_stages(stage_kind);
CREATE INDEX IF NOT EXISTS idx_bill_politicians_bill_id ON saeima_bill_politicians(bill_id);
CREATE INDEX IF NOT EXISTS idx_bill_politicians_politician_id ON saeima_bill_politicians(politician_id);
```

### 3.2 Izmaiņas esošajās tabulās

```sql
-- Migrācija 2026-04-22-001
ALTER TABLE saeima_votes ADD COLUMN bill_id INTEGER REFERENCES saeima_bills(id);
CREATE INDEX IF NOT EXISTS idx_saeima_votes_bill_id ON saeima_votes(bill_id);

-- Nekāda shēmas izmaiņa claims tabulā; tikai jauns claim_type string:
--   claims.claim_type IN ('position', 'saeima_vote', 'saeima_inquiry')
-- SQLite bez CHECK constraint; validācija notiek Python pusē (store_claim helper).
-- saeima_inquiry ievieš Phase 2, ne Phase 1.
```

### 3.3 Stage vocabulary (slēgts saraksts)

`stage_name` vērtības, Python helperī validētas:

| stage_name | Kad | stage_result | bill_type ierobežojums |
|---|---|---|---|
| `iesniegts` | Kad bill pirmoreiz parādās agendā | NULL | jebkurš |
| `1.lasījums` | 1. lasījuma konceptuālais balsojums | `pieņemts` / `noraidīts` | Lp14 |
| `2.lasījums` | 2. lasījuma gala balsojums (pēc visiem priekšlikumiem) | `pieņemts` / `noraidīts` | Lp14 |
| `2.lasījums priekšlikums` | Viens priekšlikuma balsojums 2. lasījumā. `amendment_nr` aizpildīts. | `pieņemts` / `noraidīts` | Lp14 |
| `3.lasījums` | Galīgais balsojums | `pieņemts` / `noraidīts` | Lp14 |
| `3.lasījums priekšlikums` | Priekšlikums 3. lasījumā. `amendment_nr` aizpildīts. | `pieņemts` / `noraidīts` | Lp14 |
| `atgriezts komisijā` | Balsojums par atgriešanu atpakaļ | `pieņemts` ja atgriezts | Lp14 |
| `atsaukts` | Iesniedzējs atsauc | NULL | jebkurš |
| `tiesneša_amats` | Lm14 balsojums par tiesneša iecelšanu, atbrīvošanu vai apstiprināšanu | `pieņemts` / `noraidīts` | Lm14 |
| `procesuāls` | Lm14 termiņa pagarinājums, līdzatbildīgās komisijas noteikšana, deputāta atsaukšana no komisijas | `pieņemts` / `noraidīts` | Lm14 |
| `Lm14 cits` | Citi Lm14 balsojumi (Air Baltic aizdevums, izmeklēšanas komisijas izveide, eksportētāju saraksts utml.) | `pieņemts` / `noraidīts` | Lm14 |
| `paziņojuma_balsojums` | P14 paziņojuma / rezolūcijas / deputāta pieprasījuma galīgais balsojums (Saeimas agenda lieto trīs apzīmējumus: `Paziņojums`, `Rezolūcija`, `Pieprasījums` — visi 14. Saeimas P14 dok. tipi) | `pieņemts` / `noraidīts` | P14 |
| `nezināms` | Backfill fallback motif, ko regex nevar klasificēt; atstājams līdz manuālai pārklasifikācijai | inherit no `saeima_votes.result` | jebkurš |

Vocabulary tiek kontrolēts caur `src.saeima._VALID_STAGE_NAMES` konstante + `_canonicalize_stage_name()` helper; `append_bill_stage()` noraidīs citas vērtības ar `ValueError`.

**Klasifikācijas regex (`_reading_from_motif`)**, ievērojot prioritāti:
1. `\d\.\s?lasījum` ar reading number → `{N}.lasījums` (priekšlikuma sufiksu pievieno, ja motif satur "priekšlikum")
2. `iecelšanu par.*tiesnesi` vai `apstiprināšanu par.*tiesnesi` vai `atbrīvošanu no tiesneša` → `tiesneša_amats`
3. `termiņa pagarināšanu` vai `komisijas noteikšanu` vai `atsaukšanu no.*komisijas` → `procesuāls`
4. `nodošana komisij` (Lp14 pirmā agenda parādīšanās — pirms 1. lasījuma) → `iesniegts`
5. `/P14` document_nr → `paziņojuma_balsojums`
6. `/Lm14` document_nr (citi) → `Lm14 cits`
7. Pārējie → `nezināms` (informatīvs warn ieraksts logā)

**Phase 3 hook:** `stage_kind` kolonna (`'vote' | 'debate' | 'commission'`) atļauj nākotnē Phase 3 ievietot debate utterances kā timeline rindas bez schema migrācijas. Phase 1 visi raksta `stage_kind='vote'` (default); `_VALID_STAGE_NAMES` validē tikai `kind='vote'` rindas. Phase 3 spec definēs atsevišķu `_VALID_DEBATE_STAGE_NAMES` un, iespējams, atsevišķu insert helperi `append_bill_debate()`.

### 3.4 Denormalizācijas diskusija

`saeima_bills.current_stage` un `current_status` ir denormalizēti no `saeima_bill_stages` pēdējās rindas. Tas paātrina grid renderēšanu (`/balsojumi.html#bills-list` vēlas viegli filtrēt "visi pieņemtie", "visi procesā"). Drošības mehānisms:

- **Atjaunina tikai `append_bill_stage()` helper.** Neviens cits ceļš nerakstīs šos laukus.
- `append_bill_stage()` atomāri ievieto stage rindu + atjaunina parent `current_stage/status/last_updated_at` tajā pašā transakcijā.
- Vienības tests verificē denormalizācijas sinhroniju (`tests/test_saeima_bills.py::test_current_stage_follows_latest_stage`).

Risks pie neatomiskuma: display rāda veco stadiju; nav datu bojājums. Tāpēc aceptējam denormalizāciju performanci deleguar fronts vietā.

---

## 4. Skrāpēšanas workflow

### 4.1 Esošā (pirms)

`@saeima-tracker` darbība tikai uz pabeigtām sēdēm:

1. Open session agenda → snapshot.
2. Grep vote URLs → navigate katram → snapshot.
3. Step 3.5: lasīt bill text → rakstīt summary → `UPDATE saeima_votes SET summary`.
4. Parse vote snapshots → `store_vote()` + `generate_claims_from_votes()`.

### 4.2 Jaunā (pēc)

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Open session agenda                                │
│  browser_navigate → snapshot → save agenda.md               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2 (JAUNS): Parse agenda to Bill entities              │
│  parse_agenda_snapshot(agenda.md) →                         │
│    list[AgendaBill] with:                                   │
│      document_nr, bill_type, title, iesniedzēji,            │
│      institutional_submitter, reading_hint, topic hints     │
│                                                             │
│  Arī izvelk:                                                │
│    - deputātu pieprasījumi → Phase 2 queue (JSON log)       │
│    - deputātu jautājumi → Phase 2 queue                     │
│    - tiesnešu iecelšana → atsevišķa rinda, bez bill entry   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3 (JAUNS): Upsert bills + link submitters             │
│  for agenda_bill in agenda_bills:                           │
│    bill_id = upsert_bill(document_nr, title, bill_type,     │
│                          institutional_submitter, topic)    │
│    match_submitters_to_politicians(agenda_bill.iesniedzēji) │
│    → store junction rows role='submitter'                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Capture vote snapshots (kā līdz šim)               │
│  grep vote URLs → navigate → snapshot → save                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5 (papildināts): Parse vote + link stage + link bill  │
│  for each vote_snapshot:                                    │
│    vote = parse_vote_snapshot(text)                         │
│    bill_id = resolve_bill_from_motif(vote.motif)            │
│    vote_id = store_vote(vote, bill_id=bill_id)              │
│    stage_name = _reading_from_motif(vote.motif)             │
│    append_bill_stage(bill_id, stage_name, vote.result,      │
│                      vote.date, vote_id, session_id)        │
│    generate_claims_from_votes(...)  # jau eksistē            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 6 (esošais Step 3.5, pārvietots): Enrich summary      │
│  ja bill.summary IS NULL un vote.summary iegūts:            │
│    bill.summary ← vote.summary (propagē uz bill)            │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Jaunas parsētāju funkcijas (`src/saeima.py`)

```python
@dataclass
class AgendaBill:
    document_nr: str                    # "1315/Lp14", "952/Lm14", "127/P14"
    bill_type: str                      # "Lp14" | "Lm14" | "P14"
    title: str                          # "Grozījumi Valsts aizsardzības..."
    individual_submitters: list[str]    # ["Maija Armaņeva", ...]
    institutional_submitter: Optional[str]  # "Ministru kabinets" | None
    reading_hint: Optional[str]         # no vote motif, ja pieejams
    vote_uuid: Optional[str]            # lai atrastu konkrēto balsojumu

def parse_agenda_snapshot(snapshot_text: str) -> list[AgendaBill]:
    """Izvelk visus Lp14/Lm14/P14 items no agenda snapshot.
    Regex pattern: 'Likumprojekts|Lēmuma projekts|Paziņojums' ... '(NNNN/(?:Lp14|Lm14|P14))'
    Iesniedzēji: 'Deputāti X, Y, Z' vai 'Iesniedzējs: Ministru kabinets'
    bill_type derivēts no document_nr sufiksa; jebkurš cits sufikss → log + skip.
    """

def upsert_bill(
    document_nr: str,
    title: str,
    bill_type: str,
    institutional_submitter: Optional[str] = None,
    topic: Optional[str] = None,
) -> int:
    """Idempotents — ja document_nr jau eksistē, atjaunina title/topic tikai ja tie mainījušies.
    Returns bill_id."""

def match_submitters_to_politicians(
    db: sqlite3.Connection,
    bill_id: int,
    submitter_names: list[str],
) -> tuple[int, list[str]]:
    """Izmanto esošo tracked_politicians.name_forms match. Ievieto junction rindas
    role='submitter'. Returns (matched_count, unmatched_names)."""

def append_bill_stage(
    db: sqlite3.Connection,
    bill_id: int,
    stage_name: str,
    stage_result: Optional[str],
    stage_date: str,
    vote_id: Optional[int] = None,
    session_id: Optional[int] = None,
    amendment_nr: Optional[str] = None,
) -> int:
    """Append-only. Atjaunina saeima_bills.current_stage/status/last_updated_at.
    Vienā transakcijā. Validē stage_name pret _VALID_STAGE_NAMES. Phase 1 stages
    jau saglabājas ar stage_kind='vote' DB defaults; stage_kind parameter nav nepieciešams."""

def resolve_bill_from_motif(motif: str) -> Optional[str]:
    """Izvelk document_nr no motif, piem. 'Grozījumi X likumā (1315/Lp14)' → '1315/Lp14'.
    Returns None ja nav atrasts."""

def _reading_from_motif(motif: str) -> str:
    """Canonical stage_name no motif (case-insensitive); pirmais piemērojamais
    noteikums uzvar (sk. § 3.3 priority list). Rules 4–5 substring-match
    motif, kas Saeimas agenda formātā satur document_nr ("(1315/Lp14)",
    "(127/P14)") — atsevišķa document_nr arg nav nepieciešama.
       '1.lasījums' / '2.lasījums, steidzams' → '{N}.lasījums'
       'iecelšanu par.*tiesnesi' / 'atbrīvošanu no tiesneša' → 'tiesneša_amats'
       'termiņa pagarināšanu' / 'komisijas noteikšanu' → 'procesuāls'
       '/P14' document_nr → 'paziņojuma_balsojums'
       '/Lm14' document_nr (citi) → 'Lm14 cits'
       motif bez atbilstības → 'nezināms'
    Note: stage_name 'atgriezts komisijā' un 'atsaukts' netiek
    automātiski klasificēti; tos uzliek agent prompt manually pēc
    semantiska konteksta vai eksplicīta agenda anotācija.
    """
```

### 4.4 Agenta prompt izmaiņas (`.claude/agents/saeima-tracker.md`)

Pievieno:

- **Section "Step 2: Parse agenda" pirms "Step 3: For each voting URL"** — instrukcija pirms balsojumu skrāpēšanas palaist `parse_agenda_snapshot` + `upsert_bill` + `match_submitters_to_politicians` katram agenda bill.
- **Section "Step 5.5: Link vote to bill"** — pēc katra `store_vote()` palaist `resolve_bill_from_motif` + `append_bill_stage`.
- **Agent discipline lemma**: "Kad rodas jauns institucionālais iesniedzējs (nav Ministru kabinets / Saeimas Prezidijs / zināma komisija), APSTĀJ un ziņo cilvēkam, lai varētu papildināt kanonisko sarakstu." Novērš silent misclassification.

---

## 5. Retro backfill (vienreizēja migrācija)

### 5.1 Mērķis

Aizpildīt `saeima_bills` + `saeima_bill_stages` no esošajām 113 `saeima_votes` rindām, lai Phase 1 UI nav tukša no dienas 1.

### 5.2 Skripts `scripts/backfill_saeima_bills.py`

```python
# Pseido-kods
def backfill():
    db = get_db()
    init_saeima_tables(db)  # creates saeima_bills + bill_stages + junction

    # 1. Sagrupē esošos votes pēc document_nr
    votes = db.execute("""
        SELECT id, motif, document_nr, vote_date, result, summary, topic
        FROM saeima_votes
        WHERE document_nr IS NOT NULL
        ORDER BY vote_date ASC
    """).fetchall()

    grouped = defaultdict(list)
    for v in votes:
        grouped[v['document_nr']].append(v)

    # 2. Katram document_nr izveido bill + stages
    for doc_nr, vote_list in grouped.items():
        # title no visvēlākā balsojuma
        latest = vote_list[-1]
        title = _extract_title_from_motif(latest['motif'])
        # Three-way classification; nezināms suffix → skip ar warn
        if '/Lp14' in doc_nr: bill_type = 'Lp14'
        elif '/Lm14' in doc_nr: bill_type = 'Lm14'
        elif '/P14' in doc_nr: bill_type = 'P14'
        else: continue  # neattiecas uz _VALID_BILL_TYPES; log + skip
        topic = latest['topic']
        summary = latest['summary']  # pēdējais vote summary kļūst par bill summary

        bill_id = upsert_bill(doc_nr, title, bill_type, topic=topic)
        if summary:
            db.execute("UPDATE saeima_bills SET summary=? WHERE id=?", (summary, bill_id))

        # Katrs vote kļūst par stages rindu
        for v in vote_list:
            stage_name = _reading_from_motif(v['motif'])  # may return 'nezināms'
            append_bill_stage(
                db, bill_id=bill_id, stage_name=stage_name,
                stage_result=v['result'], stage_date=v['vote_date'],
                vote_id=v['id'],
            )
            db.execute("UPDATE saeima_votes SET bill_id=? WHERE id=?", (bill_id, v['id']))

    # 3. Pārskats
    unknown_stages = db.execute("""
        SELECT COUNT(*) FROM saeima_bill_stages WHERE stage_name='nezināms'
    """).fetchone()[0]
    total_bills = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]

    print(f"Izveidots {total_bills} bills no {len(votes)} votes.")
    print(f"Stadijas ar 'nezināms': {unknown_stages}")
    if unknown_stages > len(votes) * 0.1:
        print("WARN: >10% stadiju nav klasificētas. Apsver agenda re-parse.")
```

### 5.3 Kas NETIEK backfillots

- **Iesniedzēji** — esošajos `saeima_votes` datos tie nav. Atstājam tukšus; Phase 2 opcionāli re-scrape vēsturiskās agendas.
- **Priekšlikumu autori** — tas pats.
- **`institutional_submitter`** — tas pats.
- **`first_seen_at`** — iestata uz pirmā vote datumu (approximation).
- Votes ar `document_nr IS NULL` netiek linkoti (retro-only; Phase 1 priekšā visi jauni votes nāks ar document_nr).

### 5.4 Acceptance kritēriji

- Migrācija skrien bez kļūdām uz dzīvās DB (`data/atmina.db`).
- `SELECT COUNT(DISTINCT document_nr) FROM saeima_votes` = `SELECT COUNT(*) FROM saeima_bills` (ignorējot NULL).
- `unknown_stages` ziņojums tiek ielogots; ja pārsniedz **10%** (paplašinātais vocabulary aptver 80%+ esošo motifs), failo atsevišķu issue par agenda re-parse vai jauna stage_name pievienošana. Iepriekšējais 30% slieksnis attiecās uz minimālo 9-stage vocabulary; pēc § 3.3 paplašinājuma realitāte ir <8% (audit 2026-04-26).
- `print_routine()` pievieno jaunu check: `saeima_bills` tabula ir aizpildīta, `saeima_votes.bill_id` nav 100% NULL.

---

## 6. Lietotāja interfeiss

### 6.1 Apakšcilne `/balsojumi.html#bills-list`

Pievieno **trešo subtab-btn** blakus esošajiem:

```html
<div class="subtab-bar">
  <button class="subtab-btn active" data-tab="votes-list">Balsojumi</button>
  <button class="subtab-btn" data-tab="votes-matrix">Matrica</button>
  <button class="subtab-btn" data-tab="bills-list">Likumprojekti</button>   <!-- JAUNS -->
</div>
```

**Grid kartiņa** (`bill-card`) rāda:

```
┌──────────────────────────────────────────────────────────┐
│ [1315/Lp14]  Lp14                         Aizsardzība    │  ← document_nr + bill_type pill + topic pill
│                                                          │
│ Grozījumi Valsts aizsardzības finansēšanas likumā        │  ← title (h3)
│                                                          │
│ Paaugstina aizsardzības budžeta minimumu no 3% līdz      │  ← summary (2 rindas max, ellipsis)
│ 5% no IKP sākot ar 2027. gadu                            │
│                                                          │
│ ▸ 3.lasījums  pieņemts  2026-04-23                       │  ← current_stage badge
│ Iesniedza: Ministru kabinets                             │  ← institutional vai top-3 deputāti
│                                                          │
│ [5 iesniedzēji]  [jaunākais balsojums →]                 │  ← counts + link
└──────────────────────────────────────────────────────────┘
```

**Filtru bāra**: topic multi-select + `current_status` severity-style buttons + `bill_type` toggles (Lp14 / Lm14 / P14) + teksta meklēšana pēc title un document_nr.

**Kārtošana**: default `last_updated_at DESC`. Opcijas: alfabētiski, pēc topic.

### 6.2 Detail lapa `/likumprojekti/{document_nr_slug}.html`

`document_nr_slug` = `document_nr.lower().replace("/", "-")` → `1315-lp14`.

**Lapas struktūra:**

```
┌───────────────────────────────────────────────────────────────┐
│ pagehead-header:                                              │
│   pagehead-kicker: "14. Saeima · {Likumprojekts|Lēmuma projekts|Paziņojums}"  │  ← atkarībā no bill_type
│   pagehead-h1: Grozījumi Valsts aizsardzības finansēšanas     │
│                likumā                                         │
│   pagehead-metrics: [document_nr] [topic] [current_status]   │
└───────────────────────────────────────────────────────────────┘

[Summary block — serif, 18px, max 3 rindas]
Paaugstina aizsardzības budžeta minimumu no 3% līdz 5% no IKP
sākot ar 2027. gadu. Iesniedza Ministru kabinets 2026-02-10.

[Stadiju timeline — vertikāla, mono/dense]
─── iesniegts ───────────── 2026-02-10
 ●  1.lasījums  pieņemts    2026-03-05  [53 par / 32 pret]
 ●  2.lasījums  pieņemts    2026-04-01  [67 par / 20 pret]
 ●  3.lasījums  pieņemts    2026-04-23  [71 par / 18 pret]

[Iesaistītie politiķi — 2 kolonnas]
Iesniedzēji                    │  Priekšlikumu autori (Phase 2)
────────────────                │  ───────────────────────────
· Ministru kabinets             │  · Krišjānis Feldmans (JV) — 3 priekšl.
  (institucionāls)              │  · Andris Šuvajevs (PRO) — 2 priekšl.
                                │  · ...

[Balsotāju sadalījums — partiju grid (reuse balsojumi.html kartiņa)]
JV  100% par    ZZS  60% pret
NA   88% par    AS   50% atturas
...

[Saistītais bāzes likums]  ← ja base_law_slug ne null
Šis likumprojekts groza: **Valsts aizsardzības finansēšanas likums**
[Atvērt likuma lapu →] linko uz `/likumi/valsts-aizsardzibas-finansesanas-likums.html`
(rendered no `wiki/laws/valsts-aizsardzibas-finansesanas-likums.md` ar Jinja2)

**base_law_slug atlases noteikumi (`_resolve_base_law_slug`):**
1. Ja motif satur eksaktu likuma nosaukumu no `wiki/laws/likumi.md` indeksa (case-insensitive substring match), atgriež slug.
2. Ja motif satur "Grozījumi {X}" un X normalizācijā atbilst slug → atgriež slug.
3. Citādi NULL (lielākoties tas notiek jauniem likumiem, kas vēl nav wiki).
```

**Mobilā (≤760px):** timeline paliek vertikāla; politiķu divu kolonnu bloks collapse uz stack; partiju grid collapse uz 2 kolonnām.

### 6.2.1 wiki/laws lapas auto-enrichment

Esošās `wiki/laws/<slug>.md` lapas tiek paplašinātas ar auto-ģenerētu sekciju **starp markeriem** (analogi `<!-- SYNC-AUTO START -->` / `<!-- SYNC-AUTO END -->` patternam, ko jau izmanto person profiles):

```markdown
<!-- BILLS-SYNC-AUTO START -->
## Aktuālie likumprojekti šajā likumā

| Bill nr | Nosaukums | Stadija | Datums |
|---|---|---|---|
| [1315/Lp14](/likumprojekti/1315-lp14.html) | Grozījumi par 5% IKP | 3.lasījums (pieņemts) | 2026-04-23 |
| [1098/Lp14](/likumprojekti/1098-lp14.html) | Iepirkumu vienkāršošana | 2.lasījums (pieņemts) | 2026-03-12 |
<!-- BILLS-SYNC-AUTO END -->
```

**Generators:**
- `src/wiki_sync.py` (jauna funkcija `_render_law_bills_block(slug)`) izmeklē `saeima_bills WHERE base_law_slug = ?` un atjaunina markerus.
- Tiek izsaukts no esošā wiki sync flow, palaists pēc `@saeima-tracker` agent darba un pirms publiskās ģenerācijas.
- Idempotents: ja nav saistīto bills, sekcija ir tukša ("Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā.").

**Publiskā render no wiki:**
- `src/generate.py::_generate_law_pages()` (jauna funkcija) iet pār `wiki/laws/*.md`, atjaunina BILLS-SYNC-AUTO marķierus *runtime*, un renderē `/likumi/<slug>.html` ar `templates/likums.html.j2`.
- Detail page `[Atvērt likuma lapu →]` link rāda uz šo URL.

### 6.3 Cross-linking

Publiskajā vietnē esošās atsauces uz likumprojektiem kļūst par linkiem:

- `balsojumi.html` katra vote kartiņa ar `document_nr` — pievieno `<a href="/likumprojekti/{slug}.html">` wrapperi.
- Politiķa profila `politician.html` → ja politiķis ir junction rindā (submitter/amendment_author) vai balsotājs, saraksts "Likumprojekti, kuros iesaistīts" ar linkiem.
- Pozīciju kartiņas, kur summary tekstā ir pieminēts `NNNN/Lp14`, tiek auto-linkotas — regex detect + transform (pēc backfill).

### 6.4 Template faili

Jauni:
- `templates/likumprojekts.html.j2` — detail page.
- `templates/_bill_card.html.j2` — atkārtoti izmantojams macro (grid + politiķa profilā).

Modificēti:
- `templates/balsojumi.html.j2` — pievieno 3. subtab + `#bills-list` sekciju.
- `templates/politician.html.j2` — pievieno "Likumprojekti" sekciju (zem esošajām).
- `templates/likums.html.j2` — jauns; rāda wiki/laws lapu + auto-iekļautās bills (Markdown → HTML konversija ar mistune vai esošu wiki render helper).
- `assets/style.css` — `bill-card-*` klases; timeline komponente (~80 rindas).

### 6.5 Statiskā ģenerācija (`src/generate.py`)

Jaunas funkcijas:
- `_fetch_bills()` — SELECT visas `saeima_bills` ar joined stages + submitter counts.
- `_fetch_bill_detail(bill_id)` — pilni dati vienam bill: stages, submitters, amendment_authors, vote breakdown par frakcijām.
- `_generate_bill_pages()` — iterē pār `saeima_bills`, renderē `likumprojekts.html.j2`.
- `_generate_law_pages()` — iterē pār `wiki/laws/*.md`, atjaunina `BILLS-SYNC-AUTO` markierus, renderē `/likumi/<slug>.html`. Izsaukts pirms `_generate_bill_pages()`, lai bill detail page back-link rezolvē.
- `_resolve_base_law_slug(motif)` (`src/saeima.py`) — match logic, kas aprakstīts § 6.2.

`generate_public_site()` izsauc `_generate_bill_pages()` pirms `_generate_politician_pages()`, lai politiķa profila "Likumprojekti" sekcija var reference detail URLs.

---

## 7. Phase 2: Priekšlikumu autori + pieprasījumu pipeline

### 7.1 Priekšlikumu scrape (prasa spike)

**Pirms plāna rakstīšanas, spike:**

1. Atvērt `https://titania.saeima.lv/LIVS14/saeimalivs14.nsf/webSasaiste?OpenView&restricttocategory=1315/Lp14`.
2. Identificēt, kā tiek linkota priekšlikumu tabula (vai tā ir atsevišķs dok, `anotācijas` blakus, vai PDF).
3. Playwright snapshot — vai tabula ir accessible-tree parsējama vai tikai PDF tekstā.

**Rezultātā:**
- Ja Playwright-friendly → `parse_amendments_snapshot()` helper + `match_amendment_authors_to_politicians()`.
- Ja tikai PDF → Phase 3 darbs ar `pdfminer` vai OCR; šajā darbā paliek tikai summary + balsotāji.

### 7.2 Pieprasījumu pipeline (`claim_type='saeima_inquiry'`)

1. `parse_agenda_snapshot()` jau Phase 1 izvelk pieprasījumus uz atsevišķu queue log (`data/saeima_inquiries/{date}.json`).
2. Phase 2: jauns `@claim-extractor` prompt variants `.claude/agents/claim-extractor-saeima-inquiry.md`:
   - Input: pieprasījuma pilns teksts.
   - Task: izvilkt *implicēto stance* no pieprasījuma formulējuma. Piemērs: "Kāpēc valdība neveic pasākumus pret droniem?" → stance = "Valdība nav veikusi pietiekamas drošības darbības", confidence ≤ 0.7 (zemāka nekā tiešās pozīcijas).
3. Store via `store_claim(..., claim_type='saeima_inquiry')` ar `source_url` = Saeimas pieprasījuma permalinks.

### 7.3 Readers disciplīna (mandatory)

Pēc `saeima_inquiry` ieviešanas, audit 4 failos:

- **`src/wiki.py`** — politiķa profilā: atsevišķa sadaļa "Parlamenta pieprasījumi", ne samaisīta ar pozīcijām.
- **`src/briefs.py`** — dienas brief metriki: `saeima_inquiry` ne-iekļaujas "Jaunas pozīcijas" count; atsevišķa rinda "Jauni pieprasījumi".
- **`src/generate.py`** — `/pozicijas.html` filtrē `claim_type='position'` tikai; jauna sadaļa politiķa profilā (sk. 6.2) atsevišķi.
- **`src/contradictions.py`** — cross-type comparisons atļautas: `saeima_inquiry` vs `position`, `saeima_inquiry` vs `saeima_vote`. Pievieno testu, kas verificē, ka jauni inquiry rada kontradikciju kandidātus pret esošām pozīcijām.

**Acceptance tests:**
- `test_saeima_inquiry_not_in_position_count` — `saeima_inquiry` neparādās "Pozīcijas: X" metrikas skaitītājā.
- `test_saeima_inquiry_triggers_contradictions` — pēc inquiry ingest, `search_similar_claims` atrod kandidātus pret esošām pozīcijām ar pretēju stance.

---

## 8. Testi

### 8.1 Unit tests (`tests/test_saeima_bills.py`)

- `test_init_saeima_bills_creates_schema` — tabulas, indeksi izveidoti, idempotenti.
- `test_upsert_bill_idempotent` — tas pats document_nr divreiz → viena rinda, otrais izsauc atjaunina title tikai ja mainīts.
- `test_append_bill_stage_atomic` — stage + current_stage atjauninās vienā transakcijā; ja atteikšanas, abi rollback. Phase 1 stages tiek saglabāti ar `stage_kind='vote'` default (DB-side, nav parameter).
- `test_stage_name_validation` — ne-kanoniska vērtība → `ValueError`.
- `test_current_stage_follows_latest_stage` — vairākas stages → current_stage = pēdējā pēc stage_date.
- `test_resolve_bill_from_motif` — 20 motif paraugu → pareizs document_nr vai None.
- `test_reading_from_motif` — "(1.lasījums)", "2.lasījums, steidzams", "iecelšanu par tiesnesi" (Lm14), "termiņa pagarināšanu" (Lm14), "/P14" doc_nr, "/Lm14" doc_nr bez citas atbilstības, motif bez atbilstības → pareizs stage_name; arī negative case kur motif satur gan "lasījum" gan "/Lm14" — priority 1 uzvar.
- `test_match_submitters_to_politicians` — 3 zināmi deputāti + 1 nezināms → 3 junction rindas, viens unmatched.
- `test_institutional_submitter_parse` — "Iesniedzējs: Ministru kabinets" → saglabāts `institutional_submitter` laukā, nav junction rindas.

### 8.2 Integration tests (`tests/test_saeima_integration.py`)

- `test_parse_agenda_2026_04_16` — izmanto esošo `data/saeima_snapshots/2026-04-16/agenda.md` fixture, verificē, ka visi Lp14/Lm14 ir izvilkti; vismaz viens institutional_submitter, vismaz viens individual_submitters saraksts.
- `test_backfill_preserves_vote_data` — palaiž backfill uz test DB ar 5 balsojumiem; verificē, ka `saeima_bills` + `saeima_bill_stages` reflected, `saeima_votes.bill_id` aizpildīts.

### 8.3 Smoke test pre-deploy

- `python -m src.generate` — renderē visu site bez kļūdām; `output/likumprojekti/` mape izveidota ar pareizo failu skaitu.
- Manuāli atvērt `/balsojumi.html#bills-list` lokāli (`serve.py`) un pārbaudīt: filtri strādā, jebkura kartiņa ved uz detail lapu, detail lapa rāda timeline + iesniedzējus.

---

## 9. Ieviešanas secība

1. **Shēmas migrācija + helper funkcijas** (`src/saeima.py`). Testi zaļi.
2. **Backfill skripts** (`scripts/backfill_saeima_bills.py`). Palaiž dry-run → review → live.
3. **UI: detail template + generate funkcijas**. Renderē lokāli, vizuāli review.
4. **UI: `/balsojumi.html` 3. subtab + politiķa profila sekcija**.
5. **Cross-linking** (vote kartiņas, pozīciju auto-link).
6. **Agenta prompt update** (`.claude/agents/saeima-tracker.md`).
7. **Runbook** (`wiki/operations/saeima-bills.md`).
8. **CHANGELOG + routine integration.**
9. **Ship Phase 1.** Phase 2 — atsevišķs spec pēc spike.

---

## 10. Riski un mitigācijas

| Risks | Mitigācija |
|---|---|
| Agenda format mainās Saeimas pusē | `parse_agenda_snapshot` pret esošo `2026-04-16/agenda.md` fixture; ja parsētājs fail → fallback uz vote-only režīmu (nav bill enrichment; esošā funkcionalitāte neietekmēta). |
| `document_nr` nav klasificēts kā Lp14, Lm14 vai P14 (nākotnes Saeima vai jauni dokumentu tipi) | `bill_type` validē pret `_VALID_BILL_TYPES = {'Lp14', 'Lm14', 'P14'}` whitelistu; nezināms → log + skip ar warn. Nepārdali datus. |
| Backfill `stage_name='nezināms'` pārsniedz 10% | Skripts ziņo; apsveram retro-parsēt vēsturiskās agendas (Phase 1.5). |
| Denormalizācijas sinhronija | Tests + Python invariant (`append_bill_stage` ir vienīgais ceļš). Periodiski sanity check skriptā `print_routine()`. |
| Priekšlikumu scrape nav Playwright-friendly (Phase 2 spike atklāj PDF-only) | Phase 2 pārejas plāns: `saeima_bill_politicians` junction paliek "submitter only" līdz Phase 3 PDF parser. UI cilvē ”Priekšlikumu autori” rāda empty state "Pieejams Phase 2". |
| `claim_type='saeima_inquiry'` piesārņo pozīciju metrikas (ja readers audit aizmirsts) | Nav Phase 1 risks — `saeima_inquiry` claim_type tiek ieviests tikai Phase 2. Phase 2 spec prasa audit 4 failos ar dedicated testiem pirms pirmā inquiry ingest. |
| Politiķa ID match failure iesniedzējiem ar diakritikas variantiem | Reuse esošo `match_deputies_to_politicians`, kuram jau ir `name_forms` handling. Unmatched → `scripts/audit_unmatched_submitters.py` ziņo cilvēkam. |

---

## 11. Dokumentācija

- **`wiki/operations/saeima-bills.md`** — operacionālais runbook: kā palaist `@saeima-tracker` ar jauno flow, kā backfill, kā rokām pievienot institutional_submitter.
- **`wiki/CHANGELOG.md`** — pievienot ierakstu `## YYYY-MM-DD — Saeima bills tracker` (ieviešanas dienā) ar shēmas delta un migrācijas komandu.
- **`CLAUDE.md § Pipeline Invariants`** — papildināt ar: "12. `saeima_votes.bill_id` ir tikai-rakstāms caur `append_bill_stage()`; neatjaunina manuāli."
- **`.claude/agents/saeima-tracker.md`** — jauni Step 2 / 3 / 5.5 sections.

---

## 12. Atklātie jautājumi (nav blokeri Phase 1)

1. Vai `bill_type` whitelist jāpaplašina ar nākotnes Saeimu variantiem (`/Lp15`, `/Lm15`, `/P15` kad 15. Saeima sāks)? Phase 1 ignorē — tikai 14. Konstantes nosaukums `_VALID_BILL_TYPES` neatkarīgs no Saeimas numura, tikai vērtības saraksts.
2. Vai detail lapā rādīt saistītās pozīcijas (politiķu publiskā runa par šo likumu)? — Jā, kad bill ID auto-link pozīcijās ir aktīvs (Phase 1 step 5). Sākotnēji var būt tukšs bloks.
3. Vai `wiki/laws/*.md` renderēšana uz publiskās vietnes ir atsevišķs spec (jā) vai šī scope? — **Iekļauts šajā scope (Phase 0 prep update)**: § 6.2.1 definē auto BILLS-SYNC-AUTO bloku + `_generate_law_pages()`. `templates/likums.html.j2` ir jauns šī darba ietvaros. Sākotnējā atbilde "atsevišķs" ir aizvietota.
4. Vai pie likumprojekta iesniedzējiem rādīt *arī* institucionālā iesniedzēja attēlu/logo (Ministru kabinets ģerbonis)? — Nē, tikai teksts; UI vienkāršība svarīgāka.
5. Vai Phase 3 lietos `saeima_bill_stages` ar `stage_kind='debate'` vai atsevišķu `saeima_debate_utterances` tabulu? Phase 1 hook abi pieļauj — atsevišķa tabula labāka, ja per-utterance ir vairāki politiķi (panel debate); apvienota tabula labāka, ja katra utterance ir 1 politiķis. Lēmums Phase 3 specā.
6. **P14 (paziņojuma) detail lapas URL un timeline forma:** Phase 1 izvēle — visi bill types (Lp14/Lm14/P14) dala vienu URL prefiksu `/likumprojekti/{slug}.html` un vienu template; pagehead-kicker conditional (sk. § 6.2 wireframe). Timeline P14 bills'iem dabīgi sašaurinās uz `iesniegts` + `paziņojuma_balsojums` (2 stages); priekšlikumu/lasījumu sekcijas conditional render `bill_type='Lp14'` only. Atsevišķs `/pazinojumi/{slug}.html` URL prefikss ir terminoloģiski tīrāks, bet pievieno UI/SEO sarežģījumu, kuru Phase 1 atstāj uz vēlāku redizainu, ja P14 apjoms aug.
