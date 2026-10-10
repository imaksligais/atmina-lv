# `/audit-integrity` — bāzes līnijas un incidentu vēsture

Pārcelts no `.claude/commands/audit-integrity.md` 2026-09-30, kad pārbaudes kļuva par `scripts/audit_integrity.py`. Šeit ir **kāpēc** katra pārbaude ir tāda, kāda tā ir, un ar ko salīdzināt skaitli. Triāžas noteikumi (ko darīt ar karogu) dzīvo promptā; pieņemto id saraksti un sliekšņi — skriptā kā konstantes (`ACCEPTED_*`, `*_DAYS`). Katrs skaitlis zemāk ir derīgs tikai kopā ar vaicājumu, kas to ražoja — tagad tas ir skripts.

## Pārneses piezīmes (2026-09-30)

Pārnesē semantika netika mainīta. Kur promptā bija tikai proza, skripts to lasa burtiski, un lēmums ir atzīmēts pie funkcijas ar «PROZAS LASĪJUMS»:

- **1.** «ģenerētās formas» = `_latvian_surname_inflections()` katrai glabātajai viena vārda formai + vārda pēdējam tokenam (izņemot institucionālos un `@`); paraugs — 14 d dokumenti ar `_occurrences` (vārda robeža).
- **3.** «neatrisinās» = `NULL` vai norāda uz neesošu claim.
- **5.** «satur» = `LIKE '%izstāj%'` (prefiksa forma pret stance teikumu praktiski nenostrādā — 2026-09-30 mērīts: `%…%` 1 rinda, prefikss 0). Nosacījums «party nemainīts kopš pirms `stated_at`» nav izpildāms (partijas vēstures nav) — katra rinda ir kandidāts.
- **6.** `position`, 30 d pēc `stated_at`; stance-līdzības filtrs nekad nav bijis definēts, tāpēc `flagged` = augšējā robeža (BACKLOG § Atliktais 57) un pārbaude ir informatīva.
- **8.** 30 d logs pēc `scraped_at` — vienīgais ierakstītais skrējiens (`logs` 2026-07-07, atslēga `8_truncated_stubs_30d`). Prompts platformu nefiltrēja; bez loga un platformas skaits ir ~56 500, gandrīz tikai tvīti.
- **9.** `party` → `parties.short_name` pēc `name` VAI `short_name`; saucējs = aktīvie ar ≥1 etiķetētu balsi, kuru partijas `short_name` parādās kā etiķete. 2026-07-26 atsauces skrējiens lietoja arī «≥50 etiķetētu balsu» filtru — tas nebija prompta noteikumā un nav pārnests.
- **12.** = 15. funkcija (`find_inversions`, 90 d). Prompta «`platform='web'`» ir novecojis: kopš 2026-08-27 josla ir `web`+`twitter`+`x_mention` (`DEFAULT_INVERSION_PLATFORMS`).

## Zināmas vaicājumu nepilnības (pārnestas nemainītas, ziņotas operatoram)

- **4. vecuma sadalījums** lieto `julianday('now')` (UTC) pret LV kolonnām — rinda pie 7/14/30 d robežas var pārlēkt spaini ~3 h agrāk (T17). Vārtu skaitlis nāk no `open_review_queue()` formas (`now_lv()`), ne no sadalījuma. **Labots 2026-09-30** (operatora «jā»; tests + mutācija `tests/test_audit_integrity.py`; dzīvajā DB rezultāts nemainījās: 4. sanity 0, sadalījums `<=7d: 25`, 11. delta 0).
- **4. sanity rinda** `(review_status='needs_review') != (reasoning LIKE '%NEEDS_REVIEW%')` ir SQL-NULL-akla: ja trigeri pārstātu rakstīt un `review_status` paliktu NULL, rinda to neredz — tā pati klase kā 2. pārbaudes vēsturiskais `LOWER(a)<>LOWER(b)`. **Labots 2026-09-30** (operatora «jā»; tests + mutācija `tests/test_audit_integrity.py`; dzīvajā DB rezultāts nemainījās: 4. sanity 0, sadalījums `<=7d: 25`, 11. delta 0).
- **11.** `opponent_id || '|' || source_url || '|' || topic` ar NULL `source_url` dod NULL, un `COUNT(DISTINCT …)` to neskaita — delta pieaugtu viltus veidā. **Labots 2026-09-30** (operatora «jā»; tests + mutācija `tests/test_audit_integrity.py`; dzīvajā DB rezultāts nemainījās: 4. sanity 0, sadalījums `<=7d: 25`, 11. delta 0).

## Bāzes līnijas pa pārbaudēm

**1.** Pirmais skrējiens 2026-07-07: 10 aktīvi politiķi ar ≤4 zīmju formām (ieskaitot Kolu). Kopš 2026-07-27 B2+D2+H viena vārda formas atbilst tikai vārda robežās — ≤4 zīmju forma ir vārdabrāļa risks, ne substring bumba.

**1b.** Kopš 2026-09-07 matcher pārlaidieni pār korpusu (1, 1b, 12) nebija palaisti — «nav mērīts», ne «tīrs». Pirmais skripta skrējiens 2026-09-30: `checked=10751 flagged=205` (pid, priekšējais tokens) pāri.

**2.** Bāzlīnija 2026-08-25: `111 | 1 | 1`. NULL rinda — id 27 Bordāns, apzināti NULL (`inactive`, 196 lapas uzbūvētas, `bordans` nav starp tām); vērtības nesakritība — id 62 Svirskis (`ESvirskis` pret `realNepareizais`; abi konti apzināti — operatora lēmums 2026-07-16, apstiprināts 2026-09-07, BACKLOG § Ne-darīt; (c) zars nefiltrē pēc `active`, tāpēc karo katru politiķi ar >1 X kontu). Iepriekš `111 | 2 | 1` (2026-08-23) ietvēra id 204 NBS, aizpildīts 2026-08-25 (`data/{fix,rollback}_x_handle_nbs_2026-08-25.sql`). NULL klase atrasta 2026-08-23: 7 rindas mēnešiem nereportētas, jo `LOWER(a) <> LOWER(b)` ir NULL-akls; 5 aizpildītas (`data/fix_x_handle_backfill_2026-08-23.sql`). `x_handle` ir tas, uz ko `templates/politician.html.j2` balsta profila X saiti.

**3.** 2026-08-04: `30/0`. 2026-09-30: pretruna #27 atsaukta (`confirmed=-1`), tās vecā pozīcija #6991 dzēsta → `claim_old_id` NULL, pieņemts `ACCEPTED_3`.

**4.** Kopš 2026-08-03 karogs ir kolonna `claims.review_status`, ko divi trigeri atvasina no `reasoning`; `LIKE 'NEEDS_REVIEW%'` reiz atgrieza 20 no 119 rindām. Kopš 2026-09-07 vecums skaitās no marķiera (`COALESCE(review_status_at, created_at)`, `src.db.REVIEW_AGE_EXPR`): 2026-08-22 retro-marķēšana ielika 19 aprīļa–augusta claims rindā, un `created_at` vārti uzreiz ziņoja pārkāpumu. Bāzlīnija 2026-08-03: `needs_review=119` (76 ≤7 d, 43 8–14 d), `reviewed=234`. `reviewed=1 confirmed=0` ir dokumentēts noraidījums (#40 Judins — 2026-08-04 nefiltrētais vaicājums to atkārtoti karoja).

**5.** 2026-08-04: `38/0`.

**6.** 2026-08-04: `1050/0` (ar kādu līdzības filtru, kas netika pierakstīts); 2026-09-07: `checked=1195`, 101 grupa bez filtra (augšējā robeža). Tas pats kandidātu tīkls kodā — `possible_duplicate` kopš 2026-09-24.

**7.** 2026-08-04: `checked=138 flagged=0`, spaiņi `-1`×4, `0`×32, `1`×138, `2`×71. 2026-08-02 bāzlīnija bija `137/2` (ids 93, 96, hero + `og:image` 404 dzīvajā lapā); 08-04 `138/0` sākumā nolasīja kā «salaboti», bet abas rindas bija pārgājušas uz `approved=2` — ārā no pārbaudāmās kopas. `approved=2` = atcelts kandidāts (40 no 44 tādām piezīmēm ir `approved=1` aizstājējs; 4 bez — ieskaitot 93/96 — lapas pārrenderētas uz vietnes fallback `og:image`, leģitīms bez-attēla stāvoklis). Agrāk pārbaude skenēja disku→DB («PNG bez `-hero.webp`»): kandidātu kopā bija **viens** fails ar savu blakusfailu, tāpēc tā ziņoja «tīrs» mūžīgi.

**8.** 2026-07-07: 387 (30 d). pmo.ee «97 paywall stubi» un lsm «~592 truncated» — nezināms slieksnis, nesalīdzināt.

**9.** Etiķešu ainava kopš 2026-08-04: viena etiķete uz frakciju (`ST!`/`ST` normalizēts uz `ST` datos un parserī `src/saeima/votes.py`); 2026-08-19 audits atrada 7 366 `ST!` rindas atpakaļ pēc backfill — 2026-09-30 mērījumā `ST!` vairs nav. Atsauce 2026-07-26 (119 politiķi ar ≥50 etiķetētām balsīm, 4 karogi): logā 2026-03-26…04-01 (70 balsojumi) Ābrama (77, ZZS 65/70), Kiršteins (96, LPV 57/70), Ceļapīters (145, ZZS 65/70) — īstas maiņas, atstāt; Šmits (150) `party='Stabilitātei!'` 17/70 pret 1 668 AS balsīm — labots `data/{fix,rollback}_smits_party_2026-07-26.sql`.

**9b.** 2026-09-07 (verdikts 42): `checked=25 flagged=6` — pid 15 Braže, 64 Vītols (`role='Finanšu ministra biroja ekonomists'` — substring viltus pozitīvs), 155 Melbārde, 158 Lāce, 159 Uzulnieks, 224 Melnis. pid 212 Labanovskis ir tajā pašā aklajā zonā otra iemesla dēļ (`inactive`). Melnis (224) nesa nepareizu partiju divus mēnešus un 26 publicētus pārskatus, kamēr 9. pārbaude ziņoja tīru.

**10.** Pievienots 2026-07-30 pēc `political_tensions` #175 (Claude outage, vairākas sesijas restartētas; tvīta statusa ID, kas nav nevienā dokumentā — `store_tension()` to atteiktu). Visi četri vaicājumi 2026-07-30 = 0; 2026-08-04 A 163/0, B 5468/0, C 568724/0, D 0. D limits: salīdzinājums ar UTC «tagad» ķer tikai pēdējās ~3 h rakstus; stundas heiristika vecākus neatšķir (10 spriedzes pie ≥21:00, visas izņemot #175 parasti UTC vakara raksti).

**11.** 2026-08-02 (pēc tīrīšanas): total 568 724, delta 0. 4 087 dublikāti dzēsti 2026-08-02 (`data/fix_dup_saeima_vote_claims_2026-08-02.sql` + rollback + snapshot). Cēlonis: divas `UPDATE claims SET topic` migrācijas (`fix_claims_votes_topic_drift_2026-06-13.sql` 3 991 grupa, `fix_motif_topic_coverage_2026-06-12.sql` 91) SAPLUDINĀJA trijniekus. Rindas fiziski dubultojās jau 2026-05-27 (P3 pārlāde, 46 no 64 aprīļa URL), bet tēmas tad vēl atšķīrās — šī pārbaude bija ~0 visu maiju un jūniju.

**12 / 15.** 2026-08-02 ad-hoc: 282 / 1897 = 14,9 %; saucējs saturēja dokumentus, kuru vienīgā `mentioned` entītija ir organizācija. Godīgais saucējs 2026-08-03: `checked=1273 flagged=280 (22,0 %)` — klase ~1,5× smagāka. LETA NAV cēlonis (10,9 % pret 17,9 %). Kopš 2026-08-27 josla ietver tvītus; tur satīras konti dominē viltus pozitīvus. Atsauces gadījums doc 78085 (nominatīvs ir slodzi nesošs).

**13.** 2026-08-04: `checked=54 match=54 stale=0 missing=0`, kontrole 25/25. 06-13 atlikums bija 167/167 stale ar derīgu kontroli (slēgts 2026-08-04). Kopš 2026-09-07 `saeima_vote` izslēgti.

**14.** 2026-08-02 (pēc tīrīšanas): `checked=6465 flagged=0`. Pirms: `flagged=49` — 39 tieši 2.0 (2026-03-26 ×28, 2026-04-01 ×11), lieko 4 087 rindu = 100 % no 11. delta. `missing` tad bija 0 un tam jāpaliek 0.

**16.** Četras formas bija sakrājušās (`dienas analīze`, `dienas pārskats`, `dienas parskats`, kails `daily` — id 192), `LIKE 'dienas analīze %'` redzēja 70 no 119. 2026-08-04: `checked=119 flagged=0` — id 131 (`dienas pārskats 2026-04-14`, tas pats pārskats kā id 135) dzēsts ar operatora lēmumu (`data/rollback_brief131_dedup_2026-08-04.sql`, kopā ar attēla rindu #4, FK).

**17.** 2026-08-05: `checked=30 flagged=11` (no 1 418 web citātiem). #555824 labots pret jauno versiju 2026-08-03 (Butāna precedents); #11210 pašizdziedinājās (klase kustas abos virzienos). 2026-09-07: 7 jauni id (615955, 689768, 704089, 704179, 704217, 704342, 709073) atlikti triāžas sesijai (BACKLOG § Atliktais 50/55); 615955 ir pieturzīmju klase, ne pārskrāpējums.

**18.** 2026-09-07 (verdikts 24): `checked=6564 distinct=33/33 flagged=0`. `src/tools.py::store_claim` normalizē `topic`, `src/db.py::store_claim` ne; operatora lēmums — skaitāms vārts, ne koda maiņa.

## Pirmais skripta skrējiens (2026-09-30, dzīvā DB, tikai lasīšana)

| # | checked | flagged | piezīme |
|---|---|---|---|
| 1 | 199 | 11 | info |
| 1b | 10 751 | 205 | info |
| 2 | 113 | 2 | pieņemti 27, 62 |
| 3 | 35 | 1 | pieņemts 27 |
| 4 | 48 | 0 | needs_review 13, visi ≤7 d; sanity 0 |
| 5 | 68 | 1 | #710901 — kandidāts |
| 6 | 1 411 | 118 | info, augšējā robeža |
| 7 | 204 | 0 | spaiņi `-1`×4, `0`×47, `1`×204, `2`×94 |
| 8 | 17 247 | 14 378 | info; web 43 |
| 9 | 115 | 5 | pieņemti 96, 145; jauni 87, 100, 119 — `party` LPV pret frakciju ST, bet visi trīs ir jau piemēroti operatora T6 labojumi (87/100 `data/fix_party_role_cvk_review_2026-09-25.sql`, 119 `data/rollback_pleskane_party_2026-08-13.sql`) — pievienoti `ACCEPTED_9` (operatora lēmums 2026-09-30) |
| 9b | 28 | 6 | |
| 10 | 689 495 | 0 | A 387/0, B 8043/0, C 669825/0, D 11240/0 |
| 11 | 669 825 | 0 | |
| 12/15 | 2 670 | 283 | info; web 193, twitter 90 |
| 13 | 180 | 0 | kontrole 25/25; 172 `saeima_vote` izslēgti |
| 14 | 7 638 | 0 | |
| 16 | 176 | 0 | |
| 17 | 71 | 15 | 9 pieņemti; jauni 615955, 689768, 704089, 704179, 709073, 717710 |
| 18 | 7 755 | 0 | 33/33 |

Pilns skrējiens ~1,5 min (1b ~20 s, 13 ielādē iegulšanas modeli).
