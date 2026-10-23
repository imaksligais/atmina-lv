# AS — 3. līmenis, Andris Kulbergs (id 10), meklēts 2026-09-17

Saucējs: DB dokumenti izlasīti 92 (subject 67, mentioned/mention_target 25) — no tiem 11 nolasīti pilnā `content` apjomā, pārējie 81 kā atslēgvārda konteksta logi (±300…600 zīmes ap trāpījumu); tīmekļa lapas 7 (9 WebFetch izsaukumi, divas lapas atvērtas divreiz); WebSearch vaicājumi 12.

Kā šie 92 atlasīti — saucēji, kas tos ražoja (visi vaicājumi `mode=ro`):

- Korpuss: `documents` × `document_politicians` ar `politician_id=10`, `COALESCE(published_at, scraped_at) >= '2026-01-01'` — **1210** dokumenti ar `role='subject'` (616 web, 350 twitter, 219 vestnesis, 25 x_mention) un **3646** ar `role IN ('subject','mentioned')`.
- Pirmais sijājums: `claims` ar `opponent_id=10`, `claim_type='position'`, `stated_at >= '2026-01-01'` — **564** pozīcijas; ar brīfa astoņu tēmu atslēgvārdiem tajās palika 77 / 5 / 0 / 16 / 142 / 1 / 3 / 10 (q02…q12).
- Otrais sijājums: SQL `LIKE` pa `documents.content` visā korpusā (3305 dokumenti bez `vestnesis`) ar regulārām izteiksmēm katrai tēmai plus attiecinājuma filtrs (vai nu paša X konts `source_url LIKE '%AndrisKulbergs%'`, vai vārds „Kulberg“ / „premjer“ trāpījuma logā). Rezultāti: q06 — 0 logi, q07 — 1, q09 — 15, q10 — 5, q12 — 18, q02 — 38 logi 20 dokumentos.
- Šis ir atlases saucējs, ne pierādījums: nulle logu pie q06 nozīmē, ka Kulbergs par NĪN savā 2026. gada korpusā nav runājis, nevis ka viņš to neuzskata par svarīgu.

Brīfā ir astoņas šūnas: q02, q05, q06, q07, q08, q09, q10, q12. Zemāk katra atsevišķi.

## q02

- ieteikums: par
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: 2026-08-22
- url: https://x.com/AndrisKulbergs/status/2091047167054000557
- document_id: 92475
- citats: "No 2027. gada Latvija aizsardzībai tērēs vismaz 5% no IKP."
- kāpēc: Citāts nosauc tieši to slieksni, ko apgalvojums prasa — vismaz 5 % no IKP —, un Kulbergs to pauž kā savas valdības politiku, nevis kā svešu priekšlikumu vai aprakstu par kādu citu. Pēc brīfa `piekrit_nozime` („par = 5 % vai vairāk“) tas nolasās tieši. CVK programmai pretrunas nav: programma aizsardzības budžeta IKP daļu vispār nenosauc, tāpēc izteikums to nepārraksta, bet aizpilda klusumu.
- rezerves:
  1. 2026-06-19, doc 56773, https://x.com/AndrisKulbergs/status/2068060534692319619 — "Latvija tērē 5% no iKP aizsardzībai, kur būtiski aizņemamies, un ar to nepietiek, lai būtu droši." (verbatim, ar oriģinālo rakstību „iKP“; vēl skaidrāk lasāms kā „vismaz“, jo saka, ka ar 5 % nepietiek).
  2. 2026-09-11, doc 106711, https://tv3.lv/zinas/latvija/drosibas-finansesana-uz-parada-nevar-but-ilgtermina-strategija-uzsver-kulbergs/ — "Arī citām Eiropas valstīm būtu jāseko šim piemēram. Ja mēs to spējam, tad to spēj arī citas Eiropas valstis. Mēs ieguldām drošībā, lai būtu gatavi sliktākajam scenārijam un no tā izvairītos," (šis ir jaunākais datums, bet skaitli „5 %“ satur tikai žurnālista pārstāsts blakus rindkopā, tāpēc pats citāts ir vājāks par galveno kandidātu).

## q05

- ieteikums: pret
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: 2026-06-10
- url: https://x.com/AndrisKulbergs/status/2064782973275156742
- document_id: 51779
- citats: "Galvenā prioritāte, ko pilnībā atbalstu, ir latviešu valodas nostiprināšana mediju telpā un Satversmes tiesas sprieduma ieviešana.
  Likumdevējam ir vienīgās tiesības noteikt, kā lietojama valsts valoda. Pārējos viedokļus varam uzklausīt, bet gala lēmums ir Saeimas rokās."
- kāpēc: Satversmes tiesas spriedums, kura ieviešanu Kulbergs „pilnībā atbalsta“, attiecas uz krievu valodas lietojumu sabiedriskajā medijā — tātad tieši uz mazākumtautību valodas vietu sabiedriskajā dzīvē; kopā ar tēzi, ka valsts valodas lietojumu nosaka vienīgi likumdevējs, tas nolasās pēc brīfa `pret` nozīmes („tikai valsts valodā, stiprināt latviešu valodas prasības“). Robeža, kas operatoram jāzina: izteikums sedz mediju telpu, ne skolas, tāpēc apgalvojuma izglītības daļu tas neaiztiek. CVK piezīmei pretrunas nav — programma mazākumtautību valodas nemin.
- rezerves:
  1. 2026-07-22, doc 72116, https://x.com/AndrisKulbergs/status/2079786011836502384 — "Lēmums beidzot apvienot apmācības no Labklājības Ministrijas @reinisuzulnieks  un Izglītības ministrijas @IIndriksone  pāraudzības zem viena atbildīgā – tās pārnest uz Izglītības Ministriju" (latviešu valodas apmācību centralizēšana; tēmai tuvu, bet mazākumtautību valodu jautājumu neadresē).
  2. nav — 2026-08-21 Saeimas runa (doc 91870) latviešu valodu min tikai kā valsts aizsargātu vērtību vispār, bez politikas nostājas.

## q06

- ieteikums: nav atrasts
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: —
- url: —
- document_id: —
- citats: —
- kāpēc: Nekustamā īpašuma nodoklis Kulberga 2026. gada korpusā neparādās nevienā izteikumā: regulārās izteiksmes `nekustamā īpašuma nodok` / `NĪN` / `vienīgajam mājokl` pa visiem 3305 ne-`vestnesis` dokumentiem deva **0** logu ar viņa attiecinājumu, un viņa paša X kontā vienīgais „mājokl-“ trāpījums ir par modulāro māju eksportu uz Austrāliju (doc 78136). Slazds, ko te viegli pārrakstīt kā ieteikumu: doc 55436 (nra.lv, 2026-06-17) satur teikumu "mēs kā politiskā partija uzstājam, ka vienīgajam mājoklim nevajadzētu piemērot nekustamā īpašuma nodokli" — to saka **Harijs Rokpelnis (ZZS)**, ne Kulbergs; tajā pašā rakstā AS frakcijas vadītājs Juris Viļums par NĪN saka tikai "es nezinu, vai to var paaugstināt". Abi neder pēc noteikuma nr. 3 (runātājs = līderis pats). Tīmeklī (divi WebSearch vaicājumi) Kulberga izteikums par NĪN neatradās. Sakrīt ar CVK piezīmi: programma NĪN nemin.
- rezerves: nav

## q07

- ieteikums: klusē
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: 2026-06-15
- url: https://www.lsm.lv/raksts/zinas/latvija/15.06.2026-man-ir-ideja-saruna-ar-premjeru-par-planiem-un-prioritatem.a651307/
- document_id: 54702 — **DB glabā tikai anotāciju** (647 zīmes, 83 vārdi), citāts ir tā paša URL pilnajā lapā; re-ingest kandidāts
- citats: "Šobrīd mēs dauzām teicamniekus, atņemam viņiem naudu un dodam to neteicamniekiem. Okei, tā varētu darīt. Bet tad būtu jābūt skaidriem nosacījumiem, tāpat kā Eiropā, kam to naudu drīkst tērēt."
- kāpēc: Citāts kritizē pašvaldību savstarpējo izlīdzināšanu — naudas pārdali starp pašvaldībām —, nevis nodokļu ieņēmumu dalījumu starp valsti un pašvaldībām, un viņa piedāvātais risinājums ir stingrāki izlietojuma nosacījumi, ne lielāka pašvaldību daļa. Brīfa `par` nozīme prasa tieši pēdējo, tāpēc pēc noteikuma nr. 4 nostāju no šā citāta nolasīt nedrīkst. Otrs fakts, kas turpat blakus: 2026-06-10 tikšanās ar Valsts prezidentu (doc 50867) Kulbergs nodokļu jautājuma atvēršanu četros mēnešos nosauca par „Pandoras lādes“ atvēršanu un aicināja risinājumus meklēt esošajā regulējumā — tātad virzienu viņš apzināti nenosauc. Tas sakrīt ar CVK piezīmi: programma sola „taisnīgāku pašvaldību finanšu modeli“, arī nenosaucot virzienu.
- rezerves:
  1. 2026-06-14, doc 67984, https://www.delfi.lv/video/54057146/kapec/120122178/visu-kas-ierakstits-jaunas-valdibas-deklaracija-nespaspes-izdarit-atzist-kulbergs — tā pati doma, bet žurnālista pārstāstā ar vienu vārdu pēdiņās („soda 'teicamniekus'“), tāpēc verbatim citāta nav.
  2. 2026-07-30, doc 77122, https://pmo.ee/8518528 — "pašvaldībām, kas naudu iemaksā, ir jābūt arī tiesībām aizņemties vairāk" — arī pārstāsts, ne tiešā runa; turklāt runā par aizņemšanās tiesībām, ne par nodokļu daļu.

## q08

- ieteikums: klusē
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: 2026-07-21
- url: https://x.com/AndrisKulbergs/status/2079423623698472961
- document_id: 71493
- citats: "KEM, EM un VARAM apvienošana šobrīd nav valdības prioritāte, un šīs valdības laikā to kvalitatīvi paveikt nepaspēsim. Vispirms nepieciešams nopietns finanšu un funkciju izvērtējums.
  Šo diskusiju turpināsim Nacionālā attīstības plāna izstrādes laikā un pēc vēlēšanām, kad katra partija varēs nākt ar savu redzējumu par efektīvāku valsts pārvaldi."
- kāpēc: Kulbergs ministriju apvienošanu ne apstiprina, ne noraida pēc būtības — viņš to atliek uz Nacionālā attīstības plāna izstrādi un laiku pēc vēlēšanām. Brīfa `par` nozīme prasa apņemšanos apvienot vai likvidēt ministrijas, un citātā tās nav; `pret` nozīme brīfā vispār nav definēta. Tāpēc pēc noteikuma nr. 4 šūna paliek `klusē`, un tas sakrīt ar CVK piezīmi — programma ministriju skaitu nemin.
- rezerves:
  1. 2026-05-29, doc 45504, https://nra.lv/politika/522306-vai-latvija-gaidama-ministriju-optimizacija-kulberga-viedoklis.htm — "Četru mēnešu limitētā laikā likvidēt vai apvienot ministrijas nav prāta darbs, ja enerģija un uzmanība ir jāvelta drošībai - militārai, civilajai, ekonomikas. Reformām vajag laiku un uzmanību, lai nepieļautu kļūdas griezt tikai griešanas pēc" (tā pati atlikšana, agrāks datums).
  2. 2026-07-20, doc 71084, https://www.la.lv/sasteigta-ministriju-apvienosana-pirms-velesanam-kulbergs-so-ideju-vel-neliek-piektaja-atruma — "Mēs atbalstām NA rosināto diskusiju, taču gribētu uz šo jautājumu paskatīties strukturāli un dziļāk" (atbalsts diskusijai, ne apvienošanai; šis ir tuvākais „par“ pusei, bet apņemšanos nesatur).

## q09

- ieteikums: nav atrasts
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: —
- url: —
- document_id: —
- citats: —
- kāpēc: Kulberga paša X kontā 2026. gadā „PVN“ neparādās nevienu reizi (`o_q09own` sijājums — 0 dokumentu no 375). Vienīgie viņa PVN izteikumi ir 2026. gada martā opozīcijā un par **degvielu**, ne pārtiku: 2026-03-26 Saeimas debatēs (doc 2884, delfi.lv) — "Sanāk tā, ka februārī valsts nopelna PVN tiesu litrā 26 centus. Ar cenu 2,07 eiro litrā valsts nopelna 36 centus. Tātad neplānota virspeļņa 10 centu apmērā." Tas apgalvojumu par pārtikas PVN neadresē. Samazinātā 12 % likme maizei, pienam, mājputnu gaļai un olām stājās spēkā 2026-07-01 viņa valdības laikā, taču korpusā to piesaka ekonomikas ministrs Viktors Valainis (ZZS, doc 43872), nevis līderis; divi WebSearch vaicājumi par šo lēmumu Kulberga citātu nedeva. Sakrīt ar CVK piezīmi: programma PVN pārtikai nemin.
- rezerves: nav

## q10

- ieteikums: nav atrasts
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: —
- url: —
- document_id: —
- citats: —
- kāpēc: Pensiju 2. līmenis Kulberga 2026. gada korpusā parādās trīs reizes, un nevienā viņš nerunā pats: doc 24700 ir **retvīts** (@guntarsv teksts par „pensiju izgrābšanas tēmu“ — pēc noteikuma nr. 3 retvīts nav līdera izteikums), doc 49789 ir atminaLV apkopojums, doc 33717 un 57293 ir Saeimas stenogramma un Satversmes tiesas spriedums. Viņa paša pensiju tēmas izteikumi 2026. gadā ir par **bāzes pensiju** (doc 64318: "Pirms pieņemt lēmumus, vēlos redzēt finanšu ietekmes izvērtējumu un saskaņojumu ar @Finmin ministriju.") un par ārvalstu pensiju fondu piesaisti caur ALTUM (doc 79184) — abi 2. līmeņa brīvprātīgumu neadresē. Blakus fakts, kas nav ieteikums: 2026-06-04 (doc 48129) AS finanšu ministrs Māris Kučinskis paziņoja, ka **neatbalsta** 2. līmenī uzkrātā kapitāla izmaksāšanu — tas ir ministrs, ne saraksta līderis, tāpēc šūnu nemaina. Divi WebSearch vaicājumi Kulberga citātu par 2. līmeni nedeva. Sakrīt ar CVK piezīmi: programma 2. pensiju līmeni nemin.
- rezerves: nav

## q12

- ieteikums: klusē
- līmenis: izteikums
- runatajs: Andris Kulbergs (id 10)
- datums: 2026-05-25
- url: https://www.lsm.lv/raksts/zinas/latvija/25.05.2026-premjera-amata-kandidats-kulbergs-necilasim-sabiedribu-skelosus-jautajumus.a648704/
- document_id: 42442 — **DB glabā tikai anotāciju** (328 zīmes), citāts ir tā paša URL pilnajā lapā; re-ingest kandidāts
- citats: "Neskatoties, ka tas ir priekšvēlēšanu laiks un kairinājumi varētu būt dažādi, kā tas mēdz būt, mums ir skaidra vienošanās par to, ka mēs necilājam jautājumus, kas ir šķeļoši."
- kāpēc: Izteikums ir tieši par to jautājumu loku, kurā ietilpst Stambulas konvencija (raksta ievadā tā nosaukta kā piemērs), un tas ir apzināts atteikums ieņemt nostāju, nevis nostāja — tātad `klusē` ar citātu, nevis „nav atrasts“. Ne `par` (ģimene/laulība = vīrietis + sieviete likumos), ne `pret` (laulību vienlīdzība) nozīme no tā nav nolasāma. CVK piezīmei pretrunas nav: programma ģimenes definīciju nedod, sola tikai atbalstu ģimenēm.
- rezerves:
  1. 2026-08-13, nav DB, https://bauskasdzive.lv/latvija-un-pasaule/premjera-kresls-kombains-un-mainitas-sarkanas-linijas-kulberga-skaidrojums/ — "Mēs nekur nerakstījām, ka mums vajag tagad deratificēt, izstāties. Tas ir pavisam cits līmenis." **Brīdinājums operatoram:** šī ir LETA intervijas pārpublikācija, un otrs pārpublicētājs (1188.lv, 2026-08-14, https://www.1188.lv/zinas/kulbergs-par-as-nostaju-stambulas-konvencijas-jautajuma-mes-nekur-nerakstijam-ka-mums-tagad-jaizstajas/71426) to pašu teikumu virsrakstā atveido citiem vārdiem („ka mums tagad jāizstājas“). Divas atšķirīgas redakcijas = pirms lietošanas jāpārbauda pret LETA oriģinālu; verbatim prasībai tas šobrīd neatbilst droši. Pēc satura tas arī adresē tikai izstāšanos no konvencijas, ne ģimenes definīciju.
  2. nav.

## Kopsavilkums

| jautājums | ieteikums | avota tips | document_id vai "ingest" |
|---|---|---|---|
| q02 | par | DB — paša X ieraksts | 92475 |
| q05 | pret | DB — paša X ieraksts | 51779 |
| q06 | nav atrasts | — | — |
| q07 | klusē | DB (tikai anotācija) + tā paša URL pilnā lapa | 54702 + re-ingest |
| q08 | klusē | DB — paša X ieraksts | 71493 |
| q09 | nav atrasts | — | — |
| q10 | nav atrasts | — | — |
| q12 | klusē | DB (tikai anotācija) + tā paša URL pilnā lapa | 42442 + re-ingest |

URL, kas nav DB (ingest kandidāti operatoram):

1. https://bauskasdzive.lv/latvija-un-pasaule/premjera-kresls-kombains-un-mainitas-sarkanas-linijas-kulberga-skaidrojums/ — LETA intervija ar premjeru, 2026-08-13 (Stambulas konvencija, nodokļi, iepirkumi).
2. https://www.1188.lv/zinas/kulbergs-par-as-nostaju-stambulas-konvencijas-jautajuma-mes-nekur-nerakstijam-ka-mums-tagad-jaizstajas/71426 — tās pašas intervijas otra pārpublikācija, 2026-08-14 (vajadzīga tikai redakciju salīdzināšanai).

Re-ingest kandidāti (URL **ir** DB, bet `content` saglabāts kā anotācija — pilnais teksts nekad nav bijis korpusā):

1. doc 54702 — https://www.lsm.lv/raksts/zinas/latvija/15.06.2026-man-ir-ideja-saruna-ar-premjeru-par-planiem-un-prioritatem.a651307/ — 647 zīmes, 83 vārdi, `reviewed_at = 2026-06-15 20:55:19`. Q07 citāts („teicamnieki“) ir tikai pilnajā lapā.
2. doc 42442 — https://www.lsm.lv/raksts/zinas/latvija/25.05.2026-premjera-amata-kandidats-kulbergs-necilasim-sabiedribu-skelosus-jautajumus.a648704/ — 328 zīmes. Q12 citāts ir tikai pilnajā lapā.

Piezīme par šo klasi (NAV ieteikums, bet der `/audit-integrity` pusei): abi dokumenti ir LSM raksti, kas korpusā nonākuši kā RSS anotācija un tomēr saņēmuši `reviewed_at` zīmogu. Praktiskās sekas šim meklējumam bija tiešas — abi q07 un q12 citāti manā SQL sijājumā **neparādījās**, jo atslēgvārdi (`teicamniek`, `necilājam`) glabātajā tekstā vispār nav; tos atradu tikai caur tīmekli. Cik plaša šī klase ir, šis meklējums neizmērīja — tas būtu atsevišķs vaicājums (`word_count < ~120 AND platform='web' AND reviewed_at IS NOT NULL`).

Piezīme par apjomu: Kulbergs 2026. gadā ir Ministru prezidents, tāpēc viņa korpuss (1210 `subject` dokumenti) ir daudzkārt lielāks nekā pārējiem sarakstu līderiem, bet tas ir gandrīz pilnībā valdības ikdienas darbs. Sešas no astoņām brīfa tēmām ir nodokļu un vērtību jautājumi, kurus viņš kā četru mēnešu pagaidu valdības vadītājs apzināti atlika — tas pats atkārtojas q07, q08 un q12 formulējumos („četros mēnešos nav prātīga“, „šīs valdības laikā nepaspēsim“, „necilājam jautājumus, kas ir šķeļoši“). Trīs „nav atrasts“ šeit tāpēc nav korpusa robs, bet konsekvents priekšvēlēšanu klusējums.
