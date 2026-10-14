# Claim-extractor zelta kopa v2 — 2026-09-16 (DRY-RUN — nekādu DB rakstīšanu)

Katram gadījumam atgriez JSON objektu:
{"case": N, "decision": "extract"|"empty"|"needs_review",
 "claims": [{"topic": "...", "stance": "...", "quote": "...|null",
             "confidence": 0.0, "reasoning": "..."}],
 "empty_reason": "...|null"}

Dokumenti doti pilnā tekstā. NEKĀDU save_analysis / store_* / DB izsaukumu — tikai JSON atbilde.

Katram gadījumam norādīts slots, kura vārdā ekstrahē (tāpat kā produkcijas sweepā).

---

## Gadījums 1 — Valdis Dombrovskis (tvīts no viņa konta, platform=twitter)
URL: https://x.com/VDombrovskis/status/... (2026-08-24)

🇺🇦 Congratulations to Ukraine on its Independence Day — 35 years of freedom and resilience.

For more than a third of that time, Ukrainians have courageously fought to defend their country and Europe's security.

Europe stands firmly with Ukraine, supports its fight against Russian aggression, and welcomes Ukraine on its path towards EU membership. 🇪🇺

## Gadījums 2 — Rihards Kols (tvīts no viņa konta, platform=twitter)
URL: https://x.com/RihardsKols/status/... (2026-08-26)

At the 92nd Transatlantic Legislators' Dialogue, we agreed on the essentials: stronger NATO, 5% defence investment by 2035, sustained support for Ukraine, secure supply chains and safeguards against authoritarian abuse of AI.

Authoritarian regimes weaponise technology, trade and dependency. Transatlantic unity must be measured in action.

## Gadījums 3 — Jānis Hermanis (finanšu eksperts, pid=13; tvīts no viņa konta, platform=twitter)
URL: https://x.com/JanisHermanis/status/... (2026-09-03)

Latvijas 🇱🇻 ekonomiskā attīstība šobrīd atrodas līmenī, kuru Igaunija 🇪🇪 sasniedza 14 gadus iepriekš, bet Lietuva 🇱🇹 - 13 gadus iepriekš. https://t.co/7irAg37gaz

## Gadījums 4 — Latvijas valsts meži (LVM) (organization|first_party slots; tvīts no LVM konta, platform=twitter)
URL: https://x.com/LVM_Latvija/status/... (2026-09-03)

🌪️ Pēc augustā piedzīvotās spēcīgās vētras, LVM darbinieki turpina veikt vējgāzes postījumu apzināšanu un seku likvidēšanu. Būtiski, ka meža īpašniekiem vētras seku novēršana tagad kļuvusi vienkāršāka. Nesen stājusies spēkā jauna kārtība, kas ļauj vētras skarto teritoriju precīzi iezīmēt un uzmērīt jau pēc ciršanas darbu pabeigšanas, tādējādi mazinot birokrātiju un nepieciešamību pirms darbu sākšanas doties bīstamajā vējgāzē.

Vairāk uzzini 📽️ video stāstā un 📰 lasi šeit: https://t.co/3Lw490YjcU

## Gadījums 5 — Latvijas valsts meži (LVM) (organization|first_party slots; web, LVM mājas lapa)
Virsraksts: LVM karjerā atrasti 91 militāra rakstura priekšmets un nesprāgusi munīcija
URL: https://www.lvm.lv/... (2026-09-01)

Lai derīgo izrakteņu ieguves vietā "Karogi" mazinātu vēsturiskās munīcijas radītos riskus un varētu droši turpināt minerālo materiālu ieguvi, augustā karjerā tika veikti nesprāgušas munīcijas un militāra rakstura sprādzienbīstamu priekšmetu izpētes un sanācijas darbi. Šo teritoriju AS "Latvijas valsts meži" (LVM) pētīja pastiprināti, jo karjerā jau 2020. gada augustā tika atrasts nesprādzis Otrā pasaules kara laika lādiņš, liecina LVM mājas lapā publicētā informācija.
Darbi veikti aptuveni 5,4 hektāru platībā - tika meklēti iespējamie nesprāgušas munīcijas un citi militāra rakstura sprādzienbīstami priekšmeti, pēc tam veikta to identificēšana, izcelšana, savākšana un droša uzglabāšana, līdz to nodošanai atbildīgajām iestādēm atbilstoši spēkā esošajām prasībām. Sanācijas darbu rezultātā atradnē tika konstatēts un savākts 91 militāra rakstura priekšmets un nesprāgušas munīcijas vienība. Pašlaik derīgo ieguves vieta "Karogi", kas atrodas Limbažu novada Staiceles pagastā, ir atkal pieejams minerālo materiālu ieguvei.
Noslēdzoties darbiem, eksperti uzskaitījuši vairāk nekā 40 dažāda kalibra artilērijas munīcijas, mīnmetēju munīcijas un citus militāra rakstura sprādzienbīstamus priekšmetus. Teritorijā identificēta viena Rogue Grenade fragmentācijas granāta, astoņas 82 mm mīnmetēju mīnas, 17 artilērijas munīcijas vienības (75 mm), 10 artilērijas munīcijas vienības (55 mm), trīs 100 mm artilērijas munīcijas vienības, piecas 88 mm artilērijas munīcijas vienības, viena 80 mm artilērijas munīcijas vienība un viena 150 mm artilērijas munīcijas vienība.
Skaidro "LVM Zemes dzīles un infrastruktūra" ražošanas darbu vadītājs Agris Ārgalis:
"Ņemot vērā jau iepriekš fiksētos gadījumus, pakalpojuma sniedzējam uzdevām veikt darbus ne mazāk kā 0,6 metru dziļumā no zemes virsmas - lai turpmāk šajā platībā varētu veikt drošus segkārtas atsegšanas darbus un turpināt minerālo materiālu ieguvi.
Atradnes "Karogi" sanācija ir nozīmīgs drošības pasākums, lai pirms turpmākas teritorijas atsegšanas un smilts ieguves samazinātu risku, ko varētu radīt zemē saglabājusies nesprāgusī munīcija. Sistemātiska teritorijas izpēte, atrasto priekšmetu identificēšana, savākšana un nodošana atbildīgajām iestādēm ļauj teritorijas turpmāko izmantošanu organizēt kontrolēti un droši."
Veiktie darbi apliecina, ka arī vairāk nekā 80 gadus pēc Otrā pasaules kara Latvijas teritorijā joprojām var atrasties vēsturiskā militārā mantojuma radīti sprādzienbīstami priekšmeti. Īpaši būtiski tas ir vietās, kur paredzēti zemes rakšanas, derīgo izrakteņu ieguves vai citi darbi, kas saistīti ar grunts pārvietošanu.
Jau 2020. gada 19. augustā LVM informēja par nesprāguša kara laika lādiņa atrašanu derīgo izrakteņu ieguves vietā "Karogi". Toreiz, veicot ģeodēziskā punkta ierīkošanas darbus, aptuveni 30 centimetru dziļumā tika atrasts sprādzienbīstams priekšmets. Notikuma vietā tika izsaukta Valsts policija un organizēta teritorijas pārmeklēšana, savukārt atrastais lādiņš tika neitralizēts. Pēc speciālistu sniegtās informācijas, apkārtnes reljefā bija saskatāmas pazīmes, kas liecināja par vēsturisku munīcijas atmīnēšanu.

## Gadījums 6 — Edgars Tavars (web, LETA/diena.lv)
Virsraksts: Tavars ilgstošu palikšanu bez elektroapgādes un sakariem izceļ kā galvenās vētras krīzes problēmas
URL: https://www.diena.lv/raksts/... (2026-08-26)

Arī viedās administrācijas un reģionālās attīstības ministrs Edgars Tavars (AS) pēc vētras skarto Aizkraukles un Jēkabpils novadu apmeklējuma kā galvenās krīzes izgaismotās problēmas izceļ ilgstošus elektroapgādes pārtraukumus un sakaru trūkumu, aģentūru LETA informēja ministra padomniece stratēģiskās komunikācijas jautājumos Mudrīte Grundule.
Trešdien Tavars tikās ar Aizkraukles novada domes priekšsēdētāju Leonu Līdumu (LA/Vidzemes partija) un Jēkabpils novada domes priekšsēdētāju Raivi Ragaini (LZP), kā arī abu pašvaldību pārstāvjiem un apsekoja vētras skartās vietas.
Pēc vizītēm ministrs secinājis, ka pašvaldības krīzes laikā rīkojušās atbildīgi un izmantojušas pieejamos resursus, taču valsts civilās aizsardzības un enerģētiskās krīzes vadības sistēmā atklājušies trūkumi.
Tavars norāda, ka abos novados problēmas bijušas līdzīgas kā citviet valstī - ilgstoši elektroapgādes pārtraukumi un sakaru trūkums. Viņaprāt, krīzes laikā trūcis arī informācijas un skaidras krīzes vadības no valsts puses.
Aizkraukles novadā vizītes laikā atsevišķiem pagastiem elektrības padeve vēl nebija atjaunota. Piemēram, Staburaga pagastā elektrības trūkuma dēļ nedarbojās arī sakaru infrastruktūra, savukārt atsevišķas saimniecības ar slaucamām govīm darbu turpināja, izmantojot ģeneratorus.
Pēc vizītes Tavars plāno rosināt pašvaldībās veidot vienotus krīzes informācijas punktus, kā arī nodrošināt pašvaldību vadītājus ar alternatīviem sakaru un datu pārraides risinājumiem, lai elektrības un publisko sakaru pārtraukumu gadījumā saglabātos iespēja saņemt informāciju, sazināties un koordinēt krīzes vadību.
Ministrs arī uzskata, ka nepieciešami ģeneratori, savlaicīga iedzīvotāju apziņošana un skaidri noteikta atbildība par enerģētiskās krīzes vadību.
Viedās administrācijas un reģionālās attīstības ministrija turpinās konsultēt pašvaldības par vētras radīto izdevumu uzskaiti, iesniedzamajiem dokumentiem un izdevumiem, par kuriem iespējams pieprasīt valsts atbalstu, informēja Grundule.
Kā vēstīts, sestdien, 22. augustā, un tai sekojušajā naktī Latvijā plosījās pēdējo desmitgadu laikā stiprākā vasaras vētra, kurā vēja ātrums vietām pārsniedza 30 metrus sekundē. Negaiss izraisīja plašus bojājumus gan sadales, gan pārvades elektrotīklā, kuru rezultātā sākotnēji elektroapgāde bija pārtraukta aptuveni 277 000 klientu Latvijā, bet elektrotīklu pārrāvumiem daudzviet sekoja nepieejami sakari, degvielas uzpildes stacijas un vietām arī veikali.
Trīs dienas pēc vētras elektroapgādes traucējumi Latvijā joprojām ir aptuveni 11 000 klientu.

## Gadījums 7 — Daiga Mieriņa (web, LSM; daudzrunātāju raksts ar premjera virsrakstu)
Virsraksts: Premjers: Ikvienam Latvijas pilsonim jātiecas uz mērķi veidot stipru un vienotu valsti
URL: https://www.lsm.lv/raksts/... (2026-08-21)

ĪSUMĀ:
- Latvijā 21. augustā atzīmē 35 gadus kopš Latvijas neatkarības de facto atjaunošanas.
- Tam par godu Saeima pulcējās uz svinīgo sēdi, pirms tam noliekot ziedus pie Brīvības pieminekļa.
- Saeimas priekšsēdētāja atgādināja, ka demokrātiskas valsts spēks ir atklātība.
- Premjers norādīja, ka šodien skaidrāk nekā 1991. gadā apzināmies neatkarības nozīmi.
- Eksprezidents Zatlers aicina apzināties Latvijas sasniegumus.
Šogad aprit 35 gadi kopš Latvijas neatkarības de facto atjaunošanas 1991. gada 21. augustā, kad Latvijas Republikas Augstākā Padome pieņēma konstitucionālo likumu "Par Latvijas Republikas valstisko statusu".
Augstākās Padomes deputāti šo likumu pieņēma par spīti Doma laukumā rūcošām okupantu bruņumašīnām un virs parlamenta ēkas riņķojošam armijas helikopteram. 21. augusts ir datums, kas Latvijai atnesis faktisko neatkarību, aizsāka valsts neatkarības reālas atjaunošanas ceļu, atjaunoja Satversmi un nošķīra Latvijas tiesību telpu no PSRS.
Saeima par godu šim notikumam pulcējās uz svinīgo sēdi, uz kuru bija aicināti arī toreizējās Augstākās Padomes deputāti, kuri balsoja par neatkarības atjaunošanu, Valsts prezidents, kā arī ārvalstu diplomātiskā korpusa pārstāvji.
Pirms sēdes deputāti nolika ziedus pie Brīvības pieminekļa.
Mieriņa: Atklātība ir demokrātiskas valsts spēks
Saeimas priekšsēdētāja Daiga Mieriņa (Zaļo un Zemnieku savienība), Saeimas svinīgajā sēdē uzrunājot sanākušos, sacīja, ka šodien mums ir tas, par ko 1991. gadā cilvēki bija gatavi riskēt ar visu, – sava valsts, Satversme, demokrātiski ievēlēts parlaments un droša vieta Eiropas Savienībā un NATO.
Saeimas priekšsēdētāja akcentēja, ka Latvijas neatkarības atjaunošana notika laikā, kad nebija skaidra plāna tālākajai attīstībai vai garantiju starptautiskam atbalstam, taču pastāvēja skaidra izpratne par mērķi un gatavība uzņemties atbildību.
Runājot par šodienas izaicinājumiem, Mieriņa norādīja, ka 14. Saeima ir spējusi pieņemt sarežģītus lēmumus ģeopolitisko satricinājumu un drošības izaicinājumu laikā.
Vienlaikus viņa uzsvēra nepieciešamību domāt par Latvijas attīstību ilgtermiņā, stiprināt valsts drošību un veselības aprūpi, veidot efektīvu valsts pārvaldi un veicināt atklātību lēmumu pieņemšanā.
"Atklātība ir demokrātiskas valsts spēks. Atklātībai ir jābūt ierocim pret dezinformāciju. Atklātībai ir jākļūst par veidu, kā skaidrot sarežģītus lēmumus sabiedrībai," sacīja Mieriņa, norādot, ka sabiedrībai ir jāsaprot, kas notiek Ministru kabinetā, Saeimā un valsts pārvaldē kopumā.
Atzīmējot Ukrainas Neatkarības dienas tuvošanos, Saeimas priekšsēdētāja uzsvēra, ka Ukrainas cīņa atgādina, cik augsta ir brīvības cena un cik svarīgi ir aizsargāt demokrātiju: "Mums ir pienākums sargāt to, par ko reiz cīnījāmies paši un par ko šodien cīnās ukraiņi."
Tāpat Saeimas priekšsēdētāja savā runā atzīmēja, ka parlaments ir sabiedrības spogulis.
"Sabiedrībā arvien vairāk jūtama savstarpējā necieņa un neiecietība. Daudz runājam par savām tiesībām, bet arvien mazāk par atbildību, cieņu un empātiju," pauda Mieriņa.
Runas noslēgumā Saeimas priekšsēdētāja izcēla, ka valsts ir visas sabiedrības atbildība un aicināja iedzīvotājus uzticēties demokrātijai, piedalīties vēlēšanās un ar darbiem apliecināt savu atbildību par valsti.
Kulbergs: Šodien skaidrāk apzināmies neatkarības nozīmi
Premjers Kulbergs, atskatoties uz Latvijas ceļu līdz brīvībai, pauda ticību, ka arī šodien apdraudējuma gadījumā katrs cīnītos par Latvijas neatkarību un brīvību.
"Šodien skaidrāk nekā 1991. gadā apzināmies Latvijas valstiskuma, brīvības un neatkarības nozīmi. To mums nežēlīgi atgādina Krievijas brutālais karš pret Ukrainu. Mēs labi saprotam Ukrainas tautu, jo arī mūsu zeme ir pieredzējusi Krievijas un padomju varas nestās kara, okupācijas un represiju šausmas. Ukrainas cilvēki katru dienu ik mirkli ar savām asinīm apliecina to, ka vēsture jau reiz mums mācīja, – brīvība nav pašsaprotama lieta," atgādināja premjers.
Kulbergs uzsvēra, ka Latvijas valsts ir pamats cilvēku drošībai, labklājībai, tautas attīstībai, latviešu valodai un kultūrai, un katram Latvijas pilsonim ir ne tikai tiesības, bet arī pienākumi pret valsti:
"Karavīrs sargā valsti ar savu gatavību ziedot dzīvību valsts brīvības vārdā, skolotājs – lai nodotu savas zināšanas nākamajai paaudzei, mediķi – glābjot cilvēku dzīvības, uzņēmēji – godprātīgi maksājot nodokļus un attīstot Latvijas ekonomiku, zemnieki – kopjot mūsu tēvu zemi un gādājot par pārtikas drošību, un vecāki – audzinot bērnus par mūsu valsts patriotiem."
Savukārt deputātiem un valdībai ir pienākums stiprināt valsts drošību un ekonomiku. "Mūsu pienākums ir katru dienu ar savu darbu apliecināt savu mīlestību mūsu valstij," sacīja Kulbergs.
Viņš mudināja sanākušos ikdienā nolikt malā ķīviņus un politiskās spekulācijas, un tiekties uz vienotu mērķi – veidot stipru un vienotu valsti.
Tas ir Saeimas, valdības un ikviena Latvijas pilsoņa pienākums, pauda Kulbergs.
Aicina apzināties Latvijas sasniegumus
Pirms Saeimas svinīgās sēdes ziedus Brīvības pieminekļa pakājē nolika arī biedrības "4. maija deklarācijas klubs" prezidente Velta Čebotarenoka, kura sarunā ar Latvijas Radio izteica cerību, ka cilvēki patiesi saprot, ka mēs dzīvojam brīvā valstī, to novērtē un priecājas par to, bet galvenais – sargā Latviju. Viņa piebilda, ka brīvība ir ļoti trausla, ņemot vērā, ka mums blakus ir ienaidnieks. Kamēr būs tāds, kā viņa teica, kaimiņš, Latvijai miera nebūs.
Savukārt kādreizējais Valsts prezidents Valdis Zatlers sarunā ar Latvijas Radio teica, ka neatkarību mēs būvējam jau 35 gadus, bet Latvija līdz galam nekad nebūs uzcelta. Viņaprāt, priekšā vēl ir daudz darba.
Zatlers aicināja mierīgi palūkoties uz aizvadītajiem 35 gadiem un saprast, cik daudz mēs esam sasnieguši.

## Gadījums 8 — Jānis Slaidiņš (NBS majors, militārais analītiķis ar savu neutral slotu, pid=245; web, TV24)
Virsraksts: "Krievu pozīcijas nebija vājas. Tas Ukrainas karavīriem prasīja daudz asiņu!" Slaidiņš par pēdējo Ukrainas uzbrukumu
URL: https://tv24.lv/... (2026-08-21)

Ukrainas bruņoto spēku uzbrukuma operācija frontes dienvidu sektorā Zaporižjas apgabalā parādījusi, ka Ukrainas armija ir uzkrājusi būtisku pieredzi ofensīvu operāciju īstenošanā mūsdienu kara apstākļos, TV24 raidījumā "Aktuālais par karadarbību Ukrainā" stāsta NBS majors, Zemessardzes štāba virsnieks Jānis Slaidiņš.
Viņš norāda, ka šodienas kaujas laukā izšķiroša nozīme ir droniem, izlūkošanai, artilērijai, elektroniskajai karadarbībai un nepārtrauktai frontes novērošanai. Ukrainas spēki, viņaprāt, pierādījuši, ka arī šādos apstākļos iespējams ne tikai aizstāvēties, bet arī organizēt uzbrukuma operācijas un pakāpeniski atbrīvot okupētās teritorijas.
"Ukrainas bruņotie spēki ir pierādījuši, ka šādos apstākļos ir iespējams ne tikai aizstāvēties, bet arī veikt uzbrukuma operācijas un pakāpeniski atbrīvot teritoriju," stāsta Slaidiņš.
Vienlaikus viņš uzsver, ka šāds uzbrukums vairs neatgādina klasisku plaša mēroga ofensīvu ar lielām vienībām, kas vienlaikus metas frontālā triecienā. Tā vietā tiek izmantotas nelielas, rūpīgi koordinētas trieciengrupas, kuru darbības pirms tam detalizēti izplānotas.
Pēc Slaidiņa teiktā, konkrētajā operācijā iesaistītas arī Ukrainas labākās vienības, tostarp desanta triecienu brigādes. Izlūkošana, štāba darbs, uguns atbalsts un trieciengrupas esot darbojušās kā vienots mehānisms.
"Katrs posms tika izstrādāts ārkārtīgi detalizēti un rūpīgi," norāda majors.
Operācijas uzdevums neesot bijis tikai ieņemt vai atbrīvot kādu atsevišķu ciematu. Ukrainas spēkiem bijis nepieciešams izlauzties cauri aizsardzībai, iznīcināt Krievijas vienības, kas bija iespiedušās Ukrainas aizmugurē, un radīt apstākļus turpmākai virzībai.
Slaidiņš stāsta arī par interesantu detaļu – pēc pieejamās informācijas Ukrainas spēki esot atraduši Krievijas kartes, kurās aizsardzības līnijas bijušas iezīmētas desmitiem kilometru tālāk par reāli kontrolētajām pozīcijām.
Viņaprāt, tas liecina par nopietnām problēmām Krievijas komandvadībā.
"Krievijas komandvadības sistēma burtiski bija zaudējusi priekšstatu par kaujas lauku. Uz augšu tika dota informācija par teritorijām, kuras faktiski nemaz netika kontrolētas," skaidro Slaidiņš.
Šādas neprecīzas ziņas, viņaprāt, ietekmē ne tikai komandēšanu, bet arī apgādi, loģistiku un spēku pārvietošanu.
Tomēr Ukrainas uzbrukums neesot bijis viegls. Krievijas spēki bija izveidojuši daudz nocietinātu pozīciju – betona bunkurus un citas aizsardzības būves, kuras atsevišķos gadījumos bijis ļoti grūti iznīcināt pat ar artilēriju vai trieciena droniem.
Tādēļ Ukrainas vienības bieži vien pozīcijas nevis mēģinājušas ieņemt frontālā triecienā, bet tās apiejušas, pārgriezušas apgādes ceļus un izolējušas.
"Ja pozīciju nevarēja ātri likvidēt, Ukrainas spēki to apgāja, pārtrauca loģistiku un nogrieza cietokšņa apgādi," stāsta Slaidiņš.
Tieši manevrs, nevis tikai tiešs spēka trieciens, viņaprāt, ļāvis ar salīdzinoši nelielām vienībām pakāpeniski atspiest Krievijas karaspēku un atbrīvot atsevišķas apdzīvotās vietas.
Vienlaikus Slaidiņš brīdina nenovērtēt Krievijas karavīru pretošanos. Lai gan Krievijas aizsardzību vājinājušas problēmas komandvadībā, atsevišķu nocietināto punktu garnizoni esot turējušies līdz pēdējam.
"Krievu pozīcijas nebija vājas. Tas Ukrainas karavīriem prasīja daudz asiņu," uzsver majors.
Dažos gadījumos Ukrainas vienībām nācies Krievijas nocietinājumus aplenkt, nogriezt tiem munīcijas un apgādes ceļus un gaidīt, līdz aizstāvji vairs nespēj turpināt kauju. Citās situācijās nocietinājumi iznīcināti ar spridzināšanu.
Slaidiņš arī atgādina, ka mazu trieciengrupu taktiku izmanto abas karojošās puses. Arī Krievijas armija pārņēmusi vairākus Ukrainas pielietotos paņēmumus, tostarp nelielu grupu iesūkšanos caur aizsardzības līniju spraugām.
Pēc viņa teiktā, tieši šāda taktika Krievijai iepriekš palīdzējusi gūt panākumus Pokrovskas virzienā – mazas grupas atradušas nepiesegtas vietas Ukrainas aizsardzībā, iekļuvušas dziļāk, nostiprinājušās un pēc tam turpinājušas virzību.
"Krievijas panākumi lielā mērā balstījās uz šo taktiku – atrast caurumu aizsardzībā, iesūkties iekšā, sapulcēties, nostiprināties un tad iet tālāk," skaidro Slaidiņš.
Viņš uzsver, ka mūsdienu karā abas puses ļoti ātri mācās viena no otras. "Katra darbība rada pretdarbību," rezumē NBS majors.

## Gadījums 9 — Edvīns Šnore (NA) (web, LTV «Aizliegtais paņēmiens» priekšvēlēšanu spēle «X stunda»)
Virsraksts: «X stunda» Silgalē: Eksperti vērtē partiju veikumu «Aizliegtā paņēmiena» priekšvēlēšanu spēlē
URL: https://ltv.lsm.lv/... (2026-09-14)

ĪSUMĀ:
- Atvainošanos atraitnei un policijas priekšnieka pagaidu atstādināšanu atbalsta tikai "Stabilitātei!". NA no atvainošanās nošķir līdzjūtību.
- Visas komandas vispirms runātu ar telšu nometnes dalībniekiem; pašvaldības palīdzību karodziņu noņemšanā no atraitnes sētas NA noraida.
- ZZS sākumā izvēlas nogaidīt ar premjera iesaisti. Eksperti saskata gan vēlmi mazināt spriedzi, gan vajadzību pēc redzamākas komunikācijas.
- Vargulis piesardzīgi vērtē agrīnu Zemessardzes klātbūtni, bet atbalsta NATO konsultāciju ierosinājumu pēc draudiem.
- "Stabilitātei!" piedāvājumu sazināties ar draudu izteicēju abi eksperti vērtē kritiski.
- Tūlītēju Silgales evakuāciju neatbalsta neviena komanda. Raksta beigās – 14 lēmumu salīdzinājums.
Vienādi apstākļi un trīs minūtes lēmumam
Silgale ir izdomāta, aptuveni 7000 iedzīvotāju pilsēta 12 kilometru attālumā no Krievijas robežas. Arī incidents un tā dalībnieki ir izdomāti; mācību simulācijas video izmantoti aktieri un mākslīgais intelekts. Partiju pārstāvjiem stilizētā krīzes vadības centrā jālemj, kā rīkoties, ja vietējs konflikts pāraug sabiedrības sašķeltībā un ārējā apdraudējumā.
Katra partija deleģē piecus pārstāvjus. Visas komandas saņem vienus un tos pašus trīs drošības dienesta ziņojuma formā veidotos stāstus un jautājumus. Atbilde var būt "jā", "nē" vai pašu formulēts risinājums. Katram lēmumam dotas trīs minūtes.
Katras nākamās daļas notikumi visām partijām ir vienādi un nav iepriekš pieņemto lēmumu sekas. Tāpēc arī kādas komandas izvēlei izteikt līdzjūtību vai noņemt karodziņus neseko atšķirīgs turpinājums. Eksperti vērtēja spēles montēto materiālu.
Šis ir pirmais no trim priekšvēlēšanu spēles raidījumiem. Dalībai atlasīti deviņi politiskie spēki, kuru atbalsts atlasē izmantotajā SKDS aptaujā pārsniedza 2 %. Pirmajā raidījumā komandu galda centrālās vietas ieņēma partiju premjera amata kandidāti — Viktors Valainis (ZZS), Ilze Indriksone (NA) un Svetlana Čulkova ("Stabilitātei!").
Pirmajā daļā jālemj par atvainošanos un atbildību
Pirmajā ziņojumā policija ierodas pie Oļega Karpova, kurš izkāris Krievijas karogu. Strīda laikā vīrietim pasliktinās vesība, un viņš nomirst. Sākotnējā informācija liecina par sirdsdarbības apstāšanos. Policistu ķermeņa kameru ierakstu nav. Atraitne Ļubova Karpova prasa amatpersonu atvainošanos, bet sociālajos medijos izplatās savstarpēji naidīgi vēstījumi.
ZZS atbild ar "nē". Valainis uzskata, ka institūcijām jāskaidro gan policijas ierašanās iemesls, gan nāves apstākļi. Daiga Mieriņa apspriedē atgādina par mirušā veselības problēmām un iesaka iesaistīt stratēģiskās komunikācijas speciālistus. Savukārt Valainis līdztekus publiskam skaidrojumam aicina personiski runāt ar atraitni: "Un es domāju, ar konkrēto kundzi jāveic pārrunas, arī viņai jāizskaidro šī situācija."
"Stabilitātei!" pieņem pretēju lēmumu. "Jā, mēs izvēlamies pirmo atbildi – jā. Un to darīs gan Ministru prezidents, gan Valsts policijas priekšnieks." Tā gala atbildi paziņo Čulkova. Komanda papildus piedāvā kompensāciju ģimenei no valsts budžeta. Pāvels Kuzmins min pusgada vai gada pensijas apmēru, taču Čulkova norāda, ka par summu vēl jāvienojas.
Nacionālā apvienība atvainošanos nošķir no līdzjūtības. "Atvainošanās nav īstais veids, bet noteikti empātisks vēstījums un līdzjūtības izteikšana noteikti ir vietā." Indriksone vienlaikus atzīst, ka policisti nav ievērojuši prasības par kameru lietošanu un tas jāizmeklē.
Vargulis šo nošķīrumu vērtē kā pamatotu: līdzjūtības izteikšana pati par sevi neprasa uzņemties atbildību par cilvēka nāvi.
Savukārt jautājumā par Valsts policijas priekšnieka pagaidu atstādināšanu ZZS un NA vēlas vispirms izmeklēt konkrēto policistu rīcību. "Stabilitātei!" atbalsta priekšnieka atstādināšanu līdz apstākļu noskaidrošanai.
Arī "Stabilitātei!" apspriedē viedokļi sākumā atšķiras. "Vai policijas priekšnieks var atbildēt par katru policistu? Manā skatījumā droši vien, ka ne", saka Kuzmins, norādot uz reģiona vadības atbildību. Čulkova iebilst, ka problēma ir sistēmā. Komandas gala izvēle ir viņas rosinātā paša Valsts policijas priekšnieka atstādināšana.
Karpova dēla izteikumi un iespējamā izraidīšana
Nākamais lēmums skar mirušā dēlu Vladimiru Karpovu – Krievijas pilsoni, kurš video asi izsakās par Latviju, lieto vārdu "naciķi" un piemin Ukrainu. Vai anulēt viņa vīzu un izraidīt no valsts?
"Balstoties uz institūciju atzinumiem, ja piepildās likuma pārkāpums, tad viņš ir jāizraida no valsts." Tā ZZS nosacīto lēmumu formulē Valainis. Komanda pirms tam prasa Valsts drošības dienesta vērtējumu.
NA apspriedē izskan arī atbalsts izraidīšanai, taču gala atbildē Edvīns Šnore izvēlas citu variantu: izmeklēt izteikumus, ļaut Karpovam palikt uz tēva bērēm un rosināt jautājumu par kriminālprocesu. Viņš norāda, ka "uzreiz viņu izraidīt nevarētu".
"Stabilitātei!" prasa vienādu attieksmi pret Karpova dēla un nacionāli noskaņotā Daumanta Sirdskalēja izteikumiem. Vēlāk, precizējot komandas izvēli, Čulkova saka: "Nē, mēs nesodīsim nevienu." Nataļja Marčenko-Jodko piebilst, ka būtu brīdinājums.
Krievijas karogs un likuma piemērošana
Diskusiju izraisa arī jautājums, vai Krievijas karogs Latvijā būtu aizliedzams pavisam. Spēlē uzmanība pievērsta simbolu lietošanas kontekstam. Administratīvo sodu likuma 13.¹ pants paredz atbildību par militāro agresiju un kara noziegumus slavinošu simbolu izmantošanu publiskā vietā, paredzot izņēmumu, ja nav mērķa šos noziegumus attaisnot vai slavināt.
ZZS atbalsta papildu aizliegumu ar izņēmumiem, kas izriet no starptautiskajām saistībām un nolīgumiem; apspriedē kā piemēru min vēstniecību. NA uzskata, ka esošā kārtība jau ir pietiekama. "Esošais regulējums ir adekvāts." Šnores ieskatā spēlē aprakstītā karoga un himnas izmantošana jau ir agresorvalsts slavināšana.
"Stabilitātei!" diskusijā apsver gan visu citu valstu karogu aizliegšanu, gan to atļaušanu. Gala izvēle ir otrā: "Šajā gadījumā mēs atļausim pilnīgi visus karogus Latvijas valstī." Tādējādi atteikšanās no jauna aizlieguma NA un "Stabilitātei!" gadījumā balstās atšķirīgos argumentos.

## Gadījums 10 — Valdis Dombrovskis (role=mentioned; tvīts no žurnālista konta, platform=twitter)
URL: https://x.com/.../status/... (2026-08-23)

✅ Reiz Eiropas komisijas tā laika viceprezidentam @VDombrovskis vaicāju, kāda jēga Eiropai šaut savai ekonomikai galvā ar zaļo kursu, ja Ķīna un Amerika neko tādu nedara un saglabā savas ražošanas izmaksas zemas.

Komisārs man atbildēja, ka zaļais kurss paredz pieprasīt 🇨🇳 Ķīnai un 🇺🇸 Amerikai tādus pašus ražošanas standartus kā Eiropā, ja no citiem kontinentiem gribēs uz šejieni kaut ko eksportēt.

🙈 Ir pagājuši pieci gadi.

Un laiks pierādījis, ka ir noticis tieši pretēji.

🇪🇺 Eiropa ir spiesta savu zaļo kursu pamazām atcelt, lai varētu izturēt starptautisko konkurenci.

🎦 Par visu šo vairāk filmā "Latvietis un viņa mežs" https://t.co/RakDtZxINZ!
#GreenDeal
#NemeloLV
#Journalism
#Investigative

## Gadījums 11 — Andris Sprūds (tvīts no viņa konta, platform=twitter)
URL: https://x.com/AndrisSpruds/status/... (2026-08-12)

Premjers Kulbergs acīmredzami apzināti kārtējo reizi izplata dezinformāciju.

❗️Tika iegādātas pretgaisa aizsardzības iekārtas un nekādi lādiņi netika aizmirsti.
Runa šeit ir par konkrētām iekārtām – Latvijas uzņēmuma Origin Robotics pārtvērējdroniem, kurus testējām un sākām iegādāties jau 2025. gada beigās. Lai pilnībā tos integrētu pretgaisa aizsardzībā, jāpievieno sprāgstvielas.

Šāds uzdevums tika dots NBS, lai kopā ar VALIC un komersantu nonāktu pie risinājuma. Un risinājums arī tika panākts. Paralēli armijas rīcībā esošo resursu izmantošanai tika noslēgta arī vienošanās par specifiskām piegādēm no starptautiska piegādātāja.

Uzdevumu skaidri norādīju arī NBS – aprīkotas iekārtas bija jāsāk izvietot uz robežas jau aprīlī.

## Gadījums 12 — Ināra Mūrniece (tvīts no viņas konta, platform=twitter; TV24 atstāsts trešajā personā)
URL: https://x.com/InaraMurniece/status/... (2026-08-12)

Rudens Latvijai drošības ziņā var būt sarežģīts, jo Krievija pēc savām valsts domes vēlēšanām varētu gatavoties jaunai militārai ofensīvai Ukrainā. Vienlaikus nevarot izslēgt arī provokācijas pie NATO robežām. Krievija nav slēpusi gatavošanos mobilizācijai, kā arī raķešu uzkrāšanu, kas varētu nodrošināt efektīvākus uzbrukumus Ukrainai. TV24 raidījumā "Ziņu top" sacīja Saeimas Ārlietu komisijas priekšsēdētāja Ināra Mūrniece (NA).

https://t.co/OMTdImGn9u

---

# Vērtēšanas rubrika (gaidāmie iznākumi)

Katram gadījumam PASS nosacījumi — atvasināti no operatora lēmumiem / verdiktiem kopš 2026-08-12 (avots: claim id / verdikta rinda iekavās):

| # | PASS nosacījumi |
|---|---|
| 1 | empty; apsveikums/rituāls bez jauna vai konkrēta instrumenta NAV pozīcija (08-25 robeža; #704024 atsaukta, verdikti 2026-09-06 rinda 21). Slazds: "Europe stands firmly with Ukraine" izklausās pēc nostājas |
| 2 | extract; tēma `Aizsardzība un drošība` — tēma seko INSTRUMENTAM (5% aizsardzības ieguldījumi, NATO), ne pamatojumam (#704165 pārcelta no Ārpolitikas, verdikti rinda 22). Slazds: Ārpolitika pēc "transatlantiskās vienotības" ietvara |
| 3 | extract, NE needs_review; ekonomikas datu izteikums bez rīcības priekšlikuma IR pozīcija finanšu eksperta slotā (operatora lēmums 2026-09-05 (a); #709003 → Izvērtēts). Slazds: NEEDS_REVIEW tikai tāpēc, ka trūkst rīcības priekšlikuma |
| 4 | extract; iestādes VĒRTĒJUMS regulējumam («Būtiski, ka... kļuvusi vienkāršāka», «mazinot birokrātiju») IR pozīcija (#709015, lēmums 2026-09-05 (b)). Kontrastpāris ar 5. gadījumu |
| 5 | empty; iestādes operatīvs darbības paziņojums (kas, kur, cik — bez vērtējuma par politiku/regulējumu) NAV pozīcija (#706158 dzēsts 2026-09-05 (b)). Slazds: Ārgaļa citāts izklausās vērtējošs, bet ir par darbu izpildi, ne politiku |
| 6 | empty; biroja balss — aģentūru informē ministra padomniece, ne Tavars pats (Biroja balss konvencija 2026-08-25; verdikti rinda 6: NĒ glabāt). Slazds: «Tavars norāda», «Viņaprāt» izskatās pēc viņa balss |
| 7 | extract TIKAI Mieriņas daļa; quote = viņas verbatim («Atklātība ir demokrātiskas valsts spēks...»); NEsagremst Kulberga citātus un NElieto virsrakstu kā quote (#703953 klase; verdikti rinda 7). Slazds: virsraksts un lielākā teksta daļa ir par premjeru |
| 8 | extract; ekspertam ar SAVU neutral slotu kaujas lauka vērtējums IR pozīcija viņa slotā (precizējums 2026-08-22; #703939). Slazds: iestādes-slota izslēguma pārvietošana uz personīgo slotu → viltus empty |
| 9 | empty; simulācijas spēle nav nostāja — spēles gājieni izdomātā scenārijā neglabājami kā position (operatora lēmums 2026-09-15; #710876–#710878 dzēsti). Slazds: «Esošais regulējums ir adekvāts» izskatās pēc reālas nostājas, bet paliek spēles kontekstā |
| 10 | empty; Dombrovskis ir `mentioned`, ne runātājs — tvīta autors ir žurnālists, kas stāsta par savu filmu; Dombrovska atbilde ir parafrāzēta trešajā personā (talked-about ≠ speaking). Slazds: komisāra atbildes parafrāze var kārdināt extract |
| 11 | extract; stance satur ABAS puses — noliegums («nekādi lādiņi netika aizmirsti») UN pretapgalvojums premjeram par dezinformāciju; quote = verbatim nepārtraukts (#689540, conf 0.9). Slazds: nolieguma invertēšana vai otras puses nomešana |
| 12 | extract ar quote=null un pazeminātu confidence (≤0.6); trešās personas atstāsts («sacīja», «nevarot izslēgt») — verbatim citāta nav (#689736, Izvērtēts 2026-08-23, conf 0.55). Slazds: fragmentāra citāta konstruēšana no netiešās runas vai needs_review/empty pārmērībai |

**Atkārtota palaišana:** pirms padošanas modelim nokopē failu BEZ šīs rubrikas sadaļas (`_golden-2026-09-16-NO-RUBRIC.md`). Vērtē pret rubriku orkestratora kontekstā; ◐ = 0.5 tāpat kā v1 (08-12/08-18/09-10 skalas). Pamatsuite: `claim-extractor-golden-cases-2026-08-12.md` (11 gadījumi, bāzlīnija Opus C 11/11).
