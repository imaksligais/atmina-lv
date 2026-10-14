# Video Extractor — Dizaina specifikācija

**Datums**: 2026-04-28
**Izcelsmes konteksts**: 2026-10-03. Saeimas vēlēšanas tuvojas. Pirms-vēlēšanu publiskajā telpā parādās debašu un interviju video (LSM Replay, YouTube — piem. "Kas Notiek Latvijā", LTV intervijas, partiju kanāli). Pašreizējais ingest pipeline atbalsta tikai web rakstus + X/Twitter. Video saturs paliek ārpus politiķu pozīciju kartējuma.
**Saistītie specs**: nav (jauns satura kanāls)
**CHANGELOG atsauce pēc ieviešanas**: `wiki/CHANGELOG.md § Video ingest pipeline`

---

## 1. Mērķis

Pievienot atmina.lv **ceturto satura kanālu** (papildus `web` / `twitter` / `x_mention`): latviešu valodas video debates, intervijas un raidījumi. Operators iedod video URL vai lokālu failu, sistēma to pārvērš par vienu `documents` rindu ar pilnu speaker-labelētu transkriptu, no kura tālāk standarta claim-extraction plūsma izvelk pozīcijas.

Datu modeļa līmenī — ieviešam `documents.platform='video'` kā jaunu pieņemamu vērtību. Bez schema migrācijas: `claim_type` paliek `'position'`, `source_url` per-claim iegūst timestamp anchor (`?t=N` YouTube, `#t=N` citur), kas saglabā `store_claim()` idempotenci uz `(opponent_id, source_url, topic)` tuple un atļauj UI deep-link uz precīzu video brīdi.

Komponenta līmenī — split: **CLI scripts** (`src/video_ingest/`) dara mehāniku (download, ASR, diarization, DB write), **`@video-extractor` aģents** dara LLM-darbu (claim ekstrakcija no labelēta transkripta).

Kvalitātes mērķis: stundas garš debašu video → 6-15 verificējamas pozīcijas ar timestamp-anchored avotiem, kas plūst caur esošo dashboard, profila timeline un dienas pārskatu bez papildu UI darba.

---

## 2. Scope

### MVP (šī specs)

- `src/video_ingest/` Python pakotne ar `fetch` / `finalize` / `extract-claims` / `status` / `archive` CLI komandām
- `faster-whisper` (large-v3 INT8) lokāla ASR + `pyannote.audio` 3.1 lokāla diarization
- 2-pass speaker mapping workflow ar heuristisku auto-suggestion (`suggested_speakers.json`)
- `.claude/agents/video-extractor.md` aģents ar per-speaker pass disciplīnu
- `wiki/operations/agenti/video-extractor.md` rokasgrāmata
- `wiki/operations/video-setup.md` vienreizējais setup (ffmpeg, HF token, pyannote licences)
- `tests/test_video_ingest_*.py` ar mock'otiem ASR/diarize wrapperiem
- CLAUDE.md + CHANGELOG atjauninājumi

### Ārpus scope (vēlākiem darba pakām)

- Auto-discovery (RSS no LSM Replay, YouTube channel monitoring) — manuāla ingest plūsma sākumā
- Daily routine integrācija (`src/routine.py` solis) — manuāla palaišana sākumā
- Video thumbnail ekstrakcija (ffmpeg snapshot) — atstājam graphics-designer agentam vēlāk
- OCR no name-plate banner'iem ekrānā kā automātisks speaker mapper — heuristics + manuāls confirm ir pietiekams MVP'am
- Dashboard "Video" filtrs vai sub-tab — UI atspoguļojums atsevišķā darba pakā
- Video arhīvs ar visu nemodificētu `audio.wav` ilgtermiņā — dzēšam pēc `finalize`, transkripts ir kanonisks

### Apzināti paturam vienkārši

- Vienam video = viens `documents` row (ne per-segment)
- `claim_type` paliek `'position'` (ne jauns `'video_position'`)
- Bez DB schema migrācijas (`platform` jau ir TEXT)
- Per-speaker passes claim ekstrakcijā (atjauno @claim-extractor 12-doc disciplīnas pareizi long-context'ā)

---

## 3. Datu modelis

### Bez izmaiņām

- `documents` schema: bez ALTER. `platform` ir `TEXT` un pieņem `'video'`. Esošās kolonnas mēs lietojam:
  - `content` = labelēts transkripts (`[mm:ss] @handle: text`)
  - `content_hash` = `sha256(content)` (idempotence)
  - `simhash` = standarta simhash (near-dupe detection)
  - `platform` = `'video'`
  - `source_id` = `NULL` (nav RSS avota)
  - `source_domain` = `'youtube.com'` / `'replay.lsm.lv'` / utt.
  - `source_url` = canonical video URL bez timestamp
  - `archive_path` = `'videos/<slug>/'` (relatīvs)
  - `scraped_at` = `now_lv()`
  - `word_count` = transkripta vārdu skaits
  - `language` = `'lv'`
  - `published_at` = video upload/air date no metadata
  - `is_paywall` = `0`
  - `summary` = pirmais ne-`@host` runātāja segment (līdz 200 vārdiem)
  - `title` = video virsraksts no yt-dlp / operators
  - `is_auto_caption` = `0` (mēs ģenerējam transkriptu, ne YouTube auto-CC)
  - `reviewed_at` = `NULL` līdz @video-extractor pabeidz
  - `reply_count` / `retweet_count` / `favorite_count` = `NULL` (nav video metrika)

- `claims` schema: bez ALTER. `claim_type='position'`, `speaker_id=NULL`. Atšķirība no rakstu pozīcijām — `source_url` ietver timestamp:
  - YouTube: `https://www.youtube.com/watch?v=ABC&t=243s`
  - LSM/Delfi/cits: `https://replay.lsm.lv/episode/X#t=243`
  - Lokāls fails (rare): `file:///abs/path.mp4#t=243` (nav publiski sasniedzams, bet unique DB)

- `document_politicians` junction: katrs unikāls `pid` no `speakers.json` ar `role='subject'`. (Nav `mention_target` — visi šeit zināmie speakers tiešām runā.)

### Ko validējam

- `documents.platform IN ('web', 'twitter', 'x_mention', 'facebook', 'video', 'irrelevant', 'stub')` — pievienojam `'video'` ja eksistē whitelist `src/db.py` (pārbaudīsim plānā)
- `speakers.json` validācija (Phase 3): visi `pid` vērtības eksistē `tracked_politicians` un nav `relationship_type='inactive'`
- ASR + diarization output JSON shape pret Pydantic modeļiem (jaunie `src/video_ingest/models.py`)

---

## 4. Arhitektūra

```
┌──────────────────────────────────────────────────────────────────┐
│  FĀZE 1: fetch (CLI script — bez LLM)                            │
│  python -m src.video_ingest fetch <url|path>                     │
│                                                                  │
│   input ─┬─→ yt-dlp (URL)                                        │
│          └─→ direct copy (lokāls fails)                          │
│         ↓                                                        │
│      audio.wav (16 kHz mono)                                     │
│         ↓                                                        │
│      faster-whisper large-v3 INT8 (VAD ieslēgts)                 │
│         ↓                                                        │
│      transcript.json (segmenti ar word-level ts)                 │
│         ↓                                                        │
│      pyannote.audio 3.1                                          │
│         ↓                                                        │
│      diarized.json + samples/speaker-{A..N}.mp3                  │
│         ↓                                                        │
│      heuristics.py: konteksta zīmes ("Paldies, Andrij...")       │
│         ↓                                                        │
│      suggested_speakers.json (auto-piedāvāts)                    │
└──────────────────────────────────────────────────────────────────┘
                          ↓ (operators apstiprina, koriģē JSON)
┌──────────────────────────────────────────────────────────────────┐
│  FĀZE 2: cilvēka apstiprinājums (manuāla failu rediģēšana)       │
│  Operators kopē suggested_speakers.json → speakers.json,         │
│  koriģē, ja heurists nav drošs.                                  │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  FĀZE 3: finalize (CLI script — bez LLM)                         │
│  python -m src.video_ingest finalize <slug>                      │
│                                                                  │
│  Validē speakers.json (pid eksistē, ne inactive)                 │
│  Pielīmē @handle labels transkriptam → labelled_transcript.md    │
│  Idempotence: SELECT id FROM documents WHERE content_hash=?      │
│  INSERT documents (platform='video', ...) jaunu vai existing     │
│  INSERT document_politicians per unikāls pid (role='subject')    │
│  Dzēš audio.wav (saglabā JSON + samples)                         │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  FĀZE 4: claim ekstrakcija (@video-extractor agent — LLM)        │
│  python -m src.video_ingest extract-claims <slug>                │
│  → invokē Agent({subagent_type: "video-extractor", ...})         │
│                                                                  │
│  Lasa document_id ar platform='video'                            │
│  Per-speaker pass loop (1 politiķis/iter, max 12 claims)         │
│  save_analysis ar timestamp-anchored source_urls                 │
│  Standarta contradiction check + topic normalization             │
│  Marks reviewed_at = now_lv() pabeidzot                          │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  FĀZE 5: pārpublicēšana (existing flow — bez izmaiņām)           │
│  Claims redzami dashboard, profila timeline, dienas brief        │
│  visi caur platform-agnostic claim_type='position' plūsmu        │
└──────────────────────────────────────────────────────────────────┘
```

### Stāvokļa mašīna

`status <slug>` lasa failu eksistenci un atgriež:

| Stāvoklis | Kas eksistē | Nākamais solis |
|-----------|-------------|----------------|
| `FETCHING` | `audio.wav` partial | gaidi vai `--resume` |
| `TRANSCRIBED` | `transcript.json` | (auto-pāreja) |
| `DIARIZED` | `diarized.json`, `samples/`, `suggested_speakers.json` | operators rediģē → `speakers.json` |
| `MAPPED` | `speakers.json` | `finalize` |
| `IN_DB` | DB row eksistē, `reviewed_at IS NULL` | `extract-claims` |
| `CLAIMS_EXTRACTED` | DB row, `reviewed_at IS NOT NULL` | (gatavs) |
| `ARCHIVED` | tikai JSON+samples, audio.wav dzēsts | (terminal) |

---

## 5. Failu sistēma per video

```
.scratch/videos/<slug>/
├─ metadata.json          # {url, title, uploader, published_at, language, duration, source_domain}
├─ audio.wav              # 16 kHz mono, dzēsts pēc finalize
├─ transcript.json        # Whisper output: {segments: [{start, end, text, words: [...]}]}
├─ diarized.json          # pyannote output: [{start, end, speaker: "A"}]
├─ aligned.json           # transcript ⊕ diarized: [{start, end, speaker, text}]
├─ context_cues.json      # heurist. zīmes per Speaker: vārda uzrunas, pirmā frāze, formālas frāzes
├─ samples/
│   ├─ speaker-A.mp3      # 10s reprezentatīvs gabals (vidū segmenta)
│   ├─ speaker-B.mp3
│   └─ speaker-N.mp3
├─ suggested_speakers.json   # auto-piedāvāts mapings ar confidence
├─ speakers.json             # operatora apstiprināts mapings
└─ labelled_transcript.md    # gala transkripts ar @handles (= documents.content)
```

`<slug>` formāts: `YYYY-MM-DD-<source>-<topic>` (piem., `2026-04-15-knl-velesanas`). Auto-ģenerēts no `published_at` + slugifietā `metadata.title` (max 40 chars). Override ar `--slug NAME`.

`.scratch/` ir gitignored — failos nav sensitīvas datus pēc `finalize` (audio dzēsts), bet konvencija ir lokāls workspace.

---

## 6. CLI komandas

```bash
# Phase 1
python -m src.video_ingest fetch <url|path> [--slug NAME] [--language lv]
                                            [--num-speakers N] [--resume]

# Phase 2 (manuāls failu edits, nav komandas)

# Phase 3
python -m src.video_ingest finalize <slug>

# Phase 4
python -m src.video_ingest extract-claims <slug>
# Iekšā: izveido Agent({subagent_type: "video-extractor", prompt: ...})

# Auxiliary
python -m src.video_ingest status <slug>
python -m src.video_ingest archive <slug>     # kompresē JSON, dzēš samples ja gribi
```

### Komandu īpašības

- **`fetch`** ir lēnākā (~30-60 min uz GTX 1060 par stundas video). Atbalsta `Ctrl+C` un `--resume` no pēdējās pabeigtās fāzes (audio.wav, transcript.json, diarized.json — checkpoints).
- **`finalize`** ir ātra (<1s). Drošs palaist atkārtoti — content_hash idempotence atgriež eksistējošu document_id.
- **`extract-claims`** invokē @video-extractor caur Bash; rezultāts ir DB writes + reviewed_at marking. Ja palaiž TU (Claude), izmanto Agent rīku ar `subagent_type="video-extractor"`.

### `python` izsaukumi no Claude

Claude var palaist visu pipeline savā Bash sesijā:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch "https://www.youtube.com/watch?v=..."
# → gaidi 30-60 min vai run_in_background=true
# Claude lasa transkriptu + context_cues, piedāvā speakers.json saturu
# Operators apstiprina .scratch/videos/<slug>/speakers.json
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize <slug>
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest extract-claims <slug>
```

---

## 7. Speaker mapping ar heuristikām

Phase 1 kā pēdējais solis palaiž `heuristics.py`, kas analizē transcript + diarized + tracked_politicians, lai automātiski piedāvātu kartējumus:

### Heuristikas tipi

1. **Vārda uzruna citu runātāju** — regex `(Paldies|Sveiki|Lūdzu) (Andrij|Evik|...)` matched pret `tracked_politicians.name_forms`. Speaker, pret ko vēršas, ar augstu confidence ir uzrunātais.
2. **Pašprezentācija** — `(Mans vārds ir|Es esmu) <Vārds Uzvārds>` pirmajos 30 segmenta sekundēs.
3. **Formāla frāze** — `(kā <amats>|<amats> <Vārds>)` (piem., "kā veselības ministrs", "ministrs Abu Meri"). Match'ē pret `tracked_politicians.role`.
4. **Pirmais runātājs ar formālu sveicienu** — bieži vadītājs (`@host`).
5. **Saeimas amats** — "Saeimas deputāts", "Frakcijas vadītājs" kā konteksts.

### Output: `suggested_speakers.json`

```json
{
  "A": {
    "pid": 3,
    "handle": "SlesersAinars",
    "confidence": 0.92,
    "evidence": "00:23 vadītājs uzrunā 'Andri Šleser'; 02:45 'kā partijas LPV līderis'"
  },
  "B": {
    "pid": null,
    "handle": "host",
    "confidence": 0.65,
    "evidence": "Pirmais runātājs ar 'Sveicināti, šovakar studijā...'"
  },
  "C": {
    "pid": null,
    "handle": "unknown_C",
    "confidence": 0.0,
    "evidence": "Nav konteksta zīmju; vajag manuālo verifikāciju"
  }
}
```

Operators kopē šo failu kā `speakers.json` un koriģē, kur confidence < 0.7. Ja visiem speakers confidence ≥ 0.85, operators (vai Claude) var pieņemt automātiski.

### Claude's loma Phase 1.5 (opcionāla)

Heuristikas dod baseline `suggested_speakers.json`. **Ja heurists atstāj kādu speaker ar `confidence < 0.7`**, operators (vai Claude pēc lūguma) var lasīt `transcript.json` un `context_cues.json` un piedāvāt rafinētu mapingu, kas pārsniedz regex heuristikas (piem., diskusijas plūsma — "X piekrita Y, kas teica Z" implicite norāda Y identitāti).

Tas **nav atsevišķa skripta vai aģenta darbība** — Claude vienkārši lasa failus un piedāvā JSON labojumus Bash/Telegram atbildē. Operators saglabā gala `speakers.json` manuāli. Ja heuristikas ir pietiekamas (visiem `confidence ≥ 0.85`), Phase 1.5 tiek izlaista pilnībā.

Ja izrādās, ka heuristikas atstāj daudzus `confidence < 0.7` lielākajā daļā video, vēlākajā darba pakā varam pievienot `@video-speaker-mapper` kā specializētu mini-aģentu (out of scope šobrīd).

---

## 8. Claim ekstrakcija — `@video-extractor` aģents

### Process

1. Lasa document ar `slug` (vai `document_id` argumentu): `SELECT * FROM documents WHERE platform='video' AND ...`
2. Parsē `[mm:ss] @handle: text` rindas; izveido segments per speaker
3. Loads `tracked_politicians` un meklē matching speakers (`WHERE name LIKE ... OR x_handle = ...`)
4. **Per-speaker pass loop** (1 politiķis vienā pass'ā):
   - Filtrē segments uz vienu @handle
   - Pārbauda max 12 distinktas pozīcijas (drift mitigation)
   - Ekstrakcija ar specializētiem self-check noteikumiem (skat. zem)
   - `save_analysis()` ar timestamp-anchored source_urls
5. Pēc visiem speakers: marks `documents.reviewed_at = now_lv()`
6. Standarta contradiction check (caur `save_analysis`)

### Specializēti self-check noteikumi (atšķirībā no @claim-extractor)

- **Filleri un nepabeigtas frāzes**: "Eee, nu, jā, es domāju..." → ja sentence neaizpildās ar konkrētu pozīciju, mark empty
- **Multi-speaker konteksts**: "Es piekrītu" bez konkrētas pozīcijas → atskatās uz iepriekšējo speaker; ja iepriekšējais ir cits politiķis ar konkrētu pozīciju, dublēsim viņa stance ar reasoning "Pārpostulēts no @X"; ja nezināms konteksts → empty
- **Pārtrauktās frāzes**: "Mēs uzskatām, ka — (cits speaker iejaucas) — vārdu sakot..." → empty
- **Indirekti citējumi**: "Kā Šlesers teica, mums vajag..." → speaker-citators **pats nepiekrīt**, ja nav skaidri norādīts; mark empty vai zema confidence
- **ASR kļūdu apzināšana**: ja redzi "limens" → atjauno "līmenis" quote'ā un atzīmē reasoning ("ASR error labots: limens → līmenis")
- **Diakritika**: Whisper LV labi tur ā/ē/ī/ū/ņ/ļ/ķ/ģ/š/ž/č; ja **redzi 50%+ tekstu bez diakritikas** — STOP & report (transkripts varētu būt nepilnīgs, drift risk)

### Limits

- Max **12 distinktas pozīcijas vienam politiķim** vienā pass'ā (atbilst @claim-extractor disciplīnai)
- Ja vienam speakerim ir vairāk par 12 — STOP & report ar `Pārsniegts 12 pozīciju limits @<handle>. Atlikušie segmenti N..M jāanalizē atsevišķā sesijā.`
- `confidence ≥ 0.6` ir parastais slieksnis; video pozīcijas ar runas dabu var būt zemākas — atļaujam 0.5 ar pamatojumu reasoning'ā

### Source URL formāts

```python
# YouTube
source_url = f"{base_url}?t={start_seconds}s"
# Cits portāls
source_url = f"{base_url}#t={start_seconds}"
# Lokāls fails
source_url = f"file:///{abs_path}#t={start_seconds}"
```

`start_seconds` ir integer no segments[].start (pirmā punkta integerā). Tas dod unique URL un store_claim idempotenci uz `(opponent_id, source_url, topic)`.

---

## 9. Atkarības

### Jauni Python paketes (`requirements.txt`)

```
yt-dlp==2025.10.7
faster-whisper==1.1.1
pyannote.audio==3.3.2
pydub==0.25.1
torch==2.5.1
torchaudio==2.5.1
```

### Sistēmas atkarības

- **ffmpeg** (yt-dlp + pydub atkarība). Win: `winget install ffmpeg` vai `choco install ffmpeg`. Skripts pārbauda `subprocess.run(['ffmpeg', '-version'])` pirms fetch.
- **CUDA 11.8+** ja gribam GPU (GTX 1060 6GB derīgs). PyTorch instalē CUDA wheel automātiski; pārbaudām `torch.cuda.is_available()`.

### Modeļi (cache)

- faster-whisper large-v3 INT8: ~1.6 GB → `~/.cache/whisper/`
- pyannote/speaker-diarization-3.1: ~250 MB → `~/.cache/huggingface/`

Pirmā palaišana lejupielādē; pēc tam ātri.

### HuggingFace token (vienreizējs setup)

pyannote 3.1 prasa:
1. Akceptēt licences uz https://huggingface.co/pyannote/speaker-diarization-3.1 un https://huggingface.co/pyannote/segmentation-3.0
2. Ģenerēt token https://huggingface.co/settings/tokens (read access)
3. Eksportēt: `export HUGGINGFACE_TOKEN=hf_...` vai pievienot `data/credentials.json`

Skripts pārbauda env vai `data/credentials.json` (atkarīgi no `src/credentials.py` esošā patternu) pirms diarization un izvada konkrētas instrukcijas, ja trūkst.

---

## 10. Komponenti

### Python pakotne

```
src/video_ingest/
├─ __init__.py
├─ __main__.py            # CLI entrypoint
├─ cli.py                 # argparse: fetch/finalize/extract-claims/status/archive
├─ fetch.py               # yt-dlp wrapper, slug ģenerēšana, metadata.json
├─ asr.py                 # faster-whisper wrapper, VAD, transcript.json
├─ diarize.py             # pyannote 3.1 wrapper, diarized.json + samples
├─ align.py               # transcript ⊕ diarized → aligned.json (matemātika)
├─ heuristics.py          # context_cues.json + suggested_speakers.json
├─ finalize.py            # speakers.json validation, labelled_transcript.md, DB writes
├─ db.py                  # video-specific SQL helpers
├─ state.py               # state machine (status command), idempotence
├─ models.py              # Pydantic models per JSON schema
└─ config.py              # paths, defaults, HF token loader
```

### @-aģenta faili

```
.claude/agents/video-extractor.md          # canonical execution prompt
wiki/operations/agenti/video-extractor.md  # human-readable apraksts
wiki/operations/video-setup.md             # vienreizējais setup
```

### Datu modeļa pielāgojumi

- `src/db.py` — ja eksistē `VALID_PLATFORMS` validācija, pievienot `'video'`
- CLAUDE.md § Pipeline Invariants — pievienot rindiņu par `platform='video'` un timestamp source_urls
- `wiki/CHANGELOG.md` — entry datēts ar implementācijas merge dienu, virsraksts "Video ingest pipeline (platform='video', timestamp source_url anchor)"

### Dokumentācija

- `wiki/operations/operacijas.md` — jauna sadaļa "Video ingest" ar 4-fāzu rokasgrāmatu
- `wiki/operations/video-setup.md` — vienreizējais setup
- `wiki/operations/agenti/video-extractor.md` — kā izsaukt @video-extractor

---

## 11. Kļūdu apstrāde

| Fāze | Error | Atbilde |
|------|-------|---------|
| 1 | yt-dlp fail (geoblock, bot detect, unsupported) | Exit 2, mesage "yt-dlp neizdevās. Pamēģini lokālu failu (`fetch /path/to/video.mp4`)." |
| 1 | ffmpeg trūkst | Exit 4, instrukcija (`winget install ffmpeg`) |
| 1 | Whisper OOM | Auto-fallback uz `medium` model + brīdinājums logā |
| 1 | pyannote bez HF token | Exit 3, instrukcija 3 soļos |
| 1 | pyannote viens runātājs (false neg) | Brīdinājums + `--num-speakers N` override flag |
| 1 | Whisper noklusē halucinē "paldies par skatīšanos" | VAD filter ieslēgts pēc default; aizsardzība pret klusām vietām |
| 2 | speakers.json bojāts JSON | Phase 3 validē, izvada konkrētu rindu un kolonnu |
| 2 | speakers.json piem. uz pid, kas neeksistē | Phase 3 validē pret `tracked_politicians.id`, kļūda |
| 2 | speakers.json piem. uz inactive politiķi | Phase 3 validē pret `relationship_type != 'inactive'`, kļūda |
| 3 | content_hash collision | Atgriež eksistējošu `document_id`, izvada `[exists]`, turpina pie Phase 4 |
| 3 | INSERT fails (disk full, locked) | Rollback, kļūda; nekādu daļēju ierakstu |
| 4 | save_analysis daļējs (`partial`) | Standarta @claim-extractor uzvedība — log un turpini |
| 4 | NEEDS_REVIEW claims | Standarta @quality-reviewer uztver |
| 4 | Politiķim > 12 pozīcijas | STOP & report ar speaker handle un atlikušo segmentu range (`segments N..M`); operators palaiž atkārtotu `extract-claims` pēc tam, kad pirmā partija ir saglabāta DB. Šajā MVP nav atsevišķa `--speaker` flag (atstājam Phase 2 paplašinājumam, ja izrādās nepieciešams). |

---

## 12. Testēšana

### Unit testi

```
tests/test_video_ingest_fetch.py      # mock yt-dlp, validē slug ģenerēšanu, metadata
tests/test_video_ingest_asr.py        # mock faster-whisper, validē transcript.json shape
tests/test_video_ingest_diarize.py    # mock pyannote, validē diarized.json + samples
tests/test_video_ingest_align.py      # īsts unittest (transcript ⊕ diarized matemātika)
tests/test_video_ingest_heuristics.py # īstais — text-only, konteksta zīmju regex
tests/test_video_ingest_finalize.py   # tmp DB, validē idempotence + INSERTs
tests/test_video_ingest_state.py      # state machine no failu eksistences
tests/fixtures/video/                 # golden datu samples (5-min mock transkripts)
```

### Integration test (ne CI default, manuāls smoke)

- 1 īss publisks video (~3-5 min) checked-in kā fixture vai tests pie operatora reālas instalācijas
- `pytest -m integration` palaiž pilnu pipeline pret to (lēni)

### Acceptance criteria (manuāls smoke pirms ship)

1. **YouTube fetch**: ievadu publisku KNL video URL, sagaidu pilnu pipeline līdz `IN_DB` 60 min laikā
2. **LSM Replay fetch**: ievadu replay.lsm.lv intervija URL, yt-dlp atbalsta vai izvada saprātīgu kļūdu
3. **Lokāls fails**: `fetch /path/to/local.mp4` strādā bez yt-dlp
4. **Speaker auto-suggest**: heurists piedāvā ≥ 50% confidence pareizu mapingu KNL stila video (vadītājs + 4 viesi)
5. **Idempotence**: divreizīgs `finalize <slug>` rezultējas vienā document row, ne duplikātos
6. **Claim ekstrakcija**: 60-min debašu video → ≥ 8 derīgas pozīcijas no zināmajiem speakers
7. **Diakritika**: visi `quote` un `stance` lauki iztur `validate_lv_diacritics`
8. **Contradiction check**: ja video politiķis maina nostāju pret iepriekšējo media stance, tas tiek atklāts
9. **Reviewed_at**: pēc `extract-claims` `documents.reviewed_at IS NOT NULL`
10. **Cleanup**: pēc `finalize` `audio.wav` ir dzēsts; pēc `archive` arī samples kompresēti

---

## 13. Riski un mitigation

| Risks | Iespējamība | Mitigation |
|-------|-------------|------------|
| Whisper LV kvalitāte zem cerībām | Vidēja | Sākam ar large-v3; ja kvalitāte nepietiekama, eksperimentē ar Latvian-specific fine-tuned modeļiem (atstājam paplašinājumam) |
| pyannote misnumeruje speakers (4 reālie → 3 vai 5 detected) | Augsta | `--num-speakers` override flag; suggested_speakers.json operatoram skaidri redzams |
| Garais konteksts noved pie drift extracting daudz claims | Vidēja | Per-speaker pass arhitektūra; 12-pos limit per speaker |
| GTX 1060 6GB OOM ar large-v3 | Zema | INT8 quantization (~2 GB), secīga modeļu ielāde |
| ffmpeg vai HF token trūkst | Augsta (pirmā lietotāja iestatīšana) | Skaidri error messages + `wiki/operations/video-setup.md` |
| LSM Replay yt-dlp atbalsts mainās | Vidēja | Lokāla faila fallback vienmēr darbojas |
| Privātā video (paroles aizsardzība) | Zema | Lokāls fails fallback |
| Operators aizmirst aizpildīt speakers.json | Zema | `status` komandā skaidri rāda "WAITING FOR speakers.json" |
| Disk fill no audio.wav krājuma | Vidēja | `finalize` automātiski dzēš; `archive` darbojas pēc tam |

---

## 14. Tālākie soļi pēc šī specs apstiprināšanas

1. Spec self-review (placeholder/contradiction/scope/ambiguity)
2. Lietotāja apstiprinājums (šis dokuments)
3. Implementācijas plāns caur `superpowers:writing-plans` skill — sadalīts pa darba pakām (fetch script, ASR/diarization, heuristikas, finalize/DB, agent, tests, docs)
4. Implementācija pa darba pakām ar TDD pieeju
5. Pilna integrācijas testa palaišana ar reālu KNL vai LTV video
6. Dokumentācijas pabeigšana (CLAUDE.md, CHANGELOG, wiki)
7. Merge

---

## 15. Apzināti jautājumi/atstātais

- **Cik bieži palaidīsim?** Operators teica "tu iedosi video" — manuāla plūsma. Neapsveram daily routine integrāciju MVP'am.
- **Vai vajadzēs Claude SDK izsaukumu @video-extractor invocēšanai?** Plānā precizēsim, vai Bash invokē Agent rīku vai Python `Anthropic` SDK; abi der.
- **Per-claim review gate?** Šobrīd standarta @claim-extractor flow + @quality-reviewer; nav atsevišķa human-in-loop video pozīcijām (kā graphics-designer ar `approved=0`). Ja izrādās, ka kļūdas ir biežas, varam pievienot `claims.video_review_status` kolonnu vēlāk.
- **Multi-language video?** Vēl-vēl reti latviešu kontekstā; ja ir krievu/angļu segmenti, Whisper transkribē tāpat kā lv (multilingual modelis). Atstājam.
