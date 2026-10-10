# Deploy (atmina.lv)

## Cloudflare Workers Static Assets (kopš 2026-09-16, 3. fāze)

Statiskā vietne (`output/atmina/`, pilns koks) tiek publicēta Cloudflare ar
`wrangler deploy` pēc `wrangler.json` (`html_handling: none` — publiskie URL
nes `.html` un atbild 200 bez redirect; `not_found_handling: 404-page`).
Migrācijas spec + plāns: `docs/superpowers/specs/2026-09-15-cloudflare-pages-migracija-design.md`,
`docs/superpowers/plans/2026-09-15-cloudflare-migracija.md`.

```bash
# 1. Renders — kā līdz šim (šaurais ar `static` līdzi; static kopē arī _headers/_redirects/.assetsignore)
.venv/Scripts/python.exe -m src.render --only=dashboard,blog,static

# 2. Sausais reiss: abi preflight vārti + failu skaits, wrangler NETIEK saukts
bash scripts/deploy.sh --dry-run --no-delete

# 3. Īstais deploy (pilns koks, ~10–60 s; pirmajā reizē npx lejupielādē wrangler)
bash scripts/deploy.sh --no-delete

# 4. Dzīvā pārbaude — 9 pārbaudes, katra ar denominatoru n=; exit 1, ja kāda krīt
.venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv
```

- **Akreditācija:** `.env.deploy` (gitignored) — `CLOUDFLARE_API_TOKEN` +
  `CLOUDFLARE_ACCOUNT_ID` (paraugs `.env.deploy.example`). Tokenam ir TIKAI
  `Account · Workers Scripts · Edit` (izveidots 2026-09-16 kā „atmina deploy
  (Workers Scripts:Edit only)"); tas neredz DNS, pastu, rēķinus. Ja `wrangler`
  prasa interaktīvu login — token nav eksportēts, pārbaudi `DEPLOY_ENV_FILE`.
- **Domēni `atmina.lv` + `www.atmina.lv` ir piesaistīti PANELĪ** (Workers & Pages →
  atmina → Domains → Add Domain), NEVIS `wrangler.json` `routes` blokā: `custom_domain`
  sinhronizācija prasa zonas tiesības (Workers Routes / DNS Edit), ko deploy token
  apzināti nesaņem — ar `routes` konfigā katrs deploy krita ar auth 10000 (2026-09-16).
  `workers_dev: false` — pagaidu adrese izslēgta (nav dubultsatura). `www → apex` 301 =
  zonas Redirect Rule (veidne „Redirect from WWW to root", preserve query string);
  `http → https` = SSL/TLS → Edge Certificates → Always Use HTTPS. Abi ir paneļa
  iestatījumi, ne repo — `tests/test_wrangler_config.py` sargā, ka `routes` nav konfigā.
- **Deploy jātaisa no native Windows shell (Git Bash / PowerShell / CMD), ne WSL.**
  WSL shellī `npx` ir Windows binārs caur interop, un Linux `export` env
  mainīgie uz Windows procesu neaiziet — `wrangler` krīt ar
  «CLOUDFLARE_API_TOKEN … non-interactive environment», lai gan `.env.deploy`
  ir korekts un `:?` guardi skriptā iet cauri (2026-09-19). WSL `WSLENV` to
  nepaglābj (pārbaudīts — vars ir WSL procesa env, bet interop to neizplata
  npx→node ķēdē). Apdare, ja nācies WSL: `powershell.exe -NoProfile -File
  scratchpad/deploy_cf.ps1` (ielasa `.env.deploy` un sauc wrangler).
  **Uzmanību:** šajā mašīnā `C:\Windows\system32` ir PATH priekšā Git `usr/bin`,
  tāpēc kails `bash` = WSL bash. Ne-interaktīvā aģenta sesijā deploy palaid ar
  eksplicito Git Bash: `"/c/Program Files/Git/usr/bin/bash.exe" -c 'cd /e/atmina
  && export PATH="/usr/bin:$PATH" PYTHONUTF8=1 TEMP="C:\Windows\Temp"
  TMP="C:\Windows\Temp" SQLITE_TMPDIR="C:\Windows\Temp" && bash
  scripts/deploy.sh --no-delete'` (2026-09-21). Bez tam divi papildu slazdi:
  (a) bez `PYTHONUTF8=1` `check_output.py` krīt ar `UnicodeEncodeError` uz `ā`
  (stdout = cp1252 pipe); (b) bez `TEMP`/`TMP` sqlite `mode=ro` vaicājums ar
  `ORDER BY` krīt ar «unable to open database file» — sortējumam vajag temp
  failu, un tukšs `TEMP` to liedz (prettiesti: `SQLITE_TMPDIR`).
- **`wrangler` versija piesprausta** `scripts/deploy.sh` (`npx wrangler@4.132.0`);
  pārraksta ar `WRANGLER_CMD`. Cita versija = apzināts lēmums + šī rinda.
- **Deploy vienmēr ir PILNS koks.** `--no-delete` / `--delete` paliek pieņemti
  kā no-op (dashboard poga, runbooki un `.claude/commands/*` tos padod). Nav
  „additīvā" režīma: tas, kā nav `output/atmina/`, pēc deploy nav arī live.
  Tāpēc pirms deploy koks ir jāpārrenderē tik plaši, cik ir mainījies —
  šaurais renders NEIZMET citu domēnu lapas, tās paliek kokā no iepriekšējā.
- **Preflight nemainīts:** `check_output.py` + `--publish-gate-only` PIRMS
  augšupielādes; `--no-output-check` ir apzināta apiešana. Papildu vārti
  transportā: >15 000 failu brīdinājums, >25 MiB fails = kļūda, `_headers`
  trūkst kokā = kļūda (renderē `static`).
- **Galvenes:** `assets/_headers` (CSP identiska `htaccess.template`, tests
  `tests/test_headers_file.py`). **Pārrakstīšana:** `assets/_redirects` —
  `/ /index.html 200` (bez tās kailā adrese ir 404, jo `html_handling: none`
  neatvasina sakni; `tests/test_redirects_file.py` aizliedz `.html` avotus).
  **Neaugšupielādē:** `assets/.assetsignore` — `.htaccess`, `assets/htaccess.template`,
  `assets/_headers`, `assets/_redirects` (citādi publiski lasāmi).
- **Bezpaplašinājuma URL** (`/blog/2026-04-23`) — 404 kopš Cloudflare (apzināts,
  spec § Apzināts zaudējums); ja Umami rāda tādus, pievieno rindu `_redirects`.
- **Kurētie `finanses/` + `statistika/`** nāk no `curated/atmina/` caur
  `_copy_curated` un ir kokā — pilns deploy tos nes līdzi (2. fāzes audits
  2026-09-15: 10/10 abās pusēs).
- **Drošības slēdži, DNS un Security Insights ieteikumi** — atsevišķs runbook:
  [cloudflare-security.md](cloudflare-security.md) (SPF/DMARC soļi, Bot Fight
  Mode un AI Labyrinth noraidījumi, `security.txt`, „ko nekad" saraksts). Neviens
  no tiem nav darāms no repo: šim tokenam nav zonas tiesību.

## Komandas — renders pirms deploy

Standarta režīms ir šaurais renders pēc tā, kas mainījies (`static` vienmēr līdzi —
about skaitļi + sitemap). Pilnais renders (visa vietne, ~3 min) — tikai
release/baseline vai pēc bāzes veidnes/assetu maiņas:

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

Nekad `rmtree output/atmina` mērīšanai vai tīrīšanai — renderē uz tmp mapi. Tukšāks
koks = tukšāka vietne pēc nākamā deploy. (Līdz 2026-09-16 rsync deploy bija
additīvs; tagad `--no-delete`/`--delete` ir no-op.)

## Preflight vārti pirms wrangler (abi obligāti, automātiski)

`deploy.sh` pirms `wrangler deploy` izpilda divas pārbaudes ar `.venv` python;
katra kļūme = `exit 1`, deploy nenotiek. Apzināta apiešana: `--no-output-check`
(viens karogs ABIEM vārtiem).

1. **`scripts/check_output.py`** (kopš 2026-08-01) — uzbūvētā koka atsauces
   (`src=`/`href=`/og:image) izšķiras pret failu + `sitemap.xml` abos virzienos.
   Salauzta atsauce aizietu live un tur paliktu, tāpēc pārbaude ir pirms
   augšupielādes, ne pēc. Izņēmumi: `scripts/output_check_allowlist.txt` (ar iemeslu).
2. **`scripts/check_output.py --publish-gate-only`** (kopš 2026-08-09, T15) —
   neviens deploy nedrīkst aiznest `blog/<datums>.html`, kuras pārskats nav izgājis
   publicēšanas vārtus: (a) `brief_images.approved=1` UN (b) ieraksts
   `publish_approvals` (`scripts/approve_publish.py <YYYY-MM-DD>`, nedēļai
   `nedela-<YYYY-MM-DD>`). `check.sh` pilnais renders liek dienas MELNRAKSTU kokā,
   un deploy aiznes visu koku. Orfāna lapa bez DB pārskata = bloķē; DB nepieejama =
   hard fail. Apzināti NAV `check.sh` daļa — tam jāpaliek zaļam, kamēr melnraksts
   kokā eksistē.

Ja publish-gate bloķē deploy pirms vakara rutīnas beigām — tas ir vārtu mērķis, ne
kļūme: pabeidz vārtus vai izņem melnraksta lapu no koka.

## Arhitektūra

- `scripts/deploy.sh` — preflight vārti + transporta vārti (failu skaits, 25 MiB,
  `_headers`) + `npx wrangler@<versija> deploy`. Pēc īsta deploy raksta
  `logs.action='deploy'` (versijas ID, failu skaits, apstiprinātie slugi) — to lasa
  rutīnas solis «11. Deploy»; log kļūme deploy negāž.
- `wrangler.json` — Worker konfigurācija (`assets.directory` = `output/atmina/`,
  `html_handling: none`, `not_found_handling: 404-page`, bez `routes`).
- `.env.deploy` (gitignorēts) + `.env.deploy.example` (izsekots paraugs).
- `scripts/verify_host.py` — dzīvā pārbaude pēc deploy.

## Verifikācija pēc deploy

`verify_host.py --base https://atmina.lv` — 9 pārbaudes ar denominatoru `n=`
(galvenes, sitemap lapas 200 bez redirect, 404 lapa, robots/sitemap, JSON
kompresija, kurētās lapas, hero attēli, `security.txt`, `served_by_cloudflare`).
Versija: `npx wrangler@4.132.0 deployments list`.

**Vispirms — kurš hosts tev atbild (2026-09-16 vakara mācība).** Šīs mašīnas
resolvers `atmina.lv` vēl deva veco Namecheap IP (`162.213.255.90`,
`server: LiteSpeed`) arī pēc `ipconfig /flushdns`, kamēr `nslookup atmina.lv 1.1.1.1`
jau deva Cloudflare. Deploy bija dzīvs (`wrangler deployments list` → versija 100 %),
bet `curl https://atmina.lv/...` no šejienes rādīja VECO lapu un izskatījās pēc
nenostrādājuša deploy. `verify_host.py` pārbaude `served_by_cloudflare` to
tagad ķer; ja tā krīt — pārbaudi ar `curl --resolve atmina.lv:443:<CF IP no 1.1.1.1>`,
ne ar atkārtotu deploy. Kad vecais hosts 2026-10-16 tiks izslēgts, novecojis
resolvers dos savienojuma kļūdu, ne vecu lapu.

## Politiķa deaktivācijas checklist (`relationship_type='inactive'`)

Deaktivēta politiķa lapa **pati nepazūd** no `output/` (2026-06-13 Kļaviņa/Freidenfelda mācība):

1. `generate_public_site()` pārstāj lapu ģenerēt, bet **NEdzēš** stale `politiki/{slug}.html` — dzēs to manuāli no `output/atmina/politiki/` un deploy: koks iet pilns, tāpēc lapa pazūd arī no live vietnes. Pirms deploy `check_output.py` pateiks, ja kāda cita lapa uz to vēl saista.
2. `inactive` filtrē: x.py, positions.py, dashboard, personas, parties, links (nodes), profila ģenerāciju. Pārbaudi `political_tensions` — ja deaktivētajam ir tensions rindas, dzēs tās vai pārliecinies, ka render filtrs tās izlaiž (dangling-link risks spriedzes.html / saites grafā).
3. Editorial sintēzes (manuāls teksts) var pieminēt vārdā — operatora editorial lēmums, ne automātika.
4. **`wiki/persons/<slug>.md` paliek un kļūst par orphan** — `wiki_sync()` deaktivēto no `wiki/persons/personas.md` izņem, bet pašu lapu nedzēš, tāpēc `wiki_lint` to mūžīgi rāda kā `orphan_page` un `index.md` statusā stāv „Lint: N orphans". Tas ir GAIDĪTS, ne defekts (2026-07-25: 1 orphan = Freidenfelds, id=190). Ja orphans krājas, dzēs lapu manuāli; pirms tam apsver, vai tās pozīcijas vēl vajag vēsturei.
5. Ja profils dzēšams PILNĪBĀ (privātuma lūgums, 2026-06-13 precedents): backup DB pirms purge; vec0 vektoru tabulām vajag `sqlite_vec.load()`; `claim_vectors`→claim_id, `document_vectors`→chunk_id.

## Vecais hostings — Namecheap (rezervē līdz 2026-10-16)

Līdz 2026-09-16 vietne gāja uz Namecheap koplietoto hostingu caur rsync over SSH
(vecais `scripts/deploy.sh`: `git show c4b5289d^:scripts/deploy.sh`). Hostings
paliek auksta rezerve līdz 2026-10-16 (BACKLOG 67, Task 9). Ārkārtas atkāpšanās,
SSH/cPanel iestatīšana, rsync uz Windows un problēmu tabula:
[deploy-namecheap-arhivs.md](deploy-namecheap-arhivs.md). Ikdienā tur neko nedara.
