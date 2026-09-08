# Kvalitātes latiņas — pārbaudāmi kritēriji katram nodevumam

_Izveidots 2026-07-07. Katrs punkts ir pass/fail — pārbaudi PIRMS `store_*()` / commit / publicēšanas, ne pēc tam. Rādītājs dzīvo CLAUDE.md § Quality Bars. Kanoniskajiem nesējiem (aģentu prompti, prasmes) jāsakrīt ar šo lapu — ja atšķiras, labo abus vienā piegājienā._

## Pozīcija (claim)

Kanoniskais nesējs: [`.claude/agents/claim-extractor.md`](../../.claude/agents/claim-extractor.md)

- [ ] `source_url` nav NULL un nāk no dokumenta
- [ ] LV teksts iziet diakritiku validāciju + gramatikas/stilistikas vārtus (MŪSU teksti: stance, reasoning; **`quote` ir verbatim — politiķa paša kļūdas NElabo**, operatora lēmums 2026-07-07)
- [ ] `confidence` pēc [rubrics.md](rubrics.md): <0.6 → `reasoning` PREFIKSĀ `NEEDS_REVIEW: `; <0.5 → tas pats + iemesls tajā pašā rindā. Karogu joprojām RAKSTA kā tekstu `reasoning` laukā — `needs_review` parametra nav, un liekā atslēga tiek klusi atmesta (pārbaudīts 2026-08-02). **Bet LASA to no `claims.review_status` kolonnas** (kopš 2026-08-03, atvasināta ar trigeriem); nekad ar `LIKE` pār prozu, jo marķiera forma un novietojums dreifē
- [ ] Pārskatīšanas rinda ir IEROBEŽOTA, ne tukša: **neviena `review_status='needs_review'` rinda nav vecāka par 14 dienām** (operatora lēmums 2026-08-03). Šodienas rindas rindā ir gaidītas — tas ir marķieris, kas strādā. Ziņo abus skaitļus: kopā atvērtas + cik vecākas par 14 d. **Vecumu mēra no MARĶIERA, ne no claim** — `COALESCE(review_status_at, created_at)`, kopš 2026-09-07; rindu iegūst ar `src.db.open_review_queue()`, nevis pārrakstot SQL. Vecais mērījums no `created_at` katrā retro-marķēšanas reizē uzreiz ražoja «pārkāpumu» par darbu, kas notika iepriekšējā dienā (2026-08-22: visas 19 pārkāpuma rindas bija ienākušas dienu iepriekš). Rindām, kas rakstītas pirms 2026-09-07, `review_status_at` ir NULL, un tās joprojām skaitās no `created_at` — neviena rinda ar šo maiņu nekļūst jaunāka
- [ ] Neizlasīts dokuments NAV atzīmēts ar `empty_doc_ids` (tas uzliktu `reviewed_at` un izņemtu to no rindas uz visiem laikiem — T5 + T11)
- [ ] `salience` pēc rubrikas
- [ ] Pareizs `claim_type` (+ `speaker_id` / `party_id`, kur piemērojams)
- [ ] Netieša atsauce / tikai retweet → NEEDS_REVIEW, ne first-party pozīcija
- [ ] Vēsturiskam ingestam `stated_at` = raksta publicēšanas datums, ne šodiena
- [ ] Saglabāto claim skaits == plānotais skaits (T2 — klusā apvienošana uz idempotences atslēgas)
- [ ] `sentiment=0.0`

## Pretruna

Kanoniskie nesēji: `/deep-check` + [`.claude/agents/devils-advocate.md`](../../.claude/agents/devils-advocate.md)

- [ ] Abi claim id eksistē, un "vecais" pēc `stated_at` tiešām ir vecāks
- [ ] `severity` ∈ {`direct_contradiction`, `reversal`, `minor_shift`} pēc rubrikas
- [ ] Izgājusi `@devils-advocate` (nav koalīcijas disciplīna, procedurāls/whip konteksts, žurnālista pārstāsts vai divas savienojamas pozīcijas)
- [ ] Retorika-pret-balsojumu nāk no strukturālās SQL pārbaudes ar frakcijas salīdzinājumu (T9), ne no embeddings
- [ ] Saglabāta `confirmed=0` līdz operatora apstiprinājumam
- [ ] Kopsavilkums latviski, smaguma apzīmējumi latviski, bez kailiem `#NNNNN`

## Dienas pārskats

Kanoniskie nesēji: [`.claude/agents/brief-writer.md`](../../.claude/agents/brief-writer.md) + `/dienas-rutina`

- [ ] Datums = rutīnas diena (viens pārskats dienā; tās pašas dienas refresh = UPDATE DB rindu UN `wiki/dailies` failu, nekad otrs pārskats)
- [ ] Ievadā tikai tas, kas šodien JAUNS — notikuma svaigums verificēts pret agrākiem claims/pārskatiem, pirms to ceļ uz "Galvenais"
- [ ] Katra skeleta izlaistā augstas salience solo tēma pievienota atpakaļ (T7)
- [ ] Katrs "X un Y kritizē Z" ar ≥1 saglabātu claim par Z katram nosauktajam
- [ ] Neviena rindkopa nesākas ar "N." (markdown `<ol>` slazds — pārbaude renderētajā HTML)
- [ ] **Tēmai ar konteksta kastīti zem tabulas ir ne vairāk kā VIENS teikums** (A noteikums, 2026-09-02) — skelets kastītes ņem no `routine_day_window()`, tāpēc kastīte un sintēze stāsta vienu un to pašu dienu; divi pilni prozas bloki pēc kārtas ir dublējums. Ziņo: cik tēmām bija kastīte, cik no tām sintēze pārsniedza vienu teikumu (jābūt 0)
- [ ] **Neviens aģenta rakstīts prozas bloks nepārsniedz 120 vārdus, un 4+ aktieri iet sarakstā, ne semikolu virtenē** (B noteikums). Ziņo: bloku skaits, garākā bloka vārdi, cik pāri 120. Etalons, kā NEdarīt: 2026-09-01 § Imigrācija, 206+149 vārdi pēc kārtas
- [ ] Abus iepriekšējos punktus kopš 2026-09-02 pārbauda `lint_lv_style()` 5. un 6. likums (`prose-block-too-long`, `context-box-synthesis-duplication`) — tie NAV pašpārbaudes aizvietotājs, bet tukšs `issues` saraksts tagad ir pierādījums, ne apgalvojums
- [ ] Koalīcijas bloki pēc `parties.coalition_status`; bezpartejiskie ar NULL statusu → "Neitrāli"; bez tukšām `()`
- [ ] Featured image `-hero/-og/-card/-thumb` varianti eksistē un live atgriež HTTP 200 (renders tos ģenerē PATS — `_ensure_image_variants()` iet pirms kopēšanas un sedz arī `images/briefs/`, `src/render/_orchestrator.py:497`. `src.graphics.cli brief` variantus NEģenerē, tāpēc ārpus rendera palaists `--note-id` atstāj tikai pamata PNG līdz nākamajam renderam)
- [ ] Vizuālā brief "Skaitlis" = "–", ja vien skaitlis nav attēla burtiskais enkurs
- [ ] Publicē tikai pēc operatora skaidra apstiprinājuma (proofread + attēla confirm)

## Nedēļas pārskats

Kanoniskais nesējs: [`.claude/agents/weekly-brief-writer.md`](../../.claude/agents/weekly-brief-writer.md)

- [ ] Visi dienas pārskata punkti
- [ ] Īsta starpdienu sintēze, ne pārrakstīti daily
- [ ] Prozas bloki iziet to pašu B noteikumu kā dienas pārskatam (≤120 vārdi, 4+ aktieri sarakstā) — sk. [`brief-shared-rules.md`](agenti/brief-shared-rules.md) § Prozas bloku forma
- [ ] Ministru/partiju atribūcija pārverificēta pret `tracked_politicians.role` + svaigu avota URL — nedēļas sintēze pār vecām piezīmēm gan manto novecojušus faktus, gan mēdz "izlabot" pareizos uz nepareiziem
- [ ] Bloku/movers statistika pār VISĀM nedēļas pozīcijām, ne top-N
- [ ] (2026-09-06) 1 000–1 400 vārdi bez tabulām; neviens `source_url` divās sadaļās; `[x.com](` = 0; `Avoti:` rindu = 0; aizliegtie rāmji («sadalījās divās līnijās», «trīs slāņi», «smaguma centrs») = 0 — četri skaitļi atskaitē
- [ ] (2026-09-06) `**Pārējās tēmas:**` un `**Dienu pārskati:**` rindas saglabātas; `## Pretrunas` tikai no skeleta; `## Skats uz priekšu` tikai ar datētu notikumu

## Sociālais pavediens

Kanoniskais nesējs: `/social-thread` (pilnā procedūra tur)

- [ ] Neviens tvīts nesākas ar `@`
- [ ] Katrs handle verificēts pret `social_accounts`
- [ ] Katrs tvīts savā kopējamā blokā; konts ir verified, tāpēc 280 zīmju limits nav saistošs — turi tvītu ≤3 īsām rindkopām
- [ ] Saite tikai pēdējā tvītā
- [ ] LV gramatikas/stilistikas vārti

### Ierāmējuma vārti (attiecas uz VISU ārējo sociālo tekstu — X pavediens, Reddit, Facebook)

- [ ] **Virsraksts un ievadteikums neapgalvo pretrunu, pozīcijas maiņu vai nekonsekvenci, ja `contradictions` rindas nav.** Kontrasta konstrukcijas — «X vienā dienā: A — un B», «abi virzieni», «bet tajā pašā laikā» — ir pretrunas apgalvojums bez datiem. Pārbaude: `SELECT * FROM contradictions WHERE claim_old_id IN (...) OR claim_new_id IN (...)` pār visiem citētajiem claim ID.
- [ ] **Sociālā teksta ierāmējums nav asāks par pārskata paša formulējumu.** Ja pārskats saka «vērsts atpakaļ, ne uz jaunu lēmumu», postā tas nekļūst par «abi virzieni». Pārskats ir avots; posts ir tā atstāsts, ne interpretācijas pastiprinājums.
- [ ] **«Vienā dienā» / «tajā pašā dienā» pārbaudīts pret PIRMAVOTA NOTIKUMA datumu, ne pret `stated_at`.** `stated_at` mēdz būt raksta publicēšanas datums, kas runu pārceļ uz nākamo dienu; tā pati runa var DB stāvēt divreiz ar diviem datumiem no diviem izdevējiem.

_Cēlonis (2026-08-22, r/latvia): virsraksts «Kulbergs vienā dienā: 14,5 % darījums bija kļūda — un aicinājums dot pēdējo valstisko iespēju» pasniedza kā pretrunu to, kam DB nav nevienas `contradictions` rindas, kamēr pārskats pats rakstīja «divos virzienos» un tēzē «sasaista valsts naudu ar nosacījumiem». Turklāt «vienā dienā» bija nepatiess — aicinājums izskanēja 08-20 Saeimas ārkārtas sēdē (visi seši 1495/Lp14 balsojumi `vote_date='2026-08-20'`), 14,5 % vērtējums 08-21; claim #703862 `stated_at` bija raksta datums, un tā pati runa jau stāvēja DB pareizi datēta kā #690497. Kļūdu publiski norādīja lasītājs, ne mūsu vārti._

## Sintēze (`wiki/synthesis/*.md`)

Kanoniskie nesēji: rakstīts ar roku (standing lēmums 2026-04-22) + [`.claude/agents/quality-reviewer.md`](../../.claude/agents/quality-reviewer.md) § H (valoda) un § E (neitralitāte). Sadaļa pievienota 2026-09-06 — līdz tam sintēzēm vārtu nebija.

- [ ] Frontmatter: `title`, `description`, `created`, `politicians`, `topics` (kanoniskie nosaukumi vai to slugi — `_normalize_synthesis_topics` nezināmu vērtību raksta stderr; 0 brīdinājumu renderī)
- [ ] Katram ārpus-citāta skaitlim un notikumam saite uz pirmavotu; visas saites HTTP 200 (skaits atskaitē)
- [ ] Vārds «pretruna» / «mainīja nostāju» tikai ar `contradictions` rindu; pārējais ir hronoloģija
- [ ] Darījuma stadija nosaukta (piedāvāts / pilnvarots / noslēgts / izmaksāts); nenoslēgts darījums nav pagātnes formā
- [ ] Balsojumu ķēdes citētas veselas (T14); frakcijas apgalvojumi no `faction` sadalījumā TAJĀ `vote_id` (T6)
- [ ] Analīzes beigu datums tekstā; turpinājums saitē uz iepriekšējo daļu, iepriekšējā — uz turpinājumu (abas publicē kopā)
- [ ] `lint_lv_style` 0 (izņemot verbatim citātus) UN `@quality-reviewer` § H pārlasījums ar saucēju
- [ ] Melnraksts dzīvo `docs/drafts/`, ne `wiki/synthesis/` — build kokā nonāk tikai publicējamais

## Render + deploy

Kanoniskie nesēji: `scripts/check.sh` + [`.claude/agents/quality-reviewer.md`](../../.claude/agents/quality-reviewer.md)

- [ ] `bash scripts/check.sh` iziet — baseline drifts pēc ingest ir normāla ikdiena (REGEN + commit); īsta render regresija = STOP, ne REGEN
- [ ] Renderēts šauri ar `--only=DOMAIN` skartajai virsmai (pilns render tikai release/baseline)
- [ ] Deploy ar `--no-delete`; kurētie katalogi (finanses, statistika) neaiztikti
- [ ] Deploy preflight ABI vārti zaļi (automātiski, `deploy.sh`): `check_output.py` (ref/sitemap) + `--publish-gate-only` (T15: brief lapa bez approved=1 vai orfāna = bloķē; `--no-output-check` ir apzināta apiešana, ne noklusējums)
- [ ] `@quality-reviewer` PASS ir cietie vārti — FAIL gadījumā nekas nepublicējas

## Seedēšana (politiķis / partija / organizācija)

Kanoniskais nesējs: [seeding.md](seeding.md)

- [ ] `name_forms` satur GAN diakritiku, GAN ASCII variantus; celmi pārbaudīti ar acīm (audita skripts ķer tikai trūkstošos ASCII, ne nepareizu celmu)
- [ ] Katra ģenerētā forma ≤4 zīmes atzīmēta pārskatīšanai (T1 — substring kolīziju risks)
- [ ] Dublikātu/pārrakstīšanās pārbaude pret esošajām rindām
- [ ] Partija verificēta pret neatkarīgu avotu, nekad pret kopējā saraksta formulējumu ziņās
- [ ] `x_handle` un `social_accounts.handle` saskaņoti (klusi šķiras)
- [ ] Koalīcija uz `parties.coalition_status`, ne per-politiķa laukiem
- [ ] Pārī `data/rollback_*.sql` komitēts kopā ar seed

## Saeimas sesija

Kanoniskais nesējs: [`.claude/agents/saeima-tracker.md`](../../.claude/agents/saeima-tracker.md)

- [ ] Visi trīs vote-URL paterni noskrāpēti un apvienoti (skaitli neatvasini no galvas — `saeima-tracker.md` Step 2.B)
- [ ] 0 balsojumu pie sēdes ar darba kārtības punktiem = STOP + ziņo, ne "tukša diena"
- [ ] Visi ~100 deputāti sametčoti (citādi vispirms labo `name_forms`)
- [ ] Katram bill-tipa balsojumam kopsavilkums PIRMS store
- [ ] Pilnīgums/dedupe pēc `(vote_date, vote_time)`, nekad pēc URL
