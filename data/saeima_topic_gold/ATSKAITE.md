# Saeimas balsojumu tēmu klasifikatoru salīdzinājums (plāns 2026-10-21, 7. uzdevums)

Datums: 2026-10-22. Rubrika `2026-10-22.1`, 35 tēmas. Zelta kopa: `labels.csv` (253 dokumenti: `test` 150, `dev` 103), `chain_labels.csv` (694 balsojumi). Skaitļus rada `scripts/eval_vote_topics.py` (`PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.eval_vote_topics`); DB un tīkls netiek lietoti.

Metodes:
- **keyword** — atslēgvārdu karte (`classify_keyword`); rubriku neredz; bez ticamības.
- **stored** — `saeima_votes.topic` vairākums dokumentam (pašreizējais stāvoklis DB); bez ticamības.
- **jev** — Jev `choice` (jev-1.13.0), 35 opcijas no rubrikas «Ietver» rindām.
- **claude** — Opus (claude-opus-5-5) ar pilnu rubriku, paketes pa ~50 rindām.

Definīcijas:
- `acc_doc` — pareizi dokumenti / visi dokumenti; atturēšanās skaitās par kļūdu.
- `acc_vote` — dokumenta prognoze attiecināta uz visiem tā balsojumiem, svari = `sample.csv:n_votes` (kopā 1 333, `test` pusē 460). Zelts — dokumenta etiķete.
- **Ķēžu rādītājs** (atsevišķa tabula) — dokumenta prognoze pret KATRA balsojuma zeltu `chain_labels.csv`. Tas mēra citu lietu: cik balsojumu kļūdās jebkura metode, kas dod vienu tēmu visam dokumentam.
- macro-F1 — vidējais F1 tikai pār tēmām, kurām `test` zeltā ir atbalsts > 0 (29 no 35).
- Slieksnis — prognoze ar `confidence < t` = atturēšanās (`>= t` paliek). Slieksni izvēlas **tikai uz `dev`** pēc likuma, kas noteikts pirms `test` skaitļu skatīšanas: zemākais t, pie kura dev precizitāte ≥ 0,90; ja tāda nav, t ar augstāko dev precizitāti.

## Galvenā tabula — `test`, visas rindas (150 dokumenti, 460 balsojumi)

| metode | n | acc_doc | acc_vote (n_votes) | macro-F1 | segums pie sliekšņa | precizitāte pie sliekšņa | cena 2 583 dok. |
|---|---|---|---|---|---|---|---|
| keyword | 150 | 65/150 (43,3 %) | 211/460 (45,9 %) | 0,477 (29 tēmas) | 150/150 (bez sliekšņa) | — | $0 |
| stored | 150 | 64/150 (42,7 %) | 207/460 (45,0 %) | 0,473 (29 tēmas) | 150/150 (bez sliekšņa) | — | $0 |
| jev | 150 | 128/150 (85,3 %) | 396/460 (86,1 %) | 0,826 (29 tēmas) | 103/150 (68,7 %), t=0,9 | 95/103 (92,2 %) | ~$0,31 |
| claude | 150 | 143/150 (95,3 %) | 438/460 (95,2 %) | 0,961 (29 tēmas) | 144/150 (96,0 %), t=0,5 | 140/144 (97,2 %) | ~$10 (~$4 ar kešu + Batch API) |

**Rubrikas noplūde.** Rubrika vārdos apraksta 8 `test` dokumentus (`AUDITS.md` § Aprakstīti, ne citēti). Tā nāk par labu tikai Jev un Claude, jo atslēgvārdu klasifikators rubriku neredz. Bez šiem 8 dokumentiem secība nemainās:

| metode | n | acc_doc | acc_vote (n_votes) | macro-F1 | segums pie sliekšņa | precizitāte pie sliekšņa |
|---|---|---|---|---|---|---|
| keyword | 142 | 60/142 (42,3 %) | 160/404 (39,6 %) | 0,481 (28 tēmas) | 142/142 (bez sliekšņa) | — |
| stored | 142 | 60/142 (42,3 %) | 159/404 (39,4 %) | 0,496 (28 tēmas) | 142/142 (bez sliekšņa) | — |
| jev | 142 | 122/142 (85,9 %) | 344/404 (85,1 %) | 0,857 (28 tēmas) | 97/142 (68,3 %), t=0,9 | 90/97 (92,8 %) |
| claude | 142 | 135/142 (95,1 %) | 382/404 (94,6 %) | 0,957 (28 tēmas) | 137/142 (96,5 %), t=0,5 | 133/137 (97,1 %) |

Izņemtie: 215/Lp14, 561/Lp14, 219/Lm14, 876/Lp14, 232/Lp14, 826/Lp14, 1073/Lp14, 44/Lp14 (visi 8 ir `test` pusē). Šajā kopā nav vienīgā «Droni» piemēra (1073/Lp14), tāpēc macro-F1 ir pār 28 tēmām.

## `NESKAIDRS` rindas

9 dokumentiem zelta piezīme sākas ar `NESKAIDRS`; `test` pusē no tiem ir 5 (26/P14, 744/Lp14, 876/Lp14, 95/P14, 972/Lm14), `dev` pusē 4.

| kopa | metode | n | acc_doc | acc_vote (n_votes) | macro-F1 | segums pie sliekšņa | precizitāte pie sliekšņa |
|---|---|---|---|---|---|---|---|
| test bez NESKAIDRS | keyword | 145 | 64/145 (44,1 %) | 199/440 (45,2 %) | 0,480 (29) | 145/145 | — |
| test bez NESKAIDRS | stored | 145 | 63/145 (43,4 %) | 195/440 (44,3 %) | 0,476 (29) | 145/145 | — |
| test bez NESKAIDRS | jev | 145 | 126/145 (86,9 %) | 383/440 (87,0 %) | 0,844 (29) | 102/145 (70,3 %), t=0,9 | 94/102 (92,2 %) |
| test bez NESKAIDRS | claude | 145 | 141/145 (97,2 %) | 425/440 (96,6 %) | 0,981 (29) | 141/145 (97,2 %), t=0,5 | 138/141 (97,9 %) |
| tikai NESKAIDRS | keyword | 5 | 1/5 | 12/20 | — | 5/5 | — |
| tikai NESKAIDRS | stored | 5 | 1/5 | 12/20 | — | 5/5 | — |
| tikai NESKAIDRS | jev | 5 | 2/5 | 13/20 | — | 1/5, t=0,9 | 1/1 |
| tikai NESKAIDRS | claude | 5 | 2/5 | 13/20 | — | 3/5, t=0,5 | 2/3 |

Uz 5 rindām macro-F1 nav jēgpilns, tāpēc tas nav dots. Uz šīm 5 rindām katra modeļu metode pareizi nosaka tikai 2.

## Tēmas bez `test` atbalsta

Pēc zelta etiķetēm `test` pusē nav neviena dokumenta 6 tēmām: ES politika, NVO un pilsoniskā sabiedrība, Pilsētvide, Sabiedriskie mediji, Sports, Valsts kapitālsabiedrības. Macro-F1 tās neietver (29 no 35 tēmām). Plāns pēc pašreizējās tēmas minēja Droni, Klimats, Sports, Transports; pēc zelta tikai «Sports» ir bez atbalsta, bet Droni, Klimats un Transports `test` pusē ir (1, 1 un 4 dokumenti). Kļūdaina prognoze tēmā bez atbalsta joprojām samazina `acc_doc` un tās tēmas precizitāti.

## Sliekšņi (`dev` izvēlei, `test` pārbaudei)

Segums = prognozes ar `confidence >= t` / visi; precizitāte = pareizās / paturētās; acc = pareizās / visi.

**Jev** — dev precizitāte sasniedz 0,90 tikai pie t=0,9 → izvēlētais slieksnis 0,9.

| t | dev segums | dev precizitāte | dev acc | test segums | test precizitāte | test acc |
|---|---|---|---|---|---|---|
| — | 103/103 | 85/103 (82,5 %) | 85/103 (82,5 %) | 150/150 | 128/150 (85,3 %) | 128/150 (85,3 %) |
| 0,5 | 95/103 (92,2 %) | 81/95 (85,3 %) | 81/103 (78,6 %) | 142/150 (94,7 %) | 124/142 (87,3 %) | 124/150 (82,7 %) |
| 0,6 | 88/103 (85,4 %) | 75/88 (85,2 %) | 75/103 (72,8 %) | 137/150 (91,3 %) | 121/137 (88,3 %) | 121/150 (80,7 %) |
| 0,7 | 84/103 (81,6 %) | 73/84 (86,9 %) | 73/103 (70,9 %) | 130/150 (86,7 %) | 116/130 (89,2 %) | 116/150 (77,3 %) |
| 0,8 | 75/103 (72,8 %) | 66/75 (88,0 %) | 66/103 (64,1 %) | 117/150 (78,0 %) | 106/117 (90,6 %) | 106/150 (70,7 %) |
| 0,9 | 61/103 (59,2 %) | 57/61 (93,4 %) | 57/103 (55,3 %) | 103/150 (68,7 %) | 95/103 (92,2 %) | 95/150 (63,3 %) |

**Claude** — dev precizitāte ir ≥ 0,90 jau pie t=0,5 → izvēlētais slieksnis 0,5.

| t | dev segums | dev precizitāte | dev acc | test segums | test precizitāte | test acc |
|---|---|---|---|---|---|---|
| — | 103/103 | 99/103 (96,1 %) | 99/103 (96,1 %) | 150/150 | 143/150 (95,3 %) | 143/150 (95,3 %) |
| 0,5 | 100/103 (97,1 %) | 98/100 (98,0 %) | 98/103 (95,1 %) | 144/150 (96,0 %) | 140/144 (97,2 %) | 140/150 (93,3 %) |
| 0,6 | 95/103 (92,2 %) | 95/95 (100,0 %) | 95/103 (92,2 %) | 132/150 (88,0 %) | 131/132 (99,2 %) | 131/150 (87,3 %) |
| 0,7 | 88/103 (85,4 %) | 88/88 (100,0 %) | 88/103 (85,4 %) | 126/150 (84,0 %) | 126/126 (100,0 %) | 126/150 (84,0 %) |
| 0,8 | 74/103 (71,8 %) | 74/74 (100,0 %) | 74/103 (71,8 %) | 114/150 (76,0 %) | 114/114 (100,0 %) | 114/150 (76,0 %) |
| 0,9 | 62/103 (60,2 %) | 62/62 (100,0 %) | 62/103 (60,2 %) | 84/150 (56,0 %) | 84/84 (100,0 %) | 84/150 (56,0 %) |

Jev ticamība ir vāji kalibrēta: `test` pusē no t=0,5 līdz 0,9 precizitāte aug tikai par 5 punktiem, bet segums krīt par 26 punktiem.

## Ķēžu līmenis: dokumenta prognoze pret katra balsojuma zeltu

20 garās ķēdes, 694 balsojumi. No 20 ķēžu dokumentiem 9 ir `test` pusē, 11 — `dev` pusē (arī abi budžeti 1130/Lp14 un 152/Lp14), tāpēc šis rādītājs aptver abas puses. Pirmā rinda liek katram balsojumam dokumenta zelta etiķeti — tie ir griesti, ko sasniedz jebkura dokumenta līmeņa metode.

| metode | visi balsojumi | bez budžeta ķēdēm | tikai budžeta ķēdes |
|---|---|---|---|
| zelta dokumenta etiķete (griesti) | 339/694 (48,8 %) | 311/324 (96,0 %) | 28/370 (7,6 %) |
| keyword | 239/694 (34,4 %) | 211/324 (65,1 %) | 28/370 (7,6 %) |
| stored | 261/694 (37,6 %) | 233/324 (71,9 %) | 28/370 (7,6 %) |
| jev | 328/694 (47,3 %) | 300/324 (92,6 %) | 28/370 (7,6 %) |
| claude | 339/694 (48,8 %) | 311/324 (96,0 %) | 28/370 (7,6 %) |

Budžeta likumos neviena dokumenta līmeņa metode nepārsniedz 28/370: tur katrs priekšlikums pieder savai nozarei. Bez budžetiem griesti ir 311/324; Claude tos sasniedz, Jev paliek 11 balsojumus zemāk.

## Biežākie sajaukšanas pāri (`test`, zelts → prognoze)

- **keyword** (85 kļūdas no 150): Saeimas darbs → Valsts pārvalde 15; Tieslietas → Valsts pārvalde 8; Budžets un finanses → Valsts pārvalde 5; Saeimas darbs → Vide 5; Aizsardzība un drošība → Valsts pārvalde 3; Izglītība → Valsts pārvalde 3; Sociālā politika → Valsts pārvalde 3; Vide → Lauksaimniecība 3. «Valsts pārvalde» ir atslēgvārdu kartes savācējs; «Saeimas darbs» F1 = 0.
- **stored** (86 kļūdas no 150): gandrīz tie paši pāri (Saeimas darbs → Valsts pārvalde 14; Tieslietas → Valsts pārvalde 8; …) — DB tēmas ir tās pašas kartes rezultāts.
- **jev** (22 kļūdas no 150): izkliedētas; Degviela un enerģētika → Budžets un finanses 2, → Vide 2; pārējie pa 1 (piem., Droni → Digitālā politika, Imigrācija → Valodu politika, Izglītība → Kultūra).
- **claude** (7 kļūdas no 150): Aizsardzība un drošība → Tieslietas; Degviela un enerģētika → Vide; Izglītība → Digitālā politika; Izglītība → Vide; Tieslietas → Digitālā politika; Tieslietas → Ekonomika un uzņēmējdarbība; Tieslietas → Ārpolitika (pa 1).

Pilnā F1 tabula pa tēmām: skripta izvadē (sadaļa «F1 pa tēmām»).

## Neatkarīgā marķētāja pārbaude

Gala zeltu marķēja tas pats modelis (claude-opus-5-5), kas darbina Claude klasifikatoru, ar to pašu rubriku un to pašu `input_text`. Tāpēc Claude rādītāji pret zeltu var būt uzpūsti (kopīga modeļa kļūda neparādās kā kļūda, T16). Pārbaudei — 60 `test` rindas, ko neatkarīgi marķēja gpt-6-astra (vecā rubrika 2026-10-21.1, bez 35. tēmas un jaunajiem noteikumiem):

| metode | pret gala zeltu | pret otro marķētāju |
|---|---|---|
| gala zelts | 60/60 | 49/60 (81,7 %) |
| keyword | 21/60 (35,0 %) | 24/60 (40,0 %) |
| stored | 21/60 (35,0 %) | 24/60 (40,0 %) |
| jev | 51/60 (85,0 %) | 49/60 (81,7 %) |
| claude | 58/60 (96,7 %) | 51/60 (85,0 %) |

Pret neatkarīgo marķētāju Claude pārsvars pār Jev sarūk no 7 rindām (58 pret 51) līdz 2 rindām (51 pret 49). Abu modeļu atstatums no atslēgvārdiem saglabājas.

## Darba apjoms 9. uzdevumā (aplēse)

Rēķināts uz visiem 253 izlases dokumentiem (Jev pārliecība pret `pred_stored`). Kolonnas: slieksnis t; `pending` (pārliecība < t); mainīti un < 0,9 (automātiski, jaunā tēma ≠ vecā, pārliecība < 0,9); kopā pārskatāmi ar roku; tas pats, pārrēķināts uz 2 583 dokumentiem; precizitāte pret zeltu prognozēm ar pārliecību ≥ t.

| t | `pending` | mainīti un < 0,9 | ar roku kopā | uz 2 583 | precizitāte (≥ t) |
|---|---|---|---|---|---|
| 0,5 | 16 | 40 | 56 | ~572 | 205/237 |
| 0,6 | 28 | 30 | 58 | ~592 | 196/225 |
| 0,7 | 39 | 22 | 61 | ~623 | 189/214 |
| 0,8 | 61 | 12 | 73 | ~745 | 172/192 |
| 0,9 | 89 | 0 | 89 | ~909 | 152/164 |

Tā ir aplēse no izlases (stratificēta, tāpēc pilnajā kopā daļas var atšķirties); 9. uzdevuma pārskatīšanas solis lasa «pending + jaunā≠vecā un pārliecība <0,9».

## Aplēstā cena 2 583 dokumentiem

- **keyword, stored:** $0.
- **Jev:** lineāra ekstrapolācija no viena izmērīta skrējiena ($0,03 par 253 dokumentiem; 817 141 ievades un 108 107 izvades tokenu): × 10,21 → **~$0,31**, ~8,34 M ievades un ~1,10 M izvades tokenu.
- **Claude (Opus 5.5, $4 / $20 par M tokenu, lasīšana no keša $0,20, Batch API −50 %; cenas no `claude-api` prasmes tabulas, atjaunota 2026-10-06):** 52 paketes pa 50 dokumentiem; katrā paketē rubrika (26 058 zīmes) + 50 × vidēji 625 zīmes `input_text` (vidējais no stratificētās `sample.csv`, pilnajā kopā var atšķirties) + ~300 tokenu instrukcijām. API atslēgas nav, tāpēc `count_tokens` nevarēja palaist: tokeni aplēsti pēc zīmēm, 2,0–3,0 zīmes uz tokenu (Jev skrējienā latviešu tekstam izmērīts ~2,24, bet tas ir cits tokenizators). Izvade: 40 tokenu atbildei uz dokumentu + 3 000 domāšanas tokenu paketē (Opus 5.5 domāšanu izslēgt nevar; noklusējuma piepūle `medium`).

| zīmes/tokenu | ievade | izvade | parasti | rubrika kešā | kešs + Batch API |
|---|---|---|---|---|---|
| 3,0 | ~1,01 M | ~0,26 M | ~$9,2 | ~$7,6 | ~$3,8 |
| 2,5 | ~1,21 M | ~0,26 M | ~$10,0 | ~$8,0 | ~$4,0 |
| 2,0 | ~1,51 M | ~0,26 M | ~$11,2 | ~$8,7 | ~$4,4 |

Lielākā nenoteiktība ir domāšanas tokenos: ja tie ir 10 000 paketē, nevis 3 000, izvade aug līdz ~0,62 M un cena — par ~$7 (bez Batch API).

## Piezīmes

- `dev` puse satur rubrikas piemērus, tāpēc tās rādītāji (skripta izvadē) nav salīdzināmi ar `test`; `dev` lietots tikai sliekšņa izvēlei.
- `acc_vote` pēc `n_votes` `dev` pusē ir augsts (keyword 680/873), jo tur ir lielās ķēdes, ieskaitot budžetus, kuru dokumenta etiķete ir «Budžets un finanses» — tas mēra budžetus, nevis klasifikatoru.

## Jev 1.14 pārmērījums, 2026-10-22

Iemesls: 8. uzdevuma dzīvais zvans atbildēja ar `jev-1.14.0`, bet slieksnis 0,9 un visas augstāk dotās Jev tabulas ir mērītas uz `jev-1.13.0`. Augstāk esošās tabulas paliek 1.13 mērījums.

Mērījums: tie paši 253 `sample.csv` dokumenti ar to pašu `input_text` (`input_hash` sakrīt 253/253), tā pati rubrika `2026-10-22.1` un prompts; kešs apiets (tukšs pagaidu kešs, 0 trāpījumu), 16 pieprasījumi. Atbildes `model` lauks ir `jev-1.14.0` visām 253 atbildēm; 0 tukšu vai nekanonisku atbilžu. 817 141 ievades un 108 109 izvades tokenu, ~$0,03. Prognozes: `pred_jev_1_14.csv`; skaitļi ar to pašu `threshold_stats`/`metrics` no `scripts/eval_vote_topics.py`.

**Galvenie rādītāji (bez sliekšņa):**

| kopa | jev-1.13.0 | jev-1.14.0 |
|---|---|---|
| test acc_doc | 128/150 (85,3 %) | 124/150 (82,7 %) |
| test acc_vote (n_votes) | 396/460 (86,1 %) | 388/460 (84,3 %) |
| test macro-F1 (29 tēmas) | 0,826 | 0,803 |
| test bez rubrikā aprakstītajiem, acc_doc | 122/142 (85,9 %) | 118/142 (83,1 %) |
| dev acc_doc | 85/103 (82,5 %) | 84/103 (81,6 %) |

Tēma atšķiras 13 no 253 dokumentiem: 1.14 labo 3 (1190/Lp14, 1459/Lp14, 949/Lm14), kļūdās 8 vietās, kur 1.13 bija pareizs (1134/Lp14, 1156/Lp14, 17/Lp14, 255/Lp14, 569/Lm14, 836/Lp14, 87/Lp14, 871/Lp14), bet 2 dokumentos abas versijas kļūdās dažādi. Arī tur, kur tēma nemainās, pārliecība mainās līdz 0,47.

**Sliekšņi** (segums = paturētās / visas; precizitāte = pareizās / paturētās):

| t | 1.13 dev precizitāte | 1.13 test segums | 1.13 test precizitāte | 1.14 dev precizitāte | 1.14 test segums | 1.14 test precizitāte |
|---|---|---|---|---|---|---|
| 0,5 | 81/95 (85,3 %) | 142/150 (94,7 %) | 124/142 (87,3 %) | 78/97 (80,4 %) | 139/150 (92,7 %) | 123/139 (88,5 %) |
| 0,6 | 75/88 (85,2 %) | 137/150 (91,3 %) | 121/137 (88,3 %) | 74/87 (85,1 %) | 129/150 (86,0 %) | 116/129 (89,9 %) |
| 0,7 | 73/84 (86,9 %) | 130/150 (86,7 %) | 116/130 (89,2 %) | 68/74 (91,9 %) | 114/150 (76,0 %) | 104/114 (91,2 %) |
| 0,8 | 66/75 (88,0 %) | 117/150 (78,0 %) | 106/117 (90,6 %) | 58/64 (90,6 %) | 103/150 (68,7 %) | 95/103 (92,2 %) |
| 0,9 | 57/61 (93,4 %) | 103/150 (68,7 %) | 95/103 (92,2 %) | 44/45 (97,8 %) | 83/150 (55,3 %) | 78/83 (94,0 %) |

Iepriekš noteiktais likums (zemākais t, pie kura dev precizitāte ≥ 0,90) 1.13 deva 0,9, bet 1.14 dod **0,7**.

**Darba apjoms** (visi 253 dokumenti; tās pašas kolonnas kā § Darba apjoms; «uz 2 583» — tā pati pārrēķināšana salīdzināmībai, plānā tagad 2 715 dokumentu):

| t | 1.13 `pending` | 1.13 mainīti un < 0,9 | 1.13 ar roku (uz 2 583) | 1.13 precizitāte (≥ t) | 1.14 `pending` | 1.14 mainīti un < 0,9 | 1.14 ar roku (uz 2 583) | 1.14 precizitāte (≥ t) |
|---|---|---|---|---|---|---|---|---|
| 0,5 | 16 | 40 | 56 (~572) | 205/237 (86,5 %) | 17 | 59 | 76 (~776) | 201/236 (85,2 %) |
| 0,6 | 28 | 30 | 58 (~592) | 196/225 (87,1 %) | 37 | 46 | 83 (~847) | 190/216 (88,0 %) |
| 0,7 | 39 | 22 | 61 (~623) | 189/214 (88,3 %) | 65 | 29 | 94 (~960) | 172/188 (91,5 %) |
| 0,8 | 61 | 12 | 73 (~745) | 172/192 (89,6 %) | 86 | 18 | 104 (~1 062) | 153/167 (91,6 %) |
| 0,9 | 89 | 0 | 89 (~909) | 152/164 (92,7 %) | 125 | 0 | 125 (~1 276) | 122/128 (95,3 %) |

**Secinājums.** Slieksnis 0,9 uz 1.14 joprojām tur precizitāti (test 78/83 = 94,0 %, visā izlasē 122/128), bet automātiski paliek mazāk dokumentu: ar roku jāskata ~1 276, nevis ~909. Pēc tā paša iepriekš noteiktā likuma 1.14 slieksnis ir 0,7: test precizitāte 104/114 (91,2 %), visā izlasē 172/188 (91,5 %), darbs ar roku ~960 — tuvu tam, ko operators pieņēma ar 1.13. Slieksnis ir konkrēta modeļa skaitlis: 1.14 pārliecības ir pārbīdītas, tāpēc katrai jaunai Jev versijai tas jāmēra no jauna.

**Risks kodā (nav mainīts):** ielāde (`_ingest_classify`) un `classify_jev` pēc noklusējuma sauc `jev-latest`, tāpēc modelis var nomainīties bez ziņas, bet `INGEST_CONFIDENCE_THRESHOLD` ir mērīts vienam modelim. Vai nu piesaistīt konkrētu versiju, vai pārmērīt pie katras jaunas versijas. *Atrisināts 2026-10-22:* operators piesaistīja `jev-1.14.0` (`JEV_MODEL`), partijām slieksnis 0,7, ielādei 0,9 (CHANGELOG 2026-10-22 (4)). *Aizstāts 2026-10-22:* 0,7 mērīts 16 dokumentu paketēs; ar vienu dokumentu pieprasījumā partijām 0,8 (§ Jev 1.14, viens dokuments pieprasījumā; CHANGELOG 2026-10-22 (5)).

## Jev 1.14, viens dokuments pieprasījumā (2026-10-22)

Iemesls: Jev atbilde ir atkarīga no pārējiem dokumentiem tajā pašā pieprasījumā. Zelta mērījumi (1.13 un 1.14) un partijas `classify` sūtīja 16 dokumentus vienā pieprasījumā, bet ielāde sūta vienu. Tāpēc visas augstāk dotās Jev tabulas un sliekšņi 0,7 / 0,9 attiecas uz 16 dokumentu paketēm, ne uz to, kā Jev tiek saukts ielādē. Lēmums: visur viens dokuments pieprasījumā (`JEV_CHUNK_SIZE = 1`, `src/saeima/topics.py`); keša atslēgā ir pieprasījuma izmērs, tāpēc paketēs saņemtās atbildes vairs netiek lietotas.

Mērījums: tie paši 253 `sample.csv` dokumenti ar to pašu `input_text` (`input_hash` sakrīt 253/253), rubrika `2026-10-22.1`, tas pats prompts, `model="jev-1.14.0"`; `classify_jev(rows, model="jev-1.14.0", batch_size=JEV_CHUNK_SIZE)` ar tukšu pagaidu kešu (0 trāpījumu). 253 pieprasījumi pa vienam dokumentam; atbildes `model` lauks ir `jev-1.14.0` visām 253 atbildēm, 0 tukšu vai nekanonisku atbilžu. 879 616 ievades un 108 715 izvades tokenu, ~$0,04. Prognozes: `pred_jev_1_14_single.csv`; skaitļi ar `metrics`/`threshold_stats` no `scripts/eval_vote_topics.py`. Kolonna «16» ir `pred_jev_1_14.csv`, pārrēķināta ar to pašu kodu (sakrīt ar § Jev 1.14 pārmērījums).

**Galvenie rādītāji (bez sliekšņa):**

| kopa | 16 dokumenti pieprasījumā | 1 dokuments pieprasījumā |
|---|---|---|
| test acc_doc | 124/150 (82,7 %) | 136/150 (90,7 %) |
| test acc_vote (n_votes) | 388/460 (84,3 %) | 428/460 (93,0 %) |
| test macro-F1 (29 tēmas) | 0,803 | 0,885 |
| test bez rubrikā aprakstītajiem, acc_doc | 118/142 (83,1 %) | 130/142 (91,5 %) |
| dev acc_doc | 84/103 (81,6 %) | 86/103 (83,5 %) |

**Sliekšņi** (segums = paturētās / visas; precizitāte = pareizās / paturētās; dev 103, test 150 dokumenti):

| t | 16: dev precizitāte | 16: test segums | 16: test precizitāte | 1: dev precizitāte | 1: test segums | 1: test precizitāte |
|---|---|---|---|---|---|---|
| 0,50 | 78/97 (80,4 %) | 139/150 (92,7 %) | 123/139 (88,5 %) | 85/101 (84,2 %) | 148/150 (98,7 %) | 134/148 (90,5 %) |
| 0,55 | 78/96 (81,2 %) | 137/150 (91,3 %) | 122/137 (89,1 %) | 84/98 (85,7 %) | 147/150 (98,0 %) | 133/147 (90,5 %) |
| 0,60 | 74/87 (85,1 %) | 129/150 (86,0 %) | 116/129 (89,9 %) | 84/96 (87,5 %) | 144/150 (96,0 %) | 130/144 (90,3 %) |
| 0,65 | 69/77 (89,6 %) | 123/150 (82,0 %) | 113/123 (91,9 %) | 83/95 (87,4 %) | 143/150 (95,3 %) | 129/143 (90,2 %) |
| 0,70 | 68/74 (91,9 %) | 114/150 (76,0 %) | 104/114 (91,2 %) | 79/88 (89,8 %) | 139/150 (92,7 %) | 126/139 (90,6 %) |
| 0,75 | 65/71 (91,5 %) | 110/150 (73,3 %) | 101/110 (91,8 %) | 74/83 (89,2 %) | 135/150 (90,0 %) | 122/135 (90,4 %) |
| 0,80 | 58/64 (90,6 %) | 103/150 (68,7 %) | 95/103 (92,2 %) | 71/77 (92,2 %) | 130/150 (86,7 %) | 119/130 (91,5 %) |
| 0,85 | 51/56 (91,1 %) | 94/150 (62,7 %) | 86/94 (91,5 %) | 68/73 (93,2 %) | 124/150 (82,7 %) | 114/124 (91,9 %) |
| 0,90 | 44/45 (97,8 %) | 83/150 (55,3 %) | 78/83 (94,0 %) | 65/68 (95,6 %) | 110/150 (73,3 %) | 105/110 (95,5 %) |
| 0,95 | 34/35 (97,1 %) | 59/150 (39,3 %) | 57/59 (96,6 %) | 61/64 (95,3 %) | 95/150 (63,3 %) | 93/95 (97,9 %) |

**Darba apjoms** (visi 253 dokumenti; kolonnas kā § Darba apjoms: `pending` = pārliecība < t; mainīti = pārliecība ≥ t, tēma ≠ `pred_stored`, pārliecība < 0,9; «uz 2 583» — tā pati pārrēķināšana):

| t | 16: `pending` | 16: mainīti < 0,9 | 16: ar roku (uz 2 583) | 16: precizitāte (≥ t) | 1: `pending` | 1: mainīti < 0,9 | 1: ar roku (uz 2 583) | 1: precizitāte (≥ t) |
|---|---|---|---|---|---|---|---|---|
| 0,50 | 17 | 59 | 76 (~776) | 201/236 (85,2 %) | 4 | 38 | 42 (~429) | 219/249 (88,0 %) |
| 0,55 | 20 | 57 | 77 (~786) | 200/233 (85,8 %) | 8 | 35 | 43 (~439) | 217/245 (88,6 %) |
| 0,60 | 37 | 46 | 83 (~847) | 190/216 (88,0 %) | 13 | 33 | 46 (~470) | 214/240 (89,2 %) |
| 0,65 | 53 | 34 | 87 (~888) | 182/200 (91,0 %) | 15 | 32 | 47 (~480) | 212/238 (89,1 %) |
| 0,70 | 65 | 29 | 94 (~960) | 172/188 (91,5 %) | 26 | 27 | 53 (~541) | 205/227 (90,3 %) |
| 0,75 | 72 | 27 | 99 (~1 011) | 166/181 (91,7 %) | 35 | 23 | 58 (~592) | 196/218 (89,9 %) |
| 0,80 | 86 | 18 | 104 (~1 062) | 153/167 (91,6 %) | 46 | 17 | 63 (~643) | 190/207 (91,8 %) |
| 0,85 | 103 | 10 | 113 (~1 154) | 137/150 (91,3 %) | 56 | 11 | 67 (~684) | 182/197 (92,4 %) |
| 0,90 | 125 | 0 | 125 (~1 276) | 122/128 (95,3 %) | 75 | 0 | 75 (~766) | 170/178 (95,5 %) |
| 0,95 | 159 | 0 | 159 (~1 623) | 91/94 (96,8 %) | 94 | 0 | 94 (~960) | 154/159 (96,9 %) |

**Cik atšķiras atbildes** (253 dokumenti; pārliecība salīdzināta ar 2 zīmēm aiz komata):

| salīdzinājums | tēma atšķiras | pārliecība atšķiras | vidējā / lielākā starpība | starpība > 0,05 |
|---|---|---|---|---|
| 16 pret 1 | 20 | 209 | 0,103 / 0,61 | — |
| 1 pret 1 (atkārtojums) | 3 (213/Lp14, 255/Lp14, 898/Lp14) | 114 | 0,012 / 0,12 | 16 |

Pieprasījuma izmēra ietekme ir ~9 reizes lielāka par atkārtojuma troksni. No 20 dokumentiem, kuriem tēma atšķiras, sūtot pa vienam, 17 kļūst pareizi (1123/Lp14, 1134/Lp14, 1156/Lp14, 1199/Lp14, 1349/Lp14, 17/Lp14, 194/Lm14, 213/Lp14, 45/P14, 529/Lp14, 569/Lm14, 578/Lm14, 769/Lp14, 836/Lp14, 863/Lp14, 87/Lp14, motif:208ca3ca9c34), bet 3 — nepareizi (1544/Lp14, 571/Lp14, 898/Lp14). Atkārtojums palika tikai `.scratch/` (nav komitēts).

**565/Lp14** (zelts: Tieslietas), tas pats teksts un modelis: zelta mērījumā 16 dokumentu paketē — Tieslietas 0,81; partijas b01 16 dokumentu paketē (to turēja kešs) — Budžets un finanses 0,27; viens dokuments — Tieslietas 0,72, atkārtojumā 0,76, keša pārbaudes zvanā 0,73.

**Sliekšņi pēc iepriekš noteiktā likuma** (zemākais t režģī 0,50–0,95 ar soli 0,05, pie kura dev precizitāte ≥ 0,90):

- Partijas: **0,80** — dev 71/77 (92,2 %), test segums 130/150 (86,7 %), test precizitāte 119/130 (91,5 %); ar roku ~643 dokumentu (16 paketē pie 0,7 bija ~960).
- Ielāde: max(likums, 0,9) = **0,9**, jo ielādē nav pārbaudes pret esošo tēmu — dev 65/68 (95,6 %), test segums 110/150 (73,3 %), test precizitāte 105/110 (95,5 %).
- Likums šeit stāv uz viena dokumenta robežas: pie 0,70 dev 79/88 (89,8 %), pie 0,75 — 74/83 (89,2 %). Atkārtojumā likums dod 0,75 (74/81 = 91,4 %). Izvēlēts komitētā mērījuma rezultāts 0,80, kas ir arī stingrākais.
