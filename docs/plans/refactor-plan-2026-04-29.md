# Atmiņas refaktoringa plāns — 2026-04-29

**Statuss 2026-04-30 (post F3g — Fāze 3 PILNĪBĀ PABEIGTA):** Fāzes 0, 1, 2, 3 (F3a-F3g), 4 PAVEIKTAS un mergētas master. **F3 fully closed** — `generate.py` 4250 → 173 LOC (-96%); 17 src/render/* moduļi; kanoniskais publiskais ceļš `from src.render import generate_public_site`. Atlikusi tikai: F5 (atlikt līdz DDL).
- Fāze 0 — drošības tīkls — PR #1, commit `b0f9871`
- Fāze 1 — matcher izvilkšana — PR #2, commit `4f4d25d`
- Fāze 2 — schema.sql izvilkšana — PR #3, commit `94466aa`
- Doc sync (CLAUDE.md, wiki/CHANGELOG, inventory) — commit `0b07027`
- Fāze 4 — saeima.py → src/saeima/ pakete — PR #4, merge commit `b341d4e` (6 commits: char fixtures + legacy rename + schema extract + 4-module atomic split + doc sync + review cleanup)
- Fāze 3a — generate.py 4250 → 3733 LOC; `src/render/_common.py` + `src/render/contradictions.py` izvilkti ar byte-identity char tests — PR #5, commit `3d06e05`
- Fāze 3-prep — char-fixture deterministisms (`ATMINA_ASSETS_VERSION`) + 4 leaf helpers + 2 const promovēti — PR #6, merge `dbed1a0` (3 commit-i)
- Fāze 3b — generate.py 3699 → 3198 LOC; `src/render/politicians.py` (159 detail pages) + `src/render/personas.py` izvilkti; `_bill_slug` + `_get_last_activity` promovēti `_common`-am — PR #7, commit `c97dbb5`
- Fāze 3c — generate.py 3198 → 3003 LOC; `src/render/parties.py` (15 partijas/<short>.html + index) izvilkts ar nulle jaunu leaf promotion-u (F4 disciplīna no F3-prep+F3b atmaksājas) — PR #8, commit `118b3a5`
- Fāze 3d — generate.py 3003 → 2419 LOC; `src/render/positions.py` + `news.py` + `statistika.py` izvilkti; `_download_chart_js` + `_download_annotation_plugin` promovēti `_common`-am — PR #9, merge `b0586ad`
- F3a-F3d postlude doc sync — wiki/CHANGELOG + inventory + plāna paste-block F3e-ready — commit `5ceaeaf`
- Pre-F3e baseline fix — `tests/fixtures/render_baseline_politicians.json` regen (10 stale hashes no `_load_syntheses` CWD-relative image lookup) — commit `3064541`. **SUPERSEDED by F3g-pre (PR #11) — strukturāls fix landed.**
- Fāze 3e — generate.py 2413 → 1783 LOC; `src/render/bills.py` (203 LOC, ~151 likumprojekti/<slug>.html) + `src/render/laws.py` (186 LOC, likumi.html + ~33 likumi/<slug>.html) + `src/render/votes.py` (382 LOC, balsojumi.html) izvilkti — PR #10, merge `cba1aaf`. Review-nits: dead `LAW_TITLE_RE` import + log `bill_count` (`abce764`).
- **Fāze 3g-pre — `_load_syntheses` output_dir-relative — PR #11, merge `0fd2565`.** Threads `atmina_dir` through `_load_syntheses(atmina_dir)`; default arg preserves production CWD-relative behavior. Char baselines regen captured both the synthesis fix (10 hashes) and unrelated content drift since F3d (~50 hashes). 3 unit tests in `tests/test_load_syntheses.py` lock down path-resolution invariant. Pre-F3e reactive baseline patch superseded.
- **Fāze 3f.2 — generate.py 1783 → 1536 LOC; `src/render/x.py` (285 LOC, x.html) izvilkts** — PR #12, merge `31f4c9f`. Self-contained `render_x(env, db, atmina_dir)`; 11 test_generate.py V1-metrics tests pass via shim. Char fixture `render_baseline_x.json`. Plan deviation: `_rewrite_shortener_link_labels` actually used only by `_fetch_blog_posts:859` — moves with F3f.4, not F3f.2.
- **Fāze 3f.3 — generate.py 1536 → 1187 LOC; `src/render/tensions.py` (62 LOC) + `src/render/links.py` (360 LOC) izvilkti** — PR #13, merge `5b88e7b`. Pass-through `tensions` arg matches F3a/F3e precedent. ~140 LOC inline orchestration absorbed into render_links. Char fixture `render_baseline_graph.json`.
- **Fāze 3f.5 — generate.py 1187 → 1031 LOC; `src/render/analyses.py` (120 LOC) + `src/render/syntheses.py` (126 LOC) izvilkti** — PR #14, merge `f88865d`. `_parse_frontmatter` paaugstināts uz `_common.py` (3 sub-page consumers — F3-prep promotion rule). Pre-PR commit `6cdd788` REGEN refresh atjaunināja 3 stale char fixtures (contradictions/graph/politicians driftēja kopš 22:00 deploy/auto-sync). `_load_wiki_profile` pārvietots per plāns, bet flagged kā dead code (F3b regression PR #7) — restoration ticketed F3g checklist. Char fixture `render_baseline_analyses.json`.
- **Fāze 3f.4 — generate.py 1031 → 772 LOC; `src/render/blog.py` (321 LOC) izvilkts** — PR #15, merge `0dcaf66`. `_fetch_blog_posts` + `_fetch_context_notes` + `_rewrite_shortener_link_labels` + blog index/per-post render izvilkti. Plan deviation: `render_blog(env, atmina_dir, blog_posts)` 3 args, ne 4 (context_notes ir tikai orchestrator-owned analizes.html consumer). F3f.2 cross-ref bookkeeping iebūvēts (`parties.py:185` + `_common.py:511` → `src/render/x.py`). F3f.5 docstring kļūda izlabota (`_parse_frontmatter` reālie consumeri tikai analyses+syntheses, ne blog). Char fixture `render_baseline_blog.json` — dynamic count (~25 daily/weekly briefs).
- **Fāze 3f.1 — generate.py 772 → 558 LOC; `src/render/dashboard.py` (293 LOC) izvilkts — F3f NOSLĒGTS** — PR #16, merge `385071c`. `_fetch_stats` + `_sparkline_svg` + `_fetch_hero_v2_data` + `_fetch_trends_data` + render_dashboard izvilkti. Plan deviation: `render_dashboard` rendere ABAS lapas (index.html + analizes.html — koplieto orchestrator-fetched data). 12-arg pass-through (peer max). Pre-PR commit `b249690` REGEN refresh atjaunoja stale x.html baseline (data drift kopš F3f.4 merge) + bootstrapped F3f.1 fixture. Reviewer verificēja byte-equivalence; analizes.html placement-change matemātiski drošs.
- **Fāze 3g — generate.py 558 → 173 LOC kā re-export shim; `src/render/_orchestrator.py` (444 LOC) jauns + `src/render/__init__.py` re-eksports — F3 PILNĪBĀ PABEIGTS** — PR #17, merge `6ab0019`. `generate_public_site` + `_generate_sitemap` + `_generate_og_image` lifted uz `_orchestrator.py`. Kanoniskais publiskais ceļš: `from src.render import generate_public_site`. F3g.2: `render_parties` self-contained (pieņem `parties` arg, neatgriež). F3g.3: `_load_wiki_profile` promoted no `analyses.py` uz `_common.py` un callsite restored `politicians.py:310` (F3b regression PR #7 fix — 162 wiki/persons/*.md tagad satur ~150 politiku detail pages). F3g.7: `agent_api_inventory.txt` full rewrite. F3g.4/5/6 atstāti deferred (low-value cleanup). Reviewer verdict: *SHIP* (zero MUST/SHOULD-FIX, cycle-safety verified). Plan deviation: `<50 LOC` target → 173 LOC (shim widening — 85 simbolu re-exports nepieciešami testu+agent kontaktam).
- Atlikusi: F5 migrāciju formāts (atlikt līdz nākamai DDL maiņai). **Total trajectory: 4250 → 173 LOC (-96%).**
- **Nākamās sesijas startpunkts:** sk. § "Nākamā sesija — paste-friendly start" plāna apakšā.

**Konteksts:** Strukturāla optimizācija lielajiem failiem (`src/generate.py` 4250 LOC, `src/ingest.py` 1579 LOC sākotnēji → 1075 LOC pēc F1, `src/saeima.py` 1425 LOC, `src/db.py` 1139 LOC sākotnēji → 813 LOC pēc F2). Plāns balstīts uz divu ārējo ekspertu konsultāciju ([atmina_optimization_brief.md](../../atmina_optimization_brief.md), [atminas_agentu_plana_izvertejums.md](../../atminas_agentu_plana_izvertejums.md)) un mūsu projekta-specifisku kalibrēšanu.

**Mērķis:** Sadalīt monolītus, lai turpmākais darbs kļūst ātrāks un drošāks, nesalaužot aģentu API un eksistējošos invariantus (sk. CLAUDE.md punktus 1-13).

**Ne-mērķi:** Performance optimizācija, dependency grupas, CI pipeline, pilna `src/storage/` paketes sadale, vēsturisko migrāciju retro-konvertēšana — atstāti fāzē 5+ vai vispār ārpus plāna.

---

## Pamatprincipi

1. **Aģentu API ir reālais "stable contract"** — funkciju nosaukumi un signatūras `.claude/agents/*.md` un `scripts/` patērētājiem. Pirms katras pārvietošanas pārbaudīt `.scratch/agent_api_inventory.txt` (Fāze 0).
2. **Re-export shim, ne facade slāņi.** Ja moduļa pārvietošana ietekmē aģentu API, atstāj 20-rindu shim vecajā ceļā, kas re-eksportē no jaunās vietas.
3. **Characterization tests pirms refaktoringa.** Iesaldēti fixtures `tests/fixtures/*.json`, ne tiešas DB query atkarības.
4. **Katra fāze beidzas ar `bash scripts/check.sh` zaļš + commit + push.** Ja kāds solis ir vidū fāzes, tas tomēr commit-ējams atomic pakāpienā.
5. **Rollback ceļš:** `git tag pre-refactor-2026-04-29` + `data/atmina.db.pre-refactor-20260429.backup`.

---

## Pirmsdarbi (1 sesija, ~30 min)

Tas NAV refaktorings — tas ir tīrais sākuma punkts.

- [ ] **0a. Tīrīt working tree.** Atsevišķi commit:
  ```bash
  git diff src/generate.py src/ingest.py src/tools.py
  ```
  Komitēt tematiski. **Mērķis:** `git status` rāda tikai untracked daily artefaktus pirms refaktoringa sākuma.

- [ ] **0b. Backup divi slāņi:**
  ```bash
  cp data/atmina.db data/atmina.db.pre-refactor-20260429.backup
  git tag pre-refactor-2026-04-29
  git push origin pre-refactor-2026-04-29
  ```

- [ ] **0c. Verificēt baseline:**
  ```bash
  .venv/Scripts/activate
  python -m pytest tests/ -q
  python -c "from src.generate import generate_public_site; generate_public_site()"
  python -c "from src.routine import print_routine; print_routine()"
  ```
  Pierakstīt: cik testu paiet, cik ilgi ģenerējas sait. Tas ir atskaites punkts.

- [ ] **0d. Aģentu API inventarizācija:**
  ```bash
  rg "from src\.\w+ import" .claude/agents/ scripts/ src/social_agent/ src/video_ingest/ src/csp/ src/graphics/ \
    > docs/refactor/agent_api_inventory.txt
  ```

- [ ] **0e. Commit baseline:**
  ```bash
  git add data/atmina.db.pre-refactor-* docs/refactor/agent_api_inventory.txt
  git commit -m "chore: pre-refactor baseline — DB backup + agent API inventory"
  git push
  ```

---

## Fāze 0 — Drošības tīkls (1-2 sesijas) ✅ PAVEIKTA — PR #1, commit `b0f9871`

**Mērķis:** Saliekot smoke testus invariantam un linter setupu, lai katra refaktoringa fāze beidzas ar `scripts/check.sh` zaļu.

### Darbi
- [ ] **F0.1. `pyproject.toml`** ar ruff + pytest config:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  markers = ["integration", "slow"]

  [tool.ruff]
  line-length = 100
  target-version = "py311"
  [tool.ruff.lint]
  select = ["E", "F", "I", "B", "UP", "ARG"]
  ```
- [ ] **F0.2. `scripts/check.sh`:**
  ```bash
  #!/usr/bin/env bash
  set -e
  python -m ruff check src scripts tests
  python -m pytest tests -q
  python -c "from src.generate import generate_public_site; generate_public_site()"
  ```
- [ ] **F0.3. Smoke testi 7 invariantam** — jauns fails `tests/test_invariants.py`:
  - `test_claim_without_source_url_dropped` (CLAUDE.md punkts 2)
  - `test_store_claim_idempotent_on_triple` (punkts 3)
  - `test_claim_type_filter_segregation` (punkts 4)
  - `test_speaker_id_separation` (punkts 5)
  - `test_saeima_vote_document_id_null` (punkts 6)
  - `test_save_analysis_atomic_on_failure` (punkts 9)
  - `test_relay_account_no_first_party_subject` (punkts 11)
- [x] **F0.4. Audit eksistējošo testu pārklājumu** — pabeigts 2026-04-29.

  **Pārklājuma karte (smoke layer ↔ detalizētais coverage):**
  | Inv | CLAUDE.md | Smoke (`tests/test_invariants.py`) | Esošais detalizētais coverage |
  |-----|-----------|-------------------------------------|--------------------------------|
  | 2 | claims bez source_url drop | `test_inv2_claim_without_source_url_dropped` (jauns, taisns assert uz `failures.missing_source_url` + `claims` nav rindas) | `tests/test_analyze.py` — `test_empty_doc_ids_*` aizskar source_url override no dokumenta, bet ne taisnu drop |
  | 3 | `store_claim` idempotents uz triple | `test_inv3_store_claim_idempotent_on_triple` (position-type variants) | `tests/test_db.py:408` `test_store_claim_null_document_id_url_dedup_still_works` (saeima_vote variants) |
  | 4 | claim_type filter segregācija | `test_inv4_claim_type_filter_segregation` (sanity) | `tests/test_db.py:637-679` `TestSearchSimilarClaimsFilter` 3 testi — pilns directional bidirektionālais |
  | 5 | speaker_id atdalīts no opponent_id | `test_inv5_speaker_id_separation` (sanity) | `tests/test_db.py:812, 842, 876, 910` — 4 testi |
  | 6 | `saeima_vote` ļauj `document_id=NULL` | `test_inv6_saeima_vote_document_id_nullable` (sanity) | `tests/test_db.py:368, 383` — `test_store_claim_saeima_vote` + `test_store_claim_accepts_null_document_id` |
  | 9 | `save_analysis` atomic on failure | `test_inv9_save_analysis_atomic_on_failure` (sanity ar boom() store_claim) | `tests/test_analyze.py:281-389` `TestSaveAnalysisAtomicity` — pilns rollback ar count assertions |
  | 11 | `feed_type ∈ {first_party, relay}` | `test_inv11_social_accounts_feed_type_constraint` (schema-level smoke) | `tests/test_ingest.py:474, 508` — `_store_tweets` uzvedības testi abiem feed_types |

  Stratēģija: `tests/test_invariants.py` ir vienlapas "līgums-katalogs" — katrs tests sniedz minimālu uzvedības verifikāciju + cita header citē detalizētāko testu. Inv 2 + Inv 3 (position) sniedz JAUNU pārklājumu; pārējie 5 dublē sanity, bet ar mazāku setup-u un strikti vienoti vienā failā nākotnes refaktoringa "drošības tīkla" lietošanai (`bash scripts/check.sh` zaļš → līgumi dzīvi).

### Verifikācija
- [ ] `bash scripts/check.sh` zaļš
- [ ] `pytest tests/test_invariants.py -v` rāda 7 testus, visi paiet
- [ ] Ruff izejas kļūdu skaits dokumentēts (vai 0, vai akceptēts saraksts)

### Commit + push
```bash
git add pyproject.toml scripts/check.sh tests/test_invariants.py
git commit -m "test: add 7-invariant smoke suite + ruff/pytest config + check.sh"
git push
```

---

## Fāze 1 — Matcher izvilkšana (1-2 sesijas) ✅ PAVEIKTA — PR #2, commit `4f4d25d`

**Mācība F1+:** `src/ingest.py` re-export shim must include 5 PRIVATE symbols (`_clear_politician_cache`, `_load_politician_forms`, `_latvian_surname_inflections`, `_surname_has_person_context`, `_match_politician_from_url`) IN ADDITION to the 5 public ones — `tests/test_ingest.py` and `tests/test_latvian_inflections.py` import them directly. Plus 3 test fixtures (`test_ingest.py::fixture_db` + `test_audit_*`) needed updates: their cache resets wrote to phantom `src.ingest._politician_forms_cache` attrs instead of the real cache in `src.matcher`. Fixed via `_clear_politician_cache()` calls + `monkeypatch.setattr(matcher_mod, "get_db", …)`.



**Pamatojums:** Mazākais blast radius (viens import path), augstākais frekvences-of-edit ROI (matcher ir biežs grozījumu mērķis), trenē refaktoringa procesu drošā kontekstā pirms `generate.py`/`saeima.py`.

### Darbi
- [ ] **F1.1. Characterization fixtures** — `tests/fixtures/matcher_docs.json`:
  - 10-15 reāli dokumenti no DB (`SELECT id, title, content FROM documents ORDER BY RANDOM() LIMIT 15`)
  - Katram piesaistīts gaidāmais `match_politicians()` rezultāts (politiķu ID saraksts)
  - **Iesaldēti fixtures, ne live DB**
- [ ] **F1.2. `tests/test_matcher.py`** — testē tagadējo `src.ingest.match_politicians` ar fixtures pirms pārvietošanas
- [ ] **F1.3. `src/matcher.py`** — pārvietot funkcijas:
  - `extract_twitter_author_handle`, `_clear_politician_cache`, `_surname_has_person_context`
  - `_latvian_surname_inflections`, `_load_politician_forms`
  - `_init_surname_disambiguation`, `_disambiguate_shared_surname`
  - `_match_politician_from_url`, `match_politicians`, `match_politician`
  - `link_politicians_to_documents`, `assign_unmatched_documents`
- [ ] **F1.4. `src/ingest.py` re-export shim** (atbalsta agentu promptus + skripts):
  ```python
  from src.matcher import (
      match_politicians, match_politician,
      link_politicians_to_documents, assign_unmatched_documents,
      extract_twitter_author_handle,
  )
  ```
- [ ] **F1.5. Iekšējo importu atjaunināšana:**
  ```bash
  rg "from src.ingest import (match_politicians|link_politicians|match_politician|assign_unmatched)" --files-with-matches
  ```
  Visus uz `from src.matcher import ...` (izņemot pašu `src.ingest`).

### Testi
- [ ] **Jauns:** `tests/test_matcher.py` ar `matcher_docs.json` fixtures
- [ ] **Eksistē:** `tests/test_latvian_inflections.py` zaļš pēc importu atjaunināšanas
- [ ] **Eksistē:** `tests/test_ingest.py` zaļš (orkestrācija turpina izsaukt matcher)

### Verifikācija
- [ ] `bash scripts/check.sh` zaļš
- [ ] Manuāls smoke: `python -c "from src.ingest import match_politicians; print(match_politicians('Krišjānis Kariņš teica'))"` strādā (re-export shim)

### Commit + push
```bash
git add src/matcher.py src/ingest.py tests/test_matcher.py tests/fixtures/matcher_docs.json
git commit -m "refactor(ingest): extract matcher to src/matcher.py with shim + fixtures"
git push
```

---

## Fāze 2 — `schema.sql` izvilkšana no `db.py` (1 sesija) ✅ PAVEIKTA — PR #3, commit `94466aa`

**Mācība F2+:** Divi carve-outs glabājas Python-side, NE `schema.sql`:
1. **vec0 virtual tables** (`document_vectors`, `claim_vectors`) — `tests/test_knab.py::_SafeConnection` mocko `sqlite_vec` CI vidēm un intercepto tikai `.execute()` calls satur `"vec0"`, ne `.executescript()`. Ja vec0 DDL būtu schema.sql, mock plūsma izlaiž tās caur, vec0 fail nepieejams modulis. Komentārs ABĀS vietās: `src/schema.sql` apakšā un inline `src/db.py::init_db()`.
2. **brief_images + external_profiles + ALTER TABLE migrācijas** — sqlite < 3.35 nav `ALTER TABLE ADD COLUMN IF NOT EXISTS`, tāpēc Python conditional pattern (`if "col" not in PRAGMA table_info`) glabājas `init_db()` pēc `executescript`. F5 (migrācijas formāts) varētu šīs absorb-ot.

DDL whitespace: `src/schema.sql` 4-space top-level indent vs oriģinālā 12-space inline; SQLite glabā CREATE TABLE SQL verbatim, tāpēc raw `.schema` dump differences. `tests/test_schema.py::test_schema_sql_matches_pre_refactor_dump` normalizē whitespace ar `re.sub(r"\s+", " ", …)`.



### Darbi
- [ ] **F2.1. `src/schema.sql`** — pārvietot DDL no `init_db()` (līnijas ~40-510)
- [ ] **F2.2. `src/db.py init_db()` lasa schema.sql:**
  ```python
  def init_db(db_path: str = DB_PATH) -> None:
      conn = sqlite3.connect(db_path)
      schema_path = Path(__file__).parent / "schema.sql"
      conn.executescript(schema_path.read_text(encoding="utf-8"))
      # ... pragmas, sqlite-vec load
  ```

### Testi
- [ ] **Jauns:** `tests/test_schema.py`:
  - `test_init_db_on_empty_creates_all_tables`
  - `test_init_db_on_existing_db_idempotent`
  - `test_schema_sql_matches_pre_refactor_dump`
- [ ] **Eksistē:** `tests/test_db.py` — visi testi joprojām zaļi
- [ ] **Eksistē:** `tests/test_invariants.py` no Fāzes 0 — joprojām zaļi

### Verifikācija
- [ ] `bash scripts/check.sh` zaļš
- [ ] Diff baseline: svaiga test DB no `init_db()` `.schema` == `pre-refactor-2026-04-29` DB `.schema`

### Commit + push
```bash
git add src/schema.sql src/db.py tests/test_schema.py
git commit -m "refactor(db): extract schema DDL to src/schema.sql"
git push
```

---

## Fāze 3 — `generate.py` → `src/render/` (3-5 sesijas, vairāki commit)

⚠️ Lielākā fāze. Sadalīt vairākos commit pa lapas grupām, ne vienu lielo commit.

### F3a — `_common.py` un viena lapa kā prototips ✅ PAVEIKTA — PR #5, commit `3d06e05`

**Mācība F3a+ (no PR #5 review):**

1. **Plāna sākotnējā piezīme "viens shim pietiek" izrādījās NEPILNĪGA.** Aģentu API skats (tikai `generate_public_site`) ignorēja testu suite, kas tieši importē ~20 privātos `_fetch_*`/`_safe_*`/`_persona_category`/`PARTY_COLORS` simbolus no `src.generate`. F3a stratēģija: `src/generate.py` re-eksportē KATRU pārvietoto simbolu (32+ vārdi). F3b–F3g atkārto šo modeli.
2. **`src/render/__init__.py` re-eksports radītu ciklu** (`generate.py → render._common → render.__init__ → generate`). F3a apzināti atstāj `__init__.py` tukšu (tikai docstring) — `generate_public_site` paliek `src/generate.py` līdz F3g, kad to pārvietos uz pakešu `__init__.py`.
3. **`tests/test_render_common.py` netika izveidots** — coverage paliek caur re-eksporta shim caur `tests/test_generate.py::TestSlugify` u.c. Bezatkārtošanas migration-window izvēle.

- [x] `src/render/__init__.py` — TIKAI sub-modulu kontainers (NE re-export — cycle); F3g pārcels `generate_public_site` šeit
- [x] `src/render/_common.py` (469 LOC):
  - Drošības filtri: `_sanitize_html`, `_safe_json_filter`, `_safe_url_filter`, `_autolink_bills_filter`
  - URL/slug helperi: `_slugify`, `_party_short_name`, `_persona_category`, `_confidence_tier`, `_initials_from_name`, `_delta_days`, `_domain_from_url`, `_split_summary`, `_latvian_quotes`, `_photo_data_uri`
  - Cross-page domain: `_source_to_internal_link`, `_enrich_contradiction`
  - Page primitive: `_render_page`
  - Konstantes (`BASE_URL`, `PARTY_COLORS`, `SEVERITY_LV`, `CATEGORY_LV`, `CLAIM_TYPE_LABEL`, `_SEVERITY_GLYPHS`, path roots)
  - **NB:** Jinja env setup paliek `src/generate.py::generate_public_site`; F3b-F3f pakāpeniski izvilks atlikušo env-konfigurāciju, kad būs pilnīgi skaidrs, kas vajadzīgs visām lapām
- [x] `src/render/contradictions.py` (177 LOC): `_fetch_contradictions`, `_render_og_cards`, `render_contradictions(env, atmina_dir, contradictions, all_parties)` orchestrator
- [x] `src/generate.py` re-eksportē 32+ pārvietotos simbolus + deleģē Pretrunas blokā uz `render_contradictions(...)`. 4250 → 3733 LOC (-517).

**Testi:** `tests/test_generate.py` un radniecīgie zaļi (149 testi caur shim). Pievienots `tests/test_render_chars.py` (2 byte-identity tests pret `tests/fixtures/render_baseline_contradictions.json`) — F3b-F3g izmantos to pašu šablonu pa lapu grupai.

**Verifikācija:** `pretrunas.html` + 12 detail pages SHA-256 byte-identiski ar pre-refactor baseline (REGEN=1 bootstrap pēc kuras assert).

**Commit:** `refactor(generate): F3a — extract _common.py + contradictions.py prototype` (3d06e05)

### F3-prep — char fixture stability + leaf-helper promotions ✅ PAVEIKTA — PR #6, merge commit `dbed1a0`

Pievienots starp F3a un F3b pēc PR #5 review. Divi commit-i:

1. **`e1b6549` test(render): stabilize char fixtures with ATMINA_ASSETS_VERSION env override** — `_resolve_assets_version()` helper `_common.py`, abas generate.py/generate_statistika call sites dedupotas. tests/test_render_chars.py session fixture pin-o env var uz "test"; baseline regenerated. Char fixtures vairs nedrift uz fresh worktree.
2. **`fdcf6cb` refactor(render): promote 4 leaf helpers + 2 constants to _common.py** — `_normalize_date`, `_date_sort_key`, `_format_tweet_time`, `_titlecase_party_name` + `_LV_OFFSET_HOURS`, `_PARTY_LOWERCASE_WORDS`. Katrs vajadzīgs 2+ F3b–F3f sub-pages — pre-stage, lai katra sub-page importē tikai no `_common`, ne no peer sub-page (F4 leaf-vs-fan-out).

generate.py LOC: 3733 → 3699 (-34). _common.py: 469 → 564.

### F3b — `politicians.py` + `personas.py` ✅ PAVEIKTA — PR #7, commit `c97dbb5`

**Plāna deviation no sākotnējā teksta:** Plāns sākotnēji minēja "politicians.py + politician.py", bet UI realitātē Personas IR politiķu index — nav atsevišķs `politiki.html`. F3b deliverable atbilstoši ir `politicians.py` (159 detail pages) + `personas.py` (unified index ar kategorijām un rail facets). Nemaina arhitektūru, tikai precizē nosaukumus.

Moved (3 helpers + 1 orchestrator → `src/render/politicians.py`, 333 LOC):
- `_fetch_politicians`, `_fetch_commentary_about`, `_fetch_politician_detail`
- `render_politicians(env, db, atmina_dir, politicians, pid_to_syntheses)`

Moved (2 helpers + 1 orchestrator → `src/render/personas.py`, 135 LOC):
- `_fetch_personas`, `_fetch_personas_metrics`
- `render_personas(env, db, atmina_dir)` — self-contained (re-fetches data internally; original `personas` var was only used for this one block)

Promoted to `_common.py` (F4 leaf rule — both sub-pages need them; F3c/F3e will too):
- `_bill_slug` (F3b politicians + F3e bills future)
- `_get_last_activity` (F3b personas + F3c parties future); ~100 LOC, leaf-clean

generate.py LOC: 3699 → 3198 (-501). Re-export shim widens by 9 names.

**Verifikācija:** personas.html + 159 politiki/`<slug>`.html SHA-256 byte-identiski ar pre-refactor baseline (`tests/fixtures/render_baseline_politicians.json`). 891 passed (889 + 2 jauni char tests).

### F3c — `parties.py` ✅ PAVEIKTA — PR #8, commit `118b3a5`

**Plāna deviation no sākotnējā teksta:** Plāns minēja "parties.py + party.py", bet F3c reality ir viens `parties.py` modulis, kas pārklāj abus index + per-party detail rendererus. `_fetch_parties_page` un `_fetch_party_detail` ir māsas vienā modulī ar koplietotām SQL pattern un leaf-helper importiem; ~250 LOC nav pamats split. Nemaina arhitektūru, tikai precizē failu nosaukumus.

Moved (2 helpers + 1 orchestrator → `src/render/parties.py`, 250 LOC):
- `_fetch_parties_page(db)` — party list ar member/claim/contradiction count-iem
- `_fetch_party_detail(db, party)` — per-party aggregate: members, positions, votes, tensions, KNAB summary, last news + last X post
- `render_parties(env, db, atmina_dir) -> list[dict]` — orchestrator, atgriež `parties_data` jo `_generate_sitemap` (vēl `generate.py`-ā) tas vajadzīgs URL listei. Self-contained pēc F3g.

**ZERO new helper promotions.** Visi leaf deps jau bija `_common`-ā no F3-prep + F3b — F4 leaf-vs-fan-out disciplīna atmaksājās: F3c = mazākais iespējamais diff (parties.py + 1 shim block + 1 inline-render swap). `_enrich_faction_breakdown` palika `generate.py`-ā (votes-domain, F3e teritorija, 9 testi to importē).

generate.py LOC: 3198 → 3003 (-195). Re-export shim widens by 3 names (defensive — tests neimportē tieši).

**Verifikācija:** partijas.html + 15 partijas/`<short>`.html SHA-256 byte-identiski ar pre-refactor baseline (`tests/fixtures/render_baseline_parties.json`). 893 passed (891 + 2 jauni char tests).

### F3d — `positions.py` + `news.py` + `statistika.py` ✅ PAVEIKTA — PR #9 (TBD merge commit)

Plāna teksts atbilst realitātei (no deviation). Trīs jauni moduļi vienā commitā — lielākais F3 sub-phase LOC delta līdz šim.

Moved (3 helpers + 1 const + 1 orchestrator → `src/render/positions.py`, 227 LOC):
- `_fetch_claims`, `_fetch_pozicijas_metrics`, `PZV1_TOPIC_COLORS`, `render_positions(env, db, atmina_dir)` — emits `pozicijas.html` + `pozicijas-data.json` (+ `.br` + `.gz`)

Moved (1 helper + 1 orchestrator → `src/render/news.py`, 158 LOC):
- `_fetch_news`, `render_news(env, db, atmina_dir)` — emits `zinas.html`

Moved (`src/render/statistika.py`, 305 LOC):
- `generate_statistika(output_dir, csp_db_path, events_path)` public entrypoint — STANDALONE, called manually after monthly CSP data sync. NOT in `generate_public_site` flow.
- 4 `_CSP_*` constants + 7 nested helper closures (kept inline because they close over `csp_conn` + `events`)

Promoted to `_common.py` (F4 leaf rule — both entrypoints use them):
- `_download_chart_js`, `_download_annotation_plugin` — used by `generate_public_site` (index page chart) AND `generate_statistika` (CSP dashboard charts). Promoting avoids back-import cycle from sub-page to `generate.py`.

generate.py LOC: 3003 → 2419 (-584). **Total trajectory: 4250 → 2419 (-43%).** Re-export shim widens by 8 names. Cleaned up 4 dead imports (`Counter`, `urlparse`, `CSP_TABLES`, `CSP_ORDER`, `csp_generate_insight`) and 2 dead local vars (`topic_counts`, `topics_with_counts`) post-extraction.

**Verifikācija:** pozicijas.html + zinas.html + statistika.html + 10 statistika/`<id>`.html SHA-256 byte-identiski ar pre-refactor baseline (`tests/fixtures/render_baseline_misc.json`). 897 passed (893 + 4 jauni char tests). `rendered_site` session fixture expanded to call `generate_statistika` — `csp.db` + `events.yaml` are git-tracked (override `*.db` gitignore), tāpēc worktrees iegūst tos automātiski.

### F3e — `bills.py` + `laws.py` + `votes.py` ✅ PAVEIKTA — PR #10, merge commit `cba1aaf`

**Plāna deviation no sākotnējā teksta:**

1. **`render_votes` signature precizēta** — plāns paredzēja `(env, db, atmina_dir, vote_topics, deputies_list)`; reālā implementācija ir `(env, db, atmina_dir, votes, bills, laws_index_count)`. Pamatojums: `vote_topics`, `deputies`, `vote_sessions`, `matrix_data`, `vote_metrics`, `bill_topics` ir deterministic derivations no `votes`/`bills`, tāpēc tie pārcelti iekšā render_votes-ā. Pass-through pattern atbilst F3a (`all_parties` contradictions) un F3c (`parties_data` sitemap) precedentiem. `votes` un `bills` jau tāpat tiek pre-fetched generate_public_site-ā index page (`recent_votes`) un `env.globals["bill_slugs"]` autolink vajadzībām.

2. **`_get_law_titles` glabājas `bills.py`, ne `laws.py`** — vienīgais konsumers ir `_fetch_bill_detail` (`base_law_title` lookup). Co-location ar consumer ļauj laws.py palikt leaf-clean.

3. **Char fixtures bundle balsojumi into bills** — `render_baseline_bills.json` satur balsojumi.html (1 entry) + ~151 likumprojekti/`<slug>`.html, jo votes.py emits tikai vienu index page (saves a 3rd fixture file).

Moved (5 simboli + 1 const + 1 orchestrator → `src/render/bills.py`, 203 LOC):
- `_LAW_TITLES_CACHE`, `_get_law_titles`, `_fetch_bills`, `_fetch_bill_detail`, `_generate_bill_pages`
- `render_bills(env, db, atmina_dir) -> int` — emits ~151 likumprojekti/`<slug>`.html

Moved (3 helpers + 2 regex const + 1 orchestrator → `src/render/laws.py`, 186 LOC):
- `_LAW_LIKUMI_LV_RE`, `_LAW_BODY_STRIP_RE`
- `_fetch_law_pages`, `_generate_law_pages`, `_fetch_law_index_page`
- `render_laws(env, db, atmina_dir) -> int` — emits likumi.html + ~33 likumi/`<slug>`.html. Returns `laws_index_count` for the balsojumi.html footer.

Moved (3 helpers + 1 orchestrator → `src/render/votes.py`, 382 LOC):
- `_enrich_faction_breakdown` (pure; 8 unit tests in `test_generate.py::TestEnrichFactionBreakdown`)
- `_fetch_votes`, `_build_matrix_data`
- `render_votes(env, db, atmina_dir, votes, bills, laws_index_count) -> None` — emits balsojumi.html. Folds in vote_metrics, vote_sessions, deputies, matrix_data, bill_topics computation that was previously inline in generate_public_site (~50 LOC orchestrator delta).

**ZERO new helper promotions.** Visi leaf deps (`_bill_slug`, `_slugify`, `_render_page`, `_sanitize_html`) jau bija `_common`-ā no F3-prep + F3b — F4 leaf-vs-fan-out disciplīna turpina atmaksāties.

generate.py LOC: 2413 → 1783 (-630). **Total trajectory: 4250 → 1783 (-58%).** Re-export shim widens by 16 names. Review-nits commit (`abce764`): dead `LAW_TITLE_RE` import + log `bill_count` per F3d's `b6b196a` precedent.

**Verifikācija:** balsojumi.html + ~151 likumprojekti + likumi.html + ~33 likumi/`<slug>`.html SHA-256 byte-identiski ar pre-refactor baseline (`tests/fixtures/render_baseline_bills.json` + `render_baseline_laws.json`). 901 passed (897 + 4 jauni char tests). 385 byte-identical pages kopā.

**Pre-F3e baseline drift atklāsme (commit `3064541`):** Master pre-F3e check.sh atklāja, ka `tests/fixtures/render_baseline_politicians.json` bija stale 10 hashēs. Root-cause: `_load_syntheses` (src/generate.py:1656) lasa synthesis attēlus no CWD-relatīva `output/atmina/images/synthesis/`. Main worktree-ā ir attēli no agrākiem render-iem; fresh worktree → `has_image=False` → 10 politiķu detail page nesatur synthesis `<img>` tag → hash drift. Fix: REGEN baseline + commit. **F3g uzdevums absorbē šo bug-fix:** `_load_syntheses` jāpārtaisa, lai lasa images relative to render `output_dir` arg, ne CWD.

### F3g-pre — `_load_syntheses` CWD fix ✅ PAVEIKTA — PR #11, merge `0fd2565`

Lifted forward from F3g into a standalone PR so F3f.5 (syntheses.py extraction) doesn't depend on the orchestrator-lift fix landing later.

- [x] `_load_syntheses(atmina_dir: Path = Path("output/atmina"))` — atmina_dir threaded through; default preserves prod CWD-relative behavior.
- [x] Char baselines regen — captures both the synthesis fix (10 politician hashes flip from has_image=True → False) AND unrelated content drift since F3d (~50 hashes from claims/contradictions/votes added between commits `3d8ed1e..f493dd8`). Both canonical-state correct.
- [x] 3 regression tests `tests/test_load_syntheses.py` lock down path-resolution invariant (atmina_dir lookup, empty atmina_dir, default-arg CWD-relative under `monkeypatch.chdir`).
- [x] Pre-F3e reactive baseline patch (commit `3064541`) superseded by structural fix.

### F3f.2 — `x.py` (Twitter/X feed page) ✅ PAVEIKTA — PR #12, merge `31f4c9f`

- [x] `_fetch_x_data(db)` + `render_x(env, db, atmina_dir)` self-contained orchestrator; 285 LOC.
- [x] Re-export shim widens by 2 names; 11 `tests/test_generate.py` V1-metrics tests directly import `_fetch_x_data` (all pass via shim).
- [x] Char fixture `render_baseline_x.json` (single page hash). Byte-identity preserved.
- [x] Cleanup nit: `%`-style SQL placeholder formatting → f-string + extracted `placeholders` local. New module passes full lint without per-file-ignore.
- [x] Plan deviation: `_rewrite_shortener_link_labels` was plan-listed for x.py but actually used only by `_fetch_blog_posts:859` — moves with F3f.4 (blog.py) instead. Plan updated.

generate.py LOC: 1783 → 1536 (-247). Re-export shim widens by 2 names.

### F3f.3 — `tensions.py` + `links.py` ✅ PAVEIKTA — PR #13, merge `5b88e7b`

Two leaf modules in 1 PR (siblings, both consume pre-fetched `tensions`).

- [x] `tensions.py` (62 LOC): `_fetch_tensions(db)` + `render_tensions(env, db, atmina_dir, tensions)` → spriedzes.html.
- [x] `links.py` (360 LOC): `_fetch_graph_data(db)` + `render_links(env, db, atmina_dir, tensions)` → saites.html with full inline orchestration absorbed (~140 LOC moved out: claims_by_pid, contras_by_pid, votes_by_pid payloads).
- [x] Pass-through `tensions` arg matches F3a (`render_contradictions`) and F3e (`render_votes`) precedents — orchestrator pre-fetches data shared by 2+ sub-pages.
- [x] Char fixture `render_baseline_graph.json` (both pages SHA-256 in one file). Reviewer renamed from plan's suggested `misc2.json` for semantic clarity.
- [x] Cleanup nit: compact `a = x; b = y` semicolon pattern (E702) in contradiction-swap logic → one-statement-per-line. New modules pass full lint without per-file-ignore.
- [x] F3g-deferred TODOs (from PR #13 review):
  - Extract `_chronologize_contradiction(row, key_pairs)` to `_common` (3 duplicates: `links.py`, `_common._enrich_contradiction`, `social_agent/candidates.py:93`).
  - Extract `_tension_filter_axes(tensions) -> dict` to `_common` (2 duplicates: tensions.py + links.py).

generate.py LOC: 1536 → 1187 (-349). Re-export shim widens by 4 names. **Total trajectory: 4250 → 1187 (-72%).**

### F3f.5 — `analyses.py` + `syntheses.py` ✅ PAVEIKTA — PR #14, merge `f88865d`

Two leaf modules + `_parse_frontmatter` promotion to `_common.py` (F3-prep rule, 3 consumers).

- [x] `analyses.py` (120 LOC): `_load_wiki_profile`, `_load_analyses`, `render_analyses(env, atmina_dir, analyses)` → emits analizes/<slug>.html.
- [x] `syntheses.py` (126 LOC): `_load_syntheses(atmina_dir)` (worktree-portable post-F3g-pre), `_map_syntheses_to_politicians`, `render_syntheses(env, atmina_dir, syntheses)` → emits sintezes/<slug>.html.
- [x] `_parse_frontmatter` paaugstināts no `generate.py:143` uz `_common.py` — 3 call sites caur 2 sub-page moduļiem (analyses.py: `_load_wiki_profile` + `_load_analyses`; syntheses.py: `_load_syntheses`). NB: F3f.4 audits atklāja, ka `_fetch_blog_posts` NEIZSAUC `_parse_frontmatter` (blog posts nāk no `context_notes` DB tabulas, ne markdown failiem). Promotion paliek pamatota — cycle avoidance.
- [x] Combined `analizes.html` index page paliek orchestrator-ā līdz F3f.1 (dashboard) — koplieto context (analyses, syntheses, blog_posts, trends_data, context_notes) ar index hero.
- [x] Char fixture `render_baseline_analyses.json` — 1 analizes/* + 1 sintezes/* + analizes.html sanity hash.
- [x] **Plan deviation #1:** `_parse_frontmatter` → `_common.py` (not in original F3f.5 scope; F3-prep rule).
- [x] **Plan deviation #2:** Char fixture iekļauj `analizes.html` papildus per-page (ekstra safety, beyond plan).
- [x] **Plan deviation #3:** `_load_wiki_profile` flagged kā dead code post-F3b — pārvietots per plāns, restoration ticketed F3g checklist.
- [x] **Plan deviation #4:** `tests/test_load_syntheses.py` import → `src.render.syntheses` direct (F3-prep convention, retroactive).
- [x] **Stale baseline refresh (commit `6cdd788`)** — 3 char fixtures driftēja master HEAD pirms PR (contradictions/graph/politicians). REGEN refresh + F3f.5 baseline bootstrap atsevišķā commit-ā pirms refaktoringa. Precedents: commit `3064541`. Master pre-PR: 903 passed + 4 failed; post-PR: **910 passed**, 2 xfailed, 1 xpassed.
- [x] Reviewer verdict: *Clean. Ready to merge.* Zero MUST-FIX, zero SHOULD-FIX. Review nits commit `dd9ee4c` — fix render_syntheses signature in plan (3 args, not 4 — plan was wrong, impl matches master) + ticket _load_wiki_profile F3g follow-up.

generate.py LOC: 1187 → 1031 (-156). Re-export shim widens by 7 names (6 moved + 1 promoted). **Total trajectory: 4250 → 1031 (-76%).**

### F3f.4 — `blog.py` ✅ PAVEIKTA — PR #15, merge `0dcaf66`

Single leaf module — blog index + per-post pages + ingest helpers.

- [x] `blog.py` (321 LOC, leaf): `_SHORTENER_CANONICAL` + `_MD_LINK_RE`, `_rewrite_shortener_link_labels`, `_fetch_context_notes`, `_fetch_blog_posts`, `render_blog(env, atmina_dir, blog_posts)` → emits blog.html + blog/<slug>.html (~25 daily/weekly briefs).
- [x] Imports: `_common.BASE_URL` + `_render_page` + `src.briefs.strip_visual_brief_block` (no cycle — briefs.py importē tikai `src.db`). Module-level import is cleaner than the prior lazy in-loop import in generate.py orchestrator.
- [x] Char fixture `render_baseline_blog.json` — blog.html + 25 blog/<slug>.html. Dynamic count, REGEN-per-ingest pattern (likumprojekti F3e precedents).
- [x] **Plan deviation #1:** `render_blog(env, atmina_dir, blog_posts)` 3 args, ne 4. Plāns paredzēja `context_notes` 4. arg, bet `context_notes` ir tikai orchestrator-owned `analizes.html` index render consumer. Tāda pati deviācija kā F3f.5 `render_syntheses`.
- [x] **Plan deviation #2 — F3f.2 cross-ref bookkeeping iebūvēts:** `parties.py:185` un `_common.py:511` komentāri tagad norāda `src/render/x.py` (post-F3f.2 location), ne legacy `generate.py`. Plan paste-block to apstiprināja kā "F3f.2 follow-up bookkeeping for F3f.4 or F3g".
- [x] **Plan deviation #3 — F3f.5 docstring kļūda izlabota:** `_common.py:182-189` `_parse_frontmatter` docstring kļūdaini apgalvoja "three sub-page consumers" ar `_fetch_blog_posts` kā trešo. Patiesie consumeri ir tikai `analyses.py` + `syntheses.py`. Promotion paliek pamatota (cycle avoidance), bet skaitīšana izlabota.
- [x] **Plan deviation #4 — `src/briefs.py:118`** narrative path reference no `src/generate.py:_fetch_blog_posts()` → `src/render/blog.py:_fetch_blog_posts()`.
- [x] Reviewer verdict (PR #15): *Clean — merge as-is.* Zero MUST/SHOULD-FIX. Byte-equivalence verificēta AST-līmenī (3 funkcijas: `_rewrite_shortener_link_labels` 880 chars, `_fetch_context_notes` 283 chars, `_fetch_blog_posts` 8518 chars — visas verbatim). Vienīgais NICE-TO-HAVE — `agent_api_inventory.txt` backfill — atstāts F3g pilnam rewrite (per dd9ee4c plana checklist).

generate.py LOC: 1031 → 772 (-259). Re-export shim widens by 4 names. **Total trajectory: 4250 → 772 (-82%).**

### F3f.1 — `dashboard.py` ✅ PAVEIKTA — PR #16, merge `385071c` — **F3f noslēgts**

Last F3f sub-phase. Single leaf module — homepage hero + combined analizes index.

- [x] `dashboard.py` (293 LOC, leaf): `_fetch_stats`, `_sparkline_svg`, `_fetch_hero_v2_data`, `_fetch_trends_data`, `render_dashboard(env, db, atmina_dir, stats, contradictions, votes, blog_posts, syntheses, analyses, trends_data, context_notes, days_until)` → emits index.html + analizes.html.
- [x] Imports: `_common.{BASE_URL, PARTY_COLORS, _render_page, _slugify}` + `src.db.{today_lv, CLEAN_START_DATE}` + stdlib + extern (markupsafe.Markup, jinja2.Environment).
- [x] Char fixture `render_baseline_dashboard.json` — index.html + analizes.html SHAs. analizes.html SHA cross-asserted ar F3f.5 fixture (`render_baseline_analyses.json`).
- [x] **Plan deviation:** `render_dashboard` rendere ABAS lapas — index.html (block #1) UN analizes.html (block #6). Plan paste-block to eksplicīti autorizē. Co-locating saglabā data flow skaidrību (abi koplieto stats/blog_posts/syntheses/analyses/trends_data/context_notes).
- [x] **Pass-through:** 12 args (3 primary + 9 data). Garākais peer (peer max bija render_votes 6 args).
- [x] **Stale baseline refresh (commit `b249690`)** — x.html driftēja master HEAD pirms PR (data ingest kopš F3f.4 merge). REGEN refresh + F3f.1 baseline bootstrap atsevišķā commit-ā pirms refaktoringa. Precedents: commit `6cdd788` (F3f.5).
- [x] Reviewer verdict (PR #16): *CLEAN. Merge.* Zero MUST/SHOULD-FIX. Reviewer matemātiski verificēja `analizes.html` placement-change byte-identitāti (env.globals nav mutēts post-startup; pre-fetched lists nav mutēti in-place; SHA cross-asserts pierāda).

generate.py LOC: 772 → 558 (-214). Re-export shim widens by 5 names. **Total trajectory: 4250 → 558 (-87%).**

Katrai F3 apakšfāzei tas pats šablons (proven F3a-F3f.1 pattern):
- Pārvietot `_fetch_*`, `_enrich_*`, `_generate_*` funkcijas (pluss `_load_*` syntheses gadījumā)
- Atstāt re-export shim `src/generate.py`
- `tests/test_generate.py` zaļš
- Byte-diff ģenerēto HTML ar baseline (worktree-portable post-F3g-pre; synthesis-image mirror vairs nav vajadzīgs)
- Commit + push

### F3g — pēdējais (cycle-debt clear) ✅ PAVEIKTA — PR #17, merge `6ab0019` — **F3 PILNĪBĀ PABEIGTS**

Last F3 step. Orchestrator lifted, render_parties self-contained, wiki_profile dead code restored, agent inventory rewritten.

- [x] `src/generate.py` paliek **173 LOC kā re-export shim** (`<50 LOC` target ignored shim widening; 14 sub-page imports + ~85 symbol re-exports — necessary for tests+agent contract)
- [x] `generate_public_site` + `_generate_sitemap` + `_generate_og_image` lifted uz `src/render/_orchestrator.py` (444 LOC) + `src/render/__init__.py` re-eksports
- [x] **Kanoniskais publiskais ceļš:** `from src.render import generate_public_site`
- [x] `render_parties` self-contained (F3g.2 — pieņem `parties` arg, neatgriež)
- [x] ~~`_load_syntheses` CWD-fix~~ — DONE in F3g-pre (PR #11)
- [x] **F3f.5 follow-up** — `_load_wiki_profile` promoted no `analyses.py` uz `_common.py`; callsite restored `politicians.py:310` (F3g.3). 162 `wiki/persons/*.md` tagad satur ~150 politiku detail pages.
- [x] **agent_api_inventory.txt full rewrite** — 17 src/render/* moduļi + ~85 shim simboli + status header bumps + canonical `src.render` path documented (F3g.7).
- [x] Reviewer verdict (PR #17): *SHIP.* Zero MUST/SHOULD-FIX. Cycle-safety verified in practice (`from src.render._common import _slugify` runs without error).

**F3g deferred items (low-value cleanup, not blocking F3 closure):**
- [ ] F3g.4 — `_chronologize_contradiction(row, key_pairs)` + `_tension_filter_axes(tensions)` helpers in `_common` (F3f.3 reviewer NICE-TO-HAVE)
- [ ] F3g.5 — `src/render/blog.py:125,167` redundant `import re as _re` / `_re2`; `blog.py:173` `from datetime import date as _date`; `src/render/dashboard.py:95` inline `from datetime import datetime, timedelta` (byte-equivalent carryovers)
- [ ] F3g.6 — char fixture dedup (analizes.html SHA in `render_baseline_analyses.json` + `render_baseline_dashboard.json`)
- [ ] Refactor `tests/test_generate.py` uz `tests/test_render_<page>.py` ja >1500 LOC

generate.py LOC: 558 → 173 (-385). **Total trajectory: 4250 → 173 (-96%). Fāze 3 PILNĪBĀ PABEIGTA.**

---

## Fāze 4 — `saeima.py` → `src/saeima/` pakete (1-2 sesijas) ✅ PAVEIKTA — PR #4, merge commit `b341d4e`

⚠️ **Tehniska piezīme:** Python neatļauj reizē `src/saeima.py` un `src/saeima/` paketi.

**Mācība F4+:** Plāna sākotnējais 5-moduļu shēma (schema/parsing/votes/bills/claims pa funkcionālo lomu) bija circular pa runtime imports — `VoteResult` plūsma starp parsing/votes un `_motif_to_topic` plūsma starp votes/claims radītu `from src.saeima.X import Y` ciklus. Reālais izpildītais split (sk. `wiki/CHANGELOG.md` 2026-04-29 § Fāze 4) noslēdzās ar 4 deviations:

1. **`parse_vote_snapshot` glabājas `votes.py`**, ne `parsing.py` — `VoteResult` produktu loģika grupējas ar pārējo vote pipeline-u; izvairās no parsing↔votes cikla.
2. **`match_submitters_to_politicians` glabājas `votes.py`**, ne `bills.py` — koplieto `_build_name_index` ar siblinga `match_deputies_to_politicians`.
3. **`generate_claims_from_votes` glabājas `votes.py`**, ne `claims.py` — claims.py paliek tīrs topic-mapping leaf.
4. **`SAEIMA_BASE_URL` + `_resolve_vote_url` + `_parse_vote_datetime` glabājas `bills.py`** — koplietojami helperi, ievietoti leaf modulī, lai gan votes, gan claims var importēt bez votes↔claims cikla.

**Šablons F3-am:** vispirms identificēt **leaf moduļus** (neimportē no paketes) un **fan-out moduļus** (importē no leaf-iem). Plāno katram modulim vienu virzienu — "share helpers" augšup vai "consumers" lejup, ne abus.

- [x] **F4.0. Characterization fixtures** (commit `d92164f`)
  - `tests/fixtures/saeima_chars_expected.json` — frozen baseline (19 motifs × 3 funkcijas + 1 agenda + 3 vote snapshots)
  - `tests/test_saeima_chars.py` ar `REGEN=1` env baseline regen
- [x] **F4.1. `git mv src/saeima.py src/saeima_legacy.py`** (commit `0f3f273`) — pakešu skelets ar __init__.py re-eksport shim
- [x] **F4.2. `src/saeima/schema.py`** (commit `89d9000`) — `init_saeima_tables` + `init_saeima_bills` izvilkti
- [x] **F4.3+F4.4. Atomic split** (commit `11ca874`):
  - `bills.py` — bill regexes + classification + ops + AgendaBill + SAEIMA_BASE_URL + URL/datuma helperi (leaf)
  - `parsing.py` — `parse_agenda_snapshot` + helperi (importē AgendaBill no bills)
  - `claims.py` — `_stem`, `_word`, `_MOTIF_TOPIC_MAP`, `_motif_to_topic`, `_vote_salience` (leaf)
  - `votes.py` — `IndividualVote`/`VoteResult`, `parse_vote_snapshot`, `_build_name_index`, `match_deputies_to_politicians`, `match_submitters_to_politicians`, `store_vote`, `generate_claims_from_votes`, `process_vote_snapshot` (depends on bills + claims)
  - `git rm src/saeima_legacy.py` + `__init__.py` re-eksportē 28 simbolus no sub-moduļiem
- [x] **F4.5. Iekšējo callsites + path references** atjaunināti — `.claude/agents/saeima-tracker.md`, `wiki/operations/saeima-bills.md` (3 path references), `src/db.py` (2 narrative comments)
- [x] **F4.6. Wiki + plan doc sync** — `wiki/CHANGELOG.md` jauns ieraksts, šis plāna fails atjaunina

### Testi
- [x] **Eksistē:** `tests/test_saeima.py`, `tests/test_saeima_bills.py`, `tests/test_phase_1b_ii.py`, `tests/test_generate_bills.py`, `tests/test_audit_saeima_vote_results.py` — visi zaļi
- [x] **Eksistē:** `tests/test_invariants.py` — `test_inv6_saeima_vote_document_id_nullable` zaļš
- [x] **Jauns:** `tests/test_saeima_chars.py` — 3 characterization tests pret iesaldēto baseline

### Verifikācija
- [x] `bash scripts/check.sh` exit 0 — 887 passed (884 + 3 chars), 2 xfailed (pre-existing), 1 xpassed
- [x] Manual smoke `python -c "from src.saeima import store_vote, init_saeima_tables, parse_agenda_snapshot, upsert_bill, match_submitters_to_politicians, process_vote_snapshot, resolve_bill_from_motif, append_bill_stage, _reading_from_motif, LAW_TITLE_RE, load_laws_index; print('ok')"` — visi simboli importējami
- [x] `@saeima-tracker` aģenta tools imports neielūza — visi 8 simboli (`parse_agenda_snapshot, upsert_bill, match_submitters_to_politicians, init_saeima_tables, process_vote_snapshot, resolve_bill_from_motif, append_bill_stage, _reading_from_motif`) eksponēti caur __init__.py

---

## Fāze 5 — Migrāciju formāts (1 sesija — TIKAI kad nāk nākamā DDL maiņa)

### Darbi
- [ ] **F5.1. `migrations/__init__.py` + `migrations/_runner.py`**
- [ ] **F5.2. `schema_migrations` tabula `src/schema.sql`:**
  ```sql
  CREATE TABLE IF NOT EXISTS schema_migrations (
      version TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL DEFAULT (datetime('now')),
      checksum TEXT
  );
  ```
- [ ] **F5.3. `src/db.py init_db()` izsauc `apply_migrations(conn)` pēc `executescript(schema.sql)`**
- [ ] **F5.4. `migrations/0001_<nakamais_realais_DDL>.py`** — atstāt fāzi 5 atvērtu līdz reālai vajadzībai

### Testi
- [ ] **Jauns:** `tests/test_migrations.py`:
  - `test_apply_migrations_idempotent`
  - `test_apply_migrations_records_version`
  - `test_failed_migration_does_not_record`

### Commit + push
```bash
git add migrations/ src/db.py src/schema.sql tests/test_migrations.py
git commit -m "feat(db): add schema_migrations runner for forward DDL changes"
git push
```

---

## Globālie noteikumi visās fāzēs

1. **Pirms katras fāzes:** `bash scripts/check.sh` zaļš uz tagadējā master
2. **Pēc katras fāzes:** `bash scripts/check.sh` zaļš + manuāls `generate_public_site()` smoke
3. **Commit messages:** sekot eksistējošajam stilam (`refactor(scope):`, `test:`, `feat:`)
4. **Push pēc katras fāzes** (vai pēc katra atomic commit fāzes vidū)
5. **Rollback:** `git reset --hard pre-refactor-2026-04-29` + DB restore no backup
6. **Aģentu prompti:** ja kāda funkcija pārvietojas BEZ shim, atjaunināt `.claude/agents/*.md` tajā pašā commit

## Aptuvenais laika skats

| Fāze | Sesijas | Risk | Statuss |
|------|---------|------|---------|
| Pirmsdarbi | 0.5 | Zems | ✅ |
| F0 Drošības tīkls | 1-2 | Zems | ✅ PR #1 `b0f9871` |
| F1 Matcher | 1-2 | Zems | ✅ PR #2 `4f4d25d` |
| F2 schema.sql | 1 | Zems | ✅ PR #3 `94466aa` |
| F3 generate.py → render/ | 3-5 | Vidējs | ✅ **F3 PILNĪBĀ PABEIGTS** PR #5-#17 (15 PR); 4250 → 173 LOC (-96%) |
| F4 saeima.py → pakete | 1-2 | Vidējs | ✅ PR #4 `b341d4e` (1 sesija) |
| F5 Migrācijas | 1 | Atlikt līdz vajadzībai | ⏳ Atlikta |

**Nesam mērķi pabeigt secīgi:** F3 un F4 ir savstarpēji neatkarīgi. F4 paveikts pirms F3 (mazāks blast radius); F3 atlikt līdz pieejama 3-5 sesiju logs.

---

## Nākamā sesija — paste-friendly start

Paste šo bloku pirmajā ziņā, kad atsāc darbu (vai pavēli aģentam to izlasīt). Atlikusi **F3f.1 + F3f.4 + F3g** + F5 (conditional, tikai kad nāk DDL maiņa).

```
KONTEKSTS

- Tu esi atmiņas (atmina) refaktoringa noslēgumā. Lasi CLAUDE.md PIRMĀM
  KĀRTĀM (datu kontrakti + pipeline invariants).
- Master ir tīrs: HEAD pēc F3f.1 merge — commit `385071c` (PR #16).
  PR #1-#16 visi mergēti. **F3f noslēgts** — atlicis tikai F3g.
  Tag `pre-refactor-2026-04-29` ir rollback punkts uz state PIRMS
  jebkāda refaktoringa.
- Plāns: docs/plans/refactor-plan-2026-04-29.md — Fāzes 0, 1, 2, 4 +
  F3a-F3e + F3g-pre + F3f.2 + F3f.3 + F3f.5 + F3f.4 + F3f.1 paveiktas
  (atzīmētas ✅ ar PR/commit ID). Atlikušas F3g + F5.
- Baseline pēc F3f.1: `bash scripts/check.sh` exit 0 = 914 passed
  (912 pre-F3f.1 + 2 jauni F3f.1 char tests; segums: pretrunas,
  politiki, personas, partijas, pozicijas, zinas, statistika,
  balsojumi, likumprojekti, likumi, x, spriedzes, saites,
  analizes/*, sintezes/*, blog/*, index.html, analizes.html —
  417+ byte-identical pages), 2 xfailed (pre-existing), 1 xpassed.
- generate.py LOC trajectory: 4250 (F3a sākums) → 3733 → 3699 →
  3198 → 3003 → 2419 → 1783 → 1536 → 1187 → 1031 → 772 → 558
  (post-F3f.1, -87% kopā). Mērķis F3g: <50 LOC re-export shim.
- F3 retrospekti wiki/CHANGELOG.md:
  § 2026-04-29 F3a-F3e (sub-phase table + module map + F3e CWD atklāsme),
  § 2026-04-29 F3g-pre + F3f.2 + F3f.3 (vakara sesija — 3 PR),
  § 2026-04-29 F3f.5 (nakts sesija — analyses.py + syntheses.py + _parse_frontmatter promotion),
  § 2026-04-29 F3f.4 (vēla nakts sesija — blog.py + F3f.2 cross-ref bookkeeping + F3f.5 docstring fix),
  § 2026-04-30 F3f.1 (agra rīta sesija — dashboard.py — F3f noslēgts).
- Aģentu API inventarizācija: docs/refactor/agent_api_inventory.txt
  — atjaunināta post-F3f.3; pilna F3f.5+F3f.4+F3f.1 sync atlikta uz
  F3g (per reviewer NICE-TO-HAVE, kanoniskais src.render path
  landing F3g-ā). Doc-debt augstāks; F3g full rewrite ietver
  ~15 moduļus + ~85 shim simbolus.
- Production deploy: 2026-04-29 ~22:00 (deploy.sh exit 0; rsync
  incremental ~316KB pēc F3g-pre/F3f.2/F3f.3 merge + Pūpols
  pretruna #25 reformatting "28. aprīlī ... 29. aprīlī ...").

DARBA PLŪSMA (proven F1+F2+F4+F3a-F3f.1 pattern)

1. git worktree add .worktrees/<branch> -b feature/<branch>
   ⚠️ Run no project root, NE no cita worktree. PowerShell session
   var saglabāt iepriekšējo CWD un rezultēt nested worktree path —
   ja tā gadās, `git worktree prune` + `rm -rf .worktrees/<stale>`
   + recreate from project root.
2. (DB testos): New-Item -ItemType HardLink -Path
   .worktrees/<branch>/data/atmina.db -Target (Resolve-Path
   data/atmina.db).Path. csp.db + events.yaml ir git-tracked
   (override *.db gitignore), tāpēc tos nav jāhardlinko — worktree
   paņem automātiski.
   ✅ F3g-pre (PR #11) atrisina pre-F3e CWD-bug — `_load_syntheses`
   tagad ņem `atmina_dir` argumentu. Fresh worktrees vairs nav
   jākopē `output/atmina/images/synthesis/`; char tests pass
   konsekventi visās worktrees.
3. Uzraksti characterization fixtures + tests PIRMS koda kustināšanas.
   F3a-F3e šablons: tests/test_render_chars.py + tests/fixtures/
   render_baseline_<phase>.json ar SHA-256 par katru lapu. `REGEN=1
   pytest tests/test_render_chars.py` bootstraps baseline; bez REGEN
   assert. Pievieno _capture_observed_<phase>() helper +
   EXPECTED_FILE_<PHASE> ceļu + 2-4 testus (index + detail).
4. Pārvieto kodu pa moduļiem. Ja kāds simbols figurē
   .claude/agents/*.md, scripts/* vai testos — atstāj re-export shim
   caur src/generate.py top-level (`from src.render.X import (...)
   # noqa: F401  re-exported for tests/shim`). Tikai
   `generate_public_site` un `generate_statistika` ir aģentu API
   — pārējie 66+ simboli ir test-suite stable contract.
5. Atjaunini iekšējos importētājus uz jauno ceļu (ne caur shim) — t.i.,
   ja `src/render/<page>.py` vajag _common helperi, importē tieši no
   `src.render._common`, ne caur `src.generate`.
6. bash scripts/check.sh worktree exit 0 PIRMS commit.
7. Commit ar paskaidrojošu message + Co-Authored-By trailer. ⚠️ uz
   Windows: ja message satur Latvian em-dash vai diakritiku, izmanto
   `git commit -F .git-commit-msg.tmp` (Write tool), ne PowerShell
   heredoc — tas plīst.
8. Push, gh pr create, dispatch superpowers:code-reviewer agent pār
   diff. Atrisini should-fix punktus follow-up commit-ā TAJĀ PAŠĀ PR-ā
   (F3b-F3e šablons: `docs(plan): F3X review nits — ...` commit ar
   plan deviation note + status sync). Tad merge.
9. Master pull, `git worktree remove --force .worktrees/<branch>` +
   `git branch -D feature/<branch>` (Windows file-lock dēļ --force);
   `git worktree prune` cleanup. Ja `.worktrees/<branch>` palicis
   iznīcināms (Permission denied), Remove-Item -Recurse -Force pēc
   prune-a parasti strādā.

CRITICAL ARHITEKTONISKIE NOTEIKUMI:

(a) Pirms split, identificē LEAF moduļus (neimportē no paketes) un
    FAN-OUT moduļus (importē no leaf-iem). F4 mācība (circular imports)
    veiksmīgi izvairīta F3a-F3e pa proaktīvām leaf promotions PIRMS
    peer sub-page rakstīšanas. F3-prep + F3b + F3d šablons: ja
    sub-page A un B abas vajag X, promote X uz _common AGRĀK.

(b) Sub-page modulis NEDRĪKST importēt no peer sub-page (ne politicians
    ↔ personas, ne parties ↔ politicians, ne news ↔ positions, ne
    bills ↔ laws ↔ votes). Tikai no `_common` un stdlib + extern
    (jinja2, brotli, httpx, markdown, ...).

(c) `src/render/__init__.py` paliek tukšs (tikai docstring) līdz F3g.
    NEPIEVIENO `from .X import Y` līnijas — tas trigger sub-page
    `__init__.py` izpildi, kas, ja eksponē generate_public_site
    (kurš pats importē no _common), rada cycle.

⚠️ F3a-F3f.1 TEHNISKIE PARĀDI (atstāti F3g atrisināt — F3f noslēgts):
- `src/render/__init__.py` NEEKSPONĒ `generate_public_site` (cycle)
- `render_parties` atgriež `parties_data: list[dict]`, jo
  `_generate_sitemap` (vēl `generate.py`-ā) tas vajadzīgs
- ✅ ~~`_load_syntheses` CWD bug~~ — RESOLVED in F3g-pre (PR #11):
  `_load_syntheses(atmina_dir)` signature change, default arg
  `Path("output/atmina")` preserves prod behavior; 3 unit tests
  in `tests/test_load_syntheses.py` lock down invariant.
- F3f.3 review nice-to-haves (PR #13 deferred):
  - `_chronologize_contradiction(row, key_pairs)` helper for
    `_common.py` — currently 3 duplicates: `links.py:259-272`,
    `_common._enrich_contradiction:590-608`,
    `social_agent/candidates.py:93`.
  - `_tension_filter_axes(tensions) -> dict` helper for
    `_common.py` — currently duplicated in tensions.py:48-56 +
    links.py:338-346.
- ✅ ~~F3f.2 follow-up (PR #12 deferred): comment cross-refs in
  parties.py:185 + _common.py:484~~ — DONE in F3f.4 (PR #15).
- F3f.5 follow-up (PR #14 deferred): restore `_load_wiki_profile`
  callsite in `src/render/politicians.py:310` (currently hardcodes
  `wiki_profile = None`; F3b regression PR #7). Function now lives
  in `src/render/analyses.py` as orphaned code with docstring note.
  When restored, consider promoting `_load_wiki_profile` to
  `_common.py` (politicians.py concern, not analyses.py).
- F3f.4 follow-up (PR #15 deferred): vestigial `import re as _re`
  / `_re2` aliases in `src/render/blog.py:125,167` + inline
  `from datetime import date as _date` at `blog.py:173` are
  byte-equivalence carryovers; F3g cleanup pass.
- F3f.1 follow-up (PR #16 deferred): vestigial inline `from datetime
  import datetime, timedelta` at `src/render/dashboard.py:95`
  (shadows top-level import); plus `src/generate.py` post-F3f.1
  vestigial top-level imports — `import json`, `import re`,
  `import sqlite3`, `from datetime import datetime, timedelta, timezone`,
  `from markupsafe import Markup`, `now_lv_dt + CLEAN_START_DATE`
  no `src.db` (visi vairs nelieto, ruff F401 silenced šim failam
  per pyproject.toml:50). F3g vestige sweep.
- F3f.1 follow-up (PR #16 deferred): char fixture analizes.html
  SHA divos failos (`render_baseline_analyses.json` F3f.5 un
  `render_baseline_dashboard.json` F3f.1). Cross-assertion redundancy
  ir pieņemama drošībai; F3g cleanup pass dedupē vai paliek apzināti.
- F3a-F3f.1 follow-up: full `agent_api_inventory.txt` rewrite — **15
  src/render/* moduļi + ~85 shim simboli** + status header bumps.
  Doc-debt grew across F3f.5 + F3f.4 + F3f.1. F3g lands the canonical
  src.render path; right time for the rewrite.

F3g uzdevums (final F3 step):
1) Pārvieto `generate_public_site` body uz `src/render/__init__.py`
   (vai `src/render/_orchestrator.py` un `__init__.py` re-eksportē).
   Pārvieto `_generate_sitemap` un `_render_og_image` arī.
2) Atjaunina `src/generate.py` uz tīru re-export shim (`from
   src.render import generate_public_site, generate_statistika` +
   visi tests-importētie privātie simboli no sub-pages). <50 LOC mērķis.
3) `render_parties` var kļūt self-contained (nepasniedz
   parties_data atpakaļ — sitemap orchestrate pats).
4) ✅ ~~`_load_syntheses` CWD fix~~ — DONE in F3g-pre (PR #11).
5) Apply F3f.3 review nice-to-haves: `_chronologize_contradiction`
   + `_tension_filter_axes` helpers in `_common`.
6) Update F3f.2 comment cross-refs (`parties.py:185`,
   `_common.py:484`) to point at `src/render/x.py` after blog.py
   extraction stabilizes.
7) Atjaunina docs/refactor/agent_api_inventory.txt § src.generate
   un § src.render uz jauno kanonisko ceļu (`from src.render import
   generate_public_site` ir publiskais līgums; `src.generate` ir
   shim).

KAS ATLICIS (izvēlies vienu) — **F3f noslēgts; tikai F3g + F5 atlikuši**

A) ★ F3g — cycle-debt clear (1 sesija, vidējs). **PĒDĒJAIS F3 solis.**
   Lift `generate_public_site` + `_generate_sitemap` +
   `_generate_og_image` uz `src/render/__init__.py` vai
   `src/render/_orchestrator.py`. `src/generate.py` kļūst
   ~30-50 LOC re-export shim. Atjaunini agent_api_inventory.txt
   uz `src.render` kā kanonisko publisko ceļu (**full rewrite — 15
   moduļi + ~85 shim simboli**). `render_parties` self-contained
   (atmet `parties_data` return). Apply F3f.3 review nice-to-haves
   (`_chronologize_contradiction` + `_tension_filter_axes` helpers
   in `_common`). Restore `_load_wiki_profile` callsite in
   politicians.py:310 (F3f.5 follow-up — currently dead code).
   F3f.4 + F3f.1 vestigial alias/import cleanup (blog.py + dashboard.py +
   src/generate.py top-level vestige). Char fixture dedup
   (analizes.html in F3f.5 + F3f.1 fixtures). `tests/test_generate.py`
   reorganizē uz `tests/test_render_<page>.py` ja >1500 LOC.

B) Fāze 5 — migrāciju formāts (1 sesija — TIKAI kad nāk DDL maiņa).
   Atlikt līdz reālas vajadzības.

C) Pauze. Refactor var atsākt jebkurā brīdī — nav gaida laiks.
   Visi paveiktie F3a-F3f.1 posmi ir reverzibli ar
   `git revert <merge-commit>` per-fāzi (PR squash + char-fixture
   safety net).

Pirms ja piesakies pie F3g vai F5, palaid `bash scripts/check.sh`
master un apstiprini exit 0 + 914 passed (vai jaunāks skaits, ja
citi commits aiz F3f.1 merge ir mergēti).
```

