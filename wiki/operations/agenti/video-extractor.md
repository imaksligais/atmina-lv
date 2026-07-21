# @video-extractor

> Kanoniskais prompts (izpildei): [.claude/agents/video-extractor.md](../../../.claude/agents/video-extractor.md) — šī lapa ir īss apraksts cilvēkiem.

Latviešu video debašu un interviju pozīciju ekstrakcijas aģents.

## Kad lietot

Pēc `python -m src.video_ingest finalize <slug>` — kad video transkripts ir DB ar `platform='video'` un `reviewed_at IS NULL`. Aģents izvelk politiķu pozīcijas per-speaker passes.

## Kā izsaukt

```python
Agent(
    description="extract video claims",
    subagent_type="video-extractor",
    prompt=f"Extract claims for slug={slug}",
)
```

Vai no Bash:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest extract-claims <slug>
```

(Bash variants printē instrukciju, kā izsaukt aģentu Claude sesijā — manuāli kopējams.)

## Output

- `claims` rindas ar `claim_type='position'`, `source_url` ar timestamp anchor (`?t=N` YouTube, `#t=N` citur)
- `documents.reviewed_at` atjauno uz `now_lv()`

## Atšķirības no @claim-extractor

| Aspekts | @claim-extractor | @video-extractor |
|---------|------------------|------------------|
| Ievade | Raksts vai tweet | Labelēts video transkripts |
| Pass loop | Per-politiķis-per-doc | Per-speaker-per-video |
| Source_url | Doc URL | Doc URL + `?t=N` vai `#t=N` |
| 12-limit | 12 doc/sesija | 12 pozīcijas/speaker |
| Self-check | Raksta saturs | Filleri, pārtraukumi, multi-speaker konteksts |

## Ierobežojumi

- Skip `@host` un `@unknown_*` — tie nav pozīciju avoti
- ASR kļūdu apzināšanās — labot quote'ā ar reasoning anotāciju
- Pārtrauktas frāzes (cits speaker iejaucas) → empty

Skat. arī `wiki/operations/operacijas.md § Video ingest` un `wiki/operations/video-setup.md`.
