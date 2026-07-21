# atmina ops — Operatora kontroles panelis

> Lokāls Flask dashboard, kas surfacē visu atmina dienas stāvokli vienā ekrānā: brief progress, X cookie slot health, ekstrakcijas backlog, A/B stratēģija + aktivitātes timeline. Pilna [implementation plan](../../docs/superpowers/plans/2026-05-16-operator-dashboard.md) + [design spec](../../docs/superpowers/specs/2026-05-16-operator-dashboard-design.md).

## Palaišana

```powershell
.venv/Scripts/activate
python serve.py
```

Atver `http://127.0.0.1:8080`. Servera bind ir cietkods uz `127.0.0.1` — nedrīkst atvērt LAN/internet. Bez auth (localhost only).

## Paneliišas

| Panelis | Avots | Atjauno |
|---|---|---|
| **Šodienas pārskats** | `context_notes` + `brief_images` | katra page load |
| **Rutīna** | `src.routine.check_routine()` | katra page load |
| **X cookie pool** | live probe 4 endpoints × 6 slots | 60s cache; force-refresh M2 |
| **X_MENTIONS stratēģija** | `logs` (mentions_fetch + guardrail) | katra page load |
| **Ekstrakcijas rinda** | `documents.reviewed_at IS NULL` | 30s cache |
| **Aktivitāte** | UNION (logs + brief_images + context_notes + analyses) | 30s HTMX poll |

**Klaviatūras saīsnes (M2):**

| Taustiņš | Darbība |
|---|---|
| `?` | Atvērt visu saīsņu sarakstu |
| `A` | Apstiprināt fokusēto image (kad ir pending brief image) |
| `R` | Force-refresh X cookie slot health probe (≈8 s) |
| `D` | Atvērt deploy konfirmācijas modal |
| `Esc` | Aizvērt jebkuru modālo logu |

Saīsnes neuztver, kad raksti `<input>`/`<textarea>` (lai netraucētu reject reason rakstīšanai). Ctrl/Cmd/Alt modifikatori arī tiek izlaisti, lai `Ctrl+R` joprojām reloado lapu.

**M2 darbības (HTMX action endpoints):**

| Endpoint | Triggers | Iznākums |
|---|---|---|
| `POST /api/image/<id>/approve` | Apstiprināt poga vai `A` | `brief_images.approved=1`; brief panel pārzīmējas; toast |
| `POST /api/image/<id>/reject` | Noraidīt poga (modal ar reason) | `brief_images.approved=2`, `error_message=<reason>`; toast warning |
| `POST /api/slots/refresh` | `↻ Pārbaudīt` poga vai `R` | Live probe 6 slots × 4 endpoints; toast ar healthy count |
| `GET /api/deploy/confirm` | `🚀 Deploy` poga vai `D` | Atver modal ar pēdējā deploy laiku |
| `POST /api/deploy` | Modal "Apstiprināt" | `bash scripts/deploy.sh` 300 s timeout; toast success/failure/timeout |

Visi POST endpoints atgriež HTMX-friendly response — panel HTML body + `HX-Trigger` headeris ar toast payload-u.

**Pending banner (augšā):** dzeltens svītrains paneliš parādās, ja:
- ir image, kas gaida apstiprinājumu šodienas briefam,
- brief vēl nav uzrakstīts un pulkstenis jau pēc 15:00 LV (pirms 15:00 → `'waiting'` stāvoklis, nav alarm — sk. memory `project_daily_routine_timing`),
- search_tweet slot health zem 4/6 (panelis skaita visus 6 cookie failus; produkcijas fetch pūls ielādē tikai 1.–5.json — sk. BACKLOG par 6.json) → guardrail nostrādās un kritīs uz timeline stratēģiju.

Banner ir aizverams uz sesijas garumu (Alpine.js x-data + sessionStorage). Reload — atjaunojas, ja vēl ir aktīvi pending items.

**Footer:** image budžeta strīpa (`$1.131 / $5.00 (22%)` formāts, summē brief_images.cost_usd pašreizējam kalendārajam mēnesim, soft cap `$5.00`), build SHA (`git rev-parse --short HEAD`), "nākamais" mini-list (Telegram brief / social drafts laika dārvas).

## Vides mainīgie

| Mainīgais | Default | Kur lasās |
|---|---|---|
| `X_MENTIONS_STRATEGY` | `search` (kopš 2026-06-12 flip; `timeline` = guardrail fallback) | A/B strategy panelī parādīts cipot. Lai uzspiestu `timeline`, palaid `setx X_MENTIONS_STRATEGY timeline` un atver jaunu PowerShell sesiju (user-scope mainīgais inheritējas), tad `python serve.py`. |

Visi citi paneli lasās no `data/atmina.db` ar `src.db.get_db()` — DB ceļš nāk no `DB_PATH` env mainīgā vai `data/atmina.db` default'a.

## Theme toggle

Augšējā labajā stūrī ir `◐` poga — cikls auto → ☀ light → ☾ dark → auto. Saglabājas `localStorage['ops:theme']`. `auto` = nav saglabāts, klausa `prefers-color-scheme` media query. Flash-of-wrong-theme bloķēšana notiek `<head>` skriptā pirms pirmā paint.

## Troubleshooting

**Slot probe paneli lādē lēnāk pār 10s:** pirmajā page load pēc servera startup cache ir auksts → live probe pār twikit (~1-2s × 6 slots = ~8s). Nākamie page loadi 60s laikā saņem cache. **Force-refresh** poga ar `R` keyboard shortcut tiek piegādāta Task 2.3 (M2).

**Backlog rāda `0` šodien, bet ekstrakcijas vēl nav palaistas:** tā ir gaidāmā uzvedība pirms 15:00 LV — operatora plūsma ir "ingest visu dienu, ekstraktē + brief pēcpusdienā" ([project_daily_routine_timing](../../.claude/projects/C--Users-The-User-atmina/memory/project_daily_routine_timing.md)).

**Aktivitātes timeline nerāda nesenas darbības:** pārbaudi `logs` tabulu uz konkrētu action — tikai šie iekļaujas timeline: `ingest`, `mentions_fetch`, `social_fetch`, `social_fetch_all`, `deploy`, `mentions_fetch_guardrail`. `saeima_vote_claim` (16k+ rows) ir izslēgts no timeline, lai nepalielinātu trokšņu līmeni.

**Build SHA rāda `unknown`:** `git rev-parse` neizdevās — vai nu nav git instalēts uz PATH, vai timeout 2s pārsniegts. Footer turpina renderēt; nav fatal.

**Image cost rāda `$0.000`:** Šī mēneša briefiem vēl nav ģenerēti vai cost_usd ir 0 (defaults uz `0.039` no `gemini-3.1-flash-image-preview` price-list).

**Page load > 2s:** parasti pirms cold-cache slot probe. Pēc tā 60s — sub-second. Ja persistē, profilet ar Chrome DevTools network tab.

## Drošība

- Bind ir 127.0.0.1 — nav LAN exposable. Ja vajadzīgs remote access, izmanto SSH port-forward, ne 0.0.0.0 bind.
- Nav autentikācijas. Localhost only.
- Tabula `logs.action='mentions_fetch_guardrail'` rakstās šeit pirmoreiz (Task 1.5). Vēsturiskās guardrail ieraksti nav backfillēti — tikai jaunās trips skaitās 24h logā.

## M1 → M2 → M3 plūsma

- **M1 (šis):** 5 panel + activity timeline, read-only. Visi paneli aizpildās bez operatora klikšķiem.
- **M2 (nākamais):** HTMX action buttons — image approve/reject, slot probe force-refresh, deploy ar confirm modal, keyboard shortcuts. Plāna Phase 2.
- **M3 (vēlāk):** tooltips, empty-state polish, settings page, first-visit tour, optional SSE. Plāna Phase 3.

## Saistītie

- [implementation plan](../../docs/superpowers/plans/2026-05-16-operator-dashboard.md)
- [design spec](../../docs/superpowers/specs/2026-05-16-operator-dashboard-design.md)
- [commands.md](commands.md) — viss CLI komandu atskaites punkts
- [twikit patches](twikit-notes.md) — slot health debugging
