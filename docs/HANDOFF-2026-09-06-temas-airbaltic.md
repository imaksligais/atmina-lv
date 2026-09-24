# Nodošana: tēmu lapas un airBaltic sintēzes turpinājums

Datums: 2026-09-06. **Statuss 2026-09-07: IZPILDĪTS** — tēmu lapas A1–A5 (`2b48c541`), airBaltic 1. daļas labojums + 2. daļa publicēta (`8a82c5ae`), Nozīmīgums → vārds (`f9f9c3e2`; deploy ar nākamo rutīnu). Sākotnējais teksts zemāk saglabāts kā vēsture.

## Lietotāja uzdevums un nodošanas robeža

Lietotājs lūdza izvērtēt https://atmina.lv/temas.html un dziļākos līmeņus, izlasot CLAUDE.md un wiki. Pēc priekšlikumu saņemšanas lūdza uzrakstīt nodošanas failu otram aģentam un norādīja, ka vajag atjaunot airBaltic sintēzi vai uzrakstīt tās otro daļu.

Šis ir darba pamats nākamajam aģentam. Izpētes laikā kods, DB un publicētie raksti nav mainīti. Sintēzes turpinājums vēl nav uzrakstīts. Zemākā UI secība ir ieteikums, ne apgalvojums, ka visi lielie papildinājumi jau apstiprināti. Publicēšanas atļauja šajā sarunā nav dota; sagatavo konkrētu, pārbaudītu rezultātu pirms publicēšanas apstiprinājuma prasīšanas.

Pirms darba lasīt:

- [CLAUDE.md](../CLAUDE.md), [wiki indeksu](../wiki/index.md), [portabilitāti](../wiki/operations/portability.md).
- [Vietnes backlog](../backlog/vietne-ui.md), [BACKLOG aizliegumus un lēmumus](../BACKLOG.md).
- [Kvalitātes kritērijus](../wiki/operations/quality-bars.md).

## Izpētes pierādījumi un ierobežojumi

Tīmekļa lasītājs atdeva dažāda vecuma kopijas, tādēļ būtiskie novērojumi pārbaudīti arī ar tiešu HTTP GET. 2026-09-06 direktorija, airBaltic, klimata un pretrunas Nr. 24 lapas atdeva HTTP 200; to Last-Modified bija 2026-09-05. Tieši nolasīta arī airBaltic sintēze. Pārlūka vizuālā/mobilā pārbaude nebija iespējama — ekrānattēlu audits NAV veikts.

- Publiskajā direktorijā bija 33 tēmas; airBaltic — 247 pozīcijas, Klimats — 19.
- Abu šo tēmu HTML saturēja tieši 15 pozīciju kartītes, bez saites uz pilnu tēmas arhīvu.
- Wiki airBaltic metadatos bija 254 pozīcijas. Neuzskatīt šo atšķirību automātiski par kļūdu: pārbaudīt momentuzņēmuma datumu un atlases nosacījumus. Vietnes vaicājums izslēdz neaktīvos profilus.
- Šīs vērtības ir momentuzņēmums; nākamajā sesijā skaitļus pārmērīt, ja tos izmanto tekstā vai pārbaudēs.

Galvenie faili: [topics.py](../src/render/topics.py), [temas.html.j2](../templates/temas.html.j2), [tema.html.j2](../templates/tema.html.j2), [pzv1.js](../assets/pzv1.js), [ppv1.js](../assets/ppv1.js), [syntheses.py](../src/render/syntheses.py).

## A. Tēmu lapu pirmā ieviešanas kārta

### A1. Atvērt visu tēmas vēsturi

`_fetch_topic_detail()` atlasa `LIMIT 15`. Zem saraksta pievienot “Skatīt visas N pozīcijas”, kas ved uz `pozicijas.html?tema=<kodēts kanoniskais nosaukums>`. `assets/pzv1.js` jau lasa `tema`, `persona` un `partija` URL parametrus. Kopskaitam izmantot tos pašus atlases nosacījumus kā direktorijai, ne wiki skaitli.

Pie saraksta skaidri norādīt, ka redzamas tikai jaunākās pozīcijas. Arhīva saitei jādarbojas arī tad, ja kopā ir mazāk par 15 ierakstiem; formulējumu pielāgot faktiskajam skaitam.

### A2. Saglabāt tēmu, pārejot uz profilu

Tēmas lapas personu saitēm pievienot `?tema=<kodēts kanoniskais nosaukums>`. `assets/ppv1.js` šo parametru jau atbalsta un validē pret profilā esošajiem filtriem. Aptvert gan augšējo personu sarakstu, gan pozīciju autoru saites un saglabātās apakšējās saites. Pārbaudīt tēmas ar atstarpēm un diakritiskajām zīmēm.

### A3. Salabot sintēžu piesaisti tēmām

Apstiprināts koda un datu formāta nesakritības cēlonis: `topics.py` salīdzina `name in s['topics']`, bet `_load_syntheses()` frontmatter tēmas nodod bez normalizācijas. Deviņos `wiki/synthesis/*.md` failos tēmas pārsvarā ir slugi, piemēram, `koalicija-un-partijas`, ne `Koalīcija un partijas`. `airBaltic` sakrīt tieši, tādēļ šis gadījums maskē pārējo problēmu.

Izvēlēties vienotu piesaistes līgumu, pieņemot esošos kanoniskos nosaukumus un slugus. Neveikt `claims.topic` migrāciju šīs renderēšanas problēmas dēļ. Pārbaudīt visas 9 sintēzes un katru deklarēto tēmu. Īpaši apskatīt `socialaa-politika` failā `saeima-2026-04-30-balsojumi.md`: tā ir atsevišķa iespējamā drukas kļūda, ne tikai sluga/nosaukuma atšķirība. Neatpazītu tēmu uzrādīt, ne klusi izmest.

Šis ir jauns piesaistes atradums, ne agrāk slēgtā wikilinku/bezpaplašinājuma URL problēma.

### A4. Padarīt turpinājumu saturiski saistītu

Pašreiz `other_topics = [t for t in all_topics if t['name'] != name][:5]` izvēlas lielākās tēmas. Ieviest nelielu skaidri definētu saistīto tēmu karti, piemēram:

- airBaltic → Transports, Valsts kapitālsabiedrības, Budžets un finanses.
- Klimats → Vide, Degviela un enerģētika, Lauksaimniecība.

Samazināt augšējā personu/pretrunu saraksta atkārtošanu “Turpini rakt”. Apakšējā blokā dot jaunus ceļus: arhīvs, radniecīgas tēmas, analīzes.

### A5. Skaidrākas etiķetes un datumi

- “Top politiķi par tēmu” → “Visvairāk fiksēto pozīciju”; skaits nav kompetences vērtējums. Atlase ietver arī komentētājus, tāpēc neapzīmēt visus par politiķiem.
- Sintēžu kartītēm rādīt raksta datumu; vēlāk arī aptverto periodu, ja tas ir skaidri modelēts.
- Pretrunas Nr. 24 lapā “Pašlaik” apzīmē 2026-04-14 ierakstu. Vēsturiskām salīdzinājuma pusēm piemērot “Iepriekš / Vēlāk”, pārbaudot `new_label` izņēmumus veidnē.
- “Nozīmīgums 0.50” lasītājam nepaskaidro vērtējumu. Izvērtēt pārcelšanu uz metodoloģijas detaļām vai saprotamu paskaidrojumu.
- `pmo.ee` izdevēja etiķetes labojumu saskaņot ar esošo `backlog/vietne-ui.md` ierakstu: etiķete no `documents.source_domain`, sākotnējais URL paliek.

### Pirmās kārtas pārbaudes

- [ ] airBaltic un Klimats: redzamais skaits, kopskaits un pāreja uz pilno arhīvu saskan.
- [ ] Profilā pēc pārejas ir atlasīta sākotnējā tēma.
- [ ] Visu 9 sintēžu tēmu piesaistes pārbaudītas; uzrādīts pārbaudīto atsauču un neatpazīto vērtību skaits.
- [ ] “Citas tēmas” dod definētās radniecīgās tēmas, ne globālo topu.
- [ ] Nav salauztu saišu vai dubultas URL dekodēšanas problēmu.
- [ ] Vizuāli pārbaudīts gan plats, gan šaurs ekrāns, tastatūras lietojamība un garie LV nosaukumi.
- [ ] Palaistas skartajām uzvedībām atbilstošas regresijas pārbaudes un repo prasītie rendera/kvalitātes vārti. Skatīt CLAUDE.md un quality-bars.md; šo failu neuzskatīt par to aizvietotāju.

## B. Turpmākais produkta virziens

Pēc pirmās kārtas izveidot airBaltic kā paraugu un salīdzināt ar mazāko klimata tēmu.

Direktorijai: meklēšana pēc tēmas/sinonīmiem, kārtošana alfabētiski/pēc jaunākās aktivitātes/pēc apjoma, īss tvēruma apraksts un pēdējās pozīcijas datums. Sākumā saglabāt 33 kanoniskās tēmas un adreses.

Tēmas lapas vēlamā secība: īss tvērums un periods → konkrētie jautājumi → redakcionāli izcelta analīze → filtrējamas pozīcijas un arhīvs → atsevišķi pozīciju maiņas, balsojumi, programmu solījumi → saistītās tēmas.

Lielākais iespējamais papildinājums: konkrēta jautājuma salīdzinājums pa personām/partijām, ar nosacījumiem, datumu un avotu. Piemērs: “Papildu valsts finansējums airBaltic”, ne vispārīgs “par/pret airBaltic”. Informācijas trūkumu apzīmēt “Nav fiksētas pozīcijas”. Programmu solījumus nejaukt ar individuālām pozīcijām; balsojumus nejaukt ar mediju izteikumiem.

Neieviest automātiskas sintēzes, sentimentu vai nepamatotu konsekvences reitingu. Atkārtotu viena notikuma atspoguļojumu var grupēt skatā ar visiem avotiem; tas nav pamats automātiski dzēst DB rindas. Garu pozīciju lasāmību risināt attēlojumā, nezaudējot nosacījumus.

## C. airBaltic sintēze: sagatavot otro daļu

**Ieteiktā izvēle: jauna otrā daļa, saglabājot aprīļa rakstu kā vēsturisku analīzi.** Lietotājs tieši norādīja, ka vajadzīgs atjauninājums vai otrā daļa. Jaunais raksts ir patstāvīgs redakcionāls uzdevums, ne tikai UI darba izvēles papildinājums.

Pirmā daļa: [wiki avots](../wiki/synthesis/airbaltic-30-miljoni-koalicijas-kulminacija.md), [publiskā lapa](https://atmina.lv/sintezes/airbaltic-30-miljoni-koalicijas-kulminacija.html), datēta 2026-04-22.

Darba virsraksts, kas jāprecizē pēc avotu izlasīšanas: **“airBaltic pēc 30 miljonu aizdevuma: finansējums, kreditori un politiskā atbildība”**. Neizmantot nepārbaudītu finansējuma summu vai “pretrunu” kā virsraksta pieņēmumu.

### Izpētes uzdevums

1. Izlasīt pirmo daļu pilnībā. Izveidot tabulu ar tās prognozēm/apgalvojumiem, pārbaudāmo iznākumu, datumu un pirmavotu. Vēsturisku prognozi saglabāt kā prognozi; faktisku kļūdu labot ar skaidru labojuma piezīmi.
2. Aptvert notikumus pēc 2026-04-22 līdz pēdējai faktiski pārbaudītajai dienai. Ja darbu turpina vēlāk, neapstāties pie šī handoff datuma. Lasīt pilno attiecīgo pozīciju korpusu, saistītos dokumentus, pārskatus, kontekstu un balsojumus, ne tikai 15 publiski redzamās rindas.
3. Par katru finansējuma instrumentu nošķirt summu, procentu likmi un tās nozīmi, termiņu, aizņēmēju, naudas devēju, valsts daļu un lēmuma stadiju: piedāvāts / pilnvarots / noslēgts / izmaksāts. Politiskajā izteikumā minēts skaitlis pats par sevi nav darījuma fakta pierādījums.
4. Pārbaudīt pirmavotos uzņēmuma un valsts lēmumus, kreditoru vienošanās, atmaksas termiņa izmaiņas un faktisko valsts līdzdalību. Mediju/X pozīcijas izmantot politiķu teiktā atribūcijai, ne automātiski finanšu nosacījumu apstiprināšanai.
5. Izsekot, kā mainījās konkrētu personu argumenti un nosacījumi. Amatus un partijas attiecināt uz notikuma laiku. Nošķirt publisku kritiku, priekšlikumu, valdības lēmumu un Saeimas balsojumu.
6. Par balsojumiem izlasīt pilnu saistīto balsojumu ķēdi un frakciju sastāvu attiecīgajā balsojumā (CLAUDE.md T6/T14). Frakcijas šķelšanos nevar pierādīt ar diviem atlasītiem cilvēkiem.

### Konkrēti pavedieni pārbaudei, ne gatavi secinājumi

- Pavasara 30 miljonu aizdevums, tā termiņš un turpmākā pārfinansēšana.
- Augusta diskusijas par līdz 30 miljonu papildu dalību, privāto kreditoru iesaisti un restrukturizācijas priekšnosacījumiem.
- Septembra sākuma izteikumi par 257 miljonu aizņēmumu un 25 % likmi: pārbaudīt darījuma dokumentus un precīzu nosacījumu nozīmi pirms publicēšanas.
- Investora piesaiste, valsts kontroles/līdzdalības iespējamās izmaiņas un Rīgas savienojamības arguments.
- Kulberga nosacījumi, Valaiņa publiski paustais, Švinkas argumenti un pārējo personu atšķirīgās nostājas. Tās nav automātiski pretrunas.

**Jau dokumentēts slazds:** quality-bars.md apraksta kļūdainu “vienā dienā” ierāmējumu par Kulbergu. Aicinājums Saeimā bija 2026-08-20, 14,5 % darījuma vērtējums — 08-21; raksta publicēšanas datums radīja šķietamu sakritību. Lasīt šo piemēru un pārbaudīt pirmavota notikuma datumu, ne paļauties vienīgi uz `stated_at`.

Pirmās daļas pārskatīšanas kandidāti: apgalvojums par ZZS sašķelšanos “pa pusēm”; prognoze par nākamo balsojumu pirms 31.08.; pārvaldības modeļa un valsts finansējuma nošķīrums. Šajā auditā tie NAV galīgi pārbaudīti vai atzīti par kļūdām. Pretrunu Nr. 24 nepārklasificēt bez attiecīgās verifikācijas procedūras.

### Ieteicamā raksta uzbūve

- Ko aprīlī lēma un kas kopš tā laika ir mainījies.
- Īsa pārbaudīto notikumu hronoloģija.
- Finansējuma instrumentu tabula ar avotiem un lēmumu statusu.
- Ko kurš solīja/atbalstīja un ar kādiem nosacījumiem; vēlākā rīcība, ja pierādāma.
- Kas no pirmās daļas prognozēm piepildījās, nepiepildījās vai vēl nav nosakāms.
- Atvērtie jautājumi, par kuriem publisko pierādījumu nepietiek.
- Avoti un skaidrs analīzes beigu datums.

Sintēzi rakstīt manuāli. Neizdomāt pozīciju maiņas un nepadarīt personas apgalvojumu par autora apstiprinātu faktu. Katrā būtiskā faktā skaidra avota saite, citāti burtiski, secinājumu pamatojums izsekojams.

### Nodevums un publicēšana

- Sagatavot otrās daļas melnrakstu un avotu/pārbaudes pierakstu. Kamēr nav gatavs publicēšanai, turēt melnrakstu ārpus automātiski renderētās `wiki/synthesis/` mapes, piemēram, `docs/drafts/`.
- Gatavajam rakstam paredzēt atsevišķu slugu un saites uz pirmo daļu. Pirmajai daļai sagatavot īsu norādi uz turpinājumu; nepārrakstīt visu vēsturi kā šodienas situāciju.
- Sintēzes frontmatter tēmas saskaņot ar A3 atrisināto līgumu. Pārbaudīt, ka tēmas lapā abas daļas parādās ar datumiem.
- Pārbaudīt LV valodu, citātus, atribūciju, hronoloģiju, tabulas, saites un mobilās lapas izskatu. Attēlu, ja paredzēts, sagatavot un nodot apskatei.
- Publiskošanu veikt tikai pēc repo prasītajiem vārtiem un konkrēta operatora apstiprinājuma. Melnraksta esamība build kokā nav publicēšanas atļauja.

## D. Praktiska piezīme nākamajai sesijai

Šajā vidē `rg` nebija pieejams. `.venv/Scripts/python.exe` mēģinājums apstājās ar trūkstošu bāzes Python 3.12 ceļu; analīzes/rendera testi nav palaisti. Neaizvietot to ar nejaušu globālo Python (CLAUDE.md brīdina par citas vides izmantošanu). Ja nepieciešams izpildīt kodu, vispirms sakārtot paredzēto projekta vidi.

Tiešais HTTP pieprasījums sākotnēji neizdevās tīkla ierobežojumu dēļ, pēc eskalēta izsaukuma izdevās. PowerShell `Invoke-WebRequest.Content` šeit nepareizi dekodēja UTF-8; korektai LV nolasīšanai izmantots `UTF8.GetString(response.RawContentStream.ToArray())`. Tā nebija apstiprināta vietnes kodējuma kļūda.
