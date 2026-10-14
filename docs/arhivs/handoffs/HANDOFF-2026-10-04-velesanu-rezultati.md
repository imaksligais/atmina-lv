# Handoff 2026-10-04 — vēlēšanu rezultātu diena

> **Statuss (10-05 00:20): PĀRSKATS PAR 10-04 PUBLICĒTS** (note #676, deploy `4449c2f6`, `verify_host` 9/9, attēla varianti 4/4 HTTP 200; operatora atļauja čatā «ģenerēt attēlu un publicēt»). `print_routine('2026-10-04')` — RUTĪNA PABEIGTA.
>
> **Nākamā sesija: jauno deputātu ielāde pēc plāna `docs/plans/2026-10-05-15-saeimas-deputati.md`** (advisor pārskatīts; izpilde soli pa solim ar pārbaudītāju — operatora izvēle vēl jāapstiprina; 1.–5. solis DB neraksta, 6. — pēc CVK oficiālā saraksta). Ievēlēto aprēķins (CVK 1059/1059, PROVIZORISKS, CVK oficiālā saraksta 00:20 vēl nav — `dati.cvk.lv/SV2026/ieveletie-deputati/` 404): `data/cvk_snapshots/SV2026/ievēlētie_aprēķins_20261004_final.json` (gitignored). Kad CVK publicē oficiālo — salīdzināt ar aprēķinu.

## Trešā vakara ielāde + pārskats (23:15–00:20)

- **CVK 23:08, 1059/1059 (abas protokola daļas):** AS 41 (bija 42), PRO 10 (bija 9) — Rīgas vieta pārgāja; ievēlētajos Burāne iekšā, Jānis Liepiņš ārā. Aktivitāte 51,79 %. YAML komitēts `888beb86`.
- **Ielāde** 5/5 OK (`logs/ingest_2026-10-04_vakars3.log`). Plāns 10 aģenti / 3 kārtas / 59 pāri — 59/59; atgūšana 17 pāri + Šlesera 7 nepiesaistītie doki. **30 pozīcijas #729936–#729965** (DB skaits = atskaišu summa; `NEEDS_REVIEW`: Smiltēns 729946, Kulbergs 729939, Hermanis 729953, Šlesers 729954).
- **Pretrunas:** 30/30 + T9 (12 ķēdes, 57 balsojumi) — 0; `contradiction_hunt` vakars-3 ar 6 `rejected_candidates` (Smiltēns moratorijs pret 1058/Lp14 ķēdi noraidīts — AS pati atlika likumprojektu 7431).
- **Spriedzes** #438 (Vaidere→Kulbergs atbalsts), #439 (Kulbergs→Šlesers), #440 (Hermanis→Kulbergs); #199/#200/#202 noraidīti.
- **Labojumi ar rollback:** Siliņa #729955 stance (`data/rollback_silina_729955_2026-10-04.sql`, reembed); spriedze #431 «varētu būt piesaistījis» (`data/rollback_tension_431_krauze_2026-10-05.sql`). `src/briefs.py` skeleta virsrakstos `_lv_plural` («31 pozīcija»).
- **Operatoram:** Šlesera #729954 nav junction rindas (doc 124192, T1 [3,56] skip) — claim glabāts, junction ar roku nepievienots. Jūlija Stepaņenko pid 236 `name_forms` ar kailo uzvārdu piesaista vīru Vjačeslavu (doc 122050, T1). TypeSafe 10-04 vetoed: Ceriņš 23:32 — īsts politiķis (zelta zaudējums). Quality-reviewer WARN: #729877/#729878/#729934 conf 0.6 bez `NEEDS_REVIEW` (rīta/vakara sesiju rindas).

## Kas izdarīts (rīts)

- **CVK rezultāti lapā:** jauns `scripts/fetch_cvk_results.py` (hard-fail pie formāta maiņas) → `data/cvk_sv2026_rezultati.yaml` → bloks `partijas.html` + rinda katrā partijas kartītē. Live ar 09:23 datiem (1026/1059 iecirkņi); deploy `06fbf154`, `verify_host` 9/9. 10:40 CVK jau 1031/1059 — lokāli NAV atjaunots.
- **Divas ielādes** (5/5 OK). Plāns 79/79 pāri + atgūšana 15 pāri → **24 pozīcijas** #729857–#729880 (3 `needs_review`: Pozņaks, Indriksone #729872, Bergmanis).
- **Pretrunas:** 24/24 pārbaudītas, 0 atradumu, 8 `rejected_candidates` žurnālā (`contradiction_hunt` 10-04).
- **Spriedzes** #428–#432 (Dombrava→Šlesers, Dombrava→Kulbergs atbalsts, Šlesers→Kulbergs, Krauze→Kulbergs, Dinevičs→Kulbergs); priekšlikumi #177, #180 noraidīti. **Tendence** #675 (koalīcijas robežas, papildina #673).
- **X pavediens** par provizoriskajiem rezultātiem — operators publicēja (`docs/tweet_bank/2026-10-04-velesanu-rezultati-social.md`; operatora apzināta atkāpe no 10-02 «tikai pēc oficiālajiem»).
- **TypeSafe ēnas žurnāls 10-04:** kļūdains Zivtiņa veto ×2 (`backlog/dati-db.md`).
- **BACKLOG:** jauns `[OPERATOR]` ieraksts — `coalition_status` mainīt tikai pēc 15. Saeimas sanākšanas.

## Vakaram

1. `scripts/fetch_cvk_results.py` → `render --only=partijas,static` → deploy (lapas datu atjaunošana — operators to jau prasījis).
2. Ielāde → `plan_extraction.py --days 2` → ekstrakcija → `recovery_survey.py` → pretrunas → dienas pārskats (`@brief-writer`), vadošā tēma: rezultāti + koalīcijas robežas (#675, spriedzes). Pārskatā vietu skaitus ņemt no svaigākajiem CVK datiem un norādīt iecirkņu skaitu.
3. **Ievēlēto saraksts** `https://dati.cvk.lv/SV2026/ieveletie-deputati/` — 10:40 vēl 404. Kad parādās: salīdzināt ar `tracked_politicians` (kas iekļuva / izkrita / jauni → `/seed-entity`).

## Vakara daļa (17:30–18:30)

> **Operatora lēmums 10-04 vakarā: dienas pārskatu NERAKSTA, kamēr CVK nav publicējusi oficiālo ievēlēto sarakstu** (`dati.cvk.lv/SV2026/ieveletie-deputati/` 18:10 vēl 404). Pārskats par 10-04 rakstāms vēlāk, vienā gājienā ar ievēlēto sarakstu.

- **CVK 17:16 (1057/1059):** commit `01596787`, render `partijas,static`, deploy `332f6899`, `verify_host` 9/9, live lapā «1057 no 1059». Vietas nemainījās (42/17/15/10/9/7).
- **Ievēlēto aprēķins (provizorisks, ārpus repo):** no CVK apgabalu un sarakstu lapām (Sentlagī 1,3,5…; secība pēc «Balsis*»). Vietas pa apgabaliem sakrīt ar CVK 100/100, 0 neatbilstību. Rezultāts: `data/cvk_snapshots/SV2026/ievēlētie_aprēķins_20261004_1731.json` (gitignored). Rīgas 38. vieta AS vs Progresīvie ~12 balsu starpībā; ciešas iekšsaraksta cīņas (Liepiņš/Gruntmanis 7, Morozs/Sidorova 7, Plaude/Osiņenko 15, Siliņa/Melbārde 44). No 100: 45 jau sekoti, 1 `inactive` (Lūse), 54 nav DB (precīzs vārds). CVK sarakstos ir divi Zivtiņi — Edmunds (Zemgale) un Eduards (Vidzeme): tas skaidro TypeSafe Zivtiņa veto.
- **Ielāde** 5/5 OK (`logs/ingest_2026-10-04_vakars.log`). TypeSafe 1 d: judged 655, vetoed 19 (Zivtiņš 9, Kleinbergs 3, Valainis 2, Burovs 2, Kozlovskis, Jātnieks, Kulbergs) — Valainis/Burovs/Kulbergs ir īsti politiķi → zelta zaudējumi ēnas žurnālam.
- **Ekstrakcija:** plāns 27 aģenti / 3 kārtas / 168 pāri — 168/168. + atgūšana 19 web pāri. **47 pozīcijas #729881–#729927** (DB skaits = atskaišu summa). Atmiņas trūkums (OS 1455, segfault pie embedding ielādes) — vairākas `transaction_rolled_back`, atkārtotas; daļēju ierakstu nav. Palīdz `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_DEACTIVATE_ASYNC_LOAD=1`.
- **Pretrunas:** ekstraktori embedding pārbaudi + `@contradiction-hunter` strukturālā pāreja (T9) — 47/47 pozīcijas, 10 balsojumu ķēdes (50 balsojumi), **0 atradumu**; `contradiction_hunt` (vakars) ar 13 `rejected_candidates`. Robežgadījums operatoram: Smiltēns 729887 (Par izstāšanos 2025 → tagad «nav prioritāte, varbūt referendums») — iespējams `minor_shift`.
- **Datu kļūda (BACKLOG `backlog/saeima.md` [FIX]):** `saeima_votes.summary` 24/26 rindām `1058/Lp14` iekopēts balsojuma 1057 teksts; manto ~2035 `saeima_vote` claims. Līdz labojumam šo ķēžu kopsavilkumus pārskatos necitēt.
- **Spriedzes** #433–#437 (Toro→Kulbergs atbalsts, Toro→Hermanis, Zeltīts→Kulbergs, Baško→Zeltīts, Krauze→Kulbergs atbalsts); 11 priekšlikumi noraidīti (apsveikumi, dublikāti, vecs notikums).

### `print_routine()` 18:3x

```
⚠ RUTĪNA NEPILNĪGA — 3 soļi nav pabeigti (2026-10-04)
  ✓ 3. Pretrunu pārbaude — 71 pozīcijas pārbaudītas, 0 pretrunas (medību izpilde pierādīta ar logs ierakstu)
  ✓ 5. Spriedžu reģistrēšana — 10 · ✓ 6. Konteksta piezīmes — 1
  ✗ 7. Dienas pārskats — nav (APZINĀTI atlikts)
  ◐ 9. Wiki sync — pirms rutīnas dienas · ◐ 11. Deploy — jaunāki dati pēc 332f6899
  → ATGŪŠANA: 4 pāri (tikai vestnesis), pārbaudīti 712 pāri
```

### Nākamajai sesijai (pārskats par 10-04)

- Pārskata **subjekta datums = 2026-10-04**, arī ja raksta vēlāk (`brief_subject_date`); `@quality-reviewer` dispatch ar `ROUTINE_DAY='2026-10-04'`; `approve_publish.py 2026-10-04`.
- **check.sh šovakar nebija zaļš vienā skrējienā:** 1. skrējiens 40 failed (MemoryError / OS 1455), 2. — 1 failed + 26 errors (Playwright `TargetClosedError`); izolēti 35 skartie testi + `test_invariants` iziet. Kods šovakar nav mainīts. **~19:00 ar brīvu atmiņu: `check.sh` zaļš — 3286 passed, 3 skipped, «all checks passed».**
- Žuravļevs 729909 — izlemt **PIRMS nākamā rendera** (nākamais renders ir pirmā reize, kad tas var nonākt publiskā lapā).

## Otrā vakara ielāde (19:37–20:30)

- **Ielāde** 5/5 OK 19:54 (`logs/ingest_2026-10-04_vakars2.log`; viena konta pārejoša tīkla kļūda twitter solī). Sesija pārtrūka pēc ielādes — darbs turpināts jaunā sesijā.
- **Ekstrakcija:** plāns 11 aģenti / 3 kārtas / 61 pāris — 61/61; daļa doku atkārtoti rindā, jo avotā rediģēti 19:38–19:45 (`scraped_at` > `reviewed_at`, URL-first dedup). + atgūšana 6 web pāri. **8 pozīcijas #729928–#729935** (DB skaits = atskaites; 3 `needs_review`: Šlesers 729928, Krastiņa 729931, Šuvajevs 729935). Ievērības cienīga: Kulbergs 729932 — vēlēšanu drošībai pastarpināta sadarbība ar Ukrainu (ukraiņi šajās dienās neuzbruka Krievijai).
- **Pretrunas:** 8/8, T9 strukturālā pāreja (6 ķēdes) — 0 atradumu; `contradiction_hunt` (vakars-2), 4 `rejected_candidates`.
- **Spriedzes:** 1 priekšlikums (#197 Stendzenieka satīra) noraidīts.
- **Vakarā kopā: 54 pozīcijas** (46 + 8), 5 spriedzes, 0 pretrunu. CVK ievēlēto saraksts 19:37 — 404.

## Atvērto jautājumu izskatīšana (10-04 ~19:00, ar advisor)

**Izdarīts:**
- **`saeima_votes.summary` [FIX] ATSAUKTS** — tā ir operatora konvencija 2026-08-17/18 (variants b, `src/saeima/votes.py` docstring, CHANGELOG § Māsas balsojumu kopsavilkums), ne defekts; mērogs 2 446 priekšlikumu balsojumi / 214 381 claims. Ieraksts pārcelts uz BACKLOG § Ne-darīt ar vaicājumu. 1057 totāļi 52:0:1 — pareizi.
- **Rinkēvičs 729882** stance → avota debitīvs («… un ka par to nopietni jādomā gan politiķiem, gan ekspertiem, gan žurnālistiem»); `data/rollback_rinkevics_729882_2026-10-04.sql` (commit pirms UPDATE), reembed 1/1.
- **Ievēlēto priekšskaitījums:** 54 no 100 nav DB arī pēc uzvārda+vārda meklēšanā `name` + `name_forms`. **`/seed-entity` sargs:** Eduards Zivtiņš (Vidzeme, LPV) ≠ tracked Edmunds Zivtiņš (Zemgale) — abiem tikai pilnvārda formas, kailais «Zivtiņš» ir divdomīgs.
- **Šlesers bez piesaistes (T1 «Ambiguous … [3, 56] … skipping»):** 21 doks kopš 10-03 05:00 ar «Šleser*» bez junction uz pid 3/56 — 7 web: 123400, 123423, 123433, 123435, 124192, 124198, 124226 (pārējie twitter/x_mention). Nākamajai sesijai: mērķēta lasīšana (vai runā Ainārs), NE `rescan_all`; nekad neminēt piesaisti.

**Slēgts bez darbības:** Vītols 729922/729923 (paša konta vārdi, `source_url` = oriģinālais `guntarsv` statuss — paturēt); Krauze 729911 pret 729865 (dažādas intervijas, dažāds saturs — paturēt); Šlesera LSM citāts doc 123761 — NEpiešķirt #729876 (cits dokuments, `support` līgums); Urbanovičs — visiem sarakstu līderiem `role` ir pirmsvēlēšanu etiķete, labo kopējā pēcvēlēšanu lomu tīrīšanā (pēc 15. Saeimas sanākšanas, kopā ar `coalition_status`); Smiltēns `minor_shift` — atrodams `serve.py` panelī «Pretrunu kandidāti» (`contradiction_hunt` vakars), operators var paaugstināt; junction inversijas 123749/124250/124194/124191 — klase `backlog/matcher.md` § «subject» lomai (3), atgūšana tās šovakar nosedza.

**Operatora lēmumi (10-04 ~19:15):** Žuravļevs 729909 **dzēsts** (`scripts/delete_claim_729909_zuravlevs_2026-10-04.py`, rollback `data/rollback_delete_claim_729909_zuravlevs_2026-10-04.sql`; tvīts 124339 paliek X apakšcilnē) → vakarā **46 pozīcijas**. Renders/deploy pozīcijām un spriedzēm — **kopā ar dienas pārskatu**, viens deploy. **Render NEFILTRĒ `review_status`** — `NEEDS_REVIEW` pozīcijas parādās profilos.

## Atvērts operatoram

- Vēstneša 4 atgūšanas pāri (122684/122685) — kā līdz šim.
- Lapsas tvīts 123835 («kā tiks nozagti vēlēšanu rezultāti») — žurnālista slots, nav glabāts.
- Bartaševičs pid 181: aģenta «stale party» karogs ir FP — CVK: LPV saraksts, bet partija «Kopā Latvijai» pareiza (BACKLOG 11 nemainīts).
- Doc 123749: Šlesers runā, bet junction loma `mentioned`, Kulbergs `subject` — iespējama lomu inversija. Vakarā līdzīgi: doc 124250 (Ričards `subject`, saturs par Aināru), 124194/124191 (Smiltēns `subject`, runā Šlesers/Indriksone).
- **Pārskatāmās pozīcijas:** Žuravļevs 729909 (conf 0.45, «deportēt brūnos», bez konteksta) — izlemt, vai paturēt; Rinkēvičs 729882 stance «aicina … domāt» nedaudz stiprāks par avotu («jādomā»); Vītols 729922/729923 glabāti no paša pašretvītiem (RT vārtu izņēmums).
- **Party-change signāls:** Urbanovičs pid 232 «vairs neredz sevi Saskaņā», virsraksti — pametīs vadību; `role` nemainīts (T6).
- **Datu jautājums:** Indriksones `saeima_vote` rindās «Iebilst pret» pie «atbalstīts 1. lasījumā (52:0)» (piem., 649045–651002) — pārbaudīt.
- Šlesera LSM citāts doc 123761 («Ir laiks izcelt valsti no purva…») nav glabātajā #729876 — pievienot pēc izvēles.
