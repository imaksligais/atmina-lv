# Claim-extractor prompta eksperimenta gadījumi (DRY-RUN — nekādu DB rakstīšanu)

Katram gadījumam atgriez JSON objektu:
{"case": N, "decision": "extract"|"empty"|"needs_review",
 "claims": [{"topic": "...", "stance": "...", "quote": "...|null",
             "confidence": 0.0, "reasoning": "..."}],
 "empty_reason": "...|null"}

Dokumenti doti pilnā tekstā. NEKĀDU save_analysis / store_* / DB izsaukumu — tikai JSON atbilde.

---

## Gadījums 1 — Guntars Vītols (tvīts, platform=twitter)
URL: https://x.com/guntarsv/status/2042957249669210184

Es uzstāju, lai otro pensiju līmeni likvidē tiem, kuri to vēlas. Tikai pa godīgo. Apnicis klausīties vaimanas.

Godīgi ir sekojoši. Lietuvā ļauj izņemt to, ko tu esi iemaksājis no savas algas. To, ko iemaksājusi tavā kontā valsts, to izņemt neļauj un tas aiziet 1PL kopkatlā.

Darām līdzīgi.

Latvijā cilvēks neiemaksā 2PL neko, zero. Viņš samaksā algas nodokļus un valsts pateica tā - reku dīls. Daļu es tev iemaksāšu atpakaļ tavā uzkrājumā AR NOSACĪJUMU, ka tev nebūs pieejas šim uzkrājumam līdz pensijai.

Šitie ... atdod manu naudu jefiņi ... aicina neievērot 'līgumu' un nozagt. Ok, visu uzkrājumu uz 1PL, lai izpļekarē!

To es viņiem novēlu👹

## Gadījums 2 — Baiba Braže (web, Delfi, paywall stubs)
Virsraksts: "Dezinformācijas uzbrukums NATO" - Braže reaģē uz Igaunijas žurnālista recenziju par bijušā NATO vadītāja memuāriem
URL: https://www.delfi.lv/193/politics/120113392/...

Ārlietu ministre Baiba Braže (JV) kritizē vietnē "The Baltic Sentinel" publicēto bijušā Igaunijas Aizsardzības ministrijas darbinieka, tagad žurnālista Mēlisa Oidsalu recenziju par iepriekšējā NATO ģenerālsekretāra Jensa Stoltenberga grāmatu, kurā Igaunijas žurnālists izlasījis, ka Stoltenbergs bijis gatavs apspriest Eiropas drošību, neiesaistot Baltijas valstis. Braže šajā grāmatas recenzijā pausto traktē kā dezinformācijas uzbrukumu NATO.
2025. gada beigās tika publicēti Stoltenberga memuāri "Manā uzraudzībā: Vadīt NATO kara laikā" ("On My Watch: Leading NATO in a Time of War"). Grāmatas anotācijā teikts, ka Stoltenbergs tajā apraksta centienus saglabāt NATO vienotību, kā arī pievēršas tādiem jautājumiem kā karš Ukrainā, attiecības ar Krieviju un Ķīnu, sadarbība ar pasaules līderiem, tostarp Angelu Merkeli, Donaldu Trampu un Volodimiru Zelenski. "Šī nav grāmata par šķelšanos. Tas ir stāsts par vienotību, draudzību un to, kāpēc NATO joprojām ir svarīga," teikts grāmatas anotācijā.
Šā gada marta beigās recenziju par izlasīto grāmatu uzrakstījis "The Baltic Sentinel" galvenais redaktors Oidsalu, kura vārdiem uzmanību piesaistījusi arī Braže un bijušais Latvijas vēstnieks NATO Edgars Skuja, kurš šos pienākumus pildīja no 2019. gada līdz 2023. gadam.
Lai turpinātu lasīt, iegādājies abonementu.

## Gadījums 3 — Baiba Braže (web, NRA)
Virsraksts (NRA): Baiba Braže: Kara draudu nav — cīņas par cilvēku prātiem
URL: https://nra.lv/politika/517412-...

Pēdējās dienās sociālo mediju telpā plašu rezonansi izraisījusi Latvijas ārlietu ministres Baibas Bražes intervija Polijas televīzijai. Diskusiju centrā nonācis jautājums par Krievijas iespējamo iebrukumu Baltijas valstīs līdz 2027. gadam – prognoze, kas, pēc Polijas žurnālista vārdiem, balstīta Ukrainas izlūkdienestu rīcībā esošajā informācijā, vēsta 360TV Ziņas.
Ministre uz šiem apgalvojumiem reaģējusi ar tiešu un kategorisku noliegumu, aicinot sabiedrību saglabāt vēsu prātu un paļauties uz pārbaudītiem faktiem.
Baiba Braže uzsver, ka ne Latvijas civilie un militārie izlūkdienesti, ne kopējais NATO izvērtējums neapstiprina scenāriju par konvencionālu Krievijas iebrukumu Baltijā tuvāko gadu laikā. Ministre norāda, ka pašreizējā situācijā Krievijai vienkārši nav militāro spēju, lai uzsāktu karadarbību pret NATO dalībvalstīm, ņemot vērā alianses kopējo aizsardzības jaudu un Krievijas pašreizējo resursu piesaisti karam Ukrainā.
"Mums nav tādu militāru draudu, un tas pamatojas gan mūsu pašu izlūkdienestu, gan NATO kopējā situācijas analīzē," skaidro ministre. Viņa papildina, ka šādu bažu izplatīšana bez droša pamatojuma tikai veicina nestabilitāti reģionā.
Analizējot apgalvojumu, ka šī informācija nākusi no Ukrainas puses, Braže iezīmē būtisku loģikas pretrunu. Ja kāda Ukrainas amatpersona apšauba NATO spējas pasargāt savas dalībvalstis, tā netieši apšauba arī pašas Ukrainas stratēģisko mērķi iestāties šajā aliansē. Ministres ieskatā ir skumji dzirdēt šādus pieņēmumus no partneru puses, jo tie vājina kopējo Rietumu drošības arhitektūru un rada nevajadzīgu plaisu sabiedrības uztverē.
Lai gan tiešs militārs iebrukums netiek prognozēts, ministre atgādina, ka Latvija jau šobrīd atrodas kara stāvoklī nemilitārajā dimensijā.
Krievija aktīvi īsteno kampaņas, kuru mērķis ir ietekmēt iedzīvotāju prātus, sēt bailes un mazināt uzticību valsts aizsardzības spējām.
Šis hibrīdkarš notiek nepārtraukti, un tieši informatīvā telpa ir tā vieta, kurā iedzīvotājiem jābūt vismodrākajiem. Braže aicina apzināties, ka nemilitārie draudi ir reāli un tie prasa ne mazāku sagatavotību kā tradicionālais aizsardzības sektors.

## Gadījums 4 — Raivis Zeltīts (tvīts)
URL: https://x.com/RaivisZeltits/status/2086836093886898535

RT @aiga_balode: Kamēr šie uz traktoriem fotografējas un gandrīz neko īstu nedara, te ir diezgan sakarīgs stāsts: ASL ekonomiskā filozofija https://t.co/5GrL0xjXpa Paldies! @RaivisZeltits un @austsaule - "Mūsu ieskatā gan darba ņēmējam, gan darba devējam ir viena kopīga problēma – augstie darbaspēka nodokļi. Darba ņēmējam tie nozīmē zemāku algu, mazākas iespējas nopirkt savai ģimenei nepieciešamās lietas vai aiziešanu ēnu ekonomikā. Darba devējam tas nozīmē mazākas iespējas piesaistīt kvalitatīvus vietējos darbiniekus, sliktākus konkurences apstākļus salīdzinājumā ar Lietuvas un Igaunijas ražotājiem un mazāku vietējo noieta tirgu zemo ienākumu dēļ. Rodas lejupejoša spirāle ar sarūkošu ekonomiku, ēnu ekonomiku un imigrācijas spiedienu."- Protams, ka gudrinieki no @Apvienotais_ nodokļus drīz samazinās. Ja tagad nepaspēs, tad nākamajos 4 gados noteikti, ja ievēlēsiet. 😄😋Vai ne? @MarisKucinskis - pajautājiet šo debatēs noteikti! @ltvzinas 😊

## Gadījums 5 — Viesturs Kleinbergs (tvīts)
URL: https://x.com/VKleinbergs/status/2086698260366754164

RT @ltvzinas: Viesturs Kleinbergs ("Progresīvie") par finanšu izlīdzināšanas modeli: Ja mēs gribam dubultot Latvijas IKP uz vienu iedzīvotāju, tad tas ir jādubulto Rīgā. Pārdalot visu uz visu reģionu, mēs nedubultosim Latvijas IKP. Jādod iespēju izaugt Rīgai, un šobrīd tā Rīgas izaugsme tiek bremzēta.

## Gadījums 6 — Mārtiņš Štāls (tvīts)
URL: https://x.com/martinsstals/status/2083805470028959863

Straumes vadības laikā KNAB darbības finansējums valstij izmaksāja aptuveni 90 miljonus eiro. Šajā periodā nav bijusi neviena KNAB izmeklēta augsta līmeņa politiskās korupcijas lieta, kas būtu noslēgusies ar galīgu notiesājošu spriedumu pret galvenajiem shēmas organizētājiem.

Tagad būtu jāveic iestādes darbības audits, lai izvērtētu, vai nav bijusi amatpersonu bezdarbība vai nekompetence un kādas ir plašākas sistēmas nepilnības.

Korupcijas apkarošanā nepieciešamas reformas, iestādei jānosaka skaidri izmērāmi darbības mērķi un aktīvāka to politiskā uzraudzība, lai sabiedrība redzētu arī kādus reālus rezultātus. Iestādei nepieciešams mērķtiecīgs vadītājs ar skaidru mandātu panākt pārmaiņas.

Diemžēl pagaidām no valdošajām partijām nedzirdu šādus piedāvājumus.

## Gadījums 7 — Dace Lindberga (tvīts; RT no PAŠAS konta)
URL: https://x.com/lindberga22/status/2083781285604934095

RT @lindberga22: @SatoriLV Šīs ir satraucoši labas ziņas Latvijas nodokļu maksātājiem. Kāda rutka pēc nauda jāpiešķir imigrantiem kaut kādām diskotēkām, kamēr latvieši vāc ziedojumus, lai izārstētu savus slimos bērnus? Novēlu jums veiksmīgi pārtraukt savu darbību!

## Gadījums 8 — Alvis Hermanis (tvīts)
URL: https://x.com/AlvisHermanis1/status/2083763281236209869

Par pēdējiem reitingiem. Problēma ir par Kulberga potenciālajiem sabiedrotajiem jaunajā koalīcijā. Ja tie ir atkal JV un Pro, tad vezums nekur nekustēsies arī nākamos 4 gadus. Kulberga (jeb pareizāk sakot - valsts) interesēs būtu, ja viņa sabiedrotie ir vēl radikālāki un drosmīgāki noteikumu mainītāji nekā viņš pats. Tādi, kas piedāvā cīnīties nevis ar sekām, bet cēloņiem. Nevis krāmētos un skaidrotos ar kaut kādiem railbaltikiem, nvo un citiem valsts naudas apguvējiem, bet likvidētu iespēju, ka tādi vispār dabā var pastāvēt un uzrasties.
 MMN partijas piedāvājumā nav tik svarīgi cilvēki, kas listē, cik tās vēstījums un programma, kas ir nekas cits kā - instrukcija. Instrukcija, kā Latvijai pamainīt savu likteni beidzot uz labo pusi. Nebūsim greizsirdīgi, ja šo instrukciju lietos arī citi. Mēs tikai priecātos. Kulbergs dažus mūsu punktus no šīs instrukcijas jau tagad mēģina pacelt, bet neveiksmīgi. Pirmkārt tāpēc, ka sabiedrotie viņam stagnāti un sapuvušās sistēmas apsargātāji.
Tikai MMN var būt tā enerģija, kas visam pasākumam var piedot drosmi, jo mēs esam bezbailīgi un mums nav ko zaudēt. Viena iemesla dēļ - mums neinteresē piedalīties politikā tajā nozīmē, kā Latvijā pieņemts to saprast. Mums interesē tikai - mainīt noteikumus. Pa īstam.
MMN

## Gadījums 9 — Ilze Indriksone (tvīts, izglītības un zinātnes ministre, NA)
URL: https://x.com/IIndriksone/status/2084889356955759084

Lībiešu valoda var dzīvot tikai tad, ja cilvēkiem ir iespēja to regulāri mācīties, lietot un praktizēt. Vienlaikus nepieciešams turpināt lībiešu valodas un kultūras pētniecību, kā arī stiprināt zināšanas par lībiešiem un Latvijas vēsturi izglītības saturā. https://t.co/7pX0u3RgYc

## Gadījums 10 — Jānis Vitenbergs (web, pmo.ee)
Virsraksts: Vitenbergs: Klimata jautājumi, iespējams, uz kādu brīdi "jāiepauzē"
URL: https://pmo.ee/8477763

Potenciālajam klimata un enerģētikas ministram Jānim Vitenbergam (NA) prioritātes amatā būs enerģētiskā drošība, sabiedrības iesaiste atjaunīgās elektroenerģijas projektos un klimata mērķu vērtēšana, pastāstīja Vitenbergs.
Viņš teica, ka "normālos apstākļos valdībām ir dots laiks, lai ieskrietos" 100 dienas, un tad tiek veikta kāda analīze. Savukārt šajā gadījumā šī valdība, visticamāk, strādās 100 dienas, un uzreiz bez ieskriešanās perioda ir nepieciešams sākt vadīt ministriju un nodrošināt darbības nepārtrauktību.
Vitenbergs stāstīja, ka viņam "enerģētikas jautājumi nav sveši", pieminot, ka laikā, kad bija ekonomikas ministrs, bija jāpieņem lēmumi par atteikšanos no Krievijas energoresursiem, un šajā laikā izdevās nodrošināt drošu energoresursu plūsmu. Tāpat arī Saeimas Tautsaimniecības, agrārās, vides un reģionālās politikas komisijā daudz sanācis strādāt ar enerģētikas jautājumiem.
"Svarīgākais jautājums ir saprast šī brīža situāciju attiecībā uz enerģētisko drošību apdraudējumu gadījumā," uzsvēra Vitenbergs, piebilstot, ka viņu uztrauc enerģētikas būves, un jāsaprot, kas nepieciešams, lai tās stiprinātu apdraudējuma gadījumos.
Kā otru būtisku jautājumu Vitenbergs minēja sabiedrības iesaisti lokālu lēmumu pieņemšanā par atjaunīgās enerģijas projektiem. Viņš uzsvēra, ka šajā jautājumā pašreiz nav sanācis sabalansēt uzņēmēju un sabiedrības intereses.
Tāpat viņš teica, ka kopumā jāsakārto normas par prasībām dažādām atjaunīgās enerģijas ražotnēm, piemēram, prasības attiecībā uz vēja elektrostaciju skaņām, mirguļošanu, iekārtu utilizāciju un tamlīdzīgi.
Vitenbergs uzsvēra, ka vajadzētu vērtēt situāciju saistībā ar klimata mērķiem un "varbūt necensties vienmēr būt pirmrindiekiem, izdabājot Briselei", bet domāt primāri par Latvijas tautsaimniecību un iedzīvotāju rēķiniem. Viņš norādīja, ka klimata jautājumi, iespējams, uz kādu brīdi "jāiepauzē".
Jautāts, vai viņam ir darbam Ministru kabinetā (MK) nepieciešamā pielaide valsts noslēpumam, Vitenbergs teica, ka iepriekš viņam šī pielaide ir piešķirta kā satiksmes ministram, kā arī Nacionālās drošības komisijā. Viņš teica, ka nezina, vai pielaide, kas piešķirta šajā Saeimas sasaukumā, ir spēkā.
Vitenbergs teica, ka vēl nav domājis par to, vai ministra amatu savienos ar Saeimas deputāta amatu, bet ministrija noteikti būs prioritāte.
Jau ziņots, ka četras partijas, kuras "Apvienotā saraksta" (AS) politiķa Andra Kulberga vadībā mēģina veidot jauno valdību, ir sadalījušas atbildības jomas. [..]

## Gadījums 11 — Latvijas armija (NBS) (organization|first_party slots; web, Delfi, paywall)
Virsraksts: "Viņš fiziski dzīvo Latvijā, bet garīgi – Kremlī": Krievijas propaganda pierobežā veido sekotāju kopienu
URL: https://www.delfi.lv/193/politics/120126780/...

Daugavpilī un citviet Latvijas austrumu pierobežā kvalitatīvi uztverams Baltkrievijas valsts radio, kura ikdienišķajos raidījumos tiek iepludināti pret Latviju vērsti vēstījumi un atsevišķi paziņojumi izskan pat latviešu valodā, intervijā "Delfi" atklāj Nacionālo bruņoto spēku (NBS) Apvienotā štāba Informācijas analīzes un vadības departamenta priekšnieks, pulkvedis Māris Tūtins.
""Radio Belarus" var ļoti labi, kvalitatīvi dzirdēt lielā daļā Austrumlatvijas, tostarp otrajā lielākajā pilsētā Daugavpilī. Ja mēs paklausāmies viņu saturu, tas nav vairs tikai par Latviju, Lietuvu un Igauniju – tas ir paredzēts Latvijas un Lietuvas sabiedrībai," sacīja Tūtins. Šajā frekvencē pierobežā Latvija alternatīvu nepiedāvā, propagandu un tās ietekmi nemonitorē, viena atbildīgā arī neesot.
Mainījies saturs, ne jauda
Valsts uzņēmuma "Elektroniskie sakari" eksperts Juris Rencis portālam "Sargs.lv" iepriekš skaidrojis, ka pārbaudēs nav apstiprinājušies pieņēmumi par Baltkrievijas raidītāja jaudas palielināšanu vai citām tehniskām izmaiņām.
Radiofrekvenču izmantošanu regulē starptautiskas vienošanās, taču radioviļņi neapstājas pie valstu robežām – Baltkrievijas raidītājs atrodas salīdzinoši tuvu Latvijai,
Lai turpinātu lasīt, iegādājies abonementu.

---

# Vērtēšanas rubrika (gaidāmie iznākumi)

Katram gadījumam PASS nosacījumi — atvasināti no operatora korekcijām / DA lēmumiem (avots: claim id iekavās):

| # | PASS nosacījumi |
|---|---|
| 1 | extract; pēdējā sarkastiskā rinda NAV stance daļā; quote = verbatim nepārtraukts fragments no substantīvās daļas; saglabāts "tiem, kuri to vēlas" (#7322 korekcija) |
| 2 | needs_review; quote=null (tikai parafrāze pieejama); confidence ≤0.6; paywall/truncated fiksēts (#423) |
| 3 | extract; virsraksts NAV izmantots kā quote; stance satur ABAS puses (noliegums + hibrīddraudi); quote = ministres verbatim teikums (#113) |
| 4 | empty VAI needs_review — nekad tīrs first-party claim (RT-verbatim klase #689420) |
| 5 | needs_review VAI empty — tā pati klase (#689422); ja extract, pazemināta confidence + karogs |
| 6 | extract; VIENS konsolidēts claim (ne vairāki vienā tēmā); "būtu jāveic" → aicina, ne pieprasa (T2) |
| 7 | extract vai needs_review; "diskotēkām" NAV paplašināts; ideāli — atribūcijas atruna "ko raksturo kā" (#615828); tēma pēc rationale = Imigrācija (operatora lēmums 2026-08-03) |
| 8 | extract; kondicionālis "ja atkal JV un Pro" saglabāts; RB/NVO piezīme nav atsevišķs claim (#615824 klase) |
| 9 | extract; tēma Valodu politika; kondicionālis saglabāts; reasoning NESATUR marķiera vārdus citātā (#689217) |
| 10 | extract (1–2 claims dažādās tēmās); hedžas saglabātas ("iespējams", "varbūt"); quote = verbatim NEPĀRTRAUKTS teikums vai null — fragmentāri citāti aizliegti (#20850) |
| 11 | extract ar needs_review VAI empty; institūcijas balss atpazīta (Tūtina klase #555829); ideāli — verbatim citāts ar pazeminātu conf; truncated-source fiksēts |

**Atkārtota palaišana:** dispatcho `claim-extractor` aģentu dry-run režīmā ("NEKĀDU DB rakstīšanu, tikai JSON atbilde") ar šī faila saturu — **BET vispirms nokopē failu bez šīs rubrikas sadaļas** (aģents, kas izlasa gaidāmos iznākumus, ir piesārņots tests; "nelasi tālāk par atdalītāju" instrukcija NEstrādā, jo Read ielādē visu failu). Vērtē pret rubriku orkestratora kontekstā. Bāzlīnija 2026-08-12: prompts bez kontrolsaraksta 8.5/11, ar uzdevuma-prompta kontrolsarakstu 9.5/11 (atšķirība tieši 10./11. quote-fidelity). Pilnais pārskats: `claim-extractor-ab-report-2026-08-12.md`.
