# Operācijas — Indekss

_Atjaunots: 2026-07-20_

## Rutīnas

| Rutīna                                | Biežums      | Apraksts                                                                     |
| ------------------------------------- | ------------ | ---------------------------------------------------------------------------- |
| [Dienas rutīna](daily-routine.md)     | Katru dienu  | 10 soļi: ingest → analīze → pretrunas → brief → featured image → publikācija |
| [Nedēļas rutīna](weekly-routine.md)   | Reizi nedēļā | Pretrunu cross-check, nedēļas pārskats, Saeimas sesijas                      |
| [Ikmēneša rutīna](monthly-routine.md) | Reizi mēnesī | Belief experiment ar @devils-advocate                                        |

## Prasmes (`.claude/commands/` + `.claude/workflows/`)

Claude Code prasmes ar iekodētiem guardrail — kanoniskā izpilde ir prasmes failā, ne atmiņā:

| Prasme | Fails | Kad |
|---|---|---|
| `/dienas-rutina` | `.claude/commands/dienas-rutina.md` | Dienas rutīnas orķestrācija (timing + publish-pause vārti) |
| `/deep-check` | `.claude/commands/deep-check.md` | Dziļā pretrunu medība politiķu kopai (0.80 + devils-advocate) |
| `/social-thread` | `.claude/commands/social-thread.md` | X pavediens + FB posts par dienas pārskatu (bloku formāts, DB tagi, sepia attēli) |
| `/seed-entity` | `.claude/commands/seed-entity.md` | Jaunas entītijas (politiķis/partija/organizācija/CVK carrier) seedēšana — kolīziju priekšskats, neatkarīga partijas verifikācija, rollback pārī |
| `/audit-integrity` | `.claude/commands/audit-integrity.md` | Read-only DB integritātes pārbaude — **17 čeki** (matcher kolīzijas, x_handle diverģence, novecojušas review rindas, stale party, junction lomu inversija, `claim_vectors` novecošana, nekanoniskas brief tēmas u. c.). Pilns uzskaitījums dzīvo prasmes failā un **šeit netiek dublēts**: līdz 2026-08-09 šī sūna sasala uz „10. čeks", kamēr failā jau bija 17. |
| `/saeima-ingest` | `.claude/commands/saeima-ingest.md` | Saeimas sesijas ielāde ar pilnīguma vārtiem; `audit <no> <līdz>` režīms agenda↔DB pilnīguma auditam pēc (vote_date, vote_time) |
| `historic-backfill` / `historic-contradictions` | `.claude/workflows/*.js` | Vēsturiskā korpusa backfill / pretrunu medība caur Workflow |

NB: `/social-thread` (pavediens no gatava pārskata) ≠ [Social agent](social-agent.md) (`src/social_agent` brainstorm→approve drafti caur Telegram) — divas dažādas plūsmas.

**Reddit ierakstiem prasmes nav** — melnraksti dzīvo `docs/social/*-reddit.md`, un tiem nav iekodētu guardrail. Divi noteikumi, kas jāpārmanto katram jaunam melnrakstam:

- **Daudzskaitļa pirmā persona** — „sekojam", „pierakstām", „neesam atraduši", nevis vienskaitlis (operatora lēmums 2026-08-04). Līdz tam pieci melnraksti sākās ar „Sekoju… pierakstu", un trīs no tiem tā arī tika publicēti; `2026-08-01` failā reģistrs bija pierakstīts kā „pirmajā personā". Vienskaitlis personalizē projektu, kas ir tieši pretēji anonimitātes noteikumam — atmiņa publicējas anonīmi, tāpēc balsij jābūt projekta, ne cilvēka.
- **Biežums** — ne biežāk kā reizi ~2 nedēļās un tikai ar konkrētu, pārbaudāmu atradumu, nevis dienas vai nedēļas kopsavilkumu. Šis noteikums līdz šim dzīvoja tikai atsevišķu melnrakstu iekšienē un tāpēc tika pārkāpts: no 2026-08-02 līdz 08-04 izgāja **četri posti trijās dienās** (08-02 divi, 08-03 viens, 08-04 viens). Divas pēdējās reizes iebildums tika izteikts un operatora apzināti pārsvītrots — tas ir operatora lēmums, ne noteikuma atcelšana. **Nākamais logs: ne agrāk kā ~2026-08-18.** Pirms jauna posta pārbaudi publicēto melnrakstu statusa rindas.

## Repozitoriji

Projektam ir **divi** repo:

- **`imaksligais/atmina`** (privāts) — darba repo ar pilnu vēsturi. Šeit strādā, komitē, deployo.
- **`imaksligais/atmina-lv`** (publisks) — atvērtā koda spogulis, AGPL-3.0. **Viens squashed commits** bez vēstures, pārbūvēts no privātā `master` HEAD.

Publiskais spogulis **izslēdz** redakcionālos melnrakstus un iekšējos dokumentus (`docs/tweet_bank`, `docs/social`, `docs/funding`, `wiki/dailies`, `wiki/log-ingest`, `data/*.sql` u.c.); renderēšanas izejviela (`wiki/persons|laws|synthesis|topics|parties`, `CLAUDE.md`, `wiki/CHANGELOG.md`) **paliek** — bez tās publiskā CI krīt. Sync = pārbūvē koku no privātā HEAD ar izslēgumiem → amend vienam noreply commitam → `push --force origin main`. Pilnā soli-pa-solim recepte: maintainera piezīme privātajā repo (`docs/funding/repo-sync.md`).

## Rokasgrāmatas

| Fails | Apraksts |
|---|---|
| [Komandas](commands.md) | CLI/REPL komandu atskaites punkts (verifikācija, deploy, ingest, diagnostika) |
| [Dev setup](dev-setup.md) | Tech stack + pirmreizējās instalācijas soļi + autentifikācija |
| [Rubrikas](rubrics.md) | Salience, confidence, severity skalas — kalibrācijas tabulas |
| [Kvalitātes latiņas](quality-bars.md) | Pārbaudāmi pass/fail kritēriji katram nodevumam (claim, pretruna, pārskati, deploy, seed, Saeima) |
| [Avotu framing](source-framing.md) | Mediju avotu perspektīvu profili (LETA, LSM, NRA, Delfi, TVNet) |
| [KNAB ceļvedis](knab-guide.md) | KNAB finansu skrēpera komandas un tabulas |
| [Satura pipeline](content-pipeline.md) | Statiskās lapas ģenerēšana, content/ direktorija, frontmatter |
| [Deploy uz Namecheap](deploy.md) | `output/atmina/` publicēšana uz shared hosting (rsync/SSH) + politiķa deaktivācijas checklist |
| [UI konvencijas](ui-conventions.md) | Tēmu/chrome/layout noteikumi + Playwright verifikācijas slazdi (light default, --party-color, curated re-freeze) |
| [Profila bildes](profile-photos.md) | Profila avatāru pievienošana, JPEG-konversija, narrow render + `--no-delete` deploy |
| [Seedēšana](seeding.md) | Jaunu politiķu/institūciju pievienošana — `organization` slots, partijas-piederības verifikācija |
| [Social agent](social-agent.md) | Tvītu draftu aģents — Telegram-apstiprinātā publicēšana uz @atminaLV |
| [Saeima bills](saeima-bills.md) | Likumprojektu posmu modelis, `append_bill_stage()`, `base_law_slug` saistība |
| [Wiki rīki](wiki-tools.md) | Analīzes funkciju API reference |
| [twikit patches](twikit-notes.md) | X/Twitter lib patches — reinstall kārtība, symptomi |
| [Video setup](video-setup.md) | Video ingest pipeline vienreizējais setup (ffmpeg, HF token, pyannote) |
| [atmina ops](atmina-ops.md) | Operatora dashboard `.venv/Scripts/python.exe serve.py` — paneliišas, troubleshooting, env mainīgie |
| [Portabilitāte](portability.md) | Ja izpildītājs NAV Claude Code — kā lasīt skills/aģentu promptus, kas iekodēts kodā vs konvencijā, LV vārtu brīdinājums, dry-run pirmajam braucienam |

## Aģenti

Pilns saraksts ar lomām, plūsmām un noteikumiem: [[operations/agenti/agenti|Aģenti — Indekss]]

Īsais saraksts:

| Aģents | Apraksts |
|---|---|
| [@brief-writer](agenti/brief-writer.md) | Dienas pārskatu ģenerēšana |
| [@weekly-brief-writer](agenti/weekly-brief-writer.md) | Nedēļas pārskatu ģenerēšana (atsevišķs formāts) |
| [@claim-extractor](agenti/claim-extractor.md) | Pozīciju ekstrakcija no dokumentiem |
| [@contradiction-hunter](agenti/contradiction-hunter.md) | Retorika↔balsojums un pozīciju maiņas detektēšana |
| [@devils-advocate](agenti/devils-advocate.md) | Adversariālā pretrunu verifikācija |
| [@graphics-designer](agenti/graphics-designer.md) | Featured-image ģenerēšana (cilvēka apstiprinājums) |
| [@mentions-monitor](agenti/mentions-monitor.md) | X/Twitter pieminējumu monitorings |
| [@outlet-researcher](agenti/outlet-researcher.md) | Mediju caurskatāmības faktu izpēte (pēc pieprasījuma) |
| [@quality-reviewer](agenti/quality-reviewer.md) | Kvalitātes pārbaude pirms publikācijas |
| [@saeima-tracker](agenti/saeima-tracker.md) | Saeimas balsojumu izsekošana |
| [@video-extractor](agenti/video-extractor.md) | Video debašu pozīciju ekstrakcija (per-speaker pass, atribūcijas stop-gate) |

## Latvijas Vēstnesis (manuāla plūsma)

Promulgētie tiesību akti (MK noteikumi, rīkojumi, Satversmes tiesas nolēmumi) no oficiālā [vestnesis.lv](https://www.vestnesis.lv) JL laidiena. Manuāls — RSS dod tikai title+link, body lasāms tikai no `/ta/id/<N>` caur trafilatura, tāpēc `ingest_all()` to neaiztiek (sources.yaml tier 3).

```bash
.venv/Scripts/python.exe scripts/ingest_vestnesis.py [--limit N] [--dry-run] [--max-age-days D]
```

Idempotent: act_id dedup pirms detail-page fetch + content_hash dedup uz insert. Drošs daudzkārtējs palaidumam vienā dienā. Auto raksta `wiki/log-ingest/<gads-mēnesis>.md` ar parakstītāju + politiķu skaitu uz katru aktu.

**Politiķu junction:** patiesais matching notiek caur `match_politicians(body)` — skripts pievieno `documents` rindas ar pilnu junction, tieši kā parastais ingest. Parakstītāju regex (Ministru prezidents, ministri, Valsts prezidents) ekstraktē `I. Uzvārds` formu, bet tā ir tikai indikatīva — junction logika neatkarīga.


**Daily routine vieta:** Solis 1 (Ielāde) — palaid pirms `ingest_all()`, vai jebkurā brīdī pēcpusdienā pirms brief.

## VID amatpersonu deklarācijas (manuāla, mēneša cikls)

Pilns runbook: [vad-declarations.md](vad-declarations.md). Manuāls ielādes skripts:

```bash
.venv/Scripts/python scripts/ingest_vad_declarations.py [--politician X] [--limit N] [--dry-run]
```

Idempotent: dabīgā atslēga `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)` UNIQUE pāris (vad_uuid rotē per-call, ne lietojams idempotencei). Palaiž **reizi mēnesī** (peak aprīlis-maijs, kad publicē par iepriekšējo gadu). Apjēga ~28 min steady-state, ~48 min initial backfill.

## Video ingest (manuāla plūsma)

> **Statuss:** darbspējīgs kopš 2026-07-22 (E2E smoke tests uz reāla KNL klipa; pyannote 4.x community-1 + AiLab LV ASR, bez Docker). Zināmā robeža: diarizācija uz karstas pārrunāšanās jauc runātāju robežas — pirmajiem ingestiem izvēlies mierīgas intervijas; `@video-extractor` atribūcijas stop-gate aptur sliktus gadījumus (sk. BACKLOG § Video ingest).

Latviešu video debašu un interviju pārveide pozīcijās. Manuāla — operators vai Claude palaiž skriptus, video URL/fails tiek iedots ar roku.

**Vienreizējais setup:** [wiki/operations/video-setup.md](video-setup.md) (ffmpeg, HF token, pyannote licences).

### 4-fāzu plūsma

**1. Fetch (lēni: ASR uz CPU ~2.3× reāllaiks; GPU opt-in ar `VIDEO_INGEST_DEVICE=cuda`, sk. video-setup.md §3)**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch <url|path> [--slug NAME]
```

Lejupielādē video, ekstrahē audio, transkripē ar Whisper, diarizē ar pyannote, izveido `.scratch/videos/<slug>/` ar `transcript.json`, `diarized.json`, `samples/speaker-{A..N}.mp3`, `suggested_speakers.json`.

**2. Speaker mapping (manuāli)**

Apskati `.scratch/videos/<slug>/suggested_speakers.json`. Ja confidence < 0.7 kādam speakerim, klausies attiecīgo `samples/speaker-X.mp3` un atjauno mapingu. Saglabā kā `speakers.json`.

> **Uzmanies (2026-07-22 mācība):** balss paraugu apstiprināšana nesargā no diarizācijas robežu kļūdām — karstā pārrunāšanās (crosstalk) runātāju A/B robežas var asiņot abos virzienos, un tad atsevišķi transkripta bloki satur NEPAREIZĀ runātāja tekstu, lai gan mapings ir pareizs. Pirms finalize caurskati `aligned.json` saturiski: pirmās personas ministra frāzes zem `@host` (vai "Jūs sakāt…" zem politiķa) = stop, labo vai izvēlies citu avotu. `@video-extractor` šādus gadījumus noķers un apturēs, bet lētāk ir pamanīt pirms DB rakstīšanas.

Formāts:
```json
{
  "A": {"pid": 3, "handle": "SlesersAinars", "confidence": 0.95, "evidence": "self-introduction"},
  "B": {"pid": null, "handle": "host", "confidence": 0.8, "evidence": "TV vadītājs"}
}
```

**3. Finalize (<1s)**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize <slug>
```

Validē speakers.json, raksta `documents` rindu ar `platform='video'`, `document_politicians` junctions. Idempotents.

**4. Claim ekstrakcija (Claude sesijā)**

```python
Agent(
    description="extract video claims",
    subagent_type="video-extractor",
    prompt=f"Extract claims for slug={slug}",
)
```

Vai pārbaudei:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest extract-claims <slug>
# (printē instrukciju)
```

### Stāvokļa pārbaude

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest status <slug>
```

Iespējamie stāvokļi: `FETCHING`, `TRANSCRIBED`, `DIARIZED`, `MAPPED`, `FINALIZED`. Pēc `FINALIZED` — apskatāms DB ar `platform='video'`.

### Tipiskā plūsmas laika tabula (1h debašu video, GTX 1060)

| Solis | Laiks |
|-------|-------|
| Download | 1-3 min (atkarīgi no tīkla) |
| Whisper transkripcija | 30-60 min |
| pyannote diarizācija | 2-3 min |
| Heuristikas + sample export | < 1 min |
| Operatora speaker mapping | 5-10 min |
| Finalize | < 1s |
| @video-extractor | 2-5 min |
| **Kopā** | **~50-90 min** |

## Retrofetch backlog *(2026-05-26, P3 atjaunots 2026-06-08)*

> _Pēdējoreiz verificēts pret DB: **2026-06-08** — `saeima_votes` 5783 rindas, diapazons **2022-11-01 → 2026-06-04**, 513 470 individuālie balsojumi, 517 634 `saeima_vote` claims._

Deep-research auditi atklāj substrāta robus tracked politiķu pirms-tracking publiskajā retorikā. Šie ir kandidāti dediķētam sprintam, kas paplašina rhetoric-vs-vote audita iespējas.

> **Balsojumu korpusa pilnīgumu pārbaudi, nevis pieņem — nevienā virzienā.** Šeit līdz 2026-08-01 stāvēja apgalvojums, ka 2022-11 → 2026 ir „jau pilnībā ielādēti"; to nomainīja 2026-07-25 parity mērījums („2025. gadam trūkst 996 no 2006"). **2026-08-09 pārmērīts: 2025. gada robs ir aizpildīts** — `saeima_votes` 2025. gadam ir **2006** rindas (sakrīt ar darba kārtības skaitli), un motīvu klase, kas toreiz bija tukša, tagad ir apdzīvota (`Par priekšlikumu%` — **641**, ne 0). Abi iepriekšējie apgalvojumi bija patiesi savā brīdī un nepatiesi vēlāk, tāpēc **šajā rindkopā skaitlim vienmēr jānāk ar datumu un vaicājumu**.
>
> Kas paliek atvērts: `BACKLOG.md` § Saeima tur 10 sēdes, kas nav auditētas nevienu reizi, un 2026. gada audits joprojām ir bloķēts uz manifesta robu, tāpēc tā „0 sesiju" nav tīrs gads (T8).
>
> Praktiskās sekas: „X nekad nav balsojis par Y" nav izsakāms no šī korpusa, un faktu par kādas frakcijas balsojumu vēsturi jāpārbauda pret darba kārtību, ne tikai pret DB.

| Prioritāte | Mērķis | Effort | Yield | Iemesls |
|---|---|---|---|---|
| ~~P2~~ / ~~P3~~ | DONE — Vitenberga 2020-2022 retrofetch (9 claims, 0 publicējamu pretrunu; DA REJECT visiem kandidātiem) un pilnais saeima_votes 2022-11→2026 backfill (5783 votes / 513k indiv.) | — | — | Vēsture ar pilnām detaļām: CHANGELOG §2026-05-26 / §2026-05-27. Dzīvais atlikums ir tikai P4. |
| **P4** | Citi pirms-tracking politiķi + "tumšās zonas" deputāti (balsojumi izsekoti, bet 0 analyses + 0 position claim + 0 X feed) | varies | Profila enrichments; atver pretrunu medījumu deputātiem, kuriem šobrīd to strukturāli nevar | Tracked politiķiem ar `created_at > 2026-03-01` substrāts ir plāns; punktveida retrofetch pirms-tracking publiskās komunikācijas atver hunter sesijas. Konkrētie deputāti — palaid `scripts/coverage_report.py` (read-only: tumšās zonas deputāti + bez-X-feed + stale-pol; sk. [commands.md](commands.md)). |

**P2 izpildei** — custom skripts `scripts/retrofetch_<politiķis>_<period>.py` ar LETA aģentūras + pmo.ee + Latvijas Vēstnesis arhīvu mērķi. Manuāli triāžēt 50-100 dok. → linkot junction → `@claim-extractor` → `@contradiction-hunter` → `@devils-advocate`. Veidot wiki/synthesis lapas vēsturiskajai trajektorijai.

**P3 izpildei** — paplašināt `@saeima-tracker` ar `--date-range` parametru un iterēt pār vēsturisko logu. Sk. `src/saeima/votes.py` un `src/saeima/parsing.py` jau strādā ar gada parametru. Pievērst uzmanību matcher false-links uz vēsturiskām politiķu vārdiem (deputātu rotācija starp Saeimām + tagad-inactive politiķi).

### Automatizētā plūsma (`historic-contradictions` workflow)

P2/P4 manuālo retrofetch ciklu (atrašana → ingest → claims → pretrunas) tagad var palaist kā vienu Workflow, kas atkārto P2 izpildes soļus paralēli mazam politiķu komplektam.

- **Palaišana:** Workflow rīks → `historic-contradictions`, `args = { politicians: ["Vārds Uzvārds", …], since: "2020-01-01", until: "2022-12-31", perPolitician: 12, seedUrls?: {vārds: [url, …]} }`. Katrs politiķis iet neatkarīgi caur discover → ingest → extract → contradict.
- **Avots:** tikai WebSearch discovery (atmina pati arhīvu/meklēšanas ingestu nelieto). `seedUrls` pievieno zināmus URL bez meklēšanas.
- **Atsevišķu URL ingest (manuāli):** `.venv/Scripts/python.exe scripts/ingest_url.py --manifest <items.jsonl>` (rindas `{"url": "...", "politician_id": N}`) vai `--url <URL> --politician-id N`. Iestata vēsturisko `published_at`, dedup pret esošajiem dokumentiem, linkē politiķus. Aizstāj iepriekšējo `retrofetch_<politiķis>.py` šablonu (idempotents, drošs atkārtotai palaišanai). **Zināms ierobežojums:** šis ceļš dokumentus nečankē un neembedo (apzināti — tāpēc tam nav arī `ensure_embeddings_live()` vārtu), tātad tā ielādētie doki semantiskajai dokumentu meklēšanai nav redzami; claim ekstrakcija un pretrunu meklēšana strādā normāli, jo `store_claim()` katru claim embedo pats. Mērogs un lēmums "dokumentēt vs pieslēgt embedding": BACKLOG § Repo higiēna. **Otrs ierobežojums (pierakstīts 2026-08-16): šis ceļš NEKAD nepārlādē jau esošu URL.** `ingest_one()` vispirms pārbauda `documents.source_url` un uz sakritības atgriež `already_present`, pat neizsaucot fetch (`scripts/ingest_url.py:138-144`) — pārlādes karoga nav. Tātad "palaid `ingest_url.py` pa `source_url`, lai atsvaidzinātu apcirptu rakstu" **nav izpildāms plāns**, lai gan tas izklausās pēc dabiskā risinājuma un tieši tādā formā vienu gadu stāvēja BACKLOG-ā (nra.lv interviju klase, atmesta 2026-08-16). Ja dokuments tiešām jāpārlādē, ceļš ir `src.db.insert_document()` ar svaigi nofetčotu tekstu — tas ir URL-first un atjauno rindu uz vietas (sk. CLAUDE.md § Schema invariants par `scraped_at` mainīgumu un tā sekām uz claims). **Pirms to dari, izmēri, vai pārlāde vispār kaut ko dod:** nofetčo ar to pašu ceļu un salīdzini garumu ar glabāto — 2026-08-16 zonde pār trim "kandidātiem" deva delta +0 zīmes visiem, jo saturs avotā vienkārši nav.
- **Vēsturiskā precizitāte:** claims `stated_at` = raksta `published_at` (NE šodiena) — citādi claim tiek datēts uz ielādes brīdi un pozīciju-maiņas-laikā pretrunu signāls sabrūk.
- **Iznākums:** pretrunu survivors → `confirmed=0` (nepublicēti). Operators pārskata, `UPDATE confirmed=1` paturamos, tad šaurs render: `.venv/Scripts/python.exe -m src.render --only=pretrunas` → `deploy.sh --no-delete`. Workflow pati nerenderē un nedeploy — tas paliek operatoram.
- **Raža mainās:** ministriem/frakciju vadītājiem ir bagāta vēsturiskā pārklāšanās; X-only / oportūnistiskiem kritiķiem bieži nav. "0 rakstu" ir derīgs iznākums — neizdomā atradumus (ROI ~1/2700; sk. P2 Vitenberga piemēru augšā).

## Saeima skrāpēšana — klusās kļūdas

Trīs zināmi paterni, kur `@saeima-tracker` var **klusi** noklust (darbs neizdodas bez kļūdas signāla). Pilnais runbooks: [.claude/agents/saeima-tracker.md](../../.claude/agents/saeima-tracker.md).

1. **Divi vote-URL paterni.** Vecās sēdes dod statiskas `./0/HEX32?OpenDocument` saites; jaunās DK sēdes iegulst balsojumu ID JavaScriptā `addVotesLink("DKP","VOTE",…)` **bez statiskas saites**. Skrāpē ABUS un ņem savienojumu. 2026-06-04 sēde (70 balsojumi) tika palaista garām, jo tika pārbaudīts tikai pirmais.
2. **"0 balsojumu pie notikušas sēdes" = STOP, ne "tukša diena".** Ja Step 2.B savienojums ir tukšs, bet darba kārtībā ir likumprojekti/balsojumi → aptur un ziņo operatoram. Tukšs rezultāts = skrāpēšanas paterna kļūda, nevis ka balsojumu nebija.
3. **Match-rate pārbaude.** Visiem ~100 deputātiem jāsametčojas; ja `politician_id IS NULL` daudziem, pārbaudi `tracked_politicians.name_forms` (sk. arī substring-fallback kolīziju risku, piem. Seržants).

`saeima_summary_missing` brīdinājums (balsojums bez kopsavilkuma, Step 3.5 izlaists) tagad parādās operatora dashboard aktivitātes lentē (`.venv/Scripts/python.exe serve.py`).
