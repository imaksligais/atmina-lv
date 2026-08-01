# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

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

### [OPEN] Krists Avots kā premjera balss — atribūcijas lēmums
2026-07-30 rutīnā trīs doki (76582, 76588, 76600 — NTSP minimālā alga + kiberdrošības briefings) bija Kulberga subject-doki, kuros runā tikai viņa parlamentārais sekretārs Krists Avots; Kulbergs nav citēts. Ekstrakcijas aģenti tos konsekventi marķē empty (pareizi pēc pašreizējiem noteikumiem — nav pirmās personas izteikuma). **Operatora lēmums 2026-08-05 (deleģētā ieteikumu izpilde): (a) status quo** — premjera biroja paziņojumi caur sekretāru nav Kulberga pozīcijas; pārskatīt tikai tad, ja paterns kļūst regulārs (tad kandidāts ir (b) sēt Avotu kā atsevišķu entītiju). Nekas datos nav mainīts.

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

### [SLĒGTS 2026-08-19] fasttext lid-modeļa nepieejamība → LV-diacritics vārti vaļā
SLĒGTS 2026-08-19 (vārtu vilnis 2): lid.176 vendorēts (`tests/calibration_results/lid.176.ftz`, izsekots gitā), `_get_ft_model()` repo-relatīvs + atomāra retry ielāde; vārti vairs neatkarīgi no tīkla/HF. Pieraksts CHANGELOG 2026-08-19.

### [FIX] Idempotences kluso merge — vairāki distinkti claims no viena (pid, url, topic)
Viens dokuments ar vairākām distinktām viena topika pozīcijām → otrā+ klusi sapludinās (Data Contract #3, T2). **(a) IEVIESTS 2026-07-25:** `save_analysis` ziņo `silent_dedup` + `status=partial` viena izsaukuma ietvaros (4 testi `tests/test_silent_dedup.py`); **(c) IEVIESTA 2026-08-05** — claim-extractor konsolidācijas vadlīnija. **Paliek atvērts (b):** stance-hash dimensija idempotences atslēgā — mainītu Data Contract #3, prasa atsevišķu lēmumu.

### [FIX] Partijas piederības maiņa ziņās nesinhronizējas ar tracked_politicians.party
T6 klase: partijas maiņas claim nesinhronizē `tracked_politicians.party` (Verginas gadījums 06-29, `data/fix_vergina_left_jv_2026-06-29.sql`). **(a)+(b) IEVIESTI 2026-08-05:** claim-extractor „Party-change signal check", brief-writer self-check 16, daily-routine solis. **Paliek (c):** datēta `party_history` tabula, ja vēsturiskā precizitāte kļūst svarīga; pa to laiku manuāla UPDATE + pāra rollback, amata/partijas hronoloģiju pārbaudot manuāli (Ingas Bērziņas mācība — CHANGELOG arhīvs 2026-06-11).

### [OPEN] Konteksta blokos nosaukti audience runātāji bez avota saites
Dienas pārskatu konteksta blokos (no tendenču piezīmēm) tiek nosaukti runātāji, kuru pozīcijas ir audience kontos (`journalist`/`neutral`/`organization`), un tēmu tabulas tos pēc konstrukcijas neemitē (`briefs.py` audience filtrs). Rezultāts: apgalvojums ir tekstā, avota saites lapā nav nekur, lai gan `claims.source_url` DB eksistē. Brief #387 gadījumi: Vītols (Rail Baltica blokā), Kļaviņš (Papildu konteksta blokā). Tas atduras pret koplietoto noteikumu „katram pieminētam apgalvojumam jābūt `source_url`" (`wiki/operations/agenti/brief-shared-rules.md` § Avoti). Kandidāti: (a) tendenču rakstīšanas solī pievienot saiti pie audience runātāja; (b) skeletam emitēt mazu „Komentētāji" tabulu ar saitēm zem Neitrāli rindas; (c) apzināti pieņemt kā normu un noteikumā ierakstīt izņēmumu. Saistīts: blokU „Neitrāli N" rinda `Koalīcija vs Opozīcija` tabulā ir vienīgā vieta, kur tie N skaitās, un tie neparādās nekur citur pārskatā.

### [OPEN] Tendenču piezīmēs kaili claim ID (`#NNNNNN`)
Piezīmes #384–386 (2026-07-29) satur inline `(#555764)` formas atsauces. Skelets konteksta blokus ievelk verbatim, tāpēc tie nonāk līdz publiskajam pārskatam, kur DB ID ir aizliegti (`brief-writer` self-check #9). Brief #387 tos nofiltrēju ģenerētajā tekstā (DB piezīmes neaiztiktas — tās ir append-only). Kamēr tendenču rakstīšana turpina likt ID, katrs nākamais pārskats manto to pašu darbu. Fix vietas: vai nu tendenču rakstīšanas konvencija (aprakstošas atsauces, kā prasa noteikums pretrunām), vai `briefs.py` filtrs konteksta blokiem pirms emisijas. Salīdzinājumam: brief #383 bija 0 kailu ID, tāpēc tas nav vispārējs paterns, bet 07-29 sesijas paraksts.

### [OPEN] NBS amata-apzīmējuma klase: amats kā `name_form` trāpījums, viens un tas pats runātājs

Izmērīts 2026-08-01/08-02. pid=204 („Latvijas armija (NBS)") slotā 07-31, 08-01 (×2, doki 78102 un 78096) un 08-02 nonāca `la.lv` raksti, kuros „NBS" un „Nacionālo bruņoto spēku" parādās TIKAI Jāņa Slaidiņa amata apzīmējumā — *„NBS majors un Zemessardzes štāba virsnieks Jānis Slaidiņš"* —, un runā privātpersona militārā analītiķa lomā. `name_forms` satur abas formas, tāpēc matcher organizācijas slotam piešķir `role='subject'`, lai gan NBS kā institūcija tekstā nepauž neko. Visas četras reizes ekstrakcijas aģents dokumentu korekti atzīmēja tukšu — t.i. vārti tur, bet iestādes slots katru dienu saņem darbu, kas tam nepieder. Klase atkārtosies bieži: Slaidiņš ir regulārs komentētājs presē.

Tas **nav** tas pats, kas CVK programmu gadījums (§ Matcher): tur „armija" ir tēmas piesaukums, šeit — cilvēka amats. Slaidiņš **nav** izsekota persona, tāpēc saturam nav cita leģitīma adresāta — tas ir korekti atmetams, ne pārvietojams.

**Verdikts 2026-08-17: virziens (a) — sēt Slaidiņu kā atsevišķu entītiju** (`/seed-entity`; izpildes rindā § Operatora verdikti). Vēsturiskie divi virzieni, abi operatora: (a) sēt Slaidiņu kā atsevišķu entītiju (atsevišķs seeding lēmums); (b) `negative_patterns` pēc amata konstrukcijas. **Brīdinājums pirms (b) — operatora review, ne auto-add:** paterns pēc amata (`NBS majors`, `NBS virsnieks`) ir plašāks, nekā izskatās — „NBS komandieris" blakus ĪSTAM institucionālam paziņojumam trāpītu zem tā paša paterna. Formulējums jāizvēlas šauri un jāpārbauda pret vēsturiskajiem 204. slota dokumentiem.

### [FIX] Divi mazāki matcher/konfigurācijas robi (2026-08-02)

- **Doc 78807 nesasaista Alvi Hermani**, lai gan tekstā burtiski stāv „Alvis Hermanis:" (Mielava tvīts, kas citē Hermani). Junction tam ir tikai pid=49. Sasaiste būtu `mentioned` un lēmumu nemainītu, bet `name_forms` caurums ir reāls.
- (Otrais šīs partijas ieraksts — Žuravļeva `feed_type` — slēgts 2026-08-16 un saspiests uz § Ne-darīt.)

### [OPEN] Ārpolitikas tēmas confidence drift +0,18 — neizmeklēts
2026-07-10 rutīnas statusā `Ārpolitika` tēmas claim `confidence` pārlēca 0,63 → 0,82 bez zināma iemesla; toreizējā hipotēze bija avotu sastāva maiņa. Nekad nav izmeklēts, un mērījuma vaicājums nav pierakstīts, tāpēc skaitlis pats ir hipotēze — pirms rīkoties, pārmēri ar nosauktu vaicājumu un nosauktu logu. (Pārcelts šurp no § Avoti 2026-08-05.)

