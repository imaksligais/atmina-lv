# Kvalitātes latiņas — pārbaudāmi kritēriji katram nodevumam

_Izveidots 2026-07-07. Katrs punkts ir pass/fail — pārbaudi PIRMS `store_*()` / commit / publicēšanas, ne pēc tam. Rādītājs dzīvo CLAUDE.md § Quality Bars. Kanoniskajiem nesējiem (aģentu prompti, prasmes) jāsakrīt ar šo lapu — ja atšķiras, labo abus vienā piegājienā._

## Pozīcija (claim)

Kanoniskais nesējs: [`.claude/agents/claim-extractor.md`](../../.claude/agents/claim-extractor.md)

- [ ] `source_url` nav NULL un nāk no dokumenta
- [ ] LV teksts iziet diakritiku validāciju + gramatikas/stilistikas vārtus (MŪSU teksti: stance, reasoning; **`quote` ir verbatim — politiķa paša kļūdas NElabo**, operatora lēmums 2026-07-07)
- [ ] `confidence` pēc [rubrics.md](rubrics.md): <0.6 → `needs_review`; <0.5 → NEEDS_REVIEW statuss
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
- [ ] Koalīcijas bloki pēc `parties.coalition_status`; bezpartejiskie ar NULL statusu → "Neitrāli"; bez tukšām `()`
- [ ] Featured image `-hero/-og/-card/-thumb` varianti eksistē un live atgriež HTTP 200 (render variantus tikai KOPĒ; tos ģenerē `make_variants()`; briefs katalogu self-heal nesedz)
- [ ] Vizuālā brief "Skaitlis" = "–", ja vien skaitlis nav attēla burtiskais enkurs
- [ ] Publicē tikai pēc operatora skaidra apstiprinājuma (proofread + attēla confirm)

## Nedēļas pārskats

Kanoniskais nesējs: [`.claude/agents/weekly-brief-writer.md`](../../.claude/agents/weekly-brief-writer.md)

- [ ] Visi dienas pārskata punkti
- [ ] Īsta starpdienu sintēze, ne pārrakstīti daily
- [ ] Ministru/partiju atribūcija pārverificēta pret `tracked_politicians.role` + svaigu avota URL — nedēļas sintēze pār vecām piezīmēm gan manto novecojušus faktus, gan mēdz "izlabot" pareizos uz nepareiziem
- [ ] Bloku/movers statistika pār VISĀM nedēļas pozīcijām, ne top-N

## Sociālais pavediens

Kanoniskais nesējs: `/social-thread` (pilnā procedūra tur)

- [ ] Neviens tvīts nesākas ar `@`
- [ ] Katrs handle verificēts pret `social_accounts`
- [ ] Katrs tvīts savā kopējamā blokā, ≤280 zīmes
- [ ] Saite tikai pēdējā tvītā
- [ ] LV gramatikas/stilistikas vārti

## Render + deploy

Kanoniskie nesēji: `scripts/check.sh` + [`.claude/agents/quality-reviewer.md`](../../.claude/agents/quality-reviewer.md)

- [ ] `bash scripts/check.sh` iziet — baseline drifts pēc ingest ir normāla ikdiena (REGEN + commit); īsta render regresija = STOP, ne REGEN
- [ ] Renderēts šauri ar `--only=DOMAIN` skartajai virsmai (pilns render tikai release/baseline)
- [ ] Deploy ar `--no-delete`; kurētie katalogi (finanses, statistika) neaiztikti
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

- [ ] Abi vote-URL paterni noskrāpēti un apvienoti
- [ ] 0 balsojumu pie sēdes ar darba kārtības punktiem = STOP + ziņo, ne "tukša diena"
- [ ] Visi ~100 deputāti sametčoti (citādi vispirms labo `name_forms`)
- [ ] Katram bill-tipa balsojumam kopsavilkums PIRMS store
- [ ] Pilnīgums/dedupe pēc `(vote_date, vote_time)`, nekad pēc URL
