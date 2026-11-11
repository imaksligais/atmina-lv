# Balsojumu tēmu partiju žurnāls (plāns 2026-10-21, 9. uzd.)

Katrai partijai: datums, skaitļi ar saucējiem, rollback faili. Deploy — tikai ar operatora atļauju.

## b01 — 2026-10-22

- **Saturs:** 300 dokumenti ar pašreizējo tēmu «Valsts pārvalde» (`batches.csv`); iesaldēti 297, 3 atstāti `pending` un izslēgti (1230/Lp14, 1232/Lp14 — rubrikā nav vietas politiski represētās personas statusam; 676/Lp14 — zema noteiktība). Paliek nākamajai partijai pēc rubrikas lēmuma.
- **Klasifikācija:** Jev `jev-1.14.0`, viens dokuments pieprasījumā, slieksnis 0,8 (CHANGELOG 2026-10-22 (5)). auto 209 (no tiem tēma mainīta 192, < 0,9 — 36), pending 90, klātbūtnes reģistrācija 1. Atbildes no keša (izmēģinājums uz kopijas, 298 pieprasījumi, ~$0,04).
- **Pārskatīšana:** 126 dokumenti (90 pending + 36 mainīti < 0,9) — 5 Opus pārbaudītāji pret avotu (DB teksts, vajadzības gadījumā titania PDF), katrai rindai burtisks citāts; 96 sakrīt ar Jev, 30 nē. Lēmumi `decide` (method human) 123; pārbaudītāju CSV `.scratch/b01_review/` (nav komitēti).
- **Nejaušā izlase:** 20 «auto» lēmumi (sēkla 20261022, no 173 auto ārpus pārskatīšanas saraksta) — 20/20 pareizi (vārti: > 2 kļūdas → STOP).
- **freeze:** 297 atslēgas, 1910 balsojumi, 115 977 pozīcijas (`data/rollback_vote_topics_b01.sql`, commit 13ecb83d).
- **apply:** 1910 balsojumi / 115 977 pozīcijas pārrakstītas (tēma faktiski mainīta 1743 balsojumiem un 101 060 pozīcijām); `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0`. Pēc: «Saeimas darbs» 642, «Tieslietas» 225, «Valsts pārvalde» 166 (bija 1907) u. c.
- **bills-sync b01:** 72 likumprojekti, mainīti 72 (`data/rollback_bill_topics_b01.sql`).
- **party_contradictions kandidāti** (`generate_candidates`, tikai lasa): pirms 23 520 (votes_considered 48 480, vetoed_procedural 24 011) → pēc 21 723 (45 601; 23 024).
- **Renders:** `--only=balsojumi,bills,likumi`; `likumprojekti/1366-lp14.html` rāda «Vide». Nav deplojots.
- **Konstatēts pa ceļam:** nepareizs `saeima_votes.summary` — 22/Lp14 (visi 4 balsojumi: zemes likumiskā lietošana, bet likums par PKC → Valsts kanceleja), 1106/Lp14 (3 lasījumi: Maksātnespējas kontroles dienesta pakete), 1153/Lp14 (3. las.) → `backlog/saeima.md`. Rubrikas robeža: represēto statuss (Sociālā politika vai Ukraina un Krievija).
- **Zemas noteiktības cilvēka lēmumi** (pārbaudītājs atzīmēja `low`; `decide` tos glabā kā `confirmed`): 116/Lm14, 30/Lp14, 1392/Lp14, 1252/Lp14, 976/Lp14, 1015/Lp14, 1024/Lp14, 1034/Lp14, 456/Lp14, 672/Lp14. Pierādījumi (burtiski citāti, noteiktība): `review_b01_out/`.
- **T16 pārbaude pēc apply:** «Saeimas darbs» = 7 atslēgas (klātbūtnes reģistrācija 571 balsojums, sēdes pārtraukumi/kvorums/debašu laiks/darba kārtība — `motif:` atslēgas, Jev 1,0) + 267/Lp14 (Saeimas kārtības rullis, Jev auto 0,90) — pēdējais pretrunā ar rubriku (kārtības rullis → «Valsts pārvalde»). Pārējie b01 auto lēmumi, kas rubrikā minēti kā piemēri (412, 1141, 811, 209, 1364, 309, 384, 708/Lp14), sakrīt. «Vēlēšanas» (Vēlētāju reģistra likums ×4) un «Koalīcija un partijas» (partiju finansēšana ×2) — pareizi. Pozīciju tipi snapshot: 100 % `saeima_vote` (115 977) → vektorus nepārrēķina.

## b01k — 2026-10-22 (korekcija)

- 267/Lp14 → «Valsts pārvalde» (`decide`, rubrikas noteikums). freeze/apply: 28 balsojumi, 2 271 pozīcija, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b01k.sql`). bills-sync: 0 likumprojektu (nav `saeima_bills` rindas).
- **Rollback pierādīts uz kopijas** (`.scratch/rb_proof.db`): b01k + b01 rollback → b01 balsojumi atpakaļ 1 907 «Valsts pārvalde»; pozīcijas, kas atšķiras no snapshot `old_topic`: 0; abu partiju statuss `rolled_back`.
- **Deploy:** jaunās tēmas aizies live ar NĀKAMO deploy (pilns koks). Pirms tā renderē arī domēnus, kas rāda pozīciju/balsojumu tēmas (`politiki`, `pozicijas`, `partijas`, `balsojumi`, `bills`, `likumi`), citādi `output/` būs nekonsekvents.

## b01p — 2026-10-22 (operatora lēmums par 3 gaidošajiem)

- 1230/Lp14, 1232/Lp14 (politiski represētās personas statuss) → «Sociālā politika» (statuss galvenokārt dod tiesības un pabalstus); 676/Lp14 (preses likums, atsauce uz ES direktīvām) → «Digitālā politika» (rubrika: komercmediji → «Digitālā politika»). freeze/apply: 9 balsojumi, 791 pozīcija, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b01p.sql`); bills-sync 1/1 (`data/rollback_bill_topics_b01p.sql`).
- Nepareizie `saeima_votes.summary` izlaboti (`scripts/_fix_vote_summaries_2026-10-22.py`, `data/rollback_vote_summaries_2026-10-22.sql`): 9 balsojumi (22/Lp14 ×4, 1106/Lp14 ×3, 1153/Lp14 3. las., 1185/Lp14 3. las. — pēdējais atrasts tajā pašā 2026-04-30 sēdes kļūdā) un 788 to `saeima_vote` pozīciju stance; vecā teksta paliek 0.

## b01q — 2026-10-22 (korekcija)

- 676/Lp14 «Digitālā politika» → «Tieslietas»: anotācija — likumprojekts transponē direktīvu (ES) 2016/800 par procesuālajām garantijām bērniem, kuri ir aizdomās turētie vai apsūdzētie kriminālprocesā (atsauce arī uz 2011/93/ES); «Digitālā politika» rubrikā medijus neietver. Rollback `data/rollback_vote_topics_b01q.sql` (likumprojekta rindas `saeima_bills` nav — bills-sync 0).

## b02 — 2026-10-22

- **Saturs:** 300 dokumenti ar pašreizējo tēmu «Valsts pārvalde» (`batches.csv`); iesaldēti 299. Izslēgta `motif:264f72e241b8` («Par priekšlikumu Nr.11»): atslēga apvieno divus nesaistītus balsojumus — 2609 (698/Lp14, kapitālsabiedrības) un 6686 (Zemessardzes likums) → jāsadala ar roku (`backlog/saeima.md`).
- **Klasifikācija:** Jev `jev-1.14.0`, viens dokuments pieprasījumā, slieksnis 0,8. auto 207 (tēma mainīta 186, < 0,9 — 29), pending 93. 300 pieprasījumi, ~$0,04.
- **Nejaušā izlase:** 20 «auto» lēmumi (sēkla 2026102202) — 16/20 pareizi → vārti NEIZTURĒTI (> 2 kļūdas). Kļūdas: 121/P14 → «Izglītība», 207/Lp14 → «Vēlēšanas», 856/Lp14 → «Ukraina un Krievija», 975/Lp14 (kārtības rullis) → «Valsts pārvalde». Cēlonis lielākoties — plāna ievade: b02 Jev dokumentiem garākais kopsavilkums < 200 zīmēm 122/207 (b01: 28/172).
- **Operatora lēmums (2026-10-22):** pārbaudīt pret avotu VISUS b02 lēmumus. 13 Opus pārbaudītāji (5 × pārskatāmie 122 + izlase 20 + 7 × atlikušie 158 auto), katrai rindai burtisks citāts. Nepiekrīt Jev: 32/122, 4/20, 7/158 (760, 971, 980, 216, 977, 1492, 1343/Lp14). Orķestrētājs izlasīja visas `low` nepiekrišanas; paturēta Jev tēma 136/Lm14 («Pilsētvide» — rubrika: autostāvvietas pilsētā), 861/Lm14 un 1574/Lp14 («Sociālā politika» — rubrikā pilsonība; saskaņots ar 912/Lm14).
- **Auto kļūdu līmenis:** 11 no 178 «auto» lēmumiem nepareizi (≈ 6 %; izlase 4/20 + 7/158). Sākotnējā Jev pārliecība šiem 11 (`saeima_document_topics`, pirmā rinda): 9 no 11 ≥ 0,9, no tiem 3 = 1,0 (856, 980/Lp14; 975/Lp14 0,90) → ielādes slieksnis 0,9 šo kļūdu veidu (plāns kopsavilkums, likuma nosaukums) NEaptur.
- **decide:** 106 (93 pending + 13 mainīti auto); visi 299 glabātie lēmumi = pārbaudes gala tēma (skripts, 0 neatbilstību). Pārbaudītāju CSV `.scratch/b02_review/` (nav komitēti).
- **freeze:** 299 atslēgas, 474 balsojumi, 41 109 pozīcijas (`data/rollback_vote_topics_b02.sql`, commit fdf2c4aa). Pozīcijas 100 % `saeima_vote` → vektorus nepārrēķina.
- **apply:** 474 / 41 109 pārrakstītas (tēma faktiski mainīta 423 balsojumiem un 36 543 pozīcijām); `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0`.
- **bills-sync b02:** 66 likumprojekti, mainīti 60 (`data/rollback_bill_topics_b02.sql`).
- **party_contradictions kandidāti:** pirms 21 738 (votes_considered 45 788, vetoed_procedural 23 196) → pēc 20 788 (44 596; 23 006).
- **T16 pēc apply:** «Saeimas darbs» 41 atslēga — visas ir sesiju sākšana/slēgšana, debašu laiks, pilnvaras, atsaukšana no komisijām un amatiem, delegāciju sastāvs, komisiju izveide; rubrikas piemēri b02 (751, 997/Lp14; 230, 435/Lm14) sakrīt.
- **Renders:** `--only=balsojumi,bills,likumi`; `likumprojekti/1022-lp14.html` rāda «Sociālā politika». Nav deplojots.

## b02k — 2026-10-22 (korekcija pēc rubrikas 2026-10-22.2)

- Operatora lēmums: rubrikas robi iekļauti esošajās tēmās (RUBRIKA § Operatora lēmumi 2026-10-22). Pārbaudīti visi jau izlemtie dokumenti, ko skar jaunie noteikumi (atslēgvārdu meklēšana lēmumu tabulā: darba likums, mazākumtautības, tabaka, alkohols, kārtības rullis, pilsonība, personu dokumenti u. c.) — mainās 2: 1572/Lp14 «Aizsardzība un drošība» → «Sociālā politika», 217/Lp14 «Ekonomika un uzņēmējdarbība» → «Veselības aprūpe». 716/Lp14 paliek «Ārpolitika» (konsulārais pagaidu ceļošanas dokuments), 1333/Lp14 «Tieslietas» (kriminālprocess).
- freeze/apply: 5 balsojumi, 435 pozīcijas, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b02k.sql`); bills-sync 1/1 (`data/rollback_bill_topics_b02k.sql`).
- Zelta etiķete 213/Lp14 («Digitālā politika») pēc jaunās rubrikas būtu «Veselības aprūpe» — `labels.csv` nemainīts (mērījumu vēsture), atzīmēts šeit.
- Jev prompts lasa rubrikas «Ietver» rindas → jaunā versija maina promptu; sliekšņi 0,8/0,9 mērīti uz 2026-10-22.1.

## b02n — 2026-10-22 (22.10. sēdes dokumenti ar cilvēka lēmumu)

- Pēc `/saeima-ingest` 22.10. 10 jaunie dokumenti bija `pending` (Jev < 0,9) → izšķirti pret avotu ar `decide` (cilvēks): 1143/Lm14 NVO, 1144/Lm14 Sociālā politika (pilsonība, 15. noteikums), 1200/Lp14 Valodu politika (14. noteikums; 18 balsojumi kopš februāra), 1421/Lp14 Budžets (VID), 1433/Lp14 Budžets (finanšu sektors), 1437/Lp14 Valsts pārvalde, 1542/Lp14 Izglītība (13. noteikums), 1584/Lp14 Aizsardzība, 1585/Lp14 Digitālā politika, 144/P14 Vide.
- freeze/apply: 7 atslēgas, kur balsojumu tēma ≠ lēmums; 27 balsojumi, 2027 pozīcijas snapshotā, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b02n.sql`); bills-sync 7/7 (`data/rollback_bill_topics_b02n.sql`).
- Neiekļauts: `motif:264f72e241b8` (2609 + 6686) — tā Jev lēmums kļūdains, sadalīšana b03.
- Strīdami lēmumi operatoram: 1200/Lp14 (valoda vs mediji), 1542/Lp14 (izglītība vs imigrācija).

## b03 — 2026-11-08 (00:20–01:00 LV, pirms 08.11. rutīnas dienas; `vote_topics.py status` rāda UTC — 07.11. 22:42, T17)

- **Klasifikācija:** Jev `jev-1.14.0`, viens dokuments pieprasījumā, slieksnis 0,8, rubrika 2026-10-22.2 (sliekšņi mērīti uz .1 — kontrole ir nejaušā izlase). 300 dokumenti: auto 247 (tēma mainīta 197, < 0,9 — 15), pending 50, noteikums 2; 296 pieprasījumi, ~$0,04.
- **Pārskatīšana:** 65 dokumenti (49 pending + 15 mainīti < 0,9 + 1 multi), 3 Opus pārbaudītāji pret avotu (titania PDF, stenogrammas), katrai rindai burtisks citāts; nepiekrīt Jev 13/65. Orķestrētājs izlēma visus `medium`/`low` strīdus: 906/Lm14 → «Tieslietas» (cietušo kompensācija), 92/P14 → «Pašvaldības» (lauku infrastruktūra), 631/Lm14 → «Valsts pārvalde» (Iedzīvotāju reģistra personas kods), 93/P14 → «Koalīcija un partijas» (valdības darba vērtējums ar aicinājumu atkāpties; zema noteiktība, operatoram var pārskatīt), 739/Lp14 → «Transports» (8. noteikums), 927/Lp14 → «Budžets un finanses» (rubrikas robeža).
- **Nejaušā izlase:** 20 auto (sēkla 20261108, no 233) — 19/20 pareizi; kļūda `motif:5ad40b66b691` (priekšlikumu termiņš pēc 67/Lp14 1. las.) «Saeimas darbs» → «Aizsardzība un drošība». Vārti izturēti.
- **decide:** 66 (method human), pārbaudīts skriptā 66/66. Pārbaudītāju CSV `.scratch/b03_review/` (nav komitēti).
- **freeze/apply:** 300 atslēgas, 925 balsojumi, 80 881 pozīcija (100 % `saeima_vote` → vektorus nepārrēķina); tēma faktiski mainīta 348 balsojumiem un 30 856 pozīcijām; `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0` (`data/rollback_vote_topics_b03.sql`, commit 1de2f23d).
- **bills-sync b03:** 28 likumprojekti, mainīti 18 (`data/rollback_bill_topics_b03.sql`).
- **party_contradictions kandidāti:** pirms 21 101 (votes_considered 45 210, vetoed_procedural 23 255) → pēc 20 215 (44 341; 23 302).
- **T16 pēc apply:** «Saeimas darbs» 110 atslēgas — 108 pareizas (pilnvaras, sesijas, komisiju sastāvs, atvaļinājumi, pārtraukumi, darba kārtība, izslēgšana no sēdes); 2 kļūdas → b03k. Rubrikā minētie piemēri b03: 14/14 sakrīt.
- **Renders:** `--only=balsojumi,bills,likumi` un `--only=politiki,pozicijas,partijas` (pozīciju tēmas profilos); `likumprojekti/1420-lp14.html` rāda «Aizsardzība un drošība». `test_likumi_*_byte_identical` lieto testu DB → bāzlīnija nemainās. Nav deplojots — aizies live ar nākamo deploy.
- **Nepareizi `summary`** (nelabots, `backlog/saeima.md`): 46/P14, 50/P14, 87/P14, 90/P14 pieprasījumu sauc par lēmuma projektu; 666/Lm14 «Brišķens» (pareizi Briškens); 812/Lp14 priekšlikums Nr.7 ar 1. las. rezultātu; 1108/Lp14 steidzamības balsojums ar nogrieztu 2. las. tekstu; 739/Lp14 «ievieš CO2 aprēķinu» (likmes tikai indeksē); 1011/Lp14 un 1058/Lp14 procesuālie balsojumi ar 1. las. tekstu; 727/Lp14 kopsummā trūkst «pret».

## b03k — 2026-11-08 (korekcija pēc T16)

- `motif:9c6e6cc44ed3` (priekšlikumu termiņš tūlīt pēc 592/Lp14 Pašvaldības domes vēlēšanu likuma 1. las.) → «Vēlēšanas»; `motif:cd3da3fd8955` (Norvēģijas investīciju līguma 36/Lp14 izslēgšana no darba kārtības) → «Ekonomika un uzņēmējdarbība» (1. noteikums; saskaņā ar 36/Lp14 cilvēka lēmumu). freeze/apply: 2 balsojumi, 181 pozīcija, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b03k.sql`).

## ob1108 — 2026-11-08 (likumprojekti ārpus partijām)

- Izmēģinājums uz DB kopijas (`bills-sync trial_all`): 579 likumprojekti, mainīti 46, visiem vecā tēma NULL (likuma lapa tēmu nerādīja, balsojumu lapa rādīja). No tiem 27 nav nevienā b03–b10 partijā (ielādēti pēc 22.10. vai b01/b02 bez sinhronizācijas): 9 cilvēka lēmumi, 18 Jev auto no ielādes. 18 pārbaudīti pret avotu (1 Opus pārbaudītājs): nepiekrīt 1 (1246/Lp14 → «Aizsardzība un drošība», medium) — atstāts Jev «Digitālā politika», jo rubrika elektroniskos sakarus ieskaita tajā.
- bills-sync/apply: 27/27 (`data/rollback_bill_topics_ob1108.sql`). Pārējie 18 izmēģinājuma likumprojekti pieder b04–b07 un tiks sinhronizēti ar savām partijām.

## b04 — 2026-11-11 (apply 13:48 LV; rutīnas diena bez ielādes un bez pārskata)

- **Klasifikācija:** Jev `jev-1.14.0`, viens dokuments pieprasījumā, slieksnis 0,8. 300 dokumenti: jau ar lēmumu 5, auto 236 (tēma mainīta 52, < 0,9 — 12), pending 59; 295 pieprasījumi, ~$0,05.
- **Pārskatīšana:** 71 dokuments (59 pending + 12 mainīti < 0,9), 3 Opus pārbaudītāji pret avotu (titania anotācijas, PDF), katrai rindai burtisks citāts; nepiekrīt Jev 19/71. Orķestrētājs izlēma `low` rindas: 1523/Lp14 un 1524/Lp14 → «Tieslietas» (Maksātnespējas kontroles dienesta likvidācija, 13. noteikums), 1530/Lp14 → «Imigrācija» (2 no 3 sastāviem par uzturēšanos), 1089/Lp14 → «Budžets un finanses» (VID funkcija); piekrišanas ar `low`: 288/Lp14, 598/Lp14 («Tieslietas»). Pakešu saskaņa: 1383, 1386, 1388, 1390, 1391/Lp14 — visi «Budžets un finanses».
- **Nejaušā izlase:** 20 auto (sēkla 20261111, no 228) — 19/20 pareizi; kļūda 1332/Lp14 «Digitālā politika» → «Tieslietas» (vienīgais punkts — eID izbeigšana meklēšanā izsludinātai personai; dvīnis 1333/Lp14). Vārti izturēti.
- **decide:** 72 (method human), pārbaudīts skriptā 72/72. Pirmā palaišana atteica visus 72 (`\r` tēmas beigās no Windows rindu beigām) — nekas netika ierakstīts. Pārbaudītāju CSV `.scratch/b04_review/` (nav komitēti).
- **freeze/apply:** 300 atslēgas, 1 887 balsojumi, 165 183 pozīcijas (100 % `saeima_vote` → vektorus nepārrēķina); tēma faktiski mainīta 500 balsojumiem un 43 666 pozīcijām; `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0` (`data/rollback_vote_topics_b04.sql`, commit 4b7f215b). Izmēģinājums uz DB kopijas netika darīts (apply ir atomārs un pārbauda paritāti; rollback pierādīts uz kopijas b01k).
- **bills-sync b04:** 76 likumprojekti, mainīti 52 (`data/rollback_bill_topics_b04.sql`).
- **party_contradictions kandidāti:** pirms 20 217 (votes_considered 44 343, vetoed_procedural 23 302) → pēc 20 002 (43 706; 22 889).
- **T16 pēc apply:** «Saeimas darbs» b04 — 0 atslēgu. Rubrikā minētie piemēri b04: 15/16 sakrīt; kļūda 571/Lp14 (Jev auto 0,98 «Izglītība», rubrika: «Valodu politika») → b04k.
- **Nepareizi `summary`** (nelabots): 1142/Lp14 otrreizējās caurlūkošanas balsojums (`saeima_votes.id=7`) apraksta 1248/Lp14; 645/Lp14 visi lasījumi «IeM pakļautības iestāde» (likumprojektā — finanšu ministra pārraudzībā); 1134/Lp14 3. las. min 11.1 pantu, kas netika atbalstīts; 1307/Lp14 1. las. «MK iniciatīva» (iesniedza pieci deputāti); 1332/Lp14 1. las. «eIDAS»; 1080/Lp14 «jaundibināmu»; 908/Lp14 tikai iesniedzēju saraksts; cita lasījuma teksts vai iznākums uz steidzamības, nodošanas vai priekšlikumu balsojumiem — 819, 801, 957, 987, 1004, 1057, 1069, 1085, 1089, 1092, 1100, 1103, 1111, 1115, 1123, 884, 885, 935, 662, 1193, 991, 1040, 1124/Lp14 (pēdējā klase ir T20 konvencija, ne defekts); nepilnīgi — 1124 (12 % PVN pārtikai), 484, 1040, 923, 935, 1480/Lp14.

## b04k — 2026-11-11 (korekcija pēc T16)

- 571/Lp14 (Augstskolu likums, ārvalstu akadēmiskais personāls bez valodas apliecinājuma) → «Valodu politika» (14. noteikums, rubrikas piemērs). freeze/apply: 6 balsojumi, 515 pozīcijas, `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b04k.sql`); bills-sync 0 (likumprojekta rindas `saeima_bills` nav).
- **Mācība:** rubrikas piemēru pārbaudi turpmāk palaiž PIRMS freeze (`docs/audits/2026-11-11-balsojumu-temas/precheck.py <batch>`; nolasa tēmu 109 no 116 rubrikā minētajiem numuriem, neatbilstību lasa cilvēks — b04 3 karogi bija parsera troksnis: 1286, 1064, 571/Lp14 sakrīt ar robežu rindām).

## b05 — 2026-11-11 (apply 14:14 LV)

- **Klasifikācija:** Jev `jev-1.14.0`, slieksnis 0,8. 300 dokumenti: jau ar lēmumu 3, auto 236 (tēma mainīta 38, < 0,9 — 13), pending 61; 297 pieprasījumi, ~$0,05.
- **Pārskatīšana:** 74 dokumenti, 3 Opus pārbaudītāji pret avotu, katrai rindai burtisks citāts; nepiekrīt Jev 25/74. Pakešu lēmumi: CSRD ilgtspējas ziņošana 629, 630, 634/Lp14 → «Ekonomika un uzņēmējdarbība» (rubrika: «uzņēmumu pārskatu (arī ilgtspējas ziņojumu) prasības»); AML 392, 426/Lp14 → «Budžets un finanses» (kā 1040, 1115/Lp14 b04); MKD likvidācija 1261, 1263, 1265/Lp14 → «Tieslietas»; autortiesības 14, 15/Lp14 → «Kultūra». `low`, ko orķestrētājs izlēma pēc pierādījuma: 1120/Lm14 → «Veselības aprūpe» (pandēmiju pārvaldība), 1247/Lp14 → «Aizsardzība un drošība» (iekšlietu ES fondi), 1306/Lp14 → «Budžets un finanses» (EEZ/Norvēģijas granti nav ES instruments), 1370/Lp14 → «Ekonomika un uzņēmējdarbība» (revīzijas komitejas ievēlēšana — slogs uzņēmumiem), 21/Lp14 → «Tieslietas» (piespiedu noma izriet no Civillikuma), 352/Lp14 → «Imigrācija» (kā 1530/Lp14). Piekrišanas ar `low`: 1400/Lp14 «Digitālā politika» (norma valsti nenosauc), 617/Lp14 «Ārpolitika» (ERAB līgums).
- **Nejaušā izlase:** 20 auto (sēkla 2026111102, no 226) — 20/20 pareizi.
- **decide:** 74 (method human), 74/74 pārbaudīts; precheck: rubrikas piemēri 7/7, «Saeimas darbs» 0.
- **freeze/apply:** 300 atslēgas, 907 balsojumi, 79 790 pozīcijas (100 % `saeima_vote`); tēma faktiski mainīta 222 balsojumiem un 19 631 pozīcijai; `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0` (`data/rollback_vote_topics_b05.sql`, commit 3a3e5106).
- **bills-sync b05:** 83 likumprojekti, mainīti 65 (`data/rollback_bill_topics_b05.sql`).
- **party_contradictions kandidāti:** 20 002 → 19 764 (votes_considered 43 394, vetoed_procedural 22 823).
- **Nepareizi `summary`** (nelabots): iesniedzējs «MK», bet komisijas alternatīvais likumprojekts — 35/Lp14 (Sociālo un darba lietu komisija), 352/Lp14 (Juridiskā komisija), 426/Lp14 (Aizsardzības, iekšlietu un korupcijas novēršanas komisija), 540/Lp14 (Budžeta komisija); 528/Lp14 «Jaunās Vienotības deputātu grupa» (iesniedza septiņi JV, PRO un ZZS deputāti); 1272/Lp14 1. las. apraksta principus un aizliegumu, kā likumprojektā nav; 1454/Lp14 «pārņem direktīvas prasību» (direktīva ļauj, «var noteikt»); 69/Lp14 1. las. vecuma robeža 18–27 (iesniegtajā 15–27); 1337/Lp14 tukšs saturs; cita lasījuma teksts — 1203, 1268, 1197, 1132, 1158/Lp14 (T20 klase).

## b06 — 2026-11-11 (apply 14:39 LV)

- **Klasifikācija:** Jev `jev-1.14.0`, slieksnis 0,8. 300 dokumenti: jau ar lēmumu 9, auto 233 (tēma mainīta 88, < 0,9 — 6), pending 58; 291 pieprasījums, ~$0,04.
- **Pārskatīšana:** 64 dokumenti, 3 Opus pārbaudītāji pret avotu, ar saskaņas pārbaudi pret jau izlemtajiem dokumentiem; nepiekrīt Jev 20/64. Saskaņa: 334/Lp14 → «Imigrācija» (kā 352, 1530/Lp14); 493, 530/Lp14 → «Ukraina un Krievija» (kā 1248, 691/Lp14); 855/Lp14 → «Budžets un finanses» (AML, kā 392/Lp14); 726/Lp14 → «Kultūra» (kā 14/Lp14); 73/Lp14 → «Aizsardzība un drošība» (valsts aizsardzības dienesta pakete); 924/Lp14 → «Budžets un finanses» (DORA, kā 915/Lp14); 1085, 1086/Lm14 un 752/Lp14 → «Ekonomika un uzņēmējdarbība» (SPRK, kā 1155/Lp14); 92/Lp14 → «Ekonomika un uzņēmējdarbība» (Covid seku pārvarēšanas likums, kā 504/Lp14; pārvaldības likuma atcelšana 91, 246, 340/Lp14 paliek «Veselības aprūpe»); 102/Lm14 → «Saeimas darbs» (Starpparlamentu savienības grupa, kā delegācijas 98, 103/Lm14).
- **Atstāts operatoram — 863/Lp14 (3 balsojumi, `pending`, nav iesaldēts):** rubrika to min kā «Valodu politika» piemēru, bet tas ir tikai grozāmā likuma pilnais nosaukums («Administratīvo sodu likums par pārkāpumiem pārvaldes, sabiedriskās kārtības un valsts valodas lietošanas jomā»). Anotācijas mērķis: «noteiktu Nodokļu un muitas policijas kompetenci administratīvo pārkāpumu procesā par pārkāpumiem pārvaldes jomā»; izstrādāja FM. Zelta etiķete (`labels.csv`) atzīmēta «NESKAIDRS: kopsavilkumā tikai likuma nosaukums» (T16). Ieteikums: «Budžets un finanses» (13. noteikums, kā 1108, 645/Lp14) un rubrikas piemēru izņemt.
- **Nejaušā izlase:** 20 auto (sēkla 2026111103, no 234) — 20/20 pareizi.
- **decide:** 63 (method human), 63/63 pārbaudīts; precheck: rubrikas piemēri 8/8; «Saeimas darbs» 61 atslēga — visas ievēlēšana komisijās vai atsaukšana no tām, pilnvaras, delegācijas (T16 izlasīts).
- **freeze/apply:** 299 atslēgas, 582 balsojumi, 50 881 pozīcija (100 % `saeima_vote`); tēma faktiski mainīta 190 balsojumiem un 16 729 pozīcijām; `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0` (`data/rollback_vote_topics_b06.sql`, commit 328b8b65).
- **bills-sync b06:** 64 likumprojekti, mainīti 51 (`data/rollback_bill_topics_b06.sql`).
- **party_contradictions kandidāti:** 19 764 → 19 457 (votes_considered 43 004, vetoed_procedural 22 755).
- **Nepareizi `summary`** (nelabots): 73/Lp14 visi 3 balsojumi — «Labklājības ministrijas budžeta paketes» grozījums (patiesībā Aizsardzības ministrijas, valsts aizsardzības dienests, pārņemts 1640/Lp13); 75/Lp14 visi lasījumi apraksta MK pavadvēstuli par 13. Saeimas likumprojektu turpināšanu (saturs: aizsardzības vai civildienesta laiks pensiju apdrošināšanas stāžā); 961/Lp14 iesniedzējs «Satiksmes ministrija» (titania: MK); 334/Lp14 apraksta tikai nelikumīgu uzturēšanos; 1338/Lp14 likumprojektu sauc par «lēmumu»; 1257/Lp14 vecuma robeža 16–18 pret 16–17; 369/Lm14 «komercbanku» (tekstā Nacionālā attīstības banka); 1014/Lp14 tikai nogriezts virsraksts; steidzamības balsojums ar 2. las. tekstu — 878, 913, 940, 982/Lp14 (T20 klase).

## b07 — 2026-11-11 (apply 15:14 LV)

- **Klasifikācija:** Jev `jev-1.14.0`, slieksnis 0,8. 300 dokumenti: jau ar lēmumu 3, auto 238 (tēma mainīta 84, < 0,9 — 11), pending 59; 297 pieprasījumi, ~$0,04.
- **Pārskatīšana:** 70 dokumenti, 3 Opus pārbaudītāji (kopīgs uzdevums `docs/audits/2026-11-11-balsojumu-temas/topic_review_brief.md`); nepiekrīt Jev 39/70. Galvenā klase — **8. noteikums**: vienas nozares PVN likme, akcīze vai IIN atvieglojums Jev liek «Budžets un finanses» (apkure, gāze, elektrība, degviela → «Degviela un enerģētika»; zāles un medicīnas ierīces → «Veselības aprūpe»).
- **Nejaušā izlase:** 20 auto (sēkla 2026111104, no 230) — 18/20 (14/P14 → «Valodu politika», 1239/Lp14 → «Ukraina un Krievija»). Formāli ≤ 2, bet kļūdu klase sistemātiska → **papildpārbaude visiem 31 auto nodokļu dokumentiem** ārpus saraksta un izlases (2 Opus): nepiekrīt 14/31, visi 8. noteikums (pārtika → «Lauksaimniecība»: 115, 137, 156, 183, 214, 243/Lp14; zāles → «Veselības aprūpe»: 184, 238/Lp14; enerģija → «Degviela un enerģētika»: 116, 139, 182, 239, 242, 1207/Lp14).
- **Pakete 1238–1240/Lp14** (ekonomiskās drošības nodoklis): 1238, 1239 → «Ukraina un Krievija» (nodoklis precēm no «augsta riska valsts», pārejas noteikumos — Krievija; 10.c); 1240 paliek «Budžets un finanses» (ieturējums maksājumiem uz visām ES saraksta zemu nodokļu valstīm; instruments vispārējs) — operatoram var pārskatīt.
- **decide:** 86 (method human), 86/86 pārbaudīts; precheck: rubrikas piemēri 5/5; «Saeimas darbs» 46 (29 ievēlēšana komisijā, 9 pilnvaras, 8 atsaukšana).
- **freeze/apply:** 300 atslēgas, 305 balsojumi, 26 850 pozīcijas (100 % `saeima_vote`); faktiski mainīti 144 balsojumi un 12 764 pozīcijas; `collisions=0`, `parity_mismatch=0`, `parity_mismatch_global=0` (`data/rollback_vote_topics_b07.sql`, commit c29d6147). Pirms apply pārbaudīts: ielāde neiet.
- **bills-sync b07:** 106 likumprojekti, mainīti 85 (`data/rollback_bill_topics_b07.sql`).
- **party_contradictions kandidāti:** 19 457 → 19 239.
- **Atvērts operatoram:** budžeta apropriāciju pārdales (18, 208–210, 1109–1111, 1129–1131/Lm14) paliek «Budžets un finanses»; 10. noteikuma piezīme «marķē pēc saņēmēja programmas» runā par budžeta likuma priekšlikumiem — vai tā attiecas uz piekrišanas lēmumiem, izlemj operators.
- **Nepareizi `summary`** (nelabots): 126/P14 «Stabilitātei rosināts paziņojums» (AS deputātu pieprasījums par ekonomisko saišu pārtraukšanu); 124/P14 «AS/ZZS» (visi 10 iesniedzēji — AS); 13/P14 un 14/P14 pieprasījums nosaukts par lēmuma projektu, 23/P14 un 26/P14 tāpat, 21/P14 «ierosinājums»; 1365, 1367, 1368/Lp14 «skenēts, nav pārbaudāms» (teksts lasāms); 112/Lp14 iesniedzēju vārdi kļūdaini; 140, 115, 116, 139, 241, 1498, 1499/Lp14 bez satura; 159/Lp14 bez 0 % apkurei; 1280/Lp14 bez nosacījuma «tikai pilsoņiem»; 272/Lp14 bez DRN atbrīvojuma saules paneļiem; 1508/Lp14 nogriezts.

## b08 — 2026-11-11 (apply 15:34 LV)

- **Klasifikācija:** 300 dokumenti: auto 270 (tēma mainīta 115, < 0,9 — 8), pending 30; 298 pieprasījumi, ~$0,04.
- **Pārskatīšana:** 38 dokumenti (3 Opus), nepiekrīt Jev 9/38; izlase 20 auto (sēkla 2026111105) — 19/20 (570/Lp14 → «Valodu politika»: 5 % PVN grāmatām tikai oficiālajās valodās); 8. noteikuma papildpārbaude 15 auto nodokļu dokumentiem (2 Opus) — nepiekrīt 8/15 (pārtika → «Lauksaimniecība»: 358, 361, 365, 377, 385/Lp14; HORECA → «Ekonomika un uzņēmējdarbība»: 366, 509/Lp14; sankcionēto īpašums → «Ukraina un Krievija»: 472/Lp14).
- Citi: 344, 596/Lm14 → «Saeimas darbs» (delegācijas); 525/Lm14 → «Budžets un finanses» (kā 254, 255/Lm14); 388/Lm14 → «Lauksaimniecība», 411/Lm14 → «Ekonomika un uzņēmējdarbība» (8. noteikums arī lūgumrakstiem); 482/Lm14 un 541/Lp14 (IIN pensijām) → «Budžets un finanses» pēc 1219, 1237/Lp14 (grupas atvieglojums nav nozare — operatoram).
- **decide:** 47, 47/47 pārbaudīts; precheck tīrs; «Saeimas darbs» 94 (arī 2 balsu skaitītāji). **freeze/apply:** 300 atslēgas, 300 balsojumi, 26 396 pozīcijas; mainīti 138 / 12 216; `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b08.sql`, commit d24e0b0f). bills-sync 0 (rindu nav). Kandidāti 19 239 → 18 795.

## b09 — 2026-11-11 (apply 15:53 LV)

- **Klasifikācija:** 300 dokumenti: auto 259 (mainīta 106, < 0,9 — 7), pending 41.
- **Pārskatīšana:** 48 dokumenti (3 Opus), nepiekrīt 12/48; izlase (sēkla 2026111106) — 20/20; nodokļi 5 — nepiekrīt 1 (650/Lp14 → «Lauksaimniecība», kā 263/Lp14).
- Citi: 74/Lp14 → «Aizsardzība un drošība» (Militārā policija; «valsts valodas» — tikai likuma nosaukums, kā 863/Lp14); 74/P14 (NMP un heroīna krava) — orķestrētājs: «Aizsardzība un drošība» (policijas darbs; alternatīva «Budžets un finanses», NMP tolaik FM pārraudzībā); 860/Lm14 → «Imigrācija» (rubrikas piemērs; kopsavilkumi 860 un 879 samainīti), 879/Lm14 → «Saeimas darbs»; 934/Lm14 → «Degviela un enerģētika» (rubrika); 832, 9/Lm14, 751/Lm14 → «Ukraina un Krievija»; 801/Lm14 → «Vēlēšanas» (CVK); 976/Lm14 → «Budžets un finanses».
- **decide:** 49; precheck tīrs; izmeklēšanas komisijas saskaņotas (izveide un termiņš → izmeklējamā tēma, locekļi → «Saeimas darbs»). **freeze/apply:** 300 / 300 balsojumi / 26 435 pozīcijas; mainīti 127 / 11 325; `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b09.sql`, commit 4cd756ea). bills-sync 36, mainīti 15. Kandidāti 18 795 → 18 332.

## b10 — 2026-11-11 (apply 15:58 LV)

- 15 dokumenti (4 `multi`). Orķestrētājs izlēma 8: procedūras balsojumi pēc likuma tēmas (1. noteikums) — 971/Lm14 → «Degviela un enerģētika», 957/Lm14 → «Veselības aprūpe», 958/Lm14 → «Tieslietas», 1224/Lp14 termiņš → «Valsts pārvalde» (kā 1224/Lp14); darba kārtības grozījumi — Pašvaldības domes vēlēšanu likums → «Vēlēšanas», Rēzeknes pašvaldība → «Pašvaldības»; uzticība ārlietu ministrei → «Koalīcija un partijas» (6. noteikums); LB prezidenta vēlēšanas → «Budžets un finanses».
- freeze/apply: 15 balsojumi, 1 324 pozīcijas; mainīti 9 / 818; `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_b10.sql`). bills-sync 2/2.

## kor1111 — 2026-11-11 (apply 16:08 LV; korekcija pēc visu partiju pārbaudes)

- Laiki virsrakstos: `vote_topic_batches.applied_at` (UTC) + 2 h.

- **Rubrikas piemēri visās partijās** (`docs/audits/2026-11-11-balsojumu-temas/rubcheck.py`: karogo, ja glabātā tēma nav nosaukta nevienā rindā, kur numurs minēts — 116 numuri): 2 kļūdas — 356/Lp14 «Sports» un 524/Lp14 «Lauksaimniecība» → «Ukraina un Krievija» (10.c). Pēc kor1111: 0/116. Vecais parseris (`precheck.py`) šos neredzēja.
- **8. noteikums b01–b06:** 59 auto nodokļu lēmumi pret avotu (3 Opus) — nepiekrīt 10/59: 735, 411, 1037, 1038/Lp14 → «Lauksaimniecība»; 37/Lp14 → «Degviela un enerģētika»; 1039/Lp14 → «Ekonomika un uzņēmējdarbība»; 1048/Lp14 → «Veselības aprūpe»; 474/Lp14 → «Ukraina un Krievija»; 1449/Lp14 (tonnāžas nodoklis) → «Transports»; 1427/Lp14 (PVN zīdaiņu pārtikai) NAV mainīts — operatoram kopā ar 1329, 1402/Lp14.
- **Viena likuma grozījumu saskaņa** (`docs/audits/2026-11-11-balsojumu-temas/scan.py`, tikai `saeima_bills` virsraksti «Grozījumi …»): 22 no 192 likumiem ar vairāk nekā vienu tēmu; izlasīti — visi pamatoti ar 12./13. noteikumu (Krimināllikums, IIN, Kredītiestāžu likums u. c.). Lasīšanas saraksts, ne labojumu saraksts.
- freeze/apply: 11 atslēgas, 36 balsojumi, 3 255 pozīcijas, visas mainītas; `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_kor1111.sql`, commit b6b8096f); bills-sync 1/1. Kandidāti → 18 318.
- **Kopā 2026-11-11 (b04–b10, b04k, kor1111):** 1 814 partiju dokumenti (+ 12 atkārtoti korekcijās), 4 338 balsojumi, 380 629 pozīcijas snapshotā; vektorus nepārrēķina (100 % `saeima_vote`). Jev auto kļūdas: nodokļu papildpārbaudēs 33/110 (atlase pēc virsraksta; pēc tam visi 52 atlikušie auto lēmumi ar «PVN|nodok|akcīz» motīvā vai kopsavilkumā izlasīti — 0 kļūdu, 30 no tiem komisiju sastāvs) (b07 14/31, b08 8/15, b09 1/5, b01–b06 10/59); nejaušajās izlasēs 4/120 (no tām 2 nodokļu likumi: 1239, 570/Lp14).

## kor1111b — 2026-11-11 (operatora lēmums: «piekrītu advisor»)

- 863/Lp14 (Nodokļu un muitas policijas kompetence) un 74/P14 (pieprasījums par NMP darbu) → «Budžets un finanses»; rubrikas piemērs 863/Lp14 izņemts, precedenti — RUBRIKA.md § Operatora lēmumi 2026-11-11. freeze/apply: 2 atslēgas, 4 balsojumi, 329 pozīcijas, visas mainītas; `collisions=0`, `parity_mismatch=0` (`data/rollback_vote_topics_kor1111b.sql`). bills-sync 0. `status`: pending 0.
