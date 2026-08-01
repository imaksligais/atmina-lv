# KNAB rindas izpēte: Biedrība “LATVIJA PIRMĀ” → LPV

**Datums:** 2026-08-14
**Statuss:** iekšējs faktu pārbaudes ziņojums; publicējams tikai ar zemāk norādīto piesardzīgo formulējumu.

## Īsais secinājums

Atmina rindā redzamie **316 309,12 eiro nav 316 tūkstošu eiro naudas ziedojums**. Aktuālais KNAB avots šo 2026. gada 7. maija ierakstu klasificē kā **“Manta vai pakalpojums”**. Kopā ar vēl diviem pozitīviem mantas/pakalpojuma ierakstiem biedrības sniegtais labums bija 340 654,32 eiro, bet no 11. maija līdz 18. jūlijam KNAB publicētas negatīvas naudas rindas tieši −340 654,32 eiro apmērā. Visu 24 rindu neto summa ir **0,00 eiro**.[1]

Drošākais skaidrojums: mantiskais labums tika uzrādīts un pēc tam pilnībā atmaksāts jeb atdots. Likuma 4. panta ceturtā daļa nosaka, ka ziedojums uzskatāms par pieņemtu tikai tad, ja 75 dienu laikā tas nav atdots; KNAB publicē arī atdotos ziedojumus.[2] Pēdējā negatīvā rinda ir 72 dienas pēc sākotnējā 7. maija ieraksta.

Tas nav pierādījums nelikumīgam ziedojumam. Tas ir interesants stāsts par lielu priekšvēlēšanu reklāmas labumu, kuru partija līdz likumā noteiktā loga beigām pilnībā neitralizēja ar atmaksām.

## Ko tieši rāda aktuālais KNAB avots

Biedrībai “LATVIJA PIRMĀ”, reģistrācijas numurs **40008308560**, KNAB ir 24 ar LPV saistītas rindas:[1]

| Datums | Veids | Summa |
|---|---|---:|
| 07.05.2026. | Manta vai pakalpojums | +316 309,12 € |
| 11.05.2026. | Nauda | −30 000,00 € |
| 11.05.2026. | Nauda | −30 000,00 € |
| 11.05.2026. | Manta vai pakalpojums | +24 200,00 € |
| 05.06.–18.07.2026. | vairākas naudas rindas | atlikušās atmaksas |
| 19.06.2026. | Manta vai pakalpojums / Nauda | +145,20 € / −145,20 € |
| **Kopā** | 3 pozitīvas + 21 negatīva rinda | **0,00 €** |

Kontroles summas:

- pozitīvie ieraksti: **340 654,32 €**;
- negatīvie ieraksti: **−340 654,32 €**;
- neto: **0,00 €**;
- pirmais ieraksts: 07.05.2026.;
- pēdējā atmaksa: 18.07.2026.;
- starpība: **72 dienas**.

Biedrība ir aktīva juridiska persona, reģistrēta 2021. gada 1. jūlijā, nevis politiskā partija vai fiziska persona.[5]

## Saistība ar priekšvēlēšanu reklāmu

JCDecaux pārredzamības paziņojumā LPV norādīta kā politiskās reklāmas sponsors, bet biedrība “LATVIJA PIRMĀ” — kā maksātājs. Kampaņas periods bija 2026. gada 4. maijs–1. jūnijs, un norādītā kampaņas kopējā vērtība bija **337 189,61 eiro**.[3]

SKONTO TEV paziņojumā biedrība norādīta gan kā sponsors, gan maksātājs 2026. gada 5.–30. maija reklāmai par **19 480,23 eiro**.[4]

Tas stiprina secinājumu, ka KNAB rindas ir saistītas ar biedrības apmaksātu priekšvēlēšanu reklāmu LPV labā. Tomēr ārējo paziņojumu summas nesakrīt ar KNAB 340 654,32 eiro kontroļsummu, tāpēc bez rēķiniem vai KNAB skaidrojuma nedrīkst apgalvot precīzu viena pret vienu sasaisti.

## Ko drīkst un nedrīkst publicēt

### Drošs formulējums

> KNAB datubāzē 2026. gada 7. maijā reģistrēts biedrības “LATVIJA PIRMĀ” mantisks vai pakalpojuma veida labums LPV 316 309,12 eiro apmērā. Kopā ar diviem citiem pozitīviem ierakstiem summa sasniedza 340 654,32 eiro, taču līdz 18. jūlijam KNAB publicētās atmaksas to pilnībā samazināja līdz nullei. Reklāmas pārredzamības paziņojumi apliecina, ka biedrība apmaksāja LPV priekšvēlēšanu reklāmu.

### Nepublicēt bez papildu pierādījumiem

- “LPV saņēma 316 tūkstošu eiro naudas ziedojumu.” — nepareizs veids un ignorētas atmaksas.
- “Biedrība nelikumīgi ziedoja partijai.” — KNAB rindu secība pati par sevi to nepierāda.
- “KNAB piespieda LPV atmaksāt naudu.” — nav iegūts KNAB lēmums vai skaidrojums.
- “JCDecaux kampaņa precīzi veido šo KNAB summu.” — summas nesakrīt.
- “Ziedojums nekad nenotika.” — tas tika uzrādīts, bet netika atstāts pieņemts pēc atmaksām.

## Atmina datu kļūda

Atmina 2026. gada 24. jūlija momentuzņēmumā visas trīs pozitīvās rindas kļūdaini glabājas kā **“Nauda”**, lai gan aktuālais KNAB API tās rāda kā **“Manta vai pakalpojums”**. Turklāt četri no 24 `public_id` ir mainījušies: trīs pozitīvajām rindām un 18. jūlija −10 000 eiro rindai.

`src/knab.py` izmanto KNAB `public_id` kā unikālo `knab_id` un veic `INSERT OR IGNORE`. Ja KNAB pēc importa pārklasificē ierakstu un piešķir jaunu `public_id`, nākamais atjauninājums veco rindu neatjaunos — tas ievietos jaunu rindu. Šajā konkrētajā gadījumā četru jauno ID atkārtota ielāde pievienotu **+330 654,32 eiro** viltus neto un radītu 28 rindas 24 vietā.

Nepieciešamais labojums pirms nākamā KNAB pilnā importa:

1. deduplicēt ne tikai pēc `public_id`, bet arī pēc stabila satura atslēgas (partija + reģistrācijas numurs + datums + summa), arī ierakstiem pēc 2026-04-08;
2. ja satura atslēga sakrīt, atjaunināt `donation_type`, `knab_id` un citus avota laukus;
3. agregātos skaitīt neto summu un neizcelt lielāko pozitīvo rindu bez saistīto atmaksu grupēšanas;
4. pievienot regresijas testu KNAB avota pārklasifikācijai un ID maiņai.

## Atvērtie jautājumi KNAB

Pirms stingrāka raksta būtu jāsaņem KNAB atbilde uz trim jautājumiem:

1. Vai negatīvās naudas rindas nozīmē partijas atmaksu biedrībai saskaņā ar 4. panta ceturto daļu?
2. Kāpēc mantas/pakalpojuma labums atmaksās uzrādīts kā “Nauda”?
3. Kāpēc pēc 2026. gada 24. jūlija mainījās četri `public_id` un trīs ierakstu veidi?

## Sources

[1] https://info.knab.gov.lv/donations?party_public_id=6363c9bba09da347fa751945487a2fe1 — KNAB Partiju finanšu datubāze — LPV maksājumi
[2] https://likumi.lv/ta/id/36189-politisko-organizaciju-partiju-finansesanas-likums — Politisko organizāciju (partiju) finansēšanas likums
[3] https://www.jcdecaux.lv/parredzamibas-pazinojums-latvija-pirma-biedriba — JCDecaux pārredzamības paziņojums — LATVIJA PIRMĀ
[4] https://skontotev.lv/lv/politiska-reklama — SKONTO TEV politiskās reklāmas pārredzamības paziņojumi
[5] https://www.firmas.lv/lv/uznemumi/latvija-pirma-biedriba/40008308560 — Firmas.lv — Biedrība LATVIJA PIRMĀ
