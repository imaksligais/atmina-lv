# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Publiskā vietne — renderēšana un veiktspēja

### [OPERATOR] Nākamie «Atradumi» — Toca deklarācijas un tiesas lieta par policijas izpostītu dārzu (sadaļa kopš 2026-10-17)

Sadaļa ieviesta 2026-10-17 (`kind: atradums`, `src/render/analyses.py`, `tests/test_atradumi.py`; pirmais — `visvanati-pilsoniba-2026`, CHANGELOG 2026-10-17 (1)). *Trigeris:* X izplatās īsi izmeklējumi, kuriem vietnē nav lapas: tiesas lieta par policijas izpostītu dārzu (09-09). Toca deklarācijām lapa jau ir — `analizes/vad-izmeklesana-2026` (09-19, papildināta 10-20, nav `kind: atradums`); **atsevišķu atradumu neveido** (operators 2026-11-03). Dārza tiesas lietai — tikai, ja to nes oficiāli avoti (tiesu nolēmumi, reģistri). *Rīcība:* nākamās lapas pēc plāna `docs/superpowers/plans/2026-10-16-atradumi-sadala.md` (Task 6); privātpersonām tikai oficiāli reģistri un tikai tas, kas tieši skar publisku lēmumu. Katrai lapai — atsevišķa operatora atļauja. *Īpašnieks:* operators.

### [DEFERRED] Wiki pārskati grafā izolēti — pārskatiem nav strukturēta dalībnieku saraksta (2026-10-18)

`context_notes.opponent_id` ir NULL visiem 219 pārskatiem, tāpēc wiki grafā tie stāv izolēti (Saites redizaina plāna B3, `cfbe7f9e`). Ceļš caur citēto URL ↔ `claims.source_url` NAV dalībnieku saraksts — raksts nes arī pārskatā neapspriestu politiķu pozīcijas; to neieviest. *Trigeris:* pārskatu glabāšanā parādās strukturēts dalībnieku saraksts (piem. no skeleta). *Rīcība:* tad wiki saites no šī saraksta. *Īpašnieks:* operators.

## Profili / UI

### [OPEN] Partiju krāsas — atlikums pēc 2026-11-11 (ārpus Saeimas partijas, kontrasts)
- **Problēma:** 11.11. sešas Saeimas partijas pārkrāsotas pēc logo (CHANGELOG 2026-11-11 (1)). Partiju lapā AS #f5ae00 ir tuvu ASL #fbbf24 un GKR #f59e0b, JV #4cae5a — ZZS #84cc16. Kontrasts pret fonu (dataviz validators): tumšajā tēmā NA 1,75:1, gaišajā AS 1,67:1 — atšķiramas tikai ar leģendas nosaukumiem.
- **Rīcība:** ārpus Saeimas partiju krāsas pārskatīt pret logo ar to pašu metodi (`fix`+`rollback`, validators, pilns renders); ja kontrasts traucē — tumšās tēmas tonis kodā (`parties.color` ir viena kolonna abām tēmām).
- *Trigeris:* operatora lūgums vai lasītāja signāls. *Īpašnieks:* operators.

### [OPEN] Sava vizuālā identitāte — unikāls fonts (2026-10-08, zema prioritāte)
- **Signāls:** lasītāja komentārs Reddit: lapa izskatās pēc «noklusējuma Claude izvades», tāpēc dati šķiet mazāk ticami. Fakts: Styrene netiek lietots (sistēmas sans + serifs + JetBrains Mono; serifs kopš 2026-10-11 ir pašmitināts Source Serif 4, Georgia tikai rezerve — CHANGELOG 2026-10-11), bet serifa virsraksti + mono etiķetes + krēmīgi toņi + sepijas attēli veido atpazīstamu AI-ģenerētu stilu.
- **Rīcība (operators 2026-10-08: «vēlāk darīsim ar savu unikālo fontu»):** savs burtveidolu pāris (LV diakritika!), krāsa, logotips. Paralēli — redzamāka «Kā mēs strādājam» un labojumu žurnāls; `about`/`kontakti` roku veidotā varoņa galvene → kopā ar šo (nav `pagehead`). Tumšās tēmas toņi: `--bg` viens avots (`chrome-v1.js`, `theme-init.js` literālis piesprausts testā). *Īpašnieks:* operators.

### [OPERATOR] Tēmu ikonas — live kopš 2026-11-23 (`51d58620`); atlikums: ikonu izvēle, profila saraksts
- **Izdarīts:** 35 tēmām Lucide ikona tonētā kvadrātiņā tēmu direktorijā (`temas.html`) un tēmas lapas virsrakstā; `TOPIC_ICONS` blakus `TOPIC_COLORS` (`src/render/_common/constants.py`), sprite `assets/topics.svg` būvē `scripts/build_topic_sprite.py`; noteikumi `wiki/operations/ui-conventions.md` § Tēmu ikonas. Bildes un mērījumi `.scratch/temu-ikonas/`.
- **Publicēts 23.11.** ar operatora «Ok, lieliski … publish» (deploy `51d58620`); dzīvajā Chrome 390 px: ikonas uzzīmētas 37/37 trīs lapās, konsoles kļūdu 0 (`.scratch/temu-ikonas/live_check.py`).
- **Sānu svītra noņemta** tēmu kartītēm (operators 2026-11-25; `ui-conventions.md` § Tēmu ikonas).
- **Operatoram (nav atbildēts):** ikonu izvēle nav apstiprināta pa vienai, strīdīgākās: Ukraina un Krievija (swords), Korupcija un KNAB (hand-coins), Pensijas (piggy-bank), Saeimas darbs (scroll-text), Imigrācija (id-card), ES politika (circle-star).
- **Nav pārbaudīts:** Android emulators; WebKit (iPhone) tumšā tēma; esošās tēmu birkas, kas tumšajā tēmā krāsu jauc `in oklch` (ikonām tas WebKit mainīja toni).
- **Nav darīts:** profila tēmu saraksts (tur tēmas ir birkas — sākotnējais plāns birkās ikonas neliek); sākumlapā tēmu režģa vairs nav. `TOPIC_COLORS` nav pārtaisīts par `{color, icon}` — divas vārdnīcas ar vienādām atslēgām, ko sargā `tests/test_topics.py` (mazāks diffs: krāsu lasa 6 moduļi).
- *Jaunai tēmai:* ieraksts abās vārdnīcās + sprite pārbūve (tests krīt, ja aizmirsts).

### [OPEN] UI audits 2026-10-27 — atlikums (S1 nedēļas diagramma, kastes→līnijas, S2)
Audits ar 6 pārbaudītājiem, ~240 ekrānuzņēmumi: [`docs/audits/2026-10-27-ui-audits/README.md`](../docs/audits/2026-10-27-ui-audits/README.md). Izlabots 28.10. (S1 + skaitļi LV + emoji + galvene/kājene; sk. § Statuss). Nedēļas diagramma → HTML komponente 28.10. (`_weekly_movers_for_render`, `tests/test_render_weekly.py`). *Atlikums:* ēnotas kartītes → hairline; pilulas uz neinteraktīva teksta; Tailwind krāsu tokeni; vāka bilde pār visu ekrānu; S2 saraksts (profils, pozīciju filtri telefonā, analīžu 5 dizaina ģimenes, ziņu lapa 12 MB bez lapošanas). Pretrunām divas vārdnīcas — operatora lēmums. *Īpašnieks:* operators (prioritāte).

### [OPEN] UI review — atlikums pēc 1.–3. fāzes (2026-07-04 dizaina audits)
Pabeigtais darbs — trīs fāzes, sākumlapas pārveide un visi commit heši — pārcelts uz [CHANGELOG arhīvu § 2026-07-04 UI dizaina audits](../wiki/CHANGELOG-arhivs.md) 2026-08-03. Šeit paliek TIKAI atlikums.

- **`#8b8fa3` atlikums CSS/veidnēs** (Python kodā → `FALLBACK_COLOR` 2026-10-11): `assets/style.css` `.focus-quote-card` `var(--pc, #8b8fa3)` (nomaiņa mainītu gaišo tēmu), `templates/politician.html.j2` `party_color` rezerves vērtība; vietas atrod `git grep -n 8b8fa3 -- assets templates` (rindu numuri dreifē).
- **Dizaina parāda paliekas:** font-size/line-height TOKENIZĀCIJA (apzināti atlikta — simtiem deklarāciju, mazs redzamais ieguvums); vēsturiskie breakpointi 480/560/640/700 (dokumentēti pie :root, migrē tikai pieskaroties komponentei); statistika-detail "N ieraksti" lv_plural (curated re-freeze vārti).
- **A11y paliekas (no 2. fāzes):** nav `aria-label="Galvenā izvēlne"` prasa `_CHROME_SPECS` regex paplašināšanu `<nav class="nav"[^>]*>` (`_orchestrator.py:176-177`, backward-compatible — vajag operatora svētību frozen-regex maiņai); statistika canvas sparklines teksta alternatīva (curated); zinas/pretrunas feed-item virsraksti; skip-link + typeahead nav uz curated lapām (nav sgv1.js → plain GET fallback, apzināti pieņemts).
### [OPEN] Profilu UI parāds — sintēzes ports, Bloks 3, UX tier 3

Trīs ieraksti, apvienoti 2026-08-05, skar vienu virsmu — **pārbaudi, kas jau izdarīts, pirms sākt.** 2. līmeņa plāns: `docs/plans/2026-07-26-profila-ux-tier2.md`; ātrviežu pakete DONE (CHANGELOG § 2026-07-26). Plāna 2. punkts (tēmu čipu deep-link) IZPILDĪTS 2026-09-05 (`60665b11`, `tests/test_profile_topic_deeplink.py`); 1. un 3. punkts (citāts Pozīciju cilnē, `Atturas` skaidrojums) IZPILDĪTI 2026-10-09 (`tests/test_profile_positions_quote.py`); atvērts — pretrunu flags. Agrākais pilnais teksts: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

- **Wiki sintēzes bloku ports uz publisko UI:** `wiki_sync()` raksta synthesis bloku (top tēmas / 30 d / spriedzes / pretrunas) starp `<!-- SYNC-AUTO -->` markeriem (plāns `docs/superpowers/plans/archive/2026-04-20-wiki-synthesis-block.md`) — tos pašus datus parādīt **publiskajās politiķu profila lapās**.
- **Bloks 3** (slāņi 1+2+3 MERGED 2026-05-14): Saeimā cilnes redizains (prasa „svarīga balsojuma" definīciju); Saites story-driven sub-summaries; Publikācijas filtri žurnālistiem (prasa documents metadata paplašinājumu); data freshness + citation poga (dalīšanās pogas — 2026-10-23); URL hash deeplink no ārpuses; VAD delta bloks Pārskatā (atsevišķs spec). Review saturs: `git show c03ce566^:wiki/profile-page-review.md`.
- **Pārskats cilne tieva** lielākajai daļai profilu (Bloks B prasa `confirmed=1 AND salience≥0.5`). Izdarīts: aktivitātes grafiks (`monthly`), «Balso kopā ar savu frakciju» (CHANGELOG 2026-10-09 (8)). Par/Pret/Atturas mini-bar — NĒ (§ Ne-darīt, 2026-11-09). Atvērts: žurnālistiem/analītiķiem Pārskata nav (`politicians.py` izslēdz) — dominējošās komentāru tēmas + visvairāk komentētie politiķi.
- **Personas lapa:** partiju rail grupēts pēc koalīcijas statusa — **ATLIKTS 2026-10-09 (operators) līdz koalīcijas pārslēgšanai — atbloķēts 2026-11-17** (valdība apstiprināta, `coalition_status` pārslēgts; `backlog/dati-db.md` § 15. Saeima). Ieviešana bija ~12 rindas `render_personas()` (grupas coalition → opposition → other ar `get_coalition_map`, vārdi kā «Koalīcija» railā) + `.pnv1-rail-subtitle`; netika komitēta; meklētājs neatrod tēmas („kurš runā par airBaltic?").
- **Saeimā cilne:** frakcijas-diverģences highlight (alignment SQL eksistē); grupēšana pa sēdēm.
- **Timeline cilne:** mēnešu grupu virsraksti + tipa filtru čipi (pozīcijas/balsojumi/pretrunas). (Ārējās recenzijas «laika ass profilā», verdikts 45 — ATLIKTA.)
- **«Turpini rakt» kastes** (pretrunas lapa; tas pats komponents profilos un tēmās) — vēl bēšas pildītas kastes; pieskaņot `ui-conventions.md` § Kartītes un saraksti (operators 2026-10-23 «nākamais solis»).
- **Dalīšanās kartiņas** (verdikts 45 — ATLIKTS; plāns `docs/superpowers/plans/archive/2026-04-21-shareable-pretrunu-kartinas.md`).
- **Saites v2 — atlikušie posmi** (ieteikums `docs/plans/2026-11-22-saites-v2-ieteikums.md`; 1. un 2. posms live 22.11.). **2b:** kopā iesniegtie likumprojekti (`saeima_bill_politicians`, 51 starppartiju) kā vēl viens vietu veids. **3. posms:** ģimene — 7 vārda sakritības pāri, publicē tikai operatora pārbaudītos (T1/T13). `ORG_ALLOWLIST` (34) operators var pārskatīt jebkurā brīdī; jauna organizācija pēc VID ielādes parādās renderā kā brīdinājums «nav pārbaudītas», līdz to ieliek vienā no sarakstiem. *Īpašnieks:* operators (kad sākt).
- **Saites mini-grafs:** vote alignment top/bottom 3 → pilna tabula. *Pilnajā tīklā atrisināts 2026-11-22* (3+3 izvēlētajam mezglam, CHANGELOG 2026-11-22 (2)); profila mini-grafā balsojumu līniju joprojām nav. **Mediju/iestāžu profiliem** trūkst „kāpēc mēs to izsekojam" explainer + cross-link uz `mediji.html`.

### [DEFERRED] Tēmu direktorija un tēmas lapa — 2. kārta (meklēšana, kārtošana, jautājumu salīdzinājums)

Pirmā kārta izpildīta 2026-09-06 (`2b48c541`; `docs/arhivs/handoffs/HANDOFF-2026-09-06-temas-airbaltic.md`). **Verdikts 46: ATLIKTS līdz lasītāju signālam** — vēlēšanu sezonā datu integritāte atmaksājas vairāk nekā UI. Paliek produkta virziens:

- **Direktorija (`temas.html`):** meklēšana pēc tēmas/sinonīma (`pzv1.js` jau lasa `q` parametru), kārtošana alfabētiski / pēc jaunākās aktivitātes / pēc apjoma, pēdējās pozīcijas datums kartītē. Saistīts ar § Profilu UI parāds «meklētājs neatrod tēmas».
- **Tēmas lapa:** tvērums un periods → konkrētie jautājumi → analīzes → filtrējamas pozīcijas → balsojumi / programmu solījumi atsevišķi → saistītās tēmas. `RELATED_TOPICS` sedz 2 no 33 tēmām — paplašināt, kad tēma tiek lasīta.
- **Lielākais iespējamais papildinājums:** konkrēta jautājuma salīdzinājums pa personām/partijām ar nosacījumiem, datumu, avotu un «nav fiksētas pozīcijas» šūnu. `program_promise` nejaukt ar pozīcijām; balsojumus — ar mediju izteikumiem. Bez auto-sintēzes, bez konsekvences reitinga (§ Ne-darīt).

*Trigeris:* lasītāju signāls. *Īpašnieks:* operators.

### [OPEN] good-css 5. kārtas atlikums — operatora jautājumi (2026-10-21)

Kārta: `docs/plans/archive/2026-10-21-good-css-5-karta.md`, kopsavilkums `docs/audits/2026-10-21-good-css-5/kopsavilkums.md`. Daļa (a) izdarīta 2026-11-23 (mazie mērķi telefonā, tūkstošu atstarpes, likuma lapas atstarpe, `.badge-red` tumšajā; `tests/test_phone_tap_targets.py`). Paliek: operatora jautājumi (kopsavilkums § D): `<title>`/og_title datumi `16.10.2026` (222 lapas, sociālie priekšskatījumi); lasīšanas platums garajiem rakstiem; multi-select → `popover`, mobilais filtrs → `<details>`, X filtrs telefonā; statistikā LV skaitļu formāts; nedēļas pārskata galvene kā dienas; fontu skala. D2 (ziņu/X lapošana) NEceļ — § Ne-darīt. *Trigeris:* operatora atbilde. *Īpašnieks:* operators.

### [OPEN] Dizaina vienādošana pēc golden-rules — viena kārta ar «pirms/pēc» (2026-11-25)

No 2026-11-25 Gemini projekta pārskata § 3.1 (fails glabājas tikai lokāli, ārpus repo) (pārlūka mērījumus neesam atkārtojuši). Operators 2026-11-25 apstiprināja virzienu: LIELIE BURTI etiķetēs → parasts reģistrs visā vietnē vienā kārtā (ne pa gabaliem), kopā ar krāsainajiem punktiem pogās (`pretrunas.html`), kreisās malas laika līniju profilā, faktu dublēšanos (profila cilnes pret skaitļu joslu, `saeima.html` «100 deputāti» ×4) un pogu izskatu skaitu `pozicijas.html`. Atbild arī «Valdība» (a) jautājumu. *Rīcība:* `mans-dizains`, ekrānuzņēmumi pirms/pēc, operatora apstiprinājums pirms deploy. *Īpašnieks:* operators/kods.

### [OPERATOR] Lapa «Valdība» — divi jautājumi pēc publicēšanas (2026-11-18)

Lapa publicēta 2026-11-18 (CHANGELOG 2026-11-18, deploy ecc2c821). Atvērti divi operatora jautājumi: (a) galvenes etiķete ar lielajiem burtiem (vietnes stils) pret golden-rules §5.1; (b) ministriju↔tēmu karte `src/render/valdiba.py` ir aģenta minējums (Iekšlietām pieskaitīta «Aizsardzība un drošība» → arī NATO pozīcijas). *Trigeris:* operatora atbilde vai lasītāja signāls. *Rīcība:* pēc atbildes labot etiķeti vai karti, `tests/test_render_valdiba.py`, `--only=valdiba,saeima`. *Īpašnieks:* operators.
