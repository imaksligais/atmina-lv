# atmina.lv pārcelšana no koplietotā hostinga uz Cloudflare (Workers Static Assets) — dizains

Datums: 2026-09-15. Statuss: apstiprināts dizains, gaida izpildes plānu.

## Mērķis

Publiskā vietne (`output/atmina/`, ~208 MB, ~2 200 failu, pilnībā statiska) turpmāk
tiek mitināta Cloudflare Workers Static Assets, nevis koplietotajā cPanel/LiteSpeed
hostingā. DNS zona pāriet uz Cloudflare. E-pasts PALIEK pie līdzšinējā pasta
pakalpojuma (pārcelšana vēlāk, ārpus šī darba).

Kas NEMAINĀS: publicēšanas vārti (T15 — `check_output.py` + `publish_approvals`),
rutīnas, renderis, publiskā anonimitāte, stingrā CSP, publiskie URL.

## Kāpēc tieši tā (izvēles)

- **Workers Static Assets, ne Pages.** Visi publiskie URL nes `.html`
  (`sitemap.xml`: 1 004 no 1 008 `<loc>`; `canonical` tāpat). Pages `/x.html`
  bez izvēles pāradresē uz `/x` — katra iekšējā saite, sitemap un canonical
  saņemtu redirect lēcienu. Workers ļauj `assets.html_handling = "none"`:
  `/x.html` → 200, URL paliek tādi, kādi ir. `_headers`/`_redirects`, `404.html`
  (`not_found_handling = "404-page"`) un tieša augšupielāde ar `wrangler deploy`
  tur strādā tāpat kā Pages; Cloudflare dokumentācija pati sauc `wrangler deploy`
  par `wrangler pages deploy` aizstājēju. Pārbaudīts 2026-09-15:
  developers.cloudflare.com `/workers/static-assets/routing/advanced/html-handling/`,
  `/workers/static-assets/compatibility-matrix/`, `/workers/platform/limits/`.
- **Tieša augšupielāde no operatora mašīnas, ne Git-savienojums:** `output/`
  nav komitēts, DB nav publiska, un Git-būve apietu T15 vārtus.
- **Katrs deploy ir pilns koks.** Cloudflare augšupielādē tikai mainītos failus
  (satura hash), tāpēc ikdienā tas ir sekundes; versija aktivizējas tikai pēc
  pilnas augšupielādes (ieguvums pret rsync). „Additīvais deploy" kā jēdziens
  beidzas: koks serverī = `output/atmina/` pilnībā. Lokālais koks jau ir pilns —
  šaurais renders pārraksta tikai sava domēna apakškoku, nekad nedzēš pārējo.
- **Limiti (bezmaksas plāns):** 20 000 faili/versija, 25 MiB/fails, `_headers`
  ≤100 rindas. Šobrīd ~2 200 faili, lielākais < 20 MB.
- **Apzināts zaudējums:** bezpaplašinājuma URL (`/blog/2026-04-23`), ko
  `.htaccess` līdz šim pārrakstīja uz `.html`, pēc pārcelšanas dos 404. Neviena
  vietnes saite, sitemap vai canonical tos nelieto; ārējās saites uz tiem nav
  zināmas. Ja tādas atklājas (Umami 404 pieprasījumi pirmajā nedēļā), pievieno
  konkrētas rindas `_redirects`.
- `BACKLOG.md` § Ne-darīt ieraksts „NE Cloudflare-for-compression" (2026-05-30)
  noraidīja Cloudflare kā KOMPRESIJAS risinājumu; hostinga maiņa ir cits lēmums.
  Ierakstu papildina, nevis dzēš.

## Fāzes (katra ar atsevišķu operatora apstiprinājumu pirms izpildes)

### 1. DNS → Cloudflare (hostings vēl vecais)

1. Pirms maiņas: pilns esošās zonas eksports no reģistratora paneļa (A/AAAA,
   CNAME, MX, TXT — SPF, DKIM, DMARC, verifikācijas). Saglabā privāti
   (`.env`-klases fails, NE repo). Pieraksta arī, kā šobrīd strādā `www`
   (redirect uz apex vai otrādi).
2. Cloudflare bezmaksas plāns, zona `atmina.lv`, automātiskais imports.
3. Salīdzināšana ar acīm: katrs eksporta ieraksts eksistē importā. **Pasta
   ieraksti (MX, `mail.*`, autodiscover u.tml.) — proxy IZSLĒGTS (pelēks mākonis).**
   Vietnes A/CNAME sākumā arī pelēks (vecais hostings paliek sertifikāta avots),
   lai maiņa būtu tīri vārdserveru maiņa.
4. Vārdserveru nomaiņa reģistratorā. Gaidīšana līdz propagācijai.
5. Pārbaude: vietne atveras, e-pasts sūta un saņem (tests abos virzienos),
   `dig MX atmina.lv` rāda vecās vērtības.

Atpakaļceļš: vārdserveri atpakaļ uz reģistratora noklusējumu; zona Cloudflare
pusē paliek neizdzēsta līdz 4. fāzes beigām.

### 2. Servera koka audits („kas nav repo")

Runbooks `wiki/operations/deploy.md` fiksē, ka daži vēsturisko pārskatu attēlu
varianti eksistē TIKAI serverī. Cloudflare deploy ir pilns koks, tāpēc tiem
jābūt lokāli.

1. `ssh find` saraksts no servera; diff pret lokālo `output/atmina/`.
2. Katrs tikai-serverī fails: vai nu nokopē lokāli tur, kur renderis to sagaida
   (`output/images/briefs/` u.c.), vai apzināti atmet — saraksts ar lēmumu
   katram, pierakstīts CHANGELOG ierakstā pirms 3. fāzes.
3. Denominators ziņojumā: N faili serverī, M lokāli, K tikai serverī, kas
   darīts ar katru.

### 3. Workers projekts + konfigurācija (paralēli vecajam hostingam)

Koda izmaiņas repo:

- `wrangler.json` repo saknē (+ `!/wrangler.json` `.gitignore` allow-listā):
  `name`, `compatibility_date`, `assets: { directory: "./output/atmina",
  html_handling: "none", not_found_handling: "404-page" }`. Bez Worker skripta —
  tīri statisks. Nekā operatoru identificējoša tajā nav (konts nāk no env).
- `assets/_headers` — pārnes no `htaccess.template`: HSTS, nosniff, X-Frame,
  Referrer-Policy, CSP (bez izmaiņām saturā), kešatmiņas termiņi pa ceļu
  paterniem (`/assets/*`, `/images/*`, `/*.json`, `/data/*`).
- `assets/_redirects` — tikai ja audits vai 404 žurnāls atrod nepieciešamību
  (šobrīd nav zināma).
- Renderis: `_orchestrator.py` 14a solis kopē `_headers` (un `_redirects`, ja ir)
  tāpat kā `.htaccess`. `.htaccess` kopēšana paliek līdz 4. fāzes beigām, tad
  izņem kopā ar `htaccess.template`.
- `.json.br` / `.json.gz` blakusfaili: Cloudflare saspiež pati, rewrite vairs nav.
  Pirmajā deploy tos atstāj (nekaitē); ģenerēšanas izņemšana (`positions.py`,
  `votes_matrix.py`, `search_index.py`, `links.py`, `_common.py`) ir atsevišķs,
  vēlāks uzdevums.
- `scripts/deploy.sh`: rsync/ssh zars → `npx wrangler deploy` (konfigurācija no
  `wrangler.json`). Preflight (abi `check_output.py` vārti) paliek NEMAINĪTS un
  notiek PIRMS augšupielādes. `--dry-run` → tikai preflight + failu skaits, bez
  augšupielādes. `--delete`/`--no-delete` → pieņemti kā no-op ar paziņojumu
  (visi runbooki tos padod). `--no-output-check` paliek.
  Autentifikācija: `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` no
  `.env.deploy` (jau gitignored); `.env.deploy.example` atjaunots. Tokenam
  tikai `Workers Scripts:Edit` tiesības.
- Tests galvenēm (`tests/test_no_inline_js.py` klase): nolasa `assets/_headers`
  un apgalvo, ka CSP `script-src` NESATUR `'unsafe-inline'` un ka katrs
  `htaccess.template` `Header always set` nosaukums ir pārnests (vārts lasa to,
  ko rakstītājs raksta). Kamēr abi faili eksistē, tests arī apgalvo, ka CSP
  vērtība tajos ir identiska.
- `wrangler` versija piesprausta (`npx wrangler@<versija>`), pierakstīta
  `wiki/operations/deploy.md`.

Pārbaude uz `<name>.<konts>.workers.dev` PIRMS DNS pārslēgšanas (denominators
katrai):

- galvenes identiskas vecajam serverim (`curl -sI` diff uz 3 lapām: sākumlapa,
  politiķa lapa, pārskats);
- paraugs no `sitemap.xml` (≥20 URL, visi ar `.html`) → 200 BEZ redirect
  (`curl -sI` rāda 200, ne 30x) — tas ir `html_handling: none` vārts;
- nezināms URL → 404 ar `404.html` saturu; `robots.txt`; `sitemap.xml`;
- `pozicijas-data.json` un pārējie sidecar JSON → 200 ar `content-encoding: br`
  vai `gzip`;
- Umami analītika ielādējas (CSP `connect-src` neskarts);
- `finanses.html`, `statistika/` klātbūtne (kurētais saturs);
- pārskatu hero attēlu paraugs (≥10) → 200.

### 4. Pārslēgšana + rezerve

1. `wrangler.json` `routes: [{pattern: "atmina.lv", custom_domain: true},
   {pattern: "www.atmina.lv", custom_domain: true}]` — Cloudflare pati ieraksta
   DNS un izsniedz sertifikātu. `www` → apex (vai otrādi, kā 1. fāzē fiksēts):
   Cloudflare Redirect Rule zonā.
2. Pārbaude tā pati kā 3. fāzē, bet uz `atmina.lv`.
3. Vecais hostings paliek neaiztikts ≥30 dienas kā atpakaļceļš (DNS atpakaļ uz
   veco A ierakstu = minūtes). Pēc tam: `.htaccess` kopēšana + `htaccess.template`
   izņemšana, `deploy.md` pārrakstīšana, CHANGELOG ieraksts, BACKLOG Ne-darīt
   papildinājums, `.claude/commands/dienas-rutina.md` + `deep-check.md` deploy
   rindu formulējums.

## Kļūdu apstrāde

- `wrangler` kļūme augšupielādē → ne-nulles izeja, `deploy.sh` apstājas; daļēja
  versija neaktivizējas.
- Trūkstošs token → tas pats `: "${VAR:?}"` paterns kā tagad.
- Limiti — `deploy.sh` preflightā pieskaita failus un ziņo skaitu; > 15 000 =
  brīdinājums; fails > 25 MiB = apstāšanās.
- Bezpaplašinājuma URL 404 — apzināts, sk. § Kāpēc.

## Ārpus tvēruma

E-pasta pārcelšana; `.br/.gz` ģenerēšanas izņemšana; Cloudflare kešatmiņas
noteikumi ārpus `_headers`; dashboard deploy poga (`src/dashboard/views/deploy.py`)
sauc `bash scripts/deploy.sh --no-delete` — karogs paliek pieņemts, tāpēc tur
nav izmaiņu.

## Riski

- DNS imports izlaiž pasta TXT ierakstu → pasts nonāk spamā vai netiek piegādāts.
  Aizsargs: 1. fāzes 3. solis ar pilnu eksporta sarakstu, tests abos virzienos.
- Tikai-serverī faili pazūd. Aizsargs: 2. fāze ar denominatoru, pirms 4. fāzes.
- Publicēšanas vārtu apiešana ar tiešu `wrangler deploy` no rokas. Aizsargs:
  runbooki min tikai `deploy.sh`; `.claude/agents/claim-extractor.md` 11. punkts
  paliek spēkā (aģenti neizsauc deploy).
