# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Aģenti / pipeline

### [FIX] Partija ≠ frakcija — paliek tikai (c) UI formulējums

**(a) + (b) IEVIESTI 2026-07-28** (CHANGELOG; T6 korolārs CLAUDE.md, brief-writer self-check 14, saeima-tracker piezīme; sakne — tendence #373, labota ar #377 + rollback `data/rollback_note373_kirsteins_faction_2026-07-26.sql`).

**Paliek atvērts (c):** renderēto profilu formulējums politiķiem, kuriem `party` ir, bet `faction` nav (UI lēmums, zema prioritāte).

**Brīdinājums — NEMĒĢINI „labot" Kiršteina `party`.** Gada griezums (`NULL` 454 pret `LPV` 57) ir nepareizs lasījums; sēžu logā 03-26…04-01 viņam LPV 57/70 ≈ 81 % = blīvs → īsta partijas maiņa. `/audit-integrity` viņu tur starp trim leģitīmajiem karogiem (Ābrama 77, Kiršteins 96, Ceļapīters 145) — „leave them alone, they will flag again every run".

### [OPEN] Stance-fidelity atlikums: matcher neskenē `title`, paywall stop-gate, viena notikuma dublēšanās

Konteksts: 07-25 deep-check — 4 no 6 kandidātiem nomira AVOTA, ne satura dēļ; labošanas kampaņa PABEIGTA (vārti `@claim-extractor` §8, parafrāžu klase 22→0; CHANGELOG 2026-07-25 un 2026-07-28).

Palicis atvērts:

- **(b6) matcher neskenē `title`.** Doc 4909: vārds tikai virsrakstā (intervija uzrunā ar „jūs") → piesaiste ar roku. Mērogs (07-27): +33 pāri uz 5088 dokiem (31 īsts / 2 viltus) — klusa pārklājuma klase tieši intervijās. Ieviešana 2. fāzē ar `mentioned` lomu: `docs/plans/2026-07-27-matcher-koliziju-plans.md` § 4. **Papildu arguments — amata-vārda klase (2026-08-04):** doc 80022 un 79087 Rinkēvičs ķermenī ir tikai „Valsts prezidents", junction nesaista vispār; #615955 ekstraktēts pa escape-hatch. **Šeit pieder arī `d.title` jautājums (verdikts 08-17):** `get_politician_documents()` SELECT `title` neatgriež — prompts kopš 08-1x to skaidri saka, tāpēc nesakritība slēgta; `d.title` pievienošana SELECT-am izlemjama šajā 2. fāzē, ne atsevišķi.
- **(c) `is_paywall` kā ekstrakcijas stop-gate**, analogs truncated-stub vārtiem. Prompta noteikums („paywall stubam `confidence` reti drīkst pārsniegt 0.6") eksistē, koda vārtu nav.
- **(d) #7308 un #11003 ir VIENS notikums** (Čudars uzdod dienesta pārbaudi Balševicam, 10.04.2026) divos dokumentos ar divām tēmām, tāpēc idempotence tos nesapludināja. Konsolidācija = redakcionāls lēmums, ne defekts.
- **(e) krossavota dublikāti pāri dienām — tas pats izteikums divos medijos** (2026-08-12, operatora lēmums: backlog). Aģentūras relīzi pārpublicē vairāki portāli dažādos datumos; idempotences atslēga `(pid, source_url, topic)` to pēc uzbūves nesedz. 08-12 tā radās #689553/#689555 (LETA 08-11 → diena.lv 08-12, tā pati valdības sēde) — pieķēra tikai `@quality-reviewer` 2. pārbaude, un tie ar nepareizu `stated_at` bija uzpūtuši pārskata NVO sadaļu no 2 uz 4 pozīcijām (dzēsti, `data/rollback_qr_daily_2026-08-12.sql`). Lētākais kandidāts: `@claim-extractor` promptā solis «ja dokuments ir aģentūras relīzes pārpublicējums, pārbaudi ±2 dienu claims par to pašu notikumu pirms save»; alternatīva — QR paliek vienīgais tīkls (strādā, bet maksā labošanas ciklu pēc fakta).

**Rīks paliek atkārtojams:** `scripts/audit_quote_fidelity.py` (read-only). Virsrakstu un `not_subject` klašu vājums ir izmeklēts un pierakstīts § Ne-darīt (`audit_quote_fidelity.py` virsrakstu klases 38 atlikušie ieraksti) — tur batch-fix nesāc. Jaunas **parafrāzes** rindas turpretī ir spēcīgs signāls: tās nozīmētu, ka §8 vārti kaut kur netur.

### [OPEN] Medību pēdas @contradiction-hunter (07-25 adversārā pārbaude + 08-03 ekstrakcija)

2026-08-03 ekstrakcijas un triāžas aģenti atstāja četras jaunas pēdas (neviena nav saglabāta kā pretruna — visas prasa strukturālu, ne embedding pārbaudi):

1. **Krištopans airBaltic balsojumu pāris** — #69556 `Balsoja PAR: Par iespējamajiem valsts papildus nepieciešamajiem ieguldījumiem AS "AirBaltic"` (2025-06-19) pret #10375 `Balsoja PRET: ... valsts īstermiņa aizdevuma izsniegšanai` (2026-04-16). PIRMS citēšanas obligāta pilna `document_nr` ķēde (T14) — var būt procedūra.
2. **Kulbergs solījums-pret-izpildi** — #615846: jūnijā "tūlīt šo birokrātisko murgu beidzam", augustā kavējas bez termiņa. T9 klase.
3. **Abu Meri pret savas ministrijas slieksni** — VM: drošai dzemdību palīdzībai vajag ≥500 dzemdības/gadā; Balvos 140/gadā, un ministrs aicina turpināt (#615879). Ministrs-pret-iestādi spriedze, ne personīga pretruna.
4. **Valainis #17807 iespējama vēsturiska stance INVERSIJA** — "Iebilst pret obligāto revīziju atcelšanu" (05-03) stāv starp #17781 (05-01) un #521022 (05-29), kas abi pauž pretējo; izskatās pēc ekstrakcijas kļūdas, ne pozīcijas maiņas — pārbaudīt pret avotu.

7. **Šlesers Rail Baltica interešu leņķis (2026-08-12, DA piezīme pēc KILL verdikta)** — pretruna 2019↔2026 atspēkota (instrumentāls lietojums ≠ normatīvs atbalsts; #689515 quote=null; izmaksu jaunie fakti), bet paliek potenciāli publicējams **interešu stāsts**: ģimenes tranzīta biznesa plāns 2019 (Re:Baltica, doc 85794) rēķinājās ar Rail Baltica kā kravu ceļu uz Eiropu, 2026 Šlesers projektu sauc par iespējamu afēru (#17916). Nesējs būtu analīze/sintēze, ne pretrunu virsma; operatora lēmums.

8. **Alvis Hermanis (pid=29) — MMN pašdefinīcijas maiņa piecu mēnešu laikā (2026-08-15, ekstrakcijas aģenta blakusatradums).** #95 (2026-03-24) raksturo MMN kā „ekonomiski labēji, **nacionālisti, ar kristīgām vērtībām**"; 2026-07-14 pozīcija to pozicionē „**nevis kā konservatīvu labēji nacionālistisku spēku**, bet kā modernistisku projektu". Abi ir paša partijas līdera pašdefinīcijas, tāpēc koalīcijas disciplīnas un procedūras skaidrojumi te nederēs — bet pirms citēšanas jāpārbauda, vai runa nav par divām savietojamām asīm (ekonomiskā vs kultūras pozicionējums). Abi claims ir vecāki par šo dienu; nekas nav mainīts.

Vēsturiskās divas (07-25):
Abas nāk no `@devils-advocate`, kas tās atteicās risināt pats (pareizi — tās prasa pilnu virziena meklējumu, ne blakusnojautu):
5. **Vītols #10983 (2026-04-16) ↔ #527892 (2026-06-11)** — #10983 kritizē airBaltic padomes priekšsēdētāju Martinovu par riska vērtējuma maiņu pēc „padomē iecelts", t.i. amatā iecelšanu traktē kā spriedumu korumpējošu; septiņas nedēļas vēlāk aizstāv neierobežotu personisku iecelšanas brīvību, pats pievienojoties valdībai. Tā pati mehānika abās pusēs, īsāka sprauga nekā noraidītajam K4. DA vērtē kā *a priori* vāju (Martinova kritika ir par faktu maiņu, ne par iecelšanu kā tādu), bet prasa mednieka caurlaidi, ne žēlastību.
6. **Kulbergs NVO retorika↔rīcība** — „negribēju finansējumu atņemt" (07-20/07-22) pret to, ko Valsts kancelejas analīze un paralēlās NA ministru darbības faktiski dod finansējuma lēmumos. Tā ir **strukturāla (T9 klases) pārbaude, ne embedding pāris**, un tai vajadzīgi iznākuma dati, kuru DB pagaidām nav. Dzīvs jautājums, ne slēgts.

### [FIX] Idempotences kluso merge — vairāki distinkti claims no viena (pid, url, topic)
Viens dokuments ar vairākām distinktām viena topika pozīcijām → otrā+ klusi sapludinās (Data Contract #3, T2). **(a) IEVIESTS 2026-07-25:** `save_analysis` ziņo `silent_dedup` + `status=partial` viena izsaukuma ietvaros (4 testi `tests/test_silent_dedup.py`); **(c) IEVIESTA 2026-08-05** — claim-extractor konsolidācijas vadlīnija. **Paliek atvērts (b):** stance-hash dimensija idempotences atslēgā — mainītu Data Contract #3, prasa atsevišķu lēmumu.

### [FIX] Partijas piederības maiņa ziņās nesinhronizējas ar tracked_politicians.party
T6 klase: partijas maiņas claim nesinhronizē `tracked_politicians.party` (Verginas gadījums 06-29, `data/fix_vergina_left_jv_2026-06-29.sql`). **(a)+(b) IEVIESTI 2026-08-05:** claim-extractor „Party-change signal check", brief-writer self-check 16, daily-routine solis. **Paliek (c):** datēta `party_history` tabula, ja vēsturiskā precizitāte kļūst svarīga; pa to laiku manuāla UPDATE + pāra rollback, amata/partijas hronoloģiju pārbaudot manuāli (Ingas Bērziņas mācība — CHANGELOG arhīvs 2026-06-11).

### [FIX] Pārskata virsraksta labojums ir ČETRU vietu labojums — `visual_brief_json` ir kluss ceturtais (2026-08-27)

**Trigeris.** 2026-08-26 pārskatā #505 «Galvenā tēze» bija faktu kļūda («septiņus termiņus»; pirmavots doc 95670 dod sešus centram, septīto Valsts kancelejai). Labots `content` blokā «## Vizuālais brief» + tendencēs, palaists `--only=blog,dashboard` — un renders izgāja cauri KLUSI: pārējie labojumi lapā parādījās, bet `og:title`, `twitter:title`, H1 un abi `alt` teksti palika ar veco skaitli. Vajadzēja otru renderu un otru atradumu.

**Sakne.** `src/render/blog.py:417-422` lasa virsrakstu no DENORMALIZĒTĀS kolonnas `context_notes.visual_brief_json`, ne no `content`. `src/briefs.py::parse_visual_brief()` to kolonnu aizpilda tikai pārskata RAKSTĪŠANAS brīdī; vēlāks `content` labojums to nesinhronizē, un `display_title = headline or <fallback>` nozīmē, ka glabātā vērtība vienmēr uzvar. Denormalizēts lauks, kas noklusējuma stāvoklī ir novecojis — CLAUDE.md § «Denormalizētie lauki ir novecojuši pēc noklusējuma» klase, tikai šoreiz virsrakstā.

**Rīcība (izvēle operatoram):**
- (a) `parse_visual_brief()` izsaukt renderā, ne tikai rakstīšanā — vienkāršākais, bet maina divu funkciju atbildības robežu;
- (b) tests, kas prasa `json.loads(visual_brief_json)['headline'] == parse_visual_brief(content)['headline']` katrai `daily_brief`/`weekly_brief` rindai ar aizpildītu kolonnu — noķer diverģenci, nelabo cēloni;
- (c) atzīmēt konvencijā, ka virsraksta labojums iet četrās vietās (DB `content` + `visual_brief_json` + pārskata kopija + `wiki/dailies/`) — lētākais, bet paļaujas uz cilvēku.

**Saucējs izmērīts (2026-08-27): 161 pārskats ar aizpildītu `visual_brief_json` → 143 sakrīt, 13 `content` blokā nav parsējami, 5 NEsakrīt.** Piecas diverģentās: #218 un #221 (glabātais `headline` ir `None`, tāpēc renders krīt atpakaļ uz virsrakstu — nekaitīgi), un **trīs, kur dzīvā lapa nes citu virsrakstu nekā paša pārskata «Vizuālais brief» bloks**: #212 «Rinkēvičs nominē Kulbergu veidot valdību» pret «uztic Kulbergam veidot valdību»; #252 «Saeimā 70 balsojumi» pret «Saeima pieņem 3 likumus»; #314 «…nav pieņemama» pret «…21 mrd eiro». Neviens no tiem nav faktu kļūda tādā mērā kā 08-26 gadījums, tāpēc **retroaktīva labošana NAV ieteikta** (publicētu pārskatu pārrēķins ir standing noraidījums) — skaitlis vajadzīgs tikai (b) varianta testa bāzlīnijai: ja tests prasa pilnu sakritību, tam jāsāk ar 5 zināmām izņēmuma rindām, citādi tas ir sarkans no pirmās dienas.

**Pēda:** `data/{fix,rollback}_brief505_kvc_termini_2026-08-27.sql` (rollback mutācijas-pārbaudīts abos virzienos, round-trip atgriež 41 848 B baitu precīzi).

### [OPEN] `get_pending_politicians(days=1)` neredz VECU doku, kas iegūst jaunu `subject` slotu (2026-09-06)

Štekerhofa (pid 209) reaktivācija 09-07 padarīja doc 90283 (web, 2026-08-19) par viņa `subject` doku ar `reviewed_at IS NULL`, bet rinda skatās dienas logu pēc dokumenta laika, tāpēc doks tajā neparādījās; handoff to gaidīja «pirmo reizi rindā». Apstrādāts ar rokas dispatch (doc id promptā), zīmogs sedz visus trīs junction pid. Klase: jebkurš slota statusa/lomas maiņas gadījums (reaktivācija, `feed_type` maiņa, junction pāratribūcija) atstāj vecos dokus ārpus `days=1` loga uz visiem laikiem. *Mērījums vajadzīgs:* `SELECT COUNT(*) FROM document_politicians dp JOIN documents d ON d.id=dp.document_id JOIN tracked_politicians tp ON tp.id=dp.politician_id WHERE dp.role='subject' AND d.reviewed_at IS NULL AND tp.relationship_type='tracked' AND d.scraped_at < DATE('now','-1 day')` — cik tādu ir un vai tie ir tie paši 6 493 backlog doki. *Rīcība (izvēle):* pēc katras slota reaktivācijas palaist vienreizēju `days=N` ekstrakciju tam pid, vai pievienot rutīnas statusam rindu «subject doki bez `reviewed_at` ārpus dienas loga, N». *Īpašnieks:* orkestrators.

### [OPEN] Vēstneša ingest pienāk PĒC analīzes loga — 32 no 34 augusta palaidieniem pēc 15:00

> **Ieraksta pirmā puse SLĒGTA 2026-09-07** (verdikts 39, CHANGELOG 2026-09-07 (5)): izpildīts variants (b) — `src/routine.py::vestnesis_acts_for()` uzrāda orkestratoram dienas Vēstneša dokus, kuru virsraksts sākas ar «Ministru kabineta» / «Saeimas» / «Valsts prezidenta», ar saucēju «N no M Vēstneša dokiem dienā»; nepatiesie komentāri `src/analyze.py` un `src/scope.py` pārrakstīti ar mērījumiem (2 149 doki 30.04.–04.09., ≈ 800 sludinājumu klases, 11 claims no visas platformas jebkad, 465 doku virsrakstā MK / Saeima / rīkojums / likums). Vārts nostrādāja uz dzīviem datiem tieši 2026-08-26 (doc 95670). Divi ieraksta apgalvojumi izrādījās nepatiesi paši par sevi: pārskata sadaļa «Šodien izsludināts» ir izmesta 2026-08-03 (`60c878f4`), un filtrs NEKAD nebija spogulēts `src/scope.py`.

**Kas paliek atvērts, un tikai tas:** ievākuma LAIKS. Vēstneša ingest strukturāli pienāk pēc analīzes loga — **32 no 34 augusta palaidieniem pēc 15:00**, 08-26 palaidiens 23:38:54. Vārts uzrāda aktu tajā pašā vakarā, bet ievākumu agrāk nepārceļ, tāpēc dienas pārskata rakstīšanas brīdī akts joprojām var vēl nebūt korpusā.

*Rīcība:* pārcelt `platform='vestnesis'` ievākumu uz rīta ķēdi, vai apzināti pieņemt, ka Vēstneša akts pārskatā ienāk nākamajā dienā, un to pierakstīt. Pirms izvēles pārmērīt palaidienu laikus ar nosauktu vaicājumu — augusta skaitlis ir vienas mēneša izlases. *Īpašnieks:* operators.

### [FIX] Paralēlos ekstrakcijas aģentus dala PA POLITIĶIEM, nekad pa viena politiķa dokumentiem (2026-08-25)

**Cena bija reāls dublikāts.** 08-25 rutīnā orkestrators sadalīja Baibu Bražu (pid=15, 20 doku) starp diviem paralēliem aģentiem **pa dokumentiem** (10+10), lai neviens neatdurtos pret 12 doku circuit breaker. Abi aģenti korekti izpildīja ±5 d `get_existing_claims()` pārbaudi — un tā tik un tā bija akla: otrā aģenta pārbaude nostrādāja **67 sekundes pirms** pirmā aģenta ieraksts kļuva redzams (#704058 `created_at` 22:56:30, #704060 22:57:37). Rezultāts — viena izteikuma divas rindas, ko `store_claim()` idempotence neredz, jo trijnieks ir `(opponent_id, source_url, topic)` un `source_url` atšķīrās (viņas pašas tvīts pret @Arlietas releju).

**Noteikums:** viena politiķa dokumenti iet VIENAM aģentam. Ja rinda pārsniedz circuit breaker, tad vai nu apstrādā tikai cap ietvaros un atlikums atgriežas nākamajā dienā, vai otrajam aģentam liek ±5 d pārbaudi atkārtot **tieši pirms** `save_analysis`, ne partijas sākumā. Sadalīšana pa politiķiem šo klasi izslēdz pēc konstrukcijas.

*Pēda:* `data/{fix,rollback}_claim704060_dublikats_2026-08-25.sql` (#704060 atsaukts, orfāna vektors dzēsts atsevišķi).

### [OPEN] Divvalodu un daudzizdevumu dublikāti — `store_claim()` idempotence tos neredz pēc konstrukcijas (2026-08-25)

Viens izteikums ienāk korpusā vairākas reizes ar **atšķirīgu `source_url`**, tāpēc idempotences trijnieks `(opponent_id, source_url, topic)` nesaskaras. Vienīgais strādājošais vārts ir ±5 d `get_existing_claims()` satura salīdzinājums.

**Saucējs vienā dienā (08-25):** noķerti **12 dublikāti** — 5 junction-atgūšanas aģentā J1 (Valainis ×2, Augulis, Ašeradens, Kučinskis), 2 J2 (Rinkēvičs #690433, Kulbergs #690491), 2 Kulberga slotā (#704018, #704017), 1 Butānam (#704043), 1 Smiltēnam (#704008/#704006), 1 Latvijas Bankai (#704000/#704001).

**Trīs apakšformas:**
- **Divvalodu tvīts** — Kols publicēja LV un EN versiju ~45 s starpībā (doc 94401 / 94400).
- **Viens notikums, vairāki izdevumi** — tā pati valdības sēde vai preses konference lsm.lv, diena.lv, nra.lv, jauns.lv un leta.lv versijās.
- **Paša RT par savu tvītu** — Bražes doc 91859 radīja #703870 kā #690485 dublikātu.

*Rīcība:* pieraksts, ne kods — ±5 d pārbaude šo klasi tur, kamēr tā ir KATRĀ dispatch promptā. Ja kādreiz taisa kodu vārtus, atslēga nevar būt URL. *Īpašnieks:* operators.

### [OPEN] Konteksta blokos nosaukti audience runātāji bez avota saites
Dienas pārskatu konteksta blokos (no tendenču piezīmēm) tiek nosaukti runātāji, kuru pozīcijas ir audience kontos (`journalist`/`neutral`/`organization`), un tēmu tabulas tos pēc konstrukcijas neemitē (`briefs.py` audience filtrs). Rezultāts: apgalvojums ir tekstā, avota saites lapā nav nekur, lai gan `claims.source_url` DB eksistē. Brief #387 gadījumi: Vītols (Rail Baltica blokā), Kļaviņš (Papildu konteksta blokā). Tas atduras pret koplietoto noteikumu „katram pieminētam apgalvojumam jābūt `source_url`" (`wiki/operations/agenti/brief-shared-rules.md` § Avoti). Kandidāti: (a) tendenču rakstīšanas solī pievienot saiti pie audience runātāja; (b) skeletam emitēt mazu „Komentētāji" tabulu ar saitēm zem Neitrāli rindas; (c) apzināti pieņemt kā normu un noteikumā ierakstīt izņēmumu. Saistīts: blokU „Neitrāli N" rinda `Koalīcija vs Opozīcija` tabulā ir vienīgā vieta, kur tie N skaitās, un tie neparādās nekur citur pārskatā.

### [OPEN] Tendenču piezīmēs kaili claim ID (`#NNNNNN`)
Piezīmes #384–386 (2026-07-29) satur inline `(#555764)` formas atsauces. Skelets konteksta blokus ievelk verbatim, tāpēc tie nonāk līdz publiskajam pārskatam, kur DB ID ir aizliegti (`brief-writer` self-check #9). Brief #387 tos nofiltrēju ģenerētajā tekstā (DB piezīmes neaiztiktas — tās ir append-only). Kamēr tendenču rakstīšana turpina likt ID, katrs nākamais pārskats manto to pašu darbu. Fix vietas: vai nu tendenču rakstīšanas konvencija (aprakstošas atsauces, kā prasa noteikums pretrunām), vai `briefs.py` filtrs konteksta blokiem pirms emisijas. Salīdzinājumam: brief #383 bija 0 kailu ID, tāpēc tas nav vispārējs paterns, bet 07-29 sesijas paraksts.

### [FIX] Divi mazāki matcher/konfigurācijas robi (2026-08-02)

- **Doc 78807 nesasaista Alvi Hermani**, lai gan tekstā burtiski stāv „Alvis Hermanis:" (Mielava tvīts, kas citē Hermani). Junction tam ir tikai pid=49. Sasaiste būtu `mentioned` un lēmumu nemainītu, bet `name_forms` caurums ir reāls.
- (Otrais šīs partijas ieraksts — Žuravļeva `feed_type` — slēgts 2026-08-16 un saspiests uz § Ne-darīt.)

### [OPEN] Ārpolitikas tēmas confidence drift +0,18 — 07-10 skaitlis joprojām nav pārmērīts

> **Detektora daļa SLĒGTA 2026-09-07** (verdikts 26, CHANGELOG 2026-09-07 (3)): `check_confidence_drift()` klusē, kad kādā pusē ir mazāk par 5 claims (`_MIN_HALF_CLAIMS`, agrāk 3), un katra brīdinājuma rinda — gan atskaitē, gan rutīnas statusā — iet caur `format_drift_line()`, kas rāda n abās pusēs. Vārti: `tests/test_confidence_drift.py` (12 testi, t.sk. n=4 klusēšana un n=5 robeža); krišana pirms labojuma pierādīta ar palaidienu.

**Kas paliek atvērts:** pats **2026-07-10 skaitlis** (`Ārpolitika` claim `confidence` 0,63 → 0,82) nekad nav pārmērīts, un mērījuma vaicājums nav pierakstīts, tāpēc skaitlis pats ir hipotēze. 08-24 «Degviela un enerģētika +0,23» gadījums to nepierāda un neatspēko — tas bija cita tēma un divi n≤3 paraugi (vaicājums: `SELECT DATE(created_at), COUNT(*), ROUND(AVG(confidence),2) FROM claims WHERE topic=? AND claim_type='position' AND created_at>=? GROUP BY 1`).

*Rīcība:* pirms jebkādas rīcības palaist to pašu vaicājumu par `Ārpolitika` ar 2026-07 logu; ja abās pusēs n<5, rinda aiziet uz `BACKLOG.md` § Ne-darīt ar skaitli. *Īpašnieks:* operators.

### [OPEN] `find_inversions` — trīs defekti vienā predikātā (aklā zona, viltus inversija, mūsu paša saturs)

> **Divi ieraksti apvienoti 2026-09-05.** 09-03 un 09-04 tie tika pieteikti atsevišķi, bet abi maina VIENU un to pašu kandidātu kopu un vienu un to pašu `speaks()` predikātu — jebkurš koda labojums skar abus, un divi ieraksti lika klasei izskatīties pēc diviem maziem darbiem, ne pēc vienas kopas definīcijas.

**(b) Runājošs `subject` tiek uzskatīts par inversiju (2026-09-04).** Doc **99611**: subjekts Alvis Hermanis runā pats un kritizē Kulbergu, Kulbergs tekstā tikai pieminēts — bet funkcija to atgrieza kā inversiju (citēts `mentioned` bez runājoša `subject`). Ja `speaks()` lomu nosaka pēc pieminējuma, ne pēc runas akta, šī klase atkārtosies katrā palaidienā. Mērogs 2026-09-04: **5 inversijas no 110 pārbaudītiem dokumentiem**, no tām 3 tvītu joslā viltus pozitīvas — 99611 (šī klase); 99637 (mūsu pašu @AtminaLV agregācijas tvīts, ko retvītojis Pūpols, t.i. cirkulāra pašcitēšana); 100551 (partijas konta RT ar intervijas citātu).

**(c) Mūsu paša konta saturs jāizslēdz no kandidātu kopas.** @AtminaLV tvīts, kurā apkopotas politiķu pozīcijas, pēc uzbūves izskatās kā «citēts runātājs bez runājoša subjekta». Tas ir tas pats kandidātu-kopas jautājums, kas (a), tikai no otras puses.

**(a) Aklā zona — doki ar `mentioned`, bet BEZ neviena `subject`.**

**Trigeris (2026-09-03):** junction apsekojumā mans neatkarīgais ekspozīcijas vaicājums (bez platformas filtra, kā prasa `/dienas-rutina`) atrada **86 dokumentus** ar ne-organizācijas `mentioned` politiķi; `find_inversions(days=1)` pārbaudīja **42**. Starpība — **44 doki, no tiem 42 `twitter`** — ir strukturāli neredzama: kandidātu kopa prasa `EXISTS(... role='subject' ...)`, tāpēc doks, kuram nav NEVIENA subjekta, joslā neienāk nekad.

**Kāpēc tas nav tas pats, kas jau zināmais:** 2026-08-27 labojums paplašināja PLATFORMAS (`DEFAULT_INVERSION_PLATFORMS`), ne šo predikātu. Doks bez subjekta nav „inversija" pēc definīcijas — bet tieši tāpēc citēts runātājs tur nav atgūstams ne pirmajā joslā (nav subjekta), ne otrajā (nav inversijas). Tā ir trešā klase, ne šīs paplašinājums.

**Pirms rīcības izmēri ražu, nevis mērogu.** 44 doki nav 44 pozīcijas: tvītu joslā ~puse atradumu ir viltus pozitīvi, un tos dominē satīra (`find_inversions` docstring, 08-27 mērījums). Iespējams, pareizā atbilde ir „neko nedarīt" — bet tad tas pieder § Ne-darīt ar skaitli, ne paliek neizmērīts.

**Rīcība:** vienreizēja triāža — paņem šos 42 tvītu dokus, cik no tiem satur atribuētu izteikumu no sekota politiķa, kas korpusā NAV. Ja raža < ~10 %, raksti verdiktu § Ne-darīt; ja augstāka, tad predikāts jāpaplašina.

**Secība, kas izriet no apvienošanas:** (b) un (c) sašaurina kandidātu kopu, (a) to paplašina. Tāpēc (b)+(c) jālabo PIRMS (a) ražas mērījuma — citādi (a) triāžā tiek skaitīti tie paši viltus pozitīvie, kurus (b) izmet, un skaitlis nozīmē kaut ko citu, nekā izskatās.

**Lēmumu īpašnieks:** operators (izmeklēšana pirms koda).

### [DEFERRED] Pretrunu kandidātu retrospektīvs griezums — `contradiction_candidates` tabula, ja izrādās vajadzīga

Panelis pats IZPILDĪTS 2026-09-04 (`83546921`) un pierakstīts CHANGELOG 2026-09-05; ieraksts šeit sašaurināts uz atlikumu. Nesējs ir `logs.details` lauks `rejected_candidates`, ne jauna tabula — `logs` ir liela tabula un `details` ir JSON, tāpēc retrospektīvs griezums («visi kandidāti par Jurēvicu kopš jūnija») ir SKENĒJUMS, ne vaicājums.

**Sliekšņa nosacījums, ne uzdevums:** ja operators sāk lasīt kandidātus nedēļas griezumā, tas ir arguments par `contradiction_candidates` tabulu ar `verdict` kolonnu. Kamēr tāda lasījuma nav, tabula būtu mašinērija bez pieprasījuma. *Īpašnieks:* operators.
