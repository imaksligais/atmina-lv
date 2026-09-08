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
>
> **Un kopš 2026-08-27 tas vairs nav tikai piezīme.** Šī brīdinājuma pirmā redakcija nepalīdzēja: 08-27 tā pati forma (`bash scripts/check.sh 2>&1 | tail -14`) VĒLREIZ pasniedza sarkanu pytest kā «exit 0». Piezīme, kas nokrīt divreiz, ir vārts, kas paļaujas uz atmiņu, tāpēc `scripts/check.sh` tagad nes `trap … EXIT` banneri: krītot pēdējā izvada rinda ir **`==> CHECK FAILED (exit N)`**, zaļumā — `==> all checks passed`. Tātad `| tail` loga pēdējā rinda atbild uz jautājumu bez izejas koda. Izejas kodu caurule joprojām apēd — to labot skripts nevar, to labo izsaukuma forma.

> **HTML/live satura zondes raksti Python pusē, ne ar PowerShell `-match`.** `Get-Content -Raw` un `Invoke-WebRequest ... -match` uz šīs mašīnas dekodē UTF-8 kā ANSI, tāpēc KATRA latviskā zonde krīt (diakritika sabojāta), kamēr ASCII zonde tajā pašā izsaukumā trāpa — iznākums izskatās kā „saturs daļēji trūkst", nevis kā kodējuma kļūda. 2026-08-16 tas lika nolasīt jau publicētu sintēzi kā novecojušu un uzsākt lieku deploy izmeklēšanu. Zondei lieto `.venv/Scripts/python.exe` ar `io.open(..., encoding="utf-8")` vai `urllib` + `.decode("utf-8")`.

## Statiskās vietnes ģenerēšana

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

Pilns render ~3 min (169 s pēc 2026-05-29 `idx_claims_document_id` fix; agrāk `render_news` iekārās ~16 min — sk. CHANGELOG 2026-05-29). Kanoniskais ceļš pēc F3g refaktora ir augstāk parādītais `src.render` imports. Vēsturiskais `src.generate` re-export shim izņemts 2026-09-05 (strukturas plāna 5.10).

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

> **`personas` ≠ `politiki` — un nepareizā izvēle iziet ar EXIT=0 (2026-08-23).** `personas` renderē tikai **indeksa** lapu; individuālos profilus (`output/atmina/politiki/*.html`) renderē `politiki`. `--only=personas` izvades rindā godīgi raksta `politiki/: 0 politician profile pages` un atgriež 0 — tātad profila labojums «izrenderēts», bet lapas nav mainītas. Skaties izvades rindu, ne izejas kodu: `politiki/: N politician profile pages` ar N=0 pēc profilu labojuma ir nepareizs tvērums, ne veiksme. Tā pati loģika `partijas` (indekss + partiju lapas kopā, tur dalījuma nav).

CLI implementācija un `KNOWN_DOMAINS` saraksts: `src/render/__main__.py` + `src/render/_orchestrator.py:KNOWN_DOMAINS`. Derīgo domēnu saraksts izdrukājams ar `.venv/Scripts/python.exe -m src.render --list-domains` (19 domēni).

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
.venv/Scripts/python.exe -m src.graphics.cli brief --note-id N [--metaphor "..."] [--mood "..."] [--accent "..."]

# Tvītu pavediena attēli (text-free; --style sepia (noklusējums) vai light):
.venv/Scripts/python.exe -m src.graphics.cli thread --date 2026-06-06 --prompts thread.json [--style light]
```

`thread.json` = `{"1-lead": "metaforas prompts...", "2-valdiba": "..."}` → `output/images/threads/{date}-thread-{suffix}.png`. `brief --metaphor` pārraksta ģenērisko `visual_map` (house-style `metaphor_hint`). Pēc brief: review PNG → `approve_image` → narrow render → `deploy.sh --no-delete`.

> **Budžeta saucējs ir VIENS (kopš 2026-09-07).** Katrs `generate_image()` izsaukums — `cli brief`, `cli thread` vai tiešs izsaukums vienreizējā skriptā — raksta vienu `image_audit` rindu (prompts, modelis, `kind`, izmaksa). `monthly_cost_usd()` un `budget_check()` (griesti 5,00 USD/mēn.) lasa TIKAI to tabulu; `brief_images` paliek apstiprināšanas darbplūsma. Līdz tam pavediena un sintēžu attēli budžetā neparādījās vispār — 2026-09-06 divi sintēzes attēli tā palika nereģistrēti. Pārbaude: `SELECT kind, COUNT(*), ROUND(SUM(cost_usd),3) FROM image_audit WHERE generated_at LIKE '2026-09%' GROUP BY 1;`

> **NB:** `cli brief` raksta tikai pamata PNG (+ DB audita rindu) — tas **neemitē** WebP variantus (hero/card/thumb). Variantus backfill render solī, vai palaid `src.image_variants.make_variants(out_path)`, ja vajadzīgi uzreiz.

## CSP statistikas datu atsvaidzināšana

```bash
.venv/Scripts/python.exe -m src.csp              # sausais palaidiens (noklusējums)
.venv/Scripts/python.exe -m src.csp --apply      # raksta data/csp.db
```

`data/csp.db` baro `statistika` render domēnu (`src/render/statistika.py`). Sausais palaidiens nokopē bāzi uz pagaidu failu, fetčo īsti no CSP PxWeb API un ziņo, cik rindu katrā tabulā būtu pēc atsvaidzinājuma — izsekoto bināro failu neaiztiekot. **`--apply` ir datu mutācija:** `data/csp.db` ir git-izsekots binārs, dati iesaldēti kopš 2026-04-14, tāpēc pirmais reālais atsvaidzinājums dod lielu diffu, kas aiziet arī publiskajā spogulī — vispirms sausais palaidiens, tad operatora lēmums. Pirmais sausais palaidiens 2026-09-07: 10/10 tabulu, 1 489 fetčotas rindas, `csp_data` 1 481 → 1 509 (+28). Pirmais `--apply` 2026-09-06 vakarā — tie paši skaitļi.

**`--apply` viens pats live neko nemaina — statistikas lapas deploy iet no `curated/atmina/` momentuzņēmuma** (`_copy_curated()` overlay; pilns renders svaigo izvadi PĀRRAKSTA ar veco). Pēc katra `--apply`:

```bash
.venv/Scripts/python.exe -c "from src.render.statistika import generate_statistika; generate_statistika()"   # raksta output/atmina/statistika*
cp output/atmina/statistika.html curated/atmina/ && cp output/atmina/statistika/*.html curated/atmina/statistika/
REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py -q -k pozicijas     # statistika bāzlīnija ir render_baseline_misc.json
.venv/Scripts/python.exe -m pytest tests/test_render_chars.py tests/test_no_inline_js.py tests/test_csp_external_hosts.py -q
bash scripts/deploy.sh --no-delete
```

Pārbaude: `curl -s https://atmina.lv/statistika.html | md5sum` == `md5sum output/atmina/statistika.html` (2026-09-06: sakrita, 11 faili).

**OG attēls statistikas lapai (kopš 2026-09-08).** `statistika.html` nes savu OG kartīti, nevis vietnes vispārīgo `og-image.png`. To ģenerē no DZĪVAJIEM `csp.db` datiem, tāpēc pēc katra `--apply` tā noveco:

```bash
.venv/Scripts/python.exe scripts/make_statistika_og.py       # raksta assets/statistika-og.png
```

**Secība ir svarīga, un to viegli sajaukt.** `--only=<jebkas>` palaiž `_copy_curated()`, kas `output/atmina/statistika.html` PĀRRAKSTA ar `curated/` kopiju — tāpēc `generate_statistika()` jāsauc PĒC pēdējā `src.render` palaidiena, ne pirms. Pareizā secība: (1) `make_statistika_og.py`; (2) `-m src.render --only=static` (nokopē `assets/` uz izvadi); (3) `generate_statistika()`; (4) kopija uz `curated/`; (5) baseline REGEN un vārti; (6) deploy. 2026-09-08 šī secība tika sajaukta — attēls aizgāja live, bet lapa palika ar veco `og:title`, un vajadzēja otru kārtu.

## Pārklājuma audits (read-only)

```bash
.venv/Scripts/python.exe scripts/coverage_report.py [--db data/atmina.db]
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
# 0. Manifesta svaigums PIRMS audita (sēžu saraksts ir kalendāra momentuzņēmuma atvasinājums)
.venv/Scripts/python.exe -c "from src.saeima.manifest import load_manifest; s, g = load_manifest(); print(g, len(s))"
#    Ja par vecu vai None — pārģenerē: vispirms uztver kalendāru ar Playwright
#    (browser_navigate uz https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1
#    → saglabājas .playwright-mcp/page-*.yml), tad:
.venv/Scripts/python.exe scripts/_p3_extract_sessions_2026-05-26.py --max-year 2026

# 1. Kas trūkst (tikai lasa, neko neraksta)
.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year 2025 --out data/parity_2025.json
.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year 2025 --dates 2025-04-10,2025-12-11

# 2. Trūkstošo ielāde (sausā palaide pēc noklusējuma)
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --parity data/parity_2025.json \
    --dates 2025-04-10 --apply --rollback-out data/rollback_saeima_missing_votes_2026-07-25.sql

# 2b. Ja claim solis kritis pusceļā (balsojumi DB, claims nav)
.venv/Scripts/python.exe scripts/ingest_saeima_missing_votes.py --repair-claims --dates 2025-04-10 --apply
```

Audits salīdzina darba kārtību ar DB pēc **`(vote_date, vote_time)`, nevis URL** — titania pārarhivē balsojumu lapas ar jauniem UNID, tāpēc `store_vote()` URL-dedup kļūst akls. Tā paša iemesla dēļ **nelieto `p3_backfill_year_urllib.py --year N` robu aizpildīšanai**: akls gada palaidiens ražotu dublikātus, ne aizpildītu robus.

**Manifesta vārti (kopš 2026-09-02).** Audits lasa sēžu sarakstu caur `src/saeima/manifest.py::load_manifest()`; manifesta forma ir apvalks `{"generated_at": "YYYY-MM-DD", "sessions": [...]}`. Rīks apstājas ar **izejas kodu 2** četros gadījumos: `generated_at` trūkst (vecā, kailā saraksta forma) vai nav nolasāms datums; ar `--dates` manifests ir vecāks par jaunāko pieprasīto dienu; bez `--dates` tas ir vecāks par 14 dienām (`MANIFEST_MAX_AGE_DAYS`); pieprasītajam datumam manifestā nav nevienas sēdes rindas. Katrā no tiem „trūkst 0" nozīmētu „neviens nav paskatījies", nevis tīru dienu (T8) — 2026-09-02 tieši tā 2026-08-20 sēdes 25 balsojumi izskatījās pēc kārtības.

**Vienai dienai mēdz būt vairāki sēžu UUID** — 2026-07-23 ir trīs, 2026-08-20 divi. Audits izdrukā rindu uz SĒDI, ne uz datumu, tāpēc viena rinda dienai, kurai kalendārā ir divas sēdes, ir manifesta robs, ne tīra diena.

`--apply` prasa `--rollback-out` un pirms pirmās rakstīšanas izsauc `ensure_embeddings_live()` — bez darboša embedding steka `store_vote()` paspētu ierakstīt balsojumus, un claim solis kristu aiz tiem. Palaid ar `.venv/Scripts/python.exe`, nevis kailu `python`.

Vēsture un 2025. gada rezultāti: [CHANGELOG](../CHANGELOG.md), atlikušais darbs: `BACKLOG.md`.

### 3. Kopsavilkumi + stance pārģenerēšana

```bash
# Aizpilda NULL saeima_votes.summary no melnrakstiem + pārģenerē saeima_vote claim stances
.venv/Scripts/python.exe scripts/apply_saeima_summaries_2026-09-02.py \
    --regen-sessions 2026-07-23,2026-08-20                                  # sausā palaide
.venv/Scripts/python.exe scripts/apply_saeima_summaries_2026-09-02.py --apply \
    --regen-sessions 2026-07-23,2026-08-20 \
    --rollback-out data/rollback_saeima_summaries_0723_0820_2026-09-02.sql

# Tikai stance pārģenerēšana tur, kur summary jau ierakstīts (melnrakstus nelasa)
.venv/Scripts/python.exe scripts/apply_saeima_summaries_2026-09-02.py --apply --no-drafts \
    --regen-sessions 2026-08-20 \
    --rollback-out data/rollback_saeima_stance_0820_2026-09-02b.sql
```

Melnraksti nāk no `data/saeima_summaries_drafts_2026-09-02/summaries_*.json`; skripts ir to vienīgais rakstītājs. Vārti pirms rakstīšanas: `summary` tiešām NULL, teksts neatkārto `motif`, nesatur cita balsojuma iznākuma frāzi, iziet diakritiku validāciju. Raksta tikai `saeima_votes.summary` un `claims.stance` — `bill_id` / `current_stage` netiek aiztikti (inv #12), un **pārembedošanas nav**, jo `saeima_vote` claims kopš 2026-08-21 verdikta vektoru nenes. `--rollback-out` jābūt unikālam katram palaidienam: ja fails jau eksistē, skripts apstājas, nevis pārraksta drošības tīklu. Rollback arhīvus drīkst turēt saspiestus — `data/rollback_*.sql.gz` kopš 2026-09-02 ir izņemti no `.gitignore`.

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
