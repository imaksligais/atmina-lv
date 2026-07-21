# Lieks kods un optimizācijas — analīze un izpildes plāns

**Datums:** 2026-04-16
**Branch:** `claude/xenodochial-bassi`
**Mērķis:** Noņemt mirušo/orfana kodu un izlabot korektuma riskus, kas atklāti `ruff` + `vulture` + manuālā references analīzē.

---

## Konteksts

Repo statistika brīdī, kad veikta analīze:
- `src/` kopā 11 813 līniju, 28 moduļi
- `generate.py` 2502 līn., `ingest.py` 1415 līn., `db.py` 894 līn., `saeima.py` 875 līn., `knab.py` 854 līn., `wiki.py` 759 līn.
- 21 Jinja2 template `templates/`
- Ruff (default) — 0 kļūdu jau labotas; ar plašākiem rule sets (`F,E,W,B,C90,UP,SIM,ARG,PTH,RET,TRY,PL`) — 697 atrasti, no kuriem **patiesi rīcības iespējamie ir ~50**
- Vulture min-confidence 60 — 65 atradumi (lielākā daļa false positives, jo agentu izsauktās MCP-style funkcijas no `tools.py` un publiskās analīzes funkcijas no `analyze.py`/`briefs.py`/`social.py` ir izsauktas dinamiski caur agentu instrukcijām)

Konteksta filtrs (kas NAV uzskatīts par "lieku"):
- `src/tools.py` funkcijas (`save_analysis`, `store_context_note`, `query_claims`, utt.) — agentu MCP rīki, izsauc dinamiski
- `src/analyze.py`/`briefs.py`/`social.py` `fetch_*`/`generate_*` — izsauc no agentu prompt-iem un CLI komandām, kas dokumentētas `wiki/operations/`
- `src/routine.py:print_routine` — dokumentēts CLAUDE.md kā komanda
- `src/coalition.party_status` — dokumentēts CLAUDE.md noteikumā #14
- KNAB `fetch_all`, `get_party_summary` — dokumentēti `wiki/` un, iespējams, manuāli izsaukti

---

## A. Mirušais kods — drošas dzēšanas kandidāti

### A1. `_load_ideology()` — [src/generate.py:1584](../../src/generate.py)
- **Apraksts:** Ielādē un renderē `content/ideology.md`.
- **Verifikācija:** `grep -rn _load_ideology . --include="*.py"` → tikai definīcija. `content/ideology.md` neeksistē (`ls content/ideology.md` → not found).
- **Darbība:** Dzēst funkciju (~10 līn.).

### A2. `_parse_saeima_votes()` — [src/ingest.py:624](../../src/ingest.py)
- **Apraksts:** Vecs Saeima balsojumu parser, kas tagad aizvietots ar `src/saeima.py` pipeline.
- **Verifikācija:** `grep -rn _parse_saeima_votes . --include="*.py"` → tikai definīcija.
- **Darbība:** Dzēst funkciju + iekšējo HTML parser klasi `_SaeimaParser` ja tā tiek izmantota tikai šeit (~30 līn. + verificēt klases lietojumu pirms dzēšanas).

### A3. `_append_log()` + `wiki_sync()` — [src/wiki.py:600,609](../../src/wiki.py)
- **Apraksts:** Wiki sync ārējam ceļam.
- **Verifikācija:** `grep -rn` → tikai definīcijas. Doc references `wiki/` — tikai apraksts, nav izsaucēju.
- **Darbība:** Dzēst (~30 līn.).

### A4. Saeima orfanas — [src/saeima.py:84,457,794,841](../../src/saeima.py)
- `init_saeima_tables()` — vai izsauc `db.py` `init_db()`? Verificēt: ja jā, šī ir nederīga (sk. `init_db` `db.py`).
- `store_session()` — neviens nesauc.
- `process_vote_snapshot()` — neviens nesauc.
- `get_session_votes_summary()` — neviens nesauc.
- **Verifikācija:** `grep -rn <name> . --include="*.py"` → tikai definīcijas. Pirms dzēšanas pārbaudīt, vai Saeima rutīna no `wiki/operations/` neuzskaita kā ārēju izsaukumu.
- **Darbība:** Pārbaudīt `wiki/operations/weekly-routine.md`. Ja nav atsauču — dzēst (~120 līn.).

### A5. KNAB orfanas — [src/knab.py:639,736,765,796,828](../../src/knab.py)
- `fetch_declaration_details()`, `fetch_all()`, `get_party_summary()`, `get_top_donors()`, `get_alerts()`
- **Verifikācija:** Liela varbūtība, ka šīs ir CLI/manuālas izsaukšanas. **Pirms dzēšanas — pajautāt lietotājam.**
- **Darbība:** Apstiprināt katru atsevišķi. Ja apstiprināts kā nelietots — dzēst (~190 līn.).

### A6. `_fetch_politicians_page()` — [src/generate.py:1208](../../src/generate.py)
- **Apraksts:** Datu fetcher iznīcinātam tabam.
- **Verifikācija:** `docs/superpowers/plans/2026-04-07-ui-restructuring.md:959` skaidri saka: "Keep the `_fetch_politicians_page` function for now — it may be useful for data access." 9 dienas vēlāk neviens to neizmanto.
- **Darbība:** Dzēst (~88 līn.).

### A7. DB/ingest/log orfanas
- `delete_politician_data()` — [src/db.py:826](../../src/db.py) — varbūt admin tool. Pārbaudīt vai pieminēts `wiki/operations/`.
- `store_tension()` — [src/db.py:768](../../src/db.py) — `tensions` tabula vēl tiek lietota? `grep -rn "tensions" src/`
- `store_content()` — [src/ingest.py:1053](../../src/ingest.py) — wrapper bez izsaucējiem.
- `read_ingest_log()` — [src/ingest_log.py:82](../../src/ingest_log.py) — pretpols `append_ingest_log` ir izsaukts.
- **Darbība:** Verificēt katru → dzēst (~80 līn.).

### A8. Pydantic modeļi — `PoliticianProfile`, `ScrapedContent` — [src/models.py:7,33](../../src/models.py)
- **Verifikācija:** Tikai `tests/test_models.py` tos importē. Reālajā kodā nav lietoti — visus politiķus glabā kā `dict` SQLite rindas.
- **Darbība:** Dzēst klases UN to testus `tests/test_models.py:TestPoliticianProfile`, `TestScrapedContent` (~30 līn. modeļi + ~50 līn. testi).
- **Riska piezīme:** Šie modeļi var būt paredzēti kā nākotnes API līmenis. Apstiprināt ar lietotāju.

### A9. Dublētu sekciju virsraksti — [src/generate.py:1600,1603](../../src/generate.py)
- `# ── Generator ──────` rindā 1600 un 1603. Dzēst vienu.

### A10. Ruff F401/ARG/B007 — neizmantoti imports/argumenti
33 atradumi (sk. zemāk pilnu sarakstu). Visi safe-fix ar `ruff check --fix`.

**Pilns saraksts:**
```
scripts/patch_twikit.py:16  F401  importlib
src/csp/client.py:96        B007  loop var `s`
src/csp/insights.py:5       ARG001 `direction`
src/generate.py:2186        ARG001 `freq`
src/ingest.py:94            ARG001 `source_url`
src/ingest.py:489           ARG001 `fetcher_mode`
src/ingest.py:605           ARG002 `attrs` (HTMLParser API — pārbaudīt vai parameter signature obligāts)
src/knab.py:370             ARG001 `per_page`
src/routine.py:51           ARG001 `db`
src/saeima.py:322           B007  loop var `vote_value`
src/wiki_lint.py:143        B007  loop var `slug`
src/x_scraper.py:72,132     B007  loop var `attempt`
tests/test_analyze.py:25,204 F841 `yesterday`, `result`
tests/test_calibration.py:4 F401  numpy
tests/test_cross_check.py:4 F401  numpy
tests/test_embeddings.py:3  F401  pytest
tests/test_generate.py:3    F401  pytest
tests/test_ingest.py:96-159 ARG001 `fixture_db` × 4 (tests, kas nepiemēro fixture)
tests/test_knab.py:42       ARG005 lambda `conn`
tests/test_knab.py:375      F401  sqlite3
tests/test_models.py:4      F401  datetime
tests/test_routine.py:3     F401  sqlite3
tests/test_tools.py:4       F401  pytest
tests/test_topic_map.py:3   F401  pytest
tests/test_wiki.py:2-3      F401  pytest, Path
tests/test_x_pool.py:4      F401  AsyncMock, patch
```

---

## B. Korektuma riski

### B1. `datetime.now()` / `date.today()` vietā `now_lv()`
**CLAUDE.md noteikums #7 pārkāpts.** Latvija UTC+3 — visiem laikspieliem jāizmanto `now_lv()` no `src/db.py`.

Atrašanās:
- [src/analyze.py:71,106,142](../../src/analyze.py) — cutoff aprēķini
- [src/briefs.py:14,294](../../src/briefs.py) — datuma noklusējums
- [src/confidence_drift.py:24,25](../../src/confidence_drift.py)
- [src/generate.py:270,1676,2361](../../src/generate.py) — `cutoff_7d`, `today`, sitemap

**Risks:** Vakaros LV laikā UTC vēl iepriekšējā diena → cutoff izlaiž jaunākos dokumentus.

**Darbība:** Aizvietot `datetime.now()` ar `now_lv()` un `date.today()` ar `now_lv().date()`. Verificēt ar testiem.

### B2. `generate_statistika` — orfana implementācija
- [src/generate.py:2078](../../src/generate.py) — 247 līniju funkcija
- Templati: `templates/statistika.html.j2`, `templates/statistika-detail.html.j2`
- Navigācija: `templates/base.html.j2:44` saite uz `statistika.html`
- Dati: `data/csp.db`, `data/events.yaml` eksistē
- **Output `output/atmina/statistika/` netiek ģenerēts** → tab esošajā ražošanā 404
- **Lēmums vajadzīgs:** vai (a) pievienot izsaukumu CLAUDE.md komandai/rutīnai, vai (b) noņemt funkciju + templates + navigāciju

### B3. `logger.error` `except` blokā bez stack trace
- [src/x_scraper.py:173,176,207](../../src/x_scraper.py)
- [src/x_mentions.py](../../src/x_mentions.py) (vairākas vietas)

**Darbība:** Aizvietot ar `logger.exception(...)` — automātiski iekļauj traceback. Ražošanas debug ievērojami uzlabosies.

---

## C. Strukturālas iespējas (atsevišķi plāni nākotnē)

| ID | Apraksts | Vieta | Sarežģītība |
|---|---|---|---|
| C1 | `generate.py` (2502 līn.) sadalīt → `generate/site.py`, `generate/data_fetchers.py`, `generate/assets.py`, `generate/statistika.py` | `src/generate.py` | Liela — atsevišķs plāns ar fāzēm |
| C2 | `ingest.py` (1415 līn.) `_ingest_source` (kompl. 18) un `_scrape_web_articles` (13) sadalīt | [src/ingest.py:1105,431](../../src/ingest.py) | Vidēja |
| C3 | `saeima.py` `parse_vote_snapshot` (kompl. 20, 74 stmts) sadalīt parsing/normalize | [src/saeima.py:249](../../src/saeima.py) | Vidēja |
| C4 | `os.path` → `pathlib.Path` (~40 vietas — `calibration.py`, `routine.py`, `preflight.py`, `ingest.py`) | Daudz failu | Maza, mehāniska |
| C5 | `Optional[X]` → `X \| None` (~80 vietas, ruff UP045) | `db.py`, `models.py`, `saeima.py`, `generate.py` | Maza, mehāniska — `ruff --fix` |

**Šajā plānā C-grupa NETIEK izpildīta** — tikai dokumentēta nākotnei.

---

## Izpildes fāzes

CLAUDE.md noteikums #1: katra fāze ≤5 faili, verifikācija starp fāzēm, gaidīt apstiprinājumu.

### Fāze 1 — Drošas safe-fix dzēšanas (zems risks)
**Faili (5):** `src/generate.py`, `src/wiki.py`, `src/ingest.py`, `tests/` (vairāki imports — viens commit)

1. A1 — `_load_ideology()` dzēst
2. A6 — `_fetch_politicians_page()` dzēst
3. A9 — dublētais sekcijas virsraksts
4. A10 — palaist `ruff check --fix --select F401,F841,B007,ARG` uz `tests/` un `scripts/`
5. **Verifikācija:** `pytest tests/ -q` + `ruff check src/ scripts/ tests/`

### Fāze 2 — Mirušais kods src/ (vidējs risks — verificēt ārējos izsaucējus)
**Faili (≤5):** `src/ingest.py`, `src/wiki.py`, `src/db.py`, `src/ingest_log.py`, `src/saeima.py`

Pirms dzēšanas:
- Pārbaudīt `wiki/operations/*.md` katrai funkcijai
- Pārbaudīt agentu prompt failus `.claude/agents/*.md`
- **Apstiprināt ar lietotāju katru atsevišķi**

1. A2, A3, A4, A7 — pa funkcijai komitējot
2. **Verifikācija:** `pytest tests/ -q` + manuāla rutīnas pārbaude

### Fāze 3 — KNAB un Pydantic modeļi (vajag lietotāja apstiprinājumu)
**Faili (2-3):** `src/knab.py`, `src/models.py`, `tests/test_models.py`

1. A5 — apstiprināt katru KNAB funkciju
2. A8 — apstiprināt Pydantic modeļus
3. **Verifikācija:** `pytest tests/ -q`

### Fāze 4 — Korektuma fix (B1, B3)
**Faili (5):** `src/analyze.py`, `src/briefs.py`, `src/confidence_drift.py`, `src/generate.py`, `src/x_scraper.py`

1. B1 — `now_lv()` migrācija
2. B3 — `logger.error` → `logger.exception`
3. **Verifikācija:** `pytest tests/ -q`. Manuāli pārbaudīt cutoff datus testos.

### Fāze 5 — `generate_statistika` lēmums (atsevišķi)
**Lēmums vajadzīgs lietotājam:**
- (a) Pievienot izsaukumu CLAUDE.md komandai un rutīnai (mēneša?), atstājot funkciju
- (b) Noņemt funkciju (~247 līn.), templates (~600 līn.), navigāciju, dzēst `data/csp.db` un `data/events.yaml` ja nav citu lietotāju

---

## Verifikācijas komandas

```bash
# Pēc katras fāzes:
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check src/ scripts/ tests/

# Mirušā koda atkārtota analīze:
.venv/Scripts/python.exe -m vulture src/ scripts/ --min-confidence 80

# Smoke tests:
.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

---

## Apkopots ietekmes novērtējums

| Fāze | Faili | Līnijas dzēstas | Risks | Vērtība |
|---|---|---|---|---|
| 1 | 5 | ~120 | Zems | Augsta — uzreiz tīrāks lints |
| 2 | 5 | ~260 | Vidējs | Augsta — `saeima.py`/`ingest.py` mazāks |
| 3 | 3 | ~270 | Augsts (vajag apst.) | Vidēja |
| 4 | 5 | 0 (modifikācijas) | Vidējs | Augsta — korektuma fix |
| 5 | TBD | -847 vai 0 | Zems | Atkarīgs no lēmuma |

**Kopā potenciāli noņemts:** ~650 līniju mirušā koda + 1 reāls korektuma bug klases (B1) izlabots.

---

## Atbildības

- **Kods:** `claude/xenodochial-bassi` branch
- **Apstiprinājuma punkti:** Fāzes 2, 3, 5 sākumā
- **Fallback:** Katrai fāzei `git checkout` neveiksmes gadījumā (CLAUDE.md noteikums #9)
