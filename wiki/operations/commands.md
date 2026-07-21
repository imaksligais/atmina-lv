# Komandas

Atskaites punkts visām CLI/REPL komandām. CLAUDE.md tikai uzrāda divas obligātās (`check.sh` + `print_routine`); pārējās — šeit.

## Verifikācija un pirmsizpilde

```bash
.venv/Scripts/activate                    # Windows venv aktivācija
bash scripts/check.sh                     # Refactor safety net: ruff + pytest + generate_public_site smoke
python -m pytest tests/ -v                # Pilna testu paka
python -c "from src.routine import print_routine; print_routine()"   # Rutīnas statuss
```

`scripts/check.sh` ir vienīgā kombinētā verifikācija — jāizpilda pirms commit ar src/* izmaiņām. Skat. [CHANGELOG 2026-04-29](../CHANGELOG.md) par `generate_public_site` smoke iekļaušanu.

## Statiskās vietnes ģenerēšana

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

Pilns render ~3 min (169 s pēc 2026-05-29 `idx_claims_document_id` fix; agrāk `render_news` iekārās ~16 min — sk. CHANGELOG 2026-05-29). Kanoniskais ceļš pēc F3g refaktora ir augstāk parādītais `src.render` imports. `src.generate` ir re-export shim, neizmanto jaunā kodā.

### Narrow render (`--only` flag, ~30s – 2 min)

Šauram lapu apjomam izmanto **`python -m src.render --only=DOMAIN1,DOMAIN2`** — fetcē visus DB datus, bet izsauc tikai uzskaitītos `render_X` blokus. Ietaupa lielāko daļu no ~3 min pilnā render (lēnākie posmi: `render_links` ~46 s + `render_politicians` ~60 s), kad maini tikai dažas lapas.

```bash
.venv/Scripts/python.exe -m src.render --list-domains    # 19 valid domain names
.venv/Scripts/python.exe -m src.render --only=DOMAIN,...
.venv/Scripts/python.exe -m src.render                    # bez --only = pilns render
```

**Minimālais scope pa izmaiņas tipam:**

| Izmaiņa | `--only=` argumenti | Cena |
|---|---|---|
| Jauns daily_brief / weekly_brief saglabāts | `dashboard,blog` | ~30s |
| `parties.coalition_status` flip | `partijas,personas,balsojumi,pretrunas,pozicijas,dashboard` | ~1 min |
| Jauna sintēze vai analīze saglabāta | `sintezes,analizes,dashboard` | ~30s |
| Tikai jauni Saeimas balsojumi | `balsojumi` (vai `scripts/render_balsojumi_only.py`) | ~15-30s |
| Politikim pievienoti jauni claims/pretrunas | `pretrunas,pozicijas,dashboard,politiki,blog` | ~1-2 min (`render_politicians` ~60 s) |
| Tikai static (about/kontakti/404/sitemap) | `static` | ~5s |

CLI implementācija un `KNOWN_DOMAINS` saraksts: `src/render/__main__.py` + `src/render/_orchestrator.py:KNOWN_DOMAINS`. Detaļas: memory `feedback_render_narrow_scope.md`.

> **Meklēšanas ieteikumu sidecars:** `data/sg-index.json` (+`.br`/`.gz`) — sākumlapas typeahead indekss (`src/render/search_index.py`, lasa `assets/sgv1.js`). To atsvaidzina gan `dashboard`, gan `pozicijas` domēns, tāpēc dienas rutīnas narrow renderi to nekad neatstāj novecojušu. Tuple-shēma ir load-bearing — sk. [CHANGELOG § sg-index](../CHANGELOG.md).

`scripts/render_balsojumi_only.py` ir vēl ātrāks (~15s) tikai balsojumiem — neaktīvē politicians/claims/contradictions fetches.

## Lokālais dashboard

```bash
python serve.py     # http://127.0.0.1:8080
```

Operatora dashboard — 5 paneliišas (brief / rutīna / X slot health / A/B stratēģija / ekstrakcijas backlog) + aktivitātes timeline. Localhost only (bind cietkods uz 127.0.0.1). Pilns runbook: [atmina-ops.md](atmina-ops.md).

## Publicēšana uz Namecheap

```bash
bash scripts/deploy.sh --dry-run --no-delete   # Preview rsync
bash scripts/deploy.sh --no-delete             # Faktiska deploy (standing mode — nekad bez --no-delete)
```

Pilns runbook: [deploy.md](deploy.md).

## Telegram brief

```bash
python scripts/telegram_brief.py [DATE] [--md2]
```

Bez `DATE` — šodienas brief. Pilns runbook: [telegram-brief.md](telegram-brief.md).

## Social agent (X/Twitter draftu plūsma)

```bash
python -m src.social_agent brainstorm                  # Top 3 drafti uz Telegram
python -m src.social_agent approve|skip|revise|resend <draft_id>
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
python scripts/ingest_vestnesis.py [--limit N] [--dry-run] [--max-age-days D]
python scripts/ingest_vad_declarations.py [--politician X] [--limit N] [--dry-run]
```

Vēstnesis JL un VID amatpersonu deklarācijas — abi manuāli, idempotenti. Detaļas: [operacijas.md](operacijas.md).

## Diagnostika

```bash
python scripts/probe_x_cookies.py        # Visi 4 X endpoints per cookie slot
python scripts/patch_twikit.py           # Atjauno twikit lokālos patches
```

Skat. [twikit-notes.md](twikit-notes.md) par patch arhitektūru un 2026-04-29 SearchTimeline 404 incidentu.

## Video ingest

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch <url|path> [--slug NAME]
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize <slug>
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest status <slug>
```

Pilns 4-fāzu runbook: [operacijas.md § Video ingest](operacijas.md).
