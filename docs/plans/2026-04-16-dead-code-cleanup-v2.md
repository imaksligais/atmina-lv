# Lieks kods un optimizācijas — pārstrādāts plāns (v2)

> **Šis plāns aizvieto** [`2026-04-16-dead-code-cleanup.md`](2026-04-16-dead-code-cleanup.md) (v1). v1 saturēja vairākas verifikācijas kļūdas: `wiki_sync`, `store_tension`, `read_ingest_log`, KNAB funkcijas un `init_saeima_tables` tika kļūdaini atzīmēti kā miruši, kaut tie ir aktīvi izsaukti caur `wiki/operations/` runbookiem un testiem. v2 ir pārbaudīts pret `src/`, `tests/`, `wiki/operations/` UN `docs/architecture.md`.

> **Aģentiskiem darbiniekiem:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Mērķis:** Noņemt verificēti mirušo kodu (~190 līn.) un izlabot timezone/logging korektuma riskus.

**Arhitektūra:** Mehānisks safe-fix (Fāze 1) → atsevišķi apstiprināmi orfani (Fāze 2-3) → korektuma migrācija ar TDD (Fāze 4) → `generate_statistika` lēmums (Fāze 5).

**Tech Stack:** Python 3.11+, ruff, vulture, pytest, SQLite.

---

## Verifikācijas metodoloģija (kāpēc v2 ir uzticams)

Katra "miruša" funkcija ir pārbaudīta četros slāņos:

1. `Grep "<func>" src/` — kods src/
2. `Grep "<func>" tests/` — testu izsaucēji
3. `Grep "<func>" wiki/operations/` — dokumentētas operāciju komandas
4. `Grep "<func>" docs/architecture.md` — arhitektūras komponentes

Funkcija tiek uzskatīta par mirušu **tikai ja visos četros slāņos atrod tikai definīciju**. v1 izlaida soļus 3 un 4.

**Konteksta filtrs (NAV uzskatīti par "lieku"):**
- `src/tools.py` MCP-style funkcijas (aģentu izsauktas dinamiski)
- `src/analyze.py`/`briefs.py`/`social.py` `fetch_*`/`generate_*` (aģentu prompti + CLI)
- `src/routine.py:print_routine` (CLAUDE.md komanda)
- `src/coalition.party_status` (CLAUDE.md noteikums #14)

---

## A. Verificēti miris kods

### A1. `_load_ideology()` — pilnīgi orfans
- **Vieta:** [src/generate.py:1584](../../src/generate.py)
- **Verifikācija:**
  - `src/`: tikai definīcija
  - `tests/`: nav atsauču
  - `templates/`: nav atsauču uz `_load_ideology` vai kontekstu, ko tā ražotu
  - `wiki/operations/`: nav atsauču
- **Piezīme:** `content/ideology.md` **eksistē** (v1 plāns kļūdaini apgalvoja pretējo). Funkcija ir orfana, jo neviens templates to nelieto — varbūt `about.html.j2` ideoloģijas sekcija nekad nepieslēgta vai noņemta. Faila nedzēšam — tā ir publicētā ideoloģijas dokumenta versija (sk. `wiki/operations/content-pipeline.md:6`).
- **Darbība:** Dzēst funkciju (~6 līn.).

### A2. `_parse_saeima_votes()` — orfans, aizvietots ar `src/saeima.py`
- **Vieta:** [src/ingest.py:624](../../src/ingest.py)
- **Verifikācija:** `Grep "_parse_saeima_votes"` — tikai definīcija visos slāņos.
- **Piezīme:** v1 minēja `_SaeimaParser` klasi — **tāda neeksistē**, ignorēt.
- **Darbība:** Dzēst funkciju (jāpārbauda faktiskais līniju skaits, lasot kodu).

### A3. `_fetch_politicians_page()` — atstāts "for now" pirms 9 dienām
- **Vieta:** [src/generate.py:1208](../../src/generate.py) (~88 līn.)
- **Verifikācija:** `docs/superpowers/plans/2026-04-07-ui-restructuring.md:959` — "Keep ... for now — it may be useful for data access." Pēc 9 dienām nav neviena izsaucēja.
- **Darbība:** Dzēst.

### A4. Dublēts sekcijas virsraksts
- **Vieta:** [src/generate.py:1600,1603](../../src/generate.py) — `# ── Generator ──────` divreiz pēc kārtas.
- **Darbība:** Dzēst vienu (kopā ar tukšajām rindām).

### A5. Pydantic modeļi — `PoliticianProfile`, `ScrapedContent`
- **Vieta:** [src/models.py:7,33](../../src/models.py)
- **Verifikācija:** Tikai `tests/test_models.py` importē. Reālais kods strādā ar `dict` (SQLite rindas). `docs/architecture.md:62` modeļus piemin, bet kā Pydantic kontraktu sarakstu, ne aktīvu lietojumu.
- **Riska piezīme:** Var būt iecerēti kā nākotnes API līmenis. **Pirms dzēšanas — apstiprināt ar lietotāju.** Sk. Fāze 3.

### A6. `store_content()` wrapper — orfans
- **Vieta:** [src/ingest.py:1053](../../src/ingest.py)
- **Verifikācija:** Tikai definīcija + `docs/superpowers/plans/2026-04-09-document-politicians-junction.md` (vēsturisks plāns). Nav izsaucēju `src/`, `tests/`, `wiki/operations/`. Jāuzmanās — nosaukums vispārīgs, varbūt aizvietots ar `insert_document()`.
- **Darbība:** Apstiprināt ar lietotāju + dzēst (Fāze 3).

### A7. `delete_politician_data()` — varbūtīgs admin tool
- **Vieta:** [src/db.py:826](../../src/db.py)
- **Verifikācija:** Tikai definīcija + plāna doc atsauces. Nav izsaucēju.
- **Darbība:** **Apstiprināt ar lietotāju** — admin/manuāls operāciju rīks. Ja apstiprināts kā nelietots — dzēst (Fāze 3).

### A8. Ruff safe-fix — neizmantoti imports/argumenti/cikla mainīgie
33 atradumi `tests/` un `scripts/`. Visi mehāniski.

```
scripts/patch_twikit.py:16   F401  importlib
src/csp/client.py:96         B007  loop var `s`
src/csp/insights.py:5        ARG001 `direction`
src/generate.py:2186         ARG001 `freq`
src/ingest.py:94             ARG001 `source_url`
src/ingest.py:489            ARG001 `fetcher_mode`
src/ingest.py:605            ARG002 `attrs` (HTMLParser API — VERIFICĒT vai signature obligāta!)
src/knab.py:370              ARG001 `per_page`
src/routine.py:51            ARG001 `db`
src/saeima.py:322            B007  loop var `vote_value`
src/wiki_lint.py:143         B007  loop var `slug`
src/x_scraper.py:72,132      B007  loop var `attempt`
tests/test_analyze.py:25,204 F841 `yesterday`, `result`
tests/test_calibration.py:4  F401  numpy
tests/test_cross_check.py:4  F401  numpy
tests/test_embeddings.py:3   F401  pytest
tests/test_generate.py:3     F401  pytest
tests/test_ingest.py:96-159  ARG001 `fixture_db` × 4
tests/test_knab.py:42        ARG005 lambda `conn`
tests/test_knab.py:375       F401  sqlite3
tests/test_models.py:4       F401  datetime
tests/test_routine.py:3      F401  sqlite3
tests/test_tools.py:4        F401  pytest
tests/test_topic_map.py:3    F401  pytest
tests/test_wiki.py:2-3       F401  pytest, Path
tests/test_x_pool.py:4       F401  AsyncMock, patch
```

**Brīdinājums par `ingest.py:605` un `routine.py:51`:** Šie ir API-kontraktu argumenti (HTMLParser callback / routine check signature). Pirms `ruff --fix` palaišanas pārbaudīt vai aizvietošana ar `_` neierīkos signatūras kontraktu. Ja jā — pievienot `# noqa: ARG001` komentāru, ne dzēst.

### A9. Saeima `process_vote_snapshot()`, `store_session()`, `get_session_votes_summary()`
- **Vieta:** [src/saeima.py:457,794,841](../../src/saeima.py)
- **Verifikācija:** `Grep` rāda tikai definīcijas. **BET** `docs/architecture.md:92,200` `process_vote_snapshot` aprakstīts kā galvenā Saeima funkcija pipeline diagrammā.
- **Diagnostika nepieciešama:** Vai Saeima rutīna ražošanā strādā? Ja `process_vote_snapshot` arhitektūrā uzskaitīts, bet to neviens neizsauc, tas ir **nepilnīgas integrācijas BUG**, ne dead code.
- **Darbība:** Sk. Fāze 3 — vispirms izpētīt, vai `@saeima-tracker` agents (`. claude/agents/saeima-tracker.md`) faktiski izmanto šīs funkcijas, vai ir ekvivalenti src/saeima.py.

### NEDZĒŠ — v1 kļūdaini atzīmēja kā mirušus

| Funkcija | v1 statuss | Reāls statuss | Pierādījums |
|---|---|---|---|
| `wiki_sync()` | A3 dzēst | **AKTĪVS** | `wiki/operations/daily-routine.md:134` (rutīnas solis), `routine.py:_check_wiki_sync`, 6+ testi |
| `_append_log()` | A3 dzēst | **AKTĪVS** | `wiki_sync` palīgs |
| `init_saeima_tables()` | A4 dzēst | **AKTĪVS** | `tests/test_saeima.py:18,35` |
| `fetch_all` (KNAB) | A5 dzēst | **AKTĪVS** | `wiki/operations/knab-guide.md:9` |
| `get_party_summary` | A5 dzēst | **AKTĪVS** | `knab-guide.md:12`, `tests/test_knab.py:531-549` |
| `get_top_donors` | A5 dzēst | **AKTĪVS** | `knab-guide.md:13` |
| `get_alerts` | A5 dzēst | **AKTĪVS** | `knab-guide.md:14` |
| `fetch_declaration_details` | A5 dzēst | **AKTĪVS** | KNAB workflow daļa, izsaukts caur `fetch_all` ķēdi |
| `store_tension()` | A7 dzēst | **AKTĪVS** | `wiki/operations/daily-routine.md:101-102` |
| `read_ingest_log()` | A7 dzēst | **AKTĪVS** | `daily-routine.md:27`, `wiki-tools.md:171`, tests |

---

## B. Korektuma riski

### B1. Timezone — `datetime.now()` / `date.today()` → Latvija UTC+3

**CLAUDE.md noteikums #7 pārkāpts.** Pilns saraksts (v1 izlaida 3 vietas):

```
src/analyze.py:71,106,142     cutoff = (datetime.now() - timedelta(days=days)).isoformat()
src/briefs.py:14              date = date or datetime.now().strftime("%Y-%m-%d")
src/briefs.py:294             today = datetime.now()
src/confidence_drift.py:24,25 cutoff = (datetime.now() - ...)
src/generate.py:270           cutoff_7d = (date.today() - timedelta(days=7))...
src/generate.py:1676          today = date.today()
src/generate.py:2361          today = date.today().isoformat()
src/ingest.py:982             cutoff = (datetime.now() - timedelta(days=days)).isoformat()  ← v1 IZLAISTS
src/tools.py:56               cutoff = (datetime.now() - timedelta(days=days)).isoformat()  ← v1 IZLAISTS
src/tools.py:198              params.append(date.today().isoformat())                       ← v1 IZLAISTS
src/routine.py:109            target_date = datetime.now().strftime("%Y-%m-%d")             ← v1 IZLAISTS
```

**Risks:** Vakaros LV laikā (UTC+3) UTC vēl iepriekšējā diena → cutoff izlaiž jaunākos dokumentus.

**Sarežģījums:** `now_lv()` (db.py:17) atgriež **stringu** (`"%Y-%m-%d %H:%M:%S"`), nevis `datetime` objektu. Ievietošana ar `now_lv()` vienā vietā nestrādās — vajag `datetime` aritmētikai. **Risinājums:** pievienot helper `now_lv_dt() -> datetime` un `today_lv() -> date`.

### B2. `logger.error` `except` blokā bez stack trace

**Pilns saraksts (v1 minēja tikai 3 no 7 vietām):**

```
src/x_scraper.py:91   logger.error("fetch_user_tweets: @%s lookup error — %s", handle, e)
src/x_scraper.py:103  logger.error("fetch_user_tweets: API error for @%s — %s", handle, e)
src/x_scraper.py:106  logger.error("fetch_user_tweets: unexpected error for @%s ...", ...)
src/x_scraper.py:152  logger.error("fetch_user_replies: @%s lookup error — %s", handle, e)
src/x_scraper.py:173  logger.error("fetch_user_replies: API error for @%s — %s", handle, e)
src/x_scraper.py:176  logger.error("fetch_user_replies: unexpected error for @%s ...", ...)
src/x_scraper.py:207  logger.error("  @%s: failed (%s: %s), skipping", ...)
src/x_mentions.py:148 logger.error("fetch_mentions: unexpected error — %s: %s", ...)
```

**Darbība:** Aizvietot ar `logger.exception(...)` (automātiski iekļauj traceback).

---

## C. Strukturālas iespējas (NĀKOTNEI — netiek izpildītas šajā plānā)

| ID | Apraksts | Vieta | Sarežģītība |
|---|---|---|---|
| C1 | `generate.py` (2502 līn.) sadalīt | `src/generate.py` | Liela |
| C2 | `ingest.py` `_ingest_source` (kompl. 18) sadalīt | `src/ingest.py:1105` | Vidēja |
| C3 | `saeima.py` `parse_vote_snapshot` (kompl. 20) sadalīt | `src/saeima.py:249` | Vidēja |
| C4 | `os.path` → `pathlib.Path` (~40 vietas) | Daudz failu | Maza |
| C5 | `Optional[X]` → `X \| None` (~80 vietas, ruff UP045 `--fix`) | `db.py`, `models.py`, ... | Maza, mehāniska |

---

## Izpildes fāzes

CLAUDE.md noteikums #1: ≤5 faili fāzē, verifikācija starp fāzēm, gaidīt apstiprinājumu.

---

### Fāze 1: Drošās dzēšanas + ruff safe-fix

**Faili (5):** `src/generate.py`, `src/ingest.py`, `tests/` (vairāki imports), `scripts/patch_twikit.py`, `src/csp/`

**Risks:** Zems. Visi atradumi verificēti pret 4 slāņiem.

#### Task 1.1: Dzēst `_load_ideology()`

**Files:**
- Modify: `src/generate.py:1584` (~6 līn. dzēst)

- [ ] **Step 1:** Lasīt `src/generate.py` rindas 1580-1595, lai redzētu funkcijas robežas

- [ ] **Step 2:** Dzēst funkciju `_load_ideology()` un tās `"""docstring"""`

- [ ] **Step 3:** Verificēt importu — `Grep "CONTENT_DIR" src/generate.py` (ja tikai šī funkcija to lieto, dzēst arī importu/konstanti)

- [ ] **Step 4:** Run `python -c "from src.generate import generate_public_site; generate_public_site()"` — ekspektē: bez kļūdām, output/ ģenerējas

- [ ] **Step 5:** Commit
  ```bash
  git add src/generate.py
  git commit -m "chore: remove orphan _load_ideology() (no template references)"
  ```

#### Task 1.2: Dzēst `_fetch_politicians_page()`

**Files:**
- Modify: `src/generate.py:1208` (~88 līn. dzēst)

- [ ] **Step 1:** Lasīt `src/generate.py` rindas 1205-1300, identificēt funkcijas precīzās robežas

- [ ] **Step 2:** Pirms dzēšanas — `Grep "_fetch_politicians_page" .` visā repo (apstiprināt: tikai definīcija + 1 vēsturiska plāna atsauce)

- [ ] **Step 3:** Dzēst funkciju

- [ ] **Step 4:** Run `pytest tests/test_generate.py -v` un `python -c "from src.generate import generate_public_site; generate_public_site()"`

- [ ] **Step 5:** Commit
  ```bash
  git add src/generate.py
  git commit -m "chore: remove _fetch_politicians_page() (orphaned 9 days, no callers)"
  ```

#### Task 1.3: Dzēst dublētu sekcijas virsrakstu

**Files:**
- Modify: `src/generate.py:1600,1603`

- [ ] **Step 1:** Lasīt `src/generate.py` rindas 1598-1606

- [ ] **Step 2:** Dzēst rindas 1602-1603 (otrais `# ── Generator ──` virsraksts + tukšā rinda)

- [ ] **Step 3:** Commit
  ```bash
  git add src/generate.py
  git commit -m "style: remove duplicate section header in generate.py"
  ```

#### Task 1.4: Dzēst `_parse_saeima_votes()`

**Files:**
- Modify: `src/ingest.py:624` (jāizmēra)

- [ ] **Step 1:** Lasīt `src/ingest.py` rindas 620-700, atrast funkcijas robežas

- [ ] **Step 2:** Pārbaudīt vai funkcija nereferē `_SaeimaParser` (tāda nav) vai citas iekšējas klases

- [ ] **Step 3:** Dzēst funkciju

- [ ] **Step 4:** Run `pytest tests/test_ingest.py -v`

- [ ] **Step 5:** Commit
  ```bash
  git add src/ingest.py
  git commit -m "chore: remove _parse_saeima_votes() (replaced by src/saeima.py)"
  ```

#### Task 1.5: Ruff safe-fix uz `tests/` un `scripts/`

**Files:** `tests/test_*.py` (8 faili), `scripts/patch_twikit.py`

- [ ] **Step 1:** Run `.venv/Scripts/python.exe -m ruff check --fix --select F401,F841,B007 tests/ scripts/`

- [ ] **Step 2:** Run `pytest tests/ -q` — ekspektē: visi testi paiet (vai paliek to pašu skaitu kā pirms)

- [ ] **Step 3:** Pārskatīt `git diff` — pārliecināties, ka neviens būtisks imports nav noņemts

- [ ] **Step 4:** Commit
  ```bash
  git add tests/ scripts/
  git commit -m "chore: ruff safe-fix unused imports/vars in tests/ and scripts/"
  ```

#### Task 1.6: Ruff safe-fix uz `src/` ar uzmanību

**Files:** `src/csp/client.py`, `src/csp/insights.py`, `src/wiki_lint.py`, `src/x_scraper.py`, `src/saeima.py`

- [ ] **Step 1:** **Manuāli pārskatīt** `src/ingest.py:605` `attrs` un `src/routine.py:51` `db` — vai signature ir API kontrakts? Ja jā — pievienot `# noqa: ARG001 - HTMLParser API contract` (vai analogu) ne `--fix`

- [ ] **Step 2:** Run `ruff check --fix --select B007 src/csp/ src/wiki_lint.py src/x_scraper.py src/saeima.py` (TIKAI loop var fixes, kuras drošas)

- [ ] **Step 3:** Atsevišķi pārskatīt `ARG001` atradumus `src/csp/insights.py:5`, `src/generate.py:2186`, `src/ingest.py:94,489`, `src/knab.py:370` — katra gadījumā novērtēt vai tas ir API kontrakts

- [ ] **Step 4:** Run `pytest tests/ -q`

- [ ] **Step 5:** Commit
  ```bash
  git add src/
  git commit -m "chore: ruff safe-fix loop vars in src/ (no API contract changes)"
  ```

**Fāze 1 verifikācija:**
```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check src/ scripts/ tests/
.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

**🛑 GAIDĪT LIETOTĀJA APSTIPRINĀJUMU PIRMS FĀZES 2.**

---

### Fāze 2: Korektuma migrācija (B1, B2)

**Faili (5):** `src/db.py`, `src/analyze.py`, `src/briefs.py`, `src/confidence_drift.py`, `src/x_scraper.py`

**Risks:** Vidējs — jāmaina datuma loģika daudzās vietās. TDD approach.

#### Task 2.1: Pievienot `now_lv_dt()` un `today_lv()` helperus

**Files:**
- Modify: `src/db.py` (pievienot 2 funkcijas pēc `now_lv()`)
- Test: `tests/test_db.py` (pievienot 2 testus)

- [ ] **Step 1: Write the failing test**

  ```python
  # tests/test_db.py
  from datetime import datetime, date
  from src.db import now_lv_dt, today_lv

  def test_now_lv_dt_returns_datetime():
      result = now_lv_dt()
      assert isinstance(result, datetime)
      assert result.tzinfo is None  # naive LV-local datetime

  def test_today_lv_returns_date():
      result = today_lv()
      assert isinstance(result, date)
      # Should match the date portion of now_lv()
      from src.db import now_lv
      assert now_lv().startswith(result.isoformat())
  ```

- [ ] **Step 2: Run testu, lai pārliecinātos, ka neizdodas**
  ```bash
  pytest tests/test_db.py::test_now_lv_dt_returns_datetime -v
  ```
  Ekspektē: ImportError vai nav `now_lv_dt`

- [ ] **Step 3: Implementēt**

  ```python
  # src/db.py — pievienot pēc now_lv() rindā ~20
  def now_lv_dt() -> datetime:
      """Return current datetime as naive datetime in Latvia time (EEST/EET)."""
      return (datetime.now(timezone.utc) + _LV_OFFSET).replace(tzinfo=None)


  def today_lv() -> date:
      """Return current date in Latvia time."""
      return now_lv_dt().date()
  ```

  Importu papildināt: `from datetime import datetime, timezone, timedelta, date`

- [ ] **Step 4: Run testus**
  ```bash
  pytest tests/test_db.py -v
  ```
  Ekspektē: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add src/db.py tests/test_db.py
  git commit -m "feat: add now_lv_dt() and today_lv() helpers for timezone-correct date arithmetic"
  ```

#### Task 2.2: Migrēt `src/analyze.py`

**Files:**
- Modify: `src/analyze.py:71,106,142`

- [ ] **Step 1:** Lasīt `src/analyze.py:65-150` lai redzētu kontekstu

- [ ] **Step 2:** Atrast importu — pievienot `from src.db import now_lv_dt` (vai `from .db import now_lv_dt` atkarībā no esošā stila)

- [ ] **Step 3:** Aizvietot 3 vietas:
  ```python
  # PIRMS:
  cutoff = (datetime.now() - timedelta(days=days)).isoformat()
  # PĒC:
  cutoff = (now_lv_dt() - timedelta(days=days)).isoformat()
  ```

- [ ] **Step 4:** Run `pytest tests/test_analyze.py -v`

- [ ] **Step 5:** Commit
  ```bash
  git add src/analyze.py
  git commit -m "fix: use now_lv_dt() in analyze.py cutoffs (CLAUDE.md rule #7)"
  ```

#### Task 2.3: Migrēt `src/briefs.py`

**Files:**
- Modify: `src/briefs.py:14,294`

- [ ] **Step 1:** Lasīt kontekstu

- [ ] **Step 2:** Aizvietot:
  ```python
  # rinda 14:
  date = date or now_lv_dt().strftime("%Y-%m-%d")
  # rinda 294:
  today = now_lv_dt()
  ```

- [ ] **Step 3:** Run `pytest tests/ -k brief -v`

- [ ] **Step 4:** Commit

#### Task 2.4: Migrēt `src/confidence_drift.py`, `src/ingest.py`, `src/tools.py`, `src/routine.py`, `src/generate.py`

**Files:**
- Modify: `src/confidence_drift.py:24,25`
- Modify: `src/ingest.py:982`
- Modify: `src/tools.py:56,198`
- Modify: `src/routine.py:109`
- Modify: `src/generate.py:270,1676,2361`

- [ ] **Step 1:** Katrā failā: pievienot importu, aizvietot `datetime.now()` ar `now_lv_dt()`, `date.today()` ar `today_lv()`

- [ ] **Step 2:** Run pilns `pytest tests/ -q`

- [ ] **Step 3:** Run smoke: `python -c "from src.generate import generate_public_site; generate_public_site()"`

- [ ] **Step 4:** Commit (atsevišķi katram failam vai vienā ar skaidru ziņojumu)

#### Task 2.5: `logger.error` → `logger.exception` (B2)

**Files:**
- Modify: `src/x_scraper.py:91,103,106,152,173,176,207`
- Modify: `src/x_mentions.py:148`

- [ ] **Step 1:** Katrā vietā aizvietot `logger.error("...", ..., e)` ar `logger.exception("...", ...)`. **Svarīgi:** noņemt `e` no formatēšanas argumentiem, jo `exception` automātiski pievieno traceback.

  Piemērs:
  ```python
  # PIRMS:
  except Exception as e:
      logger.error("fetch_user_tweets: @%s lookup error — %s", handle, e)
  # PĒC:
  except Exception:
      logger.exception("fetch_user_tweets: @%s lookup error", handle)
  ```

- [ ] **Step 2:** Manuāli pārbaudīt katru gadījumu — vai `e` netiek lietots citur blokā (piem., re-raise kontekstam)

- [ ] **Step 3:** Run `pytest tests/test_x_pool.py -v` un attiecīgi mentions testus

- [ ] **Step 4:** Commit
  ```bash
  git commit -m "fix: use logger.exception() in except blocks for traceback (B2)"
  ```

**Fāze 2 verifikācija:**
```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check src/
# Smoke: routine + generate
```

**🛑 GAIDĪT APSTIPRINĀJUMU PIRMS FĀZES 3.**

---

### Fāze 3: Apstiprināmas dzēšanas (vajag lietotāja `OK`)

**Faili (≤5):** `src/db.py`, `src/ingest.py`, `src/models.py`, `tests/test_models.py`, `src/saeima.py`

**Risks:** Augsts — funkcijas var būt manuāli/admin tools vai nepilnīga integrācija.

#### Task 3.1: Pieprasīt apstiprinājumu katram

**Lietotājam jāapstiprina katrs atsevišķi:**

1. `delete_politician_data()` (db.py:826) — admin tool? Ja jā: paturēt + dokumentēt `wiki/operations/`. Ja nē: dzēst.
2. `store_content()` (ingest.py:1053) — wrapper aizvietots ar `insert_document()`? Apstiprināt + dzēst.
3. `PoliticianProfile`, `ScrapedContent` (models.py:7,33) — nākotnes API kontrakts? Ja jā: paturēt + pievienot izsaucēju vai komentāru. Ja nē: dzēst + dzēst `tests/test_models.py:TestPoliticianProfile`, `TestScrapedContent`.

#### Task 3.2: Saeima diagnostika (PIRMS A9 dzēšanas)

**Šis NAV dzēšanas uzdevums — tas ir izpētes uzdevums.**

- [ ] **Step 1:** Lasīt `.claude/agents/saeima-tracker.md` un `wiki/operations/weekly-routine.md`

- [ ] **Step 2:** Atrast vai `process_vote_snapshot`, `store_session`, `get_session_votes_summary` ir izsaukti caur agentu prompta `Bash`/`Python` instrukcijām

- [ ] **Step 3:** Pārbaudīt vai SQLite `saeima_*` tabulas faktiski satur datus (`sqlite3 data/atmina.db "SELECT COUNT(*) FROM saeima_sessions"`)

- [ ] **Step 4: Lēmums:**
  - Ja Saeima rutīna **darbojas** ar šīm funkcijām (caur agentu) — atstāt + pievienot pieminējumu `wiki/operations/`
  - Ja Saeima rutīna ir **nepilnīga** (funkcijas iecerētas, bet nekad nepieslēgtas) — tas ir **bug**, ne dead code. Atvērt atsevišķu plānu integrācijai.
  - Ja Saeima rutīna ir **aizstāta** ar citu pieeju — dzēst funkcijas (~120 līn.)

#### Task 3.3: Dzēst apstiprinātos

Pēc apstiprinājuma — viens commit katrai funkcijai.

**Fāze 3 verifikācija:**
```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

**🛑 GAIDĪT APSTIPRINĀJUMU PIRMS FĀZES 4.**

---

### Fāze 4: `generate_statistika` lēmums

**Konteksts:** [src/generate.py:2078](../../src/generate.py) (~247 līn.) + `templates/statistika*.html.j2` + `templates/base.html.j2:44` navigācija + `data/csp.db`, `data/events.yaml`. Output `output/atmina/statistika/` netiek ģenerēts → tab uz `statistika.html` ražošanā 404.

**Lēmums vajadzīgs lietotājam:**

**(a) Pievienot:**
- Pievienot `generate_statistika()` izsaukumu `generate_public_site()` cikla beigās (vai atsevišķā `wiki/operations/monthly-routine.md` solī)
- Atjaunināt CLAUDE.md komandu sarakstu
- Nesāk ietekmes

**(b) Noņemt:**
- Dzēst `generate_statistika()` (~247 līn.)
- Dzēst `templates/statistika.html.j2`, `templates/statistika-detail.html.j2` (~600 līn.)
- Noņemt navigācijas saiti `templates/base.html.j2:44`
- Apsvērt: dzēst `data/csp.db`, `data/events.yaml` ja nav citu lietotāju (pārbaudīt `Grep "csp.db|events.yaml"` pirms)
- Iespējams dzēst `src/csp/` direktoriju (apstiprināt)

**Pēc lēmuma — atsevišķs commit.**

---

## Verifikācijas komandas (jāpalaiž pēc katras fāzes)

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check src/ scripts/ tests/
.venv/Scripts/python.exe -m vulture src/ scripts/ --min-confidence 80
.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

---

## Apkopots ietekmes novērtējums

| Fāze | Faili | Kods modificēts/dzēsts | Risks | Vērtība |
|---|---|---|---|---|
| 1 | 5+ | ~100 līn. dzēstas + ~25 ruff fix | Zems | Augsta — uzreiz tīrāks lints |
| 2 | 5 | ~15 vietas mainītas (+helper funkcijas) | Vidējs | Augsta — fix korektuma bugs |
| 3 | ≤5 | 0 vai ~150 līn. (atkarībā no apstiprinājumiem) | Augsts | Vidēja |
| 4 | 3-5 | 0 vai ~847 līn. | Atkarīgs | Atkarīgs no lēmuma |

**Kopā potenciāli noņemts:** ~250 līn. mirušā koda + 1 timezone bug klases (B1) izlabota + logging traceback uzlabojums (B2).

**Salīdzinājumam, v1 plāns:** apgalvoja ~650 līn., bet ~400 no tām bija aktīvi izsauktas funkcijas, kuras nekad nedrīkst dzēst.

---

## Atbildības

- **Kods:** `claude/xenodochial-bassi` branch
- **Apstiprinājuma punkti:** Fāzes 2, 3, 4 sākumā
- **Fallback:** Katram task `git checkout` neveiksmes gadījumā (CLAUDE.md noteikums #9)
- **Edit safety:** CLAUDE.md noteikums #7 — pirms KATRA edit re-read fails, pēc edit re-read lai apstiprinātu
