# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## Publiskā vietne — renderēšana un veiktspēja

### [FIX] `brief_images` divi metadatu defekti (2026-08-04 kvalitātes pārbaude)

(@graphics-designer 08-04): (a) `.png` faili satur JPEG baitus (`FF D8` — `generate_image` atdod JPEG, storage saglabā ar `.png`; publiskā virsma lieto `-hero/-card/-og` variantus, tāpēc nekaitīgs, kamēr nav Content-Type sniffing); (b) `width` kolonna hardkodēta 1408 `src/graphics/cli.py`, faktiski Gemini atdod 1376 — visās rindās. (Trešā tās pašas pārbaudes palieka — `<!-- DIENAS STATS -->` noplūde uz publisko HTML — slēgta 2026-08-05: blog renderis strippo komentārus pirms markdown, vārti `tests/test_blog_comment_strip.py`; dzīvā vietne attīrās nākamajā deploy.)

### [SLĒGTS 2026-08-20 — kodols] Render self-join lēnās stadijas
Abi balsojumu self-join aizstāti ar kopīgu numpy precompute `src/render/_common.py::vote_alignment_data` (~101s → ~2s; paritāte 0 nesakritību gan 9034 pāros, gan visos 195 per-pid sarakstos; orākuls `tests/test_vote_alignment_precompute.py`; CHANGELOG 2026-08-20). `politiki+saites` domēni tagad ~48s kopā. **Paliek atvērts tikai saistītais atlikums:** lazy pre-fetch — MVP joprojām fetcē politicians/claims/contradictions visās call ceļās.

### [DEFERRED] balsojumi.html Step 3
Plan: `docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md`. Steps 1+1.5+2 DONE (367 MB→142 KB br). Atlikušais, ja signāli par bottleneck:
- **A. Column virtualization "Visa vēsture":** šobrīd 770k DOM šūnu, render 2–5s mobilā. Spacer + absolūti pozicionētas šūnas, on-scroll visible col range (~150–200 rindas JS; ARIA `aria-rowcount` tricky).
- **B. TAB 1 cards (200×38 KB=7.6 MB):** B1 — drop SSR `<details>`, JS popover ar matrix JSON lookup (3.2 MB SSR, ~80 r. JS); B2 — tikai pirmie 50 ar details (~4.3 MB); B3 — pilna vote-list virtualizācija (daudz koda). Prioritāte ZEMA (8 MB OK desktop; mobilā 13s @5 Mbps).

## Profili / UI

### [DEFERRED] 2026-07-23 drošības audita apzināti pieņemtās paliekas
Galvenes + stingrā CSP DONE + live 07-23 (CHANGELOG § Stingrā CSP). Apzināti NErisinātās audita piezīmes, prioritātes secībā, ja operators kādreiz grib: (a) **web app manifests** (`site.webmanifest` 404 — PWA instalējamība; apple-touch-icon jau ir); (b) **tap-target izmēri** (24 elementi <48px — nav saites ~20px, hero karuseļa punkti 8×8px; reāls mobilais UX darbs, skar chrome); (c) **`<title>` 28 zīmes** (audita ieteikums 30–60 — kosmētika); (d) **robots meta taga neesamība** (noklusējums = index,follow; robots.txt + sitemap jau ir — tīri audita ķeksītis); (e) **`style-src 'unsafe-inline'`** paliek AR NOLŪKU (style="" atribūti visā vietnē; auditi nesoda). Viltus pozitīvi, NEatkārtot: leta.lv ārējo linku "timeouts" (abas saites 200 <0,3s — audita botu bloķē leta), "HTTP versijas zonde neizdevās" (301 uz HTTPS strādā), "apple-touch-icon trūkst" (ir, 200).

### [OPEN] UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
Pabeigtais darbs — trīs fāzes, sākumlapas pārveide un visi commit heši — pārcelts uz [CHANGELOG arhīvu § 2026-07-04 UI dizaina audits](../wiki/CHANGELOG-arhivs.md) 2026-08-03. Šeit paliek TIKAI atlikums.

- **Gala revīzijas minoru paliekas:** „Visas pretrunas →" saite zem Līderu joslas virsraksta (der neitrālāka), pretrunu fakta datums = `new_date` nevis `detected_at`, iniciāļu izteiksme templotē dublēta 4× (der `initials` no `rankings.py`).
- **Reviewer-nits (07-07 uzmanības centrs):** paliek `#8b8fa3` fallback literālis — kandidāts `_common.py` konstantei, tīri mehānisks. **Pārmērīts 2026-08-15: 30 trāpījumi 15 failos** (agrāk šeit stāvēja „24 vietās 12 failos" bez vaicājuma; vaicājums, kas deva jauno skaitli: `grep -rio '#8b8fa3' src templates assets | grep -v __pycache__ | wc -l` un tas pats ar `-ril` failiem). Ņem vērā: `src/render/dashboard.py:45` jau tur `_TRENDS_FALLBACK_COLOR`, tāpēc konsolidācija ir esošas konstantes pacelšana uz `_common.py`, ne jaunas radīšana. (`_fetch_tensions` dubultizsaukums un `#c25e5e` atrisināti.)
- **Dizaina parāda paliekas:** font-size/line-height TOKENIZĀCIJA (apzināti atlikta — simtiem deklarāciju, mazs redzamais ieguvums); vēsturiskie breakpointi 480/560/640/700 (dokumentēti pie :root, migrē tikai pieskaroties komponentei); `bmv1.js:220` inline gap kas prasa `!important` (JS fix); statistika-detail "N ieraksti" lv_plural (curated re-freeze vārti).
- **A11y paliekas (no 2. fāzes):** nav `aria-label="Galvenā izvēlne"` prasa `_CHROME_SPECS` regex paplašināšanu `<nav class="nav"[^>]*>` (`_orchestrator.py:176-177`, backward-compatible — vajag operatora svētību frozen-regex maiņai); statistika canvas sparklines teksta alternatīva (curated); pzv1/pnv1 rail pogām `aria-pressed`; `.link-filter-btn`/`.subtab-btn` aria-pressed; zinas/pretrunas feed-item virsraksti; skip-link + typeahead nav uz curated lapām (nav sgv1.js → plain GET fallback, apzināti pieņemts).
- NE-defekti (izmeklēts, neatkārtot): gaišais default ar dark `:root` = apzināts (c634c47); zinas/x mega-lapām pagination NErosinu (perf ne-darīt saraksts); abi `!important` izsekoti un pamatoti (802c6e8 ziņojums).

### [OPEN] Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3

Trīs agrāk atsevišķi ieraksti, apvienoti 2026-08-05, jo tie skar vienu virsmu un savstarpēji pārklājas — **pārbaudi, kas jau izdarīts, pirms sākt.** 2. līmenis ir noformēts kā plāns: `docs/plans/2026-07-26-profila-ux-tier2.md` (quote rādīšana Pozīciju cilnē, tēmu čipu deep-link ar filtru, Atturas semantikas nozīme, pretrunu flags kartītēm + filtrs — ar šķērsnoteikumiem un secību); ātrviežu pakete DONE + testēta (CHANGELOG § 2026-07-26).

- **Wiki sintēzes bloku ports uz publisko UI:** `wiki_sync()` raksta conditional synthesis bloku (top tēmas / 30 d / spriedzes / pretrunas) starp `<!-- SYNC-AUTO -->` markeriem person profilos (76/148 ar saturu; plāns `docs/superpowers/plans/archive/2026-04-20-wiki-synthesis-block.md`) — operatora uzdevums ir parādīt tos pašus datus **publiskajās atmina.lv politiķu profila lapās**.
- **Bloks 3** (datu/UI slāņi 1+2+3 MERGED 2026-05-14, Pārskats cilne 149/176 profilos): Saeimā cilnes redizains (v1 „nesenākie 5 + pretdziedoši frakcijai" — prasa „svarīga balsojuma" definīciju); Saites story-driven sub-summaries; Publikācijas filtri žurnālistiem (atdalīt retweets/ziņas/oriģinālus — prasa documents metadata paplašinājumu); data freshness + citation/share poga; URL hash deeplink no ārpuses; VAD delta bloks Pārskatā (atsevišķs delta-loģikas spec). Review faili dzēsti 2026-07-20 (`c03ce566`), saturs atgūstams ar `git show c03ce566^:wiki/profile-page-review.md`.
- **Pārskats cilne tieva** lielākajai daļai profilu (Bloks B prasa `confirmed=1 AND salience≥0.5`; DB tikai 29 pretrunas) — kandidāti no esošajiem datiem: Par/Pret/Atturas sadalījums 3 mēnešos deputātiem (mini-bar), aktivitātes sparkline 6–12 mēn., frakcijas-sakritības % (alignment jau skaitļots Saišu cilnei). Žurnālistiem/analītiķiem Pārskats vispār neeksistē (`politicians.py:889` izslēdz) — dominējošās komentāru tēmas + visvairāk komentētie politiķi aizpildītu.
- **Personas lapa:** partiju rail grupēts pēc koalīcijas statusa; aktīvo filtru čipi desktopam (šobrīd tikai mobilajā); meklētājs neatrod tēmas („kurš runā par airBaltic?"); foto placeholderi — divi iniciāļi ar partijas krāsas toni.
- **Saeimā cilne:** motīfu apcirpšana 80 zīmēs pārtrauc vārda vidū; frakcijas-diverģences highlight (alignment SQL jau eksistē); grupēšana pa sēdēm.
- **Timeline cilne:** mēnešu grupu virsraksti + tipa filtru čipi (pozīcijas/balsojumi/pretrunas) — šobrīd plakana jaukta lente.
- **Saites mini-grafs:** vote alignment top/bottom 3 → pilna tabula (mezglu labeli vārdi→uzvārdi atrisināti 2026-07-29). **Mediju/iestāžu profiliem** trūkst „kāpēc mēs to izsekojam" explainer + cross-link uz `mediji.html` caurskatāmības lapu (personas rail to linko, pats profils — nē).

