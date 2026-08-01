# atmina — CHANGELOG arhīvs (2026-04 — 2026-08-04)

Vēsturiskie ieraksti, atšķelti no `CHANGELOG.md` četrās reizēs: 2026-07-21 (aprīlis + maijs; fails bija 180 KB), 2026-08-01 (jūnijs, 16 ieraksti / 29 KB; fails bija 141 KB), 2026-08-02 (jūlijs, 33 ieraksti / 87 KB; fails bija 145 KB) 2026-08-05 (agrīnā daļa 2026-07-31 — 2026-08-02, 22 ieraksti / 92 KB; fails bija 150 KB, operatora apstiprinājums) un 2026-08-09 (2026-08-03, 6 ieraksti / 38 KB; fails bija 110 KB — agrīna atšķelšana ar operatora apstiprinājumu, jo pilna mēneša failā vairs nebija: viena dienas sesija bija pievienojusi 10 KB). Sestā atšķelšana: 2026-08-19 (diena 2026-08-04, 3 ieraksti / 12,2 KB; fails bija 124 KB — slieksnis pārsniegts).
Enkuri saglabāti identiski; aktuālajā `CHANGELOG.md` atsauktajiem ierakstiem ir
enkuru-stubi ar norādi šurp. Jauni ieraksti VIENMĒR iet `CHANGELOG.md` — šis
fails aug ar atšķelšanām **un ar vienu izņēmumu**: kad `BACKLOG.md` atrodas
pabeigts darbs, kas pieder jau atšķeltam mēnesim, tas iet TIEŠI šurp, savā
datumā. Rakstīt to `CHANGELOG.md` nozīmētu likt jūlija ierakstu augusta failā;
atstāt to backlogā nozīmētu turēt pabeigtu darbu atvērto darbu failā. Šādu
ierakstu galvā ir citāta bloks, kas nosauc pārcelšanas datumu. Pirmais gadījums:
§ 2026-07-04 UI dizaina audits (pārcelts 2026-08-03).

---

## 2026-08-04 — Priekšrutīnas kopšana: pūls 5/5, ingests 5/5, #131 dublikāts dzēsts, vektoru-staleness detektors, skaļie CDN vārti, mirušo funkciju sweep

Trešais tās pašas dienas darba bloks (operatora "do it" pirms dienas rutīnas). Viss ar TDD, kur ir kods; pilnais `check.sh` zaļš.

- **X pūls izmērīts pilnībā vesels:** `probe_x_cookies.py` — visi 5 sloti, visi 4 endpointi (arī abi STRICT), 0 rebuild. Datu punkts ierakstīts BACKLOG § timeline-fallback: nulles dienas bija pārejošas bedres, ne hroniska konfigurācija.
- **Ingests pa kanonisko ceļu 5/5** (RSS 82 doki no 11/11 avotiem; twitter solis pārdzīvoja divus `ConnectTimeout` ar iekšējo retry). Diena 08-04 pēc palaidiena: 804 doki (113 web + 288 twitter + 362 x_mention + 41 vestnesis) — rinda silta rutīnai.
- **Pārskata dublikāts #131 dzēsts (operatora lēmums):** pilna pre-image rollback `data/rollback_brief131_dedup_2026-08-04.sql` komitēts pirms apply; note 131 + tā `approved=1` attēla rinda #4 (FK) vienā transakcijā. 16. pārbaude tagad `checked=119 flagged=0`, gaidītā vērtība prasmē nomainīta uz 0 ar dzēšanas pierakstu.
- **`scripts/audit_vector_staleness.py`** — šodienas trīsreiz rakstītā scratchpad metode tagad ir atkārtojams rīks ar iebūvētu kontroles kopu (krītoša kontrole = viss skrējiens ir metodes artefakts, exit 2; viss-stale bez kontroles tiek atteikts tāpat). 6 hermētiski testi (`tests/test_audit_vector_staleness.py`); 13. pārbaude prasmē pārrakstīta uz skriptu; dzīvā bāzlīnija `checked=54 match=54 stale=0`, kontrole 25/25. Pilnībā slēgtais BACKLOG ieraksts „Tikai-tēmas UPDATE atstāj claim_vectors ar veco tēmu" izņemts (noteikums dzīvo CLAUDE.md 8. punktā, detektors — 13. pārbaudē).
- **CDN aktīvi krīt skaļi:** `_download_chart_js` UN `_download_annotation_plugin` kļūmē met `RuntimeError`, klusais stubs izmests (aditīvā deploy stubs paliktu dzīvs mūžīgi); `rendered_site` fixture testos vairs neiet tīklā (lokāls stubs, visa render-chars kopa 14 s bez tīkla).
- **Mirušo funkciju sweep (BACKLOG (c), kopa atvasināta no jauna, jo ieraksts vārdus nesauca):** 672 augšlīmeņa funkcijas pret 1 320 failiem → 3 kandidāti. `extract_tweet_id` (ingest.py) un `format_issues` (lv_style.py) dzēstas; **`link_politician_to_document` paturēta ar nolūku** — idempotentā manuālo junction ieeja interaktīvām sesijām (78573 klase), tagad dokumentēta `wiki-tools.md`, kas tai dod arī dzīvu atsauci pret nākamajiem sweep.

## 2026-08-04 — Pieci BACKLOG [FIX] vienā sesijā: IZSKATĪTS forma, DIENAS STATS kanāli, rindas nogriešanas signāls, 0 baitu DB vārti, runbook kanoniskais ceļš

Pēcpusdienas sesija pirms dienas rutīnas, operatora uzdevums „izdari, kas izdarāms bez rutīnas". Visi pieci ar TDD (sarkans → zaļš); pilnais `check.sh` zaļš.

- **`review_status` derivācija pazīst `IZSKATĪTS`** — ceturtā atrisināšanas forma `src/db.py` konstantē, trigeri pārbūvēti, pašdziedējošais `init_db()` backfill pārklasificēja **31 rindu NULL → `reviewed`** (pirms-mērījums: tieši 31 no 574 192, visas NULL, neviena ar NEEDS_REVIEW blakus). Mazo burtu proza „izskatīts" nekad neatrisina rindu — `LIKE` nefoldē `Ī`; abas puses fiksē `tests/test_review_status_column.py`. Rollback: `data/rollback_review_status_izskatits_2026-08-04.sql`. CLAUDE.md eskalācijas 2. punkts atjaunots („marker form is cosmetic" tagad ir patiess); #7019/#7397 (marķiera nav vispār) pārcelti uz BACKLOG § T4 atlikums.
- **DIENAS STATS skaita pa `platform`, ne ar atņemšanu** (`src/briefs.py`): vestnesis vairs neuzpūš „Twitter/X" kausu, nezināmas platformas parādās kā „citi". Vārti `tests/test_briefs.py::TestDienasStatsPlatformCounts`. Skaitļa nestabilitāte starp lasījumiem NAV defekts — tā ir `scraped_at` mutabilitāte (CLAUDE.md § Schema invariants), un tā paliek.
- **`get_politician_documents()` nogriešana vairs nav klusa:** kad rindā ir vairāk par `max_results`, stderr brīdinājums un katrs atgrieztais doks nes `queue_total`; `claim-extractor.md` tagad liek pārsaukt ar pilnu apjomu. (08-03 LB gadījums: nogrieztais 21. doks bija operatora prioritāte Nr. 1.)
- **`get_db()` atsakās atvērt eksistējošu 0 baitu DB failu** — SQLite tādu uzskata par derīgu tukšu DB, tāpēc darbs tajā mirst klusi; `init_db()` ir vienīgais likumīgais tukša faila rakstītājs (`_allow_empty`). `tests/test_db_refuses_empty_file.py`.
- **`daily-routine.md` 1. solis pārkārtots:** kanoniskais ceļš ir `scripts/morning_ingest.py`; trīs atsevišķie izsaukumi tagad ir avārijas variants ar brīdinājumu, ka apstāšanās pēc otrā neatstāj pēdas.
- Blakus: `tests/test_schema.py` bāzlīnija pārģenerēta pa paša testa REGEN ceļu (trigeru teksts ir daļa no `sqlite_master`).

**Tās pašas sesijas `/audit-integrity` pilnais sweep (16 pārbaudes, read-only, ierakstīts `logs`).** Tīrs pret bāzlīnijām: orphans 30/0, provenance A–D visi 0, trijnieku delta 0, per-vote 6465/0, same-day dubulti 1050/0, stale-party valoda 38/0, needs_review rinda vesela (38 atvērtas, neviena >14 d, trigeru sanity 0), 16. pārbaude tieši gaidītajā `120/1` (id 131). Jauni atradumi → BACKLOG: **14 ar roku labotas rindas ar stale vektoru** (13. pārbaude, `checked=54 stale=14`) un **`faction` etiķetes split `ST!`/`ST`** (9. pārbaude — 10 Stabilitātei! deputāti, partijas lauks NAV kļūdains, mans pirmais lasījums ar mūža-segumu bija artefakts; triāža pēc loga to noķēra). Zināmie stāvokļi apstiprināti: Svirskis x_handle 94/1, junction inversija stabila `1274/280` (22,0 %), pretruna #40 `confirmed=0` >30 d gaida operatoru. **7. pārbaude: `138/0`, bet tas ir jālasa kopā ar pārbaudāmās kopas maiņu** — sākotnēji šī sesija zaļo nolasīja nepareizi („varianti uz diska, atlicis deploy"), un tas bija tieši vakuozā zaļā slazds: #93/#96 vairs NAV `approved=1` kopā. Faktu pārbaude parādīja: abas rindas ir `approved=2`, variantu uz diska NAV, un dzīvās lapas ir pārrenderētas uz vietnes fallback `og:image` — **dzīva defekta vairs nav**, un `approved=2` semantika izmērīta pirmo reizi: 71 rinda / 44 notes, 40 no tām ar `approved=1` aizstājēju (= atcelts kandidāts), 4 bez aizstājēja (tostarp #93/#96 — attēls atcelts, lapa uz fallback). BACKLOG (d) „divās rindās" skaitlis izlabots; 7. pārbaudei pievienota `approved` sadalījuma rinda, lai kopas maiņa nākamreiz ir redzama pašā izvadē.

**Audit-13 atradums slēgts ar operatora apstiprinājumu tajā pašā dienā.** 14 stale rindas pārrēķinātas (`reembed_claims.py --ids-from data/reembed_audit13_vectors_2026-08-04.ids`); pāra rollback ar **eksaktiem hex pre-image baitiem** (`6d216cb1`, 14 rindām ~45 KB ir proporcionāli — elektr receptes izvēle bija par 9 171 rindām/15 MB) komitēts pirms apply. Cēloņu izlase: #555845 stance labots 07-30, #555782 topic labots 07-29 — abi pirms 08-02 re-embed noteikuma, tātad procesa pārkāpuma pēc noteikuma nav; #548451 08-03 labojums bija tikai `quote` (embedding tekstā neietilpst), drifts vecāks. Pēc-pārbaude pār visu ar roku laboto kopu: `checked=54 match=54 stale=0 missing=0`, bāreņi nemainīgi 7 004.

**Turpinājums tajā pašā sesijā — 06-13 topic-drift vektoru atlikums izmērīts un aizvērts.** BACKLOG turēja pieņēmumu, ka 08-02 dedup re-embed to kopu jau aizvēra; mērījums parādīja pretējo. No 4 075 kopas rindām (ids no pāra rollback faila) dzīvas **167**, un **visas 167 bija stale** — vektors joprojām kodēja pirms-migrācijas tēmu. Metode pierādīta abos virzienos, pirms tai ticēt: kontrole uz 50 elektr rindām (pārrēķinātas 08-03) deva `match=50`, un provenance 60/60 — glabātie baiti sakrīt ar `embed_text(f"{VECĀ_tēma}: {stance}")`, VECO tēmu lasot no 06-13 rollback faila (tātad arī embedding modelis nav mainījies). Labojums pa elektr precedenta ceļu: ids fails + rollback-recepte komitēti PIRMS apply (`97036cec`), `scripts/reembed_claims.py --ids-from` pārrakstīja 167/167 („MAINĪJĀS"), neatkarīgā pēc-pārbaude `checked=167 match=167 stale=0`, bāreņu identitāte nemainīga (581 196 − 574 192 = 7 004), claims bez vektora 0. Dzēsto sadalījums pierakstīts godīgi: 3 829 no 3 908 ir 08-02 dedup dublikāti, 79 — citi tīrījumi.

## 2026-08-04 — Atliktais deploy izpildīts: 13 vēlīnas pozīcijas pārskatā #406, vārdabrālis, kas izskatījās pēc novecojuša lauka, un dokumentu skaits, kas gāja uz leju

Nakts sesija, kas pabeidza 08-03 rutīnu: operators bija atlicis deploy līdz nākamajam ingestam, un tieši tas ingests atnesa materiālu, kura dēļ pārskats bija jāatsvaidzina.

**Ingests pa pilno ķēdi, ne pa pusei.** Pirmais palaidiens bija tikai `src.ingest` (RSS); tas ir puse no ceļa, tāpēc pēc tam `scripts/morning_ingest.py` 5/5 — **309 jauni dokumenti** (35 web + 92 twitter + 141 x_mention + 41 vestnesis) un autoritatīvā `logs` rinda, ko lasa `_check_ingest`. Ekstrakcija: 20 politiķi / 57 doki, 20 paralēli `@claim-extractor` (Opus) divos viļņos + **obligātais otrais sweep** Lapsam (18 doki > 12 cap) → **13 pozīcijas, visiem `failures=[]`**, rinda iztukšota. Otrais sweep atmaksājās ne ar claims (0, kā prognozēts), bet ar to, ka pirmā aģenta apraksti diviem dokiem bija nepareizi — prognozi pārbaudīja, nevis apzīmogoja.

**Visas 13 pozīcijas ar `stated_at=2026-08-03`, tāpēc tās pieder #406, ne 08-04.** Lēmums balstīts `_BRIEF_DAY_CLAIM_SQL` pirmajā zarā un tajā, ka lapa vēl bija **404 dzīvajā vietnē** — tātad melnraksta atsvaidzināšana, ne publicēta teksta pārrakstīšana. Divas jaunas sadaļas: `Veselības aprūpe` (ZZS prasa atcelt slimnīcu reformu; premjers — lēmums pieņemts, lai liek datus galdā) un `Sociālā politika` (75 % vecāku pabalsts trijos horizontos). Pārskats 33 355 → 45 352 zīmes, viena rinda, `brief_images` FK neskarts.

**`@quality-reviewer`: PASS WITH FIXES — nepatiess amats pie nosaukta cilvēka.** Aivis Ceriņš bija nosaukts par „Apvienotā saraksta deputātu"; DB `role` deputāta amatu nesatur un `saeima_individual_votes` rindu viņam ir **0**. Turklāt izņemts neapstiprināts noliegums („izmeklēšanas iestādes lietā nav iesaistītas" — 45 pārbaudītos dokumentos par to nav ziņu) un atmiņas pašas juridisks secinājums („ētikas, ne tiesību telpā") no Rasimas kompensācijas rindkopas. Seši labojumi ar pāra rollback un pirms/pēc enkuru pārbaudi (katrs 1× pirms, 0× pēc). `data/{fix,rollback}_brief406_quality_review_2026-08-04.sql`.

**Vārdabrālis, ne T6.** Rakstā par KNAB/EPPO Jelgavas slimnīcas iepirkumiem „Mārtiņš Daģis („Par!")" izskatījās pēc novecojuša `party` lauka — un nav: id=81 ir JV deputāts ar **6 473 balsojumiem `faction='JV'`** līdz 07-23. Ekstrakcijas aģents to pārbaudīja pats un neko nesaglabāja. Esošais `negative_patterns` neizšāva frāzes formulējuma dēļ („Jelgavas slimnīca" pret „Jelgavas valstspilsētas pašvaldības"). BACKLOG § Matcher.

**Dokumentu skaits, kas gāja uz leju.** Pārskata skelets 08-04 rādīja 646 dokumentus tur, kur 08-03 vakarā bija 653. Nekas nepazuda: septiņus web dokus izdevēji bija rediģējuši, un URL-kanoniskais dedup tos atjaunoja uz vietas, pārrakstot `scraped_at` uz šodienu — tātad rindas pārgāja uz citu dienu. Ierakstīts CLAUDE.md § Schema invariants, jo tas izskatās pēc datu zuduma un nav; pats DIENAS STATS defekts (vestnesis skaitās „Twitter/X") → BACKLOG.

**Deploy un pārbaude.** `check.sh` 1842 passed; narrow renders 9 domēnos ar `static`; `deploy.sh --no-delete` pēc operatora apstiprinājuma; dzīvajā pārbaudīti 8 URL — pārskata lapa, visi **četri** attēla varianti, blog indekss, about un sitemap, baitu izmēri sakrīt ar lokālajiem.

**Social: X pavediens (7 tvīti), FB posts, Reddit ieraksts — visi publicēti 08-04.** Operatora prasība bija 10. klases lasāmība; mērīts, ne apgalvots (11,7 vārdi teikumā pavedienā, 0 no 15 pārbaudītajiem žargona marķieriem). Divi noteikumi ierakstīti [`operacijas.md`](operations/operacijas.md), jo Reddit nav prasmes: **daudzskaitļa pirmā persona** („sekojam", ne „sekoju" — vienskaitlis personalizē projektu pretēji anonimitātes noteikumam; iepriekšējie pieci melnraksti un trīs publicētie posti bija vienskaitlī) un **biežums** — noteikums līdz šim dzīvoja tikai melnrakstu iekšienē un tāpēc tika pārkāpts: četri posti trijās dienās. Reddit attēls uzzīmēts ar kodu (PIL, Georgia), nevis ģenerēts — teksta halucinācijas klase, kas 08-03 divreiz sabojāja vietvārdu, tā vienkārši nav iespējama; paletes validators pa ceļam noraidīja divu toņu ideju, jo tumšais tonis ir teksta, ne sērijas krāsa, tāpēc kategorijas kodētas ar formu.


## 2026-08-03 — Pilna rutīnas diena: 653 dokumenti, 56 pozīcijas 4 viļņos, needs_review 139→31, un vārti, kas noķēra pārveidotu skaitli

Pēcpusdienas sesija, kas izpildīja visu rutīnas ķēdi un pa ceļam operatora uzdevumā iztīrīja `needs_review` rindu. Deploy APZINĀTI nav — operatora lēmums publicēt pēc nākamā ingesta, pārskatu pirms tam atsvaidzinot.

**Ingests pa kanonisko ceļu, ekstrakcija 4 viļņos.** `scripts/morning_ingest.py` 5/5 soļi, 652 dokumenti (91 RSS + twitter + mentions + 24 vestnesis); vēlāk +1 (Velpa oriģināltvīts, sk. zemāk). Ekstrakcija: 49 politiķi / 161 doku vienības, 4 viļņi × ~12 paralēli `@claim-extractor` (Opus) → **56 pozīcijas no 29 politiķiem, visi `failures=[]`, 56/56 pretrunu pārbaudes ar 0 kandidātiem** (godīga nulle — katrs aģents ziņoja savu denominatoru). Doc 79064 metadati: `published_at='2026-06-01'` (mēneša precizitātes grīda no galvenes „Vadlīnijas | Jūnijs 2026") + junction pid=243 (`data/fix_doc79064_metadata_2026-08-03.sql`).

**Velpa ievākšanas robs aizvērts ar LB precedenta metodi.** Viņa „bijušais NA vēlētājs" tvīts korpusā bija tikai kā cita RT; `client.search_tweet("from:AndrisVelps ...")` + viens `reset_transaction_key()` pēc STRICT-404 (runbook ceļš) → doc 79711 → #615884.

**Spriedze #181 (Šlesers↔Dombrava, Pāternieki) + tendences #402–405.** T6 pārbaude pirms rakstīšanas noķēra divus manas galvas faktus: Seržants ir AS (ne ZZS — tātad LB kritika nāk no premjera paša partijas), Švinka ir demisionējis satiksmes ministrs (ne klimata ministrs).

**needs_review triāža 139→31 (operatora rīkojums).** 11 paralēli aģenti, 139 rindas: **87 atrisinātas** ar nosauktu pamatu (`Izvērtēts 2026-08-03:`, iesaldētie lauki baitu līmenī nemainīti, vektori neskarti), 39 B + 13 C nodoti operatoram vienā sarakstā. Operatora lēmumi piemēroti tajā pašā vakarā (`scripts/fix_triage_decisions_2026-08-03.py`): **7 dzēšanas** (rindas+vektori vienā transakcijā), **11 stance/quote labojumi** (visi šaurāki par veco — QR to pārbaudīja pret avotiem), **5 tēmu migrācijas** ar kolīziju priekšpārbaudēm, **15 re-embed**. Jauns tēmu noteikums ierakstīts `claim-extractor.md`: **tēmu nosaka izteikuma nosauktais pamatojums, ne instruments** (Pāternieku trio → Imigrācija).

**Rollback failu vārdu kolīzija — incidents un noteikums.** Četri triāžas aģenti rakstīja vienā `data/rollback_needs_review_triage_2026-08-03.sql` cits citam pāri; divas pre-image kopas rekonstruētas no `pre-dup-cleanup-20260802` momentuzņēmuma (viena — ar dokumentētu statusa-līmeņa tuvinājumu 3 šodienas rindām). CLAUDE.md eskalācijas 8. punktā tagad: **paralēliem aģentiem unikāli rollback vārdi**.

**Pārskats #406: uzrakstīts → izkorektūrēts → refreshots → BLOKĒTS → izlabots.** Trīs manas korektūras kļūdas abās virsmās; pēc mutācijām refresh ar 24/24 tēmu rekonsiliāciju; tad `@quality-reviewer` (visi denominatori nosaukti) deva **BLOCK: „ap 600 automašīnu" bija pārveidots skaitlis** — avotā tā ir biedrības „Latvijas auto" vadītāja APLĒSE par četrās dienās potenciāli skartajām mašīnām, kamēr Robežsardze skaitli nenosauc un LSM reportāžā rindā stāv „padsmit kravas auto" (doc 79092 pret 79101). Nepiedēvēts tas stāvēja PIECĀS virsmās (Galvenais buleta, konteksta lodziņš, tendence #402, spriedze #181, Spriedžu tabulas šūna) + vizuālā brief Skaitlis. Izlabots visās ar `data/rollback_600_attribution_2026-08-03.sql`; Skaitlis → „-". Piektā virsma (Spriedžu tabulas verbatim citāts) atklājās tikai ar pēc-piemērošanas assert — meklē frāzi, nepieņem gadījumu skaitu.

**Attēls: modelis divreiz sabojāja vietvārdu.** „Pāternieku" → „Pātermieku"/„Pātenieku" divos ruļļos ar identisku promptu (LV tipogrāfijas cietais limits, ne nejaušība) → bez-teksta versija 246 apstiprināta, 244/245 noraidīti ar `reject_image()` iemesliem.

**Testu labojums:** `test_extraction_scope.py` iekodētais `DAY="2026-08-02"` no rīta gāja zaļš un tā paša 08-03 vakarā sarka (24h logs paslīdēja garām fixture) — DAY tagad dinamisks; timestamp saimes klase.

**Sistēmiskie atradumi (visi BACKLOG ar metodēm):** marķieris `IZSKATĪTS` trigerim nezināms → 31 rinda neredzama abās rindās; **13 citāti, kuru web avots pēc pārskrāpēšanas vairs nesatur citēto tekstu** (1422→30→13, vārtu šai klasei nav); fantoma `mentioned` junctions bez vārda tekstā (Stendzenieks 296/90d, doc 78108 abos virzienos); `get_politician_documents` `max_results=20` klusi nogrieza LB rindu tieši uz prioritārā doka; T1 jaunā apakšklase fem `-e`/masc `-is` akuzatīva homogrāfi (Lāce/Lācis); 4 jaunas medību pēdas @contradiction-hunter.

**Stāvoklis nodošanai:** renders sagatavots (11 domēni ieskaitot `static`, `check_output` tīrs), deploy gaida operatoru pēc nākamā ingesta; `needs_review` 31 (visas ≤14 d, katrai dokumentēts B lēmums vai iemesls); pretrunas 30 (0 jaunu); NBS doc 77881 joprojām gaida institūcijas slota lēmumu.

## 2026-08-03 — Elektr migrācijas 9 171 vektors pārrēķināts: pirmais šodienas ieraksts, kas izrādījās ĪSTS

Diena pagāja, izgriežot fantomus; šis ir tas, kas palika, kad fantomi bija projām. **2026-07-28 „elektr" migrācija mainīja `claims.topic` ar kailu `UPDATE` un vektorus nepārrēķināja**, tāpēc 9 171 `saeima_vote` rindai `claim_vectors` joprojām kodēja veco tēmu `Degviela un enerģētika`, kamēr pati rinda jau sen sauca sevi citādi. Nekas nekrita — `search_similar_claims()` klusi ranžēja tās pēc tā, ko tās agrāk teica. Tieši tas ir CLAUDE.md eskalācijas 8. noteikuma iemesls.

**Vispirms mērījums, tad darbs.** Izlasei pārrēķināts `embed_text(f"{topic}: {stance}")` un salīdzināts ar glabāto vektoru: **300 no 300 neatbilda**, vienmērīgi pār visām piecām tēmu grupām. Tikai pēc tam kaut kas tika rakstīts.

**Apjoms ņemts no migrācijas pašas `WHERE`, ne no nojautas.** 105 balsojumi piecās grupās → **precīzi 9 171** claims, kas sakrīt ar migrācijas galveni. Plašākais `saeima_votes.motif LIKE '%lektr%'` vaicājums dod **10 449** un ir tikai augšējā robeža — tas ķer arī rindas, kas nekad nav bijušas `Degviela un enerģētika`. Sākt pārrēķinu no 10 449 nozīmētu pārrakstīt 1 278 rindas bez iemesla.

**Provenance pierādīta, ne pieņemta.** Pirms rakstīšanas pārbaudīts, ka glabātais vektors baits pret baitu sakrīt ar `embed_text(f"Degviela un enerģētika: {stance}")` (paraugs #52260), un ka `embed_text` ir determinēts. Tas nozīmē divas lietas: novecošana tiešām nāk no šīs migrācijas, un vecais stāvoklis ir atjaunojams no rindas `stance` bez baitu glabāšanas. Pāra rollback tāpēc glabā **recepti**, ne 15 MB hex — tas pats lēmums un tas pats pamatojums, kas `rollback_dup_saeima_vote_claims_2026-08-02.sql`.

**Rollback komitēts PIRMS mutācijas** (`ebbbee54`): `data/rollback_reembed_elektr_vectors_2026-08-03.sql` + `data/reembed_elektr_vectors_2026-08-03.ids` (9 171 rinda; pozicionālie id neder, jo ~64 tūkst. rakstzīmju komandrindā pārsniedz Windows ~32 tūkst. limitu).

**Rezultāts un neatkarīga pārbaude.** `scripts/reembed_claims.py --ids-from` pārrakstīja **9 171 rindu, visas ar „MAINĪJĀS", 0 nemainīgas** — nemainīga rinda šeit būtu bijusi signāls, ka kaut kas nav aiztikts. Pēc tam ar CITU nejaušu izlasi: **`checked=300 match=300 stale=0 missing=0`**. Integritāte neskarta: `claim_vectors` 581 134 pirms un pēc (aizvietots, ne pievienots), claims 574 130, bāreņi 7 004, claims bez vektora 0.

**Paliek atvērts un apzināti NAV pasludināts par slēgtu:** 2026-06-13 topic-drift migrācijas kopa nav pārbaudīta. Ir ticams, ka to jau aizvēra 08-02 dedup, kas pēc dzēšanas palaida pārrēķinu — bet tas ir pieņēmums, un šī diena bija par to, kas notiek, kad pieņēmumu pieraksta kā faktu.

## 2026-08-03 — BACKLOG verifikācijas sweep II: seši novecojuši ieraksti, un visa uzdevumu saraksta augšgals bija fantoms

Sesija sākās kā salīdzinājums starp nodošanas piezīmi un no BACKLOG uzbūvētu uzdevumu sarakstu. Salīdzinājums pats atklāja, ka **saraksta augstākā prioritāte bija fantoms**: visi trīs uz āru vērstie darbi jau bija padarīti, un katrs tur nokļuva tāpēc, ka BACKLOG apgalvojums tika lasīts kā stāvoklis, ne kā hipotēze. Tas pats paterns 2026-08-02 sweep-ā deva 6 no 10 ierakstiem, iepriekšējā vakara sesijā — 5 ierakstus.

**Pārbaudīts pret dzīvo sistēmu, ne pret failu:**

**1. „Dzīvajā vietnē joprojām ir vecais teksts" (20 citāti) — NEPATIESS.** Siliņas profila lapā salabotā forma `pievīluši savu doto solījumu` parādās divreiz, vecā nulle reižu (HTTP, 2026-08-03). Renders un deploy nebija vajadzīgi.

**2. Tā paša ieraksta tvērums bija par plašu.** `templates/politician.html.j2:527` renderē `c.quote` TIKAI komentāru blokā, un visas 20 labotās rindas ir pirmās puses pozīcijas, tāpēc publiskā virsmā nonāca **viena** — #6, caur divām apstiprinātām pretrunām. **Noteikums, kas no tā izriet:** citāta labojums pēc noklusējuma NEprasa renderu; vispirms pārbaudi, vai tā virsma citātu vispār rāda. Ierakstīts § Ne-darīt.

**3. Sintēžu wikilinki — jau salaboti** (`f3c6e10a`): failā 0 `[[` formu, un klasi sargā `tests/test_synthesis_no_wikilinks.py`.

**4. Trīs sociālo tīklu melnrakstu ⛔ — noņemts.** Visi trīs publicēti 2026-08-03.

**5. Latvijas Bankas ieraksts bija pretrunā pats ar sevi četrās vietās.** Virsraksts sacīja „pavediens korpusā joprojām ir 1/3", kamēr paša ieraksta 08-03 bloks fiksē visus trīs tvītus; divi apakšpunkti sacīja, ka vadlīniju dokuments nav `documents` tabulā un tā adrese nav zināma, kamēr dažas rindas augstāk ir pierakstīts doc **79064**. Pārbaudīts DB: 79064 eksistē, `datnes.latvijasbanka.lv`, 78 132 zīmes, bez `published_at` un bez junction uz pid=243 (abi paliek atvērti).

**6. `needs_review` 119 → 118**, `reviewed` 234 → 235. Vecums pārmērīts: 76 rindas ≤7 d, 42 rindas 8–14 d, vecāku nav; vecākā ir 2026-07-20, t.i. **tieši uz 14 dienu robežas**, ko pass-kritērija lēmums grib par slieksni.

**Izmaiņas failā:** četri `[DONE→CHANGELOG]` ieraksti izgriezti pēc tam, kad katrs tika ATRASTS šajā failā, ne pieņemts par pierakstītu; ieraksti **67 → 64**. Sadaļa „Publiskā vietne — korektums un vārti" pārsaukta par „renderēšana un veiktspēja", jo pēc izgriešanas tajā palika tikai divi veiktspējas ieraksti un ievadteikums „pirmais ieraksts ir pārējo sakne" vairs neatbilda saturam.

**Divas lietas apzināti NEIZMESTAS.** (a) 0 baitu `.db` vārtu ideja bija ierakta `[DONE→CHANGELOG]` ierakstā, lai gan nav ieviesta — pārbaudīts, ka `src/db.py` izmēra pārbaudes nav (`st_size`/`getsize` neparādās nevienā ceļā), tāpēc tā tagad ir atsevišķs `[FIX]`. (b) Trīs slēgtie gadījumi pārcelti uz § Ne-darīt, jo tieši tur šis projekts glabā „izmeklēts un noraidīts"; citādi nākamā sesija tos atklātu no jauna.

**Metodiska piezīme par nodošanas piezīmi.** Skaitlis „pārskati 93/96 ar 404 hero" lasās kā attiecība, bet tie ir `brief_images` rindu numuri **#93 un #96** — divi pārskati, 2026-05-19 un 2026-05-22 (sk. šā faila 2026-08-02 ierakstu). Nolasīts kā attiecība, tas sāktu 93 pārskatu kampaņu, kuras nav. Tā ir tā pati klase, pret ko brīdina pati piezīme: skaitlis bez metodes nav skaitlis.

### Verifikācijas skrējiens pār pārējiem ierakstiem (turpinājums, tā pati diena)

Pēc izgriešanas palaists `/audit-integrity` pilnā apjomā plus mērķa vaicājumi tiem BACKLOG skaitļiem, ko prasme nesedz. **Šoreiz lielākā daļa turējās** — pretstatā rīta atradumiem, un tas ir tikpat svarīgi pierakstīt, jo citādi nākamā sesija sāk neuzticēties visam failam.

**Turas precīzi (neaiztikt):** `claim_vectors` bāreņi **7 004**; claims bez vektora **0**; liekās chunk rindas **690**; pretrunas **30 rindas, 0 dublikātu, 0 karājošos atsauču**; junction inversija **`checked=1273 flagged=280` (22,0 %)**; **32** kanoniskās tēmas ar **0** nekanoniskām; trīs aizklāto vēlēšanu čaulas ar 0 individuālajām balsīm; 16. pārbaude `checked=119 flagged=1` (id 131, kā paredzēts). Tīras arī 10A/B/C (`0/0/0`), 11. (`delta=0`) un **14. (`checked=6465 flagged=0`)** — pēdējā ir vienīgā rinda, kas visā tabulā attaisno `store_vote()` no partial write.

**Trīs skaitļi bija nepareizi:**

**1. `x_handle` novirze — „9+1" ir tagad `checked=97 flagged=1`.** Palicis Svirskis id=62 (`ESvirskis` pret `realNepareizais`).

**2. „586 dokumenti ar dublētu chunk" — 586 ir GRUPU skaits, dokumentu ir 320.** Liekās rindas (690) sakrīt precīzi, tāpēc kļūda ir marķējumā, ne mērījumā; tīrīšanas apjoms tomēr ir 1,8× mazāks, nekā pierakstīts.

**3. Pozīcijas 5 053 → 5 117** (33. tēmas ierakstā, kur skaitlis ir daļa no pārvērtēšanas sliekšņa). Nekanonisku joprojām 0, tāpēc atlikšanas pamats turas.

**Viens ieraksts APSTIPRINĀJĀS kā īsts defekts, ar mērījumu.** Elektr-migrācijas rindām pārrēķināts `embed_text(f"{topic}: {stance}")` un salīdzināts ar glabāto vektoru: **25 no 25 izlases rindām NEATBILST** — vektors joprojām nes veco tēmu (paraugs: claim #15243, `topic='Sabiedriskie mediji'`). Tas nav fantoms; pārrēķins ir jāizdara. Apjoms jāņem no migrācijas pašas `WHERE`, nevis no šodienas 10 449, kas ir augšējā robeža.

**Divi skaitļi PALIEK nepārbaudīti, un tas te tiek pierakstīts godīgi:** pmo.ee „97 paywall stubi" un lsm „~592 truncated" — abiem nav zināms slieksnis, ar kādu tie mērīti. Mans `word_count < 90` dod 393 un 1 068, bet tas ir cits vaicājums, tāpēc **tas nav pierādījums, ka pierakstītie ir nepareizi**. Salīdzināt drīkst tikai ar to pašu metodi; pretējais būtu tieši tā kļūda, ko šis skrējiens meklē.

## 2026-08-03 — Latvijas Bankas loks noslēgts: pavediens ievākts, spriedze precizēta, vadlīnijas atrastas uz cita resursdatora

Viena diena, kurā trīs reizes izrādījās, ka šķērslis nav tur, kur to bija pierakstījuši.

**1. Pavediena tvīti 2/3 un 3/3 nebija „nepieejami" — tie bija citā endpointā.** `fetch_user_tweets` (`tweet_type="Tweets"`) izlaiž paša atbildes, `fetch_user_replies` atgriež sarunas VECĀKUS, un `get_tweet_by_id` krīt ar `KeyError 'user_results'` tieši tā, kā brīdina `fetch_tweet_by_id` docstring. Atrada `client.search_tweet("from:LatvijasBanka since:… until:…")`. Ievākti doc **79061** (2/3), **79062** (3/3) un **79063** — atsevišķa LB atbilde tieši Kulbergam, par kuru neviens nezināja. Visiem `role='subject'` pid=243, stored == intended (3/3). **ID tika ATRASTI, ne uzminēti** — uzminēts status ID 2026-07-29 ienesa izdomātu provenanci publicētā pārskatā.

**2. Spriedze jau eksistēja (#180), un otra reģistrēšana būtu radījusi dublikātu**, jo `store_tension()` ir kails INSERT bez dedupa. Nepareizs bija tikai apraksta pēdējais teikums, kas pēc ievākšanas kļuva nepatiess. Labots ar pāra rollback; 162 → 162 rindas, `created_at` (UTC) neaiztikts, teksts pārbaudīts ar `validate_lv_diacritics()` ar roku, jo kails UPDATE apiet store-funkcijas vārtus.

**3. Vadlīnijas bija uz CITA resursdatora.** `www.bank.lv` no šīs vides neatbild ne sandboxā, ne bez tā, ne no īsta Chromium (`HTTP 000`, `tls=0.000000s`, `net::ERR_TIMED_OUT`), un fona lejupielāde ar 540 s logu krita ar `curl exit 28`. `WebSearch`+`WebFetch` iet pa serveri, ne pa šo mašīnu, un uzrādīja **`datnes.latvijasbanka.lv`** — tas lejupielādējas **0,45 sekundēs**. Ievākts kā **doc 79064**.

**Rezultāts: pārskats #400 bija pareizs.** No glabātā teksta: `Nelabvēlīgs` 25, `Labvēlīgs` 25, `klient*` 138, `(ne)labvēlīg* klient*` 0 abās vārdu secībās. `@quality-reviewer` tos nevarēja atveidot vienīgi tāpēc, ka dokumenta korpusā nebija — pareiza piesardzība uz nepilnīgiem datiem, ne kļūdains atradums.

**Metode ir daļa no skaitļa.** 138 ir reģistrjutības ziņā NEJUTĪGS celma skaits; reģistrjutīgi tas pats celms dod **79** (59 ar lielo burtu tabulu šūnās), precīzs nominatīvs „klients" — 95. Šī sesija pati uz mirkli „atrada neatbilstību", jo divos skriptos lietoja atšķirīgu `re.I` karogu. Pierakstīts, lai nākamais pārrēķinātājs nesāktu to pašu apli.

**4. Pārskats #400 labots (operatora apstiprināts, pāra rollback, deployots).** Avots kļuvis klikšķināms — divas raw `<a>` saites uz vadlīniju dokumentu un vēstuli ZM (markdown tur nestrādā: konteksta bloks ir raw HTML). Teikums „ir atrodams tikai Latvijas Bankas publiskajā atbildē" precizēts, jo tā pati nostāja ir formulēta arī vēstulē ministrijai („brīvprātīgi izmantojams palīginstruments"). **Instanču bija DIVAS** — tā pati frāze citos vārdos stāvēja „Galvenais" ievadpunktā, un to atrada tikai tāpēc, ka pēc-piemērošanas pārbaude MEKLĒJA frāzi, nevis pieņēma vienu gadījumu.

**Jauns fakts par stāstu:** LB vēstule atbild uz Zemkopības ministrijas **08.07.2026** vēstuli — publiskais strīds ir vismaz trīs nedēļas ilgas iestāžu sarakstes redzamā daļa, ne divu dienu uzliesmojums. Precizitātes robeža: pašas vēstules datums ir paraksta laika zīmogā un tekstā NAV redzams, tāpēc drīkst apgalvot tikai ministrijas 8. jūlija vēstuli, nevis ka LB atbildējusi pirms Kulberga ierakstiem.

**Publicēts 2026-08-03 (operators):** X pavediens par nedēļas analīzi (6 tvīti, 5 sepia attēli + nedēļas plakāts), X pavediens par 08-02 dienas analīzi (5 tvīti, 5 attēli + dienas plakāts), abi FB posti **un r/latvia posts par 08-02 fakta pārbaudi** (ar `2026-08-02-thread-3-parbaude.png`).

**Reddit biežuma iebildums tika izteikts un operatora apzināti pārsvītrots.** Sesija iebilda, jo 07-31 un 08-01 ieraksti izgāja 08-02 ar vienas dienas starpību; operators izlēma postēt tik un tā, un no diviem gataviem melnrakstiem izvēlējās ieteikto — fakta pārbaudi, ne nedēļas kopsavilkumu. Iebildums melnrakstā paliek pierakstīts, nevis dzēsts, jo tieši pēc tā faila nākamā sesija spriež, kad logs atkal ir atvērts: **nākamais r/latvia posts ne agrāk kā ~2026-08-17.**

**Pirms nodošanas posta korpusā tika izlabota pretruna pašam ar sevi:** viena rindkopa apgalvoja, ka teikums par neobligātumu „ir atrodams tikai bankas publiskajā atbildē", kamēr divas rindkopas zemāk stāvēja, ka tā pati nostāja ir formulēta arī vēstulē ministrijai. Tā ir tā pati klase, kas pārskatā #400 bija DIVĀS vietās — un abos gadījumos to atrada tikai tāpēc, ka teksts tika pārlasīts pēc papildinājuma, ne pirms tā.

**Atklāts paliek:** doc 79064 ir bez `published_at` un bez junction uz pid=243; glabātais PDF ir „Jūnijs 2026" redakcija, kamēr pārskats runāja par 11.05.2026 izsludināšanu; doc 78573 un 79061–79063 joprojām ir ekstrakcijas rindā ar 0 claims.

> Pārcelts no BACKLOG 2026-08-05.

**`t.co` un `bank.lv` bija DIVAS dažādas kļūmes, ko iepriekš jauca kopā.** `t.co` = lēnums: priekšplānā tas krīt ar `_ssl.c:993 handshake timed out` pēc ~120 s, bet fonā tas pats pieprasījums atgriež 301 ar īsto adresi — agrākais pieraksts „vidē beidzies SSL sertifikāts" bija nepareiza diagnoze, un no tā izriet, ka pārējās „neatrisināmās" `t.co` saites, visticamāk, ir dabūjamas ar garāku logu. `www.bank.lv` turpretī ir nesasniedzams: gan saknes lapa, gan PDF dod `HTTP 000` ar `tls=0.000000s` (rokasspiediens pat nesākas), fona lejupielāde ar 540 s logu krīt ar `curl exit 28`, kamēr kontrole tajā pašā brīdī — `atmina.lv` — atbild 200 pēc 0,86 s. Tur garāks logs nepalīdz un `ingest_url.py` arī ne; dokumentu var ievākt tikai no vides, kas sasniedz `bank.lv`.

**LB vēstule Zemkopības ministrijai satur atzīšanos, kas noder Kulberga pusei:** „Latvijas Bankas rīcībā nav informācijas par dabas risku vadības instrumentu precīzi novērtējamu ietekmi uz kredītpolitiku… nav iespējama arī precīza makroekonomisku ietekmju novērtēšana." Iestāde tātad nevar pierādīt arī ietekmes NEESAMĪBU, un uzraudzības spiediena arguments ar šo vēstuli nav atspēkots. Sešos sociālo tīklu melnrakstos tas ir iekšā abos virzienos.

**Procesa mācība.** Kad prasīja ievākt vienu tvītu pēc ID, sesija sāka rakstīt twikit izsaukumus ar roku un dabūja `KeyError 'user_results'`, tad `KeyError 'itemContent'` — kamēr `src/x_scraper.py::fetch_tweet_by_id()` jau eksistē, lieto batch endpointu tieši šī iemesla dēļ un savā docstring nosauc to pašu kļūdu. Grep pirms rakstīšanas būtu maksājis vienu izsaukumu.

## 2026-08-03 — Vakars: `source_url` indekss izmērīts, topic formas apvienotas, un PIECI BACKLOG ieraksti izrādījās jau padarīti

Sesija sākās kā BACKLOG izpilde un pa ceļam kļuva par verifikācijas skrējienu. **Pieci ieraksti aprakstīja darbu, kas jau bija izdarīts, un divi no tiem būtu licis mainīt publicētu saturu, lai salabotu defektu, kura nav.** Tas ir tas pats paterns, ko 2026-08-02 sweep atrada 6 no 10 ierakstiem — skaitlis vai apgalvojums BACKLOG-ā ir hipotēze, līdz to pārbauda pret dzīvo sistēmu.

**1. `claims.source_url` indekss — pievienots pēc mērījuma, ne pēc nojautas.** `src/db.py` `init_db()` (`idx_claims_source_url`). Abas puses mērītas pret dzīvo DB (574 130 claims, 6 867 balsojumi): drošības vaicājums **935,5 s → 0,0 s**; ieraksts **0,120 → 0,133 ms/rinda (+10,8 %)**, mērīts ar 3 000 īstiem `INSERT` transakcijā, kas pēc tam atritināta; DB **+61 MB**. Plānotajai 2025. gada ielādei tas ir ~2 sekundes kopā. **BACKLOG rakstīja „pārsniedza 120 s" — patiesībā 15,6 minūtes**, t.i. pārbaude bija jau deģenerējusies līdz tādai, ko pārstāj palaist. Blakus: vaicājums tagad atgriež 402 balsojumus bez claim no 6 867, un **visi 402 ir izskaidroti** (399 klātbūtne/kvorums pēc Datu kontrakta #4b, 3 aizklāto vēlēšanu čaulas) — nulle neizskaidrotu, partial write nav. Shēmas bāzlīnija pārģenerēta ar `REGEN=1`; diff ir tieši viena rinda.

**2. `daily_brief` topic četras formas → viena, ar apzinātu izņēmumu.** `data/fix_daily_brief_topic_canonical_2026-08-03.sql` + pāra rollback: **70 → 118 kanoniskas no 119**. Mērķa datums katrai rindai no `brief_subject_date()` (topic → H1 → `created_at`), nevis no virknes sagriešanas — id 192 topic bija burtiski `daily`. **Kolīziju pārbaude pirms ģenerēšanas atrada, ka id=131 sadurtos ar id=135** (viens un tas pats 2026-04-14 pārskats, saglabāts divreiz), tāpēc 131 netika migrēts: publicēta pārskata dedublēšana ir operatora redakcionāls lēmums, ne migrācijas blakusefekts. `/audit-integrity` **16. pārbaude** ar bāzlīniju `checked=119 flagged=1`, kur **gaidāmā vērtība ir 1, ne 0**. Motīvs nebija tikai ad-hoc SQL: `src/briefs.py::_BRIEF_DAY_CLAIM_SQL` iebūvē `DAILY_BRIEF_TOPIC_PREFIX || date(...)` NOT EXISTS apakšvaicājumā, tāpēc mantotās rindas tam bija neredzamas.

**3. Citāts #555664 atjaunots — vārti, kas noņēma provenanci, ir aizvērti abos galos.** `data/fix_quote_555664_restore_2026-08-03.sql` + rollback. Citāts avotā (doc 73911) ir burtisks; jaunie `validate_quote_against_source()` vārti to pieņem (`verbatim`), vecie `validate_lv_diacritics` to noraidīja (1/72 = 1,4 % diakritikas). `review_status` pārgāja uz `reviewed` pats — trigeris, ne roka. Rinda **119 → 118**.

**4. Konteksta saite pārskatā #400 nebija klikšķināma.** Operatora ziņojums, apstiprināts pret uzbūvēto lapu. **Sakne, kas ir vispārīga:** konteksta bloks ir RAW HTML (`<div class="context-box">`), un python-markdown raw blokus laiž cauri neapstrādātus — tāpēc kails URL paliek teksts, **un markdown sintakse `[x.com](url)` tur renderētos kā burtisks `[x.com](url)`**, t.i. tā pati klase, kas sintēžu wikilinki. Vienīgā pareizā forma konteksta blokā ir tiešs `<a>` tags. Mērogs pārbaudīts pirms labošanas: **135 pārskati, 1 gadījums** — vienreizējs, tāpēc laboja saturu, ne renderētāju. Pats čekeris vispirms tika validēts pret zināmo gadījumu; pirmā versija ar `<div class="context-box">.*?</div>` atgrieza pārliecinošu 0, jo non-greedy sakritība apstājās pie ligzdotā `context-label` beigu taga.

**5. `@claim-extractor` — platuma pašpārbaude.** Jauna sadaļa: „vai mana `stance` apgalvo VAIRĀK nekā avots?" ar četriem konkrētiem jautājumiem (kvalifikatori, vispārinātie lietvārdi, vēlējums→prasība, jautājums→apgalvojums) un cietu STOP vārdā nosauktām personām. Pamats: 2026-08-02 **3 no 8** dienas pozīcijām bija plašākas par avotu.

**Pieci ieraksti, kas bija jau padarīti** (visi pārbaudīti, ne pieņemti): sintēžu wikilinki (fails salabots `f3c6e10a`, dzīvā lapa tīra, `tests/test_synthesis_no_wikilinks.py` jau sargā klasi); **bezpaplašinājuma saites #184 — premisa NEPATIESA, abas formas dzīvajā atgriež 200 un vienu lapu**, tāpēc publicēta pārskata DB labojums atcelts un `output_check_allowlist.txt` iemesls pārrakstīts uz īsto (čekeris staigā pa uzbūvēto koku, serveris atrisina pats); 11 nulles baitu `.db` failu — repo tādu vairs nav neviena; `ARCHITECTURE.md` trīs neatbilstības — visas trīs jau pareizas, atrasta un salabota tikai ASCII shēmas „9 agents" pret prozas „Eleven"; `wiki/CHANGELOG.md` 2026-07-31 ieraksta trūkums — ieraksts eksistē (šajā failā, kā paskaidro pati galvene).

Blakus: trīs git-izsekoti faili vairs nenorāda uz privāto atmiņu kā detaļu avotu (`wiki/operations/commands.md` — noteikums ierakstīts iekšā; `wiki/project-brief.md` → BACKLOG; `scripts/twitter_pack_pdf.py` → `/social-thread` prasme).

## 2026-08-03 — Divi klusie zudumi aizvērti, viens saucējs izlabots, sakne kļuvusi par atļauju sarakstu

Četri gājieni, kuriem kopīga viena tēma: katrs no tiem klusi zaudēja saturu, un neviens no tiem nekritās.

**1. Junction lomu inversija — mērījums tagad ir atkārtojams, un tā saucējs bija nepareizs.** Jauns `scripts/audit_junction_role_inversion.py` (read-only) + `/audit-integrity` **15. pārbaude**; 13 testi `tests/test_audit_junction_inversion.py`. Karogu skaits atkārto pierakstīto (**280** pret 282, viena diena dreifa), bet **1897 saucējs skaitīja dokumentus, kuru vienīgā `mentioned` entītija ir organizācija** — tie cilvēka-runātāja inversiju nevar saražot nekad. Godīgais saucējs ir **1273**, tātad `checked=1273 flagged=280` = **22,0 %**, ne 14,9 %; klase ir ~1,5× smagāka, nekā pierakstīts. Diskriminators ir gramatisks — nominatīvs pie citēšanas signāla —, un tas ir fiksēts testā tieši, jo naivā „visas formas" versija doc 78085 nepamana.

**2. `claims.quote` vairs neiet caur diakritiku attiecības vārtiem.** CLAUDE.md citātu definē kā VERBATIM un vārtus attiecina uz MŪSU vārdiem, tāpēc attiecības tests uz citāta uzdeva nepareizo jautājumu — un kļūdījās abos virzienos. Aizstāts ar avota salīdzinājumu (`validate_quote_against_source` `src/quality.py`, būvēts uz jau esošā `restore_text_from_source`).

| Mērījums pār 4 735 pārbaudāmām rindām | Rezultāts |
|---|---:|
| citāts sakrīt burtiski | 4 219 |
| sakrīt tikai pēc diakritiku salocīšanas → **noraida** | 20 |
| atšķiras tikai ar lielo burtu → laiž cauri | 45 |
| avotā neatrodas → laiž cauri | 1 408 |

Noraidītā klase ir tā, ko attiecības vārti **strukturāli nevar** redzēt: viens bojāts burts diakritiku bagātā teikumā, turklāt abos virzienos — `ziņu`→`zinu` ir cits vārds, un #313 „izlaboja" runātāja paša rakstību X ierakstā (tas pats noteikums, kas Kulberga „Steidamas"). Pierādījums, ka vecie vārti maksāja provenanci: **#555664 citāts DB šodien ir tukšs** — vārti to nevis atzīmēja, bet izdzēsa. Atkāpšanās uz attiecības vārtiem neverificējamiem citātiem tika **izmērīta un noraidīta**: tā nostrādātu uz 6 rindām no 1 408, no kurām četras jau ir operatora triāžas sarakstā (#6966, #7003, #7018, #7518) un viena (#7512) ir autentiska izloksne, ko tā noraidītu nepamatoti.

**3. Auditorijas balsis iet dienas pārskata tēmu tabulās** (operatora lēmums). 2026-07-31 filtrs izmeta **11 no 50** pozīcijām, tostarp visas četras Valsts kontroles revīzijas atzinumus, un pārskata rakstītājs tās katru dienu pievienoja ar roku. Mainītas TIKAI trīs tēmu-tabulu vaicājumi (`by_topic`, per-tēmas `samples`, `Pārējās tēmas`) plus DIENAS STATS skaitītājs, kam ar tām jāsakrīt. **Apzināti NEmainīts:** Aktīvākie (politiķu rangs), starppartiju naratīva mājiens (partiju bāzēts) un Koalīcija vs Opozīcija (auditoriju apstrādā savā disjunktajā Neitrāli rindā), kā arī nedēļas un Telegram pārskati — citas virsmas. `inactive` paliek izslēgts visur. STATS marķējums paplašināts `org` → `auditorijas`, jo kopsummai tagad tiešām jābūt summai; agrāk žurnālistu rindas nebija ne vienā, ne otrā skaitā. Vārti: `tests/test_brief_audience_voices.py` (5 testi).

**4. `.gitignore` sakne ir atļauju saraksts.** `/*` ignorē visu, tad `!` ielaiž 13 mapes un 15 saknes failus pēc vārda. Jauns fails saknē tagad pēc noklusējuma ir PRIVĀTS, un publiskošana ir apzināta darbība — tieši tā, kā CLAUDE.md standing noteikums to jau apraksta. Agrāk aizsardzība balstījās uz ~24 noteikumiem, kas katrs nosauca vienu konkrētu failu: pārsauc failu vai noliec blakus māsas failu, un aizsardzības nav. Invariants pārbaudīts pirms un pēc: **0 izsekoti faili atbilst kādam ignore noteikumam** (1 864 izsekoti abās pusēs), un zondes apstiprina uzvedību — `secret-notes.docx` saknē ir privāts, `src/_probe_module.py` ir redzams.

**5. `claims.review_status` — pārskatīšanas karogs kļuvis par kolonnu.** Marķieris dzīvoja `reasoning` brīvtekstā un lūza trīs neatkarīgos veidos, no kuriem tikai viens bija par pareizrakstību: forma dreifēja (`REVIEWED` → `Izvērtēts` → `REVIEWED`, katrs dreifs apžilbināja iepriekšējo vaicājumu), novietojums dreifēja (20 no 119 prefiksā, tāpēc enkurotais `LIKE 'NEEDS_REVIEW%'`, ko pati CLAUDE.md 2. eskalācijas noteikuma formulējums ierosina, atgriezās ar 17 % rindas), un neviens nevarēja izmērīt ne skaitu, ne vecumu, tāpēc neviens to nedarīja. Marķiera izvēle būtu salabojusi tikai pirmo no trim.

Kolonna ir **atvasināta, nekad rakstīta ar roku**. Atvasināšana notiek DIVOS trigeros — `AFTER INSERT` un `AFTER UPDATE OF reasoning`. Otrais ir nesošais: triāža atrisina karogu ar `UPDATE claims SET reasoning = REPLACE(...)` ad-hoc SQL, kas caur `store_claim()` neiet nekad, tāpēc kolonna, kas uzturētos tikai rakstīšanas ceļā, būtu pareiza ievietošanas brīdī un nepareiza no pirmās atrisināšanas — tā pati novecošanas kļūda, tikai pārcelta. Šie ir repo pirmie trigeri, un pamats to pieņemt ir CLAUDE.md § „Write through the `store_*()` functions": vārti, kas dzīvo funkcijā, ir viena kaila `INSERT` attālumā no apiešanas. Derivācijas izteiksme ir viena konstante (`_REVIEW_STATUS_EXPR`), ko dala abi trigeri UN backfill, lai tie nevarētu nesakrist.

| Dzīvā DB pēc migrācijas | |
|---|---:|
| `review_status='needs_review'` | 119 |
| `review_status='reviewed'` | 234 |
| nesakritības kolonna↔teksts | **0** |
| atvērtās rindas ≤7 d / 8–14 d / vecākas | 76 / 43 / **0** |

Migrācija ir **tikai aditīva** — backfill raksta jauno kolonnu un neko citu, `reasoning` netiek grozīts, tāpēc pārembedēšana nav vajadzīga (`store_claim` iegulst `f"{topic}: {stance}"`). Tāpēc arī 1,9 GB momentuzņēmums netika ņemts: atjaunojamu datu nav, ir tikai kolonna, ko nomest. Rollback: `data/rollback_claims_review_status_2026-08-03.sql`. Vārti: `tests/test_review_status_column.py` (9 testi, t.sk. kails `INSERT` un atrisināšana ar kailu `UPDATE` — tieši tie ceļi, ko `store_claim`-only derivācija palaistu garām). `/audit-integrity` 4. pārbaude pārlikta uz kolonnu, ar sanity rindu, kas pierāda, ka trigeri joprojām strādā.

**5b. 20 vēsturiski sagrozīti citāti atjaunoti** (operatora apstiprinājums tajā pašā sesijā). `data/fix_quote_diacritic_restore_2026-08-03.sql` + pāra rollback; sausā palaide vispirms notika transakcijā, ko atritināja. Pēc piemērošanas **0 no 4 735 citātiem vairs nekrīt caur jaunajiem vārtiem** (pirms: 20) — tā ir neatkarīga pārbaude caur to pašu funkciju, kas sargā jaunos rakstus, ne skripta paša atskaite.

Sadalījums pēc virziena, jo tas maina, kā izskatās diff: **11 rindās mēs bijām nometuši garumzīmi** (labojums tās atliek atpakaļ), bet **9 rindās mēs bijām PIELIKUSI zīmes, ko runātājs nav rakstījis** — tur labojums atjauno runātāja paša kļūdaino rakstību, jo citāts ir VERBATIM (#532231 → `sistēmātiskiem`, #548451 → `Jūlija`). Divas no tām ir semantiskas, ne kosmētiskas: #1581/#1589 atgriež `zinu`, kur mēs bijām uzrakstījuši `ziņu` — cits vārds, t.i. mēs bijām mainījuši to, ko cilvēks pateica. Vienā rindā (#6) apzināti paturēts mūsu lielais sākumburts, jo vārti fragmenta sākuma lielo burtu jau uzskata par citēšanas konvenciju; citādi labojums ieviestu izmaiņu, ko paši vārti palaistu cauri. **Dzīvajā vietnē vēl ir vecais teksts** — renders + deploy ir atsevišķs solis ar atsevišķu apstiprinājumu.

**6. Pārskatīšanas vārtu kritērijs: ierobežota rinda, ne tukša** (operatora lēmums). `@quality-reviewer` prasīja, lai VISAS `NEEDS_REVIEW` rindas būtu atrisinātas — tas nekad nav bijis patiess (08-03: 119 atvērtas), un nesasniedzami vārti ir tie, ko iemācās nolaist. Jaunais kritērijs: **neviena `review_status='needs_review'` rinda nav vecāka par 14 dienām.** Turklāt paša vārtu vaicājumā bija `date(c.created_at) >= date('now','-7 days')`, tāpēc vecākas rindas pazuda no recenzenta redzesloka, kamēr kritērijs joprojām prasīja „visas" — vārti nevarēja redzēt to, ko paši pieprasīja, un tieši tā uzkrājās 119. Ziņo abus skaitļus (kopā + vecākas par 14 d). Bāzlīnija: 119 atvērtas, **0 vecākas par 14 dienām** — pašlaik iet cauri, ar 43 rindām 8–14 d joslā. Sinhronizēts: `quality-reviewer.md`, `quality-bars.md`, `weekly-routine.md`, `/audit-integrity` 4.

**7. `wiki_lint` vairs nav akls pret satura lapām.** Linku pārbaude staigāja tikai pa četriem indeksa failiem, tāpēc wikilinks IEKŠ ģenerētas personas/partijas/tēmas lapas netika pārbaudīts nekad — t.i. tieši tur, kur `wiki_sync` kļūda nokrīt. Tā bija atlikusī daļa no 08-02 gadījuma: 338 salauztos linkus toreiz salaboja, aklumu ne. Jaunā 6. pārbaude staigā pa visu vault; dzīvais rezultāts **`broken_links` 0 → 6**, kas precīzi sakrīt ar 08-02 pieraksta „341 → 6". Vārti: `tests/test_wiki_lint_content_links.py`.

**Trešo noteikumu pievienoja pati pārbaude, tiklīdz to palaida pār repo:** koda spanos un ```-blokos esošie wikilinki ir dokumentācija, ne saites. Bez tā šis pats CHANGELOG ieraksts — rindkopa, kas paskaidro tabulas ekranēšanas formu — tika saskaitīts kā salauzta saite uz `t`, blakus divām vecākām rindām, kas citē to pašu kļūdu. Skaitlis nokrita no 7 uz **4**, un tie četri ir īsti. Čekeris, kas savu dokumentāciju skaita par bojājumu, māca ignorēt skaitli.

**Divi parsēšanas noteikumi ir daļa no pārbaudes, ne detaļa**, un šī sesija tos vispirms kļūdīja: `[[t\|Label]]` ir tabulai drošā alias forma (ja `\` skaita par mērķa daļu, „salauztas" kļūst visas 194 `persons/personas.md` rindas), un mērķis var būt ne-markdown vault fails (`[[politiki.base]]`). Nepareizi skeni šajā sesijā secīgi uzrādīja 286 un 783 „salauztas" saites; īstais skaitlis ir 6. Tas ir tas pats brīdinājums, kas stāv BACKLOG galvenē — **grep skaitītājs mēdz melot, un skaitlis nav atradums, kamēr neesi izlasījis rindu.**

**8. Nedēļas pārskats 2026-07-27 līdz 2026-08-02 (piezīme #401).** Pirmā nedēļa bez neviena Saeimas balsojuma (vasaras pārtraukums), 233 pozīcijas. Rakstīts iekšēji pēc `@weekly-brief-writer` procedūras, nevis ar apakšaģentu — sesijas modelis nepārsniedz dispatch līmeni, tāpēc deleģēšanai nebija pamata. Divi labojumi pirms glabāšanas, abi noķerti ar pārbaudi, ne ar aci: **(a)** melnrakstā Kulberga Latvijas Bankas noraidījums bija ielikts svētdienā, bet `claims.stated_at` rāda **sestdienu, 1. augustu** (#615821), un svētdiena ir Pūpola pievienošanās (#615826) — datums pārbaudīts DB, pirms teikums palika tekstā; **(b)** `## Vizuālais brief` lauks „Galvenā tēze" kļūst par lapas `<h1>` (`src/briefs.py:1185`), tāpēc gara klauzula ar mazo sākumburtu renderējās kā virsraksts — pārrakstīts uz „Nedēļa bez balsojumiem: valdība pret uzraugošajām iestādēm". Visas daudzrunātāju atribūcijas pārbaudītas pret DB (Kols/Pūpols, Krištopans/Šlesers, Kulbergs/Pūpols), nedēļas dienu nosaukumi pārbaudīti ar `strftime`, `lint_lv_style` tīrs.

**8b. Featured attēls: pirmais mēģinājums noraidīts LV teksta kļūdas dēļ.** Attēls #242 renderēja virsrakstā **„valdīḃa"** — uz burta `b` bija piezīmēta lieka diakritiska zīme. Tas ir tieši tas nanobanana teksta defekts, ko `@graphics-designer` noteikumi apraksta, un tas ir **redzams tikai palielinājumā** — pilnā izmērā attēls izskatījās kārtībā. Noraidīts ar `reject_image` (`approved=2`, iemesls DB), pārģenerēts kā #243; jaunajā visas diakritikas pārbaudītas pa vienai palielinātos izgriezumos (`Nedēļa` ar mīkstinājumu, `valdība` ar tīru `b`, `uzraugošajām iestādēm`). **Mācība procedūrai: brief attēlu nedrīkst apstiprināt, neapskatot virsrakstu palielinājumā** — pilna izmēra apskate šo klasi nenoķer.

Variantus emitēja `make_variants()` atsevišķi, jo `cli brief` tos neraksta (dokumentēts `commands.md` NB); pēc renderēšanas `/audit-integrity` 7. pārbaude: `checked=137 flagged=0`.

**8c. Publicēts** (`deploy.sh --no-delete`, aditīvs; operatora apstiprinājums). Dzīvās pārbaudes pēc gājiena, nevis pieņēmumi: nedēļas lapa, visi četri attēla varianti, `movers` SVG un `sitemap.xml` — visi **HTTP 200**, un jaunā lapa ir dzīvajā sitemap. Tajā pašā gājienā **aizvērās 2026-05-19 un 2026-05-22 pārskatu 404-hero jautājums**, kas bija atvērts kopš maija: abas lapas atbild 200, un `og:image` tagad atrisinās uz `assets/og-image.png` (arī 200), nevis uz neesošu failu. BACKLOG ieraksts noņemts.

Piezīme pašpārbaudei: pirmajā dzīvajā pārbaudē abas maija lapas rādīja 404 — tas bija MANS nepareizs URL minējums (`dienas-parskats-2026-05-19.html`), nevis publicēšanas kļūme; īstie slugi ir `blog/2026-05-19.html`. Pārbaudi slugu pret `output/`, pirms 404 nolasa kā defektu.

**8d. Commit autora identitāte pārslēgta uz GitHub noreply formu** (operatora rīkojums, pēc tam kad pirms-push pārbaude to uzrādīja). Repo-lokāls `user.email`; globālā konfigurācija neaiztikta. Adrese ņemta no publiskā GitHub API (`users/<login>` → `id`), nevis minēta: kanoniskā forma ir `<id>+<login>@users.noreply.github.com`, un mantotā forma bez skaitliskā ID commitus ar profilu nesasaista. Attiecas TIKAI uz turpmākajiem commitiem — esošā vēsture nes veco adresi, un tās pārrakstīšana publiskā repo salauztu katru hash-u, tostarp tos, kas šajā failā citēti kā pierādījums; sk. BACKLOG. Blakus brīdinājums: `.git/config` nav izsekots, tāpēc svaigā klonā iestatījums jāatkārto.

**9. Telegram pārskats izmests pilnībā** (operatora lēmums: „telegram vairs neizmantojam"). Noņemts `generate_telegram_brief()` un tā ekskluzīvie palīgi (`_domain_label`, `_md2`, `_md2_url`, `_MD2_ESCAPE_RE`) — 239 rindas no `src/briefs.py`; dzēsts `scripts/telegram_brief.py` un `wiki/operations/telegram-brief.md`; divi testi un runbook atsauces (`commands.md`, `operacijas.md`) izņemtas.

**NAV noņemts, un tas ir apzināti:** `src/social_agent/telegram.py` (`send_draft`/`parse_reply`), ko lieto `social_agent/cli.py` tvītu draftu apstiprināšanas plūsmā, plus `social_drafts` kolonnas `telegram_msg_id`/`telegram_chat_id`. Tā ir cita funkcija, ne pārskats; tās izmešana salauztu social agent apstiprināšanas ceļu, un lēmums par to netika prasīts. Ja arī tā jāiet, tas ir atsevišķs gājiens ar shēmas migrāciju.

**Blakus: `parity_2025.json` pārģenerēts** ar salaboto 307 sēžu manifestu (2025-05-04 un 2025-11-18 tagad iekšā). Darba kārtībā 2006, DB 1036, **trūkst 970** — tieši tas pats skaitlis, tagad stiprajā formā (trūkst pēc ABIEM testiem: URL nezināms UN (datums, laiks) nav DB). No 970 **138 ir klātbūtnes/kvoruma ieraksti**, kas claims neģenerē nekad (#4b), tāpēc **īstais balsojumu robs ir 832**, ne 970. Jauns atradums: `jautajumi` sēdes rīks izlaiž pēc pieņēmuma „bez balsojumiem", bet **2025-10-30 ir tāda sēde, un DB tur ir 2 balsojumi** — pieņēmums nepatiess vismaz vienreiz, un tās dienas darba kārtība netiek auditēta nekad. Sk. BACKLOG § Saeima.

## 2026-08-02 — Nakts II: 4 087 dublikāti izdzēsti; Datu kontrakts #4b atkal tur

**Tīrīšana piemērota (operatora apstiprinājums tajā pašā vakarā).** `data/fix_dup_saeima_vote_claims_2026-08-02.sql` + pāra rollback + `.ids` fails vektoru pārrēķinam; momentuzņēmums `data/atmina.db.pre-dup-cleanup-20260802.db` pirms pirmās rindas. Dzēstas **4 087 rindas no 4 082 grupām** (4 077 pa divām, 5 pa trim); katrā grupā paturēta jaunākā, un visas 4 082 paturamās izrādījās 2026-05-27 vilnis — tas, kas nes bagātāku `Atbalsta: <summary>` tekstu.

| Mērs | Pirms | Pēc |
|---|---:|---:|
| `/audit-integrity` 14: flagged | 49 | **0** |
| 14: liekās rindas | 4 087 | **0** |
| 11: delta | 4 087 | **0** |
| `saeima_vote` kopā | 572 811 | **568 724** |
| claims bez vektora | 546 | **170** |
| `claim_vectors` | 584 675 | **580 964** |
| karājošās pretrunu atsauces | 0 | **0** |

**Priekšpārbaude atrada bloķētāju, ko neviens ieraksts nebija paredzējis, un tas ir šī gājiena galvenais ieguvums.** **7 no 30 pretrunām** (23 % no visas tabulas) atsaucās uz dzēšamajām rindām, un **visas septiņas ir `confirmed=1 reviewed=1`, t.i. publicētas**. Akla dzēšana būtu radījusi karājošās atsauces tieši publicētajā saturā — tā pati klase, ko `/audit-integrity` pati meklē. Forward tās pārvirza uz palikušo dvīni PIRMS dzēšanas; pārvirzīšana ir semantiski tukša, jo katrā gadījumā `opponent_id`, `topic`, `claim_type`, `stance` un `stated_at` ir identiski, un pēc tās neviena pretruna nepaliek ar `claim_old_id == claim_new_id`. Ja plāns būtu izpildīts tā, kā BACKLOG to aprakstīja („dzēst māsas vienā transakcijā"), šis būtu palicis nepamanīts.

**Otra pieņēmuma korekcija, ko deva tā pati priekšpārbaude:** dzēšamās rindas NAV tikai aprīļa — 167 no tām ir 2026-05-26. Vienīgais formulējums, kas tur, ir „paturi 05-27 rindu", un skripts to pārbauda cieti, nevis pieņem.

**Rollback atjauno rindas, nevis vektorus — apzināti.** Hex embedding uzpūstu failu no 2,72 MB uz ~15 MB publiskajā spogulī, un, kas svarīgāk, daļai dzēsto rindu glabātais vektors NEATBILDA to `topic` kolonnai (aprīļa rindas kodēja `Valsts pārvalde`, kamēr kolonna jau bija `Budžets un finanses`), tāpēc bitu precīza atjaunošana atjaunotu defektu. Vektorus pārrēķina `scripts/reembed_claims.py`; 3 711 no 4 087 rindām vektors bija, 376 nebija, un novirze ir nosaukta rollback galvenē.

**`scripts/reembed_claims.py --ids-from`** pievienots, jo rollback galvene to prasīja un tāda karoga nebija: 4 087 pozicionāli id ir ~28 tūkst. rakstzīmju komandrindā pret ~32 tūkst. Windows limitu, t.i. dokumentētā atkopšanās procedūra būtu bijusi nepalaižama. Vārti: `tests/test_reembed_claims.py` (9 testi, t.sk. bulk apjoma round-trip un tas, ka bez id skripts krīt, nevis klusi palaiž tukšu pārrēķinu).

**Bāzlīnijas pārrēķinātas:** `/audit-integrity` 11. un 14. pārbaudei gaidāmā vērtība tagad ir **0** — jebkurš ne-nulle ir jauns bojājums, ne zināmais backlogs. `wiki/index.md` pārģenerēts ar `wiki_sync()` (568 724; hand-edit tur būtu klusi pazudis nākamajā sync).

**Noteikums pārcelts uz CLAUDE.md 8. eskalācijas punktu**, lai tas nepazustu līdz ar ierakstu: `topic` ir idempotences atslēgas daļa, tāpēc `UPDATE claims SET topic` var RAŽOT dublikātus — pirms migrācijas jāpalaiž sadursmes vaicājums, un dedup lēmums pieder tam pašam skriptam. Bulk ielādēm: idempotence nav stabila pār koda izmaiņām, drošība nāk no ielādētāja `(vote_date, vote_time)` pārbaudes.

**Abas paliekas aizvērtas tajā pašā vakarā.**

`stated_at` ISO normalizācija (`data/fix_stated_at_iso_2026-08-02.sql` + pāra rollback): **1 540 → 0** punktētas rindas pār 19 balsojumu URL (pirms dublikātu tīrīšanas to bija 5 329). Kanoniskā vērtība NAV pārformatēta virkne, bet nolasīta no `saeima_votes` (`vote_date` + `vote_time`) pa `source_url` — tieši to raksta `_parse_vote_datetime()` šodienas kodā; ģenerators krīt, ja atvasinātā datuma daļa nesakrīt ar punktētās vērtības datumu (pārbaudīts: 0 neatbilstību, 38 unikāli no→uz pāri). Vektori šeit apzināti NETIEK pārrēķināti: `stated_at` nav idempotences atslēgas daļa un netiek iegults.

Vektoru pārrēķins atlikušajām 170 rindām (`scripts/reembed_claims.py --ids-from` — pirmais īstais šā karoga lietojums): **claims bez vektora 170 → 0, un tas ir 0 visos `claim_type`, ne tikai balsojumos.** Pirms rīkošanās pārbaudīta apgalvotā pārklāšanās starp „170 bez vektora" un „170 punktētās no 04-05 viļņa" — kopas izrādījās identiskas, bet tas bija jāizmēra, ne jāpieņem.

**Gala stāvoklis:** 14. pārbaude `0/0`, 11. pārbaude delta `0`, punktētais `stated_at` `0`, claims bez vektora `0`, karājošās pretrunu atsauces `0`. Atvērts paliek tikai pretējais virziens — **7 004 bāreņu vektori**, un tas skaitlis ar tīrīšanu pareizi nemainījās, jo dzēstajām rindām vektori tika dzēsti tajā pašā transakcijā.

## 2026-08-02 — Nakts: „neizskaidrotā" idempotences izspruksme neeksistēja; 4 087 dublikāti ir viena klase

**Atsaukts BACKLOG ieraksts, kas stāvēja priekšā 140 tūkst. rindu ielādei.** Tas apgalvoja trīs lietas: ka 91 no 4 082 dublēto `saeima_vote` grupu radās, `store_claim()` SELECT→INSERT ielaižot otru rindu jau esošam `(opponent_id, source_url, topic)` trijniekam; ka tas ir Datu kontrakta #3 pārkāpums pa parasto rakstīšanas ceļu; un ka mehānisms nav zināms, tāpēc „izmeklēt PIRMS bulk ielādes, ne pēc". Neviena no trim neizturēja pārbaudi.

**Bāzes mērījuma atkārtojums bija tīrs** — 4 082 grupas, 4 087 liekās rindas, 3 991 izskaidrota ar 06-13 migrāciju, 91 kandidāts; precīzi tie paši skaitļi pār 572 811 `saeima_vote` rindām. Pirmais jaunais fakts nāca no kandidātu anatomijas: **visas 91 grupas ir uz VIENA balsojuma** (`saeima_votes.id=48`, Grozījumi Kredītiestāžu likumā 1165/Lp14, 2. lasījums, 2026-03-26), un visiem 91 tā balsojuma deputātiem ir tieši divas rindas — viena aprīļa, viena maija. Nevienam nav ne vienas, ne trīs. Izkaisītas izspruksmes pa ielādi, kādu ieraksts aprakstīja, tur nav.

**Metode nevarēja redzēt atbildi.** Ieraksts balstījās uz to, ka 06-13 pāra rollback fails glabā katras skartās rindas pirms-migrācijas tēmu. Bet `data/` mapē ir vismaz piecas tēmu mutējošas migrācijas, un `fix_motif_topic_coverage_2026-06-12.sql` — diennakti agrāka un balsojumu **ID** līmenī — per-rindas pirms-vērtības nesaglabā vispār. Balsojums 48 ir tās sarakstā (mērķa tēma `Budžets un finanses`, bloks ar 253 balsojumu ID). Grupa, ko sapludināja 06-12, 06-13 metodei izskatās tieši tā, it kā migrācija nebūtu skārusi nevienu rindu.

**Viens instruments veda nepareizā virzienā, un tas ir pierakstāms.** Pirmais mēģinājums bija vektortests: `store_claim` iegulst `f"{topic}: {stance}"`, tēmu migrācijas vektorus nepārrēķināja, tātad glabātais vektors nosauc tēmu ievietošanas brīdī. Sešiem pāriem (12 rindas) abas puses baitu līmenī sakrita ar `Valsts pārvalde`, un no tā izskatījās, ka maijā trijnieki bijuši identiski, t.i. ieraksts apstiprinās. **Tas bija nepareizs slēdziens no pareiza mērījuma:** vektors nosauc tēmu RAKSTĪŠANAS brīdī, bet dedup `SELECT` salīdzina pret kolonnas TĀBRĪŽA vērtību. Aprīļa rindām tās atšķīrās, jo kāda agrāka tēmas maiņa vektoru nepārrēķināja — pats par sevi jau pierakstītais `claim_vectors` novecošanas defekts.

**Izšķīra momentuzņēmums.** `atmina.db.pre-vote-url-fix-20260427` stāv tieši starp abām ielādēm. Tajā balsojuma 48 aprīļa 91 rindai `topic` ir **`Budžets un finanses`**, kamēr `saeima_votes.topic` tolaik ir `Valsts pārvalde` — un tieši ar `Valsts pārvalde` 05-27 ielāde savas rindas arī uzrakstīja. **Trijnieki rakstīšanas brīdī atšķīrās, tāpēc dedup SELECT pareizi neatrada neko**, un 06-12 migrācija tos pēc tam saveda kopā. `source_url` tajā pašā momentuzņēmumā ir baits pret baitu identisks dzīvajam (0 no 91 rindas mainīta), tāpēc arī URL versija krīt.

**Secinājums: `store_claim()` netika apiets, Datu kontrakts #3 nav pārkāpts, un pirms bulk ielādes nav ko labot.** Visas 4 087 liekās rindas ir viena klase — ar roku palaists `UPDATE claims SET topic`, kas sapludina trijniekus, ko rakstīšanas ceļš nekad nebūtu pieņēmis; 3 991 pa 06-13, 91 pa 06-12. Arī pārējās trīs ieraksta nosauktās hipotēzes ir slēgtas: `db=` zars neiesaistās (balsojumu ceļš padod `db_path=`, `src/saeima/votes.py:607`, tāpēc katrs claim atver savu savienojumu un commit-o), Kļaviņa reatribūcija skar vienu politiķi, ne 91, un paralēlu rakstītāju versija nav vajadzīga, jo neizskaidrotas neatbilstības nav palikušas.

**Blakusatradums, kas ir svarīgāks par pašu ierakstu.** 05-27 P3 palaidiens nepārrakstīja tikai balsojumu 48: **46 no 64 aprīļa balsojumu URL** saņēma pilnu otro claims komplektu, 39 no tiem tieši ×2,0 pret nodotajiem biļeteniem. Fiziskā dublēšanās ir viens notikums; tēmu atšķirības tikai izšķīra, cik no tā idempotences atslēga vispār spēj ieraudzīt, un jūnija migrācijas pārējo padarīja redzamu. No tā izriet noteikums gaidāmajām ~140 tūkst. rindām: **idempotence nav stabila pār koda izmaiņām**, jo `topic` ir vienlaikus atslēgas daļa un `_motif_to_topic()` atvasinājums, kas laika gaitā mainās. Drošība nāk no `(vote_date, vote_time)` pārbaudes `scripts/ingest_saeima_missing_votes.py` ceļā, ne no `store_claim`; un pār ielādes tvērumā esošiem balsojumiem nedrīkst palaist tēmu migrāciju.

**`/audit-integrity` 14. pārbaude — claims PA BALSOJUMAM pret nodotajiem biļeteniem.** 11. pārbaude mēra atslēgas sadursmes, ne rindu dublēšanos, tāpēc tā ir akla tieši tajā brīdī, kad kaitējums notiek: maijā tās delta būtu bijusi ~0, un tā iedegās tikai pēc jūnija migrācijām. Šā faila 08-02 pēcpusdienas ieraksts apgalvoja, ka 11. pārbaude „būtu noķērusi maija dublikātus tajā pašā mēnesī" — **tas ir nepareizi un ar šo labots.** To dara 14. pārbaude: `checked=6465 flagged=49`, liekās rindas **4 087** (100 % no 11. pārbaudes deltas), trūkstošās **0**, 1,1 s pār visu tabulu. Nulle trūkstošo ir atsevišķi vērtīga — tā ir vienīgā rinda, kas visā tabulā attaisno `store_vote()` no daļējas rakstīšanas. Abas puses jāagregē pirms savienošanas: `claims.source_url` nav indeksa, tāpēc korelēta apakšvaicājuma forma vilktos.

**Mācība par pašu auditēšanu.** Metode, kas lasa vienu migrācijas failu, var pārliecinoši nosaukt „neizskaidrotu atlikumu" tur, kur atlikums ir tikai tas, ko fails neapraksta. Un pretējā virzienā: pareizs baitu līmeņa mērījums ved pie nepareiza secinājuma, ja tas mēra citu laika momentu, nekā prasa jautājums. Abas reizes glāba `data/` momentuzņēmumu mape, ko cits BACKLOG ieraksts tajā pašā dienā sauc par 10,6 GB novecojušu balastu — retention noteikums tāpēc jāraksta tā, lai pirms-migrācijas kopijas paliktu, kamēr attiecīgā migrācija ir atvērta.

## 2026-08-02 — Vakars: „kam ir darbs" bija trīs kopijas, 08-02 rutīna, un pozīcija, kas bija plašāka par avotu

**Ekstrakcijas tvērums nolikts vienā vietā (`src/scope.py`).** Tās pašas dienas `83033c02` izņēma 11 relay kontus no rindas (`src/analyze.py`), bet ne no rutīnas statusa denominatora (`src/routine.py:358`) un ne no publicētā backlog skaitļa (`src/wiki.py`) — predikāts bija uzrakstīts ar roku trīs reizes. Nekas nekrita; rinda vienkārši kļuva mazāka par abiem skaitļiem, kas to apraksta. Izmērītais kaitējums: relay entītijai ir `role='subject'` doks **26 no jebkurām 30 dienām**, tāpēc 2. solis praktiski nekad vairs nevarēja kļūt zaļš; un `wiki/index.md` publicēja „Nepārskatīts backlog: **577**", kamēr rindas semantikā tas ir **232** — 345 no 577 (60 %) bija dokumenti, ko neviens ekstraktors nesaņems (58 inactive, 287 relay). Tā ir OTRĀ viltus-steidzamības sajaukšana tajā pašā metrikā; `src/wiki.py` komentārs pieraksta pirmo (2026-04-10). Forma pēc `src/coalition` parauga (inv #10): viens jēdziens, viens īpašnieks. Vārti: `tests/test_extraction_scope.py` (11 testi), nesošais ir `test_both_entry_points_answer_the_same_question` — tas būtu kritis tajā pašā dienā. Tvēruma robeža nostiprināta ABOS virzienos: render virsmas (`politicians.py` X apakštabs, `x.py`) rāda politiķa PAŠA ierakstus, tur relay plūsma ir leģitīma, un predikāts tur nedrīkst nonākt. Veiktspēja: scoped vaicājums ir ĀTRĀKS (78,7 ms pret 87,8 ms).

**Rutīna 2.–10. solis izpildīta.** 26 politiķi / 51 doku slots caur paralēliem `@claim-extractor` (divi viļņi pa 13), **7 jaunas pozīcijas** (#615822–615828), 0 pretrunas, 0 jaunu spriedžu, 1 tendence (#399), pārskats #400 publicēts ar attēlu. Skaitļu saskaņa pārbaudīta pret bāzlīniju, ne pret aģentu ziņojumiem: `NEEDS_REVIEW` 114 → 119 (+5 = tieši tik, cik aģenti ziņoja), 7 nepārskatīti 08-02 doki = tieši Lapsas apzināti atstātie.

**Pozīcija #615827 bija PLAŠĀKA par avotu — un tas ir šīs dienas svarīgākais atradums.** Doc 78816 Štāls saka: „nav bijusi neviena **KNAB izmeklēta** augsta līmeņa politiskās korupcijas lieta … ar galīgu notiesājošu spriedumu **pret galvenajiem shēmas organizētājiem**". Mēs saglabājām un gatavojāmies publicēt bez ABĀM atrunām — kategoriskāks, vieglāk atspēkojams apgalvojums, ko liekam runātājam mutē, pastiprinot kritiku par vārdā nosauktu personu. Tā ir tā pati klase, kas 2026-07-25 diskreditēja publicēto ierakstu. `@quality-reviewer` to noķēra un bloķēja publicēšanu. Kad tam pašam aģentam tika prasīts pārbaudīt, vai gadījums ir vienreizējs, atbilde bija: **pēc smaguma jā, pēc paņēmiena nē** — vēl divas no 8 pozīcijām nesa to pašu sašaurinošo atrunu noņemšanu (#615828 „diskotēkām"→„pasākumiem"; #615824 nosacījuma vēlējums „būtu, ja"→„aicina"). Visas trīs labotas ar pāra rollback un vektoru pārrēķinu.

**Jauns rīks: `scripts/reembed_claims.py`.** Eskalācijas 8. noteikums prasa vektoru pārrēķinu pie katras `topic`/`stance` mutācijas, bet palaižama rīka tam nebija, un vismaz divas vēsturiskas migrācijas (~9 000 rindu) aizgāja bez tā. Izdrukā denominatoru un vai vektors tiešām mainījās.

**Latvijas Banka iesēta (id=243, `organization`, operatora lēmums).** Bez slota iestādes nostāja nebija pierakstāma nekur: doc 78573 palika `reviewed_at IS NULL` un nevienā rindā, spriedzi nevarēja reģistrēt (`store_tension()` prasa abus ID). `name_forms` = 3 formas, jo substring jau sedz „Bankas"/„Bankai"; atsevišķi vajag tikai „Bankā" un „Banku". Doc 78573 sasaistīts ar roku — `match_politicians` to atgriež TUKŠU, un tas ir pareizi: tvīts ir pašas bankas ieraksts, tāpēc tekstā tā sevi nesauc vārdā; autorību pierāda `source_url`, un tieši pēc tā `social.py` `first_party` zars pats piešķir `subject`.

**@quality-reviewer F pārbaude bija salauzta pēc konstrukcijas** — lasīja `wiki/log.md` (neeksistē, nekad nav eksistējis) ar kailu `if exists():` bez `else`, tāpēc mēnešiem ziņoja OK, apskatot 0 lietu. Aizstāta ar lint STALE skaitu ar nosauktu denominatoru.

**Divas mācības par pašu procesu.** (1) `source_url` NAV unikāla atslēga uz pārskata rindu — #615824 un #615825 nāk no VIENA tvīta, tāpēc mans sinhronizācijas skripts to pašu rindu paņēma divreiz; idempotences trijnieks nav velti trīsdaļīgs. (2) Apgalvojums par konveijera stāvokli publicētā tekstā noveco tikpat klusi kā skaitlis: „Latvijas Banka nav izsekota entītija" bija patiess 18:56 un nepatiess 19:58, kad mēs to iesējām — un tas jau bija publicēts.

**Citāts bija 1/3 no pavediena, un tas netika pateikts.** doc 78573 saturs sākas ar „1/3"; tvīti 2/3 un 3/3 nekad nav ievākti, un `BACKLOG.md` to fiksēja ar tiešu brīdinājumu — „Jāsavāc, pirms kāds apmaiņu apraksta kā 'abas puses pierakstītas'". Pārskats tieši to darīja: citātu pasniedza kā „Latvijas Bankas pašas nostāja" un aprakstīja apmaiņu pilnībā. Pievienota atruna „(pavediena pirmais tvīts no trim; pārējie divi mūsu korpusā nav nonākuši)"; **citāts pats palika verbatim** (`data/fix_note399_brief400_lb_framing_2026-08-02.sql` + pāra rollback, `wiki/dailies/2026-08-02.md` pārrakstīts no #400 tajā pašā gājienā).

**Un mācība par pašu recenzentu: korpuss nevar apliecināt, ka korpuss ir pilnīgs.** `@quality-reviewer` sākotnēji ziņoja „selektīvas citēšanas nav", jo meklējums pār `documents` atrada tikai vienu LB dokumentu. Tas bija nepareizs slēdziens no pareiza mērījuma — **trūkstošos tvītus pēc definīcijas nevar atrast tajā, kurā to nav.** Pilnīguma atbilde bija `BACKLOG.md`, ne `documents`. Kad pārbaude ir „vai kaut kā trūkst", DB negatīvs nav pierādījums; jālasa tas, kas fiksē zināmās nepilnības. Tā ir tā pati saucēja klase kā salauztā F pārbaude, tikai apgrieztā virzienā: tur vārti skatījās 0 lietas, šeit vārti skatījās pilnu tabulu un tāpēc izskatījās pārliecinoši.

## 2026-08-02 — Operators var rakstīt TIEŠI apakšaģentam, un orkestrators to neredz

> Pārcelts no BACKLOG 2026-08-05.

`@quality-reviewer` tika izsaukts ar promptu „tikai lasīšana" un pēc tam veica DB mutācijas, palaida `deploy.sh` un pušoja. Orkestrators to nolasīja kā instrukciju pārkāpumu un pierakstīja repo kā tādu — **un tas bija nepareizi.** Operators visu laiku sarakstījās TIEŠI ar apakšaģentu („vari commit un deploy", „neuztaisīji deploy? droši taisi"); ziņas vienkārši negāja caur galveno sesiju. Aģents rīkojās pareizi — operatora tiešs vārds ir noteicošs pār orkestratora dispatch promptu — un to arī godīgi nosauca savā atskaitē. **Publicēšanas pauze NAV pārkāpta:** operators atļauju deva, tikai citā kanālā.

**Īstā mācība ir par orkestratoru.** Galvenā sesija NEREDZ operatora saraksti ar apakšaģentiem, tāpēc tās priekšstats par notikušo var būt nepilnīgs — un tā var pierakstīt repo apgalvojumus par ziņām, kuru nav bijis. Tā ir tā pati novecošanas klase, kas šajā projektā jau pierakstīta ar skaitļiem; šoreiz novecoja orkestratora modelis par to, kas ir teikts. Doktrīnas kodols ierakstīts `BACKLOG.md` § Ne-darīt; `f0853761` formulējums „aģents nedeployo NEKAD, arī pilnīgi pārliecināts" atsaukts, jo liktu aģentam atteikt ĪSTU operatora rīkojumu — salabots `.claude/agents/quality-reviewer.md`.

## 2026-08-02 — Pēcpusdiena: LETA ārā no rindas, T4 teksts salabots, trīs jaunas integritātes pārbaudes

**LETA un 10 pārējie relay konti vairs nenonāk ekstrakcijas rindā.** `get_pending_politicians` izslēdz entītijas, kas ir `relationship_type='organization'` **UN** nes `feed_type='relay'` sociālo kontu. Izmērīts: 11 entītijas, 2267 `role='subject'` doki, **0 claims mūžā jebkurā `claim_type`**; LETA vien bija rindas augšgalā katrā logā (310 doki pie `days=30`) un iztērēja 141 `analyses` skrējienu uz garantēti tukša satura. Šaurais UN ir nesošs — filtrs pēc `organization` vien nogrieztu LDDK (32 claims), NBS (18), LVM (9) un Valsts kontroli (4), t.i. tieši tās iestādes, kuru pozīciju dēļ tās iesētas, un kuras `briefs.py` audience filtrs jau izmet no tēmu tabulām; visas četras ir `first_party`, tāpēc paliek. Apzināti NAV spoguļots `get_politician_documents()` — tas ņem tiešu pid un paliek kā izeja relay slota apskatei. Pieci testi, t.sk. tas, ka relay plūsma uz sekotas PERSONAS neieslaucās tajā pašā klauzulā.

**T4 nodiakritizētais teksts, 18 rindas, trīs klases.** `reasoning` 13 → 0 (mūsu teksts, publiskā virsmā nenonāk, netiek iegults; viena rinda bija angliska un pārrakstīta latviski). `quote` 3 atjaunoti VERBATIM no avota dokumenta — vērtības izvilktas ar diakritiku salocīšanu abās pusēs un paplašinātas līdz teikuma robežai, nevis rakstītas ar roku; ja avotā neatrod, rinda tiek izlaista, ne uzminēta. `stance` 2 laboti ar vektoru pārrēķinu, kas pēc tam baitu līmenī salīdzināts ar `embed_text(f"{topic}: {stance}")`.

**Un ar to atklājās klase, kas agrāk nav mērīta: diakritiku vārti ir ATTIECĪBAS tests.** Teikums, kurā bojāts viens vārds, tos iziet, jo pārējais teksts ir ar diakritiku. #6878 un #6880 `stance` publiski rādīja „Progresīvie (**Shuvajevs ka frakcijas vaditats**)" — transliterācija (š→sh), ne garumzīmju trūkums. Mērķtiecīgs zonds pār 87 sekoto personu uzvārdiem ar diakritiku: `stance` 2, `reasoning` 24, `quote` 3. Pirmais mēģinājums deva 182 „trāpījumus" `stance` laukā — **visi artefakts**, jo „Kas Notiek Latvijā" ir sekota entītija un tāpēc katrs pareizais nominatīvs „Latvija" izskatījās nodiakritizēts. Skaitlis nav atradums, kamēr nav izlasīta rinda.

Neaiztikts: #1595 („Ir balts gulbis…") — avota dokumentā teksts ir tieši tāds, tātad zemā diakritika ir runātāja, ne mūsu; dokumentēts vārtu viltus pozitīvs. Paliek 4 citāti (#6966, #7003, #7018, #7518), kas avotā neatrodas pat pēc salocīšanas — tur jautājums ir noņemt vai pāratraktēt, ne labot diakritiku.

**#615821** — `NEEDS_REVIEW` aizstāts ar `Izvērtēts 2026-08-02:` (dokumentētā konvencija, ne pamestā `REVIEWED`). Latvijas Bankas vadlīnijas atrastas un izlasītas: „Nelabvēlīgs"/„Labvēlīgs" tur tiešām ir, pa 25 reizēm katrs kā klasifikācijas kolonnu virsraksti 3.–26. lpp., bet klasificē **saimniecisko darbību, ne klientu** — savienojums ar „klients" dokumentā 0 reižu jebkurā locījumā. `stance`/`quote` neaiztikti.

**brief_images #93 un #96 pazemināti** uz `approved=2` ar iemeslu. Abu pārskatu (2026-05-19, 2026-05-22) hero un `og:image` rādīja uz failiem, kuru nav nekur, tāpēc katrs share deva tukšu kartīti. Šabloni abas virsmas sargā ar `post.image_filename`, un `--only=blog` renders to apstiprina: 0 atsauces uz trūkstošajiem failiem, `og:image` atkāpjas uz `assets/og-image.png`. Dzīvajā vietnē mainīsies tikai pēc deploy.

**`/audit-integrity` papildināts ar trim pārbaudēm, kas pārvērš vienreizējus mērījumus par pastāvīgiem.** (11) Datu kontrakta #4b vienādība — `COUNT(*)` pret `COUNT(DISTINCT opponent_id, source_url, topic)` `saeima_vote` rindām; viena rinda, bez sliekšņa, bāzlīnija 572 811 / delta 4 087, un tā būtu noķērusi maija dublikātus tajā pašā mēnesī. (12) `mentioned` runātājs, kas nekad nenonāk ekstrakcijas rindā, ar **nominatīva formu prasību** (naivā „visas formas" versija etalona doc 78085 nepamana) un bāzlīniju 282/1897. (13) `claim_vectors` novecošana — `embed_text` ir determinēts, tāpēc baitu salīdzinājums ir tīrs pass/fail; kandidātu kopa ir zināma un ierobežota (~4,4 tūkst. rindu aiztiktas ar kailu SQL). Izvades sadaļā ierakstīts, ka katra rinda nes savu saucēju.

Visi labojumi ar pāra rollback, uzrakstītu pirms mutācijas: `data/rollback_t4_diacritics_2026-08-02.sql`, `data/rollback_claim615821_reasoning_2026-08-02.sql`, `data/rollback_brief_images_93_96_2026-08-02.sql`.

## 2026-08-02 — BACKLOG verifikācijas sweep: 6 no 10 ierakstiem nesa nepareizus skaitļus; četri klusi defekti salaboti

Desmit BACKLOG ierakstu pārbaude pret dzīvo repo un DB, pirms kāds pēc tiem rīkojas — tieši tā, kā prasa paša faila galvene. **Seši no desmit nesa nepareizus skaitļus, un četros gadījumos kļūda vērsa nākamo sesiju uz nepareizu darbu.** Pilnas korekcijas ir pašos ierakstos; šeit kopsavilkums.

**Nogriezto avotu ieraksts bija nepatiess visā tā darbīgajā daļā.** Tas divas dienas pēc kārtas (07-30, 07-31) lika atkārtoti ievākt doc 77556. Atkārtojot `ingest_url.py::_default_fetch` ceļu pret dzīvo lapu, rezultāts ir **baits pret baitu identisks** glabātajam: nra.lv lapa ir VIDEO anonss, ministra atbilde ir video, ne tekstā. Abi Delfi doki ir paywall un jau pieder pieņemtajai klasei. **Un pati piedāvātā komanda ir no-op** — `ingest_one()` beidz darbu ar `already_present`, pirms vispār kaut ko fetčo, tātad būtu atgriezusi „success", neko neizmainījusi, un izskatījusies pēc padarīta darba. Ieraksts slēgts un pārcelts uz BACKLOG § Ne-darīt, jo divas sesijas to jau mēģināja.

Divas faktu kļūdas pašā ierakstā, kas laboti līdzi: claim #555829 runātājs ir **pulkvedis Māris Tūtins**, nevis Slaidiņš (`tracked_politicians` ar formu „Slaidiņ" nav neviena), un doc 76623 garums ir **1401** rakstzīme, ne 1314 — starpība ir tīrs reklāmbloķētāja teksts, bez redakcionāla ieguvuma.

**T4 diakritiku atlikums: 89 → 20.** „82 `reasoning` + 7 `quote`" nebija rindu skaits, bet vārtu pirms/pēc **delta** (`reasoning` 178 → 260), no kuras 70 bija apzināti izņemtā `saeima_vote` klase. Patiesais skaits ir 12 + 8, un tas ir stabils pret sliekšņu maiņu. Līdzīgi: brief attēlu pārbaude karo **2, ne 5** (55/73/197 faili eksistē, tiem tikai cits ceļa prefikss); partiju „Biedri" saraksti novecojuši **10 no 18, ne 12**; `saeima_vote` kopskaits ir 572 811, ne 512 918 (delta 4 087 nemainīga, tātad 08-01 ielāde dublikātus nepievienoja).

**546 claims bez vektora nav tā klase, par ko ieraksts brīdināja.** Tie ir **100 % `saeima_vote`**, vienmērīgi `salience=0.3`, **nulle `position` rindu** — viens neizdevies embed batch 2026-04-05 14:49:43, un 376 no tiem ir dublikātu māsas, tāpēc reālais meklēšanas zudums ir 170 procedurālas rindas. Blakus atrisinājās šķietama pretruna starp 07-30 un 08-01 mērījumiem: `bāreņi = kopskaitu starpība + bez_vektora` (7004 = 6458 + 546) — abi bija pareizi, atšķīrās tikai metode.

**LETA ieraksts bija par zemu novērtēts, un tā „vienkāršākais" fikss ir nepareizs.** Nevis 8 doki vienā dienā, bet **2106 `subject` doki, raža 0 mūžā, 141 iztērēts `analyses` skrējiens**. Bet izslēgt pēc `relationship_type='organization'` nogrieztu Valsts kontroli, LDDK un NBS — tās pašas balsis, ko `briefs.py` audience filtrs jau izmet. Pareizā šaurā atlase ir `organization` UN `feed_type='relay'` vienlaikus.

**Junction lomu inversija beidzot ir izmērīta**, kā ieraksts pats prasīja: **282 no 1897 web dokiem 90 dienās (14,9 %), 271 īsts zudums, ~1,4 dienā.** LETA apakšapgalvojums atspēkots — LETA doki ir retāk skarti (10,9 % pret 17,9 %), tātad tā ir vispārīga latviešu ziņu uzbūve, ne LETA pārstāstu artefakts.

### Četri klusi defekti, kas salaboti tajā pašā gājienā

**1. `wiki_sync` pats rakstīja 338 salauztus wikilinkus.** `_render_person_synthesis` trīs vietās emitēja kailu `[[Valsts pārvalde]]` formu, kas neatrisinās ne uz vienu failu — lapas dzīvo `topics/<slug>.md`, un `_slugify` noņem diakritiku un atstarpes. Tajā pašā laikā `wiki/index.md` publicēja „0 broken links", jo linku pārbaude staigā tikai pa četriem indeksa failiem. Neatkarīgs skens pār visu vault: **341 → 6**. No atlikušajiem sešiem trīs ir vienas inaktīva politiķa lapas paliekas (`wiki_sync` inaktīvos neģenerē, tāpēc vecais saturs paliek), viens ir partijas „Biedri" saraksta novecojums, viens ar roku rakstīts salauzts links (salabots), un viens ir skenera viltus pozitīvs.

**2. `wiki_lint` divas no piecām pārbaudēm nevarēja nostrādāt** — tās lasīja `claims_count` un `topics`, atslēgas, ko `wiki_sync` nekad nav rakstījis (īstās ir `positions` un `top_topics`). **Un to testi rakstīja fixtures ar tām pašām izdomātajām atslēgām**, tāpēc komplekts bija zaļš, kamēr neviena pārbaude nevarēja nostrādāt uz īstas lapas. Abas atdzīvinātas; `lint_wiki_with_db` vaicājums vienlaikus jāfiltrē uz `claim_type='position'`, citādi 193 lapas uzreiz karotu kā stale. Pievienots kontrakta tests, kas apgalvo, ka lints lasa tieši tās atslēgas, ko rakstītājs emitē — pārsaukšana `wiki.py` tagad lauž testu, nevis klusi izslēdz pārbaudi. `index.md` lint rinda tagad rāda arī `stale` un `izolētas tēmas`.

**3. `insert_chunks` pievienoja, nevis aizstāja.** `insert_document` URL-first zars atgriež ESOŠO doc id, kad atkārtota skrāpe atnes izmainītu korpusu, tāpēc katra atkārtota ievākšana uzlika vēl vienu pilnu chunku komplektu. Rezultāts: **586 dokumenti ar dublētu `(document_id, chunk_index)`, 690 liekas rindas**, katrai dzīvs vektors — dokumentu meklēšana ranžēja un atgrieza tekstu, kura rakstā vairs nav. Tagad dzēš pirms rakstīšanas, un vektorus **pirms** chunkiem, jo `document_vectors` ir vec0 virtuālā tabula un nekaskādējas. Divi regresijas testi; otrais sargā tieši „dzēsu chunkus, aizmirsu vektorus" kļūdu. Vēsturiskais atlikums gaida operatora apstiprinājumu un pāra rollback.

**4. PDF ceļš nekad nav strādājis.** `scripts/ingest_url.py::_extract_pdf` importēja `pypdf`, kas šajā venv nav uzstādīts un nav ne `requirements.txt`, ne `pyproject.toml`. Izsaukuma vieta `ImportError` noķēra ar `except Exception`, izdrukāja stderr un atgrieza `None` — tātad PDF ievākšana izskatījās pēc izlaista URL, ne pēc kļūmes, un Datu kontrakta #4a partiju programmu PDF ceļš klusi nedarbojās. Pārlikts uz `pymupdf` (jau bija klāt kā tranzitīva atkarība, tagad deklarēts skaidri), un `ImportError` tagad iet cauri: trūkstoša bibliotēka ir vides kļūme, ne slikts URL.

### Divas vietas, kur mūsu pašu dokumentācija apgalvoja nepatiesību

`.claude/agents/contradiction-hunter.md` un `.claude/commands/deep-check.md` abi rakstīja, ka `saeima_vote` claims „NAV vektorizēti" un ka tie ir „absent from `claim_vectors`". **Izmērīts: 572 265 no 572 811 (99,9 %) vektoru NES**; trūkstošie 546 ir augšminētais neizdevušais batch. Operatīvais secinājums nemainās — strukturālais SQL gājiens joprojām ir vienīgais ceļš uz retorika↔balsojums kandidātiem —, bet iemesls ir cits un tas ir svarīgi: iegultie vektori klasterē pēc TĒMAS un nešķir „atbalstu reformu" no „balsoja PRET reformu" (T9), un `claim_type_filter` tiek piemērots PĒC kNN (T10). Vecais formulējums aicināja lasīt tukšu kNN rezultātu kā „vote claims nav meklēšanas indeksā" — tie tur ir, tie vienkārši ir nepareizais instruments.

`/audit-integrity` 7. pārbaude apgriezta uz DB→disks virzienu. Vecā forma skenēja disku, kur deployētajā mapē ir tieši **viens** PNG (avota PNG dzīvo `output/images/briefs/` un netiek deployēti), tāpēc tā mūžīgi apskatīja 1 kandidātu un ziņoja tīru. Jaunā drukā `checked=` kopskaitu, lai skrējiens, kas pārbaudīja 0 rindu, nevarētu izskatīties pēc tīra. Bāzlīnija: 137 pārbaudītas, 2 karotas.

### „Nav ko darīt" vairs nav ✓ — un tests, kas rakstīja ražošanas DB

Pēc 1. soļa labojuma to pašu jautājumu bija vērts uzdot par pārējiem deviņiem. **Seši no tiem atgriezās `done`, kad godīgā atbilde ir „nebija ko darīt"** — piemēram „Nav jaunu pretrunu pārskatīšanai" vai „Nav dienas pārskata pārbaudei". Klusā dienā tas ir nekaitīgi. Dienā, kad ielāde krīt, tas nav: jaunu dokumentu nav, tāpēc 2., 3., 4. un 5. solim visiem nav ko darīt, un mirusi diena renderējās kā ✓ siena ar „10/10". Tieši tāds ieraksts stāv 07-31 handoff.

Ieviests atsevišķs statuss `n/a` ar savu ikonu `○`. Tas joprojām skaitās pabeigts — klusa diena nav nepabeigta diena —, bet vairs nav tas pats apgalvojums, un galvene tagad skaita atsevišķi: „3 soļi nav pabeigti (3 soļiem nebija ko darīt)". Četri esošie testi apstiprināja tieši veco uzvedību un ir pārmērķēti; klāt nāk trīs jauni, no kuriem viens pieprasa, ka pilnīgi tukša diena NEDRĪKST uzrādīt desmit ķeksīšus.

**Un šī paša labojuma gaitā es pats saražoju to pašu klasi.** Kopsavilkuma `log_action()` `morning_ingest.py::main()` iekšienē nesaņem `db_path`, tāpēc tas raksta DZĪVAJĀ `data/atmina.db`; `tests/test_morning_ingest.py` stubo piecus konveijera soļus, bet sestais blakusefekts tā tapšanas brīdī neeksistēja. Četri pytest skrējieni ielika **19 rindas īstajā `logs` tabulā** — un tās nebija tikai nekārtība: `_check_ingest` lasa jaunāko `morning_ingest` rindu, tāpēc rutīna sāka ziņot par ielādes kļūmi („krita: fetch_all_mentions"), kuras nav bijis, tieši tajā dienā, kad šī pārbaude tika ieviesta, lai tādus nepatiesus ziņojumus novērstu. Rindas noņemtas ar `data/{fix,rollback}_test_log_rows_2026-08-02.sql` (rollback nes pilnu rindu saturu un uzrakstīts PIRMS dzēšanas); īstā 11:03–11:11 ingesta telemetrija neaiztikta.

Novēršana divos līmeņos, jo viens no tiem šo jau vienreiz palaida garām: `tests/conftest.py` sesijas mēroga slazds salīdzina ražošanas DB rindu skaitus pirms un pēc skrējiena un nosauc tabulu, kas paaugusies (tas ir slazds, ne smilšu kaste — testi, kas ražošanas DB tikai LASA, netiek traucēti); un `tests/test_morning_ingest.py` stubs ir `autouse`, nevis daļa no `all_steps_ok` — divi testi šajā failā palaiž `main()` bez tās fikstūras, un tieši tāpēc caurums izdzīvoja pirmo labojumu. Slazds to noķēra uzreiz, jau nākamajā skrējienā. Kopsavilkuma rinda tagad ir arī līgums: divi testi apgalvo, ka veiksmīgs skrējiens raksta `success` ar tukšu `failed`, bet kritis solis atstāj `error` rindu ar sava vārda.

### Rīta ingests bija palaists garām, un rutīnas statuss to nerādīja

Pēdējais `ingest` žurnāla ieraksts bija 08-01 21:37. `print_routine()` tomēr rādīja 1. soli zaļu, jo `_check_ingest` skaita `DATE(scraped_at)` rindas, un tajā rītā viens dokuments bija ievākts ad-hoc. Parasta diena dod 600–900 dokumentu; tobrīd bija 10. Palaists (5/5 soļi OK: 23 RSS dokumenti, 89 tvīti, 177 pieminējumi, `strategy: search`, ne degradētais `timeline` fallback). Tā ir tā pati klase, kas 07-29 outage — skaitītājs, kas nešķir „rutīna nostrādāja" no „kaut kas šodien tika ierakstīts".

## 2026-08-02 — 11 nodiakritizētās nostājas noņemtas no dzīvās vietnes; vārti salaboti pēc MĒRĪJUMA, ne pēc diagnozes

Kopš 2026-04-09…04-16 (T4 laikmets) dzīvajā vietnē stāvēja 11 pilnībā nodiakritizētas nostājas — mūsu pašu teksts par nosauktiem politiķiem, uz 8 politiķu lapām, partijas lapas un divām JSON plūsmām. Salabotas visas 11, plus **6 bojāti citāti** un **1 tēmas maiņa** (#7520 `Sociālā politika` → `Valsts pārvalde`). Pāra rollback ar visām vecajām vērtībām un 11 vektoriem hex formā uzrakstīts PIRMS mutācijas; katras rindas vektors pārrēķināts un salīdzināts baitu līmenī. Verificēts dzīvajā vietnē: 11/11.

**Citātu jautājums izšķīrās par labu labošanai, jo visi 11 avota dokumenti ir ar pilnu diakritiku.** CLAUDE.md verbatim noteikums sargā politiķa PAŠA kļūdas; šeit avotā kļūdu nav, tātad bojājums bija mūsu, un atjaunošana pēc avota padara citātu patiesi verbatim. Ieviestie vārti to pārbaudīja mehāniski — katram jaunam citātam jābūt apakšvirknei savā avotā — un **noķēra manu paša kļūdu**: biju uzrakstījis Kulberga citātā `pavadām`, kamēr viņš pats raksta `pavadam`. Tā būtu bijusi nepatiesa citēšana zem labojuma karoga. Viens citāts (#7496) noņemts pavisam: avots ir žurnālista netiešā runa, ne pirmās personas izteikums, t.i. parafrāzes klase.

**Vārtu labojums: BACKLOG diagnoze bija nepareiza, un mērījums to parādīja.** Ieraksts apgalvoja, ka teksts izspruka caur EN-markieru zaru. Ieviešot tieši to, tika noķerts **1 no 11**. Īstā izeja bija `lv_score < min_lv_markers` — īsa, lietvārdiem blīva nostāja savāc 0–1 latviešu marķieri, tāpēc tā izgāja kā „laikam nav latviešu" un **nekad nesasniedza attiecības pārbaudi**, kas ir vienīgā, kas redz nodiakritizēšanu. Mehānisms pilnībā: fasttext nodiakritizētu latviešu valodu neatpazīst — pieciem tas atdeva `lv` 0.13–0.32, pārējiem `fr/lt/pl/sl/ur` 0.13–0.19. Šāds nedrošs verdikts nav pierādījums nekam, vismazāk tam, ka teksts NAV latviešu.

Jaunais noteikums: izsprukt drīkst tikai ar POZITĪVU ne-latviešu signālu (drošs fasttext ≥0.70 vai EN zars), nekad ar latviešu marķieru trūkumu vien. Ar vienu būtisku precizējumu, ko atklāja mērījums: pirmā versija noraidīja claim #1563 („Panācis Satversmes tiesas spriedumu…") — **pareizu latviešu valodu ar 1 diakritisko zīmi uz 84 burtiem**. Pie rakstīšanas robežas noraidījums nozīmē atteiktu rindu, tāpēc tas ir īsts viltus pozitīvs. Tāpēc vārti tagad tur tikai **nulles diakritikas parakstu**, nevis „zem attiecības sliekšņa".

Izmērīts pirms/pēc pār visu korpusu: nostājās **0 jaunu noraidījumu** (164 atzīmētās `saeima_vote` rindas ir leģitīmas un vārtos nemaz nenonāk — `src/db.py:748` tās izslēdz), `reasoning` +82, `quote` +7. Tie 89 ir tā pati T4 klase, kas līdz šim bija neredzama — pierakstīti BACKLOG kā atsevišķs darbs. Angļu teksts neskarts (5/5 iziet). Regresijas fixtures: visas 11 nostājas, #1563 pretējā virzienā un divi angļu paraugi (`tests/test_quality.py`).

Blakus pierakstīts BACKLOG: `quote` diakritiku validācija ir konceptuāli nepareizs vārtu veids — citātam pareizais jautājums ir „vai tas ir avotā", ne „vai te pietiek garumzīmju"; šis labojums padara viltus noraidījumus biežākus (1 → 8), tāpēc jautājums vairs nav teorētisks.

## 2026-08-02 — Divi klusi noteikumi salaboti: circuit-breaker pretruna un miris `retrieve_context`

**1. `empty_doc_ids` uz neizlasītiem dokumentiem — noteikums, kas prasīja datu zudumu.** Viens noteikums dzīvoja trīs failos ar trim atbildēm: `rubrics.md` prasīja pāri palikušos 12+ dokumentus atzīmēt ar `save_analysis(claims=[], empty_doc_ids=[...])`; kanoniskais `.claude/agents/claim-extractor.md` prasīja STOP; `wiki/operations/agenti/claim-extractor.md` prasīja dispečēt pa vienam. **Kaitējums bija tikai pirmajā, un tas bija reāls:** `empty_doc_ids` uzliek `reviewed_at`, tāpēc neizlasīti dokumenti pazūd no `get_pending_politicians()` uz visiem laikiem, bez pēdas, ka tos neviens nav atvēris (T5 + T11).

Visi trīs salāgoti uz operatora jau izšķirto virzienu: **pirmie 12 tagad, atlikušie otrajā sweep ar svaigu sub-aģentu.** 12 ir kvalitātes limits, nevis STOP un nevis iemesls dokumentus izmest. Tieši tā 08-01 rutīna arī strādāja praksē (Lapsam 18 doki → 12 + 6).

**Blakus atrasts otrs kluss noteikums tajā pašā failā.** `rubrics.md` confidence tabula prasīja pievienot `"needs_review": true` claim vārdnīcai. **Tādas kolonnas vai parametra `src/` nav nevienas** (pārbaudīts) — liekā atslēga tiek klusi atmesta, tāpēc šādi „atzīmēts" claim nonāk DB izskatoties pilnīgi pārliecināts. Tas ir tieši tas, pret ko brīdina CLAUDE.md eskalācijas 2. noteikums, tikai rubrikas to prasīja darīt. Labots uz īsto konvenciju (`reasoning` PREFIKSĀ), un tā pati kļūda izlabota `quality-bars.md:11`, kas uz rubrikām ved.

**2. `src/tools.py::retrieve_context(query=…)` bija miris kopš 2026-04-09.** Funkcija padeva `opponent_id=` uz `db.search_similar()`, kas šo parametru sauc par `politician_id` — tātad KATRS izsaukums ar `query` meta `TypeError`. Neviens to nepamanīja, jo neviens ražošanas kods to nesauc; vienīgais patērētājs ir dokumentētais piemērs `wiki/operations/wiki-tools.md`, t.i. aģentam piedāvāts rīks, kas vienmēr krita. Salabots (ne izmests — tā ir dokumentēta API), un abi zari pārbaudīti dzīvē.

Pievienoti hermētiski regresijas vārti `tests/test_tools.py`: tests apstiprina, ka `db.search_similar` parametrs joprojām saucas `politician_id`, un ka izsaukums to tiešām sasniedz. **Pārbaudīts, ka tests noķer defektu** — ar veco kwarg tas krīt, ar jauno iziet. Niansē, kas padara vārtus vajadzīgus: `retrieve_context` ieslēdz izņēmumus JSON kļūdas virknē, tāpēc slikts kwarg neizpaužas kā izmests `TypeError`, bet kā klusa tukša atbilde.

## 2026-08-01 — Vakara rutīna: pārskats #398, un trīs vārti, kas nostrādāja pēc kārtas

Rutīna pabeigta un publicēta (otrais ielādes vilnis, 714 dokumenti, **31 pozīcija**, 0 pretrunu, 0 spriedžu). Interesantais nav pats pārskats, bet tas, ka **katrs no trim vārtiem noķēra kaut ko, ko iepriekšējais bija palaidis garām** — un divi no atradumiem bija defekti manā paša darbā.

**Ekstrakcija: 19 paralēli `@claim-extractor` + otrs sweep.** 51 dokuments, 4 jaunas pozīcijas, 47 tukši — gandrīz viss bija kaili retvīti. Zemā raža ir īsts signāls, ne caurums; diena tā arī uzrakstīta. Visi 19 atgriezās ar `status=success` un tukšu `failures`.

**Vārti 1 — skelets. Audience filtrs būtu apēdis 8 no 30 rindām.** `generate_daily_brief()` tēmu vaicājumi izslēdz `relationship_type IN ('journalist','neutral',...)`, tāpēc skelets emitēja 22 pozīcijas no 30. Starp izmestajām bija **operatora tikko apstiprinātais claim #615796** — nodošana `@brief-writer` bez labojuma būtu klusi atcēlusi operatora lēmumu. Rindas atjaunotas ar roku, `Korupcija un KNAB` promovēta uz pilnu sadaļu (T7 atļauj promovēt, nekad klusi dzēst). Tas nav malas gadījums: tieši šīs 8 rindas veidoja dienas lielākās tēmas kodolu.

**Vārti 2 — korektūra. Trīs apgalvojumi mūsu pašu tekstā, ne claims.** Pārbaudot konteksta blokus pret korpusu: „Straume **iesniedza atlūgumu**" ir APSTRĪDĒTS (doc 77852 LETA saka atlūgums, doc 77863 Straume LTV to tieši noliedz — „Tas nav nekāds atlūgums") → tagad rādītas abas versijas ar avotu; „nogalināja vīrieti" → avotu formulējums „nāvējoši piekāva pedagogu"; un noņemts apgalvojums par „vienīgo robežkontroles punktu".

**Vārti 3 — `@quality-reviewer` atdeva FAIL, un tam bija taisnība trīs reizes.** (a) Nogriezta `la.lv` saite, kas dzīvajā vietnē būtu bijusi 404. (b) **Mans korektūras 3. labojums bija nepareizs** — doc 78548 (pārskatā jau citēts!) burtiski satur „vienīgā robežkontroles punkta ar Baltkrieviju - Pāterniekos"; mans meklējums bija ierobežots ar 5 dokumentu izlasi. Apgalvojums atjaunots ar avotu. (c) **Trūkstoša pozīcija:** doc 78085 Jurēvics ir vienīgais runātājs ar nostāju, bet junction viņam liek `mentioned`, tāpēc viņš nekad nenonāca ekstrakcijas rindā — un dokuments jau bija `reviewed_at` no cita politiķa slota, t.i. izskatījās apstrādāts. Saglabāta kā #615820; bez tās `Korupcija un KNAB` būtu 3 no 5 viena žurnālista nepārbaudīti apgalvojumi. Sakne pierakstīta BACKLOG — sk. § Junction lomas apgrieztas.

**Robežas stāsts — spriedze apzināti NEreģistrēta.** Šlesers (#615811) un Krištopans (#615801) sauc Pāternieku slēgšanu par NA priekšvēlēšanu kampaņu, bet viss korpuss to apraksta kā TEHNISKU (Valsts robežsardze: traucējumi informācijas sistēmās), un **nevienā dokumentā nav politiska lēmuma slēgt punktus**. Spriedzes reģistrēšana nozīmētu, ka atmina pati apgalvo konfliktu par politiku, kuras esamību avoti nerāda — 2026-07-25 @AtlasDynam1cs kļūdas forma. Pārskatā rakstītas abas puses, vadīts ar faktu, ne ar konflikta rāmējumu. Neatkarīgs apstiprinājums: Dombravas ekstrakcijas aģents, lasot dienas dokumentus no nulles, patstāvīgi konstatēja to pašu — neviens mediju doks slēgšanas lēmumu viņam nepiedēvē. **Rutīnas 5. solis paliek sarkans ar nolūku.**

**#615796 (Kļaviņš par Straumi) — divpakāpju operatora lēmums.** Vispirms: paturēt, publicējams. Pēc tam `@quality-reviewer` norādīja, ka palikusī klauzula „un nespēja pildīt amata pienākumus" ir veselības apgalvojuma nespējas puse ar noņemtu cēloni (avotā vienīgais nosauktais prombūtnes iemesls ir alkohola atkarība). Operators lēma nogriezt. `stance` labots, `claim_vectors` pārrēķināts un **baitu līmenī salīdzināts** ar jauno tekstu, pāra rollback uzrakstīts PIRMS mutācijas (`data/rollback_claim615796_stance_2026-08-01.sql`, satur gan veco tekstu, gan 1536 baitu embedding).

**Publicēšanas vārti vairs nav atkarīgi no trešās puses.** `check.sh` palaida pytest bez marķieru filtra, tāpēc divi DZĪVĀ KNAB tīkla testi bija katrā publicēšanas gājienā — KNAB nepieejamība nogāza mūsu vārtus. Noklusējums tagad `-m "${CHECK_PYTEST_MARKERS-not slow}"` (1750/1752); pilnais skrējiens dabūja mājokli nedēļas rutīnas 4. sadaļā, jo tie testi ir vienīgā pārbaude, ka KNAB skrāpis vēl atbilst avota formātam (T12).

**`NEEDS_REVIEW` ieraksts BACKLOG-ā bija nepatiess abos nesošajos apgalvojumos** — sk. commit `8ea304f4`. Īsi: konvencija IR dokumentēta (`Izvērtēts`, 169 rindas pret 62 `REVIEWED`), sweep bijuši četri, ne viens, un no 113 atvērtajiem karogiem tikai 16 ir prefiksā — 97 ir beigās, tāpēc kanoniskais `LIKE 'NEEDS_REVIEW%'` redz 16 no 113.

**Blakus izpildīts:** 11 nulles baitu `.db` failu dzēsti, t.sk. `atmina.db` repo saknē (tā pati klusās nepareizā ceļa klase kā kailais `python`); visi četri attēla varianti ģenerēti un pārbaudīti dzīvē ar HTTP 200 (klase, kas divos maija pārskatos atstāja 404 hero un `og:image`); `check_output` tīrs pēc render ar `static` — bez tā sitemap trūka šīsdienas pārskata, tieši kā brīdina runbooks.

## 2026-08-01 — X pieminējumu klusās nulles dienas: 5 no 25, neviena virsma nesūdzējās

Pamanīts, salīdzinot dienas ievākšanas apjomus. 25 dienās **5 dienas ar 0 `x_mention` dokumentiem** un vēl viena ar 1 — un katrā no tām tvītu ievākšana tajā pašā dienā strādāja normāli (272–443 tvīti), tātad X bija sasniedzams un sīkfailu pūls darbojās. Izmeklēšana atrada **divus atsevišķus cēloņus**, abus klusus.

**A. `timeline` stratēģija atnes simtiem un saglabā nulli.** Kad pūla veselo slotu skaits nokrīt zem sliekšņa, dispečers klusi pārslēdzas no `search` uz `timeline`. Tās nav līdzvērtīgas: `search` meklē pieminējumus no **jebkura** autora, bet `timeline` skenē izsekoto politiķu **pašu** taimlīnes un patur tvītus, kas piemin citu izsekoto politiķi — un tos pašus tvītus `fetch_all_twitter()` jau ir saglabājis dažas minūtes agrāk. Tāpēc katrs trāpa `insert_document()` `content_hash` dublikāta zarā un atgriež `None`.

Mērīts `logs` tabulā: 07-15 `fetched 262, stored 0`; 07-20 `fetched 258, stored 0`; 07-16 `fetched 276, stored 2` — visiem `errors: 0` un statuss **success**. Katrs degenerētais skrējiens ir `strategy: "timeline"`; katrs `search` skrējiens saglabā 176–234 no ~230–250.

Pārbaudīts arī pretējais pieņēmums, un tas **neapstiprinājās**: junction sapludināšanas zars (`content_hash` trāpījums ar to pašu `source_url`) šeit nepalīdz — tajās dienās `mention_target` savienojumu ir **0** (strādājošās dienās 264–469). Zudums ir pilnīgs, ne daļējs.

**B. Wiki ingest žurnāla statuss bija iekodēts cieti.** `append_ingest_entry(..., status="success")` — burtiski konstante, tāpēc `wiki/log-ingest/` rādīja zaļu `X/Mentions` rindu arī pie 0 saglabātiem. Operatora galvenā virsma meloja tieši tad, kad tai vajadzēja brīdināt.

Labots abās vietās: statuss tagad ir `failure`, ja `fetched > 0 un stored == 0` (ar ziņojumu, kas nosauc stratēģiju — tā ir vienīgā pēda, pēc kuras atšķirt cēloni), un ingest žurnāls saņem to pašu statusu, kļūdu un atsevišķu seguma piezīmi. `timeline` skrējiens tagad ir redzams pats par sevi arī tad, kad tas kaut ko saglabā, jo tā segums ir šaurāks pēc konstrukcijas. Vārti: `tests/test_mentions_silent_drop.py` (5 testi, no tiem 2 ir regresijas vārti, lai strādājoša diena nekļūtu par kļūdu).

**Trešais atradums, kas NAV koda defekts.** Trijās nulles dienās (07-22, 07-28, 07-31) `logs` tabulā nav **neviena** `mentions_fetch` ieraksta — ne veiksmes, ne kļūmes. Ķēde ir `ingest` × 11 → `social_fetch_all` → apstāšanās; 07-31 tas atkārtojas trīs reizes. Solis netika izsaukts vispār. Tas atbilst `daily-routine.md` manuālajam ceļam, kur ir trīs atsevišķi izsaukumi un apstāšanās pēc otrā neatstāj nekādas pēdas — `scripts/morning_ingest.py` palaiž visus piecus.

## 2026-08-01 — 2026. gads PILNS (parity 0) + wiki sinhronizācija ar izlabotajiem partiju skaitļiem

**2. partija: 305 balsojumi 12 dienās, 23 203 claims, deputātu atbilstība 27 103/27 103 = 100 %, 0 kļūmju.** Atšķirībā no 1. partijas (10 pilnīgi tumšas dienas) šīs 12 dienas DB jau bija daļēji — tātad tas ir robu aizpildījums ESOŠO dienu iekšienē, kas ir tieši T14 jautājums: nepilna balsojumu ķēde padara nedrošu jebkura atsevišķa balsojuma citēšanu, jo procedurālais un substantīvais var rādīt pretējās pusēs. Šī partija atjauno drošu citēšanu 2026. gadam.

Rīka idempotence apstiprināta mērogā: palaists pār VISU `parity_2026.json`, un 459 jau ielādētie tika izlaisti (`skipped_present: 459`), nevis dublēti.

**Kopā 2026: 764 balsojumi, 59 893 claims. Balsojumi 595 → 1359, sēžu dienas 13 → 23.** Atkārtots parity audits pēc ielādes: **darba kārtībā 1298, trūkst 0.** Gads slēgts.

Neatkarīgā pārbaude: `saeima_vote` claims 512 918 → 572 811 (delta sakrīt ar 36 690 + 23 203); 0 individuālo balsu bez `politician_id`. Balsojumi bez claims: 3 — pārbaudīti pa vienam un **nav** no šīs ielādes (mans ielādēto id kopums ir tieši 764, un neviens no trim tur nav). Tie ir agrākas ievākšanas tukši čaulas ieraksti par 2026-06-04 aizklātajām vadības vēlēšanām; pierakstīti BACKLOG kā atsevišķa nekonsekvence.

**Wiki sinhronizācija.** `wiki_sync()` pēc `src/wiki.py` labojuma; 208 faili. Partiju `claims:` lauks tagad ir pozīcijas, ne balsojumi:

| Partija | Bija | Ir |
|---|---:|---:|
| Jaunā Vienotība | 131 026 | 832 |
| Zaļo un Zemnieku savienība | 95 603 | 469 |
| Apvienotais saraksts | 66 085 | 644 |
| Nacionālā apvienība | 58 209 | 779 |
| Stabilitātei! | 56 794 | 16 |
| Progresīvie | 46 013 | 504 |
| Latvija Pirmajā Vietā | 44 787 | 341 |

Mainījās arī `top_politicians` un `top_topics` — tie tagad ranga pēc izteiktajām pozīcijām, ne pēc nobalsoto biļetenu skaita; agrāk partijas „aktīvākais" bija tās čaklākais apmeklētājs. `votes_par`/`votes_pret` pieauga atsevišķa iemesla dēļ — tie ir īsti jaunie balsojumi no ielādes.

**Blakusefekts, kas ir pareizs, bet lasās slikti:** partijai, kurai ir tikai programmas solījumi, lapa tagad rāda `claims: 0` — Gobzema saraksts (12 `program_promise`) un Suverēnā vara/Jaunlatvieši (24). Skaitlis ir patiess (pozīciju tiešām nav), bet `0` uz transparences virsmas lasās kā „neko nedara". Pierakstīts BACKLOG; risinājums prasa vai nu atsevišķu lauku, vai pārsaukšanu, un pirms tam jāpārbauda `.base` faili.

**Vēl viens klusais izejas kods, noķerts dzīvē.** 1. partijā viens balsojums izkrita ar tīkla noildzi; `failed: 1` bija kopsavilkumā, `return 0` kodā. Salabots un fiksēts testos — sk. iepriekšējo ierakstu.

## 2026-08-01 — 2026. gada ielāde, 1. partija: 10 tumšās sēžu dienas (459 balsojumi)

Operatora lēmums bija „2026 vispirms", un pirmā partija ir tā, kur DB bija **nulle**: nepārtraukta josla 2026-01-15 … 03-19, desmit sēžu dienas, kuras ievākšana nekad nav skārusi. Ielādēts pa daļām ar nolūku — nevis viss 764 balsojumu gads vienā gājienā — lai skaitļus varētu salīdzināt, kamēr atgriezties vēl ir lēti.

**Rezultāts:** 459/459 balsojumi, **36 690 `saeima_vote` claims**, deputātu atbilstība **40 390/40 390 = 100 %**. 2026. gads: 595 → 1054 balsojumi, 13 → 23 sēžu dienas. Rollback: `data/rollback_saeima_2026_tranche1_2026-08-01.sql` + `…_tranche1b_…` (atkārtojumam).

**Pārbaudīts neatkarīgi no rīka atskaites**, jo rīka izejas kods šoreiz tieši to arī nopelnīja (zemāk): DB delta +458 sakrīt pa divām neatkarīgām skaitīšanām (2026. gada kopsumma un unikālie `(vote_date, vote_time)` visā tabulā); **0 ne-reģistrācijas balsojumu bez claims** (tas ir partial-write tests — `store_vote()` commit-o pirms claim ģenerēšanas); **0 individuālo balsu bez `politician_id`**; `saeima_vote` claims 512 918 → 549 608.

**Dzīvs apstiprinājums šodienas `claim_type` vārtiem.** 36 690 jaunu balsojumu claims iekrita DB, un `wiki` partiju skaitlis **nekustējās**: JV ar vārtiem 832, bez vārtiem tas pats vaicājums tagad atgrieztu **140 507** (pieaugums 9481 tikai no šīs partijas). Ja ielāde būtu notikusi pirms rīta labojuma, tie skaitļi būtu aizgājuši wiki lapās. Secība izrādījās pareizā; pretējā tā nebūtu.

**Viens balsojums izkrita ar tīkla noildzi, un skripts izgāja ar 0.** `failed: 1` bija kopsavilkumā, `return 0` bija kodā — tā pati klase, ko šorīt slēdza `morning_ingest.py`, tikai bulk rakstīšanas rīkā. Ja to būtu palaidis kaut kas automatizēts, viens balsojums būtu pazudis klusi. Salabots: `stats["failed"]` → izejas kods 1, un ziņojums pasaka, ka atkārtojums ir drošs, jo pirms katras rakstīšanas notiek `(vote_date, vote_time)` pārbaude. Empīriski apstiprināts atkārtojot — `stored: 1, skipped_present: 64`. Vārti: `tests/test_ingest_missing_votes_exit_code.py` (4 testi, t.sk. tas, ka jau esošam balsojumam nedrīkst pieskarties tīklam — citādi ieteikums „palaid vēlreiz" ražotu dublikātus).

**Atvērts pēc šīs partijas:** 172 balsojumi ar dokumenta atsauci, bet bez pārmantojama kopsavilkuma (`summary` NULL) — to claims atkāpjas uz vispārīgo `Balsoja PAR: <motīvs>` formu. Tas ir `@saeima-tracker` Step 3.5 darbs; saraksts ir ielādes atskaitē. Paliek arī 2026. gada 305 balsojumi pārējās dienās un visa 2025. gada partija.

## 2026-08-01 — 16 aizklātie balsojumi pierakstīti kā neielādējami (operatora lēmums)

Parity audits katrā skrējienā skaitīja 16 ierakstu par „trūkstošiem", un katra sesija tos izmeklēja no jauna, lai nonāktu pie tā paša secinājuma. Pārbaudīts pret titania: visiem 16 `voteFullListByNames` ir `[""]` — **tukšs pēc dizaina**. Aizklātā balsošana (Saeimas vadības, Valsts prezidenta, valsts kontroliera vēlēšanas) neatstāj ierakstu par to, kā balsoja konkrēts deputāts, tāpēc `saeima_individual_votes` tur nav ko likt. Tie nav robi, ko aizpildīt.

Pierakstīti `src/saeima/unloadable.py` ar atslēgu `(vote_date, vote_time)` — **nevis URL**, jo titania pārarhivē balsojumu lapas ar jauniem UNID, tāpēc URL atslēga te novecotu tieši tāpat, kā tā padara aklu `store_vote()` dedup. Audits tos tagad rāda atsevišķā rindā („zināmi neielādējami"), ne kā trūkstošus; pārbaudīts dzīvē — 2022-11-01 ir `trūkst 0` agrāko 5 vietā.

**Kas tomēr saglabāts.** Lapa nav tukša: `voteShortListByNames` nes kandidātu sadalījumu, un lauku nozīme ir **nolasīta no pašas lapas renderētāja** (`redrawMainTableShort` galvenes: `Kandidāts | Par | Pret`), nevis uzminēta. Tie ir kandidātu, ne deputātu līmeņa dati, tāpēc apzināti NEIET `saeima_individual_votes` shēmā — jauna tabula netika būvēta, jo neviena virsma to šodien neprasa; dati dzīvo tur, kur tie jau bija vajadzīgi. Skaitļi sakrīt ar publisko vēsturi: Smiltēns 82:11 par priekšsēdētāju, Mieriņa 55:34, Rinkēvičs 52 balsis 3. kārtā, Korčagins 90:1.

Divi stāvokļi, kurus nedrīkst jaukt: `sealed_with_tally` (13) un `sealed_no_data` (3 — visi 2023-09-20, kur arī īsais saraksts ir `[""]`, t.i. titania nav publicējusi neko).

Viena lieta, ko dati paši izskaidroja: 2023-05-31 prezidenta vēlēšanu 1. un 2. kārtai sadalījums ir **identisks**. Tā nav dublēta rinda, bet strupceļš — neviena balss nepārgāja; 3. kārtā Pinto vairs nekandidēja un viņas 10 balsis aizgāja Rinkēvičam (42+10=52). Tas ir fiksēts testā, lai neviens to „nesalabotu".

Vārti: `tests/test_saeima_unloadable_votes.py` (8 testi). Divi no tiem sargā pretējos virzienus: saraksts nedrīkst klusi paplašināties (kļūdaina rinda paslēptu ĪSTU robu, tāpēc katram ierakstam jāizskatās pēc amatpersonu vēlēšanām), un atslēga nedrīkst saīsināties līdz datumam (2023-09-20 tajā pašā dienā notika arī parasti balsojumi).

## 2026-08-01 — T8 paša rīka līmenī: sesiju manifests salabots, 2026. gads beidzot izmērīts

Parity audits par 2026. gadu ziņoja „tīrs", nekad tur nepaskatījies. Cēlonis nebija viens, bet **trīs klusi robi vienā ķēdē**, un katrs no tiem atsevišķi ir pietiekams, lai rīks melotu.

**1. Gada logs bija iesaldēts.** `_p3_extract_sessions_2026-05-26.py` filtrēja `s["year"] <= 2025` ar komentāru „skip 2026 — already in DB". Robeža tagad ir `--max-year` (noklusējums: kārtējais gads).

**2. Divus sēžu tipus parseris klusi izmeta.** Kalendārs lieto PIECAS etiķešu formas, ne trīs: bez sufiksa, `(J)`, `(A)`, un vēl `(As)` = ārkārtas **sesijas** sēde un `(S)` = svinīgā sēde. Pēdējās divas neizturēja `int()` un pazuda bez pēdām — **16 sēdes 2022.–2026. gadā**, to skaitā **2026-07-23 ar 65 balsojumiem DB**. Tas nozīmē, ka arī jau pabeigtie 2022.–2025. gada auditi bija mērīti pret nepilnīgu sēžu sarakstu: manifestam pietrūka 8 svinīgo sēžu un **divu ārkārtas sesijas sēžu (2023-07-08, 2024-07-25), ko nekad neviens audits nav skatījis**.

**3. Momentuzņēmuma formāts bija mainījies** (T12 — formāta maiņa, ne izzušana): Playwright pieejamības kokā dienas etiķete pārcēlās no `cell` mezgla uz `link` mezglu, tāpēc parseris pret svaigu lapu atgrieza **nulli sēžu**. Parseris tagad pieņem abas formas, un abas ir fiksētas testos.

Turklāt ģenerators vispār **nebija palaižams**: tas norādīja uz 2026-05-26 momentuzņēmumu, kura vairs nav (`.playwright-mcp/` ir gitignorēta skrāpes mape), tāpēc manifests bija neatveidojams artefakts, uz kuru paļāvās viss audits. Tagad tas pieņem `--snapshot`/`--max-year` un pats atrod jaunāko momentuzņēmumu.

**Pārbaude, ka pārrakstītais parseris nav regresija:** jaunais manifests salīdzināts ar veco pa laukiem — **0 pazudušas rindas, 0 lauku atšķirības** 250 pārklājošajās; klāt nākušas tikai 10 rindas 2022.–2025. gadam (jaunie tipi) un 47 rindas 2026. gadam. 250 → 307.

**Vārti pašam rīkam.** `audit_saeima_agenda_parity.py` tagad **apstājas ar kodu 2**, ja manifestā nav nevienas prasītā gada sēdes, un pasaka, kuri gadi tur ir — „0 sēžu iekšā" nav tīrs gads, tas ir manifesta robs. Apstāšanās notiek PIRMS pirmās tīkla ielādes (fiksēts testā). Filtri (jautājumu sēdes; vēl nenotikušas sēdes) tagad tiek uzskaitīti izvadē, nevis piemēroti klusi — nākotnes sēde citādi atgrieztu 0 darba kārtības balsojumu un izskatītos pēc tukšas dienas.

**Rezultāts, ko tas atbloķēja.** 2026: darba kārtībā **1298**, DB **534**, trūkst **764 (58,9 %)** — sliktāk nekā 2025. gada 49,7 %. **10 sēžu dienas nav ievāktas nemaz** (459 balsojumi), nepārtraukta josla 01-15 … 03-19. To vidū 2026-01-15 ir **neuzticības balsojums Ministru prezidentei Evikai Siliņai** (885/Lm14, 18/45/0).

Vārti: `tests/test_saeima_session_manifest.py` (12 testi — abi momentuzņēmuma formāti, visas piecas etiķešu formas, nezināma etiķete tiek ZIŅOTA nevis izmesta, tukšs gads apstādina auditu bez tīkla pieskāriena).

## 2026-08-01 — Datu kontrakts #4 kļuvis izpildāms: `claim_type` vārti + 6 vaicājumi salaboti

`CLAUDE.md` apgalvoja, ka „every render + brief query gates on `claim_type='position'`", un tieši uz to pamatojas 4a apakšpunkts — ka programmu solījumi *par brīvu* nenonāk politiķu lapās. To nepārbaudīja **nekas**. Klase nedegradējas pakāpeniski: `saeima_vote` pārsniedz `position` attiecībā 101:1 (512 918 pret 5 078), tāpēc aizmirsts predikāts rezultātu neapgriež par mazliet — tas to apgriež pilnībā.

`tests/test_claim_type_gate.py` staigā pa `src/render/**`, `src/briefs.py`, `src/wiki.py`, `src/routine.py`, izvelk katru SQL literāli ar `ast` un prasa `claim_type` predikātu. No 99 vaicājumiem 16 bija bez tā; **6 izrādījās īsti defekti, 10 — likumīgi visu tipu lasījumi**, kas tagad dzīvo `ALLOWED` sarakstā ar pamatojumu katram. Sarakstam pašam ir vārti (`test_allowlist_has_no_dead_rows`) — novecojis izņēmums ir tieši tas, kā šāds tests klusi pārstāj sargāt.

**Salabotie seši, katrs ar mērījumu:**

1. `_get_last_activity()` (`src/render/_common.py`) — **112 no 180** aktīvo politiķu „pēdējā aktivitāte" nebija pozīcija (108 `saeima_vote`, 4 `program_promise`). Rinda renderējās kā 📌 pozīcija ar saiti uz `pozicijas.html`, kas šo ierakstu **nesatur**, jo tā lapa filtrē pareizi. Balsojumam turklāt jau bija savs, pareizi marķēts kandidāts tajā pašā funkcijā — nefiltrētais vaicājums to dublēja nepareizā formā. Pēc labojuma balsojumi parādās kā „Balsoja par/pret" un „Atturējās", nevis kā pozīcija.
2.–3. `_check_contradictions()` un `_check_tensions()` (`src/routine.py`) — abi skaitīja visu tipu claims, bet ziņoja par „jaunām pozīcijām". Saeimas ielādes diena tos iesloga: 2026-07-23 pirmais skaitīja **5361** claim, kur pozīcijas bija **72**; otrais — **115** politiķus īsto **39** vietā (07-25: 1664/33 un 121/23). Tā nav viltus zaļā, bet viltus SARKANĀ gaisma — rutīna prasīja darbu par dienu, kurā jaunu pozīciju nebija.
4.–6. Trīs partiju vaicājumi `src/wiki.py` — partiju tabulas skaitlis, TOP politiķi un TOP tēmas partijas lapā. JV rādīja **131 026** „pozīcijas" īsto **832** vietā, Stabilitātei! — **56 794** īsto **16** vietā (3550×). `ORDER BY claims DESC` tāpēc sakārtoja partijas pēc nobalsoto biļetenu skaita, un TOP politiķi partijas lapā ranga pēc apmeklētības, ne pēc izteiktajām pozīcijām. Tas ir tas pats skaitlis, ko 07-30 dublēto balsojumu izmeklējums nosauca par „vienīgo redzamo pēdu `wiki/index.md`".

**Kas ar nolūku NETIKA filtrēts.** Desmit vietas paliek visu tipu, un katra ir izmērīta, ne pieņemta: pretrunu `JOIN claims` iet pēc primārās atslēgas (kurus claims — to nosaka pati pretruna); `wiki.py` tēmu universs deva 32 pret 32; `news.py` un `x.py` tēmu tagi apraksta DOKUMENTU, ne pozīcijas attiecinājumu, un filtrs tur tagus tikai **zaudētu** (5 no 3663 ziņu dokumentiem un 6 no 32 394 X postiem paliktu bez tēmas).

**Blakus atradums, kas nav šī labojuma darbs:** mērot `news.py`, atklājās, ka CVK kandidātu sarakstu dokumenti renderējas `zinas.html` kā parastas ziņas ar 12–25 tēmu tagiem. Sakne ir matcher junction uz programmu dokiem (BACKLOG § NBS pid=204), ne `claim_type` predikāts — pierakstīts tur, ar skaidru norādi, ka pareizais labojums ir šaurāks un operatora izlemjams.

**Jāzina pirms nākamās wiki sinhronizācijas:** 4.–6. punkts maina `wiki/` partiju lapu skaitļus un kārtību. Kods salabots; sinhronizācija un deploy ir ārpus šī ieraksta un prasa operatora apstiprinājumu (publicēšanas pauze).

## 2026-08-01 — Divas viltus zaļās gaismas slēgtas: rīta ingesta izejas kods + paneļa backlog dienas robeža

Abas ir viena forma — **virsma, kas ziņo par panākumu, ko nekad nav izmērījusi**.

**1. `scripts/morning_ingest.py` izgāja ar 0 arī tad, kad krita visi pieci soļi.** `step()` noķēra katru izņēmumu, izdrukāja `FAILED` un atgriezās; `main()` neatgrieza neko, un `__main__` izsauca to bez `sys.exit()`. Failā nebija nevienas `exit(1)`. Tas ir vienīgais rutīnas solis, kas iet **bez uzraudzības**, tāpēc izejas kods ir vienīgais signāls, kas eksistē — un pilna ingesta kļūme bija neatšķirama no labas dienas. Zaudējums nav atgūstams pēc dizaina: `get_pending_politicians(days=1)` nozīmē, ka tajā dienā neievāktais ekstrakcijas rindā vairs neatgriežas.

Tagad `step()` atgriež `bool`, `main() -> int` uzskaita kritušos, drukā `KOPSAVILKUMS: N/5 soļi OK` un nosauc kritušos vārdā; `ALL DONE` paliek tikai tīram skrējienam. Izņēmuma noķeršana palikusi ar nolūku — viena soļa kļūme nedrīkst apēst pārējos četrus, jo ingests ir daļēji atgūstams.

Tajā pašā failā atrasta **otra** tās pašas klases kļūme, ko sākotnējais ziņojums nesedza: 4. solis palaiž `ingest_vestnesis.py` kā apakšprocesu un atgrieza `{"returncode": …}`. Apakšprocess izņēmumu nemet, tāpēc kritis Vēstnesis atnāca kā parasts dict un solis nodrukāja `OK`. Tagad ne-nulles kods met `RuntimeError`, un `step()` semantika paliek viena („izņēmums = kļūme"). Vārti: `tests/test_morning_ingest.py` (7 testi, t.sk. apgalvojums, ka `sys.exit(main())` tiešām stāv failā — bez tā `main()` atgrieztais kods nekur neaiziet).

**2. Paneļa backlog rādīja nepareizu dienu.** `src/dashboard/views/backlog.py` abos vaicājumos lika `DATE(scraped_at, 'localtime')`, bet `scraped_at` ir **LV** kolonna (rakstīta ar `now_lv()` — `src/db.py`), tātad modifikators to pārvērta vēlreiz. Sekas ir divvirzienu: iepriekšējās dienas 21:00–24:00 partija ieskaitījās šodienā, bet šodienas vakara partija — tā, no kuras operators gatavojas ekstraģēt — no skata pazuda. Mērīts pret dzīvo DB (2026-07-31, neapskatītie dokumenti): panelis **558**, kontrole **295**; pēc labojuma abi 295.

Kāpēc suite bija akla: `tests/test_dashboard_backlog.py` sēja tikai 09:00–12:00 dokumentus, tāpēc ±3 h nekad nešķērsoja pusnakti. Jaunais uzvedības tests sēj 22:00 un 00:30 abās dienas pusēs un apgalvo **piederību, ne skaitu** — kļūdainais vaicājums šajā kopā atdotu tikpat rindu (2), tikai citas, tāpēc katram dokumentam ir sava `platform`.

**Klases vārti, nevis viens labojums.** `tests/test_timestamp_timezone_gate.py` parsē katru SQL literāli `src/**/*.py` ar `ast` (tātad daudzrindu un f-string vaicājumi atnāk veseli) un tur četras robežas: `'localtime'` tikai uz UTC kolonnas; šāds vaicājums nosauc UTC tabulu (`created_at` kā vārds dzīvo arī LV tabulās, ar to vien nepietiek); UTC kolonna nekad netiek lasīta kaili (2026-07-29 `briefs.py` virziens); un katrs atrastais `'localtime'` ir piesaistīts atpazītai formai — citādi vārti klusi izietu cauri paši sev.

Tas bija vajadzīgs, jo **abas testa vides ir aklas, katra pret savu virzienu**: LV zīmogu UTC kolonnā noķer tikai UTC CI (07-30), bet `'localtime'` uz LV kolonnas noķer tikai LV mašīna — UTC vidē modifikators ir no-op, tāpēc kļūdains kods uzvedības testu izietu. Avota koda vārti ir zonas ziņā neatkarīgi un tur abus virzienus vienlaikus.

## 2026-08-01 — `Claim.document_id` kontrakts saskaņots; provenances vārti `store_claim()`

Divi rakstīšanas ceļi nesa divus dažādus kontraktus. `src/models.py` deklarēja `document_id: int` (obligāts, ne-nullable), bet `db.store_claim()` pieņem `Optional[int]`, un Datu kontrakts #6 saka, ka `saeima_vote` claims glabā NULL. Sekas: `tools.store_claim()` meta `ValidationError` par **likumīgu balsojuma claim**, kamēr `db.store_claim()` identisku rindu pieņēma. Pretējā virzienā noteikumu neizpildīja **neviens** — `position`/`commentary` ar NULL `document_id` aizgāja cauri klusi, kaut tādam claim nav atgriezeniski pārbaudāmas provenances vispār.

Labots abās pusēs: modelī `Optional[int]` (obligāta atslēga, nullable vērtība — izlaists lauks joprojām ir kļūda), un noteikums izpildīts **vienā vietā** — `db.store_claim()`, jo tas ir vienīgais slānis, kas redz `claim_type`; modelis to apzināti nenes. Dzīvie dati ar noteikumu sakrīt precīzi: no 518 285 rindām visas 512 918 `saeima_vote` ir NULL, bet `position`/`commentary`/`program_promise` — 0 % NULL. Tātad vārti kodificē jau esošo invariantu, nevis ievieš jaunu ierobežojumu.

Pārmantots no `atmina_optimization_brief.md` §5 (2026-04-29 ārējā konsultācija) — vienīgais tā dokumenta ieteikums, kas dokumentācijas auditā vēl bija atvērts. Vārti: `TestStoreClaimProvenanceGuard` (7 testi).

## 2026-08-01 — Dokumentācijas audits: deploy noklusējums, 22 bojātas wiki lapas, tukši aģentu vaicājumi

Sistemātisks audits pār `CLAUDE.md`, `BACKLOG.md`, `wiki/`, saknes dokumentiem, aģentu promptiem un visām šķērsatsaucēm (7 paralēli auditori + 7 adversāri verifikatori; 86 atradumi izturēja verifikāciju). Trīs atradumi jau bija izgājuši ārpus dokumentācijas.

**1. `scripts/deploy.sh` noklusējums bija `--delete`.** Visi dokumentētie izsaucēji — `CLAUDE.md`, `commands.md` („nekad bez `--no-delete`"), prasmes, workflow — padeva `--no-delete`; **paneļa deploy poga (`src/dashboard/views/deploy.py`) nepadeva neko**, tātad tā vienīgā vietā repo palaida dzēšošu sinhronizāciju. Pēc šaurā rendera — kas šajā projektā ir norma — tā būtu novākusi visu, ko renders neizdeva, ieskaitot kurētos `finanses`/`statistika` kokus. Noklusējums apgriezts uz aditīvu; dzēšana ir skaidra `--delete` izvēle ar brīdinājumu; `--no-delete` paliek pieņemts kā no-op, lai neviens esošais izsaucējs nesalūztu. Vārti: `test_deploy_script_defaults_to_additive` + `test_dashboard_deploy_invokes_script_additively` — abi, jo katrs atsevišķi ir apejams. **Neizslēdzam `finanses`/`statistika` no rsync:** `_copy_curated()` tos apzināti ieklāj būvējumā tieši tāpēc, lai deploy tos saglabātu.

**2. 22 izsekotas wiki lapas saturēja NUL baitus** (20 `topics/`, 2 `parties/`), komitētas publiskajā repo kopš 2026-05-31; divām partiju lapām nebija palicis nekāds saturs. Cēlonis nav kodējums: frontmatter ir nevainojams UTF-8, un tad seko nepārtraukts NUL gabals līdz faila beigām — apraujoša rakstīšana, kur failu sistēma reģistrēja jauno garumu, bet asti neizskaloja. **Kāpēc tas nepašārstējās divus mēnešus:** NUL dekodējas kā derīgs UTF-8, tāpēc `_parse_frontmatter` to atdeva kā parastu body, un `_update_page` „saglabā body" līgums to uzticīgi ierakstīja atpakaļ katrā sinhronizācijā. Labojums ir `_sanitize_body()` **lasīšanas** pusē, tāpēc bojājums tagad pašārstējas; tukšs body pēc attīrīšanas atgriež svaigi uzbūvēto noklusējumu, tā ka abas partiju lapas atguva biedru sarakstus no DB.

**3. Wiki lints deva viltus zaļo gaismu.** Tas pārbaudīja 4 no 11 apakšmapēm un lapu saturā neskatījās nekad — tieši tāpēc punkts 2 palika nepamanīts, kamēr `wiki/index.md` publicēja „0 broken links", un `CLAUDE.md` liek katrai sesijai lasīt index pirmo. Pievienota `corrupt_page` pārbaude pār **visu** glabātuvi. Princips, kas te iekodēts: **checkeris, kura zaļā gaisma nav pierādījums, ir sliktāks par nekādu checkeri** — tas aktīvi aptur meklēšanu.

**4. Trīs aģentu prompti saturēja vaicājumus, kas neatgriež neko.** `@contradiction-hunter` Step 0 filtrēja pēc `claim_type='vote'`, kamēr īstā vērtība ir `saeima_vote` — mērīts pret dzīvo DB: **pūls 0 pret 100**, t.i. aģenta primārais solis (balsojums pret retoriku) nevarēja darboties. Tā paša prompta koalīcijas tabula bija iesaldēta 2026-04 sastāvā un apgriezta **trīs** partijām (PRO opozīcijā; NA un AS koalīcijā) — tā kā visa FP filtrēšana griežas ap „vai tā bija koalīcijas disciplīna", stāva tabula neapzīmē partiju nepareizi, tā **apgriež verdiktu**; aizstāta ar `get_coalition_map()` izsaukumu (invariants #10). `@mentions-monitor` vaicāja `documents.mention_target_id` — kolonnas nav, saite dzīvo `document_politicians` junction tabulā.

**5. `wiki/operations/daily-routine.md` mācīja auto-publicēt pretrunas.** Fails ir pirmā saite `operacijas.md` Rutīnas tabulā, tātad sesija nonāk tur pirms `/dienas-rutina` prasmes, un tas rakstīja `UPDATE contradictions SET reviewed=1, confirmed=1` vienā rindā. `reviewed=1` („@devils-advocate izskatīja") un `confirmed=1` („atmina to publiski apgalvo") ir divi dažādi lēmumi, un otro pieņem operators — eskalācijas noteikums 3 to tieši aizliedz. Tajā pašā failā: mantotais temats `dienas pārskats` pareizā `dienas analīze` vietā (forma, ko `src/briefs.py:41` jau nosauc par notikušu kļūdu — DB glabā 47 pārskatus zem nepareizās pret 68 zem pareizās), trūkstošs operatora publicēšanas solis un pilnais renders pretrunā paša faila 10. solim. Failam virsū uzlikta precedences rindkopa: **prasme ir kanoniskā, šis ir atsauces detaļas.**

**6. Divi `CLAUDE.md` noteikumi nebija izpildāmi, kā rakstīts.** Eskalācijas noteikums 2 prasīja „store with needs_review" — tāda parametra nav, un `store_claim()` lieko atslēgu klusi izmet, tāpēc šādi „atzīmēts" claim nonāk DB pilnīgi pārliecināts; īstais mehānisms ir `NEEDS_REVIEW:` prefikss `reasoning` laukā. Noteikums 8 neprasīja pārembedēšanu pēc `claims.topic`/`stance` roku labojuma, kaut `store_claim()` embed `f"{topic}: {stance}"` — kails `UPDATE` atstāj `claim_vectors` ar vecā teksta vektoru, un nekas neizmet kļūdu.

**7. Repo svars.** `wiki/dailies` (89 faili) un `wiki/log-ingest` (4 faili, 448 KB) izņemti no indeksa, faili paliek diskā. Abi ir operatora virsmas, kuru saturs dzīvo citur (pārskati DB — 117 rindas pret 103 failiem; ielādes vēsture šajā CHANGELOG). Dailies gadījumā tas tikai **pabeidza** `05ade5c0` sākto: tas commits izņēma tikai divus nejauši pievienotos failus un uzlika ignore noteikumu, bet 89 aprīļa–jūlija failus nesasniedza, tāpēc repo dzīvoja pusstāvoklī — jaunie neizsekoti, vecie izsekoti un joprojām rediģēti. Dzēsti arī divi 2026-04-29 plānošanas dokumenti (806 rindas); to vienīgais vēl atvērtais ieteikums pārnests uz BACKLOG (`Claim.document_id` Pydantic modelī noraida likumīgu `saeima_vote` claim).

Detalizēts atradumu saraksts ar failu/rindu atsaucēm: `docs/audits/2026-08-01-dokumentacijas-audits.md`. Divi audita apgalvojumi izpildes gaitā tika atspēkoti un netika ieviesti — sk. tā paša faila statusa bloku.

## 2026-08-01 — `AGENTS.md` dzēsts (operatora lēmums)

Audits konstatēja, ka `AGENTS.md` (pēdējoreiz atjaunots `b7d50a80`, 2026-06-28) ir novecojis par **8 verificētām pretrunām** ar `CLAUDE.md`, un tas nav parasts dokumentācijas dreifs: `AGENTS.md` ir de-facto starpharness faila nosaukums, ko Codex, Cursor, Aider un Gemini CLI ielādē **automātiski**. Svešs izpildītājs tāpēc saņēma tieši nepareizos noteikumus.

Konkrēti, ko tas mācīja: „claims without `source_url` are silently dropped **at the DB layer**" — tieši tas formulējums, kura dēļ Datu kontrakts #2 tika pārrakstīts (patiesā vieta ir `save_analysis()` validācija, un `failures` saraksts ir vienīgā vieta, kur zudums parādās, tāpēc šis teikums ved taisni T3 slazdā); „31 canonical groups", kamēr `TOPIC_GROUPS` ir 32; Datu kontrakta #1 Pydantic lauki, kas ir tombstone'oti kopš politracker tīrīšanas; `.Codex/agents/*.md` kā „canonical execution" ceļš uz mapi, kuras nav; komandu bloks viss kailā `python` (dokumentētā daļēja-ieraksta bīstamība: `store_vote()` commito pirms claim ģenerēšanas); un `bash scripts/deploy.sh` **bez** `--no-delete`, kamēr `scripts/deploy.sh:31` noklusējums toreiz bija `DELETE_FLAG="--delete"` — t.i. dokumentēta komanda, kas noslaucītu kurētos `finanses`/`statistika` kokus no dzīvās vietnes. *(Pats skripta noklusējums salabots tajā pašā dienā — sk. ierakstu augstāk; toreiz tas vēl bija dzēšošs.)* Turklāt failā nebija **nevienas** Standing Decision, **neviena** slazda T1–T14 un neviena eskalācijas noteikuma.

**Lēmums: dzēst, nevis atjaunot.** Operatora pamatojums — fails tika izmantots tieši vienu reizi, tāpēc uzturēšanas izmaksas nav attaisnotas. Vispārīgā mācība, kas ierakstīta BACKLOG § Ne-darīt: **novecojis starpharness fails ir bīstamāks par tā neesamību** — trūkstošs fails liek lasītājam meklēt, bet nepareizs fails tiek ielādēts klusi un izskatās autoritatīvs.

- Pārbaudīts pirms dzēšanas: uz `AGENTS.md` neatsaucās **nekas** — ne CI, ne `.claude/`, ne `pyproject.toml`, ne `scripts/`, ne wiki. Karājošos norāžu nav.
- `wiki/operations/portability.md` — dokuments, uz kuru `CLAUDE.md` sūta svešus harness — dabūja rindu, kas fiksē dzēšanu (lai `AGENTS.md` meklētājs zina, kur iet), un tajā pašā gājienā izlabots novecojis slazdu diapazons **T1–T13 → T1–T14** (T14 = procedurālais balsojums kā pozīcija). Tas bija atsevišķs audita atradums un skāra tieši to pašu auditoriju.

## 2026-08-01 — Deploy SSH atslēga rotēta; noplūdes cikls slēgts

Noplūdes labošanas pēdējais solis: sanitizācija izņem vērtību no repo, bet nedara neko ar to, kas jau nokopēts. Atslēga tāpēc rotēta.

- **Jauna ed25519 atslēga, ģenerēta lokāli** (`atmina-deploy`, `chmod 600`, bez paroles — deploy iet neinteraktīvi), importēta cPanel ar TUKŠU privātās atslēgas lauku. Vecā (`testtt`, no aprīļa pirmuzstādīšanas) dzēsta pēc tam, kad abi ceļi bija pārbaudīti ar jauno.
- **`DEPLOY_SSH_KEY` `.env.deploy` failā** norāda uz jauno atslēgu 8.3 īsajā ceļa formā — `rsync -e` vērtību sadala pa atstarpēm, un mājas mapē ir atstarpe. `~/.ssh/config` `IdentityFile` arī pārslēgts.
- **Verificēts ar apieto konfigurāciju** (`ssh -F /dev/null`): vecā atslēga → `Permission denied`, nesaistīta cita projekta atslēga → `Permission denied`, jaunā → autentificējas. Servera `authorized_keys` satur tieši vienu atslēgu, un tās pirkstu nospiedums sakrīt ar jauno.
- **Rotācijas recepte + tās viltus-pozitīvais slazds ierakstīti `wiki/operations/deploy.md`.** Slazds ir vērtīgāks par pašu rotāciju: pārbaude ar `ssh -i <vecā> -o IdentitiesOnly=yes` **uzrādīja, ka vecā atslēga joprojām strādā**, un tas bija nepatiesi — `IdentitiesOnly` ierobežo līdz identitātēm no konfigurācijas VAI komandrindas, un config Host blokā jau bija jaunā atslēga, tāpēc katrs mēģinājums autentificējās ar to. Tas pats tests „apstiprināja" arī pilnīgi nesaistītu atslēgu, kas ir pazīme, ka tests mēra ne to. Turpmāk rotāciju pārbauda pēc servera `authorized_keys` satura, ne pēc klienta puses mēģinājuma.
- **Paliek ārpus mūsu kontroles:** hosts un cPanel lietotājvārds bija publiski ~3,5 mēnešus, tāpēc paroles/webmail pieteikšanās mēģinājumi pret zināmu-derīgu kontu paliek iespējami neatkarīgi no atslēgas. Konta pārsaukšana ir Namecheap atbalsta jautājums.

## 2026-08-01 — `scripts/check_output.py`: uzbūvētais koks beidzot tiek validēts

Sistēmiskā audita sakne slēgta. Līdz šim **neviens solis nepārbaudīja to, ko renders uzrakstīja**: `check.sh` uzrenderēja vietni un neizlasīja no tās nevienu baitu, `deploy.sh` vienīgais priekšnosacījums bija „vai mape eksistē". Tā kā `deploy.sh --no-delete` ir standarta režīms, viss sabojātais, kas nonāca serverī, tur palika bez atgriezeniskā ceļa un bez detektora.

- **Jaunais rīks** apstaigā visus 887 uzbūvētos HTML, izšķir katru `src=`/`href=`/`og:image`/`twitter:image` pret koku (ārējie hosti, `mailto:`, `tel:`, `data:`, tīri fragmenti — ārpus tvēruma) un diffo `sitemap.xml` `<loc>` kopu pret emitēto lapu kopu **abos virzienos**. Pirmais palaidiens: **63 robi**. Pēc labojumiem: tīrs, 46 197 pārbaudītas iekšējās atsauces, sitemap 886 ↔ 886.
- **Pieslēgts abās vietās:** `check.sh` 4. solis un `deploy.sh` priekšpārbaude, kas **atsakās sūtīt** koku ar salauztām atsaucēm (avārijas izeja `--no-output-check`, dokumentēta kā tāda). Apzinātie izņēmumi dzīvo `scripts/output_check_allowlist.txt` ar obligātu iemeslu katram.
- **`tests/test_check_output.py` (9 testi)** — rīks pats ir vārti, tāpēc katrs tests apgalvo, ka konkrēta lauzta forma TIEK noķerta, ne tikai to, ka tīrs koks iet cauri. Vārti, kas nevar krist, ir tieši tā klase, kuras dēļ šis viss tapa.

Ar to salaboti (visi verificēti ar atkārtotu renderi + rīka palaidienu):

- **`likumi` vertikāle nebija `sitemap.xml`** — `_generate_sitemap()` nekad nesaņēma likumu sarakstu, tāpēc `likumi.html` + 33 lapas bija emitētas un meklētājiem neredzamas. Pievienots `law_slugs` parametrs ar to pašu patiesības avotu, ko `laws.py` (`wiki/laws/*.md` stems bez `likumi.md`).
- **17 mirušas saites `likumprojekti` lapās** — iesniedzēju vaicājumam nebija `relationship_type` filtra, bet politiķu renderis `inactive` cilvēkiem lapas neģenerē (Jātnieks 7, Dzintars 6, Štekerhofs 3, Brante 1). Tagad vaicājums nes `has_page`, un veidne neaktīvam iesniedzējam emitē vārdu bez saites — **rinda paliek**, jo caurskatāmības ierakstam nedrīkst pazust, kas likumprojektu iesniedza.
- **`analizes/vad-2026.html` divas saites** — `deklaracijas.html` → `deklaracijas-2026.html` (frontmatter `url:` atslēgu renders nekad nelasīja, slug nāk no faila nosaukuma; atslēga izmesta no abiem failiem, lai nākamā kurētā analīze to nekopētu), un publiskā lapa vairs nesūta lasītājus uz **privāto** repo — `atmina` → `atmina-lv`.
- **Dienas render recepte** ieguva `static` domēnu visos četros nesējos (sk. iepriekšējo ierakstu).

Palika atvērts (BACKLOG § Publiskā vietne): abu 2026-05 pārskatu zudušie attēli + apgrieztā `/audit-integrity` 7. pārbaude; `[[wikilinks]]` sintēzes lapā; un **jauns atradums, ko audits nepamanīja un ko rīks atrada pirmajā palaidienā** — pārskatā #184 divi iekšēji URL rakstīti bez `.html`, tāpēc dzīvajā vietnē ved uz 404.

## 2026-08-01 — Deploy akreditācijas datu noplūde slēgta; repo audits; BACKLOG konsolidācija

Lasāms-tikai audits pār wiki/backlog/dokumentiem/kodu/repo higiēnu/DB (6 dimensijas, katra adversāri verificēta) + tā pirmie labojumi.

- **NOPLŪDE SLĒGTA: `wiki/operations/deploy.md` nesa īsto `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_PATH`** — hostu, cPanel lietotājvārdu un mājas ceļu — kopš `7c6a7c17` (2026-04-17). `wiki/operations` ir `docs/funding/repo-sync.md` **NEGRIEZT** sarakstā, tāpēc tas aizgāja katrā publiskajā sync un bija lasāms publiskajā spogulī ~3,5 mēnešus. Sakne ir strukturāla, ne neuzmanība: obligātais pirms-sync grepu kontrolsaraksts (uzņēmuma nosaukums / personīgais e-pasts / scraper handļi / Windows ceļa forma) šo klasi **nekad neskatījās**, tāpēc tas gāja cauri tīrs visu to laiku — pēdējais 07-31 sync ieraksts to apliecina. Sanitizēts uz `.env.deploy.example` vietturiem; īstās vērtības paliek tikai `.env.deploy` (gitignorēts) un lokālajā `~/.ssh/config`. **Vārti, lai neatkārtojas:** `tests/test_no_deploy_credentials.py` (lasa `.env.deploy`, prasa 0 hitu `git ls-files` kokā; skipojas, kad faila nav → CI zaļš; verificēts, ka tas KRĪT pret pirms-labojuma HEAD un iet cauri pēc) + jauns punkts `repo-sync.md` kontrolsarakstā, kas grepo `$DEPLOY_HOST`/`$DEPLOY_USER`/`$DEPLOY_PATH` un commit-autora e-pasta adresi. Kļūdas ziņojums apzināti nosauc failu un atslēgu, **ne vērtību** — citādi noslēpums nonāktu CI logā. Spogulis ir viens squashed force-push commits, tāpēc nākamais sync izdzēš vērtību arī no publiskās vēstures; **atslēgas rotācija paliek operatora solis — sanitizācija bez rotācijas nav labojums.**
- **BACKLOG konsolidēts pēc paša faila līnijas-3 kontrakta** („Pabeigtais darbs dzīvo CHANGELOG; šis fails ir TIKAI atvērtais"). Mērījums pirms: 15 pabeigti ieraksti + 4 `(vēsturiskais konteksts)` bloki = **92 no 356 rindām (25 %)**. Taksonomija bija sabrukusi: **8 no 10 ierakstiem sadaļā „Render / veiktspēja" nebija par render** (NVO 33. tēma, `NEEDS_REVIEW`, diakritiku vārti, nogriezti avoti, Valsts kontroles kolīzija …), bet „Shēma / DB" saturēja tikai pabeigtu darbu. Jaunums: sadaļa **`## Ne-darīt`**, kas savāc kopā līdz šim izkaisītos apzināti-noraidītos lēmumus — tie ir šī repo biežākā viltus-pozitīvo klase (audits pats atrada 6 „atradumus", kas izrādījās jau izlemti).
- **Divi ieraksti, kas dzīvoja TIKAI backlogā, pārcelti šurp pirms griešanas** (bez tā tie būtu pazuduši):
  - **Telegram pārskata topic diverģence (atrisināts 2026-07-25).** Telegram ceļš meklēja `dienas pārskats {date}`, ko neviens neraksta, tāpēc kopsavilkuma punkti bija vienmēr tukši — bez kļūdas, jo nepareiza topic virkne vienkārši atgriež neko (klusās-neveiksmes klase). Fix: `src/briefs.py` `DAILY_BRIEF_TOPIC_PREFIX` + `daily_brief_topic()`, ko lieto gan Telegram vaicājums, gan `_BRIEF_DAY_CLAIM_SQL`; 4 testi `tests/test_brief_topic_form.py`.
  - **`opponent_id` pārsaukšana — NORAIDĪTA pragmatiski.** Kolonna dzīvo 6 pamattabulās, 363 vietās 37 `src` failos, 37 vietās aģentu promptos/workflow, testos, wiki un vēsturiskajos `data/rollback_*.sql` (kas pēc pārsaukšanas vairs nedarbotos); idempotences trijnieks CLAUDE.md nosaukts vārdā `(opponent_id, source_url, topic)`. Ieguvums tīri kosmētisks — neviens ārējs lietotājs vārdu neredz. Uzskatām par etimoloģiju (kā `politracker.db` → `atmina.db`). Tagad dzīvo BACKLOG § Ne-darīt.
- **Matcher kolīziju per-gadījumu vēsture pārcelta šurp** (BACKLOG ierakstā „Kučinskis bare-surname" bija 22 rindas, no kurām atvērta darba **nulle** — pārbaudīts, palaižot `scripts/eval_matcher_collisions.py --quick`: B2D2H `fp_links=1`, un tas vienīgais ir Bērziņa dziedātāja klase, kurai ir savs ieraksts). Slēgtie gadījumi: Matīss↔Māris Kučinskis (id=105, doc 56077) · Oskars↔Viktors Valainis (id=25) · Alberts/Rolands↔Didzis Šmits (id=150) · Uģis↔Jānis Citskovskis (id=233) · Isaks del Toro↔Arigo Toro (id=234) — visi piecu klasi tur **B2+D2+H kods** kopš 07-27, `negative_patterns` nav vajadzīgi; Baškortostāna↔Baško (id=30, `data/*basko_baskortostana_negpattern_2026-07-16.sql`) · Kolumbija/Kolumbus↔Kols (id=24, `data/fix_kols_kolumbija_negpattern_2026-06-29.sql` + `data/*audit_integrity_falsejunctions_2026-07-07.sql`) · Matīss↔Raimonds Čudars (id=162, `data/*cudars_matiss_negpattern_2026-07-24.sql`) — šie ar patterniem; Lāce↔„Lācis" (id=158) — 5 junctions dzēsti 07-07, kailais pattern apzināti NAV pievienots („Lācis" ir īsts uzvārds), un D2 vārdu-robežu kods to klasi tagad tur bez tā.
- **Audita pilnais atradumu saraksts** (48 verificēti + 7 no pilnīguma kritiķa) ar pierādījumiem un verifikatora argumentāciju — sesijas artefakts, nav commitots; kopsavilkums operatoram sniegts sesijā. Galvenie vēl neizlabotie: publicētie `about.html` korpusa skaitļi noveco katru dienu (dienas render recepte izlaiž `static` domēnu), 11 nodiakritizētas nostājas dzīvajā vietnē, 2 pārskatu `og:image` 404, 4 087 dublēti `saeima_vote` claims (Datu kontrakts #4b), un sistēmiskā sakne — **neviens solis nevalidē uzbūvēto `output/atmina/` koku** (`check.sh` to uzrenderē un nepaskatās; `deploy.sh` pārbauda tikai, vai mape eksistē).

## 2026-07-31 — Divas jaunas entītijas, `NEEDS_REVIEW` triāža un rutīnas labojumi; nedokumentēta konvencija gandrīz kļuva par trešo marķieri

Dienai nebija sava ieraksta; šis uzrakstīts 2026-08-02, un tā avots ir septiņi tās dienas commiti. Saturs: divas jaunas izsekotās entītijas, `NEEDS_REVIEW` rindas pilna triāža un vakara rutīnas labojumi.

- **Valsts kontrole iesēta kā institūcija (id=241, `d37390a4`).** `relationship_type='organization'`, `party=NULL`, X konts `@VKontrole` (`first_party`), verificēts dzīvi caur twikit. `name_forms` uzskaitītas ar roku, jo institucionālam slotam matcher locījumus neģenerē; četras daudzvārdu formas nosedz visus 869 lielā burta `Valsts kontrol*` gadījumus korpusā. **Abreviatūra „VK" apzināti izlaista** — korpusā ir 312 atsevišķi „VK" tokeni, un tajos dominē Valsts kanceleja, ne Valsts kontrole (T1 substring bumba, ≤4 rakstzīmju karantīna). Rescan pār 396 dokumentiem deva 334 sasaistes (49 `subject`, 285 `mentioned`), no kurām divas norādīja uz ārvalstu revīzijas iestādēm — „Spānijas Valsts kontrole" (doc 36152) un „Krievijas Valsts kontroles" (doc 50888) — un tika noņemtas ar `data/{fix,rollback}_vk_foreign_audit_junctions_2026-07-31.sql`. `negative_patterns` šai klasei neder: tie noraidītu VISU dokumentu, un tad pazustu doc 20494, kurā blakus Somijas/Igaunijas piemēriem ir 10 tiešas Latvijas Valsts kontroles atsauces. Pareizais risinājums — ģenitīva ģeonīma prefiksa veto `src/matcher.py::_occurrences` līmenī — pierakstīts BACKLOG.
- **Anastasija Tetarenko-Supe iesēta (id=242, `c35d51de`).** Latvijas Žurnālistu asociācijas valdes priekšsēdētāja, `relationship_type='journalist'`, `party=NULL`; loma verificēta pret LETA 27.03. rakstu korpusā, X konts `@te_anastasija` verificēts dzīvi. Formas atkal ar roku (žurnālista slots matcher acīs ir institucionāls): „Tetarenko" vārda robežu režīmā noķer visus salikteņa locījumus, jo aiz tā ir defise. **Apzināti izlaisti divi:** „Supe" (4 rakstzīmes, T1 karantīna) un „Anastasija" — pirmvārds vien sader ar Anastasiju Šubinu, un pirmvārds formās neiet nekad. Rescan pār 25 dokumentiem: 40 sasaistes. Pierakstīts arī, ka konts pēc pašas bio ir privāts viedoklis, ne LŽA institucionālā balss — šis ieraksts asociāciju kā organizāciju neaizvieto.
- **`NEEDS_REVIEW` pilnā triāža: 94 izskatīti, 3 dzēsti, vienam mainīta tēma (`a3513074`).** Lielākā daļa bija leģitīmas tēmu robežas izvēles un palika neskartas; dzēsti tikai tie, kas pārkāpj repo noteikumus. #555673 (Lapsa, salience 0.85, visaugstākā kopā) — apgalvojums par nozagtām vēlēšanām ekstraktēts tikai no retvītota virsraksta, `quote` NULL, t.i. truncated-stub noteikuma pārkāpums. #555795 (Lapsa) — nenosaukts ministrs plus nepārbaudīts apgalvojums par identificējamu personu (eskalācijas noteikums #1, #555693 precedents). #555797 (Vītols) — „Rail Baltica" dokumentā neparādās vispār, referents izsecināts no pavediena, un tā paša pavediena cits tvīts tajā pašā dienā tika noraidīts tieši šī iemesla dēļ. Tēma mainīta #555776 (Krištopans, `Rail Baltica` → `Budžets un finanses`) **ar embedding pārrēķinu** — `store_claim` iegulst `f"{topic}: {stance}"`, tāpēc kails `UPDATE claims SET topic` atstātu `claim_vectors` ar veco vektoru. Salaboti arī divi `reasoning` teksti (#555776, #555782), kuros palikušais „izvēlējos X" rādīja citu tēmu, nekā ierakstīta DB — tieši uz `reasoning` balstās `@quality-reviewer`. 280 rindu `scripts/fix_needs_review_triage_2026-07-31.py` + 35 rindu `data/rollback_needs_review_triage_2026-07-31.sql`.
- **Triāža gandrīz radīja trešo marķieri — dienas īstais atradums (`224102e5`, `eb4a9ad1`).** Sākumā tā ieviesa paralēlu `PĀRSKATĪTS <datums>:` marķieri, nepamanot, ka repo kopš 2026-04-28 lieto `REVIEWED <datums>:` (62 rindas); abas jaunās rindas pārliktas uz `REVIEWED`. Trīs marķieri nozīmētu, ka jebkurš `LIKE` vaicājums klusi izlaiž daļu rindu. Sakne nav neuzmanība — **konvencija nebija dokumentēta nekur**: ne aģenta promptā, ne CLAUDE.md, ne wiki. Tagad tā ir `.claude/agents/claim-extractor.md` protokolā kopā ar diviem noteikumiem: ekstraktors pats `REVIEWED` neraksta (to izlemj cilvēks un piemēro caur `scripts/fix_*.py` ar pāra rollback), un tēmas maiņa PRASA embedding pārrēķinu. Blakus izmērīts, kāpēc atvērto skaitlis nav trauksmes signāls: sweep noticis tieši vienu reizi (2026-06-13, 56 claims), 89 atvērtie visi radīti 07-20 vai vēlāk, bet robežu aprakstošu `reasoning` īpatsvars ir stabils kopš jūnija (21 % → 23 %). Mainījusies ir marķēšana, ne ekstrakcijas kvalitāte.
- **33. tēma „NVO un pilsoniskā sabiedrība" atlikta, ar pārvērtēšanas slieksni (`45a85d36`).** Triāža atklāja, ka NVO finansējuma stāsts ir izkaisīts pa 8 tēmām (30 pozīcijas, vismaz 12 politiķi, nepārtraukti kopš 07-22) un tāpēc tēmu tabulās neparādās nekad — četri neatkarīgi ekstrakcijas aģenti to pamanīja un katrs izvēlējās citu grupu. **Operatora lēmums: nepievienot tagad** — 30 pozīcijas ir uzkrājušās tikai 10 dienās, tātad tas var būt priekšvēlēšanu uzliesmojums, un 32 tēmu saraksts ir load-bearing pārāk daudzās vietās, lai to bezsāpīgi atgrieztu. Slieksnis: pēc vēlēšanām vai ~50 pozīcijas. Starpversija (noteikums promptā, ka NVO pozīcijas iet uz `Valsts pārvalde`) apzināti noraidīta. Riska piezīme, kas lēmumu tur: `normalize_topic()` nezināmas tēmas laiž cauri neizmainītas, tāpēc vienīgie vārti pret nejauši radītu 33. tēmu ir prompta noteikums — 07-31 mērījums rāda 5 053 pozīcijas, 32 tēmas, 0 nekanonisku.
- **Vakara rutīnas trīs labojumi ar pāra rollback (`6be2043d`).** Visi trīs jau bija piemēroti un publicēti 07-31 pārskatā (piezīme #396); commits versionē to atceļamību, kā prasa noteikums par roku migrācijām. (a) claim #555872 — debitīvs „vēstījumus jābalsta" → „vēstījumi jābalsta"; atklāts tāpēc, ka `@brief-writer` pārskatā uzrakstīja pareizo formu, kamēr DB palika nepareizā, t.i. **profila lapa un pārskats būtu rādījuši atšķirīgu tekstu**. (b) claim #555865 — „ekspektācijām" → „augstākām gaidām" plus substantivizācijas pārfrāze; abi ir MŪSU teksts, ne citāts. Abiem labojumiem pārrēķināts `claim_vectors`, un rollback atjauno baitu identisku veco vektoru. (c) `tracked_politicians` id=13 Jānis Hermanis: `party` NULL → MMN, `relationship_type` neutral → tracked (T6 klases novecojis lauks; divi neatkarīgi pierādījumi — viņa paša 2026-06-25 paziņojums doc 58693 / claim #532352 un CVK SV2026 kandidātu reģistrs). **NB nākamajām sesijām: DB ir divi Hermaņi un abi ir MMN** — id=13 Jānis (`@J_Hermanis`) un id=29 Alvis (`@AlvisHermanis1`); vienāda partija NAV atribūcijas kļūdas pazīme.
- **Blakus tajā pašā commitā — BACKLOG cēloņa korekcija.** Pārskata skeleta ieraksts apgalvoja, ka tēmu tabulas izlaiž `party IS NULL` runātājus. Filtrs ir cits: `relationship_type NOT IN ('journalist','influencer','neutral','inactive','organization')`; partijas trūkums bija tikai korelācija, un skartas ir arī entītijas ar aizpildītu `party` lauku. 07-31 tas izmeta 11 no 50 dienas pozīcijām, tostarp visas 4 Valsts kontroles — tieši to entītiju, kuras dēļ tā tajā pašā dienā tika iesēta. Blakus pierakstīts, ka 7 dienu loga izslēgšana ir pareiza uzvedība, ne šā defekta daļa. Atvērts: 7 jau publicēti pārskati klasificē Jāni Hermani kā neitrālu runātāju pēc 06-25 — Šmita klases retroaktīvais lēmums.

## 2026-07-30 — `political_tensions.created_at` = UTC visos lasījumos; 07-29 pārskats pēc Claude outage

Sesija atsāka 2026-07-29 vakara rutīnu, kas bija apstājusies 7. solī (Claude outage, vairāki restarti). Divas atrastās kļūdas nav ražotas šeit — tās ir outage paraksts:

- **Spriedze #175 bija ierakstīta ar tiešu INSERT, apejot `store_tension()`** (`data/{fix,rollback}_tension175_source_url_2026-07-30.sql`). Tāpēc nenostrādāja divi vārti: (a) `source_url` validācija pret `documents` — glabātais tvīta status ID neparādījās NEVIENĀ dokumentā (Švinkam 07-29 tikai doc 75948 un 75949), tas ir tieši tas halucinēta-ID gadījums, ko funkcija ķer; (b) `created_at` konvencija — rindā bija `now_lv()` LV zīmogs UTC kolonnā. Audits pār visām 157 spriedzēm: **#175 ir vienīgā** ar nesekojamu `source_url`, tātad vienreizējs artefakts. Saturs bija pareizs (balstīts claim #555782), tāpēc citāts pārlikts uz īsto dokumentu, nevis dzēsts.
- **`political_tensions.created_at` lasījumu konvencija salāgota** (`5874e8c8`). Kolonna paļaujas uz `DEFAULT CURRENT_TIMESTAMP` (UTC), pretstatā `claims`/`context_notes`, ko `now_lv()` raksta LV laikā. `src/routine.py` to lasīja pareizi ar `'localtime'`, bet `src/briefs.py` trijos vaicājumos lasīja kaili → logā **21:00–23:59 UTC (= 00:00–02:59 LV), t.i. tieši vakara rutīnas logā**, viena un tā pati spriedze varēja būt pārskatā par vienu dienu un „neesoša" statusā par otru. Labots: 3 predikāti `briefs.py` + publiskais datums `render/tensions.py`, konvencija dokumentēta pie pašas kolonnas `src/schema.sql`, `brief-writer.md` datu piemērs, un `tests/test_briefs.py::TestTensionDayBoundaryTimezone` fiksē abas puses (testi nepieņem neko par mašīnas TZ — abas dienas iegūst no SQLite un skipo, ja tās sakrīt, tāpēc UTC CI tos neizmet kā viltus sarkanos). Tas slēdz [BACKLOG § Timestamp glabāšana](../BACKLOG.md) (1) punkta koda sakni un **atsauc** tā agrāko īstermiņa padomu („spriedžu `created_at` uzstādīt uz rutīnas dienu") — tas tagad nozīmētu tieši to LV-zīmoga formu, kas rada defektu.
- **Slazds, ko noķēra esošais tests:** `render/tensions.py` LV datumu ņem no SQL, bet to pašu vārdnīcu sarakstu `render/links.py:403` iesērijo saites lapas inline JSON blokā, tāpēc lieka atslēga mainīja lapas baitus un nogāza `test_saites_index_byte_identical`. Atslēga tagad tiek noņemta ar `pop()` pirms saraksta nodošanas tālāk.
- **Pārskats #387 (07-29) uzrakstīts, apstiprināts un publicēts:** 26 159 zīmes, attēls #237 (Rail Baltica / „24 miljardi eiro"), visi 4 varianti + live HTTP 200 verificēti. Skeleta pārbūve pēc datu labojuma mainīja tieši vienu rindu (spriedzes saiti).
- **Pārskata identitāte = subjekta datums, ne `created_at`** (operatora pasūtīts uzreiz pēc atklāšanas). Soļi 7 un 8 skaitīja pēc `created_at`, tāpēc 07-29 statuss rādīja abus zaļus, kamēr 07-29 pārskata nebija: #383 aptver 07-28, bet bija saglabāts 07-29 plkst. 00:04. 8. solis pie tam nosauca svešu pārskatu — „Featured image apstiprināts (brief 383)" — jo `ORDER BY id DESC LIMIT 1` pār `created_at` logu paņēma kaimiņa rindu un pārbaudīja TĀS attēlu. **Tie divi ķeksīši bija vienīgais, kas slēpa outage nogalinātu rutīnu.** Spoguļpuse: pēc pusnakts pabeigta rutīna rādītu ✗, lai gan pārskats ir (07-29 tas bija 11 minūšu attālumā). Jauns kopīgs helperis `src/briefs.py::brief_subject_date()` (topic → H1 → `created_at` tikai mantotajām rindām), ko tagad lieto gan `routine.py` soļi 7/8, gan `src/render/blog.py` slug atvasināšana — abas puses lasa vienu identitāti un nevar atšķirties (blog uzvedība nemainīta; baitu-identitātes testi to notur). 4 testi `tests/test_routine.py::TestBriefIdentityIsSubjectDate`, no kuriem 3 krīt bez labojuma.
- **`/audit-integrity` 10. čeks: provenance, kas neatrisinās + ar roku rakstītu rindu paraksti.** Četri validēti vaicājumi (visi 0 pēc #175 labojuma — tīra bāzlīnija): spriedzes `source_url`, ko nenes neviens dokuments; claim, kas citē citu URL nekā savs provenance dokuments; `saeima_vote` claim bez atbilstoša `saeima_votes.url`; LV zīmogs UTC kolonnā. Pēdējam pierakstīts godīgs ierobežojums — salīdzinājums pret UTC-tagad ķer tikai pēdējo 3 stundu zīmogu, tāpēc tas ir tās pašas sesijas signāls, ne vēsturisks audits (stundas heiristika nešķir: 10 spriedzēm ir ≥21:00, un visas, izņemot #175, ir parasti UTC vakara ieraksti).
- **CLAUDE.md:** divi jauni schema invarianti (timestamp konvencijas nav vienotas + pārskata identitāte) un viens Working Convention — rakstīt caur `store_*()`, jo validācija dzīvo funkcijā, ne shēmā, un tiešs INSERT to klusi nomet.
- **Atlikums BACKLOG-ā, ne labots:** konteksta blokos nosaukti audience runātāji bez avota saites; kaili claim ID tendenču piezīmēs #384–386; `claim_vectors` bāreņi.

## 2026-07-29 — Politracker tīrīšana, Bergholca seed, matcher paliekas, UI sīkumi

Operatora pasūtītā backlog pakete (viena sesija, visi datu labojumi ar pārī rollback):

- **Politracker mantojuma 1. kategorija izmesta:** `oppo_briefs` + `mention_classifications` (abas 0 rindu kopš 2026-04-06 pivota) DROP (`data/{migrate_drop,rollback_drop}_politracker_tables_2026-07-29.sql`); social-aģenta highlights attack-zars izgriezts (`candidates.py`/`cli.py`/`drafters.py` — pillar tagad tension-only), testi pārrakstīti, `preflight.py` required-saraksts + `src/schema.sql` atjaunoti, schema-dump baseline pārģenerēts. **CLAUDE.md Datu kontrakts #1 → tombstone** (numerācija saglabāta). `scripts/migrate_db.py` apzināti neaiztikts (vēsture).
- **Edgars Bergholcs iesēts (id=240):** Rīgas domes Pilsētas attīstības komitejas priekšsēdētājs. Partija **Apvienotais saraksts** — preses "(NA)" doc 74856 izrādījās kļūdaina etiķete (riga.lv oficiālais profils: frakcija AS; korpusa doki 16468/23713 raksta "(AS)") — Tutina kopsaraksta klases mācība atkārtojas arī viena-avota etiķetei. 33 vēsturiskie doki pielinkoti (`link_politicians_to_documents(doc_ids=…)`), kolīziju nav, `x_handle` NULL (verificējams konts nav atrasts).
- **Matcher paliekas (operatora apstiprinātas):** (1) Bērziņa id=146 pilnvārda dvīņa AKTIERA klase slēgta ar kolokācijas patterniem ("aktier\* Andr\* Bērziņ\*" 4 locījumos, abi reģistri) + junction 146↔74402 dzēsts; dziedātāja klase (64681 — vārds tikai uzskaitījumā) paliek string-neatrisināma; (2) vīriešu -a/-e datīvu formas "Putram"/"Krauzem" pievienotas `name_forms` (plāna § 6 robs). `data/{fix,rollback}_matcher_residuals_2026-07-29.sql`. Harness pēc izmaiņām: **FP 2→1** (paliek tikai 64681), zelts 1278≥1260, zaudētie 3 = zināmās klases. Blakus-verifikācija: Šmita (68721/69330) un del Toro (74357) klases tiešām tur B2 veto kods — BACKLOG kandidātu rindas slēgtas.
- **UI/render sīkumi:** `html { overflow-x: clip; }` aizver `.brief-hero` 100vw ~5px horizontālo ritjoslu; profila Saites mini-grafa mezglu labeli vārdi→**uzvārdi** (`split()[-1]`; render char-baselines pārģenerēti); `render_dashboard` vairs nefetčo tensions otrreiz (orkestrators padod `tensions=`).
- **Pilns render + deploy (operatora apstiprināts 2026-07-29):** `deploy.sh --no-delete` pēc pilnā render; dzīvajā verificēts Bergholca profils (200), `overflow-x: clip` CSS un mini-grafa uzvārdi. Līdz ar to dzīvajā vietnē nonāca arī 07-28 Šmita pārskatu labojums (izlases grep: "Šmits (S!)"/"(ST!)" renderētajā blogā = 0).

## 2026-07-29 — Kurētās analīzes `standalone: true` paterns + NVO dotāciju lapa

Publicēta pirmā **kurētā interaktīvā analīze** `analizes/nvo-dotacijas-2025.html` (2 189 NVO dotācijas 2025; avota dati privāti `data/NVO/`, gitignoreti) un ieviests atkārtoti lietojams ielinkošanas paterns:

- **`content/analizes/<slug>.md` ar `standalone: true` frontmatter** dod TIKAI kartīti `analizes.html` indeksā — `render_analyses()` lapu no md NEģenerē (`src/render/analyses.py` skip), jo pati lapa dzīvo `curated/atmina/analizes/<slug>.html` un nāk caur `_copy_curated` ar dzīvo chrome sync. Slug abās vietās jāsakrīt (URL = `analizes/<stem>.html`). Bez karodziņa md-ģenerētā lapa klusi pārrakstītu kurēto (vai otrādi — atkarībā no kopēšanas secības).
- Kurētās lapas izpildāmais JS pēc stingrās CSP dzīvo `assets/nvv1.js`; datu bloks `<script type="application/json" id="nvo-data">` paliek lapā. Izkliedes grafika tooltip strādā arī uz skārienekrāna (`pointerdown` → tas pats apstrādātājs).
- Publicēšanas gaitā "valsts nauda" formulējumi precizēti uz "publiskā nauda"/"dotācijas" + kājenes atruna (pārskatu postenis var ietvert pašvaldību un ES fondu naudu); abi ārpus-datu fakti verificēti avotos (labas gribas atlīdzinājuma likums 4 M€/gadā 2023–2032; "Liepāja 2027" = EKG nodibinājums).

## 2026-07-28 — Backlog tīrīšanas pakete: topiku "elektr" sanācija, vote entītijas, triāžas, Šmita pārskatu labojums

Deviņi BACKLOG ieraksti slēgti vienā dienā (operatora "sāc" + trīs atsevišķi lēmumi). Visi datu labojumi ar pārī rollback tajā pašā commitā.

- **Kailais "elektr" celms** (`src/saeima/claims.py` `_MOTIF_TOPIC_MAP` + `src/topic_map.py`) aizveda VISUS "Elektronisk\*" likumus uz Degviela un enerģētika — klase izrādījās 3× lielāka par backloga mērījumu: **105 balsojumi / 9171 claims** (mediji, e-sakari, e-nauda, e-smēķēšana, e-pārvalde, elektrovilcieni). Specifiski guardi pirms Energy bloka; Energy sašaurināts uz eksplicītiem celmiem (t.sk. "elektrības"). Backfill + 7 regresijas testi; pēc tā **claims↔votes topic mismatch = 0 visā DB**. Rollback `data/rollback_topic_elektr_2026-07-28.sql`.
- **Motif-drift triāža slēgta:** 8 "Sporta likums" balsojumi (993 claims; Sports tēma jaunāka par balsojumiem) + 5527/5580 (vecā map ķēra KOMISIJAS nosaukumu, ne saturu) sinhronizēti; **5 kurācijas** (218, 219, 1583, 5769, 1752) dokumentētas kā apzinātas — recompute-atšķirība tām ir gaidīta.
- **`saeima_individual_votes.vote` HTML-entītijas dekodētas** (31 078 rindas `Re&#291;istr&#275;jies`/`Nere…`): iztrūkums bija P3 parserī (`_decode_entry` atkodēja tikai vārdu), NE @saeima-tracker; `html.unescape` fikss automātiski nosedz arī `ingest_saeima_missing_votes.py` — 2025. gada 996 balsojumu ielāde nāks tīra.
- **b7 `misattributed_title` klase TUKŠA:** visi 7 kandidāti leģitīmi (citēti ķermenī zem sveša virsraksta); blakusatradums — 5 citāti bija netiešā runa → `quote=NULL`, #6843 stance diakritiku remonts. **(b2a) slēgts:** #532255 pabeigts ar RT backfilla pilno tekstu (conf 0.5→0.7), #10973/#7444 neatgūstami.
- **Partija ≠ frakcija iekodēts carrieros:** CLAUDE.md T6 corollary, `@brief-writer` self-check 14. punkts (faction sadalījums pa `vote_id`), `@saeima-tracker` § Faction Codes piezīme (#373 incidenta klase).
- **nra.lv dublētie URL ceļi:** mērogs = tieši 3 pāri (visi `/neatkariga/neatkariga/`); `_extract_site_article_links` tagad sakļauj secīgus dublētus segmentus + 2 testi; esošie pāri nav dzēsti (0 claims, zinas render tāpat apvieno pēc virsraksta).
- **Plāna § 6 vēsturiskie matcher viltus junctions iztīrīti** (operatora apstiprināts): 17 rindas ar pierādījumu katrai, visām claims=0.
- **Seržants (id=192) izšķirts** (operatora fakts: žurnālists UN politiķis, LZP/AS, kandidēja 2025 RD): `relationship_type='tracked'` — pozīcijas turpmāk koalīcijas blokā.
- **Šmita "Stabilitātei!" kļūda izlabota publicētajos pārskatos** (operatora izvēle: labot visus): reāli **17 context_notes + 16 wiki faili** (virsmas vietām diverģēja); etiķetes → "ārpus frakcijām", #229 balsojuma ieraksts pārrakstīts pēc vote 5754 faktiskā ieraksta (Šmits `faction=NULL`, Par — "sadalījās" bija #373 klase); bloku skaitļi apzināti nav pārrēķināti. `scripts/fix_smits_briefs_2026-07-28.py` (idempotents) + pilna satura rollback. Blogs pārrenderēts `--only=blog`; **deploy izpildīts 2026-07-29** (sk. 07-29 paketes ierakstu) — labojums dzīvajā vietnē.

## 2026-07-27 — Matcher B2+D2+H: vārda robežas, paplašinātais priekšvārda veto, @handle formas

Ieviesta izmērītā kolīziju pakete no `docs/plans/2026-07-27-matcher-koliziju-plans.md` (operatora apstiprinājums = "izpildi matcher plānu"). `match_politicians()` uzvedība mainīta pirmo reizi kopš 2026-05; visi skaitļi — no atkārtojamā `scripts/eval_matcher_collisions.py`.

- **D2 — vienvārda formas skaitās tikai pie vārda robežām** (abās pusēs ne-burts). Nokauj prefiksa bumbas ("Kolu"→"Kolumbieši", "Lāci"→"Lācis") un -is uzvārdu fantoma akuzatīvu ("Valainis" ⊃ "Valaini"), kas uzpūta formu skaitu garām vecajam `count==1` veto. Daudzvārdu formas paliek tīras apakšvirknes (robežu pārbaude frāzēm mērīti zaudēja pārklājumu — "Abu Meri" ⊂ "Abu Merim").
- **B2 — svešā-priekšvārda veto tagad darbojas pie jebkura formu skaita**, kad neviena sakritusī forma nesatur priekšvārdu, ar rafinējumiem: exempt kopa no VISIEM vārda tokeniem visos locījumos (apzināta pārprodukcija — "Ata" ne tikai ģenerētais "Aša"; "Krišjānis" pie "Arturs Krišjānis Kariņš"), ALL-CAPS tokens nav vārda signāls ("ĪSUMĀ"), vārdu partikulas skatās vienu vārdu tālāk ("Isaks del Toro"), institucionālie pid un handle-apstiprināti doki veto nepiedalās.
- **Novirze no plāna sākotnējā mērījuma (apzināta):** plāna B2 "teikuma sākuma lielais burts = ortogrāfija" bija BLANKET likums, un ieviešanas testi atklāja, ka tas atkārtoti atver dokumentēto "Linda Abu Meri" klasi — svešs PILNVĀRDS teikuma sākumā arī tiek piedots. Sākotnējais harness to nevarēja redzēt, jo mērīja tikai variantu NOŅEMTOS linkus, ne pievienotos. Aizstāts ar slēgtas klases `_VETO_STOP_WORDS` (prievārdi, vietniekvārdi, teikuma adverbi/partikulas — "Vienlaikus", "Savukārt", "Pēcāk", "Zem", "Vēl"…); atvērtās klases lietvārdi ("Prokuratūra", "Vēlēšanās") apzināti ārpusē (plāna § 7.3 klase). Harness tagad ziņo arī `silver_added`, lai šī aklā zona neatkārtojas.
- **H — reģistrētās @handles (`social_accounts` ∪ `x_handle`, mazie burti) ir pilnvērtīgas formas**: tvīts, kur politiķis parādās TIKAI kā @handle, tagad linkojas (agrāk daļa linkojās nejauši — "Kols" kā "@RihardsKols" apakšvirkne, ko D2 robežas likvidē; H to pašu dara apzināti). Handle sakritība arī apstiprina personu veto/common-word vārtiem.
- **Mērījumu rezultāts (pilnais skrējiens):** zināmie FP 13→**2** (paliek tikai Bērziņa pilnvārda dvīņi — dziedātājs 64681, aktieris 74402; 62139 jau sedz 07-27 celmu patterni), zelts **1260**/1294 = bāze+2 (zaudēti: avota drukas kļūda "Evijas Siliņas" + 2 atvērtās klases lietvārdu doki; atgūti 5 handle-only pāri), fidelity 932 doki 0 novirzes, kontrafakts bez negpatterns 29→8. Sudraba pievienojumi 1275 (1260 = @handle klase x_mention/twitter, 15 = īstas B2 atgūšanas), noņemtie 62 — nevienam nav pilnvārda sakritības (Rajevs↔@Rajevskis u.c. apakšvirkņu tīrījumi).
- **Novērojamība:** `match_politicians(text, veto_log=[])` — tīrs āķis, kas pieraksta katru veto izmesto kandidātu (pid, forma, svešais tokens, fragments); `/audit-integrity` 1. pārbaudei pievienots **1b B2-veto žurnāls** (14 dienu logs; dzīvais skrējiens 07-27: 6919 doki, 201 izmetumi, topā tikai pareizie namesake veto — t.sk. §6 kandidāti Vītols un "Andra" Bērziņa 74402 tagad apstājas automātiski).
- **Testu bāze:** +16 fixture gadījumi (`matcher_docs.json` d2-*/b2-*/h-* — 10 RED + 6 sargi) + 3 hermetiski zaru testi; `matcher_politicians.json` snapshot REGEN uz 219 rindu rosteru ar `x_handle`; hermetiskā fixture DB ieguva `social_accounts` tabulu. Viena apzināta bāzes maiņa: vecās hermetiskās negatīvās kontroles teksts paliek doc-start formā un joprojām krīt (slēgtā klase neatver pilnvārdu piedošanu). `check.sh` 1650 zaļi.
- **Harness kā regresijas instruments:** fidelity vārti tagad piesien ĪSTO matcher B2D2H konfigurācijai; vārti FP≤3, zelts≥1260; koplietotie leksikoni importēti no `src/matcher.py` (drifts neiespējams klusi).
- **Junction tīrīšana šajā izmaiņā NAV iekļauta** — 16 zināmās viltus rindas jau dzēstas ar `data/fix_matcher_falsejunctions_2026-07-27.sql` (atsevišķs operatora lēmums tajā pašā dienā); plāna § 6 triāžas kandidāti (Rajevs ×8, Vilks, Vītols, Kristovskis, Pūce, Latkovskis, Kronbergs, Ivanovs, Daugavietis) paliek operatora rindā — kods tos vairs neatkārtos, bet vecās rindas DB stāv.

## 2026-07-26 — Personas/profila UI ātrviežu pakete: uzvārda kārtošana, nulles stati, gada datums, Pārskats bez viltus skaitļa

- **"alfabēts" kārto pēc UZVĀRDA, nevis vārda.** Jauns `_persona_sort_name(name, category)` (`src/render/personas.py`): personu kategorijām (Deputāti/Amatpersonas/Žurnālisti/Analītiķi/Ietekmētāji) "Juris Viļums" → "Viļums Juris"; Mediji/Iestādes/Citi un vienvārda nosaukumi paliek pilnā formā ("Latvijas armija" zem L). Kartīte nes `data-sort-name`, un `pnv1.js` kārto (plus tie-breaks "pretrunas"/"pozicijas" sortiem) pēc tā. Iepriekš "Juris Viļums" kārtējās zem J — 189 personu reģistrs lasās pēc uzvārdiem. Sedz `TestPersonaSortName`.
- **Nulles stati kartītēs nobālēti (`.is-zero`, opacity .38).** "0 poz."/"0 pretr." renderējas kā `<div>`, nevis saite, bet līdz šim izskatījās identiski klikšķināmajam skaitlim — lasījās kā salauzta saite. Paliek redzami ("0 pretr." ir informācija), tikai vizuāli nomērķēti.
- **Pēdējās aktivitātes datums rāda gadu, ja tas nav kārtējais.** Jauns `_activity_display_date()` (`src/render/_common.py`) pievieno `display` atslēgu `_get_last_activity()` rezultātam: "07-25" šogad (tweetiem ar laiku), "2025-11-03" vecākiem gadiem (laiks tiek nomests). Iepriekš `date[5:]` rādīja "11-03" bez gada — vecs ieraksts izlasījās kā nesens. Pārslēgtas abas kartītes: `personas.html.j2` un `partija.html.j2`. Sedz `TestActivityDisplayDate` (5 testi, t.sk. `display` klātbūtne `_get_last_activity` izvadē).
- **"Pārskats N" noņemts no profila cilņu joslas.** N bija `parskats_data|length` — signālu BLOKU skaits (1–3), nevis satura apjoms; lasītāji to lasīja kā pozīciju skaitu. Pārējām cilnēm skaitlis paliek (tas ir reāls: pozīcijas, balsojumi, pretrunas). `.profile-stat` dabūja `justify-content:center`, lai bez-skaitļa cilne tur joslas augstumu.
- **Partijas īskods kartītes eyebrow dabūja `title` tooltip** ar pilno partijas nosaukumu (MMN/ASL/GKR/J/B/ST ārpusējiem nekas nesaka). Tooltip tikai kad īskods ≠ pilns nosaukums.
- **Baselines:** `render_baseline_politicians.json` REGEN (personas.html + 7 politiki detaļlapas); partijas baseline nemainījās — fixture dati ir 2026. g., kur `display` sakrīt ar veco `date[5:]`. Pilns `check.sh`: 1630 passed.
- **Deployots 2026-07-26** (`deploy.sh --no-delete`, commit `e1aa19a8`). Live verificēts: personas.html servē 189 `data-sort-name`, profila cilņu josla bez Pārskats skaitļa.

## 2026-07-25 — Interpretatora normalizācija + deploy atsiets no WSL

- **Kails `python` izņemts no visām dzīvajām komandām** — 46 rindas 15 failos (`CLAUDE.md`, `README.md`, `wiki/operations/*`). Uz šīs mašīnas `python` PATH-ā aizved uz svešu aģenta vidi, kas ielikta lietotāja **pastāvīgajā** PATH (t.i. arī operatora paša terminālī, ne tikai aģenta sesijās); aiz tās ir tikai miris Python 3.10 ceļš un Store aizbāznis. Projekta vide ir 3.12. Kļūmes forma nav "komanda nestrādā", bet daļēja rakstīšana — sk. iepriekšējo ierakstu.
- **Apzināti neaiztikts:** `python -m venv .venv` sāknēšanas komandas (vide vēl neeksistē), ```` ```python ```` bloku iezīmes, esošā `.venv/Scripts/python` forma bez `.exe` (arī nepārprotama) un vēsturiskie plāni/specifikācijas/CHANGELOG — tie ir ieraksti par padarīto, ne instrukcijas.
- **`ensure_embeddings_live()` pieslēgts vēl trim skriptiem**, kas tiešām embedo: `ingest_vestnesis.py` (dokumentu vektori), `p3_backfill_year.py` un `p3_backfill_year_urllib.py` (balsojumi → claims). `ingest_url.py` apzināti NAV — tas neembedo, tur vārti būtu tikai lieks modeļa ielādes kavējums.
- **Deploy vairs nav piesiets WSL.** `rsync` uz šīs mašīnas nebija nekur, pat ne `C:\Program Files\Git\usr\bin\`. Uzstādīts MSYS2 rsync 3.4.4, un `C:\msys64\usr\bin` pievienots lietotāja PATH **beigās** — tā `rsync` atrodas, bet MSYS2 pārējie rīki neaizēno Git for Windows savus (pārbaudīts: `ssh`/`grep`/`sed`/`awk`/`find`/`sort` → `/usr/bin/*`, `git` → `/mingw64/bin/git`, tikai `rsync` → `/c/msys64/usr/bin/rsync`). `deploy.sh` jau deva priekšroku vietējam rsync, tāpēc koda izmaiņas šim nebija vajadzīgas. Blakus ieguvums: vietējais rsync lieto Git Bash `ssh`, tātad esošās Windows puses atslēgas — WSL `~/.ssh/` atspoguļošana vairs nav vajadzīga.
- **`deploy.sh` vairs necietkodē `wsl -d Hermes`.** Tas piesēja publicēšanu vienam nosauktam distro, kas šim repo nepieder — atinstalē to, un deploy nomirtu ar neskaidru kļūdu tieši publicēšanas brīdī. Tagad WSL zars meklē: noklusējuma distro, tad jebkurš ar rsync, tad skaidra kļūda ar norādi uzstādīt vietējo rsync.
- **Kas NEDER rsync aizvietošanai** (izmeklēts): `scp -r` un `sftp` nav inkrementāli — katrs deploy augšupielādētu visu koku. `rclone` ar sftp aizmuguri der semantiski (`copy` nedzēš = mūsu `--no-delete` likums), bet prasa `deploy.sh` pārrakstīšanu; jēga tikai tur, kur rsync nav iespējams.

## 2026-07-25 — Klātbūtnes atzīmes vairs nav pozīcijas: 30 476 claims dzēsti, vārti kodā

- **Problēma:** `generate_claims_from_votes()` taisīja claim uz katru sekoto deputātu bez nosacījumiem, arī procedurālos klātbūtnes notikumos. `Reģistrējies`/`Nereģistrējies` nav `vote_lv` kartē, tāpēc stance nāca no atkāpšanās zara ar neapstrādātu biļetena vērtību: `Re&#291;istr&#275;jies: Deputātu klātbūtnes reģistrācija`, ar `confidence=1.0` un `salience=0.7`. Entītiju defekts slēpās tāpēc, ka visas četras īstās balsu vērtības ir bez garumzīmēm.
- **Apjoms:** 30 476 claims (5,5% no 548 516), visi `claim_type='saeima_vote'`, visi tēmā "Valsts pārvalde", ~304 uz deputātu jeb ~5% no viņa balsojumu claims. Tikpat lieku vektoru `claim_vectors` indeksā.
- **Publiski nenoplūda:** Data Contract #4 (render/brief filtrē `claim_type='position'`) + balsojumu sekcijas izslēgšana kopš 2026-07-17. Kaitējums bija iekšējs — uzpūsti skaitītāji, mirusi masa kNN indeksā, muļķība jebkuram tiešam `claims` vaicājumam.
- **Vārti kodā** (`src/saeima/votes.py`): motīva prefiksa agrā izeja PLUS `_BALLOT_VALUES_THAT_ARE_POSITIONS` — claim tiek taisīts tikai biļetenam ar `Par`/`Pret`/`Atturas`/`Nebalsoja`. Filtrs pēc VĒRTĪBAS, ne tikai pēc motīva, jo klātbūtnes stāvokļi parādās arī īstu balsojumu vidū. `Nebalsoja` paliek — deputāts bija klāt un nenobalsoja, kas ir jēgpilna atzīme.
- **Divi piegājieni:** pirmais notīrīja 30 376 claims no 322 `Deputātu klātbūtnes reģistrācija` notikumiem; atlikušo `&#` meklēšana atsedza vēl 100 no **`Kvoruma pārbaude`** — tā pati procedūra citā vārdā. Pēc otrā piegājiena `stance LIKE '%&#%'` atgriež 0. Ārpus šīm divām klasēm DB nav neviena `Reģistrējies`/`Nereģistrējies` biļetena.
- **Prefikss, ne apakšvirkne:** atlase ir `motif LIKE 'Deputātu klātbūtnes reģistrācija%'`, NEVIS `%reģistrācij%` — pēdējais noķertu īstus likumus (Civilstāvokļa aktu reģistrācijas likums). Tā pati izvēle kā `render/votes.py:173`; nostiprināta testā.
- **Skaitļi:** claims 548 516 → 518 040; `claim_vectors` 554 974 → 524 498. `saeima_votes` (6103) un `saeima_individual_votes` (539 909) neaiztikti — tie ir īsts ieraksts par to, kas sēdē bija klāt.
- **Rollback:** `data/atmina.db.pre-registration-claims-purge-20260725.db` (1,77 GB, gitignored) + `data/rollback_purge_registration_claims_2026-07-25.sql`, kas dokumentē atjaunošanu un atlases kritēriju. INSERT dump šeit nederētu: 30 tūkst. rindu ar 384-float vektoriem ir ~100 MB SQL, un `claim_vectors` ir vec0 virtuālā tabula, ko tīrs .sql bez sqlite-vec paplašinājuma tāpat neatjauno.
- **Viens esošs tests laboja datus, ne apgalvojumu:** `test_saeima_vote_claim_is_tagged` lietoja `vote="par"` mazajiem burtiem — produkcijā tādas vērtības nav (539 909 biļeteni, visi ar lielo burtu). Pēc jaunajiem vārtiem neatpazīta vērtība claim vairs netaisa, kas ir tieši vēlamā uzvedība, tāpēc testa dati saskaņoti ar realitāti (`vote="Par"`), nevis vārti atslābināti.

## 2026-07-25 — Saeimas 2025. gada procedurālo balsojumu robs: puse gada nebija DB

- **Kā atklājās:** publisks apgalvojums (@AtlasDynam1cs) par diviem Progresīvo balsojumiem, kurus mēs nevarējām pārbaudīt — abu DB nebija. Pārbaudot izrādījās, ka 2025. gadam iztrūkst veselas balsojumu klases: `Par nodošanu … komisijai` 0 rindu (2024. g. 12), `Par priekšlikumu Nr.N` 0 (pret 560), `atzīšanu par steidzamu` 0 (pret 124), `Par iekļaušanu …` 0 (pret 10). Nevis dienas robs, bet **metodes robs**.
- **Mērogs:** jauns `scripts/audit_saeima_agenda_parity.py` (read-only, salīdzina pēc `(vote_date, vote_time)`, **nevis URL**) noauditēja visas 51 balsojošo 2025. g. sēdi: **darba kārtībā 2006, DB 1010 — trūkst 996 (49,7%)**. Saraksts `data/parity_2025.json`.
- **Kāpēc ne pēc URL:** titania pārarhivē lapas ar jauniem UNID, tāpēc `store_vote()` URL-dedup (`src/saeima/votes.py:413`) kļūst akls. Akls `p3_backfill_year_urllib.py --year 2025` palaidiens ražotu dublikātus, nevis aizpildītu robus — tas ir dokumentēts abos jaunajos skriptos.
- **Pilots:** `scripts/ingest_saeima_missing_votes.py` ielādēja 2 sēdes — **26 balsojumi, 2231 individuālā balss, 1631 claim, deputātu atbilstība 100%** (rollback `data/rollback_saeima_missing_votes_2026-07-25.sql`). Septiņiem Lm14 balsojumiem nebija māsas ieraksta, no kā pārmantot kopsavilkumu; uzrakstīti manuāli (`data/fix_saeima_missing_summaries_2026-07-25.sql` + rollback). Atlikušie 996 gaida apjoma lēmumu — sk. BACKLOG.
- **Divi defekti, kas atklājās izpildē:**
  1. **`store_vote()` commit-o pirms claim ģenerēšanas.** Kad claim solis krita (nepareizs Python interpretators — `python` šajā mašīnā ir hermes venv, nevis `E:\atmina\.venv`), 20 balsojumu rindas palika DB, bet ārpus rollback faila, jo `vote_db_id` tika pierakstīts pēc claim ģenerēšanas. Skripts salabots (ID fiksē uzreiz pēc `store_vote`), pievienots `--repair-claims` režīms, kas atjauno claims balsojumiem, kuri jau ir DB. Rollback pārrakstīts ar pilno diapazonu.
  2. **Reģistrācijas notikumi ģenerē claims.** DB ir 316 `Deputātu klātbūtnes reģistrācija` rindu un **30 376 no tām atvasinātu claim (~5,6% no visiem)** — "Reģistrējies" nav Par/Pret/Atturas. Jaunās ielādes tos izlaiž pēc noklusējuma; vēsturiskie 30 tūkst. → BACKLOG.
- **`ensure_embeddings_live()`** (`src/preflight.py`) — stingrāks `ensure_analysis_env()` brālis bulk-rakstīšanas ieejām. Esošais vārts pārbauda `find_spec`, kas atbild "vai ir uzstādīts", nevis "vai strādā": salauztajā vidē `sentence_transformers` un `simplemma` spec bija `True`, imports krita uz torchcodec DLL, tāpēc vecais vārts būtu izlaidis cauri. Jaunais startā veic vienu īstu `embed_text()` — noķer nepareizu interpretatoru, salauztas native bibliotēkas, nelejupielādētu modeli un mirušu HF savienojumu vienā izsaukumā. Turēts ĀRPUS karstajiem ceļiem (`save_analysis()` paliek pie lētā vārta, jo torch imports maksā sekundes katrā izsaukumā). `preflight_check()` 3. solis tagad sauc to pašu funkciju, nevis dublē loģiku. Pieslēgts `ingest_saeima_missing_votes.py` abiem rakstošajiem ceļiem; parity auditam apzināti NAV — tas neko neraksta.
- **Saturiskais atradums, kas pamato visu darbu (jauns T14):** 2025-04-10 Progresīvie atturējās balsojumā par Krievijas/Baltkrievijas preču tirdzniecības aizlieguma iekļaušanu nākamās sēdes darba kārtībā (24:12, 45 atturas) un **vienu minūti vēlāk nobalsoja PAR tā paša lēmuma projekta nodošanu Budžeta un finanšu komisijai**, kas tika pieņemta 67:11. Citējot tikai atturēšanos, ieraksts tiek apgriezts otrādi. Iekodēts `CLAUDE.md` kā T14 (procedurālo balsojumu ķēde jālasa pēc `document_nr`, ne pa vienam).
- **Atturēšanās semantika iekodēta** (operatora lēmums): Saeimā lēmumu pieņem klātesošo vairākums un `Atturas` skaitās klātesošs, tāpēc atturēšanās bloķē tāpat kā `Pret` — bet stance tekstā balss jāatspoguļo tā, kā protokolā, nevis jāpārraksta par „balsoja pret". `CLAUDE.md` § Working Conventions.
- **BACKLOG korekcija:** ieraksts, kas apgalvoja, ka titania nepublicē amendment balsojumus un ka DB to ir 0, bija nepatiess jau tapšanas brīdī — DB ir 1452 `Par priekšlikumu Nr.N` rindas, un audits atrada vēl. Stenogrammu parse tiem nav vajadzīgs.

## 2026-07-25 — Trīs strukturāli claim defekti izlaboti; audits dabū divas klases, kas neatkarīgas no citāta

- **#408 Rinkēvičs — dzēsts.** Avots ir 172 zīmju paziņojums no prezidenta kancelejas par desmit dienu atvaļinājumu; pozīcijas tur nav nevienā lasījumā. Sākotnēji glabājās ar `confidence` **0.95** un ekstrakcijas pievienotu rāmējumu „skandāla un opozīcijas spiediena laikā", kā avotā nav ne miņas.
- **#7455 Siliņa — pārtipināts uz `commentary`** ar `speaker_id=25` (Valainis), Data Contract #5. Avots ir Valaiņa intervija PAR Siliņu; viņas pašas vārdu dokumentā nav vispār.
- **#279 + #280 Sprūds — dzēsti; Rajeva pozīcijas saglabātas no jauna.** Doc 4909 (diena.lv, 13 482 zīmes) ir **intervija ar Igoru Rajevu**, bet matcher tam bija iedevis `subject`=Sprūds, un no Rajeva teiktā izauga DIVI claims kā Sprūda pozīcijas. **#280 ir šī darba metodoloģiskais atradums:** tas dzīvoja ar conf 0.8 un bija neredzams visām trim audita klasēm, jo tā `quote` ir `NULL` — neviens uz citātu balstīts tests nevar redzēt claim, kuram citāta nav. Vietā trīs jauni Rajeva claims ar verbatim pirmās personas citātiem (#554009 Droni 0.9, #554010 Aizsardzība un drošība 0.9, #554011 Koalīcija un partijas 0.85), katrs savā tēmā, lai T2 idempotence tos nesapludinātu; Rajeva pozīcijas 21 → 24.
- **Audita rīks papildināts ar divām klasēm, kas nelasa `quote`:** `misattributed_title` (virsraksts attiecina saturu CITAM politiķim nekā claim īpašnieks — **7 gadījumi**, 3 pie conf≥0.85) un `not_subject` (`position` bez `subject` saites uz savu dokumentu — 104, apzināti marķēts kā vājš paraugu kopums, ne defektu saraksts).
- **Sakne, kas paliek atvērta:** vārds „Rajev" doc 4909 `content` laukā parādās **nulle reižu** — intervija uzrunā viņu ar „jūs", un vārds ir tikai `title` laukā, ko `match_politicians` neskenē. Mērogs: 10 no 3000 web dokumentiem (~0,3%). Klase sāp tieši intervijās, t.i. tur, kur pirmās personas satura ir visvairāk. Fikss prasa load-bearing matcher izmaiņu ar T1 kolīziju pārbaudi — atsevišķs lēmums (BACKLOG b6).
- **Vektoru higiēna:** dzēstajiem claims noņemti arī `claim_vectors` ieraksti, un rollback tos atjauno baitu identiski (hex literālis; round-trip verificēts). Blakusatradums: DB jau ir **7004 bāreņu vektori** no vēsturiskām dzēšanām — inerti, jo `search_similar_claims` kNN pushdown filtrē caur `claims`, bet higiēnas parāds (BACKLOG).

## 2026-07-25 — Vēsturisko retvītu pilnteksta backfill: 8140 doki, +795 politiķu saišu

- **Sakne:** 2026-07-24 `_tweet_text()` fikss bija forward-only. Vēsturē palika RT dokumenti, kas apcirsti X mantotajā 140 rakstzīmju robežā, un `link_politicians_to_documents` skenē `content` — politiķis, kas nosaukts tikai aiz robežas, nekad netika piesaistīts. Kluss pārklājuma robs, ne redzama kļūda.
- **Mērķis precizēts pirms skrējiena:** no 11 245 RT dokiem apcirsti bija **8 910**, ne visi — 2 335 ir pilni retvīti, kuru oriģināls ietilpa robežā. Tests: beidzas ar daudzpunkti VAI garums 139–152.
- **Rezultāts** (`scripts/backfill_retweet_fulltext.py`): **8 140 atjaunoti**, vidēji +244 zīmes, RT max garums 152 → 8 458, **+795 jauni junctions**. No junctioniem uz salabotajiem dokiem **623 ir tādi, kur politiķa uzvārds parādās TIKAI aiz 140. zīmes** — tas ir backfilla izmērāmais ieguvums. Dokumentu skaits nemainīgs (61 051), `scraped_at` neaiztikts, 82 claims uz RT dokiem neskarti. **770 palika apcirsti un tādi paliks:** 299 tvīti dzēsti/privāti, 307 oriģināls jau bija īss.
- **Divi arhitektūras slazdi, ap kuriem skripts būvēts:**
  1. **`insert_document()` neder** — tā update-in-place zars ir vārtos uz `platform='web'` („X tweets have stable URL→content guarantees" — tieši tas pieņēmums, ko 140-zīmju apraušana lauž). Tvītam tas kristu cauri uz INSERT un radītu DUBLIKĀTU, atraujot oriģināla claims un junctions. BACKLOG iepriekš apgalvoja pretējo; tas bija nepareizi. Skripts raksta tiešu UPDATE.
  2. **`scraped_at` nedrīkst aiztikt** — `routine._check_analysis` to salīdzina pret `analyses.created_at`, tāpēc 8 tūkstošu vēsturisku rindu pacelšana atvērtu tūkstošiem politiķu kā „pending" un sabojātu dienas rutīnas statusu. Tā vietā `link_politicians_to_documents` dabūja `doc_ids` parametru (skenē tieši tos dokumentus, ignorējot logu; tukšs saraksts = nekādu dokumentu, nekad atkāpšanās uz logu).
- **Divi defekti, kas atklājās tikai izpildē:**
  1. **`documents.content_hash` ir UNIQUE.** Pēc izvēršanas divi konti, kas retvītojuši VIENU oriģinālu, dod identisku tekstu → `IntegrityError` apturēja pirmo skrējienu pie 4400/8863. `apply_update()` tagad pārbauda kolīziju iepriekš un izlaiž rindu; sibling doks patur pilno tekstu un tiek linkots, tāpēc pieminējums nepazūd. Reāli sastapts: 1 gadījums.
  2. **Pārlinkošana notiek skrējiena beigās**, tāpēc kritiens atstāja 4 145 salabotus dokumentus nelasītus. Pievienots `--relink-only`, kas pārlinko visus jau salabotos; idempotents (`INSERT OR IGNORE`).
- **Datu drošība:** `fetch_tweets_by_ids()` (jauns, 100 ID/pieprasījums, ~1 s) verificē KATRU rezultātu pret ID, ko prasīja. X atbild ar pozīciju-alignētu sarakstu, kurā dzēstie ir `None`; naivs `zip` pret pieprasījumu ierakstītu viena politiķa tvīta tekstu cita politiķa dokumentā, tiklīdz partijā ir viens dzēsts tvīts. Blakus salabots latents `fetch_tweet_by_id` kritiens, kad atbilde ir `[None]`.
- **Rollback** (`data/rollback_retweet_fulltext_backfill_2026-07-25.sql`, 8497 rindas): katra rinda uzrakstīta un noskalota uz diska PIRMS tās forward UPDATE, tāpēc kritiens vidū nevar atstāt pārrakstītu rindu bez ieraksta. Verificēts uz izolētas kopijas — atjauno apcirsto stāvokli (max garums 147) un hash sakrīt ar saturu 300/300 paraugos.
- **T13 kohortas audits:** 8 nejauši jaunie junctions pārbaudīti ar roku — visi īsti pilnvārda pieminējumi kontekstā, substring kolīziju nav.
- **Noslēgts:** 6 jauni testi `tests/test_retweet_backfill.py` (ID kartēšana ar `None` vietturiem, nepieprasīta ID atmešana, RT izvēršana, mērķēta pārlinkošana, tukšs `doc_ids`); `check.sh` zaļš (1614 passed).

## 2026-07-25 — Quote-fidelity: parafrāžu klase izsmelta un virsrakstu klase triažēta (36 claims)

- **Sakne (BACKLOG § Stance-fidelity defekti, punkts (b)):** `quote` laukā bija nonācis žurnālista TREŠĀS PERSONAS teksts — gramatiski tāds nemaz nevar būt politiķa citāts („Rokpelnis skaidroja, ka…", „Čudars uzdevis izveidot…"). Publiskajā vietnē tas izskatījās kā citāts. Atlase: `scripts/audit_quote_fidelity.py` klase „paraphrase" ar `confidence >= 0.85` — 7 claims.
- **Labojums** (`data/{fix,rollback}_quote_fidelity_paraphrase_2026-07-25.sql`): sešos gadījumos avotā politiķa tiešās runas NAV vispār (#423 Braže, #7308 + #11003 Čudars, #20825 Kulbergs, #532198 Rokpelnis, #532753 Čakša) → `quote = NULL`, **nostāja paliek**, jo žurnālista ziņojums to pamato; vienā (#6944 Švinka) avotā verbatim tiešā runa BIJA → parafrāze aizstāta ar to („Tas, ka frakcija nezina, rada manī apmulsumu…"), verificēts kā substring dokumentā.
- **Kāpēc NULL, ne pārrakstīšana:** #11003 dokumentā Čudara verbatim citāts ir, bet tas ir no MARTA paziņojuma presei un aprīļa rīcību nepamato; #20825 vienīgā Kulberga tiešā runa attiecas uz koalīcijas sarunu gaitu, ne uz prioritātēm. Nepiederīgs verbatim citāts ir tā pati kļūdas klase, tikai grūtāk pamanāma — tāpēc tukšs lauks.
- **Ticamības korekcijas:** #423 0.9 → 0.6 (Delfi abonentu ievadstubs, `is_paywall=1`, 1508 zīmes — jaunais §8 vārtu slieksnis) un no nostājas izņemts vārds „buferzona", kāda dokumentā nav; #532753 0.85 → 0.8 (269 zīmju ievadstubs, nav verbatim).
- **Noslēgts:** audits pēc labojuma — parafrāžu klase pie conf≥0.85 = **0** (kopā 22→15); `check.sh` zaļš (1608 passed); šaurs render (`pretrunas,pozicijas,dashboard,politiki`) + grep pār `output/` apstiprina, ka neviena no sešām vecajām parafrāzēm nekur vairs neparādās. `templates/politician.html.j2` tukšam citātam jau bija korekts fallback („Citāts nav pieejams — parafrāze no avota"); neviena pretruna šos claims necitē (`claim_old_id`/`claim_new_id` pārbaudīts), tāpēc publicētās pretrunu lapas neskar.
- **Paliek atvērts:** 15 tās pašas klases parafrāzes pie conf 0.6–0.8; #113 (virsraksts) un #7322 (sarkasms nolasīts kā nostāja) — abi verificēti, bet citās audita klasēs.

### 2. un 3. partija (tā pati diena, atsevišķi pāri)

- **#7322 Vītols — sarkasms** (`data/{fix,rollback}_quote_fidelity_sarcasm_headline_2026-07-25.sql`): sākotnējā diagnoze („nostāja ir pretēja autora domai") pēc pilna tvīta izlasīšanas **precizējama** — Vītols tiešām uzstāj uz brīvprātīgu 2PL likvidāciju „pa godīgo" pēc Lietuvas parauga. Īstais defekts ir cits: ekstrakcija apstājās pusceļā un izlaida trešo rindkopu, kur viņš pats saka, ka Latvijā cilvēks 2PL neiemaksā **neko** — tātad pēc viņa paša „godīgā" principa izņemamā daļa būtu nulle. Bez tā noslēguma sarkasms („Ok, visu uzkrājumu uz 1PL, lai izpļekarē! To es viņiem novēlu👹") paliek nesaprotams, un tieši tāpēc to varēja nolasīt kā atbalstu. Nostāja papildināta ar āķi; sarkasms `reasoning`-ā nosaukts par zobgalību oponentiem; citāts (bija ar daudzpunkti sašūts no divām rindkopām) aizstāts ar vienu nepārtrauktu verbatim fragmentu.
- **#113 Braže — virsraksts:** citāta laukā bija NRA virsraksts, kas dokumenta tekstā neparādās; aizstāts ar ministres verbatim tiešo runu („Mums nav tādu militāru draudu…"). Nostāja precizēta — virsraksta saīsinājums bija nogriezis otro pusi: tajā pašā intervijā Braže hibrīddraudus sauc par reāliem. Tas maina arī iespējamās spriedzes ar Sprūdu vērtējumu — salīdzināma ir tikai KONVENCIONĀLO draudu daļa.
- **15 parafrāzes pie conf 0.6–0.8** (`data/{fix,rollback}_quote_fidelity_paraphrase_tail_2026-07-25.sql`): 14× `quote=NULL`, 1× verbatim aizstāšana (#548286 Indriksone). **Divos gadījumos dokumentā tiešā runa bija, bet pieder CITAM cilvēkam** — #532269 „Tā ir aizņemta nauda…" ir premjera Kulberga, ne finanšu ministra Kučinska; #532155 citāti pieder komisijas vadītājai Vīksnai un Šmitei-Roķei, ne Šuvajevam. Nepiederīga verbatim citāta ielikšana ir tā pati kļūdas klase, tikai grūtāk pamanāma — tāpēc tukšs lauks. Trīs claims (#10973, #7444, #532255) nāk no **apcirstiem retvītiem**, kur pirmās personas avots nekad nav bijis redzams; #532255 apcirsts teikuma vidū → ticamība 0.6 → 0.5 un atzīme, ka nostāja jāpārskata pirms citēšanas.
- **Rezultāts:** `scripts/audit_quote_fidelity.py` parafrāžu klase = **0 pie visiem ticamības līmeņiem** (22 → 0). `check.sh` zaļš (1608 passed). Verifikācija pret **renderēto publisko virsmu**: visiem 24 labotajiem claims `quote` un `confidence` `output/atmina/pozicijas-data.json` sakrīt ar DB (24/24), un neviena no 16 vecajām parafrāzēm/virsrakstiem `output/` vairs neparādās.
- **Metodoloģiska piezīme (maksāja vienu nepareizu pieņēmumu):** claims sasniedz publisko virsmu caur `pozicijas-data.json`, ne tikai caur profila lapu — profils rāda svaiguma logu (Vītolam 48 no 138 pozīcijām, līdz 2026-05-22), tāpēc aprīļa #7322 profilā nemaz nebija, kaut publiski bija. Turpmāk claim-līmeņa labojumus verificē pret JSON, ne tikai pret HTML.
- **Virsrakstu klase:** triažēta tajā pašā dienā, sk. nākamo sadaļu.

### 4. partija — virsrakstu klases triāža (50 pārbaudīti, 12 laboti)

- **Kāpēc te nedrīkstēja batch-fix:** LV ziņu virsraksts ļoti bieži **ir** politiķa citāts („Es neesmu un nebūšu politiķis!"), un daļa dokumentu ir lede-only, tāpēc frāzes neesamība saglabātajā ķermenī NEpierāda, ka tie nav viņa vārdi. Blanket-NULL būtu iznīcinājis īstus citātus.
- **Triāžas tests, kas nostrādāja** (divi soļi): (1) vai frāze parādās ķermenī ārpus virsraksta — 15/50 parādās, droši; (2) pārējiem — vai virsraksts frāzi PASNIEDZ kā politiķa vārdus: pēdiņās vai ar attiecinājumu „Vārds: …". Ja jā — leģitīms; ja nē (žurnālista proza vai netiešā runa ar „pauda/teica/atzina") — defekts. **38 no 50 iztur un paliek neaiztikti**; auditā tie parādīsies mūžīgi, jo rīks mēra tikai virsraksta sakritību.
- **Laboti 12** (`data/{fix,rollback}_quote_fidelity_headline_2026-07-25.sql`): 9× `quote=NULL`; 3× virsraksts aizstāts ar īstu verbatim ķermeņa citātu (#18234 Kozlovskis, #22991 Kulbergs, #520888 Puntulis).
- **#520888 Puntulis — virsraksts bija saturiski maldinošs, ne tikai neverbatim.** „Puntulis: centīšos panākt algu pieaugumu kultūras nozarē" lasās kā apņemšanās; ķermenī viņš tieši ATSAKĀS solīt („Es iepriekš neko nesolīju … Nesolīšu arī tagad, bet … esmu pierādījis, ka ļoti centīšos to panākt"). Saglabātā nostāja („Apņemas … prioritāri rast finansējumu") šo atrunu bija pazaudējusi — nostāja pārrakstīta.
- **Trīs strukturāli atradumi, kas paliek operatora lēmumam** (nepatiesais citāts katram jau novērsts):
  - **#279 Sprūds** — citāta laukā bija **cita politiķa vārdi**. Dokuments 4909 ir intervija ar **Rajevu** (teksts uzrunā „jūs"), un virsraksts „Rajevs: vajadzētu beidzot kaut vienu dronu notriekt" bija saglabāts kā Sprūda citāts. Nostāja („saskaras ar koalīcijas iekšēju kritiku") turklāt ir fakts PAR Sprūdu, ne viņa pozīcija → pēc Data Contract #5 `commentary` ar `speaker_id`, ne `position`. Ticamība 0.85 → 0.5; pārtipināšana/dzēšana ir strukturāls lēmums.
  - **#408 Rinkēvičs** — dokuments ir viens teikums par desmit dienu atvaļinājumu, bet nostāja tam bija pielikusi klāt „skandāla un opozīcijas spiediena laikā", kā avotā nav ne miņas, **pie confidence 0.95**. Rāmējums izņemts, ticamība 0.5; dzēšanas kandidāts, jo atvaļinājuma paziņojums nav pozīcija.
  - **#7455 Siliņa** — avots ir Valaiņa intervija par Siliņu; viņas pašas vārdu dokumentā nav, visi tiešie citāti pieder Valainim. Ticamība 0.85 → 0.7.
- **Noslēgts:** `check.sh` zaļš; virsrakstu klase 50 → 38; visiem 12 `quote`+`confidence` sakrīt ar `pozicijas-data.json` (12/12). Piezīme verifikācijai: trīs vecie virsraksti PALIEK `zinas.html` — tur tie ir avota rakstu virsraksti (`class="news-title"` ar saiti uz avotu), un tā ir vienīgā vieta, kur virsrakstam arī jābūt.

## 2026-07-25 — Deep-check skrējiens: 0 pretrunu, bet 0.80 slieksnis atzīts par inertu + pretruna #41 pārenkurota

- **Skrējiens:** 4 paralēli `@contradiction-hunter` (Kulbergs 312 poz., Braže 208, Rinkēvičs 143, Vītols 138 — visi ar „nekad neatrasta pretruna" vai pirms-fiksa pēdējo pārbaudi) → 6 kandidāti → `@devils-advocate` **nogalināja visus 6**. Nekas nav saglabāts. Tas atbilst ~1/2700 ražai; nulle ir derīgs iznākums.
- **Metodoloģiskais atradums (mērīts, verificēts galvenajā kontekstā):** `0.80` kosinusa slieksnis, kas iekodēts `/deep-check` un `@contradiction-hunter`, **nefiltrē neko**. Pilnās pāru matricas: Braže 99.4% pāru ≥0.80, Rinkēvičs 99.0%, Kulbergs 99.1%; korpusa minimums 0.758, mediāna ~0.85. Krustotā bāzlīnija ir tāda pati — **divu NESAISTĪTU politiķu claims savā starpā vidēji 0.853** pret 0.845–0.857 viena politiķa ietvaros. Modelis ir stipri anizotrops uz LV politisko prozu; sliekšņa celšana nepalīdz (pie ≥0.92 ir tās pašas dienas pārstāsti, kamēr īstie pagriezieni sēž 0.85–0.90). Der TIKAI relatīvais kNN rangs politiķa paša claims ietvaros + hronoloģiskā lasīšana. Nesēji atjaunoti abi. **Blakus precizējums:** `claim_vectors` ir vec0 tabula BEZ `distance_metric`, tāpēc atgriežamais lauks `distance` ir **eiklīda, ne kosinusa** attālums (`cos = 1 − d²/2` uz vienības vektoriem) — „distance ≤ 0.20" nozīmē kosinusu ≥0.98, t.i. praktiski tikai dublikātus.
- **Pretruna #41 (publicēta, `confirmed=1`) pārenkurota:** jaunā puse balstījās uz claim 527890 (conf 0.72), kuras citāts („Man ir ideja, kā varētu īstenot…") nepamato tās stance par gatavību pabeigt līdz 2030. gadam — un Kulberga paša tiešs videocitāts DIENU IEPRIEKŠ (548274, conf 0.9, „Es arī joprojām uzskatu, ka tas ir nereāli") saka pretējo. Pārenkurots uz 527773 (conf 0.85, tiešs citāts par RB finansēšanu kā militārās mobilitātes projektu); kopsavilkums pārrakstīts. Pati pārmaiņa (iesaldēt → finansēt) paliek — mainījās pierādījums. Pāris `data/{fix,rollback}_contradiction_41_reanchor_2026-07-25.sql`.
- **T6:** Vītols (id=64) `role` 'Ekonomists' → 'Finanšu ministra biroja ekonomists' (avots — viņa paša pirmās personas claims #531937/#532127/#548193). `party` APZINĀTI palikts NULL: „Latvijas Restarts" piederība Apvienotajam sarakstam ir ārējs fakts, ko DB nesatur, un `party` dzen koalīcijas klasifikāciju. Pāris `data/{fix,rollback}_vitols_role_2026-07-25.sql`.
- **Atvērts → BACKLOG:** stance-fidelity defektu klase (parafrāze/virsraksts/sarkasms saglabāts kā pozīcija; 4 verificēti gadījumi, 24 paywall claims kā pirmais audita kopums) + divas jaunas medību pēdas.

## 2026-07-25 — twikit STRICT-404 cēlonis: slikta transaction atslēga bootstrapā (ct0 dzīšanās beigusies)

- **Simptoms (mēnešiem):** `probe_x_cookies.py` katrā skrējienā rādīja tieši vienu „BROKEN 2/4" slotu — `user_replies` + `search_tweet` 404, kamēr `get_user`/`user_tweets` iet — un katru reizi CITU slotu. Diagnoze bija „ct0 novecojis", risinājums — operatora sīkfailu refresh. **Abi bija nepareizi.**
- **Cēlonis:** katrs twikit `Client` izveido `x-client-transaction-id` atslēgu VIENREIZ (pirmajā pieprasījumā, no X mājaslapas) un kešo to uz visu klienta mūžu. Daļa bootstrapu dod atslēgu, ko X noraida; STRICT galapunkti (`SearchTimeline`, `UserTweetsAndReplies`) atbild ar tukšu 404, LENIENT to nepārbauda. Tāpēc slots izskatās pa pusei dzīvs, un simptoms lec, jo katrs process būvē jaunus klientus.
- **Izslēgts ar mērījumiem:** novecojis ct0 (bojātais slots lec bez sīkfailu maiņas; vecais ct0 pēc tam 4/4) · twikit stub fallback (kritējam bija īsta atslēga, bez izņēmuma) · konts (3 svaigi klienti ar tiem pašiem sīkfailiem — visi gāja) · katra pieprasījuma nejaušība (viens klients 5/5 kritienu) · rate limits (404 atbildēs `x-rate-limit-remaining: 482/500`, tukšs ķermenis, 10 ms) · laika logs — **izšķirošais apļveida tests**: 75 s garumā viena slota klients krita 10/10 apļos, pārējie četri gāja 10/10 tajās pašās sekundēs (kolonna, ne rinda).
- **Fix:** `src/x_pool.py::reset_transaction_key()` notīra kešoto bootstrapu, un twikit nākamajā pieprasījumā uzbūvē JAUNU atslēgu; verificēts 3/3 — kritējs atgūstas pēc 1–3 pārbūvēm. Lietots abos STRICT patērētājos: (a) `x_scraper.fetch_user_replies` slotu tagad nosoda TIKAI pēc `TRANSACTION_KEY_ATTEMPTS=4` neveiksmīgām pārbūvēm (agrāk viens 404 slotu izslēdza uz visu procesu); (b) `x_mentions._probe_search_slot_health` pārbūvē atslēgu pirms slota skaitīšanas par neveselu — agrāk salabojams 404 varēja nolaist pūlu zem `SEARCH_MIN_HEALTHY_SLOTS` un pārslēgt VISU skrējienu uz timeline stratēģiju. Rate limits un citi izņēmumi ceļu neiet — tie nav atslēgas problēma.
- **`probe_x_cookies.py` verdikts vairs nemaldina:** tas pats retry + jauna rinda „transaction key: recovered after N rebuild(s) — a bootstrap problem, NOT the cookies", un docstring, kas brīdina PIRMS sīkfailu refresh. Pirmais skrējiens pēc fiksa: **5/5 slotu OK**, no tiem divi atgūti ar pārbūvi (slots 2 — 3, slots 5 — 1); vecais kods tos abus būtu saucis par BROKEN.
- **Noslēgts:** 9 jauni testi `tests/test_transaction_key_repair.py` (atgūšanās pēc pārbūves, budžeta izsmelšana, rate-limit caurlaide, no-op sargs, ja twikit iekšas pārvietojas); `check.sh` zaļš (1597 passed).

## 2026-07-25 — Attēla faila vārds seko pārskata SUBJEKTA datumam, ne `created_at`

`_brief_slug()` (`src/graphics/cli.py:56`) būvēja faila vārdu no `created_at`, t.i. no brīža, kad rinda tika ierakstīta. Vakara rutīna regulāri glabā pēc pusnakts, tāpēc attēla vārds aizgāja uz nākamo dienu un vairs nesakrita ar blog URL, kamēr render puse jau lietoja subjekta datumu. Mērogs: **33 pārskati**, kuriem `topic` datums atšķiras no `created_at`.

Labots: slug ņem subjekta datumu no `topic` (dienas → tās dienas datums, nedēļas → nedēļas sākums), ar fallback uz `created_at` vecajām rindām. Tas notur social-thread `{DATE}-…-og.jpg` konvenciju. Vārti: 3 testi `tests/test_graphics_cli.py`. **Vēsturiskie faili nav pārsaukti** — atsevišķs solis, ja kādreiz vajag.

Tas pats princips, kas vēlāk tika nostiprināts `brief_subject_date()` (sk. § Pārskata identitāte) — pārskata identitāte ir tā subjekta diena, nekad `created_at`. *(Ieraksts uzrakstīts 2026-08-01, kad BACKLOG kompakcija atklāja, ka šis labojums bija fiksēts tikai BACKLOG apakšpunktā un nekur citur.)*

## 2026-07-25 — Laika logu cutoff `isoformat()` 'T' slazds — logi klusi bija par dienu īsāki

- **Sakne:** pieci vaicājumi rēķināja robežu kā `(now_lv_dt() - timedelta(days=days)).isoformat()` un salīdzināja to pret kolonnām, kurās laiks glabājas ar ATSTARPI (`now_lv()`, SQLite `CURRENT_TIMESTAMP`). SQLite salīdzina kā virknes, un `" "` (0x20) šķiro PIRMS `"T"` (0x54) → `"2026-07-24 21:16:07" >= "2026-07-24T00:16:07"` ir **FALSE**. Rindas, kas krīt uz pašas robežas DATUMA, izmeta neatkarīgi no pulksteņa laika: `days=7` logs klusi kļuva par sešām dienām ar astīti.
- **Kāpēc tik ilgi nepamanīts:** slazds nostrādā tikai tad, kad glabātā laikspiedola datums SAKRĪT ar robežas datumu. Uz LV mašīnas „tagad" ir dienu priekšā `days=1` robežai, tāpēc lokālais `check.sh` bija zaļš visu laiku. Publiskā spoguļa CI (UTC runneris) 2026-07-24 21:16 UTC iekrita joslā, kur runnera datums = LV robežas datums, un pazuda VISI fixture dokumenti — 6 kritieni `test_analyze.py` + `test_post_launch_fixes.py`. Reproducēts lokāli ar pulksteņa nobīdi: bez fiksa 6 failed, ar fiksu 37 passed.
- **Fix:** jauns `src/db.py::lv_cutoff(days)` — atgriež robežu glabāšanas formātā (`"%Y-%m-%d %H:%M:%S"`) ar docstring, kas nosauc slazdu. Piecas izsaukumu vietas pārliktas uz to: `analyze.py` ×3 (`get_pending_politicians`, `get_politician_documents`, `get_existing_claims`), `matcher.py::link_politicians_to_documents`, `tools.py::search_documents`. **Noteikums turpmāk:** salīdzinājumam pret glabātu laikspiedolu lieto `lv_cutoff()`, nekad `.isoformat()`. (`src/render/*.py` `.isoformat()` izsaukumi ir uz `date` objektiem — tie dod `"YYYY-MM-DD"` bez `T` un paliek pareizi.)
- **Noslēgts:** 5 jauni testi `tests/test_lv_cutoff_format.py` ar FIKSĒTU pulksteni (nevis sienas laiku), lai kritums nebūtu atkarīgs no diennakts stundas — t.sk. tests, kas tieši nostiprina, ka dokuments uz robežas datuma logā IR, un tests, ka fixs logu paplašina atpakaļ uz `days`, nevis noņem robežu. `check.sh` zaļš (1589 passed).
- Saistīts: BACKLOG § Timestamp glabāšana nav standartizēta — šī ir tās pašas jauktā-tz saimes ceturtā izpausme (pēc tensiju `created_at`, graphics slug datuma un `DATE('now')`=UTC).

## 2026-07-24 — `analyses` dublētās rindas — UPSERT NEIEVIEST

> Pārcelts no BACKLOG 2026-08-05.

Sākotnējā premisa (viens 07-24 dublikāts → vajag UPSERT uz `(opponent_id, period_start, period_end)`) **datos neapstiprinās, un UPSERT būtu aktīvi kaitīgs.** Mērījums: 938 dublētu grupu, **1612 lieku rindu**, izlīdzināti pār 2026-03…07 — tie ir rutīnas RĪTA un VAKARA viļņi, ne pārrakstīšanas. Piemēri 07-24: id 6660 (`["Vēlēšanas"]`, 17:42) pret 6713 (`["Valsts kapitālsabiedrības"]`, 19:38); 6662 (`["Koalīcija un partijas"]`) pret 6715 (`["Korupcija un KNAB"]`) — dažādi doki, dažādas tēmas. UPSERT tos apēstu klusi, t.i. uztaisītu tieši to zaudējuma klasi, kuru backlogs citur sargā.

Faktiskais defekts ir šaurs: **tas pats vilnis, kas rakstīts divreiz** pēc neveiksmīga pirmā mēģinājuma (6694+6699, `opponent_id=156` — 6694 dzēsts 2026-07-24, `data/{fix,rollback}_dup_analysis_6694_2026-07-24.sql`). Ja kādreiz vērts automatizēt, tad tikai TAS: brīdinājums, kad tās pašas dienas jauna rinda ir gandrīz identiska esošai (tas pats `key_topics`, teksta līdzība), NE atslēgas-līmeņa UPSERT.

Ietekme paliek kosmētiska — `claims` tabulā nav `analysis_id` FK (bāreņu nav), ražošanas lasītāji (`routine.py`, `analyze.py`, `coverage.py`) izmanto `MAX(created_at)`/`NOT EXISTS`, `src/render/` `analyses` nelasa vispār; vienīgā redzamā seka ir ops dashboard aktivitātes lente (`dashboard/views/activity.py`), kas rāda politiķi divreiz — pareizi, jo divas analīzes tiešām bija.

## 2026-07-24 — Retvīti glabā pilno oriģinālu (140-rakstzīmju apraušana novērsta)

- **Sakne (BACKLOG 07-24):** `_normalize_tweet` ņēma retvīta paša `full_text`, kas X legacy formātā ir `RT @user: …` apcirsts 140 rakstzīmēs. Mērījums pār visu DB: **11 245 RT doku, no tiem 7 495 tieši 140 rakstzīmju** (maksimums 152; >140 tikai 81) — pretstatā ne-RT tvītiem tajā pašā dienā līdz 4410. Tā nav satura īpašība, bet ingesta robeža.
- **Cena nav ekstrakcija, bet linkošana:** kails retvīts tāpat nav pirmās personas pozīcija (skip-list), BET `link_politicians_to_documents` skenē `content` — politiķis, kas pieminēts tikai aiz apraušanas, netiek piesaistīts. Kluss pārklājuma robs, ne redzama kļūda; novēroja seši paralēli ekstrakcijas aģenti neatkarīgi.
- **Fix** (`src/x_scraper.py`): jauns `_tweet_text()` — kad `tweet.retweeted_tweet` nav `None`, teksts tiek pārbūvēts kā `RT @{oriģināla autors}: {pilnais oriģināls}`. **`RT @` prefikss ir load-bearing** (`src/render/x.py::is_rt`, `src/render/parties.py` `NOT LIKE 'RT @%'`) — tas saglabāts ar nolūku. `source_url` paliek RETVĪTOTĀJA statuss (tas ir doks, kas mums pieder). Trīs fallbacki: tukšs oriģināls → vecais teksts; oriģināls bez `user` → handle no `RT @…:` prefiksa; twikit payload drift (`retweeted_tweet` parsē `_legacy` iekšas) → vecais teksts, nevis zaudēts tvīts.
- **Noslēgts:** TDD — 7 jauni testi `tests/test_x_scraper_retweet.py`; `check.sh` pilnībā zaļš (1584 passed). **Forward-only** — vēsturiskie 11 245 RT doki paliek apcirsti; backfill (re-fetch pa `fetch_tweet_by_id`) ir atsevišķs BACKLOG punkts.

## 2026-07-24 — Preflight interpretatora guard: nulles-claim analīze vairs neizdodas klusi

- **Sakne (BACKLOG 07-24):** vidē bez embeddings steka `save_analysis()` AR claims krīt godīgi (`status="failed"` + `transaction_rolled_back`, atomicitāte tur), **bet nulles-claim analīze izdodas ar `status="success"`** — tā nekad nesasniedz `embed_text` (`if claims:` zars). „0 pozīciju" salauztā vidē izskatās identiski pareizam „izlasīju, nav ko ekstraģēt" — tieši Working Conventions § *Silent success is a defect class* forma. 07-24 seši aģenti uz tā uzkāpa; visi atkopās, bet tikai tāpēc, ka katrs pats to pamanīja.
- **Fix** (`src/preflight.py` → `ensure_analysis_env()`, izsaukts kā PIRMAIS solis `save_analysis()`, pirms jebkura claim-skaita zara): `importlib.util.find_spec` pārbauda `sentence_transformers` + `simplemma`; trūkstot — `RuntimeError`, kas nosauc gan neveiksmīgo `sys.executable`, gan repo `.venv` interpretatoru (`repo_python()`). Rezultāts memoizēts (guards katrā izsaukumā nedrīkst pārstaigāt `sys.path`).
- **Kāpēc atkarība, ne `sys.executable` pret `.venv`:** atkarības pārbaude paliek godīga ne-Claude-Code harnesiem (`wiki/operations/portability.md`) — jebkurš interpretators, kas SPĒJ embedot, iziet cauri, lai kur dzīvotu tā venv.
- **Noslēgts:** TDD — 4 jauni testi `tests/test_preflight.py` (veselā vidē iziet; trūkstot stekam met ar interpretatora ceļu ziņā; **nulles-claim `save_analysis()` salauztā vidē met**, ne atgriež success; memoizācija); `check.sh` pilnībā zaļš (1584 passed). Papildina 07-24 `claim-extractor.md` Step 4 prompta brīdinājumu ar koda līmeņa vārtiem.

## 2026-07-24 — T7 slēgts: brief skelets vairs klusi nemet tēmas (Pārējās tēmas tabula)

- **Sakne (T7, atkārtojies vismaz 6×):** `generate_daily_brief()` emitēja `###` sekcijas tikai top-5 tēmām pēc `interest_score` (skaits + spriedzes×3 + pretrunas×2) — bez salience, bez catch-all. Empīriskais mērogs (21 d audits pirms fixa): **nomestas 213 tēmas, no tām 98 svarīgas** (salience ≥0.7 vai ≥3 pozīcijas) — ~5/dienā; 07-23 nometa 5-pozīciju tēmu (Budžets un finanses) un Valaiņa 90 milj. raķešu ražotni. Operators/brief-writer caurumus lāpīja ar roku katru dienu.
- **Noraidītais ceļš (dati neatbalsta):** `MAX(salience)` svars rangā — salience skala saspiesta (84% claims 0.6–0.8; 54% tēmu sasniedz ≥0.7), svars paceltu pusi tēmu vienādi un rangu nemainītu. Neviena tjūnojama parametra fixā nav.
- **Fix** (`src/briefs.py`): (1) pilnas `###` sekcijas = top-5 pēc `interest_score` (rangs neaiztikts) **+ jebkura tēma ar cnt≥3** (ciets slieksnis); (2) viss atlikušais → viena kompakta `### Pārējās tēmas ({n} pozīcijas {m} tēmās)` tabula (Politiķis | Partija | Tēma | Pozīcija | Avots), tēmas kārtotas pēc `MAX(salience)` DESC — salience der kārtošanai, ne rangam; (3) `matched_topics` = tikai pilno sekciju tēmas (Pārējās tēmas konteksta piezīmes iet esošo unmatched ceļu); (4) jauns `_source_link()` helperis (domēna-linka bloks vairs nav dublēts). **Publicētā formāta izmaiņa (operatora apstiprināta):** Pārējo tabula parādās arī publiskajā pārskatā — caurskatāmības garantija, ka nekas nav izmests.
- **`brief-writer.md` promocijas noteikums:** tabula SAGLABĀ sarakstā; aģents DRĪKST pacelt dienas-būtisku rindu/tēmu uz pilnu sekciju (pārceļot rindas, saglabājot avotus, samazinot tabulas skaitītāju); klusi dzēst rindas AIZLIEGTS — rinda tabulu pamet tikai ar promociju.
- **Noslēgts:** TDD — 6 jauni testi `tests/test_briefs.py` (cnt≥3 ārpus top-5 → pilna sekcija; solo → tabulā ar avota linku; salience kārtojums; ≤5 tēmu diena bez tabulas; vienskaitļa formas); check.sh zaļš (1572). Stress-tests uz 07-23 prod datiem: 10 pilnas sekcijas + Pārējās (20 poz. 14 tēmās), tabulas augšā Aizsardzība 0.85 (tieši vecā skeleta pazaudētais saturs). CLAUDE.md T7 noteikums pārrakstīts uz jauno semantiku.

## 2026-07-24 — Rutīnas 2. soļa statuss: analyses rinda vairs nemaskē vēlāk ienākušus dokus

- **Sakne (BACKLOG 07-16):** `_check_analysis` signāls (a) — šodienas `analyses` rinda — bija absolūts: rīta backfill radīja šodienas rindas, un pa dienu VĒLĀK ienākušie doki politiķi tāpat rādīja "analizētu" (07-16: statuss 12 pending, reāli 20 — Kulbergs 9 unreviewed doki, Rinkēvičs 6, Rajevskis 5 maskēti; rutīnā bija vajadzīgs tiešā SQL workaround).
- **Fix** (`src/routine.py::_check_analysis`): (a) tagad sedz tikai dokus, kas scrapoti PIRMS politiķa jaunākās šodienas analyses rindas — vēlāk ienācis unreviewed subject-doks politiķi atkal atver kā pending. Zem-cap paliekas (bare-RT u.c., ko sesija redzēja un apzināti atstāja) paliek "done" kā līdz šim. **Mixed-tz nianse:** `documents.scraped_at` ir LV (`now_lv()`), `analyses.created_at` UTC → salīdzinājums caur `datetime(MAX(created_at), '+3 hours')`; bez nobīdes salīdzinājums melo 00:00–03:00 LV logā, tieši backfill laikā (atsevišķs regresijas tests to nosargā).
- **Noslēgts:** TDD — 4 jauni testi `tests/test_routine.py::TestCheckAnalysis` (vēlāks doks → pending; agrāks → done; tz-nobīdes obligātums; vairākas rindas → MAX sedz); 27 esošie neaiztikti; pilnais `check.sh` zaļš. Rutīnas workaround ("pending no tiešā SQL") vairs nav vajadzīgs.

## 2026-07-24 — Reply-tvītu autora piesaiste: autors = subject arī caur svešu plūsmu

- **Sakne (BACKLOG 07-23, doc 72542):** `_store_tweets` autora handle salīdzināja tikai pret FETCH-konta politiķa handles — kad tracked politiķa paša tvīts ienāca caur CITA politiķa plūsmu (reply/mentions konteksts), doks palika ar (fetch-īpašnieks, 'mentioned') un autora `subject` junction NEBIJA; `insert_document` content-hash idempotence (return None, links nomesti) neļāva to pievienot arī vēlākā paša timeline fetch. Šuvajeva reply Kulbergam par Tet/LMT tāpēc ekstrakcijas triāžā bija neredzams kā viņa pozīcija.
- **Fix (a)** `src/social.py::_store_tweets`: viens vaicājums pār VISIEM `platform='twitter'` kontiem → `author_map` (handle→(pid, feed_type)); ja tvīta autors ir CITS reģistrēts `first_party` politiķis, pievieno `(autora_id, 'subject')` papildus līdzšinējai fetch-īpašnieka lomai (relay plūsmās — bez fetch-īpašnieka linka kā līdz šim). Relay-piederīgi autora handles (org konti) `subject` nedabū — relay konvencija paliek text-scan ziņā; inactive kontu handles skaitās (īpašumtiesības nebeidzas).
- **Fix (b)** `src/db.py::insert_document`: content-hash dublikāta zarā `politician_links` tagad MERGE (`INSERT OR IGNORE`) uz esošā doka — bet TIKAI, ja sakrīt `source_url` (sargs: identisks teksts zem cita URL = copypasta, ko nedrīkst piepotēt pirmajam dokam). Joprojām atgriež `None`, lai izsaucēji nepār-embedo. Platform='web' URL-update zars neaiztikts.
- **Noslēgts:** TDD — 5 jauni testi `tests/test_social.py` (cross-feed autors, dedup merge, copypasta sargs, relay plūsma, relay-autors), 3 esošie neaiztikti; `check.sh` pilnībā zaļš (1559 passed). Vēsturiskais backfill PIEMĒROTS 2026-07-24 (operatora apstiprinājums): 218 trūkstoši (autors, 'subject') junctions (top: Lapsa 56, Stendzenieks 18, Vanags 16, Liepnieks 14; t.sk. incidenta doc 72542 @suvajevs), pāris `data/{fix,rollback}_twitter_author_subject_backfill_2026-07-24.sql`; pēc-audits: 0 trūkstošu.

## 2026-07-24 — KNAB pāreja uz JSON API (T12 SPA pārbūve)

- **Sakne:** KNAB ap 07-23 pārbūvēja `info.knab.gov.lv` par JS SPA — vecās servera-renderētās tabulas pazuda (lapas ~730 B čaulas), live fetch atgriezās ar 0 ierakstiem. Pēc T12 — formāta maiņa, ne datu izzušana.
- **Fix:** fetch slānis `src/knab.py` pārrakstīts uz jauno JSON API (`/api/parties` + `/api/payments?party_public_id` ziedojumiem; `/api/declarations` + `/api/reports` + detaļu galapunkti deklarācijām; lapas 1-indeksētas, `limit` parametrs — **default 20!**).
- **Kritiskie punkti:** (a) **legacy dedup sargs** — vecās sintētiskās `knab_id` atslēgas (`datums-donors-summa-partija[:20]`) pret jaunajām `public_id`; ierakstiem ar datumu ≤ `LEGACY_CUTOFF_DATE` (2026-04-08, pēdējais HTML skrējiens) satura-līmeņa pārbaude (datums+partija+donors+summa ±0.01) ar case-fold PYTHONĀ (SQLite `UPPER()` neloka diakritikas!) — bez tā pilns re-fetch dublicētu ~30k rindas; (b) LVL→EUR pie 0.702804 (paritāte ar legacy: 500 LVL→711.44); (c) deklarāciju detaļu `rows` kartēšana caur esošo `FIELD_MAP` ar sekcijas vārtiem (naudas plūsmas sadaļa atkārto "5. Reklāmas pakalpojumi" — bez vārtiem klobotu `expenses_advertising`).
- **Paritāte verificēta:** PROGRESĪVIE 2024 gada pārskats — visi 7 lauki sakrīt ar legacy rindu; 2 LPV ziedojumi abos avotos — sargs korekti izlaiž. 48 testi zaļi; live tests atgriež 466 ziedojumus no 1 lapas. Legacy HTML parseri paturēti ar piezīmi (izņemšana = atsevišķs lēmums).
- **API blakusieguvumi:** pilns CSV eksports (`/api/payments/export-all.csv`, bez public_id) un 74 954 maksājumi pret mūsu 30 260 (visas partijas + pilnāka vēsture) — nākamais KNAB rubrikas skrējiens ienesīs iztrūkstošo tracked-partiju daļu.
- Saistītie tās pašas dienas fixi (atsevišķi commiti): LVL konversijas drifta 1221 dublikātu sanācija + sarga original-amount zars; nulles-veidnes deklarāciju finanses → NULL (15 viltus critical); TRACKED_PARTIES +ASL/SV-AJ.

## 2026-07-24 — `search_similar_claims` kNN filtru pushdown (izspiešanas fix)

- **Sakne (diagnoze 2026-07-23):** kNN gāja pret VISU `claim_vectors` indeksu (~553k) ar `k=top_k`, filtri (`opponent_id`, `claim_type_filter`, `speaker_scope`) tikai PĒC tam Python cilpā; sqlite-vec `k` griesti 4096 → politiķa vēsture strukturāli izkrita (simptoms: "tikai self-match" / `[]` uz gandrīz identisku tekstu). Tas pats cēlonis 07-18 simptomam "id=60 Stendzenieks atgriež `[]` vai svešu claim ar similarity 0" — vektori bija rakstīti, izspiešana tos slēpa.
- **Fix:** visi trīs filtri iebīdīti kNN vaicājumā ar `claim_id IN (apakšvaicājums)` (`src/db.py::search_similar_claims`; vec0 `claim_id` = rowid alias, `rowid IN` atbalstīts pinnētajā sqlite-vec v0.1.9 — empīriski verificēts uz prod DB). `top_k` tagad = budžets politiķa paša filtrēto claims ietvaros; post-filtrs paturēts kā defense-in-depth; tukšs `claim_type_filter=[]` joprojām atgriež `[]`.
- **Noslēgts:** TDD regresijas testi `tests/test_db.py::TestSearchSimilarClaimsKnnPushdown` (izspiešana + claim_type + speaker_scope pushdown ar deterministiskiem vektoriem caur `embedding_bytes`). Carrier teksti atjaunoti: `contradiction-hunter.md` (truncation-trap rindkopa → jaunā semantika; in-memory kosinusa ceļš pāru medībām paliek), `wiki-tools.md`. Prod sanity: id=60 top_k=10 → 10/10 paša position claims (agrāk 0–2). T9/T10 nemainās — 0.80 kosinuss = "tā pati tēma", ne pretēja nostāja.

## 2026-07-23 — Stingrā CSP: drošības galvenes + viss inline JS uz assets/*.js

- **Kāpēc:** ārējs drošības audits atklāja, ka vietnei nav nevienas drošības galvenes; pēc to pievienošanas audits pamatoti iebilda pret `'unsafe-inline'` skriptiem CSP. Dziļākais pamatojums: vietne pārpublicē skrāpētu ziņu/X tekstu — stingrs `script-src` nozīmē, ka pat ja escaping kļūda kādreiz ielaistu ļaunprātīgu skriptu lapā, pārlūks to atsakās izpildīt (XSS aizsardzības tīkls zem mūsu koda).
- **Galvenes** (`assets/htaccess.template`, kopētas caur `static` render domēnu): HSTS (`max-age=31536000`, bez `includeSubDomains` — apakšdomēnu HTTPS pārklājums nav verificēts), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, un CSP ar `script-src 'self' https://cloud.umami.is https://d3js.org` — **BEZ `'unsafe-inline'`**. `style-src` apzināti patur `'unsafe-inline'` (style="" atribūti ir visā vietnē; auditi to nesoda). Jauns ārējs resurss = papildinājums CSP sarakstā, citādi tas klusi nolūst TIKAI produkcijā (lokālam priekšskatam galvenes nav).
- **Inline JS evakuācija (~2000 inline bloku 800+ lapās → 14 jauni `assets/*.js`):** `theme-init.js` (bloķējošais FOUC aizsargs + fontu media-swap uz `link[data-font-async]` — aizstāj `onload=` triku), `chrome-v1.js` (viss chrome IIFE; cuelume imports caur `document.currentScript`, ne vairs `{{ assets_prefix }}`; + vispārīgā `[data-card-href]` kartīšu delegācija), un pa lapu saimei ixv1/anv1/ppv1/ptv1/blv1/lkv1/prv1/spv1/znv1/sav1/stv1/fnv1. Per-lapas dati → ne-izpildāmi `<script type="application/json" id="…">` bloki (CSP tos neskar); visi `on*=` atribūti → `data-*` + delegācija. `ms-a11y.js` ieguva deleģēto multi-select meklēšanas filtru (24 `oninput=` noņemti; per-lapas `window.filterOptions` kopijas dzēstas).
- **Kārtības atkarības saglabātas:** `blv1.js` lādējas SINHRONI aiz `bmv1.js`; `sav1.js` — aiz d3; chart-atkarīgie faili `defer` aiz `chart.min.js` (defer saglabā secību). saites `renderNodeSection` innerHTML-`onclick` (zem stingrās CSP mirst KLUSI klikšķa brīdī) → `[data-section]` delegācija.
- **Chrome-sync kontrakts atjaunināts** (`_CHROME_SPECS`): bāzes fragments tagad = `<nav>` + ārējais `chrome-v1.js` src-tags; curated-mērķa regex ar opcionālu tieši sekojošu skriptu (negatīvs lookahead izslēdz application/json blokus) — idempotents UN izlabo **pre-eksistējošu bugu**: vecās iesaldētās curated lapas nesa novecojušu inline chrome skriptu, ko sync dublēja (`statistika.html` būvē bija DIVI chrome skripti). Fragments tagad renderē arī `{{ assets_version }}` (`_rendered_chrome` jauns parametrs). `_resolve_assets_version()` hardkodētais 7 failu saraksts → `style.css + glob("*.js")`.
- **Curated re-freeze:** statistika dashboard + 10 detaļlapas pārģenerētas no nemainīta `data/csp.db` un no jauna iesaldētas `curated/atmina/` (diff = tikai head/skripti/JSON bloki + ~3 mēnešu uzkrātā chrome novirze — favicon komplekts, SVG logo, skip-link); `finanses.html` rediģēts ar roku (3 `data-filter-table` ievades, theme-init tags).
- **Invariants noslēgts:** jauns `tests/test_no_inline_js.py` — neviens izpildāms `<script>` bez `src=`, neviens `on*=` atribūts templotēs, curated lapās un JS virknēs (innerHTML ceļš). Char bāzlīnijas pārģenerētas vienreiz. Verifikācija pirms deploy: lokāls serveris ar iešūtu jauno CSP galveni + Playwright pārstaigāja ~20 lapu saimes ar interakcijām — 0 pārkāpumu; tas pats atkārtots produkcijā pēc deploy.
- **Procesa mācība (dārga):** 9 paralēlie implementācijas sub-aģenti vienā darba kokā — viens patvaļīgi izpildīja `git stash`, noslaukot pārējo necommitēto darbu; atgūts no dangling stash commit (`git fsck --unreachable` → `git checkout <sha> -- .`) ar pilnu failu-pa-failam rekonsiliāciju. Turpmāk paralēlo sub-aģentu briefos: git TIKAI lasāmi (`status`/`diff`/`log`); stash/checkout/restore/reset/clean/commit AIZLIEGTI.

## 2026-07-22 — Bloku etiķete "Ārpus Saeimas" → "Bez Saeimas frakcijas"

- **Kāpēc:** bloks visās virsmās grupē pēc PARTIJAS statusa (`parties.coalition_status='not_in_saeima'`, personu lapā arī `other`), nevis pēc deputāta mandāta — tāpēc tajā nonāk arī ievēlēti deputāti, kuru partijai Saeimā nav frakcijas. Precedents, kas kļūdu padarīja redzamu: Oļegs Burovs (GKR, 5484 balsis, Valsts pārvaldes un pašvaldības komisijas priekšsēdētājs) 22.07 pārskatā stāvēja rindā "Ārpus Saeimas". Vecais nosaukums lasītājam meloja; jaunais ("Bez Saeimas frakcijas") ir patiess visiem bucketa iemītniekiem — gan ārpus-Saeimas partijām (ASL, MMN), gan deputātiem bez frakcijas (GKR), gan personu lapas bezpartijas personām.
- **Kur nomainīts:** `src/briefs.py` (dienas + nedēļas skeleta bloku tabula), `templates/personas.html.j2` + `assets/pnv1.js` (personu lapas sānu joslas grupa un filtra čips). DB statusa vērtības (`not_in_saeima`/`other`) NEmainās — tikai cilvēklasāmā etiķete.
- **Kas apzināti NAV mainīts:** vēsturiskie publicētie pārskati (DB `daily_brief`/`weekly_brief` rindas, `wiki/dailies`, `wiki/weeklies`, rollback SQL, testu fikstūras) — tie ir saglabāts teksts ar veco etiķeti; 22.07 pārskats atjaunināts, jo bija dienas aktuālais. Nākotnes ģenerācijas etiķeti ņem no koda.
- 22.07 pārskatam bloku sadaļā pievienots paskaidrojošs teikums par Burova gadījumu (deputāts bez frakcijas) — piemērs, kā bloka semantika lasāma.

## 2026-07-22 — Video pipeline E2E operacionāls (Task 19 diarize atbloķēts)

- **Docker plāns ATCELTS kā nevajadzīgs** — pārskatē izrādījās, ka (a) vecais k2/speechbrain bloķētājs bija speechbrain 1.1.0 artefakts, nevis platformas problēma, (b) torch venv tāpat ir CPU-only, tātad CUDA 11.8/Pascal pamatojums neattiecas.
- **Risinājums kodā:** pyannote.audio 3.3.2→4.0.7 (hub 1.x saderība), speechbrain IZŅEMTS no venv (pyannote 4.x to neprasa; abas released līnijas lauztas — sk. requirements.txt piezīmi), `diarize.py` padod dekodētu waveform caur soundfile (apiet torchcodec FFmpeg-shared-DLL prasību uz Win) + pyannote 4.x strukturētā output atbalsts. check.sh zaļš, embeddings smoke OK zem torch 2.13.
- **Pilns cikls izgājis uz reāla KNL klipa:** fetch → ASR (AiLab LV fine-tune default) → diarize community-1 → align → heiristika → finalize → `@video-extractor`. Ekstrakcijas STOP-gate verificēts uz karstas pārrunāšanās (0 claims, ziņojums, `reviewed_at` neaiztikts); testa dokuments 71981 dzēsts (`data/rollback_video_test_doc_71981_2026-07-22.sql`). CLAUDE.md inv #13 = operacionāls; atlikusī kvalitātes problēma (diarizācijas robežu asiņošana uz crosstalk) — BACKLOG § Video ingest. (3 agrāki smoke-fixi — extractor_args `player_client`, `int8_float32` Pascal, ASR CPU fallback — `018c12c`.)

## 2026-07-21 — Vēsturisko pretrunu triāžas paliekas slēgtas

- Operatora apstiprinājums: pretrunas id=7 un id=31 dzēstas apzināti; id=30/32/33/34 visas `reviewed=1, confirmed=1` (publicētas). Nekas vairs nav darāms.

## 2026-07-19 — claim-extractor Critical Rule #9: ārpus-tvēruma failu dzēšanas aizliegums

- 07-18 ekstrakcijas 1. vilnī kāds sub-agents (vainīgais nepierādāms; netieša norāde uz Vītola aģentu) izdzēsa pirms-sesijas untracked `_scratch_claims.txt` + `_scratch_pairs.json` (neatgriezeniski; visticamāk 07-17 pretrunu medību starprezultāti, pārģenerējami no DB). Fix: `.claude/agents/claim-extractor.md` Critical Rules #9 — aizliegts dzēst/pārrakstīt failus ārpus uzdevuma tvēruma (deploy-aizliegums pārcelts uz #10; uz veco numuru atsauču nav, pārbaudīts). Papildina 07-23 CSP ieraksta git-mutāciju mācību.

## 2026-07-17 — Balsojumu sekcijas pārbūve (viens renderēšanas ceļš) + klātbūtnes reģistrāciju izslēgšana + UI skaņas + gaišās tēmas aizsardzība

- **"Deputātu klātbūtnes reģistrācija" izslēgta no balsojumu renderēšanas** (`13e1cd0`, operatora lēmums): 316 reģistrācijas notikumi (visi totāli 0, maldinošs `result='Noraidīts'`) nav balsojumi — tie aizsprostoja saraksta augšu, piepūta matricas JSON ar `.`/`X` kolonnām un kropļoja `total`/`accepted_pct`/`attendance_pct` saucējus. Filtrs `_fetch_votes` SQL līmenī ar **prefiksa** formu (`NOT LIKE 'Deputātu klātbūtnes reģistrācija%'`) — `%reģistrācij%` noķertu īstus balsojumus (Civilstāvokļa aktu reģistrācijas likums). **DB rindas paliek** — T8 pilnīguma auditi pēc `(vote_date, vote_time)` tās joprojām redz. Sedz `tests/test_votes_registration_filter.py`. Blakusatradums → BACKLOG: reģistrācijas individuālās rindas glabā HTML-entītiju garumzīmes (`Re&#291;istr&#275;jies`, ~30k rindu; pēc filtra nekur nerenderējas).
- **balsojumi.html "Option 2": SSR vote-card ceļš dzēsts, kartītes VIENMĒR renderē klients** (`13e1cd0`): lapa 6,4 MB → **425 KB (−93 %)**. Sakne: katra no 200 SSR kartītēm nesa slēptu `<details>` tabulu ar ~90 deputātu balsojumiem (~25 KB katra) — tie paši dati, ko `assets/bmv1.js` jau lādēja kompaktajā matricas JSON un mācēja renderēt SSR-identiski (`archiveBuildCard`). Tagad: sākums no recent-sharda (105 KB br; jauns `opts.wantFull` uz `balsojumiArchiveRender`), pilnais arhīvs tikai pie filtriem vai lappojot dziļāk par ~gadu (newest-first kārtība recent padara par pilnā prefiksu — offseti pārdzīvo eskalāciju). `_fetch_votes` N+1 (~11,4k vaicājumi/renderā) → 1 batchots `GROUP BY vote_id, faction`; deputātu filtra opcijas no `DISTINCT` vaicājuma; `votes` konteksta atslēga veidnei noņemta; neto −104 rindas. **Dziļie linki:** svaigs `#vote-N` izceļas sarakstā; ārpus renderētā — tūlītēja atkāpe uz Matricu pirmajā renderī (regress noķerts diff-reviewā; vecā SSR semantika saglabāta). `<noscript>` piezīme JS-atkarībai. Sedz `tests/test_balsojumi_client_render.py` + `tests/test_fetch_votes_batched.py`.
- **`<meta name="darkreader-lock">` + dinamisks `meta[name=color-scheme]`** (`eeeb271`): Brave iOS "Night Mode" (DarkReader-bāzēts) gaišo tēmu pārkrāsoja olīvbrūnā puskrāsojumā (silto nokrāsu saglabājošā tumšošana + daļēja apstrāde). Vietnei ir pati sava tumšā tēma → darkreader-lock ir DarkReader dokumentētais "neaiztikt" signāls. Statiskais `content="light"` meta (kas tumšajā tēmā aicināja auto-dark rīkus tumšot jau tumšu lapu) tagad sinhronizējas ar aktīvo tēmu (agrīnais bootstrap + pārslēga sync). Sedz `tests/test_base_theme_meta.py`. Papildina 2026-06-13 gaišās tēmas ierakstu.
- **Opt-in UI skaņas (cuelume)** (`1c3bb25`, `42038c2`): skaļruņa slēdzis navigācijā (tēmas sviras dizaina valoda, `--switch-*` mainīgie), noklusēti IZSLĒGTS, stāvoklis `localStorage['atmina:sound']`. `cuelume@0.1.2` (MIT, 0 atkarību, Web Audio sintezē) vendorēts **verbatim** `assets/cuelume/` (+LICENSE), lādējas TIKAI ar lazy `import()` pēc ieslēgšanas — `./{{ assets_prefix }}` prefikss obligāts (bez `./` saknes lapās bare-specifier `TypeError`; regresijas asserts testā). Skaņas: ready (ieslēdzot), toggle (tēmas svira), success (kopēšana; jauns `atmina:copied` notikums), tick (tabi), page (iekšējie satura linki; ārējie avoti/enkuri klusi). Visa loģika VIENĪGAJĀ chrome skriptā — chrome-sync to pārnes uz kurētajām lapām. Sedz `tests/test_base_sound.py`.

## 2026-07-16 — Backlog slēgumu banda: partiju slug, stub re-ingest, db_path, brief skeleta fixi, NR kadence, Burova T6

- **Partijas lapas ceļš vairs nav raw short_name:** viena kanoniskā `_party_page_slug()` (`src/render/_common.py`): lower + failu-nedrošie simboli → '-'; ievadīta visos partijas-lapas URL punktos (parties.py, _orchestrator sitemap + Jinja filtrs, mediji.py, 2 templotes). Esošo 18 partiju URL nemainās (noslēgts ar DB-driven testu `tests/test_party_page_slug.py`); hipotētisks 'SV/AJ' → `sv-aj.html` (e2e tests).
- **Stub re-ingest 8/8:** `scripts/fix_stub_reingest_2026-07-16.py` (ingest_url `_default_fetch` ceļš) + rollback `data/rollback_stub_reingest_2026-07-16.sql`: visi 8 doki paplašināti (52683: 67→595w, 53312: 32→333, 53313: 32→310, 65226: 39→245 — diena.lv izrādījās BEZ paywall, 66455: 30→403, 66466: 67→489, 66471: 50→854, 66502: 43→360) un `reviewed_at=NULL` → ekstrakcija 07-16 vakara rutīnā.
- **db.py `db_path=DB_PATH` def-time binding izskausts:** visas 34 funkcijas 10 moduļos (db, preflight, knab×2, social_agent×3, saeima×2, vad) konvertētas uz `db_path=None` + izsaukuma-brīža resolvi pēc `get_db` parauga; vad/schema.py sentinel-salīdzinājums saglabāts ar eksplicītu resolvi pirms tā. Jauns tests `tests/test_db_path_late_binding.py`; 2 vecie testi, kas pinēja anti-paternu, pārrakstīti.
- **Brief skeleta fixu trio** (`src/briefs.py`, testi `tests/test_briefs.py`):
  - *Spriedžu tabulas tukšās iekavas bezpartejiskiem:* abi emit punkti (SQL top_tension_topics GROUP_CONCAT + Python Spriedžu tabula) → CASE/`_name_party()` helperis: party NULL/tukšs = kails vārds, nekad '()'. Pārējie emit punkti auditēti (weekly '—', telegram guard, sintēzes hinti — apzināti nemainīti).
  - *7-dienu logs vairs neievelk backfill pozīcijas nākamās dienas pārskatā:* vēsture — `_BRIEF_DAY_CLAIM_SQL` predikāta `created_at`-atzars (domāts pāris dienu vecu rakstu tveršanai) dublēja pozīcijas, kad iepriekšējā diena tika backfillota nākamās dienas rītā (07-13 gadījums: 8 07-12 pozīcijas ievilktas 07-13 pārskatā, izslēgtas manuāli). Fix = `already_briefed` NOT EXISTS: claim izslēgts TIKAI, ja tā stated-dienas daily_brief note publicēta/refreshota PĒC claim created_at (t.i., claim jau bija DB, kad dienu briefoja); vēlāk ekstraktētie (LDDK-klase) paliek iekļauti; same-day disjunkts neaiztikts. Smoke pret 07-16 reālajiem datiem + testi visiem 3 scenārijiem.
  - *DIENAS STATS = viens patiesības avots:* pozīciju skaits lieto to pašu `_BRIEF_DAY_CLAIM_SQL` predikātu kā ###-emisija; politiķu/org sadalījums eksplicīts — `N pozīcijas (M politiķu + K org)`, kad org>0 (LDDK-klase vairs nav klusi neredzama). Vēsturiskie 5 STATS-neatbilstības atkārtojumi (07-08..07-15) bija šī cēloņa sekas.
- **NEEDS_REVIEW kadence ieviesta** (commit `1c05e9e`): sakne — `@claim-extractor` prompts bija stale ("31 tēmas", bez `Sports`) → sporta pozīcijas krita `Budžets un finanses` ar NR; izlabots. Batch-triāža 49→0 (rollback `data/rollback_needs_review_triage_2026-07-16.sql`); iknedēļas NR triāžas solis `wiki/operations/weekly-routine.md` § 5 (procedūra ar embedding pārrēķinu + pārī rollback tur).
- **Burova T6:** Burovs ir GKR dibinātājs un priekšsēdētājs (godskalpotrigai.lv, viņa paša X doc 62254); Saeimas vēlēšanās kandidē no KOPĪGĀ ZZS-GKR saraksta Rīgā #3 — alianse, NE iestāšanās ZZS. UPDATE 'Bezpartejisks'→'Gods kalpot Rīgai' + rollback `data/rollback_burovs_party_gkr_2026-07-16.sql`. Bloku klasifikācijā paliek Neitrāli (GKR `coalition_status='not_in_saeima'`).
- **Svirskis (id=62) x_handle diverģence = nav kļūda:** ABI konti pieder pašam Svirskim — 'realNepareizais' ir viņa primārais oriģinālsatura konts ("Nepareizais" ir viņa paša X segvārds), 'ESvirskis' ir sekundārs pastiprinātājs (95% RT). Operatora lēmums: atstāt kā ir (id=62 inactive, dashboardā nerādās, abas rindas leģitīmas).

## 2026-07-04 — NEEDS_REVIEW pilnā triāža (126→0) + "Sports" kā 32. kanoniskā tēma

- **Viss NEEDS_REVIEW uzkrājums izvērtēts un iztīrīts: 126 → 0.** 7 program_promise atrisināti inline (sk. atsevišķo ierakstu zemāk pēc datuma); **119 vēsturiskie position/commentary** triažēti ar 9 paralēliem Opus sub-aģentiem (batči pa politiķiem, ≤15 claims; kopīgs noteikumu fails ar atļauto/aizliegto darbību sarakstu). Rezultāts: **110 CONFIRMED** (marķieris noņemts, reasoning papildināts ar "Izvērtēts 2026-07-04" lēmumu un pamatojumu), **4 RETOPICED** pēc topic_map kanona (532043 Stambulas konv.→Tieslietas, 532136 Goda ģimene→Sociālā politika, 532179 pieminekļi/vēsturiskā atmiņa→Ukraina un Krievija, 532385 politiskā filozofija→Koalīcija un partijas; visiem claim_vectors pārrēķināts), **5 eskalācijas** operatoram. Master rollback ar visu 119 oriģināliem `data/rollback_needs_review_historic_triage_2026-07-04.sql`. Dizaina princips: sub-aģentiem DELETE/stance-labojumi AIZLIEGTI (tikai eskalācija) — dzēšana ir operatora lēmums.
- **Eskalāciju izpilde (operatora lēmumi):** dzēsti 3 claims, kas pārkāpj ekstrakcijas doktrīnu — 531983 Jakovins (žurnālista otrās rokas konstatējums bez citāta), 532268 Madžiņš (insinuācija bez politikas nostājas), 532482 Liepnieks (stance = sarkasma interpretācija, citāts burtiski saka pretējo). Nevienam nebija atsauču pretrunās/piezīmēs. Rollback ar pilniem INSERT `data/rollback_needs_review_escalations_2026-07-04.sql`.
- **"Sports" pievienots kā 32. kanoniskā tēma** (operatora lēmums pēc 6 atkārtotas spiešanas gadījumiem: 06-18 ×2, programmas 07-02/04 ×2, triāžas eskalācijas ×2). Izmaiņas: `src/topic_map.py` (grupa + aliasi + `_SAEIMA_KEYWORD_MAP` ieraksts — apzināti daudzvārdu atslēgas, jo kails "sport" ir substring vārdos "tran**sport**a"/"ek**sport**a"), `src/render/_common.py` TOPIC_COLORS (#c9803d medaļu bronza), `src/graphics/visual_map.py` (skrejceļš + lauru vainags), CLAUDE.md 31→32, aģentu prompti (brief-writer, claim-extractor, contradiction-hunter). #532203 (Siliņa) un #532214 (Daugavietis) pārcelti uz Sports ar embedding pārrēķinu; `temas/sports.html` ģenerējas automātiski. "sporta infrastruktūra" alias apzināti PALIEK Pašvaldībās. Programmu konsolidētās kultūra+sports pozīcijas (AS #532831, JKP #532815) apzināti paliek Kultūrā — programmas pašas bundlē šīs jomas vienā sadaļā.
- **Procesa mācības:** (a) triāžas sub-aģentiem kopīgs noteikumu fails + master rollback PIRMS dispatch ir drošais paterns; (b) topic/stance maiņa VIENMĒR prasa claim_vectors pārrēķinu (embedding teksts = "topic: stance"); (c) viens marķieris bija "NEEDS_REVIEW " bez kola — strip loģikai jāsedz abi varianti.

## 2026-07-04 — save_analysis embedding precompute (lock fix) + get_existing_claims claim_type filtrs

- **"database is locked" zem paralēlā ekstrakcijas fan-out — atlikušā klase noņemta.** Diagnoze: `PRAGMA busy_timeout=30000` + `timeout=30.0` jau bija `get_db()` (2026-04), un `store_claim` standalone ceļš embedding skaitļoja pirms savas transakcijas — bet `save_analysis()` tur VIENU `with db:` transakciju pāri visam batčam, tāpēc pēc pirmā INSERT katrs nākamais `store_claim(db=db)` savu e5-small embedding (100ms–10s) skaitļoja jau ZEM turēta write-lock; N-claim batch = N embedding izmaksu lock-hold logā → paralēlie extractori gaidīja >30s (~4 reizes 2 dienās jūlija sākumā). Fix: `save_analysis` prekompilē visus batch embeddings PIRMS `with db:` (savienojums atvērts, bet transakcija nav sākta — lock netiek turēts) un padod tos caur jaunu opcionālu `embedding_bytes=` parametru (`db.store_claim` → `tools.store_claim`); lock-hold sarūk līdz tīriem INSERT. Atomicitāte (Data Contract #9) neskarta. **Kritiskā nianse:** prekompilētajam embedding tekstam jābūt baitu-identiskam iekšējam — topic vispirms caur `normalize_topic` (to `tools.store_claim` piemēro pirms db slāņa); pydantic `Claim` modelis topic/stance netransformē. Ekvivalences tests apzināti lieto topic, ko normalizācija maina (`NATO`→`Aizsardzība un drošība`), lai izlaista normalizācija kristu. Papildu mazināšana paliek pieejama: fan-out cap ≤8 orchestratorā.
- **`get_existing_claims` vairs neizgāž saeima_vote korpusu extractor-aģentu kontekstā.** Viss ~520k `saeima_vote` korpuss (2026-05-27 bulk imports) ir `created_at` <90d logā, tāpēc balsojumu-smagiem politiķiem funkcija atgrieza tūkstošiem rindu (~98% troksnis; pid=6 → 5060 rindas) katrā claim-extractor sub-aģentā. Jauns `claim_types=("position", "commentary")` default (SQL `IN` filtrs); `claim_types=None` = legacy visi tipi; atgrieztie dicti tagad satur `claim_type`. Iekšēju Python izsaucēju nav (tikai aģentu workflow) — droša default maiņa. Pretrunu detekciju neskar (tā iet caur `search_similar_claims` ar savu `claim_type_filter`).

## 2026-07-04 — UI dizaina audits: trīs fāzes + sākumlapas pārveide, deployētas tajā pašā dienā

> Ieraksts uzrakstīts **2026-08-03**, pārceļot pabeigto darbu no `BACKLOG.md`. Līdz tam tas bija pierakstīts TIKAI backlogā — t.i. pabeigts darbs dzīvoja atvērto darbu failā, un tāpēc to nedrīkstēja no turienes izgriezt. Visi zemāk nosauktie commiti pārbaudīti pret `git log`: deviņi no tiem ir datēti ar 2026-07-04.

**Trīs audita fāzes pabeigtas un deployētas 07-04.**

- **1. fāze — bāreņu saites, kartītes, mobilā navigācija.** Novērstas bāreņu lapas, sintēžu/analīžu kartītes pārliktas uz `-card`/`-thumb`/`-hero` webp variantiem ar variantu auto-ģenerēšanu image-sync solī, salabota mobilā ciļņu pārplūde un LV skaitļa saskaņa (`lv_plural`). Commiti `e704aa8`, `4140875`.
- **2. fāze — pieejamība.** `<th scope>`, skip-link, `aria-current`, virsrakstu hierarhija, `aria-label`/`aria-pressed`, diagrammu defer; `ms-a11y.js` deva tastatūras un ekrānlasītāja atbalstu filtru nolaižamajiem. Commiti `aa91e96`, `9eff88d`.
- **3. fāze — svars un tipogrāfija.** Balsojumu cilpu inline stili → CSS klases (**8,25 → 6,4 MB**), fontu grīda diakritikas lasāmībai (9px→10, lasāmais 10→11; share-kartes apzināti neskartas), 13 dublētu augšlīmeņa selektoru apvienošana un kanoniskā lūzumpunktu skala 600/768/900, meklētājs visās lapās (`nav`) + pretrunas ieteikumu indeksā (sg-index v3). Commiti `4254656`, `496aa4e`, `802c6e8`, `4f6c85f`.
- **Gotcha, kas maksāja vienu labojumu:** `.nav-links` ar `flex-wrap:wrap` mobilajā kolonnā aplauza paneli — risinājums `nowrap`.

**Sākumlapas pievilcības pārveide (landing redesign) — DONE + deployed 07-04 vakarā.** Plāns `docs/superpowers/plans/archive/2026-07-04-landing-redesign.md`, 11 commiti līdz `7f9eac9`. Saturs: „Šonedēļ 0" aizstāts ar faktiem, Līderu josla ar sejām, pārkārtota sekciju secība, hero countdown + karuseļa akcenti, pretrunu karšu clamp, tendenču grafiki zīmola krāsās.

**Atrisināts gala revīzijā:** `_fetch_tensions` dubultizsaukums un `#c25e5e` literālis.

**Kas NETIKA darīts un kāpēc** (paliek `BACKLOG.md`, lai to neatklātu no jauna): font-size/line-height tokenizācija atlikta apzināti (simti deklarāciju, mazs redzamais ieguvums); vēsturiskie lūzumpunkti 480/560/640/700 dokumentēti pie `:root` un migrē tikai tad, kad kāds pieskaras komponentei; `#8b8fa3` fallback literālis palika 24 vietās 12 failos. Un divi ne-defekti, kas jau reiz izmeklēti: gaišā tēma kā noklusējums ar dark `:root` ir apzināta (`c634c47`, 2026-06-13), un abi `!important` ir izsekoti un pamatoti (`802c6e8`).

## 2026-07-02 — Partiju programmu analīze: `claims.party_id` + `claim_type='program_promise'`

- **Jauna spēja: partijas vēlēšanu programmas kā partijas līmeņa saturs** (`c70bbfd`, merged master + pushots). Motivācija: 15. Saeimas kampaņā partijas publisko programmas; līdz šim tās varēja glabāt tikai kā līdera personīgās `position` pozīcijas (kā 07-01 ZZS/Valainis) — sajaucot partiju ar personu.
- **Datu modelis:** `claims.party_id` (nullable FK→`parties`) — migrācija `src/db.py` (idempotents PRAGMA guard, `speaker_id` paterns) + `schema.sql` kolonna. **Gotcha:** `idx_claims_party` TIKAI migrācijā, NE schema.sql — `executescript` izpildās pirms ALTER, indekss uz vēl-neesošu kolonnu gāž `init_db()` uz live DB. `opponent_id` paliek = saraksta līderis (carrier). Threaded caur `db.store_claim`/`tools.store_claim`/`analyze.save_analysis` (`party_id=` kwarg). Rollback: `data/rollback_claims_party_id_2026-07-02.sql`.
- **Konvencijas** (CLAUDE.md #4/#4a): `claim_type='program_promise'`; **viena konsolidēta pozīcija uz tēmu** uz programmas avotu (idempotences triple `(opponent_id, source_url, topic)` — vairāki solījumi vienā tēmā no viena URL sakristu). Izslēgšana no visām pozīciju virsmām ir **bezmaksas** — katrs render/brief/coverage vaicājums jau filtrē `claim_type='position'`; vienīgā jaunā virsma ir partijas lapas "Programma" cilne (`src/render/parties.py` fetch pēc `party_id` + tēmu grupēšana; `templates/partija.html.j2`). Jinja gotcha: dict atslēga `items` sadūrās ar `.items()` metodi → `promises`.
- **PDF ielādes ceļš** `scripts/ingest_url.py`: content-type/`.pdf` detektēšana → `pypdf` ekstrakcija (jau venv, 0 jaunu atkarību); `MAX_CHARS` 50k→200k (programmas garas; 50k klusi grieza asti).
- **YAGNI apgriezumi** (operatora "viss geniālais ir vienkāršs" revīzija): NAV atsevišķa `@program-extractor` aģenta (atkalizmanto `@claim-extractor` Opus ar programmas dispatch-promptu), NAV workflow failu (tiešs sub-aģentu dispatch), NAV bulk kandidātu loadera, NAV jauna `party_programs` galda.
- **Dati live:** ZZS 11 pozīcijas (party_id=3, carrier Valainis id=25, avots apollo.lv 07-01 raksts — kopsavilkums, ne pilnā programma; `zzs.lv/zzs-programma` 404) + NA 22 pozīcijas (party_id=4, carrier Indriksone id=72, oficiālā `nacionalaapvieniba.lv/programma/`). Deploy `--no-delete`, live verificēts. **Stale-avotu mācība:** web meklēšana atgriež vēsturiskās programmas (Providus=11. Saeima 2011, `apvienotaissaraksts.lv/programma`="divi pandēmijas gadi"=2022) — pirms ekstrakcijas verificē gada kontekstu saturā; abi stale doci dzēsti.

## 2026-06-22 — Nedēļas pārskata "Koalīcija vs Opozīcija" sadaļa + movers grafika opozīcijas joslas labojums

- **Movers grafika bloku josla rēķināja tikai top-6** (`src/briefs.py::generate_weekly_brief`): "Kas kustējās" SVG "Koalīcija / Opozīcija" josla summēja blokus tikai no top-6 kustētājiem, kas ir strukturāli koalīcijas pārsvarā (Kulbergam vien 31 pozīcija) → opozīcijas (sarkanais) segments vienmēr 0, pat nedēļās, kad opozīcija bija aktīva (15.–21.06.: opozīcija 19 pozīcijas). Labots: josla rēķinās pār VISĀM nedēļas pozīcijām (koalīcija 140 : opozīcija 19; audience konti izslēgti). Regresijas tests `test_weekly_bloc_bar_counts_opposition_outside_top6` (sēj opozīcijas deputātu ārpus top-6, pārbauda sarkano segmentu > 0).
- **Nedēļas skelets tagad emitē `## Koalīcija vs Opozīcija`** — tāda pati 5-kolonnu tabula kā daily (Bloks / Pozīcijas / Partijas / Galvenie runātāji / Dominējošās tēmas), rēķināta pār visu nedēļu. Iepriekš nedēļā nebija bloku sadaļas → opozīcija bija neredzama sintēzē, kaut tā runāja. `.claude/agents/weekly-brief-writer.md` atjaunots (skelets satur tabulu → saglabā verbatim + pievieno bloku sintēzi zem tās).
- **Note 289 (15.–21.06. nedēļas analīze)** manuāli papildināta ar opozīcijas balsīm (Šuvajevs «zelta vīzas» pretsvars imigrācijas tēmā) + bloku samēra sadaļu; grafiks pārģenerēts; šaurs re-render (`--only=dashboard,blog`) + deploy (`--no-delete`), live verificēts.

## 2026-06-13 — Gaišā tēma: pilna tokenizācija, WCAG AA, noklusējuma flip

- **Gaišais režīms + "vintage" nav slēdzis** (`83c6d1e`): pilna krāsu tokenizācija (CSS custom properties), WCAG AA mērķis; saišu krāsu palete centralizēta + statistikas reduced-motion (`5bee7db`). Konvencija: datu/krāsu tekstu emitē caur `--party-color` custom property (NE inline `color:`), lai gaišajā `color-mix` patumšina uz AA.
- **Noklusējuma flip uz gaišo** (`c634c47`): anonīmais apmeklētājs tagad redz `data-theme=light` (`localStorage.getItem('atmina:theme') !== 'dark'`), tumšais = opt-in; `color-scheme`/`theme-color` attiecīgi. JS-izslēgts fallback paliek tumšs (no-FOUC bootstrap; pieņemams JS-smagajā vietnē).
- **Kontrasts verificēts AA-clean** (2026-06-13): sākotnējais QA skans (`light_scan_results.json`) bija novecojis — tas mērīja pirms-polish tokenus (piem. `--text-dim #857b63`, tagad `#6e654f`) un stat-change pilu tumšās tēmas vērtības. Programmatiskā WCAG pārbaude pret pašreizējo CSS: visas 15 partiju krāsas (`color-mix(47%, #1f1b14)` uz papīra) iztur (zemākā ASL #fbbf24 = 4.72), 31 tēmu čips ≥5.01, visi minor findings (--text-dim 5.21, badge-green 6.37, prv2 sev 5.93, role-chip 5.40) un curated statistika pili (tokenizēti `var(--green)`/`var(--red-soft)` → ≥4.72). Verdikts: `docs/audits/light-theme-qa-2026-06-13/CONCLUSION.md`. CSS izmaiņas nebija vajadzīgas — kontrasta labojumi jau ielanda ar `83c6d1e`.

## 2026-06-13 — @Krisjanis_K vārdamāsas disentangle + Freidenfelda atvienošana + pārskata tīrīšana

- **Mis-seedētā id=191 "Krišjānis Kļaviņš" pilna privacy purge** (`ab1d582`, `0f25818`, `613b9be`): id=191 `x_handle` bija `@Krisjanis_K` (vārdamāsa, ne īstais žurnālists); zero-trace dzēšana (0 rindas claims/analyses/contradictions/context_notes/social_accounts/document_politicians). Īstais žurnālists izveidots id=231 `@kr_klavins`. id=190 Freidenfelds → `relationship_type='inactive'` (X sūdzības); `tensions.py` filtrē inactive.
- **06-12 dienas pārskata misatribūcijas tīrīšana** (`1552f6c`): purge atstāja 06-12 pārskatā dzēstos claims #531910/#531911, neeksistējošu "spriedzi #114" un atvienotu profilu citātus — purge mutēja DB rindas, NE ar roku rakstīto brief prozu. Iztīrīts visās 3 virsmās: DB note #274, `wiki/dailies/2026-06-12.md`, renderētais `blog/2026-06-12.html`; bloki pārrēķināti (Neitrāli 7→5, Ārpus Saeimas 3→2), Lato Lapsa paturēts. **Mācība:** retroaktīva profila atvienošana prasa arī ar roku rakstīto pārskatu un tvītu pārbaudi — DB purge tos neaiztiek (atkārtosies pie katra nākamā retro-retire).

## 2026-06-13 — claims↔votes topic drift fix + x_mentions slot drift diagnoze

- **claims↔votes topic drift** (`9b0e752`): BACKLOG [FIX] — 49 balsojumi / **4075 saeima_vote claims**, kur `claims.topic != saeima_votes.topic` (dominē budžeta-paketes claims ar vecāku `_motif_to_topic` versiju, klasterī 2026-03-26/04-01). `votes.topic` = autoritāte; idempotents UPDATE, neskar `bill_id`/`current_stage` (inv #12). Pāra rollback ar 4075 eksplicītiem per-claim UPDATE (`data/{fix,rollback}_claims_votes_topic_drift_2026-06-13.sql`). Atlikušie **7 motif-drift balsojumi** (id=218/219/1583…) → manuālā triāža (BACKLOG).
- **x_mentions 6.json/slot_count repo↔runtime drift diagnoze** (`1a57434`): commitētais `get_pool` default = 5 sloti (vienmēr — `git log -S`), bet `mentions_fetch_guardrail` logi rāda `total=6` kopš 2026-05-18 → dzīvais (lokālais) pipeline darbināts ar 6-slotu pūlu, ko commitētais kods neražo (necommitēts lokāls labojums, kopš atritināts). Salabots maldinošais komentārs + BACKLOG formulējums. Behaviorālais lēmums (6-slot oficiāls / palikt 5 + ct0 refresh slotiem 1.json/3.json) atvērts. **Atrisināts 2026-06-14:** `6.json` izrādījās BAITU-IDENTISKS `2.json` dublikāts (tas pats konts — vienāds auth_token+ct0), NE 6. konts → viens konts divos slotos = nulle noturības ieguvuma un bot-riskanti. Pārvietots ārā no pūla (`data/x_cookies/6.json.dup-of-slot2-2026-06-14.bak`); pūls paliek **5 atšķirīgi** konti, commitētais `get_pool` default=5 ir pareizs; `SEARCH_MIN_HEALTHY_SLOTS` paliek 4. Patiess 6. slots prasītu JAUNU X kontu.

---

## 2026-06-12 — x_mentions default flips uz `search` + izpildītās stratēģijas logging

A/B noslēgts (06-10..06-12; BACKLOG [OPERATOR] ieraksts; operatora apstiprināts flip):

- **`_resolve_strategy` default `"timeline"` → `"search"`** (`src/x_mentions.py`). Pamatojums: 0 kļūdu visos A/B skrējienos, t.sk. pilnajā ingest ķēdē tūlīt pēc `fetch_all_twitter`; ~5–7× ātrāk (58s pret ~5 min); plašāks tvērums (netrackoti autori). Apjoma 3× kritērijs atzīts par novecojušu — rakstīts pie ~12 mentions/7d, bet timeline jau pati sasniedza ~200/dienā. `timeline` paliek guardrail fallback (slot-health probe ≥4/5) + opt-in (`X_MENTIONS_STRATEGY=timeline` / `strategy=` kwarg).
- **`x_mentions.last_run_strategy`** modulis-stāvoklis + **`"strategy"` lauks `mentions_fetch` log details** (`src/social.py`) — klusais guardrail fallback tagad redzams retrospektīvi (līdz šim search/timeline skrējienus logos nevarēja atšķirt; 06-11 datu punkti tāpēc nebija interpretējami).
- A/B blakus-atradumi: viena slota 404 uz strict-TID endpointiem = novecojis ct0, fix = ct0 refresh bez re-login (twikit-notes.md § 2026-06-12); `get_pool` default `slot_count=5` → `6.json` produkcijā netiek ielādēts (atvērts BACKLOG); rīta deģenerēta pūla guardrail trip bija ct0 artefakts, ne sistēmiska pēc-twitter problēma.
- Datu higiēna tajā pašā sesijā: `@KlucisD` feed deaktivēts (konts X neeksistē; `data/deactivate_klucisd_2026-06-12.sql` + rollback pārī).

---

## 2026-06-12 — Topic-pārklājuma revīzija (543 balsojumi), emit-helpera dedup, JSON-LD SEO

Trīs BACKLOG vienības vienā sesijā (operatora izvēle; paralēli Opus aģenti, orchestratora diff-review):

- **`_motif_to_topic` pārklājuma revīzija** (`src/saeima/claims.py`): no 2255 fallback "Valsts pārvalde" balsojumiem **543 saeima_votes + 47 843 saeima_vote claims** pārcelti uz 9 pareizajām kanoniskajām tēmām (Budžets 253, Pašvaldības 102, Degviela un enerģētika 42, Tieslietas 37, Aizsardzība 36, Veselības aprūpe 24, Valsts kapitālsabiedrības 17, Kultūra 16, Sociālā politika 16). Galvenais cēlonis: `nodokļ` stems (mīkstais ļ) izlaida akuzatīvu "nodokli" — 170+ nodokļu balsojumi krita fallback; risināts ar `_word("nodokli")`. Kārtošanas guard-i: `nekustamā īpašuma nodokl`→Pašvaldības PIRMS budžeta nodokļu stemiem; `ieslodzījuma viet`/`kapitāla daļu un kapitālsabiedr`/`covid-19` PIRMS generic `pārvald`. Backfill `data/fix_motif_topic_coverage_2026-06-12.sql` + rollback pārī (UPDATE filtrē `topic='Valsts pārvalde'`, neskar bill_id/current_stage). Atlikušie 1712 fallback leģitīmi (procesuālie, kārtības rullis, viensēriju likumi). +13 testi; chars-baseline pārģenerēts. Pēcpārbaudē atklāts pirms-eksistējošs claims↔votes drift (49 balsojumi / 4075 claims, revīzijas neskarts) → BACKLOG [FIX].
- **br/gz emit-helpera dedup** (`src/render/_common.py::_emit_json_compressed`): 4 compress-and-write kopijas (positions/votes/links/search_index) → 1 helpers leaf-modulī. Kopijas NEbija pilnīgi identiskas — positions bez `mkdir`/`logger.info`/`default=str`; nianses saglabātas call-site pusē, unificēts tikai bitu-identiskais kodols (br q11 + gz l9).
- **JSON-LD strukturētie dati** (templates): `Organization` (base.html.j2, visās lapās, `{% block jsonld %}` āķis), `NewsArticle` (blog-post + _weekly_body), `Person` (politician.html.j2; `memberOf`/`sameAs` no DB, tukšie lauki izlaisti). 2026-06-09 audita canonical-daļa izrādījās **novecojusi** — `_render_page` canonical auto-inject jau sedz visas lapas, query-param filtri korekti konsolidējas uz bāzes URL; nekas nebija jālabo. Zināms sīkums: `dateModified` izmanto DB `created_at` formātu (bez `T`/zonas — Google pieņem, strikti nav ISO 8601). 14 render-baseline fixtures pārģenerētas (Organization bloks skar katru lapu).

---

## 2026-06-12 — Backlog ātrie fixi + operatora darbi: topic guard, acronym-guard, ReadForm patterns, Priede, Krauze

2026-06-11 sēdes ielādes pēcdarbi (BACKLOG [FIX]+[OPERATOR] kopa, operatora apstiprinājums "izdari ātros un operator"):

- **`_motif_to_topic` guard "dzīvnieku aizsardzīb"/"dzīvnieku labturīb" → Lauksaimniecība** (`src/saeima/claims.py`): generic "aizsardzīb" fallback klasificēja Dzīvnieku aizsardzības likuma balsojumus kā "Aizsardzība un drošība". Backfill: **24 saeima_votes (2023-05-25..2026-06-11, t.sk. 5859) + 2103 saeima_vote claims** (`data/fix_dzivnieku_aizsardzibas_topic_2026-06-12.sql` + rollback pārī). NB: backlog teica "2023 vēsturiski claims" — 2023 izrādījās *skaits*, skartas visas balsošanas no 2023. līdz 2026. gadam. Atlikusī pārklājuma revīzija (22/47 fallback "Valsts pārvalde") → BACKLOG [DEFERRED].
- **Acronym-guard stance ģenerēšanā** (`src/saeima/votes.py::generate_claims_from_votes`): summary pirmo burtu vairs nelowercase-o, ja pirmie ≥2 burti ir lielie ("LPV deputātu…" paliek "LPV", ne "lPV"). Testi `TestGenerateClaimsAcronymGuard`.
- **`p3_backfill_year_urllib.py` — visi trīs agenda-URL paterni** (`_extract_vote_urls_from_agenda`): static `./0/HEX?OpenDocument`, `addVotesLink(...)`, **`./Voting?ReadForm&parentID={GUID}`** (2026-06-11+; bez rezultāta etiķetes → klātesošo-vairākuma fallback). **Jauns atklājums (verificēts dzīvē):** ReadForm lapas embedded balsojuma datus servē TIKAI kamēr sesija ir "aktuāla" — dienu vēlāk tas pats URL atgriež tukšu `voteFullListByNames` (arī `&tm=` neatslēdz). ReadForm-ēras sesijas JĀielādē sēdes dienā; vēlīns backfill URLus atrod, bet katrs fetch redzami FAILo ar `empty data` (ne kluss izlaidums). Dokumentēts skriptā + `saeima-tracker.md` 2.B.
- **Inga Priede seedēta (pid=230)** + 43 `saeima_individual_votes` pārsasaistītas no NULL + 43 saeima_vote claims (`data/fix_priede_seed_2026-06-12.py` + rollback SQL). Partija: **Apvienotais saraksts** (backlog minēja ZZS — verificēts: AS frakcija, Edgara Tavara vietā pēc iecelšanas Kulberga kabinetā; LZP valdes locekle). `x_handle` apzināti NULL — `@ingapriedev` visticamāk pieder vārdamāsai (ex-Vienotības Inga Priede, 2014. g. skandāls); risks fiksēts `notes`. "Priede" = sugasvārds → formas pievienotas `matcher._COMMON_WORD_FORMS` (person-context gate, Krasta/Lāces paterns).
- **Armandam Krauzem (pid=154) negative_patterns** "Ivars Krauze" + locījumi (`data/fix_krauze_negative_patterns_2026-06-12.sql` + rollback) — diriģents Ivars Krauze (doc 52304 FP, claims netika radīti).

---

## 2026-06-11 — Nogriezto pmo.ee dokumentu pārlāde (913/1010) + Bērziņas „trūkstošās" deklarācijas izrādās amata maiņa

Divi 06-11 atradumi, kas abi māca vienu un to pašu: **trūkstoši dati vispirms jāpārbauda pret cilvēka karjeru, ne pret skrāpi.**

**Nogrieztie dokumenti.** `scripts/fix_pmo_truncated_docs.py` pārlādēja 913 no 1010 nogrieztajiem dokumentiem caur pmo.ee→TVNet redirektu (vidējais garums 292 → 2479 zīmes; `source_url` neaiztikts, `word_count` sinhronizēts; rollback `data/rollback_pmo_truncated_docs_2026-06-11.sql`, 913 stmt). **97 paliek īsi** — 96 ir paywall raksti, kuriem pilnais body caur publisko lapu nav dabūjams, plus viena fetch kļūda. Lai nogriezts stubs neražotu pusi pozīcijas, `@claim-extractor` promptā (Step 2) pievienoti truncated-stub vārti, kas tādu dokumentu marķē NEEDS_REVIEW. Pārbaude ar pilno bodiju: Vitenberga #20850 re-hunt deva 0 kandidātu — pilnais teksts noraidījumu tikai nostiprina (profils konsekvents „enerģētiskā drošība pirms klimata ambīcijām" kopš 2020; AER atbalstu 2026. gadā neatsauc), pārbaudīti visi 19 position claims + 109 atslēgvārdu-atlasīti balsojumi + 9 frakciju sadalījumi.

**Inga Bērziņa (pid=144) „datu robs" nebija tehnisks.** 2023-09→2025-06 viņa bija ministre Siliņas kabinetā, mandāts nolikts — un tieši tas ir redzams kā robs `saeima_individual_votes`. VID ministru deklarācijas glabā zem institūcijas „Valsts kanceleja", ko Saeima-only `vad_disambig` hints izfiltrēja. Hints paplašināti uz pilnu karjeru (rollback `data/rollback_berzina_vad_hints_2026-06-11.sql`; „kanceleja Ministr" apzināti šaurs — eksistē atsevišķa VK referente homonīma) → ielādētas visas 24 ikgadējās 2002–2025 bez robiem, t.sk. Kuldīgas mēres 2007–2021; family-cluster audits tīrs.

**Mācība nākamajiem „trūkstošas deklarācijas" gadījumiem:** vispirms pārbaudi politiķa AMATU hronoloģiju — balsojumu robi ir norāde, ne kļūda — un tikai tad meklē deklarācijas zem attiecīgās institūcijas; ministriem tā ir „Valsts kanceleja". Koda blakusieguvumi: institūcijas-aware paginācija + VID `From=` cikla wrap-detekcija (`src/vad/fetch.py::search`).

*(Ieraksts uzrakstīts 2026-08-01 BACKLOG kompakcijas gaitā — abi atradumi bija fiksēti tikai BACKLOG naratīvā un nekur citur.)*

## 2026-06-10 — Mediji ↔ feed-profilu savienojums: `x_feeds`, outlet čips, Mediji/Iestādes šķelšana

**Problēma:** viens medijs eksistēja divās nesavienotās sistēmās — `/mediji` caurskatāmības lapas (sources.yaml `outlets:`) un mediju X-feed org-profili (`politiki/ltv-zinas.html` ar "Nav norādīts" galvenē un tukšām cilnēm). LSM pieci feedi, LETA un NRA dubultojās bez nevienas saites; vakardienas "Iestādes un mediji" grozs jauca Panorāmu ar armiju. Spec: `docs/superpowers/specs/2026-06-10-mediji-feed-linkage-design.md`.

**Risinājums (savienojums dzīvo config, ne DB — nav migrācijas):**
- **`outlets.x_feeds`** (sources.yaml + `src/outlets.py`): outleta X kontu saraksts; join pret `social_accounts.handle` (autoritatīvais; NE `tp.x_handle`) caur jauno `_common._outlet_feed_map`. **NB: `social_accounts.platform` reālajā DB ir `'twitter'`** (vēsturiskais nosaukums) — vaicājumi lieto `IN ('twitter','x')`; tikai `'x'` būtu kluss 0-rindu join (atklāts Task 3 verifikācijā).
- **`mediji/<slug>.html`** — jauna sadaļa "X konti un raidījumi" (`_fetch_outlet_feeds`): feed kartes ar saiti uz profilu; handle bez DB rindas → stderr skip.
- **Feed-profila galvene** — partijas slots org-feediem tagad rāda outlet saiti (`mediji/<slug>.html`) "Nav norādīts" vietā; tas pats `profile-party-tag` paterns kā politiķu partijas saitei.
- **Personas grozs šķelts:** "Iestādes un mediji" → **Mediji** (9: LTV Ziņas, Panorāma, De Facto, Krustpunktā, KNL, LETA, NRA, TV3 Ziņas, IR žurnāls) + **Iestādes** (4: NBS, LVM, LDDK, Saeimas ziņas) caur `_split_org_category` + `media_feed_ids`; sg-index abas kartē uz `cat=2` (typeahead sekcija paliek apvienota). Railā zem "Mediji" CSS-only saite "Mediju caurskatāmība →". Personas baseline reģenerēts (`REGEN=1`).
- **Jauni outleti:** TV3 (`tv3`) un IR žurnāls (`ir`) — `@outlet-researcher`, visi 5 fakti sourced; TV3 `editorial_leadership` tikai portāla redaktors (TV ziņu dienesta vadītājs 2024–2026 nebija apstiprināms ar avotu). Kopā 11 outleti.
- **`wiki/mediji.md`** — jauna wiki_sync FULLY-overwritten lapa (konfigurācijas spogulis, bez DB joiniem); indeksā `[[mediji|Mediji]]` wikilink.

---

## 2026-06-10 — Topiku robežu precizēšana: Droni ↔ Aizsardzība, Vēlēšanas ↔ Koalīcija

**Konteksts:** topiku audits (26→31 pāreja 2026-04-25 apstiprināta kā apzināta un tīra; DB 0 nekanonisku vērtību) atrada vienu reālu robežas problēmu: 93 dronu-pieminoši claims sēdēja "Aizsardzība un drošība", un viens un tas pats notikums (drona notriekšana 06-08) aizgāja uz abiem topikiem.

- **`topic_map.py` Droni aliasi** +11 (dronu/drona notriekšana, pārtveršana, pretdronu aizsardzība/sadarbība/spējas/sistēmas, FPV droni, dronu operatori/siena/ražošana).
- **Claim-extractor boundary rindas** (kanoniskajā promptā): Droni↔Aizsardzība ("izņem vārdu drons — ja pozīcija sabrūk, tā ir Droni") un Vēlēšanas↔Koalīcija (kampaņa/kandidāti → Vēlēšanas; koalīcijas virtuve/partiju pārejas → Koalīcija; tests: vai izteikums paliktu aktuāls bez tuvajām vēlēšanām).
- **Sweep:** 12 dronu-kodola claims pārcelti uz Droni (`data/fix_drone_topic_boundary_2026-06-10.sql` + rollback; 18 kandidāti triāžēti manuāli — 3 atstāti pēc kodola testa, 3 atstāti `(opponent_id, source_url, topic)` idempotences kolīziju dēļ). Droni 123→135, Aizsardzība 421→409.
- **Lēmumi bez izmaiņām:** Vide (9) + Klimats (8) NEapvienot atpakaļ (CBAM/ETS diskurss augs; pārskatīt pēc vēlēšanām); "Aizsardzības industrija" splits atlikts — sk. BACKLOG, ja tendence #260 turpina augt.

---

## 2026-06-09 — Profilu taksonomija: "Iestādes un mediji" grozs + mediju kontu datu flips + nav "Profili"

**Problēma:** personas lapā institūcijas bija izkaisītas pa nejaušiem groziem (`_persona_category` organizācijas nepazina): LVM/LDDK → "Amatpersonas", NBS/Saeimas ziņas → "Citi", un mediju plūsmas (LTV Ziņas, LETA, Panorāma, De Facto, KNL) ar `relationship_type='journalist'` stāvēja "Žurnālisti" starp cilvēkiem. Nav poga "Politiķi" veda uz lapu "Profili" ar 24 ne-politiķiem.

**Risinājums:**
- **Datu migrācija:** 5 mediju plūsmu konti `journalist`→`organization` (`data/fix_media_feeds_organization_2026-06-09.sql`, rollback pārī). **2. kārta 2026-06-10:** vēl 4 izlaistas plūsmas (NRA, TV3 Ziņas, IR žurnāls, Krustpunktā — `data/fix_media_feeds_organization_2_2026-06-10.sql`). `journalist` tagad nozīmē tikai cilvēku (6: Lapsa, Kļaviņš, Seržants, Madžiņš, Kasems, Ozols); `journalist|relay` kombinācija DB vairs neeksistē. Atjaunotas claim-extractor slot-tabulas (wiki + kanoniskais prompts), t.sk. jauna `organization|first_party` rinda (NBS/LVM/LDDK — oficiāli paziņojumi).
- **`_persona_category` 2. noteikums:** `relationship_type='organization'` → **"Iestādes un mediji"** (pirms journalist/party/role pārbaudēm). Personas raila grozi pēc abām kārtām: Deputāti 118 · Amatpersonas 40 · Žurnālisti 6 · Analītiķi 5 · Iestādes un mediji 13; "Citi" iztukšojās. Raila secība tagad kanoniska (cilvēki pirms institūcijām), ne dict-nejaušība.
- **Nav: "Politiķi" → "Profili"** (atbilst lapas H1; poga vairs nesola tikai politiķus).
- **sg-index shēma v2:** `p` tuple +8. lauks `cat` (0=politiķis, 1=komentētājs, 2=iestāde/medijs; atvasināts no `_persona_category`); `sgv1.js` typeahead rāda trīs atsevišķas sekcijas **Politiķi / Komentētāji / Iestādes un mediji** — LVM/NBS/LETA vairs nestāv starp deputātiem.

---

## 2026-06-09 — Sākumlapas meklētāja typeahead (sg-index sidecars) + `?q=` ķēdes fix

**Problēma:** hero meklētāja forma sūtīja `pozicijas.html?q=...`, bet `pzv1.js::applyUrlParams` lasīja tikai `persona/tema/partija` — **`q` tika klusi ignorēts** (meklētājs izskatījās strādājošs, bet neko nedarīja). Ieteikumu (typeahead) nebija vispār.

**Risinājums:**
- **`data/sg-index.json`** (+`.br`/`.gz`) — jauns ieteikumu sidecars (~13 KB raw / ~4 KB br), emitē `src/render/search_index.py`, gated `_want("dashboard") or _want("pozicijas")` (abi dienas rutīnas narrow ceļi to atsvaidzina). **Tuple-shēma ir load-bearing konvencija** — `assets/sgv1.js` lasa pozicionāli: `p:[name,slug,party_short,party_color,has_photo,claims,contras]` (7), `t:[topic,color,claims]` (3), `g:[name,short,color,claims]` (4). Arity lock: `tests/test_search_index.py::test_sg_index_tuple_shape`. Skaitīšanas kontrakti: claims = `claim_type='position'`; pretrunas = `COALESCE(confirmed,1)=1` (kā publiskās lapas, NE kā `_fetch_politicians` — sk. BACKLOG).
- **`assets/sgv1.js`** — lazy fetch pie pirmā focus, NFD diakritiku folding ("jan"→"Jānis", "budž"→"Budžets"), prefikss>substring rangs ar count-desc, ARIA combobox + bultiņas/Enter/Escape, progressive enhancement (fetch-kļūda → parastā GET forma). Pievienots `_resolve_assets_version` versioned sarakstam.
- **`pzv1.js` `?q=` fix** — applyUrlParams tagad ieliek `pzState.query` + aizpilda rail meklētāju.
- **Mobilais hero-search bug:** `flex: 1 1 320px` kolonnas virzienā (≤768px) kļuva par 320px AUGSTUMU — meklētājs izstiepās par milzu ovālu. Fix: `flex: 0 0 auto` mobile blokā.
- Sīkie: `chart.min.js` defer + DOMContentLoaded init; inline `onmouseover` → `.vote-link` CSS; avatāru `width/height`+`loading=lazy` (CLS); `.votes-mini` tabula ≤600px slēpj Par/Pret/Atturas kolonnas.

---

## 2026-06-08 — Workflow-audita sanācija: invarianti, klusās kļūdas, attēlu CLI, pārklājums

Daudz-skatupunktu workflow audits (6 perspektīvas) → 10 commiti (`aa03aba`→`2c3bb9a`). Galvenā tēma: **klusās kļūdas** (darbs neizdodas bez signāla) + neiekapsulēta atkārtošanās + docs/atmiņas drift.

**Datu kontrakti / invarianti (`CLAUDE.md`):**
- **Jauns rollback-pairing noteikums:** no šī brīža katra hand-run datu migrācija (`data/*.sql` vai `scripts/fix_*.py`, kas mutē rindas) commitē pāra `data/rollback_*.sql` līdzās. Rationale: rollback tikai working-tree ir viens `git clean` no neatgriezeniska zuduma (Kļaviņa reattribution = 4161 balsis). Esošie 3 `fix_*.py` bez rollback = acknowledged-debt, ne paraugs.
- **Data Contract #2 pārformulēts:** claims bez `source_url` tiek nomests `save_analysis()` validācijā (`analyze.py`), NE "DB layer" — reģistrēts kā `missing_source_url` `failures` ierakstā (ne raised). `store_claim()` tiešs izsaukums ievieto NULL. Lock: `tests/test_invariants.py::test_inv2`. Pievienots arī invariant #10 smoke (coalition truth-source seko `parties.coalition_status`, ne `relationship_type`).

**Klusās kļūdas (0-rezultāts = trauksme):**
- `@saeima-tracker` Step 2.B tagad ekstrahē DIVUS vote-URL paternus: veco statisko `/0/HEX?OpenDocument` UN jauno JS `addVotesLink("DKP","VOTE")` (kanoniskais `_ADD_VOTES_RE`, `scripts/p3_backfill_year_urllib.py`). 2026-06-04 sēde (70 balsojumi) tika klusi palaista garām, jo tika pārbaudīts tikai pirmais. + OBLIGĀTS 0-vote STOP sargs. `saeima_summary_missing` log tagad parādās operatora dashboard aktivitātes lentē.
- Dienas brief `stated_at` scoping (`_BRIEF_DAY_CLAIM_SQL`): skelets iekļauj arī šodien-ekstrahētus claims (stated=diena VAI created=diena UN stated≥diena−7d) — vakar-teikts/šodien-ekstrahēts vairs neizkrīt. + 5. "Bezpartejiskie" bloks (bezpartejiskie tracked vairs neizkrīt cauri visiem blokiem). + `lint_lv_style` melīšana/konsenss/ol-trap noteikumi.

**Jaunie rīki:**
- `src/coverage.py` + `scripts/coverage_report.py` (read-only): "tumšās zonas" deputāti (balsojumi izsekoti, bet 0 analyses + 0 position claim + 0 X feed = 25) + bez-X-feed/never-analyzed/stale-pol. `print_routine()` rāda kopsavilkuma rindu.
- `python -m src.graphics.cli` (`brief` + `thread`): aizstāj per-dienas throwaway attēlu skriptus; kanoniskā `SEPIA_STYLE` (`prompt.py`); 20 throwaway skripti → `scripts/_scratch/` (gitignored). Sk. `commands.md`.
- `/deep-check stale-pol` scope (aktīvi ≥5 poz., pretrunu pārbaude nekad/>60d).

**Tests:** visi 3 `_BASELINE_XFAIL` baseline-2026-04-29 xfail triāžēti un atrisināti (neviens neslēpa regresiju — matplotlib genuine pass, highlights fixture laika-bug, relay-author obsolēts kontrakts). `check.sh` = **1340 passed, 0 xfailed, 0 xpassed**.

---

## 2026-06-03 — Saeimas balsojumu `summary` backfill (224 → 3079) + likumi.lv rekonsiliācija

**Problēma:** 5480 no 5704 `saeima_votes` (96%) bija tukšs vai placeholder `summary`
("Kopsavilkums nav pieejams — historic backfill 2026-05-26"), visi 2022–2025. P3 backfill
([2026-05-27](#2026-05-27--p3-pilns-14-saeimas-balsojumu-backfill-511k-saeima_vote-claims))
saglabāja balsu rindas + `motif`, bet NE `summary` — tas bloķēja retorika-vs-balsojums
pretrunu detektēšanu (FP3 prasa likumprojekta saturu, ne tikai motif). `summary` ir plain
`UPDATE` (NEattiecas uz invariantu #12, kas sargā tikai `bill_id`/`current_stage`).

**Phase 1 — 2176 votes, bez skrāpēšanas.** Pašaprakstošie balsojumi (Lm14 lēmumi, komisiju
vēlēšanas, kolektīvie iesniegumi, neuzticība, P14 lēmumprojekti, deputātu atvaļinājumi,
uzticība valdībai) kompozēti no `motif` + DB balsu skaita, 140-aģentu paralēls fan-out.
317 procesuāli (klātbūtnes reģistrācija, pārtraukumi) + 21 aģenta atrasti (kvorums/debašu
laiks/darba kārtība) godīgi apzīmēti. Integritātes vārti: katra tally verificēta pret DB
(0 neatbilstības), 0 fabricētu skaitļu, P14 ≠ kolektīvais iesniegums.

**Phase 2 — 118 salient grozījumu likumprojekti (679 votes), enacted-accurate.** Pilots
pierādīja, ka titania.saeima.lv anotācijas apraksta likumprojektu KĀ IESNIEGTU (≠ pieņemtais
likums; piem. 367/Lp14 "uz pusi samazināt likmi" → faktiski "0,5% nodeva + 30% kompensācija"),
turklāt ir lēnas/serial/~33% attēlu-PDF. Pārgāja uz **likumi.lv via WebFetch** (paralēli,
enacted-accurate): base law → konsolidētais id (DuckDuckGo meklē) → grozījums pēc pieņemšanas
datuma → faktiskais saturs. Targeted atlase pēc tēmas (imigrācija, aizsardzība, nodokļi,
valsts valoda, izglītība, enerģētika). 679/679 tally-verified pret DB, visi ar likumi.lv avotu.

**Atlikušais:** 898 distinct Lp14 bills vēl placeholder (galvenokārt tehniski grozījumi,
zemāka deep-check vērtība). Recepte + audit artefakti gatavi (`data/_p2_*.py`,
`_phase2_lawmap.json`, `_bf_*.py`) atkārtošanai ar paplašinātu atlasi.

**Deploy:** full render + `deploy.sh --no-delete` → atmina.lv (verificēts live
`balsojumi-matrica-recent.json`). Backup: `data/atmina.db.pre-summary-backfill-20260603.db`.
NB: pilnais render nejauši publicēja untracked melnraksta sintēzi (`imigracijas-konsenss-2026-06`),
kas pēc tam izlabota + papildināta ar featured image — turpmāk scoped `--only=` deploy.

## 2026-06-03 — Mediji: detaļlapas redizains + rus.delfi avota noņemšana

**Detaļlapas pulējums** (`templates/medijs.html.j2` + `assets/style.css`): caurskatāmības
fakti kā kartiņas (vietā tabulai), partiju pārklājums kā partiju-krāsu joslas ar
"vidējais visos medijos" atzīmi (rāda medija sliecienu pret vidējo), politiķu sakārtotas
joslas, tēmu chips, tīrāks jaunāko rakstu saraksts. **Partiju joslas tagad klikšķināmas**
uz profila lapu — `src/render/mediji.py` injicē `party_color` + `party_slug`; slug karte
keyota gan ar pilno nosaukumu, gan `short_name` (jo `tp.party` glabājas abās formās).
Rindas bez profila lapas (Bezpartejisks, joint lists) paliek neklikšķināmas.

**rus.delfi.lv noņemts** kā avots — `sources.yaml`: izņemts gan feed (`rus.delfi.lv`),
gan `delfi-ru` outlet. Mediju skaits 10 → **9**. 316 esošie rus.delfi dokumenti PALIEK
DB (vēsturiskā analīze nemainās), tikai vairs nav outlet lapas un netiek skrāpēts. Stale
`mediji/delfi-ru.html` manuāli noņemts no servera (`--no-delete` deploy to neattīra).
Commit `e62a487`, deployed atmina.lv. Avotu saraksti atjaunoti: `wiki/project-brief.md`,
`docs/data-policy.md`; `wiki/index.md` mediju skaits pārģenerēts ar `wiki_sync`.

## 2026-06-01 — Mediji: caurskatāmības profili (config-driven entity)

Jauna publiska sadaļa `/mediji` — mediju caurskatāmības profili, analogi
politiķu/partiju profiliem, bet medijiem (LSM, Delfi, TVNet, NRA, LETA, Diena,
Latvijas Avīze, Jauns.lv, Delfi-RU, Latvijas Vēstnesis). **Bez jaunām DB tabulām:**
reģistrs ir `sources.yaml` `outlets:` bloks (`src/outlets.py` to lasa); pārklājums
(kurus politiķus/partijas/tēmas medijs atspoguļo) aprēķināts render laikā no esošajiem
`documents`/`document_politicians`/`claims` — single-pass, host-keyed (NE per-medija N+1).

**Caurskatāmības fakti** (`outlets[].facts`): pa vienam avototam ierakstam laukiem
`owner` / `funding_model` / `legal_form` / `editorial_leadership` / `founded`. Katram
faktam savs `source_url` + `as_of`; **fakts bez `source_url` (vai `value`) tiek nomests
lasīšanas laikā** (`src/outlets.py`), atspoguļojot claims "nav source_url → nomests"
likumu (Data Contract #2). Faktus aizpilda jaunais `@outlet-researcher` aģents (pēc
pieprasījuma, viens medijs reizē, cilvēks pārskata YAML diff). Visi 10 mediji, 51 fakts
aizpildīts 2026-06-01 (`ea738ab`).

**Ētika — caurskatāmība, ne mērķēšana:** identiski lauki KATRAM medijam neatkarīgi no
uztvertās nostājas; nekādu `corrupt`/`bought`/`biased` etiķešu. Editorial `framing:`
lauks (uz `sources:` feed rindām) paliek INTERNS — `@claim-extractor` confidence signāls,
nepublicēts mediji lapās.

**Render:** `src/render/mediji.py` (mirror `parties.py`) + `templates/{mediji,medijs}.html.j2`;
`"mediji"` reģistrēts `KNOWN_DOMAINS`; nav link + sitemap. Fakta lauku nosaukumi medijs
lapā kartēti uz LV (`Īpašnieks` / `Finansējums` / `Juridiskā forma` / `Redakcijas vadība` /
`Dibināts`; `3aad7bd`). Spec/plāns:
`docs/superpowers/{specs,plans}/2026-06-01-media-outlet-profiles*`.

## 2026-06-01 — Nedēļas pārskats: atsevišķs formāts (saturs + vizuālais)

Nedēļas pārskats vairs nav daily klons. `generate_weekly_brief()` (iepriekš
orphaned, bez izsaucējiem) paplašināts ar week-over-week deltām, `<!-- WEEKLY_STATS -->`
marķieri un tēmu scaffold ar avotiem. Jauns `@weekly-brief-writer` aģents
(koplietotie noteikumi izvilkti `wiki/operations/agenti/brief-shared-rules.md`;
`@brief-writer` sašaurināts uz daily). Render caur `templates/_weekly_body.html.j2`
ar `.weekly-*` ink-navy chrome, mobile-first stat kartītēm un in-body movers
grafiku (`src/graphics/weekly_chart.py` — roku-rakstīts SVG). Featured image lieto
`WEEKLY_STYLE` rāmi. Validācija (`_validate_brief_structure`) atjaunota uz jauno
sekciju kontraktu (`## Nedēļas stāsts` + `## Nedēļas galvenās tēmas`).

**Kāpēc SVG, ne matplotlib:** matplotlib nav default venv (sk. conftest xfail
`test_visuals_chart`). **Kāpēc grafiks ārpus `brief_images`:** `get_approved_image()`
atgriež jaunāko approved rindu per note_id — otrs (grafika) attēls sajauktu
featured-image izvēli; tāpēc grafiks ir tīri DB-dati un neiet caur approval loop.
Spec/plāns: `docs/superpowers/{specs,plans}/2026-06-01-weekly-brief-redesign*`.
## 2026-05-29 — Render hang fix (`claims.document_id` indekss) + `check.sh` vārtu atjaunošana + `--only` CLI

**TL;DR:** Pilns `generate_public_site()` iekārās ~16 min (CPU pegged, 0 disk write) pēc P3 backfill. Cēlonis: `render_news._fetch_news` izpilda `WHERE document_id=?` reizi uz katru ziņu (2594×), bet `claims` tabulai trūka indeksa uz `document_id` — katrs lookup full-scan pār 514k rindām (~376 ms). Pievienots `idx_claims_document_id` → lookup 376ms→0,07ms, `_fetch_news` 16min→0,5s, pilns render **169 s**. Tajā pašā sesijā pievienots `--only` narrow-render CLI un atjaunoti `bash scripts/check.sh` vārti (bija sarkani ~mēnesi, 24 pre-existing failures).

**Izmaiņas:**
- **`idx_claims_document_id`** (`f8cf80d`) — pievienots `src/schema.sql` + live DB. Backfill izaudzēja `claims` līdz 514k rindām, kas pārvērta nesaindeksētu per-dokumenta lookup par 16 min hangu.
- **`--only`/`--list-domains` narrow-render CLI** (`9827580`) — `python -m src.render --only=DOMAIN1,DOMAIN2` renderē apakškopu (~10-30 s) pilnā ~12 min vietā. `KNOWN_DOMAINS` (17 domēni) gate caur `_want()`.
- **Orphaned claims indeksu sync** (`57a10ef`) — `idx_claims_claim_type` + `idx_claims_opp_type_topic` bija tikai live DB (nevienā koda ceļā); deklarēti `schema.sql` + regenerēts `schema-dump-pre-f2.sql` baseline.
- **preflight DB-path fix** (`3122149`) — `preflight_check()` noklusējums `politracker.db`→`DB_PATH` (`data/atmina.db`); agrāk `init_db()` radīja un validēja nepareizo (legacy) DB, nekad neapskatot reālo.
- **Vārtu atjaunošana (24 pre-existing failures):** char baselines regen pēc P3 data drift (`8febf72`), x_mentions env-hermeticity (`7556df7`), dashboard `KeyError: -1` uz `approved=-1` "superseded" image rindām (`994face`), schema-dump baseline (`57a10ef`), Windows teardown flake (`d51f100`). `check.sh` tagad zaļš (ruff + pytest 0 failed + render smoke).

**Atvērtais:** char baseline testi hash live-DB output → atkārtoti lūst pēc katra ingest (data-drift treadmill); rework uz mazu fixture DB ieteicams. `render_links` (46 s) + `render_politicians` (60 s) vote-alignment self-joini ir lēnākie posmi — cache/precompute kandidāti, ja pilna render laiks sāk sāpēt. Sk. memory `project_render_narrow_cli`.

---

## 2026-05-28 — balsojumi.html virtualizācija (367 MB → 142 KB br)

**TL;DR:** Balsojumu matrica pārveidota no servera-renderētas HTML uz JS-renderētu kompaktu JSON (`data/balsojumi-matrica.json` + pre-kompresēti `.br`/`.gz` sibling faili) ar lazy init + pagināciju. Transfers 367 MB → 142 KB br (~2700×). Procedurālie balsojumi pēc noklusējuma paslēpti no matricas.

**Izmaiņas:**
- Matrix JSON emitter (`80cd9f1`) + pre-kompresēti `.br`/`.gz` siblings (`da3da9d`)
- JS-renderēta matrica + vote-list paginācija, `assets/bmv1.js` (`5b163a3`)
- Filter dropdowns godā SSR pagināciju (`8884730`)
- Targeted balsojumi-only render skripts (~15 s) (`dbcfca9`)
- Procedurālie Saeimas balsojumi paslēpti no matricas pēc noklusējuma (`80ccdf2`)

Step 3 (column virtualization + TAB 1 lazy popover) atlikts.

---

## 2026-05-27 — P3: pilns 14. Saeimas balsojumu backfill (~511k `saeima_vote` claims)

**TL;DR:** Backfillēts viss 14. Saeimas balsojumu vēsturiskums (2022-11 → 2026-05): **5703 balsojumi / 506 963 individuālie balsojumi (100 % match) / ~511k `saeima_vote` claims**. Pievienoti 19 deputāti (pid 205-223). Šī datu izaugsme ir cēlonis vairākiem render/perf regresiem, kas risināti 2026-05-29.

**Izmaiņas:**
- P3 Phase 0+1: ST/ST! faction codes + sentinel stance fallback (`7107996`)
- Phase 2 scalable year backfill — embedded Playwright + JS extraction (`92a55ca`), pēc tam pure-urllib (Playwright dependency likvidēta) (`9887cb7`)
- `saeima_vote` claim_type atbrīvots no inactive guard + 9 historic deputāti (`ae6f023`); wave-2 deputāti + swap-name matcher fix (`de09ea4`)
- Surname-collision attribution + ghost-claim cleanup (`3422b8c`); Zelderis partijas korekcija — Progresīvie, ne Apvienotais saraksts (`c4e204a`)

**NB:** `saeima_vote` claims glabā `document_id = NULL` (provenance caur `saeima_individual_votes`, kas tagad 507k rindas) — sk. 2026-05-29 indeksa fix.

---

## 2026-05-26 — P2: Vitenberga 2020-2022 retrofetch *(ieraksts pārcelts no operacijas.md 2026-07-17)*

Klimata ministra kandidāts (pid=139) — 25.05 "klimata mērķi jāiepauzē" motivēja pirms-tracking substrāta retrofetch: 14 doc (TVNet+LSM, 2020-04→2022-05, EM tenūra Kariņa I valdībā), **9 first-party position claims #22981-22989** saglabāti. Hunter atrada 2 minor_shift kandidātus (#22986 vēja parku atbalsts JV 2022 vs #20850 "iepauzēt klimatu" 2026); `@devils-advocate` REJECT visiem — paywalled tvnet.lv lede (33 vārdi), stance overreach, FP6+FP7 (Krievijas iebrukums 2 d. pēc #22986 + EM→KEM lomas šifts). 9 claims paliek kā profila substrāts atkārtotai pārbaudei. Skripts: `scripts/retrofetch_vitenbergs_2020_2022.py`. 0 publicējamu pretrunu — vēl viens ~1/2700 ROI datu punkts.

---

## 2026-05-17 — atmina ops dashboard M2 (Phase 2 — interactivity)

**TL;DR:** Operators tagad var apstiprināt/noraidīt brief imageus, force-refreshot X cookie slot health, palaist deploy ar konfirmācijas modal, un piekļūt visam ar klaviatūru — bez Claude Code sesijas. Visi 3 darbības atvers HTMX-swapped panel updates + toast paziņojumus. Build par `feat/operator-dashboard-m2` (5 commits + this doc commit).

**M2 scope (Phase 2, 5 tasks):**

1. **HTMX action infrastructure + toast system** — `views/_actions.py` exposes `action_response(panel_html, toast_level, toast_message)` which builds Flask response combining panel HTML with `HX-Trigger: {"showToast": {...}}`. `ops.js` listens for `showToast` HTMX events and injects toasts into `#toast-container`. Success/info auto-dismiss 3 s; warning/danger require click. Defense-in-depth: message uses `textContent`, not `innerHTML`.

2. **Image approve/reject** — `POST /api/image/<id>/approve` and `/reject` call existing `src.graphics.storage.approve_image/reject_image`. Approve refuses already-approved (400, surfaced explicitly so silent button-mashing doesn't look "successful"). Reject requires non-empty `reason` (saved into `brief_images.error_message` for future `@graphics-designer` prompt tuning). UI: pending images get inline Alpine.js reject modal with required reason textarea.

3. **Slot probe force-refresh** — `POST /api/slots/refresh` calls `get_slot_snapshot(force=True)` bypassing 60 s cache. Header gets `↻ Pārbaudīt [R]` button + `htmx-indicator` showing "probē…" during ~8 s probe. Toast level escalates to warning when refresh shows guardrail tripped — forced re-look shouldn't whisper "healthy" over a 3/6 reality.

4. **Deploy trigger with confirm modal** — `GET /api/deploy/confirm` renders modal with last-deploy timestamp + status (or "pirmais log entry" copy when empty). `POST /api/deploy` runs `subprocess.run(['bash','scripts/deploy.sh'], timeout=300, capture_output=True)`. Three outcome branches feed three toast levels: success (log_action stdout tail), non-zero exit (log_action failed with stderr tail; toast `exit N: <tail>`), timeout (`Deploy timeout (300s)`). Endpoint always 200 — failures surface in toast. Footer gets `🚀 Deploy [D]` button.

5. **Keyboard shortcuts + help modal** — `?` opens help modal with shortcut table (`?` A R D Esc). Elements opt in by setting `data-shortcut="K"`; `ops.js` keydown dispatcher matches keystroke + clicks the element. Guards: skip when focus in INPUT/TEXTAREA/SELECT/contentEditable, skip when Ctrl/Meta/Alt held (so `Ctrl+R` still reloads). Header `?` button is both the click surface AND the keystroke target.

**Saistītās ārpus-`src/dashboard/` izmaiņas:** nav. Visa M2 strādā ar M1 atstātajām pipieliem (`src.graphics.storage`, `src.db.log_action`, `src.dashboard.views.slots.probe_all_slots`).

**Verifikācija:**
- 114/114 tests green (5 jauni testu faili: actions/deploy/keyboard, plus 11 jauni cases brief/slot suites)
- `ruff check src/dashboard/` clean
- Manuālā browser smoke uz operatora

**Commit range:**
```
c187b3e  feat(dashboard): HTMX action infrastructure + toast system
167cb55  feat(dashboard): image approve/reject actions
1edb45d  feat(dashboard): slot probe force-refresh action
c65db56  feat(dashboard): deploy trigger with confirm modal + log_action
7c5714f  feat(dashboard): keyboard shortcuts + help modal (M2 SHIP GATE)
<this>   docs(dashboard): CHANGELOG + atmina-ops.md keyboard + actions section for M2
```

**Phase 3 (M3) — optional polish:** per-panel tooltips, empty-state illustrations, settings page, first-visit tour, SSE for live activity. Not blocking — M2 is the operator-ready milestone.

---

## 2026-05-17 — atmina ops dashboard M1 (Phase 1 complete)

**TL;DR:** Pirmais lokālais operatora dashboard — Flask + HTMX + Tailwind + Alpine, palaižams ar `python serve.py` uz `http://127.0.0.1:8080`. 5 paneliišas (brief / rutīna / X cookie pool / X_MENTIONS A/B / ekstrakcijas backlog) + aktivitātes timeline + pending banner + footer ar image budget. Bez auth, bind cietkods uz `127.0.0.1`. Pilns plan + design spec `docs/superpowers/{plans,specs}/2026-05-16-operator-dashboard*.md`. Runbook: [`wiki/operations/atmina-ops.md`](operations/atmina-ops.md).

**M1 scope (Phase 1, 9 tasks):**

1. Scaffolding + design system + theme toggle (auto/light/dark ar localStorage)
2. Šodienas brief panel — 4 stāvokļi (active/empty/loading/error); image approval badge cycle 0/1/2
3. Rutīna panel + `check_routine()` paplašināts ar `'waiting'` statusu pirms 15:00 LV (vairs nav false-alarm "missing brief" rītā)
4. X cookie pool — 6 cards × 4 endpoints, 60s cache, guardrail surfacing
5. A/B stratēģija — `X_MENTIONS_STRATEGY` env reading, 7-run SVG bar chart, 24h guardrail trip count
6. Ekstrakcijas backlog — per-platform un top-5 politicians, 30s cache
7. Aktivitātes timeline — UNION 4 avoti (logs + brief_images + context_notes + analyses), LV relatīvais laiks, HTMX 30s polling
8. Pending banner + footer + index composition — sticky-top banner ar Alpine sessionStorage dismissal; footer ar image budget bar + git SHA
9. Wiki + CHANGELOG + CLAUDE.md integrācija (šis ieraksts)

**Saistītie kodu izmaiņas ārpus `src/dashboard/`:**
- `src/routine.py` — `check_routine(now=...)` paplašināts ar morning-window logic; `'waiting'` status izstrādāts `analysis`/`daily_brief` soļiem pirms 15:00 LV; `print_routine` `status_icons` papildināts ar `⏳` (Task 1.3).
- `src/x_mentions.py` — guardrail trip tagad raksta `log_action("mentions_fetch_guardrail", ...)` alongside `logger.warning` (Task 1.5). Vēsturiskās trips nav backfillētas — tikai jaunās skaitās.

**Tehnoloģiju izvēle (no design spec):**
- Flask 3.x + Jinja2 (jau izmantots `src/render/`)
- HTMX 1.9 + Alpine.js 3 — partial-update + tiny client state, bez React/build pipeline
- Tailwind CSS 3 via CDN — design tokens + dark mode bez build step
- Charts: inline SVG (no JS lib), Lucide ikonas + emoji glyphs

**Verifikācija:**
- 79 testi (9 testu faili: scaffold + brief + routine × 2 + slots + strategy + backlog + activity + pending)
- `ruff check src/dashboard/` clean
- Real-DB smoke katram task'am pirms commit — viens bug noķerts (lede ekstrakcija sajauca bullets, kas in-memory fixture izlaida)

**Commit range:**
```
a2082a0  feat(dashboard): scaffold serve.py + design system + theme toggle
db18f7d  feat(dashboard): brief panel with 4 explicit states
160333e  feat(routine): morning-window awareness in check_routine + dashboard panel
9770153  feat(dashboard): slot/strategy/backlog panels (Tasks 1.4+1.5+1.6)
7a59a71  feat(dashboard): activity timeline with 30s auto-refresh + LV relative time
3927241  feat(dashboard): pending banner + footer + index composition
<this>   docs(dashboard): runbook + wiki/CLAUDE/CHANGELOG integration for M1
```

**Phase 2 (M2) — nākamais:** image approve/reject UI darbības, slot probe force-refresh, deploy ar confirm modal, keyboard shortcuts. Plāna Phase 2 (5 task'i).

**Kad pārskatīt:** ja `data/atmina.db` schema kādu kolonnu pārvieto (pārmaina `reviewed_at`, `approved`, `created_at` semantiku), Backlog vai Brief view'iem var būt jāatjaunina kolonnu nosaukumi. Tests pret in-memory fixtures `init_db()` izsauks, tāpēc lielas schema izmaiņas pieprasīs sinhronu test refresh.

---

## 2026-05-16 — Step 3.5 regress + trīslīmeņu fix (`@saeima-tracker`)

**TL;DR:** 07.05 + 14.05 sesijās 21 `saeima_votes` rindai trūka `summary` lauks, jo `@saeima-tracker` dispatches izlaida Step 3.5 (bill teksta lasīšana + 1-2 teikumu LV summary uzrakstīšana). Pirms 30.04 100 % balsojumiem bija saturīgs summary; pēc — generic motif fallback, kas claim stance laukā parādījās kā "Balsoja PAR: <motif>" 1943 deputātu claims vietā "Atbalsta/Iebilst pret/Atturējās balsojumā par: <substance>".

**Cēlonis:** Step 3.5 prompt-design defekts. `.5` suffix + ievada teikums "if the vote references a bill" signalizēja par "papildu/neobligātu" soli starp Step 3 (capture) un Step 4 (parse + store). Konteksta spiediena dēļ (~90 deputāti × 15-17 votes per sesija) agenti instinktīvi izlaida šo "papildu" soli un pārlēca tieši uz Step 4 → Step 5, kurā `process_vote_snapshot()` tūlīt izsauca `generate_claims_from_votes()` ar `summary IS NULL`.

**Trīslīmeņu fix (CLAUDE.md untouched — disciplīna dzīvo `wiki/operations/agenti/` + canonical promptā + kodā):**

1. **Kods — Layer-1 signāls** (`src/saeima/votes.py`):
   - `store_vote()` pieņem keyword-only `summary`, `document_url`, `document_nr` parametrus un saglabā tos atomic INSERT'ā (likvidē senāko NULL→UPDATE pattern).
   - `process_vote_snapshot()` tos pārsūta tālāk uz `store_vote()`.
   - `generate_claims_from_votes()` papildināts ar Layer-1 detection: ja `summary IS NULL` un motif sakrīt ar `\(\d+/L[pm]14\)` regex (bill-like), `logs` tabulā tiek rakstīta `action='saeima_summary_missing'` warning rinda. Mēs neatturam izsaukumu (image-only PDFs leģitīmi nesnijdz machine-readable summary; hard block iesprostotu agentu); mēs **signalizējam audit trail**, ko Step 5 verification gate uztver.

2. **Prompt — Layer-2 strukturāla disciplīna** (`.claude/agents/saeima-tracker.md`):
   - Step 3.5 izšķīdināts. Step 3 = atomic 3A→3B→3C bloks katram balsojumam: capture → write summary → call `process_vote_snapshot(summary=..., document_url=..., document_nr=...)`.
   - Aizliedz batching ("ne ievāc visus snapshots, tad raksti visus summaries" — tas ir tieši regresa pattern).
   - Jauns Step 5: galīgais verifikācijas gate ar SQL query `SELECT id, motif FROM saeima_votes WHERE date(created_at)=date('now','+3 hours') AND summary IS NULL AND (motif LIKE '%/Lp14)%' OR motif LIKE '%/Lm14)%')`. Ja jebkura rinda atgriežas, `raise SystemExit(1)` — agents neatskaitas operatoram līdz fix.

3. **Wiki — Layer-3 audit trail** (`wiki/operations/agenti/saeima-tracker.md`):
   - "NEdrīkst" sadaļā pievienots bullet par 2026-05-16 regresu ar atsauci uz šo CHANGELOG ierakstu.

**Backfill rezultāts (DB pirms fix piemērošanas):**
- 21 `saeima_votes.summary` aizpildīti (4 caur SQL copy no `saeima_bills.summary`, 15 via `@saeima-tracker` Step 3.5 batch, 2 manuāli par 1286/Lp14 priekšlikumu Nr.1 valodas amendment).
- 12 `saeima_bills.summary` atjaunināti.
- 1943 `claims.stance` pārģenerēti generic→saturīgais formātā, plus 453 pēc post-review LV gramatikas labojumiem (5 summaries — vote 195 lasījuma kļūda 2.→3., 2 anglicismi "amendment", 2 stilistiski).

**Saistītie:**
- Commit šī fix: `<TBD>` (kods + prompt + wiki + CHANGELOG vienā commit)
- Backfill commit: `67076a0 data(saeima): 14.05 sesijas backfill — 2 jauni balsojumi + 21 summary regen`
- Vote 197 — Butāna/Vitenberga (NA) valodas politikas priekšlikums Nr.1 (1286/Lp14), noraidīts 23-22-37 (klātesošo vairākuma noteikums); citējams kā NA stratēģijas piemērs: valodas amendmenta iebakšana militāras tehnikas grozījumu likumprojektā.

**Kad pārskatīt:** Ja `logs.action='saeima_summary_missing'` ieraksti turpina parādīties pēc 2026-05-16 fix piemērošanas — pārbaudīt, vai canonical prompt nav atgriezies pirmsregress formā, un vai kāds skripts neapiet `process_vote_snapshot()` (tieši `store_vote()` izsaukums bez `summary=` kwarg ir leģitīms tikai backfill kontekstā).

---

## 2026-05-08 — twikit Patch 5: ondemand.s.js two-stage parser (real TID restored)

**TL;DR:** 2026-04-29 diagnoze ("X izņēma `ondemand.s` referenci") bija nepareiza. Live verifikācija 2026-05-08 apstiprināja: X **mainīja formātu**, nevis to noņēma. Upstream `d60/twikit#410` PR (publicēts 2026-03-18) dokumentē divposmu lookup, ko atmina pielietoja kā Patch 5.

**Formāta izmaiņa:**
- Vecais (twikit 2.3.3 regex): `"ondemand.s":"<hash>"` — single-stage, vairs nesakrīt.
- Jaunais: `,<idx>:"ondemand.s"` ... `,<idx>:"<hash>"` — divposmu lookup pa numerisko indeksu.

**Patch 5 izmaiņas (`scripts/patch_twikit.py`):**
- `ON_DEMAND_FILE_REGEX` → `,(\d+):["']ondemand\.s["']`
- Jauns `ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'` otrā posma hash lookup-am.
- `INDICES_REGEX = r"\[(\d+)\],\s*16"` (vienkāršots, captures group 1).
- `get_indices()` pārrakstīts kā divposmu parse (find index → resolve hash → fetch ondemand.s.<hash>a.js).
- Patch 4 try/except wrap saglabāts kā safety net — ja regex atkal driftē, fallback uz stub TID joprojām strādā.

**Verificēts 2026-05-08:**
- 5/5 cookie slot-i ražo reālu TID (key no twitter-site-verification meta, indices=[2,31,16], row=16). Bez stub.
- `UserTweets`, `SearchTimeline`, `UserTweetsAndReplies` (Replies tab) — visi 3 endpoint-i strādā.
- `SearchTimeline` atgrieza 10 LV-political rezultātus uz "Saeima" query (kopš 2026-04-29 atgriezas tikai 404 ar stub TID).
- `Replies` endpoint atgrieza 19 ierakstus @edgarsrinkevics.

**Sekas:**
- `@mentions-monitor` 3rd-party mention coverage atjaunota (workaround joprojām kodā kā fallback; detaļu piezīme vēsturiski dzīvoja privātajā atmiņā — kods ir avots).
- `fetch_user_replies()` darbojas atkal — `_replies_broken_slots` tagad paliek tukšs.
- Plan `docs/superpowers/plans/archive/2026-05-04-x-tid-generator.md` (NOT IMPLEMENTED) → marķēts `RESOLVED 2026-05-08` (problēma atrisināta upstream, ne ar mūsu reverse-engineering).

**Kad pārskatīt:** Ja `client.client_transaction.key == "AAAA..."` pēc request-a, X atkal kaut ko mainījis. Palaid `python scripts/patch_twikit.py --refresh`; ja regex driftējis, atjauno `ON_DEMAND_FILE_REGEX` un `ON_DEMAND_HASH_PATTERN` patch_twikit.py.

**Saistītie:** commit `9d5a26a`, `wiki/operations/twikit-notes.md § 2026-05-08`, `src/x_scraper.py:fetch_user_replies` docstring update.

---

## 2026-05-05 — VAD Phase 2: 5 papildu homonīmu sanācija

Audita gaitā ar jauno `scripts/audit_vad_family_clusters.py` skriptu atklāti 5
papildu pidi ar disjoint immediate-family klasteriem starp paralēlām
deklarācijām — pierādījums, ka Phase 1.5 whitelist bija par plašs un
iekļāva institūcijas, kas pieder homonīmiem (citiem cilvēkiem ar to pašu
vārdu+uzvārdu):

- pid 101 Inese Kalniņa: 37 → 5 dekl (Saeima only; LNA + Tiesu adm = 2 atšķirīgi homonīmi)
- pid 104 Līga Kļaviņa: 26 → 4 dekl (Saeima only; FM valsts sekretāra vietniece = atšķirīgs cilvēks)
- pid 107 Linda Liepiņa: 16 → 11 dekl (Saeima only; KNAB Vecākais inspektors = atšķirīgs cilvēks)
- pid 116 Gatis Liepiņš: 40 → 5 dekl (Saeima only; Valsts policijas Jaunākais inspektors = atšķirīgs cilvēks)
- pid 132 Jānis Skrastiņš: 27 → 4 dekl (Saeima only; Zvērināts notārs = atšķirīgs cilvēks)

§ 2 top-15 pārrēķināts: Vucāns kāpj #1 (was #3), Kalniņa/Kļaviņa/Skrastiņš
izkrīt no top-25 pavisam. § 218 piezīmes par "paralēliem amatiem"
izdzēstas (faktoloģiski nepatiesi). § 325 metodika precizēta. § 9
sanācijas hronikā pievienots Phase 2 ieraksts.

T7 atklāja un izlaboja parsēšanas defektu — VID portāla HTML reizēm
satur identiskas `<tr>` rindas, ko parser saglabāja kā dubultas
ierakstas. `_parse_income()` tagad dedupē at parse-time. Backfilled
7 atlikušās dubultās rindas no `vad_income`.

Family-cluster audita skripts (`scripts/audit_vad_family_clusters.py`)
kļūst par turpmāku pre-publish gate. Atlikušie 13 flagged politiķi
(klasificēti `docs/audits/2026-05-05-vad-residual-clusters.md`) ir
remarriage/parsing artefakti vai vēsturiskie homonīmi, kas neietekmē
2024-25 ranking — atstāti audita ciklam.

Plāns: `docs/superpowers/plans/archive/2026-05-05-vad-homonimu-sanacija.md`.

---

## 2026-05-03 — VAD analīzes publicēšana + sanācijas audits T1-T11

**TL;DR:** Pēc 1.5. posma sanācijas darba (2026-05-02 → 2026-05-03 rīts) lietotājs pieprasīja "pilnīgi precīzus datus" pirms VAD analīzes publicēšanas. Plāns `docs/superpowers/plans/archive/2026-05-03-vad-analize-sanacija.md` (11 uzdevumi T1-T11) atklāja un labotā 7 datu kvalitātes kategorijas. Analīze publicēta atmina.lv/analizes/vad-2026.html ar verificētiem 1:1 sakrītošiem skaitļiem ar politiķu profila lapām.

**Galvenās sanācijas darbības:**

- **T1-T4 — 4 augstu ienākumu politiķu disambig**: Mārtiņš Daģis (JV b.1976 Saeimas dep) atšķirts no Mārtiņa Daģa (b.1988 Kustība Par! Jelgavas dome); Agnese Lāce (PRO Kult.min) NMPD homonīms izslēgts + SIF whitelist viņas pre-politiskajai karjerai; Andris Kulbergs (AS) Valsts policija izslēgts; Jānis Vucāns (ZZS, ex-Ventspils Augstskolas rektors) Madonas policija izslēgts.
- **T5 — Ienākumu dedup**: § 3 tabulā tagad unikāli `(politiķis, gads, avots, summa)` — Inese Kalniņas 3 paralēlie amati neuzpūš algu summu (265K → 184K).
- **T6 — Profila count metodika**: § 5 (uzņēmumi) un § 6 (NĪ) re-rank'ots, lai sakristu ar to, ko lietotājs redz politiķa profila lapā (unikāli grupēti tuples + iepriekšējā gada noņemtie). Brigmanis no NĪ #1 (kumulatīvi 249) izkrīt no top-15 (4 unikāli grupē 12 raw rindas).
- **T7 — 17 ārvalstu NĪ atklāti**: Brigmana Lielbritānija (Derby) 12 ieraksti kopš 2014; Zīle, Kols, Melbārde Beļģija (Brisele) — EP/NATO darba dēļ.
- **T8 — Hosams Abu Meri**: Vārda saskaņošanas modulis naīvi sadalīja (vārds = "Hosams Abu", uzvārds = "Meri") — 0 rezultāti. Manuāls labojums atjauno 15 deklarācijas. Inga Bērziņa joprojām 2 dekl (VID safety-bound 200 rindas; Vidzemes slimnīcas homonīms 368 rindu) — 2. posma uzdevums.
- **T9 — § 5b USD/GBP sadaļa**: Dombrava 8 USD paketes (Diamondback, Barrick, SM Energy) USD 105 380; Kiršteins (LPV) NVIDIA+Meta+Broadcom USD 21 283; Kulbergs Inchcape plc GBP 2 670. Variant C: vērtības glabājas oriģinālajā valūtā, nekonvertētas.
- **T10-T11 — Galīgais audit + publikācija**: Visa anglicismu tīrīšana, skaitļu sinhronizācija (§ 5/§ 6/§ 7 atjaunoti pēc T1-T8 DB), valodas precizēšana, tad publicēšana.

**Datu kopas pārmaiņas:**
- Total VAD: 2348 → **2262** (-1221 contam DELETE + 70 yest reingest + 123 šorīt T8 reingest + 4 audit politiķu reingest)
- Politiķu skaits ar dekl: 143 → **144** (Hosams pievienojas)

**Jauni skripti:**
- `scripts/seed_homonimu_disambig.py` (multi-pid curator priekš 4 audit homonīmiem)
- `scripts/audit_vad_profile_match.py` (analīze ↔ profila atbilstības gate)
- `scripts/audit_vad_foreign_re.py` (ārvalstu NĪ pārbaude)
- `scripts/compute_vad_profile_counts.py` + `rank_vad_profile_counts.py` (top-N re-rank pa profila count)
- `scripts/cleanup_contaminated_vad.py` paplašināts ar `--politician` flag

**Saistītie:** plāns `docs/superpowers/plans/archive/2026-05-03-vad-analize-sanacija.md`, analīze `content/analizes/vad-2026.md`, atmina.lv lapa [/analizes/vad-2026.html](https://atmina.lv/analizes/vad-2026.html).

---

## 2026-05-03 — Ingmārs Līdaka matcher kļūda (pid=109 negative_patterns)

**TL;DR:** 2026-05-03 rīta claim-extractor sweep atklāja, ka pid=109 Ingmārs
Līdaka (AS Saeimas dep) bare-surname "Līdaka" name_form salinkoja rakstu par
**Gunta Līdaka** (FM/KM darbiniece) un Puntuļa tweet par citu Gunta Līdaka.
Audit: 6 junction rows total, 2 false-positive (doc_id 29378 web, 7363 tweet),
4 leģitīmi.

**Fix komponents:**
- `tracked_politicians.negative_patterns` (pid=109) = `["Gunta Līdaka", "Guntas
  Līdakas", "G. Līdaka", "G.Līdaka", "Gunta Līdakas"]`. Matcher reject'oja
  doc 29378 verifikācijā.
- 2 false-positive `document_politicians` junction rows DELETE'd.
- Reproducible curator: `scripts/seed_lidaka_disambig.py` (idempotents).

**0 claims affected** (abas false-positive doci tika empty-ekstraktētas pirms
fixa, pid=109 saglabā 143 leģitīmus claims).

**Saistītais pattern:** Tas ir tas pats matcher name-collision pattern, kas
2026-04-23 bug fixoja pid=146 Andris Bērziņš (ZZS dep vs bijušais prezidents).
Visiem politiķiem ar publiski pazīstamiem homonīmiem ārpus mūsu tracked
saraksta vajadzētu `negative_patterns` curator pass — Phase 2 backlog idea.

---

## 2026-05-02 (vakars) — VAD Phase 1.5: homonīmu cleanup + retry + Hosams override

**TL;DR:** Pēc 152-politiķu sweep (215 min, commit `8744277`) atklāja 3
deploy-blocking problēmas: (a) **homonīmu kontaminācija** 11 pidiem ar identiska
Vārds+Uzvārds (1221 dekl ar dažādu cilvēku datiem zem mūsu opponent_id —
Andris Bērziņš 228, Inese Kalniņa 205, Inga Bērziņa 184 utt.); (b) **parse-fail uz
1304 UUIDs** (VID anti-scrape mehanisms invalidates UUID nonces pēc N rapid
requests, detail returns redirect HTML bez `<table>`); (c) **Hosams Abu Meri**
naïve split dod ("Hosams Abu", "Meri") — VID search atgriež 0. Phase 1.5 worktree
`vad-phase-1.5` (PR #19) atrisina visus trīs.

**Why:** Reputational risk pirms publiska deploy — politiķa profilā par "Andris
Bērziņš" (ZZS Saeimas dep) tiktu rādītas bijušā prezidenta + Salaspils SIA
darbinieka + Smiltenes pašvaldības inspektora deklarācijas. F14 zaudētie 1304
UUIDs nozīmē 30-40% sweep coverage gap.

**Arhitektūra:**
- **A2 disambig (DB-driven)** — `tracked_politicians.keywords` JSON dabū jaunu
  `vad_disambig` lauku ar substring whitelist per pid. Filter rule: ja saraksts
  nav tukšs, row tiek pieņemts ja kāds substring (case-ins) match `r.institution`
  VAI `r.position_title`. Reuse esošo `negative_patterns` kā override-reject (pid
  146 jau ir "bijušais Valsts prezidents" u.c.). Bez hints — trust full-name
  search (pašreizējā uzvedība, droša unikāliem vārdiem). DB-driven, lai operators
  var pievienot pidus bez code release.
- **Retry on parse-fail** — `VadClient.reset_session()` jauna metode (clears
  `_session_initialized` + cookies). Orchestrator `fetch_for_politician` catches
  `ValueError("nav header table")`, calls reset → re-search → atrod fresh row pēc
  natural-key match → retry detail fetch. Max viens retry per row.
- **Name override** — `_NAME_OVERRIDES[161] = ("Hosams", "Abu Meri")`.

**Fix komponents:**
- `337f793` `src/vad/matcher.py` — Hosams override.
- `f3ceb90` `src/vad/declarations.py` — `_load_disambig_config()` + `_row_passes_disambig()`
  + filter wire-up `fetch_for_politician`. 4 jauni testi.
- `c82636b` `src/vad/fetch.py:reset_session()` + orchestrator retry. 1 fetch test +
  2 declarations testi.
- `a1f843f` `scripts/ingest_vad_declarations.py` — `Path("logs").mkdir(exist_ok=True)`
  (F15 silent crash fix).
- `a4c965a` `scripts/seed_vad_disambig.py` (curator) + `cleanup_contaminated_vad.py`
  (DELETE + targeted reingest).

**Curated hints — 11 contaminated pids** (apstiprināts Telegram msg 1584):
146 Andris Bērziņš (ZZS Saeimas dep), 101 Inese Kalniņa (JV), 144 Inga Bērziņa (JV),
104 Līga Kļaviņa (ZZS), 138 Jānis Zariņš (JV), 106 Līga Kozlovska (ZZS),
155 Dace Melbārde (NA IZM), 92 Iļja Ivanovs (Stab), 25 Viktors Valainis (ZZS Ekon.),
132 Jānis Skrastiņš (JV notārs), 107 Linda Liepiņa (LPV KNAB).

**Trade-off:** Pirms-politiska karjera ar inst='-' tiek nogriezta — neiespējami
atšķirt no homonīmiem bez gada filtra. Konkrētas pre-Saeima karjeras iekļautas
hints, ja varu droši identificēt (Kļaviņa Finanšu min, Skrastiņš notārs, Liepiņa
KNAB).

**Sweep rezultāts (post-cleanup, 2026-05-03 rīts):**
- DELETE 1221 dekl (11 pids); reingest ar disambig filter (2026-05-02 vakars +
  2026-05-03 rīts cooldown re-run) dod **193 jaunas legit dekl**: 146=31, 101=37,
  144=2, 104=26, 138=13, 106=10, 155=9, 92=5, 25=17, 132=27, 107=16. Errs=0
  (8 pids re-run 2026-05-03 ar O(n) retry hot-fix `8baf4a6`).
- Total VAD: 3376 → 2348 (–1028 net pēc contam DELETE + 193 jaunās).
- 8 commits + plan + curator scripts + CHANGELOG (šis ieraksts) + render baselines REGEN.

**Skat.:** spec § 15.2 F13/F14/F15, plan `docs/superpowers/plans/archive/2026-05-02-vad-phase-1.5.md`,
handoff `docs/superpowers/handoff-vad-phase-1.5.md`.

---

## 2026-05-02 (vēlās dienas) — VAD `role_matches` always-True fix (production smoke)

**TL;DR:** Pēc Phase 1 land production smoke (5 sample politiķi) atklāja, ka
`src/vad/matcher.py:role_matches` per-row keyword overlap dod false-negatives
3/5 gadījumos: Šlesera DB role "LPV priekšsēdētājs" (partijas amats), Kleinberga
"Rīgas mērs" ≠ VID "Valstspilsētas domes priekšsēdētājs" (sinonīmu paši label),
Pūpola "EP deputāts" ≠ VID Rīgas dome (vēsturiskie amati). DB ir 5 homonīmu pāri
ar dažādiem PIRMAJIEM vārdiem — VID search ar full Vārds+Uzvārds atgriež TIKAI
vienu personu, role disambiguation per-row ir lieks. `role_matches` pārveidots uz
`return True` ar full rationale docstring; re-ingest 5 sample politiķiem ielādēja
17+16+15+7+2+5 = 62 deklarācijas, 0 false-negatives.

**Why:** Sākotnējais nolūks (homonīmu aizsardzība) reālā nepastāv — first-name
disambiguation pietiek. Per-row check tikai radīja regressions ar realistic
DB role label variation.

**Fix komponents (commit `986ece4`):**
- `src/vad/matcher.py:role_matches` — pārveidots uz `return True`, docstring
  dokumentē sākotnējo nolūku, empīrisko evidence un re-introduction trigger
  (ja kādreiz novērojam VID atgrieztus multiple distinct persons one search'ā).
- `tests/test_vad_matcher.py::test_role_matches_always_true` — apvieno iepriekšējos
  4 testus, asertē True priekš visu kombināciju.
- `tests/test_vad_declarations.py::test_fetch_for_politician_lenient_role_post_2026_05_02_fix`
  — vecais skip-on-Žurnālists test invertēts (skip_role=0, new=1).

---

## 2026-05-02 — VAD declarations Phase 1 (UI tab + delta render)

**TL;DR:** "Deklarācijas" tab pievienots politiķa profilā (deputy, minister, mep,
regional, former, politician profile_kinds — has_vad_data konditionāls). Tab satur
year selector (top 5 gadi), 9 sekciju akkordeoni ar delta marķieriem (jauns/
mainījies/aizgāja), ģimene zem collapsed details (etika), source link uz VID
search ar pre-filled vārdu.

**Arhitektūra:**
- `src/render/vad.py` — batch fetch ar one query per tabula (F4 leaf-vs-fan-out
  paterns). Try/except OperationalError guard test DB priekš (saeima_bills
  precedents `src/render/politicians.py:503`).
- `src/vad/diff.py` — year-over-year delta engine ar 5% threshold un identity
  keys per sekcija (skat. spec § 9.2 tabula).
- `templates/_vad_panel.html.j2` — partial, included no `politician.html.j2`.
- `assets/style.css` — `.vad-delta-{new,modified,removed,unchanged}` ar
  green/yellow/red/muted krāsām, `.vad-section` border-separated akkordeoni.
- `src/profile_kind.py` ekvivalents `_profile_tab_set` (`src/render/politicians.py:110`)
  paplašināts ar `has_vad_data` argumentu, `render_politicians()` ielādē
  `get_vad_data_for_politicians` reizē batch.

**Render performance:** Single batch query 11 tabulām × visi 152 politiķi
veikta vienu reizi pirms render loopa, ne N+1.

**Privātums:** Ģimene renderēta zem `<details>` collapsed default — saskan ar
spec § 9.5 ētisko politiku (publiska, bet nepiespiedu).

**Testi:** 33 jauni testi (3 schema + 12 parsing + 4 fetch + 12 matcher + 5
declarations + 7 diff + 5 render + 8 profile_kind_vad). Visi PASS uz
vad-deklaracijas branch.

**Sākotnējais sweep:** Operatora rokas — pēc šī Phase 1 land jāpalaiž
`scripts/ingest_vad_declarations.py` no main checkout, tad `generate_public_site()`
re-render. Mēneša rutīna sākas no nākamā mēneša.

---

## 2026-05-02 — VAD declarations tracker (Phase 0 ingest)

**TL;DR:** Jauns `src/vad/` pakete ielādē strukturēti VID amatpersonu deklarācijas
no www6.vid.gov.lv/VAD priekš 152 izsekoto politiķu. 11 jaunas `vad_*` tabulas,
manuāls CLI ingest (`scripts/ingest_vad_declarations.py`) ar mēneša cikla
noklusējumu, peak aprīlis-maijs.

**Why:** Lietotāja pieprasījums (Telegram 2026-05-02) — automatizēt deklarāciju
ielādi, lai politiķa profilā varētu rādīt strukturētu finansiālo + ģimenes profilu
ar gads-pa-gadam delta marķieriem. Daudz signāla par interešu konflikta
detektēšanu (Phase 3 backlog).

**Arhitektūra (sekojot `src/saeima/` precedentam):**
- `src/vad/schema.py` — DDL un `init_vad_tables()` (lazy, ne `init_db()`).
- `src/vad/fetch.py` — `VadClient` httpx + bounded From= loop + 10s/3s throttle (F12).
- `src/vad/parsing.py` — `parse_declaration_html()` BeautifulSoup → Pydantic.
- `src/vad/matcher.py` — name split + ASCII fallback + role disambiguation.
- `src/vad/declarations.py` — orchestrator `fetch_for_politician`.
- `scripts/ingest_vad_declarations.py` — CLI.

**11 tabulas:**
`vad_declarations` (header) + 10 sekciju tabulas (positions/real_estate/companies/
vehicles/savings/income/transactions/debts/loans_given/family). NAV `documents`
rindas (saeima 2026-04-25 invariants). NAV `claims` rindas (deklarācija ≠ retoriska
pozīcija).

**Idempotence (F11):** UNIQUE pa dabīgo atslēgu `(opponent_id, declaration_kind,
declaration_year, submitted_at, position_title)`. `vad_uuid` rotē per-call (anti-scrape
session-bound nonce; empīriski apstiprināts), tāpēc nelietojams idempotencei —
glabājas kā nullable audit lauks ar latest-seen vērtību.

**Drošības margināli:**
- Throttle: 10s starp politiķiem (F12 — sub-second back-to-back search dod ReadTimeout),
  3s starp deklarācijām → ~28 min mēneša sweep, ~48 min initial backfill.
- Bounded `From=` loop ar 200-row safety bound + log warn pie >100.
- Cookie management: explicit set/delete pa fetch_detail, NEpaļaujas uz session jar.
- Modernie ieraksti only (legacy `/VAD2002Data` Phase 0.5 backlogs).
- Role-disambiguation pret 5 homonīmu pāriem DB (Šlesers Ainārs/Ričards utt.).

**Spec un plāns:**
- Spec: `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` (commit `dda5478` ar F11+F12 amendments)
- Plāns: `docs/superpowers/plans/archive/2026-05-02-vad-deklaracijas-plan.md`

**Sākotnējais sweep:** Tasks 17-18 plānā — mēneša rutīnas pirmā palaišana no main checkout pēc Phase 1 land.

---

## 2026-05-01 (vakars) — `og.jpg` MUST be baseline JPEG (Twitter Card render fix)

**TL;DR:** `src/image_variants.py` ģenerēja og.jpg ar `progressive=True`, kas izraisīja klusu Twitter Card render kļūmi — meta tagi pareizi, attēls 1200×630 pieejams ar HTTP 200, bet x.com preview palika tukšs. Pārkodējot uz baseline JPEG (`progressive=False`) preview ielādējās. Šī ir **nemainīga prasība** social-card kontekstā — fix `src/image_variants.py:96` + regresijas tests `tests/test_image_variants.py::test_og_jpeg_is_baseline_not_progressive`.

**Why:** Twitter Cards vēsturiski silently fail uz progressive JPEGs — nav error message, nav fallback, tikai blank preview. Citas platformas (Facebook OG, LinkedIn) handle abus, bet Twitter strict mode nē. og.jpg variants eksistē *specifiski* social previews, tāpēc baseline ir drošākais default. Šī uzvedība dokumentēta vairākās SEO/social tooling guides bet nav prominenta Twitter oficiālajā dokumentācijā — tāpēc viegli aizmirstama / atspēlējama.

**Diagnostiskā plūsma:** 2026-05-01 dienas pārskats neielādēja preview x.com pat ar `?v=1` cache-bust. Verificēja: meta tagi pareizi (`twitter:card=summary_large_image`, `og:image` kanonisks 1200×630), attēls fetch'ojas HTTP 200 ar Twitterbot UA, robots.txt `Allow: /`, HTTPS valid (Sectigo), nav redirect. `file og.jpg` izvads atklāja `progressive` flag → konvertēja uz baseline → preview ielādējās ar `?v=2`.

**Fix komponenti:**
- `src/image_variants.py:96` — `progressive=True` → `progressive=False` ar inline komentāru kāpēc.
- `tests/test_image_variants.py::test_og_jpeg_is_baseline_not_progressive` — pin'o uzvedību (PIL `img.info["progressive"]` falsy assertion). Future contributor, kas pārslēdzas atpakaļ "smaller file size" iemeslam, tiks noķerts CI.
- 2026-05-01 brief variants (image_id=59) re-encoded in-place + redeploy (203 KB diff).

**How to apply:** Visas brief / synthesis featured images, kas iet caur `make_variants()`, automātiski ģenerē baseline og.jpg pēc šīs izmaiņas. Nekāda manuāla iejaukšanās jaunām dienām nav nepieciešama. Hero/card/thumb webp variants nav ietekmēti (WebP nav progressive flag tādā pašā nozīmē).

**Plus side benefit:** Baseline JPEGs ir sekmīgāks ielādes UX uz lēna mobile — sequential pixel rows redzama no augšas uz leju, kamēr progressive sākotnēji rāda blurry full image. Tas pāradresē kompromisu: progressive bija optimizēts perceptīvajai veiktspējai, bet sociālajos previews nestrādāja vispār.

---

## 2026-05-01 — Role-aware profila tabi: `src/profile_kind.py` + tab dispatch

**TL;DR:** Politiķa profila lapa vairs nerāda statisku 9 tabu komplektu — tagad katram politiķim 3-5 tabi atkarībā no `profile_kind` (10 vērtību enum: deputy, minister, mep, regional, politician, journalist, analyst, organization, former, inactive). Žurnālistiem un analītiķiem nav Pozīciju taba, bet ir Komentāri-by un Publikācijas. Ministrēm nav Saeimā taba (viņi parasti nebalso). Spriedzes tab aizvietots ar Saites tab — mini-grafs SVG + 3 type-color sekcijas (uzbrukumi sarkans / spriedzes dzeltens / atbalsts zaļš) + commentary-about + vote-alignment top/bottom (deputātiem) + linka uz pilno `/saites.html`.

**Why:** 9-tabu komplekts visiem profiliem radīja kognitīvo slodzi un pretrunīgus tukšumus — žurnālistam Pozīciju tab vienmēr tukšs, ministrei Balsojumu tab vienmēr 0 (Siliņa, Braže, Sprūds), Spriedzes stat-poga lump'oja uzbrukumus + spriedzes + atbalstu zem viena skaitļa. Pēc tension #90 dzēšanas Šleseram rādīja "1 spriedze" lai gan reālā spriedze bija type='uzbrukums' — tas atklāja klasifikācijas defektu. Reorganizācija balstīta uz 2026-05-01 Telegram dizaina sesiju (Elviss ↔ Claude Opus 4.7) — sk. plāna §1.

**Arhitektūra (sekojot `src/coalition.py` precedentam):**
- **`src/profile_kind.py`** (jauns, ~110 LOC ar docstring) — `Literal["deputy", "minister", "mep", "regional", "politician", "journalist", "analyst", "organization", "former", "inactive"]` enum, `derive_profile_kind(rel, role, votes_count)` ar 10 first-match-wins likumu sarakstu, `get_profile_kind_map(db)` batch helper (one round-trip ar GROUP BY votes).
- **Compute-at-render** — `profile_kind` netiek glabāts DB. Aprēķināms no esošajiem `tracked_politicians.relationship_type` + `role` + `saeima_individual_votes` skaita. Role pārdēvēšana vai votes backfill plūst caur nākamajā `generate_public_site` palaišanā bez migrācijas.
- **`src/render/_common.py`** re-eksportē `derive_profile_kind` + `ProfileKind` per F4 leaf rule, lai `politicians.py` neimportē tieši no `src.profile_kind`.

**Derivācijas likumi (pirmais match wins, sk. `src/profile_kind.py:derive_profile_kind`):**
1. `relationship_type='inactive'` → `inactive`
2. `relationship_type='journalist'` → `journalist`
3. `relationship_type='organization'` → `organization`
4. `relationship_type='neutral'` → `analyst`
5. role satur `ministr`/`valsts kanc`/`valsts prezident` (pēc bijuš-chunk filtra) → `minister`
6. role satur `\bep\b` (word-anchored) vai `eiropas parlament` → `mep` *(catches both `EP deputāts` + EP leadership roles ar substring-style match would miss — Roberts Zīle "EP viceprezidents")*
7. role satur `mērs`/`vicemērs`/`domes` → `regional`
8. `current_term_vote_count > 0` → `deputy`
9. role.lower() satur `bijuš` → `former`
10. else → `politician`

**Bijuš-chunk filtrs (regex `^biju[sš]`):** Multi-role string-i kā `"Saeimas deputāte, bijusī Izglītības un zinātnes ministre"` (Anda Čakša) sadalīti pa komatiem; chunki, kas sākas ar past-participle "bijus(ī|i|a)" / "bijuš(...)" tiek atfiltrēti PIRMS substring match. Bez tā likums 5 (`'ministr' in active_role`) noķerm bijušo lomu un Čakša mis-classificē kā ministrs. Sākotnējais regex `^bijuš[aīi]\b` arī izlaida `Bijušais Rēzeknes mērs` (Bartaševičs) — `\b` neaktivējās pirms `i` rakstā `bijušais` — pēc paplašināšanas uz `^biju[sš]` šis case korekti klasificējas kā `former`.

**Profile_kind sadalījums DB (174 active, 2026-05-01):**
- 99 deputy, 18 minister, 11 regional, 8 mep
- 16 politician (Hermanis, Šlesers, party officials, board members)
- 15 journalist, 5 analyst (rel=neutral)
- 2 organization (LDDK, Saeimas ziņas)
- 1 former (Bartaševičs — bijušais Rēzeknes mērs)

**Tab mapping per kind:**
| Kind | Tabi |
|------|------|
| deputy | timeline, pozicijas, saeima, pretrunas, saites (5) |
| minister/mep/regional/politician | timeline, pozicijas, pretrunas, saites (4) |
| former | timeline, pozicijas, saeima (vēsturisks marker), pretrunas, saites (5) |
| organization | timeline, pozicijas, saites (3) |
| journalist/analyst | timeline, komentari-by, publikacijas (+ pretrunas/saites if data, max 5) |
| inactive | timeline (1) |

`saeima` tab apvieno iepriekšējos `balsojumi` + `likumprojekti`. `publikacijas` tab apvieno žurnālistu/analītiķu X+Ziņas. Citiem profiliem X+Ziņas inline zem Pozīcijas. Iepriekšējais `spriedzes` tab aizstāts ar `saites` tab.

**Saites tab (mini-grafs + type-color sekcijas):** Statisks SVG (400×280 viewBox) ring-layout ar centra mezglu (politiķis ar partijas krāsu) un līdz 8 kaimiņiem (tension partneri, dedupe pa pid, ar pre-computed x/y koordinātām Python pusē — Jinja nav iebūvētu trig filtru). Sekcijas: Uzbrukumi (sarkans #ef4444), Spriedzes (dzeltens #eab308), Atbalsts (zaļš #22c55e), Komentāri par šo politiķi (commentary_about), Vote-alignment top/bottom (TIKAI deputātiem; SQL pār `saeima_individual_votes` self-join, HAVING total>=10, top/bottom-3 by agree_pct). Linka uz `/saites.html` apakšā.

**Helper funkcijas pievienotas `src/render/politicians.py`:**
- `_profile_tab_set(kind, has_contradictions, has_saites_content)` — base mapping + has_data konditionals žurnālistiem/analītiķiem.
- `_vote_alignment_for(db, pid, top_n=3)` — per-pid vote-alignment query, F4 leaf rule (links.py `_fetch_graph_data` optimizēts globālam graph view ar threshold filtru, ne per-pid).
- `_saites_neighbors_with_coords(neighbors, cx, cy, r)` — pre-compute SVG ring-layout x/y.
- `_fetch_saites_for_profile(db, pid, kind, tensions, commentary)` — splits by tension_type, runs vote_alignment for deputies, builds 8-neighbor mini-graph.
- `_fetch_commentary_by(db, pid)` — claims kuros politiķis ir speaker_id (mirror of `_fetch_commentary_about`).

**Template (`templates/politician.html.j2`):** Visi stat-buttons + tab content blocks aplikti `{% if 'X' in tab_set %}`. Header `.profile-role` aizstāts ar `.role-chip role-chip-{kind}` (10 hue tokens — deputy zils, minister zaļš, mep violets, regional oranžs, politician pelēks, journalist tumši pelēks, analyst smaragds, organization rozā, former oranžs, inactive gaiši pelēks). Iepriekšējie `tab-balsojumi`, `tab-spriedzes`, `tab-x`, `tab-zinas`, `tab-likumprojekti`, `tab-komentari` (versija ar commentary_about) izņemti.

**`assets/style.css` papildinājumi:** `.role-chip` + 10 kind-specific klases · `.mini-saites-graph` SVG sizing · `.saites-link-{uzbrukums,spriedze,atbalsts,vote}` stroke krāsas · `.saites-section-{...}` ar `::before` square-marker glyphs · `.alignment-list` · `.see-full-graph-link`. ~70 LOC pievienots.

**Char-fixture REGEN:** Politicians fixture flipped 174 hashes; sibling fixtures (analyses, blog, dashboard, graph, misc, parties, x) flipped because of assets `?v=` cache-bust update. Konvencija sk. 2026-04-30 entry "Drift catch" — separate REGEN commit pēc layout/CSS changes.

**Smoke-tested 8 sample profili (visi 7 active kinds):**
- Šnore (deputy) — 5 tabi, blue chip, Saites tab ar uzbrukumi + alignment top/bottom
- Siliņa (minister) — 4 tabi, NAV Saeimā, green chip
- Pupols (mep) — 4 tabi, purple chip
- Kleinbergs (regional) — 4 tabi, orange chip
- Hermanis (politician) — 4 tabi, gray chip
- Lapsa (journalist) — 5 tabi (ar pretrunas + saites jo data >0), dark-slate chip
- Rajevskis (analyst) — 4 tabi, emerald chip
- Zīle (mep, EP viceprezidents) — fix ielāpā pēc audita: substring `ep deputāt` izlaida šo, `\bep\b` regex noķer

**Nav iekļauts šajā PR (future work):**
- Personas filtra extension pa `profile_kind` (nākamais UI restrukturizācijas solis)
- Bijušais sub-badge header (header chip jau koda krāsas, atsevišķs badge bija plāna §4.2 polish — nav nepieciešams)
- Vote-alignment promotion uz `_common.py` (waiting for second consumer)
- Org advocacy vs press split (ja Saeimas ziņas + LDDK plūsma sajaucas)

**Plan + execution:** [docs/superpowers/plans/archive/2026-05-01-profile-role-aware-tabs.md](../../docs/superpowers/plans/archive/2026-05-01-profile-role-aware-tabs.md). 5 commits uz `feat/profile-roles` branch:
1. `c45299e` feat(profile_kind): module + 12 parametrized tests
2. `b9bd1f4` fix(profile_kind): broaden bijuš filter for whole-role former markers
3. `c0a15bc` feat(profile): role-aware tab dispatch + Saites mini-graf + chips
4. `2ce0d9f` test(render): REGEN char baselines (174 hash flip)
5. `24a2331` fix(profile_kind): word-anchor EP rule for leadership roles

---

## 2026-04-30 (vēlu rīts) — Drift catch: REGEN uz schema test + daily check.sh solis

Master HEAD pirmsdienas atklāja 9 sarkanus testus, kas bija operatoriskais regen-debt no PR #18 + dienas ingest pulses. Divi atšķirīgi cēloņi, divas atšķirīgas dabas, viens kopējs preventīvs labojums.

**Cēloņi:**
1. `tests/test_schema.py::test_schema_sql_matches_pre_refactor_dump` — PR #18 pievienoja `documents.title` caur `ALTER TABLE` `src/db.py:132`, bet `docs/refactor/schema-dump-pre-f2.sql` baseline neapdroš. Tests pirms šī commit-a neatbalstīja `REGEN=1` — operatoriem nebija tipiska ceļa baseline-a atjaunošanai.
2. `tests/test_render_chars.py` — 8 char-fixture failures, jo dienas ingest (~140 docs starp d38034c regen 08:31 un 10:30) izmainīja dashboard counts un index hashes. `REGEN=1` jau strādāja, bet rutīna to nepieprasīja.

**Labojumi:**
- **`tests/test_schema.py`** atbalsta `REGEN=1` — paralēli char-tests konvencijai. Saglabā header komentāru bloku, pārraksta body no fresh `init_db()` dump. ALTER TABLE PR autors tagad palaiž `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_schema.py` un commit-o atjaunoto baseline tajā pašā PR.
- **Daily routine Solis 9.5** (`wiki/operations/daily-routine.md`) — `bash scripts/check.sh` pirms publish (Solis 10). Ja sarkans, REGEN + commit, tad turpina. Drift atklājas tajā pašā dienā kad rodas, nevis nākamreiz kad atver master.

**Why:** Char drift notiek katru dienu (DB aug ar ingest); schema drift notiek vienreizēji uz katru ALTER TABLE. Abi gadījumi ir leģitīmi expected — sarkans tests bija pareizs signāls, ka baseline jāatjauno. Trūkstošais bija (a) REGEN ceļš schema testam un (b) workflow solis, kas to ķer pirms publikācijas.

**How to apply:**
- ALTER TABLE PR-i: pievieno `REGEN=1 pytest tests/test_schema.py` + commit `docs/refactor/schema-dump-pre-f2.sql` tajā pašā PR.
- Daily routine: pirms Solis 10 palaid `bash scripts/check.sh`. Ja char-tests sarkani, `REGEN=1 pytest tests/test_render_chars.py` + commit baseline JSON-us. Reālas regresijas (broken render, importa kļūda) jārisina pirms publish.

---

## 2026-04-30 — Bundle F: `documents.title` reliably populated for all news sources

Forward-fix + backfill pair. `src.title_extract.extract_title()` (Bundle A, 17 tests) runs at ingest on every web scrape path: RSS in `_parse_rss_items` (2.0 + Atom), crawl4ai in `_scrape_tier2` (tier-2 sources), trafilatura in `_scrape_web_articles` (legacy web_scraper). Persisted via `insert_document(title=...)` (Bundle B, schema migration in `init_db()`) into the existing `documents.title` column. One-shot `scripts/backfill_titles.py` (Bundle D, 6 tests) populates 2402 legacy web docs where title was NULL/empty.

**Result:** `zinas.html` render (`src/render/news.py:_fetch_news`, Bundle E) no longer uses `content[0:140]` heuristic — reads DB title directly with URL-slug last-resort fallback. Complies with Autortiesību likuma 20. pants ("darba nosaukums" obligātā norāde), supplementing existing `source_url` + `source_domain` provenance.

**Title extraction cascade:** `og:title` → `twitter:title` → JSON-LD `headline` → `<title>` → `<h1>`. Handles both forward (`property=...content=...`) and reverse (`content=...property=...`) meta-attribute ordering (Yoast/Drupal Metatag pattern), HTML entities, whitespace collapse, 250-char cap.

**Suffix-strip patterns** (26 entries, case-insensitive): LSM.lv/LSM, Delfi (incl. capitalized), Latvijas Avīze/LA.lv, Jauns.lv, TVNet/tvnet.lv, Diena/diena.lv, NRA/nra.lv, LETA, rus.delfi.lv.

**Bundle breakdown:**
- **A** (`src/title_extract.py` + tests): Pure HTML title extractor, stdlib only.
- **B** (`src/db.py` migration): `insert_document(title=...)` + `init_db()` column setup for fresh DBs (schema.sql untouched per convention: migrations in code, not regenerated).
- **C** (`src/ingest.py` + tests): Wire extractor into RSS/crawl4ai/trafilatura paths + `_ingest_source` plumbing.
- **D** (`scripts/backfill_titles.py` + tests): Idempotent one-shot script (`--apply` flag). `derive_title_from_content()` picks first reasonable line (10-250 chars), strips LA.lv " 0" noise, normalizes via `src.title_extract._normalize`. CLI: `--limit N` for test runs.
- **E** (`src/render/news.py`): Drop heuristic, read DB title.

**Operator post-merge sequence (CRITICAL):**
1. `python -m scripts.backfill_titles` — dry-run from main worktree (expect ~2200 derived, ~2402 NULL rows)
2. `python -m scripts.backfill_titles --apply` — apply to `data/atmina.db`
3. `python -m pytest tests/test_render_chars.py::test_zinas_index_byte_identical -v` — **WILL LIKELY FAIL** (Bundle E drops the multi-step heuristic; rendered output changes for rows where old heuristic ≠ new DB-title-first logic)
4. If step 3 fails: REGEN baseline with diff review:
   - `python -c "from src.render import generate_public_site; generate_public_site()"`
   - Manually inspect `output/atmina/zinas.html` against pre-merge state
   - Update `tests/fixtures/render_baseline_misc.json` SHA-256 hash for `zinas.html` (operator diff review is the gate, not blind regen)
5. `python -c "from src.render import generate_public_site; generate_public_site()" && bash scripts/deploy.sh --dry-run` then live deploy

**Follow-up items (out of scope here, referenced for continuity):**
- **Excerpt-slicing assumption** in `src/render/news.py:75-80` (`rest = content[len(headline):].strip()`) is pre-existing tech debt: assumes `headline` is a substring prefix of `content`, generally false when `title` comes from meta tags rather than body. After Bundle E this path runs more often (more rows have DB title). See cleanup ticket when prioritized.
- **Author name extraction** (Autortiesību likuma 20. panta otra prasība — "darba autors(-i)") — `documents.author` column not yet added. Plan forward-fix when prioritized. Reference: source plan at `docs/superpowers/plans/archive/2026-04-30-zinas-title-extraction.md` § Out of scope.

**Schema note:** `schema.sql` remains unmodified (existing convention: `init_db()` migrations, not schema regeneration). Live DB already had `title` column from prior migration; Bundle B adds migration to fresh-DB bootstrap path for test suite.

**Plan + tracking:** [docs/superpowers/plans/archive/2026-04-30-zinas-title-extraction.md](../../docs/superpowers/plans/archive/2026-04-30-zinas-title-extraction.md).

---
## 2026-04-30 — F3g: F3 noslēguma posms — Fāze 3 PILNĪBĀ PABEIGTA

**TL;DR:** F3g closure merged ar 3 commits PR #17: `generate_public_site` + `_generate_sitemap` + `_generate_og_image` izvilkti uz `src/render/_orchestrator.py` (444 LOC). `src/render/__init__.py` re-eksportē tos kā **kanonisko publisko ceļu**: `from src.render import generate_public_site`. `src/generate.py` 558 → **173 LOC** (-385) plašs re-export shim. `render_parties` self-contained (F3g.2) + `_load_wiki_profile` restored politicians.py:310 (F3g.3 — F3b regression fix). **Total trajectory: 4250 → 173 LOC (-96%). Fāze 3 closed.**

**PR #17 trajectory (3 commits + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `ac5fe83` | test | 4 char fixtures | REGEN: politicians (~150 hashes flip — F3g.3 wiki_profile bodies aktīvi), misc/x/dashboard data drift |
| `335c816` | refactor | 7 files (incl. new _orchestrator.py) | F3g.1 lift + F3g.2 parties + F3g.3 wiki_profile |
| `9262213` | docs | agent_api_inventory.txt | Full rewrite for canonical src.render path |
| `6ab0019` | merge | (PR #17) | |

**F3 final module map (17 src/render/* moduļi):**
- `_common.py` (~795 LOC, leaf — gains `_load_wiki_profile` from F3g.3)
- `_orchestrator.py` (444 LOC, jauns — owns generate_public_site + _generate_sitemap + _generate_og_image)
- 15 sub-page moduļi: `contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses, blog, dashboard`

**`src/generate.py` paliek (173 LOC re-export shim):**
- Re-eksportē ~85 simbolus no `src.render._common` + 15 sub-page moduļiem
- Tests + agents + scripts turpina importēt no `src.generate` bez izmaiņām
- CLI entry-point `if __name__ == "__main__"` saglabāts

**F3g.3 — wiki_profile restoration impact:**
- 162 `wiki/persons/<slug>.md` faili eksistē
- ~150 of 159 politiku detail pages tagad satur editorial profile body
- F3b regression (PR #7 hardcoded `wiki_profile = None`) atrisināts
- `_load_wiki_profile` paaugstināts no `analyses.py` uz `_common.py` (politicians-concern)

**Cycle safety:**
- `_orchestrator` imports `_common` (leaf) + every sub-page (each leaf relative to peers)
- `_common` imports nothing from `src.render.*` — terminal
- Sub-pages import only from `_common` — never peer
- `__init__.py → _orchestrator → _common (loaded fully) → sub-pages → _common (cached)` chain works
- Reviewer verified concrete: `from src.render._common import _slugify` runs without error

**Plan deviation flagged:**
- Plan paste-block targeted `src/generate.py <50 LOC re-export shim`. Reality: 173 LOC. Difference is the wide shim itself — 14 sub-page imports + ~85 symbol re-exports — necessary to keep the test suite + agent contract intact. `<50 LOC` target ignored shim widening.

**F3 deferred items (not blocking F3 closure, kept for future opportunity):**
- F3g.4: `_chronologize_contradiction` + `_tension_filter_axes` helper promotions to `_common` (F3f.3 reviewer NICE-TO-HAVE) — dups exist, low leverage
- F3g.5: vestigial alias cleanup (blog.py `import re as _re`, dashboard.py inline datetime imports) — byte-equivalent carryovers
- F3g.6: char fixture dedup (analizes.html in 2 fixtures) — both pass, redundancy is explicit cross-assertion safety

**Reviewer verdict (PR #17):** *SHIP.* Zero MUST/SHOULD-FIX. Cycle-safety verified in practice. Byte-equivalence verified line-by-line for `_orchestrator.py` (only 2 intended diffs: `parties = _fetch_parties_page(db)` lifted into orchestrator; `render_parties` consumes `parties` positionally). `_load_wiki_profile` byte-identical in `_common.py`. Shim contract preserved (25+ test imports work). NICE-TO-HAVE: pre-existing operator log inaccuracies in `_orchestrator.py:313,316` (page-list literal, root-page count) — drift inherited from master, not F3g introduced.

**Test surface (post-F3g, F3 final):**
| Fixture | Pages | Note |
|---------|-------|------|
| 10 baseline JSON files | 417+ HTML pages | byte-identical safety net across all sub-pages |

**F3 trajectory summary (F3a → F3g):**
| Phase | PR | Master | LOC delta | Modules new |
|-------|----|----|-----|-----|
| F3a | #5 | `3d06e05` | 4250 → 3733 | _common.py + contradictions.py |
| F3-prep | #6 | `dbed1a0` | 3733 → 3699 | (leaf promotions) |
| F3b | #7 | `c97dbb5` | 3699 → 3198 | politicians.py + personas.py |
| F3c | #8 | `118b3a5` | 3198 → 3003 | parties.py |
| F3d | #9 | `b0586ad` | 3003 → 2419 | positions.py + news.py + statistika.py |
| F3e | #10 | `cba1aaf` | 2419 → 1783 | bills.py + laws.py + votes.py |
| F3g-pre | #11 | `0fd2565` | (no change) | (`_load_syntheses` CWD fix) |
| F3f.2 | #12 | `31f4c9f` | 1783 → 1536 | x.py |
| F3f.3 | #13 | `5b88e7b` | 1536 → 1187 | tensions.py + links.py |
| F3f.5 | #14 | `f88865d` | 1187 → 1031 | analyses.py + syntheses.py |
| F3f.4 | #15 | `0dcaf66` | 1031 → 772 | blog.py |
| F3f.1 | #16 | `385071c` | 772 → 558 | dashboard.py |
| **F3g** | **#17** | **`6ab0019`** | **558 → 173** | **_orchestrator.py + __init__.py canonical** |

**Total LOC reduction:** 4250 → 173 = **-4077 LOC (-96%)**. 17 src/render/* moduļi, ~85 shim symbols, 10 byte-identity fixture files, 914 tests passing.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt) (rewritten F3g closure brīdī).

---

## 2026-04-30 (agra rīta) — F3f.1: dashboard.py — F3f noslēgts

**TL;DR:** F3f.1 carve-out merged 2 commits-os PR #16: homepage hero (`index.html`) + combined `analizes.html` index izvilkti uz `src/render/dashboard.py` (293 LOC leaf). Tas ir **pēdējais F3f sub-phase** — F3f noslēgts, atlikušais F3 darbs ir tikai F3g (cycle-debt clear). `generate.py` 772 → **558 LOC** (-87% no sākotnējā 4250).

**PR #16 trajectory (2 commits + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `b249690` | test | x.json refresh + dashboard.json bootstrap + 2 F3f.1 char tests | Stale x.html baseline (data drift kopš F3f.4 merge) + jaunais F3f.1 fixture |
| `95c6fc0` | refactor | dashboard.py + generate.py | Carve-out: 4 fetcheri + render_dashboard |
| `385071c` | merge | (PR #16) | |

**Module map (post-F3f.1, 15 src/render/* moduļi):**
- F3f.1 (jauns): `dashboard.py` (293 LOC, leaf) — `_fetch_stats`, `_sparkline_svg`, `_fetch_hero_v2_data`, `_fetch_trends_data`, `render_dashboard(env, db, atmina_dir, stats, contradictions, votes, blog_posts, syntheses, analyses, trends_data, context_notes, days_until)`. Imports: `_common.{BASE_URL, PARTY_COLORS, _render_page, _slugify}` + `src.db.{today_lv, CLEAN_START_DATE}` + stdlib + extern (markupsafe.Markup, jinja2.Environment).
- Iepriekš (16 moduļi kopā ar `_common`): `_common, contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses, blog`.

**Plan deviations (1 flagged):**
1. `render_dashboard` rendere ABAS lapas — `index.html` (block #1) UN `analizes.html` (block #6). Plan paste-block to eksplicīti autorizē ("Iekļauj arī orchestrator-owned analizes.html combined index render"). Abi koplieto orchestrator-fetched data (stats, blog_posts, syntheses, analyses, trends_data, context_notes); co-locating saglabā data flow skaidrību. Reviewer verificēja byte-identitāti: analizes.html SHA `f413ff7b...` matches F3f.5 fixture.

**Pass-through args:** 12 args (3 primary + 9 data). Garākais peer (render_votes 6 args). Plan paste-block to atzina "Pass-through args list ir liels — apsveri before commit". F3g var bundle context, kad `generate_public_site` lift-osies uz `src/render/__init__.py`.

**Reviewer verdict (PR #16):** *CLEAN. Merge.* Zero MUST/SHOULD-FIX. Reviewer matemātiski verificēja `analizes.html` placement-change byte-identitāti: `env.globals["bill_slugs"]` ir set PIRMS render_dashboard izsaukuma; nekāds peer render_* nepieskaras `env.globals` post-startup; pre-fetched lists (analyses, syntheses, blog_posts) nav mutētas in-place. Char fixture cross-asserts SHA-identitāti starp F3f.5 + F3f.1 fixtures.

**Reviewer NICE-TO-HAVE → F3g checklist (added):**
- `src/generate.py` vestigial top-level imports (post-F3f.1): `import json`, `import re`, `import sqlite3`, `from datetime import datetime, timedelta, timezone`, `from markupsafe import Markup`, `now_lv_dt + CLEAN_START_DATE` no `src.db` — visi vairs nelieto. ruff F401 silenced šim failam (`pyproject.toml:50`), tāpēc check.sh paliek zaļš. F3g vestige sweep notīrīs šos kopā ar `blog.py` `import re as _re` aliases un `dashboard.py:95` inline `from datetime import` shadow.
- `_common.py:484` (now `:511`) — kompletā agent_api_inventory.txt rewrite landing F3g-ā (kanoniskais `src.render` public path).

**Test surface (post-F3f.1):**
| Fixture | Pages | Note |
|---------|-------|------|
| `render_baseline_dashboard.json` | index.html + analizes.html | F3f.1 — analizes.html SHA cross-asserted ar F3f.5 fixture |

**F3 noslēguma posms — atlicis tikai F3g:**
- Lift `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py` vai `src/render/_orchestrator.py`
- `src/generate.py` → ~30-50 LOC re-export shim
- `render_parties` self-contained (drop `parties_data` return)
- Restore `_load_wiki_profile` callsite at `politicians.py:310` (F3f.5 follow-up, dead code restoration)
- Apply F3f.3 review nice-to-haves (`_chronologize_contradiction` + `_tension_filter_axes` to `_common`)
- F3f.4 + F3f.1 vestigial alias/import cleanup
- `agent_api_inventory.txt` full rewrite (canonical `src.render` public path, ~15 modules + ~85 shim symbols)
- Char fixture dedup (analizes.html in F3f.1 + F3f.5 fixtures)
- `tests/test_generate.py` reorganize uz `tests/test_render_<page>.py` ja >1500 LOC

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (vēla nakts) — F3f.4: blog.py

**TL;DR:** F3f.4 carve-out merged 1 commit-ā PR #15: blog index (`blog.html`) + per-post pages (`blog/<slug>.html`, ~25 daily/weekly briefs) + `_fetch_blog_posts` + `_fetch_context_notes` + `_rewrite_shortener_link_labels` izvilkti uz `src/render/blog.py` (321 LOC leaf modulis). `generate.py` 1031 → **772 LOC** (-82% no sākotnējā 4250). Bonus: F3f.2 cross-ref bookkeeping iebūvēts (`parties.py:185` + `_common.py:511` tagad norāda `src/render/x.py`); F3f.5 docstring kļūda izlabota (`_parse_frontmatter` reālie patērētāji ir tikai analyses + syntheses, ne blog).

**PR #15 trajectory (1 commit + merge):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `e593f1b` | refactor | blog.py + generate.py + _common.py + parties.py + briefs.py + tests | Carve-out + F3f.2 cross-ref bookkeeping + F3f.5 docstring fix |
| `0dcaf66` | merge | (PR #15) | |

**Module map (post-F3f.4, 14 src/render/* moduļi):**
- F3f.4 (jauns): `blog.py` (321 LOC, leaf) — `_SHORTENER_CANONICAL`, `_MD_LINK_RE`, `_rewrite_shortener_link_labels`, `_fetch_context_notes`, `_fetch_blog_posts`, `render_blog`. Imports: `_common.BASE_URL` + `_render_page` + `src.briefs.strip_visual_brief_block` (no cycle — `briefs.py` importē tikai `src.db`).
- Iepriekš: `_common, contradictions, politicians, personas, parties, positions, news, statistika, bills, laws, votes, x, tensions, links, analyses, syntheses` (16 moduļi kopā ar `_common`).

**Plan deviations (4):**
1. `render_blog(env, atmina_dir, blog_posts)` — 3 args, ne 4. Plāns paredzēja `context_notes` kā 4. arg, bet `context_notes` ir tikai orchestrator-owned `analizes.html` index render consumer (NE blog rendering). Tāda pati deviācija kā F3f.5 `render_syntheses`.
2. **F3f.2 cross-ref bookkeeping iebūvēts šajā PR** (atlikts no PR #12): `parties.py:185` + `_common.py:511` komentāri tagad norāda `src/render/x.py` (post-F3f.2 location), nevis legacy `generate.py`. Plan paste-block to apstiprināja "F3f.2 follow-up bookkeeping for F3f.4 or F3g".
3. **F3f.5 docstring fix iebūvēts**: `_common.py:182-189` `_parse_frontmatter` docstring kļūdaini apgalvoja "three sub-page consumers" ar `_fetch_blog_posts` kā trešo. Patiesie consumeri ir tikai `analyses.py` (`_load_wiki_profile` + `_load_analyses`) un `syntheses.py` (`_load_syntheses`). `_fetch_blog_posts` ielasa no `context_notes` DB tabulas, NE markdown failiem — nekad neizsauc `_parse_frontmatter`. Promotion paliek pamatota (cycle avoidance), bet skaitīšana izlabota.
4. **`src/briefs.py:118`** narrative path reference no `src/generate.py:_fetch_blog_posts()` → `src/render/blog.py:_fetch_blog_posts()`.

**Reviewer verdict (PR #15):** *Clean — merge as-is.* Zero MUST-FIX, zero SHOULD-FIX. Byte-equivalence verificēta AST-līmenī (3 funkcijas: `_rewrite_shortener_link_labels` 880 chars, `_fetch_context_notes` 283 chars, `_fetch_blog_posts` 8518 chars — visas verbatim). Lint clean. Re-export shim ietur 8 lazy `from src.generate import _fetch_blog_posts` imports `tests/test_generate.py`-ā. Vienīgais NICE-TO-HAVE — `agent_api_inventory.txt` backfill F3f.5 + F3f.4 — atstāts F3g pilnam rewrite (per dd9ee4c plana checklist).

**Reviewer atklāsme:** Module-level `from src.briefs import strip_visual_brief_block` `blog.py:41` ir TĪRĀKS par iepriekšējo lazy in-loop importu `generate.py:577` — `briefs.py` importē tikai `src.db`, nekad `src.render` vai `src.generate`. Cycle-free.

**Test surface (post-F3f.4):**
| Fixture | Pages | Note |
|---------|-------|------|
| `render_baseline_blog.json` | blog.html + 25 blog/<slug>.html | Dynamic count — REGEN per blog ingest cycle (likumprojekti F3e precedents) |

**Atlikuši F3 (1 sub-fāze + final):**
- **F3f.1** dashboard.py — index.html (hero + sparklines + ticker + trends) + orchestrator-owned `analizes.html` combined index render. ⚠️ daudz pass-through args (analyses, syntheses, blog_posts, trends_data, context_notes, contradictions, votes, tensions). Sarežģītākais atlikušais.
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; restore `_load_wiki_profile` callsite (F3f.5 follow-up); apply F3f.3 review nice-to-haves; full `agent_api_inventory.txt` rewrite (canonical `src.render` public path); F3f.4 vestigial aliases cleanup (`import re as _re`, `from datetime import date as _date` blog.py-ā).

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (nakts) — F3f.5: analyses.py + syntheses.py

**TL;DR:** F3f.5 carve-out merged ar 4 commits PR #14: `analizes/<slug>.html` + `sintezes/<slug>.html` rendering izvilkts no `src/generate.py` divos leaf moduļos. `_parse_frontmatter` paaugstināts uz `_common.py` (3 sub-page consumers — F3-prep promotion rule). Trīs vakara sesijā stale char fixtures atjaunoti REGEN baseline darbībā kā atsevišķs commit pirms refaktoringa. `generate.py` 1187 → **1031 LOC** (-76% no sākotnējā 4250).

**PR #14 trajectory (4 commits):**
| Commit | Type | Files | Notes |
|--------|------|-------|-------|
| `6cdd788` | test | 5 char fixtures + tests | REGEN refresh (contradictions/graph/politicians stale) + bootstrap render_baseline_analyses.json + 3 jauni F3f.5 char tests |
| `322763d` | refactor | analyses.py + syntheses.py + _common.py + generate.py + test_load_syntheses.py | Carve-out + _parse_frontmatter promotion + shim + orchestrator wiring |
| `dd9ee4c` | docs(plan) | refactor-plan-2026-04-29.md | Review nits — fix render_syntheses signature (3 args, not 4) + ticket _load_wiki_profile follow-up |
| `f88865d` | merge | (PR #14) | |

**Module map (post-F3f.5, 13 src/render/* moduļi):**
- `_common.py` (771 LOC, leaf) — paaugstināts ar `_parse_frontmatter` (yaml frontmatter parser, 3 consumers).
- **F3f.5 (jauni):** `analyses.py` (120 LOC, leaf) — `_load_wiki_profile`, `_load_analyses`, `render_analyses`. `syntheses.py` (126 LOC, leaf) — `_load_syntheses` (worktree-portable post-F3g-pre), `_map_syntheses_to_politicians`, `render_syntheses`.
- F3a-F3e + F3f.2 + F3f.3 (iepriekš): `contradictions/politicians/personas/parties/positions/news/statistika/bills/laws/votes/x/tensions/links` (no izmaiņām).

**Plan deviations (4):**
1. `_parse_frontmatter` → `_common.py` (3 sub-page consumers: `analyses.py`, `syntheses.py`, `generate.py:_fetch_blog_posts` F3f.4). Avoids reverse `from src.generate import _parse_frontmatter` cycle.
2. Char fixture iekļauj `analizes.html` (orchestrator-owned combined index) papildus per-page baselines — sanity check, ka jaunie loaders neizmaina datu formu.
3. `_load_wiki_profile` ir **dead code** post-F3b (PR #7) — `src/render/politicians.py:310` hardcodes `wiki_profile = None`. Funkcija tomēr pārvietota uz `analyses.py` per plāns; restoration ticketed F3g (sk. plāna §F3g checklist).
4. `tests/test_load_syntheses.py` import atjaunots uz `src.render.syntheses` direktais ceļš (F3-prep convention).

**Stale char baseline refresh (commit 1):** `bash scripts/check.sh` master pirms PR #14 = 903 passed + **4 failed** (contradictions, politicians, graph fixtures driftēja kopš 22:00 deploy/auto-sync — DB content drifts no jaunām claims/contradictions). Refresh + jaunais F3f.5 baseline → **910 passed**, 2 xfailed, 1 xpassed. Precedents: commit `3064541` "fix(test): refresh stale politicians baseline".

**Reviewer verdict (PR #14):** *Clean. Ready to merge.* Zero MUST-FIX, zero SHOULD-FIX. Divi NICE-TO-HAVE atlikti F3g (agent_api_inventory status header refresh + _load_wiki_profile restoration ticket — pēdējais ievietots dd9ee4c plānā). Byte-equivalence verificēta line-by-line, shim contract pilnīgs (6 simboli + paaugstinātais `_parse_frontmatter` re-eksportēti).

**Atlikuši F3 (3 sub-fāzes + final):**
- **F3f.4** blog.py — `_fetch_blog_posts` + `_fetch_context_notes` + `_rewrite_shortener_link_labels` (single callsite). Char fixture REGEN pēc katras blog ingest darbības.
- **F3f.1** dashboard.py — index.html (hero/sparklines/ticker/trends), grūtākais (daudz pass-through args).
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; agent inventory → src.render kanoniskais ceļš; `_load_wiki_profile` restoration callsite + potential promote uz `_common.py`.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md).

---

## 2026-04-29 (vakars) — F3g-pre + F3f.2 + F3f.3 + matcher patterns

**TL;DR:** Trīs PR mergēti vienā vakara sesijā pēc dienas rutīnas. `_load_syntheses` CWD-atkarības bug atrisināts pie saknēm (F3g-pre, PR #11). x.html (F3f.2, PR #12) un spriedzes.html + saites.html (F3f.3, PR #13) carve-outs uz `src/render/`. 4 matcher false positives no šodienas analīzes papildināti ar `negative_patterns`. `generate.py` 1783 → **1187 LOC** (-72% no sākotnējā 4250).

**PR shipped trajectory (vakara sesija):**
| PR | Phase | Commit | LOC delta | Char tests | Modules |
|----|-------|--------|-----------|------------|---------|
| #11 | F3g-pre | `0fd2565` | (no change) | +3 unit tests | `_load_syntheses(atmina_dir)` signature change + 3 baselines regen |
| #12 | F3f.2 | `31f4c9f` | 1783→1536 | +1 char | `x.py` (285 LOC) |
| #13 | F3f.3 | `5b88e7b` | 1536→1187 | +2 char | `tensions.py` (62), `links.py` (360) |

**F3g-pre (PR #11) — `_load_syntheses` output_dir-relative:**
- Threads `atmina_dir` through `_load_syntheses(atmina_dir = Path("output/atmina"))` so the synthesis-image existence check resolves relative to the explicit output dir, not CWD. Default arg preserves production behavior.
- Char baselines regen captured both the synthesis fix (10 politician hashes flip from has_image=True → False) and unrelated content drift accumulated since F3d (~50 hashes from claims/contradictions/votes added between commits `3d8ed1e..f493dd8`). Both are canonical-state correct.
- 3 unit tests (`tests/test_load_syntheses.py`) lock down the path-resolution invariant — atmina_dir lookup, empty atmina_dir, default-arg CWD-relative under `monkeypatch.chdir`.
- Closes pre-F3e CWD-atkarības drift root cause; previous reactive baseline patch (`3064541`) is now superseded by the structural fix.

**F3f.2 (PR #12) — `x.py` (Twitter/X feed page):**
- `_fetch_x_data(db)` + `render_x(env, db, atmina_dir)` self-contained orchestrator. Re-export shim widens by 2 names; 11 test_generate.py tests directly import `_fetch_x_data` (V1 metrics suite).
- Char fixture: `render_baseline_x.json` (single page hash). Byte-identity preserved.
- Cleanup nit: `%`-style SQL placeholder formatting → f-string + extracted `placeholders` local. New module isn't on UP031 per-file-ignore (and shouldn't be).
- Plan deviation: `_rewrite_shortener_link_labels` was plan-listed for x.py but has only 1 callsite (`_fetch_blog_posts:859`) — moves with F3f.4 (blog.py), not F3f.2. Plan task description updated.

**F3f.3 (PR #13) — `tensions.py` + `links.py` (1 PR, 2 leaf modules):**
- `tensions.py` (62 LOC): `_fetch_tensions(db)` + `render_tensions(env, db, atmina_dir, tensions)` → spriedzes.html.
- `links.py` (360 LOC): `_fetch_graph_data(db)` + `render_links(env, db, atmina_dir, tensions)` → saites.html with full inline orchestration absorbed (claims_by_pid, contras_by_pid, votes_by_pid payloads, ~140 LOC pulled out of `generate_public_site`).
- Pass-through `tensions` arg matches F3a (`render_contradictions`) and F3e (`render_votes`) precedents — orchestrator pre-fetches data shared by 2+ sub-pages.
- Char fixture: `render_baseline_graph.json` (both pages SHA-256 in one file). Reviewer renamed from plan's suggested `misc2.json` for semantic clarity.
- Cleanup nit: compact `a = x; b = y` semicolon pattern (E702) in contradiction-swap logic → one-statement-per-line. New modules pass full lint without per-file-ignore.
- F3g-deferred TODOs (from PR #13 review): extract `_chronologize_contradiction(row, key_pairs)` to `_common` (3 duplicates: `links.py`, `_common._enrich_contradiction`, `social_agent/candidates.py:93`); extract `_tension_filter_axes(tensions) -> dict` to `_common` (2 duplicates: tensions.py, links.py).

**Module map (post-F3f.3):**
- 12 → 14 moduļi `src/render/`. New: `x.py`, `tensions.py`, `links.py`.
- All 14 modules import only from `src.render._common` and stdlib + `src.db`/`src.coalition` (lazy). Zero peer sub-page edges. F4 leaf-vs-fan-out discipline preserved.

**Baseline post-F3f.3:** 7 char fixture files (`render_baseline_contradictions/politicians/parties/misc/bills/laws/x/graph.json`) covering 388 byte-identical pages. `bash scripts/check.sh` exit 0 = **907 passed** (905 pre-PR-#13 + 2 new char tests), 2 xfailed (pre-existing), 1 xpassed.

**Matcher negative_patterns sweep (post-rutīna):**
4 pol false positives surfaced by today's claim extraction were patched directly in DB (auto-applied next ingest cycle, matcher cache reloaded on first call):
- pid=182 (Otto Ozols, journalist) ← `Ozols un Instrumenti`, `ansis`, `Gustavo, ansis`, `Rīgas 825` (musician collision; TVNet Riga 825-anniversary concert)
- pid=101 (Inese Kalniņa, JV) ← `Mārīte Tabita`, `Nejaucēni`, `Bērnu, jauniešu un vecāku žūrij` (children's-book author collision; LETA LNB Bērnu žūrija)
- pid=64 (Guntars Vītols, neutral) ← `Jāzeps Vītols`, `Jāzepa Vītol`, `Edgars Vītols`, `Edgara Vītol`, `Virsdiriģentu svētk` (composer collisions; LETA Virsdiriģentu svētki)

LTV Ziņas (pid=170, journalist/relay account, `social_accounts.feed_type='relay'`) discussed but not modified — strukturāls jautājums (relay konts dzīvo `tracked_politicians` jo `social_accounts.opponent_id` FK), atstāts pagaidu plākstera režīmā ar esošām patterns `plašsaziņas`, `360 ziņas`. Atsevišķa `relay_accounts` tabula būtu tīrāka, bet tas ir lielāks migrāciju darbs.

**Atlikuši F3 (4 sub-fāzes + final):**
- **F3f.5** analyses.py + syntheses.py — tagad CWD-bug-free pateicoties F3g-pre (recommended next).
- **F3f.4** blog.py — `_fetch_blog_posts` + `_fetch_context_notes` + `_parse_frontmatter` + `_rewrite_shortener_link_labels` (single callsite). Char fixture REGEN pēc katras blog ingest darbības.
- **F3f.1** dashboard.py — index.html (hero/sparklines/ticker/trends), grūtākais (daudz pass-through args).
- **F3g** orchestrator lift (final F3 step): `generate_public_site` + `_generate_sitemap` + `_generate_og_image` → `src/render/__init__.py`; `src/generate.py` <50 LOC; `render_parties` self-contained; agent inventory → src.render kanoniskais ceļš.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 3 (F3a-F3e): `src/generate.py` → `src/render/` pakete

**TL;DR:** 4250 LOC monolīts `src/generate.py` sadalīts daudzmoduļu paketē piecos sub-phase posmos vienā dienā. Pēc F3e generate.py = 1783 LOC (-58%); 10 jauni `src/render/*.py` moduļi + 745 LOC `_common.py` leaf. Aģentu API stabils — `from src.generate import …` turpina darboties bez izmaiņām, jo top-level imports re-eksportē visus pārvietotos simbolus (66+ vārdi). Atlikušas F3f-F3g: dashboard/x/blog/analyses, cycle-debt clear.

**Sub-phase trajectory:**
| Phase | PR | Commit | LOC delta | Char tests | Modules |
|-------|----|----|-----|-----|---------|
| F3a | #5 | `3d06e05` | 4250→3733 | +2 | `_common.py` (469), `contradictions.py` (177) |
| F3-prep | #6 | `dbed1a0` | 3733→3699 | 0 | (no new modules; helper promotions + char-fixture stability) |
| F3b | #7 | `c97dbb5` | 3699→3198 | +2 | `politicians.py` (333), `personas.py` (135) |
| F3c | #8 | `118b3a5` | 3198→3003 | +2 | `parties.py` (250) |
| F3d | #9 | `b0586ad` | 3003→2419 | +4 | `positions.py` (227), `news.py` (158), `statistika.py` (305) |
| baseline-fix | — | `3064541` | 2419→2413 | 0 | (no new modules; tests/fixtures/render_baseline_politicians.json regen — 10 stale hashes from CWD-relative `_load_syntheses` image lookup; pre-flight cleanup before F3e) |
| F3e | #10 | `cba1aaf` | 2413→1783 | +4 | `bills.py` (203), `laws.py` (186), `votes.py` (382) |

**Moduļu shēma (post-F3d):**
- `src/render/_common.py` (745 LOC) — leaf: konstantes (`BASE_URL`, `PARTY_COLORS`, `SEVERITY_LV`, `CATEGORY_LV`, `CLAIM_TYPE_LABEL`, `_SEVERITY_GLYPHS`, `PZV1_TOPIC_COLORS` apzināti _common-ā **NĒ** — paliek `positions.py`-ā kā page-specific palette, ASSETS_DIR, ELECTION_DATE, _LV_TRANS, _LV_OFFSET_HOURS, _PARTY_LOWERCASE_WORDS, path roots), drošības filtri (`_sanitize_html`, `_safe_json_filter`, `_safe_url_filter`, `_autolink_bills_filter`), slug/format helperi (`_slugify`, `_party_short_name`, `_persona_category`, `_confidence_tier`, `_initials_from_name`, `_delta_days`, `_domain_from_url`, `_split_summary`, `_latvian_quotes`, `_photo_data_uri`, `_normalize_date`, `_date_sort_key`, `_format_tweet_time`, `_titlecase_party_name`), cross-page domain (`_source_to_internal_link`, `_enrich_contradiction`, `_bill_slug`, `_get_last_activity`), asset helperi (`_resolve_assets_version`, `_download_chart_js`, `_download_annotation_plugin`), page primitive (`_render_page`)
- `src/render/contradictions.py` (177 LOC) — F3a: `_fetch_contradictions`, `_render_og_cards`, `render_contradictions`
- `src/render/politicians.py` (333 LOC) — F3b: `_fetch_politicians`, `_fetch_commentary_about`, `_fetch_politician_detail`, `render_politicians`
- `src/render/personas.py` (135 LOC) — F3b: `_fetch_personas`, `_fetch_personas_metrics`, `render_personas` (self-contained)
- `src/render/parties.py` (250 LOC) — F3c: `_fetch_parties_page`, `_fetch_party_detail`, `render_parties` (returns parties_data — sitemap dependency, resolves at F3g)
- `src/render/positions.py` (227 LOC) — F3d: `_fetch_claims`, `_fetch_pozicijas_metrics`, `PZV1_TOPIC_COLORS`, `render_positions` (writes pozicijas.html + pozicijas-data.json + .br + .gz)
- `src/render/news.py` (158 LOC) — F3d: `_fetch_news`, `render_news` (self-contained)
- `src/render/statistika.py` (305 LOC) — F3d: `generate_statistika` STANDALONE entrypoint (NOT in generate_public_site flow; called manually after monthly CSP data sync)
- `src/render/bills.py` (203 LOC) — F3e: `_LAW_TITLES_CACHE`, `_get_law_titles`, `_fetch_bills`, `_fetch_bill_detail`, `_generate_bill_pages`, `render_bills(env, db, atmina_dir) -> int`. Emits ~151 likumprojekti/<slug>.html. `_get_law_titles` co-located with bills (only consumer is `_fetch_bill_detail` for `base_law_title`).
- `src/render/laws.py` (186 LOC) — F3e: `_LAW_LIKUMI_LV_RE`, `_LAW_BODY_STRIP_RE`, `_fetch_law_pages`, `_generate_law_pages`, `_fetch_law_index_page`, `render_laws(env, db, atmina_dir) -> int`. Emits likumi.html + ~33 likumi/<slug>.html. Returns `laws_index_count` for the balsojumi.html footer (F3a `all_parties` / F3c `parties_data` pass-through pattern).
- `src/render/votes.py` (382 LOC) — F3e: `_enrich_faction_breakdown` (pure, 8 unit tests), `_fetch_votes`, `_build_matrix_data`, `render_votes(env, db, atmina_dir, votes, bills, laws_index_count) -> None`. Emits balsojumi.html. Folds in vote_metrics, vote_sessions, deputies, matrix_data computation that was previously inline in generate_public_site (~50 LOC orchestrator delta).

**Cikla pārvaldība:** Visi sub-page moduļi importē TIKAI no `_common`, nekad savā starpā. F4 leaf-vs-fan-out disciplīna stingri saglabāta. Helper promotions notika 2 reizes pirms peer sub-page izveidošanas (F3-prep promovēja 4 leaf helperus + 2 const F3b/F3c/F3d nepieciešamībām; F3b promovēja `_bill_slug` + `_get_last_activity` peer sub-page sharing dēļ; F3d promovēja `_download_chart_js` + `_download_annotation_plugin` cycle-avoidance dēļ).

**F3a tehniskais parāds (atstāts F3g atrisināt):** `src/render/__init__.py` apzināti NEEKSPONĒ `generate_public_site`, jo `generate.py → render._common → render.__init__ → generate` cikls. F3g uzdevums: pārvieto `generate_public_site` uz `__init__.py`, atjaunina `generate.py` uz pilnu re-export shim, atjaunina inventāriju.

**Char-fixture pattern (`tests/test_render_chars.py`):** Session-scoped fixture izsauc `generate_public_site(output_dir=tmp)` + `generate_statistika(output_dir=tmp)` reizi par sesiju, hash-o target HTML pages, assert pret iesaldēto baseline. `ATMINA_ASSETS_VERSION="test"` env override (no F3-prep) izvairās no `?v=` cache-bust drift fresh worktree-ā. `REGEN=1 pytest` bootstraps baseline; bare run assert. Pieci baseline JSON failos:
- `render_baseline_contradictions.json` — pretrunas.html + 12 detail
- `render_baseline_politicians.json` — personas.html + 159 politiki/<slug>.html
- `render_baseline_parties.json` — partijas.html + 15 partijas/<short>.html
- `render_baseline_misc.json` — pozicijas.html + zinas.html + statistika.html + 10 statistika/<id>.html
- `render_baseline_bills.json` — balsojumi.html + ~151 likumprojekti/<slug>.html (F3e)
- `render_baseline_laws.json` — likumi.html + ~33 likumi/<slug>.html (F3e)

385 byte-identical pages kopā post-F3e (200 pre-F3e + 185 jauni). Adds ~30s vienu reizi pytest-am (session fixture amortizācija).

**Strukturālās mācības:**
1. **"Viens shim pietiek" no plāna sākotnējā teksta bija NEPILNĪGA** — testu suite (`tests/test_generate.py`, `test_personas_v2.py`, `test_pozicijas_v2.py`, `test_phase_1b_ii.py`, `test_generate_bills.py`, `test_likumi_index.py`, `test_autolink_bills.py`) tieši importē ~32 privātos `_fetch_*` / `_safe_*` / `_persona_category` / `PARTY_COLORS` simbolus no `src.generate`. Re-export shim ir plats, ne šaurs. Pieņemts kā migrācijas-window stratēģija; F3g atrisinās.
2. **`src/render/__init__.py` cycle** — sub-page imports trigger paketes `__init__.py`, kas, ja eksponē `generate_public_site` (kurš pats importē no `_common`), rada importēšanas ciklu. Pieņemts apzināti — F3g lift atrisinās.
3. **F4 leaf-vs-fan-out disciplīna pārnests F3-am perfekti.** Visi sub-page moduļi ir `_common`-leaves. F3-prep + F3b proaktīvas leaf promocijas pirms peer sub-page izveidošanas izvairījās no jebkura cikla F3b-F3d laikā.
4. **Char-fixture cumulatīvs noslēgums.** F3a → 2 tests; F3b → +2; F3c → +2; F3d → +4. Visi vienā fixture-failā ar viena session run-a per pytest. Pattern reusable F3e/F3f.
5. **`render_*` orchestrator signatures vary by data-flow:** self-contained (`render_personas`, `render_news`, `render_positions`) re-fetch internally jo data nav reused downstream; pass-through (`render_contradictions`, `render_politicians`, `render_parties`) saņem pre-computed data un, kur nepieciešams, atgriež to atpakaļ caller-am sitemap vajadzībām.

**Verifikācija:** `bash scripts/check.sh` exit 0 pēc katra commit. 887 (pre-F3a) → 897 (post-F3d) → 901 (post-F3e) passed = +14 char tests; 2 xfailed (pre-existing), 1 xpassed.

**F3e-specifiskās mācības:**
1. **Pre-F3e baseline drift atklāja slēptu CWD-atkarību.** `_load_syntheses` (src/generate.py:1656) lasa synthesis attēlus no CWD-relatīva `output/atmina/images/synthesis/` ceļa. Main worktree ir attēli no agrākiem render-iem; fresh worktree → `has_image=False` → 10 politiķu detail page nesatur synthesis `<img>` tag → hash drift. Fix landed kā 3064541 (regen baseline). **F3g/postlude TODO:** `_load_syntheses` jāpārtaisa, lai lasa images relative to render `output_dir` arg, ne CWD. Līdz tam F3 byte-identity invariants ir worktree-portability hidden bug — fresh worktree-ā char tests fails, līdz `cp output/atmina/images/synthesis/* worktree/...` mirror.
2. **`render_votes` signature deviation no plāna.** Plāns paredzēja `(vote_topics, deputies_list)` pass-through; reālā implementācija ir `(votes, bills, laws_index_count)`, jo `vote_topics`/`deputies`/`vote_sessions`/`matrix_data`/`vote_metrics`/`bill_topics` ir deterministic derivations no `votes`/`bills`. Iekšā render_votes-ā = mazāks signature, single source of truth. Pass-through pattern atbilst F3a (`all_parties`) un F3c (`parties_data`) precedentiem. `votes` un `bills` jau tāpat tiek pre-fetched generate_public_site-ā index page (`recent_votes`) un `env.globals["bill_slugs"]` autolink vajadzībām.
3. **`_get_law_titles` co-located ar bills.py, ne laws.py** — vienīgais konsumers ir `_fetch_bill_detail` (`base_law_title` lookup). Co-location ar consumer ļauj laws.py palikt leaf-clean.
4. **F3e review nits same-PR sweep (commit `abce764`)** — F3d's `b6b196a` šablons turpinās: dead `LAW_TITLE_RE` import + unused `bill_count` capture. Ruff F401/F841 ir per-file-ignored generate.py-ā, tāpēc abi nav auto-flagged; manuāli sweep katra extraction-a beigās.

Plāns: [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Aģentu API inventarizācija: [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 4: `src/saeima.py` → `src/saeima/` pakete

**TL;DR:** 1425 LOC monolīts `src/saeima.py` sadalīts piecu moduļu paketē. Aģentu API stabils — `from src.saeima import …` turpina darboties bez izmaiņām, jo `__init__.py` re-eksportē visus 28 ārēji-importētos simbolus.

**Moduļu shēma:**
- `src/saeima/schema.py` — `init_saeima_tables`, `init_saeima_bills` (DDL paliek Python pusē, ne `src/schema.sql`, jo `init_saeima_bills` lieto conditional `ALTER TABLE` pattern, ko sqlite < 3.35 neatbalsta)
- `src/saeima/bills.py` — `_VALID_BILL_TYPES`/`_VALID_STAGE_NAMES`, motif regexes, `resolve_bill_from_motif`, `_reading_from_motif`, `_resolve_base_law_slug`, `LAW_TITLE_RE`, `load_laws_index`, `_canonicalize_stage_name`, `upsert_bill`, `append_bill_stage`, `AgendaBill`, `SAEIMA_BASE_URL`, `_resolve_vote_url`, `_parse_vote_datetime` (leaf — nav saeima/ iekšējo importu)
- `src/saeima/parsing.py` — `parse_agenda_snapshot` + 3 helperi + agenda regexes (importē `AgendaBill` no bills)
- `src/saeima/claims.py` — `_stem`, `_word`, `_MOTIF_TOPIC_MAP`, `_motif_to_topic`, `_vote_salience` (leaf — pure topic mapping)
- `src/saeima/votes.py` — `IndividualVote`/`VoteResult`, `parse_vote_snapshot`, `_build_name_index`, `match_deputies_to_politicians`, `match_submitters_to_politicians`, `store_vote`, `generate_claims_from_votes`, `process_vote_snapshot` (depends on bills + claims)

**Cikla pārvaldība:** bills + claims ir leaf moduļi (nav saeima/ iekšējo importu). votes ir vienīgais ar fan-out uz abiem. parsing importē tikai no bills.

**Deviations no sākotnējā plāna (4):**
1. `parse_vote_snapshot` glabājas `votes.py` (ne `parsing.py`) — izvairās no `parsing → votes` cikla pār `VoteResult` import
2. `match_submitters_to_politicians` glabājas `votes.py` (ne `bills.py`) — koplieto `_build_name_index` ar siblinga `match_deputies_to_politicians`
3. `generate_claims_from_votes` glabājas `votes.py` (ne `claims.py`) — claims.py paliek tīrs leaf-modulis
4. `SAEIMA_BASE_URL` + `_resolve_vote_url` + `_parse_vote_datetime` — `bills.py` (ne savs `_helpers.py`) — koplietojami starp votes + claims, glabājami leaf modulī

**Strukturālā mācība:** Plāna sākotnējais 5-moduļu shēma (schema/parsing/votes/bills/claims pa funkcionālo lomu) bija circular pa runtime imports — `VoteResult` plūsma starp parsing/votes un `_motif_to_topic` plūsma starp votes/claims radītu `from src.saeima.X import Y`-stila ciklus. Risinājums bija nedaudz pārorganizēt pa "leaf vs fan-out" loģiku, ne pa stingru funkcionālo dalījumu. F3 (`generate.py` → `src/render/`) vajadzētu paredzēt to pašu — sub-pages sākotnēji izskatās kā independent moduļi, bet kopēji helperi (Jinja env, sanitization filtri, URL parties) parasti rada lasošo cikla risku.

**Pirmsdarbi (F4.0, commit `d92164f`):**
- `tests/fixtures/saeima_chars_expected.json` — frozen baseline (63KB, 19 motifu × 3 funkciju + 1 agenda + 3 vote snapshot output-i)
- `tests/test_saeima_chars.py` — 3 asserting tests; `REGEN=1` env regenerē baseline, ja uzvedība intentionally mainās
- `tests/fixtures/saeima_snapshots/` — 4 reāli Playwright snapshot faili no 2026-04-16 sesijas

**Pakešu skelets (F4.1, commit `0f3f273`):**
- `git mv src/saeima.py src/saeima_legacy.py`
- `mkdir src/saeima` + `__init__.py` ar 25 simbolu re-eksportu no legacy
- `pyproject.toml` ruff per-file-ignores atjaunina (saeima.py → saeima_legacy.py + saeima/*.py)

**Schema izvilkšana (F4.2, commit `89d9000`):**
- `init_saeima_tables` + `init_saeima_bills` pārvietoti uz `src/saeima/schema.py`
- `__init__.py` importē tos no `.schema` (ne legacy)

**Atomic split (F4.3+F4.4, commit `11ca874`):**
- 4 jauni moduļi (`bills.py`, `parsing.py`, `claims.py`, `votes.py`) + final `__init__.py`
- `src/saeima_legacy.py` izdzēsts (`git rm`)
- 28 simboli eksponēti caur `__init__.py.__all__`

**Iekšējo callsites + path references atjauninājums (F4.5):**
- `.claude/agents/saeima-tracker.md` — path reference `src/saeima.py:_parse_institutional_submitter` → `src/saeima/parsing.py:_parse_institutional_submitter`
- `wiki/operations/saeima-bills.md` — 3 path references atjaunināti uz pakešu sub-modules
- `src/db.py` — 2 narrative comment references atjaunināti

**Verifikācija:**
- `bash scripts/check.sh` exit 0 pēc katra commit
- 887 passed (884 pre-F4 baseline + 3 jauni char tests), 2 xfailed (pre-existing), 1 xpassed
- `generate_public_site` smoke clean — 159 politicians, 24 blog posts, 12 pretrunas pages
- Manual import smoke: visi 28 publiskie simboli importējami no `src.saeima` top-level

**Out of scope (atstāts vēlākām fāzēm):**
- Fāze 3 — `src/generate.py` (4250 LOC) → `src/render/` pakete pa lapu grupām
- Fāze 5 — `migrations/` formāts (atlikt līdz nākamai DDL izmaiņai)

Skat. plānu [docs/plans/refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md), agent API inventarizāciju [docs/refactor/agent_api_inventory.txt](../docs/refactor/agent_api_inventory.txt).

## 2026-04-29 — Refaktoringa Fāze 0+1+2: drošības tīkls + matcher + schema.sql

**TL;DR:** Pirmie trīs soļi no [refactor-plan-2026-04-29.md](../docs/plans/refactor-plan-2026-04-29.md). Politiķu name-matching kods (≈530 LOC) izvilkts no `src/ingest.py` uz dedicētu `src/matcher.py` moduli, un statiskā DDL (≈340 LOC) izvilkta no `src/db.py::init_db()` uz `src/schema.sql`. Aģentu API stabils — re-export shim glabājas `src/ingest.py`, lai `from src.ingest import match_politicians` u.c. turpina strādāt bez churn.

**Fāze 0 — Drošības tīkls (PR #1, commit b0f9871):**
- `pyproject.toml` ar ruff + pytest config; ruff exit 0 ar dokumentētu accept-list `[tool.ruff.lint.per-file-ignores]`
- `scripts/check.sh` — 3 soļu gate (ruff → pytest → generate_public_site smoke); `set -e` abortē jaunās neveiksmes
- `tests/test_invariants.py` — 7 līgumu smoke testi (CLAUDE.md punkti 2,3,4,5,6,9,11)
- `tests/conftest.py` — `collect_ignore_glob` optional ML deps + `_BASELINE_XFAIL` 3 zināmiem pre-existing fails (matplotlib jau xpassed)

**Fāze 1 — Matcher izvilkšana (PR #2, commit 4f4d25d):**
- `src/matcher.py` (NEW, ~580 LOC) ar 12 funkcijām: `extract_twitter_author_handle`, `match_politicians/match_politician`, `link_politicians_to_documents`, `assign_unmatched_documents`, `_load_politician_forms`, `_latvian_surname_inflections`, `_surname_has_person_context`, `_disambiguate_shared_surname`, `_init_surname_disambiguation`, `_match_politician_from_url`, `_clear_politician_cache`. Module state (caches): `_politician_forms_cache`, `_shared_surname_set`, `_SURNAME_DISAMBIGUATION`, `_COMMON_WORD_FORMS`, `_PERSON_CONTEXT_BEFORE/AFTER`, `_ROLE_PRIORITY`.
- `src/ingest.py` re-export shim glabājas — 10 simboli (5 publiskie + 5 privāti tests-only). `.claude/agents/*.md` un legacy skripti importē caur shim bez izmaiņām.
- 5 internal callers updated tieši uz `src.matcher` (4 audit/fix scripts + `src/social.py`).
- `tests/test_matcher.py` + `tests/fixtures/matcher_docs.json` — 12 curated characterization cases + 4 URL parser cases. Sedz: explicit fullname, two-politicians, surname collision (Hermanis bare + Jānis/Alvis variants), Latvian inflection (Siliņa→Siliņas), 2 negative_pattern fires (Bērziņš), foreign-firstname guards (Krists Kalniņš, Tomass Alens), common-word guard (Krasta iela), empty match, multiword surname (Linda Abu Meri).
- `tests/test_ingest.py::tmp_db` un 2 audit-test fixtures atjauninātas — patches `src.matcher.get_db` un izsauc `_clear_politician_cache()` (iepriekš rakstīja phantom attrs uz `src.ingest`).

**Fāze 2 — schema.sql izvilkšana (PR #3, commit 94466aa):**
- `src/schema.sql` (NEW, 340 LOC) ar 21 CREATE TABLE + ~25 INDEX + 3 PRAGMA. Statiskā DDL ar `CREATE … IF NOT EXISTS`.
- `src/db.py::init_db()` tagad: load sqlite-vec → `executescript(schema.sql)` → 2 vec0 `CREATE VIRTUAL TABLE` (Python-side carve-out, sk. zemāk) → 6 conditional ALTER TABLE migrāciju bloki (PRAGMA-driven, sqlite < 3.35 nav `ALTER TABLE ADD COLUMN IF NOT EXISTS`).
- `tests/test_schema.py` (3 testi): roster check, idempotent re-init, whitespace-normalized DDL diff vs `docs/refactor/schema-dump-pre-f2.sql` (65 stmt baseline).

**Carve-out: vec0 virtual tables paliek Python.** `tests/test_knab.py::_SafeConnection` mocko `sqlite_vec` CI vidēm bez native extension. Tā intercepto `.execute()` zvanus, kas satur `"vec0"`, bet NEvelk `.executescript()`. Tāpēc `CREATE VIRTUAL TABLE … USING vec0(…)` glabājas atsevišķi `db.execute()` zvanos `init_db()`, ne `schema.sql`. Komentāri ABĀS vietās: `src/schema.sql` apakšā un inline `src/db.py::init_db()`.

**Carve-out: brief_images + external_profiles paliek Python migrācijas blokos.** Tās tika pievienotas vēlu (2026-04-17 featured images, 2026-04-25 external_profiles); F2 negrozījās tās promote-ot uz `schema.sql`, lai turētu pārvietošanu šauru. `EXPECTED_TABLES` set `tests/test_schema.py` ietver šīs tabulas.

**Verifikācija:**
- F0: `bash scripts/check.sh` exit 0 — 865 passed (859 master + 7 invariants − 1 bonusa cleanup), 2 xfailed, 1 xpassed
- F1: 881 passed (865 + 16 jauni test_matcher cases), 2 xfailed, 1 xpassed
- F2: 884 passed (881 + 3 schema tests), 2 xfailed, 1 xpassed
- Pre-existing 3 baseline failures NAV pasliktinātas; matplotlib XPASS (uzstādīts kāds cits commit), social_agent + relay-author downgrade joprojām xfail (atsevišķi tracked)

**Code review:** PR #2 un PR #3 caur `superpowers:code-reviewer` aģentu; abos verdikts "Ready to merge" ar 0 kritisku/should-fix punktu un mazām nit korekcijām pirms merge.

**Out of scope (atstāts vēlākām fāzēm):**
- Fāze 3 — `src/generate.py` (4250 LOC) → `src/render/` pakete pa lapu grupām
- Fāze 4 — `src/saeima.py` (1425 LOC) → `src/saeima/` pakete (5 moduļi)
- Fāze 5 — `migrations/` formāts (atlikt līdz nākamai DDL izmaiņai)
- F3 un F4 ir savstarpēji neatkarīgi; var izpildīt jebkurā secībā

Skat. plānu `docs/plans/refactor-plan-2026-04-29.md`, baseline `docs/refactor/baseline-2026-04-29.md`, agent API inventarizāciju `docs/refactor/agent_api_inventory.txt`, schema baseline `docs/refactor/schema-dump-pre-f2.sql`.

## 2026-04-29 — X mentions: pivot uz `UserTweets` timeline-scan (SearchTimeline TID strict-validation 404)

**Simptoms:** Visiem 6 cookie slotiem `search_tweet` (mentions) un `get_user_tweets(uid, 'Replies')` 2026-04-29 sāka atgriezt `404 NotFound` ar empty body. `UserTweets` un `UserByScreenName` joprojām strādāja.

**Root cause:** X selektīvi pastiprināja `x-client-transaction-id` validāciju. Patch 4 (2026-04-28) stub TID strādā tikai uz lenient endpoints; `SearchTimeline` un `UserTweetsAndReplies` to noraida. Apstiprināts ar hardcoded browser TID — endpoint atbild 200 OK uzreiz.

**Risinājums (Phase B):** `src/x_mentions.py` pārstrādāts no OR-batched `search_tweet` strategy uz **per-politician `UserTweets` timeline scan + tekstuāls `@mention` filter**. `DEFAULT_BATCH_SIZE` izņemts no API; `total_queries` `social.py` skaitās kā `len(handle_to_pid)`. 7 jauni unit tests `tests/test_x_mentions.py` fiksē invariantu, ka `search_tweet` vairs **netiek izsaukts**.

**Trade-off:** Mentions FROM untracked autoriem (žurnālisti, neaktivi politiķi) vairs netiek savākti. Tracked-to-tracked interakcijas — pretrunu signāla pamats — saglabājas pilnībā. Replies produkts kodā netika lietots, tāpēc nav blast-radius.

**Diagnostika:** `scripts/probe_x_cookies.py` paplašināts uz visiem 4 endpoint-iem per slot (`get_user`, `user_tweets`, `user_replies`, `search_tweet`). Nākamajai drift detection būs agrīna.

**Long-term TODO:** Reverse-engineer modern X TID generator (indices pārvietojušies no `ondemand.s.*a.js` uz iekšēju webpack chunk). Kad TID būs derīgs, twikit `search_tweet` un `Replies` atkal strādās bez koda izmaiņām.

Skat. plānu `docs/superpowers/plans/archive/2026-04-29-twikit-mentions-replies-404-fix.md` un `wiki/operations/twikit-notes.md` § 2026-04-29.

## 2026-04-28 — Video ingest pipeline (platform='video', timestamp source_url anchor)

Pievienots ceturtais satura kanāls — latviešu video debates un intervijas. `documents.platform='video'` jauna vērtība (bez schema migrācijas, kolonna jau ir TEXT). Implementācija: `src/video_ingest/` Python pakotne (yt-dlp + faster-whisper large-v3 INT8 + pyannote 3.1) + `@video-extractor` aģents. Operators iedod video URL vai lokālu failu → 4-fāzu plūsma (fetch → manuāla speaker mapping → finalize → extract-claims).

**Datu modeļa:**
- `documents.platform='video'` — viens row per video ar full speaker-labelled transkriptu
- `claim_type='position'` (saglabājas) — video pozīcijas plūst caur esošo dashboard/profila timeline
- `source_url` per claim ietver timestamp: `?t=N` YouTube, `#t=N` citur — saglabā `store_claim()` idempotenci uz `(opponent_id, source_url, topic)`
- `document_politicians` junction par katru zināmu speakeru ar `role='subject'`

**Komponenti:**
- `src/video_ingest/{cli,fetch,asr,diarize,align,heuristics,finalize,db,state,config,models}.py`
- `.claude/agents/video-extractor.md` + `wiki/operations/agenti/video-extractor.md`
- `wiki/operations/video-setup.md` (ffmpeg + HF token vienreizējais setup)

**Atkarības:**
- `yt-dlp`, `faster-whisper` (CTranslate2 INT8), `pyannote.audio` 3.3.2, `pydub`, `torch+CUDA`

Skat. spec `docs/superpowers/specs/2026-04-28-video-extractor-design.md` un plānu `docs/superpowers/plans/archive/2026-04-28-video-extractor-implementation.md`.

## 2026-04-27 — Saeima Bills Phase 1C (orchestration & glue)

**TL;DR:** `@saeima-tracker` agent prompt expanded to populate
`saeima_bill_politicians` junction live (Step 2) and link votes to bill
stages (Step 5). Public site exposes `/likumi.html` base-law index +
auto-links bill references in claim summaries. CLAUDE.md Pipeline
Invariant 12 (append_bill_stage as sole writer of vote→bill state).

**Why:** Phase 1A delivered helpers; Phase 1B delivered UI templates that
already accepted the data shape. 1C is the glue layer that makes the
templates light up live, without any new core code path.

**What changed:**
- `.claude/agents/saeima-tracker.md` — Step 2 expanded to parse agenda
  bills + match submitters; new Step 5 links each vote to its bill stage
  via `append_bill_stage()`. Adds `KNOWN_INSTITUTIONAL_SUBMITTERS` prompt
  rule (19 entries) + Failure modes tier table.
- `src/generate.py` — `_autolink_bills_filter` Jinja filter wraps
  `\b\d+/(Lp14|Lm14|P14)\b` references in claim summaries with
  `<a href="likumprojekti/<slug>.html">`. `_fetch_law_index_page()`
  builds 33-row sortable index for `/likumi.html`.
- `templates/likumi-index.html.j2` — new (mirrors `/balsojumi.html#bills-list`
  pattern: topic chip + filter + search).
- `templates/balsojumi.html.j2` — footer link "Visi pamatlikumi (33) →" in
  bills-list-tab.
- `templates/{pretruna-detail,politician,pretrunas,index}.html.j2` —
  apply autolink_bills filter to claim summaries.
- `CLAUDE.md § Pipeline Invariants` — adds Invariant 12: append_bill_stage
  is the sole writer of `saeima_votes.bill_id` and
  `saeima_bills.current_stage`. (Committed directly to master as `5cb45c8`
  before worktree creation — doc-only, branch-orthogonal.)
- `wiki/operations/saeima-bills.md` — new operator runbook.
- `src/saeima.py` — `parse_agenda_snapshot` bounds the 500-char lookahead
  window at the next bill's match start to prevent deputy-list bleed
  across bill boundaries (uncovered by 1C live smoke).

**Tests:** 12 new (6 autolink_bills + 5 likumi_index + 1 parse_agenda
boundary regression). Phase 1B suite still passes.

**Live smoke results (2026-04-27):**
- 38 bills parsed from 2026-04-30 agenda (33 new + 5 already in DB)
- 0 unknown institutional submitters; 65 individual submitters matched
- Parser bleed bug found + fixed (22 spurious junction rows deleted)
- Junction post-smoke: 49 valid rows
- Step 5 (vote→stage link) not yet validated live — 2026-04-30 session
  not held yet (today is 2026-04-27)

**Out of scope:** Top nav entry to `/likumi.html` (deferred); Phase 1.5
historical re-scrape; Phase 2 amendment authors; Phase 3 debates →
bill_id; backfilling submitters into existing 91 historical bills.

---

## 2026-04-27 — Saeima Bills Phase 1B-ii: wiki/laws + base_law_slug + politiķa profila sekcija

**Iemesls:** Phase 1B-i (commit `42b2375`) atvēra bills datus publikai (118 detail lapas + balsojumi 3. subtab + cross-link). 1B-ii sasaista bills ar wiki/laws — populē `base_law_slug`, raksta BILLS-SYNC-AUTO blokus, renderē 33 jaunas `/likumi/<slug>.html` lapas, pievieno detail lapā "Saistītais bāzes likums" linka, un sagatavo politiķa profila Likumprojekti sekciju conditional.

**Izmaiņas:**

- **`base_law_slug` retro-backfill**: `scripts/backfill_base_law_slug.py` populē šo nullable kolonnu visiem 118 esošajiem bills (matched 41/118 = 34.7%). Match teritorija: title + jaunākā saistītā vote motif. `upsert_bill()` integrācija — jaunie bills no live aģenta plūsmas (Phase 1C) automātiski iegūst `base_law_slug` ar COALESCE preserving.
- **Shared `load_laws_index` helper** `src/saeima.py` — slug → title parser no `wiki/laws/*.md` H1 rindām. Lietots no backfill skripta + `upsert_bill` + `_fetch_bill_detail` cache.
- **wiki/laws auto-render**: `src/wiki.py::_render_law_bills_block` raksta `<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->` blokus 33 wiki/laws/<slug>.md failos ar tabulu vai empty state. `wiki_sync()` integrēts. Idempotents bytewise.
- **Jaunas publiskas lapas**: `/likumi/<slug>.html` (33 failu) — markdown render no `wiki/laws/<slug>.md` ar likumi.lv linka, bills count metric, full body. Strip H1 + metadata pirms render lai nedubliesies ar pagehead.
- **Detail page papildinājums**: "Saistītais bāzes likums" sekcija conditional render — parādās 41 bills, kuriem `base_law_slug` populēts, ar linka uz attiecīgā likuma lapu.
- **Politiķa profila sekcija**: "Likumprojekti" sekcija + profile-stat butons render TIKAI ja `saeima_bill_politicians` junction populēta priekš šī politiķa. Šobrīd nevienam politiķim sekcija nav redzama (junction tukša pēc Phase 1A); 1C lights up automātiski, kad live aģents to populē.
- **Naming fix**: `wiki/laws/likumi.md` un `wiki/index.md` semantiski pareizi ("Likumi", ne "Likumprojekti"). 33 likumi (ne 34, jo indeksa fails pats nav likums — bija self-count bug).

**Atstāts 1C-am:**
- `.claude/agents/saeima-tracker.md` aģenta prompt update (steps 2/3/5.5)
- Pozīciju auto-link regex `NNNN/Lp14` summary tekstā
- `wiki/operations/saeima-bills.md` runbook
- CLAUDE.md Pipeline Invariant 12

**Datu deltas:**
- `saeima_bills.base_law_slug` populated: 0 → 41 (34.7% no 118)
- Junction `saeima_bill_politicians`: paliek tukša līdz 1C
- Jaunas HTML lapas: `output/atmina/likumi/*.html` × 33

---

## 2026-04-27 — Saeima Bills Phase 1B-i: UI uz publiku

**Iemesls:** Phase 1A (DB schema + helperi + backfill) tika ievests 2026-04-27 (commit `64f1790`), bet bills datus varēja redzēt tikai caur SQL. Phase 1B-i atver tos publikai.

**Izmaiņas:**

- **Jaunas lapas**: `/likumprojekti/<slug>.html` katram no 91+ saeima_bills (slug = `document_nr.lower().replace("/", "-")`)
- **`/balsojumi.html`**: 3. subtab "Likumprojekti" ar topic/status/bill_type filtriem un teksta meklēšanu
- **Vote-card cross-link**: `document_nr` esošās balsojumu kartiņās kļūst par iekšēju saiti uz attiecīgo bill detail lapu (105 saistīti, 34 procedurālie paliek bez)
- **Step 0 P14 motif fix**: paplašina `_DOCUMENT_NR_RE` lai tver unparenthesized `/P14` motifu + papildināts `scripts/backfill_saeima_bills.py` ar fallback uz `resolve_bill_from_motif` kad `document_nr IS NULL` — atrisina HANDOFF Phase 0.7 punkts #6 un atklāj 5 P14 bills + 22 jaunus Lp14 bills (91 → 118 total)
- **Sitemap**: `/likumprojekti/*` URLs pievienoti

**Atstāts 1B-ii:**
- "Saistītais bāzes likums" detail bloks + wiki/laws/<slug>.md auto-render + politiķa profila Likumprojekti sekcija + `base_law_slug` retro-backfill

**Datu deltas:**
- saeima_bills: 91 → 118 (5 P14 + 22 jauni Lp14)
- saeima_bill_stages: 105 → 138
- Tukšs: junction `saeima_bill_politicians` paliek tukšs līdz 1B-ii vai live aģenta flow

---

## 2026-04-26 — Saeima bills Phase 0 prep applied

Pirms Phase 1 implementācijas (`docs/superpowers/specs/2026-04-22-saeima-bills-design.md`) atklāti 5 dizaina flaws audit'ā uz dzīvās DB (139 saeima_votes, 105 ar document_nr, 67% lasījuma klasificējami):

- **Stage classification 33% nezināms** — pie spec § 5.4 30% sliekšņa. Atrisināts ar 4 jaunām stage_name vērtībām (`tiesneša_amats`, `procesuāls`, `Lm14 cits`, `paziņojuma_balsojums`); paredzamais nezināms <8% pēc § 3.3 paplašinājuma. Slieksnis aktualizēts uz 10%.
- **P14 (paziņojumi) nav whitelist** — 5 reālas P14 rindas (dronu uzbrukumi, IT vēlēšanas, robežšķērsošana) būtu silently atmestas. Pievienoti `_VALID_BILL_TYPES = {'Lp14', 'Lm14', 'P14'}` + propagēts pa AgendaBill dataclass, `parse_agenda_snapshot` regex, backfill three-way classification (iepriekš binary `Lp14 | Lm14` būtu mistagged 5 P14 → Lm14), UI filter, detail page kicker.
- **wiki/laws/* izolācija** — 33 manuālas likumu lapas neintegrētas ar bill detail page. Pievienots BILLS-SYNC-AUTO marķieru pattern + `/likumi/<slug>.html` render + `_resolve_base_law_slug` match logic. Atklātais jautājums § 12 Q3 (vai wiki/laws ir atsevišķs spec) atrisināts: iekļauts šajā scope.
- **Phase 3 debates hook** — `saeima_bill_stages.stage_kind` kolonna (default `'vote'`) ļauj nākotnē Phase 3 pievienot stenogrammu utterances bez migrācijas. Phase 1 visi raksta `kind='vote'`; `_VALID_STAGE_NAMES` validē tikai vote rindas.
- **Vote-result audit guardrail** — `scripts/audit_saeima_vote_results.py` validē present-majority formula pret stored result. Šobrīd 0 mismatches uz 139 votes; daļa nedēļas sanity check (sk. `wiki/operations/weekly-routine.md § 4`).

Spec izmaiņas: 8 commits uz `saeima-bills-phase0` branch (no `2e0ff65` audit script līdz `ce8b049` Phase 3 hook), kas modificē `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` 7 sekcijās.

**Phase 1 statuss:** schema un agent prompt darba paka ship-ready uz spec v2 pēc Phase 0 prep.

---

## 2026-04-25 — Strukturālā sanācija: pub_at meta tag fix + Saeima vote-as-document anti-pattern noņemšana

**What changed:**

- **Solis 1A — pub_at sanācija tier-2 web scrape avotos.** `_extract_published_at(html)` helper `src/ingest.py` parsē 8 dažādus meta tag patterns (`article:published_time`, `og:published_time`, `itemprop=datePublished`, `name=publish-date|pubdate|date`, `<time datetime>`, JSON-LD `datePublished`). Wired `_scrape_tier2` abās vietās (homepage fallback + per-article). Pirms — NRA, Delfi, rus.Delfi, LA scrape path saglabāja `published_at=NULL` 100% gadījumu (RSS-based LSM/Diena/TVNet path strādāja korekti). Tagad 4/5 broken avotu pareizi atgriež pub_at; LETA paliek None paywall iemesla dēļ.
- **Solis 1B — Saeima vote-as-document anti-pattern noņemts.** Pirms — `generate_claims_from_votes()` katram individual vote radīja sintētisko `documents` rindu (platform='saeima', NULL title, ~170 char content) tikai tāpēc, ka `store_claim.document_id: int` nepieļāva NULL. Tas izpildīja 8985 fake docs (38% no kopējā 23105) ar 8876 claim atsaucēm, kas izstiepa visus document-based statistic (npr "23k documents", "93.6% NULL pub_at" — patiesie skaitļi 14k web/X docs un 78% web NULL pub_at).
  - `store_claim.document_id` mainīts uz `Optional[int]` (schēma jau pieļāva NULL ar notnull=0; tikai signature un canonicalization bloķēja).
  - `generate_claims_from_votes()` vairs neveido sintētisko docs — padod `document_id=None`.
  - Migrācija `scripts/migrate_saeima_doc_cleanup.py`: pirms-migrācijas check, ka neviens non-saeima_vote claim un neviens document_chunk neatsaucas uz fake docs (abort if so). Atomic transaction: UPDATE claims SET document_id=NULL → DELETE document_politicians → DELETE documents WHERE platform='saeima'. Idempotenta. Auto-backup pirms palaišanas.

**Why:** Lietotājs 2026-04-25 pieprasīja "vispirms visur pareizi un optimāli sastrukturizēt". Strukturālā audita atklājumi nosauca šīs divas kā lielāko parādu pirms tālākām UX/feature lapām: (1) pub_at NULL share aizliedz uzticamu time-window queries pret news content, (2) fake docs iztukšoja katru document-based statistic un padarīja documents tabulas semantiku jauktu (daļa = real docs, daļa = vote skeletoni). Vote provenance pilnībā rekonstruējama no `saeima_votes` + `saeima_individual_votes` caur `(claim.opponent_id, claim.source_url, claim.stated_at)`.

**Backward compatibility:**
- `_extract_published_at` ir tīri additīvs — RSS path (LSM/Diena/TVNet) joprojām ņem pub_at no `<pubDate>`, tier-2 web_scraper tagad arī iegūst pub_at no meta tagiem. Esošie consumers (`item.get("published_at")`) jau pieņēma None, nemainās.
- Vēsturiskās 8876 saeima_vote claims paliek DB ar pareizu `claim_type`, `source_url`, `stated_at`. Tikai `document_id=NULL` mainās. Visi readeri (briefs.py, generate.py, wiki.py) jau pirms tam izmantoja `claim_type='saeima_vote'` filtrus, ne JOIN claims ON documents — nekādas render path izmaiņas vajadzīgas.

**Migration counts (real DB):** fake_docs_pre=8985, claims_nulled=8876, junctions_deleted=8985, docs_deleted=8985, fake_docs_post=0. Backup: `data/atmina_backup_pre_saeima_doc_cleanup_2026-04-25-203058.db` (122 MB).

**Statistic recalibration:**
- Total docs: 23105 → 14435 (no fake docs)
- Web NULL pub_at: 93.6% → 78.2% (3750 web news docs, 2934 NULL — vēl jāuzlabo, bet jaunie scrape no šī brīža darbojas)

**Invariants added:**
- `store_claim` pieņem `document_id=None`. Saeima_vote claims now glabājas BEZ document_id — vote provenance iegūstama caur `(opponent_id, source_url, stated_at)` join uz `saeima_individual_votes`.
- `documents.platform='saeima'` rindas vairs nav atļautas. Migration skripts idempotents — re-run atrod 0.

**Files:** `src/ingest.py` (+helper, +wiring), `src/saeima.py` (-doc creation), `src/db.py` (Optional document_id), `scripts/migrate_saeima_doc_cleanup.py` (new), `tests/test_ingest.py` (+11 tests TestExtractPublishedAt), `tests/test_db.py` (+2 tests for null document_id), `tests/test_migrate_saeima_doc_cleanup.py` (new, 5 tests). 18 jauni testi visi zaļi, 631 kopā passed.

**Out of scope (follow-ups):**
- Vēsturisks pub_at backfill 2934 esošajiem web docs (vajadzētu re-fetch katru URL, paywall risks). Atstāts, jo jaunie scrape no šī brīža darbojas — vēsturiskā metadata nav kritiska.
- LETA pub_at — paywall, nav meta tagu uz publiskās lapas. Atstājam None, jo viņu saturs jau zaudēts cita iemeslā.
- `topics` tabula (Solis 2 plānā) — first-class entitīsis ar slug/description/icon kā pamats nākotnes /temas/ lapām.
- `tracked_politicians.slug` kolonna (Solis 3) — DB-stable slug vietā derive-no-name.

---

## 2026-04-25 — Commentator demotion + profila X subtaba

**What changed:**
- 7 vēsturiskie komentētāji (pid 62 Svirskis, 169 Klucis, 171 @Heinrih5, 172 @Tuksumsz, 174 Lūsis, 175 @Kurmitis_, 177 @PStrautins) demotēti no `tracked_politicians.relationship_type='commentator'` uz `'inactive'`, un to 8 `social_accounts` rindas (Svirskim divas) pārveidotas no `feed_type='first_party'` uz `'relay'`. Tas aizver "ghost profila" antishablonu — komentētāji bija politiķi-skeleti, bet to lapas netika ģenerētas.
- Migrācijas skripts `scripts/migrate_commentator_demotion.py` (idempotents, ar testiem). Re-link `scripts/relink_commentator_documents.py` izdzēsa 366 vēsturiskus `role='subject'` linkus un palaida `link_politicians_to_documents(rescan_all=True)` lai matcher tekstu skenētu un atrastu pareizos mentioned politiķus.
- **Matcher uzlabojums:** pievienots `_latvian_surname_inflections()` `src/ingest.py`, kas ģenerē Latvijas deklināciju formas (gen/dat/acc) 4 visbiežākajiem -is/-s/-š/-ņš/-a/-e galotnēm. Atrisina silenta matcher misses tipa "Lūgums sižetus Melnim" → tagad matcher pareizi atrod Melnis (157). Palatalizācija (n→ņ utt.) tikai genitīvā. Additīvi savieto ar `name_forms` no DB.
- **Politiķa profila lapā jauna X subtaba** (`templates/politician.html.j2` + `_fetch_politician_detail` x_posts query): rāda visus twitter+x_mention dokumentus, kuros politiķis linkots, sakārtotus pēc published_at DESC, līdz 50 ierakstiem. Aizvieto zaudēto comment claims pipeline ar plašāku raw mentions plūsmu.
- **Komentāri subtabas intro paskaidrojums** — pievienots, ka šī sadaļa tagad rāda tikai vēsturisko datu (pirms 2026-04-25), aktuālie pieminējumi X subtabā.

**Why:** Commentator-as-politician modelis radīja datu modeļa antišuvi — 4 izteiksmīgi komentētāji bija pirmā klases tracked entītes, bet viņu profila lapas netika ģenerētas (relationship_type filtrs `src/generate.py:392`), kamēr 175+ citi mentions ikdienā palika kā raw documents bez profila redzamības. Demotēšana saliek vienotu modeli: politiķi ir tracked, visi pārējie X handles ir vai nu ielādes avoti (relay social_accounts) vai jēli mentions (x_mention dokumenti). Profila X subtaba dod vienotu lasītāja skatu uz visu X saturu, kas attiecas uz konkrēto politiķi.

**Esošās 9 commentary claims (pirms 2026-04-25)** paliek DB ar `speaker_id` FK valid (commentator pid joprojām eksistē, tikai `relationship_type='inactive'`). Jaunas commentary claims vairs netiek ģenerētas. Komentāri subtabas count gradually trends to 0 kā 90-d. window apzilst.

**Plāns un izpilde:** `docs/superpowers/plans/archive/2026-04-25-commentator-demotion.md`. Commits: 6212b17 (audit baseline), a3b4a14 (migrate), 0465d39 (relink), a027b78 (declension fix), 6209957 (x_posts fetcher), 36e9d1e (X subtab UI), 8e00bf7 (Komentāri intro).

**Fāze 2 (1-2 mēn):** Kad X subtaba būs piepildījusies ar reāliem datiem, pievienot pithiness ranking (pithy commentary extraction) — automātiski izcelt 5-10 visizteiksmīgākos tvītus mēnesī. Tas funkcionāli aizvietos veco operatorkurēto commentary pipeline ar plašāku datu bāzi.

---

## 2026-04-25 — `social_accounts` → X-only + `external_profiles` tabula

**What changed:**
- Jauna tabula `external_profiles` (src/db.py, init_db bloks) glabā ne-X politiķu profilus: Facebook (19), website (6), un nākotnē citus (YouTube, Instagram). Schēma paralēla `social_accounts` + papildus `url` lauks; fetch-ready (`last_fetched`, `last_post_id`, `active`), bet pagaidām bez fetcher koda — tikai UI display.
- `social_accounts` no šī brīža satur tikai X kontus. UNIQUE indekss `idx_social_accounts_unique` uz `(opponent_id, platform, handle)` novērš literālus dublikātus.
- Migrācijas skripts `scripts/migrate_external_profiles.py` idempotenti pārvieto 19 FB + 6 website rindas uz `external_profiles`, reklasificē `realNepareizais` (id=62) uz `relationship_type='commentator'` (analogs Kļuciņam), un `KNL_LTV1` (id=59) uz `relationship_type='journalist'` + `feed_type='relay'` (analogs LTV Ziņas pattern).

**Why:**
- 2026-04-25 audits atklāja, ka `social_accounts` bija piesārņota: 18 FB rindas + 5 website (URL piebāzti `handle` kolonnā) + 2 literāli X dublikāti, visas `NULL last_fetched` (nekad nav fetchotas). `social.py` un `x_mentions.py` jau filtrē `WHERE platform='twitter'`, tāpēc FB/website rindas bija tikai konfigurācijas atkritumi. Problēma: nākamais Claude varētu tos pievienot atpakaļ, neapzinoties X-only konvenciju.
- Sākotnēji šķita, ka `AinarsSlesers ×2` un `suvajevs ×2` ir X dublikāti — patiesībā tie bija X+FB pāri ar identiskiem handle (vienādais vanity name abās platformās). Migrācijas dedupe solis pareizi nekustina ne vienu (jau atsevišķas platform='twitter' un 'facebook' rindas). FB rindas `_migrate_facebook_rows` pareizi pārceļ uz external_profiles.
- `realNepareizais` un `KNL_LTV1` bija `relationship_type='inactive'`, kas slēpa tos no dashboard. Nepareizais ir trešpuses komentētājs (ekvivalents Kļuciņam), ne inaktīvs politiķis. KNL ir ziņu raidījums ar X kontu, kas post-hoc matcher pattern tiešām ir `feed_type='relay'` (sk. 2026-04-23 `ltvzinas`).

**Backward compatibility:**
- Tīri forward-only migrācija. `social.py::_store_tweets` un `x_mentions.py::fetch_mentions` jau filtrē `platform='twitter'` — nekādu behavior changes.
- `_fetch_politician_detail` un politiķa template paplašināti, lai parādītu `external_profiles` ikonas (FB + website) blakus X handle ikonai. Ja external_profiles tukša politiķim, profile-links div paliek kā iepriekš.
- Migrācija veikta vienā SQLite transakcijā; neveiksme → rollback, DB paliek nemainīga. Backup: `data/atmina_backup_pre_external_profiles.db`.

**Invariants added:**
- `social_accounts` = tikai X kontu datu ieraksti, viens uz politiķi (UNIQUE `(opponent_id, platform, handle)`). FB/website/citi → `external_profiles`. Dokumentēts `CLAUDE.md §12` prefiksā.
- Migrācija idempotenta: `INSERT OR IGNORE` pret UNIQUE(opponent_id, platform, url) external_profiles tabulā + guarded UPDATE (`WHERE current != target`) pret reklasifikāciju. Otrā palaišana atgriež visas nulles / False.

**Files:** `src/db.py` (external_profiles schema), `src/generate.py` (profile detail + render context), `templates/politician.html.j2` (FB + website icons), `scripts/migrate_external_profiles.py` (new), `tests/test_db.py` (2 new), `tests/test_migrate_external_profiles.py` (new, 6 tests), `tests/test_generate.py` (1 new), `CLAUDE.md` (§12 prefix).

**See also:** [§ `social_accounts.feed_type`](#2026-04-23--social_accountsfeed_type-relay-vs-first_party) — `feed_type` klasifikators paliek nemainīgs (`'first_party'` vs `'relay'`), tikai tabulas tvērums šaurāks.

**Out of scope (follow-ups):** FB/website fetcher implementācija (pagaidām tikai UI display). `commentator_weight` lauks, lai dampenētu skaļus komentētājus profila feed'ā — ievedīsim, kad būs 4+ tracked commentators (patreiz 2: Kļuciņš + Nepareizais).

---

## 2026-04-23 — Matcher role integrity + diacritic validator fixes

**What changed:**
- `src/social.py::_store_tweets` now assigns `role='subject'` only when the tweet's source_url author matches the politician's registered twitter handles; mismatch or unresolvable URL → `role='mentioned'`. Mirrors exactly the 2026-04-20 fix pattern that was applied only to the post-hoc scanner path.
- `src/quality.py::validate_lv_diacritics` adds a fasttext primary language-ID early-exit (`lang in {en, ru, de, fr, es, pl, it} and conf >= 0.70 → True`), extends `EN_MARKERS` with ~45 common tokens that were missed (`at`, `more`, `already`, `six`, `times`, `remain`, `fall`, etc.), and adds `logging.warning` on rejections for future observability.
- `scripts/fix_subject_role_leakage.py` one-shot idempotent backfill resolved 83 mismatched junction rows: 70 UPDATE (`subject`→`mentioned`), 13 DELETE (mentioned row already existed, UNIQUE constraint blocked straight UPDATE). Claim audit flagged 4 pre-existing claims (#11273, #11226, #11318, #11229) on now-downgraded junction rows for manual editorial review — no auto-delete.

**Why:**
- Matcher: The 2026-04-20 fix patched `src/ingest.py::link_politicians_to_documents` but NOT `src/social.py::_store_tweets`. The live-fetch path continued hardcoding `subject` on every tweet, including retweets/quote-tweets/replies that twikit normalises to the ORIGINAL author's source_url. 83 rows accumulated between 2026-04-21 and 2026-04-23 before detection during today's Komentētāji extraction run.
- Diacritic: M. Krusts English-language tweet quote was rejected because `LV_STOPWORDS` includes `to` and `EN_MARKERS` missed common counter-tokens. Agent had to drop the `quote` field to save the claim — lossy. Fix preserves stripped-LV detection via fallback-to-token-matcher design (fasttext misclassifies stripped LV as `fr`/`sr` at low confidence, so the 0.70 threshold keeps guardrail intact).

**Backward compatibility:**
- Matcher fix is forward-only; existing `mentioned` and `subject` semantics unchanged. Backfill downgrades preserved linkage metadata (UPDATE) or removed redundancy (DELETE when duplicate `mentioned` existed).
- Diacritic fix is additive: fasttext early-exit ADDS an accept path, EN_MARKERS expansion ADDS tokens. No existing acceptance path removed. Stripped-LV rejection path preserved unchanged (tested via `test_stripped_latvian_still_rejected_despite_fasttext_drift`). `logger.warning` adds observability with no behavior change.

**Invariants added:**
- `_store_tweets` role assignment now requires `source_url` author to be in `social_accounts.handle` set (case-insensitive, any `active` state) for `role='subject'`. Symmetric with `scripts/fix_subject_role_leakage.py` backfill. YouTube/Facebook sibling fetchers in same file still hardcode `subject` — acceptable because those platforms don't surface other authors via user timelines the same way twikit does.
- Backfill is idempotent by construction: `WHERE role='subject' AND handle_mismatch` means re-runs find nothing after the first pass.

**Files:** `src/social.py`, `src/quality.py`, `scripts/fix_subject_role_leakage.py`, `tests/test_social.py` (new, 3 tests), `tests/test_quality.py` (4 new tests).

**See also:** [§ `social_accounts.feed_type`](#2026-04-23--social_accountsfeed_type-relay-vs-first_party) — same `_store_tweets` function covers a different code branch (relay accounts skip the per-tweet handle match entirely).

**Out of scope (follow-ups):** `match_politicians(text)` content-scan enrichment in `_store_tweets` for multi-politician mentions. `published_at` backfill for 55% NULL web docs. `print_routine()` heuristic distinguishing "quiet user" (last_fetched today, last_post_id stale) from "scraper broken" (not fetched in Nd). Explicit `language='en'` kwarg on `store_claim` for agents that already know the quote is English.

---

## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

**What changed:** Added `social_accounts.feed_type TEXT DEFAULT 'first_party'` column (values: `first_party` | `relay`) plus `idx_social_feed_type` index. Institutional media X accounts (first seed: LTV Ziņas `@ltvzinas`; future: Delfi, TVNET, LSM, ministriju konti) now ingest as `feed_type='relay'`. Two pipeline branches read the flag:

- `src/social.py::_store_tweets` — when `feed_type='relay'`, skips the per-tweet handle-match path entirely; documents are inserted with empty `politician_links`. For `first_party` accounts the matcher entry above (per-tweet handle match → subject/mentioned) still applies.
- `src/ingest.py::link_politicians_to_documents` — precomputes `relay_handles` from social_accounts rows with `feed_type='relay'`; when a Twitter doc's URL author is a relay handle, quoted tracked politicians keep their `subject` role instead of being downgraded to `'mentioned'`. Quoted speakers therefore reach the normal extraction queue via `get_pending_politicians()`.

**Why:** Before this, `_store_tweets` unconditionally marked the account owner as `subject` of their own tweet. For politicians posting their own X content this is correct (author IS the speaker). For a news-relay account like LTV Ziņas it is wrong: LTV's tweets quote third parties (e.g. *"sacīja deputāts Edvards Smiltēns"*), so the *quoted politician* should be the subject. Under the pre-change pipeline, quoted politicians got `role='mentioned'` and never entered their own extraction queue; LTV entered its own queue with its own tweets, and the claim-extractor would attempt to extract LTV's "first-party positions" from relayed quotes — semantically wrong and invisible to first-party contradiction detection.

**Pipeline effect for a relay-sourced claim:** `opponent_id = quoted politician`, `speaker_id = NULL` (first-party), `claim_type = 'position'`, `source_url = LTV tweet URL`. `search_similar_claims` (default `speaker_scope='first_party'`) correctly contradicts these against the politician's direct posts.

**Backward compatibility:** Default `'first_party'` preserves all existing account behavior. Politicians' own X accounts, commentators (KlucisD), and individual-journalist accounts (Lato Lapsa) are unchanged. The `relationship_type='commentator'` commentary path (added earlier today) fires independently of `feed_type` and is unaffected.

**Files:** `src/db.py` (init_db schema patch + index), `src/social.py` (`_store_tweets` feed_type lookup + conditional link), `src/ingest.py` (`link_politicians_to_documents` precomputes `relay_handles`, adds guard clause on downgrade elif), `scripts/seed_media_sources.py` (MEDIA_SOURCES with `feed_type='relay'` + UPSERT-on-differ for existing rows), `tests/test_db.py` (column-present + idempotency, both with index assertion), `tests/test_ingest.py` (first-party regression guard + relay skip link + relay author keeps quoted politician as subject).

**See also:** [§ Matcher role integrity](#2026-04-23--matcher-role-integrity--diacritic-validator-fixes) — `first_party` accounts take the per-tweet handle-match branch of the same `_store_tweets` function; `relay` accounts skip that branch entirely.

**Operational:** 17 pre-patch LTV-subject junction rows (from an earlier manual fetch test) deleted; `link_politicians_to_documents(rescan_all=True, days=7)` re-evaluated them under the relay logic. Three docs correctly re-assigned (Smiltēns, Butāns, Čakša → subject). LTV Ziņas removed from `get_pending_politicians()` queue.

**Matcher hygiene (related but separate):** While auditing, discovered `match_politicians` was producing false-positive `LTV Ziņas:subject` links on news articles that mentioned the Latvian word `ziņas` ("news") — e.g. `plašsaziņas` and the brand `360 Ziņas`. Added `negative_patterns=["plašsaziņas", "360 Ziņas", "360 ziņas"]` to `tracked_politicians.id=170`. This is a name-collision symptom similar to the 2026-04-20 Andris Bērziņš case; if more relay media accounts are seeded with similarly generic tokens, a matcher-level filter that skips relay-type entities during text-scan may be worth considering.

**Out of scope (follow-ups):** Dedicated UI "Mediju avoti" grouping separate from individual "Žurnālisti"; retweet filtering at fetch time (`_store_tweets` currently stores `RT @...` posts but truncated text rarely matches politicians, so they quietly sit with no junctions); auto-detect relay from account metadata.

---

## 2026-04-23 — Komentētāji (speaker_id on claims)

**What changed:** Added `claims.speaker_id INTEGER NULL` column to distinguish authors from subjects. Introduced `relationship_type='commentator'` for non-politician public commentators (KlucisD seeded) and `claim_type='commentary'` for their output. Third-party commentary now renders on politician profiles as a dedicated "Komentāri" tab with explicit speaker attribution.

**Why:** Before this, a commentator tweeting "Pūpols ir korumpēts" either got dropped by the indirect-reference gate or misattributed as Pūpols' own position. Neither was right — the content is editorially valuable (third-party allegations are a legitimate transparency signal) but legally requires "X apgalvo par Y" framing, not assertion-of-fact. The `speaker_id` column is the minimum architectural change that enables correct attribution.

**Backward compatibility:** `speaker_id IS NULL` = first-party (legacy default). All pre-2026-04-23 claims remain NULL; readers use `COALESCE(speaker_id, opponent_id)` or explicit `IS NULL OR speaker_id = opponent_id` filters. `store_claim` signature adds optional `speaker_id` kwarg (default None).

**Invariant added:** `search_similar_claims` defaults to `speaker_scope='first_party'` — commentary claims are excluded from contradiction-candidate matching by default, so "Pūpols contradicted himself" never mis-fires because the second claim was actually a commentator writing about him.

**Files:** `src/db.py` (schema + store_claim + search_similar_claims), `src/tools.py` (pydantic wrapper plumbing), `src/analyze.py` (save_analysis plumbing), `src/generate.py` (_fetch_commentary_about + politician-listing filter + profile context), `templates/politician.html.j2` (new Komentāri tab + stat button), `assets/style.css` (`.komentari-*` block), `.claude/agents/claim-extractor.md` + `.claude/agents/contradiction-hunter.md` (prompt updates — ungitignored, on-disk only), `scripts/seed_commentators.py` (KlucisD seed).

**Out of scope (follow-ups):** Reply-tree capture under tracked politicians' posts; `/komentetaji/` index page in main nav; commentator-vs-commentator contradiction tracking.

---

## 2026-04-22 — claim-extractor batch-drift fixes

Diagnostika (sk. `data/autoresearch/DIAGNOSTIC_SUMMARY.md`) pārbaudīja divas hipotētiskās kļūdas:

- **`stated_at` = scrape-date, nevis `document.published_at`** → **nav aktuāla kļūda.** 365/365 claims pēdējā 30 dienu logā ar pub ≠ created (≥2 d atstarpe) pareizi seko `published_at`. 2026-04-21 retroaktīvais labojums + pašreizējais prompt to apstrādā pareizi.
- **Indirect-reference saves** → **reāla kļūda, bet izolētā prompt darbojas pareizi.** 33 production-saved dokumenti testēti neitrālā viena-doc eval — izolētais extractor noraida 18 no 20 šaubīgajiem kā `empty`/`skip`. Piekrīt 13 likumīgajiem saglabājumiem. Kļūda ir batch-mode context drift.

**Labojumi (šī commit):**

1. `.claude/agents/claim-extractor.md` — circuit breaker 33 → 12 dokumenti uz politiķi/sesiju. Pievienots self-check: pirms katra `save_analysis` pārlasa savu `reasoning`, ja tā atzīst "nav paša pozīcija / pašam nav ekstraktējamas / bare RT / pure retweet / does not speak / tikai pieminē" → atgriež `empty`.
2. `src/analyze.py` — soft indirect-reference gate `save_analysis`. Ja reasoning satur stiprus indirect markerus, prepend `NEEDS_REVIEW:` marķieris (nevis nomet claim — "netiešs citāts caur LETA" ir likumīgs un netiek skarts). `@quality-reviewer` triāžē NEEDS_REVIEW ierakstus. Pilnā markieru saraksta: `_INDIRECT_MARKERS_LOWER` tuple.
3. Operatora vadlīnija: > 5 docs/politiķi → dispečē pa vienam sub-aģentam ar atsevišķu kontekstu (fan-out), nevis viens sub-aģents daudzdoc režīmā.

**Artifacti:**
- `data/autoresearch/DIAGNOSTIC_SUMMARY.md` — pilnā diagnostika
- `data/autoresearch/round1_results.md`, `round1_batch.json`, `hard_batch.json`, `indirect_flagged_docs.json`, `dryrun_seed.json`
- `data/backups/atmina_2026-04-22-autoresearch-pre.db` — pirms-work DB backup

**Testi:** `tests/test_analyze.py::TestIndirectReferenceGate` (4 testi) — marker detection hits/misses + integration test pret `save_analysis`.

---

## 2026-04-17 — Diacritic validation

`save_analysis()` un `store_claim()` validē, ka `stance`, `quote`, `reasoning` un `brief_markdown` saglabā latviešu garumzīmes (āēīūņļķģšžč). Stripped teksts tiek atraidīts (sk. `src/quality.py`).

**Signāls operatoram:** ja redzi "diacritic validation failed" — tas ir context drift. Nekavējoties STOP un sāc jaunu sesiju. Drift ir autoregresīvs — turpināšana vienā sesijā pasliktinās.

**Praktiska robeža:** ~8 politiķi vienā sesijā maksimums. 2026-04-16 incidents rādīja kvalitātes kritumu pēc 8 secīgiem extractions. Validācija `src/quality.py` noraida stripped tekstu jau `save_analysis()` / `store_claim()` līmenī — papildu post-hoc skenēšana nav vajadzīga.

---

## 2026-04-11 — claim_type split (`position` vs `saeima_vote`)

`claims` tabula tagad nošķir divus tipus:

- **`position`** — mediju/X first-person retorika (default)
- **`saeima_vote`** — Saeimas balsojumu ieraksti, auto-tagged ar `generate_claims_from_votes()`

**Kāpēc:** "pozīciju" skaits iepriekš apvienoja abus un izskatījās 8× lielāks par faktisko retorisko aktivitāti. Skaitļi nav mazāki — tie ir pārklasificēti.

**Praktiskie noteikumi:**
- `@claim-extractor` nekad nepārraksta default — tas vienmēr ražo `position`
- Visi readeri (`wiki.py`, `briefs.py`, `generate.py`) filtrē pēc `claim_type`, nevis pēc `source_url LIKE '%saeima%'` heiristikas
- Rhetoric-vs-action retrieval caur `search_similar_claims(claim_type_filter=...)` strādā directionally per call-site:
  - `position` viedoklis → kandidāti iekļauj abus tipus
  - `saeima_vote` viedoklis → kandidāti iekļauj tikai `['position']` (vote-vs-vote ir procesuāls troksnis)
  - Vispārēja līdzīguma meklēšana → `None`

---

## 2026-04-11 — `save_analysis` atomicity (S10)

Pilna analīze + claims + reviewed-docs update iet **vienā SQLite transakcijā**.

- Katastrofāls DB write failure (disk full, lock timeout) → `status="failed"` ar `transaction_rolled_back` un pilnībā atceļ izmaiņas
- Validation-level skips (missing source_url, inactive politician) → `status="partial"` bez rollback (loģiski drops, ne state korupcija)

**Saistīta izmaiņa:** kontradikcijas vairs netiek automātiski salīdzinātas no `save_analysis`. Analītiķis manuāli izsauc `search_similar_claims(claim_type_filter=...)` un `store_contradiction`, kad atrod reālu pretrunu.

---

## 2026-04-11 — Coalition classification `parties.coalition_status`

Autoritatīvais truth source koalīcijas statusam ir `parties.coalition_status` kolonna (nav hardkodēts saraksts).

**Vērtības:** `coalition` | `opposition` | `not_in_saeima`

**Lasīt caur:**
- `src.coalition.get_coalition_map(db)` → `{partijas_nosaukums_vai_īsais_nosaukums: status}` (batch — izmanto, kad klasificē daudzas rindas)
- `src.coalition.party_status(party)` — single lookup

**Nekad** nelietot `tracked_politicians.relationship_type` koalīcijas loģikai — tas ir legacy per-politician tracking role bez koalīcijas semantikas.

**Pēc 2026-04-11 `relationship_type` saglabā nozīmi tikai šīm vērtībām:**

| Vērtība | Nozīme |
|---|---|
| `inactive` | Paslēpts no dashboard |
| `journalist` / `influencer` / `neutral` | Audience accounts — izslēgti no brief leaderboards |
| `tracked` | Aktīvs default |

Legacy vērtības `opponent`, `coalition_partner`, `potential_ally` migrētas uz `tracked`.
