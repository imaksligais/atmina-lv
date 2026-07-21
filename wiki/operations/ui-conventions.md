# UI / render konvencijas

Frontend un chrome noteikumi, kas nav acīmredzami no koda. Pārcelts no privātās sesiju atmiņas 2026-07-16 (gaišās tēmas, landing redesign un uzmanības centra darbu mācības). Katrs punkts ir vismaz vienreiz maksājis pārstrādi.

## Tēmas (light/dark)

- **GAIŠAIS = noklusējums** (flip `c634c47`); tumšais = opt-in caur `localStorage['atmina:theme']`. **`:root` apzināti tur DARK vērtības** — light dzīvo `html[data-theme="light"]` blokā, un bootstrap skripts uzliek `data-theme="light"`, ja localStorage ≠ 'dark'. JS-disabled → tumšais fallback (apzināti pieņemts). NElabo `:root` uz light — tas NAV bugs.
- **Datu-vadītas krāsas tekstā emitē caur CSS custom property** (`--party-color` / `--topic-color`), NEKAD inline `color:HEX` (inline pārspēj stylesheet → light režīmā nevar pārrakstīt). Resting: `color: var(--party-color, var(--text-muted))`. Light patumšināšana: `color-mix(in srgb, var(--party-color) 47%, #1f1b14)` → WCAG AA uz krēma fona pat gaišiem zīmola toņiem.
- **`<meta name="darkreader-lock">` NEDZĒST** (base.html.j2 head): vietnei ir pati sava tumšā tēma, un bez šī taga DarkReader-saimes rīki (t.sk. Brave iOS Night Mode) gaišo tēmu pārkrāso olīvbrūnā puskrāsojumā. Pāris: `meta[name=color-scheme]` ir DINAMISKS (id `meta-color-scheme`, sinhronizē bootstrap + pārslēgs) — statisks `light` tumšajā tēmā aicina auto-dark rīkus tumšot jau tumšu lapu. Sedz `tests/test_base_theme_meta.py`; vēsture CHANGELOG § 2026-07-17.

## Stingrā CSP — nekāda inline JS (invariants)

- **Katrs izpildāms skripts dzīvo `assets/*.js` failā** — dzīvā vietne servē `script-src` BEZ `'unsafe-inline'` (`assets/htaccess.template`), tāpēc pārlūks KLUSI nogalina katru `<script>` bez `src=` un katru `on*=` atribūtu, arī innerHTML-injicētu. Nekādas kļūdas konsolē pievienošanas brīdī — poga vienkārši nedara neko. Noslēgts ar `tests/test_no_inline_js.py` (templotes + curated + JS virknes).
- **Jaunas lapas JS paterns:** jauns `assets/XXv1.js` (nosaukumu konvencija kā ixv1/ppv1/sav1…) — `_resolve_assets_version()` glob to uzņem cache-bust automātiski; templotē `<script src="{{ assets_prefix }}assets/XXv1.js?v={{ assets_version }}" defer>`. Per-lapas dati → `<script type="application/json" id="…">{{ dati | tojson | safe_json }}</script>` (ne-izpildāms → CSP neskar; `safe_json` ekranē `</`) un `JSON.parse(getElementById(…).textContent)`; sīki skalāri → `data-*` atribūti. Notikumi → `data-*` + deleģēts `addEventListener`, nekad `onclick=`.
- **Ielādes kārtība:** `defer` saglabā secību starp defer skriptiem (chart-atkarīgie aiz `chart.min.js`); ja lapa sauc citu skripta `window.*` TŪLĪT (balsojumi → `bmv1.js`, saites → d3), jaunais fails jālādē SINHRONI tieši aiz atkarības. `theme-init.js` galvā ir bloķējošs AR NOLŪKU (FOUC aizsargs + fontu media-swap uz `link[data-font-async]`) — nepievieno tam defer.
- **Jauns ārējs hosts (skripts/stils/fonts/fetch) = CSP saraksta papildinājums** `htaccess.template` — citādi resurss klusi nolūst TIKAI produkcijā (lokālam priekšskatam galvenes nav). Multi-select meklēšanas filtru visām lapām dod `ms-a11y.js` delegācija (`.multi-select-search`/`.xv1-select-search`) — jaunam widgetam savs `filterOptions` nav jāraksta.

## Chrome (nav/footer) un kurētās lapas

- **`_CHROME_SPECS` regex prasa `<nav>…</nav>` + VIENU `<script src=…chrome-v1.js…>` tagu** — nepievieno otru skriptu vai markup starp tiem, citādi `_base_chrome_blocks()` met RuntimeError katrā būvē. Jauni nav elementi iet IEKŠĀ `<nav>`, to JS loģika — IEKŠĀ `assets/chrome-v1.js`. Fragmentā drīkst lietot `{{ assets_prefix }}`, `active_page` un `{{ assets_version }}` (kopš stingrās CSP `_rendered_chrome` to padod; citus mainīgos curated pārrenderēšana joprojām nepadod). Curated-mērķa regex idempotenti norij arī novecojušu inline chrome skriptu tieši aiz `</nav>` — vēsture CHANGELOG § 2026-07-23.
- **UI skaņas (cuelume) ir opt-in, noklusēti IZSLĒGTAS** — slēdzis navigācijā, stāvoklis `localStorage['atmina:sound']`; bibliotēka `assets/cuelume/` (cuelume@0.1.2, MIT, vendorēta VERBATIM ar LICENSE — atjaunināšana = visa direktorija nomaiņa, ne rediģēšana) lādējas tikai ar lazy `import()` no `chrome-v1.js`, URL atvasināts caur `document.currentScript` (Jinja prefiksa ceļš beidzās ar inline JS evakuāciju). Jaunas skaņas pievieno esošajā chrome-v1.js delegācijā; hover skaņas neliekam (mobilajā hover neeksistē, desktopā uzbāzīgi). Sedz `tests/test_base_sound.py`.
- **Kurētās statistika/finanses lapas rsync deploy sarakstā ir GAIDĪTAS** — `_sync_curated_chrome` katrā renderā iešuj dzīvo nav/footer, tāpēc `output/` kopija apzināti atšķiras no `curated/atmina/`. Tas nav drift.
- **Curated statistika re-freeze = datu-paritātes vārti:** `generate_statistika(output_dir=...)` → strip chrome/style → body byte-salīdzinājums → tikai tad pārkopē uz `curated/`. Nekad nepārraksti publicētus skaitļus akli. `finanses.html` = roku kurēts, bez ģeneratora.

## Balsojumi (saraksts + matrica)

- **Balsojumu kartītēm ir VIENS renderēšanas ceļš — klients** (`assets/bmv1.js::balsojumiArchiveRender` no kompaktā matricas JSON; Option-2 pārbūve 2026-07-17, lapa 6,4 MB → 425 KB). SSR vote-card bloku veidnē NEatjaunot — dubultais ceļš bija lapas uzpūšanās sakne un divu identiski uzturamu markup kopiju slazds. Sākuma renders no recent-sharda (~105 KB br), pilnais arhīvs tikai pie filtriem / lappošanas eskalācijas (`opts.wantFull`).
- **"Deputātu klātbūtnes reģistrācija" ir izslēgta render līmenī** (`_fetch_votes` prefiksa filtrs; DB rindas paliek — T8 auditi neskarti). Jauni balsojumu patērētāji, kas iet garām `_fetch_votes` (tiešs SQL), reģistrācijas notikumus izslēdz paši ar to pašu prefiksa formu — nekad `%reģistrācij%`.
- **Dziļo linku kontrakts:** `index`/profili linko `balsojumi.html#vote-<id>`; ja mērķis nav starp klienta renderētajām kartītēm, pirmais renders TŪLĪT atkāpjas uz Matricas tabu (bmv1 `applyHashScroll` to atrod pilnajā korpusā). Šo semantiku nemainīt bez visu ienākošo linku audita.

## Layout slazdi

- **`.hero-top` mobilajā kļūst `flex-direction:column`** → bērna `flex-basis:320px` kļūst par AUGSTUMU (320px tukšums). Jauniem `.hero-top` bērniem mobilajā vajag `flex:0 0 auto` (tas pats paterns kā `.hero-search`).
- **`.prv2-card` der TIKAI grid-2/pusplatumam** — pilnā 1fr kolonnā (~350px+) persona-galva pārklājas ar sev-badge. Pilna platuma rindai: banneris `grid-column: 1/-1` + sloti zem tā.
- **CSS specifika koplietotos blokos:** `.prv2-summary p` (0,1,1) uzvar jaunu vienas klases selektoru — krāsu/stila overrides koplietotiem blokiem raksta `parent p.class` formā.
- **`.brief-hero` 100vw full-bleed** ietver ritjoslas platumu → ~5px h-scroll (atvērts BACKLOG § Profili/UI).
- Kanoniskā breakpoint skala 600/768/900 dokumentēta pie `:root` (`assets/style.css`); vēsturiskos 480/560/640/700 migrē tikai pieskaroties komponentei.

## Verifikācijas (Playwright) slazdi

- **Pēc viewport resize Chart.js canvas dod STALE scrollWidth** (rāda viltus horizontālo pārplūdi) — horizontālā scroll pārbaudi dari ar SVAIGU lapas ielādi, ne resize. (Atkārtojies 07-04 un 07-07.)
- **Full-page screenshot + sticky nav = josla "iesprūst" lapas vidū** (scroll-šuves artefakts) — nav lapas defekts, nejaukt ar bugu.
