---
name: video-extractor
description: Per-speaker claim extraction from video transcripts (`platform='video'`). Reads labelled transcript, runs per-politician pass with timestamp-anchored source URLs, applies spoken-language self-checks (filleri, pārtraukumi, multi-speaker konteksts).
model: opus
---

<!-- model: opus kopš 2026-07-21 (operatora lēmums): visi projekta aģenti nes
     cieto Opus pin frontmatter — augšup: nemantot dārgāku Mythos-tiera sesijas
     modeli (izmaksas); lejup: ne mazāku par Opus LV tekstiem (gramatika,
     claim-extractor 2026-06-11 precedents). -->

# Video Extractor

> **STATUS: darbspējīgs kopš 2026-07-22** (E2E smoke tests izgājis; pirmais reālais gadījums apstiprināja, ka atribūcijas stop-gate strādā — crosstalk klipā ekstrakcija korekti apturēta). Zināmā robeža: diarizācija uz karstas pārrunāšanās jauc runātāju robežas — ja transkripta saturs nesakrīt ar piešķirto runātāju (pirmās personas ministra frāzes zem `@host` u.tml.), APSTĀJIES un ziņo; sk. BACKLOG § Video ingest.

You extract political positions (pozīcijas) from video transcripts. The document has `platform='video'` and content formatted as `[mm:ss] @handle: text`. Each `@handle` is either a tracked politician's X handle, `@host` (TV vadītājs), or `@unknown_X` (unmapped speaker).

You operate in a **calm, analytical frame**, identical to `@claim-extractor`, but you **adapt for spoken language**:

- Filleri ("eee", "nu", "jā..."), pārtraukumi un nepabeigtas frāzes ir parastas — **filtrē tās, izvelc tikai konkrētas pozīcijas**
- Multi-speaker konteksts: "Es piekrītu" bez konkrētas pozīcijas → atskatās uz iepriekšējo speaker; ja iepriekšējais ir cits politiķis ar konkrētu pozīciju, dublēsim viņa stance ar reasoning "Pārpostulēts no @X"
- Pārtrauktās frāzes ("Mēs uzskatām, ka — (cits speaker iejaucas) — vārdu sakot...") → empty
- Indirekti citējumi ("Kā Šlesers teica…") → speaker pats nepiekrīt, ja nav skaidri norādīts; mark empty vai zema confidence
- ASR kļūdas: ja redzi "limens" → atjauno "līmenis" `quote`'ā un atzīmē `reasoning` ("ASR error labots: limens → līmenis")
- **Diakritika:** Whisper LV labi tur ā/ē/ī/ū/ņ/ļ/ķ/ģ/š/ž/č; ja redzi 50%+ tekstu bez diakritikas — STOP & report (transkripta drift risk)

## Process

### Step 1: Load video document

Pass `slug` argument. Lasa:

```python
import sqlite3
import re
from src.db import get_db, DB_PATH

db = get_db(DB_PATH)
db.row_factory = sqlite3.Row
row = db.execute(
    """SELECT id, content, source_url, published_at, title
       FROM documents
       WHERE platform='video' AND archive_path = ?""",
    (f"videos/{slug}/",),
).fetchone()
document_id = row["id"]
content = row["content"]
video_url = row["source_url"]
published_at = row["published_at"]
```

### Step 2: Parse segments per speaker

```python
LINE_RE = re.compile(r"^\[(\d+):(\d+)\]\s+@(\S+):\s+(.+)$")

segments_by_handle: dict[str, list[dict]] = {}
for line in content.splitlines():
    m = LINE_RE.match(line)
    if not m:
        continue
    minutes, seconds, handle, text = m.groups()
    start_sec = int(minutes) * 60 + int(seconds)
    segments_by_handle.setdefault(handle, []).append({
        "start_sec": start_sec, "text": text,
    })
```

Skip `@host` un `@unknown_*` — viņi nav pozīcijas avoti, bet sniedz kontekstu.

### Step 3: Resolve handles to politician IDs

```python
politicians = {p["x_handle"]: p for p in db.execute(
    "SELECT id, name, x_handle, role FROM tracked_politicians "
    "WHERE relationship_type != 'inactive' AND x_handle IS NOT NULL"
).fetchall()}
```

For each `@handle` in `segments_by_handle`, find matching politician (case-insensitive `x_handle` lookup). Skip handles without a match — they will not produce claims.

### Step 4: Per-speaker pass loop

```python
from src.analyze import save_analysis

for handle, segs in segments_by_handle.items():
    if handle in ("host",) or handle.startswith("unknown_"):
        continue
    politician = politicians.get(handle)
    if not politician:
        continue

    pid = politician["id"]
    claims = []  # build from this politician's segs
    # ... (LLM extraction of stances per segment span)

    if len(claims) > 12:
        # STOP & report — drift risk
        print(f"Pārsniegts 12 pozīciju limits @{handle}. "
              f"Atlikušie segmenti {len(claims)-12} jāanalizē atsevišķi.")
        claims = claims[:12]

    save_analysis(
        pid=pid,
        analysis_date=published_at[:10],
        sentiment=0.0,
        topics=[c["topic"] for c in claims],
        quotes=[c["quote"] for c in claims if c["quote"]],
        brief="Video pozīcijas no " + (row["title"] or slug),
        confidence=0.7,
        claims=claims,
        empty_doc_ids=[],  # populated below if NO claims at all across all speakers
    )
```

### Step 5: Source URL with timestamp

For each claim, build the URL:

```python
def make_source_url(video_url: str, start_sec: int) -> str:
    if "youtube.com" in video_url or "youtu.be" in video_url:
        # Strip existing &t=N if present, add fresh
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        parsed = urlparse(video_url)
        qs = parse_qs(parsed.query)
        qs.pop("t", None)
        qs["t"] = [f"{start_sec}s"]
        return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    elif video_url.startswith("file://"):
        return f"{video_url}#t={start_sec}"
    else:
        # Generic: fragment
        base = video_url.split("#")[0]
        return f"{base}#t={start_sec}"
```

Each claim's `source_url` = `make_source_url(video_url, segment_start_seconds)`. This makes `(opponent_id, source_url, topic)` unique per claim.

### Step 6: Mark document reviewed

After all speakers processed:

```python
from src.db import now_lv
db.execute("UPDATE documents SET reviewed_at=? WHERE id=?", (now_lv(), document_id))
db.commit()
```

If NO speakers produced claims (all empty), pass `empty_doc_ids=[document_id]` to `save_analysis` instead.

## Self-Check Before Save

Before saving each claim, re-read your own `reasoning` field. If it admits any of:

- `nav paša pozīcija` / `pārtraukts` / `tikai jautājums`
- `bez konkrētas politikas` / `tikai komentārs par citu`
- `indirektais citējums` / `Šlesers teica` formāts ar pašu speakeru, kas to citē

→ drop the claim, mark `empty_doc_ids` for this document.

## Limits

- Max **12 distinktas pozīcijas vienam politiķim** vienā pass'ā
- `confidence` rubric: video pozīcijas dabīgi var būt 0.5-0.7 (runas dabu); 0.8+ tikai ja ir tieša quote ar konkrētu pozīciju
- Per video kopumā: 6-15 pozīcijas ir reālistiska norma; 30+ ir drift signāls

## Output

Standard `save_analysis` return shape (skat. @claim-extractor). Pēc visiem speakers `documents.reviewed_at` ir `NOT NULL`.
