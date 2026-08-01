# Komandas

Atskaites punkts visām CLI/REPL komandām. CLAUDE.md tikai uzrāda divas obligātās (`check.sh` + `print_routine`); pārējās — šeit.

## Verifikācija un pirmsizpilde

```bash
.venv/Scripts/activate                    # Windows venv aktivācija
bash scripts/check.sh                     # Refactor safety net: ruff + pytest + generate_public_site smoke
.venv/Scripts/python.exe -m pytest tests/ -v                # Pilna testu paka
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"   # Rutīnas statuss
```

> **Vienmēr `.venv/Scripts/python.exe`, nekad kails `python`.** Uz šīs mašīnas `python` PATH-ā aizved uz svešu vidi (`%LOCALAPPDATA%\hermes\hermes-agent\venv`, ielikta lietotāja pastāvīgajā PATH), un tālāk aiz tās ir tikai neesoši Python 3.10 ceļi un Microsoft Store aizbāznis. Projekta vide ir Python 3.12. Sliktākais scenārijs nav "komanda nestrādā", bet daļēja rakstīšana: `store_vote()` commit-o pirms claim ģenerēšanas, tāpēc svešā vidē balsojumi nonāk DB, bet claims krīt (2026-07-25, 20 rindas). Rakstošie skripti tagad to notver ar `ensure_embeddings_live()`, bet vārti nav visur. `scripts/check.sh` un `deploy.sh` paši atrod `.venv`, tāpēc tos drīkst saukt tieši.

`scripts/check.sh` ir vienīgā kombinētā verifikācija — jāizpilda pirms commit ar src/* izmaiņām. Skat. [CHANGELOG 2026-04-29](../CHANGELOG.md) par `generate_public_site` smoke iekļaušanu.

> **Nelasi `check.sh` iznākumu caur `| tail`.** Konveijera izejas kods ir PĒDĒJĀS komandas kods, tāpēc `bash scripts/check.sh | tail -25` atgriež `tail` nulli arī tad, kad pytest ir kritis — un izvads izskatās mierīgs, jo kritušā testa rinda paliek augstāk par apgriezto logu. 2026-08-16 tas noslēpa vienu krišanu veselu soli. Droši: `bash scripts/check.sh > /tmp/check.log 2>&1; echo $?` un tad grep pa logu.

> **HTML/live satura zondes raksti Python pusē, ne ar PowerShell `-match`.** `Get-Content -Raw` un `Invoke-WebRequest ... -match` uz šīs mašīnas dekodē UTF-8 kā ANSI, tāpēc KATRA latviskā zonde krīt (diakritika sabojāta), kamēr ASCII zonde tajā pašā izsaukumā trāpa — iznākums izskatās kā „saturs daļēji trūkst", nevis kā kodējuma kļūda. 2026-08-16 tas lika nolasīt jau publicētu sintēzi kā novecojušu un uzsākt lieku deploy izmeklēšanu. Zondei lieto `.venv/Scripts/python.exe` ar `io.open(..., encoding="utf-8")` vai `urllib` + `.decode("utf-8")`.

## Statiskās vietnes ģenerēšana

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

Pilns render ~3 min (169 s pēc 2026-05-29 `idx_claims_document_id` fix; agrāk `render_news` iekārās ~16 min — sk. CHANGELOG 2026-05-29). Kanoniskais ceļš pēc F3g refaktora ir augstāk parādītais `src.render` imports. `src.generate` ir re-export shim, neizmanto jaunā kodā.

### Narrow render (`--only` flag, ~30s – 2 min)

Šauram lapu apjomam izmanto **`.venv/Scripts/python.exe -m src.render --only=DOMAIN1,DOMAIN2`** — fetcē visus DB datus, bet izsauc tikai uzskaitītos `render_X` blokus. Ietaupa lielāko daļu no ~3 min pilnā render (lēnākie posmi: `render_links` ~46 s + `render_politicians` ~60 s), kad maini tikai dažas lapas.

```bash
.venv/Scripts/python.exe -m src.render --list-domains    # 19 valid domain names
.venv/Scripts/python.exe -m src.render --only=DOMAIN,...
.venv/Scripts/python.exe -m src.render                    # bez --only = pilns render
```

**Minimālais scope pa izmaiņas tipam:**

| Izmaiņa | `--only=` argumenti | Cena |
|---|---|---|
| Jauns daily_brief / weekly_brief saglabāts | `dashboard,blog,static` | ~35s |
| `parties.coalition_status` flip | `partijas,personas,balsojumi,pretrunas,pozicijas,dashboard` | ~1 min |
| Jauna sintēze vai analīze saglabāta | `sintezes,analizes,dashboard` | ~30s |
| Tikai jauni Saeimas balsojumi | `balsojumi` (vai `scripts/render_balsojumi_only.py`) | ~15-30s |
| Politikim pievienoti jauni claims/pretrunas | `pretrunas,pozicijas,dashboard,politiki,blog` | ~1-2 min (`render_politicians` ~60 s) |
| Tikai static (about/kontakti/404/sitemap) | `static` | ~5s |

> **`static` ir jāiet līdzi katram dienas renderim (2026-08-01).** `about.html` skaitļus (politiķi / dokumenti / spriedzes) un `sitemap.xml` ģenerē TIKAI `static` domēns, tāpēc `dashboard,blog` recepte tos atstāja novecojušus starp pilnajiem renderiem: 08-01 audits atrada `about.html` no 07-29 ar `191 politiķi / 63 064 dokumenti / 156 spriedzes`, kamēr DB bija 193 / 65 290 / 161, un `sitemap.xml` bez trim pēdējiem pārskatiem un diviem jaunajiem profiliem. Tā ir nepareiza informācija tieši tajā lapā, ko pirmreizējs apmeklētājs lasa, lai izlemtu, vai platformai ticēt. Cena ~5 s — nav iemesla to izlaist.

CLI implementācija un `KNOWN_DOMAINS` saraksts: `src/render/__main__.py` + `src/render/_orchestrator.py:KNOWN_DOMAINS`.

**Noteikums:** pirms renderēšanas nosaki tvērumu un lieto `--only=DOMAIN`. Pilns renders ir tikai laidienam vai bāzlīnijai — citādi tas maksā minūtes un pārraksta lapas, kuras neviens nav mainījis.

> **Meklēšanas ieteikumu sidecars:** `data/sg-index.json` (+`.br`/`.gz`) — sākumlapas typeahead indekss (`src/render/search_index.py`, lasa `assets/sgv1.js`). To atsvaidzina gan `dashboard`, gan `pozicijas` domēns, tāpēc dienas rutīnas narrow renderi to nekad neatstāj novecojušu. Tuple-shēma ir load-bearing — sk. [CHANGELOG § sg-index](../CHANGELOG.md).

`scripts/render_balsojumi_only.py` ir vēl ātrāks (~15s) tikai balsojumiem — neaktīvē politicians/claims/contradictions fetches.

## Lokālais dashboard

```bash
.venv/Scripts/python.exe serve.py     # http://127.0.0.1:8080
```

Operatora dashboard — 5 paneliišas (brief / rutīna / X slot health / A/B stratēģija / ekstrakcijas backlog) + aktivitātes timeline. Localhost only (bind cietkods uz 127.0.0.1). Pilns runbook: [atmina-ops.md](atmina-ops.md).

## Publicēšana uz Namecheap

```bash
bash scripts/deploy.sh --dry-run --no-delete   # Preview rsync
bash scripts/deploy.sh --no-delete             # Faktiska deploy (standing mode — nekad bez --no-delete)
```

**Publicēšanas atļauja (T15 vārti).** Deploy preflight prasa katrai `blog/` pārskata lapai divus faktus: apstiprinātu attēlu DB **un** eksplicītu operatora atļauju. Atļauju ieraksta pēc korektūras, tieši pirms deploy:

```bash
.venv/Scripts/python.exe scripts/approve_publish.py 2026-08-18            # dienas pārskats
.venv/Scripts/python.exe scripts/approve_publish.py nedela-2026-08-10     # nedēļas pārskats
.venv/Scripts/python.exe scripts/approve_publish.py 2026-08-18 --revoke   # atsaukt
.venv/Scripts/python.exe scripts/approve_publish.py --list                # pēdējie 10
```

Atslēga ir blog lapas slugs (fails bez `.html`), tāpēc atļauja pārdzīvo brief pārģenerēšanu. Bez rindas `scripts/check_output.py --publish-gate-only` atgriež 1 un deploy apstājas — tas ir vārts pret melnraksta aizbraukšanu (2026-08-09 incidents), nevis formalitāte.

Pilns runbook: [deploy.md](deploy.md).

## Social agent (X/Twitter draftu plūsma)

```bash
.venv/Scripts/python.exe -m src.social_agent brainstorm                  # Top 3 drafti uz Telegram
.venv/Scripts/python.exe -m src.social_agent approve|skip|revise|resend <draft_id>
```

Pilns runbook: [social-agent.md](social-agent.md).

## Brief / thread attēli (CLI)

Kanoniskais attēlu rīks — aizstāj per-dienas vienreizējos skriptus (vecie pārvietoti uz `scripts/_scratch/`, gitignored). `@graphics-designer` izlemj metaforu/promptus; CLI dara mehāniku.

```bash
# Brief plakāts (Economist stils, headline image-ā; build_prompt + audits + budget + approval gate approved=0):
.venv/Scripts/python -m src.graphics.cli brief --note-id N [--metaphor "..."] [--mood "..."] [--accent "..."]

# Tvītu pavediena sepia attēli (text-free, kanoniskā SEPIA_STYLE; bez DB):
.venv/Scripts/python -m src.graphics.cli thread --date 2026-06-06 --prompts thread.json
```

`thread.json` = `{"1-lead": "metaforas prompts...", "2-valdiba": "..."}` → `output/images/threads/{date}-thread-{suffix}.png`. `brief --metaphor` pārraksta ģenērisko `visual_map` (house-style `metaphor_hint`). Pēc brief: review PNG → `approve_image` → narrow render → `deploy.sh --no-delete`.

> **NB:** `cli brief` raksta tikai pamata PNG (+ DB audita rindu) — tas **neemitē** WebP variantus (hero/card/thumb). Variantus backfill render solī, vai palaid `src.image_variants.make_variants(out_path)`, ja vajadzīgi uzreiz.

## Pārklājuma audits (read-only)

```bash
.venv/Scripts/python scripts/coverage_report.py [--db data/atmina.db]
```

Uzskaita tracked politiķus bez kanāla, caur ko pozīcijas/pretrunas varētu parādīties: **tumšā zona** (Saeimas balsojumi izsekoti, bet 0 analyses + 0 position claim + 0 X feed → pretruna nevar rasties; P4 mērķis), bez X feed, nekad analizēti, bez position claims. Tā pati metrika dzīvo `print_routine()` izvades beigās kā info rinda. Stale-pol sarakstu (deep-check higiēnai) dod `src.coverage.stale_pol_politicians()`.

## Manuālie ingest skripti

```bash
.venv/Scripts/python.exe scripts/ingest_vestnesis.py [--limit N] [--dry-run] [--max-age-days D]
.venv/Scripts/python.exe scripts/ingest_vad_declarations.py [--politician X] [--limit N] [--dry-run]
```

Vēstnesis JL un VID amatpersonu deklarācijas — abi manuāli, idempotenti. Detaļas: [operacijas.md](operacijas.md).

## Saeimas pilnīguma audits un robu ielāde

```bash
# 1. Kas trūkst (tikai lasa, neko neraksta)
.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year 2025 --out data/parity_2025.json
.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year 2025 --dates 2025-04-10,2025-12-11

# 2. Trūkstošo ielāde (sausā palaide pēc noklusējuma)
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json \
    --dates 2025-04-10 --apply --rollback-out data/rollback_saeima_missing_votes_2026-07-25.sql

# 3. Ja claim solis kritis pusceļā (balsojumi DB, claims nav)
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --repair-claims --dates 2025-04-10 --apply
```

Audits salīdzina darba kārtību ar DB pēc **`(vote_date, vote_time)`, nevis URL** — titania pārarhivē balsojumu lapas ar jauniem UNID, tāpēc `store_vote()` URL-dedup kļūst akls. Tā paša iemesla dēļ **nelieto `p3_backfill_year_urllib.py --year N` robu aizpildīšanai**: akls gada palaidiens ražotu dublikātus, ne aizpildītu robus.

`--apply` prasa `--rollback-out` un pirms pirmās rakstīšanas izsauc `ensure_embeddings_live()` — bez darboša embedding steka `store_vote()` paspētu ierakstīt balsojumus, un claim solis kristu aiz tiem. Palaid ar `.venv/Scripts/python.exe`, nevis kailu `python`.

Vēsture un 2025. gada rezultāti: [CHANGELOG](../CHANGELOG.md), atlikušais darbs: `BACKLOG.md`.

## Datu higiēnas migrācijas

```bash
.venv/Scripts/python.exe scripts/fix_purge_registration_claims_2026-07-25.py
.venv/Scripts/python.exe scripts/fix_purge_registration_claims_2026-07-25.py --apply \
    --backup data/atmina.db.pre-registration-claims-purge-20260725.db
```

Dzēš claims, kas ģenerēti no klātbūtnes procedūrām (`Deputātu klātbūtnes reģistrācija`, `Kvoruma pārbaude`) — tās nav balsojumi. Vienreizējs (2026-07-25, 30 476 rindas); uz priekšu to novērš vārti `generate_claims_from_votes()`. `--apply` prasa jau eksistējošu DB kopiju un apstājas, ja atlasē trāpās kaut viena `claim_type='position'` rinda.

## Diagnostika

```bash
.venv/Scripts/python.exe scripts/probe_x_cookies.py        # Visi 4 X endpoints per cookie slot
.venv/Scripts/python.exe scripts/patch_twikit.py           # Atjauno twikit lokālos patches
```

Skat. [twikit-notes.md](twikit-notes.md) par patch arhitektūru un 2026-04-29 SearchTimeline 404 incidentu.

## Video ingest

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch <url|path> [--slug NAME]
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize <slug>
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest status <slug>
```

Pilns 4-fāzu runbook: [operacijas.md § Video ingest](operacijas.md).
