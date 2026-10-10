# Partiju tests — kodējuma melnraksts (T1, automātisks, tikai lasīts no DB)

<!-- u3: {"datums": "2026-09-14", "sunas": 70, "sakrit": 63, "nostajas_mainitas": 7} -->
<!-- d1b: {"datums": "2026-09-22", "parceltas": 15, "zari": 7} -->


Katrai šūnai: **PIEMIN** = atslēgvārds trāpa pozīcijas tekstā (kandidāts par/pret), **TĒMA** = partijai ir pozīcija tēmā, bet atslēgvārds netrāpa (visticamāk klusē), **KLUSĒ?** = tēmā pozīcijas nav. Kodējums ir cilvēka lēmums pret avota tekstu.


## Kopsavilkums (partiju skaits, kas apgalvojumu piemin — augšējā robeža)

| id | piemin | apgalvojums |
|---|---|---|
| k01 | 11 | Aizsardzībai jāatvēl vismaz 5 % no IKP arī tad, ja tāpēc jāsamazina citi izdevumi. |
| k02 | 13 | Latvijai jāturpina atbalstīt Ukrainu, kamēr karš nav beidzies. |
| k03 | 7 | Ekonomiskie sakari ar Krieviju un Baltkrieviju jāatjauno, tiklīdz tas ir iespējams. |
| k04 | 10 | Obligātais valsts aizsardzības dienests jāsaglabā. |
| k05 | 10 | Cilvēkiem ar lielākiem ienākumiem nodokļos jāatdod lielāka ienākumu daļa nekā cilvēkiem ar mazākiem. |
| k06 | 11 | Pievienotās vērtības nodoklis pārtikai vai citām pamatprecēm jāsamazina. |
| k07 | 12 | Ja valsts nespēj nodrošināt ārstēšanu laikā, valstij tā jāapmaksā privātā iestādē. |
| k08 | 11 | Skolotāju algas jāceļ ātrāk nekā citās valsts sektora nozarēs. |
| k09 | 6 | Augstskolu skaits jāsamazina, apvienojot tās. |
| k10 | 11 | Darbaspēka imigrācija no trešajām valstīm jāierobežo arī tad, ja uzņēmumiem trūkst darbinieku. |
| k11 | 9 | Skolās jāmāca tikai latviešu valodā, bez izņēmumiem mazākumtautību valodām. |
| k12 | 4 | Nepilsoņiem pilsonība jāpiešķir atvieglotā kārtībā. |
| k13 | 12 | Ministriju skaits jāsamazina, tās apvienojot. |
| k14 | 11 | Lielāka nodokļu daļa jāatstāj pašvaldībām, mazāk jāpārdala caur valsts budžetu. |
| k15 | 6 | Rail Baltica jāpabeidz pilnā apjomā arī tad, ja izmaksas turpina augt. |
| k16 | 6 | Latvijas lauksaimnieku tiešmaksājumi jāpielīdzina ES vidējam līmenim. |
| k17 | 6 | Satversmē ģimene jādefinē kā vīrieša un sievietes savienība. |
| k18 | 9 | Latvijai jāsasniedz klimatneitralitāte ES noteiktajā termiņā, pat ja tas sadārdzina enerģiju. |
| k19 | 6 | Jaunas vēja elektrostacijas jābūvē arī tad, ja vietējie iedzīvotāji iebilst. |
| k20 | 7 | Pensiju 2. līmenim jābūt brīvprātīgam, ar tiesībām uzkrājumu izņemt. |
| k21 | 7 | Sabiedriskajam medijam jāpārtrauc raidīt krievu valodā. |
| k22 | 8 | airBaltic jāpārdod privātiem investoriem. |
| k23 | 6 | Valsts prezidents tautai jāievēl tiešās vēlēšanās. |
| k24 | 7 | Par korupciju notiesātām personām uz mūžu jāaizliedz ieņemt valsts amatus. |
| k25 | 10 | Nekustamā īpašuma nodoklis vienīgajam mājoklim jāatceļ. |


## k01 — Aizsardzībai jāatvēl vismaz 5 % no IKP arī tad, ja tāpēc jāsamazina citi izdevumi.

Tēmas: Aizsardzība un drošība, Budžets un finanses  
Kodēšanas atgādne: par = 5 % vai vairāk; pret = samazināt / pārdalīt aizsardzības budžetu


### JV — PIEMIN

- claim_id 532665 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts nodrošināt aizsardzības finansējumu 5% apmērā no IKP un attīstīt NATO sabiedroto pastāvīgu klātbūtni Latvijā. Paredzēts stiprināt pretgaisa, dronu un pretdronu un citas mūsdienīgas aizsardzības spējas, izmantojot Ukrainas pieredzi, attīstīt vietējo militāro un divējāda lietojuma industriju, stiprināt Nacionālos bruņotos spēkus un Zemessardzi, palielināt apmaksāto brīvdienu skaitu zemessargiem, kā arī stiprināt civilās aizsardzības sistēmu un iekšlietu dienestus – ugunsdzēsēju, policijas un robežsardzes kapacitāti.
- claim_id 532670 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot fiskāli atbildīgu budžetu ar valsts ārējā parāda līmeni zem 55% no IKP, ievērojot eirozonas fiskālos noteikumus. Paredzēts celt minimālo algu līdz 50% no vidējās bruto darba samaksas, palielināt fiksēto neapliekamo minimumu līdz 80% no minimālās algas, padarīt nekustamā īpašuma nodokli par pilnvērtīgu pašvaldību nodokli, attīstīt kapitāla tirgu un valsts attīstības fondu. Ekonomikā izvirzīts mērķis panākt vismaz 3,5% IKP izaugsmi gadā un investīcijas virs 30% no IKP, pārejot uz augstas pievienotās vērtības ekonomiku.

### PRO — PIEMIN

- claim_id 532636 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts saglabāt finansējumu aizsardzības nozarei vismaz 5% apjomā, attīstīt aizsardzības industriju un industrijas parkus atbilstoši NBS vajadzībām, nodrošināt tehnoloģiski un fiziski drošu valsts robežu, saglabājot cilvēktiesībās balstītu pieeju, un turpināt patvertņu izbūvi un iedzīvotāju sagatavošanu krīzes apstākļiem.

### ZZS — PIEMIN

- claim_id 547879 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi līdz 2030. gadam panākt IKP izaugsmi vismaz par 2% virs ES vidējā, ikgadējās ārvalstu investīcijas vismaz 1 mljrd. € apmērā un IKP pieaugumu +3,8 mljrd. € gadā, minimālo algu 1250 € un vidējo algu 2500 €. Sola vienkāršāku nodokļu sistēmu mazajam biznesam, nodokļu atlaides ieguldījumiem ražīguma, efektivitātes un digitalizācijas celšanai, Latvijas kreditēšanas un investīciju fonda un krājaizdevu sabiedrību attīstību, eksporta veicināšanu un klasterus, kā arī darba ražīguma pieaugumu vismaz 5% gadā. Dzīves dārdzības mazināšanai sola samazinātu PVN (5% pirmās nepieciešamības pārtikai, 12% sabiedriskajai ēdināšanai un izmitināšanas pakalpojumiem), 0% nekustamā īpašuma nodokli primārajam mājoklim, attaisnoto izdevumu slieksni 1800 €, mazumtirdzniecības uzraudzības un 'pārtikas groza' iniciatīvas pilnveidi un sabiedrisko pakalpojumu cenu auditu.
- claim_id 547882 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi aizsardzībai novirzīt virs 5% no IKP. Sola stabilu aizsardzības un drošības finansējuma pieaugumu ar stiprinātu parlamentāro kontroli, stiprināt NBS, Zemessardzes un iekšlietu sistēmas spējas, pastiprināt austrumu robežas un jūras drošību, militāro infrastruktūru un sabiedroto klātbūtni, modernizēt civilo aizsardzību (patvertnes, brīdināšanas sistēmas, ģeneratoru punkti visās pilsētās un ciemos), nodrošināt materiālās rezerves un krīzes krājumus, modernizēt pierobežas drošības infrastruktūru, kā arī attīstīt aizsardzības industriju (munīcija, droni, enerģētika), lai drošības finansējums paliktu Latvijas ekonomikā.

### NA — PIEMIN

- claim_id 532704 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts palielināt aizsardzības finansējumu virs 5% no IKP, attīstot vietējo militāro industriju, turpināt NBS attīstību pretgaisa aizsardzības (t.sk. dronu un pretdronu spēju), sauszemes un krasta apsardzības jomā, paplašināt rezervistu skaitu un atbalstu NBS, ZS un VAD dienošajiem, celt iekšlietu dienestu kapacitāti un atalgojumu, nodrošināt kritiskās infrastruktūras aizsardzību un valsts vadošo lomu civilās aizsardzības un patvertņu izveidē, kā arī pilnveidot valsts stratēģiskās rezerves.
- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.

### LPV — PIEMIN (citā tēmā)

- claim_id 532659 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts veikt izmaiņas Satversmē, ļaujot Valsts prezidentu ievēlēt Latvijas tautai, un samazināt parakstu slieksni referendumu ierosināšanai no 10% līdz 5% balsstiesīgo.
  
  **Citāts:** „Veiksim izmaiņas Satversmē, ļaujot Valsts prezidentu ievēlēt Latvijas tautai.”

### AS — TĒMA

- claim_id 532820 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Paplašinās Valsts aizsardzības dienestu ar papildu dienesta virzieniem, stiprinās Zemessardzes kaujas spējas un rezerves karavīru apmācību, pabeigs austrumu robežas aizsardzības līniju un novērošanas infrastruktūru. Civilajā aizsardzībā ieviesīs reālistiskus reģionālus krīžu plānus, izveidos patvertņu tīklu, veiks valsts rezervju auditu un slēgs priekšlīgumus ar uzņēmumiem ātrai reaģēšanai. Stiprinās policiju, robežsardzi un VUGD ar apdraudējumiem atbilstošu materiāltehnisko nodrošinājumu.
  
  **Citāts:** „Paplašināsim Valsts aizsardzības dienestu, piedāvājot papildu dienesta virzienus, kas nepieciešami visaptverošai valsts aizsardzībai.”
- claim_id 532822 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Sasniegs bezdeficīta bāzes budžetu četru gadu laikā. Stabilizēs nodokļu politiku, pārtraucot tās regulāru pārskatīšanu; ieviesīs mikrouzņēmumu nodokļa 10% likmi fiziskajām personām, samazinās kapitāla pieauguma IIN līdz 17% un saglabās UIN režīmu (peļņu apliekot tikai tad, kad to sadala dividendēs). Samazinās nodokļu maksātāju administratīvo slogu un mazinās ēnu ekonomiku ar motivāciju strādāt legāli, ne sodīšanu. Izveidos valsts garantiju programmu mājokļu būvniecībai reģionos, palielinot kreditēšanu par 2 miljardiem, koncentrēs valsts atbalstu augstas pievienotās vērtības nozarēs, samazinās valsts tiešo iejaukšanos ekonomikā un sekmēs publiskās un privātās partnerības projektus.
  
  **Citāts:** „Mūsu prioritāte ir ieviest kārtību valsts finansēs, lai sasniegtu bezdeficīta bāzes budžetu četru gadu laikā.”

### MMN — PIEMIN (citā tēmā)

- claim_id 532769 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Ieviest pārnesamās balss vēlēšanu sistēmu (Īrijas modeli) gan Saeimas, gan pašvaldību vēlēšanās — viens biļetens ar visiem kandidātiem, sarindojamiem vēlamības secībā; atcelt 5% barjeru partiju sarakstiem; sadalīt Latviju mazākos apgabalos ar 5–7 deputātiem; atcelt ierobežojumus deputāta amata savienošanai ar profesiju; ļaut ārzemju latviešiem balsot par jebkuru apgabalu; pazemināt referenduma ierosināšanas slieksni līdz 25 000 parakstu.
  
  **Citāts:** „ieviesīsim pārnesamās balss vēlēšanu sistēmu jeb Īrijas modeli”
- claim_id 532788 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Radikāli mazināt birokrātiju zemniekiem un panākt tiešmaksājumu izlīdzināšanu līdz 100% no ES vidējā; valsts un pašvaldību iepirkumos noteikt, ka vismaz 95% pārtikas jābūt Latvijas izcelsmes, pat ja tas ir pretrunā ES regulējumam.
  
  **Citāts:** „valsts un pašvaldību iepirkumos vismaz 95% pārtikas jābūt Latvijas izcelsmes”

### LA — PIEMIN

- claim_id 547868 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola saglabāt aizsardzības finansējumu vismaz 5% apmērā no iekšzemes kopprodukta, mērķtiecīgi attīstot Latvijas aizsardzības industriju un valsts spēju ražot drošībai nepieciešamās tehnoloģijas. Sola attīstīt Nacionālos bruņotos spēkus, Zemessardzi, civilo aizsardzību un kiberdrošību, stiprināt kritiskās infrastruktūras un robežas aizsardzību un veidot modernu krīžu vadības sistēmu. Sola stiprināt sabiedrības noturību, attīstot medijpratību un cīņu pret dezinformāciju, kā arī atbalstīt vietējo uzņēmumu iesaisti militāro tehnoloģiju, dronu un kiberdrošības risinājumu izstrādē un ražošanā. Uzsver, ka Latvijas drošība balstās spēcīgā NATO, vienotā Eiropas Savienībā un ciešā sadarbībā ar Baltijas un Ziemeļvalstīm.

### ST — PIEMIN

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.

### JKP — TĒMA

- claim_id 532794 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot pašpietiekamu un modernu valsts aizsardzības sistēmu, stiprināt Nacionālo bruņoto spēku kaujas spējas (pretgaisa aizsardzība, artilērija, kaujas droni, munīcijas rezerves, izlūkošana, loģistika), pilnveidot Valsts aizsardzības dienestu un Zemessardzi, kā arī padziļināt sadarbību ar NATO, Ziemeļvalstīm, Kanādu un ASV lielākai sabiedroto klātbūtnei. Paredz attīstīt Latvijas militāro industriju un maksimāli izmantot ES un NATO finansējumu. Iekšējās drošības jomā sola stiprināt Valsts robežsardzi, reformēt civilās aizsardzības sistēmu (vienota pārvalde, patvertņu reģistrs), nodrošināt policijas pastāvīgu klātbūtni reģionos un veidot kopienu drošības brīvprātīgo vienības.
  
  **Citāts:** „Veidosim PAŠPIETIEKAMU UN MODERNU VALSTS AIZSARDZĪBAS SISTĒMU”
- claim_id 532798 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stabilu un konkurētspējīgu nodokļu politiku bez haotiskām izmaiņām: atcelt kapitāla pieauguma nodokli mantotam īpašumam un privātpersonu nekustamā īpašuma atsavināšanai, kā arī atcelt nekustamā īpašuma nodokli mājokļiem. Ekonomikā sola veicināt investīcijas un eksportspēju augstas pievienotās vērtības nozarēs, atbalstīt mazo uzņēmējdarbību, mazināt administratīvo slogu un nodrošināt pieejamāku kreditēšanu reģionos. Iestājas pret legālas skaidras naudas aprites ierobežošanu.
  
  **Citāts:** „Veidosim STABILU UN KONKURĒTSPĒJĪGU NODOKĻU POLITIKU”

### ASL — TĒMA

- claim_id 532600 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts astoņos gados dubultot Latvijas ekonomiku, palielināt IIN neapliekamo minimumu vidējās algas apmērā (norādīts 1900 eiro mēnesī), samazināt sociālo iemaksu darba ņēmēja daļu par 6 %, atcelt nekustamā īpašuma nodokli vienīgajam ģimenes mājoklim un radīt modernu ekosistēmu zinātnes komercializācijai un efektīviem iepirkumiem.
  
  **Citāts:** „Dubultosim Latvijas ekonomiku 8 gados”
- claim_id 532606 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts celt Nacionālo bruņoto spēku spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu, stiprināt drošības iestādes un civilo aizsardzību (medicīnu, VUGD, patvertnes), mazināt kaujas spējas vājinošu birokrātiju, palielināt policijas atalgojumu par 30–50 % piecu gadu laikā, aizliegt valsts amatpersonas amatu agresorvalstu finansētiem indivīdiem, ieviest tiešo valsts pārvaldi prokremliski vadītās pašvaldībās un pilnībā pārtraukt sadarbību un tirdzniecību ar Krieviju un Baltkrieviju, nojaucot dzelzceļa sliedes pie austrumu robežas.
  
  **Citāts:** „Celsim Nacionālo bruņoto spēku (NBS) spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu”

### SC — PIEMIN (citā tēmā)

- claim_id 532686 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt invaliditātes pabalstus par 25 % un bērna piedzimšanas pabalstu līdz 1000 eiro, par otro bērnu palielināt valsts pabalstu piecreiz, nodrošināt bezmaksas ēdināšanu visiem skolēniem līdz 9. klasei un paplašināt bērnudārzu pieejamību bērniem līdz 3 gadu vecumam. Darba tiesību jomā solīts aizstāvēt 100 % piemaksu par virsstundām, stiprināt arodbiedrību tiesības, koplīgumu un ģenerālvienošanās sistēmu, ieviest algu caurskatāmības prasības lielajos uzņēmumos un stiprināt Valsts darba inspekciju. Mājokļu jomā solīts izveidot valsts sociālo un pieejamo īres mājokļu fondu un paplašināt daudzdzīvokļu māju renovācijas programmas.
- claim_id 532687 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts stiprināt publisko veselības aprūpi: samazināt PVN būtiskākajām zālēm līdz 5 % un ieviest stingrāku zāļu cenu kontroli, izveidot valsts centralizētu zāļu iepirkumu un valsts aptieku tīkla pilotprojektu, ieviest centralizētu rindu pārvaldības sistēmu, stiprināt reģionālās slimnīcas, ieviest četru gadu atalgojuma grafiku mediķiem, māsām un NMPD darbiniekiem, pakāpeniski paplašināt valsts apmaksātu zobārstniecību un ikgadējas bezmaksas profilakses pārbaudes. Jaunu mediķu sagatavošanu valsts apmaksātu ar pienākumu noteiktu laiku strādāt Latvijas publiskajā veselības aprūpē. Solīts arī 10 % cukura nodoklis saldinātiem dzērieniem.

### GS — PIEMIN

- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547973 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Nodokļu politikā solīts vismaz 5 gadu moratorijs nodokļu paaugstināšanai un jaunu nodokļu ieviešanai, nekustamā īpašuma nodokļa atcelšana visiem mājokļiem, PVN samazināšana pārtikai un sabiedriskajai ēdināšanai līdz 5 %, iedzīvotāju ienākuma nodokļa atcelšana jauniešiem līdz 25 gadu vecumam un uzņēmējiem labvēlīgāka nodokļu sistēma; solīts atgriezt Latvijas zelta krājumus glabāšanā Latvijas Bankā.
  
  **Citāts:** „ieviest vismaz 5 gadu moratoriju nodokļu paaugstināšanai un jaunu nodokļu ieviešanai”
- claim_id 547988 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts nepieļaut Latvijas iesaistīšanos militārajos konfliktos, tostarp to finansēšanā, atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā un pārdalīt aizsardzības budžetu iekšējās drošības un infrastruktūras vajadzībām, papildus finansējot medicīnu un glābšanas dienestus.
  
  **Citāts:** „atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā”

_Piemin: 11 no 14._


## k02 — Latvijai jāturpina atbalstīt Ukrainu, kamēr karš nav beidzies.

Tēmas: Ukraina un Krievija, Ārpolitika  
Kodēšanas atgādne: par = atbalsts Ukrainai; pret = neitralitāte / neiesaistīties


### JV — PIEMIN

- claim_id 532668 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts turpināt visaptverošu politisku, militāru un diplomātisku atbalstu Ukrainai līdz taisnīgam mieram un tās eiroatlantiskajai integrācijai, uzturēt starptautisko spiedienu pret Krieviju, stiprināt sankcijas un pārtraukt ekonomisko ietekmējamību no Krievijas un Baltkrievijas.

### PRO — PIEMIN

- claim_id 532637 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts aizstāvēt starptautiskās normās balstītu pasaules kārtību, būt aktīvai NATO austrumu flanga valstij, kas sadarbojas ar NATO, ES, NB8+, Poliju, Lielbritāniju un Ukrainu, un iesaistīt diasporu lēmumu pieņemšanā, atbalstot ikvienu, kurš vēlas atgriezties Latvijā.

### ZZS — PIEMIN

- claim_id 547897 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nelokāmi atbalstīt Ukrainu un iesaistīt Latvijas uzņēmējus tās atjaunošanā.

### NA — PIEMIN

- claim_id 532708 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts atbalstīt Ukrainu militāri, politiski un ekonomiski līdz uzvarai un iestāties par tās uzņemšanu ES un NATO, kā arī pārraut ekonomiskās saites ar Krieviju un Baltkrieviju.

### LPV — PIEMIN

- claim_id 532657 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts atbalstīt Ukrainas iestāšanos Eiropas Savienībā.
  
  **Citāts:** „Atbalstīsim Ukrainas iestāšanos ES.”

### AS — PIEMIN

- claim_id 532842 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Turpinās nelokāmu atbalstu Ukrainai, vienlaikus stiprinot Latvijas aizsardzības industriju, militāro mobilitāti un noturību pret Krievijas agresiju un hibrīduzbrukumiem.
  
  **Citāts:** „Turpināsim nelokāmu atbalstu Ukrainai, vienlaikus stiprinot Latvijas aizsardzības industriju, militāro mobilitāti un noturību pret Krievijas agresiju un hibrīduzbrukumiem.”

### MMN — PIEMIN

- claim_id 532792 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Īpaši stiprināt divpusējās attiecības ar tuvākajiem sabiedrotajiem: ASV, Baltijas valstīm, Somiju, Poliju, Ukrainu un Lielbritāniju.
  
  **Citāts:** „īpaši stiprināsim divpusējas attiecības ar tuvākajiem sabiedrotajiem”

### LA — PIEMIN

- claim_id 547869 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola turpināt visaptverošu politisko, militāro un humāno atbalstu Ukrainai līdz taisnīga un ilgtspējīga miera panākšanai, uzsverot, ka Ukrainas uzvara ir Latvijas un visas Eiropas drošības interesēs.

### ST — PIEMIN

- claim_id 532587 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīta valsts neitralitātes atjaunošana un atteikšanās no dalības citu valstu militāros konfliktos, koncentrējoties uz Latvijas drošības un interešu aizsardzību, kā arī atteikšanās finansēt ārvalstis par Latvijas nodokļu maksātāju līdzekļiem.

### JKP — PIEMIN

- claim_id 532795 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot militāri tehnoloģisku aliansi ar Ukrainu, pārņemot kara pieredzi un attīstot kopīgus aizsardzības industrijas projektus.
  
  **Citāts:** „Veidosim MILITĀRI TEHNOLOĢISKU ALIANSI AR UKRAINU”

### ASL — PIEMIN

- claim_id 532611 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts sekmēt ciešāku sadarbību starp Skandināvijas, Baltijas valstīm, Poliju un Ukrainu, atbalstīt Ukrainas ceļu uz NATO un stiprināt divpusējo sadarbību ar ASV, īpaši NATO ietvaros.
  
  **Citāts:** „Sekmēsim ciešāku sadarbību starp Skandināvijas, Baltijas valstīm, Poliju un Ukrainu. Atbalstīsim Ukrainas ceļu uz NATO”

### SC — PIEMIN

- claim_id 532693 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts nosodīt Krievijas agresiju pret Ukrainu un atbalstīt proaktīvu diplomātiju taisnīgam mieram, saglabājot Ukrainas suverenitāti, teritoriālo integritāti un drošības garantijas.

### GS — PIEMIN

- claim_id 532766 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Apņemas Krievijas un Ukrainas konfliktā neieņemt aktīvu, priekšplānā ejošu pozīciju, kas, pēc partijas ieskata, nepamatoti palielina riskus Latvijas drošībai; fokusējas uz pragmatisku reālpolitiku, diplomātiju un mieru.
  
  **Citāts:** „Latvija neieņems aktīvu, priekšplānā ejošu pozīciju, kas nepamatoti palielina riskus mūsu pašu drošībai”

### SV-AJ — TĒMA

- claim_id 547989 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Ārpolitikā solīts izskaust “pakļāvīgu ārpolitiku”, aktīvi aizstāvēt Latvijas iedzīvotāju un ražotāju intereses, uzticēt Ārlietu ministrijai veicināt eksportu un izvērtēt iespēju Latvijai izstāties no Pasaules Veselības organizācijas.
  
  **Citāts:** „izvērtēt iespēju Latvijai izstāties no Pasaules Veselības organizācijas”

_Piemin: 13 no 14._


## k03 — Ekonomiskie sakari ar Krieviju un Baltkrieviju jāatjauno, tiklīdz tas ir iespējams.

Tēmas: Ukraina un Krievija, Ārpolitika, Aizsardzība un drošība  
Kodēšanas atgādne: par = atjaunot sadarbību / pārskatīt sankcijas; pret = pārtraukt / saglabāt sankcijas


### JV — PIEMIN

- claim_id 532668 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts turpināt visaptverošu politisku, militāru un diplomātisku atbalstu Ukrainai līdz taisnīgam mieram un tās eiroatlantiskajai integrācijai, uzturēt starptautisko spiedienu pret Krieviju, stiprināt sankcijas un pārtraukt ekonomisko ietekmējamību no Krievijas un Baltkrievijas.

### PRO — TĒMA

- claim_id 532636 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts saglabāt finansējumu aizsardzības nozarei vismaz 5% apjomā, attīstīt aizsardzības industriju un industrijas parkus atbilstoši NBS vajadzībām, nodrošināt tehnoloģiski un fiziski drošu valsts robežu, saglabājot cilvēktiesībās balstītu pieeju, un turpināt patvertņu izbūvi un iedzīvotāju sagatavošanu krīzes apstākļiem.
- claim_id 532637 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts aizstāvēt starptautiskās normās balstītu pasaules kārtību, būt aktīvai NATO austrumu flanga valstij, kas sadarbojas ar NATO, ES, NB8+, Poliju, Lielbritāniju un Ukrainu, un iesaistīt diasporu lēmumu pieņemšanā, atbalstot ikvienu, kurš vēlas atgriezties Latvijā.

### ZZS — TĒMA

- claim_id 547882 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi aizsardzībai novirzīt virs 5% no IKP. Sola stabilu aizsardzības un drošības finansējuma pieaugumu ar stiprinātu parlamentāro kontroli, stiprināt NBS, Zemessardzes un iekšlietu sistēmas spējas, pastiprināt austrumu robežas un jūras drošību, militāro infrastruktūru un sabiedroto klātbūtni, modernizēt civilo aizsardzību (patvertnes, brīdināšanas sistēmas, ģeneratoru punkti visās pilsētās un ciemos), nodrošināt materiālās rezerves un krīzes krājumus, modernizēt pierobežas drošības infrastruktūru, kā arī attīstīt aizsardzības industriju (munīcija, droni, enerģētika), lai drošības finansējums paliktu Latvijas ekonomikā.
- claim_id 547897 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nelokāmi atbalstīt Ukrainu un iesaistīt Latvijas uzņēmējus tās atjaunošanā.
- claim_id 547899 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola īstenot aktīvu, uzticamu un pārliecinātu ārpolitiku ar stipru ārlietu dienestu, attīstīt Ziemeļvalstu un Baltijas valstu kopīgus aizsardzības iepirkumus un parlamentāro sadarbību, meklēt risinājumus drošībai Baltijas jūrā un aizstāvēt ekonomiskās intereses, atbalstīt diasporu kā Latvijas balsi un kultūras nesēju bez liekas birokrātijas un radīt priekšnosacījumus atgriezties Latvijā, kā arī aktīvi iesaistīties starptautisko organizāciju darbībā valsts tautsaimniecības attīstībai.

### NA — PIEMIN

- claim_id 532708 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts atbalstīt Ukrainu militāri, politiski un ekonomiski līdz uzvarai un iestāties par tās uzņemšanu ES un NATO, kā arī pārraut ekonomiskās saites ar Krieviju un Baltkrieviju.

### LPV — TĒMA

- claim_id 532653 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts apvienot Iekšlietu un Aizsardzības ministrijas ar vienotu atalgojuma sistēmu militārpersonām, policistiem, ugunsdzēsējiem un glābējiem, uzskatot, ka ārējā un iekšējā drošība nav dalāmas, un pusi no visiem militārajiem iepirkumiem veikt no ASV kā Latvijas stratēģiskā partnera.
  
  **Citāts:** „Apvienosim Iekšlietu un Aizsardzības ministrijas, lai garantētu valsts drošību un ieviestu vienotu atalgojuma sistēmu militārpersonām, policistiem, ugunsdzēsējiem un glābējiem.”
- claim_id 532657 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts atbalstīt Ukrainas iestāšanos Eiropas Savienībā.
  
  **Citāts:** „Atbalstīsim Ukrainas iestāšanos ES.”
- claim_id 532658 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts nostiprināt Latvijas suverenitāti, nodrošinot, ka valsts pati nosaka savu nākotni, un veidot visciešāko aliansi ar ASV militārajā, ekonomikas un starptautisko attiecību jomā, kopā ar ES un NATO partnervalstīm rūpējoties par mieru un stabilitāti Eiropā.
  
  **Citāts:** „Veidosim visciešāko aliansi ar ASV – militārajā, ekonomikas un starptautisko attiecību jomā.”

### AS — PIEMIN

- claim_id 532842 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Turpinās nelokāmu atbalstu Ukrainai, vienlaikus stiprinot Latvijas aizsardzības industriju, militāro mobilitāti un noturību pret Krievijas agresiju un hibrīduzbrukumiem.
  
  **Citāts:** „Turpināsim nelokāmu atbalstu Ukrainai, vienlaikus stiprinot Latvijas aizsardzības industriju, militāro mobilitāti un noturību pret Krievijas agresiju un hibrīduzbrukumiem.”

### MMN — TĒMA

- claim_id 532790 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Paātrināti izbūvēt slāņveida pretgaisa un pretraķešu aizsardzības sistēmas; veidot brīvprātīgo vienības un decentralizētas rezerves novados.
  
  **Citāts:** „paātrināti izbūvēsim slāņveida pretgaisa un pretraķešu aizsardzības sistēmas”
- claim_id 532792 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Īpaši stiprināt divpusējās attiecības ar tuvākajiem sabiedrotajiem: ASV, Baltijas valstīm, Somiju, Poliju, Ukrainu un Lielbritāniju.
  
  **Citāts:** „īpaši stiprināsim divpusējas attiecības ar tuvākajiem sabiedrotajiem”

### LA — TĒMA

- claim_id 547868 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola saglabāt aizsardzības finansējumu vismaz 5% apmērā no iekšzemes kopprodukta, mērķtiecīgi attīstot Latvijas aizsardzības industriju un valsts spēju ražot drošībai nepieciešamās tehnoloģijas. Sola attīstīt Nacionālos bruņotos spēkus, Zemessardzi, civilo aizsardzību un kiberdrošību, stiprināt kritiskās infrastruktūras un robežas aizsardzību un veidot modernu krīžu vadības sistēmu. Sola stiprināt sabiedrības noturību, attīstot medijpratību un cīņu pret dezinformāciju, kā arī atbalstīt vietējo uzņēmumu iesaisti militāro tehnoloģiju, dronu un kiberdrošības risinājumu izstrādē un ražošanā. Uzsver, ka Latvijas drošība balstās spēcīgā NATO, vienotā Eiropas Savienībā un ciešā sadarbībā ar Baltijas un Ziemeļvalstīm.
- claim_id 547869 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola turpināt visaptverošu politisko, militāro un humāno atbalstu Ukrainai līdz taisnīga un ilgtspējīga miera panākšanai, uzsverot, ka Ukrainas uzvara ir Latvijas un visas Eiropas drošības interesēs.

### ST — PIEMIN

- claim_id 532586 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts atjaunot ekonomisko sadarbību ar Krieviju un Baltkrieviju visās nozarēs, kur tas atbilst Latvijas interesēm (tranzīts, rūpniecība, lauksaimniecības eksports), kā arī pārskatīt Latvijas dalību ekonomiskajās sankcijās un atteikties no sankcijām, kas, programmas ieskatā, grauj Latvijas ekonomiku.

### JKP — TĒMA

- claim_id 532794 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot pašpietiekamu un modernu valsts aizsardzības sistēmu, stiprināt Nacionālo bruņoto spēku kaujas spējas (pretgaisa aizsardzība, artilērija, kaujas droni, munīcijas rezerves, izlūkošana, loģistika), pilnveidot Valsts aizsardzības dienestu un Zemessardzi, kā arī padziļināt sadarbību ar NATO, Ziemeļvalstīm, Kanādu un ASV lielākai sabiedroto klātbūtnei. Paredz attīstīt Latvijas militāro industriju un maksimāli izmantot ES un NATO finansējumu. Iekšējās drošības jomā sola stiprināt Valsts robežsardzi, reformēt civilās aizsardzības sistēmu (vienota pārvalde, patvertņu reģistrs), nodrošināt policijas pastāvīgu klātbūtni reģionos un veidot kopienu drošības brīvprātīgo vienības.
  
  **Citāts:** „Veidosim PAŠPIETIEKAMU UN MODERNU VALSTS AIZSARDZĪBAS SISTĒMU”
- claim_id 532795 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot militāri tehnoloģisku aliansi ar Ukrainu, pārņemot kara pieredzi un attīstot kopīgus aizsardzības industrijas projektus.
  
  **Citāts:** „Veidosim MILITĀRI TEHNOLOĢISKU ALIANSI AR UKRAINU”

### ASL — PIEMIN

- claim_id 532606 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts celt Nacionālo bruņoto spēku spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu, stiprināt drošības iestādes un civilo aizsardzību (medicīnu, VUGD, patvertnes), mazināt kaujas spējas vājinošu birokrātiju, palielināt policijas atalgojumu par 30–50 % piecu gadu laikā, aizliegt valsts amatpersonas amatu agresorvalstu finansētiem indivīdiem, ieviest tiešo valsts pārvaldi prokremliski vadītās pašvaldībās un pilnībā pārtraukt sadarbību un tirdzniecību ar Krieviju un Baltkrieviju, nojaucot dzelzceļa sliedes pie austrumu robežas.
  
  **Citāts:** „Celsim Nacionālo bruņoto spēku (NBS) spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu”

### SC — PIEMIN

- claim_id 532693 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts nosodīt Krievijas agresiju pret Ukrainu un atbalstīt proaktīvu diplomātiju taisnīgam mieram, saglabājot Ukrainas suverenitāti, teritoriālo integritāti un drošības garantijas.

### GS — PIEMIN

- claim_id 532766 · Ukraina un Krievija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Apņemas Krievijas un Ukrainas konfliktā neieņemt aktīvu, priekšplānā ejošu pozīciju, kas, pēc partijas ieskata, nepamatoti palielina riskus Latvijas drošībai; fokusējas uz pragmatisku reālpolitiku, diplomātiju un mieru.
  
  **Citāts:** „Latvija neieņems aktīvu, priekšplānā ejošu pozīciju, kas nepamatoti palielina riskus mūsu pašu drošībai”

### SV-AJ — TĒMA

- claim_id 547988 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts nepieļaut Latvijas iesaistīšanos militārajos konfliktos, tostarp to finansēšanā, atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā un pārdalīt aizsardzības budžetu iekšējās drošības un infrastruktūras vajadzībām, papildus finansējot medicīnu un glābšanas dienestus.
  
  **Citāts:** „atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā”
- claim_id 547989 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Ārpolitikā solīts izskaust “pakļāvīgu ārpolitiku”, aktīvi aizstāvēt Latvijas iedzīvotāju un ražotāju intereses, uzticēt Ārlietu ministrijai veicināt eksportu un izvērtēt iespēju Latvijai izstāties no Pasaules Veselības organizācijas.
  
  **Citāts:** „izvērtēt iespēju Latvijai izstāties no Pasaules Veselības organizācijas”

_Piemin: 7 no 14._


## k04 — Obligātais valsts aizsardzības dienests jāsaglabā.

Tēmas: Aizsardzība un drošība  
Kodēšanas atgādne: par = saglabāt / paplašināt VAD; pret = atcelt obligāto iesaukšanu


### JV — PIEMIN

- claim_id 532665 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts nodrošināt aizsardzības finansējumu 5% apmērā no IKP un attīstīt NATO sabiedroto pastāvīgu klātbūtni Latvijā. Paredzēts stiprināt pretgaisa, dronu un pretdronu un citas mūsdienīgas aizsardzības spējas, izmantojot Ukrainas pieredzi, attīstīt vietējo militāro un divējāda lietojuma industriju, stiprināt Nacionālos bruņotos spēkus un Zemessardzi, palielināt apmaksāto brīvdienu skaitu zemessargiem, kā arī stiprināt civilās aizsardzības sistēmu un iekšlietu dienestus – ugunsdzēsēju, policijas un robežsardzes kapacitāti.

### PRO — TĒMA

- claim_id 532636 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts saglabāt finansējumu aizsardzības nozarei vismaz 5% apjomā, attīstīt aizsardzības industriju un industrijas parkus atbilstoši NBS vajadzībām, nodrošināt tehnoloģiski un fiziski drošu valsts robežu, saglabājot cilvēktiesībās balstītu pieeju, un turpināt patvertņu izbūvi un iedzīvotāju sagatavošanu krīzes apstākļiem.

### ZZS — PIEMIN

- claim_id 547882 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi aizsardzībai novirzīt virs 5% no IKP. Sola stabilu aizsardzības un drošības finansējuma pieaugumu ar stiprinātu parlamentāro kontroli, stiprināt NBS, Zemessardzes un iekšlietu sistēmas spējas, pastiprināt austrumu robežas un jūras drošību, militāro infrastruktūru un sabiedroto klātbūtni, modernizēt civilo aizsardzību (patvertnes, brīdināšanas sistēmas, ģeneratoru punkti visās pilsētās un ciemos), nodrošināt materiālās rezerves un krīzes krājumus, modernizēt pierobežas drošības infrastruktūru, kā arī attīstīt aizsardzības industriju (munīcija, droni, enerģētika), lai drošības finansējums paliktu Latvijas ekonomikā.

### NA — PIEMIN

- claim_id 532704 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts palielināt aizsardzības finansējumu virs 5% no IKP, attīstot vietējo militāro industriju, turpināt NBS attīstību pretgaisa aizsardzības (t.sk. dronu un pretdronu spēju), sauszemes un krasta apsardzības jomā, paplašināt rezervistu skaitu un atbalstu NBS, ZS un VAD dienošajiem, celt iekšlietu dienestu kapacitāti un atalgojumu, nodrošināt kritiskās infrastruktūras aizsardzību un valsts vadošo lomu civilās aizsardzības un patvertņu izveidē, kā arī pilnveidot valsts stratēģiskās rezerves.

### LPV — TĒMA

- claim_id 532653 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts apvienot Iekšlietu un Aizsardzības ministrijas ar vienotu atalgojuma sistēmu militārpersonām, policistiem, ugunsdzēsējiem un glābējiem, uzskatot, ka ārējā un iekšējā drošība nav dalāmas, un pusi no visiem militārajiem iepirkumiem veikt no ASV kā Latvijas stratēģiskā partnera.
  
  **Citāts:** „Apvienosim Iekšlietu un Aizsardzības ministrijas, lai garantētu valsts drošību un ieviestu vienotu atalgojuma sistēmu militārpersonām, policistiem, ugunsdzēsējiem un glābējiem.”

### AS — PIEMIN

- claim_id 532820 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Paplašinās Valsts aizsardzības dienestu ar papildu dienesta virzieniem, stiprinās Zemessardzes kaujas spējas un rezerves karavīru apmācību, pabeigs austrumu robežas aizsardzības līniju un novērošanas infrastruktūru. Civilajā aizsardzībā ieviesīs reālistiskus reģionālus krīžu plānus, izveidos patvertņu tīklu, veiks valsts rezervju auditu un slēgs priekšlīgumus ar uzņēmumiem ātrai reaģēšanai. Stiprinās policiju, robežsardzi un VUGD ar apdraudējumiem atbilstošu materiāltehnisko nodrošinājumu.
  
  **Citāts:** „Paplašināsim Valsts aizsardzības dienestu, piedāvājot papildu dienesta virzienus, kas nepieciešami visaptverošai valsts aizsardzībai.”

### MMN — PIEMIN (citā tēmā)

- claim_id 532789 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Totāli ierobežot trešo valstu imigrāciju, izsniedzot termiņuzturēšanās atļaujas tikai Latvijā nepieejamiem kvalificētiem speciālistiem; pastiprināt armijas un Zemessardzes lomu robežapsardzībā.
  
  **Citāts:** „totāla trešo valstu imigrācijas ierobežošana”

### LA — PIEMIN

- claim_id 547868 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola saglabāt aizsardzības finansējumu vismaz 5% apmērā no iekšzemes kopprodukta, mērķtiecīgi attīstot Latvijas aizsardzības industriju un valsts spēju ražot drošībai nepieciešamās tehnoloģijas. Sola attīstīt Nacionālos bruņotos spēkus, Zemessardzi, civilo aizsardzību un kiberdrošību, stiprināt kritiskās infrastruktūras un robežas aizsardzību un veidot modernu krīžu vadības sistēmu. Sola stiprināt sabiedrības noturību, attīstot medijpratību un cīņu pret dezinformāciju, kā arī atbalstīt vietējo uzņēmumu iesaisti militāro tehnoloģiju, dronu un kiberdrošības risinājumu izstrādē un ražošanā. Uzsver, ka Latvijas drošība balstās spēcīgā NATO, vienotā Eiropas Savienībā un ciešā sadarbībā ar Baltijas un Ziemeļvalstīm.

### ST — PIEMIN

- claim_id 532588 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts atteikties no obligātā valsts aizsardzības dienesta.

### JKP — PIEMIN

- claim_id 532794 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot pašpietiekamu un modernu valsts aizsardzības sistēmu, stiprināt Nacionālo bruņoto spēku kaujas spējas (pretgaisa aizsardzība, artilērija, kaujas droni, munīcijas rezerves, izlūkošana, loģistika), pilnveidot Valsts aizsardzības dienestu un Zemessardzi, kā arī padziļināt sadarbību ar NATO, Ziemeļvalstīm, Kanādu un ASV lielākai sabiedroto klātbūtnei. Paredz attīstīt Latvijas militāro industriju un maksimāli izmantot ES un NATO finansējumu. Iekšējās drošības jomā sola stiprināt Valsts robežsardzi, reformēt civilās aizsardzības sistēmu (vienota pārvalde, patvertņu reģistrs), nodrošināt policijas pastāvīgu klātbūtni reģionos un veidot kopienu drošības brīvprātīgo vienības.
  
  **Citāts:** „Veidosim PAŠPIETIEKAMU UN MODERNU VALSTS AIZSARDZĪBAS SISTĒMU”

### ASL — TĒMA

- claim_id 532606 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts celt Nacionālo bruņoto spēku spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu, stiprināt drošības iestādes un civilo aizsardzību (medicīnu, VUGD, patvertnes), mazināt kaujas spējas vājinošu birokrātiju, palielināt policijas atalgojumu par 30–50 % piecu gadu laikā, aizliegt valsts amatpersonas amatu agresorvalstu finansētiem indivīdiem, ieviest tiešo valsts pārvaldi prokremliski vadītās pašvaldībās un pilnībā pārtraukt sadarbību un tirdzniecību ar Krieviju un Baltkrieviju, nojaucot dzelzceļa sliedes pie austrumu robežas.
  
  **Citāts:** „Celsim Nacionālo bruņoto spēku (NBS) spējas, nodrošinot gatavību 30 dienas patstāvīgi aizsargāt austrumu robežu”

### SC — PIEMIN

- claim_id 532692 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts prioritāri finansēt policijas, VUGD un robežsardzes atalgojumu un aprīkojumu, palielināt atlīdzību Valsts aizsardzības dienesta dalībniekiem (iesauktajiem 500 eiro, brīvprātīgajiem 800 eiro) un daļai ļaut dienēt pašvaldības policijā vai civilās aizsardzības struktūrās, uzsākt kritiskās infrastruktūras programmu 'Baltijas kibercietoksnis' un ieviest obligātu pirmās palīdzības apmācību. Latvijas aizsardzību solīts stiprināt NATO ietvarā un Eiropas kopīgos iepirkumos munīcijā, dronos, pretgaisa aizsardzībā un kiberdrošībā.

### GS — TĒMA

- claim_id 532818 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola stiprināt iekšējo drošību: dubultotu algas policistiem, ugunsdzēsējiem un robežsargiem; izveidotu Drošības akadēmiju augstākā līmeņa iekšlietu speciālistu sagatavošanai un modernāko ekspertīžu centru Eiropā noziegumu izmeklēšanai. Mērķtiecīgi atbalstītu militāro prasmju apguvi sabiedrībā, lai ikviens pilsonis zinātu savu lomu krīzes situācijā.
  
  **Citāts:** „dubultosim algas policistiem, ugunsdzēsējiem un robežsargiem”

### SV-AJ — PIEMIN

- claim_id 547988 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts nepieļaut Latvijas iesaistīšanos militārajos konfliktos, tostarp to finansēšanā, atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā un pārdalīt aizsardzības budžetu iekšējās drošības un infrastruktūras vajadzībām, papildus finansējot medicīnu un glābšanas dienestus.
  
  **Citāts:** „atcelt jauniešu obligāto iesaukšanu Valsts aizsardzības dienestā”

_Piemin: 10 no 14._


## k05 — Cilvēkiem ar lielākiem ienākumiem nodokļos jāatdod lielāka ienākumu daļa nekā cilvēkiem ar mazākiem.

Tēmas: Budžets un finanses, Sociālā politika  
Kodēšanas atgādne: par = progresīvie nodokļi / kapitāla nodokļi; pret = vienāda likme / mazināt IIN visiem


### JV — PIEMIN

- claim_id 532670 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot fiskāli atbildīgu budžetu ar valsts ārējā parāda līmeni zem 55% no IKP, ievērojot eirozonas fiskālos noteikumus. Paredzēts celt minimālo algu līdz 50% no vidējās bruto darba samaksas, palielināt fiksēto neapliekamo minimumu līdz 80% no minimālās algas, padarīt nekustamā īpašuma nodokli par pilnvērtīgu pašvaldību nodokli, attīstīt kapitāla tirgu un valsts attīstības fondu. Ekonomikā izvirzīts mērķis panākt vismaz 3,5% IKP izaugsmi gadā un investīcijas virs 30% no IKP, pārejot uz augstas pievienotās vērtības ekonomiku.

### PRO — PIEMIN

- claim_id 532620 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts ieviest plašāku nodokļu progresivitāti, samazinot nodokļus mazajām un vidējām algām un palielinot neapliekamo minimumu, minimālo algu piesaistīt vidējai algai, pāriet no minimālās sociālo iemaksu bāzes uz proporcionālām iemaksām, vienkāršot nodokļu nomaksu maziem un vidējiem uzņēmumiem, kā arī veidot mērķtiecīgas valsts atbalsta programmas augstas pievienotās vērtības un eksporta uzņēmumiem un jaunuzņēmumu atbalsta programmu tehnoloģiju komandām.

### ZZS — TĒMA

- claim_id 547879 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi līdz 2030. gadam panākt IKP izaugsmi vismaz par 2% virs ES vidējā, ikgadējās ārvalstu investīcijas vismaz 1 mljrd. € apmērā un IKP pieaugumu +3,8 mljrd. € gadā, minimālo algu 1250 € un vidējo algu 2500 €. Sola vienkāršāku nodokļu sistēmu mazajam biznesam, nodokļu atlaides ieguldījumiem ražīguma, efektivitātes un digitalizācijas celšanai, Latvijas kreditēšanas un investīciju fonda un krājaizdevu sabiedrību attīstību, eksporta veicināšanu un klasterus, kā arī darba ražīguma pieaugumu vismaz 5% gadā. Dzīves dārdzības mazināšanai sola samazinātu PVN (5% pirmās nepieciešamības pārtikai, 12% sabiedriskajai ēdināšanai un izmitināšanas pakalpojumiem), 0% nekustamā īpašuma nodokli primārajam mājoklim, attaisnoto izdevumu slieksni 1800 €, mazumtirdzniecības uzraudzības un 'pārtikas groza' iniciatīvas pilnveidi un sabiedrisko pakalpojumu cenu auditu.
- claim_id 547886 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola reformēt invaliditātes sistēmu uz funkcionēšanu balstītu novērtējumu ar lielāku atbalstu smagiem funkcionāliem traucējumiem, stiprināt Satversmē noteiktos ģimenes un sabiedrības pamatus, izveidot krīzes atbalsta mehānismu kā pastāvīgu sistēmu, nodrošināt strādājošiem vecākiem vecāku pabalstu 100% apmērā, paaugstināt atbalstu ģimenēm ar vienu apgādnieku un sociālo pakalpojumu pieejamību visā Latvijā. Demogrāfijas veicināšanai sola bērna piedzimšanas pabalstu 2000 €, paplašināt medicīniskās apaugļošanas pieejamību, īstenot reģionu mājokļu programmu jaunajām un daudzbērnu ģimenēm, atbalstīt hipotekāro maksājumu sloga mazināšanu, kā arī atbalstīt jauniešu pirmo darba vietu un mājokli.

### NA — TĒMA

- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.
- claim_id 532719 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts palielināt bērna kopšanas pabalstu līdz 600 EUR ar ikgadēju indeksāciju, celt ģimenes valsts pabalstu (100 EUR par vienu, 300 EUR par diviem, 600 EUR par trim un vairāk bērniem), nodrošināt ģimenes ienākumu saglabāšanu bērna pirmajos 18 mēnešos, ieviest programmu "Silta maltīte katram bērnam", dzēst studiju kredītus par bērniem, atvieglot pirmā mājokļa iegādi (15 000 EUR valsts grants par katru bērnu, valsts garantēts kredīts bez pirmās iemaksas jaunajām ģimenēm), atbalstīt tēvu iesaisti bērnu audzināšanā, personu ar invaliditāti nodarbinātību un vides pieejamību, kā arī veidot remigrācijas un diasporas atgriešanās atbalsta sistēmu.

### LPV — PIEMIN

- claim_id 532642 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts noteikt 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli un 10% kapitāla pieauguma nodokli, samazināt PVN līdz 10% apkurei, plašākam pārtikas klāstam, bērnu precēm, tūrismam un ēdināšanai, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim, atbrīvot māti no IIN, ja ģimenē aug vismaz divi bērni, palielināt neapliekamo minimumu līdz minimālās algas apmēram, atcelt nodokļus jauniešu algām pirmajā darba gadā un samazināt darbaspēka nodokļus līdz Eiropas vidējam līmenim; izveidot Nacionālo attīstības banku uz ALTUM bāzes un veidot Latviju par fintech, IT un mākslīgā intelekta centru.
  
  **Citāts:** „Samazināsim nodokļus, nosakot: 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli (UIN), 10% kapitāla pieauguma nodokli.”

### AS — PIEMIN

- claim_id 532822 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Sasniegs bezdeficīta bāzes budžetu četru gadu laikā. Stabilizēs nodokļu politiku, pārtraucot tās regulāru pārskatīšanu; ieviesīs mikrouzņēmumu nodokļa 10% likmi fiziskajām personām, samazinās kapitāla pieauguma IIN līdz 17% un saglabās UIN režīmu (peļņu apliekot tikai tad, kad to sadala dividendēs). Samazinās nodokļu maksātāju administratīvo slogu un mazinās ēnu ekonomiku ar motivāciju strādāt legāli, ne sodīšanu. Izveidos valsts garantiju programmu mājokļu būvniecībai reģionos, palielinot kreditēšanu par 2 miljardiem, koncentrēs valsts atbalstu augstas pievienotās vērtības nozarēs, samazinās valsts tiešo iejaukšanos ekonomikā un sekmēs publiskās un privātās partnerības projektus.
  
  **Citāts:** „Mūsu prioritāte ir ieviest kārtību valsts finansēs, lai sasniegtu bezdeficīta bāzes budžetu četru gadu laikā.”

### MMN — PIEMIN

- claim_id 532772 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Ieviest nulles budžetu (katra pozīcija jāpamato no jauna) un sasniegt bezdeficīta budžetu viena Saeimas sasaukuma laikā; noteikt fiksētu 10% mikrouzņēmuma nodokli apgrozījumam līdz 50 000 EUR gadā; mazināt ēnu ekonomiku bez represijām, ieviešot saistību amnestiju; atcelt nekustamā īpašuma nodokli vienīgajam mājoklim; ieviest vienotu iedzīvotāju ienākuma nodokļa likmi.
  
  **Citāts:** „fiksēts 10% mikrouzņēmuma nodoklis apgrozījumam līdz 50 000 EUR gadā”
- claim_id 532776 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Atbalstīt ģimenes un demogrāfiju ar nodokļu instrumentiem: palielināt iedzīvotāju ienākuma nodokļa atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī un noteikt 0% PVN likmi pirmā mājokļa iegādei jaunos projektos.
  
  **Citāts:** „palielināsim IIN atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī”

### LA — TĒMA

- claim_id 547870 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola līdz 2030. gadam panākt sabalansētu valsts budžetu, vienlaikus saglabājot spēju ieguldīt drošībā, izglītībā, veselības aprūpē, sociālajā nodrošinājumā un zinātnē. Sola veidot stabilu, prognozējamu un uz izaugsmi orientētu uzņēmējdarbības vidi, samazināt birokrātiju, uzlabot regulējuma kvalitāti un attīstīt kapitāla tirgu. Sola atbalstīt mākslīgo intelektu, biomedicīnu, aizsardzības industriju, zaļās tehnoloģijas un zinātņietilpīgu ražošanu un panākt, ka ieguldījumi pētniecībā un attīstībā līdz 2030. gadam sasniedz vismaz 2% no iekšzemes kopprodukta. Izvirza mērķi ekonomikai augt straujāk nekā Eiropas Savienībā vidēji.
- claim_id 547873 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot ilgtermiņa ģimeņu politiku, kas uzlabo mājokļu pieejamību, nodrošina kvalitatīvu pirmsskolas un skolas izglītību un palīdz savienot darbu ar ģimenes dzīvi. Sola rūpēties par senioriem, nodrošinot labu dzīves kvalitāti vecumdienās ar prognozējamu un augošu sociālo atbalstu un veselības aprūpi.

### ST — TĒMA

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.
- claim_id 532596 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts izstrādāt visaptverošu dzimstības veicināšanas programmu (finansiāls atbalsts ģimenēm, mājokļu pieejamība, bērnu aprūpe), palielināt atbalstu jaunajām un daudzbērnu ģimenēm, izstrādāt jaunu remigrācijas programmu tautiešu atgriešanai, kā arī stiprināt sociālo aizsardzību pensionāriem, daudzbērnu ģimenēm un personām ar invaliditāti, nodrošinot cilvēka cienīgu dzīves līmeni.

### JKP — PIEMIN (citā tēmā)

- claim_id 532803 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veicināt reģionu ekonomisko attīstību un Rīgas starptautisko konkurētspēju, ieviest reģionālās ekonomiskās atdeves principu (daļai reģionos radīto nodokļu jāatgriežas to attīstībā) un piesaistīt reģioniem jaunos speciālistus ar mājokļa un studiju atbalstu. Fiskālajai decentralizācijai sola daļu uzņēmumu ienākuma nodokļa un pievienotās vērtības nodokļa novirzīt uzņēmuma darbības vietas pašvaldībai un pārdalīt iedzīvotāju ienākuma nodokļa pašvaldību daļu starp dzīvesvietas un darba vietas pašvaldībām.
  
  **Citāts:** „Atbalstīsim REĢIONĀLĀS EKONOMISKĀS ATDEVES principu”

### ASL — PIEMIN

- claim_id 532600 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts astoņos gados dubultot Latvijas ekonomiku, palielināt IIN neapliekamo minimumu vidējās algas apmērā (norādīts 1900 eiro mēnesī), samazināt sociālo iemaksu darba ņēmēja daļu par 6 %, atcelt nekustamā īpašuma nodokli vienīgajam ģimenes mājoklim un radīt modernu ekosistēmu zinātnes komercializācijai un efektīviem iepirkumiem.
  
  **Citāts:** „Dubultosim Latvijas ekonomiku 8 gados”
- claim_id 532604 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts veicināt dzimstību, lai sasniegtu summāro dzimstības koeficientu vismaz 2,1: palielināt piedzimšanas pabalstu Latvijas pilsonēm 3 vidējo algu apmērā, bērna kopšanas pabalstu minimālās algas apmērā, palielināt neapliekamo minimumu par katru bērnu, nodrošināt elastīgu mājokļu atbalstu jaunajām ģimenēm, kā arī pārtraukt starptautisko un nacionālo dokumentu darbību, kas grauj ģimenes un bioloģiskā dzimuma jēdzienus.
  
  **Citāts:** „Veicināsim latviešu tautas ataudzi, lai sasniegtu summāro dzimstības koeficientu vismaz 2,1 apmērā”

### SC — PIEMIN

- claim_id 532691 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts dibināt Latvijas Valsts attīstības banku valsts investīciju politikas nodrošināšanai, pastiprināt nodokļu progresivitāti, pārceļot slogu no zemiem un vidējiem ienākumiem uz lieliem, ieviest bagātības nodokli (ienākumiem virs 50 tūkst. eiro gadā vai mantai virs 1 milj. eiro) un luksusa un neizmantotā nekustamā īpašuma nodokli. Solīts arī ieviest pārtikas cenu ķēdes caurskatāmību un pārmērīgas peļņas ierobežošanu pamatprecēm, izskaust plēsonīgo ātro kredītu praksi ar izmaksu griestiem un veikt valsts pārvaldes funkciju un iepirkumu auditu.

### GS — PIEMIN

- claim_id 532816 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola radikālu atbalstu daudzbērnu ģimenēm un dzimstībai: atceltu iedzīvotāju ienākuma nodokli ģimenēm ar trīs un vairāk bērniem; garantētu vismaz 5000 eiro vienreizēju pabalstu par katra bērna piedzimšanu; noteiktu ģimenes valsts pabalstu 1000 eiro mēnesī par bērnu līdz 2 gadu vecumam, 100 eiro par vienu bērnu, 300 eiro par diviem, 900 eiro par trīs un 400 eiro par katru no četriem un vairāk bērniem (no 2 gadu vecuma); ģimenēm ar 3+ bērniem pakalpojumus sniegtu ārpus kārtas. Atbalstītu seniorus ar bezmaksas sabiedrisko transportu pensionāriem visā Latvijā un personas ar invaliditāti; ieviestu automātisku atbalsta piešķiršanu bez iesniegumiem un ar likumu aizliegtu krīzes laikā atsavināt cilvēka vienīgo mājokli.
  
  **Citāts:** „atbrīvosim daudzbērnu ģimenes no iedzīvotāju ienākuma nodokļa maksāšanas”

### SV-AJ — PIEMIN

- claim_id 547973 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Nodokļu politikā solīts vismaz 5 gadu moratorijs nodokļu paaugstināšanai un jaunu nodokļu ieviešanai, nekustamā īpašuma nodokļa atcelšana visiem mājokļiem, PVN samazināšana pārtikai un sabiedriskajai ēdināšanai līdz 5 %, iedzīvotāju ienākuma nodokļa atcelšana jauniešiem līdz 25 gadu vecumam un uzņēmējiem labvēlīgāka nodokļu sistēma; solīts atgriezt Latvijas zelta krājumus glabāšanā Latvijas Bankā.
  
  **Citāts:** „ieviest vismaz 5 gadu moratoriju nodokļu paaugstināšanai un jaunu nodokļu ieviešanai”

_Piemin: 10 no 14._


## k06 — Pievienotās vērtības nodoklis pārtikai vai citām pamatprecēm jāsamazina.

Tēmas: Budžets un finanses  
Kodēšanas atgādne: par = samazināt PVN; pret = PVN nemainīt / celt


### JV — PIEMIN

- claim_id 532670 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot fiskāli atbildīgu budžetu ar valsts ārējā parāda līmeni zem 55% no IKP, ievērojot eirozonas fiskālos noteikumus. Paredzēts celt minimālo algu līdz 50% no vidējās bruto darba samaksas, palielināt fiksēto neapliekamo minimumu līdz 80% no minimālās algas, padarīt nekustamā īpašuma nodokli par pilnvērtīgu pašvaldību nodokli, attīstīt kapitāla tirgu un valsts attīstības fondu. Ekonomikā izvirzīts mērķis panākt vismaz 3,5% IKP izaugsmi gadā un investīcijas virs 30% no IKP, pārejot uz augstas pievienotās vērtības ekonomiku.

### PRO — PIEMIN

- claim_id 532620 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts ieviest plašāku nodokļu progresivitāti, samazinot nodokļus mazajām un vidējām algām un palielinot neapliekamo minimumu, minimālo algu piesaistīt vidējai algai, pāriet no minimālās sociālo iemaksu bāzes uz proporcionālām iemaksām, vienkāršot nodokļu nomaksu maziem un vidējiem uzņēmumiem, kā arī veidot mērķtiecīgas valsts atbalsta programmas augstas pievienotās vērtības un eksporta uzņēmumiem un jaunuzņēmumu atbalsta programmu tehnoloģiju komandām.

### ZZS — PIEMIN

- claim_id 547879 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi līdz 2030. gadam panākt IKP izaugsmi vismaz par 2% virs ES vidējā, ikgadējās ārvalstu investīcijas vismaz 1 mljrd. € apmērā un IKP pieaugumu +3,8 mljrd. € gadā, minimālo algu 1250 € un vidējo algu 2500 €. Sola vienkāršāku nodokļu sistēmu mazajam biznesam, nodokļu atlaides ieguldījumiem ražīguma, efektivitātes un digitalizācijas celšanai, Latvijas kreditēšanas un investīciju fonda un krājaizdevu sabiedrību attīstību, eksporta veicināšanu un klasterus, kā arī darba ražīguma pieaugumu vismaz 5% gadā. Dzīves dārdzības mazināšanai sola samazinātu PVN (5% pirmās nepieciešamības pārtikai, 12% sabiedriskajai ēdināšanai un izmitināšanas pakalpojumiem), 0% nekustamā īpašuma nodokli primārajam mājoklim, attaisnoto izdevumu slieksni 1800 €, mazumtirdzniecības uzraudzības un 'pārtikas groza' iniciatīvas pilnveidi un sabiedrisko pakalpojumu cenu auditu.

### NA — TĒMA

- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.

### LPV — PIEMIN

- claim_id 532642 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts noteikt 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli un 10% kapitāla pieauguma nodokli, samazināt PVN līdz 10% apkurei, plašākam pārtikas klāstam, bērnu precēm, tūrismam un ēdināšanai, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim, atbrīvot māti no IIN, ja ģimenē aug vismaz divi bērni, palielināt neapliekamo minimumu līdz minimālās algas apmēram, atcelt nodokļus jauniešu algām pirmajā darba gadā un samazināt darbaspēka nodokļus līdz Eiropas vidējam līmenim; izveidot Nacionālo attīstības banku uz ALTUM bāzes un veidot Latviju par fintech, IT un mākslīgā intelekta centru.
  
  **Citāts:** „Samazināsim nodokļus, nosakot: 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli (UIN), 10% kapitāla pieauguma nodokli.”

### AS — PIEMIN

- claim_id 532822 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Sasniegs bezdeficīta bāzes budžetu četru gadu laikā. Stabilizēs nodokļu politiku, pārtraucot tās regulāru pārskatīšanu; ieviesīs mikrouzņēmumu nodokļa 10% likmi fiziskajām personām, samazinās kapitāla pieauguma IIN līdz 17% un saglabās UIN režīmu (peļņu apliekot tikai tad, kad to sadala dividendēs). Samazinās nodokļu maksātāju administratīvo slogu un mazinās ēnu ekonomiku ar motivāciju strādāt legāli, ne sodīšanu. Izveidos valsts garantiju programmu mājokļu būvniecībai reģionos, palielinot kreditēšanu par 2 miljardiem, koncentrēs valsts atbalstu augstas pievienotās vērtības nozarēs, samazinās valsts tiešo iejaukšanos ekonomikā un sekmēs publiskās un privātās partnerības projektus.
  
  **Citāts:** „Mūsu prioritāte ir ieviest kārtību valsts finansēs, lai sasniegtu bezdeficīta bāzes budžetu četru gadu laikā.”

### MMN — PIEMIN (citā tēmā)

- claim_id 532776 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Atbalstīt ģimenes un demogrāfiju ar nodokļu instrumentiem: palielināt iedzīvotāju ienākuma nodokļa atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī un noteikt 0% PVN likmi pirmā mājokļa iegādei jaunos projektos.
  
  **Citāts:** „palielināsim IIN atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī”
- claim_id 532779 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Stiprināt pašvaldību un reģionu autonomiju: Latgalē un Alūksnes novadā ieviest īpašu ekonomisko režīmu (PVN 10%, UIN atlaides pierobežas uzņēmumiem); ļaut pašvaldībām referendumā atjaunoties iepriekšējās robežās; liegt ministrijām diktēt teritoriju plānojumu un padarīt pašvaldību referendumus juridiski saistošus; novirzīt 20% no uzņēmuma UIN attiecīgajai pašvaldībai; ieviest tiešas mēru vēlēšanas; samazināt Rīgas domes deputātu skaitu uz pusi.
  
  **Citāts:** „Latgalē un Alūksnes novadā ieviešot īpašu ekonomisko režīmu”

### LA — TĒMA

- claim_id 547870 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola līdz 2030. gadam panākt sabalansētu valsts budžetu, vienlaikus saglabājot spēju ieguldīt drošībā, izglītībā, veselības aprūpē, sociālajā nodrošinājumā un zinātnē. Sola veidot stabilu, prognozējamu un uz izaugsmi orientētu uzņēmējdarbības vidi, samazināt birokrātiju, uzlabot regulējuma kvalitāti un attīstīt kapitāla tirgu. Sola atbalstīt mākslīgo intelektu, biomedicīnu, aizsardzības industriju, zaļās tehnoloģijas un zinātņietilpīgu ražošanu un panākt, ka ieguldījumi pētniecībā un attīstībā līdz 2030. gadam sasniedz vismaz 2% no iekšzemes kopprodukta. Izvirza mērķi ekonomikai augt straujāk nekā Eiropas Savienībā vidēji.

### ST — PIEMIN

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.

### JKP — PIEMIN

- claim_id 532798 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stabilu un konkurētspējīgu nodokļu politiku bez haotiskām izmaiņām: atcelt kapitāla pieauguma nodokli mantotam īpašumam un privātpersonu nekustamā īpašuma atsavināšanai, kā arī atcelt nekustamā īpašuma nodokli mājokļiem. Ekonomikā sola veicināt investīcijas un eksportspēju augstas pievienotās vērtības nozarēs, atbalstīt mazo uzņēmējdarbību, mazināt administratīvo slogu un nodrošināt pieejamāku kreditēšanu reģionos. Iestājas pret legālas skaidras naudas aprites ierobežošanu.
  
  **Citāts:** „Veidosim STABILU UN KONKURĒTSPĒJĪGU NODOKĻU POLITIKU”

### ASL — TĒMA

- claim_id 532600 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts astoņos gados dubultot Latvijas ekonomiku, palielināt IIN neapliekamo minimumu vidējās algas apmērā (norādīts 1900 eiro mēnesī), samazināt sociālo iemaksu darba ņēmēja daļu par 6 %, atcelt nekustamā īpašuma nodokli vienīgajam ģimenes mājoklim un radīt modernu ekosistēmu zinātnes komercializācijai un efektīviem iepirkumiem.
  
  **Citāts:** „Dubultosim Latvijas ekonomiku 8 gados”

### SC — PIEMIN (citā tēmā)

- claim_id 532687 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts stiprināt publisko veselības aprūpi: samazināt PVN būtiskākajām zālēm līdz 5 % un ieviest stingrāku zāļu cenu kontroli, izveidot valsts centralizētu zāļu iepirkumu un valsts aptieku tīkla pilotprojektu, ieviest centralizētu rindu pārvaldības sistēmu, stiprināt reģionālās slimnīcas, ieviest četru gadu atalgojuma grafiku mediķiem, māsām un NMPD darbiniekiem, pakāpeniski paplašināt valsts apmaksātu zobārstniecību un ikgadējas bezmaksas profilakses pārbaudes. Jaunu mediķu sagatavošanu valsts apmaksātu ar pienākumu noteiktu laiku strādāt Latvijas publiskajā veselības aprūpē. Solīts arī 10 % cukura nodoklis saldinātiem dzērieniem.

### GS — PIEMIN

- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547973 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Nodokļu politikā solīts vismaz 5 gadu moratorijs nodokļu paaugstināšanai un jaunu nodokļu ieviešanai, nekustamā īpašuma nodokļa atcelšana visiem mājokļiem, PVN samazināšana pārtikai un sabiedriskajai ēdināšanai līdz 5 %, iedzīvotāju ienākuma nodokļa atcelšana jauniešiem līdz 25 gadu vecumam un uzņēmējiem labvēlīgāka nodokļu sistēma; solīts atgriezt Latvijas zelta krājumus glabāšanā Latvijas Bankā.
  
  **Citāts:** „ieviest vismaz 5 gadu moratoriju nodokļu paaugstināšanai un jaunu nodokļu ieviešanai”

_Piemin: 11 no 14._


## k07 — Ja valsts nespēj nodrošināt ārstēšanu laikā, valstij tā jāapmaksā privātā iestādē.

Tēmas: Veselības aprūpe  
Kodēšanas atgādne: par = nauda seko pacientam / privāto integrācija; pret = tikai valsts sistēma


### JV — PIEMIN

- claim_id 532673 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot prognozējamu veselības finansējumu ne mazāk kā 6% apmērā no IKP un izveidot Nacionālo veselības un apdrošināšanas fondu. Paredzēts mazināt rindas, stiprināt primāro aprūpi, ģimenes ārstu pieejamību, slimnīcu un zāļu pieejamību, onkoloģijas, sirds un asinsvadu, garīgās veselības, rehabilitācijas un paliatīvās aprūpes pakalpojumus, attīstīt digitālu veselības sistēmu ar vienotu pacientu portālu, kā arī stiprināt mediķu izglītību un atalgojumu.

### PRO — TĒMA

- claim_id 532625 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts noteikt gada līdzmaksājumu griestus kompensējamām zālēm, stiprināt profilaksi ar centralizētu skrīningu un valsts apmaksātu BRCA testēšanu, nodrošināt agrīnu palīdzību psihiskās veselības, atkarību un reto slimību gadījumos, ieviest vienotu pieraksta sistēmu ar pacientu prioritizāciju un digitālās veselības ekosistēmu, kā arī pārveidot Nacionālo veselības dienestu par neatkarīgu, rezultātos balstītu pakalpojumu iepircēju.

### ZZS — PIEMIN

- claim_id 547880 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola ikgadēju veselības nozares budžeta pieaugumu līdz 6% no IKP, lai mazinātu rindas un uzlabotu pakalpojumu pieejamību, fokusēties uz profilaksi un veselīgi nodzīvotiem dzīves gadiem, paplašināt piekļuvi medikamentiem un rehabilitācijai onkoloģijā un reto slimību jomā ar pārrobežu sadarbību, veicināt bērnu zobārstniecības pieejamību, stiprināt cīņu ar atkarībām, nodrošināt atbilstošus tarifus un finansējumu ģimenes ārstiem, reģionālajām slimnīcām un universitātes klīnikām, turpināt medikamentu cenu reformu, atcelt recepšu apkalpošanas maksu, samazināt PVN un paplašināt kompensējamo zāļu grozu, kā arī risināt ārstniecības personāla pieejamību.

### NA — PIEMIN

- claim_id 532720 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts samazināt rindas pie speciālistiem, konsolidējot publisko un privāto finansējumu, nodrošināt ģimenes ārstu pieejamību un integrētu veselības aprūpi visos novados, ieviest profilaktisko pārbaužu programmu "Vesels mūžs", attīstīt psihiskās veselības pakalpojumus, paplašināt medikamentu pieejamību un kompensācijas hronisko slimību pacientiem, nodrošināt 100% valsts finansētu veselības aprūpi bērniem līdz 18 gadu vecumam un pievērst uzmanību vīriešu veselības problēmām.

### LPV — PIEMIN

- claim_id 532660 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts palielināt finansējumu kvalitatīvai medicīnas aprūpei un veicināt atalgojuma pieaugumu nozarē, nodrošināt pieejamāku aprūpi ar īsākām rindām, īpašu uzmanību pievērst onkoloģijas, sirds un asinsvadu, diabēta un jauniešu mentālās veselības ārstēšanai, paplašināt kompensēto zāļu pieejamību un attīstīt medicīnas tūrismu.
  
  **Citāts:** „Nodrošināsim pieejamāku veselības aprūpi – īsākas rindas pie speciālistiem un uz izmeklējumiem.”

### AS — PIEMIN

- claim_id 532826 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Reformēs veselības aprūpes pārvaldību: pārveidos kvotu sistēmu, ieviesīs vienotu pierakstu un valsts veselības apdrošināšanas modeli, kurā nauda seko pacientam neatkarīgi no tā, vai viņš ārstējas valsts vai sertificētā privātā iestādē. NVD pārveidos par fondu ar ilgtermiņa finanšu plānošanu. Nodrošinās bērnu savlaicīgu diagnostiku, optimizēs zāļu cenas ar caurredzamiem iepirkumiem, pakāpeniski samazinās līdzmaksājumus bērniem, senioriem un hronisku slimību pacientiem, piesaistīs mediķus novados ar mērķstipendijām un stiprinās paliatīvo un ilgstošās aprūpes pieejamību.
  
  **Citāts:** „Ieviesīsim valsts veselības apdrošināšanas modeli, kur nauda seko pacientam neatkarīgi no tā, vai ārstējas valsts vai sertificētā privātā iestādē.”

### MMN — PIEMIN

- claim_id 532775 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Mazināt pacientu rindas, prioritizējot nosūtījumus un pilnībā integrējot privātos pakalpojumu sniedzējus; ja valsts nespēj sniegt pakalpojumu medicīniski pamatotā termiņā, valsts sedz tarifa daļu privātā iestādē; budžeta palielinājumu primāri virzīt māsu un ārstu palīgu algām; pāriet uz vienotiem Baltijas zāļu iepirkumiem; salāgot tarifus ar reālo tirgu; pāriet uz ārstēšanas rezultātos balstītu finansējumu ar obligātu rezultātu publiskošanu.
  
  **Citāts:** „ja valsts nespēj sniegt pakalpojumu medicīniski pamatotā termiņā, pacients varēs vērsties privātā iestādē, kurai valsts segs noteiktā tarifa daļu”

### LA — PIEMIN

- claim_id 547872 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola panākt, lai ārstēšana būtu pieejama laikā neatkarīgi no cilvēka dzīvesvietas vai ienākumiem, stiprināt ģimenes ārstu lomu, samazināt gaidīšanas rindas un attīstīt aprūpi mājās. Sola pievērst īpašu uzmanību profilaktiskajām programmām, psihiskajai veselībai, onkoloģijai, sirds un asinsvadu slimību profilaksei un agrīnai diagnostikai, modernizēt un digitalizēt veselības aprūpes pārvaldību un nodrošināt konkurētspējīgu atalgojumu veselības aprūpes darbiniekiem. Sola nodrošināt ikgadēju, prognozējamu budžeta palielinājumu kompensējamajiem medikamentiem un ātrāku lēmumu pieņemšanu par jaunu zāļu iekļaušanu kompensējamo sarakstā.

### ST — PIEMIN

- claim_id 532595 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts palielināt veselības aprūpes finansējumu, samazināt rindas uz medicīniskajiem pakalpojumiem un attīstīt valsts medicīnas sistēmu, uzlabojot pieejamību reģionos un modernizējot medicīnas iestādes.

### JKP — PIEMIN

- claim_id 532810 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola tuvināt valsts finansējumu veselības aprūpei Eiropas attīstīto valstu vidējam līmenim, stiprināt aprūpes pieejamību reģionos (ģimenes ārstu tīkls, ambulatorie pakalpojumi, telemedicīna), mazināt rindas un pacientu līdzmaksājumus, uzlabot valsts apmaksātas bērnu zobārstniecības pieejamību, samazināt medikamentu un zāļu cenas un stiprināt profilaksi un agrīno diagnostiku. Sola arī atjaunot veselības mācību izglītības iestādēs.
  
  **Citāts:** „Veicināsim VALSTS FINANSĒJUMA VESELĪBAS APRŪPEI apjoma tuvināšanu Eiropas attīstīto valstu vidējam līmenim”

### ASL — PIEMIN

- claim_id 532613 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts valsts apmaksātos medicīnas pakalpojumus nodrošināt tikai Latvijas pilsoņiem, panākt vienmērīgu slimnīcu tīkla pārklājumu, samazināt ambulatoro pakalpojumu gaidīšanas rindas līdz 30 dienām ar bērnu veselību kā prioritāti, nodrošināt medikamentu kompensāciju pilnā apjomā un atbalstīt ģimenes paliatīvajā aprūpē.
  
  **Citāts:** „Ambulatoro pakalpojumu gaidīšanas rindu samazināšana līdz 30 dienām”

### SC — PIEMIN

- claim_id 532687 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts stiprināt publisko veselības aprūpi: samazināt PVN būtiskākajām zālēm līdz 5 % un ieviest stingrāku zāļu cenu kontroli, izveidot valsts centralizētu zāļu iepirkumu un valsts aptieku tīkla pilotprojektu, ieviest centralizētu rindu pārvaldības sistēmu, stiprināt reģionālās slimnīcas, ieviest četru gadu atalgojuma grafiku mediķiem, māsām un NMPD darbiniekiem, pakāpeniski paplašināt valsts apmaksātu zobārstniecību un ikgadējas bezmaksas profilakses pārbaudes. Jaunu mediķu sagatavošanu valsts apmaksātu ar pienākumu noteiktu laiku strādāt Latvijas publiskajā veselības aprūpē. Solīts arī 10 % cukura nodoklis saldinātiem dzērieniem.

### GS — TĒMA

- claim_id 532763 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola nodrošināt reālu un ātru primārās medicīnas — ģimenes ārstu, speciālistu un medmāsu — pieejamību ikvienam iedzīvotājam un ieviest vienotu, integrētu medicīnas izglītības procesu, likvidējot vietu trūkumu rezidentūrā.
  
  **Citāts:** „garantēs un nodrošinās primārās medicīnas jeb ģimenes ārstu, speciālistu un medmāsu reālu un ātru pieejamību”

### SV-AJ — PIEMIN

- claim_id 547987 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Veselības aprūpē solīts saglabāt slimnīcu tīkla pārklājumu, samazināt pacientu rindas un līdzmaksājumus, paplašināt kompensējamo medikamentu klāstu, samazināt PVN visiem medikamentiem līdz 5 %, ieviest zāļu cenu griestus, finansēt pensionāriem zobārstniecību 150 eiro apmērā gadā un nodrošināt bezmaksas ortodontiju bērniem.
  
  **Citāts:** „samazināt PVN visiem medikamentiem līdz 5%”

_Piemin: 12 no 14._


## k08 — Skolotāju algas jāceļ ātrāk nekā citās valsts sektora nozarēs.

Tēmas: Izglītība, Budžets un finanses  
Kodēšanas atgādne: par = pedagogu atalgojuma celšana; pret = nav


### JV — PIEMIN

- claim_id 532676 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts nodrošināt kvalitatīvu un iekļaujošu izglītību katram bērnam, mūsdienīgus mācību līdzekļus un taisnīgu, konkurētspējīgu atalgojumu visiem pedagogiem, noteikt vidējo vispārējo vai profesionālo izglītību obligātu un veidot nacionālu talantu attīstības sistēmu. Zinātnē paredzēts virzīties uz ieguldījumiem pētniecībā un attīstībā 3% apmērā no IKP, stiprināt valsts pētījumu programmas un izstrādāt jaunu Zinātniskās darbības likumu, kas sekmēs komercializāciju un universitāšu sadarbību ar industriju.

### PRO — PIEMIN

- claim_id 532635 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts noteikt jaunatnes politiku par valsts prioritāti, ieviest visaptverošu veselības mācību, tostarp seksuālo un reproduktīvo veselību, līdzsvarot skolēnu mācību slodzi, pacelt pedagogu zemāko likmi vismaz līdz 2100 eiro, ievirzīt profesionālo izglītību uz STEAM specializācijām un palielināt „Studētgods” stipendijas un finansējumu zinātnei un augstākajai izglītībai.

### ZZS — PIEMIN

- claim_id 547881 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt iekļaujošu, stabilu un kvalitatīvu izglītību visos līmeņos ar izcilību un pieejamību laukos, mazāk nepārtrauktu un vairāk pabeigtu reformu, kvalitatīvu mācību resursu un pedagogu pieejamību neatkarīgi no dzīvesvietas, kā arī pakāpeniski ieviest brīvpusdienas līdz 9. klasei no valsts budžeta. Izvirza mērķi augstākajai izglītībai un zinātnei novirzīt 2% no IKP, attīstīt augstskolas reģionu vajadzībām, eksporta spējīgu augstāko izglītību ES, NATO un OECD valstu studentiem, doktorantūras modeli, pētniecības iesaisti inovāciju ekosistēmā, augsta riska inovāciju finansējumu un dalību starptautiskās kosmosa programmās. Jauniešiem sola dzīves starta iespēju vienlīdzību, mazināt vardarbību skolu vidē un stiprināt sporta infrastruktūru arī laukos un mazpilsētās.

### NA — TĒMA

- claim_id 532701 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts izglītības saturu balstīt jaunākajos pētījumos, skolu tīklu saglabāt bērnu interesēs, stiprināt Latvijas vēstures un valstiskās audzināšanas saturu, ieviest finanšpratību un uzņēmējdarbības pamatus kā obligātu mācību saturu vidusskolā, nodrošināt tiešsaistes stundas reģionos, sagatavot skolu drošības algoritmus un gatavību attālinātām mācībām krīzēs, kā arī palielināt valsts pasūtījumu latviešu valodas, vēstures un kultūras pētījumiem.
- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.

### LPV — PIEMIN

- claim_id 532662 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts palielināt pedagogu atalgojumu, saglabāt lauku un reģionu skolas, nodrošināt bāzes mācību līdzekļus visos priekšmetos, ieviest vienkāršotu vērtēšanas sistēmu, samazināt skolotāju birokrātisko slogu, ieviest obligāto vidējo izglītību un finanšu pratības kursu, saglabāt vecāku izvēles tiesības izglītībā ģimenē un tālmācībā, panākt, ka absolventi zina vismaz četras valodas, un veicināt izglītības eksportu.
  
  **Citāts:** „Lai nodrošinātu izglītības kvalitāti, palielināsim pedagogu atalgojumu.”

### AS — PIEMIN

- claim_id 532830 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Pilnveidos 'Skola2030' sadarbībā ar pedagogiem, vecākiem un skolām, sakārtos vērtēšanas sistēmu un eksāmenu norisi un plašāk izmantos mākslīgā intelekta risinājumus mācību procesa individualizēšanai. Pakāpeniski cels pedagogu atalgojumu, sasaistot to ar slodzes sakārtošanu, izstrādās konkurētspējīgu profesionālās izglītības finansēšanas modeli un nodrošinās agrīnu bērnu vajadzību diagnostiku.
  
  **Citāts:** „Pakāpeniski celsim pedagogu atalgojumu, sasaistot to ar slodzes sakārtošanu.”

### MMN — PIEMIN

- claim_id 532778 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Decentralizēt izglītību, pārceļot lēmumu pieņemšanu no ministrijas uz skolām un stiprinot skolu autonomiju; atcelt dārgos centralizētos eksāmenus un vērtēt skolēnus pēc būtības; nodrošināt pedagogu algas no valsts neatkarīgi no pašvaldības; attīstīt profesionālo vidējo izglītību ar mērķi, ka 70% jauniešu to apzināti izvēlas; piešķirt valsts finansējumu pētniecībai, ja piesaistīts privāts vai starptautisks līdzfinansējums.
  
  **Citāts:** „atcelsim dārgos centralizētos eksāmenus”

### LA — PIEMIN

- claim_id 547871 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot izglītības sistēmu, kas nodrošina kvalitatīvu izglītību ikvienam bērnam neatkarīgi no dzīvesvietas, un turpināt stiprināt STEM jomas, kritisko domāšanu, pilsonisko līdzdalību un uzņēmējspējas. Sola nodrošināt, ka pedagoga darba samaksa par vienu pilnu slodzi sasniedz vismaz 1,2 valstī noteiktās vidējās darba samaksas līmeni, vienlaikus stiprinot profesionālās pilnveides un karjeras izaugsmes iespējas. Sola veidot vienotu zinātnes, augstākās izglītības un uzņēmējdarbības inovāciju ekosistēmu un attīstīt mūžizglītību un profesionālo pārkvalifikāciju.

### ST — TĒMA

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.
- claim_id 532594 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts atteikties no programmas „Skola 2030” un izveidot jaunu izglītības sistēmas programmu, kā arī nodrošināt iespēju iegūt izglītību dzimtajā valodā, tostarp krievu valodā, ar valsts finansētu mazākumtautību izglītību, brīvu izglītības iestāžu izvēli un bilingvālu izglītību, vienlaikus nodrošinot augstu latviešu valodas prasmes līmeni.

### JKP — PIEMIN

- claim_id 532813 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par kvalitatīvu, darba tirgus vajadzībām atbilstošu izglītību visā Latvijā, prioritāri stiprinot matemātikas, dabaszinātņu un tehnoloģiju apguvi. Pedagogiem sola mazināt birokrātisko slogu, veidot ilgtermiņā prognozējamu atalgojuma sistēmu un pilnveidot sociālo garantiju sistēmu. Zinātnē sola ilgtspējīgu pēcdoktorantūras finansējumu un augstākus pētījumu kvalitātes standartus, kā arī veicināt profesionālās izglītības prestižu un darba devēju iesaisti.
  
  **Citāts:** „Iestāsimies par KVALITATĪVU, darba tirgus vajadzībām atbilstošu IZGLĪTĪBU VISĀ LATVIJĀ”

### ASL — PIEMIN

- claim_id 532605 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts izglītības sistēmu attīstīt atbilstoši darba tirgus un tehnoloģiju pārmaiņām un nacionālās identitātes saglabāšanai, stiprināt lauku skolu tīklu, bērniem ar mācīšanās grūtībām nodrošināt izglītību atsevišķās klasēs un skolās, celt skolotāja profesijas prestižu ar samērīgu slodzi un finansējumu, kā arī paaugstināt augstākās izglītības stipendijas līdz pārējo Baltijas valstu līmenim.
  
  **Citāts:** „Celsim skolotāja profesijas prestižu. Nodrošināsim samērīgu slodzi, atbalsta personāla finansēšanu un pilnvērtīgus mācību materiālus”

### SC — PIEMIN

- claim_id 532688 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt pedagogu algas un mazināt birokrātisko slodzi, ieviest izdienas pensijas skolotājiem no 60 gadu vecuma, nodrošināt skolām psihologus un atbalsta personālu, integrēt digitālās prasmes un MI pamatus, ieviest obligātu vidējo vispārējo izglītību, palielināt budžeta vietu skaitu augstskolās un pakāpeniski virzīties uz bezmaksas augstāko izglītību valsts augstskolās. Solīts arī līdz 50 % valsts līdzfinansējums bērnu ārpusskolas nodarbībām un Mazākumtautību izglītības iestāžu likums, kas nodrošinātu izglītību mazākumtautību valodās, vienlaikus garantējot valsts valodas apguvi.

### GS — TĒMA

- claim_id 532761 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola izglītības sistēmas pilnīgu pārveidi: pilnībā atceltu mājasdarbu sistēmu, lai mācības noritētu skolā; atceltu aizliegumu labot atzīmes un atgrieztu motivējošu vērtēšanu; nodrošinātu bezmaksas ēdināšanu visiem bērniem no pirmsskolas līdz vidusskolas pēdējai klasei; izvietotu pirmsskolas un sākumskolas maksimāli tuvu bērna dzīvesvietai; garantētu kvalitatīvu vidējo izglītību ikvienam un piesaistītu spēcīgus ārvalstu mācībspēkus, saglabājot nacionālās vērtības.
  
  **Citāts:** „Mājasdarbu sistēma tiks pilnībā atcelta”
- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547984 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Izglītībā solīts atcelt Skola2030 un citas reformas, atcelt ierobežojumus tālmācībai un mājmācībai, piesaistīt pedagogu algas valsts vidējai mēnešalgai un ierobežot slodzi līdz 30 kontaktstundām, nodrošināt bezmaksas ēdināšanu un sabiedrisko transportu skolēniem un nosargāt mazās lauku skolas.
  
  **Citāts:** „atcelt Skola2030 un citas skolu reformas, nodrošināt pilnvērtīgus mācību materiālus”

_Piemin: 11 no 14._


## k09 — Augstskolu skaits jāsamazina, apvienojot tās.

Tēmas: Izglītība  
Kodēšanas atgādne: par = konsolidēt / apvienot augstskolas; pret = saglabāt reģionālās augstskolas


### JV — PIEMIN

- claim_id 532676 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts nodrošināt kvalitatīvu un iekļaujošu izglītību katram bērnam, mūsdienīgus mācību līdzekļus un taisnīgu, konkurētspējīgu atalgojumu visiem pedagogiem, noteikt vidējo vispārējo vai profesionālo izglītību obligātu un veidot nacionālu talantu attīstības sistēmu. Zinātnē paredzēts virzīties uz ieguldījumiem pētniecībā un attīstībā 3% apmērā no IKP, stiprināt valsts pētījumu programmas un izstrādāt jaunu Zinātniskās darbības likumu, kas sekmēs komercializāciju un universitāšu sadarbību ar industriju.

### PRO — TĒMA

- claim_id 532635 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts noteikt jaunatnes politiku par valsts prioritāti, ieviest visaptverošu veselības mācību, tostarp seksuālo un reproduktīvo veselību, līdzsvarot skolēnu mācību slodzi, pacelt pedagogu zemāko likmi vismaz līdz 2100 eiro, ievirzīt profesionālo izglītību uz STEAM specializācijām un palielināt „Studētgods” stipendijas un finansējumu zinātnei un augstākajai izglītībai.

### ZZS — PIEMIN

- claim_id 547881 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt iekļaujošu, stabilu un kvalitatīvu izglītību visos līmeņos ar izcilību un pieejamību laukos, mazāk nepārtrauktu un vairāk pabeigtu reformu, kvalitatīvu mācību resursu un pedagogu pieejamību neatkarīgi no dzīvesvietas, kā arī pakāpeniski ieviest brīvpusdienas līdz 9. klasei no valsts budžeta. Izvirza mērķi augstākajai izglītībai un zinātnei novirzīt 2% no IKP, attīstīt augstskolas reģionu vajadzībām, eksporta spējīgu augstāko izglītību ES, NATO un OECD valstu studentiem, doktorantūras modeli, pētniecības iesaisti inovāciju ekosistēmā, augsta riska inovāciju finansējumu un dalību starptautiskās kosmosa programmās. Jauniešiem sola dzīves starta iespēju vienlīdzību, mazināt vardarbību skolu vidē un stiprināt sporta infrastruktūru arī laukos un mazpilsētās.

### NA — PIEMIN (citā tēmā)

- claim_id 532706 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts ieviest stingru regulējumu un pastiprināt kontroli attiecībā uz trešo valstu pilsoņiem, novērst ekonomisko imigrantu legalizāciju, ieviest striktas kvotas uzturēšanās atļaujām, veicināt Latvijai nelojālu personu un Krievijas pilsoņu izceļošanu, panākt, ka augstskolas piesaista studentus no ES, NATO un OECD valstīm un diasporas, kā arī neatbalstīt ES lēmumus, kas uzliktu Latvijai pienākumu uzņemt imigrantus.

### LPV — TĒMA

- claim_id 532662 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts palielināt pedagogu atalgojumu, saglabāt lauku un reģionu skolas, nodrošināt bāzes mācību līdzekļus visos priekšmetos, ieviest vienkāršotu vērtēšanas sistēmu, samazināt skolotāju birokrātisko slogu, ieviest obligāto vidējo izglītību un finanšu pratības kursu, saglabāt vecāku izvēles tiesības izglītībā ģimenē un tālmācībā, panākt, ka absolventi zina vismaz četras valodas, un veicināt izglītības eksportu.
  
  **Citāts:** „Lai nodrošinātu izglītības kvalitāti, palielināsim pedagogu atalgojumu.”

### AS — TĒMA

- claim_id 532830 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Pilnveidos 'Skola2030' sadarbībā ar pedagogiem, vecākiem un skolām, sakārtos vērtēšanas sistēmu un eksāmenu norisi un plašāk izmantos mākslīgā intelekta risinājumus mācību procesa individualizēšanai. Pakāpeniski cels pedagogu atalgojumu, sasaistot to ar slodzes sakārtošanu, izstrādās konkurētspējīgu profesionālās izglītības finansēšanas modeli un nodrošinās agrīnu bērnu vajadzību diagnostiku.
  
  **Citāts:** „Pakāpeniski celsim pedagogu atalgojumu, sasaistot to ar slodzes sakārtošanu.”

### MMN — TĒMA

- claim_id 532778 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Decentralizēt izglītību, pārceļot lēmumu pieņemšanu no ministrijas uz skolām un stiprinot skolu autonomiju; atcelt dārgos centralizētos eksāmenus un vērtēt skolēnus pēc būtības; nodrošināt pedagogu algas no valsts neatkarīgi no pašvaldības; attīstīt profesionālo vidējo izglītību ar mērķi, ka 70% jauniešu to apzināti izvēlas; piešķirt valsts finansējumu pētniecībai, ja piesaistīts privāts vai starptautisks līdzfinansējums.
  
  **Citāts:** „atcelsim dārgos centralizētos eksāmenus”

### LA — PIEMIN

- claim_id 547871 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot izglītības sistēmu, kas nodrošina kvalitatīvu izglītību ikvienam bērnam neatkarīgi no dzīvesvietas, un turpināt stiprināt STEM jomas, kritisko domāšanu, pilsonisko līdzdalību un uzņēmējspējas. Sola nodrošināt, ka pedagoga darba samaksa par vienu pilnu slodzi sasniedz vismaz 1,2 valstī noteiktās vidējās darba samaksas līmeni, vienlaikus stiprinot profesionālās pilnveides un karjeras izaugsmes iespējas. Sola veidot vienotu zinātnes, augstākās izglītības un uzņēmējdarbības inovāciju ekosistēmu un attīstīt mūžizglītību un profesionālo pārkvalifikāciju.

### ST — TĒMA

- claim_id 532594 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts atteikties no programmas „Skola 2030” un izveidot jaunu izglītības sistēmas programmu, kā arī nodrošināt iespēju iegūt izglītību dzimtajā valodā, tostarp krievu valodā, ar valsts finansētu mazākumtautību izglītību, brīvu izglītības iestāžu izvēli un bilingvālu izglītību, vienlaikus nodrošinot augstu latviešu valodas prasmes līmeni.

### JKP — TĒMA

- claim_id 532813 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par kvalitatīvu, darba tirgus vajadzībām atbilstošu izglītību visā Latvijā, prioritāri stiprinot matemātikas, dabaszinātņu un tehnoloģiju apguvi. Pedagogiem sola mazināt birokrātisko slogu, veidot ilgtermiņā prognozējamu atalgojuma sistēmu un pilnveidot sociālo garantiju sistēmu. Zinātnē sola ilgtspējīgu pēcdoktorantūras finansējumu un augstākus pētījumu kvalitātes standartus, kā arī veicināt profesionālās izglītības prestižu un darba devēju iesaisti.
  
  **Citāts:** „Iestāsimies par KVALITATĪVU, darba tirgus vajadzībām atbilstošu IZGLĪTĪBU VISĀ LATVIJĀ”

### ASL — PIEMIN

- claim_id 532605 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts izglītības sistēmu attīstīt atbilstoši darba tirgus un tehnoloģiju pārmaiņām un nacionālās identitātes saglabāšanai, stiprināt lauku skolu tīklu, bērniem ar mācīšanās grūtībām nodrošināt izglītību atsevišķās klasēs un skolās, celt skolotāja profesijas prestižu ar samērīgu slodzi un finansējumu, kā arī paaugstināt augstākās izglītības stipendijas līdz pārējo Baltijas valstu līmenim.
  
  **Citāts:** „Celsim skolotāja profesijas prestižu. Nodrošināsim samērīgu slodzi, atbalsta personāla finansēšanu un pilnvērtīgus mācību materiālus”

### SC — PIEMIN

- claim_id 532688 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt pedagogu algas un mazināt birokrātisko slodzi, ieviest izdienas pensijas skolotājiem no 60 gadu vecuma, nodrošināt skolām psihologus un atbalsta personālu, integrēt digitālās prasmes un MI pamatus, ieviest obligātu vidējo vispārējo izglītību, palielināt budžeta vietu skaitu augstskolās un pakāpeniski virzīties uz bezmaksas augstāko izglītību valsts augstskolās. Solīts arī līdz 50 % valsts līdzfinansējums bērnu ārpusskolas nodarbībām un Mazākumtautību izglītības iestāžu likums, kas nodrošinātu izglītību mazākumtautību valodās, vienlaikus garantējot valsts valodas apguvi.

### GS — TĒMA

- claim_id 532761 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola izglītības sistēmas pilnīgu pārveidi: pilnībā atceltu mājasdarbu sistēmu, lai mācības noritētu skolā; atceltu aizliegumu labot atzīmes un atgrieztu motivējošu vērtēšanu; nodrošinātu bezmaksas ēdināšanu visiem bērniem no pirmsskolas līdz vidusskolas pēdējai klasei; izvietotu pirmsskolas un sākumskolas maksimāli tuvu bērna dzīvesvietai; garantētu kvalitatīvu vidējo izglītību ikvienam un piesaistītu spēcīgus ārvalstu mācībspēkus, saglabājot nacionālās vērtības.
  
  **Citāts:** „Mājasdarbu sistēma tiks pilnībā atcelta”

### SV-AJ — TĒMA

- claim_id 547984 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Izglītībā solīts atcelt Skola2030 un citas reformas, atcelt ierobežojumus tālmācībai un mājmācībai, piesaistīt pedagogu algas valsts vidējai mēnešalgai un ierobežot slodzi līdz 30 kontaktstundām, nodrošināt bezmaksas ēdināšanu un sabiedrisko transportu skolēniem un nosargāt mazās lauku skolas.
  
  **Citāts:** „atcelt Skola2030 un citas skolu reformas, nodrošināt pilnvērtīgus mācību materiālus”

_Piemin: 6 no 14._


## k10 — Darbaspēka imigrācija no trešajām valstīm jāierobežo arī tad, ja uzņēmumiem trūkst darbinieku.

Tēmas: Imigrācija  
Kodēšanas atgādne: par = ierobežot / kontrolēt; pret = atvieglot darbaspēka ievešanu


### JV — TĒMA

- claim_id 532666 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stiprināt austrumu robežu, neļaut robežpārkāpējiem iekļūt Latvijā un noteikt stingrākus nosacījumus trešo valstu pilsoņu uzturēšanās, studiju un nodarbinātības jomā.

### PRO — PIEMIN

- claim_id 532641 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts veidot gudru, tālredzīgu un drošu migrācijas politiku ar mērķi nodrošināt cieņpilnus dzīves apstākļus Latvijas un Eiropas iedzīvotājiem.

### ZZS — PIEMIN

- claim_id 547888 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola īstenot gudru imigrācijas politiku, nepieļaujot nelegālu imigrāciju un dodot priekšroku augsti kvalificētam darbaspēkam terminētam darbam Latvijas tautsaimniecības attīstībai, kā arī īstenot pārdomātu migrāciju valsts attīstības vajadzībām.

### NA — PIEMIN

- claim_id 532706 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts ieviest stingru regulējumu un pastiprināt kontroli attiecībā uz trešo valstu pilsoņiem, novērst ekonomisko imigrantu legalizāciju, ieviest striktas kvotas uzturēšanās atļaujām, veicināt Latvijai nelojālu personu un Krievijas pilsoņu izceļošanu, panākt, ka augstskolas piesaista studentus no ES, NATO un OECD valstīm un diasporas, kā arī neatbalstīt ES lēmumus, kas uzliktu Latvijai pienākumu uzņemt imigrantus.

### LPV — PIEMIN

- claim_id 532655 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts uzsākt bezprecedenta cīņu ar nelegālo migrāciju, lai Latvijas robežas būtu drošas.
  
  **Citāts:** „Uzsāksim bezprecedenta cīņu ar nelegālo migrāciju, lai Latvijas robežas būtu drošas.”

### AS — PIEMIN

- claim_id 532829 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Imigrāciju īstenos kontrolēti, sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.
  
  **Citāts:** „Imigrāciju īstenosim kontrolēti, uzturēšanās sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.”

### MMN — PIEMIN

- claim_id 532789 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Totāli ierobežot trešo valstu imigrāciju, izsniedzot termiņuzturēšanās atļaujas tikai Latvijā nepieejamiem kvalificētiem speciālistiem; pastiprināt armijas un Zemessardzes lomu robežapsardzībā.
  
  **Citāts:** „totāla trešo valstu imigrācijas ierobežošana”

### LA — KLUSĒ?


### ST — PIEMIN (citā tēmā)

- claim_id 532596 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts izstrādāt visaptverošu dzimstības veicināšanas programmu (finansiāls atbalsts ģimenēm, mājokļu pieejamība, bērnu aprūpe), palielināt atbalstu jaunajām un daudzbērnu ģimenēm, izstrādāt jaunu remigrācijas programmu tautiešu atgriešanai, kā arī stiprināt sociālo aizsardzību pensionāriem, daudzbērnu ģimenēm un personām ar invaliditāti, nodrošinot cilvēka cienīgu dzīves līmeni.

### JKP — PIEMIN

- claim_id 532796 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par stingru un kontrolētu imigrācijas politiku, nosakot augstas integrācijas prasības un prioritāti Latvijas ilgtermiņa interesēm.
  
  **Citāts:** „Iestāsimies par STINGRU UN KONTROLĒTU IMIGRĀCIJAS POLITIKU”

### ASL — PIEMIN

- claim_id 532597 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts apturēt masu imigrāciju: veicināt trešo valstu imigrantu izceļošanu, padarīt uzturēšanās atļauju kārtību stingrāku, izbeigt “viltus studentu” biznesu, slēgt austrumu robežu (atļaujot tikai izbraukšanu), noraidīt ES bēgļu kvotas, nepieļaut islāmisma izplatīšanos, noteikt termiņu nepilsoņa statusa izbeigšanai ar PSRS izcelsmes imigrantu repatriāciju un samazināt birokrātiju Latvijas pilsoņu reemigrācijai.
  
  **Citāts:** „Slēgsim austrumu robežu, šajā virzienā atļaujot tikai izbraukšanu no valsts. Pastiprināsim imigrācijas kontroles pasākumus valsts iekšienē”

### SC — KLUSĒ?


### GS — PIEMIN

- claim_id 532765 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Iestājas par stingru, nacionālajās interesēs balstītu migrācijas politiku; kategoriski iebilst pret masveida migrāciju un no ārpuses uzspiestām migrācijas kvotām; uzskata, ka Latvijai pašai ir tiesības lemt, kas drīkst ieceļot un uzturēties, un ka valsts robeža ir valsts pastāvēšanas pamats.
  
  **Citāts:** „kategoriski iebilstam pret masveida migrāciju un migrācijas kvotām”

### SV-AJ — PIEMIN (citā tēmā)

- claim_id 547972 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts ģimenes stiprināšanas likums, ģimenes valsts pabalsts 1/4 apmērā no minimālās algas par katru bērnu, atbalsts vecākam palikt ar bērnu līdz 3 gadu vecumam, dubultoti atvieglojumi viena vecāka ģimenēm, Goda ģimenes statuss uz mūžu daudzbērnu un adoptētāju ģimenēm un aktīva reemigrācijas politika; iebilst pret “ģimenes vērtības graujošu ideoloģiju”, tostarp Stambulas konvenciju.
  
  **Citāts:** „noteikt, ka ģimenes valsts pabalsts par katru bērnu ir 1/4 no minimālās algas”

_Piemin: 11 no 14._


## k11 — Skolās jāmāca tikai latviešu valodā, bez izņēmumiem mazākumtautību valodām.

Tēmas: Valodu politika, Izglītība  
Kodēšanas atgādne: par = tikai latviski / stiprināt; pret = izglītība dzimtajā valodā / krievu valoda kā izvēle


### JV — PIEMIN

- claim_id 532677 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stingri iestāties par kvalitatīvu un atbildīgu valsts valodas lietojumu visās jomās, kā arī paplašināt latviešu valodas apguves iespējas un pētniecību.

### PRO — TĒMA

- claim_id 532635 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts noteikt jaunatnes politiku par valsts prioritāti, ieviest visaptverošu veselības mācību, tostarp seksuālo un reproduktīvo veselību, līdzsvarot skolēnu mācību slodzi, pacelt pedagogu zemāko likmi vismaz līdz 2100 eiro, ievirzīt profesionālo izglītību uz STEAM specializācijām un palielināt „Studētgods” stipendijas un finansējumu zinātnei un augstākajai izglītībai.

### ZZS — PIEMIN (citā tēmā)

- claim_id 547889 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt stabilu atalgojuma pieaugumu kultūras nozarē, reģionu kultūras infrastruktūras (bibliotēku, kultūras namu) noturību, sakrālā un nemateriālā mantojuma saglabāšanu, profesionālās mākslas pieejamību reģionos, tostarp stiprināt GORA attīstību ar valsts līdzdalību, attīstīt 'Skolas somas' pakalpojumu, atbalstīt amatiermākslu un radošās industrijas, stiprināt latviešu valodas lomu ikdienā, kā arī veicināt kultūras izcilības eksportu un pasaules līmeņa kultūras pieejamību Latvijā.

### NA — PIEMIN

- claim_id 532700 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts nodrošināt patērētāju tiesības saņemt jebkuru pakalpojumu latviešu valodā publiskajā un privātajā sektorā, noteikt valsts valodu par savstarpējās saziņas valodu valsts un pašvaldību iestādēs, palielināt Valsts valodas centra kapacitāti, ieviest latvisku vidi tehnoloģijās (latviešu valodas rīki, mākslīgais intelekts, digitālais saturs) un pieņemt Latvijas derusifikācijas deklarāciju okupācijas seku novēršanai.
- claim_id 532701 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts izglītības saturu balstīt jaunākajos pētījumos, skolu tīklu saglabāt bērnu interesēs, stiprināt Latvijas vēstures un valstiskās audzināšanas saturu, ieviest finanšpratību un uzņēmējdarbības pamatus kā obligātu mācību saturu vidusskolā, nodrošināt tiešsaistes stundas reģionos, sagatavot skolu drošības algoritmus un gatavību attālinātām mācībām krīzēs, kā arī palielināt valsts pasūtījumu latviešu valodas, vēstures un kultūras pētījumiem.

### LPV — TĒMA

- claim_id 532662 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts palielināt pedagogu atalgojumu, saglabāt lauku un reģionu skolas, nodrošināt bāzes mācību līdzekļus visos priekšmetos, ieviest vienkāršotu vērtēšanas sistēmu, samazināt skolotāju birokrātisko slogu, ieviest obligāto vidējo izglītību un finanšu pratības kursu, saglabāt vecāku izvēles tiesības izglītībā ģimenē un tālmācībā, panākt, ka absolventi zina vismaz četras valodas, un veicināt izglītības eksportu.
  
  **Citāts:** „Lai nodrošinātu izglītības kvalitāti, palielināsim pedagogu atalgojumu.”
- claim_id 532664 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts saliedēt Latvijas tautu, apvienojot iedzīvotājus neatkarīgi no viņu dzimtās valodas, un noteikt angļu valodu par oficiālo starptautiskā biznesa valodu Latvijā, ļaujot ārvalstu uzņēmumiem iesniegt atskaites Valsts ieņēmumu dienestā angļu valodā.
  
  **Citāts:** „Angļu valoda būs oficiālā starptautiskā biznesa valoda Latvijā.”

### AS — PIEMIN (citā tēmā)

- claim_id 532829 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Imigrāciju īstenos kontrolēti, sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.
  
  **Citāts:** „Imigrāciju īstenosim kontrolēti, uzturēšanās sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.”

### MMN — TĒMA

- claim_id 532778 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Decentralizēt izglītību, pārceļot lēmumu pieņemšanu no ministrijas uz skolām un stiprinot skolu autonomiju; atcelt dārgos centralizētos eksāmenus un vērtēt skolēnus pēc būtības; nodrošināt pedagogu algas no valsts neatkarīgi no pašvaldības; attīstīt profesionālo vidējo izglītību ar mērķi, ka 70% jauniešu to apzināti izvēlas; piešķirt valsts finansējumu pētniecībai, ja piesaistīts privāts vai starptautisks līdzfinansējums.
  
  **Citāts:** „atcelsim dārgos centralizētos eksāmenus”

### LA — TĒMA

- claim_id 547871 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot izglītības sistēmu, kas nodrošina kvalitatīvu izglītību ikvienam bērnam neatkarīgi no dzīvesvietas, un turpināt stiprināt STEM jomas, kritisko domāšanu, pilsonisko līdzdalību un uzņēmējspējas. Sola nodrošināt, ka pedagoga darba samaksa par vienu pilnu slodzi sasniedz vismaz 1,2 valstī noteiktās vidējās darba samaksas līmeni, vienlaikus stiprinot profesionālās pilnveides un karjeras izaugsmes iespējas. Sola veidot vienotu zinātnes, augstākās izglītības un uzņēmējdarbības inovāciju ekosistēmu un attīstīt mūžizglītību un profesionālo pārkvalifikāciju.

### ST — PIEMIN

- claim_id 532593 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts nodrošināt plašākas iespējas krievu valodas lietošanai uzņēmējdarbībā, sabiedriskajā dzīvē un ikdienas saziņā.
- claim_id 532594 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts atteikties no programmas „Skola 2030” un izveidot jaunu izglītības sistēmas programmu, kā arī nodrošināt iespēju iegūt izglītību dzimtajā valodā, tostarp krievu valodā, ar valsts finansētu mazākumtautību izglītību, brīvu izglītības iestāžu izvēli un bilingvālu izglītību, vienlaikus nodrošinot augstu latviešu valodas prasmes līmeni.

### JKP — PIEMIN

- claim_id 532814 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stiprināt latviešu valodas lomu izglītībā, publiskajā telpā un valsts pārvaldē.
  
  **Citāts:** „Stiprināsim LATVIEŠU VALODAS LOMU izglītībā, publiskajā telpā un valsts pārvaldē”

### ASL — PIEMIN

- claim_id 532598 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts būtiski stiprināt latviešu valodu un aizsargāt tās lietotājus, nosakot atbildību par necieņu pret to un par nepamatotu krievu valodas prasību uzspiešanu darba tirgū, kā arī nodrošināt darba vidi, apkalpošanu, saziņu, mediju darbu un reklāmas tikai valsts valodā.
  
  **Citāts:** „Nodrošināsim darba vidi, apkalpošanu un saziņu, kā arī mediju darbu un reklāmas tikai valsts valodā”

### SC — PIEMIN

- claim_id 532688 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt pedagogu algas un mazināt birokrātisko slodzi, ieviest izdienas pensijas skolotājiem no 60 gadu vecuma, nodrošināt skolām psihologus un atbalsta personālu, integrēt digitālās prasmes un MI pamatus, ieviest obligātu vidējo vispārējo izglītību, palielināt budžeta vietu skaitu augstskolās un pakāpeniski virzīties uz bezmaksas augstāko izglītību valsts augstskolās. Solīts arī līdz 50 % valsts līdzfinansējums bērnu ārpusskolas nodarbībām un Mazākumtautību izglītības iestāžu likums, kas nodrošinātu izglītību mazākumtautību valodās, vienlaikus garantējot valsts valodas apguvi.
- claim_id 532697 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts veicināt integrāciju ar bezmaksas latviešu valodas kursiem naturalizācijas eksāmenu kārtošanai un Latvijas Republikas pilsonības iegūšanai, virzoties uz pakāpenisku nepilsoņa statusa izbeigšanu.

### GS — TĒMA

- claim_id 532761 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola izglītības sistēmas pilnīgu pārveidi: pilnībā atceltu mājasdarbu sistēmu, lai mācības noritētu skolā; atceltu aizliegumu labot atzīmes un atgrieztu motivējošu vērtēšanu; nodrošinātu bezmaksas ēdināšanu visiem bērniem no pirmsskolas līdz vidusskolas pēdējai klasei; izvietotu pirmsskolas un sākumskolas maksimāli tuvu bērna dzīvesvietai; garantētu kvalitatīvu vidējo izglītību ikvienam un piesaistītu spēcīgus ārvalstu mācībspēkus, saglabājot nacionālās vērtības.
  
  **Citāts:** „Mājasdarbu sistēma tiks pilnībā atcelta”

### SV-AJ — PIEMIN

- claim_id 547985 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts atjaunot skolās krievu valodas apguvi izvēles kārtībā, nodrošināt latgaliešu un lībiešu valodas saglabāšanu un attīstību un mazākumtautību valodu cieņpilnu saglabāšanu, tostarp pieļaut apmācību mazākumtautību valodās privātskolās.
  
  **Citāts:** „atjaunot skolās krievu valodas apguvi izvēles kārtībā”

_Piemin: 9 no 14._


## k12 — Nepilsoņiem pilsonība jāpiešķir atvieglotā kārtībā.

Tēmas: Valodu politika, Imigrācija  
Kodēšanas atgādne: par = atvieglota naturalizācija; pret = repatriācija / statusa izbeigšana bez pilsonības


### JV — TĒMA

- claim_id 532666 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stiprināt austrumu robežu, neļaut robežpārkāpējiem iekļūt Latvijā un noteikt stingrākus nosacījumus trešo valstu pilsoņu uzturēšanās, studiju un nodarbinātības jomā.
- claim_id 532677 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stingri iestāties par kvalitatīvu un atbildīgu valsts valodas lietojumu visās jomās, kā arī paplašināt latviešu valodas apguves iespējas un pētniecību.

### PRO — TĒMA

- claim_id 532641 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts veidot gudru, tālredzīgu un drošu migrācijas politiku ar mērķi nodrošināt cieņpilnus dzīves apstākļus Latvijas un Eiropas iedzīvotājiem.

### ZZS — TĒMA

- claim_id 547888 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola īstenot gudru imigrācijas politiku, nepieļaujot nelegālu imigrāciju un dodot priekšroku augsti kvalificētam darbaspēkam terminētam darbam Latvijas tautsaimniecības attīstībai, kā arī īstenot pārdomātu migrāciju valsts attīstības vajadzībām.

### NA — TĒMA

- claim_id 532700 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts nodrošināt patērētāju tiesības saņemt jebkuru pakalpojumu latviešu valodā publiskajā un privātajā sektorā, noteikt valsts valodu par savstarpējās saziņas valodu valsts un pašvaldību iestādēs, palielināt Valsts valodas centra kapacitāti, ieviest latvisku vidi tehnoloģijās (latviešu valodas rīki, mākslīgais intelekts, digitālais saturs) un pieņemt Latvijas derusifikācijas deklarāciju okupācijas seku novēršanai.
- claim_id 532706 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts ieviest stingru regulējumu un pastiprināt kontroli attiecībā uz trešo valstu pilsoņiem, novērst ekonomisko imigrantu legalizāciju, ieviest striktas kvotas uzturēšanās atļaujām, veicināt Latvijai nelojālu personu un Krievijas pilsoņu izceļošanu, panākt, ka augstskolas piesaista studentus no ES, NATO un OECD valstīm un diasporas, kā arī neatbalstīt ES lēmumus, kas uzliktu Latvijai pienākumu uzņemt imigrantus.

### LPV — TĒMA

- claim_id 532655 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts uzsākt bezprecedenta cīņu ar nelegālo migrāciju, lai Latvijas robežas būtu drošas.
  
  **Citāts:** „Uzsāksim bezprecedenta cīņu ar nelegālo migrāciju, lai Latvijas robežas būtu drošas.”
- claim_id 532664 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts saliedēt Latvijas tautu, apvienojot iedzīvotājus neatkarīgi no viņu dzimtās valodas, un noteikt angļu valodu par oficiālo starptautiskā biznesa valodu Latvijā, ļaujot ārvalstu uzņēmumiem iesniegt atskaites Valsts ieņēmumu dienestā angļu valodā.
  
  **Citāts:** „Angļu valoda būs oficiālā starptautiskā biznesa valoda Latvijā.”

### AS — TĒMA

- claim_id 532829 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Imigrāciju īstenos kontrolēti, sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.
  
  **Citāts:** „Imigrāciju īstenosim kontrolēti, uzturēšanās sasaistot uzturēšanās atļaujas ar tiesisku nodarbinātību, integrāciju un latviešu valodas apguvi.”

### MMN — TĒMA

- claim_id 532789 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Totāli ierobežot trešo valstu imigrāciju, izsniedzot termiņuzturēšanās atļaujas tikai Latvijā nepieejamiem kvalificētiem speciālistiem; pastiprināt armijas un Zemessardzes lomu robežapsardzībā.
  
  **Citāts:** „totāla trešo valstu imigrācijas ierobežošana”

### LA — KLUSĒ?


### ST — PIEMIN (citā tēmā)

- claim_id 532591 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts samazināt birokrātiju, apvienojot ministrijas (Aizsardzības ar Iekšlietu, Izglītības un zinātnes ar Kultūras, Ekonomikas ar Finanšu) un likvidējot Klimata un enerģētikas ministriju; samazināt Saeimas deputātu skaitu no 100 uz 50; četru gadu laikā samazināt valsts pārvaldes aparātu par 30%; ieviest tautas vēlētu Valsts prezidentu ar attiecīgiem grozījumiem Satversmē; stiprināt deputātu personisko atbildību, atceļot iespēju balsojumos atturēties; ieviest politisko atbildību amatpersonām; likvidēt Sabiedrības integrācijas fondu; kā arī likvidēt nepilsoņa statusu un vienkāršot pilsonības iegūšanas kārtību.

### JKP — TĒMA

- claim_id 532796 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par stingru un kontrolētu imigrācijas politiku, nosakot augstas integrācijas prasības un prioritāti Latvijas ilgtermiņa interesēm.
  
  **Citāts:** „Iestāsimies par STINGRU UN KONTROLĒTU IMIGRĀCIJAS POLITIKU”
- claim_id 532814 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stiprināt latviešu valodas lomu izglītībā, publiskajā telpā un valsts pārvaldē.
  
  **Citāts:** „Stiprināsim LATVIEŠU VALODAS LOMU izglītībā, publiskajā telpā un valsts pārvaldē”

### ASL — PIEMIN

- claim_id 532597 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts apturēt masu imigrāciju: veicināt trešo valstu imigrantu izceļošanu, padarīt uzturēšanās atļauju kārtību stingrāku, izbeigt “viltus studentu” biznesu, slēgt austrumu robežu (atļaujot tikai izbraukšanu), noraidīt ES bēgļu kvotas, nepieļaut islāmisma izplatīšanos, noteikt termiņu nepilsoņa statusa izbeigšanai ar PSRS izcelsmes imigrantu repatriāciju un samazināt birokrātiju Latvijas pilsoņu reemigrācijai.
  
  **Citāts:** „Slēgsim austrumu robežu, šajā virzienā atļaujot tikai izbraukšanu no valsts. Pastiprināsim imigrācijas kontroles pasākumus valsts iekšienē”

### SC — PIEMIN

- claim_id 532697 · Valodu politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts veicināt integrāciju ar bezmaksas latviešu valodas kursiem naturalizācijas eksāmenu kārtošanai un Latvijas Republikas pilsonības iegūšanai, virzoties uz pakāpenisku nepilsoņa statusa izbeigšanu.

### GS — TĒMA

- claim_id 532765 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Iestājas par stingru, nacionālajās interesēs balstītu migrācijas politiku; kategoriski iebilst pret masveida migrāciju un no ārpuses uzspiestām migrācijas kvotām; uzskata, ka Latvijai pašai ir tiesības lemt, kas drīkst ieceļot un uzturēties, un ka valsts robeža ir valsts pastāvēšanas pamats.
  
  **Citāts:** „kategoriski iebilstam pret masveida migrāciju un migrācijas kvotām”

### SV-AJ — PIEMIN

- claim_id 547993 · Imigrācija · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts vienkāršot un paātrināt pilsonības iegūšanas procedūru Latvijas nepilsoņiem.
  
  **Citāts:** „vienkāršot un paātrināt pilsonības iegūšanas procedūru Latvijas nepilsoņiem”

_Piemin: 4 no 14._


## k13 — Ministriju skaits jāsamazina, tās apvienojot.

Tēmas: Valsts pārvalde, Budžets un finanses  
Kodēšanas atgādne: par = apvienot / likvidēt ministrijas; pret = nav


### JV — PIEMIN

- claim_id 532675 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts modernizēt valsts pārvaldi, mainot fokusu no procesa uz rezultātu – noteikt nozaru attīstības rādītājus, ministrus un iestāžu vadītājus vērtēt pēc rezultātiem, ieviest vienotas valdības pieeju un kopīgus pakalpojumu centrus, pāriet uz rezultātos balstītu budžeta veidošanu, kā arī samazināt administratīvo slogu, īpaši mazajiem uzņēmumiem.

### PRO — PIEMIN

- claim_id 532626 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts pamatot valsts izdevumus ar skaidri noteiktām funkcijām un izmērāmiem mērķrādītājiem un ieviest regulāru birokrātijas sloga novērtējumu.

### ZZS — PIEMIN

- claim_id 547892 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola mazināt birokrātiju, stiprinot 'vienas pieturas aģentūras' principu, efektivizēt likumdošanas procesu, samazināt ministriju skaitu un deleģēt funkcijas, kur tas lietderīgi, veikt valsts izdevumu un funkciju auditu, ietaupot vismaz 500 milj. € un pārvirzot tos uz veselību un reģioniem, ieviest publisko iepirkumu reformu un pieņemt datos balstītus lēmumus ar sabiedrības līdzdalību.

### NA — TĒMA

- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.
- claim_id 532712 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts ieviest mākslīgā intelekta risinājumus valsts pārvaldē administratīvā sloga mazināšanai un pārskatīt funkciju dublēšanos starp ministrijām un pašvaldībām.

### LPV — PIEMIN

- claim_id 532663 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts padarīt valsts pārvaldi efektīvāku, paplašinot ministru pilnvaras izdot nozares normatīvos aktus, veicināt mākslīgā intelekta izmantošanu, nodrošināt efektīvu ES fondu apguvi, apvienot valsts iestādes un ministrijas ar izmērāmiem efektivitātes rādītājiem ierēdņiem, kā arī organizēt katru nedēļu papildu Ministru kabineta sēdi uzņēmēju organizāciju priekšlikumu izskatīšanai.
  
  **Citāts:** „Lai valsts pārvaldi padarītu efektīvāku un operatīvāku, paplašināsim ministru pilnvaras, nosakot tiesības patstāvīgi izdot nozares ārējos normatīvos aktus.”

### AS — PIEMIN

- claim_id 532839 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Ieviesīs skaidrus augstāko amatpersonu rezultātu rādītājus un rotāciju, nostiprinās personisku atbildību par lēmumiem un reformēs Civildienesta likumu. Birokrātiju samazinās pēc principa, ka katrai jaunai prasībai jāaizstāj vai jāvienkāršo esošā. Centralizēs valsts IKT pārvaldību, plaši ieviesīs mākslīgā intelekta rīkus pakalpojumu automatizācijai, vienkāršos mazos publiskos iepirkumus un nodrošinās publisku budžeta datu pieejamību līdz rēķinu līmenim.
  
  **Citāts:** „Personiskai atbildībai par pieņemtajiem lēmumiem jākļūst par valsts pārvaldes normu.”

### MMN — PIEMIN

- claim_id 532771 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Veikt ģenerāltīrīšanu valsts pārvaldē, izveidojot kompaktāko un efektīvāko pārvaldi Eiropā: ieviest individuālu atbildību par katru lēmumu, atcelt Valsts civildienesta likumu (ierēdņus pakļaut Darba likumam), ar katru jaunu likumu atcelt vismaz divus esošos, reorganizēt vai likvidēt funkcijas dublējošas ministrijas un iestādes, kā arī saīsināt ietekmes uz vidi novērtējuma termiņus līdz 9 mēnešiem.
  
  **Citāts:** „ar katru jaunu likumu atcelsim vismaz divus esošos”

### LA — PIEMIN

- claim_id 547870 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola līdz 2030. gadam panākt sabalansētu valsts budžetu, vienlaikus saglabājot spēju ieguldīt drošībā, izglītībā, veselības aprūpē, sociālajā nodrošinājumā un zinātnē. Sola veidot stabilu, prognozējamu un uz izaugsmi orientētu uzņēmējdarbības vidi, samazināt birokrātiju, uzlabot regulējuma kvalitāti un attīstīt kapitāla tirgu. Sola atbalstīt mākslīgo intelektu, biomedicīnu, aizsardzības industriju, zaļās tehnoloģijas un zinātņietilpīgu ražošanu un panākt, ka ieguldījumi pētniecībā un attīstībā līdz 2030. gadam sasniedz vismaz 2% no iekšzemes kopprodukta. Izvirza mērķi ekonomikai augt straujāk nekā Eiropas Savienībā vidēji.

### ST — PIEMIN

- claim_id 532591 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts samazināt birokrātiju, apvienojot ministrijas (Aizsardzības ar Iekšlietu, Izglītības un zinātnes ar Kultūras, Ekonomikas ar Finanšu) un likvidējot Klimata un enerģētikas ministriju; samazināt Saeimas deputātu skaitu no 100 uz 50; četru gadu laikā samazināt valsts pārvaldes aparātu par 30%; ieviest tautas vēlētu Valsts prezidentu ar attiecīgiem grozījumiem Satversmē; stiprināt deputātu personisko atbildību, atceļot iespēju balsojumos atturēties; ieviest politisko atbildību amatpersonām; likvidēt Sabiedrības integrācijas fondu; kā arī likvidēt nepilsoņa statusu un vienkāršot pilsonības iegūšanas kārtību.

### JKP — PIEMIN

- claim_id 532806 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot efektīvu, profesionālu un uz rezultātu orientētu valsts pārvaldi, mazinot birokrātiju un izvērtējot valsts iestāžu funkcijas, apvienošanas iespējas un nepieciešamās strukturālās reformas.
  
  **Citāts:** „Veidosim EFEKTĪVU, profesionālu un uz rezultātu orientētu VALSTS PĀRVALDI”

### ASL — PIEMIN

- claim_id 532601 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts samazināt valsts pārvaldes aparātu un birokrātiju – iesaldēt administratīvo līdzekļu daļu, apvienot un likvidēt liekās ministrijas, atcelt valsts kapitālsabiedrību padomes, kā arī ļaut iestādēm pārnest daļu budžeta uz nākamo gadu, lai mazinātu nesaprātīgus tēriņus gada nogalē.
  
  **Citāts:** „Samazināsim valsts pārvaldes aparātu un birokrātiju – iesaldēsim administratīvo līdzekļu daļu valsts pārvaldē, apvienosim un likvidēsim liekās ministrijas, atcelsim valsts kapitālsabiedrību padomes”

### SC — PIEMIN (citā tēmā)

- claim_id 532688 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt pedagogu algas un mazināt birokrātisko slodzi, ieviest izdienas pensijas skolotājiem no 60 gadu vecuma, nodrošināt skolām psihologus un atbalsta personālu, integrēt digitālās prasmes un MI pamatus, ieviest obligātu vidējo vispārējo izglītību, palielināt budžeta vietu skaitu augstskolās un pakāpeniski virzīties uz bezmaksas augstāko izglītību valsts augstskolās. Solīts arī līdz 50 % valsts līdzfinansējums bērnu ārpusskolas nodarbībām un Mazākumtautību izglītības iestāžu likums, kas nodrošinātu izglītību mazākumtautību valodās, vienlaikus garantējot valsts valodas apguvi.
- claim_id 532698 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts atbalstīt bioloģisko lauksaimniecību ar mērķtiecīgām subsīdijām un mazāku birokrātiju, cīnīties par ES tiešmaksājumiem Latvijas lauksaimniekiem ES vidējā līmeņa apmērā, stiprināt lauksaimnieku kooperāciju pret starpnieku cenu varu un nodrošināt taisnīgas kompensācijas par ražošanu ierobežojošiem vides nosacījumiem.

### GS — TĒMA

- claim_id 532768 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola samazināt valsts aparātu un stiprināt tiešo demokrātiju: panāktu Satversmes grozījumus, lai Valsts prezidentu vēlētu visa tauta; samazinātu referenduma ierosināšanas slieksni līdz 50 000 parakstu un ieviestu e-referendumus; veiktu valsts pārvaldes reorganizāciju un normatīvo aktu vienkāršošanu; noteiktu, ka iestādes vispirms konsultē, nevis soda (aizliedzot soda naudas kā darbības kritēriju), un pārveidotu VID par palīgu, nevis represīvu instrumentu; ieviestu pilnīgu elektronisko dokumentu apriti, aizliedzot pieprasīt datus, kas jau ir valsts datubāzēs.
  
  **Citāts:** „samazināsim valsts aparātu un dosim tautai tiesības lemt par savu likteni”
- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547990 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts veikt valsts pārvaldes funkcionālo auditu, apvienot atsevišķas ministrijas un samazināt ierēdņu skaitu, ieviest tautas vēlētu prezidentu un likvidēt bijušo prezidentu privilēģijas, centralizēt iepirkumus un apvienot NMPD un VUGD.
  
  **Citāts:** „veikt valsts pārvaldes funkcionālo auditu, pārskatot iestāžu funkcijas un apvienojot atsevišķas ministrijas, samazināt ierēdņu skaitu”

_Piemin: 12 no 14._


## k14 — Lielāka nodokļu daļa jāatstāj pašvaldībām, mazāk jāpārdala caur valsts budžetu.

Tēmas: Pašvaldības, Budžets un finanses  
Kodēšanas atgādne: par = lielāka pašvaldību/reģionu daļa; pret = centralizēt


### JV — PIEMIN

- claim_id 532670 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot fiskāli atbildīgu budžetu ar valsts ārējā parāda līmeni zem 55% no IKP, ievērojot eirozonas fiskālos noteikumus. Paredzēts celt minimālo algu līdz 50% no vidējās bruto darba samaksas, palielināt fiksēto neapliekamo minimumu līdz 80% no minimālās algas, padarīt nekustamā īpašuma nodokli par pilnvērtīgu pašvaldību nodokli, attīstīt kapitāla tirgu un valsts attīstības fondu. Ekonomikā izvirzīts mērķis panākt vismaz 3,5% IKP izaugsmi gadā un investīcijas virs 30% no IKP, pārejot uz augstas pievienotās vērtības ekonomiku.

### PRO — PIEMIN (citā tēmā)

- claim_id 532639 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts stiprināt kultūras institūcijas kā kopienu noturības centrus reģionos, ieviest ALTUM grantu vēsturisko ēku atjaunošanai, reformēt kultūras nozarē strādājošo atlīdzības sistēmu un nostiprināt autoratlīdzības režīmu, veidot jaunu Dziesmu un deju svētku pārvaldības modeli un nodrošināt likumā noteikto VKKF finansējuma pieaugumu.

### ZZS — PIEMIN (citā tēmā)

- claim_id 547881 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt iekļaujošu, stabilu un kvalitatīvu izglītību visos līmeņos ar izcilību un pieejamību laukos, mazāk nepārtrauktu un vairāk pabeigtu reformu, kvalitatīvu mācību resursu un pedagogu pieejamību neatkarīgi no dzīvesvietas, kā arī pakāpeniski ieviest brīvpusdienas līdz 9. klasei no valsts budžeta. Izvirza mērķi augstākajai izglītībai un zinātnei novirzīt 2% no IKP, attīstīt augstskolas reģionu vajadzībām, eksporta spējīgu augstāko izglītību ES, NATO un OECD valstu studentiem, doktorantūras modeli, pētniecības iesaisti inovāciju ekosistēmā, augsta riska inovāciju finansējumu un dalību starptautiskās kosmosa programmās. Jauniešiem sola dzīves starta iespēju vienlīdzību, mazināt vardarbību skolu vidē un stiprināt sporta infrastruktūru arī laukos un mazpilsētās.
- claim_id 547890 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt reģionālajiem medijiem garantētu finansējumu drošībai un cīņai pret dezinformāciju.

### NA — TĒMA

- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.
- claim_id 532711 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts saglabāt lauku kopienu pakalpojumus (pasta punkti, ģimenes ārsti, mazās skolas, bibliotēkas), stiprināt kopienu lomu vietējo lēmumu pieņemšanā, nodrošināt platjoslas interneta pārklājumu visā valstī un izveidot reģionālo būvniecības programmu energoefektīviem īres mājokļiem ar izpirkuma tiesībām.

### LPV — PIEMIN

- claim_id 532643 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts reģionu attīstībai atdot pusi no uzņēmuma ienākuma nodokļa pašvaldībām un palielināt pašvaldību ienākumu bāzi, iekļaujot ienākumus no mežizstrādes; īpašu uzmanību pievērst Latgales — kā ES ārējās robežas — drošībai un ekonomiskajai attīstībai.
  
  **Citāts:** „Lai veicinātu reģionu attīstību, pusi no UIN atdosim pašvaldībām. Pašvaldību ienākumu bāzi palielināsim, iekļaujot ienākumus no mežizstrādes.”

### AS — PIEMIN

- claim_id 532832 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Izveidos vienotu valsts un pašvaldību pakalpojumu plānošanas modeli (izglītība, civilā aizsardzība, sabiedriskais transports, atkritumu apsaimniekošana u.c.) un taisnīgāku pašvaldību finanšu modeli, kas motivētu radīt darba vietas, piesaistīt investīcijas un palielināt pašu ieņēmumus.
  
  **Citāts:** „Izveidosim taisnīgāku pašvaldību finanšu modeli, kas motivēs radīt darba vietas, piesaistīt investīcijas un palielināt pašu ieņēmumus.”

### MMN — PIEMIN (citā tēmā)

- claim_id 532778 · Izglītība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Decentralizēt izglītību, pārceļot lēmumu pieņemšanu no ministrijas uz skolām un stiprinot skolu autonomiju; atcelt dārgos centralizētos eksāmenus un vērtēt skolēnus pēc būtības; nodrošināt pedagogu algas no valsts neatkarīgi no pašvaldības; attīstīt profesionālo vidējo izglītību ar mērķi, ka 70% jauniešu to apzināti izvēlas; piešķirt valsts finansējumu pētniecībai, ja piesaistīts privāts vai starptautisks līdzfinansējums.
  
  **Citāts:** „atcelsim dārgos centralizētos eksāmenus”

### LA — TĒMA

- claim_id 547870 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola līdz 2030. gadam panākt sabalansētu valsts budžetu, vienlaikus saglabājot spēju ieguldīt drošībā, izglītībā, veselības aprūpē, sociālajā nodrošinājumā un zinātnē. Sola veidot stabilu, prognozējamu un uz izaugsmi orientētu uzņēmējdarbības vidi, samazināt birokrātiju, uzlabot regulējuma kvalitāti un attīstīt kapitāla tirgu. Sola atbalstīt mākslīgo intelektu, biomedicīnu, aizsardzības industriju, zaļās tehnoloģijas un zinātņietilpīgu ražošanu un panākt, ka ieguldījumi pētniecībā un attīstībā līdz 2030. gadam sasniedz vismaz 2% no iekšzemes kopprodukta. Izvirza mērķi ekonomikai augt straujāk nekā Eiropas Savienībā vidēji.
- claim_id 547874 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola attīstīt reģionu ekonomiku, transporta un digitālo infrastruktūru, stiprināt pašvaldību kapacitāti un veicināt investīciju piesaisti ārpus Rīgas, lai dzīves kvalitāti nenoteiktu dzīvesvieta.

### ST — TĒMA

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.

### JKP — PIEMIN

- claim_id 532803 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veicināt reģionu ekonomisko attīstību un Rīgas starptautisko konkurētspēju, ieviest reģionālās ekonomiskās atdeves principu (daļai reģionos radīto nodokļu jāatgriežas to attīstībā) un piesaistīt reģioniem jaunos speciālistus ar mājokļa un studiju atbalstu. Fiskālajai decentralizācijai sola daļu uzņēmumu ienākuma nodokļa un pievienotās vērtības nodokļa novirzīt uzņēmuma darbības vietas pašvaldībai un pārdalīt iedzīvotāju ienākuma nodokļa pašvaldību daļu starp dzīvesvietas un darba vietas pašvaldībām.
  
  **Citāts:** „Atbalstīsim REĢIONĀLĀS EKONOMISKĀS ATDEVES principu”

### ASL — PIEMIN

- claim_id 532602 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts reformēt pašvaldību finansēšanas sistēmu taisnīgākai izlīdzināšanai – iedzīvotāju ienākuma nodokli pilnībā ieskaitīt valsts budžetā un dotēt pašvaldības atbilstoši to līdzšinējam īpatsvaram, iestrādājot uzņēmējdarbības piesaistes kritēriju, atbalstu lauku skolām un reģionālajai mobilitātei.
  
  **Citāts:** „Reformēsim pašvaldību finansēšanas sistēmu, nodrošinot taisnīgāku izlīdzināšanu”

### SC — PIEMIN (citā tēmā)

- claim_id 532687 · Veselības aprūpe · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts stiprināt publisko veselības aprūpi: samazināt PVN būtiskākajām zālēm līdz 5 % un ieviest stingrāku zāļu cenu kontroli, izveidot valsts centralizētu zāļu iepirkumu un valsts aptieku tīkla pilotprojektu, ieviest centralizētu rindu pārvaldības sistēmu, stiprināt reģionālās slimnīcas, ieviest četru gadu atalgojuma grafiku mediķiem, māsām un NMPD darbiniekiem, pakāpeniski paplašināt valsts apmaksātu zobārstniecību un ikgadējas bezmaksas profilakses pārbaudes. Jaunu mediķu sagatavošanu valsts apmaksātu ar pienākumu noteiktu laiku strādāt Latvijas publiskajā veselības aprūpē. Solīts arī 10 % cukura nodoklis saldinātiem dzērieniem.
- claim_id 532696 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts digitalizēt valsts pakalpojumus, noteikt 72 stundu termiņu valsts iestāžu atbildēm digitālajos kanālos, publicēt valsts un pašvaldību izdevumus tiešsaistē, ieviest personisko materiālo atbildību amatpersonām par apzināti nelikumīgiem vai budžetam kaitīgiem lēmumiem un izveidot Latvija.lv sabiedrisko konsultāciju sadaļu iedzīvotāju viedokļiem par likumprojektiem.

### GS — PIEMIN

- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547983 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts atjaunot pašvaldībām 95 % iedzīvotāju ienākuma nodokļa proporciju un lemt par uzņēmumu ienākuma nodokļa pārdali par labu pašvaldībām, kā arī sadarbībā ar tām nodrošināt pieejamākus īres mājokļus reģionos.
  
  **Citāts:** „atjaunot pašvaldībām IIN proporciju 95% apmērā, lemt par UIN pārdali par labu pašvaldībām”

_Piemin: 11 no 14._


## k15 — Rail Baltica jāpabeidz pilnā apjomā arī tad, ja izmaksas turpina augt.

Tēmas: Rail Baltica, Transports  
Kodēšanas atgādne: par = pabeigt pilnā apjomā; pret = apturēt / samazināt apjomu / auditēt pirms turpināt


### JV — PIEMIN

- claim_id 532681 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts satiksmē nodrošināt «Rail Baltica», reģionālo ceļu, dzelzceļa, ostu, sabiedriskā transporta un digitālās infrastruktūras attīstību ar skaidru atbildību, termiņiem un izmaksu kontroli.

### PRO — TĒMA

- claim_id 532624 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts ieviest vienotu sabiedriskā transporta mēnešbiļeti valsts mērogā ar 50% atlaidi jauniešiem līdz 25 gadiem un attīstīt drošu, modernu transporta infrastruktūru, prioritāti dodot gājējiem, velobraucējiem, sabiedriskajam transportam un stāvparkiem.

### ZZS — TĒMA

- claim_id 547894 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola pabeigt ostu reformu ar caurspīdīgu pārvaldību, atbalstīt nacionālas nozīmes infrastruktūras objektus (ostas, lidostas, lielceļus, tiltus), pārskatīt ceļu un sabiedriskā transporta plānošanu un atjaunot Ceļu fondu.

### NA — TĒMA

- claim_id 532710 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts uzlabot autoceļus un ostas, nosakot prioritāti valsts drošībai un eksportam.

### LPV — PIEMIN

- claim_id 532646 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts apturēt esošo, ekonomiski neizdevīgo 'Rail Baltica' projektu un to īstenot tikai tad, ja būs pieejams ES finansējums, ar mērķi savienot Ādažu militāro bāzi, Rīgas ostu un lidostu, izbūvējot Rīgas Ziemeļu koridoru gan autotransportam, gan dzelzceļam.
  
  **Citāts:** „Apturēsim esošo, ekonomiski neizdevīgo “Rail Baltica” projektu. To īstenosim tikai tad, ja būs pieejams ES finansējums.”

### AS — PIEMIN

- claim_id 532824 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Pārskatīs Rail Baltica apjomu uz minimālo realizējamo un ieviesīs pilnu finanšu caurredzamību un izmaksu kontroli.
  
  **Citāts:** „Pārskatīsim “Rail Baltica” apjomu uz minimālo realizējamo, ieviesīsim pilnu finanšu caurredzamību un izmaksu kontroli.”

### MMN — PIEMIN

- claim_id 532783 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Latvijas savienotība, vietējais dzelzceļš un kvalitatīvi autoceļi ir svarīgāki par Rail Baltica.
  
  **Citāts:** „vietējais dzelzceļš un kvalitatīvi autoceļi ir svarīgāki par Rail Baltica”

### LA — TĒMA

- claim_id 547877 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola turpināt attīstīt transporta infrastruktūru — ostas, lidostu, dzelzceļu un digitālos sakarus —, lai Latvija kļūtu par modernu Ziemeļeiropas loģistikas, inovāciju un uzņēmējdarbības centru.

### ST — KLUSĒ?


### JKP — TĒMA

- claim_id 532804 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par pieejamu sabiedrisko transportu starp novadiem, attīstības centriem un lielākajām pilsētām, kā arī sola attīstīt stratēģiskus ātrgaitas autoceļu koridorus uz Liepāju, Ventspili, Daugavpili, Alūksni, Lietuvu un Igauniju, izmantojot ES infrastruktūras un militārās mobilitātes finansējumu.
  
  **Citāts:** „Attīstīsim STRATĒĢISKUS ĀTRGAITAS AUTOCEĻU KORIDORUS”
- claim_id 532805 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma atbalsta Rail Baltic projekta pabeigšanu ar nosacījumu, ka tiek nodrošināta būvniecības izmaksu optimizācija, kontrole un finanšu caurskatāmība.
  
  **Citāts:** „Atbalstīsim RAIL BALTIC projekta pabeigšanu, ja tiks nodrošināta būvniecības izmaksu optimizācija”

### ASL — PIEMIN

- claim_id 532618 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts pabeigt “Rail Baltica” pamattrasi, samazinot izmaksas līdz kaimiņvalstu rādītājiem, un saukt pie atbildības politiķus, projekta izstrādātājus un vērtētājus, kuru darbība vai bezdarbība radījusi zaudējumus valstij.
  
  **Citāts:** „Pabeigsim “Rail Baltica” pamattrasi, samazinot izmaksas līdz kaimiņvalstu rādītājiem”

### SC — TĒMA

- claim_id 532689 · Transports · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts pārbūvēt Liepāja–Rīga šoseju par 4 joslu šoseju, stiprināt sabiedrisko transportu, dzelzceļu un ceļus ārpus Rīgas, kā arī modernizēt un elektrificēt Latvijas dzelzceļa tīklu.

### GS — KLUSĒ?


### SV-AJ — PIEMIN

- claim_id 547980 · Rail Baltica · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts pārtraukt Rail Baltica finansēšanu, iesaldēt būvniecību un noskaidrot atbildīgās personas par līdzekļu izšķērdēšanu.
  
  **Citāts:** „pārtraukt Rail Baltica finansēšanu, iesaldēt būvniecību un noskaidrot atbildīgās personas par līdzekļu izšķērdēšanu”

_Piemin: 6 no 14._


## k16 — Latvijas lauksaimnieku tiešmaksājumi jāpielīdzina ES vidējam līmenim.

Tēmas: Lauksaimniecība  
Kodēšanas atgādne: par = izlīdzināt tiešmaksājumus; pret = nav


### JV — PIEMIN

- claim_id 532680 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts pieprasīt ES tiešmaksājumu pieaugumu Latvijas lauksaimniekiem līdz ES vidējam līmenim, noteikt publiskajos iepirkumos prioritāti Latvijas pārtikai, veicināt kooperāciju produktivitātes kāpināšanai, kā arī stiprināt zilo ekonomiku, attīstot akvakultūru un zvejniecību.

### PRO — TĒMA

- claim_id 532634 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts piesaistīt subsīdijas lauksaimniekiem ar izmērāmiem vides un sociālajiem ieguvumiem.

### ZZS — PIEMIN

- claim_id 547883 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola celt lauksaimnieku konkurētspēju, nodrošinot kopējās lauksaimniecības politikas tiešmaksājumus ES vidējā līmenī, nesamazinātu nacionālo valsts atbalstu un atbilstošu līdzfinansējumu ES fondu apguvei, aizsargāt piekrastes zvejas, zvejnieku, iekšējo ūdeņu un makšķernieku intereses, atbalstīt īsās piegādes ķēdes un vietējo produktu iepirkumus, kā arī stiprināt lauku kopienas un pilsonisko līdzdalību, izmantojot LEADER pieeju.

### NA — TĒMA

- claim_id 532717 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts veicināt ilgtspējīgu lauksaimniecības un zivsaimniecības attīstību, palielinot investīcijas modernizācijā, efektivitātē un produktu pārstrādē ar augstu pievienoto vērtību, aizstāvot Latvijas intereses un taisnīgu konkurenci ES.

### LPV — PIEMIN

- claim_id 532648 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts panākt būtiski lielākus tiešmaksājumus lauksaimniekiem, samazināt tās 'zaļā kursa' prasības, kas ir pretrunā ar Latvijas nacionālajām interesēm un sadārdzina ražojumus, saglabāt un attīstīt kūdras ieguvi lauksaimniecībā, kā arī noteikt taisnīgas kompensācijas zemju īpašniekiem par saimnieciskās darbības ierobežojumiem.
  
  **Citāts:** „Panāksim būtiski lielākus tiešmaksājumus lauksaimniekiem.”

### AS — TĒMA

- claim_id 532834 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Iestāsies par vienlīdzīgiem ES platību maksājumiem no 2028. gada, atbalstu ražojošiem lauksaimniekiem, vietējās pārstrādes attīstību, meliorācijas sakārtošanu, zemes politikas modernizāciju, jauno lauksaimnieku ienākšanu nozarē un lielāku vietējās pārtikas īpatsvaru publiskajā patēriņā.
  
  **Citāts:** „Lauksaimniecībā iestāsimies par vienlīdzīgiem ES platību maksājumiem no 2028. gada, atbalstu ražojošiem lauksaimniekiem, vietējās pārstrādes attīstību.”

### MMN — PIEMIN

- claim_id 532788 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Radikāli mazināt birokrātiju zemniekiem un panākt tiešmaksājumu izlīdzināšanu līdz 100% no ES vidējā; valsts un pašvaldību iepirkumos noteikt, ka vismaz 95% pārtikas jābūt Latvijas izcelsmes, pat ja tas ir pretrunā ES regulējumam.
  
  **Citāts:** „valsts un pašvaldību iepirkumos vismaz 95% pārtikas jābūt Latvijas izcelsmes”

### LA — KLUSĒ?


### ST — KLUSĒ?


### JKP — PIEMIN

- claim_id 532800 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola aizstāvēt Latvijas lauksaimnieku intereses Eiropas Savienībā, panākot taisnīgu tiešmaksājumu izlīdzināšanu un stiprinot vietējo pārtikas ražošanu un pārstrādi.
  
  **Citāts:** „Aizstāvēsim LATVIJAS LAUKSAIMNIEKU INTERESES EIROPAS SAVIENĪBĀ”

### ASL — TĒMA

- claim_id 532614 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts samazināt birokrātiju lauksaimniecībā, veicinot kooperāciju un ilgtspējīgu saimniekošanu, atbalstīt Latvijas lauksaimniekus, stiprinot pārtikas pašpietiekamību un eksportspēju, kā arī nodrošināt ētiskas dzīvnieku labturības vērtības, saglabājot lauksaimnieku intereses.
  
  **Citāts:** „Atbalstīsim Latvijas lauksaimniekus, stiprinot pārtikas pašpietiekamību un eksportspēju”

### SC — PIEMIN

- claim_id 532698 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts atbalstīt bioloģisko lauksaimniecību ar mērķtiecīgām subsīdijām un mazāku birokrātiju, cīnīties par ES tiešmaksājumiem Latvijas lauksaimniekiem ES vidējā līmeņa apmērā, stiprināt lauksaimnieku kooperāciju pret starpnieku cenu varu un nodrošināt taisnīgas kompensācijas par ražošanu ierobežojošiem vides nosacījumiem.

### GS — KLUSĒ?


### SV-AJ — TĒMA

- claim_id 547976 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts aizstāvēt Latvijas zvejnieku intereses, panākot zvejas ierobežojumu pārskatīšanu Baltijas jūrā, nodrošināt vienlīdzīgus platību maksājumus lauksaimniekiem ES budžetā no 2028. gada, stiprināt Zemes fondu un ierobežot lauksaimniecības zemju izmantošanu saules parkiem, kā arī samazināt PVN lopbarībai un barības piedevām līdz 5 %.
  
  **Citāts:** „samazināt PVN līdz 5% lopbarībai un barības piedevām”

_Piemin: 6 no 14._


## k17 — Satversmē ģimene jādefinē kā vīrieša un sievietes savienība.

Tēmas: Sociālā politika, Tieslietas  
Kodēšanas atgādne: par = ģimenes definīcija / Stambulas konvencijas denonsēšana; pret = laulību vienlīdzība / visu ģimeņu aizsardzība


### JV — TĒMA

- claim_id 532674 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts demogrāfijas politiku veidot kā rūpes par stiprām ģimenēm, grūtniecību, dzemdībām, bērnu veselību, neauglības ārstēšanu, vecāku psihisko veselību, tēvu iesaisti, bērnu aprūpi un darba un privātās dzīves līdzsvaru. Paredzēts nodrošināt bērnu agrīnās attīstības vajadzību noteikšanu un atbalstu (BAASIK), kā arī atbalstīt sportu kā sabiedrības veselības un bērnu attīstības daļu.
- claim_id 532683 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stiprināt tiesiskumu, tiesu efektivitāti un neatkarību, iestāties par cilvēktiesībām, bērnu tiesībām un vardarbības novēršanu ģimenē, skolā un darba vidē, kā arī aizstāvēt demokrātiskās un eiropeiskās vērtības.

### PRO — PIEMIN

- claim_id 532622 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts palielināt ģimenes valsts pabalstu, mērķtiecīgi atbalstīt ģimenes ar zemiem ienākumiem un viena vecāka ģimenes, nodrošināt sociālās iemaksas bērna kopšanas atvaļinājuma laikā, pabalstus pakāpeniski piesaistīt ienākumu mediānai un celt minimālo ienākumu sliekšņus, atbalstīt vienlīdzīgas tiesības, tostarp laulību vienlīdzību un visu ģimeņu aizsardzību, veidot pieejamu īres mājokļu fondu cilvēkiem ar zemiem un vidējiem ienākumiem un pieejamu vidi personām ar invaliditāti.

### ZZS — TĒMA

- claim_id 547886 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola reformēt invaliditātes sistēmu uz funkcionēšanu balstītu novērtējumu ar lielāku atbalstu smagiem funkcionāliem traucējumiem, stiprināt Satversmē noteiktos ģimenes un sabiedrības pamatus, izveidot krīzes atbalsta mehānismu kā pastāvīgu sistēmu, nodrošināt strādājošiem vecākiem vecāku pabalstu 100% apmērā, paaugstināt atbalstu ģimenēm ar vienu apgādnieku un sociālo pakalpojumu pieejamību visā Latvijā. Demogrāfijas veicināšanai sola bērna piedzimšanas pabalstu 2000 €, paplašināt medicīniskās apaugļošanas pieejamību, īstenot reģionu mājokļu programmu jaunajām un daudzbērnu ģimenēm, atbalstīt hipotekāro maksājumu sloga mazināšanu, kā arī atbalstīt jauniešu pirmo darba vietu un mājokli.

### NA — TĒMA

- claim_id 532705 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts saīsināt tiesvedības procesus.
- claim_id 532719 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts palielināt bērna kopšanas pabalstu līdz 600 EUR ar ikgadēju indeksāciju, celt ģimenes valsts pabalstu (100 EUR par vienu, 300 EUR par diviem, 600 EUR par trim un vairāk bērniem), nodrošināt ģimenes ienākumu saglabāšanu bērna pirmajos 18 mēnešos, ieviest programmu "Silta maltīte katram bērnam", dzēst studiju kredītus par bērniem, atvieglot pirmā mājokļa iegādi (15 000 EUR valsts grants par katru bērnu, valsts garantēts kredīts bez pirmās iemaksas jaunajām ģimenēm), atbalstīt tēvu iesaisti bērnu audzināšanā, personu ar invaliditāti nodarbinātību un vides pieejamību, kā arī veidot remigrācijas un diasporas atgriešanās atbalsta sistēmu.

### LPV — PIEMIN

- claim_id 532652 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts ieviest 5000 eiro pabalstu par katru jaundzimušo, saglabāt Goda ģimenes statusu uz mūžu vecākiem ar trīs vai vairāk bērniem, iekļaut bērna kopšanas atvaļinājumu darba stāžā, nodrošināt 100% valsts apmaksātu neauglības ārstēšanu, palielināt atbalstu ģimenēm ar bērniem ar īpašām vajadzībām un palīdzēt ģimenēm iegūt mājokli caur pastāvīgo uzturēšanās atļauju programmas ziedojumiem; denonsēt Stambulas konvenciju un Satversmē nostiprināt dabiskas ģimenes definīciju, kurā tēvs ir vīrietis un māte — sieviete.
  
  **Citāts:** „Ieviesīsim 5000 eiro pabalstu par katru jaundzimušo bērnu.”

### AS — PIEMIN (citā tēmā)

- claim_id 532838 · Vide · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Dabas politikā aizsargās mežus, ūdeņus, augsni un bioloģisko daudzveidību, nepieļaujot birokrātisku aizliegumu politiku bez kompensācijām un saimnieciska līdzsvara.
  
  **Citāts:** „Dabas politikā aizsargāsim mežus, ūdeņus, augsni un bioloģisko daudzveidību, nepieļaujot birokrātisku aizliegumu politiku bez kompensācijām un saimnieciska līdzsvara.”

### MMN — TĒMA

- claim_id 532776 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Atbalstīt ģimenes un demogrāfiju ar nodokļu instrumentiem: palielināt iedzīvotāju ienākuma nodokļa atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī un noteikt 0% PVN likmi pirmā mājokļa iegādei jaunos projektos.
  
  **Citāts:** „palielināsim IIN atvieglojumu par katru apgādībā esošu bērnu līdz 500 EUR mēnesī”
- claim_id 532782 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Nodrošināt privātīpašuma neaizskaramību ar tiesībām to bez ierobežojumiem izmantot saimniekošanai; izstrādāt jaunu Krimināllikumu un Kriminālprocesa likumu, lai mazinātu sīko lietu slogu sistēmai; aizsargāt vārda brīvību, izbeidzot cenzūru un mēģinājumus ar likumiem vai sociālu spiedienu kontrolēt iedzīvotāju runu.
  
  **Citāts:** „izstrādāsim jaunu Krimināllikumu un Kriminālprocesa likumu”

### LA — TĒMA

- claim_id 547873 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot ilgtermiņa ģimeņu politiku, kas uzlabo mājokļu pieejamību, nodrošina kvalitatīvu pirmsskolas un skolas izglītību un palīdz savienot darbu ar ģimenes dzīvi. Sola rūpēties par senioriem, nodrošinot labu dzīves kvalitāti vecumdienās ar prognozējamu un augošu sociālo atbalstu un veselības aprūpi.
- claim_id 547878 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola aizstāvēt ikviena cilvēka pamattiesības, vienlīdzību likuma priekšā un neatkarīgas demokrātiskas institūcijas, izvirzot tiesiskumu un demokrātiju par valsts pamatvērtībām.

### ST — TĒMA

- claim_id 532592 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts pārskatīt krimināllietas, kurās saskatāmas politiskas vajāšanas pazīmes, nodrošinot taisnīgu izvērtēšanu un reabilitējot nepamatoti cietušās personas.
- claim_id 532596 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts izstrādāt visaptverošu dzimstības veicināšanas programmu (finansiāls atbalsts ģimenēm, mājokļu pieejamība, bērnu aprūpe), palielināt atbalstu jaunajām un daudzbērnu ģimenēm, izstrādāt jaunu remigrācijas programmu tautiešu atgriešanai, kā arī stiprināt sociālo aizsardzību pensionāriem, daudzbērnu ģimenēm un personām ar invaliditāti, nodrošinot cilvēka cienīgu dzīves līmeni.

### JKP — TĒMA

- claim_id 532797 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola uzlabot pirmstiesas izmeklēšanas sistēmu, stiprinot ekspertīžu kapacitāti un paātrinot kriminālprocesus.
  
  **Citāts:** „Uzlabosim PIRMSTIESAS IZMEKLĒŠANAS SISTĒMU”
- claim_id 532811 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola pilnveidot mājokļa pabalsta piešķiršanu, personu ar invaliditāti asistenta pakalpojumu sistēmu un uzņēmumu atbalstu jauniešu apmācībai un pārkvalifikācijai. Demogrāfijā sola veidot ģimenēm draudzīgu, dzimstību veicinošu politiku un panākt, lai Latvija no emigrācijas valsts kļūst par atgriešanās valsti. Sola arī konsekventi novērst vardarbību ģimenē un aizsargāt cietušos, kā arī reformēt bāriņtiesu sistēmu, stiprinot bērnu tiesību aizsardzību.
  
  **Citāts:** „Veidosim ĢIMENĒM DRAUDZĪGU UN DZIMSTĪBU VEICINOŠU POLITIKU”

### ASL — PIEMIN

- claim_id 532604 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts veicināt dzimstību, lai sasniegtu summāro dzimstības koeficientu vismaz 2,1: palielināt piedzimšanas pabalstu Latvijas pilsonēm 3 vidējo algu apmērā, bērna kopšanas pabalstu minimālās algas apmērā, palielināt neapliekamo minimumu par katru bērnu, nodrošināt elastīgu mājokļu atbalstu jaunajām ģimenēm, kā arī pārtraukt starptautisko un nacionālo dokumentu darbību, kas grauj ģimenes un bioloģiskā dzimuma jēdzienus.
  
  **Citāts:** „Veicināsim latviešu tautas ataudzi, lai sasniegtu summāro dzimstības koeficientu vismaz 2,1 apmērā”

### SC — PIEMIN (citā tēmā)

- claim_id 532698 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts atbalstīt bioloģisko lauksaimniecību ar mērķtiecīgām subsīdijām un mazāku birokrātiju, cīnīties par ES tiešmaksājumiem Latvijas lauksaimniekiem ES vidējā līmeņa apmērā, stiprināt lauksaimnieku kooperāciju pret starpnieku cenu varu un nodrošināt taisnīgas kompensācijas par ražošanu ierobežojošiem vides nosacījumiem.

### GS — TĒMA

- claim_id 532816 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola radikālu atbalstu daudzbērnu ģimenēm un dzimstībai: atceltu iedzīvotāju ienākuma nodokli ģimenēm ar trīs un vairāk bērniem; garantētu vismaz 5000 eiro vienreizēju pabalstu par katra bērna piedzimšanu; noteiktu ģimenes valsts pabalstu 1000 eiro mēnesī par bērnu līdz 2 gadu vecumam, 100 eiro par vienu bērnu, 300 eiro par diviem, 900 eiro par trīs un 400 eiro par katru no četriem un vairāk bērniem (no 2 gadu vecuma); ģimenēm ar 3+ bērniem pakalpojumus sniegtu ārpus kārtas. Atbalstītu seniorus ar bezmaksas sabiedrisko transportu pensionāriem visā Latvijā un personas ar invaliditāti; ieviestu automātisku atbalsta piešķiršanu bez iesniegumiem un ar likumu aizliegtu krīzes laikā atsavināt cilvēka vienīgo mājokli.
  
  **Citāts:** „atbrīvosim daudzbērnu ģimenes no iedzīvotāju ienākuma nodokļa maksāšanas”

### SV-AJ — PIEMIN

- claim_id 547972 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts ģimenes stiprināšanas likums, ģimenes valsts pabalsts 1/4 apmērā no minimālās algas par katru bērnu, atbalsts vecākam palikt ar bērnu līdz 3 gadu vecumam, dubultoti atvieglojumi viena vecāka ģimenēm, Goda ģimenes statuss uz mūžu daudzbērnu un adoptētāju ģimenēm un aktīva reemigrācijas politika; iebilst pret “ģimenes vērtības graujošu ideoloģiju”, tostarp Stambulas konvenciju.
  
  **Citāts:** „noteikt, ka ģimenes valsts pabalsts par katru bērnu ir 1/4 no minimālās algas”

_Piemin: 6 no 14._


## k18 — Latvijai jāsasniedz klimatneitralitāte ES noteiktajā termiņā, pat ja tas sadārdzina enerģiju.

Tēmas: Klimats, Vide, Degviela un enerģētika  
Kodēšanas atgādne: par = klimatneitralitāte / zaļais kurss; pret = pārskatīt / atteikties no zaļā kursa


### JV — PIEMIN

- claim_id 532679 · Vide · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts uzturēt dabas kapitālu, zinātnē balstītu mežu, jūras un ūdeņu pārvaldību, aprites ekonomiku, klimatnoturīgu infrastruktūru un taisnīgu zaļo pāreju, garantējot taisnīgas kompensācijas, kopienu līdzdalību un prognozējamus noteikumus uzņēmējiem.

### PRO — PIEMIN

- claim_id 532632 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts iestāties par klimatneitralitāti un ieviest taisnīgus dabas resursu un klimata nodokļus uzņēmumiem, kas piesārņo vidi, ieņēmumus novirzot vides atjaunošanai.

### ZZS — TĒMA

- claim_id 547885 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola veicināt cenu stabilitāti iedzīvotājiem un energoietilpīgiem uzņēmumiem, nodrošināt drošu un konkurētspējīgu energoapgādi ar vietējiem resursiem, siltumapgādes modernizāciju, tīklu attīstību, enerģijas uzkrāšanu un bāzes ģenerējošo jaudu attīstību, attīstīt biometānu no kūtsmēsliem un atlikumiem ar skaidriem ilgtspējas kritērijiem, kā arī paplašināt energoefektivitātes programmas privātmājām, daudzdzīvokļu ēkām, uzņēmumiem un transportam.
- claim_id 547896 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola saprātīgi ieviest 'zaļo vienošanos', aizsargājot iedzīvotājus un uzņēmējus no nesamērīgām izmaksām.

### NA — PIEMIN

- claim_id 532715 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts klimata un ilgtspējas politikas pasākumus īstenot, izvērtējot to ietekmi uz sociāli ekonomisko attīstību.

### LPV — PIEMIN (citā tēmā)

- claim_id 532648 · Lauksaimniecība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts panākt būtiski lielākus tiešmaksājumus lauksaimniekiem, samazināt tās 'zaļā kursa' prasības, kas ir pretrunā ar Latvijas nacionālajām interesēm un sadārdzina ražojumus, saglabāt un attīstīt kūdras ieguvi lauksaimniecībā, kā arī noteikt taisnīgas kompensācijas zemju īpašniekiem par saimnieciskās darbības ierobežojumiem.
  
  **Citāts:** „Panāksim būtiski lielākus tiešmaksājumus lauksaimniekiem.”

### AS — PIEMIN

- claim_id 532836 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Pārskatīs zaļā kursa ieviešanu, prasot, lai klimata mērķi būtu savienojami ar Latvijas konkurētspēju, enerģētisko un pārtikas drošību un dabas vērtību aizsardzību.
  
  **Citāts:** „Pārskatīsim zaļā kursa ieviešanu. Klimata mērķiem jābūt savienojamiem ar Latvijas konkurētspēju, enerģētisko un pārtikas drošību un dabas vērtību aizsardzību.”

### MMN — PIEMIN

- claim_id 532786 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** ES Zaļā kursa prasības nedrīkst vājināt Latvijas drošību, ekonomikas konkurētspēju vai pasliktināt iedzīvotāju labklājību.
  
  **Citāts:** „ES Zaļā kursa prasības nedrīkst vājināt Latvijas drošību, ekonomikas konkurētspēju vai pasliktināt iedzīvotāju labklājību”

### LA — PIEMIN

- claim_id 547876 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Uzskata, ka klimata politikai jākļūst par Latvijas konkurētspējas priekšrocību, nevis par kavēkli.

### ST — PIEMIN (citā tēmā)

- claim_id 532591 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts samazināt birokrātiju, apvienojot ministrijas (Aizsardzības ar Iekšlietu, Izglītības un zinātnes ar Kultūras, Ekonomikas ar Finanšu) un likvidējot Klimata un enerģētikas ministriju; samazināt Saeimas deputātu skaitu no 100 uz 50; četru gadu laikā samazināt valsts pārvaldes aparātu par 30%; ieviest tautas vēlētu Valsts prezidentu ar attiecīgiem grozījumiem Satversmē; stiprināt deputātu personisko atbildību, atceļot iespēju balsojumos atturēties; ieviest politisko atbildību amatpersonām; likvidēt Sabiedrības integrācijas fondu; kā arī likvidēt nepilsoņa statusu un vienkāršot pilsonības iegūšanas kārtību.

### JKP — TĒMA

- claim_id 532799 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veicināt konkurētspējīgas energoresursu cenas un enerģētisko pašpietiekamību rūpniecības attīstībai, kā arī atbalstīt tikai tādus atjaunīgās enerģijas projektus, kas rada tiešu labumu vietējām kopienām un pašvaldībām.
  
  **Citāts:** „Veicināsim KONKURĒTSPĒJĪGAS ENERGORESURSU CENAS un enerģētisko pašpietiekamību”
- claim_id 532802 · Vide · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par taisnīgu kompensāciju sistēmu zemes īpašniekiem, ja valsts vai pašvaldības dabas aizsardzības nolūkos nosaka saimnieciskās darbības ierobežojumus.
  
  **Citāts:** „Iestāsimies par taisnīgu KOMPENSĀCIJU SISTĒMU ZEMES ĪPAŠNIEKIEM”

### ASL — TĒMA

- claim_id 532616 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts atbalstīt ilgtspējīgu enerģētiku un apturēt vēja elektrostaciju projektus tuvu apdzīvotām un ainaviski vērtīgām vietām, kā arī atbalstīt modernas ģeotermālās enerģijas un kodolenerģētikas potenciāla izpēti.
  
  **Citāts:** „Atbalstīsim ilgtspējīgu enerģētiku – apturēsim VES projektus tuvu apdzīvotām un ainaviski vērtīgām vietām”

### SC — KLUSĒ?


### GS — KLUSĒ?


### SV-AJ — PIEMIN

- claim_id 547979 · Klimats · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts atteikties no “Zaļā kursa” noteikumiem, kas, pēc programmas ieskata, apgrūtina iedzīvotāju un uzņēmēju dzīvi.
  
  **Citāts:** „atteikties no “Zaļā kursa” noteikumiem, kas apgrūtina iedzīvotāju un uzņēmēju dzīvi”

_Piemin: 9 no 14._


## k19 — Jaunas vēja elektrostacijas jābūvē arī tad, ja vietējie iedzīvotāji iebilst.

Tēmas: Degviela un enerģētika  
Kodēšanas atgādne: par = vēja parku attīstība; pret = ierobežot / vietējais veto


### JV — TĒMA

- claim_id 532671 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts attīstīt pieejamu, drošu un prognozējamu enerģiju – jaunas elektroenerģijas jaudas, tīklus, uzkrāšanas risinājumus, energoefektivitāti un satiksmes un siltuma elektrifikāciju, kā arī veidot paātrinātus investīciju koridorus enerģētikā.

### PRO — PIEMIN (citā tēmā)

- claim_id 532637 · Ārpolitika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts aizstāvēt starptautiskās normās balstītu pasaules kārtību, būt aktīvai NATO austrumu flanga valstij, kas sadarbojas ar NATO, ES, NB8+, Poliju, Lielbritāniju un Ukrainu, un iesaistīt diasporu lēmumu pieņemšanā, atbalstot ikvienu, kurš vēlas atgriezties Latvijā.

### ZZS — PIEMIN (citā tēmā)

- claim_id 547889 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt stabilu atalgojuma pieaugumu kultūras nozarē, reģionu kultūras infrastruktūras (bibliotēku, kultūras namu) noturību, sakrālā un nemateriālā mantojuma saglabāšanu, profesionālās mākslas pieejamību reģionos, tostarp stiprināt GORA attīstību ar valsts līdzdalību, attīstīt 'Skolas somas' pakalpojumu, atbalstīt amatiermākslu un radošās industrijas, stiprināt latviešu valodas lomu ikdienā, kā arī veicināt kultūras izcilības eksportu un pasaules līmeņa kultūras pieejamību Latvijā.

### NA — TĒMA

- claim_id 532716 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts veicināt energoefektivitātes paaugstināšanu, paplašinot atbalstu ēku renovācijai un pārejai uz atjaunīgajiem energoresursiem, kā arī stiprināt enerģētisko drošību un neatkarību, paātrinot elektroenerģijas pārvades tīkla modernizāciju.

### LPV — PIEMIN (citā tēmā)

- claim_id 532650 · Vide · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts apturēt vēja parku nekontrolētu attīstību, nosakot, ka pašvaldībām ir tiesības apturēt vai atteikt projektus teritorijās, kur vietējie iedzīvotāji pamatoti iebilst.
  
  **Citāts:** „Apturēsim vēja parku nekontrolētu attīstību, nosakot, ka pašvaldībām ir tiesības apturēt vai atteikt projektus teritorijās, kur vietējie iedzīvotāji pamatoti iebilst.”

### AS — PIEMIN

- claim_id 532835 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Meklēs risinājumus elektrības cenas samazināšanai energoietilpīgiem uzņēmumiem, palielinās stratēģiskās gāzes un naftas produktu rezerves ar caurredzamu pārvaldību, virzīs modulāro kodolreaktoru izpēti, atjaunojamo energoresursu attīstību, enerģijas uzkrāšanas un starpsavienojumu projektus, kā arī ļaus vietējiem ražotājiem slēgt tiešos elektroenerģijas piegādes līgumus ar uzņēmumiem un kopienām.
  
  **Citāts:** „Virzīsim modulāro kodolreaktoru izpēti, atjaunojamo energoresursu attīstību ar skaidriem drošības, vides un pašvaldību līdzdalības noteikumiem.”

### MMN — TĒMA

- claim_id 532785 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Nodrošināt iespējami lētāku un drošāku elektroenerģiju, izbeidzot stratēģisko monopolu izmantošanu slēpta nodokļa iekasēšanai; izmantot dabasgāzi kā pārejas perioda enerģijas avotu ar centralizētu ilgtermiņa iepirkumu kopā ar Igauniju un Somiju; ilgtermiņā sadarboties ar kaimiņiem mazo modulāro kodolreaktoru (SMR) būvniecībā.
  
  **Citāts:** „dabasgāze kā pārejas perioda enerģijas avots; centralizēts ilgtermiņa iepirkums kopā ar Igauniju un Somiju”

### LA — TĒMA

- claim_id 547875 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola attīstīt atjaunīgās enerģijas ražošanu, modernizēt elektroenerģijas tīklus un enerģijas uzkrāšanas tehnoloģijas, uzsverot, ka enerģētiskā neatkarība ir drošības, ekonomikas un konkurētspējas jautājums.

### ST — TĒMA

- claim_id 532589 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēta neatkarīgāka enerģētikas politika: pārskatīt starptautiskās vienošanās enerģētikas jomā, iegādāties gāzi, degvielu un citus energoresursus pēc ekonomiskā izdevīguma principa, stiprināt enerģētisko drošību un nodrošināt sociāli pieejamu elektroenerģiju ģimenēm, izmantojot valsts hidroelektrostaciju potenciālu.

### JKP — TĒMA

- claim_id 532799 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veicināt konkurētspējīgas energoresursu cenas un enerģētisko pašpietiekamību rūpniecības attīstībai, kā arī atbalstīt tikai tādus atjaunīgās enerģijas projektus, kas rada tiešu labumu vietējām kopienām un pašvaldībām.
  
  **Citāts:** „Veicināsim KONKURĒTSPĒJĪGAS ENERGORESURSU CENAS un enerģētisko pašpietiekamību”

### ASL — PIEMIN

- claim_id 532616 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts atbalstīt ilgtspējīgu enerģētiku un apturēt vēja elektrostaciju projektus tuvu apdzīvotām un ainaviski vērtīgām vietām, kā arī atbalstīt modernas ģeotermālās enerģijas un kodolenerģētikas potenciāla izpēti.
  
  **Citāts:** „Atbalstīsim ilgtspējīgu enerģētiku – apturēsim VES projektus tuvu apdzīvotām un ainaviski vērtīgām vietām”

### SC — KLUSĒ?


### GS — KLUSĒ?


### SV-AJ — PIEMIN

- claim_id 547975 · Degviela un enerģētika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Enerģētikā solīts izstrādāt alternatīvu politiku, kas nav balstīta vēja un saules elektrostacijās, neatbalstīt jaunu vēja elektrostaciju būvniecību, samazināt PVN elektrībai, ūdensapgādei un kurināmajam līdz 5 %, pārskatīt degvielas cenas veidošanu un izvērtēt iespēju izstāties no Nordpool biržas, lai panāktu zemāko elektrības cenu patērētājiem.
  
  **Citāts:** „izvērtēt iespēju atteikties no dalības Nordpool biržā, lai panāktu reāli zemāko un ekonomiski pamatotāko elektrības cenu patērētājiem”

_Piemin: 6 no 14._


## k20 — Pensiju 2. līmenim jābūt brīvprātīgam, ar tiesībām uzkrājumu izņemt.

Tēmas: Pensijas, Sociālā politika  
Kodēšanas atgādne: par = brīvprātīgs / izņemt / pārcelt uz 1. līmeni; pret = saglabāt obligātu


### JV — TĒMA

- claim_id 532674 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts demogrāfijas politiku veidot kā rūpes par stiprām ģimenēm, grūtniecību, dzemdībām, bērnu veselību, neauglības ārstēšanu, vecāku psihisko veselību, tēvu iesaisti, bērnu aprūpi un darba un privātās dzīves līdzsvaru. Paredzēts nodrošināt bērnu agrīnās attīstības vajadzību noteikšanu un atbalstu (BAASIK), kā arī atbalstīt sportu kā sabiedrības veselības un bērnu attīstības daļu.

### PRO — TĒMA

- claim_id 532622 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts palielināt ģimenes valsts pabalstu, mērķtiecīgi atbalstīt ģimenes ar zemiem ienākumiem un viena vecāka ģimenes, nodrošināt sociālās iemaksas bērna kopšanas atvaļinājuma laikā, pabalstus pakāpeniski piesaistīt ienākumu mediānai un celt minimālo ienākumu sliekšņus, atbalstīt vienlīdzīgas tiesības, tostarp laulību vienlīdzību un visu ģimeņu aizsardzību, veidot pieejamu īres mājokļu fondu cilvēkiem ar zemiem un vidējiem ienākumiem un pieejamu vidi personām ar invaliditāti.
- claim_id 532623 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts paaugstināt pensijas, straujāk ieviešot piemaksu par apdrošināšanas stāžu un atzīstot dažādu nodarbinātības formu ietvaros paveikto.

### ZZS — TĒMA

- claim_id 547886 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola reformēt invaliditātes sistēmu uz funkcionēšanu balstītu novērtējumu ar lielāku atbalstu smagiem funkcionāliem traucējumiem, stiprināt Satversmē noteiktos ģimenes un sabiedrības pamatus, izveidot krīzes atbalsta mehānismu kā pastāvīgu sistēmu, nodrošināt strādājošiem vecākiem vecāku pabalstu 100% apmērā, paaugstināt atbalstu ģimenēm ar vienu apgādnieku un sociālo pakalpojumu pieejamību visā Latvijā. Demogrāfijas veicināšanai sola bērna piedzimšanas pabalstu 2000 €, paplašināt medicīniskās apaugļošanas pieejamību, īstenot reģionu mājokļu programmu jaunajām un daudzbērnu ģimenēm, atbalstīt hipotekāro maksājumu sloga mazināšanu, kā arī atbalstīt jauniešu pirmo darba vietu un mājokli.
- claim_id 547887 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt stabilu pensiju sistēmu, pabalstu pielāgošanu inflācijai un bāzes pensiju, izvirzot mērķi līdz 2030. gadam sasniegt vidējo pensiju 1000 € apmērā.

### NA — PIEMIN

- claim_id 532721 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts veicināt vecāka gadagājuma cilvēku brīvprātīgu nodarbinātību, novēršot vecuma diskrimināciju darba tirgū, nodrošināt 2. pensiju līmeņa uzkrājuma automātisku pārmantošanu ģimenē, ar nodokļu atvieglojumiem stimulēt 3. pensiju līmeņa uzkrājumus un nodrošināt aprūpes pakalpojumu pieejamību senioriem reģionos.

### LPV — PIEMIN

- claim_id 532661 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts celt pensijas, dot cilvēkiem tiesības izņemt līdzekļus no 2. pensiju līmeņa un pašiem rīkoties ar uzkrāto naudu, kā arī panākt, ka pensionēšanās vecums netiks celts.
  
  **Citāts:** „Dosim tiesības cilvēkiem izņemt līdzekļus no 2. pensiju līmeņa un pašiem rīkoties ar savu uzkrāto naudu.”

### AS — TĒMA

- claim_id 532827 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Atbalstīs jaunās un daudzbērnu ģimenes ar mājokļa grantiem, valsts garantijām un īres mājokļu programmām. Nodrošinās iespēju strādāt bērna kopšanas laikā, nezaudējot pabalstu. Mērķtiecīgi mazinās vardarbību ģimenē, stiprinot prevenciju, sociālo dienestu kapacitāti un atbalstu cietušajiem, kā arī veicinās bērnu aizsardzību, adopciju un audžuģimeņu skaita pieaugumu. Radīs labvēlīgu nodokļu režīmu reemigrantiem uz četriem gadiem.
  
  **Citāts:** „Atbalstīsim jaunās un daudzbērnu ģimenes ar mājokļa grantiem, valsts garantijām un īres mājokļu programmām.”
- claim_id 532828 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Fiskāli atbildīgi atbalstīs pensiju sistēmas sasaisti ar bērnu audzināšanu, atzīstot vecāku ieguldījumu un nesagraujot sistēmas ilgtspēju.
  
  **Citāts:** „Fiskāli atbildīgi atbalstīsim pensiju sistēmas sasaisti ar bērnu audzināšanu, atzīstot vecāku ieguldījumu un vienlaikus nesagraujot sistēmas ilgtspēju.”

### MMN — PIEMIN

- claim_id 532777 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Pensiju 2. līmeņa priekšlaicīgas izmaksas gadījumā valsts nedrīkst regulēt, kā iedzīvotājs izlieto savu uzkrājumu.
  
  **Citāts:** „priekšlaicīgas izmaksas gadījumā valsts nedrīkst regulēt iedzīvotāju uzkrājumu izlietojumu”

### LA — TĒMA

- claim_id 547873 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola veidot ilgtermiņa ģimeņu politiku, kas uzlabo mājokļu pieejamību, nodrošina kvalitatīvu pirmsskolas un skolas izglītību un palīdz savienot darbu ar ģimenes dzīvi. Sola rūpēties par senioriem, nodrošinot labu dzīves kvalitāti vecumdienās ar prognozējamu un augošu sociālo atbalstu un veselības aprūpi.

### ST — TĒMA

- claim_id 532596 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts izstrādāt visaptverošu dzimstības veicināšanas programmu (finansiāls atbalsts ģimenēm, mājokļu pieejamība, bērnu aprūpe), palielināt atbalstu jaunajām un daudzbērnu ģimenēm, izstrādāt jaunu remigrācijas programmu tautiešu atgriešanai, kā arī stiprināt sociālo aizsardzību pensionāriem, daudzbērnu ģimenēm un personām ar invaliditāti, nodrošinot cilvēka cienīgu dzīves līmeni.

### JKP — PIEMIN

- claim_id 532812 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par 2. pensiju līmeņa uzkrājumu sistēmas pilnveidošanu, paplašinot iedzīvotāju tiesības ietekmēt savu uzkrājumu pārvaldīšanu un ieguldīšanu, vienlaikus saglabājot uzkrājumu drošību un ilgtspēju.
  
  **Citāts:** „Iestāsimies par 2. PENSIJU LĪMEŅA UZKRĀJUMU sistēmas pilnveidošanu”

### ASL — PIEMIN

- claim_id 532603 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts novirzīt 2. pensiju līmeni tautsaimniecībā, uzkrājumus ieskaitot pensiju 1. līmenī un pakļaujot tos personalizētai indeksācijai, kā arī nodrošināt pensiju taisnīgumu māmiņām – bērna kopšanas laiku ieskaitīt darba stāžā un par katru bērnu piešķirt Latvijas pilsonei pensijas 1. līmeņa kapitālu 20 000 eiro apmērā.
  
  **Citāts:** „Par katru bērnu pēc tā piedzimšanas katrai Latvijas pilsonei tiek piešķirts pensijas 1. līmeņa kapitāls 20 000 eiro apmērā”

### SC — TĒMA

- claim_id 532685 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts noteikt minimālo pensiju un garantēto sociālo minimumu virs nabadzības riska sliekšņa, kā arī augstas inflācijas periodos pāriet uz biežāku pensiju un pabalstu indeksāciju.
- claim_id 532686 · Sociālā politika · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts palielināt invaliditātes pabalstus par 25 % un bērna piedzimšanas pabalstu līdz 1000 eiro, par otro bērnu palielināt valsts pabalstu piecreiz, nodrošināt bezmaksas ēdināšanu visiem skolēniem līdz 9. klasei un paplašināt bērnudārzu pieejamību bērniem līdz 3 gadu vecumam. Darba tiesību jomā solīts aizstāvēt 100 % piemaksu par virsstundām, stiprināt arodbiedrību tiesības, koplīgumu un ģenerālvienošanās sistēmu, ieviest algu caurskatāmības prasības lielajos uzņēmumos un stiprināt Valsts darba inspekciju. Mājokļu jomā solīts izveidot valsts sociālo un pieejamo īres mājokļu fondu un paplašināt daudzdzīvokļu māju renovācijas programmas.

### GS — PIEMIN

- claim_id 532762 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola padarīt 2. fondēto pensiju līmeni pilnībā brīvprātīgu, dodot strādājošajiem izvēli turpināt iemaksas, atstāt uzkrāto kapitālu esošajā plānā vai izņemt uzkrāto naudu un rīkoties ar to pašiem; pamato to ar banku un finanšu sektora lobija ierobežošanu.
  
  **Citāts:** „pārveidosim 2. fondēto pensiju līmeni par pilnībā brīvprātīgu”

### SV-AJ — PIEMIN

- claim_id 547971 · Pensijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Atbalsta pensiju sistēmas pārveidi: 20 gadu darba stāža prasības atcelšanu pensijas izmaksai, iebilst pret pensijas vecuma celšanu, minimālo pensiju pusē no minimālās algas un iespēju izņemt pensijas 2. līmeni; invaliditātes pensijas atbrīvo no iedzīvotāju ienākuma nodokļa.
  
  **Citāts:** „neatbalstīt pensijas vecuma celšanu”

_Piemin: 7 no 14._


## k21 — Sabiedriskajam medijam jāpārtrauc raidīt krievu valodā.

Tēmas: Sabiedriskie mediji, Kultūra  
Kodēšanas atgādne: par = tikai latviski; pret = saglabāt RU saturu


### JV — PIEMIN

- claim_id 532678 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot latvisku kultūrvidi, atbalstīt kultūras mantojuma saglabāšanu un pieejamību, laikmetīgo kultūru un starptautiski konkurētspējīgu kultūras un radošo industriju, kā arī ieguldīt pilsoniskas sabiedrības un demokrātijas attīstībā, atbalstot biedrības, jauniešu iniciatīvas un kvalitatīvu mediju saturu latviešu valodā.

### PRO — PIEMIN

- claim_id 532629 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts stiprināt Latvijas sabiedriskos medijus, depolitizējot to finansēšanas modeli un nodrošinot plašāku sabiedrības pārstāvniecību pārvaldībā, un nepieļaut mediju pakļaušanu politiskam spiedienam.

### ZZS — PIEMIN

- claim_id 547890 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola nodrošināt reģionālajiem medijiem garantētu finansējumu drošībai un cīņai pret dezinformāciju.

### NA — PIEMIN

- claim_id 532703 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts sabiedriskos medijus attīstīt kā neatkarīgu, politiski neitrālu un uzticamu informācijas avotu latviešu valodā, valsts atbalstu piešķirt medijiem, kas veido kvalitatīvu saturu tikai latviešu valodā, un saglabāt drukātās preses pieejamību reģionos.

### LPV — TĒMA

- claim_id 532651 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts attīstīt kino industriju, uzbūvēt multifunkcionālu akustisko koncertzāli un iekštelpu futbola stadionu, kā arī Rīgā izveidot Laikmetīgās mākslas muzeju, lai Latvija kļūtu par biznesa un kultūras centru Ziemeļeiropā, un piešķirt valsts līdzfinansējumu Latvijas dievnamu un kultūrvēsturiskā mantojuma atjaunošanai.
  
  **Citāts:** „Uzbūvēsim Rīgā Laikmetīgās mākslas muzeju, kas aktivizēs tūrisma plūsmu un nozares attīstību.”

### AS — TĒMA

- claim_id 532831 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Nodrošinās kultūras pieejamību reģionos, stabilu finansējumu amatierkolektīviem un radošo personu statusa pilnveidi. Stiprinās jauniešu pilsonisko līdzdalību un iniciatīvu finansējumu, kā arī paplašinās tautas sportu, treneru profesionālo attīstību un sporta infrastruktūras ilgtspējīgu finansēšanu.
  
  **Citāts:** „Nodrošināsim kultūras pieejamību reģionos, stabilu finansējumu amatierkolektīviem un radošo personu statusa pilnveidi.”

### MMN — PIEMIN

- claim_id 532781 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Sabiedriskajiem medijiem jāpārstāv visa Latvijas sabiedrība, nevis šauras grupu ideoloģiskās intereses; mediju finansējums jānosaka pēc reālā sabiedrības pieprasījuma un novērtējuma.
  
  **Citāts:** „tiem jāpārstāv visa Latvijas sabiedrība, nevis šauras grupu ideoloģiskās intereses”

### LA — PIEMIN (citā tēmā)

- claim_id 547868 · Aizsardzība un drošība · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola saglabāt aizsardzības finansējumu vismaz 5% apmērā no iekšzemes kopprodukta, mērķtiecīgi attīstot Latvijas aizsardzības industriju un valsts spēju ražot drošībai nepieciešamās tehnoloģijas. Sola attīstīt Nacionālos bruņotos spēkus, Zemessardzi, civilo aizsardzību un kiberdrošību, stiprināt kritiskās infrastruktūras un robežas aizsardzību un veidot modernu krīžu vadības sistēmu. Sola stiprināt sabiedrības noturību, attīstot medijpratību un cīņu pret dezinformāciju, kā arī atbalstīt vietējo uzņēmumu iesaisti militāro tehnoloģiju, dronu un kiberdrošības risinājumu izstrādē un ražošanā. Uzsver, ka Latvijas drošība balstās spēcīgā NATO, vienotā Eiropas Savienībā un ciešā sadarbībā ar Baltijas un Ziemeļvalstīm.

### ST — KLUSĒ?


### JKP — TĒMA

- claim_id 532815 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot latviskās lauku ainavas atjaunotnes valsts programmu, atbalstīt reģionu vecpilsētu un kultūrvēsturiskā, industriālā mantojuma un nacionāli nozīmīgu zīmolu saglabāšanu, iesaistīt pilsonisko sabiedrību mantojuma saglabāšanā un aizstāvēt taisnīgākus kultūras darbinieku atalgojuma principus. Sola arī izveidot taisnīgāku un caurskatāmāku sporta finansēšanas sistēmu.
  
  **Citāts:** „Aizstāvēsim TAISNĪGĀKUS UN SALĪDZINĀMUS KULTŪRAS DARBINIEKU ATALGOJUMA principus”

### ASL — PIEMIN

- claim_id 532610 · Sabiedriskie mediji · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts aizliegt Latvijas medijos strādāt Krievijas un tai draudzīgu valstu pilsoņiem un nodrošināt sabiedriskā medija apraidi visā Latgales teritorijā.
  
  **Citāts:** „Nodrošināsim sabiedriskā medija apraidi visā Latgales teritorijā”

### SC — KLUSĒ?


### GS — TĒMA

- claim_id 532764 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Iestājas par klasisku, konservatīvu sabiedrību, kuras kultūras, valodas un identitātes pamatā ir kristīgās un tradicionālās Eiropas vērtības; uzskata, ka valsts un izglītības iestādēm ir pienākums tās sargāt un nodot nākamajām paaudzēm, atsakoties no moderniem sociāliem eksperimentiem un ideoloģijām, kas šķeļ sabiedrību; kultūrai jānostiprina nacionālā pašapziņa.
  
  **Citāts:** „Mūsu kultūras, valodas un identitātes pamatā ir kristīgās un tradicionālās Eiropas vērtības”

### SV-AJ — TĒMA

- claim_id 547986 · Kultūra · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts atjaunot 5 % PVN drukātajiem izdevumiem visās valodās, nodrošināt kultūras pasākumu pieejamību visos reģionos, palielināt valsts atbalstu sportam un veicināt vēsturisko kultūras vērtību, ēku, pieminekļu un kapsētu saglabāšanu.
  
  **Citāts:** „atjaunot 5%PVN drukātajiem izdevumiem visās valodās”

_Piemin: 7 no 14._


## k22 — airBaltic jāpārdod privātiem investoriem.

Tēmas: Valsts kapitālsabiedrības, airBaltic  
Kodēšanas atgādne: par = pārdot / privatizēt; pret = saglabāt valsts kontroli


### JV — KLUSĒ?


### PRO — PIEMIN

- claim_id 532628 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts centralizēt valsts kapitālsabiedrību pārvaldību, nodrošinot to darbu sabiedrības labā un samazinot resoru politisko ietekmi.

### ZZS — KLUSĒ?


### NA — PIEMIN

- claim_id 532713 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts veicināt profesionāļu piesaisti valsts kapitālsabiedrību padomēs, ieviešot skaidrus darbības rādītājus.

### LPV — PIEMIN

- claim_id 532647 · airBaltic · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts veidot Rīgas lidostu par lielāko lidojumu centru Ziemeļeiropā un noteikt, ka 'AirBaltic' nodrošina savienojumus tikai uz/no Rīgas, aizverot zaudējumus radošās Tallinas un Viļņas bāzes, lai aviokompānija strādātu bez zaudējumiem; ar jaudīgu mārketinga kampaņu ārvalstīs divkāršot ārvalstu tūristu skaitu.
  
  **Citāts:** „“AirBaltic” nodrošinās savienojumus tikai uz/no Rīgas. Tallinas un Viļņas bāzes tiks aizvērtas, jo tās rada zaudējumus.”

### AS — PIEMIN

- claim_id 532823 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Izveidos Latvijas Attīstības fondu, kas caurredzami pārvaldītu valsts aktīvus bez politiķu iejaukšanās, lai celtu to vērtību. Valsts kapitālsabiedrību vadības atalgojumu sasaistīs ar konkrētiem rezultātiem, investīciju disciplīnu un pakalpojumu kvalitāti.
  
  **Citāts:** „Izveidosim Latvijas Attīstības fondu, kas pārvaldītu valsts aktīvus caurredzamā veidā, bez politiķu iejaukšanās, lai celtu aktīvu vērtību.”

### MMN — PIEMIN

- claim_id 532773 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Pārtraukt valsts konkurenci ar privāto sektoru un tirgus kropļošanu, samazinot valsts kapitālsabiedrību skaitu uz pusi.
  
  **Citāts:** „Kapitālsabiedrību skaitu samazināsim uz pusi”

### LA — KLUSĒ?


### ST — KLUSĒ?


### JKP — PIEMIN

- claim_id 532807 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma iestājas par labas pārvaldības principu ievērošanu valsts kapitālsabiedrībās, tostarp finanšu disciplīnu, caurskatāmību un atbildību.
  
  **Citāts:** „Iestāsimies par LABAS PĀRVALDĪBAS PRINCIPU ievērošanu valsts kapitālsabiedrībās”
- claim_id 532809 · airBaltic · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola, pamatojoties uz airBaltic darbības izvērtējumu, atbalstīt risinājumus, kas nodrošina uzņēmuma finansiālu ilgtspēju, efektīvu pārvaldību un Latvijas valsts stratēģisko interešu aizsardzību.
  
  **Citāts:** „Pamatojoties uz AIR BALTIC darbības izvērtējumu, atbalstīsim risinājumus”

### ASL — PIEMIN

- claim_id 532619 · airBaltic · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts pārtraukt jaunus valsts aizdevumus “airBaltic” un noteikt termiņu, līdz kuram uzņēmumam jākļūst pelnošam; ja tas turpinās strādāt ar zaudējumiem, izbeigt valsts līdzdalību.
  
  **Citāts:** „Pārtrauksim jaunus valsts aizdevumus “airBaltic” un noteiksim termiņu, līdz kuram uzņēmumam jākļūst pelnošam”

### SC — KLUSĒ?


### GS — KLUSĒ?


### SV-AJ — PIEMIN

- claim_id 547974 · Valsts kapitālsabiedrības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts pārveidot ALTUM par pilnvērtīgu nacionālo banku ar paplašinātām finansēšanas funkcijām, nepieļaut valsts stratēģisko uzņēmumu privatizāciju un izveidot Valsts Sociālās drošības fondu no valstij piederošo uzņēmumu dividendēm; pārskatīt Sabiedrisko pakalpojumu regulēšanas komisijas lomu, izbeidzot valsts uzņēmumu dividenžu izmantošanu kā slēptu nodokļu slogu.
  
  **Citāts:** „nepieļaut valsts stratēģisko uzņēmumu daļēju vai pilnu privatizāciju”
- claim_id 547981 · airBaltic · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts pārtraukt airBaltic finansēšanu, pārņemot pilotu akadēmijas darbību un stiprinot tās kapacitāti.
  
  **Citāts:** „pārtraukt finansēt airBaltic, pārņemt pilotu akadēmijas darbību un stiprināt tās kapacitāti”

_Piemin: 8 no 14._


## k23 — Valsts prezidents tautai jāievēl tiešās vēlēšanās.

Tēmas: Vēlēšanas, Koalīcija un partijas, Valsts pārvalde  
Kodēšanas atgādne: par = tiešas prezidenta vēlēšanas; pret = nav


### JV — TĒMA

- claim_id 532675 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts modernizēt valsts pārvaldi, mainot fokusu no procesa uz rezultātu – noteikt nozaru attīstības rādītājus, ministrus un iestāžu vadītājus vērtēt pēc rezultātiem, ieviest vienotas valdības pieeju un kopīgus pakalpojumu centrus, pāriet uz rezultātos balstītu budžeta veidošanu, kā arī samazināt administratīvo slogu, īpaši mazajiem uzņēmumiem.

### PRO — TĒMA

- claim_id 532626 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts pamatot valsts izdevumus ar skaidri noteiktām funkcijām un izmērāmiem mērķrādītājiem un ieviest regulāru birokrātijas sloga novērtējumu.

### ZZS — TĒMA

- claim_id 547892 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola mazināt birokrātiju, stiprinot 'vienas pieturas aģentūras' principu, efektivizēt likumdošanas procesu, samazināt ministriju skaitu un deleģēt funkcijas, kur tas lietderīgi, veikt valsts izdevumu un funkciju auditu, ietaupot vismaz 500 milj. € un pārvirzot tos uz veselību un reģioniem, ieviest publisko iepirkumu reformu un pieņemt datos balstītus lēmumus ar sabiedrības līdzdalību.
- claim_id 547895 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Sola pilnveidot vēlēšanu sistēmu, tostarp piesaistīt diasporas balsojumus reģioniem.

### NA — TĒMA

- claim_id 532712 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā solīts ieviest mākslīgā intelekta risinājumus valsts pārvaldē administratīvā sloga mazināšanai un pārskatīt funkciju dublēšanos starp ministrijām un pašvaldībām.

### LPV — PIEMIN

- claim_id 532659 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts veikt izmaiņas Satversmē, ļaujot Valsts prezidentu ievēlēt Latvijas tautai, un samazināt parakstu slieksni referendumu ierosināšanai no 10% līdz 5% balsstiesīgo.
  
  **Citāts:** „Veiksim izmaiņas Satversmē, ļaujot Valsts prezidentu ievēlēt Latvijas tautai.”

### AS — TĒMA

- claim_id 532839 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Ieviesīs skaidrus augstāko amatpersonu rezultātu rādītājus un rotāciju, nostiprinās personisku atbildību par lēmumiem un reformēs Civildienesta likumu. Birokrātiju samazinās pēc principa, ka katrai jaunai prasībai jāaizstāj vai jāvienkāršo esošā. Centralizēs valsts IKT pārvaldību, plaši ieviesīs mākslīgā intelekta rīkus pakalpojumu automatizācijai, vienkāršos mazos publiskos iepirkumus un nodrošinās publisku budžeta datu pieejamību līdz rēķinu līmenim.
  
  **Citāts:** „Personiskai atbildībai par pieņemtajiem lēmumiem jākļūst par valsts pārvaldes normu.”

### MMN — PIEMIN

- claim_id 532769 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Ieviest pārnesamās balss vēlēšanu sistēmu (Īrijas modeli) gan Saeimas, gan pašvaldību vēlēšanās — viens biļetens ar visiem kandidātiem, sarindojamiem vēlamības secībā; atcelt 5% barjeru partiju sarakstiem; sadalīt Latviju mazākos apgabalos ar 5–7 deputātiem; atcelt ierobežojumus deputāta amata savienošanai ar profesiju; ļaut ārzemju latviešiem balsot par jebkuru apgabalu; pazemināt referenduma ierosināšanas slieksni līdz 25 000 parakstu.
  
  **Citāts:** „ieviesīsim pārnesamās balss vēlēšanu sistēmu jeb Īrijas modeli”

### LA — KLUSĒ?


### ST — PIEMIN

- claim_id 532591 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts samazināt birokrātiju, apvienojot ministrijas (Aizsardzības ar Iekšlietu, Izglītības un zinātnes ar Kultūras, Ekonomikas ar Finanšu) un likvidējot Klimata un enerģētikas ministriju; samazināt Saeimas deputātu skaitu no 100 uz 50; četru gadu laikā samazināt valsts pārvaldes aparātu par 30%; ieviest tautas vēlētu Valsts prezidentu ar attiecīgiem grozījumiem Satversmē; stiprināt deputātu personisko atbildību, atceļot iespēju balsojumos atturēties; ieviest politisko atbildību amatpersonām; likvidēt Sabiedrības integrācijas fondu; kā arī likvidēt nepilsoņa statusu un vienkāršot pilsonības iegūšanas kārtību.

### JKP — TĒMA

- claim_id 532806 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola veidot efektīvu, profesionālu un uz rezultātu orientētu valsts pārvaldi, mazinot birokrātiju un izvērtējot valsts iestāžu funkcijas, apvienošanas iespējas un nepieciešamās strukturālās reformas.
  
  **Citāts:** „Veidosim EFEKTĪVU, profesionālu un uz rezultātu orientētu VALSTS PĀRVALDI”
- claim_id 532843 · Koalīcija un partijas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola pilnveidot partiju finansēšanas sistēmu, mazinot tās atkarību no vēlēšanu rezultātiem un lielāku nozīmi piešķirot partiju darbībai un sabiedrības iesaistei.
  
  **Citāts:** „Rosināsim pilnveidot PARTIJU FINANSĒŠANAS SISTĒMU, mazinot tās atkarību no vēlēšanu rezultātiem”

### ASL — TĒMA

- claim_id 532601 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts samazināt valsts pārvaldes aparātu un birokrātiju – iesaldēt administratīvo līdzekļu daļu, apvienot un likvidēt liekās ministrijas, atcelt valsts kapitālsabiedrību padomes, kā arī ļaut iestādēm pārnest daļu budžeta uz nākamo gadu, lai mazinātu nesaprātīgus tēriņus gada nogalē.
  
  **Citāts:** „Samazināsim valsts pārvaldes aparātu un birokrātiju – iesaldēsim administratīvo līdzekļu daļu valsts pārvaldē, apvienosim un likvidēsim liekās ministrijas, atcelsim valsts kapitālsabiedrību padomes”

### SC — PIEMIN

- claim_id 532695 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts ieviest mažoritāro vēlēšanu sistēmu un deputātu atsaukšanas mehānismu, rosināt tiešas, vispārējās Valsts Prezidenta vēlēšanas, vienkāršot tautas nobalsošanas procedūras un ieviest drošu e-vēlēšanu pilotmodeli.

### GS — PIEMIN

- claim_id 532768 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola samazināt valsts aparātu un stiprināt tiešo demokrātiju: panāktu Satversmes grozījumus, lai Valsts prezidentu vēlētu visa tauta; samazinātu referenduma ierosināšanas slieksni līdz 50 000 parakstu un ieviestu e-referendumus; veiktu valsts pārvaldes reorganizāciju un normatīvo aktu vienkāršošanu; noteiktu, ka iestādes vispirms konsultē, nevis soda (aizliedzot soda naudas kā darbības kritēriju), un pārveidotu VID par palīgu, nevis represīvu instrumentu; ieviestu pilnīgu elektronisko dokumentu apriti, aizliedzot pieprasīt datus, kas jau ir valsts datubāzēs.
  
  **Citāts:** „samazināsim valsts aparātu un dosim tautai tiesības lemt par savu likteni”

### SV-AJ — PIEMIN

- claim_id 547990 · Valsts pārvalde · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts veikt valsts pārvaldes funkcionālo auditu, apvienot atsevišķas ministrijas un samazināt ierēdņu skaitu, ieviest tautas vēlētu prezidentu un likvidēt bijušo prezidentu privilēģijas, centralizēt iepirkumus un apvienot NMPD un VUGD.
  
  **Citāts:** „veikt valsts pārvaldes funkcionālo auditu, pārskatot iestāžu funkcijas un apvienojot atsevišķas ministrijas, samazināt ierēdņu skaitu”
- claim_id 547991 · Vēlēšanas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts ieviest jaukto vēlēšanu sistēmu, samazināt Saeimas deputātu skaitu līdz 50, ierobežot deputātu kompensācijas, samazināt referendumu rīkošanai nepieciešamo balsu skaitu līdz 5 % un paplašināt sabiedrības iespējas apturēt vai atcelt valsts un pašvaldību lēmumus.
  
  **Citāts:** „samazināt Saeimas deputātu skaitu līdz 50, ierobežot deputātu kompensācijas un nodrošināt Valsts kontroles revīziju Saeimas budžetam”

_Piemin: 6 no 14._


## k24 — Par korupciju notiesātām personām uz mūžu jāaizliedz ieņemt valsts amatus.

Tēmas: Korupcija un KNAB, Tieslietas  
Kodēšanas atgādne: par = mūža aizliegums / stingrāki sodi; pret = nav


### JV — PIEMIN

- claim_id 532684 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts stiprināt korupcijas apkarošanu un publisko iepirkumu caurskatāmību.

### PRO — TĒMA

- claim_id 532627 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts padarīt publiskos iepirkumus atklātus, ilgtspējīgus un balstītus kvalitātē, nevis zemākajā cenā.
- claim_id 532630 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts nodrošināt tiesu varas institucionālu un finansiālu neatkarību no izpildvaras budžeta veidošanā un turpināt pilnveidot regulējumu naida runas novēršanai.

### ZZS — KLUSĒ?


### NA — PIEMIN

- claim_id 532722 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts padarīt publisko iepirkumu datus atklātākus un ar mākslīgā intelekta rīku analīzi novērst sadārdzinājumus un korupciju.

### LPV — PIEMIN

- claim_id 532656 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts uzsākt reālu cīņu ar korupciju, it īpaši jomās, kas saistītas ar valsts iepirkumiem un valsts uzņēmumiem.
  
  **Citāts:** „Uzsāksim reālu cīņu ar korupciju – it īpaši jomās, kas saistītas ar valsts iepirkumiem un valsts uzņēmumiem.”

### AS — KLUSĒ?


### MMN — PIEMIN

- claim_id 532791 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Apvienot KNAB, VDD un IDB vienā politiski neatkarīgā un efektīvā struktūrā.
  
  **Citāts:** „apvienosim KNAB, VDD un IDB politiski neatkarīgā un efektīvā struktūrā”

### LA — TĒMA

- claim_id 547878 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola aizstāvēt ikviena cilvēka pamattiesības, vienlīdzību likuma priekšā un neatkarīgas demokrātiskas institūcijas, izvirzot tiesiskumu un demokrātiju par valsts pamatvērtībām.

### ST — TĒMA

- claim_id 532592 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā paredzēts pārskatīt krimināllietas, kurās saskatāmas politiskas vajāšanas pazīmes, nodrošinot taisnīgu izvērtēšanu un reabilitējot nepamatoti cietušās personas.

### JKP — PIEMIN

- claim_id 532808 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stiprināt korupcijas gadījumu izmeklēšanu un kriminālvajāšanu, nodrošinot stingrāku atbildību par publisko līdzekļu izšķērdēšanu, prettiesiskiem labumiem un slēptu ietekmēšanu.
  
  **Citāts:** „Stiprināsim KORUPCIJAS GADĪJUMU IZMEKLĒŠANU un kriminālvajāšanu”

### ASL — PIEMIN

- claim_id 532608 · Tieslietas · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts noteikt stingrākus sodus par vardarbīgiem un pret valsti vērstiem noziegumiem, paaugstināt amatpersonu atbildību un pagarināt noilguma termiņus par ekonomiskajiem nodarījumiem pret valsti.
  
  **Citāts:** „Noteiksim stingrākus sodus par vardarbīgiem noziegumiem, pret valsti vērstiem noziegumiem, paaugstināsim amatpersonu atbildību un pagarināsim noilguma termiņus par ekonomiskajiem nodarījumiem pret valsti”
- claim_id 532609 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā paredzēts izveidot nacionālā pretkorupcijas prokurora amatu ar neatkarīgām pilnvarām izmeklēt korupciju visos līmeņos.
  
  **Citāts:** „Izveidosim nacionālā pretkorupcijas prokurora amatu ar neatkarīgām pilnvarām izmeklēt korupciju visos līmeņos”

### SC — KLUSĒ?


### GS — KLUSĒ?


### SV-AJ — PIEMIN

- claim_id 547992 · Korupcija un KNAB · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Solīts stiprināt KNAB sadarbību ar publisko iestāžu valsts un pašvaldību audita un revīzijas struktūrvienībām.
  
  **Citāts:** „stiprināt KNAB sadarbību ar publisko iestāžu valsts un pašvaldību audita un revīzijas struktūrvienībām”

_Piemin: 7 no 14._


## k25 — Nekustamā īpašuma nodoklis vienīgajam mājoklim jāatceļ.

Tēmas: Budžets un finanses, Pašvaldības  
Kodēšanas atgādne: par = atcelt NĪN vienīgajam mājoklim; pret = saglabāt / stiprināt NĪN


### JV — PIEMIN

- claim_id 532670 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jauna-vienotiba)  
  **Pozīcija:** Programmā solīts veidot fiskāli atbildīgu budžetu ar valsts ārējā parāda līmeni zem 55% no IKP, ievērojot eirozonas fiskālos noteikumus. Paredzēts celt minimālo algu līdz 50% no vidējās bruto darba samaksas, palielināt fiksēto neapliekamo minimumu līdz 80% no minimālās algas, padarīt nekustamā īpašuma nodokli par pilnvērtīgu pašvaldību nodokli, attīstīt kapitāla tirgu un valsts attīstības fondu. Ekonomikā izvirzīts mērķis panākt vismaz 3,5% IKP izaugsmi gadā un investīcijas virs 30% no IKP, pārejot uz augstas pievienotās vērtības ekonomiku.

### PRO — TĒMA

- claim_id 532620 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts ieviest plašāku nodokļu progresivitāti, samazinot nodokļus mazajām un vidējām algām un palielinot neapliekamo minimumu, minimālo algu piesaistīt vidējai algai, pāriet no minimālās sociālo iemaksu bāzes uz proporcionālām iemaksām, vienkāršot nodokļu nomaksu maziem un vidējiem uzņēmumiem, kā arī veidot mērķtiecīgas valsts atbalsta programmas augstas pievienotās vērtības un eksporta uzņēmumiem un jaunuzņēmumu atbalsta programmu tehnoloģiju komandām.
- claim_id 532640 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/progresivie)  
  **Pozīcija:** Programmā solīts veidot taisnīgu un stabilu pašvaldību finanšu izlīdzināšanas modeli, paplašināt mobilitātes atbalstu Latgalē, izmantot EastInvest fondu Latgales pašvaldību sabiedriskā transporta infrastruktūrai, nodrošināt transporta kompensācijas ģimenēm pierobežā un stiprināt iedzīvotāju līdzdalību pašvaldību lēmumu pieņemšanā.

### ZZS — PIEMIN

- claim_id 547879 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/zalo-un-zemnieku-savieniba)  
  **Pozīcija:** Izvirza mērķi līdz 2030. gadam panākt IKP izaugsmi vismaz par 2% virs ES vidējā, ikgadējās ārvalstu investīcijas vismaz 1 mljrd. € apmērā un IKP pieaugumu +3,8 mljrd. € gadā, minimālo algu 1250 € un vidējo algu 2500 €. Sola vienkāršāku nodokļu sistēmu mazajam biznesam, nodokļu atlaides ieguldījumiem ražīguma, efektivitātes un digitalizācijas celšanai, Latvijas kreditēšanas un investīciju fonda un krājaizdevu sabiedrību attīstību, eksporta veicināšanu un klasterus, kā arī darba ražīguma pieaugumu vismaz 5% gadā. Dzīves dārdzības mazināšanai sola samazinātu PVN (5% pirmās nepieciešamības pārtikai, 12% sabiedriskajai ēdināšanai un izmitināšanas pakalpojumiem), 0% nekustamā īpašuma nodokli primārajam mājoklim, attaisnoto izdevumu slieksni 1800 €, mazumtirdzniecības uzraudzības un 'pārtikas groza' iniciatīvas pilnveidi un sabiedrisko pakalpojumu cenu auditu.

### NA — TĒMA

- claim_id 532709 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts nodrošināt uzņēmējiem prognozējamu un konkurētspējīgu nodokļu politiku, ieviest atvieglotu nodokļu režīmu mazajiem un vidējiem uzņēmumiem, ES fondus koncentrēt aizsardzībā un augošos ekonomikas sektoros, veicināt valsts budžeta izdevumu caurspīdību, atbalstīt eksportspējīgus uzņēmumus, jaunuzņēmumus, zinātni un inovācijas un palielināt Latvijā ražoto preču īpatsvaru valsts iepirkumos. Mērķis — IKP uz vienu iedzīvotāju sasniedz 80% no ES vidējā līdz 2030. gadam.
- claim_id 532711 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/nacionala-apvieniba-visu-latvijai-tevzemei-un-brivibailnnk)  
  **Pozīcija:** Programmā paredzēts saglabāt lauku kopienu pakalpojumus (pasta punkti, ģimenes ārsti, mazās skolas, bibliotēkas), stiprināt kopienu lomu vietējo lēmumu pieņemšanā, nodrošināt platjoslas interneta pārklājumu visā valstī un izveidot reģionālo būvniecības programmu energoefektīviem īres mājokļiem ar izpirkuma tiesībām.

### LPV — PIEMIN

- claim_id 532642 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvija-pirmaja-vieta)  
  **Pozīcija:** Programmā solīts noteikt 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli un 10% kapitāla pieauguma nodokli, samazināt PVN līdz 10% apkurei, plašākam pārtikas klāstam, bērnu precēm, tūrismam un ēdināšanai, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim, atbrīvot māti no IIN, ja ģimenē aug vismaz divi bērni, palielināt neapliekamo minimumu līdz minimālās algas apmēram, atcelt nodokļus jauniešu algām pirmajā darba gadā un samazināt darbaspēka nodokļus līdz Eiropas vidējam līmenim; izveidot Nacionālo attīstības banku uz ALTUM bāzes un veidot Latviju par fintech, IT un mākslīgā intelekta centru.
  
  **Citāts:** „Samazināsim nodokļus, nosakot: 10% nodokļu likmi pašnodarbinātajiem, 10% uzņēmuma ienākuma nodokli (UIN), 10% kapitāla pieauguma nodokli.”

### AS — TĒMA

- claim_id 532822 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Sasniegs bezdeficīta bāzes budžetu četru gadu laikā. Stabilizēs nodokļu politiku, pārtraucot tās regulāru pārskatīšanu; ieviesīs mikrouzņēmumu nodokļa 10% likmi fiziskajām personām, samazinās kapitāla pieauguma IIN līdz 17% un saglabās UIN režīmu (peļņu apliekot tikai tad, kad to sadala dividendēs). Samazinās nodokļu maksātāju administratīvo slogu un mazinās ēnu ekonomiku ar motivāciju strādāt legāli, ne sodīšanu. Izveidos valsts garantiju programmu mājokļu būvniecībai reģionos, palielinot kreditēšanu par 2 miljardiem, koncentrēs valsts atbalstu augstas pievienotās vērtības nozarēs, samazinās valsts tiešo iejaukšanos ekonomikā un sekmēs publiskās un privātās partnerības projektus.
  
  **Citāts:** „Mūsu prioritāte ir ieviest kārtību valsts finansēs, lai sasniegtu bezdeficīta bāzes budžetu četru gadu laikā.”
- claim_id 532832 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/apvienotais-saraksts---latvijas-zala-partija-latvijas-regionu-apvieniba-liepajas-partija)  
  **Pozīcija:** Izveidos vienotu valsts un pašvaldību pakalpojumu plānošanas modeli (izglītība, civilā aizsardzība, sabiedriskais transports, atkritumu apsaimniekošana u.c.) un taisnīgāku pašvaldību finanšu modeli, kas motivētu radīt darba vietas, piesaistīt investīcijas un palielināt pašu ieņēmumus.
  
  **Citāts:** „Izveidosim taisnīgāku pašvaldību finanšu modeli, kas motivēs radīt darba vietas, piesaistīt investīcijas un palielināt pašu ieņēmumus.”

### MMN — PIEMIN

- claim_id 532772 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/mes-mainam-noteikumus)  
  **Pozīcija:** Ieviest nulles budžetu (katra pozīcija jāpamato no jauna) un sasniegt bezdeficīta budžetu viena Saeimas sasaukuma laikā; noteikt fiksētu 10% mikrouzņēmuma nodokli apgrozījumam līdz 50 000 EUR gadā; mazināt ēnu ekonomiku bez represijām, ieviešot saistību amnestiju; atcelt nekustamā īpašuma nodokli vienīgajam mājoklim; ieviest vienotu iedzīvotāju ienākuma nodokļa likmi.
  
  **Citāts:** „fiksēts 10% mikrouzņēmuma nodoklis apgrozījumam līdz 50 000 EUR gadā”

### LA — TĒMA

- claim_id 547870 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola līdz 2030. gadam panākt sabalansētu valsts budžetu, vienlaikus saglabājot spēju ieguldīt drošībā, izglītībā, veselības aprūpē, sociālajā nodrošinājumā un zinātnē. Sola veidot stabilu, prognozējamu un uz izaugsmi orientētu uzņēmējdarbības vidi, samazināt birokrātiju, uzlabot regulējuma kvalitāti un attīstīt kapitāla tirgu. Sola atbalstīt mākslīgo intelektu, biomedicīnu, aizsardzības industriju, zaļās tehnoloģijas un zinātņietilpīgu ražošanu un panākt, ka ieguldījumi pētniecībā un attīstībā līdz 2030. gadam sasniedz vismaz 2% no iekšzemes kopprodukta. Izvirza mērķi ekonomikai augt straujāk nekā Eiropas Savienībā vidēji.
- claim_id 547874 · Pašvaldības · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/latvijas-attistibai)  
  **Pozīcija:** Sola attīstīt reģionu ekonomiku, transporta un digitālo infrastruktūru, stiprināt pašvaldību kapacitāti un veicināt investīciju piesaisti ārpus Rīgas, lai dzīves kvalitāti nenoteiktu dzīvesvieta.

### ST — PIEMIN

- claim_id 532590 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politiska-partija-stabilitatei)  
  **Pozīcija:** Programmā solīts veidot bezdeficīta valsts budžetu bez kredītiem un aizņēmumiem, ieviest nulles budžeta principu, veikt valsts parāda restrukturizācijas izvērtējumu, samazināt PVN pamatpārtikas produktiem līdz 12% un recepšu medikamentiem līdz 5%, atcelt nekustamā īpašuma nodokli vienīgajam mājoklim un budžeta līdzekļus prioritāri novirzīt Latvijas iedzīvotāju vajadzībām.

### JKP — PIEMIN

- claim_id 532798 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/jkp-jauna-konservativa-partija)  
  **Pozīcija:** Programma sola stabilu un konkurētspējīgu nodokļu politiku bez haotiskām izmaiņām: atcelt kapitāla pieauguma nodokli mantotam īpašumam un privātpersonu nekustamā īpašuma atsavināšanai, kā arī atcelt nekustamā īpašuma nodokli mājokļiem. Ekonomikā sola veicināt investīcijas un eksportspēju augstas pievienotās vērtības nozarēs, atbalstīt mazo uzņēmējdarbību, mazināt administratīvo slogu un nodrošināt pieejamāku kreditēšanu reģionos. Iestājas pret legālas skaidras naudas aprites ierobežošanu.
  
  **Citāts:** „Veidosim STABILU UN KONKURĒTSPĒJĪGU NODOKĻU POLITIKU”

### ASL — PIEMIN

- claim_id 532600 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/austosa-saule-latvijai)  
  **Pozīcija:** Programmā solīts astoņos gados dubultot Latvijas ekonomiku, palielināt IIN neapliekamo minimumu vidējās algas apmērā (norādīts 1900 eiro mēnesī), samazināt sociālo iemaksu darba ņēmēja daļu par 6 %, atcelt nekustamā īpašuma nodokli vienīgajam ģimenes mājoklim un radīt modernu ekosistēmu zinātnes komercializācijai un efektīviem iepirkumiem.
  
  **Citāts:** „Dubultosim Latvijas ekonomiku 8 gados”

### SC — PIEMIN

- claim_id 532691 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/politisko-partiju-apvieniba-saskanas-centrs)  
  **Pozīcija:** Programmā solīts dibināt Latvijas Valsts attīstības banku valsts investīciju politikas nodrošināšanai, pastiprināt nodokļu progresivitāti, pārceļot slogu no zemiem un vidējiem ienākumiem uz lieliem, ieviest bagātības nodokli (ienākumiem virs 50 tūkst. eiro gadā vai mantai virs 1 milj. eiro) un luksusa un neizmantotā nekustamā īpašuma nodokli. Solīts arī ieviest pārtikas cenu ķēdes caurskatāmību un pārmērīgas peļņas ierobežošanu pamatprecēm, izskaust plēsonīgo ātro kredītu praksi ar izmaksu griestiem un veikt valsts pārvaldes funkciju un iepirkumu auditu.

### GS — PIEMIN

- claim_id 532817 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/gobzema-saraksts)  
  **Pozīcija:** Sola plašu nodokļu samazināšanu: pārtikas produktiem un elektrībai un gāzei PVN 12 %, visiem medikamentiem PVN 5 %; pilnībā atceltu nekustamā īpašuma nodokli mājsaimniecībām par vienīgo mājokli; samazinātu kapitāla pieauguma un uzņēmumu ienākuma (peļņas sadales) nodokli līdz 15 %, veidojot Latviju par reģiona konkurētspējīgāko nodokļu un investīciju centru; jauniem uzņēmumiem piešķirtu 270 dienu atliktas nodokļu brīvdienas; pašnodarbinātajiem, mazajiem saimniekiem un amatniekiem ieviestu vienotu, fiksētu nodokli; pārveidotu Altum par Valsts Investīciju banku pašmāju ražošanas un eksporta finansēšanai.
  
  **Citāts:** „samazināsim kapitāla pieauguma nodokli un uzņēmumu peļņas sadales nodokli (UIN) līdz 15%”

### SV-AJ — PIEMIN

- claim_id 547973 · Budžets un finanses · [CVK](https://dati.cvk.lv/SV2026/kandidatu-saraksti/suverena-vara--apvieniba-jaunlatviesi/)  
  **Pozīcija:** Nodokļu politikā solīts vismaz 5 gadu moratorijs nodokļu paaugstināšanai un jaunu nodokļu ieviešanai, nekustamā īpašuma nodokļa atcelšana visiem mājokļiem, PVN samazināšana pārtikai un sabiedriskajai ēdināšanai līdz 5 %, iedzīvotāju ienākuma nodokļa atcelšana jauniešiem līdz 25 gadu vecumam un uzņēmējiem labvēlīgāka nodokļu sistēma; solīts atgriezt Latvijas zelta krājumus glabāšanā Latvijas Bankā.
  
  **Citāts:** „ieviest vismaz 5 gadu moratoriju nodokļu paaugstināšanai un jaunu nodokļu ieviešanai”

_Piemin: 10 no 14._
