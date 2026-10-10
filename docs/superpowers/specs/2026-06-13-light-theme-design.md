# Gaišais režīms (light theme) + slēdzis — dizaina spec

**Datums:** 2026-06-13 · **Statuss:** apstiprināts (operatora izvēles caur AskUserQuestion)

## Mērķis

atmina.lv publiskajai vietnei pievienot gaišo režīmu, kas vizuāli sakrīt ar
featured-image estētiku (krēmkrāsas papīrs + tintes melns + Georgia serifs —
sk. `docs/featured-images/dailies/2026-05-18.png`), un "vintage" pārslēdzēju
navigācijas joslā.

## Apstiprinātie lēmumi

| Jautājums | Lēmums |
|---|---|
| Noklusējums | **Tumšais paliek noklusējums.** Slēdzis ieslēdz gaišo; izvēle saglabājas `localStorage` (`atmina:theme`). |
| Slēdža stils | **Vintage flip switch** — skeuomorfs sviras slēdzis (CSS-only, plate + skrūves, snap animācija), Georgia mikrouzraksts. |
| Novietojums | **Nav labajā malā** (desktop); burger pārklājumā mobilajā. |
| Dziļums | **Viss redzamais**: `assets/style.css`, ~14 šabloni ar inline krāsām, `bmv1.js`/`pzv1.js`, Chart.js konfigurācijas `statistika*.j2`. |

## Arhitektūra

1. **Tokenizācija.** `assets/style.css` (5704 rindas) satur ~100 hardcoded
   krāsu literāļus ārpus `:root`. Tos aizstāj ar semantiskiem CSS mainīgajiem
   (`--overlay-*`, `--chip-*`, `--shadow-*` u.c.); `:root` patur tumšās
   vērtības (noklusējums bez JS), `html[data-theme="light"]` bloks pārraksta.
2. **Gaišā palete** (no featured-image papīra): fons ~`#f4efe4` (jau lietots
   `.weekly-stat-card`), tinte ~`#211f1a`, akcenti paliek `#37474F` /
   `#B71C1C` / `#1f2d4d`. Statusu krāsas (zaļš/dzeltens/sarkans/oranžs)
   patumšinātas līdz WCAG AA uz krēmkrāsas fona.
3. **No-FOUC.** Inline skripts `base.html.j2` `<head>` pirms stylesheet:
   ja `localStorage['atmina:theme']==='light'`, uzliek
   `document.documentElement.dataset.theme='light'`. Bez ierakstes —
   noklusējums tumšs. + `<meta name="color-scheme" content="dark light">`.
4. **Slēdzis.** `<button role="switch">` ar LV aria (piem. "Pārslēgt gaišo
   režīmu"); klikšķis pārslēdz `data-theme`, saglabā localStorage, raida
   `atmina:themechange` CustomEvent.
5. **JS virsmas.** `bmv1.js`, `pzv1.js` un Chart.js konfigi lasa krāsas
   runtime no `getComputedStyle` CSS mainīgajiem un klausās
   `atmina:themechange` → `chart.update()` / pārzīmēšana.
6. **Ārpus tvēruma (apzināti netiek mainīts):** `templates/og-card.html.j2`,
   `templates/social/quote_card.html.j2`, `src/social_agent/visuals.py`
   (PNG kartītes paliek tumšajā brendā), ops dashboard (`src/dashboard` —
   tam jau ir savs slēdzis), deploy.

## Verifikācija

- `bash scripts/check.sh` zaļš pirms un pēc.
- Pilna `generate_public_site()` pārģenerēšana (chrome maiņa skar katru lapu —
  šaurais `--only` te neder).
- Playwright caurskate: ~10 atslēgas lapas × {tumšs, gaišs} ekrānuzņēmumi +
  computed-style skenējums (neviens elements gaišajā režīmā nedrīkst paturēt
  tumšās paletes fonu; nekādu light-on-light tekstu).
- Adversariāls panelis: a11y/tastatūra, FOUC/persistence, WCAG kontrasts,
  LV gramatika jaunajām UI virknēm, og/social neaiztikts.

## Izpildes iznākums (2026-06-13)

Implementēts ar `light-theme-implement` workflow (8 Opus koderi, disjunktas
failu zonas) + manuāla fix-fāze. **Verifikācija:** ruff tīrs · render baselines
reģenerēti (`REGEN=1`) · pilna `pytest` **1429 passed, 0 failures** · pilns
`generate_public_site()` bez kļūdām · Playwright: nav 57px **abās tēmās**
(kritiskais 57→69px regress novērsts), slēdža toggle/persist/aria/meta/bodyBg
round-trip korekts.

**Fix-fāzē novērstais** (pēc Visual QA + 2 adversariālo refuteru):
- **Kritiskais** — slēdzis (44px) audzēja desktop nav 57→69px → katra lapa
  nobīdās 12px. Labojums: `.nav-theme { min-width/height:44px; margin:-8px 0 }`
  atsaista 44px pieskāriena mērķi no vizuālā augstuma (atrisina arī 30px
  touch-target minoru).
- **Major a11y** — `role="switch"` + mainīgs darbības `aria-label` = pretrunīgs
  SR paziņojums. Labots uz ARIA APG: statisks `aria-label="Gaišais režīms"`,
  stāvoklis tikai caur `aria-checked`.
- **Gaišā kontrasta korekcijas (tikai light, dark byte-identisks):** sev-badge
  krāsas (#dc2626/reversal/minor → AA), `.badge-green`/`.badge-yellow` teksts,
  `--text-dim` #857b63→#6e654f, `.role-chip-minister` fons, pzv1 rail-search
  `:focus-visible` outline. Visi ≥5.0:1 (verificēts).
- **meta color-scheme** → `dark` (atbilst dark-default lēmumam; novērš
  light-OS pirmā apmeklējuma kanvas zibsni).
- **Noraidīts** (refuters kļūdījās): "base.html.j2:93 dead code" — tas ir
  *apzinātais* curated-lapu late-apply bootstrap (curated heads ir iesaldēti).

**Atlikts operatora lēmumam (NEbloķē; nav regress — pre-eksistējoši/sistēmiski):**
1. Datu-vadītā partiju/tēmu palete (`x.html`, `pozicijas.html`) — 1.73–4.29:1
   pie 9–10px uz papīra. Labot paletes avotā `src/render` (plāna open Q9).
2. Curated `statistika.html` — iesaldēts tumšais hero-gradients + change-pills.
   Re-freeze pēc tēmas izlaišanas (plāna open Q1).
3. Chart-rebuild `prefers-reduced-motion` — themechange atkārto chart entry
   animāciju (tikai pie manuāla toggle; minors).
4. `x-v1.js` "topiks"→"tēma" aria-label (pre-eksistējošs, nesaistīts ar tēmu).

## Pabeigšanas fāze (2026-06-13, `light-theme-finish` workflow)

Atrisināti visi 3 atliktie operatora lēmuma punkti. Verifikācija: ruff tīrs ·
baselines reģenerēti · pilna `pytest` zaļa · pilns render · Playwright kontrasta
re-skenēšana · 2 adversariālie refuteri (**0 critical/major, 6 minori — visi
"PASS, dokumentēts"**) · neatkarīga datu-integritātes pārbaude.

1. **Datu-vadītā partiju/tēmu palete (light).** Partiju krāsas tekstam
   pārmarsrutētas no inline `color:` uz `--party-color` custom property
   (`x.html.j2` ×3, `pzv1.js`), klasēm pievienots resting `color:
   var(--party-color, var(--text-muted))` → **dark vizuāli identisks** (teksts
   atrisinās uz to pašu brenda hex; verificēts Playwright: ZZS #84cc16 utt.).
   Light pārrakstīts ar `color-mix(in srgb, <var> 47%, #1f1b14)` partijai +
   tēmas čipam (+ hover) → iepriekš 1.73–2.5:1, **tagad 5.07–5.88:1** uz krēma.
   `.stat-change.positive`/`.domain-state` zaļš → #15662e (5.6:1).
2. **Curated `statistika` re-freeze.** `generate_statistika()` →
   datu-paritātes vārti (visu 11 lapu skaitļi byte-identiski, neatkarīgi
   apstiprināts) → pārkopēts uz `curated/atmina/statistika*`. Tagad nes tēmas
   bootstrap + tokenizēto hero-gradientu (tumša tinte uz krēma, 6.5–15.5:1) +
   PRM-gated chartus. Faili sarukuši (tokenizācija, ne datu zudums).
   `finanses.html` = roku-kurēts, bez ģeneratora; QA: renderējas labi gaišajā —
   netiek aiztikts.
3. **Chart `prefers-reduced-motion` + LV.** Chart.js animācijas
   `index/analizes/statistika/statistika-detail` rebuild ceļos gated uz
   `matchMedia('(prefers-reduced-motion: reduce)')`. `x-v1.js` aria-label
   "topika"→"tēmas filtru" (anglicisma labojums).

**Statuss:** working tree, NEkomitēts/NEdeployots — gaida operatora review +
publish-pause (sk. atmiņa `feedback_brief_publish_pause`). QA artefakti:
`docs/audits/light-theme-qa-2026-06-13/` (baseline/after-dark/after-light/diff
+ recheck/ + finish/ ekrānuzņēmumi). Pilns mainīto failu kopums: 4 assets +
`src/render/_common.py` + 13 šabloni + 11 curated statistika + 11 render
baseline fikstūras.

## Riski

- Slēptas literāļu paliekas → computed-style skenējums ir vārti, ne grep.
- Testu fikstūras, kas balstās uz nav-chrome HTML — audita solis tās apzina.
- `_rendered_chrome` (curated lapas) injicē nav no `base.html.j2` — slēdzim
  jānonāk arī tur (notiek automātiski, jo chrome tiek renderēts no šablona).
