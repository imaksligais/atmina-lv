# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## Dati / DB

> Shēma, denormalizācijas dreifs, tēmu taksonomija, vektori, laikspiedoli.

### [OPERATOR] 2026-08-13/14 rutīnas atlikumi — nebloķējoši, katrs savs lēmums

Pieteikti 08-13 rutīnā un 08-14 sesijā; publicēto neietekmē. Skaitļi pārmērīti 2026-08-14 ar nosauktiem vaicājumiem:

- ~~**[OPERATOR] #689539 (Šnore) citāta bagātināšana**~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (8)): `quote` aizpildīts burtiski ar paša tvīta 12.08. tekstu (doc 86486) + provenance piezīme reasoning; `data/{fix,rollback}_claim689539_quote_2026-08-21.sql`.
- **[OPEN] Nereviewed subject-doku uzkrājumi ārpus `days=1` loga.** Vaicājums: `SELECT tp.name, COUNT(*) FROM documents d JOIN document_politicians dp ON dp.document_id=d.id AND dp.role='subject' JOIN tracked_politicians tp ON tp.id=dp.politician_id WHERE d.reviewed_at IS NULL AND tp.relationship_type!='inactive' GROUP BY tp.name ORDER BY 2 DESC` → top: LETA 503 (audience-relejs, zema vērtība), Kulbergs 136, Lapsa 106, Kučinskis 61, Siliņa 57, Rinkēvičs 55, Kļaviņš 49, Braže 49. Dienas rutīna tos nekad nesasniegs; kandidāts — mērķēts sweep pa politiķim (ne LETA) vai `historic-backfill` loga paplašinājums.
- **[OPERATOR] Video kandidāti @video-extractor:** Kola LTV intervija, Briškena airBaltic video (08-13 ingest pieteikumi; sk. § Video ingest par diarizācijas limitu).

### [OPERATOR] Citātu integritātes atlikums — klases (a)–(e)

- **(a) Pārskrāpēšanā zudušie citāti — SLĒGTS 2026-08-05** ar `/audit-integrity` 17. pārbaudi (bāzlīnija `checked=30 flagged=11` no 1 418 web citātiem; pieņemtie ID pierakstīti pašā pārbaudē; pieraksts CHANGELOG 2026-08-05). Klase kustas ABOS virzienos, tāpēc gaidāmā vērtība ir saraksts, ne skaitlis: jauns ID ārpus saraksta = svaigs zudums → per-citāta triāža (labot pret jauno redakciju — Butāna precedents — vai pieņemt un pierakstīt). (a2)/(a3) atkrīt, kamēr 17. pārbaude tur.
- **(b) T4 atlikums — 4 citātu jautājums SLĒGTS 2026-08-05**; **#7019/#7397 (+#7022, #6954) SLĒGTI 2026-08-18** (T4 kvartets: stance/reasoning diakritika atjaunota, `quote` visiem 4 izrādījās burtiski korekts avotā un nav aiztikts; `data/{fix,rollback}_t4_claims_quartet_2026-08-18.sql`, re-embed 3 rindām; CHANGELOG). Atlikušais #7397 marķiera jautājums → § Operatora verdikti Deep-check blakuskarogi.
- **NEAIZTIEC #1595** („Ir balts gulbis, melns gulbis, bet mums ir atlidojis rudais gulbis") — avota dokumentā teksts ir TIEŠI tāds, tātad zemā diakritika ir runātāja. Dokumentēts vārtu viltus pozitīvs; vārti to karos mūžīgi.
- **Partiālā bojājuma klase (mērīta 2026-08-02):** diakritiku vārti ir ATTIECĪBAS tests, tāpēc teikums ar vienu bojātu vārdu tos iziet. Zonds pār 87 sekoto personu uzvārdiem ar diakritiku: `stance` 2 (abi laboti), `reasoning` 24 (iekšējs lauks, zema prioritāte), `quote` 3 (prasa avota salīdzinājumu, ne aklu labošanu). **Brīdinājums mērītājam:** ierobežo zondu uz PERSONU uzvārdiem un izslēdz organizācijas — pirmais zonds deva 182 „trāpījumus" `stance` laukā, un visi bija artefakts, jo „Kas Notiek Latvijā" ir sekota entītija un katrs pareizais nominatīvs „Latvija" izskatījās nodiakritizēts.
- **(c) 1 408 citāti paliek ārpus pārbaudāmās klases.** Vārti (`validate_quote_against_source()`) un 20 vēsturisko rindu labojums pabeigti 2026-08-03 (pilns pieraksts CHANGELOG). Paliek tas, ko vārti apzināti NEsedz: 1 408 citāti avotā nav atrodami burtiski (angļu valoda, izlaidumi `(..)`, tipogrāfiskās pēdiņas, pāratjaunots korpuss) — tā nav defektu kopa, un rejektēšana tur bloķētu īstas pozīcijas (mērīts: attiecības vārti būtu nostrādājuši uz 6 rindām no 1 408, tāpēc atkāpšanās noraidīta), bet nozīmē arī, ka fabricētu citātu neverificējamā dokumentā neviens vairs neķer. Renderu citāta labojums pēc noklusējuma NEprasa — sk. § Ne-darīt punktu „Citātu labojumam NEplāno renderu pēc noklusējuma".
- **(d) Citātu-avota atbilstības aste — 37 vājie + bojātā 2026-04-09 partija (izmērīts 2026-08-05).** Zonds ar agresīvu normalizāciju pār 5 022 claims: 4 551 burtiski, 434 daļēji, **37 zem 50 % vārdu seguma** (starp tiem īsti žurnālista-naratīva gadījumi #12, #153, #144, #119, #11004; bet īsi/svešvalodu citāti sodīti nepelnīti — #17856, #11143). **Rindu-pa-rindai triāža, ne bulk.** Kopīgs cēlonis daļai: 04-09 16:41–16:45 ekstrakcijas partija (133 claims) ir viena bojāta sesija. Zondi pārrakstāmi no šī apraksta.
- **(e) Pieturzīmju atkāpe — 179 rindas ar ekstraktora termināļa punktu (mērīts 2026-08-08).** `_normalise()` noņem pieturzīmes pirms salīdzināšanas, tāpēc rīks klasi neredzēja; atsedza #689330 (dok. 82800) ar tiešu `instr()` testu. Mērījums (saucējs 5 128): 569 iziet `_normalise`, bet krīt burtiskajā testā → 241 kosmētika, 179 termināļa pieturzīme, 149 lūst vidū. Metode: `quote IN content` burtiski pret normalizēto; reproducējams. **RĪKA SOLIS IEVIESTS 2026-08-09** (CHANGELOG (6)): klase 6 `verbatim` ar savu saucēju, 3 testi caur `store_claim`. **Paliek datu puse: 179 rindu triāža — ne bulk-fix**, katra prasa avota salīdzinājumu (sk. (d) atrunu).

### [OPERATOR] LETA URL satura nomaiņa pēc izvērtēšanas — doc 72446 title≠content, claim #553929 bez sava pierādījuma (2026-08-06)

**Instances labojums IZPILDĪTS 2026-08-09** (CHANGELOG (5)). **Klases koda lēmumi IZPILDĪTI 2026-08-18** (CHANGELOG; `insert_document` UPDATE zars pārraksta `title` un atiestata `reviewed_at` pēc satura maiņas; identisks re-fetch zīmogus nededzina). **Paliek [OPERATOR]: 17 title≠content kandidātu triāža** (vēsturiskie nav atpakaļejoši laboti). Saistīts ar `documents.scraped_at` MUTABLE invariantu (CLAUDE.md) — **kopš 2026-08-09 tas dokumentē arī claims/junction novecošanu**, ne tikai dienas skaitītāja efektu, un nosauc `scraped_at > reviewed_at` + `title` ≠ pirmā satura rinda kā šīs klases parakstu.

### [OPERATOR] Deep-check 1. viļņa datu defekti — apgrieztas stances, aplams publicētas pretrunas datējums, name_forms robi (2026-08-06)

Deep-check vilnis (5 hunteri + DA) blakus kandidātiem atrada rindu-defektus. #17807, pretrunas #25/#29/#30 — IZPILDĪTI 2026-08-09 (CHANGELOG (5)). **Paliek atvērti (katram pāra rollback + re-embed, ja mainās stance):**

- **#548003 (Braže) stance pašapgriezusies — IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (3)): avots doc 65306 apstiprināja inversiju; jaunā stance burtiski pēc avota, re-embed MAINĪJĀS; `data/{fix,rollback}_braze_548003_stance_2026-08-21.sql`. Verdikta rinda izgriezta no § Operatora verdikti.
- **vote_id 3438 (185/Lp14) `summary` inversija — APSTIPRINĀTA UN LABOTA 2026-08-21** (CHANGELOG 2026-08-21 (8)): stenogramma (transcripts/view/2448) fiksē Rokpeļņa runu "par 15 centiem litrā samazināt akcīzes nodokli" — glabātais "Paaugstina..." bija apgriezts. `data/{fix,rollback}_vote3438_summary_2026-08-21.sql`; claims nav skarti (stances mehāniski, kopsavilkumu neietver).
- **`name_forms` robi — Melnis + Dombrava IZPILDĪTI 2026-08-18** (CHANGELOG); ~~id=151 Rasimai nav ne `x_handle`, ne `social_accounts`~~ **IZPILDĪTS 2026-08-21** (CHANGELOG 2026-08-21 (9)): `leilarasima` seedēts (x_handle + social_accounts first_party).

### [FIX] `review_status` trigera substring-kolīzijas — abi virzieni novēroti vienā dienā (2026-08-05)

Trigeris atvasina statusu no `reasoning` teksta ar `LIKE '%...%'`, tāpēc marķiera VĀRDS jebkur tekstā maina statusu. Abi virzieni piedzīvoti 08-05 rutīnā un laboti (`data/{fix,rollback}_review_status_trigger_collisions_2026-08-05.sql`): **#689220** — `save_analysis` netiešās atsauces vārtu frāze `tikai pieminē` trāpīja teikumā par SIŽETU, ne politiķi → viltus `needs_review`; **#689217** — precedenta citāts „#555717 Izvērtēts 2026-08-03" reasoning tekstā → jauns claim atvasināts `reviewed`, kaut neviens to nav izvērtējis. Mērījuma augšējā robeža: 337 `reviewed` rindas ar marķieri teksta vidū (lielākoties leģitīmas; tikai #689217 apstiprināts viltus pēc autorības). Kandidāti: (a) `claim-extractor` prompta noteikums — citējot precedentu, nekad nerakstīt burtisko rezolūcijas marķieri (rakstīt „operatora lēmums YYYY-MM-DD"); (b) vārtu frāzes tuvuma prasība (frāze pie politiķa atsauces, ne jebkur). Trigera pozīcijas enkurošana apzināti NAV kandidāts — marķiera pozīcija drīkst dreifēt (CLAUDE.md eskalācija 2).

### [FIX] Denormalizēto lauku novecojumu partija (2026-08-05 rutīnas atradumi)

**Statuss pēc 2026-08-18 T6 batch-verifikācijas: SADAĻA SLĒGTA.** (a) 168, (b) 192, (c) 163+165, (e) 99, (f) 154 izpildīti `data/fix_t6_batch_2026-08-06.sql`; (d) 119 Pleškāne izpildīts 2026-08-13 (`data/rollback_pleskane_party_2026-08-13.sql`); **(g) Ābramas `party` SLĒGTS 2026-08-18 → `NULL`** (operatora lēmums: 08-18 verifikācijā ZZS ārējos avotos neapstiprinājās, un avoti nesaskan par pareizo vērtību — jauns.lv 2025-06-19: pameta tikai frakciju; puaro.lv CV: «pie frakcijām nepiederoša» — tāpēc neapgalvojam neko; `data/{fix,rollback}_abrama_party_2026-08-18.sql`). Faktu piezīme paliek: `faction='ZZS'` nav plāns artefakts — 2026-03-26 tas ir 44 no 70 balsojumiem un 2026-04-01 21 no 23, t.i. divas sēžu dienas ar segumu, un tikai tās.

Visu deviņu gadījumu (a)–(i) apraksti izgriezti 2026-08-19 — izpildes pieraksti CHANGELOG 2026-08-06 (T6/citātu batch, t.sk. #553943 `quote`→NULL un T4 trijnieks) un 2026-08-18 (T6 batch-verifikācija). Paliek viena palieka, kurai CHANGELOG ieraksta nav: doc 76612 saturā ir nulles-rindu korupcija („Vīķi-000…Freibergu", skrāpēšanas defekts) — doks tukšs, tāpēc nekaitīgs.

### [OPERATOR] 2026-08-15 rutīnas datu defekti — viena apgriezta stance, divi `role` lauki

Trīs atradumi no 38 aģentu ekstrakcijas viļņa. **(c) izpildīts 2026-08-16; (a) pārmērīts un pārkvalificēts; (b) paliek atvērts.**

**(a) #20597 (pid=26 Atis Švinka, PRO) — NAV stance defekts. Pārmērīts 2026-08-16; abas sākotnējās hipotēzes ATSPĒKOTAS.** Avota doks 38416 (viņa paša konts `atis_svinka`, `feed_type='first_party'`, 2026-05-19) satur burtiski: *«Tikmēr Latvijā koalīcijas partneri @Progresivie ierosinājumu par 50% atlaidēm vilcienu abonementiem neatbalstīja.»* Stance ir uzticams šī teikuma atstāstījums, tāpēc (i) «ekstrakcija apgriezusi subjektu/objektu» un (ii) «stancē nepareizi nosaukta partija» abas krīt — partijas nosaukums nāk no avota. **Nelabo stanci un netērē re-embed** (tas bija sākotnējais ieteikums; tas būtu bijis nepareiza mutācija).

Un Švinkas `party` arī NAV nepareizs: `saeima_individual_votes.faction` = PRO 4981 rindās no 2022-11-17 līdz 2026-07-23 (vienīgā izņēmuma rinda ir 2022-11-01 ar NULL), un viņa paša claims runā par Progresīvajiem pirmajā personā — #20472 «apliecina, ka Progresīvie jau 2025. gada novembrī vērsa uzmanību…», #20173 «uzsver kā Progresīvo prioritātes», #532387 par «Progresīvo» vēlēšanu sarakstu.

**Kas tātad PALIEK atvērts, un tas ir cits jautājums:** kāpēc PRO deputāta paša konts 2026-05-19 sauc Progresīvos par «koalīcijas partneriem». Tas ir jautājums par AVOTU (politiskā hronoloģija ap maija valdības maiņu vai citēta/pārpublicēta teksta klase), ne par mūsu ierakstu, un to šķir operatora zināšanas, nevis vēl viens DB vaicājums. Līdz tam DB nekas nav maināms.

**Švinkas `role` — LABOTS 2026-08-18** (atsevišķs lauks no augšminētā; 08-17 rutīnas piezīme). `role='Satiksmes ministrs (demisionējis)'` bija novecojis: ministra amats beidzās 2026-05-28 (pārņēma Kozlovskis), un 2026-06-04 viņš atgriezās Saeimā — lsm.lv 04.06.2026 (a650044) + puaro.lv «Bijušie ministri Ašeradens, Čudars un Švinka atgriežas Saeimā»; iekšēji saskan ar `faction='PRO'` 429 balsojumos kopš 2026-02-01 (pēdējais 2026-07-23). Jaunā vērtība `Saeimas deputāts`; `party` netika aiztikts. `data/{fix,rollback}_t6_batch_2026-08-18.sql`.

**(b) pid=165 Ķirsis — SLĒGTS 2026-08-18.** Verifikācija apstiprināja `role`: riga.lv `/en/council-management` (Kleinbergs — Chairman, Ķirsis — Deputy Chairman) + lv.wikipedia «Rīgas dome» (Kleinbergs kopš 2025; Ķirsis mērs 2023-08-17…2025-06-27, tagad vietnieks). Tātad visas trīs «Kā Rīgas mērs» stances ir datētas PĒC amata beigām un ir mūsu teksta amata fabrikācija — #17893/#20660/#521104 pārrakstītas uz «Rīgas domes priekšsēdētāja vietnieks», visas trīs re-embedotas (visiem trim vektors MAINĪJĀS). `role` netika aiztikts. `data/{fix,rollback}_t6_batch_2026-08-18.sql`.

Paliekošā terminoloģijas piezīme: «Rīgas domes priekšsēdētājs» IR mēra formālais tituls, tāpēc «priekšsēdētāja vietnieks» un «mērs» nav sinonīmi — tie ir divi dažādi amati.

**(c) pid=39 Aizupietis — IZPILDĪTS 2026-08-16.** `role='Burgers 66, restorāni'` (uzņēmējdarbības apraksts, ne amats) → `NULL`. Pareizā vērtība nav zināma un nav pārbaudāma ar mūsu datiem (0 rindu `saeima_individual_votes`, 1 claim), bet `NULL` ir pieņemta shēmas vērtība — pēc labojuma 17 izsekotiem profiliem `role IS NULL`. Fix + rollback: `data/{fix,rollback}_aizupietis_role_2026-08-16.sql`.

### [DEFERRED] "Aizsardzības industrija" topika splits
2026-06-10 topiku audits: Aizsardzība un drošība (~409 poz.) satur koherentu industrijas/iepirkumu klasteri (Ascod komplektēšana, lokalizācija, SAFE iegādes) ar saviem runātājiem — sakrīt ar 06-07 tendenci (piezīme #260). Splits = jauns kanoniskais topiks + aliasi + backfill + temas lapa. Ieviest, ja klasteris turpina augt vēlēšanu sezonā. Sk. CHANGELOG 2026-06-10.

### [FIX] Timestamp glabāšana nav standartizēta (mixed LV/UTC) — pusnakts-pārkares artefaktu saime
Sakne (2026-05-31): daļa kolonnu glabā LV (`now_lv()`), daļa UTC (`DEFAULT CURRENT_TIMESTAMP`). **Atvērts:** `DATE('now')`=UTC slazds SQL vaicājumos; ilgtermiņa fix = viena tz visur (liela migrācija). Četri saimes artefakti slēgti (CHANGELOG 07-25/07-30/08-01); konvencija pie kolonnām `src/schema.sql`; **klases vārti** = `tests/test_timestamp_timezone_gate.py` (lasa avota kodu, zonas ziņā neatkarīgs — uzvedības testu zaļā gaisma šai saimei nekad nav pierādījums, jo abas vides ir aklas katra pret savu virzienu).
**ATSAUKTS padoms (2026-07-30):** „spriedžu `created_at` uzstādīt uz rutīnas dienu" ir AKTĪVI KAITĪGS — LV zīmogs UTC kolonnā aizlec par +3h (spriedzes #175 forma, labota `data/{fix,rollback}_tension175_source_url_2026-07-30.sql`). Spriedzes rakstīt TIKAI caur `store_tension()`.

### [DEFERRED] `claim_vectors` bāreņi — 7 004 vektori bez `claims` rindas; claims bez vektora 0

**Pārmērīts 2026-08-18** (read-only, kopu starpība — vec0 tabulai ne JOIN): bāreņi 7 010 (08-05 bija 7 004; delta = starplaika dzēšanas), claims bez vektora 0. Pretējā puse SLĒGTA 2026-08-02 (CHANGELOG; 546 bez-vektora rindas — 100 % `saeima_vote`, viena neveiksmīga 04-05 embed partija). Ietekme kosmētiska: kNN var atgriezt mirušu `claim_id`. Ja tīra — pāra rollback + pārbaude, ka neviens lasītājs uz bāreņiem nepaļaujas. Tā pati klase kā 450 `document_vectors` bāreņi (§ Repo higiēna).

