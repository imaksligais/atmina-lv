# Publicēšanas apstiprinājums ar satura hešu (audits A1) — plāns

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** apstiprinājums (`publish_approvals`) attiecas uz KONKRĒTU saturu. Ja pārskata vai Atraduma saturs pēc apstiprināšanas mainās, deploy preflight atsaka, līdz operators apstiprina vēlreiz.

**Operatora lēmums 2026-11-03:** jebkurš satura labojums pēc apstiprināšanas → atkārtoti `scripts/approve_publish.py <key>` → rutīnas 11. solis pēc tam gaida jaunu deploy.

**Architecture:** viena funkcija `publish_content_hash(db, key)` (`src/briefs.py`) atrod saturu atslēgai un atgriež SHA-256. To sauc ABI: `approve_publish.py` (raksta hešu) un `check_output.py` publish-gate (salīdzina). Jauna kolonna `publish_approvals.content_sha256`. Esošās rindas aizpilda vienreizējs skripts ar rollback.

**Tech Stack:** Python 3.12, sqlite3, pytest. Vienmēr `.venv/Scripts/python.exe`.

**Spec:** `docs/audits/2026-11-02-implicitie-stavoklu-automati.md` § A1.

## Global Constraints

- Hešo AVOTA saturu, nekad renderēto HTML (lodziņi, skaitļi mainās katrā renderā).
- Pirms hešošanas: `content.replace("\r\n", "\n").encode("utf-8")` — git CRLF konversija nedrīkst bloķēt deploy.
- Pārskats: `context_notes.content` tai rindai, ko jau izvēlas `_check_brief_gate` — jaunākā `created_at` ar `note_type IN ('daily_brief','weekly_brief')`, kuras `brief_publish_key(note_type, brief_subject_date(topic, content, created_at)) == key`.
- Atradums (`analizes/<slug>`): fails `CONTENT_DIR / "analizes" / f"{slug}.md"` (`src/render/_common/constants.py`).
- Vārti dzīvo TIKAI `scripts/check_output.py` preflight. `is_brief_published()` NEMAINĪT — izmests pārskats izdzēstu live lapu nākamajā pilnā koka deploy.
- `content_sha256 IS NULL` = bloķēt (ar re-approve komandu). Nekāda «mantojuma iziešana».
- Datu mutācija ar roku → `data/rollback_*.sql` komitēts PIRMS izpildes (CLAUDE.md escalation 8).
- **Git aizliegums palīgam:** nekad `git stash`, `git checkout --`, `git restore`, `git reset`. Commit tikai uzdevuma failiem, ziņa caur failu (`git commit -F`), beigās `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Testi nekad neaiztiek dzīvo DB (`tests/conftest.py` § 4–5).
- LV teksts (ziņojumi, docstringi, runbooki): gramatika + stilistika pēc CLAUDE.md.

## Non-goals

- Hero attēla maiņa pēc apstiprināšanas (atsevišķi `brief_images` vārti).
- Korektūras ieraksts.
- Rutīnas 11. solis nedēļas / `analizes/` atslēgām (paliek backlogā).

## Review Focus

1. Dienas un nedēļas pārskats ar vienu subjekta datumu — resolveris nedrīkst sajaukt `2026-11-02` ar `nedela-2026-11-02` (tests Task 1).
2. CRLF vs LF tas pats teksts → tas pats hešs (tests Task 1).
3. Apstiprinājums atslēgai, kurai nav satura → `approve_publish` atsaka, rinda netiek ierakstīta (tests Task 2).
4. Nemigrēta DB bez kolonnas → vārti krīt ar skaidru ziņu, ne iziet (tests Task 3).
5. Pēc backfill dzīvajā kokā 0 heša bloķējumu (Task 4 pārbaude, ne tests).

---

### Task 1: `publish_content_hash` + kolonna

**Files:**
- Modify: `src/briefs.py` (blakus `brief_publish_key`, ~rinda 105)
- Modify: `src/db_migrations.py` (pēc `publish_approvals` CREATE, ~rinda 101)
- Modify: `src/schema.sql`, ja tur ir `publish_approvals` definīcija (pārbaudi ar grep; ja nav, neko)
- Test: `tests/test_publish_approvals.py`

**Interfaces — Produces:**
- `publish_content_hash(db: sqlite3.Connection, key: str, content_dir: Path | None = None) -> str | None` — hex SHA-256 vai `None`, ja saturs nav atrodams. `content_dir` noklusējums `CONTENT_DIR`; testiem padod tmp.
- Kolonna `publish_approvals.content_sha256 TEXT` (nullable).

**Pārbaudi, nepieņem:** vai `get_db()` palaiž migrācijas, vai tikai `init_db()`. (Orientācijā: `get_db` NEmigrē.) Noskaidro, kā dzīvā DB saņem jaunu kolonnu (piem. `init_db()` ir idempotents un to drīkst palaist) — ieraksti atbildi Task 4 solī.

- [ ] **Step 1: Failing tests** (`tests/test_publish_approvals.py`; lieto esošo `db_file` fixture un `_store_daily_brief` paraugu):

```python
def test_hash_daily_and_weekly_same_date_are_distinct(db_file):
    # daily 2026-11-02 un weekly ar subjekta datumu 2026-11-02 — atšķirīgs saturs
    ...  # ievieto abas context_notes rindas
    db = sqlite3.connect(db_file); db.row_factory = sqlite3.Row
    from src.briefs import publish_content_hash
    h_day = publish_content_hash(db, "2026-11-02")
    h_week = publish_content_hash(db, "nedela-2026-11-02")
    assert h_day and h_week and h_day != h_week

def test_hash_ignores_crlf(tmp_path, db_file):
    d = tmp_path / "analizes"; d.mkdir()
    (d / "a.md").write_bytes(b"x\r\ny\r\n")
    db = sqlite3.connect(db_file)
    h1 = publish_content_hash(db, "analizes/a", content_dir=tmp_path)
    (d / "a.md").write_bytes(b"x\ny\n")
    assert publish_content_hash(db, "analizes/a", content_dir=tmp_path) == h1

def test_hash_missing_content_is_none(tmp_path, db_file):
    db = sqlite3.connect(db_file)
    assert publish_content_hash(db, "2030-01-01") is None
    assert publish_content_hash(db, "analizes/nav", content_dir=tmp_path) is None
```

Nedēļas pārskata `topic`/`content` formu ņem no esošiem testiem (`grep -n weekly_brief tests/*.py`), lai `brief_subject_date` to atpazītu.

- [ ] **Step 2:** palaid — FAIL (`ImportError`).
- [ ] **Step 3: Implementācija** (`src/briefs.py`):

```python
def publish_content_hash(db, key: str, content_dir=None) -> str | None:
    """SHA-256 saturam, ko apstiprina `publish_approvals[key]` (audits A1).

    Pārskats: jaunākā daily/weekly `context_notes` rinda ar šo lapas slugu
    (tā pati, ko izvēlas deploy publish-gate). Atradums: content/analizes/<slug>.md.
    CRLF→LF pirms hešošanas: git konversija nav satura maiņa.
    """
    import hashlib
    if key.startswith("analizes/"):
        from src.render._common.constants import CONTENT_DIR
        path = Path(content_dir or CONTENT_DIR) / "analizes" / f"{key.split('/', 1)[1]}.md"
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    else:
        text = None
        for r in db.execute(
            "SELECT topic, content, created_at, note_type FROM context_notes"
            " WHERE note_type IN ('daily_brief','weekly_brief') ORDER BY created_at DESC"
        ):
            d = brief_subject_date(r[0], r[1], r[2])
            if d and brief_publish_key(r[3], d) == key:
                text = r[1] or ""
                break
        if text is None:
            return None
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
```

(Indeksi, ne nosaukumi — `db` var būt bez `row_factory`. Ja `Path` vēl nav importēts `briefs.py`, pievieno.)

Migrācija (`src/db_migrations.py`, tūlīt pēc `publish_approvals` CREATE):

```python
    pa_cols = {r[1] for r in db.execute("PRAGMA table_info(publish_approvals)").fetchall()}
    if "content_sha256" not in pa_cols:
        # 2026-11-03 (audits A1): apstiprinājums attiecas uz konkrētu saturu.
        db.execute("ALTER TABLE publish_approvals ADD COLUMN content_sha256 TEXT")
```

- [ ] **Step 4:** testi PASS.
- [ ] **Step 5:** commit «A1: publish_content_hash + publish_approvals.content_sha256».

### Task 2: `approve_publish.py` raksta hešu, atsaka bez satura

**Files:** Modify `scripts/approve_publish.py` (`approve()`, docstring); Test `tests/test_publish_approvals.py`.

**Interfaces — Consumes:** `publish_content_hash` no Task 1.

- [ ] **Step 1: Failing tests:**

```python
def test_approve_stores_content_hash(db_file):
    _store_daily_brief(db_file, "2026-11-02", bloc_count=None)  # vai cits esošs helpers bez tabulām
    assert approve("2026-11-02", db_path=db_file) == 0
    row = sqlite3.connect(db_file).execute(
        "SELECT content_sha256 FROM publish_approvals WHERE subject_key='2026-11-02'").fetchone()
    assert row[0] and len(row[0]) == 64

def test_approve_refuses_key_without_content(db_file, capsys):
    assert approve("2030-01-01", db_path=db_file) == 1
    assert _keys(db_file) == set()
    assert "nav satura" in capsys.readouterr().err
```

Esošie testi, kas apstiprina kailu atslēgu bez pārskata (`test_approve_writes_row_with_lv_timestamp`, `_accepts_weekly_key`, `_is_idempotent`, `test_revoke_removes_row`, `test_list_prints_denominator`) tagad kritīs — tiem PIRMS `approve` ievieto saturu (daily/weekly rindu). Analīzes atslēgai `approve()` vajag `content_dir` — pievieno `approve(key, db_path=None, content_dir=None)` un padod tālāk.

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** `approve()` pēc `mismatch` pārbaudes:

```python
    digest = publish_content_hash(db, key, content_dir=content_dir)
    if digest is None:
        db.close()
        print(f"NEAPSTIPRINĀTS: {key} — nav satura, ko apstiprināt "
              "(nav pārskata ar šo slugu vai content/analizes/<slug>.md).", file=sys.stderr)
        return 1
    ...
    db.execute(
        "INSERT INTO publish_approvals (subject_key, approved_at, content_sha256) VALUES (?, ?, ?)"
        " ON CONFLICT(subject_key) DO UPDATE SET approved_at = excluded.approved_at,"
        " content_sha256 = excluded.content_sha256",
        (key, ts, digest),
    )
    ...
    print(f"apstiprināts publicēšanai: {key} ({ts}, saturs {digest[:12]})")
```

Docstringā: «Atļauja attiecas uz saturu: pēc jebkura labojuma palaid vēlreiz (2026-11-03).» Rindu «atļauja pārdzīvo brief pārģenerēšanu» precizē: pārdzīvo id maiņu, ne satura maiņu.
- [ ] **Step 4:** PASS (viss `tests/test_publish_approvals.py`).
- [ ] **Step 5:** commit.

### Task 3: publish-gate salīdzina hešu

**Files:** Modify `scripts/check_output.py` (`_check_brief_gate`, `_check_analysis_gate`); Test `tests/test_check_output.py` (lieto esošo `ROOT`/`DB_PATH` monkeypatch paraugu, ~rindas 34, 187).

**Interfaces — Consumes:** `publish_content_hash`. Analīzes vārtiem vajag `content_dir` — pievieno moduļa konstanti `CONTENT_DIR = REPO / "content"` blakus `ROOT`/`DB_PATH`, lai testi to var monkeypatch.

- [ ] **Step 1: Failing E2E tests** (caur `check_publish_gate([])`, kā esošie testi):
  - `test_brief_edited_after_approval_blocks_with_reapprove_command`: pārskats + approved=1 attēls + `approve()` → izmaini `context_notes.content` → problēmu sarakstā ir `blog/<datums>.html` un teksts `approve_publish.py <datums>`.
  - `test_brief_unchanged_after_approval_passes`: tas pats bez izmaiņas → `[]`.
  - `test_analysis_edited_after_approval_blocks`: `analizes/a.html` kokā, `content/analizes/a.md`, approve → izmaini `.md` → bloķē.
  - `test_null_hash_blocks`: `publish_approvals` rinda ar `content_sha256=NULL` → bloķē.
  - `test_gate_without_hash_column_fails_loudly`: DB ar veco tabulu bez kolonnas → problēma «DB kļūda» / «nemigrēta», ne `[]`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** abos vārtos `approvals` kļūst `dict[key, content_sha256]` (`SELECT subject_key, content_sha256`). Ja `key in approvals`, aprēķini `publish_content_hash(db, key, content_dir=CONTENT_DIR)` (savienojumam jābūt vēl atvērtam — pārvieto `db.close()` aiz cikla vai aprēķini hešus pirms aizvēršanas). Jauns zars pēc `missing_approval`:

```python
p = (f"publish-gate: {rel} — saturs mainījies pēc apstiprināšanas"
     f" (publish_approvals '{key}'); pēc korektūras:"
     f" .venv/Scripts/python.exe scripts/approve_publish.py {key}")
```

Skaitītājs `n_changed` un tas drukājas kopsavilkuma rindā (saucējs — CLAUDE.md «gate that cannot fail»). NULL hešs = tas pats zars ar tekstu «apstiprinājumam nav satura heša».
- [ ] **Step 4:** PASS `tests/test_check_output.py tests/test_publish_approvals.py`.
- [ ] **Step 5:** commit.

### Task 4: backfill dzīvajā DB + runbooki

**Files:**
- Create: `scripts/backfill_publish_approval_hashes.py` (`--dry-run` noklusējums, `--apply`)
- Create: `data/rollback_publish_approval_hashes_2026-11-03.sql` — galvā: forward izmaiņa + datums; saturs `UPDATE publish_approvals SET content_sha256 = NULL;` (kolonna paliek — tā ir koda migrācija).
- Modify: `wiki/operations/deploy.md` (T15), `.claude/commands/dienas-rutina.md`, `wiki/operations/weekly-routine.md`, `wiki/operations/commands.md`, `.claude/agents/brief-writer.md` — katrā viens teikums, kur jau minēts `approve_publish`: «Labojums pēc apstiprināšanas → apstiprini vēlreiz; citādi deploy preflight atsaka.»
- Modify: `CLAUDE.md` T15 rinda — pievieno: «apstiprinājums attiecas uz saturu (hešs); labojums pēc tā prasa atkārtotu apstiprinājumu».
- Modify: `wiki/CHANGELOG.md` (≤5 rindas, ar skaitļiem un to vaicājumu), `backlog/dati-db.md` (A1 izpildīts; atvērtais paliek).

- [ ] **Step 1:** pārbaudi, kā dzīvā DB saņem kolonnu (Task 1 piezīme). Pārliecinies ar `PRAGMA table_info(publish_approvals)` (read-only), ka kolonna ir, pirms backfill.
- [ ] **Step 2:** skripts: katrai `publish_approvals` rindai `publish_content_hash`; drukā saucēju «N rindas, M aizpildītas, K bez satura (atslēgas: …)». `--apply` raksta tikai `content_sha256 IS NULL` rindām.
- [ ] **Step 3:** rollback SQL + skripts COMMIT pirms `--apply`.
- [ ] **Step 4:** `--dry-run`, tad `--apply`. K rindas bez satura uzskaiti ziņojumā (tās nav kokā vai ir orfāni — neko nedzēst).
- [ ] **Step 5:** pārrenderē nav vajadzīgs; palaid `.venv/Scripts/python.exe scripts/check_output.py --publish-gate-only` uz esošā `output/atmina/` — gaidāms 0 «saturs mainījies» bloķējumu. Ja >0 — STOP un ziņo (nelabo, neapstiprini).
- [ ] **Step 6:** `CHECK_PYTEST_WORKERS=3 bash scripts/check.sh` — «all checks passed».
- [ ] **Step 7:** runbooki + CLAUDE.md + CHANGELOG + backlog; commit.

## Pabeigšanas ziņojums (palīgs → orķestrators)

Commit SHA saraksts; Task 4 skaitļi (N/M/K + K atslēgas); `--publish-gate-only` kopsavilkuma rinda; `check.sh` beigu rinda; kā dzīvā DB saņēma kolonnu; jebkas, kas atšķīrās no plāna.
