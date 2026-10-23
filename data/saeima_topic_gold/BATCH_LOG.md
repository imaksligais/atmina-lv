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
