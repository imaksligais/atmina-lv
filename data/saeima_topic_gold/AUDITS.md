# Zelta kopas audits (plāns 2026-10-21, 5. uzdevums)

Datums: 2026-10-22. Rubrika: `RUBRIC_VERSION 2026-10-22.1` (iepriekš 2026-10-21.1). Etiķetes: `labels.csv` (253 dokumenti), `chain_labels.csv` (694 balsojumi), `labels_astra.csv` (60 dokumenti, otrais marķētājs).

## Izlase un ievade

- `sample.csv` ir iesaldēts: to radīja `scripts/vote_topic_gold_sample.py` ar rubriku 2026-10-21.1 (commits a97928c7). Atkārtojams ar `--rubric` uz šo versiju (`git show a97928c7:data/saeima_topic_gold/RUBRIKA.md`). Ar jauno rubriku skripts sadalītu dev/test citādi (48 atslēgas mainītu pusi), tāpēc izlasi NEģenerē no jauna.
- Noplūdes pārbaude pret jauno rubriku: citēti 96 numuri, no tiem izlasē 36, `test` pusē 0.
- Marķētāji redzēja tikai `input_text`, avota URL un rubriku — bez pašreizējās tēmas (ievades fails bez `current_topic`).

## Marķētāji

- 1. marķētājs: Claude Opus (claude-opus-5-5), 6 neatkarīgas daļas pa 42–43 dokumentiem.
- Ķēdes: 4 Opus marķētāji, katrs balsojums pēc sava satura. Priekšlikumu balsojumu saturs pārbaudīts komisiju priekšlikumu tabulās (titania PDF); pierādījumi `.scratch/chain1`, `chain2`, `lab3`, `lab4` (nav repo).
- 2. marķētājs: gpt-6-astra (Codex), 60 nejaušas `test` rindas, tikai `input_text` + rubrika, bez tīkla.

## Sakritība (60 `test` rindas)

- Pirms izšķiršanas: 52/60 (87 %).
- 8 nesakritības izšķirtas pret avotu (`.superpowers/.../adjudication.md`, pierādījumi `.scratch/adj/`): 5 — otrā marķētāja kļūda (1005/Lp14, 106/Lp14, 1091/Lp14, 216/Lp14, 780/Lp14); 3 — rubrikas defekts (1210/Lp14 un 388/Lm14 — nozares PVN; 215/Lp14 — Imigrācija pret Ukraina un Krievija), labots 8. un 10. noteikumā.
- Pēc rubrikas 2026-10-22.1 un pārmarķēšanas: otrais marķētājs sakrīt ar galīgo etiķeti 49/60 (sakritības kritums nāk no jaunās 35. tēmas un jaunajiem noteikumiem, ko 2. marķētājs neredzēja).

## Balsojums ≠ dokuments (2. solis)

20 garās ķēdes, 694 balsojumi; salīdzinājums ar dokumenta galīgo etiķeti.

| Kopa | Atšķiras | Daļa |
|---|---|---|
| Visi | 355/694 | 51,2 % |
| Bez budžeta likumiem | 13/324 | 4,0 % |
| Budžeta likumi (1130/Lp14, 152/Lp14) | 342/370 | 92,4 % |

Pa dokumentiem (tikai tie, kur atšķirība > 0): 152/Lp14 166/175; 1130/Lp14 176/195; 1064/Lp14 7/11 (saziņas valodas priekšlikumi → Valodu politika); 910/Lp14 4/16 (vides iestādes nosaukums → Vide); 1286/Lp14 2/12 (mācību valoda → Valodu politika). Pārējās 15 ķēdes: 0.

**Lēmums.** Kopējais rādītājs > 5 %, tāpēc plāna ceļš ir `saeima_vote_topic_overrides` pirms 9. uzdevuma, un par to jāziņo operatoram. Rādītāju gandrīz pilnībā veido budžeta likumi: tajos katrs priekšlikums pieder savai nozarei, un šādu balsojumu ir simtiem (katrs budžets ~200). Parastajiem likumiem izņēmumi ir reti (4,0 %) un paliek pārbaudes sarakstā. Kā piešķirt tēmas budžeta priekšlikumu balsojumiem, ir dizaina jautājums operatoram, nevis mazs uzdevums.

Mērījuma robeža: ~120 priekšlikumu balsojumiem 3. daļā saturs sākumā nebija redzams; atkārtots ar priekšlikumu tabulām (124 pārbaudīti). Prezidenta otrreizējās caurlūkošanas balsojumi 1019/Lp14 (6720–6722) nav sadalāmi pa priekšlikumiem.

## T16 zaru audits (4. solis)

Jautājums katrai etiķetei: vai rubrikas zars, kā uzrakstīts, no avota teksta dod tieši šo tēmu? Lasīts avots (titania, likumi.lv, stenogrammas), ne marķētāju sakritība. Izlase: 3 etiķetes katrai tēmai («Saeimas darbs» — 10), priekšroka rubrikā necitētām atslēgām.

Kopā 86 etiķetes 31 tēmā: JĀ 62, CITA 2, DEFEKTS 22. Trīs tēmām izlasē etiķešu nebija (Pilsētvide, NVO un pilsoniskā sabiedrība, Sabiedriskie mediji) — saucējs 0, šīs tēmas audits nepārbaudīja.

| Tēma | n | JĀ | CITA | DEFEKTS |
|---|---|---|---|---|
| Saeimas darbs | 10 | 8 | 0 | 2 |
| Aizsardzība un drošība | 3 | 3 | 0 | 0 |
| airBaltic | 3 | 3 | 0 | 0 |
| Budžets un finanses | 3 | 3 | 0 | 0 |
| Degviela un enerģētika | 3 | 3 | 0 | 0 |
| Transports | 3 | 3 | 0 | 0 |
| Valodu politika | 3 | 3 | 0 | 0 |
| Valsts kapitālsabiedrības | 3 | 3 | 0 | 0 |
| Digitālā politika | 3 | 2 | 0 | 1 |
| Izglītība | 3 | 2 | 0 | 1 |
| Korupcija un KNAB | 3 | 2 | 0 | 1 |
| Mežsaimniecība | 3 | 2 | 0 | 1 |
| Tieslietas | 3 | 2 | 0 | 1 |
| Ukraina un Krievija | 3 | 2 | 0 | 1 |
| Veselības aprūpe | 3 | 2 | 0 | 1 |
| Vide | 3 | 2 | 0 | 1 |
| Lauksaimniecība | 3 | 2 | 1 | 0 |
| Pašvaldības | 3 | 1 | 0 | 2 |
| Sociālā politika | 3 | 1 | 0 | 2 |
| Valsts pārvalde | 3 | 1 | 0 | 2 |
| Ārpolitika | 3 | 1 | 1 | 1 |
| Imigrācija | 3 | 0 | 0 | 3 |
| Klimats | 2 | 2 | 0 | 0 |
| Pensijas | 2 | 2 | 0 | 0 |
| Sports | 2 | 2 | 0 | 0 |
| Vēlēšanas | 2 | 2 | 0 | 0 |
| Droni | 1 | 1 | 0 | 0 |
| Koalīcija un partijas | 1 | 1 | 0 | 0 |
| Rail Baltica | 1 | 1 | 0 | 0 |
| ES politika | 1 | 0 | 0 | 1 |
| Kultūra | 1 | 0 | 0 | 1 |

- «Saeimas darbs» robeža (plānā nosauktā): 8/10 JĀ, nevienā nav sajaukta likumprojekta procedūra; 2 DEFEKTS — deputātu pilnvaru apstiprināšana nebija minēta; kandidātu pieteikšanas termiņš sēdē bez likumprojektiem (9. noteikums). Abi labotā rubrikā.
- CITA (etiķetes kļūda): 524/Lp14 → «Ukraina un Krievija» (preču importa aizliegums); 26/P14 → «Tieslietas» (Stambulas konvencija). Abos `input_text` maldināja.
- DEFEKTS: robi un pretrunas rubrikā — jaukts saturs, Imigrācija pret Ukraina un Krievija, nozares iestādes IT un iepirkumi, valodas prasības nozares likumā, sabiedriskā kārtība, dzimumu līdztiesība, dzīvnieku labturība, konsulārais dienests, aģitācija, azartspēles, publiskas mantas atsavināšana, arhitektūra un mājokļi, zemesgrāmatas, pacientu tiesības, ES regulas pārņemšana.
- Rubrikas piemērs 878/Lp14 bija kļūdains (importa aizliegums, nevis lauksaimniecība) — aizstāts.

## Rubrika 2026-10-22.1

- Operatora lēmums: 35. tēma «Ekonomika un uzņēmējdarbība» (ietver tūrismu; commits 93c32822, f6a39ad8).
- Pārrakstīti 1., 8., 9. noteikums; jauni 10.–14. noteikums (Krievija/Baltkrievija pēc instrumenta, Satversme, jaukts saturs, nozares likums un iestāde, valsts valodas prasības); T16 labojumi 18 tēmu sadaļās.
- Pārmarķēts: `labels.csv` 21 rinda, `chain_labels.csv` 14 rindas; katrai `note` beigās `v2026-10-22.1: vecā → jaunā, iemesls`. Saraksts: `.superpowers/sdd/2026-10-21-saeimas-balsojumu-temas/relabel.csv`.
- Orķestratora lēmumi: 7832, 7844 → «Ukraina un Krievija» (10. noteikums); 7676 paliek «Sports»; 121/P14 → «Izglītība» (13. noteikums); 74/Lp14 bez primārā avota — paliek ar `NESKAIDRS`.

## Aprakstīti, ne citēti (semantiskā noplūde)

Noplūdes sargs salīdzina tikai numurus. Rubrikas 2026-10-22.1 noteikumi un piemēri vārdos apraksta 8 `test` dokumentus: 215/Lp14, 561/Lp14, 219/Lm14, 876/Lp14 (10. noteikums), 232/Lp14, 826/Lp14 (11. noteikums), 1073/Lp14 (Droni piemērs), 44/Lp14 (13. noteikums). 7. uzdevuma atskaite `test` rādītājus dod ar šīm rindām un bez tām. Atslēgvārdu klasifikators rubriku neredz, tāpēc šī noplūde nāk par labu tikai Jev un Claude — atskaitē to pasaka blakus uzvarētājam.

## Atlikumi

- `NESKAIDRS` piezīme 9 dokumentiem (26/P14, 74/Lp14, 744/Lp14, 863/Lp14, 876/Lp14, 95/P14, 972/Lm14, 997/Lp14, motif:5ad40b66b691); daļa no tiem atrisināta pārmarķējot (piezīmes beigās). 7. uzdevuma atskaite tos izdala atsevišķi.
- Datu defekti `saeima_votes.summary` (klasifikatori lasa šo tekstu): 6664, 7441 (steidzamības balsojumi ar svešu tekstu); 255/Lp14, 871/Lp14, 121/P14 (kopsavilkums neatbilst avotam), 524/Lp14, 26/P14 (saturs slēpts). Ierakstīts `backlog/saeima.md`.
