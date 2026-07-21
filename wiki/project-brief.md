# atmina — Projekta pārskats

_Atjaunots: 2026-04-30_

> **Par stāvokli:** šis fails ir augsta līmeņa apraksts — kas ir atmina, kā tā strādā, kāda ir tās arhitektūra. **Skaitļiem (politiķi, pozīcijas, balsojumi, dokumenti, top tēmas) skat. [[index]]** — tas auto-atjaunojas pēc katra ingest. Šeit hard-kodēti skaitļi tika izņemti 2026-04-30, jo tie regulāri novecoja.

## Kas ir atmina.lv

Latvijas politiskās caurskatāmības platforma. Apkopo ziņu avotus, Saeimas datus un sociālo tīklu ierakstus, ekstrahē strukturētas pozīcijas (claims) un atklāj pretrunas politiķu izteikumos. Publicē interaktīvu statisku vietni.

> **Par pozīciju skaitu:** kopš 2026-04-11 `claims` tabula nošķir `position` (mediju/X retorika) no `saeima_vote` (Saeimas balsojumi). Agrāk abus skaitīja kopā, un "pozīciju" skaits izskatījās 8× lielāks par faktisko retorisko aktivitāti. Detaļas: [[CHANGELOG]].

## Datu avoti

- **Saeima** (titania.saeima.lv) — likumprojekti, sēžu darba kārtības, individuālie balsojumi
- **X/Twitter** — politiķu tvīti + pieminējumi (twikit cookie auth)
- **Ziņu portāli** — NRA, Delfi, LSM, TVNet, Diena, LETA, LA, Jauns.lv (RSS + scraping)
- **KNAB** — finanšu deklarācijas, ziedojumi, brīdinājumi
- **Video** *(WIP)* — debašu un interviju transkripti (Whisper + pyannote)

## Tehnoloģiju steks

- **Python 3.11+** — `src/` moduļi + `tests/` testu faili
- **SQLite (WAL)** — 35+ tabulas, **sqlite-vec** 384-dim embeddings (`intfloat/multilingual-e5-small`)
- **Jinja2** šabloni → statisks HTML `output/atmina/` (kanoniskais ceļš: `from src.render import generate_public_site`)
- Skrāpošana: httpx + trafilatura + BeautifulSoup4, twikit (X/Twitter cookie auth)
- NLP: simplemma (latviešu lemmatizācija), fasttext (valodas noteikšana)
- KNAB finanšu dati (ziedojumi, deklarācijas, brīdinājumi)
- Saeimas balsojumu dati (sesijas, darba kārtības punkti, individuālie balsojumi)

## Arhitektūra

```
Ingest → Dokumenti → [Claude Code analīze] → Pozīcijas/Pretrunas → Statiskā vietne
  │                                               │
  ├─ Ziņu skrāperi (LSM, Delfi, NRA u.c.)       ├─ Pozīcijas (katram politiķim pa tēmām)
  ├─ Saeimas skrāperis (likumprojekti, balsojumi)├─ Pretrunas (pretrunu starp pozīcijām)
  ├─ X/Twitter skrāperis (twikit)                ├─ Tendences (konteksta piezīmes)
  └─ KNAB finanšu skrāperis                      └─ Dienas pārskati
```

**Galvenā dizaina izvēle:** Claude Code ir analīzes dzinējs — pozīciju ekstrakcija un dienas pārskati tiek veikti interaktīvi sarunā, nevis automatizētos skriptos.

## Aģentu sistēma (9 specializēti aģenti)

- `@claim-extractor` — neitrāla pozīciju ekstrakcija no dokumentiem
- `@contradiction-hunter` — retorika↔balsojums un pozīciju maiņas detektēšana
- `@devils-advocate` — adversariālā pozīciju verifikācija
- `@quality-reviewer` — datu integritātes un neitralitātes pārbaude pirms publicēšanas
- `@brief-writer` — dienas/nedēļas neitrālie kopsavilkumi
- `@graphics-designer` — featured-image ģenerēšana (nanobanana + cilvēka apstiprinājums)
- `@mentions-monitor` — X/Twitter pieminējumu apkopošana
- `@saeima-tracker` — parlamenta darba kārtības un balsojumu skrāpošana
- `@video-extractor` *(WIP)* — pozīciju ekstrakcija no video debašu transkriptiem (pipeline vēl nav funkcionāls)

## Izvade

Statiska vietne: sākumlapa, politiķu profili ar laika līniju, partiju lapas, tēmu lapas, pozīciju pārlūks, pretrunas, spriedzes, balsojumi, finanses, X plūsma, ziņas, blogs, par mums.

## Pastāvīgie ierobežojumi

- Paywall bloķēts saturs (TVNet, Delfi) — daļa rakstu paliek ar truncated body
- pietiek.com bloķē Cloudflare — nav iekļauts (sk. memory `project_pietiek_source.md`)
- X/Twitter rate limits — vienam cookie kontam ar laiku tiek noslogots; nepieciešama rotācija
- Aktuālo backlog (neapstrādātie dokumenti) skat. [[index]]
