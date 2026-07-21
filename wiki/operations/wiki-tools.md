# Rīku atsauce — atmina analīzes funkcijas

_Visas funkcijas, ko var izsaukt analīzes sesijas laikā._

---

## 1. Analīzes pipeline

### get_pending_politicians(days=1) → list[dict]
**Avots:** `src/analyze.py`
Atgriež politiķus, kam ir jauni dokumenti kopš pēdējās analīzes.
```python
from src.analyze import get_pending_politicians
pending = get_pending_politicians(days=1)
for p in pending: print(f"{p['name']} ({p['party']}): {p['doc_count']} docs")
```

### get_politician_documents(pid, days=1, max_results=20) → list[dict]
**Avots:** `src/analyze.py`
Atgriež nesenos dokumentus politiķim. Filtrē tikai `role='subject'` (nevis mentioned) un `reviewed_at IS NULL` (tikai vēl neapskatītos). Saturs saīsināts līdz ~2000 vārdiem.
```python
from src.analyze import get_politician_documents
docs = get_politician_documents(pid=42, days=1)
```

### get_existing_claims(pid, days=90) → list[dict]
**Avots:** `src/analyze.py`
Atgriež esošos apgalvojumus pretrunu noteikšanai. Katrs: {id, topic, stance, quote, confidence, salience, stated_at, source_url}.
```python
from src.analyze import get_existing_claims
claims = get_existing_claims(pid=42, days=90)
```

### save_analysis(pid, analysis_date, sentiment, topics, quotes, brief, confidence, claims=None, position_shifts=None, empty_doc_ids=None) → dict
**Avots:** `src/analyze.py`
Saglabā analīzi + apgalvojumus + automātiski atzīmē reviewed dokumentus. Viens izsaukums visam.
- `sentiment` vienmēr `0.0` (neitrāls)
- `claims` = saraksts ar dict: {document_id, topic, stance, quote, confidence, reasoning, salience, source_url, stated_at, **claim_type**}
  - `claim_type` ir neobligāts; noklusējums `'position'` (mediju/X retorika). `@claim-extractor` to nekad nemaina. `'saeima_vote'` ir rezervēts `@saeima-tracker` balsojumu ierakstiem un to uzstāda `generate_claims_from_votes()` automātiski.
- `empty_doc_ids` = dokumentu ID, ko skatījies bet neizvilki claims (ceremoniāli/dublikāti). Obligāts, lai tie netiktu atkal atgriezti backlog.
- **Atomicity (S10, 2026-04-11):** viss analīzes + claims + reviewed-docs saglabājums iet vienā SQLite transakcijā. Katastrofāls DB write failure (disk full, lock timeout) atgriež `status="failed"` ar `transaction_rolled_back` failure un pilnībā atceļ izmaiņas. Validation-level drops (missing source_url) paliek best-effort skip ar `status="partial"`.
- **Indirect-reference gate (2026-04-22):** ja claim `reasoning` satur stiprus indirect-reference markerus (`nav paša pozīcij`, `pašam nav ekstraktēj`, `bare retweet`, `pure retweet`, `does not speak`, `tikai pieminē` u.c. — sk. `_INDIRECT_MARKERS_LOWER` tuple `src/analyze.py`), `save_analysis` automātiski prepend `NEEDS_REVIEW:` prefiksu reasoning laukam pirms `store_claim`. Claim tiek saglabāts (nevis nomests) — `@quality-reviewer` triāžē NEEDS_REVIEW ierakstus. Soft gate ir ar nolūku, jo hard-drop false-positive uz likumīgiem "netiešs citāts caur LETA" saglabājumiem (~50% no round-1 saves). Sk. [[CHANGELOG]] § 2026-04-22 batch-drift fixes.
- Contradictions vairs netiek automātiski salīdzinātas no `save_analysis` — analītiķis manuāli izsauc `search_similar_claims` (ar direcional `claim_type_filter`) un `store_contradiction` kad atrod reālu pretrunu.

---

## 2. Datu saglabāšana

### store_claim(opponent_id, document_id, topic, stance, quote=None, confidence=0.5, reasoning="", salience=0.5, source_url=None, stated_at=None, claim_type="position", db=None) → str
**Avots:** `src/tools.py`
Saglabā vienu apgalvojumu. `topic` automātiski normalizēts caur topic_map.
- **`claim_type`** — `'position'` (noklusējums, mediju/X retorika) vai `'saeima_vote'` (Saeimas balsojumu ieraksti). Phase C filtri izmanto šo kolonnu, lai nodalītu "pozīcijas" no "balsojumiem" visās galvenēs un lapās.
- **`db`** — neobligāts externally-managed SQLite connection. Kad nodots, caller pārvalda transakcijas lifecycle (`save_analysis` to izmanto, lai visu partiju saglabātu vienā atomiskā transakcijā). Parasti nav jāizsauc tieši.
- Idempotents uz `(opponent_id, source_url, topic)` — atkārtota izsaukšana atgriež esošo claim_id bez jauna ieraksta.
```python
from src.tools import store_claim
store_claim(opponent_id=42, document_id=100, topic="Budžets", stance="Atbalsta nodokļu samazināšanu", confidence=0.7, salience=0.6, source_url="https://...")
```

### store_contradiction(opponent_id, old_claim_id, new_claim_id, topic, summary, severity, salience) → str
**Avots:** `src/tools.py`
Reģistrē pretrunu. `severity`: "direct_contradiction", "reversal", "minor_shift".
```python
from src.tools import store_contradiction
store_contradiction(opponent_id=42, old_claim_id=100, new_claim_id=200, topic="Budžets", summary="Iepriekš atbalstīja, tagad iebilst", severity="reversal", salience=0.8)
```

### store_context_note(opponent_id=None, topic=None, note_type="context", content="", source=None, expires_at=None) → str
**Avots:** `src/tools.py`
Pievieno konteksta piezīmi. `note_type`: "context", "polling", "event", "tip", "correction", "daily_brief", "weekly_brief".
```python
from src.tools import store_context_note
store_context_note(opponent_id=42, topic="Rail Baltica", note_type="context", content="Ministru kabinets apstiprinājis jaunu finansējuma modeli", source="https://...")
```

### store_analysis(opponent_id, period_start, period_end, analysis_json) → str
**Avots:** `src/tools.py`
Saglabā perioda analīzi kā JSON.

---

## 3. Datu izgūšana

### retrieve_context(opponent_id, days=1, query=None, max_results=20) → str
**Avots:** `src/tools.py`
Ja `query` ir norādīts — veic semantisko meklēšanu ar embedding vektoriem. Citādi atgriež jaunākos dokumentus.
```python
from src.tools import retrieve_context
import json
result = json.loads(retrieve_context(opponent_id=42, query="nodokļu reforma"))
```

### get_opponent_summary(opponent_id) → str
**Avots:** `src/tools.py`
Pilna politiķa kopsavilkuma JSON: profils, apgalvojumu skaits, pretrunas, pēdējās analīzes.

### query_claims(opponent_id, topic=None) → str
**Avots:** `src/tools.py`
Atgriež visus apgalvojumus politiķim (filtrējami pēc tēmas).

### search_similar_claims(opponent_id, claim_text, top_k=10, claim_type_filter=None) → str
**Avots:** `src/tools.py`
Embedding meklēšana — atrod līdzīgus apgalvojumus. Izmanto pretrunu noteikšanai.
- **`claim_type_filter`** (Phase A, 2026-04-11) — neobligāts `list[str]`, piem. `['position']` vai `['position', 'saeima_vote']`. `None` = visi tipi (legacy). Izmanto **directionally** per call-site:
  - Pretrunas no position viedokļa → `['position', 'saeima_vote']` (iekļaut retoriku un balsojumus — rhetoric-vs-action)
  - Pretrunas no saeima_vote viedokļa → `['position']` (vote-vs-vote ir procesuāls troksnis)
  - Vispārēja līdzīguma meklēšana → `None`
- Filtri (`opponent_id`, `claim_type_filter`, `speaker_scope`) kopš 2026-07-24 tiek piemēroti k-NN vaicājuma IEKŠIENĒ (`claim_id IN` apakšvaicājums) — `top_k` ir budžets politiķa paša filtrēto claims ietvaros, nevis pret visu indeksu. `top_k` uzpūšana kompensācijai vairs nav vajadzīga.

### get_contradictions(opponent_id, confirmed_only=False, min_salience=0.0) → str
**Avots:** `src/tools.py`
Atgriež pretrunas ar vecā/jaunā apgalvojuma detaļām.

### get_context_notes(opponent_id=None, topic=None) → str
**Avots:** `src/tools.py`
Atgriež konteksta piezīmes, filtrējamas pēc politiķa vai tēmas.

### last_log(action=None) → str
**Avots:** `src/tools.py`
Pēdējais audit log ieraksts (vai pēdējais ar norādīto action).

---

## 4. Wiki pārvaldība

### wiki_sync(db_path="data/atmina.db", wiki_dir="wiki") → dict
**Avots:** `src/wiki.py`
Sinhronizē DB datus uz wiki. Automātiski palaiž wiki lint beigās.
```python
from src.wiki import wiki_sync
result = wiki_sync()
# result = {persons: N, topics: N, parties: N, updated_at: "...", lint: {total_issues: N, ...}}
```

### lint_wiki_with_db(wiki_dir="wiki", db_path="data/atmina.db") → dict
**Avots:** `src/wiki_lint.py`
Pārbauda wiki integritāti: orphaned pages, broken links, stale frontmatter, isolated topics.
```python
from src.wiki_lint import lint_wiki_with_db
r = lint_wiki_with_db()
print(r["stats"])  # {total_issues, orphans, broken_links, stale, isolated}
for issue in r["issues"]: print(f"  {issue['type']}: {issue.get('path', issue.get('target'))}")
```

---

## 5. Papildu funkcijas

### mark_documents_reviewed(doc_ids: list[int], db=None) → int
**Avots:** `src/analyze.py`
Atzīmē dokumentus kā caurskatītus (ar vai bez claims). Atgriež atjaunoto skaitu. Automātiski izsaukts no `save_analysis()` gan claim dokumentiem, gan `empty_doc_ids` — tātad parasti nav jāizsauc manuāli.
- **`db`** — neobligāts externally-managed connection; `save_analysis` to izmanto, lai iekļautu reviewed update vienā atomiskā transakcijā kopā ar claims.
```python
from src.analyze import mark_documents_reviewed
mark_documents_reviewed([101, 102, 103])
```

### writeback_insight(politician_name=None, topic=None, insight="", source="analysis") → str
**Avots:** `src/tools.py`
Ieraksta ieskatu wiki lapā (## Writeback sadaļā). Automātiska dedup.
```python
from src.tools import writeback_insight
writeback_insight(politician_name="Evika Siliņa", insight="3x mainījusi pozīciju par Rail Baltica 2 mēnešos", source="daily analysis 2026-04-08")
writeback_insight(topic="Imigrācija", insight="Koalīcijas dalībnieki sašķēlušies — JV un PRO pretējas pozīcijās", source="weekly review")
```
**Kad lietot:** Tikai netriviāliem ieskatiem, ko nevar iegūt ar SQL query — konteksts, modeļi, novērojumi.

### append_ingest_entry(log_path, source_name, source_tier, documents_added, documents_skipped, status, error=None, extra=None)
**Avots:** `src/ingest_log.py`
Pievieno ierakstu ingest žurnālam. Automātiski izsaukts no `ingest_all()` un `fetch_all_twitter/mentions()`.

### read_ingest_log(log_path="wiki/log-ingest.md", last_n=20) → list[str]
**Avots:** `src/ingest_log.py`
Nolasa pēdējos N ingest ierakstus (jaunākie pirmie).
```python
from src.ingest_log import read_ingest_log
for line in read_ingest_log(last_n=10): print(line)
```

### get_coalition_map(db) → dict[str, str]
**Avots:** `src/coalition.py` (2026-04-11)
Atgriež {partijas_nosaukums_vai_īsais_nosaukums: coalition_status} no `parties` tabulas. Atslēgo gan uz pilno nosaukumu, gan uz `short_name` (tāpēc 'Mēs mainām noteikumus' un 'MMN' abi rezolvējas uz to pašu statusu). Vērtības: `coalition` | `opposition` | `not_in_saeima` | `other`.
```python
from src.coalition import get_coalition_map
cmap = get_coalition_map(db)
cmap.get("Jaunā Vienotība")  # → "coalition"
cmap.get("MMN")               # → "not_in_saeima"
```
**Kad lietot:** Kad klasificē daudzas rindas vienā pārliecinājumā (briefs, spriedzes aggregations). Batchā izmanto `get_coalition_map` vienreiz, nevis sauc `party_status` cikla iekšā.

### party_status(party, db=None) → "coalition" | "opposition" | "not_in_saeima" | "other"
**Avots:** `src/coalition.py` (2026-04-11)
Viena politiķa/partijas statusa lookup. Autoritatīvais koalīcijas truth source ir `parties.coalition_status` kolonna, nav hardkodēts saraksts. **Nekad** nelieto `tracked_politicians.relationship_type` koalīcijas klasifikācijai — tas ir legacy per-politician tracking role bez koalīcijas semantikas.
```python
from src.coalition import party_status
party_status("Nacionālā apvienība")  # → "coalition"
party_status(None)                    # → "other"
```

---

## Ātrā atsauce — biežākie workflow

### Dienas analīze vienam politiķim
```python
from src.analyze import get_pending_politicians, get_politician_documents, get_existing_claims, save_analysis
pending = get_pending_politicians(days=1)
# Izvēlies politiķi, tad:
docs = get_politician_documents(pid=42)
existing = get_existing_claims(pid=42)
# Analizē docs, salīdzini ar existing, sagatavo claims sarakstu
save_analysis(pid=42, analysis_date="2026-04-08", sentiment=0.0, topics=[...], quotes=[...], brief="...", confidence=0.6, claims=[...])
```

### Pārbaudi ingest vēsturi
```python
from src.ingest_log import read_ingest_log
print("\n".join(read_ingest_log(last_n=10)))
```

### Pārbaudi wiki veselību
```python
from src.wiki_lint import lint_wiki_with_db
r = lint_wiki_with_db()
print(r["stats"])
```
