# Aģenti — Indekss

_Atjaunots: 2026-05-16_

Specializēti Claude Code subagenti atmina platformai. Katrs aģents pilda vienu šauri definētu lomu dienas, nedēļas vai notikumu rutīnās.

**Kā aktivizēt:** rakstā `@agent-name` (piem., `@claim-extractor`) vai izsauc caur Task tool ar `subagent_type="claim-extractor"`.

**Pilnie prompti:** `.claude/agents/<name>.md` (versija kontrolēti — canonical execution path; visi 11 aģentu prompts ir repo). Šeit — īsi cilvēkiem lasāmi apraksti.

## Saraksts

| Aģents | Loma | Kad izmanto |
|---|---|---|
| [@claim-extractor](claim-extractor.md) | Pozīciju ekstrakcija no dokumentiem | Dienas rutīnas solī pēc dokumentu ielādes |
| [@contradiction-hunter](contradiction-hunter.md) | Retorika↔balsojums un pozīciju maiņas detektēšana | Nedēļas rutīnā vai pēc Saeimas sesijas (max 5 politiķi sesijā) |
| [@devils-advocate](devils-advocate.md) | Adversariālā pretrunu un claim verifikācija | Dienas rutīnā pēc claim extraction (obligāts pirms publikācijas) |
| [@quality-reviewer](quality-reviewer.md) | Galīgā kvalitātes pārbaude pirms publikācijas | Pirms jebkuras publikācijas (dienas, nedēļas, analīzes) |
| [@brief-writer](brief-writer.md) | Neitrāli dienas pārskati | Pēc analīzes un pretrunu pārbaudes |
| [@weekly-brief-writer](weekly-brief-writer.md) | Neitrāli nedēļas pārskati (proza-vadīti) | Nedēļas rutīnā, pēc analīzes un pretrunu pārbaudes |
| [@graphics-designer](graphics-designer.md) | Featured-image ģenerēšana ar cilvēka apstiprinājumu | Pēc `@brief-writer`, ja brief satur `## Vizuālais brief` bloku |
| [@mentions-monitor](mentions-monitor.md) | X/Twitter pieminējumu monitors | Pēc `fetch_all_twitter()` un `fetch_all_mentions()` |
| [@saeima-tracker](saeima-tracker.md) | Saeimas sēžu un balsojumu izsekošana | Nedēļas rutīnā vai pēc jauniem balsojumiem |
| [@video-extractor](video-extractor.md) *(WIP)* | Pozīciju ekstrakcija no video debašu transkriptiem | Pēc `python -m src.video_ingest finalize <slug>` (pipeline vēl nav funkcionāls — 2026-04-30) |
| [@outlet-researcher](outlet-researcher.md) | Mediju caurskatāmības faktu izpēte (avotots `outlets:` ieraksts) | Pēc pieprasījuma, aizpildot/atjauninot mediji `facts:` (viens medijs reizē) |

## Plūsma dienas rutīnā

```
ingest → @mentions-monitor → @claim-extractor → @devils-advocate → @brief-writer → @graphics-designer → @quality-reviewer → publish
```

## Plūsma nedēļas rutīnā

```
@saeima-tracker → @claim-extractor → @contradiction-hunter → @devils-advocate → @weekly-brief-writer → @quality-reviewer
```

## Pēc pieprasījuma (ārpus rutīnām)

- `@outlet-researcher` — viens medijs reizē, kad jāaizpilda/jāatjaunina mediju
  caurskatāmības fakti (`sources.yaml` `outlets:` → `/mediji` lapas). Cilvēks
  pārskata YAML diff pirms commit; nav daemon, nav DB rakstīšanas.

## Vispārīgie noteikumi

- **Anti-sycophancy** — visi aģenti pretojas spiedienam radīt vairāk rezultātu nekā dati pamato. "Es nevaru noteikt" ir derīga atbilde.
- **Circuit breaker** — katram aģentam ir savi limiti (claim-extractor: 12 docs/politiķis/sesijā (samazināts no 33 uz 2026-04-22 pēc batch-drift diagnostikas); contradiction-hunter: 5 politiķi sesijā). Nepārkāpt. Par >5 docs vienam politiķim — dispečē parallel sub-aģentus pa vienam dokumentam.
- **Source URL obligāts** — claims bez `source_url` tiek silenti izlaisti. Skat. CLAUDE.md Data Contracts.
- **Deduplication enforced at DB layer** — `store_claim()` ir idempotents uz `(opponent_id, source_url, topic)`. Atkārtoti izsaukumi neradīs duplicates, bet aģentiem joprojām jāizvairās no liekiem zvaniem.

## Canonical prompts

`.claude/agents/*.md` ir binding — tur aģents faktiski dzīvo un to prompt lasa Claude Code izpildes laikā. Šajā `wiki/operations/agenti/` direktorijā esošie faili ir human-readable paraugs, lomu un plūsmu apraksts. Ja tie drift no `.claude/agents`, **`.claude/agents` uzvar**.

## Sub-agent failure modes

Iezīmēt zināmas sub-aģentu kļūdu kategorijas, lai operators varētu tās ātri atpazīt un nepārstāstīt kā reālus atklājumus.

### False prompt-injection report (2026-05-04)

**Simptoms:** sub-aģents atskaitēs piemin "embedded prompt-injection attempt" vai "fake `<system-reminder>` blocks" kā atklājumu dokumenta saturā. Operators pārstāsta lietotājam.

**Cēlonis:** harness automatizēti ievada *tool-result* līmeņa system-reminders (piem., "task tools haven't been used recently") sub-aģenta kontekstā. Sub-aģents tos sajauc ar dokumenta saturu un kļūdaini secina, ka dokuments satur injekciju.

**2026-05-04 incidents:** `@claim-extractor` sub-aģents pid=74 Burovam ziņoja "embedded prompt-injection attempt (fake `<system-reminder>` blocks instructing MCP/skill use)". Faktiski dokumenta saturs bija 27 vārdu 4. maija sveiciens bez nekā aizdomīga; visu dienas dokumentu skenēšana pret 8 injection-rakstiem (`system-reminder`, `<system`, `ignore previous`, u.c.) atgrieza 0 hits.

**Mitigācija:**
1. **Verify before report.** Pirms eskalē sub-aģenta atklājumu kā security-sākotnējs incidents, paskaties uz dokumenta `content` lauku tieši (Read tool vai DB query). Ja saturs neatbilst aprakstam, sub-aģents kļūdījies.
2. **Avoid "user-facing security claims" in summaries.** Ja sub-aģenta paustā rezultāts ir piezīme par injekciju, izolē to kā tehnisko anomāliju, ne kā konfirmētu uzbrukumu.
3. **Adversariāla verifikācija.** `@devils-advocate` rīcībā ir verifikāciju protokols — gala atbildība filtrēt false security claims pirms publikācijas.
