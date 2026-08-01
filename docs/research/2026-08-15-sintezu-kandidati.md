# Sintēžu kandidātu izpēte — 2026-08-15

_Statuss: redakcionāla izpēte, nekas nav publicēts. Dati lasīti no `data/atmina.db` read-only režīmā līdz 2026-08-14 ieskaitot._

## Kā sintēzes strādā

- `wiki_sync()` automātiski ģenerē personu un tēmu profilu metadatus, bet **neraksta redakcionālu sintēzi**.
- Cross-cutting sintēze ir ar roku rakstīts `wiki/synthesis/<slug>.md`; API wrappera nav (`wiki/operations/daily-routine.md`, 230.–237. rinda; standing lēmums `CLAUDE.md`).
- `wiki_sync()` sintēžu failus glob-ē tikai indeksam (`src/wiki.py`). Publisko lapu veido `src/render/syntheses.py`.
- Frontmatter: `title`, `description`, `politicians`, `topics`, `created`; renderis atbalsta TOC no vismaz trim H2, tabulu lokālo ritināšanu, uzticamus repo vidžetus un synthesis attēlu variantus.
- Jaunai sintēzei jālieto parastas Markdown saites, ne Obsidian `[[wikilinks]]` (`tests/test_synthesis_no_wikilinks.py`).

Esošas ir 8 sintēzes. airBaltic jau ir aprīļa pirmā nodaļa — `airbaltic-30-miljoni-koalicijas-kulminacija.md`; izglītībai, Rail Baltica, NVO finansējumam un slimnīcu reformai atsevišķas sintēzes nav.

## Svarīgs wiki skaitļu brīdinājums

`wiki/topics/<slug>.md` individuālo tēmu frontmatter skaita pozīcijas pareizi, bet `wiki/topics/temas.md` indeksa vaicājums `src/wiki.py::_build_topics_index()` savieno katru claim ar visām tās tēmas pretrunām:

```sql
FROM claims c
LEFT JOIN contradictions ct ON ct.topic = c.topic
```

Tāpēc tēmās ar vairāk nekā vienu pretrunu pozīcijas un balsojumi tiek reizināti ar pretrunu skaitu. Piemērs: `Rail Baltica` indeksā ir 210 pozīcijas, bet read-only `claims WHERE claim_type='position'` ir 105; `Koalīcija un partijas` indeksā 4392, bet tieši claims tabulā 488. Šajā izpētē izmantoti tiešie `claims` skaiti, ne kļūdainais indekss.

## 1. Izglītības reforma — BUILD kā priekšlikumu un konfliktu karte

### Ierosinātais leņķis

**“Reforma pirms 1. septembra: piecas izmaiņas un viena koalīcijas bremze”**

Stāsta kodols nav “par vai pret reformu”. Ilzes Indriksones pakete vairākas atšķirīgas reformas salika vienā īsā laika logā, bet koalīcijas pretreakcija koncentrējās uz ieviešanas tempu, tiesisko sagatavotību un skolu gatavību:

- **Eksāmeni:** dabaszinību centralizētais eksāmens 9. klasē;
- **Slieksnis:** minimālā eksāmena sliekšņa atcelšana apliecības saņemšanai;
- **Vērtēšana:** pārbaudes darbu labošanas kārtība;
- **Saturs:** obligātākas paraugprogrammas un ģimenes veselības modulis;
- **Finansēšana:** skolu finansēšanas un pieejamības skolu kritēriju maiņa.

Papildu atzari: iespēja atteikties no 12. klases, stingrāka ārvalstu studentu atlase, skolu tīkla pieejamība, pedagogu algu 57 miljoni un zinātnes finansējuma lietderības strīds.

Sintēzei ir arī agrāks balsojumu mugurkauls — likumprojekts `865/Lp14` par pedagogu darba samaksas sasaisti ar skolēnu skaita rādītājiem. 2026. gada 22. janvāra 3. lasījumā rezultāts bija 49 par, 23 pret, 1 atturas un 13 nebalsoja; 19. februāra otrreizējā caurlūkošanā — 50 par, 38 pret un 1 nebalsoja. Abās reizēs JV, PRO un ZZS balsoja par, bet AS un NA bija pret vai nebalsoja (februārī pret bija arī LPV). **Toreiz tā nebija koalīcijas iekšēja šķelšanās** — AS un NA atradās opozīcijā. Analītiski interesanti ir tas, ka tagad AS un NA vada valdību un izglītības resoru, bet JV un ZZS ir to koalīcijas partneri. Pirms publicēšanas vēl jāpārbauda ārējais juridiskais konteksts, kāpēc likums nonāca otrreizējā caurlūkošanā.

### Datu signāls

Definīcija: `claims.claim_type='position'`, tēma `Izglītība`.

- 121 pozīcija kopā;
- 53 pozīcijas 2026-07-01–2026-08-14;
- 22 atšķirīgi runātāji šajā periodā;
- 21 web un 32 X/X mention avoti;
- 14 partiju programmu solījumi izglītības tēmā.

Spēcīgākais analītiskais slānis būtu salīdzināt rīcību ar programmām: AS pats solīja sakārtot vērtēšanu un eksāmenus, NA solīja skolu tīklu bērnu interesēs un saturisko kontroli, ZZS — mazāk nepabeigtu reformu, JV — obligātu vidējo/profesionālo izglītību. Tas ļauj parādīt, ka strīds neiet vienkārši pa partiju ideoloģijas asi.

### Galvenās avota rindas

- #615907 — Indriksones eksāmenu/sliekšņa pakete: https://www.lsm.lv/raksts/zinas/latvija/04.08.2026-no-septembra-planotas-izmainas-9-klase-varetu-ieviest-dabaszinatnu-eksamenu-bet-atestata-iegusanai-vairs-nevertet-eksamenu-rezultatus.a657378/
- #615908 — paraugprogrammas, ģimenes veselības modulis, tālmācības kritēriji: https://www.lsm.lv/raksts/zinas/latvija/04.08.2026-valdibas-ricibas-plana-izglitibas-nozare-verienigas-ieceres-prieksvelesanu-laika.a657350/
- #689351 un #689641 — LDDK par dabaszinību eksāmenu un astoņu gadu atlikšanu: https://www.lsm.lv/raksts/zinas/ekonomika/07.08.2026-svarigi-latvijas-biznesa-sonedel-mikrotik-ziedojums-rtu-un-lmt-novertejums.a657941/ ; https://x.com/darbadeveji/status/2088174273617661961
- #689467 — Kulbergs piekrīt pilnveidei, bet noraida būtiskas izmaiņas līdz 1. septembrim: https://x.com/AndrisKulbergs/status/2087051418062463326
- #689532 — Ašeradens iebilst pret radikālām izmaiņām īsi pirms mācību gada: https://x.com/aseradens/status/2087469526774362120
- #689537 — Batņa atbalsta dabaszinību eksāmenu, bet iebilst pret pilnīgu sliekšņa atcelšanu: https://pmo.ee/8526242
- #689504 — skolu finansēšanas/pieejamības skolu modelis: https://www.lsm.lv/raksts/zinas/latvija/11.08.2026-piedavatajam-izmainam-skolu-finansesana-vismaz-pagaidam-papildu-nauda-nebus-vajadziga.a658376/

### Robeža

Jāraksta **“ierosināts / virzīts / valdībai vēl jālemj”**, ne “pieņemta reforma”. Stāsts ir publicējams kā priekšlikumu karte jau tagad; hronoloģiska “reformas iznākuma” sintēze jāgaida līdz valdības lēmumiem.

## 2. airBaltic otrā nodaļa — BUILD, ideāli pēc Saeimas lēmuma

### Ierosinātais leņķis

**“No protesta līdz premjera atbildībai: kā Kulbergs mantoja airBaltic 30 miljonu jautājumu”**

Aprīļa sintēze beidzās ar Kulbergu opozīcijā: viņš atteicās “akli balsot” par 30 miljonu aizdevumu bez restrukturizācijas plāna un brīdināja, ka ar 30 miljoniem nepietiks pret 380 miljonu obligāciju slogu. Pēc valdības maiņas tas pats politiķis kļuva par premjeru. Jūlijā viņš prasīja privātos investorus, mazāku valsts lomu, Rīgu kā bāzi un stratēģisku investoru; 14. augustā valdība lūdza Saeimas pilnvarojumu iespējamai līdzdalībai pagaidu finansējumā līdz 30 miljoniem kopā ar privātajiem kreditoriem.

Tas nav automātiski formulējams kā pretruna. Tieši pretēji: sintēzes jautājums ir, vai augusta nosacījumi materializē aprīlī prasīto plānu, vai arī valsts atkal uzņemas to pašu risku citā juridiskā formā.

### Datu signāls

Definīcija: `claims.claim_type='position'`, tēma `airBaltic`.

- 204 pozīcijas kopā;
- 70 pozīcijas no 2026-05-01 līdz 2026-08-14;
- 48 pozīcijas 2026-07-01–2026-08-14 no 12 runātājiem;
- pēdējā logā 22 web un 26 X/X mention avoti;
- 12 airBaltic politiskās spriedzes visā korpusā;
- vecā sintēze aptver aprīļa kulmināciju, ne jauno valdību.

### Galvenās avota rindas

- aprīļa sākumpunkts — esošā sintēze: https://atmina.lv/sintezes/airbaltic-30-miljoni-koalicijas-kulminacija.html
- #532067 — Kulbergs: turpmākiem ieguldījumiem jānāk no privātā sektora: https://nra.lv/ekonomika/latvija/523526-vaditajs-pec-ziemas-sezonas-airbaltic-vajaedzes-papildu-naudas-injekciju.htm
- #548468 — valsts daļa jāsamazina līdz minimumam, sarunas ar trim investoriem: https://www.lsm.lv/raksts/zinas/ekonomika/20.07.2026-premjers-sarunas-par-ieguldisanu-airbaltic-notiek-ar-trim-investoriem.a655585/
- #553975 — Kulbergs lūdz Ģenerālprokuratūrai izvērtēt agrākos lēmumus: https://www.lsm.lv/raksts/zinas/ekonomika/24.07.2026-generalprokuratura-vertes-ar-airbaltic-finansu-situaciju-saistito-lemumu-likumibu.a656250/
- #555721–#555752 — jaunais plāns, Rīga kā bāze, 25 % + 1 akcija, plāns nav automātiska valsts finansējuma piekrišana: https://www.lsm.lv/raksts/zinas/ekonomika/28.07.2026-valdiba-vel-nelemj-par-airbaltic-jauno-biznesa-planu.a656672/
- #689577 — Kulberga pieci nosacījumi: https://x.com/AndrisKulbergs/status/2087811926575190102
- #689618 — Saeimas pilnvarojums nav automātiska 30 miljonu piešķiršana; valsts tikai kopā ar privātajiem kreditoriem: https://www.lsm.lv/raksts/zinas/ekonomika/14.08.2026-valdiba-gatava-pirkt-airbaltic-obligacijas-vel-30-miljonu-eiro-apmera-pagarinas-valsts-aizdevuma-atmaksu.a658885/

### Robeža

Labākais noslēguma punkts ir gaidāmais Saeimas lēmums un precīzie finansējuma nosacījumi. Līdz tam var sagatavot skeletu, bet neapgalvot, ka finansējums piešķirts.

**Atsevišķa audita pēda, ne vēl publicējama pretruna:** Kozlovskis 20. jūlijā teica, ka 31. augusta atmaksas termiņš nav grozāms, jo to apstiprinājusi Saeima (#548462), bet 14. augustā informēja par plānu termiņu pagarināt līdz 31. decembrim (#689616). Pirms jebkādas “apvērsuma” etiķetes jāizlasa pilnā Saeimas un juridiskā ķēde — jauna Saeimas piekrišana var abas pozīcijas savienot.

## 3. Citi kandidāti

### Dombravas vēstule un demisijas kampaņa — BUILD pēc procedūras verifikācijas

Leņķis: **“Kad ministra vēstule kļūst par ārpolitikas un valdības uzticības jautājumu.”** No 3. līdz 14. augustam Dombravas vēstule Spānijai par Seutas krīzi un Pāternieku robežpunkta priekšlikums pārauga opozīcijas demisijas kampaņā, prezidenta iebildumā par ārpolitikas pārstāvības robežām un Kulberga pilnā aizstāvībā. Stāsts ir jauns un blīvs, bet pirms publicēšanas jāpārbauda vēstules pilnais saturs, savākto parakstu statuss un Saeimas demisijas procedūra.

### “Zelta vīzas” — BUILD kā imigrācijas sintēzes turpinājumu

Jūnija imigrācijas vienprātība augustā plaisā pie viena izņēmuma — termiņuzturēšanās atļaujām pret ieguldījumiem. Kulbergs grib instrumentu saglabāt stingrākā formā, Šnore un Ašeradens prasa to izbeigt, bet arī opozīcijā nav vienas līnijas. Tas būtu fokusēts turpinājums, ne esošās imigrācijas sintēzes dublikāts.

### Saeimas kompensācijas un Valsts kontroles revīzija — BUILD kā procesa stāstu

Rasimas mājokļa kompensācijas lieta izauga no individuāla gadījuma līdz KNAB pārbaudei, kompensāciju modeļa kritikai un priekšlikumam ļaut Valsts kontrolei revidēt Saeimu. Spēcīgs institucionāls loks, bet KNAB iznākums vēl ir atvērts; jāapraksta process, ne vainas secinājums.

### NVO finansējums — RESEARCH MORE, pēc tam iespējams BUILD

Stiprākais leņķis: **“Vispirms jāvienojas, ko vispār skaita: NVO finansējuma strīda trīs dažādie saucēji.”**

84 no 87 pozīcijām ir kopš 2026-07-01, iesaistīti 32 runātāji, bet 68 no 84 ir X/X mention un tikai 16 web. Strīda būtība ir empīriska: valsts atbalsts pret deleģēto pakalpojumu apmaksu, telpu noma, LDDK izņēmums, privātais līdzfinansējums. Pirms sintēzes vajadzīga neatkarīga NVO finansējuma datu analīze; pretējā gadījumā sanāks retorikas apkopojums.

### Pretdronu spējas — BUILD pēc tehniskās verifikācijas

Leņķis: **“No maija incidenta līdz augusta notriekšanai: kas mainījās Latvijas pretdronu spējās.”** Tas sasaistītu jau esošās Siliņas valdības krišanas un Sprūda uzbrukumu sintēzes ar jauno valdību, augusta NATO notriekšanu un Melņa solījumu no septembra beigām izmantot Latvijas pārtvērējus un radarus. Risks: “lādiņu nebija” ir strīdīgs tehnisks apgalvojums starp Kulbergu un Sprūdu; vajadzīga iepirkuma/specifikāciju avotu pārbaude, ne abu tvītu salikšana blakus.

### Slimnīcu tīkla reforma — RESEARCH MORE

Augustā ir 25 veselības pozīcijas. Koalīcijā Kulbergs uzstāj, ka reforma ir pieņemta, ZZS prasa to atcelt, bet veselības ministrs Abu Meri aicina saglabāt dzemdību palīdzību Balvos par spīti pašas ministrijas kvalitātes sliekšņa fonam. Labs koalīcijas/pakalpojumu pieejamības stāsts, bet vajag pašas reformas dokumentus, slimnīcu plūsmas un finansējuma datus.

### Rail Baltica “programmas minimums” — BUILD pēc 15. septembra izvērtējuma

No 2026-07-01 ir 37 pozīcijas no 16 runātājiem (14 web, 23 X/X mention). Kulberga valdība virza tehnisko prasību minimumu un iespējamu esošo koridoru izmantošanu; opozīcija prasa atklāt izmaksas un slēgto sēžu pamatojumu. BACKLOG ir atsevišķs sensitīvs Šlesera ģimenes tranzīta biznesa interešu leņķis — to nedrīkst izmantot kā “pretrunu”; tas prasītu atsevišķu uzņēmumu datu un Re:Baltica avota pārbaudi.

## Provizoriskā prioritāte

- **Pirmā prioritāte — izglītības reforma:** publicējama kā priekšlikumu un konfliktu karte jau tagad.
- **Otrā — airBaltic jaunā nodaļa:** redakcionāli visspēcīgākā, bet pilnai hronoloģijai vēlams sagaidīt Saeimas lēmumu.
- **Trešā — Dombravas vēstule:** pilnībā jauns augusta stāsts; vajadzīga procedūras un pilnā dokumenta pārbaude.
- **Ceturtā — Rail Baltica minimuma modelis:** politiskā ass ir gatava, izmaksu ass būs pilnīgāka pēc 15. septembra.
- **Piektā — “zelta vīzu” plaisa:** fokusēts un publicējams esošās imigrācijas sintēzes turpinājums.
- **Sestā — Saeimas kompensāciju kontrole:** labs institucionāls process bez nepieciešamības sagaidīt vainas secinājumu.
- **Septītā — pretdronu spēju evolūcija:** labs starpvaldību stāsts pēc tehniskās verifikācijas.
- **Astotā — NVO finansējuma saucēji:** vispirms datu analīze, tad sintēze.
- **Devītā — slimnīcu tīkla reforma:** vispirms savākt politikas dokumentus un reģionālos datus.

## Izmantotais skaitīšanas vaicājums

```sql
SELECT c.topic,
       COUNT(*) AS total,
       SUM(CASE WHEN c.stated_at >= '2026-07-01' THEN 1 ELSE 0 END) AS recent,
       COUNT(DISTINCT CASE WHEN c.stated_at >= '2026-07-01'
                           THEN COALESCE(c.speaker_id, c.opponent_id) END) AS actors,
       SUM(CASE WHEN c.stated_at >= '2026-07-01' AND d.platform='web'
                THEN 1 ELSE 0 END) AS web,
       SUM(CASE WHEN c.stated_at >= '2026-07-01'
                     AND d.platform IN ('twitter','x_mention')
                THEN 1 ELSE 0 END) AS x
FROM claims c
LEFT JOIN documents d ON d.id = c.document_id
WHERE c.claim_type='position'
GROUP BY c.topic;
```
