# Matricas izņemšana no `balsojumi.html` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Balsojumu saraksts pats atver jebkuru `balsojumi.html#vote-N` balsojumu (arī ārpus pirmajām 200 kartītēm), un tikai pēc tam Matricas cilne pazūd no lapas.

**Architecture:** Ja `#vote-N` mērķis nav starp pirmajā renderēšanā izvadītajām kartītēm, saraksts noskaidro balsojuma sēdes datumu no tā paša JSON (recent → vajadzības gadījumā pilnais arhīvs), uzliek mēneša + sēdes filtru un pārrenderē. Lasītājs redz visu tās dienas sēdi ar iezīmētu balsojumu; adrese kļūst `?menesis=…&sede=…#vote-N` (nosūtāma). Pēc tam izņem Matricas cilni, tās JS (~840 rindas `bmv1.js`), CSS un apakšcilņu joslu (paliek viena cilne). `balsojumi-matrica*.json` PALIEK — tas ir saraksta datu avots.

**Tech Stack:** vanilla JS (stingrā CSP), Jinja2, pytest + Playwright (Chromium).

**Spec:** `docs/audits/2026-10-16-matrica-likumprojekti/astra-plans-matrica.md` (7 atradumi — visi iestrādāti), `docs/audits/2026-10-16-matrica-likumprojekti/kritika.md` (§ Kāpēc tieši šāda secība, § Ko izņemšana skar), `astra.md`, `backlog/vietne-ui.md:9–11`, `wiki/operations/ui-conventions.md:31` (dziļo saišu kontrakts — šis plāns to maina apzināti, pēc saišu audita zemāk).

## Global Constraints

- UI valoda latviski; katrai jaunai virknei gramatikas + stilistikas pārbaude (CLAUDE.md § Output Conventions).
- JS tikai `assets/*.js`; nekādu inline skriptu vai `on*=` (`tests/test_no_inline_js.py`).
- Python vienmēr `.venv/Scripts/python.exe`.
- Helperi NEDRĪKST: `git stash`, `git checkout --`, `git restore`, `git reset`. Commit ar `git commit -F <fails>`.
- DB netiek mainīta. JSON formāts (`src/render/votes_matrix.py`) netiek mainīts — izņēmums Task 2b: tikai PIEVIENO laukus `fr`, `pp`.
- **Neko nedeploy. Publicēšana tikai ar operatora skaidru atļauju šim konkrētajam laidienam (escalation 7).**
- Testi: viens e2e redzamai uzvedībai (dziļā saite). Esošos testus pielāgo, nevis dublē. Vārts pierādīts tikai, ja redzēts KRĪTAM (mutācija).
- Faila nosaukumi `bmv1.js` / `blv1.js` paliek (kešu laušana caur `?v=`).

## Datu fakti (16.10. build, `output/atmina/`)

- `balsojumi.html#vote-` saites HTML: **969** (961 unikāls vid): `likumprojekti/` 962, saknes lapas 7. Ģeneratori: `templates/likumprojekts.html.j2:41`, `templates/index.html.j2:165,705`, `src/render/_common/enrich.py:194`, `assets/sav1.js:623` (izpildes laikā).
- No 961: **0** nav pilnajā JSON; 959 ir recent shardā; **764** ir ārpus pirmajām 200 nefiltrētā saraksta kartītēm (šodien tās aiziet uz Matricu).
- Lielākā sēdes diena: 2025-12-04 — 216 balsojumi (> `pageSize` 200). No 961 saitēm **0** krīt tās dienas 201.+ pozīcijā; tomēr kods to apstrādā (Task 1 Step 3).
- Mērījumu skripts: Task 1 Step 6 (tas pats atkārtoti pret jauno build).

## Review Focus

1. **Vecā saite ar citiem filtriem adresē** (`?tema=X#vote-N`, kur N neatbilst tēmai) → sēdes filtrs aizstāj adreses filtrus; balsojums atrodas.
2. **Neeksistējošs vid vs ielādes kļūda** → divi atšķirīgi teksti, bez cilpas, bez filtru maiņas.
6. **Novēlota recent atbilde** pēc pilnā arhīva nedrīkst pazemināt `DATA` (Astra #1, esošs defekts).
3. **Lietotāja filtru maiņa pēc dziļās saites** nedrīkst atkal pārslēgt filtrus (hash apstrāde notiek tikai vienreiz).
4. **`?tab=matrix`** vecā saite → parastais saraksts, bez kļūdas.
5. **`bmv1.js` kopīgās funkcijas** — saraksts pēc dzēšanas renderē identiski (esošie node + Playwright testi zaļi).

---

### Task 1: Saraksts pats atver `#vote-N`

**Files:**
- Create: `tests/test_balsojumi_vote_deeplink.py`
- Modify: `assets/bmv1.js` (`loadInto` sacensības labojums; +`window.balsojumiVoteDate`)
- Modify: `assets/blv1.js:86–147` (paaudzes komentārs, kļūdu callback), `:131–141` (Matricas atkāpe → sēdes filtrs), `:315–353` (`balsojumiSelectSession` → privāts dienas atlases helperis, komentāri)

**Interfaces:**
- Produces: `window.balsojumiVoteDate(vid: number, cb: (dateStr: string | null) => void, errcb: (msg: string) => void)` — meklē `DATA.votes[].vid`; ja nav un pilnais arhīvs nav ielādēts → `ensureData(true, …)` un meklē vēlreiz. `null` TIKAI pēc veiksmīgas pilnā arhīva pārbaudes; ielādes kļūda → `errcb` (Astra #3).
- Consumes: `ensureData`, `monthApi`/`sessionApi.setSelection`, `clearAllVoteFilters`, `applySessionOptionVisibility`, `applyFilters`, `runVoteHashScroll`.

**Hash stāvokļa mašīna (Astra #2)** — `blv1.js` viens stāvokļa mainīgais, ne divi karogi:
- `idle` → (pirmās ielādes renders, hash ir, kartīte nav atrasta) → `resolving`: stāvokli uzliek PIRMS `balsojumiVoteDate` izsaukuma.
- `resolving` → (datums) → dienas atlase VIENREIZ: `clearAllVoteFilters()`, `voteSearchQuery=''` UN `#vote-search.value=''`, mēnesis + sēde, `applySessionOptionVisibility()`, `applyFilters()`; piefiksē šī rendera paaudzi `hashGen` → `paging`.
- `paging` → katrā kartīšu callback ar `gen === hashGen` (arī `reset=false`): `runVoteHashScroll()`; atrasts → `done`; nav un `res.shown < res.total` → `renderArchive(false)`; nav un viss parādīts → `done` (info paliek parastais).
- `resolving` → (`null`) → `done`, info «Balsojums nav atrasts arhīvā.», filtri un adrese nemainās. → (`errcb`) → `done`, info «Balsojumus neizdevās ielādēt: …», bez atkārtota pieprasījuma.
- Jebkura lietotāja filtru maiņa (`applyFilters` no vadīklām) `resolving`/`paging` laikā → `done` (atcelts). Paaudzes pārbaude arī datuma un kļūdu callback (`blv1.js:143–145` šobrīd tās nav).
- Ja mērķis atrasts jau pirmajā renderā → filtri netiek mainīti (izņēmums nosaukts Task 3 kontraktā).
- **Lejupielāde (advisor):** dienas renders, ko izraisa hash, prasa pilno arhīvu TIKAI, ja datums atrasts tikai pilnajā (`wantFull: fullLoaded || !dateInRecent`). Recent shards griezts pa veselām dienām (`src/render/votes.py:87–91`, `vote_date >= cutoff`), tāpēc recent dienas filtrs ir pilnīgs. Citādi katra saite no likumprojekta lapas mobilajā lejupielādētu +625 KB br (šodien Matrica 959/961 gadījumos to nedara). Kad lietotājs pats maina filtrus, paliek esošā kārtība (filtrs → pilnais arhīvs).
- **Secība (advisor):** stāvokli `paging` un gaidāmo paaudzi uzliek PIRMS dienas `applyFilters()` — ar jau ielādētiem datiem `ensureData` callback izpildās sinhroni tā iekšienē. «Lietotāja maiņa → atcelts» āķis ir vadīklu `onChange` / meklēšanas / pogu ceļā (vai `applyFilters` arguments), ne pašā `applyFilters`, ko lieto arī mašīna. `_voteHashDone` iekļauj stāvokļa mainīgajā, nevis tur blakus.
- **`loadInto` labojums:** novēlotās recent atbildes izlaišana tik un tā izsauc `cb` (ar pilno `DATA`) un NEatiestata `_nameToPid`.

- [ ] **Step 1: E2E tests (failing).** Harness kā `tests/test_balsojumi_url_filters.py::_site` (Playwright, Chromium, `assets/` kopija). Fikstūru ģenerē testā ar precīzu sadalījumu: **5** vecākās dienas (tikai pilnajā) + **205** vidējās dienas + **20** jaunākās dienas = 230; recent = bez vecākajiem 5; deputātu `v` virknes katram JSON indeksētas atbilstoši. Veidnes opcijās divas tēmas, abi mēneši, visas 3 sēdes. **Katrs gadījums — jauna lapa** (pilna navigācija; `hashchange` klausītāja nav). Gaidīt gala stāvokli (kartīte + izcēlums vai gala info), ne tikai «Ielādē» pazušanu.
  - (0) Saucējs: bez hash «Rāda 200 no 230 balsojumiem.»
  - (a) vecākās dienas vid (tikai pilnajā): kartīte iezīmēta (`outline`), adrese tieši `?menesis=…&sede=…#vote-N`, sēdes un mēneša vadīklās šī izvēle, info «Rāda 5 no 5 balsojumiem.»; tās pašas adreses atvēršana jaunā lapā dod to pašu.
  - (b) vidējās dienas 203. kartīte → atrasta (automātiskā otrā lapa); pilnais JSON NAV pieprasīts (route skaitītājs 0). (a) — pieprasīts tieši vienreiz.
  - (c) `?tema=<zināma, mērķim neatbilstoša tēma>#vote-N` → atrasta, tēmas vadīkla notīrīta.
  - (c2) `?deputats=…&q=…&dalitie=1#vote-N` → atrasta; meklēšanas lauks tukšs, «Tikai dalītie» izslēgts, deputātu vadīkla tukša.
  - (d) `#vote-999999999` → info «Balsojums nav atrasts arhīvā.», adresē nav `sede`.
  - (d2) pilnā JSON pieprasījums atbild ar 500 (`page.route`) → info «Balsojumus neizdevās ielādēt…», adresē nav `sede`, pilnais JSON pieprasīts tieši vienreiz.
  - (e) pēc (a) lietotājs ar vadīklām izvēlas CITU sēdi (kur mērķa nav) → adrese, vadīklas un kartīšu kopa atbilst tikai lietotāja izvēlei.
  - (f) **Ielādes secība (Astra #1):** `page.route` aiztur recent atbildi; lietotājs tikmēr ieraksta meklējumu (pilnā ielāde pabeidzas); tad recent tiek atlaists; pēc tam izvēlas vecākās dienas sēdi → kartītes ir (5), nevis 0.
- [ ] **Step 2: Run → FAIL** (`.venv/Scripts/python.exe -m pytest tests/test_balsojumi_vote_deeplink.py -q`). Gaidāms: (a)(b)(c)(c2)(d)(d2) krīt (Matricas atkāpe), (f) krīt (sacensība).
- [ ] **Step 3: Implement.** (i) `loadInto`: recent atbilde, kas pienāk, kad `fullLoaded` jau ir, NEpārraksta `DATA` — callback saņem esošo pilno `DATA`. (ii) `balsojumiVoteDate`. (iii) stāvokļa mašīna augstāk; `window.switchTab('votes-matrix')` šajā vietā pazūd. (iv) novecojušo `blv1.js:86–88` komentāru pārraksta (sākuma `?deputats=` sacensības vairs nav; paaudze sargā lietotāja filtru maiņu ielādes laikā).
- [ ] **Step 4: Run → PASS.** Plus esošie: `tests/test_balsojumi_url_filters.py tests/test_balsojumi_coalition_at_vote.py tests/test_balsojumi_readability.py tests/test_balsojumi_client_render.py`.
- [ ] **Step 5: Mutācijas** (katru atsevišķi, ieraksti, kurš gadījums krīt, tad atjauno): (m1) atgriez Matricas atkāpi → (a); (m2) atslēdz automātisko nākamo lapu → (b); (m3) noņem atcelšanu/vienreizības sargu → (e); (m4) atgriez `loadInto` bez sacensības labojuma → (f); (m5) `null` vietā kļūdai → (d2); (m6) dienas renders vienmēr ar `wantFull: true` → (b) skaitītājs.
- [ ] **Step 6: Saišu audits pret īstu build (Astra #4).** Šaurs renders `--only=bills,balsojumi` (`wiki/operations/commands.md`). Divas daļas, abas ar saucēju:
  - **Datu līmenī:** HTML saišu kopa (gaidāms 961 unikāls) + `sav1.js` izpildes laika kopa no `data/saites-votes.json` (`byPid` → `meta[i].id`; Astra: 8395, no tiem 566 nav arhīvā — visi `Reģistrējies`/`Nereģistrējies`, klātbūtne apzināti izslēgta `src/render/votes.py:166–179`; esoša neatbilstība, NE šī darba regresija, Matrica tos arī neatrada). Izdrukā: kopas lielums / arhīvā / nav arhīvā + trūkstošo balsu etiķetes. Komanda — Astras skripts `docs/audits/2026-10-16-matrica-likumprojekti/astra-plans-matrica.md` § Pārbaudītie skaitļi.
  - **Pārlūkā** (Playwright skripts `.scratch/`, ne tests): visi 961 HTML vid; ja pārāk lēni — visi 764 ārpus pirmajām 200 + 20 nejauši + ≥5 vecie `sav1.js` mērķi ārpus HTML kopas + 1 klātbūtnes mērķis (gaidāms «nav atrasts»). CHANGELOG raksta FAKTISKO atvērto skaitu, atlasi un komandu — ne automātiski «961/961».
- [ ] **Step 7: Commit** («Balsojumi: saraksts pats atver vecu #vote- balsojumu»).

### Task 2: Izņemt Matricu

**Files:**
- Modify: `templates/balsojumi.html.j2` (dzēst `.subtab-bar` 25–28, `#votes-matrix-tab` 151–163, matricas komentārus 165–172, `tabs-v1.js` iekļaušanu; `#votes-list-tab` → parasts `<div>` bez `role="tabpanel"` un bez `aria-labelledby`; noslēdzošais `</section>` paliek; saite «Likumprojekti →» paliek kur ir)
- Modify: `assets/blv1.js` (dzēst `?tab=matrix` 409–413, matricas lazy-init 415–435, `switchTab`/`atminaTabs` 22–40, apakšcilņu deleģēšanu 437–446; `window.balsojumiSelectSession` vairs nav globāls (vienīgais ārējais izsaucējs bija Matrica, `bmv1.js:322`) — tā loģika jau ir Task 1 privātais helperis; `?tab=matrix` → `history.replaceState` noņem TIKAI šo parametru, citi filtri un hash paliek; `?tab=bills` pāradresācija `:13–16` paliek)
- Modify: `assets/bmv1.js` (dzēst matricai specifiskās funkcijas; galvenes komentārs)
- Modify: `assets/style.css` (matricas noteikumi)
- Modify: `tests/test_tabs_keyboard.py:100–104` (izņemt `balsojumi.html` no ceļu cilpas — tur vairs nav tablist)
- Modify: `tests/test_vote_result_non_binary.py:65–75` (Astra #6: grepē dzēšamo `resultBadgeClass` → garantiju pārceļ uz izpildītu kartītes iznākuma klasi; vispirms pārbaudi, vai `tests/test_balsojumi_readability.py:426–438` to jau sedz — mutācija: kartītes `resultDotClass` «Nod. kom.» → sarkans → tests KRĪT; tikai tad vecais tests tiek dzēsts)
- Modify: `src/render/politicians.py:274,662` komentāri, `src/render/votes.py` komentāri, `src/render/votes_matrix.py:10` docstring («patērē saraksts»)

- [ ] **Step 1: Funkciju keep/drop tabula** (`bmv1.js`, katrai funkcijai 22–1588: izsaucēji saraksta ceļā? → paliek). Zināmie saraksta atkarīgie: `loadInto`, `ensureData`, `nameToPid`/`_nameToPid`, `foldText`, `archiveFilterIndices`, `trackedForVote`, `trackedTableHtml`, `selectedVotesHtml`, `seatsHtml`, `factionRowHtml`, `readingStage`, `archiveBuildCard`, `archiveGroupHeader`, `factionIsSplit`, `voteIsSplit`, `resultDotClass`, `lvPlural`, `lvDate`, `escHtml`, `escAttr`, konstantes `VOTE_LABEL`, `_badgeForCh`, `NO_FACTION`, ielādes mainīgie (`DATA`, `RECENT_SRC`, `FULL_SRC`, `fullLoaded`), + jaunais `balsojumiVoteDate`. DZĒŠAMI (tikai Matricas ceļš): `resultBadgeClass` (vienīgais izsaucējs `showVoteDetail`), `ensureFullData` + `renderError` (izsaucēji tikai Matricā, `:379,390,950`). Tabulu ieliek commit ziņā vai `.scratch/`, orķestrators to pārbauda PIRMS dzēšanas.
- [ ] **Step 2: CSS audits pa noteikumam**, ne pēc prefiksa: `.matrix-toggle`/`.matrix-toggle.active` lieto `#vote-split-toggle` (paliek). Pārbaudīt arī ne-`matrix-` noteikumus: `.vote-filter-btn`, `.faction-bar-*`, `.stridgie-*`, `.detail-hint`, `.detail-default*`, `.bmv1-*` (`style.css:3281–3357,3656–3688,6770–6775`). PALIEK: `.attendance-bar*` (`partijas.html.j2:57`), `.detail-pane-empty` (`saites.html.j2:73`), `.syn-matrix*` (cita lieta). Katram dzēšamam selektoram `grep` pret `templates/`, `assets/*.js`, `src/` → 0 citu lietojumu.
- [ ] **Step 3: Dzēst** (templates, blv1, bmv1, CSS, komentāri).
- [ ] **Step 4: Šaurie testi.** `tests/test_tabs_keyboard.py`, `tests/test_vote_result_non_binary.py` pielāgo. Task 1 e2e testam pievieno: DOM nav `#votes-matrix-tab`, `.subtab-bar`, `#matrix-root`; `?tab=matrix&tema=…#vote-N` → saraksts, `tab` noņemts, pārējais paliek, 0 konsoles kļūdu. Palaid Task 1 Step 4 sarakstu + šos.
- [ ] **Step 5: Render bāzlīnija (PIRMS pilnās pārbaudes — Astra #7).** Bash: `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py -k balsojumi` (PowerShell: `$env:REGEN='1'`, komanda, `Remove-Item Env:REGEN`) → `tests/fixtures/render_baseline_bills.json`; diff: mainās TIKAI `balsojumi.html` hash (fails glabā arī likumprojektu karti — tai jāpaliek identiskai). Tad pilns `bash scripts/check.sh` bez `REGEN`.
- [ ] **Step 6: Vizuāla pārbaude** (ekrānuzņēmumi, 1280 + 390 px): `balsojumi.html`, `balsojumi.html#vote-<vecs vid>`, `balsojumi.html?tab=matrix`. Pārlūka konsolē 0 kļūdu.
- [ ] **Step 7: Commit** («Balsojumi: Matricas cilne izņemta»).

### Task 2b: Zāles kvadrātiņi rāda deputātu; saraksts kārtojams (operatora pieprasījums 2026-10-16)

**Recenzija:** `docs/audits/2026-10-16-matrica-likumprojekti/astra-plans-task2b.md` (6 atradumi — visi iestrādāti zemāk).

**Ko lasītājs iegūst:** uzbraucot ar peli uz krāsaina kvadrātiņa kartītes zāles joslā VAI frakcijas joslā, redz «Vārds Uzvārds · Frakcija · Par»; klikšķis atver profilu. Pieskāriens (telefons, skārienekrāns) atver to pašu lodziņu ar saiti «Profils →», nenavigē. «Kā balsoja katrs deputāts» sarakstu var kārtot: «Pēc vārda» (noklusējums) / «Pēc frakcijas» / «Pēc balss».

**Datu fakti (16.10. build):**
- Zāle: individuālo P/N/A pret `tot` un X pret `sum(fb.x)` sakrīt 7829/7829 (pilnais) → zāles kvadrātiņus var piesaistīt deputātiem.
- **Frakcija (Astra #1, bloķē):** JSON `politicians[].f` = deputāta JAUNĀKĀ netukšā frakcija (`votes_matrix.py::_build_matrix_data`, `latest_faction`), bet frakciju joslas `fb` skaita pēc `siv.faction` balsojuma brīdī (`votes.py::_fetch_votes`). Grupēšana pēc `p.f` NEsakrīt ar `fb` 7828/7829 balsojumos (piem. vid 5508: Ābrama PRO, JSON ZZS). CLAUDE.md T6 corollary: per-vote apgalvojums lieto TĀ balsojuma frakciju. Tātad: frakciju kvadrātiņi, lodziņa frakcija un saraksta frakcija/kārtošana NEDRĪKST lietot `p.f`.
- **Profils (Astra #2):** 122/139 ir lapa; trūkstošie 17 visi `relationship_type='inactive'` — profilu atlase `politicians.py::_fetch_politicians` (`NOT IN ('inactive','commentator')`) pret failu esamību sakrīt 139/139. **Esošs defekts:** `trackedTableHtml` un `selectedVotesHtml` saite uz profilu ir beznosacījuma → 17 deputātiem 404.
- Kvadrātiņi: 200 jaunākajās kartītēs ~36 600 (zāle + frakciju joslas).

**JSON paplašinājums (Global Constraints izņēmums — tikai pievieno laukus, esošos nemaina):**
- `politicians[pid].fr` — vēsturiskās frakcijas izpildes kodējums, indeksēts kā `v`: `[[startIdx, "FRAKCIJA"], …]` (jauna ieraksts tikai, kad frakcija mainās; NULL/tukšs → tā pati normalizācija kā `fb`, `ārpusfrakciju`/`OUTSIDE_FACTION` — palīgs pārbauda abas vietas un lieto VIENU funkciju). Abām šķembām; recent indeksi ir recent `v` indeksi. Avots `siv.faction`. `fb` skaitļus NEmaina.
- `politicians[pid].pp` — `1`, ja publisks profils (tas pats predikāts kā `_fetch_politicians`; neimportē smago renderētāju — predikātu iznes kopīgā konstantē/funkcijā vai dublē ar testu, kas abus salīdzina).
- Gate (datu līmenī, abiem JSON): grupēšana pēc `(fr frakcija pie i, balss)` == `fb` VISOS balsojumos (gaidāms 7829/7829 un 2788/2788); `pp` skaits == profilu lapu skaits build (122). Izdrukā saucēju.

**Files:**
- Modify: `src/render/votes_matrix.py` (`fr`, `pp`), tā testi (`tests/test_render_votes_matrix_json.py` vai kurš sedz `_build_matrix_compact` — palīgs nosauc)
- Modify: `assets/bmv1.js` — `trackedForVote` rindām `pid`, `factionAt(p, i)`, `profileUrl`; `seatsHtml` → `data-p`; `factionRowHtml` saņem šī balsojuma frakcijas deputātus; `trackedTableHtml` + `selectedVotesHtml` saite tikai ja `pp`; jauns `window.balsojumiSeatInfo(vid, pid) → {name, faction, ballot, profileUrl|null}` (atslēga `vid`, ne indekss — recent→full maina indeksus; Astra #6)
- Modify: `assets/blv1.js` — deleģēti klausītāji uz `#votes-archive-cards`, viens kopīgs lodziņš, kārtošana
- Modify: `templates/balsojumi.html.j2` — viens `<div id="seat-pop" popover>` ĀRPUS joslu `role="img"`/`aria-hidden` apakškoka
- Modify: `assets/style.css` (beigās)
- Modify: `tests/test_toggle_aria_pressed.py:95` — dzēst mirušo `.subtab-btn[data-tab="bills-list"]` pārbaudi (`.subtab-btn` lapā vairs nav; `#bills-list-tab` pārbaude paliek)
- Create: `tests/test_balsojumi_seats.py` (viens e2e)

**Dizains:**
- **Kvadrātiņa secība grupā:** frakcija pie balsojuma, tad vārds (zāle); frakcijas joslā — vārds. `.vs-e` bez `data-p`. `X` ar `data-p`, etiķete «Nebalsoja».
- **Interaktīvā pazīme abām joslām:** `.vote-seat[data-p], .vote-mseat[data-p]` (Astra #3) — vai kopīga klase; deleģēšana tikai `#votes-archive-cards` iekšā.
- **Grupas no `trackedForVote` rindām**, ko `archiveBuildCard` jau izsauc vienreiz — nepārskenēt deputātus katram kvadrātiņam.
- **Lodziņa stāvoklis (Astra #4):** aktīvais `{vid, pid, seat, mode: 'hover'|'tap'}`.
  - Hover ceļš: media query `(hover: hover) and (pointer: fine)` UN `event.pointerType === 'mouse'`. A→B: ja avots mainās — `hidePopover()` + `showPopover({ source: B })` (atkārtots `showPopover` atvērtam lodziņam enkuru NEpārceļ); tam pašam avotam — nekā. Aizvēršana pēc īsa taimera `pointerout`, atceļama, ja kursors pāriet uz lodziņu (lai var noklikšķināt saiti).
  - Klikšķis: ja pēdējais `pointerdown.pointerType === 'mouse'` un `pp` → navigē uz profilu; citādi (touch/pen) → atver lodziņu `mode='tap'`, NEnavigē. Touch `pointerout` neaizver.
  - `popover="auto"` light-dismiss + Esc → `toggle` notikumā notīra JS stāvokli. Pirms kartīšu nomaiņas (`renderArchive(reset)`) lodziņu aizver un atceļ taimeri.
  - Saturs ar `textContent`/esošo ekranēšanu; URL tikai `politiki/<slug>.html` no `pp`.
  - Bez `{source}` atbalsta (vecāki pārlūki) lodziņš atveras centrā — pieņemami; JS pozicionēšanas fallback NErakstīt.
- **Kārtošana:** pogas veido kopā ar slinko tabulu (`<details>` pirmā atvēršana — saglabāt slinkumu); `type="button"`, tieši viena `aria-pressed="true"`; pārkārto tikai `<tbody>`, fokuss paliek uz pogas. «Pēc frakcijas» = frakcija pie balsojuma, tad vārds; «Pēc balss» = Par, Pret, Atturas, Nebalsoja, tad vārds. Saraksta frakcijas kolonna arī rāda frakciju pie balsojuma (T6), ne `p.f`.
- **A11y:** kvadrātiņi nefokusējami (~36 600). Tastatūras ceļš = saraksts ar saitēm (tikai `pp`). Zāles `role="img"` + `aria-label` un frakcijas joslas `aria-hidden` paliek kā ir.

**good-css prasības (operators 2026-10-16 — ielādēt skill `good-css` pirms CSS; `interaction.md`, `show-and-hide.md`):**
- `[popover]`: iekš `@supports (position-area: block-end)` — `margin: 0; margin-block-start: …; position-area: block-end span-inline-end; position-try-fallbacks: flip-block, flip-inline, flip-block flip-inline` (margin TIKAI iekš `@supports`).
- `:hover` TIKAI iekš `@media (hover: hover) and (pointer: fine)`; `:active` pogām, lodziņa saitei un kvadrātiņam (krāsa/outline, bez izmēra maiņas — josla nelec); `:focus-visible` + `outline`, nekad `outline: none`.
- Kustība (ja vispār) tikai iekš `prefers-reduced-motion: no-preference`, nosauktas īpašības, ne `all`/`ease-in`.
- `inline`/`block` īpašības; krāsas no tēmas mainīgajiem, atvasinājumi `color-mix(in oklch, …)` (precedents `.lpv1-*`). Gaišais + tumšais.
- Mazā trāpījuma laukuma izņēmums (kvadrātiņi ~6 px telefonā) — operatora apzināts; hit-area paplašināšanu NEmēģināt.

- [ ] **Step 1: Datu gate (failing)** — `votes_matrix.py` testā: fikstūra ar frakcijas maiņu un ārpusfrakciju balsi; `(fr, balss)` grupas == `fb`; `pp` atbilst predikātam. Run → FAIL.
- [ ] **Step 2: Implement JSON** → PASS; datu līmeņa gate pret build (šaurs renders `--only=bills,balsojumi`): izdrukā 7829/7829, 2788/2788, `pp`=122.
- [ ] **Step 3: E2E (failing)** `tests/test_balsojumi_seats.py`, Playwright. Atsevišķa konsekventa HTTP JSON fikstūra (ne `_FIXTURE`/`_vote` noklusējumi): ≥2 Par vienā frakcijā, Pret/Atturas/X, deputāts bez ieraksta, viens bez profila (`pp` 0), frakcijas maiņa (`fr` ≠ `f`), ārpusfrakciju balss; vārdu/frakciju/balsu secības savstarpēji atšķirīgas; gaidītās secības ierakstītas tekstā, ne ar produkcijas komparatoru. Pagaidu vietnē izveido vienu `politiki/<slug>.html`. Serveris sūta produkcijas CSP galveni (no `assets/_headers`); tests ķer `pageerror` un CSP pārkāpumus. Gadījumi: (a) pele uz kvadrātiņiem — teksts katrā joslā sakrīt ar gaidīto (vārds, frakcija PIE BALSOJUMA, balss); per-josla: `data-p` unikāli, komplekts == gaidītais P/N/A/X, `.vs-e` bez `data-p`; (b) A→B hover — teksts UN enkurs mainās; pāreja uz lodziņu to neaizver; Esc aizver; (c) peles klikšķis ar profilu → navigē uz izveidoto lapu; bez profila → URL nemainās, saites nav (arī sarakstā); (d) `has_touch` konteksts + `tap` → lodziņš ar «Profils», URL nemainās; pieskāriens citur aizver; (e) kārtošana: «Pēc balss», «Pēc frakcijas», atpakaļ «Pēc vārda» — precīzas vārdu secības, viena `aria-pressed=true`, fokuss uz pogas; (f) pēc «Rādīt vairāk» (pilnā arhīva ielāde) agrākas kartītes kvadrātiņš joprojām dod pareizo deputātu. Run → FAIL.
- [ ] **Step 4: Implement JS/CSS/veidne** → PASS + Task 1 Step 4 testi + `tests/test_balsojumi_readability.py` + `tests/test_no_inline_js.py` + `tests/test_toggle_aria_pressed.py`.
- [ ] **Step 5: Mutācijas** (katru atsevišķi, pieraksti, tad atjauno): apgriezt vārdu secību grupā ar ≥2 → (a); `p.f` vēsturiskās frakcijas vietā → (a)/(e); kārtošanas apstrāde tukša → (e); bezprofila saite ieslēgta → (c); touch klikšķis navigē → (d); `showPopover` bez hide pie A→B → (b).
- [ ] **Step 6: Vizuāli** — ekrānuzņēmumi 1280 un 390 px, gaišais + tumšais; lodziņš pie kvadrātiņa augšējā/apakšējā malā (flip); saraksts ar pogām. Apskati pats un apraksti.
- [ ] **Step 7: Bāzlīnija** (`balsojumi.html` mainās — `#seat-pop`) kā Task 2 Step 5 (mainās TIKAI `balsojumi.html` hash); tad pilns `bash scripts/check.sh`.
- [ ] **Step 8: Commit** («Balsojumi: zāles kvadrātiņš rāda deputātu, saraksts kārtojams»).

### Task 3: Dokumenti

- [ ] `wiki/operations/ui-conventions.md:31` — dziļo saišu kontrakts: ja mērķis ir pirmajā renderā, filtri nemainās; citādi saraksts atver tā sēdes dienu (datums, ne sēdes ID — vienas dienas sēdes kopā), dienā >200 ielādē līdz mērķim; atsauce uz Task 1 testu. Klātbūtnes mērķi `sav1.js` saitēs → «nav atrasts» (esoša neatbilstība, sk. Ārpus tvēruma).
- [ ] `backlog/vietne-ui.md:9–11` — virtualizācijas punkts slēgts (Matrica izņemta); paliek atvērts tikai «divu deputātu salīdzinājums» sarakstā (HANDOFF-2026-10-16 § 3), ja tas tur jau nav.
- [ ] `wiki/CHANGELOG.md` — ieraksts ≤5 rindas: kas, kāpēc, Task 1 Step 6 FAKTISKAIS skaits + komanda, tests, Astras recenzija.
- [ ] CHANGELOG/ui-conventions skaidri: (1) deputātu saraksta frakcija tagad = frakcija PIE BALSOJUMA (T6), ne pašreizējā; (2) 17 neaktīvajiem deputātiem vairs nav profila saites (agrāk 404).
- [ ] `docs/arhivs/handoffs/HANDOFF-2026-10-16.md` rinda 6 — «Nākamais» aktualizēts.
- [ ] `docs/audits/2026-10-16-matrica-likumprojekti/README.md` — «Matrica izpildīta: CHANGELOG …».
- [ ] Commit.

### Task 4: Publicēšana (TIKAI ar operatora atļauju)

- [ ] Pilns renders (kopīgā navigācija netiek mainīta, bet `balsojumi.html` + assets jā; `pp` atbilst `politiki/` tikai pēc PILNA rendera) — `wiki/operations/deploy.md` kārtība, `scripts/check_output.py`.
- [ ] Operatora apstiprinājums → `bash scripts/deploy.sh --no-delete` → dzīvajā vietnē `balsojumi.html#vote-<vecs vid>` atveras sarakstā; `curl -sI` 200 `assets/bmv1.js?v=…`.

## Ārpus tvēruma (karogs, ne darbs)

- `saites.html` (`assets/sav1.js:623`) linko arī klātbūtnes (`Reģistrējies`/`Nereģistrējies`) ierakstus uz `balsojumi.html#vote-N` (566 mērķi), bet saraksts klātbūtni apzināti nerāda. Pēc šī darba tie rāda «nav atrasts» (agrāk Matrica tos arī neatrada). Labojums `sav1.js` pusē (klātbūtnei saiti neveidot) — atsevišķs lēmums.

- `balsojumi-matrica*.json` lauki, ko lietoja tikai Matrica (piem. deputātu novirzes `dis`), — JSON var saīsināt vēlāk; ietaupījums lejupielādē jāizmēra atsevišķi.
- «Divu deputātu salīdzinājums» un «atšķīrās no frakcijas» sarakstā — HANDOFF § 3 / kritika.md; frakcijas novirze gaida vēsturiskās frakcijas labojumu.
