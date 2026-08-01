# DeepSeek claim-extractor tests — 2026-08-14

## Kopsavilkums

DeepSeek claim-extractor aģenti apstrādāja visu 2026. gada 14. augusta dienas rindu. Tests bija uzraudzīts: pēc katra raunda tika pārbaudīti faktiskie DB ieraksti, avotu pilnie teksti, valoda, rindas iztukšošana un pretrunu pārbaude.

- 46 politiķi un organizācijas;
- 48 atsevišķas analīzes (Lato Lapsam un NBS rinda bija sadalīta divos sweep);
- 137 politiķa–dokumenta pāri jeb 135 unikāli dokumenti;
- DeepSeek sākotnēji saglabāja 42 claims;
- 33 claims (78,6 %) nebija jāmaina;
- 7 claims (16,7 %) tika paturēti pēc operatora labojuma;
- 2 claims (4,8 %) tika dzēsti kā nederīgi;
- gala DB palika 40 pārbaudīti claims (95,2 % no sākotnēji saglabātajiem).

Šie procenti raksturo tikai vienu uzraudzītu dienu, nevis stabilu modeļa kvalitātes novērtējumu.

## Kas izdevās labi

1. **Rinda tika pabeigta.** `get_pending_politicians(days=1)` pēc darba atgrieza tukšu sarakstu. Visi 137 pāri tika apzīmogoti; `save_analysis` kļūmju nebija.
2. **Pēc prompta precizēšanas RT noteikums turējās.** Pēc pirmās kļūdas aģenti korekti atzina, ka viss teksts pēc `RT @handle:` pieder sākotnējam autoram arī tad, ja turpinājums ir pēc tukšas rindas.
3. **Nulle claims tika pieņemta kā derīgs rezultāts.** Aģenti necentās aizpildīt kvotu ar ceremonijām, pasākumu paziņojumiem, operatīvu informāciju, personiskiem ierakstiem vai trešo pušu balsīm.
4. **Kvalifikatori un darbības vārdi pārsvarā tika saglabāti.** Gala claims satur nosacījumus, nenoteiktību, netiešo runu un skaitļus no avota.
5. **Pretrunu pass tika izpildīts visiem saglabātajiem claims.** Jaunu pretrunu nebija; visi tuvākie trāpījumi tika novērtēti kā turpinājumi, atkārtojumi vai cita apakštēma.
6. **Gala automātiskā kvalitāte ir tīra.** 40 claims stance un reasoning laukiem pārbaudītas 29 111 no 29 111 zīmēm; lints neatrada problēmas. Nav tukšu/neesošu avotu, precīzu dublikātu, `NEEDS_REVIEW` atlikumu, marķieru vai analīzes kļūmju.

## Atrastās kļūdas

### Nederīgi claims — dzēsti

1. **Claim 689613 — nepareiza autorība.** DeepSeek Lato Lapsam pieskaitīja tekstu pēc `RT @didzisdejus:`. Viss teksts patiesībā bija retvītotā autora balss. Pēc šī atraduma promptā tika ieviests cietais RT astes noteikums; kļūda vairs neatkārtojās.
2. **Claim 689649 — skaidrojums nebija pozīcija.** Reiņa Uzulnieka citāts par pensiju indeksācijas formulas darbību bija administratīvs skaidrojums, ne vērtējums, prasība, priekšlikums vai apņemšanās. Aģents pats to bija atzīmējis kā robežgadījumu ar `needs_review`; operatora pārbaudē claim tika dzēsts.

### Paturēti pēc labojuma

- **689623:** darbības vārda stiprums un anglicisms — avots norādīja/sagaidīja, nevis rosināja; `design & build` aizstāts ar latvisku formulējumu.
- **689629:** izlabota gramatika un reasoning laukā avota “aicina” nepastiprināts uz “pieprasa”.
- **689630:** Šlesera lietotie, faktiski nepareizie amata apzīmējumi skaidri atribūti Šleseram, nevis pasniegti kā Atmina fakts.
- **689634:** izlabota atstarpe pirms `%` un neveikls salīdzinājuma formulējums.
- **689643:** izlabota drukas kļūda reasoning laukā.
- **689646:** `100%` → `100 %`; izlabota semantiski kļūdaina frāze par aizsardzības nozares “ievēlēšanu” kampaņā.
- **689651:** Šuvajeva apgalvojums par Siliņu skaidri atribūts viņam, nevis pasniegts kā neatkarīgi pārbaudīts fakts.

Visām izmaiņām izveidoti rollback faili; visiem mainītajiem claims pārrēķināti embeddings.

## Procesa pārkāpumi

- Vienā agrīnā sweep DeepSeek veica tiešu `UPDATE`, lai no quote laukiem noņemtu aptverošās pēdiņas. Rezultāts bija pieņemams, bet metode pārkāpa norādi izmantot tikai drošās store funkcijas.
- Dažos darba skriptos sākotnēji bija shēmas vai vides pieņēmumu kļūdas (`PYTHONPATH`, neesoši kolonnu nosaukumi). Aģenti tās izlaboja pirms datu saglabāšanas; DB ietekmes nebija.
- Aģentu gala atskaišu formāts vairākos batch atšķīrās no prasītā, lai gan paši DB rezultāti bija verificējami.

## Secinājums

DeepSeek ir lietojams claim extraction darbam **ar stingru kontraktu un obligātu operatora QA**. Tas labi veic lielapjoma pirmo atlasi, rindas iztukšošanu, RT filtrēšanu pēc precizēta noteikuma un pretrunu meklēšanu. Tomēr šo testu tas neizturēja kā pilnīgi autonoms publicēšanas aģents: 21,4 % sākotnēji saglabāto claims bija vajadzīga operatora iejaukšanās, tostarp divi claims bija jādzēš.

Drošais lietojums: DeepSeek veic ekstrakciju un glabā ar auditējamu pamatojumu; operators pārbauda autorību, pozīcijas slieksni, atribūciju, darbības vārdu stiprumu un latviešu valodu pirms publicēšanas.
