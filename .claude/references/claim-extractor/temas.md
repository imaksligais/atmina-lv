# claim-extractor — tēmas

Lasi, ja tēma nav acīmredzama. Kodols: `.claude/agents/claim-extractor.md`.

## Saraksts

Kanoniskās 33 grupas ir kodā, un tur tās arī jāskatās: `.venv/Scripts/python.exe -c "from src.topic_map import get_all_group_names; print(get_all_group_names())"`. `store_claim()` tēmas normalizē. Neizdomā jaunu tēmu. Novecojušas: ~~Irāna~~ → Ārpolitika, ~~Inovācijas~~ → Budžets un finanses.

## Tēmu izvēlas pamatojums, ne instruments

Ja izteikuma instruments (robežpunkts, likums, budžeta rinda) un tā pamatojums (kāpēc runātājs saka, ka tas ir svarīgi) velk uz dažādām tēmām, izvēlies pēc pamatojuma, ko nosauc AVOTS. Robežrežīms ar pamatojumu «migrācijas hibrīdkarš» → `Imigrācija`; robežas slēgšana dronu incidentu dēļ → `Aizsardzība un drošība`. Viena notikuma divas puses nedrīkst nonākt divās tēmās: pārbaudi, kādu tēmu tajā pašā dienā ieguva otras puses claim.

## Robežas

- `Mežsaimniecība` = meži (meža likums, kokrūpniecība, LVM). `Lauksaimniecība` = zemkopība, lauku attīstība, zemnieku saimniecības.
- `Pensijas` = pensiju sistēma, indeksācija, pensionāru labklājība — ne `Sociālā politika` pēc noklusējuma.
- `Veselības aprūpe` = slimnīcas, ārstu pieejamība, zāļu cenas, e-veselība — atsevišķi no `Sociālā politika`.
- `Klimats` = emisijas, klimata likums. `Vide` = vides aizsardzība, atkritumi, ūdeņi, gaiss.
- `Korupcija un KNAB` = izmeklēšanas, KNAB, deklarācijas, interešu konflikti. `Tieslietas` = tiesu sistēma.
- `Pilsētvide` = pilsētplānošana, vietējā mobilitāte, publiskā telpa. `Pašvaldības` = pašvaldību pārvalde.
- `Digitālā politika` = e-pakalpojumi, datu aizsardzība, AI regulējums, kiberdrošība.
- `Droni` ↔ `Aizsardzība un drošība`: ja kodols ir dronu pārtveršana, pretdronu spējas, dronu ražošana vai operatori → `Droni`. Ja drons ir tikai arguments plašākai pozīcijai → `Aizsardzība un drošība`. Tests: izņem vārdu «drons» — ja pozīcija sabrūk, tā ir `Droni`.
- `Vēlēšanas` ↔ `Koalīcija un partijas`: kandidāti, kampaņa, aicinājumi vēlētājiem, reitingi → `Vēlēšanas`; koalīcijas virtuve, partiju dibināšana un pārejas, frakciju disciplīna → `Koalīcija un partijas`. Tests: vai izteikums būtu aktuāls arī bez tuvām vēlēšanām?
- `Sports` = sporta finansējums, infrastruktūra, federāciju politika — arī tad, ja runa ir par naudu.

## Izlemtie precedenti (operatora lēmumi — nekarogo atkārtoti)

1. Drošības instruments (robeža, VAD, NBS resursi) ar migrācijas pamatojumu → `Imigrācija`; ja pamatojums ir pati spēja vai resurss → `Aizsardzība un drošība`.
2. Amatpersonu atlīdzība un ētika — pēc RUNĀTĀJA: kritiķi → `Korupcija un KNAB`; amatpersonas paskaidrojums → `Valsts pārvalde`.
3. NVO/SIF finansējums un brīvprātīgā darba regulējums → `NVO un pilsoniskā sabiedrība` (ja prasība ir par darba tiesībām → `Sociālā politika`).
4. Veselības rādītāji demogrāfiskā ierāmējumā (dzīves ilgums, zaudētie mūža gadi) → `Veselības aprūpe`.
5. Ukrainas atbalsta akti (vizītes, piegādes, ziedojumi) → `Ukraina un Krievija`, arī ja instruments ir enerģētika vai aizsardzība. IZŅĒMUMS: ja tas pats dokuments jau devis citu `Ukraina un Krievija` pozīciju, paliek instrumenta tēma, lai divas pozīcijas nesaplūst uz idempotences atslēgas.

## Tēma neiederas — `NEEDS_REVIEW`

1. Jaunu tēmu neizdomā.
2. Izvēlies labāko no 33.
3. `reasoning` sāc ar `NEEDS_REVIEW:` un paskaidro, kāpēc tēma nav skaidra un ko izvēlējies.

## Marķieris — tu to raksti, bet nekad neaizver

- Aizvēršana ir cilvēka lēmums: `wiki/operations/weekly-routine.md` § 5.
- Citējot precedentu, neraksti vārdus `Izvērtēts`, `REVIEWED`, `IZSKATĪTS`. Trigeris tos nolasa no `reasoning`, un jauns claim piedzimst «izvērtēts». Raksti «operatora lēmums YYYY-MM-DD».
- `topic` pats nemaini jau glabātam claim: `store_claim()` iegulda `f"{topic}: {stance}"`, tāpēc tēmas maiņai vajag jaunu embedding. To dara orķestrators.
