# atmina — CHANGELOG arhīvs (2026-04 — 2026-05)

Vēsturiskie ieraksti, atšķelti no `CHANGELOG.md` 2026-07-21 (fails bija 180 KB).
Enkuri saglabāti identiski; aktuālajā `CHANGELOG.md` atsauktajiem ierakstiem ir
enkuru-stubi ar norādi šurp. Jauni ieraksti VIENMĒR iet `CHANGELOG.md` — šis
fails aug tikai ar nākamajām atšķelšanām.

---

## 2026-05-29 — Render hang fix (`claims.document_id` indekss) + `check.sh` vārtu atjaunošana + `--only` CLI

**TL;DR:** Pilns `generate_public_site()` iekārās ~16 min (CPU pegged, 0 disk write) pēc P3 backfill. Cēlonis: `render_news._fetch_news` izpilda `WHERE document_id=?` reizi uz katru ziņu (2594×), bet `claims` tabulai trūka indeksa uz `document_id` — katrs lookup full-scan pār 514k rindām (~376 ms). Pievienots `idx_claims_document_id` → lookup 376ms→0,07ms, `_fetch_news` 16min→0,5s, pilns render **169 s**. Tajā pašā sesijā pievienots `--only` narrow-render CLI un atjaunoti `bash scripts/check.sh` vārti (bija sarkani ~mēnesi, 24 pre-existing failures).

**Izmaiņas:**
- **`idx_claims_document_id`** (`f8cf80d`) — pievienots `src/schema.sql` + live DB. Backfill izaudzēja `claims` līdz 514k rindām, kas pārvērta nesaindeksētu per-dokumenta lookup par 16 min hangu.
- **`--only`/`--list-domains` narrow-render CLI** (`9827580`) — `python -m src.render --only=DOMAIN1,DOMAIN2` renderē apakškopu (~10-30 s) pilnā ~12 min vietā. `KNOWN_DOMAINS` (17 domēni) gate caur `_want()`.
- **Orphaned claims indeksu sync** (`57a10ef`) — `idx_claims_claim_type` + `idx_claims_opp_type_topic` bija tikai live DB (nevienā koda ceļā); deklarēti `schema.sql` + regenerēts `schema-dump-pre-f2.sql` baseline.
- **preflight DB-path fix** (`3122149`) — `preflight_check()` noklusējums `politracker.db`→`DB_PATH` (`data/atmina.db`); agrāk `init_db()` radīja un validēja nepareizo (legacy) DB, nekad neapskatot reālo.
- **Vārtu atjaunošana (24 pre-existing failures):** char baselines regen pēc P3 data drift (`8febf72`), x_mentions env-hermeticity (`7556df7`), dashboard `KeyError: -1` uz `approved=-1` "superseded" image rindām (`994face`), schema-dump baseline (`57a10ef`), Windows teardown flake (`d51f100`). `check.sh` tagad zaļš (ruff + pytest 0 failed + render smoke).

**Atvērtais:** char baseline testi hash live-DB output → atkārtoti lūst pēc katra ingest (data-drift treadmill); rework uz mazu fixture DB ieteicams. `render_links` (46 s) + `render_politicians` (60 s) vote-alignment self-joini ir lēnākie posmi — cache/precompute kandidāti, ja pilna render laiks sāk sāpēt. Sk. memory `project_render_narrow_cli`.

---

## 2026-05-28 — balsojumi.html virtualizācija (367 MB → 142 KB br)

**TL;DR:** Balsojumu matrica pārveidota no servera-renderētas HTML uz JS-renderētu kompaktu JSON (`data/balsojumi-matrica.json` + pre-kompresēti `.br`/`.gz` sibling faili) ar lazy init + pagināciju. Transfers 367 MB → 142 KB br (~2700×). Procedurālie balsojumi pēc noklusējuma paslēpti no matricas.

**Izmaiņas:**
- Matrix JSON emitter (`80cd9f1`) + pre-kompresēti `.br`/`.gz` siblings (`da3da9d`)
- JS-renderēta matrica + vote-list paginācija, `assets/bmv1.js` (`5b163a3`)
- Filter dropdowns godā SSR pagināciju (`8884730`)
- Targeted balsojumi-only render skripts (~15 s) (`dbcfca9`)
- Procedurālie Saeimas balsojumi paslēpti no matricas pēc noklusējuma (`80ccdf2`)

Step 3 (column virtualization + TAB 1 lazy popover) atlikts.

---

## 2026-05-27 — P3: pilns 14. Saeimas balsojumu backfill (~511k `saeima_vote` claims)

**TL;DR:** Backfillēts viss 14. Saeimas balsojumu vēsturiskums (2022-11 → 2026-05): **5703 balsojumi / 506 963 individuālie balsojumi (100 % match) / ~511k `saeima_vote` claims**. Pievienoti 19 deputāti (pid 205-223). Šī datu izaugsme ir cēlonis vairākiem render/perf regresiem, kas risināti 2026-05-29.

**Izmaiņas:**
- P3 Phase 0+1: ST/ST! faction codes + sentinel stance fallback (`7107996`)
- Phase 2 scalable year backfill — embedded Playwright + JS extraction (`92a55ca`), pēc tam pure-urllib (Playwright dependency likvidēta) (`9887cb7`)
- `saeima_vote` claim_type atbrīvots no inactive guard + 9 historic deputāti (`ae6f023`); wave-2 deputāti + swap-name matcher fix (`de09ea4`)
- Surname-collision attribution + ghost-claim cleanup (`3422b8c`); Zelderis partijas korekcija — Progresīvie, ne Apvienotais saraksts (`c4e204a`)

**NB:** `saeima_vote` claims glabā `document_id = NULL` (provenance caur `saeima_individual_votes`, kas tagad 507k rindas) — sk. 2026-05-29 indeksa fix.

---

## 2026-05-26 — P2: Vitenberga 2020-2022 retrofetch *(ieraksts pārcelts no operacijas.md 2026-07-17)*

Klimata ministra kandidāts (pid=139) — 25.05 "klimata mērķi jāiepauzē" motivēja pirms-tracking substrāta retrofetch: 14 doc (TVNet+LSM, 2020-04→2022-05, EM tenūra Kariņa I valdībā), **9 first-party position claims #22981-22989** saglabāti. Hunter atrada 2 minor_shift kandidātus (#22986 vēja parku atbalsts JV 2022 vs #20850 "iepauzēt klimatu" 2026); `@devils-advocate` REJECT visiem — paywalled tvnet.lv lede (33 vārdi), stance overreach, FP6+FP7 (Krievijas iebrukums 2 d. pēc #22986 + EM→KEM lomas šifts). 9 claims paliek kā profila substrāts atkārtotai pārbaudei. Skripts: `scripts/retrofetch_vitenbergs_2020_2022.py`. 0 publicējamu pretrunu — vēl viens ~1/2700 ROI datu punkts.

---

## 2026-05-17 — atmina ops dashboard M2 (Phase 2 — interactivity)

**TL;DR:** Operators tagad var apstiprināt/noraidīt brief imageus, force-refreshot X cookie slot health, palaist deploy ar konfirmācijas modal, un piekļūt visam ar klaviatūru — bez Claude Code sesijas. Visi 3 darbības atvers HTMX-swapped panel updates + toast paziņojumus. Build par `feat/operator-dashboard-m2` (5 commits + this doc commit).

**M2 scope (Phase 2, 5 tasks):**

1. **HTMX action infrastructure + toast system** — `views/_actions.py` exposes `action_response(panel_html, toast_level, toast_message)` which builds Flask response combining panel HTML with `HX-Trigger: {"showToast": {...}}`. `ops.js` listens for `showToast` HTMX events and injects toasts into `#toast-container`. Success/info auto-dismiss 3 s; warning/danger require click. Defense-in-depth: message uses `textContent`, not `innerHTML`.

2. **Image approve/reject** — `POST /api/image/<id>/approve` and `/reject` call existing `src.graphics.storage.approve_image/reject_image`. Approve refuses already-approved (400, surfaced explicitly so silent button-mashing doesn't look "successful"). Reject requires non-empty `reason` (saved into `brief_images.error_message` for future `@graphics-designer` prompt tuning). UI: pending images get inline Alpine.js reject modal with required reason textarea.

3. **Slot probe force-refresh** — `POST /api/slots/refresh` calls `get_slot_snapshot(force=True)` bypassing 60 s cache. Header gets `↻ Pārbaudīt [R]` button + `htmx-indicator` showing "probē…" during ~8 s probe. Toast level escalates to warning when refresh shows guardrail tripped — forced re-look shouldn't whisper "healthy" over a 3/6 reality.

4. **Deploy trigger with confirm modal** — `GET /api/deploy/confirm` renders modal with last-deploy timestamp + status (or "pirmais log entry" copy when empty). `POST /api/deploy` runs `subprocess.run(['bash','scripts/deploy.sh'], timeout=300, capture_output=True)`. Three outcome branches feed three toast levels: success (log_action stdout tail), non-zero exit (log_action failed with stderr tail; toast `exit N: <tail>`), timeout (`Deploy timeout (300s)`). Endpoint always 200 — failures surface in toast. Footer gets `🚀 Deploy [D]` button.

5. **Keyboard shortcuts + help modal** — `?` opens help modal with shortcut table (`?` A R D Esc). Elements opt in by setting `data-shortcut="K"`; `ops.js` keydown dispatcher matches keystroke + clicks the element. Guards: skip when focus in INPUT/TEXTAREA/SELECT/contentEditable, skip when Ctrl/Meta/Alt held (so `Ctrl+R` still reloads). Header `?` button is both the click surface AND the keystroke target.

**Saistītās ārpus-`src/dashboard/` izmaiņas:** nav. Visa M2 strādā ar M1 atstātajām pipieliem (`src.graphics.storage`, `src.db.log_action`, `src.dashboard.views.slots.probe_all_slots`).

**Verifikācija:**
- 114/114 tests green (5 jauni testu faili: actions/deploy/keyboard, plus 11 jauni cases brief/slot suites)
- `ruff check src/dashboard/` clean
- Manuālā browser smoke uz operatora

**Commit range:**
```
c187b3e  feat(dashboard): HTMX action infrastructure + toast system
167cb55  feat(dashboard): image approve/reject actions
1edb45d  feat(dashboard): slot probe force-refresh action
c65db56  feat(dashboard): deploy trigger with confirm modal + log_action
7c5714f  feat(dashboard): keyboard shortcuts + help modal (M2 SHIP GATE)
<this>   docs(dashboard): CHANGELOG + atmina-ops.md keyboard + actions section for M2
```

**Phase 3 (M3) — optional polish:** per-panel tooltips, empty-state illustrations, settings page, first-visit tour, SSE for live activity. Not blocking — M2 is the operator-ready milestone.

---

## 2026-05-17 — atmina ops dashboard M1 (Phase 1 complete)

**TL;DR:** Pirmais lokālais operatora dashboard — Flask + HTMX + Tailwind + Alpine, palaižams ar `python serve.py` uz `http://127.0.0.1:8080`. 5 paneliišas (brief / rutīna / X cookie pool / X_MENTIONS A/B / ekstrakcijas backlog) + aktivitātes timeline + pending banner + footer ar image budget. Bez auth, bind cietkods uz `127.0.0.1`. Pilns plan + design spec `docs/superpowers/{plans,specs}/2026-05-16-operator-dashboard*.md`. Runbook: [`wiki/operations/atmina-ops.md`](operations/atmina-ops.md).

**M1 scope (Phase 1, 9 tasks):**

1. Scaffolding + design system + theme toggle (auto/light/dark ar localStorage)
2. Šodienas brief panel — 4 stāvokļi (active/empty/loading/error); image approval badge cycle 0/1/2
3. Rutīna panel + `check_routine()` paplašināts ar `'waiting'` statusu pirms 15:00 LV (vairs nav false-alarm "missing brief" rītā)
4. X cookie pool — 6 cards × 4 endpoints, 60s cache, guardrail surfacing
5. A/B stratēģija — `X_MENTIONS_STRATEGY` env reading, 7-run SVG bar chart, 24h guardrail trip count
6. Ekstrakcijas backlog — per-platform un top-5 politicians, 30s cache
7. Aktivitātes timeline — UNION 4 avoti (logs + brief_images + context_notes + analyses), LV relatīvais laiks, HTMX 30s polling
8. Pending banner + footer + index composition — sticky-top banner ar Alpine sessionStorage dismissal; footer ar image budget bar + git SHA
9. Wiki + CHANGELOG + CLAUDE.md integrācija (šis ieraksts)

**Saistītie kodu izmaiņas ārpus `src/dashboard/`:**
- `src/routine.py` — `check_routine(now=...)` paplašināts ar morning-window logic; `'waiting'` status izstrādāts `analysis`/`daily_brief` soļiem pirms 15:00 LV; `print_routine` `status_icons` papildināts ar `⏳` (Task 1.3).
- `src/x_mentions.py` — guardrail trip tagad raksta `log_action("mentions_fetch_guardrail", ...)` alongside `logger.warning` (Task 1.5). Vēsturiskās trips nav backfillētas — tikai jaunās skaitās.

**Tehnoloģiju izvēle (no design spec):**
- Flask 3.x + Jinja2 (jau izmantots `src/render/`)
- HTMX 1.9 + Alpine.js 3 — partial-update + tiny client state, bez React/build pipeline
- Tailwind CSS 3 via CDN — design tokens + dark mode bez build step
- Charts: inline SVG (no JS lib), Lucide ikonas + emoji glyphs

**Verifikācija:**
- 79 testi (9 testu faili: scaffold + brief + routine × 2 + slots + strategy + backlog + activity + pending)
- `ruff check src/dashboard/` clean
- Real-DB smoke katram task'am pirms commit — viens bug noķerts (lede ekstrakcija sajauca bullets, kas in-memory fixture izlaida)

**Commit range:**
```
a2082a0  feat(dashboard): scaffold serve.py + design system + theme toggle
db18f7d  feat(dashboard): brief panel with 4 explicit states
160333e  feat(routine): morning-window awareness in check_routine + dashboard panel
9770153  feat(dashboard): slot/strategy/backlog panels (Tasks 1.4+1.5+1.6)
7a59a71  feat(dashboard): activity timeline with 30s auto-refresh + LV relative time
3927241  feat(dashboard): pending banner + footer + index composition
<this>   docs(dashboard): runbook + wiki/CLAUDE/CHANGELOG integration for M1
```

**Phase 2 (M2) — nākamais:** image approve/reject UI darbības, slot probe force-refresh, deploy ar confirm modal, keyboard shortcuts. Plāna Phase 2 (5 task'i).

**Kad pārskatīt:** ja `data/atmina.db` schema kādu kolonnu pārvieto (pārmaina `reviewed_at`, `approved`, `created_at` semantiku), Backlog vai Brief view'iem var būt jāatjaunina kolonnu nosaukumi. Tests pret in-memory fixtures `init_db()` izsauks, tāpēc lielas schema izmaiņas pieprasīs sinhronu test refresh.

---

## 2026-05-16 — Step 3.5 regress + trīslīmeņu fix (`@saeima-tracker`)

**TL;DR:** 07.05 + 14.05 sesijās 21 `saeima_votes` rindai trūka `summary` lauks, jo `@saeima-tracker` dispatches izlaida Step 3.5 (bill teksta lasīšana + 1-2 teikumu LV summary uzrakstīšana). Pirms 30.04 100 % balsojumiem bija saturīgs summary; pēc — generic motif fallback, kas claim stance laukā parādījās kā "Balsoja PAR: <motif>" 1943 deputātu claims vietā "Atbalsta/Iebilst pret/Atturējās balsojumā par: <substance>".

**Cēlonis:** Step 3.5 prompt-design defekts. `.5` suffix + ievada teikums "if the vote references a bill" signalizēja par "papildu/neobligātu" soli starp Step 3 (capture) un Step 4 (parse + store). Konteksta spiediena dēļ (~90 deputāti × 15-17 votes per sesija) agenti instinktīvi izlaida šo "papildu" soli un pārlēca tieši uz Step 4 → Step 5, kurā `process_vote_snapshot()` tūlīt izsauca `generate_claims_from_votes()` ar `summary IS NULL`.

**Trīslīmeņu fix (CLAUDE.md untouched — disciplīna dzīvo `wiki/operations/agenti/` + canonical promptā + kodā):**

1. **Kods — Layer-1 signāls** (`src/saeima/votes.py`):
   - `store_vote()` pieņem keyword-only `summary`, `document_url`, `document_nr` parametrus un saglabā tos atomic INSERT'ā (likvidē senāko NULL→UPDATE pattern).
   - `process_vote_snapshot()` tos pārsūta tālāk uz `store_vote()`.
   - `generate_claims_from_votes()` papildināts ar Layer-1 detection: ja `summary IS NULL` un motif sakrīt ar `\(\d+/L[pm]14\)` regex (bill-like), `logs` tabulā tiek rakstīta `action='saeima_summary_missing'` warning rinda. Mēs neatturam izsaukumu (image-only PDFs leģitīmi nesnijdz machine-readable summary; hard block iesprostotu agentu); mēs **signalizējam audit trail**, ko Step 5 verification gate uztver.

2. **Prompt — Layer-2 strukturāla disciplīna** (`.claude/agents/saeima-tracker.md`):
   - Step 3.5 izšķīdināts. Step 3 = atomic 3A→3B→3C bloks katram balsojumam: capture → write summary → call `process_vote_snapshot(summary=..., document_url=..., document_nr=...)`.
   - Aizliedz batching ("ne ievāc visus snapshots, tad raksti visus summaries" — tas ir tieši regresa pattern).
   - Jauns Step 5: galīgais verifikācijas gate ar SQL query `SELECT id, motif FROM saeima_votes WHERE date(created_at)=date('now','+3 hours') AND summary IS NULL AND (motif LIKE '%/Lp14)%' OR motif LIKE '%/Lm14)%')`. Ja jebkura rinda atgriežas, `raise SystemExit(1)` — agents neatskaitas operatoram līdz fix.

3. **Wiki — Layer-3 audit trail** (`wiki/operations/agenti/saeima-tracker.md`):
   - "NEdrīkst" sadaļā pievienots bullet par 2026-05-16 regresu ar atsauci uz šo CHANGELOG ierakstu.

**Backfill rezultāts (DB pirms fix piemērošanas):**
- 21 `saeima_votes.summary` aizpildīti (4 caur SQL copy no `saeima_bills.summary`, 15 via `@saeima-tracker` Step 3.5 batch, 2 manuāli par 1286/Lp14 priekšlikumu Nr.1 valodas amendment).
- 12 `saeima_bills.summary` atjaunināti.
- 1943 `claims.stance` pārģenerēti generic→saturīgais formātā, plus 453 pēc post-review LV gramatikas labojumiem (5 summaries — vote 195 lasījuma kļūda 2.→3., 2 anglicismi "amendment", 2 stilistiski).

**Saistītie:**
- Commit šī fix: `<TBD>` (kods + prompt + wiki + CHANGELOG vienā commit)
- Backfill commit: `67076a0 data(saeima): 14.05 sesijas backfill — 2 jauni balsojumi + 21 summary regen`
- Vote 197 — Butāna/Vitenberga (NA) valodas politikas priekšlikums Nr.1 (1286/Lp14), noraidīts 23-22-37 (klātesošo vairākuma noteikums); citējams kā NA stratēģijas piemērs: valodas amendmenta iebakšana militāras tehnikas grozījumu likumprojektā.

**Kad pārskatīt:** Ja `logs.action='saeima_summary_missing'` ieraksti turpina parādīties pēc 2026-05-16 fix piemērošanas — pārbaudīt, vai canonical prompt nav atgriezies pirmsregress formā, un vai kāds skripts neapiet `process_vote_snapshot()` (tieši `store_vote()` izsaukums bez `summary=` kwarg ir leģitīms tikai backfill kontekstā).

---

## 2026-05-08 — twikit Patch 5: ondemand.s.js two-stage parser (real TID restored)

**TL;DR:** 2026-04-29 diagnoze ("X izņēma `ondemand.s` referenci") bija nepareiza. Live verifikācija 2026-05-08 apstiprināja: X **mainīja formātu**, nevis to noņēma. Upstream `d60/twikit#410` PR (publicēts 2026-03-18) dokumentē divposmu lookup, ko atmina pielietoja kā Patch 5.

**Formāta izmaiņa:**
- Vecais (twikit 2.3.3 regex): `"ondemand.s":"<hash>"` — single-stage, vairs nesakrīt.
- Jaunais: `,<idx>:"ondemand.s"` ... `,<idx>:"<hash>"` — divposmu lookup pa numerisko indeksu.

**Patch 5 izmaiņas (`scripts/patch_twikit.py`):**
- `ON_DEMAND_FILE_REGEX` → `,(\d+):["']ondemand\.s["']`
- Jauns `ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'` otrā posma hash lookup-am.
- `INDICES_REGEX = r"\[(\d+)\],\s*16"` (vienkāršots, captures group 1).
- `get_indices()` pārrakstīts kā divposmu parse (find index → resolve hash → fetch ondemand.s.<hash>a.js).
- Patch 4 try/except wrap saglabāts kā safety net — ja regex atkal driftē, fallback uz stub TID joprojām strādā.

**Verificēts 2026-05-08:**
- 5/5 cookie slot-i ražo reālu TID (key no twitter-site-verification meta, indices=[2,31,16], row=16). Bez stub.
- `UserTweets`, `SearchTimeline`, `UserTweetsAndReplies` (Replies tab) — visi 3 endpoint-i strādā.
- `SearchTimeline` atgrieza 10 LV-political rezultātus uz "Saeima" query (kopš 2026-04-29 atgriezas tikai 404 ar stub TID).
- `Replies` endpoint atgrieza 19 ierakstus @edgarsrinkevics.

**Sekas:**
- `@mentions-monitor` 3rd-party mention coverage atjaunota (sk. memory `project_x_mentions_timeline_scan.md` — workaround joprojām kodā kā fallback).
- `fetch_user_replies()` darbojas atkal — `_replies_broken_slots` tagad paliek tukšs.
- Plan `docs/superpowers/plans/2026-05-04-x-tid-generator.md` (NOT IMPLEMENTED) → marķēts `RESOLVED 2026-05-08` (problēma atrisināta upstream, ne ar mūsu reverse-engineering).

**Kad pārskatīt:** Ja `client.client_transaction.key == "AAAA..."` pēc request-a, X atkal kaut ko mainījis. Palaid `python scripts/patch_twikit.py --refresh`; ja regex driftējis, atjauno `ON_DEMAND_FILE_REGEX` un `ON_DEMAND_HASH_PATTERN` patch_twikit.py.

**Saistītie:** commit `9d5a26a`, `wiki/operations/twikit-notes.md § 2026-05-08`, `src/x_scraper.py:fetch_user_replies` docstring update.

---

## 2026-05-05 — VAD Phase 2: 5 papildu homonīmu sanācija

Audita gaitā ar jauno `scripts/audit_vad_family_clusters.py` skriptu atklāti 5
papildu pidi ar disjoint immediate-family klasteriem starp paralēlām
deklarācijām — pierādījums, ka Phase 1.5 whitelist bija par plašs un
iekļāva institūcijas, kas pieder homonīmiem (citiem cilvēkiem ar to pašu
vārdu+uzvārdu):

- pid 101 Inese Kalniņa: 37 → 5 dekl (Saeima only; LNA + Tiesu adm = 2 atšķirīgi homonīmi)
- pid 104 Līga Kļaviņa: 26 → 4 dekl (Saeima only; FM valsts sekretāra vietniece = atšķirīgs cilvēks)
- pid 107 Linda Liepiņa: 16 → 11 dekl (Saeima only; KNAB Vecākais inspektors = atšķirīgs cilvēks)
- pid 116 Gatis Liepiņš: 40 → 5 dekl (Saeima only; Valsts policijas Jaunākais inspektors = atšķirīgs cilvēks)
- pid 132 Jānis Skrastiņš: 27 → 4 dekl (Saeima only; Zvērināts notārs = atšķirīgs cilvēks)

§ 2 top-15 pārrēķināts: Vucāns kāpj #1 (was #3), Kalniņa/Kļaviņa/Skrastiņš
izkrīt no top-25 pavisam. § 218 piezīmes par "paralēliem amatiem"
izdzēstas (faktoloģiski nepatiesi). § 325 metodika precizēta. § 9
sanācijas hronikā pievienots Phase 2 ieraksts.

T7 atklāja un izlaboja parsēšanas defektu — VID portāla HTML reizēm
satur identiskas `<tr>` rindas, ko parser saglabāja kā dubultas
ierakstas. `_parse_income()` tagad dedupē at parse-time. Backfilled
7 atlikušās dubultās rindas no `vad_income`.

Family-cluster audita skripts (`scripts/audit_vad_family_clusters.py`)
kļūst par turpmāku pre-publish gate. Atlikušie 13 flagged politiķi
(klasificēti `docs/audits/2026-05-05-vad-residual-clusters.md`) ir
remarriage/parsing artefakti vai vēsturiskie homonīmi, kas neietekmē
2024-25 ranking — atstāti audita ciklam.

Plāns: `docs/superpowers/plans/2026-05-05-vad-homonimu-sanacija.md`.

---

## 2026-05-03 — VAD analīzes publicēšana + sanācijas audits T1-T11

**TL;DR:** Pēc 1.5. posma sanācijas darba (2026-05-02 → 2026-05-03 rīts) lietotājs pieprasīja "pilnīgi precīzus datus" pirms VAD analīzes publicēšanas. Plāns `docs/superpowers/plans/2026-05-03-vad-analize-sanacija.md` (11 uzdevumi T1-T11) atklāja un labotā 7 datu kvalitātes kategorijas. Analīze publicēta atmina.lv/analizes/vad-2026.html ar verificētiem 1:1 sakrītošiem skaitļiem ar politiķu profila lapām.

**Galvenās sanācijas darbības:**

- **T1-T4 — 4 augstu ienākumu politiķu disambig**: Mārtiņš Daģis (JV b.1976 Saeimas dep) atšķirts no Mārtiņa Daģa (b.1988 Kustība Par! Jelgavas dome); Agnese Lāce (PRO Kult.min) NMPD homonīms izslēgts + SIF whitelist viņas pre-politiskajai karjerai; Andris Kulbergs (AS) Valsts policija izslēgts; Jānis Vucāns (ZZS, ex-Ventspils Augstskolas rektors) Madonas policija izslēgts.
- **T5 — Ienākumu dedup**: § 3 tabulā tagad unikāli `(politiķis, gads, avots, summa)` — Inese Kalniņas 3 paralēlie amati neuzpūš algu summu (265K → 184K).
- **T6 — Profila count metodika**: § 5 (uzņēmumi) un § 6 (NĪ) re-rank'ots, lai sakristu ar to, ko lietotājs redz politiķa profila lapā (unikāli grupēti tuples + iepriekšējā gada noņemtie). Brigmanis no NĪ #1 (kumulatīvi 249) izkrīt no top-15 (4 unikāli grupē 12 raw rindas).
- **T7 — 17 ārvalstu NĪ atklāti**: Brigmana Lielbritānija (Derby) 12 ieraksti kopš 2014; Zīle, Kols, Melbārde Beļģija (Brisele) — EP/NATO darba dēļ.
- **T8 — Hosams Abu Meri**: Vārda saskaņošanas modulis naīvi sadalīja (vārds = "Hosams Abu", uzvārds = "Meri") — 0 rezultāti. Manuāls labojums atjauno 15 deklarācijas. Inga Bērziņa joprojām 2 dekl (VID safety-bound 200 rindas; Vidzemes slimnīcas homonīms 368 rindu) — 2. posma uzdevums.
- **T9 — § 5b USD/GBP sadaļa**: Dombrava 8 USD paketes (Diamondback, Barrick, SM Energy) USD 105 380; Kiršteins (LPV) NVIDIA+Meta+Broadcom USD 21 283; Kulbergs Inchcape plc GBP 2 670. Variant C: vērtības glabājas oriģinālajā valūtā, nekonvertētas.
- **T10-T11 — Galīgais audit + publikācija**: Visa anglicismu tīrīšana, skaitļu sinhronizācija (§ 5/§ 6/§ 7 atjaunoti pēc T1-T8 DB), valodas precizēšana, tad publicēšana.

**Datu kopas pārmaiņas:**
- Total VAD: 2348 → **2262** (-1221 contam DELETE + 70 yest reingest + 123 šorīt T8 reingest + 4 audit politiķu reingest)
- Politiķu skaits ar dekl: 143 → **144** (Hosams pievienojas)

**Jauni skripti:**
- `scripts/seed_homonimu_disambig.py` (multi-pid curator priekš 4 audit homonīmiem)
- `scripts/audit_vad_profile_match.py` (analīze ↔ profila atbilstības gate)
- `scripts/audit_vad_foreign_re.py` (ārvalstu NĪ pārbaude)
- `scripts/compute_vad_profile_counts.py` + `rank_vad_profile_counts.py` (top-N re-rank pa profila count)
- `scripts/cleanup_contaminated_vad.py` paplašināts ar `--politician` flag

**Saistītie:** plāns `docs/superpowers/plans/2026-05-03-vad-analize-sanacija.md`, analīze `content/analizes/vad-2026.md`, atmina.lv lapa [/analizes/vad-2026.html](https://atmina.lv/analizes/vad-2026.html).

---

## 2026-05-03 — Ingmārs Līdaka matcher kļūda (pid=109 negative_patterns)

**TL;DR:** 2026-05-03 rīta claim-extractor sweep atklāja, ka pid=109 Ingmārs
Līdaka (AS Saeimas dep) bare-surname "Līdaka" name_form salinkoja rakstu par
**Gunta Līdaka** (FM/KM darbiniece) un Puntuļa tweet par citu Gunta Līdaka.
Audit: 6 junction rows total, 2 false-positive (doc_id 29378 web, 7363 tweet),
4 leģitīmi.

**Fix komponents:**
- `tracked_politicians.negative_patterns` (pid=109) = `["Gunta Līdaka", "Guntas
  Līdakas", "G. Līdaka", "G.Līdaka", "Gunta Līdakas"]`. Matcher reject'oja
  doc 29378 verifikācijā.
- 2 false-positive `document_politicians` junction rows DELETE'd.
- Reproducible curator: `scripts/seed_lidaka_disambig.py` (idempotents).

**0 claims affected** (abas false-positive doci tika empty-ekstraktētas pirms
fixa, pid=109 saglabā 143 leģitīmus claims).

**Saistītais pattern:** Tas ir tas pats matcher name-collision pattern, kas
2026-04-23 bug fixoja pid=146 Andris Bērziņš (ZZS dep vs bijušais prezidents).
Visiem politiķiem ar publiski pazīstamiem homonīmiem ārpus mūsu tracked
saraksta vajadzētu `negative_patterns` curator pass — Phase 2 backlog idea.

---

## 2026-05-02 (vakars) — VAD Phase 1.5: homonīmu cleanup + retry + Hosams override

**TL;DR:** Pēc 152-politiķu sweep (215 min, commit `8744277`) atklāja 3
deploy-blocking problēmas: (a) **homonīmu kontaminācija** 11 pidiem ar identiska
Vārds+Uzvārds (1221 dekl ar dažādu cilvēku datiem zem mūsu opponent_id —
Andris Bērziņš 228, Inese Kalniņa 205, Inga Bērziņa 184 utt.); (b) **parse-fail uz
1304 UUIDs** (VID anti-scrape mehanisms invalidates UUID nonces pēc N rapid
requests, detail returns redirect HTML bez `<table>`); (c) **Hosams Abu Meri**
naïve split dod ("Hosams Abu", "Meri") — VID search atgriež 0. Phase 1.5 worktree
`vad-phase-1.5` (PR #19) atrisina visus trīs.

**Why:** Reputational risk pirms publiska deploy — politiķa profilā par "Andris
Bērziņš" (ZZS Saeimas dep) tiktu rādītas bijušā prezidenta + Salaspils SIA
darbinieka + Smiltenes pašvaldības inspektora deklarācijas. F14 zaudētie 1304
UUIDs nozīmē 30-40% sweep coverage gap.

**Arhitektūra:**
- **A2 disambig (DB-driven)** — `tracked_politicians.keywords` JSON dabū jaunu
  `vad_disambig` lauku ar substring whitelist per pid. Filter rule: ja saraksts
  nav tukšs, row tiek pieņemts ja kāds substring (case-ins) match `r.institution`
  VAI `r.position_title`. Reuse esošo `negative_patterns` kā override-reject (pid
  146 jau ir "bijušais Valsts prezidents" u.c.). Bez hints — trust full-name
  search (pašreizējā uzvedība, droša unikāliem vārdiem). DB-driven, lai operators
  var pievienot pidus bez code release.
- **Retry on parse-fail** — `VadClient.reset_session()` jauna metode (clears
  `_session_initialized` + cookies). Orchestrator `fetch_for_politician` catches
  `ValueError("nav header table")`, calls reset → re-search → atrod fresh row pēc
  natural-key match → retry detail fetch. Max viens retry per row.
- **Name override** — `_NAME_OVERRIDES[161] = ("Hosams", "Abu Meri")`.

**Fix komponents:**
- `337f793` `src/vad/matcher.py` — Hosams override.
- `f3ceb90` `src/vad/declarations.py` — `_load_disambig_config()` + `_row_passes_disambig()`
  + filter wire-up `fetch_for_politician`. 4 jauni testi.
- `c82636b` `src/vad/fetch.py:reset_session()` + orchestrator retry. 1 fetch test +
  2 declarations testi.
- `a1f843f` `scripts/ingest_vad_declarations.py` — `Path("logs").mkdir(exist_ok=True)`
  (F15 silent crash fix).
- `a4c965a` `scripts/seed_vad_disambig.py` (curator) + `cleanup_contaminated_vad.py`
  (DELETE + targeted reingest).

**Curated hints — 11 contaminated pids** (apstiprināts Telegram msg 1584):
146 Andris Bērziņš (ZZS Saeimas dep), 101 Inese Kalniņa (JV), 144 Inga Bērziņa (JV),
104 Līga Kļaviņa (ZZS), 138 Jānis Zariņš (JV), 106 Līga Kozlovska (ZZS),
155 Dace Melbārde (NA IZM), 92 Iļja Ivanovs (Stab), 25 Viktors Valainis (ZZS Ekon.),
132 Jānis Skrastiņš (JV notārs), 107 Linda Liepiņa (LPV KNAB).

**Trade-off:** Pirms-politiska karjera ar inst='-' tiek nogriezta — neiespējami
atšķirt no homonīmiem bez gada filtra. Konkrētas pre-Saeima karjeras iekļautas
hints, ja varu droši identificēt (Kļaviņa Finanšu min, Skrastiņš notārs, Liepiņa
KNAB).

**Sweep rezultāts (post-cleanup, 2026-05-03 rīts):**
- DELETE 1221 dekl (11 pids); reingest ar disambig filter (2026-05-02 vakars +
  2026-05-03 rīts cooldown re-run) dod **193 jaunas legit dekl**: 146=31, 101=37,
  144=2, 104=26, 138=13, 106=10, 155=9, 92=5, 25=17, 132=27, 107=16. Errs=0
  (8 pids re-run 2026-05-03 ar O(n) retry hot-fix `8baf4a6`).
- Total VAD: 3376 → 2348 (–1028 net pēc contam DELETE + 193 jaunās).
- 8 commits + plan + curator scripts + CHANGELOG (šis ieraksts) + render baselines REGEN.

**Skat.:** spec § 15.2 F13/F14/F15, plan `docs/superpowers/plans/2026-05-02-vad-phase-1.5.md`,
handoff `docs/superpowers/handoff-vad-phase-1.5.md`.

---

## 2026-05-02 (vēlās dienas) — VAD `role_matches` always-True fix (production smoke)

**TL;DR:** Pēc Phase 1 land production smoke (5 sample politiķi) atklāja, ka
`src/vad/matcher.py:role_matches` per-row keyword overlap dod false-negatives
3/5 gadījumos: Šlesera DB role "LPV priekšsēdētājs" (partijas amats), Kleinberga
"Rīgas mērs" ≠ VID "Valstspilsētas domes priekšsēdētājs" (sinonīmu paši label),
Pūpola "EP deputāts" ≠ VID Rīgas dome (vēsturiskie amati). DB ir 5 homonīmu pāri
ar dažādiem PIRMAJIEM vārdiem — VID search ar full Vārds+Uzvārds atgriež TIKAI
vienu personu, role disambiguation per-row ir lieks. `role_matches` pārveidots uz
`return True` ar full rationale docstring; re-ingest 5 sample politiķiem ielādēja
17+16+15+7+2+5 = 62 deklarācijas, 0 false-negatives.

**Why:** Sākotnējais nolūks (homonīmu aizsardzība) reālā nepastāv — first-name
disambiguation pietiek. Per-row check tikai radīja regressions ar realistic
DB role label variation.

**Fix komponents (commit `986ece4`):**
- `src/vad/matcher.py:role_matches` — pārveidots uz `return True`, docstring
  dokumentē sākotnējo nolūku, empīrisko evidence un re-introduction trigger
  (ja kādreiz novērojam VID atgrieztus multiple distinct persons one search'ā).
- `tests/test_vad_matcher.py::test_role_matches_always_true` — apvieno iepriekšējos
  4 testus, asertē True priekš visu kombināciju.
- `tests/test_vad_declarations.py::test_fetch_for_politician_lenient_role_post_2026_05_02_fix`
  — vecais skip-on-Žurnālists test invertēts (skip_role=0, new=1).

---

## 2026-05-02 — VAD declarations Phase 1 (UI tab + delta render)

**TL;DR:** "Deklarācijas" tab pievienots politiķa profilā (deputy, minister, mep,
regional, former, politician profile_kinds — has_vad_data konditionāls). Tab satur
year selector (top 5 gadi), 9 sekciju akkordeoni ar delta marķieriem (jauns/
mainījies/aizgāja), ģimene zem collapsed details (etika), source link uz VID
search ar pre-filled vārdu.

**Arhitektūra:**
- `src/render/vad.py` — batch fetch ar one query per tabula (F4 leaf-vs-fan-out
  paterns). Try/except OperationalError guard test DB priekš (saeima_bills
  precedents `src/render/politicians.py:503`).
- `src/vad/diff.py` — year-over-year delta engine ar 5% threshold un identity
  keys per sekcija (skat. spec § 9.2 tabula).
- `templates/_vad_panel.html.j2` — partial, included no `politician.html.j2`.
- `assets/style.css` — `.vad-delta-{new,modified,removed,unchanged}` ar
  green/yellow/red/muted krāsām, `.vad-section` border-separated akkordeoni.
- `src/profile_kind.py` ekvivalents `_profile_tab_set` (`src/render/politicians.py:110`)
  paplašināts ar `has_vad_data` argumentu, `render_politicians()` ielādē
  `get_vad_data_for_politicians` reizē batch.

**Render performance:** Single batch query 11 tabulām × visi 152 politiķi
veikta vienu reizi pirms render loopa, ne N+1.

**Privātums:** Ģimene renderēta zem `<details>` collapsed default — saskan ar
spec § 9.5 ētisko politiku (publiska, bet nepiespiedu).

**Testi:** 33 jauni testi (3 schema + 12 parsing + 4 fetch + 12 matcher + 5
declarations + 7 diff + 5 render + 8 profile_kind_vad). Visi PASS uz
vad-deklaracijas branch.

**Sākotnējais sweep:** Operatora rokas — pēc šī Phase 1 land jāpalaiž
`scripts/ingest_vad_declarations.py` no main checkout, tad `generate_public_site()`
re-render. Mēneša rutīna sākas no nākamā mēneša.

---

## 2026-05-02 — VAD declarations tracker (Phase 0 ingest)

**TL;DR:** Jauns `src/vad/` pakete ielādē strukturēti VID amatpersonu deklarācijas
no www6.vid.gov.lv/VAD priekš 152 izsekoto politiķu. 11 jaunas `vad_*` tabulas,
manuāls CLI ingest (`scripts/ingest_vad_declarations.py`) ar mēneša cikla
noklusējumu, peak aprīlis-maijs.

**Why:** Lietotāja pieprasījums (Telegram 2026-05-02) — automatizēt deklarāciju
ielādi, lai politiķa profilā varētu rādīt strukturētu finansiālo + ģimenes profilu
ar gads-pa-gadam delta marķieriem. Daudz signāla par interešu konflikta
detektēšanu (Phase 3 backlog).

**Arhitektūra (sekojot `src/saeima/` precedentam):**
- `src/vad/schema.py` — DDL un `init_vad_tables()` (lazy, ne `init_db()`).
- `src/vad/fetch.py` — `VadClient` httpx + bounded From= loop + 10s/3s throttle (F12).
- `src/vad/parsing.py` — `parse_declaration_html()` BeautifulSoup → Pydantic.
- `src/vad/matcher.py` — name split + ASCII fallback + role disambiguation.
- `src/vad/declarations.py` — orchestrator `fetch_for_politician`.
- `scripts/ingest_vad_declarations.py` — CLI.

**11 tabulas:**
`vad_declarations` (header) + 10 sekciju tabulas (positions/real_estate/companies/
vehicles/savings/income/transactions/debts/loans_given/family). NAV `documents`
rindas (saeima 2026-04-25 invariants). NAV `claims` rindas (deklarācija ≠ retoriska
pozīcija).

**Idempotence (F11):** UNIQUE pa dabīgo atslēgu `(opponent_id, declaration_kind,
declaration_year, submitted_at, position_title)`. `vad_uuid` rotē per-call (anti-scrape
session-bound nonce; empīriski apstiprināts), tāpēc nelietojams idempotencei —
glabājas kā nullable audit lauks ar latest-seen vērtību.

**Drošības margināli:**
- Throttle: 10s starp politiķiem (F12 — sub-second back-to-back search dod ReadTimeout),
  3s starp deklarācijām → ~28 min mēneša sweep, ~48 min initial backfill.
- Bounded `From=` loop ar 200-row safety bound + log warn pie >100.
- Cookie management: explicit set/delete pa fetch_detail, NEpaļaujas uz session jar.
- Modernie ieraksti only (legacy `/VAD2002Data` Phase 0.5 backlogs).
- Role-disambiguation pret 5 homonīmu pāriem DB (Šlesers Ainārs/Ričards utt.).

**Spec un plāns:**
- Spec: `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` (commit `dda5478` ar F11+F12 amendments)
- Plāns: `docs/superpowers/plans/2026-05-02-vad-deklaracijas-plan.md`

**Sākotnējais sweep:** Tasks 17-18 plānā — mēneša rutīnas pirmā palaišana no main checkout pēc Phase 1 land.

---

## 2026-05-01 (vakars) — `og.jpg` MUST be baseline JPEG (Twitter Card render fix)

**TL;DR:** `src/image_variants.py` ģenerēja og.jpg ar `progressive=True`, kas izraisīja klusu Twitter Card render kļūmi — meta tagi pareizi, attēls 1200×630 pieejams ar HTTP 200, bet x.com preview palika tukšs. Pārkodējot uz baseline JPEG (`progressive=False`) preview ielādējās. Šī ir **nemainīga prasība** social-card kontekstā — fix `src/image_variants.py:96` + regresijas tests `tests/test_image_variants.py::test_og_jpeg_is_baseline_not_progressive`.

**Why:** Twitter Cards vēsturiski silently fail uz progressive JPEGs — nav error message, nav fallback, tikai blank preview. Citas platformas (Facebook OG, LinkedIn) handle abus, bet Twitter strict mode nē. og.jpg variants eksistē *specifiski* social previews, tāpēc baseline ir drošākais default. Šī uzvedība dokumentēta vairākās SEO/social tooling guides bet nav prominenta Twitter oficiālajā dokumentācijā — tāpēc viegli aizmirstama / atspēlējama.

**Diagnostiskā plūsma:** 2026-05-01 dienas pārskats neielādēja preview x.com pat ar `?v=1` cache-bust. Verificēja: meta tagi pareizi (`twitter:card=summary_large_image`, `og:image` kanonisks 1200×630), attēls fetch'ojas HTTP 200 ar Twitterbot UA, robots.txt `Allow: /`, HTTPS valid (Sectigo), nav redirect. `file og.jpg` izvads atklāja `progressive` flag → konvertēja uz baseline → preview ielādējās ar `?v=2`.

**Fix komponenti:**
- `src/image_variants.py:96` — `progressive=True` → `progressive=False` ar inline komentāru kāpēc.
- `tests/test_image_variants.py::test_og_jpeg_is_baseline_not_progressive` — pin'o uzvedību (PIL `img.info["progressive"]` falsy assertion). Future contributor, kas pārslēdzas atpakaļ "smaller file size" iemeslam, tiks noķerts CI.
- 2026-05-01 brief variants (image_id=59) re-encoded in-place + redeploy (203 KB diff).

**How to apply:** Visas brief / synthesis featured images, kas iet caur `make_variants()`, automātiski ģenerē baseline og.jpg pēc šīs izmaiņas. Nekāda manuāla iejaukšanās jaunām dienām nav nepieciešama. Hero/card/thumb webp variants nav ietekmēti (WebP nav progressive flag tādā pašā nozīmē).

**Plus side benefit:** Baseline JPEGs ir sekmīgāks ielādes UX uz lēna mobile — sequential pixel rows redzama no augšas uz leju, kamēr progressive sākotnēji rāda blurry full image. Tas pāradresē kompromisu: progressive bija optimizēts perceptīvajai veiktspējai, bet sociālajos previews nestrādāja vispār.

---

## 2026-05-01 — Role-aware profila tabi: `src/profile_kind.py` + tab dispatch

**TL;DR:** Politiķa profila lapa vairs nerāda statisku 9 tabu komplektu — tagad katram politiķim 3-5 tabi atkarībā no `profile_kind` (10 vērtību enum: deputy, minister, mep, regional, politician, journalist, analyst, organization, former, inactive). Žurnālistiem un analītiķiem nav Pozīciju taba, bet ir Komentāri-by un Publikācijas. Ministrēm nav Saeimā taba (viņi parasti nebalso). Spriedzes tab aizvietots ar Saites tab — mini-grafs SVG + 3 type-color sekcijas (uzbrukumi sarkans / spriedzes dzeltens / atbalsts zaļš) + commentary-about + vote-alignment top/bottom (deputātiem) + linka uz pilno `/saites.html`.

**Why:** 9-tabu komplekts visiem profiliem radīja kognitīvo slodzi un pretrunīgus tukšumus — žurnālistam Pozīciju tab vienmēr tukšs, ministrei Balsojumu tab vienmēr 0 (Siliņa, Braže, Sprūds), Spriedzes stat-poga lump'oja uzbrukumus + spriedzes + atbalstu zem viena skaitļa. Pēc tension #90 dzēšanas Šleseram rādīja "1 spriedze" lai gan reālā spriedze bija type='uzbrukums' — tas atklāja klasifikācijas defektu. Reorganizācija balstīta uz 2026-05-01 Telegram dizaina sesiju (Elviss ↔ Claude Opus 4.7) — sk. plāna §1.

**Arhitektūra (sekojot `src/coalition.py` precedentam):**
- **`src/profile_kind.py`** (jauns, ~110 LOC ar docstring) — `Literal["deputy", "minister", "mep", "regional", "politician", "journalist", "analyst", "organization", "former", "inactive"]` enum, `derive_profile_kind(rel, role, votes_count)` ar 10 first-match-wins likumu sarakstu, `get_profile_kind_map(db)` batch helper (one round-trip ar GROUP BY votes).
- **Compute-at-render** — `profile_kind` netiek glabāts DB. Aprēķināms no esošajiem `tracked_politicians.relationship_type` + `role` + `saeima_individual_votes` skaita. Role pārdēvēšana vai votes backfill plūst caur nākamajā `generate_public_site` palaišanā bez migrācijas.
- **`src/render/_common.py`** re-eksportē `derive_profile_kind` + `ProfileKind` per F4 leaf rule, lai `politicians.py` neimportē tieši no `src.profile_kind`.

**Derivācijas likumi (pirmais match wins, sk. `src/profile_kind.py:derive_profile_kind`):**
1. `relationship_type='inactive'` → `inactive`
2. `relationship_type='journalist'` → `journalist`
3. `relationship_type='organization'` → `organization`
4. `relationship_type='neutral'` → `analyst`
5. role satur `ministr`/`valsts kanc`/`valsts prezident` (pēc bijuš-chunk filtra) → `minister`
6. role satur `\bep\b` (word-anchored) vai `eiropas parlament` → `mep` *(catches both `EP deputāts` + EP leadership roles ar substring-style match would miss — Roberts Zīle "EP viceprezidents")*
7. role satur `mērs`/`vicemērs`/`domes` → `regional`
8. `current_term_vote_count > 0` → `deputy`
9. role.lower() satur `bijuš` → `former`
10. else → `politician`

**Bijuš-chunk filtrs (regex `^biju[sš]`):** Multi-role string-i kā `"Saeimas deputāte, bijusī Izglītības un zinātnes ministre"` (Anda Čakša) sadalīti pa komatiem; chunki, kas sākas ar past-participle "bijus(ī|i|a)" / "bijuš(...)" tiek atfiltrēti PIRMS substring match. Bez tā likums 5 (`'ministr' in active_role`) noķerm bijušo lomu un Čakša mis-classificē kā ministrs. Sākotnējais regex `^bijuš[aīi]\b` arī izlaida `Bijušais Rēzeknes mērs` (Bartaševičs) — `\b` neaktivējās pirms `i` rakstā `bijušais` — pēc paplašināšanas uz `^biju[sš]` šis case korekti klasificējas kā `former`.

**Profile_kind sadalījums DB (174 active, 2026-05-01):**
- 99 deputy, 18 minister, 11 regional, 8 mep
- 16 politician (Hermanis, Šlesers, party officials, board members)
- 15 journalist, 5 analyst (rel=neutral)
- 2 organization (LDDK, Saeimas ziņas)
- 1 former (Bartaševičs — bijušais Rēzeknes mērs)

**Tab mapping per kind:**
| Kind | Tabi |
|------|------|
| deputy | timeline, pozicijas, saeima, pretrunas, saites (5) |
| minister/mep/regional/politician | timeline, pozicijas, pretrunas, saites (4) |
| former | timeline, pozicijas, saeima (vēsturisks marker), pretrunas, saites (5) |
| organization | timeline, pozicijas, saites (3) |
| journalist/analyst | timeline, komentari-by, publikacijas (+ pretrunas/saites if data, max 5) |
| inactive | timeline (1) |

`saeima` tab apvieno iepriekšējos `balsojumi` + `likumprojekti`. `publikacijas` tab apvieno žurnālistu/analītiķu X+Ziņas. Citiem profiliem X+Ziņas inline zem Pozīcijas. Iepriekšējais `spriedzes` tab aizstāts ar `saites` tab.

**Saites tab (mini-grafs + type-color sekcijas):** Statisks SVG (400×280 viewBox) ring-layout ar centra mezglu (politiķis ar partijas krāsu) un līdz 8 kaimiņiem (tension partneri, dedupe pa pid, ar pre-computed x/y koordinātām Python pusē — Jinja nav iebūvētu trig filtru). Sekcijas: Uzbrukumi (sarkans #ef4444), Spriedzes (dzeltens #eab308), Atbalsts (zaļš #22c55e), Komentāri par šo politiķi (commentary_about), Vote-alignment top/bottom (TIKAI deputātiem; SQL pār `saeima_individual_votes` self-join, HAVING total>=10, top/bottom-3 by agree_pct). Linka uz `/saites.html` apakšā.

**Helper funkcijas pievienotas `src/render/politicians.py`:**
- `_profile_tab_set(kind, has_contradictions, has_saites_content)` — base mapping + has_data konditionals žurnālistiem/analītiķiem.
- `_vote_alignment_for(db, pid, top_n=3)` — per-pid vote-alignment query, F4 leaf rule (links.py `_fetch_graph_data` optimizēts globālam graph view ar threshold filtru, ne per-pid).
- `_saites_neighbors_with_coords(neighbors, cx, cy, r)` — pre-compute SVG ring-layout x/y.
- `_fetch_saites_for_profile(db, pid, kind, tensions, commentary)` — splits by tension_type, runs vote_alignment for deputies, builds 8-neighbor mini-graph.
- `_fetch_commentary_by(db, pid)` — claims kuros politiķis ir speaker_id (mirror of `_fetch_commentary_about`).

**Template (`templates/politician.html.j2`):** Visi stat-buttons + tab content blocks aplikti `{% if 'X' in tab_set %}`. Header `.profile-role` aizstāts ar `.role-chip role-chip-{kind}` (10 hue tokens — deputy zils, minister zaļš, mep violets, regional oranžs, politician pelēks, journalist tumši pelēks, analyst smaragds, organization rozā, former oranžs, inactive gaiši pelēks). Iepriekšējie `tab-balsojumi`, `tab-spriedzes`, `tab-x`, `tab-zinas`, `tab-likumprojekti`, `tab-komentari` (versija ar commentary_about) izņemti.

**`assets/style.css` papildinājumi:** `.role-chip` + 10 kind-specific klases · `.mini-saites-graph` SVG sizing · `.saites-link-{uzbrukums,spriedze,atbalsts,vote}` stroke krāsas · `.saites-section-{...}` ar `::before` square-marker glyphs · `.alignment-list` · `.see-full-graph-link`. ~70 LOC pievienots.

**Char-fixture REGEN:** Politicians fixture flipped 174 hashes; sibling fixtures (analyses, blog, dashboard, graph, misc, parties, x) flipped because of assets `?v=` cache-bust update. Konvencija sk. 2026-04-30 entry "Drift catch" — separate REGEN commit pēc layout/CSS changes.

**Smoke-tested 8 sample profili (visi 7 active kinds):**
- Šnore (deputy) — 5 tabi, blue chip, Saites tab ar uzbrukumi + alignment top/bottom
- Siliņa (minister) — 4 tabi, NAV Saeimā, green chip
- Pupols (mep) — 4 tabi, purple chip
- Kleinbergs (regional) — 4 tabi, orange chip
- Hermanis (politician) — 4 tabi, gray chip
- Lapsa (journalist) — 5 tabi (ar pretrunas + saites jo data >0), dark-slate chip
- Rajevskis (analyst) — 4 tabi, emerald chip
- Zīle (mep, EP viceprezidents) — fix ielāpā pēc audita: substring `ep deputāt` izlaida šo, `\bep\b` regex noķer

**Nav iekļauts šajā PR (future work):**
- Personas filtra extension pa `profile_kind` (nākamais UI restrukturizācijas solis)
- Bijušais sub-badge header (header chip jau koda krāsas, atsevišķs badge bija plāna §4.2 polish — nav nepieciešams)
- Vote-alignment promotion uz `_common.py` (waiting for second consumer)
- Org advocacy vs press split (ja Saeimas ziņas + LDDK plūsma sajaucas)

**Plan + execution:** [docs/superpowers/plans/2026-05-01-profile-role-aware-tabs.md](../../docs/superpowers/plans/2026-05-01-profile-role-aware-tabs.md). 5 commits uz `feat/profile-roles` branch:
1. `c45299e` feat(profile_kind): module + 12 parametrized tests
2. `b9bd1f4` fix(profile_kind): broaden bijuš filter for whole-role former markers
3. `c0a15bc` feat(profile): role-aware tab dispatch + Saites mini-graf + chips
4. `2ce0d9f` test(render): REGEN char baselines (174 hash flip)
5. `24a2331` fix(profile_kind): word-anchor EP rule for leadership roles

---

## 2026-04-30 (vēlu rīts) — Drift catch: REGEN uz schema test + daily check.sh solis

Master HEAD pirmsdienas atklāja 9 sarkanus testus, kas bija operatoriskais regen-debt no PR #18 + dienas ingest pulses. Divi atšķirīgi cēloņi, divas atšķirīgas dabas, viens kopējs preventīvs labojums.

**Cēloņi:**
1. `tests/test_schema.py::test_schema_sql_matches_pre_refactor_dump` — PR #18 pievienoja `documents.title` caur `ALTER TABLE` `src/db.py:132`, bet `docs/refactor/schema-dump-pre-f2.sql` baseline neapdroš. Tests pirms šī commit-a neatbalstīja `REGEN=1` — operatoriem nebija tipiska ceļa baseline-a atjaunošanai.
2. `tests/test_render_chars.py` — 8 char-fixture failures, jo dienas ingest (~140 docs starp d38034c regen 08:31 un 10:30) izmainīja dashboard counts un index hashes. `REGEN=1` jau strādāja, bet rutīna to nepieprasīja.

**Labojumi:**
- **`tests/test_schema.py`** atbalsta `REGEN=1` — paralēli char-tests konvencijai. Saglabā header komentāru bloku, pārraksta body no fresh `init_db()` dump. ALTER TABLE PR autors tagad palaiž `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_schema.py` un commit-o atjaunoto baseline tajā pašā PR.
- **Daily routine Solis 9.5** (`wiki/operations/daily-routine.md`) — `bash scripts/check.sh` pirms publish (Solis 10). Ja sarkans, REGEN + commit, tad turpina. Drift atklājas tajā pašā dienā kad rodas, nevis nākamreiz kad atver master.

**Why:** Char drift notiek katru dienu (DB aug ar ingest); schema drift notiek vienreizēji uz katru ALTER TABLE. Abi gadījumi ir leģitīmi expected — sarkans tests bija pareizs signāls, ka baseline jāatjauno. Trūkstošais bija (a) REGEN ceļš schema testam un (b) workflow solis, kas to ķer pirms publikācijas.

**How to apply:**
- ALTER TABLE PR-i: pievieno `REGEN=1 pytest tests/test_schema.py` + commit `docs/refactor/schema-dump-pre-f2.sql` tajā pašā PR.
- Daily routine: pirms Solis 10 palaid `bash scripts/check.sh`. Ja char-tests sarkani, `REGEN=1 pytest tests/test_render_chars.py` + commit baseline JSON-us. Reālas regresijas (broken render, importa kļūda) jārisina pirms publish.

---

## 2026-04-30 — Bundle F: `documents.title` reliably populated for all news sources

Forward-fix + backfill pair. `src.title_extract.extract_title()` (Bundle A, 17 tests) runs at ingest on every web scrape path: RSS in `_parse_rss_items` (2.0 + Atom), crawl4ai in `_scrape_tier2` (tier-2 sources), trafilatura in `_scrape_web_articles` (legacy web_scraper). Persisted via `insert_document(title=...)` (Bundle B, schema migration in `init_db()`) into the existing `documents.title` column. One-shot `scripts/backfill_titles.py` (Bundle D, 6 tests) populates 2402 legacy web docs where title was NULL/empty.

**Result:** `zinas.html` render (`src/render/news.py:_fetch_news`, Bundle E) no longer uses `content[0:140]` heuristic — reads DB title directly with URL-slug last-resort fallback. Complies with Autortiesību likuma 20. pants ("darba nosaukums" obligātā norāde), supplementing existing `source_url` + `source_domain` provenance.

**Title extraction cascade:** `og:title` → `twitter:title` → JSON-LD `headline` → `<title>` → `<h1>`. Handles both forward (`property=...content=...`) and reverse (`content=...property=...`) meta-attribute ordering (Yoast/Drupal Metatag pattern), HTML entities, whitespace collapse, 250-char cap.

**Suffix-strip patterns** (26 entries, case-insensitive): LSM.lv/LSM, Delfi (incl. capitalized), Latvijas Avīze/LA.lv, Jauns.lv, TVNet/tvnet.lv, Diena/diena.lv, NRA/nra.lv, LETA, rus.delfi.lv.

**Bundle breakdown:**
- **A** (`src/title_extract.py` + tests): Pure HTML title extractor, stdlib only.
- **B** (`src/db.py` migration): `insert_document(title=...)` + `init_db()` column setup for fresh DBs (schema.sql untouched per convention: migrations in code, not regenerated).
- **C** (`src/ingest.py` + tests): Wire extractor into RSS/crawl4ai/trafilatura paths + `_ingest_source` plumbing.
- **D** (`scripts/backfill_titles.py` + tests): Idempotent one-shot script (`--apply` flag). `derive_title_from_content()` picks first reasonable line (10-250 chars), strips LA.lv " 0" noise, normalizes via `src.title_extract._normalize`. CLI: `--limit N` for test runs.
- **E** (`src/render/news.py`): Drop heuristic, read DB title.

**Operator post-merge sequence (CRITICAL):**
1. `python -m scripts.backfill_titles` — dry-run from main worktree (expect ~2200 derived, ~2402 NULL rows)
2. `python -m scripts.backfill_titles --apply` — apply to `data/atmina.db`
3. `python -m pytest tests/test_render_chars.py::test_zinas_index_byte_identical -v` — **WILL LIKELY FAIL** (Bundle E drops the multi-step heuristic; rendered output changes for rows where old heuristic ≠ new DB-title-first logic)
4. If step 3 fails: REGEN baseline with diff review:
   - `python -c "from src.render import generate_public_site; generate_public_site()"`
   - Manually inspect `output/atmina/zinas.html` against pre-merge state
   - Update `tests/fixtures/render_baseline_misc.json` SHA-256 hash for `zinas.html` (operator diff review is the gate, not blind regen)
5. `python -c "from src.render import generate_public_site; generate_public_site()" && bash scripts/deploy.sh --dry-run` then live deploy

**Follow-up items (out of scope here, referenced for continuity):**
- **Excerpt-slicing assumption** in `src/render/news.py:75-80` (`rest = content[len(headline):].strip()`) is pre-existing tech debt: assumes `headline` is a substring prefix of `content`, generally false when `title` comes from meta tags rather than body. After Bundle E this path runs more often (more rows have DB title). See cleanup ticket when prioritized.
- **Author name extraction** (Autortiesību likuma 20. panta otra prasība — "darba autors(-i)") — `documents.author` column not yet added. Plan forward-fix when prioritized. Reference: source plan at `docs/superpowers/plans/2026-04-30-zinas-title-extraction.md` § Out of scope.

**Schema note:** `schema.sql` remains unmodified (existing convention: `init_db()` migrations, not schema regeneration). Live DB already had `title` column from prior migration; Bundle B adds migration to fresh-DB bootstrap path for test suite.

**Plan + tracking:** [docs/superpowers/plans/2026-04-30-zinas-title-extraction.md](../../docs/superpowers/plans/2026-04-30-zinas-title-extraction.md).

---
## 2026-04-30 — F3g: F3 noslēguma posms — Fāze 3 PILNĪBĀ PABEIGTA

**TL;DR:** F3g closure merged ar 3 commits PR #17: `generate_public_site` + `_generate_sitemap` + `_generate_og_image` izvilkti uz `src/render/_orchestrator.py` (444 LOC). `src/render/__init__.py` re-eksportē tos kā **kanonisko publisko ceļu**: `from src.render import generate_public_site`. `src/generate.py` 558 → **173 LOC** (-385) plašs re-export shim. `render_parties` self-contained (F3g.2) + `_load_wiki_profile` restored politicians.py:310 (F3g.3 — F3b regression fix). **Total trajectory: 4250 → 173 LOC (-96%). Fāze 3 closed.**

**PR #17 trajectory (3 commits + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `ac5fe83` | test | 4 char fixtures | REGEN: politicians (~150 hashes flip — F3g.3 wiki_profile bodies aktīvi), misc/x/dashboard data drift |
| `335c816` | refactor | 7 files (incl. new _orchestrator.py) | F3g.1 lift + F3g.2 parties + F3g.3 wiki_profile |
| `9262213` | docs | agent_api_inventory.txt | Full rewrite for canonical src.render path |
| `6ab0019` | merge | (PR #17) | |

**F3 final module map (17 src/render/* moduļi):**
- `_common.py` (~795 LOC, leaf — gains `_load_wiki_profile` from F3g.3)
- `_orchestrator.py` (444 LOC, jauns — owns generate_public_site + _generate_sitemap + _generate_og_image)
- 15 sub-page moduļi: `contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses, blog, dashboard`

**`src/generate.py` paliek (173 LOC re-export shim):**
- Re-eksportē ~85 simbolus no `src.render._common` + 15 sub-page moduļiem
- Tests + agents + scripts turpina importēt no `src.generate` bez izmaiņām
- CLI entry-point `if __name__ == "__main__"` saglabāts

**F3g.3 — wiki_profile restoration impact:**
- 162 `wiki/persons/<slug>.md` faili eksistē
- ~150 of 159 politiku detail pages tagad satur editorial profile body
- F3b regression (PR #7 hardcoded `wiki_profile = None`) atrisināts
- `_load_wiki_profile` paaugstināts no `analyses.py` uz `_common.py` (politicians-concern)

**Cycle safety:**
- `_orchestrator` imports `_common` (leaf) + every sub-page (each leaf relative to peers)
- `_common` imports nothing from `src.render.*` — terminal
- Sub-pages import only from `_common` — never peer
- `__init__.py → _orchestrator → _common (loaded fully) → sub-pages → _common (cached)` chain works
- Reviewer verified concrete: `from src.render._common import _slugify` runs without error

**Plan deviation flagged:**
- Plan paste-block targeted `src/generate.py <50 LOC re-export shim`. Reality: 173 LOC. Difference is the wide shim itself — 14 sub-page imports + ~85 symbol re-exports — necessary to keep the test suite + agent contract intact. `<50 LOC` target ignored shim widening.

**F3 deferred items (not blocking F3 closure, kept for future opportunity):**
- F3g.4: `_chronologize_contradiction` + `_tension_filter_axes` helper promotions to `_common` (F3f.3 reviewer NICE-TO-HAVE) — dups exist, low leverage
- F3g.5: vestigial alias cleanup (blog.py `import re as _re`, dashboard.py inline datetime imports) — byte-equivalent carryovers
- F3g.6: char fixture dedup (analizes.html in 2 fixtures) — both pass, redundancy is explicit cross-assertion safety

**Reviewer verdict (PR #17):** *SHIP.* Zero MUST/SHOULD-FIX. Cycle-safety verified in practice. Byte-equivalence verified line-by-line for `_orchestrator.py` (only 2 intended diffs: `parties = _fetch_parties_page(db)` lifted into orchestrator; `render_parties` consumes `parties` positionally). `_load_wiki_profile` byte-identical in `_common.py`. Shim contract preserved (25+ test imports work). NICE-TO-HAVE: pre-existing operator log inaccuracies in `_orchestrator.py:313,316` (page-list literal, root-page count) — drift inherited from master, not F3g introduced.

**Test surface (post-F3g, F3 final):**
| Fixture | Pages | Note |
|---------|-------|------|
| 10 baseline JSON files | 417+ HTML pages | byte-identical safety net across all sub-pages |

**F3 trajectory summary (F3a → F3g):**
| Phase | PR | Master | LOC delta | Modules new |
|-------|----|----|-----|-----|
| F3a | #5 | `3d06e05` | 4250 → 3733 | _common.py + contradictions.py |
| F3-prep | #6 | `dbed1a0` | 3733 → 3699 | (leaf promotions) |
| F3b | #7 | `c97dbb5` | 3699 → 3198 | politicians.py + personas.py |
| F3c | #8 | `118b3a5` | 3198 → 3003 | parties.py |
| F3d | #9 | `b0586ad` | 3003 → 2419 | positions.py + news.py + statistika.py |
| F3e | #10 | `cba1aaf` | 2419 → 1783 | bills.py + laws.py + votes.py |
| F3g-pre | #11 | `0fd2565` | (no change) | (`_load_syntheses` CWD fix) |
| F3f.2 | #12 | `31f4c9f` | 1783 → 1536 | x.py |
| F3f.3 | #13 | `5b88e7b` | 1536 → 1187 | tensions.py + links.py |
| F3f.5 | #14 | `f88865d` | 1187 → 1031 | analyses.py + syntheses.py |
| F3f.4 | #15 | `0dcaf66` | 1031 → 772 | blog.py |
| F3f.1 | #16 | `385071c` | 772 → 558 | dashboard.py |
| **F3g** | **#17** | **`6ab0019`** | **558 → 173** | **_orchestrator.py + __init__.py canonical** |

**Total LOC reduction:** 4250 → 173 = **-4077 LOC (-96%)**. 17 src/render/* moduļi, ~85 shim symbols, 10 byte-identity fixture files, 914 tests passing.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt) (rewritten F3g closure brīdī).

---

## 2026-04-30 (agra rīta) — F3f.1: dashboard.py — F3f noslēgts

**TL;DR:** F3f.1 carve-out merged 2 commits-os PR #16: homepage hero (`index.html`) + combined `analizes.html` index izvilkti uz `src/render/dashboard.py` (293 LOC leaf). Tas ir **pēdējais F3f sub-phase** — F3f noslēgts, atlikušais F3 darbs ir tikai F3g (cycle-debt clear). `generate.py` 772 → **558 LOC** (-87% no sākotnējā 4250).

**PR #16 trajectory (2 commits + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `b249690` | test | x.json refresh + dashboard.json bootstrap + 2 F3f.1 char tests | Stale x.html baseline (data drift kopš F3f.4 merge) + jaunais F3f.1 fixture |
| `95c6fc0` | refactor | dashboard.py + generate.py | Carve-out: 4 fetcheri + render_dashboard |
| `385071c` | merge | (PR #16) | |

**Module map (post-F3f.1, 15 src/render/* moduļi):**
- F3f.1 (jauns): `dashboard.py` (293 LOC, leaf) — `_fetch_stats`, `_sparkline_svg`, `_fetch_hero_v2_data`, `_fetch_trends_data`, `render_dashboard(env, db, atmina_dir, stats, contradictions, votes, blog_posts, syntheses, analyses, trends_data, context_notes, days_until)`. Imports: `_common.{BASE_URL, PARTY_COLORS, _render_page, _slugify}` + `src.db.{today_lv, CLEAN_START_DATE}` + stdlib + extern (markupsafe.Markup, jinja2.Environment).
- Iepriekš (16 moduļi kopā ar `_common`): `_common, contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses, blog`.

**Plan deviations (1 flagged):**
1. `render_dashboard` rendere ABAS lapas — `index.html` (block #1) UN `analizes.html` (block #6). Plan paste-block to eksplicīti autorizē ("Iekļauj arī orchestrator-owned analizes.html combined index render"). Abi koplieto orchestrator-fetched data (stats, blog_posts, syntheses, analyses, trends_data, context_notes); co-locating saglabā data flow skaidrību. Reviewer verificēja byte-identitāti: analizes.html SHA `f413ff7b...` matches F3f.5 fixture.

**Pass-through args:** 12 args (3 primary + 9 data). Garākais peer (render_votes 6 args). Plan paste-block to atzina "Pass-through args list ir liels — apsveri before commit". F3g var bundle context, kad `generate_public_site` lift-osies uz `src/render/__init__.py`.

**Reviewer verdict (PR #16):** *CLEAN. Merge.* Zero MUST/SHOULD-FIX. Reviewer matemātiski verificēja `analizes.html` placement-change byte-identitāti: `env.globals["bill_slugs"]` ir set PIRMS render_dashboard izsaukuma; nekāds peer render_* nepieskaras `env.globals` post-startup; pre-fetched lists (analyses, syntheses, blog_posts) nav mutētas in-place. Char fixture cross-asserts SHA-identitāti starp F3f.5 + F3f.1 fixtures.

**Reviewer NICE-TO-HAVE → F3g checklist (added):**
- `src/generate.py` vestigial top-level imports (post-F3f.1): `import json`, `import re`, `import sqlite3`, `from datetime import datetime, timedelta, timezone`, `from markupsafe import Markup`, `now_lv_dt + CLEAN_START_DATE` no `src.db` — visi vairs nelieto. ruff F401 silenced šim failam (`pyproject.toml:50`), tāpēc check.sh paliek zaļš. F3g vestige sweep notīrīs šos kopā ar `blog.py` `import re as _re` aliases un `dashboard.py:95` inline `from datetime import` shadow.
- `_common.py:484` (now `:511`) — kompletā agent_api_inventory.txt rewrite landing F3g-ā (kanoniskais `src.render` public path).

**Test surface (post-F3f.1):**
| Fixture | Pages | Note |
|---------|-------|------|
| `render_baseline_dashboard.json` | index.html + analizes.html | F3f.1 — analizes.html SHA cross-asserted ar F3f.5 fixture |

**F3 noslēguma posms — atlicis tikai F3g:**
- Lift `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py` vai `src/render/_orchestrator.py`
- `src/generate.py` → ~30-50 LOC re-export shim
- `render_parties` self-contained (drop `parties_data` return)
- Restore `_load_wiki_profile` callsite at `politicians.py:310` (F3f.5 follow-up, dead code restoration)
- Apply F3f.3 review nice-to-haves (`_chronologize_contradiction` + `_tension_filter_axes` to `_common`)
- F3f.4 + F3f.1 vestigial alias/import cleanup
- `agent_api_inventory.txt` full rewrite (canonical `src.render` public path, ~15 modules + ~85 shim symbols)
- Char fixture dedup (analizes.html in F3f.1 + F3f.5 fixtures)
- `tests/test_generate.py` reorganize uz `tests/test_render_<page>.py` ja >1500 LOC

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (vēla nakts) — F3f.4: blog.py

**TL;DR:** F3f.4 carve-out merged 1 commit-ā PR #15: blog index (`blog.html`) + per-post pages (`blog/<slug>.html`, ~25 daily/weekly briefs) + `_fetch_blog_posts` + `_fetch_context_notes` + `_rewrite_shortener_link_labels` izvilkti uz `src/render/blog.py` (321 LOC leaf modulis). `generate.py` 1031 → **772 LOC** (-82% no sākotnējā 4250). Bonus: F3f.2 cross-ref bookkeeping iebūvēts (`parties.py:185` + `_common.py:511` tagad norāda `src/render/x.py`); F3f.5 docstring kļūda izlabota (`_parse_frontmatter` reālie patērētāji ir tikai analyses + syntheses, ne blog).

**PR #15 trajectory (1 commit + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `e593f1b` | refactor | blog.py + generate.py + _common.py + parties.py + briefs.py + tests | Carve-out + F3f.2 cross-ref bookkeeping + F3f.5 docstring fix |
| `0dcaf66` | merge | (PR #15) | |

**Module map (post-F3f.4, 14 src/render/* moduļi):**
- F3f.4 (jauns): `blog.py` (321 LOC, leaf) — `_SHORTENER_CANONICAL`, `_MD_LINK_RE`, `_rewrite_shortener_link_labels`, `_fetch_context_notes`, `_fetch_blog_posts`, `render_blog`. Imports: `_common.BASE_URL` + `_render_page` + `src.briefs.strip_visual_brief_block` (no cycle — `briefs.py` importē tikai `src.db`).
- Iepriekš: `_common, contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses` (16 moduļi kopā ar `_common`).

**Plan deviations (4):**
1. `render_blog(env, atmina_dir, blog_posts)` — 3 args, ne 4. Plāns paredzēja `context_notes` kā 4. arg, bet `context_notes` ir tikai orchestrator-owned `analizes.html` index render consumer (NE blog rendering). Tāda pati deviācija kā F3f.5 `render_syntheses`.
2. **F3f.2 cross-ref bookkeeping iebūvēts šajā PR** (atlikts no PR #12): `parties.py:185` + `_common.py:511` komentāri tagad norāda `src/render/x.py` (post-F3f.2 location), nevis legacy `generate.py`. Plan paste-block to apstiprināja "F3f.2 follow-up bookkeeping for F3f.4 or F3g".
3. **F3f.5 docstring fix iebūvēts**: `_common.py:182-189` `_parse_frontmatter` docstring kļūdaini apgalvoja "three sub-page consumers" ar `_fetch_blog_posts` kā trešo. Patiesie consumeri ir tikai `analyses.py` (`_load_wiki_profile` + `_load_analyses`) un `syntheses.py` (`_load_syntheses`). `_fetch_blog_posts` ielasa no `context_notes` DB tabulas, NE markdown failiem — nekad neizsauc `_parse_frontmatter`. Promotion paliek pamatota (cycle avoidance), bet skaitīšana izlabota.
4. **`src/briefs.py:118`** narrative path reference no `src/generate.py:_fetch_blog_posts()` → `src/render/blog.py:_fetch_blog_posts()`.

**Reviewer verdict (PR #15):** *Clean — merge as-is.* Zero MUST-FIX, zero SHOULD-FIX. Byte-equivalence verificēta AST-līmenī (3 funkcijas: `_rewrite_shortener_link_labels` 880 chars, `_fetch_context_notes` 283 chars, `_fetch_blog_posts` 8518 chars — visas verbatim). Lint clean. Re-export shim ietur 8 lazy `from src.generate import _fetch_blog_posts` imports `tests/test_generate.py`-ā. Vienīgais NICE-TO-HAVE — `agent_api_inventory.txt` backfill F3f.5 + F3f.4 — atstāts F3g pilnam rewrite (per dd9ee4c plana checklist).

**Reviewer atklāsme:** Module-level `from src.briefs import strip_visual_brief_block` `blog.py:41` ir TĪRĀKS par iepriekšējo lazy in-loop importu `generate.py:577` — `briefs.py` importē tikai `src.db`, nekad `src.render` vai `src.generate`. Cycle-free.

**Test surface (post-F3f.4):**
| Fixture | Pages | Note |
|---------|-------|------|
| `render_baseline_blog.json` | blog.html + 25 blog/<slug>.html | Dynamic count — REGEN per blog ingest cycle (likumprojekti F3e precedents) |

**Atlikuši F3 (1 sub-fāze + final):**
- **F3f.1** dashboard.py — index.html (hero + sparklines + ticker + trends) + orchestrator-owned `analizes.html` combined index render. ⚠️ daudz pass-through args (analyses, syntheses, blog_posts, trends_data, context_notes, contradictions, votes, tensions). Sarežģītākais atlikušais.
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; restore `_load_wiki_profile` callsite (F3f.5 follow-up); apply F3f.3 review nice-to-haves; full `agent_api_inventory.txt` rewrite (canonical `src.render` public path); F3f.4 vestigial aliases cleanup (`import re as _re`, `from datetime import date as _date` blog.py-ā).

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (nakts) — F3f.5: analyses.py + syntheses.py

**TL;DR:** F3f.5 carve-out merged ar 4 commits PR #14: `analizes/<slug>.html` + `sintezes/<slug>.html` rendering izvilkts no `src/generate.py` divos leaf moduļos. `_parse_frontmatter` paaugstināts uz `_common.py` (3 sub-page consumers — F3-prep promotion rule). Trīs vakara sesijā stale char fixtures atjaunoti REGEN baseline darbībā kā atsevišķs commit pirms refaktoringa. `generate.py` 1187 → **1031 LOC** (-76% no sākotnējā 4250).

**PR #14 trajectory (4 commits):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `6cdd788` | test | 5 char fixtures + tests | REGEN refresh (contradictions/graph/politicians stale) + bootstrap render_baseline_analyses.json + 3 jauni F3f.5 char tests |
| `322763d` | refactor | analyses.py + syntheses.py + _common.py + generate.py + test_load_syntheses.py | Carve-out + _parse_frontmatter promotion + shim + orchestrator wiring |
| `dd9ee4c` | docs(plan) | refactor-plan-2026-04-29.md | Review nits — fix render_syntheses signature (3 args, not 4) + ticket _load_wiki_profile follow-up |
| `f88865d` | merge | (PR #14) | |

**Module map (post-F3f.5, 13 src/render/* moduļi):**
- `_common.py` (771 LOC, leaf) — paaugstināts ar `_parse_frontmatter` (yaml frontmatter parser, 3 consumers).
- **F3f.5 (jauni):** `analyses.py` (120 LOC, leaf) — `_load_wiki_profile`, `_load_analyses`, `render_analyses`. `syntheses.py` (126 LOC, leaf) — `_load_syntheses` (worktree-portable post-F3g-pre), `_map_syntheses_to_politicians`, `render_syntheses`.
- F3a-F3e + F3f.2 + F3f.3 (iepriekš): `contradictions/politicians/personas/parties/positions/news/statistika/bills/laws/votes/x/tensions/links` (no izmaiņām).

**Plan deviations (4):**
1. `_parse_frontmatter` → `_common.py` (3 sub-page consumers: `analyses.py`, `syntheses.py`, `generate.py:_fetch_blog_posts` F3f.4). Avoids reverse `from src.generate import _parse_frontmatter` cycle.
2. Char fixture iekļauj `analizes.html` (orchestrator-owned combined index) papildus per-page baselines — sanity check, ka jaunie loaders neizmaina datu formu.
3. `_load_wiki_profile` ir **dead code** post-F3b (PR #7) — `src/render/politicians.py:310` hardcodes `wiki_profile = None`. Funkcija tomēr pārvietota uz `analyses.py` per plāns; restoration ticketed F3g (sk. plāna §F3g checklist).
4. `tests/test_load_syntheses.py` import atjaunots uz `src.render.syntheses` direktais ceļš (F3-prep convention).

**Stale char baseline refresh (commit 1):** `bash scripts/check.sh` master pirms PR #14 = 903 passed + **4 failed** (contradictions, politicians, graph fixtures driftēja kopš 22:00 deploy/auto-sync — DB content drifts no jaunām claims/contradictions). Refresh + jaunais F3f.5 baseline → **910 passed**, 2 xfailed, 1 xpassed. Precedents: commit `3064541` "fix(test): refresh stale politicians baseline".

**Reviewer verdict (PR #14):** *Clean. Ready to merge.* Zero MUST-FIX, zero SHOULD-FIX. Divi NICE-TO-HAVE atlikti F3g (agent_api_inventory status header refresh + _load_wiki_profile restoration ticket — pēdējais ievietots dd9ee4c plānā). Byte-equivalence verificēta line-by-line, shim contract pilnīgs (6 simboli + paaugstinātais `_parse_frontmatter` re-eksportēti).

**Atlikuši F3 (3 sub-fāzes + final):**
- **F3f.4** blog.py — `_fetch_blog_posts` + `_fetch_context_notes` + `_rewrite_shortener_link_labels` (single callsite). Char fixture REGEN pēc katras blog ingest darbības.
- **F3f.1** dashboard.py — index.html (hero/sparklines/ticker/trends), grūtākais (daudz pass-through args).
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; agent inventory → src.render kanoniskais ceļš; `_load_wiki_profile` restoration callsite + potential promote uz `_common.py`.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (vakars) — F3g-pre + F3f.2 + F3f.3 + matcher patterns

**TL;DR:** Trīs PR mergēti vienā vakara sesijā pēc dienas rutīnas. `_load_syntheses` CWD-atkarības bug atrisināts pie saknēm (F3g-pre, PR #11). x.html (F3f.2, PR #12) un spriedzes.html + saites.html (F3f.3, PR #13) carve-outs uz `src/render/`. 4 matcher false positives no šodienas analīzes papildināti ar `negative_patterns`. `generate.py` 1783 → **1187 LOC** (-72% no sākotnējā 4250).

**PR shipped trajectory (vakara sesija):**
| PR | Phase | Commit | LOC delta | Char tests | Modules |
|----|-------|--------|-----------|------------|---------|
| #11 | F3g-pre | `0fd2565` | (no change) | +3 unit tests | `_load_syntheses(atmina_dir)` signature change + 3 baselines regen |
| #12 | F3f.2 | `31f4c9f` | 1783→1536 | +1 char | `x.py` (285 LOC) |
| #13 | F3f.3 | `5b88e7b` | 1536→1187 | +2 char | `tensions.py` (62), `links.py` (360) |

**F3g-pre (PR #11) — `_load_syntheses` output_dir-relative:**
- Threads `atmina_dir` through `_load_syntheses(atmina_dir = Path("output/atmina"))` so the synthesis-image existence check resolves relative to the explicit output dir, not CWD. Default arg preserves production behavior.
- Char baselines regen captured both the synthesis fix (10 politician hashes flip from has_image=True → False) and unrelated content drift accumulated since F3d (~50 hashes from claims/contradictions/votes added between commits `3d8ed1e..f493dd8`). Both are canonical-state correct.
- 3 unit tests (`tests/test_load_syntheses.py`) lock down the path-resolution invariant — atmina_dir lookup, empty atmina_dir, default-arg CWD-relative under `monkeypatch.chdir`.
- Closes pre-F3e CWD-atkarības drift root cause; previous reactive baseline patch (`3064541`) is now superseded by the structural fix.

**F3f.2 (PR #12) — `x.py` (Twitter/X feed page):**
- `_fetch_x_data(db)` + `render_x(env, db, atmina_dir)` self-contained orchestrator. Re-export shim widens by 2 names; 11 test_generate.py tests directly import `_fetch_x_data` (V1 metrics suite).
- Char fixture: `render_baseline_x.json` (single page hash). Byte-identity preserved.
- Cleanup nit: `%`-style SQL placeholder formatting → f-string + extracted `placeholders` local. New module isn't on UP031 per-file-ignore (and shouldn't be).
- Plan deviation: `_rewrite_shortener_link_labels` was plan-listed for x.py but has only 1 callsite (`_fetch_blog_posts:859`) — moves with F3f.4 (blog.py), not F3f.2. Plan task description updated.

**F3f.3 (PR #13) — `tensions.py` + `links.py` (1 PR, 2 leaf modules):**
- `tensions.py` (62 LOC): `_fetch_tensions(db)` + `render_tensions(env, db, atmina_dir, tensions)` → spriedzes.html.
- `links.py` (360 LOC): `_fetch_graph_data(db)` + `render_links(env, db, atmina_dir, tensions)` → saites.html with full inline orchestration absorbed (claims_by_pid, contras_by_pid, votes_by_pid payloads, ~140 LOC pulled out of `generate_public_site`).
- Pass-through `tensions` arg matches F3a (`render_contradictions`) and F3e (`render_votes`) precedents — orchestrator pre-fetches data shared by 2+ sub-pages.
- Char fixture: `render_baseline_graph.json` (both pages SHA-256 in one file). Reviewer renamed from plan's suggested `misc2.json` for semantic clarity.
- Cleanup nit: compact `a = x; b = y` semicolon pattern (E702) in contradiction-swap logic → one-statement-per-line. New modules pass full lint without per-file-ignore.
- F3g-deferred TODOs (from PR #13 review): extract `_chronologize_contradiction(row, key_pairs)` to `_common` (3 duplicates: `links.py`, `_common._enrich_contradiction`, `social_agent/candidates.py:93`); extract `_tension_filter_axes(tensions) -> dict` to `_common` (2 duplicates: tensions.py, links.py).

**Module map (post-F3f.3):**
- 12 → 14 moduļi `src/render/`. New: `x.py`, `tensions.py`, `links.py`.
- All 14 modules import only from `src.render._common` and stdlib + `src.db`/`src.coalition` (lazy). Zero peer sub-page edges. F4 leaf-vs-fan-out discipline preserved.

**Baseline post-F3f.3:** 7 char fixture files (`render_baseline_contradictions/politicians/parties/misc/bills/laws/x/graph.json`) covering 388 byte-identical pages. `bash scripts/check.sh` exit 0 = **907 passed** (905 pre-PR-#13 + 2 new char tests), 2 xfailed (pre-existing), 1 xpassed.

**Matcher negative_patterns sweep (post-rutīna):**
4 pol false positives surfaced by today's claim extraction were patched directly in DB (auto-applied next ingest cycle, matcher cache reloaded on first call):
- pid=182 (Otto Ozols, journalist) ← `Ozols un Instrumenti`, `ansis`, `Gustavo, ansis`, `Rīgas 825` (musician collision; TVNet Riga 825-anniversary concert)
- pid=101 (Inese Kalniņa, JV) ← `Mārīte Tabita`, `Nejaucēni`, `Bērnu, jauniešu un vecāku žūrij` (children's-book author collision; LETA LNB Bērnu žūrija)
- pid=64 (Guntars Vītols, neutral) ← `Jāzeps Vītols`, `Jāzepa Vītol`, `Edgars Vītols`, `Edgara Vītol`, `Virsdiriģentu svētk` (composer collisions; LETA Virsdiriģentu svētki)

LTV Ziņas (pid=170, journalist/relay account, `social_accounts.feed_type='relay'`) discussed but not modified — strukturāls jautājums (relay konts dzīvo `tracked_politicians` jo `social_accounts.opponent_id` FK), atstāts pagaidu plākstera režīmā ar esošām patterns `plašsaziņas`, `360 ziņas`. Atsevišķa `relay_accounts` tabula būtu tīrāka, bet tas ir lielāks migrāciju darbs.

**Atlikuši F3 (4 sub-fāzes + final):**
- **F3f.5** analyses.py + syntheses.py — tagad CWD-bug-free pateicoties F3g-pre (recommended next).
- **F3f.4** blog.py — `_fetch_blog_posts` + `_fetch_context_notes` + `_parse_frontmatter` + `_rewrite_shortener_link_labels` (single callsite). Char fixture REGEN pēc katras blog ingest darbības.
- **F3f.1** dashboard.py — index.html (hero/sparklines/ticker/trends), grūtākais (daudz pass-through args).
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; agent inventory → src.render kanoniskais ceļš.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 3 (F3a-F3e): `src/generate.py` → `src/render/` pakete

**TL;DR:** 4250 LOC monolīts `src/generate.py` sadalīts daudzmoduļu paketē piecos sub-phase posmos vienā dienā. Pēc F3e generate.py = 1783 LOC (-58%); 10 jauni `src/render/*.py` moduļi + 745 LOC `_common.py` leaf. Aģentu API stabils — `from src.generate import …` turpina darboties bez izmaiņām, jo top-level imports re-eksportē visus pārvietotos simbolus (66+ vārdi). Atlikušas F3f-F3g: dashboard/x/blog/analyses, cycle-debt clear.

**Sub-phase trajectory:**
| Phase | PR | Commit | LOC delta | Char tests | Modules |
|-------|----|----|-----|-----|---------|
| F3a | #5 | `3d06e05` | 4250→3733 | +2 | `_common.py` (469), `contradictions.py` (177) |
| F3-prep | #6 | `dbed1a0` | 3733→3699 | 0 | (no new modules; helper promotions + char-fixture stability) |
| F3b | #7 | `c97dbb5` | 3699→3198 | +2 | `politicians.py` (333), `personas.py` (135) |
| F3c | #8 | `118b3a5` | 3198→3003 | +2 | `parties.py` (250) |
| F3d | #9 | `b0586ad` | 3003→2419 | +4 | `positions.py` (227), `news.py` (158), `statistika.py` (305) |
| baseline-fix | — | `3064541` | 2419→2413 | 0 | (no new modules; tests/fixtures/render_baseline_politicians.json regen — 10 stale hashes from CWD-relative `_load_syntheses` image lookup; pre-flight cleanup before F3e) |
| F3e | #10 | `cba1aaf` | 2413→1783 | +4 | `bills.py` (203), `laws.py` (186), `votes.py` (382) |

**Moduļu shēma (post-F3d):**
- `src/render/_common.py` (745 LOC) — leaf: konstantes (`BASE_URL`, `PARTY_COLORS`, `SEVERITY_LV`, `CATEGORY_LV`, `CLAIM_TYPE_LABEL`, `_SEVERITY_GLYPHS`, `PZV1_TOPIC_COLORS` apzināti _common-ā **NĒ** — paliek `positions.py`-ā kā page-specific palette, ASSETS_DIR, ELECTION_DATE, _LV_TRANS, _LV_OFFSET_HOURS, _PARTY_LOWERCASE_WORDS, path roots), drošības filtri (`_sanitize_html`, `_safe_json_filter`, `_safe_url_filter`, `_autolink_bills_filter`), slug/format helperi (`_slugify`, `_party_short_name`, `_persona_category`, `_confidence_tier`, `_initials_from_name`, `_delta_days`, `_domain_from_url`, `_split_summary`, `_latvian_quotes`, `_photo_data_uri`, `_normalize_date`, `_date_sort_key`, `_format_tweet_time`, `_titlecase_party_name`), cross-page domain (`_source_to_internal_link`, `_enrich_contradiction`, `_bill_slug`, `_get_last_activity`), asset helperi (`_resolve_assets_version`, `_download_chart_js`, `_download_annotation_plugin`), page primitive (`_render_page`)
- `src/render/contradictions.py` (177 LOC) — F3a: `_fetch_contradictions`, `_render_og_cards`, `render_contradictions`
- `src/render/politicians.py` (333 LOC) — F3b: `_fetch_politicians`, `_fetch_commentary_about`, `_fetch_politician_detail`, `render_politicians`
- `src/render/personas.py` (135 LOC) — F3b: `_fetch_personas`, `_fetch_personas_metrics`, `render_personas` (self-contained)
- `src/render/parties.py` (250 LOC) — F3c: `_fetch_parties_page`, `_fetch_party_detail`, `render_parties` (returns parties_data — sitemap dependency, resolves at F3g)
- `src/render/positions.py` (227 LOC) — F3d: `_fetch_claims`, `_fetch_pozicijas_metrics`, `PZV1_TOPIC_COLORS`, `render_positions` (writes pozicijas.html + pozicijas-data.json + .br + .gz)
- `src/render/news.py` (158 LOC) — F3d: `_fetch_news`, `render_news` (self-contained)
- `src/render/statistika.py` (305 LOC) — F3d: `generate_statistika` STANDALONE entrypoint (NOT in generate_public_site flow; called manually after monthly CSP data sync)
- `src/render/bills.py` (203 LOC) — F3e: `_LAW_TITLES_CACHE`, `_get_law_titles`, `_fetch_bills`, `_fetch_bill_detail`, `_generate_bill_pages`, `render_bills(env, db, atmina_dir) -> int`. Emits ~151 likumprojekti/<slug>.html. `_get_law_titles` co-located with bills (only consumer is `_fetch_bill_detail` for `base_law_title`).
- `src/render/laws.py` (186 LOC) — F3e: `_LAW_LIKUMI_LV_RE`, `_LAW_BODY_STRIP_RE`, `_fetch_law_pages`, `_generate_law_pages`, `_fetch_law_index_page`, `render_laws(env, db, atmina_dir) -> int`. Emits likumi.html + ~33 likumi/<slug>.html. Returns `laws_index_count` for the balsojumi.html footer (F3a `all_parties` / F3c `parties_data` pass-through pattern).
- `src/render/votes.py` (382 LOC) — F3e: `_enrich_faction_breakdown` (pure, 8 unit tests), `_fetch_votes`, `_build_matrix_data`, `render_votes(env, db, atmina_dir, votes, bills, laws_index_count) -> None`. Emits balsojumi.html. Folds in vote_metrics, vote_sessions, deputies, matrix_data computation that was previously inline in generate_public_site (~50 LOC orchestrator delta).

**Cikla pārvaldība:** Visi sub-page moduļi importē TIKAI no `_common`, nekad savā starpā. F4 leaf-vs-fan-out disciplīna stingri saglabāta. Helper promotions notika 2 reizes pirms peer sub-page izveidošanas (F3-prep promovēja 4 leaf helperus + 2 const F3b/F3c/F3d nepieciešamībām; F3b promovēja `_bill_slug` + `_get_last_activity` peer sub-page sharing dēļ; F3d promovēja `_download_chart_js` + `_download_annotation_plugin` cycle-avoidance dēļ).

**F3a tehniskais parāds (atstāts F3g atrisināt):** `src/render/__init__.py` apzināti NEEKSPONĒ `generate_public_site`, jo `generate.py → render._common → render.__init__ → generate` cikls. F3g uzdevums: pārvieto `generate_public_site` uz `__init__.py`, atjaunina `generate.py` uz pilnu re-export shim, atjaunina inventāriju.

**Char-fixture pattern (`tests/test_render_chars.py`):** Session-scoped fixture izsauc `generate_public_site(output_dir=tmp)` + `generate_statistika(output_dir=tmp)` reizi par sesiju, hash-o target HTML pages, assert pret iesaldēto baseline. `ATMINA_ASSETS_VERSION="test"` env override (no F3-prep) izvairās no `?v=` cache-bust drift fresh worktree-ā. `REGEN=1 pytest` bootstraps baseline; bare run assert. Pieci baseline JSON failos:
- `render_baseline_contradictions.json` — pretrunas.html + 12 detail
- `render_baseline_politicians.json` — personas.html + 159 politiki/<slug>.html
- `render_baseline_parties.json` — partijas.html + 15 partijas/<short>.html
- `render_baseline_misc.json` — pozicijas.html + zinas.html + statistika.html + 10 statistika/<id>.html
- `render_baseline_bills.json` — balsojumi.html + ~151 likumprojekti/<slug>.html (F3e)
- `render_baseline_laws.json` — likumi.html + ~33 likumi/<slug>.html (F3e)

385 byte-identical pages kopā post-F3e (200 pre-F3e + 185 jauni). Adds ~30s vienu reizi pytest-am (session fixture amortizācija).

**Strukturālās mācības:**
1. **"Viens shim pietiek" no plāna sākotnējā teksta bija NEPILNĪGA** — testu suite (`tests/test_generate.py`, `test_personas_v2.py`, `test_pozicijas_v2.py`, `test_phase_1b_ii.py`, `test_generate_bills.py`, `test_likumi_index.py`, `test_autolink_bills.py`) tieši importē ~32 privātos `_fetch_*` / `_safe_*` / `_persona_category` / `PARTY_COLORS` simbolus no `src.generate`. Re-export shim ir plats, ne šaurs. Pieņemts kā migrācijas-window stratēģija; F3g atrisinās.
2. **`src/render/__init__.py` cycle** — sub-page imports trigger paketes `__init__.py`, kas, ja eksponē `generate_public_site` (kurš pats importē no `_common`), rada importēšanas ciklu. Pieņemts apzināti — F3g lift atrisinās.
3. **F4 leaf-vs-fan-out disciplīna pārnests F3-am perfekti.** Visi sub-page moduļi ir `_common`-leaves. F3-prep + F3b proaktīvas leaf promocijas pirms peer sub-page izveidošanas izvairījās no jebkura cikla F3b-F3d laikā.
4. **Char-fixture cumulatīvs noslēgums.** F3a → 2 tests; F3b → +2; F3c → +2; F3d → +4. Visi vienā fixture-failā ar viena session run-a per pytest. Pattern reusable F3e/F3f.
5. **`render_*` orchestrator signatures vary by data-flow:** self-contained (`render_personas`, `render_news`, `render_positions`) re-fetch internally jo data nav reused downstream; pass-through (`render_contradictions`, `render_politicians`, `render_parties`) saņem pre-computed data un, kur nepieciešams, atgriež to atpakaļ caller-am sitemap vajadzībām.

**Verifikācija:** `bash scripts/check.sh` exit 0 pēc katra commit. 887 (pre-F3a) → 897 (post-F3d) → 901 (post-F3e) passed = +14 char tests; 2 xfailed (pre-existing), 1 xpassed.

**F3e-specifiskās mācības:**
1. **Pre-F3e baseline drift atklāja slēptu CWD-atkarību.** `_load_syntheses` (src/generate.py:1656) lasa synthesis attēlus no CWD-relatīva `output/atmina/images/synthesis/` ceļa. Main worktree ir attēli no agrākiem render-iem; fresh worktree → `has_image=False` → 10 politiķu detail page nesatur synthesis `<img>` tag → hash drift. Fix landed kā 3064541 (regen baseline). **F3g/postlude TODO:** `_load_syntheses` jāpārtaisa, lai lasa images relative to render `output_dir` arg, ne CWD. Līdz tam F3 byte-identity invariants ir worktree-portability hidden bug — fresh worktree-ā char tests fails, līdz `cp output/atmina/images/synthesis/* worktree/...` mirror.
2. **`render_votes` signature deviation no plāna.** Plāns paredzēja `(vote_topics, deputies_list)` pass-through; reālā implementācija ir `(votes, bills, laws_index_count)`, jo `vote_topics`/`deputies`/`vote_sessions`/`matrix_data`/`vote_metrics`/`bill_topics` ir deterministic derivations no `votes`/`bills`. Iekšā render_votes-ā = mazāks signature, single source of truth. Pass-through pattern atbilst F3a (`all_parties`) un F3c (`parties_data`) precedentiem. `votes` un `bills` jau tāpat tiek pre-fetched generate_public_site-ā index page (`recent_votes`) un `env.globals["bill_slugs"]` autolink vajadzībām.
3. **`_get_law_titles` co-located ar bills.py, ne laws.py** — vienīgais konsumers ir `_fetch_bill_detail` (`base_law_title` lookup). Co-location ar consumer ļauj laws.py palikt leaf-clean.
4. **F3e review nits same-PR sweep (commit `abce764`)** — F3d's `b6b196a` šablons turpinās: dead `LAW_TITLE_RE` import + unused `bill_count` capture. Ruff F401/F841 ir per-file-ignored generate.py-ā, tāpēc abi nav auto-flagged; manuāli sweep katra extraction-a beigās.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 4: `src/saeima.py` → `src/saeima/` pakete

**TL;DR:** 1425 LOC monolīts `src/saeima.py` sadalīts piecu moduļu paketē. Aģentu API stabils — `from src.saeima import …` turpina darboties bez izmaiņām, jo `__init__.py` re-eksportē visus 28 ārēji-importētos simbolus.

**Moduļu shēma:**
- `src/saeima/schema.py` — `init_saeima_tables`, `init_saeima_bills` (DDL paliek Python pusē, ne `src/schema.sql`, jo `init_saeima_bills` lieto conditional `ALTER TABLE` pattern, ko sqlite < 3.35 neatbalsta)
- `src/saeima/bills.py` — `_VALID_BILL_TYPES`/`_VALID_STAGE_NAMES`, motif regexes, `resolve_bill_from_motif`, `_reading_from_motif`, `_resolve_base_law_slug`, `LAW_TITLE_RE`, `load_laws_index`, `_canonicalize_stage_name`, `upsert_bill`, `append_bill_stage`, `AgendaBill`, `SAEIMA_BASE_URL`, `_resolve_vote_url`, `_parse_vote_datetime` (leaf — nav saeima/ iekšējo importu)
- `src/saeima/parsing.py` — `parse_agenda_snapshot` + 3 helperi + agenda regexes (importē `AgendaBill` no bills)
- `src/saeima/claims.py` — `_stem`, `_word`, `_MOTIF_TOPIC_MAP`, `_motif_to_topic`, `_vote_salience` (leaf — pure topic mapping)
- `src/saeima/votes.py` — `IndividualVote`/`VoteResult`, `parse_vote_snapshot`, `_build_name_index`, `match_deputies_to_politicians`, `match_submitters_to_politicians`, `store_vote`, `generate_claims_from_votes`, `process_vote_snapshot` (depends on bills + claims)

**Cikla pārvaldība:** bills + claims ir leaf moduļi (nav saeima/ iekšējo importu). votes ir vienīgais ar fan-out uz abiem. parsing importē tikai no bills.

**Deviations no sākotnējā plāna (4):**
1. `parse_vote_snapshot` glabājas `votes.py` (ne `parsing.py`) — izvairās no `parsing → votes` cikla pār `VoteResult` import
2. `match_submitters_to_politicians` glabājas `votes.py` (ne `bills.py`) — koplieto `_build_name_index` ar siblinga `match_deputies_to_politicians`
3. `generate_claims_from_votes` glabājas `votes.py` (ne `claims.py`) — claims.py paliek tīrs leaf-modulis
4. `SAEIMA_BASE_URL` + `_resolve_vote_url` + `_parse_vote_datetime` — `bills.py` (ne savs `_helpers.py`) — koplietojami starp votes + claims, glabājami leaf modulī

**Strukturālā mācība:** Plāna sākotnējais 5-moduļu shēma (schema/parsing/votes/bills/claims pa funkcionālo lomu) bija circular pa runtime imports — `VoteResult` plūsma starp parsing/votes un `_motif_to_topic` plūsma starp votes/claims radītu `from src.saeima.X import Y`-stila ciklus. Risinājums bija nedaudz pārorganizēt pa "leaf vs fan-out" loģiku, ne pa stingru funkcionālo dalījumu. F3 (`generate.py` → `src/render/`) vajadzētu paredzēt to pašu — sub-pages sākotnēji izskatās kā independent moduļi, bet kopēji helperi (Jinja env, sanitization filtri, URL parties) parasti rada lasošo cikla risku.

**Pirmsdarbi (F4.0, commit `d92164f`):**
- `tests/fixtures/saeima_chars_expected.json` — frozen baseline (63KB, 19 motifu × 3 funkciju + 1 agenda + 3 vote snapshot output-i)
- `tests/test_saeima_chars.py` — 3 asserting tests; `REGEN=1` env regenerē baseline, ja uzvedība intentionally mainās
- `tests/fixtures/saeima_snapshots/` — 4 reāli Playwright snapshot faili no 2026-04-16 sesijas

**Pakešu skelets (F4.1, commit `0f3f273`):**
- `git mv src/saeima.py src/saeima_legacy.py`
- `mkdir src/saeima` + `__init__.py` ar 25 simbolu re-eksportu no legacy
- `pyproject.toml` ruff per-file-ignores atjaunina (saeima.py → saeima_legacy.py + saeima/*.py)

**Schema izvilkšana (F4.2, commit `89d9000`):**
- `init_saeima_tables` + `init_saeima_bills` pārvietoti uz `src/saeima/schema.py`
- `__init__.py` importē tos no `.schema` (ne legacy)

**Atomic split (F4.3+F4.4, commit `11ca874`):**
- 4 jauni moduļi (`bills.py`, `parsing.py`, `claims.py`, `votes.py`) + final `__init__.py`
- `src/saeima_legacy.py` izdzēsts (`git rm`)
- 28 simboli eksponēti caur `__init__.py.__all__`

**Iekšējo callsites + path references atjauninājums (F4.5):**
- `.claude/agents/saeima-tracker.md` — path reference `src/saeima.py:_parse_institutional_submitter` → `src/saeima/parsing.py:_parse_institutional_submitter`
- `wiki/operations/saeima-bills.md` — 3 path references atjaunināti uz pakešu sub-modules
- `src/db.py` — 2 narrative comment references atjaunināti

**Verifikācija:**
- `bash scripts/check.sh` exit 0 pēc katra commit
- 887 passed (884 pre-F4 baseline + 3 jauni char tests), 2 xfailed (pre-existing), 1 xpassed
- `generate_public_site` smoke clean — 159 politicians, 24 blog posts, 12 pretrunas pages
- Manual import smoke: visi 28 publiskie simboli importējami no `src.saeima` top-level

**Out of scope (atstāts vēlākām fāzēm):**
- Fāze 3 — `src/generate.py` (4250 LOC) → `src/render/` pakete pa lapu grupām
- Fāze 5 — `migrations/` formāts (atlikt līdz nākamai DDL izmaiņai)

Skat. plānu [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md), agent API inventarizāciju [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 0+1+2: drošības tīkls + matcher + schema.sql

**TL;DR:** Pirmie trīs soļi no [refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Politiķu name-matching kods (≈530 LOC) izvilkts no `src/ingest.py` uz dedicētu `src/matcher.py` moduli, un statiskā DDL (≈340 LOC) izvilkta no `src/db.py::init_db()` uz `src/schema.sql`. Aģentu API stabils — re-export shim glabājas `src/ingest.py`, lai `from src.ingest import match_politicians` u.c. turpina strādāt bez churn.

**Fāze 0 — Drošības tīkls (PR #1, commit b0f9871):**
- `pyproject.toml` ar ruff + pytest config; ruff exit 0 ar dokumentētu accept-list `[tool.ruff.lint.per-file-ignores]`
- `scripts/check.sh` — 3 soļu gate (ruff → pytest → generate_public_site smoke); `set -e` abortē jaunās neveiksmes
- `tests/test_invariants.py` — 7 līgumu smoke testi (CLAUDE.md punkti 2,3,4,5,6,9,11)
- `tests/conftest.py` — `collect_ignore_glob` optional ML deps + `_BASELINE_XFAIL` 3 zināmiem pre-existing fails (matplotlib jau xpassed)

**Fāze 1 — Matcher izvilkšana (PR #2, commit 4f4d25d):**
- `src/matcher.py` (NEW, ~580 LOC) ar 12 funkcijām: `extract_twitter_author_handle`, `match_politicians/match_politician`, `link_politicians_to_documents`, `assign_unmatched_documents`, `_load_politician_forms`, `_latvian_surname_inflections`, `_surname_has_person_context`, `_disambiguate_shared_surname`, `_init_surname_disambiguation`, `_match_politician_from_url`, `_clear_politician_cache`. Module state (caches): `_politician_forms_cache`, `_shared_surname_set`, `_SURNAME_DISAMBIGUATION`, `_COMMON_WORD_FORMS`, `_PERSON_CONTEXT_BEFORE/AFTER`, `_ROLE_PRIORITY`.
- `src/ingest.py` re-export shim glabājas — 10 simboli (5 publiskie + 5 privāti tests-only). `.claude/agents/*.md` un legacy skripti importē caur shim bez izmaiņām.
- 5 internal callers updated tieši uz `src.matcher` (4 audit/fix scripts + `src/social.py`).
- `tests/test_matcher.py` + `tests/fixtures/matcher_docs.json` — 12 curated characterization cases + 4 URL parser cases. Sedz: explicit fullname, two-politicians, surname collision (Hermanis bare + Jānis/Alvis variants), Latvian inflection (Siliņa→Siliņas), 2 negative_pattern fires (Bērziņš), foreign-firstname guards (Krists Kalniņš, Tomass Alens), common-word guard (Krasta iela), empty match, multiword surname (Linda Abu Meri).
- `tests/test_ingest.py::tmp_db` un 2 audit-test fixtures atjauninātas — patches `src.matcher.get_db` un izsauc `_clear_politician_cache()` (iepriekš rakstīja phantom attrs uz `src.ingest`).

**Fāze 2 — schema.sql izvilkšana (PR #3, commit 94466aa):**
- `src/schema.sql` (NEW, 340 LOC) ar 21 CREATE TABLE + ~25 INDEX + 3 PRAGMA. Statiskā DDL ar `CREATE … IF NOT EXISTS`.
- `src/db.py::init_db()` tagad: load sqlite-vec → `executescript(schema.sql)` → 2 vec0 `CREATE VIRTUAL TABLE` (Python-side carve-out, sk. zemāk) → 6 conditional ALTER TABLE migrāciju bloki (PRAGMA-driven, sqlite < 3.35 nav `ALTER TABLE ADD COLUMN IF NOT EXISTS`).
- `tests/test_schema.py` (3 testi): roster check, idempotent re-init, whitespace-normalized DDL diff vs `docs/refactor/schema-dump-pre-f2.sql` (65 stmt baseline).

**Carve-out: vec0 virtual tables paliek Python.** `tests/test_knab.py::_SafeConnection` mocko `sqlite_vec` CI vidēm bez native extension. Tā intercepto `.execute()` zvanus, kas satur `"vec0"`, bet NEvelk `.executescript()`. Tāpēc `CREATE VIRTUAL TABLE … USING vec0(…)` glabājas atsevišķi `db.execute()` zvanos `init_db()`, ne `schema.sql`. Komentāri ABĀS vietās: `src/schema.sql` apakšā un inline `src/db.py::init_db()`.

**Carve-out: brief_images + external_profiles paliek Python migrācijas blokos.** Tās tika pievienotas vēlu (2026-04-17 featured images, 2026-04-25 external_profiles); F2 negrozījās tās promote-ot uz `schema.sql`, lai turētu pārvietošanu šauru. `EXPECTED_TABLES` set `tests/test_schema.py` ietver šīs tabulas.

**Verifikācija:**
- F0: `bash scripts/check.sh` exit 0 — 865 passed (859 master + 7 invariants − 1 bonusa cleanup), 2 xfailed, 1 xpassed
- F1: 881 passed (865 + 16 jauni test_matcher cases), 2 xfailed, 1 xpassed
- F2: 884 passed (881 + 3 schema tests), 2 xfailed, 1 xpassed
- Pre-existing 3 baseline failures NAV pasliktinātas; matplotlib XPASS (uzstādīts kāds cits commit), social_agent + relay-author downgrade joprojām xfail (atsevišķi tracked)

**Code review:** PR #2 un PR #3 caur `superpowers:code-reviewer` aģentu; abos verdikts "Ready to merge" ar 0 kritisku/should-fix punktu un mazām nit korekcijām pirms merge.

**Out of scope (atstāts vēlākām fāzēm):**
- Fāze 3 — `src/generate.py` (4250 LOC) → `src/render/` pakete pa lapu grupām
- Fāze 4 — `src/saeima.py` (1425 LOC) → `src/saeima/` pakete (5 moduļi)
- Fāze 5 — `migrations/` formāts (atlikt līdz nākamai DDL izmaiņai)
- F3 un F4 ir savstarpēji neatkarīgi; var izpildīt jebkurā secībā

Skat. plānu `docs/plans/refactor-plan-2026-04-29.md`, baseline `docs/refactor/baseline-2026-04-29.md`, agent API inventarizāciju `docs/refactor/agent_api_inventory.txt`, schema baseline `docs/refactor/schema-dump-pre-f2.sql`.

## 2026-04-29 — X mentions: pivot uz `UserTweets` timeline-scan (SearchTimeline TID strict-validation 404)

**Simptoms:** Visiem 6 cookie slotiem `search_tweet` (mentions) un `get_user_tweets(uid, 'Replies')` 2026-04-29 sāka atgriezt `404 NotFound` ar empty body. `UserTweets` un `UserByScreenName` joprojām strādāja.

**Root cause:** X selektīvi pastiprināja `x-client-transaction-id` validāciju. Patch 4 (2026-04-28) stub TID strādā tikai uz lenient endpoints; `SearchTimeline` un `UserTweetsAndReplies` to noraida. Apstiprināts ar hardcoded browser TID — endpoint atbild 200 OK uzreiz.

**Risinājums (Phase B):** `src/x_mentions.py` pārstrādāts no OR-batched `search_tweet` strategy uz **per-politician `UserTweets` timeline scan + tekstuāls `@mention` filter**. `DEFAULT_BATCH_SIZE` izņemts no API; `total_queries` `social.py` skaitās kā `len(handle_to_pid)`. 7 jauni unit tests `tests/test_x_mentions.py` fiksē invariantu, ka `search_tweet` vairs **netiek izsaukts**.

**Trade-off:** Mentions FROM untracked autoriem (žurnālisti, neaktivi politiķi) vairs netiek savākti. Tracked-to-tracked interakcijas — pretrunu signāla pamats — saglabājas pilnībā. Replies produkts kodā netika lietots, tāpēc nav blast-radius.

**Diagnostika:** `scripts/probe_x_cookies.py` paplašināts uz visiem 4 endpoint-iem per slot (`get_user`, `user_tweets`, `user_replies`, `search_tweet`). Nākamajai drift detection būs agrīna.

**Long-term TODO:** Reverse-engineer modern X TID generator (indices pārvietojušies no `ondemand.s.*a.js` uz iekšēju webpack chunk). Kad TID būs derīgs, twikit `search_tweet` un `Replies` atkal strādās bez koda izmaiņām.

Skat. plānu `docs/superpowers/plans/2026-04-29-twikit-mentions-replies-404-fix.md` un `wiki/operations/twikit-notes.md` § 2026-04-29.

## 2026-04-28 — Video ingest pipeline (platform='video', timestamp source_url anchor)

Pievienots ceturtais satura kanāls — latviešu video debates un intervijas. `documents.platform='video'` jauna vērtība (bez schema migrācijas, kolonna jau ir TEXT). Implementācija: `src/video_ingest/` Python pakotne (yt-dlp + faster-whisper large-v3 INT8 + pyannote 3.1) + `@video-extractor` aģents. Operators iedod video URL vai lokālu failu → 4-fāzu plūsma (fetch → manuāla speaker mapping → finalize → extract-claims).

**Datu modeļa:**
- `documents.platform='video'` — viens row per video ar full speaker-labelled transkriptu
- `claim_type='position'` (saglabājas) — video pozīcijas plūst caur esošo dashboard/profila timeline
- `source_url` per claim ietver timestamp: `?t=N` YouTube, `#t=N` citur — saglabā `store_claim()` idempotenci uz `(opponent_id, source_url, topic)`
- `document_politicians` junction par katru zināmu speakeru ar `role='subject'`

**Komponenti:**
- `src/video_ingest/{cli,fetch,asr,diarize,align,heuristics,finalize,db,state,config,models}.py`
- `.claude/agents/video-extractor.md` + `wiki/operations/agenti/video-extractor.md`
- `wiki/operations/video-setup.md` (ffmpeg + HF token vienreizējais setup)

**Atkarības:**
- `yt-dlp`, `faster-whisper` (CTranslate2 INT8), `pyannote.audio` 3.3.2, `pydub`, `torch+CUDA`

Skat. spec `docs/superpowers/specs/2026-04-28-video-extractor-design.md` un plānu `docs/superpowers/plans/2026-04-28-video-extractor-implementation.md`.

## 2026-04-27 — Saeima Bills Phase 1C (orchestration & glue)

**TL;DR:** `@saeima-tracker` agent prompt expanded to populate
`saeima_bill_politicians` junction live (Step 2) and link votes to bill
stages (Step 5). Public site exposes `/likumi.html` base-law index +
auto-links bill references in claim summaries. CLAUDE.md Pipeline
Invariant 12 (append_bill_stage as sole writer of vote→bill state).

**Why:** Phase 1A delivered helpers; Phase 1B delivered UI templates that
already accepted the data shape. 1C is the glue layer that makes the
templates light up live, without any new core code path.

**What changed:**
- `.claude/agents/saeima-tracker.md` — Step 2 expanded to parse agenda
  bills + match submitters; new Step 5 links each vote to its bill stage
  via `append_bill_stage()`. Adds `KNOWN_INSTITUTIONAL_SUBMITTERS` prompt
  rule (19 entries) + Failure modes tier table.
- `src/generate.py` — `_autolink_bills_filter` Jinja filter wraps
  `\b\d+/(Lp14|Lm14|P14)\b` references in claim summaries with
  `<a href="likumprojekti/<slug>.html">`. `_fetch_law_index_page()`
  builds 33-row sortable index for `/likumi.html`.
- `templates/likumi-index.html.j2` — new (mirrors `/balsojumi.html#bills-list`
  pattern: topic chip + filter + search).
- `templates/balsojumi.html.j2` — footer link "Visi pamatlikumi (33) →" in
  bills-list-tab.
- `templates/{pretruna-detail,politician,pretrunas,index}.html.j2` —
  apply autolink_bills filter to claim summaries.
- `CLAUDE.md § Pipeline Invariants` — adds Invariant 12: append_bill_stage
  is the sole writer of `saeima_votes.bill_id` and
  `saeima_bills.current_stage`. (Committed directly to master as `5cb45c8`
  before worktree creation — doc-only, branch-orthogonal.)
- `wiki/operations/saeima-bills.md` — new operator runbook.
- `src/saeima.py` — `parse_agenda_snapshot` bounds the 500-char lookahead
  window at the next bill's match start to prevent deputy-list bleed
  across bill boundaries (uncovered by 1C live smoke).

**Tests:** 12 new (6 autolink_bills + 5 likumi_index + 1 parse_agenda
boundary regression). Phase 1B suite still passes.

**Live smoke results (2026-04-27):**
- 38 bills parsed from 2026-04-30 agenda (33 new + 5 already in DB)
- 0 unknown institutional submitters; 65 individual submitters matched
- Parser bleed bug found + fixed (22 spurious junction rows deleted)
- Junction post-smoke: 49 valid rows
- Step 5 (vote→stage link) not yet validated live — 2026-04-30 session
  not held yet (today is 2026-04-27)

**Out of scope:** Top nav entry to `/likumi.html` (deferred); Phase 1.5
historical re-scrape; Phase 2 amendment authors; Phase 3 debates →
bill_id; backfilling submitters into existing 91 historical bills.

---

## 2026-04-27 — Saeima Bills Phase 1B-ii: wiki/laws + base_law_slug + politiķa profila sekcija

**Iemesls:** Phase 1B-i (commit `42b2375`) atvēra bills datus publikai (118 detail lapas + balsojumi 3. subtab + cross-link). 1B-ii sasaista bills ar wiki/laws — populē `base_law_slug`, raksta BILLS-SYNC-AUTO blokus, renderē 33 jaunas `/likumi/<slug>.html` lapas, pievieno detail lapā "Saistītais bāzes likums" linka, un sagatavo politiķa profila Likumprojekti sekciju conditional.

**Izmaiņas:**

- **`base_law_slug` retro-backfill**: `scripts/backfill_base_law_slug.py` populē šo nullable kolonnu visiem 118 esošajiem bills (matched 41/118 = 34.7%). Match teritorija: title + jaunākā saistītā vote motif. `upsert_bill()` integrācija — jaunie bills no live aģenta plūsmas (Phase 1C) automātiski iegūst `base_law_slug` ar COALESCE preserving.
- **Shared `load_laws_index` helper** `src/saeima.py` — slug → title parser no `wiki/laws/*.md` H1 rindām. Lietots no backfill skripta + `upsert_bill` + `_fetch_bill_detail` cache.
- **wiki/laws auto-render**: `src/wiki.py::_render_law_bills_block` raksta `<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->` blokus 33 wiki/laws/<slug>.md failos ar tabulu vai empty state. `wiki_sync()` integrēts. Idempotents bytewise.
- **Jaunas publiskas lapas**: `/likumi/<slug>.html` (33 failu) — markdown render no `wiki/laws/<slug>.md` ar likumi.lv linka, bills count metric, full body. Strip H1 + metadata pirms render lai nedubliesies ar pagehead.
- **Detail page papildinājums**: "Saistītais bāzes likums" sekcija conditional render — parādās 41 bills, kuriem `base_law_slug` populēts, ar linka uz attiecīgā likuma lapu.
- **Politiķa profila sekcija**: "Likumprojekti" sekcija + profile-stat butons render TIKAI ja `saeima_bill_politicians` junction populēta priekš šī politiķa. Šobrīd nevienam politiķim sekcija nav redzama (junction tukša pēc Phase 1A); 1C lights up automātiski, kad live aģents to populē.
- **Naming fix**: `wiki/laws/likumi.md` un `wiki/index.md` semantiski pareizi ("Likumi", ne "Likumprojekti"). 33 likumi (ne 34, jo indeksa fails pats nav likums — bija self-count bug).

**Atstāts 1C-am:**
- `.claude/agents/saeima-tracker.md` aģenta prompt update (steps 2/3/5.5)
- Pozīciju auto-link regex `NNNN/Lp14` summary tekstā
- `wiki/operations/saeima-bills.md` runbook
- CLAUDE.md Pipeline Invariant 12

**Datu deltas:**
- `saeima_bills.base_law_slug` populated: 0 → 41 (34.7% no 118)
- Junction `saeima_bill_politicians`: paliek tukša līdz 1C
- Jaunas HTML lapas: `output/atmina/likumi/*.html` × 33

---

## 2026-04-27 — Saeima Bills Phase 1B-i: UI uz publiku

**Iemesls:** Phase 1A (DB schema + helperi + backfill) tika ievests 2026-04-27 (commit `64f1790`), bet bills datus varēja redzēt tikai caur SQL. Phase 1B-i atver tos publikai.

**Izmaiņas:**

- **Jaunas lapas**: `/likumprojekti/<slug>.html` katram no 91+ saeima_bills (slug = `document_nr.lower().replace("/", "-")`)
- **`/balsojumi.html`**: 3. subtab "Likumprojekti" ar topic/status/bill_type filtriem un teksta meklēšanu
- **Vote-card cross-link**: `document_nr` esošās balsojumu kartiņās kļūst par iekšēju saiti uz attiecīgo bill detail lapu (105 saistīti, 34 procedurālie paliek bez)
- **Step 0 P14 motif fix**: paplašina `_DOCUMENT_NR_RE` lai tver unparenthesized `/P14` motifu + papildināts `scripts/backfill_saeima_bills.py` ar fallback uz `resolve_bill_from_motif` kad `document_nr IS NULL` — atrisina HANDOFF Phase 0.7 punkts #6 un atklāj 5 P14 bills + 22 jaunus Lp14 bills (91 → 118 total)
- **Sitemap**: `/likumprojekti/*` URLs pievienoti

**Atstāts 1B-ii:**
- "Saistītais bāzes likums" detail bloks + wiki/laws/<slug>.md auto-render + politiķa profila Likumprojekti sekcija + `base_law_slug` retro-backfill

**Datu deltas:**
- saeima_bills: 91 → 118 (5 P14 + 22 jauni Lp14)
- saeima_bill_stages: 105 → 138
- Tukšs: junction `saeima_bill_politicians` paliek tukšs līdz 1B-ii vai live aģenta flow

---

## 2026-04-26 — Saeima bills Phase 0 prep applied

Pirms Phase 1 implementācijas (`docs/superpowers/specs/2026-04-22-saeima-bills-design.md`) atklāti 5 dizaina flaws audit'ā uz dzīvās DB (139 saeima_votes, 105 ar document_nr, 67% lasījuma klasificējami):

- **Stage classification 33% nezināms** — pie spec § 5.4 30% sliekšņa. Atrisināts ar 4 jaunām stage_name vērtībām (`tiesneša_amats`, `procesuāls`, `Lm14 cits`, `paziņojuma_balsojums`); paredzamais nezināms <8% pēc § 3.3 paplašinājuma. Slieksnis aktualizēts uz 10%.
- **P14 (paziņojumi) nav whitelist** — 5 reālas P14 rindas (dronu uzbrukumi, IT vēlēšanas, robežšķērsošana) būtu silently atmestas. Pievienoti `_VALID_BILL_TYPES = {'Lp14', 'Lm14', 'P14'}` + propagēts pa AgendaBill dataclass, `parse_agenda_snapshot` regex, backfill three-way classification (iepriekš binary `Lp14 | Lm14` būtu mistagged 5 P14 → Lm14), UI filter, detail page kicker.
- **wiki/laws/* izolācija** — 33 manuālas likumu lapas neintegrētas ar bill detail page. Pievienots BILLS-SYNC-AUTO marķieru pattern + `/likumi/<slug>.html` render + `_resolve_base_law_slug` match logic. Atklātais jautājums § 12 Q3 (vai wiki/laws ir atsevišķs spec) atrisināts: iekļauts šajā scope.
- **Phase 3 debates hook** — `saeima_bill_stages.stage_kind` kolonna (default `'vote'`) ļauj nākotnē Phase 3 pievienot stenogrammu utterances bez migrācijas. Phase 1 visi raksta `kind='vote'`; `_VALID_STAGE_NAMES` validē tikai vote rindas.
- **Vote-result audit guardrail** — `scripts/audit_saeima_vote_results.py` validē present-majority formula pret stored result. Šobrīd 0 mismatches uz 139 votes; daļa nedēļas sanity check (sk. `wiki/operations/weekly-routine.md § 4`).

Spec izmaiņas: 8 commits uz `saeima-bills-phase0` branch (no `2e0ff65` audit script līdz `ce8b049` Phase 3 hook), kas modificē `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` 7 sekcijās.

**Phase 1 statuss:** schema un agent prompt darba paka ship-ready uz spec v2 pēc Phase 0 prep.

---

## 2026-04-25 — Strukturālā sanācija: pub_at meta tag fix + Saeima vote-as-document anti-pattern noņemšana

**What changed:**

- **Solis 1A — pub_at sanācija tier-2 web scrape avotos.** `_extract_published_at(html)` helper `src/ingest.py` parsē 8 dažādus meta tag patterns (`article:published_time`, `og:published_time`, `itemprop=datePublished`, `name=publish-date|pubdate|date`, `<time datetime>`, JSON-LD `datePublished`). Wired `_scrape_tier2` abās vietās (homepage fallback + per-article). Pirms — NRA, Delfi, rus.Delfi, LA scrape path saglabāja `published_at=NULL` 100% gadījumu (RSS-based LSM/Diena/TVNet path strādāja korekti). Tagad 4/5 broken avotu pareizi atgriež pub_at; LETA paliek None paywall iemesla dēļ.
- **Solis 1B — Saeima vote-as-document anti-pattern noņemts.** Pirms — `generate_claims_from_votes()` katram individual vote radīja sintētisko `documents` rindu (platform='saeima', NULL title, ~170 char content) tikai tāpēc, ka `store_claim.document_id: int` nepieļāva NULL. Tas izpildīja 8985 fake docs (38% no kopējā 23105) ar 8876 claim atsaucēm, kas izstiepa visus document-based statistic (npr "23k documents", "93.6% NULL pub_at" — patiesie skaitļi 14k web/X docs un 78% web NULL pub_at).
  - `store_claim.document_id` mainīts uz `Optional[int]` (schēma jau pieļāva NULL ar notnull=0; tikai signature un canonicalization bloķēja).
  - `generate_claims_from_votes()` vairs neveido sintētisko docs — padod `document_id=None`.
  - Migrācija `scripts/migrate_saeima_doc_cleanup.py`: pirms-migrācijas check, ka neviens non-saeima_vote claim un neviens document_chunk neatsaucas uz fake docs (abort if so). Atomic transaction: UPDATE claims SET document_id=NULL → DELETE document_politicians → DELETE documents WHERE platform='saeima'. Idempotenta. Auto-backup pirms palaišanas.

**Why:** Lietotājs 2026-04-25 pieprasīja "vispirms visur pareizi un optimāli sastrukturizēt". Strukturālā audita atklājumi nosauca šīs divas kā lielāko parādu pirms tālākām UX/feature lapām: (1) pub_at NULL share aizliedz uzticamu time-window queries pret news content, (2) fake docs iztukšoja katru document-based statistic un padarīja documents tabulas semantiku jauktu (daļa = real docs, daļa = vote skeletoni). Vote provenance pilnībā rekonstruējama no `saeima_votes` + `saeima_individual_votes` caur `(claim.opponent_id, claim.source_url, claim.stated_at)`.

**Backward compatibility:**
- `_extract_published_at` ir tīri additīvs — RSS path (LSM/Diena/TVNet) joprojām ņem pub_at no `<pubDate>`, tier-2 web_scraper tagad arī iegūst pub_at no meta tagiem. Esošie consumers (`item.get("published_at")`) jau pieņēma None, nemainās.
- Vēsturiskās 8876 saeima_vote claims paliek DB ar pareizu `claim_type`, `source_url`, `stated_at`. Tikai `document_id=NULL` mainās. Visi readeri (briefs.py, generate.py, wiki.py) jau pirms tam izmantoja `claim_type='saeima_vote'` filtrus, ne JOIN claims ON documents — nekādas render path izmaiņas vajadzīgas.

**Migration counts (real DB):** fake_docs_pre=8985, claims_nulled=8876, junctions_deleted=8985, docs_deleted=8985, fake_docs_post=0. Backup: `data/atmina_backup_pre_saeima_doc_cleanup_2026-04-25-203058.db` (122 MB).

**Statistic recalibration:**
- Total docs: 23105 → 14435 (no fake docs)
- Web NULL pub_at: 93.6% → 78.2% (3750 web news docs, 2934 NULL — vēl jāuzlabo, bet jaunie scrape no šī brīža darbojas)

**Invariants added:**
- `store_claim` pieņem `document_id=None`. Saeima_vote claims now glabājas BEZ document_id — vote provenance iegūstama caur `(opponent_id, source_url, stated_at)` join uz `saeima_individual_votes`.
- `documents.platform='saeima'` rindas vairs nav atļautas. Migration skripts idempotents — re-run atrod 0.

**Files:** `src/ingest.py` (+helper, +wiring), `src/saeima.py` (-doc creation), `src/db.py` (Optional document_id), `scripts/migrate_saeima_doc_cleanup.py` (new), `tests/test_ingest.py` (+11 tests TestExtractPublishedAt), `tests/test_db.py` (+2 tests for null document_id), `tests/test_migrate_saeima_doc_cleanup.py` (new, 5 tests). 18 jauni testi visi zaļi, 631 kopā passed.

**Out of scope (follow-ups):**
- Vēsturisks pub_at backfill 2934 esošajiem web docs (vajadzētu re-fetch katru URL, paywall risks). Atstāts, jo jaunie scrape no šī brīža darbojas — vēsturiskā metadata nav kritiska.
- LETA pub_at — paywall, nav meta tagu uz publiskās lapas. Atstājam None, jo viņu saturs jau zaudēts cita iemeslā.
- `topics` tabula (Solis 2 plānā) — first-class entitīsis ar slug/description/icon kā pamats nākotnes /temas/ lapām.
- `tracked_politicians.slug` kolonna (Solis 3) — DB-stable slug vietā derive-no-name.

---

## 2026-04-25 — Commentator demotion + profila X subtaba

**What changed:**
- 7 vēsturiskie komentētāji (pid 62 Svirskis, 169 Klucis, 171 @Heinrih5, 172 @Tuksumsz, 174 Lūsis, 175 @Kurmitis_, 177 @PStrautins) demotēti no `tracked_politicians.relationship_type='commentator'` uz `'inactive'`, un to 8 `social_accounts` rindas (Svirskim divas) pārveidotas no `feed_type='first_party'` uz `'relay'`. Tas aizver "ghost profila" antishablonu — komentētāji bija politiķi-skeleti, bet to lapas netika ģenerētas.
- Migrācijas skripts `scripts/migrate_commentator_demotion.py` (idempotents, ar testiem). Re-link `scripts/relink_commentator_documents.py` izdzēsa 366 vēsturiskus `role='subject'` linkus un palaida `link_politicians_to_documents(rescan_all=True)` lai matcher tekstu skenētu un atrastu pareizos mentioned politiķus.
- **Matcher uzlabojums:** pievienots `_latvian_surname_inflections()` `src/ingest.py`, kas ģenerē Latvijas deklināciju formas (gen/dat/acc) 4 visbiežākajiem -is/-s/-š/-ņš/-a/-e galotnēm. Atrisina silenta matcher misses tipa "Lūgums sižetus Melnim" → tagad matcher pareizi atrod Melnis (157). Palatalizācija (n→ņ utt.) tikai genitīvā. Additīvi savieto ar `name_forms` no DB.
- **Politiķa profila lapā jauna X subtaba** (`templates/politician.html.j2` + `_fetch_politician_detail` x_posts query): rāda visus twitter+x_mention dokumentus, kuros politiķis linkots, sakārtotus pēc published_at DESC, līdz 50 ierakstiem. Aizvieto zaudēto comment claims pipeline ar plašāku raw mentions plūsmu.
- **Komentāri subtabas intro paskaidrojums** — pievienots, ka šī sadaļa tagad rāda tikai vēsturisko datu (pirms 2026-04-25), aktuālie pieminējumi X subtabā.

**Why:** Commentator-as-politician modelis radīja datu modeļa antišuvi — 4 izteiksmīgi komentētāji bija pirmā klases tracked entītes, bet viņu profila lapas netika ģenerētas (relationship_type filtrs `src/generate.py:392`), kamēr 175+ citi mentions ikdienā palika kā raw documents bez profila redzamības. Demotēšana saliek vienotu modeli: politiķi ir tracked, visi pārējie X handles ir vai nu ielādes avoti (relay social_accounts) vai jēli mentions (x_mention dokumenti). Profila X subtaba dod vienotu lasītāja skatu uz visu X saturu, kas attiecas uz konkrēto politiķi.

**Esošās 9 commentary claims (pirms 2026-04-25)** paliek DB ar `speaker_id` FK valid (commentator pid joprojām eksistē, tikai `relationship_type='inactive'`). Jaunas commentary claims vairs netiek ģenerētas. Komentāri subtabas count gradually trends to 0 kā 90-d. window apzilst.

**Plāns un izpilde:** `docs/superpowers/plans/2026-04-25-commentator-demotion.md`. Commits: 6212b17 (audit baseline), a3b4a14 (migrate), 0465d39 (relink), a027b78 (declension fix), 6209957 (x_posts fetcher), 36e9d1e (X subtab UI), 8e00bf7 (Komentāri intro).

**Fāze 2 (1-2 mēn):** Kad X subtaba būs piepildījusies ar reāliem datiem, pievienot pithiness ranking (pithy commentary extraction) — automātiski izcelt 5-10 visizteiksmīgākos tvītus mēnesī. Tas funkcionāli aizvietos veco operatorkurēto commentary pipeline ar plašāku datu bāzi.

---

## 2026-04-25 — `social_accounts` → X-only + `external_profiles` tabula

**What changed:**
- Jauna tabula `external_profiles` (src/db.py, init_db bloks) glabā ne-X politiķu profilus: Facebook (19), website (6), un nākotnē citus (YouTube, Instagram). Schēma paralēla `social_accounts` + papildus `url` lauks; fetch-ready (`last_fetched`, `last_post_id`, `active`), bet pagaidām bez fetcher koda — tikai UI display.
- `social_accounts` no šī brīža satur tikai X kontus. UNIQUE indekss `idx_social_accounts_unique` uz `(opponent_id, platform, handle)` novērš literālus dublikātus.
- Migrācijas skripts `scripts/migrate_external_profiles.py` idempotenti pārvieto 19 FB + 6 website rindas uz `external_profiles`, reklasificē `realNepareizais` (id=62) uz `relationship_type='commentator'` (analogs Kļuciņam), un `KNL_LTV1` (id=59) uz `relationship_type='journalist'` + `feed_type='relay'` (analogs LTV Ziņas pattern).

**Why:**
- 2026-04-25 audits atklāja, ka `social_accounts` bija piesārņota: 18 FB rindas + 5 website (URL piebāzti `handle` kolonnā) + 2 literāli X dublikāti, visas `NULL last_fetched` (nekad nav fetchotas). `social.py` un `x_mentions.py` jau filtrē `WHERE platform='twitter'`, tāpēc FB/website rindas bija tikai konfigurācijas atkritumi. Problēma: nākamais Claude varētu tos pievienot atpakaļ, neapzinoties X-only konvenciju.
- Sākotnēji šķita, ka `AinarsSlesers ×2` un `suvajevs ×2` ir X dublikāti — patiesībā tie bija X+FB pāri ar identiskiem handle (vienādais vanity name abās platformās). Migrācijas dedupe solis pareizi nekustina ne vienu (jau atsevišķas platform='twitter' un 'facebook' rindas). FB rindas `_migrate_facebook_rows` pareizi pārceļ uz external_profiles.
- `realNepareizais` un `KNL_LTV1` bija `relationship_type='inactive'`, kas slēpa tos no dashboard. Nepareizais ir trešpuses komentētājs (ekvivalents Kļuciņam), ne inaktīvs politiķis. KNL ir ziņu raidījums ar X kontu, kas post-hoc matcher pattern tiešām ir `feed_type='relay'` (sk. 2026-04-23 `ltvzinas`).

**Backward compatibility:**
- Tīri forward-only migrācija. `social.py::_store_tweets` un `x_mentions.py::fetch_mentions` jau filtrē `platform='twitter'` — nekādu behavior changes.
- `_fetch_politician_detail` un politiķa template paplašināti, lai parādītu `external_profiles` ikonas (FB + website) blakus X handle ikonai. Ja external_profiles tukša politiķim, profile-links div paliek kā iepriekš.
- Migrācija veikta vienā SQLite transakcijā; neveiksme → rollback, DB paliek nemainīga. Backup: `data/atmina_backup_pre_external_profiles.db`.

**Invariants added:**
- `social_accounts` = tikai X kontu datu ieraksti, viens uz politiķi (UNIQUE `(opponent_id, platform, handle)`). FB/website/citi → `external_profiles`. Dokumentēts `CLAUDE.md §12` prefiksā.
- Migrācija idempotenta: `INSERT OR IGNORE` pret UNIQUE(opponent_id, platform, url) external_profiles tabulā + guarded UPDATE (`WHERE current != target`) pret reklasifikāciju. Otrā palaišana atgriež visas nulles / False.

**Files:** `src/db.py` (external_profiles schema), `src/generate.py` (profile detail + render context), `templates/politician.html.j2` (FB + website icons), `scripts/migrate_external_profiles.py` (new), `tests/test_db.py` (2 new), `tests/test_migrate_external_profiles.py` (new, 6 tests), `tests/test_generate.py` (1 new), `CLAUDE.md` (§12 prefix).

**See also:** [§ `social_accounts.feed_type`](#2026-04-23--social_accountsfeed_type-relay-vs-first_party) — `feed_type` klasifikators paliek nemainīgs (`'first_party'` vs `'relay'`), tikai tabulas tvērums šaurāks.

**Out of scope (follow-ups):** FB/website fetcher implementācija (pagaidām tikai UI display). `commentator_weight` lauks, lai dampenētu skaļus komentētājus profila feed'ā — ievedīsim, kad būs 4+ tracked commentators (patreiz 2: Kļuciņš + Nepareizais).

---

## 2026-04-23 — Matcher role integrity + diacritic validator fixes

**What changed:**
- `src/social.py::_store_tweets` now assigns `role='subject'` only when the tweet's source_url author matches the politician's registered twitter handles; mismatch or unresolvable URL → `role='mentioned'`. Mirrors exactly the 2026-04-20 fix pattern that was applied only to the post-hoc scanner path.
- `src/quality.py::validate_lv_diacritics` adds a fasttext primary language-ID early-exit (`lang in {en, ru, de, fr, es, pl, it} and conf >= 0.70 → True`), extends `EN_MARKERS` with ~45 common tokens that were missed (`at`, `more`, `already`, `six`, `times`, `remain`, `fall`, etc.), and adds `logging.warning` on rejections for future observability.
- `scripts/fix_subject_role_leakage.py` one-shot idempotent backfill resolved 83 mismatched junction rows: 70 UPDATE (`subject`→`mentioned`), 13 DELETE (mentioned row already existed, UNIQUE constraint blocked straight UPDATE). Claim audit flagged 4 pre-existing claims (#11273, #11226, #11318, #11229) on now-downgraded junction rows for manual editorial review — no auto-delete.

**Why:**
- Matcher: The 2026-04-20 fix patched `src/ingest.py::link_politicians_to_documents` but NOT `src/social.py::_store_tweets`. The live-fetch path continued hardcoding `subject` on every tweet, including retweets/quote-tweets/replies that twikit normalises to the ORIGINAL author's source_url. 83 rows accumulated between 2026-04-21 and 2026-04-23 before detection during today's Komentētāji extraction run.
- Diacritic: M. Krusts English-language tweet quote was rejected because `LV_STOPWORDS` includes `to` and `EN_MARKERS` missed common counter-tokens. Agent had to drop the `quote` field to save the claim — lossy. Fix preserves stripped-LV detection via fallback-to-token-matcher design (fasttext misclassifies stripped LV as `fr`/`sr` at low confidence, so the 0.70 threshold keeps guardrail intact).

**Backward compatibility:**
- Matcher fix is forward-only; existing `mentioned` and `subject` semantics unchanged. Backfill downgrades preserved linkage metadata (UPDATE) or removed redundancy (DELETE when duplicate `mentioned` existed).
- Diacritic fix is additive: fasttext early-exit ADDS an accept path, EN_MARKERS expansion ADDS tokens. No existing acceptance path removed. Stripped-LV rejection path preserved unchanged (tested via `test_stripped_latvian_still_rejected_despite_fasttext_drift`). `logger.warning` adds observability with no behavior change.

**Invariants added:**
- `_store_tweets` role assignment now requires `source_url` author to be in `social_accounts.handle` set (case-insensitive, any `active` state) for `role='subject'`. Symmetric with `scripts/fix_subject_role_leakage.py` backfill. YouTube/Facebook sibling fetchers in same file still hardcode `subject` — acceptable because those platforms don't surface other authors via user timelines the same way twikit does.
- Backfill is idempotent by construction: `WHERE role='subject' AND handle_mismatch` means re-runs find nothing after the first pass.

**Files:** `src/social.py`, `src/quality.py`, `scripts/fix_subject_role_leakage.py`, `tests/test_social.py` (new, 3 tests), `tests/test_quality.py` (4 new tests).

**See also:** [§ `social_accounts.feed_type`](#2026-04-23--social_accountsfeed_type-relay-vs-first_party) — same `_store_tweets` function covers a different code branch (relay accounts skip the per-tweet handle match entirely).

**Out of scope (follow-ups):** `match_politicians(text)` content-scan enrichment in `_store_tweets` for multi-politician mentions. `published_at` backfill for 55% NULL web docs. `print_routine()` heuristic distinguishing "quiet user" (last_fetched today, last_post_id stale) from "scraper broken" (not fetched in Nd). Explicit `language='en'` kwarg on `store_claim` for agents that already know the quote is English.

---

## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

**What changed:** Added `social_accounts.feed_type TEXT DEFAULT 'first_party'` column (values: `first_party` | `relay`) plus `idx_social_feed_type` index. Institutional media X accounts (first seed: LTV Ziņas `@ltvzinas`; future: Delfi, TVNET, LSM, ministriju konti) now ingest as `feed_type='relay'`. Two pipeline branches read the flag:

- `src/social.py::_store_tweets` — when `feed_type='relay'`, skips the per-tweet handle-match path entirely; documents are inserted with empty `politician_links`. For `first_party` accounts the matcher entry above (per-tweet handle match → subject/mentioned) still applies.
- `src/ingest.py::link_politicians_to_documents` — precomputes `relay_handles` from social_accounts rows with `feed_type='relay'`; when a Twitter doc's URL author is a relay handle, quoted tracked politicians keep their `subject` role instead of being downgraded to `'mentioned'`. Quoted speakers therefore reach the normal extraction queue via `get_pending_politicians()`.

**Why:** Before this, `_store_tweets` unconditionally marked the account owner as `subject` of their own tweet. For politicians posting their own X content this is correct (author IS the speaker). For a news-relay account like LTV Ziņas it is wrong: LTV's tweets quote third parties (e.g. *"sacīja deputāts Edvards Smiltēns"*), so the *quoted politician* should be the subject. Under the pre-change pipeline, quoted politicians got `role='mentioned'` and never entered their own extraction queue; LTV entered its own queue with its own tweets, and the claim-extractor would attempt to extract LTV's "first-party positions" from relayed quotes — semantically wrong and invisible to first-party contradiction detection.

**Pipeline effect for a relay-sourced claim:** `opponent_id = quoted politician`, `speaker_id = NULL` (first-party), `claim_type = 'position'`, `source_url = LTV tweet URL`. `search_similar_claims` (default `speaker_scope='first_party'`) correctly contradicts these against the politician's direct posts.

**Backward compatibility:** Default `'first_party'` preserves all existing account behavior. Politicians' own X accounts, commentators (KlucisD), and individual-journalist accounts (Lato Lapsa) are unchanged. The `relationship_type='commentator'` commentary path (added earlier today) fires independently of `feed_type` and is unaffected.

**Files:** `src/db.py` (init_db schema patch + index), `src/social.py` (`_store_tweets` feed_type lookup + conditional link), `src/ingest.py` (`link_politicians_to_documents` precomputes `relay_handles`, adds guard clause on downgrade elif), `scripts/seed_media_sources.py` (MEDIA_SOURCES with `feed_type='relay'` + UPSERT-on-differ for existing rows), `tests/test_db.py` (column-present + idempotency, both with index assertion), `tests/test_ingest.py` (first-party regression guard + relay skip link + relay author keeps quoted politician as subject).

**See also:** [§ Matcher role integrity](#2026-04-23--matcher-role-integrity--diacritic-validator-fixes) — `first_party` accounts take the per-tweet handle-match branch of the same `_store_tweets` function; `relay` accounts skip that branch entirely.

**Operational:** 17 pre-patch LTV-subject junction rows (from an earlier manual fetch test) deleted; `link_politicians_to_documents(rescan_all=True, days=7)` re-evaluated them under the relay logic. Three docs correctly re-assigned (Smiltēns, Butāns, Čakša → subject). LTV Ziņas removed from `get_pending_politicians()` queue.

**Matcher hygiene (related but separate):** While auditing, discovered `match_politicians` was producing false-positive `LTV Ziņas:subject` links on news articles that mentioned the Latvian word `ziņas` ("news") — e.g. `plašsaziņas` and the brand `360 Ziņas`. Added `negative_patterns=["plašsaziņas", "360 Ziņas", "360 ziņas"]` to `tracked_politicians.id=170`. This is a name-collision symptom similar to the 2026-04-20 Andris Bērziņš case; if more relay media accounts are seeded with similarly generic tokens, a matcher-level filter that skips relay-type entities during text-scan may be worth considering.

**Out of scope (follow-ups):** Dedicated UI "Mediju avoti" grouping separate from individual "Žurnālisti"; retweet filtering at fetch time (`_store_tweets` currently stores `RT @...` posts but truncated text rarely matches politicians, so they quietly sit with no junctions); auto-detect relay from account metadata.

---

## 2026-04-23 — Komentētāji (speaker_id on claims)

**What changed:** Added `claims.speaker_id INTEGER NULL` column to distinguish authors from subjects. Introduced `relationship_type='commentator'` for non-politician public commentators (KlucisD seeded) and `claim_type='commentary'` for their output. Third-party commentary now renders on politician profiles as a dedicated "Komentāri" tab with explicit speaker attribution.

**Why:** Before this, a commentator tweeting "Pūpols ir korumpēts" either got dropped by the indirect-reference gate or misattributed as Pūpols' own position. Neither was right — the content is editorially valuable (third-party allegations are a legitimate transparency signal) but legally requires "X apgalvo par Y" framing, not assertion-of-fact. The `speaker_id` column is the minimum architectural change that enables correct attribution.

**Backward compatibility:** `speaker_id IS NULL` = first-party (legacy default). All pre-2026-04-23 claims remain NULL; readers use `COALESCE(speaker_id, opponent_id)` or explicit `IS NULL OR speaker_id = opponent_id` filters. `store_claim` signature adds optional `speaker_id` kwarg (default None).

**Invariant added:** `search_similar_claims` defaults to `speaker_scope='first_party'` — commentary claims are excluded from contradiction-candidate matching by default, so "Pūpols contradicted himself" never mis-fires because the second claim was actually a commentator writing about him.

**Files:** `src/db.py` (schema + store_claim + search_similar_claims), `src/tools.py` (pydantic wrapper plumbing), `src/analyze.py` (save_analysis plumbing), `src/generate.py` (_fetch_commentary_about + politician-listing filter + profile context), `templates/politician.html.j2` (new Komentāri tab + stat button), `assets/style.css` (`.komentari-*` block), `.claude/agents/claim-extractor.md` + `.claude/agents/contradiction-hunter.md` (prompt updates — ungitignored, on-disk only), `scripts/seed_commentators.py` (KlucisD seed).

**Out of scope (follow-ups):** Reply-tree capture under tracked politicians' posts; `/komentetaji/` index page in main nav; commentator-vs-commentator contradiction tracking.

---

## 2026-04-22 — claim-extractor batch-drift fixes

Diagnostika (sk. `data/autoresearch/DIAGNOSTIC_SUMMARY.md`) pārbaudīja divas hipotētiskās kļūdas:

- **`stated_at` = scrape-date, nevis `document.published_at`** → **nav aktuāla kļūda.** 365/365 claims pēdējā 30 dienu logā ar pub ≠ created (≥2 d atstarpe) pareizi seko `published_at`. 2026-04-21 retroaktīvais labojums + pašreizējais prompt to apstrādā pareizi.
- **Indirect-reference saves** → **reāla kļūda, bet izolētā prompt darbojas pareizi.** 33 production-saved dokumenti testēti neitrālā viena-doc eval — izolētais extractor noraida 18 no 20 šaubīgajiem kā `empty`/`skip`. Piekrīt 13 likumīgajiem saglabājumiem. Kļūda ir batch-mode context drift.

**Labojumi (šī commit):**

1. `.claude/agents/claim-extractor.md` — circuit breaker 33 → 12 dokumenti uz politiķi/sesiju. Pievienots self-check: pirms katra `save_analysis` pārlasa savu `reasoning`, ja tā atzīst "nav paša pozīcija / pašam nav ekstraktējamas / bare RT / pure retweet / does not speak / tikai pieminē" → atgriež `empty`.
2. `src/analyze.py` — soft indirect-reference gate `save_analysis`. Ja reasoning satur stiprus indirect markerus, prepend `NEEDS_REVIEW:` marķieris (nevis nomet claim — "netiešs citāts caur LETA" ir likumīgs un netiek skarts). `@quality-reviewer` triāžē NEEDS_REVIEW ierakstus. Pilnā markieru saraksta: `_INDIRECT_MARKERS_LOWER` tuple.
3. Operatora vadlīnija: > 5 docs/politiķi → dispečē pa vienam sub-aģentam ar atsevišķu kontekstu (fan-out), nevis viens sub-aģents daudzdoc režīmā.

**Artifacti:**
- `data/autoresearch/DIAGNOSTIC_SUMMARY.md` — pilnā diagnostika
- `data/autoresearch/round1_results.md`, `round1_batch.json`, `hard_batch.json`, `indirect_flagged_docs.json`, `dryrun_seed.json`
- `data/backups/atmina_2026-04-22-autoresearch-pre.db` — pirms-work DB backup

**Testi:** `tests/test_analyze.py::TestIndirectReferenceGate` (4 testi) — marker detection hits/misses + integration test pret `save_analysis`.

---

## 2026-04-17 — Diacritic validation

`save_analysis()` un `store_claim()` validē, ka `stance`, `quote`, `reasoning` un `brief_markdown` saglabā latviešu garumzīmes (āēīūņļķģšžč). Stripped teksts tiek atraidīts (sk. `src/quality.py`).

**Signāls operatoram:** ja redzi "diacritic validation failed" — tas ir context drift. Nekavējoties STOP un sāc jaunu sesiju. Drift ir autoregresīvs — turpināšana vienā sesijā pasliktinās.

**Praktiska robeža:** ~8 politiķi vienā sesijā maksimums. 2026-04-16 incidents rādīja kvalitātes kritumu pēc 8 secīgiem extractions. Validācija `src/quality.py` noraida stripped tekstu jau `save_analysis()` / `store_claim()` līmenī — papildu post-hoc skenēšana nav vajadzīga.

---

## 2026-04-11 — claim_type split (`position` vs `saeima_vote`)

`claims` tabula tagad nošķir divus tipus:

- **`position`** — mediju/X first-person retorika (default)
- **`saeima_vote`** — Saeimas balsojumu ieraksti, auto-tagged ar `generate_claims_from_votes()`

**Kāpēc:** "pozīciju" skaits iepriekš apvienoja abus un izskatījās 8× lielāks par faktisko retorisko aktivitāti. Skaitļi nav mazāki — tie ir pārklasificēti.

**Praktiskie noteikumi:**
- `@claim-extractor` nekad nepārraksta default — tas vienmēr ražo `position`
- Visi readeri (`wiki.py`, `briefs.py`, `generate.py`) filtrē pēc `claim_type`, nevis pēc `source_url LIKE '%saeima%'` heiristikas
- Rhetoric-vs-action retrieval caur `search_similar_claims(claim_type_filter=...)` strādā directionally per call-site:
  - `position` viedoklis → kandidāti iekļauj abus tipus
  - `saeima_vote` viedoklis → kandidāti iekļauj tikai `['position']` (vote-vs-vote ir procesuāls troksnis)
  - Vispārēja līdzīguma meklēšana → `None`

---

## 2026-04-11 — `save_analysis` atomicity (S10)

Pilna analīze + claims + reviewed-docs update iet **vienā SQLite transakcijā**.

- Katastrofāls DB write failure (disk full, lock timeout) → `status="failed"` ar `transaction_rolled_back` un pilnībā atceļ izmaiņas
- Validation-level skips (missing source_url, inactive politician) → `status="partial"` bez rollback (loģiski drops, ne state korupcija)

**Saistīta izmaiņa:** kontradikcijas vairs netiek automātiski salīdzinātas no `save_analysis`. Analītiķis manuāli izsauc `search_similar_claims(claim_type_filter=...)` un `store_contradiction`, kad atrod reālu pretrunu.

---

## 2026-04-11 — Coalition classification `parties.coalition_status`

Autoritatīvais truth source koalīcijas statusam ir `parties.coalition_status` kolonna (nav hardkodēts saraksts).

**Vērtības:** `coalition` | `opposition` | `not_in_saeima`

**Lasīt caur:**
- `src.coalition.get_coalition_map(db)` → `{partijas_nosaukums_vai_īsais_nosaukums: status}` (batch — izmanto, kad klasificē daudzas rindas)
- `src.coalition.party_status(party)` — single lookup

**Nekad** nelietot `tracked_politicians.relationship_type` koalīcijas loģikai — tas ir legacy per-politician tracking role bez koalīcijas semantikas.

**Pēc 2026-04-11 `relationship_type` saglabā nozīmi tikai šīm vērtībām:**

| Vērtība | Nozīme |
|---|---|
| `inactive` | Paslēpts no dashboard |
| `journalist` / `influencer` / `neutral` | Audience accounts — izslēgti no brief leaderboards |
| `tracked` | Aktīvs default |

Legacy vērtības `opponent`, `coalition_partner`, `potential_ally` migrētas uz `tracked`.
