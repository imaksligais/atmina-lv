# atmina.lv — uzmanības & saistošuma pārstrāde (design spec)

_Datums: 2026-06-08 · Pamatā: `docs/audits/atmina_uzmanibas_parskats_2026-06-08.md` + faktiskais render kods._

## Problēma

Audits to formulē precīzi: lapa **pierāda, pirms tā ieinteresē** — atveras ar abstraktu
saukli + 3 metriku plāksnītēm (datubāzes valoda), nevis ar konkrētu stāstu. Atklāšana
prasa rakstīt/filtrēt. 12-vienību navigācija raida "datubāze, ne galamērķis" signālu.
Tēmas ir tikai filtra parametrs, nevis galamērķi. Mobilais skats ir funkcionāls, bet ne
"seksīgs".

Lielākā daļa nepieciešamo **datu jau eksistē** (`latest_contradictions`, `vote_alignment`,
`claims_7d`, nedēļas pārskati, 31 tēmu grupa) — tas ir prezentācijas + IA + CSS darbs, **ne**
jauna datu vākšana. Nav DB/shēmas izmaiņu.

## Mērķis

Pārvērst sākumlapu no datubāzes par galamērķi: konkrēts stāsts pirmajās 5 sekundēs,
atklāšana bez rakstīšanas pirmajās 30, dziļāka sesija ar tēmu lapām un "turpini rakt"
blokiem — saglabājot **neitralitāti, bez sentiment, faktiski** (CLAUDE.md). Lapa ir vienlīdz
pārliecinoša web un mobile skatā. **Bez bloat**: atkārtoti lietojam esošos datus, paterņus,
dizaina tokenus.

## Neitralitātes sargs (load-bearing)

- Nekādu vērtējošu "score" (audita brīdinājums #6). Vote-alignment = faktisks % ("balso ar
  koalīciju X% balsojumu"), nevis "dumpinieks"/spriedums.
- Bez tabloīdu tonalitātes ("kurš tiek atmaskots"). Saglabā "iepazīsties ar avotiem un
  izvērtē pats" rāmi.
- LV gramatika + stilistika gate uz katru jaunu virkni pirms render/commit.

## Apjoms (8 darba zonas)

### A. Navigācija 12 → 6 + "Vairāk" (`templates/base.html.j2` — skar visas lapas)
- Primāri: **Pretrunas · Pozīcijas · Balsojumi · Tēmas · Politiķi · Analīzes**.
- "Vairāk ▾" disclosure (sekundāri): Partijas, Mediji, Ziņas, X, Saites, Finanses, Statistika.
- Logo → sākums. `active_page` saglabā esošo loģiku; sekundārās lapas iezīmē "Vairāk" kā aktīvu.
- **Mobile:** hamburger poga atver overlay/disclosure ar primāro + sekundāro grupu. Tīrs CSS +
  ~30 rindas vanilla JS (checkbox/`<details>` toggle), bez framework.

### B. Sākumlapas hero — curiosity-first (`templates/index.html.j2`, `src/render/dashboard.py`)
- Zīmola rinda "Ko viņi teica. Kā viņi balsoja." → mazs kicker (nav dominējošais H1).
- Vizuālais varonis = **viena rotējoša izceltā pretruna** (atkārto `prv2` kartiņas vārdnīcu,
  hero-mērogā: foto, teica→balsoja, ΔT, avoti). Rotē caur `latest_contradictions` (JS fade-cycle
  kā esošais ticker; reduced-motion = statiska pirmā).
- **Globāls meklēšanas lauks** hero → `pozicijas.html?q=…` (audita #7).
- 3 metriku plāksnītes paliek kā kompakta sekundāra josla.

### C. "Atklāj bez rakstīšanas" rangu bloks (sākumlapa + `src/render/rankings.py` — JAUNS)
Faktiski saraksti (tabbed vai stacked):
- **Visvairāk pretrunu** (pretrunu skaits / politiķis)
- **Lielākie apvērsumi** (lielākais ΔT)
- **Visaktīvākie šonedēļ** (`claims_7d` / politiķis)
- **Visatšķirīgāk balso** (site-wide vote-alignment outliers — vienīgā jaunā agregācija;
  neitrāls %, ne spriedums)

`src/render/rankings.py::fetch_rankings(db) -> dict[str, list[dict]]` — tīra agregācija,
atkārto esošos query paterņus. Bez shēmas izmaiņām.

### D. "Šonedēļ" josla (sākumlapa)
Kompakts faktu kopsavilkums: jaunās pretrunas / kustētāji / jaunie balsojumi (7d) + saite uz
jaunāko nedēļas pārskatu (blog). Atkārto esošos `stats` (`claims_7d`, `votes_7d`,
`contradictions_7d`). Atgriešanās paradums.

### E. Tēmu galamērķa lapas — JAUNS domain `temas`
- `src/render/topics.py` (JAUNS) · `templates/tema.html.j2` (JAUNS) · `templates/temas.html.j2`
  (JAUNS — 31 tēmu direktorija).
- `temas/<slug>.html` katrai no 31 `topic_map.py` grupām: top politiķi par tēmu, jaunākās
  pozīcijas, pretrunas tēmā, saistītie balsojumi/likumi, saistītās sintēzes/analīzes (graceful
  ja kāds saites tips iztrūkst).
- Slug = `_slugify(canonical_group_name)` (transliterē LV → URL-safe). Sintēzēm ir `topics`
  frontmatter lauks → tieša saite.
- Wiring: `_orchestrator.py` (`_want("temas")` + `_heavy_fetch_plan` ja vajag), `KNOWN_DOMAINS`,
  `_generate_sitemap`, nav "Tēmas" → `temas.html`. Tēmu chips citur saista šeit.

### F. "Turpini rakt" bloki (`templates/_keep_digging.html.j2` — JAUNS)
Vispārina esošo `related-syntheses` bloku (`politician.html.j2`). Vienots partial ar:
Saistītās pretrunas · Citi šajā partijā · Citi par šo tēmu · Nejaušs profils. Iekļauj:
profila, pretrunas-detail, tēmas lapās. Datu provizēšana attiecīgo render moduļu pusē.

### G. Dalīšanās visur (viegls)
- Esošais `pretruna-detail` + `og-card` share → paplašina uz homepage/saraksta pretrunu
  kartiņām, profiliem, tēmu lapām (copy-URL + X-intent poga; mazs komponents).
- Pareizi per-page OG meta (title/description) tēmu + profila lapām.
- **Nav** jaunu per-tipu OG-attēlu ģenerēšanas (tas būtu bloat) — paļaujas uz esošajām
  per-pretrunu kartiņām + default OG.

### H. Dizaina pulēšana (the "sexy", mobile-first — `assets/style.css`)
Esošo tokenu robežās (dark `--bg #0d1014`, JetBrains Mono akcenti, Georgia virsraksti):
- Tipogrāfijas skala + atstarpju ritms konsekventāks.
- Kartiņu elevation + hover motion konsekventi.
- **Mobile-first audits 360–414px:** hero, rangu saraksti, pretrunu kartiņas, tabulas
  (scroll/reflow), nav (jaunais hamburger), 44px tap targets, nulle horizontāla overflow.
- Ievēro esošo `prefers-reduced-motion`.

## Arhitektūra & robežas

- Statisks generator: `templates/` + `src/render/*.py` (self-contained sub-page moduļi) +
  `assets/style.css` + SQLite. Jauni moduļi seko F3 sub-page paterņam: `render_X(env, db,
  atmina_dir, ...)`, importē tikai no `src.render._common` + `src.db`.
- **Bez DB rakstīšanas → bez rollback SQL.**
- **Neaiztiek** `finanses.html` / `statistika.*` (curated, frozen) un `wiki_sync`-regenerētos failus.
- Jauni moduļi (topics.py, rankings.py) + jauni templati = disjoint faili → droši paralēli.
  Koplietotie faili (base, index, dashboard, _orchestrator, style.css, detail templati) =
  secīga integrācija.

## Testēšana / verifikācija

- `bash scripts/check.sh` zaļš (ruff + pytest + render smoke). Jaunas kļūdas netolerē.
- **Char-baseline:** `base.html.j2` nav izmaiņas maina KATRAS lapas HTML → REGEN visus
  `tests/fixtures/render_baseline_*.json` ar `REGEN=1 pytest tests/test_render_chars.py`,
  tad commit fixtures. (CSS izmaiņas NEdriftē — `?v=` pinned uz "test".)
- `tests/test_orchestrator_gating.py` ekskluzīvi locko `KNOWN_DOMAINS` + heavy plan → atjauno
  par "temas".
- Jauni testi: `temas` lapu skaits == `len(TOPIC_GROUPS)`; `fetch_rankings` shape; nav
  kompresijas klātbūtne; jauns `temas` char-baseline.
- Playwright before/after screenshots (home + tēma + profils @ 1280px & 390px).
- **Bez deploy bez operatora apstiprinājuma** (feedback_brief_publish_pause / render_narrow_scope).

## Izpildes plāns (hibrīds)

1. **Workflow Fāze 1 (paralēli, disjoint JAUNI faili):** topics.py + tema/temas templati;
   rankings.py; _keep_digging.html.j2; jauni testi — pēc precīziem kontraktiem.
2. **Integrācija (main sesija, secīgi koplietotie faili):** nav, hero, ranks, this-week,
   search, orchestrator wiring, style.css, keep-digging includes, test/baseline atjaunošana.
   CSS iterē pret Playwright renderiem.
3. **Workflow Fāze 3 (paralēli adversariāli):** neitralitāte/CLAUDE.md konvencijas, LV
   gramatika, mobile responsiveness, render/link integritāte, accessibility/tap-targets.
4. Fix findings → re-verify → screenshots → operatora apstiprinājums deploy.

## Non-goals (YAGNI)

- Nav SQLite-WASM / klienta meklēšanas dzinēja (esošā pozicijas meklēšana pietiek).
- Nav per-tipu OG-attēlu masu ģenerēšanas.
- Nav vērtējošu scorecard/score rādītāju.
- Nav finanses/statistika pārstrādes.
- Nav nesaistītu refaktoru.
