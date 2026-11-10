---
name: dienas-rutina
description: Drive the atmina.lv daily routine — status check, afternoon analysis fan-out, contradiction + devils-advocate pass, brief (human-gated), narrow render + --no-delete deploy. Encodes the timing + publish-pause + LV-style guardrails.
argument-hint: "[YYYY-MM-DD] (defaults to today)"
---

# Dienas rutīna — atmina.lv

> **Pass/fail kritēriji dienas pārskatam — [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md). Izlasi PIRMS glabāšanas/publicēšanas, ne pēc.** CLAUDE.md § Quality Bars sauc šo failu par kanonisko nesēju.

Agrākās, garākās versijas (ar noteikumu vēsturi): `git log -- .claude/commands/dienas-rutina.md`.

Orchestrate today's routine. **Canonical state first**, then editorial steps. Respect the guardrails below — they encode prior incidents, not preferences.

## 0. Status

```bash
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

**Pasts** (`redakcija@atmina.lv`) nav rutīnas solis: `SessionStart` hook (`scripts/mail_tool.py remind`) jaunas sesijas sākumā atgādina, ja tās dienā iesūtne nav skatīta; pa dienu operators pats palūdz paskatīties (operatora lēmums 2026-10-18). Atbildes — tikai ar operatora «jā».

**Never bare `python`** — on the operator machine it resolves to a foreign venv, and the failure mode is a PARTIAL WRITE, not a clean error (CLAUDE.md § Commands).

**TypeSafe matcher veto — izslēgts (operatora lēmums 2026-10-12).** `scripts/morning_ingest.py` noklusējums ir `off` (`os.environ.setdefault`; gate `tests/test_morning_ingest_veto_default.py`): ēnas nedēļās veto regulāri noraidīja īstus politiķus (`backlog/dati-db.md` § 2026-09-18 (a)). Ikdienas `typesafe_veto_report.py` vairs nav rutīnas solis. `ATMINA_TYPESAFE_VETO=shadow|enforce` joprojām pārspēj noklusējumu vienam procesam. Saišu priekšlikumi (5. solis, `saites_proposals.py`) TypeSafe lieto atsevišķi un paliek.

Open work: `BACKLOG.md` and `backlog/*.md` (CLAUDE.md § Session Start). The 11 steps (+ 2b «backlog») live in `src/routine.py`; the agents in `.claude/agents/*.md`.

## Timing guardrails (HARD)

- **Ingest runs all day.** A morning "0/N analizēti" is EXPECTED, not a backlog warning (CLAUDE.md § Standing Decisions — Timing).
- **Analysis + brief are afternoon-only (≥15:00 LV).** Do NOT dispatch `@brief-writer` or run extraction before ~15:00.

## Steps (afternoon)

1. **Ingest** — confirm new documents landed (step shows count). Don't force it in the morning. `scripts/morning_ingest.py` exit code `1` / `KOPSAVILKUMS: N/5` below 5 = a step failed (named in the summary) — re-run it; exit 0 alone is the clean signal.
1b. **Vēstneša paraksta-pāri** (pirms ekstrakcijas plāna) — `.venv/Scripts/python.exe scripts/stamp_vestnesis_signatures.py` (dry-run). Ja paraksta-pāru > 0: `--write-rollback` → commitē `data/rollback_vestnesis_stamp_<datums>.sql` (`git commit -F`) → `--apply` (atsaka bez commitēta rollback vai ar citu pāru kopu). Raksta tikai pāra `extracted_at`, nekad `reviewed_at` (`src/vestnesis_stamp.py`).
2. **Pozīciju analīze** — fan out `@claim-extractor` in **parallel sub-agents**. Nepako ar roku: palaid `.venv/Scripts/python.exe scripts/plan_extraction.py --days 2` un dispatchē pa tā rindām — katrs `#N` ir viens apakšaģents, `kārta K` secība ir obligāta (nākamo kārtu sāc tikai pēc iepriekšējās pabeigšanas), `rt` aģenti (tīrie «RT @» doki) iet pēdējā kārtā. Noteikumi (pakošana ≤2 doki līdz 8 dokiem, viens pid = viens aģents kārtā, >12 doki → secīgas kārtas, RT pakošana, ≤10 aģenti kārtā) dzīvo `src/extraction_plan.py`; kopsavilkuma rindu rāda arī `print_routine`. Plāns katrā kārtā ieliek ne vairāk kā 10 paralēlus aģentus, jo katrs aģents ielādē embedding modeli (vairāk izsmeļ atmiņu); pārējie pāriet uz nākamo kārtu. Ja aģentu atskaitēs apstrādāto pāru kopskaits nesakrīt ar plāna `pāri`, STOP un salīdzini. Each claim still carries its own politician's `opponent_id` — cross-attribution inside a shared agent is the batch failure mode to watch. Scale wide; if diacritic validation trips in any context, stop that context and start a fresh one (CLAUDE.md T4). Circuit breakers: cap batch size (≈12 docs / 12 politicians) + the `NEEDS_REVIEW` gate to avoid indirect-reference saves (kanoniskie noteikumi: `.claude/agents/claim-extractor.md`). Every claim needs a `source_url` or it is dropped — and the drop IS reported, as a `missing_source_url` entry in `save_analysis()`'s returned `failures` with `status="partial"`. It goes to stderr and never raises, so it is easy to miss but not silent: read `failures` and treat every entry as a real lost claim (T3). `save_analysis()` atsaka arī pozīciju bez burtiska `support` fragmenta no ŠĪ dokumenta (`missing_support` / `support_not_in_source` — `src/support.py`); aģentam tā jāizlabo un jāsaglabā vēlreiz, un atskaitē saglabāto skaitam jāsakrīt ar iecerēto.
2b. **Veci neizskatīti pāri** — ja solis «2b» ir ◐ (vairāk par `STALE_PAIRS_MAX` = 20 vecu pāru), palaid `.venv/Scripts/python.exe scripts/plan_stale_sweep.py` un dispatchē pa plāna gabaliem tikai Opus `@claim-extractor` ar brīfu `wiki/operations/stale-sweep-brief.md` (≤12 doku gabalā). Runbook: `wiki/operations/operacijas.md` § Veci neizskatīti pāri.
2c. **Dienas NEEDS_REVIEW pozīcijas** — pēc ekstrakcijas `print_routine` rāda «Jāpārbauda šodien: N». Katru no tām izvērtē ar advisor; avotu lasi ar `src.analyze.get_claim_source(claim_id)` (konteksts tikai lasīšanai; citāts/support tikai no runātāja teksta). Skaidrajām `reasoning` marķieri `NEEDS_REVIEW:` aizstāj ar `Izvērtēts YYYY-MM-DD: <pierādījums no avota>. Sākotnēji: …` (sākotnējā tekstā marķiera vārdu neatkārto — trigeris rindu atkal atzīmētu), ar pāra rollback (escalation 8). Neskaidrās (apmelošanas risks, neatšifrējams konteksts) atstāj operatoram: skelets tās izlaiž pats un nosauc komentārā `NEEDS_REVIEW IZLAISTAS`.

2d. **Pozīciju neatkarīgā pārbaude** (pastāvīgs solis) — pēc 2c un pirms 3. soļa dispatchē `@stance-checker` pār rutīnas dienas pozīcijām (≤60 pozīcijas vienam aģentam, vairāk → dali pēc `opponent_id`; izvade `.scratch/stance-check/<diena>.json`). Atzīmes piemēro orķestrators pēc `.claude/agents/stance-checker.md` § Orķestratoram: B un C tikai pēc paša avota lasījuma, A nekad automātiski; `scripts/apply_stance_fixes.py` ar pāra rollback. Atskaitē nosauc «vērtētas N no M». `print_routine` šo soli nerāda — pēda ir JSON fails un rollback commits.

   **Divi pastāvīgi soļi:**
   - **±5 d aģentūras dublikātu pārbaude — katrā dispatch promptā.** Pirms glabāšanas aģents pārbauda `get_existing_claims(pid, stated_around=<raksta datums>)` (logs pēc `stated_at` ±5 d, ne pēc `created_at`) — tas pats izteikums no cita avota jau glabāts → NEGLABĀ, piemin atskaitē. Drošības tīkls pēc glabāšanas: `save_analysis()` atgrieztajā `failures` sarakstā ieraksts `possible_duplicate` (tikai ziņo, nebloķē) — aģents to nolasa un izvērtē atskaitē (logs ±5 d ir operatora lēmums 2026-08-18; ±2 d bija par šauru). Zināmās robežas: neiet RT-skip slotos un neredz cita pid dublikātus.
   - **Junction-atgūšana PĒC ekstrakcijas (orkestratora solis).** Citētie runātāji ar `role='mentioned'` nekad neienāk `get_pending_politicians` rindā (reviewed_at ir per-dokumenta) — pēc galvenā fan-out palaid apsekojumu un dispatchē atgūšanas aģentu atrastajiem pāriem:
     ```bash
     .venv/Scripts/python.exe scripts/recovery_survey.py --days 2          # --json mašīnlasāmai izvadei
     ```
     Katram pārim, ko atgūšanas aģents izlasīja un apzināti neko neglabāja (dublikāts, cita runa, satīra), atzīmē izvērtējumu, citādi tas paliek ATGŪŠANA rindā: `.venv/Scripts/python.exe -c "from src.quoted_speaker import mark_recovery_evaluated as m; m(<doc_id>, <pid>, '<īss iemesls>')"` (ja doka teksts vēlāk mainās, pāris atgriežas pats).
     Tas ir agrākais rokas SQL kodā (`src/quoted_speaker.py::recovery_survey`): josla `inversion` = `pending_quoted_mentioned` (runā tikai `mentioned`), josla `beside_subject` = runājošs `mentioned` blakus subjektam (`extracted_at IS NULL`, bez `inactive`/`journalist`/`organization`, nominatīva forma ± citāta signāls), `aklā zona` = doki bez subjekta (tikai skaits). Rinda ar `pārbaudīti N pāri` rādās arī `print_routine()` izvadē. Kāpēc tikai inversijas josla nepietiek: tā var dot 0, kamēr atgūstamās pozīcijas ir dokos, kur runā arī subjekts. Jautājuma verbi: atgūšanas apsekojums skaita arī «jautāja/jautā/prasīja/prasa/sprieda/norādot» (`RECOVERY_EXTRA_SIGNALS`, tikai atgūšanai), tāpēc deputāts, kas sēdē tikai jautā, parādās; audita `find_inversions` bāzes signālu sarakstā (`CITATION_SIGNALS`) šo verbu joprojām nav — tas apzināti iesaldēts. Platformu kods nefiltrē, tāpēc parādās arī `vestnesis` pāri (MK sēžu protokoli) — Vēstnesis ir ārpus ekstrakcijas rindas, un lēmums par tiem ir operatora, ne atgūšanas aģenta.

     **Tavs apsekojuma vaicājums NEDRĪKST atkārtot koda filtru.** Kad orkestrators pats rakstīja `platform='web'` — to pašu, kas tolaik bija `find_inversions` iekšā —, releja tvītu izteikumi aizgāja garām. **Divi vārti ar vienu aklo zonu nav divi vārti.** Kods sedz `web` + `twitter` + `x_mention` (`DEFAULT_INVERSION_PLATFORMS`), un `recovery_survey()` platformu **nefiltrē vispār** — ja raksti papildu vaicājumu, arī tu nefiltrē; joslas salīdzini pēc `by_platform`, ne izslēdz.

     **Un tvītu joslu lasi citādi nekā web joslu:** 08-27 mērījumā ~puse jauno tvītu atradumu bija viltus pozitīvi, un tos dominē SATĪRA (izdomāti «citāti» īstiem politiķiem). Strukturāla filtra tam nav — satīras kontu tur `relationship_type='tracked'` deputāts. Šķirotājs ir `@claim-extractor` satīras/RT vārti; nekad neuzskati šīs joslas pāri par apstiprinātu pozīciju.

   **Model pin — pass it explicitly on every fan-out.** All project agents carry `model: opus` in frontmatter, but that pin does **not** reach a plain `agentType: 'general-purpose'` call, and sub-agents must never inherit a Mythos-tier session model (CLAUDE.md § Standing Decisions, operator decision 2026-07-21). When dispatching via `Workflow`/`agent()`, pass `model: 'opus'` on each call; when dispatching a named project agent via `Agent`, the frontmatter pin covers you. Orchestration itself may run on any tier.
3. **Pretrunu pārbaude** — for each new claim, `search_similar_claims` with a directional `claim_type_filter`; candidates go to `@devils-advocate` FIRST; store only survivors via `src.tools.store_contradiction(..., reviewed=True, headline=…)` (`headline` — konkrētais jautājums OG kartītei, ≤60 zīmes, bez vērtējuma) (`confirmed=0` — unpublished until the operator confirms; CLAUDE.md escalation 3). Also check rhetoric-vs-action. See `/deep-check` for the deeper fan-out. **Pēc medību pabeigšanas — arī pie 0 atradumiem — pieraksti izpildes pēdu** (`store_contradiction` raksta tikai atradumus; bez šīs rindas godīgā nulle nav atšķirama no „netika palaists", un `_check_contradictions` ziņos `missing`):

   **Tvērums no datiem (kopš 2026-10-15, audits `docs/audits/2026-10-15-pretrunu-parklajums/`).** Pirms medībām:
   ```bash
   .venv/Scripts/python.exe -c "from src.db import get_db; from src.briefs import current_routine_day; from src.routine import hunt_scope; print(hunt_scope(get_db(), current_routine_day()))"
   ```
   `voter_ids` sadali grupās pa ≤5 un dispatchē ⌈balsotāji/5⌉ `@contradiction-hunter` paralēli, katram SKAIDRU pid sarakstu ar viņu dienas claim id — nekad «aktīvākos» (tā 30 d palika nepārbaudīti 13 balsotāji). Cena ≈ 39k Opus tokenu uz politiķi (~600k dienā pie ~16 balsotājiem). Pēdu raksti TIKAI tā:
   ```bash
   .venv/Scripts/python.exe -c "from src.routine import log_hunt_trace; log_hunt_trace(claim_ids=[...], politician_ids=[...], found=<M>, rejected_candidates=[...])"
   ```
   `claim_ids` = pozīcijas, kurām izpildīta embedding pāreja (ekstrakcijas aģenti); `politician_ids` = balsotāji, kuriem hunter izpildīja strukturālo pāreju. `date` NERAKSTI ar roku — to liek `current_routine_day()` (ar roku rakstīts datums pēc pusnakts iezīmē nākamo dienu kā izpildītu). `print_routine` rāda «pozīcijas N/M, balsotāji K/L»; `partial` = vēl jāpārbauda nosauktie balsotāji. Ārpus rutīnas medības: `day='<darbs>-YYYY-MM-DD'`.

   **`rejected_candidates` nav neobligāts (kopš 2026-09-04, operatora lūgums).** Bez tā kandidāti, ko aģents izvērtēja un noraidīja, dzīvo tikai apakšaģenta atskaitē, kas pazūd līdz ar sesiju. Operators tos lasa `serve.py` panelī «Pretrunu kandidāti» un reizēm izlemj kādu publicēt. Lauku līgums un piemērs: [`.claude/agents/contradiction-hunter.md`](../agents/contradiction-hunter.md) § Step 5 — `claim_new` un `why` ir obligāti, pārējie papildinājumi; atslēgu nosaukumus nemaina (vārts: `tests/test_dashboard_candidates.py`).
4. **Devils-advocate** — already done inside step 3 (verify-then-store). Here only rows `print_routine` still shows as unreviewed (stored without `reviewed=True`, e.g. by hand) go through `@devils-advocate`.
5. **Spriedzes** — first run `.venv/Scripts/python.exe scripts/saites_proposals.py --days 1` (TypeSafe pass; writes only `tension_proposals` + `tension_judged`). Review each pending proposal against its source document: real link → `scripts/saites_accept.py <id> --topic "<kanoniskā tēma>" --description "<latviski, bez #NN>" [--type spriedze|uzbrukums|atbalsts]`; not a link → `scripts/saites_accept.py <id> --reject`. The model's `relation` is a hint only — `spriedze` vs `uzbrukums` is your call. Then register any further tensions you find as before (≥2 politicians with new positions). The routine reporter shows pending proposals in the Spriedzes line.
6. **Konteksta piezīmes (tendences)** — append-only; check existing notes first, never overwrite (destroys the evolution signal). **Piezīmes teksts iziet B formu** (≤120 vārdi, 4+ nosaukti aktieri sarakstā, ne semikolu virtenē) — tā nonāk pārskatā verbatim kā `<div class="context-box">`, tāpēc gara virtene šeit kļūst par palagu publiskajā lapā. Sk. [`brief-shared-rules.md`](../../wiki/operations/agenti/brief-shared-rules.md) § Prozas bloku forma.
7. **Dienas pārskats** — `@brief-writer`. **Tikai pēc dienas pēdējās (vakara) ielādes un tās analīzes** (operatora lēmums 2026-09-07): pēcpusdienas skrējiens apstājas pēc 3. soļa, 5.–7. soli dara vakarā, kad 1.–3. solis atkārtots jaunajiem dokumentiem. **Saeimas sēdes dienā vispirms `/saeima-ingest`** — pārskats balstās pirmavotā, un pretrunu strukturālā pāreja (T9) redz dienas balsojumus. Same-day refresh = **UPDATE the existing `daily_brief` row, never a full rewrite** (`feedback_daily_brief_update_not_rewrite`); check `context_notes` first. **Re-saving an EARLIER day's brief is not free:** a backdated claim counts in one day only, and `_BRIEF_DAY_CLAIM_SQL` (`src/briefs.py`) drops it from today's brief once its `stated_at` day has a brief written or refreshed AFTER the claim's `created_at` — so re-saving yesterday's brief silently removes such claims from today's.
8. **Featured image** — `@graphics-designer` once the brief is approved.
9. **Wiki sync** — `wiki_sync()`; never hand-edit generated wiki pages.

## LV-style guardrails (every claim / brief / synthesis / tweet)

Avoid anglicisms and check grammar + stylistics before store/publish (`feedback_check_grammar_stylistics`): never "ataka" (→ uzbrukums), "polemika" (→ diskusija/domstarpības), "melīšana" (→ melošana). Diacritics intact.

## Publish gate (HARD — do NOT auto-publish)

Before any deploy of a brief: **manual proofread** the full text (verb forms, sg/pl, truncations, capitalization — `lint_lv_style` 0-issues is NOT sufficient — run `@quality-reviewer` § H «Valoda un lasāmība» and quote its table with the denominator; that section is the proofread artefact, not the orchestrator's memory), confirm the featured image, then **AskUserQuestion** for go-ahead. Never auto-publish.

## Quality gate (HARD — before render, not after)

Run `bash scripts/check.sh`, then dispatch **`@quality-reviewer`** over the day's output. CLAUDE.md § Quality Bars names both as the render+deploy carrier and calls the reviewer a hard gate: it is the last check on data integrity, source links, completeness and neutrality before anything reaches the public site. A green `check.sh` alone does not clear this step — it validates the build, not the editorial content.

**`check.sh` palaid tikai tad, kad neviens DB rakstošs aģents (`@graphics-designer`, ekstrakcija, `@brief-writer`) vairs nestrādā.** Testu ražošanas-DB sargs (`tests/conftest.py`) salīdzina tabulu skaitus pirms un pēc testa; paralēls aģenta ieraksts izskatās pēc testa noplūdes un nokauj testus. `@quality-reviewer` tikai lasa — to drīkst laist paralēli.

**If the routine wraps up after 05:00 LV, or you review an earlier day, tell the reviewer which day it is reviewing.** Its first code block binds `ROUTINE_DAY = current_routine_day()` (05:00 LV boundary) and every check keys off it, so a run between 00:00 and 05:00 already reviews the right day. The default is wrong only when the routine wraps up after 05:00 or you review an earlier day — then pass `ROUTINE_DAY` explicitly. Say the covered date explicitly in the dispatch (`ROUTINE_DAY = '2026-08-14'`), the same way `check_routine(target_date)` takes it. Two related behaviours, both deliberate: the reviewer resolves the brief through `src.routine._daily_briefs_for()` (subject date, not `created_at`), and a **missing brief is now a FAIL, not a silent pass** — if it reports "pārskats nav atrasts" on a day you did run the routine, the day you passed it is wrong, not the brief.

## Render + deploy

- **Pēc korektūras un operatora atļaujas — vispirms ieraksti publicēšanas karogu, tikai tad renderē:** `.venv/Scripts/python.exe scripts/approve_publish.py <YYYY-MM-DD>` (nedēļas pārskatam `nedela-<YYYY-MM-DD>`). Kopš 2026-08-18 deploy preflight prasa `publish_approvals` rindu KATRAI `blog/` pārskata lapai — attēla apstiprinājums vairs nav pietiekams, jo tas pierāda tikai hero izvēli, ne to, ka teksts drīkst iet ārā. Kopš 2026-10-26 renders pārskatu bez rindas izlaiž pavisam — kokā nav ne lapas, ne attēlu, ne ieraksta sarakstos un sitemap (`src.briefs.is_brief_published`), un deploy iziet veiksmīgi, tikai bez šī pārskata. Preflight ir otrā aizsardzība: tas bloķē lapu bez apstiprināta attēla (`brief_images.approved`) vai ar saturu, kas mainīts pēc apstiprināšanas. Renderētā HTML korektūrai pirms atļaujas: `.venv/Scripts/python.exe -m src.render --only=blog,dashboard,static --drafts --output=.scratch/drafts` (šo koku nekad nedeployē; [deploy.md](../../wiki/operations/deploy.md)). Atsaukšana: `--revoke`. Atļauja der vienam publicējumam un attiecas uz saturu: labojums pēc apstiprināšanas → apstiprini vēlreiz; citādi deploy preflight atsaka (`saturs mainījies pēc apstiprināšanas`).
- Identify the changed domains and render narrowly: `.venv/Scripts/python.exe -m src.render --only=DOMAIN1,DOMAIN2` (full path only for release/baseline regen — `feedback_render_narrow_scope`). **After approving the featured image, the render MUST include `dashboard`** — the landing page and `analizes.html` listing cards live in that domain, so a `blog`-only re-render publishes a brief whose image shows only on the brief page itself. **Always include `static`** — `about.html`'s corpus figures and `sitemap.xml` are emitted by that domain alone, so omitting it silently publishes stale counts and a sitemap missing the day's brief (~5s).
- **Attēla variantu vārti (quality-bars § Dienas pārskats — „varianti eksistē un live atgriež HTTP 200").** `src/graphics/cli.py` variantu ģenerēšanas kļūmi apzināti norij (`# never block approval on variant gen`), tāpēc vienīgais nesējs ir šis solis. Divi mērījumi, abi ar saucēju.

  **(a) Pirms deploy — vai visi četri varianti ir uz diska?** `_ensure_image_variants()` tos ģenerē rendera laikā, tāpēc palaid to PĒC narrow rendera:

  ```bash
  .venv/Scripts/python.exe -c "
  from pathlib import Path
  from src.image_variants import VARIANTS, variant_filename
  DAY = '2026-09-05'   # rutīnas diena, ne kalendārā
  # Pamata PNG dzīvo ārpus deploy saknes (output/images/briefs); renders uz
  # output/atmina/images/briefs kopē TIKAI variantus — PNG glob deploy kokā
  # deva 0 un nokāva vārtu (2026-09-06), tāpēc PNG meklē avota mapē.
  src = Path('output/images/briefs')
  out = Path('output/atmina/images/briefs')
  pngs = sorted(p for p in src.glob(f'{DAY}*.png'))
  print(f'pamata PNG: {len(pngs)}')
  assert pngs, 'nav neviena PNG — attēls nav ģenerēts vai diena nepareiza'
  missing = [variant_filename(p.name, v) for p in pngs for v in VARIANTS
             if not (out / variant_filename(p.name, v)).exists()]
  print(f'attēlu varianti: pārbaudīti {len(pngs) * len(VARIANTS)}, trūkst {len(missing)}')
  assert not missing, missing
  "
  ```

  Trūkstošs variants = pārskatam nav publicēšanas apstiprinājuma rindas (renders pārskatu un tā attēlus kokā neliek — vispirms `approve_publish.py`), renders nav pieskāries `blog`/`dashboard` domēnam vai `--note-id` palaists ārpus rendera. Pārrenderē, nekopē failus ar roku.

  **(b) Pēc deploy — vai live atbild 200?** `curl -I` katram hero + og + card + thumb URL; jebkas cits par 200 ir 404-hero klase:

  ```bash
  DAY=2026-09-05   # rutīnas diena, ne kalendārā
  B=output/atmina/images/briefs
  for f in $B/$DAY*-hero.webp $B/$DAY*-og.jpg $B/$DAY*-card.webp $B/$DAY*-thumb.webp; do
    u="https://atmina.lv/images/briefs/$(basename "$f")"
    code=$(curl -s -o /dev/null -w '%{http_code}' -I "$u")
    echo "$code  $u"
  done
  ```

  Ziņo SKAITU, ne tikai atradumu: „pārbaudīti N URL, 200: N, cits: 0". Denominators 0 vai 1 nozīmē, ka vārti ir salauzti, nevis ka viss ir tīrs (CLAUDE.md § „A gate that cannot fail is not evidence").
- Deploy with **`bash scripts/deploy.sh --no-delete`** (Cloudflare: ALWAYS the full local tree; `--no-delete` is an accepted no-op kept for consistency. A narrow render leaves other domains' pages in the tree from the previous build, so the tree stays complete — never delete from `output/atmina/` by hand before a deploy). After deploy: `.venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv` → expect visas zaļas (`N/N`). A real deploy writes `logs.action='deploy'` (version id), so routine step «11. Deploy» turns ✓; `missing`/`stale` there = the approved brief is not live yet. Dry-run first: `deploy.sh --dry-run --no-delete`.
- **New EXTERNAL resource host → CSP allowlist, or it dies silently on the live site.** The live `script-src` has no `'unsafe-inline'`, and every external host (script, style, font, image, `connect`) must be added to the allowlist in `assets/_headers`. Local preview serves no headers, so it **cannot** catch this — the resource simply fails in the browser after deploy, with no build error and no test failure. Two tests cover the source side: `tests/test_no_inline_js.py` (inline-JS half, all 36 templates + curated pages) and `tests/test_csp_external_hosts.py` (external-host half — also scans `curated/` and the vendored `assets/cuelume/`). Neither can verify the LIVE headers or a host that only appears at runtime, which is why the manual confirmation below stays in this checklist. If today's render touched a template, a curated page or `assets/*`, confirm no new external host appeared before deploying, and verify it live after (CLAUDE.md § No inline JavaScript).
